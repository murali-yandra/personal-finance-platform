from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.domains.categories.models import Category


class CategoryRepository:
    """Persistence operations for categories."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_visible(self, category_id: UUID, user_id: UUID) -> Category | None:
        """Return a category the user can see: their own, or a system one."""
        statement = select(Category).where(
            Category.id == category_id,
            or_(
                Category.user_id == user_id,
                Category.user_id.is_(None),  # type: ignore[union-attr]
            ),
        )
        return self._session.exec(statement).first()

    def list_visible(self, user_id: UUID) -> list[Category]:
        """Return every category the user can see, system categories first."""
        statement = select(Category).where(
            or_(
                Category.user_id == user_id,
                Category.user_id.is_(None),  # type: ignore[union-attr]
            )
        )
        categories = list(self._session.exec(statement).all())
        categories.sort(key=lambda category: (not category.is_system, category.name))
        return categories

    def find_by_name(self, user_id: UUID | None, name: str) -> Category | None:
        """Return a category by exact, case-insensitive name within its scope."""
        statement = select(Category).where(
            func.lower(Category.name) == name.strip().lower()
        )
        if user_id is None:
            statement = statement.where(Category.user_id.is_(None))  # type: ignore[union-attr]
        else:
            statement = statement.where(Category.user_id == user_id)
        return self._session.exec(statement).first()

    def find_visible_by_name(self, user_id: UUID, name: str) -> Category | None:
        """Return the user's category by name, falling back to a system one."""
        return self.find_by_name(user_id, name) or self.find_by_name(None, name)

    def add(self, category: Category) -> Category:
        """Persist a category."""
        self._session.add(category)
        self._session.flush()
        return category

    def flush(self) -> None:
        """Flush pending changes."""
        self._session.flush()

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, category: Category) -> None:
        """Reload a category from the database."""
        self._session.refresh(category)
