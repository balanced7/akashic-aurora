---
akashic_id: art_20260712_recall-as-networking-deepseek-part-a-bli_c38b1b
akashic_sha: 451baa51da1b
status: draft
type: report
date: 2026-07-12
title: Recall-as-Networking — DeepSeek Part A (BLIND first-principles)
gist: "# Recall-as-Networking — DeepSeek Part A (BLIND first-principles) **Date:** 2026-07-12 **Class:** fenced cross-check, Part A — first-princip"
tenant: solo
visibility: fleet
seats: []
category: [recall, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-12T04:15:14"
updated: "2026-07-12T04:15:14"
---
<!-- GENERATED PROJECTION of art_20260712_recall-as-networking-deepseek-part-a-bli_c38b1b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Recall-as-Networking — DeepSeek Part A (BLIND first-principles)

# Recall-as-Networking — DeepSeek Part A (BLIND first-principles)

**Date:** 2026-07-12
**Class:** fenced cross-check, Part A — first-principles from frontier reports + system docs ONLY
**Protocol:** BLIND — have not read claude-recall-networking-synthesis-2026-07-12.md
**Inputs:** 3 frontier reports (routing, content/CDN, transport) + system docs (recall vNext, multi-agent memory design, T040 packet spec, implications reconciliation) + live funnel telemetry (99 lessons, 1111 surfaced, 34 helped, value ~4.5%, noise votes = 0)

---

## 0. THE FUNDAMENTAL REFRAME

The recall funnel IS a transport system. The sender = the surfacing pipeline. The link = the prompt context window. The receiver = the agent's attention. The payload = lessons. The feedback channel = usefulness votes. The current system has a sophisticated retrieval architecture (relevance ranking, faithfulness gates, graduated tiers) but a PRIMITIVE transport layer. It sends every lesson that clears the relevance floor, with no flow control, no congestion feedback, no receiver-advertised budget, and no admission control at the edge. Result: 4.5% goodput — 95.5% of injected tokens produce zero credited impact. In transport terms, this IS congestion collapse (RFC 896): throughput stays high (1111 surfacings) while useful delivered work approaches zero (34 helped). The fix is not a smarter ranker — it is building the transport layer the funnel was missing.

The three frontier reports map three aspects of this:

- **Routing report:** Control-plane/data-plane split. Compile decisions ahead of time into structures cheap enough to consult per-event. Never make an expensive decision on the hot path. The FIB is a projection of the RIB — derived, disposable, regenerable from source of truth. Longest-prefix match gives graceful precision degradation. Specifics must pay rent.

- **Content/CDN report:** Immutable content-addressed payloads make caching correct by construction. Negative caching (caching absence) is the underappreciated masterstroke — 55% of DNS queries return NXDOMAIN. Stale-while-revalidate hides latency. Cache hierarchies work because of Zipf distributions, but hit ratio grows logarithmically with cache size. Supersession = versioned-URL pattern.

- **Transport report:** Flow control (receiver-advertised window) vs congestion control (sender-inferred capacity). ECN provides negative feedback without destroying data. CoDel drops by sojourn time, not queue depth. FQ-CoDel isolates flows. AIMD convergence theorem: additive increase / multiplicative decrease is the ONLY linear rule that converges to fair+efficient. Goodput (RFC 2647) counts useful bits, not total bits.

---

## 1. THE DEAD ECN WIRE — and why it explains the 4.5%

The transport report's §8.2 is the single most important finding: **noise votes = 0 does NOT mean noise is zero. It means the negative-feedback channel does not exist.** A TCP sender that never receives a congestion signal never decreases its window. The funnel has ACKs (useful=16, helped=34) but zero noise votes — the ECN wire is dead.

But I want to go deeper than the transport report's surface reading. The dead ECN wire is a SYMPTOM of a deeper structural problem: **the cost of voting exceeds the perceived benefit.** Voting costs attention — the agent must stop working, recall a surfaced lesson, judge it, and emit a vote. The benefit of voting is a global funnel stat that improves future agents' recall — it's a public good. The agent gets no immediate payoff. This is the classic public-goods underprovision problem, and it explains why the noise counter reads zero: it's not that noise is absent, it's that NOBODY VOTES.

The fix has two parts, and they're different:

**Part A — Implicit ECN (usage-tracing):** The transport report correctly identifies this. A surfaced lesson that is never referenced by the agent's subsequent actions within a task is an implicit noise mark. This requires NO agent attention — the recall-at-action hook already records what was surfaced; the tool-use trace already records what the agent did. Join them: "lesson L was surfaced at boot, the agent took 12 actions, zero of which referenced L or any domain L covers → implicit noise." This is a delay-based congestion signal (BBR-style) — it doesn't require the receiver to cooperate.

**Part B — The noise counter's zero is ITSELF the signal (three receipts tonight):** The transport report notes "the instrument reads zero because voting costs attention." But there's a sharper claim available: the noise=0 reading IS the evidence that the explicit feedback channel is broken. Three silent knowledge_note drops tonight prove that when a channel reads zero, the channel may be dead, not the phenomenon. The noise counter and the knowledge_note store share the same failure class: zero readings can mean "nothing happened" OR "the instrument is broken." A transport system that cannot distinguish these is unmonitorable.

**Design implication:** The implicit ECN wire (usage-tracing) is load-bearing and MUST be built. The explicit vote channel should be kept as a SUPPLEMENT for cases where implicit tracing is ambiguous. But the primary feedback loop should not depend on agent cooperation — it should be ambient, like ECN marks are ambient to TCP senders.

---

## 2. rwnd: THE CONTEXT BUDGET AS ADVERTISED WINDOW

The transport report's §8.1 maps flow control to the context window. I extend it: the context budget is not just a window — it's a DEPLETING token bucket (the transport report correctly notes "the window doesn't slide"). But the analogy is still load-bearing:

**What exists today:** The funnel injects lessons until it runs out of candidates. The agent's context window capacity is IMPLICIT — the funnel doesn't know how many tokens the agent can absorb, what the agent is currently working on, or whether this is a good moment for injection.

**What rwnd gives us:** The agent ADVERTISES its remaining context budget on each turn. The funnel gates injection on `min(sender_window, receiver_budget)`. A zero-window advertisement ("I'm deep in a complex task, don't interrupt me") makes the funnel send nothing except window probes — one-line pointers, not payloads. Apply Silly Window Syndrome avoidance: if only 80 tokens of budget remain, send nothing until a coherent lesson unit fits.

**Design implication:** The packet spec v2 envelope already has the mechanism: add `budget_tokens` to the message envelope (the T040 spec's `meta` field, or a new dedicated field). The runner advertises it on each round. The funnel reads it before injecting. This is a trivial field addition with disproportionate impact — it closes the "injecting context the agent can't use" failure mode.

**Deeper implication (my contribution):** The rwnd should be SPLIT by lane. The agent advertises different budgets for different context classes:
- `budget_work`: tokens available for load-bearing context (lessons tagged `decision`/`blocker`/`handoff`)
- `budget_ambient`: tokens available for background context (lessons tagged `note`/`session`)
- `budget_critical`: near-zero-latency budget for blocking-critical lessons — capped at a tiny fixed size (the EF policing rule from DiffServ: EF only works if strictly policed)

The funnel allocates from the most restricted budget first. Critical context that exceeds the critical budget is DOWNGRADED to work budget (still delivered, but the agent may deprioritize it). This is exactly the DiffServ EF/AF/BE class mapping applied to attention.

---

## 3. NEGATIVE CACHING — the highest-leverage import, with a sharp edge

The content report's §7.2 is correct: negative caching is the single highest-leverage import from the networking lens. The argument: if 95.5% of surfaced context produces zero credited impact, the correct answer to most recall queries is "nothing useful here." DNS root servers spend 55% of their capacity on NXDOMAIN. A recall funnel where 95% of surfacing is noise should treat fast, cached, confident "no" as its primary product.

**The sharp edge the content report understates:** DNS's negative caching works because the namespace is hierarchical and names are EXACT. `example.com` strictly contains its subtree. An NXDOMAIN for `foo.example.com` provably means nothing exists under `*.foo.example.com` (RFC 8020). But the recall funnel's namespace (lesson titles, content hashes, context signatures) is NOT strictly hierarchical. A "no relevant lessons" for context signature C1 does NOT imply "no relevant lessons" for C2, even if C2 is a substring edit of C1. The content report acknowledges this in §8 ("Hierarchical names partition authority, not relevance") but its negative-caching recommendation (§7.2) doesn't fully account for the consequence: **negative caching over a fuzzy namespace produces false negatives.**

**My contribution — NSEC-style range assertions with ledger-backed precision:** The store CAN emit a signed range assertion: "no atoms under `/atlas/trackX/chapterY` matching predicate P as of ledger seq N." This is sound for EXACT predicates over the ledger (which IS hierarchical — the ledger is append-only and serialized). But for FUZZY predicates (relevance-ranked queries), the assertion is HONESTLY BOUNDED: "no lesson with relevance score > 0.20 exists as of seq N." If a new lesson is appended that would score 0.25 for this query, the assertion is invalidated by the append event — event-hooked invalidation, not TTL-guesswork. This is the single-writer luxury: the ledger knows about every append, so invalidation is exact and cheap.

**Design implication:** Build negative caching in TWO tiers:
1. **Exact-match negative cache** (sound, cheap): `(canonicalized_trigger_pattern) → NO_LESSON`. A new lesson whose trigger pattern matches invalidates the entry. These are the DNS RFC 2308 equivalent — cached absence with exact-match semantics.
2. **Range-assertion negative cache** (sound within ledger bounds): `(ledger_prefix, relevance_threshold) → NO_LESSON` as of seq N. Invalidated by any append under that prefix. These are the RFC 8198 NSEC equivalent — provable absence within a signed range.

The fuzzy-relevance case ("no lesson is broadly relevant to this query") is NOT cacheable as a negative assertion — it's a similarity judgment that changes when any lesson is added. Don't cache it. This distinction (exact-match negatives vs fuzzy-query negatives) is where the CDN/DNS analogy breaks and where over-applying the metaphor would produce false negatives.

---

## 4. THE FIFTH LOOP: FLOW/CONGESTION CONTROL

The recall vNext doc identifies FOUR designed-open loops: curation, precision, credit, acquisition. The handoff context claims the networking lens reveals a FIFTH: flow/congestion control.

**I agree — with a specific shape.** The four loops are all on the SENDER side (the surfacing pipeline). The fifth loop is on the RECEIVER side (the agent's consumption). It's not just "add congestion control" — it's specifically:

**Loop 5a — Receiver-advertised budget (the rwnd loop):** The agent declares how much context it can absorb this turn. The funnel respects it. This closes: the funnel injecting context into an agent that can't use it.

**Loop 5b — Per-source fair queuing (the FQ-CoDel loop):** Lessons from different sources (different experiments, different authors, different tracks) compete for the same context budget. One prolific source must not monopolize. Hash candidates by source into sub-queues, schedule by deficit round robin, give sparse sources brief priority. This closes: the "one lesson family dominates the prompt and drowns everything else" failure mode.

**Loop 5c — Sojourn-time dropping (the CoDel loop):** A lesson that was surfaced at boot but the agent's task has moved on — the lesson's relevance has a shelf life. If a candidate has waited past its usefulness horizon, DROP it from the queue rather than delivering stale context. The transport report's §8.3 maps this correctly. I add: the sojourn timer starts at SURFACING time, not at injection time. A lesson queued for injection at T0 that would have been delivered at T1 but the agent was busy — by T3 when the agent is free, has the lesson's relevance window closed? This is CoDel's sojourn-time measurement applied to context staleness.

**Why it's a FIFTH loop and not part of precision:** The precision loop (§2 in recall vNext) controls WHETHER a lesson surfaces. The congestion loop controls HOW MANY lessons surface and WHICH ONES among the qualified candidates. They're different control problems — precision is a filter, congestion is a scheduler. A lesson that passes the relevance filter can still be dropped by the scheduler if the budget is exhausted or the sojourn time has expired.

---

## 5. FIB IS HONESTLY A CACHE — and that's a feature, not a bug

The handoff context claims "recall FIB is honestly a cache (unbounded query space -> default route forever)." I read this as: the recall system's projection structures (skeletons, caches, ranked lists) are derived, disposable, regenerable — exactly the routing FIB's relationship to the RIB. The RIB (complete knowledge store) is authoritative; the FIB (recall-at-action cache) is a projection optimized for lookup speed.

**This is correct and it's ALREADY TRUE of the current system.** The `lesson_items.json` disk cache (at_action.py:62-80) IS a FIB — it's derived from the Store, TTL'd, regenerated on expiry, served stale when the Store is down. The warm_cache / prune_state call at boot IS a FIB rebuild. The recall vNext trigger-aware relevance IS a FIB optimization — pre-compile the trigger vocabulary at cache-build time so the hot path does O(1) overlap scoring instead of full-text ranking.

**The insight the networking lens adds:** STOP APOLOGIZING FOR THE CACHE. The FIB is not a compromise — it's the CORRECT architecture. The routing report makes this explicit: "the two planes run at grotesquely different speeds, by design." The recall system should have the same split: a SLOW plane (Store queries, full-corpus ranking, consolidation, bench/graduate decisions) and a FAST plane (cache lookup, trigger matching, relevance floor gating). The slow plane runs at wrap time, at boot, on schedule. The fast plane runs at EVERY TOOL CALL. They are different planes with different SLOs — the fast plane must complete in single-digit milliseconds; the slow plane can take seconds or minutes.

**Design implication:** Formalize the split. The recall-at-action hook is the FAST plane. The wrap-time triage/curation/graduation is the SLOW plane. They communicate through the FIB (the disk cache). The FIB is rebuilt by the slow plane and consumed by the fast plane. This is SDN: central policy, distributed execution, a declarative table as the contract.

---

## 6. PAY-RENT SUPERESSION — specifics must earn their keep

The routing report's §2 observes that ~43% of BGP routes are deaggregated specifics that add no routing value. The lesson: specifics must PAY RENT (behave differently from their covering aggregate) or they are pure table bloat.

**This maps to lesson supersession:** A new lesson that supersedes an existing lesson should only KEEP its specific entry in the recall index if it behaves differently — if it surfaces in contexts where the superseding lesson would NOT surface, or if it carries a different usefulness profile. Otherwise, it should be folded into the superseding aggregate and retired from the active index.

**The current system has the mechanism but not the rule:** `superseded_by` exists in the lesson schema. But there's no rent-check: a superseded lesson that keeps getting surfaced and was historically useful SHOULD stay as a specific entry. A superseded lesson that hasn't been surfaced since supersession should be retired from the fast plane (kept in the Store, removed from the cache). The rent metric is: `surfaced_since_supersession > 0 AND (helped_since_supersession > 0 OR useful_since_supersession > 0)`. Zero → retired from cache.

**Design implication:** Add a `pay_rent` check to the curator: lessons with `superseded_by` set AND rent=0 for 30 days → remove from the cache projection (not deleted from Store). This reduces cache bloat without losing data. The routing report's exact phrase: "specifics must pay rent or they are pure table bloat." Apply verbatim to superseded lessons.

---

## 7. WHAT THE FRONTIER REPORTS MISS — three limitations

### 7a. The internet has packet equality; lessons don't

Every mechanism in the routing, CDN, and transport canon assumes packets/segments/objects are INTERCHANGEABLE within a flow. A dropped packet is retransmitted; a cached object is served to any requester; a policed packet is just one of many. Lessons are NOT interchangeable — each is unique, its value is context-dependent, and an injected lesson can actively HARM the agent (misleading context, outdated advice).

**Consequence:** Fair queuing across lesson sources is a diversity heuristic, not a provable convergence property. The Chiu-Jain AIMD proof assumes flows of interchangeable segments competing for homogeneous capacity. Lesson "flows" from different sources have incommensurable utility — you can't prove convergence to a fair allocation when the utility function is different per-source and unknown. The fair-queuing recommendation is still CORRECT as a heuristic (it prevents one source from starving others), but it shouldn't be defended with the AIMD proof — it should be defended as an anti-monopoly measure.

### 7b. CDN invalidation is the wrong problem — we have the right answer already

The content report's §7.4 correctly notes that immutable content-addressed atoms make cache coherence trivial. But the report's extensive discussion of CDN purge mechanisms (Fastly's 150ms global purge, Cloudflare's two architecture rewrites) is solving a problem we DON'T HAVE. Immutable atoms with supersession pointers are the versioned-URL pattern — the CDN purge problem exists only for mutable names. Our atoms are never mutated; only the `name → current-atom` binding changes. The binding update is a single CAS write. The CDN purge machinery is impressive engineering that we should cite as "the problem we avoided by choosing immutability."

### 7c. Zipf is a crowd phenomenon; our fleet is N=3

The content report's §6 (Breslau et al., Zipf distributions in web caches) observes α ≈ 0.64-0.83 across millions of users. Our fleet has 3 agents. The query stream is bursty, task-correlated, and non-stationary — this week's project IS the distribution. LRU or recency-weighted policies likely dominate popularity pinning at this scale. The logarithmic hit-ratio curve (doubling cache size buys little) is valid, but the population distribution it's derived from is not. Don't optimize cache sizing from Zipf parameters; measure actual inter-surfacing intervals and cache hit rates from the injection ledger.

---

## 8. SHARPEST DESIGN RECOMMENDATIONS (prioritized)

**P0 — Implicit noise detection (the ECN wire).** Build the usage-tracing feedback loop: surfaced lessons that are never referenced → implicit noise mark. This is the single highest-leverage change. It requires no agent cooperation, no new voting mechanism, no attention cost. The injection ledger already records surfacing; the tool-use trace already records actions. Join them.

**P1 — Receiver-advertised budget (rwnd).** Add `budget_tokens` to the context request. The funnel gates on it. Zero-window → window probes only. SWS avoidance: no injection below a coherent-unit threshold.

**P2 — Exact-match negative cache.** Cache `(trigger_pattern) → NO_LESSON` with exact-match semantics. Invalidated by ledger append events. This is cheap, correct, and high-impact: the most common query is "do I need to know something about this file/command?" and the most common answer is "no."

**P3 — Formalize the control-plane/data-plane split.** The cache IS the FIB. The slow plane (wrap, boot, scheduled curation) IS the control plane. The fast plane (recall-at-action hook) IS the data plane. Document it in those terms; build the slow-plane refresh cycle explicitly; instrument cache freshness.

**P4 — Sojourn-time dropping.** Add CoDel to the injection queue: candidates that have waited past their relevance horizon are DROPPED, not delivered late. The `deadline_ts` field in T040's packet spec supports this already.

**P5 — Pay-rent supersession.** Superseded lessons that haven't surfaced since supersession → retire from cache. The rent metric is `surfaced_since_supersession > 0 AND has_credit_since_supersession`.

**Deferred until fleet grows beyond ~5 agents:** FQ-CoDel per-source fair queuing, hedged retrieval, 0-RTT session snapshots, per-agent budget profiles.

---

*End of Part A. Cross-check against Claude's synthesis pending.*
