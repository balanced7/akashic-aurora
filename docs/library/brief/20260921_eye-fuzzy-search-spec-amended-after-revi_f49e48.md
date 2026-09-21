---
akashic_id: art_20260921_eye-fuzzy-search-spec-amended-after-revi_f49e48
akashic_sha: e33f2a9a74b3
schema_version: 1
status: current
type: brief
date: 2026-09-21
title: "eye fuzzy search — spec, amended after review"
gist: "# eye fuzzy search — spec, amended after review Status: **AMENDED 2026-09-21** after review by Navi (kimi) and Heimdall (deepseek). Vandor's"
visibility: fleet
body_type: markdown
seats: [dsh_agent]
category: [security, method, audit]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-21T09:31:46"
updated: "2026-09-21T09:31:46"
---
<!-- GENERATED PROJECTION of art_20260921_eye-fuzzy-search-spec-amended-after-revi_f49e48 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# eye fuzzy search — spec, amended after review

# eye fuzzy search — spec, amended after review

Status: **AMENDED 2026-09-21** after review by Navi (kimi) and Heimdall (deepseek). Vandor's
fence-worthiness answer still pending (read-only, Monday fine). Author: Rill (dsh_agent).

## The problem

"Fuzzy" is two different problems, and conflating them was the first error.

1. **Lexical fuzziness** — typo and stem drift ("absence renders" vs "absence rendering"). Cheap,
   deterministic, mostly solved. Not the gap.
2. **Conceptual fuzziness** — the real gap. We remember the *idea*, not the wording. The corpus
   stores one concept under many phrasings: "absence renders as normal" ≈ "default masquerading as
   fill" ≈ "a pass that should have been a red". Literal search cannot bridge that.

The operator's words are the requirement: *"we forget to search for concepts with eye in a fuzzy
way."* That is "a concept handhold at the moment of asking", not "better typo tolerance".

## Review outcome — measured, not asserted

- **KILL CLAUSE CONFIRMED (my own hands):** `find_related` drew **0 edges** between two phrasings of
  the SAME concept ("absence renders as normal" vs "default masquerading as fill") and **1 edge** for
  a lexical near-duplicate. `related_to` is a lexical-redundancy detector; it CANNOT reach concepts.
  Layer C as first written rested on a false premise, and it is struck below.
- **Navi:** Layer B read redundancy as identity. Co-occurrence can *nominate* an alias, never
  *assert* one; edges are one-directional and capped at 5. The asymmetry that matters: a MISS costs
  effort, a FALSE BIND costs truth (a wrong-concept hit is *quotable* on a citation surface).
- **Heimdall:** there is no concept graph over lessons today. `related_to` = lexical redundancy
  (~180 of 831 lessons edged, ~78% orphans). The *connectome* (utterance lineage) is the real
  concept-relevant substrate, but its idea-lineage half (the four hooks) is UNBUILT. The score must
  be a ranked failure taxonomy, not recall@k + noise.

## What we would build on (corrected)

- `eye find` (facet AND) + `eye freq` (hand-OR'd families — the caller must already know the
  phrasings, which is the failure being fixed).
- `related_to` edges: **lexical redundancy ONLY — not a concept graph** (the killed premise).
- `knowledge_map` walks those edges; useful for near-duplicates, not for concept reach.
- The connectome (`core/eye/connectome.py`): utterance lineage, rich, but a different node type, and
  its idea-lineage edges are unbuilt.

## Proposal (corrected): three layers, one struck

**Layer A — normalize + token overlap (deterministic).** A `--fuzzy` pass over `find`/`freq`:
lowercase, strip punctuation, stem, match on token overlap instead of literal substrings. Recovers
the lexical half; every hit is explainable ("matched on these tokens"). The first build.

**Layer B — co-occurrence NOMINATES, never asserts.** Aliases derived from co-occurrence are
*suggestions*, labeled "co-occurring concept, relation unconfirmed" — never "alias", which implies
identity. A separate confirmation gate (same `root_cause`/`category`, or a journalled idea edge)
promotes a suggestion to a retrievable alias. Until a confirmation gate exists, Layer B ships in the
Layer D hedging posture: "maybe related", never authoritative.

**Layer C — STRUCK.** It rested on a graph that does not exist for concepts. Re-scoped as FUTURE
WORK gated on either (a) building the four idea-lineage hooks on the connectome, or (b) walking the
connectome's utterance lineage directly. Not part of the first build.

**Layer D — semantic embeddings, HELD** (unchanged: it is a lens, and it stales).

## Honesty rules (amended)

- **R1 — provenance labels, with the axis that matters.** Every hit is labeled by (a) how it was
  reached (`literal | stem | co-occurrence-suggested | idea-edge | semantic`) AND (b) whether that
  reach step *asserts identity* or *suggests adjacency*. The word "alias" is retired as a label —
  it overclaims what co-occurrence can support.
- **R2 — zero is not a conclusive no** (unchanged). On empty literal results, offer the neighborhood
  rather than dead-ending.

## The score (amended)

Ranked failure taxonomy, per calibration pair:
1. **Silent wrong-concept hit** — a fuzzy hit that surfaces the wrong concept and looks citable. The
   only real failure. Target: **rate = zero**.
2. Labeled wrong hit — recoverable, because the label lets you refuse.
3. Miss — an honest zero, and R2 makes it visible.

A labeled wrong-neighborhood is NOT a failure to count. The calibration set must include an
orphan-concept pair and a cross-domain pair on purpose, or the number measures only the easy
quadrant.

## Calibration set (amended — MISSES, not known-wording)

- "absence renders as normal" → `default_masquerading_as_fill` (+ the absence-as-normal lesson).
- "the connection that should exist doesn't because the carrier has no text" →
  `a_causal_chain_breaks_at_the_records_that_carry_no_text` (Navi's real miss).
- "a mistake repeats with no new lesson" → the `REPEAT_INDEX` / `record_repeat` machinery (Navi's
  real miss).
- "a served blob is not a fetched blob" → `a_served_blob_is_not_a_fetched_blob`.
- "wake lane divergence" → the wake-lane family — and the silent-wrong-hit kill case: stemming
  "wake" surfaces a neighborhood of *distinct* concepts that all share the token.
- PLUS one orphan-concept pair and one cross-domain pair, on purpose.

## Non-goals and risks

- Not a search-engine rewrite. `--fuzzy` is opt-in first, default only when the calibration earns it.
- Opacity is the failure to avoid: Layer A explains, Layer B hedges, Layer D hedges. Nothing fuzzy is
  authoritative without a label.
- Layer C is OUT of the first build; the four idea-lineage hooks are a substrate build, priced
  separately.
- The citation resolver's exactness is untouched (`eye get` still resolves addresses exactly and
  refuses honestly on ambiguity).

## Open questions

- [Vandor] fence-worthiness and R2 vs the `eye get` exactness contract — still pending.
- Navi and Heimdall answered; their findings are integrated above.

— Rill
