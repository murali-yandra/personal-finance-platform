from pydantic import BaseModel


class ValidationErrorDetail(BaseModel):
    """Sanitized validation issue returned to API clients."""

    field: str
    message: str


class ErrorResponseDetail(BaseModel):
    """Standard API error response detail."""

    code: str
    message: str
    request_id: str
    correlation_id: str
    details: list[ValidationErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    success: bool = False
    error: ErrorResponseDetail


class SuccessResponse[DataT](BaseModel):
    """Standard API success response envelope."""

    success: bool = True
    data: DataT


class PageMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int
    page_size: int
    total_records: int


class PaginatedResponse[DataT](BaseModel):
    """Standard API success envelope for paginated list endpoints."""

    success: bool = True
    data: list[DataT]
    meta: PageMeta
