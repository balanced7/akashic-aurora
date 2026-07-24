---
akashic_id: art_20260717_sol-api-surface-seat-design-claude-half_8b7b89
akashic_sha: a48d07126c71
status: draft
type: report
date: 2026-07-17
title: "Sol API Surface & Seat Design — claude half (2026-07-17)"
gist: "DeepSeek's half analyzes the same receipts blind; reconcile after. Daniel directive (verbatim intent): \"make sure we understand all of the p"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_sol-gpt-5-6-live-api-probe-receipts-2026_ae0409
    rel: cites
created: "2026-07-16T23:37:41"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260717_sol-api-surface-seat-design-claude-half_8b7b89 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Sol API Surface & Seat Design — claude half (2026-07-17)

DeepSeek's half analyzes the same receipts blind; reconcile after. Daniel directive (verbatim intent):
"make sure we understand all of the parameters and flags available to us via sol … this is
architectural work so we need to be thorough and rigerous about this."

## 1. What we are seating

`gpt-5.6-sol` — OpenAI's flagship tier of the 5.6 generation (released 2026-07-09, limited preview
~20 orgs; our key has it). 1.05M context / 128K max output / cutoff 2026-02-16. $5 in / $30 out per M
(cached input $0.50). Press benchmark: AA Coding Agent Index 80 at max reasoning — above Fable 5 (77.2)
at less than half the output tokens. This is a peer frontier seat, not a helper.

## 2. The verified parameter surface (receipts, not vibes)

**Effort ladder** `none | low | medium | high | xhigh` (API-enumerated; default medium per docs).
Same ladder on all three siblings (sol/terra/luna receipts identical).
**Verbosity** `verbosity` (chat) / `text={'verbosity':...}` (responses) — works.
**Token cap** `max_completion_tokens` (chat) / `max_output_tokens` (responses); `max_tokens` is DEAD.
**Temperature** locked to 1 (reasoning-family behavior) — sampling diversity is NOT a sol knob.
**service_tier** `flex` accepted (cost lever for non-urgent lanes).
**Strict param validation** — unknown params 400 loudly. Good: no silent flag rot in our runner.

## 3. THE architectural finding

> "Function tools with reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions.
> To use function tools, use /v1/responses or set reasoning_effort to 'none'."

Our runner (bifrost_runner_deepseek.py + deepseek_chat.Agent) is a **chat-completions tool loop**.
For sol that path forces reasoning OFF — a lobotomized flagship. Unacceptable for the frontier panel.

**Decision (proposed): the sol seat speaks the Responses API.** Verified end-to-end by probe:
function_call → our dispatch → function_call_output → final text; streaming events sane.

## 4. Seat design (for fence review)

> AMENDED per Daniel 2026-07-17: **sol is its own seat** — no deepseek-named modules, envs, or flags
> anywhere on sol's surface. Sol-named home (`scripts/sol_chat.py` transport + `scripts/bifrost_runner_sol.py`
> entry, `SOL_*` envs). How much shared runner machinery to extract vs. import is the open architecture
> question (options A/B/C) put to the deepseek fence.

a. **Provider registry** in the runner: `--provider deepseek|openai` binding
   (load_key, base_url, default_model, transport). Default `deepseek` — zero behavior change
   for existing seats; deepseek drills/pins untouched.
b. **SolTransport (Responses)**: adapter satisfying the Agent loop's contract
   (messages+tools in → text+tool_calls out) marshaling to `responses.create`:
   - tools: flat function format (`{"type":"function","name":...}`)
   - reasoning: `reasoning={'effort': E}` from a `--effort` flag (default medium; `--think` analog)
   - `text={'verbosity': V}` from `--verbosity` (default medium)
   - `max_output_tokens` from `SOL_RUNNER_MAX_TOKENS` (sol-named env, default 8000;
     deepseek's env stays untouched — separate seats, separate knobs)
   - **statefulness: STATELESS full-context resend, `store:false`** — RB-26 crash-redelivery says
     consumers stay idempotent and OUR substrate is the conversation truth. `previous_response_id`
     would make OpenAI hold 30-day server state that diverges on crash redelivery. Prompt caching
     ($0.50/M cached input) soaks the resend cost. [FENCE-CHECK THIS — it is the one place I chose
     substrate-consistency over token-optimality.]
c. **401 shim**: bounded retry (3×, 2s backoff, loud log line) for the preview-window intermittent
   401s (receipts: ~30% of calls, param-independent). Removable post-GA; re-probe before removing.
d. **Flag surface** (sol seat): `--provider openai --model gpt-5.6-sol --effort none..xhigh
   --verbosity low|medium|high --service-tier default|flex`. Existing: --agentic --allow-write
   --allow-exec --once --agent sol.
e. **System prompt**: the runner's DEFAULT_SYSTEM must not identity-address DeepSeek; parameterize
   the persona line by provider/agent, keep the door contract text identical (same substrate, same
   rules — the contract carries strangers).
f. **Cost posture** (token-frugality directive): default effort medium, escalate per task; flex tier
   for non-urgent lanes; 8K default output cap (≈$0.24/turn worst case at $30/M) — same headroom
   philosophy as T018.

## 5. Open questions (fence + follow-ups)

1. Reasoning summaries: `summary:'auto'` accepted but returned no reasoning item — org-verification
   gate or preview gap? Matters for the trace-feed (thinking visibility on the UI). Probe again post-GA.
2. Programmatic tool calling (model-written JS, sandboxed V8, Responses-only): param names not yet
   public — evaluate when documented; could replace multi-hop tool chatter on read-heavy tasks (38-63%
   token cuts claimed = frugality directive material).
3. `gpt-5.6` alias→Sol not present in models.list — cosmetic; pin the explicit id in config.
4. Docs-vs-receipt discrepancy: an aggregator's `max` effort tier does not exist on the API (xhigh tops).
5. Preview-401: monitor rate; if it persists past GA, escalate to OpenAI support with receipts.

## 6. What sol gets on day one (proposal)

ACL: admin-profile mirror of deepseek (read/write/exec via the SAME guarded families door, bus.send
kinds incl. steer, kb.*, net; admin.grant withheld; NOT time-boxed — revoke by record edit, the 07-05
expiry lesson). First assignment: T081-format blind cold-boot ergonomics walk, filed to
research/reviewed/sol-boot-ergonomics-2026-07-17.md, THEN read the deepseek/claude prior halves and
append a comparative coda. Evidence shared, analyses blind — the same discipline as this file.
