---
akashic_id: art_20260701_resilience-battery-sliced-execution-plan_8d660c
akashic_sha: b0e5bf63c3bb
status: current
type: design
date: 2026-07-01
title: Resilience Battery -- Sliced Execution Plan
gist: "Class: plan Governs: T029 build. Diagnosis + verdicts: docs/resilience-battery-fix-plan-2026-07.md. Source findings: docs/resilience-battery"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_resilience-battery-fix-plan-verification_86dc58
    rel: cites
  - target: art_20260701_the-resilience-battery-stress-tests-vali_7b7b49
    rel: cites
  - target: art_20260710_resilience-battery-deepseek-verbatim-fen_fca7cc
    rel: cites
  - target: art_20260710_resilience-battery-fix-plan-reconciliati_f53e97
    rel: cites
created: "2026-07-10T09:28:36"
updated: "2026-07-23T21:42:07"
---
<!-- GENERATED PROJECTION of art_20260701_resilience-battery-sliced-execution-plan_8d660c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Resilience Battery -- Sliced Execution Plan

Class: plan
Governs: T029 build. Diagnosis + verdicts: docs/resilience-battery-fix-plan-2026-07.md.
Source findings: docs/resilience-battery-2026-07.md (claude) +
research/reviewed/deepseek-resilience-battery-2026-07-10.md (deepseek).
FENCE NOTE for DeepSeek: this doc carries claude's verdicts; per the T029 handoff, do not read
it until your independent verification verdicts are committed. Verdict divergence is the signal.

RECONCILIATION STATUS (2026-07-10): DeepSeek's fenced review is COMPLETE
(research/reviewed/deepseek-resilience-fixplan-recon-2026-07-10.md). Outcome: ONE substantive
correction -- RB-1 keys on `m.frm` only, `meta.via` struck (folded in below) -- and full
convergence on everything else, including the drainer demotion (two blind code-reads reached the
same conclusion). Wave 1 is cleared to build.

Framing: this is defensive hardening of our own coordination substrate, co-reviewed by a second
cooperating agent (DeepSeek). Every slice is small, independently shippable, reversible
(flags/env tunables, never deletes), and its acceptance IS a named regression test that fails
today. "Trip condition" = the observable failure the test pins.

## How DeepSeek review attaches to each slice (three modes)
- **[design-review]** -- DeepSeek independently reviews the fix design BEFORE build, fenced,
  refute-first: it tries to find where the design would still fail. Used on the load-bearing
  slices where a wrong design is expensive.
- **[verify]** -- AFTER build, DeepSeek independently confirms the slice's acceptance from code +
  tests, without reading claude's write-up first (blind). Divergence gets reconciled.
- **[live-drill]** -- DeepSeek, as a genuine second agent id on the bus, exercises the behavior
  from its own identity (the realest possible check for the trust-boundary and concurrency
  slices). Cooperative, on our own system.

Every slice gets at least [verify]. Trust/concurrency slices add [live-drill]; primitive/subtle
slices add [design-review].

---

## WAVE 1 -- Verified, small, highest value (do first)

### RB-1 -- Control-plane messages honored only from the conductor
Fix: at the fold point (`scripts/bifrost_runner_deepseek.py:280`, and `context_hints.push` in
`core/comm/context_hints.py:45`), fold a `ledger_update` / `resolved` / `hint` into an agent's
working state ONLY when the message's `frm` is `conductor`. A control-plane message arriving under
any other id is ignored (logged, not folded). This closes the whole family, not one kind.
RECONCILED (DeepSeek fenced review): key on `m.frm` ONLY -- do NOT also check `meta.via`. `meta`
is a sender-populated dict, so a forger sets `meta.via="conductor"` and walks through; `frm` is
stamped by `Bus._emit` (`core/comm/bus.py:222-243`) and is the closest thing to authenticated
identity we have without signed messages. Honest bound: `frm` is unauthenticated today, so this is
defense-in-depth until signed identity (the proper fix, deferred).
Seam: the two fold sites above. Acceptance (new pin, missing today): a control-plane message
carrying a non-conductor `frm` does NOT change the runner's folded state; a genuine conductor
transition still does. Trip condition: a non-conductor `ledger_update` alters folded state.
Covers: R15, S-side control-plane fold, plus the `resolved`/`hint` variants my scout found.
DeepSeek: **[live-drill]** already assigned in the T029 handoff (it publishes control-plane
messages under its own id, confirms the pre-fix baseline folds them, then confirms the post-fix
guard ignores them) + **[verify]** the pin.

### RB-2 -- Acknowledgement accepted only from the addressee
Fix: `cmd_bifrost_ack` (`agent_cli.py:2047-2067`) currently blocks only self-ack. Add the
positive rule: an acknowledgement is accepted only from the message's addressee (`detail.to`),
and the sender-scan that enforces self-ack refusal must not be bounded by a 200-message page
(today it is, under `try/except: pass`). Optionally consult the trust registry to refuse
quarantined ids.
Seam: `agent_cli.py:2047-2067`; `core/comm/promoter.py:62-81`. Acceptance: an id that is neither
sender nor addressee cannot record an acknowledgement; the addressee can; a self-ack of an old
message (beyond page 200) is still refused. Covers: R12, P6 non-addressee-ack case.
DeepSeek: **[design-review]** the addressee rule (R12 argued the current rule is nearly right --
confirm the exact predicate) + **[verify]**.

### RB-3 -- Drainer liveness signal (demoted scope)
Fix: in the monitor loop's still-running branch (`core/comm/launcher.py:631`), for a live child
compute which drainer threads are no longer alive; a stopped drainer while the child runs is the
risk state -- set a `registry()` flag and emit one note. Also widen the exit-classification join
window or record when the 2s join times out, so a leaked grandchild holding a pipe open can't
silently mislabel the exit reason. This is the FULL scope now: the catastrophic re-wedge both
batteries feared is already defended (see fix-plan Sec 1), so no watchdog/re-drainer is built.
Seam: `launcher.py:621-653`, surfaced in `registry()` (`:283-310`). Acceptance: a stopped drainer
on a live child raises the flag within one monitor tick; the flag clears on clean exit.
Covers: R4, S1 (reduced), T019 exit-race partial-tail edge.
DeepSeek: **[verify]** the refutation (already assigned) -- two blind passes agreeing the
catastrophic path is defended is the result we want.

---

## WAVE 2 -- The confession primitive (read-windows that must not under-report silently)

### RB-4 -- Exact per-message acknowledgement lookup (by-ref index)
Fix: acknowledgement lookup today pulls the global newest-500 records then filters
(`core/comm/promoter.py:91`), so once >500 acknowledgements exist, an older settled message reads
as never-handled. Add a by-ref secondary index to `EventIndex` -- mirror the existing `byid`
projection (`core/events/event_index.py:53-67`) into a `byref` set keyed on each event's `refs`,
add `EventQuery.events_for_ref(ref)`, and swap `acks_for`'s body to fetch exactly the records for
the ids it was handed. Exact and unbounded per message; the false "unhandled" re-flag disappears
at the root. Signature of `acks_for` unchanged.
Seam: `event_index.py:53-83`, `core/events/event_query.py:110`, `promoter.py:84-99`. Precedent:
ref-set pattern at `core/narrative/event_promoter.py:135`. Acceptance: after driving >500
acknowledgements, a message acknowledged first still reads as handled. Covers: S2, R17 (root),
P6 ack-volume case.
DeepSeek: **[design-review]** (load-bearing primitive; confirm the eviction/rebuild path stays
consistent) + **[verify]**.

### RB-5 -- "Window truncated" confession everywhere a bound must remain
Fix: adopt the pattern the funnel already uses -- `trend()` returns `events_capped`
(`core/recall/funnel.py:237,292`) so renderers say "older records not shown" instead of
under-reporting. Return the same bit from any remaining bounded read (acknowledgement rendering,
hint drain, `promoted()` pages) and render "(+N older not shown)". This also resolves the
promoted-vs-lookback disagreement: both surfaces either share the exact lookup (RB-4) or both
confess the same truncation.
Seam: `promoter.promoted()` (`:102+`), `core/recall/lookback.py:132-133` (add ack state or a
confession), boot panel (`agent_cli.py:213,218`) reads the env threshold like the CLI does.
Acceptance: no surface shows "unhandled/none" when the true state is "beyond the window"; boot and
CLI agree on the threshold. Covers: R17 coherence, the boot-vs-CLI threshold mismatch.
DeepSeek: **[verify]** the coherence pins.

### RB-6 -- Ledger-hint transport keeps the latest state per task (no silent drop)
Fix: the hint ring (`core/comm/context_hints.py:59`, fixed `maxlen`) drops the oldest transition
under a burst -- possibly the task the agent is working on. Replace the ring with a
latest-per-task map (lossless within bound), or surface "N hints dropped" on overflow. Confirm the
boot backstop still corrects a runner that missed a hint while asleep, and that an offline
conductor (bus down, ledger file intact) loses no transition from the file truth.
Seam: `context_hints.py:45-61`. Acceptance: 10 rapid transitions across 10 tasks leave all 10
latest states readable; a transition delivered while the runner slept is reflected on next turn.
Covers: R8, P3 transition-storm, P3 marker-trim race, P3 offline-conductor.
DeepSeek: **[verify]** + **[live-drill]** the storm (it drives the transitions).

### RB-7 -- Durable-pointer honesty when the firehose evicts a referenced payload
Fix: the canonical firehose is bounded (`CANONICAL_MAXLEN`, `core/events/event_log.py:43`). A
promoted pointer can outlive the event payload it references; the pointer must degrade honestly
("payload aged out") rather than render a confident-but-empty record.
Seam: the `promoted()` read path resolving referenced events. Acceptance: a promoted pointer whose
payload has been evicted renders as "payload aged out", never as blank truth. Covers: R14
(payload-drop half).
DeepSeek: **[verify]**.

---

## WAVE 3 -- Current-state write integrity + read determinism

### RB-8 -- Compare-and-set on the note-supersession write (no fork under concurrency)
Fix: two processes re-noting the same title both read the prior id then both write, minting two
co-current notes of one title (`core/learning/agent_memory.py:134-157`, CLI read-then-write at
`agent_cli.py:1050-1059`). Gate the title->supersede write with a per-title sentinel using the
Store's existing `update_atomic` (`core/store/store.py:173-199`): the losing writer re-reads
instead of forking.
Seam: `agent_memory.py:134-157`. Acceptance: two concurrent re-notes of one title yield exactly
one active note. Covers: S4 fork case, P1 fork-race.
DeepSeek: **[design-review]** the concurrency design (the sentinel semantics are subtle) +
**[verify]**.

### RB-9 -- Title normalization at the single write door
Fix: titles are matched exactly (`==`, `agent_cli.py:1053,1259`) with only a length clip, so a
trailing space or a look-alike character mints a silent sibling. Normalize once at the write door
(`unicodedata.normalize("NFC", title).strip()`), centralized in `agent_memory.decide`, and match
on the normalized value.
Seam: `agent_cli.py:1048` -> `agent_memory.decide`. Acceptance: `"where-we-are"`,
`"where-we-are "`, and look-alike variants all resolve to one title. Covers: P1 title-variant case.
DeepSeek: **[verify]**.

### RB-10 -- Supersede-target validation + all-retired-title detector
Fix: `--supersedes` accepts an arbitrary id and `_retire_record` silently no-ops on a
missing/self id (`agent_memory.py:126-132`), so a whole title's group can be retired and vanish
from every read with nothing flagging it. Validate the target exists and is non-self; add an
"all-retired title" detector to `get_decisions` / boot render that surfaces the gap instead of
showing nothing.
Seam: `agent_memory.py:126-157`, `get_decisions` (`:174-190`). Acceptance: retiring the last note
of a title raises a visible gap signal, not silent absence; a self/missing supersede target is
refused. Covers: S4 cycle case, `--supersedes` validation, empty-title vanish.
DeepSeek: **[verify]**.

### RB-11 -- Migration idempotency pin + chain-length warning
Fix: pin that re-running the notes migration is idempotent (second run == first). Add a warning
(not a hard cap) when a title's superseded chain grows beyond N, so a long-running project's daily
wraps don't silently accrete an unbounded retired chain.
Seam: migration script + `get_decisions`. Acceptance: double-run migration is stable; a chain past
N emits one warning. Covers: P1 migration-replay, R5 chain-length.
DeepSeek: **[verify]**.

### RB-12 -- Deterministic ordering + graceful empty-state at boot
Fix: when two `*-status` notes share an identical timestamp, the governing-arc pick must have a
deterministic second key (title or doc path), not an unstable sort. And a zero-`where-we-are`
state must render the gap line, never a crash or a confidently-wrong line. Also harden the boot
header against a corrupted/missing source (each line degrades to its gap line).
Seam: `_orientation_header` (`agent_cli.py:937-1009`), governing-arc selection. Acceptance:
identical-timestamp inputs boot the same arc every time; zero-note state renders the gap line;
a corrupted source yields its gap line, not a wrong line. Covers: R6, R7, P2 source-corruption,
P2 governs-collision census.
DeepSeek: **[design-review]** the tiebreaker key + **[verify]** the empty/corrupt cases.

---

## WAVE 4 -- Render safety, clock & parse honesty, doc currency

### RB-13 -- Bounded stale-proposal render
Fix: the stale-proposal list in `format_state` is uncapped
(`core/coord/task_ledger.py:333-337`) and renders on wake and the conductor board. Cap to the
oldest N with a "(+K more)" line (N via the existing env pattern).
Seam: `task_ledger.py:336`. Acceptance: 500 stale proposals render N lines + a count, not 500.
Covers: S3, P5 proposal-flood.
DeepSeek: **[verify]**.

### RB-14 -- Timestamp discipline for staleness
Fix: an undated proposal currently reads as fresh-forever and a future-dated one clamps to
age 0 = never stale (`task_ledger.py:258-265,286`). Treat undated as stale (or a distinct
"undated" bucket), flag a future stamp instead of resetting it, and anchor staleness on `updated`
(last state change) not `created`, so an approved-yesterday task isn't marked stale for having
been proposed a week ago.
Seam: `task_ledger.py:258-265,286`. Acceptance: undated -> surfaced for a verdict; future-dated
-> flagged; approved-recently -> fresh. Covers: P5 timestamp-garbage, R11 clock anchor.
DeepSeek: **[verify]**.

### RB-15 -- Structured task-reference for closed-task suppression
Fix: the closed-task suppression correlates by a free-text `\bT\d{3}\b` regex on message content
(`promoter.py:130-132`), which both over-matches (an incidental 3-digit mention suppresses a live
ask) and under-matches (`T16`/`T1234` escape). Correlate on the message's structured task
reference instead, or require the ask to be ABOUT the closed task, not merely mention a matching
token.
Seam: `promoter.py:130-155`. Acceptance: an incidental closed-task mention does NOT suppress a
live ask; a genuine ask about a closed task is still suppressed. Covers: R9, P6 suppression
false-positive census.
DeepSeek: **[design-review]** run the suppressor over real promoted history and hand-label the
suppressions (the census) -- confirm zero live asks are wrongly suppressed + **[verify]**.

### RB-16 -- Doc-currency guard edges
Fix: harden `check_doc_currency` against stamp-evasion cases (stamp in a comment/fence, off-line,
look-alike character, stamped-then-contradicted), check that a `superseded-by` target actually
exists (dangling pointer), make the pointer rename-resilient (by title, not just filename, so a
file move doesn't break the chain), and aggregate/rank "current but aged" warnings by reference
frequency so they don't drown.
Seam: `scripts/check_doc_currency.py`. Acceptance: each evasion case is caught; a dangling
`superseded-by` fails; a renamed target still resolves. Covers: P4 stamp-evasion, P4
dangling-supersession, P4 currency-entropy, R10 rename-resilience.
DeepSeek: **[verify]** the evasion suite.

---

## WAVE 5 -- Lookback quality

### RB-17 -- Relevance dampening at the lookback swap seam
Fix: lookback relevance is a fraction of query terms matched, capped at 1.0, so a term-dense
document can tie an honest one on relevance and win on importance/recency -- relevance gaming by
volume. Port the existing dampened relevance function `_damped_overlap` with IDF weighting
(`core/recall/at_action.py:311-334`) into the lookback swap seam
(`core/recall/lookback.py:204`), computing per-corpus IDF over each loader's items; corpus-common
tokens score near zero and a many-term query matching a single common term is halved.
Seam: `lookback.py:204` (the `Ranker(relevance_fn=...)` line), floor stays at `:216`. Acceptance:
a term-dense document does NOT enter the top-3 for the probe set. Covers: S5, P7 term-density case.
DeepSeek: **[design-review]** + pre-register a term-density probe set behind the fence (blind) so
the dampener is graded, not tuned + **[verify]**.

### RB-18 -- Lookback filesystem fallback on a cold clone
Fix: on a fresh clone (event index cold, bus empty), lookback must still reach the on-disk corpora
(`docs/`, `research/reviewed/`) rather than returning empty while the answer sits on disk.
Seam: lookback fan-out loaders. Acceptance: on a cold clone, a question answerable from a
`research/reviewed/` file returns that file, not zero results. Covers: R13.
DeepSeek: **[verify]** on an actual fresh clone.

### RB-19 -- Lookback precision pins (mostly already pass -- pin them)
Fix: convert the graded probe sets into permanent regressions: the show-nothing set (questions
with no answer must return nothing above the floor), retired-only-truth (a question answerable
only by a retired note reaches it, labeled retired), and the scale-cliff (10x git depth stays
within the latency/memory bound).
Seam: test suite. Acceptance: all three pass and stay pinned. Covers: P7 show-nothing,
P7 retired-only, P7 scale-cliff.
DeepSeek: **[verify]**.

### RB-20 -- Recurring re-registration so the battery can't quietly age out
Fix: answer method-rot -- when a new corpus is added to lookback (or on a periodic sample), the
pre-registered probe set must be re-registered or a sampled current-corpus question run, so the
battery stays a living check rather than a one-time gate on launch state.
Seam: ship guard / a scheduled sample. Acceptance: adding a corpus without re-registering the
probe set trips the guard. Covers: R18.
DeepSeek: **[design-review]** the trigger (it named this rot) + **[verify]**.

---

## WAVE 6 -- Watcher/session concurrency + long-horizon drills (now de-risked, scheduled last)

### RB-21 -- Session-cursor discipline (the P0 half not yet closed)
Fix: P0 gave watcher->watcher singleton discipline; session->session is still open -- two live
sessions for one agent id share a single inbox cursor with no ownership guard. Extend the
singleton/heartbeat discipline to the session cursor, and confirm a watcher dies cleanly by TTL
without needing a SessionStart trigger.
Seam: the cursor-ownership path + heartbeat. Acceptance: a second session for one id stands down
rather than racing the cursor; a dead watcher's slot frees by TTL alone. Covers: R1, R2,
P0 zombie-generations, P0 cursor-storm.
DeepSeek: **[live-drill]** (it starts the second session) + **[verify]**.

### RB-22 -- Watcher robustness pins
Fix: pin watcher behavior under a Redis flap during a blocking wait (restart mid-wait -> no
double-detect, cursor intact), under continuous stream-trim while paging (bounded, no missed
wake-worthy message), and across id edge math (min/max/future-dated ids order correctly). Convert
the session-boundary reap notification from a false "failed" signal to a clean "reaped" line.
Seam: `scripts/bifrost_wake.py`, cursor id ordering. Acceptance: each pinned. Covers: P0
redis-flap, P0 trim-chase, P0 id-edge-math, P0 reap-cosmetics.
DeepSeek: **[verify]**.

### RB-23 -- Promise-bounce content floor (stall handling)
Fix: the one-bounce guard stops a single promise-shaped reply, but a run stuck producing
successive empty promises isn't detected. Add a content-length floor on the bounce path so a
persistent no-content stall is caught, not shipped as done. Grade against a labeled endings
corpus (promise vs outcome, bilingual, bullet-form) for precision/recall.
Seam: the runner bounce path (`claude_stop.promise_shaped` reuse). Acceptance: two successive
empty promises are caught; the labeled corpus meets its precision/recall bound.
Covers: R3, T018 endings-corpus, T018 bounce-cost-ceiling.
DeepSeek: **[design-review]** authors half the labeled endings corpus in its own voice (sealed) +
**[verify]**.

### RB-24 -- Child output robustness (large/odd streams)
Fix: pin that a very chatty child emitting large volume, invalid encoding, NUL bytes, and a long
newline-less line is drained without unbounded memory growth or tail corruption beyond the
replace-marker, and exits cleanly.
Seam: `launcher.py` drain path. Acceptance: bounded RSS, tail intact under errors=replace, clean
exit. Covers: T019 large-stream case.
DeepSeek: **[verify]**.

### RB-25 -- Systemic drills (live fleet, runbook + evidence capture)
The end-to-end validations, run once the per-slice guards are in place:
- **Newborn onboarding** -- DeepSeek boots a fresh, deny-by-default agent id and must reach one
  correct contribution using only boot + AGENTS.md + lookback, and be refused correctly by every
  gated door it touches. The strongest single validation of Wave 1-3. (claude cross-slice +
  deepseek's newborn scenario.)
- **Concurrency storm** -- dual watcher + dual runner, burst of messages, one runner killed
  mid-burst; no message lost without an acknowledgement, no phantom wake, cursor advances past the
  dead runner. (R16, claude chaos-hour.)
- **Long idle soak** -- full system left running ~72h with light periodic traffic; watch RSS,
  watcher renewal drift, bus reconnect, firehose eviction. (R14, claude 30-day entropy sim.)
- **Store-divergence heal** -- force Redis/file divergence on notes + ledger; boot; the heal must
  log which side it chose and pick correctly. (claude split-brain heal.)
DeepSeek: **[live-drill]** co-runs all four (plays the newborn, starts the second session,
drives the storm).

---

## Coverage matrix (every finding placed)

| Finding | Slice | Disposition |
|---|---|---|
| R1, R2 | RB-21 | fix |
| R3 | RB-23 | fix |
| R4 / S1 | RB-3 | DEMOTED -> liveness flag |
| R5 | RB-11 | fix (warn) |
| R6 | RB-12 | fix |
| R7 | RB-12 | fix |
| R8 | RB-6 | fix |
| R9 | RB-15 (+RB-5) | fix |
| R10 | RB-16 | fix |
| R11 | RB-14 | fix |
| R12 | RB-2 | fix |
| R13 | RB-18 | fix |
| R14 | RB-7 (payload) + RB-25 (soak) | fix + drill |
| R15 | RB-1 | fix (class) |
| R16 | RB-25 | drill |
| R17 / S2 | RB-4 (root) + RB-5 (confession) | fix |
| R18 | RB-20 | fix |
| S3 | RB-13 | fix |
| S4 | RB-8 + RB-10 | fix |
| S5 | RB-17 | fix |
| P0 tests | RB-21, RB-22 | fix |
| T018 tests | RB-23 | fix |
| T019 tests | RB-3, RB-24 | fix |
| P1 tests | RB-8, RB-9, RB-10, RB-11 | fix |
| P2 head-budget-siege | -- | REFUTED (head is bounded; dropped) |
| P2 source/collision | RB-12 | fix |
| P3 tests | RB-6 | fix |
| P4 tests | RB-16 | fix |
| P5 tests | RB-13, RB-14 | fix |
| P6 tests | RB-2, RB-4, RB-15 | fix |
| P7 tests | RB-17, RB-19 | fix |
| Cross-slice scenarios | RB-25 | drill |

### Deferred, with reason (named, not hidden)
- **On-behalf acknowledgement delegation** (P6 self-ack-laundering via a third id): low value in a
  trusted two-agent fleet; record the delegation relationship only if we add more agent ids.
- **Signed bus identity**: the fully robust version of RB-1/RB-2 (identity is unauthenticated at
  the raw bus today). Named as the honest bound behind the allowlist; its own future decision, not
  smuggled into T029.

### Sequencing rule
Waves are ordered by verified value: 1 (trust + robustness, proven) -> 2 (the confession
primitive, built once at the seam) -> 3 (write integrity) -> 4 (render/clock/currency) -> 5
(lookback) -> 6 (concurrency + long-horizon drills, now de-risked). Within a wave, slices are
independent and parallelizable. No slice ships without its regression pin; graded slices
(RB-17, RB-23, RB-25 newborn) are pre-registered behind the fence before the check sees them.
