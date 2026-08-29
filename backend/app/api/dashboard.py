"""Serves the read-only dashboard page.

The page is deliberately served from the API's own origin. CORS is disabled by
default (``cors_origins`` is empty, so the middleware is never added), and
because ``allow_credentials=True`` a wildcard origin would be rejected anyway —
same-origin sidesteps all of it.

The route sits outside ``/api/v1``, so ``AuthenticationMiddleware`` treats it as
public and serves the HTML to anyone. That is correct: the file contains no data.
The page gates itself, logging in against ``/api/v1/auth/login`` and holding the
token in the browser, and every figure it renders comes from an endpoint that
does require a JWT.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["dashboard"])

DASHBOARD_FILE = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


@router.get("/dashboard", response_class=FileResponse, include_in_schema=False)
def get_dashboard() -> FileResponse:
    """Return the dashboard page."""
    return FileResponse(
        DASHBOARD_FILE,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )
