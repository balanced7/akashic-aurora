# API gateway review — wire-level reverse-engineering (deepseek, 2026-08-02)

Status: filed per Daniil's request ("I want to hear deepseeks and kimis thoughts on my latest
addition"). Lens: reverse-engineer the wire. Every claim cites the code that processes these
chunks today.

---

## (1) SSE GROUND TRUTH: what actually arrives

I process these chunks every turn in `_stream_turn()` at
`scripts/deepseek_chat.py:276-320`. Here is what the wire actually delivers.

### Chunk shape (OpenAI-compatible streaming, per the SDK's parsed delta)

Each SSE chunk, after the `openai` SDK parses it, arrives as a Python object whose
`.choices[0].delta` carries these fields. The fields are MUTUALLY EXCLUSIVE in practice —
DeepSeek never sends `content` and `reasoning_content` in the same chunk, and
`tool_calls` arrives in its own chunks:

```
chunk.choices[0].delta.content          → str | None    # answer text
chunk.choices[0].delta.reasoning_content → str | None   # thinking (only when thinking=enabled)
chunk.choices[0].delta.tool_calls        → list | None  # tool call fragments (streamed incrementally)
chunk.choices[0].finish_reason           → str | None   # "stop" | "length" | "tool_calls" | "content_filter"
chunk.usage                              → object | None # only on final chunk (stream_options={"include_usage":True})
```

Lines 282-324 of `scripts/deepseek_chat.py` handle each of these explicitly.

### Field-by-field corrections to the addendum's signal inventory

**usage placement: FINAL CHUNK ONLY.** The addendum says "final-chunk usage." This is
correct. `stream_options={"include_usage": True}` at `deepseek_chat.py:261` tells the
provider to include usage on the final chunk. Without it, usage is absent. The gateway
must parse `stream_options` from the outbound request to know whether to expect it.

The usage object fields (from `_absorb_usage` at line 201-213):
```
usage.prompt_tokens           → int   # always present
usage.completion_tokens       → int   # always present
usage.prompt_cache_hit_tokens → int   # DEEPSEEK-SPECIFIC: cached prefix tokens
usage.prompt_cache_miss_tokens→ int   # DEEPSEEK-SPECIFIC: non-cached prefix tokens
```

The cache hit/miss split is DeepSeek-specific and NOT in every OpenAI-compatible
provider. Kimi/Moonshot may or may not surface it. The gateway's `usage` capture must
treat these fields as optional per-provider.

**reasoning_content framing: in-body, not separate.** The addendum says
"reasoning_content as its own labeled channel." It is a field ON the delta, not a
separate channel. It streams BEFORE content for each turn — the model thinks, then
speaks. There is no structural framing beyond `delta.reasoning_content` being
non-None. The gateway cannot separate reasoning from content by HTTP header or MIME
type; it must parse the SSE body. This matters for the gateway's complexity: the
gateway needs to parse JSON, not just observe bytes.

One subtlety confirmed at `deepseek_chat.py:296-298`: when the provider nests
reasoning_content under `model_extra` instead of the standard delta field, we
already handle it:
```python
r = getattr(d, "reasoning_content", None)
if r is None and getattr(d, "model_extra", None):
    r = d.model_extra.get("reasoning_content")
```

**EMPIRICAL UPDATE 2026-08-02 (P6 probe):** The `model_extra` fallback is DEAD CODE for
DeepSeek. Every chunk across multiple streams had `model_extra = {}` and
`reasoning_content` always lived at `delta.reasoning_content`. The fallback was
speculative (for OpenAI compatibility, where reasoning_content might live in
model_extra), but DeepSeek always places it in the standard field. The fallback
is harmless but unnecessary. See `gateway-wire-probes-deepseek-2026-08-02.md` P2/P6.

**keepalive/ping frames: SSE comments or empty data — NOT PRESENT ON DEEPSEEK.**

**EMPIRICAL UPDATE 2026-08-02 (P2 probe):** The raw wire capture across two streams
shows ZERO `: keepalive` SSE comment lines. DeepSeek's API does not emit SSE keepalive
comments — at least not for short calls. The `connection: keep-alive` header is an
HTTP/1.1 mechanism, not an SSE keepalive. My prior claim that "the SDK swallows them"
was speculation without wire evidence. The only liveness signal during a silent stream
is a TCP read timeout. The gateway should measure `last_chunk_at` and raise a stall
alarm after `DEEPSEEK_READ_TIMEOUT` seconds with no bytes, rather than expecting
keepalive comments. See `gateway-wire-probes-deepseek-2026-08-02.md` P2.

**finish_reason: on the LAST chunk with content, not a standalone chunk.**
`chunk.choices[0].finish_reason` at line 304 (implicitly available but not captured
in our code today — we never read it). Values:
- `"stop"` — natural end
- `"length"` — SILENT TRUNCATION (the `reasoning_model_token_headroom` lesson:
  max_tokens exhausted, content cut mid-sentence, no error returned)
- `"tool_calls"` — model wants to call tools
- `"content_filter"` — provider safety filter tripped

The addendum's claim that `finish_reason=length` = "SILENT TRUNCATION" is CORRECT
and this is one of the highest-value signals the gateway can add. Today we only
detect truncation heuristically (content ends promise-shaped, `bounce_promise()`
fires at `bifrost_runner_deepseek.py:145-157`). `finish_reason=length` is a
deterministic signal — no heuristic needed.

**logprobs under streaming: WORKS on DeepSeek v4-pro.**

**EMPIRICAL UPDATE 2026-08-02 (P1 probe):** logprobs under `stream=True` produces
per-token `ChoiceLogprobs` objects on every content-bearing chunk. It does NOT error.
The `_kwargs()` method at line 258 has no logprobs parameter, and our harness never
enables it — but the API supports it natively. When `logprobs=True` and `top_logprobs=3`
are passed, each chunk carries `choices[0].logprobs` with `reasoning_content` token
probabilities (when thinking is on) or `content` token probabilities. The logprobs
object has fields: `content`, `refusal`, `reasoning_content` — each a list of
`{token, logprob, bytes, top_logprobs}`. The gateway CAN and SHOULD relay logprobs
when the outbound request asks for them. See `gateway-wire-probes-deepseek-2026-08-02.md` P1.

**One field the addendum MISSES: `chunk.choices[0].index`.** Every chunk carries an
`index` field (0 for single-response). When it changes mid-stream, the provider is
sending a second choice — this is a retry/fallback signal. In practice DeepSeek
never does this, but a future provider might. Worth capturing as a diagnostic.

### Corrected signal inventory

| Signal | Location | When | Reliability |
|--------|----------|------|-------------|
| request start | gateway POST time | per turn | deterministic |
| first SSE byte | gateway first chunk time | per turn | deterministic (TTFT) |
| first content chunk | `delta.content` first non-None | per turn | deterministic |
| reasoning_content | `delta.reasoning_content` | per turn (thinking on) | deterministic — NOT in model_extra (verified P6) |
| content chunks | `delta.content` streaming | per turn | deterministic |
| tool_calls | `delta.tool_calls` incremental | per tool call | deterministic |
| inter-chunk cadence | wall clock between chunks | continuous | noisy (see §3) |
| keepalive heartbeats | SSE `: ` comment lines | during prefill/queue | NOT PRESENT on DeepSeek (verified P2); use TCP read timeout |
| finish_reason | `choices[0].finish_reason` on last chunk | per turn | deterministic |
| usage | `chunk.usage` on final chunk | per turn | deterministic (when stream_options includes usage) |
| cache hit/miss | `usage.prompt_cache_hit_tokens` | per turn | DeepSeek-specific, optional; 0 for small prompts (verified P3) |
| rate-limit headers | HTTP response headers | per request | NONE on 200 responses (verified P2/P5); only 429 signals limits |
| logprobs | `choices[0].logprobs` (if enabled) | per token | WORKS on DeepSeek streaming (verified P1) |

---

## (2) PROXY RISK SURFACE: concrete failure modes

### Current client config (scripts/deepseek_chat.py:67-70)

```python
return OpenAI(api_key=api_key or load_key(), base_url=base_url,
              timeout=httpx.Timeout(MODEL_READ_TIMEOUT, connect=MODEL_CONNECT_TIMEOUT),
              max_retries=MODEL_MAX_RETRIES)
```

Where `MODEL_READ_TIMEOUT=120` (per-chunk read gap), `MODEL_CONNECT_TIMEOUT=15`,
`MODEL_MAX_RETRIES=1`.

### Failure mode 1: SSE buffering in the proxy

This is the KILLER. SSE is a streaming protocol — chunks must arrive
incrementally. If the gateway buffers the response body (e.g., waiting for
`Content-Length`, or using a buffering HTTP library), it will hold the ENTIRE
response until completion, then dump it at once. The runner's
`_stream_turn()` would see one giant chunk after 30-300 seconds instead of a
stream. The `MODEL_READ_TIMEOUT=120` would fire — 120 seconds with zero chunks
looks like a hung stream — and the turn would time out.

Mechanical fix: the gateway's forwarder MUST use `stream=True` with httpx and
iterate chunks, never collect the body. Each upstream chunk must be written to
the downstream response immediately with `response.write(chunk)` or equivalent.
No buffering middleware. The gateway must also set `Transfer-Encoding: chunked`
and never compute `Content-Length`.

### Failure mode 2: chunked-encoding pitfalls

The provider sends `Transfer-Encoding: chunked`. The gateway receives chunked,
but if its HTTP framework re-encodes as identity (buffered), mode 1 fires. If
the gateway re-chunks with a different chunk size, it is harmless for SSE (SSE
frames are delimited by `\n\n`, not by HTTP chunks). The danger is the gateway
MERGING chunks — if two SSE frames arrive in one HTTP chunk and the gateway
splits them differently, SSE parsing is unaffected. If the gateway MERGES
multiple HTTP chunks before forwarding, the TTFT signal is delayed by the merge
window. Keep chunk forwarding 1:1 (each incoming HTTP chunk → one outgoing HTTP
chunk).

### Failure mode 3: retry doubling

The client has `max_retries=1` (one retry on `APITimeoutError`). If the gateway
also retries on upstream failure, the effective retries multiply:
- Client retry → gateway receives request again → gateway retries upstream →
  worst case: 1 (original) + 1 (client retry) × 1 (gateway retry on each) = 3
  total API calls for one logical turn.

Mitigation: the gateway MUST NOT retry. It forwards the upstream response
(status, headers, body) as-is. If the upstream fails, the gateway returns the
error to the client. The client's `max_retries` handles the retry decision. The
gateway is a passthrough, not a reliability layer.

### Failure mode 4: connection pooling

The `openai` SDK uses httpx's connection pool. With `base_url` pointed at
localhost, the pool keeps TCP connections to the gateway open. The gateway must
handle connection reuse (HTTP/1.1 keep-alive) correctly. If the gateway closes
connections aggressively, the client pays a TCP handshake per turn (~1-5ms
localhost, negligible). If the gateway leaks connections (doesn't close
properly), the client pool exhausts. Mitigation: use uvicorn/gunicorn with a
reasonable keep-alive timeout (30s) and a connection limit above the client pool
size.

### Failure mode 5: gateway death mid-stream

If the gateway process dies while streaming a response, the client sees a TCP
RST or connection close. The `openai` SDK surfaces this as an
`APIConnectionError`. The runner's `try/except` at
`bifrost_runner_deepseek.py:880` catches it and produces an error string. The
turn is lost but the runner stays alive. This is correct behavior AS LONG AS the
bypass is engaged.

### The bypass must be MECHANICAL

The addendum says "gateway FAILS OPEN (bypass mode)." This must be a code path
in `make_client()`, not a configuration convention. Proposed:

```python
def make_client(api_key=None, base_url=BASE_URL):
    import os
    gw = os.environ.get("AKASHIC_API_GATEWAY")
    if gw:
        # try gateway, fall back to direct on connection failure
        try:
            import httpx
            # probe gateway health — quick connect, 1s timeout
            httpx.get(f"{gw}/health", timeout=1)
        except Exception:
            gw = None  # gateway dead → use direct
    return OpenAI(api_key=api_key or load_key(), base_url=gw or base_url, ...)
```

The gateway is tried, not demanded. If `/health` times out (1s), the client
bypasses it entirely. No operator intervention needed. The gateway can be
restarted independently and clients will pick it back up on the next turn.

One additional bypass case: the gateway must NOT buffer the response body of
the health check (it is one small JSON). The existing httpx timeout applies
only to the `/health` probe; the streaming timeout (`MODEL_READ_TIMEOUT`)
applies to the actual API call through the gateway, exactly as it does today.

---

## (3) TTFT/CADENCE SEMANTICS: what can genuinely be inferred

### TTFT (time-to-first-token)

TTFT = wall clock from POST to first SSE chunk with content. Three components,
all confounded:

1. **Provider queue time** — the request sits in a queue waiting for a GPU.
   This varies by provider load and is the dominant variable. Spikes = provider
   under load, NOT our model thinking.

2. **Prefill time** — the model processes the prompt (all input tokens in one
   forward pass). Proportional to prompt size. A 100K-token context takes longer
   to prefill than a 10K one. This IS useful: a TTFT spike with stable queue
   time = our context grew.

3. **Cache-miss penalty** — if the prompt prefix is not cached, prefill is more
   expensive. DeepSeek's cache is prefix-based: if the first N tokens match a
   prior request exactly, prefill skips them. A cache miss → longer prefill →
   longer TTFT.

**What can be inferred:** sudden TTFT spikes with STABLE prompt size = provider
queue. Sudden TTFT spikes with GROWING prompt size = larger context (prefill
cost). Gradual TTFT increase over a session = context accumulation (our
`messages` list growing, `_mark_context()` at line 225 measures this).

**What is confounded:** you cannot distinguish queue time from prefill time from
cache-miss penalty with TTFT alone. You need the prompt token count (from the
outbound request, which the gateway can parse) AND the cache hit/miss counts
(from usage on the final chunk) to disambiguate AFTER the turn completes. During
the turn, TTFT alone is a single number carrying three overlapping signals.

### Inter-chunk cadence

This is NOISE for liveness. Chunks arrive in bursts — the provider's token
generation is bursty by nature (batch decoding produces multiple tokens, then
pauses). A 5-second gap between chunks is normal behavior during a complex
reasoning step, not a stall. The only reliable signal from cadence is:

- **Zero chunks for > MODEL_READ_TIMEOUT (120s):** this IS a stall. The
  `httpx.Timeout(read=120)` already catches it.
- **Sustained very low cadence (< 1 chunk/10s for > 60s):** possible
  degradation, but also possible legitimate reasoning (the model is producing
  reasoning_content, not content — reasoning tokens are emitted at roughly the
  same rate but may not be surfaced as `delta.content`).

**Recommendation:** do NOT use cadence for liveness verdicts. Use it as a SOFT
signal for the codebook's `degraded` column ("provider is slow today"). The hard
liveness signals are:
1. Chunk arrived within READ_TIMEOUT → alive
2. No chunk within READ_TIMEOUT → dead (caught by httpx, becomes an exception)
3. finish_reason present → turn complete

Cadence adds color ("fast," "slow," "stalled") but never changes a verdict from
alive to dead or vice versa.

---

## (4) SLICE-1 DELTA: final v1 field list

My review proposed `bifrost:sensor:<agent>` with 6 fields. The gateway adds
fields derived from the socket that the existing hooks cannot see. Here is the
merged v1 field set:

### From existing hooks (tool-dispatch path, already built)
| Field | Writer | Source |
|-------|--------|--------|
| `tool_state` | `on_trace` hook | `tool` / `thinking` / `idle` |
| `last_tool_at` | `on_trace` hook | `time.time()` at each tool call |
| `turn_count` | runner loop | `_RUN_STATS["turns"]` |

### From the API gateway (socket path, new)
| Field | Writer | Source |
|-------|--------|--------|
| `api_state` | gateway | phase: `prefill` (TTFT window) / `streaming` (chunks flowing) / `done` (finish_reason received) |
| `last_chunk_at` | gateway | `time.time()` at each SSE chunk or keepalive |
| `ttft_ms` | gateway | wall clock: POST to first content chunk (writes ONCE at first chunk, never overwritten until next turn) |
| `finish_reason` | gateway | `stop` / `length` / `tool_calls` / `content_filter` (writes ONCE at final chunk) |
| `usage_prompt` | gateway | `usage.prompt_tokens` (writes ONCE at final chunk) |
| `usage_completion` | gateway | `usage.completion_tokens` (writes ONCE at final chunk) |
| `cache_hit` | gateway | `usage.prompt_cache_hit_tokens` (DeepSeek-specific; 0 if absent) |
| `cache_miss` | gateway | `usage.prompt_cache_miss_tokens` (DeepSeek-specific; 0 if absent) |
| `keepalive_count` | gateway | count of SSE `: ` comment lines (prefill liveness; resets per turn) |

### Fields the gateway can capture from the REQUEST (not the response)
| Field | Writer | Source |
|-------|--------|--------|
| `req_ctx_chars` | gateway | sum of message content lengths in the POST body (context size, proxy for `_mark_context()`) |
| `req_model` | gateway | `model` field in the POST body |
| `req_thinking` | gateway | `extra_body.thinking.type` — is thinking enabled? |

### Total: 15 fields

The existing `tool_state`/`last_tool_at`/`turn_count` from my review stay. The
gateway adds 12 fields, of which 7 are per-turn scalar writes (written once per
turn, not per chunk) and 2 are streaming counters (`last_chunk_at`,
`keepalive_count`).

All fields respect single-writer-per-field: the gateway writes the `api_*`,
`ttft_*`, `finish_reason`, `usage_*`, `cache_*`, `keepalive_*`, and `req_*`
fields. The runner loop writes `tool_*` and `turn_count`. The `standing:*`
fields (future slice) are separate.

### Redundant vs complementary

The gateway's `api_state=streaming` + `last_chunk_at` fresh is the SOCKET
liveness signal. The runner's `tool_state=tool` + `last_tool_at` fresh is the
TOOL-DISPATCH liveness signal. Together they cover the two paths that my review
showed the socket-only wrapper would miss. The codebook's `composing` state
becomes: `api_state=streaming AND tool_state=idle`. The codebook's
`tool-running` state becomes: `api_state=done AND tool_state=tool`. No gap
remains — every phase of the runner's loop has at least one sensor that fires
deterministically.

The addendum's claim that TTFT+cadence splits "composing" into "prefill /
decoding / throttled / truncated" is CORRECT with these fields:
- `api_state=prefill` (TTFT window, no content yet) → the model is loading
- `api_state=streaming` + `last_chunk_at` fresh → decoding
- `finish_reason=length` → truncated (SILENT — the addendum is right that this
  is currently invisible)
- `ttft_ms` spiking → possible throttling or cache miss (soft signal, see §3)
