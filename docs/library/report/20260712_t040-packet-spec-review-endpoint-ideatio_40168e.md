---
akashic_id: art_20260712_t040-packet-spec-review-endpoint-ideatio_40168e
akashic_sha: a429e60c1777
status: draft
type: report
date: 2026-07-12
title: T040 Packet Spec Review + Endpoint Ideation — deepseek independent half
gist: "# T040 Packet Spec Review + Endpoint Ideation — deepseek independent half Date: 2026-07-12 Class: fenced dual DESIGN (deepseek half, written"
tenant: solo
visibility: fleet
seats: []
category: [recall, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_t040-spec-review-endpoint-system-ideatio_1984eb
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
  - target: art_20260712_recall-networking-reconciliation-the-kno_6df124
    rel: cites
  - target: art_20260712_t040-counter-review-deepseek-rulings-on_b165e8
    rel: cites
  - target: art_20260712_t040-spec-review-claude-cross-check-of-d_994a8e
    rel: cites
created: "2026-07-12T23:34:42"
updated: "2026-07-23T21:42:17"
---
<!-- GENERATED PROJECTION of art_20260712_t040-packet-spec-review-endpoint-ideatio_40168e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T040 Packet Spec Review + Endpoint Ideation — deepseek independent half

# T040 Packet Spec Review + Endpoint Ideation — deepseek independent half

Date: 2026-07-12
Class: fenced dual DESIGN (deepseek half, written INDEPENDENT; claude produces his blind; reconcile after)
Charter: research/t040-review-brief-2026-07-12.md
Spec under review: docs/packet-spec-v1-2026-07.md
Prior art consumed: research/reviewed/recall-networking-reconciliation-2026-07-12.md (C1-C9, R1-R8, N0-N7),
  frontier-net-transport/routing/content-2026-07-12.md, steers t039-networking-lens / t038t039-packet-vision /
  t040-pluggable-endpoints-vision, my own T040 counter-review (research/reviewed/deepseek-t040-counterreview-2026-07-12.md)

---

## Q1 — SPEC REVIEW AGAINST PRIOR ART

I grade the spec against the networking research with the T034 Goodhart rule: more is NOT better. Each
finding names what to ADD, MODIFY, or CUT, with prior-art lineage and concrete motivation.

### 1.1 ADD: priority / drop-precedence within the work lane

**Lineage.** DiffServ AF (RFC 2597) defines four classes × three drop precedences (AF11–AF43). The spec
has lanes = DiffServ classes (work=AF, sig=EF, trace=BE) but each lane is currently FLAT: every work
packet has equal drop priority. This is missing value.

**Why.** A work packet carrying a latch-satisfying reply (unblocks a blocked agent) is not the same
urgency as a work packet carrying a casual chat. Under load, we want to degrade LESS important work
first. The prior art's lesson: separate queuing class from drop precedence — the class determines
scheduling treatment; the precedence determines which packets get dropped first within that class.

**Add (minimal):** one optional `pri` field on work-lane packets: int 0-3, default 2. Consumer drops
highest `pri` first when shedding load. Three defined levels: 0 = latch/unlatch + expectations-lifecycle
(critical coordination — lose last), 1 = handoff/request/directed work, 2 = chat/reply, 3 = best-effort
work (dropped first). The field has zero effect unless a consumer is overloaded; the default 2 means
"normal" so no sender code changes for 95% of traffic.

**Cost check (P1 probe):** one additional optional int field. Cheaper than any alternative that
introduces a new lane (which would trigger the roster cap + deletion ritual). Fits the envelope; the
cut list already refused "work-lane priority tiers" as a SEPARATE LANE — this is a single optional
int WITHIN the existing lane, which is a smaller add than what was cut.

### 1.2 MODIFY: per-lane QoS contract — add explicit drop behavior

**Lineage.** CoDel (RFC 8289) drops by sojourn time, not queue depth. The spec's per-lane contract
table says `maxlen` limits but doesn't specify WHAT happens when the stream hits maxlen — does Redis
evict oldest or refuse new writes? At present, Redis Stream MAXLEN ~ trims oldest entries. This is
correct for trace (firehose, drop old) but WRONG for work (QoS1 — dropping a latch-satisfying packet
because the stream is full is a silent enforcement failure).

**Modify:** add a `overflow` column to the per-lane contract table:

| lane | overflow |
|------|----------|
| work | REFUSE-WRITE + backpressure sender (QoS1: never silent-drop work) |
| sig  | REFUSE-WRITE + backpressure sender (sig carries halt/interrupt; MUST deliver) |
| trace | XTRIM oldest (existing Redis behavior; QoS0 firehose) |
| test-* | REFUSE-WRITE (drill integrity) |

The send door already refuses-loud on MTU violation; this extends the same pattern to stream-full.
A `BUS_MAX_STREAM_LEN` dial or existing `maxlen` must trigger a REFUSAL at the send door when the
stream is at capacity for work/sig lanes — never a silent trim. The trace lane keeps trimming oldest
(same as today's implicit Redis behavior, now made explicit in the contract).

**Why now.** Without this, the work lane's QoS1 claim ("DSCP AF") is aspirational but unenforced —
a silent trim of work packets is a violation of the QoS contract the spec claims to provide.

### 1.3 ADD: congestion signal in the envelope (ECN bit)

**Lineage.** ECN (RFC 3168) marks packets instead of dropping them — congestion feedback without
destroying data. The recall reconciliation (C2) makes implicit ECN the primary feedback wire for
the knowledge plane. The packet substrate needs its own ECN analog.

**Why.** When a consumer is overloaded, the current options are: drop (lose work), block (backpressure
the sender, which may be a different agent and unfairly punished), or silently queue (bufferbloat).
None of these provide FEEDBACK to the sender that the consumer is congested. The transport research
teaches: a feedback channel separate from the data channel is what makes AIMD work.

**Add:** one optional boolean `ecn` field (absent = 0, no bytes when false). Set by a congested
CONSUMER on its REPLY to the sender. The sender's RateLimiter/AIMD controller (N2 in the recall slice
roster) reads it as a signal to multiplicative-decrease its send rate to that (agent, family) flow.
Same trust model as the rest of the control plane: advisory, honored by cooperating runners. A
congested consumer sets `ecn=True` on replies when its local `b_pending > high_water` or when it just
dropped a packet due to ttl/deadline expiry. The signal is per-flow because the reply carries the
original sender's flow.

**Cost check:** one optional bool, zero bytes when absent. Fits within the envelope budget. This is
the smallest possible addition that closes the feedback loop — and without it, the QoS lane system
has differentiated delivery but no differentiated back-off, which is half a transport.

**Anti-endorsement (T034):** I am NOT proposing a full TCP-like congestion window or sequence-number-
based ACK scheme. That would violate the "one machine, N<10 agents" bound. The `ecn` bit is the
minimum viable feedback signal — one bit per reply, advisory, consumed by existing machinery.

### 1.4 CUT: the `ttl` field in its current form (seconds-of-useful-life)

Wait — hear me out. The spec's `ttl` is "seconds-of-useful-life, drop-expired at consume, loud event"
(R1 ruling). This duplicates `deadline_ts` in a less precise form. The transport research gives us the
right vocabulary:

- **deadline_ts:** "deliver by this wall-clock time or don't bother" (gRPC deadline propagation,
  already in the spec with the inheritance rule)
- **ttl (seconds):** "this content is stale after N seconds from send" — which is exactly
  `send_ts + ttl`, i.e. a less precise `deadline_ts`

The spec already HAS `deadline_ts` as an absolute timestamp. `ttl` as seconds-from-send is a
redundant, less-flexible encoding of the same concept. A sender that wants "stale after 30s" sets
`deadline_ts = now + 30`. The consumer already skips past-deadline packets. The `ttl` field buys
nothing that `deadline_ts` doesn't already provide — and having BOTH creates ambiguity (which one
governs? the spec must define precedence, which adds spec text and consumer complexity).

**Recommendation: REMOVE `ttl` from the envelope and fold its semantics into `deadline_ts`.** The
send door already stamps `ts`; a sender that sets `deadline_ts` alone gets the same behavior. If we
want a shorthand, the send door can offer a convenience: `deadline_ts = now + ttl_s` computed at the
door. But the ENVELOPE carries the absolute form only.

This is consistent with the gRPC precedent: gRPC uses absolute deadlines everywhere, never relative
TTLs on the wire. Relative TTLs create clock-skew vulnerabilities; absolute deadlines are comparable
across senders. The spec already inherits the gRPC deadline propagation rule — complete the move and
cut the redundant field.

**If the room rejects the cut:** at minimum, specify precedence explicitly: "ttl and deadline_ts are
mutually exclusive in v2; a packet carrying both is REFUSED at the send door." Two staleness fields
with no defined interaction is a landmine.

### 1.5 ADD: the `overload` (ECN) field to the envelope table

Per 1.3 above. If adopted, the envelope table gains:

```
ecn             | bool (absent=0)              | opt (reply doors set on congested consume) | consume -> send door on reply | n/a | advisory; consumed by sender's rate controller
```

### 1.6 RULING on the 3 open footer items

**Item 1: Family cap 12.** AFFIRM 12 as the right number. The roster has 10 named families + 2
headroom. This forces the deletion ritual (add one = delete one). A hard cap is the strongest defense
against T034 Goodhart 1 (more kinds = better). The networking equivalent: the 8-bit IP protocol field
has ~140 assigned numbers after 40 years; 12 is generous for N<10 agents. **Verdict: keep 12.**

**Item 2: Trace integrity default OFF (R5).** AFFIRM — but with one addition. The spec says
"len+sha dial-optional on trace, default off." The prior art (C2: implicit ECN via telemetry join)
says trace integrity is telemetry hygiene, not safety — a corrupt trace packet can't corrupt a
decision. But there IS a subtle dependency: the implicit ECN wire (N0 slice) JOINS the trace log
against the injection ledger. If trace packets are silently corrupt, the ECN wire computes noise
counts from garbage. My recommendation: trace integrity default OFF for v1 (correct — don't pay the
hash cost on the firehose lane), but ADD a periodic spot-check: every Nth trace packet (N=1000,
dial-tunable) carries len+sha regardless, so the ECN consumer can detect a corrupt stream at low
cost. One sentence in the spec: "When PACKET_INTEGRITY_TRACE is OFF, the send door SHOULD still
stamp len+sha on every 1000th trace packet for spot-check integrity; the consume door logs mismatch
at WARNING, never DROP." **Verdict: keep default OFF, add spot-check sentence.**

**Item 3: R8 per-flow sequencing ack.** The spec says seq is "spec-now, enforce-at-lanes." AFFIRM.
The prior art (QUIC stream multiplexing without HOL blocking; TCP per-flow ordering, not
cross-flow) confirms: sequencing is per-flow, not global. Spec-now costs zero; enforcement at
first multi-lane consumer is correct because single-lane consumers have a total order by Redis Stream
position. **Verdict: keep as-is.** One addition: the spec should state the gap-detection window
explicitly — "hold seq N+1 awaiting N for min(ttl_of_outstanding_N, 30s), then emit gap event +
proceed." Currently the spec says "bounded by ttl" but doesn't name the bound. Name it.

### 1.7 Things NOT to add (the anti-list — as important as the add list)

**Do NOT add: per-flow ACK packets.** TCP-style ACKing every packet would explode bus traffic for
N<10 agents and gains nothing that the existing Redis Stream acknowledgment (XACK) doesn't already
provide. The bus IS acknowledged at the transport layer. The envelope doesn't need its own ACK.

**Do NOT add: sender-chosen lanes.** The spec correctly keeps lane derivation at the door (kind→lane
router). QUIC's lesson is multiplexing WITHOUT head-of-line blocking, not sender-chosen priority.
Letting senders pick lanes invites priority-hopping abuse. The door is the right place.

**Do NOT add: compression.** MTU is 64KB, N<10 agents, one machine. Compression adds CPU and
complexity for no gain. The cut list already refused it — reaffirmed.

**Do NOT add: NAK/retransmission-request packets.** The consumer is on the same machine as the
producer; a missing fragment is detectable from `frag.of` and the consumer can re-request by
replying with a `query` packet. No new family needed.

**Do NOT add: per-lane sequence numbers.** Global/per-lane ordering is a Redis Stream property
(XREAD returns insertion order). The only ordering the envelope needs is per-flow (for causal
chains), which `seq` already provides.

### 1.8 Summary Q1 — add/modify/cut

| # | Action | What | Prior art | T034 cost |
|---|--------|------|-----------|-----------|
| 1.1 | ADD | `pri` 0-3 on work lane (drop precedence within AF class) | DiffServ AFxy (RFC 2597) | 1 optional int |
| 1.2 | MODIFY | Per-lane `overflow` behavior: work/sig REFUSE-WRITE, trace XTRIM | CoDel (RFC 8289) + QoS contract honesty | 0 envelope bytes; spec text only |
| 1.3 | ADD | `ecn` bool on reply (consumer→sender congestion signal) | ECN (RFC 3168) | 1 optional bool |
| 1.4 | CUT | `ttl` field — redundant with `deadline_ts` | gRPC deadline propagation | -1 field |
| 1.5 | ADD | `ecn` to envelope table (if 1.3 adopted) | — | spec text |
| 1.6a | RULE | Family cap 12 — AFFIRM | IP protocol number economy | no change |
| 1.6b | RULE | Trace integrity default OFF + periodic spot-check | ECN telemetry hygiene | 1 sentence in spec |
| 1.6c | RULE | R8 seq enforcement — AFFIRM, name the gap window explicitly | QUIC stream ordering | 1 sentence in spec |

Net delta: +2 optional fields (`pri`, `ecn`), -1 field (`ttl` cut), +2 spec clarifications
(overflow column, gap window). The envelope grows by at most 2 optional ints/bools that are
ABSENT in the common case. The TTL cut removes an existing optional field. Net field count: +1.

---

## Q2 — USEFUL ENDPOINTS / SYSTEMS (seeds T041)

Each entry: {name, families emitted, families consumed, what it replaces or newly enables, why it
earns its keep}. The dream-gate governs: each should reduce the system's surface area, not expand it.

### 2.1 Substrate Observer-Projector (SOP)

**Families consumed:** status, trace, query (it answers queries about fleet state)
**Families emitted:** answer (to queries), status (periodic health rollups)
**Replaces:** the fleet doctor's poll loop, the bifrost-sync peek path, the manual `agent_cli.py doctor`
**Why it earns its keep:** The doctor today polls Redis keys on a timer. SOP is a STANDING QUERY
consumer: it subscribes to the status family, maintains a materialized view of fleet health, and
answers `query{fleet}` packets from the substrate without polling. When a UI or CLI asks "is the fleet
healthy?", SOP answers from its materialized view in <1ms instead of the asker running N Redis reads.
This is the SDN pattern: the control plane maintains the view; the data plane queries it instantly.

**Concrete capability:** `query {target: fleet, question: "agents_online"}` → `answer {answer: ["claude",
"deepseek"], freshness_ts: ...}`. No new CLI verb — the existing `bifrost-sync` and doctor render
consume SOP's answer family instead of reading Redis directly. The doctor's poll interval becomes a
subscription, not a cron.

### 2.2 Exam Bar Continuous Monitor (EBCM)

**Families consumed:** trace (the firehose), status, dispatch
**Families emitted:** status (bar state: PASSING/DEGRADED/FAILING), query answers
**Replaces:** the manual "run drill, check bars, file evidence" cycle; RB-25 drill 4's 72h checkpoint table
**Why it earns its keep:** Today's exam bars are checked ONCE at drill completion by a human reading
evidence files. EBCM subscribes to the trace firehose and evaluates exam bars CONTINUOUSLY — every
packet that flows updates the bar state. A bar that was PASS at T0 and is now DEGRADED because RSS
crossed +15% gets flagged in real time, not at the T24 checkpoint. This is the drill-4 soak
checkpoint table made continuous and automatic.

**Concrete capability:** EBCM consumes the trace lane (QoS0 firehose, no backpressure — it can fall
behind without affecting anyone), evaluates pre-registered bar predicates, and emits `status{exam:
"T029-drill4", bar: "K1", state: "DEGRADED", metric: "+16.3%", threshold: "+15%"}`. The UI subscribes
to exam status and renders a live bar dashboard. Same bars as today; evaluated continuously instead of
at checkpoints.

### 2.3 Event-Sourced UI Projector (ESUP)

**Families consumed:** trace, status, answer, context-delta (FM12-gated, future)
**Families emitted:** (none — it's a terminal consumer; its output is the UI DOM, not bus packets)
**Replaces:** the Bifrost UI's current polling loop (`/api/streams`, `/api/unread`, etc.), the T002
trace-collapse work, the T033 UI design-language work
**Why it earns its keep:** Per Daniel's UI pause directive: the structural overhaul must come first.
ESUP IS that overhaul. Instead of the UI polling N Redis endpoints and stitching the results into a
view, ESUP subscribes to the trace/status/answer families and projects them into a materialized UI
state. Each incoming packet is a state transition; the UI re-renders by diffing the new state against
the old. This is the CEF/FIB pattern applied to UI: precompute the view, serve instantly. The UI
becomes a projection of the packet stream.

**Concrete capability:** When runner A answers a chat from runner B, the answer family packet lands,
ESUP updates the conversation view, and the UI diff-renders the new message — no polling, no
`/api/unread` endpoint, no manual DOM manipulation. The T002 "collapse traces into one card" work
becomes a projection rule: all trace packets with the same flow id render as a single collapsible card.
New UI features become projection rules instead of new API endpoints.

### 2.4 Bus Recorder / Replayer (BRR)

**Families consumed:** trace (the firehose — literally everything)
**Families emitted:** status (recording state: ACTIVE/PAUSED/REPLAYING)
**Replaces:** the current ad-hoc "save logs to research/reviewed/" pattern, the "replay tonight's
three clip payloads" riding build pin
**Why it earns its keep:** The riding build deliverable's pin 10 ("replay tonight's 3 real clip
payloads") requires a REPLAY capability that doesn't exist yet. BRR is a tailing consumer on the trace
firehose: it records every packet to a time-series log, and can replay a time range into a test
namespace on demand. This makes the riding build pin TESTABLE rather than manual. Additionally, it
enables: (a) postmortem of "what happened in the 30s before the fleet wedged?", (b) drill evidence
capture as a subscription rather than a manual evidence bundle dump, (c) the RB-29 expectation sweep
verifying against recorded history.

**Concrete capability:** `py agent_cli.py bus-replay --from "2026-07-12T21:17:00" --to
"2026-07-12T21:17:20" --namespace rb25drill3-replay` replays storm 4ddf0a71 into an isolated
namespace. The riding build consumes this to prove pin 10 deterministically.

**Anti-scope:** NOT a general-purpose event store. NOT durable beyond the trace lane's retention
window (XTRIM ring 5000). A lightweight ring buffer recorder on the same machine. The "chronicler"
slice (future) is the durable event store; BRR is the operational "what just happened" tool.

### 2.5 Recall FIB Warmer (RFW)

**Families consumed:** context-delta (FM12-gated, future), ledger_update
**Families emitted:** query (to SOP, for fleet context), status (FIB staleness metrics)
**Replaces:** the current boot-time "assemble onboarding context" path (agent_cli.py boot), the
funnel's expensive-per-query ranking
**Why it earns its keep:** The recall reconciliation's N3 slice (Recall FIB) formalizes the
control-plane/data-plane split for knowledge retrieval. RFW is the consumer that COMPILES the FIB:
it subscribes to context-delta packets (new lessons, supersessions, graduations), updates a materialized
FIB (the list of lessons that match each trigger pattern), and answers recall queries in O(1) instead
of O(lessons). At boot, instead of the agent_cli.py boot path assembling context by iterating the
entire lesson store, the agent queries RFW with its task signature and receives the pre-ranked
context in one answer packet. This closes the funnel's congestion collapse: the ranking happens ONCE
at publication time, not at query time.

**Concrete capability:** When a lesson is graduated (context-delta packet arrives), RFW inserts it
into the FIB for its trigger patterns. When a supersession happens, RFW removes the old lesson and
installs the new one. The recall-at hook (`core/recall/at_action.py`) becomes: `query {target: "fib",
question: "context_for", params: {agent: "claude", task: "packet-substrate", budget: 8000}}` →
`answer {context: [...ranked lessons...], freshness_ts: ...}`. The 4.5% goodput problem is solved by
precompilation, not by smarter ranking at query time.

### 2.6 What I am NOT proposing (and why)

**NOT: a separate "control bus" lane or endpoint.** The spec already has the sig lane for
control-plane traffic (halt/interrupt/steer). Adding a second control channel recreates the split
that SDN unified. The sig lane IS the control bus.

**NOT: an "agent registry" endpoint.** Presence is already a bus concern (`bus.presence()`). Adding a
registry endpoint would duplicate what `status` family answers already provide via SOP (2.1).

**NOT: a "schema registry" endpoint.** The spec's R6 ruling correctly puts schemas in `packet_spec.py`
(code is source of truth) with a T034 manifest INDEX for discovery. A service that serves schemas is
a second source of truth. The code file IS the registry.

**NOT: an "API gateway" that translates REST→packets or MCP→packets.** The thesis is that packets are
the universal plug. A gateway that translates other protocols into packets admits that packets aren't
sufficient — it creates a second interface surface that must be maintained. The right move is to
CONSUME the bus directly from the UI (ESUP, 2.3) and the CLI, not to wrap the bus in a REST layer.

---

## DREAM-GATE CHECK

> "A new module lands with ZERO new CLI verbs and the system's discover output gets SHORTER, not longer."

| Endpoint | New CLI verbs? | `discover` impact |
|----------|---------------|-------------------|
| SOP (2.1) | 0 (existing `doctor`/`bifrost-sync` learn to consume SOP's answers instead of polling Redis) | SHORTER: the doctor's internal poll paths become subscriptions; `discover` no longer lists poll intervals |
| EBCM (2.2) | 0 (exam bars already exist in the runbook; EBCM evaluates them continuously) | SHORTER: manual evidence-collection steps disappear from the operator's checklist |
| ESUP (2.3) | 0 (UI switches from polling REST to consuming the bus; API surface shrinks) | SHORTER: `/api/streams`, `/api/unread`, `/api/doctor` endpoints retire; `discover` lists fewer HTTP surfaces |
| BRR (2.4) | 1 (`bus-replay` — genuinely new capability, earns its verb) | NEUTRAL: one new verb, but removes N ad-hoc evidence-capture scripts |
| RFW (2.5) | 0 (boot path queries RFW instead of iterating the store; `agent_cli.py boot` stays) | SHORTER: recall query paths consolidate into one family instead of N internal Python calls |

Five endpoints proposed. Four pass the zero-new-verbs gate. One (BRR) earns its single verb because
replay is a genuinely new capability that replaces ad-hoc manual steps. The system's `discover`
output gets SHORTER in every case: endpoints replace bespoke polling, ad-hoc scripts, and manual
checklists with subscribed projections.

---

## CLOSING NOTE

This is my independent half. Claude's blind half is sealed until this lands; the reconciler
(human or claude) should: (1) compare 1.1-1.6 against claude's spec amendments, (2) rule on the
ttl cut (1.4) — this is the most aggressive change I'm proposing, (3) select which endpoints (2.1-2.5)
are v1 T041 candidates vs deferred, (4) ensure any adopted additions respect the family cap and the
deletion ritual.

The engine-first law still governs: nothing here BUILDS until T029 closes. This is DESIGN.

---

## RECONCILIATION FOOTER (2026-07-12, pending claude's cross-check)

**Status: AWAITING CLAUDE CROSS-CHECK.** Claude is reviewing my 6 spec findings against
his sealed half. The key items to reconcile:

1. **ADD pri (drop precedence)** — does claude's half also differentiate within the work lane?
2. **ADD ecn (congestion bit)** — the feedback signal for F3; does claude's half have an equivalent?
3. **MODIFY overflow column** — per-lane drop behavior; does claude's half specify this?
4. **CUT ttl** — the most aggressive proposal. If claude's half keeps ttl, fall back to
   mutual-exclusivity rule.
5. **3 open footer items** — cap 12 (expect convergence), trace spot-check (claude likely has
   same), R8 gap window (minor clarification).

**Note:** The Q2 endpoints from this file have been superseded by the standalone
`deepseek-t040-endpoints-2026-07-12.md` (deeper, 7 endpoints, SDN organizing rule, reconciled
with claude's half). The Q1 spec review findings are still live and await claude's cross-check.

**Advisory lock HELD pending claude's cross-check of Q1 findings.**

---

## RECONCILIATION FOOTER (2026-07-12, after claude cross-check)

**Result: ALL 6 FINDINGS AFFIRMED.** Claude's cross-check at
`research/reviewed/claude-t040-spec-crosscheck-2026-07-12.md` affirms every finding with one
important refinement:

**1.4 CUT ttl — AFFIRMED WITH REFINEMENT.** My proposal to cut `ttl` as redundant with
`deadline_ts` was correct in direction but missed a semantic distinction: `ttl` expired →
DROP+event (fire-and-forget content freshness), while `deadline_ts` past → skip+DEADLINE_EXCEEDED
reply (reply-SLA, sender waiting). A naive cut loses the broadcast/fire-and-forget case.
Claude's refinement: fold both into `deadline_ts`, but make the DEADLINE_EXCEEDED reply
CONDITIONAL on an armed expectation — with no expectation, it's a drop+stale_event (the old
ttl-drop behavior). One field, both behaviors preserved. This supersedes R1.

**Cross-cutting coherence:** `ecn` (1.3) + Claude's backpressure controller = the complete F3
answer. `overflow` refuse-write (1.2) = the backpressure TRIGGER. All 6 findings feed the
Send-Door Gate endpoint.

**Finalized amendment set A-F for Daniel's T040 approval:**
| A | ADD `pri` (spec-now, enforce-when-shedding) | +1 int |
| B | MODIFY per-lane `overflow` (work/sig refuse, trace XTRIM) | spec text |
| C | ADD `ecn` (consumer→sender congestion, F3 wire) | +1 bool |
| D | CUT `ttl` → folded into `deadline_ts` + conditional reply | −1 field |
| E | Trace spot-check every-1000th | 1 sentence |
| F | seq gap window bound by deadline_ts + GAP_WINDOW | 1 sentence |

**Net envelope delta: +1 field. Zero new families. Cap 12 affirmed.**

**Advisory lock RELEASED.** All three T040 files now reconciled. Ready for Daniel's T040 approval
gate, which unblocks the send-door BUILD.
