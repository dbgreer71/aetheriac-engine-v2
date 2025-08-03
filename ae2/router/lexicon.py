"""
Router lexicon for intent detection and target selection.

This module provides keyword sets and canonical term mappings for
deterministic query routing to definition, concept, or troubleshooting paths.
"""

from typing import Dict, List, Set, Tuple


# Intent detection keywords
TROUBLESHOOT_KEYWORDS: Set[str] = {
    "neighbor down",
    "down",
    "stuck in exstart",
    "mtu mismatch",
    "auth mismatch",
    "troubleshoot",
    "why isn't",
    "not forming adjacency",
    "not working",
    "broken",
    "failed",
    "issue",
    "problem",
    "tcp 179",
    "gtsm",
    "ttl",
    "hop limit",
    "session state",
    "established",
    "idle",
    "active",
    "connect",
    "opensent",
    "openconfirm",
    "port 179",
    "multihop",
    # BGP-specific troubleshooting terms
    "bgp neighbor down",
    "bgp peer down",
    "bgp session down",
    "bgp not established",
    "bgp idle state",
    "bgp active state",
    "bgp connect state",
    "bgp opensent state",
    "bgp openconfirm state",
    "bgp flap",
    "bgp dampening",
    "ebgp multihop",
    "bgp authentication",
    "bgp md5",
    "bgp keychain",
    "bgp timers",
    "bgp keepalive",
    "bgp holdtime",
    "bgp afi safi",
    "bgp address family",
    "bgp route policy",
    "bgp route map",
    "bgp asn mismatch",
    "bgp local as",
    "bgp remote as",
}

# Off-topic terms (disjoint from networking)
OFFTOPIC_TERMS: Set[str] = {
    "weather",
    "temperature",
    "cooking",
    "recipe",
    "finance",
    "stock",
    "movie",
    "netflix",
    "pizza",
    "gym",
    "horoscope",
    "lottery",
    "crypto",
    "booking",
    "restaurant",
    "travel",
    "cook",
    "pasta",
    "computer",
    "windows",
    "python",
    "database",
    "web development",
    "machine learning",
    "cloud computing",
}

# Ambiguous patterns that force abstain unless paired with protocol anchors
AMBIGUOUS_PATTERNS: Set[str] = {
    "best practices",
    "overview",
    "tutorial",
    "guide",
    "router",
    "protocol",
    "interface",
    "design",
    "help",
    "advice",
    "tips",
    "connection",
    "security",
    "performance",
    "monitoring",
    "configuration",
    "troubleshooting",
    "documentation",
    "training",
    "certification",
    "vendor",
    "hardware",
    "software",
}

CONCEPT_KEYWORDS: Set[str] = {
    "concept",
    "concept card",
    "evidence",
    "claims",
    "prove",
    "explain with evidence",
    "show me",
    "get concept",
}

# Protocol keywords for troubleshooting context
PROTOCOL_KEYWORDS: Set[str] = {
    "ospf",
    "bgp",
    "eigrp",
    "isis",
    "rip",
    "arp",
    "tcp",
    "udp",
    "ip",
}

# BGP-specific terms for robust signal detection
BGP_TERMS: Set[str] = {
    "bgp",
    "neighbor",
    "peer",
    "idle",
    "active",
    "opensent",
    "openconfirm",
    "established",
    "fsm",
    "flap",
    "ttl",
    "gtsm",
    "multihop",
    "md5",
    "session",
    "dampening",
    "authentication",
    "keychain",
    "timers",
    "keepalive",
    "holdtime",
    "afi",
    "safi",
    "address family",
    "route policy",
    "route map",
    "asn",
    "local as",
    "remote as",
}

# TCP-specific terms for handshake failure detection
TCP_TERMS: Set[str] = {
    "tcp",
    "syn",
    "syn-ack",
    "handshake",
    "three way",
    "reset",
    "rst",
    "timeout",
    "refused",
    "mss",
    "pmtud",
    "blackhole",
    "connection",
    "port",
    "listen",
    "established",
    "close",
    "fin",
    "ack",
}

# Vendor keywords for troubleshooting
VENDOR_KEYWORDS: Set[str] = {
    "iosxe",
    "ios",
    "cisco",
    "junos",
    "juniper",
    "nxos",
    "arista",
    "eos",
}

# Canonical term to RFC number mapping for definitional queries
CANONICAL_RFC_MAP: Dict[str, int] = {
    "ospf": 2328,
    "arp": 826,
    "bgp": 4271,
    "tcp": 9293,
    "ip": 791,
    "private addressing": 1918,
    "router reqs": 1812,
    "ipv6": 8200,
    "icmp": 792,
    "dns": 1035,
    "dhcp": 2131,
    "vlan": 8021,
    "stp": 8021,
    "rstp": 8021,
    "mstp": 8021,
}

# LEXICON for the definitional router
LEXICON: Dict[str, List[str]] = {
    "protocol_terms": [
        "ospf",
        "arp",
        "tcp",
        "udp",
        "dns",
    ],
}

# Playbook slug mappings for troubleshooting
PLAYBOOK_SLUG_MAP: Dict[str, str] = {
    "ospf neighbor": "ospf-neighbor-down",
    "ospf neighbor down": "ospf-neighbor-down",
    "ospf stuck": "ospf-neighbor-down",
    "ospf exstart": "ospf-neighbor-down",
    "bgp": "bgp-neighbor-down",
    "bgp neighbor": "bgp-neighbor-down",
    "bgp neighbor down": "bgp-neighbor-down",
    "tcp": "tcp-handshake",
    "tcp handshake": "tcp-handshake",
    "tcp connection": "tcp-handshake",
    "tcp timeout": "tcp-handshake",
    "tcp refused": "tcp-handshake",
    "bgp session": "bgp-neighbor-down",
    "bgp down": "bgp-neighbor-down",
    "bgp peer": "bgp-neighbor-down",
    "bgp peer down": "bgp-neighbor-down",
    "bgp idle": "bgp-neighbor-down",
    "bgp active": "bgp-neighbor-down",
    "bgp connect": "bgp-neighbor-down",
    "bgp opensent": "bgp-neighbor-down",
    "bgp openconfirm": "bgp-neighbor-down",
    "bgp established": "bgp-neighbor-down",
    # Enhanced BGP mappings
    "bgp session down": "bgp-neighbor-down",
    "bgp not established": "bgp-neighbor-down",
    "bgp idle state": "bgp-neighbor-down",
    "bgp active state": "bgp-neighbor-down",
    "bgp connect state": "bgp-neighbor-down",
    "bgp opensent state": "bgp-neighbor-down",
    "bgp openconfirm state": "bgp-neighbor-down",
    "bgp flap": "bgp-neighbor-down",
    "bgp dampening": "bgp-neighbor-down",
    "ebgp multihop": "bgp-neighbor-down",
    "bgp authentication": "bgp-neighbor-down",
    "bgp md5": "bgp-neighbor-down",
    "bgp keychain": "bgp-neighbor-down",
    "bgp timers": "bgp-neighbor-down",
    "bgp keepalive": "bgp-neighbor-down",
    "bgp holdtime": "bgp-neighbor-down",
    "bgp afi safi": "bgp-neighbor-down",
    "bgp address family": "bgp-neighbor-down",
    "bgp route policy": "bgp-neighbor-down",
    "bgp route map": "bgp-neighbor-down",
    "bgp asn mismatch": "bgp-neighbor-down",
    "bgp local as": "bgp-neighbor-down",
    "bgp remote as": "bgp-neighbor-down",
}


def extract_troubleshoot_terms(query: str) -> Tuple[bool, List[str], str]:
    """
    Extract troubleshooting terms from query.

    Returns:
        (is_troubleshoot, matched_terms, vendor)
    """
    query_lower = query.lower()
    matched_terms = []
    vendor = None

    # Check for troubleshoot keywords
    for keyword in TROUBLESHOOT_KEYWORDS:
        if keyword in query_lower:
            matched_terms.append(keyword)

    # Check for vendor keywords
    for vendor_keyword in VENDOR_KEYWORDS:
        if vendor_keyword in query_lower:
            vendor = vendor_keyword
            matched_terms.append(vendor_keyword)
            break

    # Check for protocol keywords
    for protocol in PROTOCOL_KEYWORDS:
        if protocol in query_lower:
            matched_terms.append(protocol)

    is_troubleshoot = len(matched_terms) >= 2  # Need at least protocol + issue

    return is_troubleshoot, matched_terms, vendor


def extract_concept_terms(query: str) -> Tuple[bool, List[str]]:
    """
    Extract concept-related terms from query.

    Returns:
        (is_concept, matched_terms)
    """
    query_lower = query.lower()
    matched_terms = []

    for keyword in CONCEPT_KEYWORDS:
        if keyword in query_lower:
            matched_terms.append(keyword)

    is_concept = len(matched_terms) > 0

    return is_concept, matched_terms


def find_canonical_rfc(query: str) -> Tuple[int, List[str]]:
    """
    Find canonical RFC for definitional query.

    Returns:
        (rfc_number, matched_terms)
    """
    query_lower = query.lower()
    matched_terms = []

    for term, rfc_num in CANONICAL_RFC_MAP.items():
        if term in query_lower:
            matched_terms.append(term)
            return rfc_num, matched_terms

    # Default to OSPF if no match found
    return 2328, ["ospf"]


def find_playbook_slug(query: str) -> Tuple[str, List[str]]:
    """
    Find playbook slug for troubleshooting query.

    Returns:
        (playbook_slug, matched_terms)
    """
    query_lower = query.lower()
    matched_terms = []

    for term, slug in PLAYBOOK_SLUG_MAP.items():
        if term in query_lower:
            matched_terms.append(term)
            return slug, matched_terms

    # Default to OSPF neighbor down
    return "ospf-neighbor-down", ["ospf neighbor"]


def get_confidence_score(matched_terms: List[str], intent: str) -> float:
    """
    Calculate confidence score based on matched terms and intent.

    Returns:
        confidence score (0.0 to 1.0)
    """
    if intent == "TROUBLESHOOT":
        # Higher confidence with more specific terms
        if len(matched_terms) >= 3:
            return 0.9
        elif len(matched_terms) >= 2:
            return 0.7
        else:
            return 0.5
    elif intent == "CONCEPT":
        # High confidence for concept keywords
        return 0.8
    else:  # DEFINE
        # Moderate confidence for definitional queries
        return 0.6
