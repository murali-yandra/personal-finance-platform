"""The dashboard page is served, public, and carries no data of its own."""

import pytest
from httpx import AsyncClient

from app.api.dashboard import DASHBOARD_FILE

DASHBOARD_URL = "/dashboard"


@pytest.mark.asyncio
async def test_dashboard_is_served_as_html(client: AsyncClient) -> None:
    response = await client.get(DASHBOARD_URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_dashboard_needs_no_token(client: AsyncClient) -> None:
    """The page sits outside /api/v1, so the middleware lets it through.

    That is intended: the file holds no data, and every figure it renders comes
    from an endpoint that does require a JWT.
    """
    response = await client.get(DASHBOARD_URL)

    assert response.status_code == 200
    assert "Authorization" not in response.request.headers


@pytest.mark.asyncio
async def test_dashboard_ships_no_credentials(client: AsyncClient) -> None:
    """A public page must not embed a secret.

    Only literal secret values are checked. The page legitimately contains the
    word "password" as a form field and JSON key — it collects one from the
    user, it does not carry one.
    """
    body = (await client.get(DASHBOARD_URL)).text.lower()

    for secret in ("pfp_", "x-api-key", "jwt_secret", "bearer ey", "postgresql"):
        assert secret not in body


@pytest.mark.asyncio
async def test_dashboard_calls_the_api_on_its_own_origin(client: AsyncClient) -> None:
    """Same-origin calls are what let CORS stay disabled."""
    body = (await client.get(DASHBOARD_URL)).text

    assert 'const API = "/api/v1"' in body
    assert "http://localhost:8000" not in body


def test_dashboard_file_is_committed() -> None:
    assert DASHBOARD_FILE.is_file()


def test_dashboard_is_hidden_from_the_openapi_schema() -> None:
    """The page is not an API operation and would only clutter /docs."""
    from app.main import app

    assert DASHBOARD_URL not in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_dashboard_clears_the_password_on_sign_out(client: AsyncClient) -> None:
    """Signing out must not leave a password sitting in the form."""
    body = (await client.get(DASHBOARD_URL)).text

    marker = 'function showLogin(message = "") {'
    start = body.index(marker)
    end = body.index("}", start)

    assert '$("password").value = ""' in body[start:end]
