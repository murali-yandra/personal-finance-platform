import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_authentication_middleware_allows_public_health_endpoint(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_authentication_middleware_rejects_protected_api_without_token(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/accounts",
        headers={
            "X-Request-ID": "request-protected-missing",
            "X-Correlation-ID": "correlation-protected-missing",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {
            "code": "INVALID_TOKEN",
            "message": "Invalid authentication token.",
            "request_id": "request-protected-missing",
            "correlation_id": "correlation-protected-missing",
        },
    }


@pytest.mark.asyncio
async def test_authentication_middleware_rejects_protected_api_with_malformed_header(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/accounts",
        headers={"Authorization": "Bearer not-a-jwt extra"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert "not-a-jwt" not in response.text


@pytest.mark.asyncio
async def test_authentication_middleware_uses_segment_aware_api_prefix_matching(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v10/accounts")

    assert response.status_code == 404
