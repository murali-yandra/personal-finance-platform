from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlmodel import Session

from app.core.security import security_service
from app.db.session import get_session
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import RegisterUserCommand
from app.domains.users.service import UserRegistrationService
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterUserRequest(BaseModel):
    """Request body for user registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        """Normalize emails before they enter the service layer."""
        return str(email).strip().lower()


class RegisterUserData(BaseModel):
    """Response data for user registration."""

    user_id: UUID


RegisterUserResponse = SuccessResponse[RegisterUserData]


def get_registration_service(
    session: Annotated[Session, Depends(get_session)],
) -> UserRegistrationService:
    """Build the registration service dependency."""
    return UserRegistrationService(
        repository=UserRepository(session),
        security_service=security_service,
    )


@router.post(
    "/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: RegisterUserRequest,
    registration_service: Annotated[
        UserRegistrationService,
        Depends(get_registration_service),
    ],
) -> RegisterUserResponse:
    """Register a platform user."""
    result = registration_service.register_user(
        RegisterUserCommand(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
        )
    )
    return RegisterUserResponse(data=RegisterUserData(user_id=result.user_id))
