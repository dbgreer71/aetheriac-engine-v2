"""
Cisco IOS-XE command renderer for OSPF troubleshooting.

This module provides vendor-specific command rendering for Cisco IOS-XE devices.
All commands are read-only show commands for troubleshooting purposes.
"""

from typing import Dict, List, Any
from .models import VendorCommandIR


def render_iosxe_command(intent: str, params: Dict[str, Any]) -> List[str]:
    """Render a command intent into IOS-XE specific commands."""
    cmd_ir = VendorCommandIR(intent=intent, params=params)
    return cmd_ir.render("iosxe")


# Command intent mappings for IOS-XE
IOSXE_COMMANDS = {
    "show_neighbors": "show ip ospf neighbor",
    "show_iface": "show interface {iface}",
    "show_ospf_iface": "show ip ospf interface {iface}",
    "show_mtu": "show interface {iface} | include MTU",
    "show_auth": "show ip ospf interface {iface} | include Authentication",
    "show_ospf_process": "show ip ospf",
    "show_ospf_database": "show ip ospf database",
    "show_ospf_events": "show ip ospf events",
    "show_ospf_statistics": "show ip ospf statistics",
}


def get_iosxe_command(intent: str, **params) -> str:
    """Get a formatted IOS-XE command string."""
    if intent not in IOSXE_COMMANDS:
        return f"# Unknown intent: {intent}"

    cmd_template = IOSXE_COMMANDS[intent]
    return cmd_template.format(**params)
