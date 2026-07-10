"""Lookback (P7 / T027) -- one question over the rationale corpus, layered, drillable.

The T016 finding this closes: the system's temporal drill (story/events) answers "what
happened", but the strategic WHY lives scattered across docs/, research/reviewed/, notes,
promoted bus messages, chapter summaries and git commit bodies -- reachable only by knowing
where to look. `lookback("why is the bus ephemeral")` fans the question out to every
rationale corpus, ranks with the shared Ranker (deterministic, no LLM, no new storage --
each corpus projects to the Ranker item contract), floors on the RELEVANCE component
(show-nothing beats off-topic orientation, the arch-slice discipline), and returns layered
hits each carrying a drill pointer (path / note id / event ref / commit sha) and a currency
label (current / superseded / historical / retired) so dead law never reads as live.

A tiny hit counter per corpus accrues in the Store so the NEXT audit of this feature has a
funnel instead of anecdotes (the recall-vNext lesson: telemetry first, tuning later).
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIN_RELEVANCE = 0.2          # the arch-slice floor: must match THIS question, not merely be recent
PER_LAYER = 3                # hits per corpus layer (the battery gate is top-3 by design)

_STATUS_RE = re.compile(r"^\**\s*status\s*:?\**\s*:?\s*(.+?)\s*$", re.IGNORECASE)
_CLASS_RE = re.compile(r"^\**\s*class\s*:?\**\s*:?\s*(rationale|plan|test|reference)\b",
                       re.IGNORECASE)
# Doc-class prior (S5 residual, C3 root cause -- reconciled w/ deepseek 2026-07-10): a WHY
# verb should prefer docs that EXPLAIN choices over docs that catalog mechanisms. Docs
# self-declare via an optional `Class: rationale|plan|test|reference` header line (inert to
# check_doc_currency; unstamped = neutral -- incremental adoption). The prior lands on the
# Ranker's IMPORTANCE component -- a document-level signal orthogonal to stems -- never on
# relevance (the floor's semantics stay honest: relevance means "matches THIS question").
_CLASS_IMPORTANCE_DELTA = {"rationale": 1, "plan": -1, "test": -1}
BODY_CHARS = 12000           # rationale often sits DEEP: a synthesis doc's convergence and
                             # NOT-build verdicts land 6-10KB in; a 60-line head starved the
                             # battery (AGENTS.md's ownership rule lives at line ~64)
REFERENCE_DOCS = {"MODULE_INDEX.md", "LEXICON.md", "INDEX.md"}
                             # dictionaries and indexes answer WHAT a term means / WHERE a
                             # file is -- never WHY; as vocabulary-dense docs they otherwise
                             # outrank rationale on every terminology question (probe C1)


TF_LEN_UNIT = 4000   # chars of text per EXPECTED occurrence of a matched stem: a 12KB doc
                     # must use a term ~3x to fully own it; texts under one unit (commits,
                     # notes, message excerpts) keep full weight on a single mention -- the
                     # about-vs-mentions split only exists where there is room to catalog


def _stem_relevance(text: str, query: str) -> float:
    """Morphology-tolerant keyword relevance via the Ranker's designed relevance_fn seam:
    'superseding' must find 'supersession' -- a cold agent asks in their own words. Both
    sides reduce to 6-char prefix stems; crude, deterministic, and the relevance floor
    still gates (probe C3 root cause: exact-token matching).

    S5 fix (battery sec. 3b, live-fired 2026-07-10): coverage alone cannot tell "about X"
    from "mentions X" -- a keyword-dense catalog doc matches every stem of every comms
    question once and displaces the PRIMARY rationale. Each matched stem now contributes
    its CONCENTRATION, min(1, occurrences / (len(text)/TF_LEN_UNIT)), instead of a flat 1:
    long docs must REPEAT a term to own it; short texts keep the pre-S5 behavior exactly
    (their expected-occurrence floor is 1). Deterministic, zero new storage."""
    qwords = _stems(query)
    if not qwords:
        return 0.0
    counts = _matched_counts(text, qwords)
    if not counts:
        return 0.0
    expected = max(1.0, len(text) / TF_LEN_UNIT)
    return sum(min(1.0, c / expected) for c in counts.values()) / len(qwords)


def _stems(s: str) -> set:
    return {w[:6] for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3}


def _match_excerpt(text: str, query: str, width: int = 180) -> str:
    """The ~width-char window around the densest cluster of the query's stems -- a hit
    shows the passage that MADE it hit. The old head-of-doc excerpt rendered every deep
    match as its title block: useless for drilling, and it hid the answer the ranker had
    actually found (C3: the right doc ranked top-3 while its excerpt showed a headline)."""
    flat = " ".join(text.split())
    qwords = _stems(query)
    if not qwords:
        return flat[:width]
    matches = [(m.start(), m.group()[:6]) for m in re.finditer(r"[a-z0-9]+", flat.lower())
               if len(m.group()) > 3 and m.group()[:6] in qwords]
    if not matches:
        return flat[:width]
    best_start, best_n = matches[0][0], 0
    for i, (p, _) in enumerate(matches):
        seen = {s for x, s in matches[i:] if x < p + width}
        if len(seen) > best_n:
            best_start, best_n = p, len(seen)
    start = max(0, best_start - 20)
    prefix = "..." if start > 0 else ""
    return prefix + flat[start:start + width]


def _matched_counts(text: str, qwords: set) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) > 3:
            t = w[:6]
            if t in qwords:
                counts[t] = counts.get(t, 0) + 1
    return counts


def _build_idf_relevance(texts: List[str]):
    """S5 fix, second mechanism (probe C3 root cause): process-meta docs match a question's
    FUNCTION stems ('project', 'instead', 'corrected', 'editing') which appear corpus-wide,
    and out-cover the true rationale doc that matches only the topic stems. Weight each
    stem by its rarity across THIS call's collected corpus (per-call IDF: the fan-out
    already holds every item in memory, so document frequency is free, deterministic, and
    always current -- no storage, no embeddings, still the Ranker's relevance_fn seam).
    Concentration (TF_LEN_UNIT) composes: rare stems used REPEATEDLY carry the score."""
    import math
    n = len(texts) or 1
    df: Dict[str, int] = {}
    for t in texts:
        for s in _stems(t):
            df[s] = df.get(s, 0) + 1
    norm = math.log(n + 1)

    def _idf(stem: str) -> float:
        return math.log((n + 1) / (df.get(stem, 0) + 1)) / norm

    def rel(text: str, query: str) -> float:
        qwords = _stems(query)
        if not qwords:
            return 0.0
        weights = {s: _idf(s) for s in qwords}
        denom = sum(weights.values())
        if denom <= 0:
            return 0.0
        counts = _matched_counts(text, qwords)
        if not counts:
            return 0.0
        expected = max(1.0, len(text) / TF_LEN_UNIT)
        return sum(weights[s] * min(1.0, c / expected) for s, c in counts.items()) / denom

    return rel


# ---------------------------------------------------------------- corpus adapters
# Every adapter returns Ranker items: {"text", "source", "timestamp", "importance", ...extras}.
# Each is fail-soft: any error -> [] (a broken corpus drops out; lookback never bricks).

def _read_head(path: str, chars: int = BODY_CHARS) -> str:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(chars)


def _doc_status(head: str) -> str:
    for line in head.splitlines()[:12]:
        m = _STATUS_RE.match(line.strip())
        if m:
            low = m.group(1).lower()
            if low.startswith("superseded"):
                return "superseded"
            if low.startswith(("historical", "archived")):
                return "historical"
            if low.startswith("current"):
                return "current"
    return "unstamped"


def _doc_class(head: str) -> str:
    for line in head.splitlines()[:12]:
        m = _CLASS_RE.match(line.strip())
        if m:
            return m.group(1).lower()
    return ""


def _docs_items() -> List[Dict[str, Any]]:
    out = []
    docs = os.path.join(ROOT, "docs")
    paths = [os.path.join(docs, n) for n in sorted(os.listdir(docs))
             if n.endswith(".md") and n not in REFERENCE_DOCS]
    paths.append(os.path.join(ROOT, "AGENTS.md"))   # the root contract is rationale too
    for p in paths:
        try:
            head = _read_head(p)
            is_agents = "AGENTS.md" in p
            status = _doc_status(head) if not is_agents else "current"
            dclass = _doc_class(head) if not is_agents else "rationale"
            if dclass == "reference":
                continue        # self-declared reference class joins REFERENCE_DOCS: WHAT/WHERE, never WHY
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            # current docs outrank equally-relevant dead law, but historical stays
            # REACHABLE (a why-question's answer is often in its moment); the class
            # prior then nudges rationale above plans/tests at equal relevance.
            importance = {"current": 3, "unstamped": 2}.get(status, 1)
            importance = max(1, min(5, importance + _CLASS_IMPORTANCE_DELTA.get(dclass, 0)))
            out.append({"text": head, "source": rel, "timestamp": os.path.getmtime(p),
                        "importance": importance, "layer": "docs", "status": status,
                        "class": dclass or "unclassed", "drill": rel})
        except OSError:
            continue
    return out


def _research_items() -> List[Dict[str, Any]]:
    out = []
    rr = os.path.join(ROOT, "research", "reviewed")
    try:
        names = sorted(os.listdir(rr))
    except OSError:
        return []
    for n in names:
        if not n.endswith(".md"):
            continue
        p = os.path.join(rr, n)
        try:
            rel = f"research/reviewed/{n}"
            out.append({"text": _read_head(p, 80), "source": rel,
                        "timestamp": os.path.getmtime(p), "importance": 2,
                        "layer": "research", "status": "review", "drill": rel})
        except OSError:
            continue
    return out


def _note_items() -> List[Dict[str, Any]]:
    try:
        from core.learning.agent_memory import get_agent_memory
        notes = get_agent_memory().get_decisions(days=3650, include_superseded=True)
    except Exception:
        return []
    out = []
    for d in notes:
        status = "retired" if getattr(d, "superseded", False) else "current"
        out.append({"text": f"{d.title}\n{d.decision}", "source": f"mem:decision:{d.id}",
                    "timestamp": d.created_at, "importance": 3 if status == "current" else 1,
                    "layer": "notes", "status": status,
                    "drill": f"notes --all (id {d.id})"})
    return out


def _promoted_items() -> List[Dict[str, Any]]:
    try:
        from core.comm.promoter import promoted
        evs = promoted(limit=200)
    except Exception:
        return []
    out = []
    for e in evs:
        d = e.get("detail") or {}
        ref = str((e.get("refs") or [""])[0])
        out.append({"text": f"{d.get('frm','?')} -> {d.get('to','?')} [{d.get('kind','')}]: "
                            f"{str(d.get('content',''))[:600]}",
                    "source": ref, "timestamp": e.get("at", ""), "importance": 2,
                    "layer": "promoted", "status": d.get("kind", "msg"),
                    "drill": f"events --get {e.get('id', ref)}" if e.get("id") else ref})
    return out


def _chapter_items() -> List[Dict[str, Any]]:
    try:
        import json
        idx = os.path.join(ROOT, "chronicles", "story.index.json")
        data = json.load(open(idx, encoding="utf-8"))
        chapters = data.get("chapters") or data if isinstance(data, list) else data.get("chapters", [])
    except Exception:
        return []
    out = []
    for ch in chapters or []:
        if not isinstance(ch, dict):
            continue
        cid = ch.get("id", "")
        out.append({"text": f"{ch.get('title','')}\n{ch.get('summary','')}",
                    "source": f"narr:chapter:{cid}", "timestamp": ch.get("span_end", ""),
                    "importance": 2, "layer": "chapters", "status": ch.get("track", "chapter"),
                    "drill": f"story --chapter {cid}"})
    return out


def _git_items(limit: int = 250) -> List[Dict[str, Any]]:
    try:
        raw = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%H%x1f%ct%x1f%s%x1f%b%x1e"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=20).stdout
    except Exception:
        return []
    out = []
    for rec in raw.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) < 4 or not parts[0].strip():
            continue
        sha, ts, subject, body = parts[0].strip(), parts[1], parts[2], parts[3]
        out.append({"text": subject + "\n" + body[:800], "source": sha[:8],
                    "timestamp": float(ts) if ts.isdigit() else 0, "importance": 1,
                    "layer": "git", "status": "commit", "drill": f"git show {sha[:8]}"})
    return out


LAYERS = (("docs", _docs_items), ("research", _research_items), ("notes", _note_items),
          ("promoted", _promoted_items), ("chapters", _chapter_items), ("git", _git_items))


# ---------------------------------------------------------------- the fan-out
def lookback(question: str, *, per_layer: int = PER_LAYER,
             min_relevance: float = MIN_RELEVANCE, now: Optional[float] = None,
             layers: Any = None) -> List[Dict[str, Any]]:
    """Layered rationale hits for `question`, best-first WITHIN each layer, layers in
    doctrine order (docs -> research -> notes -> promoted -> chapters -> git). Each hit:
    {layer, source, status, score, excerpt, drill}. Show-nothing floor per the arch-slice
    discipline. `layers` narrows the sweep (e.g. ["docs","git"])."""
    q = (question or "").strip()
    if not q:
        return []
    from core.primitives.ranker import Ranker
    wanted = set(layers) if layers else None
    loaded: List[Any] = []
    for name, loader in LAYERS:
        if wanted and name not in wanted:
            continue
        try:
            loaded.append((name, loader()))
        except Exception:
            continue
    # Per-call IDF over everything this sweep collected (S5): ubiquitous stems stop
    # counting, so breadth stops beating rationale. Fail-soft to plain stem relevance.
    try:
        rel_fn = _build_idf_relevance([str(i.get("text", "")) for _, items in loaded
                                       for i in items])
    except Exception:
        rel_fn = _stem_relevance
    ranker = Ranker(relevance_fn=rel_fn)
    hits: List[Dict[str, Any]] = []
    for name, items in loaded:
        try:
            if not items:
                continue
            kept = 0
            for sc in ranker.rank(items, query=q, now=now):
                if sc.components.get("relevance", 0.0) < min_relevance:
                    continue
                it = sc.item
                text = str(it.get("text", ""))
                hits.append({"layer": name, "source": it.get("source", ""),
                             "status": it.get("status", ""),
                             "score": round(sc.components.get("relevance", 0.0), 3),
                             "excerpt": _match_excerpt(text, q),
                             "drill": it.get("drill", it.get("source", ""))})
                kept += 1
                if kept >= per_layer:
                    break
            _count(name, kept)
        except Exception:
            continue
    return hits


def _count(layer: str, kept: int) -> None:
    """Accrue the lookback funnel (queries + per-layer hits) so the next audit has numbers.
    Best-effort read-add-set (a lost race costs a count, never a query); survives restarts.
    Kill switch AKASHIC_LOOKBACK_NO_COUNT=1 (the battery pin reads canonical read-only)."""
    if os.environ.get("AKASHIC_LOOKBACK_NO_COUNT") == "1":
        return
    try:
        from core.foundation.store import create_store
        st = create_store(prefer_redis=True)

        def bump(key, by):
            try:
                st.set(key, str(int(st.get(key) or 0) + by))
            except Exception:
                pass
        if layer == LAYERS[0][0]:
            bump("lookback:queries", 1)
        if kept:
            bump(f"lookback:hits:{layer}", kept)
    except Exception:
        pass
