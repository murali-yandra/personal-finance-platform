from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlmodel import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.domains.transfers.models import Transfer
from app.domains.transfers.service import TransferService
from app.domains.users.models import User
from app.shared.enums import TransferType
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/transfers", tags=["transfers"])


class TransferData(BaseModel):
    """Response data for one transfer."""

    id: UUID
    source_transaction_id: UUID
    destination_transaction_id: UUID | None
    transfer_type: str
    confidence_score: Decimal | None
    is_confirmed: bool

    @classmethod
    def from_transfer(cls, transfer: Transfer) -> "TransferData":
        """Build the response payload from a persisted transfer."""
        return cls(
            id=transfer.id,
            source_transaction_id=transfer.source_transaction_id,
            destination_transaction_id=transfer.destination_transaction_id,
            transfer_type=transfer.transfer_type,
            confidence_score=transfer.confidence_score,
            is_confirmed=transfer.is_confirmed,
        )


class CreateTransferRequest(BaseModel):
    """Request body for linking two transactions as a transfer."""

    source_transaction_id: UUID
    destination_transaction_id: UUID | None = None
    transfer_type: TransferType = TransferType.INTERNAL


class ConfirmTransferRequest(BaseModel):
    """Request body for confirming a transfer."""

    confirmed: bool = True


TransferResponse = SuccessResponse[TransferData]
TransferListResponse = SuccessResponse[list[TransferData]]


def get_transfer_service(
    session: Annotated[Session, Depends(get_session)],
) -> TransferService:
    """Build the transfer service dependency."""
    return TransferService(session)


@router.get("", response_model=TransferListResponse)
def list_transfers(
    current_user: Annotated[User, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferListResponse:
    """List the authenticated user's transfers."""
    transfers = transfer_service.list_transfers(current_user.id)
    return TransferListResponse(
        data=[TransferData.from_transfer(transfer) for transfer in transfers]
    )


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    request: CreateTransferRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferResponse:
    """Link two transactions as one transfer."""
    transfer = transfer_service.link_transfer(
        user_id=current_user.id,
        source_transaction_id=request.source_transaction_id,
        destination_transaction_id=request.destination_transaction_id,
        transfer_type=request.transfer_type,
    )
    return TransferResponse(data=TransferData.from_transfer(transfer))


@router.post("/{transfer_id}/confirm", response_model=TransferResponse)
def confirm_transfer(
    transfer_id: UUID,
    request: ConfirmTransferRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transfer_service: Annotated[TransferService, Depends(get_transfer_service)],
) -> TransferResponse:
    """Confirm or unconfirm a detected transfer."""
    transfer = transfer_service.confirm_transfer(
        user_id=current_user.id,
        transfer_id=transfer_id,
        confirmed=request.confirmed,
    )
    return TransferResponse(data=TransferData.from_transfer(transfer))
