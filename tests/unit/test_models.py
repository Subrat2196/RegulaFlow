from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models.api import APIResponse, ErrorResponse, PaginatedResponse
from app.models.regulation import (
    RegulationCreate,
    RegulationDocument,
    RegulationRequirement,
    RequirementCreate,
)


# ---------------------------------------------------------------------------
# RegulationCreate — the input shape
# ---------------------------------------------------------------------------

def test_valid_regulation_create_passes():
    reg = RegulationCreate(
        tenant_id="acme-corp",
        regulation_key="GDPR-2016",
        title="General Data Protection Regulation",
        jurisdiction="EU",
        effective_date=date(2018, 5, 25),
        source="https://eur-lex.europa.eu/gdpr",
    )
    assert reg.regulation_key == "GDPR-2016"
    assert reg.version == "1.0"          # default applied
    assert reg.jurisdiction == "EU"


def test_regulation_create_missing_required_field_fails():
    """title is required — omitting it should raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        RegulationCreate(
            tenant_id="acme-corp",
            regulation_key="GDPR-2016",
            # title intentionally omitted
            jurisdiction="EU",
            effective_date=date(2018, 5, 25),
            source="eur-lex",
        )
    assert "title" in str(exc_info.value)


def test_regulation_key_too_short_fails():
    """regulation_key must be at least 2 characters."""
    with pytest.raises(ValidationError):
        RegulationCreate(
            tenant_id="acme-corp",
            regulation_key="X",     # only 1 character
            title="Test",
            jurisdiction="EU",
            effective_date=date(2026, 1, 1),
            source="test",
        )


# ---------------------------------------------------------------------------
# RegulationDocument — the stored shape
# ---------------------------------------------------------------------------

def test_valid_regulation_document_passes():
    doc = RegulationDocument(
        id=uuid4(),
        tenant_id="acme-corp",
        regulation_key="GDPR-2016",
        title="General Data Protection Regulation",
        jurisdiction="EU",
        version="1.0",
        effective_date=date(2018, 5, 25),
        source="eur-lex",
        content_hash="abc123def456",
        previous_version_id=None,
        created_at=datetime.now(timezone.utc),
    )
    assert doc.previous_version_id is None  # optional field defaults to None
    assert isinstance(doc.id, UUID)


def test_regulation_document_links_previous_version():
    """previous_version_id should accept a UUID when a prior version exists."""
    prior_id = uuid4()
    doc = RegulationDocument(
        id=uuid4(),
        tenant_id="acme-corp",
        regulation_key="GDPR-2016",
        title="GDPR Amendment",
        jurisdiction="EU",
        version="2.0",
        effective_date=date(2026, 1, 1),
        source="eur-lex",
        content_hash="xyz789",
        previous_version_id=prior_id,
        created_at=datetime.now(timezone.utc),
    )
    assert doc.previous_version_id == prior_id


# ---------------------------------------------------------------------------
# RegulationRequirement — the agent extraction shape
# ---------------------------------------------------------------------------

def test_valid_requirement_passes():
    req = RegulationRequirement(
        id=uuid4(),
        regulation_document_id=uuid4(),
        section="4.2",
        requirement_text="Organizations must retain personal data records for a minimum of 5 years.",
        mandatory_actions=["implement retention policy", "configure system retention"],
        evidence_required=["data retention policy document", "system configuration logs"],
        domain="data_retention",
        confidence=0.93,
    )
    assert req.confidence == 0.93
    assert len(req.mandatory_actions) == 2


def test_confidence_above_1_is_rejected():
    """Confidence is a probability — it cannot exceed 1.0."""
    with pytest.raises(ValidationError) as exc_info:
        RegulationRequirement(
            id=uuid4(),
            regulation_document_id=uuid4(),
            section="4.2",
            requirement_text="Some requirement text.",
            confidence=1.7,     # invalid — above 1.0
        )
    assert "confidence" in str(exc_info.value)


def test_confidence_below_0_is_rejected():
    """Confidence cannot be negative."""
    with pytest.raises(ValidationError):
        RegulationRequirement(
            id=uuid4(),
            regulation_document_id=uuid4(),
            section="4.2",
            requirement_text="Some requirement text.",
            confidence=-0.1,    # invalid — below 0.0
        )


def test_requirement_lists_default_to_empty():
    """mandatory_actions and evidence_required should default to [] not None."""
    req = RequirementCreate(
        regulation_document_id=uuid4(),
        section="5.1",
        requirement_text="Access logs must be maintained.",
        confidence=0.85,
        # mandatory_actions and evidence_required intentionally omitted
    )
    assert req.mandatory_actions == []
    assert req.evidence_required == []


def test_two_requirements_have_independent_lists():
    """
    Each instance must get its own list — not share one list.
    This tests the default_factory=list pattern works correctly.
    If they shared a list, appending to one would affect the other.
    """
    req1 = RequirementCreate(
        regulation_document_id=uuid4(),
        section="1.1",
        requirement_text="Req 1",
        confidence=0.9,
    )
    req2 = RequirementCreate(
        regulation_document_id=uuid4(),
        section="1.2",
        requirement_text="Req 2",
        confidence=0.8,
    )
    req1.mandatory_actions.append("action A")

    assert req1.mandatory_actions == ["action A"]
    assert req2.mandatory_actions == []  # req2's list is completely separate


# ---------------------------------------------------------------------------
# APIResponse wrapper
# ---------------------------------------------------------------------------

def test_api_response_wraps_a_string():
    response = APIResponse[str](data="hello")
    assert response.success is True
    assert response.data == "hello"
    assert response.message is None


def test_api_response_wraps_a_regulation_document():
    doc = RegulationDocument(
        id=uuid4(),
        tenant_id="acme-corp",
        regulation_key="GDPR-2016",
        title="GDPR",
        jurisdiction="EU",
        version="1.0",
        effective_date=date(2018, 5, 25),
        source="eur-lex",
        content_hash="abc123",
        created_at=datetime.now(timezone.utc),
    )
    response = APIResponse[RegulationDocument](data=doc)
    assert response.success is True
    assert response.data.regulation_key == "GDPR-2016"


def test_error_response_shape():
    error = ErrorResponse(
        error="regulation_not_found",
        detail="No regulation with key 'XYZ' exists for this tenant.",
    )
    assert error.success is False
    assert error.error == "regulation_not_found"


def test_paginated_response_shape():
    items = ["item1", "item2", "item3"]
    response = PaginatedResponse[str](
        data=items,
        total=100,
        page=1,
        page_size=3,
    )
    assert response.success is True
    assert len(response.data) == 3
    assert response.total == 100
