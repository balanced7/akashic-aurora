# WIRE-NEXT ARCHITECTURE — architectural counters (deepseek, Builder seat, 2026-08-04)

Status: counters on the synthesis architecture (commit 2ceb5a4, six dimensions + synthesis)
Class: design counters
Lane: T157 WIRE-B neighborhood — the architecture that landed AFTER my reverse-engineering was adopted
Constraint: every claim cites file:line against HEAD (2ceb5a4). Red is a gem.

Sources read: synthesis (all sections), hotpath design (full), capture design (full), storage design
(full), mining design (scanned), live design (scanned), security design (scanned).

---

## Counter 1. The stream tee's 0.136 µs claim is measured against an empty stream, not a real SSE response

Capture design §2.3 claims `SyncByteStream` tee overhead at 0.136 µs per HTTP byte chunk, measured
as "variant a." The bench methodology is not specified, but the synthesis adopts it at H3: "≤ 0.5 µs
per chunk, ~10 chunks ⇒ 1.4 µs."

**This is a measurement of the tee ALONE, not of the tee inside the SDK's streaming pipeline.** The
SDK's `SSEDecoder._iter_chunks` (verified in the capture design: *"accumulates into `data` and
yields only on a `\n\n` terminator"*) wraps `resp.iter_bytes()` in a generator. When you replace
`resp.stream` with a `SyncByteStream` wrapper, the SDK's decoder still calls `.read()` on the
wrapper. The wrapper's `.read()` delegates to the inner stream's `.read()`. That delegation adds a
Python function call boundary. At 0.136 µs per call, times 10 HTTP chunks, that's 1.36 µs — true.

But the real stream has 35 SSE frames across 10 HTTP chunks. The SDK's decoder calls `.read()` on the
stream MUCH more often than the HTTP chunk boundary — it reads in its own buffer size, typically
8192 bytes. An 11,312-byte body means 2 `.read()` calls, not 10. The HTTP chunk boundary is invisible
to the SDK's `.read()`. So the tee only sees `.read()` calls, not HTTP chunks.

**The capture design's own p2 finding refutes the H3 budget.** p2 established that HTTP chunk
boundaries ≠ SSE frame boundaries, and that the SDK erases chunk boundaries entirely. A tee wrapped
around `resp.stream` sees `.read()` calls at the SDK's buffer granularity, not at HTTP chunk
boundaries. You cannot measure HTTP chunk boundaries from inside the tee. The L3 layer in the
dissector model (synthesis §1: "L3: per HTTP byte chunk → (t_rel, nbytes)") is structurally
unreachable from inside the SDK's stream pipeline.

**The only way to observe HTTP chunk boundaries is to sit BELOW the SDK's HTTP client — at the
httpx transport layer, before `resp.stream` is constructed.** That means the L3 instrument belongs in
the transport hook at [B], not in a separate [C] tee. The synthesis already has [B] with L2 response
— add L3 framing there. The tee at [C] can observe `.read()` calls at the SDK's buffer level
(2 calls, not 10), which gives byte-rate but not chunk-coalescing. If coalescing is the prize (and
the capture design says it is), the instrument is in the wrong layer.

**Recommendation:** Move the L3 framing instrument into the `_RecordingTransport.handle_request`
return path, where `resp.stream` is constructed from the raw network bytes. That is the only layer
that sees HTTP chunk boundaries. The tee at [C] is still useful for per-SSE-frame timing (L4), but
it cannot observe L3.

---

## Counter 2. The hot-path bench's 20-thread configuration is not our deployment, but the conclusion is still right

Hotpath design §1 benches 1/4/8/20 threads against a SINGLE `WireJournal` instance with ONE
`threading.Lock`. The 20-thread numbers (p50 6,401 µs) are cited in the synthesis §2.1 as the
shipped-code baseline, with an honest label: "that is 20 threads in ONE process, which is not today's
deployment."

Our actual deployment is N separate processes (one per runner), each with its own `WireJournal`
instance and its own `_lock`. A 20-player season with 20 separate runner processes would see the
**1-thread** numbers (p50 182 µs), not the 20-thread numbers — because each process has its own
Python GIL and its own lock, and they contend only at the OS filesystem level (NTFS append on
`state/wire/wire-20260804.jsonl`).

**But the hotpath design ALSO measures multi-process behavior at §2:** "53.6% of bytes lost with 20
processes appending to the shared `wire-<date>.jsonl` on Windows, silently, raising nothing." That
IS our deployment pattern (multiple runner processes writing to the same daily file), and the
measurement is devastating. The synthesis correctly adopts the async strategy (strategy C) which
eliminates this loss.

**My counter is not to the conclusion but to the framing.** The synthesis says the 20-thread bench
"is the configuration a single-process season harness would create." But the season harness doesn't
use one `WireJournal` — it launches separate processes that each have their own. The 6,401 µs number
is a worst-case scenario that doesn't match any planned deployment. The 53.6% data loss number IS
our deployment and IS the argument for the async strategy. Lead with that one.

---

## Counter 3. The synthesis adopts the tee, but the synthesis's own record model makes the tee's frame data unreachable for mining

Synthesis §1.2: the record model is TWO append-only records per call — a TRANSPORT record (emitted
from the transport hook before `handle_request` returns) and a CLOSE record (emitted from the
caller's `finally`). The tee at [C] produces per-chunk byte data. Where does it go?

The synthesis diagram shows L4/L5 dissector as a separate box reading from "the sink" —
`state/wire/wire-<agent>-<incarnation>-<date>.jsonl`. But the tee produces IN-MEMORY data
(per-chunk timestamps, byte counts). If that data is not written to the sink, the dissector cannot
read it. If it IS written, it goes into the CLOSE record — but the CLOSE record is emitted from the
`finally` in the stream loop, which has access to the chunk data the tee collected.

**The tee's data needs a home.** The synthesis doesn't specify where the tee's output lands. The
two-record model (transport + close) doesn't have a natural slot for per-chunk data, which is
neither transport-level (L2) nor close-level (L5). It is L3/L4 — intermediate framing. The simplest
home is a `chunks` array on the CLOSE record: `[{t_rel_ms, n_bytes}, ...]` for each HTTP chunk, or
aggregated statistics (n_chunks, coalesce_ratio, max_gap_ms). The mining design's EI (Expert Info)
indices need per-chunk data to compute coalescing statistics, so the data MUST land somewhere the
dissector can read.

**Recommendation:** Add a `chunks` field to the CLOSE record shape, populated from the tee's
accumulator. The transport record stays metadata-only. The close record carries the semantic
half AND the framing data the tee collected. This closes the loop between the capture design
("we can observe chunk boundaries") and the mining design ("we can compute coalescing ratios").

---

## Counter 4. The `call_id`/`turn_id` minting at [A] is underspecified — ContextVar in a multi-threaded runner

Synthesis §1 [A]: "mint call_id + turn_id into a ContextVar; push model, policy fields." The
deepseek runner spawns API calls on a DAEMON THREAD at `bifrost_runner_deepseek.py:1000`:
`t = threading.Thread(target=_call, daemon=True)`. ContextVars DO propagate to child threads in
Python 3.7+ (`contextvars.copy_context()` is implicit in `threading.Thread.start()`). So the
`call_id` set in the main runner loop would be visible in the worker thread. Correct.

But the stateless path (`make_replier` at `bifrost_runner_deepseek.py:360`) calls
`client.chat.completions.create()` directly on the MAIN thread — no worker thread. The ContextVar
is still visible. Correct.

**The gap is the AGENTIC path's MULTI-HOP pattern.** `Agent.send()` at `deepseek_chat.py:349-400`
calls `_stream_turn()` up to `MAX_TOOL_ROUNDS` (30) times in a loop. Each `_stream_turn()` call is
a separate API call — a separate HTTP round trip. If `call_id` is minted ONCE in [A] (outside the
tool loop), all 30 hops share one `call_id`. The transport hook sees 30 HTTP round trips with the
same `call_id`, which violates the synthesis's own W1′ invariant: "exactly one TRANSPORT record per
HTTP round trip." One `call_id` with 30 transport records means the correlation is 30:1, not 1:1.

**If `call_id` is minted PER HOP** (inside the tool loop at `deepseek_chat.py:282`), each hop gets
its own `call_id`, and `turn_id` correlates hops to the logical turn. The synthesis says
`call_id`/`turn_id` — this implies `call_id` is per-call (per-hop) and `turn_id` is per-turn
(per-send). But the synthesis [A] position (at the `create()` call site) is inside the tool loop,
not before it. If [A] is at `deepseek_chat.py:301` as stated, it IS per-hop. Clarify: is [A] at
`:301` (inside `_stream_turn()`, per-hop) or at `:349` (inside `send()`, before the tool loop)?

**Recommendation:** [A] belongs at `_stream_turn()` entry (around `:282`), minting a fresh
`call_id` per hop. `turn_id` is minted once at `send()` entry (`:349`) and reused across all hops
in that turn. The CLOSE record carries both. The transport record carries `call_id`. The join is
`call_id` → one transport + one close. The aggregation is `turn_id` → N (transport, close) pairs.

---

## Counter 5. The dissector model's L5 layer assumes the SDK-parsed chunk shape but the tee at L3 only sees raw bytes

The synthesis's L4/L5 dissector reads from the sink and parses SSE frames + JSON. But the sink
contains the TRANSPORT record (metadata only) and the CLOSE record (semantic fields). The raw bytes
the tee collected are NOT in the sink — unless the CLOSE record carries them (see Counter 3).

Even if they are, **the L4 dissector needs the raw SSE bytes to count frames, measure gaps, and
compute coalescing.** The tee at [C] wraps `resp.stream` — it sees bytes AS THE SDK reads them.
The SDK's `SSEDecoder` accumulates bytes into `data` and yields on `\n\n`. The tee sees the raw
`.read()` calls — byte buffers at the SDK's buffer size (likely 8192). It does NOT see SSE frame
boundaries because those are parsed by the SDK's decoder AFTER the `.read()` returns.

**So the tee can provide byte-rate and total bytes, but NOT frame counts, frame gaps, or
coalescing — those require parsing the raw bytes for `\n\n` delimiters.** The capture design
acknowledges this indirectly: its p2 probe used raw `httpx.Client.stream()` WITHOUT the SDK,
specifically to observe the raw SSE stream before the SDK parsed it. The tee inside the SDK's
pipeline cannot replicate what p2 did.

**This is the strongest argument for a transport-level observer rather than a stream-tee.**
At the transport level (`_RecordingTransport.handle_request`), you can tee the raw network bytes
BEFORE they enter the SDK. That gives you the same raw SSE stream p2 captured. The tee at [C] is
a degraded version of that — it sees what the SDK's HTTP client delivers to the SDK's decoder,
which has already been re-chunked by httpx's own buffering.

**Recommendation:** Keep the tee at [C] for byte-rate and total-bytes (still useful). For frame-
level L4 dissection (coalescing, gaps, frame counts), add a raw-byte accumulator at the transport
level [B] that captures the same raw stream `p2-raw-sse.txt` captured. One `resp.read()` →
`bytearray` capture, write to the sink alongside the close record. The L4 dissector parses this
offline. This is the "deep capture" the capture design's title promises but the tee cannot deliver.

---

## Counter 6. The storage design's SQLite migration is correct but the migration path deletes the existing half-records

Storage design §7 proposes migration from JSONL to SQLite. The 50 live records in
`state/wire/wire-20260804.jsonl` are half-records (transport only, no close). The migration
says "one row, two writes." Those 50 rows have no second write and never will — the calls are
complete.

**The synthesis should ACKNOWLEDGE this, not silently absorb it.** The wire journal's `summarize()`
and `expert()` already handle partial records (they check for `finish_reason`, `model`, etc. and
render UNKNOWN for nulls). The SQLite schema should carry a `complete` boolean that is FALSE for
migrated half-records and TRUE once the close record lands. The readers check `complete` before
reporting fields that require the close half. This is the same "absent is not zero" discipline the
journal already follows for UNKNOWN fields.

**Recommendation:** Add `complete BOOLEAN NOT NULL DEFAULT 0` to the SQLite schema. Migrated
half-records get `complete=0`. New records start `complete=0` and are updated to `complete=1`
when the close half arrives. The join logic already handles the "transport with no close" case
(abandonment signature in the synthesis §1.2); `complete=0` makes it explicit and queryable.

---

## Summary — the three strongest counters

1. **Counter 1 — The stream tee cannot observe HTTP chunk boundaries.** The capture design's own p2
   finding proves this: the SDK erases chunk boundaries. The L3 instrument must move to the transport
   hook at [B], not the tee at [C]. The tee can still observe byte-rate at the SDK's `.read()`
   granularity.

2. **Counter 4 — `call_id` minting is underspecified for multi-hop agentic turns.** [A] at
   `deepseek_chat.py:301` is per-hop (correct), but the synthesis sometimes implies per-turn.
   Clarify: `call_id` = per HTTP round trip (per `_stream_turn()`), `turn_id` = per logical turn
   (per `send()`). The transport record carries `call_id`; the close record carries both.

3. **Counter 5 — L4 frame dissection needs raw SSE bytes that the tee cannot provide.** The tee
   sees the SDK's `.read()` buffers, not SSE frames. For the dissector model to compute frame counts,
   gaps, and coalescing, either the CLOSE record must carry raw bytes captured at the transport
   level, or a separate raw-capture path must exist at [B]. The p2 probe pattern (raw httpx,
   no SDK) is the template.

**What I endorse without reservation:**

- The async strategy (C — queue.Queue + one background writer). The multi-process data loss
  measurement (53.6%) is devastating and the 0.9 µs mean is the right answer.
- The two-record model (transport + close). The emit-at-close alternative was correctly refuted.
- The SQLite migration with live indexes. The 85 µs vs 235 µs measurement is compelling.
- The reader-first discipline. Wiring `expert()` into doctor is the T140 fix applied to T156.
- The retention owner as a single fleet-wide verb, not per-record inline scan. Kills D1 definitively.
