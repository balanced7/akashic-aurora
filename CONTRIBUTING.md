# Contributing to Akashic Aurora

Thanks for your interest. This is a research project with a strong design spine; the conventions below
are what keep it coherent. They're not bureaucracy — they're the invariants that let the system stay
trustworthy as it grows.

## Setup

See [`docs/DEPLOY.md`](docs/DEPLOY.md). TL;DR: `git clone`, optionally `pip install -r requirements.txt`,
then `py bootstrap.py --agent-init` to verify. (Windows uses `py`; macOS/Linux use `python3`.)

## The quality gates (must be green)

Every change must pass all three before it lands:

```bash
py -m pytest -q                  # the full suite — all green, no skips you didn't justify
py scripts/checkers/check_boundaries.py   # core/ layering guardrail (exit 0)
py scripts/checkers/check_doc_freshness.py# only living entry-point docs at the repo root
```

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
- **Record non-obvious learnings**: `py agent_cli.py learn <id> --experiment NAME --tried … --result …
  --recommend …` so the next contributor (human or agent) inherits them.
- PRs: describe the slice, show the gates green, and call out any new latent (unwired) capability.

## Good first contributions

- A new deterministic recall signal, a new `Perspective` lens, or a `Distiller`/`Ranker` improvement.
- Docs that clarify the LEXICON or a subsystem.
- Tests that pin a current behavior or close a gap.

Welcome aboard — and remember: *the record must not decay.*
