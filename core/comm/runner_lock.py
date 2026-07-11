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

from core.comm.timescale import scaled

NS = "bifrost"
LOCK_PREFIX = f"{NS}:runner:"
GEN_PREFIX = f"{NS}:generation:"   # L1b: monotone fencing-token source, INCR per acquisition
LOCK_TTL = scaled(20)    # seconds; the heartbeat must refresh well within this
                         # (drill-shrinkable via AKASHIC_TIMEOUT_MULTIPLIER)
# RB-21: a turn-based SESSION cannot heartbeat in runner seconds -- its claim on the very
# same lock carries this TTL instead, refreshed at every consume and every stop-hook
# firing. Future T034 dial. (docs/rb21-build-spec-2026-07-11.md)
SESSION_CONSUMER_TTL = scaled(1800)

# L1b (T030, Kleppmann): each acquisition mints a GENERATION -- the fencing token the
# guarded cursor write validates AT THE RESOURCE. This process's tenure generations,
# keyed by instance token (one runner process holds at most one lock).
_TENURE_GEN: dict = {}


def generation_of(token: str) -> int:
    """The fencing generation minted when THIS process acquired with `token` (0 = none).
    Carried on every guarded cursor write; a successor's higher generation fences us out."""
    return int(_TENURE_GEN.get(token, 0))


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


def acquire(agent: str, token: str, ttl: Optional[int] = None) -> bool:
    """Try to become THE runner for `agent`. Returns True if we now hold the lock (either it was free,
    or a prior holder's key had expired). False means another live runner holds it -- do not start.
    Fail-open: if the bus is offline we return True (nothing to race with).
    `ttl` overrides LOCK_TTL in raw seconds (RB-21: session claims pass SESSION_CONSUMER_TTL).

    L1b: a successful acquisition MINTS a fencing generation (atomic INCR) recorded in the
    lock value and in this process's tenure map -- the guarded cursor write refuses any
    lower generation, so an expired-but-still-running predecessor cannot corrupt the
    cursor (Kleppmann: the token is validated at the RESOURCE, not at the lock)."""
    c = _client()
    if c is None:
        return True
    try:
        # Minted per ATTEMPT (the value must exist before the nx SET stores it); a losing
        # contender leaves a gap in the sequence, which is harmless -- monotonicity is the
        # only property the fence needs, and nobody ever WRITES with an unwon generation.
        gen = int(c.incr(GEN_PREFIX + str(agent)))
        if c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now(),
                                          "gen": gen}),
                 nx=True, ex=int(ttl or LOCK_TTL)):
            _TENURE_GEN[token] = gen
            return True
        # Held. Re-entrant only for our OWN token (e.g. a heartbeat gap that let it expire+repopulate).
        raw = c.get(_key(agent))
        if raw:
            try:
                rec = json.loads(raw)
                if rec.get("token") == token:
                    _TENURE_GEN.setdefault(token, int(rec.get("gen", 0)))
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return True


def heartbeat(agent: str, token: str, ttl: Optional[int] = None) -> bool:
    """Refresh our hold (extend the TTL) -- call once per loop iteration. Only refreshes if WE still hold
    it (guards against clobbering a successor that took over after a stall). Returns True if refreshed.
    `ttl` overrides LOCK_TTL in raw seconds (RB-21: session refreshes pass SESSION_CONSUMER_TTL)."""
    c = _client()
    if c is None:
        return True
    try:
        gen = generation_of(token)   # L1b: the tenure's generation rides every refresh
        raw = c.get(_key(agent))
        if not raw:
            # lock vanished (expired) -- reclaim ATOMICALLY (nx) so we never clobber a racing successor that
            # acquired between our GET and this SET. If nx fails, someone else owns it now -> we stand down.
            # The tenure KEEPS its original generation: nx proves the slot was empty, so no successor
            # observed the gap; if one acquired-and-died inside it (minting a higher gen), the guarded
            # cursor write is the arbiter -- our next advance gets STALE_GENERATION and we stand down.
            if not gen:
                # RB-21 P12: a refresher that does not KNOW its tenure generation (a fresh
                # process, e.g. the stop hook) must never reclaim with 0 -- the poisoned
                # value would fence the session against its own cursor. Stand down; the
                # next claim_consumer() acquires fresh with a properly minted generation.
                return False
            return bool(c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now(),
                                                       "gen": gen}),
                              nx=True, ex=int(ttl or LOCK_TTL)))
        try:
            rec = json.loads(raw)
            if rec.get("token") != token:
                return False        # someone else owns it now; we should stand down
        except Exception:
            return False
        if not gen:
            # RB-21 P12 (live incident 2026-07-11): a cross-process refresher inherits the
            # tenure generation from the LOCK VALUE instead of clobbering it with 0 --
            # gen recovery on the next re-entrant claim depends on this field.
            gen = int(rec.get("gen", 0))
        c.set(_key(agent), json.dumps({"token": token, "pid": os.getpid(), "ts": _now(), "gen": gen}),
              ex=int(ttl or LOCK_TTL))
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


# ---------------------------------------------------------------- RB-21: session consumers
# A session consuming mail IS a cursor-advancer, so it claims THE SAME lock a runner
# claims -- one invariant, zero new primitives (docs/rb21-build-spec-2026-07-11.md).
# Holder tokens are "session:<id>"-prefixed so refusal messages can teach legibly.

def session_holder_token() -> Optional[str]:
    """The stable session identity for consumer claims: the harness exports its session
    id to every subprocess, so one session's claims cohere across CLI invocations.
    None when no session env exists -- each door chooses its own fallback bucket
    (single definition per deepseek verify observation; doors delegate here)."""
    sid = os.getenv("CLAUDE_CODE_SESSION_ID") or os.getenv("CLAUDE_SESSION_ID") or ""
    return f"session:{sid}" if sid else None


def claim_consumer(agent: str, holder_token: str, ttl: Optional[int] = None):
    """Claim (or refresh) the single-consumer seat for `agent` as a SESSION.
    Returns (ok, generation, holder_info): ok=True with OUR tenure generation, or
    ok=False with the live holder's record for the teaching error.
    Re-entrant for the own token -- a re-claim refreshes the TTL and KEEPS the tenure
    generation (the acquire() own-token precedent; pinned as RB-21 P10). `ttl` in raw
    seconds; None -> SESSION_CONSUMER_TTL."""
    t = int(ttl or SESSION_CONSUMER_TTL)
    if acquire(agent, holder_token, ttl=t):
        heartbeat(agent, holder_token, ttl=t)   # refresh on re-entrant claims; fresh = harmless
        return True, generation_of(holder_token), holder(agent) or {"token": holder_token}
    return False, 0, holder(agent) or {}


def refresh_consumer(agent: str, holder_token: str, ttl: Optional[int] = None) -> bool:
    """Best-effort seat refresh (stop-hook firing / any activity moment). No-ops safely
    when we do not hold the seat -- heartbeat() refuses a foreign token."""
    return heartbeat(agent, holder_token, ttl=int(ttl or SESSION_CONSUMER_TTL))


def release_consumer(agent: str, holder_token: str) -> bool:
    """Give the seat up early (clean session end). Only frees our own hold."""
    return release(agent, holder_token)


def clear_if_pid(agent: str, pid) -> bool:
    """Force-free the lock ONLY if its current holder is `pid` -- e.g. a runner we just hard-killed
    whose `finally` release never ran. Safe: never evicts a DIFFERENT live holder (a successor that
    already took over). Returns True if the lock is now free (cleared, or already gone). Used by the
    launcher's revive/restart so a relaunch isn't blocked by its own dead predecessor's lingering key."""
    c = _client()
    if c is None:
        return True
    try:
        raw = c.get(_key(agent))
        if not raw:
            return True  # already free
        try:
            if json.loads(raw).get("pid") == pid:
                c.delete(_key(agent))
                return True
        except Exception:
            return False
        return False  # a different holder now -> leave it be
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
