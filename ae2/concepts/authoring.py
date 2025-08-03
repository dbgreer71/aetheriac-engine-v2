"""
Authoring tools for Concept Cards v1.0.

This module provides utilities for compiling, saving, and diffing concept cards
with evidence-based claims and provenance tracking.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from .models import ConceptCard, Evidence, Claim, Provenance


def compile_card(
    sources: List[str], slug: str, definition: str, claims: List[Dict[str, Any]]
) -> ConceptCard:
    """
    Compile a concept card from sources and claims.

    Args:
        sources: List of source identifiers (e.g., RFC numbers)
        slug: Concept slug (e.g., "ip-basics")
        definition: Core definition of the concept
        claims: List of claim dictionaries with evidence references

    Returns:
        Compiled ConceptCard with evidence and provenance
    """
    # Generate concept ID
    concept_id = f"concept:{slug}:v1"

    # Collect evidence from sources
    evidence = {}
    evidence_refs = []

    for source in sources:
        # Generate evidence hash
        content = f"Source: {source}"
        sha256 = hashlib.sha256(content.encode()).hexdigest()

        evidence[sha256] = Evidence(
            sha256=sha256, length=len(content), source=source, content=content
        )
        evidence_refs.append(sha256)

    # Create claims with evidence references
    compiled_claims = []
    for claim_data in claims:
        claim = Claim(
            claim=claim_data["claim"],
            evidence_refs=claim_data.get("evidence_refs", evidence_refs),
            confidence=claim_data.get("confidence", 0.8),
        )
        compiled_claims.append(claim)

    # Create provenance
    provenance = Provenance(
        index_root="/data/index",
        build_time=datetime.utcnow().isoformat(),
        compiler_version="1.0.0",
        evidence_count=len(evidence),
    )

    return ConceptCard(
        id=concept_id,
        definition=definition,
        claims=compiled_claims,
        evidence=evidence,
        provenance=provenance,
        tags=claims[0].get("tags", []),
        approved=False,
    )


def save_card(card: ConceptCard, output_dir: str = "data/concepts") -> str:
    """
    Save a concept card to disk.

    Args:
        card: ConceptCard to save
        output_dir: Directory to save the card

    Returns:
        Path to saved card file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Extract slug from ID
    slug = card.id.split(":")[1]
    filename = f"{slug}.json"
    filepath = output_path / filename

    # Convert to dict and save
    card_dict = card.model_dump()
    with open(filepath, "w") as f:
        json.dump(card_dict, f, indent=2)

    return str(filepath)


def diff_cards(card_a: ConceptCard, card_b: ConceptCard) -> Dict[str, Any]:
    """
    Compare two concept cards and return differences.

    Args:
        card_a: First concept card
        card_b: Second concept card

    Returns:
        Dictionary with differences
    """
    diff = {
        "definition_changed": card_a.definition != card_b.definition,
        "claims_added": [],
        "claims_removed": [],
        "claims_modified": [],
        "evidence_added": [],
        "evidence_removed": [],
        "tags_changed": set(card_a.tags) != set(card_b.tags),
        "approved_changed": card_a.approved != card_b.approved,
    }

    # Compare claims
    claims_a = {claim.claim: claim for claim in card_a.claims}
    claims_b = {claim.claim: claim for claim in card_b.claims}

    for claim_text in claims_b:
        if claim_text not in claims_a:
            diff["claims_added"].append(claim_text)

    for claim_text in claims_a:
        if claim_text not in claims_b:
            diff["claims_removed"].append(claim_text)
        else:
            # Check if claim was modified
            claim_a = claims_a[claim_text]
            claim_b = claims_b[claim_text]
            if (
                claim_a.evidence_refs != claim_b.evidence_refs
                or claim_a.confidence != claim_b.confidence
            ):
                diff["claims_modified"].append(claim_text)

    # Compare evidence
    evidence_a = set(card_a.evidence.keys())
    evidence_b = set(card_b.evidence.keys())

    diff["evidence_added"] = list(evidence_b - evidence_a)
    diff["evidence_removed"] = list(evidence_a - evidence_b)

    return diff


def load_card(filepath: str) -> ConceptCard:
    """
    Load a concept card from disk.

    Args:
        filepath: Path to card file

    Returns:
        Loaded ConceptCard
    """
    with open(filepath, "r") as f:
        card_dict = json.load(f)

    return ConceptCard.model_validate(card_dict)


def validate_card(card: ConceptCard) -> List[str]:
    """
    Validate a concept card and return any issues.

    Args:
        card: ConceptCard to validate

    Returns:
        List of validation issues
    """
    issues = []

    # Check ID format
    if not card.id.startswith("concept:") or not card.id.endswith(":v1"):
        issues.append("Invalid concept ID format")

    # Check definition length
    if len(card.definition) < 10:
        issues.append("Definition too short")

    # Check claims
    if not card.claims:
        issues.append("No claims provided")

    # Check evidence references
    evidence_keys = set(card.evidence.keys())
    for claim in card.claims:
        for ref in claim.evidence_refs:
            if ref not in evidence_keys:
                issues.append(f"Evidence reference {ref} not found in evidence")

    # Check confidence scores
    for claim in card.claims:
        if not 0.0 <= claim.confidence <= 1.0:
            issues.append(f"Invalid confidence score: {claim.confidence}")

    return issues
