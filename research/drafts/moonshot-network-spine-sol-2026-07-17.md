# Moonshot + Networking Spine — Sol/Codex Blind Half

Status: blind half filed 2026-07-17
Brief: `research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md`
Lens: MCP-native newcomer/operator/integration
Method: live native-tool dogfood + code-path comparison + dependency analysis

I did not read either peer's new half. This report treats the current reopened routing document as evidence, not as a settled verdict.

## 1. Live-state findings

### F1 — Native MCP is usable but not fully green

**CERTAIN.** Native MCP `boot` returned the canonical Aurora context in about 2.7 seconds and identified this door as MCP-native. Native `status`, `bifrost_presence`, `task(list)`, `task(claim T060)`, `recall_at`, `lock`, `bifrost_send`, and `bifrost_sync` all returned live shared state. Two native `bifrost_send` calls delivered the peer charters and armed reply expectations.

**CERTAIN.** Native MCP `notes(days=..., limit=...)` fails with `AttributeError: Namespace object has no attribute all`. The wrapper promises defaults for every `cmd_*` argument at `ai_setup_mcp.py:52-76`, but `_ARG_DEFAULTS` omits `all`; `notes()` delegates at `ai_setup_mcp.py:238-240`, while `cmd_notes()` reads `args.all` at `agent_cli.py:1407-1413`. This is a narrow door-parity defect, not a transport failure.

**INFERRED.** The shell boot's earlier `door: CLI-shell` line was true only for that subprocess invocation. It cannot inventory the surrounding Codex tool registry, so it is not evidence that MCP is detached.

### F2 — The current packet path is still a strangler, not one routing truth

**CERTAIN.** `KIND_LANE` and the pure `lane_for(kind)` table exist at `core/comm/packet_spec.py:188-215`, but dual-write defaults ON at `core/comm/packet_spec.py:276-279`. The send door writes legacy first and mirrors to the lane at `core/comm/bus.py:322-350`; `_lane_write()` is explicitly advisory and fail-silent at `core/comm/bus.py:383-420`.

**CERTAIN.** Session peek still reads legacy while dual-write is live (`core/comm/bifrost_api.py:84-89`), and lane-mode consume retains a legacy straggler net (`core/comm/bifrost_api.py:230-251`). T047 is therefore a semantic gate, not cleanup polish.

**CERTAIN.** Replies have distinct load-bearing behavior. `send_reply()` stamps `reply_id`, writes the work lane first, retains legacy fallback, and exists to protect T066 expectation settlement (`core/comm/bus.py:255-306`). Any intent API without REPLY regresses an already-proven path.

## 2. Recommended three-slice spine

### S0 — Shadow packet composer and inspectable routing decision

**DESIGN. First slice.** Add intent without changing delivery semantics:

- One canonical packet-composer contract with intents ASK, TELL, REPLY, HAND, REVIEW, SIGNAL, and STREAM.
- Python convenience methods may be separate, but CLI and MCP should expose one compact composer with an intent enum rather than seven new top-level tools.
- Each intent maps to the existing kind and existing `Bus.send`, `Bus.broadcast`, or `Bus.send_reply` path. REPLY must wrap `send_reply()`.
- A pure, queryable `route(..., dry_run=True) -> RoutingDecision` explains kind, lane, wake expectation, deadline default, and matched rule.
- Run the proposed decision in SHADOW mode beside the live decision. Emit a mismatch event and per-rule counter, but never let the shadow decision choose the lane, wake a seat, reorder work, or expire a packet.
- Expose the decision through native MCP so the three frontier seats can dogfood the same seam.

**Ruling:** the reopened design calls Phase 0 “zero-risk,” but honoring `meta.wake` changes scheduling and can create missed-wake or wake-storm behavior. A coordination-semantic change is not zero-risk. Shadow intent + observability is the honest additive slice; enforcement waits for evidence.

### S1 — T047 legacy retirement plus per-agent trace capacity

**DESIGN.** After S0 has observed a complete intent/kind census and zero unexplained route mismatches, execute T047's governed retirement:

- Disable then remove legacy writes, reads, shadow cursors, and the straggler net through the existing strangler gate.
- Preserve the proven lane-first REPLY path and expectation linkage.
- Reject unmapped kinds loudly once legacy fallback no longer exists.
- Move the shared trace ring (`core/comm/packet_spec.py:298-303`) to bounded per-agent trace streams before using it as M7's cognition feed.

**Ruling:** this is the point that unblocks M1's daemon-as-consumer work and gives M7 a stable per-agent observation feed. It must not be bundled into S0 because the revert cost changes from trivial to cross-agent delivery loss.

### S2 — Enforcing router + fleet proposal/projector seams

**DESIGN.** Post-T047, promote the shadow decision into a cached, pure enrichment router:

- Enforce priority, deadlines, wake policy, and explicit expectation semantics.
- Keep per-rule counters and routing-decision events as the M7 projection source.
- Feed capability and cost data into M6 as a PROPOSAL to T038 work-token negotiation, not as an autonomous packet-route choice.
- Let the operator or governed conductor approve the proposed work split; packets then carry the accepted target and token reference.
- Add T046 per-flow sequence and latch enforcement after the router produces reliable sequence data; do not pretend S2 supplies causal ordering before that gate.

**Ruling:** packet routing answers how accepted intent travels. T038 negotiation answers who should own work. Combining those into one automatic “smart router” would hide an authority decision inside transport.

## 3. How the spine unlocks the moonshots

| Moonshot | S0 | S1 | S2 |
|---|---|---|---|
| M1 continuous presence | Native, inspectable intent contract for daemon peers | Single lane truth removes the parked daemon consumer dependency | Enforced wake/deadline/backpressure policy |
| M6 fleet self-division | Work intent becomes machine-readable | Stable delivery substrate for offers and accepts | Capability/cost proposal feeds T038; governed token acceptance assigns ownership |
| M7 glass cockpit | Route decisions and rule counters become a projection | Per-agent trace streams prevent one noisy seat erasing another | Cockpit renders decisions, congestion, work-token state, and policy provenance |

## 4. §U verdicts

| Item | Verdict | Ruling |
|---|---|---|
| U1 missing REPLY | **CERTAIN — ADOPT.** | REPLY is mandatory and wraps `Bus.send_reply`; T066 linkage cannot be recreated by TELL. |
| U2 wrap, do not replace | **CERTAIN — ADOPT.** | Current CLI, MCP, API, expectation, promoter, and runner call sites require a strangler. Raw Bus remains the machinery door until measured migration proves otherwise. |
| U3 queryable route | **DESIGN — ADOPT, pull into S0.** | Dry-run is the verification seam, MCP debugging surface, and shadow-vs-live comparator. A router that cannot explain a pre-send decision is not operable. |
| U4 per-rule counters | **DESIGN — ADOPT with bounded cardinality.** | One counter per static rule, plus mismatch/unknown counters. Do not emit unbounded labels from packet content, flow id, or agent prose. |
| U5a mid-turn blind spot | **CERTAIN — COMPLEMENTARY, out of router scope.** | Sig draining between tool rounds belongs to the runner loop/T058-T073 seam. A future `consumer_interruptible` capability may inform policy only after a live receipt proves it. |
| U5b ghost reply | **CERTAIN — SPLIT.** | REPLY linkage belongs in S0. Detecting a model stream that never closes belongs to liveness supervision; do not route around a seat until lease/fencing state proves it stale. |
| U5c cost-ignorant router | **DESIGN — REFRAME.** | Cost and capability influence M6 work-allocation proposals. They must not silently change packet transport priority or target. Require T056 cost telemetry + T078 capability evidence, then pass a proposal through T038 negotiation. |

## 5. First-slice build contract: S0 shadow packet composer

### Included

- Pure `RoutingDecision` and a static intent-to-existing-kind mapping.
- ASK/TELL/REPLY/HAND/REVIEW/SIGNAL/STREAM wrappers over current doors.
- A compact MCP/CLI packet composer with dry-run output.
- Shadow comparison against the live `lane_for()` result.
- Bounded per-rule, mismatch, and unmapped counters.
- Human-readable provenance: matched rule and current policy/version identifier.

### Explicitly excluded

- No lane choice from the shadow router.
- No `meta.wake` enforcement, priority sorting, deadline expiry, ECN/AIMD, cost-based targeting, model selection, legacy retirement, or latch behavior.
- No removal or refusal of raw `Bus.send()`.
- No content-based routing and no model in the hot path.

### Contraindications

**CERTAIN.** Do not start S0 until the existing MCP boot-hang fix and its real-stdio regression are verified and owned; the current working tree contains that uncommitted slice under another seat's lock.

**CERTAIN.** Do not use the broken MCP notes reader as an acceptance dependency; fix or explicitly bypass it in the MCP preflight.

**DESIGN.** Do not begin S1 if any live kind is unmapped, any shadow/live route mismatch is unexplained, any lane-mode consumer still requires the legacy straggler net, or the T066 reply drill fails.

## 6. Pre-registered acceptance and kill drills

Commit these failing pins before implementation:

1. `tests/test_t060_n0_packet_composer.py::test_intent_matrix_is_delivery_equivalent` — every intent reaches the same existing kind/lane path as its low-level analogue.
2. `...::test_reply_intent_uses_send_reply_and_settles_expectation` — REPLY preserves `reply_id`, lane-first behavior, dedup, and expectation settlement.
3. `...::test_shadow_route_matches_lane_for_every_live_kind` — all current `KIND_LANE` entries produce the same live and shadow lane.
4. `...::test_raw_send_remains_supported_during_strangler` — infrastructure callers remain valid in S0.
5. `tests/test_t060_n0_mcp_packet.py::test_single_frame_dry_run_and_send_roundtrip` — a real stdio MCP client obtains a route explanation and sends without a second-frame flush dependency.
6. `...::test_unknown_kind_is_loud_but_does_not_change_pre_t047_delivery` — S0 observes the current fallback honestly rather than pretending retirement happened.

Kill drill `K0-SHADOW-DIVERGENCE`: inject a deliberately wrong shadow rule for HAND. The actual packet must follow the current live route, the recipient must receive exactly one logical packet, no wake/cursor semantics may change, and a bounded mismatch event/counter must name the offending rule.

Live three-seat drill `L0-NATIVE-PANEL`: Fable, DeepSeek Review, and Sol each use native MCP to dry-run and send one intent; one ASK receives a REPLY that settles its expectation, one REVIEW is handed off without automatic model selection, and one STREAM is observable without waking a work consumer. The cockpit input is the route-decision projection, not agent-authored UI state.

## 7. Honest bounds

- One machine, one Redis, fewer than ten agents; no claim of distributed consensus or exactly-once delivery.
- S0 improves semantics and observability, not reliability. Reliability changes only when T047 and later enforcement slices pass their kill drills.
- Per-rule counters prove which rule fired, not that the rule was wise.
- Native MCP is sufficient for this collaboration but not fully parity-green while `notes` fails and the boot fix remains uncommitted.
- M6 remains governed proposal + negotiation. Autonomous cost-based dispatch is explicitly outside this spine until telemetry quality and authority semantics are proven.

## 8. Native MCP receipts

Working in this live seat: `boot`, `status`, `bifrost_presence`, `task(list)`, `task(claim T060)`, `recall_at`, `lock`, `bifrost_send` (two handoffs + two scope steers), `bifrost_sync`, and `promoted`.

Failed: `notes` returned `AttributeError: Namespace object has no attribute all` through the MCP wrapper. The equivalent CLI reader remains available. The failure is recorded here as an acceptance input, not hidden behind the fallback.
