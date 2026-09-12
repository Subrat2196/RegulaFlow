import pytest
from structlog.testing import capture_logs

from app.core.config import Settings
from app.core.logging import (
    bind_correlation_id,
    get_correlation_id,
    get_logger,
    setup_logging,
)


def test_setup_logging_runs_without_error():
    """Calling setup_logging should not raise any exceptions."""
    settings = Settings()
    setup_logging(settings)


def test_bind_returns_and_stores_provided_id():
    """Providing an explicit ID should store and return it exactly."""
    cid = bind_correlation_id("req-abc-123")

    assert cid == "req-abc-123"
    assert get_correlation_id() == "req-abc-123"


def test_bind_autogenerates_uuid_when_no_id_given():
    """
    Calling bind_correlation_id() with no argument should generate a UUID4.
    UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (36 characters, 4 dashes).
    """
    cid = bind_correlation_id()

    assert len(cid) == 36
    assert cid.count("-") == 4


def test_log_entry_captures_event_and_fields():
    """
    structlog.testing.capture_logs() lets us inspect what would have been logged
    without actually writing to stdout. The captured entries are plain dicts.
    """
    setup_logging(Settings())
    logger = get_logger("regulaflow.test")

    with capture_logs() as logs:
        logger.info("ingestion_started", doc_id=42, tenant_id="acme")

    assert len(logs) == 1
    entry = logs[0]
    assert entry["event"] == "ingestion_started"
    assert entry["doc_id"] == 42
    assert entry["tenant_id"] == "acme"
    assert entry["log_level"] == "info"


def test_different_log_levels_are_recorded_correctly():
    """warning and error calls should record the correct log_level."""
    setup_logging(Settings())
    logger = get_logger("regulaflow.test")

    with capture_logs() as logs:
        logger.warning("low_disk_space", available_gb=2)
        logger.error("ingestion_failed", reason="timeout")

    assert logs[0]["log_level"] == "warning"
    assert logs[0]["available_gb"] == 2
    assert logs[1]["log_level"] == "error"
    assert logs[1]["reason"] == "timeout"


def test_multiple_key_value_pairs_are_all_captured():
    """
    Every keyword argument passed to logger.info() becomes a field in the
    log record. This is the core value of structured logging over plain strings.
    """
    setup_logging(Settings())
    logger = get_logger("regulaflow.test")

    with capture_logs() as logs:
        logger.info(
            "gap_detected",
            gap_id="GAP-001",
            requirement_id="REQ-042",
            severity="high",
            confidence=0.91,
        )

    entry = logs[0]
    assert entry["gap_id"] == "GAP-001"
    assert entry["requirement_id"] == "REQ-042"
    assert entry["severity"] == "high"
    assert entry["confidence"] == 0.91
