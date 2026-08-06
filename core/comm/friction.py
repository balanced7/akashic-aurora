"""friction -- read the collaboration tax from evidence that already exists (T196a).

Sol's recommendation ("measure collaboration friction"), fenced through deepseek (T196
spec, branches C + C2): the verb redesign is not allowed to call itself an improvement
without a baseline, and the baseline must claim nothing the anchors cannot show. This
module is a READER: fold() is pure (no I/O at all), gather() composes reads and writes
NOTHING -- observation split from action (T025), the same split expectations.sweep()
honors from the other side.

An EPISODE is one durable ask's lifetime. Terminal episodes come from the firehose
(the durable terminal events expectations.py emits -- T196b closed the ANSWERED gap);
open episodes come from the armed expectation records (expectations.snapshot). Every
number here follows the house honesty laws: a duration without evidence is None (never
0.0, never a now-based guess -- the fabricated-total lie one layer down), a rate over
zero closed episodes is None, and the report carries a structurally NON-EMPTY `blind`
list because a report that names no blindness is claiming omniscience.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.foundation.timeutil import to_epoch

# Terminal firehose kinds -> episode outcome. ECHO is deliberately distinct from
# ANSWERED (the T196 fence's one resolved disagreement): a T076c settle has NO message
# anywhere -- the answer arrived as ledger state, and the caller's move differs (read
# the ledger, not the mailbox).
TERMINAL_KINDS = {
    "expectation_settled_answered": "answered",
    "expectation_dead": "dead",
    "expectation_settled_done_task": "echo",
}

# Named blindness (no-silent-caps made structural). Static by design: these are facts
# about the ANCHORS, not about any one report.
BLIND = [
    "answered/dead durations exist only where the terminal event carries `created` "
    "(T196b, 2026-08-05) -- older episodes report duration None",
    "answered episodes are visible only from T196b onward: before it, an answered ask "
    "left no durable terminal event at all",
    "commands are not counted: CLI door captures are selective (boot/handoff/decision/"
    "learning), so operator keystrokes and shell work are invisible (fence C)",
    "silent stalls are invisible: an ask that never redrives and never settles renders "
    "as open, not as troubled (fence C2)",
    "usefulness is not measured: time-to-settle says an answer ARRIVED, not that it "
    "helped -- v2 candidates: re-ask window, self-reclamation rate (fence C2)",
    "reads the per-agent event stream (an index): an event whose index write degraded "
    "(T179 PARTIALLY) is on the canonical firehose but absent here",
]


def _redrives(detail: Dict[str, Any]) -> int:
    """Both spellings live: settled events carry `attempt`, dead events `attempts`."""
    for k in ("attempt", "attempts"):
        v = detail.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
    return 0


def _span(later: Optional[float], earlier: Any) -> Optional[float]:
    """Seconds between two moments, or None when either side lacks evidence."""
    if later is None or earlier is None:
        return None
    try:
        return max(0.0, float(later) - float(earlier))
    except (TypeError, ValueError):
        return None


def fold(terminal_events: Optional[List[Dict[str, Any]]],
         open_records: Optional[Dict[str, Dict[str, Any]]], *,
         now: float) -> Dict[str, Any]:
    """PURE fold of evidence into the friction report. No I/O; `now` injected so
    pins never sleep (the expectations-suite idiom)."""
    episodes: List[Dict[str, Any]] = []
    durations: List[float] = []
    counts = {"answered": 0, "dead": 0, "echo": 0}

    for ev in terminal_events or []:
        outcome = TERMINAL_KINDS.get(str(ev.get("kind") or ""))
        if not outcome:
            continue                                  # not an episode event
        detail = ev.get("detail") or {}
        refs = ev.get("refs") or []
        if not refs:
            continue                                  # malformed: no ask to attribute to
        try:
            closed_at = to_epoch(ev.get("at"))
        except Exception:
            closed_at = None
        duration = _span(closed_at, detail.get("created"))
        episodes.append({
            "ask_id": str(refs[0]), "peer": detail.get("to"), "outcome": outcome,
            "duration_s": duration, "redrives": _redrives(detail),
            "closed_at": ev.get("at"),
            "answer_id": detail.get("answer_id"),
        })
        counts[outcome] += 1
        if duration is not None:
            durations.append(duration)

    for oid, rec in (open_records or {}).items():
        try:
            attempt = int(rec.get("attempt", 0) or 0)
        except (TypeError, ValueError):
            attempt = 0
        deadline = rec.get("deadline_ts")
        try:
            deadline_in = (float(deadline) - float(now)) if deadline is not None else None
        except (TypeError, ValueError):
            deadline_in = None
        episodes.append({
            "ask_id": str(oid), "peer": rec.get("to"), "outcome": "open",
            "state": "redriving" if attempt > 0 else "dispatched",
            "age_s": _span(now, rec.get("created")), "redrives": attempt,
            "deadline_in_s": deadline_in,
        })

    n_closed = sum(counts.values())
    durations.sort()

    def _pct(p: float) -> Optional[float]:
        if not durations:
            return None                # a percentile of nothing is not a number
        i = int(round(p * (len(durations) - 1)))
        return durations[min(len(durations) - 1, max(0, i))]

    agg = {
        "n_open": len(open_records or {}),
        "n_answered": counts["answered"], "n_dead": counts["dead"],
        "n_echo": counts["echo"], "n_closed": n_closed,
        # 0/0 rendered as 0.0 would read as "nothing ever dies" -- None is the truth.
        "dead_rate": (counts["dead"] / n_closed) if n_closed else None,
        "settle_p50_s": _pct(0.5), "settle_p90_s": _pct(0.9),
        "n_duration_unknown": n_closed - len(durations),
    }
    return {"episodes": episodes, "agg": agg, "blind": list(BLIND)}


def gather(agent: str, *, window_h: float = 168, log=None,
           now: Optional[float] = None) -> Dict[str, Any]:
    """Compose the reads: per-agent firehose scan + armed-record snapshot -> fold.
    ZERO writes to any stream, record, or cursor (pinned). `log`/`now` injectable."""
    now = time.time() if now is None else float(now)
    if log is None:
        from core.events.event_log import EventLog
        log = EventLog()
    try:
        raw = log.scan(agent=str(agent))
    except Exception:
        raw = []
    horizon = now - float(window_h) * 3600.0
    events = []
    for ev in raw:
        if str(ev.get("kind") or "") not in TERMINAL_KINDS:
            continue
        try:
            at = to_epoch(ev.get("at"))
        except Exception:
            at = None                  # unparseable timestamp: keep (never silently drop)
        if at is not None and at < horizon:
            continue
        events.append(ev)
    from core.comm.expectations import snapshot
    return fold(events, snapshot(str(agent)), now=now)
