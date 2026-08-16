"""The stale-claim detector: a lesson's ANCHORS can resolve while its CLAIM has gone false.

THE RECEIPT THAT BUILT THIS, 2026-08-16. A blind-half study cited
`the_oldest_wish_was_never_filed_as_one`, whose finding reads "WISHLIST holds 130 open wishes
and NOT ONE is about naming coherence". Every anchor resolved. The wishlist exists, the
citations are real, the lesson is honest and was true when written. It had been false for
nine days: W133 was filed 2026-08-07 by the same session that wrote the lesson. On the
strength of a citation that checked out, I nearly re-filed the operator's oldest wish.

THE GAP, named by deepseek in July and unbuilt until now
(research:web:build_system_and_tms_invalidation): the anchor resolver answers "does this
source EXIST?" It has never answered "does this source still SUPPORT the claim?" -- RAG
CiteCheck's second dimension, which that research flagged as the tier-4 problem we do not
attempt. From the same research, JTMS supplies the discipline: a belief stands while at
least one justification stands, so age alone is not suspicion. Only moved evidence is.

DELIBERATELY NARROW. This checks ONE shape: claims of COUNT or ABSENCE over a named artifact
-- "not one is X", "zero entries", "nothing cites Y", "no guard exists". Those are
mechanically re-checkable at HEAD. Judgement claims are not, and pretending otherwise builds
a detector that fires on opinions and gets muted within a week (the wolf-guard law: an
ignored instrument's silence reads as all-clear, which is worse than no instrument).

AND IT PROPOSES, NEVER RATIFIES. There is no write path here: it does not retract, bench, or
edit a lesson. It surfaces "this claim deserves a re-read, and here is the line that seems to
refute it" -- a human decides. Five independent arrivals in this house landed on that law.

THE HONEST DIRECTION OF ITS ERRORS: an unreachable artifact returns UNCHECKABLE, never
"stale". Absence of evidence is not evidence of staleness -- the confident-zero disease in
detector form.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Shapes that assert a NEGATIVE about a named artifact. Each pattern must capture enough to
# name the artifact, because a claim we cannot re-locate is not checkable -- it is a rumour.
_ABSENCE_PATTERNS = [
    re.compile(r"\b(?P<artifact>[A-Z][A-Za-z_./]{2,40}(?:\.md|\.py|\.json)?)\s+holds?\s+"
               r"\d[\d,]*\s+[a-z ]{0,30}?and\s+(?:not one|none|zero)\b", re.I),
    re.compile(r"\b(?:not one|none|zero|no)\s+(?:open\s+)?(?P<noun>[a-z]{3,20})s?\s+"
               r"(?:in|of|under)\s+(?P<artifact>[A-Za-z_./]{3,60})", re.I),
    re.compile(r"\b(?P<artifact>[A-Za-z_./]{3,60}\.(?:md|py|json))\s+(?:has|holds|contains)"
               r"\s+(?:no|zero)\b", re.I),
]

# Words that mark a sentence as judgement rather than fact-about-an-artifact. Their presence
# disqualifies the sentence even if a pattern matches -- precision over recall, on purpose.
_JUDGEMENT = ("skill", "rather than", "most people", "i think", "seems", "feels",
              "probably", "arguably", "better than", "worse than")


def extract_checkable_claims(text: str) -> List[Dict[str, Any]]:
    """Locate count/absence claims that name an artifact. Judgement is left alone."""
    out: List[Dict[str, Any]] = []
    for raw in re.split(r"(?<=[.!?])\s+|--\s+|\n", str(text or "")):
        s = " ".join(raw.split())
        if len(s) < 12:
            continue
        low = s.lower()
        if any(j in low for j in _JUDGEMENT):
            continue
        for pat in _ABSENCE_PATTERNS:
            m = pat.search(s)
            if not m:
                continue
            gd = m.groupdict()
            artifact = (gd.get("artifact") or "").strip(" .,")
            if not artifact:
                continue
            # the needle is the thing claimed absent: the trailing subject of the clause
            tail = s[m.end():].strip(" -.,")
            needle = " ".join(tail.split()[:4]) or (gd.get("noun") or "")
            out.append({
                "kind": "absence",
                "artifact": artifact,
                "needle": needle,
                "quote": s[:200],
            })
            break
    return out


def _resolve_artifact(artifact: str) -> Optional[Path]:
    """Map a claim's artifact name onto a real file at HEAD, or None."""
    a = str(artifact or "").strip()
    if not a:
        return None
    direct = _REPO_ROOT / a
    if direct.is_file():
        return direct
    stem = a.split("/")[-1]
    if not stem.endswith((".md", ".py", ".json")):
        stem += ".md"
    for base in ("docs", ".", "state", "research"):
        p = _REPO_ROOT / base / stem
        if p.is_file():
            return p
    hits = list(_REPO_ROOT.glob(f"**/{stem}"))
    return hits[0] if len(hits) == 1 else None


def recheck_claim(claim: Dict[str, Any]) -> Dict[str, Any]:
    """Re-read the artifact and ask whether the absence still holds.

    Three outcomes, never two: still_holds True/False when checked, and None with
    checked=False when the artifact cannot be reached. UNKNOWN IS NOT FALSE."""
    artifact = str(claim.get("artifact", ""))
    needle = " ".join(str(claim.get("needle", "")).lower().split())
    path = _resolve_artifact(artifact)
    if path is None:
        return {"checked": False, "still_holds": None, "evidence": "",
                "why": f"artifact {artifact!r} is unreachable at HEAD -- unevaluable, "
                       "which is not the same as refuted"}
    if not needle:
        return {"checked": False, "still_holds": None, "evidence": "",
                "why": "the claim names no needle to search for"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:                                   # pragma: no cover - io guard
        return {"checked": False, "still_holds": None, "evidence": "",
                "why": f"could not read {path.name}: {e}"}

    words = [w for w in re.findall(r"[a-z0-9]+", needle) if len(w) > 3]
    hits: List[str] = []
    for line in text.splitlines():
        low = line.lower()
        if words and all(w in low for w in words):
            hits.append(" ".join(line.split())[:180])
        if len(hits) >= 3:
            break
    if hits:
        return {"checked": True, "still_holds": False, "evidence": hits,
                "why": f"the claimed-absent subject appears in {path.name} -- the absence "
                       "claim no longer holds; re-read the lesson before citing it"}
    return {"checked": True, "still_holds": True, "evidence": [],
            "why": f"searched {path.name} at HEAD; the subject is still absent"}


def sweep(limit: int = 50, corpus: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Read the lesson corpus, extract checkable claims, re-check them, report.

    The report carries its own frame: how many lessons were examined, how many held a
    checkable claim at all, and what was NOT looked at. A count without its scope is not a
    coverage claim."""
    rows = corpus
    source = "caller-supplied corpus"
    if rows is None:
        # THE POPULATION, checked rather than assumed. The first build read
        # session_logs/learnings.jsonl and reported a confident 0 stale from SIX records --
        # that file is a June-20 legacy stub, while the live corpus is the LearningStore
        # (942 records). A detector aimed at the wrong population returns a clean bill that
        # means nothing (ask_the_detector_for_its_POPULATION_not_only_its_predicate).
        try:
            from core.learning.learning_store import get_learning_store_instance
            rows = get_learning_store_instance().get_all_learnings()
            source = "LearningStore.get_all_learnings()"
        except Exception as e:                               # pragma: no cover - io guard
            return {"examined": 0, "checkable": 0, "stale": [],
                    "scope": f"UNREACHABLE: could not read the lesson store ({e}) -- this "
                             "is not a clean bill, it is a failure to look"}
    rows = list(rows)
    total = len(rows)
    rows = rows[-int(limit):] if limit else rows

    examined = checkable = 0
    stale: List[Dict[str, Any]] = []
    for r in rows:
        examined += 1
        blob = " ".join(str(r.get(f, "")) for f in
                        ("actual", "recommendation", "what_tried", "result"))
        for claim in extract_checkable_claims(blob):
            checkable += 1
            v = recheck_claim(claim)
            if v["checked"] and v["still_holds"] is False:
                stale.append({
                    "lesson": r.get("experiment_name") or r.get("source") or "?",
                    "claim": claim["quote"],
                    "artifact": claim["artifact"],
                    "evidence": v["evidence"],
                    "why": v["why"],
                })
    return {
        "examined": examined,
        "checkable": checkable,
        "stale": stale,
        "population": total,
        "source": source,
        "scope": (f"{examined} of {total} lesson record(s) from {source}; count/absence "
                  "claims only -- judgement claims are out of scope by design, and "
                  "unreachable artifacts report UNCHECKABLE, never stale"),
    }
