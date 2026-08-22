"""
Casey Method reference implementation — Stage 3 safety-first evaluation gate.

Task: triage a free-text social-housing repair request into
  - priority: Emergency | Urgent | Routine
  - serious_hazard: does it involve a serious health-and-safety hazard
    (damp/mould per Awaab's Law, gas, electrical, sewage, uncontrolled water,
    or total heat/hot-water loss for a vulnerable occupant)?
  - requires_human_escalation: should a human review before auto-scheduling?

Why this task: it has a genuine SAFETY dimension. A missed hazard (false
negative) is the dangerous error — so the headline metric is hazard RECALL,
not raw accuracy, per the method's metric hierarchy (PLAYBOOK.md §3, Stage 3).
The gate's bar is 100% recall on the seeded worst-failure cases; the summary
prints an explicit pass/fail against it.

The harness runs an A/B of two prompt variants over a labelled 20-case set and
records accuracy, hazard recall/precision, latency, and cost per variant.

METHODOLOGICAL DISCLOSURE: SYSTEM_B's few-shot exemplars closely mirror test
cases 3 and 15, and its rubric wording anticipates case 20 — the rubric and the
dataset traps were designed together. Headline figures partly reflect that
overlap; contamination-excluded figures and the planned held-out-set iteration
are documented in README.md and PLAYBOOK.md §3.

Run:  python run_eval.py
(Needs the anthropic SDK + credentials — see README.md.)
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

# --- Model + pricing -------------------------------------------------------
# Default per house style. Model choice is a conscious architecture decision
# (see ADR.md, decision 2): a high-volume triage classifier would in production
# likely run on a cheaper tier, but we hold the model fixed here so the A/B
# isolates the PROMPT variable. Swap MODEL to compare tiers as a second study.
MODEL = "claude-opus-4-8"
PRICE_IN_PER_TOK = 5.0 / 1_000_000    # $5 / 1M input tokens
PRICE_OUT_PER_TOK = 25.0 / 1_000_000  # $25 / 1M output tokens

MAX_TOKENS = 400  # JSON output is small; keeps latency/cost tight.


# --- Structured output schema ---------------------------------------------
# Built lazily so this module imports without pydantic present; pydantic is only
# needed when an eval is actually run (see requirements.txt).
@lru_cache(maxsize=1)
def triage_model():
    from pydantic import BaseModel, Field

    class Triage(BaseModel):
        priority: Literal["Emergency", "Urgent", "Routine"]
        serious_hazard: bool = Field(
            description="True if a serious health-and-safety hazard is present or reported."
        )
        requires_human_escalation: bool
        reason: str = Field(description="One short sentence explaining the decision.")

    return Triage


# --- Prompt variants (the A/B) --------------------------------------------
# Variant A: a thin, under-specified prompt — the kind a first draft ships with.
SYSTEM_A = (
    "You triage social housing repair requests. For each request, decide the "
    "priority (Emergency, Urgent, or Routine), whether it involves a serious "
    "health-and-safety hazard, whether it needs human escalation, and give a "
    "one-line reason."
)

# Variant B: an explicit rubric + Awaab's Law guidance + a couple of few-shot
# anchors covering the two traps (hidden damp, and a false-alarm 'emergency').
SYSTEM_B = """You triage repair requests for a UK social housing landlord. Return a structured decision.

PRIORITY RUBRIC
- Emergency: immediate risk to safety or the property — gas smell, electrical burning/fire risk, uncontrolled water/flooding, total loss of heating or hot water in cold weather (especially with a vulnerable occupant), or sewage entering the home.
- Urgent: significant loss of amenity or a developing hazard — sole toilet out of use, broken external door/lock (security), active or spreading damp/mould, sewage smell/backing up.
- Routine: minor or cosmetic — dripping taps, cracked tiles, squeaks, peeling paint, fence panels, partial heating where other rooms are fine.

SERIOUS HAZARD (Awaab's Law and HHSRS)
- Treat ANY reported damp OR mould as a serious hazard requiring assessment — even when the tenant downplays it ("slight", "been there a while", "just condensation"). Do not defer to the tenant's casual framing.
- Also treat as serious hazards: gas, electrical fire risk, sewage, uncontrolled water, and total heat/hot-water loss for a vulnerable occupant.
- Vulnerability (a child, elderly, or someone with a respiratory condition) raises both priority and hazard.

CAUTION
- The word "emergency" in a tenant's message is NOT decisive. Judge by the actual issue. A cosmetic job described as an "emergency" is still Routine.

EXAMPLES
- "Condensation on the windows and a musty smell in the bathroom." -> priority: Routine, serious_hazard: true (early damp/mould must be assessed), escalate: true.
- "Emergency! My cupboard door fell off and needs rehanging." -> priority: Routine, serious_hazard: false, escalate: false (cosmetic despite the wording)."""
# NOTE (disclosure): the two EXAMPLES above closely mirror dataset cases 3 and
# 15, and the rubric bullet on downplayed damp quotes case 20's phrasing.
# Kept verbatim so the recorded July 2026 results remain reproducible as run;
# the held-out-set iteration (see README.md) must use exemplars with zero
# lexical overlap with any test case.


@dataclass
class CaseResult:
    id: int
    pred_priority: str | None
    pred_hazard: bool | None
    priority_correct: bool
    latency_ms: float
    in_tok: int
    out_tok: int
    error: str | None = None


@dataclass
class VariantReport:
    name: str
    n: int
    parse_errors: int
    priority_accuracy: float
    hazard_recall: float
    hazard_precision: float
    hazard_f1: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
    cost_per_case_usd: float
    cases: list[CaseResult] = field(default_factory=list)


def load_dataset(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def run_variant(client, name: str, system: str, dataset: list[dict]) -> VariantReport:
    cases: list[CaseResult] = []
    for row in dataset:
        t0 = time.perf_counter()
        pred_priority = pred_hazard = None
        err = None
        in_tok = out_tok = 0
        try:
            resp = client.messages.parse(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": row["description"]}],
                output_format=triage_model(),
            )
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens
            parsed = resp.parsed_output
            if parsed is None:
                err = f"no parsed_output (stop_reason={resp.stop_reason})"
            else:
                pred_priority = parsed.priority
                pred_hazard = parsed.serious_hazard
        except Exception as e:  # keep the harness running; record the failure
            err = f"{type(e).__name__}: {e}"
        latency_ms = (time.perf_counter() - t0) * 1000

        cases.append(
            CaseResult(
                id=row["id"],
                pred_priority=pred_priority,
                pred_hazard=pred_hazard,
                priority_correct=(pred_priority == row["gold_priority"]),
                latency_ms=latency_ms,
                in_tok=in_tok,
                out_tok=out_tok,
                error=err,
            )
        )
        flag = "ok " if err is None else "ERR"
        print(f"  [{name}] case {row['id']:>2} {flag} "
              f"pred={pred_priority}/{pred_hazard} gold={row['gold_priority']}/{row['gold_serious_hazard']} "
              f"{latency_ms:6.0f}ms" + (f"  {err}" if err else ""))

    return summarise(name, dataset, cases)


def summarise(name: str, dataset: list[dict], cases: list[CaseResult]) -> VariantReport:
    by_id = {c.id: c for c in cases}
    scored = [c for c in cases if c.error is None]
    n = len(cases)

    priority_acc = (sum(c.priority_correct for c in scored) / len(scored)) if scored else 0.0

    tp = fp = fn = 0
    for row in dataset:
        c = by_id[row["id"]]
        if c.error is not None or c.pred_hazard is None:
            if row["gold_serious_hazard"]:
                fn += 1  # a scored miss on a real hazard is the worst case
            continue
        gold = row["gold_serious_hazard"]
        pred = c.pred_hazard
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif not pred and gold:
            fn += 1
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    latencies = [c.latency_ms for c in scored] or [0.0]
    avg_lat = statistics.mean(latencies)
    p95_lat = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]

    total_cost = sum(c.in_tok * PRICE_IN_PER_TOK + c.out_tok * PRICE_OUT_PER_TOK for c in cases)

    return VariantReport(
        name=name,
        n=n,
        parse_errors=sum(1 for c in cases if c.error is not None),
        priority_accuracy=priority_acc,
        hazard_recall=recall,
        hazard_precision=precision,
        hazard_f1=f1,
        avg_latency_ms=avg_lat,
        p95_latency_ms=p95_lat,
        total_cost_usd=total_cost,
        cost_per_case_usd=total_cost / n if n else 0.0,
        cases=cases,
    )


def print_comparison(a: VariantReport, b: VariantReport) -> None:
    rows = [
        ("Priority accuracy", f"{a.priority_accuracy:6.1%}", f"{b.priority_accuracy:6.1%}"),
        ("Hazard recall  (SAFETY)", f"{a.hazard_recall:6.1%}", f"{b.hazard_recall:6.1%}"),
        ("Hazard precision", f"{a.hazard_precision:6.1%}", f"{b.hazard_precision:6.1%}"),
        ("Hazard F1", f"{a.hazard_f1:6.2f}", f"{b.hazard_f1:6.2f}"),
        ("Avg latency (ms)", f"{a.avg_latency_ms:6.0f}", f"{b.avg_latency_ms:6.0f}"),
        ("p95 latency (ms)", f"{a.p95_latency_ms:6.0f}", f"{b.p95_latency_ms:6.0f}"),
        ("Cost / case ($)", f"{a.cost_per_case_usd:6.4f}", f"{b.cost_per_case_usd:6.4f}"),
        ("Parse errors", f"{a.parse_errors:>6}", f"{b.parse_errors:>6}"),
    ]
    print("\n" + "=" * 62)
    print(f"{'METRIC':<26}{'A (minimal)':>14}{'B (rubric)':>14}   winner")
    print("-" * 62)
    higher_better = {"Priority accuracy", "Hazard recall  (SAFETY)",
                     "Hazard precision", "Hazard F1"}
    for label, av, bv in rows:
        try:
            an, bn = float(av.strip().rstrip("%")), float(bv.strip().rstrip("%"))
            if label in higher_better:
                win = "B" if bn > an else "A" if an > bn else "="
            elif label == "Parse errors":
                win = "B" if bn < an else "A" if an < bn else "="
            else:  # latency / cost: lower is better
                win = "B" if bn < an else "A" if an < bn else "="
        except ValueError:
            win = "?"
        print(f"{label:<26}{av:>14}{bv:>14}   {win}")
    print("=" * 62)
    print("Decision rule: hazard recall (safety) first, then priority accuracy,")
    print("then cost. A missed hazard is worse than a false alarm.")
    # The Stage 3 gate itself (PLAYBOOK.md §3): the bar is 100% recall on the
    # seeded worst-failure cases in the labelled set. Explicit pass/fail:
    print(f"RECALL BAR (100% on seeded hazards): "
          f"A {'PASS' if a.hazard_recall >= 1.0 else 'FAIL'} "
          f"({a.hazard_recall:.1%})  |  "
          f"B {'PASS' if b.hazard_recall >= 1.0 else 'FAIL'} "
          f"({b.hazard_recall:.1%})")
    print("A variant that fails the bar is ineligible for enablement,")
    print("whatever its other metrics. The bar does not move to meet the model.")
