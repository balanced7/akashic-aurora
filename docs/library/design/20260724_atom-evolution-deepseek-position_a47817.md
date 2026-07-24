---
akashic_id: art_20260724_atom-evolution-deepseek-position_a47817
akashic_sha: dfbbbfe206d5
schema_version: 1
status: current
type: design
arc: atom-evolution
date: 2026-07-24
title: atom-evolution-deepseek-position
gist: "deepseek evolution position (consolidated): body_sha as the schema-bridge fingerprint + TOP 5 laws from the importer lens"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [substrate, governance, tooling]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_atom-evolution-contract-round_af0c75
    rel: discusses
created: "2026-07-24T17:18:21"
updated: "2026-07-24T17:18:21"
---
<!-- GENERATED PROJECTION of art_20260724_atom-evolution-deepseek-position_a47817 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-evolution-deepseek-position

Already delivered at hop 61. The full independent position is there — answering the calibrated question (body_sha as the schema-bridge fingerprint), TOP 5 ranked laws, kill list, and consumer blast-radius registry. The atom body is written and ready to mint through the door; shell is gated so I can't run `agent_cli.py doc new` directly.

Here's the consolidated answer to the calibrated question, followed by the position summary:

---

## The importer's law, six months from now

**`body_sha` as the schema-bridge fingerprint.**

The importer (`enrich_corpus.py`) minted 658 atoms. Every one carries `body_sha` — a 12-char SHA of the stripped body. The projection renderer stamps it as `akashic_sha` in frontmatter. The `--verify` pass cross-reads it. The gen_library `--verify` drift meter photographs the pair `(akashic_id, akashic_sha)`.

Six months from now, when schema bumps to v2 and `segments[]` replaces flat `body`, the importer's successor will ask: "which atoms are still v1, and did their migration succeed?" The answer lives in `body_sha`. A v1→v2 shim recomputes `body_sha` from the original body, verifies it matches the v1 atom's stored fingerprint, stamps the v2 atom with `migrated_from_sha: <original>`. The importer's six-months-later self never has to wonder "did I read this right?" — the fingerprint is the bridge.

Without this law, a v2 rebuild that silently drops a field is indistinguishable from one that correctly restructured it. The belief-vs-state disease at the schema layer.

---

## Position summary (full at hop 61)

**L0:** body_sha as schema-bridge fingerprint (my unique contribution — the answer to Daniel's calibrated question)

**L1:** Additive optional fields never bump the version (agreed with Claude `6129d6`)

**L2:** Unknown-key round-trip preservation — ranked HIGHER than Claude does because `supersede()` at `atoms.py:216` already mutates-and-reserializes; one "clean rewrite" refactor away from silent v2 field loss

**L3:** Replay-totality via chained read shims (agreed; add: shims must be idempotent)

**L4:** Consumer blast-radius registry — named all 10 consumers with version-sensitivity classes. **Kimi's answer:** `projection.render_atom()` breaks first under unshimmed v2 (renders `body` directly; v2 replaces with `segments[]`)

**L5:** V-next fire drill (agreed)

**Kill list additions:** (a) dual-write false friend — atom analog is shims-at-read, not dual JSONL; (b) auto-rewrite on read double-named

**Total cost:** ~70 lines + one contract atom

The atom body is drafted at hop 61. Needs `py agent_cli.py doc new --type design --arc atom-evolution` to mint. Cite brief `af0c75`, claude position `6129d6`.

*— deepseek, kind=reply*
