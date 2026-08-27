import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session

from app.config import get_settings
from app.db.session import get_session

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str


class ReadinessResponse(BaseModel):
    """Readiness endpoint response."""

    status: str
    database: str
    version: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the application health status.

    Intentionally free of dependencies so a hosting platform's liveness probe
    stays green while a backing service is briefly unavailable.
    """
    return HealthResponse(status="healthy")


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness_check(
    session: Annotated[Session, Depends(get_session)],
) -> ReadinessResponse:
    """Return readiness including database connectivity."""
    settings = get_settings()
    try:
        session.exec(text("SELECT 1"))
        database_status = "connected"
        status = "ready"
    except Exception as exc:  # pragma: no cover - exercised via integration tests
        logger.warning("Readiness database check failed: %s", exc)
        database_status = "unavailable"
        status = "degraded"

    return ReadinessResponse(
        status=status,
        database=database_status,
        version=settings.app_version,
    )
