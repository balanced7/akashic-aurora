"""T071-R1 relevance budget v1 -- boot's lesson section becomes MOST-RELEVANT under a
FIXED character budget (deepseek's Part 5 design governs; adopted by
creative-robustness-reconciliation-2026-07-15 row R1).

The anti-noise property IS the fixed cap: as the corpus grows, competition for the
budget gets tougher and the surface stays clean -- the depth stays one
knowledge_recall away (the budget PRIORITIZES, it never censors). Regression story:
the 2026-07-15 morning boot spent recency slots on 'r' / 'use it' / 'attempt 3'
test residue while real task-relevant lessons existed.

Score ladder (his spec, verbatim tiers):
  1.0  exact task-id mention (T\\d\\d\\d in both task and lesson)
  0.8  constraint with keyword overlap (v1 detector R1-a: category 'constraint*'
       OR an RB-\\d+ token in the text -- the tagged 'constraint kind' arrives with
       R2's lifecycle; this bridges until then)
  0.7  file-path overlap (lesson names a file the task names)
  0.5  category match (the lesson's domain words appear in the task)
  0.0  everything else (still eligible for leftover budget by recency+credit)
Recency is a small ADDITIVE tiebreak (<=0.05 over a 30-day window). Funnel credit
joins MULTIPLICATIVELY (R1-b) via the EXISTING core.recall.at_action.usefulness_factor
over recall:use:<source> counters -- zero new counters; a noise-decayed lesson can
sink below a clean lower tier, a proven one can climb above its keyword tier.

Render contract (R1-c, packet law): each entry clips at ENTRY_CLIP with an explicit
' ...[budget]' marker; the TOP hit is always included even when it must be clipped.
Kill switch (R1-d): AKASHIC_RELEVANCE_BUDGET=0 -> callers fall back to the legacy
recency/Ranker loader (see learning_loader.load_learnings_for_boot).
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, Dict, List, Optional

BUDGET_CHARS_DEFAULT = 2000
ENTRY_CLIP = 240
RECENCY_WINDOW_S = 30 * 86400
RECENCY_WEIGHT = 0.05

_TASK_ID = re.compile(r"\bT\d{3}\b")
_RB_ID = re.compile(r"\bRB-\d+\b")
_PATHISH = re.compile(r"[\w./\\-]+\.(?:py|md|json|ya?ml|toml|txt)\b", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9]{3,}")


def budget_chars() -> int:
    try:
        v = int(os.getenv("AKASHIC_RELEVANCE_BUDGET_CHARS", "") or BUDGET_CHARS_DEFAULT)
        return v if v > 0 else BUDGET_CHARS_DEFAULT
    except (TypeError, ValueError):
        return BUDGET_CHARS_DEFAULT


def _text_of(lesson: Dict[str, Any]) -> str:
    return " ".join(str(lesson.get(k) or "") for k in
                    ("experiment_name", "category", "what_tried", "recommendation"))


def _keywords(s: str) -> set:
    return set(_WORD.findall(s.lower()))


def _ts(lesson: Dict[str, Any]) -> float:
    raw = lesson.get("timestamp")
    if isinstance(raw, (int, float)):
        return float(raw)
    try:   # ISO fallback (LearningStore records vary by writer era)
        return time.mktime(time.strptime(str(raw)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0.0


def base_score(lesson: Dict[str, Any], task: str) -> float:
    """The ladder, exactly one tier per lesson (highest that matches)."""
    text = _text_of(lesson)
    task_ids = set(_TASK_ID.findall(task or ""))
    if task_ids and (task_ids & set(_TASK_ID.findall(text))):
        return 1.0
    kw_task = _keywords(task or "")
    cat = str(lesson.get("category") or "").lower()
    is_constraint = cat.startswith("constraint") or bool(_RB_ID.search(text))
    if is_constraint and (_keywords(text) & kw_task):
        return 0.8
    task_paths = {p.lower() for p in _PATHISH.findall(task or "")}
    text_paths = {p.lower() for p in _PATHISH.findall(text)}
    for extra in (lesson.get("files_affected") or []):
        text_paths.add(str(extra).lower())
    if task_paths & text_paths:
        return 0.7
    cat_words = _keywords(cat)
    if cat_words and cat_words <= kw_task:
        return 0.5
    return 0.0


def _default_credit_fn() -> Callable[[str], Dict[str, int]]:
    """The existing funnel counters (fail-open to neutral)."""
    try:
        from core.recall.at_action import _load_use, _store
        store = _store()
        return lambda source: _load_use(store, source)
    except Exception:
        return lambda source: {}


def score(lesson: Dict[str, Any], task: str, now: float,
          credit_fn: Callable[[str], Dict[str, int]]) -> float:
    from core.recall.at_action import usefulness_factor
    base = base_score(lesson, task)
    age = max(0.0, now - _ts(lesson))
    recency = RECENCY_WEIGHT * max(0.0, 1.0 - age / RECENCY_WINDOW_S)
    try:
        factor = usefulness_factor(credit_fn(str(lesson.get("experiment_name") or "")) or {})
    except Exception:
        factor = 1.0
    return (base + recency) * factor


def render_entry(entry: Dict[str, Any], max_chars: int = ENTRY_CLIP) -> str:
    """The boot line for one selected lesson -- deterministic, clip CONFESSED (R1-c)."""
    line = f"- [{entry.get('category') or 'general'}] {entry.get('source')}: " \
           f"{entry.get('recommendation') or entry.get('what_tried') or ''}".rstrip()
    if len(line) > max_chars:
        line = line[: max(0, max_chars - 12)].rstrip() + " ...[budget]"
    return line


def select_within_budget(store: Any, task: str, cap_chars: Optional[int] = None,
                         now: Optional[float] = None,
                         credit_fn: Optional[Callable[[str], Dict[str, int]]] = None
                         ) -> List[Dict[str, Any]]:
    """Rank every live lesson by the ladder and greedily fill the FIXED budget.
    Returns entries in the legacy loader's shape (+score) so the aggregator,
    skeleton and render paths stay byte-compatible. The TOP hit is always
    included (its render clips to fit); everything after competes for what
    remains. Graduated lessons are skipped (automation enforces them already)."""
    cap = int(cap_chars or budget_chars())
    now_f = float(now if now is not None else time.time())
    credit = credit_fn or _default_credit_fn()
    lessons = store if isinstance(store, list) else store.load_all_learnings_from_store()
    try:
        from core.learning.learning_store import is_graduated
    except Exception:
        def is_graduated(_l):
            return False
    scored = sorted(
        ((score(l, task, now_f, credit), base_score(l, task), _ts(l), l)
         for l in lessons if not is_graduated(l)),
        key=lambda t: (t[0], t[2]), reverse=True)
    # 'The rest are available on query but don't take boot space' (his Part 5):
    # zero-BASE lessons never ride while anything relevant exists. With a fully
    # irrelevant corpus, a small floor (top-3 by score) keeps boot non-empty --
    # and the funnel's noise decay (surfaced-often-never-useful -> 0.5x) sinks
    # residue below never-seen real lessons even there.
    relevant = [t for t in scored if t[1] > 0.0]
    pool = relevant if relevant else scored[:3]
    out: List[Dict[str, Any]] = []
    used = 0
    for sc, _b, _t, l in pool:
        entry = {"source": l.get("experiment_name"),
                 "recommendation": l.get("recommendation", ""),
                 "what_tried": l.get("what_tried", ""),
                 "success": l.get("success", ""),
                 "confidence": l.get("confidence", ""),
                 "category": l.get("category", ""),
                 "score": round(float(sc), 4)}
        cost = len(render_entry(entry, max_chars=min(ENTRY_CLIP, cap)))
        if not out:                      # R1-c: the top hit ALWAYS ships
            out.append(entry)
            used += cost
            continue
        if used + cost > cap:
            continue                     # keep scanning: a shorter lower hit may still fit
        out.append(entry)
        used += cost
    return out
