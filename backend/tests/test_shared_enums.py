"""Guard the controlled vocabularies against drift from the approved schema.

Values come from ``architecture/04-database_schema.md`` section 3. A silent rename
here would let invalid strings reach the database, which stores these as plain text.
"""

from app.shared.enums import (
    ASSET_ACCOUNT_TYPES,
    LIABILITY_ACCOUNT_TYPES,
    AccountStatus,
    AccountType,
    AuditAction,
    AuditSource,
    BusinessType,
    FeedbackType,
    NotificationMode,
    PatternType,
    ProcessingStatus,
    SourceType,
    TransactionDirection,
    TransferType,
)


def test_account_type_matches_schema() -> None:
    assert {member.value for member in AccountType} == {
        "BANK",
        "CREDIT_CARD",
        "CASH",
        "INVESTMENT",
        "LOAN",
    }


def test_wallet_is_not_an_account_type() -> None:
    """Sprint 2 architecture decision: cash wallets are represented as CASH."""
    assert "WALLET" not in {member.value for member in AccountType}


def test_account_status_matches_schema() -> None:
    assert {member.value for member in AccountStatus} == {
        "PENDING",
        "ACTIVE",
        "ARCHIVED",
        "DISABLED",
    }


def test_source_type_matches_schema() -> None:
    assert {member.value for member in SourceType} == {
        "SMS",
        "TELEGRAM",
        "EMAIL",
        "CSV",
        "AA",
        "API",
        "MANUAL",
    }


def test_processing_status_matches_schema() -> None:
    assert {member.value for member in ProcessingStatus} == {
        "RECEIVED",
        "PARSED",
        "PROCESSED",
        "DUPLICATE",
        "IGNORED",
        "FAILED",
        "UNKNOWN_FORMAT",
        "NEEDS_REVIEW",
    }


def test_transaction_direction_matches_schema() -> None:
    assert {member.value for member in TransactionDirection} == {"DEBIT", "CREDIT"}


def test_business_type_matches_schema() -> None:
    assert {member.value for member in BusinessType} == {
        "EXPENSE",
        "INCOME",
        "TRANSFER",
        "REFUND",
        "INVESTMENT",
        "LOAN",
        "EMI",
        "FEE",
        "INTEREST",
        "CASHBACK",
        "UNKNOWN",
    }


def test_feedback_type_matches_schema() -> None:
    assert {member.value for member in FeedbackType} == {
        "CATEGORY_CHANGE",
        "MERCHANT_CHANGE",
        "DESCRIPTION_UPDATE",
        "ACCOUNT_UPDATE",
        "BUSINESS_TYPE_CHANGE",
        "TRANSFER_LINK",
        "BALANCE_RECONCILIATION",
    }


def test_audit_source_matches_schema() -> None:
    assert {member.value for member in AuditSource} == {
        "USER",
        "SYSTEM",
        "TELEGRAM",
        "AI",
        "IMPORT",
        "AA",
        "API",
    }


def test_audit_action_includes_financial_actions() -> None:
    action_values = {member.value for member in AuditAction}
    assert {
        "CREATE",
        "UPDATE",
        "DELETE",
        "CATEGORY_CHANGE",
        "MERCHANT_CHANGE",
        "BALANCE_RECONCILIATION",
    } <= action_values


def test_notification_mode_matches_schema() -> None:
    assert {member.value for member in NotificationMode} == {
        "ALWAYS",
        "LOW_CONFIDENCE_ONLY",
        "DAILY_SUMMARY",
        "WEEKLY_SUMMARY",
        "DISABLED",
    }


def test_pattern_type_matches_schema() -> None:
    assert {member.value for member in PatternType} == {
        "EXACT",
        "LIKE",
        "REGEX",
        "AI_SUGGESTED",
    }


def test_transfer_type_matches_schema() -> None:
    assert {member.value for member in TransferType} == {
        "INTERNAL",
        "CREDIT_CARD_PAYMENT",
        "CASH_WITHDRAWAL",
        "ACCOUNT_TRANSFER",
        "LOAN_PAYMENT",
    }


def test_asset_and_liability_types_partition_account_types() -> None:
    assert ASSET_ACCOUNT_TYPES | LIABILITY_ACCOUNT_TYPES == set(AccountType)
    assert not ASSET_ACCOUNT_TYPES & LIABILITY_ACCOUNT_TYPES


def test_enums_compare_equal_to_plain_strings() -> None:
    """StrEnum members must round-trip through the database as plain strings."""
    assert AccountType.BANK == "BANK"
    assert f"{AccountStatus.ACTIVE}" == "ACTIVE"
