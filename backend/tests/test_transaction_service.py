"""Transaction lifecycle rules (Sprint 3)."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlmodel import Session

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.transactions.exceptions import (
    DuplicateTransactionError,
    InvalidAmountError,
    MissingAccountError,
    TransactionNotFoundError,
    TransactionValidationError,
)
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import (
    CreateTransactionCommand,
    ListTransactionsQuery,
    UpdateTransactionCommand,
)
from app.domains.transactions.service import TransactionService
from app.domains.users.models import User, UserSettings
from app.events.publisher import RecordingEventPublisher
from app.shared.enums import (
    AccountStatus,
    AccountType,
    BusinessType,
    TransactionDirection,
)

TIMESTAMP = datetime(2026, 6, 2, 10, 0, 0)


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
def account(db_session: Session, user: User) -> Account:
    created = Account(
        user_id=user.id,
        account_name="Salary",
        account_type=AccountType.BANK.value,
        bank_name="ICICI",
        last_four_digits="0452",
        status=AccountStatus.ACTIVE.value,
    )
    db_session.add(created)
    db_session.commit()
    return created


@pytest.fixture
def publisher() -> RecordingEventPublisher:
    return RecordingEventPublisher()


@pytest.fixture
def service(
    db_session: Session,
    publisher: RecordingEventPublisher,
) -> TransactionService:
    return TransactionService(
        repository=TransactionRepository(db_session),
        account_repository=AccountRepository(db_session),
        event_publisher=publisher,
    )


def _create(service: TransactionService, user: User, account: Account, **overrides):
    fields = {
        "user_id": user.id,
        "account_id": account.id,
        "amount": Decimal("70.00"),
        "direction": TransactionDirection.DEBIT,
        "merchant_raw": "SmartQ",
        "reference_number": "REF123",
        "transaction_timestamp": TIMESTAMP,
    }
    fields.update(overrides)
    return service.create_transaction(CreateTransactionCommand(**fields))


def test_create_transaction_persists_and_fingerprints(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    transaction = _create(service, user, account)

    assert transaction.id is not None
    assert transaction.amount == Decimal("70.00")
    assert transaction.direction == "DEBIT"
    assert transaction.status == "ACTIVE"
    assert transaction.transaction_fingerprint is not None
    assert len(transaction.transaction_fingerprint) == 64


def test_create_transaction_raises_transaction_created_event(
    service: TransactionService,
    user: User,
    account: Account,
    publisher: RecordingEventPublisher,
) -> None:
    transaction = _create(service, user, account)

    assert publisher.event_types() == ["TransactionCreated"]
    assert publisher.events[0].payload["entity_id"] == str(transaction.id)


def test_duplicate_transaction_is_rejected(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    first = _create(service, user, account)

    with pytest.raises(DuplicateTransactionError) as excinfo:
        _create(service, user, account)

    assert excinfo.value.existing_transaction_id == str(first.id)


def test_same_details_at_a_different_minute_is_not_a_duplicate(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    _create(service, user, account)

    second = _create(
        service,
        user,
        account,
        transaction_timestamp=TIMESTAMP.replace(minute=31),
    )

    assert second.id is not None


def test_same_details_with_a_different_reference_is_not_a_duplicate(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    _create(service, user, account)

    second = _create(service, user, account, reference_number="REF999")

    assert second.id is not None


def test_transaction_on_another_users_account_is_rejected(
    service: TransactionService,
    other_user: User,
    account: Account,
) -> None:
    with pytest.raises(MissingAccountError):
        service.create_transaction(
            CreateTransactionCommand(
                user_id=other_user.id,
                account_id=account.id,
                amount=Decimal("70.00"),
                direction=TransactionDirection.DEBIT,
            )
        )


def test_transaction_on_unknown_account_is_rejected(
    service: TransactionService,
    user: User,
) -> None:
    with pytest.raises(MissingAccountError):
        service.create_transaction(
            CreateTransactionCommand(
                user_id=user.id,
                account_id=uuid4(),
                amount=Decimal("70.00"),
                direction=TransactionDirection.DEBIT,
            )
        )


def test_transaction_on_archived_account_is_rejected(
    service: TransactionService,
    user: User,
    account: Account,
    db_session: Session,
) -> None:
    account.status = AccountStatus.ARCHIVED.value
    db_session.add(account)
    db_session.commit()

    with pytest.raises(TransactionValidationError):
        _create(service, user, account)


def test_negative_amount_is_rejected(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    with pytest.raises(InvalidAmountError):
        _create(service, user, account, amount=Decimal("-1.00"))


def test_unsupported_direction_is_rejected(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    with pytest.raises(TransactionValidationError):
        _create(service, user, account, direction="SIDEWAYS")


def test_get_transaction_rejects_cross_user_access(
    service: TransactionService,
    user: User,
    other_user: User,
    account: Account,
) -> None:
    transaction = _create(service, user, account)

    with pytest.raises(TransactionNotFoundError):
        service.get_transaction(
            user_id=other_user.id,
            transaction_id=transaction.id,
        )


def test_list_transactions_returns_total_count(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    _create(service, user, account, reference_number="A")
    _create(service, user, account, reference_number="B")

    page = service.list_transactions(ListTransactionsQuery(user_id=user.id, limit=1))

    assert len(page.items) == 1
    assert page.total_records == 2


def test_list_transactions_filters_by_direction(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    _create(service, user, account, reference_number="A")
    _create(
        service,
        user,
        account,
        reference_number="B",
        direction=TransactionDirection.CREDIT,
    )

    page = service.list_transactions(
        ListTransactionsQuery(
            user_id=user.id,
            direction=TransactionDirection.CREDIT,
        )
    )

    assert page.total_records == 1
    assert page.items[0].direction == "CREDIT"


def test_list_transactions_filters_by_date_range(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    _create(service, user, account, reference_number="A")
    _create(
        service,
        user,
        account,
        reference_number="B",
        transaction_timestamp=datetime(2026, 7, 15, 9, 0, 0),
    )

    page = service.list_transactions(
        ListTransactionsQuery(
            user_id=user.id,
            start_date=datetime(2026, 7, 1).date(),
            end_date=datetime(2026, 7, 31).date(),
        )
    )

    assert page.total_records == 1
    assert page.items[0].reference_number == "B"


def test_list_transactions_never_returns_another_users_rows(
    service: TransactionService,
    user: User,
    other_user: User,
    account: Account,
) -> None:
    _create(service, user, account)

    page = service.list_transactions(ListTransactionsQuery(user_id=other_user.id))

    assert page.total_records == 0


def test_update_transaction_changes_description_and_raises_event(
    service: TransactionService,
    user: User,
    account: Account,
    publisher: RecordingEventPublisher,
) -> None:
    transaction = _create(service, user, account)

    updated = service.update_transaction(
        UpdateTransactionCommand(
            user_id=user.id,
            transaction_id=transaction.id,
            description="Lunch with team",
        )
    )

    assert updated.description == "Lunch with team"
    assert publisher.event_types() == ["TransactionCreated", "TransactionUpdated"]
    changes = publisher.events[-1].payload["changes"]
    assert changes["description"] == [None, "Lunch with team"]


def test_update_transaction_changes_business_type(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    transaction = _create(service, user, account)

    updated = service.update_transaction(
        UpdateTransactionCommand(
            user_id=user.id,
            transaction_id=transaction.id,
            business_type=BusinessType.EXPENSE,
        )
    )

    assert updated.business_type == "EXPENSE"


def test_update_without_changes_raises_no_event(
    service: TransactionService,
    user: User,
    account: Account,
    publisher: RecordingEventPublisher,
) -> None:
    transaction = _create(service, user, account)

    service.update_transaction(
        UpdateTransactionCommand(
            user_id=user.id,
            transaction_id=transaction.id,
            business_type=BusinessType.UNKNOWN,
        )
    )

    assert publisher.event_types() == ["TransactionCreated"]


def test_update_does_not_change_the_fingerprint(
    service: TransactionService,
    user: User,
    account: Account,
) -> None:
    """Fingerprint inputs are not editable, so re-ingestion still detects duplicates."""
    transaction = _create(service, user, account)
    original = transaction.transaction_fingerprint

    updated = service.update_transaction(
        UpdateTransactionCommand(
            user_id=user.id,
            transaction_id=transaction.id,
            description="Changed",
        )
    )

    assert updated.transaction_fingerprint == original


def test_update_transaction_rejects_cross_user_access(
    service: TransactionService,
    user: User,
    other_user: User,
    account: Account,
) -> None:
    transaction = _create(service, user, account)

    with pytest.raises(TransactionNotFoundError):
        service.update_transaction(
            UpdateTransactionCommand(
                user_id=other_user.id,
                transaction_id=transaction.id,
                description="Stolen",
            )
        )
