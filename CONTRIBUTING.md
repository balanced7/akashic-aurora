# Contributing to Akashic Aurora

Thanks for your interest. This is a research project with a strong design spine; the conventions below
are what keep it coherent. They're not bureaucracy — they're the invariants that let the system stay
trustworthy as it grows.

## Setup

See [`docs/DEPLOY.md`](docs/DEPLOY.md). TL;DR: `git clone`, then `uv sync` (installs the locked
environment from `uv.lock`, on the Python pinned in `.python-version`), then
`uv run python bootstrap.py --agent-init` to verify.

**Fallback when uv is not installed:** on Windows use the `py` launcher
(`py -m pip install -r requirements.txt`, then `py bootstrap.py --agent-init`); elsewhere use
`python3`. This is the repo's own launcher policy (`core.paths.python_launcher`): `uv run` wherever
uv and `pyproject.toml` exist, `py` on Windows without uv, `python3` elsewhere.

**Windows checkouts need symlinks.** `.claude/skills` is a symlink to `.agents/skills`, the one
source for agent skills. Enable Developer Mode, then `git config core.symlinks true` and
`git checkout -- .claude/skills`; `tests/test_skills_single_source.py` fails until that is done.

`requirements.txt` and `requirements/gemini-web.txt` are **generated** from `uv.lock` for pip
consumers (`uv run poe lock`; `uv run poe lock-check` fails if they are stale). Never hand-edit them.

### Daily commands

```bash
uv sync                          # install / update the locked environment
uv run poe gate                  # the local gate: fmt-check, lint-check, types, lock-check, deps,
                                 #   guardrails, test-fast (stops at the first failure)
uv run poe test                  # the full suite (REDIS_DB=15), with coverage, vs. the g0 baseline
uv run poe fmt                   # fixer: ruff format
uv run poe lint                  # fixer: ruff check --fix
uv run poe types                 # basedpyright + the suppression policy (below)
uv run prek run --all-files      # the .pre-commit-config.yaml hooks over the whole tree
```

### Cached runs (Turborepo)

`turbo.json` puts the gate and the suite behind Turborepo's uv workspace support (experimental:
`futureFlags.experimentalPythonWorkspaces`). Each gate step is a task with its own inputs, the
steps run in parallel, and a task whose inputs have not changed replays its cached result instead
of running again: an unchanged tree goes from minutes to well under a second.

```bash
uv run poe cached-gate           # = npx --yes turbo@2.11.7 run gate --filter=aurora
uv run poe cached-test           # = ... run test: the full suite, cached on the whole tree
```

- Inputs are explicit per task in `turbo.json` (for example `ci-lint` hashes only `.github/**`,
  the certifier and the lock; `guardrails`, `test-fast` and `test` hash every tracked and
  untracked, unignored file). A failing task is never cached.
- `poe test` measures HEAD in a throwaway worktree, so `cached-test` refuses to run on a dirty
  tree (`poe clean-tree`); commit first. The gate tasks measure the working tree and need no guard.
- The cache lives in `.turbo/` (git-ignored) and is shared by this repository's worktrees.
- Turborepo discovers the uv workspace through `[tool.turbo]` and `[tool.uv.workspace]` in
  `pyproject.toml`; the workspace's one member is `tooling-upgrade/` (stdlib-only, virtual), since
  discovery needs at least one member. Needs Node (for `npx`) and uv on `PATH`.

Run anything else with `uv run <script>` or `uv run python ...`. Tool configuration (ruff,
basedpyright, ty, pytest, coverage, the poe tasks, deptry) lives **only** in `pyproject.toml`: no
`ruff.toml`, `pyrightconfig.json`, `setup.cfg`, `tox.ini`, `pytest.ini` or `.coveragerc`.

### Git hooks

The repo has its **own** hook framework in `scripts/githooks`. Install it once per clone:

```bash
uv run python scripts/githooks/install_git_hooks.py   # sets core.hooksPath -> scripts/githooks
# Windows fallback without uv:  py scripts/githooks/install_git_hooks.py
```

Its pre-commit backstop runs prek over the **staged** files as one stage: a hook finding blocks the
commit (if a fixing hook rewrote a file, review it, stage it and commit again); a missing prek only
warns (`uv sync` installs it). **Never run `prek install`** -- it would fight `core.hooksPath`.

**Never `git commit --no-verify`.** A failing hook is a finding to fix, not a gate to skip. A few hook
messages name `--no-verify` as an emergency bypass: that is for a genuine emergency only, and if you
use it you must say so out loud (in the commit body and to whoever reviews it).

### Blame-ignore setup

Once per clone:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

`.git-blame-ignore-revs` lists the mechanical format/lint commits, so `git blame` skips them and shows
the change that actually wrote each line.

### Suppression policy

Every suppression names its rule **and** a reason:

```python
x = thing()  # noqa: <CODE>  # <reason>
y = other()  # type: ignore[<code>]  # <reason>
z = third()  # pyright: ignore[<rule>]  # <reason>
```

- **Blanket forms are forbidden:** bare `# noqa`, `# ruff: noqa`, `# type: ignore` without a code, and
  `# pyright: basic` or `# pyright: <rule>=false` file headers.
- **Budget:** total suppressions <= 1 per 400 lines of in-scope code.
- `tooling-upgrade/SUPPRESSIONS.md` is generated
  (`uv run python tooling-upgrade/certify.py suppressions --write`) and must match the tree.
- Stale suppressions are caught: ruff `RUF100` (unused noqa) and basedpyright
  `reportUnnecessaryTypeIgnoreComment` are enabled.
- Per-file ignores in `pyproject.toml` are only for structural patterns (for example `S101` in
  tests), each with a comment.

`uv run poe types` enforces all of this.

## The quality gates (must be green)

Every change must pass both before it lands:

```bash
uv run poe gate                  # format, lint, types, lock, deps, every guardrail checker, fast tests
uv run poe test                  # the full suite — all green, no skips you didn't justify
```

The guardrails include `scripts/checkers/check_boundaries.py` (core/ layering) and
`scripts/checkers/check_doc_freshness.py` (only living entry-point docs at the repo root). Windows
fallback without uv: `py -m pytest -q`, `py scripts/checkers/check_boundaries.py`,
`py scripts/checkers/check_doc_freshness.py`.

CI runs these on every push (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## How we build: small, test-gated slices

- **One slice = one coherent change + its test, shipped together.** Don't land capability without the
  test that proves it, and don't land a primitive with no consumer (see "built ≠ wired" below).
- **Tests never touch the canonical Redis (db 0).** Use an injected store, a temp `FileStore`, or
  `REDIS_DB=15`. The suite must be safe to run against a live system.

## Design invariants (the non-negotiables)

1. **One immutable substrate, many projections.** *Atoms* (learnings, beats, events) are append-only and
   sacred — never rewritten or deleted. Everything else (chronicles, the Codex, MEMORY.md) is a
   *regenerable projection*. **Corrections supersede; they don't delete** (`replaces` edge + `valid_to`).
2. **Names must not lie.** Naming follows the ubiquitous language in [`docs/LEXICON.md`](docs/LEXICON.md)
   (DDD + Clean Code). Add the term to the LEXICON before the code. `check_boundaries.py` enforces layering.
3. **Built ≠ wired.** A capability isn't done until it's on a real execution path with a consumer. Prefer
   *wiring an existing primitive* over adding a new unwired one.
4. **One door.** Agent-facing capability goes through `agent_cli.py` verbs; keep CLI and MCP in parity
   (MCP tools are thin `_run()` wrappers over `cmd_*`, so they can't drift).
5. **Fail soft.** Infrastructure (Redis, the bus, embeddings) is optional; degrade to files/heuristics,
   never brick the agent.

## Commits & PRs

- **Explicit pathspecs.** `git add <your files>` then `git commit -- <your files>` — never `git add -A`
  (the tree may be shared by another agent). Commit/push only what you changed.
- **Commit messages** describe the slice and its verification. (Project style: no AI co-author trailers.)
- **Design/plan docs go in `docs/`**, not the repo root (the root holds only README/AGENTS/bootstrap).
- **Record non-obvious learnings**: `uv run agent_cli.py learn <id> --experiment NAME --tried … --result …
  --recommend …` so the next contributor (human or agent) inherits them.
- PRs: describe the slice, show the gates green, and call out any new latent (unwired) capability.

## Good first contributions

- A new deterministic recall signal, a new `Perspective` lens, or a `Distiller`/`Ranker` improvement.
- Docs that clarify the LEXICON or a subsystem.
- Tests that pin a current behavior or close a gap.

Welcome aboard — and remember: *the record must not decay.*
