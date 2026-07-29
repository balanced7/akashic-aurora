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
