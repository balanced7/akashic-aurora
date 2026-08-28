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

CONCURRENCY (O1, 2026-07-23 -- reconciled spec:
docs/library/report/20260723_reconciliation-mcp-door-concurrency-leve_600574.md):
The SDK session layer handles requests concurrently (task per message) but FastMCP
runs sync tools INLINE on the event loop -- so every verb used to starve the loop
(no pings, no cancellation, batches serialized behind their slowest member; the
parallel-batch wedge, chased since 2026-07-16). The door now dispatches:
  P-1  every tool is async and awaits its sync body on a WORKER THREAD
       (anyio.to_thread) -- the loop stays live for pings/cancellation/other calls;
  P-2  stdout capture is a swap-once THREAD-LOCAL proxy installed at import --
       concurrent captures cannot interleave BY CONSTRUCTION, and any stray write
       from an unarmed thread routes to STDERR, never the JSON-RPC channel;
  P-3  tiered concurrency: READ verbs run concurrently; WRITE verbs + consuming
       reads (consume=true advances cursors -- deepseek C1) + all bus sends
       (ordering semantics -- deepseek C2) serialize under ONE lock;
  P-4  gemini_web_login's Popen gets DEVNULL stdio (a child must never inherit the
       protocol pipes).
Fence: tests/test_mcp_concurrent_calls.py (C1 integrity at concurrency, C2 fast-not-
starved, C3 ping-under-load). The membrane stands: this door is for SEAT-MODEL agents;
runners keep the CLI/bus door and their single-consumer drain loops.
"""
import argparse
import io
import os
import subprocess
import sys
import threading
from pathlib import Path

import anyio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# T081-W1: this process IS the MCP door -- stamp it so any boot() routed through here
# renders 'door: MCP-native'. setdefault so an outer launcher can still override.
os.environ.setdefault("AKASHIC_SEAT_DOOR", "mcp")

from mcp.server.fastmcp import FastMCP

import agent_cli

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


# ---------------------------------------------------------------- P-2: capture physics
class _ThreadLocalStdout:
    """sys.stdout proxy, installed ONCE at import.

    A worker thread arms a per-thread buffer around a cmd_* call; writes from that
    thread land in its own buffer. Writes from any UNARMED thread route to stderr --
    the real stdout belongs exclusively to the JSON-RPC transport (which grabs
    sys.stdout.buffer via __getattr__ passthrough), so no python-level print() can
    ever corrupt protocol framing again. Replaces per-call redirect_stdout, whose
    process-global swap was only safe while dispatch was inline-serial.
    """

    def __init__(self, real):
        self._real = real
        self._tl = threading.local()

    def arm(self, buf: io.StringIO) -> None:
        self._tl.buf = buf

    def disarm(self) -> None:
        self._tl.buf = None

    def write(self, s):
        buf = getattr(self._tl, "buf", None)
        if buf is not None:
            return buf.write(s)
        return sys.stderr.write(s)

    def flush(self):
        buf = getattr(self._tl, "buf", None)
        if buf is None:
            try:
                sys.stderr.flush()
            except Exception:
                pass

    def __getattr__(self, name):  # buffer/encoding/isatty/... -> the real stream
        return getattr(self._real, name)


_stdout_proxy = _ThreadLocalStdout(sys.stdout)
sys.stdout = _stdout_proxy


# ---------------------------------------------------------------- P-5: the stdin membrane
class _StdinSeveredPopen(subprocess.Popen):
    """Every child spawned by THIS process gets DEVNULL stdin unless it asks otherwise.

    C7-4 physics: this process owns the JSON-RPC transport on fd 0. A child that
    inherits that handle makes Windows' Proactor defer the pending stdout completion
    until the next inbound frame arrives -- so the tool's work runs to completion and
    the reply never returns. The seat hangs on boot; any later frame flushes it in
    <0.07s. It cost a session on 2026-07-16 and was point-fixed on 2026-07-17 by
    severing stdin in agent_cli's `_git` helper.

    That point fix held for nine days. On 2026-07-25 `_head_commit_epoch` landed on the
    boot path without the sever and the hang came straight back (caught 2026-07-26 by
    the P6 pin, which was red). The lesson is that "remember to pass stdin=DEVNULL" is a
    HOPE, not a guard -- the same shape as the `_ARG_DEFAULTS` keep-in-sync comment that
    the parity pin replaced. An audit found 17 more unsevered spawns in MCP-reachable
    modules; each is one refactor away from being on a verb's path.

    So the invariant is enforced where it actually lives: not at 17 call sites, but at
    the ONE process that owns the handle. This also covers spawns inside third-party
    libraries, which no call-site discipline could ever reach. A caller that genuinely
    wants stdin passes it explicitly -- and `subprocess.run(input=...)` sets stdin=PIPE
    itself, so piped input (scripts/gemini_web.py et al) is untouched. DEVNULL gives a
    child an immediate EOF, which is strictly safer than a read on an inherited pipe.

    Deliberately NOT applied process-wide in agent_cli: a CLI child inheriting the
    terminal is correct there. This is door physics, and it belongs to the door.
    """

    def __init__(self, args, bufsize=-1, executable=None, stdin=None, *a, **kw):
        # stdin=None IS the inherit case -- the one thing this process must never do.
        super().__init__(args, bufsize, executable,
                         subprocess.DEVNULL if stdin is None else stdin, *a, **kw)


subprocess.Popen = _StdinSeveredPopen

# ---------------------------------------------------------------- P-3: the write tier
# ONE lock: write verbs, consuming reads, and bus sends serialize for ordering; read
# verbs never touch it. RLock so a write-tier cmd_* that internally re-enters another
# guarded body cannot deadlock itself.
_WRITE_LOCK = threading.RLock()


async def _athread(fn, *args, lock: bool = False, **kwargs):
    """P-1: run a sync body on a worker thread; the event loop stays live."""

    def _call():
        if lock:
            with _WRITE_LOCK:
                return fn(*args, **kwargs)
        return fn(*args, **kwargs)

    return await anyio.to_thread.run_sync(_call)


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
    body_file=None, outcome=None, receipt=None,
    name="", reason="",
    # T083 C7-1 (sol day-one receipt): cmd_notes reads args.all, cmd_note reads args.retire --
    # both were missing here, so the MCP twins raised AttributeError while CLI worked.
    # Keep-in-sync rule is now PINNED: tests/test_mcp_arg_defaults_parity.py walks every
    # cmd_* attribute read against this dict.
    all=False, retire=None,
    # ...and the pin's first catch, minutes after it was written: cmd_boot reads
    # args.sources_json (T081-W6 sidecar flag) -- a THIRD latent MCP-twin AttributeError,
    # masked until now by C7-4 (boot's response never returned for other reasons).
    sources_json=None,
    # T200: ask + friction twins (paying down the two `gap` entries check_door_parity has
    # carried since T171/T196a). cmd_ask reads a wide namespace and cmd_friction one extra
    # field; every attribute either reads must live here or the twin raises
    # AttributeError while the CLI works -- the C7-1 failure shape, now pinned by
    # tests/test_mcp_arg_defaults_parity.py.
    status=None, as_agent=None, text=None, prompt_file=None, peer=None,
    fan=0, prompts_file=None, wait=120.0, poll=2.0, launch=False, launch_wait=60.0,
    system="", model="", max_tokens=None, workers=None,
    window_h=168.0,
    # cmd_mailbox's seven, which the parity pin has been failing on independently of this
    # slice (verified pre-existing by stash). Same latent defect the T200 twins were built
    # to avoid: the MCP mailbox twin raises AttributeError while the CLI works. Costs seven
    # lines to close, and leaving a red pin red next to a green one it shares a mechanism
    # with is how the next reader learns to skim past it.
    intent_kind=None, intent_note=None, intent_sha=None, intent_to=None,
    limit_scan=None, open_sha=None, state_sha=None,
    # 2026-08-16 parity-pin catch, same C7-1 shape a fifth time: cmd_ask grew lens_file
    # (T256 lens work) and cmd_learn grew repeat_of (the twin's morning `repeat` verb,
    # e2b722f1) -- both CLI-only args the MCP twins would AttributeError on.
    lens_file=None, repeat_of="",
)


def _run(fn, **overrides) -> str:
    """Call a cmd_* with an argparse-like Namespace, returning its captured stdout.

    This is the whole trick: the CLI prints human-readable, front-loaded output; we
    capture that verbatim so the MCP tool returns the exact same text the CLI would.
    Core logging goes to stderr (safe for stdio MCP) and is left untouched. Capture
    rides the thread-local proxy (P-2) -- concurrent calls each own their buffer.
    """
    ns = argparse.Namespace(**{**_ARG_DEFAULTS, **overrides})
    buf = io.StringIO()
    _stdout_proxy.arm(buf)
    try:
        fn(ns)
    except SystemExit:
        pass
    except Exception as e:  # a tool must return text, never crash the MCP loop
        return f"ERROR: {type(e).__name__}: {e}\n{buf.getvalue()}".strip()
    finally:
        _stdout_proxy.disarm()
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
    """Run a scripts/*.py helper; optional stdin prompt. (Worker-thread safe: pure
    subprocess.run with captured pipes -- the child never sees the protocol fds.)"""
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
        "Chrome (gemini_web_login once). ask_gemini_panel fans to web + optional API. "
        "Concurrency-safe door (slice O1 -- a task id, not O(1) complexity): tools may be "
        "called in parallel batches; reads run concurrently; writes/sends/consumes "
        "serialize WITHIN THIS SERVER PROCESS under one lock for ordering. Across "
        "processes (CLI shells, other doors) there is no global serializer: single-key "
        "Redis operations are backend-atomic, and multi-step read-modify-write sequences "
        "need CAS or an advisory lock (see lock/unlock tools) -- do not assume cross-"
        "process ordering the door cannot give."
    ),
)


@mcp.tool()
async def boot(agent: str, task: str = "") -> str:
    """Load this agent's startup context. CALL THIS FIRST on a new task.

    Returns the most relevant past lessons, the latest handoff briefing addressed to
    you, and project state -- ranked and distilled to a token budget. `agent` should be
    a short stable id (e.g. 'cursor', 'claude'); `task` tunes what context is surfaced.
    """
    return await _athread(_run, agent_cli.cmd_boot, agent_id=agent, task=task or None)


@mcp.tool()
async def learn(agent: str, experiment: str, tried: str = "", result: str = "",
                recommend: str = "", expected: str = "", category: str = "",
                success: str = "yes", confidence: str = "medium") -> str:
    """Record a reusable lesson into shared memory (the next agent inherits it).

    Use for real lessons only: a fix that worked, an approach that failed, a gotcha.
    Re-using the same `experiment` name UPDATES that lesson (no duplicates).
    `success` is yes|partial|no; `category` is free-form (performance/architecture/...).
    """
    return await _athread(_run, agent_cli.cmd_learn, lock=True, agent_id=agent,
                          experiment=experiment, tried=tried, result=result,
                          recommend=recommend, expected=expected, category=category,
                          success=success, confidence=confidence)


@mcp.tool()
async def recall(query: str = "", full: str = "") -> str:
    """Search past lessons by keyword. Empty query lists ALL lessons.
    Pass `full` = a lesson's source pointer (e.g. learn:experiment:NAME) to pull its WHOLE record
    instead -- the one-hop escape from a capped recall_at surface to the raw evidence."""
    return await _athread(_run, agent_cli.cmd_recall, query=query, full=full or None)


@mcp.tool()
async def recall_at(path: str = "", command: str = "", agent: str = "", limit: int = 3) -> str:
    """Recall-at-action: the few highest-signal ACTIVE lessons + any peer lock for a file PATH or
    COMMAND you're about to act on, with source pointers. Deterministic, faithfulness-gated, and
    silent when nothing is relevant. Pass `path` OR `command`."""
    return await _athread(_run, agent_cli.cmd_recall_at, path=path or None,
                          command=command or None, agent_id=agent or None, limit=limit)


@mcp.tool()
async def task(args: str) -> str:
    """The governed task ledger (T078-W3: the one verb the door lacked). Pass the
    conductor subcommand as one string, e.g. 'list', 'next', 'propose "title" --by claude',
    'claim T075 --by claude', 'done T075 --commit abc123 --verified-by deepseek'.
    Transitions are GATED (approve is the human's); the ledger is git-durable and
    beats old bus messages -- read it before acting on backlog mail."""
    import shlex
    return await _athread(_run, agent_cli.cmd_task, lock=True, rest=shlex.split(args or "list"))


@mcp.tool()
async def recall_feedback(source: str, useful: bool = True, noise: bool = False) -> str:
    """Teach recall what's load-bearing: mark a recalled lesson 'useful' (default) or 'noise'
    (off-target). `source` is the lesson's pointer (e.g. learn:experiment:NAME); useful votes boost it
    in future recall, and lessons surfaced often but never useful decay on their own."""
    return await _athread(_run, agent_cli.cmd_recall_feedback, lock=True,
                          source=source, useful=useful, noise=noise)


@mcp.tool()
async def note(agent: str, title: str, note: str, context: str = "", category: str = "",
               supersedes: str = "") -> str:
    """Record a durable, write-once project note -- a decision or WHERE-WE-ARE -- into the substrate,
    not by editing a file. Re-noting the same `title` RETIRES the prior (correct by superseding). It
    surfaces at boot + notes(). Use for project state/decisions; use learn() for reusable how-to lessons."""
    return await _athread(_run, agent_cli.cmd_note, lock=True, agent_id=agent, title=title,
                          note=note, context=context, category=category,
                          supersedes=supersedes or None)


@mcp.tool()
async def notes(days: int = 0, limit: int = 25) -> str:
    """List active (non-superseded) project notes, newest first -- the write-once read side of note()."""
    return await _athread(_run, agent_cli.cmd_notes, days=days or None, limit=limit)


@mcp.tool()
async def knowledge_map(topic: str = "", per_layer: int = 6) -> str:
    """WALK the knowledge neighborhood of a TOPIC instead of querying it blind. Returns a graph:
    L1 surface (direct topic hits), L2 neighborhood (lessons reached by WALKING the related_to
    edges the system already grows -- BOTH directions; relevance alone cannot reach these),
    L3 archive (on-topic but retired/superseded -- reachable, not live). Each node carries a
    drill pointer. Complements recall (flat keyword hits) and lookback (flat rationale hits)."""
    return await _athread(_run, agent_cli.cmd_knowledge_map, query=topic, per_layer=per_layer)


@mcp.tool()
async def lock(agent: str, path: str, ttl: int = 900) -> str:
    """Claim an advisory path-lock so peers see you're editing PATH (coordination, not OS-enforced).
    Re-claiming your own refreshes the TTL. Now reachable without a shell (membrane door-parity)."""
    return await _athread(_run, agent_cli.cmd_lock, lock=True, agent_id=agent, path=path, ttl=ttl)


@mcp.tool()
async def unlock(agent: str, path: str) -> str:
    """Release an advisory path-lock you hold on PATH."""
    return await _athread(_run, agent_cli.cmd_unlock, lock=True, agent_id=agent, path=path)


@mcp.tool()
async def locks(agent: str = "") -> str:
    """Awareness: which advisory path-locks are held right now, and by whom (across all agents)."""
    return await _athread(_run, agent_cli.cmd_locks, agent_id=agent)


@mcp.tool()
async def tag_anti_pattern(experiment: str, name: str, reason: str = "") -> str:
    """Tag an EXISTING lesson as a reusable known-bad so recall WARNS on it (without clobbering its
    other fields). Grows the disconfirmers recall needs. Record the lesson first with learn()."""
    return await _athread(_run, agent_cli.cmd_tag_anti_pattern, lock=True,
                          experiment=experiment, name=name, reason=reason)


@mcp.tool()
async def status() -> str:
    """Honest system status: backend, lesson count, agent-memory count, spine health."""
    return await _athread(_run, agent_cli.cmd_status)


@mcp.tool()
async def packet_route(kind: str) -> str:
    """N0 read-only route explanation for one packet kind. Does not send or enforce."""
    return await _athread(_run, agent_cli.cmd_packet_trace, kind=kind, json=True)


@mcp.tool()
async def packet_route_stats() -> str:
    """N0 bounded logical-route and physical-mirror counters for the live namespace."""
    return await _athread(_run, agent_cli.cmd_packet_stats, json=True)


@mcp.tool()
async def mailbox(agent: str, explain: str = "", rebuild: bool = False) -> str:
    """T095 M0 shadow mailbox: per-message state for an agent (unhandled/consumed/
    replied/acked with evidence), derived read-only from the streams. Observation
    only -- touches no cursor, ack, wake, or delivery state."""
    return await _athread(_run, agent_cli.cmd_mailbox, agent_id=agent, explain=(explain or None),
                          rebuild=bool(rebuild), min_evidence=None, json=True)


@mcp.tool()
async def stats(hours: float = 24, days: int = 0) -> str:
    """The recall-value funnel: corpus size, surfaced impressions, votes, helped credits,
    and the recent window's flips vs lessons-recorded (capture-rate). The health check for
    whether recalled knowledge is actually helping and earned lessons are being captured.
    days > 0 ALSO prints a per-day trend (durable records) + the 30d pace vs the Wave-A gate."""
    return await _athread(_run, agent_cli.cmd_stats, hours=hours, days=(days or None))


@mcp.tool()
async def injections(hours: float = 24) -> str:
    """The injection ledger: everything recall pushed into agent contexts in the window --
    when, at which altitude (action/plan), for which target, which lessons, and the
    approximate token cost. Injected context is never hidden state."""
    return await _athread(_run, agent_cli.cmd_injections, hours=hours)


@mcp.tool()
async def graduate(agent: str, experiment: str, enforced_by: str = "", undo: bool = False) -> str:
    """Retire a lesson from recall surfacing because AUTOMATION now enforces its rule (a hook,
    guardrail, or CI check). It keeps full history and stays in list/recall with a [graduated]
    tag; it just stops competing for action-time recall slots. undo=True reverses a mistake."""
    return await _athread(_run, agent_cli.cmd_graduate, lock=True, agent_id=agent,
                          experiment=experiment, enforced_by=enforced_by, undo=undo)


@mcp.tool()
async def log(agent: str, kind: str = "note", summary: str = "", source: str = "",
              category: str = "", task: str = "") -> str:
    """Record a narrative Beat (an action/note/observation) without a full lesson.

    Lighter than learn(): captures what happened so it shows in `story` and the raw
    cross-agent event firehose. `kind` is open (note/action/observation/commit/...).
    """
    return await _athread(_run, agent_cli.cmd_log, lock=True, kind=kind or "note",
                          summary=summary, source=source, category=category, task=task,
                          agent_id=agent)


@mcp.tool()
async def handoff(from_agent: str, to: str = "", task: str = "", note: str = "",
                  blocker: str = "", list_only: bool = False) -> str:
    """Hand work to another agent -- the core cross-agent continuity verb.

    Writing a handoff leaves a briefing that the TARGET agent's next boot() surfaces
    automatically as its top context line. Set `to` + `task` (and optional `note` /
    `blocker`, blockers separated by ' || '). Set list_only=true to instead READ the
    handoffs currently addressed to `to` (or to from_agent if `to` is empty).
    """
    return await _athread(_run, agent_cli.cmd_handoff, lock=(not list_only),
                          agent_id=from_agent, to=to or None, task=task or None,
                          note=note or None, blocker=blocker or None, list=bool(list_only))


@mcp.tool()
async def story(track: str = "", chronicle: bool = False) -> str:
    """Narrative overview (the Story Atlas), or one track's chapters if `track` is set.

    Set chronicle=true to (re)build the narrative from recent beats first. This is the
    high-level 'what has the team been doing' view; drill into specifics via events().
    """
    return await _athread(_run, agent_cli.cmd_story, lock=bool(chronicle),
                          track=track or None, chronicle=bool(chronicle))


@mcp.tool()
async def events(search: str = "", agent: str = "", kind: str = "", limit: int = 20) -> str:
    """Search the raw cross-agent event firehose (every agent's actions, time-ordered).

    With `search`, rank by relevance; otherwise return the most recent events. Filter by
    `agent` and/or `kind`. This is the un-distilled detail beneath the narrative.
    """
    return await _athread(_run, agent_cli.cmd_events, search=search or None,
                          agent=agent or None, kind=kind or None, limit=limit or 20)


@mcp.tool()
async def promoted(limit: int = 20, since: str = "", until: str = "") -> str:
    """Query durable salient Bifrost messages (B2: kind=bifrost_msg in the event firehose).

    Survives Redis restarts via the File ledger. Salient kinds only: handoff/decision/
    completion/blocker. Ephemeral chat is NOT here -- use bifrost_inbox for live mail.
    """
    return await _athread(_run, agent_cli.cmd_promoted, limit=limit,
                          since=since or None, until=until or None)


@mcp.tool()
async def sweep(agent: str) -> str:
    """Pure awareness snapshot for exactly ``agent`` as structured JSON.

    Reads bus depth/window, bench count, routing attendance, and durable movement
    concurrently.  It does not register presence, beat worklive, advance a cursor,
    sweep expectations, or stamp a delta mark.
    """
    def _body():
        import json as _json
        from core.comm.awareness import build_snapshot
        return _json.dumps(build_snapshot(agent).as_dict(), indent=2, default=str)

    return await _athread(_body)


@mcp.tool()
async def ground(target: str, agent: str, continuity: bool = False) -> str:
    """Truthfully ground ``verb:<name>`` for exactly ``agent``.

    Returns the six-rung structured evidence ladder.  It observes declarations,
    per-door reach and authorization, wiring, test references, and canonical
    runtime proof without executing the target or changing shared state.
    """
    def _body():
        import json as _json
        from core.coord.ground import ground as _ground
        return _json.dumps(_ground(target, subject=agent, continuity=continuity),
                           ensure_ascii=False, indent=2, default=str)

    return await _athread(_body)


@mcp.tool()
async def capture(agent: str, thread: str, as_doc: bool = False, title: str = "",
                  cites: str = "", type: str = "chronicle", arc: str = "",
                  per_stream: int = 1000) -> str:
    """Capture one explicit-link Bifrost thread from ``agent``'s archive view.

    Collection is non-consuming and subject-bound. ``as_doc=true`` mints a
    draft conversation atom and requires the subject's ``kb.learn`` capability.
    ``cites`` is a comma-separated list of atom ids.
    """
    def _body():
        import json as _json
        from core.comm import thread_capture as _tc
        if as_doc:
            from core.trust import registry
            from core.trust.capabilities import Cap
            grant = registry.resolve(agent)
            if not grant.has(Cap.KB_LEARN):
                return _json.dumps({"ok": False, "error":
                    f"REFUSED: '{agent}' lacks {Cap.KB_LEARN.value} (role={grant.role})"})
        result = _tc.collect_thread(agent, thread, per_stream=per_stream)
        if as_doc:
            cite_rows = (list(cites) if isinstance(cites, (list, tuple)) else
                         [c.strip() for c in str(cites or "").split(",") if c.strip()])
            receipt = _tc.mint_thread_atom(result, title=title, cites=cite_rows,
                                           type_=type, arc=(arc or None))
            result = dict(result)
            result["artifact"] = receipt
            result["effects"] = [f"minted {receipt['atom_id']}"]
        return _json.dumps(result, ensure_ascii=False, indent=2, default=str)

    return await _athread(_body, lock=bool(as_doc))


@mcp.tool()
async def bifrost_sync(agent: str, limit: int = 10, consume: bool = False) -> str:
    """Bifrost pull floor: refresh presence + peek unread inbox (same data boot() shows).

    Default is non-consuming (cursor unchanged). Set consume=true to ack/read messages
    (same as bifrost_inbox). Call at turn-start in-session; boot() already peeks on startup.
    """
    # consume=true advances cursors -> WRITE tier (deepseek C1); peek stays concurrent.
    return await _athread(_run, agent_cli.cmd_bifrost_sync, lock=bool(consume),
                          agent_id=agent, limit=limit, consume=bool(consume))


# ---------------------------------------------------------------- Bifrost: real-time agent bus
# Unlike the verbs above (durable Store/Ledger via agent_cli), these are the LIVE message bus
# (core/comm/bus.py): direct/broadcast messages an agent reads from its own inbox cursor. Use a
# short stable id ('cursor', 'claude'). The bus is ephemeral; durable handoffs still use handoff().
# Sends serialize under the write lock for ORDERING (bus itself is thread-safe -- deepseek C2).

@mcp.tool()
async def bifrost_send(from_agent: str, to: str, kind: str = "chat", text: str = "",
                       expect_reply_within: int = 0) -> str:
    """Send a direct real-time message to another agent's Bifrost inbox (live, low-latency).
    expect_reply_within=SECONDS (RB-29, clamped >=30) arms a sender-side reply deadline:
    3 redrives then a loud expectation_dead, swept at boot/bifrost-sync."""

    def _body():
        from core.comm.bus import Bus
        mid = Bus(from_agent).send(to, kind, text)
        if mid and expect_reply_within:
            from core.comm.expectations import arm
            arm(from_agent, mid, to, kind, text, int(expect_reply_within))
            return f"sent {mid} -> {to} (reply expected; redrives armed)"
        return f"sent {mid} -> {to}" if mid else "BUS OFFLINE (Redis unreachable)"

    return await _athread(_body, lock=True)


@mcp.tool()
async def bifrost_nudge(from_agent: str, to: str, text: str = "", mode: str = "interrupt") -> str:
    """Send a TARGETED, fidelity-graded signal to ONE peer: mode=interrupt (HARD barge-in, default —
    the peer drops its current work at the next round boundary), steer (SOFT — fold a fact into its
    CURRENT task, no restart), or inform (AMBIENT — adopted next turn). Unlike pause, it targets one peer."""

    def _body():
        from core.comm.bus import Bus
        from core.comm import nudge as _nudge
        m = (mode or "interrupt").lower()
        if m not in ("interrupt", "steer", "inform"):
            return f"ERROR: mode must be interrupt|steer|inform (got {mode!r})"
        bus = Bus(from_agent)
        meta = {"via": f"{from_agent}-mcp", "hops": 0}
        if m == "interrupt":
            _nudge.nudge(to, by=from_agent, reason=text[:80])
            mid = bus.send(to, "nudge", text, meta=meta)
        elif m == "steer":
            _nudge.steer_push(to, from_agent, text)
            mid = bus.send(to, "steer", text, meta={**meta, "display_only": True})
        else:
            mid = bus.send(to, "inform", text, meta=meta)
        return f"nudge:{m} {mid} -> {to}" if mid else "BUS OFFLINE (Redis unreachable)"

    return await _athread(_body, lock=True)


@mcp.tool()
async def bifrost_broadcast(from_agent: str, kind: str = "announce", text: str = "") -> str:
    """Broadcast a message to EVERY agent on the Bifrost bus (each reads it from its own cursor)."""

    def _body():
        from core.comm.bus import Bus
        mid = Bus(from_agent).broadcast(kind, text)
        return f"broadcast {mid}" if mid else "BUS OFFLINE (Redis unreachable)"

    return await _athread(_body, lock=True)


@mcp.tool()
async def bifrost_inbox(agent: str, limit: int = 20, consume: bool = False) -> str:
    """Read NEW Bifrost messages addressed to you (direct + broadcast). PEEKS by default
    (cursor unmoved -- the same mail shows again next call). Pass consume=true to advance
    your cursor through the RB-21 consumer seat: if another live session/runner holds the
    seat, the read degrades to peek with a teaching line -- mail is shown, never eaten."""

    def _consume_body():
        from agent.bifrost_pull import consume_inbox
        res = consume_inbox(agent, limit=limit)
        msgs_d = (res.get("peeked") if res.get("seat_held") else res.get("consumed")) or []
        lines = [res["teach"]] if res.get("seat_held") and res.get("teach") else []
        # W65 DOOR PARITY (deepseek fence, 2026-07-25): one shared renderer, both doors.
        # The CLI door was fixed first and this one still answered "(no new messages)"
        # while the cursor advanced and asks went to the bench.
        from agent.bifrost_pull import stale_notice_lines
        lines += stale_notice_lines(res, agent)
        if not msgs_d and not lines:
            return "(no new messages)"
        lines += [f"[{m.get('kind')}] from {m.get('frm')}: {str(m.get('content'))[:300]}"
                  + (f"  [+{len(m.get('parts') or [])} part(s)]" if m.get("parts") else "")
                  for m in msgs_d]
        return "\n".join(lines)

    def _peek_body():
        from core.comm.bus import Bus
        msgs = Bus(agent).inbox(limit=limit, advance=False)
        if not msgs:
            return "(no new messages)"
        out = []
        for m in msgs:
            extra = (f"  [+{len(m.parts)} part(s): {', '.join(p.ref or p.content_type for p in m.parts)}]"
                     if m.parts else "")
            out.append(f"[{m.kind}] from {m.frm}: {str(m.content)[:300]}{extra}")
        return "\n".join(out)

    # consume advances a cursor -> WRITE tier (deepseek C1); peek stays concurrent.
    if consume:
        return await _athread(_consume_body, lock=True)
    return await _athread(_peek_body)


@mcp.tool()
async def bifrost_presence(agent: str = "") -> str:
    """Who is online on the Bifrost bus right now. Pass your `agent` id to also mark yourself online."""

    def _body():
        from core.comm.bus import Bus
        b = Bus(agent or "observer")
        if agent:
            b.register()
        live = b.presence()
        return "online: " + ", ".join(p["agent"] for p in live) if live else "(no agents online)"

    return await _athread(_body)


# ---------------------------------------------------------------- Gemini panel (web UI + AI Mode — bypass API token limits)
# Uses a dedicated Playwright Chrome profile (.secrets/gemini_web_profile). One-time login required.
# Cannot reuse your main Chrome profile or inject your Google account credentials — sign in manually once.

@mcp.tool()
async def ask(prompt: str = "", peer: str = "", as_agent: str = "claude",
              status: str = "", wait: float = 120.0, model: str = "",
              max_tokens: int = 0, fan: int = 0) -> str:
    """Ask for help. One verb, two transports, transport chosen by whether you name a peer.

    NO PEER  -- a stateless helper call: born, answers, dies inside this call. No seat, no
                lock, no cursor, no mailbox. Use `fan` for N independent answers at once
                (the aggregate reports diversity, so one answer billed N times cannot read
                as N findings).
    peer=X   -- a DURABLE ask to a real seat X, riding the bus with the full settle
                machinery underneath. Returns when it settles or when `wait` expires; an
                unsettled ask is NOT an error -- the expectation stays armed, redrives fire
                on their own schedule, and you get a handle. Check it later with status=.
    status=ID -- the seven-state readout for one durable ask (OPEN.DISPATCHED / OPEN.NOTED /
                OPEN.REDRIVING / CLOSED.ANSWERED / CLOSED.ECHO / CLOSED.DEAD / UNKNOWN),
                each carrying what the caller should do NOW.

    Returns the STRUCTURED record, not the CLI's rendered text. That is deliberate: the
    CLI writes the T197 peer verdict (peer_at_ask -- was anyone actually home when you
    asked?) to stderr, and this door captures stdout only, so a text twin would hand back
    an answer while silently dropping the reason a dead ask died.

    `launch` is NOT exposed here. On the CLI, `ask --peer X --launch` spawns X's runner if
    nobody is home; spawning a process is a privileged side effect, and this door widens
    the caller set from "someone with a shell" to "any attached seat" -- the same reasoning
    that keeps `grant` and `season_score` CLI-only. Launch a peer from the CLI, or ask a
    peer that is already attending.
    """
    if status:
        return await _athread(_run, agent_cli.cmd_ask, json=True,
                              status=status, as_agent=as_agent, text=None, launch=False)
    # A durable ask WRITES (sends + arms an expectation); the stateless helper does not.
    return await _athread(_run, agent_cli.cmd_ask, lock=bool(peer), json=True,
                          text=[prompt] if prompt else None, peer=peer or None,
                          as_agent=as_agent, wait=wait, fan=int(fan or 0),
                          model=model or "", max_tokens=(int(max_tokens) or None),
                          launch=False, status=None)


@mcp.tool()
async def friction(agent: str = "claude", window_h: float = 168.0) -> str:
    """The collaboration tax, read from evidence that already exists. WRITES NOTHING.

    Episodes from durable terminal events + armed expectation records: how many asks were
    answered, died, or echoed; time-to-settle percentiles; WHY the dead ones died (absent /
    vanished / ignored / arrived_late, from the peer's attendance at ask time AND at death);
    a per-peer breakdown worst-first; and whether a peer being present actually predicts an
    answer.

    Returns the structured record. The CLI prints its `blind` list -- what this reader
    cannot see -- to stderr, and shipping the numbers without that confession would be
    omniscience by transport. Read `blind` before quoting any figure from here.
    """
    return await _athread(_run, agent_cli.cmd_friction, json=True,
                          agent_id=agent, window_h=float(window_h))


# --- T383 tranche 1 (2026-08-26, dsh_agent): the read-family membrane paydown. The 15
#     verbs declared shared by the door-parity manifest (check_door_parity.py), now MCP
#     twins of the CLI. Same _run capture trick as every twin above: the tool returns the
#     exact text the CLI would print, and the cmd functions' own guards ride along.
#     The eye family splits into typed per-subcommand tools + one dispatcher `eye` for the
#     position verbs (look/go/back/since/inherit/stats) that are not yet census verbs.


@mcp.tool()
async def eye(eye_cmd: str, addr: str = "", seat: str = "", from_seat: str = "",
              agent: str = "", query: str = "", who: str = "", kind: str = "",
              session: str = "", as_of: str = "", limit: int = 0, patterns: str = "",
              event_id: str = "", json: bool = False) -> str:
    """THE EYE's dispatcher for the position verbs: look | go | back | since | inherit | stats
    (the query verbs have their own typed tools: find/freq/get/zoom/overview/standing/trace/
    route/ingest). Same grammar as `py agent_cli.py eye <eye_cmd> ...`."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd=eye_cmd, addr=addr or None,
                          seat=seat or None, from_seat=from_seat or None, agent=agent or None,
                          query=query or None, who=who or None, kind=kind or None,
                          session=session or None, as_of=as_of or None, limit=limit,
                          patterns=patterns.split() if patterns else [],
                          event_id=event_id or None, json=bool(json))


@mcp.tool()
async def ingest(json: bool = False) -> str:
    """[eye ingest] Index every session JSONL incrementally and rebuild the connectome edges.
    The connectome rides ingest: an edge table stale against fresh events would answer trace
    with yesterday's ancestry and no way to tell."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="ingest", json=bool(json))


@mcp.tool()
async def find(query: str, who: str = "", kind: str = "", session: str = "",
               as_of: str = "", limit: int = 0, json: bool = False) -> str:
    """[eye find] The grammar door: facets AND together -- query (text), who (voice),
    kind (event type), session, as_of (YYYY-MM-DD). Returns full-hit counts with tokens,
    degraded flags, and drill pointers -- never silent-empty."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="find", query=query or None,
                          who=who or None, kind=kind or None, session=session or None,
                          as_of=as_of or None, limit=limit, json=bool(json))


@mcp.tool()
async def freq(patterns: str, json: bool = False) -> str:
    """[eye freq] THE axis: how often a pattern family appears across sessions -- the
    thing-said-THREE-times signal (unheard / recurring / standing-directive verdict).
    patterns = space-separated phrasings OR'd together."""
    if not patterns.strip():
        return "usage: freq 'phrase1 phrase2' -- space-separated phrasings OR'd together"
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="freq",
                          patterns=patterns.split(), json=bool(json))


@mcp.tool()
async def get(event_id: str, json: bool = False) -> str:
    """[eye get] Resolve an event address (session:line) to the FULL utterance + its
    same-utterance siblings -- a citation resolves to an utterance, never a row. Ambiguous
    short prefixes REFUSE with candidates; zero matches stays an honest no-event."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="get",
                          event_id=event_id, json=bool(json))


@mcp.tool()
async def zoom(addr: str, rebuild: bool = False, json: bool = False) -> str:
    """[eye zoom] LOD navigation: a session -> its L2 digest -> an exchange. Rebuilds the
    pyramid on first call; pass rebuild to clear a stale one."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="zoom", addr=addr,
                          rebuild=bool(rebuild), json=bool(json))


@mcp.tool()
async def overview(json: bool = False) -> str:
    """[eye overview] The region map: sessions as places -- events, operator counts, spans."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="overview", json=bool(json))


@mcp.tool()
async def standing(limit: int = 0, json: bool = False) -> str:
    """[eye standing] The directive watcher: recurring operator phrasings that NO durable
    plane cites. This instrument PROPOSES -- it files nothing; read its false-positive
    confession in the output."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="standing",
                          limit=limit, json=bool(json))


@mcp.tool()
async def trace(event_id: str, depth: int = 0, formed_via: str = "",
                json: bool = False) -> str:
    """[eye trace] The connectome walk: where an utterance came from (upstream) and what
    followed (downstream). Needs `ingest` to have built the edges first."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="trace",
                          event_id=event_id, depth=depth, formed_via=formed_via or None,
                          json=bool(json))


@mcp.tool()
async def route(route_action: str, name: str = "", steps_file: str = "", by: str = "",
                resolve: bool = False, drill: bool = False, json: bool = False) -> str:
    """[eye route] Saved walkable strings through the forest: ls | save (NAME + steps-file)
    | walk (NAME). Walk history renders with the total so a count never travels alone."""
    return await _athread(_run, agent_cli.cmd_eye, eye_cmd="route",
                          route_action=route_action, name=name or None,
                          steps_file=steps_file or None, by=by or None,
                          resolve=bool(resolve), drill=bool(drill), json=bool(json))


@mcp.tool()
async def delta(agent: str, ack: bool = False) -> str:
    """The delta door (T052/R1): what moved since this agent's last boot -- commits,
    ledger transitions, bus, notes. ack advances the seen mark (boot auto-commits)."""
    return await _athread(_run, agent_cli.cmd_delta, agent_id=agent, ack=bool(ack))


@mcp.tool()
async def roster(reap: bool = False, by_agent: bool = False, json: bool = False) -> str:
    """S2 lobby: every seat's PROVEN liveness (beat freshness, never key-existence) plus
    inventory pointers. reap re-homes stranded mail from provably-dead seats."""
    return await _athread(_run, agent_cli.cmd_roster, reap=bool(reap),
                          by_agent=bool(by_agent), json=bool(json))


@mcp.tool()
async def scout(text: str, wearer: str = "", by: str = "", blind: bool = False,
                shape: str = "", json: bool = False) -> str:
    """T292: the read-only pre-flight -- 'is a seat mid-flight here / has this been done'.
    The verdict files itself UNadjudicated and waits for an operator ruling."""
    return await _athread(_run, agent_cli.cmd_scout, text=[text] if text else None,
                          wearer=wearer or None, by=by or None, blind=bool(blind),
                          shape=shape or None, json=bool(json))


@mcp.tool()
async def timeline(hours: float = 0, limit: int = 0, json: bool = False) -> str:
    """T211: the forensic super-timeline -- events + git + task transitions lined up by
    time. Coverage prints WITH the rows; a merged view missing a domain says so."""
    return await _athread(_run, agent_cli.cmd_timeline, hours=float(hours or 0),
                          limit=limit, json=bool(json))


@mcp.tool()
async def compare(a: str = "", b: str = "", list_domains: bool = False,
                  limit: int = 0, json: bool = False) -> str:
    """T213: what does one domain have that another does not -- the set difference four
    of our guards each hand-rolled. Refuses different key kinds; marks UNRELIABLE when
    either side was incompletely collected."""
    return await _athread(_run, agent_cli.cmd_compare, a=a or None, b=b or None,
                          list=bool(list_domains), limit=limit, json=bool(json))


# --- T383 tranche 2a (2026-08-26, dsh_agent): the resident-ceremony READS + repeat. The
#     ceremony's write moves stay OFF this door by decision -- peers nominate, a HUMAN
#     ratifies, the operator adjudicates (same reasoning as the ratify ruling in the
#     door-parity manifest). The MCP door carries the READ half only.


@mcp.tool()
async def resident(sub: str = "show", nominee: str = "", agent: str = "",
                   family: str = "", team: str = "", role: str = "", side: str = "",
                   exercise: str = "", provenance: str = "", shape: str = "",
                   resident: str = "", json: bool = False) -> str:
    """[resident] The callsign ceremony's door: sub = show | roster | roles | calibration
    (the read half) + nominate | assign (Daniil's approved writes, 2026-08-26). Refused
    here: ratify/place/adjudicate/verdict-file -- a HUMAN ratifies, the operator
    adjudicates; use the CLI for those."""
    if sub in ("ratify", "place", "adjudicate", "verdict-file"):
        return (f"[resident] the MCP door refuses '{sub}' -- a HUMAN ratifies and the "
                f"operator adjudicates (the ratify ruling). Use the CLI: "
                f"py agent_cli.py resident {sub} ...")
    return await _athread(_run, agent_cli.cmd_resident, sub=sub, nominee=nominee or None,
                          agent=agent or None, family=family or None, team=team or None,
                          role=role or None, side=side or None, exercise=exercise or None,
                          provenance=provenance or None, shape=shape or None,
                          resident=resident or None, json=bool(json))


@mcp.tool()
async def show(agent: str) -> str:
    """[resident show] A resident's designation, the receipts behind it, and its current
    operating role -- the permanent plane and the situational plane side by side, never merged."""
    return await _athread(_run, agent_cli.cmd_resident, sub="show", nominee=agent)


@mcp.tool()
async def roles(agent: str = "", role: str = "", side: str = "",
                exercise: str = "", provenance: str = "") -> str:
    """[resident roles] Who is operating as what -- query role assignments by agent, role,
    side, or exercise. Provenance is derived from `by`, never forged by a flag."""
    return await _athread(_run, agent_cli.cmd_resident, sub="roles", agent=agent or None,
                          role=role or None, side=side or None, exercise=exercise or None,
                          provenance=provenance or None)


@mcp.tool()
async def verdict_file(agent: str, ask_id: str, shape: str = "", gist: str = "",
                       geometry: str = "", role: str = "", cold_twin_of: str = "") -> str:
    """[resident verdict-file] File a verdict on an ask: who answered, what shape, and
    whether it is a cold twin. Lands UNadjudicated and waits for an operator ruling."""
    return await _athread(_run, agent_cli.cmd_resident, sub="verdict-file", agent=agent,
                          ask_id=ask_id, shape=shape or None, gist=gist or None,
                          geometry=geometry or None, role=role or None,
                          cold_twin_of=cold_twin_of or None)


@mcp.tool()
async def calibration(shape: str = "", resident: str = "", json: bool = False) -> str:
    """[resident calibration] The verdict ledger in COUNTS ONLY -- filed/adjudicated/
    confirmed/refuted, never rates (rates wait for RC2's n-floors; an unadjudicated
    verdict is visibly unadjudicated, never a success)."""
    return await _athread(_run, agent_cli.cmd_resident, sub="calibration",
                          shape=shape or None, resident=resident or None, json=bool(json))


@mcp.tool()
async def repeat(source: str = "", what: str = "", recall_outcome: str = "",
                 agent: str = "", report: bool = False, json: bool = False) -> str:
    """T314: record that an EXISTING lesson was violated anyway -- evidence ABOUT the
    lesson, not a new one. The number it surfaces is elapsed_s: how long a lesson
    survived before it broke (a short gap on a prose lesson says prose was the wrong
    instrument and a gate is the right one). report=True shows the ledger instead."""
    return await _athread(_run, agent_cli.cmd_repeat, source=source or None,
                          what=what or None, recall_outcome=recall_outcome or None,
                          agent=agent or None, report=bool(report), json=bool(json))


@mcp.tool()
async def nominate(nominee: str, callsign: str, by: str, receipts: str = "",
                   vendor: str = "", family: str = "", team: str = "",
                   number: str = "", note: str = "") -> str:
    """[resident nominate] Propose a callsign for a PEER (never yourself -- the registry
    refuses self-nomination). A HUMAN ratifies (rule 3); until then it is NOT active.
    Daniil approved this write on the MCP door 2026-08-26."""
    return await _athread(_run, agent_cli.cmd_resident, sub="nominate", nominee=nominee,
                          callsign=callsign, by=by,
                          receipts=[r.strip() for r in receipts.split(",") if r.strip()] or None,
                          vendor=vendor or None, family=family or None, team=team or None,
                          number=(int(number) if str(number).strip() else None),
                          note=note or None)


@mcp.tool()
async def assign(agent: str, role: str, by: str, side: str = "",
                 exercise: str = "") -> str:
    """[resident assign] Record that a resident is operating as a role -- an event, never
    a field; provenance derives from `by`, never forged by a flag. Daniil approved this
    write on the MCP door 2026-08-26."""
    return await _athread(_run, agent_cli.cmd_resident, sub="assign", nominee=agent,
                          role=role, by=by, side=side or None, exercise=exercise or None)


@mcp.tool()
async def adopt(path: str, type: str = "", title: str = "", seats: str = "") -> str:
    """[doc adopt] Mint an EXISTING loose .md as a typed atom -- NON-DESTRUCTIVE by
    construction: read, mint, leave the original exactly where it is. Type/title/seats are
    inferred when absent (override with flags). Daniil approved this write 2026-08-26."""
    return await _athread(_run, agent_cli.cmd_doc, sub="adopt", path=path,
                          type=type or None, title=title or None, seats=seats or None)


@mcp.tool()
async def bifrost_fetch(get: str, out: str = "", agent: str = "") -> str:
    """Fetch a spilled payload by content-addressed ref (blob:<sha>) or a bus message by
    stream id -- the other half of the spill; without it the pointer is decoration. Writes
    to --out when given, else prints the bytes."""
    return await _athread(_run, agent_cli.cmd_blob, get=get, out=out or None,
                          agent=agent or None)


@mcp.tool()
async def sift(terms: str, hats: str = "", planes: str = "", junction: bool = False,
               max_occurrences: int = 0, dry_run: bool = True, spend: bool = False,
               workers: int = 0, out: str = "", json: bool = False) -> str:
    """T217: the nested ask -- evidence pack -> hat fan -> curator pairs -> DISSENT FIRST.
    THE MCP TWIN IS SPEND-GATED (fan 1787717507): defaults dry_run=True (evidence pack,
    nothing spent); a live paid fan requires spend=True as a deliberate opt-in. Carried
    dissent (branch 2): a flag any seat can set is weaker than an operator-approved budget
    record -- add the record when a budget organ exists."""
    if not dry_run and not spend:
        return ("[sift] REFUSED: the MCP twin is spend-gated -- a live fan costs money. "
                "Pass dry_run=True (the default) to see the evidence pack, or spend=True "
                "to authorize the paid fan deliberately.")
    return await _athread(_run, agent_cli.cmd_sift, terms=terms.split(),
                          hats=hats or "", planes=planes or "", junction=bool(junction),
                          max_occurrences=max_occurrences, dry_run=bool(dry_run),
                          workers=workers, out=out or None, json=bool(json))


@mcp.tool()
async def ask_gemini_web(prompt: str, mode: str = "gemini", system: str = "") -> str:
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
    return await _athread(_run_gemini_web, *args, prompt=prompt, timeout=timeout)


@mcp.tool()
async def gemini_web_login() -> str:
    """One-time setup: opens Chrome so YOU can sign in to Google for free Gemini web + AI Mode.

    Sign in as your Google account (or your preferred account). Session persists in
    .secrets/gemini_web_profile/ — not your main Chrome profile (Google blocks that).
    A browser window opens on your machine; close it when done, then press Enter in the terminal.
    """
    if not (SCRIPTS / "gemini_web.py").exists():
        return "ERROR: scripts/gemini_web.py missing"

    def _body():
        try:
            # P-4: the login child must NEVER inherit this process's stdio -- anything
            # it printed would land inside the JSON-RPC channel (protocol corruption).
            subprocess.Popen(
                [sys.executable, str(SCRIPTS / "gemini_web.py"), "--login"],
                cwd=str(ROOT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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

    return await _athread(_body)


@mcp.tool()
async def ask_gemini_panel(prompt: str, system: str = "", web_mode: str = "both") -> str:
    """Fan one question to the frontier panel: Gemini web (+ AI Mode) plus optional API.

    Runs ask_gemini_web(mode=web_mode) then ask_gemini(mode=api) when an API key exists.
    Use for 3-way collab (you + Claude + Gemini) without burning Cursor/Claude tokens on the ask.
    """

    def _body():
        parts = []
        args = ["--mode", web_mode]
        if system:
            args += ["--system", system]
        web = _run_gemini_web(*args, prompt=prompt, timeout=300)
        parts.append(f"===== GEMINI WEB ({web_mode}) =====\n{web}")
        api_out = _run_script(
            "ask_gemini.py",
            *(["--system", system] if system else []),
            prompt=prompt,
        )
        if api_out and not api_out.startswith("NO_KEY"):
            parts.append(f"\n===== GEMINI API (fallback) =====\n{api_out}")
        return "\n".join(parts)

    return await _athread(_body)


# ---------------------------------------------------------------- diagnostics (test-only)
# Registered ONLY under the test/diag env so the production roster is unchanged. Routes
# through the SAME _run + capture path as every CLI-delegating tool above, so the
# concurrency fence (tests/test_mcp_concurrent_calls.py) measures the real dispatch physics.
if os.environ.get("_AISETUP_TEST_ISOLATED") or os.environ.get("AKASHIC_MCP_DIAG"):

    @mcp.tool()
    async def diag_echo_slow(tag: str, seconds: float = 2.0) -> str:
        """DIAGNOSTIC (test-only): sleep `seconds` inside the standard capture path, then
        echo the tag. Exists so the concurrency fence can time dispatch without touching
        Redis or real verbs."""
        import time as _time

        def _body(_ns):
            _time.sleep(float(seconds))
            print(f"DIAG[{tag}] slept {seconds}s")

        return await _athread(_run, _body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Akashic Aurora MCP (door over agent_cli/core)")
    parser.add_argument("--http", action="store_true", help="serve over streamable-HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=18765, help="HTTP port (with --http)")
    a = parser.parse_args()
    if a.http:
        mcp.run(transport="streamable-http", port=a.port)
    else:
        mcp.run()
