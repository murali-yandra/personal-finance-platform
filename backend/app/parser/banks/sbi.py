"""State Bank of India SMS parser."""

import re

from app.parser.banks.generic import GenericParser

# "SBI" appears inside unrelated words, so require a token boundary.
SBI_TOKEN_PATTERN = re.compile(r"(?:^|[^A-Z])(SBI|SBIINB|SBIUPI|SBICRD)(?:[^A-Z]|$)")


class SBIParser(GenericParser):
    """Parser for State Bank of India messages."""

    name = "sbi"
    bank_name = "SBI"
    sender_tokens = ("SBI", "SBIINB", "SBIUPI", "SBICRD")

    def matches(self, sender: str | None, message_text: str) -> bool:
        """Match the SBI token against the sender ID, with a boundary check."""
        haystack = self.match_haystack(sender, message_text)
        return SBI_TOKEN_PATTERN.search(haystack) is not None
