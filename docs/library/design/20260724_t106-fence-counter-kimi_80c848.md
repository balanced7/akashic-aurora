---
akashic_id: art_20260724_t106-fence-counter-kimi_80c848
akashic_sha: eea71e39729f
schema_version: 1
status: current
type: design
arc: T106
date: 2026-07-24
title: t106-fence-counter-kimi
gist: "kimi T106 fence counter (recovered from broadcast lane): stranger-test verdicts on lease-identity binding + A1 cancellation guarantee"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [bus, audit, substrate]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_t106-build-specs-o15-seat-lease-a1-await_6fc93b
    rel: discusses
created: "2026-07-24T17:18:20"
updated: "2026-07-24T17:18:20"
---
<!-- GENERATED PROJECTION of art_20260724_t106-fence-counter-kimi_80c848 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t106-fence-counter-kimi

ATOM EVOLUTION CONTRACT ROUND — KIMI INDEPENDENT POSITION

Filed: art_20260724_atom-evolution-contract-round-kimi-position_175bbe
Projection: docs/library/design/20260724_atom-evolution-contract-round-kimi-position_175bbe.md

CALIBRATED ANSWER: rebuild() breaks first.

Not get(), not the projection renderer, not gen_library — rebuild(). The JSONL replay path at core/library/atoms.py:377-403 has NO schema-version gate. get() refuses loud (line 214), but rebuild() reads raw JSON from disk and pushes it directly into the store. A v2 atom in the JSONL → _index() accesses header fields that may not exist in v2 → KeyError or phantom index entries → the entire store is poisoned before any consumer reads a single atom.

The fix is surgical: rebuild() needs the same v > SCHEMA_KNOWN_MAX check that get() has, BEFORE store write.

Three-stage drill catches it:
A. Fixture replay (unit): one v2 line → rebuild → assert clean skip or loud refuse
B. Census regression (integration): same fixture → gen_library --from-store --verify → completes without crash
C. Full-replay gate (e2e): 3 v1 + 1 v2 → rebuild → all v1 queryable, v2 parked

All three WOULD FAIL today.

Top-5 laws + kill-list are in the atom. Consumer blast-radius table names every reader and its unshimmed failure mode.

This is the full answer to Daniel's calibrated question: "which consumer breaks FIRST under an unshimmed v2, and what drill catches it before it ships?"
