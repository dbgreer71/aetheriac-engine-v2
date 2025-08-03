"""
Playbook assembler for troubleshooting responses.

This module assembles troubleshooting responses by invoking the existing
playbook engine and returning structured steps with citations.
"""

import hashlib
import json
from typing import Dict, Any, List
from ..playbooks.engine import run_playbook
from ..playbooks.models import PlayContext
from ..retriever.index_store import IndexStore


def compute_steps_hash(steps: List[Dict[str, Any]]) -> str:
    """
    Compute deterministic hash for playbook steps.

    Args:
        steps: List of step dictionaries

    Returns:
        SHA256 hash of normalized steps
    """
    # Normalize steps for deterministic hashing
    normalized_steps = []
    for step in steps:
        normalized_step = {
            "rule_id": step.get("rule_id", ""),
            "check": step.get("check", ""),
            "result": step.get("result", ""),
            "fix": step.get("fix", ""),
            "verify": step.get("verify", ""),
            "commands": sorted(
                step.get("commands", [])
            ),  # Sort commands for determinism
            "citations": sorted(
                [
                    {
                        "rfc": c.get("rfc", ""),
                        "section": c.get("section", ""),
                        "title": c.get("title", ""),
                        "url": c.get("url", ""),
                    }
                    for c in step.get("citations", [])
                ],
                key=lambda x: (x["rfc"], x["section"]),  # Sort by RFC, then section
            ),
        }
        normalized_steps.append(normalized_step)

    # Sort steps by rule_id for deterministic ordering
    normalized_steps.sort(key=lambda x: x["rule_id"])

    # Convert to JSON with deterministic formatting
    steps_json = json.dumps(
        normalized_steps,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    )

    # Compute SHA256 hash
    return hashlib.sha256(steps_json.encode("utf-8")).hexdigest()


def assemble_playbook(
    target_slug: str,
    query: str,
    store: IndexStore,
    context: Dict[str, Any] = None,
    decision_evidence: Dict[str, Any] = None,
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
        step_hash = compute_steps_hash(steps_dict)

        # Guard against insufficient steps
        if len(steps_dict) < 3:
            return {
                "intent": "TROUBLESHOOT",
                "error": "insufficient_steps",
                "steps_count": len(steps_dict),
                "target": target_slug,
                "vendor": play_context.vendor,
                "evidence": decision_evidence
                or {
                    "ranked_reasons": [],
                    "matches": {},
                    "rules": [],
                    "confidence": 0.0,
                },
            }

        # Include assumptions if present
        response = {
            "steps": steps_dict,
            "citations": all_citations,
            "confidence": 0.9,  # High confidence for deterministic playbooks
            "source_slug": target_slug,
            "vendor": play_context.vendor,
            "playbook_id": result.playbook_id,
            "step_hash": step_hash,
            "deterministic": True,
            "provenance": {
                "playbook": target_slug,
                "rules": [step.get("rule_id", "") for step in steps_dict],
            },
        }

        # Add assumptions if present in the result
        if hasattr(result, "assumptions") and result.assumptions:
            response["assumptions"] = result.assumptions

        return response

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

    # Override with provided context
    if context:
        vendor = context.get("vendor", vendor)
        iface = context.get("iface", iface)
        area = context.get("area", area)
        auth = context.get("auth", auth)
        mtu = context.get("mtu", mtu)

    # Extract from query if not provided
    query_lower = query.lower()

    # Extract vendor
    if "junos" in query_lower or "juniper" in query_lower:
        vendor = "junos"
    elif "iosxe" in query_lower or "ios" in query_lower or "cisco" in query_lower:
        vendor = "iosxe"

    # Extract interface or bundle
    interface_patterns = [
        ("g0/0", "GigabitEthernet0/0"),
        ("gigabitethernet0/0", "GigabitEthernet0/0"),
        ("ge-0/0/0", "ge-0/0/0"),
        ("ethernet0/0", "Ethernet0/0"),
        # Bundle/Port-channel patterns
        ("port-channel1", "Port-channel1"),
        ("portchannel1", "Port-channel1"),
        ("po1", "Port-channel1"),
        ("bundle-ether1", "Bundle-Ether1"),
        ("ae1", "ae1"),
        # VLAN patterns
        ("vlan10", "Vlan10"),
        ("vlan.10", "vlan.10"),
        ("irb.10", "irb.10"),
        ("svi 10", "Vlan10"),
    ]

    # Extract IP addresses
    import re

    ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
    ips = re.findall(ip_pattern, query_lower)
    if ips:
        iface = ips[0]  # Use first IP found as interface

    # Extract MAC addresses (for ARP)
    mac_pattern = r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}"
    macs = re.findall(mac_pattern, query_lower)
    macs[0] if macs else None

    # Extract VLAN numbers
    vlan_pattern = r"\bvlan\s?(\d{1,4})\b"
    vlan_match = re.search(vlan_pattern, query_lower)
    if vlan_match:
        vlan = vlan_match.group(1)
        if not ips:  # If no IP found, use VLAN as interface
            iface = f"Vlan{vlan}"

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

    return PlayContext(vendor=vendor, iface=iface, area=area, auth=auth, mtu=mtu)
