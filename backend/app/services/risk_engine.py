"""Explainable, deterministic risk scoring for OSV findings.

This scoring version uses CVSS v3.x base severity, dependency directness,
and release-line-compatible remediation information. EPSS and package-health
signals are not scored because this project snapshot does not yet retrieve
those datasets.

Missing inputs are omitted and the remaining weights are normalized.
Missing CVSS means the risk score is unknown rather than zero.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from ..models.vulnerability import Vulnerability

RiskLevel = Literal["critical", "high", "medium", "low", "unknown"]

# Weights are heuristic project parameters, not an industry-standard formula.
WEIGHTS = {
    "cvss": 0.70,
    "directness": 0.20,
    "remediation": 0.10,
}

_LEVELS: tuple[tuple[float, RiskLevel], ...] = (
    (90.0, "critical"),
    (70.0, "high"),
    (40.0, "medium"),
    (0.0, "low"),
)


def _round_up_one_decimal(value: float) -> float:
    """CVSS-style round-up to one decimal place."""
    return math.ceil((value * 10.0) - 1e-10) / 10.0


def _cvss_v3_base_score(vector: str) -> float | None:
    """Calculate a CVSS v3.0/v3.1 base score from a complete base vector."""
    if (
        not isinstance(vector, str)
        or not vector.startswith(("CVSS:3.0/", "CVSS:3.1/"))
    ):
        return None

    metrics: dict[str, str] = {}

    for part in vector.split("/")[1:]:
        if ":" not in part:
            return None

        key, value = part.split(":", 1)
        metrics[key] = value

    required = {
        "AV", "AC", "PR", "UI",
        "S", "C", "I", "A",
    }

    if not required.issubset(metrics):
        return None

    av_values = {
        "N": 0.85,
        "A": 0.62,
        "L": 0.55,
        "P": 0.20,
    }

    ac_values = {
        "L": 0.77,
        "H": 0.44,
    }

    ui_values = {
        "N": 0.85,
        "R": 0.62,
    }

    impact_values = {
        "H": 0.56,
        "L": 0.22,
        "N": 0.0,
    }

    av = av_values.get(metrics["AV"])
    ac = ac_values.get(metrics["AC"])
    ui = ui_values.get(metrics["UI"])

    scope = metrics["S"]

    confidentiality = impact_values.get(metrics["C"])
    integrity = impact_values.get(metrics["I"])
    availability = impact_values.get(metrics["A"])

    if None in (
        av,
        ac,
        ui,
        confidentiality,
        integrity,
        availability,
    ):
        return None

    if scope not in {"U", "C"}:
        return None

    if scope == "U":
        pr_values = {
            "N": 0.85,
            "L": 0.62,
            "H": 0.27,
        }
    else:
        pr_values = {
            "N": 0.85,
            "L": 0.68,
            "H": 0.50,
        }

    pr = pr_values.get(metrics["PR"])

    if pr is None:
        return None

    impact_sub_score = 1.0 - (
        (1.0 - confidentiality)
        * (1.0 - integrity)
        * (1.0 - availability)
    )

    if impact_sub_score <= 0:
        return 0.0

    if scope == "U":
        impact = 6.42 * impact_sub_score
    else:
        impact = (
            7.52 * (impact_sub_score - 0.029)
            - 3.25 * ((impact_sub_score - 0.02) ** 15)
        )

    exploitability = 8.22 * av * ac * pr * ui

    if scope == "U":
        base_score = min(
            impact + exploitability,
            10.0,
        )
    else:
        base_score = min(
            1.08 * (impact + exploitability),
            10.0,
        )

    return _round_up_one_decimal(base_score)


def extract_cvss_score(severity: Any) -> float | None:
    """
    Extract a numeric CVSS base score or calculate a CVSS v3 vector score.

    Unsupported vectors (including CVSS v4) return None instead of being
    guessed or treated as zero.
    """
    if not isinstance(severity, list):
        return None

    for item in severity:
        if isinstance(item, dict):
            score = item.get("score")

            if (
                isinstance(score, (int, float))
                and not isinstance(score, bool)
            ):
                if 0.0 <= float(score) <= 10.0:
                    return float(score)

            if isinstance(score, str):
                try:
                    numeric = float(score)
                except ValueError:
                    numeric = None

                if (
                    numeric is not None
                    and 0.0 <= numeric <= 10.0
                ):
                    return numeric

                parsed = _cvss_v3_base_score(score)

                if parsed is not None:
                    return parsed

        elif isinstance(item, str):
            parsed = _cvss_v3_base_score(item)

            if parsed is not None:
                return parsed

    return None


def cvss_severity(
    score: float,
) -> Literal["critical", "high", "medium", "low", "none"]:
    """Map a CVSS v3 base score to its conventional severity band."""
    if score >= 9.0:
        return "critical"

    if score >= 7.0:
        return "high"

    if score >= 4.0:
        return "medium"

    if score > 0.0:
        return "low"

    return "none"


def _risk_level(score: float) -> RiskLevel:
    for threshold, level in _LEVELS:
        if score >= threshold:
            return level

    return "low"


def assess_vulnerability(
    vulnerability: Vulnerability,
    *,
    direct: bool | None = None,
) -> dict[str, Any]:
    """Return a transparent risk assessment for one installed finding."""
    is_direct = (
        vulnerability.direct
        if direct is None
        else direct
    )

    cvss_score = extract_cvss_score(
        vulnerability.severity
    )

    factors: dict[str, float] = {}
    reasons: list[str] = []

    if cvss_score is not None:
        factors["cvss"] = (
            cvss_score / 10.0
        ) * 100.0

        reasons.append(
            f"CVSS base score is {cvss_score:.1f}/10 "
            f"({cvss_severity(cvss_score)} severity)"
        )

    else:
        reasons.append(
            "CVSS score is unavailable or uses an unsupported format"
        )

    if is_direct is not None:
        factors["directness"] = (
            100.0 if is_direct else 60.0
        )

        reasons.append(
            "Package is a direct dependency"
            if is_direct
            else "Package is a transitive dependency"
        )

    # Prefer release-line-compatible fixes computed from OSV SEMVER ranges.
    # Fall back to raw fixed_versions only for older/manual model instances
    # that do not carry a remediation_status.
    if vulnerability.remediation_status is not None:
        compatible_fixes = (
            vulnerability.recommended_fixed_versions or []
        )

        if vulnerability.remediation_status == "fix_available":
            factors["remediation"] = 25.0

            reasons.append(
                "A compatible fixed version for the installed release line: "
                + ", ".join(compatible_fixes)
            )

        elif vulnerability.remediation_status == "no_fix_available":
            factors["remediation"] = 100.0

            reasons.append(
                "The installed version is affected, but OSV reports no fixed "
                "version for its matching release range"
            )

        else:
            reasons.append(
                "A compatible fixed version could not be determined from "
                "the available OSV range data"
            )

    elif vulnerability.fixed_versions is not None:
        # Backward compatibility for manually constructed/older model objects.
        if vulnerability.fixed_versions:
            factors["remediation"] = 25.0

            reasons.append(
                "OSV reports a fixed version (raw advisory data): "
                + ", ".join(vulnerability.fixed_versions)
            )

        else:
            factors["remediation"] = 100.0

            reasons.append(
                "OSV explicitly reports no fixed version"
            )

    if cvss_score is None:
        score = None
        level: RiskLevel = "unknown"
        confidence: Literal["high", "medium", "low"] = "low"

    else:
        available_weight = sum(
            WEIGHTS[name]
            for name in factors
        )

        weighted_total = sum(
            factors[name] * WEIGHTS[name]
            for name in factors
        )

        score = round(
            weighted_total / available_weight,
            1,
        )

        level = _risk_level(score)

        confidence = (
            "high"
            if len(factors) == 3
            else "medium"
        )

    if (
        vulnerability.remediation_status is None
        and vulnerability.fixed_versions is None
    ):
        reasons.append(
            "No fixed-version information was supplied by OSV"
        )

    if vulnerability.dependency_depth is not None:
        reasons.append(
            f"Shortest dependency depth is "
            f"{vulnerability.dependency_depth}"
        )

    return {
        "cvss_score": cvss_score,
        "cvss_severity": (
            cvss_severity(cvss_score)
            if cvss_score is not None
            else None
        ),
        "risk_score": score,
        "risk_level": level,
        "risk_factors": factors,
        "risk_reasons": reasons,
        "score_confidence": confidence,
    }


def summarize_risks(
    vulnerabilities: dict[str, list[Vulnerability]],
) -> dict[str, int]:
    """Count findings by risk level (each installed-path finding counted once)."""
    summary = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0,
        "total": 0,
    }

    for findings in vulnerabilities.values():
        for finding in findings:
            level = finding.risk_level or "unknown"

            if level not in summary or level == "total":
                level = "unknown"

            summary[level] += 1
            summary["total"] += 1

    return summary
