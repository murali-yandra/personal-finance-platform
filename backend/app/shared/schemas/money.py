from decimal import Decimal, InvalidOperation
from typing import Any

MONEY_QUANTIZER = Decimal("0.01")
MAX_MONEY_INTEGER_DIGITS = 16
MAX_MONEY_DECIMAL_PLACES = 2


def validate_money(value: Any) -> Decimal:
    """Validate API money values as Decimal without accepting JSON numbers."""
    if isinstance(value, bool | int | float):
        raise ValueError("Money values must be strings, not JSON numbers.")

    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        money_text = value.strip()
        if "e" in money_text.lower():
            raise ValueError("Money value must use plain decimal notation.")
        try:
            decimal_value = Decimal(money_text)
        except InvalidOperation as exc:
            raise ValueError("Money value must be a valid decimal string.") from exc
    else:
        raise ValueError("Money value must be a valid decimal string.")

    if not decimal_value.is_finite():
        raise ValueError("Money value must be finite.")

    exponent = decimal_value.as_tuple().exponent
    decimal_places = max(-exponent, 0)
    if decimal_places > MAX_MONEY_DECIMAL_PLACES:
        raise ValueError("Money value must have no more than two decimal places.")

    integer_digits = decimal_value.adjusted() + 1
    if decimal_value.copy_abs() < 1:
        integer_digits = 0
    if integer_digits > MAX_MONEY_INTEGER_DIGITS:
        raise ValueError("Money value exceeds NUMERIC(18,2) precision.")

    try:
        return decimal_value.quantize(MONEY_QUANTIZER)
    except InvalidOperation as exc:
        raise ValueError("Money value exceeds NUMERIC(18,2) precision.") from exc


def serialize_money(value: Decimal) -> str:
    """Serialize API money values as strings to avoid precision loss."""
    return str(value.quantize(MONEY_QUANTIZER))
