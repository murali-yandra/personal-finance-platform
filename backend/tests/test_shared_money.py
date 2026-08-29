from decimal import Decimal
from http import HTTPStatus

import pytest

from app.domains.accounts.exceptions import (
    AccountNotFoundError,
    AccountValidationError,
    DuplicateAccountIdentityError,
)
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.money import (
    MAX_MONEY_INTEGER_DIGITS,
    MONEY_QUANTIZER,
    serialize_money,
    validate_money,
)


def test_validate_money_accepts_decimal_strings() -> None:
    assert validate_money("120.50") == Decimal("120.50")


def test_validate_money_quantizes_to_two_decimal_places() -> None:
    assert validate_money("120.5") == Decimal("120.50")


def test_validate_money_strips_surrounding_whitespace() -> None:
    assert validate_money("  99.99  ") == Decimal("99.99")


def test_validate_money_accepts_decimal_instances() -> None:
    assert validate_money(Decimal("7.5")) == Decimal("7.50")


def test_validate_money_accepts_maximum_numeric_precision() -> None:
    largest = "9" * MAX_MONEY_INTEGER_DIGITS + ".99"
    assert validate_money(largest) == Decimal(largest)


@pytest.mark.parametrize(
    "value",
    [120.50, 120, True, None, ["120.50"]],
)
def test_validate_money_rejects_non_string_inputs(value: object) -> None:
    with pytest.raises(ValueError):
        validate_money(value)


def test_validate_money_rejects_json_numbers_with_explicit_message() -> None:
    with pytest.raises(ValueError, match="must be strings, not JSON numbers"):
        validate_money(120.50)


@pytest.mark.parametrize(
    "value",
    ["12.345", "not-money", "1E+16", "", "NaN", "Infinity"],
)
def test_validate_money_rejects_invalid_decimal_text(value: str) -> None:
    with pytest.raises(ValueError):
        validate_money(value)


def test_validate_money_rejects_values_beyond_numeric_precision() -> None:
    with pytest.raises(ValueError, match="exceeds NUMERIC"):
        validate_money("9" * (MAX_MONEY_INTEGER_DIGITS + 1) + ".00")


def test_serialize_money_renders_two_decimal_places() -> None:
    assert serialize_money(Decimal("120.5")) == "120.50"


def test_money_quantizer_matches_numeric_scale() -> None:
    assert MONEY_QUANTIZER == Decimal("0.01")


def test_accounts_schemas_reexport_shared_money_validator() -> None:
    from app.domains.accounts import schemas

    assert schemas.validate_money is validate_money


def test_duplicate_account_identity_error_maps_to_conflict() -> None:
    error = DuplicateAccountIdentityError()

    assert isinstance(error, ApplicationError)
    assert error.code == "ACCOUNT_ALREADY_EXISTS"
    assert error.status_code == HTTPStatus.CONFLICT


def test_account_not_found_error_maps_to_not_found() -> None:
    error = AccountNotFoundError()

    assert isinstance(error, ApplicationError)
    assert error.code == "ACCOUNT_NOT_FOUND"
    assert error.status_code == HTTPStatus.NOT_FOUND


def test_account_validation_error_maps_to_bad_request() -> None:
    error = AccountValidationError("Opening balance is required.")

    assert isinstance(error, ApplicationError)
    assert error.code == "VALIDATION_ERROR"
    assert error.status_code == HTTPStatus.BAD_REQUEST
    assert error.message == "Opening balance is required."


def test_account_errors_do_not_leak_internal_details() -> None:
    assert "constraint" not in DuplicateAccountIdentityError().message.lower()
