# Python stack migration plan (2026-10)

**Status:** ready to execute. **Written:** 2026-10-01. **Executor:** a Claude Code session driven by `/goal`.
**Target:** Aurora's Python tooling moves onto the 2026 stack: uv for dependencies and environments, Ruff for
format and lint, basedpyright for types with ty alongside, pytest, Poe the Poet as task runner, prek hooks,
and hardened CI. Throughout, the repo keeps its own guardrails, its git-hook framework, Windows support and
multi-agent safety intact.

This is a point-in-time plan (lowercase, dated name, per docs/INDEX.md). It is written so that a
generator agent can execute it phase by phase and a separate verifier agent can independently check each
phase, with every acceptance criterion registered *before* the work (method baseline M3) and a drill that
proves the acceptance check can fail (M4).

---

## 0. How to use this document

1. Read sections 1–4 once, fully. They hold the invariants, the baseline facts and the
   generator/verifier protocol. Every phase depends on them.
2. Execute phases **P0 → P12 in order**. Do not start a phase until the previous phase's exit gate has
   a PASS verdict from a fresh verifier (section 4).
3. After every phase, append a row to the **Progress log** (section 7) and commit it with the phase's work.
   If the session is compacted or resumed, the Progress log is the source of truth for where you are.
   Re-verify the last DONE phase's exit gate before continuing.
4. Every claim of success must be backed by the command that proves it and the verbatim tail of its output
   **in the transcript**. The `/goal` evaluator can only read the transcript; it cannot run anything.

### Pre-flight decisions (the human fills these in BEFORE starting `/goal`)

- **D1. The comprehensibility gate is already red.** On 2026-10-01, `check_comprehensibility.py` reports 8
  pre-existing drift FAILs. Five are stale generated docs (MODULE_INDEX, PHYSICS, MAP, DOORS, PRIOR_ART),
  which P10 regenerates with their own generators. Three are the stale-ref check: the `REF_ALLOWLIST`
  exemption for `docs/security-amendment-deepseek-scoped-admin-2026-07-22.md` **expired 2026-09-30**, and
  docs/ARCS.md and docs/SHELVES.md still reference that path. `scripts/githooks/pre_commit.py` runs the
  stale-ref check at commit time and fails closed on real drift. So **once P3 installs the hooks, every
  commit is blocked** until this is resolved. Earlier renewals of this exemption were the operator's call,
  so the executor must not decide it alone. Choose one:
  - [ ] **D1-a:** the executor may renew the exemption for 14 days, with reason
    "renewed for python-stack migration; operator to re-verify", as its own `chore(checkers): …` commit
    before P3 step 6.
  - [ ] **D1-b:** the executor fixes the root cause instead: repoint the reference at the real file under
    docs/library/design (which also changes the ARCS and SHELVES generator inputs), in its own commit, and
    stops as BLOCKED if that requires editing another seat's uncommitted store data.
  - [ ] **D1-c:** neither. Then P3 step 6 does not install the hooks; S13's `core.hooksPath` sub-check
    is waived and the final report states the hooks were not activated because of D1.

  If no box is ticked, the executor takes **D1-c**.

---

## 1. Invariants (never violate; a violation fails the whole goal)

- **I1. No lost work.** Never run `git reset --hard`, `git clean`, `git checkout -- <path>`, `git stash drop`,
  `git push --force`, or anything else that discards uncommitted or committed work. P0 records a manifest
  of the pre-existing dirty tree. Every file in it must still exist with its content preserved (committed
  in P0, or untouched).
- **I2. Nothing leaves the machine.** No `git push`, no PR, no package publish, no issue filed upstream.
  Work happens on the local branch `chore/python-stack-2026`. The human pushes.
- **I3. No new test failures.** The set of failing or erroring test node IDs at the end must be a subset of
  the P0 baseline set. The number of collection errors must be ≤ the baseline.
- **I4. No guardrail regression.** Every script in `scripts/checkers/` must exit with the same or a better
  code than it did in P0 (0 stays 0; a baseline non-zero may become 0). Ratchet baselines (for example
  the guardrail ratchet baseline under state/ci) may only go **down**, and only via their own
  regeneration commands, never by hand-editing numbers upward.
- **I5. Tests never touch canonical Redis db 0.** Run the suite with `REDIS_DB=15` or the embedded server,
  as CONTRIBUTING.md requires.
- **I6. Cross-platform.** The Windows machine (formerly `E:\AI-Setup`) must keep working. No POSIX-only
  calls in Python code paths, and no OS-specific path literals (the repo rule: derive paths with
  `core.paths` or read them from env vars). Shell hook shims must work under Git for Windows' `sh`.
- **I7. History is read-only.** Do not edit `research/`, `docs/library/`, `docs/_archive/`, `chronicles/`,
  `fences/` or `session_logs/`. Exclude them from formatters and linters instead.
- **I8. Peer safety.** Before editing a shared path, check peer locks (`uv run agent_cli.py locks`) and
  take one (`uv run agent_cli.py lock <id> <path>`); release when done. If a peer holds a lock on a path
  a phase needs, wait or skip that file and record it. Never override.
- **I9. Mechanical commits are pure.** The repo-wide format commit (P4) contains only formatter output.
  The autofix commits contain only one rule family each. No hand edits ride along.
- **I10. Conventional Commits.** Every commit message passes `commitlint.config.ts` conventions
  (`type(scope): subject`). Commits are atomic: one concern each.
- **I11. No global installs.** Use `uv`, `uv run` and `uvx`. Never `pip install --user` or `sudo`. If you
  ever sandbox an installer, unset `XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_BIN_HOME`, because this
  host exports them and the uv installer honours them over `HOME`.

---

## 2. Current state (measured 2026-10-01, before any change)

| Area | Today | Notes |
|---|---|---|
| Python | `.venv` on 3.12.3; hooks run `uv run -p 3.12`; CI uses 3.11; `requires-python >=3.11` | Three different answers. No `.python-version`. |
| Dependencies | `pyproject.toml` (untracked, `package = false`) + `uv.lock` (untracked) + hand-kept `requirements.txt` + `requirements/gemini-web.txt` | Comments say "keep the two in step" by hand. `pytest` and `pre-commit` sit in **runtime** deps. Groups `ml` and `browser` exist. |
| uv | 0.12.21 on this host | `exclude-newer` cooldown and `required-version` not set. |
| Format | none enforced | `ruff format --check` (defaults): **~1,725 files would be reformatted**, ~1,713 already formatted (including untracked trees). One file makes `ruff format --check` panic in the default diff output ("Annotation range … beyond the end of buffer"); `--output-format concise` avoids it. |
| Lint | none enforced | Ruff 0.16.9, `--select E,F,I,UP,B`: **56,134** findings, of which E501 = 42,606, UP006 = 5,263, UP045 = 2,295, I001 = 1,225, F401 = 918, E722 = 545 (bare except, often deliberate fail-soft), E702 = 424, E402 = 251. About 10.5k are autofixable. |
| Types | none enforced | `basedpyright` (default mode) on `core/` + `agent_cli.py` + `ai_setup_mcp.py` (267 files): **1,064 errors, 26,225 warnings**. Top errors: reportMissingTypeArgument 317, reportArgumentType 230, reportOptionalMemberAccess 219. |
| Tests | `pytest.ini` (`testpaths = tests`, `-q`, return-not-none warning as error); 775 test files | Full suite takes **more than 30 minutes** serially. A partial run shows **1 collection error** (`tests/test_codex_hook_contract.py`: cannot import `codex_common` from `agent.harness.hooks`) and roughly 140 failures before 97%. P0 records the exact set. |
| Guardrails | 21 checkers in `scripts/checkers/`; CI runs 5 (boundaries, doc freshness, comprehensibility, wiring, door parity) | Some are **line-number or citation sensitive** (wiring and durability baselines, verbatim citation, pointer promises), so a mass reformat can move them. `check_comprehensibility.py` has a stale-ref exemption that expired 2026-09-30 and may already be red. P0 records all exit codes. |
| Git hooks | Custom framework: `scripts/githooks/{pre-commit,commit-msg,post-commit,pre-push}` via `core.hooksPath` (installed by `scripts/githooks/install_git_hooks.py`) | Every hook calls **`py`, which does not exist on Linux**. `core.hooksPath` is **not set** on this clone, so no hook runs here today. No `.pre-commit-config.yaml` exists, although `pre-commit` is a runtime dependency. |
| MCP door | `.mcp.json` launches `py ai_setup_mcp.py` | Fails on Linux: "Executable not found in $PATH: py" was seen in this session. |
| Claude hooks | `.claude/settings.json` hooks already use `uv run -p 3.12`; the permission allowlist is all `py agent_cli.py …` | Allowlist entries never match on Linux. |
| Launcher helper | `core.paths.python_launcher()`: `py` on Windows, `uv run` elsewhere when uv + pyproject are present, else `python3`; `AKASHIC_PYTHON` overrides | 77 Python files carry `"py"` literals, mostly user-facing messages routed through `_pyl()`. |
| CI | `.github/workflows/ci.yml`: `actions/checkout@v4`, `setup-python@v5` (tag-pinned), `pip install -r requirements.txt numpy`, Redis 7 service on 16379 | No `permissions:`, no SHA pins, no `persist-credentials: false`, no lock check, no lint or type step. No Dependabot or Renovate. |
| Docs site | `apps/docs` (Fumadocs, Next.js, pnpm) | **Keep it.** The synthesis's Zensical recommendation does not apply: a docs site already exists. |
| Commits | Conventional Commits via `commitlint.config.ts` and `changelog.config.js` | Keep. |

### What from the synthesized stack does NOT apply here (and why)

- **`src/` layout, `uv_build`, publishing, Trusted Publishing, attestations, Copier.** Aurora is an
  *application* run from a checkout (`package = false`; hundreds of modules import `core.*` from the repo
  root). It is not distributed as a wheel and not generated from a template. Converting it to a package is
  a separate architectural decision, out of scope.
- **uv workspaces.** There is a single Python project. `apps/docs` is Node.
- **Docker.** There is no container deployment.
- **Zensical.** A Fumadocs site already exists.
- **100% coverage gate, strict typing everywhere.** On a large legacy codebase these only become an
  instantly bypassed wall. Coverage is measured and reported, and types are gated on "no new errors" via
  a baseline. Strict mode is opt-in per new module.

---

## 3. Target state

| Layer | Target for Aurora |
|---|---|
| Python | `.python-version` = `3.12` (or `3.14` if P11 succeeds). `requires-python` agrees. CI, hooks and `.claude/settings.json` all use the pinned version. |
| Dependencies | `pyproject.toml` + `uv.lock` are the single source of truth. `pytest`, `pre-commit` and all tooling move to `[dependency-groups].dev`, unless a runtime import proves otherwise (P2 checks). `requirements.txt` and `requirements/gemini-web.txt` become **generated** (`uv export`) with a "do not edit" header, and CI plus the pre-commit stage check them. |
| uv settings | `[tool.uv] exclude-newer = "7 days"`, `required-version = ">=0.12"`, `package = false`. |
| Format | `ruff format` over the repo minus history trees. One pure mechanical commit, listed in `.git-blame-ignore-revs`. |
| Lint | `ruff check` with a **gate set** at zero findings, plus a **debt set** under a count ratchet (never rises), using the existing ratchet pattern under state/ci. |
| Types | basedpyright `standard` mode with a committed baseline (`.basedpyright/baseline.json`): no new errors. ty runs as an informational, non-blocking job. New modules may opt into strict with `# pyright: strict`. |
| Tests | pytest config moves to `[tool.pytest.ini_options]`. `pytest-cov` report (not gated). `pytest-xdist` and `pytest-randomly` are adopted **only if** their P6 experiments pass. |
| Task runner | Poe the Poet: `fmt`, `fmt-check`, `lint`, `lint-debt`, `types`, `types-ty`, `guardrails`, `lock-check`, `test`, `test-fast`, `gate`. |
| Git hooks | The custom `scripts/githooks/` framework stays (it owns peer locks, private-plane, door gate and secret gate). Every `py` call goes through a POSIX launcher shim. The pre-commit stage additionally runs **prek** on staged files from `.pre-commit-config.yaml`: ruff, ruff-format, check-toml, check-yaml, uv-lock, uv-export, zizmor, actionlint. Do **not** run `prek install`; it conflicts with `core.hooksPath`. |
| MCP door | `.mcp.json` launches through uv. `uv run python -m core.comm.door_probe` is green. |
| CI | uv-based, SHA-pinned actions, `permissions: contents: read`, `persist-credentials: false`, `concurrency`, timeouts, `uv sync --locked`, all gates through Poe, zizmor clean, a non-blocking ty job, and a non-blocking Windows smoke job. Dependabot for `uv` and `github-actions` with a 7-day cooldown. |
| Docs | CONTRIBUTING.md, docs/DEPLOY.md, AGENTS.md and README.md show `uv` as the primary path. The Windows `py` path is documented as the fallback. |
| Verification | A stack-conformance checker (new file `check_python_stack.py` in `scripts/checkers/`) with 22 named checks (section 5), unit-tested and wired into CI. |

---

## 4. Generator / verifier protocol

**Roles.**
- **Generator:** the main session. It implements one phase at a time, commits, and then requests verification.
- **Verifier:** a *fresh* subagent (Agent tool, `general-purpose`) spawned per phase. It gets **only**: this
  plan's path, the phase ID, the phase's start commit SHA and the end commit SHA. It does **not** get the
  generator's reasoning. Its instructions (paste verbatim):

  > You are the adversarial verifier for phase `<ID>` of docs/python-stack-migration-plan-2026-10.md.
  > Read sections 1–5 and the phase. Inspect `git diff <start>..<end>` and `git log <start>..<end>`.
  > Your job is to FALSIFY the phase's exit gate: run every exit-gate command yourself, check every
  > invariant I1–I11 against the diff, and look for shortcuts (numbers raised in baselines, checks
  > weakened, excluded paths used to hide failures, `noqa`/`type: ignore` sprayed, tests skipped or
  > deleted, commands that "pass" because they checked nothing). Do not edit files. Report: for each
  > exit-gate item, the command, the verbatim last ≤15 lines of output, and PASS/FAIL; then any invariant
  > violations; then a final line exactly `VERDICT: PASS` or `VERDICT: FAIL (<n> findings)`.

**Loop.** If the verdict is FAIL, the generator fixes each finding (new commits; never rewrite history),
then spawns a **new** verifier (fresh context again). The limit is **3 verifier rounds per phase**. After a
third FAIL on the same criterion, apply the phase's **Fallback**. If there is no fallback, or it is
exhausted, stop and report the phase as BLOCKED with the evidence. That is the only legitimate "impossible".

**Evidence rule.** After each phase, quote in the transcript: the verifier's final verdict line, the
exit-gate command outputs (tails), and the phase commit SHA(s). The Progress log row must match.

**Long commands.** The full test suite takes more than 30 minutes serially. Run it in the background with
a timeout of at least 90 minutes, writing to a file under the session scratchpad. Wait on completion, not on
polling loops. Use `test-fast` (defined in P7) for inner loops. Use the full suite at P0, P4, P6 and P12, and
whenever a phase touches runtime code.

**Test comparison helper (write in P0, reuse everywhere).** Run
`pytest -q -rfE -p no:cacheprovider --continue-on-collection-errors` and extract the node IDs from the
`FAILED`/`ERROR` summary lines into a sorted file. The comparison is `comm -13 baseline.txt current.txt`
(new failures). It must print nothing. Store the baseline under state/ci as `python_stack_test_baseline.txt`.

---

## 5. Pre-registered acceptance: the 22 conformance checks

These are implemented in P1 **before** any migration work, as a new file `check_python_stack.py` in
`scripts/checkers/`. It is stdlib-only (plus `tomllib`), cross-platform, prints one line per check
(`S01 PASS <detail>` / `S01 FAIL <detail>`), and ends with exactly `STACK CONFORMANCE: <passed>/22 PASS`.
Exit code 0 means all pass. A `--only S07,S08` flag runs a subset, and `--json` gives machine output.

| ID | Check (objective, machine-verifiable) |
|---|---|
| S01 | `.python-version` exists and is tracked, holding `3.12` or `3.14`. `requires-python` in `pyproject.toml` admits it and has the same minor as its lower bound. The CI workflow and `.claude/settings.json` hook commands use the same minor. |
| S02 | `[project].dependencies` contains neither `pytest` nor `pre-commit` (unless listed in the documented runtime-exception list in pyproject comments, with a reason). `[dependency-groups].dev` contains `ruff`, `basedpyright`, `ty`, `pytest`, `pytest-cov`, `poethepoet` and `prek`. |
| S03 | `[tool.uv]` has `exclude-newer = "7 days"`, `required-version` starting `>=0.12`, and `package = false`. |
| S04 | `pyproject.toml`, `uv.lock` and `.python-version` are tracked by git (`git ls-files`), and `uv lock --check` exits 0. |
| S05 | `requirements.txt` and `requirements/gemini-web.txt` start with the generated-file header and are byte-identical to fresh `uv export` output with the documented flags. |
| S06 | `uv run ruff format --check` exits 0 (config-scoped; the history trees are excluded in config, not on the command line). |
| S07 | `uv run ruff check` exits 0 (gate set). |
| S08 | The Ruff debt count per rule ≤ the committed debt baseline under state/ci (`ruff_debt_baseline.json`), and the baseline total ≤ its P4 value. |
| S09 | `uv run basedpyright` exits 0 with the committed `.basedpyright/baseline.json`. The baseline's error count ≤ the P5 value. |
| S10 | Poe tasks `fmt, fmt-check, lint, lint-debt, types, types-ty, guardrails, lock-check, test, test-fast, gate` all exist (`uv run poe --help` lists them). |
| S11 | Every `uses:` in `.github/workflows/*.yml` is pinned to a 40-hex SHA with a version comment. Top-level `permissions:` is `contents: read`. Every `actions/checkout` step sets `persist-credentials: false`. `astral-sh/setup-uv` is used, `uv sync --locked` runs, and no `pip install` remains. |
| S12 | `uvx zizmor .github/workflows` reports no findings at medium or higher, and `actionlint` exits 0. |
| S13 | `.pre-commit-config.yaml` exists and `uv run prek run --all-files` exits 0. `scripts/githooks/pre-commit` invokes prek. `git config core.hooksPath` equals `scripts/githooks` in this clone (waived only under pre-flight decision D1-c). `.git/hooks/` holds no non-sample hook written by prek or pre-commit. |
| S14 | No bare `py ` invocation remains in executable surfaces: `scripts/githooks/*` (shell files), `.mcp.json`, `.github/workflows/*.yml`, and `.claude/settings.json` hook `command` fields. Allowlist entries have `uv run` equivalents. |
| S15 | `.mcp.json`'s server command starts with `uv`, and `uv run python -m core.comm.door_probe` exits 0. |
| S16 | Every checker in `scripts/checkers/` exits with a code ≤ its P0 baseline code (read from `python_stack_checker_baseline.json` under state/ci), and the 5 CI checkers plus `check_secrets.py` exit 0 unless their P0 code was non-zero. |
| S17 | The most recent full-suite result file (path recorded in state/ci) is newer than the last commit touching `*.py`, `pyproject.toml` or `uv.lock`, and its failing set minus the P0 baseline is empty. |
| S18 | `.github/dependabot.yml` covers `uv` and `github-actions`, each with `cooldown` ≥ 7 days. |
| S19 | `.git-blame-ignore-revs` exists and every SHA in it is a real commit whose subject starts `style:`. |
| S20 | CONTRIBUTING.md, docs/DEPLOY.md, AGENTS.md and README.md contain `uv sync` and `uv run`. None presents `pip install -r requirements.txt` as the primary setup. |
| S21 | `git status --porcelain` is empty. The branch is `chore/python-stack-2026`. Every commit since the P0 base passes commitlint rules (checked with `npx --yes @commitlint/cli --from <base>` if Node is present, else a regex for `^(feat\|fix\|docs\|style\|refactor\|perf\|test\|build\|ci\|chore\|revert)(\(.+\))?!?: .+`). Every path in the P0 dirty-tree manifest exists in `HEAD`. |
| S22 | `uvx ty check` runs to completion (exit 0 or 1, not a crash). Its diagnostic count is recorded in state/ci and printed; the count is not gated. |

S17 depends on an artifact written by the test run, so the checker never runs the 30-minute suite itself.
The `test` Poe task writes a small result record (timestamp, commit, failing IDs) under state/ci, and that
record is gitignored if it churns (decide in P6, then document).

---

## 6. Phases

Each phase lists: **Goal**, **Steps (generator)**, **Exit gate (verifier runs these)**, **Commit(s)**, and a
**Fallback**. The start SHA of each phase is the end SHA of the previous one.

### P0: Baseline, safety and branch

**Goal:** know exactly where we start, protect existing work, and isolate the migration on a branch.

Steps:
1. Boot: `uv run agent_cli.py boot claude --task "python stack migration P0"`, then
   `uv run agent_cli.py bifrost-sync claude`. If the bus shows a peer working on the same files, stop and
   report. Run `uv run agent_cli.py locks` and record the output.
2. Record the dirty-tree manifest: `git status --porcelain=v1 > <scratch>/p0_dirty_manifest.txt`. Today it
   includes modified `core/foundation/{ledger,redis_connection}.py`, `core/paths.py`,
   `core/fleet/app_package.py`, `requirements.txt`, several scripts, `data/verb-registry/deepseek.json`, and
   untracked `core/foundation/embedded_redis.py`, `tests/test_embedded_redis.py`, `pyproject.toml` and
   `uv.lock`. This is the in-progress Linux port.
3. Create the branch: `git switch -c chore/python-stack-2026`. The dirty tree carries over; nothing is lost.
4. Run the full test suite **on the dirty tree** in the background (≥ 90 min timeout, `REDIS_DB=15`) with the
   section 4 command. Save the failing IDs.
5. Commit the pre-existing WIP as **atomic Conventional Commits**, grouped by concern (embedded Redis;
   path derivation; revive; checker and script tweaks; verb registry; `pyproject.toml` + `uv.lock` as
   `build: add uv project files`). Use the `atomic-uncommitted-commits` skill. Do not change the content.
   If `scripts/githooks` is active and a guard blocks a WIP commit, **do not bypass it**: record the block
   and apply the Fallback.
6. Re-run the suite on the committed tree only if step 5 needed any content change (it should not). The
   step 4 failing set becomes the baseline, stored under state/ci as `python_stack_test_baseline.txt`, with
   a header comment giving date, commit and command. **`.gitignore` ignores `state/ci/*`** except named
   ratchet files, so add `!` exceptions, in the style of the existing ones (a comment on why the file must
   travel with the repo), for `python_stack_test_baseline.txt`, `python_stack_checker_baseline.json`,
   `ruff_debt_baseline.json` (P4) and `python_stack_ty_count.json` (P5). `python_stack_test_last.json` (P6)
   stays ignored. Verify each with `git check-ignore` (it must print nothing).
7. Run every checker in `scripts/checkers/` (`uv run scripts/checkers/<name>.py`, 120 s timeout each). Record
   exit codes to `python_stack_checker_baseline.json` under state/ci.
8. Record tool baselines (numbers only, for the log): ruff statistics with the P4 candidate config, the
   basedpyright summary, `uvx ty check` count, and `ruff format --check --output-format concise` count. Find
   the file that makes `ruff format --check` panic by bisecting over files with the default output format.
   Record its path (P4 decides what to do with it).
9. Write this phase's row to the Progress log.

Exit gate:
- `git branch --show-current` prints `chore/python-stack-2026`.
- Every path in the manifest exists in `HEAD` (`git ls-files --error-unmatch` per path, or `git cat-file -e HEAD:<path>`).
- Both baseline files exist under state/ci and are committed. The test baseline's header names the commit and command.
- `git status --porcelain` is empty.

Commits: the WIP commits, plus `chore(ci): record python-stack migration baselines`.

Fallback: if a repo guard blocks committing the WIP, leave the WIP **uncommitted**, record that in the log,
and continue with it carried in the working tree. S21's "clean tree" then becomes "clean except for the
manifest paths", and the final report must say so. If the suite cannot complete within 3 hours, record the
partial failing set with the percentage reached. Later comparisons then use the same `--deselect` list for
the unreached tail, and the report must say so.

### P1: Pre-registered acceptance (the conformance checker)

**Goal:** encode section 5 as an executable check before migrating, and prove that it can fail.

Steps:
1. Implement `check_python_stack.py` in `scripts/checkers/`, stdlib-only, following the house style of the
   other checkers: module docstring with WHY THIS EXISTS, `_pyl()` helper, derived `ROOT`, no OS literals.
   Each S-check is a pure function taking the repo root, so it can be unit-tested against temp directories.
   Commands it runs (uv, ruff, prek, zizmor, actionlint) get a timeout. If one is missing, that check FAILs
   with "tool missing"; it never crashes and never passes.
2. Write unit tests (a new file `test_check_python_stack.py` in `tests/`): for each S-check, a passing and
   a failing fixture built in `tmp_path`. Subprocess-based checks are tested through a small injectable
   runner so the tests stay fast and hermetic.
3. **Drill (M4):** run the checker on the current tree. It must exit non-zero, and **at least 18 of 22**
   checks must FAIL (the stack is not migrated yet). Paste the output.
4. Wire it in so `check_wiring.py` and the comprehensibility checker stay green. CI wiring happens in P9. If
   the wiring guardrail demands a consumer now, the Poe `guardrails` task in P7 is the consumer. Record
   whether the wiring checker needs anything else.

Exit gate:
- `uv run pytest tests/test_check_python_stack.py -q` passes.
- The drill output shows ≥ 18 FAIL lines and a non-zero exit.
- `uv run scripts/checkers/check_wiring.py` and `uv run scripts/checkers/check_comprehensibility.py` exit
  codes ≤ their P0 baseline.

Commits: `test(checkers): pre-register python stack conformance checks`, then
`feat(checkers): add python stack conformance checker`. Test first, per slice discipline.

Fallback: none. This phase must succeed.

### P2: Dependencies, Python pin and uv settings

**Goal:** make `pyproject.toml` + `uv.lock` the single source of truth. S01–S05 pass.

Steps:
1. `.python-version` gets `3.12`. Set `requires-python = ">=3.12"`: 3.11 is dropped because the only 3.11
   consumer is CI, which moves to the pin. **Before** changing it, grep `docs/DEPLOY.md` and the Windows notes
   for a stated 3.11 requirement. If the Windows machine is documented as 3.11-only, keep `>=3.11`, pin
   `.python-version` to 3.12, and note it.
2. Check whether runtime code needs `pytest` or `pre-commit`:
   `git grep -nE "^\s*(import|from) (pytest|pre_commit)\b" -- core agent arsenal scripts '*.py' ':!tests'`,
   plus a subprocess search for `-m pytest` in runtime code (for example `agent_cli.py` suite gates). If
   runtime code shells out to pytest, pytest may still move to dev, because `uv sync` installs dev by
   default. Document that in a pyproject comment. `pre-commit` is removed entirely: prek replaces it.
3. Add `[dependency-groups].dev` with `ruff`, `basedpyright`, `ty`, `pytest`, `pytest-cov`, `pytest-xdist`,
   `pytest-randomly`, `poethepoet` and `prek`. Use loose lower bounds; the lockfile is the pin. Keep the `ml`
   and `browser` groups. Set `[tool.uv] default-groups = ["dev"]` explicitly.
4. `[tool.uv]` gets `exclude-newer = "7 days"`, `required-version = ">=0.12"` and `package = false` (kept).
5. `uv lock`, then `uv sync`. Verify imports with
   `uv run python -c "import redis, fakeredis, lupa, mcp, openai, numpy, av, fitz, rich"`.
6. Generated requirements, backward compatible for the Windows `pip` path:
   - `requirements.txt` = `uv export --format requirements.txt --no-hashes --no-emit-project --group dev --no-annotate`
     with a header block (`# GENERATED by uv export -- do not edit; edit pyproject.toml and run: uv run poe lock`).
     The dev group is included because the Windows machine runs the suite from pip.
   - `requirements/gemini-web.txt` = the same with `--only-group browser`.
   - Add a Poe task `lock` that runs `uv lock` and both exports, and `lock-check` that runs `uv lock --check` and
     diffs fresh exports against the files. (Poe lands in P7; until then, run the commands directly.)
   - Delete the "keep the two in step" comments in pyproject; the generator now keeps them in step.
7. Update the `.claude/settings.json` hook commands' `-p 3.12` only if the pin differs (it does not, at 3.12).
8. Run the section 4 fast checks (`test-fast` does not exist yet, so run `pytest tests/test_embedded_redis.py
   tests/test_portability.py -q` plus any test that imports packaging or requirements). The full suite
   comes at P4.

Exit gate:
- `uv run scripts/checkers/check_python_stack.py --only S01,S02,S03,S04,S05` → all PASS.
- `uv sync --locked` exits 0 in a fresh throwaway copy (`git worktree add <scratch>/wt HEAD`,
  `cd` there, `uv sync --locked`, then remove the worktree).
- `tests/test_portability.py` passes.

Commits: `build(deps): pin python 3.12 and move tooling to the dev group`,
`build(deps): generate requirements files from uv.lock`.

Fallback: if `exclude-newer = "7 days"` makes resolution fail because a locked version is younger than 7
days, add a per-package `exclude-newer-package` override for that package only, with a comment and a
removal date. Never drop the global setting.

### P3: One launcher everywhere (`py` → uv)

**Goal:** every executable entry point works on Linux and on Windows. S14 and S15 pass.

Steps:
1. Create a POSIX shim, `pyrun.sh` in `scripts/githooks/` (sourced, not executed), defining `pyrun`:
   honour `$AKASHIC_PYTHON`; else if `command -v uv` works, run `uv run --frozen --quiet`; else if
   `command -v py`, run `py`; else `python3`. It must be `sh`-compatible (no bash-isms) and must work
   under Git for Windows.
2. Rewrite `scripts/githooks/pre-commit`, `commit-msg`, `post-commit` and `pre-push` to source the shim and
   call `pyrun …` instead of `py …`. Keep every gate and message; change only the invocation.
3. `core.paths.python_launcher()`: prefer `uv run` on **every** OS when uv and the pyproject are present;
   otherwise `py` on Windows and `python3` elsewhere; `AKASHIC_PYTHON` still overrides. Update or add tests
   for all four branches, mocking `os.name` and `shutil.which`. This changes Windows behaviour only when uv
   is installed there. Document it in DEPLOY (P10).
4. `.mcp.json` → `"command": "uv", "args": ["run", "--frozen", "--quiet", "ai_setup_mcp.py"]`. Check
   `scripts/mcp_register.py` and any generator that writes MCP configs for other harnesses (`.codex`,
   `.cursor`, `.agents`). If they emit `py`, route them through `python_launcher()`.
5. `.claude/settings.json` permissions: for every `Bash(py agent_cli.py X*)` add a sibling
   `Bash(uv run agent_cli.py X*)`. Keep the `py` ones for Windows. Do not change the `env` block or other hooks.
6. Apply pre-flight decision **D1** (section 0) first. Then, unless D1-c applies, install hooks on this
   clone: `uv run scripts/githooks/install_git_hooks.py`. From now on the repo's own gates run on every
   commit, which is intentional. If a gate blocks a migration commit, fix the cause and never use `--no-verify`.
   Before installing, dry-run the stage with `uv run scripts/githooks/pre_commit.py` with nothing staged, to
   see whether pre-existing drift would block. Record the result.
7. Run the door probe: `uv run python -m core.comm.door_probe`.

Exit gate:
- `check_python_stack.py --only S14,S15` → PASS.
- `sh -n scripts/githooks/pre-commit scripts/githooks/pre-push scripts/githooks/commit-msg scripts/githooks/post-commit` exits 0.
- An empty commit round-trip exercises pre-commit and commit-msg:
  `git commit --allow-empty -m "chore(hooks): verify launcher shim"` succeeds with the hooks visibly running.
  Keep the commit; it is the evidence. Then run `sh scripts/githooks/pre-push` directly (no push), which must
  exit 0 or fail only for a reason that also fails at the P0 baseline (record which).
- The python_launcher tests pass.

Commits: `fix(hooks): run git hooks through a uv-aware launcher shim`,
`fix(paths): prefer uv run as the python launcher on every OS`,
`fix(mcp): launch the MCP door through uv`, `chore(claude): allow uv run equivalents of agent_cli verbs`.

Fallback: if the pre-push door gate is red at baseline for a reason unrelated to the launcher, record the
reason and treat "same failure as baseline" as passing for this gate.

### P4: Ruff (format and lint)

**Goal:** a formatted codebase and an enforceable lint gate without hiding debt. S06–S08 and S19 pass.

Steps:
1. **Configure scope** in `pyproject.toml`:
   `[tool.ruff] target-version = "py312"`, `extend-exclude = ["research", "docs/library", "docs/_archive",
   "chronicles", "fences", "session_logs", "temp", "apps", "assets", "artifacts", "store", "state"]`, plus
   any untracked heavy trees. Verify with `ruff check --show-files | wc -l`: it must be close to the tracked
   non-history `.py` count.
2. **Choose line length by data, not taste.** For L in {100, 120}, count `ruff format --check
   --output-format concise --line-length L` hits. Choose the L with fewer reformatted files; on a tie within
   5%, choose 120. Record both counts in the log.
3. **Panic file** (from P0): if it still panics with the chosen config, add it to `extend-exclude` with a
   comment that names the Ruff version and the error. Do not file an upstream issue (I2); mention it in the
   final report.
4. **Guard line-sensitive artifacts before formatting.** List the checkers whose baselines or data carry line
   numbers or verbatim code (at least `wiring_function_baseline.json`, `durability_baseline.json`,
   `check_verbatim_citation.py`, `check_pointer_promises.py`, `check_rewrite_maps.py`). For each, find its
   documented regeneration command. The format commit may be followed by **separate** regeneration commits,
   each showing that counts did not rise.
5. **Format commit** (pure, I9): `uv run ruff format`, then `git add -u` on in-scope paths only, then commit
   `style: apply ruff format repo-wide`. Nothing else goes into it.
6. Verify semantic equivalence: run the full suite in the background and compare against the baseline (no
   new failures). Run every checker and compare against the P0 codes. If a checker regressed only because
   of line movement, regenerate its baseline with its own tool in a separate commit
   (`chore(checkers): regenerate <name> baseline after reformat`), and show that the count did not increase.
7. `.git-blame-ignore-revs` gets the format commit's full SHA with a comment. Then
   `git config blame.ignoreRevsFile .git-blame-ignore-revs` (local) and a note in CONTRIBUTING (P10).
8. **Lint rules.** Start from the candidate `select = ["E4","E7","E9","F","I","UP","B","C4","SIM","RUF","T10","ASYNC","PIE","PERF","LOG"]`,
   with `ignore = ["E501"]` (the formatter owns line length). Then:
   a. Apply **safe** autofixes one rule family per commit (`ruff check --fix --select I`, then `UP`, then
      `F401` …). Never use `--unsafe-fixes`. After each commit, run `test-fast` (or the targeted tests for the
      touched modules) and the boundary and wiring checkers. Each commit is
      `style(lint): apply ruff <FAMILY> safe fixes`.
   b. Watch F401 in modules that re-export or that are imported for side effects. Keep any
      `__init__.py` re-export and any import the wiring or door-parity checkers rely on. Mark keepers with
      `__all__` or a targeted `# noqa: F401  # <reason>`.
   c. After the autofixes, count what remains per rule, excluding `tests/`. A rule with ≤ 25 remaining
      findings is **fixed by hand** (small commits, `refactor(lint): …`). A rule with more goes to the
      **debt set**.
   d. **Deliberate-pattern rules** are debt by policy, not hand-fixed: `E722` (fail-soft bare except),
      `E402` (sys.path bootstrapping in scripts and tests), `E702`, `E741`. Use per-file ignores
      only where the pattern is structural, for example `E402` under `scripts/**` and `tests/**`, with a comment.
9. **Debt ratchet.** Add a new checker, `check_ruff_debt.py` in `scripts/checkers/`: it runs
   `ruff check --select <debt set> --output-format json`, counts findings per rule, and compares them against
   `ruff_debt_baseline.json` under state/ci (per rule; `_why` and `_how_to_pay_down` fields modelled on the
   guardrail ratchet baseline). It fails if any rule's count rises and prints a "lower the baseline" hint
   when counts fall. Add unit tests for it.
10. The gate set is `select` minus the debt set. `ruff check` (gate) must exit 0.

Exit gate:
- `check_python_stack.py --only S06,S07,S08,S19` → PASS.
- The full-suite comparison prints no new failures (S17 data refreshed).
- The checker-baseline comparison shows no regressions (S16).
- `git show --stat <format-commit>` touches only `.py` files and nothing outside the Ruff scope.
- The debt checker's tests pass.

Commits: as listed. Expect one format commit, one to four regeneration commits, several autofix
commits, several hand-fix commits, and one debt-checker commit plus its tests.

Fallback: if the format commit causes new test failures that cannot be attributed and fixed within 3
verifier rounds, revert **via a new revert commit** (`git revert`, never a reset). Then narrow the format
scope to `core/`, `agent/`, `scripts/` and root files, re-exclude the rest, and try again.

### P5: Types (basedpyright, with ty alongside)

**Goal:** a type gate that blocks new errors today. S09 and S22 pass.

Steps:
1. `[tool.basedpyright]`: `typeCheckingMode = "standard"`, `pythonVersion = "3.12"`, `venvPath = "."`,
   `venv = ".venv"`, `include = ["core", "agent", "scripts", "arsenal", "agent_cli.py", "ai_setup_mcp.py",
   "bootstrap.py", "config.py", "bridge_doctor.py", "peer_connect.py", "seat_topology.py"]`,
   `exclude` = the Ruff history trees plus `tests`. Tests enter the type gate later, as a follow-up; record it
   in the report. Set `reportMissingModuleSource = "none"` for optional deps that are absent on Linux
   (`uiautomation`).
2. `uv run basedpyright --writebaseline` creates `.basedpyright/baseline.json`. Record the error count in the log.
3. Fix the cheapest real bugs basedpyright found, **only** in categories that are genuine defects:
   `reportUndefinedVariable` (29 at baseline), `reportMissingImports` (10), and `reportCallIssue`. Put them in
   small `fix(types): …` commits, then re-write the baseline so it shrinks. Do not chase annotations.
4. `[tool.ty]`: same include and exclude, Python 3.12. `uvx ty check` is informational. Record its count to
   state/ci for S22.
5. Policy text (goes into CONTRIBUTING in P10): new modules may opt into strict with `# pyright: strict`.
   The baseline may only shrink, and `--writebaseline` is run only after fixing, never to absorb new errors.

Exit gate:
- `check_python_stack.py --only S09,S22` → PASS.
- The baseline's error count ≤ the step 2 count, and ≤ the step 2 count minus the number of step 3 fixes.
- Adversarial check by the verifier: add a deliberate type error to a scratch copy of a core module in a
  temp worktree, and confirm `basedpyright` exits non-zero. This proves the gate bites.

Commits: `build(types): configure basedpyright with a no-new-errors baseline`, `fix(types): …` (n),
`build(types): configure ty as an informational checker`.

Fallback: if basedpyright cannot analyse a subtree (a crash, or a timeout over 10 minutes), exclude that
subtree with a comment and record it.

### P6: Tests (config, coverage, parallel and random-order experiments)

**Goal:** a faster, better-instrumented suite without changing what it proves. S17 passes.

Steps:
1. Move `pytest.ini` into `[tool.pytest.ini_options]` in pyproject **verbatim in meaning** (`testpaths`,
   `addopts = "-q"`, the `filterwarnings` error rule, and the comments), then delete `pytest.ini`. Collection
   must be identical: `pytest --collect-only -q | tail -1` gives the same count before and after.
2. Coverage: `[tool.coverage.run] source = ["core", "agent", "scripts", "arsenal"]`, `branch = true`.
   Report only. Record the total in the log.
3. **Experiment X: pytest-xdist.** Run `pytest -n auto --dist loadfile` with `REDIS_DB=15`. Adopt it for the
   `test` task **only if** its failing set ⊆ the baseline on **2 consecutive runs**. Tests share Redis db 15,
   ports and files, so collisions are expected. If it fails: first try `--dist loadgroup` with a per-worker
   Redis DB (`REDIS_DB = 15 - worker_index` via a conftest fixture, if the suite reads `REDIS_DB` at call
   time). If that still fails, keep the suite serial and record why. `test-fast` may still use xdist on a
   subset that is proven safe.
4. **Experiment R: pytest-randomly.** Run 3 times with different `-p randomly -p "randomly_seed=<n>"`. Adopt it
   only if all 3 are ⊆ the baseline. Otherwise install it but disable it by default (`-p no:randomly` in
   addopts), with a note listing the order-dependent tests found. Those are follow-up work, not this migration.
5. **Doctests:** run `pytest --doctest-modules core -q` once. If all pass, add `--doctest-modules` scoped to
   `core` in the `test` task. If any fail, do not adopt; record the count.
6. The test result record: the `test` Poe task writes `python_stack_test_last.json` under state/ci
   (`{commit, finished_at, failing: [...]}`), which S17 reads. If it churns, add it to `.gitignore`.
   S17 accepts an untracked file.

Exit gate:
- Collected count unchanged (quote both numbers).
- Full-suite comparison shows no new failures (S17 → PASS).
- The experiment verdicts are recorded, each with its evidence (run outputs).

Commits: `test(config): move pytest config into pyproject`, `test(coverage): report coverage for core
packages`, and, conditionally, `test(parallel): run the suite with xdist` / `test(order): randomize test order`.

Fallback: the experiments are optional by design. A failed experiment is recorded, not blocking.

### P7: Task runner (Poe the Poet)

**Goal:** one vocabulary for every gate, used by humans, hooks and CI alike. S10 passes.

Tasks in `[tool.poe.tasks]`, each with `help`:
- `fmt` = `ruff format`; `fmt-check` = `ruff format --check`
- `lint` = `ruff check --fix`, but in CI use `ruff check` (define `lint-check` if needed, and adjust S10
  accordingly *only by editing the checker in the same commit, with a reason*)
- `lint-debt` = `python scripts/checkers/check_ruff_debt.py`
- `types` = `basedpyright`; `types-ty` = `ty check`
- `guardrails` = a sequence over the CI checkers (`check_boundaries`, `check_doc_freshness`,
  `check_comprehensibility`, `check_wiring`, `check_door_parity`), plus `check_secrets`,
  `check_ruff_debt` and `check_python_stack --skip S17,S21` (those two depend on test runs and a clean tree)
- `lock` / `lock-check` (from P2)
- `test` = the full suite that writes the S17 record; `test-fast` = a curated subset of under 3 minutes
  (door pins, portability, embedded Redis, the stack checker and debt checker tests, the boundaries tests).
  Pick it by timing: `pytest --durations=0` data from P6.
- `gate` = `fmt-check`, `lint-check`, `lint-debt`, `types`, `lock-check`, `guardrails`, `test-fast`, in that
  order, stopping on the first failure.

Exit gate:
- S10 PASS; `uv run poe gate` exits 0 (quote the tail).
- `uv run poe test-fast` finishes in under 180 s (quote the timing).

Commit: `build(tasks): add poe tasks for every quality gate`.

Fallback: none needed.

### P8: Hooks (prek inside the existing framework)

**Goal:** fast staged-file checks at commit time without replacing the repo's own hook framework. S13 passes.

Steps:
1. `.pre-commit-config.yaml`, with every `rev` pinned to a full commit SHA plus a version comment:
   - `astral-sh/ruff-pre-commit`: `ruff-check` (args `--fix`), `ruff-format`
   - `astral-sh/uv-pre-commit`: `uv-lock`; `uv-export` twice, once per requirements file, with the P2 flags
   - `pre-commit/pre-commit-hooks`: `check-toml`, `check-yaml`, `check-merge-conflict`, `check-added-large-files`
     (`--maxkb=1024`). **No** repo-wide whitespace or end-of-file fixers: they would churn history trees and
     the verbatim-citation guard.
   - `zizmorcore/zizmor-pre-commit`: `zizmor`
   - `rhysd/actionlint`: `actionlint`
   - `exclude:` the same history trees as Ruff.
2. In `scripts/githooks/pre_commit.py` (or the `pre-commit` shell file, whichever is the cleaner seam), add a
   stage that runs `uv run --frozen prek run` on **staged files** after the peer-lock check and before the
   guardrail ratchet. Fail closed on real findings. Fail open, with a loud warning, only when prek itself is
   missing, matching the file's existing crash-versus-finding policy and its comments. Add a unit test for the
   new stage's wiring (the file has existing test patterns in `tests/`).
3. Confirm `git config core.hooksPath` is still `scripts/githooks`, and that no `.git/hooks/pre-commit`
   (non-sample) exists.
4. `uv run prek run --all-files` must pass. If it rewrites files (ruff `--fix`), commit those as
   `style(lint): …` and re-run until clean.

Exit gate:
- S13 PASS.
- Drill: stage a deliberately mis-formatted scratch `.py` file inside the Ruff scope in a temp worktree,
  and confirm the commit is **blocked** by the prek stage. Quote the output. Discard the temp worktree.
- A normal commit still passes all existing stages.

Commits: `build(hooks): add prek config for staged-file checks`, `feat(hooks): run prek from the pre-commit stage`.

Fallback: if prek cannot run under the existing hook on Windows semantics (it can be checked from Linux only
by reading its docs), keep it Linux-verified and document the Windows expectation in DEPLOY.

### P9: CI (hardened, uv-based) and dependency automation

**Goal:** CI runs the same Poe gates, hardened per uv-forge's practices. S11, S12 and S18 pass.

Steps:
1. Resolve pins at execution time: for `actions/checkout` and `astral-sh/setup-uv`, find the latest release
   tag (`gh api repos/<owner>/<repo>/releases/latest --jq .tag_name`, or `git ls-remote --tags`), then its
   commit SHA (`git ls-remote https://github.com/<owner>/<repo> refs/tags/<tag>^{}`, falling back to the
   non-peeled ref). Pin as `uses: owner/repo@<sha> # <tag>`.
2. Rewrite `.github/workflows/ci.yml`:
   - `permissions: contents: read` at top level; `concurrency: {group: ci-${{ github.ref }},
     cancel-in-progress: true}`; `timeout-minutes` on each job.
   - Job **gate** (ubuntu): checkout (`persist-credentials: false`), setup-uv (`enable-cache: true`), then
     `uv sync --locked`, then `uv run poe fmt-check`, `lint-check`, `lint-debt`, `types`, `lock-check`,
     `guardrails`. Keep the existing explanatory comments for each guardrail.
   - Job **test** (ubuntu): the Redis 7 service is kept (same env: `AI_SETUP`, `REDIS_HOST`, `REDIS_PORT`),
     then `uv sync --locked`, then `uv run poe test`. Keep numpy coverage: numpy is already a runtime dep.
   - Job **ty** (ubuntu, `continue-on-error: true`): `uvx ty check`.
   - Job **windows-smoke** (windows-latest, `continue-on-error: true`): `uv sync --locked`, then
     `uv run agent_cli.py status`, then `uv run pytest tests/test_portability.py -q`.
   - Job **zizmor** (ubuntu): `uvx zizmor --min-severity medium .github/workflows`.
3. `.github/dependabot.yml`: ecosystems `uv` (directory `/`) and `github-actions`, weekly, each with
   `cooldown: {default-days: 7}`, and grouped minor/patch updates.
4. Validate locally: `actionlint`, `uvx zizmor .github/workflows`. Then **replay each CI `run:` step locally
   in order**, with the same env and Redis on db 15. That is as far as verification can go without a push
   (I2). Say so explicitly in the report.

Exit gate:
- S11, S12 and S18 PASS.
- The local replay of every gate-job step exits 0 (quote each tail).

Commits: `ci: run quality gates through uv and poe`, `ci: harden workflow permissions and pin actions`,
`ci: add dependabot for uv and actions with a cooldown`.

Fallback: if zizmor flags something that cannot be fixed without changing CI semantics, add a
`# zizmor: ignore[<rule>]` comment with a reason. At most 2 such comments; beyond that the phase is
BLOCKED.

### P10: Documentation and shared memory

**Goal:** the living docs describe the new reality, and the lessons are captured. S20 passes.

Steps:
1. CONTRIBUTING.md: setup (`uv sync`), the quality gate (`uv run poe gate`, and `uv run poe test` for the full
   suite), the blame-ignore config line, the type-baseline and debt-ratchet policies, and the "never
   `--no-verify`" rule.
2. docs/DEPLOY.md §1–3: uv-first quick start on Linux, macOS and Windows. The `pip install -r requirements.txt`
   path stays as the fallback, stating that the file is generated. §8, Windows machine: install uv
   (`winget install astral-sh.uv`), run `uv sync`, and note that `python_launcher()` now prefers `uv run`.
3. AGENTS.md: in the command table and the "Details" section, state that `uv run agent_cli.py …` is the
   cross-platform form, and that `py` is the Windows fallback. Keep the document's first-40-lines contract and
   its style.
4. README.md: the quick start uses uv.
5. Regenerate the generated docs the comprehensibility checker demands (for example `docs/MODULE_INDEX.md`
   via `scripts/generators/gen_arch_index.py`), because P1, P4 and P8 added modules. Run each generator
   with its own `--check` afterwards.
6. Shared memory: record lessons with `uv run agent_cli.py learn claude --experiment <NAME> …`,
   trigger-phrased per AGENTS.md. At minimum:
   `ruff-format-line-sensitive-baselines`, `prek-inside-core-hookspath`,
   `basedpyright-baseline-ratchet`, `uv-launcher-shim-git-hooks`, and one per failed P6 experiment.
   If the store is unreachable, record the attempt; the store is fail-soft.

Exit gate:
- S20 PASS. `check_comprehensibility.py` and `check_doc_freshness.py` codes ≤ baseline. Every generator's
  `--check` exits 0.

Commits: `docs: make uv the primary setup path`, `docs(generated): regenerate module index`.

Fallback: none needed.

### P11: Python 3.14 (gated experiment; may be DEFERRED)

**Goal:** move to 3.14 if and only if it is free of regressions on both platforms' wheels.

Steps:
1. In a temp worktree: `uv python install 3.14`, set `.python-version` to `3.14`, and run `uv lock` (universal
   resolution). Confirm the lock contains cp314 or abi3 wheels for **both** `manylinux x86_64` and `win_amd64`
   for every runtime dep with native code (`lupa`, `av`, `pymupdf`, `pynacl`, `numpy`, `zstandard`, `psutil`,
   `pillow`): `uv tree` plus inspection of the `uv.lock` wheel entries. Any sdist-only fallback on Windows means DEFER.
2. `uv sync`, then the full suite in the background, then compare against the baseline.
3. If everything is clean, apply it in the main worktree: `.python-version`, `requires-python = ">=3.14"` (or
   keep `>=3.12` if the Windows machine is documented on an older version), Ruff `target-version`, basedpyright
   and ty `pythonVersion`, `.claude/settings.json` `-p 3.14`, and the CI pins. Re-run P4 step 8a for `UP`
   (new pyupgrade fixes) as its own commit, and re-write the basedpyright baseline only if the count does not rise.

Exit gate (for DONE):
- S01 PASS at 3.14; full-suite comparison clean; `uv run poe gate` exits 0.

Exit gate (for DEFERRED): a Progress log row with the exact blocker (package, platform, or failing test IDs).

Commits: `build(python): move to python 3.14`, `style(lint): apply ruff UP fixes for 3.14`.

Fallback: DEFERRED is an acceptable terminal state for this phase only.

### P12: Final verification (fresh clone, fresh verifier)

**Goal:** prove the end state from scratch, not from this session's warm environment.

Steps:
1. Full suite on `HEAD` (background), then compare against the baseline. This refreshes the S17 record.
2. Clean-clone proof: `git clone --no-hardlinks . <scratch>/clone`, `cd` into it, check out the branch, then
   `uv sync --locked`, `uv run poe gate`, and `uv run python -m core.comm.door_probe`. Also run
   `uv run scripts/check_fresh_clone.py` if it applies. Quote the tails. Delete the clone afterwards.
3. `uv run scripts/checkers/check_python_stack.py` in the main worktree must end with
   `STACK CONFORMANCE: 22/22 PASS` and exit 0.
4. Spawn the **final verifier** (fresh context, section 4 prompt, phase `P12`, range = P0 base → `HEAD`). It
   must additionally re-derive S01–S22 independently, re-check I1 against the P0 manifest, and scan the full
   diff for weakened checks.
5. Handoff: `uv run agent_cli.py handoff claude --to <next> --task "python stack migration" --note
   "<summary + branch + what the human must do: push, watch CI, Windows machine uv install>"`.
6. Final Progress log row, then commit (`docs: close out python stack migration log`). Re-run step 3 after
   this last commit, so the evidence postdates the last edit.

Exit gate: all of the above quoted in the transcript, with `git status --porcelain` empty.

---

## 7. Progress log

Append one row per phase. The `/goal` evaluator reads this table as quoted in the transcript.

| Phase | Status (DONE / DEFERRED / BLOCKED) | Commit range | Verifier rounds | Verdict line | Notes (numbers, decisions) |
|---|---|---|---|---|---|
| P0 | | | | | |
| P1 | | | | | |
| P2 | | | | | |
| P3 | | | | | |
| P4 | | | | | |
| P5 | | | | | |
| P6 | | | | | |
| P7 | | | | | |
| P8 | | | | | |
| P9 | | | | | |
| P10 | | | | | |
| P11 | | | | | |
| P12 | | | | | |

---

## 8. The `/goal` condition (paste this; about 2,100 characters, under the 4,000 limit)

The evaluator only reads the transcript, so every clause names evidence that must be *quoted*, not merely
true. The detail lives in this file; the condition points at it.

```
Execute docs/python-stack-migration-plan-2026-10.md phase by phase, P0 through P12 in order, on local branch chore/python-stack-2026, obeying its invariants I1-I11 and its generator/verifier protocol (section 4: after each phase, a fresh-context verifier subagent must return "VERDICT: PASS" before the next phase starts; max 3 verifier rounds per phase, then the phase's Fallback). Quote evidence (command + verbatim output tail) in the transcript for every exit-gate item.

The goal is MET only when the latest turn shows ALL of the following, each produced AFTER the final commit:
1. The verbatim output of `uv run scripts/checkers/check_python_stack.py` ending with the line "STACK CONFORMANCE: 22/22 PASS" and exit code 0.
2. The verbatim tail of `uv run poe gate` with exit code 0.
3. The P12 clean-clone proof: a fresh `git clone` into a scratch dir where `uv sync --locked` and `uv run poe gate` both exit 0, tails quoted.
4. A full-suite comparison against the P0 test baseline showing zero new failing test IDs (the `comm -13` output is empty), with the suite run on the final code commit.
5. The final P12 verifier subagent's report ending "VERDICT: PASS", quoted.
6. The Progress log table (section 7) quoted, with P0-P10 and P12 marked DONE and P11 marked DONE or DEFERRED with a named blocker, every row carrying a commit range and a verdict line.
7. `git status --porcelain` printing nothing (or only P0-manifest paths if the P0 fallback applied), and `git log origin/master..HEAD --oneline` listing the migration commits (nothing pushed). Pre-flight decision D1 (section 0) was applied as ticked, or as D1-c if none was ticked.

The goal is NOT met if: any checker in scripts/checkers exits worse than its P0 baseline code; any ratchet or type baseline number went up; any test was deleted, skipped or deselected to get green (other than the P0-documented unreached tail); `--no-verify`, `git reset --hard`, `git clean`, a force push, or any push at all occurred; or any path in the P0 dirty-tree manifest is missing from HEAD.

Declare IMPOSSIBLE only if a phase ends BLOCKED after 3 verifier rounds with its Fallback exhausted; then state the phase, the failing exit-gate item and the evidence. Or stop after 250 turns.
```
