"""Controlled vocabularies shared across domains.

Values mirror the enum definitions in ``architecture/04-database_schema.md`` section 3.
The database stores these as controlled strings, so application-layer validation is the
only enforcement point.
"""

from enum import StrEnum


class AccountType(StrEnum):
    """Supported financial account types."""

    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"


class AccountStatus(StrEnum):
    """Lifecycle states for an account."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DISABLED = "DISABLED"


class SourceType(StrEnum):
    """Origin of an ingested raw event."""

    SMS = "SMS"
    TELEGRAM = "TELEGRAM"
    EMAIL = "EMAIL"
    CSV = "CSV"
    AA = "AA"
    API = "API"
    MANUAL = "MANUAL"


class ProcessingStatus(StrEnum):
    """Processing lifecycle of a raw event."""

    RECEIVED = "RECEIVED"
    PARSED = "PARSED"
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
    UNKNOWN_FORMAT = "UNKNOWN_FORMAT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class TransactionDirection(StrEnum):
    """Direction of money movement relative to the account."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class BusinessType(StrEnum):
    """Financial classification of a transaction."""

    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"
    EMI = "EMI"
    FEE = "FEE"
    INTEREST = "INTEREST"
    CASHBACK = "CASHBACK"
    UNKNOWN = "UNKNOWN"


class TransactionStatus(StrEnum):
    """Lifecycle states for a transaction."""

    ACTIVE = "ACTIVE"
    REVERSED = "REVERSED"
    VOID = "VOID"


class FeedbackType(StrEnum):
    """Kinds of user correction captured as feedback."""

    CATEGORY_CHANGE = "CATEGORY_CHANGE"
    MERCHANT_CHANGE = "MERCHANT_CHANGE"
    DESCRIPTION_UPDATE = "DESCRIPTION_UPDATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    BUSINESS_TYPE_CHANGE = "BUSINESS_TYPE_CHANGE"
    TRANSFER_LINK = "TRANSFER_LINK"
    BALANCE_RECONCILIATION = "BALANCE_RECONCILIATION"


class AuditSource(StrEnum):
    """Actor that triggered an audited change."""

    USER = "USER"
    SYSTEM = "SYSTEM"
    TELEGRAM = "TELEGRAM"
    AI = "AI"
    IMPORT = "IMPORT"
    AA = "AA"
    API = "API"


class AuditAction(StrEnum):
    """Audited action names."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    CATEGORY_CHANGE = "CATEGORY_CHANGE"
    MERCHANT_CHANGE = "MERCHANT_CHANGE"
    DESCRIPTION_UPDATE = "DESCRIPTION_UPDATE"
    ACCOUNT_UPDATE = "ACCOUNT_UPDATE"
    BALANCE_RECONCILIATION = "BALANCE_RECONCILIATION"
    RULE_CREATED = "RULE_CREATED"
    RULE_UPDATED = "RULE_UPDATED"


class UserRole(StrEnum):
    """Platform roles. Checked on the JWT claim, not read from the request."""

    USER = "USER"
    ADMIN = "ADMIN"


class NotificationMode(StrEnum):
    """User notification preferences."""

    ALWAYS = "ALWAYS"
    LOW_CONFIDENCE_ONLY = "LOW_CONFIDENCE_ONLY"
    DAILY_SUMMARY = "DAILY_SUMMARY"
    WEEKLY_SUMMARY = "WEEKLY_SUMMARY"
    DISABLED = "DISABLED"


class PatternType(StrEnum):
    """Merchant pattern matching strategies."""

    EXACT = "EXACT"
    LIKE = "LIKE"
    REGEX = "REGEX"
    AI_SUGGESTED = "AI_SUGGESTED"


class TransferType(StrEnum):
    """Kinds of internal transfer between accounts."""

    INTERNAL = "INTERNAL"
    CREDIT_CARD_PAYMENT = "CREDIT_CARD_PAYMENT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    ACCOUNT_TRANSFER = "ACCOUNT_TRANSFER"
    LOAN_PAYMENT = "LOAN_PAYMENT"


ASSET_ACCOUNT_TYPES = frozenset(
    {
        AccountType.BANK,
        AccountType.CASH,
        AccountType.INVESTMENT,
    }
)

LIABILITY_ACCOUNT_TYPES = frozenset(
    {
        AccountType.CREDIT_CARD,
        AccountType.LOAN,
    }
)
