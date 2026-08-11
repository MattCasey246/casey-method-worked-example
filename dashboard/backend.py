"""Dashboard backend for the CCAR-P housing demo (D4 observability made visible).

Reads the SAME data files and event log as the MCP server — it does not talk to
the MCP server directly. The MCP layer stays a clean STDIO server for MCP
clients; this backend is the ops/observability view over the shared estate.

The one thing the backend owns is the WORLD TICK: advancing the mock sensor
estate one step. That mutation deliberately lives here, not in an MCP tool, so
the MCP surface stays read-only (guardrail story for Thursday's agent).

Run:  .venv/bin/uvicorn dashboard.backend:app --port 8123 --app-dir <repo root>
"""
import asyncio
import datetime
import json
import random
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcp_server.models import DAMP_ALERT_THRESHOLD  # noqa: E402
from mcp_server.events import EVENTS_PATH, log_event  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "mcp_server" / "data"
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="housing-demo dashboard")

# Per-property tick drift: (humidity delta, damp delta). P002 climbs fastest so
# a few clicks of "tick" produce a fresh threshold crossing on demo.
TICK_DRIFT = {
    "P001": (0.6, 1), "P002": (1.8, 3), "P003": (0.1, 0), "P004": (0.2, 0),
    "P005": (0.0, 0), "P006": (0.3, 1), "P007": (0.5, 1),
}


def _load(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text())


def _latest_by_property(sensors: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in sensors:
        pid = row["property_id"]
        if pid not in latest or row["timestamp"] > latest[pid]["timestamp"]:
            latest[pid] = row
    return latest


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/properties")
def properties():
    props = _load("properties.json")
    latest = _latest_by_property(_load("sensors.json"))
    repairs = _load("repairs.json")
    out = []
    for p in props:
        sensor = latest.get(p["id"])
        open_repairs = [r for r in repairs
                        if r["property_id"] == p["id"] and r["status"] != "closed"]
        out.append({
            **p,
            "latest": sensor,
            "damp_alert": bool(sensor and sensor["damp_risk_score"] >= DAMP_ALERT_THRESHOLD),
            "open_repairs": len(open_repairs),
            "open_hazards": sum(1 for r in open_repairs if r["hazard_flag"]),
        })
    out.sort(key=lambda p: -(p["latest"]["damp_risk_score"] if p["latest"] else 0))
    return {"threshold": DAMP_ALERT_THRESHOLD, "properties": out}


@app.get("/api/repairs")
def repairs():
    addr = {p["id"]: p["address"] for p in _load("properties.json")}
    rows = [{**r, "address": addr.get(r["property_id"], "?")}
            for r in _load("repairs.json")]
    prio_rank = {"Emergency": 0, "Urgent": 1, "Routine": 2}
    status_rank = {"open": 0, "scheduled": 1, "closed": 2}
    rows.sort(key=lambda r: (status_rank[r["status"]], prio_rank[r["priority"]]))
    return {"repairs": rows}


@app.get("/api/sensors/{property_id}")
def sensors(property_id: str):
    series = sorted((s for s in _load("sensors.json")
                     if s["property_id"] == property_id),
                    key=lambda s: s["timestamp"])
    return {"series": series, "threshold": DAMP_ALERT_THRESHOLD}


@app.get("/api/events")
def events(limit: int = 60):
    if not EVENTS_PATH.exists():
        return {"events": []}
    lines = EVENTS_PATH.read_text().strip().splitlines()
    return {"events": [json.loads(l) for l in lines[-limit:]][::-1]}


@app.get("/api/events/stream")
async def events_stream():
    """SSE tail of the shared MCP event log."""
    async def gen():
        pos = EVENTS_PATH.stat().st_size if EVENTS_PATH.exists() else 0
        yield "event: hello\ndata: {}\n\n"
        while True:
            await asyncio.sleep(1)
            if not EVENTS_PATH.exists():
                continue
            size = EVENTS_PATH.stat().st_size
            if size > pos:
                with EVENTS_PATH.open() as f:
                    f.seek(pos)
                    chunk = f.read()
                pos = size
                for line in chunk.strip().splitlines():
                    yield f"data: {line}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/docsearch")
def docsearch(q: str, k: int = 3):
    """Same BM25 index the MCP tool uses — the dashboard's retrieval viewer."""
    from mcp_server import rag
    return {"results": rag.search(q, k=k), "corpus": rag.corpus_stats()}


@app.post("/api/tick")
def tick():
    """Advance the mock estate 4 hours. The dashboard's ONLY write."""
    sensors = _load("sensors.json")
    latest = _latest_by_property(sensors)
    new_rows = []
    crossings = []
    for pid, row in latest.items():
        dh, dd = TICK_DRIFT.get(pid, (0.0, 0))
        ts = (datetime.datetime.fromisoformat(row["timestamp"])
              + datetime.timedelta(hours=4))
        new = {
            "property_id": pid,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "temp_c": round(row["temp_c"] + random.uniform(-0.3, 0.3), 1),
            "humidity_pct": round(min(96.0, row["humidity_pct"] + dh), 1),
            "co2_ppm": int(row["co2_ppm"] + random.randint(-30, 30)),
            "damp_risk_score": min(100, row["damp_risk_score"] + dd),
        }
        if (row["damp_risk_score"] < DAMP_ALERT_THRESHOLD
                <= new["damp_risk_score"]):
            crossings.append(pid)
        new_rows.append(new)
    sensors.extend(new_rows)
    (DATA / "sensors.json").write_text(json.dumps(sensors, indent=1))
    log_event("server", "world.tick",
              note=f"sensor estate advanced 4h ({len(new_rows)} readings)"
                   + (f"; crossings: {crossings}" if crossings else ""))
    # The MCP server's watcher spots the file change and emits the
    # notification itself — the dashboard does not fake MCP traffic.
    return {"advanced": len(new_rows), "crossings": crossings}
