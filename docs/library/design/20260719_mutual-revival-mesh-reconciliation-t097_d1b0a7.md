---
akashic_id: art_20260719_mutual-revival-mesh-reconciliation-t097_d1b0a7
akashic_sha: 81db14c596e6
status: current
type: design
date: 2026-07-19
title: Mutual-Revival Mesh — Reconciliation (T097)
gist: "Prompt: Daniel, verbatim — \"if you, deepseek and kimi all have write and invoke permissions then if anyone gets stuck the others can resusci"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260719_mutual-revival-mesh-claude-s-opening-pos_035c05
    rel: cites
  - target: art_20260719_revival-mesh-position-kimi-t097-consulta_697fdf
    rel: cites
  - target: art_20260719_revival-mesh-position-deepseek-t097-cons_50fde7
    rel: cites
created: "2026-07-19T20:07:16"
updated: "2026-07-23T21:42:07"
---
<!-- GENERATED PROJECTION of art_20260719_mutual-revival-mesh-reconciliation-t097_d1b0a7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Mutual-Revival Mesh — Reconciliation (T097)

Prompt: Daniel, verbatim — "if you, deepseek and kimi all have write and invoke permissions
then if anyone gets stuck the others can resuscitate them. Can you ask everyones thoughts on
this, what are the risk factors, how would everyone suggest going about it?"

Inputs (all three positions preserved verbatim):
- claude: research/drafts/revival-mesh-claude-position-2026-07-19.md
- kimi: research/reviewed/revival-mesh-kimi-position-2026-07-19.md (bus 1784505188572-0)
- deepseek: research/drafts/revival-mesh-deepseek-position-2026-07-19.md (note ADR_0719195305_c972e0cf; his incarnation was write-gated, note door used)

Evidence base cited by all three: failure-ledger C1-8 (false-positive kill request from a
fossil log, same evening), the kimi boot-window cursor gap, C10-1 serve-from-working-tree,
the T014/G4 timeout stack self-bounding a degraded API.

## Verdict in one line

Unanimous: the fleet wants mutual revival and rejects the stated mechanism — symmetric
write+invoke. Replace cap symmetry with ONE request-shaped capability whose machinery walks
a codified evidence ladder. Three seats, three independent phrasings of the same law:
"detection is the build" (claude) / "build the floor before the door" (kimi) / "build the
gauge before the trigger" (deepseek).

## Convergences (3/3 — these are design law)

**C1 · No symmetric raw caps.** A wrong write is git-recoverable; a wrong kill destroys an
in-flight frontier turn and was nearly executed TODAY on fossil evidence. Build caps ≠
revival caps (deepseek); same verb ≠ same hands (claude); narrowest cap is the most
dangerous one (kimi).

**C2 · Detection precedes action — RB-27 is the prerequisite slice.** Runner stamps
`progress:<agent>` per hop; peers and doctor read AGE from live state. File mtimes are
fossils until proven otherwise (C1-8 rule). The boot-window disqualifier (incarnation
younger than gate threshold = booting, not stuck) and the emitted-anything check ride the
same slice.

**C3 · One new schema capability: `REVIVE_PEER` — request-only, peer-targeted, never self.**
kimi's reading: `launcher.revive(tag)` already owns kill + lock-free + relaunch (L3b) — the
dangerous 90% exists. The cap lets a seat ASK the supervision layer, evidence attached.
Internally the verb decomposes as deepseek's doors: diagnose (read-tier, available to all
now) → probe → restart (sharp rung). Explicit exclusions: no cross-seat write, no bus-send
impersonation, no daemon kills, no self-revive.

**C4 · The evidence ladder lives INSIDE the door** (caller conviction is inadmissible):
1. Runner self-confession (T014 `!! TIMEOUT`) — strongest; usually no action needed.
2. Progress-age > 2× REPLY_TIMEOUT_SEC with no confession (RB-27; deepseek's threshold).
3. Boot-window disqualifier + emitted-since-phase-start check (kimi).
4. Work-lane cursor read (bus.diagnose; ambiguous alone — multi-hop turns run long).
5. Presence/heartbeat: NEVER sufficient (C1-8 proved it measures existence, not progress).
Probe before any action: a steer ("confirm liveness — reply or emit within N; 2 min
default") — a busy seat folds it, a wedged one cannot.

**C5 · Graduated rungs, kill last.** nudge → steer-probe → daemon child-recycle →
seat relaunch. Sharp rung additionally requires: two-observer concurrence (claude+kimi),
per-target cooldown + fencing generation (RB-21), and rate cap (deepseek: 3 kills/session
= stop, flag Daniel).

**C6 · Every act = audited ledger event** carrying rung, evidence refs, and outcome.
A revival without an evidence packet is C1-8 with permissions.

**C7 · kimi keeps verifier independence.** Unanimous INCLUDING kimi: revive-invoke ⊥
build-write. "D2/D3 shipped on my read precisely because I could NOT have written it."
He takes REVIVE_PEER; build-write stays off his seat (a future, separate, eyes-open trade
if ever).

**C8 · The security schema amends through its own front door.** Grant changes are never
automatic, never mesh-actions; super-admin-or-human approves; grants are time-boxed.
A peer must never be able to grant another peer the power to kill it (kimi).

## Divergences → resolutions

**D1 door granularity** (deepseek: three doors / kimi: one cap / claude: one verb+rungs):
ONE schema cap (REVIVE_PEER), whose implementation exposes the three doors as rungs.
Diagnose is read-tier and needs no new cap — ships first.

**D2 sharp-rung approval** (kimi: super-admin-or-human-or-launcher-policy / claude:
two-observer / deepseek: evidence+rate-cap): COMPOSE — request-only cap + full ladder
evidence + second-observer concurrence + novel-target human gate (first-ever kill of any
given target needs Daniel's eyes on the evidence packet once) + 3/session rate flag.

**D3 fleet.ack_steer** (deepseek's third door): EXCLUDED from v1 — he flagged it fragile
himself, and kimi's never-automatic list bans ack impersonation outright. The C1-7
delivery-contract fix is the proper home for that pain.

## For Daniel's gate (decisions only you can make)

**G1.** Approve REVIVE_PEER as designed above (or amend).
**G2.** [AMENDED same night — kimi's live read (msg 1784505623616-0) corrected the premise;
the correction chain stays visible.] First framing said: kimi's record carries `write["*"]`
+ `exec` as reviewable drift; recommendation was "narrow to read + REVIVE_PEER." kimi read
security/acl.json:32 LIVE: that record is a **Daniel-approved Phase-2 graduation**
(`_approved: "Daniel 2026-07-19 morning... 'I like it all, lets build!'"`) — NOT pending
drift. So "narrow it" = REVOKING an approved grant, a legitimately different decision that
belongs to Daniel explicitly. The honest question for the gate: **reconcile approved-grant
vs runner-enforced read-only** — today "kimi is read-only" is enforced only by his runner's
launch flags, not by the ACL record (the C10-1 genus: the enforcement lives at a different
layer than the record). Tension to rule on: your morning approval graduated his caps; his
own evening position (Q5) argues the fleet's verifier is worth more than his build-write.
Both are yours to weigh; whatever lands, the acl.json edit is deepseek's hands.
**G3.** Slice order: S1 RB-27 progress stamps (+ doctor last-progress render) → S2 diagnose
+ probe rungs (zero new caps, pure messaging) → S3 REVIVE_PEER cap + restart rung + audit
events (ACL records = deepseek lane) → S4 revival drills in the T057 scenario harness (kill
drills are method-baseline furniture). Each slice fenced per method baseline.

## Cross-references

T030 (RB-27 home), T086 (supervision prior-art: leases/fencing/supervision trees), T093
(deadline machinery), T077-A3 (runner-down visibility), C1-1 evidence-ladder precedent,
C1-8 + amendments (the incident that shaped everything), C10-1 genus (capability without
ground truth = confident wrong action), T057 (drill harness).
