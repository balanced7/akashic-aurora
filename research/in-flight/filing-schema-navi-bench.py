"""NAVI fence half_b -- hermetic LEXICAL-PROXY experiment (control vs treatment match surface).

IMPORTANT: this script was written before the discovery that the match_text fix had ALREADY
shipped on the measured tree (working-tree at_action.py carries it; pin test
tests/test_match_surface_spans_every_text_field.py is green; commit c217b608 was pins-only,
so the impl landed uncommitted). Its control arm (single-field) is therefore a PROXY for the
pre-fix engine, NOT the live engine, and its treatment numbers must not be compared to the
live run in filing-schema-navi-livebench.json (different IDF/dampener/trigger blend/floor/
faithfulness). The CLEAN instrument of record is the live bench: pre-fix keys from
tests/fixtures/recall_eval/moments.json why_not_forty_yet vs post-fix run. Kept for the
falsification re-measure in `stats` and the field_probe mechanism data, both of which stand.
"""
import json, os, sys, re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "research", "in-flight", "filing-schema-navi-bench-out.json")

from core.recall import bench as _b
from core.learning.learning_store import get_learning_store
import core.recall.at_action as aa


def frozen_items():
    recs = get_learning_store().load_all_learnings_from_store()
    return recs, aa._project_items(recs)


def field_choice(rec):
    for f in ("recommendation", "actual", "what_tried"):
        if rec.get(f):
            return f
    return ""


def toks(s):
    return set(re.findall(r"[a-z0-9_]+", (s or "").lower()))


def main():
    recs, items = frozen_items()

    # --- falsification of brief numbers #1/#2, re-measured from the store itself
    fc = Counter(field_choice(r) for r in recs)
    present = {f: sum(1 for r in recs if r.get(f)) for f in ("recommendation", "actual", "what_tried")}
    proj = [i for i in items]  # after graduated/benched filtering
    total = matched = 0
    for r in recs:
        f = field_choice(r)
        for name in ("recommendation", "actual", "what_tried"):
            v = r.get(name) or ""
            total += len(v)
            if name == f:
                matched += len(v)
    stats = {"rows": len(recs), "projected": len(proj), "field_choice": dict(fc),
             "present": present, "chars_total": total, "chars_matched": matched,
             "chars_unmatched": total - matched,
             "pct_unmatched": round(100 * (total - matched) / total, 1) if total else None}

    meta = _b.load(None)
    moments = meta["moments"]

    # freeze control display text and provenance field per lesson source
    base = {}
    for it in proj:
        src = it.get("source")
        if src and src not in base:
            base[src] = {"text": str(it.get("text") or ""), "field": str(it.get("field") or "")}
    # treatment match surface: concat of all three fields, keyed by source
    wide = {}
    for r in recs:
        src = f"learn:experiment:{r.get('experiment_name')}"
        if src in base and src not in wide:
            wide[src] = " ".join(str(r.get(f) or "") for f in ("recommendation", "actual", "what_tried"))

    def trigger_tokens(trig):
        out = set()
        for v in (trig.get("path") or "", trig.get("command") or ""):
            out |= toks(os.path.basename(str(v)))
            out |= toks(str(v))
        out -= {"py", "python", "grep", "scripts", "core", "tests", "test"}
        return out

    def rank(trig, match_map, limit):
        tt = trigger_tokens(trig)
        scored = []
        for src, mtext in match_map.items():
            inter = len(tt & toks(mtext))
            if inter:
                scored.append((inter, len(toks(mtext)), src))
        # highest overlap first; ties broken by shorter text then name for determinism
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        return [{"source": s, "text": base[s]["text"]} for _, _, s in scored[:limit]]

    control = {s: base[s]["text"] for s in base}
    treatment = {s: wide.get(s) or base[s]["text"] for s in base}

    def make_fn(match_map):
        return lambda path=None, command=None, limit=5: {
            "lessons": rank({"path": path, "command": command}, match_map, limit)}

    res = {}
    for name, mm in (("control_single_field", control), ("treatment_all_three", treatment)):
        fn = make_fn(mm)
        probe = make_fn(mm)
        d = _b.score(moments, fn, k=5, probe_fn=probe)
        res[name] = {"recall_at_1": d["recall_at_1"], "recall_at_k": d["recall_at_k"],
                     "hits1": sum(1 for r in d["rows"] if r["verdict"] == "HIT@1"),
                     "hitsk": sum(1 for r in d["rows"] if r["verdict"] in ("HIT@1", "HIT@5")),
                     "scored": d["scored"],
                     "ceiling": {k2: d["ceiling"][k2] for k2 in
                                 ("delivered", "rankable", "unmatchable", "unmatchable_ids",
                                  "rankable_ids", "cap_at_1", "best_possible_at_1") if k2 in d["ceiling"]},
                     "ceiling_amb": (d["ceiling"].get("ambiguity") or {}).get("cap_at_1"),
                     "rows": [{"id": r["id"], "verdict": r["verdict"],
                               "expected": r.get("expected"), "got": r.get("got")} for r in d["rows"]]}

    # mechanism probe: for each scored moment, which FIELD holds the winning tokens under treatment
    field_probe = {}
    name2src = {f"learn:experiment:{r.get('experiment_name')}": r for r in recs}
    for m in moments:
        exp = m.get("expect")
        if exp in (None, "UNRESOLVED", "ABSTAIN"):
            continue
        r = name2src.get(exp)
        if not r:
            field_probe[m["id"]] = "expected-lesson-not-in-store"
            continue
        tt = trigger_tokens(m.get("trigger") or {})
        overlaps = {f: len(tt & toks(r.get(f) or "")) for f in ("recommendation", "actual", "what_tried")}
        chosen = field_choice(r)
        field_probe[m["id"]] = {"chosen_field": chosen, "overlap_by_field": overlaps}

    out = {"stats": stats, "results": res, "field_probe": field_probe,
           "note": "LEXICAL PROXY for the live ranker: corpus frozen from production _project_items; "
                   "only the match surface varies. Counts, not percentages (n=18 scored)."}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
