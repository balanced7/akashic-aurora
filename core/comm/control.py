"""
Bifrost control plane -- human-in-the-loop PAUSE + runaway-loop guard for live agent collaboration.

Two safety mechanisms for a shared bus where agents wake each other (co-designed with DeepSeek, which
flagged the echo-loop risk unprompted -- two auto-answering runners can ping-pong forever, burning
tokens):

1. PAUSE (barge-in). One shared Redis flag the human can set to freeze the auto-responders. A runner
   checks is_paused() at the top of its loop; while paused it does NOT consume/answer, so incoming
   mail simply queues on the Streams until resume(). Lets a human interject mid-exchange with nothing
   lost. Shared (Redis) so the UI, the CLI, or an agent can all set it.

2. LOOP-GUARD (runaway prevention), two layers:
   - HOP COUNT (primary). Every auto-reply carries meta['hops']; a runner refuses to answer once the
     incoming hops >= MAX_HOPS, bouncing the thread back to a human. Bounds any A<->B ping-pong to
     MAX_HOPS turns no matter what.
   - RATE LIMIT (backstop). A runner may auto-reply at most MAX_REPLIES_PER_MIN (sliding 60s window);
     beyond that it auto-pauses the whole bus and says so. Catches runaway even if hop-count is bypassed
     (e.g. a third agent, or a bug that resets hops).

Both fail-open on any Redis error (never wedge the bus) and are ADVISORY -- honored by cooperating
runners, same trust model as the advisory path-locks. Tunable via env: BIFROST_MAX_HOPS,
BIFROST_MAX_REPLIES_PER_MIN.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from typing import Any, Dict, Optional

# --- namespace-scoped control plane (2026-07-12 isolation fix; claude fenced half, deepseek review
# pending) -----------------------------------------------------------------------------------------
# The pause/halt/narration/activity keys FOLLOW BIFROST_NAMESPACE (exactly like Bus.ns) instead of
# being hardcoded to 'bifrost'. Before this, a runner in an isolated STREAM namespace still shared the
# ONE 'bifrost:control:paused' key -- so a drill that tripped the rate-limit guard PAUSED THE LIVE
# FLEET (found in RB-25 drill 3). Read PER-CALL (not an import-time constant) so a process that sets
# BIFROST_NAMESPACE at runtime, or after importing this module, is still routed to the right keys.
DEFAULT_NS = "bifrost"


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", DEFAULT_NS)


def _pause_key() -> str:
    return f"{_ns()}:control:paused"


def _halt_prefix() -> str:                 # per-agent targeted halt (A1); union'd with the pause by is_halted
    return f"{_ns()}:control:halt:"


def _narration_key() -> str:               # off|key|full -- how much of claude's reasoning streams to the bus
    return f"{_ns()}:control:narration"


def _activity_prefix() -> str:             # rich-presence activity keys (same class, also ns-scoped)
    return f"{_ns()}:activity:"


_NARRATION_LEVELS = ("off", "key", "full")
MAX_HOPS = int(os.getenv("BIFROST_MAX_HOPS", "6"))
MAX_REPLIES_PER_MIN = int(os.getenv("BIFROST_MAX_REPLIES_PER_MIN", "12"))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _client():
    """The shared bus Redis client (built via the sanctioned fail-fast connector inside Bus). None when
    Redis is unreachable -- every function below then fails open."""
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


# ------------------------------------------------------------------ drain
DRAIN_TTL_S = 300


def _drain_key(agent: str) -> str:
    return f"{_ns()}:control:drain:{agent}"


def drain(agent: str, by: str = "user", reason: str = "") -> bool:
    """Request a RUNNER's graceful exit: finish the current message, release the
    singleton lock, exit 0 at the next loop top. TTL'd (DRAIN_TTL_S) so an unhonored
    request self-clears -- the C1-9 law applied at birth. Kills the restart tax
    (2026-07-21: TaskStop tree-kill ghosts + thrown-away in-flight context +
    sleep-retry lock dances, three times in one night)."""
    c = _client()
    if c is None:
        return False
    try:
        c.set(_drain_key(agent), json.dumps({"by": by, "reason": reason, "ts": _now()}),
              ex=DRAIN_TTL_S)
        return True
    except Exception:
        return False


def drain_requested(agent: str) -> Optional[Dict[str, Any]]:
    """The runner's loop-top probe. None when no live request (or bus offline)."""
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_drain_key(agent))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def clear_drain(agent: str) -> None:
    c = _client()
    if c is None:
        return
    try:
        c.delete(_drain_key(agent))
    except Exception:
        pass


# ------------------------------------------------------------------ pause
def pause(reason: str = "", by: str = "user", ttl: Optional[int] = None) -> bool:
    """Freeze the auto-responders. Idempotent. Returns False if the bus is offline.
    RB-30 (T030 L5): `ttl` seconds makes the pause SELF-HEAL -- automated backstops
    (rate-limit guards) must never freeze the fleet forever if everyone forgets them.
    None = persistent until an explicit resume (human intent stays human)."""
    c = _client()
    if c is None:
        return False
    try:
        c.set(_pause_key(), json.dumps({"reason": reason, "by": by, "ts": _now()}),
              ex=int(ttl) if ttl else None)
        return True
    except Exception:
        return False


def format_pause_line(status: Dict[str, Any], now: Optional[float] = None) -> str:
    """PURE render of pause_status() (RB-30 H5): a leftover freeze must be LOUD at every
    surface that renders fleet state (boot, bifrost-sync, fleet doctor). Age is computed
    AT RENDER from the stored ts -- the store stays clock-free (T025 doctrine). Returns
    "" when not paused so callers can `if line: print(line)`."""
    if not status.get("paused"):
        return ""
    age = "?"
    try:
        then = time.mktime(time.strptime(str(status.get("ts", "")), "%Y-%m-%dT%H:%M:%S"))
        mins = max(0, int(((now if now is not None else time.time()) - then) / 60))
        age = f"{mins // 60}h{mins % 60:02d}m" if mins >= 60 else f"{mins}m"
    except Exception:
        pass
    return (f"!! PAUSED (by {status.get('by', '?')}: {status.get('reason') or 'no reason given'}, "
            f"{age} old) -- auto-responders frozen; resume: py agent_cli.py bifrost-resume")


def resume(targets=None) -> bool:
    """Un-freeze. targets=None/[] -> resume ALL: clear the global pause AND every per-agent halt.
    targets=[ids] -> clear only those per-agent halts (leaves a global pause, if any, in place).
    Idempotent. Backward-compatible: existing no-arg resume() callers still clear the global pause."""
    c = _client()
    if c is None:
        return False
    ts = _norm_targets(targets)
    try:
        if not ts:
            c.delete(_pause_key())
            keys = c.keys(_halt_prefix() + "*") or []
            if keys:
                c.delete(*keys)
            return True
        c.delete(*[_halt_prefix() + a for a in ts])
        return True
    except Exception:
        return False


def is_paused() -> bool:
    """True iff a pause flag is set. Fail-open: any error -> not paused (never wedge the bus)."""
    c = _client()
    if c is None:
        return False
    try:
        return bool(c.exists(_pause_key()))
    except Exception:
        return False


def pause_status() -> Dict[str, Any]:
    """{paused, online, reason?, by?, ts?} -- for the UI/CLI status line."""
    c = _client()
    if c is None:
        return {"paused": False, "online": False}
    try:
        raw = c.get(_pause_key())
        if not raw:
            return {"paused": False, "online": True}
        d = json.loads(raw)
        d.update({"paused": True, "online": True})
        return d
    except Exception:
        return {"paused": False, "online": True}


# ------------------------------------------------------------------ narration (claude reasoning visibility)
# Claude Code redacts extended-thinking at rest, so claude can't auto-stream raw reasoning the way a
# runner does. Instead it DELIBERATELY narrates key reasoning to the bus via agent.harness.trace.narrate,
# which gates on this shared level -- so the human can dial claude's reasoning-visibility from the UI
# (a toggle) without touching claude's config. off=silent, key=narrate at decision points (default),
# full=narrate freely. Shared (Redis) like pause; fail-open to "key".
def get_narration_level() -> str:
    """Current narration verbosity: off|key|full. Fail-open to 'key' (the agreed default)."""
    c = _client()
    if c is None:
        return "key"
    try:
        v = c.get(_narration_key())
        v = v.decode() if isinstance(v, (bytes, bytearray)) else v
        return v if v in _NARRATION_LEVELS else "key"
    except Exception:
        return "key"


def set_narration_level(level: str, by: str = "user") -> bool:
    """Set narration verbosity (off|key|full). Idempotent. False if bad level or bus offline."""
    if level not in _NARRATION_LEVELS:
        return False
    c = _client()
    if c is None:
        return False
    try:
        c.set(_narration_key(), level)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ targeted halt (A1)
# Per-agent halt EXTENDS the global pause. halt(targets=None) reuses the global PAUSE flag (halt-all,
# backward-compatible -- a runner that only checks is_paused() still freezes), while halt(targets=[ids])
# sets a per-agent flag so ONE agent can be frozen while the others keep working. is_halted(agent) is
# the union of the two. (Refinement from DeepSeek: reuse the global flag for the all-agents case -- one
# fewer key write, and any legacy is_paused()-only runner stays correct.)
def _norm_targets(targets) -> list:
    """None/'' -> [] (means 'all'); a bare str -> [str]; else the non-empty string ids of an iterable."""
    if targets is None:
        return []
    if isinstance(targets, str):
        targets = [targets]
    return [str(t) for t in targets if str(t).strip()]


def halt(targets=None, reason: str = "", by: str = "user") -> bool:
    """Freeze agents. targets=None/[] -> halt ALL (reuses the global pause flag). targets=[ids] ->
    freeze only those agents via per-agent flags; the rest keep running. Idempotent. False if offline."""
    ts = _norm_targets(targets)
    if not ts:
        return pause(reason=reason, by=by)          # halt-all == the global pause (backward compat)
    c = _client()
    if c is None:
        return False
    try:
        payload = json.dumps({"reason": reason, "by": by, "ts": _now()})
        for a in ts:
            c.set(_halt_prefix() + a, payload)
        return True
    except Exception:
        return False


def is_halted(agent: str) -> bool:
    """True iff `agent` is frozen -- by the global pause (halt-all) OR its own per-agent halt flag. This
    is the check a runner uses in place of is_paused(). Fail-open: any error -> not halted."""
    c = _client()
    if c is None:
        return False
    try:
        if c.exists(_pause_key()):
            return True
        return bool(c.exists(_halt_prefix() + str(agent)))
    except Exception:
        return False


def halted_agents() -> Dict[str, Any]:
    """{agent: {reason, by, ts}} for each agent under a TARGETED halt (a global pause is separate, via
    pause_status()). The UI unions the two to show who is frozen and why."""
    c = _client()
    if c is None:
        return {}
    out: Dict[str, Any] = {}
    try:
        for k in (c.keys(_halt_prefix() + "*") or []):
            agent = str(k).rsplit(":", 1)[-1]
            raw = c.get(k)
            if raw:
                try:
                    out[agent] = json.loads(raw)
                except Exception:
                    out[agent] = {}
    except Exception:
        pass
    return out


# ------------------------------------------------------------------ loop guard
def next_hops(incoming_meta: Optional[dict]) -> int:
    """The hop count to stamp on the reply to a message: incoming hops + 1 (0 if unset)."""
    try:
        return int((incoming_meta or {}).get("hops", 0)) + 1
    except Exception:
        return 1


def hops_exceeded(incoming_meta: Optional[dict], max_hops: int = MAX_HOPS) -> bool:
    """True iff this message is already too deep in an auto-reply chain to answer (return to a human)."""
    try:
        return int((incoming_meta or {}).get("hops", 0)) >= max_hops
    except Exception:
        return False


class RateLimiter:
    """In-process sliding-window limiter: at most `max_per_min` events per rolling 60 seconds.
    In-process is right here -- each runner is one process and limits ITS OWN reply rate."""

    def __init__(self, max_per_min: int = MAX_REPLIES_PER_MIN):
        self.max = max(1, int(max_per_min))
        self.events: deque = deque()

    def allow(self, now: Optional[float] = None) -> bool:
        """Record an event and return True if under the limit; False if the window is full."""
        now = time.time() if now is None else now
        while self.events and now - self.events[0] > 60:
            self.events.popleft()
        if len(self.events) >= self.max:
            return False
        self.events.append(now)
        return True


# ------------------------------------------------------------------ rich presence (real activity)
# What an agent is ACTUALLY doing right now -- driven by the runner, not guessed by the UI. Stored per
# agent with a short TTL so a crashed runner's activity auto-clears (no stuck "typing"). The UI reads
# get_activities() and maps state -> an icon. States: thinking | reading | searching | inspecting |
# recalling | running | writing | working (idle = no key).
ACTIVITY_TTL = 25


def set_activity(agent: str, state: str, detail: str = "") -> bool:
    """Mark what `agent` is doing now (auto-expires after ACTIVITY_TTL). Fail-open."""
    c = _client()
    if c is None:
        return False
    try:
        c.set(_activity_prefix() + str(agent),
              json.dumps({"state": str(state), "detail": str(detail)[:120], "ts": _now()}),
              ex=ACTIVITY_TTL)
        return True
    except Exception:
        return False


def clear_activity(agent: str) -> bool:
    """The agent went idle -- drop its activity so the UI stops showing it working."""
    c = _client()
    if c is None:
        return False
    try:
        c.delete(_activity_prefix() + str(agent))
        return True
    except Exception:
        return False


def get_activities() -> Dict[str, Any]:
    """{agent: {state, detail, ts}} for every agent currently doing something (non-expired)."""
    c = _client()
    if c is None:
        return {}
    out: Dict[str, Any] = {}
    try:
        for k in (c.keys(_activity_prefix() + "*") or []):
            agent = str(k).rsplit(":", 1)[-1]
            raw = c.get(k)
            if raw:
                try:
                    out[agent] = json.loads(raw)
                except Exception:
                    pass
    except Exception:
        pass
    return out
