"""HDFC Bank SMS parser."""

from app.parser.banks.generic import GenericParser


class HDFCParser(GenericParser):
    """Parser for HDFC Bank messages."""

    name = "hdfc"
    bank_name = "HDFC"
    sender_tokens = ("HDFC", "HDFCBK", "HDFCBANK")

    def matches(self, sender: str | None, message_text: str) -> bool:
        """Match the bank token against the sender ID."""
        haystack = self.match_haystack(sender, message_text)
        return any(token in haystack for token in self.sender_tokens)
