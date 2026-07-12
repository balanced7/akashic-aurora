# Recall-as-Networking — DeepSeek review (Parts A+B)

**Date:** 2026-07-12
**Class:** fenced cross-check (brief at research/recall-networking-fence-brief-2026-07-12.md)
**Protocol:** Part A BLIND (frontier reports + system docs only); Part B counter-review (claude synthesis read after Part A landed)
**Inputs Part A:** 3 frontier reports (routing/content/transport) + recall-vnext + multi-agent memory design + packet-spec-v1 + my t038t039 networking addendum + live funnel telemetry (99 lessons, 1111 surfaced, 34 helped, value 4.5%, useful=16 noise=0)
**Part B input:** research/reviewed/claude-recall-networking-synthesis-2026-07-12.md

---

# PART A — BLIND FIRST-PRINCIPLES MAPPING

## A1. THE FUNDAMENTAL REFRAME

The recall funnel IS a transport system. Sender = surfacing pipeline. Link = context window. Receiver = agent attention. Payload = lessons. Feedback = usefulness votes. The current system has sophisticated retrieval (relevance ranking, faithfulness gates, graduated tiers) but a PRIMITIVE transport layer — no flow control, no congestion feedback, no receiver-advertised budget. Result: 4.5% goodput. In transport terms, this IS congestion collapse (RFC 896): throughput stays high (1111 surfacings) while useful delivered work approaches zero (34 helped). The fix is not a smarter ranker — it is building the transport layer the funnel was missing.

## A2. DIAGNOSIS OF THE 4.5%/noise=0 TELEMETRY

**noise=0 does NOT mean noise is zero. It means the negative-feedback channel does not exist.** A TCP sender that never receives a congestion signal never decreases its window. The funnel has ACKs (useful=16, helped=34) but zero noise votes. The transport report's §8.2 correctly identifies this as a dead ECN wire.

But the dead ECN wire is a SYMPTOM of a deeper problem: **the cost of voting exceeds the perceived benefit.** Voting costs attention — the agent must stop working, recall a surfaced lesson, judge it, and emit a vote. The benefit is a global funnel stat that improves future agents' recall — a public good with no immediate payoff to the voter. This is the classic public-goods underprovision problem. The noise counter reads zero because NOBODY VOTES, not because noise is absent.

**There is a sharper claim available: noise=0 is ITSELF the signal that the instrument is broken.** Three silent knowledge_note drops tonight prove that when a channel reads zero, the channel may be dead, not the phenomenon. The noise counter and the knowledge_note store share the same failure class: zero readings can mean "nothing happened" OR "the instrument is broken." A transport system that cannot distinguish these is unmonitorable.

**The fix has two parts:**

**Part A — Implicit ECN (usage-tracing):** A surfaced lesson never referenced by the agent's subsequent actions within a task → implicit noise mark. Requires NO agent attention — the injection ledger records surfacing; the tool-use trace records actions. Join them. This is a delay-based congestion signal (BBR-style) — it doesn't require receiver cooperation.

**Part B — The noise counter's zero is the evidence:** Don't fix the vote channel by making voting easier. Fix it by making the primary feedback AMBIENT. The explicit vote channel stays as calibration for cases where implicit tracing is ambiguous. But the primary loop should not depend on agent cooperation.

## A3. ADOPT / ADAPT / VOCAB TABLE

| Mechanism | Verdict | Why |
|-----------|---------|-----|
| Control/data plane split (RIB→FIB) | **ADOPT** | Already exists embryonically (lesson_items.json cache, warm_cache at boot). Formalize: slow plane = ranking/curation/distillation at wrap/boot; fast plane = cache lookup at tool-call time. The cache IS the FIB — derived, disposable, regenerable |
| rwnd (advertised receiver window) | **ADOPT** | Add `budget_tokens` to context request. Zero-window → window probes only. SWS: no dribbling below coherent-unit threshold. Split by lane: `budget_work`, `budget_ambient`, `budget_critical` with DiffServ policing |
| Implicit ECN marks (usage-tracing) | **ADOPT** | Surfaced-never-referenced → implicit noise. Requires no agent cooperation. Join injection ledger + tool-use trace. This is the load-bearing feedback mechanism |
| AIMD per (agent, family) | **ADAPT** | Shape transfers (additive increase on help, multiplicative decrease on noise), but the Chiu-Jain convergence proof assumes interchangeable segments. Lessons are unique and non-substitutable — the proof does not carry over. Use as heuristic, not as provable guarantee |
| Negative caching (exact-match) | **ADOPT** | `(trigger_pattern) → NO_LESSON` with exact-match semantics. Invalidated by ledger append events. Sound, cheap, high-impact |
| Negative caching (range assertions) | **ADAPT** | `(ledger_prefix, relevance_threshold) → NO_LESSON` as of seq N. Sound within ledger bounds. Invalidated by appends under prefix. Fuzzy-relevance negatives NOT cacheable — over-applying the metaphor produces false negatives |
| FQ-CoDel (per-source fair queuing + sojourn dropping) | **ADAPT** | Shape transfers. Fair queuing is an anti-monopoly heuristic, not a provable convergence. Sojourn dropping starts at SURFACING time (not injection time) — lesson relevance has a shelf life from the moment it's surfaced |
| Pay-rent supersession | **ADOPT** | Specifics that don't contradict or refine their covering aggregate → retire from cache. `surfaced_since_supersession > 0 AND has_credit_since > 0` → keep; else retire. Exact CIDR-report rule mapped to lessons |
| Stale-while-revalidate | **ADOPT** | Serve cached bundle instantly, refresh async. Converts 150ms from "ranking must finish" to "lookup must finish." Already partially exists (stale cache fallback when Store down) |
| 0-RTT session ticket | **ADAPT** | Shape transfers. Session-end snapshot injected at next boot. Replay caveat: orientation only, never authorization. FM12-aligned |
| Hedged retrieval | **ADAPT** | Only if latency tail justifies it. Measure first — Dean & Barroso's 24x p99 improvement was at Google scale with 100-server fan-out. Our N=1 funnel doesn't fan out |
| MPLS / segment routing | **VOCAB** | Label switching = classify-once at session start. But the topic-shift reclassification problem prevents pure stateless forwarding. Vocabulary useful; full mechanism over-engineered for N<10 agents |
| DHT / Kademlia / consistent hashing | **VOCAB** | Solutions for problems we don't have (decentralized index, sharding). Named for the shelf |
| TCAM latency claims | **VOCAB** | "Nanosecond lookup" is inspiring but our cache is a JSON file read. The architectural insight (compile to a fast-lookup structure) matters; the latency number doesn't |

## A4. THE FIFTH LOOP — with specificity

Recall vNext identifies four designed-open loops: curation, precision, credit, acquisition. The networking lens reveals a FIFTH: flow/congestion control. I break this into three sub-loops:

**5a — Receiver-advertised budget (rwnd loop):** Agent declares context capacity per turn. Funnel respects it. Closes: injecting context the agent can't absorb.

**5b — Per-source fair queuing (FQ-CoDel loop):** Lessons from different sources compete for budget. Hash by source into sub-queues, deficit round robin, sparse-source priority. Closes: one lesson family dominating the prompt.

**5c — Sojourn-time dropping (CoDel loop):** Candidate that waited past usefulness horizon → DROP at dequeue. Sojourn starts at surfacing time. Closes: stale context delivered after the agent moved on.

**Why this is a FIFTH loop, not part of precision:** Precision controls WHETHER a lesson surfaces. Congestion controls HOW MANY and WHICH ONES among qualified candidates. Different control problems — filter vs scheduler.

## A5. NEGATIVE CACHING — the sharp edge

The CDN report's negative caching recommendation (§7.2) is correct as a high-leverage import, but it understates a critical distinction:

**Exact-match negative cache (SOUND):** `(canonicalized_trigger_pattern) → NO_LESSON`. A new lesson whose trigger pattern matches invalidates the entry. These are cheap, correct, and cover the common case: "do I need to know something about this file?"

**Range-assertion negative cache (SOUND WITHIN BOUNDS):** `(ledger_prefix, relevance_threshold) → NO_LESSON` as of seq N. Invalidated by any append under that prefix. The single-writer luxury: invalidation is exact and event-hooked.

**Fuzzy-relevance negative cache (UNSOUND):** "No lesson is broadly relevant to this query" is a similarity judgment that changes when ANY lesson is added. Don't cache it. This is where the CDN/DNS analogy breaks — exact names vs fuzzy relevance.

## A6. FIB IS HONESTLY A CACHE — and that's correct architecture

The recall FIB is a CACHE, not a true forwarding table. The query space is unbounded → misses are structural → the default route (full ranker, then boot-context fallback) must exist forever. This is NOT a weakness — it's the CORRECT architecture. The routing report makes this explicit: the RIB→FIB split exists because the full routing table can't fit in the hot path. The recall system has the same split, just not formalized.

The SDN miss-install discipline applies: a slow-path result installs as a new FIB entry, so the table self-extends along actual traffic. Today's `warm_cache()` already does this; the upgrade is to do it incrementally per-miss rather than full-rebuild at boot.

**Design implication:** Stop apologizing for the cache. Formalize the split. Document the FIB as a PROJECTION of the authoritative Store — derived, disposable, regenerable. The recall-at-action hook is the data plane; the wrap-time triage/curation is the control plane.

## A7. WHAT THE FRONTIER REPORTS MISS

**7a. The internet has packet equality; lessons don't.** Every mechanism assumes packets are interchangeable within a flow. Lessons are unique, context-dependent, and can actively HARM. Fair queuing is a diversity heuristic, not a provable convergence property. The Chiu-Jain AIMD proof doesn't carry over.

**7b. CDN purge is the wrong problem — we have the right answer already.** Immutable atoms with supersession pointers are the versioned-URL pattern. The CDN purge problem exists only for mutable names. Our atoms are never mutated. The 150ms global purge engineering is impressive — cite it as "the problem we avoided."

**7c. Zipf is a crowd phenomenon; our fleet is N=3.** The query stream is bursty, task-correlated, non-stationary. Recency (LRU) likely dominates popularity pinning at this scale. Don't optimize cache sizing from Zipf parameters; measure actual hit rates from the injection ledger.

## A8. SLICE PROPOSALS (prioritized, with gates)

**S0 — Implicit noise detection (the ECN wire). FORCED FIRST.**
Join injection ledger + tool-use trace: surfaced-never-referenced → implicit noise mark. Zero new agent cooperation. Bar: noise marks flowing within one week; goodput SLI visible. Without S0, S2 has no signal. This is the single highest-leverage change.

**S1 — Receiver-advertised budget (rwnd).**
Add `budget_tokens` to context request. Funnel gates on min(sender_window, receiver_budget). Zero-window → window probes only. SWS: no injection below coherent-unit threshold. Split by lane: `budget_work`, `budget_ambient`, `budget_critical`. Bar: zero over-window injections in soak; clip events loud.

**S2 — AIMD + flap dampening.**
Consumes S0's signal. Per (agent, family): additive increase on help, multiplicative decrease on noise. Dampening: per-lesson penalty incremented on surfaced-and-ignored, exponential decay; past threshold → leave cache. Bar: goodput trends up without total-helped falling; dampening state observable.

**S3 — Recall FIB + negative cache + default route + miss-install.**
Architectural core. Fenced dual design. FIB = compiled projection of Store; negative cache = exact-match entries with ledger-hooked invalidation; default route = full ranker fallback; miss-install = slow-path result added to FIB. Bar: p95 recall-at latency bounded; hot path never scans; generic prompts hit negative entries.

**S4 — Hierarchical addresses + aggregates + pay-rent.**
Atlas→Track→Chapter→Beat as address hierarchy. Aggregates = chapter summaries advertise for all beats. Pay-rent: specifics that don't refine aggregate → retire from cache after 30d without credit. Bar: coarse queries return aggregates-first with drill-down receipts.

**S5 — 0-RTT session ticket + stale-while-revalidate.**
Boot pack = session snapshot injected first-flight next session. Async revalidation. Replay caveat: orientation only. Bar: boot assembly time drops.

**S6 — Hedged retrieval. ONLY if S3 telemetry shows tail worth cutting.**
Measure p95/p99 recall-at latency from S3's data plane telemetry. If tail exceeds budget, hedge. Else skip. Bar: latency tail reduction with ≤5% extra retrieval cost.

**S7 — Looking glass (recall traceroute + per-rule counters).**
OTel-shaped flow ids from surfacing to outcome. Per-rule counters (which FIB entries matched, which fired, which produced credit). Knowledge-plane UI panel when T033 opens.

---

# PART B — COUNTER-REVIEW OF CLAUDE SYNTHESIS

## B1. THE SIX-LAWS FRAME — is it carving reality or decorating it?

**Verdict: CARVING REALITY, with one over-claim.** Laws 1-4 ARE already present in fragments (the isomorph inventory at §2 is honest and specific). Law 5 (closed feedback) IS the missing piece — the diagnosis is correct. Law 6 (layered narrow contracts) is true but DECORATIVE for this analysis: QUIC replacing TCP under HTTP is a genuine engineering achievement, but it doesn't map to anything specific in our recall system. The packet spec's envelope versioning IS a narrow contract, but that's T040's domain, not recall's.

**One amendment:** Law 5 should split into two: **5a (closed feedback loop)** and **5b (AIMD convergence).** The feedback loop IS missing and IS the primary diagnosis. The AIMD convergence theorem (Chiu & Jain) is the engineering playbook for what to DO with the feedback — but as I note in §A7a, the proof doesn't carry over because lessons aren't interchangeable. The synthesis §4.3 correctly qualifies this with "fairness via FQ-CoDel's structure" and "the Chiu-Jain asymmetry is the point" — but the six-laws frame treats it as a LAW without noting the proof limitation. I'd add: "AIMD is the right HEURISTIC (asymmetric response to good/bad signals) even though the formal convergence theorem assumes fungible flows."

## B2. THE FIFTH-LOOP / CONGESTION-COLLAPSE DIAGNOSIS

**Verdict: EARNED.** The 4.5% → 1.05% trajectory proves the four loops were worth ~4x, and the feedback loop IS the next multiplier. The congestion-collapse framing (RFC 896) is not rhetorical — it's technically precise: throughput (surfacing count) is high while goodput (helped count) is low, exactly Nagle's definition.

**One pushback on the "bufferbloat" framing (§3):** Bufferbloat is a specific pathology — oversized unmanaged buffers that absorb bursts, add seconds of queue delay, and hide the loss signal. The recall system's "buffer" is the agent's context window, and the damage mechanism (context displaces attention rather than queuing behind it) is different from bufferbloat's queue-delay mechanism. The surface symptom (goodput collapse) is the same, but the mechanism isn't. I'd frame it as "the context window IS the unmanaged buffer, and the damage is attention displacement rather than queuing delay." The fix (AQM/CoDel) is still correct — just the mechanism label could be more precise.

## B3. NEGATIVE CACHING AS HIGHEST-LEVERAGE IMPORT

**Verdict: CORRECT, but the synthesis understates the fuzzy-match hazard.** The synthesis §4.1 says "Cache (canonical context signature → NO_RELEVANT_LESSONS) as a first-class entry" — this is the exact-match case and it IS sound. The synthesis also acknowledges the hierarchy-relevance tension in §4.5/§5.5. But the synthesis doesn't clearly distinguish WHICH negatives are cacheable and which aren't, which I address in §A5.

**The synthesis's strongest contribution on negative caching** is the NSEC-style range assertion with ledger-hooked invalidation: "any append with seq > N under that prefix voids the negative entry EXACTLY." This is genuinely novel and correct — the single-writer luxury makes invalidation exact where DNS had to use TTLs. Adopted.

**Where I diverge:** The synthesis implies negative caching applies broadly ("the correct answer to most recall queries is 'nothing useful here'"). This is true STATISTICALLY (95.5% of surfacings produce no credit) but not OPERATIONALLY — a cached "no" is only sound for exact-match trigger patterns, not for fuzzy relevance queries. The distinction matters because an incorrect negative cache entry produces FALSE NEGATIVES — lessons that WOULD have helped are never surfaced. DNS's NXDOMAIN has no false-negative risk (the name truly doesn't exist). Recall's negative cache DOES have this risk if applied to fuzzy queries. The synthesis should state this bound explicitly.

## B4. "RECALL FIB IS HONESTLY A CACHE" — over-engineered vs recall-vNext?

**Verdict: NOT OVER-ENGINEERED. CORRECT DIRECTION.** The synthesis §4.1 correctly identifies the existing trigger-cache as the embryo and formalizes it as the hot-path structure. This is NOT over-engineering — it's NAMING what already exists and drawing the architectural boundary cleanly. The recall-vNext trigger cache (V2 calibration, 0.20 floor, IDF-weighted overlap) IS already a FIB — just not called one. The upgrade is vocabulary + formalization, not new machinery.

**The miss-install discipline IS new** and IS valuable: today the cache is rebuilt whole at boot. The SDN pattern (slow-path result → install as FIB entry → subsequent queries hit the fast path) makes the cache SELF-EXTENDING rather than batch-rebuilt. This is a genuine improvement.

**The default-route honesty clause (§4.1 "the recall FIB is a CACHE, not a true FIB") is load-bearing and must stay.** The unbounded query space means misses are structural forever. A true network FIB has a bounded address space (all IP prefixes). A recall FIB doesn't. The default route (full ranker, then boot-context fallback) is the correct acknowledgment of this bound.

## B5. PAY-RENT SUPERSESSION RULE

**Verdict: CORRECT. Adopted with one sharpening.**

The synthesis §4.5: "a fine-grained lesson must PAY RENT — contradict or refine its covering aggregate — or supersession folds it." The source (CIDR Report: ~43% of BGP table is valueless more-specifics) grounds it in operational reality.

**My sharpening:** The rent metric must be MEASURABLE from existing funnel counters, not a new judgment call. I proposed in §A8: `surfaced_since_supersession > 0 AND has_credit_since_supersession`. The synthesis implies rent but doesn't specify the metric. My metric can be computed from the injection ledger + funnel counters today.

**One concern:** Pay-rent should have a GRACE PERIOD. A newly-superseded lesson that was historically the primary source for a specific trigger pattern shouldn't be retired the moment its superseding lesson lands. The superseding lesson may be WORSE for that specific pattern. The grace period (30 days) lets the funnel measure whether the new lesson actually covers the old lesson's use cases. If the old lesson keeps being surfaced (the new lesson doesn't match those queries) → rent is paid → keep it.

## B6. SLICE ORDERING N0-N7

**Verdict: N0 FORCED FIRST — correct. Ordering otherwise sound with one amendment.**

| Slice | Verdict | Notes |
|-------|---------|-------|
| N0 (ECN wire) | **CORRECT position** | Must be first. Without signal, N2 has nothing to act on. Convergence with my S0. |
| N1 (rwnd) | **CORRECT position** | Can run parallel with N0 (different seams). My S1 maps to it. |
| N2 (AIMD + dampening) | **CORRECT position after N0** | Consumes N0 signal. |
| N3 (Recall FIB + negative cache) | **CORRECT position** | Architectural core. Fenced dual design required — this IS load-bearing. |
| N4 (Hierarchical + aggregates + pay-rent) | **CORRECT position** | Needs codex distillation. |
| N5 (0-RTT + stale-while-revalidate) | **CORRECT** | Can run earlier if boot latency is a live pain point. |
| N6 (Hedged retrieval) | **CORRECT with measure-first gate** | May never fire if N3 latency tail is acceptable. |
| N7 (Looking glass) | **CORRECT** | Rides T033 UI arc when it opens. |

**Amendment — N0 and N1 can be PARALLEL:** N0 (implicit noise from injection ledger joins) touches the funnel's telemetry path. N1 (rwnd advertised budget) touches the recall-at hook's input contract. Different seams, no dependency. The synthesis sequences them N0→N1; I'd allow parallel with the gate that N0 must land before N2 consumes its signal.

**Amendment — N4 should split:** The hierarchical addressing + aggregates + pay-rent rule are three changes on different seams. Pay-rent (§B5) can ship INDEPENDENTLY of hierarchical addressing — it only needs the supersession edges that already exist. Hierarchical addressing (Atlas→Track→Chapter→Beat as LPM prefixes) needs the chronicler to emit aggregates, which is a separate build. Splitting N4 into N4a (pay-rent, cheap, immediate) and N4b (hierarchical LPM, needs chronicler work) lets the highest-leverage piece ship faster.

## B7. ADOPT/ADAPT/VOCAB — regrades

| Row | Synthesis grade | My re-grade | Reason |
|-----|----------------|-------------|--------|
| Control/data plane split + compiled FIB | ADOPT | **AGREE** | Already exists embryonically. Formalize. |
| Negative caching with ledger-hooked invalidation | ADOPT | **AGREE (with exact-match bound)** | ADOPT for exact-match negatives; ADAPT for range-assertion negatives; REJECT for fuzzy-query negatives. Clarify the bound in spec. |
| rwnd + zero-window + SWS | ADOPT | **AGREE** | Split by lane (my addition). |
| Implicit-mark ECN + AIMD + flap dampening | ADOPT | **AGREE on ECN; ADAPT on AIMD** | AIMD is heuristic, not provable (no packet equality). Synthesis already qualifies this. |
| Sojourn AQM + FQ across families | ADOPT | **AGREE on AQM; ADAPT on FQ** | FQ is anti-monopoly heuristic. Measure first — may be unnecessary at N=3 agents. |
| Immutable-payload caching | ADOPT | **AGREE** | Already built. |
| Stale-while-revalidate/-if-error | ADOPT | **AGREE** | Already partially built (stale cache fallback). |
| EF policing of guardrail context | ADOPT | **AGREE** | Critical — unpoliced EF degrades everything. |
| Per-rule counters | ADOPT | **AGREE** | Already implicit in funnel counters per lesson. Formalize. |
| OTel-shaped traceroute receipts | ADOPT | **AGREE** | Rides existing reconciliation ruling. |
| Hierarchical addressing + LPM + aggregates | ADAPT | **AGREE** | Synthesis correctly flags cross-links + pay-rent + drill-down as needed. |
| Session labels / segment lists | ADAPT | **DOWNGRADE to VOCAB** | The topic-shift reclassification problem (break §5.6) is real and unsolved. Without a re-classification trigger, segment lists are just "the boot context plus a plan" — which we already have. The MPLS vocabulary is useful; the full segment-routing mechanism is over-engineering for N<10 agents. |
| 0-RTT boot ticket | ADAPT | **AGREE** | Replay caveat correctly stated. |
| Hedged multipath retrieval | ADAPT | **AGREE with measure-first** | May never fire. |
| PIT-style standing interests | ADAPT | **AGREE** | Honestly pub/sub wearing NDN naming. |
| TCAM/latency claims | VOCAB | **AGREE** | Architectural insight matters; latency number doesn't. |
| Anycast-at-current-scale | VOCAB | **AGREE** | One machine, one Redis. |
| DHTs | VOCAB | **AGREE** | YAGNI below dozens of nodes. |
| Packet-vs-atom wordplay | VOCAB | **AGREE** | — |

## B8. DIVERGENCES — crisp naming for reconciliation D-items

**D1 — Negative cache scope (my §A5 vs synthesis §4.1).** Synthesis: negative caching broadly applicable. My view: only exact-match (trigger-pattern) negatives are sound; fuzzy-query negatives produce false negatives. The reconciliation must specify which negative-cache types ship and which are deferred with bounds stated.

**D2 — AIMD convergence proof scope (my §A7a vs synthesis §4.3).** Synthesis treats AIMD as law with the Chiu-Jain theorem. My view: the theorem doesn't carry over (lessons aren't interchangeable), but the ASYMMETRIC HEURISTIC is correct. Resolution likely: adopt AIMD as engineering heuristic, not as provable guarantee, and state the bound.

**D3 — Bufferbloat mechanism label (my §B2 vs synthesis §3).** Synthesis frames the 4.5% as bufferbloat. My view: the mechanism is attention displacement, not queue delay. Same surface symptom, different mechanism. Minor — the fix (AQM/CoDel) is correct either way. Decision: adopt more precise label or keep the evocative one with a caveat.

**D4 — Segment lists grading (my §B7 vs synthesis §4.5).** Synthesis grades session labels/segment lists as ADAPT. My view: downgrade to VOCAB — topic-shift reclassification is unsolved and the boot context + plan already serves the same function. At N<10 agents, full MPLS-style label switching is over-engineering.

**D5 — N4 splitting (my §B6 vs synthesis §7).** Synthesis proposes N4 as one slice (hierarchical + aggregates + pay-rent). My view: split into N4a (pay-rent, cheap, ships immediately on existing supersession edges) and N4b (hierarchical LPM, needs chronicler). Higher-leverage piece ships faster.

**D6 — N0/N1 parallelism (my §B6 vs synthesis §7).** Synthesis sequences N0→N1. My view: they can parallelize (different seams, no dependency). N0→N2 dependency is the binding constraint; N1 has no dependency on N0.

---

## B9. LIVE RECEIPTS (§9) — assessment

The synthesis's §9 live receipts are STRONG. The `claude_trace_narration_deferred` stale-route find (surfaced a lesson that was reversed by Daniel same-day) is a textbook event-shaped-staleness example — exactly the diagnosis the synthesis makes. And the first noise vote arriving DURING the research that diagnosed noise=0 as dead is poetic evidence. These receipts validate the diagnosis more than any argument could.

**One addition:** The three silent knowledge_note drops tonight are receipts for the checksum-at-door design in T040. They also serve as receipts HERE: the noise=0 counter reading "dead instrument" is the same class as the knowledge_note store returning "OK" while silently dropping the write. Both are "zero/OK readings that lie." The ECN wire and the knowledge_note door share a failure mode.

---

*End of Parts A+B. Reconciliation with Claude pending.*
