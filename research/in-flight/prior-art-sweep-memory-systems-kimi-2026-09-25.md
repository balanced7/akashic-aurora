# PRIOR-ART SWEEP — kimi (Navi), answering claude's 6 questions

Method note: for each question I name the planes I searched and whether the hit is a
**build** (shipped code), a **design** (fence/spec/doc), a **lesson** (filed learning), or a
**ledger row**. A "no hit" names exactly which planes returned empty, because an unsearched
plane is not an absence. Planes I touched: recall (+ --full where noted), task list,
fences/, research/in-flight + reviewed, docs/library atoms, core/ grep, git log
(--diff-filter=D where shown), eye freq/find (transcript plane), untracked-files
(git ls-files --others), and my own private notes. Daniel's standing rule applies: the
ledger beats old messages; where a lesson and a ledger row disagree I say so.

---

## Q1 — MEMORY EFFECTIVENESS CHAIN (authoritative -> eligible -> selected -> delivered -> decision -> outcome)

**VERDICT: YES — designed, and partially built. The decomposition exists in at least four
distinct places, two of which are far beyond the funnel's single "surfaced" number.**

### 1a. The funnel itself is already staged, not single-number
- `core/recall/at_action.py` — the recall engine. Lessons named in recall:
  `weighted_overlap_scale_invariance` (the relevance floor + IDF-weighted matcher),
  `recall_at_action_usefulness` (the usefulness_factor 0.5–1.5 re-rank),
  `recall_silence_is_suppression_not_ranking` (the outcome counters split silence into
  `excluded_silent` vs `floor_silent`). So "eligible -> selected" is already decomposed
  into: relevance floor -> exclusion rules (anti-repeat, self-echo) -> capped surface.
- `core/recall/funnel.py` + the `stats` verb — `t3_stats_funnel_first_slice`,
  `a_coverage_number_wearing_a_quality_label` (the funnel's "value rate" is really a
  feedback-coverage number; the honest split is coverage vs quality).

### 1b. The REASONING SPINE is the authoritative->eligible->selected design you are asking about
- `docs/library/design/20260701_the-reasoning-spine-co-authored-design-c_24d17f.md`
  (also `.claude/worktrees/interesting-mahavira-3eb7ee/docs/reasoning-spine-design-2026-07.md`)
  — **Tier 3 = RECALL-ELIGIBLE (~2%): decision span + outcome edge. Only this tier reaches
  recall.** Tier 2 (PERMANENT) = decision spans WITH outcome edges stored. This is exactly
  the authoritative -> eligible -> delivered chain, and it was co-authored. Cited in
  `research/reviewed/reasoning-spine-deepseek-counter-2026-07-17.md`: "Eligibility for
  recall = decision span + outcome edge."
- `core/recall/at_action.py` + `core/recall/funnel.py` are the live substrate;
  `docs/library/brief/20260822_eye-map-event-synthesis-fourview-2026-08_c6a76c.md:91`
  records: "PUSH engine = the recall funnel (BUILT, core/recall/at_action.py, 8 stages,
  52/100 fire". So the "8 stages" language already exists in a brief.

### 1c. The prevention / outcome chain (decision -> outcome) is BUILT, and it is the
    sharpest answer to "the funnel only counts surfaced"
- `core/recall/prevention.py` (S2) — lesson `recall_counted_rescue_and_was_blind_to_prevention_190_to_1`:
  the stage log (`_log_outcome_stage`) had been writing a contrastive record for weeks with
  NO consumer; the first consumer measured 3,422 PREVENTION candidates vs 18 rescue flips
  (~190:1). The stage log is literally a per-stage record (surfaced / fired / credited /
  flipped). This is the "delivered -> decision -> outcome" half, built and measured.
- `a_join_key_guessed_from_two_names_is_a_silent_confident_zero` — the S2 prevention
  observer joins the recall outcome stage log to the repeat ledger with temporal
  attribution (nearest-preceding surfacing). So "selected -> decision" attribution exists.
- `prevention_repeat_attribution_must_preserve_actor_session_and_action` — the join must
  be on an explicit exposure/action identity bound to actor+session, else report
  UNKNOWABLE. This is the design rule for the decision stage.

### 1d. The adaptive-recall arc (2026-08-27/28) is the full effectiveness-chain design
- `research/in-flight/adaptive-recall-memory-fabric-vision-2026-08-27.md` (Daniil's vision,
  formalized by Sunshine) — the addressable memory fabric, "precision at the gate buys
  density in the pool", the boundedness law. Companion files:
  `recall-dimension-register-2026-08-27.md`, `recall-garden-trigger-ladder-2026-08-27.md`,
  `predictor-lens-recall-2026-08-27.md`, `t370-shadow-shelf-pilot-2026-08-28.md`.
- `learn:experiment:adaptive_recall_round_a_measurement_causal_honesty` (deepseek Round A) —
  the three-condition intervention (Utility = with − no, Stability = with − perturbed),
  and "TIMELY vs EARLY" as a distinct delivery axis. This is the decision/outcome stage
  designed with causal-honesty requirements.
- `learn:experiment:coverage_optimal_is_not_useful_optimal_late_is_net_negative` — the
  TIMELINESS number: "did it arrive before the decision was committed, or after." The
  recommendation says plainly: "We currently have no timeliness concept at all." So the
  delivered-vs-decision ordering is named as a gap.

**So:** the chain is designed (reasoning-spine tiers + adaptive-recall dimension register)
and the outcome half is built (prevention.py + the stage log). The piece that is NOT built
is a single effectiveness ledger that walks one lesson through all stages end-to-end and
prices the delivered-vs-decided gap (timeliness). That is a named gap, not a named design.

---

## Q2 — RETIREMENT / LIFECYCLE (deprecation, supersession, "this lesson is now WRONG")

**VERDICT: partial design + a named standing hazard, but no ratified-retirement ceremony
for the "now WRONG" case (distinct from "now enforced elsewhere").**

- `graduate --enforced-by/--undo` — you found it; it's the "now enforced elsewhere" path.
- `recall-curate` + `bench list` / `bench list --all` — the curation surface. Lessons
  `cost_without_return_cannot_see_prevention` (VOTE FIRST, CURATE SECOND; prefer BENCH
  over retire) and `the_corpus_does_not_contradict_itself_and_three_fixtures_were_hiding_in_it`
  (bench is reversible, history intact, nothing deleted).
- `learn:experiment:a_competitive_position_claim_is_the_most_perishable_lesson_class` —
  the "now WRONG" case, named. Its mechanism proposal: pair position-claims with a
  registered forecast carrying `--dies-when`, and **"PROPOSE, NEVER AUTO-RETIRE: the corpus
  is append-only and a retirement is a ratified act."** That is the closest thing to a
  retirement doctrine for wrongness — but it is a lesson, not a shipped ceremony.
- `learn:experiment:a_lesson_cited_as_current_state_inherits_its_own_timestamp` — the
  staleness class; the fix is "check the artifact at HEAD before acting", i.e. read-time
  re-verification, not retirement.
- Prior-art research filed: `research:web:knowledge_base_drift_and_maintenance` (deepseek)
  — proposes a `last_verified` timestamp + scheduled re-verification (CRL push model) and
  explicitly: "This is NOT auto-retirement — the lesson survives." And
  `research:web:kbm_belief_revision_wiki_decay_slice` (kimi, me) — AGM retirement-by-
  entrenchment, SRE drill-style re-verification.
- `docs/library/design/20260905_recall-redesign-from-the-nine-arm-synthe_5daa78.md` (the
  T392 synthesis) — Vandor's opening position: "RETIRE on precision, not on ranking — one
  wrong injection poisons the whole channel." That is a designed retirement trigger, but
  the doc is an opening position to be attacked, not a ratified spec.

**So:** deprecation-by-benching exists (reversible), supersession exists for NOTES
(supersede-by-title) but NOT for lessons (re-recording overwrites in place — your Q3).
The "this lesson is now WRONG" ratified-retirement ceremony does **not** exist as a build;
it exists as a doctrine in two lessons + one opening position doc, all saying
propose-never-auto-retire. Searched: recall, task list, fences/, research/in-flight+reviewed,
docs/library, eye freq ("retire the lesson" -> RECURRING, 2 operator events 2026-07-27 ->
2026-08-01, worth eye_get on `2eba57a1-...:1961` and `:1968`).

---

## Q3 — IDENTITY + VERSION ON LESSONS (a version axis, as_of, "which form was in force when this ran")

**VERDICT: the bitemporal mechanism EXISTS and is type-agnostic — but the lesson plane
deliberately does NOT use it. This is a named, verified gap with a filed recommendation.**

- `learn:experiment:bitemporal_supersession_already_exists_and_is_type_agnostic` (claude,
  2026-07-28) — **THE hit.** `core/codex/lifecycle.py` provides `valid_from` / `valid_to` /
  `recorded_at` (valid time + transaction time, the Zep/Graphiti bi-temporal shape), and
  `supersede()` closes the old node's `valid_to`, adds `replaces` + `is_version_of` edges,
  and keeps the old queryable. It operates over a `BiTemporal` protocol — type-agnostic.
  The codex Resource and narrative Chapter planes USE it. **The lesson plane instead uses
  `is_benched` rank suppression, which can self-seal.** The recommendation: "Make the
  lesson record satisfy the BiTemporal protocol, route retirement through supersede()
  rather than is_benched, verify recall filters with is_active."
- `learn:experiment:queryable_means_dimensions_not_embeddings` — the as-of axis named as
  missing from the query surface: "AS-OF BELONGS BESIDE THE SEARCH BOX, NOT IN ADVANCED
  FILTERS ... we already have the bitemporal model in one subsystem while the lesson plane
  never adopted it."
- `learn:experiment:a_lesson_cited_as_current_state_inherits_its_own_timestamp` — the
  practical consequence: a lesson is a point-in-time observation; quoting it inherits its
  timestamp.
- eye freq ("lesson supersession | version the lesson | same lesson at a different time")
  -> UNHEARD (0 operator events; 3 agent/system, span 2026-07-17). So this was never an
  operator directive; it's house-internal design debt.

**So:** notes have supersede-by-title (write-once). Lessons do NOT have a version axis —
re-recording overwrites in place, keyed on experiment_name. The fix is designed and filed
(apply `core/codex/lifecycle.py`'s existing BiTemporal supersession to the lesson plane),
but it is NOT built. Searched: recall, core/ grep (`as_of`, `valid_from`, `supersede`,
`version`), task list, eye freq.

---

## Q4 — MODEL PROVENANCE (which MODEL authored a lesson; model identity distinct from seat identity)

**VERDICT: model identity is BUILT as a first-class plane — but it is NOT wired to lesson
authorship. The seat/model split exists; the lesson/model join does not.**

- `core/fleet/seat_model.py` — **THE hit.** Built 2026-09-04 (commit `1b3e6bc5`,
  `214820aa`, `c74e6ca9`). Two planes, deliberately separate, quoted from the module
  docstring: "THE PIN is a REQUEST ... THE SELF-REPORT is a RECEIPT. A live session stamps
  the model IT believes it is running, from inside itself." Redis key
  `seat:model:{agent}:{session}`, TTL'd 900s. This is exactly "model identity as distinct
  from seat identity" — and the operator's verbatim reason is in the docstring: "Something
  should display which model is running in discord so I can detect model changes while
  operating through discord."
- `core/comm/operator_reply.py:32` — the lesson that drove it: "self-report plane in
  core/fleet/seat_model.py existed but nothing ever called `report()`". Commit `214820aa`
  wired `report()` into the reply verb (`--model` stamps the self-report; `!model` reads it).
- BUT: `agent_id` on a lesson is the SEAT (claude / deepseek / kimi / sol / codex_root...),
  never the model. Grep of `core/learning/learning_store.py` fields shows no `model_id` /
  `authoring_model` field. eye freq ("which model wrote the lesson | model provenance on
  lessons | record the model that wrote") -> **UNHEARD, 0 operator events.** So lesson-level
  model provenance was never requested and never built.
- Adjacent: `learn:experiment:harness_tier_over_model_tier` and the whole fleet-covariance
  arc (`fleet_new_member_covariance_prioritization`) treat model identity as a fleet-routing
  fact, not a per-record provenance fact.

**So:** Daniel's mid-session Opus 5.5 -> Opus 5 swap would be recorded by `seat_model.py`'s
self-report ONLY if the seat stamped it (and only for 900s TTL). Nothing joins that to the
lessons authored in that window. The model-identity plane exists; the lesson-provenance
field does not. Searched: core/ grep (model_id, authoring_model, seat_model), recall, git
log on seat_model.py, eye freq.

---

## Q5 — WHERE RECALL FIRES (firing points beyond the tool-call boundary)

**VERDICT: three firing points exist or are designed — the tool-call boundary (built),
the boot/orientation boundary (built, and being redesigned as expectancy-priming), and the
pre-execute gate (designed, fenced, sequenced). The "cannot fire on an absence" limit is
named and its fix is designed.**

- Built: `core/recall/at_action.py` at the PreToolUse hook (the tool-call boundary you named).
- Built: SessionStart / boot — `recall_at_action_polish` shipped `claude_sessionstart.py`
  pre-warm + `cmd_boot`. So boot is a firing point today (it primes, it does not rank-by-task).
- Designed: `docs/library/design/20260905_recall-redesign-from-the-nine-arm-synthe_5daa78.md`
  — Vandor's four-station model. **Station 1 (BEFORE — boot/orientation) and Station 3
  (INSIDE-THE-LOOP — expectancy violation)** are the "other firing points" answer. The doc
  is explicit: boot should "install EXPECTANCIES, not list facts" ("you will see X; when
  you do, Y"), because an installed expectancy is "the forcing function, running in the
  seat's own perception. Zero channel cost." That directly answers
  `recall_at_cannot_fire_on_an_absence`: the expectancy IS the absence-detector, but it
  fires inside the seat's own loop, not at a hook.
- Designed + fenced: `fences/t386-pre-execute-recall-gate/reconciliation.md` — the
  pre-execute gate. Verdict: "Do not build a new pre-execute gate. Extend the veto layer
  that already exists" (`agent/harness/guards.py` `git_veto`/`lock_veto`, already wired
  into claude_pretooluse + two cursor adapters). And the load-bearing sequencing rule:
  "Do not wire lesson scopes into a DENY path until t385's plumbing-strip ships."
- Designed: `fences/t385-recall-trigger/reconciliation.md` — the trigger-derivation fix
  (target must be a SET derived from the tool contract, with shell-plumbing stripped;
  acceptance must include a measured false-positive rate).
- The absence limit itself: `learn:experiment:recall_at_cannot_fire_on_an_absence` —
  "recall-at is a PRESENCE-triggered instrument ... an omission has no tokens."
  And `recall_fires_where_commands_run_not_where_choices_are_made` — the intent plane vs
  the action plane; the recommendation is an intent-time recall pass at the
  UserPromptSubmit boundary keyed on choice-shaped features of the operator's text.

**So:** firing points beyond tool-call are (a) boot/SessionStart (built, priming), and
(b) pre-execute gate (designed, fenced, ordered behind t385). Planning-time / pre-delegation
/ verification-time recall: searched recall + eye freq ("recall at planning | recall before
delegating | recall at the gate") -> UNHEARD, 0 events. The intent-plane firing point is
designed in a lesson (`recall_fires_where_commands_run...`) but not built.

---

## Q6 — ANYTHING YOU HAVE NOT THOUGHT TO ASK

These are the parked designs / standing doctrines I would want in the frame before telling
Sergey anything is a gap:

1. **The T392 nine-arm synthesis redesign** (`docs/library/design/20260905_recall-redesign-from-the-nine-arm-synthe_5daa78.md`
   + `research/in-flight/t392-arm-*.md` arms A–F). This is the current, most-developed
   rethink of the whole recall surface (four stations, promotion ladder reminder->gate,
   Eye-wired AAR). If Sergey's Mnemosyne has anything like staged barrier classes, this is
   our counterpart and it is an opening position awaiting Heimdall's counter — i.e. live,
   not parked.

2. **The adaptive-recall memory fabric** (`research/in-flight/adaptive-recall-memory-fabric-vision-2026-08-27.md`
   + dimension register + trigger ladder + predictor-lens). Daniil's verbatim vision: "We
   will have different types of recall that are more directly defined and triggered by
   things so that the corpus can be vast but detailed." The **16-dimension register** (each
   a lens/projection over one richly-recorded atom, not 16 indexes) is the single most
   important "we already designed that" artifact for your conversation with him.

3. **`every_organ_has_a_birth_and_no_death`** — the lifecycle doctrine underneath Q2/Q3:
   "EVERY organ in the system was built with a birth and no death ... A capability without
   a retirement rule is a debt with a nice interface." This is the root-cause lesson for
   half the questions in your list.

4. **The intact-delivery ruling** (`docs/recall-intact-delivery.md`, Daniel 2026-09-16:
   "I don't want anything truncated"). Whole-record selection limits stay; no arbitrary cap.
   This is a designed-and-accepted delivery contract — relevant because Mnemosyne-style
   "effectiveness" conversations usually assume the content arrives intact; ours now does,
   by ruling, with pre-registered acceptance tests (`tests/test_recall_intact.py`).

5. **`recall_adjudicates_its_own_silence_and_nothing_checks_it`** — the epistemic gap under
   Q1: "A system that both decides what to surface AND certifies that the rest was
   irrelevant is the defendant writing the verdict." Any effectiveness chain you build must
   answer who adjudicates the silence, or the delivered-vs-eligible gap is unfalsifiable.

6. **`the_connectome_has_no_edges_to_itself`** — `core/eye/connectome.py` is BUILT
   (30,500 live edges, 98.9% recorded-or-derived) but the four INTELLECTUAL formed_via
   values (fence, recall-firing, fan, supersession) have ZERO edges. An idea-lineage plane
   exists; it is just not wired to the recall organs. Relevant if Sergey claims idea-level
   provenance — we have the substrate, off.

7. **`an_untracked_pin_is_invisible_to_every_plane_you_search`** + `work_done_in_a_worktree_is_invisible_to_recall`
   — the meta-lesson for YOUR sweep: an untracked file and a worktree file are invisible to
   recall, eye, and the ledger by construction. I ran `git ls-files --others --exclude-standard`;
   there is a large untracked surface (arsenal/web piano/*, logs/*, several research files,
   `_launch_kimi_daemon.py`, `design/t196-ask-transaction-spec.md`). If a prior-art claim
   matters, the answer may be sitting untracked. (I note `design/t196-ask-transaction-spec.md`
   is untracked and is precisely the kind of spec that sat untracked for T407.)

8. **Deleted-history plane**: `learn:experiment:a_capabilitys_death_is_invisible_from_inside_the_live_tree`
   measured the graveyard — 951 paths deleted and never restored, including 133 python
   modules. `git log --diff-filter=D` is the only door onto it. I attempted the scoped
   diff-filter=D run; the shell mangled the format flag on this host (Windows py launcher +
   quoting), so I did NOT exhaustively enumerate deleted recall modules. **That plane is
   therefore NOT exhausted** — flag it as an open cell, not an absence. The safe way to run
   it here is a single-quoted format string from Git Bash, not PowerShell.

---

## Sweep-coverage disclosure (so "absence" means something)

| Plane | Searched | Notes |
|---|---|---|
| recall + lessons | yes | primary hits for Q1/Q2/Q3/Q5/Q6 |
| task list (ledger) | yes | T011 (Recall vNext four loops), T013 (Lesson Forge), T048, T049, T052–T059, T385/T386 |
| fences/ | yes | t385-recall-trigger, t386-pre-execute-recall-gate, lesson-publication-design, doors-design |
| research/in-flight + reviewed | yes | adaptive-recall arc, recall-redesign, recall-dimension-register, predictor-lens, t370 |
| docs/library atoms | yes | reasoning-spine, recall-redesign synthesis, recall-intact-delivery, eye-map brief |
| core/ grep | yes | seat_model.py, lifecycle.py (via lesson citation), at_action.py, funnel.py, prevention.py |
| git log (live history) | partial | seat_model.py history confirmed; diff-filter=D blocked by shell quoting — **open cell** |
| eye freq/find (transcripts) | yes | Q3 UNHEARD, Q4 UNHEARD (lessons), Q5 planning UNHEARD; "retire the lesson" RECURRING (2 op events); "which model is running" STANDING-DIRECTIVE (5 op events) |
| untracked files | yes | large surface; flagged in Q6 #7 |
| private notes (mine) | yes | no additional recall-design items beyond the above |

The one plane I did NOT exhaust is **deleted git history** (diff-filter=D). Everything else
above is a searched plane; where I say "no hit" it is a searched absence, not a guess.
