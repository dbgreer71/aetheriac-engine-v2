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


def run_playbook(slug: str, ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run a playbook with the given context and return deterministic results."""

    if slug == "ospf-neighbor-down":
        playbook = create_ospf_neighbor_playbook()
    elif slug == "bgp-neighbor-down":
        from .bgp_neighbor_down import create_bgp_neighbor_playbook
        playbook = create_bgp_neighbor_playbook()
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
        "check_neighbor_state": ["show_neighbors"],
        "check_interface_status": ["show_iface"],
        "check_ospf_interface_config": ["show_ospf_iface"],
        "check_mtu_mismatch": ["show_mtu", "show_ospf_iface"],
        "check_authentication": ["show_auth", "show_ospf_iface"],
        "check_ospf_process": ["show_ospf_process"],
        "check_network_type": ["show_ospf_iface"],
        "check_hello_dead_intervals": ["show_ospf_iface"],
    }

    if rule.id in rule_commands:
        for intent in rule_commands[rule.id]:
            cmd_ir = VendorCommandIR(intent=intent, params={"iface": ctx.iface})
            commands.extend(cmd_ir.render(ctx.vendor))

    return commands


def _generate_result_text(rule: Rule, ctx: PlayContext) -> str:
    """Generate result text for a rule based on context."""

    result_templates = {
        "check_neighbor_state": "Check OSPF neighbor table for adjacency status",
        "check_interface_status": f"Verify interface {ctx.iface} is operational",
        "check_ospf_interface_config": f"Check OSPF configuration on {ctx.iface}",
        "check_mtu_mismatch": "Verify MTU values match on both interfaces",
        "check_authentication": "Check authentication configuration consistency",
        "check_ospf_process": "Verify OSPF process is active",
        "check_network_type": "Ensure network types match on both sides",
        "check_hello_dead_intervals": "Verify hello and dead intervals match",
    }

    return result_templates.get(rule.id, f"Execute {rule.then_check}")


def get_playbook_explanation(slug: str, vendor: str) -> Dict[str, Any]:
    """Get explanation of a playbook's rules and commands."""

    if slug == "ospf-neighbor-down":
        playbook = create_ospf_neighbor_playbook()
    elif slug == "bgp-neighbor-down":
        from .bgp_neighbor_down import create_bgp_neighbor_playbook
        playbook = create_bgp_neighbor_playbook()
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
