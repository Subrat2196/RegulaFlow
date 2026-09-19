from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.audit import AuditEvent, AuditEventCreate, AuditEventType
from app.models.gap import (
    ComplianceGap,
    GapCreate,
    GapSeverity,
    GapStatus,
    ReviewStatus,
)
from app.models.policy import PolicyCreate, PolicyDocument


# ---------------------------------------------------------------------------
# GapSeverity — enum values and deterministic properties
# ---------------------------------------------------------------------------

def test_gap_severity_values_exist():
    """All four severity levels must exist with correct string values."""
    assert GapSeverity.LOW.value == "low"
    assert GapSeverity.MEDIUM.value == "medium"
    assert GapSeverity.HIGH.value == "high"
    assert GapSeverity.CRITICAL.value == "critical"


def test_severity_levels_are_ordered_correctly():
    """CRITICAL must be the most severe, LOW the least."""
    assert GapSeverity.LOW.level < GapSeverity.MEDIUM.level
    assert GapSeverity.MEDIUM.level < GapSeverity.HIGH.level
    assert GapSeverity.HIGH.level < GapSeverity.CRITICAL.level


def test_low_and_medium_do_not_require_human_review():
    """LOW and MEDIUM gaps should auto-persist without human approval."""
    assert GapSeverity.LOW.requires_human_review is False
    assert GapSeverity.MEDIUM.requires_human_review is False


def test_high_and_critical_require_human_review():
    """
    HIGH and CRITICAL gaps must always require human review.
    This is the deterministic HITL rule — the LLM cannot override it.
    """
    assert GapSeverity.HIGH.requires_human_review is True
    assert GapSeverity.CRITICAL.requires_human_review is True


def test_invalid_severity_value_is_rejected():
    """Pydantic should reject any severity string not in the enum."""
    with pytest.raises(ValidationError):
        GapCreate(
            tenant_id="acme",
            requirement_id=uuid4(),
            status=GapStatus.NON_COMPLIANT,
            severity="extreme",       # not a valid GapSeverity value
            gap_summary="Missing encryption controls entirely.",
            confidence=0.95,
            requires_human_review=True,
        )


def test_severity_is_a_string_for_serialization():
    """
    Because GapSeverity inherits from str, the value should compare equal
    to a plain string. This matters for database storage and JSON serialization.
    """
    assert GapSeverity.HIGH == "high"
    assert GapSeverity.CRITICAL == "critical"


# ---------------------------------------------------------------------------
# GapStatus — compliance state values
# ---------------------------------------------------------------------------

def test_gap_status_values_exist():
    assert GapStatus.COMPLIANT.value == "compliant"
    assert GapStatus.PARTIALLY_COMPLIANT.value == "partially_compliant"
    assert GapStatus.NON_COMPLIANT.value == "non_compliant"
    assert GapStatus.INSUFFICIENT_EVIDENCE.value == "insufficient_evidence"


# ---------------------------------------------------------------------------
# GapCreate — agent output shape
# ---------------------------------------------------------------------------

def test_valid_gap_create_passes():
    gap = GapCreate(
        tenant_id="acme-corp",
        requirement_id=uuid4(),
        status=GapStatus.PARTIALLY_COMPLIANT,
        severity=GapSeverity.HIGH,
        gap_summary="Retention period is not explicitly defined in Policy 7.3.",
        recommended_remediation=["Update Policy 7.3 with explicit 5-year retention period"],
        confidence=0.89,
        requires_human_review=True,
    )
    assert gap.severity == GapSeverity.HIGH
    assert gap.severity.requires_human_review is True


def test_gap_summary_too_short_is_rejected():
    """gap_summary has min_length=10 — a vague one-word summary is not allowed."""
    with pytest.raises(ValidationError):
        GapCreate(
            tenant_id="acme-corp",
            requirement_id=uuid4(),
            status=GapStatus.NON_COMPLIANT,
            severity=GapSeverity.CRITICAL,
            gap_summary="Missing",    # only 7 characters — too short
            confidence=0.99,
            requires_human_review=True,
        )


# ---------------------------------------------------------------------------
# ComplianceGap — stored shape with review lifecycle
# ---------------------------------------------------------------------------

def test_valid_compliance_gap_passes():
    gap = ComplianceGap(
        id=uuid4(),
        tenant_id="acme-corp",
        requirement_id=uuid4(),
        status=GapStatus.PARTIALLY_COMPLIANT,
        severity=GapSeverity.HIGH,
        gap_summary="Retention period is not explicitly defined.",
        recommended_remediation=["Update Policy 7.3"],
        confidence=0.89,
        requires_human_review=True,
        review_status=ReviewStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    assert gap.reviewer_id is None          # not yet reviewed
    assert gap.reviewed_at is None          # no review timestamp yet
    assert gap.review_status == ReviewStatus.PENDING


def test_compliance_gap_after_approval():
    """Simulates the state of a gap after a manager approves it."""
    gap = ComplianceGap(
        id=uuid4(),
        tenant_id="acme-corp",
        requirement_id=uuid4(),
        status=GapStatus.PARTIALLY_COMPLIANT,
        severity=GapSeverity.HIGH,
        gap_summary="Retention period not defined explicitly in policy.",
        recommended_remediation=["Update Policy 7.3"],
        confidence=0.89,
        requires_human_review=True,
        review_status=ReviewStatus.APPROVED,
        reviewer_id="user-manager-01",
        reviewer_notes="Confirmed — retention wording is ambiguous. Remediation accepted.",
        created_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc),
    )
    assert gap.review_status == ReviewStatus.APPROVED
    assert gap.reviewer_id == "user-manager-01"
    assert gap.reviewed_at is not None


# ---------------------------------------------------------------------------
# AuditEvent — audit trail records
# ---------------------------------------------------------------------------

def test_valid_audit_event_passes():
    event = AuditEvent(
        id=uuid4(),
        tenant_id="acme-corp",
        workflow_id="wf-abc-123",
        actor="system",
        event_type=AuditEventType.REQUIREMENT_EXTRACTED,
        payload={
            "requirement_id": "req-001",
            "section": "4.2",
            "confidence": 0.93,
            "model": "gpt-4o",
        },
        timestamp=datetime.now(timezone.utc),
    )
    assert event.event_type == AuditEventType.REQUIREMENT_EXTRACTED
    assert event.payload["confidence"] == 0.93


def test_audit_event_payload_defaults_to_empty_dict():
    """Payload is optional — an event with no extra data should still work."""
    event = AuditEventCreate(
        tenant_id="acme-corp",
        actor="user-analyst-01",
        event_type=AuditEventType.REGULATION_UPLOADED,
    )
    assert event.payload == {}
    assert event.workflow_id is None


def test_audit_event_payload_is_flexible():
    """
    Different event types carry completely different payload shapes.
    The dict type handles this — no single schema enforced.
    """
    approval_event = AuditEvent(
        id=uuid4(),
        tenant_id="acme-corp",
        actor="user-manager-01",
        event_type=AuditEventType.GAP_APPROVED,
        payload={
            "gap_id": str(uuid4()),
            "previous_status": "pending",
            "reviewer_notes": "Evidence sufficient for partial compliance.",
            "approved_remediation": ["Update Policy 7.3"],
        },
        timestamp=datetime.now(timezone.utc),
    )
    assert approval_event.payload["reviewer_notes"] is not None


def test_invalid_audit_event_type_rejected():
    """An event type not in AuditEventType must be rejected."""
    with pytest.raises(ValidationError):
        AuditEvent(
            id=uuid4(),
            tenant_id="acme-corp",
            actor="system",
            event_type="something_we_never_defined",
            timestamp=datetime.now(timezone.utc),
        )


# ---------------------------------------------------------------------------
# PolicyCreate and PolicyDocument
# ---------------------------------------------------------------------------

def test_valid_policy_create_passes():
    from datetime import date
    policy = PolicyCreate(
        tenant_id="acme-corp",
        policy_key="POL-DATA-07",
        title="Data Retention Policy",
        domain="data_retention",
        effective_date=date(2025, 1, 1),
    )
    assert policy.active is True       # defaults to active
    assert policy.version == "1.0"     # default version


def test_policy_document_inactive_flag():
    """A superseded policy should be storeable with active=False."""
    from datetime import date
    doc = PolicyDocument(
        id=uuid4(),
        tenant_id="acme-corp",
        policy_key="POL-DATA-07",
        title="Data Retention Policy v1",
        domain="data_retention",
        version="1.0",
        effective_date=date(2024, 1, 1),
        active=False,           # this version has been superseded
        content_hash="abc123",
        created_at=datetime.now(timezone.utc),
    )
    assert doc.active is False
