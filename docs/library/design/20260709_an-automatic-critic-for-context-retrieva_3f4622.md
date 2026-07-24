---
akashic_id: art_20260709_an-automatic-critic-for-context-retrieva_3f4622
akashic_sha: 5eda78e4ce5c
status: fossil
type: design
date: 2026-07-09
title: An Automatic Critic for Context Retrieval — grounding the echo chamber
gist: "> Design research for a retrieval critic that surfaces *grounded* context instead of self-confirming > \"nearest\" lessons — so the architectu"
tenant: solo
visibility: fleet
seats: []
category: [recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_an-automatic-critic-for-context-retrieva_3f4622 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# An Automatic Critic for Context Retrieval — grounding the echo chamber

> Design research for a retrieval critic that surfaces *grounded* context instead of self-confirming
> "nearest" lessons — so the architecture actively promotes critical thinking and re-evaluation.
> Grounded in our real recall pipeline (FAITH-1, provenance tags, the Ranker) + the RAG-critique,
> self-correction, debate, and debiasing literature. Written 2026-06-30, for review.

## TL;DR

The danger isn't that recall is *wrong* — it's that recall surfaces what **agrees with where you're
already headed**, hedge-stripped and ranked to the top, and an agent under load reads it as
confirmation. A naive fix ("ask the model to critique the context") **fails or backfires**: LLMs
largely cannot self-correct reasoning without external feedback. So the entire design rests on one
principle:

> **A critic is only worth its independence from the actor.** Self-reflection over shared context is
> just more echo. Ground the critic in the *corpus* and in *structure*, not in the actor's own
> reasoning — and operationalize the single most effective human debiasing move, *"consider the
> opposite,"* by making **retrieval surface dissent, not just support.**

The elegant form: **change the unit of retrieval from "the best supporting lesson" to "the
best-grounded *position* — thesis + its strongest live counter."** Done deterministically and
silently-when-there-is-no-real-counter, this makes a pure self-praise echo *structurally impossible*
whenever the corpus contains a genuine objection — at almost zero cost. An independent LLM critic is
escalated only to adjudicate genuine conflicts on high-stakes actions, so compute is spent exactly
where doubt is warranted.

---

## 1. The problem, precisely (in our pipeline)

Recall today ranks lessons by `(relevance·importance·recency·relationship) × usefulness[0.5–1.5]`
and surfaces the top few. Three properties make it quietly self-confirming:

- **It retrieves by similarity to the *current* action** — so it returns what *resembles what you're
  about to do*, which is exactly the evidence that confirms the plan.
- **`usefulness` rewards agreement/co-occurrence** (the Factor-2 finding) → the most-confirmed
  lessons rank highest.
- **No disconfirming evidence is ever sought.** If a lesson says "X worked" and another says "X
  failed in context Y," only the top-scoring one surfaces. The agent never sees the tension.

This is confirmation bias implemented as a ranking function. FAITH-1 checks that what's surfaced is
*faithful to its source*, and the new provenance tags mark *how verified* it is — but neither asks
the harder question: **"is this the whole picture, or just the agreeable slice of it?"**

## 2. The crux — why the obvious fix fails

The intuitive move is "have the model reflect on the retrieved context." The literature is blunt
that this **does not work** on its own: *Large Language Models Cannot Self-Correct Reasoning Yet* —
intrinsic self-correction (no external feedback) fails to improve reasoning and **often degrades it**;
split into verification / critique-generation / critique-consideration, models do poorly at all
three, and "stacked errors often make the self-critiquing loop perform worse than guessing upfront"
([Huang et al., arXiv 2310.01798](https://arxiv.org/abs/2310.01798)). Gains appear **only when an
external, sound verifier supplies the signal**.

Our own codebase already encodes this skepticism: FAITH-1's docstring rejects LLM-as-judge as
"unreliable (self/position bias)" and judges **deterministically** instead. So the design constraint
is set by both the literature and our own precedent:

> **Independence is the whole game.** Rank the critic's possible groundings from cheapest/strongest to
> most expensive/weakest:
> 1. **Structural / corpus grounding** — the critic cites *other data in the corpus* (a contradicting
>    lesson, an anti-pattern). Independent of the actor's priors by construction. *(deterministic, ~free)*
> 2. **Role independence** — an adversarial prompt that *defaults to refuting*.
> 3. **Context independence** — a fresh instance, blind to the actor's preferred conclusion.
> 4. **Model independence** — a *different* model, to avoid shared blind spots / self-preference.
>
> A same-context, neutrally-prompted self-critique is the **worst** point on this ladder (≈ self-praise).
> Every tier below moves up it.

## 3. What the literature gives us

- **Corrective RAG (CRAG)** — a *lightweight, independent* retrieval **evaluator** grades retrieved
  docs (Correct / Ambiguous / Incorrect) and triggers corrective action (re-retrieve, decompose,
  web-search). Notably the evaluator is a small fine-tuned model, not the generator — cheap and
  independent ([CRAG, DataCamp walkthrough](https://www.datacamp.com/tutorial/corrective-rag-crag)).
- **Self-RAG** — reflection tokens critique retrieval and generation: **ISREL** (is this passage
  relevant?), **ISSUP** (does it actually support the claim?), **ISUSE** (is it useful?)
  ([Self-RAG](https://selfrag.github.io/)). The key framing: *"Self-RAG improves how the model
  reasons over evidence; CRAG improves the quality of the evidence itself — complementary."* → a
  natural two-tier split.
- **Critic-as-independent-role** — Constitutional AI (one model critiques another against principles,
  then revises), actor-critic debate where the critic is *encouraged to reach a different judgment*
  to mirror real debate ([ACC-Debate, arXiv 2411.00053](https://arxiv.org/html/2411.00053v1)).
- **The cognitive-science winner — "consider the opposite."** The most consistently effective
  individual debiasing strategy is *deliberately generating reasons your current belief might be
  wrong*; plus seek-disconfirming-evidence, devil's advocate (assign someone to challenge — "building
  a coherent counter-argument reveals gaps you couldn't see while defending"), and pre-mortem
  ([debiasing techniques](https://fiveable.me/cognitive-psychology/unit-18/debiasing-techniques/study-guide/5ACTqJiW0fu6KJ16)).
  This is the human blueprint for the whole feature.
- **The deterministic mechanism — NLI / stance / contradiction detection.** Stance is computable via
  NLI: treat a lesson as the premise and a candidate counter as the hypothesis; **contradiction** =
  refutes, **entailment** = supports ([contradiction/NLI in RAG, arXiv 2510.03418](https://arxiv.org/html/2510.03418v1)).
  This is how Tier 1 finds the counter without an LLM.

**Skeptic's caveats (this is "not without its costs"):**
- More critics ≠ less bias: multi-agent LLM judging can *amplify* bias and converge sycophantically
  ([Judging with Many Minds, arXiv 2505.19477](https://arxiv.org/pdf/2505.19477)). So don't naively
  stack model-critics; keep them grounded and few.
- LLM judges carry self/position bias (FAITH-1's own reason for going deterministic). The LLM tier
  must earn its place via independence + escalation, never as the default.

## 4. The architecture — tiered, dialectical, cost-bounded

Four tiers, each independent of the actor, each escalating cost only as warranted.

### Tier 0 — Provenance framing *(shipped)*
The `[worked | partial | unverified | anti-pattern · author · advice]` tags. A *passive* critic:
it primes the right skepticism for free. Necessary, not sufficient.

### Tier 1 — Dialectical retrieval *(deterministic, always-on, ~free) — the core move*
Change the **unit of retrieval** from "top-k supporting lessons" to a **position: thesis + its
strongest live counter.** For the top lesson, the critic actively searches the *same corpus* for:

- **A contradiction** — a lesson on the same topic with opposite `success`, a matching `anti_pattern`,
  or a recommendation that conflicts (cheap lexical/embedding opposition now; a small NLI model
  later). Surface it: `counter: <X> (source: …)`.
- **Echo detection** — if the top-k are near-duplicates (one stance), flag *"all retrieved lessons
  share one view — corpus may be one-sided here."*
- **A self-confirmation flag** — if the supporting lesson is self-authored, uncorroborated, and aligns
  with the current trajectory: *"this confirms your current path and is not independently corroborated."*
  (Reuses the Factor-1/2 provenance + corroboration signals.)
- **An applicability delta** — surface the lesson's origin (file / category / age) so the agent judges
  *transfer* instead of assuming it.

Crucially: **if no genuine counter clears a real bar, stay silent on dissent** (never manufacture
false balance — see costs). This is CRAG's "grade the retrieval" idea, turned inward and made
deterministic, with the specific job of *hunting the disconfirmer*. It bakes "consider the opposite"
into the **shape** of retrieval, so an agent literally cannot receive pure self-praise whenever a
real objection exists — at corpus-read cost, no LLM.

### Tier 2 — Independent LLM critic *(escalated, cheap model, async)*
A **separate** critic instance (independence is mandatory per Huang et al.): a *different/cheaper*
model (e.g. Haiku), in a **fresh context blind to the actor's preferred conclusion**, prompted to
**default to refuting** — Self-RAG-style ISREL/ISSUP/ISUSE over the retrieved bundle *plus the
specific action*. It produces the grounded counter-case the deterministic tier can't articulate.

Cost is bounded by a **cheap trigger gate** — run it *only* when: the action is high-stakes /
irreversible, retrieval confidence is low, **Tier 1 found a contradiction worth adjudicating**, or
the topic is known-contested. Plus: **async / non-blocking** (surface as a follow-up; never stall the
action), **cache** critiques per `(lesson, action-context)`, and a hard **budget cap**. For genuinely
irreversible actions it may run blocking-but-advisory.

### Tier 3 — Corpus immune system *(offline, feeds back)*
Critiques are **first-class artifacts**: a detected contradiction triggers a **supersession / merge
review** (directly attacking Factor 8, corpus rot) — the critic doesn't just inform the moment, it
*heals the corpus* over time. Track whether critiques were heeded and right as a meta-signal — but
**carefully**, so we don't recreate the Factor-2 sycophancy loop on the critic (calibrate; never
reward "finds problems").

---

## 5. Costs and honest trade-offs

The user named the key constraint: *this is not without its costs.* The honest ledger:

| Cost / risk | Why it bites | Mitigation |
|---|---|---|
| Latency / tokens | A critic per recall is expensive | Tiering: Tier 0/1 are deterministic & ~free; Tier 2 is trigger-gated, cheap-model, async, cached |
| **False balance / both-sidesism** | A manufactured weak objection to a solid lesson is noise | Surface a counter only when it clears a real bar (true contradiction / anti-pattern); else **silent** |
| Self-critique degradation | Shared-context self-reflection *worsens* reasoning (Huang) | **Never** rely on same-context introspection; enforce the independence ladder |
| Critic sycophancy / multi-critic bias amplification | Stacked model-judges can converge & amplify (2505.19477) | Keep critics few + corpus-grounded; deterministic-first; meta-monitor |
| **Decision paralysis / over-doubt** | A critic that challenges *everything* slows and demoralizes the actor | Critic **informs, doesn't veto** (except hard FAITH-style fails); proportional to stakes; goal is *calibrated* re-evaluation, not universal doubt |
| Crying wolf | Frequent low-value critiques get tuned out | Calibrate; surface only high-signal counters; let the agent mark a critique unhelpful (carefully) |
| Context-rot | Extra text re-pollutes the window (the friction-audit guardrail) | **Silent when no real counter; small when it speaks** |

The unifying guardrail, shared with the friction audit and the epistemic-risk register:
**reduce friction / add a critic *without* adding noise — silent-when-empty, small-when-not, and
escalate cost only toward genuine doubt.**

---

## 6. How it composes with what already exists

- **FAITH-1** is the precedent and the seam: a deterministic, no-LLM critic over surfaced text. The
  retrieval critic is its sibling — FAITH-1 asks *"is this faithful to its source?"*; the new critic
  asks *"is this the whole picture, or just the agreeable slice?"* Both deterministic-first, fail-soft.
- **Provenance tags** (shipped) are Tier 0.
- **"Recommend less, retrieve more"** (in-flight) is the perfect complement: when the critic raises a
  counter, the *cheap one-hop pull to the full record* lets the agent actually adjudicate it instead
  of taking either side on faith.
- **Independent corroboration** (Factor-1 M4 / Factor-2 M2.3) is the *positive* mirror of this
  critic's *negative* grounding: a claim earns trust by independent confirmation; the critic surfaces
  independent *dis*confirmation. Same principle, both signs.

## 7. A minimal first slice + open questions

**Smallest shippable proof:** Tier 1 contradiction surfacing — for the top recalled lesson, scan the
corpus for an opposite-`success` / `anti_pattern` / conflicting-recommendation lesson on the same
tokens; if one clears a bar, append one line: `counter: <text> (source: …)`; else stay silent.
Deterministic, fail-soft, no hot-path LLM, fully in the FAITH-1 grain. Measure: does surfacing a
counter change the action when it should (and stay quiet when there's nothing real)?

**Open questions for review:**
- Where's the bar for "a real counter" vs. false balance? (Start strict; loosen with evidence.)
- Trigger policy for Tier 2 — which actions count as "high-stakes" in this repo? (irreversible
  git ops, schema/contract edits, deletes?)
- Should the critic ever *block*, or always *advise*? (Proposed: advise, except hard FAITH fails.)
- How do we keep Tier 3's meta-signal from becoming a new Goodhart target?

---

## Principle

> **Retrieve positions, not confirmations.** A memory that only returns what agrees with the current
> plan is an echo chamber with a ranking function. Make the critic *independent of the actor* —
> grounded in the corpus, deterministic first, adversarial and blind when it must use a model — and
> change the unit of retrieval to *thesis + its strongest live counter*. Surface dissent only when
> it's real, escalate compute only toward genuine doubt, and let the cheap pull-to-truth settle it.
> The architecture should make *considering the opposite* the path of least resistance.
