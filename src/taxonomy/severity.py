"""Severity level definitions and utilities."""

from __future__ import annotations

from enum import IntEnum

from ..utils.logging import get_logger

logger = get_logger("taxonomy.severity")


class Severity(IntEnum):
    BENIGN = 0
    BORDERLINE = 1
    SEVERE = 2
    CRITICAL = 3

    @classmethod
    def from_string(cls, value: str) -> Severity:
        try:
            return cls[value.upper()]
        except KeyError:
            valid = [s.name.lower() for s in cls]
            raise ValueError(f"Invalid severity {value!r}. Valid: {valid}") from None

    def to_string(self) -> str:
        return self.name.lower()


def severity_distance(a: str, b: str) -> int:
    return abs(Severity.from_string(a) - Severity.from_string(b))
