"""Centralized Decimal money arithmetic.

``12-coding_standards.md`` section 13 forbids float arithmetic on money. Every
monetary value in this system is ``NUMERIC(18,2)``, so all results are quantized
to two places with banker's-rounding disabled in favour of ``ROUND_HALF_UP``,
which is what financial statements use.
"""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.shared.enums import (
    LIABILITY_ACCOUNT_TYPES,
    AccountType,
    TransactionDirection,
)

MONEY_EXPONENT = Decimal("0.01")
RATE_EXPONENT = Decimal("0.000001")
ZERO = Decimal("0.00")


class MoneyError(ValueError):
    """Raised when a value cannot be interpreted as money."""


class FinancialCalculator:
    """Decimal money operations shared across domains."""

    @staticmethod
    def to_money(value: object) -> Decimal:
        """Coerce a value to a two-place Decimal amount.

        Floats are accepted but routed through ``str`` so binary rounding error
        never enters the ledger.
        """
        if isinstance(value, Decimal):
            candidate = value
        elif isinstance(value, bool):
            raise MoneyError("A boolean is not a monetary amount.")
        elif isinstance(value, int | str):
            try:
                candidate = Decimal(str(value))
            except InvalidOperation as exc:
                raise MoneyError(f"Not a monetary amount: {value!r}") from exc
        elif isinstance(value, float):
            candidate = Decimal(str(value))
        else:
            raise MoneyError(f"Not a monetary amount: {value!r}")

        if candidate.is_nan() or candidate.is_infinite():
            raise MoneyError("Monetary amounts must be finite.")
        return candidate.quantize(MONEY_EXPONENT, rounding=ROUND_HALF_UP)

    @staticmethod
    def to_rate(value: object) -> Decimal:
        """Coerce a value to a six-place exchange rate."""
        if value is None:
            raise MoneyError("Exchange rate is required.")
        try:
            candidate = Decimal(str(value))
        except InvalidOperation as exc:
            raise MoneyError(f"Not an exchange rate: {value!r}") from exc
        if candidate.is_nan() or candidate.is_infinite():
            raise MoneyError("Exchange rates must be finite.")
        return candidate.quantize(RATE_EXPONENT, rounding=ROUND_HALF_UP)

    @classmethod
    def add(cls, *amounts: object) -> Decimal:
        """Return the sum of the given amounts."""
        total = ZERO
        for amount in amounts:
            total += cls.to_money(amount)
        return cls.to_money(total)

    @classmethod
    def total(cls, amounts: Iterable[object]) -> Decimal:
        """Return the sum of an iterable of amounts."""
        return cls.add(*amounts)

    @classmethod
    def subtract(cls, minuend: object, subtrahend: object) -> Decimal:
        """Return ``minuend - subtrahend``."""
        return cls.to_money(cls.to_money(minuend) - cls.to_money(subtrahend))

    @classmethod
    def convert(cls, amount: object, exchange_rate: object) -> Decimal:
        """Convert an amount using an exchange rate."""
        return cls.to_money(cls.to_money(amount) * cls.to_rate(exchange_rate))

    @classmethod
    def balance_delta(
        cls,
        amount: object,
        direction: TransactionDirection,
        account_type: AccountType,
    ) -> Decimal:
        """Return the signed change a transaction applies to an account balance.

        Asset accounts (bank, cash, investment) fall on a debit and rise on a
        credit. Liability accounts (credit card, loan) are stored as a positive
        outstanding balance, so the signs invert: spending on a credit card
        increases what is owed (``04-database_schema.md`` section 8).
        """
        magnitude = cls.to_money(amount)
        if magnitude < ZERO:
            raise MoneyError("Transaction amounts must not be negative.")

        is_debit = TransactionDirection(direction) is TransactionDirection.DEBIT
        if AccountType(account_type) in LIABILITY_ACCOUNT_TYPES:
            return magnitude if is_debit else -magnitude
        return -magnitude if is_debit else magnitude

    @classmethod
    def apply_delta(cls, balance: object, delta: object) -> Decimal:
        """Apply a signed delta to a balance."""
        return cls.to_money(cls.to_money(balance) + cls.to_money(delta))
