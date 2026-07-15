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

Cursor MCP config key (see mcp_global/cursor.mcp.json): ``akashic-aurora`` — not the
legacy ``breakthrough-stack`` name.

Cross-agent continuity: every write verb (learn / log / handoff) persists through the
shared Store/Ledger on the canonical Redis (config.py: localhost:16379), so a lesson
or handoff one agent records is surfaced by the NEXT agent's `boot` -- regardless of
which door (CLI or MCP) either agent used.
"""
import argparse
import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

import agent_cli

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

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
    consume=False,
    # handoff
    to=None, note=None, blocker=None, list=False,
    # stats
    hours=None, days=None,
    # graduate
    enforced_by=None, undo=False,
    # note / notes / locks (membrane slice 1b: MCP twins for shell-less agents)
    title=None, context="", supersedes=None, session="", project=False, path=None, ttl=None,
    name="", reason="",
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


_GEMINI_WEB_ENV = {
    "GEMINI_WEB_BROWSER": "invisible",
    "PYTHONUNBUFFERED": "1",
}


def _run_script(
    script: str,
    *args: str,
    prompt: str = "",
    timeout: int = 240,
    extra_env: dict | None = None,
) -> str:
    """Run a scripts/*.py helper; optional stdin prompt."""
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    env = {**os.environ, **extra_env} if extra_env else None
    try:
        p = subprocess.run(
            cmd,
            input=prompt if prompt else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
            env=env,
        )
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if p.returncode != 0 and not out:
            return f"ERROR (exit {p.returncode}): {err or '(no output)'}"
        if err and "WARNING" not in err.upper():
            return f"{out}\n{err}".strip() if out else err
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout}s running {script}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _run_gemini_web(*args: str, prompt: str = "", timeout: int = 240) -> str:
    """Run gemini_web.py with off-screen Chrome (no visible window flash)."""
    return _run_script(
        "gemini_web.py", *args, prompt=prompt, timeout=timeout, extra_env=_GEMINI_WEB_ENV
    )


mcp = FastMCP(
    "akashic-aurora",
    instructions=(
        "Akashic Aurora: a shared-memory system for a team of agents. FIRST on any "
        "task, call boot(agent, task) to load your ranked startup context (past lessons, "
        "the latest handoff addressed to you, project state) distilled to a token budget. "
        "As you work, give back: learn(...) records a reusable lesson; log(...) records a "
        "narrative beat; handoff(...) leaves a briefing the NEXT agent's boot surfaces "
        "automatically (cross-agent continuity). recall/status/story/events/promoted/bifrost_sync "
        "are read tools. bifrost_inbox/bifrost_send are the LIVE bus (ephemeral). Use a short, STABLE "
        "agent id so contributions are attributed and handoffs route correctly. Everything persists on shared Redis, "
        "so writes from any agent (via CLI or MCP) feed every other agent's next boot. "
        "FIRST each turn: boot(agent, task) surfaces unread Bifrost mail; in-session also call "
        "bifrost_inbox(agent) or bifrost_sync(agent) before acting on live messages. "
        "Free Gemini via web: ask_gemini_web(prompt, mode=gemini|ai_mode|both) uses invisible "
        "Chrome (gemini_web_login once). ask_gemini_panel fans to web + optional API."
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
def recall(query: str = "", full: str = "") -> str:
    """Search past lessons by keyword. Empty query lists ALL lessons.
    Pass `full` = a lesson's source pointer (e.g. learn:experiment:NAME) to pull its WHOLE record
    instead -- the one-hop escape from a capped recall_at surface to the raw evidence."""
    return _run(agent_cli.cmd_recall, query=query, full=full or None)


@mcp.tool()
def recall_at(path: str = "", command: str = "", agent: str = "", limit: int = 3) -> str:
    """Recall-at-action: the few highest-signal ACTIVE lessons + any peer lock for a file PATH or
    COMMAND you're about to act on, with source pointers. Deterministic, faithfulness-gated, and
    silent when nothing is relevant. Pass `path` OR `command`."""
    return _run(agent_cli.cmd_recall_at, path=path or None, command=command or None,
                agent_id=agent or None, limit=limit)


@mcp.tool()
def recall_feedback(source: str, useful: bool = True, noise: bool = False) -> str:
    """Teach recall what's load-bearing: mark a recalled lesson 'useful' (default) or 'noise'
    (off-target). `source` is the lesson's pointer (e.g. learn:experiment:NAME); useful votes boost it
    in future recall, and lessons surfaced often but never useful decay on their own."""
    return _run(agent_cli.cmd_recall_feedback, source=source, useful=useful, noise=noise)


@mcp.tool()
def note(agent: str, title: str, note: str, context: str = "", category: str = "",
         supersedes: str = "") -> str:
    """Record a durable, write-once project note -- a decision or WHERE-WE-ARE -- into the substrate,
    not by editing a file. Re-noting the same `title` RETIRES the prior (correct by superseding). It
    surfaces at boot + notes(). Use for project state/decisions; use learn() for reusable how-to lessons."""
    return _run(agent_cli.cmd_note, agent_id=agent, title=title, note=note, context=context,
                category=category, supersedes=supersedes or None)


@mcp.tool()
def notes(days: int = 0, limit: int = 25) -> str:
    """List active (non-superseded) project notes, newest first -- the write-once read side of note()."""
    return _run(agent_cli.cmd_notes, days=days or None, limit=limit)


@mcp.tool()
def knowledge_map(topic: str = "", per_layer: int = 6) -> str:
    """WALK the knowledge neighborhood of a TOPIC instead of querying it blind. Returns a graph:
    L1 surface (direct topic hits), L2 neighborhood (lessons reached by WALKING the related_to
    edges the system already grows -- BOTH directions; relevance alone cannot reach these),
    L3 archive (on-topic but retired/superseded -- reachable, not live). Each node carries a
    drill pointer. Complements recall (flat keyword hits) and lookback (flat rationale hits)."""
    return _run(agent_cli.cmd_knowledge_map, query=topic, per_layer=per_layer)


@mcp.tool()
def lock(agent: str, path: str, ttl: int = 900) -> str:
    """Claim an advisory path-lock so peers see you're editing PATH (coordination, not OS-enforced).
    Re-claiming your own refreshes the TTL. Now reachable without a shell (membrane door-parity)."""
    return _run(agent_cli.cmd_lock, agent_id=agent, path=path, ttl=ttl)


@mcp.tool()
def unlock(agent: str, path: str) -> str:
    """Release an advisory path-lock you hold on PATH."""
    return _run(agent_cli.cmd_unlock, agent_id=agent, path=path)


@mcp.tool()
def locks(agent: str = "") -> str:
    """Awareness: which advisory path-locks are held right now, and by whom (across all agents)."""
    return _run(agent_cli.cmd_locks, agent_id=agent)


@mcp.tool()
def tag_anti_pattern(experiment: str, name: str, reason: str = "") -> str:
    """Tag an EXISTING lesson as a reusable known-bad so recall WARNS on it (without clobbering its
    other fields). Grows the disconfirmers recall needs. Record the lesson first with learn()."""
    return _run(agent_cli.cmd_tag_anti_pattern, experiment=experiment, name=name, reason=reason)


@mcp.tool()
def status() -> str:
    """Honest system status: backend, lesson count, agent-memory count, spine health."""
    return _run(agent_cli.cmd_status)


@mcp.tool()
def stats(hours: float = 24, days: int = 0) -> str:
    """The recall-value funnel: corpus size, surfaced impressions, votes, helped credits,
    and the recent window's flips vs lessons-recorded (capture-rate). The health check for
    whether recalled knowledge is actually helping and earned lessons are being captured.
    days > 0 ALSO prints a per-day trend (durable records) + the 30d pace vs the Wave-A gate."""
    return _run(agent_cli.cmd_stats, hours=hours, days=(days or None))


@mcp.tool()
def injections(hours: float = 24) -> str:
    """The injection ledger: everything recall pushed into agent contexts in the window --
    when, at which altitude (action/plan), for which target, which lessons, and the
    approximate token cost. Injected context is never hidden state."""
    return _run(agent_cli.cmd_injections, hours=hours)


@mcp.tool()
def graduate(agent: str, experiment: str, enforced_by: str = "", undo: bool = False) -> str:
    """Retire a lesson from recall surfacing because AUTOMATION now enforces its rule (a hook,
    guardrail, or CI check). It keeps full history and stays in list/recall with a [graduated]
    tag; it just stops competing for action-time recall slots. undo=True reverses a mistake."""
    return _run(agent_cli.cmd_graduate, agent_id=agent, experiment=experiment,
                enforced_by=enforced_by, undo=undo)


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


@mcp.tool()
def promoted(limit: int = 20, since: str = "", until: str = "") -> str:
    """Query durable salient Bifrost messages (B2: kind=bifrost_msg in the event firehose).

    Survives Redis restarts via the File ledger. Salient kinds only: handoff/decision/
    completion/blocker. Ephemeral chat is NOT here -- use bifrost_inbox for live mail.
    """
    return _run(agent_cli.cmd_promoted, limit=limit, since=since or None, until=until or None)


@mcp.tool()
def bifrost_sync(agent: str, limit: int = 10, consume: bool = False) -> str:
    """Bifrost pull floor: refresh presence + peek unread inbox (same data boot() shows).

    Default is non-consuming (cursor unchanged). Set consume=true to ack/read messages
    (same as bifrost_inbox). Call at turn-start in-session; boot() already peeks on startup.
    """
    return _run(agent_cli.cmd_bifrost_sync, agent_id=agent, limit=limit, consume=bool(consume))


# ---------------------------------------------------------------- Bifrost: real-time agent bus
# Unlike the verbs above (durable Store/Ledger via agent_cli), these are the LIVE message bus
# (core/comm/bus.py): direct/broadcast messages an agent reads from its own inbox cursor. Use a
# short stable id ('cursor', 'claude'). The bus is ephemeral; durable handoffs still use handoff().

@mcp.tool()
def bifrost_send(from_agent: str, to: str, kind: str = "chat", text: str = "",
                 expect_reply_within: int = 0) -> str:
    """Send a direct real-time message to another agent's Bifrost inbox (live, low-latency).
    expect_reply_within=SECONDS (RB-29, clamped >=30) arms a sender-side reply deadline:
    3 redrives then a loud expectation_dead, swept at boot/bifrost-sync."""
    from core.comm.bus import Bus
    mid = Bus(from_agent).send(to, kind, text)
    if mid and expect_reply_within:
        from core.comm.expectations import arm
        arm(from_agent, mid, to, kind, text, int(expect_reply_within))
        return f"sent {mid} -> {to} (reply expected; redrives armed)"
    return f"sent {mid} -> {to}" if mid else "BUS OFFLINE (Redis unreachable)"


@mcp.tool()
def bifrost_nudge(from_agent: str, to: str, text: str = "", mode: str = "interrupt") -> str:
    """Send a TARGETED, fidelity-graded signal to ONE peer: mode=interrupt (HARD barge-in, default —
    the peer drops its current work at the next round boundary), steer (SOFT — fold a fact into its
    CURRENT task, no restart), or inform (AMBIENT — adopted next turn). Unlike pause, it targets one peer."""
    from core.comm.bus import Bus
    from core.comm import nudge as _nudge
    m = (mode or "interrupt").lower()
    if m not in ("interrupt", "steer", "inform"):
        return f"ERROR: mode must be interrupt|steer|inform (got {mode!r})"
    bus = Bus(from_agent)
    meta = {"via": f"{from_agent}-mcp", "hops": 0}
    if m == "interrupt":
        _nudge.nudge(to, by=from_agent, reason=text[:80]); mid = bus.send(to, "nudge", text, meta=meta)
    elif m == "steer":
        _nudge.steer_push(to, from_agent, text)
        mid = bus.send(to, "steer", text, meta={**meta, "display_only": True})
    else:
        mid = bus.send(to, "inform", text, meta=meta)
    return f"nudge:{m} {mid} -> {to}" if mid else "BUS OFFLINE (Redis unreachable)"


@mcp.tool()
def bifrost_broadcast(from_agent: str, kind: str = "announce", text: str = "") -> str:
    """Broadcast a message to EVERY agent on the Bifrost bus (each reads it from its own cursor)."""
    from core.comm.bus import Bus
    mid = Bus(from_agent).broadcast(kind, text)
    return f"broadcast {mid}" if mid else "BUS OFFLINE (Redis unreachable)"


@mcp.tool()
def bifrost_inbox(agent: str, limit: int = 20, consume: bool = False) -> str:
    """Read NEW Bifrost messages addressed to you (direct + broadcast). PEEKS by default
    (cursor unmoved -- the same mail shows again next call). Pass consume=true to advance
    your cursor through the RB-21 consumer seat: if another live session/runner holds the
    seat, the read degrades to peek with a teaching line -- mail is shown, never eaten."""
    if consume:
        from agent.bifrost_pull import consume_inbox
        res = consume_inbox(agent, limit=limit)
        msgs_d = (res.get("peeked") if res.get("seat_held") else res.get("consumed")) or []
        lines = [res["teach"]] if res.get("seat_held") and res.get("teach") else []
        if not msgs_d and not lines:
            return "(no new messages)"
        lines += [f"[{m.get('kind')}] from {m.get('frm')}: {str(m.get('content'))[:300]}"
                  + (f"  [+{len(m.get('parts') or [])} part(s)]" if m.get("parts") else "")
                  for m in msgs_d]
        return "\n".join(lines)
    from core.comm.bus import Bus
    msgs = Bus(agent).inbox(limit=limit, advance=False)
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


# ---------------------------------------------------------------- Gemini panel (web UI + AI Mode — bypass API token limits)
# Uses a dedicated Playwright Chrome profile (.secrets/gemini_web_profile). One-time login required.
# Cannot reuse your main Chrome profile or inject your Google account credentials — sign in manually once.

@mcp.tool()
def ask_gemini_web(prompt: str, mode: str = "gemini", system: str = "") -> str:
    """Ask Gemini via the FREE Google web surfaces (not API billing).

    Uses invisible off-screen Chrome by default (real renderer, no on-screen window).
    Typical latency: ai_mode ~15-60s; gemini chat ~30-90s.

    `mode`:
      gemini   — gemini.google.com chat (frontier web model)
      ai_mode  — Google Search AI Mode (?udm=50)
      both     — run both and return labeled answers (good for panel reviews)
      api      — fallback to ask_gemini.py (API key / free-tier API quota)

    First-time setup: call gemini_web_login() — opens a visible browser window for
    one-time Google sign-in; session persists in .secrets/gemini_web_profile/.
    NOTE: prompt is sent to Google's web UI — don't pass secrets you wouldn't share with Google.
    """
    args = ["--mode", mode]
    if system:
        args += ["--system", system]
    timeout = 300 if mode in ("ai_mode", "both") else 180
    return _run_gemini_web(*args, prompt=prompt, timeout=timeout)


@mcp.tool()
def gemini_web_login() -> str:
    """One-time setup: opens Chrome so YOU can sign in to Google for free Gemini web + AI Mode.

    Sign in as your Google account (or your preferred account). Session persists in
    .secrets/gemini_web_profile/ — not your main Chrome profile (Google blocks that).
    A browser window opens on your machine; close it when done, then press Enter in the terminal.
    """
    if not (SCRIPTS / "gemini_web.py").exists():
        return "ERROR: scripts/gemini_web.py missing"
    try:
        subprocess.Popen(
            [sys.executable, str(SCRIPTS / "gemini_web.py"), "--login"],
            cwd=str(ROOT),
        )
    except Exception as e:
        return f"ERROR: could not start login browser: {e}"
    return (
        "Login browser launching.\n"
        "1) Sign in with your Google account when prompted\n"
        "2) Confirm gemini.google.com and Google AI Mode load\n"
        "3) Close the browser, then press Enter in the login terminal\n"
        f"Profile saved under: {ROOT / '.secrets' / 'gemini_web_profile'}"
    )


@mcp.tool()
def ask_gemini_panel(prompt: str, system: str = "", web_mode: str = "both") -> str:
    """Fan one question to the frontier panel: Gemini web (+ AI Mode) plus optional API.

    Runs ask_gemini_web(mode=web_mode) then ask_gemini(mode=api) when an API key exists.
    Use for 3-way collab (you + Claude + Gemini) without burning Cursor/Claude tokens on the ask.
    """
    parts = []
    web = ask_gemini_web(prompt, mode=web_mode, system=system)
    parts.append(f"===== GEMINI WEB ({web_mode}) =====\n{web}")
    api_out = _run_script(
        "ask_gemini.py",
        *(["--system", system] if system else []),
        prompt=prompt,
    )
    if api_out and not api_out.startswith("NO_KEY"):
        parts.append(f"\n===== GEMINI API (fallback) =====\n{api_out}")
    return "\n".join(parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akashic Aurora MCP (door over agent_cli/core)")
    parser.add_argument("--http", action="store_true", help="serve over streamable-HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=18765, help="HTTP port (with --http)")
    a = parser.parse_args()
    if a.http:
        mcp.run(transport="streamable-http", port=a.port)
    else:
        mcp.run()
