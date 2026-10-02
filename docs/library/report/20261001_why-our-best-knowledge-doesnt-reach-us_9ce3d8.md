---
akashic_id: art_20261001_why-our-best-knowledge-doesnt-reach-us_9ce3d8
akashic_sha: acdfaed9241a
schema_version: 1
status: current
type: report
date: 2026-10-01
title: why-our-best-knowledge-doesnt-reach-us
gist: "# Why our best knowledge doesn't reach us when we need it **Akashic Aurora, knowledge reach map, 2026-10-01.** Status: current · Type: repor"
visibility: fleet
body_type: markdown
seats: []
category: [library, security, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-01T21:23:13"
updated: "2026-10-01T21:23:13"
---
<!-- GENERATED PROJECTION of art_20261001_why-our-best-knowledge-doesnt-reach-us_9ce3d8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# why-our-best-knowledge-doesnt-reach-us

# Why our best knowledge doesn't reach us when we need it

**Akashic Aurora, knowledge reach map, 2026-10-01.** Status: current · Type: report · Author: claude (Vandor), at Daniel's ask. The rendered page is `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.html` and https://claude.ai/artifact/S6gQJaj4bU1WsNzLBjpGr7 (version 4). This markdown is the library twin; where they differ, the page is the render and this is the record.

> Daniel, 2026-09-29: "How are we doing on cross domain knowledge routing and accessibility? What are the barriers to us accessing our best knowledge and how do we apply our learnings from the PDF parser ingest system to our broader knowledgebase?"

The house holds ten kinds of knowledge in a dozen planes. Only one plane, the lesson corpus, has a push path into a working seat, and that path is keyed on the command being typed rather than on what the seat is trying to do. Everything else is pull-only: it reaches a seat only if the seat already knows to go and look.

| measured | value |
|---|---|
| planes with a push path into a seat's context | 1 of 12 (lessons) |
| surfacings ever judged by a reader | 2.3% (532 of 23,333; votes last 7 days: 0) |
| domain labels across 1,529 lessons | 3 (system, empty, vfx) |
| captured events carrying a session id | 0.0% |
| tokens pushed in 24 h, credited flips | ~28k, 0 (44 injections) |
| blind eval moments for recall | 0 (the manuals shelf shipped with 40) |

## 1. What kinds of knowledge we hold, and whether they reach a seat

Daniel's lens (2026-08-26): "operational knowledge types ... recall driven by tools, recall designed for enforcement, recalls designed for play, recalls to help you remember what you wanted to remember WHEN you wanted to remember it." Reach = pushed at the moment of need; pull = a verb exists but the seat must know to run it.

| knowledge type | his words | lives in | how a seat reaches it | reach |
|---|---|---|---|---|
| Operating rules | "recall designed for enforcement" | lessons (1,529); gate_rules hand table | recall-at hook on every tool call, keyed on the Bash line; plan-time recall at prompt submit | partial: lexical, action-keyed |
| Defect history & repeats | "the mistake happened anyway" | lessons; repeat ledger (27 floor); suite baseline; task ledger | stats verb; prevention.py (190:1 prevention vs rescue, measured once) | partial: counted, not routed |
| Design intent & rulings | "the why" | fence reconciliations; library atoms; notes | boot's GROUND FIRST pointer (one doc, often stale); grep | dark: no retrieval path |
| Daniel's verbatim steers | "remember WHEN you wanted to" | transcripts (the Eye, 51,753 events); notes; the dimension register | eye find / freq, pull only | dark: pull-only |
| Live state | "what is true right now" | Redis roster, locks, lanes, doctor | boot header; doctor; roster | reaches at boot |
| Provenance & ownership | "who did what at what time" | git; authorship ledger; seat_model self-report | git blame; the who verb; lessons carry a seat id, never a model id | pull-only, unjoined |
| Verbs & tool surface | "recall driven by tools" | agent_cli discover; verb blurbs | recall-at verb lines (492 per session, 14% of pushed text) | reaches, too loud |
| Research & prior art | "in depth analysis" | research/reviewed; library atoms; manuals shelf | shelf hybrid search for manuals only; docs are grep | dark except manuals |
| Narrative & episodes | "where we are" | chronicle; handoffs; story | boot surfaces the latest handoff addressed to you | partial: last one only |
| Reasoning shapes | "primitives" (07-02) | implicit across lessons; no shape index | none; analogical retrieval is recall's named hardest miss | dark, never built |

## 2. The relationship map

The 07-28 finding still describes us: "We don't have a monolith to split. We have one cell and a dozen dark planes." The one push path runs lessons → seat, keyed on the Bash line, with a dead feedback wire (0 votes in 913 firings). Every other plane (fences and rulings, library atoms, notes, transcripts, the manuals shelf, the task ledger, the event log and touches, bus and handoffs, git and the authorship ledger, code and the module index) is dashed: the seat must already know to look. Live state alone reaches at boot. The context door (Wave 0, unbuilt) is the designed join: one anchor (`file:` `sha:` `task:` `lesson:` `session:`) to every plane, with typed states.

Joins designed and not keyed: lessons key on mutable SHAs rather than the authorship ledger's rewrite-stable key; the Eye's connectome has 39,358 edges and zero of the four intellectual kinds (fence, recall-firing, fan, supersession); lessons do not use the bitemporal supersession that codex/lifecycle.py already provides.

## 3. Why it fails, ranked by how silently

1. Feedback starvation: retirement, the usefulness factor and cross-domain promotion all consume judgments; the reader gives none (7,219 outcome rows in a week, every one `outcome: None`). Silent because the counters still print.
2. No domain axis in the data: cross-domain promotion exists in code and cannot fire (three labels across 1,529 lessons).
3. Lexical-only matching: "tappable button" vs "hit target"; the 08-08 misses M1-M3.
4. The query is the command, not the intent: a moment is an intent plus an action; M4 was right topic, wrong moment.
5. No evaluation set: the shelf shipped with 40 blind questions and a number; recall shipped with a funnel.
6. Volume without cap: ~3,600 injected items in one session, a third chrome, a seventh verb blurbs.
7. Structure absent at write time: a lesson has no path (organ / subsystem / door); 39 of 1,526 carry files_affected.
8. Dark planes: rulings, steers, docs, notes, research have no push path at all.
9. Worktree invisibility: the index follows the checkout, not the repository.

## 4. The primitives to build or unify

| # | primitive | build or unify | fixes | state | wave / owner |
|---|---|---|---|---|---|
| 1 | One target normaliser | build `context.target.v1`, one module every harness imports | four spellings of one file are one key; worktrees carry `work:<name>:` | spec sealed | W0.1, claude builds, Navi verifies blind |
| 2 | The touch, with session id | build `capture(kind="touch")` from the claude hook; forward the session id | every event joinable to the Eye | spec sealed | W0.2 |
| 3 | Recall eval set + bench | 40 blind moments with a known right lesson; `recall-bench` prints recall@5, precision@3, chrome share | the first number | spec sealed | W0.3, Navi adjudicates |
| 4 | Context door + scene | `context <anchor> --level 0|1` over git, authorship, touches, lessons, locks, focus | one anchor answers all five questions | spec sealed | W0.5, W0.6 |
| 5 | Path at write time | `learn` derives organ / subsystem / door from touches; backfill | the domain axis D5 needs | designed | Wave 1 (C2) |
| 6 | One retrieval engine | the shelf's engine (FTS5 + MiniLM + RRF + floor) serves lessons, docs, notes, bus | the meaning channel | built for manuals | Wave 2 (C3, C4, D2) |
| 7 | Intent queries and caps | query = task + last operator sentence + action; 3-4 items; chrome once | barriers 4 and 6 | designed | Wave 2 (C5) |
| 8 | Objective outcomes | the S2 adjudicator reads the stage log and the Eye | feedback without votes | prevention.py built, spec filed | Wave 3 (C6) |
| 9 | Promotion to gates | a lesson with a refusal shape that keeps earning credit becomes a door rule, never automatically | symbolic barrier becomes functional | designed (T392) | Wave 3 (C7) |
| 10 | Bitemporal lessons | route lesson retirement through `codex/lifecycle.supersede()` | "which form was in force when this ran" | exists for atoms, not lessons | unscheduled |
| 11 | Model provenance on lessons | join `seat_model`'s self-report to `learn` | a mid-session model swap no longer launders into the corpus | plane exists, unjoined | unscheduled |
| 12 | Steers that fire | a Daniel-verbatim steer carries a trigger (dimensions 1-5) | the "remember WHEN" type stops being pull-only | not started | the dimension register's promise |
| 13 | Idea-lineage edges | fence, recall-firing, fan and supersession edges in the connectome | "what influenced it" becomes a walk | 0 edges of 39,358 | unscheduled |
| 14 | A second cell | purpose-shaped retrieval over notes and rulings | the cheapest test of "unify invariants, specialize semantics" | proposed 07-28 | unscheduled |

## 5. What the seats said (2026-10-01, blind to each other)

**Heimdall (deepseek runner):** "I re-derived or re-errored on something I'd already learned." Did not reach him: his own 09-29 verdict on the velocity curve; the fence CLI argument order; the swallowed `python -c` stdout; T079's real state. Did reach him: the boot block every boot ("the one organ that works every time"); a peer handoff as a retrieval cue; one recall-at firing. First primitive: the inverse of recall-at, his own prior verdicts surfaced when he re-enters the territory, tagged as his.

**Sunshine (sol, turn-bound seat):** "Transport is not identity, capability, or continuity." Did not reach him: his own operating history, that very morning, when the boot briefer identified him as Heimdall and served Heimdall's mail; his relational history in a prior incarnation; a source fix that reached the repository but not the live world. Did reach him: typed grounding; his subject-scoped continuity note. First primitive: a subject-bound, action-time context join that refuses cross-subject injection.

**Navi (kimi runner):** "We do not lose knowledge, we fail to route it to the moment." Did not reach her: that `fence write` overwrites the slot; three capabilities she told Daniel we lacked that were pinned in code; her own 600 s ceiling in her own note. Did reach her: the boot block, "involuntary, lands before my first act"; pull recall when she knew to ask. One receipt inside her answer: she could not find her own 09-25 prior-art sweep, because it lives as a repo file. First primitive: a choice-time recall pass keyed on the situation, not the command.

**Rill (dsh web seat):** "Before knowledge can reach me, I have to be me." Did not reach him: his own 08-26 lesson about his own identity failure, which did not fire when the failure recurred the same afternoon (he booted as "deepseek" and was served Heimdall's record; the env stamp was set the whole time and the door ignored it); directed mail that stalls without a bus heartbeat. First primitive: an identity-grounded boot, one step before the choice-time pass.

**What the testimonies change:** four seats asked for one primitive by four names. All four name the same two types that never arrive, defect history including one's own prior verdicts and Daniel's verbatim steers; all four name the boot block as the organ that always works; all four say storage is not the problem. The primitive fires at the moment of choice, over an anchor the touch and the context door supply, with a subject binding so a seat's own priors return tagged as its own. Filed the same day: T418 (the identity-grounded boot, two receipts), T419 (W0.8, the choice-time subject-bound pass).

## 6. How we got here

- 2026-07-02, "the ever sharpening sword" and primitives by shape; the Tests field as first-class schema; analogical retrieval named as recall's hardest miss.
- 2026-07-12, recall as a network: six laws; funnel goodput as congestion collapse; roster N0-N7 parked at Daniel's gate.
- 2026-07-26, monolith or cells: "one cell and a dozen dark planes"; build the second cell before nine.
- 2026-08-08, the misses dossier: four measured misses, still the only ground truth recall has.
- 2026-08-26, "operational knowledge types as a segregation mechanism"; the 16-dimension register the next day.
- 2026-09-05, T392, the nine-arm redesign; untouched since.
- 2026-09-24, the manuals shelf ships: 39 of 40 blind questions right in the top 5.
- 2026-09-25, Navi's prior-art sweep, six questions plane by plane.
- 2026-09-29, the cross-domain review; filed as an opening position, absorbed the same night by the context-system round.
- 2026-09-30, the context-system reconciliation sealed: Wave 0 = schema, touch with session id, eval set, stats, scene, door.
- 2026-10-01, this map; four seats raised; first pass of Daniel's loop.

## 7. Daniel's loop, first pass

> Daniel, 2026-10-01, from work: "we could try using our easy tools for a concept or term and see what surfaces, then we could run a thorough verification pass to see what percentage surfaced and what it missed and why, implement fixes and improvements and then rerun until our easy search and what is actually there match"

Easy side: recall, eye find, knowledge-map. Thorough side: a pattern census over the full lesson dump and every file under docs, research, fences and code. The census is the oracle.

| concept | relevant lessons | easy surfaced | relevant | missed | other-plane records | surfaced |
|---|---|---|---|---|---|---|
| fence-slot overwrite | 1 | 4 | 1 | 0 | 12 | 0 |
| the captions verb | 9 | 6 | 6 | 3 | 43 | 0 |
| session_id forwarding | 0 | 6 | 0 | 0 | 7 (all fences) | 0 |

Lesson-plane recall 7 of 10; precision 7 of 16; other-plane reach 0 of 62. The telling row: the fact the whole context-system round rests on exists in no lesson, only in seven fence files, and the easy tools answered with six unrelated lessons instead of an honest zero. The fix this points at: one engine over every plane, plus a zero that names what it searched, before any ranking work. Receipt: research/in-flight/recall-experience-round-2026-10-01/first-pass-easy-vs-thorough.md.

## 8. Where we are, and what ships next

The diagnosis is complete and sealed; the first build has not started. Wave 0 is six slices, each claude plus one seat fenced, each with a pin and a drill receipt: W0.1 the schema; W0.2 the touch with session id; W0.3 the eval set and `recall-bench`; W0.4 `context --stats` for 24 h; W0.5 and W0.6 the scene and the door. Standing decisions already made: no second ledger or capture path; promotion to gates never automatic; cross-plane ids stay with the parent fence except session id forwarding; one engine for docs and lessons; minimal time-fog in Wave 0. Not settled: whether W0.8 joins Wave 0 or waits for Wave 2; the seats argue for Wave 0, and the call is Daniel's.

---

A note on this document's own fate: the day it was written, the one thing Daniel asked me to find for him, the story made as a gift on 2026-08-17, could not be reached through recall or the knowledge map because it was a loose file. This map is adopted as a library atom for the same reason; its page is also kept beside it.
