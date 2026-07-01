"""Dissent-finder (`core/recall`) — surface the strongest genuine COUNTER to a recalled lesson.

Semantic Relationship: Dissent surfaces a Counter that contradicts an ActiveKnowledge item

The pain this closes: recall ranks by similarity-to-the-current-action and boosts self-reported
successes, so it surfaces what AGREES with the plan — confirmation bias as a ranking function. This
finds the one lesson that most credibly DISAGREES with the top recalled lesson, so the agent sees a
position (thesis + its strongest live counter), not just a confirmation. Consumed by `recall_at`,
which surfaces one `counter:` line when a real counter clears the bar, and stays SILENT otherwise.

Design — deterministic, no-LLM, fail-soft, PRECISION-FIRST (evidence in docs/recall-critic-decision.md
+ the Slice-0 eval tests/test_counter_eval.py). Two experiments on the real corpus set the shape:

  1. A naive "shared tokens + opposite outcome" finder FLOODS — it flagged 81/90 successes as having a
     counter, all spurious generic-token collisions (two unrelated lessons sharing store/test/path).
     FIX: a **TF-IDF cosine topic-gate**. Weighting shared tokens by corpus rarity collapses the flood
     (spurious pairs score ~0.00–0.016) while keeping genuinely on-topic pairs — a plain rarity cutoff
     could not (it killed real counters at df<=5 yet still flooded at df<=8).

  2. Opposite OUTCOME != opposite STANCE. A `partial`/`no` lesson can carry advice that AGREES with a
     `yes` lesson (observed: a headless-failure lesson still recommending "use invisible mode", the
     same as the success). So surfacing on opposite-success alone manufactures FALSE BALANCE — a
     hallucinated disagreement, the exact failure this whole effort exists to avoid.
     FIX: a **stance signal is REQUIRED**. We fire only on an EXPLICIT declaration of opposition:
       (a) the candidate documents an `anti_pattern` (author-declared known-bad), or
       (b) an explicit contradicts/refutes relationship link.
     Opposite `success` is at most a weak corroborator (raises confidence when a stance already
     fired); it is NEVER a trigger on its own.

CONSEQUENCE (honest): on a corpus that is ~95% self-reported successes with 0 anti-patterns, this
surfaces almost nothing — which is correct (there is little real dissent to show) and is the evidence
that the next lever is the WRITE side (Slice 2: make agents record anti-patterns / contradicts-links),
not a cleverer reader. Deterministic lexical matching cannot detect semantically-phrased disagreement
(genuine conflicts often score cosine ~0.05, lexically invisible); that recall ceiling is deferred to
a later semantic tier, not faked here.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Generic English/dev tokens carry no topic signal and cause spurious collisions; never weigh them.
# (A stoplist can't fix DOMAIN-token collisions like store/test/path — that is why the gate is
# IDF-WEIGHTED cosine, not a token-count threshold: common tokens get near-zero weight by construction.)
_STOP = {"the", "and", "for", "with", "this", "that", "use", "using", "via", "from", "into", "not",
         "but", "than", "them", "they", "should", "must", "every", "each", "only", "same", "make",
         "here", "there", "also", "still", "like", "just", "then", "when", "what", "will", "been",
         "have", "does", "both", "else", "such", "more", "most", "very", "able", "keep", "gave",
         "over", "under", "onto", "need", "needs", "work", "works", "done", "next", "new", "old",
         "now", "per", "add", "adds", "set", "sets", "get", "gets", "run", "runs", "way", "ways"}

# Explicit "this refutes that" relationship-type labels (from the relationship-type vocabulary). Present
# for when the write-side (Slice 2) starts recording conflict links; harmless — just doesn't fire — until then.
_CONTRADICT_RELS = {"contradicts", "refutes", "conflicts_with", "contradicted_by", "refuted_by",
                    "disputes", "challenges"}

# Topic-gate bar. Empirically, generic-token collisions on the real corpus top out ~0.016; genuine
# on-topic pairs clear this comfortably. Start strict (precision-first); loosen only with eval evidence.
MIN_COSINE = 0.06


def _text_of(item: Dict[str, Any]) -> str:
    """The lesson's content for topic matching: the surfaced summary if present (recall items carry
    `text`), else the raw fields a lesson is summarized from (harness/store records carry these)."""
    if item.get("text"):
        return str(item["text"])
    return " ".join(str(item.get(f, "")) for f in ("recommendation", "actual", "what_tried") if item.get(f))


def _tokens(text: str) -> set:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 3 and t not in _STOP}


def document_frequencies(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Token -> number of items it appears in. The basis for IDF weighting. Cheap at this scale; bake
    it into the warm cache if the corpus grows to many thousands (see recall_at hot-path note)."""
    df: Dict[str, int] = {}
    for it in items:
        for w in _tokens(_text_of(it)):
            df[w] = df.get(w, 0) + 1
    return df


def _idf(df: Dict[str, int], n_docs: int) -> Dict[str, float]:
    # SMOOTHED idf: log((n+1)/(c+1)) + 1. Never zero, so it stays sane on tiny candidate pools (a
    # token shared across a 2-item pool would give plain idf=log(2/2)=0 and collapse the cosine);
    # still downweights common tokens (in-every-doc -> ~1) far below rare ones (topic-defining -> high).
    n = max(1, n_docs)
    return {w: math.log((n + 1) / (c + 1)) + 1.0 for w, c in df.items()}


def topic_cosine(a_tokens: set, b_tokens: set, idf: Dict[str, float]) -> float:
    """IDF-weighted (binary-TF) cosine between two token sets in [0,1]. Common tokens contribute
    ~nothing (low IDF), so it measures *topical* overlap, not generic-word coincidence."""
    shared = a_tokens & b_tokens
    if not shared:
        return 0.0
    num = sum(idf.get(w, 0.0) ** 2 for w in shared)
    na = math.sqrt(sum(idf.get(w, 0.0) ** 2 for w in a_tokens))
    nb = math.sqrt(sum(idf.get(w, 0.0) ** 2 for w in b_tokens))
    return num / (na * nb) if (na and nb) else 0.0


def _stance(cand: Dict[str, Any]) -> Optional[str]:
    """The REQUIRED explicit opposition signal on a candidate, or None. Never inferred from outcome."""
    if str(cand.get("anti_pattern", "")).strip():
        return "anti_pattern"                       # author-declared known-bad
    if str(cand.get("relationship_type", "")).lower() in _CONTRADICT_RELS:
        return "explicit_link"                      # author-declared contradiction
    return None


def find_counter(thesis: Dict[str, Any], candidates: Sequence[Dict[str, Any]], *,
                 idf: Optional[Dict[str, float]] = None, n_docs: Optional[int] = None,
                 min_cosine: float = MIN_COSINE) -> Optional[Dict[str, Any]]:
    """The strongest genuine counter to `thesis` among `candidates`, or None (silent).

    A candidate qualifies iff it carries an EXPLICIT stance signal (anti_pattern / contradicts-link)
    AND is topically related to the thesis (IDF-cosine >= min_cosine). Opposite `success` alone never
    qualifies (outcome != stance). Returns {source, text, kind, cosine} for the best, else None.
    Deterministic and fail-soft: any error -> None (a counter path must never brick recall)."""
    try:
        if not thesis:
            return None
        cands = [c for c in candidates if c.get("source") != thesis.get("source")]
        if idf is None:
            df = document_frequencies(list(cands) + [thesis])
            idf = _idf(df, n_docs if n_docs is not None else len(cands) + 1)
        t_tokens = _tokens(_text_of(thesis))
        best: Optional[Dict[str, Any]] = None
        for c in cands:
            stance = _stance(c)
            if not stance:
                continue                            # STANCE REQUIRED — never fire on topic/outcome alone
            cos = topic_cosine(t_tokens, _tokens(_text_of(c)), idf)
            if cos < min_cosine:
                continue                            # TOPIC gate — kill generic-token collisions
            # weak corroboration: an opposite recorded outcome nudges strength, but is never a trigger
            opposite = _opposite_outcome(thesis, c)
            strength = cos + (0.05 if opposite else 0.0)
            if best is None or strength > best["strength"]:
                best = {"source": c.get("source"), "text": _text_of(c), "kind": stance,
                        "cosine": round(cos, 3), "strength": round(strength, 3),
                        "corroborated_by_outcome": opposite}
        return best
    except Exception:
        return None


def _opposite_outcome(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    sa, sb = str(a.get("success", "")).lower(), str(b.get("success", "")).lower()
    win = {"yes", "true"}
    lose = {"no", "false", "partial"}
    return (sa in win and sb in lose) or (sa in lose and sb in win)
