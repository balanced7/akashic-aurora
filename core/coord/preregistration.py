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
    # ``A*`` is Git's all-or-none diff filter: keep commits containing an added
    # path, but emit every touched path in those commits. That gives us both the
    # candidate set and its source co-travelers in one stable snapshot. The old
    # implementation followed this log with one ``git show`` per candidate;
    # boot calls this audit, so its latency grew with the audit window.
    log = subprocess.run(
        ["git", "log", f"-n{n}", "--diff-filter=A*", "--name-status",
         "--format=%x01%h%x09%s"],
        capture_output=True, cwd=cwd, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, close_fds=True).stdout or ""
    total = viol = 0
    offenders = []
    for block in log.split("\x01"):
        lines = [line.rstrip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        header = lines[0].replace("\t", " ", 1)
        touched = []
        added_tests = []
        for row in lines[1:]:
            columns = row.split("\t")
            status = columns[0]
            paths = [_norm(path) for path in columns[1:] if path]
            touched.extend(paths)
            added_tests.extend(
                path for path in paths
                if status.startswith("A")
                and path.startswith("tests/test_")
                and path.endswith(".py")
            )
        if not added_tests:
            continue
        total += 1
        src = [path for path in touched
               if path and not path.startswith(NONSOURCE_PREFIXES)]
        if src:
            viol += 1
            offenders.append((header, added_tests, src[:3]))
    ok = total - viol
    return {"total": total, "clean": ok, "violations": viol,
            "pct": (100.0 * ok / total) if total else 100.0, "offenders": offenders}
