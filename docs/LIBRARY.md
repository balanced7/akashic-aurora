# LIBRARY — where things live, and why (the filing law)

Status: current  (v1.1, amended 2026-07-23 — the CATEGORY plane, §below; v1 ratified 2026-07-21
from the three-voice round; decision records: docs/library/design/20260721_library-schema-reconciliation-of-three-v_6136d4.md ·
docs/library/design/20260701_homes-and-order-reconciled-to-constants_beaca7.md. Charter: Daniel — "know where to find what we
are looking for instantly … know how to categorize and seed appropriately too. this too is a
form of ergonomics." + 2026-07-23: "I want our artifacts to fit into categories and hierarchies.
for things to have a home and an order to them.")
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

## v1.1 amendment (2026-07-23) — the CATEGORY plane (the aboutness facet, now rostered)

The one-facet law named "subsystem" as a header facet; it is now the governed CATEGORY plane
(decision record: docs/library/design/20260701_homes-and-order-reconciled-to-constants_beaca7.md — the homes-and-order round).
- Three planes, never blurred: TYPE = kind (this file's canon) · ARC = campaign · CATEGORY =
  aboutness. An artifact: exactly one type · >=1 arc · 1-3 categories (PRIMARY first; needing
  4+ means split the artifact). A category never names a type or an arc.
- THE ROSTER (capped 24; grow only via propose-category door + >=3 better-served artifacts +
  Daniel gate; retire only with re-categorization; audit flags orphans + sprawl):
  substrate · migration · library · recall · memory · bus · coordination · agent-lifecycle ·
  identity · security · method · conducting · governance · audit · testing · tooling ·
  ergonomics · ui · wiki · voice · optics · performance · frontier · narrative
- HOME stays f(TYPE) — the one-facet law is unchanged; category is header/frontmatter-served,
  rendered as grouping in VIEWS only. Re-categorization is never a re-shelving.
- Default browse tree (the atom-era Library): L1 pinned, then LIVE ARCS current-first,
  superseded collapsed under successors, fossils behind one fold; type-shelf and category-lens
  are pivots. All trees derived, never hand-held.

## Amendment

This law amends at gates by the standing round protocol (counter → reconcile → Daniel ratifies).
Censuses in this file and INDEX are generated, never hand-counted (the hand counts of 2026-07-21
ran ~2× stale — lesson `census-claims-vs-listings`). Version bumps append; ancestors stay
readable.
