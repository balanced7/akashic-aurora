# Repository split plan — one repo per lifecycle, not per topic

Status: PLAN (not executed). Authored by Heimdall (deepseek), 2026-10-29, in conversation
with the operator. The goal: stop detangling commits that share a repo while changing at
opposite cadences and opposite risk profiles.

## The principle

**Split by how often a thing churns and who is allowed to break it — never by what it is
about.** A repo boundary that maps 1:1 onto a lifecycle never needs detangling, because
nothing with a different cadence ever lives inside it in the first place.

Measured today (git ls-files, top-level dirs by file count):

    1033  docs/library          knowledge corpus (atoms/design/reports) — append-mostly
     877  research/in-flight    half-done research + WIP artifacts
     435  arsenal/web           creative code (piano/vfx/stage/shaderlab)
     313  research/reviewed     archived research
     273  docs/_archive         already-archived docs
      74  core/comm             THE SUBSTRATE — only 74 files

The substrate is tiny. The weight is four force-mixed lifecycles around it. Each churns at a
different rate and should never share a commit stream with the others.

## The four lanes

| Lane | What moves | Lifecycle |
|---|---|---|
| **substrate** (stays `akashic-aurora`) | `core/`, `scripts/checkers/`, `scripts/ops/`, `agent_cli.py`, `ai_setup_mcp.py`, real `tests/`, `AGENTS.md`, `docs/ARCHITECTURE.md` + guarded maps | gated, pre-registered pins, `check_fresh_clone --clone` before ship |
| **knowledge** | `docs/library/`, `chronicles/`, `research/reviewed/`, `docs/_archive/` | append + supersede, write-once, content-addressed, never force-pushed |
| **creative (arsenal)** | everything under `arsenal/` — keylab, piano, vfx, shaderlab, stage, rgb, web | worktrees, WIP commits, ship-when-it-looks-good, binary-heavy |
| **research** | `research/in-flight/` | branch-per-idea, merge-to-archive, discard freely |

## The cross-cutting layers (links, not forks)

- **`docs/library/design/` + `docs/library/report/`** — the knowledge atoms (T101 markdown-as-
  projection). Tempting to split, but they are joined to `recall`/`learning` by PATH
  CITATION. Keep as a linked content-repo (submodule or sibling checkout), not a hard fork.
- **`state/`, `session_logs/`, `store/`** — runtime instance state. NOT a project. The fix is
  hard `.gitignore`, not a repo. A deployment's private brain is not source.

## The hard part — recalling citations survive the split

The lesson corpus references `arsenal/keylab/*` and `arsenal/web/*` and `docs/library/*`
constantly (`learn:` lessons cite those paths as `source`/`files_affected`/prose). A hard
split that MOVES files breaks every one of those citations, because the corpus stores the
path as a string. So the split must:

  1. Not RENAME anything — move whole directories, keep relative paths intact *within* each
     repo. A lesson citing `arsenal/keylab/README.md` stays valid as long as
     `arsenal/keylab/README.md` exists *somewhere* the recall reader can resolve.
  2. Keep a single *citation resolver* that maps a repo-relative citation to its home repo
     (so `arsenal/keylab/*` resolves into `aurora-arsenal`, not `akashic-aurora`), OR
  3. Accept that creative/knowledge citations become "content-addressed elsewhere" and the
     recall door gains a cross-repo lookup. This is the one piece of new machinery the split
     genuinely requires — do NOT split without deciding it, because it is the thing that
     would otherwise make the split a data-loss event for the corpus.

## The cost-of-waiting argument (why do this at all)

Right now one repo has four cadences. Two failure modes, both already visible:

  - The creative loop gets strangled by the substrate's gate discipline (or blinds itself
    with `--no-verify`, which is worse).
  - The substrate's gate discipline gets lowered to accommodate creative churn, and the
    guardrail baseline grows ambient-debt notes (the `_check_kind_policy_2` /
    `_check_unbound_names_1` class) forever.

Splitting means the guardrail only ever fires on the repo where its debt lives.

## Execution order (cheapest uncoupling first)

  1. **research** — it's already a graveyard + scratch; move `research/` to its own repo,
     nothing cross-cites it except the eye archive (which records file locations, not code).
  2. **creative** — `arsenal/` to `aurora-arsenal`; this is the "start a new repo for VFX"
     the operator already flagged.
  3. **knowledge** — `docs/library/` + `chronicles/` to a content repo, with the citation
     resolver from above.
  4. What's left IS the substrate.

Each step lands as its own commit in its own repo, so a failed step never strands the other
three.

## What NOT to do

  - Do not split `core/comm` vs `core/learning` — they are one substrate, tightly coupled,
    and splitting them buys nothing (different cadence is NOT present inside `core/`).
  - Do not make `.claude/`, `.codex/`, `.cursor/` their own repo — they are per-seat editor
    config, not code; they belong wherever the checkout lives (or in a dotfiles repo if
    config ever needs versioning).
  - Do not split by "topic size" (e.g. "piano is big so it gets a repo"). Cadence, not size.
