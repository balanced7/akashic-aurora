---
akashic_id: art_20260724_atom-evolution-claude-position_6129d6
akashic_sha: d7bb0160fc61
schema_version: 1
status: current
type: design
arc: atom-evolution
date: 2026-07-24
title: atom-evolution-claude-position
gist: "claude half: archival-not-wire frame; 5 laws (additive-never-bumps, unknown-key round-trip pin, chained read shims, consumer registry, v-next fire drill); kill semver/registry-service/auto-writeback"
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, governance, migration]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_atom-evolution-contract-round_af0c75
    rel: discusses
created: "2026-07-24T08:05:57"
updated: "2026-07-24T08:05:57"
---
<!-- GENERATED PROJECTION of art_20260724_atom-evolution-claude-position_6129d6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-evolution-claude-position

CLAUDE'S INDEPENDENT POSITION -- atom-evolution round (harness/conductor lens; written before either seat's half, not shared with them).

## THE HONEST ANSWER TO DANIEL'S QUESTION

Mostly yes, as of last night -- and the remaining gap is law, not mechanism. v1.1 built the keystone the packet spec taught us: a version field with FAIL-CLOSED readers (absent->1, newer refuses loud), read-time folds as the deprecation mechanism (cites->discusses landed with ZERO migration churn -- the proof the pattern works), and a pre-named v2 (segments[]) with its trigger. What the packet spec has that atoms still LACK: (1) the written dual-version MIGRATION RULE as ratified law, (2) the unknown-key preservation guarantee AS A PIN, (3) the consumer blast-radius registry. Mechanism without law is how the next eager seat breaks the house politely.

## THE FRAME: atoms are an ARCHIVAL format, not a wire format

Packets age out by TTL; version skew is transient and dual-WRITE bridges it. Atoms replay FOREVER (append-only JSONL is the recovery truth) -- every shape ever minted must stay readable for the project's lifetime. Steal the packet spec's version discipline; do NOT steal dual-write (its false friend here). The atom analog of dual-write is: READERS carry shims, HISTORY stays untouched, PROJECTIONS regenerate. Avro/Parquet-class thinking, not MQTT-class.

## TOP 5 (the laws I would ratify)

1. **L1 ADDITIVE-NEVER-BUMPS.** New OPTIONAL fields with read-time defaults do NOT bump schema_version (v1.1 itself shipped body_type this way -- the precedent is one night old and already load-bearing). Version bumps are reserved for SEMANTIC changes: a field's meaning changes, or the body's shape changes (segments). Cost: zero; it is a sentence in the contract. Kill-risk it prevents: version-number inflation that trains readers to ignore the gate.

2. **L2 UNKNOWN-KEY ROUND-TRIP (the packet spec's T043 law, ported).** Any writer touching an atom it did not mint (status flip, supersede-flip, index repair) must preserve fields it does not understand. Today this is TRUE BY ACCIDENT (we json-load the whole dict, mutate, dump) -- one 'clean rewrite' away from silent data loss. Cost: one pin (~15 lines: build a fake v99 atom w/ alien fields, flip its status, assert aliens survive). This is the highest value-per-line item on the list.

3. **L3 REPLAY-TOTALITY VIA CHAINED READ SHIMS.** rebuild() must read every historical shape forever. Mechanism: pure functions upgrade_1_to_2(atom)->atom, chained at READ (get/rebuild), never rewriting JSONL lines. History is sacred; shims are cheap; a shim chain 5 versions long is still microseconds. The migrate_schema door = OPTIONAL compaction that appends new version-events for hot atoms (read-path relief), never a requirement for correctness. Rollback story: shims are read-side -- rolling back a bad v2 = revert the reader; the store still holds every event.

4. **L4 THE CONSUMER REGISTRY + BUMP CHECKLIST.** Name every atom reader in ONE table (family, projection, gen_library census + --verify, recall ingest, A2 audit rules, export, pane, MCP doors) with its version-sensitivity class (shape-blind / field-reader / body-parser). A version bump ships ONLY with the checklist ticked per consumer (shimmed / unaffected-with-reason / refuses-loud-by-design). This is T104's blast-radius law applied to schema moves. Cost: one table in the contract atom + a checker that greps the registry exists (~20 lines).

5. **L5 THE V-NEXT FIRE DRILL.** Before any bump lands: mint a fixture v-next atom (in the test namespace), run EVERY registry consumer against it, assert each either handles it (shimmed) or refuses loud (unshimmed) -- never a silent wrong render. The drill is the schema analog of the T104 fire-verification matrix and reuses v1.1's refuse-loud pin shape. Cost: ~40 lines of parameterized test; runs in the suite forever.

## KILL LIST (over-engineering I would refuse)

- **Full semver (major.minor.patch) on atoms.** One integer + L1 covers us; three-part versions invite bikeshedding and imply compatibility promises nobody audits. The packet spec's single 'v' was right.
- **A schema REGISTRY SERVICE (Avro-style).** We are one repo; the contract atom + constants in atoms.py ARE the registry. A service is corporate-wave machinery with no tenant yet.
- **Auto-migration on read-with-writeback.** Reading must NEVER write (a reader that silently rewrites atoms is a belief-vs-state factory and murders append-only). Compaction is a DOOR, deliberate, gated.
- **Per-field version stamps.** The atom versions as a WHOLE; per-field versioning is the CMS trap one level down.

## WHAT THIS COSTS TOTAL
The contract atom (the law, ~1 page) + 2 pins (L2 round-trip, L5 drill) + 1 table (L4 registry) + the migrate door deferred until v2 actually approaches (segments/pane trigger). Everything else already exists as of last night.
