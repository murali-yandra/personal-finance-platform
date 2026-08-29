from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.dependencies.auth import get_current_user
from app.core.jwt import JwtService, get_jwt_service
from app.db.session import get_session
from app.domains.users.exceptions import AccountDisabledError
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
    app.state.auth_session_factory = lambda: Session(test_engine)
    app.state.auth_jwt_service_factory = lambda: JwtService(JWT_SECRET)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        delattr(app.state, "auth_session_factory")
        delattr(app.state, "auth_jwt_service_factory")


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


def _authorization_header(user_id: UUID, email: str = "murali@example.com") -> dict:
    token = JwtService(JWT_SECRET).create_access_token(user_id=user_id, email=email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_current_user_endpoint_returns_authenticated_user(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)

    response = await auth_client.get(
        "/api/v1/users/me",
        headers=_authorization_header(user_id),
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "id": str(user_id),
            "email": "murali@example.com",
            "display_name": "Murali Yandra",
            "timezone": "Asia/Kolkata",
            "default_currency": "INR",
        },
    }


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_missing_token(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(
        "/api/v1/users/me",
        headers={
            "X-Request-ID": "request-current-missing",
            "X-Correlation-ID": "correlation-current-missing",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {
            "code": "INVALID_TOKEN",
            "message": "Invalid authentication token.",
            "request_id": "request-current-missing",
            "correlation_id": "correlation-current-missing",
        },
    }


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_refresh_token(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)
    refresh_token = JwtService(JWT_SECRET).create_refresh_token(
        user_id=user_id,
        email="murali@example.com",
    )

    response = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert refresh_token not in response.text


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_token_for_missing_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(
        "/api/v1/users/me",
        headers=_authorization_header(UUID("11111111-1111-4111-8111-111111111111")),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_current_user_endpoint_accepts_case_insensitive_bearer_scheme(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)
    token = JwtService(JWT_SECRET).create_access_token(
        user_id=user_id,
        email="murali@example.com",
    )

    response = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(user_id)


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_malformed_bearer_header(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)
    token = JwtService(JWT_SECRET).create_access_token(
        user_id=user_id,
        email="murali@example.com",
    )

    response = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token} extra"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert token not in response.text


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_expired_access_token(
    auth_client: AsyncClient,
) -> None:
    user_id = await _register_user(auth_client)
    expired_service = JwtService(
        JWT_SECRET,
        access_token_lifetime=timedelta(minutes=15),
        clock=lambda: datetime(2000, 1, 1, tzinfo=UTC),
    )
    expired_access_token = expired_service.create_access_token(
        user_id=user_id,
        email="murali@example.com",
    )

    response = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
    assert expired_access_token not in response.text


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_disabled_user(
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

    response = await auth_client.get(
        "/api/v1/users/me",
        headers=_authorization_header(user_id, email="disabled@example.com"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_current_user_endpoint_rejects_soft_deleted_user(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    user_id = await _register_user(auth_client, email="deleted@example.com")
    with Session(test_engine) as session:
        user = session.get(User, user_id)
        assert user is not None
        user.deleted_at = datetime(2026, 1, 1)
        session.add(user)
        session.commit()

    response = await auth_client.get(
        "/api/v1/users/me",
        headers=_authorization_header(user_id, email="deleted@example.com"),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_get_current_user_rechecks_inactive_request_state_user() -> None:
    request = SimpleNamespace(
        state=SimpleNamespace(
            current_user=User(
                email="disabled-state@example.com",
                password_hash="$argon2id$test",
                display_name="Disabled State",
                is_active=False,
            )
        )
    )

    with pytest.raises(AccountDisabledError):
        get_current_user(request=request, session=None, jwt_service=None)


def test_get_current_user_rechecks_soft_deleted_request_state_user() -> None:
    request = SimpleNamespace(
        state=SimpleNamespace(
            current_user=User(
                email="deleted-state@example.com",
                password_hash="$argon2id$test",
                display_name="Deleted State",
                deleted_at=datetime(2026, 1, 1),
            )
        )
    )

    with pytest.raises(AccountDisabledError):
        get_current_user(request=request, session=None, jwt_service=None)
