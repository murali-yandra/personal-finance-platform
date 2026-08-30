"""Command-line entry point for scheduled jobs.

Run from cron or a platform scheduler:

    python -m app.scheduler.cli balance-snapshots
    python -m app.scheduler.cli daily-digest
    python -m app.scheduler.cli weekly-digest --date 2026-06-15

Exits non-zero when a job reports failures, so a scheduler surfaces the problem
instead of a job silently failing every night.
"""

import argparse
import sys
from datetime import date

from app.config import get_settings
from app.core.logging import configure_logging
from app.scheduler.runner import JOBS, UnknownJobError, run_job


def main(argv: list[str] | None = None) -> int:
    """Run one job and return the process exit code."""
    parser = argparse.ArgumentParser(description="Run a scheduled job.")
    parser.add_argument("job", choices=sorted(JOBS), help="job to run")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        help="date to run for (YYYY-MM-DD); defaults per job",
    )
    args = parser.parse_args(argv)

    configure_logging(get_settings().log_level)

    try:
        result = run_job(args.job, on_date=args.date)
    except UnknownJobError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(result.summary())
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
