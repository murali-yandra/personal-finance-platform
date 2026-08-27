"""Request-scoped audit wiring.

The audit service shares the request's ``Session`` so audit rows commit or roll
back with the change they describe. Request and correlation IDs come from the
same headers the error envelope uses, which is what lets an operator join a
client-visible error to the audit trail it produced.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlmodel import Session

from app.db.session import get_session
from app.domains.audit.repository import AuditRepository
from app.domains.audit.service import AuditService
from app.shared.enums import AuditSource

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


def get_audit_service(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> AuditService:
    """Build an audit service bound to the current request and session."""
    request_id = _header_uuid(request, REQUEST_ID_HEADER)
    correlation_id = _header_uuid(request, CORRELATION_ID_HEADER) or request_id
    return AuditService(
        repository=AuditRepository(session),
        source=AuditSource.USER,
        correlation_id=correlation_id,
        request_id=request_id,
    )


def _header_uuid(request: Request, header: str) -> UUID | None:
    raw = request.headers.get(header)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None
