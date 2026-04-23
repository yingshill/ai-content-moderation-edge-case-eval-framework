"""Cross-platform policy comparison script.

Runs the same test suite against the same provider(s) but under different
platform policy profiles, then compares how policy differences affect outcomes.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
import yaml


@click.command()
@click.option("--config", "-c", default="configs/eval_config.yaml")
@click.option("--suite", "-s", required=True, help="Path to test suite JSONL file or directory.")
@click.option("--policies", "-p", required=True, help="Comma-separated policy names (e.g. tiktok,rednote).")
@click.option("--provider", default=None, help="Single provider to use (default: first enabled).")
@click.option("--output", "-o", default=None)
def main(config: str, suite: str, policies: str, provider: str | None, output: str | None) -> None:
    """Compare how different platform policies affect moderation outcomes."""
    from src.eval_runner import load_test_suite, run_eval, load_policy
    from scripts.run_eval import _build_providers

    with open(config) as f:
        eval_config = yaml.safe_load(f)

    all_providers = _build_providers(eval_config)
    if provider:
        selected = [p for p in all_providers if p.provider_name() == provider]
    else:
        selected = all_providers[:1]

    if not selected:
        click.echo("Error: No matching provider found.", err=True)
        sys.exit(1)

    test_cases = load_test_suite(suite)
    policy_names = [p.strip() for p in policies.split(",")]

    click.echo(f"Provider: {selected[0].provider_name()}")
    click.echo(f"Policies: {', '.join(policy_names)}")
    click.echo(f"Test cases: {len(test_cases)}")
    click.echo()

    results_by_policy = {}
    for policy_name in policy_names:
        # Validate policy exists
        policy = load_policy(policy_name)
        if policy is None:
            click.echo(f"Warning: Policy '{policy_name}' not found, skipping.", err=True)
            continue

        click.echo(f"Running eval with policy: {policy_name}...")
        summary = asyncio.run(run_eval(selected, test_cases, policy_name))
        results_by_policy[policy_name] = summary

    # Compare results
    click.echo("\n" + "=" * 70)
    click.echo("Cross-Platform Policy Comparison")
    click.echo("=" * 70)

    provider_name = selected[0].provider_name()
    click.echo(f"\n{'Metric':<30} ", nl=False)
    for pn in results_by_policy:
        click.echo(f"{pn:<20}", nl=False)
    click.echo()
    click.echo("-" * 70)

    for metric_name in ["Macro F1", "Calibration Error", "Handoff Rate"]:
        click.echo(f"{metric_name:<30} ", nl=False)
        for pn, summary in results_by_policy.items():
            cm = summary.classification_metrics.get(provider_name)
            hm = summary.handoff_metrics.get(provider_name)
            val = None
            if metric_name == "Macro F1" and cm:
                val = cm.macro_f1
            elif metric_name == "Calibration Error":
                val = summary.calibration_errors.get(provider_name)
            elif metric_name == "Handoff Rate" and hm:
                val = hm.trigger_rate
            click.echo(f"{val:<20.3f}" if val is not None else f"{'N/A':<20}", nl=False)
        click.echo()

    # Show divergences — cases where policies disagree on expected action
    click.echo("\n--- Policy Divergence Analysis ---")
    if len(results_by_policy) >= 2:
        policies_list = list(results_by_policy.keys())
        p1, p2 = policies_list[0], policies_list[1]
        r1 = results_by_policy[p1].provider_results.get(provider_name, [])
        r2 = results_by_policy[p2].provider_results.get(provider_name, [])

        divergent = 0
        for er1, er2 in zip(r1, r2):
            if er1.moderation_result.harm_category != er2.moderation_result.harm_category:
                divergent += 1
                if divergent <= 5:
                    click.echo(f"  Case {er1.test_case_id}: {p1}={er1.moderation_result.harm_category} vs {p2}={er2.moderation_result.harm_category}")

        click.echo(f"\nTotal divergences: {divergent}/{len(r1)} ({divergent/max(len(r1),1):.1%})")

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "provider": provider_name,
            "policies": policy_names,
            "n_cases": len(test_cases),
            "by_policy": {
                pn: {
                    "macro_f1": summary.classification_metrics.get(provider_name, None),
                    "ece": summary.calibration_errors.get(provider_name),
                }
                for pn, summary in results_by_policy.items()
            },
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        click.echo(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
