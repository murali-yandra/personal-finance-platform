import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy_status(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_api_v1_health_endpoint_returns_healthy_status(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_readiness_endpoint_reports_connected_database(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_endpoint_does_not_require_authentication(
    auth_client: AsyncClient,
) -> None:
    """Hosting platforms poll readiness without credentials."""
    response = await auth_client.get("/api/v1/health/ready")

    assert response.status_code == 200
