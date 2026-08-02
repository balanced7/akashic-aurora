---
akashic_id: art_20260802_coordination-standing-engagement-sensors_08268c
akashic_sha: 92f8dea98e61
schema_version: 1
status: current
type: report
date: 2026-08-02
title: coordination-standing-engagement-sensors-daniil
gist: "# Coordination redesign: sensors, signatures, standings, engagements Status: current (2026-08-02, claude#30e6af5c). DESIGN FOR FENCED REVIEW"
visibility: fleet
body_type: markdown
seats: []
category: [coordination, method, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T02:57:11"
updated: "2026-08-02T02:57:11"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-standing-engagement-sensors_08268c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-standing-engagement-sensors-daniil

# Coordination redesign: sensors, signatures, standings, engagements

Status: current (2026-08-02, claude#30e6af5c). DESIGN FOR FENCED REVIEW — nothing here is built,
nothing is ratified. Daniil's idea, developed in conversation with claude overnight 2026-08-01/02.
Reviewers: attack it. A confirmed refutation is worth more than an endorsement.

## Provenance and intent

Daniil, verbatim, across the design conversation:

- "the cursor be a container that has fillable fields that are read by both sides, consume needs
  to be changed to something that changes a flag rather than just consume"
- "it is simultaneously the contract, the declaration, the 'where is my attention and current
  action' piece and the communications rules of engagement"
- "agents could establish the expectation for the current set of interactions and both agree to
  move on to the next item after both have concluded work. it can be a 2 round deal, it can be a
  5 round deal"
- "both ai's can negotiate a heads down mode for an agreed amount of turns and then re-sync"
- "the artifact can itself send a warn then a red state if certain criteria get breached"
- "measure the things that move where they move. there are real signal sources we can tap into
  instead of inferring"
- "at the metal readings not inferences"
- "the model itself is either generating, standing by or whatever other states there are, each
  one has a unique signature and we can establish and define what each measurement means and
  what it could mean"

## The diagnosis this rests on

Doctrine already says the bus is for liveness; coordination rides the substrate
(docs/library/design/20260709_multi-agent-coordination-layer-research_ce0d07.md §5.5: "Our
Ledger + Store + Bus IS a blackboard... What we DON'T have: formalized blackboard patterns.
Trigger rules. A control shell."). The bus became load-bearing anyway. Measured cost, one night
(2026-08-01/02): ~4 wake-watcher re-arms on already-handled mail; a live agent declared dead
mid-answer (beat 826s stale while the API stream was flowing); two briefs delivered to dead
seats and reported dispatched; one seat's directed mail made unreachable by a twin advancing a
shared cursor (codex U1 receipt); the same sender-side lane-write bug recurring for the 3rd
time because a straggler net keeps catching it.

Pattern under all of it: every failure is TWO PATHS THAT WERE SUPPOSED TO AGREE and quietly
did not (two lanes, two cursor key shapes, two read paths, four meanings of "done").

## The layers (bottom to top; each reads only the one below)

### Wave 0 — sensor plane: capture at chokepoints, never self-report

Signal taxonomy: self-report (phase fields, heartbeats — a claim the process makes about
itself) < inference (reading artifacts that correlate) < CHOKEPOINT CAPTURE (a tap in a path
the traffic must traverse — complete by construction) < THE METAL (the socket itself).

Concrete taps, v1:
- Runner seats (deepseek/kimi/gemini): wrap the API client our own code owns. Request
  start/end, streaming chunk cadence, token usage off the response. ~20-line bridge.
- Harness seats (claude/codex): (a) the Pre/PostToolUse hooks — already built, every tool call
  traverses them; (b) session-transcript JSONL growth — the harness appends streaming events
  during generation, so file-size delta is composition-time liveness as an OS fact. (Used by
  hand 3x tonight: the runner's output file was the truth while the roster lied.)
- Substrate: Redis key census / lane depths, polled ON READ, rendered with ages.

Rules: sensors are fail-open and never block the path (the hook console-spam saga is the paid
receipt for what happens otherwise); observations only, never verdicts (a stored LIVE is a
future ghost page); meters only, never content. Distinction to keep crisp: bridges are
traversed (complete), pollers sample (gapped) — sampled signals must not masquerade as
complete ones, because absence-as-evidence depends on completeness.

Key epistemic claim, offered for refutation: ABSENCE IS ONLY EVIDENCE WHEN PRESENCE IS
GUARANTEED VISIBLE. All false-dead incidents are coverage holes (composing time is dark), not
threshold problems. F1's own measurement supports this (widening the hook matcher removed
almost no DEAD windows; the gaps were wall-clock).

### Wave 0.5 — signature codebook: states identified by combination, never by one reading

Each real state (composing, tool-running, idle-wakeable, wedged, dead, throttled, heads-down,
plan-wall...) has a distinctive fingerprint ACROSS sensors. Verdicts come only from signatures.
The current system diagnoses from beat-age alone — the row that reads "stale" in 4 of 5 states,
i.e. the least informative measurement on the panel.

- Codebook is a literal committed lookup table (booleans/thresholds), NOT a rules engine.
- Signatures are RECORDED by calibration drills (deliberately put a seat in each state, commit
  what the panel showed, dated), not authored from theory. Re-calibrate on harness/runner
  version change: a signature is an empirical fact about a version.
- A reading matching no known column renders raw as UNRECOGNIZED (unknown-first-class) — it is
  a discovery or a sensor fault, never forced to the nearest state.
- Shared/ambiguous columns are the sensor roadmap: the next sensor to build is the one that
  splits the most expensive ambiguous pair (this mechanically justified the metal tap: it is
  the only row splitting composing from dead).
- Impossible combinations (socket flowing + process absent) diagnose the SENSORS.
- The observers get columns too: "watcher armed" becomes a mechanically readable state (kills
  the blind re-arm ritual).

### Wave 1 — standing: one agent's declared position on one work item

Keyed agent × work. SINGLE WRITER PER FIELD (everyone reads everything; nobody can clobber
anybody — conflicts impossible by construction, no locks/CAS/CRDTs). Fields: state
(sent/seen/claimed/done/failed/expired), seen_by (the watcher's vocabulary — today it has
none, which is the structural cause of the wake loop), claimed_by + claim_expires (the lease;
a crashed claimant's mail must become claimable again — this is load-bearing, not a detail),
answer_id, deadline, plus telemetry: pointer to running incarnation, tool-call count
(MONOTONIC COUNTERS BEAT TIMESTAMPS — a zombie can stamp a heartbeat; it cannot fake a counter
that moves), token spend (convergence signal, not liveness), last-action age. Telemetry is
stamped by the harness/sensor plane at turn boundaries — derived, never authored; an agent
must not be able to be wrong about its own telemetry.

Naming (proposed, at Daniil's gate): CONTRACT = the fixed global grammar; ENGAGEMENT = the
negotiated per-interaction terms; STANDING = one agent's position; BOARD = the readable whole.
Test used: two things share an object only if they share key, writer, and lifetime. "Cursor"
is rejected as a name — it imports position semantics (names-that-lie class).

### Wave 2 — engagement: the negotiated terms of one interaction

The trigger already exists: --expect-reply-within is the moment chat becomes work. Today it
builds a ONE-SIDED timer the receiver cannot see (root cause of false-DEAD redrives). Change:
the same trigger creates a TWO-SIDED artifact. Zero new gestures.

- Typed shapes with fixed structure (v1: the fence only), parameters variable (rounds, members,
  deadline). Declare-and-accept; NO counter-offers in v1 (negotiating terms would need its own
  terms — regress).
- Heads-down is a TERM: N turns of deferred delivery, then a resync gate. Interrupts queue
  into the artifact instead of preempting (interrupt masking with deferred delivery).
  Constraints: operator ALWAYS breaks through (frm=user outranks masking — the "I'm back!"
  incident is the receipt); expiry on wall-clock AND turns; heads-down suppresses interruption
  but NEVER presence (standing keeps beating underneath); the resync gate REQUIRES draining
  the deferred queue (else it is a silent-loss mechanism that looks safe).
- Alerts: conditions come from the engagement's OWN declared bounds, so they are undismissable
  ("you agreed 3 turns; this is turn 6"). warn = lands in the artifact, interrupts nobody;
  red = breaks heads-down, escalates on the existing fidelity ladder. Verdicts computed at
  read time, never stored. v1 = exactly two conditions: turns exceeded; tool-counter still
  for T. No DSL.
- Wake inverts from edge-triggered (watch for the event, miss it forever, re-arm ritual) to
  LEVEL-TRIGGERED (read the board, "is it my turn?") — T095's own words ("level-triggered
  wake"), parked since July.
- Routing: no engagement → plain messages/nudges (cheap chatter is correct for conversation);
  engagement open → state changes via artifact; heads-down → deferred except operator/red.

### What this deletes (each with its expiry condition, per the anti-debt rule)

Dual-write reliance and the straggler net (expire when notifications are allowed to be lossy
because the board is the truth); the redrive/expectation sweep machinery (expire when
deadlines are two-sided fields); most wake-arm logic (expire at level-triggered wake); the
four disagreeing "done" stores (delivered/consumed/settled/acked collapse into standing
fields).

## Prior art already in-house

- The role queue (core/comm/role_queue.py) ALREADY IS this model for role work: claim + fence
  token + commit-refused-if-reclaimed. Most robust code in the comm layer. The proposal is
  "make directed coordination work the way role work already works."
- T095 (parked): "message-state index, claims, level-triggered wake" — same design, Daniil's
  own directive, half-built.
- The netcode arc board: a hand-maintained engagement (muster/brief/barrier phases, terminal
  states, "silence is not terminal") that went stale in six minutes — the manual version of
  exactly this mechanism, demonstrating both the need and the failure mode.
- 2026-07-09 research §5.5–5.6: blackboard match; CRDT rejection (scoped to "two trusted local
  agents" — the pools ambition reopens that premise; single-writer-per-field is the proposed
  cheaper answer).

## v1 scope (deliberately tiny)

One engagement type (fence). Two participants. Explicit join. Declared rounds + wall-clock
deadline + unilateral abandon. Each side marks only its own conclusion; gate is mechanical.
One wrapped client (deepseek runner) + one JSONL-growth poller feeding standing liveness.
Two alert conditions. The stream stays underneath as the append-only record; standings/board
are a projection over ledger events (replay/audit preserved).

## Open risks, named by the authors

(1) Blackboard rot — mitigations: fixed schema, single-writer-per-field, explicit
next-actor policy. (2) Barrier deadlock — every gate carries timeout + breaker (tonight had a
real swallowed-unlock deadlock). (3) Lease-crash mail stranding — claim expiry is v1-mandatory.
(4) Storage growth per-message — eviction (mailbox cap precedent). (5) Signature drift on
harness updates — dated calibrations, re-run on version change. (6) Duplicate-systems risk —
the standing's lease vs runner_lock, the sensor plane vs doctor: seams must be inherited
(T119 liveness self-proof, existing fence pattern), not rebuilt.
