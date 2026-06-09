import os
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from sqlmodel import Session, select

from app.core.security import SecurityService
from app.db.session import engine
from app.domains.users.models import User, UserSettings
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import RegisterUserCommand
from app.domains.users.service import UserRegistrationService


@pytest.mark.skipif(
    os.getenv("RUN_DB_SMOKE_TEST") != "1",
    reason="Set RUN_DB_SMOKE_TEST=1 when PostgreSQL is available.",
)
def test_registration_service_postgresql_smoke_creates_user_and_settings() -> None:
    email = f"registration-smoke-{uuid4()}@example.com"

    with Session(engine) as session:
        service = UserRegistrationService(
            repository=UserRepository(session),
            security_service=SecurityService(
                PasswordHasher(
                    time_cost=1,
                    memory_cost=1024,
                    parallelism=1,
                    hash_len=32,
                    salt_len=16,
                    type=Type.ID,
                )
            ),
        )
        result = service.register_user(
            RegisterUserCommand(
                email=email,
                password="SecurePass1",
                display_name="Registration Smoke",
            )
        )

        user = session.get(User, result.user_id)
        settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == result.user_id)
        ).one()

        assert user is not None
        assert user.email == email
        assert settings.user_id == result.user_id

        session.delete(settings)
        session.delete(user)
        session.commit()
