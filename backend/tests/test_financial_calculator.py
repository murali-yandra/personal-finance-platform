"""Money arithmetic rules (12-coding_standards.md section 13)."""

from decimal import Decimal

import pytest

from app.shared.enums import AccountType, TransactionDirection
from app.shared.financial.financial_calculator import (
    FinancialCalculator,
    MoneyError,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10", Decimal("10.00")),
        ("10.005", Decimal("10.01")),
        ("10.004", Decimal("10.00")),
        (Decimal("2.5"), Decimal("2.50")),
        (7, Decimal("7.00")),
    ],
)
def test_to_money_quantizes_to_two_places(value: object, expected: Decimal) -> None:
    assert FinancialCalculator.to_money(value) == expected


def test_to_money_routes_floats_through_str() -> None:
    """0.1 + 0.2 must not leak binary rounding error into the ledger."""
    assert FinancialCalculator.to_money(0.1 + 0.2) == Decimal("0.30")


@pytest.mark.parametrize("value", ["abc", None, object(), True])
def test_to_money_rejects_non_monetary_values(value: object) -> None:
    with pytest.raises(MoneyError):
        FinancialCalculator.to_money(value)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_to_money_rejects_non_finite_values(value: str) -> None:
    with pytest.raises(MoneyError):
        FinancialCalculator.to_money(Decimal(value))


def test_add_sums_exactly() -> None:
    assert FinancialCalculator.add("0.1", "0.2") == Decimal("0.30")


def test_total_sums_an_iterable() -> None:
    assert FinancialCalculator.total(["10.10", "20.20", "30.30"]) == Decimal("60.60")


def test_total_of_nothing_is_zero() -> None:
    assert FinancialCalculator.total([]) == Decimal("0.00")


def test_subtract() -> None:
    assert FinancialCalculator.subtract("100.00", "35.50") == Decimal("64.50")


def test_convert_applies_an_exchange_rate() -> None:
    assert FinancialCalculator.convert("100.00", "83.125000") == Decimal("8312.50")


@pytest.mark.parametrize(
    ("account_type", "direction", "expected"),
    [
        (AccountType.BANK, TransactionDirection.DEBIT, Decimal("-500.00")),
        (AccountType.BANK, TransactionDirection.CREDIT, Decimal("500.00")),
        (AccountType.CASH, TransactionDirection.DEBIT, Decimal("-500.00")),
        (AccountType.INVESTMENT, TransactionDirection.CREDIT, Decimal("500.00")),
        (AccountType.CREDIT_CARD, TransactionDirection.DEBIT, Decimal("500.00")),
        (AccountType.CREDIT_CARD, TransactionDirection.CREDIT, Decimal("-500.00")),
        (AccountType.LOAN, TransactionDirection.DEBIT, Decimal("500.00")),
    ],
)
def test_balance_delta_signs(
    account_type: AccountType,
    direction: TransactionDirection,
    expected: Decimal,
) -> None:
    """Liability balances invert: spending on a credit card increases what is owed."""
    delta = FinancialCalculator.balance_delta("500.00", direction, account_type)

    assert delta == expected


def test_balance_delta_rejects_negative_amounts() -> None:
    with pytest.raises(MoneyError):
        FinancialCalculator.balance_delta(
            "-10.00",
            TransactionDirection.DEBIT,
            AccountType.BANK,
        )


def test_apply_delta() -> None:
    assert FinancialCalculator.apply_delta("1000.00", "-250.75") == Decimal("749.25")
