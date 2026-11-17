"""Dependency Graph Engine (npm v2/v3 with proper scope handling & edge types)

This module parses the ``packages`` section of a ``package-lock.json`` (npm
v2/v3) and builds a directed graph that respects npm's *nearest‑ancestor*
resolution algorithm.  It also records the type of each dependency edge
(``prod``, ``dev``, ``optional`` or ``peer``) and correctly propagates dependency
scopes to transitive children, re‑processing descendants when new scopes are
added.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

import networkx as nx

from .lockfile_parser import parse_lockfile, LockfileParseError

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
NodeAttrs = Dict[str, Any]
Graph = nx.DiGraph

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _determine_direct_paths_and_scopes(
    packages: Dict[str, Dict[str, Any]],
) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """Return direct install paths and a mapping ``install_path → scopes``.

    The root entry (key "") contains the four dependency sections. Any package
    listed there is a *direct* dependency. For each direct package we compute the
    exact install path (e.g. ``node_modules/foo`` or ``node_modules/@scope/foo``)
    and record the scopes (``prod``, ``dev``, ``optional``, ``peer``) in which it
    was declared.
    """
    root_meta = packages.get("", {})
    direct_paths: Set[str] = set()
    path_to_scopes: Dict[str, Set[str]] = {}
    for section, scope in (
        ("dependencies", "prod"),
        ("devDependencies", "dev"),
        ("optionalDependencies", "optional"),
        ("peerDependencies", "peer"),
    ):
        for name in root_meta.get(section, {}):
            # Compute the exact install path for this direct dependency.
            install_path = f"node_modules/{name}" if name else ""
            if install_path:
                direct_paths.add(install_path)
                path_to_scopes.setdefault(install_path, set()).add(scope)
    return direct_paths, path_to_scopes

    """Return direct install paths and a mapping ``package_name → scopes``.

    The root entry (key ``""``) contains the four dependency sections.  Any
    package listed there is considered a *direct* dependency.  The function
    collects the declared scopes (``prod``, ``dev``, ``optional``, ``peer``) for
    each direct package name and returns both the set of install paths that
    correspond to those names **and** the mapping.
    """
    root_meta = packages.get("", {})
    direct_names: Set[str] = set()
    name_to_scopes: Dict[str, Set[str]] = {}
    for section, scope in (
        ("dependencies", "prod"),
        ("devDependencies", "dev"),
        ("optionalDependencies", "optional"),
        ("peerDependencies", "peer"),
    ):
        for name in root_meta.get(section, {}):
            direct_names.add(name)
            name_to_scopes.setdefault(name, set()).add(scope)
    # Translate names → install paths that actually exist.
    direct_paths = {path for path, meta in packages.items() if meta.get("name") in direct_names}
    return direct_paths, name_to_scopes


def _scope_for_package(path: str, packages: Dict[str, Dict[str, Any]], path_to_scopes: Dict[str, Set[str]]) -> Set[str]:
    """Return the declared scopes for a *direct* package, or an empty set.

    ``path_to_scopes`` is the mapping returned by ``_determine_direct_paths_and_scopes``.
    """
    return path_to_scopes.get(path, set())
    """Return the declared scopes for a *direct* package, or an empty set.

    ``name_to_scopes`` is the mapping returned by ``_determine_direct_paths_and_scopes``.
    """
    name = packages[path]["name"]
    return name_to_scopes.get(name, set())


def _ancestor_paths(start_path: str) -> List[str]:
    """Yield candidate ``node_modules`` directories for npm resolution.

    The function now uses POSIX '/' separator regardless of the host OS, because npm lockfile paths always use forward slashes.
    """
    # Split on forward slash to handle npm paths on Windows.
    parts = [p for p in start_path.split('/') if p]
    candidates: List[str] = []
    # Current package's node_modules
    cur = f"{start_path}/node_modules" if start_path else "node_modules"
    candidates.append(cur)
    # Walk up the hierarchy
    while parts:
        parts.pop()
        if parts:
            cur = f"{'/'.join(parts)}/node_modules"
        else:
            cur = "node_modules"
        candidates.append(cur)
    # Preserve order, deduplicate
    seen = set()
    ordered: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered
    """Yield candidate ``node_modules`` directories for npm resolution.

    For a package installed at ``start_path`` (e.g. ``node_modules/a/node_modules/b``)
    the function returns a list of ``node_modules`` directories that npm would search
    when that package requires another dependency, ordered from nearest to farthest.
    """
    parts = [p for p in start_path.split(os.sep) if p]
    candidates: List[str] = []
    # Current package's node_modules
    cur = os.path.join(start_path, "node_modules") if start_path else "node_modules"
    candidates.append(cur)
    # Walk up the hierarchy
    while parts:
        parts.pop()
        if parts:
            cur = os.path.join(os.path.sep.join(parts), "node_modules")
        else:
            cur = "node_modules"
        candidates.append(cur)
    # Preserve order, deduplicate
    seen = set()
    ordered: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def _find_nearest_install(parent_path: str, dep_name: str, packages: Dict[str, Dict[str, Any]]) -> str | None:
    """Return the *nearest* install path for ``dep_name`` relative to ``parent_path``.

    Implements npm's nearest‑ancestor module resolution.
    """
    for candidate_root in _ancestor_paths(parent_path):
        candidate_path = f"{candidate_root}/{dep_name}"
        if candidate_path in packages:
            return candidate_path
    return None
    """Return the *nearest* install path for ``dep_name`` relative to ``parent_path``.

    Implements npm's nearest‑ancestor module resolution.
    """
    for candidate_root in _ancestor_paths(parent_path):
        candidate_path = os.path.join(candidate_root, dep_name)
        if candidate_path in packages:
            return candidate_path
    return None

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_dependency_graph(lockfile_path: str | Path) -> Graph:
    """Construct a directed graph from a ``package-lock.json`` (v2/v3).

    Nodes are identified by their install path (e.g. ``node_modules/foo``).  A
    synthetic ``<root>`` node acts as the source for direct dependencies.
    Edge attributes include ``dep_type`` (one of ``prod``, ``dev``, ``optional``
    or ``peer``) mirroring the declaration location.
    """
    packages = parse_lockfile(lockfile_path)
    direct_paths, path_to_scopes = _determine_direct_paths_and_scopes(packages)

    graph = nx.DiGraph()
    root_node = "<root>"
    graph.add_node(
        root_node,
        name="<root>",
        version="",
        path="",
        direct=True,
        scope=set(),
        parents=[],
        depth=0,
    )

    # Add package nodes
    for path, meta in packages.items():
        if path == "":
            continue
        node_attrs: NodeAttrs = {
            "name": meta["name"],
            "version": meta["version"],
            "path": path,
            "direct": path in direct_paths,
            "scope": _scope_for_package(path, packages, path_to_scopes) if path in direct_paths else set(),
            "parents": [],
            "depth": -1,
        }
        graph.add_node(path, **node_attrs)

    # Resolve edges, preserving dependency type
    for parent_path, meta in packages.items():
        if parent_path == "":
            continue
        for dep_type, dep_map in (
            ("prod", meta.get("dependencies")),
            ("dev", meta.get("devDependencies")),
            ("optional", meta.get("optionalDependencies")),
            ("peer", meta.get("peerDependencies")),
        ):
            if not isinstance(dep_map, dict):
                continue
            for dep_name in dep_map:
                child_path = _find_nearest_install(parent_path, dep_name, packages)
                if child_path is None:
                    # Unresolved (e.g., missing peer) – skip edge.
                    continue
                # Merge dependency types if edge already exists
                if graph.has_edge(parent_path, child_path):
                    existing = graph.edges[parent_path, child_path].get('dep_type')
                    if isinstance(existing, set):
                        existing.add(dep_type)
                        graph.edges[parent_path, child_path]['dep_type'] = existing
                    else:
                        # Convert to set of types
                        new_set = {existing, dep_type}
                        graph.edges[parent_path, child_path]['dep_type'] = new_set
                else:
                    graph.add_edge(parent_path, child_path, dep_type={dep_type})
                graph.nodes[child_path]["parents"].append(parent_path)

    # Connect direct dependencies to synthetic root
    for path in direct_paths:
        if path in graph:
            # Add root edge only if the package has no other incoming edges (i.e., no parents yet)
            if not graph.nodes[path]["parents"]:
                edge_type = path_to_scopes.get(path, {"prod"})
                graph.add_edge(root_node, path, dep_type=edge_type)
                graph.nodes[path]["parents"].append(root_node)



    # ---------------------------------------------------------------
    # Scope propagation – iterative until stable (handles multiple parents)
    # ---------------------------------------------------------------
    changed = True
    while changed:
        changed = False
        for parent, child, data in graph.edges(data=True):
            parent_scope = graph.nodes[parent]["scope"]
            child_scope = graph.nodes[child]["scope"]
            new_scope = child_scope.union(parent_scope)
            if new_scope != child_scope:
                graph.nodes[child]["scope"] = new_scope
                changed = True

    # Compute depth (shortest path from root)
    for node in graph.nodes:
        if node == root_node:
            continue
        try:
            depth = nx.shortest_path_length(graph, source=root_node, target=node)
        except nx.NetworkXNoPath:
            depth = -1
        graph.nodes[node]["depth"] = depth

    return graph

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_all_nodes(graph: Graph) -> List[NodeAttrs]:
    """Return a list of node attribute dictionaries (excluding the synthetic root)."""
    return [attrs for nid, attrs in graph.nodes(data=True) if nid != "<root>"]


def get_node_info(graph: Graph, node_id: str) -> NodeAttrs:
    """Retrieve the attribute dict for a given node identifier.

    Raises ``KeyError`` if the node does not exist.
    """
    if node_id not in graph:
        raise KeyError(f"Node {node_id!r} not found in dependency graph")
    return graph.nodes[node_id]


def get_all_paths(graph: Graph, target_node: str, limit: int = 1000) -> List[List[str]]:
    """Return up to ``limit`` simple paths from the synthetic root to ``target_node``.

    ``nx.all_simple_paths`` yields an iterator; we manually stop after ``limit``
    paths to avoid exponential blow‑up.
    """
    root = "<root>"
    if target_node not in graph:
        raise KeyError(f"Target node {target_node!r} not in graph")
    paths: List[List[str]] = []
    for i, path in enumerate(nx.all_simple_paths(graph, source=root, target=target_node)):
        if i >= limit:
            break
        paths.append(path)
    return paths

# ---------------------------------------------------------------------------
# Example entry‑point (manual testing)
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.graph_engine <package-lock.json>")
        sys.exit(1)

    g = build_dependency_graph(sys.argv[1])
    print(f"Graph built – {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    for n in list_all_nodes(g)[:5]:
        print(n)
