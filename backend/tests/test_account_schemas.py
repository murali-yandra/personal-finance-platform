from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.accounts.enums import AccountStatus, AccountType
from app.domains.accounts.models import Account
from app.domains.accounts.schemas import (
    AccountResponse,
    AccountResponseData,
    CreateAccountRequest,
    UpdateAccountRequest,
)


def test_account_enums_use_architecture_values() -> None:
    assert [account_type.value for account_type in AccountType] == [
        "BANK",
        "CREDIT_CARD",
        "CASH",
        "INVESTMENT",
        "LOAN",
    ]
    assert [status.value for status in AccountStatus] == [
        "PENDING",
        "ACTIVE",
        "ARCHIVED",
        "DISABLED",
    ]


def test_create_account_request_accepts_valid_payload_and_normalizes_currency() -> None:
    request = CreateAccountRequest(
        account_name="Salary Account",
        account_type="BANK",
        bank_name="ICICI",
        last_four_digits="0452",
        currency=" inr ",
        opening_balance="1250.5",
    )

    assert request.account_type is AccountType.BANK
    assert request.currency == "INR"
    assert request.opening_balance == Decimal("1250.50")


def test_create_account_request_rejects_invalid_enum_values() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CreateAccountRequest(
            account_name="Wallet",
            account_type="WALLET",
            opening_balance="0.00",
        )

    assert exc_info.value.errors()[0]["loc"] == ("account_type",)


@pytest.mark.parametrize(
    "invalid_money",
    [
        120.50,
        120,
        "12.345",
        "not-money",
        "1E+16",
        "1E+17",
        "1E+100",
        "10000000000000000.00",
    ],
)
def test_create_account_request_rejects_invalid_money_values(
    invalid_money: object,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        CreateAccountRequest(
            account_name="Salary Account",
            account_type="BANK",
            opening_balance=invalid_money,
        )

    error_text = str(exc_info.value)
    assert "opening_balance" in error_text


def test_create_account_request_accepts_max_numeric_18_2_money_value() -> None:
    request = CreateAccountRequest(
        account_name="Large Balance Account",
        account_type="BANK",
        opening_balance="9999999999999999.99",
    )

    assert request.opening_balance == Decimal("9999999999999999.99")


@pytest.mark.parametrize("invalid_currency", ["IN", "INR1", "12A"])
def test_create_account_request_rejects_invalid_currency(
    invalid_currency: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        CreateAccountRequest(
            account_name="Salary Account",
            account_type="BANK",
            currency=invalid_currency,
            opening_balance="0.00",
        )

    assert exc_info.value.errors()[0]["loc"] == ("currency",)


@pytest.mark.parametrize("currency", ["INR", "usd", " Eur "])
def test_create_account_request_accepts_three_letter_currency_codes(
    currency: str,
) -> None:
    request = CreateAccountRequest(
        account_name="Multi Currency Account",
        account_type="BANK",
        currency=currency,
        opening_balance="0.00",
    )

    assert len(request.currency) == 3
    assert request.currency == currency.strip().upper()


def test_create_account_request_rejects_non_digit_last_four_digits() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CreateAccountRequest(
            account_name="Salary Account",
            account_type="BANK",
            last_four_digits="ABCD",
            opening_balance="0.00",
        )

    assert exc_info.value.errors()[0]["loc"] == ("last_four_digits",)


def test_update_account_request_accepts_partial_updates() -> None:
    request = UpdateAccountRequest(
        account_name="Updated Salary Account",
        status="ACTIVE",
        opening_balance="100.00",
    )

    assert request.account_name == "Updated Salary Account"
    assert request.status is AccountStatus.ACTIVE
    assert request.opening_balance == Decimal("100.00")


def test_update_account_request_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UpdateAccountRequest(status="DELETED")

    assert exc_info.value.errors()[0]["loc"] == ("status",)


def test_update_account_request_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UpdateAccountRequest()

    assert "At least one account field must be provided" in str(exc_info.value)


def test_account_response_serializes_money_as_strings_inside_success_envelope() -> None:
    account = Account(
        id=uuid4(),
        user_id=uuid4(),
        account_name="Salary Account",
        account_type="BANK",
        bank_name="ICICI",
        last_four_digits="0452",
        currency="INR",
        opening_balance=Decimal("100.00"),
        estimated_balance=Decimal("125.5"),
        status="ACTIVE",
    )

    response = AccountResponse(data=AccountResponseData.from_account(account))
    payload = response.model_dump(mode="json")

    assert payload == {
        "success": True,
        "data": {
            "id": str(account.id),
            "account_name": "Salary Account",
            "account_type": "BANK",
            "bank_name": "ICICI",
            "last_four_digits": "0452",
            "currency": "INR",
            "opening_balance": "100.00",
            "estimated_balance": "125.50",
            "status": "ACTIVE",
        },
    }
