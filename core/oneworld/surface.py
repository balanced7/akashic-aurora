"""The one-world surface adapter -- the standalone "what to show" half (spec d622ac).

This is the vertical-slice adapter Daniel asked for (2026-10-08): the core's first real, live,
agent-aware element. It assembles a serializable payload from roster presence; Heimdall wires the
"how to serve it" -- a polled `/api/world` endpoint in bifrost_ui.py (port 8787), his call, his
lane. This module holds NO web code and is a pure function of its presence source, so it is pinned
without a live Redis and reshaped freely to whatever his render needs.

THE LOAD-BEARING CONTRACT is honesty, the same rule as the floor and the bounds legend: a roster
read that FAILS reports `ok=False` with "roster unavailable", NEVER an empty agent list. "Nobody is
online" and "I could not see the roster" are different facts, and a dashboard that renders the
second as the first lies at exactly the moment the house is in trouble (zero is not no). Every view
carries a one-line bounds legend saying what it could not see (W1's law, surface-worded).

The presence source is injectable. The default reads the live roster and fails soft to unavailable;
its exact namespace and reduction are confirmed against bifrost_ui at wire time (Heimdall owns that
seam) -- until then a wrong guess reports unavailable, honestly, rather than a false reading.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# The roster's churn fields, passed through when the source has them (Heimdall's reshape, granted
# 2026-10-09). None when absent: unknown is never a guessed False or 0.
_CHURN_FIELDS = ("n_total", "n_dead", "split_brain", "churning")


def _live_presence() -> List[Dict[str, Any]]:
    """Default source: one row per logical agent from the live roster, reduced to the fields the
    surface shows. Fails soft -- any error propagates to agents_view, which reports it as
    `unavailable` rather than a false empty roster. Namespace confirmed live by Heimdall's wire."""
    from core.comm import roster
    ns = "bifrost"
    rows = roster.by_agent(roster.roster(ns))
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = {"agent": r.get("agent"), "state": r.get("state"), "phase": r.get("phase"),
               "beat_age_s": r.get("beat_age_s")}
        row.update({k: r.get(k) for k in _CHURN_FIELDS})
        out.append(row)
    return out


def _legend(ok: bool, n: int, gaps: List[str], reason: str = "") -> str:
    """Surface-worded bounds legend (W1's law: declare what you could not see before a verdict)."""
    if not ok:
        return f"roster unavailable ({reason}): cannot say who is online"
    if gaps:
        return f"{n} agent(s); could not fully see: {'; '.join(gaps)}"
    return f"{n} agent(s); complete, nothing hidden"


def agents_view(presence_source: Optional[Callable[[], List[Dict[str, Any]]]] = None, *,
                now: Optional[datetime] = None) -> Dict[str, Any]:
    """Assemble the live agent-presence payload:

        {"ok": bool, "as_of": "<iso>",
         "agents": [{"agent", "state", "phase", "beat_age_s"} ...],
         "bounds": "<what this view could not see>"}

    A failed or None source yields ok=False with an empty agent list and a legend that NAMES the
    blindness -- never a false "nobody online". A genuinely empty roster is ok=True with an empty
    list and a legend that says so: checked-and-empty is distinct from blind.
    """
    src = presence_source or _live_presence
    as_of = (now or datetime.now(timezone.utc)).isoformat()

    try:
        rows = src()
    except Exception as exc:  # noqa: BLE001 -- a dead read is UNAVAILABLE, named, never empty-roster
        return {"ok": False, "as_of": as_of, "agents": [],
                "bounds": _legend(False, 0, [], reason=f"{type(exc).__name__}: {exc}")}
    if rows is None:
        return {"ok": False, "as_of": as_of, "agents": [],
                "bounds": _legend(False, 0, [], reason="source returned None")}

    agents: List[Dict[str, Any]] = []
    missing = 0
    for r in rows:
        phase = r.get("phase")
        beat = r.get("beat_age_s")
        if phase is None or beat is None:
            missing += 1
        row = {
            "agent": str(r.get("agent") or "?"),
            "state": str(r.get("state") or "?"),
            "phase": phase,
            "beat_age_s": beat,
        }
        row.update({k: r.get(k) for k in _CHURN_FIELDS})
        agents.append(row)
    gaps = [f"{missing} agent(s) missing phase/beat"] if missing else []
    return {"ok": True, "as_of": as_of, "agents": agents,
            "bounds": _legend(True, len(agents), gaps)}


# ------------------------------------------------------------------ the floor, for a surface

FLOOR_MAX_AGE_S = 60.0
_FLOOR_CACHE: Dict[str, Any] = {}   # one per process: the cockpit polls, the floor evaluates once a minute

# (bucket in floor.evaluate's report, the status a surface shows)
_BUCKETS = (("live_firing", "fired"), ("shadow_would_fire", "fired"), ("clear", "clear"),
            ("unavailable", "unavailable"), ("off", "off"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def floor_view(entries=None, *, mode: Optional[str] = None, max_age_s: float = FLOOR_MAX_AGE_S,
               now: Optional[datetime] = None, evaluate: Optional[Callable] = None,
               clock: Callable[[], float] = time.monotonic,
               cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The floor's payload for a surface (GET /api/floor on the cockpit):

        {"ok", "as_of", "evaluated_at", "age_s", "mode",
         "entries": [{"key", "state", "status", "detail"}],   # status: fired|clear|unavailable|off
         "legend": <the ENGINE's found-vs-taken line, byte for byte>, "legend_sha256"}

    It evaluates at most once per `max_age_s` and hands the engine the previous statuses, so a
    polled surface journals a steady fire once, not once per poll. The legend is the engine's, never
    composed here (W4: a surface must not adjudicate its own silence). An engine that cannot run is
    ok=False, "cannot say what is silent" -- never an empty, calm-looking floor.
    """
    from core.oneworld import floor as _floor
    cache = _FLOOR_CACHE if cache is None else cache
    ev = evaluate or _floor.evaluate
    as_of = (now or datetime.now(timezone.utc)).isoformat()

    def blind(reason: str) -> Dict[str, Any]:
        legend = f"floor unavailable ({reason}): cannot say what is silent"
        return {"ok": False, "as_of": as_of, "evaluated_at": None, "age_s": None, "mode": mode,
                "entries": [], "legend": legend, "legend_sha256": _sha(legend)}

    try:
        ents = list(entries) if entries is not None else _floor.default_manifest()
        if mode:
            ents = _floor.apply_mode(ents, mode)
    except Exception as exc:  # noqa: BLE001 -- a manifest that cannot be built is blindness, named
        return blind(f"{type(exc).__name__}: {exc}")

    t = clock()
    fresh = (cache.get("report") is not None and cache.get("mode") == mode
             and t - cache.get("mono", float("-inf")) < max_age_s)
    if not fresh:
        try:
            report = ev(ents, previous=cache.get("statuses") or {})
        except Exception as exc:  # noqa: BLE001
            return blind(f"{type(exc).__name__}: {exc}")
        cache.update(report=report, mono=t, mode=mode, evaluated_at=as_of,
                     statuses=report.get("statuses") or {})
    report = cache["report"]

    seen: Dict[str, tuple] = {}
    for bucket, status in _BUCKETS:
        for rec in report.get(bucket) or []:
            seen[rec["key"]] = (status, rec.get("detail"))
    rows = []
    for e in ents:
        status, detail = seen.get(e.key, ("unavailable", "the engine's report did not account for this entry"))
        rows.append({"key": e.key, "state": e.state, "status": status, "detail": detail})

    legend = str(report.get("legend") or "")
    return {"ok": True, "as_of": as_of, "evaluated_at": cache.get("evaluated_at"),
            "age_s": round(t - cache["mono"], 1), "mode": mode, "entries": rows,
            "legend": legend, "legend_sha256": _sha(legend)}
