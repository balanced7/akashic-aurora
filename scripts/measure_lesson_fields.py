"""What the lesson plane actually carries, and which of it anything reads.

WHY THIS IS IN THE REPO. Companion to `scripts/measure_target_join.py`, written for the same
reason: the 2026-10-03 knowledge-plane census produced the numbers under
`docs/THE-FILING-SCHEMA.md` with scripts in a session-scoped scratchpad, and when Heimdall
went to falsify one (`fences/filing-schema/half_a.md` V3) the commands were gone. Evidence in
scratch is evidence that expires. Anything a design leans on should be re-runnable by any
seat on any day.

WHAT IT ANSWERS

  1. FILL RATE per field, over the whole corpus. A field that exists and is empty on 97% of
     rows is not a usable axis, and that distinction is most of the finding.
  2. THE MATCH SURFACE: how many characters of lesson prose a query can actually reach,
     versus how many exist. Before 2026-10-02 `_project_items` kept the FIRST of
     (recommendation, actual, what_tried) and discarded the rest at the projection seam;
     `match_text` now spans all three while `text` stays the one provenance-tagged field the
     reader is shown. This prints both so the gap is visible rather than asserted.
  3. WHICH FIELD WINS the display slot, and how often. `what_tried` was carried by 1,533 rows
     and chosen on ZERO, because one of the other two always preceded it.
  4. READERS: for each field, whether anything under core/ actually reads it. A perfectly
     filled axis with no reader is the census's central finding and the one most likely to
     recur, so it is measured rather than remembered.

HONEST BOUNDS, stated because the census's failure was a claim outrunning its evidence:
this script covers the LESSON plane only. Three figures in the schema document remain
without a kept script and are therefore still UNVERIFIED by anyone but their original agent:
the 88.3% of refs not speaking the sealed vocabulary, the 0-of-110 verbs reaching the fence
plane, and the library-atom fill rates. They are named here so the gap is visible.

Read-only.

    py scripts/measure_lesson_fields.py [--json] [--top 24]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

TEXT_FIELDS = ("recommendation", "actual", "what_tried")
ALIASES = {"recommendation": ("recommendation", "recommend"),
           "actual": ("actual", "actual_outcome"),
           "what_tried": ("what_tried", "tried")}

# Fields worth a reader-check: the census found several perfectly filled and never read.
READER_CHECK = ("narrative_chapter", "narrative_track", "related_to", "files_affected",
                "domain", "anti_pattern", "root_cause", "confidence", "enforced_by")


def _get(rec: Dict[str, Any], canonical: str) -> str:
    d = rec.get("detail") if isinstance(rec.get("detail"), dict) else {}
    for k in ALIASES.get(canonical, (canonical,)):
        v = rec.get(k) or d.get(k)
        if v:
            return str(v)
    return ""


def _fields_of(rec: Dict[str, Any]) -> Dict[str, Any]:
    d = rec.get("detail") if isinstance(rec.get("detail"), dict) else {}
    out = dict(rec)
    out.pop("detail", None)
    out.update(d)
    return out


def _readers(field: str) -> List[str]:
    """Which files under core/ mention this field at all. A writer counts as a mention, so
    one hit usually means 'written and never read' -- the shape worth seeing."""
    try:
        r = subprocess.run(["git", "grep", "-l", field, "--", "core/"],
                           capture_output=True, text=True, cwd=_REPO, timeout=60)
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:                                                     # noqa: BLE001
        return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lesson-plane field utilisation")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=24)
    a = ap.parse_args(argv)

    from core.learning.learning_store import get_learning_store
    from core.recall import at_action as A

    recs = get_learning_store().load_all_learnings_from_store()
    n = len(recs)
    if not n:
        print("no lessons loaded -- is the store up?")
        return 2

    # ---- 1. fill rates ------------------------------------------------
    present: Counter = Counter()
    for rec in recs:
        for k, v in _fields_of(rec).items():
            if v not in (None, "", [], {}):
                present[k] += 1

    # ---- 2/3. the match surface and who wins the display slot ---------
    total_chars = seen_chars = 0
    chosen: Counter = Counter()
    carried: Counter = Counter()
    for rec in recs:
        vals = {f: _get(rec, f) for f in TEXT_FIELDS}
        for f in TEXT_FIELDS:
            if vals[f]:
                carried[f] += 1
        total_chars += sum(len(v) for v in vals.values())
        for f in TEXT_FIELDS:                       # the projector's own loop
            if vals[f]:
                chosen[f] += 1
                seen_chars += len(vals[f])
                break

    items = A._project_items(recs)
    match_chars = sum(len(str(i.get("match_text") or i.get("text") or "")) for i in items)
    shown_chars = sum(len(str(i.get("text") or "")) for i in items)

    rep: Dict[str, Any] = {
        "lessons": n,
        "display_slot_winner": dict(chosen),
        "rows_carrying": dict(carried),
        "chars_across_text_fields": total_chars,
        "chars_reachable_single_field": seen_chars,
        "projected_items": len(items),
        "chars_matchable_now": match_chars,
        "chars_displayed_now": shown_chars,
        "fill_rates": {k: [v, round(100.0 * v / n, 2)] for k, v in present.most_common()},
        "readers": {f: _readers(f) for f in READER_CHECK},
        "unverified_elsewhere": [
            "88.3% of refs not speaking the sealed eight-kind vocabulary",
            "0 of 110 verbs reaching the fence plane",
            "library-atom fill rates (1,019 atoms, category 99.0%)",
        ],
    }
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0

    print("lesson plane -- %d lessons\n" % n)
    print("THE DISPLAY SLOT (the projector keeps the FIRST non-empty of three):")
    for f in TEXT_FIELDS:
        print("   %-16s carried by %4d rows, wins the slot on %4d" % (f, carried[f], chosen[f]))
    if not chosen.get("what_tried"):
        print("   -> what_tried wins on ZERO rows: one of the other two always precedes it.")
    print()
    print("THE MATCH SURFACE:")
    print("   characters across the three text fields   %9d" % total_chars)
    print("   reachable if only ONE field is matched    %9d  (%.1f%% invisible)"
          % (seen_chars, 100.0 * (total_chars - seen_chars) / max(1, total_chars)))
    print("   matchable at HEAD (match_text)            %9d" % match_chars)
    print("   displayed at HEAD (text, provenance-tagged) %7d" % shown_chars)
    print()
    print("FILL RATES, top %d:" % a.top)
    for k, v in present.most_common(a.top):
        print("   %-26s %5d  %6.2f%%" % (k, v, 100.0 * v / n))
    print()
    print("READERS under core/ (a writer counts as a mention -- ONE hit usually means")
    print("written-and-never-read, which is the shape worth seeing):")
    for f in READER_CHECK:
        rs = rep["readers"][f]
        note = "  <-- no reader but its writer" if len(rs) == 1 else ""
        print("   %-20s %d file(s)%s" % (f, len(rs), note))
        if len(rs) == 1:
            print("        %s" % rs[0])
    print()
    print("NOT COVERED BY THIS SCRIPT, and therefore still unverified by a kept command:")
    for s in rep["unverified_elsewhere"]:
        print("   - %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
