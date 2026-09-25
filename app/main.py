from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.routes import compliance, health
from app.core.config import get_settings
from app.core.logging import (
    bind_correlation_id,
    get_correlation_id,
    get_logger,
    setup_logging,
)

logger = get_logger(__name__)

# Transforms the function into an async context manager for FastAPI's lifespan.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs startup logic before the server accepts requests,
    and shutdown logic after the last request is handled.

    The code before `yield` = startup.
    The code after  `yield` = shutdown.
    """
    settings = get_settings() # Retrieve application settings
    setup_logging(settings) # Configure logging based on the application settings
    logger.info(
        "regulaflow_starting",
        environment=settings.environment,
        version=settings.app_version,
    ) # Log that the application is starting with the current environment and version
    yield
    logger.info("regulaflow_stopping") # Log that the application is stopping


# Create the FastAPI application instance with the specified title, version, description, and lifespan.
app = FastAPI(
    title="RegulaFlow",
    version="0.1.0",
    description="Multi-agent regulatory intelligence and compliance automation platform",
    lifespan=lifespan,
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """
    Runs before and after every single HTTP request.

    Before: reads X-Correlation-ID from the request headers, or generates a
    new UUID if the client didn't send one. Stores it in the ContextVar so
    every log line produced during this request carries it automatically.

    After: writes the correlation ID back into the response headers so the
    client (or a downstream service) can trace the request too.
    """
    incoming_id = request.headers.get("X-Correlation-ID")
    bind_correlation_id(incoming_id)

    response = await call_next(request)

    response.headers["X-Correlation-ID"] = get_correlation_id()
    return response


app.include_router(health.router)
app.include_router(compliance.router)