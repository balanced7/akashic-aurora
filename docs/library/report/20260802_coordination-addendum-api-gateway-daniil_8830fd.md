---
akashic_id: art_20260802_coordination-addendum-api-gateway-daniil_8830fd
akashic_sha: 6e34a5488338
schema_version: 1
status: current
type: report
date: 2026-08-02
title: coordination-addendum-api-gateway-daniil
gist: "# Addendum: the API gateway — owning the wire as the sensor's socket half Status: current (2026-08-02, claude#30e6af5c). ADDENDUM to researc"
visibility: fleet
body_type: markdown
seats: []
category: [coordination, agent-lifecycle, tooling]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T03:08:28"
updated: "2026-08-02T03:08:28"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-addendum-api-gateway-daniil_8830fd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-addendum-api-gateway-daniil

# Addendum: the API gateway — owning the wire as the sensor's socket half

Status: current (2026-08-02, claude#30e6af5c). ADDENDUM to
research/in-flight/coordination-standing-engagement-sensors-daniil-2026-08-02.md — filed
separately because that doc is under review (kimi mid-flight); the main doc is NOT edited.
This implements the socket half of Wave 0 and answers deepseek review finding (1): the
socket tap SUPPLEMENTS the existing on_trace/on_activity tool-dispatch hooks, never
replaces them.

## Daniil, verbatim

"Can we make our own interface for the api or a parser after api output to the cloud? how
can we get to know what is going on inside the api, how can we access deeper signals by
being smart about it"

## The proposal: become the endpoint

Every runner client already takes a base_url (deepseek_chat.py make_client). Point it at a
localhost gateway of ours that forwards to the real provider and observes every byte both
directions. "Must be traversed" in its perfect form: the traffic cannot exist without
crossing the tap, because we are the wire. One gateway serves all OpenAI-compatible runners
(deepseek/kimi/gemini) — the sensor is built once. Our keys, our traffic, our machine: no
MITM, no TOS exposure.

Agent attribution: the runner adds an X-Akashic-Agent header; the gateway strips it before
forwarding and uses it to key the sensor hash.

## Signal inventory, by depth

TRANSPORT: request start; time-to-first-token (prefill + provider queue; spikes = cache
miss or throttle); inter-chunk cadence (tok/s; mid-stream decay = provider degradation);
drops/retries; RATE-LIMIT HEADERS (remaining requests/tokens, retry-after — the provider
declaring its throttle state; currently discarded).

STREAM STRUCTURE (the "parser after output"): finish_reason (stop | length = SILENT
TRUNCATION | content_filter = safeguards trip | tool_calls); final-chunk usage (exact
prompt/completion tokens; DeepSeek adds prompt cache HIT vs MISS counts — context
discipline graded by the provider per turn); reasoning_content as its own labeled channel.

REQUEST SIDE (underrated): outbound parsing meters context size per turn, message count,
tool-roster bytes — the token-frugality directive becomes a measured quantity at the
chokepoint instead of a discipline.

DEEPER: logprobs → per-token ENTROPY (where the model was confident vs guessing;
high-entropy stretches correlate with fabrication risk) — a codebook column nobody has:
not "is it alive" but "is it sure". VERIFY AT BUILD: streaming + logprobs support on
DeepSeek/Moonshot is a docs claim, not a tested fact.

THE HONEST CEILING: logprobs are the bottom of the visible stack. Logits, activations,
attention — the provider's door stays shut. What we own completely: timing, structure,
confidence, cost, termination cause.

## Receipts that this class of signal pays

- reasoning_model_token_headroom lesson: runners dying on truncated replies WAS
  finish_reason=length being swallowed. The gateway makes it a counter in week one.
- fable-safeguards-downgrade memory: the model_refusal_fallback markers found by hand in
  session JSONLs (13x) WERE output-parsing for a deep signal — done manually, once. The
  parser generalizes a receipt already paid.

## Harness seats (claude/codex): the twin tap

The socket is inside the harness. (a) Session-JSONL parser — the harness streams every
event to disk; same fields, slightly delayed, no auth risk. THE v1 tap. (b)
ANTHROPIC_BASE_URL gateway routing exists in the harness but is fragile/unsupported under
Pro-plan OAuth — explicitly NOT v1.

## Rules carried from the main design, unchanged

Gateway FAILS OPEN (bypass mode; it must never be able to take the fleet down); meters by
default, content only into the trace lane by deliberate choice; liveness verdicts from
STRUCTURE (cadence, finish_reason), never from parsing what the model said; the gateway is
one more single-writer field-set on bifrost:sensor:<agent>, feeding the same codebook —
where TTFT+cadence split "composing" into prefill / decoding / throttled / truncated (four
states currently rendered as one).

## Open questions for review (deepseek lens: reverse-engineering)

(1) SSE ground truth: what ACTUALLY arrives in the stream — field shapes, keepalive
frames, usage placement, reasoning_content framing, logprobs-under-streaming reality.
(2) Proxy risk surface: what breaks with a localhost passthrough against the current
client config (httpx timeouts, SSE buffering, chunked encoding, retry doubling, pooling).
(3) TTFT/cadence semantics: what is genuinely inferable vs confounded.
(4) Whether the gateway changes the review's slice-1 sensor-hash field set.

## Open questions (kimi lens: premise/rot, AFTER its in-flight review)

(5) Does an in-path proxy create a new roster-that-lies or SPOF-shaped debt; substrate or
projection under the two-speed rule?
(6) Cold-seat: a fresh seat that configures base_url direct silently bypasses the sensor —
what forcing function makes the gateway discoverable/unavoidable?
