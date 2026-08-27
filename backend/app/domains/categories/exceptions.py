from http import HTTPStatus

from app.shared.exceptions.base import ApplicationError


class CategoryNotFoundError(ApplicationError):
    """Raised when a category is missing or not visible to the caller."""

    def __init__(self) -> None:
        super().__init__(
            code="CATEGORY_NOT_FOUND",
            message="Category not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class CategoryAlreadyExistsError(ApplicationError):
    """Raised when a category name is already taken."""

    def __init__(self) -> None:
        super().__init__(
            code="CATEGORY_ALREADY_EXISTS",
            message="A category with this name already exists.",
            status_code=HTTPStatus.CONFLICT,
        )


class SystemCategoryProtectedError(ApplicationError):
    """Raised when a caller tries to modify a shared system category."""

    def __init__(self) -> None:
        super().__init__(
            code="SYSTEM_CATEGORY_PROTECTED",
            message="System categories cannot be modified or deleted.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class CategoryValidationError(ApplicationError):
    """Raised when category input violates a business rule."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )
