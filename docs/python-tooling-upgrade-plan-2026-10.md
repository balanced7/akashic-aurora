# Python tooling upgrade: full-repo rewrite plan (2026-10)

**Written:** 2026-10-01. **Executor:** Claude Code sessions driven by `/goal`, one goal at a time (G0–G7).
**End state:** every Python file in the repo has been brought onto the modern stack, and no functionality is lost.
That means uv as the single source of truth for Python, dependencies and environments; Ruff format plus
a broad lint set at **zero** findings; basedpyright at **zero** errors (with ty running alongside); pytest
configured in pyproject; Poe the Poet as the one task vocabulary; prek staged-file hooks; and hardened,
uv-based CI with automated dependency updates.

This plan does not depend on any earlier migration attempt, branch or baseline. It starts from the repo as
it stands, derives the method from first principles, and makes every success claim provable by a command
whose output appears in the transcript.

---

## Part I: Reasoning from first principles

### 1. What "without losing functionality" means operationally

Functionality is what the repo **does**, and that can only be observed through its interfaces:

1. **Tests:** which test ids exist, which pass, and how much each one asserts.
2. **Entry points:** the CLIs and scripts people and agents run, and their help text, verbs and exit codes.
3. **Protocol surfaces:** the MCP server's tool list and JSON schemas, and any other machine-facing API.
4. **Importable surface:** which modules import cleanly, and which public names each one exposes. Other code,
   dynamic imports, agents and docs depend on these.
5. **The repo's own guardrail scripts:** the repo already encodes invariants in checkers. Their verdicts are
   part of its behaviour.
6. **Data and non-Python files:** a tooling upgrade has no reason to change them.

So "no functionality lost" becomes a **behavioural oracle**: a set of snapshots taken before any change and
compared after every change. A change preserves functionality iff the oracle compares EQUAL, or it differs
only in a way pre-registered as an intended change (for example, help text that now says `uv run` instead of
`py`).

### 2. Not all changes carry the same risk, so the proof matches the risk

| Change class | Example | Semantic risk | Strongest available proof |
|---|---|---|---|
| A. Metadata | pyproject, lockfile, CI YAML, hook config, docs | None to runtime code, but can break *environments* | Fresh-clone install + oracle |
| B. Formatter | `ruff format` | None by construction (Ruff guarantees AST equivalence) | **AST-equality per file** (deterministic) + oracle |
| C. Mechanical autofix | `ruff check --fix --select UP` | Low, but non-zero (rewrites AST) | **Replay proof** (re-run the recorded command on the parent; the tree must match the commit) + oracle |
| D. Hand fixes | lint findings needing judgement, type errors | Real | Small batches + impacted tests + surface snapshots + a semantic-review verifier + full oracle at checkpoints |
| E. Structural | moving code into a package layout | High (paths, imports, launch commands) | Separate, opt-in goal with its own go/no-go gate |

From this table:
- **Order work by increasing risk:** A → B → C → D → E. Then each stage's proof covers a smaller residue
  of uncertainty, and a failure is attributable to one class.
- **Never mix classes in a commit.** A mixed commit can only get the weakest proof of its parts.
- **Prefer deterministic proofs over sampled ones.** AST equality and replay proofs are exact. Tests only
  sample behaviour.

### 3. Runtime-visible annotations: the hidden coupling

Type work (class D) usually changes only annotations, and annotations are usually runtime-inert. They stop
being inert wherever code **introspects** them: MCP/FastMCP tool signatures (they become JSON schemas),
`dataclasses`, `typing.get_type_hints`, `inspect.signature`, pydantic, and argparse built from signatures.
Two consequences:
- G0 inventories every introspection site (the *annotation-sensitive modules*).
- In those modules, annotation edits and `from __future__ import annotations` are allowed only when the
  protocol-surface snapshot (O4) still compares EQUAL afterwards. Adding `from __future__ import annotations`
  to them is prohibited outright.

The same reasoning applies to **renames**. Renaming a public symbol (Ruff `N` rules, for example) breaks
importers that static analysis cannot see: dynamic imports, string references, agents and docs. Public
renames are therefore prohibited, and naming findings on public names are suppressed with a reason. The
public-surface snapshot (O5) enforces this.

### 4. Why verification must be bounded

A verifier asked to "find any way this could be wrong" faces an unbounded space: every fix exposes new
surface, so the loop never converges, and the phase blocks even when the work is correct. A verifier asked
"does each pre-registered criterion hold, is any invariant violated **in this diff**, and does each gate bite
when deliberately broken?" faces a finite space and converges. Hence:
- Every acceptance criterion is **pre-registered** before the work it judges, as an executable check.
- Verifier findings are classified. Only **BLOCKING** findings fail a phase: a pre-registered check fails, an
  invariant is violated in the actual diff, or a bite drill misses. Hypothetical weaknesses not exploited in
  the diff are **ADVISORY**. They go to a backlog, which a later goal may harden, and never fail a phase.
- Tamper resistance comes from **behaviour, not config parsing**. Instead of statically proving that no
  config trick can hide a file, inject a known fault and require the gate to go red (**bite drills**), and
  require the analysed-file set to equal the inventory (**scope checks**).

### 5. Why several goals rather than one

`/goal` has a single condition of at most 4,000 characters. A small fast model evaluates it after each turn,
seeing **only the transcript**; it cannot run anything. A single condition covering a whole-repo rewrite would
be either too vague to evaluate or too long to fit. Sequential goals, each with a crisp, script-printed
certificate, keep every condition short and literal. They also make each goal resumable, and give the human
a natural review point between goals.

### 6. Why the certificate is printed by a script

The evaluator cannot tell a true claim from a confident one. So the end-of-goal evidence is a block printed by
`certify.py` **inside a Bash tool result**. The script runs every pre-registered check itself. The condition
tells the evaluator to accept only that block, produced after the goal's final commit, and never prose that
paraphrases it.

---

## Part II: Operating rules

### 7. Pre-flight (the human does this before starting G0)

- [ ] **PF1. Single executor.** No other agent session is changing tooling, configs or Python files in this
  repo. Stop any session already running a migration or tooling plan here. Two executors on overlapping files
  will invalidate each other's oracle comparisons.
- [ ] **PF2. Python target policy.** Default: *the highest CPython (≤ 3.14) whose wheels exist for every native
  runtime dependency on both linux x86_64 and win_amd64, and that leaves the suite oracle EQUAL*, chosen by
  G1's procedure. Override here if a deployment machine is fixed to an older version: `________`.
- [ ] **PF3. Windows.** Default: Windows stays a supported platform. It is verified statically and by a CI job
  defined (non-blocking) but not run until the human pushes. Tick to drop Windows support: [ ]
- [ ] **PF4. Packaging goal G6.** Default **off**: the repo stays an application run from a checkout
  (`package = false`). Tick to authorize G6 (installable package with `[project.scripts]` entry points): [ ]
- [ ] **PF5. Git hooks.** The repo ships its own hook framework (`scripts/githooks`, installed via
  `core.hooksPath`). Default: the executor installs it in the migration worktree, so every commit passes the
  repo's own gates. If a pre-existing hook failure would block *all* commits, the executor records it and
  continues **without** hooks in the worktree (never `--no-verify` on an active hook). Tick to forbid
  installing hooks: [ ]
- [ ] **PF6. Wall-clock budget per goal.** Default: 250 turns. Override: `____`.

Unticked boxes take the default.

### 8. Invariants (a violation fails the current goal)

- **I1. Isolation.** All work happens on local branch `chore/tooling-upgrade-2026-10`, in a dedicated
  `git worktree` outside the main checkout (path recorded in the ledger). The main checkout is never modified.
- **I2. Nothing leaves the machine.** No `git push`, no PR, no publish, no upstream issue. The human pushes.
- **I3. No lost work, no history rewriting.** No `reset --hard`, `clean`, `checkout -- <path>`, `stash drop`,
  `rebase`, `commit --amend` on a verified commit, or force operations. Undo means `git revert`.
- **I4. Oracle equality.** At every checkpoint (§10), every oracle component compares EQUAL, or differs only by
  an entry in the **intended-change register** (`tooling-upgrade/INTENDED_CHANGES.md`). Each entry is added
  *before* the change it covers, with a reason.
- **I5. Tests are never weakened.** No test deleted, renamed without a mapping entry, skipped, xfailed,
  deselected or marked to get green. Per-test assertion strength (O9) never decreases.
- **I6. Gates are never weakened.** No checker, ratchet, hook or CI step is removed, loosened or bypassed.
  No `--no-verify`. Lint and type scope is never narrowed below the G0 inventory except for files classified
  ARCHIVAL in G0. Suppressions follow §12.
- **I7. Class purity.** One change class (§2) per commit. Mechanical commits (B, C) carry their exact
  reproduction command in the body (`Replay: <command>`) and nothing else.
- **I8. Non-Python files are unchanged** except the tooling allowlist (§11, O8).
- **I9. Cross-platform.** No POSIX-only API in Python runtime paths (`fcntl`, `os.fork`, `signal.SIGKILL`
  without a guard, hard-coded `/` path literals, `shell=True` with POSIX syntax). Shell shims are POSIX `sh`
  and run under Git for Windows. Paths are derived, never literal.
- **I10. Conventional Commits**, atomic, one concern each, passing the repo's commitlint config.
- **I11. No global installs.** Only `uv`, `uv run` and `uvx`. If an installer ever runs sandboxed, unset
  `XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_BIN_HOME` first.
- **I12. Tests never touch canonical Redis db 0.** Use `REDIS_DB=15` or the embedded server, as CONTRIBUTING.md requires.

### 9. Roles and rounds (generators and verifiers)

Every phase runs this loop:

```
 ┌─ PRE-REGISTER ─ write/extend the phase's checks in tooling-upgrade/checks/G<n>.toml; commit
 │                  (checks may be ADDED or TIGHTENED later, never removed or loosened)
 ├─ GENERATE ───── the main session (or worktree-isolated generator subagents, §9.4) does the work
 ├─ SELF-CHECK ─── generator runs: certify.py G<n> --phase <id>  + impacted oracle  (must be green)
 ├─ VERIFY A ───── fresh "criteria verifier": re-runs checks, replays mechanical commits, runs drills
 ├─ VERIFY B ───── fresh "semantic reviewer" (class D/E phases only): reads the diff for behaviour change
 ├─ FIX ────────── generator fixes BLOCKING findings in NEW commits; ADVISORY → tooling-upgrade/BACKLOG.md
 └─ repeat VERIFY with NEW fresh verifiers, max 3 rounds; then the phase Fallback
```

**9.1 Verifier A: criteria verifier** (Agent tool, `general-purpose`, fresh context). Prompt, pasted verbatim
with the placeholders filled:

> You are the criteria verifier for phase `<ID>` of docs/python-tooling-upgrade-plan-2026-10.md (worktree
> `<path>`, commits `<start>..<end>`). Read Part II and the phase. Do not edit files. Do, in order:
> (1) run `uv run python tooling-upgrade/certify.py <G> --phase <ID>` and quote its output;
> (2) for every commit whose body has `Replay:`, check out its parent in a scratch worktree, run the
> command, and confirm `git diff` against the commit is empty;
> (3) for class-B commits, run `uv run python tooling-upgrade/oracle.py ast-equal <parent> <commit>`;
> (4) run the phase's bite drills (`certify.py <G> --drills`);
> (5) check invariants I1–I12 against `git diff <start>..<end>` only (not hypotheticals);
> (6) check that `tooling-upgrade/checks/*.toml` history between `<start>` and `<end>` only adds or tightens.
> Classify each finding: BLOCKING (a pre-registered check fails, a replay or AST proof fails, a drill misses,
> or an invariant is violated in this diff, each with the reproducing command and output) or ADVISORY
> (anything else). End with exactly `VERDICT: PASS` (zero BLOCKING) or `VERDICT: FAIL (<n> blocking)`.

**9.2 Verifier B: semantic reviewer** (fresh context; class D and E phases only):

> You are the semantic reviewer for phase `<ID>` (`<start>..<end>`). Your only question: does any hunk change
> runtime behaviour beyond what tooling-upgrade/INTENDED_CHANGES.md registers? Read the diff hunk by hunk.
> Pay special attention to: changed control flow, exception handling (narrowed or broadened excepts), default
> arguments, mutable defaults, truthiness changes (`if x` vs `if x is not None`), string formatting, import
> order with side effects, removed imports (re-exports, side-effect imports), renamed public names,
> annotations in annotation-sensitive modules (list in tooling-upgrade/inventory.json), `__all__`, and tests
> whose assertions changed. For each suspicious hunk, either prove equivalence (cite the code) or show a
> failing input. BLOCKING = a demonstrated or highly probable behaviour change not registered. ADVISORY =
> style concerns. End with `VERDICT: PASS` or `VERDICT: FAIL (<n> blocking)`.

**9.3 Round rules.**
- A round-2 or round-3 verifier gets the previous rounds' BLOCKING findings and must confirm each is closed.
  It may raise new BLOCKING findings only of the classes defined above.
- The same criterion failing in 3 rounds triggers the phase **Fallback**. Every phase has one. Only a
  Fallback that is itself exhausted makes the phase BLOCKED, and only a BLOCKED phase lets the goal be
  declared impossible.
- ADVISORY findings never block, never trigger extra rounds, and are reported at goal end.

**9.4 Parallel generators (optional, class C/D phases with > ~40 files).** Partition the files into disjoint
batches (by top-level package, then by directory, aiming for ≤ 40 files or ≤ 300 findings per batch). Spawn
generator subagents with `isolation: "worktree"`, each owning one batch and forbidden to touch files outside
it. The main session cherry-picks or merges their commits in batch order and runs the impacted oracle after
each merge. Keep at most 4 concurrent generators. Verifiers are always spawned by the main session, never by
generators.

**9.5 Long commands.** The full suite and the full oracle can take a long time. Run them with
`run_in_background` and a timeout of at least 90 minutes, writing to a file in the scratchpad. `/goal`
defers evaluation while background work runs, and sends check-in turns at about 30 min and 1 h. On a check-in
turn, report "still running" and do nothing else. Never poll in a loop.

**9.6 The ledger** (`tooling-upgrade/LEDGER.md`) is the single source of truth across compaction and resume.
Each phase adds one row: phase, status (DONE / DEFERRED / BLOCKED), commit range, verifier rounds with verdict
lines, key numbers, and decisions. On resume: read the ledger, re-run `certify.py` for the last DONE phase,
then continue.

### 10. Checkpoints (when the full oracle runs)

- **Impacted oracle** after every commit in class C and D phases: O3, O5 and O9 restricted to touched
  modules, plus the tests impacted by those modules (`oracle.py impacted <commit>`: the reverse import graph
  from the touched modules, plus the always-run smoke set from G0).
- **Full oracle** (O1–O10) at the end of every phase in G1–G6, and at G7.
- **Full oracle with 2 suite runs** at goal ends (flake control, §11 O1).

---

## Part III: The oracle and the checks (built in G0, before any tooling change)

### 11. Oracle components

All oracle code lives in `tooling-upgrade/` (tracked). It is stdlib-only, so it runs identically before and
after every change, cross-platform. `oracle.py snapshot <label>` writes `tooling-upgrade/snapshots/<label>/`,
and `oracle.py compare <a> <b>` prints one line per component (`O1 EQUAL` / `O1 DIFF <n> <summary>`) and ends
`ORACLE: <k>/10 EQUAL`. A DIFF covered entirely by registered intended changes prints `EQUAL (intended: <ids>)`.

| ID | Component | How it is captured | EQUAL means |
|---|---|---|---|
| O1 | **Test outcomes** | 3 full runs at baseline (`pytest -q -rfE -p no:cacheprovider --continue-on-collection-errors --junitxml`), per node id: stable-pass, stable-fail, flaky, skip | Every baseline id is still collected; no stable-pass id fails *reproducibly* (fails, then fails again in 2 isolated reruns `pytest <id> -p no:randomly`); skip count ≤ baseline; collection errors ≤ baseline |
| O2 | **AST equality** (class B only) | `ast.dump(ast.parse(src), include_attributes=False)` per file, docstrings whitespace-normalised | Identical for every changed `.py` in a format commit |
| O3 | **Import smoke** | Each in-scope module imported in a fresh subprocess with a 20 s timeout. Record OK / ImportError(optional-dep) / other error | The OK set does not shrink; no OK module becomes an error |
| O4 | **Protocol and entry-point surface** | (a) `--help` of every argparse/CLI entry point found in G0 (normalised whitespace); (b) the CLI verb list; (c) the MCP server's tool list with full input schemas, obtained in-process through the MCP SDK; (d) exit codes of the documented no-side-effect commands | Byte-equal after normalisation, except registered intended changes |
| O5 | **Public symbol surface** | For each OK module: sorted public names (`__all__` if defined, else names not starting with `_`), plus each public function's `inspect.signature` string | No name disappears; no signature changes (annotation text changes are allowed only outside annotation-sensitive modules) |
| O6 | **Repo guardrails** | Exit code + normalised output digest of every script in `scripts/checkers/` (any that need args are run with their documented args or recorded N/A) | Exit code ≤ baseline for each; a newly crashing checker counts as worse |
| O7 | **Documented commands** | Each no-side-effect command in README/CONTRIBUTING/AGENTS quick starts (status, help, doctor-style commands), run with an isolated `REDIS_DB=15` | Same exit code; output shape (line count ±10%, key headings) the same |
| O8 | **Non-Python files** | `git diff --name-only <G0-base>..HEAD` minus `*.py` | Only paths in the tooling allowlist: `pyproject.toml`, `uv.lock`, `.python-version`, `requirements*.txt`, `requirements/**`, `pytest.ini` (deleted), `.github/**`, `.pre-commit-config.yaml`, `.git-blame-ignore-revs`, `.mcp.json`, `.claude/settings.json`, `.gitignore`, `scripts/githooks/*` shell shims, `tooling-upgrade/**`, the docs listed in G5, and generated docs regenerated by their own generators |
| O9 | **Test strength** | Per test function: the count of `assert` statements + `pytest.raises`/`warns` contexts + `assert*` method calls + `pytest.fail` calls | No test function's count decreases; total does not decrease |
| O10 | **Coverage** (advisory unless dropped) | `pytest --cov` branch coverage per package | No package's coverage drops by more than 0.5 pp (a drop is BLOCKING; small noise is tolerated) |

### 12. Suppression policy (pre-registered tamper checks)

These are the **only** anti-tamper rules. They are finite and checked by `certify.py`. Anything else a
verifier imagines is ADVISORY.

- **T1. One config home.** Ruff, basedpyright, ty, pytest and coverage are configured only in `pyproject.toml`
  (plus `ty.toml` only if ty cannot read pyproject). `git ls-files` contains no `ruff.toml`, `.ruff.toml`,
  `pyrightconfig.json`, `setup.cfg`, `tox.ini`, `pytest.ini` or `.coveragerc` (nested ones included). Ruff and
  basedpyright are invoked with explicit `--config pyproject.toml` / `-p pyproject.toml` in Poe tasks.
- **T2. Scope equals inventory.** `ruff check --show-files` and `basedpyright --outputjson` (`filesAnalyzed`)
  cover exactly the G0 in-scope set, minus nothing. Excludes are only the ARCHIVAL classification from G0.
- **T3. Every suppression carries a reason and a rule.** `# noqa: <CODE>  # <reason>`,
  `# type: ignore[<code>]  # <reason>`, `# pyright: ignore[<rule>]  # <reason>`. Blanket forms (`# noqa`,
  `# ruff: noqa`, `# type: ignore` without a code, `# pyright: basic` or `# pyright: <rule>=false` file
  headers) are forbidden. `fmt: off` / `fmt: skip` are allowed only with a reason and only around data
  tables. Ruff `RUF100` (unused noqa) and basedpyright `reportUnnecessaryTypeIgnoreComment` are enabled.
- **T4. Suppression budget.** Total suppressions ≤ 1 per 400 lines of in-scope code, per goal. The generated
  report `tooling-upgrade/SUPPRESSIONS.md` (file, line, code, reason) is regenerated by `certify.py` and
  must match the tree.
- **T5. Per-file ignores** in config are allowed only for structural patterns listed in §16 (for example,
  `S101` in tests), each with a comment.
- **T6. Tasks really run the tools.** `uv run poe -d <task>` (dry run) shows the expected command for each gate
  task, and the gate tasks never contain `--fix`, `--exit-zero`, `|| true` or `--skip`.
- **T7. Test runs are real.** A suite record counts only `passed + failed + error` as run. The run count must
  be ≥ the baseline count, and the skip count ≤ the baseline count.

### 13. Bite drills (pre-registered; prove each gate can fail)

`certify.py <G> --drills` creates a throwaway worktree at HEAD (sharing the main `.venv` via
`UV_PROJECT_ENVIRONMENT`, read-only use), applies one fault per drill, runs the named gate, expects
non-zero, removes the worktree, and prints `D<nn> BIT` or `D<nn> MISSED`. It ends `DRILLS: <bit>/<total> BIT`.
A drill whose gate does not exist yet prints `MISSED (gate absent)`. Each goal lists which drills must BIT.

| ID | Fault injected | Gate that must go red |
|---|---|---|
| D01 | New in-scope file with mis-formatted code | `poe fmt-check` |
| D02 | Unused import (`F401`) in a new in-scope file | `poe lint-check` |
| D03 | Bare `except:` in a new file | `poe lint-check` |
| D04 | `x: int = "s"` in a new module under `core/` | `poe types` |
| D05 | Root `ruff.toml` that excludes `core/` + a mis-formatted core file | `poe gate` (T1/T2) |
| D06 | File-level `# ruff: noqa` on a file with a finding | `poe gate` (T3) |
| D07 | `# pyright: basic` header on a core file | `poe gate` (T3) |
| D08 | Dependency added to pyproject without relocking | `poe lock-check` |
| D09 | Hand edit to a generated requirements file | `poe lock-check` |
| D10 | `uses: actions/checkout@v4` (tag, not SHA) in a workflow | `poe ci-lint` (zizmor + actionlint + pin check) |
| D11 | `permissions: write-all` in a workflow | `poe ci-lint` |
| D12 | A test that `assert False` in a new test file | `poe test-fast` (the file is in its selection) |
| D13 | Mis-formatted staged file, then `git commit` in the drill worktree | the pre-commit hook (only if PF5 hooks are installed) |
| D14 | A public function removed from a core module | `oracle.py compare` (O5 DIFF) |
| D15 | `poe gate` task edited to add `|| true` | `certify.py` T6 |

### 14. Goal checks files

`tooling-upgrade/checks/G<n>.toml` lists named checks:
`[[check]] id = "G2.fmt" cmd = "uv run poe fmt-check" expect = 0 phase = "G2.P1"`. `certify.py G<n>` runs
them all, plus T1–T7, the required drills and `oracle.py compare g0 HEAD`, and prints:

```
=== CERTIFICATE G<n> ===
HEAD <sha> | branch chore/tooling-upgrade-2026-10 | worktree clean: yes | pushed: no
CHECKS <passed>/<total> PASS
TAMPER T1-T7 PASS
DRILLS <bit>/<required> BIT
ORACLE <k>/10 EQUAL
RESULT: G<n> CERTIFIED          (or RESULT: G<n> NOT CERTIFIED: <first failure>)
=== END CERTIFICATE ===
```

`certify.py` refuses to print `CERTIFIED` if the worktree is dirty, if HEAD is not on the branch, if any
`checks/*.toml` entry was removed or loosened since its registration commit (diffed through git history), or
if the newest full-suite record predates the newest commit touching `*.py`, `pyproject.toml` or `uv.lock`.

---

## Part IV: The goals

Each goal below has **phases** (the generate → verify loop of §9), **exit criteria** (pre-registered in its
checks file), a **Fallback**, and a ready-to-paste **`/goal` condition**. Run the goals in order. Between
goals the human may review the branch, and that is the intended pause point.

### G0: Inventory, oracle and baselines (no tooling change)

**Purpose:** make "functionality" measurable before touching anything.

- **G0.P1 Setup.**
  - Confirm PF1 (no other executor): `git worktree list`, plus any repo-native presence or lock command
    (for example `agent_cli.py locks`, if it exists and works).
  - Create the branch and worktree: `git worktree add <scratch>/tooling-wt -b chore/tooling-upgrade-2026-10 master`.
  - Copy this plan into the worktree and commit it (`docs(plan): add python tooling upgrade plan`).
  - Install hooks per PF5. Create `tooling-upgrade/LEDGER.md`.
- **G0.P2 Inventory** (`tooling-upgrade/inventory.json`, generated by `oracle.py inventory`).
  - Classify every tracked `.py` as RUNTIME, SCRIPT, TEST, TOOLING or ARCHIVAL. ARCHIVAL requires **proof**:
    the file is not imported by any non-archival file (static import graph), not referenced by path from any
    non-archival file, CI config, hook or doc command, and lives under a history tree (`research/`,
    `docs/library/`, `docs/_archive/`, `chronicles/`, `fences/`, `session_logs/`). Files that fail any part of
    the proof are in scope.
  - List entry points: argparse/`__main__` modules, `[project.scripts]` if any, hook scripts, and commands in docs.
  - List the annotation-sensitive modules (§3): grep plus AST for `get_type_hints`, `__annotations__`,
    `inspect.signature`, `dataclass`, `pydantic`, FastMCP/`@*.tool` decorators.
  - List dependency consumers outside uv: `requirements*.txt` readers (docs, CI, Windows setup scripts).
  - Record the platform matrix the docs promise.
  - Record the tooling facts: Python versions in use (`.venv`, CI, hooks, `.claude/settings.json`), uv
    version, current config files, and which suite runtime counts as "full".
- **G0.P3 Oracle code.** Write `tooling-upgrade/oracle.py` (snapshot, compare, ast-equal, impacted,
  inventory) and `tooling-upgrade/certify.py` (checks, T1–T7, drills, certificate), stdlib-only. Write unit
  tests `tests/test_tooling_upgrade_oracle.py`: for every component, an EQUAL fixture and a DIFF fixture in
  `tmp_path`. Then write `checks/G0.toml` … `checks/G7.toml` **now**, all of them, so that every later goal's
  acceptance is registered before its work exists. Later phases may only add or tighten.
- **G0.P4 Baselines.**
  - Run the suite 3 times in the background → `snapshots/g0/O1`.
  - Run the other oracle components → `snapshots/g0/`.
  - Commit the snapshots, minus large raw logs. Store sha256 digests of the raw logs in the snapshot instead.
  - Measure (numbers only, for the ledger) Ruff findings per rule with the target config of §16,
    `ruff format --check` counts, basedpyright errors in standard mode, ty diagnostic count, suite durations
    (`--durations=50`), and coverage.
  - If `ruff format --check` panics on any file, bisect, record the file and Ruff version, and plan to
    exclude it until a Ruff release fixes it (an intended exclusion, listed in INTENDED_CHANGES).
- **G0.P5 Drill self-test.** Run `certify.py G7 --drills`. All drills must print `MISSED (gate absent)` or
  `MISSED`. This proves the drills detect absence, so a later `BIT` means something. Run
  `oracle.py compare g0 g0`, which must print `ORACLE: 10/10 EQUAL`. Then inject a removed public function in
  a scratch worktree and confirm O5 DIFF (the D14 self-test).

**Exit criteria (checks/G0.toml):** oracle unit tests pass; inventory exists, and every ARCHIVAL entry
carries its proof fields; `g0` snapshot is complete with 3 suite runs; self-compare is EQUAL; the drill
self-test shows 15/15 MISSED; all G0–G7 checks files are committed.

**Fallback:**
- If a 3-run baseline exceeds the time budget, use 2 runs and widen O1's reproduction requirement to
  3 reruns.
- If the MCP schema cannot be captured in-process, capture it by launching the server over stdio with a
  20 s timeout.
- If an entry point has side effects even under `--help`, record it as N/A in O4 with the reason.

**`/goal` condition for G0:**
```
Execute goal G0 of docs/python-tooling-upgrade-plan-2026-10.md (Part IV) in a dedicated git worktree on local branch chore/tooling-upgrade-2026-10, obeying Part II (invariants I1-I12, the generator/verifier loop of section 9: each phase needs a fresh verifier subagent returning "VERDICT: PASS", max 3 rounds, then the phase Fallback). Make no tooling change in G0: only the plan copy, tooling-upgrade/** files, the oracle tests and the ledger.
MET only when the latest turn contains, inside a Bash tool result produced after the final G0 commit: (1) the output of `uv run python tooling-upgrade/certify.py G0` ending "RESULT: G0 CERTIFIED"; (2) `uv run python tooling-upgrade/certify.py G7 --drills` showing every drill MISSED (the self-test); (3) `uv run python tooling-upgrade/oracle.py compare g0 g0` ending "ORACLE: 10/10 EQUAL". The turn must also quote the final verifier line "VERDICT: PASS" and the G0 rows of tooling-upgrade/LEDGER.md.
NOT met if: anything was pushed; any file outside tooling-upgrade/**, the plan copy, tests/test_tooling_upgrade_oracle.py, and .gitignore exceptions changed; --no-verify was used. Declare impossible only if a phase is BLOCKED after its Fallback, naming the check and the evidence. Stop after 250 turns.
```

### G1: Foundation: uv, dependencies, Python pin, launcher, task runner (class A)

- **G1.P1 Dependency truth.**
  - `uvx deptry .`, scoped by the inventory, finds missing, unused and misplaced dependencies. Fix the
    declarations so that pyproject `[project].dependencies` equals what RUNTIME and SCRIPT code imports.
  - Optional features stay in named groups (`ml`, `browser`) with import guards (verified via O3:
    ImportError(optional-dep) is allowed only for modules that guard the import).
  - Tooling (`pytest`, `pre-commit`, and so on) moves to `[dependency-groups].dev`, unless runtime code shells
    out to it. In that case it stays in dev, and a pyproject comment records that `uv sync` installs dev by
    default.
  - `pre-commit` is replaced by `prek`.
  - dev = `ruff`, `basedpyright`, `ty`, `pytest`, `pytest-cov`, `pytest-xdist`, `pytest-randomly`,
    `poethepoet`, `prek`, `deptry`.
- **G1.P2 Python version.**
  - Procedure: for candidates 3.14, 3.13 and 3.12, run `uv lock --python <v>` (universal). Check the lock's
    wheels: every native dependency needs a cp3XX or abi3 wheel for `manylinux*_x86_64` and `win_amd64`
    (PF3).
  - Take the highest passing candidate. `uv sync`, then O1 (1 run) + O3 + O4 + O5 against g0.
  - If not EQUAL, step down one version.
  - Write `.python-version`. Set `requires-python = ">=<floor>"`, where the floor is the minimum the docs
    promise for any deployment (PF2), never above the pin.
  - Make every Python mention agree: CI, hooks, `.claude/settings.json` `-p` flags, docs.
- **G1.P3 uv settings.**
  - `[tool.uv]`: `package = false` (unless G6 later changes it), `required-version = ">=<current minor>"`,
    `exclude-newer = "7 days"` (supply-chain cooldown), `default-groups = ["dev"]`.
  - Commit `pyproject.toml`, `uv.lock` and `.python-version` (tracked).
- **G1.P4 Generated requirement files.**
  - If G0 found pip consumers (Windows setup, docs), keep `requirements.txt` (+ group files) **generated** by
    `uv export --no-hashes --no-emit-project --no-annotate [--group …]` behind a "GENERATED — do not edit"
    header.
  - If there are no consumers, delete them and update the docs.
- **G1.P5 One launcher.**
  - Every executable surface (git hook shims, `.mcp.json`, CI, `.claude/settings.json` hook commands and
    allowlist, the `python_launcher()`-style helper if present, docs) runs Python through `uv run`.
  - A POSIX `sh` shim provides `pyrun` (`$AKASHIC_PYTHON` → `uv run --frozen --quiet` → `py` → `python3`).
  - On Windows the `py` path remains a documented fallback.
  - User-visible text that changes (help messages naming the launcher) goes into INTENDED_CHANGES before the
    edit.
- **G1.P6 Poe tasks** (each with `help`):
  - `fmt`, `fmt-check`, `lint` (`--fix`), `lint-check`, `types`, `types-ty`, `lock`, `lock-check`, `deps`
    (deptry), `ci-lint` (zizmor + actionlint + SHA-pin check), `guardrails` (every `scripts/checkers/*`,
    with documented args), `test` (full suite, writes the suite record), `test-fast` (the impacted selection,
    or the smoke set from G0, under 3 min), `oracle` (`oracle.py snapshot head && compare g0 head`), and
    `gate`.
  - `gate` runs `fmt-check`, `lint-check`, `types`, `lock-check`, `deps`, `ci-lint`, `guardrails` and
    `test-fast` in order and stops at the first failure.
  - Gate tasks not yet satisfiable (format and lint before G2–G3) exist but are **not** in `gate` until their
    goal adds them. The checks files record when each joins.
  - Ruff and basedpyright invocations pass explicit config (T1).
- **G1.P7 Pytest config.**
  - Move `pytest.ini` into `[tool.pytest.ini_options]` with the same meaning (testpaths, `-q`, the
    `filterwarnings` error rule, comments), and add `--strict-markers` and `--strict-config`.
  - `pytest --collect-only -q` must give the identical id set before and after (O1 collection).
  - Delete `pytest.ini`.

**Exit criteria (checks/G1.toml):**
- `uv lock --check`; `uv sync --locked` in a fresh clone; `deptry` clean.
- `.python-version` agrees with CI, hooks and settings.
- No bare `py ` in executable surfaces (grep over hooks, `.mcp.json`, workflows, settings `command` fields).
- The MCP server starts via `.mcp.json` and lists its tools (O4c EQUAL).
- `poe -d` shows each task's command (T6).
- Collection is identical; full oracle EQUAL; drills D08 and D09 BIT.

**Fallback:**
- If `exclude-newer = "7 days"` blocks resolution because a locked version is younger, add a per-package
  `exclude-newer-package` override with a removal date. Never drop the global setting.
- If deptry flags a dynamic import as unused, add a `[tool.deptry]` per-package ignore with a reason.

**`/goal` condition for G1** (the same pattern as G0, with G1 substituted):
```
Execute goal G1 of docs/python-tooling-upgrade-plan-2026-10.md on branch chore/tooling-upgrade-2026-10 in its worktree, starting from the G0-certified HEAD recorded in tooling-upgrade/LEDGER.md, obeying Part II (I1-I12; section 9 loop: fresh verifier subagent "VERDICT: PASS" per phase, max 3 rounds, then Fallback). Only class-A (metadata/launcher/config) changes; one concern per commit.
MET only when the latest turn contains, inside Bash tool results produced after the final G1 commit: (1) `uv run python tooling-upgrade/certify.py G1` ending "RESULT: G1 CERTIFIED" and showing "ORACLE 10/10 EQUAL"; (2) a fresh `git clone` of the worktree into a scratch dir where `uv sync --locked` exits 0 and `uv run poe gate` exits 0, with output tails; (3) the final verifier's "VERDICT: PASS" quoted, plus the G1 ledger rows.
NOT met if: anything pushed; any test deleted, skipped or deselected; any guardrail script exits worse than in the g0 snapshot; --no-verify, reset --hard, clean or force used; a non-allowlisted non-Python file changed. Declare impossible only if a phase is BLOCKED after its Fallback, naming check + evidence. Stop after 250 turns.
```

### G2: Format the whole repo (class B)

- **G2.P1 Config.**
  - `[tool.ruff]`: `target-version` from the G1 floor, `line-length` chosen by data (count of files changed
    at 100 vs 120; choose fewer, and 120 on a tie within 5%), `extend-exclude` = ARCHIVAL paths plus any
    recorded panic files, and nothing else (T2).
  - Format settings: Ruff defaults (`quote-style = "double"`, `docstring-code-format = true`).
- **G2.P2 Line-sensitive artifacts.**
  - Find every artifact that stores line numbers or verbatim code: checker baselines, citation maps,
    rewrite maps, doc snippets with line anchors (grep for `:\d+` anchors into `.py` paths under docs and
    state).
  - For each one, record its regeneration command. A reformat may be followed by **separate** regeneration
    commits whose counts do not rise.
- **G2.P3 The format commit.**
  - `uv run poe fmt`, then `git add` in-scope `.py` only, then `style: apply ruff format repo-wide`, with
    `Replay: uv run ruff format --config pyproject.toml` in the body.
  - Then add `.git-blame-ignore-revs` with the SHA, and set `git config blame.ignoreRevsFile` (local; noted
    in CONTRIBUTING later).
  - If one commit is too big for the hooks, split it by top-level directory. Each part is still pure and
    replayable.
- **G2.P4 Proofs.** Run `oracle.py ast-equal <parent> <format-commit>` (every file EQUAL), then the full
  oracle, then the regeneration commits for line-sensitive artifacts, then O6 again.
- Add `fmt-check` to `gate`.

**Exit criteria:** `fmt-check` exit 0; AST-equal 100%; replay proof; full oracle EQUAL; D01 and D05 BIT;
`.git-blame-ignore-revs` valid (every SHA is a `style:` commit).

**Fallback:** if a file's AST differs (a Ruff bug), revert that file in a new commit, exclude it with an
INTENDED_CHANGES entry naming the Ruff version, and continue. If more than 5 files are affected, BLOCKED.

**`/goal` condition for G2:** the same as G1, with "class-B (formatter) changes only", item (1) for G2, and an
added item: "(4) the output of `uv run python tooling-upgrade/oracle.py ast-equal <parent> <format-commit>`
for every format commit, ending `AST: <n>/<n> EQUAL`."

### G3: Lint to zero (classes C then D)

**Target rule set** (end state: zero findings, suppressions under §12):
`select = ["E","W","F","I","UP","B","C4","SIM","PIE","PERF","RUF","T10","T20","ASYNC","LOG","G","N","A","PT","RET","S","BLE","PTH","TC","ERA","PGH","FLY","ISC","ICN","Q"]`,
`ignore = ["E501" (formatter owns length), "ISC001","Q000"–"Q003" (formatter conflicts), "COM812"]`.
Per-file (T5): `tests/**` → `S101`, `PLR2004`-style magic values if selected; `scripts/**` → `T20` (scripts
print by design). Each has a comment. **Stretch, ratchet only (not zero):** `D` (docstrings), `ANN`, `ARG`,
`FBT`, `TRY`, `PL`. These are tracked as counts that may never rise, in `checks/G3.toml`.

- **G3.P1 Safe autofix waves (class C).** One rule family per commit, in this order: `I`, `UP`, `F401`*,
  `C4`, `PIE`, `RUF` (safe subset), `SIM` (safe), `PT` (safe), `RET` (safe), `ISC`, `FLY`.
  - Each commit runs `ruff check --fix --select <FAMILY>` with no `--unsafe-fixes`, and records `Replay:`.
  - After each: impacted oracle + `test-fast`. Run the full oracle after every 3 waves.
  - *F401 is special. In `__init__.py` and in any module whose name appears in O5 importers or in dynamic
    imports, an apparently unused import may be a re-export or a side-effect import. Run F401 with
    `--fix` only outside those files. Inside them, convert to explicit `__all__` or explicit
    `import x as x` re-exports by hand (class D). O5 must stay EQUAL.
  - `UP` in annotation-sensitive modules: the wave is allowed, but O4c must be EQUAL afterwards. If not,
    revert those files in a new commit and handle them by hand.
- **G3.P2 Unsafe-but-mechanical fixes (class C, reviewed).** Families whose fixes Ruff marks unsafe (for
  example `PTH`, some `SIM`) are applied per directory batch with `--unsafe-fixes --select <RULE>`, each with
  `Replay:`, **plus** Verifier B review, because unsafe means semantics can shift. `PTH` conversions
  that touch string/Path mixing at API boundaries (functions returning `str` paths to callers) are rejected and
  done by hand or suppressed with a reason.
- **G3.P3 Hand fixes (class D)**, in batches per §9.4.
  - Policy for judgement rules: `BLE001`/`E722`: a deliberately fail-soft `except Exception` gets a
    `# noqa: BLE001  # fail-soft: <why>` **only** if it logs or the docstring documents the fallback;
    otherwise narrow the exception type. A bare `except:` becomes `except Exception:`, which is strictly
    narrower, and is registered in INTENDED_CHANGES because it stops catching `KeyboardInterrupt`/`SystemExit`.
    Verify that no code path relies on catching those.
  - `S` (bandit) findings are fixed, or suppressed with a threat-model reason. `subprocess` with `shell=True`
    is fixed to argv form unless the command is user-supplied shell by design.
  - `N` on public names → suppress with `# noqa: N8xx  # public API name` (renames prohibited, §3). On
    private names → rename (O5 is unaffected).
  - `ERA` (commented-out code): delete, unless the comment is documentation (then reword it so it is not code).
  - `E402`: in scripts and tests that bootstrap `sys.path`, restructure into a `_bootstrap` import where
    trivial; otherwise suppress with the reason "sys.path bootstrap".
- **G3.P4 Lock it.**
  - Add `lint-check` to `gate`, and add Ruff's `--statistics` totals for the stretch families to the ratchet
    file.
  - Enable `RUF100`.
  - Regenerate `SUPPRESSIONS.md` (T4 budget).

**Exit criteria:** `ruff check` exit 0 over the full scope (T2 equals inventory); every class C commit is
replay-verified; Verifier B PASS on every class D batch and every unsafe-fix batch; full oracle EQUAL with 2
suite runs; T3 and T4 hold; drills D02, D03, D06 and D14 BIT.

**Fallback:**
- A rule family whose fixes repeatedly break the oracle (3 rounds) moves from the zero set to the stretch
  ratchet, with an INTENDED_CHANGES entry and a reason. At most 3 families may be demoted this way;
  beyond that, BLOCKED.
- A demoted family is listed in the final report.

**`/goal` condition for G3:** the G1 pattern with "classes C then D", item (1) for G3, plus:
"(4) `uv run ruff check --config pyproject.toml --statistics` printing no findings and
`uv run python tooling-upgrade/certify.py G3 --drills` ending `DRILLS 4/4 BIT`; (5) a Verifier B
`VERDICT: PASS` quoted for each class-D batch listed in the ledger."

### G4: Types to zero (class D)

- **G4.P1 Config.** `[tool.basedpyright]`:
  - `typeCheckingMode = "standard"` for all in-scope code, `pythonVersion` = the G1 floor, `venvPath`/`venv`
    pointing at the project `.venv`.
  - `include` = the inventory scope (TEST files included, with `executionEnvironments` giving tests `basic`
    if standard proves too noisy there; recorded as intended).
  - `reportMissingModuleSource = "none"` only for platform-specific optional dependencies (for example
    Windows-only UI automation).
  - `reportUnnecessaryTypeIgnoreComment = "error"`, `enableTypeIgnoreComments = true`.
  - `[tool.ty]`: the same scope.
- **G4.P2 Triage by defect value.** Bucket the errors by rule. Fix in this order: (1) real defects
  (`reportUndefinedVariable`, `reportAttributeAccessIssue` on real attributes, `reportCallIssue`,
  `reportArgumentType` with wrong arity or kinds, `reportOptionalMemberAccess` where None is really possible);
  (2) missing generics and annotations (`reportMissingTypeArgument` and similar: annotation-only);
  (3) library-stub gaps (add `types-*` stub packages to dev, or narrow with `cast` plus a reason);
  (4) the residue, which gets `# pyright: ignore[<rule>]  # <reason>` within the T4 budget.
  - Each **real defect** fix is a behaviour change by definition. It needs a regression test that fails
    before and passes after, plus an INTENDED_CHANGES entry ("fixes latent bug: …").
  - Annotation-only batches in annotation-sensitive modules must keep O4c and O5 EQUAL.
  - Batches follow §9.4 (disjoint directories, parallel generators allowed).
  - Run Verifier B on every batch.
- **G4.P3 Strict islands.** Modules written or substantially touched by this effort, and the oracle and
  certify tooling, opt into strict (`# pyright: strict` is the one allowed file-level pyright header, which T3
  treats as tightening).
- **G4.P4 ty.** `poe types-ty` runs informationally. Record its count in the ledger. When ty reports 1.0
  stable, the human may decide to swap gates (out of scope here).
- Add `types` to `gate`.

**Exit criteria:** `basedpyright` exit 0 with **0 errors** and no baseline file; T3 and T4 hold; every
latent-bug fix has a regression test that fails on its parent commit (the verifier runs it on the parent);
full oracle EQUAL (or intended) with 2 suite runs; D04 and D07 BIT.

**Fallback:**
- If zero errors is not reachable within the T4 budget, stop at the budget and switch the remaining
  directories to a **committed basedpyright baseline** that may only shrink, with the exact remaining counts
  in the final report.
- This is the only goal where a baseline is an acceptable terminal state, and it is reported as PARTIAL.

**`/goal` condition for G4:** the G1 pattern with item (1) for G4, plus "(4) `uv run poe types` output ending
`0 errors` (or, under the G4 Fallback, `certify.py G4` stating PARTIAL with the baseline counts);
(5) for each latent-bug fix in INTENDED_CHANGES, the regression test failing on the parent commit and passing on
HEAD, both outputs quoted."

### G5: Tests, hooks, CI, dependency automation and docs (class A, plus small D)

- **G5.P1 Test tooling experiments** (adopt only on evidence):
  - `pytest-xdist` (`-n auto --dist loadfile`): adopt for `test` if O1 is EQUAL on 2 consecutive runs. Tests
    sharing Redis db, ports or files may need a per-worker resource fixture. If that is more than a small
    conftest change, keep the suite serial and use xdist for `test-fast` only.
  - `pytest-randomly`: 3 seeds. Adopt if all 3 are O1 EQUAL; otherwise install it with `-p no:randomly`
    default and list the order-dependent tests in BACKLOG.
  - `--doctest-modules` on RUNTIME packages: adopt if green.
  - Coverage reporting is always on, with a ratchet of no package drop > 0.5 pp (O10).
- **G5.P2 Hooks.**
  - `.pre-commit-config.yaml`: every `rev` is a full SHA with a version comment. Hooks: `ruff-check`
    (`--fix`), `ruff-format`, `uv-lock`, `uv-export` (one per generated file), `check-toml`, `check-yaml`,
    `check-merge-conflict`, `check-added-large-files`, `zizmor`, `actionlint`, and `exclude` = the ARCHIVAL
    paths. No whitespace or EOF fixers over non-Python trees (I8).
  - Integrate prek into the repo's **own** hook framework as a stage in its pre-commit backstop (staged
    files only), failing closed on findings and open with a loud warning when prek is missing (matching the
    framework's crash-versus-finding policy), with a unit test.
  - Never `prek install`, because it would fight `core.hooksPath`.
- **G5.P3 CI** (`.github/workflows/ci.yml`):
  - Top-level `permissions: contents: read`; `concurrency` with cancel-in-progress; `timeout-minutes` per
    job; every `uses:` pinned to a 40-hex SHA with a `# vX.Y.Z` comment (resolved at execution time via
    `git ls-remote`); `actions/checkout` with `persist-credentials: false`; `astral-sh/setup-uv` with cache;
    `uv sync --locked`.
  - Jobs:
    - `gate` runs `uv run poe gate`.
    - `test` keeps the existing service containers and env, and runs `uv run poe test`.
    - `ty` (`continue-on-error: true`).
    - `windows-smoke` (`windows-latest`, `continue-on-error: true` until the human promotes it) runs
      `uv sync --locked`, a status command and the portability tests.
    - `ci-lint` (zizmor + actionlint).
  - Preserve every existing guardrail step and its explanatory comments; they now run via `poe guardrails`.
  - `.github/dependabot.yml`: ecosystems `uv` and `github-actions`, weekly, `cooldown: {default-days: 7}`,
    minor and patch grouped.
  - Local proof, since nothing is pushed (I2): `actionlint`, `uvx zizmor`, then replay every `run:` step of
    every job locally in order with the job env. Record the Windows job as "defined, not executed".
- **G5.P4 Docs.**
  - CONTRIBUTING, README, AGENTS and DEPLOY (or equivalents) present `uv sync` / `uv run poe gate` /
    `uv run poe test` as the primary path, with `py` as the Windows fallback. Add the blame-ignore setup, the
    suppression policy (§12) and "never `--no-verify`".
  - Regenerate generated docs with their own generators, then run their `--check`.
  - Every doc changed is in the O8 allowlist.

**Exit criteria:** experiment verdicts recorded with evidence; `prek run --all-files` exit 0; the hook stage
test passes; D10, D11, D13 (if hooks are installed) and D15 BIT; the local CI replay is green; the docs grep
shows uv as the primary path; full oracle EQUAL.

**Fallback:**
- Experiments are optional by design: a failure is recorded, not blocking.
- zizmor findings that cannot be fixed without changing CI semantics take
  `# zizmor: ignore[<rule>]  # <reason>`, at most 2; beyond that, BLOCKED.

**`/goal` condition for G5:** the G1 pattern with item (1) for G5, plus "(4) the local replay of every CI job's
run steps with exit codes; (5) `uv run prek run --all-files` exit 0."

### G6: Packaging and layout (class E, only if PF4 is ticked; otherwise mark it SKIPPED in the ledger)

Deductive go/no-go, decided in **G6.P1** before any edit. Proceed only if all three hold:
1. a named consumer benefits (installable CLI on PATH, reuse by another project, or wheel deployment);
2. every path assumption (repo-root derivation, data paths, hook paths, docs commands) is enumerated and
   each has a planned replacement;
3. a spike in a throwaway worktree, run with `package = true`, `uv_build` (or hatchling if `uv_build`
   cannot express the multi-package layout) and `[project.scripts]` entry points mapped 1:1 to existing
   commands, reaches full oracle EQUAL.

Otherwise record NO-GO with the failing condition and stop G6. NO-GO is a valid terminal state.

If GO: move to the target layout in one pure `git mv` commit (class E, replayable), then a separate import
and path-fix commit (class D, Verifier B), then the entry points. Both the old (`uv run agent_cli.py`) and
new (`uv run aurora …`) commands must work, and the old ones are kept as thin shims. Exit criteria: full
oracle EQUAL (O4 additionally covers the new entry points as aliases), a fresh-clone install works, and docs
are updated.

### G7: Certification (fresh everything)

- **G7.P1:** run the full suite twice on HEAD (background), then take the full oracle snapshot `final` and
  compare `g0 final`.
- **G7.P2:** in a fresh `git clone --no-hardlinks` of the worktree, with no shared `.venv`, run
  `uv sync --locked`, `uv run poe gate`, the MCP surface capture (O4c), and `oracle.py compare g0 <clone-snapshot>`
  (minus O1, which P1 covers).
- **G7.P3:** run `certify.py G7 --drills`. All 15 drills must BIT (D13 may be N/A under PF5).
- **G7.P4: final certifier** (fresh subagent). Give it the full range `G0-base..HEAD` and the Verifier A
  prompt, extended with: re-derive every checks file's results independently; check that the checks files
  were only ever added to or tightened (`git log -p tooling-upgrade/checks`); sample 20 random class-D hunks
  for Verifier B review; confirm that every INTENDED_CHANGES entry predates its change commit.
- **G7.P5: final report** in the ledger: the per-goal summaries; tool numbers before → after (format files,
  lint findings, type errors, suppressions, coverage, suite time); demoted rule families; ADVISORY backlog;
  what the human must do (push; watch CI; run the Windows job and promote it to blocking; install uv on the
  Windows machine); ty status.
  - Commit the report, then re-run `certify.py G7` so the certificate postdates the last commit.

**`/goal` condition for G7:**
```
Execute goal G7 of docs/python-tooling-upgrade-plan-2026-10.md on branch chore/tooling-upgrade-2026-10 (worktree per tooling-upgrade/LEDGER.md), obeying Part II. G0-G5 must be CERTIFIED in the ledger and G6 CERTIFIED, NO-GO or SKIPPED. No new tooling work: only fixes for findings, the report, and the ledger.
MET only when the latest turn contains, inside Bash tool results produced after the final commit: (1) `uv run python tooling-upgrade/certify.py G7 --drills` ending "RESULT: G7 CERTIFIED" with "ORACLE 10/10 EQUAL" and "DRILLS 15/15 BIT" (or 14/14 when hook drill D13 is N/A under PF5); (2) a fresh `git clone --no-hardlinks` where `uv sync --locked` and `uv run poe gate` exit 0, tails quoted; (3) `oracle.py compare g0 final` ending "ORACLE: 10/10 EQUAL"; (4) `git status --porcelain` empty and `git log origin/master..HEAD --oneline` listing the commits (nothing pushed). Also quote the final certifier subagent's "VERDICT: PASS" and the ledger's per-goal status table.
NOT met if: any push; any test deleted, skipped or deselected; any checks-file entry removed or loosened; any guardrail script exits worse than at g0; --no-verify, reset --hard, clean or force used. Declare impossible only if a phase is BLOCKED after its Fallback, naming check + evidence. Stop after 250 turns.
```

---

## Part V: Reference

### 15. Starting facts (observed 2026-10-01; G0 re-measures them all)

- 1,615 tracked `.py` files: tests 776, core 265, research 227, scripts 147, docs 101, arsenal 53, agent 34,
  root 8, other 4.
- `research/`, `docs/` and other history trees are ARCHIVAL candidates and still need G0's proof.
- `pyproject.toml` with `package = false`, runtime deps that include `pytest` and `pre-commit`, and groups
  `ml` and `browser`. `uv.lock` is tracked.
- `requirements.txt` is hand-kept in step with pyproject; `requirements/gemini-web.txt` also exists.
- `pytest.ini` (testpaths, `-q`, return-not-none as error).
- No Ruff, type checker or formatter config. No `.python-version`. The `.venv` runs 3.12; CI runs 3.11.
- CI: a single pip-based job on `actions/setup-python` (tag pins), a Redis service, and 5 guardrail
  steps + pytest. There is no `permissions:` block and no Dependabot.
- Git hooks: a custom framework in `scripts/githooks` with Python backstops behind `sh` shims, which already
  carry a `py` → `uv run` → `python3` fallback, installed via `core.hooksPath`.
- `.mcp.json` launches the MCP server with `uv run`.
- Node subprojects (`apps/docs`, `agent/harness/dsh_plugin`) and the commitlint/changelog configs are out
  of the Python scope. They are untouched, apart from commitlint scopes if commits need new ones.

### 16. Target configuration skeleton (G1–G5 fill in values from measurements)

```toml
[project]
requires-python = ">=<floor from G1>"
dependencies = [ ... runtime only, deptry-clean ... ]

[dependency-groups]
dev = ["ruff", "basedpyright", "ty", "pytest", "pytest-cov", "pytest-xdist", "pytest-randomly",
       "poethepoet", "prek", "deptry"]
ml = [...]
browser = [...]

[tool.uv]
package = false
required-version = ">=0.12"
exclude-newer = "7 days"
default-groups = ["dev"]

[tool.ruff]
target-version = "py3XX"
line-length = 100            # or 120, chosen by G2.P1 data
extend-exclude = [ ...ARCHIVAL paths from inventory.json only... ]

[tool.ruff.lint]
select = [ ...G3 target set... ]
ignore = ["E501", "ISC001", "COM812"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]         # pytest asserts are the point
"scripts/**" = ["T20"]        # scripts print to their user by design

[tool.basedpyright]
typeCheckingMode = "standard"
pythonVersion = "3.XX"
venvPath = "."
venv = ".venv"
include = [ ...inventory scope... ]
reportUnnecessaryTypeIgnoreComment = "error"

[tool.ty.environment]
python-version = "3.XX"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-q", "--strict-markers", "--strict-config"]
filterwarnings = ["error::pytest.PytestReturnNotNoneWarning"]
xfail_strict = true

[tool.coverage.run]
branch = true
source = ["core", "agent", "arsenal", "scripts"]

[tool.poe.tasks]
# fmt fmt-check lint lint-check types types-ty lock lock-check deps ci-lint guardrails
# test test-fast oracle gate  (see G1.P6)
```

### 17. Ledger template (`tooling-upgrade/LEDGER.md`)

| Goal.Phase | Status | Commits | Verifier rounds (A/B) | Verdict lines | Numbers and decisions |
|---|---|---|---|---|---|
| G0.P1 | | | | | |

### 18. Commit message conventions used by this plan

- `docs(plan): …` (plan copy); `test(tooling): …` (oracle tests); `chore(tooling): …` (oracle, certify,
  checks files, snapshots, ledger).
- `build(deps): …`, `build(python): …`, `build(tasks): …`; `fix(hooks): …`, `fix(mcp): …`
- `style: apply ruff format …` (class B); `style(lint): apply ruff <FAMILY> fixes` (class C)
- `refactor(lint): …`, `fix(types): …`, `refactor(types): …` (class D)
- `ci: …`, `docs: …`
- Mechanical commits carry a `Replay: <command>` line in the body. Latent-bug fixes carry `Fixes-latent: <INTENDED_CHANGES id>`.
