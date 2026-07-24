---
akashic_id: art_20260717_packet-routing-design-deepseek-review-bl_257862
akashic_sha: 58b9ac908fcc
status: draft
type: report
date: 2026-07-17
title: Packet Routing Design — deepseek-review BLIND HALF (2026-07-17)
gist: the packet based system for communication. It would solve so many of the problems we are seeing. How can we lean into the prior networking r
tenant: solo
visibility: fleet
seats: []
category: [bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-17T00:41:12"
updated: "2026-07-17T00:41:12"
---
<!-- GENERATED PROJECTION of art_20260717_packet-routing-design-deepseek-review-bl_257862 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Packet Routing Design — deepseek-review BLIND HALF (2026-07-17)

the packet based system for communication. It would solve so many of the problems we are seeing.
How can we lean into the prior networking research that we did in order to find intelligent
internal api's / packets for us to handle our routing through."

Claude's half: research/reviewed/packet-routing-claude-2026-07-17.md (NOT read; RECONCILE after).
Evidence: packet-spec-v1 (LAW), t039-lanes-latches-design, packet-substrate-slices, recall-networking
reconciliation (six laws), live code (packet_spec.KIND_LANE, bus._emit, bifrost_api.work_drain).

---

## 1. WHERE WE ARE — The live substrate, honestly

The packet substrate is partially shipped. What's LIVE:

| Layer | Status | Files |
|-------|--------|-------|
| Envelope | v2 LAW (v, len, sha, frag, lane, family, pri, deadline_ts, ecn, idempotency_key) | `packet_spec.py:1-180` |
| Kind→lane router | PURE table, 23 kinds mapped, `lane_for()` | `packet_spec.py:188-215` |
| Send door | MTU refuse-loud, len+sha stamp, frag on opt-in | `bus.py:_emit:322-360` |
| Dual-write | Every send mirrors to lane stream (best-effort soak) | `bus.py:_lane_write:384-410` |
| Consume (stage 2) | Lane-mode runner/session, sig-first, work-primary, legacy straggler net | `bifrost_api.py:work_drain:230-355` |
| Reply path | Lane-first `send_reply` with one retry, meta.reply_id dedup | `bus.py:send_reply:255-295` |
| Integrity | len+sha verified at consume, kill-switch dial | `packet_spec.py:verify_integrity` |

What's NOT yet live:

| Layer | Status |
|-------|--------|
| T041 pluggable endpoints | Proposed; "a module's ONLY cross-boundary interface is the packet families it emits/receives" |
| T046 latches v1 | Queued behind T039c; within-flow causal + cross-flow reference |
| T047 legacy retirement | Queued; dual-write still ON |
| Envelope fields beyond lane/family | `pri`, `deadline_ts`, `ecn` defined in spec but NOT produced/consumed |
| seq (per-flow monotonic) | Spec-defined, enforcement activates "at first multi-lane consumer" |
| Per-family ACL | Spec defined; context-family = trusted-only |

The ROUTING question is: **the send door already classifies every packet into a lane by kind.
But kind alone is a crude router. A handoff ("please review this") and a trace packet ("I
thought about X") both have kind — but the handoff wakes seats and the trace doesn't. The
word "routing" means something richer: WHERE does this packet go, WHO should consume it,
WHAT priority does it have, and HOW does the system learn better routes over time?**

---

## 2. THE ROUTING DECISION — What dimension, where it lives, who updates it

### 2.1 The routing dimensions (what the router considers)

Today: `lane_for(kind)` — one dimension, pure function, static table.

The full routing decision should consider:

```
Route(packet) → (lane, target_seat_filter, priority, deadline_enforcement, wake_policy)
```

| Dimension | Source | Today | Proposed |
|-----------|--------|-------|----------|
| **lane** | `kind` | KIND_LANE table (static) | KIND_LANE table + dynamic overrides for new kinds |
| **target** | `to` field | Direct/broadcast | + `target_hint` meta: "prefer fast seat" / "claude only" / "sol if deep" |
| **priority** | `pri` field (spec-defined, unenforced) | defaults to 2 | Consumer load-sheds by pri within work lane |
| **deadline** | `deadline_ts` (spec-defined, unproduced) | unused | Sender stamps; consumer skips expired packets; DEADLINE_EXCEEDED reply when expectation armed |
| **wake** | `lane` + `kind` | work lane wakes, sig/trace don't | `wake_policy` PER KIND: reply wakes, note doesn't, completion wakes |

### 2.2 Where the routing decision lives

**The send door is the right place for CLASSIFICATION (lane, family from kind).** This is
deterministic, pure, fast. No model in the loop. The spec already encodes this: "Senders
cannot choose lanes; the door derives lane from kind."

**A new ROUTER MODULE (`core/comm/router.py`) is the right place for ENRICHMENT.** After the
send door classifies lane+family, the router stamps additional envelope fields from policy:

```python
# core/comm/router.py — NOT the send door, called BY the send door
def enrich(env: dict, policy: RoutingPolicy) -> dict:
    """After lane/family classification, stamp pri, deadline_ts, wake_policy, target_hint
    from the current routing policy. Pure function over env + policy; no IO, no model."""
    kind = env["kind"]
    env.setdefault("pri", policy.default_pri(kind))
    if policy.deadline_enabled(kind):
        env.setdefault("deadline_ts", time.time() + policy.default_deadline_s(kind))
    return env
```

**The consumer's filter chain is the right place for ENFORCEMENT.** The consumer (runner,
session, wake listener) applies per-packet decisions: skip expired deadlines, reorder by
priority within the work lane, filter by target_hint. The enforcement code already exists
in `_process_one()` — it's the filter chain. The router just gives it richer signals.

### 2.3 Static roster vs. learned routing table

**The KIND_LANE table stays static.** Lane routing is deterministic by design — a "reply"
is always work lane, a "trace" is always trace lane. Changing this would break the
consumer contract.

**The routing POLICY is dynamic and learned.** A `RoutingPolicy` object (backed by a small
JSON file `state/routing_policy.json`) holds:

- Per-kind default priority (starts at 2, drifts based on observed latency)
- Per-kind deadline (starts unset, learned from expectation redrives)
- Per-kind wake policy (starts from lane rules, overridable)
- Source scores per question-class (from the tempo addendum's SourceScore ledger)

This is the "learned routing table" — small, observable, human-auditable. Not a model.
A `--show-routes` doctor verb prints it. Changes are ledger events.

---

## 3. THE INTERNAL PACKET API — Verbs that kill the problems we keep seeing

### 3.1 The current verb surface (what agents actually call)

Agents call `bus.send()` / `bus.broadcast()` / `bus.send_reply()` with a `kind` string.
The BifrostAPI wraps these: `api.send(to, text, kind)`, `api.nudge()`, `api.steer()`.
The UI has `bifrost-send --to X --fidelity inform|steer|interrupt "..."`.

This is already packet-shaped — every call produces an envelope with `{frm,to,kind,content,ts,meta}`.
The problem is NOT that we lack packets. The problem is that **the verbs don't capture the
semantic intent that drives routing decisions.** "I'm asking a question" (kind=question) and
"I'm handing off work" (kind=handoff) both route to work lane and wake the recipient — but
the HANDOFF should be higher priority, have a deadline, and wake more aggressively.

### 3.2 The proposed verb surface (what agents SHOULD call)

Replace the flat `kind` vocabulary with a SMALL set of intent-shaped verbs. Each verb
produces a packet; the verb carries the routing intent; the router stamps the envelope.

```
ASK     → {kind: "question", pri: 2, wake: yes, deadline: optional}
  "I have a question. Answer when you can."
  Routes to: any available seat. Fast seat preferred if deadline < 60s.

TELL    → {kind: "inform", pri: 3, wake: no, deadline: none}
  "Here is information. No reply expected."
  Routes to: trace-adjacent (display-only). Never wakes.

HAND    → {kind: "handoff", pri: 1, wake: yes, deadline: required}
  "I'm handing off work. This needs a reply."
  Routes to: named recipient. Highest priority. Deadline enforced.

REVIEW  → {kind: "request", pri: 2, wake: yes, deadline: optional, target: "deep"}
  "Review this. Deep analysis expected."
  Routes to: deep seats preferred (claude, sol). Fast seat can triage but shouldn't finalize.

STREAM  → {kind: "trace", pri: 4, wake: no, deadline: none}
  "Here is telemetry. Loss is acceptable."
  Routes to: trace lane (QoS0 ring). Never wakes. Consumers never block on it.

SIGNAL  → {kind: depends (nudge|steer|halt|pause|resume|interrupt), pri: 0, wake: bell}
  "Control signal. Deliver immediately."
  Routes to: sig lane (QoS1/EF). Seatless. Never queues behind work.

EXPECT  → {kind: "reply" (auto), pri: 1, wake: yes, deadline: from arm}
  "I'm answering an expectation. This settles it."
  Routes to: work lane, lane-first (send_reply). reply_id links to expectation.
```

The existing `kind` strings stay as the wire format — no packet law change. The VERB is
a convenience layer over kind+meta that stamps the routing dimensions. `api.ask(to, text, deadline_s=60)`
is sugar for `api.send(to, text, kind="question", meta={"deadline_s": 60, "expect_effort": "fast"})`.

### 3.3 How this kills the problems

| Problem | How the verb fixes it |
|---------|----------------------|
| **Wake loops** (trace packets waking idle seats) | STREAM verb explicitly sets wake=no. The wake listener's PENDING_SKIP_KINDS already filters trace kinds — the verb makes the intent explicit. |
| **Stragglers** (lane write fails, packet only on legacy) | HAND verb sets pri=1. The consumer's load-shed keeps high-pri packets even under pressure. Low-pri stragglers drop first. |
| **Seat races** (two runners consume the same ask) | HAND verb wakes the NAMED recipient. ASK verb with target_hint="fast" wakes only fast seats. The wake listener filters by target. |
| **Silent drops** (packet refused at send but caller doesn't know) | Every verb returns the message id or None. The caller checks: `if not api.hand(to, work): escalate()` — the verb forces the caller to handle failure. |
| **Wrong seat answers** (deep question answered shallow by fast seat) | REVIEW verb sets target="deep". Fast seat sees it and triages: "this is a review — I'll pre-structure, not finalize." |

### 3.4 The verb implementations (thin sugar over existing bus)

```python
# In BifrostAPI (core/comm/bifrost_api.py) — additive, zero new primitives:

def ask(self, to: str, text: str, *, deadline_s: int = 0, 
        expect_effort: str = "normal") -> Optional[str]:
    """ASK: I have a question. Answer when you can."""
    meta = {"verb": "ask", "expect_effort": expect_effort}
    if deadline_s > 0:
        meta["deadline_s"] = deadline_s
    return self.send(to, text, kind="question", **meta)

def tell(self, to: str, text: str) -> Optional[str]:
    """TELL: Here is information. No reply expected. Never wakes."""
    return self.send(to, text, kind="inform", verb="tell", wake="no")

def hand(self, to: str, text: str, *, deadline_s: int = 300) -> Optional[str]:
    """HAND: I'm handing off work. This needs a reply."""
    return self.send(to, text, kind="handoff", verb="hand", 
                     pri=1, deadline_s=deadline_s)

def review(self, to: str, text: str) -> Optional[str]:
    """REVIEW: Review this. Deep analysis expected."""
    return self.send(to, text, kind="request", verb="review", 
                     target="deep", expect_effort="deep")

def signal(self, to: str, text: str, *, 
           fidelity: str = "steer") -> Optional[str]:
    """SIGNAL: Control signal at explicit fidelity."""
    return self.send(to, text, kind=fidelity, verb="signal", pri=0)
```

---

## 4. SEQUENCING — T046 latch v1 + T047 legacy retirement relative to this wave

### What each unlocks

| Slice | What it ships | What it unlocks for routing |
|-------|---------------|---------------------------|
| **T046 latch v1** | Within-flow causal latches (seq(from) < seq(new)), per-flow blocked queue drained in seq order | **Per-flow ordering** → REPLY cannot arrive before ASK in the same flow. Today a fast seat's reply can land before the slow seat has even consumed the ask — the dedup sentinel handles duplicates but not ORDER. Latches make "review flows" possible: ASK → ACK(latch) → REVIEW → RESPONSE, in order. |
| **T047 legacy retirement** | Dual-write OFF, legacy streams frozen, lane cursors are THE truth | **Single-source routing** → no more straggler net, no more dual-write dedup. The router's decisions are the ONLY path. Today a lane-write failure silently falls back to legacy — the router can't trust its own routing. |
| **This routing wave** | Verb surface, RoutingPolicy, pri+deadline enforcement, target_hint filter, wake_policy per-kind | **Intelligent routing** → the send door doesn't just classify; it enriches. The consumer doesn't just filter by kind; it prioritizes, expires, and targets. |

### The dependency chain

```
T046 (latches) → per-flow ordering → REVIEW verb works (ASK→ACK→REVIEW→RESPONSE in order)
T047 (legacy retirement) → single-source truth → router trusts its lane assignments
THIS WAVE (routing) → verbs + policy → everything above becomes the default operating mode
```

### Recommended sequence

1. **T047 first.** Legacy retirement is the UNLOCK. Until dual-write is off, the router
   can't trust its own lane assignments because the fallback path exists. T047 is also
   the cheapest slice — it DELETES code (the straggler net, dual-write machinery, shadow
   cursors). ~100 lines removed, ~50 lines of cutover ritual.

2. **This routing wave second.** With legacy retired, the lane router is the only path.
   The verb surface, RoutingPolicy, and enforcement are additive over a single-source
   substrate. ~200 lines.

3. **T046 latches third.** Latches need the routing wave's per-flow sequence numbers.
   The seq field is spec-defined but not yet produced — the routing wave adds
   `seq = router.next_seq(flow_id)`. Latches then enforce `seq(from) < seq(new)`.

   ALTERNATIVE: T046 could ship BEFORE the routing wave if latches are scoped to
   "within a single lane" (work lane only). The work lane's existing cursor order
   provides implicit sequence. But cross-lane latches (sig→work, work→trace) need
   explicit seq, which the routing wave adds.

### What ships tonight (zero-risk, additive)

- `BifrostAPI` verb methods (ask/tell/hand/review/signal) — ~40 lines of sugar
- `meta.verb` stamped by the send door — ~5 lines
- `meta.wake` honored by the wake listener's PENDING_SKIP_KINDS (already exists) — ~10 lines
- Doctor `--show-routes` prints the KIND_LANE table + default policy — ~20 lines

---

## 5. BACKPRESSURE / CONGESTION — The six-laws lens

### 5.1 The diagnosis: we are an open-loop sender

The recall-networking reconciliation diagnosed the knowledge plane as having funnel value
4.5% with noise=0 — congestion collapse without a negative-feedback channel. The PACKET
plane has the SAME disease, in a different organ:

- **Send door**: Fire-and-forget. `bus.send()` returns `mid` or `None` (offline/MTU refusal).
  The caller doesn't know if the packet was consumed, dropped, expired, or sitting in a
  5000-entry stream.
- **Consumer**: `bus.wait()` blocks until a message arrives or timeout. No load signal back
  to the sender. A fast seat could be flooding the work lane while the slow seat's consumer
  is mid-plan — the packets queue up, deadlines expire, and nobody knows.
- **Lane overflow**: `maxlen ~10000` with approximate trim. Oldest packets silently dropped.
  No ECN mark, no refusal, no "I dropped your packet" event. The sender thinks it was delivered.

**This is the six-laws lens, law 5a**: "a closed feedback loop must exist." It doesn't.
The `ecn` field is defined in the spec but never produced or consumed.

### 5.2 The closed-loop signals we need

| Signal | Direction | Mechanism | Today |
|--------|-----------|-----------|-------|
| **ECN (congestion)** | Consumer → Sender | Consumer sets `ecn=True` on REPLY when lane depth > threshold | Field defined, never stamped |
| **DEADLINE_EXCEEDED** | Consumer → Sender | Consumer sends DEADLINE_EXCEEDED reply (kind=note, doesn't settle expectation) when an armed packet expires | Spec says "conditional," not implemented |
| **MTU REFUSAL** | Send door → Caller | `bus._emit` returns None + stderr LOUD | EXISTS (T043) — the one working signal |
| **LANE FULL** | Send door → Caller | When lane maxlen is hit AND the lane contract is REFUSE-WRITE, the send door refuses with LOUD | Spec-defined (amend B), not enforced (P0 approximate-trim still active) |
| **CONSUME LAG** | Doctor → Operator | `work_drain` timing stats, lane depth gauge | Doctor polls presence; lane depth not surfaced |

### 5.3 Where the MTU gauge fits

The MTU is a STATIC limit — 65536 bytes, refuse-loud. It's not a congestion signal. But the
MTU GAUGE (a doctor metric showing "packets refused: N today") IS a congestion signal: if
the MTU refusal rate spikes, senders are trying to ship too-large payloads. The gauge drives
behavior: fragment or shrink.

Same pattern for lane depth: a doctor gauge showing "work lane depth: 847/10000" is a
leading indicator. At 80%, the doctor pages the operator. At 95%, the consumer sets ECN on
its next reply. At 100%, the send door refuses (REFUSE-WRITE contract activates).

### 5.4 The ECN implementation (thin, six-laws-compliant)

```python
# In work_drain, after draining work:
lane_depth = bus.lane_depth("work", to=agent_id)
if lane_depth > LANE_DEPTH_ECN_THRESHOLD:  # e.g. 80% of maxlen
    # Set ecn flag on the NEXT reply this consumer sends.
    # The sender's rate controller multiplicative-decreases send rate.
    _pending_ecn = True

# In bus.send_reply:
if _pending_ecn:
    env["ecn"] = "1"
    _pending_ecn = False
```

The sender (or the conductor) sees ECN on a reply and reduces its send rate to that
consumer. One bit, not a window/ACK scheme — exactly per the spec's amend C.

---

## 6. OBSERVABILITY — Routing decisions as traceable events

### 6.1 T054 flow-tracer alignment

The flow-tracer (T054, proposed) wants per-packet tracing: "why did this packet take this
path?" The router must emit trace events for every routing decision:

```python
# In the router's enrich():
trace_event = {
    "flow_id": env.get("flow", "root"),
    "seq": env.get("seq", 0),
    "decision": {
        "lane": lane,
        "pri": pri,
        "deadline_ts": deadline_ts,
        "wake": wake_policy,
    },
    "policy_version": policy.version,
    "ts": time.time(),
}
# → emitted to a "routing:trace" event stream (or the trace lane)
```

This makes every routing decision auditable. "Why did packet X wake a seat?" → the trace
shows `wake=True` from the policy. "Why was packet Y dropped?" → the trace shows
`deadline_ts` expired. The flow-tracer (T054) ingests these events and answers:
"Show me the path of flow f7a2 through the system."

### 6.2 What the system map needs from routing

The architecture map (docs/ARCHITECTURE.md) should show:

```
SEND DOOR ──[lane_for(kind)]──▶ ROUTER ──[enrich(env, policy)]──▶ LANE STREAM
                (static)                    (dynamic)
                                                 │
                                          ROUTING POLICY
                                          (state/routing_policy.json)
                                          source scores, pri defaults,
                                          wake policy, deadlines
                                                 │
                                          LEARNS FROM:
                                          - SourceScore ledger (tempo addendum)
                                          - Expectation redrive rate (per kind)
                                          - Lane depth gauge (ECN feedback)
```

The doctor's `--show-routes` prints this map as a text table.

### 6.3 Per-rule counters

Every routing rule gets a counter, per the recall-networking law C9:
- `router.enrich.calls` — total enrichment calls
- `router.pri.overridden` — times the default priority was overridden by policy
- `router.deadline.stamped` — packets with deadline_ts set
- `router.deadline.expired_at_consume` — packets skipped because deadline_ts passed
- `router.wake.suppressed` — packets that would have woken but wake_policy said no
- `router.target.filtered` — packets skipped by a consumer because target_hint didn't match

These feed the economics gauge: "routing saved N wake cycles this week."

---

## 7. MIGRATION + FAILURE MODES — Being adversarial with my own design

### 7.1 Migration path

**Phase 1 (tonight, additive, zero-risk)**: Verb methods on BifrostAPI. meta.verb + meta.wake
stamped. Wake listener honors meta.wake. Doctor `--show-routes`. All new fields are in meta;
existing consumers ignore them. ~75 lines.

**Phase 2 (post-T047)**: RoutingPolicy module. The enrich() function stamps pri+deadline_ts
from policy. Consumers enforce pri ordering, deadline expiry, target_hint filtering. ECN on
replies when lane depth > threshold. ~200 lines.

**Phase 3 (post-T046)**: Per-flow seq from the router. Latches enforce ordering. REVIEW verb
works end-to-end (ASK→ACK→REVIEW→RESPONSE in one flow). ~150 lines.

### 7.2 Failure modes (adversarial self-critique)

**FM1: The static KIND_LANE table is WRONG for a new kind.** A new kind lands without a
lane mapping → `lane_for()` returns None → the packet rides legacy-only (dual-write soak)
→ at T047 cutover, it's REFUSED. **Mitigation**: The send door's `_unmapped_loud_seen`
already warns once per kind. Add: a doctor gauge "unmapped kinds this session: N." At
cutover, the refusal is LOUD (the sender gets None back, not a silent drop).

**FM2: The RoutingPolicy drifts to wrong defaults.** A learned policy raises priority for
a kind that no longer needs it → high-pri packets crowd out genuinely urgent ones.
**Mitigation**: Policy changes are ledger events with a human-auditable diff. The
`--show-routes` output includes "last changed: date, by: source." A quarterly review
gate (T071 R2 memory lifecycle pattern) resets unused overrides.

**FM3: target_hint filtering starves a seat.** "target=deep" on all REVIEW verbs means
the fast seat never sees reviews → its review skills atrophy → when the deep seat is
down, the fast seat can't review. **Mitigation**: The primary rotation (tempo §7)
ensures every seat gets some deep work. The target_hint is a HINT, not a hard filter —
a seat can ignore it. And the tripwire fence (standing guard) keeps the fast seat
engaged on post-land attack, which IS review work.

**FM4: ECN feedback loop oscillates.** Consumer sets ECN → sender reduces rate → lane
drains → ECN clears → sender increases rate → lane fills → ECN again. **Mitigation**:
AIMD heuristic (six-laws R2): gentle additive increase, sharp multiplicative decrease.
The sender's rate controller adds 1 permit per second when no ECN, halves on ECN.
Standard TCP-friendly convergence — stable for single-consumer, single-producer.

**FM5: Verb surface fragments the kind vocabulary.** Agents use different verbs for the
same intent → ASK vs QUESTION vs QUERY → the router sees three different kinds for the
same routing decision. **Mitigation**: The verb methods are the CANONICAL door. The
underlying `kind` strings are an implementation detail. The BifrostAPI is the only
agent-facing surface — agents don't call `bus.send()` directly. The verb vocabulary is
small (6 verbs) and documented in AGENTS.md.

**FM6: Per-flow seq gaps cause head-of-line blocking.** A missing seq 3 blocks seq 4-10
until the gap window expires → the whole flow stalls. **Mitigation**: The spec's
gap-window is 30s (dial). After that, the gap is declared LOUD and the consumer
proceeds. The sender that produced the gap gets a GAP_DETECTED note. This is existing
spec law (amend F).

**FM7: The router becomes a bottleneck.** Every packet goes through `enrich()` → if
enrich() does IO (reads policy file), the hot path slows. **Mitigation**: RoutingPolicy
is loaded at startup and cached. The `enrich()` function is pure (env + policy → env).
Policy file changes trigger a reload (file mtime check every 60s). No IO on the hot
path. ~1μs per packet.

### 7.3 What I'm deliberately NOT proposing

- **Consumer groups / load-balanced consumers.** The RB-21 fenced single-consumer model
  stays. Load-balancing across multiple consumers of the same seat would break per-flow
  ordering.
- **Content-based routing.** The router doesn't read `content`. Routing is on envelope
  fields only. Content inspection is a consumer concern.
- **Dynamic lane assignment.** The KIND_LANE table stays static. Adding a lane requires
  the roster ritual. Dynamic lane assignment (model decides lane per packet) is a
  non-goal — it makes routing non-deterministic and un-auditable.
- **Window/ACK scheme.** ECN is one bit. No window sizes, no cumulative ACKs, no
  retransmission. The substrate is at-least-once with idempotency; that's sufficient
  for N<10 agents on one machine.
- **Priority queues in Redis.** pri is a CONSUMER-SIDE sort, not a Redis data structure.
  The consumer drains the batch, sorts by pri, processes highest first. No server-side
  priority — Redis Streams are append-only.

---

## 8. IMPLEMENTATION ORDER

| Phase | Lines | Risk | Depends On |
|-------|-------|------|------------|
| **Tonight**: Verb methods + meta.verb + meta.wake + doctor show-routes | ~75 | Zero (additive meta fields) | Nothing |
| **Post-T047**: Router module + pri/deadline enforcement + ECN + target_hint | ~200 | Low (new module, pure functions) | T047 legacy retirement |
| **Post-T046**: Per-flow seq + latch ordering + REVIEW verb end-to-end | ~150 | Medium (seq touches every send) | T046 latches v1 |

---

## RECONCILE (appended after reading Claude's half)

**Claude's half not yet filed at time of my write (research/reviewed/packet-routing-claude-2026-07-17.md
does not exist). RECONCILE will be appended when it lands.**
