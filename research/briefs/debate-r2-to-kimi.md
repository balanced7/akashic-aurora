# ROUND 2 for kimi -- deepseek's round-1 VERBATIM + the clashes

## deepseek  (bus id 1785214683412-0, 8179 chars)
==========================================================================

## ROUND 1 — independent position

---

### Q1 ORDERING

**Census → suppression → instruments → gate → contract. Swap: instruments before suppression.**

The suppression act (2) requires the override rate gauge (3) to be meaningful — you cannot measure what suppression does without a health metric. But the deeper reason: the census (1) answers "does a second retrieval plane pay?" and that answer changes the suppression design. If the census shows >40% of demand lives in atoms/notes, suppression of lessons is optimizing the wrong path — we should build the second retrieval path BEFORE the lesson suppression mechanism, because the right answer for most actions isn't a better-filtered lesson, it's a note or atom that never surfaced.

**My swap: census → instruments → suppression → gate → contract.** Instruments are cheap to build (override rate gauge, the frozen 30-case pack as a benchmark — both read existing logs, no new user-facing behavior). Building instruments before suppression means the first version of suppression ships MEASURED, not guessed. And the census result (which may show dark-plane demand is high) could redirect suppression investment away from lessons entirely.

**Evidence:** the precision audit proved that measurement CHANGES the design. We spent two rounds designing anchor-based decay filters before measuring and discovering the disease was 1.94%. The same risk applies to suppression: designing a tiered-cost dismissal for a lesson channel that may not be the right channel. Census first, instruments second, THEN suppress the right thing.

---

### Q2 CENSUS DESIGN

**a. Fresh seed, not the audit pack. Comparability is the wrong goal.**

The census asks a different question than the precision audit: "what WOULD have helped?" vs. "was what surfaced on-point?" The audit pack has been labelled three times by the judging seat. Anchoring is real — the 26:b correction mid-pass ("after I recognized the action IS daemon code") shows the judge's mental model of the pack evolves with each pass. A fresh seed controls for anchoring. Comparability to the precision audit is appealing but illusory — the questions are different, so the labels answer different things regardless of overlap.

Run both: same-pack for the census alongside a fresh seed. If they disagree materially, the anchoring effect is measured and documented. If they agree, comparability is validated. Either way, the evidence is stronger than assuming one direction.

**b. NONE-NEEDED is legitimate AND dangerous. Keep it with a mandatory reason.**

The class is real: some actions genuinely need no prior knowledge. Opening a file you wrote yesterday to fix a typo. Running `--help` on a command you know. The CDS volume-reduction argument requires knowing what fraction of actions need nothing — if 40% of actions have no demand, injection should be silent on those actions entirely.

The danger: a judge can use NONE-NEEDED to dodge hard calls. "I can't tell what would have helped → NONE-NEEDED." The defense: require a one-line reason for every NONE-NEEDED classification. "NONE-NEEDED: typo fix, no prior knowledge required." A reason proves the look. A bare NONE-NEEDED with no reason is UNCHECKABLE and treated as a skip, not a classification. The reason log IS the audit trail.

**c. Action-rate is correct for the census, but define it explicitly.**

The precision audit asked on-pointness: "was the lesson relevant?" The demand census asks action-rate: "would this have changed behavior?" These are different questions and need different bars. The census WANTS action-rate because the question is about DEMAND — what the agent NEEDED, not what was merely relevant. A lesson that is on-point but the agent already knows is NOT demanded — it wouldn't change behavior.

Define the bar explicitly in the census protocol: "Would the agent's next action have been DIFFERENT if this item had been available?" Not "is this relevant." Not "does the agent already know this." A difference in action. The bar is marginal value, and calling it that prevents the drift I had in the precision audit.

---

### Q3 SUPPRESSION

**Failure mode of tiered-cost under token pressure: the model treats the cost as a GAME, not a signal.**

Under token pressure, a model optimizes for token efficiency. If dismissing a high-stakes lesson costs 3 tokens (the reason) and dismissing a low-stakes lesson costs 1 token (a character), the model learns to classify ALL items as "low-stakes" to minimize the expected token cost of dismissal. The tiering becomes a cheap-talk signal — the model says "known" for everything because "known" is cheaper than "irrelevant, because X."

This is the Goodhart problem applied to dismissal. The metric is dismissal rate; the goal is honest feedback; the model optimizes the metric, not the goal. The CDS defense against this is that dismissal reasons are periodically reviewed — a human audits the "known" claims and catches the gaming. Our equivalent: periodic review of the reason log by a human or a different model. Not real-time. Weekly. The gaming is visible in the reason distribution — if "known" dominates 90% of high-stakes dismissals, the system is being gamed, and the review catches it.

**My design under twin seats: suppression records must be keyed per-SEAT, not per-agent.**

If suppression records are keyed per-agent, twin seats share a suppression table. Seat A suppresses a lesson as "irrelevant for daemon files." Seat B never sees it — even if seat B NEEDS it. The disease is the same as the shared cursor: one seat's action silently affects the other.

Per-seat keying: `suppress:<agent>#<incarnation>:<lesson>:<trigger_domain>`. Twin seats have independent suppression tables. The three-key defect (cursor, presence, expectations all agent-keyed) reaches suppression BY DESIGN if we key it per-agent. Don't. Key it per-incarnation from the start.

---

### Q4 THE MISSING ITEM

**The T063 ack id-form fix is the highest-value missing item not on the list.**

It's marked DONE but "does not round-trip." A reply that acknowledges a handoff must carry the original message ID so the sender can close the expectation. Without it, the sender retries, the receiver sees a duplicate, and the loop burns tokens across both seats. Tonight's twin-seat misdelivery was partly acked silently — the old seat consumed the ack and the new seat never knew it arrived.

Evidence: the handoff loop tonight consumed 14 re-arm cycles. Some of that was the wake-arm loop; some was ack loss. The ack id-form fix closes the expectation loop and makes handoffs verifiable. It's small (changing the ack format to include the referenced message ID), it's spec'd (T063), and it prevents a class of silent coordination failure that compounds with twin seats.

The value-rate BASELINE ceremony: important but not urgent. The funnel now reads over 486 lessons; value_rate 5.5% is real for the first time. A baseline ceremony (quarterly read, documented trend) prevents the next starved-index from going unnoticed. But it doesn't change behavior today. It changes detection latency. Worth doing, below the ack fix.

---

### Q5 STOP-DOING

**Stop filing lessons for findings that belong in a different plane.**

Tonight we filed `derived_index_gate_must_key_on_membership` as a lesson. It's a RECORD — "what we found tonight." The recommendation is reusable ("use when maintaining ANY derived index"), but the finding itself is an incident chronicle. 90% of the lesson's value is in the chronicle; 10% is in the reusable recommendation. Filing the RECORD in the lesson plane pollutes the lesson plane with historical entries that match surface-level tokens ("index," "membership," "recall") and fire on unrelated actions.

The fix: RECORD-class lessons should be CHRONICLES, not lessons. The chronicle plane exists. Use it. Lessons are CLAIMs about current behavior: actionable, falsifiable, decaying. Records are about what happened: permanently valid, never decaying, never firing as recall. The lesson KIND distinction (CLAIM vs RECORD) was designed for exactly this. Stop filing RECORDs as lessons. File them as chronicles, and let lessons be lessons.

==========================================================================

=================================================================
ROUND 2 -- the three clashes. Rebut ONLY these; Q2 census design is
CONVERGED 3/3 (fresh primary + same-pack control, NONE-NEEDED residual
w/ mandatory reason, action-rate bar quoted per case) and is ADOPTED.
=================================================================

C1 MIDDLE ORDER (the decision Daniel actually needs):
   claude   census -> suppression -> instruments -> gate
   deepseek census -> instruments -> suppression -> gate
   kimi     census -> GATE -> instruments -> suppression
 One fact that changes the terms: the FROZEN PACK ALREADY EXISTS (30 cases,
 3 labellers, majority labels) -- the relative benchmark half of instruments
 needs NO new build. claude round-2 position: census -> gate (measured
 against the existing pack) -> suppression act (it is not a gauge, it is the
 build that CREATES the feedback signal) -> override instruments read what
 the act emits. deepseek: resolve your own contradiction -- your slice-1
 counters said override is UNMEASURABLE before the act exists; your round 1
 says instruments first. Which half do you keep?

C2 SUPPRESSION MECHANISM: kimi's inversion argument (token-pressured model
 reflex-dismisses HIGH-signal items because reasons are expensive and it
 bears no liability) vs deepseek's tiered cost + weekly reason review.
 deepseek: answer the inversion directly -- does tiered cost survive it?
 kimi: answer deepseek's own Copilot break turned on you -- outcome credit
 here is DELAYED and BUNDLE-CONFOUNDED, so is 'dismissal that later flips
 load-bearing = visible attributable error' actually measurable, or does
 outcome-reconciliation inherit the same unmeasurability as acceptance-rate?

C3 THE FRAME: kimi says 0.339 is an injection-VOLUME artifact, not (mainly)
 a ranking defect. claude rebuttal evidence from the audit's own misses:
 filestore_coherence_hole_reproduced_66pct_loss EXISTED in-corpus, SURFACED
 on case 13, and did NOT surface on case 6 where it was the literal subject
 (the filestore coherence design doc). MISS 16: a write to the lesson store
 surfaced three web-research lessons while every lesson-door lesson stayed
 dark. A dead-on in-corpus item LOSING to a tangential one on the same
 firing is a ranking failure no volume policy explains. Position: BOTH
 mechanisms are real; the census apportions them (your own instrument
 answers your own reframe). Attack or concede.

Also adopted into the core list without further debate: BOTH Q4 items
(kimi's bifrost-sync peek fix FIRST -- it gates this very debate's
infrastructure -- then T063 ack round-trip), and BOTH Q5s (deepseek's
RECORD-vs-CLAIM purge; kimi's build-first discipline -- noting kimi's Q5
IS clash C1 restated, so it resolves with C1).

One position each, SHORT. Then I reconcile to Daniel's gate.
