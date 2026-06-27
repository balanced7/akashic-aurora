"""
Doc-freshness guardrail -- keep hand-written STATUS/INVENTORY snapshots from drifting.

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS
---------------
The project's "current state" used to live in hand-written snapshots (SYSTEM_STATUS.md,
ACTUAL_INVENTORY.md, PHASE_1_CHECKPOINT.md, ...). They go stale the moment code moves
and quietly mislead the next agent -- the exact problem the narrative spine replaces.
Generated truth now comes from:
    py agent_cli.py status      # live system + lesson/blocker counts
    py agent_cli.py story       # the narrative Atlas (chronicled from Beats + git)
    git log                     # the commit ground-truth
    docs/ROADMAP.md             # the living plan

This guardrail flags status-snapshot docs that have crept back so generated truth can't
silently drift again (strangler-fig: the generated story replaces the manual status doc).

Policy:
  - FAIL (exit 1) if a stale-pattern snapshot appears at the REPO ROOT -- that's the
    first thing an agent sees, and where drift does the most damage.
  - WARN (listed, exit 0 contribution) for snapshots elsewhere (e.g. docs/current/),
    so they're visible and trackable without blocking.
  - docs/_archive/ and _archive/ are exempt: retiring a doc THERE is the fix.

Run: py scripts/check_doc_freshness.py        (exit 0 = clean root, 1 = drift at root)
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))

# Basenames that denote a hand-written point-in-time status/snapshot (drift-prone).
STALE_PATTERNS = [
    re.compile(r".*STATUS.*", re.I),
    re.compile(r".*INVENTORY.*", re.I),
    re.compile(r".*CHECKPOINT.*", re.I),
    re.compile(r"CONTINUATION_.*", re.I),
    re.compile(r".*SESSION_SUMMARY.*", re.I),
    re.compile(r".*_COMPLETE\.(md|txt)$", re.I),
    re.compile(r"SLEEP_SAFELY.*", re.I),
]

# Exempt directories (retiring a doc here IS the remedy; deps live here too).
EXEMPT_DIRS = {"_archive", ".git", "node_modules", "__pycache__", ".pytest_cache",
               "patches", "session_briefings", "session_logs"}

# Explicitly-living docs that may match a pattern but are intentionally maintained.
ALLOWLIST = set()  # e.g. {"docs/ROADMAP.md"} -- none today


def _is_stale_name(name: str) -> bool:
    return any(p.match(name) for p in STALE_PATTERNS)


def _iter_docs():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXEMPT_DIRS]
        for fn in filenames:
            if fn.lower().endswith((".md", ".txt")) and _is_stale_name(fn):
                p = Path(dirpath) / fn
                rel = p.relative_to(ROOT).as_posix()
                if rel in ALLOWLIST:
                    continue
                yield rel


def check() -> int:
    root_hits, other_hits = [], []
    for rel in _iter_docs():
        (root_hits if "/" not in rel else other_hits).append(rel)

    print("=" * 60)
    print("DOC-FRESHNESS CHECK")
    print("=" * 60)
    print("Generated truth: `py agent_cli.py status` | `story` | `git log` | docs/ROADMAP.md\n")

    if other_hits:
        print(f"Snapshot docs outside root (visible, not blocking) -- {len(other_hits)}:")
        for rel in sorted(other_hits):
            print(f"  - {rel}")
        print("  -> prefer the generated story; archive to docs/_archive/ when truly dead.\n")

    if root_hits:
        print(f"ROOT-LEVEL STALE SNAPSHOTS ({len(root_hits)}):")
        for rel in sorted(root_hits):
            print(f"  - {rel}")
        print("\nFAIL: status snapshots at the repo root drift and mislead agents.")
        print("      Retire them:  git mv <doc> docs/_archive/   (truth is generated).")
        return 1

    print("PASS: no stale status snapshots at the repo root.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
