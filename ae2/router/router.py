"""
Unified router for query intent detection and target selection.

This module provides deterministic routing logic to choose between
definition, concept, or troubleshooting paths based on query analysis.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from .lexicon import (
    extract_troubleshoot_terms,
    extract_concept_terms,
    find_canonical_rfc,
    find_playbook_slug,
    get_confidence_score,
)


@dataclass
class RouteDecision:
    """Result of query routing decision."""

    intent: str  # "DEFINE", "CONCEPT", "TROUBLESHOOT"
    target: str  # RFC number, concept slug, or playbook slug
    confidence: float  # 0.0 to 1.0
    matches: List[str]  # Matched terms/keywords
    notes: str  # Additional context
    mode_used: str  # "hybrid", "tfidf", "bm25"


def route(query: str, stores: Dict[str, Any]) -> RouteDecision:
    """
    Route a query to the appropriate intent and target.

    Args:
        query: User query string
        stores: Dictionary containing IndexStore and ConceptStore

    Returns:
        RouteDecision with intent, target, and metadata
    """
    query_lower = query.lower()

    # Check for troubleshooting intent first (highest priority)
    is_troubleshoot, troubleshoot_matches, vendor = extract_troubleshoot_terms(query)
    if is_troubleshoot:
        playbook_slug, playbook_matches = find_playbook_slug(query)
        all_matches = troubleshoot_matches + playbook_matches

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable

        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        if vendor and vendor not in allowed_vendors:
            return RouteDecision(
                intent="DEFINE",
                target="2328",  # Default to OSPF RFC
                confidence=0.3,
                matches=all_matches,
                notes=f"Troubleshooting requested but vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                mode_used="hybrid",
            )

        return RouteDecision(
            intent="TROUBLESHOOT",
            target=playbook_slug,
            confidence=get_confidence_score(all_matches, "TROUBLESHOOT"),
            matches=all_matches,
            notes=f"Troubleshooting detected for {playbook_slug}"
            + (f" on {vendor}" if vendor else ""),
            mode_used="hybrid",
        )

    # Check for concept intent
    is_concept, concept_matches = extract_concept_terms(query)
    if is_concept:
        # Try to find concept slug from query
        concept_store = stores.get("concept_store")
        if concept_store:
            # Extract potential concept name from query
            potential_concepts = ["arp", "ospf", "bgp", "tcp", "ip", "default route"]
            for concept in potential_concepts:
                if concept in query_lower:
                    # Check if concept card exists
                    try:
                        concept_store.load(f"concept:{concept}:v1")
                        return RouteDecision(
                            intent="CONCEPT",
                            target=f"concept:{concept}:v1",
                            confidence=get_confidence_score(
                                concept_matches + [concept], "CONCEPT"
                            ),
                            matches=concept_matches + [concept],
                            notes=f"Concept card found for {concept}",
                            mode_used="hybrid",
                        )
                    except FileNotFoundError:
                        # Concept card doesn't exist, fall back to definition
                        pass

        # If no concept card found, fall back to definition
        rfc_num, rfc_matches = find_canonical_rfc(query)
        return RouteDecision(
            intent="DEFINE",
            target=str(rfc_num),
            confidence=0.4,  # Lower confidence due to fallback
            matches=concept_matches + rfc_matches,
            notes="Concept requested but card not found, falling back to definition",
            mode_used="hybrid",
        )

    # Default to definition intent
    rfc_num, rfc_matches = find_canonical_rfc(query)
    return RouteDecision(
        intent="DEFINE",
        target=str(rfc_num),
        confidence=get_confidence_score(rfc_matches, "DEFINE"),
        matches=rfc_matches,
        notes=f"Definition query for RFC {rfc_num}",
        mode_used="hybrid",
    )


def extract_context_from_query(query: str) -> Dict[str, Any]:
    """
    Extract context parameters from query for troubleshooting.

    Returns:
        Dictionary with vendor, iface, area, auth, mtu if found
    """
    query_lower = query.lower()
    context = {}

    # Extract vendor
    vendors = ["iosxe", "ios", "cisco", "junos", "juniper"]
    for vendor in vendors:
        if vendor in query_lower:
            context["vendor"] = vendor
            break

    # Extract interface patterns
    interface_patterns = [r"g0/0", r"gigabitethernet0/0", r"ge-0/0/0", r"ethernet0/0"]
    for pattern in interface_patterns:
        if pattern in query_lower:
            context["iface"] = pattern
            break

    # Extract area
    if "area" in query_lower:
        # Simple extraction - could be enhanced
        context["area"] = "0.0.0.0"

    # Extract authentication
    if "auth" in query_lower or "md5" in query_lower:
        context["auth"] = "md5"

    # Extract MTU
    if "mtu" in query_lower:
        context["mtu"] = 1500  # Default MTU

    return context
