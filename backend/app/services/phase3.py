"""Phase 3 – OSV vulnerability integration.

This module bundles the three core components introduced for Phase 3:

1. **Vulnerability model** – imported from ``backend.app.models.vulnerability``.
2. **Vulnerability service** – asynchronous HTTP client that queries the OSV API,
   handles retries/back‑off, and normalises responses into ``Vulnerability`` objects.
3. **Scan service** – orchestrates parsing the lockfile, building the dependency
   graph (Phase 2), extracting unique ``(package, version)`` pairs, invoking the
   vulnerability service, and attaching findings back to the graph.

The implementation is deliberately modular; the services can also be used
independently if required.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

import httpx

from ..models.vulnerability import Vulnerability
from .graph_engine import build_dependency_graph, get_all_paths
from .lockfile_parser import parse_lockfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vulnerability service (OSV API interaction)
# ---------------------------------------------------------------------------

OSV_ENDPOINT = "https://api.osv.dev/v1/query"
_MAX_RETRIES = 3
_BACKOFF_FACTOR = 0.5  # seconds, exponential back‑off


class OSVError(RuntimeError):
    """Raised when the OSV API cannot be queried successfully."""


async def _post_osv(payload: dict, client: httpx.AsyncClient) -> dict:
    """POST payload to OSV with retry / back‑off handling.

    Retries on HTTP 429 (rate‑limit) and 5xx server errors, as well as on
    network‑level ``httpx.RequestError``. Non‑retryable status codes raise
    ``OSVError`` immediately.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = await client.post(OSV_ENDPOINT, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {429, 500, 502, 503, 504}:
                if attempt < _MAX_RETRIES:
                    backoff = _BACKOFF_FACTOR * (2 ** (attempt - 1))
                    logger.warning(
                        "OSV request transient failure %s – retry %d/%d after %.2fs",
                        exc.response.status_code,
                        attempt,
                        _MAX_RETRIES,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
            raise OSVError(f"OSV request failed ({exc.response.status_code}): {exc}") from exc
        except httpx.RequestError as exc:
            if attempt < _MAX_RETRIES:
                backoff = _BACKOFF_FACTOR * (2 ** (attempt - 1))
                logger.warning(
                    "OSV request error %s – retry %d/%d after %.2fs",
                    exc,
                    attempt,
                    _MAX_RETRIES,
                    backoff,
                )
                await asyncio.sleep(backoff)
                continue
            raise OSVError(f"OSV request error: {exc}") from exc
    raise OSVError("Exhausted retries without success.")


def _parse_iso(value: str | None) -> datetime | None:
    """Parse ISO‑8601 timestamps, returning ``None`` on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.rstrip("Z"))
    except Exception:  # pragma: no cover – defensive
        return None


def _extract_fixed_versions(entry: dict) -> List[str] | None:
    """Collect all fixed versions from OSV ``affected`` objects."""
    fixes: Set[str] = set()
    for affected in entry.get("affected", []):
        for range_ in affected.get("ranges", []):
            for event in range_.get("events", []):
                if "fixed" in event:
                    fixes.add(event["fixed"]))
    return list(fixes) if fixes else None


def _parse_osv_response(data: dict, pkg_name: str, version: str) -> List[Vulnerability]:
    """Transform raw OSV JSON into ``Vulnerability`` objects.

    Handles the normal ``{"vulns": [...]}`` shape as well as a single dict
    containing an ``id`` field.
    """
    vulns: List[Vulnerability] = []

    if isinstance(data, dict) and "id" in data:
        entries = [data]
    else:
        entries = data.get("vulns", [])

    for entry in entries:
        try:
            vuln = Vulnerability(
                id=entry["id"],
                summary=entry.get("summary"),
                details=entry.get("details"),
                aliases=entry.get("aliases"),
                package_name=pkg_name,
                installed_version=version,
                affected_ranges=entry.get("affected"),
                fixed_versions=_extract_fixed_versions(entry),
                references=[ref.get("url") for ref in entry.get("references", []) if ref.get("url")],
                severity=entry.get("severity"),
                published=_parse_iso(entry.get("published")),
                modified=_parse_iso(entry.get("modified")),
                withdrawn=_parse_iso(entry.get("withdrawn")),
            )
            vulns.append(vuln)
        except Exception as exc:  # pragma: no cover – defensive
            logger.error("Failed to parse OSV entry %s: %s", entry.get("id"), exc)
    return vulns


async def _post_and_parse(
    name: str,
    version: str,
    payload: dict,
    client: httpx.AsyncClient,
    results: Dict[Tuple[str, str], List[Vulnerability]],
) -> None:
    """POST to OSV, parse the response and store it in ``results``."""
    try:
        raw = await _post_osv(payload, client)
        results[(name, version)] = _parse_osv_response(raw, name, version)
    except OSVError as exc:
        logger.error("OSV query failed for %s@%s: %s", name, version, exc)
        raise


async def query_vulnerabilities(
    packages: Set[Tuple[str, str]],
) -> Dict[Tuple[str, str], List[Vulnerability]]:
    """Query OSV for each ``(package, version)`` pair.

    Returns a mapping from the input tuple to a list of ``Vulnerability`` objects.
    Packages with no known vulnerabilities are mapped to an empty list.
    ``OSVError`` is raised only for network / server failures – a clean
    "no vulnerability" response does **not** raise.
    """
    results: Dict[Tuple[str, str], List[Vulnerability]] = {}
    async with httpx.AsyncClient() as client:
        tasks = []
        for name, version in packages:
            payload = {"package": {"name": name, "ecosystem": "npm"}, "version": version}
            tasks.append(asyncio.create_task(_post_and_parse(name, version, payload, client, results)))
        await asyncio.gather(*tasks)
    return results

# ---------------------------------------------------------------------------
# Scan service – orchestrates parsing, graph building and vulnerability lookup
# ---------------------------------------------------------------------------


class ScanResult:
    """Container for the data produced by a full scan.

    Attributes
    ----------
    graph: The dependency graph produced by ``graph_engine``.
    vulnerabilities: Mapping ``node_path -> List[Vulnerability]`` – each node
        receives the vulnerabilities that affect its exact package+version.
    """

    def __init__(self, graph, vulnerabilities: Dict[str, List[Vulnerability]]):
        self.graph = graph
        self.vulnerabilities = vulnerabilities


async def run_scan(lockfile_path: str) -> ScanResult:
    """Execute the full Phase 3 scan.

    Steps performed:
    1. Parse ``package-lock.json`` using the existing parser.
    2. Build the dependency graph (Phase 2).
    3. Extract unique ``(package_name, installed_version)`` pairs from the graph.
    4. Query OSV for each unique pair.
    5. Attach vulnerability data to every graph node that matches the exact
       name and version, enriching each ``Vulnerability`` instance with graph‑
       specific context (paths, direct flag, depth).
    """
    # 1 + 2 – parse and build graph
    parse_lockfile(lockfile_path)  # ensures parsing works; result not needed directly
    graph = build_dependency_graph(lockfile_path)

    # 3 – collect unique (name, version) tuples and map nodes to them
    unique_pkgs: Set[Tuple[str, str]] = set()
    node_to_pkgver: Dict[str, Tuple[str, str]] = {}
    for node_id, attrs in graph.nodes(data=True):
        if node_id == "<root>":
            continue
        name = attrs["name"]
        version = attrs["version"]
        unique_pkgs.add((name, version))
        node_to_pkgver[node_id] = (name, version)

    # 4 – OSV lookup
    osv_results = await query_vulnerabilities(unique_pkgs)

    # 5 – associate findings with graph nodes
    node_vulns: Dict[str, List[Vulnerability]] = {}
    for node, (pkg, ver) in node_to_pkgver.items():
        vulns = osv_results.get((pkg, ver), [])
        if not vulns:
            continue
        # Gather all root‑to‑node paths for context
        paths = list(get_all_paths(graph, node))
        for v in vulns:
            enriched = v.copy()
            enriched.dependency_paths = paths
            enriched.direct = graph.nodes[node].get("direct", False)
            enriched.dependency_depth = graph.nodes[node].get("depth", -1)
            node_vulns.setdefault(node, []).append(enriched)

    return ScanResult(graph=graph, vulnerabilities=node_vulns)
