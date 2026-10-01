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
| G0 | CERTIFIED | d5f0615d..HEAD (G0 commits 9527fcc7..final ledger commit) | A: 5 phases x 1 round | VERDICT: PASS (P1-P5) | `certify.py G0`: CHECKS 13/13, TAMPER T1-T7 PASS (T7 binding: ran 7,426 vs g0 7,379, skipped 71 vs 71; T1-T6 not yet active), DRILLS 0/0, ORACLE 10/10 EQUAL (g0 vs head, 1 suite run). Pre-activation readings for later goals: T3 580 suppressions without a reason, T4 607 suppressions vs budget 843 (337,337 LOC) |
| G0.P1 | DONE | d5f0615d..9527fcc7 | A: 1 round | VERDICT: PASS | branch + linked worktree outside the main checkout; plan tracked via fast-forward to d5f0615d (sha256 2d1faff2); hooks not installed (D-G0-1); ledger, register, backlog, G0_BASE committed. Advisories ADV-007, ADV-008 |
| G0.P2 | DONE | 146a743c..1d897482 | A: 1 round | VERDICT: PASS | 1,619 tracked .py: 261 ARCHIVAL (proofs 261/261), 360 RUNTIME, 177 SCRIPT, 777 TEST, 44 TOOLING; 67 history files fail the proof and stay in scope; 236 __main__ modules, 127 argparse CLIs; 89 annotation-sensitive modules (protocol: ai_setup_mcp.py, 73 MCP tools); requirements consumers: CI, CONTRIBUTING, docs/DEPLOY.md, core/screenspace, scripts/gemini_web_login.bat (ADV-013); platforms: Windows (py), macOS/Linux (python3 / uv run), Python 3.11+ (developed on 3.11.9); tooling: .venv 3.12.3, CI 3.11, uv 0.12.21, configs pyproject.toml + pytest.ini + uv.lock, full suite = serial pytest over tests/ with REDIS_DB=15. Advisories ADV-013..015 |
| G0.P3 | DONE | e674063d..5e51c2df | A: 1 round | VERDICT: PASS | oracle.py + certify.py (stdlib only), 47 unit tests (EQUAL + DIFF per component, drill verdicts); checks G0 (13) and G1-G7 (40) registered before their work; G1-G7 checks are never executed before their goal starts (operator instruction, c844fff4). Advisories ADV-009..012 |
| G0.P4 | DONE | 3c1ae5dc..986bc018 | A: 1 round | VERDICT: PASS | g0 at d5f0615d: 3 suite runs of ~850 s, each 7,267 passed / 105 failed / 7 errors / 71 skipped / 23 xfailed (7,273 stable-pass, 111 stable-fail, 1 flaky); coverage agent 67.12, arsenal 85.35, core 73.90, scripts 34.54; 73 MCP tools; 5,897 public names; 15,537 assertions in 6,229 tests. Tools (scope 1,354 files, 333,907 lines): ruff target set 33,011 findings (stretch ANN 21,755, D 16,480, PL 7,695, ARG 1,664, TRY 1,569, FBT 911); ruff format would change 1,324 files at line length 100, 1,318 at 120; basedpyright standard 3,175 errors; ty 2,532. Ruff 0.16.9 renderer panic bisected to 2 files, formatter fine, no exclusion (ADV-005). g0 test ids rekeyed to hashed parameter text (ADV-016) |
| G0.P5 | DONE | c844fff4..141c1691 | A: 1 round | VERDICT: PASS | `certify.py G7 --drills`: 15/15 MISSED (gate absent), G7 checks never executed; `compare g0 g0`: ORACLE 10/10 EQUAL; selftest-d14: removing core.codex.lifecycle.is_active gives O5 DIFF. Snapshot steps now stream their logs (ADV-017) |
| G1.P1 | DONE | f9a89292..8d176759 (+ 245a91bb oracle --python) | A: 1 round | VERDICT: PASS | pre-registered 6 more G1 checks (6ab54739); pytest-randomly held off by `-p no:randomly` until G5.P1; [project].dependencies minus pytest and pre-commit, dev = the plan's 10 tools (prek replaces pre-commit), no locked runtime version moved; deptry clean over RUNTIME+SCRIPT (tests/ and the docs/, research/ history trees out: their imports were already unimportable at g0, O3), 26 sys.path siblings first-party, ignores with reasons (flvfx, bifrost, lupa, ml/browser lazy imports). Full oracle at 8d176759: 10/10 EQUAL (1 suite run). Commit types follow commitlint (no `build` type: plan `build(deps)` -> `chore(deps)`, D-G1-1) |
| G1.P2 | DONE | d0e9d8db..e8ffa7ad | A: 1 round | VERDICT: PASS | PF3 wheel check (uv pip compile --only-binary :all:, manylinux_2_28 x86_64 + win_amd64): 3.14, 3.13, 3.12 all pass. Oracle per candidate at 8d176759 (`oracle.py snapshot --python <v>`): 3.14 O4 DIFF 76 (argparse --help layout changed in 3.13) + O5 DIFF 41; 3.13 O4 DIFF 76; 3.12 O1+O3+O4+O5 4/4 EQUAL -> pin 3.12. requires-python stays >=3.11 (docs promise 3.11+); CI setup-python 3.12; settings.json -p 3.12 unchanged; DEPLOY states floor + pin. Full oracle at e8ffa7ad: 10/10 EQUAL |
| G1.P3 | DONE | e8ffa7ad..6772667c | A: 1 round | VERDICT: PASS | [tool.uv] package=false, required-version >=0.12, exclude-newer "7 days", default-groups ["dev"]. Fallback applied: the cooldown alone downgrades 14 locked packages (and the uv-add floors make it unsatisfiable), so each has an exclude-newer-package override to 2026-10-01 with a removal date 2026-10-02..08; no locked version moved. Fresh-clone `uv sync --locked`: PASS. Drills (verifier): D08 BIT, D09 BIT. Full oracle at 6772667c: 10/10 EQUAL |
| G1.P4 | DONE | 6772667c..5bb213fd | A: 1 round | VERDICT: PASS | pip consumers exist (G0), so requirements.txt + requirements/gemini-web.txt stay, GENERATED by scripts/generators/gen_requirements.py (uv export --frozen --no-hashes --no-emit-project --no-annotate [--only-group browser]); poe lock / lock-check; D08, D09 BIT. Phase-end oracle: the 5bb213fd run was corrupted by a one-bit flip in a run-tree file G1 never touched (O3 DIFF 1 + O1/O10 lost); see D-G1-3 |
| G1.P5 | DONE | 5bb213fd..cfe82d34 | A: 1 round | VERDICT: PASS | IC-0001 registered first; core.paths.python_launcher: AKASHIC_PYTHON -> uv run -> py (Windows) -> python3; scripts/githooks/pyrun (POSIX sh) + the 4 hook shims inline its chain; CI: pip install uv==0.12.21, uv sync --locked, every step `uv run python`; .mcp.json and settings hooks already uv run. Phase-end oracle at cfe82d34: 9/10, O7 DIFF 1 (agent_cli task list 378 -> 12 lines) = transient shared db-15 state seconds after another suite run; the same command prints 379 at 6772667c and at HEAD, and HEAD's O7 is 378 (D-G1-2) |
| G1.P6 | DONE | cfe82d34..6ef67ba2 (helpers 2c6cf238, 7e7607d4) | A: 1 round | VERDICT: PASS | poe tasks fmt, fmt-check, lint, lint-check, types, types-ty, lock, lock-check, deps, ci-lint, guardrails, test, test-fast, oracle, gate (each with help; ruff --config / basedpyright -p pyproject.toml). gate = lock-check, deps, guardrails, test-fast (37 s); fmt-check joins in G2, lint-check G3, types G4, ci-lint G5. guardrails: every checker held to its g0 exit code (0 worse); test-fast: smoke set + impacted, 12 s |
| G1.P7 | DONE | 6ef67ba2..c37c1d10 | A: 1 round | VERDICT: PASS | pytest.ini -> [tool.pytest.ini_options] (same testpaths, -q, -p no:randomly, filterwarnings, comments) + --strict-markers --strict-config; 7,524 ids before/after, same single collection error, identical except 3 volatile per-run ids (count 3 = 3). Also: D14 drill uses the shared venv (edf0369a, now BIT); run trees rehashed against their commit after checkout (c37c1d10) |
| G1 | CERTIFIED | f9a89292..HEAD | A: 7 phases x 1 round | VERDICT: PASS (P1-P7) | certify.py G1: CHECKS 17/17 PASS, TAMPER T1-T7 PASS (binding T1, T6, T7; T2-T5 bind from G2/G3), DRILLS 2/2 BIT (D08, D09; D12, D14 also BIT), ORACLE 10/10 EQUAL; fresh clone: uv sync --locked and uv run poe gate exit 0. Goal-end full oracle at c37c1d10 (2 suite runs): O1-O10 all EQUAL, ORACLE: 10/10 EQUAL (T7: ran 7,431 vs g0 7,379, skipped 71 vs 71) |
| G2.P1 | DONE | 5d5b8386..a84c9bb4 | A: 1 round | VERDICT: PASS | pre-registered 4 more G2 checks (e0421035). [tool.ruff]: target py311 (G1 floor); line-length 120 by data (with these settings 1,329 files change at 100, 1,323 at 120; G0 measured 1,324 / 1,318); extend-exclude = exactly the 261 ARCHIVAL files (4 dirs + 243 files); include *.py/*.pyi (Ruff 0.16 would also format code blocks in 151 .md files and pyproject.toml, I8); double quotes, docstring-code-format. T2 (ruff --show-files == in-scope set): PASS |
| G2.P2 | DONE | cae6bde1 | A: 1 round | VERDICT: PASS | Line-sensitive artifacts surveyed on an unformatted vs formatted scratch tree: every scripts/checkers/* output and every generator --check. Only line numbers moved (advertised_verbs, boundaries, ports, ui_contract, dual_authority traceback); no exit code changed, no finding count rose. One guardrail lost coverage silently: check_advertised_tools resolved 75 tools / 4 namespaces instead of 103 / 9 (regex `_fn\("` vs wrapped calls) -> fixed first (cae6bde1, output unchanged on unformatted source), pinned by check G2.P2.advertised-tools-coverage. gen_arch_index/doors/master_map/physics_sheet --check rc 1 before and after (stale since g0), gen_ports/gen_requirements rc 0. Regeneration commands: `uv run python scripts/generators/<gen>.py`; no regeneration commit needed. Historical docs citing file.py:NNN (docs/library/**) are records, not regenerated |
| G2.P3 | DONE | a84c9bb4..d8411943 | A: 1 round | VERDICT: PASS | 5913ce76 `style: apply ruff format repo-wide` (1,323 files, ruff 0.16.9, `Replay: uv run ruff format --config pyproject.toml`); .git-blame-ignore-revs lists it, blame.ignoreRevsFile set locally (5f8d80c7; CONTRIBUTING note in G5.P4); fmt-check joins gate (d8411943): gate = fmt-check, lock-check, deps, guardrails, test-fast, exit 0. One commit sufficed (no hooks installed, D-G0-1) |
| G2.P4 | DONE | a84c9bb4..47e30ea0 | A: 1 round | VERDICT: PASS | ast-equal 5913ce76^ 5913ce76: AST 1323/1323 EQUAL; replay identical (assert-mechanical-commits); D01, D05 BIT. The first goal-end oracle (d8411943) was stopped after suite run 1 showed 10 stable-pass tests failing: source-text pins broken by ruff's wrapping (e.g. `'add_parser("friction"' in cli`), not behaviour; fixed in 47e30ea0 (same asserts and literal tokens, whitespace-tolerant regex). Goal-end full oracle at 47e30ea0 (2 suite runs): O1-O10 all EQUAL, ORACLE: 10/10 EQUAL (O2: 1 format commit AST-equal; T7 ran 7,431 vs g0 7,379, skipped 71 vs 71); O6 no checker worse than g0 |
| G2 | CERTIFIED | 5d5b8386..HEAD | A: 2 verifiers (P1+P2, P3+P4) x 1 round | VERDICT: PASS (P1-P4) | certify.py G2: CHECKS 8/8 PASS, TAMPER PASS (binding T1, T2, T6, T7), DRILLS 2/2 BIT (D01, D05), ORACLE 10/10 EQUAL; fresh clone: uv sync --locked and uv run poe gate exit 0 |

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
- **D-G1-1 (commit types).** commitlint.config.ts enforces changelog.config.js types, which have
  no `build`; the plan's `build(deps|python|tasks)` commits use `chore(deps)` / `chore(config)` /
  `chore(tools)` instead (fcb7507a was reworded to 2ed8a4ec before any verification, I3).
- **D-G1-2 (phase-end oracles folded into the goal end).** Section 10 asks for a full oracle at
  every phase end. P1, P2, P3 were run (10/10 each). P4's run was corrupted (D-G1-3) and P5's
  showed one transient O7 line-count DIFF from shared db-15 state; at the operator's request
  to finish G1 promptly, P4-P7 are covered by the goal-end full oracle at HEAD c37c1d10 with 2
  suite runs. Every G1 change is class A and cumulative, so HEAD EQUAL covers each phase's
  changes; no phase-end run showed a DIFF attributable to a G1 change.
- **D-G1-3 (environmental bit flip).** In the P4 phase-end run tree, agent/harness/context.py
  line 276 read `{flagu{age_str}` instead of `{flag}{age_str}` ('}' 0x7d -> 'u' 0x75, one bit).
  The blob is intact (git fsck --full clean; P3/P5 trees and the worktree rehash clean), so
  the byte changed after checkout: a host memory/storage fault. Since c37c1d10 every oracle
  run tree is rehashed against its commit and refused on any mismatch. Operator was told to
  check the host's RAM/disk health.
