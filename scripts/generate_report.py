"""CLI script to generate evaluation reports from results JSON."""

from __future__ import annotations

import json
from pathlib import Path

import click

from src.utils.logging import setup_logging, get_logger

logger = get_logger("scripts.generate_report")


@click.command()
@click.argument("results_file", type=click.Path(exists=True))
@click.option("--format", "-f", "output_format", type=click.Choice(["markdown", "json", "both"]),
              default="both", help="Output format.")
@click.option("--output-dir", "-o", default="outputs", help="Output directory.")
@click.option("--log-level", default="INFO", help="Logging level.")
def main(results_file: str, output_format: str, output_dir: str, log_level: str) -> None:
    """Generate evaluation reports from a results JSON file."""
    setup_logging(level=log_level)

    with open(results_file) as f:
        data = json.load(f)

    run_id = data.get("run_id", "unknown")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    click.echo(f"Generating report for run: {run_id}")

    if output_format in ("markdown", "both"):
        md_path = Path(output_dir) / f"report_{run_id}.md"
        _generate_markdown(data, md_path)
        click.echo(f"Markdown report: {md_path}")

    if output_format in ("json", "both"):
        json_path = Path(output_dir) / f"report_{run_id}.json"
        _generate_json(data, json_path)
        click.echo(f"JSON report: {json_path}")


def _generate_markdown(data: dict, output_path: Path) -> None:
    lines = [
        f"# Evaluation Report: {data.get('run_id', 'unknown')}",
        "",
        f"**Generated from:** `{data.get('suite', 'N/A')}`",
        f"**Policy:** {data.get('policy', 'none')}",
        f"**Test cases:** {data.get('n_test_cases', 'N/A')}",
        "",
    ]

    for name, pdata in data.get("providers", {}).items():
        lines.extend([
            f"## Provider: {name}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Test Cases | {pdata.get('n_results', 'N/A')} |",
        ])
        if pdata.get("macro_f1") is not None:
            lines.append(f"| Macro F1 | {pdata['macro_f1']:.3f} |")
        if pdata.get("micro_f1") is not None:
            lines.append(f"| Micro F1 | {pdata['micro_f1']:.3f} |")
        if pdata.get("calibration_error") is not None:
            lines.append(f"| Calibration Error | {pdata['calibration_error']:.3f} |")
        if pdata.get("action_accuracy") is not None:
            lines.append(f"| Action Accuracy | {pdata['action_accuracy']:.1%} |")
        if pdata.get("rubric_score") is not None:
            lines.append(f"| **Rubric Score** | **{pdata['rubric_score']:.3f}** |")
        lines.append("")

    output_path.write_text("\n".join(lines))


def _generate_json(data: dict, output_path: Path) -> None:
    report = {
        "run_id": data.get("run_id"),
        "suite": data.get("suite"),
        "policy": data.get("policy"),
        "n_test_cases": data.get("n_test_cases"),
        "providers": data.get("providers", {}),
        "agreement": data.get("agreement", {}),
    }
    output_path.write_text(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
