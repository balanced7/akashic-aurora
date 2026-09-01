---
akashic_id: art_20260825_sync-confusion-drill-spec_67bd7e
akashic_sha: 1f8cc0e4ee85
schema_version: 1
status: current
type: design
date: 2026-08-25
title: sync-confusion-drill-spec
gist: "# Sync-confusion kill-drill — spec (draft, for Daniil's cross-instance sync ask) Status: DRAFT spec, not a design. Author: dsh_agent/Rill, 2"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, security, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-25T21:06:55"
updated: "2026-08-25T21:06:55"
---
<!-- GENERATED PROJECTION of art_20260825_sync-confusion-drill-spec_67bd7e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# sync-confusion-drill-spec

# Sync-confusion kill-drill — spec (draft, for Daniil's cross-instance sync ask)

Status: DRAFT spec, not a design. Author: dsh_agent/Rill, 2026-08-26.
This file pre-registers the ACCEPTANCE for the confusion-avoidance half of the sync
arc, before the sync design exists. The five laws (signed manifest, one-way git, deny
list, one master per fact, store-and-forward) are the design's invariants; this drill
proves the three that keep the house standing. RED-first per method: each case is a pin
that FAILS against today's tree, and each case's fix is named, not designed.

## The drill cases (each = one acceptance pin)

C1 — THE PEER-PULL TRAP (one-way git law). Setup: instance A commits a delete of a
tracked file F to master; instance B has a LOCAL MODIFICATION of F, uncommitted.
Action: B pulls. ACCEPTANCE: the pull CONFLICTS LOUDLY (modify/delete), B's local work
survives, and B is TOLD which ceremony resolves it. RED today: a plain pull silently
deletes B's working copy. The t384 grant --bootstrap precedent proves the mechanism
class (upstream-delete meets local-modify); the sync arc generalizes it to EVERY
instance-bound file. Pin shape: a two-tree git fixture driving the pull, asserting the
conflict.

C2 — AUTHORITY NEVER SYNCs (deny-list law). Setup: a sync manifest names a path on the
deny list (security/acl.json, state/coord/discord_seat_channels.json, .secrets/*).
Action: the sync door is asked to ship it. ACCEPTANCE: REFUSED with the named rule,
before any bytes move. RED today: no sync door exists to refuse. Fix = the deny list
as a checker pin (same discipline as check_ui_contract): the manifest builder and the
fetch path BOTH consult it, so neither side can forget independently.

C3 — TWO WRITERS, ONE TRUTH (one-master-per-fact law). Setup: both instances claim
mastery of the same fact (e.g. both register a ledger row id). Action: reconciliation
runs. ACCEPTANCE: exactly one master declared, the other row is a stamped derived copy,
and the disagreement is LOUD — never a silent last-writer-wins. RED today: nothing
declares masters. Fix = the master-declaration table (T374 doctrine) + a reconciliation
checker that reports two-master rows.

C4 — RESUME, NOT REPLAY (idempotency law, RB-26 one plane up). Setup: B syncs, crashes
mid-transfer, reconnects, syncs again. ACCEPTANCE: zero duplicate rows, zero replayed
side effects; second pass is all skips. Content-addressed refs make this nearly free —
the pin proves the ack cursor advances AFTER apply.

## Sequencing

Pins C1-C4 land RED alone (one commit, no implementation), then the sync slice builds
the smallest thing that turns each green: a manifest schema + fetch-by-ref + deny-list
checker + master table. Vandor's rulings fold in at the design fence, NOT before these
pins — the laws they pin are the parts of the design that cannot change.
