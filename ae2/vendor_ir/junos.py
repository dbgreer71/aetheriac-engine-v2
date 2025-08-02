"""
Juniper Junos command renderer for OSPF troubleshooting.

This module provides vendor-specific command rendering for Juniper Junos devices.
All commands are read-only show commands for troubleshooting purposes.
"""

from typing import Dict, List, Any
from .models import VendorCommandIR


def render_junos_command(intent: str, params: Dict[str, Any]) -> List[str]:
    """Render a command intent into Junos specific commands."""
    cmd_ir = VendorCommandIR(intent=intent, params=params)
    return cmd_ir.render("junos")


# Command intent mappings for Junos
JUNOS_COMMANDS = {
    "show_neighbors": "show ospf neighbor",
    "show_iface": "show interfaces {iface} terse",
    "show_ospf_iface": "show ospf interface {iface} detail",
    "show_mtu": "show interfaces {iface} | match MTU",
    "show_auth": "show ospf interface {iface} detail | match Authentication",
    "show_ospf_process": "show ospf overview",
    "show_ospf_database": "show ospf database",
    "show_ospf_events": "show ospf events",
    "show_ospf_statistics": "show ospf statistics",
}


def get_junos_command(intent: str, **params) -> str:
    """Get a formatted Junos command string."""
    if intent not in JUNOS_COMMANDS:
        return f"# Unknown intent: {intent}"

    cmd_template = JUNOS_COMMANDS[intent]
    return cmd_template.format(**params)
