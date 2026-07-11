"""
Turn metrics (progress-bars data half; co-designed claude+deepseek 2026-07-11).

Semantic Relationship: TurnHistory estimates TurnProgress (median+p90; honesty-labeled)

The bars Daniel asked for need three numbers per working agent: an ETA, a %-done
estimate, and elapsed-vs-ETA. All three come from HISTORY of similar turns:

  RECORD  -- at each turn close the runner records {ask_kind, duration_s,
             progress_points, outcome, prompt_len_band, tool_count?} to a capped
             per-(agent, kind) Redis list (last HISTORY_CAP; regenerable-in-a-day
             telemetry -> ephemeral store is proportionate) + a best-effort firehose
             event (durable analytics tail; never on the hot path per the recorder
             lesson).
  ESTIMATE-- median + p90 over the bucket (deepseek's refutation of EWMA stands:
             turns do not trend, EWMA overfits the last 3). Min n=3 to show anything;
             confidence 'low' below n=8; 30s in-process cache so mid-turn reads are
             stable. The p90 is the honesty interval: 90% of similar turns finished
             inside it. An ETA is a MEDIAN OF N SIMILAR TURNS, never a promise (M8).
  VIEW    -- progress_view(agent): the /status payload's card data (deepseek's UI
             renders it; doctor --progress prints the poor-man's line). pct_estimate =
             min(95, points/median_points*100): never claims done while running; no
             history -> no % claim at all.

Everything fail-open: a metrics hiccup must never touch the turn it measures.
"""
from __future__ import annotations

import json
import statistics
import time
from typing import Any, Dict, Optional

HISTORY_CAP = 200
MIN_N = 3
LOW_CONFIDENCE_N = 8
EST_CACHE_TTL = 30.0
KEY_PREFIX = "bifrost:turn_metrics:"

_est_cache: Dict[str, Any] = {}
_pulse_counts: Dict[str, int] = {}


# ------------------------------------------------------------------ small pieces
def len_band(prompt_len: int) -> str:
    """small/medium/large at 500/2000 chars (deepseek: sub-bucket only if a bucket's
    CV demands it -- the band is RECORDED now so the estimator can split later)."""
    n = int(prompt_len or 0)
    return "small" if n < 500 else ("medium" if n < 2000 else "large")


def count_pulse(agent: str) -> None:
    """Turn-scoped progress-point counter (in-process; the turn lives in-process)."""
    _pulse_counts[str(agent)] = _pulse_counts.get(str(agent), 0) + 1


def take_pulse_count(agent: str) -> int:
    return _pulse_counts.pop(str(agent), 0)


def peek_pulse_count(agent: str) -> int:
    return _pulse_counts.get(str(agent), 0)


def _key(agent: str, kind: str) -> str:
    return f"{KEY_PREFIX}{agent}:{kind}"


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("turn-metrics")._client
    except Exception:
        return None


def _push_row(key: str, row: Dict[str, Any], cap: int) -> None:
    c = _client()
    if c is None:
        return
    c.rpush(key, json.dumps(row))
    c.ltrim(key, -cap, -1)


def _read_rows(key: str):
    c = _client()
    if c is None:
        return []
    out = []
    for raw in (c.lrange(key, 0, -1) or []):
        try:
            out.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    return out


def _worklive_read(agent: str):
    from core.comm import liveness
    return liveness.read(agent)


# ------------------------------------------------------------------ record
def record(agent: str, ask_kind: str, *, duration_s: float, progress_points: int,
           outcome: str, prompt_len: int = 0, tool_count: int = 0,
           tokens: Optional[Dict[str, int]] = None) -> None:
    """One turn's facts, at turn close. Best-effort, never raises into the turn."""
    try:
        row = {"ts": time.time(), "agent": str(agent), "ask_kind": str(ask_kind),
               "prompt_len_band": len_band(prompt_len),
               "duration_s": round(float(duration_s), 2),
               "progress_points": int(progress_points),
               "outcome": str(outcome), "tool_count": int(tool_count)}
        if tokens:
            row["tokens"] = tokens
        _push_row(_key(agent, ask_kind), row, HISTORY_CAP)
        # Deliberately NOT invalidating the estimate cache here: the 30s cache is the
        # mid-turn stability guarantee (a bar must not jump because a sibling turn just
        # closed); a fresh fact waits at most EST_CACHE_TTL to influence the ETA.
        try:
            from core.events.event_log import capture_event
            capture_event("turn_metrics", f"{agent} {ask_kind} {row['duration_s']}s "
                          f"pts={row['progress_points']} {outcome}",
                          agent_id=str(agent), detail=row)
        except Exception:
            pass
    except Exception:
        pass


# ------------------------------------------------------------------ estimate
def estimate(agent: str, ask_kind: str) -> Optional[Dict[str, Any]]:
    """{median_s, p90_s, median_points, n, confidence} for the bucket, or None when
    n < MIN_N (below that the bars show elapsed-only -- no invented ETA)."""
    key = _key(agent, ask_kind)
    cached = _est_cache.get(key)
    if cached and time.time() - cached["at"] < EST_CACHE_TTL:
        return cached["est"]
    rows = [r for r in _read_rows(key) if r.get("outcome") == "ok"]
    est = None
    if len(rows) >= MIN_N:
        durs = sorted(r["duration_s"] for r in rows)
        pts = sorted(int(r.get("progress_points", 0)) for r in rows)
        p90_i = max(0, min(len(durs) - 1, int(round(0.9 * (len(durs) - 1)))))
        est = {"median_s": statistics.median(durs),
               "p90_s": durs[p90_i],
               "median_points": statistics.median(pts) if pts else 0,
               "n": len(rows),
               "confidence": "ok" if len(rows) >= LOW_CONFIDENCE_N else "low"}
    if est is not None:    # absence is never cached: the ETA appears the moment n>=MIN_N
        _est_cache[key] = {"at": time.time(), "est": est}
    return est


def pct_estimate(points_seen: int, est: Optional[Dict[str, Any]]) -> Optional[int]:
    """min(95, points/median_points*100) -- never claims done while running; None
    without history (no invented percentages, M8)."""
    if not est or not est.get("median_points"):
        return None
    return int(min(95, round(points_seen / float(est["median_points"]) * 100)))


# ------------------------------------------------------------------ live view
def progress_view(agent: str, *, peek: bool = True, _wl=None) -> Optional[Dict[str, Any]]:
    """The bar card's data for one agent, or None when no turn is live. `peek` leaves
    the pulse counter intact (the /status poll must not consume the turn's count)."""
    try:
        wl = _wl if _wl is not None else _worklive_read(agent)
        if not wl or str(wl.get("phase", "idle")) in ("idle", "online", "replied"):
            return None
        detail = str(wl.get("detail", ""))
        ask_kind = detail.rsplit(":", 1)[-1] if ":" in detail else (detail or "?")
        started = float(wl.get("since_ts", time.time()))
        points = peek_pulse_count(agent) if peek else take_pulse_count(agent)
        est = estimate(agent, ask_kind)
        return {"agent": str(agent), "phase": wl.get("phase"), "ask_kind": ask_kind,
                "started_ts": started,
                "elapsed_s": round(max(0.0, time.time() - started), 1),
                "points_seen": points, "eta": est,
                "pct_estimate": pct_estimate(points, est)}
    except Exception:
        return None
