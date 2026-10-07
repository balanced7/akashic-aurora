# Ceremony census — Sunshine's blind design half

**Status:** independently authored blind half. I did not read `research/in-flight/ceremony-census-*.md` before filing this.

**Container assumed:** two-watch cap; ceremonies do not open a third watch. They attach to the event-bearing watch or enter the priority pool with `pauses:` named. The pool follows the lawful spine, with operator appetite breaking ties: **A8 > A1 > A3 > A12 > A5; A15 yes/unranked**.

## Binding rule

A ceremony survives only as **SEAM → CATCH → CONSEQUENCE → DEATH**:

- **SEAM:** a named state transition/event, never a calendar cadence.
- **CATCH receipt:** identifies a discrepancy, decision, changed belief, or prevented invalid transition. “Meeting held,” “slots filled,” and a clean dashboard screenshot are not catches.
- **CONSEQUENCE:** the caught fact changes an authority, task, pin, ordering, pause, or retirement. A receipt with no consumer is inventory, not feedback.
- **DEATH:** each instance has `dies_when`; each ceremony is reviewed after a bounded number of *eligible event firings*, not after a number of weeks. If it produces no consequential catch, automate, merge, demote, or retire it. Clean checks may still be acceptance evidence, but do not count as ceremony yield.

## Inventory binding

### 1. Fences — KEEP, but only for independence-bearing design risk
- **SEAM:** a substrate/irreversible proposal requests promotion; an existing contract is contested; or a change crosses from projection into writing authoritative state.
- **CATCH receipt:** sealed reconciliation cites at least one independently produced disagreement or omission and points to the resulting spec/pin/scope change; otherwise it records `NO_DISTINCTIVE_CORRECTION` honestly.
- **KILL RULE:** if three eligible seals for the same change class produce no distinct correction, that class defaults to fence-lite or single-review. Restore full fencing only after an escaped defect from that class. Slot completion alone never justifies another fence.

### 2. Operator/acceptance gates — KEEP
- **SEAM:** all evidence for a named authority decision becomes ready; a named NO-GO arrives; or a task seeks a transition whose authority is external to the worker (promotion, irreversible write, ship/close).
- **CATCH receipt:** a typed ruling changes ledger state, order, pause, acceptance, or scope, with dissent and unrun/blocked evidence preserved. Silence is not assent.
- **KILL RULE:** if the same gate produces the same ruling at three eligible transitions with no exercised judgment, encode the rule and retire that human gate. If a gate twice ends with no state change and no newly named blocker, merge it into the upstream acceptance transition.

### 3. Wave-close review — KEEP as the portfolio integrator, not another meeting
- **SEAM:** every item in the wave is verified/done, explicitly carried, or proposed abandoned; this is the single wave-close transition.
- **CATCH receipt:** objective-versus-outcome delta, carried debt with destination, dependency/order changes, scored forecasts, current suite delta, and one explicit decision: close/reopen/recut. It must amend the arc register or certify a cited empty delta.
- **KILL RULE:** if two consecutive wave closes only repeat task-level receipts and cause no portfolio decision, collapse wave close into an automatic ledger projection. Reconstitute review only when cross-arc coupling or a miss appears.

### 4. Failure/recovery drills — KEEP, convert mature drills into pins
- **SEAM:** a recovery invariant is introduced or changed; a production incident contradicts it; or a task seeks verify/done for a recovery path not yet failure-injected.
- **CATCH receipt:** injected fault, observed detection path, measured recovery/loss bound, and either a gap task or a passing deterministic recovery pin. “Command exited 0” is insufficient.
- **KILL RULE:** retire the manual drill once its fault is deterministic in CI and survives two relevant implementation-change seams without a novel gap. Preserve the automated pin. Revive the live drill only after an incident or substrate change invalidates the model.

### 5. Wraps / episode bookends — KEEP as intent boundaries; DROP mandatory session-end prose
- **SEAM:** intent changes, ownership changes, a task crosses a multi-session boundary, an explicit stand-down occurs, or seat death auto-closes an open episode.
- **CATCH receipt:** a cold successor can identify `why / authority / last proven state / next event / open expectation` without transcript archaeology; failed recovery names the missing field.
- **KILL RULE:** retire any bookend field never consumed by reentry/handoff across three such boundaries. Disable auto-suggestions after two false boundaries without a confirmed useful boundary; retain manual/event-driven close. A session ending with no durable arc delta needs no ceremonial wrap.

### 6. Forecast registry — KEEP for uncertain commitments, not every task
- **SEAM:** a gate commits to a consequential uncertain bet; the registered metric/horizon event arrives; or the forecast's own `dies_when` fires.
- **CATCH receipt:** evidence-backed score plus calibration delta and the decision it changes (estimate, order, mechanism, or abandonment). Late registration after outcome evidence is invalid.
- **KILL RULE:** individual forecasts die by `dies_when`. If three scored forecasts in a class change neither calibration nor a later decision, stop registering that class. If overdue scores accumulate, block new registrations until scoring debt is cleared rather than growing the registry.

### 7. Kata — KEEP as automatic truth invalidation around tools
- **SEAM:** a belt alias/tool grammar is created or edited; its underlying door changes; or `updated_at` exceeds its last verification receipt.
- **CATCH receipt:** stale VERIFIED is demoted, a grammar/runtime mismatch is exposed, or a corrected alias is rebound to a fresh door receipt. A green run is prerequisite evidence, not a “catch.”
- **KILL RULE:** retire manual kata for a tool class once CI automatically invalidates stamps on every relevant edit and verifies the same contract. Keep the automatic invariant. Any escaped stale stamp revives the manual adversarial case until encoded.

### 8. Season scoring — KEEP only at adjudication seams; otherwise PARK
- **SEAM:** a scored round closes, a claim is challenged, or a policy comparison has a shared claim set ready.
- **CATCH receipt:** policy disagreement, ranking reversal, or scorer/calibration defect results in a rule amendment, corrected claim, or named unresolved contest.
- **KILL RULE:** park scoring after two eligible round closes with no ranking/policy/action delta, or whenever inter-rater disagreement is not itself calibrated. Revive for a new policy contest or demonstrated oracle defect; never score merely because a season exists.

### 9. Debriefs — KEEP for exceptions; MERGE clean-watch debrief into episode close
- **SEAM:** expectation death, HALT/NO-GO, failed gate/drill, width-cap violation, escaped defect, or watch close with an actual plan-versus-outcome delta.
- **CATCH receipt:** one causal correction becomes a task, lesson-with-enforcement target, contract amendment, or explicit accepted risk, and names the event that will test it. Senior/conductor error goes first where applicable.
- **KILL RULE:** no standalone debrief for a clean watch with no delta. Retire any recurring prompt whose last three eligible answers produced no correction. If the same correction recurs twice, stop debriefing it and build enforcement.

### 10. Forest Walks — KEEP as a learning/publication loop; REMOVE weekly obligation
- **SEAM:** a live question has a prediction ready before evidence; a learner teach-back is submitted; or a publication candidate reaches claim-complete citation review.
- **CATCH receipt:** prediction-versus-source delta, teach-back misconception, or citation/claim defect changes the learner model or the published walk; the corrected artifact cites its evidence.
- **KILL RULE:** no live question/prediction means no walk. If two eligible walks produce neither a model correction nor observed downstream use, pause the series and change format/audience before another. Retire prompts readers do not answer; preserve useful published artifacts.

### 11. Suite baseline — KEEP, but make expiry and invalidation loud events
- **SEAM:** baseline validity expires; a failure-affecting substrate task seeks verify/done; the test authority/config changes; or a wave seeks close/ship.
- **CATCH receipt:** node-id delta (`new / fixed / inherited / unclassified`) changes ship verdict, task classification, or creates a named gap. An expired baseline automatically degrades every dependent “current/green” claim and emits an owned expectation.
- **KILL RULE:** replace time-only refreshing with commit/config invalidation wherever possible. If three refreshes have no named consumer or decision, remove that refresh trigger. Never retire the invariant at ship/wave close; retire only redundant refresh paths. Staleness without a page is a broken loop, not permission to extend TTL.

### 12. Friction readout — KEEP as an exception-triggered sensor
- **SEAM:** expectation death, failed handoff/reentry, width-cap violation, operator correction about felt load, or wave close.
- **CATCH receipt:** a threshold breach (dead-rate, time-to-settle, episode fragmentation, re-derivation) results in a routing/cap/ownership/tooling change whose next seam is named.
- **KILL RULE:** drop a metric after three eligible readouts where it neither predicts felt friction nor drives action; do not drop the whole readout because one proxy is bad. If all metrics are actionless for three eligible seams, retire the ceremony and retain raw evidence for a redesigned sensor.

## Top three noise risks

1. **Full fences becoming parallel-essay compliance.** Expose with `decision_yield = consequential reconciliation deltas / slots requested`, plus distinct-correction density and wait time per accepted correction. Three low-yield seals in one change class trigger fence-lite.
2. **Routine watch debriefs becoming templated confession.** Expose with correction-to-enforcement conversion, recurrence rate of the same correction, and proportion of debriefs with zero plan/outcome delta. Repeated prose without enforcement is negative yield.
3. **Calendar Forest Walks becoming content quota.** Expose with prediction participation, teach-back completion, corrected-belief count, citation defects caught, and downstream use. Publication count alone is explicitly not success.

(Forecasts are the runner-up risk: measure score-debt, outcome-leakage at registration, and the fraction that changes a later decision.)

## Top three missing long-horizon loops

### M1. Armed silence escalation for every cross-session dependency
- **SEAM:** fence/gate/handoff/ask opens an expectation; its deadline or owner-presence condition dies.
- **Loop:** expectation carries owner, successor pool, deadline/event, escalation route, and idempotent page; death pages the active watch and reroutes under the two-watch cap rather than silently opening a third.
- **Receipt:** page → owner/reroute decision → expectation settled or explicitly renewed with changed evidence.
- **Why:** the one-program fence waited 36h; only an armed expectation converted silence into information.

### M2. Validity leases that poison dependent claims on expiry
- **SEAM:** a TTL, commit/config predicate, or authority version becomes invalid.
- **Loop:** expiry is a first-class event, automatically marks dependents STALE/UNCHECKABLE, opens one owned refresh expectation, and blocks wave-close/ship claims that require currency.
- **Receipt:** stale claim degraded before consumption; refresh or explicit waiver cites the dependency graph.
- **Why:** the suite baseline aged 118h past TTL with no page. A TTL nobody observes is metadata, not a loop.

### M3. Durable authority/pointer integrity plus cold-seat reentry drill
- **SEAM:** boot or an arc-open/hand-off cites a governing artifact; artifact is moved/superseded; seat stands down/dies.
- **Loop:** resolve every authority pointer by immutable id, verify projection existence/currentness, then require a cold successor to recover arc state from the register + receipts. Missing pointers fail loud and route repair; prose paths are projections, not authority.
- **Receipt:** zero archaeology reentry, or a precise missing edge that becomes a repair task; moved docs remain resolvable by id.
- **Why:** the drill-arc document was cited by boot while absent from the tree. Long-horizon state cannot depend on an unchecked pathname.

## Binding summary

Ceremonies should be **interrupt handlers on meaningful state transitions**, not a calendar. The wave-close handler composes forecast scoring, suite delta, friction exceptions, and carried debt so those do not become four extra meetings. Fences and gates reserve human judgment for places where judgment changes something. Drills and kata migrate into automation as soon as their failure model is known. Every loop must page on death, identify its consumer, and contain the condition that retires it.
