"""Line a run up with the practice log: the L1-L4 ladder (jam-spec 11.2, DATA 7.3).

  align(run, events, store, session=None) -> [Alignment]   every session overlapping the run (or the one named)
  align_session(run, events, info) -> Alignment             one session, best level first
  bar_t_ms(alignment, run, bar, beat=0) -> float            session t_ms of any bar position, extended by the tempo map

Alignment = {session, method: L1|L2|L3|L4, error_ms, bar0_t_ms, anchor, page_id, approx, refused, reason}

| Level | When                                              | Bar-line session time                         | Error   |
| L1    | an ack's log.session is the session               | ack.perf_ms(bar) - ack.log.t0_perf_ms         | 2 ms    |
| L2    | the session's meta.page_id equals an ack's page_id | perf_ms(bar) - meta.t0_perf_ms                | 2 ms    |
| L3    | meta.opened_at_client exists                      | bar_epoch_ms - epoch(opened_at_client)        | 50 ms   |
| L4    | nothing better, and the session was not buffered  | bar_epoch_ms - epoch(opened_at)               | 150 ms  |

A buffered session without opened_at_client is refused at L4: its server open time can be an hour late. Every
anchor has the shape tempomap.session_t_ms takes, so one formula serves all four levels. Read only.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional, Tuple

from arsenal.jam import tempomap

ERROR_MS = {"L1": 2, "L2": 2, "L3": 50, "L4": 150}
OVERLAP_SLACK_MS = 5000


def epoch_ms_of(iso) -> Optional[float]:
    if not isinstance(iso, str) or not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return None


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def session_window(info: dict) -> Tuple[Optional[float], Optional[float]]:
    """(start, end) of a session in epoch ms: its open time (client clock first) plus its last event time."""
    meta = info.get("meta") or {}
    start = epoch_ms_of(meta.get("opened_at_client")) or epoch_ms_of(info.get("opened_at"))
    if start is None:
        return None, None
    return start, start + max(0, int(info.get("last_t_ms") or 0))


def run_window(run: dict, events: List[dict]) -> Tuple[Optional[float], Optional[float]]:
    start = run.get("start_epoch_ms")
    if start is None:
        return None, None
    end = run.get("stopped_epoch_ms")
    if end is None:
        end = max([start] + [e.get("recorded_epoch_ms") or start for e in events])
    return start, end


def _result(method: str, info: dict, run: dict, anchor: dict, **extra) -> dict:
    bar0 = tempomap.session_t_ms(run["segments"], run["beats_per_bar"], 0, 0, anchor)
    out = {"session": info.get("session"), "run": run.get("run"), "method": method, "error_ms": ERROR_MS[method],
           "bar0_t_ms": bar0, "anchor": anchor, "page_id": None, "approx": method == "L4", "refused": False,
           "reason": None}
    out.update(extra)
    return out


def align_session(run: dict, events: List[dict], info: dict) -> dict:
    session = info.get("session")
    base = {"session": session, "run": run.get("run"), "method": None, "error_ms": None, "bar0_t_ms": None,
            "anchor": None, "page_id": None, "approx": False, "refused": True}
    if not run.get("segments"):
        return dict(base, reason="the run never started (it has no bars)")
    meta = info.get("meta") or {}
    acks = [e for e in events if e.get("kind") == "ack" and _num(e.get("perf_ms")) and _num(e.get("bar_epoch_ms"))]
    for a in acks:
        log = a.get("log")
        if isinstance(log, dict) and log.get("session") == session and _num(log.get("t0_perf_ms")):
            anchor = {"bar_epoch_ms": a["bar_epoch_ms"], "perf_ms": a["perf_ms"], "t0_perf_ms": log["t0_perf_ms"]}
            return _result("L1", info, run, anchor, page_id=a.get("page_id"))
    page_id, t0 = meta.get("page_id"), meta.get("t0_perf_ms")
    if page_id and _num(t0):
        for a in acks:
            if a.get("page_id") == page_id:
                anchor = {"bar_epoch_ms": a["bar_epoch_ms"], "perf_ms": a["perf_ms"], "t0_perf_ms": t0}
                return _result("L2", info, run, anchor, page_id=page_id)
    client = epoch_ms_of(meta.get("opened_at_client"))
    if client is not None:
        return _result("L3", info, run, {"bar_epoch_ms": 0.0, "perf_ms": 0.0, "t0_perf_ms": client})
    if meta.get("buffered"):
        return dict(base, method="L4", reason="the session was buffered and has no opened_at_client, so its server "
                                              "open time can be far from its first note")
    opened = epoch_ms_of(info.get("opened_at"))
    if opened is None:
        return dict(base, reason="the session has no open time")
    return _result("L4", info, run, {"bar_epoch_ms": 0.0, "perf_ms": 0.0, "t0_perf_ms": opened})


def bar_t_ms(alignment: dict, run: dict, bar: int, beat: float = 0) -> float:
    return tempomap.session_t_ms(run["segments"], run["beats_per_bar"], bar, beat, alignment["anchor"])


def overlapping(run: dict, events: List[dict], store, slack_ms: float = OVERLAP_SLACK_MS) -> List[str]:
    rs, re_ = run_window(run, events)
    if rs is None:
        return []
    out = []
    for row in store.list():
        try:
            info = store.info(row["session"])
        except Exception:  # an unreadable session is not an overlap
            continue
        ss, se = session_window(info)
        if ss is not None and ss <= re_ + slack_ms and se >= rs - slack_ms:
            out.append(row["session"])
    return out


def align(run: dict, events: List[dict], store, session: Optional[str] = None) -> List[dict]:
    if store is None:
        return [{"session": session, "run": run.get("run"), "method": None, "refused": True, "reason": "no log"}]
    sessions = [session] if session else overlapping(run, events, store)
    out = []
    for s in sessions:
        info = dict(store.info(s))
        info.setdefault("session", s)
        out.append(align_session(run, events, info))
    return out
