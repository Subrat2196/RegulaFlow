from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """
    Every significant decision or action in the system produces an audit event.

    These event types are the vocabulary of the audit trail. An auditor
    reading the audit log for a workflow can reconstruct exactly what
    happened, who did it, and what data was used — without touching
    the application itself.
    """

    # Document lifecycle
    REGULATION_UPLOADED = "regulation_uploaded"
    POLICY_UPLOADED = "policy_uploaded"
    REGULATION_VERSION_CHANGED = "regulation_version_changed"

    # Agent workflow
    WORKFLOW_STARTED = "workflow_started"
    REQUIREMENT_EXTRACTED = "requirement_extracted"
    POLICY_RETRIEVED = "policy_retrieved"
    GAP_DETECTED = "gap_detected"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_RESUMED = "workflow_resumed"

    # Human review
    GAP_SUBMITTED_FOR_REVIEW = "gap_submitted_for_review"
    GAP_APPROVED = "gap_approved"
    GAP_REJECTED = "gap_rejected"
    GAP_ESCALATED = "gap_escalated"
    EVIDENCE_REQUESTED = "evidence_requested"


class AuditEvent(BaseModel):
    """
    A single immutable record of something significant that happened.

    Audit events are NEVER updated or deleted — only appended. An auditor
    needs to see the full history, not just the current state. Every event
    captures who did it, in what workflow, and the exact data involved.

    The `payload` field is flexible — different event types carry different
    data. A REQUIREMENT_EXTRACTED event might carry the requirement text
    and confidence score. A GAP_APPROVED event carries the reviewer's notes.
    The audit service (Session 43) defines what goes in each payload.
    """

    id: UUID
    tenant_id: str
    workflow_id: str | None = None    # links all events from one compliance run
    actor: str                        # user ID, or "system" for automated actions
    event_type: AuditEventType
    payload: dict = Field(
        default_factory=dict,
        description="Event-specific data — what was acted on, what was decided, what evidence was used",
    )
    timestamp: datetime


class AuditEventCreate(BaseModel):
    """
    Input shape for recording a new audit event.
    No `id` (assigned by the DB) and no `timestamp` (assigned by the audit service).
    """

    tenant_id: str
    workflow_id: str | None = None
    actor: str
    event_type: AuditEventType
    payload: dict = Field(default_factory=dict)
