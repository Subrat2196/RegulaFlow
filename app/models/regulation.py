from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

# this class represents the input data for creating a new regulation document
class RegulationCreate(BaseModel):
    """
    The data a user provides when uploading a new regulation document.

    This is the INPUT shape — what the API accepts. It has no `id`,
    no `content_hash`, no `created_at` — those are assigned by the
    system after the document is received and processed.
    """
    # regulation key uniquely identifies this regulation within the tenant's context
    tenant_id: str
    regulation_key: str = Field(
        ...,
        description="Unique identifier for this regulation, e.g. 'GDPR-2016' or 'IRDAI-2026-17'",
        min_length=2,
        max_length=100,
    )
    title: str = Field(..., min_length=2, max_length=500)
    # the geographic or regulatory scope of the regulation  
    jurisdiction: str = Field(
        ...,
        description="Geographic or regulatory scope, e.g. 'EU', 'India', 'US-Federal'",
        min_length=2,
    )
    version: str = Field(default="1.0", max_length=20)
    effective_date: date
    source: str = Field(
        ...,
        description="Where this document came from — a URL or a description",
        min_length=2,
    )

# this class is different from RegulationCreate; 
# it represents a fully persisted regulation document with system-assigned fields
class RegulationDocument(BaseModel):
    """
    A fully persisted regulation document — the STORED shape.

    This is what the system holds after ingestion is complete. It adds
    the fields that the system assigns: id, content_hash, created_at,
    and optionally previous_version_id for version tracking.
    """

    id: UUID
    tenant_id: str
    regulation_key: str
    title: str
    jurisdiction: str
    version: str
    effective_date: date
    source: str
    content_hash: str          # SHA-256 hash of the document content
    previous_version_id: UUID | None = None  # links to the prior version if this is an update
    created_at: datetime

# this class represents a single structured compliance requirement extracted from a regulation
class RegulationRequirement(BaseModel):
    """
    A single structured compliance requirement extracted from a regulation.

    This is the OUTPUT of the Regulation Monitoring Agent — the agent
    reads raw regulatory text and converts it into this structured form.
    One regulation document produces many requirements (one per section
    that contains an obligation).
    """

    id: UUID
    regulation_document_id: UUID  # which document this came from
    section: str = Field(
        ...,
        description="The section or clause reference, e.g. '4.2' or 'Article 17'",
    )
    requirement_text: str          # the original regulatory obligation text
    mandatory_actions: list[str] = Field(
        default_factory=list,
        description="Specific actions the organization must take",
    )
    evidence_required: list[str] = Field(
        default_factory=list,
        description="Documents or artifacts needed to prove compliance",
    )
    domain: str | None = Field(
        default=None,
        description="Compliance domain this falls under, e.g. 'data_retention', 'access_control'",
    )
    confidence: float = Field(
        ...,
        ge=0.0,   # greater than or equal to 0.0
        le=1.0,   # less than or equal to 1.0
        description="Agent's confidence in this extraction (0.0 = uncertain, 1.0 = certain)",
    )


class RequirementCreate(BaseModel):
    """
    The data the Regulation Monitoring Agent produces for a new requirement.

    The INPUT shape when creating a requirement — no `id` yet (the database
    assigns that). This is what the agent returns after processing a section.
    """

    regulation_document_id: UUID
    section: str
    requirement_text: str
    mandatory_actions: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    domain: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
