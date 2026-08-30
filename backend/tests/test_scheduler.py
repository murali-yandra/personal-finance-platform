"""Scheduled jobs: balance snapshots and digest notifications."""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.domains.accounts.models import Account
from app.domains.balances.models import BalanceSnapshot
from app.domains.transactions.models import Transaction
from app.domains.users.models import User, UserSettings
from app.scheduler.jobs import (
    run_daily_digests,
    run_snapshot_job,
    run_weekly_digests,
)
from app.scheduler.runner import JOBS, UnknownJobError, run_job
from app.shared.enums import (
    AccountStatus,
    AccountType,
    BusinessType,
    NotificationMode,
    TransactionDirection,
)
from app.telegram.client import FakeTelegramClient

SNAPSHOT_DATE = date(2026, 6, 30)


def _user(
    db_session: Session,
    email: str = "owner@example.com",
    mode: NotificationMode = NotificationMode.DAILY_SUMMARY,
    chat_id: str | None = "123456789",
) -> User:
    user = User(
        email=email,
        password_hash="hash",
        display_name="Owner",
        telegram_chat_id=chat_id,
    )
    db_session.add(user)
    db_session.add(UserSettings(user_id=user.id, notification_mode=mode.value))
    db_session.commit()
    return user


def _account(
    db_session: Session,
    user: User,
    balance: str = "1000.00",
    status: AccountStatus = AccountStatus.ACTIVE,
    last_four: str = "0452",
) -> Account:
    account = Account(
        user_id=user.id,
        account_name="Salary",
        account_type=AccountType.BANK.value,
        bank_name="HDFC",
        last_four_digits=last_four,
        estimated_balance=Decimal(balance),
        status=status.value,
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
    when: datetime,
    fingerprint: str,
    business_type: BusinessType = BusinessType.EXPENSE,
) -> None:
    db_session.add(
        Transaction(
            user_id=user.id,
            account_id=account.id,
            amount=Decimal(amount),
            direction=direction.value,
            business_type=business_type.value,
            transaction_timestamp=when,
            transaction_fingerprint=fingerprint,
        )
    )
    db_session.commit()


# --------------------------------------------------------------------- snapshots


def test_snapshot_job_records_every_live_account(db_session: Session) -> None:
    user = _user(db_session)
    _account(db_session, user, "1000.00", last_four="1111")
    _account(db_session, user, "2500.00", last_four="2222")

    result = run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    assert result.processed == 2
    snapshots = list(db_session.exec(select(BalanceSnapshot)).all())
    assert {s.balance for s in snapshots} == {
        Decimal("1000.00"),
        Decimal("2500.00"),
    }


def test_snapshot_job_skips_archived_accounts(db_session: Session) -> None:
    user = _user(db_session)
    _account(db_session, user, "1000.00", status=AccountStatus.ARCHIVED)

    result = run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    assert result.processed == 0
    assert list(db_session.exec(select(BalanceSnapshot)).all()) == []


def test_running_twice_updates_rather_than_duplicating(
    db_session: Session,
) -> None:
    """A scheduler that retries or fires late must not corrupt the series."""
    user = _user(db_session)
    account = _account(db_session, user, "1000.00")
    run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    account.estimated_balance = Decimal("1750.00")
    db_session.add(account)
    db_session.commit()
    run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    snapshots = list(db_session.exec(select(BalanceSnapshot)).all())
    assert len(snapshots) == 1
    assert snapshots[0].balance == Decimal("1750.00")


def test_snapshots_on_different_days_are_separate(db_session: Session) -> None:
    user = _user(db_session)
    _account(db_session, user, "1000.00")

    run_snapshot_job(db_session, snapshot_date=date(2026, 6, 29))
    run_snapshot_job(db_session, snapshot_date=date(2026, 6, 30))

    assert len(list(db_session.exec(select(BalanceSnapshot)).all())) == 2


def test_snapshot_belongs_to_the_owning_user(db_session: Session) -> None:
    user = _user(db_session)
    account = _account(db_session, user)

    run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    snapshot = list(db_session.exec(select(BalanceSnapshot)).all())[0]
    assert snapshot.user_id == user.id
    assert snapshot.account_id == account.id


# ----------------------------------------------------------------------- digests


def test_daily_digest_is_sent_to_subscribers(db_session: Session) -> None:
    user = _user(db_session, mode=NotificationMode.DAILY_SUMMARY)
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "250.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "a",
    )
    client = FakeTelegramClient()

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.processed == 1
    assert len(client.sent) == 1
    assert "Daily summary" in client.messages[0]
    assert "250.00" in client.messages[0]


def test_a_quiet_day_sends_nothing(db_session: Session) -> None:
    """A digest saying nothing happened is how users end up muting the bot."""
    user = _user(db_session, mode=NotificationMode.DAILY_SUMMARY)
    _account(db_session, user)
    client = FakeTelegramClient()

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.processed == 0
    assert result.skipped == 1
    assert client.sent == []


def test_users_on_other_modes_are_not_digested(db_session: Session) -> None:
    user = _user(db_session, mode=NotificationMode.ALWAYS)
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "250.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "a",
    )
    client = FakeTelegramClient()

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.processed == 0
    assert client.sent == []


def test_a_subscriber_without_a_chat_is_skipped(db_session: Session) -> None:
    user = _user(db_session, chat_id=None)
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "250.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "a",
    )
    client = FakeTelegramClient()

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.skipped == 1
    assert client.sent == []


def test_weekly_digest_covers_seven_days(db_session: Session) -> None:
    user = _user(db_session, mode=NotificationMode.WEEKLY_SUMMARY)
    account = _account(db_session, user)
    # Inside the window ending 15 June: 9 June onwards.
    _transaction(
        db_session,
        user,
        account,
        "100.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 10, 12, 0),
        "in",
    )
    # Outside it.
    _transaction(
        db_session,
        user,
        account,
        "999.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 1, 12, 0),
        "out",
    )
    client = FakeTelegramClient()

    result = run_weekly_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.processed == 1
    assert "100.00" in client.messages[0]
    assert "999.00" not in client.messages[0]


def test_digest_excludes_transfers(db_session: Session) -> None:
    """Consistent with every other report: a transfer is not spending."""
    user = _user(db_session, mode=NotificationMode.DAILY_SUMMARY)
    account = _account(db_session, user)
    _transaction(
        db_session,
        user,
        account,
        "5000.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "t",
        business_type=BusinessType.TRANSFER,
    )
    client = FakeTelegramClient()

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.processed == 0
    assert client.sent == []


def test_one_delivery_failure_does_not_abort_the_run(
    db_session: Session,
) -> None:
    """A messaging outage must not stop every other user's digest."""
    for index in range(2):
        user = _user(
            db_session,
            email=f"user{index}@example.com",
            chat_id=f"10{index}",
        )
        account = _account(db_session, user, last_four=f"111{index}")
        _transaction(
            db_session,
            user,
            account,
            "250.00",
            TransactionDirection.DEBIT,
            datetime(2026, 6, 15, 12, 0),
            f"f{index}",
        )

    client = FakeTelegramClient(should_fail=True)

    result = run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    assert result.failed == 2
    assert result.processed == 0


def test_a_users_digest_never_includes_another_users_money(
    db_session: Session,
) -> None:
    first = _user(db_session, email="first@example.com", chat_id="111")
    account = _account(db_session, first)
    _transaction(
        db_session,
        first,
        account,
        "250.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "a",
    )

    second = _user(db_session, email="second@example.com", chat_id="222")
    other_account = _account(db_session, second, "9999.00", last_four="8888")
    _transaction(
        db_session,
        second,
        other_account,
        "7777.00",
        TransactionDirection.DEBIT,
        datetime(2026, 6, 15, 12, 0),
        "b",
    )

    client = FakeTelegramClient()
    run_daily_digests(db_session, client, on_date=date(2026, 6, 15))

    by_chat = dict(client.sent)
    assert "250.00" in by_chat["111"]
    assert "7777.00" not in by_chat["111"]


# ------------------------------------------------------------------------ runner


def test_every_job_is_registered() -> None:
    assert set(JOBS) == {"balance-snapshots", "daily-digest", "weekly-digest"}


def test_an_unknown_job_fails_loudly(db_session: Session) -> None:
    """Silently doing nothing is how a nightly job goes unnoticed for weeks."""
    with pytest.raises(UnknownJobError):
        run_job("no-such-job", session=db_session)


def test_runner_executes_a_job_with_a_supplied_session(
    db_session: Session,
) -> None:
    user = _user(db_session)
    _account(db_session, user)

    result = run_job(
        "balance-snapshots",
        on_date=SNAPSHOT_DATE,
        session=db_session,
    )

    assert result.processed == 1


def test_job_result_summarises_itself(db_session: Session) -> None:
    user = _user(db_session)
    _account(db_session, user)

    result = run_snapshot_job(db_session, snapshot_date=SNAPSHOT_DATE)

    assert "processed=1" in result.summary()
