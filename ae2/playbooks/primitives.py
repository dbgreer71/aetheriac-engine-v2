"""
Shared troubleshooting primitives for AE v2 playbooks.

This module provides deterministic helpers that return PlayResultStep objects for common
troubleshooting operations across different vendors and protocols.
"""

from .models import PlayResultStep, RFCSectionRef


def reachability(
    peer: str = None, dest: str = None, iface: str = None
) -> PlayResultStep:
    """Check reachability to peer, destination, or interface."""
    check = "Verify reachability"
    if peer:
        check += f" to peer {peer}"
    elif dest:
        check += f" to destination {dest}"
    elif iface:
        check += f" to interface {iface}"

    commands = [
        "ping {target}",
        "traceroute {target}",
        "show ip route {target}",
    ]

    citations = [
        RFCSectionRef(
            rfc=2460,
            section="1",
            title="Internet Protocol, Version 6 (IPv6) Specification",
            url="https://tools.ietf.org/html/rfc2460",
        )
    ]

    return PlayResultStep(
        rule_id="check_reachability",
        check=check,
        result=f"Check network reachability to {peer or dest or iface}",
        fix=None,
        verify=None,
        commands=commands,
        citations=citations,
    )


def iface_link_mtu(iface: str) -> PlayResultStep:
    """Check interface link MTU configuration."""
    check = f"Verify MTU configuration on interface {iface}"

    commands = [
        "show interface {iface}",
        "show interface {iface} mtu",
        "show interface {iface} capabilities",
    ]

    citations = [
        RFCSectionRef(
            rfc=2460,
            section="1",
            title="Internet Protocol, Version 6 (IPv6) Specification",
            url="https://tools.ietf.org/html/rfc2460",
        )
    ]

    return PlayResultStep(
        rule_id="check_mtu",
        check=check,
        result=f"Verify MTU values match on interface {iface}",
        fix="Configure matching MTU on both interfaces",
        verify="MTU values should match on both sides",
        commands=commands,
        citations=citations,
    )


def lacp_actor_partner_state(bundle: str = None, iface: str = None) -> PlayResultStep:
    """Check LACP actor and partner state."""
    target = bundle or iface
    check = f"Verify LACP actor and partner state for {target}"

    commands = [
        "show lacp neighbor {target}",
        "show lacp interfaces {target}",
        "show etherchannel summary",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="IEEE 802.1AX-2020 - Link Aggregation",
            url="https://standards.ieee.org/standard/802_1AX-2020.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_lacp_state",
        check=check,
        result=f"Check LACP actor and partner state for {target}",
        fix=None,
        verify="LACP state should be collecting or defaulted",
        commands=commands,
        citations=citations,
    )


def lacp_key_system_priority(bundle: str = None, iface: str = None) -> PlayResultStep:
    """Check LACP key and system priority configuration."""
    target = bundle or iface
    check = f"Verify LACP key and system priority for {target}"

    commands = [
        "show lacp neighbor {target}",
        "show lacp interfaces {target}",
        "show etherchannel summary",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="IEEE 802.1AX-2020 - Link Aggregation",
            url="https://standards.ieee.org/standard/802_1AX-2020.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_lacp_key_priority",
        check=check,
        result=f"Verify LACP key and system priority for {target}",
        fix="Configure matching LACP key and system priority",
        verify="LACP key and system priority should match",
        commands=commands,
        citations=citations,
    )


def bundle_members_status(bundle: str) -> PlayResultStep:
    """Check bundle member interface status."""
    check = f"Verify bundle member status for {bundle}"

    commands = [
        "show etherchannel summary",
        "show port-channel summary",
        "show interfaces {bundle}",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="IEEE 802.1AX-2020 - Link Aggregation",
            url="https://standards.ieee.org/standard/802_1AX-2020.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_bundle_members",
        check=check,
        result=f"Check bundle member interface status for {bundle}",
        fix=None,
        verify="Bundle members should be up and not suspended",
        commands=commands,
        citations=citations,
    )


def vlan_trunk_consistency(iface: str = None, bundle: str = None) -> PlayResultStep:
    """Check VLAN trunk configuration consistency."""
    target = iface or bundle
    check = f"Verify VLAN trunk configuration for {target}"

    commands = [
        "show interface {target} switchport",
        "show interfaces trunk",
        "show vlan",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="IEEE 802.1Q - Virtual Bridged Local Area Networks",
            url="https://standards.ieee.org/standard/802_1Q-2018.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_vlan_trunk",
        check=check,
        result=f"Verify VLAN trunk configuration for {target}",
        fix="Configure matching VLAN trunk settings",
        verify="VLAN trunk configuration should be consistent",
        commands=commands,
        citations=citations,
    )


def stp_blocking_state(iface: str = None, bundle: str = None) -> PlayResultStep:
    """Check spanning tree blocking state."""
    target = iface or bundle
    check = f"Verify spanning tree state for {target}"

    commands = [
        "show spanning-tree interface {target}",
        "show spanning-tree",
        "show spanning-tree detail",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="IEEE 802.1D - Media Access Control (MAC) Bridges",
            url="https://standards.ieee.org/standard/802_1D-2004.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_stp_state",
        check=check,
        result=f"Check spanning tree blocking state for {target}",
        fix=None,
        verify="Interface should not be in blocking state",
        commands=commands,
        citations=citations,
    )


def errdisable_sanity(iface: str) -> PlayResultStep:
    """Check interface errdisable status and recovery."""
    check = f"Verify errdisable status for interface {iface}"

    commands = [
        "show interface {iface}",
        "show errdisable recovery",
        "show errdisable detect",
    ]

    citations = [
        RFCSectionRef(
            rfc=8021,
            section="1",
            title="Cisco IOS Interface Configuration Guide",
            url="https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/interface/configuration/xe-3s/ir-xe-3s-book/ir-err-disable.html",
        )
    ]

    return PlayResultStep(
        rule_id="check_errdisable",
        check=check,
        result=f"Check errdisable status for interface {iface}",
        fix="Recover interface from errdisable state",
        verify="Interface should not be in errdisable state",
        commands=commands,
        citations=citations,
    )


def arp_entry_lookup(ip: str, vlan: str = None) -> PlayResultStep:
    """Check ARP entry lookup for specific IP."""
    check = f"Verify ARP entry for IP {ip}"
    if vlan:
        check += f" in VLAN {vlan}"

    commands = [
        "show arp {ip}",
        "show ip arp {ip}",
    ]
    if vlan:
        commands.append("show ip arp vlan {vlan}")

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_arp_entry",
        check=check,
        result=f"Check ARP entry for IP {ip}",
        fix=None,
        verify="ARP entry should be complete and not duplicate",
        commands=commands,
        citations=citations,
    )


def arp_table_health(vlan: str = None) -> PlayResultStep:
    """Check ARP table health and DAI counters."""
    check = "Verify ARP table health"
    if vlan:
        check += f" for VLAN {vlan}"

    commands = [
        "show ip arp inspection",
        "show ip arp inspection vlan {vlan}",
        "show arp inspection statistics",
    ]

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_arp_health",
        check=check,
        result="Check ARP table health and DAI counters",
        fix=None,
        verify="No excessive ARP drops or anomalies",
        commands=commands,
        citations=citations,
    )


def proxy_arp_config(iface_or_svi: str) -> PlayResultStep:
    """Check proxy ARP configuration."""
    check = f"Verify proxy ARP configuration for {iface_or_svi}"

    commands = [
        "show running-config | include proxy-arp",
        "show configuration | display set | match proxy-arp",
    ]

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_proxy_arp",
        check=check,
        result=f"Check proxy ARP configuration for {iface_or_svi}",
        fix="Configure proxy ARP if required",
        verify="Proxy ARP should be consistently configured",
        commands=commands,
        citations=citations,
    )


def mac_table_lookup(mac_or_ip: str, vlan: str = None) -> PlayResultStep:
    """Check MAC table lookup for MAC or IP."""
    check = f"Verify MAC table entry for {mac_or_ip}"
    if vlan:
        check += f" in VLAN {vlan}"

    commands = [
        "show mac address-table | include {mac_or_ip}",
        "show ethernet-switching table",
    ]
    if vlan:
        commands.append("show mac address-table vlan {vlan}")

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_mac_table",
        check=check,
        result=f"Check MAC table entry for {mac_or_ip}",
        fix=None,
        verify="MAC entry should exist and be consistent with ARP",
        commands=commands,
        citations=citations,
    )


def arp_aging_timers(vlan: str = None) -> PlayResultStep:
    """Check ARP aging timers configuration."""
    check = "Verify ARP aging timers"
    if vlan:
        check += f" for VLAN {vlan}"

    commands = [
        "show running-config | include arp timeout",
        "show configuration | display set | match arp aging",
    ]

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_arp_timers",
        check=check,
        result="Check ARP aging timers configuration",
        fix="Configure consistent ARP aging timers",
        verify="ARP aging timers should be aligned",
        commands=commands,
        citations=citations,
    )


def arp_gratuitous_signals(vlan: str = None) -> PlayResultStep:
    """Check gratuitous ARP signals."""
    check = "Verify gratuitous ARP signals"
    if vlan:
        check += f" for VLAN {vlan}"

    commands = [
        "show arp inspection statistics",
        "show ip arp inspection",
    ]

    citations = [
        RFCSectionRef(
            rfc=5227,
            section="1",
            title="IPv4 Address Conflict Detection",
            url="https://tools.ietf.org/html/rfc5227",
        )
    ]

    return PlayResultStep(
        rule_id="check_gratuitous_arp",
        check=check,
        result="Check gratuitous ARP signals and probes",
        fix="Configure gratuitous ARP if required",
        verify="Gratuitous ARP should be properly configured",
        commands=commands,
        citations=citations,
    )


def port_security_counters(iface: str) -> PlayResultStep:
    """Check port security counters."""
    check = f"Verify port security counters for interface {iface}"

    commands = [
        "show port-security interface {iface}",
        "show port-security",
    ]

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_port_security",
        check=check,
        result=f"Check port security counters for {iface}",
        fix="Clear port security violations if needed",
        verify="No excessive port security violations",
        commands=commands,
        citations=citations,
    )


def svi_status(vlan: str) -> PlayResultStep:
    """Check SVI status for VLAN."""
    check = f"Verify SVI status for VLAN {vlan}"

    commands = [
        "show ip interface vlan {vlan}",
        "show interfaces vlan.{vlan} terse",
    ]

    citations = [
        RFCSectionRef(
            rfc=826,
            section="1",
            title="An Ethernet Address Resolution Protocol",
            url="https://tools.ietf.org/html/rfc826",
        )
    ]

    return PlayResultStep(
        rule_id="check_svi_status",
        check=check,
        result=f"Check SVI status for VLAN {vlan}",
        fix="Enable SVI if down",
        verify="SVI should be up/up",
        commands=commands,
        citations=citations,
    )
