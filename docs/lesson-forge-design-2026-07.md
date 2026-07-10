# Lesson Forge — evidence-gated content optimization for the lesson corpus

Status: current  (2026-07-09, P4: Active; v2.1 locked, F3 pending accrual)
Class: rationale

**Status: v2.1 LOCKED 2026-07-09 (Daniel).** Decisions 1-4 locked at their proposed
defaults; decision 5 locked as the TRUST LADDER (human gate through F1-F2, edits earn
auto-provisional after ~10 aligned cycles, merges never auto); decision 6 locked KEEP
(plain-field buffer). F0 begins, with PRE-REGISTERED go/no-go criteria (sec.9) committed
before the audit runs — DeepSeek pre-registers its own criteria under the same fence.
Claude-authored; reconciled same-day against DeepSeek's FENCED independent design
(research/reviewed/deepseek-forge-blind-crosscheck-2026-07-08.md — raw problem + codebase
only, no access to this doc until it answered). Headline: both designs independently
derived replay-against-credit-history as the validation gate — sec.12 for the full
convergence/divergence map. Ledger: T013. Sources:
research/reviewed/frontier-autoresearch-skillopt-skills-web-2026-07-08.md (SkillOpt
findings, all 3-vote verified), docs/recall-vnext-2026-07.md (the funnel this composes
with).

## 1. The problem, at loop altitude

The learning system now closes three loops on lesson SELECTION: what gets surfaced
(trigger-aware matching + calibrated floor), what gets credited (wrap-time credit,
engaged counter, flips), and what survives (curator bench/unbench). No loop touches
lesson TEXT. A lesson that surfaces at the right moment but is written vaguely — weak
Use-when clause, buried advice, missing contraindication — earns no credit, gets benched,
and the knowledge inside it dies on the bench. Selection can only choose among the
texts we happened to write on capture day.

The Forge is the fourth loop: rewrite lesson text from outcome evidence, under a gate
that only accepts strictly-better variants. SkillOpt (microsoft/SkillOpt, arXiv
2605.23904) proved the discipline in benchmark-land: frozen target model, optimizer
model turns scored trajectories into bounded edits, held-out validation gate, rejected
edits remembered, zero inference-time cost. Our job is translating "held-out validation"
into a world where the quality signal is sparse in-vivo credit, not replayable benchmark
rollouts.

## 2. Ground truth (2026-07-08, `stats --days 7`)

- 64 lessons (80 recall-tracked counters); 853 surfaced impressions all-time.
- helped=26 all-time; useful votes=5; noise votes=0. Value rate 3.6%.
- Credit arrival is SPARSE: 2-5 credited flips/week across the ENTIRE corpus.
  Per-lesson in-vivo A/B at these rates needs months to reach significance for most
  lessons — a pure champion/challenger gate is statistically starved. The gate design
  must not pretend otherwise.
- 21 lessons have any track record (helped or useful > 0); 43 have none.
- Push cost ~4.6k tokens / 44 injections per day: the read side is cheap and must stay
  cheap (Forge cost lives at wrap/offline, never at injection — SkillOpt's own
  zero-inference-cost principle, independently our Token Frugality rule).
- Durable evidence we already record per credit: flip events carry (target, credited
  sources, session); the injection ledger carries (altitude, target, sources, chars);
  session_signals carries per-session recall economy. **These are the raw material for
  a replay-based validation set.**

## 3. What transfers from SkillOpt, and what cannot

Transfers directly:
- **Bounded edits under a textual learning rate** — small add/delete/replace, one field
  per step, token-delta cap. Cheap discipline, no adaptation needed.
- **Strict-improvement acceptance** — never accept on vibes; accept only on measured
  non-regression + improvement.
- **Rejected-edit buffer** — rejected variants persist as negative feedback so the
  optimizer never re-proposes them (we already learned this shape: advisory prints
  evaporate; stamp durable state).
- **Optimizer/target split** — SkillOpt's frozen-target/optimizer-model pair maps onto
  the fleet: the lesson CONSUMER is any agent (claude, cursor, deepseek at action time);
  the OPTIMIZER can be a different, cheaper lane (deepseek --think offline at wrap).

Cannot transfer as-is:
- **The validation split.** SkillOpt scores candidate skills by re-running benchmark
  tasks. We cannot re-run last Tuesday's debugging session. Substitute: sec.4.

## 4. The gate (the heart of the design)

Two tiers, matched to how much signal a lesson actually has.

### Tier 0 — offline replay gate (every edit, mandatory, deterministic, no LLM)

The insight: **our matcher is deterministic, and our history is durable — so retrieval
behavior is replayable even though sessions are not.** A lesson's credited flips give
the contexts (targets/queries) where its text demonstrably mattered; noise votes and
surfaced-never-credited impressions give contexts where it fired without value.

For an edited variant V of incumbent lesson L, replay the V2 matcher offline:

1. **Must-still-match (recall floor):** for every context in L's credited set,
   relevance(V, context) >= relevance(L, context) - epsilon. An edit may not lose the
   matches that earned the lesson its keep.
2. **Should-stop-matching (precision reward):** over L's surfaced-never-credited
   contexts (sampled from the injection ledger), V matching FEWER of them than L is an
   improvement, not a regression — that is the funnel's denominator shrinking.
3. **Faithfulness + structure floor:** FAITH gate passes (no fabricated pointers);
   trigger clause still parseable (_parse_trigger non-empty); token delta within the
   edit budget; provenance fields untouched (an edit may never upgrade success/agent_id
   — no laundering via rewrite).

Score = (credited-recall preserved, noise-match reduction, token delta). Accept only if
(1) and (3) hold and the variant is >= incumbent on (2) — strict improvement on at
least one axis, regression on none. This is SkillOpt's selection split, translated:
**the flip log is the validation set.**

**Blinding rule (grafted from DeepSeek FM1):** the optimizer NEVER sees the raw credit
events the gate replays — it gets lesson text + aggregate counters + related_to edges
only. The gate runs blind, after generation, as coarse pass/fail — never as a score the
optimizer can hill-climb. With a 26-event validation set, an optimizer that can see the
targets would overfit them by lunch.

Honest limits: Tier 0 validates RETRIEVAL behavior (does the right moment still find
the lesson; do wrong moments find it less), not in-context persuasiveness (does the
text change the agent's action once shown) — and not factual accuracy, which is why the
edit operations themselves forbid new claims (sec.5). Persuasiveness only shows up in
live credit — Tier 1.

### Tier 1 — in-vivo champion/challenger (only where traffic supports it)

For lessons with surfacing rate above a floor (proposal: >= 4 impressions/week),
promoted variants enter PROVISIONAL state: the variant replaces the incumbent at the
surface (no alternation — at our volumes, splitting traffic halves an already-sparse
signal; sequential testing beats A/B here), while the incumbent text is retained on the
record (previous_text). Rollback triggers, checked by the curator's periodic pass:
- any noise vote on the variant, or
- credited-flip rate over the trailing window drops below the incumbent's trailing
  baseline (window >= 14d or >= 8 impressions, whichever first), or
- an agent explicitly flags it (recall-feedback --noise).
Rollback restores previous_text, stamps the variant into the rejected-edit buffer with
the reason. Low-traffic lessons skip Tier 1: Tier 0 + provisional-with-rollback is the
whole gate (the risk is bounded by reversibility, same bet the curator makes with
bench/unbench).

## 5. The Forge loop (Reflect -> Aggregate -> Update -> Gate), mapped to our seams

- **Candidate selection (who gets forged):** the curator's economics already name them —
  bench candidates (surfaced >= 10, credit 0) are rewrite candidates BEFORE they are
  bench candidates (forge is rehab; bench is retirement). Also: lessons with helped > 0
  but poor precision (high surfaced:helped ratio); corpus-gap flips that match no lesson
  (candidates for NEW drafts, not edits); and — grafted from DeepSeek FM2 — **credit
  regression**: a lesson that earned credit before but has been silent for its last 15+
  surfacings, the signature of trigger terms drifting from the repo's current state
  (renamed files, changed verbs; the slice-1a [age] cue is this same failure seen from
  the reader's side). Cap: <= 2 forge targets per wrap; unreviewed proposals EXPIRE
  after one cycle (DeepSeek FM4 — the textual learning rate applied at process level).
- **Reflect (evidence assembly, no LLM):** per target — credited contexts, noise/ignored
  contexts, mined credited-flip vocabulary (V2 already mines this), related_to edges
  (slice 1b), the rejected-edit buffer, full record.
- **Update (the optimizer, LLM lane):** one bounded edit proposal per target: rewrite
  the Use-when trigger clause OR the recommendation body (one field per step), within
  the token budget. Permitted ops only (DeepSeek FM5): rephrase trigger clause; fold a
  near-dup's distinct details; TRIM (delete-only); refresh stale file/path references.
  **No new factual claims, ever** — the gate tests retrieval, not truth, so truth must
  be conserved by construction. Output is a diff against the incumbent, never a full
  rewrite. Lane: deepseek --think offline (cheap, and the optimizer/consumer split
  keeps the target model frozen); claude may also propose during wrap. The optimizer
  prompt includes the rejected-edit buffer as negative feedback.
- **Gate:** Tier 0 replay; on pass -> provisional promotion + Tier 1 watch; on fail ->
  rejected-edit buffer with the failing axis.
- **Bookkeeping:** every accepted edit stamps forge_history (JSON: ts, field, delta,
  gate scores, optimizer agent); previous_text retained for rollback; funnel counters
  CARRY OVER (same experiment_name — an edit is a new coat, not a new identity).

## 6. Merge verb (the related_to harvest)

Input: durable near-dup edges from slice 1b (related_to, dims >= 4) + find_related
sweeps by the curator. Exclusion (DeepSeek): anti-pattern-tagged lessons are NEVER merge
candidates — they are disconfirmers, and blending dilutes the warning. Mechanics:
1. Draft merged lesson M from incumbents A+B (optimizer lane). Drafting rule (DeepSeek):
   the higher-value-rate incumbent's text is the BASE; fold only the other's DISTINCT
   details in, preserving its distinct trigger terms as an explicit "also applies when"
   clause — distinctness is often WHY the weaker twin earned its credits. The draft must
   preserve both trigger clauses' intent; if the two ADVISE DIFFERENTLY, that is not a
   merge candidate, it is a dissent pair — route to the dissent mechanism, never blend
   contradictions.
2. Gate: Tier 0 replay against the UNION of A's and B's credited contexts (M must match
   everything either incumbent earned), noise set = union likewise.
3. On pass: M gets a new experiment_name, inherits summed counters (helped/useful/
   engaged/surfaced — value-rate honesty preserved; stamp merged_from=[A,B]); A and B
   get superseded_by=M and leave recall surfaces (graduation mechanics — history
   preserved, full-corpus queries still see them with a [merged] tag).
4. Reversible: un-merge = clear superseded_by, retire M (same reversibility bet as
   bench/unbench).

## 7. Taxonomy and the `feedback` type (closes fold-in item 6)

Categories stay EMERGENT: the credited-flip vocabulary miner (V2) + related_to edge
clusters are the raw material; the Forge may propose a category correction as an
ordinary bounded edit (gated like any other — a category change alters routing, and
routing is replayable). We do NOT hand-build a taxonomy ahead of evidence.

The harness memory taxonomy (user | feedback | project | reference) folds in as
RECOMMENDED CATEGORY VOCABULARY, not schema: document in LEXICON.md that `--category
feedback` means "the human corrected how we work" (superset of the existing
`correction` convention), alongside domain categories. One doc line, zero migration.

## 8. Organic intake (Daniel's expand-as-we-encounter question)

Already the door, now named: anything encountered — an external SKILL.md from research,
a paper's technique, a harness rule — enters via `learn` as a zero-credit challenger:
trigger-phrased at capture, deduped against the corpus (find_related), edges stamped,
then EARNS surface time through the funnel like everything else. The Forge upgrades it
in place once it has history. The future harvester (macro slice 3) is this same door
at volume with a SKILL.md->lesson field mapping in front; it needs no new trust
machinery because the funnel + gate ARE the trust machinery.

## 9. Build slices (each gated by its own benchmark)

- **F0 — replay harness + data audit.** Reconstruct per-lesson credited/noise context
  sets from flip events + injection ledger; report distribution (how many lessons have
  >= 3 credited contexts?). Benchmark: harness reproduces the live matcher's decisions
  on historical contexts bit-for-bit; audit report lands in research/.
  (F0 is also the go/no-go: if durable history is thinner than stats suggest, F0's
  fallback slice is capture-side — persist credited contexts AT credit time — and the
  Forge waits a few weeks while the validation set accrues. Evidence before machinery.)

  **PRE-REGISTERED go/no-go criteria (claude, 2026-07-09, committed BEFORE the audit
  ran — from aggregates only: 64 lessons / 853 surfaced / 26 helped / 21 tracked; the
  detailed distribution is deliberately unseen. DeepSeek pre-registers its own under
  the same fence; the audit is judged against BOTH.)**
  1. Harness fidelity: replay agrees with the live matcher on 100% of a sampled
     current-corpus decision set (the matcher is deterministic — any mismatch is a
     harness bug, not tolerance).
  2. Edits path (rehab class, axis-2-dominant) GO if: for >= 70% of current rehab
     candidates (surfaced >= 10, credit 0), >= 8 distinct surfaced contexts are
     reconstructable from the durable ledger.
  3. Regression/merge path (axis-1) GO if: >= 50% of lessons with helped-credit have
     >= 2 reconstructable credited contexts, AND >= 80% of flip records resolve to a
     concrete replayable target string.
  4. FALLBACK trigger (accrue, don't force): if criterion 2 fails because ledger
     retention is short (suspected: the injections view is windowed), build F0b =
     capture-side durable context persistence at credit/surface time, and hold F1 for
     >= 2 weeks of accrual. Criterion 1 + partial 3 still allow building F1 machinery
     against the thin set (human gate absorbs the residual risk per the trust ladder).
  5. NO-GO (redesign, not wait): > 50% of flip targets are unreplayable in principle
     (ephemeral/session-relative strings) — then the replay premise itself fails and
     sec.4 gets rethought. This would be a finding, not a failure.
- **F1 — Tier 0 gate as a verb.** `recall-curate --forge-check EXPERIMENT --draft FILE`:
  adjudicate a proposed edit, print per-axis verdict, stamp rejected-edit buffer on
  fail. Human/agent-proposed edits only (no auto-optimizer yet). Benchmark: a
  deliberately-degraded edit is rejected on axis (1); a known-good rewrite of one real
  benched lesson passes and goes provisional.
- **F2 — optimizer pass at wrap.** Auto-propose for <= 2 curator-named targets per
  session via the deepseek lane; rejected-edit buffer feeds back. Benchmark: first
  auto-forged lesson accepted by the gate AND earns credit within 14d/8 impressions
  (the provisional window) — the headline metric: a benched-track lesson returns to
  the credited column.
- **F3 — merge verb.** Over related_to edges (candidates exist as of slice 1b).
  Benchmark: one real merge with counter inheritance, zero Tier-0 regression, and the
  dissent-pair guard proven on a contradicting pair (must refuse).
- **F4 — Tier 1 watch + rollback in the curator pass.** Benchmark: forced-regression
  drill — a deliberately-bad variant promoted in sandbox gets auto-rolled-back by the
  trailing-window rule.

## 10. Decisions for Daniel (proposals attached)

1. **Edit budget (textual learning rate):** propose <= 40% token delta, one field per
   step, <= 2 targets per wrap.
2. **Provisional window:** propose 14d or 8 impressions, whichever first.
3. **Counter inheritance on merge:** propose full sum + merged_from stamp (value-rate
   continuity over clean-slate).
4. **Optimizer lane:** propose deepseek --think offline as default (frugality + the
   frozen-target split), claude allowed at wrap.
5. **Auto-promotion authority — THE central divergence with DeepSeek's design.**
   DeepSeek: human gate ALWAYS (forge-apply/forge-reject verbs; "the synthetic replay is
   the evidence floor; the human is the gate" — realistic for a 64-lesson corpus, and
   Daniel stays in the loop at 2-3 proposals/cycle). Claude: auto-provisional with
   rollback (reversible, faster compounding, the self-improving-store headline).
   **Proposed synthesis — a trust ladder:** F1-F2 run DeepSeek's human gate; after ~10
   consecutive cycles where the human verdict agrees with the gate's verdict, F4 flips
   edits (never merges) to auto-provisional with the rollback watch. Autonomy is earned
   through demonstrated gate-judgment alignment, same shape as the security schema's
   quarantine -> escalation path.
   **Amendment (2026-07-09, from the optimizer red-team, exploit 3 "UNMEASURABLE
   laundering"):** only PASS-verdict cycles count toward ladder alignment. UNMEASURABLE
   applies are pure human judgment on evidence-free lessons — an optimizer could farm
   them for fake "aligned" history; excluding them closes that path, and the CLI marks
   every UNMEASURABLE proposal accordingly.
6. **Rejected-edit buffer:** claude keeps it (durable negative feedback, prevents
   re-proposal loops once F2 automation exists; advisory_prints_evaporate); DeepSeek
   drops it ("overkill at our scale — discard failed edits"). Propose: keep, but as a
   plain field on the lesson record (zero new machinery), revisit if it never fires.

## 11. Failure modes (adversarial pass on own design)

- **Goodhart on the replay set:** an optimizer can overfit trigger text to historical
  contexts (keyword-stuff the credited targets). Mitigations: token budget caps
  stuffing room; axis (2) punishes broad matching; Tier 1 rollback catches
  live regression; forge_history makes drift auditable. Residual risk: accepted.
- **Sparse-credit statistics:** trailing-baseline comparisons on 0-2 credits are noise.
  Mitigation: rollback triggers are one-sided (regress on ANY negative signal), and
  low-traffic lessons never get irreversible treatment. The gate never claims
  significance it doesn't have — provisional means provisional.
- **Contradiction blending in merges:** blocked by the dissent-pair guard (sec.6.1) —
  merging is for redundancy, dissent is a feature (core/recall/dissent.py exists for it).
- **Optimizer echo-loop / self-reinforcement:** the optimizer must never count its own
  provisional variant's surfacings as evidence for further edits within the window
  (one edit in flight per lesson, enforced by provisional state).
- **AAR caution (verified finding):** fixed workflows underperform for capable agents —
  so forged lessons stay ADVISORY and terse (trigger + constraint, never step-by-step
  scripts); the Forge optimizes when-to-fire and what-constraint, not procedure length.
- **Fleet trust:** optimizer lane runs read-only + draft-output; only the gate (claude
  lane / CI) writes accepted variants. Matches security schema (quarantine-by-default,
  scoped grants).

## 12. Review protocol — COMPLETE (2026-07-08, same session)

Both reviews delivered and reconciled (full texts:
research/reviewed/deepseek-forge-blind-crosscheck-2026-07-08.md,
research/reviewed/deepseek-slice1-review-2026-07-08.md).

**Converged independently (locked — two fenced designers, same mechanism):**
- Replay-against-historical-credit-events as the validation gate ("the flip log is the
  validation set" / "the historical credit events ARE the held-out set" — derived
  separately, near-verbatim agreement).
- Must-still-match credited targets; must-not-increase noise matching; merges gate on
  the UNION of both incumbents' credited targets.
- Bounded ops + ~40% textual learning rate; diff-not-rewrite.
- Merge via supersession edges (redirect, not delete) + summed counters; distinct
  details preserved, contradictions never blended.
- Taxonomy emergent from trigger-clause clustering; no external import; recomputed when
  an edit changes the clause.
- Offline-only (zero hot-path cost), <= 2-3 candidates/cycle, fail-soft throughout.

**Grafted from DeepSeek (gaps in the claude draft):** optimizer blinding from the replay
set (FM1 — sec.4); credit-regression candidate trigger (FM2 — sec.5); proposal expiry
(FM4 — sec.5); no-new-factual-claims edit ops (FM5 — sec.5); base-text merge rule +
anti-pattern merge exclusion (sec.6).

**Divergences -> sec.10 decisions 5-6:** human-gate-always (deepseek) vs
auto-provisional-with-rollback (claude) — synthesis proposed as a trust ladder; and
rejected-edit buffer keep (claude) vs drop (deepseek).

**Slice-1 review consequences for this design:** findings applied same-day (stop-verb
carve-out, honest edge-stamp print, contract docstring). The grammar-ceiling insight
(finding: past ~85% precision only INTENT separates cases, so bound damage with latches
instead of growing stopword lists) is adopted here as a Forge principle too: the gate is
coarse pass/fail with reversibility, never a precision-chasing score.

- Daniel: locks sec.10 (esp. decisions 5-6), then F0 starts.
