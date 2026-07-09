"""Forge F0 -- replay harness + data-sufficiency audit (docs/lesson-forge-design-2026-07.md sec.9).

The Forge gate's premise (sec.4, independently derived by claude and DeepSeek under a
fence): the matcher is deterministic and history is durable, so RETRIEVAL behavior is
replayable even though sessions are not -- historical credit events become the held-out
validation set for lesson-TEXT edits. This module is the go/no-go instrument: it
reconstructs each lesson's historical contexts (credited = durable flip events on the
firehose; surfaced = the windowed injection ledger), replays the LIVE matcher pipeline
over them, and audits the result against the PRE-REGISTERED criteria (sec.9 F0 --
committed before this module existed; git proves the order).

Precedent: the show-nothing floor itself was calibrated this way once (recall vNext,
scratchpad recall_floor_calibration.py -- replay every credited pair + the 24h ledger).
F0 turns that one-off into a durable, tested instrument.

Read-only + fail-soft throughout: an audit never mutates corpus, counters, or ledgers.
Replay is deliberately SESSION-LESS: no anti-repeat exclusions, no self-echo window, no
lock checks -- those are per-session state, and the gate's question is "CAN this text
match that context", not "would it have shown in that exact session".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# --- pre-registered criteria constants (sec.9 F0; change only via a design-doc edit) ---
FIDELITY_REQUIRED = 1.0            # criterion 1: replay agrees with live matcher (sampled)
REHAB_MIN_CONTEXTS = 8             # criterion 2: surfaced contexts per rehab candidate...
REHAB_COVERAGE_REQUIRED = 0.70     # ...for >= 70% of candidates
CREDITED_MIN_CONTEXTS = 2          # criterion 3: credited contexts per credited lesson...
CREDITED_COVERAGE_REQUIRED = 0.50  # ...for >= 50% of credited lessons
TARGET_REPLAYABLE_REQUIRED = 0.80  # criterion 3b: flip targets resolving to a live query
NO_GO_UNREPLAYABLE = 0.50          # criterion 5: majority-unreplayable = premise fails
FALLBACK_MIN_RETENTION_DAYS = 14.0  # criterion 4: thinner ledger -> capture-side accrual


def flip_events(*, events: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Durable flip events (kind='flip') from the firehose, oldest-first; or an injected
    list for tests. Each: {target, credited, sources, at, agent_id}. Fail-soft to []."""
    if events is None:
        try:
            from core.events.event_log import get_event_log
            events = get_event_log().scan()
        except Exception:
            return []
    out: List[Dict[str, Any]] = []
    for ev in events or []:
        if not isinstance(ev, dict) or ev.get("kind") != "flip":
            continue
        d = ev.get("detail") or {}
        tgt = str(d.get("target") or "")
        if not tgt:
            continue
        try:
            credited = int(d.get("credited", 0) or 0)
        except Exception:
            credited = 0
        out.append({"target": tgt, "credited": credited,
                    "sources": [str(s) for s in (d.get("sources") or []) if s],
                    "at": str(ev.get("at") or ""), "agent_id": str(ev.get("agent_id") or "")})
    return out


def credited_contexts(*, events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[str]]:
    """source -> [target, ...] where that source was CREDITED (axis-1 validation set)."""
    out: Dict[str, List[str]] = {}
    for f in flip_events(events=events):
        if f["credited"] <= 0:
            continue
        for s in f["sources"]:
            bucket = out.setdefault(s, [])
            if f["target"] not in bucket:
                bucket.append(f["target"])
    return out


def surfaced_contexts(hours: float = 24.0 * 14,
                      *, injections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[str]]:
    """source -> [target, ...] from the injection ledger (axis-2 raw material). The ledger
    is WINDOWED temp state (prune_state) -- thinness here is exactly what criterion 4 probes."""
    if injections is None:
        try:
            from core.recall.at_action import recent_injections
            injections = recent_injections(hours)
        except Exception:
            return {}
    out: Dict[str, List[str]] = {}
    for inj in injections or []:
        if not isinstance(inj, dict):
            continue
        tgt = str(inj.get("t") or "")
        if not tgt:
            continue
        for s in inj.get("s", []) or []:
            bucket = out.setdefault(str(s), [])
            if tgt not in bucket:
                bucket.append(tgt)
    return out


def parse_target(target: str) -> Tuple[Optional[str], Optional[str]]:
    """Invert at_action.normalize_target: 'p:<path>' / 'c:<command>' -> (path, command).
    Unknown shapes -> (None, None) = unreplayable (criterion 5 counts these)."""
    t = str(target or "")
    if t.startswith("p:") and len(t) > 2:
        return t[2:], None
    if t.startswith("c:") and len(t) > 2:
        return None, t[2:]
    return None, None


def replay(target: str, *, learning_store: Optional[Any] = None, limit: int = 25,
           min_relevance: Optional[float] = None) -> List[Dict[str, Any]]:
    """Run the LIVE matcher pipeline (query builder -> trigger-aware relevance -> floor)
    over one historical target. Same code path recall_at uses, minus per-session state --
    so agreement with production is by construction, and a mismatch means wiring drift."""
    path, command = parse_target(target)
    if not (path or command):
        return []
    try:
        from core.recall import at_action as aa
        query = aa._query_from(path, command)
        if not query:
            return []
        floor = aa._floor_default() if min_relevance is None else float(min_relevance)
        items, _total = aa._lessons(query, None, max(1, int(limit)), floor,
                                    learning_store=learning_store)
        return items
    except Exception:
        return []


def fidelity_check(sample: Optional[List[Dict[str, Any]]] = None, hours: float = 48.0,
                   sample_limit: int = 60,
                   *, learning_store: Optional[Any] = None) -> Dict[str, Any]:
    """Criterion 1: for a RECENT window of real injection-ledger entries, replaying each
    entry's target must re-surface the sources the live matcher actually pushed. Recent on
    purpose -- counters and mined vocabulary drift over weeks, sessions add exclusions;
    within a fresh window the pipeline must agree with itself exactly."""
    if sample is None:
        try:
            from core.recall.at_action import recent_injections
            sample = recent_injections(hours)
        except Exception:
            sample = []
    sample = list(sample or [])[-max(1, int(sample_limit)):]
    checked = agreed = 0
    mismatches: List[Dict[str, Any]] = []
    for inj in sample:
        if not isinstance(inj, dict):
            continue
        tgt = str(inj.get("t") or "")
        srcs = [str(s) for s in inj.get("s", []) or [] if s]
        if not tgt or not srcs:
            continue
        got = {i.get("source") for i in replay(tgt, learning_store=learning_store)}
        for s in srcs:
            checked += 1
            if s in got:
                agreed += 1
            else:
                mismatches.append({"target": tgt[:100], "source": s})
    return {"checked": checked, "agreed": agreed,
            "rate": (agreed / checked) if checked else None,
            "mismatches": mismatches[:10]}


def _replayable_share(events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Share of flip targets that resolve to a non-empty live query (criteria 3b / 5)."""
    flips = flip_events(events=events)
    total = replayable = 0
    for f in flips:
        total += 1
        path, command = parse_target(f["target"])
        if not (path or command):
            continue
        try:
            from core.recall.at_action import _query_from
            if _query_from(path, command):
                replayable += 1
        except Exception:
            pass
    return {"flips": total, "replayable": replayable,
            "share": (replayable / total) if total else None}


def _rehab_candidates(*, store=None, learning_store=None) -> List[str]:
    """Rehab class (sec.5): surfaced >= 10, zero credit -- the Forge's primary edit targets.
    (Age-independent here: the audit asks about DATA coverage, not bench timing.)"""
    out: List[str] = []
    try:
        from core.learning.learning_store import get_learning_store, is_graduated, is_benched
        from core.recall.at_action import _load_use, _store
        from core.recall.curator import _credit
        ls = learning_store or get_learning_store()
        st = store or _store()
        for rec in ls.load_all_learnings_from_store():
            name = rec.get("experiment_name")
            if not name or is_graduated(rec) or is_benched(rec):
                continue
            use = _load_use(st, f"learn:experiment:{name}")
            if int(use.get("surfaced", 0) or 0) >= 10 and _credit(use) == 0:
                out.append(f"learn:experiment:{name}")
    except Exception:
        pass
    return out


def audit(*, events: Optional[List[Dict[str, Any]]] = None,
          injections: Optional[List[Dict[str, Any]]] = None,
          learning_store: Optional[Any] = None, store: Optional[Any] = None) -> Dict[str, Any]:
    """The F0 data-sufficiency audit, judged against the pre-registered criteria (sec.9 F0).
    Pure read; returns numbers + per-criterion verdicts. Injectable for tests."""
    cred = credited_contexts(events=events)
    surf = surfaced_contexts(injections=injections)
    rep_share = _replayable_share(events)
    rehab = _rehab_candidates(store=store, learning_store=learning_store)

    # credited-side coverage (criterion 3): among lessons with any credited context,
    # how many carry >= CREDITED_MIN_CONTEXTS distinct ones?
    cred_counts = {s: len(ts) for s, ts in cred.items()}
    cred_lessons = len(cred_counts)
    cred_covered = sum(1 for n in cred_counts.values() if n >= CREDITED_MIN_CONTEXTS)
    cred_cov_share = (cred_covered / cred_lessons) if cred_lessons else None

    # surfaced-side coverage (criterion 2): rehab candidates with enough noise contexts.
    rehab_counts = {s: len(surf.get(s, [])) for s in rehab}
    rehab_covered = sum(1 for n in rehab_counts.values() if n >= REHAB_MIN_CONTEXTS)
    rehab_cov_share = (rehab_covered / len(rehab)) if rehab else None

    # ledger retention span (criterion 4 evidence)
    retention_days = None
    try:
        from core.recall.at_action import recent_injections
        import time as _time
        window = injections if injections is not None else recent_injections(24.0 * 365)
        ats = [float(i.get("at", 0) or 0) for i in (window or []) if isinstance(i, dict)]
        if ats:
            retention_days = (_time.time() - min(ats)) / 86400.0
    except Exception:
        pass

    fid = fidelity_check(sample=injections, learning_store=learning_store) \
        if injections is not None else fidelity_check(learning_store=learning_store)

    verdicts = {
        "c1_fidelity": ("PASS" if (fid.get("rate") is not None and fid["rate"] >= FIDELITY_REQUIRED)
                        else "NA" if fid.get("rate") is None else "FAIL"),
        "c2_rehab_coverage": ("NA" if rehab_cov_share is None
                              else "PASS" if rehab_cov_share >= REHAB_COVERAGE_REQUIRED else "FAIL"),
        "c3_credited_coverage": ("NA" if (cred_cov_share is None or rep_share["share"] is None)
                                 else "PASS" if (cred_cov_share >= CREDITED_COVERAGE_REQUIRED
                                                 and rep_share["share"] >= TARGET_REPLAYABLE_REQUIRED)
                                 else "FAIL"),
        "c5_no_go": ("TRIGGERED" if (rep_share["share"] is not None
                                     and rep_share["share"] < NO_GO_UNREPLAYABLE) else "clear"),
    }
    verdicts["c4_fallback"] = (
        "TRIGGERED (F0b capture-side accrual)"
        if (verdicts["c2_rehab_coverage"] == "FAIL"
            and (retention_days is None or retention_days < FALLBACK_MIN_RETENTION_DAYS))
        else "not needed")

    return {
        "flips": rep_share["flips"], "flip_targets_replayable_share": rep_share["share"],
        "credited_lessons": cred_lessons,
        "credited_context_histogram": {
            ">=1": cred_lessons,
            ">=2": cred_covered,
            ">=3": sum(1 for n in cred_counts.values() if n >= 3),
        },
        "credited_coverage_share": cred_cov_share,
        "rehab_candidates": len(rehab),
        "rehab_coverage_share": rehab_cov_share,
        "rehab_context_counts": rehab_counts,
        "ledger_retention_days": retention_days,
        "fidelity": fid,
        "verdicts": verdicts,
    }
