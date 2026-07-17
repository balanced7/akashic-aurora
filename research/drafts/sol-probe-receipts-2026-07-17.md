# Sol (gpt-5.6) Live API Probe Receipts — 2026-07-17

Shared EVIDENCE file for the T090 dual analysis (claude half + deepseek half cite this; analyses stay blind to each other, evidence is common). Probes run 2026-07-17 ~03:25-03:35Z from the E:\AI-Setup host, openai SDK 2.24.0, project-scoped key (`.secrets/openai.key`, gitignored — key material never in this file). Probe scripts: session scratchpad `probe_sol.py` / `probe_sol2.py` (session-ephemeral; receipts below are the durable record).

## Models list (123 visible; the relevant slice)

- `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra` — NO plain `gpt-5.6` in the list (docs say `gpt-5.6` is an alias routing to Sol; unverified by probe).
- Full families also visible: gpt-5 .. gpt-5.5(-pro), o-series, gpt-4.x, audio/realtime/image/sora lines. Key sees the whole catalog — 5.6 access confirms the org rides the limited preview (~20 orgs per press).

## Round 1 receipts — gpt-5.6-sol

| Probe | Result |
|---|---|
| chat.completions minimal | OK ("OK") |
| chat + `max_tokens=16` | 400 `unsupported_parameter`: "'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead." |
| chat + `max_completion_tokens=16` | **401 "You have insufficient permissions for this operation."** (see anomaly section) |
| chat + `temperature=0.5` | 400 `unsupported_value`: "Only the default (1) value is supported." |
| chat + `reasoning_effort='low'` | OK |
| chat + `reasoning_effort='bogus'` | 400 `unsupported_value`: "Supported values are: **'none', 'low', 'medium', 'high', and 'xhigh'**." |
| chat + `verbosity='low'` | OK |
| chat + function tools (no explicit effort) | 400: "**Function tools with reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.**" (⇒ reasoning defaults ON — docs say default=medium) |
| responses minimal | OK |
| responses + `reasoning={'effort':'low'}` | OK |
| responses + `max_output_tokens=16` | OK |
| chat + unknown param (`bogus_param`) | 400 `unknown_parameter` (strict rejection — no silent flag rot) |

## Round 2 receipts

| Probe | Result |
|---|---|
| chat + `max_completion_tokens=64` retry 1 | 401 insufficient permissions |
| retry 2 | 401 insufficient permissions |
| retry 3 | OK ("OK") |
| `gpt-5.6-luna` minimal | 401 insufficient permissions |
| `gpt-5.6-luna` + bogus effort | 400 — enumerates same ladder none/low/medium/high/xhigh (⇒ luna authed + validated fine here) |
| `gpt-5.6-terra` minimal | OK |
| `gpt-5.6-terra` + bogus effort | 400 — same ladder |
| **responses + tools ROUND TRIP** | OK: model emitted `function_call` calc({"expr":"6*7"}); submitted `function_call_output` "42" via `previous_response_id`; final = "42" |
| chat + tools + `reasoning_effort='none'` | OK — classic tool_calls returned (fallback path exists, reasoning off) |
| responses STREAMING | OK — events: response.created / in_progress / output_item.added / content_part.added / output_text.delta ×8 / output_text.done / content_part.done / output_item.done / completed |
| responses + `reasoning={'effort':'medium','summary':'auto'}` | OK but output item types = ['message'] only; **no reasoning item, no summary returned** (open question: org verification gate? preview limitation?) |
| responses + `service_tier='flex'` | OK |
| responses + `text={'verbosity':'low'}` | OK |

## The 401 anomaly (classified)

Intermittent `401 insufficient permissions` on ~30% of calls, **independent of parameters** (hit max_completion_tokens twice then passed unchanged; hit luna's minimal while luna's other probe validated). Working hypothesis: limited-preview access ACL / fresh project key propagation on OpenAI's side. Implication: SDK treats 401 as non-retryable ⇒ **sol transport needs a bounded retry-on-401 shim (loud), removable post-GA**. Re-probe before removal.

## Docs cross-check (secondary sources; receipts govern where they conflict)

- Family: Sol = flagship ("hardest problems, complex coding, security research"), Terra = balanced/volume, Luna = fast/cheap. Released 2026-07-09/10; limited preview ~20 orgs coordinated w/ US gov; GA "coming weeks".
- Pricing /1M tok: Sol $5 in / $0.50 cached / $30 out (>272K-input requests: 2× in, 1.5× out; cache writes 1.25× uncached). Terra $2.50/$15. Luna $1/$6.
- Sol page (developers.openai.com): context 1,050,000; max output 128,000; knowledge cutoff 2026-02-16; alias `gpt-5.6`→Sol; streaming/function-calling/structured-outputs supported; fine-tuning NOT; hosted tools in Responses: web search, file search, image gen, code interpreter, hosted shell, apply patch, skills, computer use, MCP, tool search. Rate limits tier 1-5: 500→15,000 RPM, 0.5M→40M TPM.
- **Discrepancy**: one aggregator lists a `max` reasoning tier — the live API error enumerates the ladder ending at `xhigh` ("max" likely = a Pro-mode/marketing artifact, or the separate `gpt-5.6-sol-pro` OpenRouter listing). RECEIPT WINS until OpenAI docs say otherwise.
- New in 5.6 (press, params not yet public): **programmatic tool calling** — model-written JavaScript in an isolated no-network V8, Responses-only, 38-63.5% token reductions claimed; explicit prompt-cache breakpoints (30-min min life); multi-agent beta in Responses.

Sources: openai.com/index/previewing-gpt-5-6-sol (403 bot-blocked, via search summary), openai.com/index/gpt-5-6, help.openai.com articles/20001325, developers.openai.com/api/docs/models/gpt-5.6-sol, dataconomy.com 2026/07/10, marktechpost.com 2026/07/09, github.blog changelog 2026-07-09, venturebeat.com, artificialanalysis.ai.
