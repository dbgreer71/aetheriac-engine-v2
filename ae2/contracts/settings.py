"""
Configuration settings for AE v2.

This module defines the application settings using Pydantic Settings,
providing environment-based configuration with validation and type safety.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = "Aetheriac Engine v2"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Data directories
    base_dir: Path = Field(default=Path.cwd(), description="Base directory")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    index_dir: Path = Field(default=Path("data/index"), description="Index directory")
    rfc_dir: Path = Field(default=Path("data/rfc_index"), description="RFC directory")
    concepts_dir: Path = Field(
        default=Path("data/concepts"), description="Concepts directory"
    )
    playbooks_dir: Path = Field(
        default=Path("data/playbooks"), description="Playbooks directory"
    )

    # Feature flags
    enable_rfc: bool = Field(default=True, description="Enable RFC processing")
    strict_definitions: bool = Field(default=True, description="Strict definition mode")
    enable_playbooks: bool = Field(default=False, description="Enable playbooks")
    enable_lab: bool = Field(default=False, description="Enable lab integration")

    # Model settings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model to use",
    )
    max_sequence_length: int = Field(default=512, description="Maximum sequence length")

    # Index settings
    dense_index_type: str = Field(default="faiss", description="Dense index type")
    bm25_k1: float = Field(default=1.2, description="BM25 k1 parameter")
    bm25_b: float = Field(default=0.75, description="BM25 b parameter")
    hybrid_weight: float = Field(default=0.7, description="Weight for hybrid ranking")

    # RFC settings
    rfc_mirror_url: str = Field(
        default="https://www.rfc-editor.org/rfc/", description="RFC mirror URL"
    )
    rfc_sync_interval_hours: int = Field(default=24, description="RFC sync interval")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # Security
    secret_key: str = Field(default="", description="Secret key for JWT")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiry")

    # Lab settings (optional)
    lab_topology_dir: Optional[Path] = Field(None, description="Lab topology directory")
    lab_artifact_dir: Optional[Path] = Field(None, description="Lab artifact directory")

    @validator(
        "base_dir", "data_dir", "index_dir", "rfc_dir", "concepts_dir", "playbooks_dir"
    )
    def resolve_paths(cls, v: Path) -> Path:
        """Resolve relative paths to absolute paths."""
        if not v.is_absolute():
            v = Path.cwd() / v
        return v.resolve()

    @validator("secret_key")
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is set in production."""
        if not v and not (
            os.getenv("DEBUG", "false").lower() == "true"
            or os.getenv("ENVIRONMENT", "development") == "development"
        ):
            raise ValueError("Secret key must be set in production")
        return v

    @property
    def index_path(self) -> Path:
        """Get the full path to the index directory."""
        return self.base_dir / self.index_dir

    @property
    def rfc_path(self) -> Path:
        """Get the full path to the RFC directory."""
        return self.base_dir / self.rfc_dir

    @property
    def concepts_path(self) -> Path:
        """Get the full path to the concepts directory."""
        return self.base_dir / self.concepts_dir

    @property
    def playbooks_path(self) -> Path:
        """Get the full path to the playbooks directory."""
        return self.base_dir / self.playbooks_dir

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.data_dir,
            self.index_dir,
            self.rfc_dir,
            self.concepts_dir,
            self.playbooks_dir,
        ]

        if self.enable_lab and self.lab_topology_dir:
            directories.append(self.lab_topology_dir)
        if self.enable_lab and self.lab_artifact_dir:
            directories.append(self.lab_artifact_dir)

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_current_time():
        """Get current time for timestamps."""
        from datetime import datetime

        return datetime.utcnow()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
