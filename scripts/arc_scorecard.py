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


# A guard is a CHECKER SCRIPT. Both locations count: T104 moved them from scripts/ to
# scripts/checkers/, and the old prefix "scripts/check_" silently stopped matching, because
# "scripts/checkers/..." has an "e" where the prefix wants "_". M10 therefore reported
# "no signal" through a window in which a guard was demonstrably added -- a detector blinded
# by a refactor that touched neither it nor any test of it.
#
# The DEFINITION is deliberately unchanged. scripts/ship_gate.py is a guard in spirit and does
# not match; counting it would be widening the instrument until it flatters the operator, which
# is the one move that makes a self-measured method loop worthless.
GUARD_PREFIXES = ("scripts/checkers/check_", "scripts/check_")


def is_guard_path(path: str) -> bool:
    """True when `path` is a guard by M10's definition. One predicate, so the scorecard and
    its pins can never drift apart."""
    return str(path or "").replace("\\", "/").startswith(GUARD_PREFIXES)


def _added_guards(days: float) -> list:
    raw = _git("log", f"--since={_since_iso(days)}", "--diff-filter=A", "--name-only", "--format=")
    return sorted({l.strip() for l in raw.splitlines() if is_guard_path(l.strip())})


# Detectors that read commit PROSE. They measure what we SAY, and they render green silence the
# moment we stop typing a word -- the trap M3 sat in until it was made to read git. Labelled
# rather than trusted, because presenting self-report as measurement is how a scorecard flatters.
SELF_REPORT = {"M1", "M4", "M5"}

# git revert writes this subject form. Structure, not prose -- a body cannot forge it.
_REVERT_SUBJECT = re.compile(r'^\s*Revert\s+"', re.MULTILINE)


def is_revert(message) -> bool:
    """True only for a real `git revert` commit.

    This used to be `\\brevert` over the whole message BODY. Then Daniel asked that risky
    changes ship with a way to undo them, every commit of the arc grew a "REVERT: ..." line,
    and the card read 20 of 20 commits as reverts while ZERO reverts had occurred.

    Nobody edited the detector and nothing broke. A GOOD PRACTICE was adopted and its new
    writing convention collided with an old regex, silently inverting the number. That is the
    sharpest form of the confident-zero family found in this arc, because there is no defect to
    find -- only a measurement that quietly stopped meaning what it said. It also arrived while
    I was labelling three OTHER detectors [self-report], which is the lesson: prose-reading
    instruments decay from changes in how we WRITE, not only from changes in what we DO.

    Reading the subject line keeps it structural: only git itself produces `Revert "..."`.
    """
    try:
        head = str(message or "").strip().splitlines()[0] if str(message or "").strip() else ""
    except Exception:
        return False
    return bool(_REVERT_SUBJECT.match(head))

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude", "backups", "snapshots"}


def detector_health(name: str, predicate, root: str = "") -> dict:
    """kimi's META-GUARD: does this detector's evidence class exist AT ALL?

    A path-predicate detector that matches NOTHING in the current tree is BLIND, not observing
    an empty world -- and rendering blindness as zero is the confident-zero disease this arc
    found ten instances of in one night. The proof case: M10 searched for "scripts/check_"
    after T104 moved every checker to scripts/checkers/, so it reported "(no signal)" while
    guards were being written, and nothing distinguished that from "none were written".

    OK          -> the predicate matches real files; a zero in the window is real information
    UNCHECKABLE -> matches nothing anywhere; the detector is looking for something that is gone

    Fail-open: a predicate that raises confesses UNCHECKABLE rather than crashing the reader
    it audits. A meta-guard that can break the organ is worse than no meta-guard.
    """
    base = root or ROOT
    hits = 0
    try:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fn), base).replace("\\", "/")
                try:
                    if predicate(rel):
                        hits += 1
                        if hits >= 2:
                            return {"name": name, "status": "OK", "matches": hits, "detail": ""}
                except Exception:
                    return {"name": name, "status": "UNCHECKABLE", "matches": 0,
                            "detail": "predicate raised -- the detector cannot evaluate itself"}
    except Exception:
        return {"name": name, "status": "UNCHECKABLE", "matches": 0,
                "detail": "tree walk failed"}
    if hits:
        return {"name": name, "status": "OK", "matches": hits, "detail": ""}
    return {"name": name, "status": "UNCHECKABLE", "matches": 0,
            "detail": "predicate matches nothing in the tree -- the detector is blind, "
                      "so a zero here means NOT MEASURED, never 'none happened'"}


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
    reverts = sum(1 for m in msgs if is_revert(m))
    records = _added_files(days, "research/reviewed/")
    guards = _added_guards(days)
    ungated = []
    try:
        from core.events.event_query import get_event_query
        from datetime import datetime, timedelta
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        ungated = get_event_query().search("", kind="ungated_ship", since=since, top_k=10)
    except Exception:
        pass

    # META-GUARD (kimi): before trusting a zero, ask whether the detector can see anything at
    # all. A zero from a blind detector is not information.
    health = {
        "M6": detector_health("M6", lambda p: p.startswith("research/reviewed/")),
        "M10": detector_health("M10", is_guard_path),
    }

    def line(mid, label, signal, read):
        tag = " [self-report]" if mid in SELF_REPORT else ""
        if signal:
            print(f"  {mid:<4} {label:<28} FIRED   {read}{tag}")
        elif health.get(mid, {}).get("status") == "UNCHECKABLE":
            print(f"  {mid:<4} {label:<28} UNCHECKABLE -- {health[mid]['detail']}")
        else:
            print(f"  {mid:<4} {label:<28} (no signal -- annotate fired/skipped-with-reason "
                  f"in the wrap note){tag}")

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
    # M11 is MEASURED by replaying the real gate, not by regexing doc paths out of messages.
    # deepseek: "a typo fix mentioning docs/ARCHITECTURE.md counts as gated; a full-fence slice
    # whose message says only 'RB-99 landed' does not... target it upward and you get more doc
    # paths in messages, not more gated slices. Goodhart." The DENOMINATOR was wrong too: the
    # gate only applies to substrate ships, so a rate over all commits meant nothing either way.
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts", "checkers"))
        from check_reconciliation_gate import audit_stats as _gate_audit
        g = _gate_audit(max(n, 20))
        if g["applied"]:
            print(f"  M11  slice discipline            {n} slice(s), {reverts} revert(s); "
                  f"MEASURED {g['passed'] + g['ungated']}/{g['applied']} SUBSTRATE ship(s) "
                  f"gated ({g['pct']:.0f}%)"
                  + (f", {g['ungated']} ungated-with-reason" if g["ungated"] else ""))
            for sha, subj, why in g["offenders"][:3]:
                print(f"       ungated substrate: {sha} {subj}")
        else:
            print(f"  M11  slice discipline            {n} slice(s), {reverts} revert(s); "
                  f"no substrate ships in window -- gate did not apply")
    except Exception as exc:
        print(f"  M11  slice discipline            {n} slice(s), {reverts} revert(s) "
              f"[self-report: gate audit unavailable: {exc}]")
    if ungated:
        print(f"  !!   UNGATED substrate ship(s) this window: {len(ungated)} -- each needs a "
              f"wrap ruling (hook 1 audit line)")
    print("  (M0/M2/M7/M8/M9: judgment practices -- annotate in the wrap note where they "
          "fired or were deliberately skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())


