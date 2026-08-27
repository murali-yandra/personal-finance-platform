"""Parsing engine behaviour against representative bank SMS (Sprint 5)."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.parser import default_registry
from app.parser.banks import GenericParser, HDFCParser, ICICIParser, SBIParser
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
from app.parser.registry import ParserRegistry, build_default_registry
from app.shared.enums import BusinessType, TransactionDirection
from tests.fixtures.sms_samples import (
    NON_TRANSACTIONAL_SAMPLES,
    TRANSACTIONAL_SAMPLES,
    UNPARSEABLE_SAMPLES,
    SmsSample,
)

# ------------------------------------------------------------ end-to-end corpus


@pytest.mark.parametrize(
    "sample",
    TRANSACTIONAL_SAMPLES,
    ids=[sample.label for sample in TRANSACTIONAL_SAMPLES],
)
def test_sample_parses_successfully(sample: SmsSample) -> None:
    result = default_registry.parse(sample.sender, sample.message_text)

    assert result.succeeded, result.failure_reason
    assert result.parser_name == sample.expected_parser


@pytest.mark.parametrize(
    "sample",
    TRANSACTIONAL_SAMPLES,
    ids=[sample.label for sample in TRANSACTIONAL_SAMPLES],
)
def test_sample_amount_and_direction(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.amount == sample.expected_amount
    assert parsed.direction is sample.expected_direction


@pytest.mark.parametrize(
    "sample",
    TRANSACTIONAL_SAMPLES,
    ids=[sample.label for sample in TRANSACTIONAL_SAMPLES],
)
def test_sample_account_and_bank(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.bank_name == sample.expected_bank
    assert parsed.last_four_digits == sample.expected_last_four


@pytest.mark.parametrize(
    "sample",
    [s for s in TRANSACTIONAL_SAMPLES if s.expected_merchant],
    ids=[s.label for s in TRANSACTIONAL_SAMPLES if s.expected_merchant],
)
def test_sample_merchant(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.merchant_raw == sample.expected_merchant


@pytest.mark.parametrize(
    "sample",
    [s for s in TRANSACTIONAL_SAMPLES if s.expected_reference],
    ids=[s.label for s in TRANSACTIONAL_SAMPLES if s.expected_reference],
)
def test_sample_reference_number(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.reference_number == sample.expected_reference


@pytest.mark.parametrize(
    "sample",
    [s for s in TRANSACTIONAL_SAMPLES if s.expected_timestamp],
    ids=[s.label for s in TRANSACTIONAL_SAMPLES if s.expected_timestamp],
)
def test_sample_timestamp(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.transaction_timestamp == sample.expected_timestamp


@pytest.mark.parametrize(
    "sample",
    [s for s in TRANSACTIONAL_SAMPLES if s.expected_business_type],
    ids=[s.label for s in TRANSACTIONAL_SAMPLES if s.expected_business_type],
)
def test_sample_business_type(sample: SmsSample) -> None:
    parsed = default_registry.parse(sample.sender, sample.message_text).parsed

    assert parsed.business_type is sample.expected_business_type


def test_parser_accuracy_across_the_corpus() -> None:
    """14-sprint_roadmap.md section 26 targets parser accuracy above 90 percent."""
    succeeded = sum(
        1
        for sample in TRANSACTIONAL_SAMPLES
        if default_registry.parse(sample.sender, sample.message_text).succeeded
    )

    assert succeeded == len(TRANSACTIONAL_SAMPLES)


# --------------------------------------------------------- non-transactional


@pytest.mark.parametrize(
    ("label", "sender", "message_text"),
    NON_TRANSACTIONAL_SAMPLES,
    ids=[label for label, _, _ in NON_TRANSACTIONAL_SAMPLES],
)
def test_non_transactional_messages_are_not_parse_failures(
    label: str,
    sender: str,
    message_text: str,
) -> None:
    """OTPs and reminders quote amounts but are not transactions."""
    result = default_registry.parse(sender, message_text)

    assert result.succeeded is False
    assert result.is_transactional is False


@pytest.mark.parametrize(
    ("label", "sender", "message_text"),
    UNPARSEABLE_SAMPLES,
    ids=[label for label, _, _ in UNPARSEABLE_SAMPLES],
)
def test_unreadable_transactional_messages_fail_explicitly(
    label: str,
    sender: str,
    message_text: str,
) -> None:
    """A message that looks transactional but cannot be read must not be guessed."""
    result = default_registry.parse(sender, message_text)

    assert result.succeeded is False
    assert result.is_transactional is True
    assert result.failure_reason


# ------------------------------------------------------------------ registry


def test_registry_selects_the_bank_parser_by_token() -> None:
    assert isinstance(
        default_registry.select("VK-HDFCBK", "any text"),
        HDFCParser,
    )
    assert isinstance(default_registry.select("AD-ICICIB", "any text"), ICICIParser)
    assert isinstance(default_registry.select("JD-SBIINB", "any text"), SBIParser)


def test_registry_falls_back_to_the_generic_parser() -> None:
    assert isinstance(
        default_registry.select("AX-AXISBK", "Rs.10 debited"),
        GenericParser,
    )


def test_sender_prefix_changes_do_not_break_matching() -> None:
    """Circle and operator prefixes vary; the bank token does not."""
    for sender in ("VK-HDFCBK", "VM-HDFCBK", "AD-HDFCBK", "JM-HDFCBANK"):
        assert isinstance(default_registry.select(sender, "text"), HDFCParser)


def test_sbi_token_requires_a_boundary() -> None:
    """A bare substring must not claim the message for SBI."""
    parser = default_registry.select("AD-ICICIB", "Payment to SBIWALA STORE")

    assert not isinstance(parser, SBIParser)


def test_registry_order_puts_the_fallback_last() -> None:
    assert build_default_registry().parser_names[-1] == "generic"


def test_registered_parser_takes_priority_over_the_fallback() -> None:
    registry = ParserRegistry(parsers=[ICICIParser()], fallback=GenericParser())

    assert registry.select("AD-ICICIB", "text").name == "icici"
    assert registry.select("XX-OTHER", "text").name == "generic"


# ---------------------------------------------------------------- extractors


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rs.70.00 debited", Decimal("70.00")),
        ("Rs 1,899.50 spent", Decimal("1899.50")),
        ("INR 249 debited", Decimal("249.00")),
        ("₹1,234.56 paid", Decimal("1234.56")),
        ("Rs.85,000.00 credited", Decimal("85000.00")),
        ("Rs.1,02,345.00 credited", Decimal("102345.00")),
    ],
)
def test_extract_amount_handles_indian_formats(
    text: str,
    expected: Decimal,
) -> None:
    """Indian digit grouping is 2,2,3 rather than 3,3,3."""
    assert extract_amount(text) == expected


def test_amount_is_not_confused_by_a_larger_balance() -> None:
    """The balance is usually the larger, later number in the message."""
    text = "Rs.70.00 debited from A/C XXXX0452. Avl Bal Rs.12,345.67"

    assert extract_amount(text) == Decimal("70.00")


def test_available_balance_is_extracted_separately() -> None:
    text = "Rs.70.00 debited from A/C XXXX0452. Avl Bal Rs.12,345.67"

    assert extract_available_balance(text) == Decimal("12345.67")


def test_extract_amount_returns_none_without_an_amount() -> None:
    assert extract_amount("Your account was updated.") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rs.70 debited from A/c", TransactionDirection.DEBIT),
        ("Rs.70 credited to A/c", TransactionDirection.CREDIT),
        ("Rs.70 withdrawn from ATM", TransactionDirection.DEBIT),
        ("Rs.70 spent on card", TransactionDirection.DEBIT),
        ("Rs.70 received from Ravi", TransactionDirection.CREDIT),
        ("Rs.70 deposited to A/c", TransactionDirection.CREDIT),
    ],
)
def test_detect_direction(text: str, expected: TransactionDirection) -> None:
    assert detect_direction(text) is expected


def test_direction_uses_the_first_keyword() -> None:
    """Banks lead with the action; later mentions belong to advisory clauses."""
    text = "Rs.70 debited from A/c XX0452, amount will be credited back if disputed"

    assert detect_direction(text) is TransactionDirection.DEBIT


def test_detect_direction_returns_none_when_absent() -> None:
    assert detect_direction("Transaction of INR 500.00 processed") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A/C XXXX0452", "0452"),
        ("A/c XX0452", "0452"),
        ("Account XX1234", "1234"),
        ("Card xx9012", "9012"),
        ("A/c XXXXX7788", "7788"),
        ("****5566", "5566"),
    ],
)
def test_extract_account_digits(text: str, expected: str) -> None:
    assert extract_account_hint(text).last_four_digits == expected


def test_credit_card_messages_hint_at_a_credit_card_account() -> None:
    hint = extract_account_hint("spent on HDFC Bank Credit Card xx9012")

    assert hint.account_type_hint == "CREDIT_CARD"


def test_debit_card_messages_hint_at_a_bank_account() -> None:
    hint = extract_account_hint("withdrawn using Debit Card XX4321")

    assert hint.account_type_hint == "BANK"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("debited at SmartQ on 02-06-26", "SmartQ"),
        ("spent at AMAZON on 12-06-2026", "AMAZON"),
        ("credited as refund from FLIPKART", None),
        ("debited to VPA swiggy@icici on 03-06", "swiggy@icici"),
    ],
)
def test_extract_merchant(text: str, expected: str | None) -> None:
    assert extract_merchant(text) == expected


def test_merchant_is_returned_raw_without_normalization() -> None:
    """Mapping the raw string to a canonical merchant is Sprint 6's job."""
    assert extract_merchant("debited to VPA upiswiggy@icici on 1") == (
        "upiswiggy@icici"
    )


def test_extract_upi_id() -> None:
    assert extract_upi_id("debited to VPA swiggy@icici on 03") == "swiggy@icici"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Ref 998877", "998877"),
        ("Ref no 555444333", "555444333"),
        ("Ref: RFND12345", "RFND12345"),
        ("UPI Ref 412233445566", "412233445566"),
        ("Txn ID: ABC123XYZ", "ABC123XYZ"),
    ],
)
def test_extract_reference_number(text: str, expected: str) -> None:
    assert extract_reference_number(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("on 02-06-26 10:00", datetime(2026, 6, 2, 10, 0)),
        ("on 15-06-2026", datetime(2026, 6, 15, 0, 0)),
        ("on 12/06/2026 18:45", datetime(2026, 6, 12, 18, 45)),
        ("on 2026-06-20", datetime(2026, 6, 20, 0, 0)),
    ],
)
def test_extract_timestamp(text: str, expected: datetime) -> None:
    """Indian bank SMS use day-first dates."""
    assert extract_timestamp(text) == expected


def test_day_first_dates_are_not_read_as_month_first() -> None:
    """06-07-2026 is 6 July, not 7 June."""
    assert extract_timestamp("on 06-07-2026") == datetime(2026, 7, 6)


def test_timestamp_returns_none_without_a_date() -> None:
    assert extract_timestamp("debited at SmartQ") is None


def test_business_type_defaults_follow_direction() -> None:
    assert (
        detect_business_type("paid at shop", TransactionDirection.DEBIT)
        is BusinessType.EXPENSE
    )
    assert (
        detect_business_type("received money", TransactionDirection.CREDIT)
        is BusinessType.INCOME
    )


def test_is_non_transactional_flags_an_otp() -> None:
    assert is_non_transactional("123456 is your OTP for Rs.2500") is not None


def test_is_non_transactional_passes_a_real_transaction() -> None:
    assert is_non_transactional("Rs.70 debited from A/c XX0452") is None


# --------------------------------------------------------------- confidence


def test_confidence_rises_with_field_coverage() -> None:
    sparse = default_registry.parse("XX-OTHER", "Rs.70 debited").parsed
    rich = default_registry.parse(
        "VK-HDFCBK",
        "Rs.70.00 debited from A/C XXXX0452 at SmartQ on 02-06-26 10:00. Ref 998877",
    ).parsed

    assert rich.confidence_score > sparse.confidence_score


def test_confidence_never_exceeds_one() -> None:
    for sample in TRANSACTIONAL_SAMPLES:
        parsed = default_registry.parse(sample.sender, sample.message_text).parsed
        assert Decimal("0.00") <= parsed.confidence_score <= Decimal("1.00")


def test_parsers_do_not_touch_the_database() -> None:
    """Parsers are pure, which is what makes the corpus tests possible."""
    import inspect

    from app.parser.banks import generic

    source = inspect.getsource(generic)
    assert "Session" not in source
    assert "session" not in source


def test_a_bank_named_in_the_body_does_not_hijack_the_parser() -> None:
    """A UPI handle names the counterparty's provider, not the sender's bank.

    "swiggy@icici" in an HDFC message must not route it to the ICICI parser,
    or the transaction is attributed to the wrong bank.
    """
    result = default_registry.parse(
        "VK-HDFCBK",
        "Rs.150 debited from A/c XX0452 to VPA swiggy@icici on 03-06-2026.",
    )

    assert result.parser_name == "hdfc"
    assert result.parsed.bank_name == "HDFC"


def test_message_body_is_only_matched_when_no_sender_is_supplied() -> None:
    """Some ingestion sources omit the sender, so the body is the fallback."""
    parser = default_registry.select(None, "ICICI Bank Account XX1234 debited")

    assert parser.name == "icici"


def test_an_unknown_sender_falls_back_rather_than_guessing() -> None:
    parser = default_registry.select("AX-AXISBK", "Payment to ICICI merchant")

    assert parser.name == "generic"
