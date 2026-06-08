import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://placeholder_user:placeholder_password"
    "@localhost:5432/placeholder_db?connect_timeout=1",
)
os.environ.setdefault("JWT_SECRET", "placeholder-test-jwt-secret-32-bytes")
os.environ.setdefault("INGEST_API_KEY", "placeholder-test-ingest-api-key")

from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Return an ASGI-backed HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client
