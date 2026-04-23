"""Standalone report generation from eval results JSON."""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.command()
@click.option("--results", "-r", required=True, help="Path to eval results JSON file.")
@click.option("--output", "-o", required=True, help="Output path for the report.")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
def main(results: str, output: str, fmt: str) -> None:
    """Generate a formatted report from evaluation results."""
    with open(results) as f:
        data = json.load(f)

    if fmt == "markdown":
        lines = []
        lines.append(f"# Evaluation Report")
        lines.append(f"")
        lines.append(f"**Run ID:** {data.get('run_id', 'N/A')}")
        lines.append(f"**Timestamp:** {data.get('timestamp', 'N/A')}")
        lines.append(f"**Test Cases:** {data.get('n_test_cases', 'N/A')}")
        lines.append(f"**Policy:** {data.get('policy', 'none')}")
        lines.append(f"")

        for name, pdata in data.get("providers", {}).items():
            lines.append(f"## {name}")
            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Macro F1 | {pdata.get('macro_f1', 'N/A')} |")
            lines.append(f"| Micro F1 | {pdata.get('micro_f1', 'N/A')} |")
            lines.append(f"| Calibration Error | {pdata.get('calibration_error', 'N/A')} |")
            lines.append(f"| Handoff Rate | {pdata.get('handoff_trigger_rate', 'N/A')} |")
            lines.append(f"| Handoff Precision | {pdata.get('handoff_precision', 'N/A')} |")
            lines.append(f"| Handoff Recall | {pdata.get('handoff_recall', 'N/A')} |")
            lines.append(f"")

            if pdata.get("per_category"):
                lines.append(f"### Per-Category")
                lines.append(f"")
                lines.append(f"| Category | Precision | Recall | F1 |")
                lines.append(f"|----------|-----------|--------|-----|")
                for cat, m in sorted(pdata["per_category"].items()):
                    lines.append(f"| {cat} | {m.get('precision', 'N/A')} | {m.get('recall', 'N/A')} | {m.get('f1', 'N/A')} |")
                lines.append(f"")

        Path(output).write_text("\n".join(lines))
    else:
        # JSON format — just copy with pretty print
        with open(output, "w") as f:
            json.dump(data, f, indent=2)

    click.echo(f"Report generated: {output}")


if __name__ == "__main__":
    main()
