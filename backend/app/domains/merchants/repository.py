from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.domains.merchants.models import Merchant, MerchantPattern


class MerchantRepository:
    """Persistence operations for merchants and their patterns."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, merchant_id: UUID) -> Merchant | None:
        """Return a merchant by ID."""
        return self._session.get(Merchant, merchant_id)

    def find_by_name(self, merchant_name: str) -> Merchant | None:
        """Return a merchant by exact, case-insensitive name."""
        statement = select(Merchant).where(
            func.lower(Merchant.merchant_name) == merchant_name.strip().lower()
        )
        return self._session.exec(statement).first()

    def list_merchants(
        self,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Merchant]:
        """Return a page of merchants ordered by name."""
        statement = select(Merchant)
        if search:
            statement = statement.where(
                func.lower(Merchant.merchant_name).like(f"%{search.strip().lower()}%")
            )
        statement = statement.order_by(Merchant.merchant_name, Merchant.id)
        return list(self._session.exec(statement.offset(offset).limit(limit)).all())

    def count_merchants(self, search: str | None = None) -> int:
        """Return how many merchants match the search."""
        statement = select(func.count()).select_from(Merchant)
        if search:
            statement = statement.where(
                func.lower(Merchant.merchant_name).like(f"%{search.strip().lower()}%")
            )
        return int(self._session.exec(statement).one())

    def add_merchant(self, merchant: Merchant) -> Merchant:
        """Persist a merchant."""
        self._session.add(merchant)
        self._session.flush()
        return merchant

    def list_patterns_for_user(self, user_id: UUID | None) -> list[MerchantPattern]:
        """Return the user's patterns plus every global pattern.

        Ordering puts user-owned patterns first so the resolver can stop at the
        first match and still honour the rule that a personal correction wins.
        """
        statement = select(MerchantPattern).where(
            or_(
                MerchantPattern.user_id == user_id,
                MerchantPattern.user_id.is_(None),  # type: ignore[union-attr]
            )
        )
        patterns = list(self._session.exec(statement).all())
        patterns.sort(
            key=lambda pattern: (pattern.user_id is None, -len(pattern.pattern))
        )
        return patterns

    def get_pattern(
        self,
        pattern_id: UUID,
        user_id: UUID | None = None,
    ) -> MerchantPattern | None:
        """Return one pattern."""
        statement = select(MerchantPattern).where(MerchantPattern.id == pattern_id)
        if user_id is not None:
            statement = statement.where(MerchantPattern.user_id == user_id)
        return self._session.exec(statement).first()

    def find_pattern(
        self,
        user_id: UUID | None,
        merchant_id: UUID,
        pattern: str,
    ) -> MerchantPattern | None:
        """Return an identical existing pattern, if one exists."""
        statement = select(MerchantPattern).where(
            MerchantPattern.user_id == user_id,
            MerchantPattern.merchant_id == merchant_id,
            func.lower(MerchantPattern.pattern) == pattern.strip().lower(),
        )
        return self._session.exec(statement).first()

    def add_pattern(self, pattern: MerchantPattern) -> MerchantPattern:
        """Persist a merchant pattern."""
        self._session.add(pattern)
        self._session.flush()
        return pattern

    def commit(self) -> None:
        """Commit the active transaction."""
        self._session.commit()

    def rollback(self) -> None:
        """Rollback the active transaction."""
        self._session.rollback()

    def refresh(self, instance: Merchant | MerchantPattern) -> None:
        """Reload an instance from the database."""
        self._session.refresh(instance)
