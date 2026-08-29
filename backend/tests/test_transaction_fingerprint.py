"""Transaction-level duplicate detection (04-database_schema.md section 7.2)."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from app.domains.transactions.fingerprint import build_transaction_fingerprint

USER_ID = uuid4()
ACCOUNT_ID = uuid4()
TIMESTAMP = datetime(2026, 6, 2, 10, 0, 0)


def _fingerprint(**overrides) -> str:
    fields = {
        "user_id": USER_ID,
        "account_id": ACCOUNT_ID,
        "amount": Decimal("70.00"),
        "direction": "DEBIT",
        "transaction_timestamp": TIMESTAMP,
        "merchant_raw": "SmartQ",
        "reference_number": "REF123",
    }
    fields.update(overrides)
    return build_transaction_fingerprint(**fields)


def test_fingerprint_is_deterministic() -> None:
    assert _fingerprint() == _fingerprint()


def test_fingerprint_is_a_sha256_hex_digest() -> None:
    value = _fingerprint()

    assert len(value) == 64
    assert set(value) <= set("0123456789abcdef")


def test_amount_formatting_does_not_change_identity() -> None:
    assert _fingerprint(amount=Decimal("70")) == _fingerprint(amount=Decimal("70.00"))


def test_merchant_case_and_punctuation_do_not_change_identity() -> None:
    assert _fingerprint(merchant_raw="smart-q") == _fingerprint(merchant_raw="SMART Q")


def test_seconds_drift_does_not_change_identity() -> None:
    """The same transaction is often reported seconds apart by SMS and statement."""
    drifted = TIMESTAMP.replace(second=47)

    assert _fingerprint(transaction_timestamp=drifted) == _fingerprint()


def test_different_amount_changes_identity() -> None:
    assert _fingerprint(amount=Decimal("71.00")) != _fingerprint()


def test_different_direction_changes_identity() -> None:
    assert _fingerprint(direction="CREDIT") != _fingerprint()


def test_different_account_changes_identity() -> None:
    assert _fingerprint(account_id=uuid4()) != _fingerprint()


def test_different_user_changes_identity() -> None:
    """Two users may legitimately hold the same transaction details."""
    assert _fingerprint(user_id=uuid4()) != _fingerprint()


def test_different_reference_number_changes_identity() -> None:
    assert _fingerprint(reference_number="REF999") != _fingerprint()


def test_different_minute_changes_identity() -> None:
    other = TIMESTAMP.replace(minute=31)

    assert _fingerprint(transaction_timestamp=other) != _fingerprint()


def test_missing_optional_fields_are_handled() -> None:
    value = build_transaction_fingerprint(
        user_id=USER_ID,
        account_id=ACCOUNT_ID,
        amount=Decimal("70.00"),
        direction="DEBIT",
        transaction_timestamp=None,
    )

    assert len(value) == 64


def test_empty_and_missing_merchant_are_equivalent() -> None:
    assert _fingerprint(merchant_raw=None) == _fingerprint(merchant_raw="   ")
