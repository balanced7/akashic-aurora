# Recall Heuristics — deepseek Round 0: machinery read + absorb list + counters

Status: Round 0 of live co-design (parallel with claude's opening).
Reads: core/recall/at_action.py, core/primitives/ranker.py, core/recall/curator.py,
context/relevance_budget.py, context/learning_loader.py, agent/initializer.py,
research/recall-heuristics-fence-brief-2026-07-17.md.

---

## 1. MACHINERY READ — the live relevance plane (file:line)

### The two relevance paths — they diverge at the first file read

**Path A — BOOT (context/relevance_budget.py:1-164).** `load_learnings_for_boot()`
delegates to `select_within_budget()` which scores every live lesson against the
task string using a fixed ladder:

| Score | Condition | Line |
|-------|-----------|------|
| 1.0 | Exact task-id mention (T\d\d\d in both task and lesson) | `base_score()` line 80 |
| 0.8 | Constraint with keyword overlap (category "constraint*" or RB-\d+ in text) | line 85 |
| 0.7 | File-path overlap (lesson names a file the task names) | line 89 |
| 0.5 | Category match (lesson's domain words appear in task) | line 94 |
| 0.0 | Everything else | line 96 |

Then recency (+0.05 over 30 days, line 126) and funnel credit multiplier
(usefulness_factor, lines 124-128) are applied. Greedy fill of a fixed 2000-char
budget, top hit always included.

**Path B — RECALL-AT-ACTION (core/recall/at_action.py:1-800).** The PreToolUse hook
calls `recall_at()` → `_trigger_aware_relevance()` (line ~370) which builds a
`relevance_fn` that uses:
- IDF-weighted keyword overlap via `_damped_overlap()` (lines 320-344) — corpus-level
  document frequency weights, min-hits dampener for single common-token matches
- Trigger-aware: when a lesson has a "Use when ..." clause or mined trigger_terms,
  the DESIGNED trigger gets 0.6× weight vs 0.4× for prose overlap (line 375)
- `_with_mined_triggers()` (lines 263-286) appends historically-CREDITED flip
  targets to trigger vocabulary — outcome history narrows the trigger

Then the shared `Ranker` (core/primitives/ranker.py:1-120) blends:
- relevance (0.4) × importance (0.2) × recency (0.2) × relationship (0.2)
- `usefulness_factor` (line 370-386 in at_action.py) multiplies final score:
  smoothed [0.5, 1.5] based on helped/useful/noise/surfaced counters

### The two paths share ZERO code

Boot relevance budget (`context/relevance_budget.py`) and recall-at-action relevance
(`core/recall/at_action.py`) share:
- **No ranker instance** — boot uses its own ladder; recall-at uses Ranker
- **No relevance function** — boot has a fixed tier table; recall-at has IDF+trigger
- **No credit integration** — both read `usefulness_factor` from the same Store
  counters, but they apply it DIFFERENTLY (boot: multiplicative on ladder score;
  recall-at: multiplicative on Ranker score after IDF relevance)

This is the root cause of E1-E4. Two different relevance engines, tuned independently,
neither sharing the other's learning.

### The curator — the ONLY closed loop around lessons

`core/recall/curator.py:1-80`: benches lessons that have `>=10 surfaced` AND `0 credit`
AND `>=10 days old`. Unbenches any lesson whose counters later show credit. Ghosts
(zero-credit counters for deleted lessons) are pruned. This is the ONLY mechanism that
removes a lesson from recall based on its track record — and it operates on LESSONS,
not on HEURISTICS. A rule that misfires can't be retired.

### Where per-rule attribution would hang

- `base_score()` in relevance_budget.py returns a SINGLE float — the highest tier that
  matched. If a lesson matches at tier 0.7 (file-path overlap) but is ACTUALLY
  irrelevant (E4: the lesson is about the file's DOMAIN, not its content), there is
  no record of WHICH rule fired. The curator benches the LESSON when it accumulates
  noise votes, but it doesn't know WHICH rule caused the noise.
- `_trigger_aware_relevance()` in at_action.py similarly returns a single float with
  no rule attribution.
- Per-rule counters require: each scoring path records (rule_id, lesson_id, score_component)
  at decision time, and the curator can query: "which rules produce the most noise-voted
  surfacings?"

---

## 2. ABSORB LIST — mechanisms from AV and search ranking

Ranked by leverage-per-cost. Each names the exact Aurora seam.

### A1 — RULE-LEVEL ATTRIBUTION WITH PER-RULE COUNTERS (cost: LOW, leverage: HIGH)

**Source:** AV signature lifecycle (every detection carries a signature ID; false-positive
rate tracked per-signature; signatures above FP threshold are auto-disabled).

**Mechanism:** Every relevance decision records `(rule_id, lesson_id, score_contribution)`.
The existing `bump_surfaced()` and `record_feedback()` already track per-lesson counters.
Add per-rule counters at the SAME Store: `recall:rule:<rule_id>` → {surfaced, useful, noise,
helped}. The curator gains a rule-dimension query: "which rules have noise rate > 20% over
the last 30 days?" → those rules are flagged for human review or auto-weight-reduced.

**Aurora seam:** `core/recall/at_action.py:_trigger_aware_relevance()` and
`context/relevance_budget.py:base_score()`. Each rule in the ladder (exact T-id, constraint,
file-path, category, trigger-clause, IDF-overlap) gets a RULE_ID constant. `bump_surfaced()`
gains an optional `rule_ids` parameter. The curator (`core/recall/curator.py`) gains
`rule_report()` and `apply_rule_decay()`.

**Pin:** After 100+ surfacings of a rule, its noise rate converges within ±5% of the
lesson-level noise rate it produces.

**Why this is #1:** No new infrastructure. The Store counters already exist per-lesson;
per-rule counters are the same key pattern with a different prefix. The curator already
scans counters; adding a rule axis is ~80 lines. And it answers the exact question
E1/E2/E4 raise: "which rule fired wrong?"

### A2 — LEARN-TO-RANK ON IMPLICIT FEEDBACK (cost: MEDIUM, leverage: HIGH)

**Source:** Web search click models (position bias correction, inverse propensity weighting,
counterfactual evaluation). The "click" in our system = a `useful` or `helped` vote.

**Mechanism:** Train linear weights for the Ranker's four components (relevance, importance,
recency, relationship) using the existing funnel data as training labels. Each surfacing is
an "impression"; each useful/helped/noise vote is a "click" (positive/negative). A linear
model (logistic regression, ~4 features) learns per-seat or per-context weights from the
last N days of funnel data. The weights are INSPECTABLE (linear coefficients, not a neural
net). Retrained nightly from the funnel; versioned in the Store.

**Aurora seam:** `core/primitives/ranker.py:DEFAULT_WEIGHTS`. Today these are hardcoded
{relevance:0.4, importance:0.2, recency:0.2, relationship:0.2}. A `WeightLearner` module
reads `recall:use:*` counters + `recall:surface` stream, computes optimal linear weights,
and writes `recall:weights:v<N>` to the Store. The Ranker reads the latest version.

**Pin:** After 500+ impressions across 5+ sessions, the learned weights produce a
statistically significant improvement in useful/(useful+noise) ratio vs the default weights
(p < 0.05, binomial test). Regression: a `--weights-reset` flag restores defaults.

**Risk managed:** Linear weights are INSPECTABLE (not a black box). The deterministic
doctrine is preserved: the Ranker's output for a given (items, query, weights_version) is
deterministic. Weights change DISCRETELY (nightly retrain, version-stamped), not
continuously. A `--freeze-weights` flag locks the current version for reproducibility.

### A3 — QUERY UNDERSTANDING / EXPANSION (cost: LOW, leverage: MEDIUM)

**Source:** Web search query expansion (synonym expansion, acronym resolution, entity
linking). Our "query" is the task string or the file path.

**Mechanism:** Before scoring, expand the query with corpus-derived synonyms. Not an
external thesaurus — the corpus itself defines synonyms. A lesson named
`mcp_stdio_subprocess_stdout_wedge` and a task containing "MCP boot hang" have zero
token overlap (E1). But they share the CONCEPT "MCP subprocess stdout." The expansion
maps: "MCP boot" → {mcp, subprocess, stdout, boot} from the lesson corpus,
"hang" → {wedge, timeout, block} from the lesson corpus. This is a deterministic
corpus-indexed lookup, not an LLM call.

**Aurora seam:** `core/recall/at_action.py:_parse_trigger()` already extracts trigger
clauses. Add `_corpus_term_map()` — a pre-built mapping from corpus tokens to co-occurring
tokens in the same lessons and their trigger clauses. Rebuilt on `warm_cache()` (off the
hot path). The expanded query feeds the same IDF matcher.

**Pin:** E1 (boot with "recall heuristics evolution: absorb antivirus + web-search ranking
patterns" → 0 relevant lessons). After query expansion, the same task surfaces lessons
containing "ranking," "feedback," "noise" — domain terms that the raw task string doesn't
contain but the CORPUS connects.

**Not transferable:** Query expansion via LLM (generating synonyms) — violates the
deterministic doctrine and costs API tokens. Corpus-indexed expansion is mechanical.
Also NOT transferable: user intent classification (navigational/informational/transactional) —
our queries are tool calls and task strings, not search queries. The intent is already
explicit.

### A4 — HEURISTIC LADDER WITH CHEAP→EXPENSIVE STAGING (cost: MEDIUM, leverage: HIGH)

**Source:** AV layered detection (signature→heuristic→behavioral→ML→cloud reputation). Each
layer is more expensive AND more accurate; the cheap layer filters first.

**Mechanism:** The recall hot path (PreToolUse hook) must complete in <~50ms to not delay
the action. Today it runs ONE relevance function. Instead:

- **Tier 0 — CACHE (0ms):** If this exact (target, query) pair was scored in the last
  N minutes, return cached result.
- **Tier 1 — TOKEN MATCH (~1ms):** The existing IDF-weighted keyword overlap. If score
  > threshold, return immediately.
- **Tier 2 — TRIGGER MATCH (~5ms):** Query expansion + trigger-aware relevance. Fallback
  when Tier 1 produces weak results.
- **Tier 3 — FULL CORPUS RANK (~20ms):** All lessons ranked by learned weights. Only when
  Tier 1-2 produce nothing above the relevance floor.
- **Tier 4 — OFFLINE (~nightly):** Weight retraining, corpus term map rebuild, rule
  effectiveness report.

**Aurora seam:** `core/recall/at_action.py:recall_at()` — the single entry point. Each
tier is a function with the same (items, target, query) → (results, score, tier_used)
contract. The tier router picks based on: is the query cacheable? Is it a known-cold
pattern? What was the score from the last tier?

**Pin:** Tier 0-2 serve >90% of recall-at calls from cache or cheap token/trigger match.
Tier 3 fires on <10% of calls. Tier 4 is nightly. Latency budget: <50ms for hook-fired
recall-at, <200ms for CLI recall-at.

### A5 — ONLINE EVALUATION: INTERLEAVING + COUNTERFACTUAL LOGGING (cost: HIGH, leverage: MEDIUM)

**Source:** Web search interleaving (A/B test: show results from two rankers interleaved,
measure which gets more clicks). Counterfactual logging (log the ranker's decision + the
outcome for offline replay).

**Mechanism:** When the Ranker produces N results, interleave results from the CURRENT
weight version and the PREVIOUS weight version. Track which version's results get more
useful votes. This is ONLINE eval — the agent sees mixed results and votes normally.
The system learns which ranker is better without a separate eval set.

**Aurora seam:** `core/recall/at_action.py:recall_at()` — the render step. After ranking,
alternate: result 1 from current weights, result 2 from previous weights, result 3 from
current... Track per-version votes.

**Pin:** After 200+ interleaved impressions, the version with higher useful/(useful+noise)
ratio is identifiable with p<0.1.

**Not transferable for NOW:** This requires a SECOND weight version to be live
simultaneously — which means the learned weights infrastructure (A2) must exist first.
A2 → A5, not the reverse. Also: position bias matters in search (higher-ranked results
get more clicks regardless of relevance). In our 3-item recall surface, position bias
is minimal — the agent reads all 3. So the complexity of position-bias correction
(inverse propensity weighting) is NOT worth importing.

### A6 — FRESHNESS + AUTHORITY SIGNALS (cost: LOW, leverage: LOW-MEDIUM)

**Source:** Web search freshness (news queries want recent results; evergreen queries want
authoritative results regardless of age). Authority (PageRank — but for lessons: credit
from OTHER agents weighs more than self-reported success).

**Mechanism:** The Ranker's recency component already applies exponential decay. But the
DECAY RATE should be query-dependent. A query containing "T086" (task-id) wants RECENT
lessons (the task is active now). A query containing "method baseline" wants AUTHORITATIVE
lessons (evergreen contract). `relationship_weight` already exists but is unused (all 0.2).
Add a `_freshness_intent(query)` function that returns "fresh" (task-id, error message,
crash) or "evergreen" (architecture, design, method). Fresh queries get recency weight 0.3;
evergreen get recency weight 0.1. Authority: lessons credited by OTHER agents get a +0.1
importance boost (cross-agent validation).

**Aurora seam:** `core/primitives/ranker.py:DEFAULT_WEIGHTS` — make them query-dependent:
`Ranker.rank(items, query, intent=freshness_intent(query))`.

**Pin:** A task-id query (e.g. "T086 seat reconciliation") surfaces lessons from the
last 14 days before lessons from 30+ days ago. An architecture query (e.g. "bus lane
routing") does not penalize older authoritative lessons.

### A7 — DEFINITION LIFECYCLE: BORN→ACTIVE→DECAYED→RETIRED (cost: MEDIUM, leverage: MEDIUM)

**Source:** AV definition lifecycle (signature deployed → monitored for FP rate → retired
when FP rate exceeds threshold → replaced by better signature). The lifecycle is AUTOMATIC
for known-bad, HUMAN-GATED for retirement.

**Mechanism:** Every relevance rule (the `base_score` tiers, the IDF matcher, the trigger
parser, the query expander) is a versioned rule with a lifecycle state. Rules are born as
`proposed` (manual, from a reconciliation or operator action). Promoted to `active` after
a quiet period (N impressions, FP rate < threshold). Auto-decayed to `decayed` when FP
rate exceeds threshold for M days. Human-retired to `retired` with a replacement pointer.

**Aurora seam:** New module `core/recall/rule_lifecycle.py`. Rules stored as versioned
Store atoms: `recall:rule:<rule_id>:<version>` → {state, created, fp_rate, replacement}.
`base_score()` reads the active version of each rule. The curator's `rule_report()` feeds
the lifecycle state machine.

**Pin:** A rule in `decayed` state has its weight multiplied by 0.25. A `retired` rule
is never consulted. `proposed` rules run shadow-only for N impressions before promoting.

### A8 — GOLDEN CORPUS GATE (cost: HIGH, leverage: LOW-MEDIUM)

**Source:** AV regression testing (a fixed corpus of known-clean and known-malicious
samples; every definition update is tested against the corpus before deployment).

**Mechanism:** A set of ~20-30 hand-curated (task, expected_lesson_ids) pairs. Before
promoting a new weight version or rule, the gate runs the golden corpus and verifies:
known-good matches still fire, known-noise matches still don't. A regression is a FAIL →
the promotion is blocked.

**Aurora seam:** New module `core/recall/golden_corpus.py`. Corpus stored as
`state/recall/golden_corpus.json`. `check_golden_corpus(weights_version, rules_version)`
→ {pass, failures}. Called by `WeightLearner.promote()` and `rule_lifecycle.promote()`.

**Honest bound:** n~40 credited events (E5: helped=34, useful=46). A golden corpus of
20-30 query pairs with n~40 total positive events means ~1.5 expected true-positives per
query pair. The statistical power is LOW. This gate can catch GROSS regressions (a known-good
lesson stops firing completely) but cannot distinguish a 10% relevance drop from noise.
**Verdict: BUILD the gate (it catches gross regressions), but do NOT gate on statistical
significance from n~40.** The gate is a smoke detector, not a precision instrument. It
will grow statistical power as the corpus and credit events grow.

---

## 3. PREPARED COUNTERS — against claude's expected positions

### Counter: heuristics-as-data vs heuristics-as-code

**My position: BOTH. Rules are CODE (deterministic, version-controlled, auditable).
Rule EFFECTIVENESS is DATA (per-rule counters, learned weights, golden corpus results).**

A rule as pure data (a JSON blob in the Store) is correct for DEPLOYMENT (hot-reload
without code deploy) but wrong for AUDIT (who changed it, when, why?). A rule as pure
code (in relevance_budget.py) is correct for AUDIT (git log) but wrong for AGILITY
(can't hotfix a misfiring rule without a deploy).

**Compromise: rules live in CODE as the source of truth (git-tracked), with a REDIS
OVERRIDE path for hotfixes.** The same pattern I proposed for the packet routing table
(Redis override for hotfix, code is canonical). A `recall:rule_override:<rule_id>` key
that, if present, overrides the code version. `py agent_cli.py recall-rule-override
--rule file_path_match --weight 0.3` writes the override. `recall-rule-override --clear`
removes it. The override is visible in `recall-rule-report`. Git is the permanent
record; Redis is the temporary field fix.

### Counter: golden corpus gate at n~40 is a smoke detector, not a gate

If claude proposes gating new rules/weights on the golden corpus, my counter is: the
corpus is too small. At n~40 credited events and 20-30 query pairs, the expected
true-positive count per query pair is ~1.5. A single missed match drops the recall
from 1.5 to 0.5 — a 66% "regression" that is actually noise. If we gate on "any
regression," we block legitimate weight updates. If we gate on "p<0.05," we never
block anything because the power is too low.

**The gate should be: WARNING on any regression, BLOCKING only on GROSS regression.**
Gross = a known-good lesson that SHOULD match a query drops completely out of the top-K
results. This is a smoke detector: it answers "did we break recall entirely for this
query?" — not "is recall 10% better or worse?" The statistical precision gate grows
with the corpus.

### Counter: learned weights (linear) do NOT violate deterministic doctrine

The deterministic doctrine (P1 in method baseline) says: same input → same output.
Learned linear weights satisfy this. The weights are FROZEN at a version — a nightly
retrain produces a new version, but the Ranker with version N always produces the
same scores for the same (items, query). The version is stamped in the boot digest:
"recall weights: v7 (2026-07-17)."

Furthermore: linear weights are INSPECTABLE. A coefficient of 0.15 on recency means
"recency matters less than the default 0.2." A human can read that. A neural net's
weights are opaque; linear regression coefficients are not. This is the same
transparency property that makes AV signature rules auditable: "this rule uses a
byte-pattern at offset X" is inspectable; "this rule uses a 128-dim embedding" is
not.

### Counter: cheap→expensive staging cutoff on the hot path

The PreToolUse hook runs in ~200-500ms total (Python startup + recall-at + guard checks).
Recall-at is budgeted at <50ms of that. The staging:

- **Tier 0 (cache): <1ms** — always checked first. A `(path, command_hash) → last_result`
  cache with 120s TTL. Most tool calls repeat on the same files.
- **Tier 1 (token match): ~1ms** — IDF-weighted overlap. The existing `_damped_overlap()`.
  This is ALREADY the hot path; it's fast because it's pure Python string ops.
- **Tier 2 (trigger+expansion): ~5ms** — adds query expansion lookup (pre-built dict,
  O(1)) and trigger-aware rerank. Only when Tier 1 produces results below the
  relevance floor.
- **Tier 3 (full Ranker): ~20ms** — all 349 lessons ranked with learned weights. Only
  for CLI `recall-at` (not the hook — the hook never needs full corpus rank).

**Cutoff rule:** the hook NEVER runs Tier 3. Tier 3 is CLI-only. The hook runs Tier
0→1→2, with a hard 50ms wall-clock budget. If Tier 2 hasn't returned within 50ms from
hook start, return Tier 1 results. The `FAIL_OPEN` discipline applies: stale/budget-
exceeded recall is better than a delayed tool call.

---

## 4. WHAT DOES NOT TRANSFER (analogy-break honesty)

- **Cloud reputation queries (AV):** Our corpus is LOCAL. There is no "herd immunity"
  from other Aurora instances. Cross-agent credit (A6) is the closest analog, but it's
  within ONE instance, not across deployments.

- **User intent classification (web search):** Navigational/informational/transactional
  don't apply. Every recall query is a tool call or task string — the intent is explicit.

- **Adversarial classification (AV):** AV engines defend against malware authors actively
  trying to evade detection. Our lessons have no adversary trying to game the recall
  system. (The Jester Forge is the closest analog, but it attacks the KNOWLEDGE STORE,
  not the RECALL ENGINE.)

- **Position bias correction (web search):** Top-ranked results in web search get more
  clicks regardless of relevance. Our 3-item recall surface is read in full by the agent;
  position bias is negligible. Importing inverse propensity weighting would be ceremony.

- **Query performance prediction (web search):** Pre-retrieval QPP estimates whether a
  query will produce good results before running the full ranker. We always run the
  ranker (349 items is small). Not worth the complexity.

- **Collaborative filtering (web search personalization):** "Users who searched X also
  clicked Y." Our corpus is multi-agent but single-instance. Cross-agent credit (A6) is
  the correct granularity; per-query collaborative filtering is over-engineered for N=3-5
  agents.
