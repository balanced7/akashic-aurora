"""T078-W3 PRE-REGISTERED ACCEPTANCE -- the MCP-native door.

Spec: t078-capability-surface-reconciliation-2026-07-15.md W3 (claude builds,
deepseek verifies). The server (ai_setup_mcp.py, 30 tools, CLI-delegating) has
existed since the ACI refactor; the GAP was registration (.mcp.json absent -->
no harness ever loaded it) plus the task ledger verb. Once registered, new
Claude Code sessions get boot/notes/bifrost_send/task/... as NATIVE TYPED TOOLS
-- no Bash subprocess, no ~1-2s import tax, no output-parse fragility.

Pins speak real MCP over stdio (the exact transport the harness uses):
  P1  initialize handshake completes against a fresh server subprocess
  P2  tools/list carries the core roster (boot, notes, status, handoff,
      bifrost_send, bifrost_sync, learn, recall)
  P3  a read-only round-trip works end-to-end (status tool call returns text)
  P4  the `task` ledger verb EXISTS as a tool (the one verb the roster lacked)
  P5  .mcp.json registers akashic-aurora with a stdio command that matches the
      server file actually in tree
  P6  cold + warm boot calls each return on their own inbound frame, and each
      call records exactly one boot event

Run: py -m pytest tests/test_t078_w3_mcp_door.py -q
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SERVER = os.path.join(ROOT, "ai_setup_mcp.py")
MCPJSON = os.path.join(ROOT, ".mcp.json")


async def _session(extra_env=None):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=sys.executable, args=[SERVER],
                                   cwd=ROOT,
                                   env={**os.environ, "_AISETUP_TEST_ISOLATED": "1",
                                        **(extra_env or {})})
    return stdio_client(params)


def _run(coro):
    import asyncio
    return asyncio.new_event_loop().run_until_complete(coro)


# ------------------------------------------------------------- P1 + P2 + P3 + P4
def test_p1_to_p4_handshake_roster_roundtrip_task():
    async def flow():
        from mcp import ClientSession
        client = await _session()
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await s.initialize()                              # P1
                tools = {t.name for t in (await s.list_tools()).tools}
                core = {"boot", "notes", "status", "handoff", "bifrost_send",
                        "bifrost_sync", "learn", "recall"}
                missing = core - tools
                assert not missing, f"P2: core roster missing {missing}"      # P2
                out = await s.call_tool("status", {})
                text = "".join(getattr(c, "text", "") for c in out.content)
                assert text.strip(), "P3: status round-trip returned nothing"  # P3
                assert "task" in tools, \
                    "P4: the task ledger verb must be an MCP tool (the missing verb)"
    _run(flow())


# ------------------------------------------------------------- P6 C7-4 regression
def test_p6_boot_returns_without_a_second_inbound_frame(tmp_path):
    """Cold and warm MCP boots must answer without a later frame flushing them."""
    async def flow():
        import asyncio
        import uuid
        from mcp import ClientSession
        agent = f"mcp-boot-regression-{uuid.uuid4().hex[:12]}"
        client = await _session({
            "AI_SETUP": str(tmp_path),
            "REDIS_DB": "15",
            "AKASHIC_RECALL_STATE_DIR": str(tmp_path / "recall"),
        })
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await s.initialize()
                for state in ("cold", "warm"):
                    out = await asyncio.wait_for(
                        s.call_tool("boot", {
                            "agent": agent,
                            "task": f"C7-4 {state} single-frame response pin",
                        }),
                        timeout=5.0,
                    )
                    text = "".join(getattr(c, "text", "") for c in out.content)
                    assert f"# CONTEXT for {agent}" in text
                    assert "door: MCP-native" in text

                audit = await s.call_tool("events", {
                    "search": agent,
                    "agent": agent,
                    "kind": "boot",
                    "limit": 10,
                })
                audit_text = "".join(getattr(c, "text", "") for c in audit.content)
                assert "# 2 event(s) matching" in audit_text, audit_text
    _run(flow())


# ------------------------------------------------------------- P5 registration
def test_p5_mcpjson_registers_the_real_server():
    assert os.path.exists(MCPJSON), "P5: .mcp.json missing -- the door is unregistered"
    with open(MCPJSON, encoding="utf-8") as f:
        cfg = json.load(f)
    servers = cfg.get("mcpServers") or {}
    assert "akashic-aurora" in servers, f"P5: akashic-aurora not registered ({list(servers)})"
    entry = servers["akashic-aurora"]
    joined = " ".join([str(entry.get("command", ""))] + [str(a) for a in entry.get("args", [])])
    assert "ai_setup_mcp.py" in joined, "P5: registration must point at the in-tree server"
