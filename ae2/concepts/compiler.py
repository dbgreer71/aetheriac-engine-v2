"""
Concept Card compiler.

This module compiles concept cards from RFC search results using the IndexStore.
"""

import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..retriever.index_store import IndexStore
from .models import ConceptCard, Definition, Evidence, Claim, Provenance
from .store import ConceptStore
from .errors import ConceptCompileError


def _compute_sha256(text: str) -> str:
    """Compute SHA256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_definitional_section(section: Dict, slug: str) -> bool:
    """Check if a section is definitional for the given slug.

    Args:
        section: The section dictionary from IndexStore
        slug: The concept slug being compiled

    Returns:
        True if the section is definitional, False otherwise
    """
    title = section.get("title", "").lower()
    section_num = section.get("section", "")

    # Prefer introduction/overview sections
    definitional_keywords = ["introduction", "overview", "terminology", "definition"]
    if any(keyword in title for keyword in definitional_keywords):
        return True

    # Prefer section "1" or "1.1"
    if section_num in ["1", "1.1"]:
        return True

    # Prefer sections starting with "1."
    if section_num.startswith("1."):
        return True

    return False


def _get_preferred_rfc(slug: str) -> Optional[int]:
    """Get the preferred RFC number for a given slug.

    Args:
        slug: The concept slug

    Returns:
        Preferred RFC number or None
    """
    preferences = {
        "arp": 826,
        "ospf": 2328,
        "tcp": 9293,
        "bgp": 4271,
        "ip": 791,
        "dns": 1035,
    }
    return preferences.get(slug.lower())


def _select_best_definition(sections: List[Dict], slug: str) -> Dict:
    """Select the best definitional section from search results.

    Args:
        sections: List of section dictionaries from IndexStore
        slug: The concept slug being compiled

    Returns:
        The best definitional section
    """
    preferred_rfc = _get_preferred_rfc(slug)

    # First, try to find a definitional section in the preferred RFC
    if preferred_rfc:
        for section in sections:
            if section["rfc_number"] == preferred_rfc and _is_definitional_section(
                section, slug
            ):
                return section

    # Then, try to find any definitional section
    for section in sections:
        if _is_definitional_section(section, slug):
            return section

    # Fallback to the highest-scoring section
    return sections[0]


def compile_concept(
    slug: str, index_store: IndexStore, concept_store: Optional[ConceptStore] = None
) -> ConceptCard:
    """Compile a concept card for the given slug.

    Args:
        slug: The concept slug (e.g., "arp", "ospf")
        index_store: The IndexStore instance
        concept_store: Optional ConceptStore for persistence

    Returns:
        The compiled concept card

    Raises:
        ConceptCompileError: If compilation fails due to low confidence or missing data
    """
    # Define minimum score threshold
    MIN_SCORE = float(os.getenv("CONCEPT_MIN_SCORE", "0.05"))

    # Search for relevant sections
    search_results = index_store.search(slug, mode="hybrid", top_k=5)

    if not search_results:
        raise ConceptCompileError(
            "NO_MATCH", f"No search results found for slug: {slug}"
        )

    # Check if the top result has a score below the minimum threshold
    if search_results[0]["score"] < MIN_SCORE:
        # Log telemetry for tuning CONCEPT_MIN_SCORE
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "LOW_CONFIDENCE: query=%s, min_score=%.3f, top_score=%.3f",
            slug,
            MIN_SCORE,
            search_results[0]["score"],
        )
        raise ConceptCompileError(
            "LOW_CONFIDENCE", f"No section above min_score={MIN_SCORE}"
        )

    # Get the full section data for the search results using get_section
    full_sections = []
    for result in search_results:
        try:
            section = index_store.get_section(result["rfc"], result["section"])
            full_sections.append(section)
        except KeyError:
            # Skip sections that can't be found (shouldn't happen with valid search results)
            continue

    if not full_sections:
        raise ConceptCompileError(
            "MISSING_CITATION", f"Could not find full section data for slug: {slug}"
        )

    # Select the best definitional section
    best_section = _select_best_definition(full_sections, slug)

    # Build the definition
    definition_text = best_section.get("excerpt", best_section.get("text", ""))
    definition = Definition(
        text=definition_text,
        rfc_number=best_section["rfc_number"],
        section=best_section["section"],
        url=f"https://www.rfc-editor.org/rfc/rfc{best_section['rfc_number']}.txt",
    )

    # Build claims from other relevant sections
    claims = []
    for section in full_sections[:3]:  # Use top 3 sections for claims
        if section == best_section:
            continue  # Skip the definition section

        # Get the text content for this section
        section_text = section.get("excerpt", section.get("text", ""))
        if not section_text:
            continue  # Skip sections without text

        # Create evidence for this claim
        evidence = Evidence(
            type="rfc",
            url_or_path=f"https://www.rfc-editor.org/rfc/rfc{section['rfc_number']}.txt",
            sha256=_compute_sha256(section_text),
        )

        claim = Claim(
            text=(
                section_text[:200] + "..." if len(section_text) > 200 else section_text
            ),
            evidence=[evidence],
        )
        claims.append(claim)

    # Create the concept card
    card_id = f"concept:{slug}:v1"
    card = ConceptCard(
        id=card_id,
        definition=definition,
        claims=claims,
        provenance=Provenance(built_at=datetime.utcnow()),
    )

    # Save to store if provided
    if concept_store:
        concept_store.save(card)

    return card


def compile_concept_cli(
    slug: str, index_dir: str = "data/index", concepts_dir: str = "data/concepts"
) -> str:
    """CLI wrapper for compiling a concept card.

    Args:
        slug: The concept slug
        index_dir: Directory containing the index
        concepts_dir: Directory to store concept cards

    Returns:
        Path to the saved concept card
    """
    from pathlib import Path

    # Initialize stores
    index_store = IndexStore(Path(index_dir))
    concept_store = ConceptStore(Path(concepts_dir))

    # Compile the concept
    card = compile_concept(slug, index_store, concept_store)

    # Return the path
    card_path = concept_store.concepts_dir / f"{card.id}.json"
    return str(card_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m ae2.concepts.compiler <slug>")
        sys.exit(1)

    slug = sys.argv[1]
    try:
        card_path = compile_concept_cli(slug)
        print(f"Concept card compiled: {card_path}")
    except Exception as e:
        print(f"Error compiling concept card: {e}")
        sys.exit(1)
