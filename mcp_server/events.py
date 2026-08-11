"""Structured event log shared by the MCP server and the dashboard (D4 observability).

Every tool call, resource read and notification is appended as one JSON line to
logs/events.jsonl. The dashboard backend tails this file, so the UI shows real
MCP traffic rather than a mock feed. Append-only JSONL keeps the writer dumb
and crash-safe; the reader owns interpretation.
"""
import json
import time
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
EVENTS_PATH = LOG_DIR / "events.jsonl"


def log_event(kind: str, name: str, *, args: dict | None = None,
              duration_ms: int | None = None, note: str | None = None,
              result_count: int | None = None) -> dict:
    """kind: tool_call | resource_read | notification | server"""
    LOG_DIR.mkdir(exist_ok=True)
    event = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "epoch_ms": int(time.time() * 1000),
        "kind": kind,
        "name": name,
    }
    if args:
        event["args"] = args
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if result_count is not None:
        event["result_count"] = result_count
    if note:
        event["note"] = note
    with EVENTS_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")
    return event
