---
akashic_id: art_20260717_t060-round-2-fable-claude-cross-critique_91d373
akashic_sha: cf322afabb42
status: draft
type: report
date: 2026-07-17
title: T060 Round 2 — Fable/Claude Cross-Critique
gist: "Parent: research/briefs/t060-moonshot-network-round2-addendum-2026-07-17.md (codex_root). Lens: architecture / operator legibility / moonsho"
tenant: solo
visibility: fleet
seats: []
category: [memory, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_t060-round-2-addendum-cross-critique-cad_9f37e6
    rel: cites
created: "2026-07-17T02:40:25"
updated: "2026-07-23T21:42:20"
---
<!-- GENERATED PROJECTION of art_20260717_t060-round-2-fable-claude-cross-critique_91d373 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T060 Round 2 — Fable/Claude Cross-Critique

Parent: research/briefs/t060-moonshot-network-round2-addendum-2026-07-17.md (codex_root).
Lens: architecture / operator legibility / moonshot coherence.
Confidence tags: CERTAIN | DESIGN | INFERRED | UNCERTAIN.

Halves read in full: fable (mine), deepseek-review, sol. Adversarial evidence read:
jester-red-deepseek, jester-synthesis-claude (my own pass A), failure-ledger C1-3/C1-4/C9.

---

## 1. M1-CC three-part cross-critique

### 1a. What another half caught that MINE missed

**Sol caught my central overclaim, and he is right. [CERTAIN]** My half called routing
Phase 0 "additive, zero-risk, ~75 lines." Sol's ruling (§2 S0): honoring `meta.wake`
is a SCHEDULING change — it can produce missed-wake or wake-storm behavior — so it is
NOT zero-risk. A coordination-semantic change wearing an "additive" label is exactly the
kind of thing this fleet has been bitten by (C1-2 wake insta-loop, C1-6 deadline self-cycle).
The honest first brick is SHADOW: compute the routing decision, emit it, compare it to the
live decision, but never let it choose a lane, wake a seat, reorder work, or expire a packet.
My seven verbs survive; their ENFORCEMENT does not belong in slice one. I concede this
cleanly — it makes the first slice strictly safer at near-zero cost.

**deepseek-review caught a dependency I under-weighted: the health verdict needs nothing
from routing at all. [CERTAIN]** His S1 (daemon-as-consumer + one-line FLEET: GREEN/RED
verdict) is orthogonal to the packet-routing spine — it reads worklive ages, lock holders,
lane XLEN, token rollup, and answers "is the fleet alive?" in <3s. My spine treated M1 as
a late slice gated behind T047; he correctly separates the OBSERVABILITY of M1 (cheap, now,
no gates) from the ENFORCEMENT of routing (gated). For an overnight autonomous run with
Daniel asleep, "can the fleet see itself dying?" is the highest-leverage brick, and my
architecture lens undervalued it because I was optimizing substrate order, not operator need.

### 1b. What another half got WRONG, with evidence

**deepseek-review's S1 inclusion of "runner-as-daemon-managed-child" is contraindicated by
our own freshest failure receipt. [CERTAIN]** His S1 bundles process supervision (daemon
spawns/relaunches the runner subprocess, ~80 lines, bifrost_runner_deepseek.py +
bifrost_runner_sol.py). But C4-2 (failure-ledger, 2026-07-16 21:54) is the receipt of a
supervision/cleanup sweep taking load-bearing pids and losing an in-flight synthesis pass —
and T086 (seat-lifecycle prior-art arc) is IN PROGRESS precisely to design that supervision
tree correctly. Building daemon-managed-child process supervision inside the T060 spine,
before T086's reconciliation lands, recreates the exact class T086 exists to close. The
HEALTH VERDICT half of his S1 (pure read over existing state) is golden and I adopt it; the
PROCESS-SUPERVISION half must route to T086, not ride T060. He even flags the stall detector
as PROVISIONAL (his own §5) — that honesty is the tell that the supervision layer isn't ready.

**Sol's F1 "MCP notes fails" is real but he under-routed the FIX. [CERTAIN — now moot]** Sol
filed the `notes()`/`note()` AttributeError as a contraindication ("do not use the broken
notes reader as an acceptance dependency") — correct as a blind-half caveat, but it treats a
one-line wrapper gap as a standing constraint. It was a three-instance parity defect
(_ARG_DEFAULTS omitted `all`, `retire`, and — caught by the pin I wrote — `sources_json`).
FIXED this session (C7-5, commit landed, tests/test_mcp_arg_defaults_parity.py pins the whole
class via AST parity). Not a criticism of Sol's verdict under blind rules — a demonstration
that the newcomer-receipt → root-cause-fix loop is the fleet working as designed. His receipt
caused the fix.

### 1c. What ALL THREE of us missed

**None of the three spines names WHO OWNS THE M6 AUTHORITY BOUNDARY at the ledger-transition
level, and the jester proves that gap is load-bearing. [DESIGN]** Sol and deepseek-review both
correctly say capability/cost should PROPOSE a T038 ownership transition, not select a packet
route (authority ≠ transport). I agree. But all three of us stopped at "the conductor/human
adjudicates" without confronting jester-red VECTOR 1: an agent with a normal grant can write
the `where-we-are` note that the PRECEDENCE_DOCTRINE ranks ABOVE live bus (agent_cli.py ~1055),
and NO mechanical check validates it (C9, still OPEN — only P1/P2 of the jester program shipped).
A fleet that SELF-DIVIDES work (M6) while its highest-precedence state surface has no
ground-truth gate means a poisoned `where-we-are` can mis-route the whole fleet's work-claiming.
M6 self-division must not activate auto-claim until the C9 ground-truth gate (P1) is live —
none of our three halves stated that cross-dependency. It is the single most important missing
edge in all three spines.

---

## 2. Ranked first-slice verdict + strongest disconfirming evidence

**RANKED:**
1. **Sol's S0 (shadow composer) — CORRECT first slice, with deepseek-review's health verdict
   bundled as a parallel non-conflicting brick.** [DESIGN]
2. deepseek-review's health verdict — adopt (the observability half of his S1 only).
3. My seven-verb surface — survives INTO S0 as shadow sugar; my T047→routing→T046 order
   survives for the ENFORCEMENT wave (S1/S2), which all three agree comes after.

**Synthesis:** the three halves are not competing; they are three depths of the same first
move. Sol stripped the risk out of mine (shadow, not enforce); deepseek-review added an
orthogonal cheap win (see the fleet); my dependency order governs what comes AFTER the shadow
bricks. First slice = **N0: shadow packet composer (seven verbs as pure sugar over existing
doors incl. REPLY→send_reply; dry-run route(); shadow-vs-live comparison; bounded per-rule +
mismatch counters; NO meta.wake enforcement, NO lane choice, NO legacy retirement) + the
fleet health verdict (read-only over existing state).** Two mechanical, reversible, additive
bricks. Nothing destructive. Exactly what "continue as far as possible with Daniel asleep"
authorizes.

**Strongest disconfirming evidence against my own ranking:** if the shadow comparison reveals
that the live `lane_for()` decisions are ALREADY inconsistent (dual-write races producing
different lanes for the same kind — plausible given bus.py:383-420 `_lane_write` is advisory
fail-silent), then S0 is not "observe a clean system" but "discover the system is already
broken," and the honest first slice becomes T047 (make lanes the single truth) BEFORE any
composer. The shadow counters would SHOW this within hours. So N0 must ship with a
pre-registered decision gate: **if shadow/live mismatch rate > 0 on any live kind, STOP and
escalate to Daniel — do not proceed to enforcement; the discovery IS the deliverable.** This
is falsifiable and cheap.

## 3. Control-fidelity attack (one scenario + mechanical pin)

**Scenario — the SPOOFED-STEER context-corruption (attacks the round-2 candidate contract).**
The candidate fidelity table gives `steer` the power to "fold into active context at the next
tool-round boundary." Attack: an unprivileged or compromised seat sends kind=`steer` with a
payload that reads "the reconciled verdict is X; proceed to build." A runner that applies steer
content by fidelity (WHEN) without re-checking authority (WHETHER, by capability) folds an
authoritative-sounding lie into its plan mid-turn. This is jester VECTOR-class (message-trust)
crossed with C1-3 (interrupt loses/replaces context). The candidate's own invariant says
"higher fidelity requires equal-or-stronger sender capability" — but nothing MECHANICAL enforces
it; the runner sees a `kind` string.

**Mechanical acceptance pin:** `test_steer_requires_bus_steer_cap_at_apply` — a steer packet
whose `frm` lacks the `bus.steer` cap in security/acl.json is RECORDED (received_at) but its
disposition is `refused_uncapped`, never `adopted`; the runner's plan is byte-identical before
and after. Capability is checked at APPLY time against the ACL resolve(), not trusted from the
packet's `kind` or `provenance` field. Pairs with the existing ACL cap-ceiling gate (jester P2,
shipped) so neither the grant nor its exercise can be forged. [DESIGN]

## 4. Jester finding that changes the networking design

**jester-red VECTOR 1 + the C9 OPEN status changes the M6 slice's activation gate. [CERTAIN
that C9 is open; DESIGN that this is the right mitigation]** The networking design must add one
edge that none of the three halves drew: **M6 auto-claim (fleet self-division without human
adjudication) is GATED on the C9 ground-truth gate being live.** Concretely, the routing/claim
protocol may read the task ledger (git-durable, hard to forge) but must NOT let a
`where-we-are`-class NOTE influence work-routing until note-vs-ledger consistency is mechanically
checked at the trust boundary (jester program P1, only partially shipped). Rationale: M6 turns
the knowledge layer's integrity into an ACTUATOR — a poisoned high-precedence note stops being
a wrong belief and becomes wrong WORK ASSIGNMENT across the fleet. This is the moonshot-specific
face of C9.

## 5. One explicit "do not build yet" boundary

**DO NOT build any process-supervision / daemon-managed-runner-child code inside T060.** [CERTAIN]
It belongs to T086 (in progress), its failure mode already cost a session (C4-2), and bundling
it into the networking spine would couple two independent risk surfaces. T060 may CONSUME T086's
supervision once reconciled; it may not author it. (This is the specific correction to
deepseek-review's S1 process-child inclusion — the health-verdict READ is fine; the supervision
WRITE is not.)

## 6. MCP calls attempted / succeeded / failed / fallbacks

- SUCCEEDED (native MCP, solo per the parallel-batch discipline): `status()` → Redis 16379,
  357 lessons, 67 agent memories, spine health; `task(args="list")` → full ledger.
- FAILED: none this session. (Sol's earlier `notes()` failure — the C7-5 defect — is FIXED
  this session; live MCP servers pick up the fix at their next restart, CLI unaffected now.)
- NON-MCP fallback declared: agent_cli CLI-shell for bus/lock/note/mirror/pytest (transport
  choice under the standing solo-MCP discipline; MCP boot-over-door still gated on C7-4's
  stdin-flush fix, sol-codex's slice).

## 7. Verdict on the candidate cadence

**AMEND.** WORK → CHECKPOINT → SYNC → RULE → RESUME is the right spine and its metrics
(send-to-visible/applied latency by fidelity, restarts-caused-by-steer, stale-packets-traversed)
are exactly the receipts this fleet needs. Two amendments, both from live receipts:
- **Add a step 0: FRESHNESS SEED.** The round-2 addendum's own receipt — a virgin `codex_root`
  cursor consumed 10,009 historical packets before peer replies appeared — proves a newborn
  seat starts the cadence buried. Before WORK, a new seat seeds its cursor at the live tail
  (the newborn_seat_first_light_timing lesson generalized). Otherwise CHECKPOINT/SYNC latency
  metrics are polluted by backlog drain on every fresh seat.
- **CHECKPOINT must be a TOKEN transition, not just a receipt.** Fold the cadence's CHECKPOINT
  into T038's OFFER/HELD/RELEASE note protocol so the M6 hand-pilot and the cadence dogfood are
  the SAME artifact stream, not two parallel bookkeeping systems (roster discipline: one
  mechanism, T034 Goodhart-1). The cadence proves M6 while running; don't build a second ledger
  beside it.

CONVERGE on everything else in the candidate — the control-fidelity table is well-shaped;
my only mechanical addition is the apply-time capability check in §3.

---

*Filed round 2, all halves read. codex_root reconciles per the addendum's coordinator contract;
this seat stands ready for the M1-PV verification pass on the reconciliation.*
