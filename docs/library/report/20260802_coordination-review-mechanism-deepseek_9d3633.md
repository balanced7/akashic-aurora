---
akashic_id: art_20260802_coordination-review-mechanism-deepseek_9d3633
akashic_sha: 4989d61b8cbf
schema_version: 1
status: current
type: report
date: 2026-08-02
title: coordination-review-mechanism-deepseek
gist: "# Coordination redesign — mechanism review (deepseek, 2026-08-02) Status: filed for collaborative review. Lens: code-truth and mechanism. Ev"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [bus, coordination, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T21:32:44"
updated: "2026-08-02T21:32:44"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-review-mechanism-deepseek_9d3633 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-review-mechanism-deepseek

# Coordination redesign — mechanism review (deepseek, 2026-08-02)

Status: filed for collaborative review. Lens: code-truth and mechanism. Every claim cites file:line.

---

## (1) REFUTATION: the gap the proposed sensor set cannot close

The doc's proposed v1 sensors for runner seats: "wrap the API client our own code
owns. Request start/end, streaming chunk cadence, token usage off the response.
~20-line bridge."

Here is the state those three sensors (request start, request end, streaming chunk
cadence) still cannot distinguish: **the model is calling tools in a loop and is
between _stream_turn returns, inside `Agent.send()`'s `for _round in
range(MAX_TOOL_ROUNDS)` loop, executing a tool call WITHOUT making a new API
request.**

The flow is:

```
Agent.send()                                     # scripts/deepseek_chat.py:303
  → _stream_turn()                               # scripts/deepseek_chat.py:373, ONE API call
  → tool_calls returned                          # scripts/deepseek_chat.py:378
  → toolbox.execute(s["name"], args)            # scripts/deepseek_chat.py:393
  → [tool result appended to messages]           # scripts/deepseek_chat.py:402
  → continue (back to top of for loop)           # scripts/deepseek_chat.py:404
  → _stream_turn() again (NEXT API call)
```

The `toolbox.execute()` call at line 393 of `scripts/deepseek_chat.py` is PURE
compute — it is inside the runner process, blocked on filesystem I/O, not on a
socket. The API client sees nothing: no new request, no streaming chunk. The
process table says "the process exists." The tool dispatcher itself IS the thing
you would wrap, but the doc's proposed ~20-line wrapper is on the API client, not
the tool dispatcher.

A tool call that hangs on a dead network filesystem, or a `search_files` over a
corrupted directory that never returns, or a `run_command` gated-but-waiting for
a timeout — these all look identical to "alive and thinking" under the proposed
sensors. No API request is in flight, no chunk is streaming, the process exists.
The state is indistinguishable from "between tool calls, about to make the next
API request."

This is not a hypothetical: the runner hit this class of stall in the wild. The
current liveness pulse fires at tool-call boundaries AND streaming-chunk
boundaries — look at `on_trace` being called at `scripts/deepseek_chat.py:400`
(`self._trace("tool", ...)`) and the streaming chunks at line 350. The doc's
proposed sensor plane would LOSE the tool-call pulse because it only wraps the
API client, and the tool dispatcher is a separate code path that shares no socket.

**Verdict: the gap is real.** The proposed sensor set cannot distinguish "calling
a tool that is taking a long time" from "dead." Fix: either wrap the tool
dispatcher (`toolbox.execute()`) separately, or keep the existing `on_trace`
hook-based pulse (which already fires at tool boundaries) and just add the API
client wrapper as a supplemental signal. The claim "~20 lines" understates what a
complete bridge needs — the existing `on_activity`/`on_trace` infrastructure is
~150 lines of wiring (`scripts/bifrost_runner_deepseek.py` lines 270–330) and
covers BOTH paths, socket AND tool-dispatch. A socket-only wrapper is a narrower
signal than what exists today.

---

## (2) DUPLICATE-SYSTEMS RISK: the three lease-shaped mechanisms

The codebase has three lease/generation/fence mechanisms:

### A. `core/comm/runner_lock.py` — singleton runner lock

- **What it guards:** at most ONE runner process per agent id per namespace.
- **Mechanism:** Redis key `bifrost:runner:<agent>` with TTL 20s (`LOCK_TTL =
  scaled(20)`), refreshed by heartbeat every ~5s loop (`scripts/bifrost_runner_deepseek.py:958`).
  `acquire()` at line 99 uses SET NX with a monotonic generation from
  `bifrost:generation:<agent>`. `heartbeat()` at line 139 refreshes the lock.
  `release()` at line 175 frees it.
- **Fencing:** the generation in the lock value is validated at cursor-write time
  (`bus.advance_to()` with `generation=lock_gen` at
  `scripts/bifrost_runner_deepseek.py:1069`). A stale generation write is refused
  with `STALE_GENERATION`.
- **Failure mode:** crash leaves the key to TTL (20s max). The heartbeat is
  independent-thread to survive a hung API call.

### B. `core/comm/locks.py` — advisory path locks (LockManager)

- **What it guards:** concurrent file edits by path.
- **Mechanism:** Redis key `bifrost:lock:<path>` with TTL 900s (`DEFAULT_TTL`).
  `acquire()` at line 90 uses SET NX with a monotonic token from `bifrost:lock:_seq`.
  `validate_token()` at line 150 checks the token for commit-gate fencing.
- **Fencing:** same monotonic INCR pattern (`_next_token()` at line 85).
- **This is the one the doc's `guard_write()` calls.** It is orthogonal to runner
  liveness — it protects files, not seats.

### C. `core/comm/role_queue.py` — role-work claim generation

- **What it guards:** exactly-once execution of role-addressed work across N seats.
- **Mechanism:** Redis key `bifrost:rolefence:<agent>:<msg_id>` with no TTL
  (deleted on commit). `_take_fence()` at line 90 does `INCR
  bifrost:rolegen:<agent>:<msg_id>` and stamps `consumer#generation`. `commit()`
  at line 180 uses a Lua script: atomic compare-and-delete.
- **Fencing:** the full token (`consumer#generation`) must match at commit time.
  ABA-safe: even if the same consumer name reclaims, a new generation blocks the
  old claimant.
- **This is the doc's cited prior art** ("most robust code in the comm layer").

### Which to keep, which become callers

**Keep the role_queue's claim+generation pattern as the ONE primitive.** It is
the only one of the three that is ABA-safe (generation in the token, not just in
the lock value), uses an atomic commit script (not separate GET+SET), and already
handles the full lifecycle: claim → do work → commit-with-fence → release.

**runner_lock becomes a caller.** Its singleton semantics (at-most-one) are a
special case of claim semantics where the resource is "the right to consume
mail." The rewrite is: `claim_consumer()` already exists at
`runner_lock.py:199` and ALREADY calls `acquire()` with a generation. The
standing's `claim` field maps directly: "standing.claimed_by = token" ←
`runner_lock.holder(agent).token`. The generation that fences cursor writes is
the same generation the standing would publish.

What breaks at the seam: **the TTL difference.** `runner_lock` is 20s (runner
heartbeat), `role_queue` has no TTL at all (claim expires only on commit or
reclaim). A standing with a 20s heartbeat TTL but a claim that outlives the
process is a decoherence: the standing says "claimed" but the lock already
expired and a successor took over. The standing's `claim_expires` field must be
the lock TTL, not an independent value — derived, never authored independently.

**locks.py stays independent.** It protects files, not seats. The standing does
not replace it. The doc's claim-counting (monotonic counters beat timestamps) is
correct and should feed the standing's telemetry, but it does not merge with
path-lock fencing. Different resource, different key space, different lifetime.

**Bottom line:** the three are not duplicates. They protect different things
(seat, file, work item). The risk is not "which to delete" — it is that the
standing's claim/lease field must be the SAME artifact as the runner_lock value,
not a parallel structure that can diverge. If the standing says `claimed_by =
deepseek` and the runner_lock says the holder is a session with token
`session:abc`, those two must be the same Redis key read from the same Redis
hash. The doc's "single writer per field" on a Redis hash is the answer — the
claim field in the standing hash IS the runner_lock holder field, written once,
read everywhere.

---

## (3) THE WRAP: what the API client wrap actually looks like

The doc says "~20-line bridge." Here is the actual wiring.

### Where it hooks today

The existing instrumentation is NOT in the API client. It is in the runner loop,
at three points:

1. **`on_activity` callback** — fired at state transitions in `Agent.send()`:
   - `"calling-model"` → `"thinking"` (first stream token, `deepseek_chat.py:279`)
   - `"reading"` / `"searching"` / etc. (tool execution, `deepseek_chat.py:393`)
   - These are emitted by `_activity()` at line 240, which calls the runner's
     `on_activity` closure at `bifrost_runner_deepseek.py:275`.

2. **`on_trace` callback** — fired at tool-call AND thinking-chunk boundaries:
   - Tool calls: `self._trace("tool", ...)` at `deepseek_chat.py:400`
   - Thinking chunks: `self._trace("thinking", ...)` at `deepseek_chat.py:341`
   - Both fire `liveness.pulse()` at `bifrost_runner_deepseek.py:290` AND
     broadcast a `kind=trace` message at line 293.

3. **`interrupt` / `inject` hooks** — checked between tool rounds at
   `deepseek_chat.py:306-314` — these are the barge-in and steering paths.

### What the API client wrap would add

The API client is created at `deepseek_chat.py:65-68`:
```python
def make_client(api_key=None, base_url=BASE_URL):
    return OpenAI(api_key=..., base_url=...,
                  timeout=httpx.Timeout(MODEL_READ_TIMEOUT, connect=MODEL_CONNECT_TIMEOUT),
                  max_retries=MODEL_MAX_RETRIES)
```

A ~20-line wrapper would intercept `chat.completions.create()` to emit:
- **request start** (a `time.time()` and a pulse)
- **streaming chunk cadence** (count chunks, compute inter-chunk gaps)
- **request end** (wall time, token usage from `chunk.usage` at line 285)

The chunk-cadence signal is already available — `_stream_turn()` at line 269
iterates chunks. The wrapper would just count them and emit a pulse every N
chunks.

### What it costs per turn

A normal turn (no tools): 1 API call → 1 request-start pulse, N chunk-cadence
pulses (where N ≈ response tokens / chunks-per-pulse, say 1 pulse per 50
chunks), 1 request-end pulse. Negligible — ~3 extra Redis SET operations per
turn.

A tool-using turn: the same N times, where N = number of tool rounds. A 10-round
turn adds ~30 Redis SETs. At the runner's measured throughput (~3 turns/minute
worst case, from `_token_journal` data), this is ~90 Redis ops/minute —
negligible.

### Where the estimate is wrong

"~20 lines" is right for the wrapper itself but WRONG for the end-to-end cost.
The wrapper only adds socket-path signals. The tool-dispatch path
(`toolbox.execute()`) is NOT covered by an API client wrapper — that path needs
either its own wrapper or the existing `on_trace` hook must remain. The doc's
"~20-line bridge" is at best half the sensor plane. The other half (tool-call
liveness) already exists in the `on_activity`/`on_trace` infrastructure and
should be KEPT, not replaced by a socket-only wrapper that would be a
regression.

The current `on_trace` path fires a bus broadcast (`kind=trace`) AND a
`liveness.pulse()` at `bifrost_runner_deepseek.py:290-293`. If the socket
wrapper replaces the pulse source, the trace broadcasts (which the console uses
to show "🔧 search_files(...)" live) must keep working through the same channel
or the UX degrades. The doc does not mention this coupling.

---

## (4) SINGLE-WRITER-PER-FIELD on a Redis hash: does it survive?

**Yes.** Redis HSET on different fields of the same hash from concurrent
processes is atomic per field and does not produce torn reads or torn writes.

The Redis documentation is explicit: HSET is atomic. A concurrent HSET of field
`claimed_by` by process A and HSET of field `tool_count` by process B on the
same hash key cannot produce a torn state where `claimed_by` has half of A's
write. Each HSET is an all-or-nothing operation. A concurrent HGETALL sees
either the old value of each field or the new value — never a partial value.

The crucial property that makes the single-writer-per-field model work is that
fields NEVER share a writer. If process A writes `claimed_by` and process B
writes `claimed_by`, the last writer wins and the loser's write is silent —
that IS a conflict, just a silent one. Single-writer-per-field eliminates that
class: only the claimant writes `claimed_by`, only the sensor plane writes
`tool_count`, only the engagement owner writes `deadline`. No field has two
writers, so no write-conflict is possible.

**One nuance:** the doc proposes "telemetry is stamped by the harness/sensor
plane at turn boundaries — derived, never authored." This means the sensor plane
writes fields the agent's own process might also try to write. The single-writer
rule must be enforced AT THE CODE LEVEL, not by convention. The agent's runner
loop must NOT HSET `tool_count` directly — it must emit a sensor event and the
sensor plane does the HSET. If the runner writes it AND the sensor plane writes
it, the single-writer guarantee breaks and last-writer-wins silently kicks in.
The doc says this ("derived, never authored"), but the enforcement mechanism
needs to be mechanical: either a separate Redis key prefix that the agent cannot
write to, or a Lua script that refuses writes from the wrong source.

**Torn-read case that DOES exist:** HGETALL reads all fields atomically, but the
fields may have been written at different wall-clock times. If you read
`claimed_by` from t=0 and `tool_count` from t=5, you see a consistent snapshot
of the hash AT THE MOMENT OF THE READ, which is correct. The problem is not torn
reads; it is stale reads — reading a field that was just overwritten. That is
fine for standing data (a slightly stale tool count is still useful).

---

## (5) MIGRATION SEAM: smallest first slice that coexists with the live bus

**Build the sensor plane and the codebook FIRST, before touching the bus
semantics.** This is zero-risk to the live bus because sensors are fail-open and
write-only (they emit to a new Redis key, never to the bus protocol).

### Concrete first slice (~2 build sessions):

#### Step 1: the sensor key

Add ONE Redis hash per agent: `bifrost:sensor:<agent>` with these fields written
by the existing instrumentation:

| Field | Writer | Source |
|-------|--------|--------|
| `api_state` | API client wrapper | `_stream_turn()` phase: `calling-model` / `streaming` / `done` |
| `tool_state` | `on_trace` hook | `tool` / `thinking` / `idle` |
| `last_chunk_at` | API client wrapper | `time.time()` at each stream chunk |
| `last_tool_at` | `on_trace` hook | `time.time()` at each tool call |
| `turn_count` | runner loop | `_RUN_STATS["turns"]` at turn end |
| `pulse_gen` | runner loop | `PULSE_GEN[0]` (already exists, `bifrost_runner_deepseek.py:38`) |

This uses EXISTING code paths. The API client wrapper is the only new code; the
`on_trace` paths already pulse through `liveness.pulse()`. Write to
`bifrost:sensor:<agent>` instead of/in addition to the existing bus broadcast.

#### Step 2: the codebook v0

A committed file with exactly 3 signatures:

```
state: composing     → api_state=streaming, tool_state=idle, last_chunk_at < 30s ago
state: tool-running  → api_state=done, tool_state=tool, last_tool_at < 60s ago
state: dead          → last_chunk_at > 300s ago AND last_tool_at > 300s ago AND pulse_gen unchanged
```

All thresholds are file-level constants. Derive from ONE calibration drill (put
deepseek in each state manually, record readings).

#### Step 3: the first standing field

Add ONE field to the sensor hash: `standing:claimed_by`. Written by the
`runner_lock.heartbeat()` path — it IS the runner lock holder, exposed in the
same key. This is the doc's "single writer per field" in microcosm: one field,
one writer, zero conflicts.

#### What this costs the live bus

Zero. The bus does not change. The existing `liveness.pulse()` calls gain one
additional HSET each. The bus protocol is untouched. The board is readable via
`HGETALL bifrost:sensor:deepseek` — a new read path, not a changed write path.

#### What this enables

Once the sensor hash is live, the codebook can be tested against real fleet
behavior for a week. The observer (doctor/UI) can switch from beat-age inference
to signature matching WITHOUT changing how the bus operates. After the drift is
calibrated and the false-dead rate is measured, THEN the standing and engagement
layers can be built on top — with real data, not projected data.

**This preserves the doc's own ordering (sensor plane first, then codebook, then
standing) and keeps every layer read-only on the layer below it.**
