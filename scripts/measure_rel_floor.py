"""Score the RELATIVE FLOOR against the absolute one, both arms, on the recall bench.

THE EXPERIMENT. `_lessons` (core/recall/at_action.py) keeps a lesson when its relevance
clears an absolute floor, default 0.20, calibrated 2026-07-08 against historical credits.
The proposal under test is a per-query SHAPE statistic instead:

    cut = max(abs_floor, best_relevance_in_this_call * ratio)

armed by AKASHIC_RECALL_REL_FLOOR (0 = off, the shipped default). `max()` means it can only
ever be STRICTER than the calibrated floor, so arming it cannot un-silence a call.

WHY THIS FILE IS IN THE REPO. Pre-registered as forecast F-relfloor-2026-10-06, and the
forecast door REFUSES a scratchpad path as evidence -- it derives when an outcome became
knowable from the artifact, and a session-scoped scratch file cannot carry that. Same rule
that produced scripts/measure_target_join.py: evidence in scratch is evidence that expires.
Anyone can re-derive every number below with one command.

RESULT, 2026-10-06, committed set (18 scored moments):

    ratio   recall@1   recall@5   abstention
    0 (off) 5/18       10/18      0/6
    0.5     5/18       10/18      0/6     <- the pre-registered value: nothing moves
    0.8     6/18       10/18      0/6
    0.95    6/18       10/18      0/6
    0.999   6/18       10/18      0/6

ONE moment changes across the whole sweep: N21, HIT@5 -> HIT@1. One moment on 18 is not
evidence of improvement, and tuning the ratio until it appears is fitting a threshold to
the labels already in hand -- which is why the prediction was committed first.

TWO FINDINGS WORTH MORE THAN THE TABLE:

1. A RELEVANCE FLOOR CAN REORDER BY REMOVAL. The pre-registered mechanism said a floor can
   only remove, never promote. Wrong: the final sort is score*usefulness_factor while the
   floor cuts on RELEVANCE, so dropping a high-score/low-relevance item promotes whatever
   sat behind it. Whenever a filter and a sort disagree about their key, filtering reorders.

2. NO FLOOR OF ANY TIGHTNESS CAN BUY ABSTENTION. 0 of 6 at every ratio including 0.999,
   where only the single best-scoring item can survive -- and the engine still speaks. The
   engine ALWAYS has a top item, so "should I speak at all" is not a function of relative
   relevance. The 6 SPOKE-WHEN-SILENT moments need a mechanism outside this axis entirely.

A NOTE ON INSTRUMENTS. The first run of this sweep reported no change at any ratio,
including 0.999, which is impossible if the knob is live. Cause: the harness built a
subprocess env dict and never passed env= to subprocess.run. Identical-before-and-after is
a question about the instrument before it is a finding about the subject, so this script
CALIBRATES itself first (--calibrate, run by default) by proving the child process reads
the ratio it was given, and refuses to report numbers if it does not.

    py scripts/measure_rel_floor.py [--set PATH] [--ratios 0,0.5,0.8] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KNOB = "AKASHIC_RECALL_REL_FLOOR"


def _child_env(ratio: str) -> Dict[str, str]:
    """A fresh env per arm. PYTHONPYCACHEPREFIX is per-ratio so no arm can read another's
    bytecode: a fresh process is not a fresh import, and the cache key is (mtime, size)."""
    env = dict(os.environ)
    env[_KNOB] = str(ratio)
    env["PYTHONPYCACHEPREFIX"] = os.path.join(
        env.get("TEMP") or env.get("TMP") or ".", "pycache_relfloor_" + str(ratio).replace(".", "_"))
    return env


def calibrate() -> bool:
    """Prove the knob reaches the child. Without this, a dead knob reads as a null result."""
    probe = ("from core.recall.at_action import _rel_floor_ratio as r; print(r())")
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", probe], cwd=_REPO,
                       env=_child_env("0.777"), capture_output=True, text=True,
                       errors="replace", timeout=120)
    got = (r.stdout or "").strip()
    ok = got.startswith("0.777")
    print("calibration: child reads ratio %s -- %s" % (got or "(nothing)", "OK" if ok else "FAILED"))
    if not ok:
        print("  REFUSING to report numbers: the arms would be indistinguishable.")
        if r.stderr:
            print("  stderr: " + r.stderr[-400:])
    return ok


def arm(ratio: str, moments: Optional[str]) -> Optional[Dict[str, Any]]:
    cmd = [sys.executable, "-X", "utf8", "agent_cli.py", "recall-bench", "--json"]
    if moments:
        cmd += ["--set", moments]
    r = subprocess.run(cmd, cwd=_REPO, env=_child_env(ratio), capture_output=True,
                       text=True, errors="replace", timeout=900)
    if r.returncode != 0:
        print("arm ratio=%s FAILED rc=%s\n%s" % (ratio, r.returncode, (r.stderr or "")[-800:]))
        return None
    try:
        return json.loads(r.stdout)["result"]
    except Exception as exc:                                              # noqa: BLE001
        print("arm ratio=%s: unreadable bench output (%s)" % (ratio, exc))
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="both-arms sweep for the relative floor")
    ap.add_argument("--set", dest="moments", default=None, help="moments.json (default: committed set)")
    ap.add_argument("--ratios", default="0,0.5,0.8,0.95,0.999")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not calibrate():
        return 2

    ratios: List[str] = [x.strip() for x in args.ratios.split(",") if x.strip()]
    out: Dict[str, Any] = {"ratios": {}, "moments_set": args.moments or "(committed)"}
    verdicts: Dict[str, Dict[str, str]] = {}

    for ratio in ratios:
        res = arm(ratio, args.moments)
        if not res:
            return 1
        ab = res.get("abstention") or {}
        scored = res.get("scored") or 0
        row = {
            "scored": scored,
            # Counts, not rates: at n=18 a percentage manufactures significance.
            "recall_at_1_n": round(res.get("recall_at_1", 0.0) * scored),
            "recall_at_k_n": round(res.get("recall_at_k", 0.0) * scored),
            "recall_at_1": res.get("recall_at_1"),
            "recall_at_k": res.get("recall_at_k"),
            "abstention_correct": ab.get("correct"),
            "abstention_total": ab.get("total"),
        }
        out["ratios"][ratio] = row
        verdicts[ratio] = {r["id"]: r["verdict"] for r in res.get("rows", [])}
        if not args.json:
            print("ratio=%-6s scored=%-3s recall@1=%s/%s  recall@5=%s/%s  abstention=%s/%s" % (
                ratio, scored, row["recall_at_1_n"], scored, row["recall_at_k_n"], scored,
                row["abstention_correct"], row["abstention_total"]))

    base = ratios[0]
    changed = {}
    for ratio in ratios[1:]:
        d = {i: (verdicts[base].get(i), verdicts[ratio].get(i))
             for i in verdicts[base] if verdicts[base].get(i) != verdicts[ratio].get(i)}
        if d:
            changed[ratio] = d
    out["changed_vs_" + base] = changed

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print()
    if not changed:
        print("NO moment changed verdict at any ratio (compared id by id against ratio=%s)." % base)
    else:
        print("MOMENTS THAT CHANGED VERDICT (vs ratio=%s):" % base)
        for ratio, d in changed.items():
            for i, (was, now) in sorted(d.items()):
                print("  ratio=%-6s %-5s %-18s -> %s" % (ratio, i, was, now))
    print("\nRead the count, not the rate. One moment moving on 18 is not an improvement;")
    print("it is the size of sample at which a tuned threshold starts to look like one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
