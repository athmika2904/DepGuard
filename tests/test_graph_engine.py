
import json
import os
import sys
import tempfile

from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend"),
)

from app.services.graph_engine import (
    build_dependency_graph,
    get_node_info,
    get_all_paths,
    _ancestor_paths,
)

from app.services.lockfile_parser import LockfileParseError


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _graph_from_fixture(name: str):
    return build_dependency_graph(FIXTURE_DIR / name)


# ---------------------------------------------------------------------------
# Existing graph tests
# ---------------------------------------------------------------------------

def test_direct_dependencies_v2():

    graph = _graph_from_fixture("lockfile_v2.json")

    direct = {
        node
        for node, data in graph.nodes(data=True)
        if data.get("direct")
    }

    assert "node_modules/express" in direct
    assert "node_modules/lodash" in direct
    assert "node_modules/mocha" in direct
    assert "node_modules/optional-lib" in direct


def test_transitive_dependency_v2():

    graph = _graph_from_fixture("lockfile_v2.json")

    debug_paths = [
        node
        for node, data in graph.nodes(data=True)
        if data["name"] == "debug"
    ]

    assert len(debug_paths) == 2

    for debug_path in debug_paths:

        info = get_node_info(graph, debug_path)

        assert not info["direct"]

        paths = get_all_paths(graph, debug_path)

        assert any(
            "node_modules/express" in path
            or "node_modules/lodash" in path
            for path in paths
        )


def test_duplicate_package_versions():

    graph = _graph_from_fixture("lockfile_v2.json")

    versions = {
        graph.nodes[node]["version"]
        for node in graph.nodes
        if graph.nodes[node]["name"] == "debug"
    }

    assert versions == {"2.6.9", "3.1.0"}


def test_same_package_same_version_different_paths():

    graph = _graph_from_fixture("lockfile_v2.json")

    express_debug = "node_modules/express/node_modules/debug"
    lodash_debug = "node_modules/lodash/node_modules/debug"

    assert express_debug in graph
    assert lodash_debug in graph

    assert (
        graph.nodes[express_debug]["path"]
        != graph.nodes[lodash_debug]["path"]
    )


def test_dev_dependency_scope_v2():

    graph = _graph_from_fixture("lockfile_v2.json")

    mocha = graph.nodes["node_modules/mocha"]

    assert "dev" in mocha["scope"]
    assert mocha["direct"]


def test_optional_dependency_scope_v2():

    graph = _graph_from_fixture("lockfile_v2.json")

    optional_package = graph.nodes[
        "node_modules/optional-lib"
    ]

    assert "optional" in optional_package["scope"]
    assert optional_package["direct"]


def test_unresolved_dependency_v2():

    graph = _graph_from_fixture("lockfile_v2.json")

    missing = "node_modules/missing-parent"

    children = list(graph.successors(missing))

    assert children == []


def test_hoisted_dependency():

    graph = _graph_from_fixture("lockfile_hoisted.json")

    shared_node = "node_modules/shared"

    assert shared_node in graph

    assert shared_node in list(
        graph.successors("node_modules/left")
    )

    assert shared_node in list(
        graph.successors("node_modules/right")
    )

    shared_info = get_node_info(graph, shared_node)

    assert "prod" in shared_info["scope"]


def test_nearest_version_resolution():

    graph = _graph_from_fixture("lockfile_multiversion.json")

    left_foo = "node_modules/left/node_modules/foo"
    right_foo = "node_modules/right/node_modules/foo"

    assert left_foo in list(
        graph.successors("node_modules/left")
    )

    assert right_foo in list(
        graph.successors("node_modules/right")
    )

    assert graph.nodes[left_foo]["version"] == "1.0.0"
    assert graph.nodes[right_foo]["version"] == "2.0.0"


def test_peer_dependency_unresolved(tmp_path):

    fixture = {
        "name": "peerproj",
        "version": "1.0.0",
        "lockfileVersion": 2,
        "packages": {
            "": {
                "name": "peerproj",
                "version": "1.0.0",
                "dependencies": {
                    "peerpkg": "^1.0.0"
                },
            },
            "node_modules/peerpkg": {
                "name": "peerpkg",
                "version": "1.0.0",
                "peerDependencies": {
                    "react": "^17"
                },
            },
        },
    }

    lockfile_path = tmp_path / "peer-lockfile.json"

    lockfile_path.write_text(
        json.dumps(fixture),
        encoding="utf-8",
    )

    graph = build_dependency_graph(lockfile_path)

    assert not any(
        graph.nodes[node]["name"] == "react"
        for node in graph.nodes
    )

    assert list(
        graph.successors("node_modules/peerpkg")
    ) == []


def test_path_limit():

    graph = _graph_from_fixture("lockfile_hoisted.json")

    paths = get_all_paths(
        graph,
        "node_modules/shared",
        limit=1,
    )

    assert len(paths) == 1

    all_paths = get_all_paths(
        graph,
        "node_modules/shared",
        limit=10,
    )

    # shared is declared directly by root and required by left and right.
    assert len(all_paths) == 3

    for path in all_paths:

        assert path[0] == "<root>"
        assert path[-1] == "node_modules/shared"

    assert [
        "<root>",
        "node_modules/shared",
    ] in all_paths


# ---------------------------------------------------------------------------
# New tests: nearest-ancestor resolution
# ---------------------------------------------------------------------------

def test_ancestor_paths_for_nested_package():

    paths = _ancestor_paths(
        "node_modules/a/node_modules/b"
    )

    assert paths == [
        "node_modules/a/node_modules/b/node_modules",
        "node_modules/a/node_modules",
        "node_modules",
    ]


def test_nearest_ancestor_install_wins(tmp_path):

    fixture = {
        "name": "nearest-project",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "nearest-project",
                "version": "1.0.0",
                "dependencies": {
                    "a": "^1.0.0",
                    "foo": "^2.0.0",
                },
            },
            "node_modules/a": {
                "name": "a",
                "version": "1.0.0",
                "dependencies": {
                    "foo": "^1.0.0",
                },
            },
            "node_modules/a/node_modules/foo": {
                "name": "foo",
                "version": "1.0.0",
            },
            "node_modules/foo": {
                "name": "foo",
                "version": "2.0.0",
            },
        },
    }

    lockfile_path = tmp_path / "nearest-lockfile.json"

    lockfile_path.write_text(
        json.dumps(fixture),
        encoding="utf-8",
    )

    graph = build_dependency_graph(lockfile_path)

    nested_foo = "node_modules/a/node_modules/foo"
    root_foo = "node_modules/foo"

    # Package A must resolve its own nearest foo installation.
    assert nested_foo in list(
        graph.successors("node_modules/a")
    )

    # It must not resolve the root-level foo instead.
    assert root_foo not in list(
        graph.successors("node_modules/a")
    )

    assert graph.nodes[nested_foo]["version"] == "1.0.0"
    assert graph.nodes[root_foo]["version"] == "2.0.0"


# ---------------------------------------------------------------------------
# Parser validation tests
# ---------------------------------------------------------------------------

def test_parser_rejects_non_object_lockfile(tmp_path):

    lockfile_path = tmp_path / "invalid-lockfile.json"

    lockfile_path.write_text(
        json.dumps(["not", "an", "object"]),
        encoding="utf-8",
    )

    with pytest.raises(LockfileParseError):
        build_dependency_graph(lockfile_path)


def test_parser_rejects_invalid_dependency_section(tmp_path):

    fixture = {
        "name": "invalid-project",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "invalid-project",
                "version": "1.0.0",
                "dependencies": [],
            }
        },
    }

    lockfile_path = tmp_path / "invalid-dependencies.json"

    lockfile_path.write_text(
        json.dumps(fixture),
        encoding="utf-8",
    )

    with pytest.raises(LockfileParseError):
        build_dependency_graph(lockfile_path)



