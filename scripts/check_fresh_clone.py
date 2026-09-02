"""check_fresh_clone -- the T180 gate: "the working tree is not the repo" fails LOUDLY.

THE WOUND (task T180, found 2026-08-05, gate shipped 2026-09-02)
----------------------------------------------------------------
core/comm/room_feed.py sat UNTRACKED while tracked scripts/bifrost_ui.py imported it.
The working tree ran fine. A fresh clone hit 3 collection errors, pytest INTERRUPTED,
the suite ran ZERO tests, and a naive pipeline read the empty failure list as SUCCESS.
By the time the gate was built, the named file had healed by drift (someone tracked it,
task untouched) -- and the same class had regenerated three times in one day when first
found. Individual fixes don't hold; only a gate does.

THE MEANING (not a membership list -- harden the meaning, not the location)
---------------------------------------------------------------------------
1. STATIC LAW: no TRACKED file may import a module whose resolved file exists on disk
   but is untracked. That is works-here-breaks-there in its purest form: the tree has
   the file, only the repo doesn't, so every clone inherits a breakage the author
   cannot see.
2. DRILL LAW: a clone of HEAD, alone, must produce the full test surface -- zero
   collection errors AND a collected count at or above the floor. ZERO COLLECTED IS
   NEVER SUCCESS, whatever the exit code says: an empty suite is the poison itself.

MODES
-----
  py scripts/check_fresh_clone.py            # static scan only (fast; hook-friendly)
  py scripts/check_fresh_clone.py --clone    # + clone HEAD to temp, pytest --collect-only
  py scripts/check_fresh_clone.py --clone --receipt state/coord/fresh_clone_gate.json

The receipt is written INSIDE the repo (state/coord/, tracked) because a guard whose
evidence lives on a gitignored path cannot be verified from any clone -- the exact
disease this gate exists to cure would then infect its own receipts.

FLOOR RATCHET: the floor is a tracked constant, deliberately edited upward as the
suite grows (4954 collectable on 2026-09-02). Lowering it is a deliberate, visible,
reviewable act -- never an ambient drift.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Collected count on 2026-09-02 was 4954 across 630 files. Headroom for legitimate
# test consolidation; raise at gates as the suite grows (one-way by convention).
FLOOR = 4900

_PER_FILE = re.compile(r"^(?:\S+?):\s*(\d+)\s*$")


# --------------------------------------------------------------------------- git
def _git_lines(root: str, *args: str) -> list[str]:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {root}: {proc.stderr.strip()}")
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _posix(rel: str) -> str:
    return rel.replace("\\", "/")


# ------------------------------------------------------------------ static scan
def _module_candidates(importing_rel: str, node: ast.AST) -> list[str]:
    """Repo-relative candidate paths a tracked import could resolve to.

    Approximation by design: only repo-local, file-backed resolutions matter here.
    A candidate that doesn't exist on disk is stdlib/third-party and is skipped, so
    the scan cannot false-positive on requests/json/etc. The clone drill remains
    the meaning-level backstop for anything a static walk cannot see.
    """
    cands: list[str] = []

    def from_dotted(base: str, dotted: str) -> None:
        path = dotted.replace(".", "/")
        prefix = f"{base}/" if base else ""
        cands.append(f"{prefix}{path}.py")
        cands.append(f"{prefix}{path}/__init__.py")

    if isinstance(node, ast.Import):
        for alias in node.names:
            from_dotted("", alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0:
            if node.module:
                from_dotted("", node.module)
                for alias in node.names:
                    from_dotted("", f"{node.module}.{alias.name}")
        else:
            # relative: climb from the importing file's package dir
            pkg_dir = os.path.dirname(importing_rel)
            for _ in range(node.level - 1):
                pkg_dir = os.path.dirname(pkg_dir)
            base = _posix(pkg_dir)
            if node.module:
                from_dotted(base, node.module)
                for alias in node.names:
                    from_dotted(base, f"{node.module}.{alias.name}")
            else:
                for alias in node.names:
                    from_dotted(base, alias.name)
    return cands


def scan_static(root: str) -> list[dict]:
    """Every tracked .py whose import resolves to a present-but-untracked file."""
    tracked = [_posix(p) for p in _git_lines(root, "ls-files")]
    tracked_py = [p for p in tracked if p.endswith(".py")]
    tracked_set = set(tracked)
    untracked = {
        _posix(p)
        for p in _git_lines(root, "ls-files", "--others", "--exclude-standard")
    }

    violations: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rel in tracked_py:
        full = os.path.join(root, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                tree = ast.parse(fh.read(), filename=rel)
        except (OSError, SyntaxError):
            continue  # unparseable tracked code is a different wound; the drill catches it
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for cand in _module_candidates(rel, node):
                if cand in tracked_set or cand not in untracked:
                    continue
                if not os.path.exists(os.path.join(root, cand)):
                    continue
                key = (rel, cand)
                if key in seen:
                    continue
                seen.add(key)
                violations.append(
                    {"importer": rel, "module": cand.rsplit("/", 1)[-1][:-3],
                     "file": cand,
                     "law": "tracked code imports a present-but-untracked file"}
                )
    return violations


# ------------------------------------------------------------------ clone drill
def clone_verdict(returncode: int, collected: int, errors: int,
                  floor: int = FLOOR) -> dict:
    """Pure judgment on a collection run. Empty is never success."""
    reasons: list[str] = []
    if errors > 0:
        reasons.append(f"{errors} collection error(s) -- the exact T180 interrupt shape")
    if collected == 0 or returncode == 5:
        reasons.append(
            "zero tests collected -- an empty suite is the poison itself, "
            "never success (T180)"
        )
    elif returncode not in (0,):
        reasons.append(f"pytest exit {returncode}")
    if collected and collected < floor:
        reasons.append(f"collected {collected} below floor {floor}")
    return {"ok": not reasons, "reasons": reasons}


def _rm_readonly(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def run_clone_drill(root: str, floor: int = FLOOR, tmp_base: str | None = None,
                    keep: bool = False) -> dict:
    """Clone HEAD to temp, collect the suite there, judge, clean up, return receipt."""
    sha = _git_lines(root, "rev-parse", "--short", "HEAD")[0]
    tmp = tempfile.mkdtemp(prefix="t180-fresh-clone-", dir=tmp_base)
    clone = os.path.join(tmp, "clone")
    try:
        subprocess.run(["git", "clone", "--quiet", root, clone],
                       capture_output=True, text=True, check=True)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=clone, capture_output=True, text=True, timeout=900,
        )
        counts = [int(m.group(1)) for m in
                  (_PER_FILE.match(ln) for ln in proc.stdout.splitlines()) if m]
        collected = sum(counts)
        errors = len(re.findall(r"^ERROR\b", proc.stdout, re.M))
        verdict = clone_verdict(proc.returncode, collected, errors, floor)
        return {
            "v": 1,
            "kind": "fresh_clone_gate",
            "sha": sha,
            "seat": os.environ.get("AKASHIC_AGENT_ID", "unknown"),
            "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "collected": collected,
            "files": len(counts),
            "errors": errors,
            "returncode": proc.returncode,
            "floor": floor,
            "ok": verdict["ok"],
            "reasons": verdict["reasons"],
        }
    finally:
        if not keep:
            shutil.rmtree(tmp, onerror=_rm_readonly)


# ------------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=REPO_ROOT)
    ap.add_argument("--clone", action="store_true",
                    help="also clone HEAD and collect the suite there (the drill)")
    ap.add_argument("--floor", type=int, default=FLOOR)
    ap.add_argument("--receipt", help="write the drill receipt JSON here (tracked path!)")
    ap.add_argument("--tmp", help="temp base for the clone (e.g. a ramdisk)")
    args = ap.parse_args(argv)

    failed = False

    violations = scan_static(args.root)
    if violations:
        failed = True
        for v in violations:
            print(f"VIOLATION: tracked {v['importer']} imports {v['module']} "
                  f"-> untracked {v['file']}")
        print(f"static law: {len(violations)} works-here-breaks-there import(s)")
    else:
        print("static law: clean -- no tracked import resolves to an untracked file")

    if args.clone:
        receipt = run_clone_drill(args.root, floor=args.floor, tmp_base=args.tmp)
        line = (f"drill law: clone @{receipt['sha']} collected {receipt['collected']} "
                f"tests / {receipt['files']} files, {receipt['errors']} error(s), "
                f"floor {receipt['floor']}")
        print(line)
        if not receipt["ok"]:
            failed = True
            for r in receipt["reasons"]:
                print(f"  FAIL: {r}")
        if args.receipt:
            path = os.path.join(args.root, args.receipt) \
                if not os.path.isabs(args.receipt) else args.receipt
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(receipt, fh, indent=1)
                fh.write("\n")
            print(f"receipt -> {args.receipt}")

    print(f"fresh-clone gate: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
