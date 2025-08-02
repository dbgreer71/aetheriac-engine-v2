"""
Concept Card storage and manifest management.

This module handles persistence of concept cards to disk with manifest tracking.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import ConceptCard


class ConceptStore:
    """Storage for concept cards with manifest management."""

    def __init__(self, concepts_dir: Optional[Path] = None):
        """Initialize the concept store.

        Args:
            concepts_dir: Directory to store concept cards. Defaults to data/concepts/.
        """
        if concepts_dir is None:
            concepts_dir = Path("data/concepts")

        self.concepts_dir = Path(concepts_dir)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.concepts_dir / "concepts_manifest.json"
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load the manifest file, creating it if it doesn't exist."""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r") as f:
                data = json.load(f)
                # Handle both old format (with "concepts" key) and new format (direct array)
                if isinstance(data, dict) and "concepts" in data:
                    self.manifest = data["concepts"]
                else:
                    self.manifest = data if isinstance(data, list) else []
        else:
            self.manifest = []
            self._save_manifest()

    def _save_manifest(self) -> None:
        """Save the manifest file."""
        with open(self.manifest_path, "w") as f:
            json.dump(
                self.manifest, f, indent=2, separators=(",", ":"), ensure_ascii=True
            )

    def _compute_sha256(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_card_hash(self, card_dict: dict) -> str:
        """Compute SHA256 hash of card using deterministic JSON serialization."""
        card_json = json.dumps(
            card_dict,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            default=str,
        )
        return hashlib.sha256(card_json.encode("utf-8")).hexdigest()

    def _compute_root_hash(self) -> str:
        """Compute deterministic root hash from manifest SHA256 values."""
        if not self.manifest:
            return hashlib.sha256(b"").hexdigest()

        # Sort by id for deterministic ordering
        sorted_entries = sorted(self.manifest, key=lambda x: x["id"])

        # Concatenate SHA256 values
        concatenated = "".join(entry["sha256"] for entry in sorted_entries)

        return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

    def save(self, card: ConceptCard) -> Path:
        """Save a concept card to disk and update manifest.

        Args:
            card: The concept card to save

        Returns:
            Path to the saved file
        """
        # Extract slug from card ID (concept:arp:v1 -> arp)
        slug = card.id.split(":")[1] if ":" in card.id else card.id

        # Create the card file path using slug
        card_path = self.concepts_dir / f"{slug}.json"

        # Serialize the card with deterministic JSON
        card_dict = card.model_dump()
        card_json = json.dumps(
            card_dict,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            default=str,
        )

        # Compute SHA256 of the card content using deterministic method
        card_sha256 = self._compute_card_hash(card_dict)

        # Write the card file
        with open(card_path, "w") as f:
            f.write(card_json)

        # Update manifest
        manifest_entry = {
            "id": slug,
            "sha256": card_sha256,
            "bytes": len(card_json.encode("utf-8")),
            "built_at": card.provenance.built_at.isoformat(timespec="seconds"),
        }

        # Remove existing entry if it exists
        self.manifest = [entry for entry in self.manifest if entry["id"] != slug]

        # Add new entry
        self.manifest.append(manifest_entry)
        self._save_manifest()

        return card_path

    def load(self, card_id: str) -> ConceptCard:
        """Load a concept card by ID or slug.

        Args:
            card_id: The concept card ID or slug

        Returns:
            The loaded concept card

        Raises:
            FileNotFoundError: If the card doesn't exist
        """
        # Extract slug from card ID if it's a full concept ID
        if card_id.startswith("concept:") and ":" in card_id:
            slug = card_id.split(":")[1]
        else:
            slug = card_id

        # Try loading by slug first (for new API)
        slug_path = self.concepts_dir / f"{slug}.json"
        if slug_path.exists():
            with open(slug_path, "r") as f:
                card_dict = json.load(f)
            return ConceptCard(**card_dict)

        # Fallback to old ID-based loading (for backward compatibility)
        old_path = self.concepts_dir / f"{card_id}.json"
        if old_path.exists():
            with open(old_path, "r") as f:
                card_dict = json.load(f)
            return ConceptCard(**card_dict)

        raise FileNotFoundError(f"Concept card not found: {card_id}")

    def list_ids(self) -> List[str]:
        """List all concept card IDs.

        Returns:
            List of concept card IDs
        """
        return [entry["id"] for entry in self.manifest]

    def list_concepts(self) -> List[Dict]:
        """List all concepts with manifest data.

        Returns:
            List of concept entries with id, sha256, built_at
        """
        return sorted(self.manifest, key=lambda x: x["id"])

    def exists(self, card_id: str) -> bool:
        """Check if a concept card exists.

        Args:
            card_id: The concept card ID or slug

        Returns:
            True if the card exists, False otherwise
        """
        # Extract slug from card ID if it's a full concept ID
        if card_id.startswith("concept:") and ":" in card_id:
            slug = card_id.split(":")[1]
        else:
            slug = card_id

        # Check by slug first
        if (self.concepts_dir / f"{slug}.json").exists():
            return True

        # Fallback to old ID-based check
        return (self.concepts_dir / f"{card_id}.json").exists()

    def get_manifest(self) -> Dict:
        """Get the current manifest.

        Returns:
            The manifest dictionary
        """
        return self.manifest.copy()

    def get_root_hash(self) -> str:
        """Get the current root hash.

        Returns:
            The root hash string
        """
        return self._compute_root_hash()

    def delete_card(self, slug: str) -> bool:
        """Delete a concept card by slug.

        Args:
            slug: The concept slug to delete

        Returns:
            True if the card was deleted, False if it didn't exist
        """
        # Remove the file
        card_path = self.concepts_dir / f"{slug}.json"
        file_existed = card_path.exists()
        if file_existed:
            card_path.unlink()

        # Remove from manifest
        self.manifest = [entry for entry in self.manifest if entry["id"] != slug]
        self._save_manifest()

        return file_existed

    def gc_manifest(self) -> int:
        """Garbage collect manifest entries for missing files.

        Returns:
            Number of entries removed
        """
        original_count = len(self.manifest)

        # Keep only entries whose files exist
        self.manifest = [
            entry
            for entry in self.manifest
            if (self.concepts_dir / f"{entry['id']}.json").exists()
        ]

        removed_count = original_count - len(self.manifest)
        if removed_count > 0:
            self._save_manifest()

        return removed_count

    def list_concepts_with_stale(
        self, current_index_root_hash: Optional[str] = None
    ) -> List[Dict]:
        """List all concepts with manifest data and stale flag.

        Args:
            current_index_root_hash: Current index root hash to compute stale flag

        Returns:
            List of concept entries with id, sha256, built_at, stale
        """
        # GC manifest first
        self.gc_manifest()

        concepts = []
        for entry in sorted(self.manifest, key=lambda x: x["id"]):
            concept_entry = entry.copy()

            # Compute stale flag if we have the current index root hash
            if current_index_root_hash is not None:
                # Load the card to get its stored index root hash
                try:
                    card = self.load(entry["id"])
                    stored_hash = card.provenance.index_root_hash
                    concept_entry["stale"] = stored_hash != current_index_root_hash
                except Exception:
                    # If we can't load the card, assume it's stale
                    concept_entry["stale"] = True
            else:
                concept_entry["stale"] = False

            concepts.append(concept_entry)

        return concepts

    def validate_references(self, slug: str) -> Dict:
        """Validate references for a concept card.

        Args:
            slug: The concept slug to validate

        Returns:
            Dictionary with missing, cycles, and ok status
        """
        try:
            card = self.load(slug)
            related = card.related
        except FileNotFoundError:
            return {"missing": [], "cycles": [], "ok": False}

        # Check for missing references
        missing = []
        for ref_slug in related:
            if not self.exists(ref_slug):
                missing.append(ref_slug)

        # Check for cycles
        cycles = self._detect_cycles(slug)

        return {
            "missing": sorted(missing),  # Deterministic ordering
            "cycles": sorted(cycles),  # Deterministic ordering
            "ok": len(missing) == 0 and len(cycles) == 0,
        }

    def _detect_cycles(
        self, slug: str, visited: Optional[set] = None, path: Optional[list] = None
    ) -> List[str]:
        """Detect cycles in the reference graph using DFS."""
        if visited is None:
            visited = set()
        if path is None:
            path = []

        if slug in visited:
            # Check if this creates a cycle
            if slug in path:
                cycle_start = path.index(slug)
                return path[cycle_start:] + [slug]
            return []

        visited.add(slug)
        path.append(slug)

        try:
            card = self.load(slug)
            for ref_slug in card.related:
                if self.exists(ref_slug):
                    cycle = self._detect_cycles(ref_slug, visited, path)
                    if cycle:
                        return cycle
        except FileNotFoundError:
            pass

        path.pop()
        return []

    def get_all_cards(self) -> List[Dict]:
        """Get all cards as dictionaries with deterministic sorting."""
        # GC manifest first
        self.gc_manifest()

        cards = []
        for entry in sorted(self.manifest, key=lambda x: x["id"]):
            try:
                card = self.load(entry["id"])
                card_dict = card.model_dump()

                # Ensure deterministic sorting of related and tags
                card_dict["related"] = sorted(card_dict.get("related", []))
                card_dict["tags"] = sorted(card_dict.get("tags", []))

                cards.append(card_dict)
            except Exception:
                # Skip cards that can't be loaded
                continue

        return cards

    def get_tag_counts(self) -> List[Dict]:
        """Get tag counts with deterministic ordering."""
        cards = self.get_all_cards()

        # Count tags
        tag_counts = {}
        for card in cards:
            for tag in card.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count (descending), then by tag (ascending)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))

        return [{"tag": tag, "count": count} for tag, count in sorted_tags]

    def export_concepts(self, slugs: Optional[List[str]] = None) -> bytes:
        """Export concepts to a ZIP file.

        Args:
            slugs: List of slugs to export. If None, export all concepts.

        Returns:
            ZIP file as bytes
        """
        import io
        import zipfile
        import json

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            manifest_json = json.dumps(
                self.manifest, separators=(",", ":"), ensure_ascii=True
            )
            zip_file.writestr("concepts_manifest.json", manifest_json)

            # Determine which slugs to export
            if slugs is None:
                # Export all concepts
                slugs_to_export = [entry["id"] for entry in self.manifest]
            else:
                # Export only specified slugs that exist
                slugs_to_export = [slug for slug in slugs if self.exists(slug)]

            # Sort for deterministic ordering
            slugs_to_export.sort()

            # Add concept files
            for slug in slugs_to_export:
                card_path = self.concepts_dir / f"{slug}.json"
                if card_path.exists():
                    zip_file.writestr(f"cards/{slug}.json", card_path.read_text())

        return zip_buffer.getvalue()
