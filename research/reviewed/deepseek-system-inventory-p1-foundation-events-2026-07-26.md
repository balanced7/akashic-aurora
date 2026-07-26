# System Inventory + Prior-Art Register — Part 1: Foundation & Events
## DeepSeek, 2026-07-26 — overnight program

---

## core/foundation (8 modules)

### 1. Store (store.py, sqlite_store.py)

**WHAT IT DOES:** Abstract persistence interface mirroring Redis's command surface (kv, hash, list, set, zset, TTL, CAS, keyspace scan). Three backends: RedisStore (thin pass-through to Redis), SqliteStore (SQLite with WAL, landed tonight), HybridStore (dual-write, read Redis-first, file heals). The factory `create_store()` is the universal constructor — zero production code imports a specific backend.

**CONNECTED TO:**
- Reads from: nothing (it IS the persistence layer)
- Written to by: every domain module via `create_store()` — `learning_store.py`, `agent_memory.py`, `beat_log.py`, `chronicler.py`, `event_index.py`, `event_log.py`, `tag_audit.py`, `tag_governance.py`, `funnel.py`, `knowledge_map.py`, `curator.py`, `lookback.py`, `mailbox.py`, `toolbox.py`, `agent_cli.py` (every CLI verb), hook scripts (pretooluse, posttooluse, sessionstart, sessionend, userpromptsubmit)
- Migrated by: `core/foundation/migrate_to_sqlite.py` (one-way JSON→SQLite, run tonight, 17→455 lessons healed)

**COMPARABLE SYSTEMS:**
1. **Redis itself** — in-memory data structures server. We emulate its API surface. Redis is our L1 cache tier; SQLite is now L2 durable tier.
2. **SQLite** — embedded SQL database. We just adopted it. WAL mode, zero-config, stdlib, single-file. The comparison is now internal: how much of our custom Redis-emulation should yield to native SQL queries?
3. **LMDB** — memory-mapped ordered KV store. Would replace Redis-emulation with native ordered access. Research round tonight found it's the wrong abstraction for our 28-method Redis-shaped interface (zset encoding alone is a design project).
4. **DuckDB** — embedded analytical SQL. Overkill for OLTP workloads. Beautiful for analytics; absurd for per-tool-call `hset` of one lesson field.
5. **Bitemporal SQL tables** — SQL:2011 temporal features (valid-time, transaction-time). Two timestamp columns, one WHERE clause. Tonight's deep dive: this rides SqliteStore for ~50 lines.

**THE DELTA:**
- Redis: native data structures, network-accessible, TTL eviction. We emulate these in SQLite with tables. Missing: Redis's pub/sub (we use bus streams instead), Redis's LRU eviction (we have manual `_evict_if_expired`).
- SQLite: native SQL queries, JOINs, indexes, transactions. Our Redis-emulation layer hides all of this behind hset/hget/lrange. We can't query "all lessons by agent_id" without loading every hash.
- Bitemporal: validity intervals, as-of queries. We have no temporal query capability — `timestamp` gets overwritten on edit.

**THE IMPORT:** **Let the cache be the cache, let the store be SQL.** The `_cached_items()` pattern (one JSON file with ALL lessons) is the scaling cliff at 50K+ lessons. Replace it with a SQL query against the SqliteStore that filters by recency/importance and LIMITs — the cache becomes a materialized view, not a full dump. The SqliteStore just landed; this is the natural next step.

**THE ANTI-IMPORT:** **Datomic-style fact tuples.** Decomposing lessons into [entity, attribute, value, txn] tuples would be a complete rewrite for speculative benefit. Our hashes map cleanly to SQL rows; the fact model adds GROUP-BY complexity for no current use case. Revisit only when as-of queries on individual fields (not whole records) become load-bearing.

**STATUS:** `sqlite_store.py` is LIVE (landed tonight, re-healed 455 lessons). `store.py` has the ABC + RedisStore + HybridStore. `migrate_to_sqlite.py` is one-shot, already run. `FileStore` is now legacy — it caused the 65.6% silent data loss at 3 processes. Per tonight's research: it should be retired once SqliteStore proves stable.

---

### 2. Ledger (ledger.py)

**WHAT IT DOES:** Append-only event log over Redis Streams, with FileStore fallback. Events are `{kind, at, detail, refs, agent_id}`. Used for the durable "what happened" record — distinct from the bus (ephemeral transport) and the store (current state). Bounded streams (maxlen), consumer groups for at-least-once delivery.

**CONNECTED TO:**
- Reads from: Redis Streams (primary) or FileStore (fallback)
- Written to by: `event_log.py` (canonical event capture), `promoter.py` (bus→ledger promotion), `flow_trace.py`, hook scripts
- Queried by: `event_query.py` (time-window queries), `event_index.py` (Store-backed materialized index for fast time-range scans)

**COMPARABLE SYSTEMS:**
1. **Kafka** — distributed append-only log with partitions, log compaction, consumer groups. Our ledger is single-node; Kafka's partition model would enable parallel consumers. Kafka's log compaction (keep latest per key) would solve our "every lesson edit overwrites timestamp" problem at the log level.
2. **EventStoreDB** — purpose-built event store with stream-per-aggregate, projections, $all stream. Our ledger is stream-per-kind (one Redis stream); EventStore's stream-per-aggregate model maps better to "one stream per lesson."
3. **Kinesis** — AWS managed log. Same shape as Kafka but managed. Overkill for single-node.
4. **Certificate Transparency** — append-only Merkle tree log. Every entry is cryptographically linked to its predecessor; tampering is detectable. Our ledger has no cryptographic integrity — events are JSON in Redis, trivially editable.

**THE DELTA:**
- Kafka: partitioning (parallel consumers), log compaction (key-level retention), exactly-once semantics (idempotent producers). Our ledger has none of these — it's single-consumer, no compaction, at-least-once via consumer groups.
- EventStoreDB: stream-per-aggregate. Our events are timestamp-ordered in one stream; finding "all events for lesson X" requires scanning. EventStore's projection model would let us project lesson state from events.
- Certificate Transparency: Merkle tree integrity. Our ledger has zero tamper detection. An operator with Redis access can delete or modify any event.

**THE IMPORT:** **Log compaction for lessons.** Kafka's log compaction keeps only the latest value per key. A compacted lesson stream would mean: every `learn` or `graduate` or `bench` event lands on the `learn:experiment:NAME` stream, and compaction keeps only the latest state. This is bitemporal-lite without schema changes — the event IS the version history, and the current state is the compacted view.

**THE ANTI-IMPORT:** **Exactly-once semantics.** Kafka's idempotent producer + transactional reads is complex distributed coordination for a guarantee we don't need. Our at-least-once + idempotent consumers (RB-26) is simpler and sufficient at our scale. Don't add distributed transactions for a single-node system.

**STATUS:** LIVE. Redis Streams primary, FileStore fallback. `event_index.py` provides time-range queries over the Store. No cryptographic integrity, no log compaction, no stream-per-aggregate.

---

### 3. Redis Connection (redis_connection.py)

**WHAT IT DOES:** Fail-fast Redis connector with retry, timeout, and the canonical host/port/db config. The single source of truth for "how to reach Redis." Every RedisStore is built through this connector.

**CONNECTED TO:**
- Reads from: environment (REDIS_HOST, REDIS_PORT, REDIS_DB), config defaults
- Written to by: nothing (it's a factory)
- Used by: `RedisStore`, `HybridStore`, and anything that needs a raw Redis client

**COMPARABLE SYSTEMS:**
1. **Redis Sentinel** — high-availability with automatic failover. We hardcode one host:port; Sentinel would give us failover to replicas.
2. **Envoy / proxy-sidecar** — connection pooling, circuit breaking, retry budgets. Our connector has simple retry; a sidecar would offload resilience.
3. **Connection pool libraries (HikariCP, r2d2)** — production-grade pooling with health checks. Our connector creates a new client per call; no pooling.

**THE DELTA:**
- Sentinel: automatic primary election. If our Redis goes down, we fall back to SQLite — no automatic Redis recovery. Sentinel would reconnect transparently.
- Connection pooling: reuse, health checks, max connections. Our one-client-per-call pattern is fine at low volume but wastes connections under load.

**THE IMPORT:** **Connection pooling with health checks.** The `redis` Python library supports connection pools natively. Switching from `redis.Redis(...)` to a pool-backed client is a one-line change. This would reduce connection churn on every tool call (hooks fire PreToolUse → recall → store read → new connection each time).

**THE ANTI-IMPORT:** **Redis Cluster.** Sharding across multiple nodes adds operational complexity (resharding, slot migration, multi-key operations) for a scale we don't need. Single Redis + SQLite fallback is simpler and sufficient.

**STATUS:** LIVE and stable. `DEFAULT_REDIS_HOST`, `DEFAULT_REDIS_PORT` (16379), `DEFAULT_REDIS_DB` (0). Timeout: 2.0s. No pooling, no Sentinel, no Cluster.

---

### 4. Time Utilities (timeutil.py)

**WHAT IT DOES:** `to_epoch()` — deterministic timestamp→epoch conversion that treats naive datetimes as UTC. Fixes the locale-dependent `.timestamp()` bug where Windows (UTC-5) and Linux (UTC) produced different epochs from the same ISO string.

**CONNECTED TO:**
- Used by: `chronicler.py`, `beat_log.py`, `event_index.py`, `curator.py`, `tag_governance.py`, `at_action.py` — anywhere timestamps are compared

**COMPARABLE SYSTEMS:** N/A — this is a bugfix, not a novel system. The comparable is "any library that handles timezones correctly": Arrow, Pendulum, Python 3.11's `datetime.UTC`.

**STATUS:** LIVE. Landed as part of the D4 timezone fix.

---

### 5. Relationship Types (relationship_types.py)

**WHAT IT DOES:** Typed relationship vocabulary for the knowledge graph — 50+ relationship types with forward/backward labels, domains, and constraints. Used by the atom family's `citations_out` edges.

**CONNECTED TO:**
- Used by: `atoms.py` (citation edges), `knowledge_map.py` (graph traversal), `projection.py` (rendering)
- Defines: `discusses`, `supersedes`, `superseded_by`, `derives_from`, `contradicts`, `supports`, `refutes`, etc.

**COMPARABLE SYSTEMS:**
1. **Wikidata properties** — P-numbers for every relationship. Our 50 types are a tiny subset of Wikidata's ~10K properties. Wikidata's property constraints (domain, range, cardinality) are richer.
2. **Schema.org** — web-scale relationship vocabulary. Our types are project-specific; schema.org is universal.
3. **Datomic schema** — typed attributes with cardinality and uniqueness. Our relationships are strings; Datomic's are typed refs with guarantees.

**THE DELTA:**
- Wikidata: 10K properties, constraints, qualifiers. We have 50 types, no property-level constraints.
- Datomic: ref types with `:db/cardinality` and `:db/unique`. Our edges carry `rel` and `target` strings with no schema enforcement.

**THE IMPORT:** **Wikidata-style qualifiers on citations.** A citation edge today is `{target, rel}`. Adding `{since, until, confidence, evidence}` qualifiers would make edges bitemporal and provenance-tagged — a lesson citing an atom could say "cites as-of version 3, with high confidence, per the review verdict at X." This is Wikidata's statement model: the edge itself is a claim with evidence.

**THE ANTI-IMPORT:** **Schema.org's universal vocabulary.** Our 50 types are domain-specific and that's correct. Adopting an external vocabulary would force our concepts into someone else's taxonomy and lose the precision we need.

**STATUS:** LIVE. 50+ types, used by atom citations. No qualifiers, no constraints beyond label strings.

---

## core/events (3 modules)

### 6. Event Log (event_log.py)

**WHAT IT DOES:** Canonical event capture. `capture(kind, detail, refs, agent_id)` writes to the durable ledger. Singleton `get_event_log()` returns the canonical instance. Events are the system's "what happened" — every learn, graduate, bench, flip, injection, and bus-promoted event flows through here.

**CONNECTED TO:**
- Writes to: `ledger.py` (append-only stream)
- Written by: `agent_cli.py` (every CLI verb), `at_action.py` (flips, injections, outcomes), `promoter.py` (bus→event promotion), hook scripts
- Read by: `event_query.py`, `event_index.py`, `funnel.py`, `curator.py`, `forge.py`, `replay.py`

**COMPARABLE SYSTEMS:**
1. **Event Sourcing (Fowler)** — state is derived from events, not stored directly. Our events are a SIDE EFFECT of state changes; we don't yet derive state from replaying events. The sqlite migration tonight proves we CAN rebuild from events if needed.
2. **CQRS** — separate read and write models. Our `event_index.py` IS a CQRS read model: it maintains a Store-backed index (zset scored by time) for fast window queries, rebuilt from the event stream.
3. **Change Data Capture (Debezium)** — capture DB changes as events. We're doing the inverse: events ARE the data; the store is a materialized view.

**THE DELTA:**
- Event Sourcing: we write events but don't yet rebuild state from them. The sqlite migration was a one-shot script, not a general replay mechanism. If the store is corrupted, we can't rebuild it from the ledger.
- CQRS: our event_index is a good start but not general — it indexes by time only. No per-agent, per-kind, or per-target indexes. Queries like "all flips credited to lesson X" scan the event log.

**THE IMPORT:** **Make the event stream the source of truth, not a side effect.** Today, `agent_cli.py learn` writes to the store FIRST, then captures an event. If the event capture fails, the store is updated but the event is lost — we've silently diverged. Flip the order: capture the event, then project to the store. The store becomes a materialized view that can be rebuilt from events.

**THE ANTI-IMPORT:** **Full CQRS with separate databases.** Event Sourcing + CQRS at scale uses separate databases for reads and writes, with eventual consistency and complex synchronization. We're a single-node system; splitting reads and writes across databases adds latency and failure modes for no benefit. The event_index as an in-store projection is the right scope.

**STATUS:** LIVE. Singleton. Captures events to the ledger. `event_index.py` provides time-window queries. No replay capability (UNVERIFIED — `replay.py` exists but I haven't traced whether it can rebuild the full store).

---

### 7. Event Index (event_index.py)

**WHAT IT DOES:** Store-backed time-range index over the event log. Maintains a zset `events:raw:tindex` scored by epoch time. `events_in_window(start, end)` queries by score range. Bounded — evicts oldest entries when the index exceeds capacity.

**CONNECTED TO:**
- Reads from: `event_log.py` (rebuild source), itself (Store)
- Written to by: `event_log.py` (on each capture, if index is enabled)
- Queried by: `event_query.py`, `chronicler.py`, `funnel.py`, `curator.py`

**COMPARABLE SYSTEMS:**
1. **Elasticsearch** — time-range queries over indexed documents. Our zset-based index is simpler but single-dimensional (time only). Elasticsearch would add full-text search over event detail.
2. **TimescaleDB** — time-series PostgreSQL extension. Automatic partitioning by time, retention policies. Our manual eviction (`zremrangebyrank` when over capacity) is a crude retention policy.

**THE DELTA:**
- Elasticsearch: multi-field queries, full-text search, aggregations. Our index is time-only; you can't query "all flips by agent deepseek."
- TimescaleDB: automatic time partitioning (hypertables), retention policies, continuous aggregates. Our index is a single zset with manual eviction.

**THE IMPORT:** **Make the event index a SQL table, not a zset.** With SqliteStore landed, the event index can be a `CREATE TABLE event_index (ts REAL, kind TEXT, agent_id TEXT, detail TEXT, ...)` with a `CREATE INDEX ON event_index(ts)` and `CREATE INDEX ON event_index(kind, agent_id)`. This enables multi-dimensional queries (all flips by agent, all learns in a window) that the zset cannot express. The zset was the best we could do with the Redis-emulation model; SQL makes it obsolete.

**THE ANTI-IMPORT:** **TimescaleDB's hypertables.** Adding a PostgreSQL extension for time-series when SQLite's B-tree indexes already handle time-range queries perfectly at our scale. Premature specialization.

**STATUS:** LIVE. Zset-based, time-only index. Bounded capacity. Rebuilt from event log on startup.

---

### 8. Event Query (event_query.py)

**WHAT IT DOES:** High-level query interface over the event log + index. `recent(limit, kinds, agent_id)`, `in_window(start, end)`, `events_by_kind(kind)`. Wraps the raw ledger access and the event_index.

**CONNECTED TO:**
- Reads from: `event_index.py` (time-window queries), `ledger.py` (raw scan)
- Used by: `funnel.py`, `curator.py`, `forge.py`, `at_action.py` (flip history for trigger mining)

**COMPARABLE SYSTEMS:**
1. **Kafka Streams / KSQL** — stream processing with filters, aggregates, windows. Our query interface is pull-based; Kafka Streams is push-based (continuous queries).
2. **Elasticsearch Query DSL** — structured queries with filters, aggregations, sorting. Our query interface is Python function calls; ES has a query language.

**THE DELTA:**
- Kafka Streams: continuous queries, windowed aggregates, state stores. We have no continuous query capability — every query is a point-in-time pull.
- Elasticsearch: rich query language. We have three query methods (recent, in_window, by_kind) — no composition, no filtering beyond kind/agent.

**THE IMPORT:** UNVERIFIED — the SqliteStore migration may make this module unnecessary. If events live in SQL tables with indexes, direct SQL queries replace the need for a separate query module. This is a collapse opportunity, not an enhancement.

**THE ANTI-IMPORT:** **Kafka Streams.** Continuous stream processing adds operational complexity (state stores, changelog topics, rebalancing) that a single-node system doesn't need. Pull-based queries are sufficient.

**STATUS:** LIVE. Thin wrapper. May be obsoleted by SqliteStore.
