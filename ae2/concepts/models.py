"""
Concept Card models for AE v2.

This module defines the data structures for concept cards, which provide
structured knowledge about network concepts with evidence and provenance.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Evidence supporting a claim in a concept card."""

    type: str = Field(description="Type of evidence: 'rfc' or 'artifact'")
    url_or_path: str = Field(description="URL or file path to the evidence")
    sha256: str = Field(description="SHA256 hash of the evidence content")
    length: Optional[int] = Field(
        default=None, description="Length of the evidence excerpt"
    )
    source: Optional[dict] = Field(
        default=None, description="Source metadata for the evidence"
    )


class Claim(BaseModel):
    """A claim about a concept with supporting evidence."""

    text: str = Field(description="The claim text")
    evidence: List[Evidence] = Field(
        default_factory=list, description="Supporting evidence"
    )


class Definition(BaseModel):
    """Definition of a concept from an RFC."""

    text: str = Field(description="Definition text")
    rfc_number: int = Field(description="RFC number")
    section: str = Field(description="RFC section")
    url: str = Field(description="URL to the RFC section")


class Provenance(BaseModel):
    """Provenance information for a concept card."""

    built_at: datetime = Field(description="When the card was built")
    index_root_hash: Optional[str] = Field(
        default=None, description="Root hash of the index used to compile this card"
    )


class ConceptCard(BaseModel):
    """A concept card containing structured knowledge about a network concept."""

    id: str = Field(description="Unique identifier, e.g., 'concept:arp:v1'")
    definition: Definition = Field(description="Primary definition of the concept")
    claims: List[Claim] = Field(
        default_factory=list, description="Claims about the concept"
    )
    provenance: Provenance = Field(description="Provenance information")
    related: List[str] = Field(
        default_factory=list,
        description="Slugs of related concepts this card references",
    )
    tags: List[str] = Field(
        default_factory=list, description="Free-form lowercase tags for categorization"
    )
