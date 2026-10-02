"""W0.4 -- the instrument: what the touch stream costs, and what it covers.

SPEC: W0.4 of `fences/context-system/reconciliation.md` section 4. PINS: `tests/test_touch_stats_v1.py`.
READ BY: `py agent_cli.py context --stats`. Heimdall reads the 24 h number and rules A5b (whether
the touch stream shares the firehose or earns its own ring).

WHY IT EXISTS AT ALL. W0.2 put a new record on the spine's hot path, for every seat, on every tool
call. Shipping that without an instrument would be asking the house to trust a cost nobody measured,
which is the thing this house keeps filing lessons about. The spec pairs them deliberately: the emit
and the meter are one decision, and the meter runs for 24 h before Wave 1 may fence.

THE HEADLINE IS COVERAGE, NOT VOLUME. Measured on `events:raw` before W0.2 shipped: 89 of 6,918
records carried a session id, all of a single kind, and not one kind the hook emits carried any.
That is the reach map's "0.0% of captured events carrying a session id" as a live count. Session
coverage is the number the whole wave is for, so it is reported first, across EVERY kind rather than
only the one this wave added -- measuring only our own records would be grading our own homework.

THE THREE THINGS THIS MODULE REFUSES TO DO, each because the opposite has cost this house before:
  - It never reports a share of an empty population as 0.0. A share of nothing is UNKNOWN. A zero
    that means "nothing happened" and a zero that means "nothing was asked" are different facts.
  - It never estimates what it cannot measure. p95 hook latency and the anchor resolve cost are
    not captured today, so they come back UNCHECKABLE with the reason attached. An instrument that
    invents a number is worse than one that admits a hole, because the invented number is the one
    that gets quoted back.
  - It never reports a rate over a window the ring has already eaten. If the oldest record is
    younger than the window asked for, every rate over that window is understated, and the report
    says so instead of letting the reader believe a measurement that cannot be one.

Pure: every statistic is computed from records handed in. Nothing here reads Redis.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

#: Distinct from 0, from None and from a missing key, and it is a STRING so that it survives JSON,
#: a terminal render and a copy-paste into a report without quietly becoming null.
UNCHECKABLE = "UNCHECKABLE"

_WHY = {
    "p95_hook_latency_ms":
        "not captured: the PostToolUse payload carries no duration and touch.v1 does not stamp "
        "one yet, so there is nothing to take a percentile of. Stamping it is one field in the "
        "hook and the next slice after this one.",
    "anchor_resolve_cost_ms":
        "not captured: the context door (W0.6) is the thing that resolves an anchor, and it does "
        "not exist yet, so there is no call to time.",
}


def _pct(sorted_vals: Sequence[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    i = min(len(sorted_vals) - 1, max(0, int(round(q * (len(sorted_vals) - 1)))))
    return sorted_vals[i]


def compute(records: Sequence[Dict[str, Any]], *, now: float, window_h: float = 24.0,
            drops: int = 0) -> Dict[str, Any]:
    """One report over the raw event records handed in.

    `records` are events:raw rows as dicts ({at, kind, agent_id, session_id, detail}), with `at`
    either a float epoch or an ISO string. The caller decides how many to read; this decides what
    they mean."""
    floor = now - window_h * 3600.0
    rows: List[Dict[str, Any]] = []
    oldest_seen: Optional[float] = None

    for r in records or []:
        at = _at(r)
        if at is None:
            continue
        oldest_seen = at if oldest_seen is None else min(oldest_seen, at)
        if at >= floor:
            rows.append({**r, "_at": at})

    touches = [r for r in rows if r.get("kind") == "touch"]

    # ---- coverage, across every kind: the number the wave is for
    by_kind: Dict[str, Dict[str, int]] = {}
    with_sid = 0
    for r in rows:
        k = str(r.get("kind") or "?")
        slot = by_kind.setdefault(k, {"total": 0, "with_session": 0})
        slot["total"] += 1
        if str(r.get("session_id") or "").strip():
            slot["with_session"] += 1
            with_sid += 1

    coverage = {
        "total": len(rows),
        "with_session": with_sid,
        # A share of an empty population is UNKNOWN, never 0.0 -- see the module docstring.
        "share": (with_sid / len(rows)) if rows else None,
        "by_kind": by_kind,
    }

    # ---- rate, per seat
    per_hour: Dict[str, float] = {}
    span_h = max(1e-9, min(window_h, (now - oldest_seen) / 3600.0) if oldest_seen else window_h)
    for r in touches:
        a = str(r.get("agent_id") or "?")
        per_hour[a] = per_hour.get(a, 0.0) + 1.0
    per_hour = {a: round(n / span_h, 3) for a, n in per_hour.items()}

    # ---- shape: how many targets a touch actually carries, as a distribution
    # A touch whose targets are NULL could not be seen into, and counting it as zero targets would
    # drag the mean toward nothing and report a fleet that barely touches anything. Null is not
    # empty; the distribution is over touches whose targets are KNOWN, and the unknown share is
    # reported beside it rather than folded into it. Caught by running this on live data, where
    # the first render said mean=0.13 and the number was a lie told by its own denominator.
    counts: List[float] = []
    incomplete = truncated = unknown = 0
    for r in touches:
        d = r.get("detail") or {}
        tg = d.get("targets")
        if d.get("targets_incomplete"):
            incomplete += 1
        if d.get("targets_truncated"):
            truncated += 1
        if isinstance(tg, list):
            counts.append(float(len(tg)))
        else:
            unknown += 1
    counts.sort()

    report: Dict[str, Any] = {
        "window_h": window_h,
        "session_coverage": coverage,
        "touches": len(touches),
        "touches_per_hour": per_hour,
        "targets_per_touch": {
            "mean": round(sum(counts) / len(counts), 4) if counts else None,
            "p50": _pct(counts, 0.50),
            "p95": _pct(counts, 0.95),
            "max": counts[-1] if counts else None,
            "known": len(counts),
            "unknown": unknown,
        },
        "incomplete_share": (incomplete / len(touches)) if touches else None,
        "truncated_share": (truncated / len(touches)) if touches else None,
        "ring_retention_h": round((now - oldest_seen) / 3600.0, 3) if oldest_seen else None,
        "drops": int(drops),
        # Named, not estimated. The reason travels with the hole so the next reader inherits the
        # next slice rather than a mystery.
        "p95_hook_latency_ms": UNCHECKABLE,
        "anchor_resolve_cost_ms": UNCHECKABLE,
        "uncheckable_why": dict(_WHY),
    }

    # The ring ate part of the window: every rate above is a floor, not a measurement.
    report["window_truncated_by_ring"] = bool(
        oldest_seen is not None and (now - oldest_seen) < window_h * 3600.0 * 0.999
        and len(rows) > 0)
    return report


def _at(r: Dict[str, Any]) -> Optional[float]:
    v = r.get("at")
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v:
        try:
            import datetime as _dt
            return _dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except Exception:                                                 # noqa: BLE001
            return None
    return None


def render(rep: Dict[str, Any]) -> str:
    """One screen a human reads, with the headline first and the holes visible."""
    cov = rep["session_coverage"]
    share = cov["share"]
    share_s = f"{share:.1%}" if isinstance(share, float) else "UNKNOWN (no records in window)"
    out = [
        f"context --stats   window: {rep['window_h']}h",
        "",
        f"  SESSION COVERAGE   {cov['with_session']}/{cov['total']} = {share_s}",
        "    the number this wave exists to move; it was 89/6918 of one kind before W0.2",
    ]
    for k, v in sorted(cov["by_kind"].items(), key=lambda kv: -kv[1]["total"])[:8]:
        s = (v["with_session"] / v["total"]) if v["total"] else None
        out.append(f"      {k:<22} {v['with_session']:>5}/{v['total']:<6} "
                   f"{(f'{s:.0%}' if s is not None else '-'):>5}")
    out += ["", f"  TOUCHES            {rep['touches']} in window"]
    for a, n in sorted(rep["touches_per_hour"].items(), key=lambda kv: -kv[1]):
        out.append(f"      {a:<22} {n:>8.2f}/h")
    t = rep["targets_per_touch"]
    out += [
        "",
        f"  TARGETS PER TOUCH  mean={t['mean']} p50={t['p50']} p95={t['p95']} max={t['max']}"
        f"   (over {t['known']} knowable; {t['unknown']} unknowable excluded, not counted as zero)",
        f"  COULD NOT SEE IN   {_share(rep['incomplete_share'])}   "
        f"(a command whose targets are unknowable, reported as null, never as zero)",
        f"  TRUNCATED AT CAP   {_share(rep['truncated_share'])}",
        f"  RING RETENTION     {rep['ring_retention_h']}h"
        + ("   <- SHORTER THAN THE WINDOW: every rate above is a floor, not a measurement"
           if rep.get("window_truncated_by_ring") else ""),
        f"  TOUCHES DROPPED    {rep['drops']}",
        "",
        "  NOT MEASURED (named rather than estimated):",
    ]
    for k, why in rep["uncheckable_why"].items():
        out.append(f"    {k} = {UNCHECKABLE}")
        out.append(f"      {why}")
    return "\n".join(out)


def _share(v: Optional[float]) -> str:
    return f"{v:.1%}" if isinstance(v, float) else "UNKNOWN (no touches in window)"
