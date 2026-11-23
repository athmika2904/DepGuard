
"""
Dependency Graph Engine for npm package-lock.json v2/v3.

Builds a directed dependency graph using npm's nearest-ancestor
module resolution algorithm.

Features:
- Direct and transitive dependency identification.
- Dependency edge types: prod, dev, optional, peer.
- Dependency scope propagation.
- Support for hoisted and nested dependencies.
- Multiple installation paths for the same package.
- Root-to-package dependency path tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx

from .lockfile_parser import parse_lockfile


NodeAttrs = dict[str, Any]
Graph = nx.DiGraph


# ---------------------------------------------------------------------------
# Direct dependency detection
# ---------------------------------------------------------------------------

def _determine_direct_paths_and_scopes(
    packages: dict[str, dict[str, Any]],
) -> tuple[set[str], dict[str, set[str]]]:
    """
    Identify direct dependencies declared in the root package.

    Returns:
        direct_paths:
            Exact installation paths of direct dependencies.

        path_to_scopes:
            Mapping of installation path to its declared scopes.
    """

    root_meta = packages.get("", {})

    direct_paths: set[str] = set()
    path_to_scopes: dict[str, set[str]] = {}

    sections = (
        ("dependencies", "prod"),
        ("devDependencies", "dev"),
        ("optionalDependencies", "optional"),
        ("peerDependencies", "peer"),
    )

    for section, scope in sections:
        for name in root_meta.get(section, {}):
            install_path = f"node_modules/{name}"

            direct_paths.add(install_path)
            path_to_scopes.setdefault(install_path, set()).add(scope)

    return direct_paths, path_to_scopes


def _scope_for_package(
    path: str,
    packages: dict[str, dict[str, Any]],
    path_to_scopes: dict[str, set[str]],
) -> set[str]:
    """
    Return the declared scopes for a direct dependency.

    The packages parameter is retained for compatibility with the
    existing graph-engine interface.
    """

    return path_to_scopes.get(path, set()).copy()


# ---------------------------------------------------------------------------
# npm dependency resolution
# ---------------------------------------------------------------------------

def _ancestor_paths(start_path: str) -> list[str]:
    """
    Return node_modules directories from nearest to farthest.

    Example:

        start_path:
            node_modules/a/node_modules/b

        Result:
            1. node_modules/a/node_modules/b/node_modules
            2. node_modules/a/node_modules
            3. node_modules
    """

    parts = [part for part in start_path.split("/") if part]

    candidates = [f"{start_path}/node_modules"]

    # Find actual node_modules ancestor directories.
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == "node_modules":
            candidates.append("/".join(parts[:index + 1]))

    # Remove duplicates without changing search order.
    return list(dict.fromkeys(candidates))


def _find_nearest_install(
    parent_path: str,
    dep_name: str,
    packages: dict[str, dict[str, Any]],
) -> str | None:
    """
    Find the nearest installed dependency relative to a parent package.

    npm searches the closest node_modules directory first, then
    continues towards the project root.
    """

    for candidate_root in _ancestor_paths(parent_path):
        candidate_path = f"{candidate_root}/{dep_name}"

        if candidate_path in packages:
            return candidate_path

    return None


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_dependency_graph(lockfile_path: str | Path) -> Graph:
    """
    Build a directed dependency graph from an npm v2/v3 lockfile.

    Every package installation path becomes a separate graph node.

    A synthetic <root> node represents the project itself.
    """

    packages = parse_lockfile(lockfile_path)

    direct_paths, path_to_scopes = (
        _determine_direct_paths_and_scopes(packages)
    )

    graph = nx.DiGraph()

    root_node = "<root>"

    # Add synthetic root.
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

    # -----------------------------------------------------------------------
    # Add package nodes
    # -----------------------------------------------------------------------

    for path, meta in packages.items():

        if path == "":
            continue

        node_attrs: NodeAttrs = {
            "name": meta["name"],
            "version": meta["version"],
            "path": path,
            "direct": path in direct_paths,
            "scope": (
                _scope_for_package(path, packages, path_to_scopes)
                if path in direct_paths
                else set()
            ),
            "parents": [],
            "depth": -1,
        }

        graph.add_node(path, **node_attrs)

    # -----------------------------------------------------------------------
    # Resolve package-to-package dependency edges
    # -----------------------------------------------------------------------

    dependency_sections = (
        ("dependencies", "prod"),
        ("devDependencies", "dev"),
        ("optionalDependencies", "optional"),
        ("peerDependencies", "peer"),
    )

    for parent_path, meta in packages.items():

        if parent_path == "":
            continue

        for section, dep_type in dependency_sections:

            dep_map = meta.get(section, {})

            if not isinstance(dep_map, dict):
                continue

            for dep_name in dep_map:

                child_path = _find_nearest_install(
                    parent_path,
                    dep_name,
                    packages,
                )

                # Missing dependencies or unresolved peers are skipped.
                if child_path is None:
                    continue

                # Merge dependency types if the same edge is declared
                # under more than one dependency section.
                if graph.has_edge(parent_path, child_path):

                    existing = graph.edges[parent_path, child_path].get(
                        "dep_type",
                        set(),
                    )

                    if not isinstance(existing, set):
                        existing = {existing}

                    existing.add(dep_type)

                    graph.edges[parent_path, child_path][
                        "dep_type"
                    ] = existing

                else:

                    graph.add_edge(
                        parent_path,
                        child_path,
                        dep_type={dep_type},
                    )

                # Record each parent only once.
                parents = graph.nodes[child_path]["parents"]

                if parent_path not in parents:
                    parents.append(parent_path)

    # -----------------------------------------------------------------------
    # Connect direct dependencies to the synthetic root
    # -----------------------------------------------------------------------

    for path in direct_paths:

        if path not in graph:
            continue

        edge_types = path_to_scopes.get(path, {"prod"})

        graph.add_edge(
            root_node,
            path,
            dep_type=set(edge_types),
        )

        parents = graph.nodes[path]["parents"]

        if root_node not in parents:
            parents.append(root_node)

    # -----------------------------------------------------------------------
    # Scope propagation
    # -----------------------------------------------------------------------

    """
    A direct dependency can belong to multiple scopes.

    Example:

        Root
          |
          | dev
          v
          A
          |
          v
          B

    B inherits the dev scope from A.

    If B is also reachable through a production dependency,
    B will contain both prod and dev scopes.

    We repeat propagation until no node receives a new scope.
    """

    changed = True

    while changed:

        changed = False

        for parent, child, _ in graph.edges(data=True):

            parent_scope = graph.nodes[parent]["scope"]
            child_scope = graph.nodes[child]["scope"]

            new_scope = child_scope.union(parent_scope)

            if new_scope != child_scope:

                graph.nodes[child]["scope"] = new_scope
                changed = True

    # -----------------------------------------------------------------------
    # Compute shortest dependency depth from root
    # -----------------------------------------------------------------------

    for node in graph.nodes:

        if node == root_node:
            continue

        try:
            depth = nx.shortest_path_length(
                graph,
                source=root_node,
                target=node,
            )

        except nx.NetworkXNoPath:
            depth = -1

        graph.nodes[node]["depth"] = depth

    return graph


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_all_nodes(graph: Graph) -> list[NodeAttrs]:
    """
    Return all package node attributes, excluding the synthetic root.
    """

    return [
        attrs
        for node_id, attrs in graph.nodes(data=True)
        if node_id != "<root>"
    ]


def get_node_info(graph: Graph, node_id: str) -> NodeAttrs:
    """
    Retrieve attributes for a package node.

    Raises:
        KeyError: If the requested node does not exist.
    """

    if node_id not in graph:
        raise KeyError(
            f"Node {node_id!r} not found in dependency graph"
        )

    return graph.nodes[node_id]


def get_all_paths(
    graph: Graph,
    target_node: str,
    limit: int = 1000,
) -> list[list[str]]:
    """
    Return up to `limit` simple paths from root to a target package.

    The limit prevents excessive path enumeration in large graphs.
    """

    root = "<root>"

    if target_node not in graph:
        raise KeyError(
            f"Target node {target_node!r} not in graph"
        )

    if limit <= 0:
        return []

    paths: list[list[str]] = []

    for path in nx.all_simple_paths(
        graph,
        source=root,
        target=target_node,
    ):

        if len(paths) >= limit:
            break

        paths.append(path)

    return paths


# ---------------------------------------------------------------------------
# Manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m app.services.graph_engine "
            "<package-lock.json>"
        )
        sys.exit(1)

    graph = build_dependency_graph(sys.argv[1])

    print(
        f"Graph built – {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges"
    )

    for node in list_all_nodes(graph)[:5]:
        print(node)

