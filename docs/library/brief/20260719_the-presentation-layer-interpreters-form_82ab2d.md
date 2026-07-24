---
akashic_id: art_20260719_the-presentation-layer-interpreters-form_82ab2d
akashic_sha: e2a2c1cb46dd
status: draft
type: brief
date: 2026-07-19
title: "The Presentation Layer — Interpreters, Formatters, and TOON (Charter + claude opening position)"
gist: "# The Presentation Layer — Interpreters, Formatters, and TOON (Charter + claude opening position) **Date:** 2026-07-19 · **Directed by:** Da"
tenant: solo
visibility: fleet
seats: []
category: [substrate, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T10:03:25"
updated: "2026-07-19T10:03:25"
---
<!-- GENERATED PROJECTION of art_20260719_the-presentation-layer-interpreters-form_82ab2d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# The Presentation Layer — Interpreters, Formatters, and TOON (Charter + claude opening position)

# The Presentation Layer — Interpreters, Formatters, and TOON (Charter + claude opening position)

**Date:** 2026-07-19 · **Directed by:** Daniel (verbatim, mid-turn): *"analyze whether interpreters and formatters would be useful in our system depending on the communication type and payload, to shift the burden of dealing with this away from the llm and into the substrate"* + *"I just learned about TOON (Token Optimized Object Notation). I have a suspicion that this would be useful for us, can you and the others investigate."*
**Fence:** claude opening (this doc) → deepseek counter (he READS more machine payloads than anyone — runner-side felt data is unique) → kimi half at next wake (he personally paid the chunk-protocol tax) → reconciliation → Daniel's gate. No build before the gate.

## The frame (one sentence)

We built the transport layers of the internal internet — lanes (T039), packet spec + MTU + frag (T040/T043), routing (packet_route) — and never built the **presentation layer**: today every LLM seat hand-parses and hand-formats whatever crosses its boundary, which is exactly the burden Daniel wants pushed into the substrate.

## Two directions, one layer

**Formatters (substrate → LLM):** render stored structure in the cheapest encoding the consumer comprehends, negotiated per payload shape × consumer. Uniform tables → TOON/CSV-class; ragged/nested → compact JSON; narrative → prose (our boot already does prose well — it's the JSON surfaces that are fat).

**Interpreters (LLM → substrate):** tolerant intake — the substrate parses, validates, reassembles, and confesses; agents stop hand-assembling protocol envelopes. **We have been building this ad hoc at every pain point without naming it:** W06 stdin fallthrough, C3-1 --text-file, T064 _intake spill+confession (RB-5 class), kimi's manual "chunk n/N" reassembly protocol, len/sha validation at consume (T043). Daniel's directive names the layer; the census below says it's load-bearing.

## TOON — verified state (2026-07-19)

- Spec + SDK: toonformat.dev, github.com/toon-format/toon + toon-format/spec (TypeScript reference; Python ports exist — maturity to verify in S1). InfoQ coverage 2025-11.
- **arXiv 2603.03306 (Feb 2026), plain + constrained decoding benchmark:** TOON ~76.4% retrieval accuracy vs JSON 75.0% at **~40% fewer tokens** (4 models); 99.4% @ 46% fewer on GPT-5 Nano; realistic corpora: 61% (orders), 55% (tickets), 64% (catalog) savings. **Caveats that shape our design:** (1) wins concentrate on UNIFORM arrays — ragged/nested data can be no better than compact JSON; (2) "prompt tax" of format instructions eats savings on small payloads; (3) **generation: plain JSON still wins** — models write JSON more reliably than TOON.
- **Design consequence: TOON is an INPUT-side formatter only.** LLM output stays JSON/prose with tolerant interpreters. This asymmetry IS the formatter/interpreter split.

## Census — where structure crosses an LLM boundary today (measured this morning)

| Surface | Weight | Shape | Candidate |
|---|---|---|---|
| `notes --json` | **229,027 chars (~57k tok)** | ragged (long prose bodies + uniform metadata) | split: metadata table → TOON; bodies → on-demand drill (W01's wish) |
| `task list` render | 35,933 chars (~9k tok), re-rendered per boot/wake | semi-uniform rows + prose titles | TOON/table candidate; better: DELTA not dump (see S2) |
| wake payload | fires the FULL ledger render on every wake (today's receipt: watcher output = entire 36k ledger + detected mail) | re-render | **delta-not-dump composes T052** |
| `events --limit 20` | 3.3k chars | uniform | TOON natural fit, low stakes |
| `--json` flags in agent_cli | 56 surfaces | mixed | negotiate per shape, not per verb |
| bus message bodies | 4000-clip door; **deepseek's D2/D3 counter arrived clipped MID-WORD by the exact door his verdict raises to 8000 (same day)** | prose + ad-hoc structure | interpreters: substrate chunk/reassembly, envelope validation |

Boot itself is already prose-shaped and hand-tuned — the fat sits in the JSON drill surfaces and re-rendered state, not the narrative.

## Honest ordering: selection beats encoding

T071-R1 (relevance budget, ~2k cap) cuts tokens by SELECTING less; formatters cut by ENCODING what's selected. Selection is the bigger lever on boot; encoding is the lever on drill surfaces (`notes --json`, events, ledger) and machine-to-machine payloads. They compose; neither replaces the other. (Frugality directive: measure first — S0 below.)

## Proposed slices (gated, in order)

- **S0 Measure:** bytes-per-surface-per-day heat map from turn_metrics + the R5/T056 cost-telemetry seam. One week of truth before any encoder ships. Bars: top-5 hot surfaces ranked with real weights.
- **S1 TOON-render behind a flag** for the 2-3 hottest UNIFORM surfaces (events, funnel, ledger rows; notes METADATA only). **N-version comprehension drill:** the same payload rendered TOON vs compact-JSON, read blind by every fleet model (fable/opus/deepseek/kimi), probe questions, accuracy + token cost recorded. Ship only where parity holds. (The arXiv numbers are other people's corpora; ours rules.)
- **S2 Delta-not-dump:** wake/boot payloads render what MOVED (T052 delta door exists) instead of re-rendering full state. Possibly the biggest win, zero new formats.
- **S3 Interpreters formalized:** substrate-side chunk/reassembly (kills the manual n/N protocol), envelope validation with errors-that-teach, tolerant intake normalization at every door (RB-5 confession lineage → one named layer in packet_spec).
- **S4 Content negotiation at the door:** consumer profile (model class, harness tier, UI, script) picks the encoding; strangler-fig migration; **format-roster capped** with a why-not-an-existing-format ritual (T034/T039 Goodhart guard — no zoo).

## Evaluation bars (all slices)

MDL-under-faithfulness (codex law governs renders too) · measured token delta on hot surfaces, not benchmark transfer · comprehension parity per model before default-on · LLM OUTPUT stays JSON/prose (arXiv generation finding) · zero new primitives (rides packet_spec, doors, delta, telemetry).

## Risks

Format zoo (capped roster) · weaker-model misreads (N-version drill gates) · our-corpus-isn't-their-benchmark (ragged notes ≠ uniform orders — hence metadata/body split) · premature encoding before selection (S0/T071-R1 first) · spec churn in a young format (pin a spec version; vendor the encoder).
