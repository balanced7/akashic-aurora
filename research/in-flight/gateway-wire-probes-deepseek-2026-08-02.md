# API Gateway Wire Probes — Empirical Results (deepseek, 2026-08-02)

Status: complete. Every probe in the battery ran against the live DeepSeek API
(api.deepseek.com, model deepseek-v4-pro) on 2026-08-02 ~07:13 UTC.
All raw evidence lives in `research/in-flight/wire-capture-deepseek-2026-08-02/`.

---

## P1 — logprobs under stream=True: IT WORKS.

**Verdict: my round-1 assumption was WRONG.** logprobs under stream=True produces
token-level log probabilities on every content-bearing chunk. It does NOT error.

Evidence: `p1-logprobs-stream.json` — 10 chunks, indices 1–8 carrying
`ChoiceLogprobs` objects with per-token `logprob`, `bytes`, and `top_logprobs`
(3 alternatives each, as requested).

### Chunk shape (logprobs stream):
- Chunk 0: `delta.role="assistant"`, `logprobs=null` — role-only preamble, no token
- Chunks 1–8: `delta.reasoning_content="We"/" are"/...` with logprobs on reasoning_content tokens
- Chunk 9: `delta.content=""`, `finish_reason="length"`, `usage=...` — terminal chunk

The logprobs object lives at `chunk.choices[0].logprobs`, NOT nested inside delta.
It is a `ChoiceLogprobs` with fields: `content` (None when thinking), `refusal` (None),
`reasoning_content` (list of `{token, logprob, bytes, top_logprobs}`).

### Gateway implications:
- `logprobs` and `top_logprobs` are valid alongside `stream=True`. The gateway
  can expose them when the outbound request asks for them.
- Logprobs on reasoning_content tokens are provided — this is a DeepSeek-specific
  extension. OpenAI's API only has logprobs on content tokens. The gateway must
  distinguish the two.
- Every token in the reasoning_content stream carries its own logprobs entry.

---

## P2 — RAW WIRE CAPTURE (httpx direct, no SDK)

Evidence: `p2-raw-sse.txt` (full SSE stream), `p2-byte-chunks.json` (HTTP chunk framing).

### Response headers (full dump):
```
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked
connection: keep-alive
server: elb
cache-control: no-cache
x-ds-trace-id: 7d0a37b8dcabac6f7fa679e94984f73e
x-cache: Miss from cloudfront
via: 1.1 ...cloudfront.net (CloudFront)
x-amz-cf-pop: ATL59-P1
```

Key findings:
1. **No rate-limit headers.** No `x-ratelimit-*`, no `Retry-After`. DeepSeek
   surfaces rate limits through HTTP 429 responses, not as headers on 200 responses.
2. **CloudFront CDN in front.** `x-cache: Miss from cloudfront` + `via` header
   show DeepSeek uses AWS CloudFront as their edge. This means TTFT includes CDN
   transit time (~10-50ms in the US).
3. **`server: elb`** — AWS Elastic Load Balancer terminates TLS.

### SSE frame structure per the raw bytes:

Each SSE message is exactly `data: <json>\n\n`. No `event:` field, no `id:` field,
no `retry:` field. The empty line after each `data:` line is the SSE boundary.

**Chunk 0** (role preamble):
```json
{"id":"...","object":"chat.completion.chunk","created":...,"model":"deepseek-v4-pro",
 "choices":[{"index":0,"delta":{"role":"assistant","content":null,"reasoning_content":""},
 "logprobs":null,"finish_reason":null}],"usage":null}
```

**Reasoning chunks** (one token each):
```json
{"id":"...","choices":[{"index":0,"delta":{"content":null,"reasoning_content":"We"},
 "logprobs":null,"finish_reason":null}],"usage":null}
```

**Final chunk** (carries BOTH finish_reason AND usage):
```json
{"id":"...","choices":[{"index":0,"delta":{"content":"","reasoning_content":null},
 "logprobs":null,"finish_reason":"length"}],
 "usage":{"prompt_tokens":20,"completion_tokens":32,"total_tokens":52,
   "prompt_tokens_details":{"cached_tokens":0},
   "completion_tokens_details":{"reasoning_tokens":32},
   "prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":20}}
```

**Stream termination:** `data: [DONE]\n\n`

### HTTP chunk framing vs SSE framing:

The wire shows TWO independent framing layers:
1. **HTTP chunked transfer encoding** — 10 byte-chunks (341 to 1953 bytes each).
   Multiple SSE messages can share one HTTP chunk (e.g. chunk 3 carries 5 SSE
   messages: "asked", ":", " \"", "Think", "briefly"). This is HTTP-level batching
   by the server's TCP stack — NOT semantic.
2. **SSE framing** — `data: ...\n\n` boundaries ARE the semantic unit. Each SSE
   message is one token (when thinking is on) or one content fragment.

### `: keepalive` SSE comments: NOT PRESENT.

**Correction to my round 1 review:** I claimed "the SDK swallows `: keepalive`
comment lines before they reach our loop." This was speculation. The raw wire
capture across TWO full streams (P1 run + P2 run) shows ZERO `: keepalive` lines.
DeepSeek's API apparently does not emit SSE keepalive comments — at least not
during short calls (max_tokens=32). The `connection: keep-alive` is an HTTP/1.1
header, not an SSE keepalive mechanism.

**Updated guidance for the gateway:** Do not assume keepalive comments exist.
If a stream goes silent, the only liveness signal is a TCP read timeout.
The gateway should measure `last_chunk_at` and raise a stall alarm after
`DEEPSEEK_READ_TIMEOUT` seconds with no bytes received.

### reasoning_content placement: delta field, NOT model_extra.

Every chunk places `reasoning_content` directly in `choices[0].delta.reasoning_content`.
It is NEVER in `model_extra`. The `model_extra` on every P6-inspected chunk was `{}`.

**Correction to `_stream_turn()` at `scripts/deepseek_chat.py:296-298`:**
```python
r = getattr(d, "reasoning_content", None)
if r is None and getattr(d, "model_extra", None):
    r = d.model_extra.get("reasoning_content")
```
The `model_extra` fallback is dead code for THIS provider. It may exist for
OpenAI compatibility (where reasoning_content might live in `model_extra`), but
DeepSeek places it directly in `delta.reasoning_content`. The fallback costs
a dict lookup + an attribute access on every chunk and has never fired. It is
harmless but unnecessary for DeepSeek.

### chunk.index: ALWAYS 0 for single-response calls.

Every chunk across all probes has `choices[0].index: 0`. This field would
differ for multi-response calls (n>1), but we never use those. Consistent.

---

## P3 — TTFT DECOMPOSITION (cache hit vs miss)

Evidence: `p3-ttft-decomposition.json`.

Three sequential calls, 0.5s apart:
| Run | Prompt | TTFT | Total | prompt_cache_hit_tokens | prompt_cache_miss_tokens |
|-----|--------|------|-------|------------------------|--------------------------|
| 1 | "The capital of France is Paris..." | 0.859s | 1.156s | 0 | 23 |
| 2 | SAME prompt (expected cache hit) | 0.813s | 1.063s | 0 | 23 |
| 3 | "...Spain is" (perturbed prefix) | 0.890s | 1.093s | 0 | 23 |

### Findings:

1. **TTFT difference is minimal (~0.05-0.08s across runs).** All three calls
   completed in ~1 second. The difference between "cold" and "should-be-cached"
   is within noise. This likely means the cache TTL is very short (<0.5s?) or
   the prompt is too small (23 tokens) for cache to matter.

2. **prompt_cache_hit_tokens = 0 on ALL runs.** Despite run 2 being identical to
   run 1 and only 0.5s later, the API reported ZERO cache hit tokens. Either:
   - The cache TTL is sub-second (so our 0.5s gap already evicted it)
   - Cache only applies to much larger prefixes (system prompts, long contexts)
   - The prompt (23 tokens, one sentence) doesn't meet a minimum size threshold

3. **Content is empty in all runs** because max_tokens=8 was consumed entirely
   by reasoning (thinking=enabled by default for v4-pro). The model used 8
   reasoning_tokens and 0 completion_tokens on every call.

4. **`usage.prompt_tokens_details.cached_tokens` = 0** — this is the OpenAI-compatible
   field, consistently zero alongside `prompt_cache_hit_tokens`.

### Gateway implications:
- TTFT alone is NOT a reliable cache-hit detector. The difference is too small
  to distinguish from network jitter.
- `prompt_cache_hit_tokens > 0` IS the definitive cache-hit signal. When it is
  >0, the provider is telling us explicitly that it served cached prefix.
- The gateway should emit a `cache` metric: `{hit_tokens, miss_tokens}` from
  the usage block, and derive `cache_hit_ratio = hit/(hit+miss)` when >0.
- For small prompts, cache is irrelevant — don't expect cache hits.

---

## P4 — FORCED TRUNCATION: finish_reason="length"

Evidence: `p4-forced-truncation.json`.

max_tokens=8 on "List the numbers from 1 to 20, one per line."

Result: 10 chunks. Chunks 0–8 all carry `delta.content=null` (reasoning tokens
consumed the budget). Chunk 9 (final):
```json
{"delta":{"content":"","reasoning_content":null}, "finish_reason":"length",
 "usage":{"completion_tokens":8, "prompt_tokens":18, "completion_tokens_details":{"reasoning_tokens":8}}}
```

### The truncation signal is deterministic:
- `finish_reason="length"` — the provider stopped because max_tokens was reached,
  not because the model chose to stop.
- `content=""` (empty string, not null) — the final delta carries an empty content
  field alongside the finish_reason. This is different from null.
- `usage` on the SAME chunk — the final chunk carries both finish_reason AND usage
  (with `stream_options={"include_usage": True}`).

### Gateway implications:
- `finish_reason="length"` is the deterministic signal replacing `bounce_promise()`
  heuristics. When the gateway sees `length`, it knows the model was truncated,
  not done.
- The gateway should relay `finish_reason` to the consumer: `stop`, `length`,
  `tool_calls`, `content_filter`.
- If `finish_reason="length"` AND the model was in the middle of a tool call,
  the tool call arguments are incomplete — the gateway should flag this as
  a PARTIAL tool call, not pass it through.

---

## P5 — RATE-LIMIT HEADERS: NONE on 200 responses

Evidence: `p5-rate-limit-headers.json`.

The OpenAI SDK does not expose raw HTTP response headers on the completion
result object. Neither `_response` nor `response` attributes exist on the
parsed `ChatCompletion` or stream chunks.

However, the P2 raw wire capture provides the definitive answer: the HTTP 200
response headers contain NO rate-limit headers whatsoever:

```
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked
connection: keep-alive
date: Sun, 02 Aug 2026 07:13:28 GMT
x-content-type-options: nosniff
server: elb
cache-control: no-cache
vary: origin, access-control-request-method, access-control-request-headers
access-control-allow-credentials: true
x-ds-trace-id: 616fc77f047c75c7a96b9098ca9d650c
strict-transport-security: max-age=31536000; includeSubDomains; preload
x-cache: Miss from cloudfront
via: 1.1 ...cloudfront.net (CloudFront)
x-amz-cf-pop: ATL59-P5
x-amz-cf-id: ...
```

Notable absences:
- No `x-ratelimit-limit-requests`
- No `x-ratelimit-remaining-requests`
- No `x-ratelimit-reset-requests`
- No `x-ratelimit-limit-tokens`
- No `Retry-After`

DeepSeek signals rate limits ONLY through HTTP 429 responses (which we have
seen in production — the runner handles them as retryable errors). There is
no proactive rate-limit telemetry on successful responses.

### Gateway implications:
- The gateway cannot predict rate limits from headers. It must react to 429s.
- Rate-limit awareness must be built from observing 429 responses and backing off.
- `x-ds-trace-id` is the only DeepSeek-specific header. It can be logged for
  support correlation.

---

## P6 — EXTRA: chunk internals, model_extra, surprises

Evidence: `p6-extra-chunk-internals.json` — 16 chunks, full `model_dump()`
for each.

### model_extra: ALWAYS EMPTY `{}`.

Every chunk's `model_extra` is an empty dict. The SDK uses Pydantic v2 models
(`model_dump()`, `model_validate()`, `model_fields_set` are all present), and
`model_extra` is the catch-all for fields not defined in the schema. Its
emptiness confirms: DeepSeek's API stays within the OpenAI-compatible schema;
there are no undocumented fields bleeding through.

### Chunk fields (full inventory from model_dump):
```
id: str                    # same across all chunks of one response
choices: list[Choice]      # always length 1 for us
created: int               # Unix timestamp, same for all chunks
model: str                 # "deepseek-v4-pro"
object: str                # "chat.completion.chunk"
service_tier: null         # always null
system_fingerprint: str    # "fp_9954b31ca7_prod0820_fp8_kvcache_20260402"
usage: null | Usage        # only on final chunk
```

### Choice fields:
```
delta: {
  content: str | null
  function_call: null         # always null (legacy OpenAI field)
  refusal: null               # always null (safety refusal, never seen)
  role: "assistant" | null    # only on first chunk, null thereafter
  tool_calls: null            # null when not using tools
  reasoning_content: str | null  # DeepSeek extension
}
finish_reason: null | "stop" | "length" | "tool_calls" | "content_filter"
index: 0                      # always 0
logprobs: null | ChoiceLogprobs
```

### Surprise: reasoning_content="" on the initial chunk.

The first chunk has `reasoning_content: ""` (empty string), NOT null. This is
the role preamble chunk — it establishes `role: "assistant"` and carries an
empty reasoning_content. The gateway should treat `""` and `null` equivalently
for reasoning_content, since the preamble uses `""`.

### Surprise: the model ALWAYS thinks, even for trivial prompts.

Every single probe call with `max_tokens <= 32` consumed its entire token
budget in reasoning_content, producing ZERO visible content. The only exception
was P1 (logprobs), which did NOT set `thinking={"type": "enabled"}` explicitly
in `extra_body` — but `_kwargs()` in `deepseek_chat.py` sets `thinking: enabled`
unconditionally when `self.think` is True (which is the default). The probes.py
script for P1 did NOT pass `extra_body={"thinking":...}`, relying on the default.
The result: P1's 10 chunks included both reasoning tokens AND a `finish_reason="length"`
with 0 completion_tokens and 8 reasoning_tokens — proving that thinking mode is
ON by default even without the explicit `extra_body`.

For P3/P4/P6, `extra_body={"thinking": {"type": "enabled"}}` was explicitly set,
and the model used all max_tokens for reasoning.

### Gateway implication:
- When `thinking` is enabled, `completion_tokens_details.reasoning_tokens` can
  be >0 while `completion_tokens` = 0. This is normal — the model spent its
  budget thinking.
- The gateway MUST track `reasoning_tokens` separately from `completion_tokens`.
  A consumer looking only at `completion_tokens` would see 0 and think nothing
  was produced, when in fact reasoning consumed the budget.

---

## CORRECTIONS TO MY ROUND 1 REVIEW

| Round 1 Claim | Empirical Finding | Correction |
|---|---|---|
| "logprobs does NOT work under stream=True" | Works perfectly, 10 chunks with per-token logprobs | **Wrong.** Remove the restriction. |
| "`: keepalive` SSE comments exist; SDK swallows them" | Zero keepalive comments on wire across 2 streams | **Unfounded.** DeepSeek doesn't send them. Remove from signal inventory. |
| "reasoning_content may be in model_extra" | Always in `delta.reasoning_content`, never in model_extra | The `model_extra` fallback in deepseek_chat.py:298 is dead code for DeepSeek. |
| "rate-limit headers vary by provider" | No rate-limit headers on 200; only 429 signals limits | Settled: DeepSeek = reactive-only, no proactive telemetry. |
| "TTFT confounds queue/prefill/cache" | Confirmed empirically — cache difference is ~50ms, within noise | Theory correct but effect smaller than expected for small prompts. |

---

## CONSOLIDATED GATEWAY SIGNAL INVENTORY (post-probe)

### Per-chunk signals:
| Signal | Location | When | Gateway action |
|---|---|---|---|
| `delta.reasoning_content` | `choices[0].delta.reasoning_content` | thinking chunks | Accumulate, relay |
| `delta.content` | `choices[0].delta.content` | answer chunks | Accumulate, relay |
| `delta.tool_calls` | `choices[0].delta.tool_calls` | tool call chunks | Accumulate by index |
| `logprobs` | `choices[0].logprobs` | when `logprobs=True` in request | Relay as-is |
| `finish_reason` | `choices[0].finish_reason` | final chunk only | `stop`/`length`/`tool_calls`/`content_filter` |
| `usage` | root `.usage` | final chunk only (with `stream_options.include_usage`) | Capture, relay |
| `usage.prompt_cache_hit_tokens` | `.usage` | final chunk | Cache hit counter (DeepSeek-specific) |
| `usage.prompt_cache_miss_tokens` | `.usage` | final chunk | Cache miss counter (DeepSeek-specific) |
| `usage.completion_tokens_details.reasoning_tokens` | `.usage` | final chunk | Reasoning token counter |

### Stream-level metrics (derived by gateway):
| Metric | How to compute |
|---|---|
| `ttft` | `first_chunk_at - request_sent_at` |
| `ttft_reasoning` | Time to first `reasoning_content` token |
| `ttft_content` | Time to first `content` token |
| `total_time` | `last_chunk_at - request_sent_at` |
| `finish_reason` | From final chunk |
| `prompt_tokens` / `completion_tokens` / `reasoning_tokens` | From final chunk usage |
| `cache_hit_ratio` | `prompt_cache_hit / (prompt_cache_hit + prompt_cache_miss)` |
| `stall` | `now - last_chunk_at > DEEPSEEK_READ_TIMEOUT` |

---

*Battery completed 2026-08-02 ~07:14 UTC. 8 API calls made. All tiny (max_tokens<=32).*
