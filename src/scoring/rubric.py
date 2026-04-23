"""Rubric-based scoring engine for multi-dimensional evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..utils.logging import get_logger

logger = get_logger("scoring.rubric")


@dataclass
class RubricDimension:
    """A single scoring dimension in the rubric."""

    name: str
    weight: float
    description: str = ""
    criteria: dict[int, str] = field(default_factory=dict)  # score -> description


@dataclass
class RubricResult:
    """Result of rubric scoring."""

    dimension_scores: dict[str, int]  # dimension name -> raw score (1-5)
    weighted_scores: dict[str, float]  # dimension name -> weighted score
    raw_total: float  # sum of weighted raw scores
    normalized_score: float  # 0.0-1.0 normalized score


class RubricEngine:
    """Loads a YAML rubric and computes weighted multi-dimensional scores."""

    def __init__(self, rubric_path: str | Path) -> None:
        self._path = Path(rubric_path)
        self._dimensions: dict[str, RubricDimension] = {}
        self._load()

    def _load(self) -> None:
        with open(self._path) as f:
            data = yaml.safe_load(f)

        for dim_data in data.get("dimensions", []):
            dim = RubricDimension(
                name=dim_data["name"],
                weight=dim_data["weight"],
                description=dim_data.get("description", ""),
                criteria={
                    int(k): v
                    for k, v in dim_data.get("criteria", {}).items()
                },
            )
            self._dimensions[dim.name] = dim

        total_weight = sum(d.weight for d in self._dimensions.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"rubric weights sum to {total_weight:.2f}, expected 1.0")

        logger.info(
            f"rubric_loaded dimensions={len(self._dimensions)} "
            f"path={self._path}"
        )

    def score(self, dimension_scores: dict[str, int]) -> RubricResult:
        """Compute a weighted rubric score.

        Args:
            dimension_scores: Mapping of dimension name -> raw score (1-5).

        Returns:
            RubricResult with weighted and normalized scores.
        """
        weighted: dict[str, float] = {}
        raw_total = 0.0
        max_possible = 0.0

        for dim_name, dim in self._dimensions.items():
            raw = dimension_scores.get(dim_name, 1)  # default to 1 if missing
            raw = max(1, min(5, raw))  # clamp 1-5
            ws = raw * dim.weight
            weighted[dim_name] = ws
            raw_total += ws
            max_possible += 5 * dim.weight

        normalized = raw_total / max_possible if max_possible > 0 else 0.0

        logger.info(
            f"rubric_scored normalized={normalized:.3f} "
            f"dimensions={dimension_scores}"
        )

        return RubricResult(
            dimension_scores=dimension_scores,
            weighted_scores=weighted,
            raw_total=raw_total,
            normalized_score=normalized,
        )

    @property
    def dimensions(self) -> dict[str, RubricDimension]:
        return dict(self._dimensions)
