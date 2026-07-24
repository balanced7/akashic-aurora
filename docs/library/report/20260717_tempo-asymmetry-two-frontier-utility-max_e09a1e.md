---
akashic_id: art_20260717_tempo-asymmetry-two-frontier-utility-max_e09a1e
akashic_sha: 08b957bd1fae
status: draft
type: report
date: 2026-07-17
title: "Tempo Asymmetry: Two-Frontier Utility Maximization — claude half (2026-07-17)"
gist: "cheap deepseek tokens (only used $10 of $100)... deepseek is faster... different models work at and respond at different speeds, we need our"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-17T00:20:03"
updated: "2026-07-17T00:20:03"
---
<!-- GENERATED PROJECTION of art_20260717_tempo-asymmetry-two-frontier-utility-max_e09a1e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Tempo Asymmetry: Two-Frontier Utility Maximization — claude half (2026-07-17)

cheap deepseek tokens (only used $10 of $100)... deepseek is faster... different models work at and
respond at different speeds, we need our framework to be wise to that and optimize the possibilities
to the fullest." deepseek-review files his half blind to this one; reconcile after.

## The asymmetry, stated as resources

| Seat | Cost | Tempo | Scarce resource | Abundant resource |
|---|---|---|---|---|
| claude (Fable) | plan-capped | slow (deep turns) | context + plan tokens | judgment, final authority |
| deepseek v4-pro | $2.19/$8.78 per M, $90 headroom | FAST (2-4s hops) | depth ceiling | iterations, wall-clock, tokens |
| sol (gpt-5.6-sol) | $5/$30 per M, preview | dialable (effort none→xhigh) | budget | ceiling on demand |

The design error to avoid: treating the seats as interchangeable workers with different price tags.
They are different RESOURCE PROFILES; the framework should route work by profile.

## The six patterns

1. PRE-CHEW (breadth→depth pipeline). The fast seat bulk-reads and emits structured distillates;
   the deep seat consumes briefs, not raw files. Every deepseek dollar spent this way BUYS claude
   plan-tokens. Metric: claude context consumed per decision, before/after.
2. SPECULATIVE DRAFTING. Fast seat authors first drafts (fragments, scaffolds, spec extractions,
   N variants when a rubric exists); deep seat adjudicates + merges. Authorship is cheap where
   review is the real value-add.
3. TRIPWIRE FENCE (standing, not discrete). Post-land, the fast seat re-derives and attacks every
   artifact within minutes — silent when clean, fidelity-ladder escalation (INFORM→STEER→INTERRUPT)
   on findings. The deep seat stops WAITING at review gates; reviews chase the work.
4. TEMPO ROUTING VIA expect_reply_within. The bus already stamps reply deadlines on asks (RB-29).
   Use the deadline as the ROUTER: seconds-profile → deepseek; minutes/depth-profile → sol high/xhigh
   or claude. A tempo mismatch (deep ask, tight deadline) should refuse loudly, not silently degrade.
5. SATURATION RULE. The slow seat never blocks on the fast one; the fast one never idles while the
   slow one thinks. Operationally: every claude turn ENDS by teeing deepseek's next batch (CPU
   keeping the DMA queue full). Candidate method-baseline item — habits belong in the contract.
6. ECONOMICS GAUGE. Token journal (T078) + per-seat $ + the exchange rate: deepseek-$ spent per
   claude-token saved. Gauge inversion (2026-07-15 theme): visible budgets change behavior.

## The kept constraint

Speed never gets commit authority. Fast seat drafts and attacks; deep seats adjudicate; claude stays
sole committer (two-model overnight finding). Velocity that skips adjudication is how
plausible-but-wrong ships.

## Live instantiation (T090 sol runner, tonight)

- deepseek-review (fast lane, parallel): (a) runner-loop SPEC extracted from his own runner —
  the consume→respond→reply→commit pipeline with RB-25/26/29, T045 lanes, T066 reply path as a
  verification CHECKLIST; (b) sol-named draft fragments (consume skeleton, dedup pair, trim) to
  scratch/; (c) his blind half of THIS question.
- claude (deep lane, parallel): SolAgent (Responses-native tool loop) in sol_chat.py — novel logic,
  no precedent to pre-chew; then merge his fragments against his checklist; pins; commit.
- Expected: his three deliverables land before my SolAgent is done — the pipeline adds ZERO wall-clock
  to the launch. That is the pattern working, measured on its first outing.

## Open questions for the reconcile

1. Does the tripwire fence need a rate limiter so escalations stay rare enough to stay loud?
2. Should tempo routing live in the bus (meta field) or in the ask conventions (docs)?
3. Sol's effort ladder as an in-seat tempo dial: who chooses effort — the sender (deadline implies
   effort) or the seat (reads its own queue depth)?
4. What is the failure mode of pre-chew — distillate drift (fast seat's summary quietly wrong)?
   Counter: spot-check ratio (deep seat re-reads N% of raw sources, receipts logged).
