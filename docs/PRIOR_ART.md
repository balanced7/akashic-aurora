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

## Coverage: 8 current, 14 drift, 0 gap (of 22 subsystems)

**DRIFT -- surveyed, but the subsystem has changed size since:**

- `core/foundation` -- DRIFT (8->10), reviewed 2026-07-26
- `core/comm` -- DRIFT (36->66), reviewed 2026-07-26
- `core/coord` -- DRIFT (11->25), reviewed 2026-07-26
- `core/learning` -- DRIFT (3->5), reviewed 2026-07-26
- `core/recall` -- DRIFT (10->16), reviewed 2026-07-26
- `core/primitives` -- DRIFT (7->8), reviewed 2026-07-26
- `core/trust` -- DRIFT (2->4), reviewed 2026-07-26
- `core/fleet` -- DRIFT (2->7), reviewed 2026-07-26
- `agent/harness` -- DRIFT (9->13), reviewed 2026-07-26
- `scripts/hooks` -- DRIFT (7->8), reviewed 2026-07-26
- `scripts/checkers` -- DRIFT (12->19), reviewed 2026-07-26
- `scripts/generators` -- DRIFT (6->11), reviewed 2026-07-26
- `scripts/ops` -- DRIFT (2->8), reviewed 2026-07-26
- `tests` -- DRIFT (331->636), reviewed 2026-07-26

---

## `core/foundation` -- 10 modules  ·  DRIFT (8->10)

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

## `core/signals` -- 2 modules  ·  current

**What it does.** The Agent Signal Ledger -- an ordered record of every signal agents emit -- plus a minimal coordinator logging API.

**Connected to.** Written by agents during work; feeds the event firehose and the coordination surfaces.

**Comparable systems.**

- **OpenTelemetry** — Traces, metrics and logs under ONE semantic convention, with span context propagated across process boundaries.
- **RED / USE method** — Prescribed metric sets (Rate-Errors-Duration; Utilisation-Saturation-Errors) so dashboards are comparable across services.
- **structlog / canonical log lines** — One wide structured event per unit of work rather than scattered log statements.

**The delta.** We have an ordered signal record but no shared semantic convention, so each producer names things its own way and cross-agent comparison is manual. OTel's actual contribution is the CONVENTION, not the transport.

**The import.** Canonical log lines -- one wide structured event per turn carrying every dimension, instead of many narrow ones. It makes cross-agent questions answerable by filtering rather than by joining.

**The anti-import.** Do NOT adopt the OpenTelemetry SDK. It is a distributed-tracing runtime for multi-service systems; we have five local processes and already own the bus that would carry spans. Take the naming conventions, not the dependency.

**Evidence.** Docstrings read 2026-07-26. UNVERIFIED: consumer set and whether the ledger is queried operationally or only written.

_Reviewed 2026-07-26 by claude._

## `core/comm` -- 66 modules  ·  DRIFT (36->66)

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

## `core/coord` -- 25 modules  ·  DRIFT (11->25)

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

## `core/learning` -- 5 modules  ·  DRIFT (3->5)

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

## `core/recall` -- 16 modules  ·  DRIFT (10->16)

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

## `core/primitives` -- 8 modules  ·  DRIFT (7->8)

**What it does.** Cross-cutting primitives built once at the seam: the Ranker (keyword relevance with IDF weighting), the faithfulness critic, supersession helpers, and the distiller family.

**Connected to.** Ranker feeds recall; supersession.is_active is the shared truth with core/codex's bi-temporal lifecycle; the critic guards generated summaries.

**Comparable systems.**

- **BM25 / Okapi ranking** — The decades-proven lexical baseline. Includes DOCUMENT LENGTH NORMALISATION, which we lack.
- **Learning-to-rank (LambdaMART)** — Learned ranking from click/relevance feedback.
- **RAGAS faithfulness** — LLM-judged groundedness of generated text against its sources.

**The delta.** The Ranker has IDF weighting but no document-length normalisation, so verbose lessons matching on generic terms are not penalised for dilution. deepseek prices the fix at roughly five lines in _damped_overlap.

**The import.** BM25 document-length normalisation -- log(1 + doc_length / avg_doc_length) into the keyword score. Small, deterministic, and it addresses a real ranking distortion.

**The anti-import.** Do NOT adopt learning-to-rank, and do NOT adopt RAGAS-style faithfulness. Learned ranking needs a TRUSTWORTHY funnel and ours is double-logged across a pre/post-fix series -- fix the measurement before learning from it. RAGAS would put an LLM call on the recall hot path, and deepseek's framing is right that the no-LLM constraint here is a deliberate design trade-off rather than a gap: recall must stay cheap and deterministic.

**Evidence.** research/reviewed/deepseek-system-inventory-p4-recall-learning-narrative-2026-07-26.md sections 27-28

_Reviewed 2026-07-26 by deepseek (swept), claude (folded)._

## `core/renew` -- 1 modules  ·  current

**What it does.** Session signals: fold one session's tool calls into deterministic context-health signals that survive the session.

**Connected to.** Reads the session transcript at SessionEnd; writes a durable session_signals event consumed by later boots.

**Comparable systems.**

- **Post-incident review automation** — Deriving structured findings from a timeline automatically rather than by recollection.
- **Git bisect / blame** — Deterministic attribution of an outcome to a point in a history.
- **Continuous profiling** — Always-on sampling so questions can be asked after the fact instead of requiring foresight.

**The delta.** One module doing a genuinely valuable thing -- deriving signals deterministically from what actually happened rather than from self-report. That determinism is exactly what kimi's binding-failure ruling says is unavailable at the APPLICATION stage, which makes this subsystem more important than its size suggests.

**The import.** Always-on capture, profiling-style: the signals worth having are the ones you did not know you needed, and they can only be derived if the raw material was kept.

**The anti-import.** Do NOT extend this into self-reported application claims. Deterministic derivation from tool calls is trustworthy; asking an agent to declare whether a lesson changed its behaviour is gameable, and kimi's ruling is explicit that no applied-stage gauge survives self-report.

**Evidence.** Docstring read 2026-07-26. Design context: kimi's binding-failure ruling (application observable only via self-report or counterfactual) in the recall redesign round.

_Reviewed 2026-07-26 by claude._

## `core/narrative` -- 17 modules  ·  current

**What it does.** The narrative spine: Beat -> Chapter -> Track -> Atlas, with a chronicler that distils beats into chapters, an event bridge and promoter joining the raw firehose, theme and track inference, episode bookends, drift detection, and an append-only confidence-gated tag governance path with a flag-only tag auditor.

**Connected to.** Reads the event firehose; writes beats and chapters to the Store; shares chapter_lifecycle's bi-temporal stamping with core/codex; surfaces via story, episode and the boot digest.

**Comparable systems.**

- **Event sourcing with projections** — Beats are events, Chapters are read models rebuilt by the chronicler. Our own corpus already records CQRS as the chosen pattern here.
- **RAPTOR recursive summarisation** — Hierarchical roll-up of a corpus into progressively coarser summaries -- the Beat-to-Chapter-to-Atlas shape, with an established evaluation.
- **Wikipedia revision + talk pages** — Every assertion carries a revision history and a separate space for contested interpretation, rather than one authoritative render.

**The delta.** Two things already right and worth noting rather than 'fixing': tag_governance is an APPEND-ONLY confidence-gated write path, and tag_audit is FLAG-ONLY (it returns suspects and does not act). Those are the exact disciplines the recall redesign has been trying to invent for lessons. The gap is that theme and track inference are Tier-0 heuristics with an embedding augmentation, and their accuracy is not measured.

**The import.** Nothing external and urgent. The internal one is the same as codex's: the lesson plane should adopt this plane's append-only, flag-only, confidence-gated tagging discipline rather than reinventing it.

**The anti-import.** Do NOT adopt LLM-based summarisation on any hot path. The spine's value is that it is deterministic and cheap; a chronicler that needs a model call becomes a cost and a nondeterminism on every session close.

**Evidence.** Docstring sweep of all 17 modules 2026-07-26. tag_governance.py: 'the append-only, confidence-gated re-tag write path'. tag_audit.py: 'FLAG-ONLY: it returns suspects'. chapter_lifecycle.py: 'bi-temporal stamping, in-place regeneration'. Partial prior-art detail in research/reviewed/deepseek-system-inventory-p4-recall-learning-narrative-2026-07-26.md

_Reviewed 2026-07-26 by claude (docstring sweep) + deepseek (partial, p4)._

## `core/trust` -- 4 modules  ·  DRIFT (2->4)

**What it does.** Capability-based access control: capabilities.py issues Capability(action, resource, constraints) tokens and verifies them; registry.py maps agent_id to allowed capabilities and answers can(agent, action, resource).

**Connected to.** Consumed by guards.py for pre-action authorisation and by toolbox.py for verb gating. deepseek marks the full consumer set UNVERIFIED -- neither module has been traced end to end.

**Comparable systems.**

- **Macaroons** — Bearer tokens with caveats, supporting ATTENUATION -- deriving a strictly weaker capability from a stronger one -- plus third-party caveats.
- **OAuth 2.0 scopes** — Our capabilities are essentially scopes with resource-level granularity, minus the refresh/revoke/introspect lifecycle.
- **Kubernetes RBAC** — Role -> RoleBinding -> Subject. We bind agent directly to capability with no intermediate Role abstraction.
- **OPA / Rego** — Policy as code, decoupled from the data it evaluates. Our registry is data with the policy embedded in Python.

**The delta.** Our capabilities are STATIC -- you cannot derive a read-only capability from a read-write one. Macaroon attenuation makes privilege reduction a construction rather than a convention, which matters for a fleet where one seat spawns work for another.

**The import.** Capability attenuation. An agent holding write:* should be able to mint write:scratch/* for a sub-agent by appending a caveat. That prevents privilege escalation by construction rather than by review.

**The anti-import.** Do NOT deploy OPA as a service. An external policy engine consulted on every hook firing would add latency to every tool call, and in-process Python policy is both faster and sufficient at four agents. (deepseek's judgement, and it matches our own measurement that per-tool-call cost is the thing that hurts.)

**Evidence.** research/reviewed/deepseek-system-inventory-p3-coord-trust-fleet-2026-07-26.md sections 21-22. Both modules marked UNVERIFIED by the sweeper -- capabilities.py and registry.py exist and are wired, but consumers are not fully traced. Treat this entry as a map of intent, not of enforcement.

_Reviewed 2026-07-26 by deepseek (swept), claude (folded)._

## `core/fleet` -- 7 modules  ·  DRIFT (2->7)

**What it does.** Presence autopilot supervising the fleet: crash backoff, circuit breaker, presence held across Redis outages, and a refusal to steal a running session's seat.

**Connected to.** Watches runner and seat liveness; interacts with core/coord's consumer seat and with the launcher in core/comm.

**Comparable systems.**

- **Erlang/OTP supervision trees** — Restart strategies (one-for-one, one-for-all, rest-for-one) with intensity limits -- restart storms are bounded by construction rather than by a hand-written breaker.
- **Kubernetes controllers** — The reconcile loop: continuously drive observed state toward declared state, with no assumption that any single action succeeded.
- **systemd** — Restart policies, backoff, and dependency ordering as declarative unit configuration.

**The delta.** Ours is an imperative supervisor with hand-rolled backoff; the comparables are declarative and make the restart POLICY inspectable separately from the code that enforces it.

**The import.** The reconcile-loop framing: describe desired fleet state and let a loop converge toward it, instead of scripting transitions. It makes 'a seat died' an ordinary input rather than an exception path.

**The anti-import.** Do NOT adopt Kubernetes scheduling semantics -- taints, tolerations, priorities and affinity are over-engineered for a four-agent fleet. deepseek's line, and it is the same judgement that rejected Raft for coord.

**Evidence.** research/reviewed/deepseek-system-inventory-p3-coord-trust-fleet-2026-07-26.md section 24. Notable receipt: the autopilot's first live launch proved its safety property by REFUSING to steal a running session's seat, twice, with legible reasons -- a guard that demonstrated itself rather than being asserted.

_Reviewed 2026-07-26 by deepseek (swept), claude (folded)._

## `core/state` -- 2 modules  ·  current

**What it does.** Crash recovery: session_checkpoint.py writes recovery checkpoints; session_recovery.py restores from them with fallback.

**Connected to.** Written during a session's life; read on restart to rehydrate a seat.

**Comparable systems.**

- **Temporal durable execution** — The workflow's progress IS the persisted artifact, so a crashed worker resumes from the log rather than from a snapshot.
- **Write-ahead logging** — Log the intent before the act, so recovery replays rather than guesses.
- **CRIU / process checkpointing** — Whole-process snapshot and restore.

**The delta.** Checkpoints are SNAPSHOTS at points in time; durable-execution systems persist the progress log itself, which makes recovery exact rather than approximate. Ours can only resume from the last checkpoint, losing whatever happened after it.

**The import.** The durable-execution framing for the one place it matters -- long-running jobs that cross an irreversible boundary. Our own corpus already has a lesson about fencing a publish before allowing forced cancellation, which is the same insight arrived at locally.

**The anti-import.** Do NOT adopt a workflow engine. Temporal is the right idea and enormous machinery; at our scale the framing is the import, not the runtime.

**Evidence.** Docstrings read 2026-07-26. Related corpus lesson: publish_fence_before_force. UNVERIFIED: I have not traced how often checkpoints are actually written or whether recovery is exercised.

_Reviewed 2026-07-26 by claude._

## `core/codex` -- 2 modules  ·  current

**What it does.** The knowledge-axis node and its lifecycle. schema.py defines the Resource node and the structural bi-temporal contract; lifecycle.py provides bi-temporal stamping and supersession as TYPE-AGNOSTIC functions over a BiTemporal protocol rather than a base class.

**Connected to.** Shares its lifecycle functions with core/narrative (Chapter uses the same supersede path). core/primitives/supersession.is_active is documented to AGREE with it, so one definition of inactive spans both axes.

**Comparable systems.**

- **Zep / Graphiti bi-temporal model** — Valid time plus ingestion time per fact; supersede by closing validity rather than deleting. THE SAME MODEL WE ALREADY HAVE.
- **SQL:2011 temporal tables** — System-versioned and application-time period tables -- the relational standardisation of the same idea.
- **Datomic** — Immutable assert/retract with as-of queries; supersession is the only mutation.

**The delta.** INVERTED -- this is the one subsystem where we are level with the state of the art rather than behind it. valid_from is set once and never moves, valid_to closes on supersession, recorded_at refreshes on regeneration, and supersede() persists BOTH nodes so the old one stays queryable and inbound links forward via replaces edges. The real gap is not in this subsystem: it is that the LESSON plane never adopted it.

**The import.** Nothing from outside. The import is INTERNAL: make lesson records carry valid_from / valid_to / recorded_at and route retirement through supersede() instead of is_benched. VERIFIED 2026-07-26 by running it -- a lesson-shaped object with those three attributes works with lifecycle.stamp() and lifecycle.is_active() TODAY, unmodified: stamp set both timestamps and is_active correctly flipped when valid_to closed. Three fields buy the whole mechanism. GOTCHA FOUND WHILE VERIFYING: isinstance(node, BiTemporal) returns FALSE even for an object carrying all three attributes, because runtime_checkable Protocols validate METHODS and not DATA members. The lifecycle functions work regardless because they are duck-typed through getattr -- but anyone who adds an isinstance guard for safety will silently break a mechanism that otherwise just works.

**The anti-import.** Do NOT rebuild this for lessons, and do NOT let the recall redesign specify bi-temporal invalidation as new work. The 2026-07-26 recall research recommended importing exactly this from Zep before anyone checked whether we had it. We did.

**Evidence.** VERIFIED by reading core/codex/lifecycle.py: is_active, stamp, regenerate_in_place, supersede. Docstring: 'supersede is the only way a bi-temporal node goes inactive... persists BOTH (the old stays queryable; inbound links resolve to it and forward via replaces)'. Lesson: bitemporal_supersession_already_exists_and_is_type_agnostic

_Reviewed 2026-07-26 by claude._

## `core/perspectives` -- 2 modules  ·  current

**What it does.** Swappable interpretation: schema.py defines Lens and Map shapes as pure data; reinforce.py is an association graph whose edges STRENGTHEN with co-use.

**Connected to.** Reads the knowledge graph; intended to let the same corpus be read through different interpretive frames.

**Comparable systems.**

- **Hebbian learning / co-occurrence graphs** — Edges strengthened by joint activation -- exactly reinforce.py's mechanism, with a long literature on its failure modes.
- **Spreading activation retrieval** — The classic cognitive-model retrieval strategy over an association network.
- **Belnap four-valued logic** — Represent BOTH-supported-and-attacked explicitly rather than resolving to one truth -- the formal shape for holding two perspectives at once.

**The delta.** Co-use reinforcement is a POPULARITY signal, and popularity was the specific trap identified in the authoritative-atoms design work: if authority derives from how often something is cited, we have built a popularity metric wearing a provenance costume. This subsystem is where that risk actually lives in code.

**The import.** Belnap's explicit BOTH state, so two lenses disagreeing is representable rather than resolved. That also happens to be the one mechanism from the recall research that touches binding as well as retrieval, because a visible conflict forces the agent to reason rather than accept.

**The anti-import.** Do NOT let reinforcement strength feed authority or ranking. Hebbian edges measure co-use, which is exactly the popularity signal the provenance design is trying to avoid. Keep reinforcement as a navigation aid, never as a trust signal.

**Evidence.** Docstrings read 2026-07-26: reinforce.py 'an association graph whose edges STRENGTHEN with co-use'. Design context in research/reviewed/recall-redesign-peer-research-2026-07-26.md section 2 (source-provenance vs popularity).

_Reviewed 2026-07-26 by claude._

## `agent/harness` -- 13 modules  ·  DRIFT (9->13)

**What it does.** The seat side of the fleet: how an agent session is launched, kept alive, woken from idle, and stood down. Includes the wake listener, seat lifecycle and the runner glue that turns a bus message into a live turn.

**Connected to.** Driven by core/comm's launcher and bus; coordinates with core/coord's consumer seat and generations; the stop hook enforces that a session stays wakeable.

**Comparable systems.**

- **Erlang/OTP supervision** — Restart strategies with INTENSITY LIMITS -- a supervisor that exceeds N restarts in T seconds escalates rather than looping. Restart storms are bounded by construction.
- **systemd** — Declarative restart policy, backoff, and socket activation -- a unit is started BY demand rather than polling for it.
- **Kubernetes liveness / readiness probes** — Two DISTINCT questions: is it alive, and is it ready to receive work. Conflating them is a classic outage cause.
- **Long-poll / server-sent events** — The standard answer to 'wake on an event without burning a core polling for it'.

**The delta.** The liveness/readiness distinction is the sharp one. Our wake path effectively answers only 'is it alive', and the failure mode we hit repeatedly on 2026-07-25 was a watcher that armed, fired instantly on undrainable mail, and exited -- alive but never ready, six times in a row, with the stop hook asking for the same action each time. OTP's intensity limit is exactly the missing guard: a supervisor that notices N restarts in T seconds and escalates rather than repeating.

**The import.** Restart-intensity limiting on the wake path: detect the insta-fire signature (armed and exited within seconds, same pending count) and escalate with a diagnosis instead of requesting another identical arm. That converts a loop into a finding.

**The anti-import.** Do NOT add a polling supervisor. The corpus already records a wake watcher burning 20% of a core continuously while idle, and the fix was to block correctly rather than to poll faster. Any liveness mechanism here must be event-driven or it re-creates the defect it was added to detect.

**Evidence.** MEASURED 2026-07-25: six consecutive arm-and-exit cycles; root cause was that the watcher peeks the LEGACY stream while drains were going to the work lane. Corpus lessons wake_watcher_insta_fires_lane_divergence and nonseatholder_wake_spin_burns_plan. Pain point P1 in claude-painpoints-2026-07-25, where the deeper issue was named as the stop hook demanding a workaround on a loop.

_Reviewed 2026-07-26 by claude (partial), deepseek (p3 adjacent)._

## `agent` -- 2 modules  ·  current

**What it does.** The agent-facing door surface: the boot/context assembly an agent receives at session start, and the harness-facing glue that carries it.

**Connected to.** Assembles from the task ledger, durable notes, LIVE_CONSTRAINTS, recall and the bus; rendered into every seat's first turn and into the SessionStart whisper.

**Comparable systems.**

- **Model Context Protocol (MCP)** — A typed tool surface with descriptions that ARE the prompt -- discovery and invocation in one contract. We already expose an MCP door beside the CLI.
- **Language Server Protocol (LSP)** — The precedent MCP follows: one protocol, many clients, capabilities negotiated at initialise. Its lesson is that the DOOR outlives the client.
- **OpenAPI / JSON Schema** — Machine-readable contracts that generate clients and validate calls, so the surface cannot silently drift from its documentation.
- **Unix man pages + --help conventions** — The oldest working answer to 'how does a newcomer learn a tool from the tool itself'.

**The delta.** Our door is inconsistent in a way a schema-driven surface cannot be. Three CLI syntax failures in one session on 2026-07-25 -- bifrost-nudge rejecting --text, bifrost-send rejecting positional text after flags, capture taking no agent_id positional while nearly every sibling verb does. Each printed usage, which is good; none was guessable from its neighbours, which is the actual defect. LSP and OpenAPI make that class of inconsistency structurally impossible.

**The import.** Schema-first verb definitions, so the CLI parser, the MCP tool description and the DOORS.md reference are generated from ONE declaration rather than maintained in three places. door-parity already checks that the doors agree; generating them would mean they cannot disagree.

**The anti-import.** Do NOT chase full capability negotiation. LSP's initialise handshake exists because clients and servers version independently across vendors; our doors ship in one repo at one version, and the ceremony would buy nothing.

**Evidence.** Three syntax failures logged 2026-07-25 (claude-painpoints-2026-07-25, pain P4). check_door_parity.py exists and compares CLI/MCP/ToolBox surfaces -- notably it was itself broken by a moved file and reported a clean pass over an EMPTY parse, which is why generation beats checking where it is available.

_Reviewed 2026-07-26 by claude._

## `scripts/hooks` -- 8 modules  ·  DRIFT (7->8)

**What it does.** Seven Claude Code integration hooks: pretooluse (recall injection before every tool call), posttooluse (outcome capture, flip detection, learn nudge), sessionstart (cache warm), sessionend (wrap), userpromptsubmit (plan-time recall), stop (wake enforcement), trace (tool-call to bus).

**Connected to.** Registered in USER settings with absolute paths; read core/recall/at_action and core/comm/bus; write traces, flips and injections. They are the highest-frequency code in the system -- two to three process spawns per tool call.

**Comparable systems.**

- **git hooks** — Identical pattern: a script is registered, the host calls it, exit code decides. Our checkers are effectively pre-commit hooks.
- **pre-commit framework** — A managed runner: environment caching, PARALLEL execution, autoupdate, standard interface. Our 12 checkers run sequentially as raw Python.
- **oxlint category tiers** — Severity as confidence. Our hooks and checkers are binary -- gate or absent.
- **OPA admission control** — Policy evaluated before an operation. Our PreToolUse hook IS admission control, with the policy embedded in Python.

**The delta.** Two. (1) No severity tiers: a checker either fails the build or does not exist, which is why CI reads as a fire alarm. (2) No managed runner: the 12 checkers run sequentially with no caching, re-running against unchanged files.

**The import.** The pre-commit framework for the checkers -- caching, parallelism and autoupdate for a YAML file plus a dependency, not a rewrite. Pairs naturally with oxlint-style tiering so correctness blocks and style warns.

**The anti-import.** Do NOT put an external policy engine on the hook path. These fire two to three times per tool call; we already measured that per-tool-call cost is what makes the system unpleasant to use (it was console spawns, but the lesson generalises). Anything on this path must be cheap by construction.

**Evidence.** research/reviewed/deepseek-system-inventory-p3-coord-trust-fleet-2026-07-26.md section 23. Status LIVE. Also measured by claude 2026-07-25: these hooks were the dominant source of Windows console spam precisely because they fire on every tool call -- the frequency is the defining property of this subsystem.

_Reviewed 2026-07-26 by deepseek (swept), claude (folded)._

## `scripts/checkers` -- 19 modules  ·  DRIFT (12->19)

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

## `scripts/generators` -- 11 modules  ·  DRIFT (6->11)

**What it does.** Six generators projecting live code into documents: MAP.md (module census), MODULE_INDEX.md (docstrings), PHYSICS.md (bounds and env flags), DOORS.md (CLI verb reference), PRIOR_ART.md (this register), and the arch index.

**Connected to.** Read the live source tree; their output is committed; check_comprehensibility re-runs each generator's own render() and fails the build if the committed document differs.

**Comparable systems.**

- **go generate + a CI drift check** — The Go ecosystem's standard: commit generated code, have CI run the generator and fail if the diff is non-empty. Structurally identical to what we do.
- **Golden-file / approval / snapshot testing** — Generate, compare against a committed artifact, fail on drift. Jest snapshots and approval-tests are the same mechanism applied to test output.
- **terraform plan / kubectl diff** — Show the delta between declared and actual and refuse to proceed on unexpected drift. GitOps drift detection generalises it.
- **Sphinx autodoc / Doxygen** — Extract documentation from source. WEAKER than ours: extraction keeps docs derived, but nothing fails if the published output is stale.

**The delta.** Small, and in our favour -- this is a subsystem where we are already doing the established right thing. The generators reuse their OWN render() inside the checker, so there is exactly one definition of correct output and drift is impossible to miss. That is stronger than Sphinx-style extraction, which derives docs but never fails on a stale published copy.

**The import.** Nothing structural. The available refinement is parallelism and caching (the pre-commit import noted under scripts/hooks) -- six generators plus twelve checkers currently run sequentially against unchanged files.

**The anti-import.** Do NOT let any document become authored-and-trusted once it has a generator. The temptation is to hand-edit generated output when the generator is inconvenient; that is how MAP, PHYSICS and MODULE_INDEX all went stale the moment new modules landed on 2026-07-25. The header on every generated file says do not edit by hand, and it must stay true.

**Evidence.** check_comprehensibility.py _derived_docs_current compares each committed doc against the generator's own render. VERIFIED 2026-07-26 by deliberately corrupting PRIOR_ART.md and confirming the checker reports it stale -- a green guard is not proof the guard can fail.

_Reviewed 2026-07-26 by claude._

## `scripts/ops` -- 8 modules  ·  DRIFT (2->8)

**What it does.** Operator tools for the knowledge substrate: snapshot_knowledge.py (snapshot / list / restore / verify across Redis, the file tier and chronicles, keeping the last 20) and reheal_durable_tier.py (backfill the durable tier FROM Redis, added 2026-07-26).

**Connected to.** Reads Redis db0 and the store file(s); writes timestamped snapshot directories under backups/snapshots; the restore path writes back over live state.

**Comparable systems.**

- **PostgreSQL pg_basebackup + WAL archiving** — Physical backup plus a continuous log, giving point-in-time recovery rather than discrete restore points.
- **restic / borg** — Content-addressed, deduplicated, ENCRYPTED snapshots with an explicit integrity-check command -- verification is a first-class operation, not an assumption.
- **sqlite3 online backup API** — ADOPTED 2026-07-26. Reads through the write-ahead log to produce a complete file. The reason a plain file copy is wrong for a live database.
- **ZFS / btrfs snapshots** — Copy-on-write snapshots that are atomic by construction rather than by a copy loop.

**The delta.** Two. (1) We have discrete snapshots and no continuous log, so recovery granularity is 'the last snapshot' rather than a point in time. (2) restic and borg treat VERIFY as a routine command; our snapshots were until tonight taken with a plain file copy that would have silently produced stale artifacts once the store became a WAL database.

**The import.** Routine verification, restic-style: a snapshot that has never been restore-tested is a hypothesis. We now hold 20 snapshots and have exercised restore rarely.

**The anti-import.** Do NOT add deduplication or encryption. Both solve problems we do not have -- our corpus is ~10MB on a local disk with no adversary in the model -- and both add a failure mode between us and our own recovery path, which is the one place complexity is least welcome.

**Evidence.** Fixed 2026-07-26: snapshot_knowledge.py:105/153-156 and harmonize_knowledge.py:78 used shutil.copy2, which under a WAL database yields a stale-or-corrupt copy WHILE REPORTING SUCCESS. Moved to the online backup API with sidecar clearing on restore; pinned in tests/test_snapshot_wal_correct.py.

_Reviewed 2026-07-26 by claude._

## `tests` -- 636 modules  ·  DRIFT (331->636)

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

