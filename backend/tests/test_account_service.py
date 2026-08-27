"""Service-level rules for account management (Sprint 2, issue #63)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.domains.accounts.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AccountValidationError,
    ArchivedAccountImmutableError,
    InvalidAccountStatusTransitionError,
    InvalidAccountTypeError,
)
from app.domains.accounts.repository import AccountRepository
from app.domains.accounts.schemas import (
    CreateAccountCommand,
    ListAccountsQuery,
    UpdateAccountCommand,
)
from app.domains.accounts.service import AccountService
from app.domains.users.models import User, UserSettings
from app.events.publisher import RecordingEventPublisher
from app.shared.enums import AccountStatus, AccountType


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
def other_user(db_session: Session) -> User:
    created = User(
        email="intruder@example.com",
        password_hash="hash",
        display_name="Intruder",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def publisher() -> RecordingEventPublisher:
    return RecordingEventPublisher()


@pytest.fixture
def service(
    db_session: Session,
    publisher: RecordingEventPublisher,
) -> AccountService:
    return AccountService(
        repository=AccountRepository(db_session),
        event_publisher=publisher,
    )


def _create(service: AccountService, user: User, **overrides) -> object:
    command_fields = {
        "user_id": user.id,
        "account_type": AccountType.BANK,
        "account_name": "Salary Account",
        "bank_name": "ICICI",
        "last_four_digits": "0452",
    }
    command_fields.update(overrides)
    return service.create_account(CreateAccountCommand(**command_fields))


def test_create_account_persists_active_account(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user)

    assert account.id is not None
    assert account.user_id == user.id
    assert account.account_type == "BANK"
    assert account.status == AccountStatus.ACTIVE


def test_create_account_seeds_estimated_balance_from_opening_balance(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user, opening_balance=Decimal("2500.50"))

    assert account.opening_balance == Decimal("2500.50")
    assert account.estimated_balance == Decimal("2500.50")


def test_create_account_raises_account_created_event(
    service: AccountService,
    user: User,
    publisher: RecordingEventPublisher,
) -> None:
    account = _create(service, user)

    assert publisher.event_types() == ["AccountCreated"]
    assert publisher.events[0].payload["entity_id"] == str(account.id)


def test_create_account_allows_pending_for_detected_accounts(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user, status=AccountStatus.PENDING)

    assert account.status == AccountStatus.PENDING


def test_create_account_rejects_archived_status(
    service: AccountService,
    user: User,
) -> None:
    with pytest.raises(AccountValidationError):
        _create(service, user, status=AccountStatus.ARCHIVED)


def test_create_account_rejects_unknown_account_type(
    service: AccountService,
    user: User,
) -> None:
    with pytest.raises(InvalidAccountTypeError):
        _create(service, user, account_type="WALLET")


def test_create_account_rejects_non_numeric_last_four_digits(
    service: AccountService,
    user: User,
) -> None:
    with pytest.raises(AccountValidationError):
        _create(service, user, last_four_digits="04X2")


def test_create_account_rejects_invalid_currency(
    service: AccountService,
    user: User,
) -> None:
    with pytest.raises(AccountValidationError):
        _create(service, user, currency="RUPEE")


def test_create_account_rejects_duplicate_for_same_user(
    service: AccountService,
    user: User,
) -> None:
    _create(service, user)

    with pytest.raises(AccountAlreadyExistsError):
        _create(service, user)


def test_same_account_identity_is_allowed_across_users(
    service: AccountService,
    user: User,
    other_user: User,
) -> None:
    _create(service, user)
    account = _create(service, other_user)

    assert account.user_id == other_user.id


def test_get_account_rejects_cross_user_access(
    service: AccountService,
    user: User,
    other_user: User,
) -> None:
    account = _create(service, user)

    with pytest.raises(AccountNotFoundError):
        service.get_account(user_id=other_user.id, account_id=account.id)


def test_get_account_rejects_unknown_account(
    service: AccountService,
    user: User,
) -> None:
    with pytest.raises(AccountNotFoundError):
        service.get_account(user_id=user.id, account_id=uuid4())


def test_list_accounts_excludes_archived_by_default(
    service: AccountService,
    user: User,
) -> None:
    kept = _create(service, user, last_four_digits="1111")
    archived = _create(service, user, last_four_digits="2222")
    service.archive_account(user_id=user.id, account_id=archived.id)

    accounts = service.list_accounts(ListAccountsQuery(user_id=user.id))

    assert [account.id for account in accounts] == [kept.id]


def test_list_accounts_includes_pending_and_disabled(
    service: AccountService,
    user: User,
) -> None:
    pending = _create(
        service,
        user,
        last_four_digits="1111",
        status=AccountStatus.PENDING,
    )
    active = _create(service, user, last_four_digits="2222")
    service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=active.id,
            status=AccountStatus.DISABLED,
        )
    )

    accounts = service.list_accounts(ListAccountsQuery(user_id=user.id))

    assert {account.id for account in accounts} == {pending.id, active.id}


def test_list_accounts_can_include_archived_explicitly(
    service: AccountService,
    user: User,
) -> None:
    archived = _create(service, user)
    service.archive_account(user_id=user.id, account_id=archived.id)

    accounts = service.list_accounts(
        ListAccountsQuery(user_id=user.id, include_archived=True)
    )

    assert [account.id for account in accounts] == [archived.id]


def test_list_accounts_never_returns_another_users_accounts(
    service: AccountService,
    user: User,
    other_user: User,
) -> None:
    _create(service, user)

    accounts = service.list_accounts(ListAccountsQuery(user_id=other_user.id))

    assert accounts == []


def test_update_account_changes_metadata_and_raises_event(
    service: AccountService,
    user: User,
    publisher: RecordingEventPublisher,
) -> None:
    account = _create(service, user)

    updated = service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            account_name="Primary Salary",
        )
    )

    assert updated.account_name == "Primary Salary"
    assert publisher.event_types() == ["AccountCreated", "AccountUpdated"]
    changes = publisher.events[-1].payload["changes"]
    assert changes["account_name"] == ["Salary Account", "Primary Salary"]


def test_update_account_without_changes_raises_no_event(
    service: AccountService,
    user: User,
    publisher: RecordingEventPublisher,
) -> None:
    account = _create(service, user)

    service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            account_name="Salary Account",
        )
    )

    assert publisher.event_types() == ["AccountCreated"]


def test_update_account_rejects_cross_user_access(
    service: AccountService,
    user: User,
    other_user: User,
) -> None:
    account = _create(service, user)

    with pytest.raises(AccountNotFoundError):
        service.update_account(
            UpdateAccountCommand(
                user_id=other_user.id,
                account_id=account.id,
                account_name="Stolen",
            )
        )


def test_update_account_rejects_duplicate_identity(
    service: AccountService,
    user: User,
) -> None:
    _create(service, user, last_four_digits="1111")
    second = _create(service, user, last_four_digits="2222")

    with pytest.raises(AccountAlreadyExistsError):
        service.update_account(
            UpdateAccountCommand(
                user_id=user.id,
                account_id=second.id,
                last_four_digits="1111",
            )
        )


def test_archived_account_cannot_be_modified(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user)
    service.archive_account(user_id=user.id, account_id=account.id)

    with pytest.raises(ArchivedAccountImmutableError):
        service.update_account(
            UpdateAccountCommand(
                user_id=user.id,
                account_id=account.id,
                account_name="Reopened",
            )
        )


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (AccountStatus.PENDING, AccountStatus.ACTIVE),
        (AccountStatus.PENDING, AccountStatus.DISABLED),
        (AccountStatus.ACTIVE, AccountStatus.DISABLED),
    ],
)
def test_allowed_status_transitions(
    service: AccountService,
    user: User,
    start: AccountStatus,
    target: AccountStatus,
) -> None:
    account = _create(service, user, status=start)

    updated = service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            status=target,
        )
    )

    assert updated.status == target


def test_disabled_account_can_be_reactivated(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user)
    service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            status=AccountStatus.DISABLED,
        )
    )

    updated = service.update_account(
        UpdateAccountCommand(
            user_id=user.id,
            account_id=account.id,
            status=AccountStatus.ACTIVE,
        )
    )

    assert updated.status == AccountStatus.ACTIVE


def test_active_account_cannot_return_to_pending(
    service: AccountService,
    user: User,
) -> None:
    account = _create(service, user)

    with pytest.raises(InvalidAccountStatusTransitionError):
        service.update_account(
            UpdateAccountCommand(
                user_id=user.id,
                account_id=account.id,
                status=AccountStatus.PENDING,
            )
        )


def test_archive_account_sets_archived_status_without_deleting(
    service: AccountService,
    user: User,
    db_session: Session,
    publisher: RecordingEventPublisher,
) -> None:
    account = _create(service, user)

    archived = service.archive_account(user_id=user.id, account_id=account.id)

    assert archived.status == AccountStatus.ARCHIVED
    assert publisher.event_types() == ["AccountCreated", "AccountArchived"]

    from app.domains.accounts.models import Account

    assert db_session.get(Account, account.id) is not None


def test_archive_account_is_idempotent(
    service: AccountService,
    user: User,
    publisher: RecordingEventPublisher,
) -> None:
    account = _create(service, user)
    service.archive_account(user_id=user.id, account_id=account.id)

    again = service.archive_account(user_id=user.id, account_id=account.id)

    assert again.status == AccountStatus.ARCHIVED
    assert publisher.event_types().count("AccountArchived") == 1


def test_archive_account_rejects_cross_user_access(
    service: AccountService,
    user: User,
    other_user: User,
) -> None:
    account = _create(service, user)

    with pytest.raises(AccountNotFoundError):
        service.archive_account(user_id=other_user.id, account_id=account.id)
