# The Library Schema — the file plane is a store (opening expansion, claude)

Status: design draft (round doc — supersedes nothing; EXTENDS repo-organization-opening-claude-2026-07-21.md)
Type: design (opening) · Arc: repo-organization/library-schema · Seats: claude → deepseek, kimi · Date: 2026-07-21

**Charter (Daniel, verbatim):** "Lets consolidate and compile as would be best to preserve the
intention of the files as well as codifying our best practices for going forward … I want our
documentation to be robust and categorized in a way that makes sense for an ever expanding library
like aurora. having a schema for storage and retrieval will make it easier for us to both trace our
steps. We will be able to know both where to find what we are looking for instantly, but we will
know how to categorize and seed appropriately too. this too is a form of ergonomics."

---

## 1 · The unifying claim

Aurora already solved storage-and-retrieval once — for machine knowledge. Immutable atoms, typed
families, supersession-by-title, regenerable projections, recall at the moment of need. **The file
library is the HUMAN plane of the same knowledge system, and it should obey the same physics.**
One schema, two planes:

| Law (already proven on the Redis plane) | File-plane equivalent |
|---|---|
| Atoms are typed at birth | every doc declares its TYPE in a 4-line header |
| Atoms are immutable; supersession, not mutation | dated docs never rewritten; successors stamp `superseded by` |
| Resources are regenerable projections over atoms | INDEX/MAP/shelves are GENERATED, never hand-groomed |
| Recall surfaces the right atom at the right moment | docs join the recall plane via their headers |
| Consolidation compresses without losing faithfulness | gate-time consolidation writes a reconciled successor; ancestors fossilize honestly |

Nothing new to invent — the library inherits laws the substrate already earned.

## 2 · Shelf vs catalog (the library-science law that ends folder agony)

A shelf is one-dimensional: a book stands in exactly ONE place. A catalog is multi-dimensional:
the same book is findable by author, subject, and era. Every "which folder does this go in?"
agony is an attempt to make the shelf do the catalog's job — it cannot (Ranganathan's faceted
classification, 1933; the answer is a century old).

**LAW: the path encodes exactly ONE facet — the document's TYPE (+ date + slug). Every other
facet (arc, seats, subsystem, status) lives in the header, and generated catalogs serve them.**
Never re-shelve to re-categorize; regenerate the catalog. This is why the schema survives an
ever-expanding library: filing is O(1) (type → home, zero judgment), and finding is O(1) through
whichever facet you remember.

## 3 · The type system (genus → home → lifecycle → door)

| TYPE | What it is | Home | Mutability | Primary door |
|---|---|---|---|---|
| **contract** | living law (AGENTS, LEXICON, LIVE_CONSTRAINTS, method-baseline) | `docs/UPPERCASE.md` (+ repo root) | superseded in place, guarded | INDEX L1 |
| **map** | generated projection (MODULE_INDEX, MAP, PHYSICS, DOORS) | `docs/UPPERCASE.md` | regenerated ONLY | its generator |
| **design** | point-in-time position/counter/reconciliation/spec | `research/drafts/` → reconciled to `docs/<topic>-<date>.md` | immutable once reconciled | arc-thread |
| **brief** | work order to a seat | `research/briefs/` | immutable | arc-thread |
| **report** | verbatim evidence (fences, reviews, walks, frontier sweeps) | `research/reviewed/` | immutable (verbatim doctrine) | arc-thread + recall |
| **chronicle** | narrative (JOURNEY, FOSSILS, reflections, story) | `chronicles/` + `docs/JOURNEY.md` | append-only | story door |
| **ledger** | living append/flip lists (WISHLIST, failure-ledger, tasks) | `docs/` | append + flip, guarded | boot render |
| **agent-contract** | per-seat CHARTER | `charters/<agent>/` | amended with version | fleet door |
| **skill** | harness skill | `.agents/skills/` | versioned | harness |
| **pin** | behavioral spec test | `tests/` | permanent | suite-baseline |
| **receipt** | ephemeral runtime output (play runs, logs, pytest out) | `scratch/`, `data/play/*/runs/`, `*.log` | disposable | none — TTL/gitignore |

Prior-art nods, and where we diverge: Diátaxis's four quadrants are for USER documentation; our
library is an engineering MEMORY, so lifecycle (living/point-in-time/append-only/ephemeral) is the
primary axis, not audience task. ADR practice contributes the immutable-decision + supersession
stamp. Zettelkasten contributes stable IDs + links. Faceted classification contributes §2.

## 4 · The header contract (atoms self-describe; seeding becomes mechanical)

Formalize the existing `Status:` convention into four machine-checkable lines at the top of every
non-generated doc:

```
Status: current | superseded by <path> | fossil
Type: design (counter) · Arc: T094 / library-schema · Seats: claude,deepseek · Date: 2026-07-21
```

**The seeding rule Daniel asked for: a document is born with its header, and its Type decides its
home.** No judgment at file time, ever. Optional door: `py agent_cli.py doc new --type design
--arc T0xx --topic <slug>` stamps the header, names the file by canon, and puts it in the right
place — the "where does this go?" question stops existing.

## 5 · Retrieval: four doors, all cheap

1. **Shelf** — INDEX.md stays the hand-curated one-screen L1 (living set only). Below it,
   GENERATED per-type shelves (`gen_library.py`, sibling of gen_master_map) — the projection can't rot.
2. **Arc-thread** — `py agent_cli.py arc T094` → every brief, design, report, pin, commit, note,
   and lesson that cites the arc, in order. **This is "trace our steps," materialized.** Cheap to
   build: names + headers + commit messages already carry arc ids; a generator greps and threads.
3. **Recall** — headers make docs first-class recall citizens: boot and recall-at surface the
   contract/design you need at the moment you touch its subsystem (the knowledge-map already
   walks these paths; headers give it types to rank with).
4. **Name** — the naming canon makes paths guessable: `<seat>-<topic>-<kind>-<date>.md`. If you
   can say what you want, you can nearly type its path.

## 6 · Why this scales (the cache hierarchy is the expansion strategy)

- **L1 — the living set** (contracts + maps): stays ~constant size, one screen, always hot.
- **L2 — active arcs**: dated docs of work in flight; hot while the arc is open.
- **L3 — cold history**: everything reconciled, superseded, or fossilized; append-forever,
  findable through the catalogs, never in the way.

Consolidation at gates DEMOTES L2→L3: write the reconciled successor, stamp ancestors
`superseded by`, fossilize the abandoned. **Intention is preserved by construction** — the
successor carries the intent forward; the ancestors keep the full reasoning trail; nothing is
deleted. Growth all lands in L3, so the library expands forever while the working set stays
one screen. (MDL-under-faithfulness, on the file plane.)

## 7 · Guards — a schema is real only if enforced

- check_boundaries: **rule-8** mojibake scan (`â€ Ã— â† Â§` classes) · **rule-9** probes never in
  `tests/` · **rule-10** header contract on new docs · **rule-11** home-matches-type ·
  **rule-12** repo-root allowlist.
- UTF-8 forced at every write door (the second-bite lesson: encoding is a door property, not a
  discipline property).
- `wrap` census: new docs without headers, listed at session end.
- boot: one library-drift line (like suite drift) — "N docs missing headers, M unfiled".

## 8 · The concrete first pass (this week, all gated by Daniel)

1. Ratify the type table + header contract (this round's reconciliation).
2. Commit-by-name the ~60 untracked research/charter/skill files (typed census attached at
   reconcile; research persists by doctrine).
3. INDEX re-render + first generated shelves.
4. Land guards 8–12 + UTF-8 at doors (fenced build).
5. Junk executions (stray `E:` dir with prehistory parked to `_archive/prehistory/`,
   `data/play/test/`, probe tests, root probe jsons).
6. Headers backfill: NEW docs from ratification day forward are born with headers; backfill old
   docs lazily (when touched) — never a big-bang rewrite.

## 9 · Counters wanted

- **deepseek** (builder eyes): enforcement cost of rules 8–12; who owns the generators; play/receipt
  TTL mechanics; UTF-8 at YOUR write door; does the header contract fight the runner's writes?
- **kimi** (taxonomy eyes): holes in the type table; the stranger test (can a newcomer file + find
  without asking?); naming-canon collisions ("charter" ambiguity); is the L1 one-screen bar right?
- **Both**: is ONE path facet (type) correct, or do arcs deserve directories? (My kill-test: show
  a retrieval that folders-by-arc serves and the arc-thread door cannot.)

Protocol: counters → reconcile to `docs/library-schema-2026-07.md` → Daniel ratifies → the law
lands as **`docs/LIBRARY.md` (living contract)** + generators + guards. Daniel gates: ratification,
all deletions, the bulk commit, any tracked-path move.
