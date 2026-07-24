"""Session signals (RENEW slice A'') -- fold one session's tool calls into deterministic context-health signal aggregates.

The SIGNAL half of the Strand-A correlation dataset (the `fail` label half is slice A').

Semantic Relationship: SessionSignals aggregates ToolCalls (per session, deterministic)

WHY THIS EXISTS (docs/library/report/20260707_renew-strand-a-cheap-deterministic-conte_6eba11.md): Strand A found
the signals are cheap but were only being persisted while a manually-run bus recorder happened
to be alive -- it died 2026-07-07 and the dataset silently stopped growing, while the durable
`fail` LABELS (slice A') kept accruing. This module is the signal half made as durable as the
label half: the SessionEnd hook folds the session transcript through fold_signals() and captures
ONE `session_signals` event, so the signal x label correlation dataset accrues passively.

Signal catalog = Strand A's REVISED one, not the docket's original:
  * reread_rate is recorded but DEMOTED -- Strand A showed it saturates at 0.62-0.77 on healthy
    deep work; it stays in the row so the correlation can CONFIRM non-discrimination on labeled
    data, but no policy may threshold on it.
  * the promising family is churn-over-PROGRESS: calls_per_progress and
    tail_calls_after_last_progress, where progress = commits + FAIL->SUCCESS flips.
  * repetition (consecutive identical action) and max_target_touch come along at zero cost.

Deterministic, NO-LLM, pure fold -- consumers: the Strand-A correlation (join `fail` events by
session/time), later the context-health estimator. A session may emit MORE THAN ONE event when
it is resumed and ends again (the hook re-emits only when the call count grew); consumers keep
the NEWEST event per session_id.

Input contract (harness-agnostic; adapters build it -- e.g. the Claude Code SessionEnd hook
parses the session transcript): an ORDERED list of calls, each
    {"tool": str, "target": str, "ok": bool, "at": iso8601-str}
where `target` is core.recall.at_action.normalize_target() output ("p:<abspath>" for file
targets, "c:<normalized command>" for shell, "" for tools without one) so targets join exactly
against the `fail`/`flip` labels, and calls that never got a result are omitted by the adapter.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

# Progress marker: a SUCCEEDED shell command that lands work durably. Substring-matched against
# the normalized (lowercased) "c:" target. ship.py and mirror.py are this repo's commit doors;
# task-ledger closes are not visible in a transcript yet (future refinement, Strand A catalog).
_COMMIT_MARKERS = ("git commit", "mirror.py", "ship.py")


def _parse_at(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def fold_signals(calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold an ordered per-session call list into the signal aggregates (see module docstring).

    Pure + total: bad/missing fields degrade to neutral values, never raise. Rates are 0.0 when
    their denominator is 0. `calls_per_progress` is total_calls when NO progress happened (the
    reading: the whole session was churn), else total/progress rounded to 2 places.
    """
    total = len(calls)
    path_calls = 0
    rereads = 0
    repetitions = 0
    fails = 0
    flip_count = 0
    commit_count = 0
    seen_paths: set = set()
    failed_open: set = set()          # targets with an unresolved failure (flip pending)
    fail_targets: set = set()
    touch: Dict[str, int] = {}        # per-target hit count (any tool, targeted calls only)
    prev_key = None
    last_progress_idx = -1            # call index of the newest commit-or-flip
    first_at = last_at = None

    for i, call in enumerate(calls):
        tool = str(call.get("tool") or "")
        target = str(call.get("target") or "")
        ok = bool(call.get("ok", True))
        at = _parse_at(call.get("at") or "")
        if at is not None:
            first_at = first_at or at
            last_at = at

        key = (tool, target)
        if prev_key is not None and key == prev_key:
            repetitions += 1
        prev_key = key

        if target:
            touch[target] = touch.get(target, 0) + 1
        if target.startswith("p:"):
            path_calls += 1
            if target in seen_paths:
                rereads += 1
            seen_paths.add(target)

        if not ok:
            fails += 1
            if target:
                fail_targets.add(target)
                failed_open.add(target)
            continue

        # success path: a target coming back from failure is a FLIP; a landed commit is progress
        if target and target in failed_open:
            failed_open.discard(target)
            flip_count += 1
            last_progress_idx = i
        if target.startswith("c:") and any(m in target for m in _COMMIT_MARKERS):
            commit_count += 1
            last_progress_idx = i

    progress = commit_count + flip_count
    duration_s = (last_at - first_at).total_seconds() if (first_at and last_at) else 0.0
    return {
        "total_calls": total,
        "path_calls": path_calls,
        "distinct_paths": len(seen_paths),
        "reread_count": rereads,                       # DEMOTED signal -- see module docstring
        "reread_rate": round(rereads / path_calls, 4) if path_calls else 0.0,
        "repetition_count": repetitions,
        "repetition_rate": round(repetitions / total, 4) if total else 0.0,
        "max_target_touch": max(touch.values()) if touch else 0,
        "fail_count": fails,
        "distinct_fail_targets": len(fail_targets),
        "flip_count": flip_count,
        "commit_count": commit_count,
        "progress_count": progress,
        "calls_per_progress": (round(total / progress, 2) if progress else total),
        "tail_calls_after_last_progress": (total - 1 - last_progress_idx) if total else 0,
        "started_at": first_at.isoformat() if first_at else "",
        "ended_at": last_at.isoformat() if last_at else "",
        "duration_s": round(max(0.0, duration_s), 1),
    }
