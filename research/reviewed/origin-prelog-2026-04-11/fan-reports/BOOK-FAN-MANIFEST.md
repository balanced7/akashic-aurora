# Book fan — coverage manifest (CORRECTED 2026-08-17)

**This file previously documented a 26-shard geometry that the book did not use.** That was the
pre-filter auto-slice, in which twelve shards were a single agent-authored dispatch brief each
(the largest a lone 711,573-char item). Those were classified out before the fan ran. The book
was written from the geometry below and from nothing else.

Correction found by codex on an independent read of book-vs-manifest, filed as
`book_evidence_geometry_must_match_final_corpus`. A synthesis whose coverage labels cannot be
reconstructed from its own manifest is not auditable, whatever the prose says.

## Corpus actually read

- 4,547 operator utterances, 3,178,225 chars, 2026-04-11 → 2026-08-16
- EXCLUDED and named: 32 agent-authored dispatch briefs carrying 3,218,153 chars (50.3% of the
  raw operator plane). Not operator speech; see `dispatch_briefs_are_recorded_as_operator_speech`.
- Auto-sliced to a 250,000-char budget. **Complete coverage of the filtered spine; zero drops.**

## Partition shards (13 sent, 12 landed, 1 starved)

- shard 00: 2026-04-11 .. 2026-04-18 — 558 utterances, 251,591 prompt chars
- shard 01: 2026-04-18 .. 2026-07-03 — 333 utterances, 247,794 prompt chars
- shard 02: 2026-07-03 .. 2026-07-03 — 106 utterances, 250,845 prompt chars
- shard 03: 2026-07-03 .. 2026-07-11 — 174 utterances, 247,948 prompt chars
- shard 04: 2026-07-11 .. 2026-07-19 — 551 utterances, 251,248 prompt chars
- shard 05: 2026-07-19 .. 2026-07-21 — 218 utterances, 250,012 prompt chars
- shard 06: 2026-07-21 .. 2026-07-30 — 587 utterances, 240,820 prompt chars
- shard 07: 2026-07-30 .. 2026-08-01 — 285 utterances, 251,230 prompt chars
- shard 08: 2026-08-01 .. 2026-08-04 — 382 utterances, 251,443 prompt chars
- shard 09: 2026-08-04 .. 2026-08-05 — 118 utterances, 244,810 prompt chars
- shard 10: 2026-08-05 .. 2026-08-11 — 573 utterances, 251,233 prompt chars
- shard 11: 2026-08-11 .. 2026-08-12 — 224 utterances, 248,864 prompt chars
- shard 12: 2026-08-12 .. 2026-08-16 — 438 utterances, 212,435 prompt chars

Shard 10 (2026-08-05 → 08-11) STARVED — its reasoning consumed the full 16,000-token completion
budget before visible output. That window is therefore **unread** and any claim resting on it is
unsupported.

## Decorrelated-by-question branches
- **silence** — 2026-04-28 .. 2026-06-20, 124,726 chars. Landed.
- **adversarial** — two 120,000-char samples (April vs August). Landed.

## Standing limits
- All branches ran on one vendor (deepseek-v4-pro). Correlated failure is NOT excluded.
- Branch outputs are preserved verbatim in this directory and were not edited into the prose.
