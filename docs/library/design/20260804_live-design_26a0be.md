---
akashic_id: art_20260804_live-design_26a0be
akashic_sha: 529cac82f9b0
schema_version: 1
status: current
type: design
date: 2026-08-04
title: live-design
gist: "# Live telemetry and the operator surface — the wire journal's second half Dimension owner: opus5 seat (live telemetry / operator surface), "
visibility: fleet
body_type: markdown
seats: []
category: [bus, agent-lifecycle, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T02:52:26"
updated: "2026-08-04T02:52:26"
---
<!-- GENERATED PROJECTION of art_20260804_live-design_26a0be -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# live-design

# Live telemetry and the operator surface — the wire journal's second half

Dimension owner: opus5 seat (live telemetry / operator surface), 2026-08-04
Status: DESIGN ONLY. No code written, no bus sent, no ledger touched. Every measurement below was
taken read-only against the live repo and the live Redis, and the commands are named so they can be
re-run.

Daniil, 2026-08-04: *"I want us to overengineer this to the max while retaining performance. I want
us to be able to mine this for information and to feed it into our live telemetry, this deserves our
best."*

This document owns the second clause: **feed it into our live telemetry**. It answers how records
reach a live surface, what that surface shows, how it survives a 20-player season, where the
DeepSeek/Claude seam sits, and which findings are allowed to interrupt a human.

---

## 0. The finding that reorders everything else

**A live wire panel built today would have four true things to show, and three of them would be
false zeros.**

I ran the shipped reader against the shipped journal. 41 live records, `state/wire/wire-20260804.jsonl`:

```
records            41
model              populated  0 / 41
stream             populated  0 / 41
system_fingerprint populated  0 / 41
finish_reason      populated  0 / 41
prompt_tokens      populated  0 / 41
total_tokens       populated  0 / 41
reasoning_tokens   populated  0 / 41
cache_hit_tokens   populated  0 / 41
ms_total           populated  0 / 41
prompt_sha         populated  0 / 41
response_id        populated  0 / 41
service_tier       populated  0 / 41
agent              populated 41 / 41   -- but the value is "unknown" in all 41
status             populated 41 / 41
attempt            populated 41 / 41   -- all 0
ms_first_byte      populated 41 / 41
headers            populated 41 / 41   -- x-ds-trace-id captured live, this part works
```

Then `WireJournal().summarize()` on that same journal:

```
{"records": 41, "dropped_captures": 0, "total_tokens": "UNKNOWN",
 "reasoning_tokens": "UNKNOWN", "truncated": 0, "errors": 0, "retries": 0,
 "fingerprints": [], "cache_hit_rate": "UNKNOWN"}
```

`expert()` returned exactly **one** finding: `('info', 'cache hit rate UNKNOWN', ...)`.

Three of those aggregates are **MEASURED zeros over a field that is 0/41 populated**:

- `scripts/wire_journal.py:216` — `out["truncated"] = sum(1 for r in rows if r.get("finish_reason") == "length")`
- `scripts/wire_journal.py:217` — `out["errors"] = sum(1 for r in rows if r.get("error"))`
- `scripts/wire_journal.py:218` — `out["retries"] = sum(1 for r in rows if (r.get("attempt") or 0) > 0)`

`finish_reason` is structurally unreachable at the transport, because the transport deliberately
never reads the body (`scripts/wire_journal.py:336-337`: *"the body is deliberately not read:
touching resp.stream would consume the SSE stream"*). So `truncated: 0` is not a measurement of
zero truncations — it is a measurement of nothing, rendered as zero. That is precisely the defect the
module's own docstring says it avoids (`scripts/wire_journal.py:190-196`, and the `UNKNOWN` constant
at `scripts/wire_journal.py:69` citing T141).

`fingerprints: []` has the same shape and is worse in consequence: an empty set renders in a panel as
"no model swap detected", when the truth is "we cannot detect a model swap." That is the exact
failure the journal was built to prevent (`scripts/wire_journal.py:23-26`).

**Consequence for this dimension.** The operator surface is *downstream of a correlation half that
does not exist yet.* The design doc already names it — a usage-capture callback at
`scripts/deepseek_chat.py` correlated by `call_id`
(`research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md:246-258`) — but it is not built,
and until it is, the panel's headline numbers are UNKNOWN. I therefore treat **L0 (§7) as a
prerequisite of the panel, not a follow-on**, and every surface below renders UNKNOWN honestly rather
than dropping the tile.

---

## 1. TRANSPORT: the wire feed must not ride the trace lane

### 1.1 The lane-cap arithmetic, measured on live Redis

```
bifrost:trace   XLEN = 5001        (LANE_MAXLEN["trace"] = 5000, core/comm/packet_spec.py:216)
bifrost:work    XLEN = 0
bifrost:sig     XLEN = 0
bifrost:trace:spotcount = 40389    (lifetime writes since the counter was minted)
oldest entry    2026-08-01 13:59:32
newest entry    2026-08-04 02:08:19
residency       216,527 s = 60.1 hours
arrival rate    0.023 msg/s = ~83/hour
```

The trace ring has already turned over roughly eight times (40,389 lifetime writes / 5,000 slots).
Its current residency window is 60.1 hours. Every wire record pushed onto it **shortens that window
for the conversation traces that live there.** At a modest 2 HTTP round trips per turn across five
runners, wire records would roughly double the trace arrival rate and cut residency to ~30 hours.
Under a 20-player season it collapses: the season doc budgets 200 model calls for
`20 players × 10 rounds` (`docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:711`);
with agentic tool loops and SDK retries counted as the separate round trips they are
(`scripts/wire_journal.py:116`), 1,000–2,000 records in a single season run is the realistic figure.
That is 20–40% of the entire ring, consumed by one game, evicting three days of fleet narration.

### 1.2 The decisive argument: nothing reads the trace lane's contents

I grepped every reader in `core/`, `scripts/`, and `agent_cli.py` for `xread`/`xrange`/
`lane_stream_key`. **The only consumer of `{ns}:trace` is `core/comm/lane_depths.py:33`, and it calls
XLEN only** — a depth gauge. No code anywhere reads the trace lane's entries.

The console does render trace messages, but not from that lane. `core/comm/room_feed.py:43-70`
discovers exactly two stream families — `{ns}:inbox:*` and `{ns}:broadcast` — and
`core/comm/room_feed.py:32-36` says so explicitly: *"The two stream families the console renders as
conversation."* Trace-kind messages reach the UI through the **legacy dual-write copy**
(`core/comm/bus.py:545-549`; T039a/T044 per `docs/LIVE_CONSTRAINTS.md:15`), never through the lane.

So the trace lane is, today, **40,389 writes into a ring whose only reader counts its length.** Putting
the wire feed there would be the `cognitive_metrics` defect reproduced at the transport layer — a
writer with no reader — and the brief names that as the standing warning. **Refused.**

### 1.3 The cost of a bus write on the API hot path, measured

`WireJournal.record()` is called from inside `handle_request` **before the response is returned to
the SDK** (`scripts/wire_journal.py:338-341`). Anything done there sits on the caller's
time-to-first-byte path. Measured on this machine:

| operation | mean | source |
|---|---|---|
| Redis `PING` round trip | **464 µs** | `c.ping()` × 300 |
| Redis `GET` round trip | **490 µs** | `c.get('bifrost:presence:claude')` × 300 |
| Redis `XADD` (maxlen 5000, approximate) | **564 µs** | throwaway `bifrost_wirebench:trace` key, deleted after |
| `WireJournal.record()` today, 1 journal file | **273 µs** | tempdir, 500 iterations |
| `WireJournal.record()` today, 14 journal files | **332 µs** | tempdir + 13 stub files, 300 iterations |

A `Bus.send()` is **not** one XADD. The path at `core/comm/bus.py:474-540` performs: `compute_len_sha`
(SHA-256 over the envelope), MTU check, `shadow_router.route`, `INCR {ns}:trace:spotcount`
(`core/comm/bus.py:505-506`), `XADD` to the lane, `XADD` to legacy, and
`shadow_router.record_observation`. That is **≥5 Redis round trips ≈ 2.4 ms** plus hashing.

Against a measured API call of 1,063–1,156 ms total and 813–890 ms TTFT
(`research/in-flight/wire-capture-deepseek-2026-08-02/p3-ttft-decomposition.json`), 2.4 ms is 0.22%.
Latency is not the objection. **The objection is the failure mode:** a Redis stall or a fail-fast
client timeout (`core/foundation/redis_connection.py`, short socket timeout by design) would convert a
coordination-plane hiccup into a model-call stall, on a thread the SDK is about to stream from. A
telemetry layer that can make an API call slower is a regression dressed as observability.

### 1.4 The transport that is already there: the file is the feed

The wire journal already writes an **append-only, local, rotating, doubly-gitignored** JSONL file
(`scripts/wire_journal.py:96-99`). An append-only local file is a perfectly good live transport
provided the reader tails it by byte offset instead of re-parsing it. This is not a novel pattern
here — `core/comm/engine_vitals.py:55-65` (`_today_journal`) already reads a per-agent JSON file on
every 2-second `/api/now` poll, and `core/comm/engine_vitals.py:70-71` documents the budget it holds
itself to: *"Cheap (<=3 backend reads + 1 file stat)."*

**Decision: the live wire feed is a file tail, read in-process by the UI server. No new Redis keys, no
new stream, no second daemon, no bus traffic per packet.** The bus appears in this design exactly
once — for *findings*, not for packets (§6).

---

## 2. HOT PATH: what I propose changing, and why it makes the call faster

The one hot-path change I propose **reduces** hot-path work by roughly three orders of magnitude. It
is not a tradeoff.

### 2.1 What the hot path does today

`scripts/wire_journal.py:93-104`, inside `handle_request`:

1. `self._shape(kw)` — builds a dict, runs `_sha` (SHA-256) up to three times
2. acquires `self._lock` (a `threading.Lock`, `scripts/wire_journal.py:83`)
3. `os.makedirs(...)` — a syscall, **every record**
4. `open(path, "a")` + `write` + implicit `close` — three syscalls, every record
5. `self._rotate()` → `self.files()` → `os.listdir` + `os.path.getsize` — every record

Measured: **273 µs** with one file, **332 µs** with fourteen. All of it synchronous, under a
process-global lock, on the thread the SDK will stream from.

### 2.2 What I propose

Split capture into **enqueue (hot)** and **shape + serialise + write (warm)**.

```
handle_request  ──►  SimpleQueue.put(raw_tuple)     0.035 µs   [HOT PATH ENDS HERE]
                              │
                     drain thread (daemon, 1 per process)
                              ├─► _shape() + json.dumps()      1.55 µs
                              ├─► batched append, fsync never, flush every N or 250 ms
                              ├─► O(1) rolling-aggregate bumps 0.118 µs
                              └─► finding evaluation (§6), cooldown-gated
```

Measured primitives (200,000 iterations each unless noted):

| operation | mean |
|---|---|
| `queue.SimpleQueue().put(rec)` | **0.035 µs** |
| `deque(maxlen=4096).append` + 3 counter bumps | **0.118 µs** |
| `json.dumps(record)` (20,000 iterations) | **1.55 µs** |

**Hot-path cost after the change: 0.035 µs per HTTP round trip.** Against today's 332 µs that is a
~9,500× reduction; against a 1,063 ms API call it is 0.000003%. Batched appends also collapse the
syscall count from 5-per-record to ~5-per-batch.

### 2.3 The three rules that keep the drain honest

1. **Bounded queue, and the drop is counted.** `SimpleQueue` is unbounded; use a `deque(maxlen=N)`
   with a lock-free append and a `dropped_enqueue` counter, or a bounded queue with `put_nowait` and
   an except that bumps `self.dropped`. The existing drop-counting doctrine
   (`scripts/wire_journal.py:82`, `:103`, `:271-273`) extends unchanged. A telemetry queue that
   silently discards under load is the same lie as an unpopulated counter.
2. **The drain thread is a daemon and never joins.** A runner exiting must not block on telemetry.
   Accept the loss of the last partial batch; record a `flush_lost` count in the shutdown record.
3. **Flush before the process can die on purpose.** Runners have known exit points; the drain gets a
   `flush(timeout=0.25)` call there, best-effort. This is the only place telemetry may block, and it
   is bounded at 250 ms and off the API path.

### 2.4 What this does NOT change

No change to `scripts/deepseek_chat.py:66-90`'s `make_client` contract, no change to the SDK seam, no
change to `scripts/bifrost_runner_deepseek.py`'s call site. The transport hook keeps the same
signature; only the body of `record()` changes from "write a file" to "enqueue".

---

## 3. THE PROJECTION: rolling aggregates, and the reader that must never re-parse

### 3.1 The reader defect that would kill the panel

`expert()` reads the entire journal **twice**:

- `scripts/wire_journal.py:230` — `s = self.summarize(limit)` → `scripts/wire_journal.py:198` →
  `read_all(limit)`
- `scripts/wire_journal.py:252` — `for r in self.read_all(limit):` — a **second** full read

And `limit` does not bound the IO. `read_all` (`scripts/wire_journal.py:172-187`) iterates **every
file, every line**, and only then slices `rows[-limit:]` at `:187`. Passing `limit=200` reads 100% of
the journal and throws away 99.9% of it.

Measured cost, extrapolated from real record size:

| quantity | value | source |
|---|---|---|
| bytes per record | **697 B** | 18,834 B / 27 records, `state/wire/wire-20260804.jsonl` |
| parse 20,000 records | **69 ms** | `json.loads` × 20,000 |
| records per file at `MAX_BYTES` (8 MB) | **~11,480** | `scripts/wire_journal.py:61` |
| records at full rotation (14 files) | **~160,700** | `scripts/wire_journal.py:60` |
| one `read_all()` at full rotation | **~554 ms** | 160,700 / 20,000 × 69 ms |
| one `expert()` at full rotation | **~1.11 s** | two full reads |
| at the live 2 s poll (`scripts/bifrost_ui.py:3402`) | **~55% of one CPU core, permanently** | 1.11 s / 2.0 s |

Two browser tabs open would exceed one core. **Calling `expert()` from a polled endpoint is a
non-starter and must be pinned against.**

### 3.2 The projection module: `WireTail`

A standalone module (Claude-authored, §5) holding three things, all O(1) in traffic:

**(a) A byte-offset tail.** `{path: (inode_or_size, offset)}`. Each poll: `os.stat` each journal file,
seek to the stored offset, read only new bytes, parse, advance. On rotation (size shrank, or a new
date file appeared) reset that file's offset to 0 and re-read only the new file. Cost at a 20-player
burst of 20 records/s over a 2 s poll = 40 records = **28 KB, ~0.14 ms to parse.** Against the naive
reader's 1.11 s that is a **~8,000× reduction**, and it is *constant in journal size* — the property
that matters, because the naive reader gets slower every hour the season runs.

**(b) Fixed-size time buckets.** Not a growing list.

| ring | bucket | count | span | memory |
|---|---|---|---|---|
| `live` | 1 s | 120 | 2 min | ~10 KB |
| `pulse` | 60 s | 60 | 1 h | ~5 KB |
| `session` | 300 s | 288 | 24 h | ~24 KB |

Each bucket holds counters only: `{n, n_2xx, n_4xx, n_5xx, n_err, n_retry, ttfb_sum, ttfb_sq_sum,
ttfb_max, tok_prompt, tok_completion, tok_cached, n_trunc, n_fp_seen}` plus a per-bucket
`measured_mask` bitfield recording **which of those fields the provider actually populated in this
bucket**. The mask is what makes UNKNOWN survive aggregation: a bucket where `finish_reason` was
never present reports `trunc: UNKNOWN`, not `trunc: 0`. This is the single most important structural
decision in the projection, and it is a direct consequence of §0.

**(c) A 200-record detail ring.** `deque(maxlen=200)` of the most recent records, for the drawer
(§4.5). Precedent for a bounded UI ring already exists at `scripts/bifrost_ui.py:2914-2920`
(`_traceBuffer`, "keep last 20 traces" per agent).

**Total resident memory: ~200 KB, independent of traffic volume or journal size.**

### 3.3 Percentiles without storing samples

TTFB p50/p95 matter (§4.2) and naive percentiles need retained samples, which is unbounded. Use
**fixed log-scale histogram buckets**: 16 buckets at `[0, 100, 200, 350, 500, 750, 1000, 1500, 2000,
3000, 5000, 8000, 12000, 20000, 40000, ∞)` ms. 16 ints per time bucket. Percentiles are interpolated
within a bucket; the error is bounded by bucket width and is far below the precision an operator
needs. Live TTFB samples measured at 813/859/890 ms (`p3-ttft-decomposition.json`) sit in the
`[750,1000)` bucket, so the default boundaries are calibrated to the traffic we actually have.

---

## 4. THE OPERATOR SURFACE: what earns screen space

Design constraint, stated as a rule: **a packet list is not information.** Wireshark's value to a
practitioner is Expert Info, the IO graph, and the flow graph — the packet list is where you go
*after* one of those told you where to look. The panel is built in that order.

The operator is optics-first. Five zones, in descending priority. Zones 1–3 are always visible and
total ~120 px of vertical space. Zones 4–5 are click-to-open.

### 4.1 Zone 1 — the fingerprint band (the highest-value pixels in this design)

One horizontal strip, one row per model, 60 cells (one per minute of the last hour). Each cell is
coloured by the `system_fingerprint` observed in that minute — a stable hash → stable hue. A solid
band means one build served us all hour. **A colour change is a silent model swap.**

This is the highest-value pixel we can draw and it is currently undrawable
(`system_fingerprint` 0/41 populated, §0). `scripts/wire_journal.py:23-26` states the stakes: a swap
"looks like 'the agents got worse' with no cause -- and it would invalidate every champion-challenger
comparison in a tournament without anyone noticing." A 20-player season is exactly a
champion-challenger comparison. Until L0 lands, this band renders as a single grey `UNKNOWN` strip
with the tooltip *"provider build id not captured — a swap would be invisible"*, which is the honest
render and is itself a standing argument for building L0.

### 4.2 Zone 2 — the pulse (the IO graph)

A 60-cell sparkline of round trips per minute, stacked by status class (2xx / 4xx / 5xx / transport
error), plus an overlaid TTFB p95 line. Reuses the existing `.er-flow` bar idiom already in the
console (`scripts/bifrost_ui.py:2177-2179`, `:3356-3364`) so it looks native on arrival.

What it earns: **provider degradation shows here before it shows anywhere else.** Our baseline TTFB
is 813–890 ms; a p95 crossing 3 s with a flat request rate is the provider, not us, and today the
only way we learn that is an agent taking longer for reasons nobody can name.

### 4.3 Zone 3 — the four-number ribbon

Four tiles. Each is a number an operator would *act* on, and each renders `UNKNOWN` when its
`measured_mask` bit is clear.

| tile | why it earns a tile | live status |
|---|---|---|
| **cache hit rate** | the largest cost lever we have; cached prompt tokens bill ~10× cheaper (`scripts/wire_journal.py:33-34`). The measured evidence it matters: 3,551,616 of 3,778,366 prompt tokens cached in one day for one agent (`state/runner_deepseek_2026-08-03.json`) | **UNKNOWN** today |
| **truncated** | `finish_reason=length` means the answer was cut off, not finished — the difference between a bad answer and a clipped one | **UNKNOWN** today (renders `0` in the shipped reader — §0) |
| **retries** | SDK retries happen *inside* one `create()` call (`scripts/wire_journal.py:11-12`), so a wrapper sees one slow request where three round trips happened. This is the only place they are countable | measurable but always 0 so far (41/41 `attempt=0`) |
| **capture drops** | fail-open is only honest when failures are visible (`scripts/wire_journal.py:44-47`) | **structurally unreachable — see §4.6** |

**No money on this panel.** `scripts/runner_token_journal.py:56` owns `PRICES` and `:133` owns
`total_cost_est`; the wire panel emits token counts and links to the existing spend surface. A second
pricing path is forbidden and I am not proposing one.

### 4.4 Zone 4 — Expert Info (click to open; badge always visible)

The findings list from §6, severity-ordered, **deduplicated by finding key with a count and a
first/last-seen timestamp**. Never one row per packet. Each row carries the copyable
`x-ds-trace-id` of the most recent instance, because that is the handle the provider's support needs
(`scripts/wire_journal.py:35-36`) and it is *the one field the shipped capture already gets right*
(41/41 populated, e.g. `5abed503289909b8f60317f8bcfa8659`).

A collapsed badge in Zone 3 shows `⚠ N` using the same idiom as the existing pages indicator
(`scripts/bifrost_ui.py:3371-3374`).

### 4.5 Zone 5 — the packet drawer (click to open, paged, capped)

The last 200 records, newest first, from the detail ring. Columns: time, agent, model, status, TTFB,
finish_reason, tokens, trace-id. Virtualised or hard-capped at 200 DOM rows — **the DOM node count
must be O(1) in traffic**, because unbounded row growth, not event rate, is what actually kills a
long-running console tab.

Two forensic affordances that are cheap because the data is already hashed:

- **Group by `prompt_prefix_sha`** (`scripts/wire_journal.py:139-140`) — this is the cache
  investigation. Two turns with the same prefix hash and different cache outcomes is a *provider*
  cache miss; two turns with different prefix hashes is *us* invalidating our own prefix. Today we
  cannot tell those apart, and one is a bug in our prompt assembly while the other is not.
- **`prompt_sha` recurrence** — the same exact prompt sent twice is either a legitimate retry or an
  idempotency bug. At 20 players it is the cheapest duplicate-work detector we will ever have.

### 4.6 A defect this dimension surfaces: the drop counter cannot reach the operator

`self.dropped` (`scripts/wire_journal.py:82`) is **per-process, in-memory**, and `journal()`
(`scripts/wire_journal.py:280-285`) is a per-process singleton *"One per process keeps the drop
counter meaningful."* The UI server is a different process. Any `summarize()` it calls constructs its
own `WireJournal` whose `dropped` is **always 0**.

So `dropped_captures` is structurally unreachable from the operator surface — the one number whose
entire job is to prove the fail-open path is honest cannot be seen by the human it is honest to.

**Fix (design):** the drain thread writes a periodic `kind:"heartbeat"` record into the journal
itself, carrying `{agent, pid, dropped, flush_lost, uptime_s, wire_version}`, at most once per 60 s
and once at flush. The tail reader picks it up like any other record. This costs one record per
runner per minute (≈7 KB/day for five runners) and closes the loop with the same mechanism as
everything else — no sidecar, no new key, no new file.

---

## 5. THE INTEGRATION SEAM: three lines in a file I do not own

The boundary is already ratified and already has a working precedent that states it in prose.
`core/comm/room_feed.py:1-19`: *"extracted rather than inlined so the console keeps one import and
two call sites (the ratified UI boundary: claude authors modules and backend, deepseek owns
bifrost_ui.py integration)."*

### 5.1 What Claude authors (new files, no existing file edited)

| file | what it is | why it can be standalone |
|---|---|---|
| `scripts/wire_live.py` | the `WireTail` projection (§3): offset tail, fixed buckets, histogram, findings evaluator, `snapshot()` → plain dict | pure read side; imports nothing from the UI |
| `scripts/wire-panel.js` | the five zones (§4), rendering from the `wire` key of `/api/now` | exactly the shape of the seven JS modules already served — `presence-rail.js`, `timeline.js`, `rail.js`, `agent-avatar.js`, `activity-line.js`, `bifrost_viz.js`, `theme-void.js` (`scripts/bifrost_ui.py:746-761`) |
| `scripts/wire_ring.py` *(optional split)* | the hot-path enqueue + drain (§2), if it is cleaner not to grow `wire_journal.py` | runner-side, sibling of `runner_token_journal.py`, stays out of `core/` per the membrane law |

`scripts/wire_live.py` lives in `scripts/`, not `core/`, for the same reason
`scripts/wire_journal.py` does — it is runner-plane telemetry, and `scripts/bifrost_ui.py:26` does
`sys.path.insert(0, REPO)`, so `from scripts.wire_live import snapshot` resolves from the UI process
with no packaging work.

### 5.2 What DeepSeek adds to `scripts/bifrost_ui.py` — the complete diff

**One import** (near `scripts/bifrost_ui.py:28-34`):

```python
from scripts.wire_live import wire_snapshot        # standalone; fail-open, returns {} on any error
```

**One route line** (in the static block at `scripts/bifrost_ui.py:746-761`, byte-identical in shape
to its seven neighbours):

```python
if path == "/wire-panel.js":
    return self._static("scripts/wire-panel.js", "application/javascript")
```

**One key in the `_api_now` assemble dict** (`scripts/bifrost_ui.py:970-978`):

```python
"wire": wire_snapshot(),        # <=1 file stat + tail-read per journal file; ~0.14 ms
```

**Two lines of HTML**: a `<div id="wire-panel"></div>` where the panel belongs, and
`<script src="/wire-panel.js"></script>`.

That is the whole handover: **one import, one route, one dict key, two markup lines.** No logic of
mine enters a file I do not own, and `wire_snapshot()` is total (never raises, returns `{}` on any
failure) so a broken projection degrades the panel to empty rather than breaking the console.

### 5.3 Why it rides `/api/now` and NOT a second SSE stream

This is a deliberate refusal and it is grounded in a scar already recorded in the file.
`scripts/bifrost_ui.py:3395-3400`:

> *"TRUTH/NOISE TIER: one poll scheduler replaces the scattered loops — Sighted-audit receipt: 8x
> /status + 6x /vitals in 140ms — two parallel pollers ... racing the same indicators →
> last-writer-wins flicker. The fix: ONE setInterval drives ONE fetch to /api/now."*

Adding a second poller or a second `EventSource` would re-open exactly that wound. The existing
`/events` SSE (`scripts/bifrost_ui.py:1053-1092`) also **holds a dedicated Redis connection and a
server thread per browser tab** for its blocking tail — a second one doubles that for a feed that is
strictly lower-priority than the conversation.

**The wire panel adds zero new network chatter.** It rides the poll that already runs every 2 s
(`scripts/bifrost_ui.py:3402`, `_nowPollMs = 2000`) and adds ~0.14 ms of server work and a few KB of
JSON to a response that already carries presence, vitals, lanes, seat classes, and progress for every
agent.

**The one escalation path:** if a finding reaches INTERRUPT severity (§6), it does *not* wait for the
next 2 s poll — it goes to `pager.page()` (`core/comm/pager.py:43`), which the hook already surfaces
into any live seat (`core/comm/pager.py:127-136`). Findings use the bus; packets never do.

---

## 6. AGGREGATION, RATE-LIMITING, AND THE 20-PLAYER FLOOD

### 6.1 What actually floods

At current fleet load this is a non-problem: measured turns/day are 22 (deepseek 08-01), 21 (kimi
08-01), 6–10 typical (`state/runner_*_2026-08-0*.json`). Today's partial wire journal holds 41
records. The whole day fits in 29 KB.

A season changes the *shape*, not mainly the volume: **20 players running concurrently means 20
round trips landing inside the same second, repeatedly.** The season's own budget is 200 model calls
(`docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:711`); with tool loops and
retries counted separately, call it 1,000–2,000 records ≈ 0.7–1.4 MB — comfortably under the 8 MB
file cap. **The disk is fine. The UI is what needs the governor**, and specifically:

1. **DOM growth**, not event rate — solved by the 200-row cap (§4.5).
2. **Findings storms** — one truncation finding per player per round is 200 alert rows. Solved by
   key-dedup + cooldown (§6.3).
3. **Re-parse cost growing with the season** — solved by the offset tail (§3.2), which is constant in
   journal size.

### 6.2 The three-stage funnel

```
per record   ──► drain thread, O(1) counter bumps, never touches the UI
per 1 s      ──► live bucket closes; nothing is sent anywhere
per 2 s      ──► /api/now poll pulls the current snapshot (pull, not push:
                 a slow or closed tab costs the server nothing)
per finding  ──► evaluated on bucket close, cooldown-gated, only then may it page
```

Because the operator surface **pulls**, there is no flood channel to overrun by construction. Twenty
players producing 20 records/s produce exactly the same number of UI messages as one player producing
one record/hour: **one snapshot per 2 s poll.** Burst amplitude changes the numbers inside the
snapshot, never the message count. That is the whole rate-limit story for zones 1–3, and it is why
pull beat push here.

### 6.3 Findings dedup: key + cooldown + retraction

Every finding gets a stable key `wire:<finding>:<scope>` — e.g. `wire:truncation:deepseek-red`,
`wire:fingerprint_change:deepseek-v4-pro`, `wire:http_429:*`.

- **Dedup**: a finding already present updates `count` / `last_seen`; it does not add a row.
- **Cooldown**: a key may escalate at most once per cooldown window (defaults in §6.4). Within the
  window it still increments the dashboard count.
- **Retraction**: when the condition clears for a full window, `pager.clear_key(key)`
  (`core/comm/pager.py:67`) retracts it. This mechanism exists *because* of a real incident recorded
  at `core/comm/pager.py:45-52`: a resolved `lane_stall` page rendered into every prompt for nine
  hours because the only retraction available would have discarded other agents' live pages. Using
  keys from day one means the wire journal never repeats it.
- **Cap**: `core/comm/pager.py:20` caps the page list at 50. If wire findings could produce 50 pages
  they would evict every other page in the system. The cooldown must be sized so that the wire
  journal's steady-state page contribution is **≤ 2 keys**, and that is a pin, not a hope (§8).

### 6.4 Concrete windows

| parameter | value | reasoning |
|---|---|---|
| drain flush | 250 ms or 32 records | bounded staleness; batches syscalls ~30× |
| live bucket | 1 s × 120 | 2 min of second-resolution for burst shape |
| pulse bucket | 60 s × 60 | 1 h; matches the 60-cell fingerprint band |
| session bucket | 300 s × 288 | 24 h; one screen, one day |
| UI poll | 2 s | already exists; adds nothing |
| finding eval | on 1 s bucket close | never per record |
| INTERRUPT cooldown | 900 s per key | a fingerprint swap is worth one page, not sixty |
| STEER cooldown | 300 s per agent | folds into a turn; more often is noise |
| retraction | 2 consecutive clear windows | one clear window can be a lull |

---

## 7. ALERTING: mapping findings onto the fidelity ladder

The ladder exists: **inform / steer / interrupt / halt** (`docs/PRIOR_ART.md:112`), with
`bifrost-nudge` as the targeted door (`docs/DOORS.md:23`), `nudge.steer_push`
(`core/comm/nudge.py:122`) as the fold-into-live-work rung, `nudge.nudge`
(`core/comm/nudge.py:64`) as the barge-in, and `control.halt` (`core/comm/control.py:334`) at the top.
`pager.page` (`core/comm/pager.py:43`) is the reach-a-human channel, relayed to phone/desktop by a
live seat via PushNotification (`core/comm/pager.py:6-9`).

### 7.1 HALT — nothing. Stated as a refusal.

**No wire-journal finding may halt the fleet.** Halt is a human verb here. Every condition the wire
journal can see either self-limits (auth failure fails every call anyway) or is a judgement call about
whether the work is still worth doing — and that judgement belongs to Daniil. A telemetry layer that
can stop the fleet is a telemetry layer that can stop the fleet *by being wrong*, and this one is
built on an inferred retry heuristic (`scripts/wire_journal.py:305-320`) that explicitly labels itself
a heuristic. **Refused by design, not by omission.**

### 7.2 INTERRUPT — reaches a human (page + PushNotification relay)

Four conditions. The bar: *a human would want to be woken, because every minute of delay costs
either money or the validity of a run in progress.*

| finding | why it interrupts | cooldown |
|---|---|---|
| **`system_fingerprint` changed while a season/tournament is live** | it invalidates every A/B comparison spanning the change (`scripts/wire_journal.py:24-26`, `:260-263`). Silent, irreversible, and the only moment to act is *now* — after the run it is unfixable data | 900 s |
| **HTTP 401/403** | every subsequent call burns wall clock and produces nothing. Self-healing is impossible; only a human has the key | 900 s |
| **HTTP 429 sustained** (≥3 in one 60 s bucket, or any `retry-after` > 60 s) | never yet observed by us (`research/in-flight/api-wire-reverse-engineering-deepseek-2026-08-04.md:233-239`), which means the first time it happens nobody will recognise it. `retry-after` and `x-ratelimit-remaining-*` are already in the header allowlist (`scripts/wire_journal.py:65-67`) | 900 s |
| **capture drops > 0** | the journal is now lying by omission, and every number on the panel is under-counting. This is the honesty invariant — if it breaks, the operator must know before trusting anything else on screen | 900 s |

Note the asymmetry: three of four are about **trust in the numbers or the run**, not about a single
bad call. A single failed API call is not a page. It never is.

### 7.3 STEER — folds into the affected agent's live work

Sent with `nudge.steer_push(agent, "wire", text)` (`core/comm/nudge.py:122`), drained by the seat at
its next turn boundary (`core/comm/nudge.py:136`). These are facts *the agent itself* needs and the
human does not.

| finding | what the agent does with it |
|---|---|
| **its own last response had `finish_reason=length`** | it knows its answer was clipped rather than finished — the difference between "reply badly" and "reply again, shorter." Today the seat cannot tell |
| **`reasoning_tokens` ≥ 80% of completion budget with empty content** | the `runner_reasoning_eats_final_answer` incident, named at `scripts/wire_journal.py:30-32`: 8,000 tokens of reasoning, empty content, no visible cause. This turns it into a fact the agent receives |
| **its cache hit rate fell below 20% across 3 consecutive turns** | its prompt prefix is churning; it can stabilise it. Actionable only by the agent |

Rate discipline: at most one steer per agent per 300 s, and never during a fence phase (a steer
mid-fence contaminates a blind half).

### 7.4 INFORM — dashboard only, never a message

Everything else. TTFB p50/p95 drift, retry counts, per-model breakdowns, cache-rate trends, per-POP
distribution from `x-amz-cf-pop` (which we already capture — `ATL58-P5`, `IAD12-P1`, `ATL59-P5` in
today's 41 records, and a sudden POP shift is a routing change worth *seeing* and never worth being
woken for), status-class mix, prefix-hash groupings.

**The default is INFORM.** A finding is promoted out of it only by naming, in the design, the specific
human action it enables. Promotion without a named action is how a pager becomes noise, and a noisy
pager is a pager that gets ignored on the night it matters.

### 7.5 The escalation gate, stated as one rule

> A wire finding may page a human only if (a) a human action exists that no agent can take, **and**
> (b) delay makes the situation worse rather than merely longer. Everything else is a pixel.

All four INTERRUPT conditions pass both clauses. No STEER condition passes (a) — the agent can act.
No INFORM condition passes (b) — a drift is equally visible in an hour.

---

## 8. PINS (pre-registered, RED first)

Every pin below is a claim that can fail, with the number it fails against.

| pin | assertion |
|---|---|
| **P1** | The hot path never touches the filesystem or the network. A test that monkeypatches `open` and the socket module to raise, then drives 100 round trips through the recording transport, must see 100 successful responses. |
| **P2** | Hot-path enqueue ≤ **5 µs** mean over 10,000 iterations (measured baseline: 0.035 µs; the headroom is for the bounded-queue guard). Today's `record()` is 273–332 µs — the pin is a *regression* guard on a 60× improvement. |
| **P3** | `wire_snapshot()` is **O(1) in journal size**. Assert: snapshot latency against a 100,000-record journal is within 2× of the same call against a 1,000-record journal. The naive reader fails this by ~100×. |
| **P4** | `wire_snapshot()` ≤ **5 ms** at the 95th percentile with 40 new records per poll (measured estimate 0.14 ms). Anything slower is stealing from `/api/now`, which serves every other card. |
| **P5** | **No false zeros.** With a journal where `finish_reason` is 0/N populated, the snapshot's `truncated` field must equal `UNKNOWN`, not `0`. This pin fails today against `scripts/wire_journal.py:216`. |
| **P6** | **Bounded memory.** After 1,000,000 synthetic records, `WireTail` resident size is within 20% of its size after 1,000. |
| **P7** | **Bounded DOM.** After 5,000 records stream through the panel, `#wire-panel` contains ≤ 400 elements. |
| **P8** | **Page budget.** A synthetic 20-player season with 200 truncations, 50 retries, and 3 fingerprint changes produces ≤ **4** distinct pager keys and ≤ **6** total pages. `core/comm/pager.py:20` caps the list at 50; the wire journal may never be more than ~10% of it. |
| **P9** | **Retraction works.** A finding that clears for two windows calls `pager.clear_key` and disappears from the badge. |
| **P10** | **The UI degrades, never breaks.** With `state/wire/` deleted, made unreadable, and filled with 1 MB of non-JSON garbage, `/api/now` still returns 200 with every other key intact and `wire: {}`. |
| **P11** | **No new poller.** A network-panel capture of a 60 s console session shows exactly the same request count with the panel as without it. |
| **P12** | **No money.** `grep -c "PRICES\|cost\|price\|usd" scripts/wire_live.py scripts/wire-panel.js` returns 0. Money lives in `scripts/runner_token_journal.py:56`. |

---

## 9. CONTRADICTIONS — recorded, not resolved

**C1. The journal's own docstring vs. three of its own aggregates.**
`scripts/wire_journal.py:190-196` promises *"Every aggregate distinguishes MEASURED from UNKNOWN
(W7)"*. `:216`, `:217`, `:218` do not: `truncated`, `errors`, and `retries` return `0` over fields
that are 0/41 populated in live data. Verified by running `summarize()` (§0). Someone must decide
whether the fix is a `measured_mask` in the record shape or a per-field population census in the
reader. I have designed for the former (§3.2b) but I did not author the change.

**C2. Per-agent journal files: designed, then not built.**
`research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md:329` specifies
`state/wire/<agent>/<date>.jsonl`. The shipped path is flat: `wire-<date>.jsonl`
(`scripts/wire_journal.py:97`), with no agent in the filename. Three consequences for this dimension:
(a) the panel cannot group by agent from the filesystem and must rely on the `agent` field, which is
`"unknown"` in 41/41 live records; (b) five runner processes append to one file with only a
**per-process** `threading.Lock` (`scripts/wire_journal.py:83`) — cross-process append interleaving
is unguarded, and at 20 concurrent players it is a live risk that today's 697-byte records probably
survive and tomorrow's larger ones may not (the reader's torn-line guard at
`scripts/wire_journal.py:183-184` limits the damage to one lost record, which is honest but is not a
fix); (c) per-agent files would make the tail reader trivially parallel and per-agent aggregation
free. I recommend per-agent files but this is a writer-side decision and not mine to make.

**C3. `model` is captured from a header that no SDK sends.**
`scripts/wire_journal.py:332` reads `request.headers.get("x-model")`. The model name lives in the
request **body**, not a header; `x-model` is not an OpenAI-SDK header. Live data confirms: `model` is
0/41 populated. The consequence for the surface is severe — the fingerprint band (§4.1) and every
per-model breakdown are keyed on a field that is structurally always `None`. This is separate from
the usage-correlation gap (§0) because it is fixable at the transport alone: parse `model` out of
`request.content` (a small JSON body, already in memory, ~10 µs) or have `make_client` bind the model
at construction. I flag it; I did not fix it.

**C4. `MAX_BYTES` does not bound a single day.**
`scripts/wire_journal.py:61` declares an 8 MB cap and `:157-161` enforces it by deleting
`files[0]` — guarded by `len(files) > 1`. On a single-file day the size cap is a no-op: the current
file can grow without bound. `MAX_FILES` (`:60`) bounds the file *count*, not the bytes. The stated
purpose at `:58-59` — *"a season of 20 players must not be able to fill a disk"* — is therefore not
enforced on the exact scenario it names. This matters to the live surface only because §3.2's offset
tail makes reader cost independent of file size; without it, a runaway file is also a runaway poll.

**C5. Membrane law vs. `LIVE_CONSTRAINTS.md`.**
The prior design doc records that `docs/LIVE_CONSTRAINTS.md` contains zero occurrences of "runner",
"membrane", or "subprocess"
(`research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md:299-302`). I re-read the file
(22 lines) and confirm it. The membrane law governs where my modules live (`scripts/`, not `core/`)
and it is not in the constraint pack that boot renders into every seat. Flagged, not filled — and it
is a live risk for *this* slice specifically, because a future seat placing `wire_live.py` in
`core/comm/` would break the law without any document telling it so.

**C6. Pull vs. push, honestly stated.**
I chose pull (`/api/now`) over push (SSE). The cost is **up to 2 s of staleness** on the panel. For a
system whose API calls take 1.06–1.16 s, a 2 s panel is roughly one call behind — visible to a
watching human. I judged that acceptable because push costs a Redis connection and a server thread
per tab (`scripts/bifrost_ui.py:1053-1092`) and re-opens the multi-poller flicker scar
(`scripts/bifrost_ui.py:3395-3400`). Someone who values sub-second liveness over that would choose
differently, and the decision is reversible: the projection module is transport-agnostic and
`snapshot()` would serve an SSE loop unchanged.

---

## 10. BUILD ORDER — smallest first, each independently useful

| slice | what | unlocks | hot-path cost |
|---|---|---|---|
| **L0** | usage correlation: bind `call_id` at the transport, fill body-derived fields where the runner already assembles them (`_absorb_usage`), and capture `model` from the request body (C3) | **everything.** Without it the panel has four fields | ~10 µs (one small JSON parse) |
| **L1** | hot path split: enqueue + drain thread (§2) | removes 332 µs of syscalls from every API call | **−332 µs** (it is a saving) |
| **L2** | `scripts/wire_live.py`: offset tail + buckets + `snapshot()`, plus a `measured_mask` so nothing renders a false zero (C1) | a truthful JSON blob; CLI-readable immediately | none (off-path) |
| **L3** | `scripts/wire-panel.js` zones 1–3, and the 3-line handover to DeepSeek (§5.2) | the operator surface | none |
| **L4** | findings evaluator + pager keys + cooldowns (§6.3, §7) | alerting | none |
| **L5** | zones 4–5: Expert Info drawer + packet drawer + prefix grouping | forensics | none |

L0 before L1 is deliberate: L1 is a refactor of a path whose output is currently mostly `null`, and
refactoring an empty pipe teaches you nothing about whether the pipe is right.

---

## APPENDIX — WHAT I DID NOT VERIFY

1. **I did not run the UI.** Every claim about `/api/now`, `/events`, the poll scheduler, and the
   static-JS route table is read from `scripts/bifrost_ui.py` at the cited lines. I did not start the
   server on :8787 and I did not confirm the panel renders.

2. **I did not measure `Bus.send()` end to end.** The ~2.4 ms figure is **INFER**: ≥5 Redis ops ×
   the measured 464–564 µs per-op round trip, plus SHA-256 hashing I did not time. I deliberately did
   not call `bus.send()` — the brief forbids bus sends. I *did* run 205 raw `XADD` calls against a
   throwaway key `bifrost_wirebench:trace` (a test namespace per `core/comm/packet_spec.py:279`) and
   deleted it afterwards, confirming `exists == 0`. If that counts as a bus write, it is recorded
   here rather than omitted.

3. **The 20-player volume figures are estimates.** 1,000–2,000 records per season run extrapolates
   from the season doc's 200-call budget
   (`docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:711`) times an assumed
   5–10 HTTP round trips per agentic round. I did not measure round trips per agentic turn. Today's
   only datapoint is 41 wire records against 10 deepseek turns on 2026-08-04
   (`state/runner_deepseek_2026-08-04.json`), and the wire journal was hooked mid-day, so even that
   ratio is not clean.

4. **`MAX_BYTES` behaviour on a multi-file day is read, not run.** I traced `_rotate`
   (`scripts/wire_journal.py:147-161`) and reasoned about the `len(files) > 1` guard. I did not
   generate an 8 MB journal and watch it rotate.

5. **Cross-process append atomicity on Windows (C2b) is unverified.** I did not run concurrent
   writers against one file. Whether a 697-byte buffered text-mode append from five processes can
   interleave on this platform is stated as a risk, not a measurement.

6. **Percentile-bucket error is unquantified.** The 16 log-scale boundaries in §3.3 are calibrated to
   three TTFB samples (813/859/890 ms). I did not compute the p95 error those boundaries produce
   against a realistic distribution, because I do not have one — TTFB is 41/41 populated for
   `ms_first_byte` but that is transport-level first byte, not model TTFT, and the two are not the
   same measurement.

7. **I did not verify that `pager.page()` reaches a phone.** The relay doctrine is read from
   `core/comm/pager.py:6-9` (a live seat relays `[PAGE]` lines via PushNotification). I did not test
   the path, and `core/comm/pager.py:9` itself says the unattended case — no live seat anywhere — is
   *"wave-2's scheduled-session anchor"*, i.e. **an overnight INTERRUPT may reach nobody.** That is a
   real limitation of my §7.2 design and I could not close it.

8. **Memory figures for `WireTail` are arithmetic, not measured.** ~200 KB is the sum of bucket-array
   sizes; I did not `tracemalloc` an instance.

9. **The three-line DeepSeek handover is designed, not tried.** I did not write the modules, so I have
   not proven `from scripts.wire_live import wire_snapshot` resolves cleanly inside the running UI
   process — only that `scripts/bifrost_ui.py:26` inserts `REPO` on `sys.path`, which makes it
   importable in principle.

10. **`x-model` (C3) is asserted from SDK knowledge plus the 0/41 live population.** I did not read
    the installed `openai` package's header construction to prove no version sends it.

11. **Season 1 concurrency shape.** I assumed 20 players can produce simultaneous round trips. I did
    not read the season harness's launch logic to confirm whether players run concurrently or in
    waves, and the answer changes the burst amplitude in §6.1 substantially.
