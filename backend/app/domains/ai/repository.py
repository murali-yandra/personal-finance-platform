from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.domains.ai.models import AISuggestion, UserFeedback


class SuggestionRepository:
    """Persistence for AI suggestions and user feedback."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_suggestion(self, suggestion: AISuggestion) -> AISuggestion:
        """Persist a suggestion."""
        self._session.add(suggestion)
        self._session.flush()
        return suggestion

    def get_suggestion(
        self,
        suggestion_id: UUID,
        user_id: UUID,
    ) -> AISuggestion | None:
        """Return a user-owned suggestion."""
        statement = select(AISuggestion).where(
            AISuggestion.id == suggestion_id,
            AISuggestion.user_id == user_id,
        )
        return self._session.exec(statement).first()

    def list_suggestions(
        self,
        user_id: UUID,
        status: str | None = None,
        transaction_id: UUID | None = None,
    ) -> list[AISuggestion]:
        """Return a user's suggestions, newest first."""
        statement = select(AISuggestion).where(AISuggestion.user_id == user_id)
        if status is not None:
            statement = statement.where(AISuggestion.status == status)
        if transaction_id is not None:
            statement = statement.where(AISuggestion.transaction_id == transaction_id)
        statement = statement.order_by(
            AISuggestion.created_at.desc(),  # type: ignore[attr-defined]
            AISuggestion.id,
        )
        return list(self._session.exec(statement).all())

    def mark_reviewed(self, suggestion: AISuggestion, status: str) -> AISuggestion:
        """Record the outcome of a review."""
        suggestion.status = status
        suggestion.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        self._session.add(suggestion)
        self._session.flush()
        return suggestion

    def add_feedback(self, feedback: UserFeedback) -> UserFeedback:
        """Persist one correction."""
        self._session.add(feedback)
        self._session.flush()
        return feedback

    def list_feedback(
        self,
        user_id: UUID,
        feedback_type: str | None = None,
    ) -> list[UserFeedback]:
        """Return a user's corrections, newest first."""
        statement = select(UserFeedback).where(UserFeedback.user_id == user_id)
        if feedback_type is not None:
            statement = statement.where(UserFeedback.feedback_type == feedback_type)
        statement = statement.order_by(
            UserFeedback.created_at.desc(),  # type: ignore[attr-defined]
            UserFeedback.id,
        )
        return list(self._session.exec(statement).all())

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, instance: AISuggestion | UserFeedback) -> None:
        """Reload an instance from the database."""
        self._session.refresh(instance)
