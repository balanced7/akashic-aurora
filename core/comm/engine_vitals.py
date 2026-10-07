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
    except Exception as exc:                                               # noqa: BLE001
        # TYPED ABSENCE. Until 2026-10-07 this returned {"prompt": 0, "completion": 0}, so a seat
        # with no journal and a seat that ran all day and spent nothing rendered identically -- and
        # a quiet meter is the one nobody investigates. `measured` is the field that separates them;
        # the numeric keys stay PRESENT (as None) so every existing reader keeps its shape.
        return {"prompt": None, "completion": None, "measured": False,
                "why": "%s: %s" % (type(exc).__name__, str(exc)[:80])}
    # THE KEYS THE WRITER ACTUALLY SERIALIZES. This asked for "prompt"/"completion"; the journal
    # has always written "prompt_tokens"/"completion_tokens" (scripts/runner_token_journal.py:98),
    # so `.get` returned None, `or 0` made it a number, and the gauge reported a confident zero over
    # real traffic -- measured 2026-10-07 at 5,049,156 deepseek tokens shown as 0. W118, filed
    # 2026-08-07, and the `or 0` is why it survived two months without anyone doubting the reading.
    #
    # core/comm/doctor.py:1305-1306 has read the correct names all along, which is the tell: two
    # readers of one file disagreed and only the quieter one was wrong.
    #
    # The bare names are still accepted as a fallback so an older or hand-written journal is not
    # silently zeroed by the fix itself.
    def _pick(*names):
        for n in names:
            v = d.get(n)
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return None
        return None

    p = _pick("prompt_tokens", "prompt")
    c = _pick("completion_tokens", "completion")
    if p is None and c is None:
        # The file exists and carries neither shape: readable, and still not a measurement.
        return {"prompt": None, "completion": None, "measured": False,
                "why": "journal present but carries no token keys"}
    return {"prompt": p or 0, "completion": c or 0, "measured": True}


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
