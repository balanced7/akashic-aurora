# The filing schema: one address, one shelf, one reader contract

Written 2026-10-03 by claude (Vandor), at Daniel's ask: *"analyze our current bits of knowledge
that we underutilize and come up with a schema for filing storage and access so that we can
index and retrieve faster, more thoroughly and more accurately. the right information needs to
live in the right place."*

Evidence: `research/reviewed/knowledge-plane-census-2026-10-03.md` — six blind agents, one
plane each, ~1.0M tokens, 445 tool uses, every number produced by a named command. This
document is the design; that one is the measurement. Where they disagree, the measurement wins.

Successor to `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md` (2026-10-01), which diagnosed
reach. This asks the next question: *given what we actually hold, where should it live.*

---

## 1. The finding that reframes the ask

**We do not have a filing problem. We have a reading problem.**

Daniel asked for a schema to file knowledge into. The census says the filing already exists,
is populated, and is well-formed — and in plane after plane, nothing reads it:

| structure that exists | how well it is filled | who reads it |
|---|---|---|
| library atoms (1,019) | `category` 99.0% across 24 labels; `type`, `status` 100% | **no door at all** |
| `narrative_chapter` on lessons | 94.37%, 315 chapters, **100% referential integrity**, 0 dangling | **one writer, zero readers** |
| T-id → commit-subject edges | 908 subjects → 304 tasks at **100% precision**, rewrite-stable | **nothing walks it** |
| `related_to` lesson graph | 790 edges over 372 lessons | one *visualisation*; **no ranker** |
| the fence plane | 28 rounds, 21 sealed reconciliations, 3.78 MB | **0 of 110 verbs** |
| lesson prose | 1,924,634 characters | **57.7% never matched against any query** |

A new taxonomy would add a seventh row to that table. The schema below therefore specifies
**three contracts** — an address, a shelf, and a reader — and each one exists to close a
*measured* defect rather than to impose an ontology.

**This is not an original stance and the house already holds it**, which after today is worth
checking before claiming. Heimdall's lesson `a_magnitude_axis_is_a_lens_not_a_filing_location`
says it directly: *"THE AXIS IS A LENS, NOT A FILING LOCATION — record richly, and let an axis
lens project it later; one finding then sits on several axes, axes are added retroactively with
no migration."* Contract B below is that lesson applied: we reuse the atom categories as a lens
rather than minting a taxonomy, so nothing has to be migrated to be found.

---

## 2. What we underutilise, ranked by measured cost

1. **57.7% of the lesson corpus is invisible to its own ranker.** `_project_items`
   (`core/recall/at_action.py:367-372`) takes the FIRST of `recommendation`, `actual`,
   `what_tried` and `break`s. **1,110,737 of 1,925,277 characters never reach a query.**
   CERTAIN — re-measured by hand rather than taken from the census, because it is the number
   this document leans on hardest; the independent replay agrees with the agent to within
   field-aliasing noise.
   The sharper figure the census did not surface: `recommendation` is chosen on 1,509 of 1,534
   projected rows (98.4%), `actual` on 25 (1.6%), and **`what_tried` on zero** — it is present
   on 1,533 rows and matchable on none of them, because one of the other two always precedes
   it. A field filled on 98% of the corpus that no query can ever touch.
2. **The target axis is two mutually unintelligible vocabularies.** 0 of 365 normalised touch
   target keys appear among `recall:outcome`'s 17,733 target keys — intersection computed raw,
   then again after stripping the `p:`/`c:` prefix and case-folding. **The join Wave 0 is being
   built on does not presently exist.** CERTAIN.
3. **Daniel's own words cannot be pushed.** 8,286 operator utterances in `state/eye/eye.db`,
   29,277,232 characters (~7.3M tokens), reachable only by `eye find`/`freq`, which a seat must
   already know to run. The single largest body of intent in the house. CERTAIN.
4. **The fence plane is unreachable.** 3.78 MB of adjudicated design rulings — the blind halves
   and reconciliations the current Wave-0 build is executing from — and zero of 110 verbs read
   it. The build specs are grep-only. CERTAIN.
5. **The sealed reference vocabulary is not spoken.** W0.1 sealed eight ref kinds
   (`core/coord/target.py REF_KINDS`); of 4,780 refs on 13,408 `events:raw` rows, only `mem:`
   (11.7%) is one of them. **88.3% of written references cannot be walked.** CERTAIN.
6. **Session id is absent exactly where it matters.** `context --stats` over 24h: touch
   796/796 and phase 88/88 at 100%, but `boot` 0/23, `boot_unverified` 0/22, `fail` 0/17,
   `learning` 0/4. **A filed lesson is not joinable to the session that produced it.** Three
   session-id resolvers already exist and the capture path uses none. CERTAIN.
7. **`narrative_chapter` is a free episode/theme axis with no reader.** 94.37% filled, 315
   chapters, every one resolving to a live record, 0 dangling. `grep -rln narrative_chapter
   core/` returns exactly one file: the writer. CERTAIN.
8. **The only rewrite-stable cross-plane edge set is unused.** 908 commit subjects carry a
   T-id, resolving to 304 real tasks at 100% precision, zero phantoms. Git itself carries **no**
   seat provenance — all 2,847 commits share one author — so this edge and the authorship
   ledger are the only answers to "who built this, and why". CERTAIN.
9. **28 ghost lessons: index entries whose bodies are gone.** 26 were surfaced 147 times and 10
   earned explicit judgments, so a reader once read a body that no longer exists. This is
   measured knowledge *loss*, not an empty field. CERTAIN that the bodies are absent; LIKELY
   that they were written and lost rather than never written — the surfacing counters are the
   evidence.
10. **Ranking inputs with no variance.** `success` is 90.5% `yes`, so the success-derived
    importance term is the same value on nine rows in ten. `confidence` is 79.4% `medium` and
    its vocabulary is split — 1,240 `medium`, 257 `high`, and 37 numeric strings (`"0.85"`,
    `"0.9"`) that no comparison handles. `domain` has three values and only 4.74% of rows carry
    a non-default one, so D5 cross-domain scoping has 4.74% of the corpus to work with. CERTAIN.
11. **The primary key is unparseable.** `experiment_name` has no convention: 704 distinct
    first-tokens, 488 occurring once, the commonest prefixes being the English words "a" (108)
    and "the" (30). Sixteen names carry a date; **zero** carry a slice id. Nothing can be
    grouped, scoped or ranged by it. CERTAIN.

---

## 3. The schema — three contracts

### Contract A — THE ADDRESS: one ref vocabulary, spoken on both sides

Every record in every plane is addressed by a ref in the **already-sealed** eight-kind
vocabulary (`event:`, `sha:`, `task:`, `lesson:`, `mem:`, `doc:`, `session:`, `seat:`). This
is not new; W0.1 sealed it. The contract is that it becomes **mandatory at write time** and
that the normaliser is applied on **both** sides of every join.

Three rules, each closing a numbered defect above:

- **A1.** A ref that is not one of the eight kinds is refused at the write door, not silently
  accepted. *(closes #5 — 88.3% unwalkable)*
- **A2.** `core/coord/target.py`'s normaliser is the only producer of a target key, and both
  the touch path and the outcome path call it. *(closes #2 — the 0-of-365 split; this is the
  single highest-value fix in the document, because every other join waits on it)*
- **A3.** Every capture carries `session_id`, resolved by one shared helper rather than three.
  *(closes #6)*

**Acceptance, pre-registered:** after A2, the touch∩outcome intersection is non-empty and its
size is reported; after A3, `context --stats` shows non-zero coverage for `learning`, `fail`
and `boot`. Both are already measured at zero, so neither can pass by accident.

### Contract B — THE SHELF: the library atom system is the filing schema

We do not design a taxonomy. We already have one that works — 1,019 atoms, `category` 99.0%
filled across 24 labels, `type` and `status` at 100% — and the census's own words for it are
*"the filing schema Daniel is asking for already exists, is populated, is indexed, and has no
door."* The contract is to give it a door and move the dark planes onto it.

- **B1.** Build the door: atoms become retrievable by category/type/status without knowing a
  filename.
- **B2.** Adopt the fence plane as atoms. 3.78 MB of adjudicated rulings, currently read by
  nothing. *(closes #4)*
- **B3.** Adopt `research/reviewed/` the same way — house doctrine already requires
  full-fidelity peer reports to land there, and today added 325 KB that only grep can find.
- **B4.** Project the operator's utterances as a retrievable plane. 29.3 MB is too large to
  push whole; the unit is the *steer*, not the sentence. *(closes #3 — and this one needs
  Daniel's judgment about what counts as a steer, so it is specified, not built.)*

**Acceptance:** a seat that has never seen the tree can retrieve the Wave-0 build spec by what
it is about, in one command, without knowing the path.

### Contract C — THE READER: a surface must declare what it reads

The 57.7% defect is not a storage failure. It is a reader matching one field of three and
saying nothing about it. So every retrieval surface declares, in code and in its output:

- **C1.** **Coverage:** which planes, and *which fields of each*, it matches against. A surface
  that reads one field of three must say so. *(closes #1)*

  **The obvious fix is wrong, and the code says why.** "Just project all three fields" was this
  document's first proposal and it would break something deliberate. The comment directly above
  the loop reads: *"`recommendation` is forward-looking advice (a claim), `actual` is an
  observed outcome (evidence), `what_tried` is the action. The reader must be able to tell a
  claim from evidence, so carry the field through (-> `_provenance_tag`)."* Concatenating the
  three destroys exactly that distinction, which is a property worth more than the retrieval
  it would buy.

  **So the contract is to separate matching from display**: one `match_text` spanning all three
  fields, and a `text` that stays the single provenance-tagged field the reader is shown. The
  ranker gets 1.9M characters; the reader still gets told whether it is looking at a claim or
  at evidence. A surface may widen *what it matches*; it may not widen *what it claims to be*.
- **C2.** **A typed zero:** silence names what was searched and why nothing came back —
  `empty` / `UNCHECKABLE` / `error`, never a bare absence. This is the law this house has
  derived six times; here it becomes a surface contract rather than a lesson.
- **C3.** **Edges are rankable:** a plane with a graph is traversable by the ranker, not only
  by a visualiser. *(closes #10/`related_to`, #7/`narrative_chapter`, #8/the T-id edges)*

**Acceptance:** replay the six known derivations of "an absent value is not a negative answer"
through the law register built as C's first instance; it must collide on at least five. That
test is falsifiable and already measured viable (claim-shape fires on 16% of the corpus and on
6 of 6 of the known instances).

---

## 4. The order, and why

0. **The two cheap independent wins, first, today.** Project all three lesson text fields
   (#1 — the largest single retrieval gain available, roughly three lines) and close the
   session-id gap (#6 — one shared resolver, ~7 call sites). Neither depends on anything else
   and both are measured at a known-bad baseline, so both are honestly falsifiable.
1. **Contract A, the address.** A2 first: without one target vocabulary, every join below is
   theoretical.
2. **Contract B, the shelf.** Needs A's address to file against.
3. **Contract C, the reader**, with the law register as its first instance — so the register is
   an instance of the schema rather than a one-off we later discover should have been one.

Wave 1 is unblocked as of today (the `context --stats` gate is met: 24h window, 92.5%
coverage) and runs alongside; this schema does not displace it.

---

## 5. What this document does not settle

- **B4** (what counts as a steer) is Daniel's call, not a seat's.
- The 28 ghost lessons are a *recovery* question, not a schema question. Their bodies may be in
  a backup snapshot; nobody has looked.
- Whether `experiment_name` should become parseable (#11) is deferred: renaming a mutable
  primary key that 790 edges and 1,562 counter rows point at is a migration, and the address
  contract (A) makes it unnecessary for retrieval.
- This document is itself subject to the problem it describes. It is a loose file in `docs/`.
  Under Contract B it should be an atom, and the measure of whether B worked is whether a seat
  that has not read this conversation can find it.
