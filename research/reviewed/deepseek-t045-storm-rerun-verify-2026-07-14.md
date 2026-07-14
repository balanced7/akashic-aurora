# DeepSeek T045 Storm Rerun Verify — cfdcb65f (2026-07-14)

Status: **GREEN** — all bars hold; the storm-gap find (R11 newborn split) is correctly fixed;
four amendments are faithful sharpenings. T045 completion bar is met.

Tier: FENCE-LITE (single-blind adversarial review; charter from research/rb25-t045-rerun-verify-brief-2026-07-14.md)
Evidence: research/reviewed/rb25-drill3-evidence-cfdcb65f.json (812 lines), burst logs, ledger, test suite

---

## BARS

### S1 — No unacked loss (PASS, CERTAIN)
`requests_sent=29, send_side_lost=0, answered=29, unaccounted=[]`.
Every sent request has an answer. The ledger is a superset of the answers — loss rate is
zero under the trace flood. The 29/29 includes all corpse-directed requests (messages
012-019 were addressed to runner B which was killed mid-burst; the successor caught and
answered them — verified in successor.out: storm-8a4d414e2a81-request-044 etc.).

### S2 — No phantom wake under flood (PASS, CERTAIN)
`watcher1_detected=false, watcher2_detected=false`. Both watchers survived the flood
without a single wake. This is the structural bar: lane-mode watchers on the work lane
do not spuriously wake under trace flood. S2-NEW (no phantom wake on the lane seat
itself) is implicit in the S2 pass — the watchers are lane consumers.

### S3 — Cursor-passes-the-corpse (SUBSTANCE PASS, CERTAIN)
The self-read artifact is correctly documented: `corpse_cursor` and `successor_cursor`
are both legacy-keyed `{inbox:"0", bc:"0"}` — the shared cursors. Lane-mode runners
never advance these (pin R8, verified: `test_r8_shared_cursor_never_written_in_lane_mode`).
This is NOT a defect — it's the strangler pattern working as designed; the shared cursor
is a legacy read-only surface.

**Substance evidence:** `t045.lane_cursor_b` shows progression from virgin (`inbox:"0"`)
to `inbox:"1784035834556-0"` — the successor drained 44 messages through the lane cursor.
All 29 sent requests received answers. The session-consume leg passed (44 consumed via
lane seat). The corpse's mail was delivered through the lane, not the legacy shared cursor.

**Ruling:** S3 `pass=false` is a MECHANICAL reading against legacy-keyed metrics —
the self-read correctly flags its own irrelevance. The substance (lane cursor progression +
29/29 delivery) passes. CERTAIN.

### S4 — Single consumer (PASS, CERTAIN)
`dupe_exit=3, refused=true`. The duplicate-runner guard fired (pid 40340 already live;
refused to start a second runner). Exactly one consumer per agent. CERTAIN.

### S5 — Duplicate discipline (PASS, CERTAIN)
`handoff_reply_counts`: both handoffs (036, 037) have exactly 1 reply each. No duplicate
replies. The RB-26 reply_sent dedup sentinel is in effect. CERTAIN.

### S6 — HALT/sig latency under flood (PASS, CERTAIN)
`latency_s: 0.05`, `sig_beat_final_work: true`. The nudge probe (d3s6-cfdcb65f) round-tripped
in 0.05 seconds — well within the ≤10s M8 bound. The sig arrived BEFORE the final work
packet (`sig_beat_final_work: true`), confirming P3 ordering is preserved under flood.
This is the bar that gate-keeps HALT: the lane MUST route a control signal with bounded
latency even when work is flooding. CERTAIN.

### SESSION-LEG (PASS, CERTAIN)
`consumed_count=44, seat_held_by_other=false, pass=true`. The session door consumed 44
messages from the lane seat. The lane cursor after consume: `shadow_bc:"1784035833598-0"`
seeded at tails (newborn split in effect), `inbox:"0"` for directed per RB-26 sanctity.
Seat was free (no other holder). CERTAIN.

---

## ARTIFACTS

### (a) S3 self-read artifact
**RULING: documented correctly, substance passes.** The legacy-keyed cursor/pending
metrics are pin R8 working as designed (shared cursor never touched in lane mode).
The lane-substance evidence (lane_cursor_b progression, 29/29 delivery, session_leg
consumed=44) confirms the corpse's mail moved through the lane. No message was lost
to the legacy/metric mismatch. CERTAIN.

### (b) S1 answered=29, unconsumed_at_end=29
**RULING: valid, not a contradiction.** All 29 sent requests received answers AND all
29 remain unconsumed in the legacy streams — because the ANSWERS are on the lane reply
path (runner replies go to the sender's inbox via the bus, not to the legacy work streams).
The legacy work streams retain the original requests (unconsumed because no lane consumer
advances the shared cursor — R8 again). The `unaccounted: []` proves no request lacked
an answer. Dual-write preserves the legacy stream as a superset of the lane stream;
accounting is valid. CERTAIN.

---

## NEWBORN SPLIT (R11)

The `lane_cursor_flip_init` in `core/comm/bus.py` (lines 720-737 per diff) splits
newborn seeding: DIRECTED positions stay "0" (RB-26 sanctity — addressed mail delivers
even pre-onboarding); BROADCAST positions seed at tails via `self.tail()` (RB-25 F2
discipline — 44 broadcast replays caught live in the storm are now prevented).

The `work_drain` onboarding seed in `core/comm/bifrost_api.py` (lines 258-269 per diff)
handles the virgin-cursor case at drain time: `lane_cursor_flip_init()` is called once
per API instance, and the `_lane_seeded` flag prevents re-execution.

**RULING: holds as designed.** The split is principled (directed = sanctity, bc = tails),
the onboarding seed is bounded (once-per-instance), and the fallback belt in the straggler
net (lines 309-313 per diff) handles failed/raced seeds by continuing the shared cursor's
story. Pin R11 test (`test_r11_newborn_shadow_seeds_at_tails_no_history_replay`) is
correctly specified: 6 ancient broadcasts sent before newborn first drain → first drain
returns empty, post-seed mail flows. CERTAIN.

---

## AMENDMENTS (R2, R7, R10a)

### R2 — Established-consumer sharpening (AFFIRM)
Original: lane write failure falls back to legacy. Amendment pre-establishes the consumer
(one drain + advance) before the failure injection, because the newborn path now skips
history via R11. The sharpened test exercises the ESTABLISHED consumer's straggler net,
which is the real subject. Faithful sharpen, not a bar-weakening. CERTAIN.

### R7 — Established-consumer gap test (AFFIRM)
Original: lane-only mail drains without dual-write. Amendment pre-establishes the consumer
(same reason as R2 — newborn now skips pre-onboarding traffic by R11 doctrine), then
creates a lane-only gap by deleting the legacy copies. The revived consumer drains from
the durable lane cursor alone. Faithful sharpen — the bar (durable cursor catch) is
identical, the precondition is now correct. CERTAIN.

### R10a — Migrant precondition (AFFIRM)
Original: seed-at-tail via flip ritual. Amendment adds explicit shared-cursor advance
before the flip (`advance_to(inbox="1-1", bc="1-1")`) to establish a MIGRANT (not a
newborn, which now takes the R11 path). The amendment also adds explicit assertions:
flip_init returns True (first call), False (idempotent), and pre-flip history is soak.
Faithful sharpen — clarifies the migrant-vs-newborn boundary that R11 made explicit.
CERTAIN.

### R11 — New pin (AFFIRM)
New pin exercising the newborn shadow-seed-at-tails contract. 6 ancient broadcasts →
first drain empty → post-seed mail flows. Correctly isolates the storm-gap find.
CERTAIN.

---

## VERDICT

All bars (S1-S6, SESSION-LEG) pass on the evidence. The S3 self-read artifact is
correctly documented and its substance passes via lane-cursor progression. The S1
double-count is valid (answers on reply path ≠ unconsumed requests on work path).
The newborn split (R11) is principled and correctly implemented. All four amendments
(R2, R7, R10a, R11) are faithful sharpenings, not bar-weakenings.

**T045 → DONE. T046 unlocks.**
