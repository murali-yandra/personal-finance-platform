from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.pagination import Pagination, get_pagination
from app.db.session import get_session
from app.domains.merchants.models import Merchant, MerchantPattern
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.users.models import User
from app.shared.enums import PatternType
from app.shared.schemas.responses import (
    PageMeta,
    PaginatedResponse,
    SuccessResponse,
)

router = APIRouter(prefix="/merchants", tags=["merchants"])


class MerchantData(BaseModel):
    """Response data for one merchant."""

    id: UUID
    merchant_name: str
    merchant_group: str | None
    default_category_id: UUID | None
    is_global: bool

    @classmethod
    def from_merchant(cls, merchant: Merchant) -> "MerchantData":
        """Build the response payload from a persisted merchant."""
        return cls(
            id=merchant.id,
            merchant_name=merchant.merchant_name,
            merchant_group=merchant.merchant_group,
            default_category_id=merchant.default_category_id,
            is_global=merchant.is_global,
        )


class MerchantPatternData(BaseModel):
    """Response data for one merchant pattern."""

    id: UUID
    merchant_id: UUID
    pattern: str
    pattern_type: str
    confidence: Decimal
    created_by: str
    is_global: bool

    @classmethod
    def from_pattern(cls, pattern: MerchantPattern) -> "MerchantPatternData":
        """Build the response payload from a persisted pattern."""
        return cls(
            id=pattern.id,
            merchant_id=pattern.merchant_id,
            pattern=pattern.pattern,
            pattern_type=pattern.pattern_type,
            confidence=pattern.confidence,
            created_by=pattern.created_by,
            is_global=pattern.user_id is None,
        )


class CreateMerchantRequest(BaseModel):
    """Request body for creating a merchant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    merchant_name: str = Field(min_length=1, max_length=255)
    default_category_id: UUID | None = None


class CreateMerchantPatternRequest(BaseModel):
    """Request body for creating a merchant pattern."""

    model_config = ConfigDict(str_strip_whitespace=True)

    merchant_id: UUID
    pattern: str = Field(min_length=1, max_length=255)
    pattern_type: PatternType = PatternType.LIKE


MerchantResponse = SuccessResponse[MerchantData]
MerchantListResponse = PaginatedResponse[MerchantData]
MerchantPatternResponse = SuccessResponse[MerchantPatternData]
MerchantPatternListResponse = SuccessResponse[list[MerchantPatternData]]


def get_merchant_service(
    session: Annotated[Session, Depends(get_session)],
) -> MerchantService:
    """Build the merchant service dependency."""
    return MerchantService(repository=MerchantRepository(session))


@router.get("", response_model=MerchantListResponse)
def list_merchants(
    current_user: Annotated[User, Depends(get_current_user)],
    merchant_service: Annotated[MerchantService, Depends(get_merchant_service)],
    pagination: Annotated[Pagination, Depends(get_pagination)],
    search: Annotated[str | None, Query()] = None,
) -> MerchantListResponse:
    """List known merchants."""
    merchants, total = merchant_service.list_merchants(
        search=search,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return MerchantListResponse(
        data=[MerchantData.from_merchant(merchant) for merchant in merchants],
        meta=PageMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total,
        ),
    )


@router.post(
    "",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_merchant(
    request: CreateMerchantRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    merchant_service: Annotated[MerchantService, Depends(get_merchant_service)],
) -> MerchantResponse:
    """Create a merchant, or return the existing one with the same name."""
    merchant = merchant_service.get_or_create_merchant(
        merchant_name=request.merchant_name,
        default_category_id=request.default_category_id,
    )
    return MerchantResponse(data=MerchantData.from_merchant(merchant))


@router.get("/patterns", response_model=MerchantPatternListResponse)
def list_merchant_patterns(
    current_user: Annotated[User, Depends(get_current_user)],
    merchant_service: Annotated[MerchantService, Depends(get_merchant_service)],
) -> MerchantPatternListResponse:
    """List the caller's patterns plus every global pattern."""
    patterns = merchant_service.list_patterns(current_user.id)
    return MerchantPatternListResponse(
        data=[MerchantPatternData.from_pattern(pattern) for pattern in patterns]
    )


@router.post(
    "/patterns",
    response_model=MerchantPatternResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_merchant_pattern(
    request: CreateMerchantPatternRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    merchant_service: Annotated[MerchantService, Depends(get_merchant_service)],
) -> MerchantPatternResponse:
    """Create a pattern owned by the caller.

    Patterns created here are user-owned, so they take precedence over the
    global rules for this user only.
    """
    pattern = merchant_service.create_pattern(
        user_id=current_user.id,
        merchant_id=request.merchant_id,
        pattern=request.pattern,
        pattern_type=request.pattern_type,
        created_by="USER",
    )
    return MerchantPatternResponse(data=MerchantPatternData.from_pattern(pattern))


@router.get("/{merchant_id}", response_model=MerchantResponse)
def get_merchant(
    merchant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    merchant_service: Annotated[MerchantService, Depends(get_merchant_service)],
) -> MerchantResponse:
    """Return one merchant."""
    merchant = merchant_service.get_merchant(merchant_id)
    return MerchantResponse(data=MerchantData.from_merchant(merchant))
