"""AI foundation and learning engine (Sprints 12 and 13)."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlmodel import Session, select

from app.ai.adapters.base import AIResponse, PromptRequest
from app.ai.adapters.fake import FakeAIProvider
from app.ai.factory import build_ai_provider
from app.ai.prompts.templates import (
    PROMPT_VERSION,
    build_category_prompt,
    build_merchant_prompt,
)
from app.ai.schemas.suggestions import (
    ConfidenceBand,
    Suggestion,
    SuggestionKind,
    SuggestionStatus,
)
from app.ai.services.learning_service import (
    LearningService,
    build_learned_pattern,
)
from app.ai.services.suggestion_service import AISuggestionService
from app.ai.validators.response import parse_suggestion
from app.config import get_settings
from app.domains.ai.models import AISuggestion, UserFeedback
from app.domains.ai.repository import SuggestionRepository
from app.domains.merchants.models import MerchantPattern
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.resolver import resolve_merchant
from app.domains.merchants.service import MerchantService
from app.domains.users.models import User, UserSettings
from app.shared.enums import FeedbackType

ALLOWED = ["Food", "Transport", "Shopping"]


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


# ------------------------------------------------------------------- validation


def test_parses_a_well_formed_response() -> None:
    suggestion = parse_suggestion(
        '{"value": "Swiggy", "confidence": 0.95}',
        SuggestionKind.MERCHANT,
    )

    assert suggestion.value == "Swiggy"
    assert suggestion.confidence == Decimal("0.95")


def test_extracts_json_wrapped_in_prose() -> None:
    """Models routinely add commentary around the JSON."""
    suggestion = parse_suggestion(
        'Sure! Here you go:\n{"value": "Swiggy", "confidence": 0.9}\nHope that helps.',
        SuggestionKind.MERCHANT,
    )

    assert suggestion.value == "Swiggy"


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "not json at all", "{broken", "[1, 2, 3]", '{"confidence": 0.9}'],
)
def test_unusable_responses_are_discarded(raw: str) -> None:
    """A fabricated suggestion corrupts financial history; an absent one does not."""
    assert parse_suggestion(raw, SuggestionKind.MERCHANT) is None


def test_percentage_confidence_is_normalized() -> None:
    """Models answer 85 when asked for 0.85."""
    suggestion = parse_suggestion(
        '{"value": "Swiggy", "confidence": 85}',
        SuggestionKind.MERCHANT,
    )

    assert suggestion.confidence == Decimal("0.85")


def test_out_of_range_confidence_is_rejected() -> None:
    assert (
        parse_suggestion(
            '{"value": "Swiggy", "confidence": -1}',
            SuggestionKind.MERCHANT,
        )
        is None
    )


def test_a_category_outside_the_allowed_set_is_discarded() -> None:
    """A model asked for a category will happily invent one."""
    suggestion = parse_suggestion(
        '{"value": "Groceries and Sundries", "confidence": 0.99}',
        SuggestionKind.CATEGORY,
        allowed_values=set(ALLOWED),
    )

    assert suggestion is None


def test_an_allowed_category_is_accepted_case_insensitively() -> None:
    suggestion = parse_suggestion(
        '{"value": "food", "confidence": 0.9}',
        SuggestionKind.CATEGORY,
        allowed_values=set(ALLOWED),
    )

    assert suggestion.value == "food"


# ------------------------------------------------------------------- confidence


@pytest.mark.parametrize(
    ("confidence", "band", "auto"),
    [
        (Decimal("0.95"), ConfidenceBand.HIGH, True),
        (Decimal("0.90"), ConfidenceBand.HIGH, True),
        (Decimal("0.80"), ConfidenceBand.MEDIUM, False),
        (Decimal("0.70"), ConfidenceBand.MEDIUM, False),
        (Decimal("0.40"), ConfidenceBand.LOW, False),
    ],
)
def test_confidence_bands(
    confidence: Decimal,
    band: ConfidenceBand,
    auto: bool,
) -> None:
    suggestion = Suggestion(
        kind=SuggestionKind.CATEGORY,
        value="Food",
        confidence=confidence,
    )

    assert suggestion.band is band
    assert suggestion.can_auto_apply is auto


# --------------------------------------------------------------------- prompts


def test_prompts_never_include_account_or_balance_details() -> None:
    """13-ai_integration_standards.md section 26: financial identifiers stay local."""
    merchant_prompt = build_merchant_prompt("UPISWIGGY@ICICI")
    category_prompt = build_category_prompt("Swiggy", Decimal("249.00"), ALLOWED)

    for prompt in (merchant_prompt, category_prompt):
        lowered = prompt.lower()
        assert "a/c" not in lowered
        assert "xxxx" not in lowered
        assert "balance" not in lowered


def test_category_prompt_lists_the_allowed_categories() -> None:
    prompt = build_category_prompt("Swiggy", Decimal("249.00"), ALLOWED)

    for category in ALLOWED:
        assert category in prompt


# -------------------------------------------------------------------- provider


def test_fake_provider_records_requests() -> None:
    provider = FakeAIProvider(responses=['{"value": "Swiggy", "confidence": 0.9}'])

    response = provider.complete(PromptRequest(prompt="hello"))

    assert response.succeeded
    assert len(provider.requests) == 1


def test_failure_is_a_value_not_an_exception() -> None:
    response = AIResponse.failure("provider down")

    assert response.succeeded is False
    assert response.text == ""


def test_factory_returns_an_unavailable_provider_when_disabled() -> None:
    settings = get_settings()
    original = settings.enable_ai
    settings.enable_ai = False
    try:
        provider = build_ai_provider(settings)
        assert provider.is_available() is False
    finally:
        settings.enable_ai = original


# --------------------------------------------------------------------- service


@pytest.fixture
def repository(db_session: Session) -> SuggestionRepository:
    return SuggestionRepository(db_session)


def test_merchant_suggestion_is_stored(
    db_session: Session,
    user: User,
    repository: SuggestionRepository,
) -> None:
    provider = FakeAIProvider(responses=['{"value": "Swiggy", "confidence": 0.95}'])
    service = AISuggestionService(provider, repository)

    suggestion = service.suggest_merchant(user.id, "UPISWIGGY@ICICI")

    assert suggestion.value == "Swiggy"
    stored = list(db_session.exec(select(AISuggestion)).all())
    assert len(stored) == 1
    assert stored[0].status == SuggestionStatus.PENDING
    assert stored[0].prompt_version == PROMPT_VERSION


def test_suggestions_are_stored_not_applied(
    db_session: Session,
    user: User,
    repository: SuggestionRepository,
) -> None:
    """The user decides; a wrong category corrupts every report."""
    provider = FakeAIProvider(responses=['{"value": "Swiggy", "confidence": 0.99}'])
    AISuggestionService(provider, repository).suggest_merchant(user.id, "SWIGGY")

    stored = list(db_session.exec(select(AISuggestion)).all())[0]
    assert stored.status == SuggestionStatus.PENDING
    assert stored.reviewed_at is None


def test_a_provider_outage_produces_no_suggestion_and_no_error(
    user: User,
    repository: SuggestionRepository,
) -> None:
    """13-ai_integration_standards.md section 22: AI failure must not block work."""
    provider = FakeAIProvider(should_fail=True)

    assert (
        AISuggestionService(provider, repository).suggest_merchant(user.id, "SWIGGY")
        is None
    )


def test_a_raising_provider_is_contained(
    user: User,
    repository: SuggestionRepository,
) -> None:
    class Exploding(FakeAIProvider):
        def complete(self, request):
            raise RuntimeError("boom")

    assert (
        AISuggestionService(Exploding(), repository).suggest_merchant(user.id, "SWIGGY")
        is None
    )


def test_disabled_service_never_calls_the_provider(
    user: User,
    repository: SuggestionRepository,
) -> None:
    provider = FakeAIProvider(responses=['{"value": "Swiggy", "confidence": 0.9}'])
    service = AISuggestionService(provider, repository, enabled=False)

    assert service.suggest_merchant(user.id, "SWIGGY") is None
    assert provider.requests == []


def test_category_suggestion_is_restricted_to_real_categories(
    user: User,
    repository: SuggestionRepository,
) -> None:
    provider = FakeAIProvider(
        responses=['{"value": "Invented Category", "confidence": 0.99}']
    )
    service = AISuggestionService(provider, repository)

    assert (
        service.suggest_category(user.id, "Swiggy", Decimal("249.00"), ALLOWED) is None
    )


# ------------------------------------------------------------- learning engine


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("KA51AJ1234", "%KA51AJ%"),
        ("KA51AJ5678", "%KA51AJ%"),
        ("UPISWIGGY@ICICI", "%UPISWIGGY@ICICI%"),
        ("SmartQ", "%SmartQ%"),
    ],
)
def test_learned_pattern_generalizes_the_varying_tail(
    raw: str,
    expected: str,
) -> None:
    """KA51AJ1234 and KA51AJ5678 are the same operator with different vehicles."""
    assert build_learned_pattern(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["KA51AJ1234", "UPISWIGGY@ICICI", "SmartQ", "AMAZON.IN", "PAY*NETFLIX"],
)
def test_a_learned_pattern_always_matches_what_it_learned_from(raw: str) -> None:
    """The essential guarantee: a rule that misses its own source is useless.

    Deriving from a punctuation-stripped string broke this: UPISWIGGY@ICICI
    yielded UPISWIGGYICICI%, which never matches the original.
    """
    from uuid import uuid4

    pattern = build_learned_pattern(raw)
    assert pattern is not None

    match = resolve_merchant(
        raw,
        [
            MerchantPattern(
                user_id=None,
                merchant_id=uuid4(),
                pattern=pattern,
                pattern_type="LIKE",
            )
        ],
    )
    assert match is not None


def test_literal_like_wildcards_do_not_widen_the_rule() -> None:
    """A % in a bank string is not a wildcard, and would match everything."""
    pattern = build_learned_pattern("50%OFF STORE")

    assert "%" not in pattern[1:-1]


def test_no_pattern_from_an_unusable_string() -> None:
    assert build_learned_pattern("") is None
    assert build_learned_pattern("ab") is None


def test_roadmap_example_learns_transport_from_a_correction(
    db_session: Session,
    user: User,
) -> None:
    """14-sprint_roadmap.md section 18: KA51AJ* becomes Transport."""
    merchant_service = MerchantService(repository=MerchantRepository(db_session))
    service = LearningService(
        repository=SuggestionRepository(db_session),
        merchant_service=merchant_service,
    )

    service.learn_merchant_correction(
        user_id=user.id,
        merchant_raw="KA51AJ1234",
        corrected_merchant_name="BMTC",
    )

    # A different vehicle from the same operator now resolves without asking.
    match = merchant_service.resolve(user.id, "KA51AJ9999")
    assert match is not None
    merchant = merchant_service.get_merchant(match.merchant_id)
    assert merchant.merchant_name == "BMTC"


def test_correction_records_feedback(db_session: Session, user: User) -> None:
    service = LearningService(
        repository=SuggestionRepository(db_session),
        merchant_service=MerchantService(repository=MerchantRepository(db_session)),
    )

    service.learn_merchant_correction(
        user_id=user.id,
        merchant_raw="UPISWIGGY@ICICI",
        corrected_merchant_name="Swiggy",
    )

    stored = list(db_session.exec(select(UserFeedback)).all())
    assert len(stored) == 1
    assert stored[0].feedback_type == FeedbackType.MERCHANT_CHANGE
    assert stored[0].new_value == "Swiggy"


def test_learned_rules_are_private_to_the_correcting_user(
    db_session: Session,
    user: User,
) -> None:
    """One person's preference must not reclassify everyone else's history."""
    merchant_service = MerchantService(repository=MerchantRepository(db_session))
    LearningService(
        repository=SuggestionRepository(db_session),
        merchant_service=merchant_service,
    ).learn_merchant_correction(
        user_id=user.id,
        merchant_raw="KA51AJ1234",
        corrected_merchant_name="BMTC",
    )

    patterns = list(db_session.exec(select(MerchantPattern)).all())
    assert len(patterns) == 1
    assert patterns[0].user_id == user.id
    assert patterns[0].created_by == "USER"


def test_a_learned_rule_outranks_a_global_one(db_session: Session, user: User) -> None:
    merchant_service = MerchantService(repository=MerchantRepository(db_session))
    wrong = merchant_service.get_or_create_merchant("Wrong Merchant")
    db_session.add(
        MerchantPattern(
            user_id=None,
            merchant_id=wrong.id,
            pattern="KA51%",
            pattern_type="LIKE",
        )
    )
    db_session.commit()

    LearningService(
        repository=SuggestionRepository(db_session),
        merchant_service=merchant_service,
    ).learn_merchant_correction(
        user_id=user.id,
        merchant_raw="KA51AJ1234",
        corrected_merchant_name="BMTC",
    )

    patterns = merchant_service.list_patterns(user.id)
    match = resolve_merchant("KA51AJ1234", patterns)
    assert merchant_service.get_merchant(match.merchant_id).merchant_name == "BMTC"


# -------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_ai_endpoints_require_authentication(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/api/v1/ai/suggestions")).status_code == 401


@pytest.mark.asyncio
async def test_ai_status_reports_disabled_by_default(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.get("/api/v1/ai/status", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["enabled"] is False
    assert response.json()["data"]["available"] is False


@pytest.mark.asyncio
async def test_merchant_correction_endpoint_learns_a_rule(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user

    response = await auth_client.post(
        "/api/v1/ai/feedback/merchant",
        json={
            "merchant_raw": "KA51AJ1234",
            "corrected_merchant_name": "BMTC",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["new_value"] == "BMTC"

    patterns = await auth_client.get("/api/v1/merchants/patterns", headers=headers)
    assert any(
        item["pattern"] == "%KA51AJ%" for item in patterns.json()["data"]
    ), patterns.json()


@pytest.mark.asyncio
async def test_feedback_is_listed_for_its_owner_only(
    auth_client: AsyncClient,
    authenticated_user: tuple,
) -> None:
    _, headers = authenticated_user
    await auth_client.post(
        "/api/v1/ai/feedback/merchant",
        json={"merchant_raw": "SMARTQ", "corrected_merchant_name": "SmartQ"},
        headers=headers,
    )

    from tests.conftest import authorization_header, register_user

    intruder_id = await register_user(auth_client, email="intruder@example.com")
    intruder_headers = authorization_header(intruder_id, email="intruder@example.com")

    response = await auth_client.get("/api/v1/ai/feedback", headers=intruder_headers)

    assert response.json()["data"] == []
