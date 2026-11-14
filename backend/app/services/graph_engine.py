"""Dependency Graph Engine
================================

This module builds a directed dependency graph from a ``package-lock.json``
file (v2/v3 format).  It uses **NetworkX** to represent the graph so that the
backend can later query paths, depths, and parent relationships.

The public API is deliberately small – the rest of the codebase can import the
functions without needing to know the internal representation.

Why NetworkX?
--------------
* It provides a clean ``DiGraph`` class with built‑in algorithms for shortest
  paths, reachability, and depth‑first traversal.
* It is pure Python and works in the restricted sandbox.
* The graph can be serialised to a simple dictionary if we need to send it to
  the frontend later.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

import networkx as nx

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
DependencyInfo = Dict[str, Any]
Graph = nx.DiGraph

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_lockfile(lockfile_path: Path) -> Dict[str, Any]:
    """Load a ``package-lock.json`` file.

    Parameters
    ----------
    lockfile_path:
        Path to the lockfile on disk.

    Returns
    -------
    dict
        The parsed JSON content.
    """
    if not lockfile_path.is_file():
        raise FileNotFoundError(f"Lockfile not found: {lockfile_path}")
    with lockfile_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_dependency_graph(lockfile_path: str | Path) -> Graph:
    """Create a directed graph of the dependency tree.

    The function reads the supplied ``package-lock.json`` (v2/v3) and adds a
    node for every package/version pair.  Edges point **from** a package **to**
    its dependency (i.e. ``parent -> child``).  The root of the graph is a
    synthetic node called ``<root>`` that represents the application itself.

    Direct dependencies are identified by the top‑level ``dependencies`` object
    in the lockfile.  All other entries are considered transitive.

    Parameters
    ----------
    lockfile_path:
        Path to the ``package-lock.json`` file.

    Returns
    -------
    networkx.DiGraph
        A directed graph where each node attribute contains:

        * ``name`` – package name
        * ``version`` – resolved version
        * ``direct`` – ``True`` for direct dependencies, ``False`` otherwise
    """
    lock_data = _load_lockfile(Path(lockfile_path))

    # The lockfile format contains a top‑level "dependencies" dictionary where
    # each key is a package name and the value holds metadata including the
    # resolved version and its own nested "requires" map.
    deps = lock_data.get("dependencies", {})

    graph = nx.DiGraph()
    root_node = "<root>"
    graph.add_node(root_node, name="<root>", version="", direct=True)

    def _add_node(pkg_name: str, meta: dict, is_direct: bool) -> None:
        node_id = f"{pkg_name}@{meta.get('version', '')}"
        if node_id not in graph:
            graph.add_node(
                node_id,
                name=pkg_name,
                version=meta.get("version", ""),
                direct=is_direct,
            )
        return node_id

    # First pass – add all packages as nodes.
    for pkg_name, meta in deps.items():
        _add_node(pkg_name, meta, is_direct=True)  # top‑level are direct

    # Second pass – create edges based on the "requires" map.
    for parent_name, parent_meta in deps.items():
        parent_id = f"{parent_name}@{parent_meta.get('version', '')}"
        requires: dict = parent_meta.get("requires", {})
        for child_name, _ in requires.items():
            child_meta = deps.get(child_name)
            # Some lockfiles list a child only under "requires" but not at the
            # top level (e.g. optional peer deps).  Guard against a missing entry.
            if child_meta is None:
                # Create a minimal placeholder so the graph stays connected.
                placeholder = {"version": "unknown"}
                child_id = _add_node(child_name, placeholder, is_direct=False)
            else:
                child_id = _add_node(child_name, child_meta, is_direct=False)
            graph.add_edge(parent_id, child_id)

    # Finally, connect direct dependencies to the synthetic root.
    for pkg_name, meta in deps.items():
        node_id = f"{pkg_name}@{meta.get('version', '')}"
        graph.add_edge(root_node, node_id)

    return graph

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_dependency_paths(graph: Graph, target_pkg: str) -> List[List[str]]:
    """Return **all** paths from the root to a given package.

    ``target_pkg`` should be supplied as ``"name@version"`` – the exact node
    identifier used inside the graph.  The function walks the graph using
    ``nx.all_simple_paths`` which yields every acyclic route.
    """
    root = "<root>"
    if target_pkg not in graph:
        raise ValueError(f"Package {target_pkg!r} not present in the graph")
    return list(nx.all_simple_paths(graph, source=root, target=target_pkg))


def get_package_info(graph: Graph, node_id: str) -> DependencyInfo:
    """Retrieve the stored attributes for a node.

    The return dictionary mirrors the node attributes (``name``, ``version`` and
    ``direct``) and adds a ``depth`` field computed from the shortest path length
    from the root.
    """
    if node_id not in graph:
        raise KeyError(f"Node {node_id!r} does not exist in the graph")
    attrs = graph.nodes[node_id].copy()
    # Depth: number of edges from root to this node.
    try:
        depth = nx.shortest_path_length(graph, source="<root>", target=node_id)
    except nx.NetworkXNoPath:
        depth = -1
    attrs["depth"] = depth
    return attrs


def list_all_dependencies(graph: Graph) -> List[DependencyInfo]:
    """Convenient helper returning a flat list of every package in the lockfile.

    Each entry includes ``name``, ``version``, ``direct`` flag and ``depth``.
    The synthetic ``<root>`` node is omitted because it does not correspond to a
    real package.
    """
    infos: List[DependencyInfo] = []
    for node in graph.nodes:
        if node == "<root>":
            continue
        infos.append(get_package_info(graph, node))
    return infos

# ---------------------------------------------------------------------------
# Example usage (for manual testing)
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.graph_engine <path-to-package-lock.json>")
        sys.exit(1)

    g = build_dependency_graph(sys.argv[1])
    print(f"Graph has {g.number_of_nodes()} nodes and {g.number_of_edges()} edges")
    for pkg in list_all_dependencies(g)[:5]:
        print(pkg)
