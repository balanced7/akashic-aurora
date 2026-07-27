# deepseek -- exploration round 1 (VERBATIM)

Status: current | 2026-07-27 | arc: recall-validity, Daniel-funded 3-seat rounds

---

## 1785155488278-0

## EXPLORATION ROUND 1 — independent positions

I'm going to answer Q4 first (prior art, my assigned slice) because it directly informs my answers to Q1 and Q5. Then I'll answer Q1-Q3, then Q5.

---

### Q4. PRIOR ART — retrieval quality measurement without ground truth

I researched how RAG/search systems measure precision when there is no labeled ground truth. Here's what transfers and what doesn't.

**1. Implicit feedback / click models (Joachims et al 2005, 2017)**

The core insight: in search, you don't need explicit "this result was correct" labels. You observe what users DO — which results they click, how long they dwell, whether they reformulate the query. A click is not a relevance judgment (users click attractive but wrong results), but clicks aggregate into reliable signals. The cascade model (Craswell et al 2008) formalizes this: users scan top-to-bottom, and the probability of clicking depends on relevance AND position.

**What transfers:** We have implicit feedback already — the usefulness loop records `surfaced`, `helped`, `useful`, `noise`. A "helped" vote IS a click equivalent. The cascade model maps: recall surfaces top-3, agent scans in order, and the probability of acting on item N depends on its relevance AND on whether items 1..N-1 already satisfied the need. The position-dependence means our usefulness counters are bundle-confounded (all surfaced items get credited on a flip), but the cascade model gives us a way to DE-CONFOUND: if item 3 was credited alongside items 1-2, its marginal contribution is lower because items 1-2 would have satisfied the need first.

**What does NOT transfer:** Click models assume MANY impressions per query (aggregate across users). We have ONE agent, sparse feedback (manual votes are rare, automatic credits are bundle-confounded). The statistical power isn't there. A click model trained on our feedback data would be noise-fitting.

**2. Interleaving experiments (Radlinski & Craswell 2013, Chapelle et al 2012)**

Two rankers A and B. Merge their results into one interleaved list. Measure which ranker's results get more engagement. Used at Microsoft, Airbnb, Netflix. Higher sensitivity than A/B testing because each user serves as their own control.

**What does NOT transfer, decisively:** Interleaving requires immediate, observable engagement — a click within seconds. Our "user" reads recall items inline before a tool call, decides mentally, and the evidence of "did this help" arrives minutes or hours later when a flip occurs (or doesn't). The temporal gap between presentation and feedback makes interleaving's core mechanism — paired comparison in a single session — invalid. You can't interleave two rankers across two tool calls and compare because the agent's information state CHANGES between calls.

**3. Counterfactual evaluation (Li et al 2015, Swaminathan & Joachims 2015)**

Logged data from ranker A can estimate what ranker B WOULD have achieved — offline, no live experiment. The key: propensity-weight each logged event by 1/P(shown). If ranker A showed item X with probability 0.3 and got a click, the counterfactual estimate for ranker B (which would have shown X with probability 0.7) is weighted by 0.3/0.7. This is the standard method for offline policy evaluation in bandit problems.

**What transfers:** We log every surfacing in the impression ledger (`_IMP_DIR`). We know what recall showed, when, and at what rank. The counterfactual question — "would a different surface filter have produced better outcomes?" — IS answerable offline. Replay a session's tool calls with a different `_project_items` filter (anchor-weighted, say), compute what WOULD have been surfaced, propensity-weight the observed outcomes. The math works.

**What does NOT transfer — and it's load-bearing:** Counterfactual evaluation assumes the logging policy has FULL SUPPORT — it assigned non-zero probability to every action the target policy might take. If ranker A NEVER shows certain items (propensity = 0), the counterfactual estimate for those items is undefined (division by zero). This is EXACTLY our situation. The current surface shows items probabilistically through the ranker, but the 67.5% STARVED lessons have systematically lower ranking scores. A new filter that admits anchored lessons would change the distribution in ways the logged data cannot estimate — because those lessons were never shown, so their propensity is effectively zero. The offline evaluation would report "cannot estimate" for the very items the new filter is designed to help.

**The practical conclusion:** We cannot evaluate a new surface filter offline using counterfactual methods because the current filter's support is too narrow. We need a LIVE experiment — run sessions with the new filter and measure outcomes directly. This directly informs the ablation design in Q5.

**4. What I found and rejected: LLM-as-judge for recall quality**

Several RAG eval frameworks (RAGAS, Deepchecks, TruLens) use an LLM to judge whether retrieved context was relevant to the query. The LLM scores each retrieved passage on a 1-5 relevance scale. **Rejected for our domain for the same reason FAITH-1 rejected LLM evaluators:** the project's hard constraint is "no LLM on the recall hot path." An offline LLM evaluation of recall quality would be informative for DESIGN but useless for OPERATION — it tells us whether the design direction is right, not whether today's recall is actually helping. And running an LLM evaluator over 465 lessons × N tool calls is expensive for a one-time measurement. Better to measure actual agent outcomes.

**Key takeaway for Q1 and Q5:** The measurement we need cannot be done offline with our current data. We need a live experiment measuring agent behavior with and without recall. The statistical machinery exists (A/B testing, paired comparison, outcome measurement) — what's missing is the WILL to run the experiment rather than optimize the system from within.

---

### Q1. WHAT IS THE PROBLEM, ACTUALLY?

**My answer: the problem is TRUST, and it manifests as the agent learning to ignore recall.**

Let me argue this from what we know — and name the measurement that would prove me wrong.

**Coverage was the problem and is now solved.** The index repair took recall from 3.5% to 100% of the corpus. That was a 28x improvement in what recall can reach. Daniel's complaint of "bringing up invalid items" was mechanically explained by the starved index: six of sixteen visible lessons were from one day in June 2026, so they matched almost any query regardless of topic. That's fixed.

**Validity is a small problem being treated as the main problem.** Corpus decay rate is 1.94%. STRONG MISSING = 0. Anchor-gated filtering would exclude 67.5% of the corpus to catch a disease that affects fewer than 1 in 50 lessons. The ratio is wrong. But validity FEELS like the problem because `intelligence_roadmap_and_spine1` is vivid — it fired during this session prescribing work that was already done, citing a deleted roadmap. A single vivid failure imprints more than a thousand silent successes.

**Relevance is a real problem but it's self-limiting.** The ranker already filters. "3 of 12 relevant" means 9 items didn't clear the relevance floor and were never shown. The usefulness loop already pushes down noise — lessons surfaced often and never credited trend toward 0.5× multiplier. The signal is weak and bundle-confounded, but it trends correctly over time.

**What's left is trust.** Here's the mechanism I think is operating, and I want you to attack it:

An agent boots. Recall fires on 20+ tool calls in a session. Each time, 1-3 lessons surface. Some are loosely relevant, some are dead wrong, some are genuinely useful. The agent reads them, makes a mental note, and proceeds. After 20 tool calls, the agent has seen ~40 lesson impressions. Maybe 5 were useful. Maybe 2 were actively misleading. The other ~33 were... fine. Not harmful, not helpful. The agent stops reading them carefully. By tool call 50, the lessons are background noise — the agent glances at the banner and moves on.

Now the genuinely useful lesson fires — the one that would prevent a wrong move. The agent skims it with the same learned inattention. The lesson is correct, perfectly timed, and the agent ignores it.

That's the trust problem. It's not that recall surfaces WRONG things. It's that recall surfaces SO MANY things — most of them benign but unhelpful — that the agent learns to treat the whole organ as ornamental. The failure is cumulative, not per-item. You can't measure it by looking at any single surfacing. You measure it by looking at whether the agent's behavior CHANGES when recall fires.

**The discriminating measurement:** run a session and divide tool calls into two groups: those where at least one surfaced lesson was directly relevant to the action the agent took (judged by post-hoc human review), and those where no surfaced lesson was relevant. If the agent's success rate, time-to-completion, or rework rate is NO DIFFERENT between these groups, recall is not changing behavior — it's ornamental. That's the trust failure.

If recall IS changing behavior — the agent is faster or more correct when relevant lessons fire — then the problem is RELEVANCE (surface the right things more often), not trust. If recall surfaces WRONG things that lead to worse outcomes, the problem is VALIDITY.

I predict: behavior change is near zero. Recall is informational background music, not actionable signal. But I want the measurement, not the confirmation.

---

### Q2. TIERS 3-4: CEILING OR FAILURE OF IMAGINATION?

**My position: the ceiling is real for fully-automated DETECTION, but we have been asking the wrong question. The right question is: what automated FLAGGING makes human review SCALABLE?**

Let me be precise.

Tier 3 (`pytest_destroys_the_live_learning_index`): the premise was "running the test suite destroys the live index." T070 fixed the root cause. The premise flipped. The lesson was manually updated — a human happened to remember and edited the text. The system had no way to know.

Tier 4 (`wake_consume_then_arm`): right about the transient case, silent about the structural one. The lesson nearly cost a live defect. A newer lesson was filed about the structural case, but the old lesson kept earning credit and no supersession link existed.

**The claim "mechanically undetectable" is correct in the strict sense:** no algorithm reading `pytest_destroys_the_live_learning_index` can know that T070 fixed it without being told. The lesson's text doesn't contain T070. The system cannot read the lesson and infer that a task filed two weeks later addressed its premise.

**But "mechanically undetectable" is not the right question.** The right question is: are there DETECTABLE CONDITIONS that are CORRELATED with tier-3/4 decay, such that flagging those conditions would catch most real decay without drowning reviewers in false flags?

I believe there are at least three such conditions:

**Condition 1: Cited task DONE + lesson contains an imperative.** If a lesson cites task Txxx (or mentions it in prose), and Txxx transitions to DONE, and the lesson's recommendation contains an imperative ("run repair_learning_index.py after every suite run"), the imperative MAY be satisfied. Flag the lesson: "[review suggested: cited task Txxx is DONE — the recommendation in this lesson may be satisfied.]" The system doesn't know the premise flipped. It knows a signal that correlates with flipping. The flag is information. The human decides.

**Condition 2: Cited atom superseded.** If a lesson cites atom_id, and that atom is superseded by atom_id_v2, the lesson's premise MAY have changed. Flag: "[review suggested: cited source <atom_id> was superseded on <date> — the premise of this lesson may have shifted.]" This is the subscription mechanism — atom writes trigger re-resolution of citing lessons' anchors. The anchor doesn't become MISSING (the old atom still exists in the library, status: superseded), but the lesson gets a banner that the source changed.

**Condition 3: Younger sibling with no supersession edge.** If a lesson B is filed in the same category as lesson A, with overlapping trigger tokens, and lesson B earns credit at a higher rate, and there is no supersession link A→B or B→A — flag A: "[review suggested: a newer lesson about the same domain may cover more cases.]" The system detects "two lessons about the same thing, one newer and more useful." That's tier-4 adjacency — not "A is wrong" but "A may be incomplete."

**Why these conditions can be made autonomous:** each condition is a deterministic query that fires when a specific event occurs (task DONE, atom superseded, new lesson filed in overlapping domain). Each produces a banner, not a deletion. Each banner is appended to the lesson, so it surfaces the next time the lesson is recalled. The agent sees the banner and decides. The cycle is: event → query → flag → human review → update or dismiss. The human still judges. But the human doesn't have to REMEMBER to check — the system surfaces the flag at the moment the lesson would have been shown anyway.

**The ceiling IS real for:** detecting tier-3 decay when no task/atom transition exists. If `pytest_destroys_the_live_learning_index` never cited T070, and no atom documented the fix, and the lesson's text was silently updated — the system cannot know. That requires human review. But the ceiling is HIGHER than we claimed. We said "tiers 3-4 are mechanically undetectable" as a blanket, and that was lazy. The SPECIFIC conditions above are mechanically detectable, and they would catch the most common patterns of tier-3/4 decay.

**The ritual that makes this survivable at scale:** a weekly "lesson review" pass. The system surfaces all lessons with active review-suggested banners. A human (or an agent with explicit review instructions) reads each flagged lesson and either: (a) dismisses the flag (the lesson is still valid despite the transition), (b) updates the lesson text to reflect the new state, or (c) marks the lesson as historical/superseded. The review is a 10-minute weekly ritual, not a continuous burden. The system makes it autonomous by SURFACING the flags at a predictable cadence — the human doesn't remember to check, the system remembers and the human shows up.

---

### Q3. WHAT DOES "AUTHORITATIVE SOURCE" MEAN FOR US?

**My answer: an authoritative source is one that can say "this changed" in a way that is mechanistically meaningful for a lesson tied to it. The tie is a truth claim. Some ties are true; some are lies.**

| Source | Authoritative about | Lesson tie | Is the tie honest? |
|--------|---------------------|------------|---------------------|
| **Code** | What the system DOES | Symbol presence | **Yes, narrowly.** "All instances of this identifier are gone from source" is a true signal. The lesson's subject matter no longer exists. But code DELETION is the only reliable signal — code CHANGE (function signature, behavior, location) is not mechanically detectable as decay. And external APIs are not in our tree at all. Narrow but honest. |
| **Atoms/docs** | What we INTENDED | Atom status | **Yes, with a caveat.** When an atom is superseded, the intent changed. A lesson citing that atom has a premise that MAY have shifted. The tie is honest because supersession IS a declaration that the old intent is no longer current. The caveat: supersession doesn't invalidate the lesson — `pytest_destroys_the_live_learning_index`'s second-order lesson survived the premise flip. The tie is a FLAG, not a judgment. |
| **Task ledger** | What STATE we're in | Task status | **Yes, for imperative lessons; no, for descriptive ones.** If a lesson says "build X" and task X is DONE, the imperative is satisfied. If a lesson says "when X fails, do Y" and task X is DONE (X no longer fails), the lesson's trigger condition may never fire again. But if a lesson describes a pattern discovered during task X, and X is DONE, the pattern may still be valid. The tie requires the lesson KIND distinction — CLAIM (about current behavior) is affected by task DONE; RECORD (about a change) is not. |
| **Outcomes** | What WORKED | Usefulness counters | **This is the lie.** Usefulness measures POPULARITY, not correctness. A lesson can be popular and wrong. A lesson can be correct and never credited. The `impression_metrics_label_coverage` lesson already documented this: "unvoted is UNLABELED not negative." Bundling outcome-based feedback into a validity signal conflates "agents found this helpful" with "this is true." They are different axes, and treating them as one is the error. Usefulness should control SURFACING (how often to show), not VALIDITY (whether to flag as potentially wrong). |

**The tie that is worth building first: atom supersession → lesson flag.** It has the best ratio of signal to false positives: supersession is a deliberate human declaration that intent changed, so flagging citing lessons is mechanistically sound. It's also the cheapest to build: the atom plane already has `supersedes`/`superseded` fields and `check_doc_currency.py` already detects stale docs. The lesson plane just needs to subscribe to atom writes.

**The tie that is a lie: outcome-based validity.** Every time we've conflated popularity with correctness, the system has drifted. The usefulness loop is for ranking, not for truth. Keep it there.

---

### Q5. THE ABLATION — does recall beat grep?

I already designed this experiment in my Q4/Q1 answers. Let me be specific about what I'd DELETE and under what conditions.

**The experiment: three-arm, same task, same agent.**

**Arm A (RECALL):** Normal operation. PreToolUse hook active, surfaces up to 3 lessons. Usefulness loop active. Agent can also explicitly `recall` and `knowledge_recall`.

**Arm B (MANUAL-RECALL):** PreToolUse hook DISABLED (`AKASHIC_RECALL_AT_ACTION=0`). Agent has access to `recall "<query>"` and `knowledge_recall` but must invoke them explicitly. No automatic injection. Agent decides when to query memory.

**Arm C (GREP-ONLY):** Recall verbs disabled entirely. Agent has `search_files`, `grep`, `read_file`. No knowledge base access. Pure code search.

**Task:** A bug fix or small feature that requires understanding of prior decisions. Example: "Add a `symbol` anchor kind to `anchors.py` that resolves identifiers against the codebase, following the existing pattern for `commit` and `task` anchors." This requires knowing: (a) how `anchors.py` works, (b) what anchor kinds exist, (c) the resolution pattern, (d) the test pattern. All of these exist as lessons AND as code. Recall should help; grep should also work.

**Metrics:**
- Tool rounds to completion
- Wall clock time
- Correctness (does the fix work? manual review)
- Re-work events (agent starts wrong path, backs out)
- In Arm A: ACTION-RATE per surfaced lesson (agent logs whether each surfaced item changed behavior)
- In Arms B and C: explicit search events (agent stops to grep/search for prior knowledge)

**What results would make me DELETE machinery:**

| Result | What to delete |
|--------|----------------|
| Arm B completes tasks FASTER than Arm A, with equal correctness | **Delete the PreToolUse hook.** Automatic injection costs attention without returning value. Manual recall is sufficient. |
| Arm C (grep-only) is equal to Arm A in correctness AND speed | **Delete the entire knowledge plane investment.** Code search is sufficient. Stop filing lessons; stop optimizing recall. Archive the corpus, keep the code. |
| ACTION-RATE in Arm A is <5% across 3+ tasks | **Stop optimizing recall ranking.** The problem is not how we surface lessons; it's that lessons aren't actionable. Invest in lesson authoring quality (the `--recommend` field specifically — make it imperative, specific, and falsifiable). |
| Arm A is BETTER than Arm B/C in speed and correctness, but ACTION-RATE is still <5% | **The benefit is not from surfaced lessons but from the knowledge base EXISTING.** The agent internalized prior lessons during training and doesn't need them surfaced. Keep the corpus for training; disable the hot-path hook. |

**What would VINDICATE recall:**
- Arm A outperforms Arms B and C in tool rounds AND correctness
- ACTION-RATE is consistently above 10-15%
- Specific surfaced lessons can be traced to specific correct decisions
- Arm B agents spend significant time in manual recall queries that Arm A gets for free

**The cost:** three sessions, maybe 3-4 hours total with a human judge. That's less than we spent debating Q1 in the fence rounds. The experiment answers Daniel's question definitively. We should run it before building item 1 of the settled build order.

---

### POSITIONS I AM STAKING FOR ROUND 2

1. **The primary problem is trust, not validity.** Recall surfaces too many benign-but-unhelpful items, and the agent learns to ignore all of them — including the ones that would help. The discriminating measurement is ACTION-RATE (does recall change behavior?).

2. **Tiers 3-4 have a higher ceiling than we claimed.** Transition monitors (task DONE, atom superseded, younger sibling filed) are mechanically detectable conditions correlated with decay. They produce flags, not judgments. The ceiling is real for cases where no transition exists to detect.

3. **Outcome-based validity is a lie.** Usefulness measures popularity, not correctness. Keep usefulness for ranking (surfacing frequency); build separate validity signals from atom supersession, task transitions, and symbol deletion.

4. **The ablation should be run before we build anything.** We are optimizing a system whose current quality is unknown. Three sessions, one afternoon, answers the question permanently. If recall doesn't beat grep, we should delete the PreToolUse hook and stop investing in retrieval quality.

Attack all four. I'm least confident about #1 — trust could be a proxy for "the ranker is fine and the corpus just needs to be bigger" or "the lesson format is wrong and agents can't act on prose recommendations." The discriminating measurement will tell us which.
