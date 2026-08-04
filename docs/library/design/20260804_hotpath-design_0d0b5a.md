---
akashic_id: art_20260804_hotpath-design_0d0b5a
akashic_sha: b93593d02480
schema_version: 1
status: current
type: design
date: 2026-08-04
title: hotpath-design
gist: "--- status: current (2026-08-04, opus5 hot-path seat, design-only lane) class: design dimension: Hot path and performance architecture (T156"
visibility: fleet
body_type: markdown
seats: []
category: [bus, agent-lifecycle, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T02:52:26"
updated: "2026-08-04T02:52:26"
---
<!-- GENERATED PROJECTION of art_20260804_hotpath-design_0d0b5a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# hotpath-design

---
status: current (2026-08-04, opus5 hot-path seat, design-only lane)
class: design
dimension: Hot path and performance architecture (T156 WIRE-B input)
ask: Daniil 2026-08-04 verbatim — *"I want us to overengineer this to the max while retaining
     performance. I want us to be able to mine this for information and to feed it into our live
     telemetry, this deserves our best."*
method: every number below is MEASURED on this machine (Windows 11, Python 3.11.9, 32 logical
     cores, httpx 0.28.1, openai 2.24.0) unless labelled INFER. Benchmark sources are named in §10.
---

# The hot path: maximal fidelity at near-zero cost on the request thread

## 0. HEADLINE

**The capture path is currently 196 microseconds of blocking syscalls on the caller's thread, and
it silently loses records.** Both are fixable to the point of irrelevance, and the fix makes the
journal *more* forensic, not less: I measured a complete replacement hot path at **0.98 us for a
non-streaming round trip and 5.23 us for a streamed one (35 SSE messages)** — 20x to 1200x cheaper
than what ships today — while capturing strictly more (per-chunk timing, stall gaps, byte counts,
sequence numbers, anomaly classification).

The constraint "retain performance" is not in tension with "overengineer to the max". It is in
tension with *doing the work on the wrong thread*. Everything expensive in a forensic record —
serialisation, hashing, filtering, file IO, rotation — is deferrable. Almost nothing that is
genuinely *unobservable later* is expensive.

The performance headline is not even the most important finding. That one is in §2.

---

## 1. HONEST ASSESSMENT OF THE SHIPPED IMPLEMENTATION

`scripts/wire_journal.py::record` (`:86-104`) does all of this **inline, on the caller's thread,
inside a mutex**:

| Op | file:line | Measured cost |
|---|---|---|
| `self._lock` acquire/release | `:95` | 0.091 us (uncontended) |
| `os.makedirs(..., exist_ok=True)` | `:96` | **45.47 us** |
| `time.strftime('%Y%m%d')` | `:97` | 0.67 us |
| `open(path,"a") … write … close` | `:98-99` | **77.59 us** |
| `json.dumps(rec, ensure_ascii=False)` | `:99` | 4.04 us |
| `self._rotate()` → `files()` → `os.listdir`+sort+`getsize` | `:100`, `:147-161`, `:164-170` | **58.21 us** |
| `_shape()` header comprehension over all headers | `:142-143` | 0.63 us |
| **Total, measured end-to-end** | | **196.2 us / record (median, single thread)** |

**Three syscalls are 92% of the cost, and all three are pure waste per record.** The directory is
created once in the life of a process, not 196,000 times a day. The file can stay open. The
rotation scan re-reads a 14-entry directory listing on *every single record* to answer a question
that changes at most once per day.

Under concurrency the mutex at `:95` turns that 196 us serial section into a queue:

```
threads=  1   p50=  182.6us   p95=  261.5us   p99=   450.8us   max=    453.2us
threads=  4   p50= 1248.4us   p95= 2143.5us   p99=  2762.4us   max=   3344.3us
threads= 20   p50= 6401.5us   p95=12129.8us   p99= 14772.5us   max=  28785.4us
```

At 20 concurrent callers the median caller waits **6.4 milliseconds** and the worst waits **28.8
milliseconds** to write one 832-byte line. Today the deepseek runner makes its API call on a
dedicated worker thread (`scripts/bifrost_runner_deepseek.py:1000`, `t = threading.Thread(target=_call,
daemon=True)`) alongside a heartbeat thread (`:1389`), so in-process contention is currently low —
but this is exactly the number that decides whether a 20-player season can ever run its runners
inside one process, or whether per-SSE-chunk instrumentation is affordable. Both answers are "no"
at 196 us.

**Contradiction recorded.** The prior design's §7 estimated *"order tens of microseconds … under
0.1% and beneath measurement noise"* (`research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md:452-457`)
and said plainly *"I have not benchmarked this."* The estimate was for the two-event-hook tier-0
sketch; the shipped code does considerably more per record. Measured, it is **196 us**, one to two
orders of magnitude above the estimate, and **6.4 ms** under 20-way contention. The estimate was
not dishonest — it was unmeasured, and it was labelled as such. This document is the measurement.

### What the shipped record actually contains

41 live records exist right now in `state/wire/wire-20260804.jsonl`. Field census across all 41:

| Field | non-null |
|---|---|
| `status`, `attempt`, `ts`, `ms_first_byte`, `headers`, `agent` | 41/41 |
| `model`, `stream`, `ms_total`, `finish_reason`, `system_fingerprint`, `response_id`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `reasoning_tokens`, `cache_hit_tokens`, `cache_miss_tokens`, `cached_tokens`, `prompt_sha`, `prompt_prefix_sha`, `response_sha`, `service_tier`, `error` | **0/41** |

**17 of 23 fields are structurally always null**, because the transport hook
(`scripts/wire_journal.py:322-341`) never sees a parsed body and no second half was built to fill
them. We are paying 196 us to write 698 bytes of mostly `null`. The two-half correlation the prior
design specified (`api-wire-visibility-design-opus5-2026-08-04.md:250-254`) is the missing piece,
and §5 below is my proposal for joining the halves at zero hot-path cost.

One concrete dead read: `scripts/wire_journal.py:332` calls `request.headers.get("x-model")`. Grep
over the whole repo finds `x-model` at exactly one place — that line. No such request header is ever
set. `model` is null in 41/41 records for this reason, not because the data is unavailable.

---

## 2. THE FINDING THAT MATTERS MOST: THE JOURNAL SILENTLY LOSES RECORDS

Runners are separate OS processes. `state/wire/wire-<date>.jsonl` is **one file per day, shared by
every process** (`scripts/wire_journal.py:97`). The mutex at `:83` is a *per-process* lock; it does
nothing across processes.

I measured 20 processes appending 850-byte lines to one file, byte accounting only, no parsing:

| Offered rate | Bytes on disk vs expected | Records lost/corrupted |
|---|---|---|
| 16,246 rec/s | 11,967,613 / 25,500,000 | **53.12 %** |
| 2,919 rec/s | 2,307,061 / 3,400,000 | **32.23 %** |
| 358 rec/s | 642,505 / 680,000 | **5.62 %** |
| **73 rec/s** (near real fleet rate) | 167,647 / 170,000 | **1.50 %** |

Every append mode I tried loses bytes on Windows under 20 processes:

| Mode | Bytes lost | Aggregate rate |
|---|---|---|
| Python text `open(p,"a")` — **what ships today** | 53.61 % | 15,451/s |
| Python binary `open(p,"ab")` | 53.92 % | 15,723/s |
| Persistent binary handle, unbuffered | 76.44 % | 130,228/s |
| Raw `os.open(O_APPEND\|O_BINARY)` + `os.write` | 72.40 % | 123,451/s |
| **One file per PID** | **0.00 %** | **149,225/s** |

INFER on the mechanism: Windows' CRT emulates `O_APPEND` as seek-to-end-then-write, and that pair is
not atomic across processes, so two writers land at the same offset and one overwrites the other.
I measured the *effect* exhaustively; I did not instrument the CRT to confirm the *cause*.

**This defeats the journal's own honesty contract.** `record()` (`:102-104`) increments
`self.dropped` on an exception — but an overwritten record raises nothing. The loss is invisible to
`summarize()` (`:189-227`) and to `expert()`'s dropped-captures finding (`:271-273`). *"Fail-open,
but never silent"* (`:44-47`) is true of the exception path and false of the dominant failure mode.

A second Windows-specific consequence: `_rotate()` (`:147-161`) calls `os.remove` on a journal file
another process may hold open. Measured directly:

```
os.remove on an OPEN file: FAILED -> PermissionError: [WinError 32]
```

`:151-153` catches this and `break`s, so `MAX_FILES` (`:60`) is silently unenforced whenever more
than one runner is live.

**Fix, and it costs nothing:** one journal file per writing process,
`state/wire/<agent>-<pid>-<date>.jsonl`. Measured at 0.00 % loss and the *highest* throughput of any
mode. The reader already globs (`files()`, `:164-170`); it needs a wider pattern, nothing more.
Rotation becomes per-process and therefore uncontended.

---

## 3. WHAT MUST HAPPEN ON THE REQUEST THREAD, AND WHAT MUST NOT

The test is not "is it cheap" but **"is it observable later?"** Anything the request thread is the
only witness to must be captured inline. Everything else is a scheduling decision.

### MUST be inline (the irreducible set)

| Observation | Where | Cost |
|---|---|---|
| `t_request_sent` — `perf_counter_ns()` before `super().handle_request` | `wire_journal.py:325` today | 0.058 us |
| `t_headers` — after it returns (this is TTFB-to-headers, **not** first byte of content) | `:334` | 0.058 us |
| `status_code` | `:334` | ~0 |
| 9 allowlisted header values, pulled into a fixed tuple | vs `dict(resp.headers)` at `:339` | **0.112 us** |
| Request `method`, `url.path` (never the query string), `content-length` | — | ~0.1 us |
| `attempt` inference | `:316-320` | ~0.1 us |
| Exception class name on the error path | `:328-333` | ~0 |
| **Per SSE chunk:** arrival ns, byte length, running max inter-arrival gap | not captured today | **0.131 us/chunk** |
| Sequence number `next(itertools.count())` | not present today | **0.032 us** |

### MUST NOT be inline (all of it is reconstructible from the tuple above)

`json.dumps` · header allowlist filtering · file open/write/close · `makedirs` · rotation scan ·
`strftime` · full-body hashing · UNKNOWN/MEASURED state annotation · derived ratios · anomaly
*explanation* (as opposed to anomaly *flagging*) · UI projection · any Redis/bus/MCP touch.

### The one genuinely hard case: hashing

`_shape()` hashes the prompt inline (`:138-141`). Measured:

| Strategy | 400 KB body | 45 MB body |
|---|---|---|
| Full `sha256` | 151.7 us | **17,396 us (17.4 ms)** |
| Bounded digest: `sha256(len ‖ head 4 KB ‖ tail 4 KB)` | **4.48 us** | **4.49 us** |

45 MB is not hypothetical: `scripts/deepseek_chat.py:200-208` records a measured worst turn of
**11.4 M tokens over 127 hops**, and the context is re-sent every hop. A full prompt hash on that
turn is 17 ms of pure CPU on the request thread, per attempt.

**Decision: the default digest is bounded and O(1) in body size — 4.48 us flat.** It must be named
for what it is (`prompt_digest_kind: "len+head4k+tail4k"`), never `prompt_sha`, because two prompts
that differ only in the middle collide. That is a real, stated limitation: it detects head changes
(system prompt) and tail changes (appended tool results) — which is the overwhelming majority of
real prompt mutation here — and it misses mid-context compaction. An exact digest is available as an
opt-in that folds sha256 into the request write (O(n) at a measured ~2.4 GB/s ≈ +17 ms on a 45 MB
body, ~0.5 % of that call's wall clock); it is off by default.

**Rejected: deferring the hash to the drain thread.** It requires holding the request body alive
until drain. At 45 MB × N in flight that is a memory cliff, and it violates §6's bound. The whole
point of a bounded digest is that the hot thread touches 8 KB and then forgets the body exists.

---

## 4. THE HANDOFF: A BOUNDED RING, DROP-OLDEST, AND SEQUENCE NUMBERS

### 4.1 Primitive choice, measured

| Primitive | Cost | Bounded? | Notes |
|---|---|---|---|
| `collections.deque(maxlen=N).append` | **0.028 us** | yes | drop-oldest by construction |
| `queue.SimpleQueue.put` | 0.028 us | **no** | unbounded memory |
| `queue.Queue(maxsize).put_nowait` + `except Full` | 0.508 us | yes | 18x the deque, pure-Python condvars |
| deque append + `len()` overflow check + 12-field tuple build | 0.135 us | yes | **the proposal** |

`deque.append` is atomic under the GIL. Verified rather than assumed: 20 threads × 5,000 appends,
three trials, **100,000/100,000 landed every time, zero loss**. A `deque(maxlen=N)` is therefore a
lock-free-enough MPSC ring for our purposes without a mutex on the producer side at all.

Carry a **tuple, not a dict, not JSON**. Measured: tuple build 0.019 us vs dict 0.110 us (5.8x), and
at 4,096 entries a tuple ring holds **0.66 MB** against a dict ring's **2.65 MB** (4x). Element 0 is
a schema version int so a reader can decode old rings after a format change.

### 4.2 Backpressure policy: two rings, not one

- **`RING_NORMAL`**, cap 4,096, **drop-oldest**, counted.
- **`RING_ANOMALY`**, cap 512, drop-oldest, counted separately. Fed by an inline predicate measured
  at **0.047 us**: `status not in 2xx` OR `attempt > 0` OR `max_gap > stall_threshold` OR (at join
  time) `finish_reason == "length"`.

Drop-oldest, not drop-newest and not block. Blocking would let a telemetry stall become an API stall
— the exact inversion the fail-open rule at `wire_journal.py:44-47` exists to prevent. Drop-newest
loses the record *closest to the incident*, which is the worst possible choice for forensics.
Drop-oldest keeps the recent past, which is what an Expert Info panel reads.

Anomalies get their own ring because they are rare (<1 % of traffic) and precious. Measured: the
drain thread clears **343,273 rec/s**; a 512-slot anomaly ring cannot fill unless the drain thread is
dead — and *that* is itself the anomaly worth reporting.

### 4.3 How drops stay COUNTED, and survive process death

Two mechanisms, deliberately redundant:

1. **In-process counters** — `dropped_overflow`, `dropped_encode`, `dropped_drain_dead`. Increment
   only in the overflow branch, under a lock taken *only there* (0.091 us, paid at 0 Hz in the
   normal case). Note honestly: a naive `+=` on a shared counter is **not guaranteed atomic** in
   CPython 3.11; my test at 20 threads × 20,000 increments happened to be exact twice, which proves
   nothing. The lock in the rare branch removes the doubt for free.

2. **Per-process sequence numbers** — `next(itertools.count())`, measured **0.0315 us**, and
   verified atomic: 20 threads × 5,000 draws × 3 trials, **100,000 distinct values, zero duplicates**
   every time. Every emitted record carries `(pid, seq)`.

Mechanism 2 is the one that matters. A counter dies with the process; a **sequence gap is
arithmetic that survives on disk**. A reader that sees seq 41,203 followed by 41,890 knows 686
records were lost, without the writer having lived long enough to say so. This converts the entire
class of silent loss — ring overflow, drain-thread death, `SIGKILL`, the Windows append-overwrite of
§2 — into a *computed, attributable* number. It costs 0.0315 us.

This is the answer to "drops stay COUNTED not silent" that I would defend hardest, because it is the
only one that holds when the thing doing the counting is the thing that failed.

### 4.4 Drain wake policy — and the bug a timer-only design has

My first prototype used a timer-only drain (`Event.wait(0.2)`). Under a burst it lost **31,808 of
40,000 records** — correctly counted, but lost. Adding a **high-water wake at 25 % ring fill**
(`Event.set()`, measured 0.309 us when already set, 0.496 us for set+clear) fixed it:

| Load | p50 enqueue | p99 | written | dropped | unaccounted |
|---|---|---|---|---|---|
| 800 ev/s (20 streams × 40 SSE/s — the measured real rate) | 1.30 us | 6.10 us | 4,000/4,000 | 0 | **0** |
| 8,000 ev/s (10x real) | 0.70 us | 5.10 us | 16,000/16,000 | 0 | **0** |
| 1,152,414 ev/s (unthrottled, 1,440x real) | 0.50 us | 1.20 us | 21,384 | 78,616 | **0** |

The accounting identity `enqueued == written + dropped + in_ring` held **exactly** at every load,
including the pathological one. That identity is a pin (§8).

**Where 800 ev/s comes from:** `research/in-flight/wire-capture-deepseek-2026-08-02/p2-raw-sse.txt`
carries 35 SSE `data:` messages across 10 HTTP byte-chunks in a 0.875 s span — **40.0 SSE msg/s and
11.4 HTTP chunks/s per stream**, with inter-chunk gaps of `[453, 109, 47, 47, 47, 31, 47, 47, 47]`
ms. Twenty concurrent players is 800 SSE events/s fleet-wide. Every rate claim in this document is
anchored to that measurement, not to a guess.

### 4.5 Drain thread: policy and durability

One drain thread per process. Loop: `wake.wait(0.25s)` → `popleft` until `IndexError` → batch 512 →
`json.dumps` → one `write` into a 1 MB buffered handle → `flush`.

| Op | Cost |
|---|---|
| `json.dumps` on the drain thread | 4.04 us/rec |
| Serialize + write + one fsync, 20,000 records | 58.3 ms = **2.91 us/rec**, 343,273 rec/s |
| `write()` into a 1 MB buffer | 0.49 us |
| `write()+flush()` to page cache | 3.45 us |
| `write()+flush()+fsync()` to platter | **1,281 us** |

At the real fleet rate the drain thread costs **0.23 % of one core** (2.91 us × 800/s). `fsync` per
record is 1.28 ms and is therefore never done per record. Policy: **flush every drain cycle
(≤250 ms, page-cache durable), fsync every 10 s and at clean shutdown.** Worst-case loss on a hard
power cut is 10 s of records, and the sequence numbers make that loss exactly countable.

**Do not adopt a faster encoder.** `ujson` (1.64 us) and `msgpack` (1.68 us) are both ~2.4x faster
than stdlib `json` and both are already installed. At 0.23 % core utilisation the saving is
unmeasurable and the dependency is real. `orjson` is not installed and must not be added for this.
If the storage seat chooses SQLite, encoding moves there and this paragraph is moot — the hot path
is unaffected either way, which is the point of the split.

**Drain-thread death must be a counted state.** My timer-only prototype died on a bad path and the
harness reported `unaccounted=4000` — enqueued, never written, never dropped. That must be
impossible: a watchdog checks `thread.is_alive()` on each `record()`… no — that is 0.4 us on the hot
path for a once-per-process event. Instead the **reader** detects it: the drain thread stamps a
`drain_heartbeat_ts` into every batch, and `wire_health()` reports `drain: DEAD` when the newest
batch is older than 3 wake intervals. Sequence gaps then quantify the loss. Zero hot-path cost.

**Shutdown.** The drain thread must not be a daemon whose `finally` never runs. Register an `atexit`
hook that sets `stop`, drains, flushes, fsyncs, joins with a 2 s cap. Bounded, worst-case loss at
exit: one wake interval.

---

## 5. JOINING THE TWO HALVES AT ZERO COST

The transport sees status, headers, timing, retries. It cannot see `finish_reason`, `usage`,
`system_fingerprint`, `response_id` — those live in the parsed body, which is why 17/23 fields are
null (§1). The runner's stream loop already holds them: `scripts/deepseek_chat.py:306-311` iterates
chunks and calls `_absorb_usage(chunk.usage)` (`:216-228`).

**Proposal: a thread-local current-observation slot.** The transport stores its `Obs` object in
`threading.local()` before returning the response; the stream loop reads it and folds in
`finish_reason`, `usage`, `system_fingerprint`, `response_id` on the final chunk. One record, both
halves, emitted at stream close.

Why this works here: the API call and the stream iteration run on the **same thread** — the runner
spawns exactly one worker (`scripts/bifrost_runner_deepseek.py:1000`) and the sync SDK does not hand
the request to another thread. Cost of a `threading.local()` attribute read is ~0.05 us. Under SDK
retries (`max_retries` at `scripts/deepseek_chat.py:63`, `core/comm/runner_lib.py:17,27`,
`scripts/sol_chat.py:65`) the transport is invoked repeatedly on that same thread; the slot holds the
latest `Obs`, and only the successful attempt has a body to fold — which is the correct semantics.

**INFER, not verified:** that the openai 2.24.0 sync client never moves a request to a worker thread
or an anyio portal. This is the single load-bearing assumption in §5. A `contextvars.ContextVar`
would survive an `async` re-entry where `threading.local()` would not; it costs marginally more and
is the safer choice if the assumption is ever in doubt. **A pin must assert the correlation actually
lands** (§8, B5), not merely that the mechanism compiles.

---

## 6. MEMORY BOUNDS PER PROCESS

Measured with `tracemalloc`, full rings:

| Ring contents | 4,096 | 8,192 | 32,768 |
|---|---|---|---|
| Fixed tuples | 0.66 MB | 1.05 MB | 5.26 MB |
| Dicts | 2.65 MB | 5.30 MB | 21.24 MB |
| Pre-serialised JSON strings | 1.44 MB | 2.87 MB | 11.50 MB |

Proposed steady-state budget, **per runner process**:

| Component | Bound |
|---|---|
| `RING_NORMAL` 4,096 tuples | 0.66 MB |
| `RING_ANOMALY` 512 tuples | 0.08 MB |
| Drain batch buffer, 512 JSON strings | ~0.18 MB |
| Buffered file handle | 1.00 MB |
| Per-in-flight-call `Obs` (`__slots__`, 9 ints) + 64-slot chunk trace | ~0.6 KB × in-flight |
| **Total** | **≤ 2.0 MB steady, 3 MB hard ceiling** |

Twenty processes → **≤ 60 MB fleet-wide, hard-bounded**, with no growth term. The bound holds because
nothing unbounded is ever retained: no bodies, no `httpx.Response` references (the 9 header values
are copied out as strings, so the response is free to be collected), no per-chunk record list beyond
64 slots, no accumulating dict of in-flight calls keyed by anything that could leak.

`__slots__` on `Obs` is not decoration — it is what keeps the per-in-flight allocation at hundreds of
bytes instead of a dict's ~200 B minimum plus per-key overhead.

---

## 7. SAMPLING: KEEP EVERY ROUND TRIP, FOLD EVERY CHUNK, RETAIN ON ANOMALY

### 7.1 Do not sample round trips

At 0.135 us per enqueue and a measured real rate of a few HTTP round trips per second fleet-wide,
sampling round-trip records buys nothing and costs fidelity. **100 % capture of HTTP round trips.**
Sampling here would be an unforced loss.

### 7.2 Do not *record* chunks — *fold* them

Per-SSE-chunk records at 800 ev/s would be 69 M records/day. The answer is not to sample them; it is
that **nobody wants per-chunk rows.** What forensics wants is the *shape* of the stream, and that is
eight integers folded in place at 0.131 us/chunk:

`n_chunks · n_bytes · t_first_ns · t_last_ns · max_gap_ns · t_first_content_ns ·
t_last_reasoning_ns · n_gaps_over_threshold`

From those alone: TTFT, thinking-phase duration, content-phase duration, the stall gap, throughput,
and the silence before the final usage chunk. Full fidelity on the statistics; **zero** per-chunk
records. Total streamed-round-trip cost measured at **5.23 us** including all 35 folds.

This is aggregation, not sampling. Nothing is thrown away that anyone asked for.

### 7.3 Retain-on-anomaly for the raw chunk trace

For the rare investigation that *does* want per-chunk detail, each in-flight call keeps a **64-slot
ring of (arrival_ns, nbytes)** — 512 bytes — and that trace is **emitted only if the call is
anomalous**: non-2xx, `attempt > 0`, `finish_reason == "length"`, or `max_gap > stall_threshold`.
A clean call discards its trace at close, costing nothing on disk.

This is the concrete form of "keep ALL anomalies, sample only the boring": we keep the full trace of
every incident and none of the boring ones, decided *after* we know which it was. A sample-first
policy decides before it knows, and therefore loses incidents.

The stall threshold is adaptive but computed **on the drain thread**, never inline: an EWMA of
inter-chunk gap per `(agent, model)`, published as a single float the hot thread reads (~0.02 us).
Anchor from the probe data: healthy steady-state gaps are 31–47 ms, with a 453 ms first gap. A
threshold of `max(2 s, 8 × ewma_gap)` flags a genuine stall without firing on the normal prefill
pause. `DEEPSEEK_READ_TIMEOUT` is 120 s (`scripts/deepseek_chat.py:62`), so anything between 2 s and
120 s is invisible today — that band is exactly where the F5 600-second-timeout incident lives
(`api-wire-reverse-engineering-deepseek-2026-08-04.md:228-231`).

### 7.4 The last-resort boring sampler, and why it is arithmetically honest

If `RING_NORMAL` hits high-water on two consecutive drains, raise `sample_shift` 0 → 1 → 2 → 3
(keep 1 in 2^shift **boring** records; anomalies are never sampled). Gate cost measured at 0.052 us
(`counter & mask`) — deterministic, not `random()` (0.042 us), because a deterministic stride is
reproducible and a reader can verify it. **`sample_shift` is written into every record**, so a
sampled count can be scaled back up; a dropped count cannot. Decay the shift to 0 after four clean
drains.

Order of degradation under overload, all counted: fold chunks (always) → shed boring chunk traces →
raise `sample_shift` on boring records → drop-oldest boring records → drop-oldest anomalies (should
be unreachable; if reached, that fact is itself the top-severity Expert Info finding).

---

## 8. THE BUDGET, AND HOW A PIN VERIFIES IT

### 8.1 The numbers I am committing to

| Budget | Value | Measured today |
|---|---|---|
| **B1** Added latency per **non-streaming** round trip, request thread, p99 | **< 6 us** | 0.98 us (median, complete proposed path) |
| **B2** Added latency per **streamed** round trip (35 SSE msgs), p99 | **< 25 us** | 5.23 us + 4.48 us digest = 9.71 us |
| **B3** Marginal cost per additional SSE chunk | **< 0.5 us** | 0.131 us |
| **B4** Journal RSS per runner process | **< 3 MB** | ~2.0 MB by component |
| **B5** Drain-thread CPU, fleet-wide, at 800 ev/s | **< 1 % of one core** | 0.23 % |
| **B6** Records lost without being countable | **0** | seq-gap arithmetic + per-PID files |
| **B7** Fraction of a ~1,000 ms API round trip | **< 0.005 %** | 9.71 us / 1,000 ms = **0.00097 %** |

B7's denominator is measured, not assumed: `ms_first_byte` across the 41 live records runs
638–1,414 ms, and `p3-ttft-decomposition.json` records total call times of 1.063–1.156 s.

Headroom is deliberate: B2 at 25 us against a measured 9.71 us is 2.6x, which absorbs a slower CI
box without letting a genuine 10x regression through.

### 8.2 The benchmark pin

`tests/test_t156_hotpath_budget.py`, following the M3 RED-first rule and the existing naming
(`tests/test_t156_wire_journal.py`).

**The stability problem is real and must be designed around.** An absolute-microseconds assertion is
a flaky test on shared CI. The pin therefore asserts a **ratio against a calibration loop measured in
the same process, in the same run**:

```
calib   = median time of 20,000 × time.perf_counter_ns()          # ~0.058 us here
delta   = median(recording transport) − median(null transport)     # over 20,000 synthetic RTs
assert  delta / calib < K          # K = 120 for streaming (measured here: 9.71/0.058 = 167 → see note)
```

Note on K: the measured ratio on this machine is 9.71/0.058 ≈ 167, so K must be set from the
measured value with headroom (K = 400), not from the absolute microsecond target. The ratio form
survives a machine 3x slower; the absolute form does not. **The calibration constant must be
recorded in the test with the machine it was taken on**, per the method-baseline receipts rule.

Companion pins, none of which are timing-sensitive:

- **P-HP1 — accounting identity.** Drive 100,000 records through a ring whose drain is paused;
  assert `enqueued == written + dropped_overflow + dropped_encode + len(ring)` exactly. (Measured
  exact at every load in §4.4, including 78,616 drops.)
- **P-HP2 — drop-OLDEST, not newest.** Push `cap + N` monotonically increasing records; assert the
  surviving head is record `N`, not record `0`. (Measured: pushed 20,000 into an 8,192 ring →
  oldest survivor ts = 11,808 = exactly `20,000 − 8,192`.)
- **P-HP3 — no shared-file append.** Structural: assert the resolved journal path contains
  `os.getpid()`. This is the §2 defect, pinned so it cannot come back.
- **P-HP4 — multi-process losslessness.** Spawn 8 processes × 2,000 records; assert
  `sum(lines across all files) == 16,000` and zero unparseable lines. This test **fails today** on
  the shipped shared-file design and is therefore the RED that opens the slice.
- **P-HP5 — sequence continuity.** Assert every emitted record carries `(pid, seq)` and that within
  one pid the seqs are strictly increasing with no duplicates; assert a deliberately induced drop
  shows up as a gap of exactly the right size.
- **P-HP6 — no hot-thread hashing over an unbounded body.** AST/behavioural: record with a 45 MB
  `prompt_text` and assert the hot-path call returns in under 10x the 2 KB case. (Today: 381 us vs
  196 us for a 400 KB body — already 2x, and it scales linearly to 17 ms at 45 MB.)
- **P-HP7 — the correlation lands.** Against a stub that streams and then reports usage: assert the
  emitted record has `finish_reason` AND `status` AND `x-ds-trace-id` populated — i.e. that the two
  halves of §5 actually joined. Today this fails: 0/41 live records have `finish_reason`.
- **P-HP8 — streaming is not consumed.** Inherited from the prior design's P6; the fold must be a
  pass-through tee. Measured generator-frame overhead if a wrapper is used: +0.035 us/chunk.

### 8.3 The reader, named — because a writer without one is the defect

Rule 3 of the brief, and the standing `cognitive_metrics` warning. The wire journal's `summarize()`
(`:189`) and `expert()` (`:229`) have **zero production callers** — grep finds them only at
`tests/test_t156_wire_journal.py:113,124`. Meanwhile `TokenJournal` *does* have one:
`core/comm/doctor.py:1099-1102` re-prices at read time. The asymmetry is exact and current.

This design adds telemetry *about the telemetry*, and it must be read too. `wire_health()` returns
`{enqueued, written, dropped_overflow, dropped_encode, seq_gaps_detected, ring_depth_p99,
sample_shift, drain_alive, drain_lag_ms}`. **Named reader: the doctor line in `core/comm/doctor.py`,
alongside the existing token-journal read.** If that line is not written in the same slice, the slice
has reproduced T140 one directory over — and this time with a performance budget attached to
something nobody looks at.

---

## 9. THE PROPOSED HOT PATH, IN FULL

```
observe_open()                 → Obs() with __slots__: seq=next(count), t0=perf_counter_ns()
  … super().handle_request() …
o.t_hdr = perf_counter_ns()
observe_chunk(o, n)  ×N        → ts, max_gap, n_chunks, n_bytes   [0.131 us each]
observe_close(o, status, hdrs, model, attempt, digest)
     → build 22-field tuple, 9 header .get()s, anomaly predicate,
       pick ring, len-check, append, conditional wake
```

Measured, complete:

| Path | Cost |
|---|---|
| `observe_open` + `t_hdr` + `observe_close` (non-streaming) | **0.978 us** |
| Full streamed round trip, 35 SSE chunks | **5.226 us** |
| Bounded body digest (any body size) | **4.48 us** |
| **Worst realistic total per streamed round trip** | **9.71 us** |

Against today's **196 us** single-threaded and **6,401 us** at 20-way contention: **20x** and
**660x** respectively — while capturing per-chunk timing, stall gaps, byte counts, sequence numbers
and anomaly classification that the 196 us path does not capture at all.

That is the whole argument for "overengineer to the max while retaining performance": the maximal
version is the cheap one, because maximal fidelity is about *what you observe*, and cost is about
*where you process it*.

---

## 10. BENCHMARK PROVENANCE

All numbers were produced by scripts I wrote and ran in
`C:\Users\L5\AppData\Local\Temp\claude\C--Users-L5\7507b107-24ca-4b3e-b7c8-07940bf0d958\scratchpad\`
on 2026-08-04: component decomposition and 20-thread contention against the live
`WireJournal`; ring/memory/drain throughput; stream tee and durability cadence; high-water wake;
20-process file contention (`hp_bench5_multiproc.py`); append-atomicity byte accounting
(`hp_bench6_append_atomicity.py`, `hp_bench7_append_modes.py`); and the complete proposed hot path
(`hp_bench8_proposed.py`). Each timing is a median of 7 runs of 1,000–50,000 iterations.

**Hazard, recorded:** the scratchpad is shared and two of my earlier benchmark files were overwritten
mid-session by another seat writing SQLite benchmarks to the same names. My results were captured
before the overwrite, but the two earliest scripts are no longer recoverable at those paths. Seats
running concurrent benchmarks should namespace scratchpad filenames — I renamed mine `hp_*` after the
collision. (This is the file-plane analogue of the test-file clobber in the two-model concurrency
findings.)

---

## 11. CONTRADICTIONS RECORDED, NOT RESOLVED

1. **Estimate vs measurement.** The prior design estimated "tens of microseconds … under 0.1 %"
   (`api-wire-visibility-design-opus5-2026-08-04.md:452-457`) and said it had not benchmarked. The
   shipped code measures 196 us and 6.4 ms under 20-way contention. Both statements are honest; only
   one is measured.
2. **"Never silent" vs the dominant failure mode.** `wire_journal.py:44-47` promises counted drops.
   The measured dominant loss (§2) raises no exception and is not counted. The promise holds for the
   exception path only.
3. **One file vs many processes.** The prior design specified `state/wire/<agent>/<date>.jsonl`
   (`:335`); the shipped code writes `state/wire/wire-<date>.jsonl` with no agent segment. Neither is
   per-process, and per-process is what the measurement demands. Whether "agent" is a sufficient
   partition depends on whether two processes can ever share an agent id (restarts, incarnations, the
   deepseek/deepseek-review split) — I did not resolve that.
4. **Bounded digest vs exact identity.** A `len+head+tail` digest cannot distinguish prompts that
   differ only mid-context. That is a real fidelity loss traded for O(1) cost, and it is the one place
   in this design where "maximal fidelity" is knowingly not chosen. Mid-context compaction is exactly
   the case it misses.
5. **`threading.local()` vs `ContextVar`** for the §5 join. I chose the cheaper one on an unverified
   assumption about the SDK's threading. Recorded rather than resolved.
6. **The counter that lost nothing.** A naive `+=` drop counter did not lose increments in my
   400,000-increment test, but CPython gives no guarantee. I am proposing the lock anyway. Recording
   this so nobody later "optimises" the lock away citing my measurement.
7. **Per-process rings vs a fleet view.** Twenty processes means twenty rings, twenty sequence
   spaces, twenty files. Cross-process ordering is only as good as the clocks. `perf_counter_ns` is
   *not* comparable across processes; wall-clock `time.time()` is, at ~15 ms Windows resolution. Every
   record needs both: `perf_counter_ns` for intra-call deltas, `time.time()` for cross-process
   ordering. I did not measure clock skew across processes.

---

## APPENDIX — WHAT I DID NOT VERIFY

**Not run, not measured:**

- **I made no live API call.** Every rate claim (40 SSE msg/s, 11.4 HTTP chunks/s, 1,000 ms round
  trip) comes from the 2026-08-02 probe artifacts and from the 41 records already on disk in
  `state/wire/wire-20260804.jsonl`. I did not generate new traffic.
- **I did not build or run the proposed transport against httpx.** `observe_open/chunk/close` were
  benchmarked as standalone functions with realistic arguments, not wired into an
  `httpx.HTTPTransport`. The integration cost — one extra generator frame per chunk if a wrapper
  stream is used — I measured separately at **+0.035 us/chunk** and included, but the composed
  object was never executed.
- **I did not verify that the openai 2.24.0 sync path keeps the request on the caller's thread.**
  §5's whole join mechanism rests on it. Labelled INFER; pinned by P-HP7.
- **I did not measure `contextvars.ContextVar` get/set cost**, so the safer alternative in §5 has no
  number attached.
- **I did not measure cross-process clock skew** or `time.time()` resolution on this box, though §11.7
  depends on it.
- **I did not confirm the CRT mechanism** behind the Windows append loss — only its effect, which I
  measured five ways at four rates.
- **The 45 MB body figure is derived, not observed.** It comes from the 11.4 M-token worst turn noted
  at `scripts/deepseek_chat.py:200-208` times ~4 chars/token. I did not find a 45 MB request body on
  disk.
- **I did not measure on Linux or WSL.** Every file-system result in §2 is Windows-specific, and
  POSIX `O_APPEND` is genuinely atomic up to `PIPE_BUF`, so the shared-file loss may not reproduce
  there. The per-PID fix is correct on both; the *severity* argument is Windows-only.
- **The `text_a` row of §2's mode table shows `intact 0/30,000`.** That is an artifact of my checker:
  Windows text mode translates `\n` to `\r\n`, so lines are 851 bytes and my 849-byte equality test
  never matched. The load-bearing number in that row is `53.61 % bytes lost`, which is
  translation-independent. Recording this so the table is not read as "text mode corrupts everything".

**Sampled, not exhausted:**

- **Runner source: sampled.** I read `scripts/wire_journal.py` in full (344 lines),
  `scripts/runner_token_journal.py` in full, and targeted ranges of `scripts/deepseek_chat.py`
  (50–120, 190–346) and `scripts/bifrost_runner_deepseek.py` (985–1015, 1380–1395). I did **not**
  read the ~4,400 lines of runner source, so a second API call site or a second thread that makes
  requests could exist outside my greps. The prior design already found one such outlier
  (`scripts/kimi_chat.py:145-155`, raw `urllib` for a balance probe).
- **Probe artifacts: 3 of 7 read** (`probes.py`, `p2-byte-chunks.json`, `p3-ttft-decomposition.json`),
  plus a line/timestamp count over `p2-raw-sse.txt`. I did not read `p1`, `p4`, `p5`, `p6` directly —
  their contents reach me via the two prior-art documents.
- **The other five seats' designs: unread.** I read `mining-design.md`'s existence in
  `research/in-flight/wire-next/` but not its contents. If another seat proposes SQLite on the writer
  path, §4.5's encoder paragraph and B5's drain budget need re-derivation against *their* measured
  insert cost, not mine. My hot-path numbers hold regardless — the ring boundary is the same — but the
  **drain** budget is theirs to defend.
- **`core/coord/cognitive_metrics.py`: not read this session.** Its role here is only as the
  cautionary precedent, quoted from the brief and from the prior design.

**Deliberately not done:**

- No git operations, no bus sends, no ledger writes, no MCP calls. One file written in the repo:
  this one. Benchmark scripts live outside the repo, in the session scratchpad.
- I proposed no pricing field, no `cost` symbol, and no import of `runner_token_journal`. Money stays
  in `TokenJournal` (`scripts/runner_token_journal.py:56-82`).
- I changed nothing under `core/`. The recorder stays runner-side per the membrane law.
