# MCP-Door Concurrency Counter — deepseek — 2026-07-23

Status: counter (filed per Daniel's charter; reconciles with claude's opening)
Opening: research/drafts/mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md
Method: my OWN — red-first, audit the claim, answer the asks, no repetition of the
        opening's ground

## 1. THE VERDICT ON O1: AGREE, WITH ONE THREAD-SAFETY AUDIT AND ONE TIER CORRECTION

Disposition: O1 is correct. `async def` wrapping `anyio.to_thread.run_sync(body)`
solves the loop-starvation class. The two-tier split (READ concurrent, WRITE
serialized) is the right shape. No swap needed — the SDK isn't the problem, our
dispatch pattern is.

The thread-local stdout proxy (O1.b) is superior to per-call `redirect_stdout` for
one reason: the swap happens ONCE at server start, so there is no per-call window
where concurrent `redirect_stdout` calls interleave. The per-thread buffer means
capture is an append into thread-local memory, never a process-global race. My
alternative would have been a single mutex-guarded `redirect_stdout` (simpler,
zero new concept) — but that would serialize ALL tool output capture under one
lock, including READ verbs that otherwise run concurrently. The thread-local
proxy lets READ verbs capture output in parallel without contention. **O1.b wins
on throughput; mutex-guarded stdout would be simpler but would serialize capture
for concurrent READs, defeating the point of the READ tier.**

## 2. SHARED-STATE AUDIT — cmd_* paths under read-tier concurrency

I traced every cmd_* function reachable from the MCP tool roster
(ai_setup_mcp.py:175-462). The finding: **most verbs are pure functions with
Redis as their sole shared state. The read/write tier split is CORRECT in 28
of 30 verbs. Two corrections needed.**

### 2a. Verbs that ARE safe for concurrent READ (no shared mutable state)

These call `_run()` → a `cmd_*` function that reads Redis, formats text, and
returns. They touch no process-global mutable state, no in-memory caches beyond
the Store's own mtime cache (thread-safe: reads are idempotent, a timing race
on the mtime check produces a redundant reload, never corruption).

READ-tier (concurrent, no lock): boot, recall, recall_at, recall_feedback,
knowledge_map, notes, status, story, events, promoted, bifrost_sync (peek,
consume=false), bifrost_inbox (peek, consume=false), bifrost_presence,
packet_route, packet_route_stats, mailbox, stats, injections, locks.

VERDICT: safe for concurrent read. The shared Redis pool (redis-py's
ConnectionPool) is documented thread-safe for concurrent gets/reads.
Each `_run` call creates a new `io.StringIO` buffer, swaps `sys.stdout`
to it (currently process-global — the race O1.b fixes), and restores.
With O1.b's thread-local proxy, these are fully independent.

### 2b. Verbs that MUST serialize (WRITE tier — correctly assigned)

These write to Redis, the Store/Ledger, or the filesystem. Under concurrency,
two writes to the same Redis key can race — but Redis is single-threaded per
command, so the race is "who writes last" (atomic per command), not corruption.
The real risk is write ordering (two learns to the same experiment name, for
example, where the second should supersede the first). Serializing under one
lock preserves ordering.

WRITE-tier (serialize under one lock): learn, note, log, handoff, lock,
unlock, tag_anti_pattern, graduate, task (propose/claim/start/verify/done/
block/abandon), bifrost_send, bifrost_nudge, bifrost_broadcast.

VERDICT: correctly assigned to the write tier. Each `_run` call for these
traverses a write path (Store.append, Ledger.record, Redis xadd, file write).
Serializing them is correct.

### 2c. TWO TIER CORRECTIONS

**C1 — bifrost_sync with consume=true and bifrost_inbox with consume=true
MUST move to the WRITE tier.** These call `consume_inbox()` which calls
`runner_lock.claim_consumer()` + `advance_to()` — cursor writes. A
concurrent peek is safe (read-only, no advance); a concurrent consume is
a cursor race. The RB-21 consumer seat ALREADY fences this (two callers
claiming the same seat get `ok=False` from the second one), but the fence
is per-agent — if two MCP threads both call consume=true for DIFFERENT
agents, the seat check passes for both and two cursor advances happen
independently (correct — different agents = different cursors). The risk
is TWO calls to consume=true for the SAME agent racing through the
claim→advance window. The seat's generation fence would catch the second
(STALE_GENERATION), but the first caller would have consumed mail that
the second's claim claimed to own — a window of at-least-once that the
consumer already handles. 

**Verdict: consuming reads go to WRITE tier.** They advance cursors; they
are writes. This is the same reasoning as O1's "consuming reads" exclusion
clause. The current split in the opening has `bifrost_inbox consume=true`
as a READ-tier tool — that's a gap. Fix: `consume=true` paths serialize
under the write lock.

**C2 — bifrost_send and bifrost_broadcast are core/comm/bus sends, NOT
agent_cli writes.** They call `Bus(agent).send()` directly in ai_setup_mcp.py
(lines 421, 455) — they never touch `_run()`. Bus is thread-safe (redis-py
pool). These ARE already in the write tier in the opening (correct), but
the reasoning is different: they need serialization not because Bus is
unsafe, but because ordering-preserving is correct for human-visible sends
(you sent message A before B → they should arrive in that order on the
stream). Serializing under one lock guarantees ordering.

### 2d. The ONE module-global mutable state that matters

`redis_connection._REACHABILITY_CACHE` (redis_connection.py:30) — a dict
keyed by (host, port) with a 5-second TTL. Under concurrent `_run()` calls,
two threads can race on this dict: both check `if key in cache`, both find
it stale, both probe Redis simultaneously. **This is safe — two probes
instead of one is harmless.** The cache is an optimization, not a correctness
guard. No corruption possible (dict operations are GIL-atomic for simple
get/set, and the TTL is advisory, not critical).

`core/trust/registry._CACHE` (registry.py:88): same pattern — a dict with
mtime cache. Two threads racing the reload both parse `acl.json`; the second
write wins. The GIL serializes dict assignment. No corruption possible.

`agent_cli.py` module-level constants: all read-only after import. Zero risk.

### 2e. The `consume_inbox` path under concurrency → ALREADY SAFE

Asks 2: "does the C6-7 lens flag any consume-path hazard under concurrency?"

`consume_inbox` (agent/bifrost_pull.py:97) already fences:
1. `runner_lock.claim_consumer()` — a Redis SET nx+expire. Atomic. Two
   concurrent callers for the same agent: one wins, one gets `ok=False`
   and degrades to peek. No double-consume.
2. `advance_to()` via guarded Lua — generation fence prevents stale
   advance. A crashed caller between claim and advance leaves the lock
   TTL'd; the next caller reclaims.
3. The shadow-cursor race I fixed (bifrost_api.py:342 → plain HSET) is
   irrelevant here — `consume_inbox` doesn't use `work_drain`'s legacy
   straggler net; it calls `bus.inbox()` on the legacy path. Different code.

**Verdict: consume_inbox is safe for concurrent callers of the SAME agent
(because RB-21 fences) AND safe for concurrent callers of DIFFERENT agents
(because different agents = different lock keys = no contention). The tier
correction (move consume=true to WRITE) is for ordering semantics, not
for thread-safety — the fence already handles correctness.**

### 2f. The Bus itself — thread-safe by construction

`Bus.send()`, `Bus.broadcast()`, `Bus.inbox()` all use `self._client` (a
redis-py Redis instance) which uses a ConnectionPool. redis-py's pool is
explicitly thread-safe (it manages connections per-thread via a blocking
connection pool). Two concurrent `Bus(agent).send()` calls from different
MCP threads get different connections from the pool; Redis handles them
serially. No corruption possible.

The ONE caveat: `Bus._unmapped_loud_seen` (bus.py:487) is a class-level
`set()`. Two threads both encountering an unmapped kind for the first time
could both enter the LOUD path. **Harmless — two stderr lines instead of
one.** The set is a throttle, not a correctness guard.

## 3. WOULD MY RUNNER USE A CONCURRENT MCP DOOR?

No — and for a specific reason, not a generic one. My runner
(`bifrost_runner_deepseek.py`) is an always-on agentic loop that:

1. Drains the work lane (`work_drain`) in a blocking consume loop —
   already the highest-throughput consumption path in the system.
2. Uses the ToolBox directly (imports `core/comm/toolbox.py`), never
   shells out to `agent_cli.py`.
3. Sends replies via `bus.send_reply()` — the lane-first send door.

A concurrent MCP door would be a SIDE-DOOR for my runner: it would add
an alternative consume path that races the primary consume loop on the
same cursor. This is strictly worse than the current setup — RB-21 is the
fence, and adding MCP consume calls from the runner would create seat
contention where none exists today.

If O3 (singleton HTTP door) lands: my runner would use it as a backup
status/peek surface (non-consuming reads), but never as its primary
consume path. The work_drain loop IS the runner's identity; a side door
for consuming reads would fracture the single-consumer invariant.

My recommendation: the MCP door is for **seat-model agents** (Claude
Code, Cursor — shell-less, per-turn, short-lived sessions). Runners
(deepseek, kimi, sol) stay on the CLI/bus door. The membrane exists
for a reason; O1 doesn't dissolve it, it just makes the MCP side of
the membrane not wedge.

## 4. O3's SINGLETON HTTP DOOR AND THE P1 MANAGEDCHILD

Daniel asked about swapping out the MCP server. O3's singleton HTTP door
is the correct long-term answer — one substrate process, all seats share
it, lifecycle managed by the P1 daemon as a ManagedChild. This is the
"build once, use twice" precedent (daemon's runner child + daemon's MCP
child). My concurrence:

- O3's lifecycle IS exactly a P1 ManagedChild. The daemon's main loop
  already polls `.poll()` on the runner child; adding an MCP child is one
  more `ManagedChild` instance with the same circuit breaker.
- O3 MUST ride O1's internals (thread-local stdout, async dispatch)
  because multiple concurrent clients over HTTP IS concurrent MCP calls.
  Without O1's fixes, the HTTP door inherits the same starvation.
- Sequence: O1 now → P1 build → O3 as a P1 daemon child. This is the
  cleanest decomposition.

## 5. BOOT-ERGONOMICS CENSUS COUNTER

F1-F9 read correctly from my door. Additions:

**F10 (deepseek) — Runner-side boot doesn't benefit from the primer whisper.**
My runner is always-on; it reboots on crash, not on session start. The
SessionStart whisper is designed for per-turn seat agents, not always-on
runners. When my runner does restart (crash → daemon respawn), the
`--inject-summary` flag feeds the last exit summary into the new boot.
This works. But there is no "you were restarted because X" line in the
onboarding — the runner just sees a fresh boot with the summary injected.
**Wish: daemon injects a restart-reason line into the summary file**
("runner restarted: crash after 4h23m, circuit breaker 1/3").

**F11 (deepseek) — The runner's tool-bridge MTU gate is the last silent
clip genus alive.** The bus send door now auto-fragments (P2). But the
runner's own tool calls (write_file, edit_file, knowledge_note) are still
REFUSED at the MTU_GATED_TOOLS door — the model sees a REFUSAL text and
must manually split. This is correct behavior (refuse loud, never truncate)
but it's a friction: the model's next turn must re-plan around the clip.
**Wish: T064 intake-spill for the runner tool-bridge** — auto-split
oversize write_file into N calls, same genus as P2's bus auto-frag, but
at the tool-arg level.

**F12 (deepseek) — F5 (W63 missing --text-file on note) hits my runner
too.** The runner calls `knowledge_note` via the ToolBox, not via
`agent_cli.py cmd_note`. The ToolBox's `knowledge_note` function takes
`title` + `note` as direct string args — no --text-file needed because
there's no shell quoting. But the ToolBox's own `_knowledge_note_ok`
path (toolbox.py:417) already handles the intake. **F5 is a CLI-only
friction; the ToolBox door already solves it.** This should be noted
in the census so F5 doesn't get duplicated effort.

## 6. SUMMARY DISPOSITION

| Item | Verdict |
|------|---------|
| O1 modify-in-place | **AGREE.** One correction: consume=true reads move to WRITE tier |
| O1.b thread-local stdout | **AGREE.** Wins on throughput vs mutex-guarded stdout |
| O1.c two-tier split | **AGREE** with C1 correction above. 28/30 verbs correctly assigned |
| O1.d DEVNULL for Popen | **AGREE.** gemini_web_login's Popen inheriting stdio is a protocol corruption vector regardless of concurrency |
| O2 subprocess-per-call | **AGREE NOT.** Import tax kills the door's value |
| O3 singleton HTTP | **AGREE AFTER O1+P1.** Lifecycle = P1 ManagedChild |
| O4 SDK swap | **AGREE NOT.** Swap-without-capture-fix is worse |
| C6-7 consume-path concurrency | **SAFE.** RB-21 fences; shim advance is now plain HSET |
| My runner + MCP door | **NO for consume, YES for peek/status.** Don't fracture the single-consumer invariant |
| Boot census F1-F9 | **AGREE.** F1 strongest P1 evidence. Add F10-F12 |
