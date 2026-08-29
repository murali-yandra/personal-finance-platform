"""Structured application logging.

Every line is JSON carrying the fields ``10-security_standards.md`` section 11
requires: timestamp, request id, correlation id, user id and module. Sensitive
values are redacted in the formatter rather than at call sites, so a new log
line cannot leak a secret by forgetting to mask it.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.context import current_context
from app.core.masking import MASK, is_sensitive_key, mask_text

# Attributes LogRecord always carries; anything else was added by the caller
# via `extra=` and is worth including in the structured output.
_STANDARD_RECORD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """Format application logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Render one record, redacting sensitive values."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": mask_text(record.getMessage()),
        }

        payload.update(current_context())

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key.startswith("_"):
                continue
            if is_sensitive_key(key):
                payload[key] = MASK
            elif isinstance(value, str):
                payload[key] = mask_text(value)
            else:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = mask_text(self.formatException(record.exc_info))

        return json.dumps(payload, default=str)


def configure_logging(log_level: str) -> None:
    """Configure baseline structured logging for the application."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())
