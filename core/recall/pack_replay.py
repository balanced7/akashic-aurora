"""pack_replay (R2) -- replay the frozen census pack through TODAY's recall pipeline.

The reconciled slice-1 bar (kimi's counter-bar, adopted 2026-07-28) scores any
future silence gate against named case-sets from the frozen 30-case pack. This
module is the harness that does the scoring -- built BEFORE the gate exists, so:

  1. the BASELINE is measurable: how many shape-catchable NONE-NEEDED cases are
     already silent under the existing 0.20 floor, with no gate at all;
  2. any pre-existing violation surfaces now: an intersection-HIT or
     should-have-surfaced case that is ALREADY floor-silenced today is a live
     defect of the floor, and blaming it on a not-yet-written gate would be wrong
     in both directions;
  3. when the gate lands, its effect is a DIFF against this baseline, not an
     anecdote.

CAVEAT, stated where it cannot be missed: the corpus has evolved since the pack
was drawn (the judges saw the corpus of draw-time). A replay measures TODAY's
behaviour on those actions -- which is the right baseline for a gate that will
also run today, but it is NOT a re-judgment of the census. The case labels stay
frozen; only the pipeline's fire/silent verdict is live.

HERMETIC BY CONSTRUCTION: replay calls redirect the outcome sink to a scratch
dir before touching recall_at, so a 30-case replay never writes 30 fake rows
into the live denominator it exists to protect (the instrument must not pollute
the instrument).

Case-sets, verbatim from research/in-flight/r2-slice1-reconciled-bar-2026-07-28.md:
  SHAPE_CATCHABLE  {3,6,10,15,17,22,27}  gate targets (>=5 must be silent WITH a gate)
  INTERSECTION_HIT {4,18,24}             hard zero silenced, ever
  CONTESTED        {8,29}                silence unscored, logged with plane attribution
  case 9           the floor's business, explicitly not a gate target
  SHOULD_SURFACE   everything else       hard zero silenced by a GATE (floor may;
                                         the bar's clause 3 binds the gate, and the
                                         baseline shows what the floor already does)
"""
from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, List, Optional

PACK_PATH = os.path.join("research", "in-flight",
                         "demand-census-fresh-pack-seed2-2026-07-28.md")

SHAPE_CATCHABLE = {3, 6, 10, 15, 17, 22, 27}
INTERSECTION_HIT = {4, 18, 24}
CONTESTED = {8, 29}
FLOOR_BUSINESS = {9}

_CASE_RE = re.compile(r"^## case (\d+)\s+\[(command|path)\]", re.M)


def parse_pack(text: str) -> List[Dict[str, Any]]:
    """[{case, kind, action}] from the frozen pack. The ACTION line runs until the
    first surfaced-item slot (` N:a `) or the next case header."""
    out: List[Dict[str, Any]] = []
    matches = list(_CASE_RE.finditer(text))
    for i, m in enumerate(matches):
        block = text[m.end(): matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        am = re.search(r"^ACTION:\s*(.+?)(?=^\s*\d+:[a-z]\s|\Z)", block, re.M | re.S)
        action = " ".join((am.group(1) if am else "").split())
        out.append({"case": int(m.group(1)), "kind": m.group(2), "action": action})
    return out


def classify(case_no: int) -> str:
    if case_no in SHAPE_CATCHABLE:
        return "shape_catchable_none_needed"
    if case_no in INTERSECTION_HIT:
        return "intersection_hit"
    if case_no in CONTESTED:
        return "contested_plane"
    if case_no in FLOOR_BUSINESS:
        return "floor_business"
    return "should_surface"


def replay(pack_path: str = PACK_PATH, *, root: Optional[str] = None) -> Dict[str, Any]:
    """Run every pack case through recall_at with production settings; return per-case
    verdicts and the bar-relevant tallies. Read-only against the corpus; outcome rows
    go to a scratch sink."""
    from core.recall import at_action as A

    root = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(root, pack_path), encoding="utf-8") as f:
        cases = parse_pack(f.read())

    saved = A._OUTCOME_DIR
    A._OUTCOME_DIR = tempfile.mkdtemp(prefix="r2replay_")   # hermetic: never pollute the live sink
    rows: List[Dict[str, Any]] = []
    try:
        for c in cases:
            kw = {"command": c["action"]} if c["kind"] == "command" else {"path": c["action"]}
            r = A.recall_at(**kw)
            fired = bool(r.get("lessons"))
            rows.append({**c, "bucket": classify(c["case"]), "fired": fired,
                         "n_items": len(r.get("lessons") or []),
                         "error": r.get("error") or ""})
    finally:
        A._OUTCOME_DIR = saved

    def _tally(bucket: str) -> Dict[str, int]:
        sub = [r for r in rows if r["bucket"] == bucket]
        return {"cases": len(sub), "fired": sum(r["fired"] for r in sub),
                "silent": sum(not r["fired"] for r in sub)}

    return {
        "cases": rows,
        "tally": {b: _tally(b) for b in ("shape_catchable_none_needed", "intersection_hit",
                                         "contested_plane", "floor_business", "should_surface")},
        "errors": [r["case"] for r in rows if r["error"]],
    }


def render(result: Dict[str, Any]) -> str:
    lines = ["# R2 pack replay -- TODAY'S pipeline vs the reconciled bar's case-sets",
             "# (baseline: no gate exists; silence here is the existing floor's doing)"]
    for b, t in result["tally"].items():
        lines.append(f"  {b:28} cases={t['cases']:2}  fired={t['fired']:2}  silent={t['silent']:2}")
    hits_silent = [r["case"] for r in result["cases"]
                   if r["bucket"] == "intersection_hit" and not r["fired"]]
    if hits_silent:
        lines.append(f"  !! INTERSECTION-HIT ALREADY SILENT TODAY (floor defect, pre-gate): {hits_silent}")
    if result["errors"]:
        lines.append(f"  !! error_empty during replay (fix before trusting): {result['errors']}")
    for r in result["cases"]:
        mark = "FIRED " if r["fired"] else "silent"
        lines.append(f"    case {r['case']:2} [{r['kind']:7}] {mark} n={r['n_items']}  {r['bucket']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(replay()))
