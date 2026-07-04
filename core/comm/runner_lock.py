"""
Bifrost runner singleton-lock -- at most ONE live runner per agent id.

The bug this fixes (observed live): two runners for the SAME agent share one Redis read-cursor, so one
advances the cursor past a message the other should have answered -- messages get silently consumed with
no reply. A runner is a process; the bus gives each AGENT one inbox + one cursor. Two processes on one
cursor is a race. This is a single-holder lock keyed by agent (not by holder), with a unique per-process
instance token, so a second runner for the same id refuses to start.

Crash-safe: the lock is a TTL key refreshed by a heartbeat while the runner lives. If a runner crashes,
its key expires after LOCK_TTL and the next start (or a supervisor's respawn) takes over cleanly. Steal
semantics are TTL-only -- we never forcibly evict a live holder.

Fail-open on Redis errors (a down bus means no runner anyway); ADVISORY, same trust model as the rest of
core/comm. Instance token varies by pid so a respawn never collides with its own stale key value.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Optional

NS = "bifrost"
LOCK_PREFIX = f"{NS}:runner:"
LOCK_TTL = 20            # seconds; the heartbeat must refresh well within this


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def _key(agent: str) -> str:
    return LOCK_PREFIX + str(agent)


def instance_token(agent: str) -> str:
    """A token unique to THIS runner instance: pid + a random suffix so it is unique even if two tokens
    are minted in the same millisecond (and so a respawn never reuses a predecessor's value). Passed to
    heartbeat/release so only the holder can refresh or free the lock."""
    return f"{agent}:{os.getpid()}:{uuid.uuid4().hex[:12]}"


def acquire(agent: str, token: str) -> bool:
    """Try to become THE runner for `agent`. Returns True if we now hold the lock (either it was free,
    or a prior holder's key had expired). False means another live runner holds it -- do not start.
    Fail-open: if the bus is offline we return True (nothing to race with)."""
    c = _client()
    if c is None:
        return True
    try:
        if c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now()}),
                 nx=True, ex=LOCK_TTL):
            return True
        # Held. Re-entrant only for our OWN token (e.g. a heartbeat gap that let it expire+repopulate).
        raw = c.get(_key(agent))
        if raw:
            try:
                if json.loads(raw).get("token") == token:
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return True


def heartbeat(agent: str, token: str) -> bool:
    """Refresh our hold (extend the TTL) -- call once per loop iteration. Only refreshes if WE still hold
    it (guards against clobbering a successor that took over after a stall). Returns True if refreshed."""
    c = _client()
    if c is None:
        return True
    try:
        raw = c.get(_key(agent))
        if not raw:
            # lock vanished (expired) -- reclaim ATOMICALLY (nx) so we never clobber a racing successor that
            # acquired between our GET and this SET. If nx fails, someone else owns it now -> we stand down.
            return bool(c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now()}),
                              nx=True, ex=LOCK_TTL))
        try:
            if json.loads(raw).get("token") != token:
                return False        # someone else owns it now; we should stand down
        except Exception:
            return False
        c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now()}), ex=LOCK_TTL)
        return True
    except Exception:
        return True


def release(agent: str, token: str) -> bool:
    """Give up the lock on clean shutdown, but only if we hold it (never free a successor's lock)."""
    c = _client()
    if c is None:
        return True
    try:
        raw = c.get(_key(agent))
        if raw and json.loads(raw).get("token") == token:
            c.delete(_key(agent))
        return True
    except Exception:
        return True


def holder(agent: str) -> Optional[dict]:
    """{token, pid, ts} of the current runner for `agent`, or None. For diagnostics / the UI roster."""
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_key(agent))
        return json.loads(raw) if raw else None
    except Exception:
        return None
