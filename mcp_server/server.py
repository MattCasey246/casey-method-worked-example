"""CCAR-P housing demo — MCP server (D3: Integration).

STDIO transport, read-only typed tools, resources for attachable context, and a
damp-risk watcher that emits `resources/updated` notifications when a property
crosses the Awaab serious-hazard threshold.

Run directly (STDIO):            .venv/bin/python -m mcp_server.server
Inspect with MCP Inspector:      npx @modelcontextprotocol/inspector .venv/bin/python -m mcp_server.server
Register in Claude Code:         claude mcp add housing-demo -- <abs path>/.venv/bin/python -m mcp_server.server

Design notes (full rationale in ADR.md):
- STDIO over StreamableHTTP: local, single-client, zero network surface.
- Tools are query-only. No mutation tools — the world is mutated by the
  dashboard's tick simulator, not by the MCP layer, which keeps Thursday's
  guardrail story clean (the agent physically cannot write).
- Resources expose records as attachable context; tools answer queries.
- Every tool call / resource read / notification is appended to
  logs/events.jsonl (D4 observability) — the dashboard tails that file.
"""
import asyncio
import json
import time
import weakref
from pathlib import Path

from pydantic import AnyUrl

from mcp.server.fastmcp import FastMCP, Context

from .models import (DAMP_ALERT_THRESHOLD, Property, Repair, RepairSummary,
                     SensorReading)
from .events import log_event

DATA = Path(__file__).resolve().parent / "data"
_sessions: "weakref.WeakSet" = weakref.WeakSet()


def _load(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text())


def _latest_damp() -> dict[str, int]:
    latest: dict[str, tuple[str, int]] = {}
    for row in _load("sensors.json"):
        pid = row["property_id"]
        if pid not in latest or row["timestamp"] > latest[pid][0]:
            latest[pid] = (row["timestamp"], row["damp_risk_score"])
    return {pid: score for pid, (_, score) in latest.items()}


async def _damp_watcher() -> None:
    """Poll sensors.json; on a threshold crossing, log + notify live sessions.

    Notifications are only deliverable while a client session is connected
    (STDIO is request/response until the client subscribes); the observability
    log records every crossing regardless, so the dashboard never misses one.
    """
    last_scores = _latest_damp()
    last_mtime = 0.0
    while True:
        await asyncio.sleep(2)
        try:
            mtime = (DATA / "sensors.json").stat().st_mtime
            if mtime == last_mtime:
                continue
            last_mtime = mtime
            scores = _latest_damp()
            for pid, score in scores.items():
                prev = last_scores.get(pid, 0)
                if prev < DAMP_ALERT_THRESHOLD <= score:
                    log_event("notification", "damp_risk.crossed",
                              args={"property_id": pid, "score": score,
                                    "threshold": DAMP_ALERT_THRESHOLD},
                              note="Awaab serious-hazard threshold crossed")
                    for session in list(_sessions):
                        try:
                            await session.send_resource_updated(
                                AnyUrl(f"housing://properties/{pid}"))
                        except Exception:
                            pass
            last_scores = scores
        except FileNotFoundError:
            continue


from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(_server: FastMCP):
    task = asyncio.create_task(_damp_watcher())
    log_event("server", "startup", note="housing-demo MCP server started (STDIO)")
    try:
        yield {}
    finally:
        task.cancel()


mcp = FastMCP("housing-demo", lifespan=_lifespan)


def _track(ctx: Context | None) -> None:
    if ctx is not None:
        try:
            _sessions.add(ctx.session)
        except Exception:
            pass


# ---------------------------------------------------------------- tools

@mcp.tool()
def list_repairs(status: str | None = None, priority: str | None = None,
                 ctx: Context = None) -> list[RepairSummary]:
    """List repairs, optionally filtered by status (open/scheduled/closed)
    and/or priority (Emergency/Urgent/Routine)."""
    _track(ctx)
    t0 = time.perf_counter()
    rows = [Repair(**r) for r in _load("repairs.json")]
    if status:
        rows = [r for r in rows if r.status == status]
    if priority:
        rows = [r for r in rows if r.priority == priority]
    out = [RepairSummary(**r.model_dump()) for r in rows]
    log_event("tool_call", "list_repairs",
              args={"status": status, "priority": priority},
              duration_ms=int((time.perf_counter() - t0) * 1000),
              result_count=len(out))
    return out


@mcp.tool()
def get_repair(repair_id: str, ctx: Context = None) -> dict:
    """Full detail for one repair, including the property it belongs to and
    the occupant vulnerability context (Awaab-relevant)."""
    _track(ctx)
    t0 = time.perf_counter()
    repair = next((r for r in _load("repairs.json") if r["id"] == repair_id), None)
    if repair is None:
        log_event("tool_call", "get_repair", args={"repair_id": repair_id},
                  duration_ms=int((time.perf_counter() - t0) * 1000),
                  note="not found")
        raise ValueError(f"No repair with id {repair_id}")
    prop = next((p for p in _load("properties.json")
                 if p["id"] == repair["property_id"]), None)
    out = {"repair": Repair(**repair).model_dump(),
           "property": Property(**prop).model_dump() if prop else None}
    log_event("tool_call", "get_repair", args={"repair_id": repair_id},
              duration_ms=int((time.perf_counter() - t0) * 1000), result_count=1)
    return out


@mcp.tool()
def get_property_sensors(property_id: str, ctx: Context = None) -> dict:
    """Latest sensor reading + 48h series for a property, with the damp-risk
    alert state against the Awaab threshold."""
    _track(ctx)
    t0 = time.perf_counter()
    series = [SensorReading(**s) for s in _load("sensors.json")
              if s["property_id"] == property_id]
    series.sort(key=lambda s: s.timestamp)
    if not series:
        log_event("tool_call", "get_property_sensors",
                  args={"property_id": property_id},
                  duration_ms=int((time.perf_counter() - t0) * 1000),
                  note="not found")
        raise ValueError(f"No sensor data for property {property_id}")
    latest = series[-1]
    out = {
        "latest": latest.model_dump(),
        "damp_alert": latest.damp_risk_score >= DAMP_ALERT_THRESHOLD,
        "threshold": DAMP_ALERT_THRESHOLD,
        "series": [s.model_dump() for s in series],
    }
    log_event("tool_call", "get_property_sensors",
              args={"property_id": property_id},
              duration_ms=int((time.perf_counter() - t0) * 1000),
              result_count=len(series))
    return out


@mcp.tool()
def search_asset_docs(query: str, k: int = 3, ctx: Context = None) -> dict:
    """Search asset documentation (surveys, EPCs, service histories, policy
    memos, component schedules). Returns the top-k chunks with document and
    section provenance so answers can be cited."""
    _track(ctx)
    t0 = time.perf_counter()
    from . import rag
    results = rag.search(query, k=k)
    log_event("tool_call", "search_asset_docs", args={"query": query, "k": k},
              duration_ms=int((time.perf_counter() - t0) * 1000),
              result_count=len(results))
    return {"results": results, "corpus": rag.corpus_stats()}


# ------------------------------------------------------------ resources

@mcp.resource("housing://properties")
def properties_resource() -> str:
    """All properties in the mock estate (read-only context)."""
    log_event("resource_read", "housing://properties")
    return json.dumps(_load("properties.json"), indent=1)


@mcp.resource("housing://properties/{property_id}")
def property_resource(property_id: str) -> str:
    """One property with its open repairs and latest sensor state."""
    prop = next((p for p in _load("properties.json") if p["id"] == property_id), None)
    if prop is None:
        raise ValueError(f"No property {property_id}")
    repairs = [r for r in _load("repairs.json")
               if r["property_id"] == property_id and r["status"] != "closed"]
    series = sorted((s for s in _load("sensors.json")
                     if s["property_id"] == property_id),
                    key=lambda s: s["timestamp"])
    log_event("resource_read", f"housing://properties/{property_id}")
    return json.dumps({"property": prop, "open_repairs": repairs,
                       "latest_sensors": series[-1] if series else None}, indent=1)


if __name__ == "__main__":
    mcp.run()  # STDIO transport
