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
| G3.P1 | DONE | e7319838..9e9511a9, 891d1636..e9c85442, b5a886d3..957a55e6, ea9b706c | A: 3 rounds (with P2-P4) | round 1 FAIL (3: D14 missed; commitlint header/Replay lengths); round 2 FAIL (1: SUPPRESSIONS.md stale after the D14 fix; others CLOSED, lengths under D-G3-3); round 3 VERDICT: PASS | Pre-registered zero set = target minus PTH/BLE/T20/S/N (D-G3-1, operator choice; IC-0003), 10 more G3 checks, IC-0002/0004. Safe waves, one family per commit with Replay (`sh -c "ruff check --select <F> --fix --exit-zero && ruff format"`): I (562 files), UP (390), F401 outside the 76-file hand set (518; no removed name read elsewhere: reverse import graph + dotted-name search), C4, PIE, RUF (RUF100 excluded), SIM, PT, RET (ISC/FLY had no safe fix), then F/W/B and second UP/I passes; RUF100 in P4 (ea9b706c, `--fixable RUF100`; a first run with `--select RUF100` stripped every noqa and was reverted, 441462d0, ADV-037). Checkpoint full oracle after I/UP/F401 (9e9511a9): ORACLE 10/10 EQUAL (O5 annot items covered by IC-0002) |
| G3.P2 | DONE | de4e0afd, b7cf0c9d, 8b5d0711 | B: 2 reviewers x 2 rounds | round 1: FAIL (1 blocking: B011 lowered O9 for 8 tests) and FAIL (2 blocking: deepseek_chat subprocess re-export, openai probe — both from D1); round 2: VERDICT: PASS (all 4 closed) | Unsafe-but-mechanical rules per directory batch (tests/, core/, rest) with Replay: PT018, UP031 (literal tuples only), SIM105, RUF059, ISC004, RUF005, B905, C408, PT006, E731, RUF007, RET504, SIM1xx/2xx, C4xx, B011, PERF102, RET503, FLY002, B007, PT022, RUF022, ICN001, W293. Fixes: c5725577 (pytest.fail, restored pins, private_plane split), f2beccd0 (deepseek_chat), 38e53b2c (3 vacuous asserts dropped). No PTH (ratcheted) |
| G3.P3 | DONE | 772f2960 (D1), 093dbe00 (D6), 0c06057e..b4ba8688 (B2), 11d92f65-cherry..a040c189 (B3), d8b9e53b..4ac32cd1 (B1), B4 cherry..f2beccd0, 4cce1ce9, 0f15ac32, 62e863db (D7), b8d4a412 (D8) | B: one reviewer per batch (+round 2) | D1: PASS after round 2; B1: VERDICT: PASS; B2: VERDICT: PASS; B3: FAIL (1: SIM112 env key case) -> round 2 VERDICT: PASS; B4: VERDICT: PASS; D7: VERDICT: PASS; D8: VERDICT: PASS | 4 worktree-isolated generators (B1/B2 tests, B3 core/agent/root, B4 research/scripts/arsenal/docs) + main session (tooling-upgrade/, D1, D7, D8). ~2,900 hand findings to 0; 86 new noqa with reasons. E722: 209 sites, all in archived/dead code, -> `except Exception:` (IC-0004; none relied on catching KeyboardInterrupt/SystemExit). 9 LATENT undefined names suppressed and handed to G4.P2 (ADV-033, ADV-034). G2's formatter had joined one deliberate anti-scanner split ("best-" "practices"), restored (ADV-031). D7/D8: the goal-end oracle at 61ae0081/1021591b showed O1/O3/O5 DIFFs from B4's runner edits (top-level suppress blocks un-probeable, try/except source pins, walrus-bound HERE/REPO/ROOT); restored |
| G3.P4 | DONE | 61ae0081, cc3bc7d3, ba15d03f, 476bdcef | A: 3 rounds (with P1-P3) | round 3 VERDICT: PASS | lint-check joins gate (gate = fmt-check, lint-check, lock-check, deps, guardrails, test-fast); RUF100 on (RUF in select, ratchet families' noqa kept via lint.external); every noqa has a rule and a reason (T3: cc3bc7d3, comment-only, AST-equal except 2 noqa comments inside string literals and the D06 drill string split); SUPPRESSIONS.md 556 rows / budget 934 (T4). Ratchet set from G3's end counts (D-G3-2): ANN 22148, ARG 1702, BLE 2449, D 16574, FBT 928, N 808, PL 7750, PTH 5256, S 1498, T20 3968, TRY 1582 (vs G2 HEAD: BLE +26 from E722 -> except Exception and D7's restored guards, S110 -206, PTH +91 from E402 path inlining, ANN/ARG/D/N802 from lambda->def, PLC0414 +19 from `X as X`, TRY003 +11) |
| G3 | CERTIFIED | 1a38090b..HEAD | A: 3 rounds; B: one per class-D and unsafe-fix batch (+round 2 where FAIL) | VERDICT: PASS (A round 3; B: D1+P2 round 2, B1, B2, B3 round 2, B4, D7, D8) | certify.py G3 at 42afaa5a: CHECKS 17/17 PASS, TAMPER T1-T7 PASS (T3 every noqa has a reason; T4 556/934), DRILLS 4/4 BIT (D02, D03, D06, D14), ORACLE 10/10 EQUAL (2 suite runs; O5 intended IC-0002/IC-0005); ruff check --statistics: no findings; fresh clone: uv sync --locked and uv run poe gate exit 0 (gate now includes lint-check). Zero set per D-G3-1 (PTH, BLE, T20, S, N ratcheted); 9 latent NameErrors handed to G4.P2 (ADV-033/034); D14 gate fixed to apply the register (31b39eae); commitlint lengths in G3 history recorded (D-G3-3) |
| G4.P1 | DONE | 0dca155c, 045832c4, c6f86514 | A: with P2-P4 | see G4 | Pre-registered 11 more G4 checks + certify assert-types-config / assert-strict-islands / assert-suppressions (T3 at G4 strength + T4; poe types runs it after basedpyright, which is what makes D07 bite). [tool.basedpyright]: standard everywhere, tests included (basic measured: removes only 101 of 2,665 errors, so no executionEnvironments split), pythonVersion 3.11, venvPath/venv .venv, the ruff ARCHIVAL exclude list + git-ignored oracle snapshots, extraPaths for bare-name sibling imports, enableTypeIgnoreComments, reportUnnecessaryTypeIgnoreComment = error; no reportMissingModuleSource override needed (3 warnings only). [tool.ty]: same scope. First count: basedpyright 2,665 errors in 1,359 files (1,358 inventory files + G1's gen_requirements.py); ty 2,221. IC-0006 (annotation corrections), IC-0007 (narrowing only on unreachable branches) |
| G4.P2 | DONE | ddaa2320..02c23f17 (batches A, C, T1-T4, R, S + integration 56d10aa9, b70ad492, cf34c383, 0de93365) | B: one reviewer per batch (+round 2 for T1) | A: VERDICT: PASS; C: VERDICT: PASS; T1: FAIL (1: narrowing assert inside an except that records str(e), rb25_drill4) -> fixed cf34c383 -> round 2 VERDICT: PASS; T2: VERDICT: PASS; T3: VERDICT: PASS; T4: VERDICT: PASS; R (+56d10aa9, b70ad492): VERDICT: PASS; S (+0de93365): VERDICT: PASS | 8 worktree-isolated generators (<=4 concurrent, disjoint batches: arsenal/agent/root; core; tests x4; t342 dead modules; scripts/docs/research) + main-session integration. 2,665 -> 0 basedpyright errors. Fix order per plan: 13 latent bugs fixed, each with its own commit, a regression test (tests/test_g4_latent_*.py) and an INTENDED_CHANGES entry with fix_commit/regression_test (IC-0008..IC-0020; certify assert-latent-regressions: 13/13 fail on parent, pass on HEAD), incl. the 6 ADV-033 agent_cli NameErrors and ADV-034 gemini_chat smoke; annotation corrections (IC-0006); narrowing via assert in tests and cast/isinstance in runtime code (IC-0007); residue as `# pyright: ignore[rule]  # reason`. Judgement-call defects left LATENT-suppressed and listed (ADV-038, ADV-041: Discord guest replies never post because GuestReplyTracker.poll() lacks on_drop - urgent for the owner). Suppressions 555 -> 763 rows / budget 935 (T4); R's archived dead modules alone needed 106 (57 unresolvable imports of uninstalled packages/archived modules). Ratchet flat (FBT001 on 17 positional flags via `noqa: FBT001, RUF100`) |
| G4.P3 | DONE | cd1995de, 7734874d, 221393c6, ddaa2320 | B: VERDICT: PASS (batch X) | VERDICT: PASS | `# pyright: strict` on the 5 Python files this effort wrote: tooling-upgrade/oracle.py, certify.py, pytest_plugin/aurora_oracle_plugin.py, tests/test_tooling_upgrade_oracle.py, scripts/generators/gen_requirements.py: 2,127 strict errors -> 0, annotation-only (stdlib-only and Python 3.11+ kept; --help output byte-identical; oracle unit tests 52 passed before and after). certify.py assert-strict-islands PASS |
| G4.P4 | DONE | 0efd8d94, 6912cd1e | A: with P1-P3 | see G4 | `types` joins gate (gate = fmt-check, lint-check, types, lock-check, deps, guardrails, test-fast). `poe types-ty` (informational): ty 0.0.84 reports 856 diagnostics at 02c23f17 (2,221 at G4 start); ty is not 1.0, gate stays basedpyright. Drill trees now get the project .venv (6912cd1e: basedpyright reads venv relative to the tree), so D04 and D07 BIT. Commit-message lint: D-G4-1 |
| G4 | CERTIFIED | bf8f8e7a..39f987e1 | A: 1 round; B: one per batch (X, A, C, T1 +round 2, T2, T3, T4, R, S) | VERDICT: PASS (A round 1; every B batch PASS, T1 after round 2) | certify.py G4 --drills at 39f987e1: CHECKS 16/16 PASS, TAMPER T1-T7 PASS (T4 763/940; T7 ran 7449 vs g0 7379, skipped 71 vs 71), DRILLS 2/2 BIT (D04, D07), ORACLE 10/10 EQUAL (2 suite runs; O5 intended IC-0002/0005/0006). poe types: basedpyright 0 errors, 13 warnings, no baseline; assert-latent-regressions 13/13. A first full oracle at 6912cd1e caught one O1 regression (test_r7: the two claude_pretooluse hook copies diverged between batches A and S), fixed in 39f987e1 and re-snapshotted. Advisories: IC entries land right after their fix commits (they record the fix SHA); D10/D11/D15 red-before-fault for G5. ty 856 (informational) |
| G5.P1 | DONE | 0a498377, e522a0da, 4f30cc9b | A: with P2-P4 | see G5 | Experiments (tooling-upgrade/EXPERIMENTS-G5.md, certify assert-experiments): pytest-xdist REJECT (2/2 full runs aborted at collection: time-stamped parametrize ids differ across workers, import-time registry race, shared db-15 flush; test-fast: smoke set 1 s serial vs 2 s, 60-file selection 70 s -> 31 s but a new failure in 2/3 xdist runs), so suite and test-fast stay serial; pytest-randomly REJECT (seed 1 O1 DIFF skips 129 > 71, seed 2 DIFF skips 267 and run 7261 < 7379, seed 3 EQUAL), stays installed with -p no:randomly, 298 order-dependent ids in order-dependent-tests.txt (ADV-042); --doctest-modules REJECT (0 doctests in 360 RUNTIME modules, exit 5); coverage ADOPT: poe test = snapshot suite O1+O10 then compare g0 (0.5 pp ratchet), [tool.coverage.run] branch + O10 sources. Oracle plugin writes its record from the xdist controller only |
| G5.P2 | DONE | 15d53088, ba170f61, 02c9fac5, c0e78d38 | B: VERDICT: PASS | see G5 | .pre-commit-config.yaml (prek): ruff-check --fix and ruff-format (types_or python/pyi: the hooks' default markdown type rewrote 151 .md files on the first run, backed out by reverse patch), uv-lock, uv-export x2 (one per generated requirement file; gen_requirements now renders uv's own --output-file text so hook and lock-check agree byte for byte, IC-0022), check-toml/yaml/merge-conflict/added-large-files, zizmor --offline, actionlint (actionlint-py); every rev a full SHA from git ls-remote with its tag; exclude = the ARCHIVAL list (certify assert-precommit-config checks it matches every ARCHIVAL file and no in-scope file). `uv run prek run --all-files` exit 0. scripts/githooks/pre_commit.py runs prek over the staged files as a backstop stage: finding -> block, missing prek/config/crash -> loud warning (IC-0021); tests/test_pre_commit.py -k prek (6 tests). Never prek install |
| G5.P3 | DONE | c7566971, 64964ab3, 766a4009, c1068581, 6164804f, fd8bb739 | A: with P1, P2, P4 | see G5 | ci.yml: permissions contents: read, concurrency cancel-in-progress, timeout-minutes per job, actions/checkout v7.0.1 and astral-sh/setup-uv v10.2.0 pinned by SHA (git ls-remote) with persist-credentials false / enable-cache, uv sync --locked; jobs gate (poe gate, then the 5 pre-G5 guardrail steps with their names and comments, each `poe guardrails --only <checker>`, held to g0: 3 of the 5 were already red at g0), test (Redis service + env kept; poe test), ty (continue-on-error), windows-smoke (windows-latest, continue-on-error; defined, not executed), ci-lint. dependabot.yml: uv + github-actions, weekly, cooldown 7 days, minor+patch grouped. poe ci-lint: zizmor over .github (dependabot.yml too), actionlint, SHA pins, and assert-workflow-permissions (zizmor's default persona let a single-job write-all through: D11 had missed). Auditor-persona leftover: unpinned redis:7 service image (as before G5). certify assert-ci-replay replays every Linux job's run: steps in a fresh clone |
| G5.P4 | DONE | 4332052f..63d8b05c, 843054f8..e290e8e3, cbb2d0b1..b0a84aac, a591aaa8, c9298d4c, e33c00c5 | B: VERDICT: PASS (IC-0023) | see G5 | README, CONTRIBUTING, AGENTS, docs/DEPLOY lead with uv sync / uv run poe gate / uv run poe test, py as the Windows fallback; CONTRIBUTING adds daily commands, hooks (never prek install), never --no-verify, blame-ignore setup, the suppression policy (assert-docs-uv PASS). Generated docs regenerated by their own generators (one Replay commit each) and judged by each generator's --check (assert-generated-docs). Latent fix IC-0023: gen_prior_art_register run as a script wrote `py` where check_comprehensibility renders `uv run`, so PRIOR_ART.md always read stale (regression test fails on parent, passes on HEAD) |

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
- **D-G3-1 (G3 zero set).** Measured at G2 HEAD 1a38090b with the plan's target set: 29,769
  findings in 1,312 files (safe fix 9,079, unsafe fix 7,497, no fix 13,048), and T4 room for
  ~320 new suppressions (607 exist, budget 927). PTH, BLE, T20 and S cannot reach zero inside
  T4 (S603/S607/S310 need ~550 suppressions alone), and N802 on test names cannot be fixed
  without changing pytest node ids (O1). The operator chose (2026-10-02) to move PTH, BLE,
  T20, S and N into the stretch ratchet with D, ANN, ARG, FBT, TRY, PL (IC-0003). The zero
  set is the rest of the target set. RUF100 keeps the ratchet families' existing `noqa`s via
  `lint.external`.
- **D-G3-2 (when the ratchet is set).** tooling-upgrade/ratchet.json was first written at the
  start of G3 (e7319838) with G2-HEAD counts. Plan G3.P4 sets the stretch counts from Ruff's
  `--statistics` at the end of G3, and zero-set fixes move them: lambda->def (E731) adds ANN/D/
  N802/ARG findings for the new defs, f-strings from UP031 add TRY003, explicit `X as X`
  re-exports add PLC0414, contextlib.suppress lowers BLE001/S110. So the P4 values replace the
  e7319838 values, and the ledger's G3.P4 row lists the per-rule delta from G2 HEAD with its
  cause. From G3.P4 on they never rise.
- **D-G3-3 (commitlint footer and header lengths in G3 history).** Verifier A (G3 round 1)
  ran commitlint over 1a38090b..HEAD: the 21 G3 class-C commits carry a `Replay:` footer line
  longer than commitlint's 100-character footer-max-line-length (the plan's Replay convention
  puts the full ruff command, with its rule list, on one line), and 62e863db's header is 97
  characters (limit 96). G0-G2 history passes. History cannot be rewritten (I3: no rebase, no
  amend of verified commits), so these stay as they are and are recorded here; nothing is
  pushed (I2), so the operator can squash or reword before publishing. From here on every
  commit is checked with commitlint before verification, and Replay lines stay within 100
  characters (long rule lists go through a committed script).
- **D-G4-1 (commitlint scope `tooling` in G4 history).** commitlint over bf8f8e7a..6912cd1e
  flags 13 G4 commits: 11 use the scope `tooling` (plan §18's convention, but the repo's
  scope-enum has no `tooling`; earlier goals used `chore:` without a scope or `global`), two
  headers are 99-100 characters (limit 96: a8201532, 0de93365) and one subject is
  sentence-case (10553637, "VFX"). As with D-G3-3 the history is not rewritten (I3), nothing is
  pushed (I2), and the operator can reword before publishing. From here on tooling commits use
  `chore:` (no scope) or an allowed scope (`tools`, `global`), checked with commitlint first.
- **D-G5-1 (commit-message lint).** 766a4009 (`ci: rebuild the workflow ...`) has one body line
  over commitlint's 100-character limit; it is not HEAD and cannot be reworded without a rebase
  (I3), so it stays, like D-G4-1. Every later G5 commit message was linted before committing.
- **D-G5-2 (a registered check that no tree can satisfy).** The final G5 certificate (HEAD
  4aa75b99) failed only G5.hook-stage-test: its command passes `-q` on top of the `-q` in
  pytest's addopts, and at verbosity -2 pytest prints no summary line, so expect_stdout
  "passed" cannot match even though all 6 tests pass. Checks are append-only, so it is not
  edited: G5.hook-stage-test-summary supersedes G5.hook-stage-test, with the same phase, expect,
  expect_stdout and tests and one `-q` fewer. certify.py accepts a supersession only when the
  command drops nothing but verbosity flags, the successor was registered later, and this line
  names both ids; the old check still runs and is printed as SUPERSEDED in the certificate.
  Round-2 verifier blocking B1 narrowed the rule: the dropped flags must be pytest's own (not
  `git diff --quiet` or `grep -v`, not an option's value as in `-k -q`), and every key but id
  and cmd, timeout_s included, must match.
  Round 3 (blocking: `uv run --with pytest git ...`, `-m pytest` inside `python -c`, `pytest.sh`)
  closed the rule: pytest is recognised only by an exact launch prefix (PYTEST_LAUNCHERS). The
  supersede mechanism was new work after G5.P2 passed, and its own verify loop used rounds 1-2
  (FAIL, FAIL); the next verifier is that loop's third and last round under section 9.3.
  Round 3 also failed (a `-q` after `--` is a path). Three rounds failing on one criterion
  triggers the phase Fallback (9.3). G5's written Fallback (experiments, zizmor ignores) does not
  cover it, so the Fallback was derived: drop the general rule and pin each supersession
  literally (certify.PINNED_SUPERSESSIONS: G5.hook-stage-test -> G5.hook-stage-test-summary,
  both argvs token for token). No rule is left to bypass, so verification is one finite
  question: is this pair a non-loosening? Rounds 1-3 established that empirically for this
  argv (the dropped -q directly follows `-m pytest`; at verbosity -2 only the summary line is
  lost).
- **D-G5-3 (the G3 stretch ratchet in G5).** G5's checks never ran `assert-ratchet G3`. The G7
  dry run found that G5's new code had raised 8 families: ARG +3, BLE +1, D +38, PL +27, PTH +10,
  S +6, T20 +12, TRY +1 versus 17ea7e48, where the ratchet passes. G5.stretch-ratchet and
  G7.stretch-ratchet were registered first (99f44f23). Real fixes (docstrings, pathlib, named
  constants, helper splits, narrowed except, module imports) took every family to its G3 count
  or below except S and T20, whose remaining findings the G5 mandate itself requires. The prek
  stage must spawn prek, and the certificate must print CI-replay evidence. Those take §12
  suppressions with a rule and a reason: 2 x `noqa: S603` (threat-model reasons, as G3.P3
  prescribes for S) and 13 x `noqa: T201` on the CLI output lines G5 added (the rationale the
  scripts/** T20 ignore records: these programs print to their user by design). They are the
  first T201/S603 noqa in the repo, listed in SUPPRESSIONS.md (780 rows, within T4) for the
  operator's review. The ratchet now passes: ARG 1685, D 16513, PL 7746, S 1498, T20 3967.
- **D-G5-4 (generated-doc and replay comparisons are exact).** A tolerance for gen_physics_sheet's
  "> Derived at <sha>." stamp (assert-generated-docs, then the replay proof) failed three verifier
  rounds in a row: prefix-skipped diff headers, then diff-text parsing (renames, modes, binary),
  then decoded-text comparison (CR, invalid bytes). Under 9.3 that is the Fallback; G5's written
  one does not cover it, so it was derived: no general tolerance at all.
  - assert-generated-docs judges a generator with a `--check` by that `--check`, its own freshness
    verdict, which accounts for its own HEAD stamp. A generator without one is re-run in a drill
    tree, and `git status` there must be empty.
  - The replay proof requires git's exact tree equality. The one commit that cannot replay
    exactly, eec0d183 (PHYSICS generated at c0e78d38, two commits before it landed), is pinned
    in certify.PINNED_REPLAY_STAMPS. It passes only if swapping its one literal stamp
    (00c842bf -> c0e78d38) makes the tree equal to the commit. Later PHYSICS regenerations
    (53ad5418) replay exactly.
  Rounds 1-2 also closed the archival proof's exclusion-list handling: tomllib entries, count-based,
  failing closed on any backslash. Round 3 found nothing in it after a 56,704-case fuzz.
