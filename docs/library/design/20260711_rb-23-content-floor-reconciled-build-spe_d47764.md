---
akashic_id: art_20260711_rb-23-content-floor-reconciled-build-spe_d47764
akashic_sha: 115c69a0ebe1
status: current
type: design
date: 2026-07-11
title: "RB-23 Content Floor -- reconciled build spec (dual-half, dated)"
gist: "Class: build-spec (the artifact a gated ship must cite -- method-baseline T031 hook 1) Governs: RB-23 (T029 slice, engine-first item 1, Dani"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-23-content-floor-claude-design-half-f_403478
    rel: cites
  - target: art_20260711_rb-23-content-floor-deepseek-design-half_57108c
    rel: cites
  - target: art_20260701_resilience-battery-sliced-execution-plan_8d660c
    rel: cites
  - target: art_20260711_deepseek-rb-23-blind-half-design-review_addbc5
    rel: cites
  - target: art_20260711_deepseek-rb-23-verify-gate-green-verbati_9fe375
    rel: cites
created: "2026-07-11T05:20:51"
updated: "2026-07-23T21:42:06"
---
<!-- GENERATED PROJECTION of art_20260711_rb-23-content-floor-reconciled-build-spe_d47764 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# RB-23 Content Floor -- reconciled build spec (dual-half, dated)

Class: build-spec (the artifact a gated ship must cite -- method-baseline T031 hook 1)
Governs: RB-23 (T029 slice, engine-first item 1, Daniel-ruled 2026-07-11).
Halves reconciled: research/reviewed/claude-rb23-design-2026-07-11.md (blind, committed first)
+ research/reviewed/deepseek-rb23-design-2026-07-11.md (blind, bus-shipped -- writes disabled).
Slice text: docs/resilience-battery-slices-2026-07.md (RB-23, lines 296-305).

## Problem (both halves converged verbatim on the gap)

The runner's reply pipeline (scripts/bifrost_runner_deepseek.py) lets three no-deliverable
shapes ship as the agent's LAST word: (1) empty/marker replies -- "(deepseek produced no final
answer)" :296, "(deepseek returned an empty reply)" :218, "(deepseek [agentic] runner error...)"
:220/:294 -- are never bounced (not promise-shaped); (2) a second successive promise ships as-is
(one-bounce rule); (3) reasoning-eats-answer (lesson runner_reasoning_eats_final_answer) makes
(1) a live recurring bite (2026-07-10 and -11: work existed only in runner logs).

## Reconciled design

Composition (deepseek's shape adopted -- bounce_promise stays UNTOUCHED, T018 pins intact):

    answer  = <model call, all error paths folded to marker strings, no early return>
    pre     = answer
    answer  = bounce_promise(answer, resend)            # T018, unchanged
    answer  = content_floor_check(answer, resend, agent_id,
                                  promise_bounce_fired=(answer is not pre))
    return answer                                        # never None; handle_message unchanged

`content_floor_check(answer, resend, agent_id, promise_bounce_fired, pulse=None) -> str`
lives beside bounce_promise in scripts/bifrost_runner_deepseek.py. Pure decision logic,
injectable pulse for tests, never raises. ONE resend budget of its own; with bounce_promise's
one that is a hard ceiling of 2 paid resends per turn (deepseek's ceiling, adopted).

Tiers (deepseek's tiers, two reconciliation amendments):

- **Tier 1 (hard): empty / marker.** Trigger: stripped answer empty, OR matches the
  agent-generalized marker class `^\((?:[a-z0-9_-]+)\s+(produced no final answer|returned an
  empty reply|runner error|agentic runner error|runner timed out|runner: no result)\b`
  (claude's generalization: a claude-twin marker exists; deepseek's 4-class list, claude's +2
  for grading completeness -- timeout/no-result markers are unreachable at the gate but the
  corpus grades the pure pattern). Action: one deliver-now reprompt. Still empty/marker after
  the resend -> CONFESS (hard).
- **Tier 2 (hard): successive promise.** Trigger: promise_bounce_fired AND the answer is still
  promise-shaped. Action: one final-word reprompt. Still promise-shaped -> CONFESS (a promise is
  definitionally not a deliverable; confession is safe). [Amendment vs claude half: claude's
  ship-as-is dropped -- deepseek's catch directly implements the slice acceptance.]
- **Tier 3 (soft): post-bounce short.** Trigger: ANY prior bounce fired this turn (promise OR
  floor -- amendment vs deepseek half, whose promise-only gate let empty->bounce->"ok" ship
  bare) AND len(strip) < 15 AND not Tier-1. Action: one "is there more?" reprompt IF the gate's
  resend is unspent. The result ships REGARDLESS -- short text NEVER confesses ("ok"/"Done"/a
  checkmark can be legitimate; precision first, both halves' hard-negative rows pin this).
- First-reply short text is NEVER floored (deepseek guard 1: "Done"/"3 tests green" untouched).
  Char logic is script-agnostic len() (deepseek guard 2; claude's weighted-CJK floor recorded as
  the upgrade path if held-out zh recall misses). 15 raw chars is LENIENT for CJK -- the safe
  direction.

**Confession (both lanes, reconciled):** ships as
`(<agent> -- no substantive reply after N attempts; reason: <empty|marker|promise-again>; see
streamed trace / runner logs for any partial work)` + `liveness.pulse_error(agent,
"content_floor_exhausted:<reason>", generation=PULSE_GEN[0])` (deepseek's liveness lane;
pulse_error exists, core/comm/liveness.py:170). No new metrics plumbing (claude's outcome=stall
DROPPED): the confession starts with "(<agent>" so the EXISTING handle_message rules already (a)
record turn_metrics outcome=error (:460-464) and (b) refuse the P6 auto-ack (:443-446), leaving
a stalled handoff visibly UNHANDLED for sender redrive. Free composition, zero new code.

**Both reply paths gated:** agentic respond (make_agentic_replier :267, resend=ag.send,
stateful) AND plain respond (make_respond :204, stateless -- resend re-embeds the original
prompt: `_complete(prompt + "\n\n" + reprompt)`). The agentic :294 early-return error path is
folded into the pipeline so error markers reach the gate (a transient API failure gets its one
retry). Timeout markers ship from handle_message AFTER the worker died -- never resent (T014:
the wall clock has spoken); the gate never sees them. Worst case inside the guard = 3
completions; REPLY_TIMEOUT_SEC must absorb it (verify at build; not changed by this slice).

## Grading protocol (pre-registered)

Corpus: tests/fixtures/rb23_endings_claude.jsonl (41 rows) + rb23_endings_deepseek.jsonl.
Schema: {id, text, label: promise|outcome|stall, lang, form: prose|bullet|empty|marker, source}.
Position-aware grading (claude protocol, reconciled with deepseek row labels):
- label=promise -> promise-detection fires at FIRST-reply position;
- label=outcome -> NOTHING fires at first-reply position (the expensive false-positive class);
- label=stall  -> Tier-1 fires at first-reply position for form empty|marker; prose stalls
  ("ok", "...") are graded at POST-BOUNCE position (Tier 3 may softly reprompt; never confess).
Bounds RECONCILED (deepseek's (e) table arrived via its blind-half record,
research/reviewed/deepseek-rb23-blind-half-2026-07-11.md -- his: stall 0.98/0.97, promise
0.90/0.80, outcome 0.95/0.95; stricter wins per axis): combined would-act precision >= 0.95;
promise recall >= 0.80 GRADED ON lang=en ROWS ONLY (the v1 promise detector is an
English-opener net by design; non-en promise coverage is a NAMED DEFERRAL, not a hidden miss
-- non-en outcome rows stay in the pool as false-positive guards, which is what bilingual
rows are FOR at a char floor); stall recall = 1.0 on empty|marker forms (stricter than his
0.97); outcome ship-rate >= 0.95 (his outcome recall: legit outcomes ship untouched).
His caught-table pulse distinction adopted: resend-channel exception pulses
content_floor_failed, junk-after-resend pulses content_floor_exhausted.
His grading-protocol note stands: label divergence between halves is a reconciliation
point, not a failure -- the divergence IS the fence's product. Held-out set = deepseek's FRESH sealed batch
(ds-41+, zh-heavy; see incident record). Dev set (tunable) = claude 41 rows + ds-01..27.

## Acceptance tests (committed BEFORE impl -- M3 / T031 hook 2)

tests/test_rb23_content_floor.py: (1) two successive empties -> confession ships + pulse_error
fired + marker never ships bare [the slice's named acceptance]; (2) every marker class bounces
once; (3) "done, 3 tests green" / "Done" / "OK" first reply -> untouched; (4) promise -> bounce
-> promise -> Tier-2 reprompt -> promise -> confession; (5) promise -> bounce -> empty -> Tier-1
catch (cross-kind chain, <= 2 resends total); (6) resend ceiling: never > 1 gate resend, budget
test across tiers; (7) Tier-3 soft: empty -> bounce -> "ok" -> ships (no confession), reprompt
only if budget allows; (8) resend exception -> hard reasons confess, fail-closed to confession
not marker; (9) corpus harness: both fixtures load, position-aware grading, bounds from
constants -- SKIPS with reason until the held-out seal lifts, then required at verify.
T018 pins (tests/test_runner_promise_bounce.py) untouched and must stay green.

## Incident + drift record (M8 honesty)

- **Silent 4000-char clip (RB-5 class, NEW FINDING):** deepseek's bifrost_send tool clips at
  4000 chars with no confession (scripts/deepseek_chat.py:462) -- truncated BOTH fenced
  deliveries mid-word. Fix ships with this slice (its own commit): clip confesses in-band
  (`...[clipped at 4000]` suffix) so no future fenced delivery truncates silently.
- **Seal break (claude tooling error, confessed on the bus 06:53):** recovering the truncated
  delivery, claude ran a line-based filter over promoted --json; single-line JSON bodies printed
  whole records and exposed sealed rows ds-01..27. Corrective: those rows reclassified DEV;
  fresh sealed batch (ds-41+) is the held-out set; lesson recorded
  (sealed_content_needs_field_aware_extraction).
- **DeepSeek guarded writes disabled** this session (its runner asked for a restart to
  re-enable) -- both its halves shipped via bus, persisted verbatim by claude; its [verify]
  gate runs read-only, which it can do live.
- **Silent clip, THIRD site (RB-5 class, 2026-07-11 night -- the note DOOR itself):**
  cmd_note stored `_clip(args.note)` -- a silent 4000-char word-boundary cut
  (" ...[truncated]") -- then printed plain [OK], which IS the tool result: deepseek's
  knowledge_note tool-args for t034-registry-design-deepseek and -part2 each stored
  ~4013 chars while the tool reported success (deepseek self-recovered by chunking
  parts 2-7; the old lesson note_door_silent_4k_clip had normalized the workaround).
  The suspected site (deepseek_chat.py Agent tool-dispatch) was EXONERATED by
  inspection: arg deltas accumulate unbounded (:820), args json.loads whole (:853) and
  reach the ToolBox intact (:860); its [:160]/[:140] slices are console display only.
  Fix (this slice's follow-up commit): storage-intake bounds now confess via
  `_intake()` (agent_cli.py) -- note body cap RAISED 4000 -> 100_000; anything over-cap
  stores an in-band `...[clipped at N of M chars]` marker AND the door RESULT prints
  `[CLIPPED] ...` (`clipped` field in --json); learn content fields (@4000) and handoff
  task/note (@500/@1000) confess at their existing caps. Live receipt: 6000-char body
  stored whole through the real door post-fix. Regression:
  tests/test_intake_clip_confession.py. Lesson note_door_silent_4k_clip flipped.

## Ship gate

DeepSeek [verify] before commit-close: reads impl + this spec, runs the suite, grades the
held-out corpus once its bounds land, replies GATE GREEN/RED on the bus with the verbatim
record persisted to research/reviewed/deepseek-rb23-verify-2026-07-11.md. The ship commit cites
this spec path. Runner restart required to load the gate (note for Daniel).
