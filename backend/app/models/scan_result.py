
from typing import Any, Literal

from pydantic import BaseModel, Field

from .vulnerability import Vulnerability


class ScanResultModel(BaseModel):
    status: Literal["complete", "partial"]

    vulnerabilities: dict[str, list[Vulnerability]] = Field(
        default_factory=dict
    )

    errors: dict[str, str] = Field(
        default_factory=dict
    )

    graph: dict[str, Any] | None = None
    risk_summary: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unknown": 0,
            "total": 0,
        }
    )
