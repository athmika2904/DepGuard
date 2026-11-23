
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend"),
)

import networkx as nx
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def valid_lockfile():
    return {
        "name": "demo",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "demo",
                "version": "1.0.0",
                "dependencies": {},
            }
        },
    }


def upload_lockfile(content: bytes):
    return client.post(
        "/api/scan",
        files={
            "lockfile": (
                "package-lock.json",
                content,
                "application/json",
            )
        },
    )


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Invalid input tests
# ---------------------------------------------------------------------------

def test_invalid_json():
    response = upload_lockfile(b"{invalid json")

    assert response.status_code == 400


def test_invalid_lockfile_structure():
    response = upload_lockfile(
        b'{"hello": "world"}'
    )

    assert response.status_code == 400


def test_unsupported_lockfile_version():
    lockfile = valid_lockfile()
    lockfile["lockfileVersion"] = 1

    response = upload_lockfile(
        json.dumps(lockfile).encode()
    )

    assert response.status_code == 400


def test_missing_root_package_entry():
    lockfile = valid_lockfile()
    lockfile["packages"] = {
        "node_modules/express": {
            "name": "express",
            "version": "4.18.0",
        }
    }

    response = upload_lockfile(
        json.dumps(lockfile).encode()
    )

    assert response.status_code == 400


def test_oversized_upload():
    response = upload_lockfile(
        b"x" * (5 * 1024 * 1024 + 1)
    )

    assert response.status_code == 413


# ---------------------------------------------------------------------------
# Successful scan test
# ---------------------------------------------------------------------------

def test_scan_success(monkeypatch):

    async def fake_run_scan(path):

        graph = nx.DiGraph()

        graph.add_node(
            "<root>",
            name="<root>",
            version="",
            scope=set(),
        )

        return SimpleNamespace(
            status="complete",
            vulnerabilities={},
            errors={},
            graph=graph,
        )

    monkeypatch.setattr(
        "app.main.run_scan",
        fake_run_scan,
    )

    response = upload_lockfile(
        json.dumps(valid_lockfile()).encode()
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "complete"
    assert body["vulnerabilities"] == {}
    assert body["errors"] == {}

    assert "nodes" in body["graph"]
    assert "edges" in body["graph"]

