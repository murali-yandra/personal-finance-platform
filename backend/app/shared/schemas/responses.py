from pydantic import BaseModel


class ErrorResponseDetail(BaseModel):
    """Standard API error response detail."""

    code: str
    message: str
    request_id: str
    correlation_id: str


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    success: bool = False
    error: ErrorResponseDetail


class SuccessResponse[DataT](BaseModel):
    """Standard API success response envelope."""

    success: bool = True
    data: DataT
