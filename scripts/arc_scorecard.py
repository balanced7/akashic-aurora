#!/usr/bin/env python3
"""arc_scorecard.py -- T031 hook 3: the wrap-time M-practice scorecard.

Deterministic reads over the arc window (git history + the event firehose): which
M practices FIRED, with metric reads; a practice with zero signal renders as an
annotate-me prompt -- skipped-with-reason belongs in the wrap note, never silence.
A READER, not a gate: always exits 0. Wired into the wrap draft; also standalone:

  py scripts/arc_scorecard.py --days 2
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITE_RE = re.compile(r"(?:docs|research/reviewed)/[A-Za-z0-9_\-./]+\.md")


def _git(*argv) -> str:
    # encoding pinned: text=True means cp1252 on Windows, and one unicode commit body
    # kills the reader thread (stdout becomes None). utf-8 + replace, always.
    r = subprocess.run(["git", *argv], capture_output=True, cwd=ROOT,
                       encoding="utf-8", errors="replace")
    return r.stdout or ""


def _commits(days: float):
    """[(sha, subject+body)] newest-first in the window."""
    raw = _git("log", f"--since={days} days ago", "--format=%x01%h%x09%s%n%b")
    out = []
    for block in raw.split("\x01"):
        if block.strip():
            sha, _, rest = block.partition("\t")
            out.append((sha.strip(), rest.strip()))
    return out


def _added_files(days: float, prefix: str) -> list:
    raw = _git("log", f"--since={days} days ago", "--diff-filter=A", "--name-only", "--format=")
    return sorted({l.strip() for l in raw.splitlines()
                   if l.strip().replace("\\", "/").startswith(prefix)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=2.0)
    args = ap.parse_args()
    days = args.days
    commits = _commits(days)
    msgs = [m for _, m in commits]
    n = len(commits)

    def count(pattern, flags=re.IGNORECASE):
        rx = re.compile(pattern, flags)
        return sum(1 for m in msgs if rx.search(m))

    gated = sum(1 for m in msgs if CITE_RE.search(m))
    prereg = count(r"pre-?registered|committed BEFORE impl|registration")
    drills = count(r"\bdrill")
    live = count(r"\blive[- ](?:drill|drill:|exercis|prov|incident|finding)")
    fences = count(r"\b(?:fenced|design[- ]review|dual[- ]half|reconcil)")
    reverts = count(r"\brevert")
    records = _added_files(days, "research/reviewed/")
    guards = _added_files(days, "scripts/check_")
    ungated = []
    try:
        from core.events.event_query import get_event_query
        from datetime import datetime, timedelta
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        ungated = get_event_query().search("", kind="ungated_ship", since=since, top_k=10)
    except Exception:
        pass

    def line(mid, label, signal, read):
        if signal:
            print(f"  {mid:<4} {label:<28} FIRED   {read}")
        else:
            print(f"  {mid:<4} {label:<28} (no signal -- annotate fired/skipped-with-reason "
                  f"in the wrap note)")

    print(f"## ARC SCORECARD (last {days:g}d: {n} commit(s)) -- method-baseline reads (T031 hook 3)")
    line("M1", "fenced dual pass", fences, f"{fences} fence/review/reconcile ship(s)")
    line("M3", "pre-registered acceptance", prereg, f"{prereg} registration-marked ship(s)")
    line("M4", "drills as acceptance", drills, f"{drills} drill-bearing ship(s)")
    line("M5", "live-exercise after ship", live, f"{live} live-exercise mention(s)")
    line("M6", "verbatim preservation", records,
         f"{len(records)} record(s) added: " + ", ".join(os.path.basename(r) for r in records[:4]))
    line("M10", "guards for new law", guards,
         f"{len(guards)} guard(s) born: " + ", ".join(os.path.basename(g) for g in guards[:4]))
    print(f"  M11  slice discipline            {n} slice(s), {reverts} revert(s), "
          f"{gated}/{n} cite a spec/record ({(100.0 * gated / n if n else 0):.0f}% gated)")
    if ungated:
        print(f"  !!   UNGATED substrate ship(s) this window: {len(ungated)} -- each needs a "
              f"wrap ruling (hook 1 audit line)")
    print("  (M0/M2/M7/M8/M9: judgment practices -- annotate in the wrap note where they "
          "fired or were deliberately skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
