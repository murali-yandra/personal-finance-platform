"""Prompt templates.

Versioned per ``13-ai_integration_standards.md`` section 16, so a stored
suggestion can be traced to the prompt that produced it.

Prompts carry only the merchant string and amount. Account numbers, balances and
raw message text are never sent to a model
(``13-ai_integration_standards.md`` section 26).
"""

from decimal import Decimal

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = (
    "You classify Indian bank transactions. "
    "Reply with JSON only, in the form "
    '{"value": "<answer>", "confidence": <0.0-1.0>, "reasoning": "<short>"}. '
    "Do not add any text outside the JSON object."
)


def build_merchant_prompt(merchant_raw: str) -> str:
    """Build the prompt that normalizes a raw merchant string."""
    return (
        "Normalize this raw merchant string from a bank SMS into the "
        "well-known business name.\n"
        f"Raw merchant: {merchant_raw}\n"
        'Example: "UPISWIGGY@ICICI" becomes "Swiggy".\n'
        "If you cannot tell, use a confidence below 0.5."
    )


def build_category_prompt(
    merchant_name: str,
    amount: Decimal,
    allowed_categories: list[str],
) -> str:
    """Build the prompt that assigns a category.

    The allowed list is included so the model picks from real categories, and
    the response validator rejects anything outside it regardless.
    """
    categories = ", ".join(sorted(allowed_categories))
    return (
        "Choose the best spending category for this transaction.\n"
        f"Merchant: {merchant_name}\n"
        f"Amount: INR {amount}\n"
        f"Allowed categories: {categories}\n"
        "The value must be exactly one of the allowed categories."
    )
