"""
OSPF LSA storm troubleshooting playbook.

This module provides deterministic troubleshooting for OSPF LSA storm issues
following RFC 2328 (OSPF Version 2) standards.
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


def create_ospf_lsa_storm_playbook() -> Playbook:
    """Create the OSPF LSA storm troubleshooting playbook."""

    # RFC citations for OSPF LSA storm troubleshooting
    rfc_2328_retransmit = RFCSectionRef(
        rfc=2328,
        section="13",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_pacing = RFCSectionRef(
        rfc=2328,
        section="16.1",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_maxlsa = RFCSectionRef(
        rfc=2328,
        section="12.4",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_drbdr = RFCSectionRef(
        rfc=2328,
        section="9.1",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_misconfig = RFCSectionRef(
        rfc=2328,
        section="12.5",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_lsa_types = RFCSectionRef(
        rfc=2328,
        section="12",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_spf_throttle = RFCSectionRef(
        rfc=2328,
        section="16.1",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rfc_2328_interface_errors = RFCSectionRef(
        rfc=2328,
        section="8.2",
        title="OSPF Version 2",
        url="https://tools.ietf.org/html/rfc2328",
    )

    rules = [
        Rule(
            id="check_lsa_retransmit_queues",
            if_="LSA retransmit queues are overflowing",
            then_check="Check LSA retransmit queues and queue depths",
            then_fix="Clear retransmit queues and investigate source",
            verify="Retransmit queues should be manageable",
            citations=[rfc_2328_retransmit],
        ),
        Rule(
            id="check_lsa_pacing_throttle",
            if_="LSA pacing/throttle is insufficient",
            then_check="Verify LSA pacing and throttle configuration",
            then_fix="Adjust LSA pacing parameters",
            verify="LSA pacing should prevent storms",
            citations=[rfc_2328_pacing],
        ),
        Rule(
            id="check_max_lsa_limits",
            if_="Max-LSA limits are being exceeded",
            then_check="Check Max-LSA configuration and limits",
            then_fix="Increase Max-LSA limits if needed",
            verify="Max-LSA limits should be appropriate",
            citations=[rfc_2328_maxlsa],
        ),
        Rule(
            id="check_drbdr_churn",
            if_="DR/BDR churn is causing LSA storms",
            then_check="Monitor DR/BDR election stability",
            then_fix="Stabilize DR/BDR election",
            verify="DR/BDR should be stable",
            citations=[rfc_2328_drbdr],
        ),
        Rule(
            id="check_misconfigs_generating_lsas",
            if_="Misconfigurations are generating excess LSAs",
            then_check="Identify misconfigurations generating LSAs",
            then_fix="Correct misconfigurations",
            verify="No misconfigurations should generate excess LSAs",
            citations=[rfc_2328_misconfig],
        ),
        Rule(
            id="check_lsa_type_distribution",
            if_="LSA type distribution is abnormal",
            then_check="Analyze LSA type distribution (1/2/3/5/7)",
            then_fix="Investigate abnormal LSA type patterns",
            verify="LSA type distribution should be normal",
            citations=[rfc_2328_lsa_types],
        ),
        Rule(
            id="check_spf_throttle_timers",
            if_="SPF throttle/timers are insufficient",
            then_check="Check SPF throttle and timer configuration",
            then_fix="Adjust SPF throttle parameters",
            verify="SPF throttle should prevent excessive computation",
            citations=[rfc_2328_spf_throttle],
        ),
        Rule(
            id="check_interface_errors_drops",
            if_="Interface errors/drops are prompting floods",
            then_check="Check interface errors and drops",
            then_fix="Resolve interface issues",
            verify="Interfaces should be healthy",
            citations=[rfc_2328_interface_errors],
        ),
    ]

    return Playbook(
        id="ospf-lsa-storm",
        name="OSPF LSA Storm Troubleshooting",
        description="Deterministic troubleshooting for OSPF LSA storm issues",
        rules=rules,
        citations=[
            rfc_2328_retransmit,
            rfc_2328_pacing,
            rfc_2328_maxlsa,
            rfc_2328_drbdr,
            rfc_2328_misconfig,
            rfc_2328_lsa_types,
            rfc_2328_spf_throttle,
            rfc_2328_interface_errors,
        ],
    )


def run_ospf_lsa_storm_playbook(ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run the OSPF LSA storm troubleshooting playbook."""

    playbook = create_ospf_lsa_storm_playbook()
    steps = []

    # Step 1: Check LSA retransmit queues
    step1_commands = [
        VendorCommandIR(intent="show_ospf_retransmit_queues", params={}),
        VendorCommandIR(intent="show_ospf_neighbor_retransmit", params={}),
    ]
    step1_citations = [playbook.citations[0]]
    steps.append(
        PlayResultStep(
            check="Check LSA retransmit queues and queue depths",
            commands=step1_commands,
            citations=step1_citations,
        )
    )

    # Step 2: Check LSA pacing/throttle
    step2_commands = [
        VendorCommandIR(intent="show_ospf_lsa_pacing", params={}),
        VendorCommandIR(intent="show_ospf_throttle_config", params={}),
    ]
    step2_citations = [playbook.citations[1]]
    steps.append(
        PlayResultStep(
            check="Verify LSA pacing and throttle configuration",
            commands=step2_commands,
            citations=step2_citations,
        )
    )

    # Step 3: Check Max-LSA limits
    step3_commands = [
        VendorCommandIR(intent="show_ospf_max_lsa", params={}),
        VendorCommandIR(intent="show_ospf_max_lsa_warnings", params={}),
    ]
    step3_citations = [playbook.citations[2]]
    steps.append(
        PlayResultStep(
            check="Check Max-LSA configuration and limits",
            commands=step3_commands,
            citations=step3_citations,
        )
    )

    # Step 4: Check DR/BDR churn
    step4_commands = [
        VendorCommandIR(intent="show_ospf_neighbor_dr", params={}),
        VendorCommandIR(intent="show_ospf_interface_dr", params={}),
    ]
    step4_citations = [playbook.citations[3]]
    steps.append(
        PlayResultStep(
            check="Monitor DR/BDR election stability",
            commands=step4_commands,
            citations=step4_citations,
        )
    )

    # Step 5: Check misconfigs generating LSAs
    step5_commands = [
        VendorCommandIR(intent="show_ospf_lsa_generators", params={}),
        VendorCommandIR(intent="show_ospf_misconfigs", params={}),
    ]
    step5_citations = [playbook.citations[4]]
    steps.append(
        PlayResultStep(
            check="Identify misconfigurations generating LSAs",
            commands=step5_commands,
            citations=step5_citations,
        )
    )

    # Step 6: Check LSA type distribution
    step6_commands = [
        VendorCommandIR(intent="show_ospf_lsa_types", params={}),
        VendorCommandIR(intent="show_ospf_lsa_distribution", params={}),
    ]
    step6_citations = [playbook.citations[5]]
    steps.append(
        PlayResultStep(
            check="Analyze LSA type distribution (1/2/3/5/7)",
            commands=step6_commands,
            citations=step6_citations,
        )
    )

    # Step 7: Check SPF throttle/timers
    step7_commands = [
        VendorCommandIR(intent="show_ospf_spf_throttle", params={}),
        VendorCommandIR(intent="show_ospf_spf_timers", params={}),
    ]
    step7_citations = [playbook.citations[6]]
    steps.append(
        PlayResultStep(
            check="Check SPF throttle and timer configuration",
            commands=step7_commands,
            citations=step7_citations,
        )
    )

    # Step 8: Check interface errors/drops
    step8_commands = [
        VendorCommandIR(intent="show_ospf_interface_errors", params={}),
        VendorCommandIR(intent="show_ospf_interface_drops", params={}),
    ]
    step8_citations = [playbook.citations[7]]
    steps.append(
        PlayResultStep(
            check="Check interface errors and drops",
            commands=step8_commands,
            citations=step8_citations,
        )
    )

    return PlayResult(
        playbook_id=playbook.id,
        target=ctx.target,
        steps=steps,
        facts=get_ospf_lsa_storm_facts(),
        assumptions=get_ospf_lsa_storm_assumptions(),
        operator_actions=get_ospf_lsa_storm_operator_actions(),
    )


def get_ospf_lsa_storm_facts() -> List[Dict[str, Any]]:
    """Get OSPF LSA storm troubleshooting facts."""
    return [
        {
            "fact": "LSA retransmit queues can overflow during storms",
            "source": "RFC 2328 Section 13",
            "confidence": 0.95,
        },
        {
            "fact": "LSA pacing and throttle mechanisms prevent storms",
            "source": "RFC 2328 Section 16.1",
            "confidence": 0.90,
        },
        {
            "fact": "Max-LSA limits protect against excessive LSAs",
            "source": "RFC 2328 Section 12.4",
            "confidence": 0.85,
        },
        {
            "fact": "DR/BDR churn can cause LSA storms",
            "source": "RFC 2328 Section 9.1",
            "confidence": 0.80,
        },
        {
            "fact": "Misconfigurations can generate excess LSAs",
            "source": "RFC 2328 Section 12.5",
            "confidence": 0.85,
        },
        {
            "fact": "LSA type distribution indicates storm patterns",
            "source": "RFC 2328 Section 12",
            "confidence": 0.80,
        },
        {
            "fact": "SPF throttle prevents excessive computation",
            "source": "RFC 2328 Section 16.1",
            "confidence": 0.90,
        },
        {
            "fact": "Interface errors/drops can trigger LSA floods",
            "source": "RFC 2328 Section 8.2",
            "confidence": 0.85,
        },
    ]


def get_ospf_lsa_storm_assumptions() -> List[Dict[str, Any]]:
    """Get OSPF LSA storm troubleshooting assumptions."""
    return [
        {
            "assumption": "OSPF network should be stable under normal conditions",
            "confidence": 0.95,
            "rationale": "OSPF should maintain stability without excessive LSA generation",
        },
        {
            "assumption": "Network topology is relatively stable",
            "confidence": 0.90,
            "rationale": "Topology changes should be infrequent and controlled",
        },
        {
            "assumption": "Device has sufficient resources for OSPF processing",
            "confidence": 0.85,
            "rationale": "OSPF processing requires CPU and memory resources",
        },
        {
            "assumption": "OSPF configuration is intentional and correct",
            "confidence": 0.80,
            "rationale": "OSPF configuration should be stable and well-defined",
        },
        {
            "assumption": "Interface errors are not normal",
            "confidence": 0.75,
            "rationale": "Interfaces should be healthy in normal operation",
        },
    ]


def get_ospf_lsa_storm_operator_actions() -> List[Dict[str, Any]]:
    """Get OSPF LSA storm troubleshooting operator actions."""
    return [
        {
            "action": "Check LSA retransmit queues and clear if needed",
            "priority": "high",
            "rationale": "Overflowing queues indicate storm conditions",
        },
        {
            "action": "Verify LSA pacing and throttle configuration",
            "priority": "high",
            "rationale": "Proper pacing prevents storm propagation",
        },
        {
            "action": "Check Max-LSA limits and adjust if necessary",
            "priority": "medium",
            "rationale": "Limits protect against excessive LSAs",
        },
        {
            "action": "Monitor DR/BDR election stability",
            "priority": "medium",
            "rationale": "DR/BDR churn can cause storms",
        },
        {
            "action": "Identify and correct misconfigurations",
            "priority": "high",
            "rationale": "Misconfigs can generate excess LSAs",
        },
        {
            "action": "Analyze LSA type distribution patterns",
            "priority": "medium",
            "rationale": "Abnormal patterns indicate storm sources",
        },
        {
            "action": "Check SPF throttle configuration",
            "priority": "medium",
            "rationale": "Throttle prevents excessive computation",
        },
        {
            "action": "Resolve interface errors and drops",
            "priority": "high",
            "rationale": "Interface issues can trigger floods",
        },
    ]
