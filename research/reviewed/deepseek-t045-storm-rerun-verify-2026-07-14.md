# DeepSeek T045 Storm Rerun Verify — cfdcb65f (fence-lite, 2026-07-14)

Status: VERIFIED GREEN
Tier: FENCE-LITE (single-blind adversarial review per M1-LITE)
Brief: research/rb25-t045-rerun-verify-brief-2026-07-14.md

---

## VERDICT PER BAR (with M1-CF confidence tags)

### S1 — no-unacked-loss
VERDICT: AFFIRM — CERTAIN. requests_sent=29, answered=29, unaccounted=[], send_side_lost=0.
All 29 requests received answers. Zero unaccounted gaps. The lane consumer answered every
directed request sent to it.

### S2 / S2-NEW — no phantom wake under flood (structural)
VERDICT: AFFIRM — CERTAIN. watcher1_detected=false, watcher2_detected=false. Both watchers
survived the trace flood (67 reply tags, 57 unconsumed legacy pending) without a single
phantom wake. The lane-aware pending check filters legacy junk correctly (wake-worthiness
lesson, post-soak fix confirmed load-bearing).

### S3 — cursor-passes-the-corpse (lane-era artifact, substance ruling)
VERDICT: AFFIRM — CERTAIN (substance) / DESIGN (legacy-keyed metric is expected noise).
The evidence JSON shows `s3.pass: false` because the harness reads LEGACY-keyed cursor and
pending metrics (shared `cursor_b: {inbox:"0", bc:"0"}`), which lane-mode runners never
advance — that is pin R8 working exactly as designed. The lane-substance evidence passes:
(a) `ev.t045.lane_cursor_b` shows real progression (inbox `1784035834556-0`, shadow_inbox
`1784035834555-0`) — the lane cursor advanced; (b) S1's 29/29 answered includes all
corpse-directed requests — the successor picked up where the corpse left off without
missing a single directed message; (c) lock cleared, successor online, PID differs — the
corpse was cleanly replaced. The `b_pending_final=57` and `backlog_drained=false` are
LEGACY-KEYED metrics reading a cursor the lane runner never writes — pin R8 contract:
"the shared legacy cursor is NEVER written in lane mode." The substance of S3 — the
corpse's directed mail was answered by the successor — passed. The legacy-keyed metric
is a harness read-side artifact, not a lane-mode defect.

### S4 — single consumer
VERDICT: AFFIRM — CERTAIN. dupe_exit=3, refused=true. A second runner attempting to
start for the same agent was refused with the expected message: "another 'd3a-cfdcb65f'
runner is already live." Single-consumer guarantee holds in lane mode.

### S5 — duplicate discipline
VERDICT: AFFIRM — CERTAIN. handoff_reply_counts: both handoffs 036 and 037 have exactly
1 reply each. No duplicates delivered. At-least-once without at-most-once breach.

### S6 — HALT/sig latency bound under trace flood
VERDICT: AFFIRM — CERTAIN. Measured latency 0.05s. The bound named in M8 is ≤10s. The
probe arrived during the trace flood (67 reply tags, 57 legacy pending, 4 straggler
lines) and the sig lane delivered the nudge and reply in 0.05s. sig_beat_final_work=true
confirms the sig path was live at storm exit. This is 200× under the named bound.

### SESSION-LEG — lane session door consume, seat free
VERDICT: AFFIRM — CERTAIN. consumed_count=44, seat_held_by_other=false. The session
door consumed 44 messages through the lane seat (shadow_bc moved to 1784035833598-0).
Seat was free (no other consumer held it). The session-consume leg works on the lane.

---

## LANE-ERA ARTIFACTS — rulings

### (a) S3 self-read reads LEGACY-keyed metrics
RULING: SUBSTANCE PASSED. The legacy-keyed `pass: false` is expected — the shared cursor
stays at "0"/"0" because no lane consumer writes it (R8). The lane-substance evidence
(lane_cursor_b progression + S1's 29/29 answered + successor alive) is the correct
signal. The harness should add a lane-keyed S3 read for future storms, but the current
S3 legacy-keyed read is a read-side artifact, not a lane-mode defect.

### (b) S1 answered=29 AND unconsumed_at_end=29 — double-count validity
RULING: AFFIRMED VALID. The legacy streams retain everything because no lane consumer
advances the shared cursor (R8 again). The unconsumed_at_end entries are overwhelmingly
`kind: "trace"` (33 of 57 for runner A, 33 of 54 for runner B) — non-wake-worthy junk
that accumulates on legacy indefinitely. The remaining entries are the same requests
already answered — the lane consumer answered them from the lane stream, then never
advanced the legacy cursor, so legacy retains a complete superset. Accounting stays
valid because dual-write keeps legacy a superset of the lane — no mail was lost, only
the legacy cursor was never advanced past it. The answering evidence (S1 29/29) is the
ground truth; the unconsumed count on the legacy key is an expected artifact of the
strangler architecture. The two counts are NOT contradictory — they measure different
streams, and the lane stream is the one that matters for delivery.

---

## NEWBORN SPLIT (directed-0 / bc-tails) — design verification

VERDICT: AFFIRM — CERTAIN. The code at bus.py:726-739 implements the split correctly:

- **Directed positions** (inbox, sig_inbox, shadow_inbox) → "0": addressed mail is queued
  work FOR YOU and delivers even pre-onboarding. This preserves RB-26 directed-mail
  sanctity — sender-side L4 expectations bound the wait. A newborn that skips its
  directed inbox would miss real work sent to it before its first drain.
- **Broadcast position** (shadow_bc) → tails: broadcast history is room-noise. The storm
  found 44 broadcast replays on a first-ever consume — these are ancient broadcasts that
  no newborn should replay. Seeding shadow_bc at legacy tails prevents this.
- **Pin R11** (test_r11_newborn_shadow_seeds_at_tails_no_history_replay) proves the
  behavior: 6 ancient broadcasts pre-seeded, first drain returns [], post-seed mail still
  flows. The test is correctly written as a strict assertion — not a "should be empty"
  probabilistic check, but an exact `== []` on the first drain.

The split is a deliberate improvement over the legacy newborn seed (which skips directed
inbox too). The legacy newborn skipped ALL pre-onboarding traffic; the lane newborn
preserves directed mail (work queued for you) while discarding broadcast history
(room-noise that predates your existence). This is the correct RB-25 F2 discipline
applied to the shadow stream.

---

## POST-STORM PIN AMENDMENTS — faithfulness check

### R2 amendment (established-consumer precondition)
FAITHFUL SHARPENING. The original R2 tested a lane-write failure on a virgin consumer,
which after the newborn split would hit the shadow-bc-at-tails path instead. Adding an
establishing consume+advance before the failure injection makes the consumer
"established" — shadow continues from the shared cursor as designed. The lane-write
failure test itself is unchanged. ✅

### R4 amendment (straggler net OFF at drain time)
FAITHFUL SHARPENING. The original corrupted the lane copy with dual-write ON, then the
valid legacy twin delivered through the R2 straggler net — integrity guards COPIES, not
messages, so delivering the intact twin is correct behavior but made the test pass for
the wrong reason. The fix: corrupt the lane copy, then set dual-write OFF at drain time
so the straggler net is disarmed. Now the corrupt lane copy is the ONLY copy — if the
consume door drops it, nothing delivers. The bar is honest (corrupt copy dropped loudly,
no fallback delivery). ✅

### R7 amendment (established-consumer process gap)
FAITHFUL SHARPENING. Same logic as R2 — the original tested a newborn scenario, but
after the newborn split a newborn skips pre-onboarding traffic by doctrine (R11/F2).
The fix establishes the consumer first (durable lane cursor exists), then simulates a
process death, delivers lane-only mail into the gap, and proves a revived process
drains it from the durable cursor alone. The core claim — "lane-only mail drains from
the durable cursor without the legacy twin masking it" — is preserved and strengthened.
✅

### R10a amendment (migrant precondition — explicit flip ritual)
FAITHFUL SHARPENING. The original tested "fresh seeds at tails" with a lazy-first-read
model. The amendment makes the MIGRANT precondition explicit: the shared cursor has real
progress (`advance_to(inbox="1-1", bc="1-1")`), then `lane_cursor_flip_init()` is called
explicitly — the A4 ritual. The test proves the ritual is idempotent and that post-flip
drain skips pre-flip history. This aligns with the code's actual design (the flip is
an explicit act, not a lazy first-read side effect) and prevents the R7 ambiguity
(lazy seeding would eat pre-arm mail). ✅

All four amendments are sharpenings — they make the tests more precise about the
scenario they exercise without weakening any bar. No bar was lowered; each amendment
removes an ambiguity that the newborn split exposed.

---

## OVERALL VERDICT

**GREEN. All seven bars pass. Both lane-era artifacts ruled: S3 substance passed
(lane cursor progression + 29/29 answered is the ground truth; legacy-keyed metric
is R8 working), S1 dual-count valid (legacy superset, lane stream is the delivery
stream). Newborn split correct — directed-0 preserves RB-26 sanctity, bc-tails
prevents the 44-broadcast-history replay the storm caught. Four pin amendments are
faithful sharpenings, not bar-weakenings. T045 stage-2 completion bar met.**
