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

import json
import os
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional

from core.comm import wake_seat

# ---------------------------------------------------------------- Phase 3: TTL cards
# (T074 W11/W12, deepseek sec. 4.) A card is the session's self-published presence:
# born at SessionStart, re-armed at every stop-hook firing, gone 30 minutes after the
# last sign of life. Namespaced like every comm key (R9) so drills never leak.
CARD_TTL_SEC = int(os.getenv("AKASHIC_INCARNATION_TTL_MIN", "30")) * 60
IDLE_AFTER_MIN = 5.0                     # R11: derived at READ time, never written
_TS_FMT = "%Y-%m-%dT%H:%M:%S"


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _card_key(agent: str, session_id: str) -> str:
    return f"{_ns()}:incarnation:{agent}:{session_id}"


def _redis():
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def _now_ts() -> str:
    return time.strftime(_TS_FMT)


def _age_min(ts: str, now: Optional[float] = None) -> Optional[float]:
    try:
        then = datetime.strptime(str(ts), _TS_FMT).timestamp()
    except Exception:
        return None
    return max(0.0, ((now if now is not None else time.time()) - then) / 60.0)


def _ledger_claims(agent: str, limit: int = 4) -> List[str]:
    """Task ids this AGENT holds open (claimed/in_progress/verifying). Agent-level on
    purpose: per-SESSION claim attribution is T072's plumbing, and a card must not
    pretend to a precision the ledger cannot give."""
    try:
        from core.coord.task_ledger import read_ledger
        tasks = (read_ledger() or {}).get("tasks", [])
        return [t["id"] for t in tasks
                if t.get("owner") == agent
                and t.get("status") in ("claimed", "in_progress", "verifying")][:limit]
    except Exception:
        return []


def _resolve_client(c, allow_fallback: bool):
    if c is not None:
        return c
    return _redis() if allow_fallback else None


def publish_card(agent: str, session_id: str, pid: Optional[int] = None,
                 claims: Optional[List[str]] = None, c=None,
                 allow_fallback: bool = True) -> bool:
    """Birth (or rebirth) of a session's card. False when no client -- callers are
    hooks and MUST stay fail-open; the marker path still proves life without Redis."""
    cli = _resolve_client(c, allow_fallback)
    if cli is None or not session_id:
        return False
    now = _now_ts()
    card = {"session_id": session_id, "pid": int(pid if pid is not None else os.getpid()),
            "started": now, "refreshed": now,
            "claims": list(claims) if claims is not None else _ledger_claims(agent),
            "status": "active"}
    try:
        cli.set(_card_key(agent, session_id), json.dumps(card), ex=CARD_TTL_SEC)
        return True
    except Exception:
        return False


def refresh_card(agent: str, session_id: str, claims: Optional[List[str]] = None,
                 c=None, allow_fallback: bool = True) -> bool:
    """Every stop-hook firing re-arms the TTL. Keeps the birth stamp and claims (unless
    new ones are given); a MISSING card self-heals by republishing (R12: a Redis outage
    window must not leave a live session cardless until restart)."""
    cli = _resolve_client(c, allow_fallback)
    if cli is None or not session_id:
        return False
    key = _card_key(agent, session_id)
    try:
        raw = cli.get(key)
        if raw:
            card = json.loads(raw)
            if claims is not None:
                card["claims"] = list(claims)
        else:
            card = {"session_id": session_id, "pid": os.getpid(), "started": _now_ts(),
                    "claims": list(claims) if claims is not None else _ledger_claims(agent),
                    "status": "active"}
        card["refreshed"] = _now_ts()
        cli.set(key, json.dumps(card), ex=CARD_TTL_SEC)
        return True
    except Exception:
        return False


def read_cards(agent: str, c=None, allow_fallback: bool = True,
               now: Optional[float] = None) -> List[Dict]:
    """All live cards for `agent`, status DERIVED at read time (R11): refreshed within
    IDLE_AFTER_MIN = active, older = idle. TTL expiry already removed the dead."""
    cli = _resolve_client(c, allow_fallback)
    if cli is None:
        return []
    out: List[Dict] = []
    try:
        for key in cli.scan_iter(match=f"{_ns()}:incarnation:{agent}:*"):
            try:
                raw = cli.get(key)
                card = json.loads(raw) if raw else None
                if not card or not card.get("session_id"):
                    continue
                age = _age_min(card.get("refreshed", ""), now=now)
                card["age_min"] = age
                card["status"] = "active" if (age is not None and age < IDLE_AFTER_MIN) else "idle"
                out.append(card)
            except Exception:
                continue
    except Exception:
        return []
    return out


def live_incarnations(agent: str, my_session: Optional[str] = None,
                      tmp: Optional[str] = None,
                      now: Optional[float] = None,
                      c=None, allow_fallback: bool = True) -> List[Dict]:
    """All OTHER live sessions of `agent`, freshest first:
    [{session_id, age_min, has_seat, (status, claims when carded)}].

    Phase 3 (R10): TTL cards are the primary signal; Phase-1 activity markers still
    count for sessions that predate cards (organic migration -- a live pre-P3 session
    must not vanish from SIBLINGS). Where both exist, the card's richer fields win.
    Prefix-exact on the agent id (the wake_seat convention: 'claude' never enumerates
    'claude-2'). Never raises; broken sources read as solo -- the whisper must not
    fail because liveness was unreadable."""
    base = tmp or tempfile.gettempdir()
    fresh = wake_seat.fresh_minutes()
    t_now = now if now is not None else time.time()
    by_sid: Dict[str, Dict] = {}

    for card in read_cards(agent, c=c, allow_fallback=allow_fallback, now=t_now):
        sid = str(card.get("session_id") or "")
        if not sid or (my_session and sid == my_session):
            continue
        by_sid[sid] = {
            "session_id": sid,
            "age_min": card.get("age_min"),
            "has_seat": os.path.exists(wake_seat.seat_path(agent, sid, base)),
            "status": card.get("status"),
            "claims": card.get("claims") or [],
        }

    prefix = f"bifrost_wake_{agent}_"
    try:
        names = os.listdir(base)
    except Exception:
        names = []
    for name in names:
        if not (name.startswith(prefix) and name.endswith(".alive")):
            continue
        sid = name[len(prefix):-len(".alive")]
        if not sid or sid in by_sid or (my_session and sid == my_session):
            continue                       # carded sids already counted -- cards win (R10)
        try:
            ts = float(open(os.path.join(base, name)).read().strip())
        except Exception:
            continue                       # unreadable marker proves nothing -- skip
        age_min = max(0.0, (t_now - ts) / 60.0)
        if age_min >= fresh:
            continue                       # K7 threshold: staler than fresh_minutes() = not live
        by_sid[sid] = {
            "session_id": sid,
            "age_min": age_min,
            "has_seat": os.path.exists(wake_seat.seat_path(agent, sid, base)),
        }

    out = list(by_sid.values())
    out.sort(key=lambda d: (d["age_min"] is None, d["age_min"]))
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
