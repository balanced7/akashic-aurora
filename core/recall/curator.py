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


FORGE_WATCH_WINDOW_DAYS = 14.0   # provisional window (design decision 2, locked)
FORGE_WATCH_MIN_IMPRESSIONS = 8  # ...or this many fresh impressions, whichever first
FORGE_PROPOSAL_TTL_DAYS = 7.0    # unreviewed optimizer proposals expire (F2, sec.5)


def _forge_watch_rows(recs, store, now: float) -> Dict[str, List[Dict[str, Any]]]:
    """Tier-1 watch (F4) over provisional Forge edits + expiry sweep over stale proposals.
    ROLLBACK triggers (one-sided, reversibility absorbs the sparse-credit noise -- sec.11):
      - any NEW noise vote since the apply-time baseline, or
      - a credited lesson's fresh credit-rate falls below its baseline rate once enough
        fresh impressions exist (>= FORGE_WATCH_MIN_IMPRESSIONS).
    CONFIRM: the window passes (days or impressions) with no trigger -> the variant earned
    its keep; clear the provisional flag, keep the text, keep previous_text for history."""
    import json as _json
    from core.recall.at_action import _load_use
    from core.foundation.timeutil import to_epoch
    rows: Dict[str, List[Dict[str, Any]]] = {"rollback": [], "confirm": [], "expire": []}
    for rec in recs:
        name = rec.get("experiment_name")
        if not name:
            continue
        # --- proposal expiry sweep (F2) ---
        raw_prop = str(rec.get("forge_proposal") or "").strip()
        if raw_prop:
            try:
                at = to_epoch(_json.loads(raw_prop).get("at") or 0)
                if at and (now - at) / 86400.0 > FORGE_PROPOSAL_TTL_DAYS:
                    rows["expire"].append({"name": name})
            except Exception:
                rows["expire"].append({"name": name})   # unparseable proposal = stale
        # --- provisional watch (F4) ---
        forged_at = to_epoch(str(rec.get("forge_provisional") or "").strip() or 0)
        if not forged_at:
            continue
        try:
            base = _json.loads(str(rec.get("forge_baseline") or "{}"))
        except Exception:
            base = {}
        use = _load_use(store, f"learn:experiment:{name}")
        d_noise = int(use.get("noise", 0) or 0) - int(base.get("noise", 0) or 0)
        d_surf = int(use.get("surfaced", 0) or 0) - int(base.get("surfaced", 0) or 0)
        d_cred = _credit(use) - _credit(base)
        age_d = (now - forged_at) / 86400.0
        if d_noise > 0:
            rows["rollback"].append({"name": name, "why": f"noise vote on the variant (+{d_noise})"})
            continue
        base_surf = int(base.get("surfaced", 0) or 0)
        base_rate = (_credit(base) / base_surf) if base_surf else 0.0
        if base_rate > 0 and d_surf >= FORGE_WATCH_MIN_IMPRESSIONS \
                and (d_cred / d_surf) < base_rate:
            rows["rollback"].append({"name": name, "why":
                                     f"credit rate fell below baseline ({d_cred}/{d_surf} vs {base_rate:.2f})"})
            continue
        if age_d >= FORGE_WATCH_WINDOW_DAYS or d_surf >= FORGE_WATCH_MIN_IMPRESSIONS:
            rows["confirm"].append({"name": name, "age_days": round(age_d, 1),
                                    "fresh_impressions": d_surf, "fresh_credit": d_cred})
    return rows


def curation_report(*, store=None, learning_store=None, now: Optional[float] = None,
                    min_surfaced: int = BENCH_MIN_SURFACED,
                    min_age_days: float = BENCH_MIN_AGE_DAYS) -> Dict[str, Any]:
    """What the curator WOULD do (read-only): {bench, unbench, credited_ghosts, ghost_prune_count,
    surface_active, corpus} + the Forge sections {forge_rollback, forge_confirm, forge_expire}
    (F4 watch + F2 proposal expiry). Each row carries its evidence so the operator (or the
    wrap nudge) can see WHY. Fail-soft to an empty report."""
    out: Dict[str, Any] = {"bench": [], "unbench": [], "credited_ghosts": [],
                           "ghost_prune_count": 0, "surface_active": 0, "corpus": 0,
                           "forge_rollback": [], "forge_confirm": [], "forge_expire": []}
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
        try:   # Forge watch (F4) + proposal expiry (F2) -- read-only rows; apply() stamps
            fw = _forge_watch_rows(recs, store, now)
            out["forge_rollback"], out["forge_confirm"], out["forge_expire"] = \
                fw["rollback"], fw["confirm"], fw["expire"]
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
        # Forge stamps (F4 + F2): rollbacks restore the pre-edit text (reversibility is the
        # whole bet); confirms clear the provisional flag (the variant earned its keep);
        # expiries clear stale unreviewed proposals (process-level learning rate).
        rolled, confirmed, expired = [], [], []
        for row in report.get("forge_rollback", []):
            if learning_store.rollback_forge_edit(row["name"]):
                rolled.append(row["name"])
        for row in report.get("forge_confirm", []):
            try:
                key = f"learn:experiment:{row['name']}"
                from datetime import datetime as _dt
                learning_store.store.hset(key, mapping={
                    "forge_provisional": "", "forge_confirmed": _dt.utcnow().isoformat()})
                confirmed.append(row["name"])
            except Exception:
                pass
        for row in report.get("forge_expire", []):
            if learning_store.clear_forge_proposal(row["name"]):
                expired.append(row["name"])
        _invalidate_surface_cache()
        return {"benched": benched, "unbenched": unbenched,
                "ghosts_pruned": len(ghosts.get("pruned", [])),
                "kept_ghosts": ghosts.get("kept_credited", []),
                "forge_rolled_back": rolled, "forge_confirmed": confirmed,
                "forge_proposals_expired": expired}
    except Exception:
        return {"benched": [], "unbenched": [], "ghosts_pruned": 0, "kept_ghosts": [],
                "forge_rolled_back": [], "forge_confirmed": [], "forge_proposals_expired": []}


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
