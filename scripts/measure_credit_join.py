"""Measure how much of the credit sensor's blindness the COARSE JOIN AXIS recovers.

COMPANION TO scripts/measure_target_join.py, and a different question. That script asks
whether the outcome plane and the TOUCH plane can meet at all. This one stays inside the
outcome plane and asks the question the credit loop actually turns on:

    when an action FAILED, could any later SUCCESS in the same session ever join it?

That join is what makes a lesson creditable. `normalize_target` keys a command on its
whole literal string, so the answer for commands was structurally almost always no -- a
fixed command is a different string from the broken one it replaced. 17,606 of 18,024
distinct keys on this stream are commands.

WHAT IS COMPARED, per session, in stream order:

  EXACT   a FAIL at key K is joinable if some LATER row has key K and ok=True.
          This is the sensor as it behaved before 0c51836b.
  COARSE  a FAIL is joinable if some LATER row has the same non-empty
          `coarse_target` and ok=True. This is the sensor after it.

THIS IS A COUNTERFACTUAL AND THE NUMBER MUST BE READ AS ONE. Every row on this stream was
written by the OLD code, so no coarse key was ever stored; the script RECOMPUTES the
coarse key from each row's recorded target to ask what WOULD have been joinable. It cannot
prove any of those joins would have credited a lesson, because credit also needs an
impression for that target -- so the `surfaced` column is reported separately and is the
honest upper bound on realised credit, while the joinable column is the upper bound on
observability.

It also reports the share of newly-joinable failures whose join is COARSE-ONLY, because
that is exactly the population where a false join can mint false credit (the reason every
credit now records which axis won it).

Read-only: xrange replays, no cursor is advanced, nothing is written.

    py scripts/measure_credit_join.py [--limit 50000] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

OUTCOME_STREAM = "recall:outcome"


def _rows(limit: int) -> List[dict]:
    """Replay the outcome stream oldest-first. Never consumes."""
    from core.comm.bus import Bus
    client = Bus("claude")._client
    out: List[dict] = []
    for _mid, fields in client.xrange(OUTCOME_STREAM, min="-", max="+", count=limit):
        try:
            raw = next(iter(fields.values()))
            out.append(json.loads(raw.decode() if isinstance(raw, bytes) else str(raw)))
        except Exception:                                                 # noqa: BLE001
            continue
    return out


def measure(limit: int) -> Dict[str, Any]:
    from core.recall.at_action import coarse_target

    rows = _rows(limit)
    by_sid: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_sid[str(r.get("sid") or "?")].append(r)

    stats: Counter = Counter()
    axis_examples: List[Dict[str, str]] = []

    for _sid, srows in by_sid.items():
        # Later-success index: which keys (exact and coarse) succeed at or after each point.
        # Walk backwards once so "is there a LATER success" is O(n) rather than O(n^2).
        later_exact, later_coarse = set(), set()
        suffix = []
        for r in reversed(srows):
            suffix.append((r, set(later_exact), set(later_coarse)))
            if r.get("ok"):
                t = str(r.get("t") or "")
                later_exact.add(t)
                c = coarse_target(t)
                if c:
                    later_coarse.add(c)
        for r, exact_after, coarse_after in reversed(suffix):
            if r.get("ok"):
                continue                                   # only FAILs can open a flip
            t = str(r.get("t") or "")
            stats["fails"] += 1
            is_cmd = t.startswith("c:")
            stats["fails_command" if is_cmd else "fails_path"] += 1
            c = coarse_target(t)
            if not c:
                stats["fails_without_coarse_axis"] += 1
            joins_exact = t in exact_after
            joins_coarse = bool(c) and c in coarse_after
            if joins_exact:
                stats["joinable_exact"] += 1
            if joins_exact or joins_coarse:
                stats["joinable_either"] += 1
                if r.get("surfaced"):
                    stats["joinable_either_surfaced"] += 1
            if joins_coarse and not joins_exact:
                stats["joinable_coarse_only"] += 1
                if r.get("surfaced"):
                    stats["joinable_coarse_only_surfaced"] += 1
                if len(axis_examples) < 8:
                    axis_examples.append({"fail_target": t[:120], "coarse_key": c[:120]})

    fails = stats["fails"] or 1
    return {
        "outcome_rows_replayed": len(rows),
        "sessions": len(by_sid),
        "fails": stats["fails"],
        "fails_command": stats["fails_command"],
        "fails_path": stats["fails_path"],
        "fails_without_coarse_axis": stats["fails_without_coarse_axis"],
        "joinable_exact": stats["joinable_exact"],
        "joinable_either": stats["joinable_either"],
        "joinable_coarse_only": stats["joinable_coarse_only"],
        "joinable_either_surfaced": stats["joinable_either_surfaced"],
        "joinable_coarse_only_surfaced": stats["joinable_coarse_only_surfaced"],
        "pct_joinable_before": round(100.0 * stats["joinable_exact"] / fails, 2),
        "pct_joinable_after": round(100.0 * stats["joinable_either"] / fails, 2),
        "coarse_only_share_of_joinable": round(
            100.0 * stats["joinable_coarse_only"] / (stats["joinable_either"] or 1), 2),
        "coarse_only_examples": axis_examples,
        "_reading": "COUNTERFACTUAL: rows were written before the coarse axis existed; "
                    "joinable is an upper bound on OBSERVABILITY, and the _surfaced "
                    "variants are the upper bound on realised CREDIT.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=50000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    res = measure(args.limit)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print(f"outcome rows replayed : {res['outcome_rows_replayed']} over {res['sessions']} session(s)")
    print(f"failures              : {res['fails']}  "
          f"({res['fails_command']} command, {res['fails_path']} path)")
    print(f"  no coarse axis      : {res['fails_without_coarse_axis']}  "
          f"(refused: identity lived in the flags)")
    print(f"joinable BEFORE       : {res['joinable_exact']}  ({res['pct_joinable_before']}%)")
    print(f"joinable AFTER        : {res['joinable_either']}  ({res['pct_joinable_after']}%)")
    print(f"  coarse-only         : {res['joinable_coarse_only']}  "
          f"({res['coarse_only_share_of_joinable']}% of all joinable)")
    print(f"  ...with a lesson up : {res['joinable_coarse_only_surfaced']}  "
          f"(the creditable subset)")
    print(f"\n{res['_reading']}")
    if res["coarse_only_examples"]:
        print("\ncoarse-only examples (audit these: each is a place a FALSE join could mint credit)")
        for e in res["coarse_only_examples"]:
            print(f"  {e['fail_target']}\n    -> {e['coarse_key']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
