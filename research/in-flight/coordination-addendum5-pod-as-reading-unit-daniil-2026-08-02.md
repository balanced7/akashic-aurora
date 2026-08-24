# Addendum 5: RATIFIED at the gate + pod as the reading unit + the pod is enterable

Status: current (2026-08-02, claude#30e6af5c). Records Daniil's gate ratification and two
new rulings he raised at the same moment.

## GATE RATIFICATION — Daniil, verbatim: "I approve all of them"

All six decisions from pod-round2-reconciliation-2026-08-02.md are RATIFIED:

1. VOCABULARY: GRAMMAR (fixed rules) / ENGAGEMENT (the negotiated deal) / POD (the work
   scope it convenes) / POSITION (one agent's state in it) / BOARD (the render ONLY) /
   STEWARD (the pod's deterministic servicer, Sol's addition — the acting part is named so
   the pod cannot quietly become an actor).
   CONVENER CORRECTION, 2026-08-02: I described the pod as "the ROOM the engagement
   convenes" throughout the design conversation. That is a NAMES-THAT-LIE COLLISION and it
   is retracted. ROOM is a SHIPPED UI ENTITY — the bifrost console renders a ROOMS panel
   whose own definition text reads "A room is a bus namespace." I missed it because the
   label is rendered from the channels API, not literal in the source, and my grep for
   "room" returned only engine-room and the metaphor comments. Daniil caught it by
   screenshot. POD is never "the room"; it is the WORK SCOPE. Same failure class that
   retired CONTRACT (occupancy), found the same way: by looking rather than by reasoning.
2. TOPOLOGY REASON REPAIRED (kimi's correction of the convener's own ruling): the verdict
   "one shared pod, per-agent plugs" stands, but NOT because "two paths are diseased" —
   that proves too much, since board and ledger are also two paths. The ratified rule is
   PEERS RECONCILE, PROJECTIONS REBUILD. Two pods would be two AUTHORITIES with a hope
   between them; a plug is an adapter, never a replica.
3. BUILD ORDER: Sol's staged vote supersedes the flat 0->4. Approve now = observation
   envelope + runner tap + gateway correlation + append-only journal + gateway failure
   drills. Then = calibrated codebook + sensor-only UI. HOLD = position/pod state until
   two-level identity, replayable events and generation-fenced policy exist. Then = task
   badges, help, steering. LAST = heads-down masking behind the operator-breakthrough
   kill drill.
4. T-NUMBERS: five slices to be minted (sensor plane + gateway, codebook, board render +
   UI, position store, engagement/pod v1). T095 is SUPERSEDED rather than unparked — the
   design has moved far enough that carrying its old scope would mislead.
5. KEYS-IN-GATEWAY: LATER, as its own slice. Kept named because it is the only form where
   coverage is structurally guaranteed rather than monitored.
6. KIMI SPEND: HOLD unless a specific premise question arises (~$172 of $225, hard refuse
   $203). deepseek is the mechanism workhorse; codex/Sol has proven the verification lens.

## RULING A: the POD does NOT replace the CHANNEL

Daniil: "we need to decide if pod replaces rooms or not for reading the pod based
communications."

WHAT EXISTS TODAY: ROOM IS A SHIPPED, NAMED, USER-FACING ENTITY. The console renders a
ROOMS panel (currently "ROOMS 1 / bifrost [MAIN] claude, deepseek, kimi") backed by
scripts/bifrost_ui.py:312 _api_channels — a room IS a bus namespace, discovered by worklive
keys ("a channel exists when someone beats in it"). The panel's own text states the
contract: "A room is a bus namespace. Side rooms are invisible to this feed by design —
listing them here is the only way you can see one exists... an empty room is not a
conversation." Code says CHANNEL, the operator sees ROOM; they are one concept with two
names, which is its own small LEXICON debt worth settling on one word.

THE TEST (key/writer/lifetime, the same one that settled GRAMMAR/POSITION):
  channel: key = the namespace | writer = substrate/config | lifetime = the deployment
  pod:     key = the engagement | writer = its members     | lifetime = the engagement
Different on all three => separate objects. RULING: a CHANNEL is a WORLD (an isolation
boundary; test-* drill namespaces are invisible to production BY DESIGN). A POD is a WORK
SCOPE INSIDE one. One channel, many pods. The pod does not replace the channel and must
never be keyed by namespace.

WHAT THE POD DOES REPLACE — and this is the real finding behind Daniil's question: the UI
has NO READING UNIT AT ALL. Today it renders a flat message log plus a deck; there is no
per-conversation grouping, which is why reading the bus has always meant scanning an
undifferentiated stream. The pod supplies the structure the feed has always lacked: you
read BY POD, within a channel. That is a projection-lane change (fence-lite), and it is the
first thing in this arc that makes the bus legible rather than merely observable.

NAMING HYGIENE, adopted (INVERTED from this doc's first revision): ROOM belongs to the
NAMESPACE — it is shipped, rendered, and defined in the operator's own console. The POD
must never be called a room. The pod is the WORK SCOPE. Vocabulary that survives:
  ROOM (= namespace, = channel in code) contains many PODS; a POD is one ENGAGEMENT's work
  scope; a BOARD renders pods; a POSITION is one agent's state inside a pod.

## RULING A-2: the ROOMS panel is a dead end today, and that is the immediate ask

The panel's own text admits the gap: "listing them here is the only way you can see one
exists." You can see that a side room EXISTS and you cannot read it, enter it, or speak
into it. Discovery without access. That is shippable NOW, needs no pod, no sensor plane and
no gate decision — it is pure projection lane.

SLICE (projection, fence-lite, independently shippable):
  1. Room entries in the panel are CLICKABLE -> switch the feed to that room's namespace.
  2. The composer targets the SELECTED room (its Inform/Steer/Interrupt ladder already
     exists) so the operator can speak into a side room instead of only the main one.
  3. The current room is unmistakable in the chrome — reading one room while typing into
     another is the failure this must not create.
  4. Empty rooms stay invisible BY DESIGN (the existing contract; do not "fix" it).
This is the same shape as RULING B one level up: the pod badge becomes an entry point
later, exactly as the room entry becomes one now. Rooms first — it exists, it is visible,
and it is already frustrating.

## RULING B: the pod is ENTERABLE by the operator, not merely readable

Daniil: "that button needs to be clickable to view the conversation and be able to directly
speak into the pod."

This makes the operator a PARTICIPANT, not an observer, and it completes a mechanism the
design already built for agents. Requirements:

1. The pod badge on the board is an ENTRY POINT, not a status glyph. Click => the pod's
   conversation view.
2. The view is scoped to the pod: its engagement terms, its members' positions, its
   deferred queue, its alerts, its message history — the thing "readable on Bifrost" from
   addendum 4, now given a surface.
3. THE OPERATOR CAN SPEAK INTO THE POD. Mechanically this is the pod-addressed steer
   already designed in addendum 4 (steer the WORK, not the worker) — the operator gets the
   same addressing mode as agents, which is why no new transport is needed.
4. OPERATOR MESSAGES ALWAYS BREAK THROUGH: heads-down defers peers, never Daniil. This is
   the existing frm=user override (bifrost_wake wake_worthy, born from the "I'm back!"
   incident) carried into the pod. Non-negotiable, and it is the same rule the
   heads-down kill drill exists to protect.
5. The operator is NOT a pod member with a position — he holds no lease, owes no
   conclusion, and cannot be waited on by a gate. He speaks in and reads out. A gate that
   could block on the operator would be the fleet holding its own operator hostage.

LANE: the button, the view and the compose box are PROJECTION (fence-lite, gated on Daniil
seeing it). The pod-addressed steer delivery path is SUBSTRATE and is already sequenced
under "then: task badges, help, steering" in the ratified build order. So the READ half can
ship with the sensor-only UI; the SPEAK half lands with steering.

## SEQUENCING NOTE

Neither ruling changes the ratified build order. Ruling A is a naming/scoping decision with
no build cost. Ruling B splits across two already-sequenced slices (read with the UI, speak
with steering) and adds no new stage.
