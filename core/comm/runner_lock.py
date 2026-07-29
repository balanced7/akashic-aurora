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
from datetime import datetime
from typing import Any, Dict, Optional

from core.comm.timescale import scaled
from core.foundation.timeutil import now_iso

def _ns() -> str:
    # ns-isolation (2026-07-12): the consumer SEAT + fencing generation are per-namespace by design
    # (RB-21 single-consumer is WITHIN a namespace); a drill seat must never block the live seat.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _lock_prefix() -> str:
    return f"{_ns()}:runner:"


def _gen_prefix() -> str:                # L1b: monotone fencing-token source, INCR per acquisition
    return f"{_ns()}:generation:"
LOCK_TTL = scaled(20)    # seconds; the heartbeat must refresh well within this
                         # (drill-shrinkable via AKASHIC_TIMEOUT_MULTIPLIER)
# RB-21: a turn-based SESSION cannot heartbeat in runner seconds -- its claim on the very
# same lock carries this TTL instead, refreshed at every consume and every stop-hook
# firing. Future T034 dial. (docs/library/design/20260711_rb-21-session-cursor-discipline-build-sp_9fbdcd.md)
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
    return now_iso()   # T119: the one clock (aware UTC), not the machine's naive wall


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def _key(agent: str) -> str:
    return _lock_prefix() + str(agent)


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
        gen = int(c.incr(_gen_prefix() + str(agent)))
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
# claims -- one invariant, zero new primitives (docs/library/design/20260711_rb-21-session-cursor-discipline-build-sp_9fbdcd.md).
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
    # A TOMBSTONED SESSION MAY NOT CLAIM. Live incident 2026-07-28: a retiring seat kept
    # draining its successor's mail, because the seat serialises to whoever refreshed most
    # recently and the STOP HOOK refreshes on every turn end. A session being wound down still
    # takes turns -- re-arm demands, task notifications, one more operator question -- and each
    # one renewed the claim it was trying to give up. It never reached a clean SessionEnd, so
    # session_exit never released, and the successor was refused and silently degraded to peek.
    # A dying session out-competed its successor purely by still breathing.
    # The tombstone already recorded "done by RECORD, not by inference" and free_if_dead()
    # already honoured it; this end never did, so standing down was undone by the next consume.
    if str(holder_token or "").startswith("session:"):
        try:
            from core.comm import wake_seat
            if wake_seat.is_tombstoned(str(holder_token)[len("session:"):]):
                return False, 0, holder(agent) or {}
        except Exception:
            pass                      # tombstone unreadable -> fail toward the old behaviour
    if acquire(agent, holder_token, ttl=t):
        heartbeat(agent, holder_token, ttl=t)   # refresh on re-entrant claims; fresh = harmless
        return True, generation_of(holder_token), holder(agent) or {"token": holder_token}
    return False, 0, holder(agent) or {}


def stand_down(agent: str, holder_token: str) -> bool:
    """Yield the consumer seat PERMANENTLY for this session -- the voluntary hand-over.

    release_consumer() alone is not enough: the very next consume re-claims, because nothing
    remembers that the session was retiring. session_exit() does both but only fires on a clean
    SessionEnd, which a session that keeps being invoked never reaches -- which is exactly how a
    retiring seat spent an evening draining its successor's mail.

    So this writes the tombstone FIRST (the durable "I am done" record that claim_consumer now
    honours) and then releases. Order matters: tombstone-then-release means a crash between the
    two leaves the seat held by a session that can no longer re-claim -- it TTLs away and the
    successor gets it. Release-then-tombstone would leave a window where the retiree could take
    the seat straight back.

    Idempotent, and safe when we never held the seat. Never raises: a stand-down that can fail
    loudly is one an operator will skip.
    """
    ok = True
    try:
        from core.comm import wake_seat
        sid = str(holder_token or "")
        wake_seat.write_tombstone(sid[len("session:"):] if sid.startswith("session:") else sid)
    except Exception:
        ok = False
    try:
        held = holder(agent) or {}
        if held.get("token") == holder_token:
            release_consumer(agent, holder_token)
    except Exception:
        ok = False
    return ok


def refresh_consumer(agent: str, holder_token: str, ttl: Optional[int] = None) -> bool:
    """Best-effort seat refresh (stop-hook firing / any activity moment). No-ops safely
    when we do not hold the seat -- heartbeat() refuses a foreign token."""
    return heartbeat(agent, holder_token, ttl=int(ttl or SESSION_CONSUMER_TTL))


def release_consumer(agent: str, holder_token: str) -> bool:
    """Give the seat up early (clean session end). Only frees our own hold."""
    return release(agent, holder_token)


def free_if_dead(agent: str, *, grace_s: int = 300, stale_s: int = 900,
                 now: Optional[float] = None, tmp: Optional[str] = None,
                 pid_alive=None) -> Dict[str, Any]:
    """T083-C1-1: free a SESSION-held consumer seat whose holder is PROVABLY dead -- the crash
    net's slow leg made fast. clean_death (T075 M1-beta) already frees the seat on a GRACEFUL
    SessionEnd; a crash-killed session leaves its seat to TTL (up to 30 min of blocked consumes,
    live receipt 2026-07-15: seat 29f15d47, ~17 min). Prior art: k8s node leases -- liveness is
    RENEWAL, not lease existence; the controller frees a lease whose holder object is gone.

    Evidence ladder (probes injectable for pins; every ambiguity resolves toward ALIVE -- a
    false-free hands the seat over and the true owner's next consume degrades to a LOUD peek,
    non-corrupting via generation fencing, but we still never free on a guess):
      0. holder token must be 'session:'-prefixed (runners heartbeat properly; never touched)
         AND claim age > grace_s (a fresh claim is never probed).
      1. activity marker (touched at EVERY hook firing) fresh within grace_s  -> ALIVE.
      2. armed wake-listener pid file: pid DEAD -> DEAD (listener dies with its session);
         pid ALIVE -> ALIVE.
      3. no pid file: marker absent or older than stale_s -> DEAD-enough (no liveness evidence
         at all); otherwise indeterminate -> ALIVE (TTL rules).
      (incarnation card deliberately unused: CARD_TTL == seat TTL, so it discriminates nothing.)

    Returns {"freed": bool, "reason": str, "holder": token}. Frees via token-matched release
    (never evicts a successor) + a durable audit event. Fail-open: any probe error -> not freed."""
    verdict = {"freed": False, "reason": "no-holder", "holder": None}
    try:
        rec = holder(agent)
        if not rec:
            return verdict
        token = str(rec.get("token") or "")
        verdict["holder"] = token
        if not token.startswith("session:"):
            verdict["reason"] = "holder-is-runner"
            return verdict
        t_now = float(now if now is not None else time.time())
        age = t_now - _ts_epoch(rec.get("ts"), default=t_now)
        sid = token[len("session:"):]
        from core.comm import wake_seat
        # 0.5) T086 S1: a TOMBSTONED session is dead BY RECORD, not by inference -- no
        #      grace (its claim can never become live again; RB-21 fencing guards the
        #      rest). Probe errors read as not-tombstoned (fail toward alive, S1c).
        tombstoned = False
        try:
            tombstoned = wake_seat.is_tombstoned(sid, tmp)
        except Exception:
            tombstoned = False
        dead = "session-tombstoned (SessionEnd on record)" if tombstoned else None
        if dead is None and age <= grace_s:
            verdict["reason"] = f"grace ({int(age)}s <= {grace_s}s)"
            return verdict
        alive_probe = pid_alive if pid_alive is not None else _pid_alive_default
        marker = wake_seat.activity_marker_path(agent, sid, tmp)
        marker_age = None
        if dead is None:
            # 1) activity marker -- the every-hook-firing renewal channel
            try:
                if os.path.exists(marker):
                    marker_age = t_now - os.path.getmtime(marker)
                    if marker_age < grace_s:
                        verdict["reason"] = f"marker-fresh ({int(marker_age)}s)"
                        return verdict
            except Exception:
                verdict["reason"] = "marker-probe-error"
                return verdict
            # 2) T086 S2a: renewal staleness OUTRANKS a live listener pid. The listener is
            #    a PROCESS fact; the marker is the SESSION's renewal channel -- and C1-5's
            #    receipt (2026-07-16: listener alive, marker 192m stale, 30 min unwakeable)
            #    is exactly the conflation. A seat release is fenced + re-claimable: an
            #    idle-but-live session that wakes later simply re-claims (k8s lease
            #    eviction semantics). Destructive reaps keep K7/K8 conservatism; claim
            #    releases follow the lease.
            if marker_age is not None and marker_age >= stale_s:
                dead = f"renewal-stale ({int(marker_age)}s >= {stale_s}s; listener pid not consulted)"
        if dead is None:
            # 3) armed listener pid -- only consulted in the mid-band (grace < marker < stale)
            #    or when no marker exists (a session's first seconds; stay conservative)
            seat_file = wake_seat.seat_path(agent, sid, tmp)
            if os.path.exists(seat_file):
                pid = wake_seat.read_pid(seat_file)
                if pid is None:
                    verdict["reason"] = "seat-file-unreadable"
                    return verdict
                alive = alive_probe(pid)
                if alive:
                    verdict["reason"] = f"listener-alive (pid {pid})"
                    return verdict
                dead = f"listener-pid-dead ({pid})"
            # 4) no pid file -> no-evidence
            if dead is None:
                if marker_age is None:
                    dead = "no-liveness-evidence (no seat file, no marker)"
                else:
                    verdict["reason"] = f"indeterminate (marker {int(marker_age)}s; TTL rules)"
                    return verdict
        if release(agent, token):
            verdict.update({"freed": holder(agent) is None or holder(agent).get("token") != token,
                            "reason": dead})
            try:   # durable audit -- a freed seat must never look like a silent expiry
                from core.events.event_log import capture_event
                capture_event("seat_freed_dead_holder",
                              f"consumer seat for '{agent}' freed: holder {token} {dead} "
                              f"(claim age {int(age)}s)",
                              agent_id=agent,
                              detail={"holder": token, "evidence": dead, "claim_age_s": int(age)})
            except Exception:
                pass
        return verdict
    except Exception as e:
        verdict["reason"] = f"probe-error ({type(e).__name__})"
        return verdict


def _ts_epoch(ts, default: float = 0.0) -> float:
    """A holder record's ts -> epoch seconds. _now() stamps via the one clock (T119:
    timeutil.now_iso, aware UTC) whose own offset is its exact inverse; LEGACY naive rows
    were written as LOCAL wall-clock, so mktime(strptime) stays their inverse (one date
    source per era, the W1-flake lesson). Numeric strings pass through for forward-compat.
    Unparseable -> default (callers pass t_now => age 0 => grace protects; fail toward ALIVE)."""
    if ts is None:
        return default
    try:
        return float(ts)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(str(ts))
        if dt.tzinfo is not None:
            return dt.timestamp()
    except ValueError:
        pass
    try:
        return time.mktime(time.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return default


def _pid_alive_default(pid) -> bool:
    """Is this pid running? tasklist probe (the claude_stop.py pattern -- proven on this host).
    FAIL TOWARD ALIVE: a probe error must never justify freeing a seat."""
    try:
        import subprocess
        out = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"],
                             capture_output=True, text=True, timeout=5)
        return str(pid) in (out.stdout or "")
    except Exception:
        return True


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
