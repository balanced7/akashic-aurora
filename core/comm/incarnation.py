"""incarnation -- who else is HERE right now, per agent id (T074 W3/R4).

One agent id can be N concurrent sessions ("incarnations": the twin-split receipts of
2026-07-15). The whisper's SIBLINGS line and any coordination decision need one cheap
question answered: which OTHER sessions of this agent are alive?

Phase 1 (this module, v1): derive liveness from the EXISTING signals only --
  * activity markers  bifrost_wake_<agent>_<sid>.alive   (touched at SessionStart and
    every stop-hook firing; wake_seat.touch_activity is the single writer)
  * seat files        bifrost_wake_<agent>_<sid>.pid     (an armed wake watcher)
A sibling is an incarnation whose marker is FRESHER than wake_seat.fresh_minutes()
(default 30m, same K7 threshold the janitor trusts). No WMI, no process walks: this
runs inside the SessionStart whisper and must cost one listdir, not a snapshot.

Phase 3 (T074 W11/W12) upgrades the same seam to published TTL cards
(bifrost:incarnation:<agent>:<sid> with claims + status); callers keep this signature.
Precedent: "for a runner, the runner lock IS the incarnation card" (deepseek T074 half,
sec. 4) -- v1 simply reads the session-side equivalents that already exist.
"""
from __future__ import annotations

import os
import tempfile
import time
from typing import Dict, List, Optional

from core.comm import wake_seat


def live_incarnations(agent: str, my_session: Optional[str] = None,
                      tmp: Optional[str] = None,
                      now: Optional[float] = None) -> List[Dict]:
    """All OTHER live sessions of `agent`, freshest first:
    [{session_id, age_min, has_seat}]. Prefix-exact on the agent id (the wake_seat
    convention: 'claude' never enumerates 'claude-2'). Never raises; a broken tempdir
    reads as solo -- the whisper must not fail because liveness was unreadable."""
    base = tmp or tempfile.gettempdir()
    fresh = wake_seat.fresh_minutes()
    t_now = now if now is not None else time.time()
    prefix = f"bifrost_wake_{agent}_"
    out: List[Dict] = []
    try:
        names = os.listdir(base)
    except Exception:
        return out
    for name in names:
        if not (name.startswith(prefix) and name.endswith(".alive")):
            continue
        sid = name[len(prefix):-len(".alive")]
        if not sid or (my_session and sid == my_session):
            continue
        try:
            ts = float(open(os.path.join(base, name)).read().strip())
        except Exception:
            continue                       # unreadable marker proves nothing -- skip
        age_min = max(0.0, (t_now - ts) / 60.0)
        if age_min >= fresh:
            continue                       # K7 threshold: staler than fresh_minutes() = not live
        out.append({
            "session_id": sid,
            "age_min": age_min,
            "has_seat": os.path.exists(wake_seat.seat_path(agent, sid, base)),
        })
    out.sort(key=lambda d: d["age_min"])
    return out


def _fmt_one(agent: str, s: Dict) -> str:
    sid8 = str(s.get("session_id", ""))[:8]
    age = s.get("age_min")
    idle = f"{age:.0f}m idle" if isinstance(age, (int, float)) else "age unknown"
    seat = "" if s.get("has_seat") else ", unseated"
    return f"{agent}#{sid8}, {idle}{seat}"


def siblings_line(agent: str, siblings: List[Dict]) -> str:
    """'solo' | '1 live sibling (claude#b0b7771d, 45m idle)' | 'N live siblings (...)'."""
    if not siblings:
        return "solo"
    n = len(siblings)
    noun = "live sibling" if n == 1 else "live siblings"
    return f"{n} {noun} (" + "; ".join(_fmt_one(agent, s) for s in siblings) + ")"
