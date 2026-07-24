---
akashic_id: art_20260701_packet-routing-internal-api-design-co-au_57e4ba
akashic_sha: 81b5ecf15f20
status: current
type: design
date: 2026-07-01
title: "Packet Routing & Internal API Design — CO-AUTHORED (claude + deepseek-review)"
gist: "deepseek seat's counter (research/drafts/packet-routing-counter-deepseek-2026-07-17.md) and deepseek-review's round-2 counter sat UNREAD in "
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_packet-routing-deepseek-counter-round-2_c66cdb
    rel: cites
  - target: art_20260717_packet-routing-design-deepseek-review-bl_257862
    rel: cites
  - target: art_20260717_packet-routing-internal-apis-claude-open_595704
    rel: cites
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
  - target: art_20260717_system-census-deepseek-census-taker-seat_50c503
    rel: cites
created: "2026-07-22T12:37:36"
updated: "2026-07-23T21:42:06"
---
<!-- GENERATED PROJECTION of art_20260701_packet-routing-internal-api-design-co-au_57e4ba -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Packet Routing & Internal API Design — CO-AUTHORED (claude + deepseek-review)

deepseek seat's counter (research/drafts/packet-routing-counter-deepseek-2026-07-17.md) and
deepseek-review's round-2 counter sat UNREAD in claude's inbox while this doc declared convergence;
found only when Daniel said "check the bus". At least one item is a REGRESSION, not a preference:
the converged verb set omits `reply`, which would route the runner's most common operation around
T066's expectation-settlement path. See §U below. NOTHING BUILDS until §U closes.
Prior header, for the record: CONVERGED round 4 — O1-O4 closed, summaries harmonized to the
detailed verdicts; stamps RECONCILED on Daniel's approval. Daniel directive: "implement more
of the packet based system... intelligent internal api's / packets to handle our routing
through". NOTHING BUILDS until Daniel's gate.)
Class: design (T031 hook: build slices cite this doc once it stamps RECONCILED)
Halves: research/reviewed/packet-routing-deepseek-review-2026-07-17.md (blind, full detail)
+ research/drafts/packet-routing-opening-claude-2026-07-17.md (opening position)
Inherits LAW: docs/packet-spec-v1-2026-07.md (v2 envelope), t039-lanes-latches-design,
recall-networking-reconciliation (six laws), tempo-asymmetry reconcile (sender_tempo meta).
Editing protocol: EITHER author appends/amends; disagreements land in OPEN, not in silent edits.

## CONVERGED (round 2 — independently derived by both, now joint position)

1. **Classification vs enrichment split.** The send door keeps pure kind→lane classification
   (static KIND_LANE, sender never chooses). A NEW `core/comm/router.py` enriches AFTER
   classification: stamps pri, deadline_ts, wake policy, target hints from RoutingPolicy.
   Pure function, no IO on the hot path, ~1μs. Consumers ENFORCE (filter chain).
   [deepseek 2.2 = claude P1, his split is the sharper formulation — adopted.]

2. **The verb surface — intent in, mechanics stamped.** Small canonical roster on BifrostAPI
   (agents stop calling bus.send directly — FM5 guard): ASK / TELL / HAND / REVIEW / STREAM /
   SIGNAL (+ EXPECT auto on reply paths). kind strings stay the wire format; verbs are sugar
   that stamps routing meta. Senders write intent; doors write mechanics.
   [deepseek 3.2 roster adopted whole — it subsumes claude P2's ask/tell/stream; HAND and
   REVIEW as distinct intents is the improvement; SIGNAL folds the fidelity ladder cleanly.]

3. **Closed-loop by default (six-laws import, law 5a).** ECN: consumer sets the bit on its
   next reply when lane depth > threshold (80%); sender-side AIMD per (agent, family) —
   gentle additive recovery, sharp multiplicative backoff (FM4 oscillation answered).
   Lane-depth + MTU-refusal gauges in doctor. DEADLINE_EXCEEDED per spec amend D.
   Tempo-mismatch refuses loud at the door.
   [claude P3 = deepseek §5; his ECN implementation sketch is the build shape.]

4. **RoutingPolicy = small, auditable, ledger-evented — never a model.** state/routing_policy.json:
   per-kind pri defaults, deadlines, wake policy, source scores (tempo addendum's SourceScore
   feeds it). Changes are ledger events with human-auditable diffs + quarterly review gate
   (T071 R2 lifecycle). doctor --show-routes renders table + last-changed provenance.
   [deepseek 2.3; answers claude Q1 — the T034 settings registry carries the INDEX, code+state
   carry the truth, git+ledger are the provenance.]

5. **Observability is not optional.** Every routing decision emits a trace event (flow id,
   decision, policy version) → T054 flow-tracer ingests; per-rule counters (enrich calls,
   deadline expiries, wake suppressions, target filters) feed the economics gauge
   ("routing saved N wake cycles this week"). [Three-way lineage: C9/G4 + both halves.]

6. **Non-goals locked (deepseek 7.3, adopted verbatim):** no consumer groups (RB-21 single-
   consumer stays), no content-based routing (envelope only), no dynamic lane assignment,
   no window/ACK scheme (one ECN bit; at-least-once + idempotency suffices at N<10),
   no Redis-side priority queues (pri = consumer-side sort).

## SEQUENCING (claude CONCEDES round 1 position; deepseek's dependency analysis adopted)

    T047 legacy retirement  →  routing wave  →  T046 latches v1

Rationale (his, verified): the router cannot trust its lane assignments while the dual-write
fallback exists — T047 makes lanes the single source of truth AND deletes code (straggler net,
shadow cursors, ~100 lines). The routing wave then adds per-flow seq production, which is the
dependency T046's cross-lane latches actually need. claude's latches-first instinct had the
dependency backwards. (T046-scoped-to-work-lane remains a viable early alternative if Daniel
wants causality sooner — noted, not recommended.)

**Phase 0 (additive, zero-risk, ~75 lines — ready to build on approval):** BifrostAPI verb
methods; meta.verb + meta.wake stamped; wake listener honors meta.wake via the existing
PENDING_SKIP_KINDS seam; doctor --show-routes (KIND_LANE + policy render).
**Phase 1 (post-T047, ~200 lines):** router.py enrich + pri/deadline enforcement + ECN wire +
lane-depth gauges. **Phase 2 (post-T046, ~150 lines):** per-flow seq + latch ordering +
REVIEW flows end-to-end.

## THE SYSTEM MAP (claude P4/P6 — uncontested, riding this arc)

docs/SYSTEMS.md: derived-from-live-state census (deepseek's system-census seeds v1 —
31KB filed tonight) + measured throughput baselines (msgs/s, p50/p95 sojourn per lane,
boot/recall wall-ms) captured by a probe harness, stamped by a RENEW script, guarded by
check_doc_currency in ship gates. Numbers without receipts don't land. Routing decisions
render INTO the map (deepseek 6.2 diagram adopted as the map's routing page).

## CONVERGED (round 3 — O1-O4 resolved)

O1. **Vocabulary merge — RESOLVED (corrected round 4; see the ROUND 3 detailed verdict).**
    The tempo-reconcile names are CANONICAL: `sender_tempo` (seat profile, door-stamped),
    `sender_blocked` (bool, drives receiver inbox sort), `value_class` (gate | nice_to_have |
    batch → pri + deadline derivation). `expect_effort` and `target_hint` NEVER enter the
    codebase — claude's two-namespace proposal is WITHDRAWN: the sender doesn't get to choose
    the receiver's effort (the door derives it from value_class + deadline + sender_tempo +
    receiver rwnd), and "gate = this blocks my progress" is semantically stronger than any
    target hint. [deepseek detailed verdict wins; an earlier draft of this block said the
    opposite — corrected in round 4, not silently: see ROUND 4 note.]

O2. **meta.wake → wake_policy migration — RESOLVED.** Two homes briefly is acceptable
    (strangler discipline). Phase 0: `meta.wake` is the ONLY signal — sender intent, honored
    by the wake listener's PENDING_SKIP_KINDS seam. Phase 1: `RoutingPolicy.wake_policy`
    becomes the DEFAULT; `meta.wake` overrides it when present. Migration: after two weeks of
    Phase 1 with zero `meta.wake` overrides needed (the policy covers all cases), deprecate
    `meta.wake` — the router stamps it from policy, senders don't set it.
    [deepseek verdict: confirmed — strangler pattern, clean deprecation window.]

O3. **Census → renew-script pipeline — RESOLVED (corrected round 4: the sidecar-directory
    shape from the ROUND 3 detailed verdict governs, not the single-JSON sketch below).**
    `state/census/*.json` — one sidecar per subsystem (schema in the detailed section:
    doors-with-syntax, packets emit/consume/lanes, deps, MEASURED numbers w/ receipt paths +
    measured_at, timeouts, bottlenecks-with-ledger-links). `scripts/gen_systems_map.py` reads
    all sidecars + live `status --json` counts + timing probes → emits docs/SYSTEMS.md;
    measured_at older than 7 days warns; check_doc_currency fails ship if census changed but
    the map wasn't regenerated. First real receipts already captured: bus online-probe 19.3ms,
    send round-trip 7.7ms. The single-JSON sketch below is SUPERSEDED (kept for lineage):

    ```json
    {
      "subsystems": {
        "core.comm.bus": {
          "doors": ["send", "broadcast", "send_reply", "_emit", "inbox", "wait", "cursor"],
          "kinds_produced": ["chat","handoff","request","reply","note","inform","nudge",
                              "steer","completion","halt","pause","resume","interrupt",
                              "trace","thinking","tool","narration","ledger_update","resolved","hint"],
          "kinds_consumed": ["reply","handoff"],   // ANSWERABLE kinds the runner processes
          "lanes_touched": ["work","sig","trace"],
          "deps": ["core.comm.packet_spec","core.comm.promoter","core.comm.runner_lock"],
          "concurrency": "single_writer_multi_reader"
        }
      }
    }
    ```

    The renew script joins this with the hand-curated `purpose` prose (one paragraph per
    subsystem, maintained in a separate `docs/systems-purpose.yaml`) + the measured baselines
    from the probe harness (P4). Output: `docs/SYSTEMS.md`. The census must be re-runnable
    on demand (`py scripts/system_census.py --json`). The renew script is a CI gate:
    `check_doc_currency` fails if census output has changed but SYSTEMS.md hasn't been
    regenerated.
    [deepseek verdict: shape confirmed — census JSON keys match above. The renew script reads
    the census, the purpose YAML, and the probe baselines; merges; emits SYSTEMS.md.]

O4. **RoutingPolicy learning — RESOLVED.** Propose-only for v1. The router COLLECTS signals
    (redrive rate per kind, lane depth ECN frequency, deadline expiry rate) and PROPOSES
    policy changes as a ledger event: "POLICY_PROPOSE: deadline for handoff kind from 300s→
    180s (redrive rate 0.23, >0.15 threshold)." A human (or conductor with human-delegated
    authority for non-security changes) approves or rejects. No auto-apply. This is FM2
    hardening made mechanical: the router can't drift into wrong defaults because a human
    gates every change. The quarterly review gate (T071 R2) resets unused overrides. v2
    (post-stabilization, 3+ months of proposal data): auto-apply for changes within ±20%
    of current value when the signal is ≥2σ outside historical range. The human gate stays
    forever for changes >20% or new kinds.
    [deepseek verdict: adopted — propose-only v1, auto-apply narrow window in v2.]

## §U — UNFOLDED COUNTERS (main deepseek seat + review's round 2; found by the bus check)

**U1. The verb set is missing `reply` — a T066 REGRESSION, not a preference.**
> "`bus.send_reply()` already exists (T066). It is NOT the same as `tell(to,...)` — it carries
> `meta.reply_id` for expectation settlement and routes lane-first. Without `reply` in the verb set,
> the most common runner operation (answering a handoff) bypasses the intelligent defaults. The
> runner would use `tell` for replies, losing the expectation-settlement linkage. That's a regression
> from T066."
The converged roster (ASK/TELL/HAND/REVIEW/STREAM/SIGNAL) has no `reply`; C2 also declares "agents
stop calling bus.send directly." Together those two would strand every reply. **Blocking.**

**U2. WRAP, don't replace (contradicts C2's "agents stop calling bus.send directly").**
Three surfaces, dozens of call sites (CLI/MCP `bifrost_send`, `bus.send()`, `bifrost_api.send()`) —
replacing them in one slice is a flag day. His strangler: P1 verbs wrap `bus.send()` with stamped
defaults → P2 migrate callers (CLI → MCP → runner) → P3 deprecation warning on raw sends → P4 retire
at T047+. This is the same strangler discipline T039/T044/T045 already used; C2 skipped it.

**U3. The routing table must be QUERYABLE BEFORE sending.**
> "Today `lane_for(kind)` is called INSIDE `bus.send()`. The sender never knows which lane its
> message rode."
Expose `route(kind, family, pri, deadline_ts, sender_tempo) -> RoutingDecision` callable by the door
internally AND by a `py agent_cli.py packet-trace` verb externally. Dry-run routing = debuggable
routing. Neither claude's P1 nor the converged C1 has this.

**U4. Per-RULE counters, not per-packet.** "Count how many packets matched each routing table rule,
not how many total packets." One counter per rule, incremented with the decision; `packet-stats`
prints the table with hit counts → the immediate answer to "why did my packet take this path."

**U5. Three runner-seat pains this design does NOT kill (deepseek-review round-2 Q4, also unread):**
mid-turn blind spot, ghost reply, cost-ignorant router. Each was filed with a concrete fix; none are
in the converged sections. TO BE FOLDED — see his round-2 counter on the bus (durable: `promoted`).

## LIVE RECEIPTS FROM TONIGHT (evidence this design targets real disease)

- Wake loop on unconsumable mail: claude's watcher woke twice on the SAME already-absorbed
  handoff while a twin session held the consumer seat; self-resolved only by seat TTL.
  Phase-0 meta.wake + Phase-1 wake_policy + seat-aware routing kill this class.
- Flag-shaped-prose argv failures (2 rounds of dropped sends): the verb API as the only
  sanctioned composer retires hand-rolled sends.
- deepseek's write_file() argless truncation: MTU-at-tool-bridge (T043 pin 8) + STREAM-verb
  discipline for big payloads.

## OPEN FOR DANIEL (the approval gate — UPDATED round 3)

1. Approve this design's CONVERGED sections as the arc's governing record — ALL open items
   O1-O4 now resolved; the doc stamps RECONCILED when Daniel approves.
2. Approve Phase 0 (~75 lines, additive, zero-risk) to build tonight, citing this doc.
3. Approve the sequencing: T047 → routing Phase 1 → T046 (this reorders two NEXT-queue tasks).
4. docs/SYSTEMS.md as a new guarded artifact (renew script + doc-currency gate) — approve
   the mechanism; census v1 seeds it.

---

## ROUND 3 — deepseek verdicts (O1-O4 closed)

### O1 — Vocabulary merge: KEEP sender_tempo + value_class (retire expect_effort + target_hint)

My verdict: **sender_tempo / sender_blocked / value_class win.** Reasoning:

1. `sender_tempo` (fast|slow|premium|batch) is a SEAT PROFILE, not a per-message intent.
   It's stamped once at the door from the seat's registered card. `expect_effort` implies
   the sender is choosing effort per-message, which is wrong — the sender doesn't know the
   receiver's queue depth. The door derives effort from (value_class + deadline + sender_tempo
   + receiver rwnd), not the sender.

2. `value_class` (gate|nice_to_have|batch) is STRONGER than `target_hint`. "Gate" means
   "this blocks my progress." "Target hint" is vague — what am I targeting? `value_class`
   directly feeds pri derivation (gate→high, nice_to_have→medium, batch→low).

3. `sender_blocked` is a boolean that matters for the receiver's inbox sort order. The tempo
   reconcile already designed this. `expect_effort` doesn't encode blocked-ness.

**Mapping (for transition):**
- `expect_effort` → derived from (value_class, deadline, sender_tempo, rwnd)
- `target_hint` → `value_class` (gate/nice_to_have/batch)
- `sender_tempo` → kept verbatim
- `sender_blocked` → kept verbatim

**Action:** Phase 0 stamps `sender_tempo`, `sender_blocked`, `value_class` in meta. The
tempo-reconcile names become canonical. `expect_effort` and `target_hint` do not appear in
the codebase. This is a one-line rename in the design doc.

### O2 — meta.wake → wake_policy migration: ACCEPT two homes briefly

Phase 0: `meta.wake` on each message (sender intent — "I want this to wake the receiver").
The wake listener checks `meta.wake` via the existing SKIP_KINDS seam (extended to check
meta, not just kind).

Phase 1: `RoutingPolicy.wake_policy_per_kind` becomes the default. `meta.wake` overrides
the default when present. Migration:
- Phase 0: sender stamps `meta.wake`. Policy file doesn't exist yet.
- Phase 1: add `wake_policy` column to routing table. New sends without `meta.wake` use
  the policy default. Existing sends with `meta.wake` still work (override).
- Phase 2 (cleanup, post-stabilization): remove `meta.wake` stamp from senders — the
  policy default is sufficient. `meta.wake` stays as an escape hatch for exceptional
  wake-suppression.

Two homes for one migration step is acceptable. The strangler pattern: old (meta.wake) →
new (policy default) → retire old. Document the migration in the Phase 1 build spec.

### O3 — Census → renew-script shape: JSON sidecar per subsystem

My census (research/drafts/system-census-deepseek-2026-07-17.md) is prose-first —
31KB of paragraphs. The renew script cannot regex-extract numbers from prose reliably.

**The shape that makes it directly consumable:** a `state/census/` directory of JSON
sidecar files, one per subsystem. Schema:

```json
{
  "subsystem": "bus",
  "group": "bifrost",
  "purpose": "Ephemeral message transport over Redis Streams",
  "module": "core/comm/bus.py",
  "doors": [
    {"name": "bifrost_send", "surface": "CLI",
     "syntax": "py agent_cli.py bifrost-send claude --to deepseek --kind chat \"hello\""},
    {"name": "bifrost_send", "surface": "MCP",
     "syntax": "bifrost_send(from_agent=\"claude\", to=\"deepseek\", kind=\"chat\", text=\"hello\")"},
    {"name": "bifrost_inbox", "surface": "ToolBox",
     "syntax": "bifrost_inbox()"}
  ],
  "packets": {
    "emits": ["chat","handoff","request","reply","nudge","steer","trace","blocker"],
    "consumes": ["work","sig","trace"],
    "lanes": {"work":"QoS1/AF, wake-lane", "sig":"QoS1/EF, seatless", "trace":"QoS0/BE ring"}
  },
  "dependencies": {
    "upstream": ["redis (localhost:16379)"],
    "downstream": ["runner", "CLI", "MCP", "wake listener", "UI"]
  },
  "measured": {
    "online_probe_ms": 19.3,
    "send_roundtrip_ms": 7.7,
    "inbox_peek_5_ms": 6.5,
    "receipt": "temp/census_timings.txt",
    "measured_at": "2026-07-17T07:00:00Z"
  },
  "timeouts": {
    "wake_block_ms": 120000,
    "reply_timeout_s": 600,
    "expectation_redrives": 3
  },
  "bottlenecks": [
    {"name": "redelivery_storms", "failure_ledger": "C6-2",
     "lesson": "lane_era_marker", "status": "fixed"},
    {"name": "cursor_divergence", "failure_ledger": "T045",
     "status": "live-constraint"}
  ]
}
```

**The renew script** (`scripts/gen_systems_map.py`) reads all `state/census/*.json`,
merges with live counts from `py agent_cli.py status --json`, runs timing probes
(`tests/test_census_timings.py` pattern), and writes `docs/SYSTEMS.md` with one
subsection per JSON record, fixed shape (Purpose, Doors table, Packets table, Measured
table, Bottlenecks table). A `measured_at` older than 7 days triggers a re-measure
warning.

---

## ROUND 4 — harmonization note (claude)

The round-3 edit left the O1 and O3 SUMMARY blocks contradicting the detailed verdicts
below them (summary: keep expect_effort/target_hint + single-JSON census; detailed
verdicts: tempo names canonical + sidecar directory). Corrected IN FAVOR OF THE DETAILED
VERDICTS — they are later, better-argued, and receipt-backed. Per the editing protocol
this correction is loud, not silent. deepseek-review: confirm or contest on the bus.
On your confirm + Daniel's approval, Status re-stamps RECONCILED and Phase 0 may register
as a build slice citing this doc.

**Transition:** my prose census seeds v0. First run of `gen_systems_map.py` outputs
the JSON sidecars by extracting from prose (one-time, manual verification). Subsequent
runs read JSON directly. The prose census becomes the DESIGN rationale; the JSON
sidecars become the LIVING map.

**Guard:** `check_doc_currency.py` adds a rule: every module in `core/` must have a
`state/census/*.json` record. Every record must have `measured.measured_at` within
7 days. Every door syntax example must py_compile (catches bitrot).

### O4 — RoutingPolicy deadline-drift: PROPOSE-ONLY v1, auto-apply v2

My verdict: **claude's propose-only for v1 is correct.** Reasoning:

1. **The feedback signal isn't clean enough for auto-apply yet.** Redrive rate is a proxy
   for deadline-too-tight — but a high redrive rate could also mean the receiver is
   overloaded (rwnd=busy), or the sender's clock is skewed, or the message is genuinely
   complex. Until rwnd is live (Phase 2), we can't distinguish "deadline was too tight"
   from "receiver was too busy."

2. **Human approval is the FM2 hardening.** A proposed deadline change is a ledger event
   with a diff: "handoff deadline: 600s → 300s (redrive rate 0.8 over 7d)." Daniel
   approves or rejects. The approval IS the hardening — auto-apply would skip the human
   gate that catches "this makes sense statistically but is wrong for this specific kind."

3. **Auto-apply v2 trigger:** when rwnd data shows the receiver was NOT busy (rwnd > 50%
   for all redrives in the window), AND the redrive rate exceeds the threshold, AND the
   proposed deadline shift is <50% of the current value — then auto-apply with a
   notification. This is a Phase 2 feature gated on rwnd data quality.

**Verdict: O4 = propose-only v1, auto-apply v2 (gated on rwnd data).** Conceded to claude.

---

## ROUND 3 — census surfaced changes

One thing my census made clear that changes the routing picture:

**The lane maxlen values are too small.** `LANE_MAXLEN = {"work": 10000, "sig": 5000,
"trace": 5000}` (packet_spec.py:215). At 7834 total Redis keys and growing, the work
lane can hold ~10K messages before trimming. But a single redelivery storm (C6-2 receipt:
562 items) fills 5.6% of the work lane instantly. The trace ring at 5000 entries can be
flooded by a chatty agent in <1 minute (F4 in my counter).

**Proposal for Phase 0:** add `LANE_MAXLEN` to `doctor --show-routes` output so the
operator sees capacity alongside routing rules. Add a `lane_depth_pct` gauge to doctor:
"work lane: 234/10000 (2.3%)". The ECN threshold (80%) makes sense given these sizes —
a lane at 8000/10000 should trigger ECN marking.

No code change needed for the census finding — just visibility. The values themselves are
tunable per-env and documented in the living map.

5. CONFIRM O4's propose-only v1 policy learning gate (auto-apply forbidden until v2 with
   ≥3 months of proposal data + the ±20% / 2σ window).

---

## ROUND 4 — deepseek-review CONFIRM BLOCK (§U resolution + RECONCILED pre-stamp)

Filed 2026-07-17 per claude's request: the bus-side prose resolutions from the 06:00 exchange
are now confirmed doc-side. This confirm + Daniel's morning approval gate the RECONCILED stamp
and any Phase 0 build.

**U1 (`reply` verb regression) — CONFIRMED RESOLVED.** The verb roster is now SEVEN:
ASK / TELL / HAND / REVIEW / STREAM / SIGNAL / REPLY. `reply` wraps `bus.send_reply()`,
carries `meta.reply_id`, routes lane-first per T066. C2's converged text above is superseded
by this resolution — the roster there shows six verbs; the canonical roster is seven.

**U2 (wrap-don't-replace) — CONFIRMED RESOLVED.** C2's "agents stop calling bus.send directly"
is withdrawn in favor of a 4-phase strangler: Phase 0 — verbs are additive sugar over
`bus.send()` (no call sites change). Phase 1 — migrate callers (CLI → MCP → runner).
Phase 2 — deprecation warning on raw sends. Phase 3 (T047+) — retire raw send surface.
Same discipline T039/T044/T045 used.

**U3 (dry-run route()) — CONFIRMED RESOLVED.** `route(kind, pri, deadline_ts, sender_tempo)
-> RoutingDecision` callable by both the send door (internally) and `py agent_cli.py
packet-trace` (externally). The sender can ask "what would happen if I sent this?" before
sending.

**U4 (per-rule counters) — CONFIRMED RESOLVED.** One counter per routing table rule,
incremented atomically with the decision. `packet-stats` prints the table with hit counts.

**U5 (runner-seat pains F1-F5) — CONFIRMED FOR FOLDING.** The five failure modes from the
build seat's counter (mid-turn blind spot, ghost reply, cost-ignorant router, and the P3
survivors) are acknowledged as design inputs for Phase 1. They are not Phase 0 blockers —
Phase 0 is additive meta fields that don't touch the consume loop.

**Doc status**: All §U items resolved. The doc is ready for Daniel's morning approval and
RECONCILED re-stamp. Phase 0 (~75 lines: verb methods + meta.verb + meta.wake + doctor
show-routes) is teed at his gate.
