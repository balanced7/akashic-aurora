# Narrative Spine — design plan (System 4 capstone)

> **Status:** DESIGN (plan-first, build-in-slices). 2026-06-27.
> Plan before code, like `docs/knowledge-harmonization-plan.md` and
> `docs/context-pillar-plan.md`. This doc defines the model, schema, the Chronicler,
> the agent-facing views, the auto-logging hooks, the prior art we're learning from,
> and a phased slice plan. No code until the model here is agreed.

---

## 1. The problem

Three observations, all from real use:

- **Isolated learnings have no connective tissue.** The LearningStore holds *point
  facts* (6 refactoring lessons). There is no *story* — no "what happened, in what
  order, why, and what it led to."
- **Fresh agents recall a stale, false picture.** Two OpenCode tests asked "what's
  been done?" and got a months-old answer, because the agent read hand-written status
  docs (`SYSTEM_STATUS.md`, …) that had drifted from reality. The system does not
  remember its own construction history in a trustworthy, queryable way.
- **No multi-resolution navigation.** An agent needs to zoom **broad → mid → narrow**
  and jump from any point in the story straight into the concrete learning, file, or
  moment that produced it. Today there's no spine to navigate.

**Goal:** a time-ordered, cross-linked *narrative spine* over the event Ledger, with
three zoom levels, where the skeletal learnings hang off the narrative and every node
is a skeleton-with-a-followable-pointer. Generated from real events, so it **cannot
drift** the way the hand-written docs did.

---

## 2. The model

A narrative is a **multi-resolution spine over the append-only Ledger.** Timestamps
are the backbone; everything is time-anchored; edges use our `relationship_types`
vocabulary so it's a *graph*, not a flat log.

```
BROAD   Storyline   the whole journey (ordered Chapter summaries)        [generated]
MID     Chapters    coherent stretches of work (a session / sub-goal)    [generated]
NARROW  Beats       salient time-anchored events  ── point to ──>  atoms [logged]
                                                  learnings · files/commits · ledger events
```

- **Beat** — a single narrative-weighted event on the spine (a decision, a learning
  recorded, a milestone reached, a commit). Distinct from raw Ledger noise: a Beat is
  a *salient* event (see narrative weight, §4). Each Beat points to its underlying
  atom (a learning id, a commit sha, a ledger event id).
- **Chapter** — a coherent stretch of Beats, bounded by triggers (§5): `{id, title,
  span:[t0,t1], summary, beats:[…], learnings:[…], commits:[…], relates:[{type,target}],
  parent:storyline_id}`.
- **Storyline** — the ordered roll-up of Chapter summaries, distilled to the highest-
  signal arc. Each arc point links to its Chapter.
- **Chronicler** — the process that folds a Ledger window (+ `git log`) into a Chapter
  and re-rolls the Storyline. The time-windowed sibling of `core/learning/consolidation.py`.

Reuses the exact Ranker → Distiller pipeline we already built — just scoped by **time
window** instead of by task.

---

## 2b. Multi-domain: Tracks, Themes & inferred routing

The narrative is a weave of **three axes** connected by relationship-typed edges — not
one linear story (the system is for *all* work, not just code):

- **Track (which domain)** — a long-running thread per project/domain: `ai-setup`,
  `stemroller`, `vision`, `voice`, `research`, `ideas`. Each Track has its own Chapters
  + arc. **Git commits are only the *code* tracks' beat-source**; research/decisions/
  milestones/notes feed the others. A Beat's *evidence* (`source`) is decoupled from its
  *domain* (`track`).
- **Time (when)** — the shared spine; Tracks run in parallel.
- **Theme (which idea)** — cross-cutting idea-groups (e.g. "local-first") that weave
  across Tracks. A Beat carries one `track` + many `themes[]`.

Hierarchy: **Atlas → Track → Chapter → Beat**, with **Themes orthogonal**.

### The 66 relationship types ARE the edge schema
The schema falls out of the vocabulary we already built — no new edge model:

| Category | Example types | Connects | Navigation it gives |
|---|---|---|---|
| Temporal | precedes, follows, concurrent_with | beat ↔ beat | the sequence (within & across tracks) |
| Causal | causes, enables, prevents, led_to | beat → beat | *why* / what unblocked what |
| Hierarchical | part_of, derived_from, depends_on | beat→chapter→track; track→track | structure, containment, dependency |
| Versioning | is_version_of, supersedes | iterations | v1→v2 / what replaced what (bi-temporal) |
| Semantic | is_about, exemplifies, advances | beat → **Theme** | which idea-group it advances |
| Associative | relates_to, inspired_by, analogous_to | **track → track** | **cross-domain pollination** |
| Agent-based | created_by, contributed_by | beat → agent | who did it |
| Spatial | located_in, hosted_on | beat → repo/machine | where it lives |

Tracks = group by `part_of` a domain. Themes = group by `is_about` an idea. Cross-domain
= `associative`. Time = `temporal`.

### Tracks are INFERRED from context, not declared (the TrackRouter)
The system recognizes when work switches domains and files beats accordingly — no
`--track` flag. This is a known problem with strong prior art (see §10b):
**conversation disentanglement** (assign interleaved messages to threads = assign a Beat
to its Track), **topic segmentation / topic-shift detection** (detect the switch),
**intent/task-drift detection** (recognize drift via embedding-centroid cosine), and
**unsupervised topic discovery + auto-tagging** (spawn + name a *new* Track when nothing
matches). All can be done unsupervised.

**TrackRouter — tiered, heuristic-first (our standard pattern):**
- **Tier 0 (ships first, no ML):** infer from cheap signals — a commit's touched
  repo/dir (`core/`→ai-setup, stemroller paths→stemroller); a learning/decision's
  category + the agent's active task keyword. The active Track **persists** until a
  switch. Switch = repo change / task-keyword change / time gap / explicit marker.
- **Tier 1 (embeddings, later slice):** per-Beat embedding via the Ranker's existing
  `relevance_fn` seam; per-Track **centroid**; assign to nearest centroid by cosine;
  **spawn a new Track when max-similarity < threshold** (novelty); flag a **switch when
  the running representation drifts** past a threshold (DeepContext). Unsupervised
  (clustering / contrastive — needs no labels).
- **Tier 2 (LLM, optional):** disambiguate hard cases; auto-name new Tracks/Themes
  (cluster-tagging).

Themes use the same machinery, multi-label. Boundary detection (§5) runs **per-Track**.

## 3. Lexicon additions

| Term | Meaning | Genus |
|---|---|---|
| **Beat** | one salient, time-anchored narrative event (points to its atom) | narrative event |
| **Chapter** | a bounded coherent stretch of Beats in one Track (mid view) | narrative segment |
| **Track** | a long-running per-domain/project thread (its own Chapters + arc) | narrative thread |
| **Theme** | a cross-cutting idea-group weaving across Tracks (orthogonal) | narrative thread |
| **Atlas** | the broad view across all Tracks over time | narrative overview |
| **Storyline** | one Track's rolled-up arc of Chapter summaries | narrative |
| **Chronicler** | builds Chapters/Storyline from the Ledger (writes the chronicle) | derivation process |
| **TrackRouter** | infers a Beat's Track from context + detects switches | router |
| **narrative weight** | salience score stamped on an event at log time (0–5) | scalar |
| **bi-temporal** | `valid_from/valid_to` (true-in-world) vs `recorded_at` (logged) | time model |

`chronicle` stays our reserved word for *curated derived views*; the Storyline/Chapters
render into `chronicles/story.md` (human) + `chronicles/story.index.json` (machine).

---

## 4. Data model

All nodes live on the existing **Store** (`narr:` namespace) + render to `chronicles/`.
Raw stays in the **Ledger** (never rewritten).

**Beat** (`narr:beat:<id>`)
```yaml
id: beat_<ts>_<rand>
at: <iso timestamp>            # spine anchor
kind: decision | learning | milestone | commit | blocker | note
weight: 0..5                   # narrative salience (write-time, see below)
summary: "<one line>"
source: "<followable pointer>" # learn:experiment:X | git:<sha> | ledger:<stream>:<id> | session_logs/…:Ln
relates: [{type: <relationship_type>, target: <node id>}]
chapter: <chapter_id>          # back-link (bidirectional provenance)
```

**Chapter** (`narr:chapter:<id>`)
```yaml
id: chapter_<ts>
title: "Harmonize the knowledge store"
span: [<t0>, <t1>]
summary: "<2-3 sentences, regenerated from the Beats>"
beats: [beat_id, …]
learnings: [experiment_name, …]   # convenience index
commits: [<sha>, …]
relates: [{type: led_to, target: chapter_id}, …]
parent: storyline
# bi-temporal:
valid_from: <t0>
valid_to: null | <ts>             # set when superseded by a corrected chapter
recorded_at: <ts>
critic_ok: true|false             # faithfulness gate result
```

**Storyline** (`narr:storyline:current`) = ordered `[chapter_id]` + a distilled arc
summary + `relates` edges between chapters.

**Edges** use `core/foundation/relationship_types.py`: `caused`, `led_to`, `part_of`,
`derived_from`, `prevents`, `supersedes`, `produced`, `depends_on`. The graph is what
lets an agent ask "*why* did this happen" not just "*what*."

**Bidirectional pointers (Zep lesson):** a Beat knows its Chapter; a learning gains a
`chapter` back-link. Any narrative claim is traceable to source; any atom knows its
place in the story.

---

## 5. The Chronicler (how it's built)

Pipeline, run at session end or on demand (`agent_cli.py chronicle` / a hook):

1. **Collect** the new window: Ledger events since the last Chapter + `git log`
   commits in the span + learnings recorded in the span.
2. **Promote to Beats**: keep events whose **narrative weight ≥ threshold** (drop
   noise). Weight is stamped at log time (decisions/milestones/learnings high;
   routine reads low) — *importance-at-write-time*, the Generative Agents lesson.
3. **Segment into Chapters (boundary triggers, not ML)** — cut a new Chapter when ANY
   fires (the ES-Mem/HingeMem lesson, reduced to cheap heuristics):
   - explicit `mark_chapter` signal (an agent/session declares a boundary),
   - **task/topic shift** (the agent's task keyword changes),
   - a **git-commit cluster** gap (e.g., >N hours, or a "milestone" commit),
   - a **salience spike** (a high-weight decision/milestone Beat).
   Boundaries are tunable and **mergeable/splittable** later (over-segmentation guard).
4. **Distill** each Chapter: Ranker (salience × recency × relevance) → Distiller
   (writer→critic) over the Chapter's Beats → the `summary` + `relates`. **Regenerate
   from Beats, never summarize-the-summary** (anti-drift, the timeline-summarization
   lesson). The critic gate sets `critic_ok`.
5. **Roll up** the Storyline: distill the Chapter summaries into the arc. Same rule —
   regenerate from Chapters, keep pointers.
6. **Supersede, don't overwrite** (Zep/bi-temporal): a corrected Chapter sets the old
   one's `valid_to` and adds a `supersedes` edge. History stays queryable.

Read-only on raw. Empty-graceful. Idempotent per window.

---

## 6. Auto-logging hooks ("as things get built, they get logged")

The spine fills itself — the key is making meaningful actions emit **narrative-grade
Beats**, which is the one real prerequisite:

- **Signals → Ledger** (already the design): decisions, learnings, blockers, milestones
  emit signals; add a `weight` field at emit time.
- **`agent_cli.py learn`** already records a learning → also emits a `learning` Beat.
- **`scripts/mirror.py` commit** → emits a `commit` Beat (sha + message + touched
  files). Git *is* the file-narrative; we just index it.
- **`mark_chapter <title>`** verb → an explicit boundary + title (mirrors the harness
  chapter concept; lets a session name its own arc).
- **Session start/end** → Beats that bound a default Chapter.

Without these, the Chronicler has thin material — so **Slice 1 is the logging hooks**,
not the rendering.

---

## 7. The three views + agent verbs (navigation)

**ACI discipline (`docs/agent-interface-aci.md`): keep the verb surface tiny and
stable — reach subsystems *through* existing verbs, don't add a tool per node type.**
So the whole narrative is **one new verb, `story`**, with progressive-disclosure
args (not three separate verbs):

```
py agent_cli.py story                 # BROAD: the arc (budgeted; chapters as beats + ids)
py agent_cli.py story <chapter_id>    # MID:   that chapter's summary + learnings/commits/beats as links
py agent_cli.py story --beat <id>     # NARROW: a single event + its source pointer
py agent_cli.py story --at <date>     # jump to the chapter covering a moment
py agent_cli.py story --mark "title"  # (rare) declare a chapter boundary; boundaries are mostly auto
```
Existing verbs already cover the deepest drill-down: `recall <name>` (learning atom),
`git show <sha>` (file atom). `--json` on each for machines; output is **budgeted**
(context-rot lesson) with explicit drill hints; **errors teach** ("no chapters yet —
run `story --rebuild`"). Each level carries pointers **down**; back-links go **up**.

**Closing the loop (the fix for stale recall):** the recent Storyline/Chapter is also
injected into `agent_cli.py boot` context. A fresh agent then gets the *true, generated*
"what's been done lately" in its startup context — instead of reaching for the stale
hand-written `SYSTEM_STATUS.md`. The narrative *feeds the Context pillar*; the spine and
the harness are the same machinery pointed at time.

---

## 8. Rendering

The MD+YAML skeleton from our compaction research (`docs/context-compaction-skeleton-
research.md`): hierarchical `Storyline > Chapter > Beat`, each node human-readable +
machine-parseable with `type/span/relates/source`. Two artifacts, both generated:
- `chronicles/story.md` — the readable narrative (broad at top, chapters below).
- `chronicles/story.index.json` — the machine index the verbs query.

Serves **both** audiences (the open question from before): agents navigate the index
via verbs; humans read the MD. Default Chapter grain = **sub-goal within a session**
(finer, mergeable) per the event-segmentation literature, not one-chapter-per-session.

---

## 9. Reuse vs. new

| Reuse (already built) | New (this plan) |
|---|---|
| Ledger (append-only spine, timestamps) | Chronicler (windowed distill + boundary triggers) |
| Ranker (salience × recency × relevance) | Beat/Chapter/Storyline schema (`narr:`) |
| Distiller (writer→critic, budgeted skeleton) | `story` / `beat` / `mark_chapter` verbs |
| Supersession → extend to bi-temporal | narrative-weight at emit time + back-links |
| relationship_types (edges) | git-commit → Beat indexing |
| chronicles/ + consolidation.py (template) | story.md + story.index.json renderers |
| followable source pointers | evaluation harness (timeline QA) |

Most of it is reuse — consistent with "build the primitive once."

---

## 10. Prior art & lessons (what we're learning from)

The 2023→2026 literature has solved pieces of this; our design folds in the lessons.

- **Generative Agents** (Park et al., 2023) — memory stream + retrieval (recency ×
  importance × relevance) + **reflection**. → validates the Ranker; **reflection = our
  Chapters/Storyline**; stamp **importance at write time**.
  https://ar5iv.labs.arxiv.org/html/2304.03442
- **Zep / Graphiti** (2025) — temporal knowledge graph; **bi-temporal**, **invalidate-
  don't-delete**, **bidirectional provenance** for citation. → our bi-temporal Chapter
  fields + back-links. https://arxiv.org/html/2501.13956v1
- **A-MEM** (NeurIPS 2025) — Zettelkasten atomic notes + explicit links + evolution. →
  atomic Beats + typed edges; **evolve via supersession, not in-place** (see SSGM).
  https://arxiv.org/abs/2502.12110
- **MemGPT / Letta** (2023) — tiered memory (core/recall/archival) + paging. → the
  agent **pages a zoom level into context** (story → chapter → atom), not the whole
  story. https://arxiv.org/abs/2310.08560
- **Event-segmentation cluster** (2026: ES-Mem, HiMem, HyperMem, HingeMem) — segment a
  stream into coherent episodes via **boundary triggers** (topic shift / salience /
  entity change). → our cheap boundary heuristics; **no ML needed to start.**
  https://arxiv.org/abs/2601.07582 · https://arxiv.org/pdf/2601.06377 · https://arxiv.org/html/2604.06845v1
- **Timeline Summarization / NexusSum / Narrative Consolidation** (NLP) — multi-level
  timelines; chronological integrity via a Temporal Alignment Event Graph. →
  **regenerate-from-atoms + critic gate** to avoid summary drift.
  https://arxiv.org/html/2505.24575v1 · https://arxiv.org/html/2512.18041
- **Surveys**: Memory for Autonomous LLM Agents (https://arxiv.org/pdf/2603.07670);
  governing evolving memory / **SSGM** risks (https://arxiv.org/html/2603.11768v1).

**Track inference & context-switch detection** (the "infer, don't declare" problem) —
four bodies of prior art map onto the TrackRouter (§2b):
- **Conversation disentanglement** — assign interleaved messages to threads = assign a
  Beat to its Track. Siamese similarity + ranking; contrastive/clustering (no labels);
  discourse-graph + GCN beats GPT-4. https://aclanthology.org/N18-1164/ ·
  https://arxiv.org/pdf/2210.15265
- **Dialogue topic segmentation / topic-shift detection** — detect the switch (BERT+TCN
  sequence labeling; sentence-embedding similarity between consecutive units + threshold;
  unsupervised topic-shift in chats). https://arxiv.org/pdf/2305.01195
- **Intent / task-drift detection** — recognize the switch via the temporal trajectory of
  intent; **embedding-centroid drift (cosine)**, PSI / KS tests. DeepContext:
  https://arxiv.org/html/2602.16935v1
- **Unsupervised topic discovery + auto-tagging** — SBERT + clustering; a cluster-tagging
  engine that **spawns a new tag when nothing matches** = spawn + name a new Track.
  https://arxiv.org/pdf/2108.08543

**Our novel angle:** most systems are conversation-only; we weave **three dimensions
into one spine — events (Ledger) + knowledge (learnings) + code (git commits)** — across
**multiple parallel domain Tracks** with inferred routing. Local-first (no Neo4j); a
lightweight temporal graph on our Store/Ledger.

---

## 10b. Synthesis from our *own* prior research (naming + architecture)

The external prior art (§10) says *what* to build; our four internal research docs say
*how to build it so it stays coherent*. The best of each, applied:

- **Ubiquitous Language + genus-before-species + names-must-not-lie**
  (`coding-principles-research.md`). The narrative tier uses domain-genus names: a story
  has a **Storyline → Chapters → Beats** (a "Beat" *is* the skeleton-research **Entry** —
  the leaf — named in story terms). `Chronicler` writes `chronicles/` (our reserved word
  for curated-derived views) — no name lies. Add the new terms to `docs/LEXICON.md` in
  the same pass.
- **Build the primitive once / rule of three** (`shared-primitives-and-coherence.md`).
  The `Chronicler` is **not new code — it generalizes `core/learning/consolidation.py`**
  (which already distills a collection → a chronicle with source pointers). `lessons.md`
  and `story.md` become two outputs of one chronicler. Beats/Chapters are another
  `IndexedRecords` user — they ride the same Store index/hydrate shape.
- **The harness owns context over the event stream** (`context-compaction-skeleton-research.md`).
  Our Ledger *is* the event stream; the Chronicler and the Context pillar are the **same
  harness pointed at different slices** (time-window vs task). `story.md` is the
  researched **MD+YAML skeleton** (`Domain>Topic>Entry` ⇒ `Storyline>Chapter>Beat`,
  edges = relationship_types, each node `type/tags/relates/confidence/source`). The
  pitfalls table there (context rot, irreversible discard, hallucinated summaries, stale
  facts) maps directly onto our defenses (budget, append-only Ledger, writer→critic,
  Supersession).
- **ACI: tiny stable verb surface, descriptions-as-prompts, errors-that-teach, budgeted
  progressive-disclosure returns** (`agent-interface-aci.md`). → one `story` verb (§7),
  not four; the narrative feeds the inbound Context surface so "know" and "do" stay
  siblings.
- **Cleanup-at-scale discipline** (`coding-principles-research.md`): the Chronicler is a
  *strangler-fig* over the stale status docs — once the generated Storyline is trusted,
  the hand-written `SYSTEM_STATUS.md`/`ACTUAL_INVENTORY.md` are retired (Slice plan).
  Consider a **doc-freshness guardrail** (extend `check_boundaries.py`): flag hand-written
  status docs so generated truth can't silently drift again.

## 10c. Closest analogues — and what we uniquely combine

Two worlds build *pieces* of this; nobody combines all of them.

**Machine / retrieval:**
- **RAPTOR** (https://arxiv.org/abs/2401.18059) — recursively embed→cluster→summarize
  into a tree of multi-level summaries; retrieve at any abstraction. = our broad/mid/
  narrow skeleton, built bottom-up. → a concrete algorithm for the **Chronicler's roll-up**.
- **Microsoft GraphRAG** (https://microsoft.github.io/graphrag/) — entity KG + **Leiden
  hierarchical community detection** + community summaries + local↔global queries. =
  cross-domain clusters (communities ≈ Themes/Tracks, *auto-discovered*) + multi-
  resolution. → **Track/Theme discovery via community detection** (TrackRouter Tier-1);
  the "global query" = the **Atlas**, answered cheaply from community summaries.
- **HippoRAG** (https://arxiv.org/html/2405.14831v1) — hippocampal *index* over neocortex
  *store*; schemaless KG + Personalized PageRank + cosine **synonymy edges**. = our
  skeleton (index) → atoms (store); synonymy/association edges = **cross-domain
  pollination**; PageRank = "what relates to X across everything," single-step + cheap.
- **Amory** (https://arxiv.org/html/2601.06282, "narrative-driven agent memory"),
  **AriGraph**, **Temporal-Semantic Memory** (https://arxiv.org/pdf/2601.07468) — THE
  direct analogues: a KG of **episodic events + semantic facts**; episodic → **durative**
  via temporal segmentation + semantic abstraction = **beats → chapters/themes**, exactly.
  This precise combination is a 2026 frontier — we're not alone, and we're aligned.

**Human / tools-for-thought (closest in spirit):**
- **Zettelkasten + Roam/Logseq/Obsidian** — daily notes (temporal journal = the spine) +
  atomic notes + **block-level bidirectional links** (cross-domain graph), in **local
  Markdown**. = our spine + followable beat-level pointers + back-links, local-first. →
  make `story.md` **Obsidian/Logseq-compatible** (wiki-links) so the *human* browses the
  same narrative the agents navigate.
- **Building a Second Brain (CODE + PARA + Progressive Summarization)** — **PARA** =
  Tracks (file by project/domain); **atomic Zettelkasten notes** = Themes (cross-connect);
  **Progressive Summarization** = the Distiller skeleton; **CODE** (Capture→Organize→
  Distill→Express) = our pipeline (log→route→chronicle→serve). The PKM world's proven
  split — *project-file for action, atomic-note for connection* — **is exactly our
  Tracks + Themes.**

**What WE uniquely combine** (the intersection none of them spans): a **temporal narrative
spine** × an **auto-built multi-resolution skeleton** × **cross-domain hierarchical
clustering with inferred routing** × **followable lossless pointers to ground truth** ×
**relationship-typed edges** × **local-first** × spanning **code + knowledge + ideas**.
Each analogue validates one slice; the product is new.

**Concrete refinements these add to later slices:**
- Chronicler roll-up (Slice 3) ← **RAPTOR** recursive cluster+summarize tree.
- Track/Theme discovery (Slice 6) ← **GraphRAG** Leiden community detection; Atlas =
  GraphRAG "global query" over community summaries.
- Cross-domain links + retrieval ← **HippoRAG** cosine synonymy edges + Personalized
  PageRank ("what relates to X across all domains").
- `story.md` rendering (Slice 3) ← **Obsidian-compatible** wiki-links (human browses the
  agent's narrative in a PKM tool).

## 11. Evaluation

Borrow the long-horizon QA target these systems benchmark on (LoCoMo-style): can an
agent, given only the narrative + drill-down, correctly answer **"what happened around
date X, why, and what did it lead to?"** Plus a **faithfulness test**: every Chapter
claim must resolve to a real Beat/source (no orphan claims — extends the Distiller's
source-pointer invariant). Add a `test_narrative.py` modeled on `test_robustness.py`.

---

## 12. Risks & mitigations

| Risk (from the literature) | Mitigation |
|---|---|
| Summary drift (compounding) | Regenerate each level from atoms; faithfulness critic; keep pointers |
| Evolving-memory corruption (SSGM) | Supersession + critic, never silent in-place edits |
| Over-/under-segmentation | Tunable triggers; chapters mergeable/splittable; `mark_chapter` override |
| Thin material (events not logged) | Slice 1 = logging hooks first |
| LLM cost of reflection | Run at boundaries/session-end; budget via Distiller; heuristic writer ships first |

---

## 13. Phased slice plan (build order)

- **Slice 0 — schema + lexicon.** `narr:` schema (Beat/Chapter/**Track**/**Theme**/
  Atlas), relationship-type edge schema, `chronicles/story.*` format, lexicon entries.
  No behavior.
- **Slice 1 — logging hooks (the prerequisite).** narrative-weight on signals; `learn`
  → Beat; `mirror.py` commit → Beat (with touched-paths); session start/end Beats.
  Beats accrete (unrouted).
- **Slice 2 — TrackRouter (Tier 0, heuristic).** assign each Beat to a Track from cheap
  signals (commit repo/dir; category + active task keyword); persist active Track;
  heuristic switch (repo / task-keyword / time-gap). **This is the "smart enough to
  recognize the switch" piece — heuristic first.** Test on a labeled fixture of beats.
- **Slice 3 — Chronicler (per-Track, heuristic).** per-Track boundary triggers + windowed
  Ranker/Distiller → Chapters + per-Track Storyline + the Atlas; regenerate-from-atoms +
  critic gate. Renders `story.md`/`story.index.json`.
- **Slice 4 — the `story` verb.** `story` (Atlas), `--track`, `--at`, `--chapter`,
  `--beat`, `--json`; budgeted; errors-that-teach.
- **Slice 5 — Themes.** theme assignment (keyword → later embedding), `is_about` edges,
  `story --theme` (cross-domain view).
- **Slice 6 — embedding routing (Tier 1).** SBERT embeddings via the Ranker `relevance_fn`
  seam; per-Track centroids; nearest-centroid assignment; novelty→new Track; drift→switch;
  unsupervised Theme clustering. Upgrades Slices 2 & 5 behind the seam.
- **Slice 7 — bi-temporal + back-links + feed `boot`.** extend Supersession to validity
  intervals; learning↔chapter links; inject the recent Atlas/Track into `boot` context
  (closes the stale-recall loop).
- **Slice 8 — evaluation.** `test_narrative.py` — timeline QA + faithfulness + TrackRouter
  assignment accuracy on the fixture.
- **Slice 9 (optional) — LLM writer/critic + LLM Track/Theme naming.**

Each slice is independently testable and leaves the system green. Seed the first real
narrative by chronicling **this build-out** across its Tracks (ai-setup, research, …) so
an agent recalling "what's been done" finally gets the truth — which also retires the
stale status docs at the root.

---

## 14. Decisions — resolved by the synthesis (for final sign-off)

1. **Chapter grain → sub-goal, with session as a tag (3 explicit levels).**
   The event-segmentation literature (ES-Mem/HingeMem) segments *sub-session* episodes,
   and the skeleton research wants a real 3-level hierarchy. One-chapter-per-session
   collapses to 2 useful levels. So: `Storyline (broad) > Chapter = sub-goal (mid) >
   Beat (narrow)`, each Chapter carrying a `session` tag for filtering, and Chapters are
   **mergeable** (a single-goal session → one chapter). Richest navigation, matches
   broad/mid/narrow exactly.

2. **`story.md` → `chronicles/`.** It's a *generated curated derived view*; the skeleton
   research and our lexicon both put those in `chronicles/` (alongside `lessons.md`).
   `docs/` stays hand-authored design. (`chronicles/story.md` + `chronicles/story.index.json`.)

3. **Cadence → incremental auto at session-end + on-demand full rebuild.** Compaction
   fires at *boundaries*, not continuously (cost + the "summarize near the limit"
   pattern). A session-end hook (piggybacking the `mirror.py` commit / a session-end
   signal) chronicles only the *new* window into a new Chapter (cheap, heuristic writer);
   `story --rebuild` regenerates the whole thing on demand. LLM writer/critic is Slice 6.

4. **Git indexing → index ALL commits as Beats, but weight by salience.** Completeness
   is a stated narrative objective (Narrative Consolidation), and `git log` is cheap — so
   every commit becomes a *low-weight* Beat (complete, followable file-history). Commits
   with salience signals (merge, tag, conventional-commit `feat:`/`fix:`, or touching
   `core/`) get **higher narrative weight** and surface in Chapter summaries; routine
   "Mirror progress" commits stay as quiet drill-down. Honors both completeness
   (Narrative Consolidation) and importance-at-write-time (Generative Agents).

With these resolved, **Slice 0 (schema + lexicon, zero behavior) is ready to start.**
