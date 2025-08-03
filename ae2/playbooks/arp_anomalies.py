"""
ARP anomalies troubleshooting playbook.

This module provides deterministic troubleshooting for ARP anomalies
following RFC 826 (ARP) and RFC 5227 (ARP Probe/Gratuitous) standards.
"""

from typing import List, Dict, Any
from .models import (
    Playbook,
    PlayContext,
    PlayResult,
    PlayResultStep,
    Rule,
    RFCSectionRef,
)
from ..retriever.index_store import IndexStore


def create_arp_anomalies_playbook() -> Playbook:
    """Create the ARP anomalies troubleshooting playbook."""

    # RFC citations for ARP troubleshooting
    rfc_826_arp = RFCSectionRef(
        rfc=826,
        section="1",
        title="An Ethernet Address Resolution Protocol",
        url="https://tools.ietf.org/html/rfc826",
    )

    rfc_5227_arp_probe = RFCSectionRef(
        rfc=5227,
        section="1",
        title="IPv4 Address Conflict Detection",
        url="https://tools.ietf.org/html/rfc5227",
    )

    rules = [
        Rule(
            id="check_svi_status",
            if_="SVI/VLAN interface is down",
            then_check="Check SVI status for VLAN",
            then_fix="Enable SVI if down",
            verify="SVI should be up/up",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_arp_entry_lookup",
            if_="ARP entry is incomplete or duplicate",
            then_check="Verify ARP entry lookup for target IP",
            then_fix=None,
            verify="ARP entry should be complete and not duplicate",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_arp_table_health",
            if_="DAI/inspection shows drops or anomalies",
            then_check="Check ARP table health and DAI counters",
            then_fix=None,
            verify="No excessive ARP drops or anomalies",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_proxy_arp_config",
            if_="Proxy-ARP configuration mismatch",
            then_check="Verify proxy ARP configuration",
            then_fix="Configure proxy ARP if required",
            verify="Proxy ARP should be consistently configured",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_mac_table_lookup",
            if_="MAC/ARP correlation mismatch",
            then_check="Verify MAC table lookup for IP→MAC path",
            then_fix=None,
            verify="MAC entry should exist and be consistent with ARP",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_arp_gratuitous_signals",
            if_="Gratuitous/Probe signals not working",
            then_check="Check gratuitous ARP signals",
            then_fix="Configure gratuitous ARP if required",
            verify="Gratuitous ARP should be properly configured",
            citations=[rfc_5227_arp_probe],
        ),
        Rule(
            id="check_arp_aging_timers",
            if_="ARP aging timers misaligned",
            then_check="Check ARP aging timers configuration",
            then_fix="Configure consistent ARP aging timers",
            verify="ARP aging timers should be aligned",
            citations=[rfc_826_arp],
        ),
        Rule(
            id="check_port_security_counters",
            if_="Port security violations detected",
            then_check="Check port security counters",
            then_fix="Clear port security violations if needed",
            verify="No excessive port security violations",
            citations=[rfc_826_arp],
        ),
    ]

    return Playbook(
        id="arp-anomalies",
        applies_to=[
            "arp",
            "proxy-arp",
            "gratuitous",
            "incomplete",
            "duplicate",
            "dai",
            "inspection",
        ],
        rules=rules,
    )


def run_arp_playbook(ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run the ARP anomalies playbook with deterministic results."""

    playbook = create_arp_anomalies_playbook()
    steps = []

    # Execute rules in deterministic order
    for rule in playbook.rules:
        # Generate commands for this rule using the engine's command generation
        from .engine import _generate_commands_for_rule, _generate_result_text

        commands = _generate_commands_for_rule(rule, ctx)

        # Create result step
        step = PlayResultStep(
            rule_id=rule.id,
            check=rule.then_check,
            result=_generate_result_text(rule, ctx),
            fix=rule.then_fix,
            verify=rule.verify,
            commands=commands,
            citations=rule.citations,
        )
        steps.append(step)

    # Add assumption ledger to the result
    result = PlayResult(playbook_id=playbook.id, steps=steps)
    result.assumptions = {
        "facts": [
            "Vendor commands are guidance; no device-state claims.",
            "DAI/Inspection may drop ARP frames if bindings absent.",
        ],
        "assumptions": [
            "User can run show commands on target device.",
            "If VLAN unspecified, SVI or trunk context applies.",
        ],
        "operator_actions": [
            "Collect outputs from steps 1–3; note MAC/IP/VLAN alignment.",
            "If DAI drops suspected, verify DHCP Snooping bindings.",
        ],
    }
    return result


def get_arp_assumptions() -> List[Dict[str, Any]]:
    """Get assumptions for ARP troubleshooting."""
    return [
        {
            "assumption": "Provided IP belongs to VLAN on this device",
            "basis": "operator_input",
            "impact": "Determines which VLAN to check for ARP entries",
        },
        {
            "assumption": "ARP is enabled and functioning on the device",
            "basis": "rfc_826_standard",
            "impact": "Affects ARP table checking and configuration verification",
        },
        {
            "assumption": "Vendor supports ARP protocol and related features",
            "basis": "vendor_capability",
            "impact": "Determines available ARP commands and features",
        },
        {
            "assumption": "SVI interface exists for the specified VLAN",
            "basis": "network_topology",
            "impact": "Affects SVI status checking and ARP resolution",
        },
    ]


def get_arp_operator_actions() -> List[Dict[str, Any]]:
    """Get operator actions for ARP troubleshooting."""
    return [
        {
            "action": "If ARP entry stale, clear specific entry after maintenance window",
            "condition": "stale_arp_entry_detected",
            "priority": "medium",
        },
        {
            "action": "If DAI drops excessive, check for ARP spoofing or misconfiguration",
            "condition": "excessive_dai_drops_detected",
            "priority": "high",
        },
        {
            "action": "If proxy ARP mismatch, align configuration on both ends",
            "condition": "proxy_arp_mismatch_detected",
            "priority": "medium",
        },
        {
            "action": "If MAC/ARP correlation fails, check for MAC spoofing or duplicate MACs",
            "condition": "mac_arp_correlation_failed",
            "priority": "high",
        },
        {
            "action": "If gratuitous ARP not working, verify network allows ARP probes",
            "condition": "gratuitous_arp_failed",
            "priority": "medium",
        },
        {
            "action": "If ARP aging timers misaligned, configure consistent timers across devices",
            "condition": "arp_timers_misaligned",
            "priority": "low",
        },
        {
            "action": "If port security violations, check for unauthorized devices or MAC changes",
            "condition": "port_security_violations",
            "priority": "high",
        },
    ]
