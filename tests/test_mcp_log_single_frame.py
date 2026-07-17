"""M1-LITE pins for the MCP ``log`` single-frame cold-start repair.

The default keyword-theme path must not import the opt-in embedding stack.  A
fresh stdio MCP server must therefore answer ``log`` without needing a second
inbound JSON-RPC frame to shake the first response loose.
"""
from __future__ import annotations

import asyncio
import builtins
import os
import sys
import types
from types import SimpleNamespace

from core.narrative.beat_log import BeatLog


def _beat():
    return SimpleNamespace(summary="routing verification", source="test:mcp-log", themes=[])


def test_default_keyword_path_does_not_import_embedding_discovery(monkeypatch):
    """Deterministic class pin: cache warmth cannot hide the eager heavy import."""
    monkeypatch.setenv("AKASHIC_EMBED_THEMES", "0")
    monkeypatch.delitem(sys.modules, "core.narrative.theme_discovery", raising=False)
    real_import = builtins.__import__
    attempted = []

    def recording_import(name, *args, **kwargs):
        if name == "core.narrative.theme_discovery":
            attempted.append(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", recording_import)
    beat = _beat()
    BeatLog.__new__(BeatLog)._assign_themes(beat, hint=None)

    assert attempted == [], (
        "default keyword theming imported the opt-in embedding module; on a fresh "
        "sync MCP handler this cold NumPy import blocks the stdio event loop"
    )
    assert "routing" in beat.themes


def test_explicit_embedding_opt_in_still_uses_discovery_selector(monkeypatch):
    """The repair is a default-path lazy import, not removal of embedding themes."""
    monkeypatch.setenv("AKASHIC_EMBED_THEMES", "1")
    calls = []

    class FakeAssigner:
        def assign(self, beat, hint):
            calls.append((beat.summary, hint))
            return ["embedding-opt-in"]

    fake_module = types.ModuleType("core.narrative.theme_discovery")
    fake_module.select_theme_assigner = lambda: FakeAssigner()
    monkeypatch.setitem(sys.modules, "core.narrative.theme_discovery", fake_module)

    beat = _beat()
    BeatLog.__new__(BeatLog)._assign_themes(beat, hint=None)

    assert calls == [("routing verification", None)]
    assert beat.themes == ["embedding-opt-in"]


def test_fresh_stdio_mcp_log_returns_without_second_frame(tmp_path):
    """Real transport pin: one request, one response, no flush-probe frame."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server = os.path.join(root, "ai_setup_mcp.py")

    async def flow():
        params = StdioServerParameters(
            command=sys.executable,
            args=[server],
            cwd=root,
            env={
                **os.environ,
                "_AISETUP_TEST_ISOLATED": "1",
                "REDIS_DB": "15",
                "AI_SETUP": str(tmp_path),
                "AKASHIC_RECALL_STATE_DIR": str(tmp_path / "recall"),
                "AKASHIC_EMBED_THEMES": "0",
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                out = await asyncio.wait_for(
                    session.call_tool(
                        "log",
                        {
                            "agent": "mcp-log-single-frame",
                            "kind": "note",
                            "summary": "single-frame transport pin",
                            "source": "test:mcp-log-single-frame",
                            "category": "test",
                            "task": "T060",
                        },
                    ),
                    timeout=5.0,
                )
                text = "".join(getattr(item, "text", "") for item in out.content)
                assert "[OK] note: single-frame transport pin" in text

    asyncio.run(flow())

