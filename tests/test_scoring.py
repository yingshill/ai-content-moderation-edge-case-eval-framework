"""Tests for scoring module."""

import pytest
from src.scoring.metrics import (
    compute_classification_metrics,
    compute_calibration_error,
    compute_handoff_metrics,
)
from src.scoring.agreement import cohens_kappa
from src.scoring.rubric import RubricEngine


class TestClassificationMetrics:
    def test_perfect_predictions(self):
        y_true = ["hate_speech", "violence", "harassment"]
        y_pred = ["hate_speech", "violence", "harassment"]
        m = compute_classification_metrics(y_true, y_pred)
        assert m.macro_f1 == 1.0
        assert m.micro_f1 == 1.0

    def test_all_wrong(self):
        y_true = ["hate_speech", "violence"]
        y_pred = ["violence", "hate_speech"]
        m = compute_classification_metrics(y_true, y_pred)
        assert m.macro_f1 == 0.0

    def test_partial(self):
        y_true = ["hate_speech", "hate_speech", "violence"]
        y_pred = ["hate_speech", "violence", "violence"]
        m = compute_classification_metrics(y_true, y_pred)
        assert 0.0 < m.macro_f1 < 1.0


class TestCalibrationError:
    def test_perfect_calibration(self):
        confs = [0.9, 0.9, 0.1, 0.1]
        correct = [True, True, False, False]
        ece = compute_calibration_error(confs, correct)
        assert ece < 0.15  # approximately well-calibrated

    def test_empty(self):
        assert compute_calibration_error([], []) == 0.0


class TestCohensKappa:
    def test_perfect_agreement(self):
        labels = ["a", "b", "c", "a"]
        assert cohens_kappa(labels, labels) == 1.0

    def test_no_agreement(self):
        a = ["a", "a", "b", "b"]
        b = ["b", "b", "a", "a"]
        kappa = cohens_kappa(a, b)
        assert kappa < 0.0  # worse than chance

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            cohens_kappa(["a"], ["a", "b"])


class TestHandoffMetrics:
    def test_all_escalated(self):
        hm = compute_handoff_metrics(
            [True, True, False],
            [True, True, True],
            [{"content_snippet": "x", "harm_category_prediction": "y", "confidence_score": 0.5, "recommended_action": "review"}] * 3,
        )
        assert hm.trigger_rate == 1.0
        assert hm.trigger_recall == 1.0
