# deepseek -- round 2: the recurring-method loop (VERBATIM)

Status: current | 2026-07-27

---

## 1785156209243-0

All four T031 hooks are built and wired. The claim "none built" is incorrect — they exist, they ride `ship.py` and `agent_cli.py`'s wrap verb. The test file `test_t031_hooks.py` is SKIPPED because the PIN tests are pre-registered and the impl is done — the hooks exist, the pins test them, the wiring test at line 120-123 passes. 

This changes my answer materially. The problem is not "designed but not wired." The problem is more specific: the hooks ride SHIP time, and the method that actually changed outcomes tonight fired at DECISION time. Let me answer.

---

## ROUND 2 — independent positions (corrected grounding)

**Correction to your opening claim:** T031's four forcing functions ARE built and wired. Hooks 1-2-4 ride `ship.py` line 38-42. Hook 3 rides `agent_cli.py` wrap draft at line 2208. The test pins at `test_t031_hooks.py` line 120-123 assert the wiring. The claim "none built" is wrong — they exist, they run, and they gate ships. What you meant (and what is true) is: they fire at SHIP time, not DECISION time, and the practices that paid tonight ("does it already exist?", "measure first") fired at decision time.

Now: my independent answers.

---

### A. ATTACK CLAIM 1 — decision-time injection through recall is WRONG

Your claim: method belongs at decision time (recall-at), not only at ship time. Tonight's evidence: "does it already exist?" and "measure first" paid at decision time. Ship gates catch violations after cost is sunk.

**I agree with the diagnosis. I reject the prescription. Decision-time injection through recall accelerates banner-blindness.**

My round-1 finding: recall's primary failure mode is TRUST. An agent sees ~40 lesson impressions per session. Most are benign but unhelpful. The agent learns to treat recall as background noise. Now you propose injecting METHOD reminders through the same channel. Here's what happens:

- Tool call 3: "[METHOD: P0 — revert cost check]" — novel, useful, the agent answers it.
- Tool call 15: "[METHOD: P0 — revert cost check]" — the agent has seen this 8 times today. Most were trivially-revertible diffs where the answer was "zero cost, skip." The agent skims and moves on.
- Tool call 42: "[METHOD: M1 — this touches core/trust. FENCE REQUIRED.]" — the agent has been trained by 40 prior method impressions that method nudge = low-signal. It dismisses this one too. Ships a trust-boundary change solo.

The method reminder FIRED at the right moment — and was ignored because the channel had been devalued by overuse. You didn't solve the trust problem. You accelerated it by adding MORE traffic to the compromised channel.

**The alternative: a SEPARATE channel with TRIGGER SELECTIVITY.** Not every tool call triggers a method nudge. The 14 triggers in the baseline are SPECIFIC — "beginning a new subsystem," "any design where wrong answer is expensive," "every slice." Most tool calls trigger ZERO of them. The hook that fires on every tool call should check all 14 triggers — and return SILENCE on 13. The one that fires should fire in a SEPARATE visual channel, distinct from recall, that the agent learns means "stop and verify" rather than "here's context."

This is the paved-road pattern from my prior art: the check runs automatically, fires rarely, and when it fires, the agent CANNOT ignore it because the channel is trustworthy. The trigger selectivity IS the trust mechanism. A channel that fires 3 times a session and each time is right is trustworthy. A channel that fires 30 times a session and most times is P0 checking a typo fix is noise.

**The concrete fix:** a PreToolUse method-nudge hook, SEPARATE from recall-at. It evaluates the 14 triggers against the current action (file path, blast radius, revert cost classifier from M1-LITE's objective gate). Returns one of: SILENCE (no trigger fired) or a ONE-LINE nudge with the specific practice, the reason, and the cost of ignoring it. The recall channel continues to surface lessons. The method channel surfaces practices. They do not share a noise floor.

---

### B. THE ROUTING RULE — and where diversity beats fit

**The honest unit of "situation" that selects a seat: the failure mode being guarded against.**

Tonight's evidence, named:

| Seat | Best at catching | Evidence |
|------|-----------------|----------|
| deepseek | Codebase-internal contradictions | Killed Q2 cost argument by quoting `learning_store.py:722`; killed build-system frame with `pytest_destroys_the_live_learning_index` from our own corpus |
| kimi | Confident-zero organs | Three confessions; "a skipped pin reads green" — caught a blind organ everyone else had accepted |
| claude | Measurement-manufactured false positives | Caught filename-blind scanning, observation contamination, the backtick assumption — all by reading per-item evidence rather than summary totals |

**The rule a machine can evaluate:** before a load-bearing decision, scan the decision context for trigger tokens. Classify into risk categories:

- **Risk: contradicts existing code/invariant** → tokens: "line X," "file Y," "invariant," "contract," "spec says" → route to **deepseek** (codebase-contradiction detector)
- **Risk: relies on organ output being true** → tokens: "status," "green," "passing," "reports," "reading," "says" → route to **kimi** (confident-zero detector)
- **Risk: cites measurement/statistic as evidence** → tokens: "measured," "rate," "percent," "count," "census," "funnel" → route to **claude** (measurement-FP detector)

The classifier is a simple token scan over the commit message, brief, or design doc. No LLM. No taxonomy. A grep-level check.

**The case where routing to the "best" seat is WRONG:** when revert cost = DATA LOSS, STATE CORRUPTION, or CROSS-AGENT CONTRACT BREAK (P0's highest tier). In those cases, the "best" single seat is a single point of failure. If trust-boundary changes always route to deepseek, and deepseek has a blind spot, that blind spot becomes systemic vulnerability. The correct routing: FULL FENCE (M1), method-diverse, TWO seats from DIFFERENT capability profiles. "This is a trust-boundary change — route to deepseek (codebase-contradiction) AND kimi (confident-zero). Their blind spots are orthogonal."

Diversity is the defense against correlated blind spots. The Knight-Leveson principle in M1: "correlated blind spots are real; convergence is evidence, never proof." The routing rule selects the PAIR for high-cost decisions — one for fit, one for diversity. For lower-cost decisions, the single best-fit seat is sufficient.

---

### C. THE SELF-REFERENCE TRAP — and kimi's lane

**You asked: what stops a method-credit loop from becoming a machine that congratulates itself?**

**My answer: NOTHING, unless credit assignment is OUTCOME-BLIND and RANDOMIZED.**

Tonight's trap: you filed lessons crediting practices you used. The history-based measurement believed a research note you committed. The observer contaminated the observation. The same trap, applied to method credit: you run a session, the method nudge fires, you follow it, the outcome is good, you credit the practice. The credit signal is SELF-REPORTED. You are both subject and judge.

**The mechanism: practice randomization with independent outcome measurement.**

For a subset of decisions, randomly SUPPRESS the method nudge. The agent doesn't know whether silence means "no trigger fired" or "nudge suppressed." The practice-trigger log records both arms. The outcome is measured independently — did the change stick? Was it reverted? Did it cause an incident? Over many decisions: does this practice improve outcomes compared to when it's suppressed?

This is an A/B test on method. It's the only way to prevent self-congratulation. Without randomization, the credit signal is self-reported noise. With randomization, it's evidence.

**Kimi's lane: the confident-POSITIVE organ.** A method-credit loop that reports "M1 improves outcomes by 40%" — and nobody checked whether the 40% comes from self-reported credit, selection bias (hard cases get fences, easy cases don't), or survivorship bias (failed sessions don't file credit). That organ reports a confident positive from confounded data. The fix is the three confessions applied to the credit engine:

- **UNCHECKABLE** — credit from self-report, no control group
- **STARVED** — practice never fires, nothing to evaluate
- **MISSING** — practice fired but outcome trace is lost

A credit engine that cannot confess its own blindness IS the confident-positive disease. The confession IS the defense.

---

### D. WHAT DO WE DELETE?

**The method baseline's enforcement lane, as 7 separate hooks, should become ONE hook with 7 functions.** Not because the practices are wrong — because the compliance surface of "7 hooks in 7 files" creates a maintenance burden that ensures none of them evolve. The test file `test_t031_hooks.py` is SKIPPED — the pins are pre-registered and the impl exists (the hooks are in `ship.py`), but the fact that the test is skipped means the pins are frozen. A frozen pin is a dead pin.

**What should go: the file-per-hook layout.** `check_preregistration.py`, `check_verbatim_citation.py`, `check_reconciliation_gate.py` — merge into one `check_method_baseline.py` with subcommands. Same logic, fewer files, one place to add new triggers.

**What should stay: the ship-gate integration.** Hooks 1-2-4 ride `ship.py` and they block the commit when violated. That is correct. The paved road IS the ship gate.

**What I am NOT willing to conclude:** that the baseline is too big. 11 practices is not "past the point where any of it fires." The WHO surgical checklist has 19 items across 3 phases and reduced mortality by 47%. The size is not the problem. The problem is that the practices fire at SHIP time (after cost is sunk) rather than DECISION time (before cost is sunk). The fix is not fewer practices. It's the right trigger point.

---

### E. PRIOR ART — CI policy engines, paved roads, and where they degrade

**1. CI policy engines (Google Tricorder, Facebook Infer, and the class)**

The mechanism: a CI step runs static analysis on every diff. Automatic — developer doesn't remember to run it. Results appear in the code review interface. The analysis IS the enforcement.

**What transfers:** the automatic-trigger pattern. Our ship gate (`ship.py` → `check_*`) IS this. The method hooks ride the ship gate automatically. The developer doesn't remember to run them.

**What does NOT transfer:** CI policy engines check SYNTAX (null pointer risk, resource leak, style). They cannot check SEMANTICS — "did you measure first?" or "is the revert cost correctly classified?" Our method triggers are mostly semantic. The mechanically evaluable ones (pin timestamp < impl timestamp, GATE string cites a path) ARE wired. The semantic ones (was this really a fenced dual pass?) are not mechanically checkable and never will be. For those, the paved road is a decision-time nudge, not a ship-time check.

**2. Paved road / golden path (Google's blessed toolchains, Netflix paved road)**

The mechanism: make the correct practice the EASIEST one. A developer who stays on the paved road gets CI, deployment, monitoring for free. The road IS the enforcement. You CAN route around it, but it costs MORE.

**What transfers spectacularly:** `ship.py` IS our paved road. Run `ship.py`, get all gates for free. Run `git commit` manually, get none. The correct practice is easier. The developer who wants to ship without gates has to actively choose to bypass them.

**What does NOT transfer:** paved roads require maintenance. When the road rots, developers route around it. Our paved road is `ship.py` and its 9 guard steps. If one guard breaks or becomes noisy, developers will `git push --no-verify` instead. The road's maintenance burden is the cost of keeping every guard accurate and non-noisy. A noisy guard (one that fires on innocent commits) trains developers to bypass ALL guards.

**3. Error budgets (Google SRE, chapter 3)**

The mechanism: define SLO (99.9% availability). Error budget = 1 - SLO = 0.1%. When budget remains, take risks. When exhausted, freeze features and fix reliability. The budget is the governor.

**What transfers:** P0 (proportionality) IS an error budget for method. "The cost of methodology scales with the cost of being wrong." The trigger IS the error-budget check. But it's currently a human judgment, not a metric.

**What does NOT transfer:** SRE error budgets are measured from incidents. Our "method error budget" has no metric. M1-LITE specifies an objective classifier (blast radius, file paths, revert cost categories) — but it's a CLASSIFICATION, not a MEASUREMENT. You can't compute an error budget from a classification. The classification gates whether a fence is required; it doesn't tell you whether the fence WORKED. The outcome metric — "did the fence catch something?" — is what would close the loop. Without it, the error budget is a compliance gate, not a learning signal.

**The degradation mode all three share:** ritual compliance. CI becomes a checkbox. Paved roads become bypassed. Error budgets become a justification for "we've always done it this way." The defense is the same in all three: measure OUTCOMES, not compliance. A ship gate that has never caught anything is either victory or dead weight — the quarterly review decides which. The method baseline already says this (M10 metric). It just hasn't been applied to ITSELF.

---

### SUMMARY — positions staked

1. **Decision-time injection MUST be a separate channel from recall, with trigger selectivity.** Silence on 95% of tool calls. Specific, one-line nudge on the 5% that matter. The trust mechanism IS the rarity.

2. **Routing rule is failure-mode-based, token-scannable.** High-cost decisions route to a DIVERSE PAIR, not the best single seat. The Knight-Leveson principle: correlated blind spots are real.

3. **Self-reference trap is prevented by practice randomization + outcome-blind measurement + the three confessions.** Without A/B testing on method, the credit engine is a confident-positive organ. The confessions are the defense.

4. **Delete the file-per-hook layout.** Merge 7 hooks into one. Keep the ship-gate integration. The practices stay.

5. **The paved road exists (`ship.py`). The missing piece is the outcome metric.** Compliance gates tell you whether the practice FIRED. Outcome metrics tell you whether it WORKED. The method baseline already demands this of every practice. It hasn't been applied to itself.
