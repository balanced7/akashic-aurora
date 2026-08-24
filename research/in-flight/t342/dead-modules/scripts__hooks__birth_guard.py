"""Rule-13 birth guard (A1, T101) -- naked .md creation becomes unrepresentable at commit.

Spec: docs/library/design/20260701_artifact-substrate-the-reconciled-design_8ea728.md section 4 + docs/taxonomy-ergonomics-
reconciliation-2026-07.md. Genus: rule-8 mojibake guard (mirror.py pre-commit REFUSE);
the wrap census + audit library domain are the permanent backstops.

Posture (strangler-safe, per the reconciliation's migration window):
  ALLOW   docs/library/** (the door's own projections) · any README.md (generated) ·
          docs/UPPERCASE.md (crown/generated dress, LIBRARY law) · docs/_archive/**.
  REFUSE  any other NEW .md under docs/ -- knowledge is born through the door now:
          py agent_cli.py doc new (or --draft to dump-and-go).
  WARN    new .md under research/ or chronicles/ -- legal during the migration window
          (the corpus still lives there until A3/P3); flips to REFUSE at P3, or now
          with AKASHIC_BIRTH_GUARD=strict.
Env: AKASHIC_BIRTH_GUARD = off (skip, loud) | strict (WARN tier refuses too).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_CROWN = re.compile(r"^docs/[A-Z0-9_]+\.md$")
_TEACH = ("  -> knowledge artifacts are born through the door now: "
          "py agent_cli.py doc new --type <t> --title <x> [--draft]")


def classify(relpath: str) -> str:
    """Pure rule: 'allow' | 'refuse' | 'warn' for a NEW .md path (repo-relative, /)."""
    p = relpath.replace("\\", "/")
    if not p.endswith(".md"):
        return "allow"
    if p.startswith("docs/library/") or p.startswith("docs/_archive/"):
        return "allow"
    if p.endswith("/README.md") or p == "README.md":
        return "allow"
    if _CROWN.match(p):
        return "allow"
    if p.startswith("docs/"):
        return "refuse"
    if p.startswith("research/"):
        # P3 FLIP (2026-07-23 night, Daniel's deletion gate fired): the research zone's
        # corpus migrated to atoms; new loose research .md is refused like docs/.
        return "refuse"
    if p.startswith("chronicles/"):
        # P3b flip (2026-07-23 night): write-once records migrated to atoms; only the
        # four LIVE machinery projections exist as files (reprojected, never hand-born).
        if p in ("chronicles/memory.md", "chronicles/last-session-draft.md",
                 "chronicles/lessons.md", "chronicles/story.md"):
            return "allow"
        return "refuse"
    if p.startswith("charters/"):
        # charters/<agent>/CHARTER.md is the LAWFUL agent-contract home (LIBRARY canon);
        # loose charter files belong in atoms.
        return "allow" if re.fullmatch(r"charters/[a-z0-9_-]+/CHARTER\.md", p) else "warn"
    return "allow"


def staged_added() -> list[str]:
    r = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
                       cwd=ROOT, capture_output=True, text=True)
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def main() -> int:
    mode = os.environ.get("AKASHIC_BIRTH_GUARD", "").strip().lower()
    if mode == "off":
        print("[birth-guard] AKASHIC_BIRTH_GUARD=off -- SKIPPED (loud by design)")
        return 0
    refusals, warns = [], []
    for p in staged_added():
        verdict = classify(p)
        if verdict == "refuse":
            refusals.append(p)
        elif verdict == "warn":
            warns.append(p)
    if warns:
        tier = "REFUSED (strict mode)" if mode == "strict" else "warning (migration window; flips to REFUSE at P3)"
        print(f"[birth-guard] {len(warns)} new loose .md in research/chronicles zones -- {tier}:")
        for p in warns:
            print(f"  {p}")
        print(_TEACH)
        if mode == "strict":
            refusals.extend(warns)
    if refusals:
        print(f"[birth-guard] rule-13 REFUSED: {len(refusals)} new .md outside the door's homes:")
        for p in refusals:
            print(f"  {p}")
        print(_TEACH)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
