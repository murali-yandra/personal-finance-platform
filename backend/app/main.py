from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import get_settings
from app.core.logging import configure_logging


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

    return application


app = create_app()
