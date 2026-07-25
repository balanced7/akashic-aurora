# Method Baseline -- the codified practices, with receipts, metrics, and bars

Status: current  (2026-07-14)
Class: contract
Amended 2026-07-14 (T049 fence-protocol v2): M1-PV, M1-CF, M1-BRIEF, M1-CC inserted into
M1; M1-LITE added as the proportional tier; enforcement lane extended. Provenance:
deepseek draft (docs/library/report/20260714_deepseek-t049-fence-protocol-v2-draft-20_ce18d3.md) + claude
cross-check (docs/library/report/20260714_claude-cross-check-t049-fence-protocol-v_d91e76.md, two A3 adjustments
folded) + Daniel ratification via directive 2026-07-14. All additions; nothing removed.
Governs: HOW all system work is done (the companion to AGENTS.md's WHAT). Daniel's
ruling 2026-07-11: high-value events stop being one-time highlights -- they become the
repeatable, EMPIRICAL baseline to match or exceed. A practice without a measurable
signal is an aspiration, not a baseline; every entry below carries its metric.
Method: fenced dual codification (this doc = claude half + deepseek's blind bus half,
reconciled -- the doc was built by the practice it codifies), then a third-reviewer
pass (GPT critique via Daniel, 2026-07-11, persisted verbatim) triaged per M1 and
folded: M0, the principles layer, outcome-metric bias, and the phase map came from it.

## Principles (what the practices serve)

P0. PROPORTIONALITY -- the cost of the methodology scales with the cost of being
    wrong. A typo needs no fence, no SOTA read, no drills; a coordination primitive
    needs all of it. The anchor is REVERT COST, not self-assessment (deepseek's
    sharpening: "what breaks if we revert this?" is objective; "this feels cheap" is
    the loophole) -- state corruption, trust-boundary exposure, or cross-agent
    contracts mean expensive; a cleanly revertible diff means cheap. Every practice
    below binds through its TRIGGER, and triggers answer that question first. This is
    the governor that keeps the method powerful instead of burdensome -- the standing
    frugality directive generalized. The wrap scorecard's skipped-with-reason line is
    the audit.
P1. TRUTH FROM EVIDENCE -- claims carry dated receipts; forensics precede diagnosis;
    the live system outranks the model of it.  (M5, M6, M7, receipts everywhere)
P2. WRONGNESS CAUGHT BY INDEPENDENCE -- separate contexts, different methods,
    refute-first; agreement gates, divergence teaches.  (M1, the ReferenceState idea)
P3. FAILURE IS EXERCISED, NOT HOPED AWAY -- name the kill condition before building;
    murder the pipeline on purpose; pin the tolerances you choose.  (M0, M3, M4, M8)
P4. KNOWLEDGE OUTLIVES THE SESSION -- verbatim records, lessons at flips, guards for
    every law; chat is disposable, the record is not.  (M6, M10, the funnel)

## Lifecycle map (where each practice fires)

  Discovery      M0 taxonomy-first, M2 SOTA grounding, M7 forensics
  Design         M1 fenced dual pass, M8 honest bounds
  Build          M3 pre-registration, M11 slice discipline
  Verification   M4 drills, M5 live-exercise
  Preservation   M6 verbatim records, M10 guards
  (M9 peer protocol spans all phases. The map is iterative, not linear -- any practice
  fires whenever its trigger trips; a verification find reopens discovery.)

## The practices

### M0. Problem taxonomy first
TRIGGER: beginning a new subsystem, failure domain, or any slice whose problem KIND is
not already classified in a governing doc.
PROTOCOL: classify the problem formally (what IS this: delivery semantics? failure
detection? canonicalization?) -> name the owning field -> define SUCCESS and FAILURE
(the kill condition) -> only THEN design. The classification is written where the
build will cite it.
RECEIPTS: the robustness SOTA map (13 problem types -> fields -> verdicts, 07-10) and
the liveness taxonomy A-F -- the third reviewer's judgment, concurred: this practice
changed the project's direction more than any individual robustness feature.
METRIC: outcome-flavored -- design changes attributable to the classification (the
fencing token, the sentinel, and the 5-window scope-down all trace to a taxonomy
entry); proxy -- slices whose governing doc names their problem type.
BAR: no new subsystem designs ahead of its taxonomy.

### M1. Fenced dual pass, method-diverse
TRIGGER: any design, diagnosis, review, or research question where a wrong answer is
expensive (load-bearing primitive, trust boundary, root-cause call, SOTA verdict).
PROTOCOL: both agents work the SAME question from SEPARATE contexts, no reading the
other's half until yours is committed; REFUTE-FIRST framing on reviews (the brief asks
the reviewer to break the design, not bless it); vary the METHOD, not just the analyst
(static code-read vs live-drill; top-down taxonomy vs bottom-up traces). Reconcile with
the explicit triage (deepseek's vocabulary, adopted): CONVERGED -> adopt,
COMPLEMENTARY -> adopt both, DIVERGENT -> rule and record. The reconciled BUILD SPEC is
the gate artifact -- the design-review record the build cites. Divergence is the
signal, agreement is only a gate (Knight-Leveson: correlated blind spots are real;
convergence is evidence, never proof; the drill outranks any agreement).
M1-PV. PRE-RECONCILIATION VERIFICATION PASS (mandatory step 1). Before any
reconciliation triage (converged/complementary/divergent), the reconciler GLOBS every
file:line citation in BOTH fence halves against the live repo. A citation that resolves
to a non-existent file, a path with no matching glob, or a line number beyond the file's
actual length INVALIDATES the section containing it. INVALIDATION is section-scoped: one
fabricated citation retires its enclosing claim-block, not the whole report; invalidated
sections are recorded with their offending citations in the reconciliation header. A
citation to a DESIGN-ONLY artifact is valid if the cited design document exists AND the
claim is explicitly marked design-level; a citation that fabricates implementation
detail against a DESIGN-ONLY seam is an automatic invalidation (grounding pressure at a
no-code seam induced it -- the T039 r1/r2 receipts). Renamed files RECLASSIFY (fuzzy
filename match), never invalidate. This pass completes BEFORE the reconciler reads
either half's conclusions: verify the evidence, then read the arguments.
M1-CF. CONFIDENCE FIELD PER VERDICT. Every verdict item in a fence half carries exactly
one tag -- CERTAIN (citation-grounded to an existing file:line or design-doc section),
DESIGN (about a not-yet-built artifact, grounded in the governing spec; no fabricated
code paths), INFERRED (grounded in behavior/patterns, not a direct citation; weighted
accordingly), or UNCERTAIN (the author cannot resolve it from the inputs -- a structured
"I don't know" that prevents silent omission, not a failure). Hedging prose never
substitutes for the tag; an untagged verdict is an incomplete deliverable and returns to
its author. (Fence-lite reviews: recommended, not mandatory.)
M1-BRIEF. BRIEF FORMAT CONTRACT. Every fence brief is one file with exactly FIVE
sections in order: (1) CHARTER -- one sentence, fence kind + the question at stake;
(2) INPUTS -- itemized paths that EXIST at brief-write time; DESIGN-ONLY fences state
"DESIGN ONLY -- no implementation exists; cite only the design docs listed" (the
grounding-pressure relief valve, T039 r1 receipt); (3) RULES OF ENGAGEMENT -- this
fence's protocol, blindness, phases, deliverable path; (4) THE QUESTION -- verbatim or
verbatim-close, no analysis; (5) OUTPUT CONTRACT -- exact deliverable path(s), format
(verdict-per-item with M1-CF tags), bus-reply contract (pointer-only vs full). Missing
any section returns the brief; extra sections go AFTER the five. The ASKER writes the
brief; a peer who believes the question is ill-posed records that as a D-item, never by
rewriting the brief. (Fence-lite: sections 1, 2, 4, 5. Counter-checks inherit the parent
brief plus a one-line scope addendum.)
M1-CC. COUNTER-CHECK ECONOMY. A counter-check (third look, after reconciliation) is NOT
a re-run: its scope is (a) what the reviewer missed, (b) what the reviewer got wrong,
(c) what BOTH halves missed. AFFIRMED verdicts get ONE LINE with a one-sentence reason
(a bare AFFIRM is insufficient -- the reason proves the look); REFUTED verdicts and
MISSING items get full evidence, same standard as an original half. A counter-check that
only affirms is a ONE-PAGE report and a SUCCESS -- the fence held; length is the signal
(the R3 receipt: ~80% re-proof of settled findings was ceremony, not substance).
RECEIPTS: meta.via forgery hole (RB-1 recon, 07-10); Store.srem leak (RB-4 review,
07-10); mail-loss-paging ruling stale against hour-old RB-26 code (L2 read, 07-11);
single-sample stall trigger would false on Redis blips (L2 recon, 07-11).
METRIC: divergence yield = substantive divergences caught per dual pass (this arc: >=1
in 4 of 5 passes); unique-find ratio per method (static-only vs dynamic-only finds --
over-reliance on one method shows here, deepseek's metric); refute-induced-change rate
on design reviews (RB-4: 1 mandatory change). A long run of zero-divergence passes
means the fence has decayed into ceremony -- vary the method harder.
BAR: every load-bearing decision shows a reconciliation record; zero solo-shipped
trust-boundary changes.

### M1-LITE. Fence-lite: single-blind + review (the proportional tier)
TRIGGER: assessed at slice REGISTRATION time by the claiming agent, recorded in the
slice's ledger entry, and CONFIRMED by the reviewer before beginning (mis-rated slices
escalate lite->full or are challenged full->lite with a one-line reason). The gate is
OBJECTIVE -- file paths and revert cost, never "this feels simple":
  1. FULL FENCE (M1) -- ANY of: (a) blast radius >= 3 files AND any file in core/comm/,
     core/trust/, core/foundation/ (the whole pillar: Store AND Ledger are both
     poison-on-revert surfaces -- claude cross-check adjustment 1; list is extend-only),
     or a coordination primitive; (b) revert cost = DATA LOSS, STATE CORRUPTION, or
     CROSS-AGENT CONTRACT BREAK (a bad ledger event survives the revert); (c) the change
     touches a Trust Boundary (auth, capabilities, ACL, secrets, agent identity, bus
     addressing); (d) the change modifies THIS document or AGENTS.md.
  2. FENCE-LITE -- ALL of: (a) blast radius >= 3 files, none in the full-fence paths;
     (b) revert cost = WORK LOST only (clean revert, nothing poisons state); (c) the
     change is a capability, design decision, or cross-module refactor where review
     adds value beyond a linter. One agent authors, a DIFFERENT agent reviews
     adversarially (break it, not bless it); no blind half, no reconciliation.
  3. NO FENCE -- ALL of: (a) blast radius <= 2 files, none in the full-fence paths;
     (b) trivial revert; (c) mechanical nature (typo, rename, comment, bugfix with a
     pre-registered pin).
  DEFAULT CLAUSE (claude cross-check adjustment 2): a change that fits neither tier 2
  nor tier 3 takes FENCE-LITE -- under-fencing is never the fall-through.
  Daniel's word overrides any tier in either direction.
RECEIPTS: every fence to date ran full-M1 regardless of blast radius -- T039 and the
recall-networking fence were DESIGN/research-stage (no revert cost beyond a doc) yet
took blind halves + reconciliation + counter-check, violating P0 proportionality;
T043 (core/comm packet law) earned every full-fence step and the gate confirms it.
METRIC: tier distribution per arc + escalation/challenge rate at reviewer confirmation;
M1's own ceremony-decay metric (zero-divergence streaks) read alongside it.
BAR: zero full-fence-path changes shipped below full fence; every registered slice
carries its recorded tier.

### M2. SOTA grounding before building
TRIGGER: a slice whose problem type has an owning field (delivery semantics, failure
detection, concurrency, retrieval...) not already covered by the cached corpus.
PROTOCOL: classify the problem formally -> name the field -> fetch primary sources into
research/sources-cache/ (gitignored; repo is public) -> BOTH agents read and verdict
blind (ADOPT/ADAPT/REJECT-with-reason, scoped to this fleet) -> reconcile into the
governing doc. Web-verify citations (models hallucinate papers). Rejections are named,
never silent -- the ceiling stays visible.
RECEIPTS: fencing token import (Kleppmann, 07-10); reply_sent sentinel + SIGKILL-only
launcher (deepseek deep-read, 07-10); crash sweep scoped from every-IO-line to 5 windows
(SQLite/FDB, 07-10); mutation testing scoped to a one-shot 8-guard list (07-10).
METRIC: import yield = design changes per reading pass (deep-read 07-10: 4 adopted
changes; L2 read 07-11: 3 divergences, 2 adopted). Also: build commits cite the map
verdict they implement. A reading pass that changes nothing twice in a row means we are
re-reading covered ground -- check the cache first (Daniel's ruling 07-11: L1 follow-up
needed zero new research; the cache decides).
BAR: no slice in a newly-touched problem field builds without its map entry.

### M3. Pre-registered acceptance (the kill condition comes first)
TRIGGER: every slice; every graded probe or drill.
PROTOCOL: the acceptance is a NAMED failing test (or strict xfail) committed BEFORE the
fix builds; graded batteries and rubrics commit behind the fence before the checked
thing exists. Flipping the xfail off IS the completion event.
RECEIPTS: RB-4 acceptance pre-registered as strict xfail 07-10, flipped green same
night; Newborn Gauntlet rubric committed before the newborn existed; D1-D5 drill
windows named in the tier doc before any L1 code.
METRIC: pre-registration compliance -- for each slice, the acceptance test's first
commit timestamp <= the implementation's (checkable in git history). This arc: 100%
of T030 slices.
BAR: no slice ships whose acceptance postdates its implementation.

### M4. Crash the pipeline on purpose (drills as acceptance)
TRIGGER: any code on the consume->outcome path, any guard meant to be load-bearing.
PROTOCOL: enumerate the crash windows (named killpoints), murder the process at each,
assert the invariant + compare against an INDEPENDENT reference encoding
(ReferenceState pattern -- a transliteration, not the same code); shrink the timeout
knobs (AKASHIC_TIMEOUT_MULTIPLIER) so timeout paths actually exercise; seed-stamp runs.
RECEIPTS: W1-W5 drills 07-11 -- W1 IS the 2026-07-10 incident window, now a permanent
regression; the drills tripped the crash-only lease discipline live (lingering lock)
and proved the reap path.
METRIC: outcome first -- failures caught pre-ship by drills (W-drills proved the L1
semantics before any production crash could) and incident classes converted to
permanent drills (mail-loss: same day). Coverage (drilled/named windows, L1: 5/5) is
the proxy while catches are scarce.
BAR: the incident class of any live failure becomes a drill within one arc of its
forensics (mail-loss: same day).

### M5. Live-exercise after ship
TRIGGER: every shipped slice with a runtime surface.
PROTOCOL: drive the REAL door verbs against the LIVE store before calling it done --
hermetic pins defend what we predicted; the live pass finds what we didn't.
RECEIPTS: 07-10 -- the aged-out overclaim (nonsense id rendered as evicted) and the
byref migration gap (old acks blanked until rebuild) were both invisible to green pins
and found within minutes of driving the real CLI.
METRIC: live-find rate (2 real bugs in one evening). Ship messages state what was
live-exercised.
BAR: no "done" claim on unexercised runtime surfaces.

### M6. Verbatim preservation of peer output
TRIGGER: any substantive report, review, or verdict from a peer agent (deepseek, GPT,
frontier passes) -- especially when the delivery channel is lossy.
PROTOCOL: persist the FULL text as a report ATOM (projected to docs/library/report/) with
provenance header before synthesizing; chat is disposable, the record is not. Pre-migration
records live at research/reviewed/ and stay cited as-is -- corrections supersede, they never
rewrite history. When the reply channel fails
(no-final-answer), harvest from the streamed log -- the work usually exists.
RECEIPTS: 6 verbatim records this arc; the L1 verify GATE GREEN existed ONLY in the
streamed log (bus reply was the 35-char no-answer marker, twice).
METRIC: every GATE decision cites a persisted verbatim record (this arc: 100%).
BAR: zero decisions resting on evidence that lives only in a bus stream or chat scroll.

### M7. Evidence-first forensics (diagnosis quarantined from facts)
TRIGGER: any live incident or anomaly.
PROTOCOL: a pure-evidence record first -- timeline, artifacts, probes, and what each
probe RULED OUT -- fence-safe for the dual pass; diagnosis and fixes live in a separate
fenced doc. Probes prefer decisive observables (stacks, sockets, cursors, raw streams)
over inference; deleting a hypothesis is progress.
RECEIPTS: runner-mail-loss forensics 07-10 -- four successive hypotheses (stuck review,
lost handoff lane, wedged call, watcher theft) each KILLED by a probe before the true
cause (pipe-kill mid-consume) survived; the record then powered both blind halves.
METRIC: forensics-before-fix ordering on every incident (git timestamps); probes-that-
ruled-out counted in the record.
BAR: no incident fix ships without its evidence record.

### M8. Honest bounds, named tolerances
TRIGGER: every design and every claim -- what remains unprotected, what is accepted.
PROTOCOL: residual windows get named and sized (the ~1.5s fence window); accepted
costs become PINNED TESTS (the W3 duplicate-reply tolerance is a passing drill, so the
tolerance is a decision, not a surprise); REJECTs and deferrals are recorded with
reasons; claims stay within their evidence (aged-out "if it ever existed").
RECEIPTS: W3 tolerance drill 07-11; the verify found our 5s bound was conservative --
honest in the right direction; "evicted if it ever existed" hedge 07-10.
METRIC: every slice's spec section contains a residual/tolerance line; tolerances have
pins (this arc: 100%).
BAR: a reviewer can enumerate what a slice does NOT protect from its doc alone.

### M9. Budget-aware peer protocol
TRIGGER: every ask to a runner-hosted peer.
PROTOCOL: gate-critical asks go on BOTH lanes (durable handoff + live bus-send); long
analytical asks carry a size cap + CONTINUES flag (reasoning eats the completion
budget); replies that come back as no-answer markers get harvested from the log, then
the ask is split or the budget raised.
RECEIPTS: two-lanes lesson 07-10 (15 minutes lost to the boot-lane verb); two no-answer
failures 07-10/11; the capped L2 ask returned a complete 1k verdict first try.
METRIC: no-answer rate per ask (uncapped long asks: 2/2 failed; capped: 1/1 clean).
BAR: zero waiting-on-a-reply-that-cannot-arrive incidents.

### M10. Guards for every new law
TRIGGER: any new convention, map, or contract.
PROTOCOL: a law without a forcing function decays -- wire the check into ship gates
(the immune-system pattern); the guard must FAIL on the defect class, not warn.
RECEIPTS: doc-currency guard blocked the untracked tier doc 07-10; comprehensibility
guard caught the unmapped timescale.py 07-11; the _no_live_bus fixture ended real
test-pollution the same night it was proven live.
METRIC: guard catches per arc (3 this arc) -- a guard that never fires for a year is
either victory or dead weight; the quarterly review decides which.
BAR: every practice in this doc that CAN be mechanically checked eventually is (T031).

### M11. Slice discipline, now measured
TRIGGER: all build work (pre-existing law -- AGENTS.md/ship contract -- promoted here
so it is MEASURED, per deepseek's half).
PROTOCOL: small, reversible, independently-shippable changes; each with its
pre-registered acceptance; never a big-bang rewrite; ship ritual per slice.
RECEIPTS: this arc: ~15 slices across T029 W2 + T030, zero reverts, every one gated.
METRIC: revert rate (0 this arc); slice size distribution; gated-vs-ungated ship ratio.
BAR: revert rate stays ~0; a growing slice size trend is a smell the retrospective
names.

## What we deliberately do NOT codify
- THE MARATHON CADENCE (deepseek's call, adopted verbatim in spirit): the overnight
  parallel rhythm was circumstance, not method -- "codifying it guarantees burnout."
  The fence generalizes; the pace does not. The baseline is the practices at ANY pace.
- Multi-agent ceremony for trivial or mechanical work -- the fence is for expensive
  wrongness, not for typo fixes (frugality is a standing directive, and M1's own metric
  detects ceremony-decay).
- One night's lucky specifics (exact window counts, exact thresholds, W1-W5's map --
  both halves independently) -- the PRACTICES are the baseline; their parameters stay
  slice-local.
- Tool choices (mutmut, Hypothesis, py-spy) -- named in the SOTA map as current best,
  swappable at the seam; the practice is mutation-testing-the-guards, not mutmut.
- Design heuristics that already live in their slice specs (hysteresis-over-single-
  sample stays in the L2 spec -- the method doc codifies HOW we decide, not every
  decision).

## The empirical loop (how the baseline stays a baseline)
- Metrics prefer OUTCOMES over activity (third-reviewer point, adopted): catches,
  adopted imports, reverts avoided, incidents-to-drills -- not passes run or drills
  counted. An activity metric is only a proxy while its outcome is scarce, and the
  quarterly review asks whether each proxy has earned its outcome yet.
- Each practice's metric is reviewable from durable records (git history, promoted
  tier, the report atoms in docs/library/, the funnel) -- no new bookkeeping demanded
  of anyone.
- Wrap-time: the session draft already lists shipped slices; the arc retrospective
  (sprint_pattern_close_the_loop) scores the arc against this doc -- which practices
  fired, which were skipped WITH REASON, what the metrics read.
- Quarterly (or per-pillar): metrics reviewed; a practice whose metric shows decay gets
  a forcing function (T031 lane) or gets retired HERE, in this doc, with its reason --
  the baseline itself obeys M8.
- Exceeding the bar mints a new receipt line; the doc is append-mostly and its receipts
  are the empirical memory of what excellence looked like.

## Enforcement lane (proposed as T031; hook order reconciled)
(1) RECONCILIATION GATE (deepseek's hook, adopted first): a gated slice's ship must
    cite its dated dual-half build-spec artifact -- without it "we're just two agents
    chatting"; with it every design decision has a converged, dated record that gates
    the build. Zero new infrastructure (ship-gate check on the commit message + doc).
(2) Pre-registration checker: acceptance-test commit <= impl commit per slice (M3,
    from git history).
(3) Wrap-time arc scorecard: which M# fired, which skipped WITH REASON, metric reads.
(4) Verbatim-record linter: GATE strings in ship messages cite a report-atom path
    (docs/library/report/...) or the atom id; legacy research/reviewed/ paths stay
    accepted for pre-migration history (M6).
(5) M1-LITE tier recorded in the slice's ledger entry (checkable from the ledger).
(6) M1-PV: reconciliation records open with the verification-pass header (checkable
    from docs/library/report/).
(7) M1-BRIEF: fence briefs carry the five mandatory sections (mechanically checkable).
