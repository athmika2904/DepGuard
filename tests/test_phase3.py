import pytest

from app.services import phase3


@pytest.mark.asyncio
async def test_run_scan_deduplicates_package_versions_and_enriches_paths(monkeypatch, tmp_path):
    lockfile = {
        "name": "scan-demo",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "scan-demo",
                "version": "1.0.0",
                "dependencies": {"left": "1.0.0", "right": "1.0.0"},
            },
            "node_modules/left": {
                "name": "left",
                "version": "1.0.0",
                "dependencies": {"shared": "1.0.0"},
            },
            "node_modules/right": {
                "name": "right",
                "version": "1.0.0",
                "dependencies": {"shared": "1.0.0"},
            },
            "node_modules/shared": {
                "name": "shared",
                "version": "1.0.0",
            },
        },
    }
    path = tmp_path / "package-lock.json"
    import json
    path.write_text(json.dumps(lockfile), encoding="utf-8")

    calls = []

    async def fake_query(packages):
        calls.append(packages)
        from app.models.vulnerability import Vulnerability
        return {
            ("shared", "1.0.0"): [
                Vulnerability(
                    id="GHSA-demo",
                    package_name="shared",
                    installed_version="1.0.0",
                )
            ],
            ("left", "1.0.0"): [],
            ("right", "1.0.0"): [],
        }, {}

    monkeypatch.setattr(phase3, "query_vulnerabilities", fake_query)

    result = await phase3.run_scan(str(path))

    assert result.status == "complete"
    assert len(calls) == 1
    assert calls[0] == {
        ("left", "1.0.0"),
        ("right", "1.0.0"),
        ("shared", "1.0.0"),
    }
    finding = result.vulnerabilities["node_modules/shared"][0]
    assert finding.id == "GHSA-demo"
    assert len(finding.dependency_paths) == 2
    assert finding.direct is False
    assert finding.dependency_depth == 2


@pytest.mark.asyncio
async def test_run_scan_returns_partial_when_lookup_fails(monkeypatch, tmp_path):
    lockfile = {
        "name": "partial-demo",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "partial-demo",
                "version": "1.0.0",
                "dependencies": {"pkg-a": "1.0.0", "pkg-b": "2.0.0"},
            },
            "node_modules/pkg-a": {"name": "pkg-a", "version": "1.0.0"},
            "node_modules/pkg-b": {"name": "pkg-b", "version": "2.0.0"},
        },
    }
    import json
    path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(lockfile), encoding="utf-8")

    async def fake_query(packages):
        return {
            ("pkg-a", "1.0.0"): [],
        }, {
            ("pkg-b", "2.0.0"): "OSV request failed with HTTP 503",
        }

    monkeypatch.setattr(phase3, "query_vulnerabilities", fake_query)

    result = await phase3.run_scan(str(path))

    assert result.status == "partial"
    assert result.errors == {
        ("pkg-b", "2.0.0"): "OSV request failed with HTTP 503"
    }
    assert result.vulnerabilities == {}


@pytest.mark.asyncio
async def test_run_scan_returns_complete_for_no_vulnerabilities(monkeypatch, tmp_path):
    lockfile = {
        "name": "clean-demo",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "clean-demo",
                "version": "1.0.0",
                "dependencies": {"safe": "1.0.0"},
            },
            "node_modules/safe": {"name": "safe", "version": "1.0.0"},
        },
    }
    import json
    path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(lockfile), encoding="utf-8")

    async def fake_query(packages):
        return {("safe", "1.0.0"): []}, {}

    monkeypatch.setattr(phase3, "query_vulnerabilities", fake_query)

    result = await phase3.run_scan(str(path))

    assert result.status == "complete"
    assert result.vulnerabilities == {}
    assert result.errors == {}


@pytest.mark.asyncio
async def test_run_scan_adds_risk_assessment_and_summary(monkeypatch, tmp_path):
    lockfile = {
        "name": "risk-demo",
        "lockfileVersion": 3,
        "packages": {
            "": {
                "name": "risk-demo",
                "version": "1.0.0",
                "dependencies": {"demo": "1.0.0"},
            },
            "node_modules/demo": {"name": "demo", "version": "1.0.0"},
        },
    }
    import json
    path = tmp_path / "package-lock.json"
    path.write_text(json.dumps(lockfile), encoding="utf-8")

    async def fake_query(packages):
        from app.models.vulnerability import Vulnerability
        return {
            ("demo", "1.0.0"): [
                Vulnerability(
                    id="GHSA-risk-test",
                    package_name="demo",
                    installed_version="1.0.0",
                    severity=[{
                        "type": "CVSS_V3",
                        "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    }],
                    fixed_versions=["1.0.1"],
                )
            ]
        }, {}

    monkeypatch.setattr(phase3, "query_vulnerabilities", fake_query)
    result = await phase3.run_scan(str(path))

    finding = result.vulnerabilities["node_modules/demo"][0]
    assert finding.risk_score is not None
    assert finding.risk_level == "critical"
    assert finding.score_confidence == "high"
    assert result.risk_summary["critical"] == 1
    assert result.risk_summary["total"] == 1
