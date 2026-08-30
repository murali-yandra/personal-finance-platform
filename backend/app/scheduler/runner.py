"""Job dispatch.

A single entry point so cron, a platform scheduler and the CLI all invoke jobs
the same way, and so an unknown job name fails loudly rather than silently
doing nothing.
"""

import logging
from collections.abc import Callable
from datetime import date

from sqlmodel import Session

from app.config import get_settings
from app.db.session import engine
from app.scheduler.jobs import (
    JobResult,
    run_daily_digests,
    run_snapshot_job,
    run_weekly_digests,
)
from app.telegram.factory import build_telegram_client

logger = logging.getLogger(__name__)

JobFn = Callable[[Session, date | None], JobResult]


def _snapshot(session: Session, on_date: date | None) -> JobResult:
    return run_snapshot_job(session, snapshot_date=on_date)


def _daily_digest(session: Session, on_date: date | None) -> JobResult:
    return run_daily_digests(
        session,
        client=build_telegram_client(get_settings()),
        on_date=on_date,
    )


def _weekly_digest(session: Session, on_date: date | None) -> JobResult:
    return run_weekly_digests(
        session,
        client=build_telegram_client(get_settings()),
        on_date=on_date,
    )


JOBS: dict[str, JobFn] = {
    "balance-snapshots": _snapshot,
    "daily-digest": _daily_digest,
    "weekly-digest": _weekly_digest,
}


class UnknownJobError(ValueError):
    """Raised when a job name is not registered."""


def run_job(
    name: str,
    on_date: date | None = None,
    session: Session | None = None,
) -> JobResult:
    """Run one named job and return its result.

    A caller-supplied session is used as-is, which is what lets tests drive a
    job without touching the configured database.
    """
    job = JOBS.get(name)
    if job is None:
        raise UnknownJobError(
            f"Unknown job {name!r}. Known jobs: {', '.join(sorted(JOBS))}."
        )

    if session is not None:
        result = job(session, on_date)
        logger.info("%s", result.summary())
        return result

    with Session(engine) as owned_session:
        result = job(owned_session, on_date)
        logger.info("%s", result.summary())
        return result
