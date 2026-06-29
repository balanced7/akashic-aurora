"""Faithfulness critic (FAITH-1) -- a deterministic, NO-LLM grounding gate for distillations.

Semantic Relationship: Distillation gated_by SourceGrounding (every claim traces to a real atom)

The seam already exists: `Distiller(critic=...)` and `chronicler._compute_metrics` (chapter-level).
This is the reusable, source-pointer-level critic that any consolidation (lessons, chronicle,
future Codex Resources) injects, so a projection that fabricates is caught before it's trusted.

SOTA, honestly applied (no LLM on a local box):
- LLM-as-judge is unreliable (self/position bias) and automated coherence is "broken" (Hoyle 2021)
  -> we judge deterministically, not with a model.
- RAGAS-style per-claim grounding is the right SHAPE; SummaC/FactCC entailment needs a model and
  errs on paraphrase/numbers -> we approximate per-line grounding with robust deterministic signals.
- Overlap/ROUGE is faithfulness-blind and gameable -> it is REPORTED (confidence), never the hard gate.

HARD gate (robust, ~0 false-positive on extractive output): every distilled line must
  (a) carry a source pointer that RESOLVES to a real input item, and
  (b) introduce no NUMBER/identifier absent from that cited source (fabricated figures are the worst lie).
SOFT signal (observed, not gated): token grounding overlap of the line to its cited source -- low
  overlap is flagged in notes + lowers `confidence`, but does NOT fail the verdict (legitimate
  paraphrase has low overlap; gating on it would block real knowledge -- the classic FP trap).

The heuristic Distiller writer copies each item's own text + source into the line, so faithfulness
is trivially 100% today -- this critic is the forward gate for an LLM writer that can mis-attribute.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.primitives.distiller import _SUMMARY_FIELDS, _source_of

# Line-final source capture (paren-safe: a source like learn:experiment:...(prior art) is whole).
_SOURCE_RE = re.compile(r"\(source:\s*(.+)\)\s*$")
_RELATES_RE = re.compile(r"\[relates:[^\]]*\]")
_NUM_RE = re.compile(r"\d[\d,.]*\d|\d")          # numbers/figures inside a line
_WORD_RE = re.compile(r"[a-z0-9_]+")
_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "it",
         "this", "that", "via", "use", "using", "from", "by", "at", "as", "be"}


def _words(s: str) -> set:
    return {w for w in _WORD_RE.findall((s or "").lower()) if len(w) > 2 and w not in _STOP}


def _source_text(items: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    """Map each input source -> its concatenated textual content (the same fields the Distiller
    summarizes from), so we can check a line's content/numbers against the record it cites."""
    out: Dict[str, str] = {}
    for it in items:
        src = _source_of(it)
        if not src:
            continue
        txt = " ".join(str(it.get(f, "")) for f in _SUMMARY_FIELDS if it.get(f))
        out[str(src)] = (out.get(str(src), "") + " " + txt).strip()
    return out


def faithfulness_report(items: Sequence[Dict[str, Any]], skeleton: str,
                        entries: Optional[Sequence[Dict[str, Any]]] = None,
                        *, grounding_tau: float = 0.5) -> Dict[str, Any]:
    """Deterministic per-line grounding check. Returns the full report (verdict + signals)."""
    src_text = _source_text(items)
    known = set(src_text)
    lines = [ln for ln in (skeleton or "").splitlines() if ln.strip()]
    untraceable = unresolved = number_fail = low_grounding = 0
    grounded_sum = 0.0
    per_line: List[Dict[str, Any]] = []
    for ln in lines:
        m = _SOURCE_RE.search(ln)
        if not m:                                    # a claim with no pointer can't be traced
            untraceable += 1
            per_line.append({"ok": False, "reason": "no source pointer"})
            continue
        src = m.group(1).strip()
        content = _RELATES_RE.sub("", ln[:m.start()]).lstrip("- ").strip()
        resolves = src in known
        cited = _words(src_text.get(src, ""))
        cw = _words(content)
        overlap = (len(cw & cited) / len(cw)) if cw else 1.0
        grounded_sum += overlap
        line_nums = set(_NUM_RE.findall(content))
        src_nums = set(_NUM_RE.findall(src_text.get(src, "")))
        nums_ok = line_nums.issubset(src_nums) if line_nums else True
        if not resolves:
            unresolved += 1
        if not nums_ok:
            number_fail += 1
        if resolves and overlap < grounding_tau:
            low_grounding += 1
        per_line.append({"src": src, "resolves": resolves, "overlap": round(overlap, 2),
                         "nums_ok": nums_ok, "ok": resolves and nums_ok})
    n = len(lines) or 1
    # HARD verdict: robust signals only (pointer resolves + no fabricated numbers + traceable).
    faithful = (untraceable == 0 and unresolved == 0 and number_fail == 0)
    return {
        "faithful": faithful,
        "confidence": round(grounded_sum / n, 3),    # SOFT: mean grounding overlap (observed)
        "lines": len(lines), "untraceable": untraceable, "unresolved": unresolved,
        "number_fail": number_fail, "low_grounding": low_grounding, "per_line": per_line,
    }


def faithfulness_critic(items: Sequence[Dict[str, Any]], skeleton: str,
                        entries: Optional[Sequence[Dict[str, Any]]] = None) -> Tuple[bool, List[str]]:
    """Distiller-critic adapter -> (ok, notes). HARD-gates fabricated/untraceable pointers + fabricated
    numbers; REPORTS low grounding without failing (paraphrase-safe, the FP trap)."""
    r = faithfulness_report(items, skeleton, entries)
    notes: List[str] = []
    if r["untraceable"]:
        notes.append(f"unfaithful: {r['untraceable']} claim(s) with no source pointer")
    if r["unresolved"]:
        notes.append(f"unfaithful: {r['unresolved']} fabricated/unresolvable source pointer(s)")
    if r["number_fail"]:
        notes.append(f"unfaithful: {r['number_fail']} line(s) cite a number absent from the source")
    if r["low_grounding"]:
        notes.append(f"observed: {r['low_grounding']} line(s) weakly grounded (paraphrase or drift)")
    if r["faithful"]:
        notes.append(f"faithful (grounding conf={r['confidence']})")
    return r["faithful"], notes
