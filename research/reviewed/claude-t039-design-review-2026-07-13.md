# T039 lanes+latches — claude DESIGN REVIEW (post-reconciliation, pre-registration)

Status: current (2026-07-13)
Class: design review (claude, Fable seat). Reviews the reconciled T039 design:
research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md (+ both blind halves + brief).
Fence: this is claude's half of the REVIEW stage. deepseek counter-check requested via bus
2026-07-13 (durable handoff = this file). Amendments fold into T039a–d registration ONLY after
the counter-check lands and Daniel's design gate (reconciliation "OPEN FOR DANIEL" 1–4) answers.

## VERDICT: APPROVE-WITH-AMENDMENTS
The architecture is settled and the fence demonstrably worked: two blind halves converged on the
same lane mechanism (per-lane stream keys, pure kind→lane router at the door, wake = work-bell-only
so wake-on-trace is impossible BY CONSTRUCTION), the same worst risk (misrouted halt→trace), and
the same guard. D-1 (keep XREAD+RB-21 per-agent inboxes; consumer groups load-balance = the
documented broadcast-reached-one-agent bug) is correctly grounded in bus history. D-2 is a true
synthesis better than either half: deepseek's within-flow DAG (cycle-free by construction — a
causal latch may only point backward within its own flow) + claude's defer-not-HOL-block consumer
+ deepseek's L4-down ttl backstop. Cut lists are honest; T043's R5 trace-exemption debt is
correctly folded into T039a. Nothing below overturns the architecture.

## AMENDMENTS (design-level; fold into sub-slice registration)

### A1 (T039c) Flow-FIFO across a deferral — the one design-level miss
Deferring packet N of flow F while processing N+1 of flow F breaks per-flow ordering exactly where
per-flow seq promises it. QUIC's actual model: FIFO WITHIN a stream, independence ACROSS streams.
Fix: key the consumer blocked-set BY FLOW — when a flow's head is deferred on a latch, its
same-flow successors queue behind it in the blocked-set; packets of other flows proceed. Cost:
one flow-id membership check on drain. Add an S7 sub-bar: mid-drain deferral of flow-head →
same-flow successor is NOT processed before it; cross-flow packet IS.

### A2 (T039c) "Review gates commit" requires flow-threading — state it + demo it
With cross-flow enforcement CUT from v1, the brief's own motivating invariant only works when the
whole review→ship chain rides ONE flow id. Doors already propagate flow on reply/redrive/ack, but
the SHIP act must emit a packet in that same flow. State this discipline in the design doc, and
make it the flagship T039c L-bar demo: a ship packet transport-REFUSED until the review-GREEN
packet exists in its flow. Convergence note: this makes T031 (method enforcement) and T039c the
same idea at two layers — the transport becomes the method's enforcement hook.

### A3 (T039a) Reader census bar (grep-gated)
The migration names wake-listener, runner, trace sinks. Source grep (xread/xrange/xrevrange, live
code only) finds the ACTUAL census: runner via bifrost_api, wake listener, core/comm/doctor.py
(stalled-consumer math must move to work-lane depth), scripts/bifrost_ui.py (stream tail),
scripts/bifrost_console.py, and boot/bifrost-sync's unread peek. promoter.py is push-side (promotes
at send; reads the EVENT firehose for acks) — NOT a stream reader. Bar: T039a ships with a
grep-gated reader census table; T039b's cutover order covers EVERY row or names why a row is
unaffected. (Lesson no_relocation_arg_needs_source_grep_gate, institutionalized.)

### A4 (T039b) Cursor initialization at the cutover flip
The atomic read-source flag-flip prevents dual-source reads but NOT backlog replay: a consumer
cutting to its lane inbox mid-dual-write replays everything dual-written since P0 unless its lane
cursor initializes to tail-at-flip (or the flip happens quiesced). Define the init rule explicitly;
S1's per-cutover rerun (0 lost, answered exactly once) is the catching bar.

## REGISTRATION PINS (small; pin at T039b/c registration)
- P1 (T039c): latch INDEX shape was never actually merged — claude half: `{ns}:latch:open` HASH
  keyed by latched packet id (one HGET); deepseek half: per-latch key GET driven off the envelope's
  latch[]. Pick ONE (either satisfies "one GET on the hot path"; per-latch key composes better with
  the envelope already carrying latch ids).
- P2 (T039c): unlatch signaling unspecified — ring the WORK bell (a deferred work packet becoming
  ready IS work-lane traffic; keeps the wake story single-lane).
- P3 (T039b): pin sig-drained-BEFORE-work at the consumer loop (peek sig between work packets, not
  between full drains) — S6 tests sig vs trace flood, not sig vs work backlog; without this, steers
  apply stale. EF-beats-AF must hold at the consumer, not just at the streams.
- P4 (T039b): work-bell ring policy — lanes kill wake-on-trace, not wake-on-boring. kind=note/
  status packets must not wake idle (Fable) seats: either the door rings the bell only for
  wake-worthy kinds, or the listener keeps its kind filter. Name which.

## PROCESS FINDINGS (feed T031)
- F1: brief + both halves + reconciliation landed in ONE commit (e15911a) — blindness is real but
  not git-auditable. Second motivating data point for T031's pre-registration checker (brief/
  acceptance commit <= halves commit). Priority up.
- F2: the brief's Produces line promises docs/t039-lanes-latches-design-2026-07.md — never
  produced. Either emit it when the gate closes (reconciliation + folded amendments graduate to
  docs/) or amend the Produces line. Doc-currency (T024) wants the governing artifact findable.
- F3: receipts hygiene — the 07-12 fence receipts sat untracked until this review's mirror run.
  Verbatim-persist discipline held; COMMIT discipline lagged a session. (T031 item 4 territory.)

## OPEN
1. deepseek counter-check verdict on A1–A4 / P1–P4 (this file = the durable handoff).
2. Daniel design gate (reconciliation items 1–4) + whether A1/A2 fold in pre-registration
   (recommended: yes — both are registration-time text, no rework of the converged architecture).

## ROUND-2 ADDENDUM (2026-07-13) — FENCE CLOSED, CHECK INVALID ×2
r2 was worse: tool-call-as-text (write_file emitted as prose, never executed), cut mid-report
again, and a CONFABULATED corpus (nonexistent filenames, invented spec section/field width, a
strawman A2, network-on-chip vocabulary describing no part of this system). Bounded rounds
exhausted; NO round 3. **This review stands as a claude-only half (unfenced)** pending Daniel:
rerun the check through a FULL deepseek session lane, or accept claude-only at the gate. Root
cause + receipts: deepseek-t039-review-countercheck-2026-07-13-r2-invalid.md. Two live receipts
now support folding "runner replies ride the packet integrity door" into T039a scope. Lessons:
fence_report_citation_path_gate, fence_heavy_asks_need_full_session_lane.

## ROUND-1 ADDENDUM (2026-07-13, post counter-check r1)
- deepseek's r1 reply was EVIDENCE-INVALID (cited nonexistent `bifrost/lane.py` — T039 has no
  build) and CUT mid-A2 (token ceiling). Round-2 re-ask sent: re-ground vs design docs, deliver
  via write_file. Record: deepseek-t039-review-countercheck-2026-07-13-r1-partial.md.
- **A1 → A1′ (accepted sharpening from r1's surviving conceptual core):** the per-flow blocked
  structure must be a QUEUE re-drained in per-flow **seq** order, not a set — mutual exclusion
  alone still breaks within-flow order at un-deferral. S7 sub-bar updated accordingly: defer
  flow-head with TWO buffered same-flow successors → un-defer → successors process in seq order.
