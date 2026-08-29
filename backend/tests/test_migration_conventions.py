"""Conventions every migration must follow.

These are cheap checks for mistakes that only surface against a real database,
where they break a deployment rather than a test run.
"""

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "versions"

# Alembic's alembic_version.version_num column is VARCHAR(32). A longer
# revision id inserts fine on SQLite but fails on PostgreSQL with
# StringDataRightTruncation, part-way through the upgrade.
MAX_REVISION_ID_LENGTH = 32

REVISION_PATTERN = re.compile(r'^revision: str = "([^"]+)"', re.MULTILINE)
DOWN_REVISION_PATTERN = re.compile(
    r"^down_revision: str \| None = (?:\"([^\"]+)\"|None)",
    re.MULTILINE,
)


def _migration_files() -> list[Path]:
    return sorted(path for path in MIGRATIONS_DIR.glob("[0-9]*.py"))


def _revision_of(path: Path) -> str:
    match = REVISION_PATTERN.search(path.read_text())
    assert match, f"{path.name} declares no revision id"
    return match.group(1)


def test_migrations_exist() -> None:
    assert _migration_files()


@pytest.mark.parametrize(
    "path",
    _migration_files(),
    ids=[path.stem for path in _migration_files()],
)
def test_revision_id_fits_the_alembic_version_column(path: Path) -> None:
    revision = _revision_of(path)

    assert len(revision) <= MAX_REVISION_ID_LENGTH, (
        f"Revision id {revision!r} is {len(revision)} characters; "
        f"alembic_version.version_num holds only {MAX_REVISION_ID_LENGTH}."
    )


@pytest.mark.parametrize(
    "path",
    _migration_files(),
    ids=[path.stem for path in _migration_files()],
)
def test_migration_defines_a_downgrade(path: Path) -> None:
    """Migrations must be reversible so a bad deploy can be rolled back."""
    source = path.read_text()

    assert "def downgrade() -> None:" in source
    body = source.split("def downgrade() -> None:", 1)[1]
    assert "op." in body, f"{path.name} has an empty downgrade"


def test_revision_ids_are_unique() -> None:
    revisions = [_revision_of(path) for path in _migration_files()]

    assert len(revisions) == len(set(revisions))


def test_migrations_form_a_single_chain() -> None:
    """Exactly one root and no branches, or `alembic upgrade head` is ambiguous."""
    files = _migration_files()
    revisions = {_revision_of(path) for path in files}

    downs: list[str | None] = []
    for path in files:
        match = DOWN_REVISION_PATTERN.search(path.read_text())
        assert match, f"{path.name} declares no down_revision"
        downs.append(match.group(1))

    assert downs.count(None) == 1, "there must be exactly one root migration"

    parents = [down for down in downs if down is not None]
    assert len(parents) == len(set(parents)), "a migration is branched"
    assert set(parents) <= revisions, "a down_revision points at a missing migration"
