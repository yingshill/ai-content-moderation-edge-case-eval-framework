"""Tests for scoring metrics, calibration, handoff, agreement, and rubric."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.scoring.metrics import (
    ClassificationMetrics,
    HandoffMetrics,
    compute_calibration_error,
    compute_classification_metrics,
    compute_handoff_metrics,
)
from src.scoring.agreement import cohens_kappa, multi_provider_agreement
from src.scoring.rubric import RubricEngine


# --- Classification Metrics ---


class TestClassificationMetrics:
    def test_perfect_classification(self):
        y_true = ["harassment", "hate_speech", None, "violence"]
        y_pred = ["harassment", "hate_speech", None, "violence"]
        result = compute_classification_metrics(y_true, y_pred)
        assert result.macro_f1 == 1.0
        assert result.micro_f1 == 1.0

    def test_all_wrong(self):
        y_true = ["harassment", "hate_speech", "violence"]
        y_pred = ["violence", "harassment", "hate_speech"]
        result = compute_classification_metrics(y_true, y_pred)
        assert result.macro_f1 == 0.0
        assert result.micro_f1 == 0.0

    def test_partial_correct(self):
        y_true = ["harassment", "harassment", "hate_speech", None]
        y_pred = ["harassment", "hate_speech", "hate_speech", None]
        result = compute_classification_metrics(y_true, y_pred)
        assert 0 < result.macro_f1 < 1.0
        assert 0 < result.micro_f1 < 1.0
        assert "harassment" in result.per_category
        assert "hate_speech" in result.per_category

    def test_empty_input(self):
        result = compute_classification_metrics([], [])
        assert result.macro_f1 == 0.0
        assert result.micro_f1 == 0.0

    def test_per_category_support(self):
        y_true = ["harassment", "harassment", "violence"]
        y_pred = ["harassment", "harassment", "violence"]
        result = compute_classification_metrics(y_true, y_pred)
        assert result.per_category["harassment"]["support"] == 2.0
        assert result.per_category["violence"]["support"] == 1.0


# --- Calibration Error ---


class TestCalibrationError:
    def test_perfect_calibration(self):
        # Confidence matches accuracy perfectly
        confidences = [0.9, 0.9, 0.9, 0.1, 0.1]
        correct = [True, True, True, False, False]
        ece = compute_calibration_error(confidences, correct)
        assert ece < 0.1  # Should be very low

    def test_poor_calibration(self):
        # High confidence but all wrong
        confidences = [0.95, 0.95, 0.95, 0.95]
        correct = [False, False, False, False]
        ece = compute_calibration_error(confidences, correct)
        assert ece > 0.5  # Should be high

    def test_empty_input(self):
        assert compute_calibration_error([], []) == 0.0


# --- Handoff Metrics ---


class TestHandoffMetrics:
    def test_perfect_handoff(self):
        true = [True, False, True, False]
        pred = [True, False, True, False]
        ctx = [
            {"content_snippet": "x", "harm_category_prediction": "y",
             "confidence_score": 0.9, "recommended_action": "flag"},
            None,
            {"content_snippet": "x", "harm_category_prediction": "y",
             "confidence_score": 0.8, "recommended_action": "flag"},
            None,
        ]
        result = compute_handoff_metrics(true, pred, ctx)
        assert result.trigger_precision == 1.0
        assert result.trigger_recall == 1.0
        assert result.context_completeness == 1.0

    def test_no_escalations(self):
        true = [False, False, False]
        pred = [False, False, False]
        ctx = [None, None, None]
        result = compute_handoff_metrics(true, pred, ctx)
        assert result.trigger_rate == 0.0

    def test_missing_context(self):
        true = [True, True]
        pred = [True, True]
        ctx = [None, None]  # Predicted escalation but no context
        result = compute_handoff_metrics(true, pred, ctx)
        assert result.context_completeness == 0.0

    def test_empty_input(self):
        result = compute_handoff_metrics([], [], [])
        assert result.trigger_rate == 0.0


# --- Cohen's Kappa ---


class TestCohensKappa:
    def test_perfect_agreement(self):
        a = ["cat", "dog", "cat", "dog"]
        b = ["cat", "dog", "cat", "dog"]
        assert cohens_kappa(a, b) == 1.0

    def test_no_agreement(self):
        a = ["cat", "cat", "cat", "cat"]
        b = ["dog", "dog", "dog", "dog"]
        kappa = cohens_kappa(a, b)
        assert kappa <= 0.0

    def test_partial_agreement(self):
        a = ["cat", "dog", "cat", "dog"]
        b = ["cat", "dog", "dog", "cat"]
        kappa = cohens_kappa(a, b)
        assert -1.0 <= kappa <= 1.0
        assert kappa != 1.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="equal length"):
            cohens_kappa(["a", "b"], ["a"])

    def test_empty_lists(self):
        assert cohens_kappa([], []) == 0.0


class TestMultiProviderAgreement:
    def test_two_providers(self):
        labels = {
            "provider_a": ["cat", "dog", "cat"],
            "provider_b": ["cat", "dog", "dog"],
        }
        result = multi_provider_agreement(labels)
        assert ("provider_a", "provider_b") in result
        assert -1.0 <= result[("provider_a", "provider_b")] <= 1.0

    def test_three_providers(self):
        labels = {
            "a": ["x", "y"],
            "b": ["x", "y"],
            "c": ["y", "x"],
        }
        result = multi_provider_agreement(labels)
        assert len(result) == 3  # C(3,2) = 3 pairs


# --- Rubric Engine ---


class TestRubricEngine:
    def test_load_and_score(self):
        rubric_path = Path("rubrics/default.yaml")
        if not rubric_path.exists():
            pytest.skip("rubrics/default.yaml not found")

        engine = RubricEngine(rubric_path)
        assert len(engine.dimensions) == 5

        result = engine.score({
            "accuracy": 4,
            "calibration": 3,
            "cultural_sensitivity": 4,
            "handoff_quality": 3,
            "explanation_quality": 4,
        })
        assert 0.0 <= result.normalized_score <= 1.0
        assert result.raw_total > 0

    def test_score_clamping(self):
        rubric_path = Path("rubrics/default.yaml")
        if not rubric_path.exists():
            pytest.skip("rubrics/default.yaml not found")

        engine = RubricEngine(rubric_path)
        # Score out of range should be clamped
        result = engine.score({"accuracy": 10, "calibration": -1})
        # Clamped to 5 and 1 respectively
        assert result.normalized_score > 0

    def test_missing_dimension_defaults_to_1(self):
        rubric_path = Path("rubrics/default.yaml")
        if not rubric_path.exists():
            pytest.skip("rubrics/default.yaml not found")

        engine = RubricEngine(rubric_path)
        result_all_1 = engine.score({})
        assert result_all_1.normalized_score == pytest.approx(0.2)  # 1/5

    def test_perfect_score(self):
        rubric_path = Path("rubrics/default.yaml")
        if not rubric_path.exists():
            pytest.skip("rubrics/default.yaml not found")

        engine = RubricEngine(rubric_path)
        result = engine.score({
            "accuracy": 5,
            "calibration": 5,
            "cultural_sensitivity": 5,
            "handoff_quality": 5,
            "explanation_quality": 5,
        })
        assert result.normalized_score == pytest.approx(1.0)
