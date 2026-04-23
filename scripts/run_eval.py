"""CLI entry point for running evaluations."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml


def _build_providers(config: dict) -> list:
    """Instantiate enabled providers from config."""
    from src.providers.openai_mod import OpenAIModerationProvider
    from src.providers.perspective import PerspectiveProvider
    from src.providers.llm_judge import LLMJudgeProvider

    providers = []
    provider_configs = config.get("providers", {})

    if provider_configs.get("openai", {}).get("enabled"):
        providers.append(OpenAIModerationProvider(
            model=provider_configs["openai"].get("model", "omni-moderation-latest"),
        ))

    if provider_configs.get("perspective", {}).get("enabled"):
        providers.append(PerspectiveProvider(
            attributes=provider_configs["perspective"].get("attributes"),
        ))

    if provider_configs.get("llm_judge_claude", {}).get("enabled"):
        cfg = provider_configs["llm_judge_claude"]
        providers.append(LLMJudgeProvider(
            backend=cfg.get("backend", "anthropic"),
            model=cfg.get("model"),
        ))

    if provider_configs.get("llm_judge_gpt4o", {}).get("enabled"):
        cfg = provider_configs["llm_judge_gpt4o"]
        providers.append(LLMJudgeProvider(
            backend=cfg.get("backend", "openai"),
            model=cfg.get("model"),
        ))

    return providers


@click.command()
@click.option("--config", "-c", default="configs/eval_config.yaml", help="Path to eval config YAML.")
@click.option("--suite", "-s", required=True, help="Path to test suite (JSONL file or directory).")
@click.option("--policy", "-p", default=None, help="Policy profile name (e.g. tiktok, rednote).")
@click.option("--output", "-o", default=None, help="Output file path (default: outputs/eval_<timestamp>.json).")
def main(config: str, suite: str, policy: str | None, output: str | None) -> None:
    """Run AI moderation evaluation."""
    from src.eval_runner import load_test_suite, run_eval

    # Load config
    with open(config) as f:
        eval_config = yaml.safe_load(f)

    # Build providers
    providers = _build_providers(eval_config)
    if not providers:
        click.echo("Error: No providers enabled in config.", err=True)
        sys.exit(1)

    click.echo(f"Providers: {', '.join(p.provider_name() for p in providers)}")

    # Load test suite
    test_cases = load_test_suite(suite)
    click.echo(f"Test cases: {len(test_cases)}")

    # Run evaluation
    click.echo("Running evaluation...")
    max_concurrent = eval_config.get("evaluation", {}).get("max_concurrent", 5)
    summary = asyncio.run(run_eval(providers, test_cases, policy, max_concurrent))

    # Output results
    if output is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        output = f"outputs/eval_{ts}.json"

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    results_data = {
        "run_id": summary.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "suite": suite,
        "policy": policy,
        "n_test_cases": len(test_cases),
        "providers": {},
    }

    for name in summary.provider_results:
        cm = summary.classification_metrics.get(name)
        hm = summary.handoff_metrics.get(name)
        results_data["providers"][name] = {
            "n_results": len(summary.provider_results[name]),
            "macro_f1": cm.macro_f1 if cm else None,
            "micro_f1": cm.micro_f1 if cm else None,
            "calibration_error": summary.calibration_errors.get(name),
            "handoff_trigger_rate": hm.trigger_rate if hm else None,
            "handoff_precision": hm.trigger_precision if hm else None,
            "handoff_recall": hm.trigger_recall if hm else None,
            "per_category": cm.per_category if cm else {},
        }

    with open(output, "w") as f:
        json.dump(results_data, f, indent=2, default=str)

    click.echo(f"\nResults saved to {output}")
    click.echo("\n--- Summary ---")
    for name, data in results_data["providers"].items():
        click.echo(f"\n{name}:")
        click.echo(f"  Macro F1: {data['macro_f1']:.3f}" if data["macro_f1"] else "  Macro F1: N/A")
        click.echo(f"  Calibration Error: {data['calibration_error']:.3f}" if data["calibration_error"] else "  ECE: N/A")
        click.echo(f"  Handoff Rate: {data['handoff_trigger_rate']:.1%}" if data["handoff_trigger_rate"] is not None else "  Handoff Rate: N/A")


if __name__ == "__main__":
    main()
