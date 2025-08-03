"""
Concept Card diff utility.

This module provides deterministic diff functionality for comparing concept cards.
"""

import hashlib
import json
from typing import Any


def card_diff(old: dict, new: dict) -> dict:
    """Return a minimal, deterministic structural diff.

    Args:
        old: The old concept card dictionary
        new: The new concept card dictionary

    Returns:
        Dictionary with changed, added, and removed fields
    """
    # Remove response-only fields that shouldn't be compared
    old_clean = _remove_transient_fields(old)
    new_clean = _remove_transient_fields(new)

    # Compute the diff
    changed = {}
    added = {}
    removed = {}

    # Compare all keys
    all_keys = sorted(set(old_clean.keys()) | set(new_clean.keys()))

    for key in all_keys:
        if key not in old_clean:
            added[key] = new_clean[key]
        elif key not in new_clean:
            removed[key] = old_clean[key]
        else:
            # Key exists in both, compare values
            diff = _compare_values(old_clean[key], new_clean[key], key)
            if diff:
                changed[key] = diff

    return {"changed": changed, "added": added, "removed": removed}


def _remove_transient_fields(card: dict) -> dict:
    """Remove transient fields that shouldn't be compared in diffs."""
    card_copy = card.copy()

    # Remove stale flag if present
    if "stale" in card_copy:
        del card_copy["stale"]

    return card_copy


def _compare_values(old_val: Any, new_val: Any, path: str) -> Any:
    """Recursively compare values and return differences."""
    if not isinstance(old_val, type(new_val)):
        return {"old": old_val, "new": new_val}

    if isinstance(old_val, dict):
        return _compare_dicts(old_val, new_val, path)
    elif isinstance(old_val, list):
        return _compare_lists(old_val, new_val, path)
    else:
        # Simple value comparison
        if old_val != new_val:
            return {"old": old_val, "new": new_val}
        return None


def _compare_dicts(old_dict: dict, new_dict: dict, path: str) -> Any:
    """Compare dictionaries recursively."""
    all_keys = sorted(set(old_dict.keys()) | set(new_dict.keys()))
    changes = {}

    for key in all_keys:
        if key not in old_dict:
            changes[key] = {"added": new_dict[key]}
        elif key not in new_dict:
            changes[key] = {"removed": old_dict[key]}
        else:
            diff = _compare_values(old_dict[key], new_dict[key], f"{path}.{key}")
            if diff:
                changes[key] = diff

    return changes if changes else None


def _compare_lists(old_list: list, new_list: list, path: str) -> Any:
    """Compare lists by index."""
    if len(old_list) != len(new_list):
        return {"old": old_list, "new": new_list}

    changes = {}
    for i, (old_item, new_item) in enumerate(zip(old_list, new_list)):
        diff = _compare_values(old_item, new_item, f"{path}[{i}]")
        if diff:
            changes[i] = diff

    return changes if changes else None


def compute_card_hash(card: dict) -> str:
    """Compute a deterministic hash of a concept card."""
    # Remove transient fields and sort keys
    clean_card = _remove_transient_fields(card)
    card_json = json.dumps(
        clean_card, separators=(",", ":"), sort_keys=True, ensure_ascii=True
    )
    return hashlib.sha256(card_json.encode("utf-8")).hexdigest()
