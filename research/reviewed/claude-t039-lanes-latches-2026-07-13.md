# claude BLIND half — T039 lanes + latches design (SEALED until deepseek's lands)

Status: current (2026-07-13)
Class: design half (claude, blind). Brief: research/t039-lanes-latches-design-brief-2026-07-13.md.
Written BEFORE seeing deepseek's half. Reconcile after.

## A. LANE MECHANISM — lane is a KEY DIMENSION, orthogonal to agent + namespace
Today: `{ns}:inbox:{agent}` (all directed kinds merged), `{ns}:broadcast` (all fan-out merged),
cursor `{ns}:cursor:{agent}` (inbox+bc), doorbell `{ns}:bell:{to}`. Namespace = test isolation (KEEP).
Lane is a NEW dimension inserted before the topology suffix, so each lane keeps its own contract:

  work : `{ns}:work:inbox:{agent}`  + `{ns}:work:broadcast`   -- per-agent, RB-21 SEATED, cursor'd, BELL
  sig  : `{ns}:sig:inbox:{agent}`                              -- per-agent, SEATLESS, cursor'd, BELL (barge-in)
  trace: `{ns}:trace`  (ONE shared ring, XTRIM 5000)          -- seatless firehose, NO per-agent inbox, NO bell
  test-*: `{ns}:test-{suffix}:work:inbox:{agent}` ...         -- as work, per drill namespace + TTL

Router (pure dict at the SEND door): `KIND_LANE = {handoff:work, reply:work, request:work, note:work,
answer:work, dispatch:work, status:work, nudge:sig, steer:sig, halt:sig, interrupt:sig, pause:sig,
thinking:trace, tool:trace, narration:trace}`. Unknown kind → REFUSED loud (spec). The door picks the
stream key from (lane, to). Cursor/seat/bell PER LANE:
- work: cursor `{ns}:work:cursor:{agent}`, RB-21 generation-fenced seat, bell `{ns}:work:bell:{agent}`.
  WAKE-LISTENERS SUBSCRIBE ONLY to `{ns}:work:bell:*` -> trace/sig can never wake (S2-NEW by construction).
- sig: cursor `{ns}:sig:cursor:{agent}`, NO seat (any runner reads between rounds), bell for barge-in.
- trace: no cursor/seat/bell; consumers tail live or from a LOCAL ephemeral position. Pure QoS0 firehose.
Rationale: the lane dimension makes the per-lane contract STRUCTURAL (seat exists only where the key has
a cursor+generation), not enforced by convention. `broadcast` splits per-lane (work broadcast vs trace ring).

## B. MIGRATION — strangler fig, consumer-by-consumer, wake-listener FIRST
- P0 DUAL-WRITE: the send door writes BOTH legacy `{ns}:inbox` AND `{ns}:{lane}:...`. Consumers still read
  legacy. (Router lives at the door already, so this is one code site.)
- P1 CUT THE WAKE-LISTENER first (highest payoff, lowest risk): it subscribes to `{ns}:work:bell:*` only.
  Trace/sig can no longer wake it. Rerun S1-S5 + S2-NEW here.
- P2 CUT THE RUNNER CONSUMER: reads work-lane inbox (seated) + sig-lane inbox (between rounds); ignores
  trace. Rerun S1-S5 + S6 (HALT latency under a trace flood -- sig must beat the flood).
- P3 CUT TRACE PRODUCERS to trace-only (stop dual-writing trace to legacy). The broadcast lane shrinks to
  work-broadcast. S7 (per-flow seq / latch storm) once multi-lane consumers exist.
- P4 RETIRE legacy `{ns}:inbox`/`{ns}:broadcast` (ledger event). 
Double-delivery avoidance: each consumer reads exactly ONE source; cutover = an atomic per-consumer
read-source flag flip. ROLLBACK = flip the flag back (dual-write keeps legacy live until P4). Cost: 2x
writes during the bounded window (acceptable; strangler standard).

## C. LATCH v1 (causal + ref; bundle DEFERRED)
- INDEX (spec: one GET on the hot path): `{ns}:latch:open` HASH, field=latched_packet_id, value=json of
  its unsatisfied enforce-gates. A consumer reading a latched work packet does ONE `HGET {ns}:latch:open
  <id>`; absent = satisfied/none, proceed. Satisfaction (the from_id consumed) HDELs the field + rings an
  unlatch on the waiters.
- CYCLE CHECK AT CREATION: the door walks the new edge's transitive closure over `{ns}:latch:edges`
  (adjacency: packet_id -> [from_ids]); if the new edge closes a cycle, REFUSE naming the path. Bounded by
  graph depth (latches are rare/deliberate).
- EXPIRY REUSES L4: a causal-latch is armed like an L4 expectation with a gate predicate; the L4 sweep
  fires expiry per fail-direction (enforce -> stays BLOCKED loud + dead event; depend -> proceeds degraded
  loud). ONE temporal engine, two vocabularies. ttl_s = the expectation window.
- BLOCKED-PACKET SEMANTICS (avoid lane-wide HOL, per the QUIC lens): a work packet whose enforce-latch
  gate is unsatisfied is DEFERRED, not HOL-blocking -- advance the cursor past it, buffer it in a
  consumer-local blocked-set (REUSE the T043 advance-and-buffer + Redis-durable pattern), re-check on the
  next drain and on an unlatch bell; enforce/depend fires at ttl expiry. So orchestration is parallel-by-
  default, serialized only on the exact latched edge. Per-lane fencing: only WORK needs the RB-21 seat;
  sig/trace are seatless so no generation contention.

## D. NETWORKING PRIOR-ART GRADE (adopt / adapt / skip)
- DiffServ/DSCP: ADOPT (concept) -- the per-lane QoS classes ARE DiffServ (work=AF, sig=EF, trace=BE).
  Adopt the class semantics (already LAW); SKIP the DSCP bits (we key by lane).
- QUIC multiplexed streams: ADOPT the RATIONALE -- independent per-lane delivery so a stalled/latched
  work packet never blocks a sig packet; adopt "deferred latched packet doesn't HOL its lane." SKIP QUIC's
  wire format/crypto.
- TCP state machine + TIME_WAIT: SKIP here (it is T038 token lifecycle; note the mapping only).
- MTU/frag + checksum-at-door: DONE (T043). SKIP (already adopted).
- W3C Trace Context / OTel span+links: ADOPT the SHAPE -- flow=trace_id (LAW), ref-latch=link,
  causal-latch=parent-span; the latch graph is OTel-exportable. SKIP building the exporter (spec Phase 4).
- gRPC deadline propagation: ADAPT -- a latched packet INHERITS its gate's L4 deadline (deadline flows
  down the causal chain). Adapt into the L4 engine; SKIP gRPC's wire.
- SDN control/data-plane split: ADOPT as the sig framing -- sig = control plane (halt/steer/pause), work =
  data plane; invariant "control plane is never starved by data plane" (sig=EF, REFUSE-WRITE not trim).

## E. TRACE EXEMPTION (T043 inheritance)
Policy lives in packet_spec (integrity SSOT); the LANE is the input. Add `packet_spec.lane_wants_integrity
(lane, counter) -> bool`: True for work/sig/test-*, and for trace only when counter % 1000 == 0 (amend E)
or PACKET_INTEGRITY_TRACE on. The SEND door, having routed to a lane, calls it and stamps len+sha
accordingly. Router = lane SSOT; packet_spec = integrity SSOT; the door composes them.

## F. ROSTER DISCIPLINE + CUT LIST
4-lane cap CONFIRMED (work/sig/trace/test-*). Roster registry = a small manifest (name, class QoS, seat?,
wake?, introduced, removed) -- lives beside the T034 dial manifest. DELETION RITUAL: (1) grep + live audit
proving no producer emits the lane's kinds; (2) migrate/retire consumers; (3) tombstone with removed-date
+ ledger event. CUT from v1 (named for honesty): bundle-latch, latch.gate expression language, sender-
chosen lanes, a 5th lane, the OTel exporter (Phase 4), per-flow-seq enforcement beyond S7's exercise.

## G. RISKS / KILL-CONDITIONS
- WORST: a router bug misroutes a `halt` (control) to the trace ring (lossy XTRIM) -> HALT lost -> runaway
  agent not stopped. GUARDS (three, defense-in-depth): (1) the router is a PURE table with a PER-KIND pin
  asserting every control kind -> sig, NEVER trace; (2) sig is REFUSE-WRITE (never trimmed) so even at
  overflow a halt refuses loud, never silently drops; (3) S6 bar proves sig beats a trace flood. The halt
  hard-path ALSO keeps its existing Redis control-key + doorbell (spec V1-HONESTY: sig complements, does
  not replace, the control key) -> a lost sig packet is not a lost halt.
- Latch cycle deadlocks work lane -> GUARD: DAG-at-creation cycle refusal + L4 latch-expiry.
- Migration double-delivery -> GUARD: one-source-per-consumer + atomic cutover flag + rollback.
- Trace ring starves nothing (QoS0, its own key) -> a trace flood cannot touch work/sig streams (separate
  keys, separate maxlen). This is the whole point, and it is STRUCTURAL not policed.
