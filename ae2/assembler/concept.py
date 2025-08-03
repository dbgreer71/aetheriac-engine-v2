"""
Concept assembler for concept card responses.

This module assembles concept responses by loading concept cards from the
ConceptStore and returning their content with citations.
"""

from typing import Dict, Any
from ..concepts.store import ConceptStore


def assemble_concept(
    target_slug: str, query: str, concept_store: ConceptStore, pull: bool = False
) -> Dict[str, Any]:
    """
    Assemble a concept response from concept card.

    Args:
        target_slug: Concept slug (e.g., "concept:arp:v1")
        query: Original user query
        concept_store: ConceptStore for loading cards
        pull: Whether to attempt compilation if card not found

    Returns:
        Dictionary with card content, citations, and metadata
    """
    try:
        # Load the concept card
        card = concept_store.load(target_slug)

        # Extract card content
        card_dict = card.model_dump()

        # Get citations from card evidence
        citations = []
        for claim in card.claims:
            for evidence in claim.evidence:
                # Handle both enum and string types
                evidence_type = (
                    evidence.type.value
                    if hasattr(evidence.type, "value")
                    else str(evidence.type)
                )
                if evidence_type == "rfc_section":
                    # Parse RFC section from path_or_url
                    citation = {
                        "rfc": _extract_rfc_from_url(evidence.path_or_url),
                        "section": _extract_section_from_url(evidence.path_or_url),
                        "title": evidence.excerpt[:100] if evidence.excerpt else "",
                        "url": evidence.path_or_url,
                    }
                    citations.append(citation)

        # Add definition citation
        if card.definition:
            citations.append(
                {
                    "rfc": card.definition.rfc_number,
                    "section": card.definition.section,
                    "title": card.definition.text[:100],
                    "url": card.definition.url,
                }
            )

        return {
            "card": card_dict,
            "citations": citations,
            "confidence": 0.8,  # High confidence for existing cards
            "source_slug": target_slug,
            "stale": card_dict.get("stale", False),
        }

    except FileNotFoundError:
        if pull:
            # Try to compile the concept
            try:

                # This would need the index store, but we don't have it here
                # For now, return error
                return {
                    "error": f"Concept card {target_slug} not found and pull compilation not implemented",
                    "citations": [],
                    "confidence": 0.0,
                    "source_slug": target_slug,
                }
            except Exception as e:
                return {
                    "error": f"Failed to compile concept {target_slug}: {str(e)}",
                    "citations": [],
                    "confidence": 0.0,
                    "source_slug": target_slug,
                }
        else:
            return {
                "error": f"Concept card {target_slug} not found",
                "citations": [],
                "confidence": 0.0,
                "source_slug": target_slug,
            }

    except Exception as e:
        return {
            "error": f"Failed to load concept card {target_slug}: {str(e)}",
            "citations": [],
            "confidence": 0.0,
            "source_slug": target_slug,
        }


def _extract_rfc_from_url(url: str) -> int:
    """Extract RFC number from URL."""
    try:
        if "rfc" in url.lower():
            # Look for RFC number in URL
            import re

            match = re.search(r"rfc(\d+)", url.lower())
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return 2328  # Default fallback


def _extract_section_from_url(url: str) -> str:
    """Extract section from URL."""
    try:
        if "section" in url.lower():
            # Look for section in URL
            import re

            match = re.search(r"section[=#]?([^&]+)", url.lower())
            if match:
                return match.group(1)
    except Exception:
        pass
    return "1.1"  # Default fallback
