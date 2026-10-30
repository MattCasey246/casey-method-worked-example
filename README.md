# The Casey Method — worked example

The worked example for **the Casey Method**, a five-stage method for secure
modernisation and safety-gated AI adoption in small and mid-sized organisations
(assess, modernise, automate, secure and govern, train and hand over). The method itself
is published separately as a citable document: *The Casey Method*, v2.0.0, Zenodo DOI
[10.5281/zenodo.23810507](https://doi.org/10.5281/zenodo.23810507). This repository holds no copy of the method text. It is a
demonstration of the method's AI gates as real, runnable artefacts: the Stage 4C
safety-first evaluation gate, the Stage 4D least-capability integration patterns,
and the Stage 5 observability dashboard handed over to the organisation, built on
a **fully synthetic** housing estate. Stages 1 to 3 use standard industry tooling
and are not reproduced here.

> **All data in this repository is synthetic.** Every property, occupant,
> organisation, survey, sensor reading, and repair record is fictitious and was
> generated for this demonstration. Any resemblance to real properties, firms,
> or persons is coincidental.

## What it demonstrates

**Stage 4C — the safety-first evaluation gate.** Triages a free-text
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
> prompt exemplar. Full disclosure in the method document, §3, Stage 4C.

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
| `dataset.jsonl` | 20 labelled synthetic cases (gold priority + hazard) |
| `eval_harness.py` | schema, the two prompt variants, metrics, A/B logic, recall bar |
| `run_eval.py` | entry point + credential handling |
| `ADR.md` | architecture decision records 1–15 |
| `CITATION.cff` | citation metadata |

## MCP server + dashboard (Stage 4D / Stage 5)

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

## RAG layer

- **Retrieval:** `search_asset_docs` — section-aware chunking + hand-rolled
  BM25 over 6 synthetic asset docs (`mcp_server/data/asset_docs/`), hits carry
  doc/section provenance. Try it in the dashboard's "Asset-doc search" panel.
  ADRs 13–14.

## Licence and citation

Code: [MIT](LICENSE). The method text is not in this repository; it is published under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) with its own DOI.
To cite the method or this implementation, see [`CITATION.cff`](CITATION.cff) —
independent implementations, replications of the Stage 4C evaluation, and
statutory-metric derivations for other jurisdictions are invited and will be
credited.
