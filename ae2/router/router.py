"""
Unified router for query intent detection and target selection.

This module provides deterministic routing logic to choose between
definition, concept, or troubleshooting paths based on query analysis.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .lexicon import (
    extract_troubleshoot_terms,
    extract_concept_terms,
    find_canonical_rfc,
    get_confidence_score,
    OSPF_TERMS,
    BGP_TERMS,
    TCP_TERMS,
)

# Import cache if available
try:
    from ..common.ttl_lru import cache_get, cache_set

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


@dataclass
class TroubleshootCandidate:
    """Candidate for troubleshooting routing."""

    intent: str = "TROUBLESHOOT"
    target: str = ""
    score: int = 0
    reasons: List[str] = None
    features: Dict[str, Any] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
        if self.features is None:
            self.features = {}


@dataclass
class RouteDecision:
    """Result of query routing decision."""

    intent: str  # "DEFINE", "CONCEPT", "TROUBLESHOOT"
    target: str  # RFC number, concept slug, or playbook slug
    confidence: float  # 0.0 to 1.0
    matches: List[str]  # Matched terms/keywords
    notes: str  # Additional context
    mode_used: str  # "hybrid", "tfidf", "bm25"


def _extract_protocol_features(query: str, vendor: Optional[str]) -> Dict[str, Any]:
    """Extract protocol-specific features from query."""
    features = {"vendor": vendor}

    # Extract IP addresses, ports, areas, interfaces
    import re

    # IP addresses
    ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    ips = re.findall(ip_pattern, query)
    if ips:
        features["peer_ip"] = ips[0]

    # Port numbers
    port_pattern = r":(\d{1,5})\b"
    ports = re.findall(port_pattern, query)
    if ports:
        features["port"] = int(ports[0])

    # Areas (OSPF)
    area_pattern = r"\barea\s+([0-9.]+)\b"
    areas = re.findall(area_pattern, query)
    if areas:
        features["area"] = areas[0]

    # Interfaces
    interface_patterns = [
        r"\b(g0/\d+|GigabitEthernet\d+/\d+)\b",
        r"\b(ge-\d+/\d+/\d+|xe-\d+/\d+/\d+)\b",
        r"\b(Ethernet\d+/\d+)\b",
    ]
    for pattern in interface_patterns:
        interfaces = re.findall(pattern, query)
        if interfaces:
            features["interface"] = interfaces[0]
            break

    return features


def _calculate_base_score(
    vendor: Optional[str], protocol_terms: bool, state_terms: bool
) -> int:
    """Calculate base score for troubleshooting candidate."""
    if vendor and protocol_terms and state_terms:
        return 3  # vendor + protocol + state
    elif protocol_terms and state_terms:
        return 2  # protocol + state
    elif protocol_terms:
        return 1  # protocol only
    return 0


def _apply_tie_breakers(
    candidates: List[TroubleshootCandidate],
) -> List[TroubleshootCandidate]:
    """Apply tie-breakers to sort candidates by priority."""

    def tie_breaker_score(candidate: TroubleshootCandidate) -> tuple:
        features = candidate.features

        # Tie-breaker 1: Exact vendor detected
        vendor_score = 0
        if features.get("vendor") in ["iosxe", "junos", "nxos"]:
            vendor_score = 1

        # Tie-breaker 2: Presence of relevant tokens
        token_score = 0
        if (
            features.get("peer_ip")
            or features.get("port")
            or features.get("area")
            or features.get("interface")
        ):
            token_score = 1

        # Tie-breaker 3: Fewer abstain triggers (inverse - higher is better)
        # This is handled by the base score already

        return (-candidate.score, -vendor_score, -token_score)

    return sorted(candidates, key=tie_breaker_score)


def _detect_protocol_candidates(
    query: str, vendor: Optional[str]
) -> List[TroubleshootCandidate]:
    """Detect all protocol candidates from query."""
    query_lower = query.lower()
    candidates = []

    # Extract features once
    features = _extract_protocol_features(query, vendor)

    # BGP detection - require explicit BGP terms
    bgp_terms_present = any(term in query_lower for term in BGP_TERMS)
    bgp_state_terms = any(
        term in query_lower
        for term in [
            "down",
            "not established",
            "opensent",
            "openconfirm",
            "active",
            "idle",
        ]
    )

    if bgp_terms_present:
        base_score = _calculate_base_score(vendor, bgp_terms_present, bgp_state_terms)
        if base_score >= 1:
            candidate = TroubleshootCandidate(
                target="bgp-neighbor-down",
                score=base_score,
                reasons=["bgp_terms"]
                + (["bgp_state_terms"] if bgp_state_terms else []),
                features=features.copy(),
            )
            candidates.append(candidate)

    # OSPF detection - require explicit OSPF terms
    ospf_terms_present = any(term in query_lower for term in OSPF_TERMS)
    ospf_state_terms = any(
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

    if ospf_terms_present:
        base_score = _calculate_base_score(vendor, ospf_terms_present, ospf_state_terms)
        if base_score >= 1:
            candidate = TroubleshootCandidate(
                target="ospf-neighbor-down",
                score=base_score,
                reasons=["ospf_terms"]
                + (["ospf_state_terms"] if ospf_state_terms else []),
                features=features.copy(),
            )
            candidates.append(candidate)

    # TCP detection
    tcp_terms_present = any(term in query_lower for term in TCP_TERMS)
    tcp_state_terms = any(
        term in query_lower
        for term in [
            "timeout",
            "refused",
            "reset",
            "rst",
            "syn",
            "syn-ack",
            "blackhole",
            "mss",
            "pmtud",
        ]
    )

    if tcp_terms_present:
        base_score = _calculate_base_score(vendor, tcp_terms_present, tcp_state_terms)
        if base_score >= 1:
            candidate = TroubleshootCandidate(
                target="tcp-handshake",
                score=base_score,
                reasons=["tcp_terms"]
                + (["tcp_state_terms"] if tcp_state_terms else []),
                features=features.copy(),
            )
            candidates.append(candidate)

    return candidates


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

    def _cache_and_return(decision: RouteDecision) -> RouteDecision:
        """Cache the decision and return it."""
        if CACHE_AVAILABLE:
            cache_key = f"route:{query}"
            cache_set(cache_key, decision)
        return decision

    # Check for troubleshooting intent first (highest priority)
    is_troubleshoot, troubleshoot_matches, vendor = extract_troubleshoot_terms(query)

    # Multi-protocol ranking for troubleshooting
    if is_troubleshoot:
        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable
        if vendor and vendor not in allowed_vendors:
            return _cache_and_return(
                RouteDecision(
                    intent="DEFINE",
                    target="2328",  # Default to OSPF RFC
                    confidence=0.3,
                    matches=troubleshoot_matches,
                    notes=f"Troubleshooting requested but vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                    mode_used="hybrid",
                )
            )

        # Detect all protocol candidates
        candidates = _detect_protocol_candidates(query, vendor)

        # Apply tie-breakers and sort
        ranked_candidates = _apply_tie_breakers(candidates)

        # Check if any candidate passes minimum score
        if not ranked_candidates:
            return _cache_and_return(
                RouteDecision(
                    intent="ABSTAIN",
                    target="",
                    confidence=0.1,
                    matches=troubleshoot_matches,
                    notes=f"No protocol candidates found with sufficient score. Query: {query}",
                    mode_used="hybrid",
                )
            )

        # Select winner (highest ranked)
        winner = ranked_candidates[0]

        # Prepare notes with ranking information
        ranked_info = []
        for i, candidate in enumerate(ranked_candidates[:3]):  # Cap to last 3
            ranked_info.append(
                {
                    "target": candidate.target,
                    "score": candidate.score,
                    "reasons": candidate.reasons[
                        :3
                    ],  # Cap reasons to keep logs compact
                }
            )

        notes_data = {
            "ranked": ranked_info,
            "winner": winner.target,
            "reasons": winner.reasons[:3],  # Cap reasons to keep logs compact
        }

        return _cache_and_return(
            RouteDecision(
                intent="TROUBLESHOOT",
                target=winner.target,
                confidence=get_confidence_score(
                    troubleshoot_matches + winner.reasons, "TROUBLESHOOT"
                ),
                matches=troubleshoot_matches + winner.reasons,
                notes=str(notes_data),  # Convert to string for compatibility
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
                if concept in query.lower():
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
