"""Scoring rubric engine: load YAML rubric and compute per-dimension scores."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DimensionScore:
    """Score for a single rubric dimension."""

    dimension: str
    score: int  # 1-5
    weight: float
    weighted_score: float
    rationale: str = ""


@dataclass
class RubricResult:
    """Complete rubric scoring result for one evaluation."""

    dimension_scores: list[DimensionScore]
    total_weighted_score: float
    max_possible: float
    normalized_score: float  # 0.0 - 1.0


class RubricEngine:
    """Load a YAML rubric and score evaluation results."""

    def __init__(self, rubric_path: str | Path) -> None:
        self._rubric_path = Path(rubric_path)
        with open(self._rubric_path) as f:
            self._rubric = yaml.safe_load(f)
        self._dimensions: dict[str, dict[str, Any]] = self._rubric.get("dimensions", {})

    @property
    def dimension_names(self) -> list[str]:
        return list(self._dimensions.keys())

    @property
    def total_weight(self) -> float:
        return sum(d["weight"] for d in self._dimensions.values())

    def score(
        self, scores: dict[str, int], rationales: dict[str, str] | None = None
    ) -> RubricResult:
        """Score a set of dimension scores (1-5) against the rubric.

        Args:
            scores: {dimension_name: score} where score is 1-5.
            rationales: Optional {dimension_name: rationale_text}.
        """
        rationales = rationales or {}
        dimension_scores: list[DimensionScore] = []

        for name, dim_config in self._dimensions.items():
            raw = scores.get(name, 0)
            if not 1 <= raw <= 5:
                raise ValueError(f"Score for '{name}' must be 1-5, got {raw}")
            weight = dim_config["weight"]
            dimension_scores.append(
                DimensionScore(
                    dimension=name,
                    score=raw,
                    weight=weight,
                    weighted_score=raw * weight,
                    rationale=rationales.get(name, ""),
                )
            )

        total = sum(ds.weighted_score for ds in dimension_scores)
        max_possible = 5.0 * self.total_weight

        return RubricResult(
            dimension_scores=dimension_scores,
            total_weighted_score=total,
            max_possible=max_possible,
            normalized_score=total / max_possible if max_possible > 0 else 0.0,
        )
