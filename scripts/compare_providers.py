"""CLI script to compare evaluation results across providers."""

from __future__ import annotations

import json
import sys

import click

from src.utils.logging import setup_logging, get_logger

logger = get_logger("scripts.compare_providers")


@click.command()
@click.argument("results_file", type=click.Path(exists=True))
@click.option("--metric", "-m", default="macro_f1", help="Metric to rank by.")
@click.option("--log-level", default="INFO", help="Logging level.")
def main(results_file: str, metric: str, log_level: str) -> None:
    """Compare providers from an evaluation results JSON file."""
    setup_logging(level=log_level)

    with open(results_file) as f:
        data = json.load(f)

    providers = data.get("providers", {})
    if not providers:
        click.echo("No provider results found.", err=True)
        sys.exit(1)

    click.echo(f"\n{'='*60}")
    click.echo(f"Provider Comparison - {data.get('run_id', 'unknown')}")
    click.echo(f"{'='*60}")
    click.echo(f"Test cases: {data.get('n_test_cases', 'N/A')}")
    click.echo(f"Suite: {data.get('suite', 'N/A')}")
    click.echo(f"Policy: {data.get('policy', 'none')}")
    click.echo()

    header = f"{'Provider':<35} {'Macro F1':>9} {'ECE':>7} {'Action':>8} {'Rubric':>8} {'Handoff':>8}"
    click.echo(header)
    click.echo("-" * len(header))

    ranked = sorted(
        providers.items(),
        key=lambda x: x[1].get(metric) or 0,
        reverse=True,
    )

    for name, pdata in ranked:
        f1 = f"{pdata['macro_f1']:.3f}" if pdata.get("macro_f1") is not None else "N/A"
        ece = f"{pdata['calibration_error']:.3f}" if pdata.get("calibration_error") is not None else "N/A"
        action = f"{pdata['action_accuracy']:.1%}" if pdata.get("action_accuracy") is not None else "N/A"
        rubric = f"{pdata['rubric_score']:.3f}" if pdata.get("rubric_score") is not None else "N/A"
        handoff = f"{pdata['handoff_trigger_rate']:.1%}" if pdata.get("handoff_trigger_rate") is not None else "N/A"
        click.echo(f"{name:<35} {f1:>9} {ece:>7} {action:>8} {rubric:>8} {handoff:>8}")

    agreement = data.get("agreement", {})
    if agreement:
        click.echo(f"\nInter-Provider Agreement (Cohen's Kappa):")
        for pair, kappa in sorted(agreement.items()):
            click.echo(f"  {pair}: {kappa:.3f}")

    click.echo()


if __name__ == "__main__":
    main()
