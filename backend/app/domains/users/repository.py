from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.users.exceptions import UserAlreadyExistsError
from app.domains.users.models import User, UserSettings

USER_EMAIL_UNIQUE_NAMES = {"idx_users_email", "users_email_key"}


class UserRepository:
    """Persistence operations for users and user settings."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email."""
        statement = select(User).where(User.email == email)
        return self._session.exec(statement).first()

    def add_user_with_settings(self, user: User, settings: UserSettings) -> None:
        """Persist a user and one-to-one settings row."""
        try:
            self._session.add(user)
            self._session.add(settings)
            self._session.flush()
        except IntegrityError as exc:
            if _is_user_email_unique_violation(exc):
                raise UserAlreadyExistsError() from exc
            raise

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()


def _is_user_email_unique_violation(exc: IntegrityError) -> bool:
    constraint_name = _constraint_name(exc)
    if constraint_name in USER_EMAIL_UNIQUE_NAMES:
        return True

    error_message = str(exc.orig).lower()
    return "users.email" in error_message or "idx_users_email" in error_message


def _constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name:
        return str(constraint_name)
    return None
