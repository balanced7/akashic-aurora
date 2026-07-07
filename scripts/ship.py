#!/usr/bin/env python3
"""ship.py -- one disciplined command to ship a slice: GATE -> commit+push -> (lesson) -> snapshot.

    py scripts/ship.py "commit message" path [path ...]
    py scripts/ship.py "msg" a.py b.py --learn-exp NAME --tried "..." --result "..." --recommend "..."
    py scripts/ship.py "msg" a.py --no-snapshot
    py scripts/ship.py "msg" a.py --dry-run         # print the plan; do nothing

Encodes the whole slice ritual so the conventions can't be forgotten or half-done:
  1. GATE -- check_boundaries + check_doc_freshness + the full pytest suite. ANY failure ABORTS
     before anything is committed, so you never push something CI would reject.
  2. COMMIT + PUSH via mirror.py with EXPLICIT paths (never `git add -A`; the shared-tree rule).
  3. (optional) record a lesson  (--learn-exp ...).
  4. snapshot the knowledge store (knowledge DATA is not in git).
Fail-fast: if a step exits non-zero, ship stops and reports; nothing past it runs.
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable or "py"


def build_plan(args):
    """The ordered [(label, argv)] steps. PURE -- powers --dry-run and the tests (no side effects)."""
    steps = []
    if not args.no_test:
        steps.append(("guard: boundaries", [PY, "scripts/check_boundaries.py"]))
        steps.append(("guard: doc-freshness", [PY, "scripts/check_doc_freshness.py"]))
        steps.append(("guard: comprehensibility (map matches code)", [PY, "scripts/check_comprehensibility.py"]))
        steps.append(("tests (full suite)", [PY, "-m", "pytest", "-q"]))
    steps.append(("commit + push", [PY, "scripts/mirror.py", args.message, *args.paths]))
    if args.learn_exp:
        learn = [PY, "agent_cli.py", "learn", args.agent, "--experiment", args.learn_exp]
        if args.tried:
            learn += ["--tried", args.tried]
        if args.result:
            learn += ["--result", args.result]
        if args.recommend:
            learn += ["--recommend", args.recommend]
        if getattr(args, "anti_pattern", ""):
            learn += ["--anti-pattern", args.anti_pattern]
        steps.append(("record lesson", learn))
    if not args.no_snapshot:
        steps.append(("snapshot", [PY, "scripts/snapshot_knowledge.py", "snapshot"]))
    return steps


def _run(label, cmd):
    print(f"\n=== {label} ===")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


def main():
    p = argparse.ArgumentParser(prog="ship.py", description="Gate -> commit+push -> lesson -> snapshot, in one step.")
    p.add_argument("message", help="commit message")
    p.add_argument("paths", nargs="*", help="the EXPLICIT files you're shipping (never git add -A)")
    p.add_argument("--agent", default=os.getenv("AKASHIC_AGENT_ID", "claude"))
    p.add_argument("--learn-exp", dest="learn_exp", default=None, help="record a lesson with this experiment name")
    p.add_argument("--tried", default="")
    p.add_argument("--result", default="")
    p.add_argument("--recommend", default="")
    p.add_argument("--anti-pattern", dest="anti_pattern", default="",
                   help="tag the recorded lesson as a reusable known-bad (recall's dissent-finder warns on it)")
    p.add_argument("--no-test", action="store_true", help="skip the gate (rare; e.g. a docs-only fixup)")
    p.add_argument("--no-snapshot", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = p.parse_args()

    if not args.paths:
        print("ERROR: name the EXPLICIT paths you're shipping (ship never `git add -A` in a shared tree).")
        print('Example: py scripts/ship.py "fix X" core/foo.py tests/test_foo.py')
        return 2

    steps = build_plan(args)
    if args.dry_run:
        print("# ship plan (dry-run -- nothing executed):")
        for label, cmd in steps:
            print(f"  - {label}: {' '.join(cmd)}")
        return 0

    for label, cmd in steps:
        if not _run(label, cmd):
            print(f"\n[ship] ABORTED at: {label} (exit non-zero). Nothing past this step ran.")
            return 1
    print("\n[ship] done -- gated green, committed, pushed" +
          ("" if args.no_snapshot else ", snapshotted") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
