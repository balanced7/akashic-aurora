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

Two independent staleness signals a reader can derive:
  * ``now - since_ts`` large while phase != idle  -> stuck IN a phase (a wedge L0 didn't catch)
  * ``now - beat_ts``  large                      -> the heartbeat thread itself stopped
"""
import json
import threading
import time

NS = "bifrost"
WORKLIVE_PREFIX = f"{NS}:worklive:"
WORKLIVE_TTL = 45          # > the ~5s heartbeat refresh, so a live record never flaps; a wedge keeps it alive


def _client():
    """Shared bus Redis client (same connector as control/bus). None when unreachable -> fail open."""
    try:
        from core.comm.bus import get_bus
        return get_bus("liveness")._client
    except Exception:
        return None


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
                }
            c.set(WORKLIVE_PREFIX + self.agent, json.dumps(rec), ex=WORKLIVE_TTL)
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
        raw = c.get(WORKLIVE_PREFIX + str(agent))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def stuck_seconds(agent: str):
    """Seconds the agent has been in its current phase (None if unknown). A reader's convenience."""
    rec = read(agent)
    if not rec:
        return None
    try:
        return max(0.0, time.time() - float(rec["since_ts"]))
    except Exception:
        return None
