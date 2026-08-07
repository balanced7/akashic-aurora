"""suite_baseline — the test-suite receipt the next seat diffs instead of re-deriving (W34/B4).

Born from the fresh-seat tax measured 2026-07-21: 12 inherited full-suite failures took
ledger cross-referencing to classify as sibling-lane/drift/leftover — work a receipt
written at the LAST run makes a one-line diff. Consensus (claude opening + kimi counter):

  NODE-ID DELTAS, NEVER COUNTS (kimi blocking (a)) — "12 -> 12" must expose
    3-fixed+3-new churn; count-matching silently breaks the trust the baseline exists for.
  CLASSIFICATION DECAYS (kimi (b)) — "sibling lane T067" means something only while
    T067 is open; the baseline snapshots claims and the render flags lanes closed since.
  ATOMIC + PROVENANCE (kimi (c)) — sha/seat/at ride the record (the K0 discipline);
    multiple writers, one file, torn writes unrepresentable.
  NOBODY RUNS THE SUITE AT WRAP (Q3, both seats) — seats produce receipts when they run
    suites anyway; this module snapshots the freshest and confesses its age.

Auto-classification is mechanical honesty: a failing node whose test file appears in an
ACTIVE ledger task's own `files` list belongs to that lane; everything else stays
unclassified rather than guessed.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.foundation.timeutil import now_iso

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASELINE_PATH = os.path.join(_ROOT, "state", "coord", "suite_baseline.json")

_FAILED_RE = re.compile(r"^FAILED\s+(\S+::\S+?)(?:\s+-\s.*)?$", re.MULTILINE)


def ingest_pytest(text: str) -> List[str]:
    """FAILED node ids from pytest terminal output (the universal receipt format)."""
    return [m.group(1) for m in _FAILED_RE.finditer(str(text or ""))]


def _ledger_claims() -> Dict[str, str]:
    """{task_id: status} for non-done ledger tasks (fail-open {})."""
    try:
        from core.coord.task_ledger import state_view
        out: Dict[str, str] = {}
        for v in state_view().values():
            if isinstance(v, list):
                for t in v:
                    if isinstance(t, dict) and t.get("id"):
                        out[str(t["id"])] = str(t.get("status", ""))
        return out
    except Exception:
        return {}


def _task_files() -> Dict[str, List[str]]:
    """{task_id: files[]} for ledger tasks that declare files (fail-open {})."""
    try:
        from core.coord.task_ledger import state_view
        out: Dict[str, List[str]] = {}
        for v in state_view().values():
            if isinstance(v, list):
                for t in v:
                    if isinstance(t, dict) and t.get("id") and t.get("files"):
                        out[str(t["id"])] = [str(f) for f in t["files"]]
        return out
    except Exception:
        return {}


def classify(nodes: List[str]) -> Dict[str, str]:
    """node_id -> lane task id ('' = unclassified). Mechanical: the node's FILE half
    matches a task's declared files. Never guesses."""
    files_by_task = _task_files()
    out: Dict[str, str] = {}
    for n in nodes:
        fpath = str(n).split("::", 1)[0].replace("\\", "/")
        lane = ""
        for tid, files in files_by_task.items():
            if any(fpath == str(f).replace("\\", "/") for f in files):
                lane = tid
                break
        out[n] = lane
    return out


def record(nodes: List[str], *, seat: str, sha: str = "") -> Dict[str, Any]:
    """Snapshot the receipt: failures + lanes + claims-at-snapshot + provenance."""
    lanes = classify(nodes)
    rec = {"v": 1, "sha": str(sha), "seat": str(seat),
           "at": now_iso(),   # T119: the one clock (aware UTC)
           "failures": [{"node": n, "lane": lanes.get(n, "")} for n in nodes],
           "claims_at_snapshot": _ledger_claims()}
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    tmp = f"{BASELINE_PATH}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    os.replace(tmp, BASELINE_PATH)
    return rec


def read() -> Optional[Dict[str, Any]]:
    try:
        with open(BASELINE_PATH, encoding="utf-8") as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) and "failures" in rec else None
    except Exception:
        return None


def delta(current_nodes: List[str]) -> Dict[str, List[str]]:
    """Node-id set math vs the baseline: {new, fixed, inherited}. No baseline ->
    everything is 'new' (an honest first run, not an error)."""
    rec = read()
    base = {f["node"] for f in (rec or {}).get("failures", [])}
    cur = set(current_nodes)
    return {"new": sorted(cur - base), "fixed": sorted(base - cur),
            "inherited": sorted(cur & base)}


def head_sha() -> str:
    """Short sha of the tree the tests just ran against, or "" when git cannot answer.

    Injectable in pins, and "" is load-bearing: an unresolvable HEAD means we cannot
    know the baseline is current, and the only honest reading is UNKNOWN. Failing toward
    "fresh" would manufacture confident attributions out of a broken git call.
    """
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short=7", "HEAD"],
                           cwd=os.path.dirname(os.path.dirname(os.path.dirname(
                               os.path.abspath(__file__)))),
                           capture_output=True, text=True, timeout=10,
                           stdin=subprocess.DEVNULL)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


#: verdict -> what the reader should actually do about it.
VERDICT_NEXT = {
    "YOURS": "this failure is not in the baseline and the baseline is CURRENT -- it "
             "arrived with your change; investigate it",
    "INHERITED": "already failing at the baseline, which is current -- not yours, leave it",
    "LIKELY_INHERITED": "was failing when the baseline was taken, but that baseline is "
                        "STALE -- probably not yours, though it could have been fixed and "
                        "re-broken in the gap; re-record the baseline to be sure",
    "UNKNOWN": "cannot be attributed: the baseline is stale or absent, so this may have "
               "arrived any time in the gap -- BISECT this one (stash or a worktree at "
               "HEAD), or re-record the baseline first",
}


def verdicts(current_nodes: List[str], *, now_sha: Optional[str] = None,
             full_suite: bool = False) -> Dict[str, Any]:
    """Per-node attribution: is this failure MINE? (T208)

    WHY THIS EXISTS, measured 2026-08-06. Four failures were hit while shipping T200 and
    T203, and each cost a manual `git stash` bisect -- one of which was answered WRONG,
    publicly, from an inconclusive single-test run. The baseline already knew one of the
    four (`test_t060_n0_shadow_router`, recorded 2026-07-24) and nothing surfaced it. Same
    shape as T197: the verdict existed, the door never asked.

    WHAT delta() COULD NOT SAY. It does pure set math and never compares the stored sha to
    HEAD, so "new" silently means both "arrived with your change" and "broke somewhere in
    the 14-day gap". Collapsing those is how a baseline trains a lie -- and it is the same
    one-word-two-meanings failure as `drained`, `unread` and `wakeable`.

    STALENESS CONTAMINATES BOTH DIRECTIONS, which is the half a naive fix misses: a node
    IN a stale baseline is only PROBABLY inherited, because it could have been fixed and
    re-broken since. "It was failing before" is the comfortable answer, so it is the one
    that rots unwatched.

    ADDITIVE: delta() keeps its contract; existing callers are untouched.
    """
    rec = read()
    base = {f["node"] for f in (rec or {}).get("failures", [])}
    b_sha = str((rec or {}).get("sha") or "")
    h_sha = str(now_sha if now_sha is not None else head_sha())
    # Fresh ONLY when both shas are known and equal. Unknown either side -> stale, because
    # "I could not check" must never render as "I checked and it matched".
    fresh = bool(rec) and bool(b_sha) and bool(h_sha) and b_sha.startswith(h_sha[:7])

    by_node: Dict[str, Any] = {}
    for n in sorted(set(current_nodes)):
        if n in base:
            v = "INHERITED" if fresh else "LIKELY_INHERITED"
        else:
            v = "YOURS" if fresh else "UNKNOWN"
        by_node[n] = {"verdict": v, "next": VERDICT_NEXT[v]}

    counts: Dict[str, int] = {}
    for row in by_node.values():
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    # `fixed` is only computable when the run COVERED the baseline's scope. Caught live
    # 2026-08-07 on this function's first real use: running three files reported ten
    # baseline failures as "fixed" when they had simply not been run -- and "fixed"
    # invites a re-record, which would have DELETED ten known failures from the receipt.
    # Correct under one assumption, silently wrong under another: the same shape as
    # every other defect in this arc. A subset run reports them as not_evaluated.
    missing = sorted(base - set(current_nodes))
    return {"by_node": by_node, "counts": counts,
            "fixed": missing if full_suite else [],
            "not_evaluated": [] if full_suite else missing,
            "full_suite": bool(full_suite),
            "stale": not fresh, "baseline_sha": b_sha or None,
            "head_sha": h_sha or None, "baseline_at": (rec or {}).get("at"),
            "has_baseline": bool(rec)}


def render_boot_line() -> str:
    """One boot line: count + provenance + age + the DECAY advisory (kimi (b)):
    classified lanes that have since CLOSED mean the classification rotted even if
    the receipt is young. '' when no baseline (fail-open, never a shout)."""
    rec = read()
    if not rec:
        return ""
    try:
        at_s = str(rec["at"])
        dt = datetime.fromisoformat(at_s)
        # T119 dual-era read: one-clock stamps carry their offset; legacy naive rows
        # were LOCAL wall-clock and keep their historical meaning.
        then = dt.timestamp() if dt.tzinfo is not None \
            else time.mktime(time.strptime(at_s, "%Y-%m-%dT%H:%M:%S"))
        age_h = max(0.0, (time.time() - then) / 3600.0)
    except Exception:
        age_h = -1.0
    n = len(rec.get("failures", []))
    lanes_then = {f["lane"] for f in rec.get("failures", []) if f.get("lane")}
    now = _ledger_claims()
    closed = sorted(l for l in lanes_then
                    if now.get(l, "").lower() in ("done", "abandoned"))
    age_s = f"{age_h:.1f}h old" if age_h >= 0 else "age unknown"
    line = (f"# suite baseline @{rec.get('sha', '?')[:7]} ({age_s}, by {rec.get('seat', '?')}): "
            f"{n} known failure(s)")
    if closed:
        line += (f" -- {len(closed)} classified lane(s) since closed ({', '.join(closed)}): "
                 "re-run advised (classification rots even when the receipt is young)")
    return line
