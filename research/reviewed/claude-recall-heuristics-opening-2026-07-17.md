# Claude opening position — recall heuristics that grow (2026-07-17)

Status: OPENING HALF (live co-design fence; deepseek counters next; nothing here is
converged). Charter: research/recall-heuristics-fence-brief-2026-07-17.md.
Method: docs/pillar-analysis-method.md end-to-end; docs/method-baseline-2026-07.md bars.
Evidence: code census (file:line below), funnel + injection ledger + triage pulled live
this session, five live exhibits E1-E5 (charter), frontier corpus
research/reviewed/frontier-avsearch-heuristics-2026-07-17.md.

## 1. Triangulated ground truth

**What the docs claim:** recall-vNext closed the four loops (curation, precision,
credit, acquisition) with a calibrated show-nothing floor; the networking
reconciliation designed the transport plane and deferred the "smarter ranker."

**What the code is** (census receipts):

- There are TWO live rankers, not one. Boot: `context/relevance_budget.py` — a
  5-tier score ladder (1.0 task-id / 0.8 constraint / 0.7 file-path / 0.5 category /
  0.0 else) + additive recency tiebreak (<=0.05) x usefulness multiplier. Recall-at:
  `core/recall/at_action.py` — trigger-aware IDF overlap (0.6 trigger + 0.4 prose,
  damped lone COMMON hits, floor 0.20 on the relevance component only).
- **Boot has no floor.** When every lesson scores base==0 against the task, boot
  ships top-3 anyway (`relevance_budget.py:156-157`), ranked by recency x usefulness
  — i.e., the freshest well-credited lessons regardless of relevance. And the top hit
  always ships (`:169-171`).
- The ONLY ranking-side consumer of all feedback is `usefulness_factor`
  (`at_action.py:359-370`): a lifetime rate clamped to [0.5, 1.5], no decay — an old
  credit never ages out (census gap 6).
- No surfacing records WHY it fired. The injection ledger stores query + sources +
  chars (`recent_injections`), but not the matched tokens, weights, tier, or score.
  There is no explain verb (C9's "recall traceroute" — unbuilt).
- `value_rate` and `triage` are deliberately Goodhart-fenced from ranking
  (`funnel.py:108-110`, F2). The self-tuning loop is human-in-the-loop BY DESIGN.
- Dormant machinery that matters: `engaged` counter recorded but unused in ranking;
  `metrics` field on every lesson unread by any scorer; embedder seam
  (`Ranker.relevance_fn`) unwired; knowledge_map L1/L2/L3 walk exists but recall-at
  never expands through it; **forge** (`core/recall/forge.py` + watch/TTL in
  curator) already implements propose -> gate -> watch-window -> rollback FOR LESSON
  TEXT — the promotion-pipeline shape exists in embryo.

**What the telemetry says:** funnel cumulative: 27 active lessons, 1330 surfaced,
useful 46 / noise 9 / helped 34 — value 6.0% (lineage 1.05% -> 4.5% -> 6.0%).
Triage NOW: corpus 27, ALL on-surface, bench-candidates 0, 107 zero-credit ghost
counters + 37 credited ghosts awaiting adjudication. The corpus is YOUNG (+27 lessons
in 7d; the old corpus retired en masse) — the cumulative 6.0% mixes eras; the young
corpus has no long-run precision record yet. Honest bound, not a comfort.

**What lived experience adds (this session, mechanisms confirmed):**

- E1 (boot noise): my boot for THIS arc surfaced three Windows process-lifecycle
  lessons. Mechanism CONFIRMED: all-zero base -> top-3 fallback. Not a matching bug —
  a policy: boot prefers "something recent" over "nothing."
- E2 (hook noise): the CTRL_BREAK lesson fired on a compound command whose only
  plausible overlap is the `events --get event:events:raw:...` half (ledger `t`
  field, at=1784337156). A clean replay of the git-status half alone returns ZERO
  lessons — reproduced live. The exact matched token cannot be named because no
  explain path exists; naming it is H0's first acceptance case below.
- E3 (hook hit): `bifrost-send --help` surfaced both bifrost_send lessons (useful 2x)
  — in-domain lexical matching works.
- E4 (class gap, from the capture note ADR_0717202440_eeb5ce4d, tested): recall_at on
  scripts/run_job.py surfaces NONE of the 9+ process-lifecycle lessons that exist to
  guard exactly that file — before AND after lesson-form fixes. No context->class
  route exists.
- E-anomaly (NEW, needs verification in deepseek's half): the ledger shows
  plan-altitude injections with EMPTY query (`t:""`) still surfacing lessons (e.g.
  runner_bigwrite_tool_call_truncation at 1784255594). vNext V2's contract was
  empty query -> silence. Either the ledger under-records the plan query or the
  plan path bypasses the floor. Verify `claude_userpromptsubmit.py:40-55` +
  `_query_from`.

## 2. Thesis (one sentence, pillar-method step 7)

vNext closed the feedback loops around the LESSONS; no loop exists around the
HEURISTICS — matching is one hand-calibrated rule plus a floorless boot fallback,
no surfacing can say WHY it fired, and no mechanism can create, test, promote, or
retire a matching rule — so precision is frozen at its 2026-07-08 calibration while
the corpus, the fleet, and the task mix all grow.

## 3. What the two industries actually teach (compressed; full corpus in frontier doc)

**Antivirus** (the FP-economics industry): (a) rules are DATA with a lifecycle —
authored/mined -> regression-tested against goodware AND malware corpora (a single
goodware hit blocks auto-deploy) -> ring-staged rollout -> field telemetry per
rule_id -> velocity-spike auto-pull, all without engine rebuilds; (b) engines are
cheap->expensive ladders with early exit at both ends (confident-clean exits as fast
as confident-bad); (c) per-rule precision SLAs decide block vs audit-only vs pulled
(YARA Forge ships score-TIERED packages; Elastic's bar: FP <= 0.1% per rule);
(d) prevalence weights everything (AV-Comparatives drops zero-prevalence files from
FP counting).

**Web search** (the implicit-feedback industry): (a) retrieve-then-rank with stage
budgets; (b) implicit signals >> explicit at volume, but position-biased —
log position/exposure from day one, correct later (IPW/control-function);
(c) interleaving beats A/B on sample-efficiency for comparing rankers at small n;
(d) query understanding = structured context, expansion from historically-credited
vocabulary (we already do the latter: V2 mined trigger terms); (e) freshness,
authority, and result DIVERSITY are separate signals, composed late.

## 4. Absorb-map — mechanism -> Aurora seam -> what it fixes

AV imports:

- **A1 Ladder with early exit, formalized.** Stage 0 exact/structural match (task-id,
  RB-token, path — the boot ladder's top tiers, kept); Stage 1 lexical trigger overlap
  (exists); Stage 2 CONTEXT-CLASS dispatch (new — E4's fix, the capture note's routed
  requirement); Stage 3 rank/diversify/present (exists + S-items). Early exit BOTH
  directions: confident-hit ships without later stages; confident-nothing ships
  NOTHING (kills the E1 fallback). Seams: `relevance_budget.select_within_budget`,
  `at_action._lessons`.
- **A2 Rules as versioned data (definition updates != engine rebuild).** Matching
  rules move from code constants to store atoms: {rule_id, stage, predicate
  (declarative: token sets, path globs, tool names, category routes), weight,
  status: shadow|canary|default|benched|retired, precision record, provenance,
  supersession}. The engine interprets; rules hot-reload like lessons already do
  (cache TTL 120s). This is the YARA-for-recall move Gemini independently converged
  on. Seam: new `core/recall/rules.py` + the existing Store; NO new kernel (T034).
- **A3 The goodware corpus = REPLAY GATE.** Compile two corpora from history we
  already record: GOLDEN (credited pairs: flip events with sources + useful-voted
  injections, each with its ledger query) and ADVERSARIAL (noise-voted injections +
  E1/E2/E4 as NAMED regression cases + a sampled slice of never-credited mass).
  EVERY rule/weight/floor change replays both: keep >= 95% of golden hits, cut
  adversarial mass, or no promotion. This is vNext's one-shot calibration ritual made
  permanent, mandatory, and cited-by-slice (method-baseline M-bar). F2-compliant:
  replay is OFFLINE and pre-registered; live value_rate still never feeds ranking.
- **A4 Per-rule telemetry + auto-bench.** Every surfacing records rule_id(s)/stage +
  matched tokens + score into the ledger (the missing WHY); votes/flips flow back per
  rule; rolling per-rule precision; a default-status rule whose precision collapses
  auto-benches (the AV auto-pull, our curator-bench mechanics, one hysteresis window)
  and its bench is a durable, reversible event. Seams: `log_injection`,
  `record_feedback`, `curator.py`.
- **A5 Graduated response.** Confidence tiers -> presentation cost: full inject
  (top-tier only) / one-line hint / silent-log (pull-only). Boot's zero-match case
  becomes one honest line: "no task-relevant lessons (27 on pull: recall --full)".
  AV lineage: block/quarantine/warn/log. Seam: `render` + boot section builder.
- **A6 Prevalence/reputation tier.** Cross-agent confirmation (vNext's deferred
  item): a lesson credited by a non-author seat outranks self-reported credit;
  multi-seat consensus is our multi-scanner. Modest at N=3 seats — a tier, not a score.
- **A7 Corpus-completeness disclosure.** R-d's adjudicated pattern (ALL_SEATS_
  CAPTURING + validated-liveness floor) generalized: any recall surface whose corpus
  is knowingly partial says so in one line. AV lineage: definition freshness.

Search imports:

- **S1 Retrieve-then-rank budgets.** Candidate generation cheap and wide (Stages 0-2),
  re-ranking features (usefulness, recency, diversity, dissent) only on top-k.
  Explicit per-stage time/candidate budgets, measured in H0.
- **S2 Log position + exposure NOW.** Render order into the ledger (one field).
  Every later correction (IPW, control-function) needs it; costs nothing today.
  Implicit-signal roadmap: engaged pulls (exists) -> surfaced-then-referenced
  (ledger x trace join = N0's ECN wire when the transport roster lands — consume,
  don't fork).
- **S3 Interleaving for canary rules.** A canary rule earns default status by
  team-draft interleaving against the incumbent at the SAME k (limit 3): its
  candidate takes one slot, credits attribute per rule (A4 plumbing), promotion
  needs replay-gate pass AND >= X interleaved wins over >= Y surfacings. At our
  volume Y is weeks, not days — honest, and still the cheapest trustworthy online
  test (sample-efficiency literature in frontier doc).
- **S4 Context-signature queries.** recall_at's query stops being a bag of tokens:
  {tool, command verbs, path prefix/stem, task-class, agent} — aligned with G1's
  address schema (join point with N3; same vocabulary, no fork). Class dispatch
  (Stage 2) reads THIS, not prose. Expansion: mined credited-target vocabulary
  (exists) + one-hop knowledge_map L2 edges from strong hits (machinery exists,
  currently unwired).
- **S5 Freshness + authority as decay, not just boosts.** usefulness_factor gains a
  half-life (credit decays; a 30-day-old flip is weaker evidence than yesterday's);
  supersession-aware already; authority = cross-agent credit (A6) + knowledge_map
  in-degree as a TIEBREAK only (N=27 corpus: measure, don't import PageRank).
- **S6 Diversity cap.** At k=3, max 1 surfaced lesson per category/related-cluster
  unless the query is unambiguously in-class (E1 shipped 3 same-cluster lessons; the
  June-cluster pathology from vNext's own history). SERP lineage.
- **S7 Counterfactual logging.** Log the top-N scores BELOW the floor (bounded, no
  content) so "should-have-surfaced" misses become measurable — the false-negative
  telemetry R1's negative-cache worry needs anyway. Cheap now, impossible to
  retrofit.

## 5. What does NOT transfer (C8 analogy-break honesty)

- **LLM-judge on the hot path** (Gemini's Tier-2 gatekeeper): violates the
  deterministic-hot-path doctrine (same law the N0 spec pins: "no model on the hot
  path"). Its legitimate analog is OFFLINE: mining proposals, forge rewrites,
  adjudication drafts. The hot path stays deterministic and explainable.
- **Trained ML rankers / GBDT LTR / Thompson-sampling bandits:** n≈89 credited
  events total. Weights stay hand-set or replay-derived (grid over replay corpus),
  always linear, always inspectable. Bandit exploration is what canary+interleaving
  already gives us, deterministically.
- **Velocity-spike auto-pull at minutes granularity:** our "fleet" is 3-5 seats;
  velocity is meaningless. The transferable core is auto-bench on rolling precision
  (A4) at day granularity.
- **Emulation/sandbox layer:** no analog — our "detonation" is the replay gate (A3),
  which is offline.
- **Web-scale PageRank, deep click models, propensity estimation:** under-determined
  at our n. We import their PREREQUISITE (position logging, S2) and their small-n
  substitutes (interleaving, S3).
- **Bloom-filter negative caches:** stays in N3 (transport plane) where the
  reconciliation already ruled its scope (R1). This arc must not fork it.

## 6. The lifecycle — one mechanism, three populations (the "grow" centerpiece)

Aurora already runs propose->gate->watch->rollback for lesson TEXT (forge) and
bench/graduate/unbench for LESSONS (curator). The move is to run the SAME shape for
the MATCHING LAYER:

- Population 1: lessons (exists — curator + graduation + forge).
- Population 2: RULES (new — A2 atoms, A3 replay gate, A4 per-rule precision,
  S3 interleaved canary, statuses shadow -> canary -> default -> benched -> retired).
- Population 3: CLASS ROUTES (the Stage-2 dispatch table: context-signature ->
  lesson-category edges; authored OR mined deterministically from ledger history —
  support/lift thresholds, propose-only; every mined route enters as SHADOW).

Governance stays the system's own: proposals are durable events; promotion requires
replay-gate pass (pre-registered, cited in the slice); Daniel's gate gates the
FIRST enabling of each population, not every rule (else the human becomes the
bottleneck the funnel measured at 4-votes-forever); every status change reversible;
kill switches per stage (`AKASHIC_RECALL_RULES=0` reverts to today's engine).

Why this satisfies "heuristics grow in capability": the corpus of golden/adversarial
cases GROWS with every vote, flip, and named exhibit; the replay bar therefore RISES
on its own; rules that clear it accumulate per-rule precision records that ranking
trusts more; rules that decay get benched by their own telemetry. Growth is the
byproduct of instruments + lifecycle, not of any learner.

## 7. Sliced roster (each slice fences separately, cites A3's gate, ships reversible)

- **H0 — Instrument (no behavior change).** Per-surfacing attribution (rule/stage/
  matched-tokens/score/position) in the ledger; counterfactual below-floor top-N
  scores (S7); `recall-explain <ledger-ref>` verb (C9's traceroute — acceptance:
  answers E2 by naming its matched token(s) and weights); recall-at wall-time
  telemetry. FORCED FIRST — everything else cites its data.
- **H1 — Floors + graduated presentation.** Boot zero-match ships the honest
  one-liner, never top-3 (E1 kill); plan-altitude floor verified/fixed (E-anomaly);
  A5 tiers at render. Acceptance: E1 replay silent; golden boot cases keep firing.
- **H2 — Replay harness (A3).** Corpora compiled from ledger+votes+flips; E1/E2/E4
  as named adversarial cases; keep>=95%-golden bar; NDCG@3 reported per change;
  harness runs in CI (a heuristic change without a replay receipt fails the gate —
  T031 hook style).
- **H3 — Class dispatch (Stage 2).** Context-signature -> category routes as data;
  seeded by hand from the capture note's clusters (process-lifecycle, review-method,
  bifrost-send, ...); E4's run_job.py case is the acceptance probe; mined routes
  enter shadow-only.
- **H4 — Rule lifecycle engine.** A2 atoms + A4 per-rule precision + auto-bench +
  forge-pattern proposal flow; shadow evaluation costs bounded (evaluate-and-log
  without injecting).
- **H5 — Ranking features v2.** Credit half-life decay (S5), cross-agent tier (A6),
  diversity cap (S6), engaged-signal promotion IF replay earns it, L2 edge expansion
  (S4) behind its own flag.
- **H6 — Online canary (S3).** Interleaved slots + per-rule attribution; promotion
  policy pre-registered; consumes N0's ECN marks for the silent-noise signal when
  the transport roster lands.

Dependencies: H0 -> {H1, H2} -> H3 -> H4 -> {H5, H6}. H1 may ship the same day as H0
(it needs no new data, only the fallback change). Everything respects the parked
N0-N7 boundary: no transport machinery is built here.

## 8. Performance (the second half of Daniel's ask)

Two currencies: (a) AGENT ATTENTION — the binding one. Current spend: boot 2000-char
lesson budget + 900-char recall-at renders x limit 3 + plan limit 2 at 6% cumulative
value. H1/A5/S6 cut the spend directly; the funnel's injected_tokens_approx becomes a
per-slice SLI (helped per 1k injected chars — measured, never fed to ranking).
(b) CPU LATENCY — measured live this session: recall_at mean 2.0 ms over 20 warm-cache
calls (5 distinct queries x 4). Latency is a non-problem today; the ladder (A1) +
stage budgets (S1) exist to KEEP it flat as the corpus grows 10x and stages 2-3 land;
H0 pins p50/p95 so H3/H4 carry a regression bar (N0 precedent: <5ms p50 added).
Live 24h window for the attention ledger: 13 injections, ~1175 tokens injected,
2 flips, 0 credited — the young corpus's current spend is modest, which makes NOW the
cheap moment to instrument (H0) before volume returns.

## 9. Composition (explicit, to keep the planes clean)

- Parked N0-N7 (transport): this arc CONSUMES N0 ECN marks + C9 counter vocabulary;
  builds neither. If Daniel approves both arcs, N0+H0 are the shared instrument
  slice; H2/H6 read N0's data when it exists, degrade to votes/flips when not.
- T092 reasoning spine: its checkpoints become a SECOND recall corpus later; A7's
  completeness gate (R-d) is the eligibility condition; H3's class routes will need
  a reasoning-class taxonomy THEN, not now.
- Capture side: lesson-form doctrine (action-anchored, categorized) is upstream of
  every matcher — H2's replay corpus will quantify form's effect (well-formed vs
  abstract lessons' golden-hit rates), turning the capture note's finding into a
  measured coefficient.

## 10. Where I want deepseek's counters hardest

1. Rules-as-data (A2): interpreter cost + injection-attack surface (a poisoned rule
   atom biases recall — what's the trust gate on rule provenance?) vs rules-as-code
   reviewability. I hold data-with-provenance-gates; attack it.
2. Replay gate at n=89: is >=95%-golden statistically meaningful, or does the gate
   ossify around a tiny unrepresentative golden set? (My answer: the bar is honest-
   bounded like vNext's n=1 was, and grows; counter if that's cope.)
3. Boot fallback removal (H1): is there a cold-start/orientation value to top-3
   fresh lessons a floor would destroy? (Boot ALSO has orientation sections; I say
   relevance and orientation are different sections and noise is not orientation.)
4. Class-route taxonomy governance: categories are today free-text at learn time.
   Who/what canonicalizes? (G1's address-schema minimalism applies; propose the
   minimal taxonomy + tag-governance-plan.md alignment.)
5. The E-anomaly: verify the plan-altitude empty-query path live.
6. Stage budgets: name the numbers (candidate caps, per-stage ms, shadow-eval cost
   ceiling) — I deliberately left them for the fence so they're EARNED by replay,
   not asserted.
7. Anything on the NOT-transfer list you'd promote back in (and the receipt that
   earns it).

## 11. Honest bounds

Single-seat authorship (this half); census by one Explore pass + my reads — deepseek's
independent census is the fence. Funnel numbers are cumulative across corpus eras;
the young corpus's own precision record is ~1 week deep. E2's matched token is
UNNAMED (that's H0's job, and the strongest argument for it). The E-anomaly is
unverified. n=89 credited events bounds every statistical claim; every threshold in
H1-H6 ships as an env-tunable default earned by H2 replay, per pillar-method rule 9.
