"""Entry point for the housing-repair triage eval.

Usage:
    python run_eval.py

Credentials (either works):
    export ANTHROPIC_API_KEY=sk-ant-...        # or
    ant auth login                              # stores a profile the SDK reads

Results (full per-case detail + metrics) are written to results/.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent


def main() -> int:
    try:
        import anthropic  # noqa: F401
    except ModuleNotFoundError:
        print("The 'anthropic' SDK is not installed.\n"
              "  pip install -r requirements.txt", file=sys.stderr)
        return 1

    from eval_harness import (SYSTEM_A, SYSTEM_B, MODEL, load_dataset,
                              print_comparison, run_variant)

    dataset = load_dataset(HERE / "dataset.jsonl")
    print(f"Loaded {len(dataset)} labelled cases. Model: {MODEL}\n")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY or an `ant auth login` profile

    try:
        print("Running variant A (minimal prompt)...")
        report_a = run_variant(client, "A", SYSTEM_A, dataset)
        print("\nRunning variant B (rubric + Awaab guidance + few-shot)...")
        report_b = run_variant(client, "B", SYSTEM_B, dataset)
    except anthropic.AuthenticationError:
        print("\nAuthentication failed. Set ANTHROPIC_API_KEY or run `ant auth login`,\n"
              "then re-run:  python run_eval.py", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError as e:
        print(f"\nCould not reach the API: {e}", file=sys.stderr)
        return 1

    print_comparison(report_a, report_b)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = HERE / "results" / f"results_{stamp}.json"
    out.write_text(json.dumps(
        {"model": MODEL,
         "variant_A": {k: v for k, v in asdict(report_a).items() if k != "cases"},
         "variant_B": {k: v for k, v in asdict(report_b).items() if k != "cases"},
         "cases_A": [asdict(c) for c in report_a.cases],
         "cases_B": [asdict(c) for c in report_b.cases]},
        indent=2))
    print(f"\nSaved: {out.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
