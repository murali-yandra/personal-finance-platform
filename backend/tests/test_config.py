import pytest
from pydantic import ValidationError

from app.config import Settings


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
