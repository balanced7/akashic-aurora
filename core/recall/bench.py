"""W0.3 -- recall-bench: the first number recall has ever been judged on.

SPEC: W0.3 of `fences/context-system/reconciliation.md` section 4 -- "40 blind moments with a known
      right lesson; `py agent_cli.py recall-bench` prints recall@5, precision@3, chrome share, and
      the baseline number is committed with the set". Navi adjudicates the answer set blind.
SET:  `tests/fixtures/recall_eval/moments.json`.

WHY A BENCH AT ALL. The reach map's measurement: the manuals shelf shipped with 40 blind questions
and a number; recall shipped with a funnel. A funnel counts what was SURFACED, which is volume, not
quality -- 23,333 surfacings and 532 ever judged. Nothing in this house has ever been able to answer
"did the right thing arrive at the right moment", and until something can, every change to recall is
a matter of taste.

WHAT A MOMENT IS, and why it is not a query. A query asks "what do you know about X". A moment is a
situation an agent was actually IN, with the lesson that would have prevented what happened next.
The 2026-08-08 dossier's sharpest finding is that retrieval is not the problem: querying the store
directly returns the right lesson FIRST almost every time. The failure is in WHEN, not WHAT. So the
bench drives the real trigger (path, command) and never the query, because keying on the query would
measure the half that already works.

THE TWO CASES THAT MAKE IT AN EVAL RATHER THAN A DEMO.
  - UNRESOLVED: a moment whose ground truth cannot be established is EXCLUDED and counted, never
    pointed at the nearest plausible lesson. An answer key filled in by guessing measures the
    guesser.
  - ABSTAIN: a moment where the right answer is SILENCE. Without one, a bench rewards a surface that
    always speaks, and "it fired something" becomes indistinguishable from "it was right". The
    dossier's M4 is this case and it was discovered as a positive control that turned out to be a
    miss: a correct match on TOPIC can be a total miss on MOMENT.

PRECISION IS REPORTED AS UNCHECKABLE, DELIBERATELY. precision@3 needs a relevance label for every
returned item, and the set carries one label per moment (the right lesson). Computing "precision"
from that would really be measuring recall@3 under another name, and a number with the wrong name
is worse than no number because it gets compared to other people's precision. It becomes checkable
when moments carry a labelled relevant-set, which is a job for whoever writes the remaining 36.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Sequence

UNCHECKABLE = "UNCHECKABLE"
SCHEMA = "recall_eval.v1"


def load(path: Optional[str] = None) -> Dict[str, Any]:
    p = path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "tests", "fixtures", "recall_eval", "moments.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("schema") != SCHEMA:
        raise ValueError(f"{p}: expected schema {SCHEMA!r}, got {d.get('schema')!r}")
    return d


def score(moments: Sequence[Dict[str, Any]], recall_fn: Callable[..., Dict[str, Any]],
          *, k: int = 5) -> Dict[str, Any]:
    """Drive the real trigger for each moment and grade what came back."""
    hits_at_1 = hits_at_k = scored = 0
    abstain_total = abstain_ok = 0
    excluded: List[str] = []
    rows: List[Dict[str, Any]] = []
    chrome_chars = body_chars = 0

    for m in moments:
        mid = str(m.get("id") or "?")
        expect = str(m.get("expect") or "")
        trig = m.get("trigger") or {}
        res = recall_fn(path=trig.get("path"), command=trig.get("command"), limit=k) or {}
        got = [str(x.get("source") or "") for x in (res.get("lessons") or [])]

        # Chrome is everything pushed that is not a lesson body. The reach map measured verb
        # blurbs at 14% of pushed text, and a surface that is mostly chrome trains its reader to
        # skim -- which costs the true positives too.
        body_chars += sum(len(str(x.get("text") or "")) for x in (res.get("lessons") or []))
        chrome_chars += sum(len(str(v)) for v in (res.get("verbs") or []))

        if expect == "UNRESOLVED":
            excluded.append(mid)
            rows.append({"id": mid, "verdict": "EXCLUDED", "why": "ground truth unresolved",
                         "got": got[:k]})
            continue

        if expect == "ABSTAIN":
            abstain_total += 1
            ok = not got                      # silence is the right answer; anything is a false hit
            abstain_ok += 1 if ok else 0
            rows.append({"id": mid, "verdict": "ABSTAIN-OK" if ok else "SPOKE-WHEN-SILENT",
                         "got": got[:k]})
            continue

        accept = {expect, *(m.get("also_acceptable") or [])}
        scored += 1
        at1 = bool(got[:1]) and got[0] in accept
        atk = any(g in accept for g in got[:k])
        hits_at_1 += 1 if at1 else 0
        hits_at_k += 1 if atk else 0
        rows.append({"id": mid, "verdict": "HIT@1" if at1 else ("HIT@%d" % k if atk else "MISS"),
                     "expected": expect, "got": got[:k]})

    pushed = chrome_chars + body_chars
    return {
        "k": k,
        "scored": scored,
        "recall_at_1": (hits_at_1 / scored) if scored else None,
        "recall_at_k": (hits_at_k / scored) if scored else None,
        # Named rather than invented -- see the module docstring.
        "precision_at_3": UNCHECKABLE,
        "precision_why": ("the set carries one labelled right answer per moment, not a labelled "
                          "relevant-set, so any 'precision' computed here would be recall@3 under "
                          "another name"),
        "abstention": {"total": abstain_total, "correct": abstain_ok,
                       "rate": (abstain_ok / abstain_total) if abstain_total else None},
        "excluded": excluded,
        "chrome_share": (chrome_chars / pushed) if pushed else None,
        "rows": rows,
    }


def render(d: Dict[str, Any], meta: Dict[str, Any]) -> str:
    def pct(v):
        return f"{v:.0%}" if isinstance(v, float) else "UNKNOWN (nothing scored)"
    out = [
        f"recall-bench   set: {meta.get('seeded')}/{meta.get('target')} moments seeded",
        "",
        f"  RECALL@1          {pct(d['recall_at_1'])}   ({d['scored']} scored)",
        f"  RECALL@{d['k']}          {pct(d['recall_at_k'])}",
        f"  ABSTENTION        {d['abstention']['correct']}/{d['abstention']['total']} "
        f"({pct(d['abstention']['rate'])})   silence when silence was right",
        f"  CHROME SHARE      {pct(d['chrome_share'])}   of pushed characters that are not a lesson",
        f"  PRECISION@3       {UNCHECKABLE}",
        f"                      {d['precision_why']}",
        "",
        "  PER MOMENT:",
    ]
    for r in d["rows"]:
        out.append(f"    {r['id']:<4} {r['verdict']:<18} {r.get('why') or r.get('expected') or ''}")
        for g in (r.get("got") or [])[:3]:
            out.append(f"           got: {g}")
        if not r.get("got"):
            out.append("           got: (nothing)")
    if meta.get("why_not_forty_yet"):
        out += ["", "  WHY THE SET IS NOT YET 40:", "    " + meta["why_not_forty_yet"]]
    return "\n".join(out)
