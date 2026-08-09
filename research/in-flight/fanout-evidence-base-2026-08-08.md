# What actually changes an AI's behaviour — the evidence base under our fan-outs

Status: current · Type: reference · Arc: agent-ergonomics
Author: claude#f9d12d26, 2026-08-08, at Daniil's ask: *"I want our procedures to reflect what is
true and actually works best."*

**This is the EVIDENCE layer, not a playbook.** Two playbooks already exist and both stand:

- `20260807_fanout-playbook_23cec6` — the doors (`--with`, `--bg`, `--peer`, `discover`) and
  seven laws of asking, each with a receipt.
- `multiview-playbook-2026-08-07` — how to compose branches; the view catalogue.

Those say *how to do it*. This says *why, and how confident we are*. When a playbook and this
document disagree about a mechanism, this one carries the citation and the playbook should be
corrected.

Claims are tagged: **[M]** measured on this project, receipt named · **[R]** external research,
source named · **[C]** contested or recently changed · **[X]** believed and NOT established.

---

## THE PATTERN UNDERNEATH EVERYTHING

**[R][M] Almost every prompt variable that works is an ATTENTION control, not a CAPABILITY
control.**

You are not making the model smarter or dumber. You are choosing what it looks at, what shape it
must answer in, and what it is permitted to say. That single fact predicts most of what follows:
why grounding fixes facts but not reasoning, why personas barely register, and why one clause can
outperform a paragraph of instruction.

**The operational corollary, which is the most useful sentence in this document:**

> **Different evidence beats different questions, and different questions beat different personas.**

Two personas on one model share every blind spot, because the errors live in the model and not in
the costume. Two positions holding genuinely different evidence do not. So a "newcomer" branch
should not be *asked to pretend* — it should be *given only what a newcomer can see*. One is a
request; the other is a fact it cannot get around.

---

## TIER 1 — the strongest levers

### What the helper can SEE
**[M]** Grounding fixes FACTUAL error almost completely and fixes REASONING error not at all.
Five factual lookups with the file attached: **5/5 correct with line citations**. One judgement
question, same file, same model: **confidently wrong, with real and accurate citations** — it
failed by equivocating on a single word (T207).

> **The tell that you are in the danger zone: your question contains should / better / more /
> fewer.** Ask what the code DOES; draw the conclusion yourself.

### Whether that evidence is COMPLETE
**[M]** A truncated source does not produce a hedged answer. It produces a confident answer about
the *window*, phrased as though it were about the whole. Measured 2026-08-08: a file silently cut
at **40,000 of 49,529 chars**; every branch answered fluently about a region that excluded the
subject under study. Two paid runs lost before anyone noticed, and the correct warning existed
the whole time in a field nobody read (fixed as T242).

### WHERE in the context it sits
**[R]** Attention is U-shaped — beginning and end are used well, the middle badly, with **>30%
accuracy degradation** for material in the middle, replicated across model families.
**[C] But a 2026 replication found the effect not straightforwardly reproducible in real
retrieval pipelines** — position interacts strongly with retrieval quality and model choice
(*Lost in the Evidence?*, arXiv 2605.27105). **Put the important thing first or last, and verify
on our own setup rather than trusting the rule.**

### Whether the QUESTION IS DECOMPOSED
**[M] The strongest single effect we have measured.** The same model, same file, got a normative
question WRONG asked directly and RIGHT asked as *"if the list is non-empty does it return or
block? if empty, which? therefore?"* **The decomposition did the work, not the file access**
(T207).

### Whether YOUR OWN BELIEF is in the prompt
**[M]** If your reasoning is visible in the payload, the answer reflects it back, and agreement
then measures nothing. Stripping a docstring that contained the entire design argument is what
let a branch *derive* the design independently — with it left in, that branch is a mirror and
its agreement reads as confirmation.

---

## TIER 2 — real, and cheap per word

### What KIND of thing you demand back
**[M]** Branches returning the same *kind* of output must be merged by the reader, and merging at
the junction is where fan cost actually lives. Five questions all returning "problems found" cost
**$0.065** and changed nothing; three views returning *different kinds* — facts, an analogy, a
divergence — cost **$0.0155** and found a live defect.

> **Vary the OUTPUT TYPE across branches, not just the question.**

### Single clauses that do disproportionate work
**[M]** All measured 2026-08-07/08. Note what they have in common: every one is a **permission or
a ranking instruction. Not one is a role assignment.**

| clause | what it produced |
|---|---|
| *"rank by how SILENT the failure is"* | turned a bug list into a list of things that would break invisibly later — the strongest new view of that run |
| *"which of these would happen by ACCIDENT?"* | separated real risk from theatre in a system that has no adversary |
| *"give the cheapest thing that would prove you WRONG"* | 3 of 7 findings settled in ONE command each, including one that refuted itself |
| *"saying NOT EXPLOITABLE is a real answer"* | a branch used it, and that abstention became the control that validated a fix |
| *"say what your prevention COSTS an honest player"* | catches the anti-gaming rule that is itself an exploit |

### Worked examples
**[C] Changed since 2024.** On current strong models, chain-of-thought exemplars *"do not improve
reasoning performance compared to Zero-Shot CoT, with their primary function being to align output
format with human expectations"* (arXiv 2506.14641). Treat examples as **format control**, not a
reasoning boost. They also remain sensitive to which examples are chosen and in what ORDER.

---

## TIER 3 — mostly theatre

### Personas and role assignment
**[R]** Across **162 roles and 2,410 factual questions in four model families**: no improvement,
sometimes a small decline (Zheng et al., EMNLP Findings 2024). A newer study finds the aggregate
hides a real effect — persona prompting **increases expertise depth while reducing clarity**
(arXiv 2605.29420). So it changes voice and emphasis, not accuracy.

**[M] Our own version, independently:** hats differed sharply in precision (`jester` 3/3,
`historian` 1/3) and marginal contribution pointed the OPPOSITE way from precision. And from an
earlier multi-seat round: *"the seats' uniqueness turned out to be POSITION not personality —
none of which can be assigned, only noticed and routed to"*
(`route_to_position_not_personality`).

### Urgency, flattery, stakes
**[C]** Early positive results replicate poorly. Not harmful; simply not where leverage is.

---

## HOW TO RETIRE A BRANCH, once you have several

**[M] Marginal contribution and precision point in OPPOSITE directions**, so a branch must be
retired on BOTH numbers or not at all. `jester` had zero marginal contribution and 3/3 precision;
`historian` was pivotal and wrong (1/3). Deleting on the ablation number alone would have removed
the best branch to keep the worst.

**[M] Build the truth set BEFORE the instrument.** The stated blindness of that ablation, verbatim:
*"I built seven hats and then discovered I could only grade them on three examples."*

---

## WHAT THIS DOCUMENT DOES NOT ESTABLISH

- **[X]** That any of the Tier-2 clauses generalise beyond this repo and this model. Each is n=1
  to n=3 on our own work.
- **[X]** Whether our measured effects survive a different model. That is T229's open question.
- Every **[M]** receipt is from a five-day window on one project, by one seat, mostly unreviewed
  by a second reader.
- The external results are cited as reported; none have been replicated by us.

**Sources.** Zheng et al., *When "A Helpful Assistant" Is Not Really Helpful*, EMNLP Findings 2024
· *When Does Persona Prompting Actually Help?*, arXiv 2605.29420 · *Lost in the Evidence?*,
arXiv 2605.27105 · *Revisiting Chain-of-Thought Prompting*, arXiv 2506.14641.
