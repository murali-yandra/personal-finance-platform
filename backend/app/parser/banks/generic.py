"""Fallback parser for banks without a dedicated implementation.

Runs last in the registry. It uses only the shared extractors, so it handles the
common Indian bank SMS shape without knowing the sender. A message it cannot
read is reported as ``UNKNOWN_FORMAT`` rather than guessed at, because a wrong
transaction is far more expensive to undo than a missing one.
"""

from decimal import Decimal

from app.parser.base import BaseParser, ParsedTransaction, ParseResult
from app.parser.extractors import (
    detect_business_type,
    detect_direction,
    extract_account_hint,
    extract_amount,
    extract_available_balance,
    extract_merchant,
    extract_reference_number,
    extract_timestamp,
    extract_upi_id,
    is_non_transactional,
)

BASE_CONFIDENCE = Decimal("0.50")
MERCHANT_BONUS = Decimal("0.15")
ACCOUNT_BONUS = Decimal("0.15")
REFERENCE_BONUS = Decimal("0.10")
TIMESTAMP_BONUS = Decimal("0.10")
MAX_CONFIDENCE = Decimal("1.00")


class GenericParser(BaseParser):
    """Bank-agnostic parser used when no specific parser matches."""

    name = "generic"
    bank_name = None
    sender_tokens = ()

    def matches(self, sender: str | None, message_text: str) -> bool:
        """Accept every message. The registry only reaches this parser last."""
        return True

    def parse(self, sender: str | None, message_text: str) -> ParseResult:
        """Parse a message using the shared extractors."""
        skip_reason = is_non_transactional(message_text)
        if skip_reason is not None:
            return ParseResult.not_transactional(skip_reason, parser_name=self.name)

        amount = extract_amount(message_text)
        if amount is None:
            return ParseResult.failure(
                "No amount found in message.",
                parser_name=self.name,
            )

        direction = detect_direction(message_text)
        if direction is None:
            return ParseResult.failure(
                "No debit or credit indicator found in message.",
                parser_name=self.name,
            )

        account_hint = extract_account_hint(message_text)
        merchant_raw = extract_merchant(message_text)
        reference_number = extract_reference_number(message_text)
        transaction_timestamp = extract_timestamp(message_text)

        return ParseResult(
            parsed=ParsedTransaction(
                amount=amount,
                direction=direction,
                business_type=detect_business_type(message_text, direction),
                bank_name=self.resolve_bank_name(sender, message_text),
                last_four_digits=account_hint.last_four_digits,
                account_type_hint=account_hint.account_type_hint,
                merchant_raw=merchant_raw,
                reference_number=reference_number,
                upi_id=extract_upi_id(message_text),
                transaction_timestamp=transaction_timestamp,
                available_balance=extract_available_balance(message_text),
                confidence_score=self.score(
                    merchant_raw=merchant_raw,
                    last_four_digits=account_hint.last_four_digits,
                    reference_number=reference_number,
                    has_timestamp=transaction_timestamp is not None,
                ),
            ),
            parser_name=self.name,
        )

    def resolve_bank_name(self, sender: str | None, message_text: str) -> str | None:
        """Return the bank this message came from, when it is knowable."""
        return self.bank_name

    @staticmethod
    def score(
        merchant_raw: str | None,
        last_four_digits: str | None,
        reference_number: str | None,
        has_timestamp: bool,
    ) -> Decimal:
        """Score how much of the message was understood.

        Downstream consumers use this to decide whether to ask the user to
        confirm, so it reflects field coverage rather than certainty about the
        amount.
        """
        confidence = BASE_CONFIDENCE
        if merchant_raw:
            confidence += MERCHANT_BONUS
        if last_four_digits:
            confidence += ACCOUNT_BONUS
        if reference_number:
            confidence += REFERENCE_BONUS
        if has_timestamp:
            confidence += TIMESTAMP_BONUS
        return min(confidence, MAX_CONFIDENCE)
