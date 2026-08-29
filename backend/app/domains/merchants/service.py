import re
from decimal import Decimal
from uuid import UUID

from app.domains.merchants.exceptions import (
    MerchantNotFoundError,
    MerchantPatternValidationError,
)
from app.domains.merchants.models import Merchant, MerchantPattern
from app.domains.merchants.repository import MerchantRepository
from app.domains.merchants.resolver import MerchantMatch, resolve_merchant
from app.shared.enums import PatternType

MAX_PATTERN_LENGTH = 255


class MerchantService:
    """Application service for merchants and merchant patterns."""

    def __init__(self, repository: MerchantRepository) -> None:
        self._repository = repository

    def resolve(self, user_id: UUID, merchant_raw: str | None) -> MerchantMatch | None:
        """Resolve a raw merchant string for a user."""
        patterns = self._repository.list_patterns_for_user(user_id)
        return resolve_merchant(merchant_raw, patterns)

    def get_merchant(self, merchant_id: UUID) -> Merchant:
        """Return one merchant."""
        merchant = self._repository.get_by_id(merchant_id)
        if merchant is None:
            raise MerchantNotFoundError()
        return merchant

    def list_merchants(
        self,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Merchant], int]:
        """Return a page of merchants and the total match count."""
        merchants = self._repository.list_merchants(
            search=search,
            offset=offset,
            limit=limit,
        )
        return merchants, self._repository.count_merchants(search=search)

    def get_or_create_merchant(
        self,
        merchant_name: str,
        default_category_id: UUID | None = None,
    ) -> Merchant:
        """Return the named merchant, creating it when it is new."""
        name = merchant_name.strip()
        if not name:
            raise MerchantPatternValidationError("Merchant name is required.")

        existing = self._repository.find_by_name(name)
        if existing is not None:
            return existing

        merchant = Merchant(
            merchant_name=name,
            default_category_id=default_category_id,
        )
        self._repository.add_merchant(merchant)
        self._repository.commit()
        self._repository.refresh(merchant)
        return merchant

    def create_pattern(
        self,
        user_id: UUID | None,
        merchant_id: UUID,
        pattern: str,
        pattern_type: PatternType = PatternType.LIKE,
        confidence: Decimal = Decimal("1.00"),
        created_by: str = "USER",
    ) -> MerchantPattern:
        """Create a merchant pattern, rejecting one that cannot match."""
        self.get_merchant(merchant_id)

        cleaned = (pattern or "").strip()
        if not cleaned:
            raise MerchantPatternValidationError("Pattern is required.")
        if len(cleaned) > MAX_PATTERN_LENGTH:
            raise MerchantPatternValidationError(
                f"Pattern exceeds {MAX_PATTERN_LENGTH} characters."
            )

        parsed_type = _parse_pattern_type(pattern_type)
        if parsed_type is PatternType.REGEX:
            _validate_regex(cleaned)

        existing = self._repository.find_pattern(
            user_id=user_id,
            merchant_id=merchant_id,
            pattern=cleaned,
        )
        if existing is not None:
            return existing

        record = MerchantPattern(
            user_id=user_id,
            merchant_id=merchant_id,
            pattern=cleaned,
            pattern_type=parsed_type.value,
            confidence=confidence,
            created_by=created_by,
        )
        try:
            self._repository.add_pattern(record)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

        self._repository.refresh(record)
        return record

    def list_patterns(self, user_id: UUID | None) -> list[MerchantPattern]:
        """Return the user's patterns plus every global pattern."""
        return self._repository.list_patterns_for_user(user_id)


def _parse_pattern_type(value) -> PatternType:
    if isinstance(value, PatternType):
        return value
    try:
        return PatternType(str(value).strip().upper())
    except ValueError as exc:
        raise MerchantPatternValidationError(
            f"Unsupported pattern type: {value}."
        ) from exc


def _validate_regex(pattern: str) -> None:
    """Reject an invalid regex at write time rather than silently at match time."""
    try:
        re.compile(pattern)
    except re.error as exc:
        raise MerchantPatternValidationError(
            f"Pattern is not a valid regular expression: {exc}"
        ) from exc
