import os
from collections.abc import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://placeholder_user:placeholder_password"
    "@localhost:5432/placeholder_db?connect_timeout=1",
)
os.environ.setdefault("JWT_SECRET", "placeholder-test-jwt-secret-32-bytes")
os.environ.setdefault("INGEST_API_KEY", "placeholder-test-ingest-api-key")

from app.core.jwt import JwtService, get_jwt_service  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402

TEST_JWT_SECRET = "placeholder-test-jwt-secret-32-bytes"
TEST_INGEST_API_KEY = "placeholder-test-ingest-api-key"
DEFAULT_TEST_EMAIL = "murali@example.com"
DEFAULT_TEST_PASSWORD = "SecurePass1"
DEFAULT_TEST_DISPLAY_NAME = "Murali Yandra"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Return an ASGI-backed HTTP client with no database wiring."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.fixture
def test_engine():
    """Return an in-memory SQLite engine with the full schema created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """Yield a session bound to the in-memory test engine."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def override_session(test_engine) -> Generator[None, None, None]:
    """Point the app and the authentication middleware at the test engine.

    ``AuthenticationMiddleware`` runs before FastAPI dependency resolution and opens
    its own session, so ``app.dependency_overrides`` alone is not enough. The
    middleware reads its factories from ``app.state``, which this fixture also sets.
    """

    def get_test_session() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_jwt_service] = lambda: JwtService(TEST_JWT_SECRET)
    app.state.auth_session_factory = lambda: Session(test_engine)
    app.state.auth_jwt_service_factory = lambda: JwtService(TEST_JWT_SECRET)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        for attribute in ("auth_session_factory", "auth_jwt_service_factory"):
            if hasattr(app.state, attribute):
                delattr(app.state, attribute)


@pytest_asyncio.fixture
async def auth_client(override_session: None) -> AsyncGenerator[AsyncClient, None]:
    """Return an HTTP client wired to the in-memory test database."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


async def register_user(
    client: AsyncClient,
    email: str = DEFAULT_TEST_EMAIL,
    password: str = DEFAULT_TEST_PASSWORD,
    display_name: str = DEFAULT_TEST_DISPLAY_NAME,
) -> UUID:
    """Register a user through the API and return the new user ID."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["data"]["user_id"])


def authorization_header(
    user_id: UUID,
    email: str = DEFAULT_TEST_EMAIL,
) -> dict[str, str]:
    """Build an Authorization header carrying a valid access token."""
    token = JwtService(TEST_JWT_SECRET).create_access_token(
        user_id=user_id,
        email=email,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authenticated_user(auth_client: AsyncClient) -> tuple[UUID, dict[str, str]]:
    """Register a user and return its ID alongside a ready Authorization header."""
    user_id = await register_user(auth_client)
    return user_id, authorization_header(user_id)
