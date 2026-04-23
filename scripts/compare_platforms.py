"""CLI script to compare moderation behavior across platform policies."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml

from src.utils.logging import setup_logging, get_logger

logger = get_logger("scripts.compare_platforms")


@click.command()
@click.option("--config", "-c", default="configs/eval_config.yaml", help="Path to eval config YAML.")
@click.option("--suite", "-s", default="test_suites/cross_platform/same_content_diff_policy.jsonl",
              help="Path to cross-platform test suite.")
@click.option("--policies", "-p", multiple=True, default=["tiktok", "rednote"],
              help="Policy profiles to compare.")
@click.option("--output", "-o", default=None, help="Output file path.")
@click.option("--log-level", default="INFO", help="Logging level.")
def main(config: str, suite: str, policies: tuple[str, ...], output: str | None, log_level: str) -> None:
    """Compare moderation decisions across different platform policies."""
    from scripts.run_eval import _build_providers
    from src.eval_runner import load_test_suite, run_eval

    setup_logging(level=log_level)

    with open(config) as f:
        eval_config = yaml.safe_load(f)

    providers = _build_providers(eval_config)
    if not providers:
        click.echo("Error: No providers enabled.", err=True)
        sys.exit(1)

    test_cases = load_test_suite(suite)
    click.echo(f"Test cases: {len(test_cases)}")
    click.echo(f"Policies: {', '.join(policies)}")
    click.echo(f"Providers: {', '.join(p.provider_name() for p in providers)}")

    eval_settings = eval_config.get("evaluation", {})
    max_concurrent = eval_settings.get("max_concurrent", 5)
    rubric_path = eval_settings.get("rubric", "rubrics/default.yaml")

    results: dict[str, dict] = {}
    for policy in policies:
        click.echo(f"\nRunning with policy: {policy}")
        summary = asyncio.run(
            run_eval(providers, test_cases, policy, max_concurrent, rubric_path)
        )
        for name in summary.provider_results:
            key = f"{name}_{policy}"
            cm = summary.classification_metrics.get(name)
            results[key] = {
                "provider": name,
                "policy": policy,
                "macro_f1": cm.macro_f1 if cm else None,
                "calibration_error": summary.calibration_errors.get(name),
                "action_accuracy": summary.action_accuracy.get(name),
                "rubric_score": summary.rubric_scores.get(name),
            }

    click.echo(f"\n{'='*70}")
    click.echo("Cross-Platform Policy Comparison")
    click.echo(f"{'='*70}")

    header = f"{'Provider + Policy':<40} {'F1':>7} {'ECE':>7} {'Action':>8} {'Rubric':>8}"
    click.echo(header)
    click.echo("-" * len(header))

    for key, rdata in sorted(results.items()):
        f1 = f"{rdata['macro_f1']:.3f}" if rdata.get("macro_f1") is not None else "N/A"
        ece = f"{rdata['calibration_error']:.3f}" if rdata.get("calibration_error") is not None else "N/A"
        action = f"{rdata['action_accuracy']:.1%}" if rdata.get("action_accuracy") is not None else "N/A"
        rubric = f"{rdata['rubric_score']:.3f}" if rdata.get("rubric_score") is not None else "N/A"
        label = f"{rdata['provider']} ({rdata['policy']})"
        click.echo(f"{label:<40} {f1:>7} {ece:>7} {action:>8} {rubric:>8}")

    if output is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        output = f"outputs/platform_comparison_{ts}.json"

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    click.echo(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
