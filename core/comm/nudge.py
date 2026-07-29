"""
Bifrost nudge -- targeted, per-agent barge-in (companion to control.py's global PAUSE).

PAUSE (control.py) is GLOBAL: it freezes EVERY runner. A NUDGE is DIRECTED: one agent (or a human)
tells a SPECIFIC peer "stop what you're doing and look at this" without freezing the whole bus. It is
the fidelity DeepSeek asked for -- a nudge that actually interrupts work-in-progress, not just another
chat message that waits in line.

Mechanism (two parts, same trust model as PAUSE and the advisory path-locks):
  1. A small per-target flag in Redis (`bifrost:control:nudge:<agent>`), TTL-bounded so a missed
     pick-up never sticks.
  2. A `kind=nudge` message carrying the actual ask.
A cooperating runner checks is_nudged(<self>) between tool rounds -- the SAME seam the pause interrupt
uses -- so a nudge interrupts at the next round boundary, not just between messages. On pick-up the
runner clears the flag and acks, so the nudger knows it landed.

Fail-open on any Redis error (never wedge a runner) and ADVISORY (honored by cooperating runners).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from core.foundation.timeutil import now_iso


def _ns() -> str:
    # ns-isolation (2026-07-12): nudge/steer are directed control signals; a drill nudge to agent X
    # must not wake the LIVE X runner. Default "bifrost" preserved; per-call.
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _nudge_prefix() -> str:
    return f"{_ns()}:control:nudge:"


def _steer_prefix() -> str:               # per-agent queue of facts to FOLD INTO current work
    return f"{_ns()}:steer:"


NUDGE_TTL = 120          # a nudge auto-expires so a missed pick-up never sticks
STEER_TTL = 900          # a queued steer that's never picked up self-expires after 15 min


def _now() -> str:
    return now_iso()   # T119: the one clock (aware UTC), not the machine's naive wall


def _client():
    """The shared bus Redis client (via the sanctioned connector inside Bus). None when Redis is
    unreachable -- every function below then fails open, exactly like control.py."""
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def _key(agent: str) -> str:
    return _nudge_prefix() + str(agent)


def nudge(agent: str, by: str = "user", reason: str = "") -> bool:
    """Set the nudge flag for `agent` -- signals its runner to interrupt at the next round boundary.
    Idempotent; auto-expires after NUDGE_TTL. Returns False if the bus is offline."""
    c = _client()
    if c is None:
        return False
    try:
        c.set(_key(agent), json.dumps({"by": by, "reason": reason, "ts": _now()}), ex=NUDGE_TTL)
        return True
    except Exception:
        return False


def clear(agent: str) -> bool:
    """Acknowledge/consume the nudge (called by the target when it picks the nudge up). Idempotent."""
    c = _client()
    if c is None:
        return False
    try:
        c.delete(_key(agent))
        return True
    except Exception:
        return False


def is_nudged(agent: str) -> bool:
    """True iff a nudge is pending for `agent`. Fail-open: any error -> not nudged (never wedge work)."""
    c = _client()
    if c is None:
        return False
    try:
        return bool(c.exists(_key(agent)))
    except Exception:
        return False


def nudge_status(agent: str) -> Optional[Dict[str, Any]]:
    """{by, reason, ts} for a pending nudge, or None if there isn't one / bus offline."""
    c = _client()
    if c is None:
        return None
    try:
        raw = c.get(_key(agent))
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


# ------------------------------------------------------------------ STEER (soft: fold into current work)
# A nudge INTERRUPTS. A steer does NOT: it drops a fact onto a per-agent queue that the runner drains
# BETWEEN tool rounds and splices into the live conversation, so the agent adopts it without losing its
# place or its accumulated context. This is "be made aware of a new fact to adopt into your current task."
def _steer_key(agent: str) -> str:
    return _steer_prefix() + str(agent)


def steer_push(agent: str, frm: str, text: str) -> bool:
    """Queue a steering fact for `agent`, to be folded into its current work. Idempotency is not desired
    here (each steer is a distinct fact); the queue self-expires after STEER_TTL. Returns False if offline."""
    c = _client()
    if c is None:
        return False
    try:
        c.rpush(_steer_key(agent), json.dumps({"frm": str(frm), "text": str(text), "ts": _now()}))
        c.expire(_steer_key(agent), STEER_TTL)
        return True
    except Exception:
        return False


def steer_drain(agent: str) -> list:
    """Pop ALL queued steering facts for `agent` (oldest-first), as ['[from X] text', ...]. Called by the
    runner between tool rounds. Fail-open: any error -> [] (never wedge the loop)."""
    c = _client()
    if c is None:
        return []
    out = []
    try:
        while True:
            raw = c.lpop(_steer_key(agent))
            if raw is None:
                break
            try:
                d = json.loads(raw)
                out.append(f"[from {d.get('frm', '?')}] {d.get('text', '')}")
            except Exception:
                out.append(str(raw))
    except Exception:
        pass
    return out


def steer_pending(agent: str) -> int:
    """How many steering facts are queued for `agent` (peek, non-consuming). For the UI roster."""
    c = _client()
    if c is None:
        return 0
    try:
        return int(c.llen(_steer_key(agent)) or 0)
    except Exception:
        return 0
