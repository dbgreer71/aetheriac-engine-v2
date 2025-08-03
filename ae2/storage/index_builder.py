"""
Index builder for loading and managing RFC sections.

This module handles loading RFC sections from storage and building
searchable indexes with content-addressed storage.
"""

import hashlib
import json
import logging
from typing import Dict, List

import orjson

from ..contracts.models import RFCSection, IndexManifest
from ..contracts.settings import settings

logger = logging.getLogger(__name__)


class IndexBuilder:
    """Builds and manages searchable indexes from RFC sections."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.index_builder")
        self.rfc_index_file = settings.rfc_dir / "rfc_index.jsonl"
        self.manifest_file = settings.rfc_dir / "manifest.json"
        self.index_dir = settings.index_dir

        # Ensure directories exist
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"Index builder initialized with RFC index: {self.rfc_index_file}"
        )

    def index_exists(self) -> bool:
        """Check if the index already exists."""
        return self.rfc_index_file.exists() and self.manifest_file.exists()

    async def build_index(self) -> None:
        """Build the index from RFC sections."""
        if self.index_exists():
            self.logger.info("Index already exists, skipping build")
            return

        self.logger.info("Building index from RFC sections")

        # For now, we'll create a simple index
        # In the future, this could trigger RFC sync if needed
        sections = self._load_rfc_sections()

        if not sections:
            self.logger.warning("No RFC sections found, creating empty index")
            self._create_empty_manifest()
            return

        # Create manifest
        self._create_manifest(sections)

        self.logger.info(f"Index built with {len(sections)} sections")

    def load_documents(self) -> List[RFCSection]:
        """Load RFC sections from the index."""
        if not self.index_exists():
            self.logger.warning("Index does not exist, returning empty list")
            return []

        sections = self._load_rfc_sections()
        self.logger.info(f"Loaded {len(sections)} RFC sections")
        return sections

    def _load_rfc_sections(self) -> List[RFCSection]:
        """Load RFC sections from the JSONL file."""
        sections = []

        if not self.rfc_index_file.exists():
            self.logger.warning(f"RFC index file not found: {self.rfc_index_file}")
            return sections

        try:
            with open(self.rfc_index_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Parse JSON line
                        data = orjson.loads(line)
                        section = RFCSection(**data)
                        sections.append(section)
                    except Exception as e:
                        self.logger.error(f"Failed to parse line {line_num}: {e}")
                        continue

            self.logger.debug(
                f"Successfully loaded {len(sections)} sections from {self.rfc_index_file}"
            )

        except Exception as e:
            self.logger.error(f"Failed to load RFC sections: {e}")
            return []

        return sections

    def _create_manifest(self, sections: List[RFCSection]) -> IndexManifest:
        """Create a manifest for the RFC sections."""
        # Calculate hashes
        section_hashes = [section.hash for section in sections]
        embeddings_hash = hashlib.sha256(
            json.dumps(section_hashes, sort_keys=True).encode("utf-8")
        ).hexdigest()

        # Create metadata hash
        metadata = {
            "rfc_numbers": sorted(
                list(set(section.rfc_number for section in sections))
            ),
            "total_sections": len(sections),
            "section_hashes": section_hashes,
        }
        metadata_hash = hashlib.sha256(
            json.dumps(metadata, sort_keys=True).encode("utf-8")
        ).hexdigest()

        manifest = IndexManifest(
            index_id=f"rfc_index_{int(hashlib.sha256(embeddings_hash.encode()).hexdigest()[:8], 16)}",
            index_type="hybrid",
            document_count=len(sections),
            created_at=settings.get_current_time(),
            embeddings_hash=embeddings_hash,
            metadata_hash=metadata_hash,
            version=settings.app_version,
        )

        # Save manifest
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest.dict(), f, indent=2, sort_keys=True)

        self.logger.info(f"Created manifest: {manifest.index_id}")
        return manifest

    def _create_empty_manifest(self) -> None:
        """Create an empty manifest when no sections exist."""
        manifest = IndexManifest(
            index_id="empty_index",
            index_type="hybrid",
            document_count=0,
            created_at=settings.get_current_time(),
            embeddings_hash=hashlib.sha256(b"").hexdigest(),
            metadata_hash=hashlib.sha256(b"").hexdigest(),
            version=settings.app_version,
        )

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest.dict(), f, indent=2, sort_keys=True)

        self.logger.info("Created empty manifest")

    def get_index_stats(self) -> Dict[str, any]:
        """Get statistics about the index."""
        if not self.index_exists():
            return {"error": "Index does not exist"}

        try:
            sections = self._load_rfc_sections()

            # Load manifest
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            return {
                "document_count": len(sections),
                "rfc_numbers": sorted(
                    list(set(section.rfc_number for section in sections))
                ),
                "manifest": manifest_data,
                "index_file_size": (
                    self.rfc_index_file.stat().st_size
                    if self.rfc_index_file.exists()
                    else 0
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

    def validate_index(self) -> bool:
        """Validate the index integrity."""
        if not self.index_exists():
            self.logger.warning("Index does not exist")
            return False

        try:
            sections = self._load_rfc_sections()

            # Load manifest
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            # Validate document count
            if len(sections) != manifest_data.get("document_count", 0):
                self.logger.error("Document count mismatch")
                return False

            # Validate section hashes
            section_hashes = [section.hash for section in sections]
            expected_hashes = manifest_data.get("section_hashes", [])

            if section_hashes != expected_hashes:
                self.logger.error("Section hashes mismatch")
                return False

            self.logger.info("Index validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Index validation failed: {e}")
            return False


def main():
    """Main entry point for index building."""
    import asyncio

    async def build():
        builder = IndexBuilder()
        await builder.build_index()

        # Print stats
        stats = builder.get_index_stats()
        print(f"Index stats: {json.dumps(stats, indent=2)}")

        # Validate
        is_valid = builder.validate_index()
        print(f"Index validation: {'PASSED' if is_valid else 'FAILED'}")

    asyncio.run(build())


if __name__ == "__main__":
    main()
