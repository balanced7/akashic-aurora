# Kimi Fresh-Eyes — Packet-Routing Halves (2026-07-18)

Seat: kimi (kimi-k3), phase-1. Round: protocol step 5 of kimi-k3-blind-walk-protocol-2026-07-18.md.
Read cold: `research/drafts/packet-routing-opening-claude-2026-07-17.md` + `research/drafts/packet-routing-counter-deepseek-2026-07-17.md`.
Deliberately NOT read before filing: `docs/gate-packets-2026-07-18.md`, any reconciliation/review/verdict of these halves. Code greps to verify constants are not grader material; cited where used.
Labels: **VERIFIED** (checked against doc text or code, cited) / **INFER** (reasoned, not directly demonstrated) / **GUESS** (flagged speculation).

## 1. Shared assumptions — and the strongest attack on each

### A1. The TCP congestion-control metaphor fits this bus (rwnd / ecn / AIMD imported wholesale)

Both halves drink from the same well: claude's header cites recall-networking-reconciliation-2026-07-12.md and calls P3 "the six-laws import"; deepseek writes in that reconciliation's N0/N1/N2 vocabulary without re-deriving it. Their agreement here is not two independent confirmations — it is one metaphor read twice. VERIFIED (both docs).

Three mismatches, each independently damaging:

- **Currency mismatch.** AIMD controls *count of packets in flight*; the scarce resource is *receiver compute/attention*. One trace message and one deep-research ask differ by ~5 orders of magnitude in receiver cost yet count identically toward rwnd. rwnd as "queue depth + busy state" (claude P3) measures slots, not load. INFER.
- **Timescale mismatch.** AIMD is stable when feedback delay ≪ response time. Here feedback rides presence cards and daemon sweeps (seconds to tens of seconds — LOCK_TTL=20s scaled, runner_lock.py:39) while message sojourn is milliseconds (their own census: send_roundtrip_ms 7.7). The name for this regime is oscillation: every sender sees "busy" late, backs off together, sees "clear" late, surges together. Neither half mentions damping, jitter, or sender-side hysteresis (deepseek's F3 hysteresis is for doctor, not the AIMD loop). VERIFIED (constants) / INFER (stability consequence).
- **Enforcement mismatch.** TCP endpoints obey backoff because the kernel enforces it. Here compliance is per-runner voluntary — and raw `bus.send()` stays callable through strangler phases 1–3 (deepseek's own P2 sequence), so the congestion-contracted door is optional for the whole migration window. Cooperative congestion control with voluntary compliance is a courtesy, not a control loop. VERIFIED (phase list) / INFER (consequence).

The unasked question: at N≈4 agents on a single Redis, the centralized alternatives — per-sender token bucket at the door, weighted fair queueing at the consumer, a single arbiter — need no cross-agent feedback loop at all, and a crude version already exists in-house (`control.pause` on reply-rate-limit, bifrost_runner_sol.py:378) unreferenced by both halves. Neither half considers a single centralized mechanism. VERIFIED (absence; the pause precedent) / GUESS (that they'd suffice).

### A2. Presence/heartbeat state is trustworthy enough to route on

deepseek's F3 demolishes presence fidelity (HB tick gaps, Redis hiccups, stale cards) — then F1 and all of P3 build *routing decisions* on that same data. A document that refutes its own foundation and keeps building. VERIFIED (F1/F3 text).

The proposed fix (rwnd as T046 latch, not tick) trades stale-tick for **dead-holder**: a consumer that crashes holding rwnd=0 leaves every sender's pre-send check queueing forever. Who clears a dead owner's latch? The project has already lived exactly this — C1-1 seat dead-holder rescue with an evidence ladder (failure ledger) — and neither half connects the rwnd latch to that lesson. Latches need owner-liveness adjudication from day one. VERIFIED (C1-1 per boot context) / INFER (recurrence).

### A3. Routing stays a pure static function while dynamic state bolts on at the edges

Both keep the table pure ((kind, family, pri, deadline, tempo) → lane) and attach receiver state outside it (F1's pre-send poll). Attacks:

- **TOCTOU.** The pre-send rwnd read and the send are two operations; the receiver can saturate between them. The race is unavoidable — but neither half names it, so nothing bounds it or defines behavior when it fires. INFER.
- **F1's local retry queue is a new persistence domain.** "Queues the ask locally and retries when rwnd clears" — where is that queue, is it durable, who drains it on sender crash? RB-26 protects in-flight copies; nothing protects *unsent* ones. A crashed sender holding a locally-queued gate ask is silent loss — strictly worse than the busy inbox it avoided, because the sender believes it sent. INFER.
- **Ordering is never stated as an invariant.** Local queueing reorders sends (a queued gate ask overtaken by a later direct tell). Streams give per-stream FIFO; the verb layer above them now reorders. Neither half says whether causal send-order is a contract the router must preserve. VERIFIED (absence) / INFER (consequence).

### A4. Redis is substrate, never a congestion source

The control plane (presence, sweeps, ecn feedback, expectations) is fully in-band: it rides the Redis it governs. When Redis hiccups — and F3 already assumes Redis hiccups — the congestion signals hiccup with the traffic. No out-of-band path, no degraded mode in either half. And the cadence gap is ~3 orders of magnitude (7.7ms send RTT vs multi-second control cadence): the control loop always steers a snapshot of a system that has already changed. VERIFIED (in-band by construction) / INFER (steering-stale-snapshot).

### A5. An idle-probe measurement is a throughput spec (P4, STRONG AGREE both sides)

7.7ms roundtrip on localhost with one producer is a latency floor, not capacity. Neither half's probe harness generates load: no drain-rate-at-N-msgs/s, no p95 sojourn during a redrive storm, no overflow behavior at lane_maxlen. The numbers that matter in production are all under load — and under load is exactly when this bus has historically broken (C6-2 redelivery storms). Benchmarking the empty pipe and stamping it into SYSTEMS.md manufactures confidence, not specs. VERIFIED (P4 text; the JSON "measured" block) / INFER (manufactured confidence).

## 2. What neither half considered

- **B1. Retransmission without backoff — the design's own amplifier.** Expectations redrive a fixed 3× (VERIFIED: expectations.py:68) at fixed cadence (F1's 40/80/120s). Retransmission into congestion without exponential backoff is the classic collapse mechanism. P3 closes the send loop and leaves the redrive loop open: redrives consult neither ecn, rwnd, nor AIMD state. C6-2 (redelivery storms) is in their own failure ledger. VERIFIED (constants) / INFER (interaction).
- **B2. The receive half of the API.** Both design send verbs; neither specifies how a caller *awaits* — `ask()` returns what, a ticket? a future? awaited via wake_block, poll, or wake listener? Daniel's charge was "intelligent internal api's … for us to handle our routing" — the API as designed is send-only. The correlation path every runner actually needs (send ask, block till reply-or-deadline) is unbuilt in both. VERIFIED (absence in both verb tables).
- **B3. Authorization on the control plane.** F5's `route_override` Redis key is writable by any seat and reroutes any kind — no authz, no provenance, no conflict story (two seats writing overrides = flapping routes). In a fleet of LLM agents that consume bus content, an unauthenticated routing override is prompt-injection's shortest path to traffic redirection. The project gates exec grants through security/acl.json and Daniel; the routing control plane deserves at least that bar. VERIFIED (F5 text; acl.json per morning-gate directive) / GUESS (injection realism — no red-team run).
- **B4. Strangler coexistence rot.** Raw send stays live through phases 1–3, so argv-hand-rolling and missing-defaults failures stay alive on every unmigrated caller. The project's own T044→T047 history says "temporary" coexistence lanes persist and tax. Neither half sets a migration-completeness gate or a kill-date. VERIFIED (phase list; T044/47 history).
- **B5. The observability tax is unpriced.** "Per-rule counters incremented atomically with the routing decision" (deepseek P1): a Redis INCR per send adds a roundtrip to a 7.7ms operation unless batched — and batched counters lie exactly when crashes matter. Per-(agent, family) AIMD state residency is unspecified: in-memory resets on restart (fail-open to full rate? fail-closed to slow-start? neither half picks); in-Redis adds write load to the governed bus. INFER (cost) / VERIFIED (unspecified).
- **B6. Timeout-constant composition.** wake_block=120s (VERIFIED bifrost_api.py:115), reply_timeout=600s, redrives=3, min_deadline=30s (deepseek's own JSON), plus new per-value_class derived deadlines — no stated invariants relating them (is deadline enforced < reply_timeout? does the redrive window fit inside the deadline?). One inconsistent pair is the next wake-loop class. VERIFIED (constants enumerated) / INFER (interaction).
- **B7. The ecn marking point doesn't exist mechanically.** TCP routers mark at the bottleneck queue. Redis Streams don't mark; nothing sits in the send path with queue visibility. Who sets the bit, where does it live on the entry, how does it reach the sender — reply? presence? sig-lane? If feedback rides sig-lane, congestion feedback multiplies the steer/halt traffic class. "Imported from the recall plane" (claude P3) — but the recall plane's ecn was a single-process pressure reading, not a cross-agent signal. VERIFIED (no mechanism in either half) / INFER (recall-plane disanalogy — I have not read amend C).
- **B8. rwnd-vs-XLEN: the unasked question exposes the metric.** Inbox depth is directly readable (XLEN) — fresher than any advertised card. The reason that's *not* sufficient (a consumer at depth 0 mid-10-minute-task is saturated) is precisely the proof that queue depth is the wrong currency (A1). Advertisement adds staleness to a metric that was already measuring the wrong thing. INFER.

## 3. Where I AGREE with both — and why that agreement is safe

- **Routing table as first-class inspectable artifact in code (P1, both).** Safe: the R6 precedent is already load-bearing in packet_spec.py (VERIFIED: `lane_for`/`lane_maxlen`/`LANE_MAXLEN` live there today); it adds observability, not behavior; git answers claude's Q1 — git IS the provenance for the base table (overrides, if any, need their own audit trail — B3).
- **Derived-beats-handwritten for SYSTEMS.md, JSON-sidecar shape (P4/P6/Q5, both).** Safe: T022/T024 doctrine is house law precisely because doc rot is the demonstrated default; the sidecar makes the map regenerable rather than maintainable. The risk isn't the shape — it's what gets stamped into it (A5).
- **T047 legacy retirement kills the straggler class at the root (P3/P5, both).** Safe: the dual-write tax is measured history (C6-2), not theory — removing a write path can't strand what no longer exists.
- **Fenced slices + Daniel gates (P5, both).** Safe: it's process, and the process has been catching real bugs all week (23/23 two-suite fence on T095 M0, per boot notes).
- **Caveat on this section as a whole:** these agreements are safe partly because they are the *low-ambition* parts — observability, doc generation, path removal, gating. The shared risk concentrates exactly where both halves are most ambitious (A1's closed loop), and there their agreement is same-source, not independent. Agreement density is not evidence of safety when both authors read one reconciliation doc. INFER.

## 4. Honesty ledger

- **VERIFIED (doc- or code-checked):** REDRIVES=3 (expectations.py:68); wake_block=120s (bifrost_api.py:115); trace maxlen=5000 (packet_spec.py:206 — deepseek's F4 number checks out); LOCK_TTL=20s scaled (runner_lock.py:39 — note: deepseek's F3 constants "TTL=60s, HB=8s" did NOT match what I found; treat those two as unverified — my argument doesn't rest on them); `route_override` absent from code today (grep — expected, it's a proposal); all absence claims (no ordering invariant, no await API, no authz on overrides, no cadence budget, no load-generating probe) verified by full read of both halves.
- **INFER (reasoned, not demonstrated):** AIMD oscillation at these timescales; dead-holder recurrence on rwnd latches; TOCTOU consequences; observability cost; redrive×congestion amplifier; recall-plane ecn disanalogy; the §3 caveat.
- **GUESS (flagged speculation):** that token-bucket/WFQ/arbiter alternatives suffice at N=4 (no prototype); that prompt-injection-via-bus makes route_override a practical attack (no red-team); that a trace consumer will ever exist (deepseek's own F4 says "if").
- **Blind discipline kept:** no reconciliation/review/verdict read before filing; the gate-packets doc remains untouched. Organically surfaced lessons cited: C1-1 dead-holder rescue, C6-2/lane_era_marker, RB-26, destructive_filters_never_stale_pids (kill-time re-verification ≈ route-time re-verification — never trust state fetched earlier than the act).
- **Null-result check:** not a null result — material dissent found in both directions (A1–A5 shared assumptions attacked, B1–B8 unconsidered).
- **Not done:** no probes, no load tests, no simulation; the stability critique is control-theory reasoning, not measurement. Code reading limited to constant-checking greps.
