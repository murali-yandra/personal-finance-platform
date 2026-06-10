from collections.abc import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JwtService,
    TokenType,
    get_jwt_service,
)
from app.db.session import get_session
from app.domains.users.models import User
from app.main import app

JWT_SECRET = "placeholder-test-jwt-secret-32-bytes"


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def override_session(test_engine) -> Generator[None, None, None]:
    def get_test_session() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_jwt_service] = lambda: JwtService(JWT_SECRET)
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(override_session: None) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


async def _register_user(
    client: AsyncClient,
    email: str = "murali@example.com",
    password: str = "SecurePass1",
    display_name: str = "Murali Yandra",
) -> UUID:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert response.status_code == 201
    return UUID(response.json()["data"]["user_id"])


@pytest.mark.asyncio
async def test_login_endpoint_returns_access_and_refresh_tokens(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "MURALI@example.com",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    jwt_service = JwtService(JWT_SECRET)
    access_claims = jwt_service.decode_token(
        data["access_token"],
        expected_token_type=TokenType.ACCESS,
    )
    refresh_claims = jwt_service.decode_token(
        data["refresh_token"],
        expected_token_type=TokenType.REFRESH,
    )

    assert access_claims["user_id"] == str(user_id)
    assert access_claims["email"] == "murali@example.com"
    assert refresh_claims["user_id"] == str(user_id)
    assert refresh_claims["email"] == "murali@example.com"


@pytest.mark.asyncio
async def test_login_endpoint_rejects_unknown_email(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "SecurePass1",
        },
        headers={
            "X-Request-ID": "request-login-unknown",
            "X-Correlation-ID": "correlation-login-unknown",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password.",
            "request_id": "request-login-unknown",
            "correlation_id": "correlation-login-unknown",
        },
    }


@pytest.mark.asyncio
async def test_login_endpoint_rejects_wrong_password(
    auth_client: AsyncClient,
) -> None:
    await _register_user(auth_client)

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "murali@example.com",
            "password": "WrongPass1",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "WrongPass1" not in response.text


@pytest.mark.asyncio
async def test_login_endpoint_rejects_disabled_account(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    user_id = await _register_user(auth_client, email="disabled@example.com")
    with Session(test_engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        user.is_active = False
        session.add(user)
        session.commit()

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "disabled@example.com",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_login_endpoint_returns_invalid_credentials_for_disabled_wrong_password(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    user_id = await _register_user(auth_client, email="disabled-wrong@example.com")
    with Session(test_engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        user.is_active = False
        session.add(user)
        session.commit()

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "disabled-wrong@example.com",
            "password": "WrongPass1",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_endpoint_rejects_invalid_email_with_validation_detail(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "not-an-email",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "email" for detail in error["details"])
    assert "not-an-email" not in str(error["details"])
