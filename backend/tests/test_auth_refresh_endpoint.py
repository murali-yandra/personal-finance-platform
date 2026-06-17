from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.jwt import JwtService, TokenType, get_jwt_service
from app.core.refresh_token import RefreshTokenService, get_refresh_token_service
from app.db.session import get_session
from app.domains.users.models import User
from app.main import app

JWT_SECRET = "placeholder-test-jwt-secret-32-bytes"
USER_EMAIL = "murali@example.com"


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
def override_dependencies(test_engine) -> Generator[None, None, None]:
    def get_test_session() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_jwt_service] = lambda: JwtService(JWT_SECRET)
    app.dependency_overrides[get_refresh_token_service] = lambda: RefreshTokenService(
        JwtService(JWT_SECRET)
    )
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    override_dependencies: None,
) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


def _create_user(
    session: Session,
    user_id: UUID,
    email: str = USER_EMAIL,
    is_active: bool = True,
) -> None:
    session.add(
        User(
            id=user_id,
            email=email,
            password_hash="$argon2id$test",
            display_name="Murali Yandra",
            is_active=is_active,
        )
    )
    session.commit()


@pytest.mark.asyncio
async def test_refresh_endpoint_returns_new_access_token(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    jwt_service = JwtService(JWT_SECRET)
    user_id = uuid4()
    with Session(test_engine) as session:
        _create_user(session, user_id)
    refresh_token = jwt_service.create_refresh_token(
        user_id=user_id,
        email=USER_EMAIL,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert set(payload["data"]) == {"access_token"}

    claims = jwt_service.decode_token(
        payload["data"]["access_token"],
        expected_token_type=TokenType.ACCESS,
    )
    assert claims["user_id"] == str(user_id)
    assert claims["email"] == USER_EMAIL


@pytest.mark.asyncio
async def test_refresh_endpoint_uses_current_database_email_for_access_token(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    jwt_service = JwtService(JWT_SECRET)
    user_id = uuid4()
    with Session(test_engine) as session:
        _create_user(session, user_id, email="current@example.com")
    refresh_token = jwt_service.create_refresh_token(
        user_id=user_id,
        email="old@example.com",
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    claims = jwt_service.decode_token(
        response.json()["data"]["access_token"],
        expected_token_type=TokenType.ACCESS,
    )
    assert claims["user_id"] == str(user_id)
    assert claims["email"] == "current@example.com"


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_access_token(
    auth_client: AsyncClient,
) -> None:
    jwt_service = JwtService(JWT_SECRET)
    access_token = jwt_service.create_access_token(
        user_id=uuid4(),
        email=USER_EMAIL,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
        headers={
            "X-Request-ID": "request-refresh-invalid",
            "X-Correlation-ID": "correlation-refresh-invalid",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "success": False,
        "error": {
            "code": "INVALID_TOKEN",
            "message": "Invalid authentication token.",
            "request_id": "request-refresh-invalid",
            "correlation_id": "correlation-refresh-invalid",
        },
    }


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_expired_refresh_token(
    auth_client: AsyncClient,
) -> None:
    expired_jwt_service = JwtService(
        JWT_SECRET,
        refresh_token_lifetime=timedelta(days=30),
        clock=lambda: datetime(2000, 1, 1, tzinfo=UTC),
    )
    expired_refresh_token = expired_jwt_service.create_refresh_token(
        user_id=uuid4(),
        email=USER_EMAIL,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_refresh_token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
    assert expired_refresh_token not in response.text


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_malformed_refresh_token(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
    assert "not-a-jwt" not in response.text


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_disabled_user(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    jwt_service = JwtService(JWT_SECRET)
    user_id = uuid4()
    with Session(test_engine) as session:
        _create_user(session, user_id, is_active=False)
    refresh_token = jwt_service.create_refresh_token(
        user_id=user_id,
        email=USER_EMAIL,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_soft_deleted_user(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    jwt_service = JwtService(JWT_SECRET)
    user_id = uuid4()
    with Session(test_engine) as session:
        _create_user(session, user_id)
        user = session.get(User, user_id)
        assert user is not None
        user.deleted_at = datetime(2026, 1, 1)
        session.add(user)
        session.commit()
    refresh_token = jwt_service.create_refresh_token(
        user_id=user_id,
        email=USER_EMAIL,
    )

    response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_refresh_endpoint_requires_refresh_token(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post("/api/v1/auth/refresh", json={})

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "refresh_token" for detail in error["details"])
