"""npm lockfile parser for v2/v3 "packages" format.

The parser extracts a flat mapping of *installation path* → package metadata.
Each entry contains:
- name
- version
- dependencies (prod)
- devDependencies
- optionalDependencies
- peerDependencies
- any other fields are ignored for the graph construction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

class LockfileParseError(RuntimeError):
    """Raised when the lockfile cannot be parsed or lacks required fields."""


def load_lockfile(lock_path: str | Path) -> Dict[str, Any]:
    """Load a ``package-lock.json`` file and return the parsed JSON.

    Parameters
    ----------
    lock_path:
        Path to the lockfile.

    Returns
    -------
    dict
        Parsed JSON object.
    """
    p = Path(lock_path)
    if not p.is_file():
        raise FileNotFoundError(f"Lockfile not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise LockfileParseError(f"Invalid JSON in {p}: {exc}") from exc


def _extract_packages(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return the ``packages`` dict from the lockfile.

    npm v2/v3 lockfiles contain a top‑level ``packages`` key where each key is
    an installation path ("" for the project root, "node_modules/foo" for a direct
    dependency, etc.).
    """
    packages = data.get("packages")
    if not isinstance(packages, dict):
        raise LockfileParseError("Lockfile is missing a top‑level 'packages' mapping")
    return packages


def parse_packages(packages: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Normalise package entries.

    The function guarantees that each returned entry contains at least the
    fields ``name`` and ``version``.  Missing optional fields are replaced with an
    empty dict.
    """
    normalised: Dict[str, Dict[str, Any]] = {}
    for path, meta in packages.items():
        if not isinstance(meta, dict):
            continue
        name = meta.get("name")
        version = meta.get("version")
        if not name or not version:
            # The root entry may omit "name" – we still keep it for completeness.
            name = name or "<root>"
            version = version or ""
        normalised[path] = {
            "name": name,
            "version": version,
            "dependencies": meta.get("dependencies", {}),
            "devDependencies": meta.get("devDependencies", {}),
            "optionalDependencies": meta.get("optionalDependencies", {}),
            "peerDependencies": meta.get("peerDependencies", {}),
        }
    return normalised


def parse_lockfile(lock_path: str | Path) -> Dict[str, Dict[str, Any]]:
    """High‑level helper that returns a mapping ``install_path → package info``.

    This is the entry point used by the graph engine.
    """
    data = load_lockfile(lock_path)
    packages = _extract_packages(data)
    return parse_packages(packages)
