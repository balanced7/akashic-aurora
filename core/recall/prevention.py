"""prevention -- the missing consumer of the outcome stage log (S2, recall's AAR).

WHAT WAS BROKEN
---------------
`_log_outcome_stage` (at_action.py:973) has recorded every action resolution for weeks --
surfaced or not, flipped or not -- and shipped a contrastive design in its own docstring:

    success AND surfaced AND NOT flipped   ->  PREVENTION candidate
    success AND NOT surfaced               ->  its CONTROL arm

    "the credited-flip numerator counts RESCUE, never PREVENTION -- 'a first-try success
     credits and logs nothing' was the contrastive gate, by design -- so the single most
     valuable thing a lesson can do (stop the failure from happening at all) was invisible
     to the only value metric the system had."

Nothing consumed it. Live at first run: 18 flips against 3414 prevention candidates. Recall's
only value signal could see 18 events and was blind to 3414. This module reads that log.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not adjudicate. Fence r2 H-C1 (core/fleet/verdicts.py:156) reserves adjudication to
operator identities because "a two-record join doesn't close self-grading", and the stage log's
own rule is "OBSERVATION ONLY -- nothing here feeds ranking ... no automatic steer may ride this
signal until the stages are separately observed." So: `steers` is False in every report, and the
module writes no credit, no bench, no retirement. It observes and cites; a human rules.

THE HONESTY THAT COSTS THE MOST
-------------------------------
`COMPLIED` is NEVER minted. The deterministic join (stage log x repeat ledger) can prove a
violation -- a repeat is positive evidence, and `record_repeat` raises on unknown lessons so the
target namespace is sound. It cannot prove compliance, because
`clause_evidence_is_only_as_sound_as_the_id_namespace` established that the join is directional
and BOTH directions fail: "absence never means 'not done' and presence never means 'done'."
Nobody may have filed a repeat. So silence resolves to UNKNOWABLE, and the honest report is
mostly UNKNOWABLE by construction. That is the instrument confessing its blindness rather than
manufacturing a comfortable number -- the same discipline `precision_audit` states as
"UNLABELLED IS NOT NEGATIVE" and "STARVED, never 100%, on an empty ledger".

Closing the COMPLIED gap needs the Eye (what the seat ACTUALLY did next), which is the next
slice. This one makes the prevention numerator computable for the first time, contrastively.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any, Callable, Dict, List, Optional

VERDICTS = ("COMPLIED", "VIOLATED", "INAPPLICABLE", "UNKNOWABLE")

# Named beside every rate, per the stage log's own warning. A number without these invites the
# steer the docstring forbids.
CONFOUNDS = (
    "exposure-bias: a lesson surfaces BECAUSE the matcher judged the moment risky, so surfaced "
    "actions are not a random sample -- the control arm is not a matched control",
    "self-inflation: the positive feedback loop credits whatever was surfaced at flip time "
    "(resolve_action_outcome) with no causal check; this report deliberately ignores that counter",
    "self-sealing demotion: a benched lesson stops surfacing, so it can never earn the credit "
    "that would redeem it -- absence of exposure is not absence of value",
    "COMPLIED is unprovable from this join: silence is UNKNOWABLE, never compliance",
)


def _stage_dir() -> str:
    from core.recall import at_action as aa
    return getattr(aa, "_STAGE_DIR", "")


def read_stage_rows(stage_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every durable stage row. Sorted for determinism (P7)."""
    base = stage_dir or _stage_dir()
    rows: List[Dict[str, Any]] = []
    if not base or not os.path.isdir(base):
        return rows
    for path in sorted(glob.glob(os.path.join(base, "*.jsonl"))):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue          # a torn line is not a row; never a guess
                    rec["_session"] = os.path.basename(path)[:-6]
                    rows.append(rec)
        except OSError:
            continue
    rows.sort(key=lambda r: (str(r.get("at", "")), str(r.get("t", "")), r.get("_session", "")))
    return rows


def load_repeats(store: Any = None) -> Dict[str, List[Dict[str, Any]]]:
    """Repeats indexed by lesson source. The VIOLATED evidence side of the join.

    `recall_outcome` is the field that earns its place: fired = a READING failure,
    suppressed = a TARGETING failure. Only the FIRED class is evidence that a SURFACED lesson
    was violated -- a suppressed repeat says the lesson never reached the seat, which is a
    targeting defect, not a compliance one, and must not be scored as a violation here.
    """
    out: Dict[str, List[Dict[str, Any]]] = {}
    from core.learning.learning_store import LearningStore
    ls = store or LearningStore()
    rep = ls.repeat_report() or {}
    # The list lives under "entries". The first draft of this function guessed
    # ("repeats" or "rows"), matched NEITHER, and returned {} -- so the join reported ZERO
    # violations while the ledger held 24 repeats, 8 of them recall_outcome=fired. A silent
    # empty join is the confident-zero disease this whole module exists to expose, committed
    # by the module itself. Read the real key, and make a suspicious empty LOUD (below).
    entries = rep.get("entries") or []
    for row in entries:
        of = str(row.get("of") or "")
        if not of:
            continue
        key = of if of.startswith("learn:experiment:") else f"learn:experiment:{of}"
        out.setdefault(key, []).append(dict(row))
    declared = int(rep.get("count") or 0)
    if declared and not out:
        raise RuntimeError(
            f"repeat ledger declares count={declared} but the join extracted 0 rows -- the "
            f"record shape changed (keys: {sorted(rep.keys())}). REFUSING to report zero "
            f"violations from an empty join; that is indistinguishable from 'no violations' "
            f"and would be a confident zero.")
    return out


def _epoch(value: Any) -> Optional[float]:
    """Best-effort epoch seconds from either a float (stage) or ISO string (repeat)."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(value)).timestamp()
    except Exception:
        return None


def observe(*, stage_dir: Optional[str] = None,
            repeats: Optional[Dict[str, List[Dict[str, Any]]]] = None,
            sources_resolver: Optional[Callable[[str], bool]] = None) -> List[Dict[str, Any]]:
    """One observation per (prevention candidate, surfaced lesson). Never a judgment.

    TEMPORAL ATTRIBUTION (fixed after the first live run reported 170 violations from 8
    repeats). A repeat is evidence about ONE moment: the surfacing it followed. The first
    draft marked EVERY surfacing of a lesson as violated whenever a repeat existed for it
    anywhere in time, so a single repeat retroactively condemned all 63 prior impressions --
    a 20x inflation, and the temporal half of the directional-join law
    (clause_evidence_is_only_as_sound_as_the_id_namespace). Each fired repeat is now
    attributed to the NEAREST PRECEDING surfacing of that lesson, at most once. A repeat with
    no preceding surfacing in the window attributes to nothing and is reported as unattributed
    rather than dropped silently.
    """
    reps = load_repeats() if repeats is None else repeats
    rows = read_stage_rows(stage_dir)

    candidates: List[Dict[str, Any]] = []
    for rec in rows:
        if not (rec.get("ok") and rec.get("surfaced") and not rec.get("flipped")):
            continue
        for src in (rec.get("s") or []):
            candidates.append({"session": rec.get("_session", ""), "at": rec.get("at"),
                               "target": rec.get("t", ""), "source": str(src),
                               "verdict": "UNKNOWABLE", "evidence": [],
                               "authority": "observation"})

    # index candidates by source, ascending in time, for nearest-preceding attribution
    by_src: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates:
        by_src.setdefault(c["source"], []).append(c)
    for lst in by_src.values():
        lst.sort(key=lambda c: (_epoch(c["at"]) or 0.0))

    unattributed: List[str] = []
    for src, rlist in (reps or {}).items():
        fired = [r for r in rlist
                 if str(r.get("recall_outcome") or "").lower().startswith("fired")]
        for rep in fired:
            r_at = _epoch(rep.get("at"))
            pool = by_src.get(src) or []
            target = None
            for c in pool:                       # nearest PRECEDING, unclaimed
                c_at = _epoch(c["at"])
                if c_at is None or r_at is None:
                    continue
                if c_at <= r_at and c["verdict"] != "VIOLATED":
                    target = c                   # keep advancing -> last one <= r_at
            if target is not None:
                target["verdict"] = "VIOLATED"
                target["evidence"] = [str(rep.get("id") or "")]
            else:
                unattributed.append(str(rep.get("id") or ""))

    if sources_resolver is not None:
        for c in candidates:
            if not sources_resolver(c["source"]):
                c["verdict"], c["evidence"] = "UNKNOWABLE", []

    for c in candidates:
        c["unattributed_repeats"] = unattributed if False else c.get("unattributed_repeats")
    if candidates:
        candidates[0]["_unattributed_repeats"] = unattributed
    return candidates


def report(*, stage_dir: Optional[str] = None,
           repeats: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """The contrastive prevention report. Rates only over SETTLED rows; coverage always rides."""
    rows = read_stage_rows(stage_dir)
    obs = observe(stage_dir=stage_dir, repeats=repeats)

    prevention_candidates = sum(1 for r in rows
                                if r.get("ok") and r.get("surfaced") and not r.get("flipped"))
    control_arm = sum(1 for r in rows if r.get("ok") and not r.get("surfaced"))
    flips = sum(1 for r in rows if r.get("flipped"))
    failures = sum(1 for r in rows if not r.get("ok"))
    surfaced_total = sum(1 for r in rows if r.get("surfaced"))
    unsurfaced_total = len(rows) - surfaced_total

    counts = {v: sum(1 for o in obs if o["verdict"] == v) for v in VERDICTS}
    settled = counts["COMPLIED"] + counts["VIOLATED"] + counts["INAPPLICABLE"]
    coverage = (settled / len(obs)) if obs else 0.0

    # NO "violated_of_settled" RATE. COMPLIED and INAPPLICABLE are structurally unmintable
    # from this join, so that denominator can contain ONLY violations and the rate is 1.0 by
    # construction -- a number that reads as "100% of observations were violations" while
    # meaning "the only thing this instrument can see is violations". A rate over a degenerate
    # denominator is worse than no rate: it is a confident lie. Rates return when the Eye can
    # mint COMPLIED (next slice); until then, counts and coverage only.
    rates: Dict[str, float] = {}

    # The contrastive arms, reported as RAW rates with their confounds attached -- never as a
    # causal claim. Success-when-surfaced vs success-when-not is the shape the stage log was
    # built to expose; exposure-bias is why it is not yet an effect size.
    contrast = {
        "success_rate_when_surfaced": (
            sum(1 for r in rows if r.get("surfaced") and r.get("ok")) / surfaced_total
            if surfaced_total else None),
        "success_rate_when_not_surfaced": (
            sum(1 for r in rows if not r.get("surfaced") and r.get("ok")) / unsurfaced_total
            if unsurfaced_total else None),
    }

    per_lesson: Dict[str, Dict[str, int]] = {}
    for o in obs:
        d = per_lesson.setdefault(o["source"], {v: 0 for v in VERDICTS})
        d[o["verdict"]] += 1

    return {
        "stage_rows": len(rows),
        "observations": len(obs),
        "prevention_candidates": prevention_candidates,
        "control_arm": control_arm,
        "rescue_flips": flips,
        "failures": failures,
        "verdicts": counts,
        "unattributed_repeats": (obs[0].get("_unattributed_repeats") if obs else []),
        "settled": settled,
        "coverage": round(coverage, 4),
        "rates": rates,
        "contrast": contrast,
        "per_lesson": dict(sorted(per_lesson.items())),
        "confounds": list(CONFOUNDS),
        "steers": False,          # fence r2 H-C1 + the stage log's own standing rule
        "authority": "observation",
    }
