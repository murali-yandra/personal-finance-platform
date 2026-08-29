import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"
ENV_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=")


def test_settings_require_runtime_secret_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required runtime settings must not have committed defaults."""
    for env_var in ("DATABASE_URL", "JWT_SECRET", "INGEST_API_KEY"):
        monkeypatch.delenv(env_var, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    missing_fields = {error["loc"][0] for error in exc_info.value.errors()}

    assert "database_url" in missing_fields
    assert "jwt_secret" in missing_fields
    assert "ingest_api_key" in missing_fields


def _documented_env_keys() -> set[str]:
    """Return every environment key assigned in .env.example."""
    matches = (
        ENV_ASSIGNMENT.match(line) for line in ENV_EXAMPLE.read_text().splitlines()
    )
    return {match.group(1) for match in matches if match}


def test_env_example_documents_every_setting() -> None:
    """.env.example must document every field on Settings.

    A field missing here is invisible until it fails at runtime: ingestion
    returns 503 when INGEST_USER_EMAIL is unset, and the local .env was in fact
    missing eight keys that this file already defined.
    """
    documented = _documented_env_keys()
    expected = {name.upper() for name in Settings.model_fields}

    assert not expected - documented


def test_env_example_documents_no_unknown_keys() -> None:
    """Every key in .env.example must map to a Settings field or Compose.

    POSTGRES_* are consumed by docker-compose for the database container, not by
    the application, so they are the only permitted extras.
    """
    compose_only = {"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"}
    known = {name.upper() for name in Settings.model_fields} | compose_only

    assert not _documented_env_keys() - known
