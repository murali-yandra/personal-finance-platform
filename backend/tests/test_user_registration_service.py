from collections.abc import Generator
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.security import SecurityService
from app.domains.users.exceptions import (
    UserAlreadyExistsError,
    UserRegistrationValidationError,
)
from app.domains.users.models import User, UserSettings
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import RegisterUserCommand
from app.domains.users.service import UserRegistrationService


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as test_session:
        yield test_session


@pytest.fixture
def registration_service(session: Session) -> UserRegistrationService:
    return UserRegistrationService(
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


def test_register_user_creates_user_and_settings(
    session: Session,
    registration_service: UserRegistrationService,
) -> None:
    result = registration_service.register_user(
        RegisterUserCommand(
            email="Murali@Example.COM ",
            password="SecurePass1",
            display_name=" Murali Yandra ",
        )
    )

    user = session.get(User, result.user_id)
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == result.user_id)
    ).one()

    assert user is not None
    assert user.email == "murali@example.com"
    assert user.display_name == "Murali Yandra"
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != "SecurePass1"
    assert user.timezone == "Asia/Kolkata"
    assert user.default_currency == "INR"
    assert settings.notification_mode == "LOW_CONFIDENCE_ONLY"
    assert settings.ai_suggestions_enabled is False
    assert settings.preferred_language == "en"


def test_register_user_rejects_duplicate_email(
    registration_service: UserRegistrationService,
) -> None:
    command = RegisterUserCommand(
        email="murali@example.com",
        password="SecurePass1",
        display_name="Murali Yandra",
    )
    registration_service.register_user(command)

    with pytest.raises(UserAlreadyExistsError):
        registration_service.register_user(command)


def test_register_user_rejects_weak_password_and_rolls_back(
    session: Session,
    registration_service: UserRegistrationService,
) -> None:
    with pytest.raises(UserRegistrationValidationError):
        registration_service.register_user(
            RegisterUserCommand(
                email="weak@example.com",
                password="lowercaseonly",
                display_name="Weak Password",
            )
        )

    assert (
        session.exec(select(User).where(User.email == "weak@example.com")).first()
        is None
    )
    assert session.exec(select(UserSettings)).all() == []


def test_register_user_rejects_blank_display_name(
    session: Session,
    registration_service: UserRegistrationService,
) -> None:
    with pytest.raises(UserRegistrationValidationError):
        registration_service.register_user(
            RegisterUserCommand(
                email="blank@example.com",
                password="SecurePass1",
                display_name="   ",
            )
        )

    assert (
        session.exec(select(User).where(User.email == "blank@example.com")).first()
        is None
    )


class IntegrityFailingSession:
    def add(self, _value: object) -> None:
        return None

    def flush(self) -> None:
        raise IntegrityError(
            statement="INSERT INTO user_settings",
            params={},
            orig=Exception("UNIQUE constraint failed: user_settings.user_id"),
        )


def test_user_repository_reraises_non_email_integrity_errors() -> None:
    user_id = uuid4()
    repository = UserRepository(IntegrityFailingSession())

    user = User(
        id=user_id,
        email="integrity@example.com",
        password_hash="$argon2id$test",
        display_name="Integrity Test",
    )
    settings = UserSettings(user_id=user_id)

    with pytest.raises(IntegrityError):
        repository.add_user_with_settings(user, settings)
