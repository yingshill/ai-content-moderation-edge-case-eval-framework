"""Classification, calibration, and handoff metrics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..utils.logging import get_logger

logger = get_logger("scoring.metrics")


@dataclass
class ClassificationMetrics:
    """Aggregated classification performance metrics."""

    macro_f1: float
    micro_f1: float
    per_category: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class HandoffMetrics:
    """Human-AI handoff quality metrics."""

    trigger_rate: float  # fraction of cases escalated
    trigger_precision: float  # of escalated, how many truly needed it
    trigger_recall: float  # of truly needing escalation, how many were caught
    context_completeness: float  # fraction of escalation contexts with required fields


def compute_classification_metrics(
    y_true: list[str | None],
    y_pred: list[str | None],
) -> ClassificationMetrics:
    """Compute per-category and aggregate classification metrics.

    Args:
        y_true: Ground-truth harm categories (None = benign).
        y_pred: Predicted harm categories.

    Returns:
        ClassificationMetrics with macro/micro F1 and per-category breakdown.
    """
    categories = sorted(
        set(c for c in (y_true + y_pred) if c is not None)
    )

    per_cat: dict[str, dict[str, float]] = {}
    total_tp = total_fp = total_fn = 0

    for cat in categories:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p == cat)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cat and p == cat)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cat and p != cat)
        support = tp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        per_cat[cat] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": float(support),
        }

        total_tp += tp
        total_fp += fp
        total_fn += fn

    # Include None/benign as a "category" for micro averaging
    tp_none = sum(1 for t, p in zip(y_true, y_pred) if t is None and p is None)
    fp_none = sum(1 for t, p in zip(y_true, y_pred) if t is not None and p is None)
    fn_none = sum(1 for t, p in zip(y_true, y_pred) if t is None and p is not None)
    total_tp += tp_none
    total_fp += fp_none
    total_fn += fn_none

    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (
        2 * micro_p * micro_r / (micro_p + micro_r)
        if (micro_p + micro_r) > 0
        else 0.0
    )

    cat_f1s = [m["f1"] for m in per_cat.values()]
    macro_f1 = sum(cat_f1s) / len(cat_f1s) if cat_f1s else 0.0

    logger.info(f"classification_metrics macro_f1={macro_f1:.3f} micro_f1={micro_f1:.3f} categories={len(per_cat)}")

    return ClassificationMetrics(
        macro_f1=macro_f1,
        micro_f1=micro_f1,
        per_category=per_cat,
    )


def compute_calibration_error(
    confidences: list[float],
    correct: list[bool],
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE).

    Args:
        confidences: Model confidence scores (0-1).
        correct: Whether each prediction was correct.
        n_bins: Number of bins for ECE computation.

    Returns:
        ECE value (lower is better).
    """
    if not confidences:
        return 0.0

    confs = np.array(confidences)
    accs = np.array(correct, dtype=float)
    bin_boundaries = np.linspace(0, 1, n_bins + 1)

    ece = 0.0
    for i in range(n_bins):
        mask = (confs > bin_boundaries[i]) & (confs <= bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_conf = confs[mask].mean()
        bin_acc = accs[mask].mean()
        ece += (mask.sum() / len(confs)) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_handoff_metrics(
    should_escalate_true: list[bool],
    should_escalate_pred: list[bool],
    escalation_contexts: list[dict[str, Any] | None],
) -> HandoffMetrics:
    """Compute human-AI handoff quality metrics.

    Args:
        should_escalate_true: Ground truth for escalation need.
        should_escalate_pred: Predicted escalation decisions.
        escalation_contexts: Context objects provided with escalations.

    Returns:
        HandoffMetrics with trigger rate, precision, recall, and context completeness.
    """
    n = len(should_escalate_true)
    if n == 0:
        return HandoffMetrics(0.0, 0.0, 0.0, 0.0)

    tp = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if t and p)
    fp = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if not t and p)
    fn = sum(1 for t, p in zip(should_escalate_true, should_escalate_pred) if t and not p)
    n_pred = tp + fp

    trigger_rate = n_pred / n
    precision = tp / n_pred if n_pred > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Context completeness: check required fields in escalation contexts
    required_fields = {"content_snippet", "harm_category_prediction", "confidence_score", "recommended_action"}
    ctx_scores: list[float] = []
    for pred, ctx in zip(should_escalate_pred, escalation_contexts):
        if pred and ctx:
            present = sum(1 for f in required_fields if ctx.get(f) is not None)
            ctx_scores.append(present / len(required_fields))
        elif pred and not ctx:
            ctx_scores.append(0.0)

    context_completeness = sum(ctx_scores) / len(ctx_scores) if ctx_scores else 0.0

    logger.info(
        f"handoff_metrics trigger_rate={trigger_rate:.3f} "
        f"precision={precision:.3f} recall={recall:.3f} "
        f"context_completeness={context_completeness:.3f}"
    )

    return HandoffMetrics(
        trigger_rate=trigger_rate,
        trigger_precision=precision,
        trigger_recall=recall,
        context_completeness=context_completeness,
    )
