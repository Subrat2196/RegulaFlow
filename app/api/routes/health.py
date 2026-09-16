from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])
# Health check endpoints for liveness and readiness probes
# swagger documentation will automatically include these endpoints

@router.get("/health") # Liveness check endpoint
async def health_check() -> dict: # Returns the health status of the application
    """
    Liveness check — answers: is the process alive?

    A load balancer or Kubernetes hits this continuously.
    If it returns anything other than 2xx, the container is restarted.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Readiness check — answers: is the process ready to serve traffic?

    Separate from /health because a process can be alive but not ready
    (e.g. still connecting to the database). In later sessions this will
    verify the database connection before returning ok.
    """
    return {"status": "ok"}
