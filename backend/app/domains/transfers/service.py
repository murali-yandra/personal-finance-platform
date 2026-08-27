"""Linking two transactions that represent one movement of money."""

from decimal import Decimal
from http import HTTPStatus
from uuid import UUID

from sqlmodel import Session, select

from app.domains.transactions.models import Transaction
from app.domains.transfers.models import Transfer
from app.shared.enums import TransferType
from app.shared.exceptions.base import ApplicationError


class TransferNotFoundError(ApplicationError):
    """Raised when a transfer is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="TRANSFER_NOT_FOUND",
            message="Transfer not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class InvalidTransferError(ApplicationError):
    """Raised when two transactions cannot form a transfer."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="INVALID_TRANSFER",
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TransferUserMismatchError(ApplicationError):
    """Raised when a transfer would span two users' transactions."""

    def __init__(self) -> None:
        super().__init__(
            code="TRANSFER_USER_MISMATCH",
            message="Both transactions must belong to the same user.",
            status_code=HTTPStatus.BAD_REQUEST,
        )


class TransferService:
    """Application service for transfers."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_transfers(self, user_id: UUID) -> list[Transfer]:
        """Return the user's transfers, newest first."""
        statement = (
            select(Transfer)
            .where(Transfer.user_id == user_id)
            .order_by(Transfer.created_at.desc(), Transfer.id)  # type: ignore[attr-defined]
        )
        return list(self._session.exec(statement).all())

    def get_transfer(self, user_id: UUID, transfer_id: UUID) -> Transfer:
        """Return one user-owned transfer."""
        statement = select(Transfer).where(
            Transfer.id == transfer_id,
            Transfer.user_id == user_id,
        )
        transfer = self._session.exec(statement).first()
        if transfer is None:
            raise TransferNotFoundError()
        return transfer

    def link_transfer(
        self,
        user_id: UUID,
        source_transaction_id: UUID,
        destination_transaction_id: UUID | None = None,
        transfer_type: TransferType = TransferType.INTERNAL,
        confidence_score: Decimal | None = None,
        is_confirmed: bool = False,
    ) -> Transfer:
        """Link two transactions as one transfer.

        Both sides must belong to the caller. Linking across users would let one
        account's balance be moved by another user's transaction.
        """
        source = self._owned_transaction(user_id, source_transaction_id)

        destination = None
        if destination_transaction_id is not None:
            if destination_transaction_id == source_transaction_id:
                raise InvalidTransferError(
                    "A transaction cannot be transferred to itself."
                )
            destination = self._owned_transaction(
                user_id,
                destination_transaction_id,
            )
            if destination.account_id == source.account_id:
                raise InvalidTransferError(
                    "A transfer must move money between two different accounts."
                )

        transfer = Transfer(
            user_id=user_id,
            source_transaction_id=source.id,
            destination_transaction_id=(
                destination.id if destination is not None else None
            ),
            transfer_type=TransferType(transfer_type).value,
            confidence_score=confidence_score,
            is_confirmed=is_confirmed,
        )
        self._session.add(transfer)
        self._session.commit()
        self._session.refresh(transfer)
        return transfer

    def confirm_transfer(
        self,
        user_id: UUID,
        transfer_id: UUID,
        confirmed: bool = True,
    ) -> Transfer:
        """Mark a transfer as confirmed or unconfirmed by the user."""
        transfer = self.get_transfer(user_id=user_id, transfer_id=transfer_id)
        transfer.is_confirmed = confirmed
        self._session.add(transfer)
        self._session.commit()
        self._session.refresh(transfer)
        return transfer

    def _owned_transaction(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = self._session.get(Transaction, transaction_id)
        if transaction is None:
            raise InvalidTransferError("Transaction not found.")
        if transaction.user_id != user_id:
            raise TransferUserMismatchError()
        return transaction
