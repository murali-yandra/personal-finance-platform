"""Scheduled background jobs.

Jobs are plain callables that take a ``Session`` and return a result object.
Nothing here owns a timer: the runner is invoked by cron, by a platform
scheduler, or by the CLI in ``app/scheduler/cli.py``. That keeps the jobs
testable without waiting on wall-clock time, and it means the MVP needs no
extra container (``11-deployment_standards.md`` section 5).
"""

from app.scheduler.jobs import (
    JobResult,
    run_daily_digests,
    run_snapshot_job,
    run_weekly_digests,
)
from app.scheduler.runner import JOBS, run_job

__all__ = [
    "JOBS",
    "JobResult",
    "run_daily_digests",
    "run_job",
    "run_snapshot_job",
    "run_weekly_digests",
]
