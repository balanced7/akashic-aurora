---
akashic_id: art_20260804_api-wire-visibility-design-opus5_e76892
akashic_sha: fbe0e8017bd7
schema_version: 1
status: current
type: design
date: 2026-08-04
title: api-wire-visibility-design-opus5
gist: "--- status: current (2026-08-04, opus5 design-only lane) class: design lane: API-level telemetry (T140/T141/T153 neighbourhood). NOT livenes"
visibility: fleet
body_type: markdown
seats: []
category: [bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T01:20:37"
updated: "2026-08-04T01:20:37"
---
<!-- GENERATED PROJECTION of art_20260804_api-wire-visibility-design-opus5_e76892 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# api-wire-visibility-design-opus5

---
status: current (2026-08-04, opus5 design-only lane)
class: design
lane: API-level telemetry (T140/T141/T153 neighbourhood). NOT liveness — T155 is a separate seat.
ask: Daniil 2026-08-04 verbatim — "lets fix the liveness and the telemetry I want us to understand
     what is happening at the api level". Earlier, 2026-08-02 — "did we ever build that api proxy
     thing that would enable us to see closer to the wire the actual mechanics of what is going on
     inside the api?"
---

# Seeing the wire: API-level telemetry for our own runners

## 0. A correction to my own brief, recorded not resolved

My brief stated: *"Answer established: NO, never built."* That is **true of implementation and false
of design.** Before writing a line I found a complete prior arc from two days ago:

- `research/in-flight/coordination-addendum-api-gateway-daniil-2026-08-02.md` — a full gateway
  design answering Daniil's near-identical 2026-08-02 ask.
- `research/in-flight/wire-capture-deepseek-2026-08-02/` — a **battery of real API calls that
  already ran**: `probes.py` plus committed evidence (`p1-logprobs-stream.json`, `p2-raw-sse.txt`,
  `p2-byte-chunks.json`, `p3-ttft-decomposition.json`, `p4-forced-truncation.json`,
  `p5-rate-limit-headers.json`, `p6-extra-chunk-internals.json`).
- `research/in-flight/gateway-wire-probes-deepseek-2026-08-02.md` — empirical results with a
  `CONSOLIDATED GATEWAY SIGNAL INVENTORY` at `:347`.
- Two reviews: `gateway-review-wire-deepseek-2026-08-02.md`,
  `gateway-review-premise-kimi-2026-08-02.md`.

Both statements can be held at once: **no gateway or recorder exists in `scripts/` or `core/`**
(verified: no `wire_log`/`api_log`/`raw_response` symbol anywhere; no proxy/tap script). So "never
built" is correct. But this design is not a fresh start — it is the *third* pass on a question that
already has measured answers, and re-deriving them would be waste. Everything below that is marked
`[probe]` is cited from that battery rather than re-argued.

The one thing the prior arc did **not** produce is a decision. That is what this document is for.

---

## 1. RECOMMENDATION

**Build a call-site recorder. Do not build a network proxy. But move the recorder one layer down
from where "call-site" usually means — to the `httpx` transport the SDK already uses.**

I agree with the conductor's conclusion and reject part of its reasoning.

### Where the conductor is right

A network proxy for runners whose call site we own is the wrong first move. It buys nothing we
cannot get in-process, and it costs: a second process to supervise, a new SPOF in the fleet's
critical path, a bypass mode to design and test, TLS/auth re-plumbing, and a `base_url` rewrite on
four clients. The prior gateway design conceded the SPOF risk itself — it specifies *"Gateway FAILS
OPEN (bypass mode; it must never be able to take the fleet down)"*. A component whose design must
include its own bypass switch is announcing its risk.

**The existence proof is already in the repo.** `wire-capture-deepseek-2026-08-02/probes.py:69` is
headed *"P2: RAW WIRE CAPTURE — httpx direct, no SDK filter"*. At `probes.py:88-118` it opens
`HTTPX.stream(...)` (client built at `probes.py:23`) and records the HTTP status
(`raw_lines.append(f"# HTTP {resp.status_code}")`, `:103`), **every response header** (`:104-105`),
and **per-byte-chunk arrival timings** (`:107-113`). No proxy. No network configuration. Nothing
outside the Python process. Every signal the gateway design wanted was captured in-process, two days
ago, by the same library our SDK already runs on.

### Where the conductor is wrong

The brief says a call-site recorder *"gets the same data"*. **If "call-site" means wrapping the SDK
method — `client.chat.completions.create(...)` — that is false**, and it fails on two of the seven
things Daniil explicitly asked to see.

1. **Retries are structurally invisible.** Every client is constructed with an explicit
   `max_retries` (`core/comm/runner_lib.py:17,27`; `scripts/deepseek_chat.py:63,74`;
   `scripts/sol_chat.py:55,65`). The SDK retries **inside** one method call. A wrapper around
   `create()` sees one logical call and cannot know whether it cost one HTTP request or three. Daniil
   asked for retries by name.
2. **HTTP status and response headers are not reachable from the returned object.** This is measured,
   not assumed: `p5-rate-limit-headers.json` records `"note": "no _response/response attribute on
   the SDK result"`, and its `dir_resp` dump confirms the parsed object exposes `choices`, `usage`,
   `model`, `_request_id` — and no headers, no status. `[probe]`

Both become visible one layer down, and that layer is still in-process. `openai==2.24.0` accepts an
`http_client=` parameter (verified present in `OpenAI.__init__`; `httpx==0.28.1`), and **`http_client`
appears nowhere in `scripts/` or `core/` today** — a clean, uncontested seam. A custom transport sees
each retry as a separate `handle_request`, with its own status, headers and latency.

So the real correction is to the framing, not the verdict: **"proxy vs call-site" is a false
dichotomy.** The httpx transport hook is not a compromise between them. It is the wire — on our side
of TLS, inside our own process, with no second component to keep alive.

### Verdict

| | Build? | What it uniquely buys |
|---|---|---|
| **httpx-layer recorder (in-process)** | **YES — first and probably only** | status, headers, retries, per-attempt latency, byte timings, raw body — with no network config, no TLS interception, no new process |
| SDK-method wrapper | No, as a separate thing | Nothing the layer below lacks. It does have the assembled response, which the recorder gets by other means (§2) |
| Network proxy | **No** | Nothing, for clients we construct |
| Proxy for **opaque** harnesses (Claude Code) | Deferred, and probably never | The prior design already ruled here, and against itself: the session-JSONL parser is *"THE v1 tap"*, while `ANTHROPIC_BASE_URL` routing is *"fragile/unsupported under Pro-plan OAuth — explicitly NOT v1"*. A proxy is the expensive answer to a question a file tail already answers. |

**One honest complication, stated up front.** The agentic DeepSeek path streams:
`scripts/deepseek_chat.py:261` sends `"stream": True, "stream_options": {"include_usage": True}`. A
transport that *reads* a streaming response body to record it would consume the stream the runner
needs. This is the single real engineering hazard in the design, and it is why the recorder is
**two-tier** (§2.4): the default tier never touches the body at all.

---

## 2. THE RECORD SHAPE

### 2.1 The validity vocabulary (T141, used exactly as the ledger states it)

T141 defines three states by rule rather than by a named enum:

- **MEASURED** — the sensor was explicitly activated. A zero here is a real zero and means zero.
- **UNKNOWN** — the counter was never observed. Renders as `null`. Also: any derived value whose
  inputs are incomplete.
- **UNDEFINED** — a derived ratio with a zero denominator.

Every field below carries its state. **The state is stored, not inferred at read time.** A reader
must never have to reconstruct "was this observed?" from the value.

This is not novel — it is the generalisation of a move already made twice in this repo:

- `scripts/deepseek_chat.py:215-221`, `cache_rate()`, whose docstring is the clearest statement of
  the principle anywhere in the codebase: *"None, never 0.0: 'no cache data' and 'nothing was
  cached' are different facts, and collapsing them is how a dead meter reads as a real reading."*
- T110's **UNPRICED** as a first-class counted, named, rendered state in
  `scripts/runner_token_journal.py:24-30`: *"PRICE WHAT WE CAN SOURCE, AND MAKE WHAT WE CANNOT
  SOURCE VISIBLE RATHER THAN PLAUSIBLE."*

### 2.2 The record

One record per **HTTP attempt** (not per logical call — that is the point of the layer). Records
sharing a `call_id` are attempts of one call; `attempt_ix` orders them.

**Identity and routing**

| Field | State | Source |
|---|---|---|
| `call_id` | MEASURED | recorder-generated uuid, stable across retries |
| `attempt_ix` | MEASURED | recorder counter, 0-based |
| `agent_id` | MEASURED | runner-injected at client construction |
| `ts_request_sent` | MEASURED | recorder clock |
| `method`, `url_path` | MEASURED | httpx request. **Path only — never the query string** (§4) |
| `model` | MEASURED | request body |
| `stream` | MEASURED | request body |
| `provider_request_id` | MEASURED **or** UNKNOWN | response header when present; UNKNOWN when absent |

**Outcome**

| Field | State | Source |
|---|---|---|
| `http_status` | MEASURED **or** UNKNOWN | UNKNOWN when the attempt died before a response (connect timeout, DNS, reset) |
| `error_class` | MEASURED **or** UNDEFINED | exception type name; UNDEFINED on success — no error is a *category error*, not a missing measurement |
| `finish_reason` | MEASURED / UNKNOWN / UNDEFINED | `stop`/`length`/`tool_calls`/`content_filter` `[probe]`. UNKNOWN if the body was not parsed (tier-0, §2.4). UNDEFINED on a non-200 — a failed call has no finish reason |
| `truncated` | derived: `finish_reason == "length"` → MEASURED; else inherits `finish_reason`'s state |

**Timing** — all recorder-computed, all MEASURED when the attempt produced the relevant event, else
UNKNOWN. Never 0.

| Field | Notes |
|---|---|
| `latency_total_ms` | last byte − request sent |
| `ttfb_ms` | response headers received − request sent |
| `ttft_ms` | first content-bearing chunk − request sent. UNDEFINED for non-streaming |
| `ttft_reasoning_ms` | UNKNOWN when the model emits no reasoning; UNDEFINED for providers with no reasoning channel |
| `last_chunk_gap_ms` | max inter-chunk gap; the stall signal `[probe]` |

**Token accounting — counts only. No prices. Ever.** (§5)

| Field | State | Source |
|---|---|---|
| `usage_raw` | MEASURED or UNKNOWN | **the provider's usage object verbatim**, unnormalised |
| `prompt_tokens` | MEASURED or UNKNOWN | normalised across dialects (below) |
| `completion_tokens` | MEASURED or UNKNOWN | ditto |
| `reasoning_tokens` | MEASURED / UNKNOWN / UNDEFINED | `usage.completion_tokens_details.reasoning_tokens` `[probe]`. UNDEFINED where the provider has no reasoning channel |
| `cache_hit_tokens`, `cache_miss_tokens` | MEASURED or **UNKNOWN** | see the live defect below |
| `cache_hit_ratio` | MEASURED / UNKNOWN / **UNDEFINED** | UNDEFINED when hit+miss == 0 |
| `tokens_estimated_local` | **never populated** | out of scope; a local tokeniser estimate is a different measurement and would invite silent substitution |

`usage_raw` is stored **because the four providers do not agree**, and normalisation loses evidence.
Verified, three distinct dialects across four providers:

- DeepSeek: `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` (`scripts/deepseek_chat.py:209-210`)
- Kimi and Gemini: `cached_tokens` **or** `prompt_tokens_details.cached_tokens`, probed in order
  (`scripts/kimi_chat.py:144-145`; `scripts/gemini_chat.py:133-134`)
- Sol: the **Responses** API — `input_tokens` / `output_tokens`, not `prompt_`/`completion_`
  (`scripts/sol_chat.py:232-233`)

**A live measured-zero defect, visible in production data right now.** Both `_cached_tokens` helpers
document their own failure: *"Absent -> 0 -> bills full price"* (`scripts/kimi_chat.py:143`,
`scripts/gemini_chat.py:132`). Today's on-disk evidence,
`state/runner_kimi_2026-08-02.json`:

```json
{"agent":"kimi","turns":22,"prompt_tokens":3948826,"completion_tokens":74023,"cached_prompt_tokens":0}
```

3.95M prompt tokens over 22 turns — ~180k per turn, overwhelmingly resent context — reporting
**exactly zero cache**. That zero is almost certainly UNKNOWN wearing MEASURED's clothes. It is the
T140 hazard, in the live money path, dated two days ago. For billing the conflation is *conservative*
(it overcharges rather than under). For observability it is fatal, and it is the single strongest
argument that this design's core contribution is the validity state, not the extra fields.

A related contradiction worth recording rather than fixing here: `deepseek_chat._absorb_usage`
(`:207-212`) degrades every absent field to `0` via `or 0`, and `cache_rate()` (`:215-221`) then
recovers the distinction by testing whether `hit + miss == 0`. That works **only while both fields go
missing together**. A provider that reported misses but not hits would read as a confident 100% miss
rate. The recovery is real but incidental.

**Content — the redaction-governed fields.** Default tier stores no bodies (§4).

| Field | State | Default tier |
|---|---|---|
| `request_bytes`, `response_bytes` | MEASURED | always (sizes are cheap and never sensitive) |
| `request_sha256`, `response_sha256` | MEASURED | always — gives dedup and "did the prompt change?" without the prompt |
| `messages_shape` | MEASURED | roles, per-message char counts, tool-call names. Structure without content |
| `request_head`, `request_tail` | MEASURED or UNKNOWN | bounded excerpt, redacted, opt-in |
| `request_body`, `response_body` | **UNKNOWN by default** | tier-2 only, flag-gated, rotating (§4) |

**Genuinely unavailable — do not add fields for these:**

- *Rate-limit headroom.* Settled empirically: DeepSeek sends **no rate-limit headers on 200**; limits
  surface only as a 429. `[probe]` — *"The gateway cannot predict rate limits from headers. It must
  react to 429s."* Any `rate_limit_remaining` field would be permanently UNKNOWN for this provider.
- *Server-side queue vs prefill time.* TTFT confounds them and cannot be decomposed from outside
  `[probe]`.
- *Anything inside the model.* Logprobs are the floor of the visible stack; attention, routing and
  sampler state are not exposed by any provider. This is the honest ceiling on Daniil's "deeper
  signals", and it should be said plainly rather than implied away.
- *Reasoning coordination-vs-productive split.* The API reports reasoning **token counts**, never
  their purpose. See §5.
- *`:keepalive` SSE comments.* Refuted by probe: zero observed across two streams `[probe]`. The
  `model_extra` fallback at `scripts/deepseek_chat.py:299` is likewise dead for DeepSeek `[probe]`.

### 2.3 Serialisation rule

`null` alone is not enough — a JSON `null` is indistinguishable from a field a future writer forgot.
Each non-trivially-measured field serialises as an object:

```json
"cache_hit_ratio": {"v": null, "s": "UNDEFINED", "why": "hit+miss==0"}
"cache_hit_tokens": {"v": null, "s": "UNKNOWN"}
"prompt_tokens":    {"v": 4193, "s": "MEASURED"}
```

Cost: ~2x bytes on annotated fields. Worth it, and §4 keeps the volume bounded anyway.

### 2.4 Two tiers, because streaming

- **Tier 0 — metering (default, always on).** An `httpx` **event hook** pair. Sees request metadata,
  status, headers, and timing. **Never reads the response body**, so streaming is untouched and there
  is no risk of consuming the runner's stream. Body-derived fields (`finish_reason`, `usage_raw`,
  token counts) are UNKNOWN at this tier *from the transport* — and are filled instead by a thin
  **usage-capture callback** at the point where the runner already assembles the stream
  (`scripts/deepseek_chat.py:199` `_absorb_usage`, and its siblings), which is where those values
  already exist. The recorder correlates the two halves by `call_id`.
- **Tier 2 — body capture (flag-gated, off by default, bounded).** A custom transport that **tees**
  the byte stream into a bounded buffer while passing it through. Only under
  `AKASHIC_WIRE_BODIES=1`, only into a rotating sink, never in an unattended overnight run.

There is no tier 1. The gap is deliberate: tier 0 is the honest default and tier 2 is a debugging
posture, and blurring them is how full prompts end up on disk forever.

---

## 3. WHERE IT HOOKS

Every runner's API traffic passes through **exactly four `make_client` factories**, and two of them
already delegate to one shared seam (K0):

| File:line | Serves | Shape |
|---|---|---|
| `core/comm/runner_lib.py:14-27` — `make_openai_compat_client` | **gemini + kimi** | shared factory; builds `OpenAI(...)` |
| `scripts/gemini_chat.py:82-87` — `make_client` | gemini | thin wrapper, delegates to the above |
| `scripts/kimi_chat.py:83-88` — `make_client` | kimi | thin wrapper, delegates to the above |
| `scripts/deepseek_chat.py:66-74` — `make_client` | deepseek | inline `OpenAI(...)` |
| `scripts/sol_chat.py:59-65` — `make_client` | sol | inline `OpenAI(...)` |

So the hook is **three edits**, each adding one optional `http_client=` argument: `runner_lib.py:25`,
`deepseek_chat.py:72`, `sol_chat.py:63`. Or **one edit** if `deepseek_chat` and `sol_chat` are first
migrated onto the shared factory — a strangler-fig step the K0 seam already invites
(`runner_lib.py:14` exists precisely because "the deepseek, sol and kimi seats share one seam").
I recommend the three-edit version first: migration and instrumentation in one slice is two changes
wearing one commit.

The single downstream consumer of the deepseek client is
`scripts/bifrost_runner_deepseek.py:376` — `resp = client.chat.completions.create(**kwargs)` — and it
needs **no change at all**. That is the argument for this seam in one line: *the call sites do not
move.*

### Staying on the runner side of the membrane

The membrane law's canonical statement is
`docs/library/design/20260724_t106-build-specs-o15-seat-lease-a1-await_6fc93b.md:42` — *"runners
NEVER consume via MCP -- seat-model agents only"* — restated and extended for players in
`docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:568-577` (*"Players stay
outside the core"*). Note for the record: `docs/LIVE_CONSTRAINTS.md` contains **zero** occurrences of
"runner", "membrane", or "subprocess". The law is real but it is not codified in the standing
constraints doc — a gap I am flagging, not filling.

The design respects it structurally:

- **The recorder module lives in `scripts/`, not `core/`** — `scripts/wire_journal.py`, sibling to
  `scripts/runner_token_journal.py`, which is the exact precedent for a runner-side meter.
- **`core/comm/runner_lib.py` gains no recording logic.** It gains one optional pass-through
  parameter and stays a pure factory. Core never imports the recorder; the runner side injects it.
  If the parameter is absent, behaviour is byte-identical to today.
- No MCP. No bus. No Redis on the hot path. The recorder writes one local file and nothing else.

---

## 4. REDACTION AND RETENTION

**A design that quietly writes full prompts to disk forever is a finding, not a feature.** Agreed, and
here is the arithmetic that makes it concrete, from real data rather than estimate:
`state/runner_kimi_2026-08-02.json` records 3,948,826 prompt tokens in one day for **one** agent.
At ~4 bytes/token that is **~16 MB/day of prompt text for kimi alone**; four runners on a busy day is
plausibly 50-100 MB/day, i.e. **~5-9 GB per 90-day season** — and because prompt volume is dominated
by *resent context*, the overwhelming majority of those bytes are the **same repo content written
dozens of times**. Full-body capture as a default is not a privacy problem first; it is a
self-inflicted storage problem that also happens to be a privacy problem.

**Policy.**

1. **Header allowlist, never a denylist.** Only `content-type`, `content-length`, and known-safe
   provider headers are recorded. `Authorization` is **not dropped by rule — it is never read**. A
   denylist is one provider-specific header name away from leaking a key; this is the one place the
   design refuses a "filter it out" approach.
2. **URL path only. Never the query string.** Some providers accept keys as query params.
3. **Default tier stores no bodies.** Hash + length + `messages_shape` answer most real questions
   ("did the prompt change?", "how big was context?", "which tools were offered?") without storing
   content at all.
4. **Bodies are opt-in, bounded, and rotating.** `AKASHIC_WIRE_BODIES=1` only. Bounded per-record
   (head/tail excerpt, default 2 KB each) and bounded in aggregate: a size-capped rotating sink
   (default 256 MB, oldest-first eviction) — **bounded by bytes, not by days**, because a day is not
   a unit of volume.
5. **Where the bytes live.** `state/wire/<agent>/<date>.jsonl`. Two independent reasons this is the
   right home, both verified: `.gitignore:108` ignores `state/*`, and `.gitignore:50` ignores
   `*.jsonl` globally (the negations at `:52,55,59` do not cover `state/`). The capture is
   **doubly gitignored** and cannot be committed by accident.
6. **The redactor fails CLOSED.** See §7 — this is the one component that must not fail open.

**A gap, stated plainly: there is no content-redaction helper in this repo to reuse.** The only
secret-aware code is `core/comm/toolbox.py:242-249`, `_is_secret`, and it is **path-based** — it
refuses to *read* `.env`, `*.pem`, `id_rsa` and friends. It does not scan text for secret *values*.
So content redaction must be built, not borrowed. This slightly reduces the risk (the ToolBox already
prevents most secret file content from entering a prompt) and does not eliminate it (a secret pasted
by a human into a bus message rides straight through).

Given that, tier 2 carries a standing rule: **body capture is an attended debugging mode.** Turn it
on to investigate, turn it off when done. It is not a season-long posture.

---

## 5. RELATIONSHIP TO T140 / T141 / T153

**This COMPLEMENTS `cognitive_metrics`; it does not subsume it.** They measure different planes: the
wire journal measures *the API call*, `cognitive_metrics` measures *the agent's turn*. Merging them
would produce a module that is authoritative about neither.

**Money stays in `TokenJournal`. The wire journal emits counts and never a price.** It holds no
`PRICES` table, no `cost_est`, no rate. If a cost question needs wire data, `TokenJournal` gains a
reader — the wire journal does not grow a wallet. (`scripts/runner_token_journal.py:56-65` stays the
sole rate card; `price_of()` at `:79` stays the sole pricing door.)

Of T140's **12 dead recorders**, this work makes **2 honestly live**, offers **1 partially**, and
leaves **9 dead** — and the honest accounting matters more than the count:

| Recorder | Verdict |
|---|---|
| `record_prompt_tokens` (`cognitive_metrics.py:156`) | **LIVE** — MEASURED from `usage` |
| `record_completion_tokens` (`:161`) | **LIVE** — MEASURED from `usage` |
| `record_reasoning` (`:166`) | **PARTIAL, and this is the interesting one.** The API gives reasoning *token counts* `[probe]`. It never gives their *purpose*. The signature takes `category: 'coordination' \| 'productive'` — a semantic judgment no provider reports. Wire data can fill the total and must leave the split **UNKNOWN**. Filling the split from wire data would be fabrication. |
| `record_abandoned` (`:175`) | DEAD — needs barge-in correlation, not wire data |
| `record_context_refresh` (`:201`) | DEAD — a runner-loop fact |
| `record_tool_call` (`:206`) | DEAD here — a runner-loop fact. **This is T153's territory**, not this design's |
| `reset`, `reset_all`, `disable`, `enable`, `dump`, `dump_all` (`:238-275`) | Unaffected — lifecycle, not sensors |

**The unpopulated-field hazard is not fixed by this design and must not be claimed as fixed.**
`cognitive_metrics.py:63-98` — the five derived properties — each `return 0.0` on an empty
denominator. `coordination_token_ratio` returning `0.0` reads as *"0% of effort on coordination"*,
an excellent result, when it means *"no data"*. That is T141's job, it is claimed by `codex_root`,
and its acceptance already names the fix. **This design must not race it.** Concretely: I add no
field to `EfficiencySnapshot` and change no file under `core/coord/`.

**Ordering.** T141 lands first, or at minimum its validity vocabulary does. If the wire journal ships
first it should carry its own validity states (§2.3) and adopt T141's type when it exists. I would
rather have two compatible three-state vocabularies converge than block this on another seat's claim.

**T153** is untouched and stays open. Verified independently: `scripts/bifrost_runner.py` references
`cognitive_metrics` **zero times** (grep count 0 over 275 lines), while all four provider runners call
`cog.init` — `_deepseek:1365`, `_gemini:748-749`, `_kimi:804-805`, `_sol:726-727`. Worth noting for
whoever takes T153: the generic runner would inherit wire telemetry **for free** the moment it uses
any of the four `make_client` factories, because the hook is in the factory rather than in the runner.
That is a second argument for the seam chosen in §3.

---

## 6. PINS (M3: pre-registered acceptance, RED first)

Per `docs/method-baseline-2026-07.md:180-191` — *"the acceptance is a NAMED failing test (or strict
xfail) committed BEFORE the fix builds... Flipping the xfail off IS the completion event"*, and the
bar: *"no slice ships whose acceptance postdates its implementation."*

All in `tests/test_wire_journal.py` unless noted. Naming follows the T110 precedent
(`tests/test_t110_cost_meter_honesty.py`, `tests/test_t110_runner_globals_defined_once.py`).

**P1 — NEGATIVE PIN (the required one): an unmeasured field renders UNKNOWN, never 0.**
Record a call whose response carries no cache fields. Assert `cache_hit_tokens.s == "UNKNOWN"` and
`cache_hit_tokens.v is None`. Assert **`0 not in (v for v in record.values())` for every
UNKNOWN-stated field**, and assert the serialised JSON contains no bare `0` for an unobserved
counter. Companion assertion in the same test: a response that *does* report `cached_tokens: 0`
renders `{"v": 0, "s": "MEASURED"}` — proving the two zeros are distinguishable, which is the whole
claim.

**P2 — UNDEFINED is distinct from UNKNOWN.** `hit + miss == 0` → `cache_hit_ratio.s == "UNDEFINED"`;
body never parsed → `finish_reason.s == "UNKNOWN"`. A test that accepts either state for either case
fails the pin.

**P3 — retries produce multiple records.** With a stub transport failing once then succeeding under
`max_retries=1`: exactly 2 records, same `call_id`, `attempt_ix` 0 and 1, first with its own
`http_status`. **This is the pin that a SDK-method wrapper cannot pass** — it is the executable form
of §1's disagreement.

**P4 — the recorder never takes the runner down.** A recorder that raises on every hook: the call
still returns its normal result, and a `wire_journal_errors` counter increments. Asserted for both
tiers.

**P5 — REDACTION, fails closed.** (a) `Authorization` never appears in any output byte, asserted over
the raw serialised file. (b) Query strings are absent. (c) If the redactor raises, the record is
**dropped** and a drop is counted — assert the unredacted bytes are absent from the sink.

**P6 — streaming is not consumed.** Under tier 0 against a streaming stub, the caller receives every
chunk in order, byte-identical to the unhooked path. Guards the one real hazard in §1.

**P7 — bounded on disk.** Write past the cap; assert total sink size stays under it and that eviction
is oldest-first.

**P8 — no second pricing path** (`tests/test_wire_journal_no_pricing.py`). AST-check that
`scripts/wire_journal.py` contains no price literal, no `cost` symbol, and no import of
`runner_token_journal`. Precedent for AST-checking a structural rule already exists —
`tests/test_deepseek_chat_imports.py` does exactly this for the re-export list
(`scripts/deepseek_chat.py:82-86`), and `tests/test_t110_runner_globals_defined_once.py` pins a
structural property across the three runners.

**P9 — the membrane holds** (`tests/test_wire_journal_membrane.py`). Assert nothing under `core/`
imports `scripts.wire_journal`, and that `core/comm/runner_lib.py` gains no recording logic — it may
only pass a client through.

---

## 7. COST AND RISK

**Per-call overhead.** Tier 0 is two event-hook invocations, a few `time.perf_counter()` reads, a
dict build and one buffered line append. Order **tens of microseconds** against API calls whose
measured TTFT is in the hundreds of milliseconds `[probe]` — call it under 0.1% and beneath
measurement noise. I have not benchmarked this; it is an estimate from operation counts, and P-series
pins do not currently assert an overhead budget. If that matters, add a pin — but I would not gate
the slice on it. Tier 2 adds a memcpy per chunk plus bounded buffering, and is off by default.

**Disk.** Tier 0: ~1-2 KB per record with validity annotations. At a few hundred calls/day across
four runners, **a few MB/month** — negligible, and it is the tier that runs unattended. Tier 2 is
capped by construction (§4) at a default 256 MB with oldest-first eviction, so the season-scale answer
is "the cap", not "it grows". The 5-9 GB/season figure in §4 is what tier 2 *would* cost **without**
the cap — it is the justification for the cap, not a projection of the design.

**If the recorder itself throws.**

**Tier 0 and tier 2 fail OPEN.** A telemetry component must never be able to take the fleet down. The
reasoning is not general principle but this repo's own history: `deepseek_chat._absorb_usage`
(`:199-212`) documents it — *"an exception here would silently cost us the whole meter, which is how
T078-W1 spent weeks reporting zero"* — and the prior gateway design conceded the same by specifying a
bypass mode. Failing open means: catch everything at the hook boundary, return control to the SDK
untouched, increment `wire_journal_errors`, and never re-raise. Pinned by P4.

**But the redactor fails CLOSED, and this is a deliberate asymmetry.** If redaction raises, we do not
know whether the bytes are safe. Failing open there means writing possibly-unredacted content to
disk — trading a *silent, permanent* confidentiality loss for an *observable, recoverable* gap in
telemetry. The record is dropped and the drop is counted. Pinned by P5(c).

Stated as one rule: **failing open is correct when the cost of failure is a missing measurement, and
wrong when the cost is a leaked secret.**

**The failure mode I would actually worry about** is neither: it is *silent success*. A recorder that
runs, writes, and is read by nobody is T140 repeating itself one directory over. `dump`/`dump_all` in
`cognitive_metrics.py:238-248` are called only by tests — nothing in production reads the accumulator
the runners feed. **This slice should not ship without naming its reader.** W105 in `docs/WISHLIST.md`
is Daniil verbatim on exactly this genus: *"The bifrost ui is giving me no indication of what kimi is
currently doing... The data already exists; this is a surfacing gap, not an instrumentation gap."* A
wire journal with no reader converts a surfacing gap into a second instrumentation gap. Whether the
reader is a `doctor` line, a UI pane (W24), or a CLI verb is a decision for the conductor — but it is
part of *this* slice, not a follow-up.

---

## 8. WHAT I DID NOT VERIFY

An explicit accounting, in the style of the prior Opus session.

**Not run, not measured:**
- **I ran no code and made no API call.** Every runtime claim is read from source or from the
  2026-08-02 probe artifacts. The overhead figures in §7 are estimates from operation counts.
- **I did not verify that `http_client=` composes with the SDK's internal retry loop as I claim.**
  I verified the parameter exists (`inspect.signature(OpenAI.__init__)`, openai 2.24.0) and that
  `http_client` appears nowhere in `scripts/` or `core/`. The claim that each retry surfaces as a
  separate transport call follows from how httpx transports work, but **P3 exists precisely because
  I could not confirm it without running it.** If P3 fails, §1's disagreement with the conductor
  weakens substantially — though the header/status argument, which is probe-backed, survives.
- **I did not test the streaming tee.** §2.4's tier-2 is the least-verified part of this design. P6
  guards the hazard; it does not prove the tee is implementable without a memory cliff on long
  streams.

**Sampled, not exhausted:**
- **Runner API call sites: exhaustive by grep, not by reading.** I grepped all four runners for
  `requests.post|httpx|client.chat|.completions.create|generate_content|OpenAI(` and found exactly
  one direct SDK call (`_deepseek:376`). I then traced the other three through their imports to
  `*_chat.py`. I read the four `make_client` bodies in full. **I did not read the ~4,400 lines of
  runner source**, so a call constructed some other way — an inline `OpenAI()`, a raw `urllib`
  call — could exist outside my greps. One such call *does* exist and I found it:
  `scripts/kimi_chat.py:145-155` uses `urllib.request` directly for `/users/me/balance`. It is a
  balance probe, not a model call, and my hook would not see it. **There may be others.**
- **`cognitive_metrics.py`: exhaustive.** I read all 275 lines. The 16-public-function count and the
  9-of-16-fields-pinned-at-0 arithmetic are mine and match T140's text exactly.
- **Ledger, wishlist, method-baseline, membrane: delegated** to a read-only subagent and used as
  quoted. I did **not** independently re-open `state/coord/tasks.json`, `docs/WISHLIST.md`, or
  `docs/method-baseline-2026-07.md`. T141's vocabulary and M3's text are quoted at one remove.
- **Probe artifacts: sampled at roughly 3 of 7 files.** I read the signal inventory in the results
  doc, plus `p5-rate-limit-headers.json` and the head of `p4-forced-truncation.json`. I did **not**
  read `p1`, `p2-raw-sse.txt`, `p2-byte-chunks.json`, `p3`, or `p6`. Every `[probe]` claim above is
  either from the consolidated inventory or from a file I opened.
- **Prior gateway design: read at one remove.** I have the subagent's quotes from
  `coordination-addendum-api-gateway-daniil-2026-08-02.md` and its two reviews; I did not read those
  documents end to end. **I am disagreeing with a design I have not read in full** — §1's argument
  addresses the mechanism as quoted, and if the addendum contains a reason for out-of-process capture
  that its summary omits, my §1 is incomplete. This is the largest single gap in this document.

**Deliberately not done:**
- **I did not touch T155's files.** `core/comm/bus.py`, `agent/bifrost_pull.py` and
  `core/comm/liveness.py` are under concurrent edit; I read none of them and depend on no line number
  in them. Liveness is not my lane.
- **I did not verify current W-numbering for a new wishlist entry.** The sweep reports W127 as
  highest, with a known hazard of same-day collisions. I filed nothing.
- **Design only, one file.** No code, no commits, no bus sends, no ledger writes. This document is
  the only file I wrote.

**Open contradictions recorded, not resolved:**
1. "Never built" is true of code and false of design (§0).
2. `_absorb_usage` conflates absent-with-zero while `cache_rate()` recovers the distinction — the
   recovery is incidental and would fail on an asymmetric provider (§2.2).
3. The membrane law is standing but absent from `docs/LIVE_CONSTRAINTS.md` (§3).
4. `state/runner_kimi_2026-08-02.json` reports 0 cached tokens on 3.95M prompt tokens. I believe this
   is UNKNOWN-as-MEASURED, but **I did not confirm that Moonshot actually caches or that the field is
   truly absent** — the alternative, that kimi genuinely gets no cache hits, is unlikely but unfalsified
   by anything I read.
