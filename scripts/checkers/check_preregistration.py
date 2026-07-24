#!/usr/bin/env python3
"""check_preregistration.py -- T031 hook 2: M3's forcing function at ship time.

M3's bar: no slice ships whose acceptance postdates its implementation. The mechanical
form: a ship that stages a NEW pre-registered pin file (a tests/ file whose header
declares pre-registration) TOGETHER with non-test source is a pins-born-with-impl ship
-- exactly what pre-registration exists to prevent. Registration is its OWN commit,
BEFORE the impl commit.

Deliberately NOT machine-checked: modifying an EXISTING pin file inside an impl ship
(harness fixes -- quiesce parks, fixture plumbing -- are legitimate; assertions-frozen
is fence-review territory, a regex cannot referee it).

Usage (ship.py passes these):  check_preregistration.py <message> <path>...
       check_preregistration.py --audit N     # M3 metric over the last N commits
Exit 0 = pass; exit 1 = the gate holds the ship.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth
PREREG_RE = re.compile(r"pre-?registered", re.IGNORECASE)
# Source = where impl lives. docs/, research/, chronicles/ ride along with registrations.
NONSOURCE_PREFIXES = ("tests/", "docs/", "research/", "chronicles/")


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def _is_new_in_git(path: str) -> bool:
    """True when HEAD does not know this path (a brand-new file in this ship)."""
    r = subprocess.run(["git", "cat-file", "-e", f"HEAD:{_norm(path)}"],
                       capture_output=True, cwd=ROOT)
    return r.returncode != 0


def _declares_prereg(path: str) -> bool:
    try:
        head = open(os.path.join(ROOT, path), encoding="utf-8", errors="replace").read(2000)
        return bool(PREREG_RE.search(head))
    except OSError:
        return False


def _audit(n: int) -> int:
    """M3 metric: of the last N commits that ADD a tests/test_*.py, how many also
    touched source in the same commit (violations)."""
    log = subprocess.run(
        ["git", "log", f"-n{n}", "--diff-filter=A", "--name-only", "--format=%x01%h %s"],
        capture_output=True, cwd=ROOT, encoding="utf-8", errors="replace").stdout or ""
    total = viol = 0
    for block in log.split("\x01"):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        header, files = lines[0], [_norm(l) for l in lines[1:]]
        added_tests = [f for f in files if f.startswith("tests/test_") and f.endswith(".py")]
        if not added_tests:
            continue
        total += 1
        # The same commit's FULL touch set (adds + modifications):
        sha = header.split()[0]
        touched = (subprocess.run(["git", "show", "--name-only", "--format=", sha],
                                  capture_output=True, cwd=ROOT, encoding="utf-8",
                                  errors="replace").stdout or "").split()
        src = [f for f in map(_norm, touched) if f and not f.startswith(NONSOURCE_PREFIXES)]
        if src:
            viol += 1
            print(f"  VIOLATION {header}: new test(s) {added_tests} shipped with source {src[:3]}")
    ok = total - viol
    pct = (100.0 * ok / total) if total else 100.0
    print(f"M3 pre-registration compliance: {ok}/{total} test-adding commits clean ({pct:.0f}%)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=int, default=0, metavar="N")
    ap.add_argument("message", nargs="?", default="")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()
    if args.audit:
        return _audit(args.audit)

    paths = [_norm(p) for p in args.paths]
    new_prereg = [p for p in paths
                  if p.startswith("tests/") and p.endswith(".py")
                  and _is_new_in_git(p) and _declares_prereg(p)]
    source = [p for p in paths if not p.startswith(NONSOURCE_PREFIXES)]

    if new_prereg and source:
        print("FAIL: pins born WITH their impl -- the M3 violation this gate exists for:")
        for p in new_prereg:
            print(f"  new pre-registered pin file: {p}")
        for p in source[:5]:
            print(f"  source in the same ship:     {p}")
        print("Fix: commit the pin file FIRST (its own registration ship, skip-guarded), "
              "then ship the impl against the frozen contract (M3: the kill condition "
              "comes first).")
        return 1
    if new_prereg:
        print(f"PASS: registration ship ({len(new_prereg)} pre-registered pin file(s), "
              f"no source) -- M3 followed.")
        return 0
    print("PASS: no new pre-registered pin files staged -- M3 gate does not apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
