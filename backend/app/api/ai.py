from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.ai.factory import build_ai_provider
from app.ai.schemas.suggestions import SuggestionStatus
from app.ai.services.learning_service import LearningService
from app.api.dependencies.auth import get_current_user
from app.config import get_settings
from app.db.session import get_session
from app.domains.ai.models import AISuggestion, UserFeedback
from app.domains.ai.repository import SuggestionRepository
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.service import MerchantService
from app.domains.users.models import User
from app.shared.exceptions.base import ApplicationError
from app.shared.schemas.responses import SuccessResponse

router = APIRouter(prefix="/ai", tags=["ai"])


class SuggestionNotFoundError(ApplicationError):
    """Raised when a suggestion is missing or owned by another user."""

    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message="Suggestion not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class SuggestionData(BaseModel):
    """Response data for one AI suggestion."""

    id: UUID
    transaction_id: UUID | None
    suggestion_type: str
    suggested_value: str
    confidence_score: Decimal | None
    status: str
    model_name: str | None
    created_at: datetime

    @classmethod
    def from_suggestion(cls, suggestion: AISuggestion) -> "SuggestionData":
        """Build the response payload from a stored suggestion."""
        return cls(
            id=suggestion.id,
            transaction_id=suggestion.transaction_id,
            suggestion_type=suggestion.suggestion_type,
            suggested_value=suggestion.suggested_value,
            confidence_score=suggestion.confidence_score,
            status=suggestion.status,
            model_name=suggestion.model_name,
            created_at=suggestion.created_at,
        )


class FeedbackData(BaseModel):
    """Response data for one recorded correction."""

    id: UUID
    transaction_id: UUID | None
    feedback_type: str
    old_value: str | None
    new_value: str | None
    created_at: datetime

    @classmethod
    def from_feedback(cls, feedback: UserFeedback) -> "FeedbackData":
        """Build the response payload from stored feedback."""
        return cls(
            id=feedback.id,
            transaction_id=feedback.transaction_id,
            feedback_type=feedback.feedback_type,
            old_value=feedback.old_value,
            new_value=feedback.new_value,
            created_at=feedback.created_at,
        )


class ReviewSuggestionRequest(BaseModel):
    """Request body for accepting or rejecting a suggestion."""

    accepted: bool


class MerchantCorrectionRequest(BaseModel):
    """Request body for correcting a merchant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    merchant_raw: str = Field(min_length=1, max_length=255)
    corrected_merchant_name: str = Field(min_length=1, max_length=255)
    transaction_id: UUID | None = None


class AIStatusData(BaseModel):
    """Response data describing the AI configuration."""

    enabled: bool
    provider: str
    available: bool


SuggestionListResponse = SuccessResponse[list[SuggestionData]]
SuggestionResponse = SuccessResponse[SuggestionData]
FeedbackResponse = SuccessResponse[FeedbackData]
FeedbackListResponse = SuccessResponse[list[FeedbackData]]
AIStatusResponse = SuccessResponse[AIStatusData]


def get_suggestion_repository(
    session: Annotated[Session, Depends(get_session)],
) -> SuggestionRepository:
    """Build the suggestion repository dependency."""
    return SuggestionRepository(session)


def get_learning_service(
    session: Annotated[Session, Depends(get_session)],
) -> LearningService:
    """Build the learning service dependency."""
    return LearningService(
        repository=SuggestionRepository(session),
        merchant_service=MerchantService(repository=MerchantRepository(session)),
    )


@router.get("/status", response_model=AIStatusResponse)
def ai_status(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIStatusResponse:
    """Report whether AI is enabled and whether the provider answers."""
    settings = get_settings()
    provider = build_ai_provider(settings)
    return AIStatusResponse(
        data=AIStatusData(
            enabled=settings.enable_ai,
            provider=provider.name,
            available=provider.is_available() if settings.enable_ai else False,
        )
    )


@router.get("/suggestions", response_model=SuggestionListResponse)
def list_suggestions(
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[SuggestionRepository, Depends(get_suggestion_repository)],
    suggestion_status: Annotated[str | None, Query(alias="status")] = None,
) -> SuggestionListResponse:
    """List the caller's stored suggestions."""
    suggestions = repository.list_suggestions(
        user_id=current_user.id,
        status=suggestion_status,
    )
    return SuggestionListResponse(
        data=[SuggestionData.from_suggestion(item) for item in suggestions]
    )


@router.post("/suggestions/{suggestion_id}/review", response_model=SuggestionResponse)
def review_suggestion(
    suggestion_id: UUID,
    request: ReviewSuggestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[SuggestionRepository, Depends(get_suggestion_repository)],
) -> SuggestionResponse:
    """Accept or reject a suggestion.

    Suggestions are never applied silently: the user decides
    (``13-ai_integration_standards.md`` section 9).
    """
    suggestion = repository.get_suggestion(
        suggestion_id=suggestion_id,
        user_id=current_user.id,
    )
    if suggestion is None:
        raise SuggestionNotFoundError()

    repository.mark_reviewed(
        suggestion,
        (
            SuggestionStatus.ACCEPTED.value
            if request.accepted
            else SuggestionStatus.REJECTED.value
        ),
    )
    repository.commit()
    repository.refresh(suggestion)
    return SuggestionResponse(data=SuggestionData.from_suggestion(suggestion))


@router.get("/feedback", response_model=FeedbackListResponse)
def list_feedback(
    current_user: Annotated[User, Depends(get_current_user)],
    repository: Annotated[SuggestionRepository, Depends(get_suggestion_repository)],
) -> FeedbackListResponse:
    """List the caller's recorded corrections."""
    return FeedbackListResponse(
        data=[
            FeedbackData.from_feedback(item)
            for item in repository.list_feedback(current_user.id)
        ]
    )


@router.post(
    "/feedback/merchant",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def correct_merchant(
    request: MerchantCorrectionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    learning_service: Annotated[LearningService, Depends(get_learning_service)],
) -> FeedbackResponse:
    """Record a merchant correction and learn a rule from it.

    The rule is owned by the correcting user, so one person's preference never
    reclassifies anyone else's history.
    """
    feedback = learning_service.learn_merchant_correction(
        user_id=current_user.id,
        merchant_raw=request.merchant_raw,
        corrected_merchant_name=request.corrected_merchant_name,
        transaction_id=request.transaction_id,
    )
    return FeedbackResponse(data=FeedbackData.from_feedback(feedback))
