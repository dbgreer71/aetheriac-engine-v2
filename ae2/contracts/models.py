"""
Core data contracts for AE v2.

This module defines the Pydantic models that establish the data contracts
for all components in the Aetheriac Engine v2 system. These models ensure
type safety, validation, and consistent data structures across the entire
system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, validator


class EvidenceType(str, Enum):
    """Types of evidence that can be cited."""

    RFC_SECTION = "rfc_section"
    LAB_CASE = "lab_case"
    VENDOR_DOC = "vendor_doc"
    CONFIG_SNIPPET = "config_snippet"
    LOG_ENTRY = "log_entry"


class QueryType(str, Enum):
    """Types of queries the system can handle."""

    DEFINITION = "definition"
    CONCEPT = "concept"
    TROUBLESHOOTING = "troubleshooting"


class VendorType(str, Enum):
    """Supported network vendor types."""

    CISCO_IOS_XE = "cisco_ios_xe"
    CISCO_IOS_XR = "cisco_ios_xr"
    CISCO_NX_OS = "cisco_nx_os"
    JUNIPER_JUNOS = "juniper_junos"
    ARISTA_EOS = "arista_eos"
    NOKIA_SROS = "nokia_sros"


class RFCSection(BaseModel):
    """Represents a section from an RFC document."""

    rfc_number: int = Field(..., description="RFC number")
    section: str = Field(..., description="Section identifier (e.g., '1.1', '2.3.4')")
    title: str = Field(..., description="Section title")
    excerpt: str = Field(..., description="Text excerpt from the section")
    url: str = Field(..., description="URL to the RFC section")
    hash: str = Field(..., description="SHA256 hash of normalized text")
    built_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this section was built"
    )

    @computed_field
    @property
    def id(self) -> str:
        """Generate a unique identifier for this RFC section."""
        return f"rfc:{self.rfc_number}:{self.section}:{self.hash[:8]}"

    @validator("hash")
    def validate_hash(cls, v: str) -> str:
        """Validate that hash is a valid SHA256 hash."""
        if not v or len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Hash must be a valid SHA256 hash (64 hex characters)")
        return v.lower()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Evidence(BaseModel):
    """Represents evidence supporting a claim or definition."""

    type: EvidenceType = Field(..., description="Type of evidence")
    path_or_url: str = Field(..., description="Path to evidence or URL")
    sha256: str = Field(..., description="SHA256 hash of evidence content")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from evidence")

    @validator("sha256")
    def validate_sha256(cls, v: str) -> str:
        """Validate that sha256 is a valid SHA256 hash."""
        if not v or len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("SHA256 must be 64 hex characters")
        return v.lower()


class Claim(BaseModel):
    """Represents a claim about a concept."""

    text: str = Field(..., description="The claim text")
    evidence: List[Evidence] = Field(
        default_factory=list, description="Supporting evidence"
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score (0-1)")


class Definition(BaseModel):
    """Represents a definition of a concept."""

    text: str = Field(..., description="Definition text")
    rfc_number: int = Field(..., description="RFC number where definition appears")
    section: str = Field(..., description="Section where definition appears")
    url: str = Field(..., description="URL to the definition")
    evidence: List[Evidence] = Field(
        default_factory=list, description="Supporting evidence"
    )


class ConceptCard(BaseModel):
    """Represents a concept card with definition and claims."""

    id: str = Field(
        ..., description="Unique concept identifier (e.g., 'concept:arp:v1')"
    )
    definition: Definition = Field(..., description="Primary definition")
    claims: List[Claim] = Field(
        default_factory=list, description="Claims about the concept"
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Provenance information"
    )
    built_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this card was built"
    )

    @validator("id")
    def validate_id(cls, v: str) -> str:
        """Validate concept ID format."""
        if not v or ":" not in v:
            raise ValueError("Concept ID must contain at least one colon")
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Artifact(BaseModel):
    """Represents an artifact from a lab case."""

    name: str = Field(..., description="Artifact name")
    path: str = Field(..., description="Path to artifact file")
    sha256: str = Field(..., description="SHA256 hash of artifact")
    artifact_type: str = Field(
        ..., description="Type of artifact (config, log, capture, etc.)"
    )

    @validator("sha256")
    def validate_sha256(cls, v: str) -> str:
        """Validate that sha256 is a valid SHA256 hash."""
        if not v or len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("SHA256 must be 64 hex characters")
        return v.lower()


class Case(BaseModel):
    """Represents a single lab fault instance."""

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique case identifier"
    )
    symptoms: List[str] = Field(..., description="List of symptoms observed")
    observations: List[str] = Field(..., description="Technical observations")
    root_cause: str = Field(..., description="Identified root cause")
    fix: str = Field(..., description="Applied fix")
    verify: str = Field(..., description="Verification steps")
    artifacts: List[Artifact] = Field(
        default_factory=list, description="Associated artifacts"
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Provenance information"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this case was created"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PlaybookRule(BaseModel):
    """Represents a rule in a playbook."""

    if_condition: str = Field(..., description="Condition that triggers this rule")
    then_check: List[str] = Field(..., description="Checks to perform")
    then_fix: List[str] = Field(..., description="Fixes to apply")
    verify: List[str] = Field(..., description="Verification steps")
    citations: List[str] = Field(
        default_factory=list, description="Citations to RFC sections or cases"
    )


class Playbook(BaseModel):
    """Represents a troubleshooting playbook."""

    id: str = Field(..., description="Unique playbook identifier")
    applies_to: List[str] = Field(
        ..., description="Protocols/technologies this applies to"
    )
    rules: List[PlaybookRule] = Field(..., description="Rules in this playbook")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this playbook was created"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class VendorCommandIR(BaseModel):
    """Intermediate representation for vendor commands."""

    intent: str = Field(..., description="Command intent")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )
    vendor: VendorType = Field(..., description="Target vendor")

    def render(self) -> List[str]:
        """Render the command for the specified vendor."""
        # This will be implemented by vendor-specific renderers
        raise NotImplementedError("Vendor-specific rendering not implemented")

    class Config:
        use_enum_values = True


class Query(BaseModel):
    """Represents a query to the system."""

    text: str = Field(..., description="Query text")
    query_type: QueryType = Field(..., description="Type of query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    class Config:
        use_enum_values = True


class QueryResponse(BaseModel):
    """Represents a response to a query."""

    query_id: str = Field(..., description="Query identifier")
    response_type: QueryType = Field(..., description="Type of response")
    content: Dict[str, Any] = Field(..., description="Response content")
    citations: List[str] = Field(default_factory=list, description="Citations")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When response was created"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        use_enum_values = True


class IndexManifest(BaseModel):
    """Manifest for an index with metadata and hashes."""

    index_id: str = Field(..., description="Index identifier")
    index_type: str = Field(..., description="Type of index (dense, bm25, hybrid)")
    document_count: int = Field(..., description="Number of documents in index")
    created_at: datetime = Field(..., description="When index was created")
    embeddings_hash: str = Field(..., description="Hash of embeddings")
    metadata_hash: str = Field(..., description="Hash of metadata")
    version: str = Field(..., description="Index version")

    @validator("embeddings_hash", "metadata_hash")
    def validate_hash(cls, v: str) -> str:
        """Validate that hash is a valid SHA256 hash."""
        if not v or len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Hash must be a valid SHA256 hash (64 hex characters)")
        return v.lower()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
