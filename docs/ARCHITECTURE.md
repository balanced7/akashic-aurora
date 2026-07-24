# Akashic Aurora — System Architecture (the living skeleton)

Status: current  (2026-07-09, P4: Living skeleton, actively maintained)

The map of the whole system at **subsystem altitude** — what each part is *for*, and how the
layers stack. Deliberately coarse so it changes rarely; the churny per-module detail lives in the
**auto-generated** [MODULE_INDEX.md](MODULE_INDEX.md) (run `py scripts/generators/gen_arch_index.py`), which
cannot rot. See "How this map stays alive" at the bottom.

> **Derived companion maps** (all auto-generated, all guarded by `check_comprehensibility.py` so
> they cannot silently rot): [MODULE_INDEX.md](MODULE_INDEX.md) — every module's one-line job ·
> [MAP.md](MAP.md) — the master census matrix (module × pin/paper/flags with an honest GAP queue) ·
> [PHYSICS.md](PHYSICS.md) — the machinery's static bounds, caps, timeouts, and config flags ·
> [DOORS.md](DOORS.md) — the agent-door I/O reference (every CLI verb and its inputs).
> Dynamic envelopes (throughput/latency) are measured, not derived — see the master-map charter.

> One sentence: *a message bus lets multiple agents work together, a knowledge stack keeps what they
> learn, a coordination layer stops them colliding, and a supervision layer keeps them alive — all on
> two storage primitives.*

---

## The layer stack (each layer builds only on the ones below it)

```
INTERFACE (System 5) — the doors agents/humans come through
  agent_cli.py · ai_setup_mcp.py · scripts/bifrost_ui.py · bifrost_runner_deepseek.py · bifrost_wake.py
        |
        v
NARRATIVE (System 4)          KNOWLEDGE & MEMORY               COORDINATION
  core/narrative/               core/learning + recall +          core/coord/
  the self-writing story        primitives + renew                who does what, without racing
                                (the "codex")
                                core/library/  atoms as truth,
                                markdown as projection (T101)
                                core/toolbelt/  self-minted verbs,
                                audit, spend (T099)
        |                              |                               |
        +---------------+--------------+---------------+---------------+
                        v
BIFROST — the agent nervous system            TRUST (cross-cutting)     FLEET (cross-cutting)
  core/comm/  bus · control · launcher ·         core/trust/ + security/   core/fleet/
  liveness · promoter · locks                    who MAY do what           who EXISTS
        |
        v
SUBSTRATE — durable records
  core/events/ (raw event firehose)   ·   core/signals/ (agent signal ledger + coordinator)
        |
        v
FOUNDATION · Pillar 0 — two primitives
  Store ("what IS true, by key")   ·   Ledger ("what HAPPENED, in order")
        |
        v
STORAGE BACKENDS — Redis (fast) · File (always) · Hybrid (both, the default; fail-fast)
```

**The dependency rule:** a layer imports only *downward*. This is enforced by
`scripts/checkers/check_boundaries.py` — run it before shipping; a violation means the architecture is drifting.

---

## Foundation · Pillar 0 (`core/foundation/`)
Everything narrows to two primitives, named for the question each answers (classic store+ledger):

| Primitive | Answers | Shape |
|-----------|---------|-------|
| `Store`  | "what IS the value of X?" | state read back by key |
| `Ledger` | "what HAPPENED, in order?" | events appended, replayed by cursor |

Each has an abstract base + three backends (`Redis*` / `File*` / `Hybrid*`) + a `create_*` factory.
`Hybrid*` writes File-always + Redis-best-effort and degrades gracefully (no hang when Redis is down).
Swapping a backend changes nothing above. Also here: `redis_connection.py` (fail-fast connect),
`timeutil.py` (one timezone-safe epoch), `relationship_types.py` (graph edge vocabulary).

## Substrate — durable records
- **`core/events/`** — the raw cross-agent event firehose: `EventLog` (append) → `EventIndex`
  (time index) → `EventQuery` (search/window). "Everything that happened," queryable.
- **`core/signals/`** — the older domain layer: `AgentSignalLedger` (the canonical signal firehose)
  + `SignalEmitter` (agents announce work). Its reactive coordinator was retired 2026-07-07 —
  reaction/coordination now lives in Bifrost (bus + promoter + handoff).

## Bifrost — the agent nervous system (`core/comm/`)
How live agents talk, are steered, and are kept alive.
- **`bus.py`** — the ephemeral message transport (Redis Streams); one inbox + cursor per agent.
- **`bifrost_api.py`** — *the one door* an agent uses to join and work the bus.
- **`control.py` / `nudge.py` / `interject.py` / `dispatcher.py`** — the control plane: global PAUSE +
  runaway guard, targeted barge-in, human-interjection routing, doorbell→wake.
- **`launcher.py`** — spawns + monitors agent processes; the **supervision layer** (revive, backoff,
  opt-in auto-revive, singleton-lock gate).
- **`liveness.py`** — per-agent `worklive` heartbeat (phase + stuck-time) for wedge detection.
- **`runner_lock.py`** — one live runner per agent (singleton, TTL+token). **`promoter.py`** — promote
  salient bus messages into the durable Ledger. **`locks.py`** — advisory path-locks. **`blobs.py` /
  `context_hints.py`** — media payloads / per-agent context forwarding.

## Coordination (`core/coord/`)
Stops agents colliding and plays them to their strengths.
- **`task_ledger.py`** — the deterministic coordination substrate (who owns what task, no model in loop).
- **`conductor.py`** — the orchestration shell over the pure ledger.
- **`negotiation.py` / `intent.py`** — plan-declaration windows. **`cognitive_metrics.py` /
  `experiment.py` / `metrics.py`** — the Stage-3 evidence engine (measure whether coordination helps).

## Knowledge & memory (the "codex")
Give the right agent the right context at the moment of action.
- **`core/learning/`** — `learning_store.py` (experiment lessons), `agent_memory.py` (`mem:` per-agent),
  `consolidation.py` (distill raw memory → chronicle).
- **`core/recall/`** — `at_action.py` (recall AT the moment of a tool call: trigger-aware IDF matching,
  calibrated show-nothing floor, self-echo suppression), `funnel.py` (is surfaced knowledge actually
  helping? the value metric + triage buckets), `curator.py` (triage made an ACTOR: bench/unbench by
  earned track record, ghost pruning — vNext loop 1), `dissent.py` (surface the counter-case).
- **`core/primitives/`** — the reusable engines: `ranker.py` (deterministic relevance×importance×recency),
  `distiller.py` (compact to a token budget + source pointers), `faithfulness.py` (NO-LLM grounding gate —
  silence beats fabrication), `embedder.py`, `clusterer.py`, `consolidator.py`, `supersession.py`
  (newer record retires older).

## Renew (`core/renew/`)
The membrane's temporal (5th) job: keep working context healthy ACROSS sessions
(docs/library/design/20260701_the-mediation-membrane-founding-design-n_4f941f.md §Renew). Deterministic organs only — the health *estimator*
is data-gated on the Strand-A correlation and does not exist yet.
- **`session_signals.py`** — fold one session's tool calls into the signal aggregates
  (churn-over-progress family; reread recorded-but-demoted). Fed by the Claude SessionEnd hook →
  one durable `session_signals` event per session: the passive signal×label correlation dataset.

## Narrative spine (`core/narrative/`) — System 4
The project's self-writing story: **Atlas → Track → Chapter → Beat**. `schema.py` (shapes),
`beat_log.py` (append salient beats), `session.py` (the spine fills itself per session), `chronicler.py`
(beats → chapters), `event_bridge.py`/`event_promoter.py` (join to the raw firehose), `tagging.py`/
`tag_governance.py`/`tag_audit.py` (governed tags), `drift.py`/`health.py` (self-checks).
- **Episodes / bookends** (`episode.py`) — segment a live session into titled EPISODES: a Chapter
  given an explicit `why` (intent), closed manually (a user bookend) or by auto-suggestion, with a
  `{title, description, why}` draft over the closed span. Surfaced via `agent_cli task`'s sibling
  `episode` verb. (Design: `docs/library/design/20260701_session-bookends-design-for-peer-review_c38e0c.md`.)
- **Episode auto-suggester** (`episode_suggester.py`) — ADVISORY close suggestions, poll-evaluated at
  the door: impl-complete / subsystem-switch (routed beats, not the live router key) / new-objective /
  15-min idle, noise-gated + fingerprint-once. Each new suggestion is one durable `episode_suggestion`
  event — the same stream Renew's refresh policy will read (one phase-boundary detector, no double-nudge).

## Cross-cutting
- **Trust/Security** — `core/trust/` (`capabilities.py` roles, `registry.py` reader over
  `security/acl.json` = the source of truth for who-may-do-what). See [security-schema](../MEMORY-links).
- **Fleet** — `core/fleet/` (the roster: who exists). **State** — `core/state/`
  (`session_checkpoint.py` = crash-resume checkpoints; `session_recovery.py` = session-history recovery).
- **Projections (swappable, over the substrate)** — `core/perspectives/` (interpretation lenses over
  the narrative graph — Map × Lens), `core/codex/` (knowledge-compiler / regenerable-projection work).
- **Agent membrane / RENEW** — a *control loop* (not a subpackage) over snapshot + boot + funnel +
  launcher + supersession that keeps an agent's working context healthy **across** the session boundary:
  detect cognitive debt → capture durable knowledge → reload a curated set. Design + status:
  `docs/library/design/20260701_the-mediation-membrane-founding-design-n_4f941f.md`.

## Interface (System 5) — the doors
- **`agent_cli.py`** — THE single CLI door (`boot`, `learn`, `recall`, `note`, `task` (coordination
  ledger), `episode` (session bookends), `bifrost-*`, …).
- **`ai_setup_mcp.py`** — the MCP-transport door. **`bootstrap.py`** — system entry + honest status.
- **`scripts/bifrost_ui.py`** — the realtime web console. **`bifrost_runner_deepseek.py` /
  `bifrost_runner.py`** — make stateless API models first-class bus citizens.
  **`bifrost_wake.py`** — the idle wake listener (an agent can't wake itself; this does).
- **`scripts/mirror.py`** (commit+push) · **`ship.py`** (gated slice-ship) · **`check_boundaries.py`** /
  **`check_doc_freshness.py`** (drift guardrails) · **`snapshot.py`** (session save).

---

## Where to start reading
1. This file (the map). 2. `AGENTS.md` (the contract for agents). 3. `py agent_cli.py boot claude`
(live state). 4. `docs/ROADMAP.md` (the plan). 5. For any subsystem: its module's one-line docstring
(see `MODULE_INDEX.md`) — every module states its single responsibility in line 1.

## How this map stays alive (the anti-rot contract)
A doc survives only if it is **stable-altitude**, **auto-generated**, or **guardrail-enforced**. This
map uses all three:
1. **Stable altitude** — this file describes *subsystems*, which change rarely. Update it only when a
   new `core/` subpackage is born or a layer's *responsibility* changes — not when a file is added.
2. **Auto-generated detail** — `MODULE_INDEX.md` is regenerated from module docstrings by
   `py scripts/generators/gen_arch_index.py`; the per-module truth never goes stale by hand.
3. **Guardrail-enforced** — `check_comprehensibility.py` is the *immune system*: it FAILs when a `core/`
   subpackage is missing from this map, `MODULE_INDEX.md` is stale, a living doc (or a core docstring)
   cites a repo path that's gone (stale reference), or a filename's case drifts. It runs at three
   unbypassable chokepoints — every commit (pre-commit hook, fast checks), every push (CI), and every
   slice (`ship.py`, full) — and a crashing check FAILs loud rather than passing green. `check_boundaries.py`
   catches layer violations; `check_doc_freshness.py` keeps the root clean; `check_wiring.py` catches
   built-but-unwired modules. Design: `docs/library/design/20260701_the-comprehensibility-immune-system-desi_339b01.md`.

**The rule of thumb:** if you add a *file*, do nothing here (the index regenerates). If you add a
*subpackage* or change what a layer is *for*, add/edit one line above.
