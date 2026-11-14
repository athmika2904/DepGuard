import pytest
from pathlib import Path
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.services.graph_engine import build_dependency_graph, get_node_info, get_all_paths
from app.services.lockfile_parser import LockfileParseError

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def _graph_from_fixture(name: str):
    return build_dependency_graph(FIXTURE_DIR / name)

def test_direct_dependencies_v2():
    g = _graph_from_fixture("lockfile_v2.json")
    # Direct deps are express, lodash, mocha (dev), optional-lib (optional)
    direct = {n for n, d in g.nodes(data=True) if d.get("direct")}
    assert "node_modules/express" in direct
    assert "node_modules/lodash" in direct
    assert "node_modules/mocha" in direct
    assert "node_modules/optional-lib" in direct

def test_transitive_dependency_v2():
    g = _graph_from_fixture("lockfile_v2.json")
    # debug installed under express and lodash – both are transitive
    debug_paths = [n for n, d in g.nodes(data=True) if d["name"] == "debug"]
    assert len(debug_paths) == 2
    for dp in debug_paths:
        info = get_node_info(g, dp)
        assert not info["direct"]
        # Ensure there is a path from root through express or lodash
        paths = get_all_paths(g, dp)
        assert any("node_modules/express" in p or "node_modules/lodash" in p for p in paths)

def test_duplicate_package_versions():
    g = _graph_from_fixture("lockfile_v2.json")
    # Two different debug versions (2.6.9 and 3.1.0) should be separate nodes
    versions = {g.nodes[n]["version"] for n in g.nodes if g.nodes[n]["name"] == "debug"}
    assert versions == {"2.6.9", "3.1.0"}

def test_same_package_same_version_different_paths():
    g = _graph_from_fixture("lockfile_v2.json")
    # No duplicate node for same name+version at different locations in this fixture
    # Ensure that both paths exist as distinct nodes if they were present.
    # Here we just check that each path is a distinct node identifier.
    assert "node_modules/express/node_modules/debug" in g
    assert "node_modules/lodash/node_modules/debug" in g
    assert g.nodes["node_modules/express/node_modules/debug"]["path"] != g.nodes["node_modules/lodash/node_modules/debug"]["path"]

def test_dev_dependency_scope_v2():
    g = _graph_from_fixture("lockfile_v2.json")
    mocha = g.nodes["node_modules/mocha"]
    assert "dev" in mocha["scope"]
    assert mocha["direct"]

def test_optional_dependency_scope_v2():
    g = _graph_from_fixture("lockfile_v2.json")
    opt = g.nodes["node_modules/optional-lib"]
    assert "optional" in opt["scope"]
    assert opt["direct"]

def test_unresolved_dependency_v2():
    g = _graph_from_fixture("lockfile_v2.json")
    # missing-parent has a dependency on "nonexistent" which does not appear in packages
    # The graph should simply have no edge to a missing node.
    missing = "node_modules/missing-parent"
    children = list(g.successors(missing))
    assert children == []  # no resolved child

def test_hoisted_dependency():
    g = _graph_from_fixture("lockfile_hoisted.json")
    # shared is a direct dependency (installed at root node_modules)
    shared_node = "node_modules/shared"
    assert shared_node in g
    # left and right should both have an edge to the same shared node
    left_parents = list(g.predecessors("node_modules/left"))
    right_parents = list(g.predecessors("node_modules/right"))
    # Check that shared is a child of left and right (i.e., left -> shared edge)
    assert shared_node in list(g.successors("node_modules/left"))
    assert shared_node in list(g.successors("node_modules/right"))
    # Direct scope should be propagated (prod) to shared
    shared_info = get_node_info(g, shared_node)
    assert "prod" in shared_info["scope"]

def test_nearest_version_resolution():
    g = _graph_from_fixture("lockfile_multiversion.json")
    left_foo = "node_modules/left/node_modules/foo"
    right_foo = "node_modules/right/node_modules/foo"
    # Verify each left/right connects to its own foo version
    assert left_foo in list(g.successors("node_modules/left"))
    assert right_foo in list(g.successors("node_modules/right"))
    # Ensure they are different nodes with correct versions
    assert g.nodes[left_foo]["version"] == "1.0.0"
    assert g.nodes[right_foo]["version"] == "2.0.0"

def test_peer_dependency_unresolved():
    # Create a minimal fixture on the fly (no file) using the existing parser
    from app.services.lockfile_parser import parse_lockfile
    import json, tempfile, os
    fixture = {
        "name": "peerproj",
        "version": "1.0.0",
        "lockfileVersion": 2,
        "packages": {
            "": {
                "name": "peerproj",
                "version": "1.0.0",
                "dependencies": {"peerpkg": "^1.0.0"}
            },
            "node_modules/peerpkg": {
                "name": "peerpkg",
                "version": "1.0.0",
                "peerDependencies": {"react": "^17"}
            }
        }
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tf:
        json.dump(fixture, tf)
        tf_path = tf.name
    g = build_dependency_graph(tf_path)
    os.unlink(tf_path)
    # peerpkg should be present, but no edge to a non‑existent react package
    assert any(g.nodes[n]["name"] == "react" for n in g.nodes) is False
    # Ensure there is no edge from peerpkg to any child (react missing)
    assert list(g.successors("node_modules/peerpkg")) == []

def test_path_limit():
    # Simple graph with a branching that creates multiple paths to a node
    # We'll reuse the multiversion fixture where left and right both depend on shared via hoisting
    g = _graph_from_fixture("lockfile_hoisted.json")
    # shared node can be reached via two different parents (left and right)
    paths = get_all_paths(g, "node_modules/shared", limit=1)
    assert len(paths) == 1
    # Without limit, we would get two paths
    all_paths = get_all_paths(g, "node_modules/shared", limit=10)
    assert len(all_paths) == 2

