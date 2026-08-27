"""SMS processing pipeline.

Implements the flow in ``07-sequence_diagrams.md``:

```text
raw event -> parse -> resolve account -> resolve merchant -> resolve category
          -> create transaction -> TransactionCreated
```

Processing runs synchronously inside the ingestion request. MVP deploys only a
backend and a database container (``11-deployment_standards.md`` section 5), so
there is no worker to hand off to, and the SMS-to-transaction budget of five
seconds (``14-sprint_roadmap.md`` section 26) is met comfortably.

The raw event is already committed before this runs, so every outcome here is
recorded against a stored message rather than lost.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from app.domains.accounts.models import Account
from app.domains.accounts.repository import AccountRepository
from app.domains.categories.repository import CategoryRepository
from app.domains.ingestion.models import RawEvent
from app.domains.ingestion.repository import RawEventRepository
from app.domains.ingestion.schemas import IngestSmsResult
from app.domains.merchants.service import MerchantService
from app.domains.transactions.exceptions import DuplicateTransactionError
from app.domains.transactions.schemas import CreateTransactionCommand
from app.domains.transactions.service import TransactionService
from app.parser import ParseResult, ParserRegistry, default_registry
from app.shared.enums import AccountStatus, ProcessingStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedAccount:
    """The account a parsed message belongs to."""

    account: Account
    was_created: bool
    is_archived: bool = False

    @property
    def needs_review(self) -> bool:
        """Return whether the user should be asked to confirm the account."""
        return self.was_created or self.is_archived


class SmsPipeline:
    """Turns a stored raw event into a transaction."""

    def __init__(
        self,
        raw_event_repository: RawEventRepository,
        account_repository: AccountRepository,
        transaction_service: TransactionService,
        merchant_service: MerchantService,
        category_repository: CategoryRepository,
        registry: ParserRegistry | None = None,
    ) -> None:
        self._raw_events = raw_event_repository
        self._accounts = account_repository
        self._transactions = transaction_service
        self._merchants = merchant_service
        self._categories = category_repository
        self._registry = registry or default_registry

    def process(self, raw_event: RawEvent) -> IngestSmsResult:
        """Parse and post a stored raw event."""
        result = self._registry.parse(raw_event.sender, raw_event.message_text)

        if not result.succeeded:
            return self._record_unparsed(raw_event, result)

        parsed = result.parsed
        resolved = self._resolve_account(raw_event.user_id, result)
        merchant_id = self._resolve_merchant(raw_event.user_id, parsed.merchant_raw)
        category_id = self._resolve_category(raw_event.user_id, merchant_id)

        try:
            transaction = self._transactions.create_transaction(
                CreateTransactionCommand(
                    user_id=raw_event.user_id,
                    account_id=resolved.account.id,
                    amount=parsed.amount,
                    direction=parsed.direction,
                    currency=parsed.currency,
                    business_type=parsed.business_type,
                    merchant_raw=parsed.merchant_raw,
                    reference_number=parsed.reference_number,
                    upi_id=parsed.upi_id,
                    transaction_timestamp=(
                        parsed.transaction_timestamp or raw_event.received_at
                    ),
                    sms_received_timestamp=raw_event.received_at,
                    raw_event_id=raw_event.id,
                    merchant_id=merchant_id,
                    category_id=category_id,
                    confidence_score=parsed.confidence_score,
                    allow_archived_account=resolved.is_archived,
                )
            )
        except DuplicateTransactionError as exc:
            self._set_status(raw_event, ProcessingStatus.DUPLICATE)
            return IngestSmsResult(
                raw_event_id=raw_event.id,
                status=ProcessingStatus.DUPLICATE,
                is_duplicate=True,
                transaction_id=(
                    UUID(exc.existing_transaction_id)
                    if exc.existing_transaction_id
                    else None
                ),
            )

        status = (
            ProcessingStatus.NEEDS_REVIEW
            if resolved.needs_review
            else ProcessingStatus.PROCESSED
        )
        self._set_status(raw_event, status)
        return IngestSmsResult(
            raw_event_id=raw_event.id,
            status=status,
            transaction_id=transaction.id,
        )

    def _record_unparsed(
        self,
        raw_event: RawEvent,
        result: ParseResult,
    ) -> IngestSmsResult:
        """Record why a message produced no transaction.

        A non-transactional message (an OTP, a due-date reminder) is IGNORED
        rather than UNKNOWN_FORMAT, so genuine parser gaps stay visible in the
        FAILED and UNKNOWN_FORMAT queues instead of being buried in noise.
        """
        status = (
            ProcessingStatus.UNKNOWN_FORMAT
            if result.is_transactional
            else ProcessingStatus.IGNORED
        )
        self._set_status(raw_event, status, error=result.failure_reason)
        return IngestSmsResult(raw_event_id=raw_event.id, status=status)

    def _resolve_account(
        self,
        user_id: UUID,
        result: ParseResult,
    ) -> ResolvedAccount:
        """Find the account the message belongs to, creating a stub if unknown.

        An unrecognized account is created as PENDING rather than dropped: the
        transaction is real money and must be recorded, and the user confirms
        the account details afterwards (``07-sequence_diagrams.md``,
        NewAccountDetected).

        An archived account still matches. Archiving says the user stopped using
        it, but a bank message says money moved on it anyway, and the accounts
        uniqueness constraint would reject a second account with the same bank
        and digits regardless. The transaction is recorded against the real
        account, the account stays archived so the user's decision is not
        silently reversed, and the message is flagged NEEDS_REVIEW so they are
        asked about the conflict.
        """
        parsed = result.parsed
        existing = self._find_account(
            user_id=user_id,
            bank_name=parsed.bank_name,
            last_four_digits=parsed.last_four_digits,
        )
        if existing is not None:
            return ResolvedAccount(
                account=existing,
                was_created=False,
                is_archived=existing.status == AccountStatus.ARCHIVED,
            )

        account = Account(
            user_id=user_id,
            account_type=parsed.account_type_hint or "BANK",
            bank_name=parsed.bank_name,
            last_four_digits=parsed.last_four_digits,
            currency=parsed.currency,
            status=AccountStatus.PENDING.value,
        )
        self._accounts.add(account)
        self._accounts.commit()
        self._accounts.refresh(account)
        logger.info("Created pending account %s from parsed message", account.id)
        return ResolvedAccount(account=account, was_created=True)

    def _find_account(
        self,
        user_id: UUID,
        bank_name: str | None,
        last_four_digits: str | None,
    ) -> Account | None:
        candidates = self._accounts.list_for_user(user_id=user_id, statuses=None)

        if last_four_digits:
            by_digits = [
                account
                for account in candidates
                if account.last_four_digits == last_four_digits
            ]
            # Prefer a live account when one exists; fall back to an archived
            # match rather than colliding with the uniqueness constraint.
            by_digits.sort(key=lambda a: a.status == AccountStatus.ARCHIVED)
            if bank_name:
                exact = [
                    account
                    for account in by_digits
                    if (account.bank_name or "").upper() == bank_name.upper()
                ]
                if exact:
                    return exact[0]
            # Digits alone identify the account when only one holds them.
            if len(by_digits) == 1:
                return by_digits[0]
        return None

    def _resolve_merchant(self, user_id: UUID, merchant_raw: str | None) -> UUID | None:
        """Resolve the merchant, leaving it unset when nothing matches."""
        if not merchant_raw:
            return None
        match = self._merchants.resolve(user_id, merchant_raw)
        return match.merchant_id if match is not None else None

    def _resolve_category(
        self,
        user_id: UUID,
        merchant_id: UUID | None,
    ) -> UUID | None:
        """Take the merchant's default category, if it has one."""
        if merchant_id is None:
            return None
        merchant = self._merchants.get_merchant(merchant_id)
        if merchant.default_category_id is None:
            return None
        category = self._categories.get_visible(
            category_id=merchant.default_category_id,
            user_id=user_id,
        )
        return category.id if category is not None else None

    def _set_status(
        self,
        raw_event: RawEvent,
        status: ProcessingStatus,
        error: str | None = None,
    ) -> None:
        raw_event.processing_status = status.value
        raw_event.processing_error = error
        self._raw_events.add(raw_event)
        self._raw_events.commit()
