from fastapi import FastAPI
from app.core.logging import configure_logging, get_logger
from app.api.feedback import router as feedback_router

from app.core.config import get_settings

configure_logging()
logger = get_logger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for collecting customer feedback "
        "and generating evidence-backed product insights."
    ),
    version=settings.app_version,
    debug=settings.debug,
)
app.include_router(feedback_router)

logger.info("FastAPI application initialized.")

@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "environment": settings.environment,
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "environment": settings.environment,
    }