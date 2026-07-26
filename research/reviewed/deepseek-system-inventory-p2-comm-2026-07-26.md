# System Inventory + Prior-Art Register — Part 2: Comm (Bus, Lanes, Wake, Launcher)
## DeepSeek, 2026-07-26 — overnight program

---

## core/comm (36 modules — covered: the load-bearing ones)

### 9. Bus (bus.py)

**WHAT IT DOES:** Ephemeral message transport over Redis Streams. Per-agent inbox streams (`bifrost:inbox:<agent>`), shared broadcast stream (`bifrost:broadcast`). Per-agent cursors track last-read position. Bounded streams (maxlen). Deliberately NOT durable — the ledger is the durable record.

**CONNECTED TO:**
- Reads from: Redis Streams (inbox + broadcast)
- Written to by: `BifrostAPI.send()`, `BifrostAPI.broadcast()`, hook scripts, runners, `bifrost-sync`, `bifrost-drain`
- Promoted to: `promoter.py` (salient kinds → ledger events)
- Cursor managed by: `bus.py` itself (per-agent cursor hash)

**COMPARABLE SYSTEMS:**
1. **NATS** — CNCF messaging with subjects, queue groups, request-reply. NATS subjects are hierarchical (`bifrost.inbox.claude`); our stream keys are flat. NATS has built-in request-reply; we build reply on top of send + meta.reply_id.
2. **Kafka** — partitioned log with consumer groups. Our broadcasts go to a single stream read by all; Kafka would partition by agent for parallel delivery. Overkill for single-node.
3. **MQTT** — pub/sub with QoS tiers (0=at-most-once, 1=at-least-once, 2=exactly-once). Our bus is QoS 1 (at-least-once via streams + consumer groups). MQTT's retained messages (last message on a topic) would give us "latest directive" without querying.
4. **Erlang/OTP mailboxes** — per-process message queues with pattern matching. Each agent is an Erlang process with a mailbox; our inbox stream is the Redis-backed equivalent. Erlang's selective receive (pattern-match on messages) is more expressive than our pull model.

**THE DELTA:**
- NATS: request-reply built into the protocol (`NATS.request()`). We build reply on top of `meta.reply_id` + dedup in the consumer. NATS would collapse ~200 lines of reply routing into one call.
- MQTT: retained messages. The "current directive" for an agent is queryable as "last message on `bifrost/directive/claude`." Our directives ride the boot block, manually assembled.
- Erlang: selective receive. An agent can say "give me the first handoff message, ignore steers and traces." Our inbox returns FIFO; filtering happens in the consumer.

**THE IMPORT:** **NATS-style subjects for lane routing.** Our lane system (work, sig) uses separate stream keys. NATS subjects (`bifrost.lane.work.claude`) would make lane routing a subscription pattern rather than a stream-key switch. The hierarchical namespace is the value, not the NATS server — we could adopt subject naming without changing the transport.

**THE ANTI-IMPORT:** **Kafka.** Distributed log with ZooKeeper/KRaft, partition rebalancing, and operational complexity for a single-node system. Redis Streams are simpler and sufficient.

**STATUS:** LIVE. 61KB file — one of the largest in the repo. Stable. The bus has survived kill drills, crash-redelivery storms, and the T045 lane cutover.

---

### 10. BifrostAPI (bifrost_api.py)

**WHAT IT DOES:** One agent-facing door to the bus. `send()`, `inbox()`, `wake_block()`, `nudge()`, `steer()`. Wraps the bus + control/nudge/wake so an agent needs one import. The T045 lane mode (`_wake_block_lane`, `consume_lane_enabled`, `work_drain`) watches work/sig lanes instead of legacy inbox/bc.

**CONNECTED TO:**
- Reads from: `bus.py` (via `wait()`, `inbox()`), `control.py` (pause/halt), `nudge.py`
- Written to by: runners (deepseek, kimi, sol), UI, any agent
- Lane routing: `packet_spec.py` (stream key derivation), `bifrost_wake.py` (wake watcher)

**COMPARABLE SYSTEMS:**
1. **gRPC bidirectional streaming** — persistent connection with request/response + streaming. Our API is pull-based (poll the bus); gRPC would push messages to the agent over a persistent connection.
2. **RabbitMQ consumer** — bind to exchange, receive via callback. Our `inbox()` is a polling model; RabbitMQ pushes to a callback.
3. **Actor framework (Akka, Orleans)** — each agent is an actor with a mailbox. Our BifrostAPI is the mailbox interface. Akka's supervision hierarchy and location transparency are more advanced.

**THE DELTA:**
- gRPC: persistent connection means zero polling latency. Our wake watcher polls at 1ms intervals (the hot-spin we just fixed). gRPC would eliminate the polling entirely.
- Akka: location transparency. An agent's address is logical; the runtime routes to wherever the actor lives. Our agents are tied to their runner process.

**THE IMPORT:** UNVERIFIED. The wake watcher (fixed tonight, 20%→0% CPU) removed the biggest pain point. The remaining gap is the polling model itself — but a push model requires persistent connections, which Redis Streams don't natively support. Redis Pub/Sub (the `bell` channel?) may bridge this.

**THE ANTI-IMPORT:** **Akka/Orleans.** Actor frameworks are a platform commitment (JVM/.NET, clustering, persistence). Our Python + Redis + SQLite stack is lighter and sufficient.

**STATUS:** LIVE. 28KB. Survived the wake hot-spin fix, the T045 lane cutover, and the reply-path dedup.

---

### 11. Packet Spec (packet_spec.py)

**WHAT IT DOES:** Packet format, lane key derivation, fragment reassembly, integrity validation. Every message on the bus is a `Packet` with `frm`, `to`, `kind`, `ts`, `content`, `meta`. `lane_stream_key(ns, lane, to)` derives the Redis stream key for a given lane.

**CONNECTED TO:**
- Used by: `bus.py` (packet construction), `bifrost_api.py` (lane key derivation), `mailbox.py` (dedup by sha), `router.py` (shadow routing)
- Integrity: `integrity_enabled()` guard, `validate_packet()` — currently kill-switched OFF (integrity_enabled returns False by default)

**COMPARABLE SYSTEMS:**
1. **Protocol Buffers / Avro** — schema-driven serialization with versioning. Our packets are Python dicts serialized as JSON — no schema enforcement, no versioning, no backward compatibility.
2. **Envelope pattern (Enterprise Integration Patterns)** — message = header + body. Our packet IS an envelope (meta = header, content = body). EIP's "message translator" and "content enricher" patterns would apply to our shadow routing.
3. **JWT** — signed tokens with claims. Our packets are unsigned — any agent can forge a message from any other agent.

**THE DELTA:**
- Protobuf: schema, versioning, compact binary encoding. Our JSON packets are human-readable but unversioned — changing the packet format breaks all consumers.
- JWT: cryptographic sender verification. We have no sender authentication — `frm` is a self-claimed string.

**THE IMPORT:** **Re-enable integrity validation.** `integrity_enabled()` is OFF. The integrity validator exists but is kill-switched. Turning it ON (with a LOUD log line on failure, not a gate) would catch malformed packets without breaking the bus. This is a one-line change with an existing module.

**THE ANTI-IMPORT:** **Protobuf/Avro.** Schema-driven serialization adds a build step (compile .proto → Python), a dependency (protoc), and a migration burden for every format change. JSON is slower but zero-friction for a single-node system.

**STATUS:** LIVE. 31KB. Integrity kill-switched OFF. Lane key derivation is load-bearing for T045.

---

### 12. Wake Seat (wake_seat.py)

**WHAT IT DOES:** Detect-only wake watcher that blocks on the bus and alerts when mail arrives. Does NOT consume — leaves messages for the real consumer (T017). Fixed tonight: the lane watcher was hot-spinning because `_lane_since` was never seeded when wake-worthy mail was pending.

**CONNECTED TO:**
- Reads from: `bifrost_api.py` (wake_block / _wake_block_lane), `bus.py` (wait with since=)
- Used by: `bifrost_wake.py` (the wake CLI command), `bifrost_standby` (standby mode)
- Pins: `test_wake_detect.py`, `test_wake_pending_spin.py`, `test_wake_seat.py`

**COMPARABLE SYSTEMS:**
1. **Linux epoll / kqueue** — event notification when a file descriptor becomes readable. Our wake watcher polls Redis; epoll would push a notification on new stream entries.
2. **Redis keyspace notifications** — pub/sub event when a key is modified. `notify-keyspace-events` could push "new message on inbox" without polling.
3. **inotify** — filesystem event notification. If messages were files, inotify would wake on new files without polling.

**THE DELTA:**
- epoll/kqueue: zero CPU while waiting, notification in microseconds. Our wake watcher blocks on `XREAD` with a timeout — the blocking IS the epoll equivalent, but the polling loop (fixed tonight) was spinning instead of blocking.
- Redis keyspace notifications: push-based wake. Instead of "block on XREAD until timeout," subscribe to `__keyspace@0__:bifrost:inbox:claude` and wake on `xadd` events. This eliminates the timeout entirely.

**THE IMPORT:** **Redis keyspace notifications for wake.** The wake watcher currently blocks on XREAD with a 1-5s timeout. Subscribing to keyspace notifications would turn this into a push model: the watcher subscribes, blocks on the pub/sub connection, and wakes INSTANTLY when a message lands. No polling, no timeout, no CPU burn. Requires `notify-keyspace-events` enabled on Redis — a config change, not a code change.

**THE ANTI-IMPORT:** **inotify.** Tying wake to the filesystem would couple the comm layer to a specific persistence backend. The bus is Redis; the wake should stay in Redis.

**STATUS:** LIVE. Fixed tonight (hot-spin → 0% CPU). Pins green. Lane-aware via `_wake_block_lane`.

---

### 13. Launcher (launcher.py)

**WHAT IT DOES:** Process launcher for runners, daemons, and drill scenarios. Spawns `bifrost_runner_*.py` as subprocesses with supervision. `launch_runner(agent, ...)`, `launch_daemon(...)`, `kill_runner(agent)`. Powers the killwindow crash-safety drills.

**CONNECTED TO:**
- Spawns: `scripts/bifrost_runner_deepseek.py`, `bifrost_runner_kimi.py`, `bifrost_runner_sol.py`, `bifrost_wake.py`, `bifrost_ui.py`
- Uses: `runner_lock.py` (consumer seat fencing), `daemon_state.py` (supervisor state), `liveness.py` (heartbeat)
- Drills: `test_killwindow_drill.py` (crash recovery tests)

**COMPARABLE SYSTEMS:**
1. **systemd** — service manager with supervision, restart policies, dependency ordering. Our launcher is a Python script spawning subprocesses; systemd would handle crash restart, logging, and resource limits at the OS level.
2. **Erlang supervision trees** — hierarchical process supervision with restart strategies (one-for-one, one-for-all). Our launcher has ad-hoc restart; Erlang supervisors have defined strategies and escalation.
3. **Kubernetes controllers** — reconcile loop that ensures desired state matches actual state. Our launcher spawns once; a controller would continuously reconcile (if runner died, restart it).
4. **supervisord** — Python process manager. The closest analog — XML config, auto-restart, log rotation. Our launcher is a lighter, code-configured version of supervisord.

**THE DELTA:**
- systemd: OS-level supervision, journald logging, resource limits, socket activation. Our launcher has none of these — if the launcher process dies, orphaned runners keep running.
- Erlang supervisors: restart strategies. Our launcher has no strategy — if a runner dies, it stays dead unless manually restarted. The autopilot (`autopilot_a1.py`) adds basic crash-backoff but not a general supervision hierarchy.
- Kubernetes: desired-state reconciliation. Our launcher is imperative (launch this, kill that); Kubernetes is declarative (I want 1 runner, make it so).

**THE IMPORT:** **Reconcile loop for runner liveness.** A simple loop: "for each agent that should be running, check if its process is alive; if not, restart with backoff." This is what the autopilot partially does. Making it a general launcher feature (not just autopilot) would make runner supervision declarative and crash-resistant. ~50 lines.

**THE ANTI-IMPORT:** **systemd unit files.** Requiring OS-level service configuration for every agent adds operational friction. Our Python launcher is self-contained and cross-platform. systemd is the right answer for production deployment but wrong for development — keep the Python launcher and add a systemd unit file as optional.

**STATUS:** LIVE. 39KB. Autopilot has basic crash-backoff. No general supervision hierarchy. Killwindow drills exercise the crash paths.

---

### 14. Runner Lock (runner_lock.py)

**WHAT IT DOES:** Consumer seat fencing for Redis Streams. `claim_consumer(agent, token)` — claims the consumer seat with a generation counter. Prevents two processes from consuming the same agent's inbox (the RB-21 fix). `holder()` returns current seat info.

**CONNECTED TO:**
- Used by: `bifrost_api.py` (inbox consume path), `launcher.py` (pre-launch seat check), `bus.py` (guarded cursor advance)
- Fencing: generation-based — if a successor claims the seat with a higher generation, the old holder's writes are rejected

**COMPARABLE SYSTEMS:**
1. **Chubby / ZooKeeper ephemeral nodes** — distributed lock with session-based liveness. If the lock holder's session expires, the lock is released. Our consumer seat is a Redis hash with no automatic expiry on process death.
2. **Fencing tokens (Raft, etcd)** — monotonically increasing token that stale writers can't forge. Our `generation` counter IS a fencing token — a successor increments it, and the old holder's generation is too low.
3. **Redlock (Redis distributed lock)** — multi-node lock with quorum. Our seat is single-node Redis; Redlock would survive a Redis failure.

**THE DELTA:**
- ZooKeeper: session liveness with heartbeats. If our process dies, the consumer seat is stuck until manually cleared. ZooKeeper ephemeral nodes auto-release on session timeout.
- Fencing tokens: integrated with the storage layer (the token is checked on every write). Our fencing token IS checked (`generation` in `commit_status_out`) but only on explicit `advance=True` — not on every store write.

**THE IMPORT:** **Ephemeral consumer seats with TTL.** The consumer seat hash should have a Redis TTL that auto-expires. The runner refreshes it on heartbeat. If the runner dies, the seat auto-releases after TTL. This is simpler than ZooKeeper sessions and uses existing Redis TTL infrastructure.

**THE ANTI-IMPORT:** **Redlock.** Multi-node distributed locking for a single-node Redis instance. Over-engineered. Our single-node fencing token is correct and sufficient.

**STATUS:** LIVE. 19KB. Generation-based fencing. No auto-expiry on process death — seats must be manually cleared (the `doctor` verb does this).

---

### 15. Mailbox (mailbox.py)

**WHAT IT DOES:** Deduplication store for bus messages. Every message's SHA is stored in a Redis zset; `is_new(sha)` checks if it's been seen. Bounded by capacity — evicts oldest (lowest score) when full. Used by the lane consumer to filter twin deliveries (dual-write copies).

**CONNECTED TO:**
- Written to by: lane consumer (`work_drain` dedup path), legacy consumer
- Read by: lane consumer (is_new check before delivering)
- The S0-gamma wake dedup: 6,202,600 twins deduped in 3.97h (the hot-spin incident)

**COMPARABLE SYSTEMS:**
1. **Bloom filters** — probabilistic "have I seen this?" with configurable false-positive rate. Our mailbox is exact (Redis zset of SHAs); a Bloom filter would use constant memory regardless of message count.
2. **Kafka idempotent producers** — the producer assigns a sequence number; the broker deduplicates. Our dedup is consumer-side (the mailbox checks SHAs). Kafka's is producer-side.
3. **Redis SET with TTL** — simpler than zset: `SADD seen:<window> <sha>`, `EXPIRE seen:<window> 3600`. Our zset with score-based eviction is more complex than needed; a SET with hourly rotation would be simpler.

**THE DELTA:**
- Bloom filter: constant memory, configurable false-positive rate. At 6.2M messages in 4 hours, a Bloom filter with 0.1% FP rate would use ~10MB. Our zset grows unboundedly until eviction.
- Redis SET: simpler eviction model (TTL per key vs zset score-based). SET members auto-expire; zset members must be manually evicted.

**THE IMPORT:** **Redis SET with TTL for dedup, plus a Bloom filter for the cold path.** Hot dedup (last hour): SET with 1h TTL. Cold dedup (up to 24h): Bloom filter. This reduces Redis memory while maintaining exact dedup for recent messages and probabilistic dedup for old ones. The current zset is correct but memory-inefficient.

**THE ANTI-IMPORT:** **Kafka idempotent producers.** Requires broker-side coordination. Our consumer-side dedup is simpler and works with any transport.

**STATUS:** LIVE. 17KB. Zset-based dedup. Processed 6.2M twins in 4h during the hot-spin incident. Memory usage proportional to message rate × retention window.

---

### 16. Liveness (liveness.py)

**WHAT IT DOES:** Heartbeat-based agent presence. `WorkLive` tracks per-agent phase, turn count, and heartbeat timestamp. Written to Redis with TTL. The `doctor` verb reads presence to determine which agents are alive.

**CONNECTED TO:**
- Written to by: runners (deepseek, kimi, sol — heartbeat thread), `bifrost_ui.py`, `agent_cli.py` (boot)
- Read by: `doctor.py` (fleet status), `autopilot_a1.py` (crash detection), UI (dashboard)

**COMPARABLE SYSTEMS:**
1. **Redis TTL-based presence** — SET with TTL, refreshed on heartbeat. Exactly what we do. The standard pattern.
2. **Consul health checks** — agent reports health; Consul tracks liveness. Would replace our custom presence with a standard health-check protocol.
3. **Kubernetes liveness probes** — container runtime checks process health. OS-level; our presence is application-level.

**THE DELTA:**
- Consul: standard HTTP health check endpoint. Our presence is Redis keys with TTL — simpler but not queryable via HTTP.

**THE IMPORT:** **Already correct.** Redis TTL-based presence is the standard pattern. No change needed. The `doctor` verb already reads and renders it well.

**THE ANTI-IMPORT:** **Consul.** Adding a service mesh for a single-node system. Redis TTL is simpler and we already have Redis.

**STATUS:** LIVE. 11KB. Stable. Powers the fleet dashboard and autopilot.

---

### 17. Locks (locks.py)

**WHAT IT DOES:** Advisory file locks for concurrent editing. `lock(path, agent, ...)` / `unlock(path, agent)`. Used by the guarded write door to prevent two agents editing the same file.

**CONNECTED TO:**
- Used by: `agent_cli.py` (guarded write/edit_file), `mirror.py` (pre-commit hook)
- Stored in: Redis (primary) with FileStore fallback
- The pre-commit hook: verifies AKASHIC_AGENT_ID owns the lock before allowing commit

**COMPARABLE SYSTEMS:**
1. **flock / fcntl** — OS-level file locking. Our locks are Redis-based advisory locks; OS locks would work across any process on the same machine but not across network.
2. **Chubby / ZooKeeper** — distributed lock service. Our Redis locks are single-node; ZooKeeper would survive Redis failure.
3. **Git LFS locks** — lock API for large files. Same advisory lock pattern: claim lock, verify ownership, release.

**THE DELTA:**
- OS locks: automatic release on process death. Our locks persist until manually released or TTL-expired.
- ZooKeeper: session-based liveness, ephemeral nodes. If the lock holder's session expires, the lock is released.

**THE IMPORT:** **TTL on locks with automatic refresh.** A lock should have a TTL (e.g., 5 minutes) and the holder should refresh it on heartbeat. If the holder dies, the lock auto-releases. Currently locks persist until manually `unlock`ed — a crashed editor leaves a permanent lock.

**THE ANTI-IMPORT:** **ZooKeeper.** Adding a ZooKeeper ensemble for lock management in a single-node system.

**STATUS:** LIVE. 10KB. Redis-based advisory locks. No auto-release on crash.

---

### REMAINING COMM MODULES (inventory only — not deep-dived)

- **control.py** (15KB) — pause/halt/resume for agents. Signal-based flow control.
- **nudge.py** (6KB) — hard interrupts (barge-in) and soft steers.
- **promoter.py** (17KB) — promotes salient bus messages to the durable ledger.
- **doctor.py** (44KB) — fleet health dashboard. Reads presence, locks, lane depths.
- **dispatcher.py** (5KB) — pub/sub doorbell for wake. `bell_channel` pattern.
- **storm_detect.py** (5KB) — redelivery storm detection. Used during the 562-echo incident.
- **incarnation.py** (11KB) — agent incarnation cards (boot identity, session tracking).
- **flow_trace.py** (10KB) — tool-call trace for bus observability.
- **expectations.py** (12KB) — timeout/expectation tracking for handoff replies.
- **session_state.py** (8KB) — per-session state tracking.
- **turn_metrics.py** (8KB) — per-turn cost/timing estimation.
- **toolbox.py** (67KB) — the ToolBox door (34 verbs, guarded execution).
- **fence_phase.py** (2KB) — fence stage tracking for design rounds.
- **context_hints.py** (7KB) — ephemeral context hints between peers.
- **blobs.py** (3KB) — large payload storage (write_file bodies).
- **pager.py** (3KB) — paged reading for large inboxes.
- **timescale.py** (1KB) — time constants.
- **lane_depths.py** (3KB) — lane queue depth tracking.
- **runner_lib.py** (2KB) — shared runner utilities.
- **session_exit.py** (5KB) — clean session teardown.
- **triage_park.py** (5KB) — parked message triage.
- **daemon_state.py** (8KB) — daemon supervisor state.
- **engine_vitals.py** (4KB) — engine health metrics.
- **cursor_admin.py** (5KB) — cursor inspection and repair.
- **interject.py** (6KB) — intent detection for interjected messages (halt vs steer vs ask).
- **assertions.py** (5KB) — pre-flight assertion runner for bus messages.
- **router.py** (7KB) — shadow router for lane-aware delivery.
