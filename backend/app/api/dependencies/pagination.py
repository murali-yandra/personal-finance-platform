from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class Pagination:
    """Validated pagination window for list endpoints."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        """Return the zero-based row offset for this page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Return the maximum number of rows for this page."""
        return self.page_size


def get_pagination(
    page: int = Query(default=DEFAULT_PAGE, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> Pagination:
    """Build the pagination window from query parameters."""
    return Pagination(page=page, page_size=page_size)
