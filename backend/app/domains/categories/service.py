from uuid import UUID

from app.domains.categories.exceptions import (
    CategoryAlreadyExistsError,
    CategoryNotFoundError,
    CategoryValidationError,
    SystemCategoryProtectedError,
)
from app.domains.categories.models import Category
from app.domains.categories.repository import CategoryRepository

MAX_NAME_LENGTH = 255


class CategoryService:
    """Application service for category management."""

    def __init__(self, repository: CategoryRepository) -> None:
        self._repository = repository

    def list_categories(self, user_id: UUID) -> list[Category]:
        """Return every category visible to the user."""
        return self._repository.list_visible(user_id)

    def get_category(self, user_id: UUID, category_id: UUID) -> Category:
        """Return one visible category."""
        category = self._repository.get_visible(
            category_id=category_id,
            user_id=user_id,
        )
        if category is None:
            raise CategoryNotFoundError()
        return category

    def create_category(
        self,
        user_id: UUID,
        name: str,
        parent_category_id: UUID | None = None,
    ) -> Category:
        """Create a category owned by the user.

        A user may reuse a system category's name: the two live in separate
        uniqueness scopes, and forbidding it would stop someone renaming their
        own view of a shared concept.
        """
        cleaned = _validate_name(name)

        if self._repository.find_by_name(user_id, cleaned) is not None:
            raise CategoryAlreadyExistsError()

        if parent_category_id is not None:
            parent = self._repository.get_visible(parent_category_id, user_id)
            if parent is None:
                raise CategoryValidationError("Parent category not found.")

        category = Category(
            user_id=user_id,
            name=cleaned,
            parent_category_id=parent_category_id,
            is_system=False,
        )
        try:
            self._repository.add(category)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(category)
        return category

    def update_category(
        self,
        user_id: UUID,
        category_id: UUID,
        name: str | None = None,
        parent_category_id: UUID | None = None,
    ) -> Category:
        """Rename or re-parent a user-owned category."""
        category = self.get_category(user_id=user_id, category_id=category_id)
        if category.is_system or category.user_id is None:
            raise SystemCategoryProtectedError()

        if name is not None:
            cleaned = _validate_name(name)
            if cleaned.lower() != category.name.lower():
                existing = self._repository.find_by_name(user_id, cleaned)
                if existing is not None:
                    raise CategoryAlreadyExistsError()
            category.name = cleaned

        if parent_category_id is not None:
            if parent_category_id == category.id:
                raise CategoryValidationError("A category cannot be its own parent.")
            parent = self._repository.get_visible(parent_category_id, user_id)
            if parent is None:
                raise CategoryValidationError("Parent category not found.")
            category.parent_category_id = parent_category_id

        try:
            self._repository.flush()
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(category)
        return category

    def resolve_by_name(self, user_id: UUID, name: str) -> Category | None:
        """Return the user's category by name, falling back to a system one."""
        if not name or not name.strip():
            return None
        return self._repository.find_visible_by_name(user_id, name.strip())


def _validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise CategoryValidationError("Category name is required.")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise CategoryValidationError(
            f"Category name exceeds {MAX_NAME_LENGTH} characters."
        )
    return cleaned
