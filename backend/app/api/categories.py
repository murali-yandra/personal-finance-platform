from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.categories.models import Category
from app.domains.categories.repository import CategoryRepository
from app.domains.categories.service import CategoryService
from app.domains.users.models import User
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryData(BaseModel):
    """Response data for one category."""

    id: UUID
    name: str
    parent_category_id: UUID | None
    is_system: bool

    @classmethod
    def from_category(cls, category: Category) -> "CategoryData":
        """Build the response payload from a persisted category."""
        return cls(
            id=category.id,
            name=category.name,
            parent_category_id=category.parent_category_id,
            is_system=category.is_system,
        )


class CreateCategoryRequest(BaseModel):
    """Request body for creating a category."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    parent_category_id: UUID | None = None


class UpdateCategoryRequest(BaseModel):
    """Request body for updating a category."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_category_id: UUID | None = None


CategoryResponse = SuccessResponse[CategoryData]
CategoryListResponse = SuccessResponse[list[CategoryData]]


def get_category_service(
    session: Annotated[Session, Depends(get_session)],
) -> CategoryService:
    """Build the category service dependency."""
    return CategoryService(repository=CategoryRepository(session))


@router.get("", response_model=CategoryListResponse)
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryListResponse:
    """List the system categories plus the caller's own."""
    categories = category_service.list_categories(current_user.id)
    return CategoryListResponse(
        data=[CategoryData.from_category(category) for category in categories]
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    request: CreateCategoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    """Create a category owned by the caller."""
    category = category_service.create_category(
        user_id=current_user.id,
        name=request.name,
        parent_category_id=request.parent_category_id,
    )
    return CategoryResponse(data=CategoryData.from_category(category))


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    request: UpdateCategoryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    category_service: Annotated[CategoryService, Depends(get_category_service)],
) -> CategoryResponse:
    """Rename or re-parent a category the caller owns.

    System categories are shared by every user, so they cannot be modified.
    """
    category = category_service.update_category(
        user_id=current_user.id,
        category_id=category_id,
        name=request.name,
        parent_category_id=request.parent_category_id,
    )
    return CategoryResponse(data=CategoryData.from_category(category))
