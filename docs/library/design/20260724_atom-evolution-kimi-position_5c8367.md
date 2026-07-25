---
akashic_id: art_20260724_atom-evolution-kimi-position_5c8367
akashic_sha: 56867740cb4c
schema_version: 1
status: current
type: design
arc: atom-evolution
date: 2026-07-24
title: atom-evolution-kimi-position
gist: "kimi evolution position: rebuild() breaks FIRST (silent store poisoning) + 3-stage drill + 10-consumer blast-radius registry + 5 laws (rebuild gate, additive-only v+1...)"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [substrate, audit, library]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_atom-evolution-contract-round_af0c75
    rel: discusses
created: "2026-07-24T21:18:26"
updated: "2026-07-24T21:18:26"
---
<!-- GENERATED PROJECTION of art_20260724_atom-evolution-kimi-position_5c8367 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-evolution-kimi-position

## CALIBRATED ANSWER: which consumer breaks FIRST under an unshimmed v2?

**`AtomFamily.rebuild()` — the JSONL replay path (core/library/atoms.py:377-403).** It breaks SILENTLY, before any other consumer reads a single atom.

### The break chain

1. `rebuild()` has NO schema-version gate. `get()` does (line 214: `if v > SCHEMA_KNOWN_MAX: raise AtomError`), but `rebuild()` reads raw JSON from disk and pushes it directly into the store with zero version check.

2. After a v2 atom lands in the JSONL (say, with `header.lifecycle` replacing `header.status`, or `body` replaced by `segments[]`), `rebuild()` calls `self._index(atom)` which accesses `atom["header"]["status"]` — a KeyError on the v2 shape. This either crashes `rebuild()` mid-stream (torn store) or writes phantom index entries.

3. Once the store is poisoned, EVERY downstream consumer that iterates atoms breaks:
   - `gen_library --from-store`: `find()` → `get()` → `AtomError`, census build crashes
   - `projection.render_atom()`: `get()` → `AtomError`, projection missing
   - recall injector: any atom-linked lesson → `AtomError`
   - MCP boot stats: atom enumeration → `AtomError`

4. The failure is contagious: one v2 atom in the JSONL poisons the entire store. And it's silent: `rebuild()` returns a success count, but the next operation explodes with an unrelated `AtomError`.

### Why rebuild is the canary

Every other consumer reads atoms through `get()` — which has the refuse-loud gate. An unshimmed `get()` is survivable: loud error, skip, continue. But `rebuild()` WRITES v2 atoms into the store WITHOUT the gate. Once there, index contamination spreads to v1 atoms via backlinks. The library becomes unreadable as a whole.

### The fix (surgical)

`rebuild()` needs the same `schema_version > SCHEMA_KNOWN_MAX` check that `get()` has — BEFORE writing to the store. A v2 line should be (a) refused with a loud stderr line naming the atom id + the `migrate_schema` door, or (b) parked in an `artifact:index:schema_future` set for later upgrade.

---

## THE DRILL THAT CATCHES IT BEFORE SHIPPING

### Stage A: Fixture replay (unit)

Place ONE v2-atom fixture line in a test JSONL. Run `rebuild()`. Assert:
- `rebuild()` either refuses the v2 line loudly, or skips it cleanly and leaves the store intact
- After rebuild, `find()` returns only v1 atoms
- `verify_backlink_index()` is clean (no phantom entries)
- No `KeyError` escapes `_index()`

**Current state:** WOULD FAIL — `rebuild()` silently ingests the v2 line and `_index()` crashes on the missing field.

### Stage B: Census regression (integration)

With the same fixture v2 atom in the JSONL, run `gen_library --from-store --verify`. Assert:
- Census build completes (non-zero exit for "found unknown version" is acceptable; crash is not)
- All v1 atoms render in the census
- The v2 atom is counted as "skipped" or "future-version" in the output, never silently dropped

**Current state:** WOULD CRASH — `_atoms_as_entries()` calls `fam.find()` → iterates → `fam.get()` → `AtomError`.

### Stage C: Full-replay acceptance gate (end-to-end)

Extend `test_rebuild_from_jsonl_restores_store` (tests/test_atoms.py:170) with a v2-resilience variant:
- Fixture has 3 v1 atoms + 1 v2 atom
- Rebuild runs to completion
- All 3 v1 atoms are queryable
- The v2 atom is either refuse-loud-at-rebuild-time or parked in `artifact:index:schema_future`
- `gen_library --verify` is green on the v1 corpus

---

## CONSUMER BLAST-RADIUS REGISTRY

Every atom consumer, ranked by breakage severity under an unshimmed v2:

| # | Consumer | File | Breaks under unshimmed v2? | Failure mode |
|---|----------|------|---------------------------|-------------|
| 1 | `rebuild()` | atoms.py:377 | YES — SILENT | Ingests v2 without gate; index corruption spreads to v1 atoms via backlinks |
| 2 | `gen_library --from-store` | gen_library.py:112 | YES — CRASH | `find()` → `get()` → `AtomError` on v2 atom; census build aborts |
| 3 | `projection.render_atom()` | projection.py:94 | YES — LOUD | `get()` refuses v2; projection missing; `--verify` catches the gap |
| 4 | `enrich_corpus.py --verify` | enrich_corpus.py | YES — LOUD | sha cross-read fails on missing projection; exit 1 gates the ship |
| 5 | recall-at-action injector | at_action.py | PARTIAL | Lesson records are separate from atoms; only atom-cited lessons break |
| 6 | MCP `boot()` library stats | agent_cli.py cmd_boot | PARTIAL | Atom enumeration → `AtomError` on v2; v1 stats still render |
| 7 | `harmonize_knowledge.py` | harmonize_knowledge.py:156 | NO | Works on learn: keys, not atoms; orthogonal substrate |
| 8 | A2 audit (verify_backlink_index) | atoms.py:326 | PARTIAL | Operates on store index directly; phantom entries from contaminated rebuild |
| 9 | Future pane UI | (not built) | TBD | Will need its own version gate; rebuild contamination would poison its index reads |
| 10 | MCP `doc get` / `doc find` | agent_cli.py cmd_doc | YES — LOUD | `get()` refuses v2; `find()` skips (index-only, no body parse); mismatch = silent drop |

---

## TOP-5 RANKED LAWS (with costs)

### LAW 1: The Rebuild Gate
**Rule:** `rebuild()` MUST apply the same `schema_version > SCHEMA_KNOWN_MAX` refusal that `get()` applies BEFORE writing any atom into the store. A v2 JSONL line is either REFUSED (with a loud stderr naming the atom id + the `migrate_schema` door) or parked in a dedicated `artifact:index:schema_future` set.
**Cost:** ~4 lines in `rebuild()`. Trivial.
**Why #1:** Without this, every other law is moot — the store is already poisoned.

### LAW 2: Additive-Only v+1
**Rule:** A schema v+1 MUST carry all vN fields with identical keys and semantics. New fields are ADDITIVE and OPTIONAL. No field is renamed (add the new name, keep the old as a deprecated alias). No field changes type. The `segments[]` array in v2 is ADDED alongside `body` (v1 readers ignore it; v2 readers prefer it, falling back to `body` when absent).
**Cost:** Discipline in the migrate transform. Trivial to verify: a `diff(old_atom_keys, new_atom_keys)` must be a strict superset.
**Why #2:** This is the Avro/Protobuf law that makes forward-compatibility mechanical. Rename = break. Add = safe. Every v1 reader that only touches `body` ignores `segments[]` entirely.

### LAW 3: The Replay-Totality Contract
**Rule:** Every historical shape (including pre-v1.1 atoms with `tenant` stored in the header, pre-version atoms with no `schema_version`, and atoms from every intermediate migration state) MUST survive a `rebuild()` → `get()` → `frontmatter()` round-trip with byte-identical projection output. The test fixture grows one atom of each historical shape; the rebuild-render-compare pin gates every schema bump.
**Cost:** A growing fixture of ~5-10 atoms. One test that rebuilds and diff's projections. ~30 lines.
**Why #3:** This is the archival-format distinction — atoms are forever. The packet spec can drop old versions after TTL; atoms must replay every shape minted in the project's history.

### LAW 4: The Migrate Door Is Append-Only
**Rule:** `migrate_schema` NEVER edits JSONL lines. It appends new version-event lines (one per atom), and `rebuild()`'s "latest version wins" rule picks them up. Rollback = delete the migration lines and re-rebuild. No in-place mutation, ever.
**Cost:** The migrate door writes one line per atom. Rollback is `git checkout store/docs/*.jsonl && rebuild`. Zero new infrastructure.
**Why #4:** The packet-spec dual-WRITE pattern has no analog in append-only storage. The "latest-version-wins" semantics of rebuild() already provide the migration path — the door just formalizes it.

### LAW 5: The Consumer Registry + Pre-Ship Drill
**Rule:** Every atom consumer MUST be listed in the blast-radius registry (this document's table). Before ANY `SCHEMA_KNOWN_MAX` bump, the three-stage drill (fixture replay → census regression → full-replay gate) runs against EVERY consumer. The drill is a SHIP GATE: `SCHEMA_KNOWN_MAX` cannot advance until every consumer's drill row is green.
**Cost:** One registry table (maintained). One drill script (~50 lines) that fans the three stages across consumers.
**Why #5:** The packet spec's roster discipline, applied to atoms. The consumer you forget to check IS the one that breaks.

---

## KILL-LIST (over-engineering to avoid)

1. **Per-consumer version shims.** Don't build a plugin architecture where each consumer registers its own upgrade function. The additive-only law means v1 readers need ZERO changes — they ignore new fields. The only "shim" is the rebuild gate.

2. **Dual-write (packet analog).** There is no atom dual-write. The JSONL is append-only by construction. "Latest version wins" at rebuild() is the migration path. Don't invent a second storage layer.

3. **Backward migration (v2 → v1 downgrade).** Don't build it. v1 readers handle v2 atoms by ignoring new fields. "Downgrade" is a non-operation. The only direction that needs a door is forward migration (v1 → v2), and that's the `migrate_schema` door appending new lines.

4. **Schema registry service.** Don't build a runtime schema registry. `SCHEMA_KNOWN_MAX` is a single integer in `atoms.py`. Bumping it is one line. A registry that queries atoms to discover schemas adds a runtime dependency with zero benefit — the corpus is finite and versioned in git.

5. **Automatic schema detection from JSONL.** Don't scan the JSONL to auto-detect the max version. The `SCHEMA_KNOWN_MAX` constant is the reader's CLAIM about what it understands. Auto-detection would silently raise it on a v2 line, defeating the refuse-loud gate.

6. **Version negotiation at the MCP door.** Don't build it. The MCP door serves atoms through `get()`/`find()` — the gate is at the reader, not the transport. Version negotiation on the wire adds complexity for a problem that doesn't exist (there's one reader, local, same process).
