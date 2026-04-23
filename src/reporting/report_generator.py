"""Generate evaluation reports in Markdown and JSON formats."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..eval_runner import EvalRunSummary

from ..utils.logging import get_logger

logger = get_logger("reporting.generator")


def generate_markdown_report(summary: EvalRunSummary, output_path: str | Path) -> None:
    """Generate a Markdown evaluation report."""
    lines: list[str] = []
    lines.append(f"# Evaluation Report: {summary.run_id}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    for name in summary.provider_results:
        results = summary.provider_results[name]
        cm = summary.classification_metrics.get(name)
        hm = summary.handoff_metrics.get(name)
        ece = summary.calibration_errors.get(name, 0.0)
        rubric = summary.rubric_scores.get(name)
        action_acc = summary.action_accuracy.get(name)

        lines.append(f"## Provider: {name}")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Test Cases | {len(results)} |")
        if cm:
            lines.append(f"| Macro F1 | {cm.macro_f1:.3f} |")
            lines.append(f"| Micro F1 | {cm.micro_f1:.3f} |")
        lines.append(f"| Calibration Error (ECE) | {ece:.3f} |")
        if action_acc is not None:
            lines.append(f"| Action Accuracy | {action_acc:.1%} |")
        if rubric is not None:
            lines.append(f"| **Rubric Score (5-dim)** | **{rubric:.3f}** |")
        if hm:
            lines.append(f"| Handoff Trigger Rate | {hm.trigger_rate:.1%} |")
            lines.append(f"| Handoff Precision | {hm.trigger_precision:.3f} |")
            lines.append(f"| Handoff Recall | {hm.trigger_recall:.3f} |")
            lines.append(f"| Context Completeness | {hm.context_completeness:.1%} |")
        lines.append("")

        if cm and cm.per_category:
            lines.append("### Per-Category Breakdown")
            lines.append("")
            lines.append("| Category | Precision | Recall | F1 | Support |")
            lines.append("|----------|-----------|--------|-----|---------|")
            for cat, metrics in sorted(cm.per_category.items()):
                lines.append(
                    f"| {cat} | {metrics['precision']:.3f} | "
                    f"{metrics['recall']:.3f} | {metrics['f1']:.3f} | "
                    f"{int(metrics['support'])} |"
                )
            lines.append("")

    if summary.agreement_scores:
        lines.append("## Inter-Provider Agreement")
        lines.append("")
        lines.append("| Provider A | Provider B | Cohen's Kappa |")
        lines.append("|------------|------------|---------------|")
        for (a, b), kappa in sorted(summary.agreement_scores.items()):
            lines.append(f"| {a} | {b} | {kappa:.3f} |")
        lines.append("")

    Path(output_path).write_text("\n".join(lines))
    logger.info(f"markdown_report_written path={output_path}")


def generate_json_report(summary: EvalRunSummary, output_path: str | Path) -> None:
    """Generate a JSON evaluation report."""
    data: dict[str, Any] = {
        "run_id": summary.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "providers": {},
    }

    for name in summary.provider_results:
        cm = summary.classification_metrics.get(name)
        hm = summary.handoff_metrics.get(name)
        data["providers"][name] = {
            "classification": asdict(cm) if cm else None,
            "handoff": asdict(hm) if hm else None,
            "calibration_error": summary.calibration_errors.get(name),
            "action_accuracy": summary.action_accuracy.get(name),
            "rubric_score": summary.rubric_scores.get(name),
        }

    data["agreement"] = {
        f"{a}_vs_{b}": kappa for (a, b), kappa in summary.agreement_scores.items()
    }

    Path(output_path).write_text(json.dumps(data, indent=2, default=str))
    logger.info(f"json_report_written path={output_path}")
