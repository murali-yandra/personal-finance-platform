"""Merchant normalization (Sprint 6)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.domains.merchants.exceptions import (
    MerchantNotFoundError,
    MerchantPatternValidationError,
)
from app.domains.merchants.models import MerchantPattern
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.resolver import resolve_merchant
from app.domains.merchants.service import MerchantService
from app.domains.users.models import User, UserSettings
from app.shared.enums import PatternType
from tests.conftest import authorization_header, register_user

SWIGGY_ID = uuid4()
AMAZON_ID = uuid4()


def _pattern(
    pattern: str,
    pattern_type: PatternType = PatternType.LIKE,
    merchant_id=SWIGGY_ID,
    user_id=None,
) -> MerchantPattern:
    return MerchantPattern(
        user_id=user_id,
        merchant_id=merchant_id,
        pattern=pattern,
        pattern_type=pattern_type.value,
        confidence=Decimal("1.00"),
    )


# -------------------------------------------------------------------- resolver


def test_roadmap_example_upiswiggy_resolves_to_swiggy() -> None:
    """14-sprint_roadmap.md section 11: UPISWIGGY@ICICI resolves to Swiggy."""
    match = resolve_merchant("UPISWIGGY@ICICI", [_pattern("%SWIGGY%")])

    assert match is not None
    assert match.merchant_id == SWIGGY_ID


def test_exact_pattern_matches_case_insensitively() -> None:
    match = resolve_merchant("swiggy", [_pattern("SWIGGY", PatternType.EXACT)])

    assert match is not None


def test_exact_pattern_does_not_match_a_substring() -> None:
    match = resolve_merchant(
        "SWIGGY INSTAMART",
        [_pattern("SWIGGY", PatternType.EXACT)],
    )

    assert match is None


def test_like_pattern_treats_percent_as_a_wildcard() -> None:
    assert resolve_merchant("KA51AJ1234", [_pattern("KA51AJ%")]) is not None


def test_like_pattern_treats_underscore_as_one_character() -> None:
    assert resolve_merchant("SWIGGY1", [_pattern("SWIGGY_")]) is not None
    assert resolve_merchant("SWIGGY12", [_pattern("SWIGGY_")]) is None


def test_regex_pattern_matches() -> None:
    match = resolve_merchant(
        "UPI-SWIGGY-412233",
        [_pattern(r"SWIGGY-\d+", PatternType.REGEX)],
    )

    assert match is not None


def test_exact_beats_like() -> None:
    """A literal match is stronger evidence than a wildcard."""
    patterns = [
        _pattern("%SWIG%", PatternType.LIKE, merchant_id=AMAZON_ID),
        _pattern("SWIGGY", PatternType.EXACT, merchant_id=SWIGGY_ID),
    ]

    match = resolve_merchant("SWIGGY", patterns)

    assert match.merchant_id == SWIGGY_ID


def test_like_beats_regex() -> None:
    patterns = [
        _pattern(".*", PatternType.REGEX, merchant_id=AMAZON_ID),
        _pattern("%SWIGGY%", PatternType.LIKE, merchant_id=SWIGGY_ID),
    ]

    match = resolve_merchant("MY SWIGGY ORDER", patterns)

    assert match.merchant_id == SWIGGY_ID


def test_user_pattern_overrides_a_global_pattern() -> None:
    """A personal correction must never be overridden by a shared rule."""
    user_id = uuid4()
    patterns = [
        _pattern("%SWIGGY%", PatternType.LIKE, merchant_id=AMAZON_ID),
        _pattern(
            "%SWIGGY%",
            PatternType.LIKE,
            merchant_id=SWIGGY_ID,
            user_id=user_id,
        ),
    ]

    match = resolve_merchant("UPISWIGGY@ICICI", patterns)

    assert match.merchant_id == SWIGGY_ID


def test_user_pattern_wins_even_when_the_global_one_is_more_specific() -> None:
    user_id = uuid4()
    patterns = [
        _pattern("UPISWIGGY@ICICI", PatternType.EXACT, merchant_id=AMAZON_ID),
        _pattern(
            "%SWIGGY%",
            PatternType.LIKE,
            merchant_id=SWIGGY_ID,
            user_id=user_id,
        ),
    ]

    match = resolve_merchant("UPISWIGGY@ICICI", patterns)

    assert match.merchant_id == SWIGGY_ID


def test_longer_pattern_wins_within_the_same_type() -> None:
    patterns = [
        _pattern("%S%", PatternType.LIKE, merchant_id=AMAZON_ID),
        _pattern("%SWIGGY%", PatternType.LIKE, merchant_id=SWIGGY_ID),
    ]

    match = resolve_merchant("SWIGGY", patterns)

    assert match.merchant_id == SWIGGY_ID


def test_no_match_returns_none_rather_than_guessing() -> None:
    """A wrongly attributed merchant corrupts every report grouped by merchant."""
    assert resolve_merchant("UNKNOWN VENDOR", [_pattern("%SWIGGY%")]) is None


def test_empty_input_resolves_to_nothing() -> None:
    assert resolve_merchant(None, [_pattern("%SWIGGY%")]) is None
    assert resolve_merchant("   ", [_pattern("%SWIGGY%")]) is None


def test_an_invalid_stored_regex_does_not_break_other_patterns() -> None:
    """Patterns can be user-supplied, so one bad expression must not be fatal."""
    patterns = [
        _pattern("[unclosed", PatternType.REGEX, merchant_id=AMAZON_ID),
        _pattern("%SWIGGY%", PatternType.LIKE, merchant_id=SWIGGY_ID),
    ]

    match = resolve_merchant("SWIGGY ORDER", patterns)

    assert match.merchant_id == SWIGGY_ID


# --------------------------------------------------------------------- service


@pytest.fixture
def user(db_session: Session) -> User:
    created = User(
        email="owner@example.com",
        password_hash="hash",
        display_name="Owner",
    )
    db_session.add(created)
    db_session.add(UserSettings(user_id=created.id))
    db_session.commit()
    return created


@pytest.fixture
def service(db_session: Session) -> MerchantService:
    return MerchantService(repository=MerchantRepository(db_session))


def test_get_or_create_merchant_is_idempotent(service: MerchantService) -> None:
    first = service.get_or_create_merchant("Swiggy")
    second = service.get_or_create_merchant("  swiggy  ")

    assert first.id == second.id


def test_create_pattern_requires_an_existing_merchant(
    service: MerchantService,
) -> None:
    with pytest.raises(MerchantNotFoundError):
        service.create_pattern(
            user_id=None,
            merchant_id=uuid4(),
            pattern="%SWIGGY%",
        )


def test_create_pattern_rejects_an_invalid_regex(
    service: MerchantService,
) -> None:
    """Reject at write time rather than silently failing at every match."""
    merchant = service.get_or_create_merchant("Swiggy")

    with pytest.raises(MerchantPatternValidationError):
        service.create_pattern(
            user_id=None,
            merchant_id=merchant.id,
            pattern="[unclosed",
            pattern_type=PatternType.REGEX,
        )


def test_create_pattern_is_idempotent(
    service: MerchantService,
    user: User,
) -> None:
    merchant = service.get_or_create_merchant("Swiggy")

    first = service.create_pattern(
        user_id=user.id,
        merchant_id=merchant.id,
        pattern="%SWIGGY%",
    )
    second = service.create_pattern(
        user_id=user.id,
        merchant_id=merchant.id,
        pattern="%swiggy%",
    )

    assert first.id == second.id


def test_service_resolution_uses_user_and_global_patterns(
    service: MerchantService,
    user: User,
    db_session: Session,
) -> None:
    merchant = service.get_or_create_merchant("Swiggy")
    db_session.add(
        MerchantPattern(
            user_id=None,
            merchant_id=merchant.id,
            pattern="%SWIGGY%",
            pattern_type=PatternType.LIKE.value,
        )
    )
    db_session.commit()

    match = service.resolve(user.id, "UPISWIGGY@ICICI")

    assert match is not None
    assert match.merchant_id == merchant.id


def test_another_users_pattern_is_not_applied(
    service: MerchantService,
    user: User,
    db_session: Session,
) -> None:
    merchant = service.get_or_create_merchant("Swiggy")
    db_session.add(
        MerchantPattern(
            user_id=uuid4(),
            merchant_id=merchant.id,
            pattern="%SWIGGY%",
            pattern_type=PatternType.LIKE.value,
        )
    )
    db_session.commit()

    assert service.resolve(user.id, "UPISWIGGY@ICICI") is None


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_merchant_endpoints_require_authentication(
    auth_client: AsyncClient,
) -> None:
    assert (await auth_client.get("/api/v1/merchants")).status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_merchants(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    created = await auth_client.post(
        "/api/v1/merchants",
        json={"merchant_name": "Swiggy"},
        headers=headers,
    )
    assert created.status_code == 201

    listed = await auth_client.get("/api/v1/merchants", headers=headers)
    names = [item["merchant_name"] for item in listed.json()["data"]]
    assert "Swiggy" in names
    assert listed.json()["meta"]["total_records"] == 1


@pytest.mark.asyncio
async def test_create_merchant_pattern_endpoint(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    merchant = await auth_client.post(
        "/api/v1/merchants",
        json={"merchant_name": "Swiggy"},
        headers=headers,
    )
    merchant_id = merchant.json()["data"]["id"]

    response = await auth_client.post(
        "/api/v1/merchants/patterns",
        json={"merchant_id": merchant_id, "pattern": "%SWIGGY%"},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["pattern_type"] == "LIKE"
    assert data["is_global"] is False
    assert data["created_by"] == "USER"


@pytest.mark.asyncio
async def test_patterns_route_is_not_shadowed_by_the_id_route(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    """/merchants/patterns must not be parsed as /merchants/{merchant_id}."""
    _, headers = authenticated_user

    response = await auth_client.get("/api/v1/merchants/patterns", headers=headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_unknown_merchant_returns_not_found(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get(
        f"/api/v1/merchants/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MERCHANT_NOT_FOUND"


@pytest.mark.asyncio
async def test_pattern_list_excludes_other_users_patterns(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    merchant = await auth_client.post(
        "/api/v1/merchants",
        json={"merchant_name": "Swiggy"},
        headers=headers,
    )
    await auth_client.post(
        "/api/v1/merchants/patterns",
        json={"merchant_id": merchant.json()["data"]["id"], "pattern": "%SWIGGY%"},
        headers=headers,
    )

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get(
        "/api/v1/merchants/patterns",
        headers=intruder_headers,
    )

    assert response.json()["data"] == []
