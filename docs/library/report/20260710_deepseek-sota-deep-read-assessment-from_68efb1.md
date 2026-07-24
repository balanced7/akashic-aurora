---
akashic_id: art_20260710_deepseek-sota-deep-read-assessment-from_68efb1
akashic_sha: 74f58cdd9602
status: draft
type: report
date: 2026-07-10
title: "DeepSeek SOTA deep-read assessment -- from the cached primary materials (verbatim, committed by claude)"
gist: "# DeepSeek SOTA deep-read assessment -- from the cached primary materials (verbatim, committed by claude) Provenance: bus msg 1783740928856-"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:36:13"
updated: "2026-07-10T23:36:13"
---
<!-- GENERATED PROJECTION of art_20260710_deepseek-sota-deep-read-assessment-from_68efb1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek SOTA deep-read assessment -- from the cached primary materials (verbatim, committed by claude)

# DeepSeek SOTA deep-read assessment -- from the cached primary materials (verbatim, committed by claude)

Provenance: bus msg 1783740928856-0, 2026-07-10; runner write-gated. Fenced from claude-sota-reading.

Here is my full assessment. The primary materials are substantially richer than the map's summaries — several verdicts sharpen and one requires a design change.

---

## 1. WHERE THE PRIMARY MATERIALS CHANGE OR SHARPEN THE MAP

**Kleppmann — fencing token is MANDATORY for correctness locks, not optional**

The map classifies runner_lock as a correctness lock (two writers on one cursor corrupts delivery). Kleppmann is explicit: for correctness locks, the fencing token is NOT optional — "if a lock service is used to protect access to a shared resource, it must include fencing tokens." Our current runner_lock has no fencing token. The map says "ADAPT" but Kleppmann's own framing says the current design is INCOMPLETE, not a matter of adaptation. This elevates L1b from a nice-to-have to a requirement. The map's verdict should read: **ADOPT the fencing token as mandatory for the cursor-write path; the unfenced state is the E1 vulnerability in the taxonomy.**

**Kleppmann — the token is checked AT THE RESOURCE, not at the lock**

The map conflates "token issued at acquisition" with "token validated." Kleppmann's central point is that the resource SERVER (our Redis, holding the cursor) must reject writes with stale tokens. This means the cursor advance in RB-26 cannot be a blind `hset` — it must be a compare-and-set operation: "write cursor to (inbox=X, bc=Y) ONLY IF generation >= last_seen_generation, else refuse." The simplest implementation is a Lua script. Without this, the token is decorative — an expired holder can still write.

**Kleppmann — GC pauses break TTL-based locks even with heartbeat**

The map assumes the heartbeat thread prevents lock expiry. Kleppmann's GC-pause scenario: a stop-the-world pause longer than LOCK_TTL (20s) means the heartbeat thread also stops. Python's GIL makes a true multi-second stop unlikely but not impossible (disk I/O in a destructor, memory pressure triggering swap, OS scheduler starvation). The fencing token protects against this case; the heartbeat does not. This sharpens L1b's value: it defends against the class of failures where the heartbeat ALSO failed.

**Kafka — batch granularity is the right unit, not per-message**

The Kafka offset-commit pattern commits AFTER processing, but it commits at the granularity of a CONSUMER POLL RESULT — the equivalent of our batch. Our RB-26 design advances per-message within a batch. This is CORRECT (surviving the mid-batch crash case) but creates an edge: after RB-26, the cursor advances for messages 1..K but NOT for messages K+1..N if message K+1 crashes the runner. On restart, K+1..N are redelivered. This is at-least-once — correct. But Kafka's model also warns that the offset commit itself can fail. If the cursor-write Redis call fails after processing message K, the cursor doesn't advance. On restart, all messages K+1..N are redelivered AND message K is also redelivered (cursor still at old position). This creates double-processing of message K, which our ack-idempotency check catches for handoffs but NOT for chat/reply kinds. **Build-spec implication: the ack-idempotency check should extend to ALL answerable kinds, not just handoffs.** A simple `reply_to:<msg_id>` sentinel in Redis (TTL = 1 hour) prevents duplicate replies to chat/request/nudge too.

**Candea-Fox — graceful shutdown is the WRONG path**

Our launcher currently does: SIGTERM → wait 3s → SIGKILL → wait 2s. Candea-Fox would say: just kill. The paper's first design rule is "no graceful shutdown paths" — every shutdown is a crash, so the recovery path is ALWAYS exercised. Building a graceful path means you have two shutdown codepaths, and the one that gets tested less (graceful) is the one with bugs. **Build-spec implication: the launcher's kill path should be a single SIGKILL. The runner's `finally` block already handles cleanup — that IS the crash-only recovery path.** The 3-second graceful window adds complexity and hides bugs in the crash path.

**Candea-Fox — lease expiry, not force-clear**

The paper's "Lease-Based Resource Management" rule: leases auto-expire; other components reclaim expired resources without explicit coordination. Our `runner_lock.clear_if_pid(dead_pid)` is explicit coordination — it bypasses the lease TTL. Candea-Fox would say: wait for LOCK_TTL (20s) to expire naturally. The `clear_if_pid` is a performance optimization (don't make the human wait 20s for a relaunch) but it's a correctness risk — it can free a lock that a still-running-but-temporarily-silent holder owns. **Build-spec implication: `clear_if_pid` should verify the pid is genuinely dead (OS-level check) before force-clearing, not just match the stored pid.** The stored pid could be stale; the OS is authoritative.

**FDB — the CHECK phase matters more than the injection phase**

The map focuses on BUGGIFY (injection). But FDB's real insight is the three CHECK phases: reference implementation comparison, operation log replay, invariant checking. Our 5-window kill harness currently only has invariant checking (message delivered, ack correct). **Missing: a reference-implementation comparison.** A simple Python dict fake of the bus+cursor that replays the same message sequence and asserts the real cursor matches. Without this, our harness can pass while the cursor is subtly wrong (e.g., one ID off, wrong stream). The reference model catches this.

**ShardStore — differential testing beats property testing for data stores**

The map merges ShardStore into "Hypothesis stateful testing." But ShardStore's actual approach is DIFFERENTIAL: a reference model (same interface, simpler implementation) tested against the real one via random operation sequences. This is stronger than property-based invariants because it catches ANY divergence, not just the invariants you remembered to write. For our Store: a `DictStore` (pure Python dict backing) tested differentially against FileStore and RedisStore via Hypothesis rule sequences catches missing `srem` bugs, CAS edge cases, and key-eviction inconsistencies — things we'd never write invariants for because we haven't thought of them.

**Regehr — structure-diversity, not just fencing**

The map treats "fenced" (analysts don't communicate) as the gold standard. Regehr's argument — that compiler bugs are independent because GCC and LLVM have DIFFERENT INTERNAL STRUCTURES (different IRs, different optimizer algorithms) — implies something different for our dual passes. Two analysts doing the SAME METHOD (code-read → classify → design) on the SAME evidence will converge on the SAME blind spots because they share the same ANALYSIS STRUCTURE. The Knight-Leveson correlated failures came from shared spec interpretation; our correlated failures would come from shared code-read interpretation. **Methodology implication: vary the ANALYSIS METHOD, not just the analyst.** One pass = code-read (static), the other = live-drill (dynamic). Or one = top-down (start from taxonomy), the other = bottom-up (start from traces/forensics). This is an actual change to how we structure dual passes.

---

## 2. CONCRETE L1 + L1b BUILD-SPEC (as a reviewer who gates the build)

### L1 (RB-26): at-least-once inbox

**Mechanism** (unchanged from blind-converged design):

```
# BEFORE (current, at-most-once):
msgs = bus.wait(advance=True)          # cursor moves for whole batch
for m in msgs:
    _process_one(m)

# AFTER (L1):
msgs = bus.wait(advance=False)         # detect only
for m in msgs:
    _process_one(m)
    bus._advance_cursor_for(m)         # advance ONLY for this message
```

**Commit granularity** (sharpened by Kafka reading):

Each `_advance_cursor_for(m)` writes the cursor hash. After processing message K in a batch of N, the cursor reflects messages 1..K. If message K+1 crashes the runner, messages 1..K are committed and won't redeliver. Messages K+1..N will redeliver (at-least-once). This is correct.

**Duplicate prevention** (sharpened by Kafka reading):

The map's design checks the P6 ack tier only for handoffs. BUT: if the cursor-write fails AFTER processing (Redis hiccup), the cursor doesn't advance. On restart, ALL messages in the batch redeliver, including those already answered. For handoffs: ack-idempotency catches it (already acked = skip). For chat/reply/nudge: NO dedup exists today, so the sender gets duplicate replies.

**Mandatory addition**: a `reply_sent:<msg_id>` sentinel in Redis (TTL = 1 hour, or `REPLY_TIMEOUT_SEC + 60`). Set AFTER `bus.send()` succeeds AND BEFORE `_advance_cursor_for()`. On redelivery, before processing: check the sentinel. If present → skip (reply already sent). This makes ALL answerable kinds effectively-once, not just handoffs.

**Crash between `bus.send()` and sentinel write**: reply was sent but sentinel is absent → on redelivery, duplicate reply. Acceptable: at-least-once for non-handoff kinds; the duplicate is a chat message, not a state corruption.

**Crash between sentinel write and cursor advance**: sentinel exists, cursor didn't move → on restart, message is re-read, sentinel check fires → skip. Correct.

### L1b: Fencing token on the cursor write

**Token issuance** (at runner startup):

`runner_lock.acquire()` already returns a token (`agent:pid:uuid12`). Add a `generation` field: a Redis `INCR bifrost:generation:<agent>` call at acquisition time. The token becomes:

```
token = {"agent": agent, "pid": pid, "instance": uuid, "generation": gen}
```

`generation` is a monotonically increasing integer scoped to this agent. The `INCR` is atomic — no two runners can get the same generation.

**Where checked** (sharpened by Kleppmann: AT THE RESOURCE):

The cursor advance must become a Lua script, not a blind `hset`:

```lua
-- advance_cursor.lua
local cursor_key = KEYS[1]       -- bifrost:cursor:<agent>
local gen_key = KEYS[2]          -- bifrost:cursor:gen:<agent>
local new_gen = tonumber(ARGV[1])
local inbox = ARGV[2]
local bc = ARGV[3]

local current_gen = tonumber(redis.call('HGET', cursor_key, 'generation') or '0')
if new_gen < current_gen then
    return {err = "STALE_GENERATION"}
end
redis.call('HSET', cursor_key, 'inbox', inbox, 'bc', bc, 'generation', new_gen)
return {ok = true}
```

**Monotonicity source**: Redis `INCR` on a dedicated key. The generation is stored in the cursor hash alongside inbox/bc so the Lua script can read it atomically.

**What happens on refusal**: `STALE_GENERATION` → the runner logs "cursor advance refused (stale generation X < current Y)" and **immediately stands down** (the other runner is the authority now). No retry, no fallback — the stale runner must exit.

**E1 window closure**: Before L1b, if runner A's lock TTL expires and runner B acquires the lock, both A and B can write to the cursor. After L1b: A has generation N, B has generation N+1. If A tries to advance the cursor after B has already done so, the Lua script sees generation N < N+1 and refuses. No corruption.

**The remaining unprotected window**: between runner A's cursor advance (generation N accepted) and runner A detecting lock loss on next heartbeat. In this window, A can still write a stale cursor position. But this window is bounded by the heartbeat interval (5s). The fencing token shrinks the E1 window from "until lock TTL expiry" to "until next heartbeat check." For a 20s TTL with 5s heartbeat, that's a 4x improvement.

---

## 3. WHAT CANDEA-FOX CHANGES ABOUT THE LAUNCHER RESTART PATH

**Kill path: single SIGKILL, no graceful window.**

Remove the 3s graceful SIGTERM → 2s SIGKILL sequence. Replace with: `handle.kill()` immediately. The runner's `finally` block IS the crash-only cleanup path (release lock, stop heartbeat). Testing this path on every restart is the Candea-Fox principle — the graceful path hides bugs in the crash path because the graceful path exercises different code.

**Restart: recovery IS initialization.**

After a crash, the launcher should NOT check exit code classification before restarting (current behavior: classify exit → decide whether to auto-restart). Instead: always restart (if `auto_restart` is set). The runner's OWN initialization IS its recovery path (re-read cursor, re-onboard, resume polling). The launcher doesn't need to know WHY the runner died — it just needs to restart it. Exit classification becomes a DIAGNOSTIC (logged for the human), not a GATE on restart.

**Lease: trust the TTL, not the PID check.**

`clear_if_pid` should validate against the OS, not just the stored PID: `os.kill(pid, 0)` (or `psutil.pid_exists(pid)`) before force-clearing. If the OS says the process is alive, do NOT clear — wait for TTL. This is the Candea-Fox lease discipline: "if a component crashes, leases automatically expire."

**State externalization audit**: The runner holds exactly ONE piece of non-externalized state between operations: whether it's currently processing a message. Everything else (cursor position, lock token, presence, worklive) is in Redis. The in-flight message is the only volatile state, and RB-26's at-least-once redelivery handles its loss. This is good crash-only design already.

---

## 4. WHAT FDB IMPLIES FOR OUR 5-WINDOW KILL HARNESS

**What is portable:**

**(a) Seeded determinism at the bus layer.** Inject a `FakeBus` that replaces Redis with a Python dict, uses a seeded PRNG for message IDs, and advances a simulated clock. The runner code above the bus is unchanged — only the transport is swapped. This makes crash-point injection REPRODUCIBLE: same seed → same message sequence → same crash point → same outcome.

**(b) BUGGIFY-style timeout shrinking.** Add `AKASHIC_TIMEOUT_MULTIPLIER` env: when set to 0.01, every timeout (REPLY_TIMEOUT_SEC, LOCK_TTL, WORKLIVE_TTL) shrinks proportionally. This makes the harness fast (a 600s timeout becomes 6s) AND exercises timeout paths that are normally unreachable in testing.

**(c) Reference-implementation CHECK phase.** The harness should maintain a `ReferenceBus` — a pure-Python dict that mirrors every operation (send, deliver, reply, ack, cursor advance) using the same semantics but zero I/O. After the crash+restart sequence, compare the real bus state against the reference model. This catches cursor-off-by-one, missed delivery, and double-delivery bugs that invariant-only checks miss.

**(d) Workload phases.** FDB's SETUP → EXECUTION → CHECK → METRICS structure maps directly:
- SETUP: launch runner, seed bus with N messages
- EXECUTION: let runner process K messages, inject crash at window W
- CHECK: verify invariants + compare against reference model
- METRICS: record pass/fail + seed for reproducibility

**What is NOT portable:**

**(a) Single-threaded cooperative multitasking.** The runner has real OS threads (heartbeat daemon, worker thread, main loop). We cannot make their interleaving deterministic. The FakeBus makes the TRANSPORT deterministic; the threading stays non-deterministic but its effects are bounded (heartbeat only touches presence/lock; worker thread only touches the model response).

**(b) Full-system simulation.** FDB simulates the ENTIRE cluster in one process. We're testing ONE runner against a fake bus. The Redis layer between launcher and runner is real (or fake). This is appropriate — we're testing the runner's crash behavior, not Redis's.

**(c) "One trillion CPU-hours."** We get maybe 100 runs × 5 windows × 3 seeds = 1500 crash scenarios. That's the right scale.

**Refined harness design:**

```
for window in [W1..W5]:
    for seed in [0..N]:
        bus = FakeBus(seed=seed)
        reference = ReferenceBus(seed=seed)
        runner = launch_runner(bus=bus, timeout_multiplier=0.01)
        bus.deliver(N_messages)
        let_runner_process(K_messages)
        inject_kill_at(window)          # via env flag, logical not timing
        runner.wait_for_exit()
        runner2 = launch_runner(bus=bus)  # successor
        let_runner2_process_remaining()
        assert invariants_hold(bus, reference)
        assert bus.cursor_matches(reference.cursor)
```

---

## 5. WHAT SHARDSTORE + HYPOTHESIS IMPLY FOR THE STORE CONFORMANCE MACHINE

**The ShardStore differential approach is the right one.**

Build a `DictStore(Store)` — a pure-Python dict implementation of the FULL Store interface (get/set/delete/exists/setex/expire/ttl/hset/hget/hgetall/lpush/rpush/lrange/ltrim/llen/sadd/smembers/sismember/srem/zadd/zrange/zscore/zrangebyscore/zcard/zremrangebyrank/zrem/keys/cas). This is ~200 lines. Then:

**Hypothesis RuleBasedStateMachine** generates random operation sequences (e.g., `sadd("k", "a")`, `zadd("z", {"m": 1.0})`, `srem("k", "a")`, `cas("k", None, "v")`, `zrangebyscore("z", 0, 10)`) and applies each operation to BOTH DictStore and FileStore/RedisStore/HybridStore, asserting identical return values and identical readable state.

**Bundles** (Hypothesis feature from the docs) for keys: a bundle of generated key names ensures operations share keys, creating realistic contention. Without bundles, Hypothesis generates independent random keys and nothing conflicts — you never test `srem` on a key that `sadd` populated.

**ShardStore's decomposition for the Store** (three sub-properties, same as their durability split):

1. **Sequential crash-free**: Hypothesis stateful test — random operation sequences, DictStore vs real backends, no crashes. Covers: all return-value correctness, CAS semantics, srem empty-key deletion, zset score ordering.

2. **Sequential crashing**: our existing crash-point sweep — write, crash, recover, verify. Covers: FileStore `_flush` atomicity, HybridStore drift detection, rebuild correctness.

3. **Concurrent crash-free**: Two threads hammering the SAME Store instance with overlapping operations (set+delete on same key, zadd+zrem on same zset, cas+cas). Covers: FileStore lock correctness, HybridStore write-ordering.

**The invariants** (per ShardStore's explicit-property approach):
- `smembers(key) ⊆ sadd()` history — no phantom members
- `zcard(key) == |zrange(key, 0, -1)|`
- After `delete(key)`, `get(key) is None` AND `exists(key) is False`
- `cas(key, expected, value)` succeeds iff current value == expected
- `srem` returns count of actually-removed members
- FileStore: after crash, no partial writes (keys are either fully written or absent)

**This replaces the map's "five day-sized Hypothesis targets" with a SINGLE more powerful one**: the Store conformance machine covers cursor monotonicity (cursor is stored via `hset`), EventIndex trim invariance (trim uses `zcard`/`zrange`/`srem`/`delete`), and supersession (notes use `cas` for the RB-8 sentinel) — because they all exercise the Store. Differential testing catches bugs across the WHOLE interface, not just the invariants you enumerate.

---

## 6. WHAT REGEHR/KNIGHT-LEVESON CHANGES ABOUT DUAL PASSES

**The Knight-Leveson trap applies to our dual passes.**

Our convergence on the T030 root cause (cursor advance before processing) is strong evidence the bug is real — but NOT strong evidence we found ALL bugs. Knight-Leveson showed that correlated failures come from shared SPEC interpretation. Our shared "spec" is the code itself — we both read the same `bifrost_runner_deepseek.py`, we both traced the same `wait(advance=True)` → `_process_one` path. A bug in a code path NEITHER of us traced (e.g., the `nudge` handling branch, the `rate.allow()` path, the `is_halted` freeze loop) would be missed by BOTH analysts because neither traced it.

**Regehr's compiler-testing counter-evidence shows the path to actual independence.**

Compiler bugs are independent because the implementations have DIFFERENT INTERNAL STRUCTURES. Translated to our process:

| Current (shared structure) | Regehr-prescribed (diverse structure) |
|---|---|
| Both do code-read | One does code-read, one does live-drill |
| Both trace the same paths | One traces happy-path, one traces edge-paths only |
| Both reason top-down from taxonomy | One reasons bottom-up from traces/forensics |
| Both share the same evidence | One gets ONLY the forensics, one gets ONLY the code |

**Concrete change for the next dual pass (e.g., L1/L1b design-review):**

Instead of both reading the same code and producing independent diagnoses:
- **Analyst A (code-read)**: reads `bifrost_runner_deepseek.py`, `runner_lock.py`, `bus.py`, designs the fix.
- **Analyst B (live-drill)**: does NOT read the code. Instead, gets a live runner and a script that injects specific failure scenarios (kill at each of the 5 windows, lock-TTL expiry, Redis flap). Reports: "scenario X produced failure Y." Does not see the code.

This is Regehr's structure-diversity: the code-reader finds bugs by REASONING about the code; the live-driller finds bugs by OBSERVING behavior. They converge on different bug classes because their METHODS differ, not just their identities.

**Limitation we must document**: Regehr's compiler independence relied on fundamentally different IRs (Gimple vs LLVM IR) — optimizer bugs at that level cannot correlate because the optimizers operate on different intermediate representations. Our "different methods" (code-read vs live-drill) still operate on the SAME system. The Knight-Leveson case (same spec, different implementations) is closer to our situation. We should expect SOME correlated misses (the spec-interpretation bugs) and SOME independent finds (the implementation-detail bugs). Document this explicitly: **dual-pass convergence is a spec-quality gate; dual-pass DIVERGENCE is an implementation-quality gate.** A bug found by one method but not the other is an implementation bug (Regehr class). A bug found by neither method is a spec bug (Knight-Leveson class).
