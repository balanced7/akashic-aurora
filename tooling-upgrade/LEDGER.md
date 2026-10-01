# Python tooling upgrade ledger (2026-10)

Status: current
Class: reference

The single source of truth across compaction and resume (plan section 9.6). On resume: read this
file, re-run `uv run python tooling-upgrade/certify.py <last DONE goal>`, then continue.

- **Plan:** docs/python-tooling-upgrade-plan-2026-10.md (sha256 2d1faff2...; committed on master
  by d5f0615d, identical to the operator's copy).
- **Branch / worktree:** `chore/tooling-upgrade-2026-10` at
  `/mnt/lnx-storage/projects/akashic-labs/aurora-tooling-wt` (outside the main checkout, I1).
- **G0 base:** d5f0615decac5f2449c59b18e3e3a3c6effe823c (tooling-upgrade/G0_BASE). The branch
  was created from master 589f5039 and fast-forwarded (no rewrite) to d5f0615d when the operator
  committed the plan to master before the branch had any commit of its own.
- **Pre-flight:** PF2-PF4, PF6 at their defaults. PF5: see decision D-G0-1 below.

## Status

| Goal.Phase | Status | Commits | Verifier rounds (A/B) | Verdict lines | Numbers and decisions |
|---|---|---|---|---|---|
| G0.P1 | IN PROGRESS | | | | worktree + branch created; plan present via fast-forward |
| G0.P2 | IN PROGRESS | | | | |
| G0.P3 | IN PROGRESS | | | | |
| G0.P4 | IN PROGRESS | | | | |
| G0.P5 | IN PROGRESS | | | | |

## Decisions

- **D-G0-1 (PF5, hooks).** The repo's hooks are NOT installed in the worktree. Evidence: with
  nothing staged on master d5f0615d, the pre-commit stage blocks (guardrail ratchet:
  check_boundaries 5 > baseline 3, check_comprehensibility 8 > 0, check_wiring 1 > 0; and
  `check_comprehensibility --fast` reports 3 drift FAILs), so installed hooks would block every
  commit. PF5 says to record this and continue without hooks, never `--no-verify`. Hooks are
  installed in no checkout of this repo (`core.hooksPath` unset). Consequence: drill D13 is N/A
  (G7 needs 14/14). Raised with the operator, who chose "No hooks, PF5 exception" on
  2026-10-01; see BACKLOG ADV-001.
- **D-G0-2 (baseline ref).** The g0 snapshot is taken at the G0 base d5f0615d itself (pure
  master, before any file of this effort exists), in a throwaway worktree with its own
  `uv sync --frozen` venv and REDIS_DB=15.
- **D-G0-3 (commit scopes).** The plan's `docs(plan)` / `chore(tooling)` / `test(tooling)` scopes
  are not in the commitlint scope enum (changelog.config.js), and G0 may not edit that file, so
  G0 commits use no scope (`chore: ...`, `test: ...`), which commitlint accepts.
