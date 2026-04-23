"""Head-to-head provider comparison script."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml


@click.command()
@click.option("--config", "-c", default="configs/eval_config.yaml")
@click.option("--providers", "-p", required=True, help="Comma-separated provider names (e.g. openai,perspective).")
@click.option("--suite", "-s", required=True, help="Path to test suite JSONL file or directory.")
@click.option("--policy", default=None, help="Policy profile name.")
@click.option("--output", "-o", default=None)
def main(config: str, providers: str, suite: str, policy: str | None, output: str | None) -> None:
    """Compare two or more providers head-to-head on the same test suite."""
    from src.eval_runner import load_test_suite, run_eval
    from scripts.run_eval import _build_providers

    with open(config) as f:
        eval_config = yaml.safe_load(f)

    requested = {p.strip() for p in providers.split(",")}
    all_providers = _build_providers(eval_config)
    selected = [p for p in all_providers if p.provider_name() in requested]

    if len(selected) < 2:
        click.echo(f"Error: Need at least 2 providers. Found: {[p.provider_name() for p in selected]}", err=True)
        sys.exit(1)

    test_cases = load_test_suite(suite)
    click.echo(f"Comparing {', '.join(p.provider_name() for p in selected)} on {len(test_cases)} cases")

    summary = asyncio.run(run_eval(selected, test_cases, policy))

    # Print comparison table
    click.echo("\n" + "=" * 70)
    click.echo(f"{'Metric':<30} ", nl=False)
    for name in summary.provider_results:
        click.echo(f"{name:<20}", nl=False)
    click.echo()
    click.echo("-" * 70)

    for name in summary.provider_results:
        cm = summary.classification_metrics.get(name)
        if cm:
            click.echo(f"{'Macro F1':<30} {cm.macro_f1:<20.3f}")
            break

    # More detailed comparison
    for metric_name in ["Macro F1", "Micro F1", "Calibration Error", "Handoff Precision", "Handoff Recall"]:
        click.echo(f"{metric_name:<30} ", nl=False)
        for name in summary.provider_results:
            cm = summary.classification_metrics.get(name)
            hm = summary.handoff_metrics.get(name)
            val = None
            if metric_name == "Macro F1" and cm:
                val = cm.macro_f1
            elif metric_name == "Micro F1" and cm:
                val = cm.micro_f1
            elif metric_name == "Calibration Error":
                val = summary.calibration_errors.get(name)
            elif metric_name == "Handoff Precision" and hm:
                val = hm.trigger_precision
            elif metric_name == "Handoff Recall" and hm:
                val = hm.trigger_recall
            click.echo(f"{val:<20.3f}" if val is not None else f"{'N/A':<20}", nl=False)
        click.echo()

    if summary.agreement_scores:
        click.echo(f"\nInter-provider Agreement (Cohen's Kappa):")
        for (a, b), kappa in summary.agreement_scores.items():
            click.echo(f"  {a} vs {b}: {kappa:.3f}")

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump({
                "providers": list(summary.provider_results.keys()),
                "n_cases": len(test_cases),
                "metrics": {
                    name: {
                        "macro_f1": summary.classification_metrics[name].macro_f1 if name in summary.classification_metrics else None,
                        "calibration_error": summary.calibration_errors.get(name),
                    }
                    for name in summary.provider_results
                },
                "agreement": {f"{a}_vs_{b}": k for (a, b), k in summary.agreement_scores.items()},
            }, f, indent=2)
        click.echo(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
