"""Balance engine and reporting (Sprints 9 and 10)."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.balances.repository import BalanceRepository
from app.domains.balances.service import BalanceService
from app.domains.categories.models import Category
from app.domains.reporting.repository import ReportingRepository
from app.domains.reporting.service import ReportingService, ReportValidationError
from app.domains.transactions.models import Transaction
from app.domains.transactions.repository import TransactionRepository
from app.domains.transactions.schemas import CreateTransactionCommand
from app.domains.transactions.service import TransactionService
from app.domains.transfers.service import (
    InvalidTransferError,
    TransferService,
    TransferUserMismatchError,
)
from app.domains.users.models import User, UserSettings
from app.shared.enums import (
    AccountStatus,
    AccountType,
    BusinessType,
    TransactionDirection,
)

JUNE = datetime(2026, 6, 15, 12, 0, 0)


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
        email="other@example.com",
        password_hash="hash",
        display_name="Other",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


def _account(
    db_session: Session,
    user: User,
    account_type: AccountType = AccountType.BANK,
    balance: Decimal = Decimal("0.00"),
    name: str = "Salary",
    last_four: str = "0452",
) -> Account:
    account = Account(
        user_id=user.id,
        account_name=name,
        account_type=account_type.value,
        bank_name="HDFC",
        last_four_digits=last_four,
        estimated_balance=balance,
        status=AccountStatus.ACTIVE.value,
    )
    db_session.add(account)
    db_session.commit()
    return account


def _transaction(
    db_session: Session,
    user: User,
    account: Account,
    amount: str,
    direction: TransactionDirection,
    business_type: BusinessType = BusinessType.EXPENSE,
    when: datetime = JUNE,
    category_id=None,
    fingerprint: str | None = None,
) -> Transaction:
    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal(amount),
        direction=direction.value,
        business_type=business_type.value,
        transaction_timestamp=when,
        category_id=category_id,
        transaction_fingerprint=fingerprint,
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction


# --------------------------------------------------------------- balance engine


def test_bank_debit_lowers_the_balance(db_session: Session, user: User) -> None:
    account = _account(db_session, user, balance=Decimal("1000.00"))
    transaction = _transaction(
        db_session, user, account, "250.00", TransactionDirection.DEBIT
    )

    service = BalanceService(db_session, AccountRepository(db_session))
    service.apply_transaction(transaction)
    db_session.commit()

    db_session.refresh(account)
    assert account.estimated_balance == Decimal("750.00")


def test_bank_credit_raises_the_balance(db_session: Session, user: User) -> None:
    account = _account(db_session, user, balance=Decimal("1000.00"))
    transaction = _transaction(
        db_session, user, account, "500.00", TransactionDirection.CREDIT
    )

    BalanceService(db_session, AccountRepository(db_session)).apply_transaction(
        transaction
    )
    db_session.commit()

    db_session.refresh(account)
    assert account.estimated_balance == Decimal("1500.00")


def test_credit_card_spend_increases_what_is_owed(
    db_session: Session,
    user: User,
) -> None:
    """Liability balances invert: spending raises the outstanding amount."""
    card = _account(
        db_session,
        user,
        account_type=AccountType.CREDIT_CARD,
        balance=Decimal("2000.00"),
        name="Card",
        last_four="9012",
    )
    transaction = _transaction(
        db_session, user, card, "500.00", TransactionDirection.DEBIT
    )

    BalanceService(db_session, AccountRepository(db_session)).apply_transaction(
        transaction
    )
    db_session.commit()

    db_session.refresh(card)
    assert card.estimated_balance == Decimal("2500.00")


def test_credit_card_payment_reduces_what_is_owed(
    db_session: Session,
    user: User,
) -> None:
    card = _account(
        db_session,
        user,
        account_type=AccountType.CREDIT_CARD,
        balance=Decimal("2000.00"),
        name="Card",
        last_four="9012",
    )
    transaction = _transaction(
        db_session, user, card, "800.00", TransactionDirection.CREDIT
    )

    BalanceService(db_session, AccountRepository(db_session)).apply_transaction(
        transaction
    )
    db_session.commit()

    db_session.refresh(card)
    assert card.estimated_balance == Decimal("1200.00")


def test_balance_updates_when_a_transaction_is_created(
    db_session: Session,
    user: User,
) -> None:
    """The balance subscriber shares the transaction's session and commit."""
    account = _account(db_session, user, balance=Decimal("1000.00"))
    balance_service = BalanceService(db_session, AccountRepository(db_session))
    service = TransactionService(
        repository=TransactionRepository(db_session),
        account_repository=AccountRepository(db_session),
        event_publisher=balance_service,
    )

    service.create_transaction(
        CreateTransactionCommand(
            user_id=user.id,
            account_id=account.id,
            amount=Decimal("70.00"),
            direction=TransactionDirection.DEBIT,
            transaction_timestamp=JUNE,
        )
    )

    db_session.refresh(account)
    assert account.estimated_balance == Decimal("930.00")


def test_a_transfer_still_moves_the_balance(
    db_session: Session,
    user: User,
) -> None:
    """Transfers are excluded from reporting, not from balances."""
    account = _account(db_session, user, balance=Decimal("1000.00"))
    transaction = _transaction(
        db_session,
        user,
        account,
        "300.00",
        TransactionDirection.DEBIT,
        business_type=BusinessType.TRANSFER,
    )

    BalanceService(db_session, AccountRepository(db_session)).apply_transaction(
        transaction
    )
    db_session.commit()

    db_session.refresh(account)
    assert account.estimated_balance == Decimal("700.00")


def test_reconcile_absorbs_the_drift(db_session: Session, user: User) -> None:
    account = _account(db_session, user, balance=Decimal("24800.00"))
    service = BalanceService(db_session, AccountRepository(db_session))

    updated, previous, difference = service.reconcile(
        user_id=user.id,
        account_id=account.id,
        actual_balance=Decimal("25000.00"),
    )
    db_session.commit()

    assert previous == Decimal("24800.00")
    assert difference == Decimal("200.00")
    assert updated.estimated_balance == Decimal("25000.00")


def test_reconcile_rejects_another_users_account(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    from app.domains.accounts.exceptions import AccountNotFoundError

    account = _account(db_session, user)
    service = BalanceService(db_session, AccountRepository(db_session))

    with pytest.raises(AccountNotFoundError):
        service.reconcile(
            user_id=other_user.id,
            account_id=account.id,
            actual_balance=Decimal("1.00"),
        )


def test_snapshots_are_idempotent_per_day(db_session: Session, user: User) -> None:
    """A re-run of the snapshot job must update, not duplicate."""
    account = _account(db_session, user, balance=Decimal("1000.00"))
    repository = BalanceRepository(db_session)
    service = BalanceService(db_session, AccountRepository(db_session), repository)

    service.capture_snapshot(user.id, account, date(2026, 6, 30))
    account.estimated_balance = Decimal("1500.00")
    service.capture_snapshot(user.id, account, date(2026, 6, 30))
    db_session.commit()

    snapshots = repository.list_for_account(user.id, account.id)
    assert len(snapshots) == 1
    assert snapshots[0].balance == Decimal("1500.00")


# -------------------------------------------------------------------- reporting


@pytest.fixture
def reporting(db_session: Session) -> ReportingService:
    return ReportingService(repository=ReportingRepository(db_session))


def test_monthly_summary_totals(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "80000.00",
        TransactionDirection.CREDIT,
        BusinessType.INCOME,
        fingerprint="a",
    )
    _transaction(
        db_session,
        user,
        account,
        "35000.00",
        TransactionDirection.DEBIT,
        fingerprint="b",
    )

    summary = reporting.monthly_summary(user.id, 2026, 6)

    assert summary.income == Decimal("80000.00")
    assert summary.expenses == Decimal("35000.00")
    assert summary.savings == Decimal("45000.00")
    assert summary.transaction_count == 2


def test_transfers_are_excluded_from_income_and_expenses(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    """Money moved between your own accounts is not spending."""
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "5000.00",
        TransactionDirection.DEBIT,
        BusinessType.TRANSFER,
        fingerprint="t",
    )

    summary = reporting.monthly_summary(user.id, 2026, 6)

    assert summary.expenses == Decimal("0.00")
    assert summary.transaction_count == 0


def test_summary_excludes_other_months(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "100.00",
        TransactionDirection.DEBIT,
        when=datetime(2026, 7, 1, 9, 0),
        fingerprint="july",
    )

    assert reporting.monthly_summary(user.id, 2026, 6).expenses == Decimal("0.00")


def test_summary_includes_the_last_day_of_the_month(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    """A month-end transaction must not fall outside its own month."""
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "100.00",
        TransactionDirection.DEBIT,
        when=datetime(2026, 6, 30, 23, 59, 59),
        fingerprint="last",
    )

    assert reporting.monthly_summary(user.id, 2026, 6).expenses == Decimal("100.00")


def test_summary_never_includes_another_users_transactions(
    db_session: Session,
    user: User,
    other_user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    _transaction(db_session, user, account, "500.00", TransactionDirection.DEBIT)

    assert reporting.monthly_summary(other_user.id, 2026, 6).expenses == Decimal("0.00")


def test_invalid_month_is_rejected(reporting: ReportingService, user: User) -> None:
    with pytest.raises(ReportValidationError):
        reporting.monthly_summary(user.id, 2026, 13)


def test_category_breakdown_is_largest_first(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    food = Category(user_id=None, name="Food", is_system=True)
    transport = Category(user_id=None, name="Transport", is_system=True)
    db_session.add(food)
    db_session.add(transport)
    db_session.commit()

    _transaction(
        db_session,
        user,
        account,
        "500.00",
        TransactionDirection.DEBIT,
        category_id=transport.id,
        fingerprint="t1",
    )
    _transaction(
        db_session,
        user,
        account,
        "2000.00",
        TransactionDirection.DEBIT,
        category_id=food.id,
        fingerprint="t2",
    )

    rows = reporting.category_breakdown(user.id, date(2026, 6, 1), date(2026, 6, 30))

    assert [row.category for row in rows] == ["Food", "Transport"]
    assert rows[0].amount == Decimal("2000.00")


def test_uncategorized_spend_is_labelled(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    _transaction(db_session, user, account, "300.00", TransactionDirection.DEBIT)

    rows = reporting.category_breakdown(user.id, date(2026, 6, 1), date(2026, 6, 30))

    assert rows[0].category == "Uncategorized"


def test_reversed_date_range_is_rejected(
    reporting: ReportingService,
    user: User,
) -> None:
    with pytest.raises(ReportValidationError):
        reporting.category_breakdown(user.id, date(2026, 6, 30), date(2026, 6, 1))


def test_income_vs_expense_is_grouped_by_month(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "1000.00",
        TransactionDirection.DEBIT,
        when=datetime(2026, 6, 5, 10, 0),
        fingerprint="j1",
    )
    _transaction(
        db_session,
        user,
        account,
        "2000.00",
        TransactionDirection.DEBIT,
        when=datetime(2026, 7, 5, 10, 0),
        fingerprint="j2",
    )

    rows = reporting.income_vs_expense(user.id, date(2026, 6, 1), date(2026, 7, 31))

    assert [(row.month, row.expenses) for row in rows] == [
        (6, Decimal("1000.00")),
        (7, Decimal("2000.00")),
    ]


def test_net_worth_subtracts_liabilities(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    """Liability balances are stored as a positive amount owed."""
    _account(db_session, user, balance=Decimal("500000.00"))
    _account(
        db_session,
        user,
        account_type=AccountType.CREDIT_CARD,
        balance=Decimal("100000.00"),
        name="Card",
        last_four="9012",
    )

    result = reporting.net_worth(user.id)

    assert result.assets == Decimal("500000.00")
    assert result.liabilities == Decimal("100000.00")
    assert result.net_worth == Decimal("400000.00")


def test_net_worth_excludes_archived_accounts(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user, balance=Decimal("1000.00"))
    account.status = AccountStatus.ARCHIVED.value
    db_session.add(account)
    db_session.commit()

    assert reporting.net_worth(user.id).assets == Decimal("0.00")


def test_account_summary_counts_transactions(
    db_session: Session,
    user: User,
    reporting: ReportingService,
) -> None:
    account = _account(db_session, user, balance=Decimal("1000.00"))
    _transaction(db_session, user, account, "10.00", TransactionDirection.DEBIT)

    rows = reporting.account_summary(user.id)

    assert len(rows) == 1
    assert rows[0].transaction_count == 1
    assert rows[0].estimated_balance == Decimal("1000.00")


# -------------------------------------------------------------------- transfers


def test_transfer_links_two_transactions(db_session: Session, user: User) -> None:
    source = _account(db_session, user)
    destination = _account(db_session, user, name="Card", last_four="9012")
    outgoing = _transaction(
        db_session, user, source, "5000.00", TransactionDirection.DEBIT, fingerprint="s"
    )
    incoming = _transaction(
        db_session,
        user,
        destination,
        "5000.00",
        TransactionDirection.CREDIT,
        fingerprint="d",
    )

    transfer = TransferService(db_session).link_transfer(
        user_id=user.id,
        source_transaction_id=outgoing.id,
        destination_transaction_id=incoming.id,
    )

    assert transfer.source_transaction_id == outgoing.id
    assert transfer.destination_transaction_id == incoming.id


def test_transfer_rejects_the_same_transaction_on_both_sides(
    db_session: Session,
    user: User,
) -> None:
    account = _account(db_session, user)
    transaction = _transaction(
        db_session, user, account, "100.00", TransactionDirection.DEBIT
    )

    with pytest.raises(InvalidTransferError):
        TransferService(db_session).link_transfer(
            user_id=user.id,
            source_transaction_id=transaction.id,
            destination_transaction_id=transaction.id,
        )


def test_transfer_rejects_two_sides_on_one_account(
    db_session: Session,
    user: User,
) -> None:
    account = _account(db_session, user)
    first = _transaction(
        db_session, user, account, "100.00", TransactionDirection.DEBIT, fingerprint="a"
    )
    second = _transaction(
        db_session,
        user,
        account,
        "100.00",
        TransactionDirection.CREDIT,
        fingerprint="b",
    )

    with pytest.raises(InvalidTransferError):
        TransferService(db_session).link_transfer(
            user_id=user.id,
            source_transaction_id=first.id,
            destination_transaction_id=second.id,
        )


def test_transfer_rejects_crossing_users(
    db_session: Session,
    user: User,
    other_user: User,
) -> None:
    """Linking across users would let one account be moved by another's activity."""
    account = _account(db_session, user)
    transaction = _transaction(
        db_session, user, account, "100.00", TransactionDirection.DEBIT
    )

    with pytest.raises(TransferUserMismatchError):
        TransferService(db_session).link_transfer(
            user_id=other_user.id,
            source_transaction_id=transaction.id,
        )


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_reports_require_authentication(auth_client: AsyncClient) -> None:
    response = await auth_client.get(
        "/api/v1/reports/monthly-summary",
        params={"year": 2026, "month": 6},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_monthly_summary_endpoint(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get(
        "/api/v1/reports/monthly-summary",
        params={"year": 2026, "month": 6},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["income"] == "0.00"
    assert data["savings"] == "0.00"


@pytest.mark.asyncio
async def test_net_worth_endpoint(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    await auth_client.post(
        "/api/v1/accounts",
        json={
            "account_type": "BANK",
            "account_name": "Salary",
            "opening_balance": "5000.00",
        },
        headers=headers,
    )

    response = await auth_client.get("/api/v1/reports/net-worth", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["assets"] == "5000.00"
    assert data["net_worth"] == "5000.00"


@pytest.mark.asyncio
async def test_reconcile_endpoint_reports_the_difference(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    created = await auth_client.post(
        "/api/v1/accounts",
        json={
            "account_type": "BANK",
            "account_name": "Salary",
            "opening_balance": "24800.00",
        },
        headers=headers,
    )
    account_id = created.json()["data"]["id"]

    response = await auth_client.post(
        f"/api/v1/accounts/{account_id}/reconcile",
        json={"actual_balance": "25000.00"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["estimated_balance"] == "24800.00"
    assert data["actual_balance"] == "25000.00"
    assert data["difference"] == "200.00"


@pytest.mark.asyncio
async def test_reconciliation_is_audited(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    created = await auth_client.post(
        "/api/v1/accounts",
        json={"account_type": "BANK", "opening_balance": "100.00"},
        headers=headers,
    )
    account_id = created.json()["data"]["id"]
    await auth_client.post(
        f"/api/v1/accounts/{account_id}/reconcile",
        json={"actual_balance": "150.00"},
        headers=headers,
    )

    audit = await auth_client.get(
        "/api/v1/audit",
        params={"entity_type": "account"},
        headers=headers,
    )

    actions = [entry["action"] for entry in audit.json()["data"]]
    assert "BALANCE_RECONCILIATION" in actions


@pytest.mark.asyncio
async def test_transfers_endpoint_lists_nothing_initially(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get("/api/v1/transfers", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"] == []
