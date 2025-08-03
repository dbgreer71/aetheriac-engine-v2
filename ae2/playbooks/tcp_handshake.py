"""
TCP Handshake Failure Playbook

This playbook provides deterministic troubleshooting steps for TCP handshake failures
with 8 rules in fixed order, backed by RFC references.
"""

import logging

from .models import PlayContext, PlayResult, PlayResultStep, Citation

logger = logging.getLogger(__name__)


def run_tcp_handshake_playbook(ctx: PlayContext, store) -> PlayResult:
    """
    Run TCP handshake failure troubleshooting playbook.

    Args:
        ctx: PlayContext with vendor, src, dst, dport
        store: Index store for RFC lookups

    Returns:
        PlayResult with 8 deterministic steps
    """
    logger.info(f"Running TCP handshake playbook for {ctx.vendor}")

    # Extract context
    vendor = ctx.vendor or "iosxe"
    src = ctx.src or "192.0.2.1"  # Default source
    dst = ctx.dst or "203.0.113.10"  # Default destination
    dport = ctx.dport or "443"  # Default port

    steps = []

    # Rule 1: Reachability/ARP/ND (ICMP reachability & ARP/ND cache) — RFC 1122
    steps.append(
        PlayResultStep(
            check=f"Check reachability to {dst}",
            commands=[
                f"ping {dst}",
                f"show arp {dst}",
                (
                    f"show ipv6 neighbors {dst}"
                    if vendor == "iosxe"
                    else f"show ipv6 neighbor {dst}"
                ),
            ],
            citations=[Citation(rfc="1122", section="3.2.2")],
        )
    )

    # Rule 2: L4 state listen/refuse (server listening on port; "connection refused" vs timeout) — RFC 793
    steps.append(
        PlayResultStep(
            check=f"Check if destination {dst}:{dport} is listening",
            commands=[
                f"telnet {dst} {dport}",
                (
                    "show tcp brief all"
                    if vendor == "iosxe"
                    else "show system connections"
                ),
                (
                    "show control-plane host open-ports"
                    if vendor == "iosxe"
                    else "show system services"
                ),
            ],
            citations=[Citation(rfc="793", section="3.4")],
        )
    )

    # Rule 3: SYN flow seen (counters/pcap ring; IOS-XE show ip tcp connection, Junos show security flow session) — RFC 793
    steps.append(
        PlayResultStep(
            check=f"Check if SYN packets are being sent to {dst}:{dport}",
            commands=[
                (
                    "show ip tcp connection"
                    if vendor == "iosxe"
                    else "show system connections"
                ),
                (
                    "show security flow session"
                    if vendor == "junos"
                    else "show ip tcp statistics"
                ),
                "show ip traffic",
            ],
            citations=[Citation(rfc="793", section="3.1")],
        )
    )

    # Rule 4: SYN-ACK seen? (reverse path ACL/NAT) — RFC 1812 / NAT refs, RFC 3022
    steps.append(
        PlayResultStep(
            check=f"Check if SYN-ACK is received from {dst}:{dport}",
            commands=[
                "show ip access-list",
                (
                    "show ip nat translations"
                    if vendor == "iosxe"
                    else "show security nat translations"
                ),
                f"show ip route {dst}",
                (
                    f"show ip cef {dst} detail"
                    if vendor == "iosxe"
                    else f"show route {dst} detail"
                ),
            ],
            citations=[
                Citation(rfc="1812", section="5.3.4"),
                Citation(rfc="3022", section="2.2"),
            ],
        )
    )

    # Rule 5: RST storms (middlebox reset) — RFC 793
    steps.append(
        PlayResultStep(
            check=f"Check for RST packets from {dst}:{dport}",
            commands=[
                "show ip tcp connection",
                "show ip traffic | include RST",
                "show logging | include RST",
            ],
            citations=[Citation(rfc="793", section="3.4")],
        )
    )

    # Rule 6: MSS/PMTUD blackhole (DF bit path; MSS clamp) — RFC 879, RFC 1191
    steps.append(
        PlayResultStep(
            check=f"Check MSS/PMTUD issues to {dst}",
            commands=[
                "show ip mtu",
                "show interfaces | include MTU",
                (
                    "show policy-map interface"
                    if vendor == "iosxe"
                    else "show interfaces extensive"
                ),
                f"ping {dst} size 1500 df-bit",
            ],
            citations=[
                Citation(rfc="879", section="3.1"),
                Citation(rfc="1191", section="4"),
            ],
        )
    )

    # Rule 7: Firewall/Policy (zone/policy drops) — vendor docs; cite RFC 2979 (FW transparency) as generic
    steps.append(
        PlayResultStep(
            check=f"Check firewall/policy drops for {dst}:{dport}",
            commands=[
                (
                    "show policy-map interface"
                    if vendor == "iosxe"
                    else "show security policies hit-count"
                ),
                f"show ip access-list | include {dst}",
                "show logging | include DENY",
            ],
            citations=[Citation(rfc="2979", section="2.1")],
        )
    )

    # Rule 8: Interface/Errors (drops, CRC, input errors) — ops hygiene
    steps.append(
        PlayResultStep(
            check=f"Check interface errors on path to {dst}",
            commands=[
                "show interfaces counters errors",
                "show interfaces | include errors",
                "show ip interface brief",
            ],
            citations=[Citation(rfc="1122", section="3.2.2")],
        )
    )

    return PlayResult(
        playbook_id="tcp-handshake",
        steps=steps,
        vendor=vendor,
        context={
            "src": src,
            "dst": dst,
            "dport": dport,
        },
    )


def get_tcp_handshake_explanation() -> str:
    """Get explanation for TCP handshake playbook."""
    return """
    TCP Handshake Failure Troubleshooting

    This playbook follows a systematic approach to diagnose TCP handshake failures:

    1. **Reachability**: Verify basic IP connectivity and ARP/ND resolution
    2. **L4 State**: Check if the destination port is listening or refusing connections
    3. **SYN Flow**: Verify SYN packets are being sent and tracked
    4. **SYN-ACK**: Check for reverse path issues, ACLs, and NAT
    5. **RST Storms**: Identify middlebox interference or policy blocks
    6. **MSS/PMTUD**: Detect path MTU discovery issues and MSS clamping
    7. **Firewall/Policy**: Check for security policy drops
    8. **Interface Errors**: Verify physical layer and interface health

    Each step is backed by relevant RFC specifications and vendor-specific commands.
    """
