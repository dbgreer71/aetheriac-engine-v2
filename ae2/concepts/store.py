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
        self.manifest_path = self.concepts_dir / "manifest.json"
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load the manifest file, creating it if it doesn't exist."""
        if self.manifest_path.exists():
            with open(self.manifest_path, "r") as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {"concepts": []}
            self._save_manifest()

    def _save_manifest(self) -> None:
        """Save the manifest file."""
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2, default=str)

    def _compute_sha256(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def save(self, card: ConceptCard) -> Path:
        """Save a concept card to disk and update manifest.

        Args:
            card: The concept card to save

        Returns:
            Path to the saved file
        """
        # Create the card file path
        card_path = self.concepts_dir / f"{card.id}.json"

        # Serialize the card
        card_dict = card.model_dump()
        card_json = json.dumps(card_dict, indent=2, default=str)

        # Compute SHA256 of the card content
        card_sha256 = self._compute_sha256(card_json)

        # Write the card file
        with open(card_path, "w") as f:
            f.write(card_json)

        # Update manifest
        manifest_entry = {
            "id": card.id,
            "path": str(card_path.relative_to(self.concepts_dir)),
            "sha256": card_sha256,
            "built_at": card.provenance.built_at.isoformat(),
        }

        # Remove existing entry if it exists
        self.manifest["concepts"] = [
            entry for entry in self.manifest["concepts"] if entry["id"] != card.id
        ]

        # Add new entry
        self.manifest["concepts"].append(manifest_entry)
        self._save_manifest()

        return card_path

    def load(self, card_id: str) -> ConceptCard:
        """Load a concept card by ID.

        Args:
            card_id: The concept card ID

        Returns:
            The loaded concept card

        Raises:
            FileNotFoundError: If the card doesn't exist
        """
        card_path = self.concepts_dir / f"{card_id}.json"

        if not card_path.exists():
            raise FileNotFoundError(f"Concept card not found: {card_id}")

        with open(card_path, "r") as f:
            card_dict = json.load(f)

        return ConceptCard(**card_dict)

    def list_ids(self) -> List[str]:
        """List all concept card IDs.

        Returns:
            List of concept card IDs
        """
        return [entry["id"] for entry in self.manifest["concepts"]]

    def exists(self, card_id: str) -> bool:
        """Check if a concept card exists.

        Args:
            card_id: The concept card ID

        Returns:
            True if the card exists, False otherwise
        """
        return (self.concepts_dir / f"{card_id}.json").exists()

    def get_manifest(self) -> Dict:
        """Get the current manifest.

        Returns:
            The manifest dictionary
        """
        return self.manifest.copy()
