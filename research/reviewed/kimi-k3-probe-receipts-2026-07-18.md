# Kimi K3 Probe Receipts — 2026-07-18 (key-gated probes P1/P2/P3-lite/P4)

Method: scratch/kimi_probe.py (stdlib urllib, key from .secrets/kimi.key, never echoed) run
2026-07-18 ~08:55 against api.moonshot.ai/v1. Survey: kimi-k3-platform-survey-2026-07-18.md §6.

## P1 — Live models (0.67s)

kimi-k2.6, kimi-k2.7-code, kimi-k2.7-code-highspeed, kimi-k3
(k2.5 and moonshot-v1 absent for this new account, matching the sunset notes.)

## P4 — Balance endpoint (0.35s)

available_balance **105** = cash 100 + voucher **5** (USD). Daniel's $100 landed plus a $5
voucher. Endpoint healthy, trivially cheap to poll.
FINDING: balance showed **zero delta** across two completions (~$0.01 real cost) — it is a
COARSE/lazily-updated ground truth. Spend-ledger design: per-turn usage parsing is the fine
meter; balance reconciles periodically; never rely on balance for per-turn accounting.

## P2 — Usage anatomy (cold call, 2,685-token prompt, 4.48s)

```json
{"prompt_tokens": 2685, "completion_tokens": 37, "total_tokens": 2722,
 "completion_tokens_details": {"reasoning_tokens": 19}}
```
content: "PROBE_ONE_OK" (exact-match instruction FOLLOWED); finish_reason stop; model echo kimi-k3.
FINDINGS:
- **Thinking bills as output**: reasoning_tokens (19) sit INSIDE completion_tokens (37). At
  $15/M out, thinking is the cost term to watch — BUT K3 right-sizes: a trivial ask spent only
  19-28 reasoning tokens despite reasoning_effort=max. Not a flat tax.
- reasoning_content arrives as a separate message field (79 chars here); parse content only.

## P3-lite — Cache-hit probe (same 2,685-token prefix, new tail, 18.01s)

```json
{"prompt_tokens": 2685, "completion_tokens": 46, "total_tokens": 2731,
 "completion_tokens_details": {"reasoning_tokens": 28}}
```
content: "PROBE_TWO_OK" (exact again).
FINDING — **UNRESOLVED**: no cached-token field appeared on call 2 (no prompt_tokens_details,
no deepseek-style hit/miss split); prompt_tokens identical both calls; latency went UP (18s vs
4.5s — server variance, not a cache signal). Either 2.7k is under a hit threshold, the cache
needs longer to materialize, or hits are billing-side-only (invisible in usage). The $0 balance
delta is too coarse to disambiguate.
=> P3-FULL follow-up during the soak: 10k+ prefix, spaced repeats (1min/5min/1h), cross-check
the platform billing dashboard. Runner design guidance (byte-stable prefix, append-only) stands
regardless — it is free to do and the docs promise 90% on hits.

## Latency note

Trivial completions ran 4.5s and 18s (thinking-mode variance). Fence-voice turns will run tens
of seconds to minutes — comfortably inside runner REPLY_TIMEOUT (600s scaled).

## P7 addendum — Anthropic door probed (post-Daniel-go, same day)

- `/anthropic/v1/messages` accepts BOTH `x-api-key` and `Bearer` (HTTP 200 each).
- **USAGE FIELD NAMES REVEALED on this door**: `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `cached_tokens`, `output_tokens_details.thinking_tokens`,
  plus OpenAI-style mirrors (`prompt_tokens`/`completion_tokens`/`total_tokens`). The spend
  ledger has concrete fields for the anthropic door; the /v1 door's hit-field still rides P3-FULL.
- **Cache hits ARE reported on this door** — both probe calls showed the full 90-token prompt
  as `cache_read_input_tokens: 90` / `input_tokens: 0`. Honest caveat: the FIRST call already
  reported the hit (possible priming by an earlier 401'd CLI preflight, or cross-request dedup
  at tiny sizes) — P3-FULL (50k prefix, spaced, dashboard cross-check) disambiguates.
- **LESSON (fence-call design)**: `max_tokens: 32` → thinking consumed the entire budget →
  `content` came back EMPTY with `stop_reason: max_tokens`. Always leave thinking headroom;
  schema/fence calls set generous max_completion_tokens. Floors per deepseek (post-launch
  note, T018 precedent — "a reasoning model with a tight cap delivers a promise instead of an
  answer"): >=8000 for fence turns, >=32000 for megareads. Spend-ledger schema strategy: expect
  the anthropic-door field names, fall back to conservative billing when absent.
- **Harness smoke**: logged-in CLI 401'd (stored claude.ai OAuth outranks env auth and fails
  against Moonshot — loud, not silent). FIX: `CLAUDE_CONFIG_DIR=E:\AI-Setup\.kimi-claude-home`
  (fresh config home, no stored OAuth, env key becomes sole credential; project-level akashic
  hooks still fire from .claude/ in the repo). Result: `claude -p` returned KIMI_ENDPOINT_OK
  through the real harness. Launcher updated; .kimi-claude-home gitignored.

## First behavioral datapoint (for the walk rubric, R1 directive fidelity)

Kimi's first two utterances on our substrate followed an exact-output instruction perfectly,
with tight, obedient reasoning traces ("We need answer exactly PROBE_ONE_OK. Need not add
anything."). One swallow does not make a summer; noted as datapoint zero.
