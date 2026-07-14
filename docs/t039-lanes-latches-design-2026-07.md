# T039 — Purpose-keyed lanes + latches — GOVERNING DESIGN (decision record)

Status: current (2026-07-13)
Class: governing design doc for the T039 arc (the file the brief's Produces line promised; closes
review finding F2). Thin by design — the full rationale lives in the fenced records below; this doc
records WHAT governs and WHO decided.

## One sentence
Partition the single bifrost stream into a capped lane roster (work / sig / trace / test-*) with a
pure kind->lane router at the send door, migrate strangler-fig with per-cutover storm bars, and add
latch v1 (within-flow causal + cross-flow reference) so process rules become transport invariants.

## The decision record (read in this order)
1. research/t039-lanes-latches-design-brief-2026-07-13.md — the blind brief (M1 fence)
2. research/reviewed/claude-t039-lanes-latches-2026-07-13.md — claude blind half
3. research/reviewed/deepseek-t039-lanes-latches-2026-07-13.md — deepseek blind half (verbatim)
4. research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md — CONVERGED architecture,
   D-1..D-4 resolutions, build sub-slices
5. research/reviewed/claude-t039-design-review-2026-07-13.md — review: amendments A1'-A4, pins
   P1-P4, findings F1-F3, round addenda
6. research/reviewed/deepseek-t039-review-countercheck-2026-07-13.md — VALID counter-check (round
   3, full-capability lane): all items AFFIRMED + M1-M4. (r1/r2 records: INVALID, kept as method
   evidence.)
Rides the LAW packet spec: docs/packet-spec-v1-2026-07.md.

## GATE — Daniel, 2026-07-13 (recorded verbatim from the ruling)
1. APPROVED: design governs; T039a-d register citing this doc.
2. CONFIRMED D-1: keep per-agent XREAD + RB-21 generation-fenced seat; NO consumer groups.
3. CONFIRMED: cross-flow ENFORCEMENT latches are CUT from v1 (cross-flow = reference only);
   within-flow causal latches only (seq(from) < seq(new) — cycle-free by construction).
4. CONFIRMED sequencing: lanes (T039a/b) -> latches (T039c) -> T038 tokens.
AMENDMENTS: fold ALL — A1', A2, A3, A4, P1-P4, plus counter-check M1 (folds into P2) and M2 (new
T039b bar). First build: T039a.

## Folded amendments (registration-time bars; full text in the review)
- A1' (T039c): per-flow blocked QUEUE re-drained in per-flow seq order (not a set). S7 sub-bar:
  deferred flow-head with 2 buffered same-flow successors un-defers in seq order.
- A2 (T039c): review-gates-ship requires the whole chain to thread ONE flow id; state the door
  discipline; flagship L-bar demo = ship packet refused until review-GREEN exists in its flow.
- A3 (T039a): grep-gated READER CENSUS bar; known census: runner via bifrost_api, wake listener,
  core/comm/doctor.py, scripts/bifrost_ui.py, scripts/bifrost_console.py, agent_cli.py
  cmd_bifrost_sync -> agent/bifrost_pull.py consume_inbox. promoter.py is push-side (not a reader).
- A4 (T039b): lane-cursor initialization at the cutover flip (tail-at-flip or quiesced flip) —
  the atomic flag stops dual-source reads, NOT backlog replay. S1 rerun is the catching bar.
- P1 (T039c): latch index = PER-LATCH key (envelope already carries latch ids; one GET).
- P2+M1 (T039c): unlatch rings the WORK bell and CARRIES the satisfied latch id(s); the consumer's
  deferred-set is indexed by gating latch id (no O(N) re-check).
- P3 (T039b): consumer loop drains sig BETWEEN work packets (EF-beats-AF at the consumer, not just
  the streams).
- P4 (T039b): work-bell ring policy — note/status must not wake idle seats; pick door-side or
  listener-side kind filter at registration.
- M2 (T039b): dual-write retention guard — cutover order bounded by lane retention windows, or
  dual-write retention = MAX(legacy, lane) for the migration window.

## Lane roster (the stable contract; per-lane detail = packet spec PER-LANE CONTRACT)
| lane   | QoS      | seat                | wake            | retention          |
|--------|----------|---------------------|-----------------|--------------------|
| work   | QoS1/AF  | RB-21 fenced seat   | THE wake lane   | maxlen 10k, REFUSE |
| sig    | QoS1/EF  | seatless + cursor   | no wake (bell)  | maxlen 5k, REFUSE  |
| trace  | QoS0/BE  | none (firehose)     | never           | XTRIM ring 5k      |
| test-* | as work  | per-namespace seat  | in-ns only      | 10k + ns TTL       |
Roster CAPPED at these four; adding a lane requires a why-not-an-existing answer + deletion ritual
(drain -> unroute -> remove keys -> ledger event).

## Build sub-slices (register citing this doc; each fenced + gated)
- T039a: kind->lane router (pure table) + per-lane key shapes + dual-write at the door + trace
  integrity exemption (packet_spec.lane_wants_integrity + global spot counter, folds T043 R5 debt)
  + reader census bar. Consumers UNTOUCHED. Bars: per-kind router pins (control->sig NEVER trace),
  exemption spot-check, dual-write leaves legacy byte-identical, census table committed, full
  regression green.
- T039b: consumer cutover (strangler; wake-listener first, then runner) + A4 cursor-init + P3
  sig-interleave + P4 bell filter + M2 retention guard. Bars: RB-25 S1-S5 per cutover + S2-NEW +
  S6.
- T039c: latch v1 (within-flow causal + ref) + A1' flow-FIFO + A2 flow-threading demo + P1 per-
  latch key + P2/M1 latch-id bell. Bars: L1-L3 + S7 (incl. A1' sub-bar); R8 binds enforcement
  families behind full-path v2.
- T039d: retire legacy + roster registry + deletion ritual (ledger event).
