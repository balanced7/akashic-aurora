# LIBRARY — where things live, and why (the filing law)

Status: current  (v1, 2026-07-21 — ratified from the three-voice round; decision record:
docs/library-schema-reconciliation-2026-07-21.md. Charter: Daniel — "know where to find what we
are looking for instantly … know how to categorize and seed appropriately too. this too is a
form of ergonomics.")
Type: contract · Arc: library-schema · Seats: fleet

**The one-facet law:** a path encodes exactly ONE thing — the document's TYPE (+ date + slug).
Every other facet (arc, seats, status, subsystem) lives in the header and is served by generated
catalogs. **Never re-shelve to re-categorize; regenerate the catalog.** Filing takes zero
judgment: the type decides the home.

## The header contract (every non-generated doc is born with it)

```
Status: current | superseded by <path> | fossil
Type: <type> (<kind>) · Arc: <arc-or-T#> · Seats: <authors> · Date: YYYY-MM-DD
```

- **The header beats the filename.** `Status: current` in the header is the living-marker;
  UPPERCASE is the recommended dress for contracts, not the law (this is what makes
  `method-baseline-2026-07.md` lawful as it stands).
- Legacy tolerances on read: `Class:` ≡ `Type:` · `superseded-by` ≡ `superseded by`.
- Seeding door: `doc new` stamps header + canon name + home (D1, deepseek). Direct writes ship
  without headers (runner exempt); the wrap census and push-lint catch stragglers — never a
  write-time block.

## WHERE THINGS GO

| You have in hand | Type | Home |
|---|---|---|
| Living law that must stay true | contract | `docs/`, named `UPPERCASE.md` (or repo root: README, AGENTS, CONTRIBUTING) |
| Generated census/projection — never hand-edit | map | `docs/` (MODULE_INDEX, MAP, PHYSICS, DOORS, SHELVES) |
| Position / counter / reconciliation | design | `research/drafts/` → reconciled to `docs/` |
| Work order to a seat | brief | `research/briefs/` (the word is *brief* — see LEXICON: charter) |
| Verbatim evidence: fence, review, walk, frontier sweep | report | `research/reviewed/` |
| Story, reflection, journey | chronicle | `chronicles/` (+ `docs/JOURNEY.md`) |
| Living append/flip list | ledger | `docs/` (fleet) or `research/` root (research-day, per its README) |
| A seat's standing contract | agent-contract | `charters/<agent>/CHARTER.md` |
| Harness skill | skill | `.agents/skills/` |
| Behavioral pin | pin | `tests/` — probes NEVER here (→ `scratch/`) |
| Run output, logs, play receipts | receipt | `scratch/`, `data/play/*/runs/` — gitignored, curated at wrap |
| Code the fleet runs | machine: code | `core/`, `agent/`, `scripts/`, root CLIs |
| Seat/harness config | machine: config | `.claude/`, `.codex/`, `.agents/`, `config.py` — secrets-scan at the door |
| Runtime state | machine: state | `state/`, `data/`, `sessions/` — gitignored per family (task ledger excepted) |
| Dead but instructive | fossil | stamped in place, or `docs/_archive/` + a FOSSILS.md row |
| New repo-root entry | — | don't — rule-12 allowlist; propose at a gate |

## Naming: two declared zones

- **research zone**: `<seat>-<topic>-<kind>-<YYYY-MM-DD>.md` (who spoke, about what, in what role, when)
- **docs zone**: `<topic>-<kind>-<YYYY-MM>.md` (what it is; month is enough for artifacts)

## The four doors (finding)

1. **Shelf** — INDEX.md stays the hand-curated one-screen living set; `SHELVES.md` (generated
   into `docs/` by D2) is the per-type census — can't rot, carries its timestamp.
2. **Arc-thread** — `arc <id>`: every brief, design, report, pin, commit, and lesson of an arc,
   in order ("trace our steps," materialized — build slice, claude).
3. **Recall** — headers make docs first-class recall citizens (ingestion owner: boot/knowledge-map).
4. **Name** — the zone canons make paths guessable.

## Growth: L1 / L2 / L3

L1 = the living set (contracts + maps): one screen, forever. L2 = active arcs (hot dated docs).
L3 = cold history: superseded, reconciled, fossilized — findable through every door, never in
the way. Consolidation at gates demotes L2→L3: write the successor, stamp the ancestors, never
delete meaning. Default is **stamp-in-place**; a file MOVES to `docs/_archive/` only when
grep-uncited (including store-side citations) AND superseded.

## The guard registry (rules land with pins; a schema without doors is lore)

| Rule | Checks | Placement | Status |
|---|---|---|---|
| 8 | mojibake byte-classes in tracked md | mirror.py pre-commit REFUSE (+ check_boundaries backstop) | building (D3, deepseek; claude fences) |
| 9 | probes out of `tests/` | check_boundaries | queued (claude) |
| 10 | header contract on new docs | push-lint + wrap census (never write-time) | after D1 lands |
| 11 | home-matches-type | check_boundaries | queued (claude) |
| 12 | repo-root allowlist | check_boundaries | queued (claude) |

## Amendment

This law amends at gates by the standing round protocol (counter → reconcile → Daniel ratifies).
Censuses in this file and INDEX are generated, never hand-counted (the hand counts of 2026-07-21
ran ~2× stale — lesson `census-claims-vs-listings`). Version bumps append; ancestors stay
readable.
