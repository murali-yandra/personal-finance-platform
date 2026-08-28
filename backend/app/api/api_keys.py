"""Per-user ingestion API key management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.access.api_keys import ApiKeyService
from app.domains.access.models import UserApiKey
from app.domains.users.models import User
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyNotFoundError(ApplicationError):
    """Raised when an API key is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message="API key not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ApiKeyData(BaseModel):
    """Response data for one API key. Never carries the secret."""

    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    @classmethod
    def from_key(cls, key: UserApiKey) -> "ApiKeyData":
        """Build the response payload from a stored key."""
        return cls(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            revoked_at=key.revoked_at,
        )


class CreatedApiKeyData(ApiKeyData):
    """Response for a newly created key, including the one-time secret."""

    api_key: str


class CreateApiKeyRequest(BaseModel):
    """Request body for creating an API key."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(default="default", max_length=100)


ApiKeyListResponse = SuccessResponse[list[ApiKeyData]]
CreatedApiKeyResponse = SuccessResponse[CreatedApiKeyData]
ApiKeyResponse = SuccessResponse[ApiKeyData]


def get_api_key_service(
    session: Annotated[Session, Depends(get_session)],
) -> ApiKeyService:
    """Build the API key service dependency."""
    return ApiKeyService(session)


@router.get("", response_model=ApiKeyListResponse)
def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyListResponse:
    """List the caller's API keys. Secrets are never returned."""
    return ApiKeyListResponse(
        data=[ApiKeyData.from_key(key) for key in service.list_keys(current_user.id)]
    )


@router.post(
    "",
    response_model=CreatedApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    request: CreateApiKeyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> CreatedApiKeyResponse:
    """Create an API key.

    The secret is returned exactly once. Only its hash is stored, so it cannot
    be recovered later; a lost key is revoked and replaced.
    """
    issued = service.issue(user_id=current_user.id, name=request.name)
    return CreatedApiKeyResponse(
        data=CreatedApiKeyData(
            **ApiKeyData.from_key(issued.record).model_dump(),
            api_key=issued.plaintext,
        )
    )


@router.delete("/{key_id}", response_model=ApiKeyResponse)
def revoke_api_key(
    key_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiKeyService, Depends(get_api_key_service)],
) -> ApiKeyResponse:
    """Revoke an API key the caller owns."""
    revoked = service.revoke(user_id=current_user.id, key_id=key_id)
    if revoked is None:
        raise ApiKeyNotFoundError()
    return ApiKeyResponse(data=ApiKeyData.from_key(revoked))
