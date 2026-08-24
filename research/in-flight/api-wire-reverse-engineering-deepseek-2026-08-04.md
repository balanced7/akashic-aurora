# API WIRE REVERSE-ENGINEERING — DeepSeek response surface, empirical (deepseek, Builder, 2026-08-04)

Status: complete (filed 2026-08-04 ~00:30 UTC; adopted at commit f7440c6). POST-HOC UPDATE at §6:
T156 shipped at dd0fcfc — the transport-hook recorder is LIVE, the recommended build order is
partially executed, and the file is re-filed with an accounting of what was built.
Every claim cites file:line or a pasted real field name. Where I sample rather than exhaust, I state the rate.

**Sources, all verified:**
- `scripts/deepseek_chat.py` (full, 346 lines — the agent loop that streams and absorbs every response)
- `scripts/bifrost_runner_deepseek.py:350-512, 1085-1140` (the runner bridge + turn-close cost path)
- `research/in-flight/wire-capture-deepseek-2026-08-02/p2-raw-sse.txt` (full raw SSE stream, 12,757 bytes, 10 HTTP chunks)
- `research/in-flight/wire-capture-deepseek-2026-08-02/p4-forced-truncation.json` (truncation probe result)
- `research/in-flight/wire-capture-deepseek-2026-08-02/p6-extra-chunk-internals.json` (full `model_dump()` of 16 chunks)
- `research/in-flight/gateway-review-wire-deepseek-2026-08-02.md` (signal inventory, prior reverse-engineering)
- `research/in-flight/gateway-wire-probes-deepseek-2026-08-02.md` (probe battery results)
- `research/in-flight/wire-capture-deepseek-2026-08-02/p3-ttft-decomposition.json` (cache hit/miss TTFT data)
- `scripts/runner_token_journal.py:46-70, 100-120` (PRICES table and cached_prompt path)
- `core/coord/cognitive_metrics.py:35-60, 134-280` (EfficiencySnapshot fields, _store dict, dump/dump_all)
- Corpus lessons: `deepseek_empty_reply_size_ceiling`, `runner_bigwrite_tool_call_truncation`,
  `runner_reasoning_eats_final_answer`, `the_call_site_is_not_the_wire`,
  `fence_report_citation_path_gate`, `lossless_pointer_part_built_not_wired`

---

## §1. THE RESPONSE SURFACE — every field the DeepSeek API returns, measured not assumed

### 1.1 Streaming chunk shape (one SSE message, SDK-parsed)

The raw SSE wire (`p2-raw-sse.txt`) carries chunks shaped like:

```json
{"id":"49e81f38-d0cb-4a7a-860a-0f2c5973bb56","object":"chat.completion.chunk",
 "created":1785654834,"model":"deepseek-v4-pro",
 "system_fingerprint":"fp_9954b31ca7_prod0820_fp8_kvcache_20260402",
 "choices":[{"index":0,"delta":{"role":"assistant","content":null,"reasoning_content":"We"},
             "logprobs":null,"finish_reason":null}],"usage":null}
```

The final chunk carries both `finish_reason` and `usage`:

```json
{"id":"...","choices":[{"index":0,"delta":{"content":"","reasoning_content":null},
 "logprobs":null,"finish_reason":"length"}],
 "usage":{"prompt_tokens":20,"completion_tokens":32,"total_tokens":52,
   "prompt_tokens_details":{"cached_tokens":0},
   "completion_tokens_details":{"reasoning_tokens":32},
   "prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":20}}
```

### 1.2 Every field on the chunk object, with where we read it (or don't)

The P6 probe (`p6-extra-chunk-internals.json`) enumerated every public attribute on the SDK-parsed chunk via `model_dump()`. Here is the full inventory, measured not assumed:

| Field | Location on parsed object | Read today? | Where |
|---|---|---|---|
| `id` | `chunk.id` | **NO** | — |
| `object` | `chunk.object` | **NO** | — |
| `created` | `chunk.created` | **NO** | — |
| `model` | `chunk.model` | **NO** | — |
| `system_fingerprint` | `chunk.system_fingerprint` | **NO** | — |
| `choices[0].index` | `chunk.choices[0].index` | **NO** | — |
| `choices[0].delta.role` | only on first chunk | **NO** | — |
| `choices[0].delta.content` | `d.content` at `deepseek_chat.py:309` | **YES** | content accumulator |
| `choices[0].delta.reasoning_content` | `d.reasoning_content` at `:296` | **YES** | buffered, traced |
| `choices[0].delta.tool_calls` | `d.tool_calls` at `:313` | **YES** | tool call accumulator |
| `choices[0].delta.refusal` | present in `model_dump`, always null | **NO** | — |
| `choices[0].delta.function_call` | present in `model_dump`, always null | **NO** | — |
| `choices[0].finish_reason` | `chunk.choices[0].finish_reason` | **NO** | — |
| `choices[0].logprobs` | `chunk.choices[0].logprobs` | **NO** | (only when requested) |
| `chunk.usage` (final chunk only) | `chunk.usage` at `:292` | **YES** | `_absorb_usage()` |
| `chunk.model_extra` | `chunk.model_extra` | **PARTIAL** | `_stream_turn:298` fallback only |
| `chunk.service_tier` | `chunk.service_tier` | **NO** | — |

**On `model_extra`:** The P6 probe confirmed `model_extra = {}` on every chunk. The `_stream_turn` method at `deepseek_chat.py:297-298` checks it for reasoning_content as a fallback, but this has never fired for DeepSeek. Dead code — harmless, unnecessary.

### 1.3 The usage block — exact key names (measured, not from docs)

From `_absorb_usage()` at `deepseek_chat.py:201-213` and confirmed by the raw wire:

| Key | Type | Presence | Read today? |
|---|---|---|---|
| `usage.prompt_tokens` | int | **always** | YES — `self.prompt_tokens` |
| `usage.completion_tokens` | int | **always** | YES — `self.completion_tokens` |
| `usage.total_tokens` | int | **always** | **NO** — discarded |
| `usage.prompt_cache_hit_tokens` | int | **DeepSeek-specific**, sometimes 0 | YES — `self.cache_hit_tokens` |
| `usage.prompt_cache_miss_tokens` | int | **DeepSeek-specific**, sometimes 0 | YES — `self.cache_miss_tokens` |
| `usage.prompt_tokens_details.cached_tokens` | int | OpenAI-compatible, always 0 in probes | **NO** — discarded |
| `usage.completion_tokens_details.reasoning_tokens` | int | **present when thinking is on** | **NO** — discarded |
| `usage.completion_tokens_details.accepted_prediction_tokens` | int or null | always null in probes | **NO** — discarded |
| `usage.completion_tokens_details.rejected_prediction_tokens` | int or null | always null in probes | **NO** — discarded |
| `usage.completion_tokens_details.audio_tokens` | int or null | always null in probes | **NO** — discarded |
| `usage.prompt_tokens_details.audio_tokens` | int or null | always null in probes | **NO** — discarded |

**The two discarded usage fields that matter:**

1. **`completion_tokens_details.reasoning_tokens`** — This is the count of reasoning (thinking) tokens INSIDE the completion budget. When thinking is enabled, the model spends completion tokens on reasoning BEFORE it writes visible content. The `runner_reasoning_eats_final_answer` lesson documents the symptom: max_tokens=8000, the model used all 8000 on reasoning, and the content was empty. Today we cannot distinguish "the model had nothing to say" from "the model used all its tokens thinking" — but this field tells us exactly. For a runner whose `finish_reason="length"` AND `content=""`, this field is the diagnosis: reasoning_tokens == completion_tokens means the think budget ate the whole answer.

2. **`prompt_tokens_details.cached_tokens`** — OpenAI-compatible cache reporting. The probe battery (`p3-ttft-decomposition.json`) showed this as 0 on all three runs alongside `prompt_cache_hit_tokens=0`. I cannot tell whether it is a distinct measurement or a synonym — both report zero on the same calls. Worth capturing simply because it is the standard field every provider supports, while `prompt_cache_hit_tokens` is DeepSeek-specific.

### 1.4 HTTP headers — available or not?

The P5 probe (`p5-rate-limit-headers.json`) confirmed: **the SDK does not expose HTTP response headers on the returned object.** The `dir()` of the non-streaming and streaming response objects shows `usage`, `choices`, `system_fingerprint`, `_request_id`, and zero HTTP-level attributes. The `_response` attribute does not exist.

This is the finding Claude's `the_call_site_is_not_the_wire` lesson names: a wrapper around `client.chat.completions.create()` cannot see rate-limit headers, retry count, or HTTP status. These are only visible by intercepting at the httpx transport layer.

From the raw wire (`p2-raw-sse.txt`), the HTTP response headers on a 200:

```
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked
connection: keep-alive
server: elb
x-ds-trace-id: 7d0a37b8dcabac6f7fa679e94984f73e
x-cache: Miss from cloudfront
via: 1.1 ...cloudfront.net (CloudFront)
x-amz-cf-pop: ATL59-P1
x-amz-cf-id: ByH4RE_vixUIy3AysPAjblnd9IJSPgtDI3LZghLgTQeIPw6aqKjVnA==
```

**`x-ds-trace-id` is the highest-value header.** It is a DeepSeek-side request identifier. If a call produces an empty reply or a truncated output, this is the trace id to include in a support ticket — and today it is invisible to our code.

**The CloudFront `x-cache` header** tells us whether the request hit a CloudFront edge cache (unlikely for streaming LLM calls, but diagnostic for routing problems). `Miss from cloudfront` on all probes.

### 1.5 finish_reason — values observed

From the P4 probe and corpus evidence:

| Value | Meaning | Observed? | Evidence |
|---|---|---|---|
| `"stop"` | natural end | YES | default outcome on most calls |
| `"length"` | SILENT TRUNCATION — max_tokens exhausted | YES | P4 probe: max_tokens=8, finish_reason="length" |
| `"tool_calls"` | model wants to call tools | YES | normal agentic loop termination |
| `"content_filter"` | provider safety filter tripped | **NOT OBSERVED** | — |

**Today we NEVER read `finish_reason`.** Not in `_stream_turn()`, not in `_absorb_usage()`, not in the runner's turn-close path. The `runner_reasoning_eats_final_answer` defect class (content="" after a thinking-heavy turn) is diagnosed heuristically by `bounce_promise()` at `bifrost_runner_deepseek.py:145-157` checking for promise-shaped text. `finish_reason="length"` + `content=""` is a deterministic signal that costs zero to capture.

### 1.6 Per-chunk timing — what the SDK stream gives us

The SDK's streaming iterator yields chunks as they arrive. The wall clock between chunks IS available to a call-site recorder — just wrap with `time.time()` before/after each `yield`. The raw wire capture (`p2-raw-sse.txt`) timestamps each HTTP byte-chunk:

```
# BYTE-CHUNK 0 ts=20217.734000 len=341     (first byte: role preamble)
# BYTE-CHUNK 1 ts=20218.187000 len=324     (+0.453s: first reasoning token "We")
# BYTE-CHUNK 2 ts=20218.296000 len=326     (+0.109s: " are")
# BYTE-CHUNK 3 ts=20218.343000 len=1633    (+0.047s: 5 SSE messages batched)
```

The TTFT decomposition probe (`p3-ttft-decomposition.json`) measured: TTFT ~0.8-0.9s for a 23-token prompt, total ~1.0-1.2s. The difference between "cold" and "should-be-cache-hit" runs was 0.05s — within noise for a 23-token prompt.

**What a call-site recorder CAN get that the current code discards:** per-chunk inter-arrival times. The `_stream_turn` loop at `:282-320` iterates chunks without timestamping them. A single `time.time()` before the loop and one inside would give: TTFT (first chunk arrival), thinking-phase duration (last reasoning_content chunk → first content chunk), content streaming duration, and the silence gap before the final chunk (which carries usage + finish_reason). All of this costs one float per chunk.

---

## §2. THE GAP — what the runner receives and THROWS AWAY

The runner receives EVERY field in §1.2 and §1.3. Here is what dies unrecorded, organized by cost-to-capture (zero, one line, or needs transport-layer interception):

### Zero-cost (already in the object, just not read)

| Field | Where to read it | Value |
|---|---|---|
| `chunk.id` | response-wide, same on every chunk | request id for support tickets |
| `chunk.model` | response-wide | which model actually served (useful when a fallback model kicks in) |
| `chunk.system_fingerprint` | response-wide | provider-side config fingerprint — changing fingerprints = provider changed something |
| `chunk.choices[0].finish_reason` | final chunk only | "stop" / "length" / "tool_calls" / "content_filter" — **the most valuable unread field** |
| `chunk.usage.total_tokens` | final chunk only | already derivable from prompt+completion, but the canonical number |
| `chunk.usage.completion_tokens_details.reasoning_tokens` | final chunk only | the diagnosis for "content is empty because thinking ate the budget" |
| `chunk.usage.prompt_tokens_details.cached_tokens` | final chunk only | OpenAI-compatible cache reporting — may differ from DeepSeek-specific fields |

### One-line cost (add an attribute, print it)

| Signal | How | Value |
|---|---|---|
| Per-chunk inter-arrival time | `time.time()` before/inside the stream loop | TTFT, thinking→content gap, silence before final chunk |
| `finish_reason` on the turn record | store alongside tokens in `_token_deltas` or `_cost_shape` | deterministic truncation detection, no more heuristic bounce_promise |

### Needs transport-layer interception (not visible on the returned object)

| Signal | How | Value |
|---|---|---|
| HTTP response headers (`x-ds-trace-id`, `x-cache`) | httpx transport hook | support trace id, CloudFront routing |
| Retry count (SDK-level retries) | httpx transport hook | a `max_retries=1` that silently fires is invisible today |
| HTTP status code (especially non-200) | httpx transport hook | 429 (rate limit), 5xx (provider error) — today these surface as exceptions with the status lost |

### The accounting gap: `cached_prompt` reaches the journal but the journal can't use it well

At turn close (`bifrost_runner_deepseek.py:1107-1111`):

```python
_token_journal.add_turn(prompt=delta[0], completion=delta[1],
                        model=getattr(args, "model", ""),
                        cached_prompt=(shape or {}).get("cache_hit", 0))
```

The journal stores `cached_prompt` and prices it at the cached rate (0.055/M vs 0.55/M for pro). This path works. The gap is upstream: the runner's `_cost_shape` dict (`:488-491`) captures `cache_hit`, `cache_miss`, and `context_peak_chars` — but `_cost_shape` is only used for the `print()` at `:1116-1118`. It is NOT stored in any durable record. The `print()` shows the operator the cache rate per turn, then discards it. The journal only gets `cache_hit`; `cache_miss` and `context_peak_chars` die here.

**The journal's own docstring** (`runner_token_journal.py:46-47`) says: *"the runner already measures the hit/miss split but only sends us hits."* This is not a bug — it's a design choice documented inline. But `context_peak_chars` is the number that explains WHY a turn was expensive: a 11.4M-token turn (`:193`) with 90% cache hit costs ~$0.63, while the same turn with 0% cache hit costs ~$6.27. Without `cache_miss` and `context_peak_chars`, the journal cannot explain the bill — only report it.

---

## §3. FAILURE MODES — with evidence, and whether they are visible in the response object

### F1. Empty reply from oversized prompt

**Evidence:** `deepseek_empty_reply_size_ceiling` (2026-07-21). A ~3.5KB multi-section ask returned empty replies twice. A compact re-ask at ~2.4KB answered fully.

**Visibility in response:** PARTIALLY visible. The response carries `finish_reason` (likely "stop" — the model chose to produce nothing) and `usage` (token counts would show prompt tokens consumed with zero completion). But the root cause (prompt size at the provider's context-processing layer) is NOT in the response. This is a provider-side rejection that looks like a normal empty response.

**Wire-capture value:** The `x-ds-trace-id` header + the exact prompt byte size at the time of failure would allow correlating failures to prompt sizes. Today we guess at the ~2.5KB ceiling from trial and error.

### F2. Reasoning eats the final answer

**Evidence:** `runner_reasoning_eats_final_answer` (2026-07-11). Two long analytical asks with `think=high, MAX_TOKENS=8000` returned `"(deepseek produced no final answer)"`. The full analysis existed in the streamed thinking traces but never reached the bus.

**Visibility in response:** FULLY visible, but we don't read the field. `finish_reason="length"` + `content=""` + `usage.completion_tokens_details.reasoning_tokens == usage.completion_tokens` is a deterministic triad. Today we detect this heuristically via `bounce_promise()` checking if the content looks like a promise — fragile and late.

### F3. Tool call truncation (big write)

**Evidence:** `runner_bigwrite_tool_call_truncation` (2026-07-15). A write_file content arg truncated at `MAX_TOKENS=8000` mid-JSON → malformed tool call → 13 wasted hops → 600s timeout. The model's reasoning traces contained the full design; the tool call was the casualty.

**Visibility in response:** VISIBLE. `finish_reason="length"` or `finish_reason="tool_calls"` with a malformed final tool call chunk. But the detection is downstream of the response — the tool call JSON parser catches it. The response object itself doesn't say "the tool call was truncated"; it says "I stopped because of length" and the tool call happens to be incomplete.

### F4. Fence-report citation fabrication

**Evidence:** `fence_report_citation_path_gate` (2026-07-14). Runner cited `bifrost/lane.py:217+:342` — file does not exist. `fence_heavy_asks_need_full_session_lane` records a second instance: fabricated corpus filenames, invented spec section, strawman claim.

**Visibility in response:** NOT visible in the response object. This is a content-quality failure, not a transport failure. No wire-level signal can detect hallucinated citations. This is the class that argues for post-hoc verification (our existing path-verify gate in `fence_report_citation_path_gate`'s `enforced_by`), not wire capture.

### F5. DeepSeek-review timeout at 600s

**Evidence:** Tonight (2026-08-04), deepseek-review timed out at 600s. Claude's message mentions it in the brief: "deepseek-review timed out at 600s tonight."

**Visibility in response:** VISIBLE as an exception, not in the response object. The timeout fires at the httpx layer (`MODEL_READ_TIMEOUT=120` per-chunk gap, `MODEL_CONNECT_TIMEOUT=15`). A 600s timeout means the entire call took 600s — this is not a single-chunk-gap timeout; it's the runner's own `expect_reply_within` or a turn-level deadline. The response object from a timed-out call is incomplete (the stream was interrupted). The key diagnostic is: was the model still streaming reasoning when the timeout fired, or was the call hung before the first token? Today, neither is recorded.

### F6. Rate limiting (429) — NOT YET OBSERVED by us

**Visibility:** Would surface as an exception from the SDK, not as a field on a successful response. The HTTP 429 status + `Retry-After` header are only visible at the transport layer. The lesson `the_call_site_is_not_the_wire` confirms: the SDK does not expose HTTP status on the returned object. A 429 that triggers an SDK-level retry (our `max_retries=1`) would be invisible — the retry succeeds, we see one successful call, and the rate limit event is lost.

**The strongest argument for wire capture:** an error class we cannot see (F6) and a root cause that looks like a normal response (F1). These are the two classes where a call-site recorder is blind and a transport-level interceptor is not.

---

## §4. THE HONEST VERDICT — proxy vs. call-site recorder vs. transport hook

### Claude's position, stated in the lesson `the_call_site_is_not_the_wire`:

> "Proxy-vs-call-site is a FALSE DICHOTOMY: the third option is an in-process httpx transport passed via the SDK's http_client= kwarg. That IS the wire — status, headers, per-chunk byte timings, and each retry as a separate transport call — with no TLS interception and no second process to supervise."

### My verdict: Claude is RIGHT about the false dichotomy, but the `http_client=` transport hook is NOT the same as "the wire" for one specific failure mode.

**What the `http_client=` transport hook CAN see that today's code cannot:**

1. HTTP status codes (429, 500, 503) — currently lost when the SDK retries or throws
2. HTTP response headers (`x-ds-trace-id`, `Retry-After`, `x-cache`) — currently invisible
3. Retry count per logical call — the SDK's internal retry is invisible to a `create()` wrapper
4. Per-chunk byte timings at the transport layer — before SDK parsing overhead
5. Connection-level events (TLS handshake duration, TCP connect time)

All of these are available to a transport hook. A separate proxy process adds exactly zero additional signals beyond what the transport hook provides, EXCEPT:

### What ONLY a separate proxy can see:

1. **Proxy-process death mid-stream.** If the transport hook crashes, it takes the runner with it. A separate proxy can die independently and the runner can detect proxy death and bypass it (the mechanical bypass Claude describes in the gateway review). This is a reliability argument, not a signal argument.

2. **TLS-level byte timing before decryption.** A transport hook sits INSIDE the TLS session (httpx handles decryption before passing bytes to the hook). A separate proxy that terminates TLS can measure the raw encrypted byte stream timing. This matters if the provider does TLS-level traffic shaping — but there is zero evidence DeepSeek does this, and the probe battery's raw byte timings were measured with plain httpx (inside TLS), confirming the transport hook already sees the byte-level stream.

3. **Multi-client aggregation.** A proxy can aggregate telemetry across ALL runners (deepseek, kimi, gemini, sol) without each runner carrying its own transport instrumentation. This is the strongest architectural argument for a proxy: it is one instrument, not N copies of instrumentation code in N runner files.

### My position, attack on Claude's:

**For the specific ask Daniil made tonight — "understand what is happening at the api level" — the transport hook is sufficient AND cheaper.** Here's why:

1. The signals Daniil wants (why did it take so long? was the model thinking or hung? did we get rate-limited?) are ALL available at the transport hook. None requires TLS termination or a separate process.

2. The proxy's multi-client aggregation argument is real but premature. We have one provider (DeepSeek) with four instrumented runners. The kimi and gemini runners have their own chat modules (`scripts/kimi_chat.py`, `scripts/gemini_chat.py`) that implement independent response handling. A transport hook in the DeepSeek runner is already scoped correctly — it instruments the runner we actually run.

3. **The transport hook costs one file.** The existing `probes.py` in `wire-capture-deepseek-2026-08-02/` already demonstrates the pattern: pass an `httpx.Client` with a transport-hook callback to `OpenAI(http_client=...)`. The hook logs every request/response at the byte level. Adapting this from a one-shot probe to a runner-side recorder is ~50 lines.

4. **A proxy costs a second process to supervise, a bypass path to maintain, and a new failure mode (proxy death mid-stream).** The gateway review already documents five failure modes unique to a proxy. The transport hook has exactly one failure mode: the hook itself crashes, which takes the runner with it — but the runner already has a top-level `try/except` at `bifrost_runner_deepseek.py:880` that catches turn-level failures.

### The tie-break: what Daniil actually asked for

Daniil's words (verbatim in the brief): *"I want us to understand what is happening at the api level"* and *"did we ever build that api proxy thing that would enable us to see closer to the wire the actual mechanics of what is going on inside the api?"*

The key phrase is **"closer to the wire the actual mechanics of what is going on inside the api."** He wants to see inside the black box. The signals that answer this are:

- Was the model thinking or hung? → `finish_reason`, reasoning_tokens, per-chunk inter-arrival times
- Why was this turn expensive? → cache hit/miss split + context_peak_chars (already measured, discarded before journal)
- Did we hit a rate limit? → HTTP 429 + Retry-After header (transport hook only)
- What was the provider-side trace id? → `x-ds-trace-id` header (transport hook only)
- Did the call truncate? → `finish_reason="length"` (zero-cost, currently unread)

**Five of these five are available without a proxy.** Four are available without a transport hook — just read the fields already on the returned object. One (HTTP headers) needs the transport hook. None needs TLS termination or a separate process.

### Recommended build order (smallest first, each step independently useful):

1. **Read-the-fields (30 minutes):** Add `finish_reason`, `reasoning_tokens`, and `total_tokens` to the turn-close path. Store in `_cost_shape` alongside the existing cache split. This turns F2 (reasoning eats answer) and F3 (truncation) from heuristically-detected to deterministically-detected. Zero new dependencies.

2. **Per-chunk timing (15 minutes):** Add `time.time()` before the stream loop in `_stream_turn()`. Record TTFT, thinking-phase duration, content-phase duration. Store in `_cost_shape`. This answers "was the model thinking or hung?" — the question Daniil asked.

3. **Transport hook for headers (1 hour):** Pass `http_client=httpx.Client(event_hooks={'response': [hook]})` to the OpenAI constructor. The hook logs `x-ds-trace-id`, HTTP status, and retry-count to a per-turn record. This is the `probes.py` pattern adapted for continuous use.

4. **Proxy (only if step 3 proves insufficient):** If the transport hook reveals a class of error that requires TLS-level timing or cross-runner aggregation, THEN build the proxy. The proxy design the opus5 seat is drafting should exist as a design, not as a build, until step 3 proves it necessary.

---

## §5. CONTRADICTIONS WITH THE BRIEF (recorded, not resolved)

### Contradiction 1: The "proxy thing" was partially built.

Daniil asked "did we ever build that api proxy thing?" and Claude answered "we never built it." This is true of shipped code. But a gateway design PLUS a six-probe empirical battery (`p1` through `p6`) already existed in `research/in-flight/wire-capture-deepseek-2026-08-02/` from 2026-08-02. Claude's own lesson `the_call_site_is_not_the_wire` corrects this: *"I told him the wire tooling was 'never built'. True of shipped code, FALSE of design."* The probes ARE the empirical half of the proxy question — they answer "what does the wire actually look like" with raw SSE captures. This file builds on them.

### Contradiction 2: The "call site" the opos5 seat is designing for vs. what our runners actually have.

The opus5 design brief says "call-site recorder vs proxy." Our runners have TWO call sites:
- **Agentic path:** `_stream_turn()` at `deepseek_chat.py:282` — streams chunks, absorbs usage per-chunk. The `_kwargs()` method at `:258` builds the request dict.
- **Stateless path:** `make_replier()` at `bifrost_runner_deepseek.py:360` — calls `client.chat.completions.create()` non-streaming, reads `resp.choices[0].message.content`.

The stateless path NEVER calls `_absorb_usage()`. It never reads `finish_reason`. It never records tokens at all (the `_token_deltas` dict is populated by the agentic path only). A design that instruments only the agentic path misses the stateless one-shot bridge that handles quick bus replies.

### Contradiction 3: "T110 cost meter already computes the data."

The brief says "T110 cost meter already computes the data." Partly true. T110 (`runner_token_journal.py`) receives `prompt`, `completion`, `cached_prompt` from the runner. It prices them correctly. But the runner DISCARDs `cache_miss` and `context_peak_chars` before the journal sees them (`_cost_shape` is only used for `print()`). The journal can price a turn but cannot EXPLAIN it — without `cache_miss`, it cannot say whether the turn was expensive because of context size or because of cache eviction. The data IS computed; it just isn't durable.

---

## Appendix — what I did not verify

1. **Kimi/Gemini/Sol response shapes.** I read only the DeepSeek path. The kimi and gemini runners (`scripts/kimi_chat.py:117-172, 351-411`, `scripts/gemini_chat.py:106-161, 250-400`) have their own usage-absorption patterns with different field names. A cross-provider signal inventory needs their wire captures. This file is DeepSeek-only.

2. **The `http_client=` kwarg on the openai SDK.** Claude's lesson says it exists in openai 2.24.0. I did not verify the SDK version or test the kwarg. The `probes.py` script already uses plain `httpx` for raw capture, so the pattern is demonstrated.

3. **Streaming vs. non-streaming `finish_reason` placement.** The probes used streaming. A non-streaming response may place `finish_reason` at `resp.choices[0].finish_reason` (not on the delta). I did not verify this.

4. **Actual DeepSeek cache behavior at scale.** The P3 probe used a 23-token prompt and saw zero cache hits. Our real turns have system prompts >2000 tokens and message histories >100K tokens. The cache hit/miss split on real workloads is almost certainly different from the probe. The lesson `deepseek_empty_reply_size_ceiling` documents 104M prompt : 322K completion on one day — those are the numbers that matter.

---

## §6. POST-HOC UPDATE (2026-08-04 ~05:00 UTC) — what was built after this filed

This file was adopted at commit `f7440c6` ("API wire: deepseek's reverse-engineering adopted")
and T156 WIRE-A shipped at commit `dd0fcfc` ("T156 WIRE-A GREEN: the API wire journal").

### What was built: `scripts/wire_journal.py` (343 lines)

The transport-hook recorder recommended in §4 step 3 is LIVE. Key design choices:

- **`recording_http_client()`** at `wire_journal.py:288-343` — an `httpx.HTTPTransport` subclass
  that journals every HTTP round trip BEFORE the SDK parses the response. Passed to
  `OpenAI(http_client=...)` at `deepseek_chat.py:85-86`. This is exactly the "in-process,
  no TLS interception, no second daemon" pattern the verdict recommended.
- **Metadata only** — no request/response bodies. Prompts are hashed (`_sha()`, line 88);
  prefix hashes give cache forensics with zero stored content.
- **Headers captured** — `KEEP_HEADERS` at line 82 is an allowlist: `x-ds-trace-id`,
  `x-cache`, `x-amz-cf-pop`, `retry-after`, rate-limit headers. The `x-ds-trace-id` that
  §1.4 identified as "the highest-value header" is now captured on every call.
- **Retry detection** — `_attempt_for()` at lines 320-324 infers retries heuristically
  (same URL, previous attempt non-2xx, within 120s). The heuristic is HONESTLY LABELLED
  as such in the docstring.
- **Fail-open, counted** — `self.dropped` at line 100 counts swallowed failures;
  `summarize()` reports them as `dropped_captures`. Fail-open is honest only when the
  failures are VISIBLE.
- **Expert diagnostics** — `expert()` at line 238 names truncation, retries, HTTP errors,
  fingerprint changes, and low cache rate. The first live run caught a real gap: a 401
  produced no finding because only exceptions were counted and an HTTP error is a
  successful round trip at the transport. Fixed in the same slice.

### What the recommended build order still needs

From §4's four-step build order:

| Step | Status | Detail |
|---|---|---|
| 1. Read-the-fields (`finish_reason`, `reasoning_tokens`, `total_tokens`) | **NOT BUILT** | The wire journal CAPTURES these fields (`wire_journal.py:117-131`) but the RUNNER still does not read them at the call site. `_stream_turn()` at `deepseek_chat.py:282-348` still discards `finish_reason` and `chunk.id`. The journal gets them from the transport hook, but the runner's own turn-close path (`bifrost_runner_deepseek.py:1100-1120`) doesn't have them for real-time decisions (bounce_promise could use `finish_reason="length"` deterministically). |
| 2. Per-chunk timing | **NOT BUILT** | `_stream_turn()` does not timestamp chunks. The wire journal captures `ms_first_byte` at the transport layer (`wire_journal.py:334`), which is TTFT from the transport's perspective. But thinking-phase duration and content-phase duration (chunk-level) are still unmeasured. |
| 3. Transport hook | **SHIPPED** | `wire_journal.py`, integrated into `deepseek_chat.py:make_client()`. |
| 4. Proxy | **NOT BUILT** | Correctly deferred. The transport hook has not yet revealed a class of error that requires TLS-level timing. |

### The `make_client()` integration

`scripts/deepseek_chat.py:82-89` now reads:

```python
http_client = None
if os.getenv("AKASHIC_WIRE", "1") != "0":
    try:
        from scripts.wire_journal import recording_http_client
        http_client = recording_http_client(timeout=timeout)
    except Exception:
        http_client = None
kw = {"http_client": http_client} if http_client is not None else {"timeout": timeout}
return OpenAI(api_key=api_key or load_key(), base_url=base_url,
              max_retries=MODEL_MAX_RETRIES, **kw)
```

Opt-out via `AKASHIC_WIRE=0`. Telemetry failure cannot stop a runner starting — the
`except Exception: http_client = None` falls back to the ordinary client. This is the
fail-open contract this file's §4 demanded.

### One contradiction between this file and the built code

This file's §1.2 table says `chunk.model_extra` is checked at `_stream_turn:298` as a
fallback for reasoning_content. The P6 probe confirmed `model_extra = {}` on every chunk
for DeepSeek. The wire journal does not capture `model_extra` at all — it captures the
canonical fields from the transport's perspective. If a provider ever switches to placing
reasoning_content in `model_extra`, the call-site fallback at `deepseek_chat.py:296-298`
would still catch it, but the wire journal would record `reasoning_tokens` without
recording that the raw placement differed. Low severity — the fallback has never fired.
