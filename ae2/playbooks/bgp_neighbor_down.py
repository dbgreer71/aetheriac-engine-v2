"""
BGP neighbor-down troubleshooting playbook.

This module provides deterministic BGP neighbor troubleshooting with
RFC citations and vendor-specific command rendering.
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


def create_bgp_neighbor_playbook() -> Playbook:
    """Create the BGP neighbor-down troubleshooting playbook."""

    # RFC 4271 citations for BGP neighbor states and troubleshooting
    rfc_4271_session_states = RFCSectionRef(
        rfc=4271,
        section="8",
        title="BGP Finite State Machine",
        url="https://tools.ietf.org/html/rfc4271#section-8",
    )

    rfc_4271_transport = RFCSectionRef(
        rfc=4271,
        section="6.8",
        title="TCP Connection",
        url="https://tools.ietf.org/html/rfc4271#section-6.8",
    )

    rfc_4271_timers = RFCSectionRef(
        rfc=4271,
        section="6.5",
        title="Hold Timer",
        url="https://tools.ietf.org/html/rfc4271#section-6.5",
    )

    rfc_4271_policy = RFCSectionRef(
        rfc=4271,
        section="9",
        title="UPDATE Message Handling",
        url="https://tools.ietf.org/html/rfc4271#section-9",
    )

    # RFC 2385 for TCP-MD5 authentication
    rfc_2385_auth = RFCSectionRef(
        rfc=2385,
        section="1",
        title="Introduction",
        url="https://tools.ietf.org/html/rfc2385#section-1",
    )

    # RFC 5082 for GTSM (TTL/Hop-limit)
    rfc_5082_gtsm = RFCSectionRef(
        rfc=5082,
        section="1",
        title="Introduction",
        url="https://tools.ietf.org/html/rfc5082#section-1",
    )

    # RFC 4760 for MP-BGP (AFI/SAFI)
    rfc_4760_mpbgp = RFCSectionRef(
        rfc=4760,
        section="1",
        title="Introduction",
        url="https://tools.ietf.org/html/rfc4760#section-1",
    )

    rules = [
        Rule(
            id="check_neighbor_fsm_state",
            if_="BGP neighbor FSM state check",
            then_check="Check BGP neighbor FSM state (Idle/Active/Connect/OpenSent/OpenConfirm/Established)",
            then_fix=None,
            verify="Neighbor should be in Established state",
            citations=[rfc_4271_session_states],
        ),
        Rule(
            id="check_interface_status_mtu",
            if_="Interface status and MTU check",
            then_check="Verify interface is up/up and MTU matches peer",
            then_fix="Configure matching MTU on both interfaces",
            verify="Interface should be up/up with matching MTU",
            citations=[rfc_4271_transport],
        ),
        Rule(
            id="check_authentication_md5_keychain",
            if_="Authentication and MD5 keychain check",
            then_check="Verify TCP MD5 authentication and keychain configuration",
            then_fix="Configure matching authentication on both sides",
            verify="Authentication should be consistent",
            citations=[rfc_2385_auth],
        ),
        Rule(
            id="check_ebgp_multihop_ttl_gtsm",
            if_="EBGP multihop TTL and GTSM check",
            then_check="Verify TTL/hop-limit for EBGP single-hop vs multi-hop",
            then_fix="Configure appropriate TTL for EBGP multihop",
            verify="TTL should be sufficient for path length",
            citations=[rfc_5082_gtsm],
        ),
        Rule(
            id="check_keepalive_hold_timers_mismatch",
            if_="Keepalive and hold timer mismatch check",
            then_check="Verify keepalive and hold-time consistency",
            then_fix="Configure matching timers on both sides",
            verify="Timers should be consistent",
            citations=[rfc_4271_timers],
        ),
        Rule(
            id="check_afi_safi_mismatch",
            if_="Address Family and SAFI mismatch check",
            then_check="Verify negotiated address-family and SAFI",
            then_fix="Configure matching address-families",
            verify="Address-families should match",
            citations=[rfc_4760_mpbgp],
        ),
        Rule(
            id="check_route_policy_filters",
            if_="Route policy and filter check",
            then_check="Verify inbound/outbound route-maps and policies",
            then_fix="Review and adjust route policies",
            verify="Policies should allow expected routes",
            citations=[rfc_4271_policy],
        ),
        Rule(
            id="check_peer_asn_mismatch",
            if_="Peer ASN and local-AS mismatch check",
            then_check="Verify local-AS and neighbor remote-as configuration",
            then_fix="Configure correct ASN values",
            verify="ASN configuration should match",
            citations=[rfc_4271_session_states],
        ),
    ]

    return Playbook(
        id="bgp-neighbor-down",
        applies_to=["BGP", "BGPv4"],
        rules=rules,
    )


def run_bgp_playbook(ctx: PlayContext, store: IndexStore) -> PlayResult:
    """Run the BGP neighbor-down playbook."""
    playbook = create_bgp_neighbor_playbook()

    steps = []
    for rule in playbook.rules:
        commands = _generate_bgp_commands_for_rule(rule, ctx)
        result_text = _generate_bgp_result_text(rule, ctx)

        step = PlayResultStep(
            rule_id=rule.id,
            check=rule.then_check,
            result=result_text,
            fix=rule.then_fix,
            verify=rule.verify,
            commands=commands,
            citations=rule.citations,
        )
        steps.append(step)

    return PlayResult(
        playbook_id=playbook.id,
        steps=steps,
    )


def _generate_bgp_commands_for_rule(rule: Rule, ctx: PlayContext) -> List[str]:
    """Generate vendor-specific commands for BGP troubleshooting rule."""
    commands = []
    vendor = ctx.vendor
    peer = ctx.peer
    iface = ctx.iface

    if rule.id == "check_neighbor_fsm_state":
        if vendor == "iosxe":
            commands.extend(
                [
                    "show ip bgp summary",
                    (
                        f"show ip bgp neighbors {peer}"
                        if peer
                        else "show ip bgp neighbors"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    "show bgp summary",
                    f"show bgp neighbor {peer}" if peer else "show bgp neighbor",
                ]
            )

    elif rule.id == "check_interface_status_mtu":
        if vendor == "iosxe":
            commands.extend(
                [
                    f"show interface {iface}" if iface else "show interface",
                    (
                        f"show ip bgp neighbors {peer} | include interface"
                        if peer
                        else "show ip bgp neighbors | include interface"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    (
                        f"show interfaces {iface} terse"
                        if iface
                        else "show interfaces terse"
                    ),
                    (
                        f"show bgp neighbor {peer} | include interface"
                        if peer
                        else "show bgp neighbor | include interface"
                    ),
                ]
            )

    elif rule.id == "check_authentication_md5_keychain":
        if vendor == "iosxe":
            commands.extend(
                [
                    "show key chain",
                    (
                        f"show ip bgp neighbors {peer} | include authentication"
                        if peer
                        else "show ip bgp neighbors | include authentication"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    "show security authentication-key-chains",
                    (
                        f"show bgp neighbor {peer} | include authentication"
                        if peer
                        else "show bgp neighbor | include authentication"
                    ),
                ]
            )

    elif rule.id == "check_ebgp_multihop_ttl_gtsm":
        if vendor == "iosxe":
            commands.extend(
                [
                    "show running-config | section ^router bgp",
                    (
                        f"show ip bgp neighbors {peer} | include ttl"
                        if peer
                        else "show ip bgp neighbors | include ttl"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    "show configuration protocols bgp | display set",
                    (
                        f"show bgp neighbor {peer} | include ttl"
                        if peer
                        else "show bgp neighbor | include ttl"
                    ),
                ]
            )

    elif rule.id == "check_keepalive_hold_timers_mismatch":
        if vendor == "iosxe":
            commands.extend(
                [
                    (
                        f"show ip bgp neighbors {peer} | include timers"
                        if peer
                        else "show ip bgp neighbors | include timers"
                    ),
                    "show running-config | section ^router bgp",
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    (
                        f"show bgp neighbor {peer} | include timers"
                        if peer
                        else "show bgp neighbor | include timers"
                    ),
                    "show configuration protocols bgp | display set",
                ]
            )

    elif rule.id == "check_afi_safi_mismatch":
        if vendor == "iosxe":
            commands.extend(
                [
                    (
                        f"show ip bgp neighbors {peer} | include Address-family"
                        if peer
                        else "show ip bgp neighbors | include Address-family"
                    ),
                    "show running-config | section ^router bgp",
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    (
                        f"show bgp neighbor {peer} | include family"
                        if peer
                        else "show bgp neighbor | include family"
                    ),
                    "show configuration protocols bgp | display set",
                ]
            )

    elif rule.id == "check_route_policy_filters":
        if vendor == "iosxe":
            commands.extend(
                [
                    "show route-map",
                    (
                        f"show ip bgp neighbors {peer} advertised-routes"
                        if peer
                        else "show ip bgp neighbors advertised-routes"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    "show policy-options",
                    (
                        f"show bgp neighbor {peer} detail"
                        if peer
                        else "show bgp neighbor detail"
                    ),
                ]
            )

    elif rule.id == "check_peer_asn_mismatch":
        if vendor == "iosxe":
            commands.extend(
                [
                    "show running-config | section ^router bgp",
                    (
                        f"show ip bgp neighbors {peer} | include AS"
                        if peer
                        else "show ip bgp neighbors | include AS"
                    ),
                ]
            )
        elif vendor == "junos":
            commands.extend(
                [
                    "show configuration protocols bgp | display set",
                    (
                        f"show bgp neighbor {peer} | include AS"
                        if peer
                        else "show bgp neighbor | include AS"
                    ),
                ]
            )

    return commands


def _generate_bgp_result_text(rule: Rule, ctx: PlayContext) -> str:
    """Generate result text for BGP troubleshooting rule."""
    peer = ctx.peer or "neighbor"
    iface = ctx.iface or "interface"

    if rule.id == "check_neighbor_fsm_state":
        return f"Check BGP neighbor FSM state for {peer} using vendor-specific commands"
    elif rule.id == "check_interface_status_mtu":
        return f"Verify interface {iface} status and MTU configuration for {peer}"
    elif rule.id == "check_authentication_md5_keychain":
        return f"Verify TCP-MD5 authentication and keychain configuration for {peer}"
    elif rule.id == "check_ebgp_multihop_ttl_gtsm":
        return f"Check eBGP multihop and TTL/GTSM configuration for {peer}"
    elif rule.id == "check_keepalive_hold_timers_mismatch":
        return f"Verify keepalive and hold timer configuration for {peer}"
    elif rule.id == "check_afi_safi_mismatch":
        return f"Check Address Family and SAFI configuration for {peer}"
    elif rule.id == "check_route_policy_filters":
        return f"Review import/export policies affecting {peer}"
    elif rule.id == "check_peer_asn_mismatch":
        return f"Verify local-AS and neighbor remote-as configuration for {peer}"
    else:
        return rule.then_check


def get_bgp_playbook_explanation(vendor: str) -> Dict[str, Any]:
    """Get explanation of BGP neighbor-down playbook structure."""
    playbook = create_bgp_neighbor_playbook()

    return {
        "playbook": {
            "id": playbook.id,
            "applies_to": playbook.applies_to,
        },
        "rules": [
            {
                "id": rule.id,
                "if": rule.if_,
                "check": rule.then_check,
                "fix": rule.then_fix,
                "verify": rule.verify,
                "citations": [
                    {"rfc": c.rfc, "section": c.section, "title": c.title}
                    for c in rule.citations
                ],
            }
            for rule in playbook.rules
        ],
        "vendor": vendor,
        "total_rules": len(playbook.rules),
    }
