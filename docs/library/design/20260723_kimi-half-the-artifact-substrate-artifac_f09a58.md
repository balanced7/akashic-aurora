---
akashic_id: art_20260723_kimi-half-the-artifact-substrate-artifac_f09a58
akashic_sha: f6736153515c
status: current
type: design
date: 2026-07-23
title: "kimi half — the artifact substrate: artifacts as store atoms, markdown as projection"
gist: "# kimi half — the artifact substrate: artifacts as store atoms, markdown as projection **My lens (declared):** the audit lens I proved tonig"
tenant: solo
visibility: fleet
seats: []
category: [substrate, audit, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T09:16:45"
updated: "2026-07-23T09:16:45"
---
<!-- GENERATED PROJECTION of art_20260723_kimi-half-the-artifact-substrate-artifac_f09a58 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# kimi half — the artifact substrate: artifacts as store atoms, markdown as projection

# kimi half — the artifact substrate: artifacts as store atoms, markdown as projection

**My lens (declared):** the audit lens I proved tonight, one level up. The .md sprawl is the
same defect as the stale VERIFIED stamp and the `current` fossil: **the artifact and its
truth live in a medium nobody can cross-read.** The fix is not labeling files — it is
moving the *source of truth* into the substrate that already does supersession, durability,
and search, and demoting markdown to what the Codex plan always said it was: a **regenerable
projection over immutable atoms.** This half is the Codex unparked, pointed at Daniel's
verbatim ask, with the migration story the Codex plan never had to write.

**The one-sentence design:** every knowledge artifact is born as a **typed store atom**
(sacred, append-only, supersession-aware, HybridStore-backed); markdown files, the console
face, the GitHub portfolio, and the recall plane are all **projections regenerated from
those atoms** — never the truth, always rebuildable, never edited by hand.

---

## Q1 SUBSTRATE — where artifacts live

**Store atoms in the HybridStore, one key family: `artifact:<id>`.** Not a new database,
not a wiki, not files-with-better-names. The store is the substrate Aurora already trusts
for the two artifacts it handles perfectly today: notes (supersede-by-title, boot-rendered)
and lessons (recall-ranked, usage-credited). Documents are the third citizen of the same
genus.

```
artifact:<id> = {
  id,                       # art_<date>_<slug>_<hash6> — stable, minted at birth
  header: {                 # the LIBRARY.md header contract, AS FIELDS (not prose)
    status,                 # current | superseded-by <art_id> | fossil
    type,                   # contract|design|brief|report|chronicle|ledger|map|…
    arc, seats, date,
    title, category[],      # NEW: explicit category facet (Daniel's #1 ask)
  },
  body,                     # full-fidelity markdown (verbatim law rides INSIDE the atom)
  supersedes, superseded,   # the lifecycle pointers the note verb already proves
  version, created_at, updated_at,
  citations_out[],          # art_ids + legacy paths this artifact cites (the graph)
}
```

**Durability (the non-negotiable, matched to git's free properties):**
- *Crash mid-write:* atomic JSON replace, same pattern as the note verb and the SpendMeter
  sidecar — a torn atom is unrepresentable.
- *Machine loss:* the File store is the durable record (Redis is the speed cache) — and the
  **git projection (Q2) is the off-machine backup**: the canonical corpus is regenerated to
  a tracked folder and pushed, so GitHub holds a full, restorable, timestamped copy. We do
  not LOSE git's durability — we *automate* it, where today it is manual and per-file.
- *History:* supersession-not-deletion (the note verb's `supersedes`/`superseded` pair)
  + `snapshot_knowledge.py` (proven restore) for point-in-time recovery. History beats git:
  supersession is a first-class field, not an archaeologist's `git log` dig.

**Why not the alternatives (Q8 carries my own design's attacks; these are the rejected
siblings):** SQLite = a second substrate to back up, schema-migrate, and keep honest against
the store — the very dual-truth defect the audit tool exists to catch. A wiki/Dendron =
another files-plus-conventions system; the sprawl returns at the next altitude. Git-managed
markdown with better lint = symptom care; the spawn-rate is untouched.

---

## Q2 GIT RESIDUE — what stays real files, and why exactly those

Three classes, and ONLY these:

1. **Crown docs (hand-edited, the portfolio's load-bearing prose):** README, AGENTS.md,
   LICENSE, CONTRIBUTING, and `docs/` UPPERCASE contracts (CONDUCT, LIBRARY, PRINCIPLES,
   ARCHITECTURE, LEXICON, VOICE…). **Why real files:** they are the repo's public face and
   its hand-maintained law; a reader clones and reads them cold. They are the L1 living set.
2. **The projection folder `docs/library/` (generated, never hand-edited, committed by
   mirror):** every current + superseded atom rendered as clean markdown with its header
   block, organized by category. **Why a file at all:** (a) git durability/off-machine
   backup for free; (b) citations resolve to a stable public URL (Q5); (c) Daniel can open
   one in any viewer. It is the *render*, not the truth — regenerable in one command from
   the store, so it can never silently drift (audit row: `git-projection` domain).
3. **Machine:** code, config, tests, scripts — unchanged.

**What LEAVES main:** the ~890 loose `research/drafts|reviewed|briefs` files, the
`research/refs` sprawl, the dated one-night positions, the fence records — all of it becomes
atoms, rendered into the projection folder, and *deleted from their old paths in one gated
migration commit* (Q6). The repo face goes from ~900 loose files to ~30 crown docs + one
tidy generated tree.

---

## Q3 BIRTH — the write door + the guard against naked .md

**The door is the `doc` verb's backend changed, not its surface.** Today `doc new` stamps a
header and writes a file (agent_cli.py:1491). Tomorrow, same verb, same args — the atom is
minted in the store and the projection re-renders. The agent's muscle memory does not change;
the substrate underneath does. That is the strangler move, and it is why the door wins on
ergonomics: `doc new --type report --title fence-x --arc ui` is *already* the cheapest way
to be born; we make it the only way.

```
doc new --type report --title "fence-ui-contract" --arc ui --seats kimi \
        --category ui,fence --body-file report.md     # body rides a file (long-body
                                                     # transport = W63 prose-door law)
# -> atom minted art_20260723_fence-ui-contract_a1b2c3, projection re-rendered
```

**Auto-typed headers:** the header contract becomes atom *fields*, so status/type/arc/date/
category are queryable natively (today they are prose only regex can read). The `doc-new`
door already stamps them; the atom makes them structured.

**The GUARD (mechanical, mint-door genus — not memory):** a pre-commit / ship-gate check,
`check_artifact_birth.py`, same genus as deepseek's mojibake guard and my audit tool:
**any new `*.md` under `research/`, `design/`, or `docs/library/` that is not in the
projection manifest REFUSES the commit.** The projection manifest is the allowlist; the only
way onto it is through the door. Naked creation becomes unrepresentable *in the commit*, the
same way rule-12 already makes a new repo-root file unrepresentable. This is the mechanical
kill of the spawn-rate — the difference between this design and every "please file properly"
convention that has failed for 890 files.

---

## Q4 READING — Daniel's open/search/rule surface

**One verb + one pane, both reading the atoms.**

- **CLI:** `lib find --category ui --status current --arc library --after 2026-07-20` and
  `lib open art_<id>` (prints the body). Search facets are the atom's header *fields* —
  category, arc, date, status, type — plus full-text over bodies. This is strictly more
  searchable than today (today: grep over filenames; the category facet does not exist).
- **Console:** a Library pane on :8787 (the face Daniel already watches) — the same query
  against the store, rendered. Open / search / rule all in the pane he already has open.
- **Rule surface:** a ruling is itself an atom (`type: ruling`) that supersedes its question —
  the note verb's supersede mechanics, so Daniel's verdict is durable, attributed, and
  auto-retires the open question from the live set.

The console pane and CLI read the *same atoms*, so they can never disagree — the audit tool's
belief-vs-state theorem, satisfied by construction instead of by a checker.

---

## Q5 CITATIONS — stable IDs + resolver + the legacy story

- **Stable ID:** the `art_<date>_<slug>_<hash6>` id is minted once and never changes, even as
  the body is superseded (the *id* is the citation; supersession is a field, not a new id).
- **Resolver:** `lib open <id>` locally; in the projection, each atom renders to
  `docs/library/<category>/<slug>-<hash6>.md` — a **stable public URL** for GitHub readers
  and for cross-file links inside the corpus.
- **Legacy path-citations (the hard constraint — hundreds exist):** migration mints every
  existing file an id and records a **`legacy_path → art_id` map as a committed atom +
  a generated `docs/library/LEGACY.md` redirect table**. `lib open <old-path>` resolves
  through the map. **Nothing becomes unfindable; every old citation keeps resolving.** This
  is the receipts doctrine applied to the migration itself: we preserve not just the bodies
  but the *web of references between them* (`citations_out` makes the graph explicit and
  queryable — today it is implicit and greppable only by luck).

---

## Q6 MIGRATION — phases, verification, what Daniel gates

The supersession-sweep classification I filed this morning returns here as **evidence, not
stamps** — the 184-row census with verdicts is the migration's founding triage.

- **P0 — prove the loop on one type (gate: Daniel picks the type; recommend `report`).**
  Build atom + door + projection + guard for reports only. Migrate the ~88 `research/reviewed`
  files. **Verification:** byte-for-byte body preservation check (every migrated body's sha
  matches its source file's sha), the legacy map resolves all old paths, `lib find --type
  report` returns the full set. Zero value loss is the *acceptance bar*, not a hope.
- **P1 — the hot types:** `brief`, `design`, `chronicle` (the arcs in flight). Same bars.
- **P2 — the long tail + `refs/` cleanup:** dated positions, fence records, one-night
  halves. My sweep's FOSSIL/SUPERSEDED lists decide their birth status (migrated *as*
  fossil/superseded — the truth rides the atom from birth).
- **P3 — the flip:** old paths deleted in ONE gated commit (the projection is live, the
  legacy map committed, restore proven via snapshot_knowledge). **Daniel gates P3 — the
  deletion is his, and it is one visible commit, not a slow leak.**

**What Daniel gates:** P0 type choice, the phase bars (he sees each phase's verification
receipt), and the P3 deletion commit. He never gates a routine artifact birth — the door
and guard make those safe by construction.

---

## Q7 PUBLIC FACE — what GitHub becomes

**From ~900 loose files to a portfolio.** The clone shows: `README.md` that sings, `docs/`
with ~30 crown contracts, `core/` + `scripts/` clean code, and `docs/library/` — a tidy,
category-organized, generated knowledge tree that *demonstrates the product in its own
docs*: "this fleet's memory is a queryable substrate; the markdown is a render." For a
public Apache-2.0 portfolio that is a *stronger* story than a wall of dated research files —
the repo stops confessing its process mess and starts exhibiting its architecture. The
900-file chaos reads as a team that can't govern its own knowledge; the atom-and-projection
repo reads as a team that built the cure.

---

## Q8 SELF-ATTACK — the costs and failure modes of MY OWN design (mandatory, adversarial)

1. **Binary-diff opacity / review friction.** Git diffs of prose are how the fleet fences
   documents today. Store atoms don't diff in GitHub's UI. **Mitigation:** the projection
   folder restores exactly that — every change re-renders to a git diff of clean markdown,
   so review happens on the projection, as readable as today. But the *truth* is in the
   store, so a fence that reads only the diff could miss that the atom's *header fields*
   changed without a body change. The projection must render header diffs too — and I have
   not fully solved "the fence reads the projection but rules on the atom." Real cost.
2. **The guard can be bypassed.** `check_artifact_birth.py` guards the *commit*, but an
   agent can write a loose .md and simply not commit it, or commit it under `scratch/`
   (gitignored). The spawn-rate isn't killed, just fenced at the repo boundary. Loose files
   still accumulate locally. **Honest residual:** the guard stops *pushed* sprawl, not local
   sprawl; the wrap census (already exists) must catch local strays. Weaker than it sounds.
3. **Store = single point of failure + a NEW belief surface.** Today git is the truth and
   anyone can read it. If the store corrupts and the projection is stale, we have *two*
   truths and my own audit tool's founding theorem (the fleet trusts its beliefs about
   itself) applies: the projection could claim current while the atom says superseded.
   **Mitigation:** the `git-projection` audit domain (cross-read projection vs atoms) is
   load-bearing, not optional — the design ships its own lie detector or it recreates the
   disease one layer down.
4. **Migration is the risky part, not the target state.** Byte-preservation + citation
   remapping for ~890 files is where value actually gets lost. A botched sha check or a
   missed citation silently breaks the receipts law. **Mitigation:** phase bars with sha
   verification per file; but I flag honestly that "zero value loss" is an aspiration with
   a verification bar, not a guarantee — P0 on one type exists precisely to find out.
5. **Ergonomics regression risk.** If `doc new` + projection re-render is *slower* than
   Write-a-file (a store write + a regenerate + a mirror commit per artifact), agents will
   feel the tax and route around it (the exact drift the guard then has to catch — a
   self-inflicted arms race). The projection re-render must be incremental (one atom → one
   file), not a full-corpus regen per birth, or the door is too expensive and Q3's whole
   premise collapses.
6. **Category facet Goodhart.** Daniel's #1 ask is search-by-category, but a free-text
   `category[]` field invites category-sprawl (900 categories is the .md sprawl one facet
   over). Needs a capped, governed taxonomy (the T034 Goodhart-1 law applies to facets
   exactly as to dials) — and this design names the need but does not yet design the
   taxonomy. Unowned sub-problem, flagged.

**Where I want the counter to hit hardest:** Q8.1 (the fence-reads-projection-rules-on-atom
gap) and Q8.5 (door-expense collapse). If either is fatal, the design degrades to "atoms for
verbatim receipts, files for everything else" — a defensible fallback, but not the cure.

— kimi (fresh-eyes / megaread seat; peer halves UNREAD at filing)
