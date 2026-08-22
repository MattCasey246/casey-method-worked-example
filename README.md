# The Casey Method — reference implementation

The working reference implementation of **the Casey Method**, a safety-gated
governance framework for AI adoption in social and assisted housing and other
essential services. The method itself is specified in [`PLAYBOOK.md`](PLAYBOOK.md)
(canonical deposit: Zenodo DOI, to be minted at deposit). This repository is the
proof that the method's instruments are real, runnable artefacts: the Stage 3
safety-first evaluation gate, the Stage 4 least-capability integration patterns,
and the Stage 5 observability dashboard, built on a **fully synthetic** housing
estate.

> **All data in this repository is synthetic.** Every property, occupant,
> organisation, survey, sensor reading, and repair record is fictitious and was
> generated for this demonstration. Any resemblance to real properties, firms,
> or persons is coincidental.

## What it demonstrates

**Stage 3 — the safety-first evaluation gate.** Triages a free-text
social-housing repair request into a priority (Emergency / Urgent / Routine)
and a serious-hazard flag, using the Claude API with structured outputs, then
runs an A/B of two prompt variants over a labelled 20-case set and scores them
with the method's metric hierarchy:

- **Hazard recall** — the safety metric, derived from statutory duty
  (Awaab's Law). A missed hazard (damp/mould, gas, electrical, sewage) is the
  dangerous error, so recall is the headline, not raw accuracy. The gate's bar
  is 100% recall on the seeded worst-failure cases; the harness prints an
  explicit pass/fail against it.
- Priority accuracy, hazard precision/F1.
- Latency (avg + p95) and cost per case.

The dataset deliberately includes traps: damp hidden in "routine"-sounding
language (cases 3, 20) and a cosmetic job a tenant labels "emergency" (case 15).

> **Methodological disclosure (evaluation design).** Variant B's few-shot
> exemplars closely mirror test cases 3 and 15, and its rubric wording
> anticipates case 20 — the rubric and the trap cases were designed together.
> Headline figures therefore partly reflect that overlap. Excluding cases 3,
> 15, and 20, Variant B still catches the one seeded hazard Variant A misses
> (9/9 vs 8/9 recall) while the accuracy difference disappears (both 88.2%).
> The stated next iteration is a held-out set with no lexical overlap with any
> prompt exemplar. Full disclosure in `PLAYBOOK.md` §3, Stage 3.

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
| `PLAYBOOK.md` | The Casey Method — the full published methodology |
| `dataset.jsonl` | 20 labelled synthetic cases (gold priority + hazard) |
| `eval_harness.py` | schema, the two prompt variants, metrics, A/B logic, recall bar |
| `run_eval.py` | entry point + credential handling |
| `ADR.md` | architecture decision records 1–15 |
| `CITATION.cff` | citation metadata |

## MCP server + dashboard (Stage 4 / Stage 5)

- **MCP server (STDIO):** `.venv/bin/python -m mcp_server.server` — 4 read-only tools
  (`list_repairs`, `get_repair`, `get_property_sensors`, `search_asset_docs`),
  property resources, damp-risk `resources/updated` notifications. A working
  example of the method's least-capability integration pattern: read-only
  surface by construction, typed narrow tools.
  Register in Claude Code: `claude mcp add housing-demo -- $(pwd)/.venv/bin/python -m mcp_server.server`
- **Dashboard (Stage 5 observability):** `.venv/bin/uvicorn dashboard.backend:app --port 8123 --app-dir $(pwd)`
  → http://localhost:8123. Live-tails `logs/events.jsonl` (every MCP tool call /
  resource read / notification), shows the estate with damp gauges + Awaab
  alerts, and has a "Simulate 4h sensor tick" button — the tick is the only
  writer; the MCP layer stays read-only (single-writer design).
- **Smoke test:** `.venv/bin/python smoke_test_mcp.py` (spawns the server over real STDIO).
- Decisions 7–12 in `ADR.md`.

## RAG layer + caching study

- **Retrieval:** `search_asset_docs` — section-aware chunking + hand-rolled
  BM25 over 6 synthetic asset docs (`mcp_server/data/asset_docs/`), hits carry
  doc/section provenance. Try it in the dashboard's "Asset-doc search" panel.
  ADRs 13–14.
- **Caching study:** `ANTHROPIC_API_KEY=... .venv/bin/python run_caching_study.py`
  — measures uncached vs cached (rubric + corpus prefix, ~4k tok) over the 20
  cases: cache write/read tokens, latency, cost delta. ADR 15 documents the
  minimum-cacheable-prefix constraint the design works around. ~40 API calls,
  ≈$1.25 total.

## Licence and citation

Code: [MIT](LICENSE). Method text (`PLAYBOOK.md`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
To cite the method or this implementation, see [`CITATION.cff`](CITATION.cff) —
independent implementations, replications of the Stage 3 evaluation, and
statutory-metric derivations for other jurisdictions are invited and will be
credited.
