"""Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action.

Semantic Relationship: Recall surfaces ActiveKnowledge for a PointOfAction (path | command)

The pain this closes: storage is passive — lessons are written far more than they are read when
they matter. Given the file path or shell command an agent is about to act on, return the FEW
highest-signal ACTIVE items (relevant lessons + a lock/peer-activity warning) with `source`
pointers. The one reusable engine consumed by BOTH the `recall-at` CLI verb AND the PreToolUse
hook's `additionalContext` (so it is wired by construction, never built-but-not-wired).

Design — deterministic, no-LLM, fail-soft (SOTA-informed; see docs/agent-experience-plan.md):
- **keyword/path-first relevance** via the shared Ranker (no embedding on the hot path).
- **SHOW NOTHING unless it clears a relevance floor** — a weak, off-topic hint at action-time is
  worse than silence (context-rot). We gate on the Ranker's RELEVANCE component specifically, not
  the blended score, so a merely-important-but-irrelevant lesson never fires.
- **cap at a few entries** (default 3) — skeleton-first, lossy summary + lossless `source` pointer.
- **FAITH-1 gate** — recalled text runs through `faithfulness_report`; nothing unfaithful (a
  fabricated/unresolvable pointer) ever reaches the agent.
- **provenance-labelled** — each item is prefixed with outcome-status + author + claim-kind
  (worked / partial / unverified / anti-pattern; `advice` marks a forward-looking recommendation),
  so a self-authored, unverified hypothesis never returns framed as an external verified fact
  (Factor 1: opinion-laundering). Status reflects the AUTHOR'S OWN report (`worked` = self-reported
  success, not an independent check). The store already holds this; projection carries it to the surface.
- **fully degrades to empty** on any error — a recall path must never brick the action.

LATENCY: lesson items are served from a TTL disk cache (a fresh hook process can't hold an in-memory
one), so after warm-up a call is a ~1ms file read + rank, not a store round-trip. On a cold/down store
the cache returns last-known-good (stale fallback) instead of empty — this kills the cold-start empty.
The PreToolUse hook is also non-blocking + fail-open, so even a cold first call delays a hint, never the
action. Anti-repeat (don't re-surface a lesson already shown this session) is handled by the hook via
`exclude_sources`. Tunables: AKASHIC_RECALL_CACHE_TTL (sec), AKASHIC_RECALL_AT_ACTION=0 (off).
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
# generic tokens that carry no recall signal (tooling/noise) — never used as query terms.
_STOP = {"core", "self", "true", "false", "none", "null", "test", "tests", "json",
         "http", "https", "www", "com", "the", "and", "for", "with", "this", "that",
         "py", "python", "git", "main", "init", "args", "data", "path", "file"}

# --- warm disk cache: a fresh hook process can't keep an in-memory cache, so cache the projected
# lesson items to a small JSON file (read ~1ms) instead of cold-connecting the store every call.
# Fresh (within TTL) -> read it; expired -> refresh from the store; store fails (cold/down) -> fall
# back to the STALE cache (last-known-good) -- this is what kills the cold-start empty. Env-tunable.
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "akashic_recall")
_CACHE_FILE = os.path.join(_CACHE_DIR, "lesson_items.json")
_CACHE_TTL = float(os.getenv("AKASHIC_RECALL_CACHE_TTL", "120"))


def _project_items(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for rec in recs:
        # Track WHICH field the surfaced text came from: `recommendation` is forward-looking advice
        # (a claim), `actual` is an observed outcome (evidence), `what_tried` is the action. The
        # reader must be able to tell a claim from evidence, so carry the field through (-> _provenance_tag).
        summary, field = "", ""
        for f in ("recommendation", "actual", "what_tried"):
            if rec.get(f):
                summary, field = rec[f], f
                break
        if not summary:
            continue
        success = str(rec.get("success", "")).lower()
        items.append({
            "text": summary,
            "source": f"learn:experiment:{rec.get('experiment_name')}",
            "importance": 4 if success in ("yes", "true") else 3,
            "timestamp": rec.get("timestamp"), "kind": "lesson",
            # Provenance carried to the surface so a self-authored, unverified hypothesis can never
            # return wearing the costume of an external verified fact (Factor 1: opinion-laundering).
            # The store already holds all of this; the old projection discarded it at this seam.
            "success": success,
            "agent_id": rec.get("agent_id", ""),
            "confidence": rec.get("confidence", ""),
            "anti_pattern": rec.get("anti_pattern", ""),
            "field": field,
        })
    return items


def _cached_items(learning_store: Optional[Any]) -> List[Dict[str, Any]]:
    """Projected lesson items via a TTL disk cache with stale-fallback. An INJECTED store (tests)
    bypasses the cache for determinism; only the production singleton path is cached."""
    if learning_store is not None:
        return _project_items(learning_store.load_all_learnings_from_store())
    try:
        if (time.time() - os.stat(_CACHE_FILE).st_mtime) < _CACHE_TTL:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)          # fresh cache hit (~1ms, no store round-trip)
    except Exception:
        pass
    try:
        from core.learning.learning_store import get_learning_store
        items = _with_usefulness(_project_items(get_learning_store().load_all_learnings_from_store()))
        if items:
            try:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(items, f)
            except Exception:
                pass
        return items
    except Exception:
        try:                                  # store cold/down -> last-known-good (kills cold empties)
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


# Per-session anti-repeat files live here (the hook writes them; this module prunes them). Keep this
# path in sync with claude_pretooluse.py:_SEEN_DIR.
_SEEN_DIR = os.path.join(_CACHE_DIR, "seen")


def warm_cache(learning_store: Optional[Any] = None) -> int:
    """Force-refresh the lesson-item disk cache from the store (ignores TTL). Best-effort; returns the
    item count (0 on failure). Call at session start (SessionStart hook / boot) so the FIRST recall is
    already warm -- the last cold-start corner."""
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        items = _with_usefulness(_project_items(learning_store.load_all_learnings_from_store()))
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f)
        return len(items)
    except Exception:
        return 0


def prune_state(max_age_days: float = 7.0) -> int:
    """Best-effort sweep of stale per-session state files (anti-repeat seen-sets, open impressions, and
    last-outcomes). Returns the count removed. The cache itself is a single self-refreshing file."""
    removed = 0
    cutoff = time.time() - max_age_days * 86400.0
    for d in (_SEEN_DIR, _IMP_DIR, _OUTCOME_DIR):
        try:
            for name in os.listdir(d):
                p = os.path.join(d, name)
                try:
                    if os.path.isfile(p) and os.stat(p).st_mtime < cutoff:
                        os.remove(p)
                        removed += 1
                except Exception:
                    pass
        except Exception:
            pass
    return removed


# --- usefulness feedback loop: recall learns what's LOAD-BEARING. Each lesson accrues counters in the
# Store (recall:use:<source>): `surfaced` (auto, each time it's shown) + explicit `useful`/`noise` votes
# (via `agent_cli.py recall-feedback`). A smoothed factor then boosts proven-useful lessons and decays
# ones surfaced often yet never useful -- self-improving relevance, deterministic, no LLM. Counters are
# baked into the warm cache at build time, so the hot path stays a pure file read.
_USE_PREFIX = "recall:use:"


def _store():
    from core.foundation.store import create_store
    return create_store()


def _load_use(store, source: str) -> Dict[str, int]:
    try:
        raw = store.get(_USE_PREFIX + str(source))
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _with_usefulness(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach each lesson's usefulness counters (read once at cache-build time -> off the hot path)."""
    try:
        store = _store()
        for it in items:
            it["_use"] = _load_use(store, it.get("source"))
    except Exception:
        pass
    return items


def usefulness_factor(use: Optional[Dict[str, int]]) -> float:
    """Smoothed ranking multiplier in [0.5, 1.5]. Neutral (1.0) for unseen; ->1.5 for proven-useful;
    ->0.5 for noise-voted or surfaced-often-yet-never-useful (the automatic noise decay)."""
    use = use or {}
    useful = int(use.get("useful", 0))
    noise = int(use.get("noise", 0))
    helped = int(use.get("helped", 0))            # automatic contrastive positive (FAIL->SUCCESS flip)
    surfaced = int(use.get("surfaced", 0))
    eff = useful - noise + min(helped, surfaced)  # cap helped at impressions (defends join drift)
    denom = max(surfaced, useful + noise + helped) + 2.0   # rate, not raw count -> anti-runaway
    rate = max(0.0, min(1.0, (eff + 1.0) / denom))   # ~0.5 neutral; ->1 proven; ->0 stale/noise
    return 0.5 + rate


def record_feedback(source: str, kind: str = "useful", *, store=None) -> bool:
    """Record a usefulness signal for a recalled lesson. kind: 'useful'/'noise' (explicit votes) or
    'helped' (the automatic contrastive positive -- a FAIL->SUCCESS flip). Best-effort, repeatable."""
    if not source or kind not in ("useful", "noise", "helped"):
        return False
    try:
        store = store or _store()
        use = _load_use(store, source)
        use[kind] = int(use.get(kind, 0)) + 1
        store.set(_USE_PREFIX + str(source), json.dumps(use))
        return True
    except Exception:
        return False


def full_record(source: str, *, learning_store: Optional[Any] = None) -> Dict[str, Any]:
    """The one-hop pull from a recalled lesson's lossy summary to its WHOLE record (what_tried,
    expected, actual, root_cause, metrics, ...) -- the escape hatch `render()` points to when more
    exists than the capped surface shows. `source` is the pointer already carried on every recalled
    item, e.g. `learn:experiment:NAME`. Fail-soft: {} on any error, bad pointer, or unknown source
    (a failed pull must never brick the caller, same discipline as recall_at)."""
    prefix = "learn:experiment:"
    try:
        if not source or not str(source).startswith(prefix):
            return {}
        exp_id = str(source)[len(prefix):]
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        return learning_store._load_experiment(exp_id) or {}
    except Exception:
        return {}


def bump_surfaced(sources, *, store=None) -> None:
    """Increment the `surfaced` (impression) counter for shown lessons -- best-effort, fire-and-forget."""
    try:
        store = store or _store()
        for s in sources:
            use = _load_use(store, s)
            use["surfaced"] = int(use.get("surfaced", 0)) + 1
            store.set(_USE_PREFIX + str(s), json.dumps(use))
    except Exception:
        pass


# --- implicit-useful: the contrastive FAIL->SUCCESS flip (automatic positive, no agent vote needed).
# At surface time PreToolUse records an "open impression" {target -> sources}; a PostToolUse hook calls
# resolve_outcome() when the action completes. If a target that JUST FAILED now SUCCEEDS, the lessons
# surfaced for it are credited 'helped' (consume-on-credit). Contrastive by construction: a first-try
# success credits nothing. All best-effort + fail-soft (a PostToolUse hook must never affect the action).
_IMP_DIR = os.path.join(_CACHE_DIR, "imp")
_OUTCOME_DIR = os.path.join(_CACHE_DIR, "outcome")


def _safe_id(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


def normalize_target(path: Optional[str] = None, command: Optional[str] = None) -> str:
    """Stable key for a point of action -- MUST be identical at surface (PreToolUse) and resolve
    (PostToolUse) time or the join silently evaporates. Paths -> normcased absolute; commands ->
    lowercased + whitespace-collapsed."""
    if path:
        try:
            return "p:" + os.path.normcase(os.path.abspath(path))
        except Exception:
            return "p:" + str(path)
    if command:
        return "c:" + " ".join(str(command).lower().split())
    return ""


def mark_impression(session_id: str, target: str, sources) -> None:
    """Record that `sources` were surfaced for `target` this session (the outcome-join key)."""
    srcs = [s for s in (sources or []) if s]
    if not session_id or not target or not srcs:
        return
    try:
        os.makedirs(_IMP_DIR, exist_ok=True)
        with open(os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": target, "s": srcs}) + "\n")
    except Exception:
        pass


def _impressions_for(session_id: str, target: str) -> list:
    out = []
    try:
        with open(os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("t") == target:
                        out += rec.get("s", [])
                except Exception:
                    pass
    except Exception:
        pass
    return list(dict.fromkeys(out))   # dedup, order-stable


def _clear_impressions(session_id: str, target: str) -> None:
    try:
        p = os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl")
        kept = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    if json.loads(line).get("t") != target:
                        kept.append(line)
                except Exception:
                    pass
        with open(p, "w", encoding="utf-8") as f:
            f.writelines(kept)
    except Exception:
        pass


def _outcome_file(session_id: str) -> str:
    return os.path.join(_OUTCOME_DIR, _safe_id(session_id) + ".json")


def _get_outcome(session_id: str, target: str):
    try:
        with open(_outcome_file(session_id), encoding="utf-8") as f:
            return json.load(f).get(target)
    except Exception:
        return None


def _set_outcome(session_id: str, target: str, status: str) -> None:
    try:
        os.makedirs(_OUTCOME_DIR, exist_ok=True)
        p = _outcome_file(session_id)
        d = {}
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        d[target] = status
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


def resolve_outcome(session_id: str, target: str, success: bool, *, store=None) -> int:
    """PostToolUse resolver. If `target` SUCCEEDS now after having JUST FAILED, credit the lessons
    surfaced for it with 'helped' (consume-on-credit, so one flip can't be farmed). Returns the number
    credited. Best-effort + fail-soft -- a first-try success credits nothing (the contrastive gate)."""
    if not session_id or not target:
        return 0
    credited = 0
    try:
        if success and _get_outcome(session_id, target) == "FAIL":
            for src in _impressions_for(session_id, target):
                if record_feedback(src, "helped", store=store):
                    credited += 1
            _clear_impressions(session_id, target)
        _set_outcome(session_id, target, "SUCCESS" if success else "FAIL")
    except Exception:
        pass
    return credited


def _query_from(path: Optional[str], command: Optional[str]) -> str:
    """Build a keyword query from a path (dir/stem tokens) and/or command. Keeps tokens len>3
    (the Ranker's keyword_relevance ignores shorter ones) minus generic noise; order-stable, deduped."""
    parts: List[str] = []
    if path:
        parts += _TOKEN_RE.findall(path.replace("\\", "/"))
    if command:
        parts += _TOKEN_RE.findall(command)[:16]
    out: List[str] = []
    for t in parts:
        t = t.lower()
        if len(t) > 3 and t not in _STOP and t not in out:
            out.append(t)
    return " ".join(out)


def _lessons(query: str, now: Optional[float], limit: int, min_relevance: float,
             learning_store: Optional[Any] = None,
             exclude_sources: Optional[set] = None) -> "tuple[List[Dict[str, Any]], int]":
    """Rank ACTIVE lessons by relevance; keep those above the show-nothing floor, minus any already
    surfaced this session (`exclude_sources` -> anti-repeat) and intra-call source dups. Returns
    (items capped at `limit`, TOTAL that cleared the floor) -- the total is what powers the N-of-M
    escape line in render(): the agent should know more exists even when `limit` hides it."""
    from core.primitives.ranker import Ranker
    items = _cached_items(learning_store)
    excl = exclude_sources or set()
    cands: List = []
    seen = set()
    for s in Ranker().rank(items, query=query, now=now):   # Ranker excludes superseded (is_active)
        if s.components.get("relevance", 0.0) <= min_relevance:
            continue   # SHOW-NOTHING floor (T_min): must actually match this path/command; never pad to `limit`
        src = s.item.get("source")
        if src in seen or src in excl:
            continue   # intra-call dedup + cross-action anti-repeat (each item adds NEW info)
        seen.add(src)
        # usefulness re-rank: proven-useful lessons rise; surfaced-often-yet-never-useful decay
        cands.append((s.score * usefulness_factor(s.item.get("_use")), s.item))
    cands.sort(key=lambda t: t[0], reverse=True)
    return [it for _, it in cands[:limit]], len(cands)


def _locks(path: Optional[str], agent_id: Optional[str]) -> List[Dict[str, Any]]:
    """A peer holding an advisory lock on this exact path = the single most actionable hint."""
    if not path:
        return []
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, agent_id or "(unidentified)")
    except Exception:
        return []
    if c.get("conflict"):
        return [{"held_by": c.get("held_by"), "reason": c.get("reason", "")}]
    return []


def recall_at(*, path: Optional[str] = None, command: Optional[str] = None,
              agent_id: Optional[str] = None, limit: int = 3,
              min_relevance: float = 0.0, now: Optional[float] = None,
              learning_store: Optional[Any] = None,
              exclude_sources: Optional[set] = None,
              count_surface: bool = False) -> Dict[str, Any]:
    """Given a point of action (path and/or command), return the few highest-signal active items.
    `exclude_sources` (lesson sources already shown this session) enables hook anti-repeat.
    Deterministic, no-LLM, FAITH-gated, fail-soft (returns an empty result on any error)."""
    try:
        query = _query_from(path, command)
        lessons, total = _lessons(query, now, limit, min_relevance, learning_store, exclude_sources) \
            if query else ([], 0)
        locks = _locks(path, agent_id)
        faithful, conf = True, 1.0
        if lessons:
            from core.primitives.faithfulness import faithfulness_report
            skeleton = "\n".join(f"- {l['text']}  (source: {l['source']})" for l in lessons)
            rep = faithfulness_report(lessons, skeleton)
            faithful, conf = rep["faithful"], rep["confidence"]
            if not faithful:
                lessons, total = [], 0   # never surface unfaithful recall — silence beats a fabricated hint
        if count_surface and lessons:
            bump_surfaced([l.get("source") for l in lessons])   # impression count (best-effort, feeds noise-decay)
        return {"path": path, "command": command, "query": query, "lessons": lessons,
                "locks": locks, "shown": len(lessons) + len(locks), "total": total,
                "faithful": faithful, "confidence": conf}
    except Exception as e:
        return {"path": path, "command": command, "query": "", "lessons": [], "locks": [],
                "shown": 0, "total": 0, "faithful": True, "confidence": 1.0, "error": type(e).__name__}


def _provenance_tag(item: Dict[str, Any]) -> str:
    """A terse, honest status prefix for a recalled lesson — the antidote to opinion-laundering
    (Factor 1). Encodes outcome-status + author + claim-kind from provenance the store already
    holds, so a self-authored, unverified hypothesis can't come back framed as an external verified
    fact. Status is the AUTHOR'S OWN report ('worked' = self-reported success, not an independent
    check). Kept ASCII + short to stay off the context-rot / meta-noise line (Factors 6, 9).

    NB: the store normalizes a MISSING success to 'no', so the non-success bucket is labelled
    'unverified' ('not a confirmed success' — failed OR never checked), never the over-claim 'failed'.
    A populated `anti_pattern` is the one case we *can* call out as actively known-bad."""
    success = str(item.get("success", "")).lower()
    author = str(item.get("agent_id") or "").strip()
    field = item.get("field") or ""
    parts: List[str] = []
    if item.get("anti_pattern"):
        parts.append("anti-pattern")          # documented known-bad: doing this IS the mistake
    elif success in ("yes", "true"):
        # 'worked', NOT 'verified': success=yes is the AUTHOR'S OWN report, not an independent check.
        # Calling it 'verified' would re-launder a self-claim as external fact (the exact Factor-1 trap).
        # Independent corroboration (a cross-agent `helped`) could later earn a stronger 'confirmed' tag.
        parts.append("worked")
    elif success == "partial":
        parts.append("partial")
    else:
        parts.append("unverified")
    if author and author.lower() != "unknown":
        parts.append(author)
    if field == "recommendation" and success not in ("yes", "true"):
        parts.append("advice")                # forward-looking suggestion, not an observation
    return "[" + " ".join(parts) + "]"


def render(result: Dict[str, Any], *, max_chars: int = 110) -> str:
    """Compact, agent-readable rendering for the hook's additionalContext. Each lesson is prefixed
    with a provenance tag (verification-status + author + claim-kind) so the agent reads it with the
    right epistemic weight rather than as a settled fact. Empty result -> ''.

    When more lessons cleared the relevance floor than `limit` surfaced, appends a single N-of-M
    escape line — the cheap one-hop pull to the rest, instead of silently truncating (the "recommend
    less, retrieve more" pull-side: a capped surface should say so, not pretend it's complete)."""
    lines: List[str] = []
    for lk in result.get("locks", []):
        lines.append(f"[lock] {lk.get('held_by')} holds an advisory lock on this path — coordinate before editing")
    for l in result.get("lessons", []):
        s = l.get("text", "")
        if len(s) > max_chars:
            s = s[:max_chars].rsplit(" ", 1)[0] + "..."
        lines.append(f"{_provenance_tag(l)} {s} (source: {l.get('source')})")
    if not lines:
        return ""
    shown, total = len(result.get("lessons", [])), result.get("total", 0)
    if total > shown:
        lines.append(f"... {shown} of {total} relevant lesson(s) shown — `recall-at --limit {total}` for the rest, "
                      f"or `recall --full <source>` for any one's whole record")
    # Factual framing (not imperative — imperative trips prompt-injection defenses). Hard total cap
    # well under Claude Code's 10k-char additionalContext limit.
    body = "Recall-at-action (Akashic) - facts relevant to what you're about to do:\n" + "\n".join(lines)
    return body[:900]
