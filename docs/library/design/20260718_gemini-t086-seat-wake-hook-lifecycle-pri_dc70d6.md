---
akashic_id: art_20260718_gemini-t086-seat-wake-hook-lifecycle-pri_dc70d6
akashic_sha: 4b40a85a7012
status: draft
type: design
date: 2026-07-18
title: Gemini — T086 Seat/Wake/Hook Lifecycle Prior-Art Sweep (2026-07-18)
gist: "# Gemini — T086 Seat/Wake/Hook Lifecycle Prior-Art Sweep (2026-07-18) **Provenance:** ask_gemini_web mode=api (free tier), claude seat 665aa"
tenant: solo
visibility: fleet
seats: []
category: [migration, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260716_t086-seat-wake-hook-prior-art-deep-dive_b0896c
    rel: cites
created: "2026-07-18T12:49:38"
updated: "2026-07-23T21:42:10"
---
<!-- GENERATED PROJECTION of art_20260718_gemini-t086-seat-wake-hook-lifecycle-pri_dc70d6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Gemini — T086 Seat/Wake/Hook Lifecycle Prior-Art Sweep (2026-07-18)

# Gemini — T086 Seat/Wake/Hook Lifecycle Prior-Art Sweep (2026-07-18)

**Provenance:** ask_gemini_web mode=api (free tier), claude seat 665aaea3, 2026-07-18 ~12:25 EDT.
Web mode returned empty twice (invisible-Chrome session likely needs a one-time
`gemini_web_login` re-auth — flagged separately); API fallback answered. Persisted VERBATIM
below per the full-fidelity rule. Feeds T086 step 3 (production prior art) alongside
deepseek's blind half (research/reviewed/deepseek-seat-priorart-2026-07-16.md — his
liveness-vs-lifecycle thesis) and claude's half.

**Prompt (summary):** our shape (N heterogeneous seats on Redis Streams; wake-on-address,
singleton consumer seats, dead-peer takeover, split-brain fencing, zero-noise wake floor) vs
candidates ZK/etcd, OTP, Kafka consumer groups, K8s Leases, SQS, Temporal/Celery; TTL/heartbeat
ratios; where fencing tokens must be checked; postmortem failure ordering; Redis-native vs
external coordinator.

---

Designing a robust liveness/wake/lifecycle layer for a multi-agent system on Redis Streams is a classic distributed systems challenge, blending concerns of leader election, work distribution, and fault tolerance. Let's break down your questions with concrete mechanisms and numbers.

---

### 1. Which production systems is this shape MOST like?

Your system, aiming for "exactly one live session per agent ID" with crash detection and safe takeover, most closely resembles **Kafka Consumer Group rebalancing** combined with **ZooKeeper/etcd ephemeral nodes and leases**.

Here's an analysis of your candidates:

*   **ZooKeeper/etcd ephemeral nodes + leases + fencing tokens**
    *   **Most Like**: High. Directly provides a robust mechanism for leader election, singleton ownership, and split-brain prevention.
    *   **Mechanism**: **Ephemeral nodes + Watches**. A client creates a unique ephemeral node (e.g., `/agents/<agent_id>/lock`) and holds onto it. If the client crashes or disconnects, the ephemeral node is automatically deleted by the coordinator, triggering watches on other clients.
    *   **Failure mode killed**: **Uncoordinated failover and split-brain**. The ephemeral node guarantees only one owner, and its atomic creation/deletion prevents multiple contenders from believing they are active simultaneously without a clear signal.

*   **Erlang/OTP supervision trees + monitors**
    *   **Most Like**: Low. Primarily designed for fault tolerance *within a single node or tightly coupled cluster*, managing process lifecycles and restarts. It doesn't inherently solve distributed singleton ownership across arbitrary machines without external coordination.
    *   **Mechanism**: **Process linking/monitoring**. A process monitors another, receiving a `'DOWN'` message if the monitored process terminates.
    *   **Failure mode killed**: **Local process crashes and resource leaks**. Ensures local processes are supervised and restarted or cleaned up.

*   **Kafka consumer-group rebalancing (incremental cooperative, generation ids)**
    *   **Most Like**: High. This directly solves the problem of "exactly one consumer per partition" (mapping well to "exactly one consumer per agent inbox") and graceful failover of work.
    *   **Mechanism**: **Group coordinator + Generation IDs + Cooperative Rebalancing**. The Kafka broker (coordinator) tracks active consumer group members. On member join/leave/crash, it orchestrates a rebalance, assigning partitions to new members. **Generation IDs** are a crucial fencing token: a consumer *must* present the current generation ID to commit offsets; commits from old generations are rejected.
    *   **Failure mode killed**: **Stale consumer committing offsets or processing duplicates during rebalance**. Generation IDs provide strong fencing against old consumers interfering with the new assignment.

*   **Kubernetes leader-election Leases + liveness probes**
    *   **Most Like**: High. Kubernetes Leases are an API object backed by etcd, designed for distributed leader election (singleton ownership). Liveness probes detect application health.
    *   **Mechanism**: **Lease API object + etcd atomic Compare-And-Swap (CAS)**. Pods attempt to acquire or renew a Lease object by atomically updating its `holderIdentity` and `leaseTransitions` fields.
    *   **Failure mode killed**: **Multiple leaders trying to perform a singleton action simultaneously**. The atomic CAS operation ensures only one pod can successfully claim/renew the lease at any instant.

*   **SQS visibility timeouts + dead-letter queues**
    *   **Most Like**: Low. SQS provides message delivery guarantees (at-least-once, with visibility timeouts to prevent concurrent processing of the *same message*) but not a system for ensuring a *single active instance per identity*. DLQs handle unprocessable messages.
    *   **Mechanism**: **Visibility Timeout**. A message is temporarily hidden from other consumers for a configurable duration after being received.
    *   **Failure mode killed**: **Multiple consumers concurrently processing the same message before successful deletion.**

*   **Temporal/Celery worker heartbeats + task leases**
    *   **Most Like**: Medium-High. Focuses on ensuring progress and failover of *tasks* or *workflows*, using heartbeats to detect worker failures.
    *   **Mechanism**: **Worker heartbeats + central task queue/workflow engine**. Workers periodically report their liveness to a central system. If heartbeats are missed, the system marks tasks assigned to that worker as failed/stale and re-queues or reassigns them.
    *   **Failure mode killed**: **Tasks getting permanently stuck on a failed worker**. Heartbeats provide the signal for the central system to reassign work.

---

### 2. Lease TTL vs Heartbeat interval ratios in practice

The ratio is critical for balancing failover speed against system stability (false positives).

*   **Heartbeat Interval**: How often a healthy client explicitly reports its liveness.
*   **Lease TTL (or Session Timeout)**: The maximum duration a coordinator waits without a heartbeat before declaring a client dead and expiring its lease.

**General Rule of Thumb**: `Lease TTL = k * Heartbeat Interval`, where `k` is typically **3 to 10**.

*   `k=1` is too aggressive, as a single transient network hiccup or a brief GC pause could cause premature lease expiry and unnecessary failover.
*   A larger `k` provides more buffer for transient issues but increases the time to detect a true failure.

**Typical Numbers & Examples**:

*   **Kafka Consumer Groups**:
    *   `heartbeat.interval.ms`: Default 3,000 ms (3 seconds).
    *   `session.timeout.ms`: Default 10,000 ms (10 seconds).
    *   **Ratio**: ~3.3 (`10s / 3s`). This means a consumer can miss two heartbeats before being considered dead.
*   **Apache ZooKeeper**:
    *   Client `ping` interval (heartbeat): Typically `session_timeout / 3`.
    *   `session_timeout`: Configurable, often 4-30 seconds.
    *   **Example**: If `session_timeout` is 30s, heartbeat is 10s. **Ratio**: 3.
*   **Kubernetes Lease API**:
    *   `leaseDurationSeconds`: Default 15 seconds.
    *   `renewTime` (effective heartbeat): Controllers attempt to renew every `retryPeriodSeconds` (default 2 seconds).
    *   **Ratio**: 7.5 (`15s / 2s`). Allows for multiple missed renewals before expiration.

**Practical Considerations**: Choose `k` based on your network reliability, application pause times (GC, heavy computation), and acceptable failover latency. For "under a minute" failover, a `Lease TTL` of 30-45 seconds (with a 10-15 second heartbeat) is a good starting point.

---

### 3. Fencing: Where must the token be CHECKED?

The Kleppmann fencing token argument states that a *monotonically increasing token* (e.g., generation ID, epoch number) must be issued to a new leader/owner, and **this token MUST be validated by the shared resource on EVERY state-changing operation.**

*   **Core Principle**: It's not enough for the new leader to *have* the token. The *shared resource* itself must atomically check the token *before* applying any write or critical state modification. This ensures that operations from a stale, fenced-off owner are rejected.

*   **Concrete Implementations**:

    1.  **Kafka Consumer Groups**: The Kafka broker (the shared resource for consumer offsets) checks the `generationId` included in every `OffsetCommitRequest`. If the `generationId` from the client does not match the broker's current `generationId` for that consumer group, the commit is rejected. This prevents stale consumers from corrupting offset progress.

    2.  **Distributed Databases / Shared Storage**:
        *   If agents are modifying shared state in a database (e.g., PostgreSQL, Redis), the data schema itself must incorporate the fencing token (e.g., an `epoch` or `fencing_id` column/field).
        *   **For every write operation**: The new leader acquires a higher `fencing_token`. Its writes must include this token. The database operation must be conditional: "update this record *only if* its current `fencing_token` is less than or equal to my new `fencing_token`."
        *   **Redis Example (using Lua scripting for atomicity)**:
            Assume an agent's persistent state is a Redis Hash `agent:<id>` with a `fencing_token` field.
            When a new leader `L_new` takes over for `agent:<id>`, it first increments a shared counter to get a new `fencing_token` (e.g., `INCR agent:<id>:fencing_seq`, or atomically `HINCRBY agent:<id> fencing_token 1`). Let's say `L_new` gets token `124`.
            Any subsequent write from `L_new` to the `agent:<id>`'s state must use this token. A Lua script ensures atomicity:

            ```lua
            -- Script to update a field in an agent's hash, protected by a fencing token.
            -- KEYS[1]: agent_hash_key (e.g., 'agent:my_agent_id')
            -- ARGV[1]: new_fencing_token (e.g., '124')
            -- ARGV[2]: field_to_update (e.g., 'status')
            -- ARGV[3]: new_value (e.g., 'active')

            local current_token = redis.call('HGET', KEYS[1], 'fencing_token')

            -- If there's no fencing token yet, or if the provided token is newer, allow the update.
            -- This handles initial writes and new leader takeovers.
            if not current_token or tonumber(ARGV[1]) >= tonumber(current_token) then
                -- Atomically update the fencing token and the specified field.
                redis.call('HSET', KEYS[1], 'fencing_token', ARGV[1], ARGV[2], ARGV[3])
                return 1 -- Success
            else
                return 0 -- Rejected: Stale fencing token
            end
            ```
            An old leader `L_old` (with token `123`) attempting to write will be rejected because `123` is not `>= 124`. This is where the fence holds.

---

### 4. What breaks first in such systems per postmortems: Standard mitigations

Based on common incidents in distributed systems (Kafka, K8s, ZooKeeper):

1.  **Rebalance Herd Effects / Thundering Herds**:
    *   **What breaks**: A single node failure (or network partition) can cause many remaining nodes to simultaneously attempt to acquire resources or rebalance, overwhelming the coordinator or shared resource. This delays recovery and causes cascades.
    *   **Mitigations**:
        *   **Jitter**: Randomize retry backoffs and heartbeat intervals slightly to spread out activity and prevent synchronized behavior. E.g., `backoff_time = base_time * (2 ^ retries) * (1 + random_jitter)`.
        *   **Cooperative Rebalancing (Kafka-style)**: Instead of a full reset, the group coordinator orchestrates an incremental assignment. Consumers don't all rejoin; they negotiate a split or accept coordinator assignments.
        *   **Sticky Assignment**: During rebalance, prioritize re-assigning an agent's work/stream to the *same* consumer that previously owned it if that consumer is still healthy. This minimizes state transfer.
        *   **Rate Limiting**: The coordinator or the shared resource (Redis) should rate-limit acquisition attempts or rebalance requests.

2.  **Zombie Consumers / Stale Owners (Split-Brain)**:
    *   **What breaks**: A consumer that *appears* dead (lost its lease) but is still alive and tries to perform actions, conflicting with the new, legitimate owner. This leads to data corruption, duplicate processing, and inconsistent state.
    *   **Mitigations**:
        *   **Robust Fencing (as in Q3)**: The most critical mitigation. Every state-changing operation on shared resources *must* validate the fencing token.
        *   **Hard Termination**: If a client is informed it has lost its lease or been fenced (e.g., its lease renewal is rejected with a clear "stale token" error), it *must immediately cease all activity*, preferably shutting down or transitioning to a passive, read-only state.
        *   **Centralized Lease Authority**: The coordinator (or Redis lock) must be the single source of truth for ownership.

3.  **Cursor/Offset Corruption**:
    *   **What breaks**: Incorrectly tracking the "last processed message ID" for an agent's inbox stream. This results in messages being reprocessed (duplicates) or missed.
    *   **Mitigations**:
        *   **Atomic Offset Commits with Fencing**: As in Kafka, `XACK` (or custom offset storage) must be tied to the current fencing token for the agent. If the token doesn't match, the commit is rejected.
        *   **Idempotent Processing**: Design message processing to be idempotent wherever possible, so reprocessing messages has no ill effects.
        *   **Redis Streams Consumer Groups**: These intrinsically handle offset management. `XACK` marks messages as processed. `XPENDING` identifies unacknowledged messages, and `XAUTOCLAIM` allows a new consumer to take over pending messages from a dead one, ensuring progress.

4.  **Wake Storms / Excessive Notifications**:
    *   **What breaks**: If every message or minor state change triggers an expensive wake-up attempt, or if a failure causes all idle agents to poll for work simultaneously, it can overwhelm notification systems or Redis.
    *   **Mitigations**:
        *   **Targeted Wakes**: Use distinct Redis Streams (e.g., `agent:inbox:<id>`) so messages only wake the *specific* target agent.
        *   **Lease-based Acquisition (Lazy)**: Agents don't constantly poll. Instead, they attempt to acquire a lease/ownership for their ID. If successful, they start consuming. If not, they back off with jitter.
        *   **Batching/Debouncing**: If many rapid events occur, aggregate them into a single "wake-up" signal rather than individually.
        *   **Exponential Backoff with Jitter**: For retrying lease acquisition or joining a group.

---

### 5. ONE architecture pattern for "exactly-one live consumer per identity, with crash takeover under a minute, on top of Redis"

**Architecture Pattern**: **Redis-native: Redis Streams Consumer Groups + Redis-based Distributed Lease with Fencing Tokens.**

**Why this combination and not an external coordinator**:

1.  **Leverages Existing Infrastructure**: You're already using Redis Streams as your message bus. Introducing an external coordinator (ZooKeeper, etcd) adds significant operational complexity, another service to manage, monitor, and scale, and an additional dependency. Sticking to Redis simplifies your stack.
2.  **Operational Simplicity & Performance**: Redis is extremely fast and well-understood for atomic operations. Using `SET NX EX` for locks and Lua scripts for atomic compare-and-swap operations for renewals and fencing token updates provides robust distributed coordination with minimal latency.
3.  **Directly Addresses Requirements**:
    *   **Exactly-one live consumer per identity**: Achieved by the Redis-based distributed lease (`SET NX EX`) for agent ownership.
    *   **Crash takeover under a minute**: The `EX <lease_ttl>` on the Redis lock directly controls the maximum time to detect a crash. With a 30-second TTL and 10-second heartbeat, failover can occur within ~30-40 seconds. For message consumption, `XAUTOCLAIM` can instantly re-assign pending messages from the crashed consumer.
    *   **Safe work transfer**: `XAUTOCLAIM` for messages and the fencing token mechanism for state mutations ensure safety.
    *   **Avoid split-brain**: Achieved by the unique client ID in the lock and the explicit fencing token validated via Lua scripts for all critical state changes.

**Concrete Mechanisms**:

1.  **Agent Identity Ownership (Singleton)**:
    *   Each agent instance (`A_1`, `A_2` for `Agent_ID_X`) tries to acquire a lock for its `Agent_ID_X`.
    *   **Lock Acquisition**: `SET agent:lock:<Agent_ID_X> <instance_id> EX <lease_ttl> NX`
        *   `instance_id`: A unique string for the current process (e.g., `hostname:pid:<uuid>`).
        *   `lease_ttl`: E.g., 30 seconds.
        *   `NX`: Ensures the key is only set if it doesn't already exist (atomic acquisition).
    *   **Lock Renewal (Heartbeat)**: The owning agent periodically renews its lease using a Lua script to ensure atomicity:
        ```lua
        -- KEYS[1]: lock_key (e.g., 'agent:lock:Agent_ID_X')
        -- ARGV[1]: my_instance_id
        -- ARGV[2]: new_lease_ttl (e.g., 30)
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('EXPIRE', KEYS[1], ARGV[2])
        else
            return 0 -- Not the owner, or lock expired/taken by another.
        end
        ```
    *   If renewal fails (returns `0`), the agent must assume it's been fenced and gracefully shut down or enter a passive state.

2.  **Fencing Tokens for State Changes**:
    *   When an agent successfully acquires the lock, it must increment its `fencing_token` for its `Agent_ID_X`. This can be stored in a separate Redis Hash for the agent's state:
        `HINCRBY agent:<Agent_ID_X>:state fencing_token 1`
    *   All critical state changes (e.g., writing to a persistent agent state store, interacting with external systems requiring agent identity) *must* include this `fencing_token` and be validated by the shared resource (via a Lua script in Redis, as shown in Q3).

3.  **Message Consumption (Inbox)**:
    *   Each `Agent_ID_X` has its own dedicated Redis Stream: `agent:inbox:<Agent_ID_X>`.
    *   The active agent instance `A_1` for `Agent_ID_X` joins a Redis Streams Consumer Group (e.g., `agent_group`) for `agent:inbox:<Agent_ID_X>`. It uses `XREADGROUP` to consume messages.
    *   When `A_1` processes a message, it `XACK`s it.
    *   **Crash Takeover**: If `A_1` crashes, its `agent:lock:<Agent_ID_X>` expires. Another instance `A_2` acquires the lock and the new `fencing_token`.
    *   `A_2` then uses `XAUTOCLAIM agent:inbox:<Agent_ID_X> agent_group <A_2_consumer_name> <min_idle_time_ms> <count>` to claim any `XPENDING` messages that `A_1` left unacknowledged. A typical `min_idle_time_ms` would be a few seconds, less than the `lease_ttl`.

This Redis-native approach is powerful, streamlined, and provides the necessary primitives for robust, fault-tolerant agent management within your existing technology stack.
