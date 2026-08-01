"""preregistration -- M3's pre-registration metric, as numbers (T123 boundary fix).

M3's bar: no slice ships whose acceptance postdates its implementation. This module owns
the MEASUREMENT of that practice; rendering lives with the callers.

WHY THIS MODULE EXISTS AT ALL (T123, ratified 2026-07-28): `audit_stats` used to live in
scripts/checkers/check_preregistration.py, and core/coord/method_drift.py reached OUT to it
by mutating the import path at call time -- an inverted dependency that the architecture
guardrail correctly refuses (`no-syspath-insert`). core/ is a library: it must never rewrite
the import path to reach the script layer. The direction is now right-way-round -- this is
the home, and both the boot reader (method_drift) and the ship gate import INWARD.

T123 also ruled the alternative out explicitly: the violation "may not be allowlisted
without this task's completion or Daniel's explicit ruling." Precedent: codex refused to
self-allowlist its own gate, and that refusal is now doctrine.

No outward imports. Nothing here may import from scripts/, agent/, or any harness.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Source = where impl lives. docs/, research/, chronicles/ ride along with registrations.
NONSOURCE_PREFIXES = ("tests/", "docs/", "research/", "chronicles/")


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def audit_stats(n: int, root: str = "") -> Dict[str, Any]:
    """M3 metric as NUMBERS: of the last N commits that ADD a tests/test_*.py, how many also
    touched source in the same commit (violations).

    Split out from the printing path deliberately. The wrap scorecard needs the RATE, and a
    reader that re-parses a rendered compliance line is fragile -- delimiters collide with
    content, and the number silently becomes whatever the formatting last did. Returns
    {total, clean, violations, pct, offenders}; callers render, this computes.
    """
    cwd = root or ROOT
    log = subprocess.run(
        ["git", "log", f"-n{n}", "--diff-filter=A", "--name-only", "--format=%x01%h %s"],
        capture_output=True, cwd=cwd, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, close_fds=True).stdout or ""
    total = viol = 0
    offenders = []
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
                                  capture_output=True, cwd=cwd, encoding="utf-8",
                                  errors="replace", stdin=subprocess.DEVNULL,
                                  close_fds=True).stdout or "").split()
        src = [f for f in map(_norm, touched) if f and not f.startswith(NONSOURCE_PREFIXES)]
        if src:
            viol += 1
            offenders.append((header, added_tests, src[:3]))
    ok = total - viol
    return {"total": total, "clean": ok, "violations": viol,
            "pct": (100.0 * ok / total) if total else 100.0, "offenders": offenders}
