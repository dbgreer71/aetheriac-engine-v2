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
    OSPF_TERMS,
)

# Import cache if available
try:
    from ..common.ttl_lru import cache_get, cache_set

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


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
    # Check cache first
    if CACHE_AVAILABLE:
        cache_key = f"route:{query}"
        cached_result = cache_get(cache_key)
        if cached_result is not None:
            return cached_result

    query_lower = query.lower()

    def _cache_and_return(decision: RouteDecision) -> RouteDecision:
        """Cache the decision and return it."""
        if CACHE_AVAILABLE:
            cache_key = f"route:{query}"
            cache_set(cache_key, decision)
        return decision

    # Check for troubleshooting intent first (highest priority)
    is_troubleshoot, troubleshoot_matches, vendor = extract_troubleshoot_terms(query)

    # Special handling for OSPF neighbor-down queries - prefer TROUBLESHOOT
    ospf_terms_present = any(term in query_lower for term in OSPF_TERMS)
    ospf_state_terms_present = any(
        term in query_lower
        for term in [
            "down",
            "not full",
            "stuck",
            "2-way",
            "init",
            "exstart",
            "loading",
            "dead",
        ]
    )

    if ospf_terms_present and ospf_state_terms_present:
        playbook_slug, playbook_matches = find_playbook_slug(query)
        all_matches = troubleshoot_matches + playbook_matches + ["ospf"]
        reasons = ["ospf+state_terms"]

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable

        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        if vendor and vendor not in allowed_vendors:
            return _cache_and_return(
                RouteDecision(
                    intent="DEFINE",
                    target="2328",  # Default to OSPF RFC
                    confidence=0.3,
                    matches=all_matches,
                    notes=f"OSPF troubleshooting requested but vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                    mode_used="hybrid",
                )
            )

        if vendor:
            reasons.append(f"vendor:{vendor}")

        return _cache_and_return(
            RouteDecision(
                intent="TROUBLESHOOT",
                target="ospf-neighbor-down",
                confidence=get_confidence_score(all_matches, "TROUBLESHOOT"),
                matches=all_matches,
                notes=f"OSPF troubleshooting detected for ospf-neighbor-down on {vendor if vendor else 'unknown vendor'}. Reasons: {', '.join(reasons)}",
                mode_used="hybrid",
            )
        )

    # Additional OSPF detection: vendor present and ospf present
    vendor_present = vendor is not None
    if vendor_present and "ospf" in query_lower:
        playbook_slug, playbook_matches = find_playbook_slug(query)
        all_matches = troubleshoot_matches + playbook_matches + ["ospf", vendor]
        reasons = ["ospf+vendor"]

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable

        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        if vendor not in allowed_vendors:
            return _cache_and_return(
                RouteDecision(
                    intent="DEFINE",
                    target="2328",  # Default to OSPF RFC
                    confidence=0.3,
                    matches=all_matches,
                    notes=f"OSPF troubleshooting requested but vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                    mode_used="hybrid",
                )
            )

        reasons.append(f"vendor:{vendor}")

        return _cache_and_return(
            RouteDecision(
                intent="TROUBLESHOOT",
                target="ospf-neighbor-down",
                confidence=get_confidence_score(all_matches, "TROUBLESHOOT"),
                matches=all_matches,
                notes=f"OSPF troubleshooting detected for ospf-neighbor-down on {vendor}. Reasons: {', '.join(reasons)}",
                mode_used="hybrid",
            )
        )

    if is_troubleshoot:
        playbook_slug, playbook_matches = find_playbook_slug(query)
        all_matches = troubleshoot_matches + playbook_matches

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable

        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        if vendor and vendor not in allowed_vendors:
            return _cache_and_return(
                RouteDecision(
                    intent="DEFINE",
                    target="2328",  # Default to OSPF RFC
                    confidence=0.3,
                    matches=all_matches,
                    notes=f"Troubleshooting requested but vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                    mode_used="hybrid",
                )
            )

        return _cache_and_return(
            RouteDecision(
                intent="TROUBLESHOOT",
                target=playbook_slug,
                confidence=get_confidence_score(all_matches, "TROUBLESHOOT"),
                matches=all_matches,
                notes=f"Troubleshooting detected for {playbook_slug}"
                + (f" on {vendor}" if vendor else ""),
                mode_used="hybrid",
            )
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
                        return _cache_and_return(
                            RouteDecision(
                                intent="CONCEPT",
                                target=f"concept:{concept}:v1",
                                confidence=get_confidence_score(
                                    concept_matches + [concept], "CONCEPT"
                                ),
                                matches=concept_matches + [concept],
                                notes=f"Concept card found for {concept}",
                                mode_used="hybrid",
                            )
                        )
                    except FileNotFoundError:
                        # Concept card doesn't exist, fall back to definition
                        pass

        # If no concept card found, fall back to definition
        rfc_num, rfc_matches = find_canonical_rfc(query)
        return _cache_and_return(
            RouteDecision(
                intent="DEFINE",
                target=str(rfc_num),
                confidence=0.4,  # Lower confidence due to fallback
                matches=concept_matches + rfc_matches,
                notes="Concept requested but card not found, falling back to definition",
                mode_used="hybrid",
            )
        )

    # Default to definition intent
    rfc_num, rfc_matches = find_canonical_rfc(query)
    return _cache_and_return(
        RouteDecision(
            intent="DEFINE",
            target=str(rfc_num),
            confidence=get_confidence_score(rfc_matches, "DEFINE"),
            matches=rfc_matches,
            notes=f"Definition query for RFC {rfc_num}",
            mode_used="hybrid",
        )
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
