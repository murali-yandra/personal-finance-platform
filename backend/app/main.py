from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.admin import router as admin_router
from app.api.ai import router as ai_router
from app.api.api_keys import router as api_keys_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.dashboard import router as dashboard_router
from app.api.errors import register_exception_handlers
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.merchants import router as merchants_router
from app.api.middleware.authentication import AuthenticationMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.raw_events import router as raw_events_router
from app.api.reports import router as reports_router
from app.api.telegram import router as telegram_router
from app.api.transactions import router as transactions_router
from app.api.transfers import router as transfers_router
from app.api.users import router as users_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
    )

    application.include_router(health_router)
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(users_router, prefix="/api/v1")
    application.include_router(accounts_router, prefix="/api/v1")
    application.include_router(transactions_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")
    application.include_router(ingest_router, prefix="/api/v1")
    application.include_router(raw_events_router, prefix="/api/v1")
    application.include_router(merchants_router, prefix="/api/v1")
    application.include_router(categories_router, prefix="/api/v1")
    application.include_router(telegram_router, prefix="/api/v1")
    application.include_router(reports_router, prefix="/api/v1")
    application.include_router(transfers_router, prefix="/api/v1")
    application.include_router(ai_router, prefix="/api/v1")
    application.include_router(api_keys_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")
    application.include_router(dashboard_router)
    application.add_middleware(AuthenticationMiddleware)

    if settings.rate_limit_enabled:
        application.add_middleware(
            RateLimitMiddleware,
            limiter=RateLimiter(
                limit=settings.rate_limit_per_minute,
                window_seconds=60,
            ),
        )
    # Added last so it runs first: every other layer, including authentication
    # failures, is logged with a request id.
    application.add_middleware(RequestContextMiddleware)

    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(application)

    return application


app = create_app()
