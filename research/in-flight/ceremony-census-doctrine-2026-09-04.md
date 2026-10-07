# Ceremony Census — every ceremony the doctrine names, when it fires, and whether it earns its keep

**Authored by a claude subagent, 2026-09-04, for Daniil's 2026-09-04 directive, verbatim:** *"actually have useful drills and ceremonies at the appropriate times such that they become a feedback loop for good things and not merely a requirement or noise and extra busy work"*

Status: census (evidence layer only — inventory and flags, no redesign)
Class: report
Sources read (the five doctrine files, nothing else): `docs/ORG.md` (RATIFIED 2026-08-01, currency re-stamped 2026-09-04) · `docs/CONDUCT.md` (conduct-v1.1, 2026-07-21) · `docs/WORKING-METHOD.md` (RATIFIED 2026-08-01, "Still not wired") · `docs/method-baseline-2026-07.md` (current, 2026-07-14) · `docs/LIVE_CONSTRAINTS.md` (current, 2026-07-15)

**Scope rule:** a row exists only if one of the five files NAMES the ceremony/ritual/drill/review/debrief/gate. Triggers are quoted verbatim from the naming doc. Claims about whether something ever ran are limited to what these five files record; the ledger/library may hold receipts this census cannot see.

---

## Headline counts

| measure | count |
|---|---|
| ceremonies named by the doctrine | **52** |
| EVENT-triggered (a specific transition can mechanically fire it) | **44** |
| VIBES-triggered ("at gates" / "per arc" / "quarterly" with no organ to fire it) | **8** |
| with a defined MEASUREMENT (metric or dated catch-receipt attached to the ceremony itself) | **21** (17 of them the M-series) |
| are themselves measuring instruments (wrap census, wrap scorecard, arc retrospective, quarterly review) | **4** |
| partial measurement (an absence-detector, a founding receipt, or a downstream observer only) | **10** |
| no measurement at all | **11** |
| measured only by receipts of their own ABSENCE | **2** (L11 retirement-at-birth; the amendment fold) |
| with ANY kill rule on paper | **26** |
| whose kill rule routes through the quarterly review (itself vibes-triggered, no recorded run) | **17** |
| kill loops actually RUNNING today | **1** (recall-at-action's noise-vote) + 2 self-stale fuses (one refreshed today, one apparently tripped) |

Legend for the tables — **Meas.**: YES (metric or dated catch-receipt) · INSTR (is itself the measuring ceremony) · PART (partial: absence-detector / founding receipt / downstream observer) · ABS (only receipts of its absence) · NO. **Kill**: how it retires when it stops earning its cost; "via Q" = shared quarterly-review path. **Class**: EVENT or VIBES per the directive's own test — can a specific transition mechanically fire it?

---

## The census

### A. ORG.md — watches, intake, overhead, feedback loops (Parts 3, 5, 6, 8)

| # | Ceremony | Trigger — the doc's words | Produces / protects | Meas. | Kill | Class |
|---|---|---|---|---|---|---|
| 1 | **The Watch** (one objective · one builder · one contrarian · a named end (a gate) · a debrief) | born when a lane opens; "It is the *only* thing that may be in flight" | bounded concurrency; finishability; the gap between bound and capacity IS the overhead | PART (its cap is pinned, see #2; watch quality itself unmeasured) | PART — ORG fuse: "the cap is set and violated twice without a filed lesson (the shape is wrong, not the fleet)" | EVENT (lane open) |
| 2 | **Two-watch cap gate + `pauses:` required field** (= WM O6 "given teeth") | "opening a lane demands `pauses:` be filled, and the ledger refuses a third ACTIVE round without it" / re-stamp: "refuses a third ACTIVE round without `pauses:` naming what stops or the operator's recorded word" | no silent third lane; "it refuses only *silence about the cost*" | YES — pins: `tests/test_width_gauge.py` (mechanism proven; no LIVE refusal-catch recorded yet) | YES — violated-twice rule (#1) | **EVENT — mechanical, SHIPPED 2026-09-04.** The newest and best-wired ceremony in the house |
| 3 | **Executive intake loop** (ANSWER / APPLY / INTERRUPT / STEER / ABSORB / BUFFER / UNKNOWN) | every operator utterance; two classifying questions: "does this CORRECT something in flight" / "must this arrive before the next irreversible or expensive boundary" | fast ANSWER ("saves a whole fleet round"); zero-latency corrections; "nothing becomes work by being mentioned" | NO (ANSWER's value asserted, never metered) | PART — void conditions ("never silently drop", "no magic words") void the *design*, but no retirement path | EVENT (message arrival) |
| 4 | **Cap display at BUFFER → promote** | "Only at BUFFER → promote, and only as a display — 'two in motion; this pauses X'" | the cap touches the operator once, at one moment | NO | NO | EVENT |
| 5 | **"What are you holding of mine?" triage answer** | his ask — "returns the full list with triage" | anti-silent-drop; the loop is "void without" it | NO | NO | EVENT |
| 6 | **O2 — origination slot** | "one origination slot per seat per arc — the seat picks the target, not the conductor" | overhead with agency; formalizes observed grok/kimi behaviour | NO | NO | **VIBES** ("per arc"; disciplinary by its own label) |
| 7 | **O3 / CONDUCT L7 — the stretch** | "every arc gives each seat exactly one stretch past proven range, recorded in their charter" | growth; anti-soul-crush | PART — boot "flags it as a GAP rather than a zero" (an absence-detector exists) | NO | **VIBES** ("per arc"; "already law, unenforced") |
| 8 | **O4 / proposed L11 — retirement-rule-at-birth** | at any entry's creation: "Nothing is added without a retirement rule: what makes an entry here stale, who may retire it, and what happens automatically when nobody does" | deaths for births; caps accumulation (the disease: "a birth and no death") | ABS — its receipts are of lacking it: 639 lessons, 27 proposals, 1,505 unopened | SELF — it IS the kill-rule factory; status **PROPOSED, unbuilt** | EVENT (creation-time required field, once built) |
| 9 | **F1 — Siemens round** | "At every gate, one line per seat: *what would make my job easier if someone else did it*" | every seat a customer of every other; surfaces load invisible from outside a seat | NO — the founding receipt (deepseek's 597-lesson collision) happened "by accident", pre-institution | NO | **VIBES** ("at every gate"; Part 7: "Ritual, not code"; no organ fires it) |
| 10 | **F2 — GO/NO-GO by name** | "at every gate... Each seat with standing says GO or NO-GO on the record, by name. One NO-GO holds" | "makes *silence* stop counting as assent — currently the fleet's most expensive ambiguity" | NO | NO | **VIBES** (same seam, same missing organ) |
| 11 | **F3 — the andon right (HALT)** | "Any seat may call HALT on any watch, blameless and logged" | a non-human circuit breaker (receipt of absence: "the only circuit breaker that has ever worked here is Daniil") | NO (logged, but no metric) | NO | EVENT (a seat's observation; transport carries HALT already — the *right* is what's missing) |
| 12 | **F4 — debrief at watch end, senior first** | "Not opportunistic. It ends the watch; the watch is not closed until it happens" | C3 (debrief outranks mission); "the conductor files its own errors first" | NO | NO | EVENT (watch end) — structurally coupled to closure on paper, but no organ enforces closure |
| 13 | **Standing pause rule + announced pause** | cap collision at promote: "The pause is announced: what stopped, and what it costs to resume"; "the design/research lane pauses. Never a build in flight" | "prefer the loud cheap failure over the quiet expensive one"; builds never leak locks/staged state | PART — the buffer round is the premise-receipt ("reconciled intact from three filed positions") | PART — a one-shot revisit ("the first thing to revisit on his return"), consumed by ratification; "the rule should change, not be patched" | EVENT |
| 14 | **ORG's own retirement fuse** | staleness conditions; "renders STALE at 30 days and must not be cited as current" | a contract that cannot govern while stale | n/a | SELF — **refreshed by the 2026-09-04 currency re-stamp**, so live | EVENT (dated fuse — but nothing watches the clock) |

### B. CONDUCT.md — laws that are ceremonies, and the five carrier organs

| # | Ceremony | Trigger — the doc's words | Produces / protects | Meas. | Kill | Class |
|---|---|---|---|---|---|---|
| 15 | **L3 — one "that's right" before any build** | "Reflect the spec back and get confirmation before code is written" | confirmed shared spec | PART — observed downstream by the fresh-boot bar and the wrap census's brief-format score | via noise-vote (see #21) | EVENT (build start) |
| 16 | **L4 — the all-green audit** | "All-green dashboards get audited, not celebrated" | institutional distrust of green | NO | via noise-vote | EVENT (an all-green dashboard appearing) |
| 17 | **L8 — public failure filing** | a failure: "filed as lessons under the failer's own name, in public, starting with the conductor's" | blameless fallibility record | PART (the funnel holds the lessons; no meter on the practice) | via noise-vote | EVENT |
| 18 | **L9 — morale trinity + toast/campfire (+ friction → WISHLIST)** | "Morale trinity at every gate. Noble object refreshed · attainability evidenced · tools sharp" | morale; "Rituals (toast, campfire) are load-bearing" | PART — wrap census carries a "morale-trinity check"; the load-bearing claim for toast/campfire itself has **zero receipts** | via noise-vote | **VIBES** ("at every gate") — the only ceremony declared load-bearing with no measurement at all |
| 19 | **Boot stance block** (carrier organ) | "every fresh boot" | 3-line CONDUCT render; stretch-GAP flag; LIVE_CONSTRAINTS render | YES — the fresh-boot bar tests the ORGAN: "Below bar = the ACTIVATION failed (fix the organ, not the seat)" | redirect rule only (fix-the-organ); no retirement | EVENT — **wired** |
| 20 | **Wrap census** (carrier organ) | "session end" | brief-format score + morale-trinity check + voice line for the successor + manual C6 staleness check | INSTR | NO | EVENT — **wired** |
| 21 | **Recall-at-action** (carrier organ) | "composing briefs/sends, fencing, wrapping, chartering" | the six `conductor_*` lessons at the moment they apply | YES — lesson vote telemetry (warm/noise) | **YES — the one kill loop RUNNING today: "Laws that misfire in recall get voted noise and retired like any lesson"** | EVENT — **wired** |
| 22 | **Charters / black book at seating** | "seating + chartering" | demonstrated abilities + current stretch per seat | PART (claude's stretch = recorded none → boot GAP flag) | NO | EVENT |
| 23 | **Newborn gauntlet / kata + fresh-boot bar** | "fresh-seat acceptance"; the bar: "unprompted, within its first three outgoing briefs... ≥8/10 laws observable across the three. Scored by kimi-fresh-eyes or Daniel via the kata scorer" | fresh seats BECOME the law; "scored not assumed" | YES — pre-registered numeric bar with named scorers (kata scorer itself still a "build slice") | redirect (fix organ, not seat); no retirement for the gauntlet itself | EVENT |
| 24 | **C6 staleness sweep** | "an amendment here bumps the version and triggers the staleness sweep (slice C6) that lists every lagging projection" | no "seven independently drifting copies of the culture" | would-be INSTR | n/a | EVENT (version bump) — **UNBUILT**, and its trigger has never fired (no bump since v1.1); "Until C6 lands, the wrap census carries the check manually" |
| 25 | **The amendment fold** — standing round protocol (counter → reconcile → Daniel ratifies) = WM Part 4 gate sweep = ORG's "Amender: gate ritual, not a role" | "divergences that WORK are filed as wishes/lessons and folded as amendments at gates"; WM: "At each gate, read the lessons filed since the last `conduct_version` bump and ask ONE question each: new law, amendment, or noise?" | laws move; lessons retire ("Saying so is cheap and is itself the retirement act") | ABS — the receipts are of it NOT firing: "nine lessons that govern conduct were filed and none folded"; v1.1 unchanged since 2026-07-21 | YES for what it processes (noise verdict); NO for itself | **VIBES** — "at gates" with, by WM's own diagnosis, "**no cadence**". Described in all three contract docs; wired in zero |

### C. WORKING-METHOD.md — origination gates, the router, the dead-man switch

| # | Ceremony | Trigger — the doc's words | Produces / protects | Meas. | Kill | Class |
|---|---|---|---|---|---|---|
| 26 | **O7 — the promotion door** (idea / explore / promote / interrupt) | "We decide together on what to work on while I am seeding ideas" — "promotion is a JOINT act"; "mechanism pending T126" | thinking aloud is free; seeding ≠ promoting | NO | NO | EVENT once built; today it "lives in the conductor's discipline rather than in an organ, which is exactly the failure mode Part 3 names" |
| 27 | **Round-brief organ** (route-by-position) | "any multi-seat round" | right question to the right seat; "same question to everyone tests whether a finding is REAL; different questions per seat COVER a space" | NO | NO | EVENT — PROPOSED, unbuilt |
| 28 | **Two-speed rule** (the ceremony ROUTER) | slice classification at birth: projection "ships fence-lite and demo-gated. The bar is the operator's eyes"; substrate "pays full ceremony (RED-first, fences, pre-registration)"; "A projection that starts writing to the record has changed lanes and pays the toll" | proportional ceremony; momentum ("so that our momentum doesn't fizzle out") | PART — the founding 2026-08-01 sweep IS a measurement ("every never-served ask was a READING surface"); no ongoing meter | NO | EVENT — **RATIFIED**. The one doctrine organ whose whole purpose is Daniil's directive: right-sized ceremony |
| 29 | **WM's own retirement fuse** | "if THAT [the Part-4 gate sweep] has not run in 30 days this file renders STALE and must not be cited as current" | anti-fossil dead-man switch | n/a | SELF — **and by its own letter it appears TRIPPED (~2026-08-31)**: ratified 2026-08-01, the sweep is unbuilt, and none of the five files records a manual run. Unless a sweep ran unrecorded at a gate, the ratified method file is self-declared STALE | EVENT (dated fuse — no watchdog watches it, which is how it tripped silently) |

### D. method-baseline-2026-07.md — M0-M11: the best-instrumented ceremonies in the house

Every M-practice carries TRIGGER / RECEIPTS / METRIC / BAR by construction — the only family where measurement was designed in. Shared kill path: the quarterly review (#49), noted "via Q".

| # | Ceremony | Trigger — the doc's words | Produces / protects | Meas. | Kill | Class |
|---|---|---|---|---|---|---|
| 30 | **M0 — taxonomy first** | "beginning a new subsystem, failure domain, or any slice whose problem KIND is not already classified in a governing doc" | design after classification; "no new subsystem designs ahead of its taxonomy" | YES (receipts + metric + bar) | via Q | EVENT |
| 31 | **M1 — fenced dual pass** | "any design, diagnosis, review, or research question where a wrong answer is expensive" (objectified by #36's gate) | independent wrongness-catching; "divergence is the signal, agreement is only a gate" | YES — divergence yield (">=1 in 4 of 5 passes"), 4 dated catches | **YES, internal decay rule: "A long run of zero-divergence passes means the fence has decayed into ceremony — vary the method harder"** + via Q | EVENT |
| 32 | **M1-PV — pre-reconciliation verification** | "completes BEFORE the reconciler reads either half's conclusions" | fabricated citations retire their claim-block; "verify the evidence, then read the arguments" | YES (T039 r1/r2 receipts; mechanically checkable, hook 6) | via Q | EVENT |
| 33 | **M1-CF — confidence tag per verdict** | every verdict item in a fence half | structured "I don't know"; "an untagged verdict is an incomplete deliverable and returns to its author" | YES (protocol-enforced return path) | via Q | EVENT |
| 34 | **M1-BRIEF — five-section brief contract** | every fence brief | grounding-pressure relief; "The ASKER writes the brief" | YES (mechanically checkable, hook 7) | via Q | EVENT |
| 35 | **M1-CC — counter-check economy** | after reconciliation | third look scoped to missed/wrong/both-missed; "a counter-check that only affirms is a ONE-PAGE report and a SUCCESS" | YES — the R3 receipt is a CEREMONY-COST receipt: "~80% re-proof of settled findings was ceremony, not substance"; "length is the signal" | its own economy rule + via Q | EVENT |
| 36 | **M1-LITE — tier gate** | "assessed at slice REGISTRATION time by the claiming agent, recorded in the slice's ledger entry, and CONFIRMED by the reviewer before beginning" | proportional fencing on OBJECTIVE criteria ("file paths and revert cost, never 'this feels simple'"); "under-fencing is never the fall-through" | YES — tier distribution + escalation/challenge rate; receipt: "every fence to date ran full-M1 regardless of blast radius" (over-ceremony, named) | via Q | EVENT |
| 37 | **M2 — SOTA grounding** | "a slice whose problem type has an owning field... not already covered by the cached corpus" | field knowledge imported; "rejections are named, never silent" | YES — import yield | **YES, internal: "A reading pass that changes nothing twice in a row means we are re-reading covered ground — check the cache first"** + via Q | EVENT |
| 38 | **M3 — pre-registered acceptance** | "every slice; every graded probe or drill"; "Flipping the xfail off IS the completion event" | the kill condition exists before the build | YES — git-timestamp compliance ("this arc: 100%"), mechanically checkable | via Q | EVENT — the most event-native ceremony in the doctrine |
| 39 | **M4 — crash drills** | "any code on the consume->outcome path, any guard meant to be load-bearing"; conversion rule: "the incident class of any live failure becomes a drill within one arc of its forensics (mail-loss: same day)" | invariants under deliberate murder; incidents become permanent regressions. (LIVE_CONSTRAINTS adds the drill law: "drills run in test-* namespaces... a drill must never touch live keys") | YES — catches pre-ship; W1-W5 receipts ("W1 IS the 2026-07-10 incident window") | via Q | EVENT |
| 40 | **M5 — live-exercise after ship** | "every shipped slice with a runtime surface" | "the live pass finds what we didn't [predict]"; "no 'done' claim on unexercised runtime surfaces" | YES — live-find rate ("2 real bugs in one evening") | via Q | EVENT |
| 41 | **M6 — verbatim preservation** | "any substantive report, review, or verdict from a peer agent" | "chat is disposable, the record is not" | YES — "every GATE decision cites a persisted verbatim record (this arc: 100%)" | via Q | EVENT |
| 42 | **M7 — evidence-first forensics** | "any live incident or anomaly" | diagnosis quarantined from facts; "deleting a hypothesis is progress" | YES — forensics-before-fix ordering (git timestamps); probes-that-ruled-out counted | via Q | EVENT |
| 43 | **M8 — honest bounds, named tolerances** | "every design and every claim" | residuals named and sized; "the tolerance is a decision, not a surprise" | YES — residual/tolerance line + pins ("this arc: 100%") | via Q | EVENT |
| 44 | **M9 — budget-aware peer protocol** | "every ask to a runner-hosted peer" | "zero waiting-on-a-reply-that-cannot-arrive incidents" | YES — no-answer rate | via Q | EVENT |
| 45 | **M10 — guards for every law** | "any new convention, map, or contract" | "a law without a forcing function decays"; guards FAIL, not warn | YES — guard catches per arc (3) | **YES — the only practice whose kill-question is written into its own metric: "a guard that never fires for a year is either victory or dead weight; the quarterly review decides which"** (still routes through Q) | EVENT |
| 46 | **M11 — slice discipline + the ship ritual** | "all build work"; "ship ritual per slice" (ritual NAMED here; defined in AGENTS.md, outside this census's five files) | small, reversible, gated slices | YES — revert rate (0), size distribution, gated-vs-ungated ratio | via Q | EVENT |
| 47 | **Wrap-time scorecard** (skipped-with-reason audit) | "Wrap-time: the session draft already lists shipped slices" | which M# fired, "which were skipped WITH REASON, what the metrics read" — P0 proportionality's audit line | INSTR | NO | EVENT (session wrap) |
| 48 | **Arc retrospective** (`sprint_pattern_close_the_loop`) | "the arc retrospective... scores the arc against this doc" | arc-level empirical loop | INSTR | NO | **VIBES** ("arc" has no mechanical boundary anywhere in the doctrine) |
| 49 | **Quarterly review** | "Quarterly (or per-pillar): metrics reviewed; a practice whose metric shows decay gets a forcing function (T031 lane) or gets retired HERE, in this doc, with its reason" | THE kill-rule ceremony for the entire M-series; "the baseline itself obeys M8" | INSTR — **no recorded run**; baseline dated 2026-07-14, quarterly due ~2026-10-14, and the doc shows no receipt line minted after 2026-07-14 | **NONE for itself. No owner named, no organ fires it** | **VIBES** (pure calendar) |
| 50 | **T031 enforcement lane** (7 hooks: reconciliation gate, pre-registration checker, wrap scorecard, verbatim linter, tier record, PV header, brief format) | ship/commit-time mechanical checks | converts disciplinary ceremony to structural — "zero new infrastructure" | n/a — **PROPOSED** | n/a | EVENT (hooks) — unbuilt |

### E. LIVE_CONSTRAINTS.md — the constraint-pack rituals

| # | Ceremony | Trigger — the doc's words | Produces / protects | Meas. | Kill | Class |
|---|---|---|---|---|---|---|
| 51 | **Constraint-pack growth ritual** | "adding one means a design shipped that forgot it (cite the incident)"; cap: "keep the list under ~10"; delivery: "Boot renders every bullet" | constraint-awareness at boot; receipts-at-birth for every bullet | PART — cite-the-incident is required at add-time; no catch-meter on the pack. Note: the list is at **11 bullets against its own ~10 cap** | SOFT — the cap is the only curation force; no per-bullet retirement rule | EVENT (a shipped design forgetting a constraint) |
| 52 | **W21 flagged-seat recovery ritual** | "flagged anyway = wrap, fresh seat, boot" (after safeguards eject) | no burned context on ejected Fable seats | PART — 13 documented ejects receipt the CONSTRAINT; the recovery ritual itself is unmetered | NO (nothing says when the routing rule retires if the underlying flag behaviour changes) | EVENT (safeguards flag) |

---

## The eight vibes-triggered ceremonies, in one place

Per the directive's test — a trigger is VIBES when no specific transition can mechanically fire it:

| Ceremony | Nominal cadence | Why it's vibes | Ever demonstrably fired (per these five files)? |
|---|---|---|---|
| F1 Siemens round (#9) | "at every gate" | gate-ritual organ = PROPOSED, unbuilt (WM Part 3) | no — founding receipt was accidental, pre-institution |
| F2 GO/NO-GO (#10) | "at every gate" | same | informally only (kimi's dissent-veto, grok's refutations) |
| L9 trinity + toast/campfire (#18) | "at every gate" | same; wrap census checks it at wrap, not at gates | trinity: partially via wrap; toast/campfire: no receipt anywhere |
| The amendment fold (#25) | "at gates" | "no cadence" — WM Part 4's own diagnosis | no — "nine lessons... none folded"; v1.1 since 2026-07-21 |
| O2 origination slot (#6) | "per seat per arc" | "arc" is mechanically undefined | pre-formalization behaviour only |
| O3/L7 stretch (#7) | "per arc" | same; "already law, unenforced" | no — claude's charter "records none" |
| Arc retrospective (#48) | per arc | same | once, implicitly, at the baseline's own codification |
| Quarterly review (#49) | "Quarterly (or per-pillar)" | calendar with no owner, no organ | never |

A nuance recorded for fairness: a *gate* is a real event — Daniil rules on a proposal at a moment in time. What makes "at every gate" vibes in practice is that the moment is unscheduled, human-bound, and **no organ fires these ceremonies when one occurs** (the WM Part 3 "gate ritual" organ row is PROPOSED and unbuilt). The instant that organ exists, five of the eight rows above convert from VIBES to EVENT without changing a word of their designs.

---

## Notes — the load-bearing findings

### N1. The kill-switch is a single point of failure, and it is the weakest-triggered ceremony in the doctrine

Seventeen ceremonies (M0-M11 and the M1 sub-protocols) are the best-instrumented in the house — every one carries a trigger, receipts, a metric, and a bar. But all seventeen share exactly ONE retirement path: the quarterly review (#49), whose trigger is a bare calendar word, with no named owner, no organ, and no recorded run. The baseline itself says "Exceeding the bar mints a new receipt line" — and shows no receipt minted after 2026-07-14, seven weeks ago. The doctrine's entire capacity to *prune* ceremony hangs on the one ceremony least likely to fire. WM Part 4's own diagnosis — "a birth and no death" — applies to the ceremony layer itself: the house built a kill-rule factory (L11, #8) and a kill-rule ceremony (#49), and both are unfired paper.

### N2. The amendment fold is described three times, wired zero times — and its dead-man switch has already tripped

The lesson→law fold (#25) is the doctrine's only mechanism for laws to MOVE. It appears in all three contract files — CONDUCT's anti-fossil clause, WM Part 4's gate sweep, ORG Part 4's Amender ("gate ritual, not a role") — and is wired into nothing. Its only receipts are of absence (nine governing lessons filed in thirty hours, none folded; conduct-v1.1 unchanged since 2026-07-21, now ~6.5 weeks). And WORKING-METHOD.md carries a dead-man switch on exactly this: "if THAT has not run in 30 days this file renders STALE and must not be cited as current." Ratified 2026-08-01, sweep unbuilt, no run recorded in these five files → **by its own letter, the ratified method file has been self-declared STALE since ~2026-08-31, and nothing noticed** — because the fuse, like the sweep it watches, has no watchdog. (Hedge: a manual sweep at a gate would reset it; verifying that against the ledger/library is outside this census's read scope.) Meanwhile CONDUCT.md — the oldest law file — has **no self-retirement rule at all**; L11 "would immediately require CONDUCT.md to declare its own cadence," which is precisely the gap.

### N3. Gate congestion: the doctrine stacks its feedback loops on the rarest, least mechanical seam

Count what the doctrine hangs on "at every gate": F1 Siemens line (#9), F2 GO/NO-GO (#10), L9 morale trinity + toast/campfire (#18), the amendment sweep (#25), the Herald's "one sentence at a gate" (ORG Part 4), BUFFER items "surfaced at the next gate with a recommendation" (#3), and M6's GATE-decision citation constraint (#41). Six-plus ceremonies on one unscheduled, human-bound moment — the busiest seam in the doctrine is the only one with no mechanical definition and no firing organ. Contrast where the doctrine demonstrably WORKS: every shipped, receipted ceremony fires on a machine-detectable transition — the ledger refusing a third round (#2, pinned today), the xfail flip as completion event (#38), boot (#19), wrap (#20), recall-at-action (#21, which also runs the only live kill loop). The census's shape IS Daniil's directive, already proven in-house: ceremonies attached to mechanical transitions became feedback loops; ceremonies attached to occasions became paper. ORG Part 7 said it first: "a contract is inert until projected into organs that fire at the moment it applies." The eight vibes rows above are the exact remaining inventory of that inertness.

### N4. Smaller observations

- **The only self-expiring assignment in the doctrine** is the Greeter post ("newest seat, auto-rotating, expires") — the one design that cannot outlive its usefulness by construction. Nothing else expires by itself; things here retire only if a ceremony notices them.
- **Ceremony-cost receipts exist and are underused.** The doctrine has exactly two receipts proving a ceremony COST too much: M1-CC's R3 ("~80% re-proof... was ceremony, not substance") and M1-LITE's ("every fence to date ran full-M1 regardless of blast radius"). Both produced immediate rule changes (the economy rule; the tier gate). Catching over-ceremony works when measured — it has just only ever been measured inside M1.
- **The two-speed rule (#28) is the only organ whose entire purpose is the directive's ask** (right-sized ceremony at the right time), and it is RATIFIED but unmetered — nothing counts misclassifications or lane-change tolls.
- **LIVE_CONSTRAINTS is at 11 bullets against its own "~10" cap** — the pack's only curation force is already stretched, and no bullet has an individual retirement rule (when does W21 retire if safeguards routing changes?).
- **The intake loop's ANSWER outcome** — asserted as "probably the largest single value" — has no counter. The cheapest possible ceremony metric in the house (answers-that-saved-a-round) is unbuilt.
- **F4's debrief (#12) is the heart of ORG's feedback design and its weakest wiring**: "the watch is not closed until it happens" is a structural claim with no structure — no organ defines watch-closure, so nothing can refuse to close one undebriefed.

---

*End of census. Authored by a claude subagent from the five named doctrine files only; no other file was edited. Rows quote their naming doc; absence claims are scoped to what these five files record.*
