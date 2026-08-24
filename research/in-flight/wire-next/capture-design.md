# Deep capture and layered dissection — the fidelity ceiling and how to reach it

**Seat:** opus5, dimension "Deep capture and layered dissection", 2026-08-04.
**Scope:** maximal FIDELITY. What more can we physically see, and how do we decode it in layers.
**Method:** every number below is either read from a committed probe artifact, read from source at a
cited `file:line`, or **measured by me tonight** on this box in a local experiment with no network
egress. Claims I could not run are labelled INFER. The appendix lists what I did not verify.

---

## 0. HEADLINE

The shipped transport (`scripts/wire_journal.py:322-341`) hooks the right seam and then reads almost
nothing through it. **Live evidence, `state/wire/wire-20260804.jsonl`, 27 records: 18 of the 24
record fields are `null` on every single record.** Populated: `ts`, `agent`, `status`, `attempt`,
`ms_first_byte`, `headers`. Everything else — `model`, `stream`, `system_fingerprint`,
`finish_reason`, all seven usage fields, `ms_total`, all three shas — is null 27/27.

That is not a defect in the design; it is the design's own boundary. `wire_journal.py:336-337` says
it plainly: *"The body is deliberately not read: touching resp.stream would consume the SSE stream
the caller is about to iterate."* The transport therefore sees the envelope and refuses the letter.

**This document's claim: the refusal is unnecessary, and I have proved the safe alternative works.**
A `SyncByteStream` interposer on `resp.stream` observes every byte the caller receives without
consuming one of them, and a second, entirely separate instrument — httpcore's `trace` extension —
decomposes the latency the current `ms_first_byte` silently conflates. Both were measured tonight.

---

## 1. WHAT THE EXISTING PROBES ACTUALLY CAPTURED (exact)

The brief asks me to say exactly what p2/p3 captured. Here it is, recomputed from the artifacts
rather than quoted from the prior summaries.

### 1.1 p2 — `wire-capture-deepseek-2026-08-02/p2-byte-chunks.json` + `p2-raw-sse.txt`

Captured by `probes.py:88-120`, using `httpx.Client.stream()` **directly, bypassing the SDK**, and
iterating `resp.iter_bytes()` with a `time.monotonic()` stamp per HTTP byte chunk (`probes.py:109-116`).

Recomputed by me from the two files:

| Quantity | Measured |
|---|---|
| HTTP byte chunks | **10** |
| SSE `data:` frames inside them (incl. `[DONE]`) | **35** |
| Total body bytes | **11,312** |
| Mean frames per HTTP chunk | **3.5** (range 1 → 5; chunk 0 = 1 frame / 341 B, chunk 4 = 1944 B) |
| Model output characters delivered | **114** (`content` + `reasoning_content` summed across all frames) |
| **Payload as a share of body bytes** | **1.01 %** |
| **SSE framing overhead** | **98.99 %** |
| Constant framing per frame | **~320 bytes** (of a 322-byte frame carrying `" asked"`) |
| Of which: `id` | 36 chars, repeated identically on all 35 frames |
| Of which: `system_fingerprint` | 43 chars, repeated identically on all 35 frames |

**The single most important structural fact p2 established: HTTP chunk boundaries are NOT SSE frame
boundaries.** 10 chunks carried 35 frames. The OpenAI SDK erases this — `SSEDecoder._iter_chunks`
re-frames on `\n\n` regardless of how the bytes arrived (verified by reading
`openai/_streaming.py::SSEDecoder._iter_chunks`; it accumulates into `data` and yields only on a
blank-line terminator). **Coalescing is therefore a transport-only observable.** Nothing above the
transport can ever tell you that five tokens arrived in one TCP segment.

Also captured, and present in `p2-raw-sse.txt:1-16`: the **full unfiltered response header set** on a
200 — 16 headers. Today's journal keeps 5 of them (`x-ds-trace-id`, `x-cache`, `x-amz-cf-pop`,
`content-type`, `server`) because `KEEP_HEADERS` at `scripts/wire_journal.py:65-67` allowlists 9 and
DeepSeek sends 5 of those 9. Dropped by the allowlist and never seen again: `via` (the CloudFront
chain), `x-amz-cf-id` (the per-request edge id, distinct from `x-ds-trace-id`),
`strict-transport-security`, `vary`, `access-control-allow-credentials`, `x-content-type-options`,
`cache-control`, `transfer-encoding`, `connection`, `date`.

### 1.2 p2's timestamps are quantized — and the quantum is 15.625 ms

`probes.py:110` stamps each chunk with `time.monotonic()`. Recomputed inter-chunk gaps:

```
453, 109, 47, 47, 47, 31, 47, 47, 47   (ms)
```

Divide by 15.625: `29.0, 7.0, 3.0, 3.0, 3.0, 2.0, 3.0, 3.0, 3.0`. Every gap is an integer number of
system ticks. I measured the clock on this box directly:

```
time.monotonic  implementation=GetTickCount64()          resolution 0.015625 s   observed steps: {15 ms, 16 ms}
time.time       implementation=GetSystemTimeAsFileTime() declared   0.015625 s   observed steps: ~0.5 ms
time.perf_counter QueryPerformanceCounter()              resolution 1e-07 s      observed steps: 0.3-0.7 us
```
(Python 3.11.9, Windows 11. Python 3.13 changed `monotonic()` to QPC; we are not on 3.13.)

**Consequence 1 — retroactive.** The "+0.047 s" figure quoted in
`api-wire-reverse-engineering-deepseek-2026-08-04.md:143` is **3 ticks**. The true gap lies somewhere
in ≈[31.25, 62.5) ms. p2's inter-token timing is real but has a ±15.6 ms error bar that has not been
stated anywhere. Any inter-token-latency analysis built on `time.monotonic()` on this box is
measuring the Windows scheduler as much as the model.

**Consequence 2 — forward.** `scripts/wire_journal.py:328` and `:340` compute `ms_first_byte` from
`time.time()`. That clock has ~0.5 ms observed granularity (fine) but is **adjustable** — an NTP step
mid-call produces a negative or inflated duration, silently. **All durations must come from
`time.perf_counter()`; `time.time()` is correct only for the wall-clock record stamp at
`wire_journal.py:112`.** Measured call cost: `perf_counter` 56.5 ns, `time.time` 37.3 ns,
`monotonic_ns` 35.2 ns. The 19 ns difference is not a reason to keep the wrong clock.

### 1.3 p3 — `p3-ttft-decomposition.json`

Captured by `probes.py:136-181`. Three SDK-level streamed calls, `max_tokens=8`, `temperature=0.0`,
timing the arrival of the **first content-OR-reasoning-bearing delta** (`probes.py:150-157`).

| Run | TTFT | Total | prompt_tok | cache hit / miss |
|---|---|---|---|---|
| run-1 cold | 0.859 s | 1.156 s | 23 | 0 / 23 |
| run-2 identical prompt | 0.813 s | 1.063 s | 23 | 0 / 23 |
| run-3 perturbed prefix | 0.890 s | 1.093 s | 23 | 0 / 23 |

**What p3 actually established is a negative result, and it is worth more than the timings.** A
23-token prompt is below DeepSeek's cache-block threshold, so all three runs report `cache_hit=0` —
including the byte-identical repeat. The experiment could not separate cache-hit prefill from
cache-miss prefill **because it never produced a cache hit**. The 0.05 s spread between runs is
within the noise of the three samples. p3 named the decomposition problem; it did not solve it.

It also confirmed, three times over, that `completion_tokens_details.reasoning_tokens == 8 ==
completion_tokens` while `content == ""` — the exact `runner_reasoning_eats_final_answer` signature,
sitting in a committed artifact, unread by any production code path.

### 1.4 p1, p4, p5, p6 — the rest of the battery, and one under-reported finding

- **p4** (`p4-forced-truncation.json`): 10 chunks, `finish_reason` is `null` on chunks 0-8 and
  `"length"` on chunk 9, which also carries `usage`. **Truncation is a last-frame-only property.**
  A dissector that samples frames cannot see it; it must observe the terminal frame.
- **p5** (`p5-rate-limit-headers.json`): the SDK result object has **no** `_response`. The full
  `dir()` is in the artifact. Settled: headers are transport-only.
- **p6** (`p6-extra-chunk-internals.json`, 16 chunks): top-level chunk keys are
  `['id','choices','created','model','object','service_tier','system_fingerprint','usage']`; choice
  keys `['delta','finish_reason','index','logprobs']`; delta keys
  `['content','function_call','refusal','role','tool_calls','reasoning_content']`. `model_extra` is
  `{}` on **all 16** chunks. `service_tier` is `None` on all 16 — so the `service_tier` field at
  `scripts/wire_journal.py:122` is a permanently-UNKNOWN column for this provider.
- **p1 — the under-reported one.** `p1-logprobs-stream.json` records `"status": "success"`, 10
  chunks, and **DeepSeek returns logprobs under `stream=True`, on the REASONING channel**:
  `ChoiceLogprobs(content=None, refusal=None, reasoning_content=[{token, logprob, bytes,
  top_logprobs:[3]}])`. Measured examples from the artifact: `' are'` at `-0.009482` (p = 0.9906) with
  alternatives `' need'` at `-4.663` (p = 0.0094) and `"'re"` at `-13.601`.

  **This is the floor of the visible stack and we have never used it.** It is per-token model
  confidence with the top-3 alternatives, on the thinking channel, and it costs **zero extra
  tokens**. I sized the wire cost: one token's logprobs object with `top_logprobs=3` serialises to
  **384 bytes**, against a 322-byte base frame — **a 2.19x increase in stream volume**. That is the
  honest price, and it is bandwidth and parse time, not money.

---

## 2. THE LAYERED DISSECTOR MODEL

Wireshark's actual architecture is not "log packets". It is a **dissector chain**: each layer parses
its own header, hands the remaining payload to the next dissector, and registers its fields into one
flat, queryable field space (`tcp.analysis.retransmission`, `http.time`, …). Every layer is
independently filterable, and a field's *absence* is distinct from its *zero*.

The same shape maps onto an LLM API call with six layers. **Each layer has exactly one instrument, and
the instruments are independent** — you can enable L1 without L3, or L3 without L5.

| Layer | Name | Instrument | Observable only here |
|---|---|---|---|
| **L0** | Connection | `network_stream` extension + httpcore `trace` | peer IP, TLS version/cipher/cert, connection reuse |
| **L1** | Transaction | `trace` extension phase events | TCP-connect vs TLS vs send vs server-wait vs body |
| **L2** | HTTP | `handle_request` request/response objects | status, all headers, request bytes, retries |
| **L3** | Transport framing | `SyncByteStream` tee on `resp.stream` | HTTP-chunk boundaries, coalescing, byte timing |
| **L4** | SSE frame | offline parse of the teed byte log | frame count, frame sizes, framing overhead, gaps |
| **L5** | Semantic | offline parse of frame JSON | delta kind, finish_reason, usage, tool-call assembly, logprobs |

The layer boundary that matters most: **L0-L3 are hot-path and must be microsecond-cheap; L4-L5 are
pure functions of L3's output and belong OFF the hot path entirely.** That single split is what makes
"overengineer to the max while retaining performance" a coherent instruction instead of a
contradiction. We capture at maximum fidelity in-line and dissect at maximum depth out-of-line.

### The field-space discipline

Every layer writes into one namespaced flat space, exactly as Wireshark does:

```
conn.peer_ip      conn.tls_version   conn.reused
txn.connect_ms    txn.tls_ms         txn.send_ms      txn.server_wait_ms
http.status       http.attempt       http.req_bytes   http.req_sha256
frame.n           frame.bytes        frame.gap_ms_p50 frame.coalesce_ratio
sse.first_token_ms  sse.first_content_ms  sse.stall_max_ms
sem.finish_reason   sem.reasoning_tokens  sem.tool_calls  sem.logprob_p50
```

`UNKNOWN` (`wire_journal.py:69`) applies per-field, per-layer. A record captured with L3 disabled has
every `frame.*` field UNKNOWN — never zero. This is the T141 vocabulary the existing journal already
declares; the dissector model just gives it a shape wide enough to be worth having.

---

## 3. L0/L1 — THE CONNECTION AND THE TRANSACTION. Verified tonight.

### 3.1 The instrument nobody has used: httpcore's `trace` extension

`httpcore` 1.0.9 (installed; verified) fires a user-supplied callback at named phase boundaries. The
mechanism is `Trace.trace()` at `httpcore/_trace.py:31-35`, which reads
`request.extensions.get("trace")`. Call sites: `httpcore/_sync/connection.py:123` (`connect_tcp`),
`:132`, `:155` (`start_tls`), `:164` (`retry`), `:172` (`close`); `httpcore/_sync/http11.py:83`
(`send_request_headers`), `:87` (`send_request_body`), `:97` (`receive_response_headers`), `:333`
(`receive_response_body`), `:134`/`:347` (`response_closed`).

**It costs nothing when off.** `_trace.py:28`: `should_trace = self.debug or self.trace_extension is
not None`. No extension, no logging → `__enter__` does not even build the info dict.

**Injecting it is one line inside our existing transport**, because `httpx.HTTPTransport.handle_request`
passes `extensions=request.extensions` straight through to the httpcore request (read from
`httpx/_transports/default.py::HTTPTransport.handle_request`):

```python
request.extensions = {**request.extensions, "trace": cb}   # before super().handle_request(request)
```

### 3.2 The measurement (my experiment, local server, no egress)

I stood up a loopback HTTP server that sleeps **250 ms before sending response headers** and a
further **150 ms before the first body frame**, then drove httpx through a transport carrying both
the trace callback and a stream tee. Result:

```
   ms  event
 0.08  connection.connect_tcp.started
12.32  connection.connect_tcp.complete            <-- 12.24 ms TCP connect, ISOLATED
12.41  http11.send_request_headers.started
12.87  http11.send_request_headers.complete       <-- 0.46 ms
12.89  http11.send_request_body.started
13.03  http11.send_request_body.complete          <-- 0.14 ms
13.04  http11.receive_response_headers.started
263.43 http11.receive_response_headers.complete   <-- 250.39 ms SERVER WAIT (injected 250 ms)
263.48 <transport returns>
263.73 http11.receive_response_body.started
413.94 [tee] first raw chunk, 58 bytes            <-- 150.2 ms headers->first token (injected 150 ms)
565.56 http11.receive_response_body.complete
565.80 http11.response_closed.complete
```

The instrument recovered both injected delays to **better than 0.4 ms**. The decomposition is real.

### 3.3 What this proves about the field we ship today

**`ms_first_byte` (`scripts/wire_journal.py:340`) is misnamed and conflated.** It is measured from
transport entry to `super().handle_request()` returning — which the trace shows is
`receive_response_headers.complete`. So it is **time-to-first-HEADER**, and it silently bundles:

```
ms_first_byte  =  DNS+TCP connect  +  TLS handshake  +  request send  +  server wait to headers
```

In the probe, the transport returned at 263 ms while the **first actual token byte arrived at 414
ms** — 151 ms later, entirely unmeasured. On the live journal the field reads `min 638 / p50 1023 /
p90 1336 / max 1414 ms` (n=27, computed by me from `state/wire/wire-20260804.jsonl`). Nobody can
currently tell whether a 1023 ms call spent 900 ms in the model or 900 ms in a TLS handshake to a
cold CloudFront edge.

**And the live data says the handshake question is not hypothetical.** Across those 27 requests I
counted **19 distinct `x-amz-cf-pop` values** (ATL58-P5, ATL59-P{1,3,5,7,8,11,13,17,18},
IAD12-P{1,2,3}, IAD55-P{3,10}, IAD61-P10, IAD89-P1). Per-PoP TTFH medians range from 638 ms
(ATL58-P5, n=1) to 1347 ms (ATL59-P13, n=1). Either connection reuse is not happening, or edge
selection varies per connection — **and `txn.connect_ms` + `txn.tls_ms` + `conn.reused` answer that
question directly, which nothing today can.**

### 3.4 L0 — what `network_stream` gives us

`httpcore/_sync/http11.py` returns `extensions={"http_version", "reason_phrase", "network_stream"}`
(read from source). `network_stream.get_extra_info(...)` accepts (verified in
`httpcore/_backends/sync.py:106-117` and `:173-184`): **`ssl_object`**, **`client_addr`**,
**`server_addr`**, `socket`, `is_readable`.

That yields, at zero marginal round trips:

- `conn.peer_ip` — `server_addr` is `getpeername()`: the actual resolved edge IP. Layer-3
  corroboration of `x-amz-cf-pop`, and the thing you correlate when a PoP misbehaves.
- `conn.tls_version`, `conn.tls_cipher` — `ssl_object.version()`, `.cipher()`.
- `conn.peer_cert_sha256` — `ssl_object.getpeercert(binary_form=True)` hashed. **This is the
  security-eyes hook Daniil asked for**: a changed certificate fingerprint on `api.deepseek.com` is
  exactly what an enterprise appliance alarms on, and it is one hash of bytes we already hold.
- `conn.alpn` — `.selected_alpn_protocol()`. `h2 4.3.0` **is installed**, so `http2=True` is
  available and is not currently used (`wire_journal.py:343` constructs the client without it).
  Everything today is HTTP/1.1; a dissector must handle the `http2.` trace prefix if that changes,
  because the prefix is derived from the logger name (`_trace.py:27`).

**Cost:** one `get_extra_info` call and, for the cert, one SHA-256 over ~1-2 KB — **do it once per
CONNECTION, not per request**, keyed on `id(network_stream)`. On reuse it is a dict lookup.

---

## 4. L2 — REQUEST-SIDE CAPTURE. Everything the SDK sends, pre-flight, for free.

The current transport reads `request.headers.get("x-model")` (`wire_journal.py:332`) — a header the
OpenAI SDK never sets, which is why `model` is null on 27/27 live records. The model is in the
**body**, and the body is sitting right there.

**Verified by me:** `httpx.Client.build_request(..., json=...)` memoizes the encoded body, so at the
transport `request.content` is plain bytes, **idempotent, with zero consumption risk**:

```
has _content: True     len(request.content): 125     idempotent read: True
```

This is the asymmetry that makes request-side capture cheap and response-side capture hard: **the
request body is already fully in memory; the response body is a lazy stream.**

### What becomes visible, all pre-flight

| Field | Source | Why it earns its place |
|---|---|---|
| `req.model` | body `model` | fixes the 27/27 null; catches silent model fallback |
| `req.stream` | body `stream` | fixes another 27/27 null |
| `req.n_messages`, `req.role_histogram` | body `messages` | context growth per turn, by role |
| `req.msg_chars[]` | per-message lengths | *where* the context is: one runaway tool result vs. even growth |
| `req.tools_n`, `req.tools_bytes` | body `tools` | **measured: 33 tools, 16,775 bytes** (`core/comm/toolbox.py::TOOLS`) resent on every single call |
| `req.max_tokens`, `req.temperature`, `req.reasoning_effort`, `req.thinking` | body | the settings that CAUSED the outcome — today an outcome is recorded with no record of its inputs |
| `req.tool_choice`, `req.response_format` | body | ditto |
| `req.sha256` | full body | **turns INFERRED retry into MEASURED retry** (§4.1) |
| `req.prefix_sha[]` | rolling hashes at message boundaries | *where* the cache prefix broke, not just that it did |

`req.tools_bytes = 16,775` is a standalone finding. Every DeepSeek call in the fleet carries ~16.4 KB
of tool schema, ~4k tokens, unchanging. Whether that sits inside the cacheable prefix is currently
unknown and is directly checkable once `req.prefix_sha[]` and `cache_hit_tokens` land in the same
record.

### 4.1 Retry detection: inferred today, measurable tomorrow

`wire_journal.py:316-320` infers a retry from *same URL + previous attempt non-2xx + within 120 s*,
and honestly labels it a heuristic (`:305-310`). **I verified the underlying premise empirically** —
a stub transport returning 500 then 200 under `OpenAI(max_retries=1)`:

```
transport handle_request calls: 2
  attempt 0 ('POST', 'https://api.deepseek.com/chat/completions', 71)
  attempt 1 ('POST', 'https://api.deepseek.com/chat/completions', 71)
caller saw: ok | finish: stop        <-- the 500 never reached the caller
```

This settles the claim the design doc listed as unverified
(`api-wire-visibility-design-opus5-2026-08-04.md:494-510`, P3): **SDK retries do surface as separate
`handle_request` calls**, with openai 2.24.0 + httpx 0.28.1.

It also shows the fix for the heuristic: **both attempts carry a byte-identical body**. Hashing the
request body (measured: **0.275 ms for 716 KB**) makes retry correlation exact — same sha + same URL
within the window = the same logical call, MEASURED rather than INFER. It additionally survives the
case the current heuristic cannot handle: two different logical calls to the same URL where the first
failed.

### 4.2 Measured cost of full request-side capture

Realistic bodies built from the real `TOOLS` schema plus synthetic context:

| Body size | `json.loads` + role/length shape | `sha256` (full body) | cheap byte scan |
|---|---|---|---|
| 22.5 KB (no context) | 0.041 ms | 0.010 ms | 0.002 ms |
| 70 KB | 0.076 ms | 0.028 ms | 0.022 ms |
| 219 KB | 0.204 ms | 0.087 ms | 0.068 ms |
| **716 KB (~180k tokens — the kimi-scale turn)** | **0.740 ms** | **0.275 ms** | 0.210 ms |

**Worst case ≈ 1.0 ms**, against a measured p50 TTFH of 1023 ms → **≈0.1 %**. And it is spent while
the socket is idle, before the request goes out.

**Degradation rule, stated so it is not lost:** above a `req_bytes` threshold (suggest 1 MB), skip
`json.loads` and fall back to the byte scan (`raw.count(b'{"role":')`, `len(raw)`), marking
`req.shape_method = "SCAN"`. Fidelity degrades to a named, visible state instead of latency growing
without bound.

---

## 5. L3 — STREAMING REASSEMBLY WITHOUT CONSUMING THE CALLER'S STREAM

This is the real hazard the brief names, and it is worth being precise about *why* it is a hazard and
*why* the fix is safe.

### 5.1 Why the naive approaches are wrong

- `resp.read()` / `b"".join(resp.iter_bytes())` in the transport: sets `_content` and flips
  `is_stream_consumed`; the caller's later `iter_raw()` raises `StreamConsumed` (read from
  `httpx/_models.py::Response.iter_raw`, first two lines). **It also destroys streaming semantics** —
  the runner's `_stream_turn` (`scripts/deepseek_chat.py:306`) would block until the last token and
  the live console (`:329-336`) would go dark.
- An httpx **response event hook** cannot help either: hooks receive the `Response` before the body
  is read, so a hook that wants the body must call `response.read()` — the same trap.

### 5.2 The correct instrument: a `SyncByteStream` interposer

`httpx.Response.stream` is a **plain, settable attribute** — assigned at
`httpx/_models.py::Response.__init__` in the `else` branch (`self.stream = stream`), with no property
guard. `Response.iter_raw()` iterates `self.stream` and `iter_bytes()` decodes `iter_raw()`. So
replacing `resp.stream` with a wrapper that yields the same bytes is **transparent by construction,
lazy, and driven entirely by the consumer's own pull**:

```python
class _Tee(httpx.SyncByteStream):
    __slots__ = ("inner", "t0", "sink")
    def __init__(self, inner, t0, sink): self.inner, self.t0, self.sink = inner, t0, sink
    def __iter__(self):
        sink, t0 = self.sink, self.t0            # hoist attribute lookups out of the loop
        for b in self.inner:
            sink.append((time.perf_counter() - t0, len(b)))   # NO parsing, NO copy
            yield b                                            # caller gets the SAME object
    def close(self):
        self.inner.close()                       # close MUST propagate or the socket leaks
```

**Verified byte-identical, twice.** Small probe: consumer received 4 chunks / 199 bytes, server sent
199, `BYTE-IDENTICAL: True`, tee saw each chunk in order at the right times. Large probe: 2000-frame
/ 656,014-byte response, `assert tot == len(PAYLOAD)` passed on every one of 60 requests.

**Five properties that make this safe, each with its reason:**

1. **Zero copy.** `yield b` hands the caller the *same* bytes object. We store `len(b)`, not `b`.
2. **Zero parsing on the hot path.** No `json.loads`, no `splitlines`. See §5.3 for the number.
3. **Lazy.** The tee only runs when the caller pulls. It cannot get ahead of, or starve, the consumer.
4. **`close()` propagates.** Verified in the small probe (`inner.closed: True`). A tee that forgets
   this leaks connections — this is the one line that must never be dropped.
5. **Exceptions pass through.** No `try/except` inside `__iter__`: a `ReadTimeout` mid-stream must
   still reach `Agent.send()`'s handler, which is the whole G4/L0 anti-wedge design
   (`scripts/deepseek_chat.py:58-63`). The tee must not be the thing that swallows a wedge. Guard the
   *sink append* if you must guard anything — never the yield.

### 5.3 Measured hot-path cost per HTTP chunk

Per HTTP chunk of 1640 bytes (5 real DeepSeek frames — matches p2's chunk 3):

| Variant | Cost | Verdict |
|---|---|---|
| (a) `perf_counter()` + `len()` append | **0.136 µs** | ship this |
| (b) + byte-scan frame count | 0.326 µs | optional |
| (c) + `json.loads` on every frame | **10.502 µs** | **77x (a). Never on the hot path.** |
| (d) `queue.put_nowait` handoff of the raw bytes | 0.639 µs | for tier-2 body capture |

Variant (c) is the trap: it duplicates work the SDK's `SSEDecoder` is about to do anyway, **inside
the consumer's own iteration**, on a stream that may run for minutes. At 2000 frames that is 21 ms of
pure duplicated parsing — small in absolute terms, and still the wrong architecture, because it grows
linearly with output length exactly when the operator is already waiting.

### 5.4 End-to-end A/B, and an honest note about it

Loopback server, 2000 frames, 656 KB, instrumented arm carrying **trace extension + tee + request
sha256 + request `json.loads` shape**, interleaved with the plain arm so drift hits both:

```
plain        median 20.982 ms   min 15.191
instrumented median 21.933 ms   min 15.544
DELTA        +0.952 ms  (+4.54%)      min-to-min +0.353 ms
```

**Be honest about what that is.** Two earlier non-interleaved runs of the identical code produced
−1.632 ms and +2.473 ms — the sign flipped. On a zero-latency loopback the delta is inside the noise.
The trustworthy figure is the analytic sum of the microbenchmarks (§4.2 + §5.3):

```
request sha256 (716 KB)      0.275 ms
request shape parse          0.740 ms
tee, 570 HTTP chunks         0.078 ms
trace callbacks (13/req)    <0.010 ms
                            ----------
worst-case total             ~1.10 ms   per API call
```

Against a **measured p50 TTFH of 1023 ms** on live traffic: **≈0.11 %**. Against a real multi-second
thinking turn: less. **The 4.54 % loopback figure is the ratio against a 21 ms request that does not
exist in production** — it is the stress-test denominator, not the operating one.

### 5.5 One correctness hazard nobody has stated

The tee sits on `resp.stream`, which is the **RAW, still-encoded** byte stream — `iter_raw()`
iterates `self.stream`, and `iter_bytes()` applies `self._get_content_decoder()` *after*. httpx sends
`accept-encoding: gzip, deflate` by default (I dumped the built request headers and confirmed it).

DeepSeek's SSE responses carry **no `content-encoding`** (verified: `p2-raw-sse.txt:1-16` lists 16
headers, none of them `content-encoding`), so today the tee sees plaintext. **But that is a provider
behaviour, not a guarantee**, and a non-streaming or a different-provider response may well be
gzipped. The dissector must branch on `content-encoding` and, when it is present, either decode in
the offline stage or mark every `frame.*` and `sem.*` field **UNKNOWN**. A dissector that
byte-scans gzip and reports "0 frames" is the measured-zero defect wearing a new hat.

---

## 6. TTFT DECOMPOSITION — what is separable, and what is not

Composing L1's trace events with L3's tee gives the following breakdown. Marked by whether the split
is **real** (two independent instruments bracket it) or **INFER** (a boundary we assign by
interpretation).

| Segment | Boundary | Separable? |
|---|---|---|
| DNS + TCP connect | `connect_tcp.started` → `.complete` | **REAL** — measured 12.24 ms in probe |
| TLS handshake | `start_tls.started` → `.complete` | **REAL** for https. *I did not exercise TLS* (§App) |
| Connection reuse | trace events absent for this request | **REAL** — their absence *is* the signal |
| Request upload | `send_request_headers.started` → `send_request_body.complete` | **REAL** — 0.60 ms in probe |
| **Server wait → headers** | `send_request_body.complete` → `receive_response_headers.complete` | **REAL** — 250.39 ms recovered from an injected 250 ms |
| **Headers → first byte** | headers complete → first tee chunk | **REAL** — 150.2 ms recovered from an injected 150 ms |
| First byte → first *reasoning* token | tee chunk 0 → first frame with non-empty `reasoning_content` | **REAL**, offline. p2 chunk 0 is the `role` preamble carrying `reasoning_content:""`; chunk 1 is the first real token, +453 ms |
| First reasoning → first *content* token | offline frame scan | **REAL**, offline |
| Decode rate | frame timestamps ÷ `completion_tokens` | **REAL**, offline |
| Stall detection | max inter-chunk gap from the tee | **REAL** — this is the "hung vs thinking" answer |
| **Queue vs prefill** | — | **NOT SEPARABLE.** Both live inside "server wait → headers". No header, no field, no timing distinguishes them from our vantage. |

**On queue-vs-prefill, the honest position.** Both the design doc
(`api-wire-visibility-design-opus5-2026-08-04.md`, §2.2 "Genuinely unavailable") and I agree it
cannot be decomposed directly. **But it can be attacked statistically, and that is worth stating
because it is the difference between "impossible" and "we did not try":** prefill time should scale
with `prompt_tokens` and drop sharply on a cache hit; queue time should not correlate with prompt
size at all but should correlate with time-of-day and with concurrent in-flight requests from our own
fleet. With `server_wait_ms`, `prompt_tokens`, `cache_hit_tokens`, and a fleet-wide concurrency count
in the same record, a regression of `server_wait_ms` on `prompt_tokens` gives a slope (ms/token =
prefill) and an intercept (≈ queue + fixed overhead). **That is an estimate, never a measurement, and
must be labelled so** — but it is a real, cheap analysis that requires only fields this design already
captures. It is the honest version of "seeing inside the black box".

`p3-ttft-decomposition.json` could not run it: three samples, one prompt size, zero cache hits.

---

## 7. L4/L5 — OFFLINE DISSECTION

The tee's output per call is a list of `(t_rel, nbytes)` plus, under tier-2 only, the bytes
themselves. **L4 and L5 are pure functions of that.** Running them off the hot path is not a
compromise; it is the only place they can run at full depth without a latency budget.

**L4 — SSE frame layer**, from teed bytes: frame count, per-frame byte sizes, **coalesce ratio**
(frames ÷ HTTP chunks — measured 3.5 on p2, and a *rising* ratio means the network is batching, i.e.
buffering somewhere between us and the model), inter-frame gap distribution (p50/p95/max), framing
overhead ratio (measured 98.99 %), and `[DONE]`-present (a stream that ends without it was cut).

**L5 — semantic layer**, per frame: delta kind (`role` | `reasoning_content` | `content` |
`tool_calls` | terminal), `finish_reason` (terminal frame only — see §1.4), the full `usage` block,
`system_fingerprint` **per frame** (p2 shows it repeated on all 35; a mid-stream change would mean the
provider swapped models *within one response*, which nothing currently could detect), tool-call
argument assembly across frames, and — if enabled — `logprobs`.

**Two derived signals that only exist once L4 and L5 are joined:**

1. **Reasoning-to-content transition time.** Index of the last `reasoning_content` frame → index of
   the first `content` frame, mapped back to L3 timestamps. This is the literal answer to "was it
   thinking or hung", and it is *not* obtainable from `usage` alone: `reasoning_tokens` tells you the
   count, never when they were spent.
2. **Confidence trajectory.** With logprobs on, `sem.logprob_p50` and the count of tokens under a
   threshold, per phase. A reasoning phase whose logprobs collapse is a *measurable* model-confusion
   signal. This is the deepest layer physically available and we have a committed artifact proving it
   works (§1.4).

**Where L4/L5 run.** Two options, and the choice is not mine to make:

- **(A) Bounded in-process queue + one background daemon thread.** `queue.put_nowait` measured at
  **0.639 µs**; on `queue.Full` drop and increment a counter (never block the runner — a telemetry
  queue that applies backpressure to the API stream is a self-inflicted stall). Gives near-live
  fields.
- **(B) Pure post-hoc.** The tee writes `(t_rel, nbytes)` only; tier-2 writes raw bytes to a rotating
  sink; a CLI verb dissects later. Zero runtime risk, no live L5 fields.

Option (A) inherits `docs/LIVE_CONSTRAINTS.md` and the wake-listener rule from
`[[wake-listener-must-be-harness-tracked]]` — a background thread in a runner process is a real
supervision question, not a free lunch. **INFER: (B) is the correct default and (A) is the upgrade
once a live reader exists to consume it.**

---

## 8. WHAT REMAINS GENUINELY INVISIBLE

Stated plainly, because the ceiling deserves as much precision as the floor.

**Invisible to any client, in or out of process:**
- Model internals: attention, MoE routing, sampler state, KV-cache internals. Logprobs are the floor.
- Queue time as a separate quantity (§6). Only statistically estimable.
- Batch-mate interference — whether our request shared a batch with other tenants.
- Which physical GPU/replica served us. `system_fingerprint` names a *build*, not an instance.
- Rate-limit headroom before a 429. Settled empirically: DeepSeek sends no rate-limit headers on 200
  (16 headers in `p2-raw-sse.txt:1-16`, none of them `x-ratelimit-*`), so two of the nine entries in
  `KEEP_HEADERS` (`wire_journal.py:66-67`) are permanently dead for this provider.
- The provider-side reason for a `content_filter` finish. Never observed by us in any case.

**Invisible to a transport hook but visible to a TLS-terminating proxy:**
- Encrypted-record boundaries and TLS-frame timing. `api-wire-reverse-engineering-deepseek-2026-08-04.md:255-257`
  argues this only matters under provider traffic shaping, for which there is zero evidence. I agree.

**Invisible only because we have not enabled it** (i.e. *not* a ceiling, a choice):
- Logprobs (§1.4) — off by default. 2.19x wire volume, zero token cost.
- HTTP/2 multiplexing observables — `h2 4.3.0` is installed; `http2=True` is not set
  (`wire_journal.py:343`).
- TLS cert/cipher (§3.4) — one `get_extra_info` away.
- Anything on kimi, gemini, or sol: **1 of 4 seats is instrumented.**
  `core/comm/runner_lib.py:14-27` has no `http_client` parameter, so
  `scripts/kimi_chat.py:85` and `scripts/gemini_chat.py:84` cannot be instrumented without touching
  it; `scripts/sol_chat.py:59-65` builds its own `OpenAI()` and is on the **Responses** API, whose
  SSE frames have a different shape (`response.output_text.delta` events rather than
  `choices[].delta`) — **INFER, from the API family, not verified by me.** L0-L4 are
  provider-agnostic; **L5 must be a per-dialect dissector.** That is the correct place for the
  variation, and it mirrors how Wireshark registers one dissector per protocol.

---

## 9. NAMED READERS — because a writer without a reader is the defect

`core/coord/cognitive_metrics.py` is the standing warning, and **T156 already has the same problem in
miniature**: `grep -rn "wire_journal" --include=*.py .` returns exactly three hits —
`scripts/deepseek_chat.py:85` (the writer), and two lines in `tests/test_t156_wire_journal.py`.
`summarize()` (`wire_journal.py:189`) and `expert()` (`:229`) exist and **nothing in production calls
either.** Every proposal here names its reader up front:

| Signal | Reader | Precedent |
|---|---|---|
| `txn.*` decomposition, `conn.reused` | a `doctor` line: "deepseek: p50 1023 ms = 12 connect / 250 wait / 761 decode" | `core/comm/doctor.py:1099` already reads `TokenJournal` from `core/` |
| `sem.finish_reason == "length"` + `sem.reasoning_tokens == completion_tokens` | `expert()` finding, promoted to a doctor warning | `wire_journal.py:240-243` already has the shape |
| `conn.peer_cert_sha256` change | `expert()` **error** finding — the security-eyes seed | `wire_journal.py:260-263` fingerprint-change precedent |
| `req.tools_bytes`, `req.prefix_sha[]` vs `cache_hit_tokens` | a cache-forensics CLI verb | `wire_journal.py:267-270` already tells the operator to compare prefix shas — with no tool to do it |
| `frame.*` L4 fields | a `wire dissect <call_id>` CLI verb, Wireshark's packet-detail pane | none — this is new |

**Nothing in this document should ship without its row filled in.**

---

## 10. CONTRADICTIONS (recorded, not resolved)

1. **P9 (the membrane pin) is already violated by its own precedent.**
   `api-wire-visibility-design-opus5-2026-08-04.md:445-447` would assert *"nothing under `core/`
   imports `scripts.wire_journal`"*. But `core/comm/doctor.py:1099` does
   `from scripts.runner_token_journal import TokenJournal` — the *only* proven telemetry-reader
   pattern in this repo crosses that line. Enforced literally, P9 forbids the wire journal from
   having a doctor reader, which §9 argues is the thing it most needs. Unresolved.

2. **`ms_first_byte` names one thing and measures another.** `wire_journal.py:340` and the field name
   say first byte; §3.3 shows it is first *header*, inclusive of connect and TLS. Whether to rename
   (breaking the 27 records on disk) or to add `ms_first_token` alongside is not my call.

3. **The RE doc understates its own p1 finding.**
   `api-wire-reverse-engineering-deepseek-2026-08-04.md:63` lists logprobs as
   *"(only when requested)"* in a NO column. The artifact shows top-3 logprobs streaming on the
   reasoning channel with usable values (§1.4). The design doc's "logprobs are the floor of the
   visible stack" is right; both docs then move on. Nobody has proposed using them.

4. **"Per-chunk timing costs one float per chunk"**
   (`api-wire-reverse-engineering-deepseek-2026-08-04.md:150`) is right about SDK-level chunks and
   wrong about what it buys. SDK-level timing measures **post-`SSEDecoder` frames**, which have
   already lost the HTTP chunk boundaries (§1.1). The proposed fix and the transport tee are
   different instruments measuring different layers; they are not substitutes.

5. **The design doc's tier-2 is "the least-verified part"**
   (`api-wire-visibility-design-opus5-2026-08-04.md:512-515`). §5.2 now verifies the tee mechanism
   itself, twice, byte-identical. The **memory-cliff** question it raises is still open — my probes
   stored `(t, len)` tuples, not bytes. A 656 KB response at ~570 chunks is ~570 tuples ≈ 46 KB of
   Python objects; retaining the *bytes* is where a cliff would live, and that is tier-2's problem,
   not the tee's.

6. **`service_tier` is a permanently-null column.** `wire_journal.py:122` records it; p6 shows it
   `None` on all 16 chunks. Harmless, but it is a field that will always read UNKNOWN for DeepSeek and
   should be labelled so rather than quietly carried.

---

## APPENDIX — WHAT I DID NOT VERIFY

**No live API call.** I made zero requests to `api.deepseek.com`. Every provider-behaviour claim comes
from the committed 2026-08-02 probe artifacts or from `state/wire/wire-20260804.jsonl`. My own
experiments all ran against a **loopback HTTP server I wrote**, in the scratchpad, with no egress.

**TLS was never exercised.** My trace probe used plain HTTP, so `connection.start_tls.started/complete`
**never fired in my run**. I read the call site (`httpcore/_sync/connection.py:155`) and the
`get_extra_info("ssl_object")` implementation (`httpcore/_backends/sync.py:106-117`), but the claim
that TLS handshake time and cert fingerprint are recoverable in practice is **read from source, not
observed**. Someone should run one https request with the trace callback attached before this is
treated as settled.

**HTTP/2 untested.** `h2 4.3.0` is installed; I did not enable `http2=True` or confirm that the trace
prefix becomes `http2.` (I inferred that from `_trace.py:27`, `logger.name.split(".")[-1]`). All my
measurements are HTTP/1.1.

**The A/B benchmark is noise-dominated and I say so in §5.4.** Three runs of identical code gave
−1.632, +2.473, and +0.952 ms. I report the analytic microbenchmark sum as the trustworthy figure. I
did **not** benchmark against a real API call, which is the only measurement that would settle it.

**The live journal is 27 records from one day, one agent, one provider, all HTTP 200.** The p50 TTFH
of 1023 ms and the 19-distinct-PoP count are real but thin. Zero non-2xx responses are present, so I
have observed no 429 and no `Retry-After` in live data.

**Retry proof used a stub, not a real provider failure.** §4.1's two-call result came from a fake
transport returning a synthetic 500. It proves the SDK↔transport contract; it does not prove DeepSeek
produces retryable failures in the shape I stubbed.

**`server_addr` / cert-fingerprint cost is estimated, not measured.** I did not benchmark
`get_extra_info` or `getpeercert(binary_form=True)`. The "once per connection, not per request"
recommendation follows from the cost being per-handshake, which is INFER.

**Sol's SSE dialect is inferred.** I read `scripts/sol_chat.py:59-65` and know it is the Responses
API; I did not read its streaming loop and did not verify the frame shape I asserted in §8.

**I did not read the runners.** `scripts/bifrost_runner_{deepseek,gemini,kimi,sol}.py` were not opened
except through targeted greps. A call built outside the four `make_client` factories would be invisible
to everything here, and the deepseek RE doc already found one such case
(`scripts/kimi_chat.py` uses `urllib` for a balance probe).

**The 98.99 % framing-overhead figure is from one 35-frame probe response** with `max_tokens=32`.
Longer responses have the same per-frame constant (~320 bytes) but more payload per frame once the
model emits multi-character tokens, so the true production ratio is lower and unmeasured.

**I did not verify that the tee composes with the SDK's retry path**, i.e. what happens to a
half-consumed teed stream when the SDK aborts and retries mid-body. §5.2's exception-passthrough rule
addresses it by construction, but it is untested.

**I did not verify `docs/LIVE_CONSTRAINTS.md` bus-lane implications** for the §7 option-(A)
background thread. I cited the file from the brief without opening it.
