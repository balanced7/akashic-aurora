"""suite_read — the READ-ONLY half of the suite verb family (wired 2026-10-01).

Companion spec: design/suite-verb-family-spec.md. Reached from agent_cli.py `suite diff |
triage | rerun-failing | tail` (see cmd_suite).

This module is the pure, testable core behind `suite diff` / `suite triage` /
`suite rerun-failing` / `suite tail`. It is deliberately a PROJECTION layer over records that
already exist (suite_baseline.py + pytest's lastfailed cache + a log file). It must never:

  * write to state/coord/suite_baseline.json   (recording/tightening stay in ship_gate)
  * own a subprocess pipe as its only record     (the log FILE is the record)
  * hardcode an interpreter                       (always sys.executable -m pytest)
  * render UNKNOWN as an accusation               (UNKNOWN never exits nonzero)

WHY READS-ONLY IS THE SAFETY STORY (the spec's "one rule"):
every failure mode this house has already paid for lives in the WRITE path — record-by-default
(never_verify_a_write_door_by_invoking_it), absence-eats-known-failures (verdicts' fixed-scope
clause), stdout-swallow-confident-zero (attribution_organ_swallows_stdout_confident_zero),
pipe-holding orphans (timeout_py_launcher_orphans_python_exe). This module contains none of
those paths by construction.
"""
from __future__ import annotations

import glob
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from core.coord import suite_baseline as sb

#: where suite runs deposit their full output; the FILE is the tail-able record, matching
#: background_receipt_runs_capture_full_output_not_tail.  OS-agnostic (no tempdir-shape, no
#: cp1252) so Linux and Windows agree on the path.
SUITE_LOG_GLOB = os.path.join("state", "suite-run-*.log")


# ---------------------------------------------------------------------------
# suite diff -- project the existing delta/verdicts compute, no new logic
# ---------------------------------------------------------------------------
def diff(nodes: List[str], *, now_sha: Optional[str] = None,
         full_suite: bool = False) -> Dict[str, Any]:
    """Render the delta + per-node verdicts for a failure list.

    Pure projection over suite_baseline.delta()/verdicts(); returns their union plus a stable
    render. Reads the baseline file but never writes it.
    """
    d = sb.delta(nodes)
    v = sb.verdicts(nodes, now_sha=now_sha, full_suite=full_suite)
    return {
        "delta": d,
        "by_node": v["by_node"],
        "counts": v["counts"],
        "stale": v["stale"],
        "baseline_sha": v["baseline_sha"],
        "head_sha": v["head_sha"],
        "baseline_at": v["baseline_at"],
        "has_baseline": v["has_baseline"],
        "full_suite": v["full_suite"],
    }


def render_diff(res: Dict[str, Any]) -> str:
    """Stable text for `suite diff`. UNKNOWN is printed with its 'next' text, never as an
    accusation, and never contributes to a nonzero exit (see cmd-level contract)."""
    lines: List[str] = []
    counts = res["counts"]
    prov = (f"baseline @{res['baseline_sha']} vs HEAD @{res['head_sha']}"
            if res["has_baseline"] else "NO baseline recorded")
    stale = "  [STALE: attribution limited]" if res["stale"] else "  [current]"
    lines.append(f"# {sum(counts.values())} failure(s) -- {prov}{stale}")
    for verdict in ("YOURS", "UNKNOWN", "LIKELY_INHERITED", "INHERITED"):
        hits = sorted(n for n, row in res["by_node"].items()
                      if row["verdict"] == verdict)
        if not hits:
            continue
        lines.append(f"\n{verdict} ({len(hits)}): {sb.VERDICT_NEXT[verdict]}")
        lines.extend(f"    {n}" for n in hits)
    if res["delta"]["fixed"] and res["full_suite"]:
        lines.append(f"\nfixed since baseline ({len(res['delta']['fixed'])}):")
        lines.extend(f"    {n}" for n in res["delta"]["fixed"][:10])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# suite triage -- attribute failures to lanes via classify()
# ---------------------------------------------------------------------------
def triage(nodes: List[str]) -> Dict[str, str]:
    """node_id -> owning lane task id ('' = unclassified). Pure projection."""
    return sb.classify(nodes)


def render_triage(lanes: Dict[str, str]) -> str:
    tally: Dict[str, int] = {}
    for lane in lanes.values():
        key = lane or "unowned"
        tally[key] = tally.get(key, 0) + 1
    lines = [f"{k}:{v}" for k, v in sorted(tally.items())]
    out = ["# suite triage (node -> owning lane)"]
    out.append("  " + ", ".join(lines) if lines else "  no lanes classified")
    for node in sorted(lanes):
        out.append(f"  {node}  ({lanes[node] or 'unowned'})")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# suite rerun-failing -- surface pytest's OWN lastfailed cache, or the baseline's list
# ---------------------------------------------------------------------------
def _pytest_cache_dir(root: Optional[str] = None) -> str:
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, ".pytest_cache", "v", "cache")


def lastfailed_nodes(root: Optional[str] = None) -> List[str]:
    """FAILED node ids from pytest's own lastfailed cache (the record of record for 'what broke
    last'). Returns [] and NEVER raises: a missing cache is 'no prior run', not an error."""
    cache = os.path.join(_pytest_cache_dir(root), "lastfailed")
    try:
        with open(cache, encoding="utf-8") as f:
            import json
            return sorted(json.load(f).keys())
    except Exception:
        return []


def rerun_command(nodes: List[str], *, run: bool = False) -> Tuple[int, str]:
    """Build (and, with run=True, execute) the exact failing-node selector.

    Exit code = pytest's own exit code (the gate is the process exit, never a pipe). The
    .pytest_cache is left UNTOUCHED: pytest rewrites it on completion; we never mutate it.
    """
    if not nodes:
        return 0, "[suite rerun-failing] no prior failing nodes (empty lastfailed cache)"
    args = [sys.executable, "-m", "pytest", "-q"] + nodes
    cmd = " ".join(args)
    if not run:
        return 0, f"[suite rerun-failing] (dry) {cmd}\n  add --run to execute"
    code = _run_pytest(args)
    return code, f"[suite rerun-failing] exit {code}: {cmd}"


def _run_pytest(args: List[str], timeout: Optional[int] = None) -> int:
    """Spawn pytest with the FULL output captured to a file (the record), not a pipe we own.

    The file is written regardless of the process exit; we return only the exit code. stdout and
    stderr are STDOUT-merged into the log so the tail shows failures interleaved with progress,
    and NOTHING is held in memory (the file is the record; we never own the pipe). Timeout is
    optional and, when set, bounds the interpreter directly (never a py-launcher) so a timed-out
    run orphans a real python, not a wrapper -- see timeout_py_launcher_orphans_python_exe.
    """
    import subprocess
    import time
    import uuid

    os.makedirs("state", exist_ok=True)
    log = os.path.join("state", f"suite-run-{int(time.time())}-{uuid.uuid4().hex[:6]}.log")
    with open(log, "w", encoding="utf-8") as fh:
        r = subprocess.run(args, stdout=fh, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, timeout=timeout)
    print(f"[suite] full run logged to {log}", file=sys.stderr)
    return r.returncode


# ---------------------------------------------------------------------------
# suite tail -- poll the log file(s), never own a process pipe
# ---------------------------------------------------------------------------
STALE_AFTER_S = 300  # a suite log this old (with no growth) is 'finished', not 'live'


def tail(lines: int = 20, stale_after_s: float = STALE_AFTER_S) -> Tuple[bool, str]:
    """Return (running, rendered_tail) over the newest suite log.

    `running` is an HONEST guess, never a confident zero and never a confident live: 'still
    running' iff the newest log exists AND its mtime is within the staleness horizon. A log past
    the horizon reads as 'finished' (the process ended or died -- the FILE is the truth either
    way; we do not own the process, so we never claim to know it from here).
    """
    logs = sorted(glob.glob(SUITE_LOG_GLOB), key=os.path.getmtime)
    if not logs:
        return False, "[suite tail] no suite run log found (none in progress)"
    newest = logs[-1]
    try:
        mtime = os.path.getmtime(newest)
    except OSError:
        mtime = 0.0
    try:
        with open(newest, encoding="utf-8") as f:
            body = f.read().splitlines()
    except OSError as e:
        return False, f"[suite tail] unreadable {newest}: {type(e).__name__}: {e}"
    tail_lines = body[-lines:]
    running = (time.time() - mtime) < stale_after_s
    state = "running" if running else "finished (no recent growth)"
    header = f"[suite tail] {newest} ({len(body)} lines) -- {state}"
    return running, header + "\n" + "\n".join(tail_lines)
