"""Recall curator (vNext loop 1) -- the funnel's triage made an ACTOR, not a report.

Semantic Relationship: Curator retires/restores Lessons by their earned track record

WHY (docs/recall-vnext-2026-07.md, evidence 2026-07-08): 7 days of funnel data showed 34 of 60
lessons had 5+ surfacings and ZERO earned credit -- more than half the corpus was pure injection
cost -- and the triage that names them had no hands. This module gives it hands, deterministically:

  * BENCH  -- surfaced >= min_surfaced AND no credit (helped/useful/engaged all 0) AND the record
    is older than min_age_days -> `benched` stamp (learning_store.mark_benched). Benched lessons
    leave the recall surfaces (cache/boot) but keep full history + full-corpus visibility --
    graduation's mechanics with the opposite cause. Never a delete.
  * UNBENCH -- any benched lesson whose counters now show credit gets its slot back (the safety
    valve: a quiet guardian that finally fires is restored automatically).
  * GHOSTS -- zero-credit counters for retired lessons are pruned (at_action.prune_ghost_counters);
    CREDITED ghosts are reported for supersession adjudication, never auto-folded (no edge data
    means no deterministic fold -- honesty over tidiness).

`curation_report()` is read-only; `apply_curation()` stamps. Both fail-soft. The wrap verb nudges
when the bench bucket is non-empty; `recall-curate [--apply]` is the operator door.

Age gate rationale: a YOUNG lesson with impressions and no credit may simply not have met its
moment; only a lesson that has had both exposure AND time gets benched. Credit definitions widen
in loop 3 (engaged / wrap votes), which automatically makes benching fairer over time.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

BENCH_MIN_SURFACED = 10      # exposure floor: it had its chances...
BENCH_MIN_AGE_DAYS = 10.0    # ...and its time. Both, or it stays.

_CREDIT_FIELDS = ("helped", "useful", "engaged")


def _age_days(rec: Dict[str, Any], now: float) -> Optional[float]:
    """Record age in days, or None when the timestamp is missing/unparseable (-> not benchable:
    we only bench what is PROVABLY old). timeutil.to_epoch (naive==UTC) matches how records are
    stamped -- raw .timestamp() would read them as local (the self-echo flight-test bug)."""
    ts = str(rec.get("timestamp") or "").strip()
    if not ts:
        return None
    try:
        from core.foundation.timeutil import to_epoch
        ep = to_epoch(ts)
        return max(0.0, (now - ep) / 86400.0) if ep else None
    except Exception:
        return None


def _credit(use: Dict[str, Any]) -> int:
    return sum(int(use.get(f, 0) or 0) for f in _CREDIT_FIELDS)


def curation_report(*, store=None, learning_store=None, now: Optional[float] = None,
                    min_surfaced: int = BENCH_MIN_SURFACED,
                    min_age_days: float = BENCH_MIN_AGE_DAYS) -> Dict[str, Any]:
    """What the curator WOULD do (read-only): {bench, unbench, credited_ghosts, ghost_prune_count,
    surface_active, corpus}. Each bench/unbench row carries its evidence so the operator (or the
    wrap nudge) can see WHY. Fail-soft to an empty report."""
    out: Dict[str, Any] = {"bench": [], "unbench": [], "credited_ghosts": [],
                           "ghost_prune_count": 0, "surface_active": 0, "corpus": 0}
    try:
        from core.learning.learning_store import get_learning_store, is_graduated, is_benched
        from core.recall.at_action import _load_use, _store
        learning_store = learning_store or get_learning_store()
        store = store or _store()
        now = now if now is not None else time.time()
        recs = learning_store.load_all_learnings_from_store()
        out["corpus"] = len(recs)
        for rec in recs:
            name = rec.get("experiment_name")
            if not name:
                continue
            source = f"learn:experiment:{name}"
            use = _load_use(store, source)
            credit = _credit(use)
            surfaced = int(use.get("surfaced", 0) or 0)
            if is_benched(rec):
                if credit > 0:   # earned its way back
                    out["unbench"].append({"name": name, "credit": credit, "surfaced": surfaced})
                continue
            if is_graduated(rec):
                continue         # graduation outranks benching; automation already owns its rule
            out["surface_active"] += 1
            age = _age_days(rec, now)
            if (surfaced >= min_surfaced and credit == 0
                    and age is not None and age >= min_age_days):
                out["bench"].append({"name": name, "surfaced": surfaced,
                                     "age_days": round(age, 1)})
        # Ghost counts come from triage (read-only) -- pruning mutates, so only apply() prunes.
        try:
            from core.recall.funnel import triage
            tri = triage(min_surfaced=1, store=store, learning_store=learning_store)
            ghost_rows = tri.get("ghosts", []) or []
            out["credited_ghosts"] = [g for g in ghost_rows
                                      if any(int(g.get(f, 0) or 0) for f in ("helped", "useful"))]
            out["ghost_prune_count"] = len(ghost_rows) - len(out["credited_ghosts"])
        except Exception:
            pass
    except Exception:
        pass
    return out


def apply_curation(report: Optional[Dict[str, Any]] = None, *, store=None,
                   learning_store=None) -> Dict[str, Any]:
    """Stamp the report: bench/unbench via learning_store (reversible state, never a delete) and
    prune ZERO-credit ghost counters. Returns {benched, unbenched, ghosts_pruned, kept_ghosts}.
    Recomputes the report when not given (apply-what-you-see is the CLI's job: it passes one)."""
    try:
        from core.learning.learning_store import get_learning_store
        from core.recall.at_action import prune_ghost_counters, _store
        learning_store = learning_store or get_learning_store()
        store = store or _store()
        report = report or curation_report(store=store, learning_store=learning_store)
        benched, unbenched = [], []
        for row in report.get("bench", []):
            if learning_store.mark_benched(
                    row["name"],
                    reason=f"curator: surfaced {row['surfaced']}x / 0 credit / {row['age_days']}d old"):
                benched.append(row["name"])
        for row in report.get("unbench", []):
            if learning_store.mark_benched(row["name"], undo=True):
                unbenched.append(row["name"])
        ghosts = prune_ghost_counters(store=store, learning_store=learning_store)
        _invalidate_surface_cache()
        return {"benched": benched, "unbenched": unbenched,
                "ghosts_pruned": len(ghosts.get("pruned", [])),
                "kept_ghosts": ghosts.get("kept_credited", [])}
    except Exception:
        return {"benched": [], "unbenched": [], "ghosts_pruned": 0, "kept_ghosts": []}


def _invalidate_surface_cache() -> None:
    """Curation changes what may surface; expire the recall TTL cache so the next call rebuilds
    (otherwise a benched lesson keeps riding the warm cache for up to the TTL)."""
    try:
        import os
        from core.recall.at_action import _CACHE_FILE
        if os.path.exists(_CACHE_FILE):
            os.utime(_CACHE_FILE, (0, 0))   # mtime -> epoch 0: expired, but stale-fallback intact
    except Exception:
        pass
