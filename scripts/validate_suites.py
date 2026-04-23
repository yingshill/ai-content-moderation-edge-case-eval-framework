"""Validate all test suite JSONL files for required fields."""

from __future__ import annotations

import sys
from pathlib import Path

import jsonlines


def main() -> None:
    errors: list[str] = []
    suite_dir = Path("test_suites")

    for f in sorted(suite_dir.rglob("*.jsonl")):
        with jsonlines.open(f) as reader:
            for i, obj in enumerate(reader, 1):
                if "id" not in obj:
                    errors.append(f"{f}:{i} missing 'id'")
                if "content" not in obj:
                    errors.append(f"{f}:{i} missing 'content'")
                if "ground_truth" not in obj:
                    errors.append(f"{f}:{i} missing 'ground_truth'")

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("All test suite files validated successfully.")


if __name__ == "__main__":
    main()
