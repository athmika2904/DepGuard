
from __future__ import annotations

from typing import Dict, List, Set, Tuple

import networkx as nx

from ..models.vulnerability import Vulnerability
from .graph_engine import build_dependency_graph, get_all_paths
from .vulnerability_service import query_vulnerabilities
from .risk_engine import assess_vulnerability, summarize_risks


class ScanResult:
    def __init__(
        self,
        graph: nx.DiGraph,
        vulnerabilities: Dict[str, List[Vulnerability]],
        status: str = "complete",
        errors: Dict[Tuple[str, str], str] | None = None,
        risk_summary: Dict[str, int] | None = None,
    ):
        self.graph = graph
        self.vulnerabilities = vulnerabilities
        self.status = status
        self.errors = errors or {}
        self.risk_summary = risk_summary or summarize_risks(vulnerabilities)


async def run_scan(lockfile_path: str) -> ScanResult:
    graph = build_dependency_graph(lockfile_path)

    unique_packages: Set[Tuple[str, str]] = set()
    node_to_package: Dict[str, Tuple[str, str]] = {}

    for node_id, attrs in graph.nodes(data=True):
        if node_id == "<root>":
            continue

        package_name = attrs["name"]
        version = attrs["version"]

        if not package_name or not version:
            continue

        package_key = (package_name, version)

        unique_packages.add(package_key)
        node_to_package[node_id] = package_key

    osv_results, osv_errors = await query_vulnerabilities(
        unique_packages
    )

    node_vulnerabilities: Dict[str, List[Vulnerability]] = {}

    for node_id, package_key in node_to_package.items():
        findings = osv_results.get(package_key, [])

        if not findings:
            continue

        paths = get_all_paths(graph, node_id)

        for vulnerability in findings:
            enriched = vulnerability.model_copy(
                update={
                    "dependency_paths": paths,
                    "direct": graph.nodes[node_id].get("direct", False),
                    "dependency_depth": graph.nodes[node_id].get(
                        "depth", -1
                    ),
                }
            )
            enriched = enriched.model_copy(
                update=assess_vulnerability(enriched)
            )

            node_vulnerabilities.setdefault(
                node_id, []
            ).append(enriched)

    # Present the most urgent findings first within each installed package path.
    for findings in node_vulnerabilities.values():
        findings.sort(
            key=lambda item: (
                item.risk_score is not None,
                item.risk_score if item.risk_score is not None else -1.0,
            ),
            reverse=True,
        )

    status = "partial" if osv_errors else "complete"
    risk_summary = summarize_risks(node_vulnerabilities)

    return ScanResult(
        graph=graph,
        vulnerabilities=node_vulnerabilities,
        status=status,
        errors=osv_errors,
        risk_summary=risk_summary,
    )

