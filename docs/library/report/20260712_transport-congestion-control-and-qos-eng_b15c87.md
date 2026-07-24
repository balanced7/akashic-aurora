---
akashic_id: art_20260712_transport-congestion-control-and-qos-eng_b15c87
akashic_sha: 660d2eb45209
status: draft
type: report
date: 2026-07-12
title: "Transport, Congestion Control, and QoS: Engineering Lessons for Context Delivery to LLM Agents"
gist: "# Transport, Congestion Control, and QoS: Engineering Lessons for Context Delivery to LLM Agents > Frontier research report (claude-lane web"
tenant: solo
visibility: fleet
seats: []
category: [library, recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_recall-as-a-network-the-knowledge-plane_163b1e
    rel: cites
created: "2026-07-12T04:04:50"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260712_transport-congestion-control-and-qos-eng_b15c87 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Transport, Congestion Control, and QoS: Engineering Lessons for Context Delivery to LLM Agents

# Transport, Congestion Control, and QoS: Engineering Lessons for Context Delivery to LLM Agents

> Frontier research report (claude-lane web-research agent, 2026-07-12), persisted verbatim
> per the full-fidelity rule. Consumed by:
> research/reviewed/claude-recall-networking-synthesis-2026-07-12.md

**Scope.** This report surveys the transport-layer engineering canon — flow/congestion control, AQM, QoS, QUIC, tail-latency technique, goodput — and then maps each mechanism onto Akashic Aurora's recall funnel, which must deliver the right amount of past-lesson context into an LLM's bounded context window. Current funnel telemetry (99 lessons, 1,111 surfacings, 34 helped, value ≈ 4.5%, votes useful=16 / noise=0) is analyzed in transport terms in §8.

---

## 1. Flow Control vs. Congestion Control

TCP separates two problems that are easy to conflate:

- **Flow control** protects the *receiver*. The receiver advertises a window (**rwnd**) in every ACK segment — an explicit declaration of remaining buffer space (RFC 9293 §3.8.6). It is a fact, not an inference. A receiver can advertise **zero**, and the sender must stop entirely, sending only periodic window probes until the window reopens (RFC 9293 §3.8.6.1). Window scaling (RFC 7323) extends the 16-bit field to ~1 GiB for high bandwidth-delay-product paths.
- **Congestion control** protects the *network*. No router advertises its capacity, so the sender maintains a congestion window (**cwnd**) *inferred* from feedback — loss, delay, or ECN marks (RFC 5681).

The sender may have outstanding at most **min(cwnd, rwnd)**: the lesser of what the network can carry and what the receiver can absorb (RFC 5681 §3.1). The sliding window advances as ACKs return, so ACK arrival "clocks" new transmissions ("ACK clocking"). A companion rule, Silly Window Syndrome avoidance (RFC 9293 §3.8.6.2, RFC 1122), forbids dribbling tiny segments into tiny window openings — wait until a useful amount of window is available.

The design lesson: **explicit declaration where a party can know its own state; inference plus feedback where it cannot.**

## 2. Congestion Control Evolution: AIMD → CUBIC → BBR → ECN

**AIMD.** Chiu & Jain (1989) proved that among linear control rules, only Additive-Increase/Multiplicative-Decrease converges to an allocation that is both efficient and fair across competing flows; AIAD, MIMD, and MIAD do not. The asymmetry is deliberate: a congestion signal is urgent and reliable (overload compounds itself), so back off multiplicatively — fast; absence of congestion only proves you are *somewhere below* capacity, so probe additively — cautiously. TCP Reno implements this: cwnd += 1 MSS per RTT in congestion avoidance, cwnd halved on loss (RFC 5681). Congestion collapse — the failure mode AIMD exists to prevent — was first documented by Nagle: networks where offered load rises while useful delivered throughput falls by orders of magnitude (RFC 896).

**CUBIC** (RFC 9438, obsoleting RFC 8312) keeps loss as the signal but replaces linear growth with a cubic function of time-since-last-loss, so cwnd re-approaches the prior loss point quickly, plateaus near it, then probes beyond. It is the default in Linux, Windows, and Apple stacks (RFC 9438).

**BBR** abandons loss-as-signal for an explicit *model*: it continuously estimates the bottleneck bandwidth (windowed-max of delivery rate) and the round-trip propagation delay (windowed-min RTT over a 10-second filter, `BBR.MinRTTFilterLen = 10s`), and **paces** transmission at the estimated bandwidth with roughly one BDP in flight — Kleinrock's optimal operating point (Cardwell et al., ACM Queue 2016; draft-ietf-ccwg-bbr). It cycles through ProbeBW (briefly overshoot to discover new bandwidth, then drain) and ProbeRTT (briefly cut in-flight data so queues empty and true min-RTT is visible). Loss-based CC *must fill the bottleneck buffer to learn anything*; BBR keeps queues near-empty by design. BBRv2/v3 (draft-ietf-ccwg-bbr) add bounded loss/ECN responsiveness to fix v1's documented unfairness to Reno/CUBIC and its overshoot with multiple flows.

**ECN** (RFC 3168) replaces the drop with a mark: a congested router sets the CE codepoint; the receiver echoes it via the TCP ECE flag; the sender reduces cwnd exactly as if a packet had been lost and confirms with CWR. Congestion feedback without destroying data. L4S (RFC 9331) refines this: immediate, frequent, fine-grained marking with a proportionally smaller, smoothed response per mark — a high-resolution feedback channel instead of a rare binary one.

## 3. Bufferbloat and AQM: CoDel and FQ-CoDel

Bufferbloat is the pathology of oversized, unmanaged buffers: they absorb bursts (helping measured throughput) while adding seconds of standing queue delay, and they *defeat* congestion control by hiding the loss signal until far too late (Gettys & Nichols, CACM Jan 2012). Crucially, the damage is misattributed — users blame "insufficient bandwidth" when the problem is queue *delay*.

**CoDel** (RFC 8289) fixed the control law by changing the measured variable: not queue *length*, but per-packet **sojourn time** — how long each packet actually waited. If the *minimum* sojourn time stays above **TARGET = 5 ms** for an **INTERVAL = 100 ms**, CoDel enters a dropping state, dropping at increasing frequency until the standing queue drains. Bursts that drain quickly are tolerated; *persistent* queues are punished. The parameters are effectively deployment-free for normal Internet use (RFC 8289 §4.4).

**FQ-CoDel** (RFC 8290) adds isolation: flows are hashed into 1,024 (by default) sub-queues scheduled by byte-based Deficit Round Robin with a configurable quantum, with CoDel running on each queue. A two-tier "new list / old list" gives **sparse flows** (those that haven't built a backlog) brief priority, so a keystroke or DNS query slips past a bulk transfer. One heavy flow can no longer inflate everyone's delay or starve others.

## 4. QoS Architectures: DiffServ, Token Buckets, Admission Control

**DiffServ** (RFC 2474, RFC 2475) marks each packet's DS field with a codepoint selecting a per-hop behavior — no per-flow state in the core. Three canonical classes: **EF** (Expedited Forwarding, RFC 3246): low loss/latency/jitter, but only if EF arrival rate is strictly policed below configured capacity; **AF** (Assured Forwarding, RFC 2597): four classes × three drop precedences (AF11–AF43), degrade by dropping high-precedence packets first; **BE** (best effort, the default PHB, RFC 2474).

**Token buckets** meter conformance: tokens accrue at committed rate CIR into a bucket of burst size CBS; conformant packets spend tokens, excess is either **policed** (dropped/remarked immediately — srTCM RFC 2697, trTCM RFC 2698 with a peak rate) or **shaped** (delayed in a buffer to smooth the profile, RFC 2475 §2.3.3). Policing trades loss for zero added delay; shaping trades delay for zero loss.

**IntServ/RSVP** (RFC 1633, RFC 2205) took the other road: per-flow bandwidth *reservations* signaled hop-by-hop. It failed to scale — per-flow classification, scheduling, and soft state in every backbone router (scaling concerns stated in RFC 2208; RFC 2998 retreats to IntServ-at-edges-over-DiffServ-core). The durable lesson: **per-flow reservation dies in the core, but admission control survives at the edge** — it is cheaper to refuse a flow entry than to degrade everyone mid-stream.

## 5. QUIC: 0-RTT, Stream Multiplexing, Migration

QUIC (RFC 9000) rebuilds transport over UDP with three relevant moves:

1. **0-RTT resumption.** A client caches the server's transport parameters and a TLS 1.3 session ticket (RFC 8446 NewSessionTicket; RFC 9001 §4.6) from a prior connection and sends application data in its *first* flight — no handshake round-trip, at the cost of replay-attack constraints on what 0-RTT data may do (RFC 9001 §9.2).
2. **Stream multiplexing without head-of-line blocking.** Many independent ordered streams share one connection; a lost packet stalls only the stream whose data it carried (RFC 9000 §2), unlike HTTP/2-over-TCP where one lost TCP segment blocks all streams behind it.
3. **Connection migration.** Connections are identified by connection IDs, not the 4-tuple, so a session survives an address change — Wi-Fi to cellular — without re-establishment (RFC 9000 §9).

## 6. Tail Latency Engineering

Dean & Barroso's "The Tail at Scale" (CACM 2013) shows why the p99 dominates user experience at fan-out: if each server answers in 10 ms typically but 1 s at p99, a request fanning out to 100 servers waits >1 s **63%** of the time. Mitigations:

- **Hedged requests:** send a duplicate to a second replica only after the first has been outstanding longer than the ~p95 latency, take the first answer, cancel the loser. This caps added load near 5%. Google benchmark: reading 1,000 BigTable keys across 100 servers, hedging after 10 ms cut p99.9 from **1,800 ms to 74 ms** for ~**2% extra requests**.
- **Tied requests:** enqueue on two servers simultaneously, each tagged with the other's identity; whichever dequeues first cancels its twin — attacking queueing variance rather than service variance.

The meta-lesson: at scale you cannot eliminate variance, so you *route around it* with small amounts of redundancy, and you optimize the distribution's tail, not its mean.

## 7. Goodput vs. Throughput

Throughput counts bits moved; **goodput** counts only bits *usefully delivered*: "forwarded to the correct destination … minus any bits lost or retransmitted" (RFC 2647 §3.17). Retransmissions, duplicates, protocol overhead, and data discarded after delivery all inflate throughput while leaving goodput unchanged. Congestion collapse (RFC 896) is precisely the regime where throughput stays high while goodput approaches zero — the wire is busy carrying waste.

---

## 8. Transferable Patterns for Context Delivery

The recall funnel is a transport system: sender = retrieval/surfacing pipeline; link = the prompt; receiver = the LLM's context window and attention; payload = lessons. Applying the canon:

**8.1 The context budget is an rwnd — make it advertised, not guessed.** Today the funnel implicitly guesses how much context an agent can absorb. TCP's answer: the receiver *declares* it. Each recall request (or each envelope on the Redis bus) should carry an explicit `budget_tokens` field — remaining window minus task reserve — and the funnel must never inject beyond min(budget, its own send window). Honor the zero-window case: an agent deep in a long task can advertise 0 and receive nothing but "window probes" (one-line pointers, not payloads). Apply SWS avoidance: if only 80 tokens of budget remain, don't dribble a fragment of a lesson — send nothing until a coherent unit fits (RFC 9293 §3.8.6.2's logic, transposed).

**8.2 The ECN wire is dead — and that explains the 4.5%.** The vote counters read useful=16 / noise=0. In transport terms: **the funnel has ACKs but no loss and no ECN marks — the negative-feedback channel does not exist.** A TCP sender that never receives a congestion signal never decreases; its window grows to whatever the buffer absorbs. The context window, like a bloated buffer, absorbs everything silently (Gettys & Nichols's exact pathology: the buffer "helps throughput" while destroying quality-of-experience, and the damage is misattributed). Result: 1,111 surfacings for 34 helps (3.1% surfacing-level hit rate) and 4.5% useful-tokens/injected-tokens — a link running at 4.5% goodput is in congestion collapse by any RFC 896 reading. The fix is not smarter ranking first; it is *building the feedback wire*: (a) make "noise" votes near-zero-cost and, better, *implicit* — a surfaced lesson that is never referenced by the agent's subsequent actions within the task is an implicit ECN mark (delay-based signal), no explicit vote needed; (b) run **AIMD per (agent, task-type) flow**: additively increase surfacing volume/aggressiveness on useful signals, multiplicatively cut it on noise marks (Chiu & Jain's result says this asymmetric rule, not proportional tuning, is what converges to fair and efficient). Prefer the L4S refinement (RFC 9331): frequent fine-grained marks ("skimmed", "read-no-use", "actively harmful") with proportional response, over rare binary ones.

**8.3 CoDel on the injection queue — drop by sojourn, not by backlog.** Lessons queued for surfacing should carry an enqueue timestamp; the control variable is **sojourn time**, not queue depth (RFC 8289). If candidate context has waited past its usefulness horizon — the action it was retrieved for has moved on, its `deadline` envelope field has passed — *drop it*, don't deliver it late. Late context is worse than none: it spends budget on a decision already made. The envelope spec already has `ttl`/`deadline` fields; CoDel's contribution is the discipline that these are enforced *at dequeue*, with tolerance for brief bursts but escalating drops for *standing* backlog. Pick a TARGET analog (e.g., "context must be ≤ N agent-turns stale") and measure it per delivery.

**8.4 FQ-CoDel across lesson families and sources.** One prolific lesson family (or one chatty retriever) must not monopolize the window. Hash candidates by source/family into sub-queues, schedule by deficit round robin with a token *quantum*, and give **sparse sources brief priority** (RFC 8290's new/old lists): the lesson family that rarely speaks probably has something task-specific; the family that fills its queue every time is bulk traffic. This is per-flow fairness applied to attention.

**8.5 DiffServ classes for context, mapped to existing lanes.** The bus already maps sig=EF, work=QoS1/AF, trace=QoS0/BE. Context deliveries should be classed the same way: **blocking-critical** (a lesson that says "this exact action failed catastrophically before") = EF/sig — but per RFC 3246, EF only works if *strictly policed*: cap EF-class context to a small fixed token rate or it degrades everything; **advisory** (relevant precedent) = AF/work with drop-precedence levels — under budget pressure, shed AF3 before AF1; **ambient** (background flavor) = BE/trace, first to be dropped entirely. Police with a token bucket per class (RFC 2697): a committed injection rate plus a small burst allowance, and *shape* (defer to next turn) rather than drop only for AF, never for stale EF.

**8.6 Admission control at the edge, not reservation in the core.** IntServ's failure warns against per-delivery negotiation machinery; its surviving kernel says: gate *entry into the surfacing pool*. A lesson corpus of 99 producing 1,111 surfacings means each lesson surfaces ~11 times; lessons with repeated implicit-noise marks should lose admission (quarantine/demotion) — refusal at the edge is cheaper than per-delivery filtering in the hot path (RFC 2208's lesson, RFC 2998's architecture).

**8.7 0-RTT session boot.** Cold-starting an agent by re-deriving "what matters" is a full handshake every time. The QUIC pattern: on session end, mint a **session ticket** — a compiled, budget-sized context snapshot (active notes, open docket, top-K lessons for the agent's standing role) — and inject it in the first flight of the next session with zero retrieval round-trips (RFC 9000/9001 resumption). Carry QUIC's caveat: 0-RTT data may be *stale/replayed* — the snapshot must be safe to act on if the world changed, so restrict it to idempotent orientation, not authorization.

**8.8 Hedged retrieval; pace, don't burst; measure goodput.** Run lexical/vector/graph retrievers in parallel only in hedged form: fire the cheap one, hedge with the expensive ones after its p95 latency, take first-good-answer, cancel losers — bounding both latency tail and compute (Dean & Barroso: 1,800→74 ms for 2% extra work). From BBR, take *pacing*: deliver context smoothly across turns at an estimated absorption rate rather than dumping a burst that builds an attention queue; and maintain an explicit two-parameter model per consumer — absorption bandwidth (useful tokens/turn) and a min-"RTT" (turns until feedback) — refreshed by occasional ProbeRTT-style low-injection turns that reveal the agent's uninfluenced baseline. Finally, adopt goodput (RFC 2647) as *the* SLO — the funnel already computes it as "value." Target movement in useful-tokens/injected-tokens, never in surfacing counts (throughput), which the current telemetry shows can grow while value stagnates.

## 9. Where the Analogy Breaks

Be honest about which mappings are load-bearing and which are decorative:

- **Loss is observable in-band; noise is not.** A dropped packet is detected mechanically by the sender (dupACKs, timeout) within an RTT. Context "noise" requires the *consumer* to judge and report — a lossy, laggy, cognitively taxed channel. The noise=0 counter is itself the proof: the instrument reads zero because voting costs attention, not because noise is absent. Any ECN-analog here must be mostly *implicit* (usage tracing), and even then it measures correlation with mention, not causal helpfulness. TCP never has this epistemology problem.
- **Bandwidth is fungible; attention is not.** Every byte through a bottleneck costs the same. Tokens do not: position matters (mid-context content is measurably under-attended — "lost in the middle," Liu et al., TACL 2024), ordering matters, and injected context can *actively mislead*, a failure mode with no packet analog — a delivered packet never subtracts value; a delivered lesson can.
- **The window doesn't slide.** TCP's receiver drains its buffer and re-advertises; an LLM context window is consumed monotonically within a session. "rwnd" here is a *depleting* budget, closer to a token bucket that never refills until session reset. Flow control maps; the *sliding* does not.
- **No packet equality.** Congestion control assumes flows of interchangeable segments; lessons are unique, non-substitutable, and their value is context-dependent. Fair queuing across sources is a real transferable structure, but "fairness" between lesson families is a heuristic for diversity, not a provable Chiu-Jain equilibrium — the convergence theorem does not carry over because the utility function isn't shared or linear.
- **Retransmission is free of semantics; repetition isn't.** Retransmitting a segment is pure recovery. Re-surfacing a lesson changes the message ("the system really wants you to see this") — duplicates carry pragmatics. Hedged *retrieval* transfers cleanly (it happens before the consumer); hedged *delivery* does not.
- **One receiver, shared fate.** Internet CC coordinates thousands of independent selfish senders through a dumb core. The funnel is a single administratively-owned sender with a cooperative receiver — it could, in principle, be solved by central optimization. The transport patterns are valuable because they are *robust under uncertainty and cheap*, not because decentralized emergence is required here.

**Bottom line.** Three mappings are load-bearing and should be built: advertised budget (rwnd), a real negative-feedback wire driving AIMD (ECN — currently dead, and its absence explains the 4.5% goodput), and sojourn-time dropping with per-source fair queuing (FQ-CoDel). Classes/policing, 0-RTT snapshots, and hedged retrieval are strong seconds. The rest is instructive metaphor — use it for vocabulary, not for design authority.

## Sources

- RFC 9293, Transmission Control Protocol — https://www.rfc-editor.org/rfc/rfc9293.html
- RFC 5681, TCP Congestion Control — https://www.rfc-editor.org/rfc/rfc5681.html
- RFC 7323, TCP Extensions for High Performance — https://www.rfc-editor.org/rfc/rfc7323.html
- Chiu & Jain, "Analysis of the Increase and Decrease Algorithms for Congestion Avoidance," 1989 — https://www.semanticscholar.org/paper/805d0da469da6ba7571ee75732ab66202aaea9e0
- RFC 896, Congestion Control in IP/TCP Internetworks (Nagle) — https://www.rfc-editor.org/rfc/rfc896
- RFC 9438, CUBIC for Fast and Long-Distance Networks — https://www.rfc-editor.org/info/rfc9438/
- Cardwell et al., "BBR: Congestion-Based Congestion Control," ACM Queue 14(5), 2016 — https://dl.acm.org/doi/10.1145/3012426.3022184
- draft-ietf-ccwg-bbr, BBR Congestion Control — https://datatracker.ietf.org/doc/draft-ietf-ccwg-bbr/
- RFC 3168, The Addition of Explicit Congestion Notification (ECN) to IP — https://www.rfc-editor.org/rfc/rfc3168.html
- RFC 9331, ECN Protocol for L4S — https://www.rfc-editor.org/info/rfc9331/
- Gettys & Nichols, "Bufferbloat: Dark Buffers in the Internet," CACM 55(1), 2012 — https://cacm.acm.org/magazines/2012/1/144810-bufferbloat/fulltext
- RFC 8289, Controlled Delay Active Queue Management (CoDel) — https://www.rfc-editor.org/rfc/rfc8289.html
- RFC 8290, The Flow Queue CoDel Packet Scheduler and AQM — https://www.rfc-editor.org/rfc/rfc8290
- RFC 2474, Definition of the Differentiated Services Field — https://www.rfc-editor.org/rfc/rfc2474
- RFC 2475, An Architecture for Differentiated Services — https://www.rfc-editor.org/rfc/rfc2475
- RFC 3246, An Expedited Forwarding PHB — https://www.rfc-editor.org/rfc/rfc3246
- RFC 2597, Assured Forwarding PHB Group — https://www.rfc-editor.org/rfc/rfc2597
- RFC 2697 / RFC 2698, Single/Two Rate Three Color Markers — https://www.rfc-editor.org/rfc/rfc2697 , https://www.rfc-editor.org/rfc/rfc2698
- RFC 1633, Integrated Services Architecture — https://www.rfc-editor.org/rfc/rfc1633
- RFC 2205, RSVP Version 1 — https://www.rfc-editor.org/rfc/rfc2205
- RFC 2208, RSVP Applicability Statement (scaling concerns) — https://www.rfc-editor.org/rfc/rfc2208
- RFC 2998, IntServ over DiffServ Networks — https://www.rfc-editor.org/rfc/rfc2998
- RFC 9000, QUIC: A UDP-Based Multiplexed and Secure Transport — https://www.rfc-editor.org/rfc/rfc9000
- RFC 9001, Using TLS to Secure QUIC — https://www.rfc-editor.org/rfc/rfc9001
- RFC 8446, TLS 1.3 (session tickets) — https://www.rfc-editor.org/rfc/rfc8446
- Dean & Barroso, "The Tail at Scale," CACM 56(2), 2013 — https://cacm.acm.org/research/the-tail-at-scale/
- RFC 2647, Benchmarking Terminology for Firewall Performance (goodput, §3.17) — https://www.rfc-editor.org/rfc/rfc2647.html
- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," TACL 2024 — https://arxiv.org/abs/2307.03172
