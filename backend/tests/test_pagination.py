import pytest

from app.api.dependencies.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Pagination,
    get_pagination,
)
from app.shared.schemas.responses import PageMeta, PaginatedResponse


def test_first_page_starts_at_zero_offset() -> None:
    pagination = Pagination(page=1, page_size=50)

    assert pagination.offset == 0
    assert pagination.limit == 50


@pytest.mark.parametrize(
    ("page", "page_size", "expected_offset"),
    [(1, 50, 0), (2, 50, 50), (3, 20, 40), (10, 1, 9)],
)
def test_offset_is_derived_from_page_and_size(
    page: int,
    page_size: int,
    expected_offset: int,
) -> None:
    assert Pagination(page=page, page_size=page_size).offset == expected_offset


def test_defaults_match_the_api_contract() -> None:
    """Defaults are declared as FastAPI Query objects, so assert the constants.

    Resolution of the dependency itself is covered by the list-endpoint tests.
    """
    assert DEFAULT_PAGE == 1
    assert DEFAULT_PAGE_SIZE == 50
    assert DEFAULT_PAGE_SIZE <= MAX_PAGE_SIZE


def test_pagination_dependency_is_registered_as_a_callable() -> None:
    assert callable(get_pagination)


def test_paginated_response_envelope_shape() -> None:
    response = PaginatedResponse[str](
        data=["a", "b"],
        meta=PageMeta(page=2, page_size=2, total_records=7),
    )

    assert response.model_dump() == {
        "success": True,
        "data": ["a", "b"],
        "meta": {"page": 2, "page_size": 2, "total_records": 7},
    }
