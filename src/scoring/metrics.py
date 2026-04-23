"""Evaluation metrics: precision, recall, F1, calibration error, handoff metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np


@dataclass
class ClassificationMetrics:
    """Per-category and aggregate classification metrics."""

    per_category: dict[str, dict[str, float]] = field(default_factory=dict)
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    micro_precision: float = 0.0
    micro_recall: float = 0.0
    micro_f1: float = 0.0
    cultural_bias_delta: float | None = None


@dataclass
class HandoffMetrics:
    """Metrics for human-AI handoff quality."""

    trigger_rate: float  # % of cases escalated
    trigger_precision: float  # % of escalations that were genuinely ambiguous
    trigger_recall: float  # % of ambiguous cases that were escalated
    context_completeness: float  # avg % of required fields populated


def compute_classification_metrics(
    y_true: list[str | None],
    y_pred: list[str | None],
    categories: list[str] | None = None,
) -> ClassificationMetrics:
    """Compute precision, recall, F1 per category and macro/micro averages."""
    if categories is None:
        all_cats = set(y_true) | set(y_pred)
        categories = sorted(c for c in all_cats if c is not None)

    per_cat: dict[str, dict[str, float]] = {}
    total_tp, total_fp, total_fn = 0, 0, 0

    for cat in categories:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p == cat)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cat and p == cat)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p != cat)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        per_cat[cat] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
        total_tp += tp
        total_fp += fp
        total_fn += fn

    n_cats = len(categories) or 1
    macro_p = sum(v["precision"] for v in per_cat.values()) / n_cats
    macro_r = sum(v["recall"] for v in per_cat.values()) / n_cats
    macro_f1 = sum(v["f1"] for v in per_cat.values()) / n_cats

    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (
        2 * micro_p * micro_r / (micro_p + micro_r)
        if (micro_p + micro_r) > 0
        else 0.0
    )

    return ClassificationMetrics(
        per_category=per_cat,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        micro_precision=micro_p,
        micro_recall=micro_r,
        micro_f1=micro_f1,
    )


def compute_calibration_error(
    confidences: list[float],
    correctness: list[bool],
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error (ECE) — binned confidence vs accuracy."""
    if not confidences:
        return 0.0

    confs = np.array(confidences)
    accs = np.array(correctness, dtype=float)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        mask = (confs > bin_edges[i]) & (confs <= bin_edges[i + 1])
        count = mask.sum()
        if count == 0:
            continue
        avg_conf = confs[mask].mean()
        avg_acc = accs[mask].mean()
        ece += (count / len(confs)) * abs(avg_acc - avg_conf)

    return float(ece)


def compute_handoff_metrics(
    should_escalate_true: list[bool],
    should_escalate_pred: list[bool],
    escalation_contexts: list[dict | None],
    required_fields: list[str] | None = None,
) -> HandoffMetrics:
    """Compute handoff trigger rate, precision, recall, and context completeness."""
    n = len(should_escalate_pred)
    if n == 0:
        return HandoffMetrics(0.0, 0.0, 0.0, 0.0)

    required_fields = required_fields or [
        "content_snippet",
        "harm_category_prediction",
        "confidence_score",
        "recommended_action",
    ]

    trigger_rate = sum(should_escalate_pred) / n

    tp = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if t and p)
    fp = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if not t and p)
    fn = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if t and not p)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Context completeness for triggered escalations
    completeness_scores: list[float] = []
    for pred, ctx in zip(should_escalate_pred, escalation_contexts):
        if pred and ctx:
            present = sum(1 for f in required_fields if f in ctx and ctx[f] is not None)
            completeness_scores.append(present / len(required_fields))
        elif pred:
            completeness_scores.append(0.0)

    avg_completeness = (
        sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
    )

    return HandoffMetrics(
        trigger_rate=trigger_rate,
        trigger_precision=precision,
        trigger_recall=recall,
        context_completeness=avg_completeness,
    )
