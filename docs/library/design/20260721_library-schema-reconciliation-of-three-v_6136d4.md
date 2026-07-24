---
akashic_id: art_20260721_library-schema-reconciliation-of-three-v_6136d4
akashic_sha: f66a80cdedb5
status: current
type: design
arc: library-schema
date: 2026-07-21
title: Library Schema — reconciliation of three voices
gist: "Reconciles: `research/drafts/repo-organization-opening-claude-2026-07-21.md` + `research/drafts/library-schema-opening-claude-2026-07-21.md`"
tenant: solo
visibility: fleet
seats: []
category: [library, method, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260721_repo-organization-hygiene-opening-positi_b06cf7
    rel: cites
  - target: art_20260721_the-library-schema-the-file-plane-is-a-s_b0ee40
    rel: cites
  - target: art_20260721_repo-organization-library-schema-counter_7b7d06
    rel: cites
  - target: art_20260721_kimi-counter-library-schema-repo-organiz_81a2e9
    rel: cites
created: "2026-07-21T22:09:57"
updated: "2026-07-23T23:13:48"
---
<!-- GENERATED PROJECTION of art_20260721_library-schema-reconciliation-of-three-v_6136d4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Library Schema — reconciliation of three voices

Reconciles: `research/drafts/repo-organization-opening-claude-2026-07-21.md` +
`research/drafts/library-schema-opening-claude-2026-07-21.md` (claude, openings) ·
`research/drafts/repo-organization-counter-deepseek-2026-07-21.md` (deepseek, counter) ·
`research/reviewed/kimi-library-schema-counter-2026-07-21.md` (kimi, fresh-eyes counter).
Upon ratification the law lands as **docs/LIBRARY.md** (living contract); this doc then reads as
the record of how it was decided.

---

## A · Unanimous core (independently affirmed by all three seats)

- **U1 — One schema, two planes.** The file library is the human plane of the store's physics:
  typed at birth, supersession not mutation, regenerable projections, recall integration,
  consolidation that preserves intention. (kimi: the wild already practices it — supersession
  stamps exist on files today.)
- **U2 — The one-facet law.** Path encodes TYPE only; every other facet lives in the header and
  is served by generated catalogs. Both counters ran the kill-test independently and type won
  both times: folders-by-arc silently drops multi-arc docs (deepseek); no stranger question is
  answered better by arc folders, and research/'s shared shelf makes arc folders impossible
  anyway (kimi). Never re-shelve to re-categorize.
- **U3 — The type table**, lifecycle (living / point-in-time / append-only / ephemeral) as the
  primary axis — better than audience-first (Diátaxis) for an engineering memory.
- **U4 — Four retrieval doors** (shelf / arc-thread / recall / name); arc-thread is the star:
  "trace our steps," materialized.
- **U5 — L1/L2/L3.** Living set stays one screen forever; history grows cold, findable, never lost.
- **U6 — Guards make it law instead of lore.** Discipline-without-door fails (the mojibake
  second bite is the season's proof).
- **U7 — First-pass sequence**: ratify → commit-by-name → generated shelves → guards → junk →
  **lazy backfill only** (never a big-bang rewrite of ~97 docs).

## B · Reconciled under counter-fire (what the round changed)

- **R1 — Header contract = convention + door, never a write-time gate.** `doc new` stamps
  headers at birth (deepseek builds it); the runner is exempt at write time; rule-10 fires as a
  push-time lint + wrap census, and **accepts legacy spellings** (`Class:` ≡ `Type:`,
  `superseded-by` ≡ `superseded by`) so day one doesn't red-flag the fleet's best-behaved docs.
  Pre-registered acceptance: >2 unheaded new docs/week after `doc new` ships = the door failed.
- **R2 — Header beats filename.** The living marker is `Status: current` in the header;
  UPPERCASE is recommended dress for contracts, not law. This heals the fleet's most-cited
  contract (`docs/method-baseline-2026-07.md` — lowercase, dated, and *the* HOW law) without
  renaming anything, and makes rule-11 checkable by header. Amends INDEX.md's two-kinds phrasing
  (ratification item — it edits standing law).
- **R3 — The machine rows.** kimi's Gap 2: Daniel said *files*, not docs. Three rows added —
  **code** (`core/`, `agent/`, `scripts/`, root CLIs), **config** (`.claude/`, `.codex/`,
  `.agents/`, `config.py`; standing secrets-scan at the door), **state** (`state/`, `data/`,
  `sessions/`, logs; gitignored per family). Rule-12's root allowlist is now writable; kimi's
  Part-3 table is its v0 draft.
- **R4 — research/ is two organisms, one root.** The research-day loop (queue→drafts→reviewed,
  README-lawful root files) and the fleet-round loop (briefs/openings/counters/reports) share
  shelves. Amend `research/README.md` to declare BOTH lifecycles; only then do the P2 guards
  arm. Most "root strays" were the day organism's lawful files.
- **R5 — Naming: two declared zones.** research zone `<seat>-<topic>-<kind>-<YYYY-MM-DD>`;
  docs zone `<topic>-<kind>-<YYYY-MM>`. Door 4 (guessable names) becomes honest by declaring
  the zones instead of pretending one canon exists.
- **R6 — Generators, owned.** `gen_library.py` (shelves) = deepseek · `arc_thread.py` = claude ·
  wrap `header_census` = claude · **recall-door ingestion gets a named owner** (boot/knowledge-map
  walk reads headers; claude designs it in its build slice — no more asserted-not-designed).
- **R7 — Orphan rot has an owner.** Docs that never pass a gate (one-off audits, moodboards)
  get their `Status:` flips from the wrap census + boot drift-line — otherwise L3 fills with
  fossils still stamped `current`.
- **R8 — LEXICON ruling proposed: "charter" = an agent's standing contract, ONLY.** Work orders
  are **briefs**. kimi found FOUR live meanings; the word is the fleet's most overloaded.
  Forward-naming only — cited fossil filenames keep their names (P1), the WORD gets fixed.
- **R9 — One guard registry.** Rules 8–12 as numbered in the library opening; the repo-org P9
  numbering is retired (kimi caught the collision).
- **R10 — Rule-8 (mojibake) lands at mirror.py pre-commit**: REFUSE the commit, name
  file+line+class; check_boundaries is the backstop. The write doors are already UTF-8 — the
  proven vectors were the verbatim-persist pipe and PowerShell edits (second-bite forensics).
- **R11 — .codex/** commits clean, with a deny-by-default `.codex/.gitignore` and a standing
  secrets-scan at the door — a one-time peek justifies nothing (kimi), the guard must stand
  (deepseek concurs).
- **R12 — Play physics.** Tools (.py) and curated `out/*.md` = committed; `runs/*` = gitignored;
  `data/play/test/` = deleted. **No TTL timers** — "a timer that silently deletes is a
  knowledge-loss mechanism"; curation happens at wrap, owned by the seat that played.
- **R13 — `docs/_archive/` is the declared physical L3 shelf** (103 entries already live there).
  Default is stamp-in-place; a doc MOVES to _archive only when grep-uncited — including
  store-side citations (notes/lessons/ADRs) — AND superseded. FOSSILS.md rows point at it.
- **R14 — Censuses are generated, never hand-counted.** Every hand count in the openings was
  ~2× stale against live listings (kimi's meta-finding, lesson `census-claims-vs-listings`).
  INDEX's dated-docs census becomes generator output with a timestamp.

## C · Ratification gate (Daniel) — in the stranger's unlock order

1. **G1 — The four unlocks**: header contract (with R1 tolerances) · header-beats-filename (R2)
   · machine rows (R3) · research README two-organisms amendment (R4). These make every other
   element checkable and every current file lawful.
2. **G2 — The table + words**: type table as amended (12 types + 3 machine rows) · two naming
   zones (R5) · LEXICON "charter" ruling (R8).
3. **G3 — Guards**: registry 8–12 placements (R9/R10) + wrap/boot telemetry (R7).
4. **G4 — Junk executions**: stray `E:`-mojibake dir (park its two April OpenCode jsonls to
   `_archive/prehistory/` first) · `data/play/test/` · the probe tests (`test_mcp_deep_inspect1–6`,
   `test_mcp_inspect`) · root `test_code/data/memory.json` (same species, kimi P7).
5. **G5 — The bulk commit-by-name**: ~60 untracked research/skills/launcher files now;
   `charters/` after ratification (its exemplar says so).
6. **G6 — Build slices, fenced, acceptance pre-registered**: `doc new` (deepseek) ·
   `gen_library` (deepseek) · `arc_thread` (claude) · `header_census` in wrap (claude) ·
   rule-8 mirror scan (deepseek build, claude fence) · rules 9/11/12 (claude build, deepseek
   fence) · recall-ingestion design (claude).
7. **G7 — The law lands**: `docs/LIBRARY.md` rendered from the ratified table + INDEX re-render
   with generated census.

## D · Kill-test register (standing evidence)

| Claim | Test | Result |
|---|---|---|
| Type is the one path facet | Find a retrieval arc-folders serve that arc-thread cannot | Failed twice, independently — multi-arc docs vanish from folders; no stranger question prefers folders. HOLDS. |
| Runner exemption is safe | Find a runner write that SHOULD be header-blocked | None exists — pins have docstrings, edits touch headed files. HOLDS. |
| `doc new` makes rule-10 zero-cost | Count unheaded new docs in week 1 after ship | >2/week = the door failed. ARMED (pre-registered). |
| Door 4 (names) is honest | kimi's stranger test, 3 real files | 1/3 before zones; the two lies map exactly to R2 and R8. Re-run after G1/G2 lands. ARMED. |

— Reconciled by claude from three independently-written halves; the disagreements above were
resolved by mechanism, not by rank. The fence caught what each frame could not see alone.
