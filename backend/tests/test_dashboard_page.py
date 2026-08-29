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


@pytest.mark.asyncio
async def test_dashboard_offers_account_creation(client: AsyncClient) -> None:
    """A new user must be able to start without Swagger UI or a terminal."""
    body = (await client.get(DASHBOARD_URL)).text

    assert "Create an account" in body
    assert '"/auth/register"' in body


@pytest.mark.asyncio
async def test_sign_up_collects_a_display_name(client: AsyncClient) -> None:
    """display_name is required by the register endpoint, so the form asks for it."""
    body = (await client.get(DASHBOARD_URL)).text

    assert 'id="display-name"' in body
    assert "display_name" in body


@pytest.mark.asyncio
async def test_sign_up_states_the_password_policy(client: AsyncClient) -> None:
    """The rules are enforced server-side; showing them avoids a guessing game."""
    body = (await client.get(DASHBOARD_URL)).text

    assert "uppercase letter" in body
    assert "number" in body


@pytest.mark.asyncio
async def test_expired_session_returns_to_sign_in(client: AsyncClient) -> None:
    """showLogin must reset the form, not leave a half-filled sign-up."""
    body = (await client.get(DASHBOARD_URL)).text

    start = body.index('function showLogin(message = "") {')
    end = body.index("\n}", start)

    assert "setMode(false)" in body[start:end]


@pytest.mark.asyncio
async def test_hidden_elements_are_actually_hidden(client: AsyncClient) -> None:
    """Author styles beat the user-agent default for [hidden].

    Regression: `label { display: block }` overrode the browser's built-in
    `[hidden] { display: none }`, so the sign-up-only fields rendered on the
    sign-in form.
    """
    body = (await client.get(DASHBOARD_URL)).text

    assert "[hidden] { display: none !important; }" in body
