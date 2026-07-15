"""engine_vitals -- gauge_snapshot(), the engine room's pulse (T079-E1).

Spec: t079-engine-room-reconciliation-2026-07-15.md; deepseek's Zone-1 gauge
table is the contract. ONE call returning ONE dict, polled by the UI at ~2s:

    {"heartbeat": "active|idle|offline",
     "runtimes":  {...verbatim from the daemon presence card...},
     "tokens":    {"prompt": N, "completion": N},          # W1 daily journal
     "pages":     N,                                        # unread pager items
     "daemon_live": bool}

PURE READER over signals that already exist (presence card, daemon key, W1
journal file, pager list). Never raises -- a hostile or absent backend yields
the all-quiet snapshot (P6): the engine room must render even when the engine
is the thing that's broken.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

IDLE_AFTER_S = 300          # his Zone-1 table: active < 5m <= idle
_TS_FMT = "%Y-%m-%dT%H:%M:%S"


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _client(c=None, allow_fallback: bool = True):
    if c is not None:
        return c
    if not allow_fallback:
        return None
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def _heartbeat(card: Optional[Dict[str, Any]], now: float) -> str:
    if not card:
        return "offline"
    try:
        ts = str(card.get("ts") or "")[:19]
        then = time.mktime(time.strptime(ts, _TS_FMT))
        return "active" if (now - then) < IDLE_AFTER_S else "idle"
    except Exception:
        return "idle"       # a card with an unreadable stamp is present but unproven


def _today_journal(agent: str, journal_dir: Optional[str]) -> Dict[str, int]:
    try:
        base = journal_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "state")
        path = os.path.join(base, f"runner_{agent}_{time.strftime('%Y-%m-%d')}.json")
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return {"prompt": int(d.get("prompt") or 0), "completion": int(d.get("completion") or 0)}
    except Exception:
        return {"prompt": 0, "completion": 0}


def gauge_snapshot(agent: str, c=None, allow_fallback: bool = True,
                   journal_dir: Optional[str] = None,
                   now: Optional[float] = None) -> Dict[str, Any]:
    """The Zone-1 snapshot for one agent. Cheap (<=3 backend reads + 1 file
    stat), shape-stable, exception-free."""
    now_f = float(now if now is not None else time.time())
    out: Dict[str, Any] = {"heartbeat": "offline", "runtimes": {},
                           "tokens": {"prompt": 0, "completion": 0},
                           "pages": 0, "daemon_live": False}
    cli = _client(c, allow_fallback)
    card = None
    if cli is not None:
        try:
            raw = cli.get(f"{_ns()}:presence:{agent}")
            card = json.loads(raw) if raw else None
        except Exception:
            card = None
        try:
            out["daemon_live"] = bool(cli.exists(f"{_ns()}:daemon:{agent}"))
        except Exception:
            pass
        try:
            out["pages"] = len(cli.lrange(f"{_ns()}:pages", 0, -1) or [])
        except Exception:
            pass
    out["heartbeat"] = _heartbeat(card, now_f)
    if card:
        try:
            out["runtimes"] = dict(card.get("runtimes") or {})
        except Exception:
            pass
    out["tokens"] = _today_journal(agent, journal_dir)
    return out
