from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the application health status."""
    return HealthResponse(status="healthy")
