"""
Playbook engine for deterministic troubleshooting workflows.

This module provides the core engine for executing playbooks with
deterministic rule evaluation and vendor-specific command rendering.
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
from ..vendor_ir.models import VendorCommandIR
from ..retriever.index_store import IndexStore


def create_ospf_neighbor_playbook() -> Playbook:
    """Create the OSPF neighbor-down troubleshooting playbook."""

    # RFC 2328 citations for OSPF neighbor states and troubleshooting
    rfc_2328_neighbor_states = RFCSectionRef(
        rfc=2328,
        section="10.1",
        title="Neighbor State Machine",
        url="https://tools.ietf.org/html/rfc2328#section-10.1",
    )

    rfc_2328_mtu = RFCSectionRef(
        rfc=2328,
        section="8.1",
        title="Interface Data Structure",
        url="https://tools.ietf.org/html/rfc2328#section-8.1",
    )

    rfc_2328_auth = RFCSectionRef(
        rfc=2328,
        section="9",
        title="The Interface Data Structure",
        url="https://tools.ietf.org/html/rfc2328#section-9",
    )

    rfc_2328_exstart = RFCSectionRef(
        rfc=2328,
        section="10.3",
        title="The Neighbor State Machine",
        url="https://tools.ietf.org/html/rfc2328#section-10.3",
    )

    rules = [
        Rule(
            id="check_neighbor_state",
            if_="OSPF neighbor is down or not visible",
            then_check="Check OSPF neighbor state and adjacency status",
            then_fix=None,
            verify="Verify neighbor appears in show output",
            citations=[rfc_2328_neighbor_states],
        ),
        Rule(
            id="check_interface_status",
            if_="Neighbor not found in OSPF neighbor table",
            then_check="Verify interface is up and configured for OSPF",
            then_fix=None,
            verify="Interface should be up/up and OSPF enabled",
            citations=[rfc_2328_neighbor_states],
        ),
        Rule(
            id="check_ospf_interface_config",
            if_="Interface is up but OSPF neighbor not established",
            then_check="Verify OSPF interface configuration and area assignment",
            then_fix=None,
            verify="OSPF interface should be in correct area",
            citations=[rfc_2328_neighbor_states],
        ),
        Rule(
            id="check_mtu_mismatch",
            if_="Neighbor stuck in EXSTART state",
            then_check="Check for MTU mismatch between interfaces",
            then_fix="Configure matching MTU on both interfaces",
            verify="MTU values should match on both sides",
            citations=[rfc_2328_mtu, rfc_2328_exstart],
        ),
        Rule(
            id="check_authentication",
            if_="Authentication mismatch suspected",
            then_check="Verify OSPF authentication configuration",
            then_fix="Configure matching authentication on both sides",
            verify="Authentication should be consistent",
            citations=[rfc_2328_auth],
        ),
        Rule(
            id="check_ospf_process",
            if_="OSPF process not running",
            then_check="Verify OSPF process is active and configured",
            then_fix="Enable OSPF process if not running",
            verify="OSPF process should be active",
            citations=[rfc_2328_neighbor_states],
        ),
        Rule(
            id="check_network_type",
            if_="Network type mismatch",
            then_check="Verify OSPF network type configuration",
            then_fix="Configure matching network type",
            verify="Network types should match on both sides",
            citations=[rfc_2328_neighbor_states],
        ),
        Rule(
            id="check_hello_dead_intervals",
            if_="Hello/Dead interval mismatch",
            then_check="Verify OSPF hello and dead intervals",
            then_fix="Configure matching intervals",
            verify="Hello and dead intervals should match",
            citations=[rfc_2328_neighbor_states],
        ),
    ]

    return Playbook(
        id="ospf-neighbor-down", applies_to=["OSPF", "OSPFv2", "routing"], rules=rules
    )


def create_bgp_neighbor_playbook() -> Playbook:
    """Create the BGP neighbor-down troubleshooting playbook."""

    # RFC 4271 citations for BGP neighbor states and troubleshooting
    rfc_4271_neighbor_states = RFCSectionRef(
        rfc=4271,
        section="8.2.2",
        title="BGP Finite State Machine",
        url="https://tools.ietf.org/html/rfc4271#section-8.2.2",
    )

    rfc_4271_opensent = RFCSectionRef(
        rfc=4271,
        section="8.2.2",
        title="OpenSent State",
        url="https://tools.ietf.org/html/rfc4271#section-8.2.2",
    )

    rules = [
        Rule(
            id="check_bgp_neighbor_state",
            if_="BGP neighbor is down or not established",
            then_check="Check BGP neighbor state and session status",
            then_fix=None,
            verify="Verify neighbor appears in BGP table",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_interface_status",
            if_="BGP neighbor not found in routing table",
            then_check="Verify interface is up and configured for BGP",
            then_fix=None,
            verify="Interface should be up/up and BGP enabled",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_bgp_configuration",
            if_="Interface is up but BGP session not established",
            then_check="Verify BGP neighbor configuration and AS number",
            then_fix=None,
            verify="BGP neighbor should be configured with correct AS",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_opensent_state",
            if_="BGP neighbor stuck in OpenSent state",
            then_check="Check for BGP Open message issues",
            then_fix="Verify BGP parameters match on both sides",
            verify="BGP Open messages should be accepted",
            citations=[rfc_4271_opensent],
        ),
        Rule(
            id="check_authentication",
            if_="BGP authentication mismatch suspected",
            then_check="Verify BGP authentication configuration",
            then_fix="Configure matching authentication on both sides",
            verify="Authentication should be consistent",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_bgp_process",
            if_="BGP process not running",
            then_check="Verify BGP process is active and configured",
            then_fix="Enable BGP process if not running",
            verify="BGP process should be active",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_route_policies",
            if_="BGP routes not being advertised",
            then_check="Verify BGP route policies and filters",
            then_fix="Configure appropriate route policies",
            verify="Routes should be advertised correctly",
            citations=[rfc_4271_neighbor_states],
        ),
        Rule(
            id="check_connectivity",
            if_="BGP session cannot be established",
            then_check="Verify network connectivity to BGP peer",
            then_fix="Resolve network connectivity issues",
            verify="Network should be reachable",
            citations=[rfc_4271_neighbor_states],
        ),
    ]

    return Playbook(id="bgp-neighbor-down", applies_to=["BGP", "routing"], rules=rules)


def create_tcp_handshake_playbook() -> Playbook:
    """Create the TCP handshake troubleshooting playbook."""

    # RFC 9293 citations for TCP handshake and troubleshooting
    rfc_9293_handshake = RFCSectionRef(
        rfc=9293,
        section="3.4",
        title="Establishing a connection",
        url="https://tools.ietf.org/html/rfc9293#section-3.4",
    )

    rfc_9293_syn = RFCSectionRef(
        rfc=9293,
        section="3.4.1",
        title="Three-Way Handshake",
        url="https://tools.ietf.org/html/rfc9293#section-3.4.1",
    )

    rules = [
        Rule(
            id="check_connectivity",
            if_="TCP connection cannot be established",
            then_check="Verify basic network connectivity",
            then_fix=None,
            verify="Network should be reachable",
            citations=[rfc_9293_handshake],
        ),
        Rule(
            id="check_syn_timeout",
            if_="SYN timeout or no response",
            then_check="Check if destination is listening on port",
            then_fix="Verify service is running on destination port",
            verify="SYN-ACK should be received",
            citations=[rfc_9293_syn],
        ),
        Rule(
            id="check_port_filtering",
            if_="Connection refused or port filtered",
            then_check="Verify firewall and port filtering rules",
            then_fix="Configure firewall to allow traffic",
            verify="Port should be accessible",
            citations=[rfc_9293_handshake],
        ),
        Rule(
            id="check_mss_issues",
            if_="MSS issues or PMTUD problems",
            then_check="Check for MTU and MSS configuration",
            then_fix="Configure appropriate MSS values",
            verify="MSS should be negotiated correctly",
            citations=[rfc_9293_handshake],
        ),
        Rule(
            id="check_rst_response",
            if_="RST received during handshake",
            then_check="Check if service is rejecting connections",
            then_fix="Verify service configuration",
            verify="Service should accept connections",
            citations=[rfc_9293_syn],
        ),
        Rule(
            id="check_blackhole",
            if_="Traffic appears to be blackholed",
            then_check="Check for routing issues or packet drops",
            then_fix="Resolve routing or forwarding issues",
            verify="Packets should be forwarded correctly",
            citations=[rfc_9293_handshake],
        ),
        Rule(
            id="check_interface_status",
            if_="Interface issues affecting connectivity",
            then_check="Verify interface status and configuration",
            then_fix="Resolve interface issues",
            verify="Interface should be operational",
            citations=[rfc_9293_handshake],
        ),
        Rule(
            id="check_application",
            if_="Application-level connection issues",
            then_check="Verify application is listening and configured",
            then_fix="Start or configure application correctly",
            verify="Application should accept connections",
            citations=[rfc_9293_handshake],
        ),
    ]

    return Playbook(id="tcp-handshake", applies_to=["TCP", "connectivity"], rules=rules)


def run_playbook(slug: str, ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run a playbook with the given context and return deterministic results."""

    if slug == "ospf-neighbor-down":
        playbook = create_ospf_neighbor_playbook()
    elif slug == "bgp-neighbor-down":
        playbook = create_bgp_neighbor_playbook()
    elif slug == "tcp-handshake":
        playbook = create_tcp_handshake_playbook()
    elif slug == "lacp-port-channel-down":
        from .lacp_port_channel_down import create_lacp_port_channel_playbook

        playbook = create_lacp_port_channel_playbook()
    elif slug == "arp-anomalies":
        from .arp_anomalies import run_arp_playbook

        return run_arp_playbook(ctx, store)
    else:
        raise ValueError(f"Unknown playbook: {slug}")
    steps = []

    # Execute rules in deterministic order
    for rule in playbook.rules:
        # Generate commands for this rule
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


def _generate_commands_for_rule(rule: Rule, ctx: PlayContext) -> List[str]:
    """Generate vendor-specific commands for a rule."""
    commands = []

    # Map rule IDs to command intents
    rule_commands = {
        # OSPF commands
        "check_neighbor_state": ["show_neighbors"],
        "check_interface_status": ["show_iface"],
        "check_ospf_interface_config": ["show_ospf_iface"],
        "check_mtu_mismatch": ["show_mtu", "show_ospf_iface"],
        "check_authentication": ["show_auth", "show_ospf_iface"],
        "check_ospf_process": ["show_ospf_process"],
        "check_network_type": ["show_ospf_iface"],
        "check_hello_dead_intervals": ["show_ospf_iface"],
        # BGP commands
        "check_bgp_neighbor_state": ["show_bgp_neighbors"],
        "check_bgp_configuration": ["show_bgp_config"],
        "check_opensent_state": ["show_bgp_neighbors"],
        "check_bgp_process": ["show_bgp_process"],
        "check_route_policies": ["show_route_policies"],
        "check_connectivity": ["ping", "traceroute"],
        # TCP commands
        "check_syn_timeout": ["telnet", "nc"],
        "check_port_filtering": ["telnet", "nc"],
        "check_mss_issues": ["show_mtu"],
        "check_rst_response": ["telnet", "nc"],
        "check_blackhole": ["traceroute", "ping"],
        "check_application": ["show_processes"],
        # LACP commands
        "check_bundle_members_status": [
            "show_etherchannel_summary",
            "show_port_channel",
        ],
        "check_lacp_actor_partner_state": [
            "show_lacp_neighbor",
            "show_lacp_interfaces",
        ],
        "check_lacp_key_system_priority": [
            "show_lacp_neighbor",
            "show_lacp_interfaces",
        ],
        "check_admin_mode_mismatch": [
            "show_lacp_interfaces",
            "show_etherchannel_summary",
        ],
        "check_mtu_speed_duplex_mismatch": ["show_mtu", "show_iface"],
        "check_vlan_trunk_consistency": [
            "show_interface_switchport",
            "show_interfaces_trunk",
            "show_vlan",
        ],
        "check_stp_blocking_state": [
            "show_spanning_tree_interface",
            "show_spanning_tree",
        ],
        "check_errdisable_sanity": [
            "show_errdisable_recovery",
            "show_errdisable_detect",
        ],
        # ARP commands
        "check_svi_status": ["show_svi"],
        "check_arp_entry_lookup": ["show_arp_table"],
        "check_arp_table_health": ["show_dai_status"],
        "check_proxy_arp_config": ["show_proxy_arp"],
        "check_mac_table_lookup": ["show_mac_table"],
        "check_arp_gratuitous_signals": ["show_dai_status"],
        "check_arp_aging_timers": ["show_arp_timers"],
        "check_port_security_counters": ["show_port_security"],
    }

    if rule.id in rule_commands:
        for intent in rule_commands[rule.id]:
            # Handle different parameter contexts
            params = {"iface": ctx.iface}
            if "bundle" in intent or "port_channel" in intent:
                params["bundle"] = ctx.iface
            if "target" in intent or "lacp" in intent:
                params["target"] = ctx.iface
            if "arp" in intent or "mac" in intent or "svi" in intent:
                params["ip"] = ctx.iface
                params["vlan"] = ctx.iface
                params["mac"] = ctx.iface

            cmd_ir = VendorCommandIR(intent=intent, params=params)
            commands.extend(cmd_ir.render(ctx.vendor))

    return commands


def _generate_result_text(rule: Rule, ctx: PlayContext) -> str:
    """Generate result text for a rule based on context."""

    result_templates = {
        # OSPF templates
        "check_neighbor_state": "Check OSPF neighbor table for adjacency status",
        "check_interface_status": f"Verify interface {ctx.iface} is operational",
        "check_ospf_interface_config": f"Check OSPF configuration on {ctx.iface}",
        "check_mtu_mismatch": "Verify MTU values match on both interfaces",
        "check_authentication": "Check authentication configuration consistency",
        "check_ospf_process": "Verify OSPF process is active",
        "check_network_type": "Ensure network types match on both sides",
        "check_hello_dead_intervals": "Verify hello and dead intervals match",
        # BGP templates
        "check_bgp_neighbor_state": "Check BGP neighbor table for session status",
        "check_bgp_configuration": "Verify BGP neighbor configuration",
        "check_opensent_state": "Check BGP Open message exchange",
        "check_bgp_process": "Verify BGP process is active",
        "check_route_policies": "Check BGP route policies and filters",
        "check_connectivity": "Verify network connectivity to BGP peer",
        # TCP templates
        "check_syn_timeout": "Check if destination is listening on port",
        "check_port_filtering": "Verify firewall and port filtering rules",
        "check_mss_issues": "Check for MTU and MSS configuration",
        "check_rst_response": "Check if service is rejecting connections",
        "check_blackhole": "Check for routing issues or packet drops",
        "check_application": "Verify application is listening and configured",
        # LACP templates
        "check_bundle_members_status": f"Check bundle member interface status for {ctx.iface}",
        "check_lacp_actor_partner_state": f"Verify LACP actor and partner state for {ctx.iface}",
        "check_lacp_key_system_priority": f"Verify LACP key and system priority for {ctx.iface}",
        "check_admin_mode_mismatch": f"Check admin mode configuration for {ctx.iface}",
        "check_mtu_speed_duplex_mismatch": f"Verify MTU, speed, and duplex configuration for {ctx.iface}",
        "check_vlan_trunk_consistency": f"Verify VLAN trunk configuration for {ctx.iface}",
        "check_stp_blocking_state": f"Check spanning tree blocking state for {ctx.iface}",
        "check_errdisable_sanity": f"Check errdisable status for interface {ctx.iface}",
        # ARP templates
        "check_svi_status": f"Check SVI status for VLAN {ctx.iface}",
        "check_arp_entry_lookup": f"Check ARP entry for IP {ctx.iface}",
        "check_arp_table_health": "Check ARP table health and DAI counters",
        "check_proxy_arp_config": f"Check proxy ARP configuration for {ctx.iface}",
        "check_mac_table_lookup": f"Check MAC table entry for {ctx.iface}",
        "check_arp_gratuitous_signals": "Check gratuitous ARP signals and probes",
        "check_arp_aging_timers": "Check ARP aging timers configuration",
        "check_port_security_counters": f"Check port security counters for {ctx.iface}",
    }

    return result_templates.get(rule.id, f"Execute {rule.then_check}")


def get_playbook_explanation(slug: str, vendor: str) -> Dict[str, Any]:
    """Get explanation of a playbook's rules and commands."""

    if slug == "ospf-neighbor-down":
        playbook = create_ospf_neighbor_playbook()
    elif slug == "bgp-neighbor-down":
        playbook = create_bgp_neighbor_playbook()
    elif slug == "tcp-handshake":
        playbook = create_tcp_handshake_playbook()
    else:
        raise ValueError(f"Unknown playbook: {slug}")

    explanation = {"playbook_id": playbook.id, "vendor": vendor, "rules": []}

    for rule in playbook.rules:
        commands = _generate_commands_for_rule(
            rule,
            PlayContext(vendor=vendor, iface="GigabitEthernet0/0"),  # Example interface
        )

        explanation["rules"].append(
            {
                "rule_id": rule.id,
                "if_condition": rule.if_,
                "check": rule.then_check,
                "commands": commands,
                "citations": [
                    f"RFC {ref.rfc} Section {ref.section}" for ref in rule.citations
                ],
            }
        )

    return explanation
