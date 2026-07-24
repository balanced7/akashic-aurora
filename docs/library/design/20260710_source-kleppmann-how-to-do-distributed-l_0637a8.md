---
akashic_id: art_20260710_source-kleppmann-how-to-do-distributed-l_0637a8
akashic_sha: 27d2b3fd5eb3
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Kleppmann, \"How to do distributed locking\" (2016)"
gist: "# SOURCE: Kleppmann, \"How to do distributed locking\" (2016) # URL: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.htm"
tenant: solo
visibility: fleet
seats: []
category: [coordination]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:30:09"
updated: "2026-07-10T23:30:09"
---
<!-- GENERATED PROJECTION of art_20260710_source-kleppmann-how-to-do-distributed-l_0637a8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Kleppmann, "How to do distributed locking" (2016)

# SOURCE: Kleppmann, "How to do distributed locking" (2016)
# URL: https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Lock Purpose Distinction

Kleppmann identifies two fundamentally different use cases:

**Efficiency locks:** Prevent redundant work (duplicate computation, repeated API calls). If the lock fails, consequences are minor -- extra cost or user inconvenience. Single Redis instance with async replication suffices.

**Correctness locks:** Prevent concurrent operations that would corrupt data or create inconsistency. Lock failure causes serious problems: corrupted files, data loss. These demand stronger guarantees.

The critical insight: "if you are using locks merely for efficiency purposes, it is unnecessary to incur the cost and complexity of Redlock."

## The Unsafe Code Pattern

Standard distributed lock usage appears sound but contains a fatal flaw. A client acquires a lock, reads shared storage, modifies it, and writes back. However, the client may experience arbitrary delays -- garbage collection pauses, network buffering, page faults -- after acquiring the lock but before writing. If delays exceed the lock's time-to-live (TTL), the lock expires. A second client acquires it and performs concurrent writes, corrupting the data.

"Stop-the-world" GC pauses have lasted several minutes in production HBase systems. The problem cannot be solved by checking lock expiry before writing: pauses can occur between the final check and the actual write operation.

## Fencing Tokens: The Solution

The fix requires including a monotonically increasing token with every write to protected storage. The lock service increments this number with each acquisition. When client 1 pauses and client 2 acquires the lock with a higher token, the storage service rejects client 1's delayed write (lower token value). This requires the storage server to actively validate tokens and reject writes with non-increasing values.

**Critical limitation of Redlock:** It generates only random unique values, not monotonically increasing tokens. "It does not have any facility for generating fencing tokens." Without this, race conditions remain unsafe regardless of Redlock's other properties.

## Timing Assumptions in Redlock

Redlock's correctness depends entirely on synchronous system model assumptions:
- Bounded network delay: packets always arrive within a known maximum
- Bounded process pauses: hard real-time constraints
- Bounded clock error: accurate clock synchronization

The algorithm fails if these bounds are violated. Redis uses gettimeofday, not monotonic clocks, making it vulnerable to clock jumps. An NTP adjustment or manual clock correction can cause keys to expire faster or slower than intended.

## Failure Scenarios

**Clock jump example:** Client 1 acquires locks on nodes A, B, C. Node C's clock jumps forward, expiring the lock early. Client 2 acquires locks on C, D, E. Both clients now believe they hold the lock.

**GC pause example:** Client 1 sends lock requests to all five nodes. Before responses arrive, stop-the-world GC pauses it. All locks expire. Client 2 acquires all locks. After GC, client 1 receives its successful responses from the kernel buffer (held during pause) and also believes it holds the lock.

Long network delays produce identical effects: packets can be delayed in flight, causing writes to arrive after the lock expires.

## System Model Comparison

Consensus algorithms designed for partially synchronous or asynchronous models with failure detectors (Raft, Viewstamped Replication, Zab, Paxos) ensure safety properties hold WITHOUT timing assumptions. Liveness depends on timeouts, but safety remains guaranteed even when clocks, networks, and processes misbehave.

Redlock violates this principle: "Its safety depends on a lot of timing assumptions."

## Recommendations

**For efficiency locks:** Use single-node Redis with conditional set-if-not-exists. Document clearly that locks are approximate and may occasionally fail.

**For correctness locks:** Do not use Redlock. Instead use proper consensus systems like ZooKeeper (via Curator recipes) or databases with transactional guarantees. Enforce fencing tokens on all resource access under the lock.

The article emphasizes Redis is "an excellent tool if you use it correctly" -- its limitations simply require matching use cases to guarantees.
