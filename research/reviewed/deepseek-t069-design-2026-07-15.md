# DeepSeek T069 Design — Singleton Isolation (2026-07-15)

Status: **DESIGN HALF** (blind — raw problem only, claude's half fenced until mine files)
Author: deepseek (the adversary who must verify the isolation contract holds under drill)
Context: Daniel's dual design for T069 — singleton isolation. The defect reproduces
tonight: test order reverses pass/fail. Four offender factories never adopted the
event_log precedent; a door touch (_orientation_header reading notes+ledger) pins
singletons bound to whatever env is live, poisoning later consumers expecting isolation.

---

## PART (a): THE DEFECT MECHANISM — traced from evidence

### The two test orders

**Order A (FAILS 3):** `[test_t068_wave_a, test_boot_orientation, test_agent_interface]`
1. test_t068_wave_a runs with `_AISETUP_TEST_ISOLATED=1`. At some point it hits a code
   path that calls `get_agent_memory()` → no existing singleton → creates a NEW
   AgentMemory bound to the ISOLATED test store. The singleton `_agent_memory` is pinned.
2. test_boot_orientation calls `_orientation_header("claude")` → internally calls
   `get_agent_memory().get_decisions(days=90)` → the singleton ALREADY exists (pinned
   by step 1) → serves the ISOLATED store's AgentMemory. It expects to read canonical
   notes but gets the test store's (empty or wrong) decisions. The boot header is wrong.
3. test_agent_interface expects canonical behavior → gets the isolated singleton → fails.

**Order B (PASSES 19/19):** `[test_boot_orientation, test_agent_interface, test_t068_wave_a]`
1. test_boot_orientation runs first → no singleton → creates AgentMemory bound to
   the CANONICAL store. Everything works.
2. test_agent_interface → same canonical singleton → works.
3. test_t068_wave_a → sets `_AISETUP_TEST_ISOLATED=1` → BUT the singleton already
   exists from step 1 → isolation is never honored. The test passes anyway because it
   doesn't assert ISOLATION — it only cares that it gets SOME AgentMemory.

**The asymmetry**: Order A fails because the ISOLATED store's singleton doesn't have
canonical data. Order B passes because the CANONICAL store's singleton happens to
satisfy both tests. The isolation contract is silently broken in BOTH orders — but
only A exposes the break as a visible failure.

### The root cause: four factories never adopted the event_log precedent

The event_log precedent (lines 308-330):
```python
def get_event_log(ledger=None):
    if ledger is not None:
        return EventLog(ledger)           # explicit injection → fresh
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return EventLog(create_ledger())  # isolated → fresh every call
    if _INSTANCE is None:
        _INSTANCE = EventLog(...)         # canonical → singleton (lazy)
    return _INSTANCE
```

Three branches:
1. **Explicit injection** (caller passes a store/ledger) → always fresh, never cached
2. **Isolated mode** (`_AISETUP_TEST_ISOLATED` env flag) → fresh instance per call, never cached
3. **Canonical mode** (production) → singleton, lazy-init, cached

The four offenders have only the canonical branch (or a simpler cache):
- `get_agent_memory()` — only branch 3 (singleton, no isolated check)
- `get_learning_store_instance()` — only branch 3
- `get_bus(agent_id)` — branch 3 with agent_id-keyed dict (no namespace awareness, no isolated check)
- `get_reinforced_graph()` — branch 3 + explicit injection (store param → fresh), but NO isolated check

### The coupling vector

`_orientation_header` at agent_cli.py:1025: `get_agent_memory().get_decisions(days=90)`

This is the "door touch" — a function that reads live application state during
test setup. When it's the first caller of `get_agent_memory()` in a test process,
the singleton is born bound to whatever env is live AT THAT MOMENT. If
`_AISETUP_TEST_ISOLATED` is set, the store is isolated. If not, canonical. From
that moment on, EVERY caller gets that same store.

The coupling is: _orientation_header (a boot-rendering utility) reaches into the
knowledge layer (AgentMemory) which reaches into the Store (Redis+files). That
chain bakes the Store instance into a module-level variable that lives for the
process lifetime.

---

## PART (b): SEMANTICS FORK — three approaches ranked

### Approach 1: FRESH-INSTANCE-PER-CALL under isolation (event_log precedent)

**Mechanism**: When `_AISETUP_TEST_ISOLATED` is set, the factory returns a FRESH
instance on every call. Never writes to the module cache. The cache variable is
never populated in isolated mode.

**Precedent**: `get_event_log` (event_log.py:308), `get_event_query` (event_query.py:167),
`get_beat_log` (beat_log.py:150) — all three already do this.

**Safe iff**: The instance is a stateless wrapper over a Store/Ledger. All state
lives in the injected Store; the class itself has no instance fields that callers
depend on preserving across calls.

**Verification per factory**:
- `AgentMemory.__init__(store)` → stores `self.store = store`, nothing else mutable. ✓ stateless wrapper.
- `LearningStore.__init__(store, redis_client)` → stores `self.store = store`, nothing else mutable. ✓ stateless wrapper.
- `Bus.__init__(agent_id)` → stores `self.agent_id`, calls `_redis()` which reads
  `REDIS_HOST/REDIS_PORT/REDIS_DB` at CONSTRUCTION time and stores `self._client`.
  ALSO reads `BIFROST_NAMESPACE` at construction and stores `self.ns`. **NOT**
  stateless — the Redis connection and namespace are baked at init.
- `ReinforcedGraph.__init__(store)` → stores `self.store = store`, nothing else
  mutable. ✓ stateless wrapper.

**Problem with Bus**: Bus is NOT a stateless wrapper. It creates a Redis connection
at construction. Creating a fresh Bus on every call in isolated mode would create
N Redis connections for N `get_bus()` calls — wasteful but not incorrect (the Bus
client is lazy-initialized and connections are cheap). More critically, the Bus
is cached per-agent-id specifically because the connection IS expensive to
recreate — and callers DO depend on the same instance (cursors, reassemblers, etc.
are instance state).

**Verdict**: Approach 1 is correct for AgentMemory, LearningStore, and
ReinforcedGraph (they're stateless wrappers). It's WRONG for Bus (stateful
connection holder).

### Approach 2: CONFIG-KEYED CACHES (fingerprint the relevant env)

**Mechanism**: The cache key includes ALL environment variables the constructor
depends on. A namespace flip produces a different cache key → different instance.
An isolated-mode call produces a key that includes an isolation marker → never
collides with canonical.

**Precedent**: None in the codebase. This is a new pattern.

**For Bus**: Cache key = `(agent_id, BIFROST_NAMESPACE, REDIS_HOST, REDIS_PORT, REDIS_DB, _AISETUP_TEST_ISOLATED)`. Under isolation, every call with a unique agent_id + namespace produces a new instance (but repeated calls with the same agent_id + ns reuse it within the same test — which is fine: tests create one bus per agent_id and reuse it).

**For AgentMemory/LearningStore/ReinforcedGraph**: Cache key = `(store_fingerprint, _AISETUP_TEST_ISOLATED)`. Under isolation, the key includes a unique marker (uuid or counter) → never collides. But this is overkill for stateless wrappers — a fresh instance per call is simpler and already proven.

**Runtime implications**: Growth under drill namespace flips. If a test suite creates 50 buses with 50 unique (agent_id, namespace) pairs, the cache has 50 entries. Each holds a Redis connection. At test teardown, the cache is NOT cleared (module-level dict lives for the process). This is acceptable for pytest (process per worker) but could grow unboundedly in a long-running process that flips namespaces repeatedly.

**Verdict**: Approach 2 is necessary for Bus (stateful, needs connection reuse within same config). It's unnecessary complexity for the three stateless wrappers.

### Approach 3: HYBRID — Approach 1 for stateless wrappers, Approach 2 for Bus

**Mechanism**:
- `get_agent_memory()` — Approach 1 (fresh per call when isolated)
- `get_learning_store_instance()` — Approach 1
- `get_reinforced_graph()` — Approach 1
- `get_bus()` — Approach 2 (config-keyed cache: `(agent_id, namespace)`)

**Rationale**: Stateless wrappers don't benefit from caching under isolation — the
cache only creates the very cross-test contamination we're trying to eliminate.
Bus DOES benefit from caching because connection reuse within a test is correct
and wasted-connection churn is real.

**THIS IS THE RECOMMENDED APPROACH.**

---

## PART (c): CENSUS — ALL module-level caches in core/

### OFFENDER (must fix — binds config at first call, no isolation check)

| Factory | Module | Cache type | Binds | Fix approach |
|---------|--------|-----------|-------|-------------|
| `get_agent_memory()` | `core/learning/agent_memory.py:644` | `_agent_memory: Optional[AgentMemory]` | Store | Approach 1 |
| `get_learning_store_instance()` | `core/learning/learning_store.py:832` | `_learning_store: Optional[LearningStore]` | Store | Approach 1 |
| `get_bus()` | `core/comm/bus.py:926` | `_INSTANCES: Dict[str, Bus]` | namespace, Redis conn | Approach 2 |
| `get_reinforced_graph()` | `core/perspectives/reinforce.py:104` | `_INSTANCE: Optional[ReinforcedGraph]` | Store | Approach 1 |

### ALREADY COMPLIANT (honors _AISETUP_TEST_ISOLATED or explicit injection)

| Factory | Module | Pattern |
|---------|--------|---------|
| `get_event_log()` | `core/events/event_log.py:308` | Fresh per call under isolation ✓ |
| `get_event_query()` | `core/events/event_query.py:167` | Fresh per call under isolation ✓ |
| `get_beat_log()` | `core/narrative/beat_log.py:140` | Fresh per call under isolation ✓ |

### HARMLESS MEMOS (stateless, no config bound at construction, OR explicit-injection-only caching)

| Factory | Module | Why harmless |
|---------|--------|-------------|
| `get_blob_store()` | `core/comm/blobs.py:82` | BlobStore uses AI_SETUP dir (filesystem path), no Redis. Under isolation, AI_SETUP is already temp. Cache within same isolated dir is correct. |
| `get_embedder()` | `core/primitives/embedder.py:165` | Has `store=` injection path; canonical singleton is a lazy stateless wrapper. No isolated check needed because the injection path IS the isolation. |
| `get_clusterer()` | `core/primitives/clusterer.py:221` | Same pattern as embedder |
| `get_consolidator()` | `core/primitives/consolidator.py:64` | Same pattern as embedder |
| `get_tag_auditor()` | `core/narrative/tag_audit.py:89` | Same pattern — store injection path exists |
| `get_tag_governor()` | `core/narrative/tag_governance.py:109` | Same pattern |
| `get_theme_assigner()` | `core/narrative/theme_assigner.py:64` | Same pattern |
| `get_theme_discoverer()` | `core/narrative/theme_discovery.py:168` | Same pattern |
| `get_track_router()` | `core/narrative/track_router.py:167` | Same pattern |
| `_est_cache` | `core/comm/turn_metrics.py:48` | TTL'd estimation cache — keyed by namespace (reads BIFROST_NAMESPACE per-key), expires after 30s. Configuration-independent: a stale entry under a different ns just produces a different key. Not a singleton — it's a time-bounded computation cache. |
| `_pulse_counts` | `core/comm/turn_metrics.py:49` | In-process counter — per-agent dict, turn-scoped. No Store or Redis binding. |
| `expectations._client()` | `core/comm/expectations.py:47` | Calls `get_bus("expect")._client` — transitively fixed when `get_bus` is fixed. No direct cache — it's a convenience accessor. |
| `_bus_conn` on ToolBox | `scripts/deepseek_chat.py:252` | Per-instance field, not module-level. Each ToolBox created gets its own. |

### NOT A CACHE (constructor only, no module-level state)

| Factory | Module | Why |
|---------|--------|-----|
| `Bus.__init__` | `core/comm/bus.py` | Constructor; `get_bus` IS the cache, already listed above |
| `AgentMemory.__init__` | `core/learning/agent_memory.py` | Constructor; `get_agent_memory` IS the cache |
| `LearningStore.__init__` | `core/learning/learning_store.py` | Constructor; `get_learning_store_instance` IS the cache |

---

## PART (d): RUNTIME IMPLICATIONS

### Bus cache growth under namespace flips

The current `get_bus` cache is `Dict[str, Bus]` keyed by agent_id only. The fix
changes it to `Dict[Tuple[str, str], Bus]` keyed by `(agent_id, namespace)`.

**Growth scenario**: A test suite that flips `BIFROST_NAMESPACE` N times while
using the same agent_id creates N Bus instances. Each holds a Redis connection
(lazy, created on first use). The process lifetime of a pytest worker is ~minutes.

**Mitigation**: None needed for pytest — at process exit, connections close. For a
long-running process (the launcher, the UI server), namespace flips are rare
(drill namespaces are test-only). The canonical namespace is "bifrost" and stays
fixed for the process lifetime.

**Eviction**: No eviction policy. The cache is a leaky bucket by design — it
assumes a bounded set of (agent_id, namespace) pairs in a given process. This is
true: agent_ids are drawn from a small fixed set (deepseek, claude, cursor), and
namespaces are either "bifrost" (canonical) or a drill namespace (temporary, one
per test worker). The cache never needs to evict because the key space is bounded.

### Memory/connection overhead

Each Bus instance holds:
- `self._client` (redis.Redis) — one TCP connection, ~4KB memory
- `self._reasm` (Reassembler) — in-memory fragment buffer, ~1KB normally
- Cursor positions (strings, ~100 bytes)

With 3 agents × 3 namespaces (canonical + 2 drill workers) = 9 buses = ~45KB + 9
connections. Trivial.

---

## PART (e): THE BELT — conftest autouse reset

**Question**: Should conftest have an autouse fixture that resets all module
singletons between tests? Defense-in-depth or redundant debt?

**Answer: REDUNDANT DEBT. Do NOT add.**

**Reasoning**:

1. **The fix is at the factory, not the test**. When every factory honors
   `_AISETUP_TEST_ISOLATED` by never caching, there is nothing to reset. The
   module cache variable stays `None` during isolated tests — it's never written.
   A conftest reset would be resetting `None` to `None`.

2. **A reset fixture IS the poison it claims to cure**. A conftest `autouse`
   fixture imports the offender modules at collection time — BEFORE any test runs.
   That import executes the module-level code, which may call `get_bus()` or
   `get_agent_memory()` transitively. The reset fixture ITSELF becomes the first
   door-touch, pinning singletons before the first test even starts.

3. **The event_log precedent proves this is unnecessary**. Three factories already
   honor `_AISETUP_TEST_ISOLATED` with no conftest reset. They've never needed
   one. The fix is to make the four offenders match the precedent — not to add
   a new layer that papers over the gap.

4. **Reset fixtures create ordering fragility of their own**. If test A calls
   `reset_event_log_singleton()` at teardown but test B is mid-execution on a
   different thread, the reset corrupts test B's state. Module-level singletons
   and autouse resets are fundamentally incompatible with parallel test execution.

5. **What IS useful: a diagnostic assertion**. Instead of an autouse reset, add
   a SINGLE test that asserts: "after importing all offender modules, calling
   each factory under isolation returns a fresh instance." This is the census
   test — a canary that fails when a NEW factory is added without the isolated
   check, not a belt that tries to undo already-pinned state.

**Verdict**: No conftest belt. The factory-level fix is sufficient and the
diagnostic census test is the canary. The belt creates more problems than it
solves.

---

## PART (f): PINS (pre-registered RED → GREEN)

| Pin | Description | Test |
|-----|-------------|------|
| P1 | `get_agent_memory()` under `_AISETUP_TEST_ISOLATED` returns a fresh instance every call; never writes module cache | `test_p1_agent_memory_isolated_is_fresh_per_call` |
| P2 | `get_learning_store_instance()` under `_AISETUP_TEST_ISOLATED` returns a fresh instance every call | `test_p2_learning_store_isolated_is_fresh_per_call` |
| P3 | `get_bus(agent_id)` keys on `(agent_id, namespace)`; a namespace flip produces a different Bus instance | `test_p3_get_bus_cache_keys_on_namespace` |
| P4 | `get_bus(agent_id)` under `_AISETUP_TEST_ISOLATED` returns a fresh instance every call; never writes module cache | `test_p4_get_bus_isolated_never_caches` |
| P5 | `_orientation_header` (the door touch) does NOT pin stores for isolated consumers: an isolated `get_agent_memory()` after a door touch returns a fresh instance | `test_p5_door_touch_cannot_pin_stores_for_isolated_consumers` |
| P6 | `get_reinforced_graph()` under `_AISETUP_TEST_ISOLATED` returns a fresh instance every call | `test_p6_reinforce_isolated_is_fresh` |
| P7 | Canonical (non-isolated) path unchanged: singletons still cache as before | `test_p7_canonical_singletons_unchanged` |
| P8 | `get_event_log/get_event_query/get_beat_log` isolated behavior unchanged (non-regression) | `test_p8_existing_isolated_factories_unchanged` |
| P9 | Census test: all core factories that hold Store/Redis-binding state honor `_AISETUP_TEST_ISOLATED` | `test_p9_census_all_factories_honor_isolation` |

---

## PART (g): FILES TOUCHED (estimated)

1. **`core/learning/agent_memory.py:644`** — `get_agent_memory()`: add `_AISETUP_TEST_ISOLATED` check (Approach 1). ~8 lines.

2. **`core/learning/learning_store.py:832`** — `get_learning_store_instance()`: add `_AISETUP_TEST_ISOLATED` check (Approach 1). ~8 lines.

3. **`core/comm/bus.py:926`** — `get_bus()`: change cache key from `str` to `(str, str)` = `(agent_id, namespace)`; add `_AISETUP_TEST_ISOLATED` check returning fresh Bus with no cache write (Approach 2). ~15 lines.

4. **`core/perspectives/reinforce.py:104`** — `get_reinforced_graph()`: add `_AISETUP_TEST_ISOLATED` check (Approach 1). ~8 lines.

5. **`tests/test_t069_singleton_isolation.py`** — 9 pins, already pre-registered with RED tests matching the design. ~120 lines (mostly already written; the test file IS the pre-registered RED).

---

## PART (h): NON-GOALS

- Changing Bus construction to defer namespace resolution (separate arc — the
  stale-ns class Fix A in expectations already reads env per-call; making Bus do
  the same is a larger refactor)
- Adding eviction to the Bus cache (bounded key space makes it unnecessary)
- Adding isolated checks to harmless memos (blobs, embedder, clusterer, etc. —
  their injection path already provides isolation)
- Conftest autouse reset (redundant debt — see Part (e))
- Fixing turn_metrics._est_cache (TTL'd computation cache, not a singleton)
- Changing `_orientation_header` to not call `get_agent_memory()` (the door touch
  is correct behavior; the factory should handle isolation, not the caller)

---

## PART (i): DESIGN RATIONALE

**Why Approach 1 for stateless wrappers, not Approach 2**: A config-keyed cache
for a stateless wrapper is just a memory leak with extra steps. The whole point
of isolation is that each test gets its own store. Caching by config fingerprint
under isolation serves no purpose — each test would have a unique fingerprint
anyway (different temp dir). Fresh-per-call is simpler, shorter code, and matches
the three existing precedents exactly.

**Why Approach 2 for Bus**: Bus has instance state (cursors, reassembler buffers,
pending fragments). Two callers that get different Bus instances for the same
agent_id + namespace would have inconsistent cursors — one advances past a message
the other hasn't seen. Within a single test, ALL callers must get the SAME Bus
instance for a given agent_id + namespace. The config-keyed cache preserves this
invariant while preventing cross-namespace contamination.

**Why `(agent_id, namespace)` not `(agent_id, namespace, redis_host, redis_port, redis_db)`**: The env vars that Bus reads at construction are `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `BIFROST_NAMESPACE`, and `AGENT_ID`. Of these, only `BIFROST_NAMESPACE` and `AGENT_ID` are expected to vary within a single process. `REDIS_HOST/REDIS_PORT/REDIS_DB` are process-wide configuration — they don't change between tests on the same worker. Adding them to the cache key adds complexity without preventing any real collision. If a test worker DOES flip `REDIS_DB`, the Bus connection is to the wrong DB and the cache miss is the least of the problems — the whole isolation contract is broken at the filesystem/environment level. The fix for that is `isolate_canonical.py` (which sets `REDIS_DB=15` once per process), not a more granular cache key.
