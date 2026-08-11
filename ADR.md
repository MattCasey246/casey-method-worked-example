# Architecture Decision Records — housing triage eval

One line per decision, with the reasoning. This doubles as CCAR-P practice for
Domains 1 (Solution Design) and 6 (Stakeholder/Lifecycle), and as Lane-2
"here's how I reason about an AI system" collateral.

1. **Structured outputs over free-text parsing.** Used `output_config.format`
   (via `messages.parse` + a Pydantic schema) so every response is a valid
   `Triage` object. Removes brittle regex/JSON-scraping and makes the eval
   deterministic to score.

2. **Model held fixed (`claude-opus-4-8`) for the A/B.** The study isolates the
   *prompt* variable, so the model is a constant. Noted as a follow-up: a
   production triage classifier is high-volume and latency-sensitive, so a
   model-tier study (swap `MODEL`, re-run) is the natural next experiment — the
   harness already reports cost/latency to support that decision.

3. **Thinking left off (default on Opus 4.8 when `thinking` is omitted).** This
   is a bounded classification task, not open-ended reasoning; omitting thinking
   keeps latency and cost realistic for a high-throughput triage service.
   Structured outputs guarantee clean JSON regardless.

4. **Hazard recall is the primary metric, not accuracy.** A false negative (a
   missed damp/mould or gas hazard) can cause real harm and legal exposure under
   Awaab's Law; a false positive just sends a human to double-check. The scoring
   and the printed decision rule rank safety recall first, then priority
   accuracy, then cost.

5. **Human-in-the-loop via `requires_human_escalation`.** The model flags cases
   for human review rather than silently auto-actioning — the guardrail that
   makes an assistive (not autonomous) triage tool defensible to a housing
   provider's risk owner.

6. **Traps baked into the dataset on purpose.** Hidden damp (cases 3, 20) and a
   keyword false-alarm (case 15) test the two ways a naive prompt fails:
   under-reading a downplayed hazard, and over-reacting to the word "emergency".
   The eval measures whether the rubric variant actually fixes them.

## MCP server + observability dashboard (built 16 Jul, D3 + D4)

7. **STDIO transport, not StreamableHTTP.** Local, single-client (Claude
   Code / Inspector / the guarded agent), zero network surface, no auth story
   needed. StreamableHTTP is the right choice when the server is remote or
   serves multiple concurrent clients (e.g. a shared org-wide housing-data
   service behind SSO) — that trade-off is the D3 exam point; recording it
   here is the answer.

8. **Resources AND tools, deliberately split.** Property records are exposed
   as MCP *resources* (attachable, read-only context the client controls);
   queries are *tools* (parameterised calls the model makes). Same data,
   different contract — knowing which side of that line a capability sits on
   is a Domain-3 discriminator.

9. **The MCP surface is read-only; the world tick lives in the dashboard
   backend.** No mutation tools exist on the server, so Thursday's guarded
   agent physically cannot write — least-privilege enforced by construction,
   not by prompt. The only writer of estate state is the dashboard's
   `/api/tick` simulator, which stands in for the real world (sensors drift
   whether or not any AI is watching).

10. **Observability = one append-only JSONL event log, shared by writer and
    viewer.** The MCP server appends every tool call, resource read and
    notification (with args, duration, result counts) to `logs/events.jsonl`;
    the dashboard tails the file (SSE) rather than coupling to the server
    process. Either side can run alone; the log is the interface. This is the
    D4 "structured logging of tool calls" requirement made visible.

11. **Notifications: log always, deliver when connected.** A watcher task
    polls sensor state; an Awaab threshold crossing is *always* recorded as a
    `notification` event, and additionally delivered as MCP
    `resources/updated` to any live session (sessions captured per-request,
    weakly referenced). STDIO servers only have someone to notify while a
    client is attached — the log guarantees the crossing is never silently
    lost.

12. **One threshold constant, one home.** `DAMP_ALERT_THRESHOLD = 70` lives in
    `models.py` and is imported by the server, the watcher and the dashboard —
    the eval harness, MCP layer and UI all agree on what "serious hazard"
    means because there is exactly one definition.

## RAG layer + caching study (built 16 Jul late, D3 + D2)

13. **Section-aware chunking, no overlap.** Markdown headings are semantic
    boundaries in survey-style documents, so chunks follow sections (merged to
    ~180 words) and every hit carries doc + section provenance. At this corpus
    size the citation story matters more than recall micro-optimisation;
    overlap earns its complexity only when chunks split mid-argument.

14. **Lexical BM25 over embeddings — a deliberate, reversible choice.** Six
    documents, ~12 chunks, domain vocabulary shared between queries and text:
    lexical retrieval is accurate, explainable (scores are inspectable),
    dependency-free and free. The flip conditions are recorded: paraphrase-
    heavy resident-facing queries, corpus beyond a few hundred chunks,
    multilingual content, or semantic cross-document joins → Voyage embeddings
    + a vector store. Choosing the simplest retrieval that meets the
    requirement — and writing down when it stops meeting it — is the D3 point.

15. **Caching study designed around the minimum-cacheable-prefix gotcha.** The
    minimum cacheable prefix is MODEL-DEPENDENT: on `claude-opus-4-8` (this
    study's model) it is **4096 tokens**, not the 1024 that applies to
    Sonnet-4.5-tier models. A prefix below the model's floor is silently NOT
    cached — no error, `cache_creation_input_tokens` stays 0, and "saving"
    reads 0%. The Variant-B rubric alone (~600 tokens), and even rubric +
    the 6-doc asset corpus (~1.9k tokens), are both below the 4096 Opus floor.
    The study therefore caches rubric + corpus + a standards/procedures
    appendix (>4.3k tokens) as one shared prefix — realistic (triage with org
    context) and demonstrably cacheable. `build_context_pack()` now ASSERTS the
    pack clears the floor before any billed call, so a mis-sized pack fails
    loudly instead of printing a misleading zero (the earlier ~1.9k-token pack
    would have done exactly that). Writes bill 1.25x, reads 0.1x → breakeven ~2
    calls within the 5-minute TTL. Run: `run_caching_study.py` (needs an API
    key). [Corrected 23 Jul: original ADR cited the wrong 1024 floor and a
    non-existent ~4k pack size.]
