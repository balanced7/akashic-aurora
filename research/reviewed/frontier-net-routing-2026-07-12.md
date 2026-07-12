# What Internet Routing Teaches a Knowledge-Retrieval System About Finding the Right Atoms Fast

> Frontier research report (claude-lane web-research agent, 2026-07-12), persisted verbatim
> per the full-fidelity rule. Consumed by:
> research/reviewed/claude-recall-networking-synthesis-2026-07-12.md

**Research report — design input for Akashic Aurora's recall architecture.** The internet forwards ~76 billion packets per second through single chips while its route-computation machinery takes minutes to converge — and this is a *feature*. The architecture that makes that possible (plane separation, precompiled tables, hierarchical addresses, classify-once labels, hash-spread multipath) is a study in one discipline: **never make an expensive decision on the hot path; compile decisions ahead of time into structures cheap enough to consult per-event.** Aurora's recall funnel currently does the opposite — it effectively "runs the routing protocol per packet" — and its 4.5% surfaced-context value rate (34 helped / 1111 surfaced) is what that looks like. Below: the mechanisms with real numbers, then the transfers, then where the analogy lies to us.

---

## 1. Control plane vs data plane: RIB slow, FIB fast

Routers split cleanly into a **control plane** that *computes* reachability and a **data plane** that *executes* it. BGP ([RFC 4271](https://www.rfc-editor.org/rfc/rfc4271)) and OSPF ([RFC 2328](https://www.rfc-editor.org/rfc/rfc2328)) run as software processes exchanging messages and building the **RIB** (Routing Information Base) — all candidate routes from all protocols, with attributes and policy. From the RIB, the router distills the **FIB** (Forwarding Information Base): one best (or ECMP set of) next-hop(s) per prefix, restructured purely for lookup speed and pushed down into hardware, with a companion adjacency table holding the precomputed L2 rewrite ([Cisco CEF](https://www.cisco.com/c/en/us/support/docs/routers/12000-series-routers/47321-ciscoef.html)). The FIB is a *projection* of the RIB: derived, disposable, regenerable — never authoritative.

The two planes run at grotesquely different speeds, by design:

- **Data plane:** TCAM performs a longest-prefix match in a **single clock cycle** ([IEEE 6602288](https://ieeexplore.ieee.org/abstract/document/6602288/)) — order a nanosecond. A Broadcom Tomahawk 5 (BCM78900) forwards **51.2 Tb/s, >76 billion packets/second** at 64-byte frames, and redirects around a failed link in **<500 ns** ([Broadcom](https://www.broadcom.com/products/ethernet-connectivity/switching/strataxgs/bcm78900-series), [press release](https://investors.broadcom.com/news-releases/news-release-details/broadcom-now-shipping-worlds-first-512-tbps-switch-production)).
- **Control plane:** BGP path failover after a fault averaged **3 minutes, with tails to 15 minutes** in Labovitz et al.'s landmark measurement study ([Delayed Internet Routing Convergence](https://www.cs.princeton.edu/courses/archive/fall10/cos561/papers/BGPconverge00.pdf), SIGCOMM 2000 / ToN 2001). BGP even rate-limits itself: the MinRouteAdvertisementIntervalTimer (conventionally ~30 s for eBGP, [RFC 4271 §9.2.1.1](https://www.rfc-editor.org/rfc/rfc4271)) deliberately batches updates to trade convergence latency for stability.

That's roughly **eleven orders of magnitude** between decision-making and decision-execution, and the internet works *because* nobody minds. Slow control is acceptable because (a) topology changes are rare relative to packets, (b) the FIB keeps forwarding on stale-but-mostly-right state during convergence, and (c) even failure response is precompiled — Loop-Free Alternates ([RFC 5286](https://www.rfc-editor.org/rfc/rfc5286)) precompute a backup next-hop per prefix so repair is a FIB swap, not a recomputation. The table being consulted is ~**1,064,295 IPv4 prefixes** in the default-free zone as of 2026-07-12 ([bgp.potaroo.net](https://bgp.potaroo.net/as2.0/bgp-active.html)), plus **256,046 IPv6** ([potaroo v6](https://bgp.potaroo.net/v6/as2.0/index.html)) — nanosecond lookups against a million-entry structure.

## 2. Hierarchical addressing and longest-prefix match

Why does the core route on ~1M prefixes instead of the billions of attached hosts? **CIDR** ([RFC 4632](https://www.rfc-editor.org/rfc/rfc4632)): addresses are allocated hierarchically so that one aggregate (`203.0.112.0/20`) stands for thousands of hosts, and forwarding is **longest-prefix match** — mandated for IPv4 by [RFC 1812 §5.2.4.3](https://www.rfc-editor.org/rfc/rfc1812) and for IPv6 by [RFC 7608](https://www.rfc-editor.org/rfc/rfc7608). LPM gives graceful precision degradation: a router that knows a specific /24 uses it; one that only knows the covering /16 still delivers; one that knows nothing uses the **default route** (0.0.0.0/0) — the coarsest aggregate, "when in doubt, send it toward someone who knows more." Only the default-free zone has no such escape hatch.

Aggregation trades precision for table size, and the trade is contested in practice: the CIDR Report counts **~461,596 more-specific routes (≈43% of the table) that add no routing value** — deaggregation leaked for traffic engineering or by accident ([potaroo, March 2026](https://www.potaroo.net/ispcol/2026-03/cidr-report.html)). Lesson: specifics must *pay rent* (behave differently from their covering aggregate) or they are pure table bloat.

## 3. MPLS and segment routing: classify once, then O(1)

MPLS ([RFC 3031](https://www.rfc-editor.org/rfc/rfc3031)) observes that per-hop header analysis re-answers the same question at every router. Instead, the **ingress** router classifies the packet **once** into a Forwarding Equivalence Class (FEC) and pushes a short fixed-length label (20 bits, [RFC 3032](https://www.rfc-editor.org/rfc/rfc3032)). Every subsequent hop does an **exact-match label lookup → swap → forward**: O(1), no prefix matching, no policy evaluation. Crucially, ingress classification can be *richer* than destination alone (VPN membership, QoS class, application) precisely because it's paid once.

**Segment routing** ([RFC 8402](https://www.rfc-editor.org/rfc/rfc8402)) refines this: the ingress attaches an ordered *list* of segments (waypoints/instructions) to the packet, so the path is source-programmed and **per-flow state exists only at ingress — midpoints stay stateless**. Label-switched paths beat per-hop routing when flows are long-lived relative to classification cost and when you want path decisions centralized rather than emergent.

## 4. SDN: the split made programmable

OpenFlow made the control/data split an explicit API: a central controller installs **match-action flow entries** into switch tables; packets are matched against prioritized entries across a pipeline of tables; a **table-miss** entry decides what happens when nothing matches — typically "punt to controller," which computes an answer and *installs a new flow entry* so subsequent packets of that flow hit the fast path ([OpenFlow Switch Specification 1.5.1](https://opennetworking.org/wp-content/uploads/2014/10/openflow-switch-v1.5.1.pdf); terminology per [RFC 7426](https://www.rfc-editor.org/rfc/rfc7426)). Flow entries carry **counters** — the data plane meters itself and reports usage back to the controller. P4 goes further: the *match schema itself* is programmable — you declare parsers and match-action tables rather than accepting fixed header fields ([Bosshart et al., SIGCOMM CCR 44(3), 2014](https://dl.acm.org/doi/10.1145/2656877.2656890)). The architectural content: **central policy, distributed execution, and a declarative table as the contract between them — with a defined miss path and built-in telemetry.**

## 5. ECMP and anycast: many equally good answers

When several paths cost the same, routers **hash** each packet's flow identity (5-tuple) to pick one — per-*flow*, not per-packet, so a flow's packets stay ordered ([RFC 2991](https://www.rfc-editor.org/rfc/rfc2991), [RFC 2992](https://www.rfc-editor.org/rfc/rfc2992)). No coordinator, no state: determinism from hashing.

**Anycast** ([RFC 4786](https://www.rfc-editor.org/rfc/rfc4786)) advertises one address from many locations; ordinary routing delivers each client to the *nearest* instance. The DNS root is the existence proof: **13 named server addresses, ~1,954 physical instances** worldwide as of Dec 2025 ([root-servers.org via Wikipedia](https://en.wikipedia.org/wiki/Root_name_server)). Callers name the *service*; topology picks the *replica*.

## 6. Router internals: why the hot path is fast

Compressing the above into the design rules that make nanosecond forwarding possible:

1. **Precomputation everywhere** — routes, aggregates, L2 rewrites, even failure responses (LFA) are compiled before traffic arrives.
2. **Fixed-length keys, bounded match** — 32/128-bit addresses, 20-bit labels; lookup structures (TCAM, tries) exploit that rigidly.
3. **Pipelining** — parse → lookup → rewrite → queue as fixed stages; throughput from parallelism, not per-stage cleverness.
4. **No per-packet global decisions** — every hot-path decision is local table state; anything global (policy, optimality, convergence) happens off-path.
5. **Graceful degradation over stalls** — stale FIB entries and default routes keep packets moving; the system never blocks awaiting better information.
6. **Self-limiting churn** — MRAI batching, and route-flap dampening ([RFC 2439](https://www.rfc-editor.org/rfc/rfc2439), tuned by [RFC 7196](https://www.rfc-editor.org/rfc/rfc7196)) which assigns flapping prefixes an exponentially-decaying penalty and *suppresses* them past a threshold. Churn is pathologically concentrated: **half of all BGP updates come from <5% of unstable prefixes, and 50 origin ASes generate a third of all IPv4 updates** ([potaroo, Jan 2026](https://www.potaroo.net/ispcol/2026-01/bgpupd2025.html)).

---

## 7. Transferable patterns

### 7.1 Compile a Recall FIB (RIB/FIB split)
**Principle: the hot path consults precomputed answers; it never searches, ranks, or decides globally.**
Aurora's action-time recall should be a *lookup against a compiled table*, not a live funnel run. Concretely: a **ranking control plane** — an offline/async process with the whole ledger, recall-outcome history, and unlimited time — maintains the "RIB" (full scored candidate structure: every context signature it has seen × candidate atoms × evidence). From it, compile a **recall FIB**: `context-signature → top-k atom IDs + prefetch hints`, stored in Redis (L2) as flat entries. The 100–150ms query budget then covers a hash lookup plus optional cheap re-rank of ~k items — comfortably inside budget, because the expensive judgment already happened. Key disciplines to copy: the FIB is *derived and regenerable* (matches Aurora's projections-over-immutable-atoms doctrine); RIB changes patch the FIB incrementally (a new atom triggers targeted table edits, not recompute); and **stale is acceptable** — a recall table minutes behind the ledger beats a live search that blows the latency budget, exactly as BGP's 3-minute convergence is tolerable because the FIB keeps forwarding meanwhile. Precompute failure response too (LFA-style): every FIB entry carries a fallback ("if top-k unavailable/rejected, serve chapter summary").

### 7.2 Hierarchical knowledge addresses with LPM and paying-rent specifics (CIDR)
**Principle: structure in the address space buys table compression; match at the longest prefix you know, and keep specifics only where they behave differently from their aggregate.**
Atlas → Track → Chapter → Beat is already a prefix hierarchy — make it an *address*: `aurora:/system4/spine/wave2/v7-benchmark`. Recall becomes LPM: exact beat-level lessons if present; else the **chapter-level aggregate** — a Distiller-maintained summary atom playing the role of the covering /16; else track; else the **default route**: the boot context, guaranteeing recall never returns nothing, only something coarser. Two routing disciplines transfer directly: (a) aggregate summaries are *routes*, maintained objects with the same citizenship as specifics; (b) a fine-grained lesson deserves existence only if it **contradicts or refines its covering summary** — the CIDR Report's 43% valueless more-specifics is precisely what an undisciplined lesson store becomes, and Supersession is the natural enforcement point.

### 7.3 Session-ingress classification and label-switched recall (MPLS/SR)
**Principle: classify once at ingress into an equivalence class; make every subsequent decision an O(1) exact-match on the attached label.**
Today each recall-at-action re-derives context from scratch. Instead: at session ingress (agent boot / door open / task claim), run *rich* classification once — task type × subsystem × agent × active chapter — yielding a **recall FEC label**. Aurora's bus packet spec already carries `flow/lane/class`; add the recall label to the session envelope. Subsequent recalls exact-match the label into the label table (which points into the recall FIB) — no per-action re-classification. The segment-routing upgrade: when an agent *plans* a multi-step task, the plan compiles a **segment list of knowledge waypoints** ("for step 3 you'll need the CAS lessons; step 5, the lock-thrash notes") attached at ingress — per-task state lives only at ingress, and mid-task recall is stateless label-popping ([RFC 8402]'s exact property).

### 7.4 Match-action recall policy with a miss path and counters (SDN)
**Principle: central policy, distributed execution, declarative tables as the contract — and every table entry meters its own usefulness.**
Express recall policy as OpenFlow-style rules: `match(context fields) → action(surface atom set | suppress | summarize-first)`. Agents' hot paths only execute tables; one controller owns policy. **Table-miss = reactive installation**: an unrecognized context punts to the slow path (full funnel search), whose result is *installed as a new entry* so the next similar context is fast — the FIB becomes self-extending along actual traffic. And copy OpenFlow's counters: every entry records `surfaced / acted-on`, which is exactly Aurora's 1111/34 metric — but *per-rule* rather than global, giving the control plane the resolution to fix specific rules instead of lamenting an aggregate 4.5%.

### 7.5 Recall-flap dampening (RFC 2439)
**Principle: penalize sources of repeated worthless churn with an exponentially decaying suppression score; waste is concentrated, so suppression is cheap.**
The single most actionable transfer for the 4.5% problem. Give each lesson a penalty that increments when surfaced-and-ignored and decays exponentially with time; past a suppress threshold the atom stops being advertised into recall (except under exact-match request) until it decays below a reuse threshold. BGP's churn concentration (<5% of prefixes → half of updates) predicts Aurora's waste is likewise concentrated in a few over-eager lessons — measure per-atom surfaced:helped ratios first; dampening a handful likely reclaims most of the wasted 96%. Heed [RFC 7196], though: early dampening over-suppressed; make thresholds forgiving and observable.

### 7.6 Anycast tiers and ECMP spreading
**Principle: name the knowledge, not the replica; let resolution pick the nearest instance, and hash-spread load without coordination.**
Aurora's L1/L2/L3 skeleton cache is anycast waiting to be named: an agent requests `aurora:knowledge/X` and resolution serves the nearest tier holding it — session cache, Redis, cold store — one name, 1,954-instances-style. For multi-agent load, ECMP transfers as **per-session hashing** across replicas/shards (never per-query, preserving session cache coherence, mirroring per-flow hashing's ordering guarantee in [RFC 2992]).

---

## 8. Where the analogy breaks

Adversarial pass — the places the isomorphism is decorative:

1. **Routing is handed its destination; retrieval must discover it.** A packet arrives with a 32-bit answer to "where?" written on it; forwarding only executes delivery. A recall query's destination — *which atoms* — is the entire unknown. The recall-FIB pattern silently relocates all difficulty into computing a good **context signature**, which is a semantic-similarity/ranking problem routing never faces. If signatures don't cluster real-world contexts well, the FIB is a fast index into wrong answers.
2. **No fixed-length keys, no prefix order.** LPM and single-cycle TCAM work because keys are fixed-width bit strings with a total hierarchical order ([RFC 7608]). Semantic space has no prefix structure; embeddings don't nest. Aurora's hierarchical addresses exist only because a *librarian assigns them* — a misfiled atom is unreachable in a way a misaddressed packet is not (the sender owns IP addressing; the store owns atom addressing). ANN search is sublinear, not O(1); the *shape* (precompute vs search) transfers, the latency floor does not.
3. **One exact destination vs many fuzzy ones.** Forwarding is argmax to a single next hop with binary success. Retrieval is top-k under graded relevance: there is no "converged" state, and a FIB can be *verified* consistent with its RIB while a recall table can only be *evaluated* (precision@k against judgments that are themselves noisy).
4. **The destination space is enumerable; the query space is not.** The DFZ compiles because ~1.06M prefixes exist, change slowly, and are exhaustively known. Contexts are unbounded — a recall FIB covers only head signatures, so unlike a real FIB it *will* miss, and the slow path must stay fully operational forever. The recall FIB is honestly a cache, not a FIB.
5. **Aggregation is lossless for delivery, lossy for meaning.** A covering /16 still delivers the packet perfectly; a chapter summary standing in for a specific lesson can actively mislead. In routing, precision loss costs optimality; in retrieval it costs correctness.
6. **Labels assume flow stability.** MPLS flows keep their FEC; agent sessions drift topic mid-task. A stale recall label pins the session to the wrong equivalence class — and unlike a bad MPLS label (drop or loop, detectably wrong), wrongly-labeled recall produces *plausible-but-irrelevant context*, which is undetectable on the data plane. That is the current 4.5% failure mode wearing a new hat; labels need re-classification triggers (topic-shift detection) that MPLS never needed.
7. **Anycast replicas are identical; knowledge tiers are not.** Nearest-instance selection is safe only because every root-server instance serves the same zone. L1/L2/L3 tiers trade freshness and fidelity — "nearest" answers can be stale or summarized, a dimension anycast doesn't have.
8. **Routing has no utility feedback.** No router asks whether a packet was *worth delivering*. Aurora's defining metric — helped/surfaced — has no networking analog; flap dampening penalizes instability, not uselessness (7.5 above bends it deliberately). The most important loop in the whole design, value-feedback-driven re-ranking, must be imported from IR/ML, not networking.
9. **Decorative borrowings, fine as vocabulary only:** DiffServ lane names, TTL on lessons, "packets vs atoms" — naming conveniences that carry no mechanism.

**Net judgment:** the load-bearing transfers are the *plane split* (7.1, 7.4), *dampening* (7.5), and *default-route graceful degradation* (7.2's fallback chain) — these are architecture-shape lessons independent of key semantics. The label and LPM transfers are valuable but conditional on solving classification quality, which the analogy assumes away. Adopt the shapes; do not import the latency claims or the correctness guarantees.

---

## Sources

- BGP table size (IPv4, AS65000 FIB): https://bgp.potaroo.net/as2.0/bgp-active.html
- BGP table size (IPv6): https://bgp.potaroo.net/v6/as2.0/index.html
- CIDR Report / more-specifics analysis (Huston, ISP Column, March 2026): https://www.potaroo.net/ispcol/2026-03/cidr-report.html
- BGP update churn concentration (Huston, ISP Column, Jan 2026): https://www.potaroo.net/ispcol/2026-01/bgpupd2025.html
- Labovitz et al., *Delayed Internet Routing Convergence*: https://www.cs.princeton.edu/courses/archive/fall10/cos561/papers/BGPconverge00.pdf
- Broadcom Tomahawk 5 (BCM78900) product page: https://www.broadcom.com/products/ethernet-connectivity/switching/strataxgs/bcm78900-series
- Broadcom 51.2 Tbps press release: https://investors.broadcom.com/news-releases/news-release-details/broadcom-now-shipping-worlds-first-512-tbps-switch-production
- Tomahawk 5 packet-rate analysis (TechInsights): https://www.techinsights.com/blog/tomahawk-5-switches-512tbps
- TCAM single-cycle LPM: https://ieeexplore.ieee.org/abstract/document/6602288/
- Cisco Express Forwarding (RIB/FIB/adjacency): https://www.cisco.com/c/en/us/support/docs/routers/12000-series-routers/47321-ciscoef.html
- OpenFlow Switch Specification 1.5.1 (ONF): https://opennetworking.org/wp-content/uploads/2014/10/openflow-switch-v1.5.1.pdf
- Bosshart et al., *P4: Programming Protocol-Independent Packet Processors*, SIGCOMM CCR 44(3): https://dl.acm.org/doi/10.1145/2656877.2656890
- Root name server anycast instance counts: https://en.wikipedia.org/wiki/Root_name_server (data: https://root-servers.org)
- RFC 4271 (BGP-4): https://www.rfc-editor.org/rfc/rfc4271
- RFC 2328 (OSPFv2): https://www.rfc-editor.org/rfc/rfc2328
- RFC 4632 (CIDR): https://www.rfc-editor.org/rfc/rfc4632
- RFC 1812 (Requirements for IPv4 Routers, LPM): https://www.rfc-editor.org/rfc/rfc1812
- RFC 7608 (IPv6 prefix length / LPM requirement): https://www.rfc-editor.org/rfc/rfc7608
- RFC 3031 (MPLS architecture): https://www.rfc-editor.org/rfc/rfc3031
- RFC 3032 (MPLS label stack encoding): https://www.rfc-editor.org/rfc/rfc3032
- RFC 8402 (Segment Routing architecture): https://www.rfc-editor.org/rfc/rfc8402
- RFC 2991 / RFC 2992 (multipath / ECMP hashing): https://www.rfc-editor.org/rfc/rfc2991, https://www.rfc-editor.org/rfc/rfc2992
- RFC 4786 (Operation of Anycast Services): https://www.rfc-editor.org/rfc/rfc4786
- RFC 2439 (Route Flap Damping): https://www.rfc-editor.org/rfc/rfc2439
- RFC 7196 (Making Route Flap Damping Usable): https://www.rfc-editor.org/rfc/rfc7196
- RFC 5286 (Loop-Free Alternates / IP Fast Reroute): https://www.rfc-editor.org/rfc/rfc5286
- RFC 7426 (SDN Layers and Architecture Terminology): https://www.rfc-editor.org/rfc/rfc7426
