"""
LACP/Port-channel down troubleshooting playbook.

This module provides deterministic troubleshooting for LACP/Port-channel issues
following IEEE 802.1AX-2020 Link Aggregation standard.
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


def create_lacp_port_channel_playbook() -> Playbook:
    """Create the LACP/Port-channel down troubleshooting playbook."""

    # IEEE 802.1AX-2020 citations for LACP troubleshooting
    ieee_8021ax_lacp = RFCSectionRef(
        rfc=8021,
        section="1",
        title="IEEE 802.1AX-2020 - Link Aggregation",
        url="https://standards.ieee.org/standard/802_1AX-2020.html",
    )

    ieee_8021q_vlan = RFCSectionRef(
        rfc=8021,
        section="1",
        title="IEEE 802.1Q - Virtual Bridged Local Area Networks",
        url="https://standards.ieee.org/standard/802_1Q-2018.html",
    )

    ieee_8021d_stp = RFCSectionRef(
        rfc=8021,
        section="1",
        title="IEEE 802.1D - Media Access Control (MAC) Bridges",
        url="https://standards.ieee.org/standard/802_1D-2004.html",
    )

    rfc_2460_mtu = RFCSectionRef(
        rfc=2460,
        section="1",
        title="Internet Protocol, Version 6 (IPv6) Specification",
        url="https://tools.ietf.org/html/rfc2460",
    )

    rules = [
        Rule(
            id="check_bundle_members_status",
            if_="Bundle/Port-channel is down or suspended",
            then_check="Check bundle member interface status and suspension state",
            then_fix=None,
            verify="Bundle members should be up and not suspended",
            citations=[ieee_8021ax_lacp],
        ),
        Rule(
            id="check_lacp_actor_partner_state",
            if_="LACP state is not collecting or defaulted",
            then_check="Verify LACP actor and partner state",
            then_fix=None,
            verify="LACP state should be collecting or defaulted",
            citations=[ieee_8021ax_lacp],
        ),
        Rule(
            id="check_lacp_key_system_priority",
            if_="LACP key or system priority mismatch",
            then_check="Verify LACP key and system priority configuration",
            then_fix="Configure matching LACP key and system priority",
            verify="LACP key and system priority should match",
            citations=[ieee_8021ax_lacp],
        ),
        Rule(
            id="check_admin_mode_mismatch",
            if_="Admin mode mismatch (on/active/passive; static vs LACP)",
            then_check="Verify admin mode configuration consistency",
            then_fix="Align admin mode on both ends (active/active or static/static)",
            verify="Admin mode should be consistent on both sides",
            citations=[ieee_8021ax_lacp],
        ),
        Rule(
            id="check_mtu_speed_duplex_mismatch",
            if_="MTU/speed/duplex mismatch between interfaces",
            then_check="Verify MTU, speed, and duplex configuration",
            then_fix="Configure matching MTU, speed, and duplex settings",
            verify="MTU, speed, and duplex should match on both sides",
            citations=[rfc_2460_mtu, ieee_8021ax_lacp],
        ),
        Rule(
            id="check_vlan_trunk_consistency",
            if_="VLAN/Trunk allowed list/Native VLAN mismatch",
            then_check="Verify VLAN trunk configuration consistency",
            then_fix="Configure matching VLAN trunk settings",
            verify="VLAN trunk configuration should be consistent",
            citations=[ieee_8021q_vlan],
        ),
        Rule(
            id="check_stp_blocking_state",
            if_="STP blocking or inconsistent state",
            then_check="Verify spanning tree blocking state",
            then_fix=None,
            verify="Interface should not be in blocking state",
            citations=[ieee_8021d_stp],
        ),
        Rule(
            id="check_errdisable_sanity",
            if_="Interface in errdisable state",
            then_check="Check interface errdisable status and recovery",
            then_fix="Recover interface from errdisable state",
            verify="Interface should not be in errdisable state",
            citations=[ieee_8021ax_lacp],
        ),
    ]

    return Playbook(
        id="lacp-port-channel-down",
        applies_to=["lacp", "etherchannel", "port-channel", "link-aggregation"],
        rules=rules,
    )


def run_lacp_playbook(ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run the LACP/Port-channel down playbook with deterministic results."""

    playbook = create_lacp_port_channel_playbook()
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

    return PlayResult(playbook_id=playbook.id, steps=steps)


def get_lacp_assumptions() -> List[Dict[str, Any]]:
    """Get assumptions for LACP troubleshooting."""
    return [
        {
            "assumption": "Bundle logical name maps to member interfaces",
            "basis": "operator_input",
            "impact": "Determines which interfaces to check for bundle membership",
        },
        {
            "assumption": "LACP is enabled on both ends of the link",
            "basis": "ieee_8021ax_standard",
            "impact": "Affects LACP state checking and configuration verification",
        },
        {
            "assumption": "Vendor supports LACP protocol",
            "basis": "vendor_capability",
            "impact": "Determines available LACP commands and features",
        },
    ]


def get_lacp_operator_actions() -> List[Dict[str, Any]]:
    """Get operator actions for LACP troubleshooting."""
    return [
        {
            "action": "If admin mode mismatched, align both ends (active/active or static/static)",
            "condition": "admin_mode_mismatch_detected",
            "priority": "high",
        },
        {
            "action": "If LACP key/system priority mismatch, configure matching values",
            "condition": "lacp_key_priority_mismatch_detected",
            "priority": "high",
        },
        {
            "action": "If MTU/speed/duplex mismatch, configure matching settings",
            "condition": "mtu_speed_duplex_mismatch_detected",
            "priority": "medium",
        },
        {
            "action": "If VLAN trunk mismatch, align allowed VLANs and native VLAN",
            "condition": "vlan_trunk_mismatch_detected",
            "priority": "medium",
        },
        {
            "action": "If interface in errdisable, check recovery timers and clear errdisable",
            "condition": "errdisable_state_detected",
            "priority": "high",
        },
    ]
