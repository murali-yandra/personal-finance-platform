"""Multi-factor authentication management."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.access.mfa import MfaService
from app.domains.users.models import User
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/mfa", tags=["mfa"])


class MfaStatusData(BaseModel):
    """Response data describing a user's MFA state."""

    enabled: bool
    enrolment_pending: bool
    confirmed_at: datetime | None
    recovery_codes_remaining: int


class MfaEnrolmentData(BaseModel):
    """Response data for a new enrolment. Returned once."""

    secret: str
    provisioning_uri: str
    recovery_codes: list[str]


class MfaCodeRequest(BaseModel):
    """Request body carrying a verification code."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(min_length=6, max_length=32)


class RecoveryCodesData(BaseModel):
    """Response data for regenerated recovery codes."""

    recovery_codes: list[str]


MfaStatusResponse = SuccessResponse[MfaStatusData]
MfaEnrolmentResponse = SuccessResponse[MfaEnrolmentData]
RecoveryCodesResponse = SuccessResponse[RecoveryCodesData]


def get_mfa_service(
    session: Annotated[Session, Depends(get_session)],
) -> MfaService:
    """Build the MFA service dependency."""
    return MfaService(session)


@router.get("", response_model=MfaStatusResponse)
def mfa_status(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MfaService, Depends(get_mfa_service)],
) -> MfaStatusResponse:
    """Report whether MFA is enabled and how many recovery codes remain."""
    record = service.get_mfa(current_user.id)
    return MfaStatusResponse(
        data=MfaStatusData(
            enabled=bool(record and record.is_enabled),
            enrolment_pending=bool(record and not record.is_enabled),
            confirmed_at=record.confirmed_at if record else None,
            recovery_codes_remaining=service.remaining_recovery_codes(current_user.id),
        )
    )


@router.post(
    "/enrol",
    response_model=MfaEnrolmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def begin_enrolment(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MfaService, Depends(get_mfa_service)],
) -> MfaEnrolmentResponse:
    """Start enrolment by generating a secret and recovery codes.

    This does **not** enable MFA. The user must confirm with a real code first,
    so a secret that never reached their authenticator cannot lock them out.
    The secret and recovery codes are shown once and never again.
    """
    enrolment = service.begin_enrolment(
        user_id=current_user.id,
        email=current_user.email,
    )
    return MfaEnrolmentResponse(
        data=MfaEnrolmentData(
            secret=enrolment.secret,
            provisioning_uri=enrolment.provisioning_uri,
            recovery_codes=list(enrolment.recovery_codes),
        )
    )


@router.post("/confirm", response_model=MfaStatusResponse)
def confirm_enrolment(
    request: MfaCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MfaService, Depends(get_mfa_service)],
) -> MfaStatusResponse:
    """Enable MFA once a code proves the authenticator holds the secret."""
    record = service.confirm_enrolment(current_user.id, request.code)
    return MfaStatusResponse(
        data=MfaStatusData(
            enabled=record.is_enabled,
            enrolment_pending=False,
            confirmed_at=record.confirmed_at,
            recovery_codes_remaining=service.remaining_recovery_codes(current_user.id),
        )
    )


@router.post("/disable", response_model=MfaStatusResponse)
def disable_mfa(
    request: MfaCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MfaService, Depends(get_mfa_service)],
) -> MfaStatusResponse:
    """Turn MFA off, which requires a valid code.

    Without the code, anyone holding a stolen access token could strip the
    protection that MFA exists to provide.
    """
    service.disable(current_user.id, request.code)
    return MfaStatusResponse(
        data=MfaStatusData(
            enabled=False,
            enrolment_pending=False,
            confirmed_at=None,
            recovery_codes_remaining=0,
        )
    )


@router.post("/recovery-codes", response_model=RecoveryCodesResponse)
def regenerate_recovery_codes(
    request: MfaCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[MfaService, Depends(get_mfa_service)],
) -> RecoveryCodesResponse:
    """Replace the recovery codes. The previous set stops working."""
    codes = service.regenerate_recovery_codes(current_user.id, request.code)
    return RecoveryCodesResponse(data=RecoveryCodesData(recovery_codes=list(codes)))
