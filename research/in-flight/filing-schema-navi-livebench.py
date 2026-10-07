"""NAVI half_b -- LIVE bench on the CURRENT tree (match_text already shipped, c217b608).
Drives recall_at exactly as cmd_recall_bench does (agent_cli.py:5624) and writes JSON."""
import json, os, sys, functools
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "research", "in-flight", "filing-schema-navi-livebench.json")

from core.recall import bench as _b
from core.recall.at_action import recall_at

meta = _b.load(None)
probe = functools.partial(recall_at, min_relevance=0.0)
d = _b.score(meta.get("moments") or [], recall_at, k=5, probe_fn=probe)
slim = {"recall_at_1": d["recall_at_1"], "recall_at_k": d["recall_at_k"],
        "hits1": sum(1 for r in d["rows"] if r["verdict"] == "HIT@1"),
        "hitsk": sum(1 for r in d["rows"] if r["verdict"] in ("HIT@1", "HIT@5")),
        "scored": d["scored"],
        "abstention": d["abstention"],
        "ceiling": {k2: d["ceiling"][k2] for k2 in
                    ("delivered", "rankable", "unmatchable", "unmatchable_ids", "rankable_ids")
                    if k2 in d["ceiling"]},
        "ambiguity_cap": (d["ceiling"].get("ambiguity") or {}).get("cap_at_1"),
        "rows": [{"id": r["id"], "verdict": r["verdict"], "expected": r.get("expected"),
                  "got": r.get("got")} for r in d["rows"]]}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(slim, f, indent=2, default=str)
print("WROTE", OUT, "hits1", slim["hits1"], "hitsk", slim["hitsk"],
      "unmatchable", slim["ceiling"].get("unmatchable_ids"))
