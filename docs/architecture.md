# E:\AI-Setup — System Architecture

> Diagram: [architecture.svg](architecture.svg)

The system lets multiple agents work together and keep what they learn, so no
agent redoes work or re-makes a decision another already figured out. It is
organized in four layers; **each layer is built on the one below it.**

```
how agents use it
  SignalEmitter ............ agents announce what they do
  CoordinatorService ....... reacts: caches decisions, builds briefings
        |
        v  (uses)
domain — built on the foundation
  AgentSignalLedger ........ the signal firehose (built on Ledger)
  LearningStore ............ experiment learnings (built on Store)
  StoreReconciler .......... heals Redis vs File drift (operates on Store)
        |
        v  (built on)
foundation · Pillar 0 — two primitives
  Ledger ................... "what HAPPENED, in order"  (append + replay by cursor)
  Store .................... "what IS true, by key"     (state you read back)
        |
        v  (each runs on)
storage backends — shared, dual-write, fail-fast
  Redis (fast)  ·  File (always on disk)  ·  Hybrid (both — the default)
```

## The two primitives (Pillar 0)

Everything narrows to two ideas, named for the question each answers. This is
the classic **store + ledger** pairing from systems engineering.

| Primitive | Answers | Shape | Examples |
|-----------|---------|-------|----------|
| `Store`  | "what IS the value of X?" | state read back by key | decisions, learnings, project state |
| `Ledger` | "what HAPPENED, in order?" | events appended and replayed by cursor | the signals agents emit |

Both share one shape: an abstract base + three backends (`Redis*`, `File*`,
`Hybrid*`) + a `create_*` factory + a fail-fast Redis connect. `Hybrid*` writes
File-always and Redis-best-effort, and degrades gracefully (no 48s hang when
Redis is down). Swapping a backend changes nothing in the layers above.

- `core/foundation/store.py` — `Store` / `RedisStore` / `FileStore` / `HybridStore` / `create_store`
- `core/foundation/ledger.py` — `Ledger` / `RedisLedger` / `FileLedger` / `HybridLedger` / `create_ledger`

## The domain layer (built on the foundation)

- `core/signals/agent_signal_ledger.py` — `AgentSignalLedger`: THE specific
  ledger this system runs on. Owns the signal layout (a canonical `agent:events`
  firehose + per-agent streams + retention). `append_signal()` / `replay_signals()`.
- `core/learning/learning_store.py` — `LearningStore`: experiment-outcome
  learnings, indexed on a `Store`.
- `core/state/sync_reconciler.py` — `StoreReconciler`: detects and heals
  Redis-vs-File divergence on a `HybridStore` (`sync_state_reconciling_divergence()`).

## How it's used

- `SignalEmitter` (in `core/signals/coordinator_api.py`) — the friendly API
  agents call to announce work (`emit_decision...`, `emit_blocker...`). Writes to
  the `AgentSignalLedger`.
- `CoordinatorService` (in `core/signals/coordinator_service.py`) — replays the
  firehose and reacts: caches decisions for reuse (`DecisionCache`), generates
  handoff briefings, escalates blockers, routes `learning` signals to
  `LearningStore`. Reads the `AgentSignalLedger` and the `Store`.

`core/state/redis_sync_coordinator.py` is a deprecated thin facade kept for
back-compat; it delegates to the primitives above.

## Naming principles (so a name tells you the thing's purpose and scope)

1. **State vs. events** — recording a fact you'll look up → `Store`. Announcing
   something that happened → `Ledger`.
2. **Genus, not species** — name a container after the *genus* of what it holds,
   never one *species*. The six signal types (action / decision / blocker /
   handoff / completion / learning) are species; `signal` is the genus → so
   `AgentSignalLedger`, never `decision_log`.
3. **Generic primitive, specific use** — the reusable primitive is generic
   (`Ledger`); its specific use names the variable (`signal_ledger`). We can have
   other ledgers.
4. **"Chronicle" is reserved** for a future *curated* highlights layer
   (`chronicles/`: decisions, failures, milestones) *derived from* the raw
   ledger. Raw ledger → distilled chronicle.
