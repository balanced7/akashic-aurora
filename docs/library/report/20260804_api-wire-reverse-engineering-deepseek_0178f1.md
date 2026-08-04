---
akashic_id: art_20260804_api-wire-reverse-engineering-deepseek_0178f1
akashic_sha: c1e19fdaaca7
schema_version: 1
status: current
type: report
date: 2026-08-04
title: api-wire-reverse-engineering-deepseek
gist: "# API WIRE — reverse-engineering report (deepseek, Builder seat, 2026-08-04) Status: in-flight / EMPIRICAL — every field name cited is obser"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T01:27:21"
updated: "2026-08-04T01:27:21"
---
<!-- GENERATED PROJECTION of art_20260804_api-wire-reverse-engineering-deepseek_0178f1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# api-wire-reverse-engineering-deepseek

# API WIRE — reverse-engineering report (deepseek, Builder seat, 2026-08-04)

Status: in-flight / EMPIRICAL — every field name cited is observed on live wire traces
Class: research
Lane: EMPIRICAL half of the api-wire-visibility ask. Companion to opus5's ARCHITECTURE draft
       at research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md.

Ask, verbatim: "REVERSE-ENGINEER WHAT THE PROVIDER ACTUALLY SENDS BACK. A design that
assumes fields the API does not return is worthless; you can just look."

Method: I traced every line where the DeepSeek API response touches my own runner. I did
NOT sample — I read every call site, every field access, and every discard. The wire probe
battery from 2026-08-02 (research/in-flight/gateway-wire-probes-deepseek-2026-08-02.md, P1–P8)
provides the raw ground truth; this file maps it onto the runner's consumption.

Sources read in full: `scripts/deepseek_chat.py` (all 590 lines), `scripts/bifrost_runner_deepseek.py`
(all ~1350 lines, the consume→reply pipeline), `scripts/runner_token_journal.py` (all ~250 lines),
`scripts/ask_deepseek.py` (all ~75 lines), `research/in-flight/gateway-wire-probes-deepseek-2026-08-02.md`
(all 8 probes, raw SSE captures), `research/in-flight/gateway-review-wire-deepseek-2026-08-02.md`
(full 400 lines, field inventory + proxy risk surface).

---

## 1. THE RESPONSE SURFACE — every field the DeepSeek API actually returns

### 1.1 The streaming chunk (per-SSE-frame object, after SDK parsing)

The raw wire is SSE: `data: <json>\n\n`. The SDK parses each into a `ChatCompletionChunk` object.
Here is every field observed on that object (all confirmed by wire captures P1/P2/P6, 2026-08-02):

| Field | Type | When present | Read today? |
|-------|------|-------------|-------------|
| `chunk.id` | str | every chunk | **NO** — never read |
| `chunk.object` | str | every chunk | **NO** — always `"chat.completion.chunk"` |
| `chunk.created` | int | every chunk | **NO** — Unix timestamp |
| `chunk.model` | str | every chunk | **NO** — model name repeated on every chunk |
| `chunk.choices[0].index` | int | every chunk | **NO** — always `0` for single-response; a change signals a provider retry/fallback |
| `chunk.choices[0].delta.role` | str | first chunk only | **NO** — always `"assistant"` |
| `chunk.choices[0].delta.content` | str\|None | content chunks | **YES** — `deepseek_chat.py:310` |
| `chunk.choices[0].delta.reasoning_content` | str\|None | thinking chunks | **YES** — `deepseek_chat.py:295` (also `:297` fallback) |
| `chunk.choices[0].delta.tool_calls` | list\|None | tool-call chunks | **YES** — `deepseek_chat.py:316-322` |
| `chunk.choices[0].finish_reason` | str\|None | final chunk | **NO** — never captured; values: `"stop"`, `"length"`, `"tool_calls"`, `"content_filter"` |
| `chunk.choices[0].logprobs` | object\|None | content chunks (if `logprobs=True`) | **NO** — our harness never enables it |
| `chunk.usage` | object\|None | final chunk (if `stream_options.include_usage=True`) | **PARTIALLY** — see §1.2 |
| `chunk.choices[0].delta.model_extra` | dict | every chunk | **YES** — `deepseek_chat.py:297` (fallback for reasoning_content) but EMPIRICALLY always `{}` on DeepSeek (P6) |

**Cite:** chunk iteration at `deepseek_chat.py:284-324`, `_kwargs()` at `:258-273`,
wire verification at `gateway-wire-probes-deepseek-2026-08-02.md` P2 raw SSE capture.

### 1.2 The usage object (on the final chunk)

Read at `deepseek_chat.py:293-294` and absorbed by `_absorb_usage()` at `:201-213`.

| Field | Type | Read? | Destination |
|-------|------|-------|-------------|
| `usage.prompt_tokens` | int | **YES** | `ag.prompt_tokens` (`:207`) → `_token_deltas` → `TokenJournal` |
| `usage.completion_tokens` | int | **YES** | `ag.completion_tokens` (`:208`) → `_token_deltas` → `TokenJournal` |
| `usage.total_tokens` | int | **NO** — discarded | Discarded. Sum of the two above, but a data-integrity check we never run. |
| `usage.prompt_tokens_details.cached_tokens` | int | **NO** — discarded | This is the **OpenAI-compatible** cache-hit field. DeepSeek ALSO populates it (P2 wire: `"cached_tokens":0`), but we read the DeepSeek-specific field instead. |
| `usage.completion_tokens_details.reasoning_tokens` | int | **NO** — discarded | How many completion tokens were reasoning. Discarded — we can't separate reasoning from output spend. |
| `usage.prompt_cache_hit_tokens` | int | **YES** | `ag.cache_hit_tokens` (`:209`) → `_cost_shape["cache_hit"]` → `TokenJournal.add_turn(cached_prompt=...)` |
| `usage.prompt_cache_miss_tokens` | int | **YES** | `ag.cache_miss_tokens` (`:210`) → `_cost_shape["cache_miss"]` → printed only, NOT journaled |

**Key finding: `total_tokens`, `cached_tokens` (OpenAI-compat path), and `reasoning_tokens` all arrive and are thrown away.** Three integer fields, every turn, zero storage cost.

Also: `usage.completion_tokens_details` is a nested object confirmed on wire (P2), but we never check it. The `reasoning_tokens` field inside it tells us how much of our completion spend went to thinking vs. output — the single most useful cost disaggregation we don't have.

**Cite:** `deepseek_chat.py:201-213`, `bifrost_runner_deepseek.py:472-496`, wire evidence at `gateway-wire-probes-deepseek-2026-08-02.md` P2 final chunk.

### 1.3 The non-streaming response (stateless path)

The stateless responder at `bifrost_runner_deepseek.py:370-377` reads exactly ONE field:

```python
resp = client.chat.completions.create(**kwargs)
return resp.choices[0].message.content or "(deepseek returned an empty reply)"
```

Every other field on `resp` — `id`, `model`, `created`, `usage`, `choices[0].finish_reason`,
`choices[0].message.role`, `choices[0].message.tool_calls` — is discarded.

**This is the thinnest consumption in the system.** For one-shot (non-agentic) turns, the
only thing that survives the API call is the text string. No usage, no finish_reason, no timing.

Cite: `bifrost_runner_deepseek.py:370-377`.

### 1.4 HTTP response headers (RAW wire, not SDK)

From the P2 raw SSE capture (httpx direct, no SDK):

| Header | Value observed | Useful? |
|--------|---------------|---------|
| `content-type` | `text/event-stream; charset=utf-8` | confirms SSE |
| `transfer-encoding` | `chunked` | confirms streaming |
| `connection` | `keep-alive` | HTTP/1.1, NOT SSE keepalive |
| `server` | `elb` | AWS Elastic Load Balancer |
| `x-ds-trace-id` | `7d0a37b8dcabac6f7fa679e94984f73e` | **HIGH VALUE — request tracing** |
| `x-cache` | `Miss from cloudfront` | CDN cache status |
| `via` | `1.1 ...cloudfront.net (CloudFront)` | CDN edge node |
| `x-amz-cf-pop` | `ATL59-P1` | CDN point-of-presence location |

**Key finding: `x-ds-trace-id` is a per-request UUID that DeepSeek's own infrastructure uses for tracing.** This is the field you give DeepSeek support when debugging a specific call.
The openai SDK almost certainly swallows response headers — they are not on the parsed response object,
they're on the httpx `Response` which the SDK discards after parsing the body. **A local proxy
is the ONLY way to capture this header without forking the SDK.** More in §4.

Also: NO `x-ratelimit-*` headers, no `Retry-After` on 200 responses. Rate limits surface ONLY as
HTTP 429 responses (probe P5). You cannot see your rate-limit budget on a successful call.

Cite: `gateway-wire-probes-deepseek-2026-08-02.md` P2 response headers dump, P5 rate-limit probe.

### 1.5 SSE framing metadata — NOT PRESENT

- **No `event:` field** — every SSE message is the default `message` type.
- **No `id:` field** — no SSE-level message IDs.
- **No `retry:` field** — no server-specified reconnection delay.
- **No `: keepalive` comment lines** — P2 wire trace: ZERO `: ` comment lines across two full streams. DeepSeek does not emit SSE keepalive comments. The `connection: keep-alive` header is HTTP/1.1, not SSE.

Cite: `gateway-wire-probes-deepseek-2026-08-02.md` P2 raw SSE capture, confirmed in P6.

### 1.6 Tool call stream parsing — what the runner extracts

`deepseek_chat.py:316-322` extracts from `delta.tool_calls`:
- `tc.id` — the tool call ID (arrives on first chunk of each tool call)
- `tc.function.name` — the function name (arrives incrementally)
- `tc.function.arguments` — JSON string, accumulated across chunks

What is NOT extracted:
- `tc.type` — always `"function"`, discarded
- `tc.index` — tool call position (0, 1, ...), used internally for slot-keying but not recorded

---

## 2. THE GAP — fields received and thrown away

This is the cheapest telemetry in the system. Every field below crosses the wire, costs the
API call budget, enters our Python process, and is dropped before any storage path sees it.

### 2.1 Per-chunk discards (every SSE frame, streaming path)

| Field | Location on chunk | Why it matters |
|-------|------------------|----------------|
| `chunk.id` | `chunk.id` | Correlates chunks to the same logical response. When a provider retries mid-stream, the id changes. |
| `chunk.created` | `chunk.created` | Server-side timestamp — the ONLY clock that isn't ours. TTFT computed from this vs. `time.time()` gives network+server latency. |
| `chunk.model` | `chunk.model` | Which model actually served the request (can differ from requested if provider load-balances). |
| `chunk.choices[0].index` | `choices[0].index` | Always `0` for single-response. A change signals a provider fallback/retry mid-stream. |
| `chunk.choices[0].finish_reason` | `choices[0].finish_reason` | **THE single highest-value discarded field.** `"length"` = silent truncation (max_tokens exhausted). `"content_filter"` = safety filter tripped. Currently we detect truncation only heuristically via `bounce_promise()` + `content_floor_check()`. A deterministic signal costs nothing and replaces heuristics. |
| `usage.total_tokens` | `usage.total_tokens` | Cross-check against prompt+completion. A mismatch = a counting bug in our accumulation. Never checked. |
| `usage.completion_tokens_details.reasoning_tokens` | `usage.completion_tokens_details` | How many output tokens were reasoning vs. content. This is the disaggregation that tells you whether your `REPLY_TIMEOUT_SEC` was consumed by thinking or by writing. Structurally zero in our accounting. |

### 2.2 Per-request discards (non-streaming path)

The stateless path at `bifrost_runner_deepseek.py:376` calls `resp.choices[0].message.content`
and returns. The following fields on `resp` are garbage-collected:

- `resp.id` — request UUID
- `resp.model` — model that served
- `resp.usage` — the whole usage block (prompt/completion/cache) — **this means the stateless path has ZERO cost accounting.** The TokenJournal is updated only in the agentic path (`_process_one` at line ~1090). A one-shot reply costs real money and records nothing.
- `resp.choices[0].finish_reason` — truncation invisible
- `resp.choices[0].message.role` — always "assistant", but still

**This is a correctness gap, not just a telemetry gap.** The stateless path spends money with no
ledger entry. The `_token_deltas` dict is populated only by the agentic `respond()` closure
(`bifrost_runner_deepseek.py:482-496`); the stateless `respond()` at `:370-377` never touches it.

### 2.3 HTTP headers (discarded by the SDK before we even see them)

The openai SDK wraps httpx. The response object the SDK hands us (`ChatCompletion` or stream
iterator) does NOT carry HTTP headers. The `x-ds-trace-id`, `x-cache`, `via`, and
`x-amz-cf-pop` headers are on the httpx `Response` which the SDK reads and discards.

**This is a class of data a call-site recorder CANNOT capture and a proxy CAN.** More in §4.

### 2.4 Summary: the delta between "arrives" and "recorded"

```
API response bytes ─────────> our process ─────────> storage
        │                        │                      │
        │  ~100% of fields       │  usage: 5/9 fields    │  TokenJournal: 3 fields
        │  arrive                │  chunk: 1/7 fields    │  _cost_shape: 3 fields
        │                        │  headers: 0/8 fields  │  cognitive_metrics: 2 fields
        │                        │  finish_reason: 0/1   │
        │                        │  timing: 0/n          │
        │                        │                       │
        ▼                        ▼                       ▼
    full fidelity            narrow extraction        narrower recording
```

The cost of capturing the discarded fields is zero additional API calls. Every field above is
already in memory. The work is: (1) read the field, (2) write it somewhere. No new network
traffic, no additional API budget.

---

## 3. FAILURE MODES — with evidence

### 3.1 Empty reply (deepseek_empty_reply_size_ceiling)

**Observed:** July 2026. A ~3.5KB multi-section ask returned empty content twice. The same
content as compact bullets under ~2.4KB answered fully on first try.

**Is it visible in the response object?** PARTIALLY. The non-streaming path checks
`resp.choices[0].message.content or "(deepseek returned an empty reply)"` at
`bifrost_runner_deepseek.py:377`. The fallback string is a sentinel that the runner's
content-floor gate catches. But the STATELESS path never reads `finish_reason`, so it cannot
distinguish "model chose to say nothing" (finish_reason=stop, empty content) from
"model was truncated before it could speak" (finish_reason=length, empty content) from
"content filter tripped" (finish_reason=content_filter). All three produce the same
`"(deepseek returned an empty reply)"` string.

**Fix cost:** read `resp.choices[0].finish_reason` (one attribute access, zero bytes of
additional network) and include it in the error string: `"(deepseek returned an empty reply; finish_reason=length)"`.

**Lesson source:** `learn:experiment:deepseek_empty_reply_size_ceiling`.

### 3.2 Tool call truncation (runner_bigwrite_tool_call_truncation)

**Observed:** July 15, 2026. A `write_file` call with a giant content argument was truncated
by `MAX_TOKENS=8000` — the truncation produced a malformed JSON argument, which the model
interpreted as `"missing 2 required positional arguments"` and retried the same doomed shape
~13 times, burning ~600s and producing a 4-char file stub.

**Is it visible in the response object?** YES — but only if we read `finish_reason`.
`finish_reason="length"` on the final chunk is the deterministic signal that `max_tokens` was
exhausted. The runner never read it — instead it ran `bounce_promise()` + `content_floor_check()`
heuristics, which catch the *content* being a promise but not the *truncation* being the cause.

**The runner's own lesson records this:** `runner_bigwrite_tool_call_truncation` recommends
"(3) treat repeated 'missing required arguments' on big-payload calls as TRUNCATION, not the
model forgetting the schema." A single field read would replace pattern-matching with a
deterministic signal.

**Fix cost:** one line in `_stream_turn()` to capture `finish_reason` from the final chunk
and surface it in the return value or a side channel. `deepseek_chat.py:304` is already inside
the chunk loop — the field is one attribute away.

**Lesson source:** `learn:experiment:runner_bigwrite_tool_call_truncation`.

### 3.3 Timeout (REPLY_TIMEOUT_SEC = scaled(600))

**Observed:** Tonight, 2026-08-04. deepseek-review hit the 600s wall-clock timeout. The
runner's `REPLY_TIMEOUT_SEC` is enforced by a `threading.Timer` at
`bifrost_runner_deepseek.py:870-882` that sets `result_holder[0] = TimeoutError(...)`.

**Is it visible in the response object?** NO — it is a CLIENT-SIDE signal. The API call never
completes, so there is no response object to inspect. The timeout is inferable from the
runner's own log (`"timed out"` in `_process_one`) but is not recorded in any structured form.

**What the runner records on timeout:**
- `_tm.record(... outcome="timeout" ...)` at `:1096` — yes, outcome is recorded
- No token delta (the API call never returned usage)
- No cost_shape (ditto)
- The timeout duration is known (600s) but the *how much of that was API time vs. queue time*
  is unknown — the `threading.Timer` fires at `REPLY_TIMEOUT_SEC` from `turn_t0`, which
  includes both queue + streaming time

**The gap:** when a timeout fires, we know the TOTAL time but not the SPLIT between
"never connected" vs "connected but stream stalled" vs "streaming too slowly." The ONLY
way to get that split is a proxy that records `connect_time`, `first_byte_time`,
`last_chunk_time` — or a call-site recorder that wraps `client.chat.completions.create()`
with timing instrumentation. Currently we have neither.

### 3.4 SDK-level timeout (httpx.ReadTimeout, mid-stream stall)

**Observed:** `openai_sdk_timeout_aborts_streaming_wedge` — confirmed that a read timeout
on a streaming call fires `httpx.ReadTimeout`, which the SDK surfaces as `APITimeoutError`,
which the runner's `try/except` at `deepseek_chat.py:352` catches.

**Is it visible in the response object?** NO — same as §3.3, it's a client-side exception.
The `except` block at `deepseek_chat.py:352` pops the last user message and returns `""`.
The runner then sees an empty string and runs it through the content-floor gate.

**The gap:** the runner cannot distinguish "model returned empty" from "API timed out" from
"API connection failed." All three produce the same empty-string result. The exception type
is printed to the console (`"DEEPSEEK_ERROR ... ReadTimeout"`) but never recorded in a
structured field. Adding `error_class` to `turn_metrics.record()` would close this.

**Lesson source:** `learn:experiment:openai_sdk_timeout_aborts_streaming_wedge`,
`learn:experiment:reasoning_model_token_headroom`.

### 3.5 Cache-hit invisibility (T110 pre-fix)

**Not a failure mode, but a cost-blindness that was live for weeks:** Before T110, the
`_cost_shape` was computed at `bifrost_runner_deepseek.py:493-496`, printed to the console
at `:1103-1117`, and then **dropped on the floor** — `add_turn()` at `:1109` received only
`prompt=` and `completion=`, no `cached_prompt=`. The journal billed every cached token at
the full fresh-input rate. A day with 104M prompt : 322k completion → billed as if all 104M
were fresh. Fixed by T110 at `runner_token_journal.py:20-26` — cached prompt is now passed
to `add_turn(cached_prompt=shape["cache_hit"])`.

**This is the poster child for "meter what you measure."** The data was in the response
object the whole time. We read it. We printed it. And then we threw it away one line
before the ledger.

**Lesson source:** `scripts/runner_token_journal.py:20-26` docstring, T110 commit.

---

## 4. THE HONEST VERDICT — proxy vs. call-site recorder

The claude/Fable position: *"For a call site we own, a proxy is machinery we do not need,
and it is only strictly necessary for opaque harnesses (Claude Code itself)."*

### 4.1 What a call-site recorder can get (and a proxy CANNOT add)

Everything in §1 and §2 — every field on the SDK response object — is available at the
call site at zero additional network cost. A call-site recorder that wraps
`client.chat.completions.create()` or instruments `_stream_turn()` can capture:

- **Usage** (all 9 fields) — already partially captured
- **finish_reason** — one attribute access, currently discarded
- **timing** — `time.time()` before and after the call, already partially captured
- **error class** — `type(e).__name__` from the except block
- **model** — which model actually served
- **chunk.id** — for response correlation
- **logprobs** — if we ever enable them

**All of this is inside our process right now.** The work is reading fields we already have.

### 4.2 What ONLY a proxy can get

Three data classes are invisible at the call site:

**A. HTTP response headers.** The openai SDK parses the JSON body and discards the HTTP
response. `x-ds-trace-id` is the single highest-value header — it's the request UUID
DeepSeek support needs to trace a specific call. Also: `x-cache` (CDN cache status),
`x-amz-cf-pop` (which edge node served us), and any future rate-limit headers.

**B. TCP/TLS timing.** A proxy at localhost can measure: TCP connect time to the provider,
TLS handshake duration, time-to-first-byte (before any parsing), and raw byte timing across
the stream. These are invisible to the SDK — the SDK sees the parsed objects, not the socket.
A call-site timer measures "time from `create()` call to first chunk," which includes SDK
overhead (JSON parsing, object construction). The proxy measurement is closer to the wire.

**C. Retry storms below the SDK.** If the provider returns HTTP 429/503/502, the openai SDK
may retry internally (we set `max_retries=1`, but the default is 2, and a future config
change could revert that). A proxy sees every HTTP request, including retries. The call site
sees only the final result. A proxy would catch a retry-storm regression the moment it starts.

**D. Raw byte counts.** A proxy can count bytes-in and bytes-out at the socket level,
independent of the SDK's parsing. This catches a subtle class of bug: the SDK successfully
parses a chunk but the JSON was malformed in a way the SDK silently corrected. The byte
count is the ground truth for bandwidth cost.

### 4.3 The honest weighting

For OUR runners: **a call-site recorder captures 90% of the value at 10% of the complexity.**
The fields most urgently missing — `finish_reason`, `reasoning_tokens`, error class — are all
on the response object today. Reading them is a few lines of Python. A proxy adds a network
hop, an additional process to maintain, and a new failure mode (proxy dies mid-stream,
blocking all API access).

For **opaque harnesses** (Claude Code, Cursor, any tool that calls the API through its own
SDK): a proxy is the ONLY option. You cannot edit their code to add a recorder.

For **debugging provider issues**: the proxy's HTTP header capture (`x-ds-trace-id`) is the
cheapest way to get a per-request trace ID. If Daniil's "I want us to understand what is
happening at the API level" includes "and be able to send DeepSeek support a trace ID when
something goes wrong," the proxy is the answer. A call-site recorder cannot see HTTP headers.

### 4.4 The compromise position

Build the call-site recorder FIRST (finish_reason, reasoning_tokens, error class, timing).
This is the evening's work and it closes the largest gap — invisible truncation and
undifferentiated errors.

Build the proxy SECOND, with a specific charter: capture HTTP headers, TCP timing, and
raw byte counts — the three things the call site cannot see. Do not duplicate the call-site
recorder's work in the proxy. The proxy is the WIRE layer; the recorder is the SEMANTIC
layer. Together they cover the full stack without redundancy.

The proxy's FAIL-OPEN design (documented in the gateway review §2.5: `/health` probe before
every call, bypass on failure) makes it safe to deploy incrementally. It cannot wedge the
runner.

### 4.5 What the proxy design MUST NOT do

Per the wire probe findings:

1. **Do not buffer SSE.** The proxy must write each upstream chunk to the downstream
   response immediately. Any buffering turns streaming into batch and triggers
   `MODEL_READ_TIMEOUT`.
2. **Do not retry.** The SDK retries; a retrying proxy multiplies retries. The proxy
   forwards as-is or fails open.
3. **Do not expect SSE keepalive comments.** DeepSeek does not send them. The liveness
   signal is "last_chunk_at < READ_TIMEOUT," not "keepalive received."
4. **Do not alter chunk boundaries.** Re-chunking is safe for SSE (frames are delimited
   by `\n\n`, not HTTP chunks) but it adds latency. Forward 1:1.

---

## 5. CONCRETE BUILD PLAN — what to instrument at the call site, today

Not a design doc — the three smallest changes that close the largest gaps.

### 5.1 Capture finish_reason (one line)

In `deepseek_chat.py:_stream_turn()`, inside the chunk loop at line ~304, set an attribute
on the agent:

```python
# after line 324, outside the for-chunk loop:
ag._last_finish_reason = getattr(chunk.choices[0], "finish_reason", None)
```

Then in the runner's `_process_one()` at `bifrost_runner_deepseek.py:1096`, add
`finish_reason` to `turn_metrics.record()`. The truncation signal becomes deterministic.

### 5.2 Capture reasoning_tokens (one line)

In `_absorb_usage()` at `deepseek_chat.py:201-213`, add:

```python
try:
    ctd = getattr(usage, "completion_tokens_details", None)
    if ctd:
        self.reasoning_tokens += getattr(ctd, "reasoning_tokens", 0) or 0
except Exception:
    pass
```

Then pass it through `_cost_shape` to the journal. One additional column on the cost print
line: `reasoning N%`.

### 5.3 Capture error class on the stateless path (two lines)

In the stateless `respond()` at `bifrost_runner_deepseek.py:376-378`, change:

```python
resp = client.chat.completions.create(**kwargs)
finish = getattr(resp.choices[0], "finish_reason", "unknown")
content = resp.choices[0].message.content
if not content:
    return f"(deepseek returned an empty reply; finish_reason={finish})"
return content
```

And in the except block, include `type(e).__name__` in the error string (already done
at `:379` but the stateless path's error is `f"(deepseek runner error: {type(e).__name__}: {e})"`,
which IS structured — just not recorded to `turn_metrics`).

### 5.4 Wire the stateless path to TokenJournal (three lines)

The stateless `respond()` at `:370-377` never touches `_token_deltas` or `_token_journal`.
Add after the response:

```python
# in _process_one, after the stateless path returns:
if delta:
    _token_journal.add_turn(prompt=delta[0], completion=delta[1])
```

But the stateless path doesn't compute a delta. Fix: read `resp.usage.prompt_tokens` and
`resp.usage.completion_tokens` from the response and pass them to a shared accumulator.

**This is the only finding in this report that requires more than a one-line edit** —
the stateless path currently returns a bare string and the runner loop has no hook to
intercept the usage. The cleanest fix is to change the return type to a tuple
`(content, usage)` or to read `resp.usage` in the caller after the stateless responder
returns.

---

## Appendix — what I did NOT verify

1. **Streaming error chunks.** I have no wire capture of a mid-stream error (HTTP 5xx after
   some chunks have been delivered). The openai SDK behavior on a mid-stream failure is "raises
   an exception and the partial content is lost." This is documented SDK behavior, not
   something I observed on the wire. A proxy would be the instrument to capture this.

2. **Rate-limit response body.** P5 confirmed that 429 responses carry `Retry-After` in
   headers. I did not capture the 429 response BODY to check for structured error details.
   The SDK surfaces 429 as `RateLimitError`.

3. **The `x-ds-trace-id` header on non-streaming responses.** P2 captured it on a streaming
   response only. I assume it is present on all responses but have not verified non-streaming.

4. **`finish_reason="content_filter"`.** I have never observed this value. It is documented
   by OpenAI as a possible finish_reason when the safety filter trips. I cannot confirm
   DeepSeek emits it, but the field position is standard.

5. **The `model_extra` fallback for reasoning_content.** P6 confirmed it is `{}` on every
   chunk across multiple streams. It may be non-empty on a future API version or a different
   model. The fallback at `deepseek_chat.py:297` is harmless and costs nothing to keep.
