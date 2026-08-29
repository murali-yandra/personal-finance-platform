"""Parser contract.

Every bank parser subclasses ``BaseParser`` and implements ``parse``
(``12-coding_standards.md`` section 22). Parsers are pure: they take text and
return a value object. They never touch the database, which is what makes the
whole engine table-testable against real message samples.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.shared.enums import BusinessType, TransactionDirection


@dataclass(frozen=True)
class ParsedTransaction:
    """Structured transaction data extracted from a message."""

    amount: Decimal
    direction: TransactionDirection
    currency: str = "INR"
    business_type: BusinessType = BusinessType.UNKNOWN
    bank_name: str | None = None
    last_four_digits: str | None = None
    account_type_hint: str | None = None
    merchant_raw: str | None = None
    reference_number: str | None = None
    upi_id: str | None = None
    transaction_timestamp: datetime | None = None
    available_balance: Decimal | None = None
    confidence_score: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class ParseResult:
    """Outcome of parsing one message."""

    parsed: ParsedTransaction | None = None
    parser_name: str | None = None
    is_transactional: bool = True
    failure_reason: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def succeeded(self) -> bool:
        """Return whether structured data was produced."""
        return self.parsed is not None

    @classmethod
    def failure(
        cls,
        reason: str,
        parser_name: str | None = None,
        is_transactional: bool = True,
    ) -> "ParseResult":
        """Build a failed result."""
        return cls(
            parsed=None,
            parser_name=parser_name,
            is_transactional=is_transactional,
            failure_reason=reason,
        )

    @classmethod
    def not_transactional(
        cls,
        reason: str,
        parser_name: str | None = None,
    ) -> "ParseResult":
        """Build a result for a message that is not a transaction at all.

        OTPs, balance alerts and marketing are not parse failures; they are
        messages the pipeline should ignore rather than flag for review.
        """
        return cls(
            parsed=None,
            parser_name=parser_name,
            is_transactional=False,
            failure_reason=reason,
        )


class BaseParser(ABC):
    """Base class for bank SMS parsers."""

    name: str = "base"
    bank_name: str | None = None
    sender_tokens: tuple[str, ...] = ()

    def matches(self, sender: str | None, message_text: str) -> bool:
        """Return whether this parser recognizes the message."""
        return any(
            token in self.match_haystack(sender, message_text)
            for token in self.sender_tokens
        )

    @staticmethod
    def match_haystack(sender: str | None, message_text: str) -> str:
        """Return the text a parser should match its bank token against.

        Indian bank SMS senders look like ``VK-HDFCBK`` or ``AD-ICICIB``: a
        two-character circle prefix, a hyphen, then the bank token. Matching the
        token alone survives the prefix changing between circles and operators.

        Only the sender is searched when one is present. The message body
        routinely names other banks -- a UPI address like ``swiggy@icici`` is
        the counterparty's payment provider, not the sender -- and matching on
        the body would hand the message to the wrong bank's parser. The body is
        the fallback only when no sender was supplied at all.
        """
        if sender and sender.strip():
            return sender.upper()
        return message_text.upper()

    @abstractmethod
    def parse(self, sender: str | None, message_text: str) -> ParseResult:
        """Parse a message into structured transaction data."""
        raise NotImplementedError
