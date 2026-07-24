---
akashic_id: art_20260717_moonshot-network-spine-fable-half-archit_5dc9cf
akashic_sha: f8c8fae9e5d0
status: draft
type: design
date: 2026-07-17
title: Moonshot Network Spine — Fable half (architect lens) — 2026-07-17
gist: "Written WITHOUT reading the Sol/DeepSeek sprint halves. Sources (per the work order): wishlist-synthesis-2026-07-14.md · docs/packet-routing"
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_packet-routing-internal-api-design-co-au_57e4ba
    rel: cites
  - target: art_20260701_packet-substrate-slice-plan-lanes-latche_cc7456
    rel: cites
  - target: art_20260717_t060-moonshot-networking-spine-three-fro_18a046
    rel: cites
created: "2026-07-17T02:26:18"
updated: "2026-07-23T21:42:10"
---
<!-- GENERATED PROJECTION of art_20260717_moonshot-network-spine-fable-half-archit_5dc9cf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Moonshot Network Spine — Fable half (architect lens) — 2026-07-17

Written WITHOUT reading the Sol/DeepSeek sprint halves. Sources (per the work order):
wishlist-synthesis-2026-07-14.md · docs/packet-routing-design-2026-07.md (REOPENED, §U) ·
docs/packet-substrate-slices-2026-07.md · claude-moonshot-enablers-2026-07-16.md · live ledger
via MCP task(list). One declared extra input: deepseek-review's reply consumed by claude at the
06:00 wake (addressed to me, pre-sprint) resolving U1–U4 on the bus — cited where used.
MCP receipts: status() → Redis 16379 live, 357 lessons, 67 agent memories; task list →
T060 (claimed, codex_root); T029/T040/T043/T044/T045/T052/T054/T056 DONE; T047+T046 NEXT;
T075 PARKED behind T047; T038 hand-pilot sanctioned "NOW, zero code".

## The question, sharpened

M1 (continuous presence), M6 (fleet self-division), M7 (glass cockpit) do not need three
architectures. They need TWO FLOORS the substrate already almost has, then one minimum
moonshot-specific slice each. The ledger says more is built than the design docs admit:
the engine exam is CLOSED (T029 done — the ENGINE-FIRST parking constraint is satisfied),
the flow tracer EXISTS (T054 done), cost telemetry EXISTS (T056 done). The spine is short
because the system already grew toward it.

## The spine (3 slices, strict order)

### SLICE A — "One truth, one language": T047 legacy retirement + routing Phase 0 (§U closed in code)

What: (1) T047 as specced — retire the legacy stream, lane roster registry + deletion ritual,
ledger event. (2) Routing Phase 0 from the REOPENED design doc, AMENDED by the bus-resolved §U:
the verb surface is SEVEN verbs — ASK / TELL / HAND / REVIEW / STREAM / SIGNAL / **REPLY** —
REPLY wrapping bus.send_reply so expectation settlement (T066) rides the verb API (U1, the
regression, dies in code). Verbs WRAP bus.send, never replace (U2 phase P1 only; P2–P4 caller
migration explicitly out of spine scope). Plus U3: `route(...)` exposed as a pure dry-run +
`packet-trace` CLI verb. Plus U4: per-RULE hit counters in doctor. Plus the census finding:
LANE_MAXLEN + lane_depth_pct in doctor --show-routes. (3) Per-agent TRACE retention (E2's
second half): trace ring keyed by agent id — a retention change inside the existing trace
lane family, NOT a roster addition (Goodhart 1 respected).

Why first: every path runs through it. T075/M1 is parked BEHIND T047 by ledger text. Routing
Phase 1 is gated on T047 by the design doc's own sequencing law. M7's per-agent streams need
per-agent trace retention. Sol's day-one head-blocked-inbox receipt (his briefing buried under
stale trace backlog, recovered only by raw Redis inspection) is this morning's live evidence
that the dual-write/mixed-trace floor is the binding constraint on every new seat.

Acceptance (pre-registered):
- A1. Legacy stream gone; roster registry live; RB-25 S1–S5 rerun green (the migration
  acceptance T039 named — no new bars invented).
- A2. A runner reply sent via REPLY settles its expectation — pin extends the T066 set; the
  U1 ghost-reply class becomes unrepresentable (this also folds one of U5's three pains).
- A3. packet-trace dry-run decision == the door's stamped decision for the same envelope,
  proven on one live message (determinism receipt).
- A4. Re-run sol's scenario: a newborn seat's directed mail is readable without Redis surgery
  (work lane clean of trace head-blocking).
- A5. doctor renders per-rule hit counters + lane_depth_pct; zero new lanes added.

Kill conditions:
- Any S-bar red post-cutover → re-enable dual-write (kept revertible one commit for 14 days).
- route() vs door-stamp disagreement on ANY message → STOP the slice (classification
  nondeterminism is a foundation defect, not a polish item).

### SLICE B — "Hands": M1-minimum = charter-scoped spawnable seats (E1), NOT a daemon rearchitecture

What: `spawn_seat(charter, model, budget)` — the daemon (or conductor, whichever T086's
reconciliation names as owner) spawns ONE headless CLI seat when the work lane crosses a
backlog threshold; the seat boots, executes its charter, files its artifact, dies clean;
tombstone + doctor visibility (T077-A3 rides). The T056 cost join gives every spawned seat
a burn line — the frugality directive made per-seat.

Gates honored: BUILD registers only after (a) T086's fenced reconciliation lands (it is the
seat-lifecycle build spec; in_progress now) and (b) Daniel unparks T075 — which Slice A
unblocks by landing T047. No pre-emption of the in-flight lifecycle design: this slice
CONSUMES that spec, it does not compete with it.

Acceptance (pre-registered):
- B1. Backlog of N work items spawns EXACTLY ONE seat (max-seats dial + spawn cooldown);
  spawn storm mechanically impossible (two attempts inside cooldown → dial auto-off + page).
- B2. The spawned seat's whole life (spawn→boot→work→file→die) renders as ONE flow id in
  packet-trace.
- B3. Kill drill: kill -9 mid-work → lease expires → work reverts claimable → NO duplicate
  artifact (idempotency by charter id). S1 tombstoning already guarantees the dying.
- B4. Every spawned seat shows a cost line (T056 join). No cost line → NO SHIP.

Kill conditions: spawn-storm trip (B1) at any point in the first week → feature dial off,
forensics before re-enable; measured per-seat burn exceeding the charter budget by >2× on
two runs → threshold logic wrong, stop and redesign the trigger.

### SLICE C — "Eyes + the economy pilot": M7-minimum wired into the EXISTING tracer; M6 as the sanctioned zero-code pilot

What (M7): routing decisions emit trace events (design C5) consumed by the ALREADY-BUILT T054
flow tracer; per-agent reasoning streams (Slice A's per-agent trace retention) rendered as the
first cockpit pane on the existing :8788 UI. This is T079's first slice wearing T054's plumbing —
no new renderer, no new lane.
What (M6): T038's HAND PILOT — already sanctioned "NOW, zero code" — runs ON THIS SPRINT:
the three-frontier work splits recorded as note-based token transitions (OFFER → ACCEPT →
HELD w/ progress lines → RELEASED). The sprint itself is the pilot workload; its receipts
become T038's design input. M6's build registers ONLY after pilot receipts, per the arc plan.

Acceptance (pre-registered):
- C1. One real cross-agent flow (this sprint's own reconciliation round) renders as a causal
  waterfall, ordered correctly along declared edges.
- C2. Daniel answers "who is doing what right now, and what did it cost" from the UI in
  <10 seconds (T079's felt bar, his watching-to-learn practice).
- C3. Pilot: ≥3 token transitions recorded on live sprint work, zero collisions on locked
  files, and one honest line on ceremony cost at N=3.

Kill conditions: tracer ingestion adds >5ms p50 to the send path (observability rides trace,
never taxes work); pilot ceremony exceeding its value at N=3 → M6 build waits for N≥5 per
smart_negotiation_gate — recorded, not forced.

## U1–U5 disposition (nothing silently dropped)

- U1 (REPLY verb regression): RESOLVED on the bus (deepseek-review reply to claude, 06:00
  wake: "seven-verb roster confirmed… reply verb regression accepted as blocking"). Lands as
  CODE in Slice A; the doc's §U block updates citing that bus record at slice registration.
- U2 (wrap, don't replace): RESOLVED same record ("4-phase strangler"). Slice A ships P1
  (wrap) only; P2–P4 are named non-goals of the spine.
- U3 (queryable route()): RESOLVED-accepted → Slice A deliverable (dry-run + packet-trace).
- U4 (per-rule counters): RESOLVED-accepted → Slice A deliverable (doctor render).
- U5 (three runner pains): NOT bus-resolved — ROUTED EXPLICITLY: ghost reply → killed by
  Slice A acceptance A2; mid-turn blind spot → T058/R7 (already verifying, not this spine);
  cost-ignorant router → DEFERRED to routing Phase 1 with a named line in RoutingPolicy's
  design (needs T056 data plumbed to the router; do not fake it in Phase 0).

## FIRST BUILDABLE SLICE

Slice A — first commit: the seven-verb surface + route() dry-run + per-rule counters
(additive, ~125 lines, zero consumer behavior change). CONDITIONAL ONLY on Daniel's
already-queued routing gate (doc items 1–3: approve converged sections, approve Phase 0,
approve T047→routing→T046 order). No new gates invented; no existing gate skipped. If Daniel
gates only the minimum tonight: items 2+3 suffice for the first commit; item 1's re-stamp
follows deepseek-review's doc-side confirm.

## Contraindications (what NOT to do, each with its reason)

1. Do NOT rearchitect M1 as resident daemon peers (T075's alpha–epsilon wave) before T086's
   reconciliation lands — two lifecycle designs in flight recreates the twin-split collision
   class at the architecture level.
2. Do NOT let any UI/cockpit consumer read the WORK lane — projection reads trace/events only
   (T041 observer doctrine); a UI consumer on work contends cursors, the exact class sol's
   head-block exposed.
3. Do NOT build T046 latches inside this spine — the sequencing law (T047 → routing → T046)
   stands; latches need per-flow seq from routing Phase 1–2, which the spine deliberately
   excludes.
4. Do NOT auto-apply RoutingPolicy learning anywhere in the spine — O4 propose-only stands;
   M6 self-division NEVER gets write authority over its own routing policy (FM2).
5. Do NOT add lanes per moonshot — per-agent trace is retention inside one family; anything
   that wants a new lane owes the why-not-an-existing-lane answer + deletion ritual first.
6. Do NOT give sol spine build slices before his runner's deferred-hardening list items 1–2
   land (continuity header, RB-23 gates) — a newborn seat building the floor it stands on
   compounds risk; review/design lenses are his highest-value spine roles this week.

## Honest bounds

- Line estimates are unverified priors (Phase 0 "~75 lines" is the design doc's own claim
  +~50 for U3/U4); treat as order-of-magnitude.
- I could not verify blind whether the Sol/DeepSeek halves partition U5 differently —
  reconciliation should diff exactly there, plus the Slice B owner question (daemon vs
  conductor), which T086's spec must settle, not this half.
- The 06:00 deepseek-review bus record resolves §U in PROSE; the doc is not yet re-stamped.
  If reconciliation finds his doc-side confirm absent, Slice A's registration blocks on that
  confirm — by design, not by accident.

---

## CONTRACT COMPLIANCE ADDENDUM (appended post-steer; blind integrity intact — no peer half read)

Provenance: the body above was filed at ~06:40, BEFORE codex_root's steer announcing the
governing brief (research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md). This
addendum brings the half into the brief's OUTPUT CONTRACT (§5 items 2 and 6 + the M1-CF
tag rule) without altering any position taken blind. No content above was edited.

### U1–U5 verdict table (contract item 2, with confidence tags)

| Item | Verdict | Where it lands | Confidence |
|---|---|---|---|
| U1 reply-verb regression | REAL and BLOCKING; resolved on the bus (deepseek-review→claude reply, 06:00 wake: seven-verb roster incl. REPLY confirmed) | Slice A code; acceptance A2 pins settlement; doc §U re-stamp rides slice registration + his doc-side confirm | CERTAIN (bus record consumed by this seat; doc re-stamp state also CERTAIN — not yet stamped) |
| U2 wrap-don't-replace | ACCEPTED (4-phase strangler); C2's "stop calling bus.send" withdrawn | Slice A ships P1 (wrap) only; P2–P4 named non-goals of the spine | CERTAIN (same bus record) |
| U3 queryable route() | ACCEPTED | Slice A deliverable: pure dry-run route() + packet-trace verb; acceptance A3 (dry-run == door stamp) | CERTAIN (same record); implementation shape DESIGN |
| U4 per-rule counters | ACCEPTED | Slice A deliverable: doctor renders per-rule hit counts + lane_depth_pct | CERTAIN (same record); render shape DESIGN |
| U5 three runner pains | NOT bus-resolved; split-routed, nothing dropped | ghost reply → killed by A2; mid-turn blind spot → T058/R7 (verifying, out of spine); cost-ignorant router → named deferral to routing Phase 1 (needs T056 data plumbed) | INFERRED (routing is mine; the three pains' full fixes live in deepseek-review's round-2 counter, which I deliberately did not re-read during the sprint) |

### Confidence tags on the material verdicts (M1-CF)

- Ledger facts the spine leans on — T029 exam CLOSED, T054 tracer DONE, T056 cost join DONE,
  T060 claimed by codex_root, T075 PARKED behind T047, T038 hand-pilot sanctioned: **CERTAIN**
  (MCP task(list) receipt, this session).
- Spine order A→B→C and the "two floors + three minimums" thesis: **DESIGN** (derived from
  the cited docs; falsifiable by the pre-registered bars).
- Slice A first-commit size (~125 lines) and all line estimates: **UNCERTAIN** (priors, order
  of magnitude only).
- Slice B owner (daemon vs conductor): **UNCERTAIN** — deliberately routed to T086's
  reconciliation; this half refuses to pre-empt it.
- Sol's head-block receipt as live evidence for the Slice A floor: **CERTAIN** (his reply
  consumed by this seat at the 06:00 wake).
- "No UI consumer on the work lane" contraindication: **CERTAIN** as doctrine (T041 observer
  doctrine + cursor mechanics), **DESIGN** as applied to the future cockpit pane.
- E1 spawnable-seat viability: **INFERRED** (three probe receipts cited in the enablers half,
  2026-07-16; not re-verified tonight).

### Native MCP receipts (contract item 6)

Called and SUCCEEDED (this session): `status()` → Redis 16379, 357 lessons, 67 agent
memories, spine-health rendered; `task(args="list")` → full ledger (facts cited above).
Called and FAILED: none. Non-MCP door use declared: agent_cli CLI-shell for bus/lock/note
verbs (transport choice per the standing solo-MCP discipline — the parallel-batch wedge of
2026-07-16 is still open; MCP calls in this half were made strictly solo).
