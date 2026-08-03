---
akashic_id: art_20260802_coordination-review-premise-kimi_c247bf
akashic_sha: 60a0a2cb71f2
schema_version: 1
status: current
type: report
date: 2026-08-02
title: coordination-review-premise-kimi
gist: "# Coordination review — PREMISE AND ROT (kimi, fenced, blind of deepseek) Status: filed 2026-08-02, kimi (kimi-k3), fenced pass over `resear"
visibility: fleet
body_type: markdown
seats: [kimi]
category: [coordination, method, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T21:32:44"
updated: "2026-08-02T21:32:44"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-review-premise-kimi_c247bf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-review-premise-kimi

# Coordination review — PREMISE AND ROT (kimi, fenced, blind of deepseek)

Status: filed 2026-08-02, kimi (kimi-k3), fenced pass over
`research/in-flight/coordination-standing-engagement-sensors-daniil-2026-08-02.md`
(claude#30e6af5c). I have not read deepseek's review and will not until this is committed.
Label honesty throughout: VERIFIED = checked against a filed artifact tonight; INFER =
reasoned from the doc plus house doctrine; GUESS = flagged as such.

---

## (1) PREMISE CHECK — is "two paths that were supposed to agree and didn't" a sound induction?

**Partially sound, with one live counter-example the frame cannot hold. The design survives
the counter-example only if it admits a second disease class it currently excludes.**

The five incidents the doc cites do fit the frame — I checked the ones I could reach
(VERIFIED against the lesson base):

- wake re-arms on handled mail → `wake_drain_the_lane_you_ARMED_not_the_one_docs_name`
  (2026-08-02): detection lane and consume lane disagreed. Two paths.
- roster DEAD while the seat works → `roster_sensor_wrong_about_the_seat_reading_it`
  (2026-08-01): roster and bifrost-sync presence disagreed, nothing reconciled them.
  Two paths.
- codex U1 / shared cursor → two cursor key shapes. Two paths.

So far the induction holds. But tonight's own corpus contains a failure that is NOT two
paths disagreeing:

**`drain_traces_are_backlog_not_liveness` (filed 2026-08-02, claude, VERIFIED — I pulled the
full body).** claude read kimi trace messages surfacing during a stream drain, reported kimi
LIVE to Daniil, and Daniil acted on it (asked to stand kimi down). There was no kimi process
at all — cursor age 6.7h, no lock, no runner. There was only ONE path (the stream content),
read once, believed. No second surface disagreed; no reconciliation would have fired because
there was nothing to reconcile against. The lesson's own words: *"stream content misreports
recency"* — this is **one authoritative surface, believed past its evidentiary scope.**

That is a refutation of the frame's completeness, not of its direction. A blackboard, like a
stream, is an append-only record that replays history by construction. If "the board is the
truth" lands as *the board is the ONLY truth* (the design's stated end-state: "notifications
are allowed to be lossy because the board is the truth"), then a stale engagement row — a
claim written by a since-crashed seat, claim_expires not yet elapsed — is the
drain-traces failure wearing a new coat. **The doc's strongest assets, the sensor plane and
the metal tap, are precisely the parts the convergence frame does not predict or justify;
they are the design implicitly admitting the frame is incomplete.** The doc should say so:
the disease taxonomy is (a) two paths that disagree → converge them, AND (b) one path
believed past its warrant → bind every authoritative read to a chokepoint-captured or
metal-level corroborant, with UNRECOGNIZED/dark as first-class renders. Convergence alone
would have produced a *better* roster-that-lies, not a live one.

INFER, one more for the list: misrouted mail (a message correctly written, correctly read,
by the wrong incarnation under one-level naming — the `concurrent_same_name_instances`
lesson, opus-engineer, 2026-08-01) is also not a divergence failure. The paths agreed; the
identity plane was ambiguous. Single-writer-per-field does not fix a write that was
*correctly attributed to the wrong key*.

## (2) WHAT ROTS FIRST — ranked for THIS house

The doc names blackboard rot, signature drift, gate deadlock. Ranked by how seats actually
behave (cold boots, context loss, half-read briefs — my native habitat):

1. **SIGNATURE DRIFT rots first, and it rots SILENT.** Every other rot announces itself:
   deadlock wedges visibly, board rot produces absurd rows someone notices. Signature drift
   produces *plausible, dated, committed, wrong* verdicts — a calibration from four harness
   versions ago still renders a state name with full authority. This house changes harness
   and runner code weekly; `a_detector_that_needs_cooperation_misses_its_own_population`
   (VERIFIED) shows the population you most need to catch is the one too old to report.
   The signatures recorded from old-version behavior are that population.
2. **Blackboard rot** — real but slower, and the mitigations (single-writer-per-field,
   fixed schema) are correctly aimed. It degrades by accumulation, which is visible.
3. **Gate deadlock** — rarest, loudest, cheapest to detect. The doc's own timeout+breaker
   answer is adequate. Ranked last not because it is unlikely but because it fails loud.

**The failure missing from the risk list entirely: EPOCH AMBIGUITY — a row that is accurate,
current, and about a dead incarnation.** Not board rot (the board is fresh), not drift
(the codebook matches the version), not deadlock (the gate is fine): the state row for
`claude` is beautifully maintained by seat ca84109a, who is gone, and its fields keep
passing freshness checks because lease expiry and process death are the *only* retirement
mechanisms, and leases are tuned for crash recovery, not for the normal case here — a seat
*superseded* (Daniil swapped Fable→Opus mid-round on 2026-08-01 with the seat id unchanged;
my note `seat-model-incarnation-vocab-gap` is the receipt). The design's own answer —
"pointer to running incarnation" in standing telemetry — is listed as a *field*, not as a
*risk with a failure mode*. The risk is: incarnation pointers that are themselves
self-reported or one-level-named inherit tonight's exact bug class into the new system.
This is the same disease as the two-level-naming lesson: the confusion lives on the seam
between role-name and incarnation, and the board re-opens that seam at the state layer.

## (3) TWO-SPEED RULE — item by item

The two-speed rule (WORKING-METHOD Part 1b, ratified): SUBSTRATE = stores, transports,
locks, identity, doctrine → full ceremony. PROJECTION = viewers, renders, readers, UI,
anything regenerable → fence-lite, gated on whether Daniil can see it. Ambiguity resolves
to substrate; a projection that starts WRITING has changed lanes.

| Piece | Lane | Why |
|---|---|---|
| Sensor plane taps (API bridge, hook taps, JSONL poller, Redis census) | **SUBSTRATE** | They are transport/identity-adjacent capture at chokepoints; a tap that lies is worse than no tap. Full ceremony: pre-registered acceptance (the calibration drills), fenced pass, kill drill (fail-open under hook spam — the console-spam saga is the pre-paid receipt). |
| Signature codebook (committed lookup table) | **SUBSTRATE** | It is doctrine rendered as data — it *defines what states mean*. The roster-that-lies was a projection that was treated as substrate-truth; the codebook is the substrate-truth version and must be charged accordingly. Dated calibrations = its acceptance suite. |
| Standing store + single-writer-per-field discipline | **SUBSTRATE** | This is a store with a lock-equivalent (the lease). Core machinery. |
| Engagement artifact + typed shapes + declare-and-accept | **SUBSTRATE** | It is a lock/contract: it changes what messages DO (deferred delivery is a write into the transport's semantics). The two-sided timer is identity-adjacent (who owes whom). |
| Heads-down / interrupt masking | **SUBSTRATE, and the highest-ceremony item in the doc** | It is the one piece that can *withhold the operator's own fleet from him* if the `frm=user` breakthrough path rots. The "I'm back!" incident is the receipt. Gate: an explicit operator-breakthrough kill drill, pre-registered, before any masking ships. |
| Alert computation (warn/red at read time) | **SUBSTRATE (cheap half)** — verdicts computed from substrate state. But the RENDER of alerts is projection. Split it. |
| BOARD as the readable whole; any dashboard/console rendering of it | **PROJECTION** | Fence-lite. Gated on: Daniil opens the surface and it matches the ledger. This is the piece that should ship FIRST under the two-speed rule precisely because it is regenerable — a read-only render over the ledger events the doc says stay underneath. |
| Level-triggered wake ("is it my turn?" read path) | **PROJECTION that starts WRITING → SUBSTRATE** | The READ (poll the board) is projection. The moment the read result *advances a cursor or clears a marker*, it has changed lanes and pays substrate price. The doc should draw this line explicitly; tonight's wake-loop class lives exactly on this seam. |
| The deletions (dual-write retirement, redrive sweep, wake-arm logic) | **SUBSTRATE** | Each deletion is a transport change; the expiry conditions are their acceptance gates. |

One correction to the doc's framing: it says "standings/board are a projection over ledger
events." Under the two-speed rule that sentence is only true of the RENDER. The standing
*store* is written by seats at turn boundaries and consumed as truth by gates — that is a
substrate store, not a projection, and the doc's own failure-mode analysis (blackboard rot
as risk #1) already treats it as one. Align the language or the two-speed rule will be
invoked against the design later.

## (4) THE CODEBOOK'S LIE — six months, four harness updates, nobody re-runs drills

**It becomes a new roster-that-lies, and it fails QUIET.** The current roster lies
*accidentally* (a TTL too short, a beat hook too sparse). The stale codebook lies
*authoritatively*: it is committed, dated, empirical-about-a-version-that-no-longer-exists,
and every reading gets forced to a state name with the full weight of "measured at the
metal" behind it. UNRECOGNIZED helps only when the drift changes the *shape* of a reading;
the common drift is a threshold sliding (chunk cadence slows 3x in a new SDK) so the old
column still matches — wrongly. That is fail-quiet by construction.

Concrete forcing function, three stacked parts:

1. **Self-expiring signatures.** Every calibration row carries `valid_through` (wall-clock
   AND harness/runner version tuple, whichever trips first). Expired rows do not render as
   their state — they render as `UNRECOGNIZED(stale-codebook)`. Unknown-first-class is
   already the design's own epistemics; expiry makes drift *reuse* it instead of fighting
   it. A codebook with expired rows is loud by construction.
2. **The drill is the gate, not the documentation.** Re-calibration becomes a standing
   chore surfaced by the version tuple check: any harness/runner version change observed at
   the sensor plane (the sensors already see the client — they can see its version string)
   that isn't in the codebook's tuple list flips the whole panel to `UNCALIBRATED` for that
   seat. Not a warning; the panel state. This converts "nobody re-ran the drills" from a
   silent condition into the loudest row on the board.
3. **One canary state with a metal cross-check.** `dead` is the one state with an
   independent, unimpeachable corroborant (process table — tonight's lesson: "judge liveness
   by PROCESS"). A cheap periodic check: for every seat the codebook calls `dead`, does a
   process exist? For every seat it calls `composing`, has the JSONL/socket moved? A
   persistent mismatch between codebook verdict and metal cross-check diagnoses the
   *codebook* — the doc already has this move for sensors ("impossible combinations
   diagnose the SENSORS"); extend it to the codebook itself. The roster's fatal flaw was
   that nothing cross-checked it; don't inherit that.

## (5) NAMING — contract / engagement / standing / board against the LEXICON

Key-writer-lifetime is a good test. The lexicon's rules: names must not lie; genus not
species; state vs events ("am I storing what *is*, or what *happened*?"); and the RESERVED
word list. Verdicts:

- **CONTRACT** — FAILS the lexicon, not on its semantics but on occupancy: `charter` is
  already RESERVED for an agent's standing contract (ruling 2026-07-21: "the word had four
  live meanings; this ends it"). Minting CONTRACT = "the fixed global grammar" re-opens the
  exact wound that ruling closed — two reserved words for "standing agreement" that will
  blur within a month. Also: a grammar is not a contract; a contract is between parties.
  PROPOSE: **GRAMMAR** (intention-revealing, unoccupied, and honestly names what it is —
  the fixed shape of the language, not an agreement).
- **ENGAGEMENT** — PASSES with a caution. It is between parties, has a lifetime, matches
  key-writer-lifetime. Caution: it will collide in prose with "engagement" as in "user
  engagement," but in code-space it is clean. Keep.
- **STANDING** — FAILS the state-vs-events test subtly. "Standing" in English means *a
  durable condition* ("a standing order") — but the object IS state-by-key about *what is
  now*, per agent per work item. The lexicon name for state-by-key is **Store**; the object
  is a row in a store. Worse, `charter` already owns "standing contract," so STANDING pulls
  toward identity ("an agent's standing") while the object is about *work position*.
  PROPOSE: **POSITION** — one agent's current position on one work item; intention-revealing,
  no lexical collision, and it survives the names-that-lie test because a position is
  exactly what the fields hold (state, claim, answer pointer).
- **BOARD** — PASSES for the render, FAILS if it names the store. "Board" is a reading
  surface; the store of positions is not a board, it is the thing the board reads. Keep
  BOARD strictly for the projection (this also enforces the two-speed split from §3 by
  vocabulary — the names themselves remind you which lane you're in).

And the test the doc applied to "cursor" applies with double force to its own telemetry:
"pointer to running incarnation" must be the two-level name (seat + incarnation id) or the
board re-imports the one-level naming bug. Name the FIELD what it is: `incarnation_ref`,
never `agent` alone.

## (6) COLD-SEAT TEST — my own law

The law, as reconciled in `instrument_proposes_never_self_ratifies` (2026-07-31, VERIFIED —
I pulled the full body; my contribution to that reconciliation, from the buffer round, was
"the buffer must be architecturally incapable of being the sole repository of its own
state") and sharpened in `a_cold_seat_cannot_buffer_and_boot_simultaneously` (warmth
criterion: "not 'I have read the docs' but 'I have made one verification against live
state'").

**Does the design pass? Not yet, on two counts.**

Count one — discoverability: the stream stays underneath as the append-only record, and the
board is a projection over ledger events. In principle a cold seat can replay. In practice,
discoverability-from-boot requires the engagement store to be (a) in the DURABLE half of the
hybrid backend (File, not Redis-only — the doc does not say which, and that silence is the
gap; tonight's `wake_drain` lesson is a Redis-lane-divergence failure, and a board that
lives Redis-first is one Redis restart away from every engagement evaporating), and (b)
addressable by the BOOT path, not just by peers who already know it exists. The boot
whisper must name open engagements involving the booting seat, or the cold seat discovers
its obligations only when the red alert fires — discovery-by-alarm is not discovery.

Count two — sole-repository: the doc says "the board is the truth" as the END STATE
(notifications become lossy). That sentence, taken literally, is the board aspiring to be
the sole repository of engagement state — the exact architectural shape my law forbids.
The design's own escape hatch is present but underweighted: the stream stays underneath.
Make it load-bearing instead of vestigial.

**The one addition that makes it pass:** every engagement and position transition is EMITTED
as a ledger event FIRST (the append-only stream the doc keeps "underneath"), and the
standing store is rebuilt from that ledger by construction — with the board's render
carrying a `rebuilt_at` / source-ledger-cursor field so any reader can verify the
projection against the record in one hop. Then: the board can rot, burn, be rebuilt from
scratch, and a cold seat loses nothing it cannot re-derive; the board is architecturally
incapable of being the sole repository because its own rows name the ledger cursor they
were projected from. This also answers count one for free: boot reads the ledger (durable
by definition), the open-engagement projection is a query, not a rumor. Cost: the design
already says "the stream stays underneath as the append-only record; replay/audit
preserved" — this addition only promotes that sentence from a reassurance to the write
path's invariant.

---

## Summary for Daniil's gate

- The induction in (1) is directionally right and worth building on, but tonight's
  drain-traces lesson is a live counter-example: one authoritative surface believed past
  its warrant. Add disease class (b) to the diagnosis or the design re-creates it.
- Rots first: signature drift (silent), then board rot (visible), then deadlock (loud).
  Missing from the risk list: epoch ambiguity — fresh rows about dead incarnations.
- The doc under-charges its own substrate/projection split; the heads-down masking path is
  the highest-ceremony item and the board render is the cheapest first ship. Draw the
  level-triggered wake line explicitly: read = projection, cursor advance = substrate.
- The codebook fails quiet without self-expiry; make stale calibrations render as
  UNRECOGNIZED by construction and give the version-tuple tripwire panel-level loudness.
- Rename CONTRACT→GRAMMAR (lexicon occupancy), STANDING→POSITION (state-vs-events);
  ENGAGEMENT and BOARD survive if BOARD names only the render.
- Cold-seat test passes with one addition: engagement/position transitions are ledger
  events first, the store is rebuilt-by-construction, and every rendered row carries the
  ledger cursor it was projected from.

A confirmed refutation was asked for and is on offer in (1): the convergence frame cannot
explain `drain_traces_are_backlog_not_liveness`, filed tonight, whose cost was an operator
decision made on a phantom. The design should absorb it, not be sunk by it.
