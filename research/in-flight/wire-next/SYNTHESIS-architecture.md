---
status: current (2026-08-04, T156 WIRE-B synthesis seat)
class: design
lane: T156 WIRE-B — ONE architecture across six parallel design dimensions, after adversarial verification
inputs: research/in-flight/wire-next/{hotpath,capture,storage,mining,live,security}-design.md
        + verifier verdicts for hotpath, capture, storage (see §7.1 — three verdicts did not reach me)
extends: scripts/wire_journal.py (T156 WIRE-A, shipped 2026-08-04)
ask: Daniil 2026-08-04 verbatim — "I want us to overengineer this to the max while retaining
     performance. I want us to be able to mine this for information and to feed it into our live
     telemetry, this deserves our best." Earlier: "the same kind of forensics that wireshark has as
     well as enterprise security appliances with deep packet sniffing"; the journal should be
     "a good place for our security eyes when we get them".
method: every claim cites file:line. Numbers marked MEASURED-HERE were run by me tonight with the
     in-repo benches named in §2.4. Numbers inherited from a dimension carry that dimension's name.
     Anything I could not verify is labelled INFER or listed in §7.
scope: DESIGN ONLY. No code written, no commits, no bus sends, no ledger writes. One file written.
---

# The wire platform: one architecture

## 0. THE ONE-PARAGRAPH ARCHITECTURE

Six dimensions converged, independently, on the same load-bearing move: **the request thread
observes and enqueues; everything else happens somewhere else.** Hot-path (§4 ring), storage (§6.2
bounded queue), and live (§2.2 SimpleQueue) each proposed it separately, and the repo already
contains the benchmark that settles it. What they disagreed about — storage engine, digest shape,
where chunks are counted, whether the record is one or two — resolves cleanly once you accept that
the split is the architecture and the rest is a scheduling decision. The platform is therefore:
**two append-only records per logical call, joined by a caller-minted `call_id`; enqueued in
microseconds; drained, dissected, indexed and mined off the request thread; projected into the
console through the poll that already runs; and read — for the first time — by a production
reader.** The reader is the part that has never existed, and it is the part everything else is
worthless without.

---

## 1. THE ARCHITECTURE, LAYER BY LAYER

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ RUNNER PROCESS  (scripts/bifrost_runner_deepseek.py, one worker thread at :1000)             │
│                                                                                              │
│  ┌── THE REQUEST THREAD ─ everything here is measured in microseconds ────────────────────┐  │
│  │                                                                                        │  │
│  │  [A] CALL BRACKET            scripts/deepseek_chat.py:301  (create() call site)         │  │
│  │      mint call_id + turn_id into a ContextVar; push model, policy fields               │  │
│  │      NEW: scripts/wire_ctx.py            ~0.1 µs   (INFER, pinned P-W1-7)              │  │
│  │                                                                                        │  │
│  │  [B] TRANSPORT HOOK          scripts/wire_journal.py:322-341 (_RecordingTransport)      │  │
│  │      ├ L2 request   : host, url_path (never query), method, req_bytes=len(content),    │  │
│  │      │                scheme, port, model (caller-pushed, NOT parsed)      ~0.1 µs     │  │
│  │      ├ L4 ladder    : 9-rung prefix digest over request.content, ONE pass,             │  │
│  │      │                .copy() per rung, capped 128 KB              ≤0.20 ms (H2)       │  │
│  │      ├ L0/L1 trace  : httpcore `trace` extension + network_stream.get_extra_info       │  │
│  │      │                → connect_ms, tls_ms, server_wait_ms, conn.reused,               │  │
│  │      │                  peer_ip, tls_cipher, peer_cert_sha256          <0.01 ms        │  │
│  │      ├ L2 response  : status, 9 allowlisted headers, ms_to_headers (perf_counter)      │  │
│  │      └ EMIT TRANSPORT RECORD  → enqueue                              ≤5 µs p99 (H1)    │  │
│  │                                                                                        │  │
│  │  [C] STREAM TEE              NEW class in scripts/wire_journal.py (SyncByteStream)      │  │
│  │      L3: per HTTP byte chunk → (t_rel, nbytes). No parse, no copy, yield the SAME      │  │
│  │      object; close() propagates; exceptions pass through   0.136 µs × ~10 = 1.4 µs     │  │
│  │                                                                                        │  │
│  │  [D] SEMANTIC STAMP          scripts/deepseek_chat.py:306-345 (the existing loop)       │  │
│  │      L5: per SSE chunk → ttfr, ttft, think_ms, max_gap, n_sse.                          │  │
│  │      One perf_counter (56.5 ns) beside a flushing print() at :336        ~2 µs         │  │
│  │                                                                                        │  │
│  │  [E] CLOSE HALF              scripts/deepseek_chat.py:346 (the existing `finally`)      │  │
│  │      outcome ∈ {complete, abandoned, error}; finish_reason, usage,                     │  │
│  │      system_fingerprint, response_id, messages_shape                                    │  │
│  │      EMIT CLOSE RECORD → enqueue                                     ≤5 µs (H6)        │  │
│  └────────────────────────────────────────────────────────────────────────────────────────┘  │
│                    │ queue.Queue(maxsize=10_000).put_nowait / except Full → dropped++         │
│                    ▼                                                                          │
│  ┌── THE DRAIN THREAD ─ one per process, atexit-joined, never a bare daemon ──────────────┐  │
│  │  NEW: scripts/wire_ring.py                                                              │  │
│  │  serialize (json.dumps 4.04 µs) → batch 512 → one write into a 1 MB buffered handle    │  │
│  │  flush ≤250 ms · fsync every 10 s and at clean exit · 2.91 µs/record, 343k rec/s        │  │
│  │  ANOMALY WRITE-THROUGH: non-2xx, error, outcome!=complete → synchronous flush           │  │
│  │  (<1 % of traffic; restores the shipped durability guarantee for the records that       │  │
│  │  matter, on calls that already failed — answers the "daemon loses the crash" objection) │  │
│  └────────────────────────────────────────────────────────────────────────────────────────┘  │
│                    │                                                                          │
└────────────────────┼──────────────────────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ THE SINK                                                                                     │
│   state/wire/wire-<agent>-<incarnation>-<date>.jsonl   (per WRITER, not per fleet)            │
│   BIFROST_INCARNATION already exists: bifrost_runner_deepseek.py:855, :1385                   │
│   double-gitignored: .gitignore:50 (*.jsonl) and :108 (state/*) — verified by git check-ignore│
│   Engine is a DRAIN-THREAD choice, invisible above (§6 slice W6 swaps JSONL → SQLite/WAL)     │
│                                                                                              │
│   RETENTION OWNER — a single fleet-wide verb, NOT an inline scan                              │
│   `py agent_cli.py wire --retain`, plus at-process-close guarded ≤1/hour                      │
│   enumerates ALL writers' files, one AGGREGATE byte budget, oldest-first, COUNTED             │
│   (kills D1, kills the orphan-file problem, kills 58 µs of listdir per record — one fix)      │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┬──────────────────────┬─────────────────────────┐
        ▼                          ▼                      ▼                         ▼
┌───────────────────┐  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────────┐
│ L4/L5 DISSECTOR   │  │ THE JOIN + MINING  │  │ LIVE PROJECTION    │  │ SECURITY PLANE      │
│ scripts/wire_     │  │ scripts/wire_      │  │ scripts/wire_      │  │ scripts/wire_       │
│   dissect.py      │  │   expert.py        │  │   live.py          │  │   guard.py          │
│ pure fn of L3     │  │ join transport+    │  │ byte-OFFSET tail   │  │ EGRESS-1 fields (in │
│ frame counts,     │  │ close on call_id;  │  │ (constant in       │  │ [B], ~0 cost)       │
│ coalesce ratio,   │  │ flows; baselines   │  │ journal size)      │  │ taint vector pulled │
│ gap distribution, │  │ (median+MAD, n≥8/  │  │ fixed time buckets │  │ from ToolBox getter │
│ [DONE] present,   │  │ 30/100 floors);    │  │ + measured_mask    │  │ delta DLP scan,     │
│ logprobs (opt-in) │  │ EI-00..EI-62;      │  │ 16-bucket log      │  │ content-addressed   │
│ per-dialect L5    │  │ cache break class  │  │ histogram; 200-rec │  │ memo; hash chain    │
│                   │  │ B1-B6; TTL interval│  │ ring; snapshot()   │  │ (~0.3 µs/record)    │
│                   │  │ compaction verdict │  │ ~200 KB resident   │  │ EGRESS cap (core/   │
│                   │  │ NO PRICES (§5.1)   │  │                    │  │ trust — GATED §6)   │
└───────────────────┘  └────────────────────┘  └────────────────────┘  └─────────────────────┘
        │                      │                        │                        │
        └──────────────────────┴────────────┬───────────┴────────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ THE READERS — named, because a writer without a reader is the defect                         │
│                                                                                              │
│  1. DOCTOR LINE     core/comm/doctor.py, beside _token_cost_line at :1069-1116                │
│                     exact precedent: :1099 does a guarded, function-local, read-only          │
│                     `from scripts.runner_token_journal import TokenJournal`, and :1114        │
│                     renders `UNPRICED (… — no rate in PRICES)` instead of a plausible number  │
│  2. BOOT ONE-LINER  agent_cli.py:395-402 already prints a DOCTOR line at boot; one insertion, │
│                     silent when clean. The only reader that runs without anyone deciding to.  │
│  3. CLI VERBS       `wire '<filter>'` · `wire flows` · `wire cache` · `wire dissect <call_id>` │
│  4. BIFROST UI      /api/now key "wire"; ONE import, ONE route, ONE dict key, TWO markup lines │
│                     Claude authors scripts/wire_live.py + scripts/wire-panel.js;              │
│                     DeepSeek owns the scripts/bifrost_ui.py integration (membrane holds)      │
│  5. PAGER           findings only, never packets. core/comm/pager.py:43 page / :67 clear_key  │
│                     CAP=50 at :20 — the wire journal's steady-state share is pinned ≤2 keys   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 What is reused rather than built

| Reused | Where | For |
|---|---|---|
| the `http_client=` SDK seam | `scripts/deepseek_chat.py:83-89` | the whole transport hook; already shipped |
| the existing `finally` in the stream loop | `scripts/deepseek_chat.py:346-348` | hanging the close-half emit on. It exists and does nothing but reset colour today |
| `BIFROST_INCARNATION` | `scripts/bifrost_runner_deepseek.py:855`, `:1385` | globally-unique writer identity — no new id scheme |
| the doctor's telemetry-reader pattern | `core/comm/doctor.py:1095-1116` | the production reader, verbatim shape incl. the visible-gap render at `:1114` |
| `/api/now` + its single poll scheduler | `scripts/bifrost_ui.py:3402` (`_nowPollMs = 2000`) | live transport. Zero new network chatter |
| the file-read-per-poll budget | `core/comm/engine_vitals.py:70-71` (*"Cheap (<=3 backend reads + 1 file stat)"*) | the projection's cost contract |
| `turn_metrics` statistics constants | `core/comm/turn_metrics.py:35-38` (`HISTORY_CAP=200`, `MIN_N=3`, `LOW_CONFIDENCE_N=8`, `EST_CACHE_TTL=30.0`), `:53-57` (`len_band` at 500/2000) | baselining. **Do not invent a second bucketing** |
| the cost-attribution chain | `core/comm/turn_metrics.py:112-144` → `core/coord/task_costs.py:74-93` `attribute_turn` | wire → `turn_id` → task → arc. The wire journal contributes one ContextVar read and nothing else |
| `PRICES` / `price_of` | `scripts/runner_token_journal.py:56-65`, `:79-82` (verified: pro prompt $0.55/M vs cached $0.055/M = **10x**) | the sole rate card. The wire plane holds no price literal |
| `pager` keys + retraction | `core/comm/pager.py:43`, `:67`, `CAP=50` at `:20` | alerting, with the nine-hour stale-page scar already designed around |
| the in-repo hot-path benches | `tests/manual/bench_wire_hotpath.py`, `tests/manual/bench_wire_shard.py` | the performance contract. **These already exist and two of six seats' greps missed them** (§4.3) |

### 1.2 The record model, stated as an invariant

The shipped pin W1 (`tests/test_t156_wire_journal.py:25`) says *one entry per HTTP round trip*.
That survives, restated so the two halves do not violate it:

> **W1′ — exactly one TRANSPORT record per HTTP round trip, emitted before `handle_request`
> returns; at most one CLOSE record per `call_id`, emitted from the caller's `finally`.
> A transport record with no close record IS the abandonment signature, not a hole.**

Why two append-only records and not one assembled record, or one row updated:

- Hot-path §5's single record "emitted at stream close" **deletes the events we care most about.**
  Today `wire_journal.py:338-340` lands the record before the caller iterates, so a call that
  streams for 600 s and is then abandoned still has status, headers and `x-ds-trace-id` on disk.
  Under emit-at-close it has nothing. `MODEL_READ_TIMEOUT = 120` exists at
  `scripts/deepseek_chat.py:62` *because streams stall.* Refuted and rejected.
- Storage §3.1's `UPDATE … WHERE call_id=? AND attempt=?` is correct in SQL and unavailable in
  JSONL, and it makes the engine decision a prerequisite of the correlation. The append-only pair
  makes the correlation available **tonight**, in the format already on disk, and matches Akasha's
  own physics.
- Mining §1.1 proposed exactly this and it is the version that survives. Adopted.

---

## 2. THE PERFORMANCE CONTRACT

### 2.1 What the request thread pays today — MEASURED HERE

I ran the repo's own bench against the shipped `WireJournal`, tonight
(`tests/manual/bench_wire_hotpath.py`, 4,000 calls per row):

| threads | mean µs | p50 µs | p99 µs | max µs |
|---|---:|---:|---:|---:|
| 1 | **220.2** | 183.4 | 621.8 | 4,577.5 |
| 4 | 1,379.5 | 1,333.2 | 3,040.3 | 5,228.7 |
| 8 | 2,773.7 | 2,743.8 | 6,770.8 | 10,612.5 |
| 20 | **6,924.4** | 6,816.7 | 15,876.0 | 26,596.9 |

Every microsecond of that is on the caller's thread, inside one process-global
`threading.Lock` (`scripts/wire_journal.py:83`, taken at `:95`), doing `os.makedirs` (`:96`),
`open`/`write`/`close` (`:98-99`) and `_rotate()` → `files()` → `os.listdir` + `sorted` +
`os.path.getsize` (`:100`, `:147-170`) — **per record.**

Honest label on the 20-thread row: that is 20 threads in ONE process, which is not today's
deployment (runners are separate processes; `bifrost_runner_deepseek.py:1000` spawns one worker).
It is the configuration a single-process season harness would create. In the multi-process
deployment the failure is different and worse — hot-path §2 measured **53.6 % of bytes lost** with
20 processes appending to the shared `wire-<date>.jsonl` on Windows, silently, raising nothing.

### 2.2 What the request thread pays under this architecture — MEASURED HERE

Same bench file, strategy C (bounded `queue.Queue.put_nowait`, one background writer,
`tests/manual/bench_wire_shard.py`), 20 threads:

| strategy | mean µs | p50 µs | p99 µs | max µs | dropped |
|---|---:|---:|---:|---:|---:|
| A monolith (**shipped**) | 7,705.3 | 7,376.8 | 19,212.8 | 28,620.9 | — |
| B sharded instances | 3,145.2 | 3,054.5 | 5,826.7 | 9,785.2 | — |
| **C async, 1 writer** | **0.9** | **0.6** | **3.2** | 473.9 | **0** |
| D sharded + async | 0.7 | 0.6 | 1.7 | 37.2 | — |

### 2.3 The budget

Per HTTP round trip, on the request thread:

| # | Item | Budget | Basis |
|---|---|---:|---|
| **H1** | transport-half enqueue: 22-field tuple, 9 header `.get()`s, anomaly predicate, `put_nowait` | **≤ 5 µs p99** | MEASURED-HERE 0.9 µs mean / 3.2 µs p99 (bench C, 20 threads); hot-path component measures: tuple 0.019 µs, header pull 0.112 µs, predicate 0.047 µs, seq 0.032 µs |
| **H2** | prefix ladder over `request.content`, one pass, ≤128 KB, 9 `.copy()`s | **≤ 0.20 ms** | capture MEASURED sha256 at 0.275 ms / 716 KB ⇒ 2.6 GB/s ⇒ 128 KB ≈ 0.05 ms. blake2b UNMEASURED — pinned |
| **H3** | L3 tee, per HTTP byte chunk | **≤ 0.5 µs/chunk**, ~10 chunks ⇒ 1.4 µs | capture MEASURED 0.136 µs/chunk (variant a) |
| **H4** | L5 stamp, per SSE chunk, in the existing loop | **≤ 0.2 µs/chunk**, ~35 chunks ⇒ 2.0 µs | capture MEASURED `perf_counter` at 56.5 ns. Sits beside a *flushing* `print()` at `deepseek_chat.py:336` — three orders of magnitude larger |
| **H5** | `call_id`/`turn_id` ContextVar reads | **≤ 1 µs** | mining estimate ~0.1 µs. UNMEASURED — pinned |
| **H6** | close-half enqueue | **≤ 5 µs** | same mechanism as H1 |
| **H7** | L0/L1 httpcore trace callbacks, 13/request | **≤ 0.01 ms** | capture MEASURED `<0.010 ms`; free when the extension is absent (`httpcore/_trace.py`, `should_trace`) |
| | **TOTAL ADDED** | **≤ 0.22 ms worst case; ~15 µs with the ladder off** | |
| | **REMOVED** | **−220 µs (1 thread) / −6,900 µs (20 threads)** | MEASURED-HERE, §2.1 vs §2.2 |
| | **NET** | **negative at every concurrency measured** | |

Against a MEASURED-HERE p50 `ms_first_byte` of **1,153 ms** over the 58 live records
(`state/wire/wire-20260804.jsonl`, min 638 / max 1,780), 0.22 ms is **0.019 %**.

**The headline, stated the way it survives attack:** this platform captures the connection, the
transaction, the request body shape, per-chunk stream timing, the semantic close, and a security
destination record — and it *reduces* request-thread work, because everything expensive was
already being done in the wrong place. That claim is measured against two configurations that
exist, not one that does not. Hot-path's "660x" is CUT (§4.1 R7).

### 2.4 The benchmark pin

Primary pin is **structural and timing-free**, because a microsecond assertion on shared CI is a
flaky test and a flaky perf test gets deleted:

- **P-BUDGET-1 (the real one).** Monkeypatch `os.makedirs`, `os.listdir`, `os.path.getsize` and
  `builtins.open` to raise; drive 100 round trips through the recording transport; assert 100
  successful responses **and** that 100 records reach the sink after the drain unblocks. The hot
  path must be incapable of touching the filesystem. Fails today against `wire_journal.py:96-100`.
- **P-BUDGET-2 (ratio, not absolute).** In one process, in one run: `calib = median(20,000 ×
  perf_counter_ns())`; `delta = median(recording transport) − median(null transport)` over 20,000
  synthetic round trips; assert `delta / calib < K`. K is set from the machine it was taken on and
  **the calibration constant and the machine are recorded in the test** (method-baseline receipts
  rule). Absolute-µs assertions are forbidden.
- **P-BUDGET-3.** `tests/manual/bench_wire_hotpath.py` and `bench_wire_shard.py` are promoted from
  `tests/manual/` to a `--bench` marked test and their outputs are the receipt. They already exist,
  they already measure exactly this, and **two of six design seats' greps did not find them.**

### 2.5 What violated the budget and what I cut

| Proposal | Violation | Disposition |
|---|---|---|
| capture §4 `req.prefix_sha[]`, naive per-boundary sha256 | MEASURED 3.87 / 11.08 / 22.04 ms at 20 / 60 / 120 message boundaries — up to **20x the entire budget**, quadratic in message count | **CUT.** Replaced by mining's one-pass 9-rung ladder with `hashlib.copy()`, capped at 128 KB. Fixed cost, not quadratic |
| hot-path §3 bounded digest over a reconstructed prompt string | The string does not exist; producing it means joining `self.messages` on the request thread — 45 MB worst case (`deepseek_chat.py:207-208`, 11.4 M tokens over 127 hops). The hash was priced; the materialization was not | **CUT.** Digest `request.content`, which capture VERIFIED is already memoized bytes and idempotent to read. Zero materialization |
| hot-path §7.2 eight folded integers from one 0.131 µs site | The transport sees **10 byte chunks**; SSE-message semantics (reasoning vs content) live at `deepseek_chat.py:314-334`. One site cannot produce them | **SPLIT AND RE-PRICED** as H3 + H4 |
| hot-path §7.3 64-slot per-call chunk-trace ring | ~1.6 µs unbudgeted (~31 % of its own headline) | **DEFERRED** to a later slice. Lowest capture value, highest fiddliness |
| capture §7 option (A) live background SSE parse | 10.502 µs/frame `json.loads` moved to a thread that competes for the GIL during the exact window the operator waits on tokens | **CUT for v1.** Default is post-hoc (option B). L4/L5 are pure functions of L3's output |
| capture §1.4 logprobs on by default | 2.19x stream bytes ⇒ 2.19x SSEDecoder + `json.loads` on the consumer's own thread, and it **mutates the production request** | **OFF by default; operator ruling** (§6.2) |
| storage §5.1 `wire_anomaly` as a never-expiring copy table | An unpriced second INSERT on ~14 % of rows, with no line in its own budget | **DEFERRED** with the engine (slice W6) |
| storage §3.2 eight indexes, five measured; two on permanently-NULL columns | MEASURED +8.8 µs/row and +13.4 B/row for an index that can never return a row. `arc` has no producer; `prompt_prefix_sha` is 0/58 on real records | **RULE ADOPTED: no index without a producer** — the exact shape of *no writer without a reader* |
| per-record `_rotate()` retention | `os.listdir` + `sorted` + `getsize` on every record (58 µs measured by hot-path, 53 µs by storage). Per-writer files would make it 20 processes × a growing directory | **MOVED OFF THE PATH ENTIRELY** to the fleet retention verb |

---

## 3. WHAT WE CAN NEWLY UNDERSTAND

Ranked by (money or run-validity at stake) × (probability it is happening now) ÷ effort. Each entry
names the **inference**, not the field.

### 3.1 Localize a cache break to a message index — the money finding
**Capture that makes it possible:** the 9-rung prefix ladder over `request.content` (H2) +
`cache_hit_tokens` from the close half + caller-pushed `messages_shape`.

**The inference:** `i* = min{i : ladder[n][i] ≠ ladder[n−1][i]}` brackets the break to a factor of
two; a cumulative-length walk over `messages_shape` maps that byte range to a message index `j`.
That splits four causes which today all present identically as "hit rate dropped":

- **B1 head mutation** (`j == 0`) — one volatile token at the head destroys 100 % of the cache.
- **B3 compaction** — we chose it; §3.2 says whether it paid.
- **B4 mid-history edit** (`0 < j < len−2`) — almost always a bug; histories should be append-only.
- **B5 provider eviction** — ladder *identical*, `cache_hit_tokens == 0`. **We did not break it;
  they dropped it.** The remedy is not "fix the prompt", it is "shorten the idle gap."

Four different fixes. Without the ladder they are one symptom.
**Stake:** `runner_token_journal.py:57-60` — $0.55/M fresh vs $0.055/M cached, a **10x** ratio,
verified. Against the 393 M-token measurement at `deepseek_chat.py:207-208`, every 10 percentage
points of hit rate is **~$19.45**.

**A guard that comes with it:** p3 ran the same 23-token prompt twice and got `cache_hit = 0` both
times. Three identical-prefix runs, zero cache, **no defect** — the prompt was below the provider's
block granularity. So all cache findings are suppressed below `CACHE_MIN_BLOCK` (ASSUMED = 64, not
measured), and the suppression itself renders as an `info` finding so the operator sees *why* the
panel is quiet.

### 3.2 Whether a compaction saved money or cost money — per event, in dollars
**Capture:** ladder (gives the retained fraction `f`) + flow segmentation (gives realized turns `T`)
+ `price_of()`.

**The inference,** derived entirely from the repo's own rate card with `r = 0.55/0.055 = 10`:

> trimming to a retained fraction `f` only pays if at least **9f/(1−f)** more turns will follow.

| turns remaining `T` | trimming pays only if you retain less than |
|---|---|
| 1 | **10 %** |
| 5 | 35.7 % |
| 9 | 50 % |
| 20 | 69 % |

Every instinct in this codebase says "the context is too big, trim it"
(`deepseek_chat.py:209-211` names the driver). For a conversation with one or two turns left,
front-trimming is close to **always wrong while the cache is warm**, because trimming the front IS
a B1 head mutation. That is counter-intuitive, computable from the journal retrospectively, and
nobody has been able to check it. It is a cost-floor comparison, not a decision oracle — it ignores
quality and prefill latency.

### 3.3 Learn the provider's cache TTL with zero extra API calls
**Capture:** ladder equality across a flow + inter-call gap.
**The inference:** `max_hit_gap` = largest gap that still hit; `min_miss_gap` = smallest gap that
missed with an identical prefix. TTL ∈ `[max_hit_gap, min_miss_gap]` — **an interval, never a point
estimate.** If the interval inverts, eviction is capacity-driven rather than time-driven and the
remedy changes again. This is a natural experiment already sitting in traffic we pay for.

### 3.4 The silent model swap — the only thing that can invalidate a whole season
**Capture:** `system_fingerprint` from the close half. Today **0/58 populated.**
**The inference:** the observed value decomposes —
`fp_9954b31ca7_prod0820_fp8_kvcache_20260402` reads as
`fp_<hash>_prod<MMDD>_<quant>_<feature>_<YYYYMMDD>` — so a change can be classified as "config hash
moved" vs "quantization changed from fp8" vs "build date advanced" (**INFER from ONE sample**; the
parse must fail soft to an opaque comparison, never to a claim).

The second-order inference is the valuable one: **a step change in think-share at a fingerprint
boundary is the provider changing the reasoning economy, not the tasks getting harder.** Without the
fingerprint, that is an unfalsifiable story about agent quality. `wire_journal.py:23-26` states the
stake and it is precisely a champion-challenger season.

The sound claim is *"any comparison spanning this boundary is invalid"* — never *"the model was
swapped"* (a routine redeploy of identical weights changes the fingerprint). The shipped hedge at
`wire_journal.py:261-263` ("**may** have swapped") is doing real work and must survive any rewrite.

### 3.5 Reasoning starvation, deterministically, at n=1
**Capture:** `finish_reason` + `reasoning_tokens` + `completion_tokens` from the close half.
**The inference:** `finish_reason == "length"` AND `reasoning_tokens == completion_tokens` AND empty
content ⇒ **the think budget ate the entire answer.** Ground truth is committed:
`p4-forced-truncation.json` shows `max_tokens=8 → completion 8 / reasoning 8 / content "" /
finish_reason "length"`. The triad is exact, has no false positives by construction, and costs
nothing.

Today this incident class (`runner_reasoning_eats_final_answer`, named at `wire_journal.py:30-32`)
is caught **heuristically and late**, by `bounce_promise()` inspecting whether the reply *looks like
a promise* (`bifrost_runner_deepseek.py:145-157`). This converts a text heuristic into a fact.

### 3.6 "The model was slow" vs "we re-handshaked"
**Capture:** httpcore `trace` extension + `network_stream` (L0/L1).
**The inference:** `ms_first_byte` today is **time-to-first-HEADER** and silently bundles
DNS + TCP + TLS + request send + server wait. Capture MEASURED the decomposition on a loopback
server with injected delays and recovered a 250 ms server wait and a 150 ms headers→first-byte to
**better than 0.4 ms**. Nobody can currently tell whether a 1,153 ms p50 spent 900 ms in the model
or 900 ms in a cold TLS handshake.

MEASURED-HERE: **31 distinct `x-amz-cf-pop` values across 58 records** (top: IAD12-P1 ×6,
ATL59-P18 ×5). Three hypotheses fit — reuse is failing, edge selection varies per connection, or
many short-lived processes each pay one handshake (`make_client` is called once per process,
`deepseek_chat.py:66`). **The journal cannot distinguish them because it carries no pid and no
`conn.reused`.** That is the sharpest single argument for the correlation key in this document.

### 3.7 Context runaway visible while it runs
**Capture:** `prompt_tokens` + `completion_tokens` + `reasoning_tokens`, per call.
**The inference:** `thought_density = (completion − reasoning) / prompt` — answer produced per unit
of context. The 11.4 M-token / 127-hop turn (`deepseek_chat.py:207-208`) is *enormous prompt,
ordinary answer*: `thought_density` collapses while it happens, instead of surfacing in a post-mortem.
Paired with `think_share` rising and `policy_hash` held fixed, it discriminates context bloat from
task-difficulty drift.

### 3.8 Tokens we paid for and never counted
**Capture:** the transport half, which exists whether or not the call completed.
**The inference:** `bifrost_runner_deepseek.py:1108-1111` calls `add_turn` only when `delta` is
truthy, and `delta` is computed from `ag.prompt_tokens` around a `send()` **that must have
returned**. So every token spent on a call that timed out or died mid-stream is **structurally
invisible to `TokenJournal`.** The wire journal sees the attempt and can state an **upper bound**.
It must render as a bound in a separate column and **must never sum into `cost_est`**
(`runner_token_journal.py:193`). A bound inside a total is a lie wearing a measurement's clothes.

### 3.9 Where our bytes actually went
**Capture:** EGRESS-1 — `host`, `url_path` (never `query`), `method`, `req_bytes =
len(request.content)`, `scheme`, `port`. All attribute reads on an object the transport holds.
**The inference:** bytes-out per agent per host per day — the one number an exfiltration monitor is
built around. Today the record has **no destination field at all**, and `agent` is `"unknown"` on
**58/58** records (MEASURED-HERE). `scripts/gemini_chat.py:43-46` reads `BASE_URL` from the
environment, so a runner's traffic can be redirected by anything that can set an env var, and the
journal would record that as an indistinguishable success.

### 3.10 Two things we already capture and have never once read
MEASURED-HERE, the kept header set is exactly
`{content-type, server, x-ds-trace-id, x-cache, x-amz-cf-pop}` on 58/58 records.

- **`x-amz-cf-pop`** is the natural partition for a latency anomaly that is CDN-side rather than
  model-side — and it is the confounder that makes naive latency alerting worthless *and* the
  covariate that rescues it. Pure reader work, zero capture cost.
- **`x-ds-trace-id`** is 58/58 populated and 58/58 distinct — the handle the provider's support
  needs (`wire_journal.py:35-36`) — and no surface anywhere shows it to a human.

Also free: `req_bytes` per hop within one turn is the direct meter for the cost driver named at
`deepseek_chat.py:207-211`, at literally zero marginal cost, and it is absent from every design's
final record.

### 3.11 The floor of the visible stack (deepest, lowest priority)
`p1-logprobs-stream.json` proves DeepSeek streams **top-3 logprobs on the REASONING channel** under
`stream=True`, at zero token cost. A reasoning phase whose logprobs collapse is a *measurable*
model-confusion signal. Costs 2.19x stream volume and consumer-side parse. **Operator ruling; off by
default.**

---

## 4. WHAT THE VERIFIERS KILLED

Nothing below is dropped quietly. Format: claim → why it died → what this architecture does.

### 4.1 Hot-path (10 refutations, 5 perf violations)

| # | Killed claim | Disposition |
|---|---|---|
| R1 | "One record, both halves, emitted at stream close" is a pure fidelity gain | **REJECTED.** It is a coverage *regression*: abandoned streams — the 120 s stall, the 600 s incident, the highest-value forensics in the corpus — emit nothing, where `wire_journal.py:338-340` records them today. Replaced by two append-only records + a `finally`-anchored close half with an explicit `outcome` |
| R2 | The 2–120 s stall band is "exactly where the F5 600-second incident lives" | **STRUCK.** The cited source says the opposite: a 600 s timeout is a turn-level deadline, not a chunk-gap timeout. The adaptive stall threshold survives on its own merits; the incident attribution does not |
| R3 | Per-PID files: "the reader needs a wider glob, nothing more", cost "negative" | **HALF-ADOPTED.** Per-writer files KEPT (0.00 % loss vs 53.6 %). But `MAX_FILES=14` × `MAX_BYTES=8 MB` × 20 writers is 2.24 GB against an intended 112 MB, and dead-writer files have no owner. **Retention moves to one fleet-wide verb with one aggregate byte budget, oldest-first, counted.** Filename becomes `<agent>-<incarnation>-<date>` using the existing `BIFROST_INCARNATION` |
| R4 | `observe_chunk` yields 8 integers from one site at 0.131 µs | **SPLIT.** 10 byte chunks ≠ 35 SSE messages. Two instruments, two prices (H3, H4) |
| R5 | `sha256(len ‖ head4k ‖ tail4k)` is "the default" digest | **REJECTED.** It destroys prefix-comparability, which is the entire stated purpose of `prompt_prefix_sha` (`wire_journal.py:34`, `:267-270`). Replaced by the ladder, which is prefix-comparable at every rung by construction |
| R6 | "Records lost without being countable = 0" | **QUALIFIED.** (a) A seq gap conflated telemetry loss with call abandonment — fixed by making `outcome` an explicit recorded value, so the gap becomes unambiguous. (b) `len(ring)` + `append` is a check-then-act race — fixed by using `queue.Queue.put_nowait` + `except Full` instead of a deque length check. Measured cost of that choice: **0.9 µs** (bench C), so the "18x penalty" is irrelevant at this scale |
| R7 | "20x single-threaded, **660x** at p50 under contention" | **HEADLINE CUT.** 660x compares against a configuration the same document says does not exist. Replaced with MEASURED-HERE numbers against two configurations that do: 220 µs → ~1 µs at 1 thread, 6,924 µs → 0.9 µs at 20 in-process threads |
| R8 | "17 of 23 fields structurally always null" | **CORRECTED, MEASURED-HERE:** 24 keys, **18** always null, 6 populated, n=58 |
| R9 | "Today's inline hash costs 381.5 µs on a 400 KB prompt" (framed as a live cost) | **CORRECTED.** Nobody pays it — no production caller passes `prompt_text`, and `prompt_sha` is 0/58. The hazard belonged to the *proposal*. Eliminated by hashing `request.content` |
| R10 | `t_request_sent = perf_counter_ns()` at `wire_journal.py:325` | **CORRECTED.** `:325` is `t0 = time.time()`, and `:331`/`:340` truncate to int ms. Moving all durations to `perf_counter` is free and strictly better; adopted in slice W0. (Clock-resolution contradiction recorded at §7.2 C1) |
| V1 | 64-slot chunk ring unbudgeted (~31 % of the headline) | DEFERRED |
| V2 | Body materialization unpriced (potentially 45 MB on the request thread) | KILLED — digest `request.content` |
| V3 | SSE-message granularity unpriced | RE-PRICED as H4 |
| V4 | Drain budget excludes retention; per-PID ⇒ ~80 listdir+stat storms/s fleet-wide | KILLED — retention leaves the record path entirely |
| V5 | `self._last` attempt inference is unsynchronised shared state, and `attempt > 0` gates the anomaly ring | **THE HEURISTIC IS DELETED, NOT TUNED.** Replaced by counting transport records per `call_id` — a retry becomes *observed*, not inferred. Interim (slice W0): emit `attempt_kind: "INFERRED"` so the label survives to the reader |

### 4.2 Capture (9 refutations, 7 perf violations)

| # | Killed claim | Disposition |
|---|---|---|
| R11 | "`model` is null because the transport reads `x-model` at `:332`" | **MISDIAGNOSED.** `:332` is inside the `except` branch; all 58 live records are status 200 / attempt 0, so that line has **never executed**. The success path `:338-340` passes no `model` at all. Both are fixed, and `model` is **caller-pushed, never parsed** — `json.loads` on a 716 KB body is 0.74 ms and the caller already holds `self.model` (`deepseek_chat.py:277`) |
| R12 | "`grep wire_journal` returns exactly three hits" | **FALSE — five hits, four files.** I reproduced the correct grep. The two missed files are `tests/manual/bench_wire_hotpath.py` and `bench_wire_shard.py`, the hot-path benches that measure exactly the cost this budget is about. I ran both (§2.1, §2.2). A section titled *"a writer without a reader is the defect"* failed to find two existing readers |
| R13 | "the record roughly doubles to ~1.3 KB" | **TRUE ONLY AT ~20 MESSAGES.** At 120 it is 3,855 B (5.5x), shrinking the forensic retention window 5.5x. `messages_shape` is **capped** (head N + tail N + totals) and record size becomes a pin |
| R14 | "19 distinct PoPs ⇒ either reuse is failing or edge selection varies" | **FALSE DICHOTOMY.** A third explanation — many short-lived processes, one handshake each — fits and is cheaper. The record has no pid to distinguish them. Adopted as the argument for the correlation key (§3.6). Numbers refreshed MEASURED-HERE: 58 records, **31** PoPs, p50 1,153 ms |
| R15 | "Per-PoP TTFH medians range 638–1,347 ms" | **STRUCK.** Those are min and max of n=1 samples relabelled as medians. No per-PoP estimate is supportable at n=1–6 |
| R16 | Cross-document line citations | **4 of 5 drift 2–9 lines; the httpcore `_trace.py` `:27`/`:28` pair is transposed.** Diagnostic split: every citation into **Python source** verified clean in both the verifier's check and mine; every drifting citation pointed at **prose**. Build rule: cite source, not summaries |
| R17 | "16 headers; two of nine `KEEP_HEADERS` are dead" | **CORRECTED.** 15 headers (line 1 is `# HTTP 200`), and **four** of nine are absent on 200s. MEASURED-HERE the kept set is exactly 5. The four dead entries (`x-request-id`, `retry-after`, both `x-ratelimit-*`) are **kept anyway** — they are the ones that fire when things break, and we have never observed a non-2xx |
| R18 | `req.tools_bytes = 16,775` | **CORRECTED.** Measured with default `json.dumps` separators; the SDK ships compact JSON at 16,019 B. `req_bytes` must come from `len(request.content)`, never from re-serializing `TOOLS` |
| V6 | `req.prefix_sha[]` naive is 3.87–22.04 ms, quadratic | KILLED — one-pass ladder (§2.5) |
| V7 | The budget omits the write it builds on (0.189–0.576 ms) | ADOPTED — it is line 1 of §2.3 as the thing being *removed* |
| V8 | `_rotate()` does directory I/O per record | KILLED |
| V9 | The lock is a fleet-scale serialisation point | KILLED by the queue (MEASURED-HERE: 7,705 → 0.9 µs at 20 threads) |
| V10 | No stated path from the tee's data (available at close) to the record (written at header time) | **RESOLVED** by the two-record model and the restated W1′ invariant (§1.2) |
| V11 | Logprobs priced as bandwidth only | ADOPTED — consumer-side CPU counted; operator ruling |
| V12 | Live SSE parse competes for the GIL while the operator waits on tokens | CUT for v1 — post-hoc dissection is the default |
| V13 | The end-to-end A/B is noise-dominated (−1.632 / +2.473 / +0.952 ms on identical code) | ADOPTED. §2.3 uses only reproducible in-repo benches plus component microbenchmarks, and names every unmeasured line |

### 4.3 Storage (12 refutations; its perf-violation list reached me truncated — §7.1)

| # | Killed claim | Disposition |
|---|---|---|
| R19 | "SQLite is not a cost to mitigate but a **2.8x speedup** (235 µs → 85 µs)" | **HEADLINE CUT, and the repo already had the counter-evidence.** `tests/manual/bench_wire_shard.py` strategy C — async JSONL — costs **0.9 µs** caller-side (MEASURED-HERE), against SQLite's own proposed 2.17 µs hot path. **The hot-path win belongs to the QUEUE, not to the engine.** SQLite's honest case is reads, correlation and retention |
| R20 | "grep returns exactly three call sites" | **FALSE — five.** The same error as R12, about the same two files, made independently by a second seat. That is itself a finding (§7.3) |
| R21 | "`tests/test_t156_wire_journal.py:31-38` pins W1–W7" | **CORRECTED:** W1 is at `:25`, W7 ends at `:33` (verified) |
| R22 | "an index on an all-NULL column is free but useless" | **MEASURED FALSE:** +8.8 µs/row and +13.4 B/row. Two of eight proposed indexes are on permanently-NULL columns. **Rule adopted: no index without a producer** |
| R23 | `wire_prefix` "serves cache forensics" | Its column is NULL on **58/58** real records (MEASURED-HERE), so the flagship filter returns zero rows on every real record today. Covered by R22's rule |
| R24 | `call_id` "retries SHARE it", synthesised from the trace id for history | **INTERNALLY CONTRADICTORY.** Trace ids are per round trip (58/58 distinct, MEASURED-HERE), so a trace-derived `call_id` is unique per attempt and `UNIQUE(call_id, attempt)` degenerates. **`call_id` is minted by the caller at the `create()` bracket**, never derived. Historical rows get `call_id = trace_id`, `attempt = 0`, and an explicit `call_id_source: "synthesised"` marker |
| R25 | The storage-engine sweep's verdict ("five processes, ~9 MB, read-dominated") is "our profile" | **SCOPE VIOLATION.** This profile is 20 processes, 765 MB–2 GB, write-dominated — and the sweep's own author flagged that reframe as suspect. The engine decision does not rest on it; it rests on storage's own 20-process measurement, and it is deferred either way |
| R26 | "One database, not one per agent — SQLite's `MAX_ATTACHED=10` means sharding would not even work" | **STRAWMAN, and it contradicts a recorded operator steer** quoted verbatim at `tests/manual/bench_wire_shard.py:1`: *"multiple instances of things for performance reasons instead of one monolith."* Cross-shard queries need iteration or UNION, not 20 simultaneous ATTACHes. **Architecture is sharded at the write layer, unified at the read layer** — which also matches the measurement (D sharded+async 0.7 µs beat C 0.9 µs) |
| R27 | "both the before and after are noise against an 850 ms TTFB" | **SELF-CANCELLING** with the 2.8x headline. The argument that is *not* noise — concurrency — was never run. I ran it: 220 → 6,924 µs from 1 → 20 threads |
| R28 | D3 cited at `:238` | **CORRECTED to `:236`** (verified: `s = self.summarize(limit)`) |
| R29 | `wire_anomaly` tier vs `wire_anom` partial index | Cannot be the same object; if it is a copy table it is an unpriced second write. **DEFERRED with the engine** |
| R30 | "≈90k prompt tokens per HTTP call" | Uses the **worst** turn's per-hop rate as a fleet mean, so the derived volumes are **floors**, structurally biased toward undersizing. Season sizing is relabelled a floor, and the engine trigger is defined on **observed** record count (§5, W6) |
| **V16** | The drain thread is a daemon; anything queued at interpreter exit is gone, and `dropped` counts only queue-FULL overflow — trading a guaranteed-durable write for a lossy one on exactly the crash a forensics journal exists to capture | **THE SHARPEST OBJECTION IN THE SET.** Answered three ways: (a) `atexit` — stop, drain, flush, fsync, join with a 2 s cap; **not a bare daemon**; (b) **anomaly write-through** — any record failing the anomaly predicate (non-2xx, error, `outcome != complete`) is written synchronously with a flush, restoring the shipped durability guarantee for exactly the records that matter, on calls that already failed, at <1 % of traffic; (c) seq gaps + `outcome` make any residual loss countable and unambiguous |

### 4.4 D1 — the defect that outranks the entire design

`scripts/wire_journal.py:155-161`, verbatim:

```python
if files:
    newest = files[-1]
    if os.path.getsize(newest) > MAX_BYTES and len(files) > 1:
        os.remove(files[0])          # deletes the OLDEST because the NEWEST is too big
```

Reproduced by the storage seat against the shipped module: **14 days of history destroyed in 13
records**, one day per record, while the file the cap was written to bound kept growing. The
docstring at `:58-59` — *"Oldest file is dropped, newest always survives"* — describes the inverted
behaviour as the intent, which is worse than no docstring, because the reader stops checking.

**This is data destruction, it is live, and it is a two-line fix. It ships in slice W0 regardless of
whether anything else in this document is adopted.**

---

## 5. BUILD ORDER

RED-first per `docs/method-baseline-2026-07.md` (M3): every pin below is pre-registered, and the
ones marked **RED** fail against the code as it stands tonight.

### W0 — Stop the bleeding, and get a reader ★ HIGHEST VALUE PER EFFORT
**Size:** one sitting. ~150 lines in `scripts/wire_journal.py`, one line in `core/comm/doctor.py`,
one new test file. No new module, no thread, no engine decision.

**Delivers:**
1. **Fix D1** — the byte bound deletes *its own* oldest, in a `while` until under budget, never
   below `MIN_RETAIN_ROWS`, and **every deletion is counted** into a new `expired_records`.
2. **Delete the dead `x-model` read** (`:332`, the only occurrence repo-wide) and pass a
   **caller-pushed** `model` on both the success and error paths.
3. **Label the retry heuristic** — keep `attempt`, add `attempt_kind: "INFERRED"`, and change
   `expert()`'s wording at `:244-245` from *"the SDK re-sent inside one call"* (a statement of fact)
   to *"≤N repeat-shaped round trips (INFERRED)"*. The heuristic's own docstring at `:305-310` is
   honest; the label is lost by the time a human reads it.
4. **Correct clocks** — all durations from `perf_counter`; `time.time()` only for the `ts` stamp at
   `:112`. Add `ms_to_headers` under its true name; keep `ms_first_byte` so the 58 records on disk
   stay comparable.
5. **Every zero-cost field** — `host`, `url_path` (never `query`), `method`, `scheme`, `port`,
   `req_bytes = len(request.content)`, `pid`, `incarnation`, `seq`, `call_id` slot.
6. **Attribution** — `recording_http_client(agent=...)` passed explicitly at
   `deepseek_chat.py:86`, so 58/58 `"unknown"` becomes attributable. Marked **SELF-DECLARED, not
   verified** — the recorder lives in the agent's own process.
7. **Per-writer filenames** — `wire-<agent>-<incarnation>-<date>.jsonl`, using
   `BIFROST_INCARNATION` (`bifrost_runner_deepseek.py:855`). Kills the 53.6 % multi-process byte
   loss. Retention moves to a `wire --retain` verb.
8. **EI-00 and the production reader** — `expert()` reports **COVERAGE before FINDINGS** and may not
   say "no anomalies" while diagnostic fields are >20 % null; and a doctor line calls it, following
   `core/comm/doctor.py:1095-1116` exactly.

**Pins:**
- **P-W0-1 (RED)** — seed 15 files, oversize today's; drive 20 records; assert no history file is
  deleted while the aggregate is under budget, and `expired_records` counts every deletion.
- **P-W0-2 (RED)** — `expert()` over a fixture copy of tonight's live 58-record journal returns a
  coverage `error` and does **not** return `("info", "no anomalies", …)`.
- **P-W0-3 (RED)** — AST/grep: `x-model` appears zero times in the repo.
- **P-W0-4 (RED)** — a record carries `host`, `url_path`, `req_bytes`, `pid`, `seq`; driving a URL
  with `?key=SECRET`, `request.url.query` appears in **zero output bytes**. (security S2)
- **P-W0-5 (RED)** — `expert()` is reachable from a real CLI verb, asserted by invoking it. This is
  the anti-T140 pin. **Verified tonight: `expert()` has zero callers anywhere in the repo**;
  `summarize()`'s only callers are `wire_journal.py:236` and `tests/test_t156_wire_journal.py:113,124`.
- **P-W0-6 (green, held)** — `git check-ignore` still excludes `state/wire/**`, computed rather than
  read. Verified tonight: `.gitignore:108 state/*`. One careless negation publishes repo content to
  a PUBLIC repo. Highest-severity pin in the set. (security S3)
- **P-W0-7 (green, held)** — `Authorization` / `api-key` / `x-api-key` never appear in an output
  byte, with a deliberately injected header. `tests/manual/bench_wire_hotpath.py:78` already checks
  this ad hoc and it passes; promote it to a pin. (security S1)

**Why highest value-per-effort:** it stops active data destruction, removes two fields that *lie*
(a dead read that renders as MEASURED-absent, and an inferred count rendered as fact), adds every
field that costs nothing, and — for the first time in this journal's life — gives it a reader. Every
later slice depends on the correlation key and the reader existing.

### W1 — The two halves and the queue (the spine)
**Size:** medium. One new module (`scripts/wire_ring.py`), edits to `wire_journal.py` and to the
stream loop at `deepseek_chat.py:306-348`.

**Delivers:** `call_id`/`turn_id` minted in a ContextVar at the `create()` bracket (`:301`); the
transport half unchanged in timing; **the close half emitted from the existing `finally` at `:346`**
carrying `outcome ∈ {complete, abandoned, error}`, `finish_reason`, full `usage`,
`system_fingerprint`, `response_id`, `ttft/ttfr/think_ms/max_gap/n_sse`. `record()` becomes an
enqueue; one drain thread with `atexit`; anomaly write-through.

**Pins:**
- **P-W1-1 (RED)** — the correlation lands: against a stub that streams and then reports usage, the
  joined view has `finish_reason` **and** `status` **and** `x-ds-trace-id`. Fails today: 0/58.
- **P-W1-2 (RED)** — abandonment is *recorded*: kill the stream mid-iteration; assert a close record
  with `outcome="abandoned"` **and** that the transport record still landed.
- **P-W1-3** — accounting identity: `enqueued == written + dropped + in_queue`, exactly, at 100,000
  records with the drain paused.
- **P-W1-4 (RED)** — P-BUDGET-1 (§2.4): the hot path cannot touch the filesystem.
- **P-W1-5** — P-BUDGET-2 ratio pin.
- **P-W1-6** — `attempt` is MEASURED (count of transport records per `call_id`); the inferred
  heuristic and `self._last` are gone.
- **P-W1-7** — ContextVar propagation survives the SDK's retry loop, asserted against the stub.
  This is the load-bearing unverified assumption of the whole join (§7.4).

### W2 — The live surface
**Size:** medium. `scripts/wire_live.py` + `scripts/wire-panel.js`, plus the three-line handover.

**Delivers:** byte-offset tail (constant in journal size), fixed time buckets (`live` 1 s × 120,
`pulse` 60 s × 60, `session` 300 s × 288) each carrying a **`measured_mask`** so a bucket where
`finish_reason` was never present reports `trunc: UNKNOWN` rather than `0`, a 16-bucket log-scale
TTFB histogram, a 200-record detail ring, `snapshot()` → plain dict. Zones 1–3: the fingerprint
band, the pulse, the four-number ribbon. Rides `/api/now` — **no second poller, no second SSE, no
new Redis key.**

**Pins:** P3 O(1) in journal size (snapshot against a 100k-record journal within 2x of a 1k-record
one); P4 ≤5 ms p95; **P5 no false zeros** — with `finish_reason` 0/N populated, `truncated` must be
`UNKNOWN`, which fails today against `wire_journal.py:216`; P7 bounded DOM (≤400 elements after
5,000 records); P10 degrade-never-break (`state/wire/` deleted / unreadable / filled with garbage →
`/api/now` still 200 with `wire: {}`); P11 no new poller; P12 no money symbol in the panel.

### W3 — Expert Info and baselining
**Size:** medium-large. `scripts/wire_expert.py`.

**Delivers:** the rule set — **deterministic rules first** (EI-00/01/02, 10/11/12, 20/21/22/24,
30/40/41/42, 50/51/53, 60), statistical rules only where the sample floors are met. Two severity
ladders kept **deliberately separate**: mixing them is how one noisy latency alert teaches the
operator to ignore the truncation alert next to it. Baseline key
`(agent, model, ask_kind, len_band, system_fingerprint, policy_hash)`, median + MAD, empirical
quantiles, and the sample floors reused from `turn_metrics.py:35-38`: **n<8 → UNKNOWN; 8≤n<30 →
direction only; 30≤n<100 → threshold; n≥100 → quantile claims.** Baseline poisoning defended three
ways (deterministic-flagged records excluded; a fingerprint or policy change resets to n=0 UNKNOWN,
never blends; bounded window with a floor). Pager keys + cooldowns + retraction via
`pager.clear_key` (`core/comm/pager.py:67`). **HALT is refused by design** — halt is a human verb.

**Pins:** deterministic rules fire at n=1, statistical never do; a baseline below the floor reports
UNKNOWN, never a number; **FP budget** — replay 19,000 synthetic in-distribution evaluations with
3-of-5 persistence, assert ≤2 alerts; **page budget** — a synthetic 20-player season with 200
truncations, 50 retries and 3 fingerprint changes produces ≤4 distinct pager keys and ≤6 pages
(`pager.CAP = 50` at `:20`; the wire plane may never be more than ~10 % of it).

### W4 — Cache forensics (the money slice)
**Size:** medium.

**Delivers:** the 9-rung ladder over `request.content`; caller-pushed capped `messages_shape`; the
B1–B6 break classifier; the TTL interval; the per-event compaction verdict; and **one extraction
in `scripts/runner_token_journal.py`** — `cost_of(model, prompt, cached_prompt, completion)` pulled
out of the arithmetic already inline in `total_cost_est()` (`:133-147`), so a wire reader can price
without re-implementing. Zero new rates, one door.

**Pins:** ladder localization exact for offsets in every rung including past the 128 KB cap;
**B1 vs B5 distinguished** — identical ladder + `cache_hit=0` → provider eviction; ladder differing
at rung 0 → head mutation; a test accepting either for either fails; sub-granularity suppression
built from p3's literal 23-token numbers; **no second pricing path** (AST: the wire plane contains
no price literal and no rate table); `cost_of` is behavior-preserving
(`total_cost_est() == sum(cost_of(...))` over randomized buckets including unpriced models);
H2 measured on a real 128 KB body.

### W5 — Deep capture: L0 / L1 / L3
**Size:** medium.

**Delivers:** the httpcore `trace` extension (one line into `request.extensions` before
`super().handle_request`, free when absent); `network_stream.get_extra_info` for `peer_ip`,
`tls_version`, `tls_cipher`, `peer_cert_sha256`, `alpn` — **once per connection, keyed on
`id(network_stream)`**, not per request; the `SyncByteStream` tee.

**Blocking prerequisite:** *one real https call with the trace callback attached.* Capture's probe
ran on plain-HTTP loopback, so `start_tls` **never fired**, and the certificate-fingerprint hook —
the operator's literal "security eyes" ask — rests entirely on reading source.

**Pins:** the tee is a pass-through (byte-identical output, `close()` propagates, exceptions pass
through un-swallowed — capture verified all three twice; promote to repo pins); `conn.reused` is
populated; a `peer_cert_sha256` change raises an `expert()` **error**.

### W6 — The storage engine, TRIGGERED not scheduled
**Trigger, pre-registered:** any of (a) a single day's journal exceeds **100,000 records**;
(b) `wire_snapshot()` p95 exceeds its 5 ms budget; (c) a season run is scheduled. Until then the
drain thread writes JSONL and the engine is invisible above it.

**Rationale for deferral:** the hot-path win is the queue, not the engine (R19), and today's corpus
is 58 records / 40,528 bytes. The genuine SQLite arguments — indexed reads (`read_all()` measured at
1,413 ms and **794 MB peak RAM** at 200k records), byte-budgeted retention, WDF reaching an index —
are all *read-side*, and all arrive at a volume we can name and detect rather than guess.

**Delivers when triggered:** `scripts/wire_store.py` (stdlib `sqlite3`, WAL, `synchronous=NORMAL`,
`wal_autocheckpoint=0` in writers with one designated checkpointer, `auto_vacuum=INCREMENTAL` set
before the first `CREATE TABLE`), the `validity` column encoding (NULL = UNKNOWN, `validity` JSON
= UNDEFINED, non-NULL = MEASURED), the `wire_v` view, the WDF display filter compiling to a
parameterised SQL prefix plus a **hand-walked AST interpreter** for the residual — **never
`eval()`**, in a tool whose stated purpose is security eyes.

**Pins:** dual-write `both` stays the default **through retirement**, not before it
(`reversible_cutover_requires_post_flip_reverse_path`); the backend's reported status is derived
from what the factory *did*, not what the env var *says*
(`backend_selector_must_cover_wrapped_factory_branches` — the wrapped branch is
`deepseek_chat.py:83-89`); `tests/test_t156_wire_journal.py` passes with only the constructor
argument changed; **backup is `sqlite3.Connection.backup()`, never `shutil.copy2`**; no index
without a producer.

### W7 — The security plane (gated on §6)
**Size:** large; several independent pieces, each individually gated.

`EGRESS-1` fields ship in W0. The rest — the taint vector (ToolBox getter + runner-side pull), the
delta-only DLP scan with the content-addressed memo, the per-line `prev_sha` hash chain (~0.3 µs,
converts a log into evidence), tier-1 body capture, and `Cap.EGRESS` + `egress_scope` in
`core/trust/` — each needs a ruling. **Nothing in W7 lands before §6.5**: designing encryption for
the wire journal while the plaintext provider keys next door may be world-readable is theatre.

---

## 6. WHAT NEEDS THE OPERATOR'S RULING

### 6.1 Tier-1 body capture — the one that stores prompt content
Two designs, by the same author, four hours apart, disagree. The prior design deliberately refuses a
middle tier (*"blurring them is how full prompts end up on disk forever"*); security-design §3.1
reinstates it on the grounds that **structural** redaction is categorically different from textual
redaction, because we own the assembly point: `system` stored once per `system_sha` and referenced
thereafter; `user` excerpted head+tail 512 B and redacted; `assistant` length+sha only; and `tool`
messages — 80–95 % of the bytes and 100 % of the "we wrote the repo to disk twice" problem —
**never stored as text at all**, only `{tool_name, args_sha, result_len, result_sha,
source_paths_n, taint_classes}`. That collapses ~16 MB/day/agent to ~176 KB/day.

**This stores excerpts of prompts on disk. It is yours.** My recommendation: yes to the skeleton,
no to the excerpt, until the hash chain and the ACL work land.

### 6.2 Logprobs
Zero token cost, 2.19x stream volume, plus `SSEDecoder` and `json.loads` work on the consumer's own
thread mid-turn — and enabling it **mutates the production request** to serve telemetry. It buys
per-token model confidence on the reasoning channel, the deepest layer physically visible.
Recommendation: **off by default; opt-in per call**, never fleet-wide.

### 6.3 Prompt-hash salting
`_sha()` (`wire_journal.py:72-73`) is unsalted sha256 truncated to 64 bits. Anyone who can read the
journal and guess a candidate prompt can **confirm** it was sent — and for templated prompts (a
bounty card, a boot block) the guess space is small. Salting kills the oracle and also kills
cross-agent, cross-install comparability, which is the entire value of `prompt_prefix_sha`.
Recommendation: **keep unsalted at tier 0** (the file is double-gitignored and pinned); revisit if
tier 1 lands.

### 6.4 `Cap.EGRESS` — this changes what the fleet is *allowed* to do
`core/trust/capabilities.py:13-28` has 13 capabilities and **none of them describes sending bytes to
a third-party inference provider** — the single largest exfiltration surface the system has. A
`quarantined` agent (`READ`, `BIFROST_INBOX`) can read the repo and, if it holds a runner, ship
every byte it reads outward, and nothing records it. The proposed control is a structural copy of
`can_write` with `quarantined → []`, checked **once at client construction** (zero per-request
cost), with the journal serving as the proof the gate held. It touches `core/trust/`, and it can
stop a runner from starting. **Your call.**

### 6.5 `.secrets/` permissions — the highest-value, lowest-cost security item, and it is not ours
Security-design measured `.secrets/deepseek.key`, `openai.key` and siblings as `-rw-r--r--`
(world-readable), plus a 1.8 MB `gemini_debug.html` accumulating **inside the credential
directory**. That reading came through Git Bash's POSIX emulation of Windows ACLs and **should be
re-checked with `icacls` before being acted on** — but if it holds, it dominates everything in this
document. Also unchecked: whether `E:` is BitLocker-protected, which would make the whole
at-rest-encryption question moot.

### 6.6 The retention budget, in bytes
Today: `MAX_FILES = 14` and `MAX_BYTES = 8 MB` (`wire_journal.py:60-61`), which — because of D1 and
the single-file case — bounds neither the aggregate nor a single day. Per-writer files without a
fleet owner would be 20 × 14 × 8 MB = **2.24 GB** against an intended 112 MB. Proposal: **one fleet
aggregate for tier 0, 512 MB, oldest-first, counted.** Your number.

### 6.7 May a wire finding wake you?
Four INTERRUPT conditions are proposed (fingerprint change during a live season; 401/403; sustained
429; capture drops > 0), each passing a two-clause gate: *a human action exists that no agent can
take*, **and** *delay makes it worse rather than merely longer*. You should know before agreeing
that `core/comm/pager.py:9` says the unattended case — no live seat anywhere — is wave-2's problem,
i.e. **an overnight INTERRUPT may reach nobody.**

### 6.8 Instrument the other three seats
`core/comm/runner_lib.py:14-27` `make_openai_compat_client` has no `http_client` parameter, so
**kimi and gemini cannot be instrumented at all** (verified: `:25-27` builds a bare `OpenAI(...)`),
and `sol_chat.py` builds its own. Adding one optional `http_client=None` passthrough **triples
instrumented coverage in one parameter.** It is a `core/` edit and it changes what gets recorded
about three more agents. Cheapest high-leverage change in the entire program, and no dimension
proposed it.

---

## 7. HONEST APPENDIX

### 7.1 Three of six verdicts did not reach me
I received adversarial verdicts for **hot-path**, **capture**, and **storage** — and the storage
verdict arrived **truncated mid-sentence** inside its `perf_violations` list (it cut off during the
drain-thread durability item, which I have reconstructed and answered as V16 in §4.3; the remainder
of its list is unknown to me).

**No verdict reached me for mining, live, or security.** Their claims therefore carry less evidential
weight than the three that were attacked, and three of their load-bearing numbers are exactly the
kind an attacker would go for:

- mining's ladder cost (0.05–0.15 ms) is an estimate from operation counts; mining ran **no code at
  all** and says so.
- live's 0.14 ms `wire_snapshot()` is extrapolated from a parse-rate measurement, never run against
  a real projection, and its ~200 KB memory figure is arithmetic, not `tracemalloc`.
- security's DLP timings **were** measured on this machine — but against scratchpad scripts that
  the author states will not survive the session, so they are unreproducible as written.

Treat every number in §2.3 that is not marked MEASURED-HERE or attributed to a verified probe
artifact accordingly. The pins exist to convert them.

### 7.2 Unresolved contradictions between dimensions

- **C1 — the clock.** The hot-path verifier states `time.time()` has ~15.6 ms resolution on
  CPython 3.11/Windows, so every shipped `ms_first_byte` is quantized into ~15 ms buckets.
  Capture **measured** the opposite: `time.time` declared 0.015625 s but *observed steps ~0.5 ms*
  (and `time.monotonic` genuinely quantized at 15.625 ms). Both cannot be right. It is moot for the
  decision — `perf_counter` is correct either way, at 56.5 ns — but the error bar on the 58
  `ms_first_byte` values already on disk depends on which is true, and nobody resolved it.
- **C2 — a fourth validity state.** Mining §5.4 wants `BOUNDED` alongside MEASURED / UNKNOWN /
  UNDEFINED, for the unbilled-but-spent tokens of §3.8. T141's vocabulary is fixed at three and is
  **claimed by another seat (codex_root)**. My non-blocking resolution: report `UNKNOWN` plus a
  separate `upper_bound_tokens` field, which needs no vocabulary change. Not mine to settle.
- **C3 — `record_reasoning`: PARTIAL or BLOCKED.** The prior design calls it PARTIAL (fill the
  total, leave the split UNKNOWN). Mining argues **BLOCKED**, because `EfficiencySnapshot` has only
  `reasoning_tokens_coordination` and `reasoning_tokens_productive` — **there is nowhere to put an
  unsplit total**, and feeding one side makes `coordination_token_ratio` render *"0 % of effort
  spent on coordination"* (an outstanding result) when it means *"we never measured the coordination
  half"*. **I ruled BLOCKED** and made it an AST pin: the wire plane contains no call to
  `cognitive_metrics.record_reasoning`. The API reports reasoning token **counts**; it never reports
  their **purpose**, and no provider field ever will.
- **C4 — membrane pin P9.** P9 would assert *"nothing under `core/` imports `scripts.wire_journal`"*
  — but `core/comm/doctor.py:1099` already does exactly that with `runner_token_journal` (verified
  tonight), and it is the **only proven telemetry-reader pattern in the repo**. Enforced literally,
  P9 forbids the wire journal the one reader it most needs. **My narrowing:** no `core/` module may
  import `scripts.wire_*` at module-import time; a guarded, function-local, read-only import inside
  a doctor/dashboard function is permitted, following `:1099`'s exact shape. Three dimensions found
  this contradiction independently; the membrane's custodian should confirm the narrowing.
  Compounding it: `docs/LIVE_CONSTRAINTS.md` is 22 lines and contains no occurrence of "runner",
  "membrane", or "subprocess" — **the law is real and uncodified**, which is how the ambiguity
  persists, and a future seat placing `wire_live.py` in `core/comm/` would break it with no document
  saying so.
- **C5 — membrane vs taint.** The taint ledger needs `core/comm/toolbox.py` state to reach a
  `scripts/` recorder. Security proposes a **pull, not a push** — `core/` gains a read-only
  `taint_snapshot()` getter and imports nothing; the runner reads it. I believe that holds. Same
  custodian.
- **C6 — pull vs push liveness.** The panel rides a 2 s poll, so it is up to 2 s stale against calls
  that take ~1.15 s — roughly one call behind, visible to a watching human. Chosen because push
  costs a Redis connection and a server thread per browser tab and re-opens the recorded
  multi-poller flicker scar. **Reversible**: `snapshot()` is transport-agnostic and would serve an
  SSE loop unchanged.
- **C7 — tier count.** §6.1. Two designs by the same author, four hours apart.

### 7.3 A meta-finding worth recording
**Two independent seats (capture §9, storage §1.1) reported the same grep as returning three hits
when it returns five — and both missed the same two files**, `tests/manual/bench_wire_hotpath.py`
and `tests/manual/bench_wire_shard.py`. Those two files are the hot-path benchmarks that measure
precisely the cost both documents were arguing about, they were written in the same session, and
running them (which I did, §2.1–2.2) settles the storage headline against its own author. Both
sections were titled some version of *"a writer without a reader is the defect."*

The systematic pattern across all three verdicts: **every citation into Python source verified
clean; the citations that drifted were all into prose.** Build rule for this program: cite code, and
re-run the bench rather than quoting a sibling document's summary of it.

### 7.4 What nobody verified

- **No live API call was made by any of the six seats.** Every provider-behaviour claim in the entire
  program traces to the 2026-08-02 probe battery or to the records on disk. My own additions are
  read-only census plus two in-repo benches against temp directories.
- **TLS was never exercised.** Capture's trace probe ran on plain HTTP, so
  `connection.start_tls.started/complete` never fired. The certificate-fingerprint hook — the literal
  "security eyes" deliverable — is **read from source, not observed**. One https call settles it and
  it is the prerequisite of slice W5.
- **The error path is entirely unexercised.** MEASURED-HERE: 58/58 status 200, 58/58 attempt 0. Every
  claim about 429, `Retry-After`, retry behaviour and the exception-branch record at
  `wire_journal.py:328-333` rests on **zero live evidence**. A cheap fault-injection harness against
  a local stub would convert that whole half from INFER to MEASURED, and nobody proposed one.
- **The ContextVar join has never been run against the real SDK retry loop.** Hot-path chose
  `threading.local()` on an explicitly unverified assumption that openai 2.24.0's sync path never
  moves a request to a worker thread or an anyio portal; I chose `ContextVar` because it survives an
  async re-entry where `threading.local()` would not — but **neither has been measured**, and
  `ContextVar.get()` has no number attached anywhere in the program. P-W1-7 exists for this.
- **blake2b vs sha256 on this hardware** — unmeasured. **`hashlib.copy()` being O(1)** — asserted
  from CPython's fixed-size state, not tested. The ladder design does not depend on the algorithm,
  only on the one-pass structure.
- **`CACHE_MIN_BLOCK = 64` is ASSUMED**, not sourced from DeepSeek's documentation. The p3 data is
  consistent with a block size somewhere above 23 tokens; that is all it establishes.
- **The fingerprint decomposition is a reading of ONE sample string.** Marked INFER in place, and it
  must fail soft.
- **`cached_tokens` and `prompt_cache_hit_tokens` have never been observed to disagree** — both
  report 0 on every probe — so we have no evidence they are independent measurements rather than the
  same number under two names. Treat as one observation with two labels; the day they diverge is
  itself a finding.
- **The WDF pushable/residual split is unbuilt and unmeasured** — its correctness under `OR` is, by
  its own author's admission, the thing most likely to be subtly wrong. FTS5 availability was
  probed; its behaviour was not.
- **The 20-process SQLite contention test had no long-lived reader holding a transaction open** —
  which is exactly the shape that grew a `-wal` to 523,272 bytes in the earlier probe, and **the UI
  is a held reader.** Named by its own author as the highest-value follow-up.
- **Season-1 concurrency shape.** Nobody read the season harness's launch logic, so whether 20
  players run concurrently or in waves is unknown — and it changes the burst amplitude, the
  multi-process append hazard, and the engine trigger substantially.
- **Cross-process clock skew** was not measured, though cross-process record ordering depends on it.
- **Windows ACLs via `icacls`** (§6.5) and **BitLocker status on `E:`** — both unchecked, and §6.5's
  recommendation ordering depends on them.
- **Season volume figures are floors, not estimates** (R30), derived from the worst turn's per-hop
  token rate applied as a fleet mean.

### 7.5 What this design explicitly does not protect against
Carried forward from security-design §10 because a document that lists only what it catches is
marketing: any egress that does not pass through the four `make_client` factories
(`scripts/gemini_web.py` drives a full Chrome via Playwright — every byte is invisible here); the
pytest exec family, which runs arbitrary repo code by its own admission and could read a key and
post it anywhere while `EGRESS-2` watches the wrong door; a malicious in-process recorder
(`AKASHIC_WIRE=0` at `deepseek_chat.py:83` is a documented off switch, and any process can build its
own `OpenAI()` client) — **this is a monitor, not a sandbox**; self-declared identity; semantic
exfiltration (taint says the file was read, never why); the provider's own conduct once bytes
arrive; secrets under 32 characters or hex-encoded (measured: **0 % detection for hex at any
length**; a real 20-char AWS `AKIA` id scores H=3.72, below every threshold tested); and everything
already sent, which is unrecoverable and unaudited.

**And the one that actually decides whether this program succeeds:** the most likely failure mode is
not a bypass or a regression. It is that all of it gets built and **nobody reads it** — which is why
W0's smallest deliverable is a doctor line, and why every slice above names its reader before it
names its fields.
