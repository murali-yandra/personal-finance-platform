"""ICICI Bank SMS parser."""

from app.parser.banks.generic import GenericParser


class ICICIParser(GenericParser):
    """Parser for ICICI Bank messages."""

    name = "icici"
    bank_name = "ICICI"
    sender_tokens = ("ICICI", "ICICIB", "ICICIBK")

    def matches(self, sender: str | None, message_text: str) -> bool:
        """Match the bank token against the sender ID."""
        haystack = self.match_haystack(sender, message_text)
        return any(token in haystack for token in self.sender_tokens)
