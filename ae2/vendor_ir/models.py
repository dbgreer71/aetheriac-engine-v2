"""
Vendor command intermediate representation models.

This module defines the models for vendor-agnostic command intents that can
be rendered into vendor-specific CLI commands.
"""

from typing import Dict, List, Any, Literal
from pydantic import BaseModel, Field


class VendorCommandIR(BaseModel):
    """Intermediate representation for vendor commands."""

    intent: str = Field(
        ..., description="Command intent (e.g., 'show_neighbors', 'show_iface')"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )

    def render(self, vendor: Literal["iosxe", "junos"]) -> List[str]:
        """Render this command intent into vendor-specific CLI commands."""
        if vendor == "iosxe":
            return self._render_iosxe()
        elif vendor == "junos":
            return self._render_junos()
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")

    def _render_iosxe(self) -> List[str]:
        """Render commands for Cisco IOS-XE."""
        if self.intent == "show_neighbors":
            return ["show ip ospf neighbor"]
        elif self.intent == "show_iface":
            iface = self.params.get("iface", "")
            return [f"show interface {iface}"]
        elif self.intent == "show_ospf_iface":
            iface = self.params.get("iface", "")
            return [f"show ip ospf interface {iface}"]
        elif self.intent == "show_mtu":
            iface = self.params.get("iface", "")
            return [f"show interface {iface} | include MTU"]
        elif self.intent == "show_auth":
            iface = self.params.get("iface", "")
            return [f"show ip ospf interface {iface} | include Authentication"]
        # BGP commands
        elif self.intent == "show_bgp_summary":
            return ["show ip bgp summary"]
        elif self.intent == "show_bgp_neighbor":
            peer = self.params.get("peer", "")
            return [
                f"show ip bgp neighbors {peer}" if peer else "show ip bgp neighbors"
            ]
        elif self.intent == "show_bgp_config":
            return ["show running-config | section ^router bgp"]
        elif self.intent == "show_bgp_neighbor_detail":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show ip bgp neighbors {peer} detail"
                    if peer
                    else "show ip bgp neighbors detail"
                )
            ]
        elif self.intent == "show_bgp_cef":
            peer = self.params.get("peer", "")
            return [f"show ip cef {peer}" if peer else "show ip cef"]
        elif self.intent == "show_tcp_brief":
            return ["show tcp brief all"]
        elif self.intent == "show_key_chain":
            return ["show key chain"]
        elif self.intent == "show_interface":
            iface = self.params.get("iface", "")
            return [f"show interface {iface}" if iface else "show interface"]
        elif self.intent == "show_bgp_timers":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show ip bgp neighbors {peer} | include timers"
                    if peer
                    else "show ip bgp neighbors | include timers"
                )
            ]
        elif self.intent == "show_bgp_route_maps":
            return ["show route-map"]
        elif self.intent == "show_bgp_afi_safi":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show ip bgp neighbors {peer} | include Address-family"
                    if peer
                    else "show ip bgp neighbors | include Address-family"
                )
            ]
        elif self.intent == "show_control_plane":
            return ["show control-plane host open-ports"]
        elif self.intent == "show_access_lists":
            return ["show access-lists"]
        elif self.intent == "show_cpu":
            return ["show processes cpu sorted | ex 0.00"]
        elif self.intent == "show_platform_drops":
            return ["show platform hardware qfp active statistics drop"]
        elif self.intent == "show_bgp_dampening":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show ip bgp flap-statistics {peer}"
                    if peer
                    else "show ip bgp flap-statistics"
                )
            ]
        else:
            return [f"# Unknown intent: {self.intent}"]

    def _render_junos(self) -> List[str]:
        """Render commands for Juniper Junos."""
        if self.intent == "show_neighbors":
            return ["show ospf neighbor"]
        elif self.intent == "show_iface":
            iface = self.params.get("iface", "")
            return [f"show interfaces {iface} terse"]
        elif self.intent == "show_ospf_iface":
            iface = self.params.get("iface", "")
            return [f"show ospf interface {iface} detail"]
        elif self.intent == "show_mtu":
            iface = self.params.get("iface", "")
            return [f"show interfaces {iface} | match MTU"]
        elif self.intent == "show_auth":
            iface = self.params.get("iface", "")
            return [f"show ospf interface {iface} detail | match Authentication"]
        # BGP commands
        elif self.intent == "show_bgp_summary":
            return ["show bgp summary"]
        elif self.intent == "show_bgp_neighbor":
            peer = self.params.get("peer", "")
            return [f"show bgp neighbor {peer}" if peer else "show bgp neighbor"]
        elif self.intent == "show_bgp_config":
            return ["show configuration protocols bgp | display set"]
        elif self.intent == "show_bgp_neighbor_detail":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show bgp neighbor {peer} detail"
                    if peer
                    else "show bgp neighbor detail"
                )
            ]
        elif self.intent == "show_tcp_brief":
            return ["show system connections | match 179"]
        elif self.intent == "show_key_chain":
            return ["show security authentication-key-chains"]
        elif self.intent == "show_interface":
            iface = self.params.get("iface", "")
            return [
                f"show interfaces {iface} terse" if iface else "show interfaces terse"
            ]
        elif self.intent == "show_bgp_timers":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show bgp neighbor {peer} | match timers"
                    if peer
                    else "show bgp neighbor | match timers"
                )
            ]
        elif self.intent == "show_bgp_route_maps":
            return ["show policy-options"]
        elif self.intent == "show_bgp_afi_safi":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show bgp neighbor {peer} | match family"
                    if peer
                    else "show bgp neighbor | match family"
                )
            ]
        elif self.intent == "show_system_connections":
            return ["show system connections | match 179"]
        elif self.intent == "show_cpu":
            return ["show system processes extensive | match bgp"]
        elif self.intent == "show_platform_drops":
            return ["show interfaces extensive | match drops"]
        elif self.intent == "show_bgp_dampening":
            peer = self.params.get("peer", "")
            return [
                (
                    f"show bgp neighbor {peer} | match dampening"
                    if peer
                    else "show bgp neighbor | match dampening"
                )
            ]
        elif self.intent == "show_firewall":
            return ["show firewall"]
        elif self.intent == "show_interfaces_terse":
            iface = self.params.get("iface", "")
            return [
                (
                    f"show interfaces terse | match {iface}"
                    if iface
                    else "show interfaces terse"
                )
            ]
        else:
            return [f"# Unknown intent: {self.intent}"]
