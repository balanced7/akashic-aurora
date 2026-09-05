"""Doc-freshness guardrail -- the repo ROOT holds only living, intentionally-maintained docs.

Semantic Relationship: Guardrails enforce GeneratedTruthOverHandwrittenStatus

WHY THIS EXISTS
---------------
Pre-rename caps-docs (AGENT_ONBOARDING, SYSTEMS_ARCHITECTURE, SIGNAL_REFERENCE, ERROR_HANDLING_GUIDE,
...) and hand-written STATUS snapshots drift the moment code moves and quietly mislead the next agent
-- the exact problem the narrative spine replaces. Truth is generated:
    py agent_cli.py status      # live system + lesson/blocker counts
    py agent_cli.py story       # the narrative Atlas (chronicled from Beats + git)
    git log                     # the commit ground-truth
    docs/ROADMAP.md             # the living plan

POLICY (ALLOWLIST, not blocklist -- review DOC-02)
-------------------------------------------------
The old version only flagged STATUS/INVENTORY/CHECKPOINT-shaped *names*, so misleading docs that
didn't match those patterns (AGENT_ONBOARDING.md, SYSTEMS_ARCHITECTURE.md, ...) passed clean. Now:
  FAIL (exit 1) if any root-level *.md is NOT in the small allowlist of permitted living root docs.
New design/plan docs belong in docs/; retired docs belong in _archive/. The root stays minimal.

Run: py scripts/checkers/check_doc_freshness.py        (exit 0 = clean root, 1 = an unlisted root doc)
"""
import os
import sys
from pathlib import Path

# W161 (2026-08-14): DERIVED, not defaulted. This read the AI_SETUP env var with a hardcoded
# fallback -- the exact pattern core/paths.py exists to delete, and whose docstring already
# measured the reason: "0 machines with AI_SETUP actually set -- including the original one."
# With three worlds live the cost stopped being hypothetical: run from a twin, this guardrail
# scanned PRODUCTION's files and returned production's verdict, so a twin could not audit
# itself and a green result named the wrong world. Found when a class rename verified clean in
# alpha and the checker kept reporting the old name -- because it was reading prod. Third
# instance of this class in one arc, after core/paths.py itself and snapshot_knowledge.py.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.paths import repo_root as _rr
ROOT = _rr()

# The ONLY *.md files allowed at the repo root -- the agent's designated entry points.
ALLOWED_ROOT_MD = {"README.md", "AGENTS.md", "bootstrap.md", "CONTRIBUTING.md"}


def check() -> int:
    offenders = sorted(p.name for p in ROOT.glob("*.md") if p.name not in ALLOWED_ROOT_MD)

    print("=" * 60)
    print("DOC-FRESHNESS CHECK (root allowlist)")
    print("=" * 60)
    print("Allowed at root: " + ", ".join(sorted(ALLOWED_ROOT_MD)))
    print("Generated truth: `py agent_cli.py status` | `story` | `git log` | docs/ROADMAP.md\n")

    if offenders:
        print(f"UNLISTED ROOT DOCS ({len(offenders)}):")
        for n in offenders:
            print(f"  - {n}")
        print("\nFAIL: only living entry-point docs belong at the root; these drift and mislead.")
        print("      Move a design/plan doc to docs/, or retire it:  git mv <doc> _archive/")
        return 1

    print("PASS: the repo root holds only the allowlisted living docs.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
