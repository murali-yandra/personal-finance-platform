"""Audit persistence rules (04-database_schema.md section 4.12)."""

from uuid import uuid4

import pytest
from sqlmodel import Session, select

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import CreateAccountCommand, UpdateAccountCommand
from app.domains.accounts.service import AccountService
from app.domains.audit.models import AuditLog
from app.domains.audit.repository import AuditRepository
from app.domains.audit.service import AuditService
from app.domains.users.models import User, UserSettings
from app.events.base_event import BaseEvent
from app.shared.enums import AccountType, AuditAction, AuditSource


@pytest.fixture
def user(db_session: Session) -> User:
    created = User(
        email="owner@example.com",
        password_hash="hash",
        display_name="Owner",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def audit_service(db_session: Session) -> AuditService:
    return AuditService(repository=AuditRepository(db_session))


def _entries(session: Session) -> list[AuditLog]:
    return list(session.exec(select(AuditLog)).all())


def test_create_event_writes_a_single_create_row(
    db_session: Session,
    audit_service: AuditService,
    user: User,
) -> None:
    entity_id = uuid4()
    audit_service.publish(
        BaseEvent(
            event_type="AccountCreated",
            payload={
                "entity_type": "account",
                "entity_id": str(entity_id),
                "user_id": str(user.id),
            },
        )
    )
    db_session.commit()

    entries = _entries(db_session)
    assert len(entries) == 1
    assert entries[0].action == AuditAction.CREATE
    assert entries[0].entity_type == "account"
    assert entries[0].entity_id == entity_id
    assert entries[0].source == AuditSource.USER


def test_update_event_writes_one_row_per_changed_field(
    db_session: Session,
    audit_service: AuditService,
    user: User,
) -> None:
    audit_service.publish(
        BaseEvent(
            event_type="AccountUpdated",
            payload={
                "entity_type": "account",
                "entity_id": str(uuid4()),
                "user_id": str(user.id),
                "changes": {
                    "account_name": ["Old", "New"],
                    "bank_name": ["ICICI", "HDFC"],
                },
            },
        )
    )
    db_session.commit()

    entries = _entries(db_session)
    assert len(entries) == 2
    by_field = {entry.field_name: entry for entry in entries}
    assert by_field["account_name"].old_value == "Old"
    assert by_field["account_name"].new_value == "New"
    assert by_field["bank_name"].new_value == "HDFC"


def test_event_without_user_id_is_skipped(
    db_session: Session,
    audit_service: AuditService,
) -> None:
    audit_service.publish(
        BaseEvent(
            event_type="AccountCreated",
            payload={"entity_type": "account", "entity_id": str(uuid4())},
        )
    )
    db_session.commit()

    assert _entries(db_session) == []


def test_correlation_id_is_recorded(
    db_session: Session,
    user: User,
) -> None:
    correlation_id = uuid4()
    request_id = uuid4()
    service = AuditService(
        repository=AuditRepository(db_session),
        correlation_id=correlation_id,
        request_id=request_id,
    )

    service.publish(
        BaseEvent(
            event_type="AccountCreated",
            payload={
                "entity_type": "account",
                "entity_id": str(uuid4()),
                "user_id": str(user.id),
            },
        )
    )
    db_session.commit()

    entry = _entries(db_session)[0]
    assert entry.correlation_id == correlation_id
    assert entry.request_id == request_id


def test_account_service_writes_audit_rows_through_the_publisher(
    db_session: Session,
    audit_service: AuditService,
    user: User,
) -> None:
    """Sprint 2 raised the events; Sprint 3 persists them with no service change."""
    service = AccountService(
        repository=AccountRepository(db_session),
        event_publisher=audit_service,
    )

    account = service.create_account(
        CreateAccountCommand(
            user_id=user.id,
            account_type=AccountType.BANK,
            account_name="Salary",
            bank_name="ICICI",
            last_four_digits="0452",
        )
    )
    service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            account_name="Primary Salary",
        )
    )
    service.archive_account(user_id=user.id, account_id=account.id)

    entries = _entries(db_session)
    actions = [entry.action for entry in entries]
    assert actions.count(AuditAction.CREATE) == 1
    assert actions.count(AuditAction.ACCOUNT_UPDATE) == 1
    assert actions.count(AuditAction.UPDATE) == 1
    assert all(entry.entity_id == account.id for entry in entries)


def test_audit_rows_do_not_survive_a_rolled_back_change(
    db_session: Session,
    audit_service: AuditService,
    user: User,
) -> None:
    """The audit write shares the caller's transaction, so a failure loses both."""
    service = AccountService(
        repository=AccountRepository(db_session),
        event_publisher=audit_service,
    )
    service.create_account(
        CreateAccountCommand(
            user_id=user.id,
            account_type=AccountType.BANK,
            bank_name="ICICI",
            last_four_digits="0452",
        )
    )
    committed = len(_entries(db_session))

    from app.domains.accounts.exceptions import AccountAlreadyExistsError

    with pytest.raises(AccountAlreadyExistsError):
        service.create_account(
            CreateAccountCommand(
                user_id=user.id,
                account_type=AccountType.BANK,
                bank_name="ICICI",
                last_four_digits="0452",
            )
        )

    assert len(_entries(db_session)) == committed
    assert len(list(db_session.exec(select(Account)).all())) == 1


def test_audit_repository_exposes_no_mutation_methods() -> None:
    """Audit rows are append-only: there must be no update or delete path."""
    method_names = {name for name in dir(AuditRepository) if not name.startswith("_")}

    assert not {"update", "delete", "remove", "purge"} & method_names
