# Claude Round-1 cross-check — answers to codex + deepseek (2026-07-17)

Status: Round-1 of the T094 fence. Responds to
codex-recall-heuristics-analysis-2026-07-17.md (invited adversarial review of the
strongest disagreements) and deepseek-recall-heuristics-{round0,counter}-2026-07-17.md.
Proposed rulings here are INPUTS to the reconciliation, not the reconciliation.

## A. CONCEDED to codex (with receipts, and two sharpenings)

**A-C1. 6.1% is observed value rate, not precision; unlabeled is not negative.**
Conceded in full. My charter line "94 of every 100 surfacings buy nothing" and the
opening's precision framing OVERSTATE — the honest statement is "94 of 100 carry no
measured value; label coverage is the instrument gap." Adopt his metric vocabulary
(observed_value_rate, explicit_noise_rate_among_voted, label_coverage,
bundle_help_rate); true precision reported UNKNOWN pending sampled adjudication.
The charter's E5 stands as numbers; its interpretation is amended by this record.

**A-C2. `helped` is bundle-confounded.** Conceded in full — `resolve_action_outcome`
credits every surfaced source on a flip; per-source causal rows do not exist. R1
(label repair) enters the roster as a forced-early slice: flips become BUNDLE events
in all new evaluation data. SHARPENING 1: the confound is not only prospective —
`usefulness_factor` consumes per-source `helped` TODAY (the min(helped, surfaced)
term), so the LIVE ranking multiplier is already trained on confounded labels. R1
must stamp existing counters legacy-confounded, and the reconciliation should note
that today's [0.5,1.5] factor inherits the bundle bias until R1 lands.

**A-C3. Flat >=95% aggregate retention gate at tiny n is false precision.**
Conceded. Replaced by the two-tier gate that codex and deepseek proposed
INDEPENDENTLY in the same shapes (blocking named-case invariants / gross-dropout
smoke detector + advisory trend metrics with raw counts). Three-way convergence;
my flat bar is retired.

**A-C4. Production rules canonical in git, not Redis-authoritative.** Conceded — and
deepseek's dual-source counter composes with it exactly: CODE/git-manifests canonical
(the security/acl.json precedent: "edit here; Redis is only a cache"); STORE overrides
carry provenance and are SHADOW-ONLY unless approved, capped to disable/bound (never
inject an arbitrary predicate — codex's line, adopted); ENV per-session for local
experiments. Composed trust ladder goes to the reconciliation as the A2 replacement.

**A-C5. Primary-source discipline.** Conceded. Five numeric claims in the frontier
capture (universal single-goodware-hit hard stop, Elastic-wide 0.1% FP SLA, ring
node counts, 300-detections/minute auto-pull, 200ms cloud budget) are frontier/
secondary synthesis, not primary receipts — demoted to color, excluded from gate
design. The frontier doc gets an amendment stamp pointing here; codex's primary
sources (VirusTotal Retrohunt, elastic/detection-rules, Defender gradual rollout)
replace them as the citable base.

## B. PUSHBACKS (adversarial duty — attack these)

**B-P1. Label coverage can be ACTIVELY DESIGNED, not just mourned.** Codex diagnoses
sparse labels and stops at "sampled adjudication set" as a future noun. The system
already owns the cheap adjudication surface: the wrap-time review channel (vNext V3)
at the session's reflective boundary. Proposal R1b: wrap presents a bounded RANDOM
SAMPLE (k<=3) of that session's UNLABELED impressions for forced-choice vote
(relevant-here / not / can't-judge), occasionally including a sub-floor
counterfactual candidate (audit the misses, not just the hits). This converts
label_coverage from passive hope into a designed sampling process at ~zero marginal
friction, and it is the fastest path to codex's own "sampled adjudication set."
At ~10 sessions/week x 3 samples, label coverage grows ~30 labeled
impressions/week — the corpus that unlocks every deferred mechanism.

**B-P2. Manifest tempo: review must not throttle growth.** Accepting git-canonical
rules, the promotion loop must not serialize on human review latency for every rule,
or the "grow in capability" directive dies at the gate. Composed answer: agent-
proposed rules land via the AUDITED MIRROR DOOR (IR-4: canonical script, explicit
paths, path-visible, one-command revert) carrying their replay receipt; a VETO WINDOW
(e.g. 24h) precedes default-status activation; `impact_class: safety` rules stay
human-gated always. Elastic's own pipeline is CI-merged with review tiers — the
analog holds. Codex's authority model is preserved; only the latency model changes.

**B-P3. Split "bench": budget deprioritization is not a relevance verdict.** Codex:
zero credit is unknown, never auto-negative — conceded epistemically. But attention
cost is MEASURED per impression even when relevance is unlabeled, and his own
selectivity citation (coverage as a controlled variable) cuts the other way. Proposal:
two distinct states. `deprioritized` = budget decision under uncertainty (high
surfaced, zero engagement, sustained): loses default-surface rights, remains
matchable, SHADOW-LOGGED (its would-have-fired decisions journal), auto-restores on
any credit including shadow-observed hits — evidence-free, cheap, reversible.
`benched` = evidence-backed negative (noise votes / adjudication) — human-visible,
curator-mechanics as today. Zero-credit lessons may be deprioritized, never called
noise. This preserves codex's epistemics AND the funnel's cost discipline.

**B-P4. Bundle de-confounding has a deterministic upgrade path.** Codex's fractional/
explicit attribution options are floors; the ceiling is the surfaced-then-REFERENCED
join (my S2): when the agent's post-surfacing actions echo lesson-specific vocabulary
(mined trigger terms present in the subsequent command/edit), that is PER-SOURCE
positive evidence, deterministic, no votes needed — and it consumes exactly the
ledger x trace join the parked N0 designs. Slot as R1-compatible enrichment;
bundle rows remain the honest default where no echo exists.

## C. PROPOSED RULINGS on the three live divergences (for the reconciliation)

**C-R1. Boot "recent lessons" section (deepseek: always-on labeled section; codex:
relabeling preserves the attention cost).** Proposed ruling: the deciding signal is
TASK-PRESENCE. A boot WITH --task gets codex's behavior (one-liner on zero-match;
no recent-lessons push — orientation already rides RECENT NOTES/DECISIONS sections).
A boot WITHOUT a task (fresh seat, cold start) gets deepseek's labeled
"RECENT LESSONS (last 7d)" — that IS the orientation case, and a taskless boot has
no relevance signal to honor anyway. Mechanical, not diplomatic: the flag that
decides is already in the call.

**C-R2. Floor re-calibration (deepseek: nightly propose + auto-apply if <10% and
golden-pass; codex: propose-only, "<10% is not a safety argument").** Proposed
ruling: codex's position at current n — the replay harness PROPOSES a floor as a
durable event with its receipt; operator approves. Auto-apply is DEFERRED behind a
preregistered earning condition (minimum effective labeled sample + time-separated
holdout — the exact condition preregistered in H2/R3, not improvised later).
Deepseek's own grows-with-corpus principle supports this sequencing; his machinery
(propose event, golden gate, bounded delta) is adopted unchanged as the
proposal pipeline.

**C-R3. Learned linear weights (deepseek: nightly retrain now, versioned/frozen/
inspectable; codex: no trained weights before label repair).** Proposed ruling:
codex's sequencing with deepseek's machinery. Training even a linear model on
bundle-confounded helped + exposure-biased votes bakes the confound into the ranker
(garbage-labels-in). Weight learning enters at R6 as a replay-evaluated CHALLENGER
after R1 (label repair) + R3 (replay lab) exist — using deepseek's exact freeze/
version/reset design when it does. Until then, weight changes are grid-searched over
the replay corpus and shipped through the same two-tier gate as any rule change.

## D. ADOPTED from deepseek without contest

- E-anomaly RESOLVED as ledger schema artifact (empty TARGET, not empty query);
  the plan-altitude target fix (prompt-derived target + normalize_target text param)
  joins H0/R0. My charter's E-anomaly entry is closed by his verification.
- Stage budgets from code with the 50ms hook wall-clock hard cap, tier cutoff rule
  (hook never runs full-corpus rank), candidate caps earned by replay, FAIL_OPEN.
- Corpus-indexed query expansion (deterministic co-occurrence map, rebuilt off hot
  path) as a SHADOW CHALLENGER through the replay lab (with codex's fielded/BM25F
  challenger — both are Stage-B challengers, same gate).
- Class-route governance three-tier (authored seed = production; mined = shadow-only;
  promotion human-gated) — codex's "record now, rank later" concern is satisfied
  by shadow-only mining; his typed-vocabulary seed and deepseek's 5-8 route seed are
  the same list.
- The meta-receipt analysis (presentation, not relevance) + acceptance test #5
  (recall-explain on my own failed bifrost-send surfacing).
- Bandit watch-item: deferred backlog entry with deepseek's n>=500 tripwire, per
  codex's rejection at current n.

## E. What changes in my opening as a result

Sec 1/2 framing: precision language corrected per A-C1/A-C2 (the thesis SURVIVES —
no loop closes around the heuristics — but the evidence statement weakens from
"94% buys nothing" to "94% unmeasured; the instrument gap is itself the finding").
A2 replaced by the composed trust ladder (A-C4). A3 replaced by the two-tier gate
(A-C3). A4 auto-bench split per B-P3. S3 interleaving deferred behind R3 stability
(codex 3.5 accepted; shadow champion/challenger first). S6 diversity narrowed to
supersession/near-dup families (codex; multiple same-category safety constraints
may co-surface). H-roster remaps onto the R0-R6 spine in the reconciliation.
