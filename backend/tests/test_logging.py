import json
import logging

from app.core.logging import configure_logging


def test_configure_logging_emits_structured_json(capsys) -> None:
    """Baseline logging should emit parseable structured JSON records."""
    configure_logging("INFO")

    logger = logging.getLogger("finance_tracker.test")
    logger.info("startup logging ready")

    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "finance_tracker.test"
    assert payload["message"] == "startup logging ready"
    assert "timestamp" in payload
