"""
Playbook utilities for deterministic behavior and hash computation.

This module provides utilities for computing stable hashes of playbook steps
to ensure deterministic behavior across runs.
"""

import hashlib
from typing import List
from .models import PlayResultStep


def compute_steps_hash(steps: List[PlayResultStep]) -> str:
    """
    Compute a deterministic hash of playbook steps.

    The hash is computed over the normalized content of each step:
    - check command
    - command list (sorted and joined)
    - rfc references (sorted and joined)

    Args:
        steps: List of PlayResultStep objects

    Returns:
        SHA256 hash as hex string
    """
    if not steps:
        return hashlib.sha256(b"").hexdigest()

    # Normalize each step's content
    step_contents = []
    for step in steps:
        # Normalize check command (strip whitespace)
        check = step.check.strip() if step.check else ""

        # Normalize commands (sort and join)
        commands = sorted([cmd.strip() for cmd in step.commands if cmd.strip()])
        commands_str = "|".join(commands)

        # Normalize RFC references (sort by RFC number and section)
        rfc_refs = []
        for citation in step.citations:
            rfc_refs.append(f"{citation.rfc}:{citation.section}")
        rfc_refs.sort()
        rfc_str = "|".join(rfc_refs)

        # Combine step content
        step_content = f"{check}|{commands_str}|{rfc_str}"
        step_contents.append(step_content)

    # Join all step contents with newlines and compute hash
    all_content = "\n".join(step_contents)
    return hashlib.sha256(all_content.encode("utf-8")).hexdigest()


def normalize_step_for_hash(step: PlayResultStep) -> str:
    """
    Normalize a single step for hash computation.

    Args:
        step: PlayResultStep object

    Returns:
        Normalized string representation
    """
    # Normalize check command
    check = step.check.strip() if step.check else ""

    # Normalize commands
    commands = sorted([cmd.strip() for cmd in step.commands if cmd.strip()])
    commands_str = "|".join(commands)

    # Normalize RFC references
    rfc_refs = []
    for citation in step.citations:
        rfc_refs.append(f"{citation.rfc}:{citation.section}")
    rfc_refs.sort()
    rfc_str = "|".join(rfc_refs)

    return f"{check}|{commands_str}|{rfc_str}"
