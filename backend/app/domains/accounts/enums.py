from enum import StrEnum


class AccountType(StrEnum):
    """Controlled account type values from the approved architecture docs."""

    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"


class AccountStatus(StrEnum):
    """Controlled account status values from the approved architecture docs."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DISABLED = "DISABLED"
