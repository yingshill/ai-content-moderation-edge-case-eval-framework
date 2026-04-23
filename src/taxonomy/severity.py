"""Severity level definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    """Ordered severity levels for content moderation."""

    BENIGN = 0
    BORDERLINE = 1
    SEVERE = 2
    CRITICAL = 3


@dataclass(frozen=True)
class SeverityLevel:
    severity: Severity
    label: str
    description: str
    expected_action: str


SEVERITY_LEVELS: dict[str, SeverityLevel] = {
    "benign": SeverityLevel(
        severity=Severity.BENIGN,
        label="Benign",
        description="Content does not violate any policies.",
        expected_action="allow",
    ),
    "borderline": SeverityLevel(
        severity=Severity.BORDERLINE,
        label="Borderline",
        description="Content is ambiguous; reasonable reviewers may disagree.",
        expected_action="flag_for_review",
    ),
    "severe": SeverityLevel(
        severity=Severity.SEVERE,
        label="Severe",
        description="Content clearly violates policies.",
        expected_action="remove",
    ),
    "critical": SeverityLevel(
        severity=Severity.CRITICAL,
        label="Critical",
        description="Content poses immediate safety risk (CSAM, imminent violence, etc).",
        expected_action="remove_and_escalate",
    ),
}


def parse_severity(s: str) -> Severity:
    """Convert a severity string to enum."""
    try:
        return Severity[s.upper()]
    except KeyError:
        raise ValueError(f"Unknown severity: {s!r}") from None
