# Teardown card: THE KNOWLEDGE PLANES (where findings live, and whether anyone can find them again)

Date: 2026-10-13. Seat: Vandor (claude), a read-only subagent of the "deconstruct the house" run.
Method: `teardown-card.md` (draft v1). All eight rows are filled. Every claim carries a label (observed /
inferred / unknown) and a pointer. Loop altitude follows `docs/pillar-analysis-method.md`.

**Scope.** This card covers:
- the library: typed atoms, their projections under `docs/library/`, the generated shelves, and the four doors;
- the eye: the transcript index `state/eye/eye.db` and its verbs find, freq, standing and trace (the trace
  walks the connectome);
- `research/`: the in-flight, reviewed, drafts and briefs zones;
- `fences/`;
- notes, plus the `chronicles/memory.md` digest built from them;
- the story atlas and `chronicles/`;
- `knowledge-map` and `lookback`;
- `docs/FOSSILS.md`;
- the path a finding takes from a chat into one of these places.

Lessons and recall have their own cards (`card-memory-core.md`, `card-recall.md`). I touch them only where a
knowledge plane depends on them.

**Prior work this card stands on, and does not repeat.** Two documents already studied the same territory:
- `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md` (2026-10-01) measured reach.
- `docs/THE-FILING-SCHEMA.md` (2026-10-03, from the six-agent census in
  `research/reviewed/knowledge-plane-census-2026-10-03.md`) found that "we do not have a filing problem, we
  have a reading problem".

This card checks what has changed since then, and it adds two axes those documents did not measure:
**freshness** (do the maps keep up with the corpus?) and **provenance** (does a reader know whose words it
is reading, and which population it is searching?).

**What I did NOT change.** I made no edits to house files except this card. I ran no generator in write
mode, no note, learn, wrap, `notes --project`, `story --chronicle`, `eye ingest` or `eye go`. Side effects I
could not avoid, listed so nobody mistakes them for organic traffic:
- (a) Every eye read opens `eye.db` through `_connect` (`core/eye/index.py:456-530`). That function runs
  `CREATE TABLE IF NOT EXISTS` and rewrites one `meta` row on every open. It is idempotent: no content
  changes, but the file's timestamp moves. I made about ten eye calls.
- (b) I ran `knowledge-map` and `lookback` with their own kill switches set (`AKASHIC_KMAP_NO_COUNT=1`,
  `AKASHIC_LOOKBACK_NO_COUNT=1`), so their funnel counters did not move.
- (c) The user-level recall-at hook fired on my own shell calls. That is the same side effect the recall card
  reports.
- (d) My eye reads went through the command-line door and through read-only SQLite (`mode=ro`). **Neither is
  recorded in the eye's disclosure log** (finding F9 below). I am disclosing them here instead:
  - freq on "deconstruct the house", "reverse engineer | first principles" and "second press";
  - find on "second press", "second-press", "escalating hints" and "never reaches him";
  - standing, stats and overview;
  - SQL counts of the voice and subagent columns.
- (e) Privacy. I did not open `private/`, Daniel's personal memory, the story oracle, playing data or the
  shader corpus. Some store-only atoms are, at least in part, private-plane records. I describe them by role
  only (corrected at review: an earlier draft gave their count and dates). Their ids, titles, counts and dates
  are themselves a leak: "existence metadata is a leak" (`core/trust/private_plane.py:17-19`).

---

## The picture in one paragraph (for Daniel)

Think of the knowledge planes as the house's **storage subsystem**.

| storage part | what it is in the house |
|---|---|
| a journaled disk | the library atoms: the JSONL files in `store/docs/` are the write-ahead journal, Redis is the RAM cache, and the `docs/library/*.md` projections are the file-system view you browse |
| the file-allocation table and the search indexer | the generated shelves (`docs/SHELVES.md`, `docs/ARCS.md`, the zone READMEs) |
| the flight data recorder | the eye: it records every word of every session and rebuilds its full-text index once a day |
| the scratch tier and the archive tier | `research/in-flight` and `research/reviewed` |
| the chip's published errata sheet | `docs/FOSSILS.md`: the known-bad designs, so nobody repeats them |
| on-demand search, nothing prefetched | `knowledge-map` and `lookback` |

**Thesis.** The disk itself is healthy: every one of 1,028 atom bodies rehashes clean, and nothing is
corrupt. What has decayed is the layer *around* the disk:
- **The maps rebuild only when someone remembers to run the indexer.** The shelves are 6 days and 105 commits
  stale, the story atlas is 11 days stale, and the errata sheet is 95 days stale.
- **Three readers point at the wrong population.**
  - The directive watcher checks lessons against a six-line June stub file.
  - The eye's "his voice" axis counts dispatched subagent briefs as Daniel (22.8% of "operator" rows).
  - Lookback reads reviewed research by its first 80 characters, and in-flight research not at all.
- **Twice, a fix that landed in one organ never reached its twin organ.**

The cache is coherent. The directory is stale, and some of the people reading it are reading the wrong drive.

---

## Row 1: Purpose

- **What it is for.** It turns what was said and decided into something a later seat (or Daniel) can find,
  trust and act on.
  - The library law's charter, in Daniel's words: "know where to find what we are looking for instantly …
    know how to categorize and seed appropriately too".
  - **observed**: `docs/LIBRARY.md:5-8`.
  - The eye's founding purpose: to stop "the class of loss it was built to answer" (directives Daniel gave
    that no durable plane kept).
  - **observed**: `agent_cli.py eye --help` (the `standing` line); `core/eye/directives.py:287-296`.
- **For whom.**
  - Every seat, through the doors.
  - Daniel, through the rendered artifacts and the docs.
  - Future contributors to a public repo (Apache-2.0).
  - **observed**: `AGENTS.md` (the two doors); `docs/FOSSILS.md:5-11` ("future contributors (human or agent)
    can learn from these experiments without repeating them").
- **What outcome would make it worth keeping.** "The right information needs to live in the right place"
  (Daniel, quoted in `docs/THE-FILING-SCHEMA.md:3-6`).
  - In storage terms, the measure is **retrieval at the moment of need**, not capacity.
  - The filing-schema census already measured that the shelf exists and is well formed. Its open problem is
    readers. **observed**: `docs/THE-FILING-SCHEMA.md:17-35`.

## Row 2: Observables (what we can see without trusting its self-description)

Numbers are from the live house, 2026-10-13, about 13:30 UTC.

| what | value | where it came from |
|---|---|---|
| atom record (journal) | 1,386 lines → 1,028 unique atoms. By type: report 597, design 326, brief 58, chronicle 28, map 7, contract 6, ruling 6 | my replay of `store/docs/*.jsonl` (latest version wins, same rule as `atoms.py:439-441`) |
| atom status | current 556, draft 408, fossil 60, superseded 4 | same replay |
| atom origin | migrated 662, authored 364, conversation 2. 884 of 1,028 carry no arc (86%) | same replay |
| atoms minted per month | Jun 10, **Jul 713**, Aug 193, Sep 90, **Oct 22** | same replay (header dates) |
| projections on disk | 1,024 `.md` files under `docs/library/` | directory listing |
| projection integrity | `--verify`: 1,028 bodies rehashed, **0 corrupt, 0 sha-drift**, 14 orphans, and a small "missing" count (store atoms with no projection; it includes the private overlay, so the number is withheld) | `py scripts/generators/gen_library.py --verify` (read-only path, `gen_library.py:591-592`) |
| store vs journal | the store index and the journal hold the same **number** of ids, **but not the same ids**: some public journal atoms (dated 07-29) have no store key, and the store holds atoms the journal lacks (at least partly the private overlay; counts withheld) | Redis `ZRANGE artifact:index:all` diffed against the replay |
| shelf freshness | `SHELVES.md`, `ARCS.md`, zone READMEs generated **2026-10-07 06:46 UTC**. 105 commits since. 0 of 5 atoms minted after that time appear on SHELVES | file headers; `git rev-list --count --since=2026-10-07T07:00 HEAD`; grep |
| story atlas | generated 2026-10-02. Main track `ai-setup`: **4,178 beats, 0 chapters**. `story --at` finds no chapter for 2026-09-20 or 2026-10-12. Lifetime `chronicle:run` = 5 | `py agent_cli.py story`, `story --track ai-setup`, `story --at …`; Redis hash `narr:health` |
| eye corpus | 61,036 events, 2,237 sessions. By voice: operator 9,616, agent 36,595, system 14,825. Time-fog 1.9% | `py agent_cli.py eye stats` |
| eye freshness | newest event 2026-10-12 12:12 local. Daily ingest at 16:20 UTC. 1 persistent address collision ("LOST") | read-only SQL on `eye.db`; `state/eye/ingest-receipts/2026-10.jsonl` |
| "operator" rows from subagent transcripts | **2,193 of 9,616 (22.8%)** | read-only SQL: `voice='operator' AND is_subagent=1` |
| eye use via the tool door | 396 disclosed reads, 2026-08-17 → today. kimi 175, deepseek-family 218, sol 2 | `state/coord/corpus_reads.jsonl` |
| knowledge-map / lookback use, all time | `knowledge_map:queries` 46, `lookback:queries` 29 (compare recall's 28,847 surfacings in `card-recall.md`) | Redis GET |
| research zones | in-flight 967 files (522 `.md`, 38 MB). reviewed 247 files (179 `.md`, 15 MB; 131 at top level). drafts 39. briefs 4 | `find`, `du` |
| fences | 33 rounds, 24 reconciliation files | `ls fences` |
| notes | 1,249 active. Scratch notes: kimi 276, deepseek 238. `where-we-are` chain 227 records. 3.2 M characters | `py agent_cli.py notes --json --limit 5000` |
| FOSSILS.md | 7 entries (F1–F7), all June–July. Last commit 2026-07-09 (2 commits ever). 60 atoms carry status `fossil` | `docs/FOSSILS.md`; `git log -- docs/FOSSILS.md`; replay |
| doc currency | 17 stale-current warnings (FOSSILS 95 d, LIBRARY 80 d, PRINCIPLES 95 d …) and 17 failures (15 unstamped or unrecognised vocabulary, 2 untracked, one of them today's story-layer atom projection) | `py scripts/checkers/check_doc_currency.py` (read-only: git log and ls-files only) |

## Row 3: Mechanism (how inputs become what we observe)

### 3.1 The library (typed atoms)

**The write path.** `doc new` or `doc adopt` calls `AtomFamily.mint`. One mint does three things:
- writes the atom as JSON to the store under `artifact:<id>`;
- adds the id to index sets: type, status, arc, category, cited-by and supersedes;
- appends one line to `store/docs/<type>.jsonl` (tracked in git).

**observed**: `core/library/atoms.py:151-205`. A projection renderer then writes one read-only `.md` file
with YAML frontmatter. Its `akashic_sha` field lets the file self-verify against the atom body. **observed**:
`core/library/projection.py:49-118`.

**The path law.** A path encodes only type, date and slug ("one-facet law"). Arc, category and status live in
the header. **observed**: `docs/LIBRARY.md:11-14`; `projection.py:88-92`.

**Supersession.** It never deletes. The successor is minted first, then the ancestor is flipped by
compare-and-swap. `resolve_current` walks forward through `superseded`; `lineage` walks backward through
`supersedes`. **observed**: `atoms.py:221-262`, `376-407`.

**The four finding doors** (`LIBRARY.md:57-64`):
- **(1) Shelf.** The hand-curated `INDEX.md`, plus the generated `SHELVES.md`.
- **(2) Arc-thread.** Defined as an `arc <id>` verb.
  - **observed**: no such verb exists. `py agent_cli.py arc` returns "invalid choice". Only the generated
    `ARCS.md` file serves this door. `doc arc` exists, but it *relabels* an atom's arc; it does not read one.
- **(3) Recall.** Lessons only (see 3.5). Atoms reach the text-ranked doors as projection files, never by
  their typed facets. **observed**: `core/recall/lookback.py:178-251` (`_library_paths`, `_docs_items`).
- **(4) Name.** The naming canon.

**The maps.** `scripts/generators/gen_library.py` builds SHELVES, ARCS and the zone READMEs. Nothing calls it
on a schedule or a hook.
- **observed**, bounded search: no reference in `scripts/mirror.py`, `scripts/githooks/`, or any
  `.py/.ps1/.json/.toml/.cmd/.bat/.yml` caller. The Task Scheduler entries `AkashicAurora-*` contain no
  library task.
- Its own `--one` message says "full regen at mirror catches up" (`gen_library.py:608`). **observed**:
  `mirror.py` contains no `gen_library` reference.

### 3.2 The eye (the flight recorder)

**Ingest.** `eye ingest` reads every session transcript, incrementally by (modification time, line
cursor), into SQLite with an FTS5 full-text table. Each event gets an address `<session>:<line>`. Every event
is labelled with a voice (operator / agent / system). A user record that contains harness markers is labelled
system. **observed**: `core/eye/index.py:1-17`, `34-50`, `724-860`.

**Schedule.** Ingest runs daily as `AkashicAurora-EyeIngest-Daily` at 16:20 UTC. **observed**: receipts file;
`Get-ScheduledTask`.

**The connectome edges.** They are rebuilt on every ingest, so `trace` never answers with yesterday's
ancestry. **observed**: `agent_cli.py:2728-2732`.

**Readers:**
- `find` (phrase plus facets);
- `freq` (a pattern family becomes a verdict: unheard, mentioned-once, recurring, standing-directive);
- `standing`: recurring operator phrases that no durable plane cites. It proposes and files nothing;
- `zoom`, `trace`, `look`.

**observed**: `agent_cli.py:2721-3040`; `core/eye/index.py:941-1017`; `core/eye/directives.py:139-343`.

**Disclosure.** Reads through the tool door are appended to `state/coord/corpus_reads.jsonl`. The code
comment says "the operator can see every query run against his transcripts". **observed**:
`core/comm/toolbox.py:600-630`.

### 3.3 research/

`research/README.md` documents two lifecycles:
- the research-day loop: queue → drafts → reviewed;
- the fleet-round loop: briefs → drafts → reviewed, then reconciliations "graduate OUT to docs/".

**observed**: `research/README.md:9-26`, `86-96`.

**The largest zone is missing from that README.** `in-flight/` holds 967 files and 38 MB. It is not
mentioned in the README, nor in `docs/LIBRARY.md`. **observed**: grep for "in-flight" in both files returns
nothing.

**Yet in-flight is where build specs live.** Code names in-flight files as its SPEC. **observed**:
- `core/coord/target.py:3-4` (`context-system-navi-m1.md`, sealed);
- `core/coord/scene.py:3`;
- `core/comm/bridge_seal.py:3`;
- `core/eye/__init__.py:3` (the eye's own design);
- `arsenal/shaders/atlas_build.py:66-67` (today's shader school).

### 3.4 Fences, notes, chronicles, the story

- **Fences.** `fences/<round>/` hold briefs, blind halves and reconciliations. Since 2026-10-07 they are a
  lookback and knowledge-map layer, ranked second, right after docs. **observed**: `lookback.py:553-563`;
  `THE-FILING-SCHEMA.md:131-135`.
- **Notes.**
  - Notes are Redis records (`mem:decision:ADR_*`), write-once by title, superseded by re-noting.
  - `notes --project` regenerates the tracked digest `chronicles/memory.md` (last regenerated 2026-10-12
    05:00).
  - **observed**: `notes --help`; file timestamp.
- **The story.**
  - Beats are distilled into chapters by `Chronicler.chronicle_all`.
  - That runs only from `story --chronicle` / `--mark`, `end_session`, or `seed_narrative.py`.
  - **observed**: grep `chronicle_all(`; `core/narrative/session.py:43-51`.
  - No session is open (`narr:session:open` is empty), and nothing scheduled runs it. **observed**: Redis
    GET; task list.
- **The curated stories** (`docs/THE-STRING-THROUGH-THE-FOREST.md`, the reach map) are typed `report` and
  live in `docs/`. The type law says "Story, reflection, journey → chronicle → `chronicles/`". **observed**:
  `LIBRARY.md:40`; those files' header lines.

### 3.5 The search doors (pull only)

- **`recall "<words>"`.** Keyword search over **lessons only**. **observed**: `agent_cli.py:836-880`.
- **`lookback`.** Eight layers in this order: docs, fences, charters, research, notes, promoted, chapters,
  git. **observed**: `lookback.py:553-555`. Its research layer reads **only top-level `research/reviewed/*.md`,
  only the first 80 characters** of each. **observed**: `lookback.py:458-476` (`_read_head(p, 80)`).
- **`knowledge-map`.** Lessons with their `related_to` edges, plus notes, docs, fences and charters. **No
  research layer at all.** **observed**: `core/recall/knowledge_map.py:208-230` (imports `_docs_items`,
  `_note_items`, `_fence_items`, `_charter_items`; not `_research_items`).
- **The archive rule.** Both doors read a doc's status from its first 12 lines. They know current,
  superseded and historical; anything else reads as "unstamped". The archive layer's set is retired,
  superseded, historical, benched and graduated. **observed**: `lookback.py:156-167`;
  `knowledge_map.py:38-39`.
  - The atom vocabulary adds `draft` and `fossil`, which neither door understands. So a projection stamped
    `status: fossil` ranks as "unstamped" (importance 2, above historical's 1) and lands on the **live
    surface**.
  - **inferred** from the two code sites; **verified** by V11 below.
- **`context`.** "One anchor, every plane". Its planes are git, touches, lessons, authorship, locks and focus.
  None of this card's planes is among them. **observed**: `core/coord/scene.py:47`.

### 3.6 How a finding travels from a chat to a durable place (the write path)

```
chat (L1 register: gone when the session compacts or ends)
  |-- passive, always: transcript file --(daily 16:20 UTC)--> eye.db   [lag up to ~24 h]
  |-- active, seat's choice:
  |     learn  -> lesson (Redis)               -> pushed by recall-at    (the only push path)
  |     note   -> mem:decision (Redis)          -> boot / notes / knowledge-map (pull)
  |     write  -> research/in-flight/*.md       -> grep only (no door reads it)
  |     write  -> research/reviewed/*.md        -> lookback, title only (80 chars)
  |     fence  -> fences/<round>/               -> lookback + knowledge-map (since 10-07)
  |     doc new/adopt -> atom + journal + projection -> text doors; shelves only after a manual regen
  |     edit   -> docs/UPPERCASE.md             -> lookback, knowledge-map, INDEX if hand-added
  |-- curated, rare: FOSSILS.md row, chronicle atom, the rendered artifact pages
```

**observed** for each arrow (pointers in 3.1–3.5).

**inferred**: the only automatic arrow is chat → eye. Every other arrow needs a seat to *decide* to write, and
then a *second* decision (a manual regeneration, a hand edit of INDEX, a FOSSILS row) for the finding to show
up on a map.

**A worked example: today's ask.** Daniel's 2026-10-13 message is:
- **not yet** in the eye (`eye freq "deconstruct the house"` → UNHEARD; the newest indexed event is 10-12
  12:12);
- present as a file in `research/in-flight/deconstruct-the-house-2026-10-13/`, which no door reads;
- adjacent to a deepseek scratch note dated today, about the related reverse-engineering suite (I did not
  open it to check whether it carries his words).

**observed**: the commands above; the `notes` listing.

## Row 4: First principles (each tested: can you name the evidence or law it rests on?)

| # | principle | label | evidence or law | axiom or assumption? |
|---|---|---|---|---|
| P1 | Knowledge has value only at the moment it is read. A plane without a reader is pure cost. | inferred | the census: "in plane after plane, nothing reads it" (`THE-FILING-SCHEMA.md:19-35`); 46 and 29 lifetime queries on the two map doors | law-like (it is the definition of retrieval value). Measured here, not assumed. |
| P2 | Append-only with supersession, never deletion. Meaning is never destroyed, only stamped. | observed | `atoms.py:7-13`, `221-262`; `LIBRARY.md:66-72` ("never delete meaning") | **operator value** (Daniel's), held deliberately. Its evidence is the house's own history (F1–F7 were kept because they teach). |
| P3 | A generated view is only as fresh as its last regeneration. A cache with no invalidation trigger goes stale silently. | observed | cache coherence (hardware law); SHELVES 6 days and 105 commits behind; the story atlas 11 days | **law** |
| P4 | A path should encode one facet only, so re-categorising never moves a file. | observed | `LIBRARY.md:11-14`; FOSSILS F7 ("mine, don't invent") | **assumption with evidence**: a design choice, defended by the F7 fossil. It holds: I found no re-shelving. |
| P5 | A count without its population is not evidence. Ask a detector what it searched before trusting its silence. | observed | `core/recall/staleness.py:152-156` (the six-record stub incident); `THE-FILING-SCHEMA.md` C2 ("a typed zero") | **law the house derived** (it says six times). Violated twice in this subsystem (F1, F2). |
| P6 | Whose words a record carries is part of its truth. A brief from an agent is not the operator speaking. | observed | `directives.py:144-157` (the authorship fix, RED a5afd360); the eye's voice law (`index.py:6-9`) | **operator value** (provenance), with a measured cost when broken (22.8%). |
| P7 | The repo is public, so private material must stay out of every tracked plane, *including its titles and ids*. | observed | `private_plane.py:3-20` (Daniel's ruling 2026-08-16; "existence metadata is a leak") | **constraint** (licence plus the operator's ruling) |
| P8 | The journal (JSONL in git) is the recovery truth. `rebuild()` restores the store from it. | observed | `atoms.py:8-13`, `411-452` | **assumption, now scoped**: true for the public plane only. Private atoms are store-only by design (`private_plane.py:34-44`: "private is an OVERLAY"), and some public journal atoms are absent from the store. Trap 1 if stated unscoped. |
| P9 | The shelf "can't rot, carries its timestamp". | observed (the claim) | `LIBRARY.md:59-60` | **false first principle (trap 1)**. It carries its timestamp, true. It rots: nothing regenerates it. |

## Row 5: Capabilities (what you need to HAVE to build or run it)

| capability | used for | label |
|---|---|---|
| Redis on 16379 (db 0) | the atom store and indexes, notes, the narrative store, funnel counters | observed (all reads above) |
| git plus a tracked JSONL journal | atom durability and history; doc currency (the last-touch age) | observed (`atoms.py:117-122`; `check_doc_currency.py:60-75`) |
| SQLite with FTS5, write-ahead logging, a 180 s busy timeout | the eye (421 MB `eye.db`) | observed (`index.py:456-530`; file size) |
| Windows Task Scheduler | the only automatic refresh (eye ingest daily, transcript archive daily, wishlist weekly) | observed (`Get-ScheduledTask`) |
| transcript files from every harness (Claude Code, DSH, workflow journals, subagents) | the eye's raw material | observed (`index.py:56-80`; ingest receipt: 2,379 files found) |
| seats willing to write (learn, note, doc, fence) | every active arrow in 3.6 | observed (the notes counts; mint rate) |
| a cross-model fence habit (blind halves plus a reconciliation) | the rulings that govern code | observed (`fences/`, 24 reconciliations) |
| Daniel's gate | ratifying the law, growing the category roster, B4 (what counts as a steer), deletions | observed (`LIBRARY.md:91-93`, `144`; `THE-FILING-SCHEMA.md:224`) |
| a privacy overlay (`private/` plus a commit-time backstop) | keeping a public repo safe | observed (docstring); **unknown** whether it fires on a regeneration (not testable read-only) |

## Row 6: Required steps (rebuild from nothing; what blocks what)

1. **Decide the planes and their type law** (what goes where). Blocks everything. *(Exists: LIBRARY v1.3.)*
2. **The durable record:** journal plus store for atoms; `eye.db` for speech; files for research and fences.
   Blocks 3–6. *(Exists, healthy: 0 corrupt.)*
3. **Capture doors** (doc new/adopt, note, fence, eye ingest). Needs 2. *(Exist. Eye ingest is the only
   automatic one.)*
4. **Projections and maps** (library `.md`, SHELVES, ARCS, the story atlas, `memory.md`). Needs 2.
   *(Exist.)*
5. **Freshness triggers.** Regenerate 4 when 2 changes: on write, on a schedule, or at least *print the age
   where readers look*. Needs 4. **← the missing link on the critical path.**
6. **Readers aimed at the right population** (every door states which planes, which fields and whose voice
   it reads). Needs 2. *(Partly exists, three readers mis-aimed.)*
7. **Feedback** (was this find useful? promote, fossilise, supersede). Needs 6. *(Counters exist; there is no
   usefulness signal for docs or atoms. `eye look` itself prints "credit UNKNOWN (this plane has no
   funnel)", `agent_cli.py:2885`.)*
8. **Negative knowledge curation** (the errata sheet). Needs 7. *(Frozen since 07-09.)*

**Critical path:** 2 → 5 → 6 → 7. The house built 1–4 thoroughly and 6 partly. Step 5 is what makes 4
trustworthy; without it, every map is a photograph. **inferred** from rows 2 and 3.

## Row 7: Invariants and failure modes

| invariant (what must always hold) | holds? | what a break looks like from outside | label / pointer |
|---|---|---|---|
| I1. Every public atom has exactly one projection whose body sha matches | **holds** for content (0 sha-drift, 0 corrupt); 14 orphan projections; a few "missing" (the private overlay among them) | an orphan reads as library truth with no atom behind it | observed: `--verify` |
| I2. A projection's header tells the atom's current status | **breaks once**: one public projection says `current` for an atom the store and journal mark `superseded` (Heimdall web-door requirements, 2b7021) | a reader trusts a superseded requirement as live; `--verify` reports CLEAN for it because it checks only the body sha | observed: my diff of projection frontmatter vs the replay; `gen_library.py:538-543` (sha only) |
| I3. Journal replay equals the store | **breaks both ways**: store-only atoms (at least partly the deliberate private overlay; described by role only) and public journal-only atoms (dated 07-29; no store key, no status index) | equal totals hide it. Store-reading doors (`AtomFamily.find`, the `continuity` artifacts source) do not see the journal-only atoms | observed: ZRANGE diff; inferred (the cause of the 07-29 journal-only atoms): **unknown** |
| I4. Supersession is walkable both ways | **breaks 3 of 4**: only 1 successor carries `supersedes`; 3 ancestors point forward to successors that do not point back | `lineage()` from a successor misses its ancestor (`atoms.py:376-394`) | observed: replay |
| I5. Generated maps are fresh against the corpus | **breaks**: SHELVES/ARCS 6 days, 105 commits; 0 of 5 later atoms listed; the story atlas 11 days, main track 0 chapters | a stale map is indistinguishable from a complete one unless you read its timestamp line | observed (row 2) |
| I6. "operator" means Daniel | **breaks in `freq` and `stats`** (22.8% of operator rows are subagent briefs); **holds in `standing`** (it filters `is_subagent`) | a verdict credits Daniel with words an agent wrote. Example: `freq "second press"` → MENTIONED-ONCE, and that one "operator" utterance is in a subagent transcript (`agent-a81…`, `is_subagent=1`) | observed: `index.py:976-1010` (no filter) vs `directives.py:158-162` (filter); SQL |
| I7. A detector searches the population it claims | **breaks twice**: (a) `standing` checks lessons in `session_logs/learnings.jsonl` (6 lines, last written 2026-06-20) instead of the LearningStore; (b) its `for sub in ("docs/library","docs")` loop `break`s after the first, so top-level `docs/`, `research/`, `fences/` and notes are never read; its docstring also promises "recent commit subjects", which no code collects | false "unheeded" items, a watcher that cries wolf and gets ignored | observed: `directives.py:320-343`; file stats; V2 |
| I8. Every `docs/*.md` carries one status vocabulary | **breaks**: three vocabularies. LIBRARY says `current / superseded by / fossil`; the checker says `current / superseded-by / historical`; atoms say `current / draft / superseded / fossil`. 17 currency failures | fossil and draft atoms read as "unstamped" and rank on the live surface (V11) | observed: `LIBRARY.md:19`; `check_doc_currency.py:49-56`; `atoms.py:33` |
| I9. Every read of Daniel's transcripts is disclosed | **breaks for the command-line door**: only the tool door appends to `corpus_reads.jsonl`; my ~10 CLI reads left no line | the disclosure promise holds for one door of two | observed: `toolbox.py:612-630`; 0 matches for my queries in the log |
| I10. Negative knowledge is recorded when a design is falsified | **breaks**: contracts A1 and A2 were withdrawn on 2026-10-06, "falsified … additionally by measurement" (`THE-FILING-SCHEMA.md:110-135`); FOSSILS.md has no row for them; 60 atoms carry status `fossil` | the errata sheet reads as complete at 7 entries | observed |

**The common failure signature.** Silence, not errors. Every broken invariant above presents as
"nothing to report": a clean verify, an equal count, a quiet map, a confident verdict. **inferred** from
I2–I10.

## Row 8: Verification (predictions that could fail, the cheapest test, what happened)

Each prediction was stated before its command ran. Where I asked an open question instead, I say so and do
not count it.

| # | prediction | test | result | held? |
|---|---|---|---|---|
| V1 | The currency checker flags FOSSILS.md as stamped current but untouched for over 45 days | `py scripts/checkers/check_doc_currency.py` | "FOSSILS.md -- claims current, untouched 95d" (plus 16 more warnings and 17 failures) | **held** |
| V2 | If `standing` reads only its two files plus `docs/library`, then `durable_sources` = 2 + 1,024 = **1,026** exactly (no top-level docs, no commit subjects) | `py agent_cli.py eye standing --json --limit 5` | `durable_sources 1026`, checked 69, withheld 28. Its #1 "standing directive" (34 sessions) is the Discord spawn wrapper text, not Daniel | **held** |
| V3 | The store's atom index count equals the journal's unique ids | Redis `ZCARD artifact:index:all` vs the replay | equal totals. **But the members differ in both directions.** The test was too weak: it checked the total, not the members (trap 5) | **held, and misleading** |
| V4 | The map doors are rarely used next to recall | Redis GET on the funnel counters | knowledge-map 46 queries ever, lookback 29 ever (recall: 28,847 surfacings) | **held** |
| V5 | `--verify` (read-only) finds 0 corrupt, 0 sha-drift, a predicted small number missing, about 14 orphans | `py scripts/generators/gen_library.py --verify` | exact on all four counts (0 / 0 / the missing count, withheld because it includes the private overlay / 14); 1,028 bodies rehashed | **held** |
| V6 | The story atlas lags the notes plane | `py agent_cli.py story`; `story --track ai-setup`; `story --at …` | generated 2026-10-02; the main track has 4,178 beats and 0 chapters; no chapter covers 09-20 or 10-12. The atlas prints "ai-setup: 0 chapter(s)" and "ai-setup: 390 chapter(s)" on the same screen | **held** |
| V7 | knowledge-map finds `docs/THE-FILING-SCHEMA.md` by topic (the doc's own acceptance test, `:230-232`) | `knowledge-map --json filing schema address shelf reader` | surface hit at relevance 1.0 (status "unstamped"), with `fences/filing-schema/reconciliation.md` second | **held** |
| V8 | knowledge-map does **not** surface the sealed in-flight spec that `core/coord/target.py` names as its SPEC | `knowledge-map --json target ref vocabulary REF_KINDS normaliser sealed` | no `research/in-flight/…` node; the reconciliation that ordered it (`fences/context-system/reconciliation.md`) does surface | **held** (bounded: one query) |
| V9 | `recall` (lessons only) does not return the 10-07 "second press" atom | `recall "second press" --json` | 347 bag-of-words hits; none is the atom | **held** |
| V10 | LIBRARY's door 2 (`arc <id>`) does not exist as a verb | `py agent_cli.py arc --help` | "invalid choice: 'arc'" | **held** |
| V11 | A `fossil` atom lands on knowledge-map's **live surface** as "unstamped", not in the archive | `knowledge-map --json T060-M1 reconciliation continuous presence` | 55da7b and 4e2038 (both `status: fossil` in frontmatter) on the L1 surface as `unstamped` at 1.0; the archive holds only superseded and historical items | **held** |
| V12 | Lookback's research layer reads titles only, so a deep-body query misses a file that a title query finds | `lookback --layers research --json narrative_chapter referential integrity dangling` vs `… knowledge plane census` | deep: **0 hits** (the term occurs 7 times in the census body); title: the census at relevance 1.0 | **held** |
| V13 | Atoms minted after the last shelf generation are absent from SHELVES | grep SHELVES for the 10-07-late, 10-08 and 10-13 atoms | 0 of 5 present | **held** (direction implied by the timestamp, so a weak test) |
| (open) | Is today's ask in the eye yet? | `eye freq "deconstruct the house"` | UNHEARD; the newest indexed event is 10-12 12:12 | not counted: posed as a question, no direction pre-stated |

**Score:** 13 predictions, 13 held, 0 failed. **inferred**: some were bold (V2's exact 1,026, V5's exact
8/14, V11's placement); some were weak (V3, V13). V3 is the honest lesson of the run: a check can pass and
still hide the defect.

---

## Loop altitude (the value chain, link by link: does the signal flow back?)

The chain: **capture → record → project → index/map → retrieve → use → judge → promote / supersede /
fossilise → (back into ranking)**.

| loop | links that exist | does the signal flow back? | verdict | label |
|---|---|---|---|---|
| L1 Capture of speech | chat → transcript → eye (daily) | yes: automatic, with receipts and a coverage contract | **closed** (lag up to 24 h; provenance contaminated, I6) | observed |
| L2 Capture of findings | chat → seat decides → note / file / atom | depends on a seat's choice. Mint rate 713 → 193 → 90 → 22 per month while in-flight grew to 967 files | **open by habit**: findings now go to the zone no door reads | observed (counts); inferred (the habit shift) |
| L3 Map freshness | atoms change → SHELVES / ARCS / story / INDEX | **no trigger**: no schedule, no hook, no age warning where a reader looks | **open**: the classic designed-open loop (the measurement exists as a timestamp, nothing acts on it) | observed |
| L4 Retrieval | doors → reader | text doors reach docs, fences, notes and library projections; research is title-only; in-flight is never read; atoms are never read by facet | **partly closed** | observed (V7–V12) |
| L5 Use → judgement | read → "was this useful?" | counters for queries and nodes only; no usefulness vote for docs or atoms; the eye says "credit UNKNOWN (this plane has no funnel)" | **open** (measurement without actuation) | observed (`agent_cli.py:2885`; the `_count` functions) |
| L6 Promotion and curation | in-flight → reviewed → docs/atom; draft atoms → curated | 408 drafts, 387 of them July migrations; the projection banner promises "the wrap sweep + library lint curate drafts" (`projection.py:105`) | **open** | observed (counts); unknown whether a lint runs (not traced) |
| L7 Supersession | new truth → old stamped → readers forwarded | the flip works in the store; the projection header was not re-rendered once (I2); back-links missing on 3 of 4 (I4) | **mostly closed, leaks at the edges** | observed |
| L8 Negative knowledge | falsified → FOSSILS row → future seats avoid | the currency checker warns (95 d); nobody acts; 60 fossil atoms and the withdrawn A1/A2 are unrecorded | **open** | observed |
| L9 Directive watch | Daniel repeats a steer → `standing` notices → a seat files it | proposes only, by design (Daniel's gate); but it checks against the wrong population (I7) and its top slot is machine text | **designed-open (correct), mis-aimed (defect)** | observed |

**Reductionism check (trap 3).** Every part passes its own unit test: the bodies rehash, the verifier exits
cleanly on content, the eye's coverage contract is honest about its frame. The failure lives **between** the
parts: a projection written once, a map never re-run, a fix applied to one reader and not its twin. You would
not find it by testing any part in isolation. **inferred** from L3, L6, L7 and I6/I7.

## The traps, as seen in this subsystem

1. **False first principles.** "The shelf can't rot" (`LIBRARY.md:59-60`): it rotted (P9, I5). "The JSONL is
   the recovery truth": true only for the public plane (P8, I3).
2. **Chesterton's fence (stated before any proposal).**
   - The store-only atoms exist, at least in part, **because** of Daniel's privacy ruling. Do not "repair" them
     back into the journal.
   - The `break` in `collect_durable` was most likely written as a *fallback* for trees without
     `docs/library` (**inferred** from the loop shape).
   - The 80-character research read may exist to stop 15–38 MB of research from swamping docs in ranking
     (**unknown**: no comment explains it).
   - The eye's marker list is deliberately conservative: adding a marker reclassifies history ("widening a
     corpus must not restate its history", `index.py:66-71`).
3. **Reductionism.** See the loop-altitude note above.
4. **The map is not the territory.** SHELVES, ARCS, the story atlas, INDEX and the eye's "operator" label are
   all maps that drifted from their territory. V3 is the sharpest case: matching totals are a map of matching
   members, and they lied.
5. **Goodhart.**
   - `--verify` checks the body sha (the metric) while a header lies about status (the thing).
   - `freq` verdicts count records labelled operator (the metric), not Daniel's utterances (the thing).
   - The currency checker's remedy, "re-affirm or re-stamp", can be satisfied by touching a file without
     checking that it is still true.

## Twin-fix pattern (the most reusable finding)

Twice, a fix landed in one organ and its sibling kept the bug:
- **Population fix.** `core/recall/staleness.py:152-156` was corrected away from the six-record
  `learnings.jsonl` stub, in its own words: "a detector aimed at the wrong population returns a clean bill
  that means nothing". `core/eye/directives.py:327` still reads that stub.
- **Authorship fix.** `directives.py:158-162` excludes subagent briefs from "his voice". `index.py:freq`
  (`:976-1010`) does not, and neither does `stats`.

**The house already holds the lesson for this.** `learn:experiment:when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`
surfaced in my own knowledge-map run (V7). **inferred**: lessons alone did not carry it across. A shared
helper would: one `operator_rows()` and one `lesson_population()`, imported by every reader.

---

## Great Sage report

> **Notice.**
> - 1,028 atoms; every body rehashes clean (0 corrupt, 0 sha-drift, `gen_library.py --verify`).
> - The shelves were last generated 2026-10-07 06:46 UTC, with 105 commits since, and nothing schedules a
>   regeneration (`mirror.py`, githooks and Task Scheduler searched).
> - The story atlas is from 2026-10-02; its main track has 4,178 beats and 0 chapters.
> - FOSSILS.md was last changed 2026-07-09 and holds 7 entries, while 60 atoms are stamped fossil and
>   contracts A1/A2 were withdrawn on 10-06.
> - The directive watcher reads `session_logs/learnings.jsonl` (6 lines, June 20) as "lessons", and only
>   `docs/library` as docs (`directives.py:327-342`; `durable_sources` = 1,026 exactly).
> - 2,193 of 9,616 "operator" rows (22.8%) come from subagent transcripts. `freq` and `stats` count them;
>   `standing` does not.
> - Lookback reads reviewed research by its first 80 characters (`lookback.py:472`). No door reads
>   `research/in-flight` (967 files, 38 MB), which is where code's SPEC pointers lead.
> - Fossil and draft atoms read as "unstamped" and land on the live surface (V11).
> - Journal and store disagree in both directions under an equal total.
> - Command-line eye reads are not disclosed (`toolbox.py:612`, tool door only).
>
> **Analysis.**
> - The storage is sound and the surrounding loops are open. The maps are photographs because step 5 (a
>   freshness trigger) was never built (from I5 and the search for callers).
> - Readers mis-aim because fixes were applied per organ, not per class (from the twin-fix pair).
> - New findings drift into the one zone no door reads, because writing a file is cheaper than minting an
>   atom (from a mint rate of 713 → 22 per month against in-flight growth). That habit is reasonable and the
>   doors simply did not follow it.
> - The common failure is silence that reads as health (I2–I10). The filing-schema diagnosis still stands
>   ("a reading problem"), and this run adds that it is also a **refresh** and a **provenance** problem.
>
> **Unknown.**
> - The cause of the journal-only atoms missing from the store (dated 07-29). Not traced.
> - Whether every store-only atom is a private-plane record. I did not open them, by rule.
> - Whether the private-plane backstop fires when a generator regenerates. That cannot be tested read-only.
> - Why 3 of 4 supersessions lack back-links (the flipping path was not traced).
> - Whether any lint curates the 408 drafts.
> - Why lookback reads research at 80 characters (no comment).
> - Which file the eye's one address collision loses.
> - The college plane (`artifacts/college`): not examined.
> - Who, if anyone, reads SHELVES and ARCS. File reads have no counter.
> - Daniel's personal memory, `private/` and the story oracle were out of bounds, by rule. Search boundaries
>   are named per row.
>
> **Proposal** (smallest first; every one waits for Daniel):
> 1. Point `directives.collect_durable` at the LearningStore, the same fix `staleness.py` already has, and
>    stop the `break` from skipping top-level `docs/`, `fences/` and `research/`. Keep the fallback the
>    `break` was written for. It is a few lines.
> 2. Give `eye freq` and `eye stats` the same `COALESCE(is_subagent,0)=0` filter `standing` uses, and keep
>    the raw count visible beside it. Better: move it into one shared `operator_rows()` helper.
> 3. Have `gen_library --verify` also compare header *status*, and know the private overlay, so its
>    "missing" rows stop being a false alarm that teaches people to ignore it. Then re-render the one stale
>    projection.
> 4. Print shelf and atlas age where readers look (boot or status), or schedule `gen_library` beside the daily
>    eye ingest. Chesterton first: the generator writes tracked files, and daily churn in the working tree may
>    be why it was never scheduled.
> 5. Teach lookback and knowledge-map the atom vocabulary (`draft`, `fossil` → archive) and reconcile the
>    three status vocabularies at a LIBRARY gate.
> 6. Give research the docs layer's read depth and add `research/in-flight` as a layer (or at least the
>    in-flight files that code cites as SPEC). Measure ranking swamp first, since the 80-character read may be
>    deliberate.
> 7. Log command-line eye reads to the same disclosure file as the tool door.
> 8. Name `research/in-flight` in `LIBRARY.md` and `research/README.md`; add A1/A2 (and the other withdrawn
>    contracts) to FOSSILS.md, or make FOSSILS a generated view over fossil-status atoms. This is Daniel's
>    call: LIBRARY amends only at gates.
>
> No deletions are proposed.
>
> **Verification.** 13 predictions stated before running; 13 held, 0 failed. The weak ones are labelled (V3,
> V13). V3 passed while hiding a two-way membership drift, and that is the run's own Goodhart specimen. The
> sharpest held: V2 (exactly 1,026), V5 (exact on all four counts), V11 (fossils on the live surface) and V12 (deep
> body: 0 hits; title: found).
>
> **Proceed?** YES / NO: Daniel's gate. Proposals 1, 2, 3 and 7 are code-only and pinnable. Proposals 4–6
> touch ranking and scheduling. Proposal 8 amends the library law.
