from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.users.exceptions import UserAlreadyExistsError
from app.domains.users.models import User, UserSettings


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
            raise UserAlreadyExistsError() from exc

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()
