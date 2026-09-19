from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """
    Data a user provides when uploading an internal company policy.

    INPUT shape — what the API accepts. No id, no content_hash, no
    created_at — those are assigned by the system after processing.
    """

    tenant_id: str
    policy_key: str = Field(
        ...,
        description="Unique identifier for this policy, e.g. 'POL-DATA-07' or 'POL-ACCESS-03'",
        min_length=2,
        max_length=100,
    )
    title: str = Field(..., min_length=2, max_length=500)
    domain: str = Field(
        ...,
        description="Compliance domain this policy covers, e.g. 'data_retention', 'access_control'",
        min_length=2,
    )
    version: str = Field(default="1.0", max_length=20)
    effective_date: date
    active: bool = True


class PolicyDocument(BaseModel):
    """
    A fully persisted internal policy document — the STORED shape.

    Policies are what the Policy Analyzer Agent retrieves and compares
    against regulatory requirements. The `domain` field is the primary
    filter used in hybrid search — only policies in the relevant domain
    are retrieved for a given regulatory requirement.
    """

    id: UUID
    tenant_id: str
    policy_key: str
    title: str
    domain: str
    version: str
    effective_date: date
    active: bool
    content_hash: str
    created_at: datetime
