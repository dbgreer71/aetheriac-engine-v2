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

    def render(self, vendor: Literal["iosxe", "junos", "nxos", "eos"]) -> List[str]:
        """Render this command intent into vendor-specific CLI commands."""
        if vendor == "iosxe":
            return self._render_iosxe()
        elif vendor == "junos":
            return self._render_junos()
        elif vendor == "nxos":
            return self._render_nxos()
        elif vendor == "eos":
            return self._render_eos()
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
        # LACP commands
        elif self.intent == "show_lacp_neighbor":
            target = self.params.get("target", "")
            return [f"show lacp neighbor {target}"]
        elif self.intent == "show_lacp_interfaces":
            target = self.params.get("target", "")
            return [f"show lacp interfaces {target}"]
        elif self.intent == "show_etherchannel_summary":
            return ["show etherchannel summary"]
        elif self.intent == "show_port_channel":
            bundle = self.params.get("bundle", "")
            return [f"show interfaces {bundle}"]
        elif self.intent == "show_interface_switchport":
            target = self.params.get("target", "")
            return [f"show interface {target} switchport"]
        elif self.intent == "show_interfaces_trunk":
            return ["show interfaces trunk"]
        elif self.intent == "show_vlan":
            return ["show vlan"]
        elif self.intent == "show_spanning_tree_interface":
            target = self.params.get("target", "")
            return [f"show spanning-tree interface {target}"]
        elif self.intent == "show_spanning_tree":
            return ["show spanning-tree"]
        elif self.intent == "show_errdisable_recovery":
            return ["show errdisable recovery"]
        elif self.intent == "show_errdisable_detect":
            return ["show errdisable detect"]
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
        # LACP commands
        elif self.intent == "show_lacp_neighbor":
            target = self.params.get("target", "")
            return [f"show lacp interfaces {target}"]
        elif self.intent == "show_lacp_interfaces":
            target = self.params.get("target", "")
            return [f"show lacp interfaces {target}"]
        elif self.intent == "show_etherchannel_summary":
            return ["show lacp interfaces"]
        elif self.intent == "show_port_channel":
            bundle = self.params.get("bundle", "")
            return [f"show interfaces {bundle} extensive"]
        elif self.intent == "show_interface_switchport":
            target = self.params.get("target", "")
            return [f"show interfaces {target} detail"]
        elif self.intent == "show_interfaces_trunk":
            return ["show interfaces detail | match trunk"]
        elif self.intent == "show_vlan":
            return ["show vlans"]
        elif self.intent == "show_spanning_tree_interface":
            target = self.params.get("target", "")
            return [f"show spanning-tree interface {target}"]
        elif self.intent == "show_spanning_tree":
            return ["show spanning-tree"]
        elif self.intent == "show_errdisable_recovery":
            return ["show interfaces diagnostics optics"]
        elif self.intent == "show_errdisable_detect":
            return ["show interfaces diagnostics optics"]
        # ARP commands
        elif self.intent == "show_arp_table":
            ip = self.params.get("ip", "")
            vlan = self.params.get("vlan", "")
            if ip:
                return [f"show arp no-resolve | match {ip}"]
            elif vlan:
                return [f"show arp vlan {vlan}"]
            else:
                return ["show arp no-resolve"]
        elif self.intent == "show_dai_status":
            vlan = self.params.get("vlan", "")
            if vlan:
                return [f"show ip arp inspection vlan {vlan}"]
            else:
                return ["show ip arp inspection"]
        elif self.intent == "show_proxy_arp":
            return ["show configuration | display set | match proxy-arp"]
        elif self.intent == "show_mac_table":
            mac = self.params.get("mac", "")
            vlan = self.params.get("vlan", "")
            if mac and vlan:
                return [f"show ethernet-switching table | match {mac} vlan {vlan}"]
            elif mac:
                return [f"show ethernet-switching table | match {mac}"]
            elif vlan:
                return [f"show ethernet-switching table vlan {vlan}"]
            else:
                return ["show ethernet-switching table"]
        elif self.intent == "show_svi":
            vlan = self.params.get("vlan", "")
            return [f"show interfaces vlan.{vlan} terse"]
        elif self.intent == "show_arp_timers":
            return ["show configuration | display set | match arp aging"]
        elif self.intent == "show_port_security":
            iface = self.params.get("iface", "")
            return [f"show ethernet-switching interface {iface} detail"]
        else:
            return [f"# Unknown intent: {self.intent}"]

    def _render_nxos(self) -> List[str]:
        """Render commands for Cisco NX-OS."""
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
        # LACP commands
        elif self.intent == "show_lacp_neighbor":
            target = self.params.get("target", "")
            return [f"show lacp neighbor {target}"]
        elif self.intent == "show_lacp_interfaces":
            target = self.params.get("target", "")
            return [f"show lacp interfaces {target}"]
        elif self.intent == "show_etherchannel_summary":
            return ["show port-channel summary"]
        elif self.intent == "show_port_channel":
            bundle = self.params.get("bundle", "")
            return [f"show interface {bundle}"]
        elif self.intent == "show_interface_switchport":
            target = self.params.get("target", "")
            return [f"show interface {target} switchport"]
        elif self.intent == "show_interfaces_trunk":
            return ["show interface trunk"]
        elif self.intent == "show_vlan":
            return ["show vlan"]
        elif self.intent == "show_spanning_tree_interface":
            target = self.params.get("target", "")
            return [f"show spanning-tree interface {target}"]
        elif self.intent == "show_spanning_tree":
            return ["show spanning-tree"]
        elif self.intent == "show_errdisable_recovery":
            return ["show errdisable recovery"]
        elif self.intent == "show_errdisable_detect":
            return ["show errdisable detect"]
        else:
            return [f"# Unknown intent: {self.intent}"]

    def _render_eos(self) -> List[str]:
        """Render commands for Arista EOS."""
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
        # LACP commands
        elif self.intent == "show_lacp_neighbor":
            target = self.params.get("target", "")
            return [f"show lacp neighbor {target}"]
        elif self.intent == "show_lacp_interfaces":
            target = self.params.get("target", "")
            return [f"show lacp interfaces {target}"]
        elif self.intent == "show_etherchannel_summary":
            return ["show port-channel summary"]
        elif self.intent == "show_port_channel":
            bundle = self.params.get("bundle", "")
            return [f"show interface {bundle}"]
        elif self.intent == "show_interface_switchport":
            target = self.params.get("target", "")
            return [f"show interface {target} switchport"]
        elif self.intent == "show_interfaces_trunk":
            return ["show interface trunk"]
        elif self.intent == "show_vlan":
            return ["show vlan"]
        elif self.intent == "show_spanning_tree_interface":
            target = self.params.get("target", "")
            return [f"show spanning-tree interface {target}"]
        elif self.intent == "show_spanning_tree":
            return ["show spanning-tree"]
        elif self.intent == "show_errdisable_recovery":
            return ["show errdisable recovery"]
        elif self.intent == "show_errdisable_detect":
            return ["show errdisable detect"]
        else:
            return [f"# Unknown intent: {self.intent}"]
