"""Parser selection.

Bank parsers are tried in registration order and the generic parser runs last,
so adding a bank never changes how existing messages parse.
"""

from app.parser.banks.generic import GenericParser
from app.parser.banks.hdfc import HDFCParser
from app.parser.banks.icici import ICICIParser
from app.parser.banks.sbi import SBIParser
from app.parser.base import BaseParser, ParseResult


class ParserRegistry:
    """Selects the parser that should handle a message."""

    def __init__(
        self,
        parsers: list[BaseParser] | None = None,
        fallback: BaseParser | None = None,
    ) -> None:
        self._parsers = parsers if parsers is not None else []
        self._fallback = fallback or GenericParser()

    def register(self, parser: BaseParser) -> None:
        """Add a bank parser ahead of the fallback."""
        self._parsers.append(parser)

    def select(self, sender: str | None, message_text: str) -> BaseParser:
        """Return the first parser that recognizes the message."""
        for parser in self._parsers:
            if parser.matches(sender, message_text):
                return parser
        return self._fallback

    def parse(self, sender: str | None, message_text: str) -> ParseResult:
        """Parse a message with the selected parser."""
        return self.select(sender, message_text).parse(sender, message_text)

    @property
    def parser_names(self) -> list[str]:
        """Return the registered parser names, fallback last."""
        return [parser.name for parser in self._parsers] + [self._fallback.name]


def build_default_registry() -> ParserRegistry:
    """Build the registry with every supported bank parser."""
    return ParserRegistry(
        parsers=[ICICIParser(), HDFCParser(), SBIParser()],
        fallback=GenericParser(),
    )


default_registry = build_default_registry()
