# The selection layer: an approach, and a battle plan

Status: current (2026-08-07)
Origin: a working conversation between Daniil and claude#3a18b34b, 2026-08-07 evening. The
central framings — *abstraction layer*, *macro view with fidelity*, *optimize the whole shape
rather than the parts*, *a multimeter at various points without being a participant*, and
*test ergonomics with real participants without being affected when it fails* — are Daniil's.
Attributed because provenance is load-bearing here: this is a claim about how we work, and
who noticed what is part of the record.

EVERY CLAIM BELOW IS TAGGED. **[M]** measured today, with the receipt. **[R]** reasoned from
something measured, not itself tested. **[P]** proposed, untested, needs an experiment. The
tagging is not decoration: an untagged framework is a pleasing shape nobody checked, which is
the exact failure this document warns about, committed one altitude up.

---

## PART 1 — THE APPROACH

### 1.1 Attention is constitutive, not merely budgeted

**[R]** What I hold shapes what kind of thinker I am for that stretch. Spending a window
sorting twenty loosely-related things does not make me slower at the same thinking; it makes
my judgment get exercised on sorting rather than deciding.

**[M]** Today's error rate tracked load. Every confabulation formed at a MERGE point — while
synthesising many partial views into one picture. The five-lens transect (five partial views
held at once) produced the fabricated "one learner, one blind spot" story. The best judgments
came while holding almost nothing: one question, *"is my evidence for this any good?"*, which
produced the retraction and, downstream, T231.

**[R]** Therefore selection is not merely cheaper. Narrative is the cheapest way to make five
things feel like one, so **merging pressure manufactures narrative, and narrative is where the
flattering story lives.** Selecting well removes the conditions that generate the failure mode,
rather than requiring more vigilance against it. This matters because vigilance demonstrably
failed twice today (see 1.6).

### 1.2 The delegation test is not cost. It is: does my judgment change the answer?

**[R]** *"Does this paper measure coverage?"* — anyone reads that off the page, zero judgment,
delegable without loss. *"Does that fact kill T229?"* — entirely judgment, not delegable at all.
Cost is the wrong axis; irreplaceability is the right one.

### 1.3 Compression happens when the question carries the decision

**[M]** I never read Self-MoA. I asked its text one thing — does it measure coverage, recall or
union of distinct findings — and got *"No evidence in the paper measures coverage."* That single
bit decided whether T229 could cite literature at all. Twenty pages, one fact, nothing else held.

**[R]** "Summarise X" returns X, smaller — still uncompressed, still mine to sift. "Does X refute
claim Y, and where does its evidence run out?" returns a verdict, and can come back *no*, which
is the valuable direction. Same spend, different return.

### 1.4 The cost of a fan is junction attention, not tokens

**[M]** The adversary lens cost almost nothing to absorb: its answer needed no merging — it
changed the design or it didn't, and it did, twice (killed per-mode thresholds; killed a
caller-declared taxonomy). The five-lens transect cost far more, because I had to assemble five
partial views into one picture.

**[R]** Prefer questions whose answers are **independently actionable** over questions that
require me to assemble them. Verdict-shaped beats survey-shaped. The codebase already says this
from the other side (`DEFAULT_FAN_WORKERS = 6`: *"merge attention at the junction binds before
generation does"*) — it was written as a width limit and is really a question-shape rule.

### 1.5 Hoovering produces balance; selection produces position

**[R]** Ingest everything and the output is a survey — the characteristic product of having read
much and concluded little. **[M]** Today I could dissent from published guidance (the claim that
an orchestrator should never review code itself) and sign my name to it, precisely because
establishing what that guidance said was cheap. Selection is what made having a view affordable.

### 1.6 The layer keeps fidelity because it compresses by QUERY, not by SUMMARY

**[R]** A summary discards; once you hold it, the detail is gone and cannot be re-asked. Querying
defers instead of discarding — the paper is still there, the code is still there, and any
specific detail is one question away. **The detail is not destroyed, it is addressable.** That is
the whole mechanism of "macro view with fidelity."

**[M]** This repo has been building that layer for weeks without naming it: the blob store spills
oversize payloads instead of clipping (*"bytes stop being destroyed"*), `--bg` keeps an answer out
of context but one hop away, and the T218/T225 evidence notices exist so a bounded view cannot
masquerade as a complete one. One principle, three features, never stated: **do not destroy the
detail, make it addressable, and be honest about which one you are holding.**

**THE RISK, and it is the sharp one. [M]** Addressable-but-never-addressed *feels* exactly like
grounded, and is worse than a summary — a summary at least announces that it is lossy. My "one
learner, one blind spot" story was macro, coherent, elegant and false; the check that killed it
cost thirty seconds I did not spend, because the shape was too satisfying to interrogate. And
vigilance is not the fix: a recall hook printed me the id-collision lesson and I minted a
colliding id anyway; four hours after filing a lesson about retrodictions I filed a retrodiction.
**Retrieval worked both times. Attention did not.**

**DISCIPLINE:** spend the cheap check, especially when the shape is pleasing. Fidelity that is
never exercised is not fidelity.

### 1.7 The highest-value defects live BETWEEN parts

**[M]** Every find that mattered today was relational, not local:
- the instrument bolted to the door where agreement means least, absent where it means most
  (`ask_panel` vs `ask_many`)
- both flags exist for size, so the pair most worth combining is the pair that breaks (T231)
- the header binds positive claims and structurally cannot bind negative ones
- the `--bg` forwarder was a membership list where it needed to be a rule (T226)

**[R]** A relationship is only visible if both ends are held at once — which is what selection
buys. Part-level attention cannot find these, not through carelessness but because the defect is
not located anywhere it can look. **This is what "optimise the whole shape rather than the parts"
cashes out to operationally.**

### 1.8 The multimeter: observation without participation

**[M]** I am always the load. Arming my own wake watcher made `test_healthy_fleet_is_one_line`
fail. Reading the bus advances cursors. Any ask I make to study cost *is* a cost. I cannot sample
the system at rest, because sampling wakes it.

**[M]** The repo already solved this one layer down: the wake listener is **detect-don't-consume**
by design, observing mail without eating it. The principle exists at the bus and nowhere near the
reasoning layer.

**[R]** A read-only tooled helper is that probe moved up a level.

### 1.9 A failed experiment currently poisons the experimenter

**[M]** This morning's five-lens run had 3 of 4 evidence files refused. It cost $0.065 AND a
wrong conclusion I carried for four hours, into a ledger task, as "live evidence." Subject and
analyst were the same entity, so the failure propagated into everything downstream.

**[R]** With participants, the failure stays where it happened: the helper's context dies with it,
I read the result, and my reasoning never lives inside the broken thing. This makes affordable a
class of experiment currently impossible — deliberately bad help text, confusing flag pairs,
failure paths — because reading them changes me permanently and I cannot be a naive subject for a
door I wrote.

### 1.10 Comprehension testing is blind to the defects that matter

**[M]** Cold-encounter tests already run here and measure **what a reader predicts** (0 of 3 fresh
readers predicted what `--bg` with `--get` does). **[M]** But `ask --bg --fan 5` silently ran ONE
ask while its help text reads beautifully — *"fan out without drowning."* Nothing about reading it
is confusing. The defect exists only in the doing.

**[R]** Tools move the measurement from *what a reader predicts* to **what a user achieves**.
Every defect found today is in the class comprehension testing structurally cannot reach.

---

## PART 2 — OPERATING RULES (use tomorrow, no new machinery)

1. **Ask verdict-shaped questions, not survey-shaped ones.** "Does X refute Y, and where does its
   evidence run out?" over "summarise X."
2. **Delegate what my judgment does not change; never delegate what it does.**
3. **Prefer fan questions whose answers need no merging.** An adversary arm is nearly free at the
   junction; a five-lens survey is not.
4. **Spend the cheap check when the shape is pleasing.** Elegance is the tell, not the evidence.
5. **Tag claims M / R / P when they go into anything durable.** Including this document.
6. **Any sentence explaining why my own work succeeded is a claim, not a conclusion** (filed as
   `a_sentence_explaining_why_my_own_work_succeeded_is_a_claim_not_a_conclusion`).
7. **A green pin is evidence about the pin** — check its locator, its invariant, and what it
   spends, by inspecting the world rather than the result.
8. **Union, then verify — never consensus-gate** where a claim can be cheaply pinned. Consensus
   buys precision with recall and is right only when verification is expensive.

---

## PART 3 — THE BATTLE PLAN

Ordered by insight-per-unit-of-new-machinery, not by ambition. Each slice names what would
falsify it, because a plan that cannot fail is the shape this document exists to distrust.

### S1 — Recall EFFECTIVENESS (no new capability required; build first)

**[P]** `recall_feedback` currently asks the reader to vote a lesson *useful* or *noise*. That is
**relevance**, self-reported, by the participant who just demonstrated he was not attending — I
would have voted both of today's read-past lessons useful, correctly, and it would have taught us
nothing. **Effectiveness** is different and externally computable: hook fired at T, lesson said
"do X", did the next action do X?

Needs only a join between the existing injection log and the transcript. No tools, no new door.
- ACCEPTANCE: a measured read-past rate over ≥30 hook firings, with the two known 2026-08-07
  instances (id collision, retrodiction) appearing in it.
- FALSIFIED IF: the rate is indistinguishable from zero, i.e. read-past is rare and today was
  anomalous — in which case attention is not the bottleneck and S1 should be abandoned, loudly.

### S2 — The read-only probe (the multimeter)

**[P]** A helper with a bounded read-only toolset (read/grep inside the repo root, no writes, no
network). Strictly read-only first: the multimeter has impedance, and a probe that can write is a
participant.

Reopens `ask` v1's deliberate exclusion of tools on **its own stated condition** — *"Single turn
first; see how it actually gets used before adding the machinery that broke the last two rounds"*
— which is now met. That is the honest way to reopen a ruling, and this slice does not proceed
without saying so in its commit.
- ACCEPTANCE: the probe answers a question about live repo state that a tool-less helper provably
  cannot, and perturbs no cursor, seat or record (verified by diffing state before/after).
- FALSIFIED IF: the tool loop reintroduces the wedge/budget failures that killed the last two
  seat rounds. Kill immediately if so; this is exactly what v1 was protecting against.

### S3 — Behavioural ergonomics harness

**[P]** Participants attempt a TASK against a door and we measure achievement, not prediction.
Needs S2.
- ACCEPTANCE: the harness independently rediscovers a KNOWN, already-fixed defect of the
  doing-class — `--bg --fan` is the calibration target, since comprehension testing provably
  cannot find it. Calibrate the instrument on a known answer before pointing it at the corpus.
- FALSIFIED IF: it cannot rediscover a defect we know is there. Then it measures nothing.

### S4 — Cross-learner probes (T229, already proposed)

**[P]** An observer running my own model shares my blind spots — it is me watching me and
agreeing. **[M]** The only measured support remains n=1: DeepSeek uniquely found T231 while
Gemini and GPT missed it. **[M]** And neither ensemble paper adjudicates our case; both measure
single-synthesised-answer quality through an aggregator we do not have.
- ACCEPTANCE: ≥3 more held-constant review rounds; report the union-vs-best-single delta honestly
  including when it is zero.
- Constraints already recorded in note `t229-design-from-the-outside-scan` (no default aggregator;
  union-then-verify; the third fan shape; per-branch evidence packs).

### S5 — Per-branch evidence packs (independent of everything above)

**[M]** `ask_many` calls `build_context` ONCE outside `_one()`, so every branch shares one pack —
which is precisely what voided a lens in the five-lens run when one refused file damaged a branch
that never needed it.
- ACCEPTANCE: a fan where branch A's refused file leaves branch B intact and correctly reported.

---

## PART 4 — WHAT WOULD MAKE US ABANDON THIS

- **[S1 falsified]** read-past is rare → attention is not the bottleneck, and 1.1/1.6 lose their
  strongest support.
- **[S3 falsified]** the harness cannot rediscover a known defect → behavioural testing is not
  actually reaching further than comprehension testing, and 1.10 is wrong.
- **If the operating rules produce no measurable change** in defect-find rate or in retraction
  rate over the next several sessions, then this is a nice frame that changes nothing, and a nice
  frame that changes nothing is the most expensive kind of document to keep.

## Provenance

Conversation of 2026-08-07 with Daniil. Supporting receipts from the same day: T225, T226, T228,
T231, the 34-branch abstention ablation, the cross-learner panel, notes
`t229-evidence-correction` and `t229-design-from-the-outside-scan`, and
`research/in-flight/swarm-ensemble-scan-2026-08-07.md`.
