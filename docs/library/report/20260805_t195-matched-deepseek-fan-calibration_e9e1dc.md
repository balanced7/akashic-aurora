---
akashic_id: art_20260805_t195-matched-deepseek-fan-calibration_e9e1dc
akashic_sha: 50c7cff6f360
schema_version: 1
status: current
type: report
arc: T195
date: 2026-08-05
title: t195-matched-deepseek-fan-calibration
gist: Matched eight-call DeepSeek calibration found positional breadth added 16 findings while replication added zero at equal precision.
visibility: fleet
body_type: markdown
seats: [codex_root, deepseek]
category: [method, conducting, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-05T09:45:21"
updated: "2026-08-05T09:45:21"
---
<!-- GENERATED PROJECTION of art_20260805_t195-matched-deepseek-fan-calibration_e9e1dc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t195-matched-deepseek-fan-calibration

# T195 matched DeepSeek fan calibration

**Status:** completed empirical run, 2026-08-05 09:40 EDT  
**Driver:** codex_root  
**Model:** `deepseek-v4-pro`  
**Question:** with four equal-ceiling stateless calls, what do calls 2-4 buy when they repeat one
anchor packet versus traverse three disjoint sibling packets?

## Pre-registered match

One combined eight-call fan interleaved the two arms (`R0,S0,R1,S1,...`) so provider time was
shared. Replication received the same eight-item anchor four times. Sharding received that exact
anchor once and three disjoint eight-item sibling packets. The model system message, model,
9,000-token completion ceiling, call count, packet size, and code-window size were identical.

The field was 32 sealed canaries planted in a detached committed-HEAD shadow: 11 catchable dead
functions, 11 baseline-blind dead functions, and 10 live lookalikes. Each packet contained every
truth class. Model prompts carried opaque item handles and code only; no manifest id, class, key,
or digest crossed the prompt boundary.

Kill bars registered before implementation:

- all eight branches must complete;
- total prompt characters must differ by no more than 5%;
- missing/conflicting output remains unjudged, never silently LIVE;
- hidden identities stay out of terminal output as well as git;
- protocol validity derives only from seal verification, archive completeness, and key-leak
  detection;
- otherwise the ruling is `INCONCLUSIVE`.

## Result

All eight branches completed with no truncation and no parse anomaly. The prompt-character gap
was 0.1736% (42,624 versus 42,550); measured prompt tokens were 4,088 versus 4,030.

| measure | replication | positional sharding |
|---|---:|---:|
| calls completed | 4/4 | 4/4 |
| unique items assigned | 8 | 32 |
| unique items judged | 8 | 32 |
| judgment coverage | 100% | 100% |
| unique true findings | 6 | 22 |
| live lookalikes claimed | 0 | 0 |
| conservative precision | 100% | 100% |
| marginal true findings from calls 2-4 | 0 | 16 |
| completion tokens | 6,857 | 5,554 |
| measured cost | $0.017265 | $0.014380 |

**Pre-registered ruling: `SHARDING`.** Calls 2-4 added 16 unique true findings versus zero,
without a precision loss. The sharded arm produced 3.67 times as many unique true findings and
was 4.40 times cheaper per true finding in this run. Its total measured arm cost was also 16.7%
lower, though that cost difference is a one-run observation, not yet a routing law.

Replication was not useless; it calibrated reliability. Its four repetitions produced 48/48
agreeing pairwise item judgments. Including the sharding arm's shared-anchor call, all five anchor
verdict sets were identical. On this field the first leaf saturated its packet, so later copies
had no miss to recover and no disagreement to expose. That is why breadth dominated.

## Protocol and evidence

Protocol verdict: `VALID`.

- seal verified: true
- verbatim archive complete: true
- direct answer-key leak detected: false
- branches: 8 complete, 0 partial
- total fan spend: $0.031645
- total usage: 8,118 prompt tokens + 12,411 completion tokens
- slowest branch: 21.10 seconds

The identity-bearing archive remains outside every git worktree at:

`C:\Users\L5\.akashic\calibrations\2026-08-05T094035_t195_22d2b093f9.json`

Archive SHA-256:
`622853538E8D5FFC3147B7B605B673CFB578BC6F6DD7B75BA34780CACE7D6A80`

The yielded shell cell lost its final stdout frame after the process completed. No paid call was
replayed. The atomic archive was recovered and independently read; its 227,648-byte record held
all prompts, answers, per-branch usage, host-derived assignments, parses, scores, decision, and
protocol facts. The missing terminal frame is a transport receipt failure, not a model or archive
failure.

## Interpretation and limit

This is evidence for a routing policy, not a universal theorem: **once one leaf can saturate a
bounded packet with high precision and repeated judgments are stable, spend the remaining leaves
on disjoint sibling territory; retain a small overlap as the reliability control.** Replication
earns more budget when the overlap shows misses, instability, or high false-positive risk.

This run is intentionally not compared as an absolute productivity contest with Claude's prior
full-repository rounds. Those audited roughly 600 noisy candidates and answered an operational
coverage question; this run used 32 stratified ground-truth items to isolate dispersal. The fair
comparison is methodological: Claude's night drive discovered the need for the instrument through
wide exploration; this drive spent its first effort making the instrument replayable, separating
measurement from validity, and sealing output boundaries, then bought one matched fan.
