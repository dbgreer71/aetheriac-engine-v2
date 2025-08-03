"""
Playbook models for AE v2 troubleshooting system.

This module defines the Pydantic models for the playbook system, including
rules, contexts, and results for deterministic troubleshooting workflows.
"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class RFCSectionRef(BaseModel):
    """Reference to an RFC section with metadata."""

    rfc: int = Field(..., description="RFC number")
    section: str = Field(..., description="Section identifier (e.g., '1.1', '2.3.4')")
    title: str = Field(..., description="Section title")
    url: str = Field(..., description="URL to the RFC section")


class Rule(BaseModel):
    """A rule in a troubleshooting playbook."""

    id: str = Field(..., description="Unique rule identifier")
    if_: str = Field(..., description="Condition that triggers this rule")
    then_check: str = Field(..., description="Check to perform when condition is met")
    then_fix: Optional[str] = Field(None, description="Optional fix to apply")
    verify: Optional[str] = Field(None, description="Optional verification step")
    citations: List[RFCSectionRef] = Field(
        default_factory=list, description="RFC citations for this rule"
    )


class Playbook(BaseModel):
    """A troubleshooting playbook with ordered rules."""

    id: str = Field(..., description="Unique playbook identifier")
    applies_to: List[str] = Field(
        ..., description="Protocols/technologies this applies to"
    )
    rules: List[Rule] = Field(..., description="Ordered list of rules to execute")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this playbook was created"
    )


class PlayContext(BaseModel):
    """Context for executing a playbook."""

    vendor: Literal["iosxe", "junos", "nxos", "eos"] = Field(
        ..., description="Target vendor"
    )
    iface: str = Field(..., description="Interface name")
    area: Optional[str] = Field(None, description="OSPF area ID")
    auth: Optional[str] = Field(None, description="Authentication type")
    mtu: Optional[int] = Field(None, description="Interface MTU")


class PlayResultStep(BaseModel):
    """Result of executing a single rule step."""

    rule_id: str = Field(..., description="ID of the rule that was executed")
    check: str = Field(..., description="Check that was performed")
    result: str = Field(..., description="Result of the check")
    fix: Optional[str] = Field(None, description="Optional fix that was applied")
    verify: Optional[str] = Field(None, description="Optional verification step")
    commands: List[str] = Field(
        default_factory=list, description="Vendor-specific commands to execute"
    )
    citations: List[RFCSectionRef] = Field(
        default_factory=list, description="RFC citations for this step"
    )


class PlayResult(BaseModel):
    """Result of executing a complete playbook."""

    playbook_id: str = Field(..., description="ID of the playbook that was executed")
    steps: List[PlayResultStep] = Field(
        ..., description="Ordered list of executed steps"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this result was created"
    )
