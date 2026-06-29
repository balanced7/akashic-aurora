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
- **fully degrades to empty** on any error — a recall path must never brick the action.

LATENCY (honest): v1 loads + ranks the learning store on each call (correctness-first, fail-soft).
Since the hook fires on every Read/Edit/Write, the SOTA target is ~<=50ms via an mtime-keyed cache
pre-warmed at SessionStart (aider diskcache / Cursor Merkle pattern) — a documented next step, not v1.
The PreToolUse hook is non-blocking + fail-open, so cold-load latency delays a hint, never the action.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
# generic tokens that carry no recall signal (tooling/noise) — never used as query terms.
_STOP = {"core", "self", "true", "false", "none", "null", "test", "tests", "json",
         "http", "https", "www", "com", "the", "and", "for", "with", "this", "that",
         "py", "python", "git", "main", "init", "args", "data", "path", "file"}


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
             learning_store: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Rank ACTIVE lessons by relevance to the query; keep only those above the show-nothing floor."""
    from core.primitives.ranker import Ranker
    if learning_store is None:
        from core.learning.learning_store import get_learning_store
        learning_store = get_learning_store()
    recs = learning_store.load_all_learnings_from_store()
    items: List[Dict[str, Any]] = []
    for rec in recs:
        summary = rec.get("recommendation") or rec.get("actual") or rec.get("what_tried") or ""
        if not summary:
            continue
        items.append({
            "text": summary,
            "source": f"learn:experiment:{rec.get('experiment_name')}",
            "importance": 4 if str(rec.get("success", "")).lower() in ("yes", "true") else 3,
            "timestamp": rec.get("timestamp"), "kind": "lesson",
        })
    out: List[Dict[str, Any]] = []
    seen = set()
    for s in Ranker().rank(items, query=query, now=now):   # Ranker excludes superseded (is_active)
        if s.components.get("relevance", 0.0) <= min_relevance:
            continue   # SHOW-NOTHING floor (T_min): must actually match this path/command; never pad to `limit`
        src = s.item.get("source")
        if src in seen:
            continue   # dedup by source (one line per experiment — MMR-style: each item adds new info)
        seen.add(src)
        out.append(s.item)
        if len(out) >= limit:
            break
    return out


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
              learning_store: Optional[Any] = None) -> Dict[str, Any]:
    """Given a point of action (path and/or command), return the few highest-signal active items.
    Deterministic, no-LLM, FAITH-gated, fail-soft (returns an empty result on any error)."""
    try:
        query = _query_from(path, command)
        lessons = _lessons(query, now, limit, min_relevance, learning_store) if query else []
        locks = _locks(path, agent_id)
        faithful, conf = True, 1.0
        if lessons:
            from core.primitives.faithfulness import faithfulness_report
            skeleton = "\n".join(f"- {l['text']}  (source: {l['source']})" for l in lessons)
            rep = faithfulness_report(lessons, skeleton)
            faithful, conf = rep["faithful"], rep["confidence"]
            if not faithful:
                lessons = []   # never surface unfaithful recall — silence beats a fabricated hint
        return {"path": path, "command": command, "query": query, "lessons": lessons,
                "locks": locks, "shown": len(lessons) + len(locks),
                "faithful": faithful, "confidence": conf}
    except Exception as e:
        return {"path": path, "command": command, "query": "", "lessons": [], "locks": [],
                "shown": 0, "faithful": True, "confidence": 1.0, "error": type(e).__name__}


def render(result: Dict[str, Any], *, max_chars: int = 110) -> str:
    """Compact, agent-readable rendering for the hook's additionalContext. Empty result -> ''."""
    lines: List[str] = []
    for lk in result.get("locks", []):
        lines.append(f"[lock] {lk.get('held_by')} holds an advisory lock on this path — coordinate before editing")
    for l in result.get("lessons", []):
        s = l.get("text", "")
        if len(s) > max_chars:
            s = s[:max_chars].rsplit(" ", 1)[0] + "..."
        lines.append(f"[lesson] {s} (source: {l.get('source')})")
    if not lines:
        return ""
    # Factual framing (not imperative — imperative trips prompt-injection defenses). Hard total cap
    # well under Claude Code's 10k-char additionalContext limit.
    body = "Recall-at-action (Akashic) - facts relevant to what you're about to do:\n" + "\n".join(lines)
    return body[:900]
