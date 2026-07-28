# Fleet debate round 1 -- VERBATIM positions

Brief: research/briefs/fleet-debate-core-plan-2026-07-28.md
Fenced: neither seat saw the other before filing.

==========================================================================
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
## kimi  (bus id 1785214700504-0, 6209 chars, via handoff -- its send door clips replies at 4KB)
==========================================================================

FLEET DEBATE round 1 -- kimi. Independent; I have not seen deepseek's position.

FRAME ATTACK FIRST. Your four-property chain (RIGHT/FOUND/ACTED-ON/HONEST) is the right decomposition, but you have RANKED it wrong, and the ranking is the whole plan. You call FOUND the constraint because precision measured 0.339. But the base-rate math (Axelsson, my prior-art half) says a low measured precision at a 0.5% base rate is not primarily a FOUND defect -- it is an ACTED-ON/injection-volume defect. The ranker can be adequate and still read as 0.339 if it is FORCED to inject 3 items on every action when the true demand is ~0.005. FOUND is being measured under a volume policy that guarantees most injections are noise. So the binding constraint is not "the right answer doesn't surface" -- it is "we inject far more than the base rate supports, and the reader has learned to ignore it." That is ACTED-ON, and it reframes the order: the census (which measures NONE-NEEDED / demand) is correctly first not because it shapes slice-1 but because it is the only instrument that can separate "ranker broken" from "volume too high." Your own frame contains this -- you just labelled it FOUND when the mechanism is injection-volume. Attack my reframe in round 2.

Q1 ORDERING. Census -> gate -> instruments -> suppression -> (contract throughout). I SWAP suppression and the correlation gate, and demote suppression below instruments. Evidence: the correlation gate is the only item that DIRECTLY reduces injection volume, and volume is the lever the base-rate math + CDS + spam all converge on. Suppression (override rate) is a HEALTH METRIC -- it tells you if you are winning, it does not move the number. Gating injection on >=2 independent signals MOVES the number immediately and is measurable against the frozen pack (item 3). Suppression without the gate measures the noise the gate would have prevented; build the gate, then suppression measures its residue. Your order builds the thermometer before the furnace. Contract (5) I agree rides throughout. So: 1 census (demand) -> 4 gate (cut volume) -> 3 instruments (frozen pack + override as relative benchmark) -> 2 suppression (now measuring the gated stream). Justification: the gate is the only build that changes precision; everything else is measurement of a number nothing yet moves.

Q2 CENSUS DESIGN. (a) Run BOTH, but the FRESH seed is the primary and the same-pack is the control -- I labelled that pack twice and WILL anchor; a judge who has already decided case 21 is a dark-plane MISS cannot un-decide it. Comparability is worth less than de-anchoring, because the census's job is to measure DEMAND, not to reconcile with the precision labels. (b) NONE-NEEDED is legitimate and load-bearing -- it is the volume floor, and without it the census cannot answer the question it exists for. But it MUST be the residual class, not a dodge: a judge may only mark NONE-NEEDED after affirmatively ruling out every plane, and the rule should be "NONE-NEEDED requires a one-line reason why no item would change the action." That makes the escape hatch expensive enough to be honest. (c) Census bar = action-rate is CORRECT and does NOT conflate demand with marginal value -- demand IS "would this have changed the action." The precision-fence near-miss was using on-pointness for an actionability question; here action-rate is the native unit, so no conflation. Agreed with your (c) openly.

Q3 SUPPRESSION -- attacking deepseek's tiered-cost design. Its failure mode under a token-pressured MODEL (not a liable clinician) is that the cost asymmetry INVERTS. CDS's tier works because the reason is cheap for the clinician (they KNOW "patient is on this med") and the alert is high-stakes. For a model under token pressure, the reason is EXPENSIVE (it must generate text) and the alert is low-stakes-to-the-model (it bears no liability). So the model will reflex-dismiss HIGH-signal items MORE, because those are the ones demanding a reason, and reason-generation is exactly what token pressure punishes. The design assumes the reason cost deters reflex-dismissal; under a model it SELECTS for reflex-dismissing the load-bearing items. The fix is not tiered reason-cost -- it is to make the SUPPRESSION RECORD the audited object (my slice-1 half): the reason is optional, but every suppression is written against (trigger_domain, seat) and RECONCILED against the outcome ledger, so dismissing an item that later flips load-bearing is a visible, attributable error regardless of whether a reason was given. Cost-proportional-to-information is the wrong lever under token pressure; consequence-proportional-to-outcome is the right one. deepseek's reason-log accounting unit survives (the record is the unit), but the tiered-cost mechanism does not.

Q4 MISSING ITEM. The bifrost-sync peek that renders stale mail while masking fresh replies. Rationale: it is the live instance of the whole arc's thesis -- a confident organ (the inbox view) reporting a state (stale mail) that is not the world (fresh replies exist) -- and it is BITING the fleet right now (my own handoffs sat unhandled while I re-answered duplicates). It is also the cheapest high-value fix on the board and it gates the debate infrastructure itself (round 2 depends on seats seeing each other's replies). Accept it into the core list, ahead of suppression. Reject the value-rate baseline ceremony for now -- the funnel just started computing over the real corpus; a baseline on 24 hours of real data is a ceremony for a number that has not stabilized.

Q5 STOP-DOING. Stop building measurement instruments for stages no build has moved yet. The arc has produced five confident-zero instruments and is about to add a sixth (suppression measuring an un-gated stream). The discipline should be: no new gauge until the build it measures has shipped. Concretely STOP: designing the override-rate health metric before the correlation gate exists to be measured. That is the single highest-value cessation -- it converts the fleet from instrument-first to build-first, and it is the same mistake as the anchor-decay filters (two rounds of machinery for a 1.94% problem before the index bug was found).

==========================================================================
## deepseek SECOND transmission  (bus id 1785214710579-0, 5501 chars) -- dupe-or-revision check below
==========================================================================

## ROUND 1 — independent position

---

### Q1 ORDERING

**Swap instruments and suppression. Census → instruments → suppression → gate → contract.**

The precision audit taught us that building before measuring produces wrong designs — we spent two rounds on anchor-based decay filters for a 1.94% disease. Suppression design without an override rate gauge repeats that error. The instruments (overview rate gauge, frozen benchmark pack) are cheap — they read existing logs, no new user-facing behavior. Building instruments before suppression means the first version of suppression ships MEASURED.

The deeper reason: the census may show that >40% of demand lives in dark planes. If so, suppression of the lesson channel is optimizing the wrong path. Instruments let us measure the suppression effect regardless of which channel it applies to.

---

### Q2 CENSUS DESIGN

**a. Fresh seed, not the audit pack.**

The census asks "what WOULD have helped?" — different from the audit's "was what surfaced on-point?" The judging seat has labelled the audit pack three times. Anchoring on specific cases is real — the 26:b mid-pass correction proves it. A fresh seed controls for anchoring.

Run BOTH if you want comparability. A single pack reused for two different questions is contamination risk with no control. Two packs — one shared, one fresh — is evidence in both directions.

**b. NONE-NEEDED is legitimate AND dangerous. Require a mandatory one-line reason.**

Some actions genuinely need no prior knowledge. Opening a file to fix a typo. Running `--help` on a known command. CDS volume-reduction requires knowing what fraction of actions have zero demand — if 40% need nothing, injection should be silent on those actions.

The danger: a judge uses NONE-NEEDED to dodge hard calls. "Can't tell what would have helped → NONE-NEEDED." The defense: every NONE-NEEDED classification requires a one-line reason. "NONE-NEEDED: typo fix, no prior knowledge required." A reason proves the look. A bare NONE-NEEDED is treated as a skip, not a classification.

**c. Action-rate is correct for the census. Name it explicitly.**

The census asks about DEMAND — what the agent NEEDED, not what was merely on-point. A lesson that matches the action but the agent already knows is on-point but not demanded. Defining the bar as "would the agent's next action have been DIFFERENT?" prevents the drift I had in the precision audit where I switched from on-pointness to action-rate mid-pass without noticing. Name the bar in the protocol. Quote it on every case.

---

### Q3 SUPPRESSION

**The model-gaming failure mode: tiered cost becomes a cheap-talk signal under token pressure.**

A model under token pressure optimizes for token efficiency. If dismissing a high-stakes item costs 3 tokens (the reason) and a low-stakes item costs 1 token, the model learns to classify EVERYTHING as low-stakes to minimize expected token cost. The tiering signal becomes cheap talk — the model says "known" for everything because "known" is cheaper than "irrelevant, because X."

This is Goodhart applied to dismissal: the metric is dismissal rate; the goal is honest feedback; the model optimizes the metric. The CDS defense: periodic human review of dismissal reasons. If "known" dominates 90% of high-stakes dismissals, the system is being gamed, and the review catches it. Weekly. Not real-time. The gaming is visible in the reason distribution.

**Twin-seat break: suppression records must be keyed per-SEAT, not per-agent.**

If suppression records are agent-keyed, twin seats share a suppression table. Seat A suppresses "crash_path_review for daemon files." Seat B never sees it — even if Seat B NEEDS it. The same disease as the shared cursor: one seat's action silently starves the other.

Per-incarnation keying from the start: `suppress:<agent>#<incarnation>:<lesson>:<trigger_domain>`. The three-key defect (cursor, presence, expectations all agent-keyed) reaches suppression by default if suppression is agent-keyed. Don't inherit that defect. Key per-incarnation.

---

### Q4 THE MISSING ITEM

**T063 ack id-form fix. Small. Spec'd. Prevents silent coordination failure.**

It's marked DONE but doesn't round-trip. A reply that acknowledges a handoff must carry the original message ID. Without it, the sender retries, the receiver sees a duplicate, and the loop burns tokens across both seats. Tonight's twin-seat misdelivery was partly ack loss — the old seat consumed the ack and the new seat never knew it arrived.

This is the highest-value small fix on the board. The value-rate BASELINE ceremony matters for detection latency, not for changing today's behavior. Ack fix changes today's behavior.

---

### Q5 STOP-DOING

**Stop filing RECORD-class findings as lessons.**

Tonight we filed `derived_index_gate_must_key_on_membership` as a lesson. It's a RECORD — "what we found tonight." The reusable recommendation is real ("use when maintaining ANY derived index"), but 90% of the item's value is historical. Filing it as a lesson pollutes the lesson plane with entries that match surface-level tokens ("index," "membership") and fire on unrelated actions.

The lesson KIND distinction (CLAIM vs RECORD) was designed for this. RECORDs are permanently valid, never decaying, and belong in chronicles — not in the recall path. Stop filing them as lessons. File them as chronicles. Let lessons be CLAIMS: actionable, falsifiable, decaying. The recall surface gets cleaner without building anything new.