"""
Playbook assembler for troubleshooting responses.

This module assembles troubleshooting responses by invoking the existing
playbook engine and returning structured steps with citations.
"""

from typing import Dict, Any
from ..playbooks.engine import run_playbook
from ..playbooks.models import PlayContext
from ..playbooks.utils import compute_steps_hash
from ..retriever.index_store import IndexStore


def assemble_playbook(
    target_slug: str, query: str, store: IndexStore, context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Assemble a playbook response by executing the playbook.

    Args:
        target_slug: Playbook slug (e.g., "ospf-neighbor-down")
        query: Original user query
        store: IndexStore for playbook execution
        context: Optional context parameters (vendor, iface, etc.)

    Returns:
        Dictionary with steps, citations, and metadata
    """
    try:
        # Create play context from query and provided context
        play_context = _create_play_context(query, context)

        # Run the playbook
        result = run_playbook(target_slug, play_context, store)

        # Extract citations from all steps
        all_citations = []
        for step in result.steps:
            for citation in step.citations:
                all_citations.append(
                    {
                        "rfc": citation.rfc,
                        "section": citation.section,
                        "title": citation.title,
                        "url": citation.url,
                    }
                )

        # Convert steps to dictionaries
        steps_dict = []
        for step in result.steps:
            step_dict = {
                "rule_id": step.rule_id,
                "check": step.check,
                "result": step.result,
                "fix": step.fix,
                "verify": step.verify,
                "commands": step.commands,
                "citations": [
                    {"rfc": c.rfc, "section": c.section, "title": c.title, "url": c.url}
                    for c in step.citations
                ],
            }
            steps_dict.append(step_dict)

        # Compute deterministic step hash
        step_hash = compute_steps_hash(result.steps)

        return {
            "steps": steps_dict,
            "citations": all_citations,
            "confidence": 0.9,  # High confidence for deterministic playbooks
            "source_slug": target_slug,
            "vendor": play_context.vendor,
            "playbook_id": result.playbook_id,
            "step_hash": step_hash,
        }

    except Exception as e:
        return {
            "error": f"Failed to execute playbook {target_slug}: {str(e)}",
            "citations": [],
            "confidence": 0.0,
            "source_slug": target_slug,
        }


def _create_play_context(query: str, context: Dict[str, Any] = None) -> PlayContext:
    """
    Create PlayContext from query and optional context.

    Args:
        query: User query string
        context: Optional context dictionary

    Returns:
        PlayContext object
    """
    # Default values
    vendor = "iosxe"
    iface = "GigabitEthernet0/0"
    area = "0.0.0.0"
    auth = None
    mtu = 1500
    peer = "192.0.2.1"  # Default BGP peer

    # Override with provided context
    if context:
        vendor = context.get("vendor", vendor)
        iface = context.get("iface", iface)
        area = context.get("area", area)
        auth = context.get("auth", auth)
        mtu = context.get("mtu", mtu)
        peer = context.get("peer", peer)

    # Extract from query if not provided
    query_lower = query.lower()

    # Extract vendor
    if "junos" in query_lower or "juniper" in query_lower:
        vendor = "junos"
    elif "iosxe" in query_lower or "ios" in query_lower or "cisco" in query_lower:
        vendor = "iosxe"

    # Extract interface
    interface_patterns = [
        ("g0/0", "GigabitEthernet0/0"),
        ("gigabitethernet0/0", "GigabitEthernet0/0"),
        ("ge-0/0/0", "ge-0/0/0"),
        ("ethernet0/0", "Ethernet0/0"),
    ]

    for pattern, replacement in interface_patterns:
        if pattern in query_lower:
            iface = replacement
            break

    # Extract area
    if "area" in query_lower:
        # Simple extraction - could be enhanced
        area = "0.0.0.0"

    # Extract authentication
    if "auth" in query_lower or "md5" in query_lower:
        auth = "md5"

    # Extract MTU
    if "mtu" in query_lower:
        mtu = 1500  # Default MTU

    # Extract BGP peer IPv4 address from query
    import re

    ipv4_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    ipv4_matches = re.findall(ipv4_pattern, query)
    if ipv4_matches:
        peer = ipv4_matches[0]  # Use first IPv4 address found

    # Extract TCP destination and port from query
    dst = None
    dport = None
    if ":" in query:
        # Look for IP:port pattern
        port_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d+\b"
        port_matches = re.findall(port_pattern, query)
        if port_matches:
            dst_port = port_matches[0].split(":")
            dst = dst_port[0]
            dport = dst_port[1]
        else:
            # Look for separate IP and port
            if ipv4_matches:
                dst = ipv4_matches[0]
            port_pattern = r"\b\d{1,5}\b"
            port_matches = re.findall(port_pattern, query)
            if port_matches:
                dport = port_matches[0]

    return PlayContext(
        vendor=vendor,
        iface=iface,
        area=area,
        auth=auth,
        mtu=mtu,
        peer=peer,
        dst=dst,
        dport=dport,
    )
