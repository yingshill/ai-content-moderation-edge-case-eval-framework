"""Orchestrator: load test suite -> call providers -> collect responses -> score."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonlines
import yaml

from .providers.base import ModerationProvider, ModerationRequest, ModerationResult
from .scoring.metrics import (
    ClassificationMetrics,
    HandoffMetrics,
    compute_calibration_error,
    compute_classification_metrics,
    compute_handoff_metrics,
)
from .scoring.agreement import cohens_kappa, multi_provider_agreement
from .scoring.rubric import RubricEngine
from .taxonomy.category_registry import validate_category
from .utils.logging import get_logger

logger = get_logger("eval_runner")


@dataclass
class TestCase:
    """A single test case loaded from a JSONL suite."""

    id: str
    content: str
    language: str
    context: dict[str, Any]
    ground_truth: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class EvalResult:
    """Result of evaluating one test case against one provider."""

    test_case_id: str
    provider_name: str
    moderation_result: ModerationResult
    ground_truth: dict[str, Any]
    is_category_correct: bool
    is_severity_correct: bool
    is_action_correct: bool
    severity_distance: int


@dataclass
class EvalRunSummary:
    """Summary of a complete evaluation run."""

    run_id: str
    provider_results: dict[str, list[EvalResult]] = field(default_factory=dict)
    classification_metrics: dict[str, ClassificationMetrics] = field(default_factory=dict)
    handoff_metrics: dict[str, HandoffMetrics] = field(default_factory=dict)
    calibration_errors: dict[str, float] = field(default_factory=dict)
    agreement_scores: dict[tuple[str, str], float] = field(default_factory=dict)
    rubric_scores: dict[str, float] = field(default_factory=dict)
    action_accuracy: dict[str, float] = field(default_factory=dict)


def load_test_suite(path: str | Path) -> list[TestCase]:
    """Load test cases from a JSONL file or directory of JSONL files.

    Validates each test case against the canonical taxonomy.
    """
    path = Path(path)
    cases: list[TestCase] = []
    validation_warnings: list[str] = []

    files = list(path.glob("**/*.jsonl")) if path.is_dir() else [path]

    for f in sorted(files):
        with jsonlines.open(f) as reader:
            for line_num, obj in enumerate(reader, 1):
                # Validate required fields
                if "id" not in obj or "content" not in obj or "ground_truth" not in obj:
                    validation_warnings.append(
                        f"{f.name}:{line_num} missing required fields (id, content, ground_truth)"
                    )
                    continue

                # Validate harm category against taxonomy
                gt_category = obj["ground_truth"].get("harm_category")
                if not validate_category(gt_category):
                    validation_warnings.append(
                        f"{f.name}:{line_num} unknown harm_category={gt_category!r}"
                    )

                cases.append(
                    TestCase(
                        id=obj["id"],
                        content=obj["content"],
                        language=obj.get("language", "en"),
                        context=obj.get("context", {}),
                        ground_truth=obj["ground_truth"],
                        metadata=obj.get("metadata", {}),
                    )
                )

    if validation_warnings:
        for w in validation_warnings:
            logger.warning(f"test_suite_validation {w}")

    logger.info(f"loaded_test_suite cases={len(cases)} files={len(files)}")
    return cases


def load_policy(policy_name: str | None) -> dict[str, Any] | None:
    """Load a platform policy profile by name."""
    if not policy_name:
        return None
    policy_path = Path("policies") / f"{policy_name}.yaml"
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy profile not found: {policy_path}")
    with open(policy_path) as f:
        return yaml.safe_load(f)


_SEVERITY_ORDER = {"benign": 0, "borderline": 1, "severe": 2, "critical": 3}


async def run_eval(
    providers: list[ModerationProvider],
    test_cases: list[TestCase],
    policy_name: str | None = None,
    max_concurrent: int = 5,
    rubric_path: str = "rubrics/default.yaml",
) -> EvalRunSummary:
    """Run evaluation across all providers and test cases."""
    import uuid

    run_id = f"eval_{uuid.uuid4().hex[:8]}"
    semaphore = asyncio.Semaphore(max_concurrent)
    summary = EvalRunSummary(run_id=run_id)

    logger.info(f"eval_start run_id={run_id} providers={len(providers)} cases={len(test_cases)}")

    for provider in providers:
        name = provider.provider_name()
        results: list[EvalResult] = []

        async def evaluate_case(tc: TestCase) -> EvalResult:
            async with semaphore:
                request = ModerationRequest(
                    content=tc.content,
                    content_id=tc.id,
                    language=tc.language,
                    context=tc.context,
                    policy_profile=policy_name,
                )
                mr = await provider.moderate_timed(request)

                gt = tc.ground_truth
                is_cat_correct = mr.harm_category == gt.get("harm_category")
                gt_sev = _SEVERITY_ORDER.get(gt.get("severity", ""), 0)
                pred_sev = _SEVERITY_ORDER.get(mr.severity, 0)
                is_action_correct = mr.expected_action == gt.get("expected_action", "")

                return EvalResult(
                    test_case_id=tc.id,
                    provider_name=name,
                    moderation_result=mr,
                    ground_truth=gt,
                    is_category_correct=is_cat_correct,
                    is_severity_correct=(mr.severity == gt.get("severity")),
                    is_action_correct=is_action_correct,
                    severity_distance=abs(pred_sev - gt_sev),
                )

        tasks = [evaluate_case(tc) for tc in test_cases]
        results = await asyncio.gather(*tasks)
        summary.provider_results[name] = list(results)

        # --- Classification metrics ---
        y_true = [r.ground_truth.get("harm_category") for r in results]
        y_pred = [r.moderation_result.harm_category for r in results]
        summary.classification_metrics[name] = compute_classification_metrics(y_true, y_pred)

        # --- Calibration error ---
        confs = [r.moderation_result.confidence for r in results]
        correct = [r.is_category_correct for r in results]
        summary.calibration_errors[name] = compute_calibration_error(confs, correct)

        # --- Handoff metrics ---
        esc_true = [
            r.ground_truth.get("severity") in ("borderline", "critical")
            or r.ground_truth.get("annotator_agreement", 1.0) < 0.6
            for r in results
        ]
        esc_pred = [r.moderation_result.should_escalate for r in results]
        esc_ctx = [r.moderation_result.escalation_context for r in results]
        summary.handoff_metrics[name] = compute_handoff_metrics(esc_true, esc_pred, esc_ctx)

        # --- Action accuracy ---
        n_action = sum(1 for r in results if r.is_action_correct)
        summary.action_accuracy[name] = n_action / len(results) if results else 0.0

        # --- Rubric scoring (5-dimension weighted) ---
        rubric_path_obj = Path(rubric_path)
        if rubric_path_obj.exists():
            rubric = RubricEngine(rubric_path_obj)
            cm = summary.classification_metrics[name]
            hm = summary.handoff_metrics[name]
            ece = summary.calibration_errors[name]

            # Map eval metrics to rubric dimensions (1-5 scale)
            dim_scores = {
                "accuracy": _metric_to_rubric_score(cm.macro_f1),
                "calibration": _metric_to_rubric_score(1.0 - ece),
                "cultural_sensitivity": _metric_to_rubric_score(
                    _compute_cultural_sensitivity(results)
                ),
                "handoff_quality": _metric_to_rubric_score(
                    (hm.trigger_precision + hm.trigger_recall + hm.context_completeness) / 3.0
                ),
                "explanation_quality": _metric_to_rubric_score(
                    _compute_explanation_quality(results)
                ),
            }
            rubric_result = rubric.score(dim_scores)
            summary.rubric_scores[name] = rubric_result.normalized_score

            logger.info(
                f"rubric_score provider={name} "
                f"normalized={rubric_result.normalized_score:.3f} "
                f"dimensions={dim_scores}"
            )

        logger.info(
            f"provider_eval_complete provider={name} "
            f"macro_f1={summary.classification_metrics[name].macro_f1:.3f} "
            f"ece={summary.calibration_errors[name]:.3f} "
            f"action_accuracy={summary.action_accuracy[name]:.3f}"
        )

    # Cross-provider agreement
    if len(providers) > 1:
        provider_labels = {
            name: [r.moderation_result.harm_category or "none" for r in results]
            for name, results in summary.provider_results.items()
        }
        summary.agreement_scores = multi_provider_agreement(provider_labels)

    # Clean up provider resources
    for provider in providers:
        await provider.close()

    logger.info(f"eval_complete run_id={run_id}")
    return summary


def _metric_to_rubric_score(value: float) -> int:
    """Convert a 0.0-1.0 metric to a 1-5 rubric score."""
    if value >= 0.9:
        return 5
    if value >= 0.75:
        return 4
    if value >= 0.5:
        return 3
    if value >= 0.25:
        return 2
    return 1


def _compute_cultural_sensitivity(results: list[EvalResult]) -> float:
    """Compute cultural sensitivity score based on cross-cultural test cases.

    Measures accuracy specifically on cases tagged with cultural context.
    Falls back to overall accuracy if no cultural cases exist.
    """
    cultural_results = [
        r for r in results
        if r.ground_truth.get("metadata", {}).get("cultural_context")
        or "cultural" in r.ground_truth.get("metadata", {}).get("edge_case_type", "")
    ]
    # Also check the top-level metadata field
    if not cultural_results:
        cultural_results = [
            r for r in results
            if "cultural" in (getattr(r, "metadata", {}) or {}).get("edge_case_type", "")
        ]

    if not cultural_results:
        # Fall back: use all results
        cultural_results = results

    if not cultural_results:
        return 0.5

    correct = sum(1 for r in cultural_results if r.is_category_correct)
    return correct / len(cultural_results)


def _compute_explanation_quality(results: list[EvalResult]) -> float:
    """Compute explanation quality score.

    Checks whether explanations are non-empty and contain policy-relevant language.
    """
    if not results:
        return 0.0

    scores: list[float] = []
    policy_keywords = {
        "category", "flagged", "score", "confidence", "context",
        "policy", "severity", "harm", "escalat", "review",
    }

    for r in results:
        explanation = r.moderation_result.explanation
        if not explanation:
            scores.append(0.0)
            continue

        score = 0.0
        # Non-empty explanation
        score += 0.3
        # Reasonable length (at least 20 chars)
        if len(explanation) >= 20:
            score += 0.2
        # Contains policy-relevant terms
        explanation_lower = explanation.lower()
        keyword_hits = sum(1 for kw in policy_keywords if kw in explanation_lower)
        score += min(0.5, keyword_hits * 0.1)

        scores.append(min(1.0, score))

    return sum(scores) / len(scores)
