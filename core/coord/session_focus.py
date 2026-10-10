"""Session focus -- which task THIS session's tool calls belong to, and a nudge when they drift.

WHY THIS EXISTS, with the measurement that forced it (2026-09-27).

T056 built per-task cost telemetry and made `tool_calls` one of its four fields. In 172 completed
tasks it recorded ZERO. The cause is not a bug: task_costs._active_task_for() attributes a turn to
"the ONE task owned by this agent in in_progress or verifying", and defensively returns None on 0
or >1. Measured: 11 tasks are active, NINE of them owned by `claude` and two by `sol`. Both owners
refuse. The organ has been working exactly as designed against an assumption -- the one-in-progress
gate -- that does not hold in practice.

Owner-matching cannot disambiguate nine simultaneously-open tasks. No amount of fixing
attribute_turn creates the missing information. What is missing is a PRIMITIVE: a session saying
which task it is working on. That is what this module adds, and it is the input the existing
accumulator has always needed -- writes land on task_costs' own key, so finalize() picks them up at
DONE with no second ledger and no parallel organ.

THE DRIFT NUDGE, and the guard it must not trip. task_costs.py refuses a live display on purpose:
"Render is RETRO-ONLY: done tasks only (K5 -- the Goodhart guard: no live ticker, never codify
pace)." A nudge saying "you are at 40 calls" measures HOW FAST and invites gaming; K5 rightly bans
it. A nudge saying "these calls stopped touching this task's files" measures whether the RECORD IS
TRUE. That is a correctness check, not a pace metric, and this module only ever emits the second.

It is also EVIDENCE-BASED, never a timer. A task declares `files`; a call that touches none of them
is a miss. Only a run of consecutive misses speaks. A nudge on elapsed time would fire on a long
think and become noise by Tuesday.

RETIREMENT RULE, stated up front because a capability without one is debt with a nice interface:
every nudge and every dismissal is counted (`nudges`, `dismissed`). If dismissals run at or above
DISMISS_RETIRE of nudges across real use, the detector is noise and should be turned off -- the
counters exist so that is a measurement rather than an argument.
"""

from __future__ import annotations

import contextlib
import os
import time
from typing import Any


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


def _cli() -> str:
    """The CLI as a printed command names it: `aurora` under the installed launcher, else
    `<_pyl()> agent_cli.py` (core.paths.cli_command)."""
    import os as _os

    return "aurora" if (_os.getenv("AURORA_LAUNCHER") or "").strip() else f"{_pyl()} agent_cli.py"


#: consecutive misses before the first nudge, and between repeats. Generous on purpose: reading
#: around a problem legitimately wanders, and a detector that fires during exploration is noise.
MISS_BEFORE_NUDGE = 14
#: a session stops being nudged after this many dismissals, without the operator doing anything.
DISMISS_QUIET = 2
#: the share of nudges dismissed at which the whole detector should be retired (see module docstring).
DISMISS_RETIRE = 0.5
FOCUS_TTL_S = 36 * 3600  # a focus outlives a long session but never a forgotten week


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _key(session_id: str) -> str:
    return f"{_ns()}:focus:{_safe(session_id)}"


def _safe(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


def this_session() -> str:
    """The id the HOOKS will use, read from the same environment the CLI runs in.

    Claude Code exports CLAUDE_CODE_SESSION_ID into every tool process, and its hook payloads
    carry the identical value as `session_id`. That shared value is what lets `focus --set` from a
    Bash call and the PostToolUse counter two seconds later address the same record -- without it
    the CLI would be writing to a session nobody reads. AKASHIC_SESSION_ID overrides for a harness
    that exports neither (a runner lane, a test).
    """
    return os.environ.get("AKASHIC_SESSION_ID") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""


def _client():
    """A PLAIN store client -- deliberately NOT get_bus().

    task_costs._client() goes through get_bus(), which is correct there: it runs inside a runner
    that already has a seat. This module runs inside a PreToolUse/PostToolUse hook, and
    tests/test_seat_heartbeat_wiring.py::test_w4 caught what that costs -- constructing a bus
    REGISTERS PRESENCE, so merely importing this module invented the seat ('claude', 'beef9999')
    in a process with no AKASHIC_AGENT_ID. A phantom seat is worse than a missing one, and
    bookkeeping must never mint an identity. The foundation connection has no such side effect.
    """
    try:
        from core.foundation.redis_connection import (
            DEFAULT_REDIS_HOST,
            DEFAULT_REDIS_PORT,
            connect_to_redis_with_fail_fast,
        )

        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=2, decode_responses=True
        )
    except Exception:
        return None


def _ledger():
    try:
        from core.coord.task_ledger import TaskLedger

        return TaskLedger()
    except Exception:
        return None


def _task(task_id: str) -> dict[str, Any] | None:
    led = _ledger()
    if led is None:
        return None
    try:
        return led.tasks.get(str(task_id))
    except Exception:
        return None


# --------------------------------------------------------------------------- the pointer ---


def set_focus(session_id: str, task_id: str, agent: str = "") -> dict[str, Any]:
    """Point this session at a task. Refuses an id the ledger does not know, because a focus on a
    typo would silently attribute a day's work to nothing."""
    tid = str(task_id).strip().upper()
    t = _task(tid)
    if t is None:
        return {"ok": False, "error": f"no task {tid} in the ledger"}
    c = _client()
    if c is None:
        return {"ok": False, "error": "no store; focus needs one to outlive a single hook process"}
    k = _key(session_id)
    try:
        c.delete(k)
        c.hset(
            k,
            mapping={
                "task": tid,
                "agent": str(agent or ""),
                "set_at": str(int(time.time())),
                "calls": "0",
                "hits": "0",
                "misses": "0",
                "streak": "0",
                "nudges": "0",
                "dismissed": "0",
                "quiet": "0",
            },
        )
        c.expire(k, FOCUS_TTL_S)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "task": tid,
        "title": t.get("title", ""),
        "status": t.get("status"),
        "files": list(t.get("files") or []),
        "note": ("this task declares no files, so drift cannot be detected -- attribution still works")
        if not (t.get("files") or [])
        else "",
    }


def clear_focus(session_id: str) -> dict[str, Any]:
    """Check out. Returns what the session accumulated, so the act of leaving reports something."""
    st = current(session_id) or {}
    c = _client()
    if c is not None:
        with contextlib.suppress(Exception):
            c.delete(_key(session_id))
    return {
        "ok": True,
        "was": st.get("task"),
        "calls": st.get("calls", 0),
        "hits": st.get("hits", 0),
        "misses": st.get("misses", 0),
    }


def current(session_id: str) -> dict[str, Any] | None:
    c = _client()
    if c is None:
        return None
    try:
        h = c.hgetall(_key(session_id))
    except Exception:
        return None
    if not h:
        return None

    def g(k, d=""):
        return h.get(k.encode()) or h.get(k) or d

    def dec(v):
        return v.decode() if isinstance(v, (bytes, bytearray)) else str(v)

    out = {"task": dec(g("task")), "agent": dec(g("agent")), "set_at": int(dec(g("set_at", "0")) or 0)}
    for f in ("calls", "hits", "misses", "streak", "nudges", "dismissed", "quiet"):
        try:
            out[f] = int(dec(g(f, "0")) or 0)
        except Exception:
            out[f] = 0
    return out


# ------------------------------------------------------------------------- attribution ---


def _declared(task_id: str) -> list[str]:
    t = _task(task_id) or {}
    out = []
    for f in t.get("files") or []:
        s = str(f).replace("\\", "/").strip().lstrip("./")
        if s:
            out.append(s.lower())
    return out


def touches(target: str, declared: list[str]) -> bool:
    """Does this tool call touch the task's declared ground?

    Deliberately GENEROUS: a declared directory counts for everything under it, a declared file
    counts when its name appears anywhere in a shell command, and an empty declaration matches
    nothing (so it cannot manufacture false hits). Being generous is the right error direction --
    a false miss nags the operator, a false hit only fails to nag.
    """
    if not target or not declared:
        return False
    t = str(target).replace("\\", "/").lower()
    for d in declared:
        if d in t:
            return True
        base = d.rsplit("/", 1)[-1]
        if base and len(base) > 3 and base in t:
            return True
    return False


def record_call(session_id: str, tool: str = "", target: str = "") -> str | None:
    """Count one SUCCESSFUL tool call against the focused task. Returns the tid, or None.

    Writes land on task_costs' own accumulator key, so task_ledger's DONE transition finalizes
    them through the existing cold path -- this module adds an input, not a second ledger.
    Never raises: it runs inside a hook, and a telemetry failure must never cost a tool call.
    """
    try:
        st = current(session_id)
        if not st or not st.get("task"):
            return None
        tid = st["task"]
        c = _client()
        if c is None:
            return None
        from core.coord.task_costs import _acc_key

        c.hincrby(_acc_key(tid), "tool_calls", 1)
        k = _key(session_id)
        c.hincrby(k, "calls", 1)
        if touches(target, _declared(tid)):
            c.hincrby(k, "hits", 1)
            c.hset(k, "streak", "0")
        else:
            c.hincrby(k, "misses", 1)
            c.hincrby(k, "streak", 1)
        c.expire(k, FOCUS_TTL_S)
        return tid
    except Exception:
        return None


# ------------------------------------------------------------------------------ the nudge ---


def drift_note(session_id: str) -> str | None:
    """One line when this session's calls have stopped touching the focused task, else None.

    Says what was observed and offers both exits, because the honest reading is often "the focus
    is stale", not "stop what you are doing".
    """
    try:
        st = current(session_id)
        if not st or not st.get("task"):
            return None
        if st.get("quiet") or st.get("dismissed", 0) >= DISMISS_QUIET:
            return None
        if st.get("streak", 0) < MISS_BEFORE_NUDGE:
            return None
        tid = st["task"]
        t = _task(tid) or {}
        declared = _declared(tid)
        if not declared:
            return None  # nothing to drift from; never nag on no evidence
        c = _client()
        if c is not None:
            c.hincrby(_key(session_id), "nudges", 1)
            c.hset(_key(session_id), "streak", "0")  # earn the next one
        age_d = max(0, int((time.time() - int(st.get("set_at") or 0)) / 86400))
        return (
            f"[focus] {st['streak']} calls in a row have not touched {tid}'s files "
            f"({', '.join(declared[:3])}{'...' if len(declared) > 3 else ''}). "
            f'{tid} "{str(t.get("title", ""))[:60]}" was focused {age_d}d ago. '
            f"If you have moved on: `{_cli()} focus --clear` (or --set T###). "
            f"If this is still the task: `{_cli()} focus --quiet`, "
            f"or `--dismiss` to wave this one off."
        )
    except Exception:
        return None


def dismiss(session_id: str) -> dict[str, Any]:
    """The operator said 'not now'. Counted, because the retirement rule is a measurement."""
    c = _client()
    if c is not None:
        try:
            c.hincrby(_key(session_id), "dismissed", 1)
            c.hset(_key(session_id), "streak", "0")
        except Exception:
            pass
    return current(session_id) or {"ok": True}


def quiet(session_id: str) -> dict[str, Any]:
    """Silence drift notes for this session, keeping attribution on. The common honest case:
    the focus IS right and the work legitimately ranges outside the declared files."""
    c = _client()
    if c is not None:
        with contextlib.suppress(Exception):
            c.hset(_key(session_id), "quiet", "1")
    return current(session_id) or {"ok": True}


def health() -> dict[str, Any]:
    """Is the detector earning its keep? The retirement rule, as a number anyone can read."""
    c = _client()
    if c is None:
        return {"sessions": 0, "nudges": 0, "dismissed": 0, "verdict": "no store"}
    n = d = s = 0
    try:
        for k in c.scan_iter(match=f"{_ns()}:focus:*", count=200):
            s += 1
            h = c.hgetall(k)

            def get(f, h=h):
                return int((h.get(f.encode()) or b"0").decode() or 0)

            n += get("nudges")
            d += get("dismissed")
    except Exception:
        pass
    rate = (d / n) if n else 0.0
    return {
        "sessions": s,
        "nudges": n,
        "dismissed": d,
        "dismiss_rate": round(rate, 3),
        "verdict": "retire the drift nudge"
        if n >= 10 and rate >= DISMISS_RETIRE
        else ("earning its keep" if n else "no data yet"),
    }
