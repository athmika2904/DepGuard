import pytest

from app.models.vulnerability import Vulnerability

from app.services.risk_engine import (
    _cvss_v3_base_score,
    assess_vulnerability,
    extract_cvss_score,
    summarize_risks,
)


def make_vulnerability(**overrides):
    data = {
        "id": "GHSA-test-1234",
        "package_name": "demo-package",
        "installed_version": "1.0.0",
        "severity": [{
            "type": "CVSS_V3",
            "score": (
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
                "S:U/C:H/I:H/A:H"
            ),
        }],
        "direct": True,
        "fixed_versions": ["1.0.1"],
        "dependency_depth": 1,
    }

    data.update(overrides)

    return Vulnerability(**data)


def test_cvss_v31_vector_calculates_known_base_score():
    vector = (
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
        "S:U/C:H/I:H/A:H"
    )

    assert _cvss_v3_base_score(vector) == 9.8


def test_cvss_vector_with_no_impact_is_zero():
    vector = (
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
        "S:U/C:N/I:N/A:N"
    )

    assert _cvss_v3_base_score(vector) == 0.0


def test_cvss_parser_accepts_numeric_score():
    assert extract_cvss_score([
        {
            "type": "CVSS_V3",
            "score": "8.1",
        }
    ]) == 8.1


def test_unsupported_cvss_vector_is_unknown():
    assert extract_cvss_score([
        {
            "type": "CVSS_V4",
            "score": "CVSS:4.0/...",
        }
    ]) is None


def test_direct_finding_scores_higher_than_transitive_finding():
    direct = assess_vulnerability(
        make_vulnerability()
    )

    transitive = assess_vulnerability(
        make_vulnerability(direct=False)
    )

    assert direct["risk_score"] > transitive["risk_score"]

    assert direct["risk_level"] in {
        "critical",
        "high",
        "medium",
        "low",
    }

    assert "direct dependency" in direct["risk_reasons"][1]


def test_fixed_version_reduces_score_and_is_explained():
    with_fix = assess_vulnerability(
        make_vulnerability()
    )

    without_fix_data = assess_vulnerability(
        make_vulnerability(fixed_versions=None)
    )

    assert with_fix["risk_score"] < without_fix_data["risk_score"]

    assert any(
        "fixed version" in reason
        for reason in with_fix["risk_reasons"]
    )


def test_missing_cvss_is_unknown_not_zero():
    result = assess_vulnerability(
        make_vulnerability(severity=None)
    )

    assert result["risk_score"] is None
    assert result["risk_level"] == "unknown"
    assert result["score_confidence"] == "low"


def test_risk_summary_counts_findings_by_level():
    high = make_vulnerability()

    unknown = make_vulnerability(
        id="GHSA-unknown",
        severity=None,
    )

    high_assessment = assess_vulnerability(high)
    unknown_assessment = assess_vulnerability(unknown)

    high = high.model_copy(
        update=high_assessment
    )

    unknown = unknown.model_copy(
        update=unknown_assessment
    )

    assert summarize_risks({
        "node_modules/a": [high, unknown]
    }) == {
        "critical": 1,
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 1,
        "total": 2,
    }


def test_risk_score_is_bounded_between_zero_and_100():
    result = assess_vulnerability(
        make_vulnerability()
    )

    assert result["risk_score"] is not None

    assert (
        0.0 <= result["risk_score"] <= 100.0
    )


def test_explicit_empty_fixed_version_list_increases_risk():
    with_fix = assess_vulnerability(
        make_vulnerability(
            fixed_versions=["1.0.1"]
        )
    )

    no_fix = assess_vulnerability(
        make_vulnerability(
            fixed_versions=[]
        )
    )

    assert no_fix["risk_score"] > with_fix["risk_score"]

    assert any(
        "no fixed version" in reason
        for reason in no_fix["risk_reasons"]
    )


def test_risk_assessment_uses_compatible_fixes_not_raw_advisory_list():
    finding = make_vulnerability(
        installed_version="5.0.9",
        fixed_versions=[
            "1.1.19",
            "2.1.5",
            "3.0.7",
            "5.0.10",
        ],
        recommended_fixed_versions=["5.0.10"],
        remediation_status="fix_available",
    )

    result = assess_vulnerability(finding)

    assert result["cvss_score"] == 9.8
    assert result["cvss_severity"] == "critical"

    assert any(
        "5.0.10" in reason
        and "compatible fixed version" in reason
        for reason in result["risk_reasons"]
    )

    assert not any(
        "1.1.19" in reason
        or "2.1.5" in reason
        or "3.0.7" in reason
        for reason in result["risk_reasons"]
    )


def test_cvss_75_is_high_even_when_composite_risk_is_medium():
    finding = make_vulnerability(
        severity=[{
            "type": "CVSS_V3",
            "score": (
                "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/"
                "S:U/C:N/I:N/A:H"
            ),
        }],
        direct=False,
        recommended_fixed_versions=["1.0.1"],
        remediation_status="fix_available",
    )

    result = assess_vulnerability(finding)

    assert result["cvss_score"] == 7.5
    assert result["cvss_severity"] == "high"

    assert result["risk_score"] == 67.0
    assert result["risk_level"] == "medium"
