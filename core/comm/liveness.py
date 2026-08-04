"""Work-progress heartbeat (L1) -- pure observability for wedge detection.

A per-agent record on the bus answering "what phase is this agent in, and since when?".
A separate heartbeat thread REFRESHES the record without moving ``since_ts``, so an agent
wedged in a non-idle phase (e.g. a hung model call) stays VISIBLE with an ever-ageing
``since_ts`` -- exactly the signal a watchdog (L2) or supervisor/UI (L3) reads to decide
"stuck". This module only OBSERVES: it is fail-open like control.py and never raises into
the path it watches.

Record at ``bifrost:worklive:<agent>`` (JSON, TTL'd):
  phase     -- "online" | "idle" | "handling" | "thinking" | "reading" | "replied" | ...
  since_ts  -- epoch when the CURRENT phase began (moves only on a phase change)
  beat_ts   -- epoch of the last stamp (every set()/refresh(); its staleness = the beater died)
  turn      -- monotonic count of messages handled
  detail    -- short context (sender, tool name)
  seq       -- monotonic stamp counter
  code_sha  -- T114: the commit THIS PROCESS is executing. A long-lived worker
               keeps running the module it imported; without this the roster can
               say a seat is alive but never say alive ON WHAT, and a fix can be
               shipped, announced and believed while no process runs it.

Two independent staleness signals a reader can derive:
  * ``now - since_ts`` large while phase != idle  -> stuck IN a phase (a wedge L0 didn't catch)
  * ``now - beat_ts``  large                      -> the heartbeat thread itself stopped
"""
import json
import os
import re
import threading
import time
from typing import Optional

from core.comm.timescale import scaled as _scaled

def _ns() -> str:
    # ns-isolation (2026-07-12): per-agent liveness is per-namespace observability; a drill agent's
    # worklive/progress must not surface on the live doctor. Default "bifrost" preserved; per-call.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _worklive_prefix() -> str:
    return f"{_ns()}:worklive:"


_CODE_SHA: Optional[str] = None


def _safe_code_sha() -> str:
    """P7: liveness is load-bearing. A version probe that can break a heartbeat is
    worse than no version probe -- it turns an observability nicety into an outage."""
    try:
        return _running_code_sha()
    except Exception:
        return ""


def _running_code_sha() -> str:
    """T114: the commit this PROCESS is executing, resolved once and cached.

    Not a nicety. On 2026-07-28 a fix was committed, tested, pushed and announced to
    the fleet while every runner still ran the old module from memory -- the roster
    said LIVE, and nothing anywhere could say LIVE ON WHAT. The only way it surfaced
    was hashing raw stream envelopes after two peers tested the claim.

    Cached at first call because a process's code cannot change under it; re-reading
    per heartbeat would spend a subprocess every few seconds to learn a constant."""
    global _CODE_SHA
    if _CODE_SHA is None:
        _CODE_SHA = ""
        try:
            import subprocess
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            r = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=root,
                               capture_output=True, text=True, timeout=5,
                               stdin=subprocess.DEVNULL, close_fds=True)
            if r.returncode == 0:
                _CODE_SHA = (r.stdout or "").strip()
        except Exception:
            _CODE_SHA = ""
    return _CODE_SHA or ""
WORKLIVE_TTL = _scaled(45)  # > the ~5s heartbeat refresh, so a live record never flaps; a wedge
                            # keeps it alive (drill-shrinkable via AKASHIC_TIMEOUT_MULTIPLIER)

# Phases that mean "not doing work" -- never counted as a wedge no matter how long they last.
IDLE_PHASES = {"idle", "online", "replied"}
# Time in a NON-idle phase beyond which we FLAG (not kill) a suspected wedge. Deliberately past L0's
# worst-case self-heal (read-timeout x retries ~= a few minutes) so "wedged" means "L0 didn't fix it".
DEFAULT_WEDGE_S = _scaled(float(os.getenv("BIFROST_WEDGE_SECONDS", "300")), floor=1)
# Sub-threshold visibility floor (T097-S1 / P-S1-0): a non-idle phase with a DEAD pulse aged
# into [APPROACHING_WEDGE_S, DEFAULT_WEDGE_S) is surfaced by the doctor as a DASHBOARD
# "approaching wedge" -- the window where C1-8's stall lived invisibly (silent < 300s). Fixed,
# named (no auto-threshold magic); below the page threshold so it OBSERVES, never revives.
APPROACHING_WEDGE_S = _scaled(float(os.getenv("BIFROST_APPROACHING_WEDGE_SECONDS", "150")), floor=1)


def _client():
    """Shared bus Redis client (same connector as control/bus). None when unreachable -> fail open."""
    try:
        from core.comm.bus import get_bus
        return get_bus("liveness")._client
    except Exception:
        return None


class BusLossGuard:
    """RB-30 B2 (T030 L5): a runner that loses Redis must DEGRADE VISIBLY and stand down
    after `max_dead` consecutive dead beats -- never spin invisible (the heartbeat's
    fail-open made a bus-less runner look alive forever: presence expired, worklive
    expired, loop still burning CPU). Pure decision core: the caller sleeps `backoff_s`
    between dead beats and exits cleanly on 'stand_down'. One live beat resets fully."""

    def __init__(self, max_dead: int = 10):
        self.max_dead = int(max_dead)
        self.dead_beats = 0
        self.backoff_s = 0

    def beat(self, online: bool) -> str:
        if online:
            self.dead_beats = 0
            self.backoff_s = 0
            return "ok"
        self.dead_beats += 1
        if self.dead_beats >= self.max_dead:
            return "stand_down"
        self.backoff_s = min(30, 2 ** (self.dead_beats - 1))   # 1,2,4,8,16,30,30,... capped
        return "degraded"


class WorkLive:
    """Per-agent phase tracker. ``set()`` is called from the work path on a phase change;
    ``refresh()`` is called from the heartbeat thread to keep the record alive and ageing."""

    def __init__(self, agent: str):
        self.agent = str(agent)
        self._lock = threading.Lock()
        self._phase = "online"
        self._since = time.time()
        self._detail = ""
        self._turn = 0
        self._seq = 0

    def set(self, phase: str, detail: str = "", new_turn: bool = False) -> None:
        """Record a phase transition (or a same-phase detail update). ``since_ts`` moves only
        when the phase actually changes, so time-in-phase is measurable across many beats."""
        with self._lock:
            if phase != self._phase:
                self._phase = str(phase)
                self._since = time.time()
            self._detail = str(detail)[:120]
            if new_turn:
                self._turn += 1
        self._flush()

    def refresh(self) -> None:
        """Re-stamp the current phase (heartbeat thread). Keeps the key + TTL fresh; since_ts unchanged."""
        self._flush()

    def _flush(self) -> None:
        c = _client()
        if c is None:
            return
        try:
            with self._lock:
                self._seq += 1
                rec = {
                    "phase": self._phase,
                    "since_ts": round(self._since, 3),
                    "beat_ts": round(time.time(), 3),
                    "turn": self._turn,
                    "detail": self._detail,
                    "seq": self._seq,
                    # T114: WHAT is alive, not just that something is. Guarded so an
                    # observability field can never wedge the heartbeat it rides on.
                    "code_sha": _safe_code_sha(),
                }
            c.set(_worklive_prefix() + self.agent, json.dumps(rec), ex=WORKLIVE_TTL)
        except Exception:
            pass  # fail-open: observability must never wedge the path it observes


_registry = {}
_reg_lock = threading.Lock()


def worklive(agent: str) -> "WorkLive":
    """The shared WorkLive for ``agent`` (created on first use). Lets the runner loop and the
    Agent's on_activity callback stamp the SAME record without threading it through signatures."""
    key = str(agent)
    with _reg_lock:
        wl = _registry.get(key)
        if wl is None:
            wl = _registry[key] = WorkLive(key)
        return wl


def read(agent: str):
    """Read an agent's worklive record (UI / watchdog). None if absent or bus unreachable."""
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_worklive_prefix() + str(agent))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def worklive_beat_age(agent: str):
    """Seconds since this agent's worklive record was last stamped, or None if there is no record.

    The signal a roster heartbeat cannot give for a runner-backed seat. WORKLIVE_TTL is 45s and a
    heartbeat thread refreshes every ~5s, so an IDLE-but-alive runner keeps this fresh while it has
    no progress pulse at all (pulses mark work, and idle is not work). Measured 2026-08-03: kimi
    2.4s and deepseek 1.0s, both idle, both demonstrably answering, while the roster reported both
    as 29,611s stale.

    A record whose own beat has aged out is evidence the heartbeat THREAD stopped -- death, not
    life. Readers must check the age, never merely the record's existence.
    """
    rec = read(agent)
    if not rec:
        return None
    try:
        return max(0.0, time.time() - float(rec["beat_ts"]))
    except (KeyError, TypeError, ValueError):
        return None


# T155: the same threshold the send door uses (core/comm/bus.py UNATTENDED_S), read from the same
# env var so the two cannot drift apart -- a shared verdict with two thresholds is still two answers.
UNATTENDED_S = float(os.environ.get("AKASHIC_UNATTENDED_S", "300") or 300)

# T155: an id like `codex_root_019fab2d` is one INCARNATION of `codex_root`, but `codex_root`
# itself contains an underscore -- so "strip the last _segment" would resolve it to `codex`.
# Only a trailing session-shaped suffix (>=6 hex chars) is stripped, which `root` is not.
_INCARNATION_SUFFIX = re.compile(r"_([0-9a-f]{6,})$", re.I)


class Attendance(tuple):
    """A three-state verdict: ATTENDED | UNATTENDED | UNKNOWN.

    UNKNOWN is the load-bearing member. Every gauge before this one collapsed "I cannot tell"
    into "not here", which is how a beating-but-wedged seat read as running and a registration
    echo read as online. Absence of evidence is not evidence of absence -- and it is certainly
    not evidence of presence.
    """
    __slots__ = ()

    def __new__(cls, state, reason="", beat_age_s=None, agent=""):
        return tuple.__new__(cls, (state, reason, beat_age_s, agent))

    state = property(lambda s: s[0])
    reason = property(lambda s: s[1])
    beat_age_s = property(lambda s: s[2])
    agent = property(lambda s: s[3])

    def __repr__(self):
        return f"Attendance({self.state}, {self.reason!r}, beat_age_s={self.beat_age_s})"


def attendance(agent: str, *, namespace: str = None, client=None) -> "Attendance":
    """THE liveness verdict. One answer, so surfaces cannot contradict each other (T155).

    Measured 2026-08-03/04: four surfaces gave four answers about one seat, and a directed brief
    addressed exactly as that seat asked was queued where nothing would read it. The cause was two
    meanings of one word -- `Bus.presence()` answers "who REGISTERED recently" while the send path
    answers "who is ATTENDING now" -- and only the second is what a sender needs to know.

    Evidence is consulted in ONE direction: each probe can only ever turn UNATTENDED into
    ATTENDED, never invent a death. Each was bought by a real incident:

      1. roster beat      -- the ordinary signal, and the one that lies while a seat is mid-call
      2. progress pulse   -- stamped at real work (T133/M4: the beat alone lied twice on 08-02)
      3. worklive beat    -- the IDLE case a pulse cannot cover; a runner in its consume loop has
                             no pulse yet answers instantly (kimi 2.4s, deepseek 1.0s, both called
                             29,611s stale by the roster on 2026-08-03)

    NEVER RAISES. If no probe can be reached at all, the verdict is UNKNOWN -- a caller that
    cannot check liveness must not be handed a confident "dead".
    """
    name = str(agent or "")
    probed_anything = False
    youngest = None

    for candidate in _id_forms(name):
        try:
            from core.comm import roster as _roster
            rows = [r for r in _roster.roster(namespace or _ns(), client=client)
                    if str(r.get("agent") or "").split("#")[0] == candidate]
            ages = [r["beat_age_s"] for r in rows if r.get("beat_age_s") is not None]
            probed_anything = True
            if ages:
                fresh = min(ages)
                youngest = fresh if youngest is None else min(youngest, fresh)
                if fresh <= UNATTENDED_S:
                    return Attendance("ATTENDED", f"roster beat {fresh:.0f}s", fresh, candidate)
        except Exception:
            pass

        try:
            if progress_age(candidate) is not None:
                probed_anything = True
                return Attendance("ATTENDED", "progress pulse (working now)", youngest, candidate)
            probed_anything = True
        except Exception:
            pass

        try:
            wl = worklive_beat_age(candidate)
            probed_anything = True
            if wl is not None and wl <= UNATTENDED_S:
                return Attendance("ATTENDED", f"worklive beat {wl:.0f}s (idle, listening)",
                                  youngest, candidate)
        except Exception:
            pass

    if not probed_anything:
        return Attendance("UNKNOWN", "no probe could be read (bus unreachable?)", youngest, name)
    return Attendance("UNATTENDED", "no beat, pulse, or worklive", youngest, name)


def _id_forms(agent: str):
    """The id as given, plus its bare agent form if it carries a session-shaped suffix.

    T155: mail addressed to `codex_root_019fab2d` must not get a different answer than mail to
    `codex_root`, or a directed ask queues into a void under a near-identical name.
    """
    forms = [agent]
    bare = _INCARNATION_SUFFIX.sub("", agent)
    if bare and bare != agent:
        forms.append(bare)
    return forms


def stuck_seconds(agent: str):
    """Seconds the agent has been in its current phase (None if unknown). A reader's convenience."""
    rec = read(agent)
    if not rec:
        return None
    try:
        return max(0.0, time.time() - float(rec["since_ts"]))
    except Exception:
        return None


# ---------------------------------------------------------------- progress pulse (L2 / RB-27a)
# The signal wedge_view's caveat asked for: worklive says WHAT PHASE; the pulse says the
# worker is REACHING PROGRESS POINTS inside it (each tool call / thinking chunk / turn
# edge). Dead pulse + non-idle phase = the worker died inside a turn (HARD WEDGE, the
# doctor's page state); fresh pulse + aged phase = genuinely long work (F2, never paged).
# sd_notify heritage: keepalive at ~half the TTL; "trigger:<reason>" = WATCHDOG=trigger
# (self-confessed failure, rendered above inference). The value carries the tenure's
# LOCK GENERATION (deepseek: the L1b fence doubles as the writer gate -- a stale
# tenure's pulse is self-identifying).
def _progress_prefix() -> str:
    return f"{_ns()}:progress:"
PROGRESS_TTL = _scaled(5)


def pulse(agent: str, detail: str = "", *, generation: int = 0) -> bool:
    """Touch the progress key at a REAL progress point. Fail-open, never raises."""
    try:   # progress-bars data half: every pulse is a countable progress point
        from core.comm import turn_metrics
        turn_metrics.count_pulse(agent)
    except Exception:
        pass
    c = _client()
    if c is None:
        return False
    try:
        c.set(_progress_prefix() + str(agent),
              json.dumps({"ts": time.time(), "generation": int(generation),
                          "detail": str(detail)[:120]}),
              ex=PROGRESS_TTL)
        return True
    except Exception:
        return False


def progress_age(agent: str):
    """Seconds since this agent's last progress pulse, or None when there is no live pulse key.

    PRESENCE IS A POSITIVE SIGNAL ONLY. The key's TTL is deliberately short, so a missing pulse
    means "no progress point in the last few seconds" and never "this seat is dead" -- a seat
    between tool calls has no pulse and is perfectly alive. Readers must use this to CONFIRM
    liveness, never to conclude death. That asymmetry is the whole reason it is safe to consult
    from the send door, where a false negative costs a wrong warning and a false positive costs
    nothing at all.
    """
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_progress_prefix() + str(agent))
        if not raw:
            return None
        return max(0.0, time.time() - float(json.loads(raw)["ts"]))
    except Exception:
        return None


def pulse_error(agent: str, reason: str, *, generation: int = 0) -> bool:
    """Self-confessed failure (WATCHDOG=trigger equivalent): distinguishable from a
    silent hang, rendered with its reason by the doctor. Longer TTL so the confession
    outlives the crash that follows it."""
    c = _client()
    if c is None:
        return False
    try:
        c.set(_progress_prefix() + str(agent),
              json.dumps({"ts": time.time(), "generation": int(generation),
                          "detail": f"trigger:{str(reason)[:100]}"}),
              ex=PROGRESS_TTL * 12)
        return True
    except Exception:
        return False


def progress_read(agent: str):
    """{age_s, generation, detail} of the last pulse, or None (no pulse / bus down)."""
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_progress_prefix() + str(agent))
        if not raw:
            return None
        rec = json.loads(raw)
        return {"age_s": round(max(0.0, time.time() - float(rec.get("ts", 0))), 1),
                "generation": int(rec.get("generation", 0)),
                "detail": rec.get("detail", "")}
    except Exception:
        return None


def wedge_view(agent: str, wedge_s: float = None):
    """A reader's summary for the roster / watchdog (L3/L2): current phase, time-in-phase,
    beat age, and a heuristic ``wedged`` flag (in a non-idle phase past the threshold).
    Observe-only -- callers DISPLAY this; acting on it (kill/revive) is a later, gated layer.
    Returns None when there is no record (agent down / bus unreachable). Never raises.

    Caveat (honest): a genuinely long single phase (e.g. a 5-min generation or a long test run)
    also reads as high ``stuck_seconds``; distinguishing legit-long from truly-hung needs a
    per-token/per-tool progress signal (L2's job). Treat ``wedged`` as a hint, not proof."""
    rec = read(agent)
    if not rec:
        return None
    now = time.time()
    try:
        stuck = max(0.0, now - float(rec.get("since_ts", now)))
        beat_age = max(0.0, now - float(rec.get("beat_ts", now)))
    except Exception:
        stuck, beat_age = 0.0, 0.0
    phase = rec.get("phase", "?")
    thr = DEFAULT_WEDGE_S if wedge_s is None else float(wedge_s)
    return {
        "phase": phase,
        "detail": rec.get("detail", ""),
        "turn": rec.get("turn", 0),
        "stuck_seconds": round(stuck, 1),
        "beat_age": round(beat_age, 1),
        "wedged": (phase not in IDLE_PHASES) and stuck >= thr,
        "wedge_threshold": thr,
    }
