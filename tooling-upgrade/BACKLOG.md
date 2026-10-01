# Advisory backlog

Status: current
Class: reference

ADVISORY verifier findings and observations that never fail a phase (plan section 9). A later
goal may harden any of them.

| Id | Raised in | Finding | Suggested owner |
|---|---|---|---|
| ADV-001 | G0.P1 | The repo's pre-commit stage fails on `master` itself with nothing staged: the guardrail ratchet (boundaries 5 vs baseline 3, comprehensibility 8 vs 0, wiring 1 vs 0) and `check_comprehensibility --fast` (3 drift FAILs, stale references in docs/SHELVES.md). It also regenerates and stages 5 derived docs (docs/MODULE_INDEX.md, MAP.md, PHYSICS.md, DOORS.md, PRIOR_ART.md) on every commit; they are stale on master and PHYSICS.md embeds the HEAD sha. Hooks are not installed in any checkout (core.hooksPath unset). | repo owner |
| ADV-002 | G0.P1 | A full suite run inside a checkout mutates it: it rewrote the tracked `data/verb-registry/deepseek.json` and an untracked `docs/*.md` file disappeared during the run (culprit test not isolated). The oracle runs every suite in a throwaway worktree and records `tree_side_effects` per run in O1. | G5 (test tooling) |
| ADV-003 | G0.P2 | 17 argparse entry points exit 1 under `--help` when run as `python <path>` (relative imports or `core` not on sys.path, e.g. arsenal/band.py, core/coord/conductor.py). Recorded as-is in O4; they work as `python -m`. | G6 or later |
| ADV-004 | G0.P2 | `scripts/generators/gen_doors.py --help` rewrites docs/DOORS.md (side effect under --help); recorded N/A in O4 per the G0 Fallback. | repo owner |
