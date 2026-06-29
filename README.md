# Akashic Aurora

*A self-curating memory and knowledge system for AI agents — local-first, append-only, and built to get better over time instead of decaying.*

---

## The name

- **Akasha** — in Sanskrit, the *aether*: the medium that holds the record of everything. Here it is the
  immutable, append-only **substrate** — the Ledger + Store of every atom the system has ever seen (learnings,
  narrative beats, raw events). The record is sacred; it is never rewritten or deleted.
- **Aurora** — the light that *dawns and dances across that sky*. Here it is the self-organizing **knowledge**
  that emerges over the record: the narrative spine, the Codex, the moment of recall and insight. Order, lit up.

> **Akashic Aurora**: order emerging luminously from the total record. Anti-entropy as a dawn that keeps coming.

## What it is

A single-user, local-first environment that lets autonomous coding agents (Claude, Cursor, OpenCode, a local
LLM) **remember their own work as a navigable story**, **self-curate** what they've learned so it sharpens
rather than sprawls, **recall the right knowledge at the moment of action**, and **coordinate** with one
another — all on one machine, degrading gracefully when infrastructure is down. The core runs on the Python
standard library alone; Redis is an optional accelerator, never a requirement.

Three organizing ideas hold the whole system together:

1. **One immutable substrate, many derived projections.** *Atoms* are append-only and sacred. Everything
   else — tags, chapters, knowledge resources, the agent's own `MEMORY.md` — is a *regenerable projection*
   over atoms, never a precious hand-edited file. The **narrative spine** projects atoms by *time*
   (`Beat → Chapter → Atlas`); the **Codex** projects them by *topic* (`Resource → tree`). Same machinery, two axes.
2. **Governance-as-CRDT.** Derived values are confidence-scored *opinions* over immutable *facts*; the resolver
   is a lattice join (`max by confirmed, confidence, recency`), so repeated or reordered cleanup runs **converge
   and can never degrade data**. Corrections *supersede* (a `replaces` edge + `valid_to`); they never delete.
3. **Trust is enforced, not assumed.** Every distilled claim must resolve to a real source atom (a deterministic,
   no-LLM **faithfulness critic**), and recall surfaces only *active, grounded* knowledge.

---

## The full stack, end to end

Each layer is built strictly on the one below it; an automated boundary checker (`scripts/check_boundaries.py`)
fails CI if a lower layer reaches up. Top to bottom:

```
S5  INTERFACE — the door            agent_cli.py (one CLI) · ai_setup_mcp.py (MCP tools) ·
                                    recall-at-action hooks · Bifrost bus · advisory locks
S4  PROJECTIONS — "Aurora"          Narrative spine (Beat→Chapter→Track→Atlas) · Codex (Resource trees) ·
                                    Perspectives (swappable lenses) · tag-governance CRDT
      ── cross-cutting primitives:  Ranker · Distiller · Consolidator · Faithfulness critic ·
                                    Embedder · Clusterer · Supersession
S1–3 DOMAIN                         LearningStore (learn:) · AgentMemory (mem:) ·
                                    AgentSignalLedger (firehose) · Event log + time-indexed read model · Coordinator
S0  FOUNDATION — "Akasha"           Store ("what IS true, by key") · Ledger ("what HAPPENED, in order") ·
                                    tz-safe time layer · 66-type relationship vocabulary
      ── storage backends:          Redis (fast) · File (always on disk) · Hybrid (both — the default, fail-soft)
```

### S0 — Foundation (the two primitives)

Everything narrows to the classic **store + ledger** pairing. `Store` answers *"what is the value of X?"* (state
by key); `Ledger` answers *"what happened, in order?"* (events appended and replayed by cursor). Each has an
abstract base + three backends (`Redis*` / `File*` / `Hybrid*`) + a `create_*` factory. `Hybrid*` writes
File-always and Redis-best-effort and degrades gracefully — no hang when Redis is down. `Store.cas` /
`update_atomic` give optimistic concurrency; a tz-safe time layer and a validated 66-type relationship
vocabulary round out the floor. *(`core/foundation/`)*

### S1–3 — Domain

- **LearningStore** (`learn:`) — experiment outcomes, deduped by experiment name.
- **AgentMemory** (`mem:`) — episodic experiences, decisions, reflections; supersession-aware.
- **AgentSignalLedger** — the canonical `agent:events` firehose + per-agent streams, with a time-indexed
  read model for "what happened around T" queries (CQRS over the append-only log).
- **Coordinator / SignalEmitter** — agents announce work; decisions are cached for reuse, blockers escalate.

### Cross-cutting primitives (the seam)

Built **once** and shared by every projection, so a capability (ranking, distillation, the trust gate) is wired
in a single place: **Ranker** (transparent weighted relevance/importance/recency, supersession-aware) →
**Distiller** (compact to a token budget, lossy summary + lossless `source` pointer) → **Consolidator** (the one
engine that ranks-then-distills) with a deterministic **Faithfulness critic** injected at the seam. Plus
**Embedder** + **Clusterer** (optional, embedding-based) and **Supersession** (the invalidate-don't-delete rule).

### S4 — Projections ("Aurora")

- **Narrative spine** — raw atoms become a navigable story: `Beat → Chapter → Track → Atlas`, with a
  TrackRouter (which project), a bi-temporal Chapter lifecycle (Zep-style valid-vs-recorded time), a Chronicler
  that distills chapters with faithfulness/coverage metrics, and **theme discovery** (cross-cutting ideas).
- **Codex** — the topic axis: cluster atoms into regenerable **Resources** under MDL-under-faithfulness pressure.
  The Resource lifecycle, clusterer, and faithfulness gate exist; the curator loop that ties them is the next build.
- **Perspectives** — swappable interpretation lenses over the same graph.
- **Tag-governance CRDT** — tags are an append-only history of confidence-scored opinions with a lattice-join
  resolver; cleanup converges and can't lose data.

### S5 — Interface (the door)

- **`agent_cli.py`** — one CLI "door": `boot` / `learn` / `recall` / `recall-at` / `recall-feedback` / `discover`
  / `status` / `story` / `log` / `handoff` / `events` / `promoted` / `bifrost-sync` / `lock` / `discover` lists
  every verb with its purpose (self-describing; a test forbids a silent verb).
- **`ai_setup_mcp.py`** — the same verbs as MCP tools (thin `_run()` wrappers over `cmd_*`, so CLI and MCP can't drift).
- **recall-at-action** — see below.
- **Bifrost bus + advisory locks** — live cross-agent mail (Redis Streams, per-agent cursor, durable salient
  promotion) and transient `lock`/`unlock` coordination for concurrent edits.

---

## The recall-at-action loop (the flagship)

Most memory systems inject context at *turn start*. Akashic Aurora surfaces the right knowledge **at the moment
you act** — a Claude Code `PreToolUse` hook that, when you're about to edit a file or run a command, returns the
few highest-signal **active** lessons + any peer-lock warning, with `source` pointers. The full loop:

1. **Surface** — rank lessons by relevance to the path/command; show nothing unless they clear a relevance floor
   (silence beats a weak hint); cap at ~3; dedup; **FAITH-gate** (no fabricated pointer reaches the agent).
2. **Don't repeat** — per-session anti-repeat: a lesson shown once rotates out, so edits surface *new* knowledge.
3. **Stay fast** — a warm disk cache with stale-fallback (≈1 ms read; no cold-start blank); pre-warmed at SessionStart/boot.
4. **Learn what helped** — `surfaced` impressions + explicit `useful`/`noise` votes + an automatic **contrastive
   signal**: when a target that *just failed* then succeeds, the lessons surfaced for it are credited `helped`
   (a smoothed, capped rate — proven-useful lessons rise, chronically-surfaced-never-useful ones decay).
5. **Reach it anywhere** — works whether Claude is launched from the repo, via the read-bootstrap contract, or a
   scope-guarded user-level hook; fail-open, with an `AKASHIC_RECALL_AT_ACTION=0` kill switch.

---

## What's tested — and what isn't

Built in small, **test-gated slices**: every slice ships with the test that proves it. The suite is **455 tests
green**, run on every push by GitHub Actions (`pytest` + the boundary checker + the doc-freshness guard, against
a Redis service). Honesty about coverage matters more than a green badge, so:

### ✅ Solidly tested (deterministic unit + integration coverage)
- **Foundation** — Store/Ledger across all three backends, `cas`/`update_atomic`, time unification, supersession.
- **Primitives** — Ranker, Distiller, Consolidator, the **Faithfulness critic** (7 characterization tests),
  Embedder + Clusterer (deterministic, with fake embedders).
- **Narrative spine** — schema, beat-log, TrackRouter, Chronicler (+ timezone), theme discovery, tagging,
  the tag-governance CRDT + audit, perspectives, chapter lifecycle, health counters (~100 tests).
- **Events** — log, bridge, time-indexed query, promoter, hooks.
- **Comms & coordination** — Bifrost bus / mesh / presence / parts / pull / promoter / runner, advisory **locks**
  (fencing + TTL), the git-guard, pre-commit, and mirror guardrails.
- **Recall-at-action** — relevance floor, dedup, anti-repeat, warm cache + stale-fallback, the usefulness factor,
  and the contrastive FAIL→SUCCESS credit logic.
- **The door** — CLI/MCP verbs, `discover` self-description, the "no silent verb" guarantee.

### ⚠️ Tested with real caveats (verified narrowly, not end-to-end)
- **The faithfulness critic** is characterized for **zero false-positives on today's extractive output**; it is a
  *forward gate* for an LLM writer that doesn't exist yet, so its discrimination on abstractive text is unproven.
- **Embeddings** (Embedder / Clusterer / theme discovery) pass deterministic unit tests and an *ablation gate*
  when the real model is present — but they're **off by default** (hardware-gated); the always-on path is keyword/deterministic.
- **Concurrency** (locks / git-guard / pre-commit / CAS) is unit-tested per mechanism; a sustained real
  two-process race at scale is **not** continuously exercised.

### ❌ Not yet verified (known, honestly flagged)
- **Live gemini/Chrome web automation** (`scripts/gemini_web.py`) — structurally sound and import-lazy, but the
  live browser behavior (login, AI-mode extraction, invisible mode, Chrome singleton contention) needs a
  logged-in session; not in CI, not unit-tested.
- **The recall PostToolUse implicit signal** — the FAIL→SUCCESS flip is unit-tested, but its success/failure
  *detection* assumes the Claude Code `tool_response` payload shape; it stays **inert (safe), not wrong**, until tuned against a live payload.
- **The Codex curator** (cluster atoms → mint/regenerate/supersede Resources) — its parts are built and tested;
  the loop that ties them is **not built yet**.
- **Recall's real-world value** — the *mechanism* is tested and live; whether surfacing these lessons actually
  improves outcomes needs field data (the usefulness loop is how we'll measure it).
- **Hardening items** — Redis authentication and parts of crash/corruption recovery are designed but not all wired.

---

## Engineering disciplines

- **Test-gated slices + CI.** No capability lands without its test; CI runs the full suite + guardrails on every push.
- **Guardrails that can't be argued with.** `check_boundaries.py` (layer enforcement), `check_doc_freshness.py`
  (only living entry-point docs at the root), a git-guard hook, and a pre-commit backstop.
- **Built ≠ wired.** A primitive isn't "done" until it's on a real execution path with a consumer.
- **Names must not lie.** Naming follows the ubiquitous language in [`docs/LEXICON.md`](docs/LEXICON.md) (DDD +
  Clean Code); the genus names the container, never one species.
- **Any agent, any task.** No permanent per-agent ownership of files or tasks — whoever is online does the work;
  concurrent edits coordinate via transient locks. (Fixed roles only as a deliberate local-LLM choice.)
- **Fail soft, everywhere.** Redis, embeddings, the bus, and the hooks all degrade rather than break the agent.

---

## Get started

```bash
git clone https://github.com/balanced7/akashic-aurora.git && cd akashic-aurora
py -m pip install -r requirements.txt   # optional — the core runs on the stdlib alone
py bootstrap.py --agent-init            # verify: prints the init command + Redis/lesson status
py agent_cli.py boot me --task "trying Akashic Aurora"
```

No third-party packages are required for a first run; Redis is optional (the store falls back to files).
On macOS/Linux use `python3` instead of `py`. Full setup — Redis, the test suite, and the Claude Code
**recall-at-action** hooks — is in **[`docs/DEPLOY.md`](docs/DEPLOY.md)**.

## Where to read next

- [`docs/DEPLOY.md`](docs/DEPLOY.md) — install & run it yourself
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the synthesis (layers, waves, what's done)
- [`docs/architecture.md`](docs/architecture.md) — the foundation (Store + Ledger) in depth
- [`docs/agent-experience-plan.md`](docs/agent-experience-plan.md) — recall-at-action & the agent-experience roadmap
- [`docs/LEXICON.md`](docs/LEXICON.md) — the ubiquitous language
- [`docs/codex-plan.md`](docs/codex-plan.md) + [`docs/codex-inventory.md`](docs/codex-inventory.md) — the self-curation build
- [`docs/tag-governance-plan.md`](docs/tag-governance-plan.md) — the CRDT governance + safety invariants
- [`AGENTS.md`](AGENTS.md) — the agent-facing contract · [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add a slice

## License

[Apache License 2.0](LICENSE) — see also [`NOTICE`](NOTICE). © 2026 balanced7.

*A personal research project. Names must not lie; the record must not decay.*
