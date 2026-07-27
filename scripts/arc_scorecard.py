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


def _since_iso(days: float) -> str:
    """A CONCRETE timestamp for --since: git's approxidate silently ignores fractional
    'N days ago' (0.25 days ago -> full history -- the scorecard's own first live run
    read 411 commits as one arc). Never hand git a phrase when a date will do."""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def _commits(days: float):
    """[(sha, subject+body)] newest-first in the window."""
    raw = _git("log", f"--since={_since_iso(days)}", "--format=%x01%h%x09%s%n%b")
    out = []
    for block in raw.split("\x01"):
        if block.strip():
            sha, _, rest = block.partition("\t")
            out.append((sha.strip(), rest.strip()))
    return out


def _added_files(days: float, prefix: str) -> list:
    raw = _git("log", f"--since={_since_iso(days)}", "--diff-filter=A", "--name-only", "--format=")
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
    # M3 is MEASURED, not self-reported. It used to render `{prereg} registration-marked
    # ship(s)` -- a count of commits whose MESSAGE mentioned registration. That is compliance
    # by announcement: it counted what we said, never what we did, and it rendered a healthy
    # number straight through a window measured at 33% the first time anyone ran the audit
    # (8/24 test-adding commits clean, 2026-07-27, on an --audit mode that had shipped with
    # T031 and never once been run). The rate comes from git, so it cannot be talked up.
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))
        from check_preregistration import audit_stats
        m3 = audit_stats(max(n, 20))
        if m3["total"]:
            flag = "  <-- pins are landing WITH their implementation" if m3["pct"] < 80 else ""
            print(f"  M3   pre-registered acceptance  MEASURED {m3['clean']}/{m3['total']} "
                  f"test-adding commit(s) clean ({m3['pct']:.0f}%){flag}")
        else:
            line("M3", "pre-registered acceptance", prereg, "no test-adding commits in window")
    except Exception as exc:                      # a reader must never break the wrap
        line("M3", "pre-registered acceptance", prereg,
             f"{prereg} registration-marked ship(s) (audit unavailable: {exc})")
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
