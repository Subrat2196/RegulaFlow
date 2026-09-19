from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

# Enum is used to restrict the possible values for gap severity and ensure consistent JSON serialization
# the AI may determine severity, but the enum ensures it is always one of the predefined levels
class GapSeverity(str, Enum):
    """
    The four severity levels for a compliance gap.

    This enum carries the HITL routing rules as code — not as a comment,
    not as documentation, but as executable logic. The severity engine
    (Session 25) uses `requires_human_review` and `level` to make
    deterministic decisions that the LLM cannot override.

    Using `str, Enum` means the values serialize to plain strings in JSON:
    GapSeverity.HIGH → "high" (not "<GapSeverity.HIGH: 'high'>")
    This makes FastAPI responses and database storage work naturally.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    # @property is used to define the deterministic rules as read-only attributes
    # difference between method and attribute: methods require parentheses to call, properties do not
    @property  
    def requires_human_review(self) -> bool:
        """
        Deterministic HITL routing rule — this is never decided by the LLM.

        LOW      → auto-persist, no review needed
        MEDIUM   → auto-persist (analyst may optionally review)
        HIGH     → compliance manager approval required before finalizing
        CRITICAL → mandatory escalation, cannot proceed without approval
        """
        return self in (GapSeverity.HIGH, GapSeverity.CRITICAL)

    @property
    def level(self) -> int:
        """
        Numeric representation for ordering and comparison.
        Useful when you need to find the most severe gap in a list,
        or compare whether one gap is more severe than another.

        LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4
        """
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}[self.value]


class GapStatus(str, Enum):
    """The four possible compliance states for a requirement."""

    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReviewStatus(str, Enum):
    """
    Tracks where a gap is in the human review lifecycle.

    The state machine:
        not_required  (LOW/MEDIUM severity — auto-persisted)
        pending       (HIGH/CRITICAL — waiting for manager action)
        approved      (manager confirmed the gap and remediation)
        rejected      (manager disagrees — gap re-evaluated)
        escalated     (CRITICAL — sent to senior authority)
    """

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class GapCreate(BaseModel):
    """
    The output of the Gap Detector Agent — input to the persistence layer.

    The agent produces this. The deterministic severity engine then validates
    it (checking that `requires_human_review` matches what `severity` demands)
    before it is stored as a ComplianceGap.
    """

    tenant_id: str
    requirement_id: UUID
    status: GapStatus
    severity: GapSeverity
    gap_summary: str = Field(..., min_length=10)
    recommended_remediation: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_review: bool


class ComplianceGap(BaseModel):
    """
    A fully persisted compliance gap — the STORED shape with review lifecycle.

    This is the record that lives in the database, accumulates review history,
    and forms the basis of compliance reports and audit trails.
    """

    id: UUID
    tenant_id: str
    requirement_id: UUID
    status: GapStatus
    severity: GapSeverity
    gap_summary: str
    recommended_remediation: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_human_review: bool
    review_status: ReviewStatus
    reviewer_id: str | None = None        # who reviewed it
    reviewer_notes: str | None = None     # what they said
    created_at: datetime
    reviewed_at: datetime | None = None   # when the review decision was made
