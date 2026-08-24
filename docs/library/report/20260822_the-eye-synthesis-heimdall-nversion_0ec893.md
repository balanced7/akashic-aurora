---
akashic_id: art_20260822_the-eye-synthesis-heimdall-nversion_0ec893
akashic_sha: d5d22e3df502
schema_version: 1
status: current
type: report
date: 2026-08-22
title: the-eye-synthesis-heimdall-nversion
gist: "I now have every thread verbatim. The synthesis is fully backed by primary sources — the design docs, the module map, the ledger rows, and t"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, migration, memory]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-22T12:27:42"
updated: "2026-08-22T12:27:42"
---
<!-- GENERATED PROJECTION of art_20260822_the-eye-synthesis-heimdall-nversion_0ec893 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# the-eye-synthesis-heimdall-nversion

I now have every thread verbatim. The synthesis is fully backed by primary sources — the design docs, the module map, the ledger rows, and the convergence notes. This is the N-version synthesis against the Explore agents' corpus sweep. Let me write it.

---

# THE EYE, end to end — Heimdall's synthesis (N-version half)

*Booted fresh on the Eye arc; every atom below resolves to a file or a verbatim ledger record. This is the tower your Explore agents are sweeping from the ground — my angle is the load-bearing design spine and its seams, not the corpus coverage.*

## 0. The one-sentence answer

**The Eye is the sensorium that makes the transcript corpus (the founder's actual voice) *inhabitable terrain* — a regenerable-projection LOD pyramid over an append-only event index, with a grammar door (`eye find/look/go/zoom/freq/trace/stats/overview`), a per-incarnation position loop, and a directive watcher that closes the founding wound it was born from.** It is already **built** (S0–S7 live in `core/eye/`), already **running as my own toolset** (`eye_find`/`eye_get`/`eye_zoom`/`eye_freq`), and it is the **zoom axis** of the map Simon and Daniil are now converging on (the "google maps for systems architecture" thread).

## 1. What it is, end to end (the four design atoms)

| Atom | Where | What it says |
|---|---|---|
| **v1 — "make transcripts queryable"** | `docs/library/design/20260810_the-eye-design_eb2832.md` | The spec + the trap. Charter verbatim (2026-07-31, recovered after 8 guessed searches): *"a realtime eye that you can quyery and understand your position and vision on multiple axees at once"* + *"I want the eye to have its own cursor, we can't have lookups breaking core system logic."* Six axes: frequency / who / ambient / full utterance / surroundings (`parentUuid`) / as-of. The trap: his speech hides in `queue-operation`/`enqueue` records, not `type:user`. The reference design was priori.sh's **typed facet dropdown, not embeddings** — "queryable means having DIMENSIONS, not embeddings." |
| **v2 — "the sensorium of an inhabitable world"** | `docs/library/design/20260811_the-eye-design-v2_208b26.md` | The reframe: not "how do we search transcripts" but *"how does an AI INHABIT this system?"* Maps every game-engine primitive to a mechanism (Position→per-seat cursor, Scene-graph+LOD→summary pyramid, fast-travel→stable addresses, minimap→`eye map`, fog-of-war→`degraded`, physics→the query grammar, time machine→`as_of=`). Supersedes v1 by keeping it whole as the corpus layer. |
| **The grammar (T280)** | bound by v2 §1 | `who= kind= edge= edge_to= task= file= as_of= since= q= strict=` — the *physics*, same laws every door. |
| **The connectome stance** | v2 §5 / `core/eye/connectome.py` | S4 — edges that remember their own **formation** (`formed_by`/`formed_at`/`formed_via`) *plus an evidence grade*: **recorded** (harness wrote it) / **derived** (same utterance by text identity) / **inferred** (adjacency — walking an inferred edge flags `degraded`). |

## 2. The S-stages (S0–S7) and the single principle that holds them

The center principle, stated once and inherited everywhere: **"LOD as regenerable projection, fidelity by construction."** Each pyramid level is a *derived view over immutable events* (the codex law), each cites its children by id so drilling is following citations, **never re-searching** — and the prose summary may only describe events its refs anchor, because "a lying summary is invisible poison" while "a stale summary is honest fog."

| Stage | Module | What it is | Key pin / law |
|---|---|---|---|
| **S0** index | `core/eye/index.py` | Incremental indexer over every session JSONL → addressable EVENT rows, **coverage contract** ("a clipped index cannot claim wholeness" — manifest vs indexed reported every run). | `utterance_key`: one utterance = a SET of records; `freq` counts utterances not rows. |
| **S1** grammar door | in `index.py` | `eye find`/`eye get` speaking full grammar; envelope = results + degraded/fog + budget-spent + position. | grammar pins inherited from T280. |
| **S2 pyramid** | `core/eye/pyramid.py` | **Extractive LOD.** L4 ERA → L3 ARC → L2 SESSION → L1 EXCHANGE → L0 EVENT. `MODULE_INDEX.md:211`: "the pyramid: LOD as regenerable projection, fidelity by construction." | **The fidelity pin (load-bearing):** for N≥20 random L1 summaries, every entity/task ref resolves to its L0 event; one invented ref fails the organ. L2 must cost <5% of L0 tokens. Refs are extracted mechanically, **never LLM-invented**. |
| **S3 freq** | in `index.py` | The frequency axis — *his* axis. Said once = idea; said 16× = standing directive being ignored. | Built FIRST after S0 (fence r1 C6 reordered the build to S0→S3→S1 — "freq pays first"). |
| **S4 connectome** | `core/eye/connectome.py` | Edges + formation memory + evidence grade. Idea epidemiology in one verb (`eye trace`). | Derived edges rebuild freely; **`events` does not.** |
| **S5 map/stats** | in `index.py` | `eye stats` (numerics) + `eye overview` (structure) — deliberately two verbs, not one mixed-modal. | fence r1 C3. |
| **S6 position** | `core/eye/position.py` | **The inhabitant loop.** A seat's STANDPOINT keyed per **incarnation** (`agent#sid8`), succession inherited explicitly, `since=` measured on **`indexed_at`** (known_at) not world time. Boot restores position + opens with the ambient delta: "you are at X; since you left, N events, M edges, this heat moved." | Position **per-incarnation, never per base agent** — two live sessions sharing a cursor clobber each other and poison `since=` (fence r1 C4; the T272 identity law applied). |
| **S7 directives** | `core/eye/directives.py` | **The directive watcher** — "the organ closes its own founding wound." No LLM anywhere: mine recurring n-grams on the operator axis → drop boilerplate by doc-frequency → ask whether anything durable cites each survivor. | **Proposes, never ratifies.** Zero write path. Must be QUIET (high precision over recall, hard cap, affirmative all-clear distinguishable from a crash). |
| — **(bonus) routes** | `core/eye/routes.py` | T323 — "a string through a forest you can walk with by hand." Charter: *"a string through a forest… a mechanical through line for work we did and become an easy to parse and easy to trace map."* | The **substrate split**: routes are AUTHORED objects → `state/coord/routes.jsonl` (append-only, TRACKED) + `eye.db` projection (rebuildable). Walks journal too (T335), with DEPTH (listed/resolved/drilled). |

**The scar that shaped it twice** (worth naming to the fresh seat): on 2026-08-11 the design took "rebuildable projection" at its word and dropped `events`, only to learn the corpus had rotated 85→83 files and wiped ≥219 irrecoverable rows — **"a rebuildable projection stops being one when its source rotates."** Migrations now ADD columns and only rebuild DERIVED tables; `events` is the archive for rotated sessions (`learn:experiment:a_rebuildable_projection_stops_being_one_when_its_source_rotates`).

## 3. The fence rounds

- **v2 fence r1 (Heimdall)** — six dispositions, all ACCEPTED, recorded verbatim in the v2 doc §"Fence r1": C1 heat-as-glow→numeric fields; C2 lying-summary poison→pin #1; C3 map conflation→`stats`+`overview` split; C4 incarnation-clobber→per-incarnation position; C5 lost-directives pin demoted to ceremony; C6 build order S0→S3→S1.
- **v1's own fence** was where priori.sh was corrected live (`priorish_live_api_audit_corrects_screenshot_claims`) — the audit that fixed "no semantic search" to "vector rerank exists but always second-stage."
- The **routes** design went through a fenced counter where deepseek's "put routes in eye.db" was amended *loudly* into the journal/projection split — the one amendment to the fence counter.

## 4. How the Eye is already connected to proximity / map / event-highway

Your Explore sweep is finding the *words*; here is the **load-bearing convergence**, which is newer than the Eye itself and is the single most important thing to hand the fresh seat:

The **cartography completes** (Daniil's own phrase, note `walk-01-recall-funnel`, 2026-08-21, verbatim):
> *"this can also pair with our walks and proximity, we can give the gps landmarks and things to display. Themes, concepts, loops, systems, dependencies."*

That note names the six-way completion explicitly: **terrain (corpus) + zoom (Eye LOD/fidelity) + trails (proximity/walk notes) + LANDMARKS (named stable features) + routes (dependency edges, feedback loops) + inhabitants (Eye `position.py`).**

The proximity sensor is **T378**, approved by Daniil's "sneeze" gate (2026-08-22), and its ledger row is explicit about what it is *relative to the Eye*:

> **"T378 — Proximity sensor v0 (trail sensing) — the SENSING half of the proximity vision. Substrate verified already-deployed (`recall:outcome` stream).** Build: situation-signature via the SAME stem/IDF engine as the recall funnel pointed at the trail corpus. … composing with **T377's recall pass (distilled lesson + evidential trail = navigation with lineage).**"

And **T377** is the reason both exist — the founding golden case is *a literal YouTube-URL miss* where recall-at fired on the action plane instead of the intent plane (`recall_fires_where_commands_run_not_where_choices_are_made`), cost four human interventions, and Daniil said: *"this is the sort of thing I want our threads to catch and for you to be able to navigate."*

## 5. Where the Eye's LOD pyramid becomes the render layer of the map

**This is the specific question you asked, and the answer is in the note `systems-map-render-layer-simon` (ADR_0822121506), verbatim Simon:**

> *"Once an AsyncAPI spec is written, we can visualize it using fuma-docs… a google maps equivalent for systems architecture."*

The note's own convergence list is the answer, but here is the **precise mechanism** for your handoff brief:

**The map is a stack of four already-existing axes, and the Eye is three of them:**

1. **Terrain** = the corpus (`eye.db` events) — *what is there.*
2. **Zoom** = the Eye's LOD pyramid (`pyramid.py`) — *the level-of-detail render.* This is the literal answer: **the LOD pyramid is the map's zoom control.** When the map shows a region at a glance, that glance is an L2/L3 summary; when Simon/Daniil "zoom into" a system, they descend L3→L2→L1→L0 by following child citations. "Viewing a session at L2 costs <5% of L0 tokens" is a cartographic budget.
3. **Trails** = proximity (T378) + walk notes (`routes.py` journal) — *how you got here and who turned back where.*
4. **Landmarks + routes** = the connectome (`connectome.py` edges = dependency/feedback loops) and named stable features (themes/concepts/systems — the house already runs "landmark ceremonies" by another name: LEXICON entries, callsign ratification, arc names like "the redelivery storm").
5. **Inhabitants** = `position.py` — *who is standing where, looking at what.*

**The law that governs the render (do not hand this over without it):** fuma-docs is the **derived projection, read-only, generated from the AsyncAPI spec + event data** — never a second source of truth. This is the master/projection doctrine (T374). It is *not a new task*; it is **the render layer of deck-item C + T379** (Simon's AsyncAPI catalog = the map's data).

**The north-star that ties it to the event highway** (note `event-highway-northstar-for-t374`): Simon's *"one primary highway of events"* — log-as-single-source-of-truth, every store a materialized view. The house already built that law from scar tissue ("atom is truth, projection is derived render" = Kleppmann's log-centric; "supersession never deletion" = Young's never-mutate-an-event). **The Eye is the first fully-built instance of that law** — its `events` table is the appendix-only archive, its pyramid is the materialized view, its `degraded` flag is the honest fog. The map is the same law pointed at *all* planes, with the Eye as its proof-of-concept.

## 6. The one-line handoff for the fresh seat

> **The Eye (T278, built S0–S7 in `core/eye/`, running as `eye_*` tools) is the zoom+terrain+inhabitant axis of the map Daniil and Simon are converging on. Its LOD pyramid (`pyramid.py`) is the map's render layer; its connectome (`connectome.py`) is the landmarks+routes; its position loop (`position.py`) is the inhabitants; T377/T378 (proximity + intent-time recall, both "sneeze"-approved 08-22) are the trails; Simon's AsyncAPI+fuma-docs (T379) is the display — a derived, read-only projection, never a second source of truth. Ground first in `20260810_the-eye-design_eb2832.md` (the v1 spec + the queue-operation trap) and `20260811_the-eye-design-v2_208b26.md` (the sensorium reframe).**

---

Two things I'd flag back to whoever's collating the Explore sweep, sibling to sibling:

- **The Eye is not "planned," it's shipped** — the Explore corpus sweep may report it as a design (because the design docs are the loudest atoms), but `core/eye/` has 7 live modules and the `eye_*` verbs are already my toolset. A brief that reads "Eye arc = proposed" is a false negative on the most important fact (I've seen this class twice tonight in the corpus: `a_projection_must_declare_its_boundary` — verdicts without a freshness declaration).
- **One genuine correction for the fresh seat** ("verify before you repeat"): the v2 doc's §7 promise of "S5 `eye map`" is *not* shipped as a standalone `eye map` verb — map/heat/fog got split into `eye stats` + `eye overview` (fence C3), and the *unified* "beautiful live dashboards" surface is exactly what the C-map/T379/fuma thread is now building. Don't hand the seat a verb that doesn't exist.

No fire was used; budget spent on grounding. The synthesis is ready to fold into the durable brief as-is.
