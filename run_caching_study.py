"""D2 study — prompt caching applied and MEASURED (CCAR-P Domain 2).

Scenario: the triage service carries a shared context pack on every call —
the Variant-B rubric PLUS the org's policy/asset corpus (Awaab memo, surveys,
component schedule). That prefix is identical across calls, which is exactly
what prompt caching is for.

Design notes:
- The MINIMUM CACHEABLE PREFIX IS MODEL-DEPENDENT and is the D2 gotcha this
  study demonstrates by construction. On claude-opus-4-8 (this study's model)
  it is 4096 tokens; on Sonnet 4.5/4.1 it is 1024. A prefix below the model's
  floor is silently NOT cached (no error — cache_creation_input_tokens stays 0
  and "saving" reads 0%). The rubric alone (~600 tokens) and even rubric+corpus
  (~1.9k tokens) are BELOW the 4096 Opus floor, so the cacheable unit is
  rubric + corpus + a standards/procedures appendix (>4096 tokens by
  construction). build_context_pack() asserts the pack clears the floor before
  any billed call, so a mis-sized pack fails loudly instead of printing a
  misleading zero.
- Two modes over the same 20 cases: UNCACHED (plain system string) vs CACHED
  (same content, cache_control: ephemeral on the shared prefix block).
- Cache pricing: writes cost 1.25x input rate, reads 0.1x. Breakeven is
  therefore ~2 calls on the same prefix within the 5-minute TTL.

Run:  ANTHROPIC_API_KEY=... .venv/bin/python run_caching_study.py
Cost: ~40 calls with a ~5k-token prefix — roughly $1 uncached + ~$0.25 cached.
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent

MODEL = "claude-opus-4-8"
PRICE_IN = 5.0 / 1_000_000
PRICE_OUT = 25.0 / 1_000_000
PRICE_CACHE_WRITE = PRICE_IN * 1.25
PRICE_CACHE_READ = PRICE_IN * 0.10


# A standards/procedures appendix carried on every triage call. Real reference
# content (HHSRS bands, Awaab's Law timescales, repairs SLAs, tenant-data
# handling) — not filler: it is the kind of shared corpus a real service would
# pin, and it exists here to push the cacheable prefix comfortably over the
# 4096-token Opus floor so the study demonstrates a genuine cache hit.
STANDARDS_APPENDIX = """STANDARDS, HAZARD BANDS & PROCEDURES APPENDIX (authoritative reference)

1. HHSRS (Housing Health and Safety Rating System) — hazard assessment
   The 29 HHSRS hazards are each scored by likelihood x spread of harm outcomes
   into a numeric hazard score, banded A-J. Bands A-C are Category 1 hazards:
   the landlord has a statutory duty to act, and the local authority may serve
   an improvement notice or take emergency remedial action. Bands D-J are
   Category 2. Damp and mould growth is HHSRS hazard #1; excess cold is #2.
   Triage rule: any ticket describing visible mould, penetrating/rising damp,
   or condensation with respiratory-risk indicators is treated as a potential
   Category 1 damp-and-mould hazard and escalated for a surveyor inspection,
   regardless of the tenant's own severity wording.

2. Awaab's Law (Social Housing (Regulation) Act 2023, damp-and-mould provisions)
   Named after Awaab Ishak. Registered providers must investigate reported
   hazards within a fixed period of the report, and where a hazard poses a
   significant risk to health or safety, begin repair works within a further
   fixed period, with emergency hazards addressed within 24 hours. The
   provider must keep the tenant informed in writing throughout, and provide
   alternative accommodation where a dwelling cannot be made safe within the
   required timescale. Missing a damp-and-mould hazard is therefore both a
   safety failure and a statutory-breach exposure — the asymmetric cost that
   makes hazard RECALL the primary triage metric over headline accuracy.

3. Repair priority definitions and target response times
   EMERGENCY (make-safe within 24 hours): total loss of heating in cold
   weather, total loss of water, major uncontainable leak, electrical danger,
   insecure ground-floor door/window, blocked sole WC, any make-safe for an
   immediate risk to health, safety or security, and any confirmed significant
   damp-and-mould hazard under Awaab's Law.
   URGENT (attend within 3-7 working days): partial heating loss, minor
   containable leaks, non-functioning extractor fans in a room with reported
   condensation, a single inoperable WC where another is available, roof
   defects not yet causing internal water ingress.
   ROUTINE (attend within 20-28 working days): general joinery, decorative
   repairs, non-urgent plumbing, fencing, and planned-maintenance items with
   no active hazard.
   Over-escalation (routing a routine ticket as urgent) wastes resource but
   carries no safety cost; under-escalation of a hazard can injure a tenant and
   breach statute. Where the model is uncertain, it escalates.

4. Decent Homes Standard (baseline dwelling condition)
   A decent home meets the statutory minimum for housing (no Category 1 HHSRS
   hazards), is in a reasonable state of repair, has reasonably modern
   facilities and services, and provides a reasonable degree of thermal
   comfort. Tickets indicating a fall below this baseline are flagged for the
   asset-management review queue in addition to any repair action.

5. Tenant-data handling (UK GDPR / Data Protection Act 2018)
   Repair tickets contain personal data (name, address, vulnerability flags)
   and sometimes special-category data (health conditions relevant to a damp
   hazard). Processing is limited to the repairs purpose; vulnerability and
   health indicators are used only to inform prioritisation and are never
   included in outbound content beyond the service boundary. Access to the
   underlying repairs and sensor systems is read-only for the triage layer by
   construction; no tenant-identifying free text is echoed into logs.

6. Sensor and building-systems context
   Damp-risk telemetry (relative humidity, surface temperature, dew-point
   margin) is monitored per property. A property crossing the damp-risk
   threshold raises a proactive flag independent of any tenant-reported ticket;
   a reported ticket for a property already over threshold is corroborating
   evidence and raises confidence in a hazard classification.

7. Escalation and human-in-the-loop
   The triage layer classifies and routes; it does not close, cancel, or
   dispatch works autonomously. Any Emergency classification and any
   damp-and-mould hazard is queued for human confirmation before dispatch. This
   keeps an irreversible or safety-critical action behind a person, consistent
   with least-privilege operation of the connected systems.

8. Damp typology and diagnostic differentiation
   Correct routing depends on distinguishing the three damp mechanisms, because
   the remedy and urgency differ. CONDENSATION damp arises from moisture-laden
   air meeting cold surfaces; it is the most common and presents as black spot
   mould in corners, behind furniture, and around windows and cold bridges. It
   is driven by a combination of occupancy moisture, inadequate heating, and
   insufficient ventilation, and is the mechanism most often implicated in
   Awaab's Law cases. PENETRATING damp enters horizontally through a defect in
   the building envelope — a failed roof covering, cracked render, defective
   pointing, a leaking gutter or downpipe, or a breached window seal — and
   presents as localised staining that worsens after rainfall. RISING damp
   travels vertically from ground level through a failed or bridged damp-proof
   course and presents as a tide-mark up to roughly a metre above floor level,
   often with salt efflorescence. A ticket that describes mould worsening in
   cold weather and in unventilated rooms points to condensation; one that
   describes staining tied to rainfall points to penetrating damp; one that
   describes a ground-floor tide-mark points to rising damp. Where the
   description is ambiguous but health risk is indicated, the ticket is
   escalated for a surveyor rather than routed on a best-guess mechanism.

9. Ventilation and thermal-comfort standards
   Adequate ventilation is a primary control for condensation damp. Habitable
   rooms require background ventilation and, in kitchens and bathrooms,
   extract ventilation capable of removing moisture at source. A reported
   non-functioning extractor fan in a room with active condensation is
   therefore not a cosmetic fault but a contributory hazard control and is
   routed as URGENT rather than routine. Thermal comfort under the Decent Homes
   Standard requires efficient heating and effective insulation; a property
   that cannot be affordably heated to a safe temperature has an excess-cold
   hazard (HHSRS #2) that interacts with and worsens condensation damp.

10. Gas safety (Gas Safety (Installation and Use) Regulations 1998)
    Every property with a gas supply requires an annual gas safety check by a
    Gas Safe registered engineer, with a valid Landlord Gas Safety Record
    retained. Any report of a gas smell, a suspected carbon-monoxide alarm
    activation, or a gas appliance behaving abnormally is an immediate
    EMERGENCY make-safe and is escalated ahead of all other categories.

11. Electrical safety (EICR requirements)
    Fixed electrical installations require inspection and testing at intervals
    not exceeding five years, evidenced by a satisfactory Electrical
    Installation Condition Report. Reports of exposed wiring, repeated tripping,
    burning smells, scorching around sockets, or shocks from fittings are
    EMERGENCY electrical-danger make-safes.

12. Fire safety and building safety
    Communal fire-safety provisions — self-closing fire doors, protected
    escape routes, alarm and detection systems, and emergency lighting — are
    life-safety critical. A report of a wedged-open or damaged fire door, a
    sounding-but-ignored communal alarm, or an obstructed escape route is
    treated as EMERGENCY. For higher-risk residential buildings the provider
    also maintains a building-safety case and a resident-engagement duty.

13. Asbestos management
    Properties constructed or refurbished before the year 2000 may contain
    asbestos-containing materials. Any repair that risks disturbing suspected
    asbestos (drilling, cutting, or removing textured coatings, insulation
    board, or floor tiles) is paused pending an asbestos check; the triage
    layer flags such tickets rather than routing them straight to works.

14. Complaints handling and record-keeping
    Handling of dissatisfaction follows the statutory Complaint Handling Code:
    acknowledge promptly, investigate fairly, and respond within defined
    timescales, with a clear route to the Housing Ombudsman. Every triage
    decision, its rationale, the evidence relied on, and any hazard flag is
    recorded so that a decision can be audited and, if challenged, explained.
    Auditability of the automated decision is itself a governance requirement,
    not an optional extra: the observability layer exists so that what the
    system classified, why, and at what cost can be inspected after the fact.

15. Void turnaround and allocations context
    When a property becomes empty (a "void"), it is inspected, repaired to the
    lettable standard, and re-let. Void repairs that reveal a Category 1 hazard
    must be remedied before re-letting; a void ticket describing damp, mould,
    or an unsafe installation therefore blocks allocation and is prioritised
    accordingly. Newly reported hazards in an occupied home always take
    precedence over planned void works.

16. Vulnerability and reasonable adjustments
    A tenant's recorded vulnerability — a respiratory condition, a young child
    or infant in the household, reduced mobility, or a safeguarding flag —
    raises the effective priority of an otherwise-borderline hazard, because
    the spread-of-harm outcome under HHSRS is worse for a susceptible occupant.
    The Awaab Ishak case itself involved a young child with a respiratory
    vulnerability. Vulnerability data is used solely to inform prioritisation
    and reasonable adjustments and is handled as special-category personal data.

17. Repairs recharge and responsibility boundaries
    Most repairs are the provider's responsibility. A limited set of damage
    caused by tenant misuse or neglect may be rechargeable, but a safety hazard
    is never left unaddressed pending a recharge decision — the make-safe
    happens first and cost responsibility is determined separately. The triage
    layer never withholds a hazard response on responsibility grounds.

18. Contractor dispatch and appointment standards
    Confirmed works are dispatched to an in-house team or an approved
    contractor against the priority timescales above, with an appointment
    offered where the work requires access. Emergency make-safes are attended
    without waiting for a mutually convenient appointment. Failure to meet a
    published timescale is itself a service-standard breach that feeds the
    complaints and performance-monitoring processes.
"""


def build_context_pack() -> str:
    from eval_harness import SYSTEM_B
    docs_dir = HERE / "mcp_server" / "data" / "asset_docs"
    corpus = "\n\n---\n\n".join(
        f"[{p.name}]\n{p.read_text()}" for p in sorted(docs_dir.glob("*.md")))
    pack = (SYSTEM_B + "\n\nPOLICY & ASSET CONTEXT PACK (reference when relevant)\n\n"
            + corpus + "\n\n---\n\n" + STANDARDS_APPENDIX)
    # Guard the D2 gotcha: a prefix below the model's cache floor caches nothing
    # and prints a misleading 0% saving. Fail loudly instead. ~4 chars/token is
    # a conservative estimate; 4096 is the claude-opus-4-8 floor.
    approx_tokens = len(pack) // 4
    if approx_tokens < 4300:  # 4096 floor + margin for estimate error
        raise SystemExit(
            f"Context pack ~{approx_tokens} tokens is below the 4096-token "
            f"cache floor for {MODEL} (with margin). It would cache nothing and "
            f"report a false 0% saving. Enlarge the corpus/appendix before running.")
    return pack


def run_mode(client, name: str, system_param, dataset: list[dict]) -> dict:
    lat, in_tok, out_tok, cache_w, cache_r = [], 0, 0, 0, 0
    from eval_harness import triage_model
    for row in dataset:
        t0 = time.perf_counter()
        resp = client.messages.parse(
            model=MODEL, max_tokens=400, system=system_param,
            messages=[{"role": "user", "content": row["description"]}],
            output_format=triage_model())
        lat.append((time.perf_counter() - t0) * 1000)
        u = resp.usage
        in_tok += u.input_tokens
        out_tok += u.output_tokens
        cache_w += getattr(u, "cache_creation_input_tokens", 0) or 0
        cache_r += getattr(u, "cache_read_input_tokens", 0) or 0
        print(f"  [{name}] case {row['id']:>2} {lat[-1]:6.0f}ms  "
              f"in={u.input_tokens} cache_write={getattr(u,'cache_creation_input_tokens',0)} "
              f"cache_read={getattr(u,'cache_read_input_tokens',0)}")
    cost = (in_tok * PRICE_IN + out_tok * PRICE_OUT
            + cache_w * PRICE_CACHE_WRITE + cache_r * PRICE_CACHE_READ)
    return {"mode": name, "n": len(dataset),
            "input_tokens": in_tok, "output_tokens": out_tok,
            "cache_write_tokens": cache_w, "cache_read_tokens": cache_r,
            "avg_latency_ms": round(statistics.mean(lat)),
            "p95_latency_ms": round(sorted(lat)[max(0, int(len(lat)*0.95)-1)]),
            "total_cost_usd": round(cost, 4),
            "cost_per_case_usd": round(cost / len(dataset), 5)}


def main() -> int:
    import anthropic
    from eval_harness import load_dataset

    dataset = load_dataset(HERE / "dataset.jsonl")
    pack = build_context_pack()
    print(f"Context pack ~{len(pack)//4} tokens (rubric + 6-doc corpus). "
          f"{len(dataset)} cases per mode. Model: {MODEL}\n")
    client = anthropic.Anthropic()

    print("Mode 1: UNCACHED (identical prefix resent and re-billed every call)")
    uncached = run_mode(client, "U", pack, dataset)

    print("\nMode 2: CACHED (cache_control: ephemeral on the shared prefix)")
    cached_system = [{"type": "text", "text": pack,
                      "cache_control": {"type": "ephemeral"}}]
    cached = run_mode(client, "C", cached_system, dataset)

    print("\n" + "=" * 64)
    print(f"{'METRIC':<28}{'UNCACHED':>16}{'CACHED':>16}")
    print("-" * 64)
    for key, label in [("input_tokens", "Input tokens (billed full)"),
                       ("cache_write_tokens", "Cache write tokens (1.25x)"),
                       ("cache_read_tokens", "Cache read tokens (0.1x)"),
                       ("avg_latency_ms", "Avg latency (ms)"),
                       ("p95_latency_ms", "p95 latency (ms)"),
                       ("total_cost_usd", "Total cost ($)"),
                       ("cost_per_case_usd", "Cost / case ($)")]:
        print(f"{label:<28}{uncached[key]:>16}{cached[key]:>16}")
    print("=" * 64)
    saving = 1 - cached["total_cost_usd"] / uncached["total_cost_usd"]
    print(f"Cost saving from caching: {saving:.0%} across {uncached['n']} calls "
          f"(write premium amortised; breakeven ~2 calls, TTL 5 min).")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = HERE / "results" / f"caching_{stamp}.json"
    out.write_text(json.dumps({"model": MODEL, "uncached": uncached,
                               "cached": cached, "saving_pct": round(saving*100, 1)}, indent=2))
    print(f"Saved: {out.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
