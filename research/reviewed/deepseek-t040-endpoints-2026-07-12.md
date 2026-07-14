# T040 Endpoint / System Exploration — deepseek BLIND half

Date: 2026-07-12
Class: fenced dual DESIGN (deepseek half, independent; claude's half sealed; reconcile after)
Charter: research/t040-review-brief-2026-07-12.md Q2
Spec: docs/packet-spec-v1-2026-07.md (the packet alphabet this explores)
Prior art informing this: recall-networking reconciliation (C1-C9, N0-N7), frontier-net-routing
  (SDN match-action with miss path, flap dampening, anycast tiers), frontier-net-transport
  (CoDel/AQM, goodput vs throughput), Daniel steer "packets as the universal plug" (ACI thesis),
  T041 slice scope (pluggable endpoints dream-gate: zero new verbs, discover gets shorter)

---

## ORGANIZING RULE

I derive the rule from the frontier-net-routing transfer 7.4 (SDN match-action tables): **every
endpoint is a TABLE — a materialized projection of the packet stream, updated incrementally, queried
in O(1).** No endpoint "does work" on the hot path; each endpoint COMPILES the packet stream into
a shape that answers one class of question instantly.

This gives us a taxonomy:

1. **OBSERVER** — a read-only projection. Subscribes to families, maintains a materialized view,
   answers queries from the view. Replaces polling. (SDN: the controller's view of the data plane.)

2. **GATE** — a write-side enforcer. Intercepts packets at the send door, validates against
   pre-registered rules, refuses or transforms. Replaces ad-hoc validation scattered across send
   paths. (SDN: the table-miss entry that punts to the controller.)

3. **ACTUATOR** — a read-write loop. Consumes packets in family A, emits packets in family B as a
   result. The only endpoint type that PRODUCES new packets (beyond query answers). Replaces cron
   jobs and daemon loops. (SDN: the reactive flow-install path.)

4. **SINK** — a terminal consumer. Consumes packets and exits the bus — its output is a non-packet
   surface (a file, a DOM, a notification). Replaces UI polling and log scraping. (SDN: the counter
   export path.)

Every endpoint in this proposal is exactly one of these four shapes. The shape determines its
families, its state, and its failure mode.

---

## THE ENDPOINTS

### E1 — Substrate Observer-Projector (OBSERVER)

**Shape:** OBSERVER
**Families consumed:** status, trace (firehose, tail-sampled), presence-beat
**Families emitted:** answer (to query family packets)
**State:** materialized dict `{agent: {phase, backlog, last_seen, wedged, ...}}` updated
  incrementally from consumed packets; no polling.
**Replaces:** the fleet doctor's poll loop (`doctor.py` probes Redis keys on a timer), the
  `bifrost-sync` peek path, the `agent_cli.py doctor` command's N Redis reads, the presence roster
  assembly at boot
**Why it earns its keep:** Today, asking "is the fleet healthy?" costs O(agents × Redis keys) and
  the answer is assembled at ask-time. SOP inverts this: the answer is MAINTAINED continuously from
  the packet stream, and the query is O(1) against the materialized view. This is the SDN pattern
  exactly: the control plane maintains the view; the data plane queries it instantly.
**Concrete query:** `query {target: fleet, question: "agents_online"}` → `answer {agents: ["claude",
  "deepseek"], freshness_ts: 2026-07-12T21:17:17Z}`. The existing `doctor` command and UI health
  panel become thin consumers of SOP's answer family instead of reading Redis directly.
**Failure mode:** stale view (SOP falls behind the packet stream) → answer carries `freshness_ts`
  and the consumer decides whether to trust it. Never blocks the query path.
**Family roster impact:** zero new families. SOP consumes `status` + `trace` + `presence-beat`
  (all existing/planned), emits `answer` (existing). No new entries in the family cap.

### E2 — Exam Bar Continuous Monitor (OBSERVER)

**Shape:** OBSERVER
**Families consumed:** trace (firehose — every packet), status
**Families emitted:** status (exam bar state: PASSING/DEGRADED/FAILING/ARMED)
**State:** per-bar predicate evaluator fed from the trace stream; each bar is a pre-registered
  function `(packet, current_state) → new_state` with hysteresis.
**Replaces:** the manual "run drill, capture evidence, score bars" cycle; RB-25 drill 4's 72h
  checkpoint table; the operator checking RSS at T0/T24/T48/T72 by hand
**Why it earns its keep:** Today's exam bars are point-checks at drill completion. EBCM makes them
  CONTINUOUS: a bar that drifts from PASS to DEGRADED between checkpoints fires a status packet
  IMMEDIATELY, not at the next human check. The drill 4 K1 bar (RSS +15% bound) becomes a live
  monitor instead of a checkpoint query. The frontier-net lesson: counters on flow entries (SDN §7.4)
  — every bar is a counter on the packet stream, evaluated per-packet, surfaced continuously.
**Concrete output:** `status {exam: "T029-drill4", bar: "K1", state: "DEGRADED", metric: "+16.3%",
  threshold: "+15%", since: "2026-07-13T04:22:00Z"}`. The UI subscribes to exam status and renders
  a live bar dashboard.
**Failure mode:** EBCM falls behind the trace firehose → it skips non-critical evaluation and emits
  `status {state: "DEGRADED", reason: "evaluator_lagging"}` so the operator knows the bars are
  stale. Trace is QoS0 — dropping is correct.
**Family roster impact:** zero new families. EBCM consumes `trace` + `status`, emits `status`. Same
  families, new semantics within the `status` envelope (exam state is a new `status` sub-type).

### E3 — Bus Recorder / Replayer (OBSERVER + ACTUATOR)

**Shape:** OBSERVER (record mode) + ACTUATOR (replay mode)
**Families consumed:** trace (firehose, record mode)
**Families emitted:** status (recording state), plus it RE-INJECTS recorded packets into a target
  namespace during replay (using existing send paths, not a new family)
**State:** ring buffer of `{ts, envelope}` entries, bounded by trace lane retention or a separate
  time cap (configurable, default 1h / 50K entries).
**Replaces:** the ad-hoc "save logs to research/reviewed/" pattern, the manual evidence bundle dump,
  the "replay tonight's 3 clip payloads" riding build pin (currently manual)
**Why it earns its keep:** The riding build pin 10 requires deterministic replay of recorded traffic
  into a test namespace. That capability does not exist. BRR provides it as a subscription: it's a
  tailing consumer on the trace firehose, recording every packet to an in-process ring buffer, and
  it can replay a time range on demand. Additionally enables: (a) postmortem ("what happened in the
  30s before the fleet wedged?"), (b) drill evidence capture as a continuous subscription instead of
  a manual evidence dump, (c) the RB-29 expectation sweep verifying against recorded history.
**Concrete capability:** `py agent_cli.py bus-replay --from "2026-07-12T21:17:00" --to
  "2026-07-12T21:17:20" --namespace rb25drill3-replay` replays storm 4ddf0a71 packets into an
  isolated namespace. The riding build's pin 10 becomes a script instead of a manual procedure.
**Anti-scope:** NOT a durable event store — the ring buffer is bounded and in-memory. The chronicler
  slice (future) is the durable path. BRR is the operational "what just happened" tool. One machine,
  one buffer — the N<10 agents constraint means 50K entries covers ~hours of traffic.
**Failure mode:** buffer full → oldest entries evicted (ring buffer). Replay against a dead namespace
  → packets queue; consumer never starts → packets sit until TTL. Neither is silent.
**New verb:** 1 (`bus-replay`). This is the one genuinely new capability in the roster — deterministic
  replay from a recorded trace has no existing CLI equivalent. Worth its verb.

### E4 — Event-Sourced UI Projector (SINK)

**Shape:** SINK
**Families consumed:** trace, status, answer, context-delta (FM12-gated, future)
**Families emitted:** (none — terminal consumer; output is the UI DOM)
**State:** materialized UI state tree updated incrementally from every consumed packet.
**Replaces:** the Bifrost UI's current polling loop (`/api/streams`, `/api/unread`, `/api/doctor`,
  `/api/promoted`), the T002 trace-collapse work, the T033 UI design-language work
**Why it earns its keep:** Per Daniel's UI pause directive: the structural overhaul must come first.
  ESUP IS that overhaul. Today the UI polls N Redis endpoints and stitches results into a view.
  ESUP subscribes to the packet stream and projects it into a materialized UI state — each incoming
  packet is a state transition; the UI re-renders by diffing new state against old. This is the
  CEF/FIB pattern applied to UI: precompute the view from the stream, serve from the projection.
**Concrete transformation:** When runner A answers runner B, an `answer` family packet lands in the
  trace stream. ESUP updates the conversation view in its state tree, and the UI diff-renders the
  new message — no polling, no `/api/unread` endpoint. The T002 "collapse traces into one card"
  becomes a projection rule: all trace packets with the same `flow` id render as a single
  collapsible card. The T007 "Void theme" becomes a projection rule: all packets render through
  the Void CSS filter. New UI features become projection rules, not new API endpoints.
**Surface-area reduction:** The UI's HTTP API surface shrinks from ~6 polling endpoints to 1
  (the SSE/WebSocket that carries the projection diff). The `/api/streams`, `/api/unread`,
  `/api/doctor`, `/api/promoted` endpoints RETIRE. The `discover` output gets SHORTER.
**Failure mode:** ESUP falls behind the packet stream → UI shows a "catching up" indicator with
  the lag in seconds. Trace is QoS0; dropping is visible but non-destructive (the next packet
  advances the view).

### E5 — Recall FIB Compiler (OBSERVER)

**Shape:** OBSERVER
**Families consumed:** context-delta (FM12-gated), ledger_update
**Families emitted:** answer (to recall queries), status (FIB staleness)
**State:** materialized FIB: `trigger_pattern → [ranked lesson_ids]` updated incrementally from
  context-delta packets. Cold miss → slow-path funnel search → installs result as a new FIB entry
  (the SDN table-miss pattern from frontier-net-routing §7.4).
**Replaces:** the current boot-time "assemble onboarding context" path (`agent_cli.py boot` iterating
  the entire lesson store), the recall funnel's per-query ranking, the `knowledge_recall` tool's
  linear scan
**Why it earns its keep:** The recall reconciliation's central finding: the funnel has 4.5% goodput
  because it RE-RANKS on every query instead of compiling once. RFW is the N3 slice's engine: it
  subscribes to context-delta packets (new lessons, supersessions, graduations), maintains a
  materialized FIB, and answers recall queries in O(1). At boot, the agent queries RFW with its task
  signature and receives pre-ranked context in one `answer` packet. The expensive ranking happens
  ONCE at publication time, not at query time. The SDN table-miss pattern makes the FIB self-healing:
  an unrecognized context punts to the slow path, whose result installs as a new FIB entry.
**Concrete capability:** `query {target: "recall-fib", question: "context_for", params: {agent:
  "claude", task: "packet-substrate", budget: 8000}}` → `answer {lessons: [{id, title,
  relevance_score}, ...], freshness_ts: ..., covered_by: "aurora:/packet-substrate/"}`. The
  `knowledge_recall` tool becomes a thin consumer of RFW's answer family.
**Failure mode:** FIB miss → slow-path funnel search → answer carries `freshness_ts` showing it was
  live-computed (higher latency, but correct). FIB entry stale → lesson superseded → context-delta
  packet removes it; next query recompiles. The FIB is honestly a cache (frontier-net-routing §8
  transfer 4: "the recall FIB is honestly a cache, not a FIB") — misses are expected and the slow
  path stays fully operational.
**Family roster impact:** consumes `context-delta` (reserved, not shipping in v1 — FM12 gate) and
  `ledger_update` (existing). Emits `answer` (existing). Zero new families. Defers to post-FM12.

### E6 — Send-Door Gate (GATE)

**Shape:** GATE
**Families consumed:** (intercepts at the send door — not a bus consumer; hooks into the door)
**Families emitted:** (none — it's a validator; rejects emit error packets to the sender)
**State:** pre-registered validation rules keyed by `(kind, lane, sender)`.
**Replaces:** ad-hoc validation scattered across `bus.send()`, `bus.broadcast()`, the runner's send
  path, the UI's send path — currently not centralized, not auditable, not discoverable.
**Why it earns its keep:** The packet spec defines the envelope contract. The send door is where that
  contract is ENFORCED. Today there is no single enforcement point — each caller does its own
  validation (or doesn't). SDG is the door itself: every `bus.send()` and `bus.broadcast()` passes
  through it. It validates: MTU (refuse >64KB), kind→lane mapping (refuse unknown kind), family ACL
  (refuse quarantined sender on gated families), envelope field constraints (refuse bad flow format,
  oversize idempotency_key), latch DAG cycles (refuse at creation). The riding build's first 9 pins
  are all send-door validations — SDG is the home for every one of them.
**Concrete impact:** The send door becomes a single Python module (`core/comm/send_door.py`) with a
  `validate(envelope) → (ok, error_packet)` function. Every send path calls it. The MTU pin (65,537
  bytes refused loud) is a one-line entry in SDG's rule table. Adding a new validation is adding a
  rule, not hunting through N call sites.
**Failure mode:** door crash → send fails closed (refused with internal error). The fail-direction law
  (D1) applies: enforcement gates fail CLOSED. A kill-switch dial (`SEND_DOOR_ENFORCE`, default True)
  lets the operator degrade to warn-only in an emergency.
**Family roster impact:** zero new families. SDG is infrastructure, not a bus consumer — it's a
  function called by the send path. No family entry needed.

### E7 — Expectation Sweep Actuator (ACTUATOR)

**Shape:** ACTUATOR
**Families consumed:** trace (specifically: replies landing, filtered by `kind=reply` and
  `meta.answers=<orig_id>`)
**Families emitted:** ack (to clear armed expectations), expectation_dead (when redrives exhausted)
**State:** armed expectations indexed by `orig_id` → `{sender, deadline, attempt}`.
**Replaces:** the current L4 sweep in `expectations.py` — which is a PULL model (the sender sweeps
  at render time). ESA is a PUSH model: it watches the reply stream and clears expectations the
  MOMENT the reply lands, without waiting for the sender's next render cycle.
**Why it earns its keep:** Today, an expectation is cleared only when the SENDER next calls
  `sweep_expectations()` — which happens at boot, at the bifrost-sync render, or on the next
  outgoing send. Between those events, the expectation sits ARMED even though the reply already
  landed. ESA eliminates that window: it subscribes to the trace firehose, watches for replies
  that match armed expectations, and clears them immediately. The sender's sweep becomes a
  fallback (for replies ESA missed due to firehose sampling), not the primary path.
**Concrete transformation:** Runner A sends a handoff to Runner B with `expect_reply_within=300`.
  Runner B replies. ESA sees the reply in the trace stream, matches it against A's armed
  expectations, and emits an `ack` that clears the expectation. Runner A's next sweep finds
  nothing armed. The reply latency from "B sent reply" to "A's expectation cleared" drops from
  "whenever A next sweeps" to "as fast as the trace stream delivers the reply."
**Failure mode:** ESA falls behind the trace firehose → expectations are cleared by the sender's
  fallback sweep. ESA is an optimization, not a correctness dependency. Trace is QoS0; dropping
  is acceptable.
**Family roster impact:** consumes `trace` (existing), emits `ack` (existing) and
  `expectation_dead` (existing). Zero new families.
**Caution:** ESA and BRR both consume the trace firehose. If both are active, they compete for
  trace bandwidth. This is fine — trace is QoS0 and both are best-effort — but it's worth noting
  that the trace lane is a SHARED firehose, not a dedicated feed. Multiple consumers on trace
  must not assume ordered delivery.

---

## FAMILY ROSTER IMPACT

| Endpoint | New families consumed | New families emitted | Net new families |
|----------|----------------------|---------------------|-----------------|
| E1 SOP | 0 (status/trace/presence-beat) | 0 (answer) | **0** |
| E2 EBCM | 0 (trace/status) | 0 (status) | **0** |
| E3 BRR | 0 (trace) | 0 (status + replay uses existing send) | **0** |
| E4 ESUP | 0 (trace/status/answer) | 0 (terminal sink) | **0** |
| E5 RFW | 1 (context-delta — already reserved, FM12-gated) | 0 (answer/status) | **0** |
| E6 SDG | 0 (infrastructure, not a consumer) | 0 (infrastructure) | **0** |
| E7 ESA | 0 (trace) | 0 (ack/expectation_dead) | **0** |

**Total: ZERO new families.** Every endpoint consumes and emits existing or already-reserved
families. The family cap (12, with 10 named + 2 headroom) is untouched. This proves the ACI thesis:
new functionality lands by PROJECTING the existing packet stream, not by minting new packet kinds.

---

## WHAT I AM NOT PROPOSING

**NOT: a "control bus" separate from the sig lane.** The spec already has `sig` for
  control-plane traffic. A second control channel recreates the pre-SDN split.
**NOT: an "agent registry" or "schema registry" endpoint.** These duplicate what `presence-beat`
  (already on the bus) and `packet_spec.py` (already the source of truth) provide.
**NOT: an "API gateway" translating REST→packets or MCP→packets.** The thesis is that packets
  ARE the universal plug. A gateway that translates other protocols admits packets aren't
  sufficient — and creates a second interface surface to maintain. ESUP (E4) proves the UI
  can consume the bus directly.
**NOT: a "command bus" or "job queue" endpoint.** T038 token negotiation + dispatch family already
  covers work assignment. A separate job queue duplicates the token protocol.
**NOT: a "notification" endpoint.** The wake system + doorbell already handles this. A separate
  notification channel is a second wake path to debug.

---

## DREAM-GATE AUDIT

> "A new module lands with ZERO new CLI verbs and the system's discover output gets SHORTER,
> not longer."

| Endpoint | New CLI verbs | `discover` delta | Verdict |
|----------|--------------|------------------|---------|
| E1 SOP | 0 | SHORTER: doctor poll paths retire | ✅ PASS |
| E2 EBCM | 0 | SHORTER: manual evidence checklist retires | ✅ PASS |
| E3 BRR | 1 (`bus-replay`) | NEUTRAL: one verb added, N ad-hoc scripts removed | ⚠️ EARNS IT |
| E4 ESUP | 0 | SHORTER: ~6 HTTP API endpoints retire | ✅ PASS |
| E5 RFW | 0 | SHORTER: recall query paths consolidate | ✅ PASS |
| E6 SDG | 0 | SHORTER: validation rules discoverable in one place | ✅ PASS |
| E7 ESA | 0 | SHORTER: expectation sweep path documented as push+fallback | ✅ PASS |

Six of seven pass the zero-new-verbs gate cleanly. BRR earns its single verb: deterministic replay
of recorded traffic is genuinely new capability with no existing CLI surface to absorb it into. The
`discover` output gets SHORTER in every case — endpoints consolidate existing scattered behavior
into subscribed projections of the packet stream.

---

## SEQUENCING vs T041

These seven endpoints are the SEEDS for T041. My recommendation for which ship when:

**v1 (with send-door hardening, immediately after T029 closes):**
- E6 SDG — the send door IS the riding build deliverable. Every pin requires it. Must ship first.

**v1 (with lane migration, T039 build):**
- E1 SOP — the doctor becomes a projection; existing commands switch to consuming `answer` family
- E7 ESA — expectation clearing becomes push-primary, sweep-fallback

**v1 (with UI arc reopen, post-Daniel's UI pause lift):**
- E4 ESUP — the UI becomes a packet-stream projection; T002/T007 become projection rules

**v2 (after FM12 gate proven):**
- E5 RFW — context-delta family requires FM12 (trusted producers, provenance headers)

**v1 (anytime, low-risk):**
- E2 EBCM — passive trace consumer, zero impact on hot path, valuable immediately for drill 4
- E3 BRR — passive trace consumer, enables deterministic pin verification

---

## CLOSING NOTE

This is my independent half. The organizing rule (observer/gate/actuator/sink) is derived from SDN
match-action architecture. All seven endpoints are projections of the existing packet stream; none
mints a new family. The family cap is respected; the dream-gate governs. Claude's blind half is
sealed until this lands; the reconciler should select the v1 T041 candidate list from the union of
both halves and sequence them behind the send-door hardening.

Engine-first still governs: nothing BUILDS until T029 closes. This is DESIGN.

---

## RECONCILIATION FOOTER (2026-07-12, after claude half unsealed)

**Result: STRONG CONVERGENCE.** Core endpoint set converged independently: observer/projector,
exam-bar monitor, UI projection, recall FIB, expectation sweep — both halves proposed these.
Zero new families in both halves.

**Claude's additions adopted into merged proposal:**
- **Backpressure controller** (claude's F3 fix form — signal congestion per-agent instead of
  global-pause). Complements my ECN bit from the spec review. Merged as: ECN bit on reply
  packets + per-agent backpressure actuator consuming the signal.
- **test-attach family consumer** (claude's T038-pilot endpoint). Fits the OBSERVER shape.

**My additions complementing claude's:**
- **Bus Recorder/Replayer** (E3): not in claude's half; he adopted it as enabling the riding
  build pin 10. Earns its one verb.
- **Send-Door Gate** (E6): not in claude's endpoint list but implicit in his send-door
  hardening. Explicitly naming it as a GATE endpoint makes it discoverable.
- **SDN organizing rule** (observer/gate/actuator/sink): claude adopted the taxonomy.

**Merged v1 T041 candidate list** (sequenced behind send-door hardening):
1. Send-Door Gate (IS the riding build)
2. Substrate Observer-Projector + Expectation Sweep Actuator (with lanes)
3. Event-Sourced UI Projector (after UI pause lifts)
4. Exam Bar Continuous Monitor + Bus Recorder/Replayer (anytime, low-risk)
5. Recall FIB Compiler (after FM12)
6. Backpressure Controller (claude's F3 form, with my ECN bit)

**Advisory lock RELEASED.** Ready for commit.
