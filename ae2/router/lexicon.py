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

# OSPF-specific terms for neighbor issue detection
OSPF_TERMS: Set[str] = {
    "ospf",
    "ospfv2",
    "ospfv3",
    "lsa",
    "hello",
    "dead timer",
    "dr",
    "bdr",
    "neighbor",
    "adjacency",
    "area",
    "designated router",
    "full",
    "2-way",
    "exstart",
    "loading",
}

# BGP-specific terms for neighbor issue detection
BGP_TERMS: Set[str] = {
    "bgp",
    "border gateway protocol",
    "peer",
    "session",
    "route",
    "as",
    "autonomous system",
    "opensent",
    "openconfirm",
    "established",
    "idle",
    "active",
    "connect",
}

# TCP-specific terms for handshake issue detection
TCP_TERMS: Set[str] = {
    "tcp",
    "syn",
    "syn-ack",
    "handshake",
    "three way",
    "3-way",
    "reset",
    "rst",
    "timeout",
    "refused",
    "connection refused",
    "mss",
    "pmtud",
    "mtu blackhole",
    "blackhole",
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

# Vendor inference hints with tokens and interface prefixes
VENDOR_HINTS = {
    "iosxe": {
        "tokens": {"iosxe", "ios-xe", "cisco ios xe", "cisco xe", "cisco ios"},
        "if_prefixes": {
            "gi",
            "gigabitethernet",
            "te",
            "tengigabitethernet",
            "fa",
            "fastethernet",
        },
    },
    "junos": {
        "tokens": {"junos", "juniper"},
        "if_prefixes": {"ge-", "xe-", "et-", "ae", "lo0"},
    },
    "nxos": {
        "tokens": {"nxos", "nx-os", "nexus"},
        "if_prefixes": {"eth", "ethernet"},
    },
    "eos": {
        "tokens": {"eos", "arista"},
        "if_prefixes": {"et", "ethernet"},
    },
}

# Canonical interface expansions for normalization
IF_CANON = {
    r"^gi(\d.*)$": r"gigabitethernet\1",
    r"^te(\d.*)$": r"tengigabitethernet\1",
    r"^fa(\d.*)$": r"fastethernet\1",
    r"^eth(\d.*)$": r"ethernet\1",
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

# Playbook slug mappings for troubleshooting
PLAYBOOK_SLUG_MAP: Dict[str, str] = {
    "ospf": "ospf-neighbor-down",
    "ospf neighbor": "ospf-neighbor-down",
    "ospf neighbor down": "ospf-neighbor-down",
    "ospf stuck": "ospf-neighbor-down",
    "ospf exstart": "ospf-neighbor-down",
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
