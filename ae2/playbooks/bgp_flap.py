"""
BGP flap troubleshooting playbook.

This module provides deterministic troubleshooting for BGP flap issues
following RFC 4271 (BGP-4) and RFC 5082 (GTSM) standards.
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
from ..vendor_ir.models import VendorCommandIR


def create_bgp_flap_playbook() -> Playbook:
    """Create the BGP flap troubleshooting playbook."""

    # RFC citations for BGP troubleshooting
    rfc_4271_bgp = RFCSectionRef(
        rfc=4271,
        section="6.5",
        title="BGP-4 Protocol",
        url="https://tools.ietf.org/html/rfc4271",
    )

    rfc_4271_timers = RFCSectionRef(
        rfc=4271,
        section="10",
        title="BGP-4 Protocol",
        url="https://tools.ietf.org/html/rfc4271",
    )

    rfc_4271_transport = RFCSectionRef(
        rfc=4271,
        section="6.8",
        title="BGP-4 Protocol",
        url="https://tools.ietf.org/html/rfc4271",
    )

    rfc_5082_gtsm = RFCSectionRef(
        rfc=5082,
        section="3",
        title="The Generalized TTL Security Mechanism (GTSM)",
        url="https://tools.ietf.org/html/rfc5082",
    )

    rfc_7454_policy = RFCSectionRef(
        rfc=7454,
        section="5.1",
        title="BGP Operations and Security",
        url="https://tools.ietf.org/html/rfc7454",
    )

    rfc_7454_prefix = RFCSectionRef(
        rfc=7454,
        section="2.1",
        title="BGP Operations and Security",
        url="https://tools.ietf.org/html/rfc7454",
    )

    rfc_7454_dampening = RFCSectionRef(
        rfc=7454,
        section="2.3",
        title="BGP Operations and Security",
        url="https://tools.ietf.org/html/rfc7454",
    )

    rfc_7454_load = RFCSectionRef(
        rfc=7454,
        section="1",
        title="BGP Operations and Security",
        url="https://tools.ietf.org/html/rfc7454",
    )

    rules = [
        Rule(
            id="check_neighbor_flap_history",
            if_="BGP neighbor has recent flap history",
            then_check="Check BGP neighbor flap history and last reset reason",
            then_fix="Investigate root cause of previous flaps",
            verify="Neighbor should have stable history",
            citations=[rfc_4271_bgp],
        ),
        Rule(
            id="check_keepalive_hold_timers",
            if_="Keepalive/hold timers are unstable",
            then_check="Verify keepalive and hold timer configuration",
            then_fix="Configure consistent keepalive/hold timers",
            verify="Timers should be stable and consistent",
            citations=[rfc_4271_timers],
        ),
        Rule(
            id="check_gtsm_ttl_config",
            if_="GTSM/TTL causing adjacency drops",
            then_check="Check GTSM/TTL configuration",
            then_fix="Configure appropriate TTL values",
            verify="TTL should not cause adjacency drops",
            citations=[rfc_5082_gtsm],
        ),
        Rule(
            id="check_policy_churn",
            if_="Policy churn affecting BGP stability",
            then_check="Check import/export policy changes",
            then_fix="Stabilize policy configuration",
            verify="Policies should be stable",
            citations=[rfc_7454_policy],
        ),
        Rule(
            id="check_prefix_churn",
            if_="Prefix updates/withdraws causing instability",
            then_check="Monitor prefix update/withdraw frequency",
            then_fix="Investigate source of prefix churn",
            verify="Prefix announcements should be stable",
            citations=[rfc_7454_prefix],
        ),
        Rule(
            id="check_transport_health",
            if_="Transport layer issues (RST/retrans)",
            then_check="Check TCP transport health and retransmissions",
            then_fix="Resolve transport layer issues",
            verify="Transport should be healthy",
            citations=[rfc_4271_transport],
        ),
        Rule(
            id="check_dampening_effect",
            if_="Route dampening affecting reachability",
            then_check="Check route dampening configuration and status",
            then_fix="Adjust dampening parameters if needed",
            verify="Dampening should not block legitimate routes",
            citations=[rfc_7454_dampening],
        ),
        Rule(
            id="check_device_load_spikes",
            if_="Device load spikes around flap events",
            then_check="Monitor device CPU/memory during flap events",
            then_fix="Optimize device performance",
            verify="Device should handle BGP load without spikes",
            citations=[rfc_7454_load],
        ),
    ]

    return Playbook(
        id="bgp-flap",
        applies_to=["bgp", "border gateway protocol"],
        rules=rules,
    )


def run_bgp_flap_playbook(ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run the BGP flap troubleshooting playbook."""

    playbook = create_bgp_flap_playbook()
    steps = []

    # Step 1: Check neighbor flap history
    step1_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_history", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_events", params={"neighbor": ctx.target}
        ),
    ]
    step1_citations = [playbook.citations[0]]
    steps.append(
        PlayResultStep(
            check="Check BGP neighbor flap history and last reset reason",
            commands=step1_commands,
            citations=step1_citations,
        )
    )

    # Step 2: Check keepalive/hold timers
    step2_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_timers", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_config", params={"neighbor": ctx.target}
        ),
    ]
    step2_citations = [playbook.citations[1]]
    steps.append(
        PlayResultStep(
            check="Verify keepalive and hold timer configuration",
            commands=step2_commands,
            citations=step2_citations,
        )
    )

    # Step 3: Check GTSM/TTL configuration
    step3_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_ttl", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_gtsm", params={"neighbor": ctx.target}
        ),
    ]
    step3_citations = [playbook.citations[3]]
    steps.append(
        PlayResultStep(
            check="Check GTSM/TTL configuration",
            commands=step3_commands,
            citations=step3_citations,
        )
    )

    # Step 4: Check policy churn
    step4_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_policy", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_advertised", params={"neighbor": ctx.target}
        ),
    ]
    step4_citations = [playbook.citations[4]]
    steps.append(
        PlayResultStep(
            check="Check import/export policy changes",
            commands=step4_commands,
            citations=step4_citations,
        )
    )

    # Step 5: Check prefix churn
    step5_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_received", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_advertised", params={"neighbor": ctx.target}
        ),
    ]
    step5_citations = [playbook.citations[5]]
    steps.append(
        PlayResultStep(
            check="Monitor prefix update/withdraw frequency",
            commands=step5_commands,
            citations=step5_citations,
        )
    )

    # Step 6: Check transport health
    step6_commands = [
        VendorCommandIR(
            intent="show_bgp_neighbor_transport", params={"neighbor": ctx.target}
        ),
        VendorCommandIR(
            intent="show_bgp_neighbor_retrans", params={"neighbor": ctx.target}
        ),
    ]
    step6_citations = [playbook.citations[2]]
    steps.append(
        PlayResultStep(
            check="Check TCP transport health and retransmissions",
            commands=step6_commands,
            citations=step6_citations,
        )
    )

    # Step 7: Check dampening effect
    step7_commands = [
        VendorCommandIR(intent="show_bgp_dampening", params={}),
        VendorCommandIR(intent="show_bgp_dampening_penalties", params={}),
    ]
    step7_citations = [playbook.citations[6]]
    steps.append(
        PlayResultStep(
            check="Check route dampening configuration and status",
            commands=step7_commands,
            citations=step7_citations,
        )
    )

    # Step 8: Check device load spikes
    step8_commands = [
        VendorCommandIR(intent="show_processes_cpu", params={}),
        VendorCommandIR(intent="show_memory_statistics", params={}),
    ]
    step8_citations = [playbook.citations[7]]
    steps.append(
        PlayResultStep(
            check="Monitor device CPU/memory during flap events",
            commands=step8_commands,
            citations=step8_citations,
        )
    )

    return PlayResult(
        playbook_id=playbook.id,
        target=ctx.target,
        steps=steps,
        facts=get_bgp_flap_facts(),
        assumptions=get_bgp_flap_assumptions(),
        operator_actions=get_bgp_flap_operator_actions(),
    )


def get_bgp_flap_facts() -> List[Dict[str, Any]]:
    """Get BGP flap troubleshooting facts."""
    return [
        {
            "fact": "BGP neighbor flap indicates instability in the BGP session",
            "source": "RFC 4271",
            "confidence": 0.95,
        },
        {
            "fact": "Keepalive/hold timer mismatches can cause session flaps",
            "source": "RFC 4271 Section 10",
            "confidence": 0.90,
        },
        {
            "fact": "GTSM/TTL misconfiguration can cause adjacency drops",
            "source": "RFC 5082 Section 3",
            "confidence": 0.85,
        },
        {
            "fact": "Policy churn can destabilize BGP sessions",
            "source": "RFC 7454 Section 5.1",
            "confidence": 0.80,
        },
        {
            "fact": "Excessive prefix updates/withdraws indicate upstream issues",
            "source": "RFC 7454 Section 2.1",
            "confidence": 0.85,
        },
        {
            "fact": "Transport layer issues (RST/retrans) can cause flaps",
            "source": "RFC 4271 Section 6.8",
            "confidence": 0.90,
        },
        {
            "fact": "Route dampening can affect legitimate route reachability",
            "source": "RFC 7454 Section 2.3",
            "confidence": 0.80,
        },
        {
            "fact": "Device load spikes during flap events indicate resource constraints",
            "source": "RFC 7454 Section 1",
            "confidence": 0.75,
        },
    ]


def get_bgp_flap_assumptions() -> List[Dict[str, Any]]:
    """Get BGP flap troubleshooting assumptions."""
    return [
        {
            "assumption": "BGP neighbor is configured and should be stable",
            "confidence": 0.95,
            "rationale": "BGP sessions should maintain stability under normal conditions",
        },
        {
            "assumption": "Network connectivity between peers is functional",
            "confidence": 0.90,
            "rationale": "BGP requires underlying network connectivity",
        },
        {
            "assumption": "Device has sufficient resources for BGP processing",
            "confidence": 0.85,
            "rationale": "BGP processing requires CPU and memory resources",
        },
        {
            "assumption": "Policy configuration is intentional and correct",
            "confidence": 0.80,
            "rationale": "BGP policies should be stable and well-defined",
        },
        {
            "assumption": "Upstream network changes are legitimate",
            "confidence": 0.75,
            "rationale": "Prefix changes should be legitimate network events",
        },
    ]


def get_bgp_flap_operator_actions() -> List[Dict[str, Any]]:
    """Get BGP flap troubleshooting operator actions."""
    return [
        {
            "action": "Check BGP neighbor status and flap history",
            "priority": "high",
            "rationale": "Identify recent flap patterns and causes",
        },
        {
            "action": "Verify keepalive/hold timer configuration",
            "priority": "high",
            "rationale": "Timer mismatches are common cause of flaps",
        },
        {
            "action": "Check GTSM/TTL configuration",
            "priority": "medium",
            "rationale": "TTL misconfiguration can cause adjacency drops",
        },
        {
            "action": "Monitor policy changes and their impact",
            "priority": "medium",
            "rationale": "Policy churn can destabilize sessions",
        },
        {
            "action": "Investigate prefix update/withdraw patterns",
            "priority": "medium",
            "rationale": "Excessive churn indicates upstream issues",
        },
        {
            "action": "Check transport layer health",
            "priority": "high",
            "rationale": "TCP issues can cause session drops",
        },
        {
            "action": "Review dampening configuration",
            "priority": "low",
            "rationale": "Dampening can affect legitimate routes",
        },
        {
            "action": "Monitor device resource utilization",
            "priority": "medium",
            "rationale": "Resource constraints can cause instability",
        },
    ]
