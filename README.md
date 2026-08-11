# Housing-repair triage — eval harness

Part of the CCAR-P build-week demo. This is the **Evaluation, Testing &
Optimization** component (exam Domain 4 — the weakest-domain piece, so it's the
mandatory one).

## What it does

Triages a free-text social-housing repair request into a priority
(Emergency / Urgent / Routine) and a serious-hazard flag, using the Claude API
with structured outputs. It then runs an **A/B of two prompt variants** over a
labelled 20-case dataset and reports the metrics that matter for this task:

- **Hazard recall** — the safety metric. A missed hazard (damp/mould, gas,
  electrical, sewage) is the dangerous error, so recall is the headline, not raw
  accuracy. Ties directly to Awaab's Law.
- Priority accuracy, hazard precision/F1.
- Latency (avg + p95) and cost per case.

The dataset deliberately includes traps: damp hidden in "routine"-sounding
language (cases 3, 20) and a cosmetic job a tenant labels "emergency" (case 15).
Variant B (rubric + Awaab guidance + few-shot) should beat the thin Variant A
mainly on **hazard recall**.

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # or: ant auth login
python run_eval.py
```

Per-case detail + summary metrics are written to `results/results_<timestamp>.json`.

## Files

| File | Purpose |
|------|---------|
| `dataset.jsonl` | 20 labelled cases (gold priority + hazard) |
| `eval_harness.py` | schema, the two prompt variants, metrics, A/B logic |
| `run_eval.py` | entry point + credential handling |
| `ADR.md` | architecture decisions (exam Domains 1/6 — and demo collateral) |

## Exam-domain mapping

Metric design, mixed methodologies, and A/B for an LLM system are exactly the
Domain-4 targets. The decision to make **hazard recall** the primary metric (a
false negative is worse than a false alarm) is the "which metric actually
matters" judgement the scenario questions reward.

## MCP server + dashboard (added 16 Jul)

- **MCP server (STDIO, D3):** `.venv/bin/python -m mcp_server.server` — 4 read-only tools
  (`list_repairs`, `get_repair`, `get_property_sensors`, `search_asset_docs` stub),
  property resources, damp-risk `resources/updated` notifications.
  Register in Claude Code: `claude mcp add housing-demo -- $(pwd)/.venv/bin/python -m mcp_server.server`
- **Dashboard (D4 observability):** `.venv/bin/uvicorn dashboard.backend:app --port 8123 --app-dir $(pwd)`
  → http://localhost:8123 (or preview config `ccar-demo-dashboard`). Live-tails
  `logs/events.jsonl` (every MCP tool call / resource read / notification), shows the
  estate with damp gauges + Awaab alerts, and has a "Simulate 4h sensor tick" button —
  the tick is the only writer; the MCP layer stays read-only.
- **Smoke test:** `.venv/bin/python smoke_test_mcp.py` (spawns the server over real STDIO).
- Decisions 7–12 in `ADR.md`.

## RAG layer + caching study (added 16 Jul late)

- **RAG (D3):** `search_asset_docs` is now real — section-aware chunking + hand-rolled
  BM25 over 6 mock asset docs (`mcp_server/data/asset_docs/`), hits carry doc/section
  provenance. Try it in the dashboard's "Asset-doc search" panel. ADRs 13–14.
- **Caching study (D2):** `ANTHROPIC_API_KEY=... .venv/bin/python run_caching_study.py`
  — measures uncached vs cached (rubric + corpus prefix, ~4k tok) over the 20 cases:
  cache write/read tokens, latency, cost delta. ADR 15 explains the ~1024-token
  minimum-prefix gotcha the design works around. ~40 API calls, ≈$1.25 total.
