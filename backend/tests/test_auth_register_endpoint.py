import logging
from collections.abc import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.auth import get_registration_service
from app.db.session import get_session
from app.domains.users.models import User, UserSettings
from app.main import app


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


def _validation_detail(error: dict, field: str) -> dict:
    return next(detail for detail in error["details"] if detail["field"] == field)


@pytest.mark.asyncio
async def test_register_endpoint_creates_user_and_settings(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "Murali@Example.COM",
            "password": "SecurePass1",
            "display_name": " Murali Yandra ",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    user_id = UUID(payload["data"]["user_id"])

    assert payload["success"] is True
    assert set(payload["data"]) == {"user_id"}

    with Session(test_engine) as session:
        user = session.get(User, user_id)
        settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == user_id)
        ).one()

    assert user is not None
    assert user.email == "murali@example.com"
    assert user.display_name == "Murali Yandra"
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != "SecurePass1"
    assert settings.notification_mode == "LOW_CONFIDENCE_ONLY"
    assert settings.preferred_language == "en"


@pytest.mark.asyncio
async def test_register_endpoint_rejects_duplicate_email(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    request_body = {
        "email": "murali@example.com",
        "password": "SecurePass1",
        "display_name": "Murali Yandra",
    }
    first_response = await auth_client.post("/api/v1/auth/register", json=request_body)
    duplicate_response = await auth_client.post(
        "/api/v1/auth/register",
        json={**request_body, "email": "MURALI@example.com"},
        headers={
            "X-Request-ID": "request-123",
            "X-Correlation-ID": "correlation-123",
        },
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "success": False,
        "error": {
            "code": "USER_ALREADY_EXISTS",
            "message": "A user with this email already exists.",
            "request_id": "request-123",
            "correlation_id": "correlation-123",
        },
    }

    with Session(test_engine) as session:
        users = session.exec(select(User)).all()
        settings = session.exec(select(UserSettings)).all()

    assert len(users) == 1
    assert len(settings) == 1


@pytest.mark.asyncio
async def test_register_endpoint_rejects_invalid_email(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass1",
            "display_name": "Invalid Email",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    error = payload["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Request validation failed."
    assert _validation_detail(error, "email")["message"]
    assert "not-an-email" not in str(error["details"])

    with Session(test_engine) as session:
        assert session.exec(select(User)).all() == []


@pytest.mark.asyncio
async def test_register_endpoint_rejects_weak_password(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "lowercaseonly",
            "display_name": "Weak Password",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Password must contain an uppercase letter."

    with Session(test_engine) as session:
        assert session.exec(select(User)).all() == []
        assert session.exec(select(UserSettings)).all() == []


@pytest.mark.asyncio
async def test_register_endpoint_rejects_missing_display_name(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "missing-name@example.com",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    error = payload["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert _validation_detail(error, "display_name")["message"]

    with Session(test_engine) as session:
        assert session.exec(select(User)).all() == []


@pytest.mark.asyncio
async def test_register_endpoint_rejects_short_password_with_field_detail(
    auth_client: AsyncClient,
    test_engine,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "short-password@example.com",
            "password": "Short1",
            "display_name": "Short Password",
        },
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    detail = _validation_detail(error, "password")
    assert detail["message"]
    assert "Short1" not in str(error["details"])

    with Session(test_engine) as session:
        assert session.exec(select(User)).all() == []


@pytest.mark.asyncio
async def test_register_endpoint_does_not_require_authorization_header(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "public@example.com",
            "password": "SecurePass1",
            "display_name": "Public Register",
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_endpoint_returns_standard_500_for_unexpected_errors(
    caplog,
) -> None:
    def raise_unexpected_error():
        raise RuntimeError("database exploded")

    app.dependency_overrides[get_registration_service] = raise_unexpected_error
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            with caplog.at_level(logging.ERROR, logger="app.api.errors"):
                response = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "unexpected@example.com",
                        "password": "SecurePass1",
                        "display_name": "Unexpected Error",
                    },
                    headers={
                        "X-Request-ID": "request-500",
                        "X-Correlation-ID": "correlation-500",
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": {
            "code": "UNEXPECTED_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": "request-500",
            "correlation_id": "correlation-500",
        },
    }
    assert "database exploded" not in response.text
    assert "Unhandled API exception" in caplog.text
    assert any(record.exc_info for record in caplog.records)
