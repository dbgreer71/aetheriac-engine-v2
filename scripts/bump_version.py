#!/usr/bin/env python3
"""
Version bumping script for ae2 package.

Usage:
    python scripts/bump_version.py [patch|minor|major]
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse version string into major, minor, patch components."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(int(x) for x in match.groups())


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version components into version string."""
    return f"{major}.{minor}.{patch}"


def bump_version(version_str: str, bump_type: str) -> str:
    """Bump version according to semantic versioning rules."""
    major, minor, patch = parse_version(version_str)

    if bump_type == "patch":
        patch += 1
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use patch, minor, or major.")

    return format_version(major, minor, patch)


def update_version_file(version: str) -> None:
    """Update __version__ in ae2/__init__.py."""
    init_file = Path("ae2/__init__.py")

    if not init_file.exists():
        raise FileNotFoundError("ae2/__init__.py not found")

    content = init_file.read_text()

    # Replace existing __version__ line
    pattern = r'^__version__\s*=\s*["\'][^"\']*["\']'
    replacement = f'__version__ = "{version}"'

    if re.search(pattern, content, re.MULTILINE):
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        # Add __version__ if it doesn't exist
        new_content = f'__version__ = "{version}"\n\n{content}'

    init_file.write_text(new_content)


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    bump_type = sys.argv[1].lower()

    if bump_type not in ["patch", "minor", "major"]:
        print(
            f"Error: Invalid bump type '{bump_type}'. Use patch, minor, or major.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        # Read current version
        init_file = Path("ae2/__init__.py")
        if not init_file.exists():
            print("Error: ae2/__init__.py not found", file=sys.stderr)
            sys.exit(1)

        content = init_file.read_text()
        version_match = re.search(
            r'^__version__\s*=\s*["\']([^"\']*)["\']', content, re.MULTILINE
        )

        if not version_match:
            print("Error: __version__ not found in ae2/__init__.py", file=sys.stderr)
            sys.exit(1)

        current_version = version_match.group(1)
        new_version = bump_version(current_version, bump_type)

        # Update the file
        update_version_file(new_version)

        print(f"Bumped version from {current_version} to {new_version}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
