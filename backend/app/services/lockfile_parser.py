
"""
npm lockfile parser for package-lock.json v2/v3.

Extracts the packages section into a normalized mapping:

    installation_path -> package metadata

Each package entry contains:
- name
- version
- dependencies
- devDependencies
- optionalDependencies
- peerDependencies

Other package metadata is ignored by the graph engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LockfileParseError(RuntimeError):
    """Raised when a lockfile is invalid or lacks required fields."""


# ---------------------------------------------------------------------------
# Load lockfile
# ---------------------------------------------------------------------------

def load_lockfile(lock_path: str | Path) -> dict[str, Any]:
    """
    Read and parse a package-lock.json file.

    Raises:
        FileNotFoundError: If the file does not exist.
        LockfileParseError: If the JSON is invalid or unreadable.
    """

    path = Path(lock_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Lockfile not found: {path}"
        )

    try:

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except (json.JSONDecodeError, UnicodeDecodeError) as exc:

        raise LockfileParseError(
            f"Invalid JSON in {path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise LockfileParseError(
            "Lockfile must contain a JSON object"
        )

    return data


# ---------------------------------------------------------------------------
# Extract packages section
# ---------------------------------------------------------------------------

def _extract_packages(
    data: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Extract the top-level packages mapping.

    npm v2/v3 lockfiles contain installation paths as keys.

    Examples:
        ""
        "node_modules/express"
        "node_modules/express/node_modules/debug"
        "node_modules/@scope/package"
    """

    if not isinstance(data, dict):
        raise LockfileParseError(
            "Lockfile must contain a JSON object"
        )

    packages = data.get("packages")

    if not isinstance(packages, dict):
        raise LockfileParseError(
            "Lockfile is missing a top-level 'packages' mapping"
        )

    return packages


# ---------------------------------------------------------------------------
# Normalize package entries
# ---------------------------------------------------------------------------

def _infer_package_name(path: str) -> str:
    """
    Infer a package name from its installation path.

    Examples:
        node_modules/express -> express
        node_modules/@scope/pkg -> @scope/pkg
        node_modules/a/node_modules/debug -> debug
    """

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    name_parts: list[str] = []

    # Use the last node_modules segment.
    for index, part in enumerate(parts):

        if part == "node_modules" and index + 1 < len(parts):
            name_parts = parts[index + 1:]

    if not name_parts:
        raise LockfileParseError(
            f"Cannot determine package name for path: {path}"
        )

    return "/".join(name_parts)


def parse_packages(
    packages: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Normalize package metadata by installation path.

    Missing package names are inferred from installation paths.
    Missing versions are represented as empty strings.
    """

    if not isinstance(packages, dict):
        raise LockfileParseError(
            "The 'packages' section must be a JSON object"
        )

    normalized: dict[str, dict[str, Any]] = {}

    dependency_fields = (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    )

    for path, meta in packages.items():

        if not isinstance(path, str) or not isinstance(meta, dict):
            raise LockfileParseError(
                "Each package entry must have a string path "
                "and object metadata"
            )

        # ---------------------------------------------------------------
        # Package name
        # ---------------------------------------------------------------

        name = meta.get("name")

        if not name:

            if path == "":
                name = "<root>"

            else:
                name = _infer_package_name(path)

        # ---------------------------------------------------------------
        # Package version
        # ---------------------------------------------------------------

        version = meta.get("version")

        if version is None:
            version = ""

        if not isinstance(name, str) or not isinstance(version, str):
            raise LockfileParseError(
                f"Invalid name or version for package at {path}"
            )

        # ---------------------------------------------------------------
        # Dependency sections
        # ---------------------------------------------------------------

        entry: dict[str, Any] = {
            "name": name,
            "version": version,
        }

        for field in dependency_fields:

            value = meta.get(field, {})

            if not isinstance(value, dict):
                raise LockfileParseError(
                    f"Invalid {field} for package at {path}"
                )

            entry[field] = value

        normalized[path] = entry

    return normalized


# ---------------------------------------------------------------------------
# Public parser entry point
# ---------------------------------------------------------------------------

def parse_lockfile(
    lock_path: str | Path,
) -> dict[str, dict[str, Any]]:
    """
    Load and normalize an npm package-lock.json file.

    Returns:
        A mapping of installation path to normalized package metadata.
    """

    data = load_lockfile(lock_path)

    packages = _extract_packages(data)

    return parse_packages(packages)

