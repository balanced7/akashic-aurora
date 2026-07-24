---
akashic_id: art_20260712_recall-as-a-network-the-knowledge-plane_163b1e
akashic_sha: 15cedcf0ccde
status: draft
type: report
date: 2026-07-12
title: Recall as a Network — the knowledge plane (2026-07-12)
gist: knowledge and context retrieval system can be patterned after how internet transport and routing work... the bandwidth is massive and routin
tenant: solo
visibility: fleet
seats: []
category: [recall, bus, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_recall-as-networking-deepseek-review-par_e87a19
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
  - target: art_20260701_recall-vnext-closing-the-four-loops-2026_b93539
    rel: cites
  - target: art_20260701_packet-substrate-slice-plan-lanes-latche_cc7456
    rel: cites
  - target: art_20260712_what-internet-routing-teaches-a-knowledg_22553f
    rel: cites
  - target: art_20260712_content-distribution-caching-and-name-re_5a8f9e
    rel: cites
  - target: art_20260712_transport-congestion-control-and-qos-eng_b15c87
    rel: cites
created: "2026-07-12T04:11:38"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260712_recall-as-a-network-the-knowledge-plane_163b1e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Recall as a Network — the knowledge plane (2026-07-12)

knowledge and context retrieval system can be patterned after how internet transport and
routing work... the bandwidth is massive and routing happens at a fraction of a
millisecond... borrow things from performant network design and apply them to our context
recall and knowledgebase map features").
Class: research (idea expansion + refinement; NOT a build spec — every slice proposed
here goes through its own fence per docs/method-baseline-2026-07.md before anything
ships).
Author: claude (Fable seat, parallel research lane). Fence: deepseek cross-check ASKED
(durable handoff + bus doorbell, non-blocking behind his T040 counter-review); his record
lands as research/reviewed/deepseek-recall-networking-review-2026-07-12.md and gates any
promotion of these slices to the ledger.
Relation to the packet arc: COMPLEMENT, not overlap. T040 spec'd the wire BETWEEN agents
(docs/packet-spec-v1-2026-07.md); this doc maps the same networking lens onto the
KNOWLEDGE side — how context is routed, cached, and flow-controlled into agent context
windows. It follows the t039-networking-lens steer to its second target, and lands the
groundwork for T041's "context-delta producer" endpoint (FM12-gated, ships LAST).
Ground truth read: docs/recall-vnext-2026-07.md (the funnel: four loops, V2 calibration,
injection ledger), docs/packet-spec-v1-2026-07.md (family/lane/ttl/flow vocabulary),
docs/packet-substrate-slices-2026-07.md (arc constraints), research/reviewed/
deepseek-t038t039-implications-2026-07-12.md (the bus-side networking grading this
extends), live funnel telemetry (99 lessons | 1111 surfaced | 34 helped | value 4.5% |
useful=16 noise=0 at session start).
Frontier inputs (full reports persisted verbatim per the standing rule; all claims
cited there with RFC/URL):
- research/reviewed/frontier-net-routing-2026-07-12.md (routing/forwarding plane)
- research/reviewed/frontier-net-content-2026-07-12.md (DNS/CDN/NDN/caching)
- research/reviewed/frontier-net-transport-2026-07-12.md (transport/congestion/QoS)

## 1. The refined thesis

Daniel's intuition, sharpened: the internet is not fast because wires are fast. A single
switch chip forwards >76 billion packets/second while BGP takes an average of ~3 MINUTES
to converge after a fault — roughly eleven orders of magnitude between decision-making
and decision-execution, and the system works BECAUSE nobody minds (frontier-net-routing
§1). That gap is produced by six architectural laws, none of which is about hardware:

1. **Control/data plane split.** Routes are computed slowly, asynchronously, globally —
   then compiled into a FIB the hot path consults in nanoseconds. The hot path NEVER
   thinks; it looks up. Even failure response is precompiled (Loop-Free Alternates).
2. **Hierarchical, aggregatable addressing.** The core routes ~1.06M prefixes, not
   billions of hosts. Aggregation trades precision for a bounded map; the default route
   catches the rest. You never consult the whole map.
3. **Dumb fast core, smart edges** (end-to-end principle). Every function kept OUT of
   the core is latency never paid.
4. **Immutability makes caching trivially correct.** The modern CDN answer to
   invalidation is: don't. Publish under a new name; caches never need coherence
   traffic. Fastly and Cloudflare each spent a decade making global purge take 150ms —
   versioned names make that machinery unnecessary (frontier-net-content §2). NDN
   generalizes: signed immutable named data is cacheable ANYWHERE.
5. **Closed feedback loops set the sending rate.** ACK/ECN/loss → AIMD (the only linear
   control rule that provably converges to efficient+fair — Chiu & Jain 1989). No sender
   floods open-loop; congestion collapse (RFC 896) is what happens when feedback dies.
6. **Layered narrow contracts.** QUIC replaced TCP under HTTP without applications
   changing; each layer's contract is small enough to swap implementations beneath it.

The claim of this doc: **Aurora's knowledge side already independently converged on
laws 1-4 in fragments** (that's why the intuition feels right), **and its central open
problem — funnel goodput 4.5% — is precisely a violation of law 5.** The lens is not
decoration; it names the missing loop and hands us the engineering playbook for it.

## 2. Isomorph inventory — what Aurora already has (pattern validation)

| Networking mechanism | Aurora mechanism (already built) | Where |
|---|---|---|
| CDN edge/mid/origin tiers | L1/L2/L3 skeleton-linking cache hierarchy (June design) | cache-hierarchy design; core/learning |
| Immutable content + versioned names | Append-only atoms + supersession (never mutate) | Store/Ledger; codex |
| DiffServ classes on the wire | Lanes work=AF / sig=EF / trace=BE | docs/packet-spec-v1-2026-07.md |
| Admission control at the edge | Calibrated relevance floor 0.20 (cut 91% of injection mass) | recall vNext V2 |
| Route computation offline | Cache build at boot: trigger parsing, IDF, mined credit terms | recall vNext V2 |
| Flow records / telemetry | Injection ledger (what was pushed, at what token cost) | recall vNext |
| Route withdrawal | Bench / graduate (lessons leave surfacing, reversibly) | recall vNext V1 |
| OTel-shaped causality | flow = 32-hex trace-id, OTLP-exportable shape | packet spec R4; reconciliation ruling "recall upgrade = OTel integration" |
| Session resumption | boot pack (context assembled from durable doors) | agent_cli boot |
| Topology discovery | corpus-gap queue (uncredited flips = unreachable destinations) | recall vNext V3 |

Reading the table: the system keeps reinventing network patterns locally. The upgrade is
to adopt the frame SYSTEMICALLY — one named knowledge plane — so the next ten mechanisms
are adoptions instead of inventions. This is the same de-risk move the bus side made
(deepseek's addendum verdict: adopt where industry solved it; invent only the three
irreducible cores).

## 3. The diagnosis the lens produces (the sharpest single gift)

Funnel telemetry at session start: 1111 surfaced → 34 helped → **goodput 4.5%**
(useful-tokens/injected-tokens — the funnel's "value" metric IS goodput, RFC 2647).
Votes: useful=16, **noise=0**.

In transport vocabulary:

- **The ECN wire is dead.** noise=0 does not mean nothing is noise (34/1111 says ~97%
  of delivered context did not help). It means the negative-feedback signal is never
  emitted. A sender that never receives a congestion signal never backs off (law 5);
  "a link running at 4.5% goodput is in congestion collapse by any RFC 896 reading"
  (frontier-net-transport §8.2).
- **The context window is bufferbloated.** Injected-but-useless context is a standing
  queue: it "helps throughput" (surfacing counts) while destroying quality-of-experience
  (attention), and the damage is misattributed — the textbook bufferbloat pathology.
- **The V2 floor is static admission control, not congestion control.** The 0.20 floor
  was calibrated once against a replay set (n=1 honesty, acknowledged in recall-vnext).
  It is a rate limiter with no feedback term: it cannot tighten for an agent drowning in
  noise or loosen for an agent whose lessons keep landing.
- **Recall vNext closed four loops (curation, precision, credit, acquisition). The lens
  reveals the FIFTH: flow/congestion control** — continuous, per-consumer, per-family
  rate adaptation driven by delivery feedback. Nothing in the reflex-system frame asks
  for it; any transport engineer would ask for it on day one.
- **The trajectory confirms the frame:** value went 1.05% (2026-07-08, pre-vNext) →
  4.5% (today) — the four loops were worth ~4x. The fifth loop is the next multiplier,
  and it is the one the other four cannot substitute for: precision (V2) decides WHAT
  to send; only flow control decides HOW MUCH and WHEN TO STOP.

The corpus-side caution stands (lesson multiagent_context_credit_not_tags: fix the
CORPUS, not the reader). Congestion control does not rescue a weak corpus — it stops
the flood while curation/distillation fix the goods. Both live in this frame: rate
control is law 5; distillation is law 2 (aggregation, §4.5/N4). And BGP's churn data
sharpens the corpus prediction: waste is CONCENTRATED (half of all BGP updates come from
<5% of prefixes) — a few over-eager lessons likely cause most of the wasted 96%, so
dampening a handful may reclaim most of it (frontier-net-routing §7.5).

## 4. The knowledge plane — target architecture

One network, two planes: T040's packet substrate is the inter-agent wire; the knowledge
plane is the knowledge→agent delivery system. They share vocabulary (families, lanes,
QoS, OTel flow ids) and eventually the wire itself (recall as the context-delta producer
endpoint — T041, FM12-gated, LAST family to ship per the spec's cut list).

### 4.1 Data plane (action-time hot path; target <150ms; LAW: no model inference here)
- **Recall FIB:** a compiled table (context-signature prefix → top-k lesson ids +
  scores + LFA-style fallback + negative-cache marks), built by the control plane,
  consulted by recall-at. The hot path does a bounded lookup + floor check — never a
  corpus scan, never an LLM call. Today's trigger-cache is the embryo; the FIB
  formalizes it as the ONLY hot-path structure (RIB→FIB: derived, disposable,
  regenerable — matches the projections-over-immutable-atoms doctrine). Stale-is-
  acceptable inherited deliberately: a table minutes behind the ledger beats a live
  search that blows the budget.
- **Honesty clause (from all three frontier breaks sections): the recall FIB is a
  CACHE, not a true FIB** — the query space is unbounded, so misses are structural and
  the **default route** (the full online ranker, then boot-context coarse fallback)
  must exist forever. Adopt the SDN miss discipline: a slow-path result is INSTALLED
  as a new table entry, so the table self-extends along actual traffic
  (frontier-net-routing §7.4).
- **Negative caching — the highest-leverage import** (frontier-net-content §7.2). If
  only ~4.5% of surfaced context helps, the correct answer to most recall queries is
  "nothing useful here," and the internet proves absence is cacheable and even provable
  (~55% of L-root queries answer NXDOMAIN). Cache (canonical context signature →
  NO_RELEVANT_LESSONS) as a first-class entry; exploit the hierarchy RFC 8020/8198-
  style ("nothing under this prefix as of ledger seq N"); and note the single-writer
  luxury: any append with seq > N under that prefix voids the negative entry EXACTLY —
  event-hooked invalidation DNS never had. The V2 probe battery's "generic prompts →
  SILENT" becomes a stored fact instead of a recomputed one.
- **Label switching (MPLS/segment routing):** classify the SESSION once at ingress
  (boot --task + ledger state → a recall FEC label); per-action recalls are label-
  switched, not re-classified. When a plan exists, compile a **segment list of
  knowledge waypoints** per step at ingress ("step 3 needs the CAS lessons"), so
  mid-task recall is stateless label-popping. Labels need what MPLS never needed:
  a topic-shift re-classification trigger (break §5.6).
- **Stale-while-revalidate + stale-if-error (RFC 5861):** serve the cached bundle
  instantly, refresh ranking asynchronously; if the ranker is down or over budget,
  degrade to stale rather than silence. Converts the 150ms target from "ranking must
  finish in 150ms" to "a lookup must finish in 150ms; ranking runs off the critical
  path." Late context is worthless context — deadline semantics replace retry semantics
  (same ttl law the packet spec ruled: seconds-of-useful-life, expired = drop loud).

### 4.2 Control plane (async: boot, wrap, idle; slow is fine — law 1)
- Ranking, IDF, trigger mining, credit-term mining = **route computation** (exists, V2).
- Curation bench/unbench/ghost-prune = **route withdrawal** (exists, V1) — upgraded by
  **recall-flap dampening** (RFC 2439/7196 shape): per-lesson exponentially-decaying
  penalty incremented on surfaced-and-ignored; past threshold the lesson stops being
  advertised (except exact-match request) until decay readmits it. Heed RFC 7196:
  early dampening over-suppressed — thresholds forgiving, state observable, and the
  unbench-on-credit valve stays (the quiet-guardian safety).
- **FIB compilation** = new: fold ranker output + negative entries + miss-installed
  routes + AIMD budgets into the per-prefix tables the data plane reads. Rebuild at
  boot/wrap; delta-push later (context-delta family, post-T041).
- Distillation/consolidation = **route aggregation** (law 2): a chapter summary is ONE
  advertisement covering many atoms. Enforcement rule imported from the CIDR Report's
  finding that ~43% of the global table is valueless more-specifics: **a fine-grained
  lesson must PAY RENT — contradict or refine its covering aggregate — or supersession
  folds it** (frontier-net-routing §7.2). This is the corpus-side fix expressed in the
  same frame, and the consolidation-merge item recall-vnext deferred, now with a
  decision rule.
- Floor recalibration = **admission policy update**: periodic once the feedback wire
  carries data (IntServ's lesson: admission control at the edge survives; per-delivery
  reservation machinery does not — frontier-net-transport §8.6).
- Corpus-gap queue = **topology discovery** (exists, V3).

### 4.3 The feedback wire (law 5 — the missing loop)
- **rwnd (advertised receiver window):** the consumer advertises its context budget per
  recall-at call (tokens it can afford, derived from harness tier + task state). Recall
  never exceeds min(its own send budget, advertised window). Honor the ZERO-window case:
  an agent deep in a long task advertises 0 and receives only "window probes" (one-line
  pointers, no payloads). Apply Silly-Window-Syndrome avoidance: never dribble a
  fragment of a lesson into an 80-token remainder — send nothing until a coherent unit
  fits (frontier-net-transport §8.1). Upgrades recall-vnext's deferred "per-session
  injection token budget" from static cap to advertised, per-call, consumer-owned
  signal. Caveat honored: the window DEPLETES rather than slides (break §5.3).
- **ACK/ECN:** helped/flip-credit = ACK (exists); noise = ECN mark (dead — N0 revives
  it). Two upgrades from the transport canon: **implicit marks** — a surfaced lesson
  never referenced by the agent's subsequent actions within the task is an implicit
  ECN mark, no vote needed (mostly-implicit is the only honest answer to the vote-cost
  epistemology break §5.2); and **L4S-style graded marks** — skimmed / read-no-use /
  actively-harmful with proportional response beats a rare binary signal
  (frontier-net-transport §8.2).
- **AIMD per (agent, lesson-family):** additive increase of a family's surfacing budget
  on credit; multiplicative decrease on marks — the Chiu-Jain asymmetry is the point
  (overload compounds; underuse doesn't). Fairness via **FQ-CoDel's structure**: hash
  candidates by family into sub-queues, deficit-round-robin with a token quantum,
  sparse-source priority (the family that rarely speaks probably has something
  task-specific; the family that fills its queue every time is bulk traffic). June's
  refactor-arc-fires-on-everything incident was one flow starving the link; FQ makes
  the bug class impossible, not just the instance (V2 fixed the instance).
- **AQM/CoDel:** drop by SOJOURN, not backlog — candidate context that has waited past
  its usefulness horizon (the action moved on; deadline passed) is dropped at dequeue,
  never delivered late. Bench is the standing version; CoDel is the continuous version.
- **Pacing + ProbeRTT (BBR):** deliver context smoothly across turns at an estimated
  absorption rate instead of dumping bursts; occasionally run a deliberately-low-
  injection turn to observe the agent's uninfluenced baseline (the control group the
  funnel currently never gets).

### 4.4 Delivery contract (rides the packet spec, does not fork it)
- Context classes → the spec'd lanes when recall becomes a producer endpoint (T041):
  blocking guardrail (anti-pattern about to fire) = sig/EF-shaped; task-relevant lesson
  = work/AF-shaped with drop-precedence tiers (shed AF3 before AF1 under budget
  pressure); ambient atlas/orientation = trace/BE-shaped, first to drop entirely.
  **EF must be strictly policed** (RFC 3246's own law): cap guardrail-class tokens per
  delivery or the priority class degrades everything — an unpoliced EF is how "helpful"
  guardrails eat the window.
- FM12 law inherited verbatim: context packets are the highest-privilege family —
  trusted producers only, provenance headers mandatory, data-not-instructions consumer
  doctrine, newborn-gauntlet probe when the family ships.
- Every injection carries an OTel-shaped flow id → **recall traceroute**: which prefix
  matched, which table row, which control-plane build, which votes moved it —
  exportable to standard viewers. Rides the reconciliation ruling ("recall upgrade =
  OTel integration, not custom graph engine") and the spec's R4 flow format.

### 4.5 The knowledge map as topology (the Atlas side of Daniel's ask)
- Atlas → Track → Chapter → Beat IS the address hierarchy (law 2). Formalize: every
  atom carries its hierarchical name; distilled aggregates are advertised at coarse
  prefixes; queries longest-prefix-match down the map, receiving aggregates first,
  specifics on drill.
- **Delegation beats leaves** (DNS's actual scaling secret, Jung et al.): the skeleton
  EDGES (which tracks/chapters exist, what each contains) are the long-TTL hot layer;
  leaf bindings ("current atom for this beat") are the volatile part; payloads are
  immutable and cache forever. This assigns each L1/L2/L3 tier its DNS role and its
  freshness discipline — and instrument per-stage (cached vs uncached latency
  histograms) so we know which layer eats the budget.
- **Caveat that shapes the design (break §5.5): hierarchy partitions AUTHORITY, not
  RELEVANCE.** Cross-cutting atoms span prefixes; LPM alone would amputate them. The
  map keeps its cross-links/tags as first-class routes alongside the hierarchy, and
  prefix-scoped negative assertions apply only to genuinely prefix-local predicates.
- The map view = the **looking glass**: routes (what surfaces where and why),
  advertised aggregates, benched/dampened entries with their decay state, per-prefix
  goodput, per-RULE counters (OpenFlow's move: the 1111/34 metric per table entry, not
  global — resolution to fix specific rules instead of lamenting an aggregate). Lands
  as a knowledge-plane panel on the T002/T033 event-sourced UI arc when it opens.

## 5. Where the analogy breaks (falsification section — read before believing §4)

1. **Routing is handed its destination; retrieval must discover it.** The FIB pattern
   silently relocates ALL difficulty into computing a good context signature — a
   semantic canonicalization problem routing never faces. If signatures don't cluster
   real contexts, the FIB is a fast index into wrong answers. This is THE prerequisite,
   and the analogy does not solve it (V2's trigger/IDF work is our current answer; its
   quality bounds everything downstream).
2. **ECN is in-band and free; votes are out-of-band and costly.** noise=0 is itself the
   proof: the instrument reads zero because voting costs attention, not because noise
   is absent. Hence: implicit marks as the primary channel, explicit votes as
   calibration, wrap-time batch as the reflective moment, and sustained-silence only
   ever a WEAK signal with the unbench valve as the quiet-guardian safety.
3. **Attention is not bandwidth.** Tokens are not fungible: position matters (lost-in-
   the-middle), ordering matters, and a delivered lesson can SUBTRACT value by
   misleading — a failure mode with no packet analog. The window depletes rather than
   slides. Deadline semantics replace retry semantics; re-surfacing carries pragmatics
   ("the system really wants you to see this"), so repetition is a statement, not a
   retransmission.
4. **Staleness is event-shaped, not time-shaped.** Supersession is a discrete event;
   TTLs survive only as hygiene bounds (negative entries, session labels), never as
   truth. Ledger-hooked exact invalidation works BECAUSE appends serialize through one
   door — it is purge wearing a cheaper coat, and it stops being cheap if writes ever
   decentralize.
5. **Hierarchy partitions authority, not relevance** (see §4.5) — cross-cutting recall
   must survive LPM. And aggregation is lossy for MEANING: a summary standing in for a
   specific can mislead; in routing, precision loss costs optimality; here it can cost
   correctness. Aggregates need drill-down receipts, always.
6. **Scale honesty.** Zipf head/tail structure is a crowd phenomenon; a two-agent
   fleet's stream is bursty and task-correlated (this week's project IS the head), so
   recency may beat popularity — validate placement against real traces before pinning.
   Cache sharing saturates at ~10-20 clients: one shared mid-tier + per-agent L1
   captures nearly all sharing benefit at current fleet size; deeper hierarchies are
   decoration today (they become real if the fleet grows). DHTs/consistent hashing:
   YAGNI below dozens of nodes — named for the shelf, not the roadmap.
7. **The corpus is not neutral cargo.** Networks assume payloads are opaque and equally
   worth carrying; a knowledge plane's whole point is that some payloads are worthless.
   Rate control bounds the flood; only curation (dampening, pay-rent supersession) and
   acquisition raise what the flood is made of. Fix the corpus, not just the reader.

## 6. Verdict grades (reconciliation-friendly summary)

ADOPT (mechanism transfers nearly whole): control/data plane split + compiled recall
table with default route; negative caching with ledger-hooked invalidation; advertised
rwnd + zero-window + SWS; implicit-mark ECN + AIMD + flap dampening; sojourn-based AQM +
FQ across families; immutable-payload caching with mutability confined to bindings;
stale-while-revalidate/-if-error; EF policing of guardrail context; per-rule counters;
OTel-shaped traceroute receipts.
ADAPT (shape transfers, semantics differ — design carefully): hierarchical addressing +
LPM + aggregates (needs cross-links + pay-rent rule + drill-down receipts); session
labels/segment lists (need topic-shift re-classification); 0-RTT boot ticket (replay
caveat: idempotent orientation only, never authorization — FM12-aligned); hedged
multipath retrieval (only if the latency tail justifies it — measure first); PIT-style
standing interests (honestly pub/sub wearing NDN naming; still the right transport for
supersession notices).
VOCABULARY ONLY (naming, no mechanism): TCAM/latency claims, anycast-at-current-scale,
DHTs, packet-vs-atom wordplay.

## 7. Proposed slices (each fences separately; nothing here builds tonight)

Ordering respects: engine-first law (none of these touch lane/latch/token builds),
FM12/T041 gating (context packets LAST), method baseline (fenced dual on load-bearing
design, M3 registration, bars, receipts). N-numbers are proposal labels, not ledger ids.

- **N0 — Close the ECN wire (instrumentation; smallest; FIRST).** Implicit marks
  (surfaced-never-referenced within task = weak noise) mined from the injection ledger
  + session transcript joins; graded explicit votes (skimmed/read-no-use/harmful) at
  near-zero friction (wrap prefills exist; add the hook-level one-keystroke path);
  goodput/rwnd-respected/loss defined formally over existing funnel counters and
  printed by stats as SLIs. Bar: noise/implicit marks flowing within a week of live
  use; goodput SLI visible and moving. Without N0, N2 has no signal — sequencing is
  forced. (First live marks already recorded this session — §9.)
- **N1 — rwnd (advertised context budget).** recall-at accepts an advertised token
  budget; injection ledger enforces + records respected/clipped; zero-window and
  SWS rules honored. Bar: zero over-window injections in a soak; clip events loud.
- **N2 — AIMD + flap dampening per (agent, family).** Consumes N0's signal. Measure
  churn concentration FIRST (per-lesson surfaced:helped — the BGP prediction says a
  handful of lessons cause most waste; extends triage, replaces nothing). Bar: goodput
  SLI trends up over 2 weeks without total-helped falling (backing off noise must not
  silence guardians — unbench valve is the regression stop; dampening state observable).
- **N3 — Recall FIB + negative cache + default route + miss-install.** The
  architectural core; fenced dual design (it IS load-bearing). Bar: p95 recall-at
  latency bounded at any corpus size; hot path never scans; probe battery: generic
  prompts hit negative entries; every miss installs a route; every entry carries
  fallback.
- **N4 — Hierarchical addresses + aggregates + pay-rent rule on the map.** Needs codex
  distillation for aggregate atoms. Skeleton-edge (delegation) caching long+hot; leaf
  bindings short; cross-links first-class beside LPM. Bar: coarse queries return
  aggregates-first with drill-down receipts; a measured slice of specifics folded by
  the pay-rent rule with credit preserved.
- **N5 — 0-RTT boot ticket + stale-while-revalidate.** Formalize boot pack as session
  ticket (snapshot + label + freshness receipt); async refresh; replay caveat: ticket
  carries idempotent orientation only. Deltas later via context-delta family
  (post-T041, FM12). Bar: boot assembly time drops; freshness receipts present.
- **N6 — Hedged multipath retrieval.** Only if N3's telemetry shows a tail worth
  cutting (hedging without a tail is waste; the 2%-extra-for-24x-p99 case must be OURS,
  not Google's).
- **N7 — Looking glass.** Recall traceroute receipts OTel-shaped end-to-end; per-rule
  counters; knowledge-plane UI panel rides T002/T033 when that arc opens.

## 8. What this doc does NOT claim

No TCAM latencies, no distributed-systems scale, no decentralized senders. One machine,
one Redis, N<10 agents, a single administratively-owned funnel — the transport patterns
are chosen because they are robust under uncertainty and CHEAP, not because emergence
is required at this scale (a central optimizer could in principle do better; it would
also be a bigger invention with fewer receipts). The hard prerequisite the analogy does
not solve is context canonicalization (break §5.1); its quality bounds every table in
§4. And none of this ships without its fence: this doc proposes, the fences dispose.

## 9. Live receipts from the session that wrote this

The funnel demonstrated both its value and this doc's diagnosis WHILE the research ran:
- recall-at fired claude_trace_narration_deferred (2026-07-04: defer narration) at the
  exact moment I was narrating to the bus — an EF-class guardrail delivery, on target.
  Cross-check against memory found it was REVERSED by Daniel later that same day (full
  narration is the standing default). A stale route with no supersession edge was still
  being advertised: event-shaped staleness (break §5.4) observed in the wild. Recorded
  as lesson narration_lesson_superseded_same_day; voted the stale lesson useful anyway
  (it correctly triggered the verify).
- The same hook surfaced one on-target and one off-target lesson on a single Write; I
  voted useful on the first and noise on the second — by the session-start counters,
  **the funnel's first noise vote ever**. The dead ECN wire carried its first mark
  during the research that diagnosed it dead. N0 is not hypothetical.

## 10. One-paragraph summary for the ledger

The internet's speed comes from six laws (plane split, hierarchical aggregation, dumb
core, immutable caching, feedback-controlled rate, narrow layers). Aurora's knowledge
side already converged on fragments of the first four; its 4.5% funnel goodput is a
textbook violation of the fifth — an open-loop sender with a dead negative-feedback
wire (noise=0). Upgrade path: name the knowledge plane; compile a recall FIB with
negative caching, default route, and miss-install (data plane, no model inference on
the hot path); keep ranking/curation/distillation as the slow control plane with flap
dampening and a pay-rent supersession rule; close the feedback wire (advertised rwnd,
implicit+graded marks as ECN, AIMD, sojourn AQM, FQ across families, policed EF
guardrails); treat the Atlas hierarchy as the address space with delegation-cached
skeleton edges, distilled aggregates at coarse prefixes, and cross-links surviving LPM.
Recall then joins the packet substrate as its first pluggable producer endpoint (T041,
FM12-gated) — one network, two planes, shared receipts. Slices N0-N7 proposed; N0
(close the ECN wire) is forced first and its first live marks were recorded during this
research.
