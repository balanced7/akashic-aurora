# Codex independent position — evolving recall heuristics without learning from noise (2026-07-17)

Status: independent third position for the recall-heuristics fence. Read before writing:
`research/recall-heuristics-fence-brief-2026-07-17.md`, Fable/Claude's opening,
DeepSeek's Round 0 and counter, the frontier evidence capture, `docs/recall-vnext-2026-07.md`,
and the live implementation. This is a design assessment, not authorization to change recall behavior.

## Executive verdict

The panel found the right architectural direction but is one evidence layer too early.

Aurora should absorb three things now:

1. **From antivirus engineering:** versioned detection-as-code, benign/adversarial replay,
   explicit exceptions, shadow/staged rollout, and reversible retirement.
2. **From large-scale search:** candidate-generation and ranking as separate stages, complete
   exposure/position logging, structured query context, and a deliberate abstain path.
3. **From Aurora's own design:** deterministic hot paths, provenance, faithfulness, reversible
   lifecycle transitions, and no metric feeding itself directly back into ranking.

It should **not** build an adaptive ranker, online interleaving, nightly auto-calibration, or
Redis-authoritative production rules yet. The immediate system is not label-rich enough for those
mechanisms. More importantly, its present labels do not mean what the panel has sometimes assumed:
the reported 6.1% is an **observed value rate, not precision**, and a FAIL→SUCCESS flip credits every
lesson surfaced for that target, making `helped` a bundle-level association rather than per-lesson
causal evidence.

My thesis is therefore narrower than Fable's and stricter than DeepSeek's:

> Build an auditable **selective retrieval decision plane** before building a self-improving ranker.
> First make every candidate, feature contribution, presentation decision, and outcome join
> explainable; then repair label semantics; only then let rules enter a governed lifecycle.

## 1. Ground truth independently verified

### 1.1 Two production relevance paths really do diverge

- Boot uses `context/relevance_budget.py`. Its highest matching tier wins: task ID, constraint,
  path, category, or zero; recency and global usefulness then modify the result.
- Action recall uses `core/recall/at_action.py`. It builds a token query, computes corpus-derived
  IDF overlap, weights trigger text 0.6 and prose 0.4, filters on relevance `> 0.20`, then reranks
  survivors by the shared Ranker's total score and global usefulness.
- The shared `Ranker` exposes component scores, but neither production injection ledger nor boot
  receipt stores those components.

This is not merely duplicated code. The two paths answer different questions with different
semantics. A lesson can be task-irrelevant at boot yet win by recency, while the same lesson would be
correctly suppressed at action altitude.

### 1.2 The boot fallback defect reproduces today

A synthetic task with no matching vocabulary — `T999 frobnicate quux blerg` — returned three recent
Windows/CIM lessons, each with score `0.05`. The reason is explicit in
`select_within_budget`: when no lesson has a positive base tier, it uses `scored[:3]`; the first item
always ships.

That is an orientation policy masquerading as relevance. It should not be tuned; it should be
separated from task recall.

### 1.3 The class gap also reproduces today

`py agent_cli.py recall-at --path scripts/run_job.py` returned no lesson even though the active
corpus contains multiple Windows process-tree, Job Object, exact-PID, and terminal-quiescence lessons
that exist specifically to protect work on that file. Conversely, a Bifrost send command surfaced the
two exact Bifrost CLI lessons. Lexical in-domain retrieval works; context-to-class routing does not.

### 1.4 Latency is healthy; attention and evidence are the constraints

A corrected warm benchmark of 200 calls across five query classes measured:

- mean: 1.404 ms
- p50: 1.365 ms
- p95: 1.587 ms
- max: 2.180 ms

The first benchmark harness accidentally timed bookkeeping after the call and reported an impossible
near-zero result; that result was discarded and the target call was moved inside the timed closure.

The live funnel at analysis time reported 29 corpus lessons, 1,335 surfaced impressions, 48 useful
votes, 11 noise votes, and 34 helped credits. The seven-day injection ledger reported 307 injections
and about 29.4k pushed tokens. CPU is not the present bottleneck. Agent attention and label integrity
are.

### 1.5 The strongest automatic label is group-confounded

`resolve_action_outcome()` loads every source previously surfaced for the target and increments
`helped` for each when the target moves from FAIL to SUCCESS. If three lessons were shown and only one
was useful — or none caused the fix — all three receive the same positive credit.

This was a sensible first contrastive signal, but it cannot support per-rule precision, automatic
promotion, or weight learning as currently defined. It is best interpreted as:

> “This surfaced bundle preceded a successful retry on the same normalized target.”

It is not yet:

> “This individual lesson caused or contributed to success.”

## 2. What the antivirus analogy actually earns

The strongest public evidence is less magical and more useful than the frontier summaries suggest.

- VirusTotal Retrohunt exposes a known-good corpus of about one million files specifically to help
  rule authors spot YARA false positives. That validates paired positive/benign replay as a rule
  development practice, not a universal “one benign hit always blocks deployment” law.
  [VirusTotal Retrohunt](https://docs.virustotal.com/docs/retrohunt)
- Elastic keeps detection rules in a Git repository with schemas, parsing, packaging, validation,
  unit tests, and a release process. This is strong evidence for **rules as reviewed data in source
  control**, not for arbitrary production predicates hot-loaded from Redis.
  [Elastic detection-rules repository](https://github.com/elastic/detection-rules)
- Elastic supports rule preview and explicit exceptions for trusted activity. That maps cleanly to
  shadow evaluation plus bounded negative predicates in recall.
  [Elastic rule creation and preview](https://www.elastic.co/guide/en/security/current/rules-ui-create.html/),
  [Elastic rule exceptions](https://www.elastic.co/docs/solutions/security/detect-and-alert/rule-exceptions)
- Microsoft Defender uses beta, preview, staged, and broad update channels so defects are observed
  before global rollout. That supports staged rollout and impact monitoring, while saying nothing
  about Aurora's exact sample thresholds.
  [Microsoft Defender gradual rollout](https://learn.microsoft.com/en-us/defender-endpoint/manage-gradual-rollout)

The transferable AV mechanisms are therefore:

1. rules have identity, provenance, version, tests, and a reversible status;
2. known-good and known-bad cases are both replayed;
3. exceptions are first-class and inspectable;
4. challengers observe before they act;
5. rollout is gradual and rollback is cheap;
6. runtime cost is part of rule quality.

The following precise claims in the frontier capture are **not strong enough to become Aurora gates**
without better primary receipts: a universal single-goodware-hit hard stop, an Elastic-wide 0.1% FP
SLA, fixed 5,000/50,000-node rings, a 300-detections-per-minute auto-pull threshold, and a universal
200 ms cloud decision budget. They came from secondary or frontier synthesis, not the primary sources
reviewed here.

### The analogy break

Malware detection is usually a binary, adversarial, high-consequence classification problem. Recall
is contextual multi-label retrieval. A false recall costs attention; a missed safety constraint may
cost much more; a lesson can be relevant without being visibly used; and several useful lessons can
coexist. Aurora should import the **lifecycle and false-positive discipline**, not AV verdict
thresholds or malware-specific machinery.

## 3. What large-scale search actually earns

### 3.1 Cascades transfer directly

The classic cascade-ranking result progressively applies richer ranking functions to smaller
candidate sets, jointly managing effectiveness and latency. Aurora has the beginning of this shape
but currently mixes eligibility, retrieval, ranking, and presentation decisions.
[Wang, Lin, and Metzler, “A Cascade Ranking Model for Efficient Ranked Retrieval”](https://cs.uwaterloo.ca/~jimmylin/workspace/Ivory/docs/publications/Wang_etal_SIGIR2011.pdf)

The correct transfer is a cheap structural candidate union, then fielded lexical retrieval, then a
small transparent rerank, then an abstain/presentation decision. It does not require learned models.

### 3.2 Exposure bias is already relevant

Search research shows that implicit feedback is biased by result position and exposure; directly
learning from clicks yields biased rankers. Aurora currently logs neither position nor the candidate
set, and its render forms differ in salience. A full lesson, a compact line, and a buried boot entry
are not equivalent exposures.
[Joachims, Swaminathan, and Schnabel, “Unbiased Learning-to-Rank with Biased Feedback”](https://www.microsoft.com/en-us/research/publication/unbiased-learning-rank-biased-feedback/)

The immediate transfer is logging, not propensity weighting. Aurora needs `position`, `render_tier`,
`candidate_count`, and `exposed` now so later evidence can be interpreted honestly.

### 3.3 Non-use is not negative evidence

Search research explicitly warns that non-clicked results cannot simply be treated as irrelevant.
Aurora's unvoted impressions are even more ambiguous: the agent may not have read the text, may have
already known it, may have used it silently, or may have been unable to vote.
[Google Research, “Non-Clicks Mean Irrelevant?”](https://research.google/pubs/non-clicks-mean-irrelevant-propensity-ratio-scoring-as-a-correction/)

This invalidates both “94% noise” and auto-benching based primarily on many impressions with no
credit. The aggregate counters do not even identify a unique label for each impression: votes can be
repeated and bundle-help events overlap the surfaced population. Impressions without a joined label
are **unlabeled**, not negatives.

### 3.4 Selectivity transfers better than personalization

Research on highly selective rankers shows that limiting reranking to cases with evidence can retain
most gain while reducing risk. Aurora's “show nothing” doctrine is the right local analogue: coverage
is a controlled variable, not a failure to fill three slots.
[Bennett, Shokouhi, and Caruana, “Implicit Preference Labels for Learning Highly Selective Personalized Rankers”](https://www.microsoft.com/en-us/research/publication/implicit-preference-labels-for-learning-highly-selective-personalized-rankers/)

### 3.5 Interleaving is real, but premature here

Team-draft interleaving can compare rankers with fewer interactions than conventional online tests,
but it still depends on interpretable user interaction and credit assignment. Aurora has tiny volume,
non-independent agent sessions, heterogeneous render forms, and group-confounded `helped` labels.
[Generalized Team Draft Interleaving](https://eprints.gla.ac.uk/108076/)

The prerequisite transfer is complete exposure and decision logging. Online interleaving should wait
until labels and presentation are stable. A paired **shadow champion/challenger** comparison is safer
first because it does not alter agent context.

## 4. Statistical corrections to the panel's current framing

### 4.1 “Value rate” must not be renamed precision

Aurora computes:

`observed_value_rate = (useful + helped) / surfaced = 82 / 1335 = 6.1%`

That is a useful steering metric, but it is not precision because:

- most impressions have no label;
- `helped` is bundle-attributed;
- explicit voting is sparse and presentation-biased;
- multiple lessons can be relevant without receiving separate credit.

The only observed strong-negative count is 11 explicit noise votes. Even that is not a population FP
rate because voters and exposures are selected. Reports should use the names:

- `observed_value_rate`
- `explicit_noise_rate_among_voted`
- `label_coverage`
- `bundle_help_rate`

True precision should be reported as **unknown** until a sampled adjudication set exists.

### 4.2 Replay needs three label states, not two corpora pretending to be complete

Use:

- **positive:** explicit useful votes and manually adjudicated/named hits;
- **negative:** explicit noise votes and manually adjudicated/named false hits;
- **unknown:** unvoted impressions, raw recency fallbacks, and bundle-only helped events.

`helped` can still add a weak bundle constraint: at least one source in the shown bundle may deserve
credit. It should not create one positive training row per source.

### 4.3 A 95% aggregate retention gate is too brittle at current n

The previous floor was calibrated from one scorable historical positive. A percentage over a tiny,
corpus-churned set gives false precision. The first replay gate should have two layers:

1. **Blocking named-case invariants:** no loss of preregistered hard-positive cases and no
   reintroduction of preregistered hard-negative cases.
2. **Advisory ranking trends:** Recall@3, MRR@3/NDCG@3, negative exposure, and context cost, each with
   exact counts and uncertainty; warnings only until the effective sample is large enough.

Splits must be by time/session/task cluster, not random impressions, so mined tokens from one event do
not leak into evaluation of that same event.

### 4.4 Nightly floor auto-application would overfit drift

The corpus is young and changes quickly. Recalibrating every night on sparse, correlated labels risks
threshold oscillation and leakage. Nightly jobs may **propose** a challenger floor and replay it, but
production changes should remain versioned, shadowed, and operator-approved until a preregistered
minimum effective sample and a time-separated holdout exist. “Less than 10% change” is not a safety
argument.

## 5. Proposed architecture: the Recall Decision Plane

The core separation is:

`context → eligibility → candidate union → transparent rank → selective presentation → outcome join`

Each stage emits a bounded decision receipt. No model runs on the hot path.

### 5.1 Typed `RecallContext`

Stop asking one bag of tokens to encode every kind of intent. Build a deterministic structure:

```text
altitude:       boot | plan | action | pull
surface:        claude_hook | cursor_hook | codex | cli
tool:           shell | edit | bifrost-send | pytest | ...
verbs:          [launch, cancel, push, edit, inspect, ...]
paths:          normalized paths and path classes
task_ids:       T093, RB-28, ...
error_facts:    exception type, exit code, platform signal
free_text:      bounded/redacted lexical query
agent_context:  agent id + optional hat/scope (telemetry first)
```

The vocabulary should be small and code-reviewed. Do not mine a free-text category taxonomy nightly
from 29 active lessons. Mined route proposals can come later, but the first path classes and action
verbs should be authored from real hook inputs and named exhibits.

### 5.2 Stage A — hard eligibility and structural retrieval

- exclude superseded/benched/ineligible records;
- exact task/RB ID matches;
- exact tool/action predicates;
- path glob and module/class routes;
- explicit exception/negative predicates;
- self-echo and scope constraints.

This stage returns a **union**, not a single highest tier. An exact path rule should not erase a
simultaneous safety constraint match.

### 5.3 Stage B — fielded sparse retrieval

Score trigger, recommendation, experiment name, category, and affected paths as separate fields.
The current query-normalized IDF overlap remains the incumbent. A BM25F-like challenger is worth
shadowing because standard BM25 adds term saturation and document-length normalization; Aurora's
current scorer does not penalize verbose lesson prose for incidental matches.
[Lucene BM25Similarity](https://lucene.apache.org/core/7_6_0/core/org/apache/lucene/search/similarities/BM25Similarity.html)

Do not replace the incumbent merely because BM25 is standard. Replay decides.

### 5.4 Stage C — one versioned, transparent reranker

Boot and recall-at should consume the same feature definitions, with surface-specific policy only at
the final presentation stage. The reranker remains linear and inspectable. Every feature stores its
contribution, not just a total:

```text
structural_match + trigger_lexical + prose_lexical + provenance +
strong_credit + bounded_recency - duplicate_penalty - exception_penalty
```

Global usefulness must not silently stand in for per-agent or per-rule precision. Cross-agent
confirmation and per-agent usefulness should be logged first and promoted to ranking features only
after label semantics are repaired and sample sizes earn them.

### 5.5 Stage D — selective presentation, separate from relevance

- **full nudge:** strong structural match or preregistered safety constraint;
- **compact hint:** medium-confidence lexical match;
- **silent shadow:** challenger/candidate rule only;
- **abstain:** no candidate clears the relevant surface's bar.

Boot should remove the floorless top-three fallback. If orientation is desired, expose it as an
explicit mode or separately labelled pull surface. Do not always push three recent lessons under a new
heading; that preserves the attention cost while only fixing the label.

Duplicate suppression should operate on supersession/near-duplicate families, not a blanket
one-per-category cap. Multiple same-category safety constraints may all matter.

### 5.6 Canonical rules as reviewed manifests

Production rule predicates should be Git-tracked, schema-validated manifests compiled into the local
cache. The Store holds telemetry, proposals, shadow observations, and reversible status events.

Suggested minimum schema:

```text
rule_id, version, provenance, status
context_predicate, target_lessons_or_class
positive_terms, negative_terms, path_globs, tool_verbs
impact_class, presentation_ceiling
created_at, expires_at, supersedes
replay_receipt, rollout_receipt
```

Redis may carry an emergency **disable** or bounded weight cap behind an administrative capability;
it should not be able to inject an arbitrary production predicate that bypasses review. Local env
overrides are acceptable for shadow experiments, not production truth.

### 5.7 The decision journal — forced first

Every candidate decision needs one ID and one bounded record:

```text
decision_id, time, session, surface, altitude
engine_version, rule_bundle_version, corpus_version
redacted context signature
candidate ids + feature contributions + matched rule ids
selected/rejected/abstained reason
position, render_tier, chars, latency_ms
later feedback/outcome links
```

Below-floor candidates should be logged by ID and numeric feature vector, not by duplicating lesson
content. Raw commands may contain secrets; preserve the current normalized target only after bounded
redaction/truncation or store a keyed digest plus safe facets.

This journal enables the missing `recall-explain <decision_id>` door and makes rule-level telemetry
meaningful. For rules that overlap, record each contribution and a deterministic ablation delta; do
not pretend one rule “caused” the final score.

## 6. Feedback and lifecycle semantics

### 6.1 Evidence ladder

| Signal | Meaning now | Ranking use |
|---|---|---|
| explicit `useful` on one source | strong positive, still exposure-biased | eligible after instrumentation |
| explicit `noise` on one source | strong negative, still exposure-biased | eligible after instrumentation |
| FAIL→SUCCESS `helped` | weak positive on the surfaced bundle | do not copy to every source's precision |
| `engaged` full pull | interest/inspection, not correctness | telemetry only |
| no vote/no pull | unknown | never auto-negative |
| cross-agent confirmation | stronger provenance once source attribution is sound | telemetry first |

A future source-level help attribution can be explicit (“which lesson changed the action?”), derived
from an actual source reference in the agent trace, or conservatively assigned fractionally across a
bundle. Until then, preserve the bundle event losslessly.

### 6.2 Lifecycle

`proposed → shadow → canary → default → benched → retired`

- proposals may be authored, deterministically mined, or LLM-drafted offline;
- shadow rules evaluate without injecting;
- promotion requires named replay invariants, advisory trend receipts, latency receipts, and review;
- canary affects one opted-in surface/session at a time and is reversible;
- bench/retire decisions require explicit negative evidence or human adjudication, not silence;
- every state change is a durable event with supersession and rollback.

The existing forge and curator provide useful lifecycle shapes, but rule status and lesson status must
remain distinct populations.

## 7. Slice order and preregistered acceptance

### R0 — decision instrumentation; no ranking change

- journal score components, matched tokens/rules, candidate rank, position, render tier, latency,
  engine/rule/corpus versions;
- add `recall-explain <decision_id>`;
- record plan-altitude prompt facets instead of an empty target artifact;
- acceptance: 100% of injected test decisions explain exactly why each selected lesson cleared and
  why the highest rejected candidate did not; raw secret sentinel is absent from receipts;
- latency: warm recall p95 remains under 5 ms on the current characterization battery.

### R1 — label repair; no ranking change

- preserve flip credit as a bundle event;
- stop treating the same bundle flip as independent per-source truth in new evaluation data;
- add label coverage and explicit-noise-among-voted metrics;
- acceptance: a three-source flip produces one bundle-positive observation, not three source-positive
  replay rows; existing counters remain readable for compatibility and are marked legacy-confounded.

### R2 — unify policy and remove dishonest fallback

- introduce typed `RecallContext` and one shared feature implementation;
- remove boot's zero-base top-three relevance fallback;
- keep orientation behind an explicit labelled mode/pull;
- acceptance: the synthetic T999 probe abstains, the Bifrost probe still surfaces its exact lessons,
  and no named hard-positive replay case disappears.

### R3 — replay laboratory

- build positive, negative, and unknown sets with time/session/task-cluster boundaries;
- pin E1 boot noise, E2 explainability, E3 Bifrost hit, and E4 `run_job.py` class gap;
- report Recall@3/MRR@3, explicit-negative exposure@3, coverage, pushed chars, label coverage, and
  p50/p95 latency with raw counts;
- blocking gates are named invariants; aggregate metrics are advisory until sample size is earned.

### R4 — structural routes and fielded challenger

- seed a minimal reviewed tool/action/path-class vocabulary;
- union structural candidates with the lexical path;
- shadow a fielded length-normalized scorer against the incumbent;
- acceptance: `scripts/run_job.py` surfaces at least one relevant process-lifecycle lesson through a
  named route; unrelated file classes remain silent; candidate cap is chosen by replay, not asserted.

### R5 — rule manifests and shadow lifecycle

- schema, compiler, Git source of truth, Store telemetry/status, emergency-disable-only override;
- proposal/shadow/bench/retire receipts and kill switch;
- acceptance: an unapproved Store predicate can never inject; a shadow rule records its hypothetical
  decision; disabling the rule bundle returns byte-for-byte incumbent decisions on the replay set.

### R6 — ranking refinements only after evidence grows

Candidate refinements: bounded credit decay, per-agent credit, cross-agent provenance, duplicate
suppression, one-hop knowledge edges, and eventually online interleaving. Each is a separate challenger
with its own replay and coverage/risk receipt. No bandit, trained LTR, PageRank, or hot-path LLM at the
current sample size.

Dependencies: `R0 → R1 → R2 → R3 → R4 → R5 → R6`.

R0 and R1 are deliberately before the “smarter” matcher. Otherwise every later rule will optimize
against ambiguous telemetry and appear more certain than it is.

## 8. Differential verdict on Fable + DeepSeek

### Adopt substantially as proposed

- forced-first explainability and per-decision attribution;
- remove the boot relevance fallback;
- build a replay harness with named golden/adversarial exhibits;
- typed context/class routing;
- deterministic cheap-to-expensive stages and early abstention;
- shadow/canary/default/bench/retire lifecycle;
- no hot-path LLM, trained LTR, PageRank, or bandit now;
- record position/exposure immediately.

### Adopt with material changes

- **Rules as data:** yes, but canonical production rules are reviewed manifests in Git; Store data is
  proposals, telemetry, status, and emergency disable — not unrestricted executable truth.
- **Replay gate:** three-state labels and named invariants first; no false statistical confidence from
  a 95% percentage over tiny n.
- **Recent boot lessons:** only in explicit orientation mode, not an always-pushed substitute for the
  removed fallback.
- **Auto-bench:** only on explicit negative/adjudicated evidence with uncertainty and reversibility;
  zero credit is unknown.
- **Class routes:** seed a typed action/path vocabulary; do not let free-text categories or nightly
  clustering define production taxonomy yet.
- **Diversity:** suppress true duplicates/supersession families, not one result per category.
- **Floor recalibration:** proposal and shadow replay only; no nightly auto-apply at current n.
- **Cross-agent authority:** record it now, rank on it only after source attribution is repaired.

### Defer or reject now

- online team-draft interleaving before stable exposure/outcome attribution;
- Redis hot overrides capable of introducing arbitrary production predicates;
- simple thresholds such as “3 positives” or “20 surfacings” for automatic promotion/retirement;
- treating 6.1% observed value as precision or the remainder as noise;
- copying a bundle-level flip into per-rule precision;
- LLM gatekeeping on the hook path;
- nightly self-tuning of floors/weights against the same small corpus used to evaluate them.

## 9. Final recommendation

Approve R0 and R1 as the first fenced build specification. R2 is the first behavior-changing slice and
should not begin until the journal can explain current and challenger decisions. R3 then becomes the
permanent promotion gate. Only after those receipts exist should the team implement structural routes
or a rule lifecycle.

This sequencing still produces the adaptive system Daniel wants. It makes adaptation grow from
better evidence rather than from increasingly confident interpretation of sparse, confounded signals.
