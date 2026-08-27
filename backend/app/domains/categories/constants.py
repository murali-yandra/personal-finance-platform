"""Seed data for system categories.

The list is the one approved in ``04-database_schema.md`` section 6. Changing it
means changing that document first: these names are referenced by the merchant
seed defaults and by reporting.
"""

DEFAULT_SYSTEM_CATEGORIES: tuple[str, ...] = (
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Travel",
    "Entertainment",
    "Salary",
    "Investment",
    "Transfer",
    "Loan",
    "EMI",
    "Refund",
    "Miscellaneous",
)
