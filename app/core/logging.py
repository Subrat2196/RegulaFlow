import logging
import sys
import uuid
from contextvars import ContextVar

import structlog

from app.core.config import Settings

# ContextVar holds the correlation ID for the current async context.
# Unlike a plain global variable, each concurrent request gets its own
# value — they cannot overwrite each other even when running simultaneously.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current request context."""
    return _correlation_id.get()


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """
    Set the correlation ID for the current request context.
    If none is provided, a new UUID is generated automatically.
    Returns the ID that was set.
    """
    cid = correlation_id or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def _inject_correlation_id(
    logger: object, method_name: str, event_dict: dict
) -> dict:
    """
    structlog processor — injects the correlation ID into every log record.

    Processors are functions that transform a log event before it is written.
    Each processor receives the event dictionary, modifies it, and passes it
    to the next processor in the chain.
    """
    cid = _correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def setup_logging(settings: Settings) -> None:
    """
    Configure structlog and Python's standard logging.
    Call this exactly once at application startup — in main.py.

    The processor chain runs in order on every log call:
        1. merge any context variables bound via structlog.contextvars
        2. inject our correlation ID
        3. add the log level (info, warning, error …)
        4. add the logger name (which module it came from)
        5. add an ISO-8601 timestamp
        6. render stack traces if present
        7. serialize the whole event dict to JSON
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure Python's built-in logging to write plain messages to stdout.
    # structlog uses this as its output backend.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_correlation_id,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structlog logger for a module.
    Use this everywhere instead of logging.getLogger().

    Usage:
        logger = get_logger(__name__)
        logger.info("ingestion_started", doc_id=42, tenant_id="acme")

    That produces a JSON line like:
        {
            "event": "ingestion_started",
            "doc_id": 42,
            "tenant_id": "acme",
            "correlation_id": "a3f2...",
            "log_level": "info",
            "logger": "app.services.ingestion",
            "timestamp": "2026-09-12T17:40:00Z"
        }
    """
    return structlog.get_logger(name)
