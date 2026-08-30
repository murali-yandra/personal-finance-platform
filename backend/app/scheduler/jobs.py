"""Scheduled jobs.

Each job is a function over a ``Session``. They are written to be safe to run
twice: a scheduler that fires late, retries, or overlaps must not corrupt data
or spam a user.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.balances.repository import BalanceRepository
from app.domains.balances.service import BalanceService
from app.domains.reporting.repository import ReportingRepository
from app.domains.reporting.service import ReportingService
from app.domains.users.models import User, UserSettings
from app.shared.enums import AccountStatus, NotificationMode
from app.telegram.client import TelegramClient
from app.telegram.formatter import format_amount

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """What a job did."""

    name: str
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    details: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Return a one-line summary for logs and the CLI."""
        return (
            f"{self.name}: processed={self.processed} "
            f"skipped={self.skipped} failed={self.failed}"
        )


def run_snapshot_job(
    session: Session,
    snapshot_date: date | None = None,
) -> JobResult:
    """Record today's balance for every live account.

    Snapshots are what let a balance trend be drawn without replaying every
    transaction. The write is an upsert keyed on account and date, so running
    the job twice in a day updates rather than duplicating, and a scheduler
    that retries is harmless.
    """
    target_date = snapshot_date or datetime.now(UTC).date()
    result = JobResult(name="balance-snapshots")

    balance_service = BalanceService(
        session=session,
        account_repository=AccountRepository(session),
        balance_repository=BalanceRepository(session),
    )

    accounts = session.exec(
        select(Account).where(Account.status != AccountStatus.ARCHIVED.value)
    ).all()

    for account in accounts:
        try:
            balance_service.capture_snapshot(
                user_id=account.user_id,
                account=account,
                snapshot_date=target_date,
            )
            result.processed += 1
        except Exception:
            logger.exception("Snapshot failed for account %s", account.id)
            result.failed += 1

    session.commit()
    return result


def run_daily_digests(
    session: Session,
    client: TelegramClient,
    on_date: date | None = None,
) -> JobResult:
    """Send a one-day summary to users who asked for a daily digest."""
    target = on_date or (datetime.now(UTC).date() - timedelta(days=1))
    return _run_digests(
        session=session,
        client=client,
        mode=NotificationMode.DAILY_SUMMARY,
        start_date=target,
        end_date=target,
        title=f"Daily summary for {target:%d %b %Y}",
        job_name="daily-digest",
    )


def run_weekly_digests(
    session: Session,
    client: TelegramClient,
    on_date: date | None = None,
) -> JobResult:
    """Send a seven-day summary to users who asked for a weekly digest."""
    end = on_date or (datetime.now(UTC).date() - timedelta(days=1))
    start = end - timedelta(days=6)
    return _run_digests(
        session=session,
        client=client,
        mode=NotificationMode.WEEKLY_SUMMARY,
        start_date=start,
        end_date=end,
        title=f"Weekly summary, {start:%d %b} to {end:%d %b %Y}",
        job_name="weekly-digest",
    )


def _run_digests(
    session: Session,
    client: TelegramClient,
    mode: NotificationMode,
    start_date: date,
    end_date: date,
    title: str,
    job_name: str,
) -> JobResult:
    """Send a digest to every user on the given notification mode."""
    result = JobResult(name=job_name)
    reporting = ReportingService(repository=ReportingRepository(session))

    for user, _ in _users_with_mode(session, mode):
        if not user.telegram_chat_id:
            # Opted into a digest but never linked a chat; nothing to send to.
            result.skipped += 1
            continue

        try:
            income, expenses, count = ReportingRepository(session).income_and_expenses(
                user_id=user.id,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            logger.exception("Digest query failed for user %s", user.id)
            result.failed += 1
            continue

        if count == 0:
            # A digest saying nothing happened is noise, and sending it every
            # day is how users end up muting the bot entirely.
            result.skipped += 1
            continue

        message = _format_digest(
            title=title,
            income=income,
            expenses=expenses,
            count=count,
            accounts=reporting.account_summary(user.id),
        )

        try:
            if client.send_message(user.telegram_chat_id, message):
                result.processed += 1
            else:
                result.failed += 1
        except Exception:
            # A messaging outage must not abort the run for everyone else.
            logger.exception("Digest delivery failed for user %s", user.id)
            result.failed += 1

    return result


def _users_with_mode(
    session: Session,
    mode: NotificationMode,
) -> list[tuple[User, UserSettings]]:
    rows = session.exec(
        select(User, UserSettings)
        .join(UserSettings, UserSettings.user_id == User.id)
        .where(
            UserSettings.notification_mode == mode.value,
            User.is_active,
            User.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    ).all()
    return list(rows)


def _format_digest(
    title: str,
    income: Decimal,
    expenses: Decimal,
    count: int,
    accounts: list,
) -> str:
    lines = [
        f"<b>{title}</b>",
        "",
        f"Income: {format_amount(income)}",
        f"Expenses: {format_amount(expenses)}",
        f"Net: {format_amount(income - expenses)}",
        f"Transactions: {count}",
    ]

    if accounts:
        lines.append("")
        lines.append("<b>Balances</b>")
        for account in accounts[:10]:
            lines.append(
                f"• {account.account_name}: "
                f"{format_amount(account.estimated_balance, account.currency)}"
            )
    return "\n".join(lines)
