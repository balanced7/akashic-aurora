# PRIOR ART -- every subsystem, beside what the field already built

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_prior_art_register.py`.
> INVENTORY is derived from live code and cannot rot. PRIOR ART is authored in
> `data/prior-art/register.json`. COVERAGE is derived: **GAP** = no entry, **DRIFT** =
> the subsystem changed size since it was surveyed. DRIFT does NOT claim the research
> is wrong -- only that the thing researched has moved and nobody has looked since.
> Companion: MAP.md (module census) - ARCHITECTURE.md (skeleton).

## Why this file exists

Daniel, 2026-07-26: *"We keep finding gold when we do this but we rarely do it so I
want a full comprehensive suite so we can actually start making informed decisions
instead of stepping on every rake as it comes along."*

The claim is empirical, not aspirational. In one night, five sweeps each paid:
oxlint gave confidence-tiered gating; ruff already implemented a lint we were about to
hand-write; pytest already shipped the entire mechanism for the CI-honesty slice;
Letta's plain files beat a graph memory system; Wikidata's three ranks run at ~1.5B
statements where ATMS dies around 100 beliefs. The cost of NOT sweeping is measured in
rebuilt wheels and dead ends, so the sweep is now a standing artifact rather than a mood.

## Coverage: 8 current, 0 drift, 14 gap (of 22 subsystems)

**GAP -- no prior-art entry yet.** The honest backlog, worst first:

- `core/narrative` (17 modules)
- `agent/harness` (9 modules)
- `core/primitives` (7 modules)
- `scripts/hooks` (7 modules)
- `scripts/generators` (6 modules)
- `core/signals` (2 modules)
- `core/trust` (2 modules)
- `core/fleet` (2 modules)
- `core/state` (2 modules)
- `core/codex` (2 modules)
- `core/perspectives` (2 modules)
- `agent` (2 modules)
- `scripts/ops` (2 modules)
- `core/renew` (1 modules)

---

## `core/foundation` -- 8 modules  ·  current

**What it does.** The Store: a Redis-command-shaped key/value substrate emulating five structures (kv, hash, list, set, zset) over three backends -- RedisStore (pass-through), FileStore (JSON whole-file, superseded), SqliteStore (WAL, landed 2026-07-26), and HybridStore (dual-write, Redis-preferred reads).

**Connected to.** Everything. create_store() is the universal factory and no production code imports a backend directly, so every consumer -- learning store, agent memory, beat log, chronicler, event index, recall, runners -- inherits its backend from one line.

**Comparable systems.**

- **SQLite (WAL mode)** — ADOPTED 2026-07-26. One writer, concurrent readers, ACID, stdlib. Measured on our 3-process probe: 450 writes attempted, 450 survived, versus FileStore's 155.
- **LMDB** — Rejected. Multi-process safety is its design centre and reads are lock-free mmap, but zset scores are mutable and maintaining score order in a key-sorted B-tree needs a secondary index or full scan. deepseek: 'the zset encoding alone is a design project'. Also not stdlib.
- **Datomic** — Immutable assert/retract over a fact log with as-of queries. Never deletes. The model our supersession problem actually wants, at a cost we have not priced.
- **SQL:2011 temporal tables (Snodgrass bitemporal)** — Valid-time and transaction-time columns; supersede by closing an interval rather than deleting. Proven at billions of rows in ordinary relational engines. Nearly free now that we are on SQL, and was impossible in a JSON blob.

**The delta.** Every comparable system makes superseded state a first-class, queryable thing. Ours had no representation for it at all -- writes overwrote, and a concurrent writer's whole-dict flush erased the other's keys with no error (measured 65.6% loss).

**The import.** Bitemporal columns on the durable tier. Now that the backend is SQL this is two timestamp columns plus a read-path predicate, where in a JSON blob it would have been a rewrite. The SQLite migration is the enabler and neither was obvious from the other.

**The anti-import.** Do NOT adopt Datomic's full immutable-log model wholesale. It is the most correct answer here and it would replace a substrate five subsystems depend on, for a corpus of 455 lessons. The measured defect was write loss, and SQLite already fixes that; the immutability is a separate want that must earn its own slice.

**Evidence.** docs/filestore-coherence-design-2026-07.md; tests/test_filestore_coherence.py (strict xfail pin); tests/test_sqlite_store.py (6 cross-process pins); research/reviewed/storage-engine-sweep-2026-07-26.md

_Reviewed 2026-07-26 by claude._

## `core/events` -- 3 modules  ·  current

**What it does.** The append-only event firehose and its time index -- every agent action, learning, decision and bus message, queryable by agent, kind and recency.

**Connected to.** Written by nearly every verb; read by story, events, promoted, lookback and the boot digest.

**Comparable systems.**

- **Event sourcing / CQRS** — The log is the system of record; read models are projections rebuilt from it. Our own corpus already records this as the clean pattern for the narrative spine.
- **Kafka log compaction** — Retains the latest value per key while keeping the log append-only -- bounded storage without losing the append-only property.
- **Certificate Transparency** — Append-only Merkle log where inclusion and consistency are cryptographically PROVABLE, not merely asserted. The strongest available answer to 'how do you know the record was not altered'.

**The delta.** Ours is append-only by convention rather than by construction: nothing prevents or detects a rewrite. CT makes tampering detectable; log compaction bounds growth without breaking append-only. We have neither property.

**The import.** Log compaction semantics for the high-volume families (trace, impressions) so retention is bounded without special-casing deletion -- the same reasoning that led to lane-scoped retention.

**The anti-import.** Do NOT add Merkle-proof tamper-evidence. It answers a threat we do not have (a hostile local editor) at real complexity cost, and our actual measured event-integrity problem was silent WRITE LOSS in the store beneath, which is now fixed. Solve the defect we measured, not the one that is interesting.

**Evidence.** Corpus lesson spine_v1_event_time_index records the CQRS read-model pattern as already-chosen for the narrative spine

_Reviewed 2026-07-26 by claude._

## `core/signals` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/comm` -- 36 modules  ·  current

**What it does.** The Bifrost bus and everything around it -- purpose-keyed lanes (work / trace / sig), per-agent consume cursors, packet envelopes with integrity and fragmentation, expectations and redrives, the wake listener, the launcher, and the fidelity ladder (inform / steer / interrupt / halt). By far our largest subsystem.

**Connected to.** Every agent talks through it. Writes to core/events; read by wake, runners, the UI console and boot; coordinates with core/coord for consumer seats.

**Comparable systems.**

- **Kafka** — Consumer offsets, at-least-once by default, and REWIND -- a consumer can be moved back to an arbitrary point and replay everything, which is how downstream state gets rebuilt after a bug.
- **NATS JetStream** — Core NATS is fire-and-forget at-most-once; JetStream adds durable streams, at-least-once and replay. Three delivery tiers that map onto MQTT's QoS levels.
- **MQTT QoS 0/1/2** — Delivery guarantee as an explicit per-message property rather than a property of the whole system.
- **Erlang/OTP mailboxes + supervision** — Per-process mailboxes with selective receive, and failure handled by supervised restart rather than by defensive code in the consumer.

**The delta.** Two gaps. (1) We partition lanes by PURPOSE (work/trace/sig) and have organically ended up with different delivery guarantees per lane -- trace is effectively fire-and-forget, work is at-least-once with redrive -- but we never NAMED that as a QoS tier, so the guarantee is emergent rather than declared. (2) We have skip-to-now but no REWIND: Kafka can replay a consumer from an arbitrary earlier point, which is exactly what rebuilding state after a bug needs, and it is the capability we lacked every time a cursor got scarred this week.

**The import.** Declare the per-lane delivery guarantee explicitly, the way MQTT declares QoS, so consumers can reason about it instead of inferring it. Cheap: it is documentation plus an assertion, not new transport.

**The anti-import.** Do NOT pursue exactly-once. Kafka's transactional exactly-once is enormous machinery, and RB-26 already commits us to the cheaper correct answer -- idempotent consumers under at-least-once. Chasing exactly-once would replace a working discipline with a distributed-transaction problem we do not need at five processes on one machine.

**Evidence.** LIVE_CONSTRAINTS RB-26 (cursor advances AFTER processing; a crash redelivers), T039/T044 lane router, T045 consumer cutover. UNVERIFIED: whether a rewind primitive exists anywhere in the verb surface.

_Reviewed 2026-07-26 by claude._

## `core/coord` -- 11 modules  ·  current

**What it does.** Coordination primitives: advisory path locks, the RB-21 consumer seat with generations, the task ledger with gated transitions, the conductor, and expectation/redrive bookkeeping.

**Connected to.** Guards concurrent writes across seats; the ledger is read at boot and is declared to outrank notes and bus messages in the precedence doctrine.

**Comparable systems.**

- **Google Chubby** — Coined SEQUENCERS -- monotonically increasing tokens handed out with a lock, which the protected RESOURCE checks and rejects if stale.
- **etcd / ZooKeeper** — The same idea as a first-class primitive: etcd's key revision or ZooKeeper's zxid IS the fencing token. etcd also ships a Lease API -- grant(ttl) returns a lease_id, keys attach to it, a keepalive stream renews, and expiry auto-deletes everything attached.
- **Kleppmann's fencing argument** — A lock WITHOUT fencing is unsafe by construction: a holder paused by GC can wake after expiry and still act. The token is not an optimisation, it is the correctness property.
- **Temporal** — Durable execution -- the workflow's progress is the persisted thing, so a crashed worker resumes rather than needing a lock to prevent double-work.

**The delta.** SMALLER THAN EXPECTED, and this entry was corrected by checking. I assumed the classic half-implementation -- tokens issued but never validated. VERIFIED FALSE: bus.py advance_to executes a Redis LUA script that refuses stale generations and backwards ids AT THE RESOURCE, atomically, returning STALE_GENERATION so a fenced-out predecessor must stand down. That is exactly where Chubby and etcd put the check, and it puts us ahead of most hand-rolled locking rather than behind it. The Redis dependency is coherent rather than a gap: the bus is Redis Streams by design and ephemeral, so the SQLite store migration does not touch this path. The remaining real gap is the DEAD HOLDER -- a process that dies holding a lock -- which is open and blocking the FileStore lock design.

**The import.** etcd's lease-attachment shape: resources attach to a lease id and expiry cascades automatically, instead of every holder managing its own TTL. That directly addresses the dead-holder case, which is the one genuinely open problem here.

**The anti-import.** Do NOT adopt Raft or any consensus protocol. It buys multi-node correctness at a real latency and complexity cost, and we are five processes on ONE machine with a shared filesystem. Kleppmann's own framing reserves consensus locks for correctness-critical DISTRIBUTED cases; ours is local coordination and SQLite's own locking already covers the store.

**Evidence.** VERIFIED at core/comm/bus.py:838-866 -- guarded Lua, stale-generation and backwards both refused at the resource on any cursor hash. LIVE_CONSTRAINTS RB-21. Corpus lesson rb21_live_drill_single_process_blind_spot notes the drill was single-process, so the mechanism is verified by CODE READING and the cross-process rejection is still unexercised by a live drill.

_Reviewed 2026-07-26 by claude._

## `core/learning` -- 3 modules  ·  current

**What it does.** The lesson corpus: learning_store (455 lessons as learn:experiment:* hashes), agent_memory, consolidation. Each lesson carries tried/result/recommend, an agent_id, a success verdict and a confidence field.

**Connected to.** Written by learn() from CLI and MCP; read by all of core/recall; projected into boot context and at-action injection.

**Comparable systems.**

- **Wikidata** — ~1.5B statements. Three RANKS (preferred/normal/DEPRECATED), per-statement REFERENCES, time QUALIFIERS, and properties recording the REASON for a rank change. Deprecated statements are kept and simply not returned by default.
- **Zep / Graphiti** — Bi-temporal: valid-time and ingestion-time per fact, four timestamps, supersede by marking expired rather than deleting.
- **W3C PROV-O / nanopublications** — Standard vocabularies for who-said-what-derived-from-what. Machine-readable attribution as a first-class field.
- **Truth Maintenance Systems (JTMS/ATMS)** — REJECTED on measurement, not taste. ATMS is exponential worst-case and the literature reports it performing well at roughly 100 beliefs. We are at 455. The formally elegant answer dies before we start.

**The delta.** Wikidata is explicitly a SECONDARY knowledge base -- it collects and links to references rather than asserting facts. Our corpus asserts: roughly 300 of 440 lessons reportedly carry no checkable anchor. And their deprecation is a stated fact WITH references, where our is_benched is a rank suppression that self-seals (a demoted lesson stops surfacing, so it can never earn the credit that would redeem it).

**The import.** Replace demotion with time-bounded invalidation plus a recorded REASON. It removes an existing self-sealing loop rather than adding a second one, it is a subtraction, and it needs no working metric to justify -- which matters because our funnel metric is currently defective.

**The anti-import.** Do NOT adopt a continuous confidence score. Wikidata runs 1.5B statements on THREE ranks. The simplicity is the scaling property. A per-lesson scalar is also arguably a category error, since confidence is a property of (lesson, context) rather than of the lesson.

**Evidence.** research/reviewed/recall-redesign-peer-research-2026-07-26.md; Wikidata Help:Ranking and Help:Deprecation; the ~300/440 cites figure is UNVERIFIED and being re-derived by deepseek

_Reviewed 2026-07-26 by claude._

## `core/recall` -- 10 modules  ·  current

**What it does.** Retrieval over the lesson corpus: at_action (PreToolUse injection), funnel (surface/credit accounting), curator (bench/unbench), forge (lesson content optimisation), anchors, dissent, lookback, knowledge_map.

**Connected to.** Reads the learning store; fires from the PreToolUse hook on every tool call; writes impressions and flip credit back into the funnel; renders into agent context at boot and at action.

**Comparable systems.**

- **Letta (ex-MemGPT)** — Attached PLAIN FILES to an ordinary agent and scored 74.0 on LoCoMo against 68.5 for mem0's best graph variant, on the stated grounds that specialised SINGLE-HOP retrieval underperforms an agent searching iteratively. Our at_action injection IS single-hop pre-selection.
- **Lucene / BM25** — Decades-proven lexical ranking with an inverted index. Answers top-k without materialising the corpus -- the property we lack.
- **HNSW / DiskANN / SPANN** — Approximate nearest-neighbour indexes built for the millions-of-entries regime Daniel named as the target.
- **SQLite FTS5** — Full-text search in the engine we just adopted. Hermes (Feb 2026) uses exactly this for agent memory. Would let lookback stop hand-rolling keyword search.

**The delta.** Every comparable system pushes the filter and the top-k INTO an index. Ours materialises the entire corpus per query and ranks in Python. There is no index, no filter pushdown, no top-k.

**The import.** Query pushdown: SELECT ... WHERE ... ORDER BY ... LIMIT k over an index, instead of load-everything-then-rank. This is the single highest-value change in the register and it is only possible since the SQLite migration.

**The anti-import.** Do NOT reach for a vector index first. Our measured failure is O(n) materialisation, not poor semantic matching -- and the Letta result warns that adding retrieval sophistication can LOSE to letting the agent search. Fix the algorithmic shape before adding ML to it.

**Evidence.** MEASURED 2026-07-26: load_all_learnings_from_store reads the full index then does one store read PER LESSON; core/recall/at_action.py:150 calls it on the PreToolUse path. 455 lessons = 220ms/query, 0.483ms/lesson. Extrapolated: 100k = 48s, 1M = 483s per query. Lesson: recall_scaling_defect_is_the_algorithm_not_the_store

_Reviewed 2026-07-26 by claude._

## `core/primitives` -- 7 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/renew` -- 1 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/narrative` -- 17 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/trust` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/fleet` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/state` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/codex` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `core/perspectives` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `agent/harness` -- 9 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `agent` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `scripts/hooks` -- 7 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `scripts/checkers` -- 12 modules  ·  current

**What it does.** Twelve guards run at ship/CI time: door parity, doc currency, pointer promises, comprehensibility, boundaries, clobber scan and others. They fail the build on drift.

**Connected to.** Invoked by ship gates and CI; several read the generated docs (MAP/PHYSICS/MODULE_INDEX) and compare them against live code.

**Comparable systems.**

- **oxlint** — 844 rules sorted by CONFIDENCE -- correctness (definitely wrong) through suspicious, pedantic, style, restriction, nursery -- with only correctness on by default (113 of 844). Provenance is a queryable column: every rule carries its source plugin and the table filters on it. Fixability is tiered, including a marker meaning 'a fix is possible and we have not built it'.
- **ruff** — Already implements the syntactic half of the empty-error-collapse lint we were about to hand-write: S110 (try-except-pass) and BLE001 (blind except). BLE001 is off by default -- the same confidence-tiering, arrived at independently.
- **OPA / Rego** — Policy as data, evaluated against structured input, with decisions explainable rather than boolean.

**The delta.** Our gates are all-or-nothing: a check either fails the build or does not exist. oxlint's axis is how SURE the tool is that something is a defect, and it gates only on the high-confidence subset. That is why our CI was a constantly-ringing fire alarm and theirs is an instrument.

**The import.** Confidence-tiered gating: the default gate is the high-confidence subset, everything else is visible, counted and non-blocking. Plus provenance as a queryable field on findings.

**The anti-import.** Do NOT import a 'nursery' tier of experimental checks that fire but do not gate. We already have the failure mode it creates -- checks nobody reads. Our version of that marker must be counted on a surface a human opens, or it is just a quieter version of the fire alarm.

**Evidence.** research/reviewed/peer-oss-2026-07-25-lint-taxonomy-and-agent-memory.md; the 2026-06-19 audit counted ~65 bare excepts, which is the starting inventory for the ruff import

_Reviewed 2026-07-26 by claude._

## `scripts/generators` -- 6 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `scripts/ops` -- 2 modules  ·  GAP

_No entry. This subsystem has not been swept against the field._

## `tests` -- 331 modules  ·  current

**What it does.** 331 test modules plus conftest, providing universal backend isolation, a parity exerciser shared across store backends, and a differential harness that cross-verifies two implementations of the same semantics.

**Connected to.** Runs against every subsystem; conftest controls isolation and (since 2026-07-25) Windows console suppression for spawned children.

**Comparable systems.**

- **pytest xfail(strict=True)** — ADOPTED. Runs the body, expects a known failure, stays quiet, and FAILS THE BUILD the day it starts passing. raises= narrows the excuse to one exception, so a differently-failing test surfaces as a real failure.
- **pytest-error-for-skips** — Turns skips into failures so a suite cannot silently stop testing when a dependency vanishes.
- **Known-failure baselines (node-id diffing)** — Our own suite-baseline already does this: new/fixed/inherited deltas make churn visible even at an identical failure count.

**The delta.** Before 2026-07-25 the suite used skipif 50 times and xfail ZERO times. skip does not run the body, so 'cannot run here' and 'would fail if it ran' collapsed into one silent outcome -- the same empty-and-error-share-a-type defect we were hunting in production code, living in the test suite.

**The import.** xfail(raises=..., strict=True) wherever the body can safely run, plus xfail_strict in the ini. Already used for the FileStore coherence pin, which is the repo's first genuine xfail.

**The anti-import.** Do NOT convert skips to xfail where running is genuinely unsafe or impossible -- a true platform gate should stay a skip. And never let an xfail be flaky: under strict, an occasional XPASS cries wolf, which is the disease rather than the cure.

**Evidence.** MEASURED: skipif=50, skip=1, importorskip=11, xfail=0 before the change. tests/test_filestore_coherence.py verified deterministic 5/5. research/reviewed/ci-tree-differential-census-2026-07-25.md

_Reviewed 2026-07-26 by claude._

