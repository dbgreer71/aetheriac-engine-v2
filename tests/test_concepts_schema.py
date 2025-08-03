"""
Tests for Concept Cards v1.0 schema and validation.
"""

import pytest
from fastapi.testclient import TestClient
from ae2.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_concepts_schema_endpoint(client):
    """Test that /concepts/schema returns the schema."""
    response = client.get("/concepts/schema")
    assert response.status_code == 200

    schema = response.json()
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert schema["title"] == "Concept Card v1.0 Schema"
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "definition" in schema["properties"]
    assert "claims" in schema["properties"]
    assert "evidence" in schema["properties"]
    assert "provenance" in schema["properties"]


def test_concept_card_validation():
    """Test that concept cards validate against the schema."""
    from ae2.concepts.models import ConceptCard, Evidence, Claim, Provenance
    from datetime import datetime

    # Create a valid concept card
    evidence = {
        "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890": Evidence(
            sha256="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
            length=150,
            source="RFC 791",
        )
    }

    claims = [
        Claim(
            claim="Test claim",
            evidence_refs=[
                "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
            ],
            confidence=0.9,
        )
    ]

    provenance = Provenance(
        index_root="/data/index",
        build_time=datetime.utcnow().isoformat(),
        compiler_version="1.0.0",
        evidence_count=1,
    )

    card = ConceptCard(
        id="concept:test:v1",
        definition="Test definition",
        claims=claims,
        evidence=evidence,
        provenance=provenance,
        tags=["test"],
        approved=False,
    )

    # Should not raise validation errors
    assert card.id == "concept:test:v1"
    assert len(card.claims) == 1
    assert len(card.evidence) == 1


def test_concept_card_invalid_id():
    """Test that invalid concept IDs are rejected."""
    from ae2.concepts.models import ConceptCard, Evidence, Claim, Provenance
    from datetime import datetime
    from pydantic import ValidationError

    evidence = {
        "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890": Evidence(
            sha256="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
            length=150,
            source="RFC 791",
        )
    }

    claims = [
        Claim(
            claim="Test claim",
            evidence_refs=[
                "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
            ],
            confidence=0.9,
        )
    ]

    provenance = Provenance(
        index_root="/data/index",
        build_time=datetime.utcnow().isoformat(),
        compiler_version="1.0.0",
        evidence_count=1,
    )

    # Invalid ID format
    with pytest.raises(ValidationError):
        ConceptCard(
            id="invalid-id",
            definition="Test definition",
            claims=claims,
            evidence=evidence,
            provenance=provenance,
            tags=["test"],
            approved=False,
        )


def test_concept_card_short_definition():
    """Test that short definitions are rejected."""
    from ae2.concepts.models import ConceptCard, Evidence, Claim, Provenance
    from datetime import datetime
    from pydantic import ValidationError

    evidence = {
        "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890": Evidence(
            sha256="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
            length=150,
            source="RFC 791",
        )
    }

    claims = [
        Claim(
            claim="Test claim",
            evidence_refs=[
                "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
            ],
            confidence=0.9,
        )
    ]

    provenance = Provenance(
        index_root="/data/index",
        build_time=datetime.utcnow().isoformat(),
        compiler_version="1.0.0",
        evidence_count=1,
    )

    # Too short definition
    with pytest.raises(ValidationError):
        ConceptCard(
            id="concept:test:v1",
            definition="Short",
            claims=claims,
            evidence=evidence,
            provenance=provenance,
            tags=["test"],
            approved=False,
        )


def test_concept_card_confidence_bounds():
    """Test that confidence scores are within bounds."""
    from ae2.concepts.models import Claim
    from pydantic import ValidationError

    # Valid confidence
    claim = Claim(
        claim="Test claim",
        evidence_refs=[
            "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
        ],
        confidence=0.5,
    )
    assert claim.confidence == 0.5

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        Claim(
            claim="Test claim",
            evidence_refs=[
                "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
            ],
            confidence=1.5,
        )

    # Invalid confidence (too low)
    with pytest.raises(ValidationError):
        Claim(
            claim="Test claim",
            evidence_refs=[
                "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567890"
            ],
            confidence=-0.1,
        )
