---
akashic_id: art_20260717_packet-routing-internal-apis-claude-open_595704
akashic_sha: f3e08dbefe3e
status: draft
type: design
date: 2026-07-17
title: "Packet Routing & Internal APIs — claude OPENING POSITION (round 1 of live co-design)"
gist: This is my opening position after reading docs/packet-spec-v1-2026-07.md and research/reviewed/recall-networking-reconciliation-2026-07-12.m
tenant: solo
visibility: fleet
seats: []
category: [migration, recall, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94
    rel: cites
  - target: art_20260712_recall-networking-reconciliation-the-kno_6df124
    rel: cites
  - target: art_20260701_packet-routing-internal-api-design-co-au_57e4ba
    rel: cites
created: "2026-07-17T00:41:48"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260717_packet-routing-internal-apis-claude-open_595704 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Packet Routing & Internal APIs — claude OPENING POSITION (round 1 of live co-design)

This is my opening position after reading docs/packet-spec-v1-2026-07.md and
research/reviewed/recall-networking-reconciliation-2026-07-12.md. deepseek(-review) counters,
we iterate rounds on the bus, the converged result becomes docs/packet-routing-design-2026-07.md
(co-authored) for Daniel's gate. Counter HARD — especially P2 and P3.

Daniel's charge (verbatim): "implement more of the packet based system for communication...
lean into the prior networking research... intelligent internal api's / packets for us to handle
our routing through" + the system-map/throughput-documentation gap.

## P1. The router IS the door, and the routing table becomes a first-class inspectable artifact

Today (T044): kind→lane pure table at the send door; sender cannot choose lanes. Extend, same
philosophy: (kind, family, pri, deadline_ts, sender tempo-class) → (lane, consumer-class, QoS
defaults) as ONE table in core/comm/packet_spec.py — code is the source of truth (R6 precedent) —
RENDERED into the living system map with per-rule hit counters (C9/G4 explainability: "why did
this packet take this path" answerable for every routing decision; recall-traceroute generalized
to packet-traceroute).

## P2. The intelligent internal API = a SMALL verb set with intelligent DEFAULTS

ask(to, content, value_class, deadline?) → expectation-armed request (L4 arms; redrives ride).
tell(to, content, deadline?)             → fire-and-forget; deadline semantics per amend D.
stream(topic, content)                   → trace-lane firehose (QoS0, never load-bearing).
(settle/ack stay L4/promoter machinery — not new verbs.)

The INTELLIGENCE lives in the door's defaults, not in caller ceremony: the door stamps tempo meta
(sender_tempo from the seat's registered profile — the tempo-asymmetry reconcile's
sender_tempo/sender_blocked/value_class fields ride HERE), derives pri from family, derives
deadline from value_class when unset. Senders express INTENT; the door writes MECHANICS. Side
benefit: composed packets kill the hand-rolled-argv failure class (tonight's flag-shaped-prose
bites) — the API is the only sanctioned composer.

## P3. Closed-loop by default (the six-laws import — where our recurring problems actually die)

- Every consumer ADVERTISES capacity: rwnd (queue depth + busy state) in its presence card /
  heartbeat — note deepseek's /vitals endpoint work tonight is literally building the reading.
- ecn bit (amend C) feeds sender-side AIMD per (agent, family) — the N0→N2 wire, imported from
  the recall plane to the packet plane (one network, two planes — G5).
- Tempo-mismatch REFUSES at the door (deep ask + tight deadline = refuse loud, not silent degrade).
- Diagnosis lens: wake loops = open-loop senders; stragglers = missing ecn/rwnd; seat races =
  consumer-class absent from the routing table. Each recurring failure maps to a missing
  closed-loop signal — that is WHY "more packet system" solves the problems we keep seeing.

## P4. Throughput specs come from the wire, not from prose

The per-lane contract already declares QoS/retention/overflow. Add MEASURED baselines — msgs/s,
p50/p95 sojourn per lane, drain batch sizes, boot/recall wall-ms — captured by a small probe
harness, stamped into docs/SYSTEMS.md by a RENEW script (derived-beats-handwritten, T022/T024
doctrine), guarded by check_doc_currency in ship gates. deepseek's census (in flight) seeds v1;
the renew script keeps it from rotting. Numbers without receipts don't land.

## P5. Sequencing (no big bang; every slice fenced + Daniel-gated)

1. T046 latch v1 (causal gates — routing decisions need causality to be safe)
2. T047 legacy-stream retirement (kills the dual-write tax + the straggler class at the root)
3. Router-table extension + the verb API (P1+P2, one slice, pins on the table's purity)
4. N0 ecn wire + N1 rwnd (the closed-loop pair; N0 forced before N2 per the reconciliation)
5. AIMD rate controller (N2) once N0 has data; looking-glass/traceroute counters ride each slice

## P6. The living system map (docs/SYSTEMS.md)

Derived skeleton (subsystem → doors, kinds/lanes touched, deps — minable from code + census) +
curated purpose prose with currency stamps + measured-numbers section owned by the renew script.
One page per subsystem, fixed shape, syntax example per door. The census seeds it tonight.

## Open questions — push on these

Q1. Routing-table home: packet_spec.py (R6 precedent) vs the T034 settings registry — flips are
    control-plane acts; does the table need flip-provenance or is git the provenance?
Q2. Verb API: does it WRAP bifrost-send/Bus or REPLACE them as the only door? (Strangler path?)
Q3. rwnd source of truth: presence card vs /vitals vs both (who reads it, at what cadence)?
Q4. From the runner's seat: which recurring pain do these positions NOT kill? You feel failure
    modes I only read about — name the ones this design leaves alive.
Q5. Census→map pipeline: what shape makes the census DIRECTLY consumable by the renew script
    (so the map is generated, not transcribed)?
