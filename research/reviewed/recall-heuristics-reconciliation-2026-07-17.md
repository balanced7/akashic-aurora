# Recall-heuristics reconciliation — heuristics that grow (2026-07-17)

Status: **DRAFT-RECONCILED** — folded from all filed rounds; pending (1) codex_root +
deepseek acks/objections to the three C-rulings (window open), (2) deepseek-review
gate, (3) DANIEL APPROVAL. Nothing here builds until (3). T094 (proposed) is the
ledger anchor; first build wave on approval = R0+R1 only.

Charter: research/recall-heuristics-fence-brief-2026-07-17.md (Daniel directive
verbatim). Halves and rounds, in filing order:
- claude opening: claude-recall-heuristics-opening-2026-07-17.md
- deepseek round-0 + counter: deepseek-recall-heuristics-{round0,counter}-2026-07-17.md
- codex independent position: codex-recall-heuristics-analysis-2026-07-17.md
- claude round-1 cross-check: claude-crosscheck-round1-2026-07-17.md
- frontier evidence: frontier-avsearch-heuristics-2026-07-17.md (amended: five numeric
  claims demoted to unverified synthesis per cross-check A-C5; codex's primary sources
  govern)

EPISTEMICS, stated plainly: this was a LIVE ITERATIVE fence (per the standing
collaboration doctrine), not blind halves. Codex read all prior rounds before filing;
deepseek's counter read claude's opening. Convergence below is deliberative, not
verification-grade independence — its strength is receipts and surviving adversarial
rounds, not blindness. Where the SAME structure was derived before reading (the
two-tier replay gate: codex sec 4.3 and deepseek counter 2.2 name the identical
blocking-smoke-detector + advisory-trend split), it is marked [parallel-derived].

## 1. CONVERGED (all three seats)

- **C1 — The diagnosis.** Two production relevance paths sharing zero code (boot
  ladder vs recall-at IDF), a floorless boot fallback (E1, reproduced independently
  by codex's T999 probe), no per-decision attribution (E2 unanswerable), no
  context→class routing (E4, reproduced via run_job.py probe), and no lifecycle for
  the heuristics themselves. The thesis stands: loops close around LESSONS, none
  around HEURISTICS.
- **C2 — Label honesty [the fence's sharpest correction, codex].** 6.1% is
  OBSERVED VALUE RATE, not precision; unvoted impressions are UNLABELED, not
  negative; `helped` is BUNDLE-confounded (every surfaced source credited per flip)
  — and the live usefulness_factor already consumes those confounded labels today.
  True precision: UNKNOWN until adjudicated samples exist. Metric vocabulary
  adopted: observed_value_rate, explicit_noise_rate_among_voted, label_coverage,
  bundle_help_rate.
- **C3 — Instrument before intelligence.** Decision journaling (per-rule/tier
  attribution, matched tokens, position, render tier, candidate set, below-floor
  counterfactuals as IDs+vectors, version stamps) is the forced-first slice; the
  explain verb (`recall-explain`) is its acceptance surface. All three seats put
  this first independently.
- **C4 — Two-tier replay gate [parallel-derived].** BLOCKING: named-case invariants
  only (a preregistered golden case drops out of top-K entirely; a preregistered
  adversarial case reappears). ADVISORY: trend metrics (Recall@3, MRR@3/NDCG@3,
  negative-exposure, context cost) with raw counts and uncertainty, warnings until
  the effective sample earns promotion to blocking. Splits by time/session/task
  cluster to stop mined-token leakage.
- **C5 — Deterministic hot path, forever.** No LLM, no trained model, no bandit on
  the hook path at current n. Linear/inspectable everything; challengers evaluate in
  SHADOW through the replay lab. (Bandit tripwire deferred at n>=500 credited,
  deepseek's number, codex's deferral.)
- **C6 — Selective retrieval / abstention.** Show-nothing is a first-class outcome
  on every surface; coverage is a controlled variable. Boot's floorless fallback is
  removed (see R-1 for the orientation split).
- **C7 — Graduated presentation.** Confidence tier → render cost (full inject /
  compact hint / silent-shadow / abstain). The live meta-receipt (the
  bifrost_send_text_ordering lesson surfaced and was still not absorbed) is the
  acceptance anchor: relevance was right, presentation failed — deepseek's analysis,
  adopted. Duplicate suppression on supersession/near-dup FAMILIES only (codex) —
  never a blanket one-per-category cap.
- **C8 — Rule authority: composed trust ladder.** Git-tracked reviewed manifests are
  CANONICAL (acl.json precedent); Store carries telemetry, proposals, status, and
  bounded overrides (disable / weight-cap ONLY — never a new predicate), overrides
  SHADOW-unless-approved (deepseek) and capability-gated; env vars for volatile
  per-session experiments; emergency disable always available. An unapproved Store
  write can never inject.
- **C9 — Class routing with governed taxonomy.** Authored seed routes (5-8, from the
  capture note's clusters) are the only production taxonomy at launch; mined routes
  (deterministic nightly clustering over flip targets, co-tokens, L2 edges) enter
  SHADOW-ONLY; promotion is human-gated. Self-healing without human bottleneck at
  the shadow tier, human authority at the production tier.
- **C10 — E-anomaly resolved (deepseek verification).** Plan-altitude `t:""` is a
  ledger schema artifact (empty TARGET — no path/command exists at plan altitude),
  not a floor bypass; recall ran legitimately against prompt text. Fix rides R0
  (prompt-derived target + normalize_target text param).
- **C11 — What does not transfer.** Hot-path LLM judges; trained LTR/GBDT/bandits at
  current n; velocity-spike auto-pull at fleet-of-5 (daily-granularity auto-flag
  instead); emulation/sandbox (replay lab is the analog); PageRank/deep click models/
  propensity estimation (import their prerequisite — position+exposure logging — and
  their small-n substitutes); web-scale negative caches (stay in N3, transport);
  cross-deployment cloud reputation (cross-agent credit is the in-instance analog);
  intent classification (intent is explicit in tool calls).

## 2. RULINGS (divergences argued to closure this round)

- **R-1 Boot orientation vs relevance (deepseek: always-on RECENT section; codex:
  relabeling keeps the attention cost). RULED: task-presence decides.** Boot WITH
  --task: zero-match renders ONE honest line ("no task-relevant lessons; N on pull")
  — no recent-lessons push (orientation already rides RECENT NOTES/DECISIONS).
  Boot WITHOUT task: a labeled "RECENT LESSONS (last 7d)" section IS the correct
  content — a taskless boot has no relevance signal to honor. Mechanical rule,
  already in the call signature.
- **R-2 Floor recalibration (deepseek: nightly propose + auto-apply <10%+golden;
  codex: propose-only, "<10% is not a safety argument"). RULED: propose-only now.**
  The replay lab proposes floor updates as durable events with receipts; operator
  approves. Auto-apply DEFERRED behind a preregistered earning condition (minimum
  effective labeled sample + time-separated holdout) written into R3's spec — not
  improvised later. Deepseek's pipeline machinery adopted verbatim as the proposal
  path.
- **R-3 Learned weights (deepseek: nightly linear retrain now, frozen/versioned;
  codex: nothing trained before label repair). RULED: codex's sequencing, deepseek's
  machinery.** Training on bundle-confounded + exposure-biased labels bakes the
  confound into the ranker. Weight learning enters at R6 as a shadow challenger
  after R1+R3 exist, using deepseek's freeze/version/reset design unchanged. Until
  then: grid-search over the replay corpus through the C4 gate.
- **R-4 Bench semantics (codex: zero credit never auto-negative; funnel discipline:
  attention cost is real). RULED: split the state.** `deprioritized` = budget
  decision under uncertainty (sustained high-surfaced/zero-engagement): loses
  default-surface rights, stays matchable, shadow-logged, auto-restores on ANY
  credit including shadow hits — evidence-free and reversible. `benched` =
  evidence-backed (noise votes / adjudication), curator mechanics as today. Neither
  state is ever called noise without explicit evidence. (Claude proposal B-P3;
  pending codex ack.)
- **R-5 Rule-promotion tempo (codex: reviewed manifests; risk: human review latency
  throttles growth). RULED: audited-door autonomy with veto window.** Agent-proposed
  rules land via the IR-4 audited mirror family carrying their replay receipt;
  activation to default waits a 24h VETO WINDOW; `impact_class: safety` rules are
  human-gated always. Authority model preserved, latency model fixed. (Pending
  codex ack.)
- **R-6 Interleaving (claude S3: canary slots early; codex: premature before stable
  exposure/labels). RULED: deferred to R6.** Shadow champion/challenger (no context
  change) is the online comparison until R1+R3 stabilize labels and exposure logging;
  team-draft interleaving enters only then, with position logged from R0 day one.
- **R-7 Active adjudication (claude R1b, new this round). ADOPTED into R1 pending
  acks:** wrap-time sampled adjudication — k<=3 random unlabeled impressions from
  the session, forced-choice (relevant-here / not / can't-judge), occasionally one
  sub-floor counterfactual (audit misses, not just hits). ~30 designed labels/week
  at current cadence; the fastest path to codex's adjudication set and to every
  gate's statistical power. Friction budget is a Daniel gate item (G3).
- **R-8 Bundle de-confound ceiling.** Fractional/bundle rows are the honest floor
  (codex); the surfaced-then-REFERENCED echo join (deterministic per-source evidence
  from post-surfacing vocabulary echo) is the ceiling, consuming the parked N0
  ledger x trace join when transport lands. Named in R1 as the enrichment path;
  never a substitute for bundle honesty where no echo exists.

## 3. THE LIFECYCLE (the "grow in capability" answer, final form)

One mechanism, three populations, one authority model:

- Populations: LESSONS (curator/graduate/forge — exists), RULES (new; manifests per
  C8), CLASS ROUTES (new; governance per C9).
- States: proposed → shadow → canary → default → deprioritized | benched → retired.
  Every transition is a durable, reversible event with supersession links. Shadow
  evaluates-and-journals without injecting; canary is one opted-in surface at a
  time; kill switch restores byte-identical incumbent decisions on the replay set
  (codex R5 acceptance, adopted).
- Promotion currency: replay receipts through the C4 two-tier gate + veto window
  (R-5). Demotion: explicit evidence (benched) or budget (deprioritized, R-4) or
  decay of a mined route that stops earning its shadow record.
- Growth mechanism, stated once: the labeled corpus grows by design (R-7 active
  adjudication + R-8 echo join + votes + named exhibits), the gates' statistical
  power grows with it (advisory tiers promote to blocking at preregistered n), and
  the rule population evolves under those gates. Adaptation emerges from
  instruments + lifecycle, not from any learner. F2 stands: no live metric feeds
  ranking; all promotion is offline-replay-gated.

## 4. SLICE ROSTER (final; R-spine = codex's ordering; each slice fences separately,
cites this record + the C4 gate; design-only until Daniel approves)

- **R0 — Decision instrumentation (no behavior change).** The journal: decision_id,
  context signature (redacted; secret-sentinel pin), candidate set + per-feature
  contributions + matched rule/tier/tokens, selected/rejected/abstained reason,
  position, render_tier, chars, latency, engine/rules/corpus versions; below-floor
  top-N as IDs+vectors; `recall-explain <decision-id|ledger-ref>`; plan-altitude
  target fix (C10). Latency pins: warm p95 <5ms; hook wall-clock cap 50ms,
  FAIL_OPEN, tier-cutoff rule (hook never runs full-corpus rank). ACCEPTANCE:
  explains E2 by naming its matched tokens/weights; meta-receipt test (explain shows
  bifrost_send_text_ordering in-top-3 with score>floor on the failed-send call);
  100% of injected test decisions fully explained; no secret sentinel in receipts.
- **R1 — Label repair + designed labels.** Flips become BUNDLE events in all new
  evaluation data; legacy counters stamped legacy-confounded (incl. the live
  usefulness_factor note); label_coverage + explicit_noise_among_voted reported;
  R1b wrap sampled adjudication (R-7); echo-join named as enrichment (R-8).
  ACCEPTANCE: a three-source flip produces one bundle-positive row; wrap presents
  <=3 samples with one-keystroke votes; label_coverage visibly grows week-over-week.
- **R2 — Policy unification + honest boot.** Typed RecallContext (altitude, surface,
  tool, verbs, paths, task_ids, error_facts, bounded free_text, agent) shared by
  both surfaces; one feature implementation, surface policy only at presentation;
  boot fallback removed per R-1; graduated presentation tiers (C7); family-only
  dedup. ACCEPTANCE: T999 probe abstains with the honest line; taskless boot shows
  labeled RECENT section; E3 keeps firing; no named golden case lost.
- **R3 — Replay laboratory.** Three-state labels (positive/negative/unknown);
  cluster splits; E1/E2/E3/E4 pinned as named cases; C4 two-tier gates wired into
  CI (a heuristic change without a replay receipt fails — T031-hook style); floor
  proposal pipeline (R-2); advisory metrics with raw counts. This slice is the
  PERMANENT promotion gate every later change cites.
- **R4 — Structural routes + Stage-B challengers.** Authored seed routes production
  (C9); mined routes shadow-only; fielded/BM25F and corpus-expansion scorers as
  shadow challengers; candidate caps earned by replay. ACCEPTANCE: run_job.py
  surfaces >=1 process-lifecycle lesson via a NAMED route; unrelated classes stay
  silent; each challenger has a replay verdict on record.
- **R5 — Rule manifests + lifecycle engine.** Schema (rule_id, version, provenance,
  status, context_predicate, targets, positive/negative terms, path_globs,
  tool_verbs, impact_class, presentation_ceiling, expiry, supersedes, replay/rollout
  receipts); git-canonical + bounded Store overrides (C8); promotion tempo per R-5;
  states per sec 3; per-rule telemetry feeding curator rule reports. ACCEPTANCE:
  unapproved Store predicate cannot inject (pin); shadow rule journals hypothetical
  decisions; kill switch returns byte-identical incumbent decisions.
- **R6 — Evidence-earned refinements.** Learned linear weights (R-3), credit decay
  half-life, cross-agent provenance tier, one-hop L2 expansion, interleaving (R-6),
  per-agent usefulness — each a separate shadow challenger with its own replay
  verdict; bandit tripwire n>=500 stays deferred-listed.

Dependencies: R0 → R1 → R2 → R3 → R4 → R5 → R6 (R1/R2 may overlap after R0; nothing
skips R3 once it exists). Composition: consumes N0's ECN join and C9 counter
vocabulary from the PARKED networking roster when Daniel approves that lane;
builds no transport; T092 reasoning-corpus eligibility stays behind the R-d
completeness gate (adjudicated 2026-07-17).

## 5. PROCESS RECEIPTS (what the fence itself proved)

- Codex discarded his own first latency benchmark on discovering harness error, then
  corrected mine (2.0ms → 1.4ms mean; same conclusion) — the evidence discipline
  held under self-audit.
- The fence's sharpest finding (C2 label honesty) OVERTURNED the panel's own charter
  framing — the record self-corrected before Daniel's gate, which is what fences are
  for.
- The E-anomaly went from unverified charter item to root-caused ledger artifact in
  one round (deepseek), with the fix folded into R0 rather than a workaround note.
- Live meta-receipt (surfaced ≠ absorbed) became C7's acceptance anchor within the
  same session it occurred.
- The twin-seat consumer race and false wakes that punctuated this fence are
  DELIBERATELY out of scope here: they are the comms-architecture thread
  (deepseek-comms-mailbox-2026-07-17.md + claude's assessment to Daniel; candidate
  T095), which this record cites but does not rule.

## 6. OPEN FOR DANIEL (the approval gate)

- **G1** Approve this reconciliation as T094's governing record; activate T094 with
  R0+R1 as the first fenced build wave (both design-complete here; each still files
  its pre-registered pins before code).
- **G2** Confirm the rule-authority model (C8 + R-5): agents may promote non-safety
  rules through the audited mirror door with replay receipts and a 24h veto window;
  safety-class stays human-gated. This grants bounded rule autonomy — explicitly
  your call.
- **G3** Confirm R1b wrap adjudication (<=3 forced-choice votes at wrap — a small
  standing friction cost buying the labeled corpus everything else needs).
- **G4** Confirm the R-4 deprioritized/benched split semantics.
- **G5** Note the frontier-doc amendment (five numeric claims demoted to unverified
  synthesis) — no gate rests on them.
- **G6** Dissent rights: any seat may appeal any sec-2 ruling at this gate.
  Ack ledger: deepseek ACKED R-1/R-2/R-3 with no dissent (bus, 2026-07-17 ~23:20;
  his note on R-2: "my auto-apply was premature; codex's '<10% is not a safety
  argument' is correct"). Outstanding: codex acks on R-4/R-5 (window open; appeal
  rights preserved here regardless).
