# Keeping recall honest — critic vs. dialectical retrieval (the decision)

> **The fork, decided.** Should we defend recall against confirmation bias with (1) a second,
> independently-*trained* adversarial critic, or (2) an elegant modification of the existing
> pipeline? This doc settles it against the 2023–2026 literature, our own code, and an independent
> read from Gemini. **Recommendation: Path 2 now, tiered; Path 1 gated to a distant V2 that only
> earns its cost after we can measure.** Written 2026-07-01, for review.
>
> Companion docs: `retrieval-critic-design.md` (the detailed Tier design), the
> `epistemic-risk-register` note (F1 laundering / F2 sycophancy / F3 recommender loop), and the
> `adversarial-critic-partner-idea` note (Path 1's original framing). This doc is the decision layer
> over those.

## TL;DR

- The failure mode is real and it is **in the code, not in the agent**: the Ranker scores by
  similarity-to-the-current-action, importance is boosted by *self-reported* success, and
  `usefulness_factor` rewards agreement. Recall surfaces what agrees with the plan, hedge-stripped
  and ranked #1. **This is confirmation bias implemented as a ranking function.**
- **A trained critic (Path 1) is premature.** The single most decision-relevant finding —
  Cross-Context Review (2026) — shows that *context separation alone* captures most of an
  independent critic's value at ~zero infrastructure. Training a critic buys a marginal gain over a
  free move, before we can even measure whether the gain exists.
- **The elegant modification (Path 2) is the right first program** and has fresh, independent 2026
  academic backing (O-RAG). It reuses the FAITH-1 seam and the Ranker, stays deterministic-first,
  and bakes "consider the opposite" into the *shape* of retrieval.
- **The sharpest risk is not the mechanism — it's the corpus.** Gemini named it: *confirmation by
  omission.* A dissent-surfacer is only as good as the dissent that exists and is discoverable. So
  the plan must treat the **write-side and corpus health as first-class**, not just retrieval.
- **Measurement comes first (Slice 0).** Without a ground-truth eval of "did recall mislead the
  agent," any engagement metric is Goodhart bait. Build the tiny labeled harness *before* the fix.

---

## Status — Slices 0 & 1 shipped (2026-07-01)

Built and green (full suite + boundaries); the real numbers refined the plan.

- **Slice 0 — the eval harness** (`tests/test_counter_eval.py` + `tests/fixtures/counter_fixture.py`):
  a labeled gold set (counter / no-counter, all three counter kinds + precision distractors), metrics
  (counter-recall / silence-accuracy / counter-precision / per-kind), and a live-store coverage probe.
  Findings: the corpus is **90 `yes` / 3 `no` / 2 `partial` / 0 anti-patterns** — confirmation-by-omission
  is the *measured* present state, not a hypothetical. A naive keyword finder **floods 81/90** of real
  successes with spurious generic-token collisions, so keyword matching can't even *measure* dissent.
- **Slice 1 — the counter-finder** (`core/recall/dissent.py`, wired into `recall_at`/`render`):
  a TF-IDF cosine topic-gate (kills the flood) + **an explicit stance signal required** (`anti_pattern`
  or a contradicts/refutes link). Opposite-*outcome* is forbidden as a trigger — two experiments showed
  outcome ≠ stance (a `partial` lesson can carry *agreeing* advice) and that genuine conflicts are
  lexically invisible (cosine ≈ 0.05). On the gold set: **precision 1.0, silence 1.0, anti-pattern recall
  1.0**; opposite-success / conflicting-recommendation are deferred to a later semantic tier, *not faked*.
  On the real corpus it surfaces **0** counters — correct, because there are no explicit stance markers yet.
- **Consequence (revises §7):** the binding constraint is **corpus content, not the reader**. Slice 2
  (write-side capture of anti-patterns / contradicts-links) is the lever, and its biggest risk is
  **adoption** — agents won't record dissent unless it is near-free. An independent review (Gemini)
  concurred on every point above.

---

## 1. The problem, in our own code

`core/recall/at_action.py` + `core/primitives/ranker.py`, precisely:

```
score = 0.4·relevance + 0.2·importance + 0.2·recency + 0.2·relationship   (Ranker)
final = score × usefulness_factor∈[0.5,1.5]                                (_lessons)
importance = 4 if success∈{yes,true} else 3                                (_project_items)
```

Three properties make it quietly self-confirming — each is a line of code, not a vibe:

1. **`relevance` = keyword overlap with the *current action*** (`keyword_relevance`). It returns what
   *resembles what you're about to do* — exactly the evidence that confirms the plan. It can only
   *match*; it has no notion of *opposition*.
2. **Self-reported success is boosted** (`importance=4`). The author's own "it worked" outranks a
   sibling "it failed in context Y." Provenance tags honestly label this `[worked]` (= self-report,
   not verified) — but labelling the bias is not removing it.
3. **`usefulness_factor` rewards agreement** — `useful` votes and FAIL→SUCCESS `helped` credit push
   the most-confirmed lessons up. It's an automatic accelerator with only a manual brake.

FAITH-1 (`core/primitives/faithfulness.py`) already guards *faithfulness to source* — a surfaced
line can't fabricate a pointer or a number. It does **not** ask the harder question: *is this the
whole picture, or the agreeable slice of it?* That question is the gap this program fills.

## 2. The two paths, precisely

**Path 1 — a second, independently-*trained* adversarial critic.** A separate model that catches the
actor's mistakes, improves at critiquing over time, and self-grades on catching real mistakes.
Lineage: CriticGPT (synthetic-bug insertion for ground truth), Self-Taught Evaluators (iterative
synthetic contrastive pairs, no human labels), Prover-Verifier games (helpful/sneaky prover +
verifier co-training), debate / scalable oversight.

**Path 2 — an elegant modification of the pipeline.** Change the *unit of retrieval* from "best
supporting lesson" to a **position = thesis + its strongest live counter.** Deterministically hunt
the same corpus for a genuine contradiction (opposite `success`, matching `anti_pattern`, conflicting
recommendation); surface one `counter: … (source)` line when it clears a bar, stay **silent** when
there's no real counter (no manufactured false balance). Escalate to a cheap *independent* LLM critic
(fresh context, blind, default-to-refute) only on high-stakes/contested actions. Reuses FAITH-1 + the
Ranker; deterministic-first; no training.

## 3. What the evidence says (2023–2026)

| Claim relevant to the decision | Source | Bearing |
|---|---|---|
| LLMs largely **can't self-correct reasoning without external feedback**; same-context self-critique often *degrades* it | Huang 2310.01798; Kamoi 2024 survey; Zhang 2025 | Kills naive "ask the model to critique its context." Independence is mandatory. |
| **Self-correction blind spot**: models fail to fix errors in their *own* output but fix the *identical* error framed as *external* input | Tsui 2025 | The cheap lever: re-present the actor's retrieval as *external* input to a blind critic. |
| **Cross-Context Review**: a critic in a *separate session blind to production* beats same-session self-review (F1 28.6% vs 24.6%, p=.008) and beats a context-aware subagent (23.8%). Benefit is *context separation itself*; "no infrastructure, one extra session." **But best F1 is low — <⅓ of injected errors caught.** | 2603.12123 (2026) | The bridge. Most of Path 1's value is free via context separation. Also: any LLM critic is a *weak signal* — inform, don't gate. |
| **Confirmation bias is empirically real in LLMs**; a plain "consider counterexamples" prompt lifted rule-discovery **42%→56%** | 2604.02485 (2026) | The core Path-2 move works *specifically on LLMs*, even though it's mixed in humans. |
| **RAG must represent diverse opinions**: "factual queries minimize posterior entropy; opinion queries must preserve it"; +26.8% viewpoint diversity | O-RAG 2604.12138 (2026) | Independent academic twin of "retrieve positions, not confirmations." |
| Conflict-aware retrieval is a hot, validated area (detect/ arbitrate conflicting sources; NLI for stance) | DRAGged-into-Conflicts 2506.08500; ArbGraph 2604.18362; 2510.03418 | Tier 1's contradiction-hunt is mainstream, not exotic. |
| **CriticGPT** caught 85% of code bugs vs 25% human — but needs a synthetic-bug **ground-truth training pipeline** | 2407.00215 | Path 1 is powerful *and* expensive; needs labels we don't have. |
| **Self-Taught Evaluators**: no human labels, but a **70B model + RewardBench-style eval harness** | 2408.02666 | Path 1's "trains itself" needs an eval we haven't built. |
| **Multi-critic can *amplify* bias** and converge sycophantically | Judging with Many Minds 2505.19477 | Don't stack model-judges. Keep few + corpus-grounded. |
| Our own **FAITH-1** rejected LLM-as-judge (self/position bias), went deterministic | this repo | Precedent: deterministic-first at the seam. Path 1 re-imports the bias FAITH-1 fled. |

**Honesty correction to our prior doc:** `retrieval-critic-design.md` calls "consider the opposite"
"the most consistently effective" human debiasing move. The refreshed human evidence is **mixed at
best**. What rescues the design is that (a) the *LLM-specific* result is positive (2604.02485), and
(b) our mechanism makes the **corpus** do the considering structurally — it doesn't depend on the
agent's willpower or introspection, which is exactly the part that fails.

## 4. The decision, and why

**Path 2 first, built as tiers; Path 1 gated to a distant, measurement-triggered V2.**

The reasoning, in order of weight:

1. **Cross-Context Review collapses the cost argument for Path 1.** If a *free* move (fresh blind
   session) captures most of the independent-critic value, spending weeks on a training pipeline to
   beat it — before we can measure the gap — is optimizing the wrong term. Build the free thing first.
2. **We can't measure a trained critic yet.** CriticGPT needs ground-truth bugs; Self-Taught
   Evaluators needs a RewardBench-equivalent for *our* domain ("did this recalled lesson mislead the
   agent?"). We have neither. Training a critic against a metric we can't compute is how you Goodhart.
3. **Path 1 re-imports the exact bias FAITH-1 fled**, and multi-critic stacking can *amplify* it
   (2505.19477). Deterministic-first is our house style *and* the safer default.
4. **Path 2 is deterministic, reuses two existing seams, and has independent 2026 backing** (O-RAG).
   It changes the *shape* of retrieval so pure self-praise is structurally impossible whenever a real
   counter exists — at corpus-read cost, no hot-path LLM.
5. **The two paths are not mutually exclusive; they're a sequence.** Path 2's Tier 2 *is* a cheap,
   context-independent critic (CCR-style). Path 1 is just Tier 2 with weights that update — a V2
   optimization of the same slot, worth it only if Tier 2 plateaus *and* we have the eval to prove it.

This also answers the three scoping questions parked in the `adversarial-critic-partner-idea` note:
**integration target** = extend Akashic's existing pipeline (not a standalone system); **mechanism**
= architectural/deterministic first, training deferred; **compute** = none needed now (the local GPU
is a V2 question, not a V1 one).

## 5. Gemini's independent read (verbatim-summarized)

Asked blind, with the same evidence, Gemini reached the same call — **Path 2** — and added value on
risk and measurement:

- *"Your system is not merely prone to confirmation bias; it's architected to enforce it."* Agrees
  the mechanism is the ranking function.
- **Path 1 premature**: CCR is "the killer blow"; validate the *value of surfacing dissent* with the
  cheap deterministic approach + a simple independent LLM check first; a trained critic is "a distant
  V2."
- **The risk it surfaced (and I under-weighted): confirmation by omission.** *"You'll have built a
  mechanism to find dissent, but if the dissent isn't present or discoverable above a threshold,
  you've simply moved the goalpost… The outcome for the agent is identical: only confirming
  evidence."* → the corpus content and write-side matter as much as the retrieval change.
- **Measurement**: favor proxies for *engaging with diversity* over "correctness" — a
  "dissent-resolution" instrument (accepted / accepted-counter / ignored-both / needed-more), and
  watch abandonment (are counters being tuned out as noise?).

Where I diverge from Gemini: its engagement metrics (decision-latency delta, dissent-engagement rate)
are themselves Goodhartable and hard to instrument for an autonomous agent. I keep its
*resolution-distribution* idea and its exposure-not-correctness framing, but anchor the program on a
small offline **labeled eval** (Slice 0) rather than live engagement telemetry.

## 6. The sharpest risk: confirmation by omission

A dissent-surfacer is only as good as the dissent in the corpus. Today the **write-side is
agreement-biased too**: agents record "X worked" far more than "X failed in context Y," and a missing
`success` is normalized to `no`, not to a real post-mortem. So the corpus underproduces exactly the
counters Tier 1 needs. Implications the plan must honor:

- **Retrieval alone is insufficient.** Pair every retrieval change with a **coverage signal** ("all
  retrieved lessons share one view — corpus may be one-sided here") so silence-from-absence is
  distinguishable from silence-from-agreement.
- **The write-side is in scope.** Nudge failure/counter capture (cheap: a JIT "what would make this
  fail?" at learn-time — ties into the directive-friction-audit's learn-prompt) so the corpus grows
  the disconfirmers. Without this, Tier 1 quietly degrades to today's behavior.
- **Tier 3 (corpus immune system) is not optional polish** — it's the mechanism that keeps the
  disconfirmer supply alive as lessons supersede each other.

## 7. The plan — phased, each slice gated by a measurement

Ordered so the cheapest, highest-learning moves ship first and nothing is built before we can tell if
it works.

- **Slice 0 — the eval harness (do this FIRST).** Hand-label a small set (~30–50) of
  `(action, corpus-state, is-there-a-real-counter, should-it-change-the-action)` cases drawn from the
  real store + a few synthetic contradictions. Deterministic, offline, re-runnable. This is the only
  thing that lets us say "the fix helped" without Goodharting engagement. *Measure:* precision/recall
  of "surfaced a real counter when one existed" and "stayed silent when none did."
- **Slice 1 — Tier 1 deterministic dissent surfacing (the smallest shippable proof).** For the top
  lesson, scan the corpus for an opposite-`success` / `anti_pattern` / conflicting-recommendation
  lesson on the same tokens; if it clears a strict bar, append one `counter: <text> (source:)` line;
  else silent. Extends `_lessons()` / `render()`; fail-soft; FAITH-gated like everything else.
  *Measure against Slice 0.* Start strict (few, high-precision counters); loosen only with evidence.
- **Slice 2 — coverage signal + write-side nudge (kills confirmation-by-omission).** Emit the
  "corpus may be one-sided here" flag when the top-k are one-stance; add a JIT learn-time prompt that
  invites a counter/failure-mode. *Measure:* rate of one-sided-topic flags over time (should fall as
  the corpus fills); counter-capture rate at learn-time.
- **Slice 3 — Tier 2 cheap context-independent critic (CCR-style).** A fresh, blind, default-to-refute
  pass using `ask_gemini` / a cheap model, **trigger-gated** (high-stakes / irreversible / Tier-1
  found a conflict / low confidence), **async, cached, budget-capped, advisory-not-blocking**. This is
  the free capture of most of Path 1's value. *Measure:* on the Slice 0 set, does Tier 2 catch real
  counters Tier 1 missed? At what token cost per catch?
- **Slice 4 — trained critic (Path 1), GATED, maybe-never.** Only if Slices 1–3 measurably *plateau*
  below a useful bar AND Slice 0 has grown into a real eval set. Then, and only then, evaluate
  Self-Taught-Evaluator-style iteration on the local GPU. Until that gate trips, this stays a note,
  not a build.

## 8. How we measure — and avoid Goodhart

- **Ground the loop in Slice 0's labeled set**, not in live "engagement." Engagement metrics
  (latency, click-through) reward a *noisier* critic; precision/recall on real counters rewards a
  *right* one.
- **Never reward "finds problems."** Tier 3's heeded/correct meta-signal must be calibrated so we
  don't grow a sycophantic critic that manufactures dissent (the F2 loop, one level up).
- **The critic informs, it doesn't veto** (except hard FAITH fails). The goal is *calibrated*
  re-evaluation, not universal doubt — a critic that challenges everything gets tuned out (crying
  wolf), which is its own failure.
- **Silent-when-empty, small-when-not.** Every added line is context-rot risk; the bar for speaking
  is high by construction.

## 9. Open questions (for review)

1. Slice 0 labeling: who adjudicates "should it have changed the action"? (Proposed: you + me on a
   small set; keep it small enough to stay honest.)
2. The bar for "a real counter" vs. false balance — start strict where exactly? (opposite `success`
   on ≥N shared salient tokens? a matching `anti_pattern`?)
3. Tier 2 trigger policy: which repo actions are "high-stakes"? (irreversible git ops, schema/contract
   edits, deletes?)
4. Does the write-side nudge (Slice 2) belong here or fold into the directive-friction-audit's
   learn-prompt work? (They're the same lever.)

## Principle

> **Retrieve positions, not confirmations — and grow the corpus that makes positions possible.** The
> cheapest independent critic is a change in the *shape* of retrieval plus a fresh, blind pair of
> eyes when doubt is warranted. A trained adversary is a real thing, but it's a V2 you earn by first
> proving — on a labeled set, not on engagement vanity — that surfacing dissent changes the action
> when it should and stays quiet when it shouldn't. Build the measurement, then the free move, then
> the paid one — in that order.
