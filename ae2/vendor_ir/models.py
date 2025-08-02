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
        else:
            return [f"# Unknown intent: {self.intent}"]
