# LEXICON — the ubiquitous language of Akashic Aurora

Status: current  (2026-07-09, P4: Living ubiquitous language)

> **Akashic Aurora** is the name of this system. **Akasha** = the immutable, append-only substrate (the
> Ledger of every atom — the record that is never rewritten). **Aurora** = the self-organizing knowledge
> that emerges *over* the record (the narrative spine, the Codex, recall). Order, lit up over the total record.
> (The repo directory is still `E:\AI-Setup`; the MCP server rename is coordinated with Cursor separately.)

One authoritative definition per term. We use these words the same way in
conversation and in code (Domain-Driven Design "ubiquitous language") so there's
no translation layer. When you reach for a name, reach for one of these.

## Naming rules

- **State vs. Events.** Recording a fact you'll look up later → it's *state* (goes
  in a **Store**). Announcing something that happened, in order → it's an *event*
  (goes in a **Ledger**). If you can't tell which, ask "am I storing what *is*, or
  what *happened*?"
- **Genus, not species.** Name a container after the *genus* of what it holds,
  never one *species*. The six signal types (action/decision/blocker/handoff/
  completion/learning) are species; `signal` is the genus → `AgentSignalLedger`,
  never `decision_log`.
- **Generic primitive, specific use.** The reusable primitive stays generic
  (`Ledger`); the specific use names the variable (`signal_ledger`). We can have
  other ledgers.
- **Names must not lie.** A name must match what the thing does. If behavior and
  name disagree, one of them changes (we renamed `Bus`→`Ledger` for this reason;
  we normalized `success: "True"`→`"yes"`).
- **Intention-revealing, precision over brevity.** `append_signal`, not `add`;
  `derive_full_context_for_agent_repriming`, not `get_ctx`.
- **Backward-compat aliases are deprecated, not equal.** A terse old name may alias
  the canonical one, marked "Deprecated: use X".

## Persistence (System 0 — foundation, `core/foundation/`)

- **Store** — persistence of *state by key*: "what IS the value of X?" Mirrors the
  Redis command surface we use (key/value, hash, list, set, sorted-set, TTL,
  ltrim, key-scan). Backends: `RedisStore`, `FileStore`, `HybridStore`; factory
  `create_store`.
- **Ledger** — persistence of *events in sequence*: "what HAPPENED, in order?"
  Append-and-replay by cursor (`emit` / `consume`). NOT a real-time message bus
  (nothing is pushed). Backends: `RedisLedger`, `FileLedger`, `HybridLedger`;
  factory `create_ledger`.
- **Hybrid (Store/Ledger)** — the default backend: writes File-always +
  Redis-best-effort, reads Redis-first with File fallback. Degrades gracefully
  (no 48s hang) and never loses durability.
- **fail-fast connector** — `connect_to_redis_with_fail_fast`: the ONLY sanctioned
  way to reach Redis. Probes reachability first so a down Redis fails in ~seconds,
  not ~48s. (Enforced by `scripts/check_boundaries.py`.)
- **Redis↔File reconcile** — `HybridStore.check_drift()` / `reconcile()` heal divergence by
  backfilling Redis from the durable File (the source of truth) after Redis was down. Wired into
  cold-start boot (`agent_cli cmd_boot`). (The old `StoreReconciler` wrapper was retired 2026-07-07.)

## Domain (Systems 1–3, `core/`)

- **AgentSignalLedger** — THE specific ledger this system runs on: every signal an
  agent emits, recorded in order. Owns the signal layout (canonical `agent:events`
  firehose + per-agent streams + retention). `append_signal` / `replay_signals`.
- **signal** — the genus for what agents emit. Species: `action`, `decision`,
  `blocker`, `handoff`, `completion`, `learning` (+ `insight`, `context`).
- **SignalEmitter** — the agent-facing API for emitting signals
  (`emit_decision_referenced_by_agents`, etc.). Single source of truth for
  `SignalType`.
- **LearningStore** — experiment-outcome learnings (the `learn:` namespace).
  Success vocabulary is canonical `{yes, partial, no}`; keyed by `experiment_name`.
- **AgentMemory** — the richer multi-type memory (the `mem:` namespace): decisions
  (semantic), experiences (episodic), reflections (Reflexion), approaches
  (procedural). Persists through a Store. Distinct from `LearningStore`.

## Bifrost — live agents, control & supervision (`core/comm/`, `core/coord/`)

The runtime nervous system for agents that are actually *running*. (This layer has grown the most
since the June foundation docs; keep it current.)

- **Bifrost** — the whole live-agent comms + control + supervision layer (`core/comm/`).
- **Bus** — the ephemeral real-time message transport (Redis Streams); one **inbox** + read **cursor**
  per agent. Distinct from the Ledger: the bus is disposable and pushed, the Ledger is durable and
  pulled. `core/comm/bus.py`. The one door onto it: **bifrost.api** (`core/comm/bifrost_api.py`).
- **Runner** — the process that makes a stateless API model (DeepSeek/Gemini) a first-class bus
  citizen (wake → answer → post). `scripts/bifrost_runner_*.py`.
- **Runner-lock / singleton** — one live runner per agent id (TTL + per-instance token); a second
  refuses to start. `core/comm/runner_lock.py`.
- **Presence** — the "online" heartbeat per agent. **Worklive** — the richer *"what phase am I in,
  and since when?"* heartbeat used to detect wedges. `core/comm/liveness.py`.
- **Wedge** — an agent that is *alive but STUCK* (a hung call, a frozen phase) — distinct from a
  **crash** (process exit). **Revive** — kill a wedged/dead runner, free its lock, relaunch it.
  `launcher.revive()`.
- **Launcher / supervisor** — spawns + monitors agent processes; owns revive, restart backoff+cap,
  and opt-in **auto-revive** (armed per agent, default off — observe-only by default). `core/comm/launcher.py`.
- **Control plane** — human-in-the-loop steering: **Pause/Halt** (freeze), **Nudge** (targeted
  barge-in), **Steer** (fold a fact into live work, no restart), **Interject** (route a typed human
  message). `core/comm/control.py`, `nudge.py`, `interject.py`.
- **Wake / doorbell** — an idle agent can't wake *itself*; a wake listener blocks on the bus and the
  harness re-invokes the agent when mail lands. `scripts/bifrost_wake.py`, `core/comm/dispatcher.py`.
- **Promoter / promoted** — salient bus messages (handoff/decision/completion/blocker) copied into
  the durable Ledger so they survive Redis restarts. `core/comm/promoter.py`.

### Coordination (`core/coord/`)
- **Task ledger** — the deterministic who-owns-which-task substrate (no model in the loop). `core/coord/task_ledger.py`.
- **Conductor** — the impure orchestration shell over the pure task ledger. `core/coord/conductor.py`.
- **Negotiation round** — a brief window after human input where agents declare plans before acting. `core/coord/negotiation.py`.
- **Barrier** — a stop-and-synchronize checkpoint so agents converge instead of racing. *(planned — Wave 3.)*
- **Hat** — an opt-in role layer scoping an agent's context AND permissions (a "reviewer" vs "builder"
  lens). Note: a hat is where *role-based context* lives — not per-lesson tags. *(planned — Wave 3.)*

## Context & interface (Systems 4–5)

- **Context pillar (System 4)** — assembles 8–10k tokens of ranked, relevant
  context so an agent starts informed ("what the agent KNOWS"). Built in `context/`
  (`aggregator.py` + per-source loaders + `arch_loader.py`, the boot code-orientation slice).
- **Agent Interface / ACI (System 5)** — the small, coherent verb surface agents
  use to act ("what the agent DOES"). Tool descriptions are prompts; errors teach.

## Cross-cutting concepts

- **charter** — RESERVED for an agent's *standing contract* (`charters/<agent>/CHARTER.md`):
  identity, responsibilities, current stretch. NOT a work order. (Ruling 2026-07-21: the word had
  four live meanings; this ends it. Old filenames keep their names as fossils — the WORD is fixed
  going forward.)
- **brief** — a *work order to a seat* (`research/briefs/`): mission, constraints, deliverable,
  write scope. What "charter" colloquially meant in run-orders before the ruling above.
- **chronicle** — RESERVED for the *curated highlights* layer (`chronicles/`:
  decisions, failures, milestones) *derived from* the raw ledger. Do NOT name the
  raw event log "chronicle". Raw ledger → distilled chronicle.
- **Ranker** (`core/primitives/ranker.py`) — deterministic scoring of items by relevance ×
  importance × recency, plus relationship-type weighting. Used across recall and context.
- **Distiller** (`core/primitives/distiller.py`) — compact many items to a token budget, keeping a
  lossless `source` pointer per line; optional writer→critic seam. Gated by the **Faithfulness**
  critic (`core/primitives/faithfulness.py`) — a NO-LLM grounding check; silence beats fabrication.
- **relationship type** — one of 66 standardized relations (Dublin Core / OBO /
  RDF) in `core/foundation/relationship_types.py`; the vocabulary semantic method
  names are built from. Real short-names include `part_of`, `causes`, `prevents`,
  `precedes`, `influences`, `is_version_of`, `replaces`, `member_of`, `instance_of`,
  `related_to` (NOT `derived_from`/`supersedes`/`led_to` — those are not in the set;
  validate with `get_relationship_by_name`). Inverses are bidirectional + unique-short-named,
  guarded by `tests/test_relationship_types.py`.
- **Agent membrane / RENEW** — the control loop that keeps working context healthy **across** sessions:
  detect cognitive debt → *Capture* durable knowledge → *Surface* a curated reload (the MemGPT-style
  **paging function**). A loop over snapshot + boot + funnel + launcher + supersession — NOT a new
  subsystem. Design + status: `docs/library/design/20260701_the-mediation-membrane-founding-design-n_4f941f.md`.
- **session_checkpoint / session_snapshot / session_recovery** (three "session state" things — do NOT
  confuse; the shared name was a real bug): `core/state/session_checkpoint.py` = crash-resume
  CHECKPOINTS (+ `CheckpointRecovery` = derive a resume-plan from one); `core/comm/session_state.py` =
  live-Bifrost-session SNAPSHOT (save the fleet to resume later); `core/state/session_recovery.py` =
  SESSION-HISTORY recovery from local files (its `SessionRecovery` is a *different* class than
  `CheckpointRecovery`).

## Narrative spine (System 4 — `core/narrative/`, see docs/library/design/20260709_narrative-spine-design-plan-system-4-cap_2357df.md)

- **Beat** — one salient, time-anchored narrative event; points to its raw atom
  (a learning / commit / ledger event) via a followable `source`.
- **Chapter** — a bounded coherent stretch of Beats within one Track (the mid view).
- **Episode / Bookend** — an **Episode** IS a Chapter given an explicit `why` (intent), segmenting a
  *session* into confined titled spans. A **Bookend** is the boundary that closes one episode + opens
  the next — manual (a user button) or auto (a suggestion from the same signals that trigger RENEW);
  the close drafts `{title, description, why}` over the span. `core/narrative/episode.py`, `agent_cli episode`.
- **Track** — a long-running per-domain/project thread (`ai-setup`, `stemroller`,
  `vision`, `research`, …); has its own Chapters + arc.
- **Theme** — a cross-cutting idea-group weaving across Tracks (orthogonal to Tracks).
- **Atlas** — the broad view across all Tracks over time.
- **Storyline** — one Track's rolled-up arc of Chapter summaries.
- **Chronicler** — the process that distills the Ledger into Chapters/Storyline
  (generalizes `consolidation.py`); implemented in `core/narrative/chronicler.py`;
  writes `chronicles/story.md` + `chronicles/story.index.json`.
- **TrackRouter** — infers a Beat's Track from context + detects domain switches.
- **narrative weight** — salience (0–5) stamped on a Beat at log time.
- Three axes: **Time** (when) × **Track** (which domain) × **Theme** (which idea);
  edges are relationship-types. Beat `source` obeys the lossy-summary + lossless-pointer
  rule.

## Perspectives layer (System 4 — `core/perspectives/`, see docs/library/design/20260709_perspectives-maps-build-plan-the-interpr_5a5e0a.md)

The interpretation layer over the narrative graph. **Substrate stays sacred; this is swappable.**

- **Map** — a *structural* projection: which relationship-type *domains* (causal / temporal /
  structural / …) form the graph you traverse. Selects a sub-graph of the substrate.
- **Lens** (Perspective) — a *value-set*: factor weights (relevance/importance/recency/
  strength) + per-relation weights + an optional focus seed. Parameterizes the Ranker.
- **ReinforcedGraph** — an association graph whose edges **strengthen with co-use**
  (bounded Hebbian) and **decay without it** (half-life). Turns the static typed graph into
  a living, experience-shaped map. Read-only on the substrate; bounded reinforcement is the
  only write-back (lens-law safe). Decay is the anti-ossification guard.
- A **view** = `Map × Lens` applied to the substrate (read-only). Swap either → a different
  surfaced map from the same data.

## Layers (who may depend on whom)

`System 0 (foundation)` ← `1–3 (domain)` ← `4 (context)` ← `5 (interface)`.
Lower layers never import higher ones. Agents touch only the top (System 5);
`Store`/`Ledger`/`AgentMemory` internals are never agent-facing tools.

## Knowledge layers (one source of truth, three views)

Harmonized 2026-06-20 (see `docs/library/design/20260709_knowledge-store-harmonization-plan-2026_9e9656.md`):

1. **Raw / archival** — `session_logs/learnings.jsonl` + Ledger streams. The deepest,
   richest record. Append-only; never mutated or deleted.
2. **Canonical state** — the `Store` (`learn:*` / `mem:*` / `proj:*`), mirrored across
   Redis (16379 db 0) and `session_logs/store_state.json`. Each record holds a lossy
   summary **plus** a `source` pointer (and `detail_json`) back to the raw line.
3. **Derived / curated** — `chronicles/`: generated `lessons.md` (Distiller output,
   regenerated, never hand-edited) and legacy curated `*.json` (milestones/failures/adrs).

Rule: raw is sacred; the Store summarizes-with-pointer; chronicles are regenerated from
the Store. Never hand-edit a derived view as if it were a source.

## Coordination patterns (two-agent concurrency — see `docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md`)

Names for what the system already does, so we can reason about it precisely:

- **Blackboard** — agents coordinate *indirectly* by reading/writing a shared knowledge
  space rather than messaging each other directly. Our **Akasha Ledger** is the blackboard.
- **Stigmergy** — coordination via traces left in a shared environment (the ledger/git
  state) that trigger the next agent's action; no direct talk required. What two agents
  writing one ledger are doing.
- **Advisory lock** — a lock honored only by cooperating writers (not OS-enforced). Correct
  here because we own both agents. `core/comm/locks.py`; `py agent_cli.py lock`.
- **Fencing token** — a monotonic number issued per lock acquisition; a stale/paused holder
  is detected by a too-old token at the commit gate. The one must-have lock-safety property.
- **Optimistic CAS** — compare-and-set: write only if the value is unchanged since you read
  it; a conflicting write is rejected (lost-update guard), not silently applied. `Store.cas` /
  `Store.update_atomic` → `CASConflict`.
- **Three planes** — *coordination* (shared substrate) · *workspace* (isolated per agent via
  git worktrees) · *singleton OS resources* (serialized: route/lock, never duplicated).

## Redis topology & test isolation

- **Canonical endpoint** = `config.REDIS_PORT` (16379, the Docker master). The 6379/6380
  WSL pair is a separate, inactive HA-server concern (`services/redis_ha_manager.py`).
- **Tests NEVER touch canonical.** They run on `config.REDIS_TEST_DB` (15) + a temp
  `AI_SETUP` file dir. Use `tests/isolate_canonical.py` (import first) for default-store
  tests, or `tests/redis_test_helpers.py` for explicit live-Redis stores/ledgers.
  Invariant: a full test run must leave canonical db 0 unchanged.
