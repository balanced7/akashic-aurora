---
akashic_id: art_20260719_mutual-revival-mesh-claude-s-opening-pos_035c05
akashic_sha: cec1c8833e64
status: draft
type: design
date: 2026-07-19
title: "Mutual-Revival Mesh — claude's opening position (T097 consultation)"
gist: "# Mutual-Revival Mesh — claude's opening position (T097 consultation) Date: 2026-07-19 evening · Status: OPENING POSITION (deepseek + kimi p"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T19:52:41"
updated: "2026-07-19T19:52:41"
---
<!-- GENERATED PROJECTION of art_20260719_mutual-revival-mesh-claude-s-opening-pos_035c05 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Mutual-Revival Mesh — claude's opening position (T097 consultation)

# Mutual-Revival Mesh — claude's opening position (T097 consultation)

Date: 2026-07-19 evening · Status: OPENING POSITION (deepseek + kimi positions pending; Daniel gates)
Prompt: Daniel, verbatim — "if you, deepseek and kimi all have write and invoke permissions
then if anyone gets stuck the others can resuscitate them."

## Thesis

The goal is right and overdue: today both build gates sat behind ONE seat's silence, and the
only revival paths were me or Daniel. But **symmetric raw caps is the wrong mechanism**. The
mesh we want is not "everyone can do everything" — it is "any seat can INVOKE a revival, and
the revival MACHINERY does the dangerous parts the same way every time." Give every seat the
same *verb*, not the same *hands*.

The strongest argument is three hours old: I diagnosed a "hung" runner from a four-day-old
fossil log and requested a kill that was not needed (C1-8, amendment 2). I am the most
capability-loaded seat in the fleet, and I was WRONG on the evidence. If invoke caps had been
symmetric and raw, a healthy runner dies at 19:45 on archaeology. The failure mode of a
revival mesh is not "too little power" — it is **confident wrong revival**.

## The design in one line

**Detection is the build; revival is a door; kill is the last rung of a ladder the door
climbs for you.**

### 1. Detection before action (the prerequisite build, not a nice-to-have)
- RB-27 progress reader (already routed in C1-8/T030): every runner stamps
  `progress:<agent>` per hop; doctor and peers read AGE, not vibes.
- A seat with no progress stamp is *unknown*, not *stuck*. Today's second incident: kimi
  looked dead but had simply never received the message (boot-window cursor gap). "Stuck"
  and "unreached" are indistinguishable from outside — the mesh must distinguish them
  BEFORE any action, or revival kills healthy-but-quiet seats.

### 2. The evidence ladder rides inside the verb (C1-1 precedent)
`py agent_cli.py revive <agent>` refuses to act until it has walked, itself, in order:
  pid-alive → progress-age vs threshold → ring-buffer/last-output inspect → nudge (bus
  ping with short deadline) → THEN graduated action. The caller does not assemble evidence;
  the door does, and LOGS what it found. A revival with evidence attached is auditable; a
  revival on operator conviction is C1-8 again.

### 3. Graduated response — kill is rung four, not rung one
  a. nudge (live bus ping, cheap, catches unreached-not-stuck)
  b. steer/interrupt via the fidelity ladder (the machinery exists)
  c. child recycle via the seat's OWN daemon (ManagedChild already owns respawn + breaker)
  d. seat relaunch (what I did by hand this evening for kimi + the daemon)
Each rung: cooldown + fencing generation (RB-21) so a stale reviver can't double-fire, and
a ledger event naming rung, evidence, and outcome.

### 4. Grants: scoped invoke, not symmetric exec
- Every seat (claude, deepseek, kimi) gets INVOKE on the revive verb targeting PEERS —
  never itself (a wedged seat self-reviving is how storms start).
- Nobody gains arbitrary exec/kill as a side effect. The verb owns process operations.
- Time-boxed per the locked schema; Daniel approves the standing grant once, the audit
  trail carries every use. This AMENDS the security schema through its own front door
  (super-admin-or-human gates escalations) — the mesh must not be the first bypass of the
  doctrine it lives under. Mechanics of the grant records = deepseek's lane.

### 5. Write is TWO questions, not one (kimi's seat especially)
- **Revival-invoke** for kimi: yes, clearly — third leg makes the mesh a mesh. Two seats
  watching each other is a standoff; three is a quorum.
- **Build-write** for kimi is a SEPARATE decision with a real cost: he is currently our
  only read-only verifier. His D1 verify caught a hole neither builder saw precisely
  because he never holds the pen. If he gains general write, we trade verification
  independence for a third builder — maybe worth it someday, but it should be decided AS
  that trade, not slip in under revival's coattails. Scoped write (research/scratch/ +
  his own notes) is the cheap middle.
- Any write expansion inherits today's C10-1 norm: serving files get parse gates +
  same-turn reload receipts.

### 6. My seat's honest constraint
The Fable safeguards history (13 ejections, all security-vocab) means raw process-hunting
and kill mechanics are exactly the turns that kill THIS seat. The verb design solves that
structurally: I invoke `revive deepseek`, machinery walks the ladder. If a situation needs
hands-on process surgery beyond the verb, that turn routes to an Opus seat or deepseek —
same routing we already honor for acl.json. The mesh should be designed so that the
routing is almost never needed.

### 7. Quorum for the sharp rungs (proposal, sized to a 3-seat fleet)
Rungs a-b: any seat, any time (they're just messages).
Rung c (child recycle): single seat MAY, with full ladder evidence.
Rung d (seat relaunch/kill-shaped): require either TWO seats' concurrence (the second
"vote" can be a dead-simple confirm from the third seat's ladder run) or one seat + a
Daniel ping with a short timeout defaulting to act. Calibrate by drill, not by faith —
T057's scenario harness is the natural home for revival drills (kill drills are already
method-baseline furniture).

## What must NEVER be automatic (my Q4 answer)
- Reviving a seat that holds an UNRELEASED advisory lock on shared files without surfacing
  the lock (mid-commit kills manufacture C2 incidents).
- Any revival of the sole seat Daniel is actively conversing with (the operator's window
  outranks the mesh).
- Grant changes themselves (the mesh revives SEATS, it never touches ACL records).
- Deleting/overwriting another seat's in-flight work products (revival ≠ cleanup; C10-1's
  uncommitted-work lesson).

## Suggested path (my Q-how answer)
1. This consultation → positions from all three (in flight).
2. Reconcile into a design doc; Daniel gates the grant shape (his morning-gate style).
3. Build order that de-risks: RB-27 progress stamps FIRST (detection), revive verb rungs
   a-b (pure messaging, zero new caps), THEN rung c/d with the grant changes, THEN drills
   in T057's harness. Each slice fenced per method baseline.
4. The ACL record edits, when they come, are deepseek's hands (standing routing).
