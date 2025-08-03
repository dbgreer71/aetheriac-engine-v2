"""
Unified router for query intent detection and target selection.

This module provides deterministic routing logic to choose between
definition, concept, or troubleshooting paths based on query analysis.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .lexicon import (
    extract_troubleshoot_terms,
    extract_concept_terms,
    find_canonical_rfc,
    get_confidence_score,
    OSPF_TERMS,
    BGP_TERMS,
    TCP_TERMS,
    VENDOR_HINTS,
    IF_CANON,
)

# Import cache if available
try:
    from ..common.ttl_lru import cache_get, cache_set

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


def normalize_query(q: str) -> Tuple[str, Dict[str, Any]]:
    """Normalize query for consistent tokenization."""
    raw = q or ""
    s = " ".join(raw.strip().split()).lower()
    # area normalization
    s = re.sub(r"\barea\s+0\b", "area 0.0.0.0", s)
    # interface canonicalization (cheap pass)
    for pat, repl in IF_CANON.items():
        s = re.sub(pat, repl, s)
    return s, {"original": raw}


def infer_vendor(s: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Infer vendor from query tokens and interface prefixes."""
    evid = {"hits": [], "if_hits": []}
    for v, spec in VENDOR_HINTS.items():
        if any(tok in s for tok in spec["tokens"]):
            evid["hits"].append(v)
        # interface prefix hints
        if any(re.search(r"\b" + re.escape(pref), s) for pref in spec["if_prefixes"]):
            evid["if_hits"].append(v)
    # majority vote, tiebreak lexicographically for stability
    candidates = evid["hits"] + evid["if_hits"]
    if not candidates:
        return None, evid
    counts = {}
    for c in candidates:
        counts[c] = counts.get(c, 0) + 1
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    evid["winner"] = best
    evid["counts"] = counts
    return best, evid


@dataclass(frozen=True)
class MatchEvidence:
    """Evidence for a routing match with deterministic scoring."""

    tokens: Dict[str, int]  # e.g., {"bgp": 2, "neighbor": 1, "down": 1}
    rules: List[str]  # e.g., ["bgp_auto_vendor", "bgp_auto_state"]
    ranked_reasons: List[str]  # ordered human text reasons
    score: float  # 0..1


# Thresholds for routing decisions
MIN_CONFIDENCE_ROUTE = 0.60  # below this → ABSTAIN
SHORT_QUERY_TOKEN_MAX = 2  # 1–2 tokens → ABSTAIN unless vendor+proto

PROTO_WEIGHTS = {
    "bgp": 1.15,
    "ospf": 1.05,
    "tcp": 1.00,
    "neighbor": 0.40,
    "down": 0.30,
    "idle": 0.2,
    "2-way": 0.2,
    "syn": 0.2,
    "state": 0.30,  # for idle/2-way/exstart/syn etc
    "vendor": 0.4,
    "peer": 0.2,
    "iface": 0.2,
    "port": 0.15,
    "area": 0.15,
}

TIEBREAK_ORDER = [
    "vendor",
    "protocol",
    "state",
    "ip",
    "iface",
    "port",
    "area",
    "keyword_count",
]


def compute_score(tokens: Dict[str, int], tiebreak: Dict[str, int]) -> float:
    """Compute deterministic score from tokens and tiebreak data."""
    raw = sum(PROTO_WEIGHTS.get(k, 0.1) * v for k, v in tokens.items())
    # deterministic clamp & normalize
    return min(1.0, round(raw / 4.0, 4))


def rank_reasons(
    tokens: Dict[str, int], rules: List[str], tiebreak: Dict[str, int]
) -> List[str]:
    """Generate ranked reasons for routing decision."""
    tb = [f"{k}={tiebreak.get(k,0)}" for k in TIEBREAK_ORDER]
    hits = [
        f"{k}:{v}" for k, v in sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return [
        f"rules:{'|'.join(rules)}",
        f"hits:{','.join(hits)}",
        f"tiebreak:{','.join(tb)}",
    ]


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
    notes: Any  # Additional context (can be dict or str)
    mode_used: str  # "hybrid", "tfidf", "bm25"
    reason_code: Optional[str] = None  # ABSTAIN reason code


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

    # Normalize query and infer vendor
    normalized, norm_meta = normalize_query(query)
    vendor_guess, vend_meta = infer_vendor(normalized)

    # Check for troubleshooting intent first (highest priority)
    is_troubleshoot, troubleshoot_matches, vendor = extract_troubleshoot_terms(
        normalized
    )

    # Multi-protocol ranking for troubleshooting
    if is_troubleshoot:
        # Use inferred vendor if no explicit vendor provided
        if not vendor and vendor_guess:
            vendor = vendor_guess

        # Normalize vendor name
        if vendor == "ios" or vendor == "cisco":
            vendor = "iosxe"

        # Validate vendor for troubleshooting
        allowed_vendors = ["iosxe", "junos"]  # TODO: make configurable
        if vendor and vendor not in allowed_vendors:
            return _cache_and_return(
                RouteDecision(
                    intent="ABSTAIN",
                    target="",
                    confidence=0.3,
                    matches=troubleshoot_matches,
                    notes={
                        "normalized": norm_meta.get("original"),
                        "vendor_inference": vend_meta,
                        "reason": f"Vendor '{vendor}' not supported. Supported: {allowed_vendors}",
                    },
                    mode_used="hybrid",
                    reason_code="UNSUPPORTED_VENDOR",
                )
            )

        # Build tokens, rules, and tiebreak for each protocol path
        query_lower = normalized
        candidates = []

        # BGP path
        bgp_tokens = {}
        bgp_rules = []
        bgp_tiebreak = {
            "vendor": 1 if vendor else 0,
            "protocol": 0,
            "state": 0,
            "ip": 0,
            "iface": 0,
            "port": 0,
            "area": 0,
            "keyword_count": 0,
        }

        if any(term in query_lower for term in BGP_TERMS):
            bgp_tokens["bgp"] = sum(1 for term in BGP_TERMS if term in query_lower)
            bgp_rules.append("bgp_auto_protocol")
            bgp_tiebreak["protocol"] = 1

        if "neighbor" in query_lower:
            bgp_tokens["neighbor"] = query_lower.count("neighbor")
            bgp_rules.append("bgp_auto_neighbor")

        if any(
            state in query_lower
            for state in [
                "down",
                "idle",
                "active",
                "connect",
                "opensent",
                "openconfirm",
                "established",
            ]
        ):
            bgp_tokens["down"] = query_lower.count("down")
            bgp_tokens["idle"] = query_lower.count("idle")
            bgp_rules.append("bgp_auto_state")
            bgp_tiebreak["state"] = 1

        if vendor:
            bgp_tokens["vendor"] = 1
            bgp_rules.append("bgp_auto_vendor")

        # Extract peer IP
        import re

        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ips = re.findall(ip_pattern, query)
        if ips:
            bgp_tokens["peer"] = 1
            bgp_rules.append("bgp_auto_peer")
            bgp_tiebreak["ip"] = 1

        bgp_tiebreak["keyword_count"] = len(bgp_tokens)

        if bgp_tokens:
            bgp_score = compute_score(bgp_tokens, bgp_tiebreak)
            bgp_reasons = rank_reasons(bgp_tokens, bgp_rules, bgp_tiebreak)
            candidates.append(
                ("bgp-neighbor-down", bgp_score, bgp_tokens, bgp_rules, bgp_reasons)
            )

        # TCP path
        tcp_tokens = {}
        tcp_rules = []
        tcp_tiebreak = {
            "vendor": 1 if vendor else 0,
            "protocol": 0,
            "state": 0,
            "ip": 0,
            "iface": 0,
            "port": 0,
            "area": 0,
            "keyword_count": 0,
        }

        if any(term in query_lower for term in TCP_TERMS):
            tcp_tokens["tcp"] = sum(1 for term in TCP_TERMS if term in query_lower)
            tcp_rules.append("tcp_auto_protocol")
            tcp_tiebreak["protocol"] = 1

        if any(
            state in query_lower
            for state in ["syn", "syn-ack", "timeout", "refused", "reset", "rst"]
        ):
            tcp_tokens["syn"] = query_lower.count("syn")
            tcp_rules.append("tcp_auto_state")
            tcp_tiebreak["state"] = 1

        if vendor:
            tcp_tokens["vendor"] = 1
            tcp_rules.append("tcp_auto_vendor")

        # Extract port
        port_pattern = r":(\d{1,5})\b"
        ports = re.findall(port_pattern, query)
        if ports:
            tcp_tokens["port"] = 1
            tcp_rules.append("tcp_auto_port")
            tcp_tiebreak["port"] = 1

        tcp_tiebreak["keyword_count"] = len(tcp_tokens)

        if tcp_tokens:
            tcp_score = compute_score(tcp_tokens, tcp_tiebreak)
            tcp_reasons = rank_reasons(tcp_tokens, tcp_rules, tcp_tiebreak)
            candidates.append(
                ("tcp-handshake", tcp_score, tcp_tokens, tcp_rules, tcp_reasons)
            )

        # OSPF path
        ospf_tokens = {}
        ospf_rules = []
        ospf_tiebreak = {
            "vendor": 1 if vendor else 0,
            "protocol": 0,
            "state": 0,
            "ip": 0,
            "iface": 0,
            "port": 0,
            "area": 0,
            "keyword_count": 0,
        }

        if any(term in query_lower for term in OSPF_TERMS):
            ospf_tokens["ospf"] = sum(1 for term in OSPF_TERMS if term in query_lower)
            ospf_rules.append("ospf_auto_protocol")
            ospf_tiebreak["protocol"] = 1

        if "neighbor" in query_lower:
            ospf_tokens["neighbor"] = query_lower.count("neighbor")
            ospf_rules.append("ospf_auto_neighbor")

        if any(
            state in query_lower
            for state in ["down", "2-way", "exstart", "loading", "full"]
        ):
            ospf_tokens["2-way"] = query_lower.count("2-way")
            ospf_tokens["down"] = query_lower.count("down")
            ospf_rules.append("ospf_auto_state")
            ospf_tiebreak["state"] = 1

        if vendor:
            ospf_tokens["vendor"] = 1
            ospf_rules.append("ospf_auto_vendor")

        # Extract interface
        interface_patterns = [
            r"\b(g0/\d+|GigabitEthernet\d+/\d+)\b",
            r"\b(ge-\d+/\d+/\d+|xe-\d+/\d+/\d+)\b",
            r"\b(Ethernet\d+/\d+)\b",
        ]
        for pattern in interface_patterns:
            interfaces = re.findall(pattern, query)
            if interfaces:
                ospf_tokens["iface"] = 1
                ospf_rules.append("ospf_auto_iface")
                ospf_tiebreak["iface"] = 1
                break

        # Extract area
        area_pattern = r"\barea\s+([0-9.]+)\b"
        areas = re.findall(area_pattern, query)
        if areas:
            ospf_tokens["area"] = 1
            ospf_rules.append("ospf_auto_area")
            ospf_tiebreak["area"] = 1

        ospf_tiebreak["keyword_count"] = len(ospf_tokens)

        if ospf_tokens:
            ospf_score = compute_score(ospf_tokens, ospf_tiebreak)
            ospf_reasons = rank_reasons(ospf_tokens, ospf_rules, ospf_tiebreak)
            candidates.append(
                (
                    "ospf-neighbor-down",
                    ospf_score,
                    ospf_tokens,
                    ospf_rules,
                    ospf_reasons,
                )
            )

        # Deterministic tie-breaks: higher score, then lexicographic target, then longest rules list
        if candidates:
            candidates.sort(key=lambda x: (-x[1], x[0], -len(x[3])))
            winner_target, winner_score, winner_tokens, winner_rules, winner_reasons = (
                candidates[0]
            )

            # Store evidence in notes
            notes_data = {
                "normalized": norm_meta.get("original"),
                "vendor_inference": vend_meta,
                "ranked_reasons": winner_reasons,
                "matches": winner_tokens,
                "rules": winner_rules,
                "confidence": winner_score,
                "candidates": [
                    {"target": target, "score": score, "rules": rules}
                    for target, score, _, rules, _ in candidates[:3]
                ],
            }

            # Apply ABSTAIN guard for low confidence
            if winner_score < MIN_CONFIDENCE_ROUTE:
                return _cache_and_return(
                    RouteDecision(
                        intent="ABSTAIN",
                        target="",
                        confidence=round(winner_score, 3),
                        matches=troubleshoot_matches + list(winner_tokens.keys()),
                        notes={
                            **notes_data,
                            "reason": "below_min_confidence",
                            "min": MIN_CONFIDENCE_ROUTE,
                        },
                        mode_used="hybrid",
                        reason_code="LOW_CONFIDENCE",
                    )
                )

            return _cache_and_return(
                RouteDecision(
                    intent="TROUBLESHOOT",
                    target=winner_target,
                    confidence=winner_score,
                    matches=troubleshoot_matches + list(winner_tokens.keys()),
                    notes=notes_data,
                    mode_used="hybrid",
                )
            )
        else:
            return _cache_and_return(
                RouteDecision(
                    intent="ABSTAIN",
                    target="",
                    confidence=0.1,
                    matches=troubleshoot_matches,
                    notes={
                        "normalized": norm_meta.get("original"),
                        "vendor_inference": vend_meta,
                        "reason": f"No protocol candidates found. Query: {query}",
                    },
                    mode_used="hybrid",
                    reason_code="MISSING_EVIDENCE",
                )
            )

    # Check for off-topic or ambiguous queries
    query_tokens = normalized.split()
    if len(query_tokens) <= SHORT_QUERY_TOKEN_MAX:
        # Check if it's a short but valid query (vendor + protocol)
        has_vendor = any(
            v in normalized for v in ["iosxe", "junos", "cisco", "juniper"]
        )
        has_protocol = any(p in normalized for p in ["bgp", "ospf", "tcp"])
        if not (has_vendor and has_protocol):
            return _cache_and_return(
                RouteDecision(
                    intent="ABSTAIN",
                    target="",
                    confidence=0.1,
                    matches=[],
                    notes={
                        "normalized": norm_meta.get("original"),
                        "vendor_inference": vend_meta,
                        "reason": f"Query too short ({len(query_tokens)} tokens)",
                    },
                    mode_used="hybrid",
                    reason_code="SHORT_QUERY",
                )
            )

    # Check for off-topic queries (no networking terms)
    networking_terms = [
        "bgp",
        "ospf",
        "tcp",
        "ip",
        "neighbor",
        "router",
        "switch",
        "interface",
        "port",
    ]
    has_networking = any(term in normalized for term in networking_terms)
    if not has_networking:
        return _cache_and_return(
            RouteDecision(
                intent="ABSTAIN",
                target="",
                confidence=0.1,
                matches=[],
                notes={
                    "normalized": norm_meta.get("original"),
                    "vendor_inference": vend_meta,
                    "reason": "No networking terms detected",
                },
                mode_used="hybrid",
                reason_code="OFFTOPIC",
            )
        )

    # Check for concept intent
    is_concept, concept_matches = extract_concept_terms(normalized)
    if is_concept:
        # Try to find concept slug from query
        concept_store = stores.get("concept_store")
        if concept_store:
            # Extract potential concept name from query
            potential_concepts = ["arp", "ospf", "bgp", "tcp", "ip", "default route"]
            for concept in potential_concepts:
                if concept in normalized:
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
                                notes={
                                    "normalized": norm_meta.get("original"),
                                    "vendor_inference": vend_meta,
                                    "reason": f"Concept card found for {concept}",
                                },
                                mode_used="hybrid",
                            )
                        )
                    except FileNotFoundError:
                        # Concept card doesn't exist, fall back to definition
                        pass

        # If no concept card found, fall back to definition
        rfc_num, rfc_matches = find_canonical_rfc(normalized)
        return _cache_and_return(
            RouteDecision(
                intent="DEFINE",
                target=str(rfc_num),
                confidence=0.4,  # Lower confidence due to fallback
                matches=concept_matches + rfc_matches,
                notes={
                    "normalized": norm_meta.get("original"),
                    "vendor_inference": vend_meta,
                    "reason": "Concept requested but card not found, falling back to definition",
                },
                mode_used="hybrid",
            )
        )

    # Default to definition intent
    rfc_num, rfc_matches = find_canonical_rfc(normalized)
    return _cache_and_return(
        RouteDecision(
            intent="DEFINE",
            target=str(rfc_num),
            confidence=get_confidence_score(rfc_matches, "DEFINE"),
            matches=rfc_matches,
            notes={
                "normalized": norm_meta.get("original"),
                "vendor_inference": vend_meta,
                "reason": f"Definition query for RFC {rfc_num}",
            },
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
