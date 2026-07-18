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

## First behavioral datapoint (for the walk rubric, R1 directive fidelity)

Kimi's first two utterances on our substrate followed an exact-output instruction perfectly,
with tight, obedient reasoning traces ("We need answer exactly PROBE_ONE_OK. Need not add
anything."). One swallow does not make a summer; noted as datapoint zero.
