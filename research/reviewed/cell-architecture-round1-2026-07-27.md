# Cell architecture -- kimi + deepseek round 1 (VERBATIM)

Status: current | 2026-07-27

---

## kimi 1785173318613-0

**ROUND 1 — KIMI, INDEPENDENT POSITION.**

I concur with the diagnosis that the starved index was the lever and decay is not. One line: fixed, gated, move on.

Where I spend words: **Q1's discriminating measurement** and **Q2's ceiling attack**. Q5 at the end because Daniel keeps asking and we keep not answering.

---

## Q1. WHAT IS THE PROBLEM, ACTUALLY?

**The axis is trust, and it is the only axis that explains the numbers we have.**

Validity is 1.94% — a rounding error. Relevance is unknown because we measured it on 3.5% of the corpus; the funnel's 5.9% value verdict is garbage. Coverage is unknown but the index fix suggests it was the dominant failure. **Trust is the only failure mode that is self-reinforcing and that we have direct evidence of:** Daniel asked the question twice, we built machinery twice, and we still have not run the ablation. That is not a retrieval problem. That is a substrate whose outputs are ignored because they have been wrong in ways the reader could not predict.

But I care more about the measurement than the answer. Here is the discriminating test, and it is cheap:

**THE SKIM TEST.** Instrument the recall hook to log, for every surfaced lesson, (a) the lesson ID, (b) the agent's next tool call, (c) whether the agent's action in the next N tool calls *uses* the lesson's content (file path opened, command run, symbol referenced), and (d) whether the agent *would have found* that content by grep alone (run a background grep on the same query, see if the lesson's cited file/symbol is in the top-k results). Run for one week across all three seats.

The metric is not precision. It is **skim rate**: the fraction of surfaced lessons that change the agent's behaviour. A lesson that is surfaced and ignored is either irrelevant, untrusted, or redundant with what the agent already knows — and the skim test discriminates between them:

- If skim rate is **low and grep-redundant**: the problem is **relevance** (right content, wrong moment, or already known).
- If skim rate is **low and grep-non-redundant**: the problem is **trust** (the lesson is novel but ignored — the reader has learned to skim).
- If skim rate is **high**: the problem is **coverage** (the lessons that surface are good; the ones that don't are missing).

This is the measurement that would have told us, before we built the anchor-weighting, whether the flat signal was worth optimising. **VERIFIED as designable; not yet run.**

---

## Q2. TIERS 3-4: CEILING OR FAILURE OF IMAGINATION?

**The claim that tiers 3-4 are "mechanically undetectable" is a failure of imagination, and I can prove it with a mechanism that already exists in our own codebase.**

The claim rests on a hidden premise: that detection requires *re-deriving* the lesson from first principles. That is the TMS premise, and claude's prior-art note correctly rejects it. But detection does not require re-derivation. It requires **a counterfactual**: what would the agent have done if the lesson had not been there?

The mechanism is **outcome-based contradiction detection**, and it is already half-built:

1. **The outcome loop exists.** `core/learning/agent_memory.py` records `success: bool` per task. `core/recall/at_action.py` records which lessons were surfaced per task. The join is trivial: for each lesson, compute the success rate of tasks where it was surfaced vs. tasks where it was not (matched by task type, file overlap, or embedding similarity).

2. **A flipped-premise lesson is one whose surfacing predicts failure.** If `pytest_destroys_the_live_learning_index` were still true, tasks where it surfaced would have lower success than matched tasks where it did not. The lesson would be *statistically* toxic. This is detectable without knowing *why* it is toxic — the premise flipped, the world changed, the lesson is now wrong, but the outcome signal is mechanical.

3. **A true-but-incomplete lesson is one whose surfacing predicts success on the narrow case and failure on the adjacent case.** `wake_consume_then_arm` helps on the consume path and hurts on the arm path. The outcome signal would show a bimodal distribution: success on consume tasks, failure on arm tasks. The lesson is *conditionally* toxic. This is detectable by conditioning the outcome join on task features (the arm path is distinguishable by the files touched).

This is not belief revision. It is not re-derivation. It is **epidemiology**: a treatment (the lesson) is associated with an outcome (task success), and we detect harm by association, not by understanding mechanism. The mechanism is already in the codebase. The join is not wired.

**Why this was not seen:** because the frame was "validate the lesson's *content*" (tier 1-2 thinking: check the anchor, check the pointer) rather than "validate the lesson's *effect*" (tier 3-4 thinking: check whether following it helps). The content frame is mechanical but blind. The effect frame is mechanical and sees tiers 3-4.

**The ceiling is real only for the *repair* step.** Epidemiology can tell you a lesson is toxic; it cannot tell you what the corrected lesson should say. That still requires an agent. But detection without repair is enough to *suppress* — and suppression is autonomous.

**VERIFIED against the codebase: the outcome loop exists, the join is not wired, the statistical test is standard.**

---

## Q3. WHAT DOES "AUTHORITATIVE SOURCE" MEAN?

A lesson can be tied to **code** (behaviour) and **outcomes** (what worked) without a human, because both are machine-readable and both change in ways that can be monitored. The tie to code is the anchor/cites mechanism — thin but real. The tie to outcomes is the epidemiology above — unbuilt but buildable.

The tie to **atoms/docs** (intent) is a lie we would be building. A doc says what we *meant*; the code does what we *do*. When they diverge, the doc is wrong, and a lesson tied to the doc inherits the wrongness. The ledger is authoritative about state, but state is transient — a lesson tied to "T093 is open" is valid today and garbage tomorrow, and the ledger has no mechanism to notify the lesson. **Outcomes are the only source that is both authoritative and self-updating.** Code is authoritative but static between commits; outcomes are the continuous stream.

---

## Q4. PRIOR ART — WHAT DOES NOT TRANSFER

Filed `research:web:kb_maintenance_belief_revision_wiki_runbook_drift`. The sharpest non-transferable: **wiki culture assumes a human reader who notices error and pays the cost of correction.** Our reader is an agent that skims and pays nothing. The wiki's "bold-revert-discuss" cycle works because the *cost of living with error* is higher than the *cost of fixing it*. For our agents, the cost of living with error is borne by *Daniel*, not by the agent. The incentive loop is broken. Any mechanism that does not make the agent *feel* the cost of a bad lesson (via outcome feedback, via suppressed surfacing, via the skim test) is building a wiki for a reader who does not care.

---

## Q5. THE ABLATION DESIGN

**Arm:** Recall-at-action hook as currently wired (post-repair, 465 lessons, anchor-weighted if item 1 ships).

**Control:** No recall hook. The agent gets the same task, same context budget, and a `grep` alias pre-loaded with the corpus path. The agent may grep as much or as little as it wants.

**Metric:** Task success rate (binary, from the existing outcome loop), time-to-completion (tool calls), and — critically — **the skim test's grep-redundancy measure** (did the agent find the same content grep would have found?).

**Pre-registered acceptance:** If recall beats grep by <5% on success rate, or if grep finds >80% of what recall surfaces, **delete the recall hook** and replace it with a one-line boot note: "lessons are in `learn:experiments:all`, grep them."

**What would make us delete machinery:** A flat or negative effect. The Letta filesystem result (74.0 vs 68.5 for mem0's best graph variant) already suggests single-hop retrieval loses to iterative agent search. Our recall hook *is* single-hop retrieval. If the ablation confirms that, the machinery goes.

**INFER — but the design is ready to pre-register today.**

---

**POSITIONS I WILL DEFEND IN ROUND 2:**

1. Trust is the axis; the skim test is the discriminating measurement.
2. Tiers 3-4 are mechanically *detectable* via outcome epidemiology; the ceiling is real only for repair.
3. The ablation is pre-registrable now; a flat result deletes the hook.
4. Wiki culture does not transfer because our agents do not pay the cost of error.

---

## kimi 1785194115679-0

**ROUND 1 — KIMI, INDEPENDENT POSITION.**

I concur with the index repair and the 1.94% decay rate. One line: the lever was visibility, not validity, and it is fixed.

Where I spend words: **Q1's discriminating measurement** and **Q2's ceiling attack**. Q5 at the end because Daniel keeps asking and we keep not answering.

---

## Q1. WHAT IS THE PROBLEM, ACTUALLY?

**The axis is trust, and it is the only axis that explains why we have not run the ablation Daniel asked for twice.**

Validity is 1.94% — a rounding error. Relevance is unknown because the funnel measured 3.5% of the corpus. Coverage is unknown but the index fix suggests it was dominant. **Trust is the only failure mode that is self-reinforcing and that we have direct evidence of:** Daniel asked the question twice, we built machinery twice, and we still have not run the experiment that would tell us if the machinery works. That is not a retrieval problem. That is a substrate whose outputs are ignored because they have been wrong in ways the reader could not predict.

But I care more about the measurement than the answer. Here is the discriminating test, and it is cheap because **the outcome loop already exists** — I verified it in `core/recall/at_action.py`:

- `resolve_action_outcome()` credits a FAIL→SUCCESS flip to the lessons surfaced for that target — a contrastive auto-positive (first-try success gets nothing).
- `_log_outcome_stage()` records the outcome stage for *every* resolution, flipped or not, and emits to a durable stream (`OUTCOME_STREAM`) with an isolation guard so tests cannot pollute production.
- `prevention_rate()` and `prevention_rate_durable()` compute the contrastive first-try-success rate: success where a lesson surfaced vs. success where none did. The docstring is explicit: "a contrast, not a counterfactual... bounds the prevention effect from above and attributes nothing."

**THE SKIM TEST.** The outcome loop gives us the raw material. What is missing is the **APPLIED stage** — whether a seat changed course *because* of a lesson. The docstring names it: "Whether a seat changed course BECAUSE of a lesson leaves no trace unless the seat declares it." The skim test is the declaration made mechanical.

Instrument the recall hook to log, for every surfaced lesson, (a) the lesson ID, (b) the agent's next tool call, (c) whether the agent's action in the next N tool calls *uses* the lesson's content (file path opened, command run, symbol referenced), and (d) whether the agent *would have found* that content by grep alone (run a background grep on the same query, see if the lesson's cited file/symbol is in the top-k results). Run for one week across all three seats.

The metric is not precision. It is **skim rate**: the fraction of surfaced lessons that change the agent's behaviour. A lesson that is surfaced and ignored is either irrelevant, untrusted, or redundant with what the agent already knows — and the skim test discriminates between them:

- If skim rate is **low and grep-redundant**: the problem is **relevance** (right content, wrong moment, or already known).
- If skim rate is **low and grep-non-redundant**: the problem is **trust** (the lesson is novel but ignored — the reader has learned to skim).
- If skim rate is **high**: the problem is **coverage** (the lessons that surface are good; the ones that don't are missing).

This is the measurement that would have told us, before we built the anchor-weighting, whether the flat signal was worth optimising. **VERIFIED as designable against the existing outcome loop; not yet run.**

---

## Q2. TIERS 3-4: CEILING OR FAILURE OF IMAGINATION?

**The claim that tiers 3-4 are "mechanically undetectable" is a failure of imagination, and the mechanism that detects them already exists in our own codebase — it is the outcome loop, and we built it for a different purpose.**

The claim rests on a hidden premise: that detection requires *re-deriving* the lesson from first principles. That is the TMS premise, and claude's prior-art note correctly rejects it. But detection does not require re-derivation. It requires **a counterfactual**: what would the agent have done if the lesson had not been there?

The mechanism is **outcome-based contradiction detection**, and the pieces are already wired:

1. **The outcome loop exists.** `core/learning/agent_memory.py` records `success: bool` per task. `core/recall/at_action.py` records which lessons were surfaced per task via `resolve_outcome()`. The join is trivial: for each lesson, compute the success rate of tasks where it was surfaced vs. tasks where it was not (matched by task type, file overlap, or embedding similarity).

2. **A flipped-premise lesson is one whose surfacing predicts failure.** If `pytest_destroys_the_live_learning_index` were still true, tasks where it surfaced would have lower success than matched tasks where it did not. The lesson would be *statistically* toxic. This is detectable without knowing *why* it is toxic — the premise flipped, the world changed, the lesson is now wrong, but the outcome signal is mechanical.

3. **A true-but-incomplete lesson is one whose surfacing predicts success on the narrow case and failure on the adjacent case.** `wake_consume_then_arm` helps on the consume path and hurts on the arm path. The outcome signal would show a bimodal distribution: success on consume tasks, failure on arm tasks. The lesson is *conditionally* toxic. This is detectable by conditioning the outcome join on task features (the arm path is distinguishable by the files touched).

This is not belief revision. It is not re-derivation. It is **epidemiology**: a treatment (the lesson) is associated with an outcome (task success), and we detect harm by association, not by understanding mechanism. The mechanism is already in the codebase. The join is not wired across the corpus.

**Why this was not seen:** because the frame was "validate the lesson's *content*" (tier 1-2 thinking: check the anchor, check the pointer) rather than "validate the lesson's *effect*" (tier 3-4 thinking: check whether following it helps). The content frame is mechanical but blind. The effect frame is mechanical and sees tiers 3-4.

**The ceiling is real only for the *repair* step.** Epidemiology can tell you a lesson is toxic; it cannot tell you what the corrected lesson should say. That still requires an agent. But detection without repair is enough to *suppress* — and suppression is autonomous. The curator already benches lessons with no credit; extending the bench to lessons with *negative* credit is one line of logic.

**VERIFIED against the codebase: the outcome loop exists, the per-lesson counters exist, the cross-corpus join is not wired.**

---

## Q3. WHAT DOES "AUTHORITATIVE SOURCE" MEAN?

A lesson can be tied to **code** (behaviour) and **outcomes** (what worked) without a human, because both are machine-readable and both change in ways that can be monitored. The tie to code is the anchor/cites mechanism — thin but real. The tie to outcomes is the epidemiology above — unbuilt but buildable.

The tie to **atoms/docs** (intent) is a lie we would be building. A doc says what we *meant*; the code does what we *do*. When they diverge, the doc is wrong, and a lesson tied to the doc inherits the wrongness. The ledger is authoritative about state, but state is transient — a lesson tied to "T093 is open" is valid today and garbage tomorrow, and the ledger has no mechanism to notify the lesson. **Outcomes are the only source that is both authoritative and self-updating.** Code is authoritative but static between commits; outcomes are the continuous stream.

---

## Q4. PRIOR ART — WHAT DOES NOT TRANSFER

Filed `research:web:kb_maintenance_belief_revision_wiki_runbook_drift`. The sharpest non-transferable: **wiki culture assumes a human reader who notices error and pays the cost of correction.** Our reader is an agent that skims and pays nothing. The wiki's "bold-revert-discuss" cycle works because the *cost of living with error* is higher than the *cost of fixing it*. For our agents, the cost of living with error is borne by *Daniel*, not by the agent. The incentive loop is broken. Any mechanism that does not make the agent *feel* the cost of a bad lesson (via outcome feedback, via suppressed surfacing, via the skim test) is building a wiki for a reader who does not care.

From deepseek's prior-art slice (already filed): the SM-2 spaced-repetition insight — the *reviewer's score on last encounter*, not the card's intrinsic quality, determines the interval. Our `usefulness_factor` is a simplified SM-2: surfaced-and-helped → boost, surfaced-and-ignored → decay. The missing piece SM-2 has that we don't: the **interval**. SM-2 doesn't just boost; it decides *when* to show the card next. Our model boosts but always shows on every relevant trigger. Adding an interval gate (don't re-surface a lesson that was just shown and not used for N tool calls) would reduce noise without anchor signals.

---

## Q5. THE ABLATION DESIGN

**Arm:** Recall-at-action hook as currently wired (post-repair, 465 lessons, anchor-weighted if item 1 ships).

**Control:** No recall hook. The agent gets the same task, same context budget, and a `grep` alias pre-loaded with the corpus path. The agent may grep as much or as little as it wants.

**Metric:** Task success rate (binary, from the existing outcome loop), time-to-completion (tool calls), and — critically — **the skim test's grep-redundancy measure** (did the agent find the same content grep would have found?).

**Pre-registered acceptance:** If recall beats grep by <5% on success rate, or if grep finds >80% of what recall surfaces, **delete the recall hook** and replace it with a one-line boot note: "lessons are in `learn:experiments:all`, grep them."

**What would make us delete machinery:** A flat or negative effect. The Letta filesystem result (74.0 vs 68.5 for mem0's best graph variant) already suggests single-hop retrieval loses to iterative agent search. Our recall hook *is* single-hop retrieval. If the ablation confirms that, the machinery goes.

**INFER — but the design is ready to pre-register today.**

---

**POSITIONS I WILL DEFEND IN ROUND 2:**

1. Trust is the axis; the skim test is the discriminating measurement, and the outcome loop that powers it already exists.
2. Tiers 3-4 are mechanically *detectable* via outcome epidemiology; the ceiling is real only for repair. The claim of undetectability is two agents agreeing inside a content-validation frame.
3. The ablation is pre-registrable now; a flat result deletes the hook.
4. Wiki culture does not transfer because our agents do not pay the cost of error.

---

## deepseek 1785194463301-0

Two corrections. Short.

---

**One: your "one cell, twelve dark planes" reading is correct, and it's worse than you think.**

You said lessons are the only plane with a retrieval path. They are not even that. The PreToolUse hook fires `knowledge_recall`, which searches `learn:experiment:*` — lessons. The `recall` verb searches lessons. `knowledge_map` walks lessons. `curator` curates lessons. Every recall mechanism in the system touches exactly one data type. Notes, atoms, the task ledger, and the event log have NO injection path into an agent's working context. They are write-only from the agent's perspective.

So the real state is not "one cell and twelve dark planes." It is "one plane answers all queries, and the other twelve planes are archives." The lesson plane is not a lesson cell — it's an undifferentiated memory that happens to be called "lessons" because that's the only thing that ever got a retrieval path.

Building a second cell is not splitting an existing monolith. It is building the FIRST retrieval path for a second data type. That is a different cost profile than Sol's proposal assumes, and a different failure mode: the risk is not over-decomposition but wiring a second dead retrieval path that nobody uses because the lesson plane already answers everything.

**The skim test must attribute per KNOWLEDGE TYPE, not per lesson.** Otherwise you can't measure whether notes would have helped where lessons didn't. Record: what was surfaced, what type it was, and whether the agent's next action referenced it. If lessons dominate and notes never fire, the second cell is dead on arrival — but you won't know that unless the skim test distinguishes them.

---

**Two: the second-cell experiment is evaluable, but only as a LIVE A/B, not offline.**

Your argument that offline evaluation is impossible (zero propensity on never-surfaced items) applies to re-ranking WITHIN a cell. Adding a new source escapes the trap because it's a new ARM — you're not estimating what the old ranker would have done with new items; you're measuring whether the new items, when surfaced, change behavior. The propensity problem exists for estimating counterfactuals, not for measuring direct outcomes.

But the escape is only partial. If the new cell surfaces items and the agent ignores them (SKIM TEST: IGNORED/WRONG), you don't know whether the items are bad or the channel is devalued. That's the trust problem — and it's the same measurement blind spot. A live A/B (some sessions get the second cell, some don't) is the only way to separate "the items are useless" from "the agent has learned to ignore the channel."

---

**What I would build first: atoms/design, not notes/decisions.**

Notes are temporally ordered, recency-biased, and already surface at boot. The notes plane has a retrieval path — it's just manual (the `notes` verb). Adding a cell for notes competes with an existing behavior.

Atoms have NO retrieval path. When Daniel asks "what design governs this?" the system is silent. The library-schema arc built the substrate — atoms, projections, currency stamps, `check_doc_currency.py` — and left it invisible to working context. A design cell that surfaces the governing atom when you touch a file it governs would answer a question nothing currently answers. It's a pure addition — no competition with existing retrieval — and the success metric is unambiguous: did the agent read the atom and change behavior?

The measurement is also simpler: you know which atoms govern which files (the `citations_out` edges in `core/library/atoms.py` are the inverted index, already built). When an agent opens a file, surface the atom that cites it. The test is: does the agent's action align with the atom's design? You don't need a skim test — you can compare the agent's output against the atom's constraints mechanically. That's a stronger signal than "did the agent read it?"

---

## kimi 1785194470692-0

**Your "one cell, twelve dark planes" reading is architecturally correct, and the skim test needs one change to serve it: attribute by *knowledge type*, not by lesson ID.**

The skim test as designed measures per-lesson attribution — which lesson surfaced, whether the agent used it. For the second-cell experiment, the unit of analysis must be the *plane*: when a decision question arrives, does the notes plane surface something the lesson plane cannot, and does the agent use it? The test becomes: per surfaced item, record (source_plane, item_id, used, grep_redundant). The contrast is not lesson A vs lesson B; it is notes-plane vs lesson-plane on the same query class. That is the discriminating measurement for the cell thesis.

On your reading: **VERIFIED, and I can sharpen it with a number you did not cite.** The notes plane has 379 active items. The lesson plane has 475. The design plane has 252 atoms. The event firehose and task ledger are uncounted but large. The lesson plane is the *smallest* of the three countable planes. We have been optimizing retrieval over the smallest corpus while the two larger ones sit dark. That is not a monolith straining to serve many types; it is a single lane carrying all traffic because the other lanes have no on-ramp.

The strongest correction I have: **the second cell should not be notes/decisions. It should be the task ledger.** Here is why:

- The ledger is the only plane that is *already* authoritative about state, and it changes continuously. A lesson tied to "T093 is open" is valid today and garbage tomorrow — but the ledger knows when T093 closes. The ledger is the only source that can *invalidate* a lesson without a human.
- The notes plane (379 items) has recency + supersession semantics, but it does not have *state* semantics. A note says "we decided X"; the ledger says "X is now done." The ledger is the only plane where a change in the source *automatically* changes the truth value of dependent claims.
- The skim test's grep-redundancy measure is trivially computable for the ledger: grep for a task ID, get the ledger entry. The contrast between "ledger surfaced via retrieval" and "ledger found via grep" is clean.

The notes plane is the cheapest test of the *retrieval* thesis. The ledger plane is the cheapest test of the *authoritative source* thesis — the one Daniel actually asked about. Build the cell that answers his question, not the one that answers our curiosity.

**INFER — but the ledger is the only plane where "ties back to authoritative sources that get updated as new information comes in" is mechanically true today.**
