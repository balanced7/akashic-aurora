# bootstrap.md — system entry point

> **START HERE.** This orients you in ~3 minutes, then points you to the right doc.
> Last updated: 2026-07-02.

> ### 🤖 If you are an AGENT, you don't need this file — use the CLI:
> ```
> py agent_cli.py boot <your_agent_id> --task "<what you are doing>"   # load context
> py agent_cli.py learn <your_agent_id> --experiment NAME --tried "..." --result "..."
> py agent_cli.py list                                                 # see all lessons
> py agent_cli.py recall-at --path <file>                              # relevant lessons/locks BEFORE you edit
> ```
> Hooks (recall-at-action, locks, git-guard, FAIL→SUCCESS credit) are wired for **Claude
> Code** (user-level, absolute paths — they fire for ANY session cwd, including this
> read-bootstrap flow, and stay silent outside the repo) AND for **Cursor** (project
> `.cursor/hooks.json`; your agent id there is `composer`, set automatically at
> sessionStart). What your runtime actually delivers, tier by tier:
> **`py agent_cli.py harnesses`** (story: `docs/integration-tiers.md`). Only run
> `recall-at` by hand if your harness has **no hook wiring at all** (bare CLI follows
> this contract manually).
> The full contract is in **`AGENTS.md`** (read that, not the internals). Use `py`,
> not `python` (the `python` alias may be unset on Windows). Do **not** import the
> internal Python modules directly — `agent_cli.py` is the supported door.
>
> Lost, or arriving from another directory? Get a machine-readable map of exactly
> what to run: **`py bootstrap.py --agent-init`** (emits JSON: init command, the
> working `python_cmd`, Redis status, lesson count).

## What this system is

A team of agents that work together and keep what they learn — so no agent redoes
work or re-decides what another already settled. It's built as a layered stack;
each layer sits on the one below, and agents touch only the top.

```
System 5  Agent Interface (ACI)      how agents DO things          [built: agent_cli.py]
System 4  Context pillar             what agents KNOW (8-10k token re-priming)  [built]
System 1-3 Memory · Signals · Coordination   the domain            [built]
System 0  Store + Ledger             persistence (state / events)  [built]
```

The vocabulary below is exact — see **`docs/LEXICON.md`** for every term.

- **Store** — "what IS true" (state by key). **Ledger** — "what HAPPENED, in order"
  (events). Both have Redis / File / Hybrid backends and degrade gracefully.
- **AgentSignalLedger** — the firehose of signals agents emit.
- **LearningStore** (`learn:`) — experiment outcomes. **AgentMemory** (`mem:`) —
  decisions / experiences / reflections / approaches.

## Where to go next

| You want to… | Read |
|--------------|------|
| See the plan & current wave | **`docs/ROADMAP.md`** ⭐ |
| Know what each term means | **`docs/LEXICON.md`** |
| Understand the architecture | **`docs/architecture.md`** |
| Understand the memory design | `docs/learning-memory-analysis.md` + `-integration-plan.md` |
| Understand the context goal | `docs/context-pillar-plan.md` |
| Understand the agent interface | `docs/agent-interface-aci.md` |
| See what YOUR harness delivers | **`docs/integration-tiers.md`** + `py agent_cli.py harnesses` |
| See the cleanup backlog | `docs/codebase-audit.md` |

## Quick checks

```bash
py bootstrap.py                 # status: foundation, Redis, context, stored data
py scripts/check_boundaries.py  # enforce core/ boundaries (should exit 0)
```

## Initialize an agent

Use the CLI (see the 🤖 callout at the top). Don't import the internals:

```
py agent_cli.py boot <your_agent_id> --task "<what you are doing>"
```

## Status (current — 2026-07-02)

- **All layers built & in use**: Store + Ledger (System 0), Memory · Signals ·
  Coordination (1–3), Context pillar (System 4), Agent Interface `agent_cli.py` (System 5),
  plus the harness adapter layer (`agent/harness/` + `scripts/hooks/` — Claude Code and
  Cursor both wired; `docs/integration-tiers.md`).
- Knowledge store: live on Redis 16379 db0 + file mirror. **Counts rot in prose** — get
  them generated: `py agent_cli.py stats` (lessons + funnel value), `list`, `story`.
- Guardrails (`scripts/check_boundaries.py`, `scripts/check_doc_freshness.py`):
  **enforced, green**; every ship is gated (`scripts/ship.py`). Code public on GitHub
  (`balanced7/akashic-aurora`); knowledge backed up via `scripts/snapshot_knowledge.py`.

> ⚠️ **Truth is generated, not hand-written.** The old root status snapshots
> (`SYSTEM_STATUS.md`, `ACTUAL_INVENTORY.md`, `PHASE_1_CHECKPOINT.md`,
> `CONTINUATION_SESSION_SUMMARY.txt`, …) have been **retired to `docs/_archive/`** —
> they drifted the moment code moved. For current truth use:
> `py agent_cli.py story` (the chronicled narrative), `py agent_cli.py status`,
> `git log`, and `docs/ROADMAP.md`. A guardrail keeps them from creeping back:
> `py scripts/check_doc_freshness.py` (fails on any status snapshot at the repo root).

Redis is optional everywhere — the Hybrid backends fall back to files, so the
system works with Redis down (just slower / no cross-process sharing).
