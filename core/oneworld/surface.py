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

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


def _live_presence() -> List[Dict[str, Any]]:
    """Default source: one row per logical agent from the live roster, reduced to the fields the
    surface shows. Fails soft -- any error propagates to agents_view, which reports it as
    `unavailable` rather than a false empty roster. The namespace is confirmed at wire time."""
    from core.comm import roster
    ns = "bifrost"  # confirmed against bifrost_ui.py at wire time (Heimdall's seam)
    rows = roster.by_agent(roster.roster(ns))
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "agent": r.get("agent"),
            "state": r.get("state"),
            "phase": r.get("phase"),
            "beat_age_s": r.get("beat_age_s"),
        })
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
        agents.append({
            "agent": str(r.get("agent") or "?"),
            "state": str(r.get("state") or "?"),
            "phase": phase,
            "beat_age_s": beat,
        })
    gaps = [f"{missing} agent(s) missing phase/beat"] if missing else []
    return {"ok": True, "as_of": as_of, "agents": agents,
            "bounds": _legend(True, len(agents), gaps)}
