#!/usr/bin/env python3
"""
ai_setup_mcp.py -- the MCP-transport door into the Akashic Aurora (System 5).

This is the MCP twin of ``agent_cli.py``. It exposes the SAME verbs
(boot / learn / recall / status / log / story / events / handoff) as MCP tools,
and it implements them by calling ``agent_cli``'s own ``cmd_*`` functions under a
stdout capture. That is deliberate: there is ONE source of truth for what each verb
does (the CLI), and two doors onto it -- the shell (OpenCode and humans) and MCP
(Cursor / Claude Desktop). They can never drift, because the MCP tool literally runs
the CLI's code path.

Why this replaces the old archived ai_setup_mcp.py: the previous server wrapped the
pre-refactor session pipeline (session_canonical / session_supervisor / fast_cache),
which the Store/Ledger + Context + ACI refactor retired. This server wraps the CURRENT
architecture instead, via the supported entry point (agent_cli / core).

Transport: stdio by default (no port, no manual start -- Cursor/Claude spawn it).

    py -3 ai_setup_mcp.py              # stdio (default)
    py -3 ai_setup_mcp.py --http --port 18765   # optional shared HTTP process

Cross-agent continuity: every write verb (learn / log / handoff) persists through the
shared Store/Ledger on the canonical Redis (config.py: localhost:16379), so a lesson
or handoff one agent records is surfaced by the NEXT agent's `boot` -- regardless of
which door (CLI or MCP) either agent used.
"""
import argparse
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

import agent_cli

# Defaults for EVERY attribute any cmd_* reads off its argparse Namespace. A tool
# overrides only the fields it cares about; everything else falls back to these, so a
# cmd_* never trips over a missing attribute. Keep in sync with agent_cli's parsers.
_ARG_DEFAULTS = dict(
    json=False, agent_id="", task=None, query="",
    experiment=None, tried="", result="", expected="", recommend="",
    category="", success=None, confidence=None,
    kind="note", summary="", source="",
    # story
    chronicle=False, mark=None, session_end=False, track=None, theme=None,
    themes=False, at=None, chapter=None, beat=None, raw=False,
    # events
    search=None, around=None, window=None, get=None, capture=False, promote=False,
    threshold=None, detail_json=None, refs=None, agent=None, since=None, until=None,
    limit=None,
    # handoff
    to=None, note=None, blocker=None, list=False,
)


def _run(fn, **overrides) -> str:
    """Call a cmd_* with an argparse-like Namespace, returning its captured stdout.

    This is the whole trick: the CLI prints human-readable, front-loaded output; we
    capture that verbatim so the MCP tool returns the exact same text the CLI would.
    Core logging goes to stderr (safe for stdio MCP) and is left untouched.
    """
    ns = argparse.Namespace(**{**_ARG_DEFAULTS, **overrides})
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(ns)
    except SystemExit:
        pass
    except Exception as e:  # a tool must return text, never crash the MCP loop
        return f"ERROR: {type(e).__name__}: {e}\n{buf.getvalue()}".strip()
    return buf.getvalue().strip() or "(no output)"


mcp = FastMCP(
    "akashic-aurora",
    instructions=(
        "Akashic Aurora: a shared-memory system for a team of agents. FIRST on any "
        "task, call boot(agent, task) to load your ranked startup context (past lessons, "
        "the latest handoff addressed to you, project state) distilled to a token budget. "
        "As you work, give back: learn(...) records a reusable lesson; log(...) records a "
        "narrative beat; handoff(...) leaves a briefing the NEXT agent's boot surfaces "
        "automatically (cross-agent continuity). recall/status/story/events are read tools. "
        "Use a short, STABLE agent id (e.g. 'cursor', 'claude') so your contributions are "
        "attributed and your handoffs route correctly. Everything persists on shared Redis, "
        "so writes from any agent (via CLI or MCP) feed every other agent's next boot."
    ),
)


@mcp.tool()
def boot(agent: str, task: str = "") -> str:
    """Load this agent's startup context. CALL THIS FIRST on a new task.

    Returns the most relevant past lessons, the latest handoff briefing addressed to
    you, and project state -- ranked and distilled to a token budget. `agent` should be
    a short stable id (e.g. 'cursor', 'claude'); `task` tunes what context is surfaced.
    """
    return _run(agent_cli.cmd_boot, agent_id=agent, task=task or None)


@mcp.tool()
def learn(agent: str, experiment: str, tried: str = "", result: str = "",
          recommend: str = "", expected: str = "", category: str = "",
          success: str = "yes", confidence: str = "medium") -> str:
    """Record a reusable lesson into shared memory (the next agent inherits it).

    Use for real lessons only: a fix that worked, an approach that failed, a gotcha.
    Re-using the same `experiment` name UPDATES that lesson (no duplicates).
    `success` is yes|partial|no; `category` is free-form (performance/architecture/...).
    """
    return _run(agent_cli.cmd_learn, agent_id=agent, experiment=experiment, tried=tried,
                result=result, recommend=recommend, expected=expected, category=category,
                success=success, confidence=confidence)


@mcp.tool()
def recall(query: str = "") -> str:
    """Search past lessons by keyword. Empty query lists ALL lessons."""
    return _run(agent_cli.cmd_recall, query=query)


@mcp.tool()
def status() -> str:
    """Honest system status: backend, lesson count, agent-memory count, spine health."""
    return _run(agent_cli.cmd_status)


@mcp.tool()
def log(agent: str, kind: str = "note", summary: str = "", source: str = "",
        category: str = "", task: str = "") -> str:
    """Record a narrative Beat (an action/note/observation) without a full lesson.

    Lighter than learn(): captures what happened so it shows in `story` and the raw
    cross-agent event firehose. `kind` is open (note/action/observation/commit/...).
    """
    return _run(agent_cli.cmd_log, kind=kind or "note", summary=summary, source=source,
                category=category, task=task, agent_id=agent)


@mcp.tool()
def handoff(from_agent: str, to: str = "", task: str = "", note: str = "",
            blocker: str = "", list_only: bool = False) -> str:
    """Hand work to another agent -- the core cross-agent continuity verb.

    Writing a handoff leaves a briefing that the TARGET agent's next boot() surfaces
    automatically as its top context line. Set `to` + `task` (and optional `note` /
    `blocker`, blockers separated by ' || '). Set list_only=true to instead READ the
    handoffs currently addressed to `to` (or to from_agent if `to` is empty).
    """
    return _run(agent_cli.cmd_handoff, agent_id=from_agent, to=to or None,
                task=task or None, note=note or None, blocker=blocker or None,
                list=bool(list_only))


@mcp.tool()
def story(track: str = "", chronicle: bool = False) -> str:
    """Narrative overview (the Story Atlas), or one track's chapters if `track` is set.

    Set chronicle=true to (re)build the narrative from recent beats first. This is the
    high-level 'what has the team been doing' view; drill into specifics via events().
    """
    return _run(agent_cli.cmd_story, track=track or None, chronicle=bool(chronicle))


@mcp.tool()
def events(search: str = "", agent: str = "", kind: str = "", limit: int = 20) -> str:
    """Search the raw cross-agent event firehose (every agent's actions, time-ordered).

    With `search`, rank by relevance; otherwise return the most recent events. Filter by
    `agent` and/or `kind`. This is the un-distilled detail beneath the narrative.
    """
    return _run(agent_cli.cmd_events, search=search or None, agent=agent or None,
                kind=kind or None, limit=limit or 20)


# ---------------------------------------------------------------- Bifrost: real-time agent bus
# Unlike the verbs above (durable Store/Ledger via agent_cli), these are the LIVE message bus
# (core/comm/bus.py): direct/broadcast messages an agent reads from its own inbox cursor. Use a
# short stable id ('cursor', 'claude'). The bus is ephemeral; durable handoffs still use handoff().

@mcp.tool()
def bifrost_send(from_agent: str, to: str, kind: str = "chat", text: str = "") -> str:
    """Send a direct real-time message to another agent's Bifrost inbox (live, low-latency)."""
    from core.comm.bus import Bus
    mid = Bus(from_agent).send(to, kind, text)
    return f"sent {mid} -> {to}" if mid else "BUS OFFLINE (Redis unreachable)"


@mcp.tool()
def bifrost_broadcast(from_agent: str, kind: str = "announce", text: str = "") -> str:
    """Broadcast a message to EVERY agent on the Bifrost bus (each reads it from its own cursor)."""
    from core.comm.bus import Bus
    mid = Bus(from_agent).broadcast(kind, text)
    return f"broadcast {mid}" if mid else "BUS OFFLINE (Redis unreachable)"


@mcp.tool()
def bifrost_inbox(agent: str, limit: int = 20) -> str:
    """Read NEW Bifrost messages addressed to you (direct + broadcast). Advances your read cursor."""
    from core.comm.bus import Bus
    msgs = Bus(agent).inbox(limit=limit)
    if not msgs:
        return "(no new messages)"
    out = []
    for m in msgs:
        extra = f"  [+{len(m.parts)} part(s): {', '.join(p.ref or p.content_type for p in m.parts)}]" if m.parts else ""
        out.append(f"[{m.kind}] from {m.frm}: {str(m.content)[:300]}{extra}")
    return "\n".join(out)


@mcp.tool()
def bifrost_presence(agent: str = "") -> str:
    """Who is online on the Bifrost bus right now. Pass your `agent` id to also mark yourself online."""
    from core.comm.bus import Bus
    b = Bus(agent or "observer")
    if agent:
        b.register()
    live = b.presence()
    return "online: " + ", ".join(p["agent"] for p in live) if live else "(no agents online)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akashic Aurora MCP (door over agent_cli/core)")
    parser.add_argument("--http", action="store_true", help="serve over streamable-HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=18765, help="HTTP port (with --http)")
    a = parser.parse_args()
    if a.http:
        mcp.run(transport="streamable-http", port=a.port)
    else:
        mcp.run()
