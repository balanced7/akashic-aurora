---
akashic_id: art_20260724_atom-design-reconciled-v1-1_fd2275
akashic_sha: e2aee290823c
status: current
type: design
arc: atom-design
date: 2026-07-24
title: atom-design-reconciled-v1-1
gist: "GATED full-fleet convergence: schema_version, body_type+source stamp, segments-at-pane-trigger, inverse indexes w/ lie-detector, resolution laws, diff+export doors, cuts, arc law v1.3"
tenant: solo
visibility: fleet
seats: [claude, deepseek, kimi]
category: [substrate, library, coordination]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_atom-design-fleet-exploration_419165
    rel: discusses
  - target: art_20260724_atom-design-round2-reconciliation-counte_9ebbcf
    rel: discusses
  - target: art_20260724_atom-design-round2-counter-deepseek_c44321
    rel: discusses
created: "2026-07-24T00:56:38"
updated: "2026-07-24T00:56:38"
---
<!-- GENERATED PROJECTION of art_20260724_atom-design-reconciled-v1-1_fd2275 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-design-reconciled-v1-1

RECONCILED ATOM DESIGN v1.1 -- the full-fleet convergence (GATED: nothing builds without Daniel's word).

Round record: Daniel's charter (verbatim in the brief atom) -> independent openings (deepseek builder / kimi audit, no coordination) -> claude reconciliation + counters -> both seats' round-2 counters. Every position below is a CONVERGED position -- affirmed by all three voices, with concessions recorded on both sides. Daniel's axes all answered: parse/compare, linking, multi-datatype, ingest cost, exportability.

## THE PACKAGE (9 items, build-ready order)

1. **schema_version: 1** on every atom; readers assert known-version and refuse loud on newer (fail-closed). The lie-killer (kimi: "the schema's first lie is silent format drift"); the foundation the multi-datatype change rides. Migration ~zero (658 atoms stamp at rebuild).

2. **body_type flag (v1 of the multi-datatype axis)** -- enum LOCKED to the future segment-kind roster: markdown | code | json | tabular | transcript (T034-capped). PLUS kimi's round-2 hardening: **body_type_source: flag|auto|unstated** stamps detection confidence (a wrong auto-stamp must be visible -- the category_sources gem one field over). Auto-detect at enrichment via deepseek's regexes; wrong stamps are post-hoc lint fixes, never write-time blocks. Migration zero (default markdown).

3. **segments[] = schema_version 2, at a NAMED TRIGGER: the Library pane reader build** (the first consumer that renders code-as-code, table-as-table). All three voices affirmed the staging AND the trigger; deepseek's boundary holds: recall chunking is orthogonal (chunk-by-heading over the joined body serves recall; do not couple). At v2: body becomes DERIVED (join of segment texts -- never dual truth), body_sha over the canonical concatenation so gen_library --verify survives unchanged, per-kind metadata (lang, schema) rides the SEGMENT never the atom, kinds = the same 5-roster. Lands via the migrate_schema door.

4. **Inverse indexes**: citations_in (cited-by sets) + supersedes-target, maintained at mint, backlinks O(corpus)->O(1). SHIPS WITH its lie-detector (kimi's audit law): an A2 row cross-reads index-vs-citations_out, and rebuild() recomputes indexes from citation truth.

5. **Resolution laws (linking that pays rent, zero new rel types)**: (a) resolve-forward -- readers/tools follow the supersession chain to the current head by default; never read a fossil thinking it is live; the receipt stays one hop away. (b) backlinks AGGREGATE across a lineage. (c) related = bounded 1-hop union (citations_out + backlinks + chain) PLUS deepseek's thematic-related: shared category AND bidirectional discusses -> related in the graph lens (computed at query time, zero storage -- the super-wiki's thematic hop derived from existing fields). (d) citation cycles = an A2 photograph, never a refusal.

6. **doc diff verb**: unified body diff + header-field changes reported separately + supersession auto-resolve (doc diff <id> compares to successor) + --json stats. Read-side, ~40 lines.

7. **doc export door**: export-as-projection -- atom JSON + projection markdown + manifest.json (schema_version, field glossary, citation closure bounded by --depth). Formats: jsonl, zip-html. The atom stays truth; the bundle is a render. Read-side, ~50-70 lines.

8. **The cuts (converged)**: tenant DEMOTED to door-default (unenforced, S-1b re-adds at its wave). cites MERGED into discusses -- REL_ROSTER becomes derives-from | contradicts | supports | discusses (one rewrite pass). discusses STAYS as the door's cheap default (a strong-claim-only door would thin the graph at birth); the A2 discusses-share metric is the lie-detector for dilution (kimi's withdrawal + metric = stronger than either opening). visibility KEPT -- kimi conceded with evidence (enforcement verified at gen_library + enrich_corpus, P3b redaction). Provenance block KEPT (conversation door live + authority law rides it; deepseek conceded -- revisit with a month of usage). category_sources KEPT until A2's low-confidence lint ships.

9. **LIBRARY.md v1.3 amendment (the arc law)**: an artifact belongs to exactly ZERO or ONE arc. Arcless is legal for evergreens (LEXICON, VOICE, CONDUCT -- they ARE the constitution campaigns operate under; forcing an arc manufactures fakes). Cross-arc relevance rides a SPECIFIC typed edge (derives-from or discusses -- named, never vague), NEVER two arc values (would fork the index). A2's arcless census lints arcless NON-evergreens only.

## DEFERRED WITH NAMED TRIGGERS (not tonight, not silently dropped)
- segments[] v2 -> the pane reader build (item 3).
- JSONL sharding / rebuild windowing -> corpus growth makes rebuild slow (A2 photographs it).
- part-of composition rel -> the first real composite that derives-from cannot serve.
- projection body-hand-edit detection -> A2's repair pass (frontmatter-sha cross-read ships tonight-era; body re-derivation is its successor).
- body_norm_sha + supersession diff stats (deepseek #5) -> folds into the diff verb's --json if wanted; not a stored field until a consumer needs it.

## COST HONESTY
Items 1, 2, 8, 9: field additions + roster edits + one LIBRARY.md amendment -- small, largely rebuild-stamped. Item 4: index backfill pass. Items 5-7: read-side verbs (~150 lines total). Nothing rewrites the JSONL history; nothing moves a projection; --verify stays green through all of it.

## ATTRIBUTION (proportionality law)
Daniel's charter opened the round and every axis is his. Openings: deepseek (builder), kimi (audit). Reconciliation + refusals: claude. Concessions that made it stronger: deepseek (provenance, trigger boundary), kimi (visibility-with-evidence, discusses-metric). The hardening stamp (body_type_source): kimi. The thematic-related view: deepseek.
