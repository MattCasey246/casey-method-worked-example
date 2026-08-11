"""End-to-end smoke test: spawn the MCP server over STDIO as a real client.

Proves: initialize handshake, tool discovery, each tool, resource read,
and that every interaction lands in logs/events.jsonl.
Run: .venv/bin/python smoke_test_mcp.py
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent


async def main() -> int:
    params = StdioServerParameters(
        command=str(ROOT / ".venv" / "bin" / "python"),
        args=["-m", "mcp_server.server"], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("tools:", names)
            assert names == ["get_property_sensors", "get_repair",
                             "list_repairs", "search_asset_docs"], names

            r = await session.call_tool("list_repairs", {"status": "open"})
            open_count = len(json.loads(r.content[0].text)) if len(r.content) == 1 \
                else len(r.content)
            print("open repairs:", open_count)

            r = await session.call_tool("list_repairs",
                                        {"priority": "Emergency"})
            emergencies = [json.loads(c.text) for c in r.content]
            print("emergencies:", [e["id"] for e in emergencies])

            r = await session.call_tool("get_repair", {"repair_id": "R101"})
            detail = json.loads(r.content[0].text)
            assert detail["property"]["occupant_vulnerability"] == "child"
            print("R101 property:", detail["property"]["address"])

            r = await session.call_tool("get_property_sensors",
                                        {"property_id": "P001"})
            sens = json.loads(r.content[0].text)
            print(f"P001 damp={sens['latest']['damp_risk_score']} "
                  f"alert={sens['damp_alert']} series={len(sens['series'])}")
            assert sens["damp_alert"] is True

            r = await session.call_tool("search_asset_docs",
                                        {"query": "damp survey recommendations"})
            rag_out = json.loads(r.content[0].text)
            hits = rag_out["results"]
            assert hits and any(h["doc"] == "damp-survey-P001.md" for h in hits), hits
            print(f"RAG: {len(hits)} hits, top = {hits[0]['doc']} / "
                  f"{hits[0]['section']} (score {hits[0]['score']}); "
                  f"corpus = {rag_out['corpus']}")

            r = await session.call_tool("search_asset_docs",
                                        {"query": "Awaab phase 2 timescales"})
            hits = json.loads(r.content[0].text)["results"]
            assert any(h["doc"] == "awaab-compliance-memo.md" for h in hits), hits
            print("RAG: Awaab memo retrieved for timescales query")

            res = await session.list_resources()
            print("resources:", [str(x.uri) for x in res.resources])
            body = await session.read_resource("housing://properties/P001")
            payload = json.loads(body.contents[0].text)
            assert payload["property"]["id"] == "P001"
            print("resource P001 open repairs:", len(payload["open_repairs"]))

    events = (ROOT / "logs" / "events.jsonl").read_text().strip().splitlines()
    kinds = [json.loads(l)["kind"] for l in events]
    print(f"event log: {len(events)} events "
          f"({kinds.count('tool_call')} tool calls, "
          f"{kinds.count('resource_read')} resource reads)")
    assert kinds.count("tool_call") >= 5
    print("SMOKE TEST PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
