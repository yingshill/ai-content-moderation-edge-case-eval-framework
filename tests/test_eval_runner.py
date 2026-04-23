"""Tests for eval_runner: test suite loading, validation, metric wiring."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.eval_runner import (
    TestCase,
    EvalResult,
    load_test_suite,
    _metric_to_rubric_score,
    _compute_explanation_quality,
)
from src.providers.base import ModerationResult


# --- Test Suite Loading ---


class TestLoadTestSuite:
    def _write_jsonl(self, path: Path, records: list[dict]) -> None:
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    def test_load_valid_suite(self, tmp_path: Path):
        suite_file = tmp_path / "test.jsonl"
        self._write_jsonl(suite_file, [
            {
                "id": "tc-001",
                "content": "Test content",
                "ground_truth": {"harm_category": "harassment", "severity": "severe"},
            },
            {
                "id": "tc-002",
                "content": "Another test",
                "ground_truth": {"harm_category": None, "severity": "benign"},
            },
        ])
        cases = load_test_suite(suite_file)
        assert len(cases) == 2
        assert cases[0].id == "tc-001"
        assert cases[1].ground_truth["harm_category"] is None

    def test_load_directory(self, tmp_path: Path):
        sub = tmp_path / "edge_cases"
        sub.mkdir()
        self._write_jsonl(sub / "a.jsonl", [
            {"id": "a-1", "content": "A", "ground_truth": {"harm_category": None}},
        ])
        self._write_jsonl(sub / "b.jsonl", [
            {"id": "b-1", "content": "B", "ground_truth": {"harm_category": "spam"}},
        ])
        cases = load_test_suite(tmp_path)
        assert len(cases) == 2

    def test_skip_invalid_records(self, tmp_path: Path):
        suite_file = tmp_path / "test.jsonl"
        self._write_jsonl(suite_file, [
            {"id": "tc-001", "content": "Valid", "ground_truth": {}},
            {"content": "Missing id", "ground_truth": {}},  # Missing 'id'
            {"id": "tc-003"},  # Missing 'content' and 'ground_truth'
        ])
        cases = load_test_suite(suite_file)
        assert len(cases) == 1  # Only the first is valid

    def test_default_language(self, tmp_path: Path):
        suite_file = tmp_path / "test.jsonl"
        self._write_jsonl(suite_file, [
            {"id": "tc-001", "content": "Test", "ground_truth": {}},
        ])
        cases = load_test_suite(suite_file)
        assert cases[0].language == "en"

    def test_custom_language(self, tmp_path: Path):
        suite_file = tmp_path / "test.jsonl"
        self._write_jsonl(suite_file, [
            {"id": "tc-001", "content": "Test", "language": "zh", "ground_truth": {}},
        ])
        cases = load_test_suite(suite_file)
        assert cases[0].language == "zh"


# --- Metric to Rubric Score Mapping ---


class TestMetricToRubricScore:
    def test_excellent(self):
        assert _metric_to_rubric_score(0.95) == 5

    def test_good(self):
        assert _metric_to_rubric_score(0.80) == 4

    def test_fair(self):
        assert _metric_to_rubric_score(0.60) == 3

    def test_poor(self):
        assert _metric_to_rubric_score(0.30) == 2

    def test_very_poor(self):
        assert _metric_to_rubric_score(0.10) == 1

    def test_boundary_090(self):
        assert _metric_to_rubric_score(0.90) == 5

    def test_boundary_075(self):
        assert _metric_to_rubric_score(0.75) == 4

    def test_boundary_050(self):
        assert _metric_to_rubric_score(0.50) == 3

    def test_boundary_025(self):
        assert _metric_to_rubric_score(0.25) == 2


# --- Explanation Quality ---


class TestExplanationQuality:
    def _make_eval_result(self, explanation: str) -> EvalResult:
        mr = ModerationResult(
            harm_category="harassment",
            severity="severe",
            confidence=0.9,
            should_escalate=True,
            escalation_context={},
            explanation=explanation,
            raw_response={},
            latency_ms=50.0,
        )
        return EvalResult(
            test_case_id="tc-001",
            provider_name="test",
            moderation_result=mr,
            ground_truth={},
            is_category_correct=True,
            is_severity_correct=True,
            is_action_correct=True,
            severity_distance=0,
        )

    def test_good_explanation(self):
        result = self._make_eval_result(
            "Flagged categories: harassment. Top score: 0.92. "
            "Content contains harmful language targeting an individual. "
            "Severity: severe. Confidence: high. Escalation recommended for review."
        )
        quality = _compute_explanation_quality([result])
        assert quality > 0.5

    def test_empty_explanation(self):
        result = self._make_eval_result("")
        quality = _compute_explanation_quality([result])
        assert quality == 0.0

    def test_short_explanation(self):
        result = self._make_eval_result("Bad.")
        quality = _compute_explanation_quality([result])
        assert quality < 0.5

    def test_empty_results(self):
        assert _compute_explanation_quality([]) == 0.0
