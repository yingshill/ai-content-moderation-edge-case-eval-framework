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


def load_test_suite(path: str | Path) -> list[TestCase]:
    """Load test cases from a JSONL file or directory of JSONL files."""
    path = Path(path)
    cases: list[TestCase] = []

    files = list(path.glob("**/*.jsonl")) if path.is_dir() else [path]

    for f in sorted(files):
        with jsonlines.open(f) as reader:
            for obj in reader:
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
) -> EvalRunSummary:
    """Run evaluation across all providers and test cases."""
    import uuid

    run_id = f"eval_{uuid.uuid4().hex[:8]}"
    semaphore = asyncio.Semaphore(max_concurrent)
    summary = EvalRunSummary(run_id=run_id)

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

                return EvalResult(
                    test_case_id=tc.id,
                    provider_name=name,
                    moderation_result=mr,
                    ground_truth=gt,
                    is_category_correct=is_cat_correct,
                    is_severity_correct=(mr.severity == gt.get("severity")),
                    severity_distance=abs(pred_sev - gt_sev),
                )

        tasks = [evaluate_case(tc) for tc in test_cases]
        results = await asyncio.gather(*tasks)
        summary.provider_results[name] = list(results)

        # Compute metrics per provider
        y_true = [r.ground_truth.get("harm_category") for r in results]
        y_pred = [r.moderation_result.harm_category for r in results]
        summary.classification_metrics[name] = compute_classification_metrics(y_true, y_pred)

        confs = [r.moderation_result.confidence for r in results]
        correct = [r.is_category_correct for r in results]
        summary.calibration_errors[name] = compute_calibration_error(confs, correct)

        esc_true = [
            r.ground_truth.get("severity") in ("borderline", "critical")
            or r.ground_truth.get("annotator_agreement", 1.0) < 0.6
            for r in results
        ]
        esc_pred = [r.moderation_result.should_escalate for r in results]
        esc_ctx = [r.moderation_result.escalation_context for r in results]
        summary.handoff_metrics[name] = compute_handoff_metrics(esc_true, esc_pred, esc_ctx)

    # Cross-provider agreement
    if len(providers) > 1:
        provider_labels = {
            name: [r.moderation_result.harm_category or "none" for r in results]
            for name, results in summary.provider_results.items()
        }
        summary.agreement_scores = multi_provider_agreement(provider_labels)

    return summary
