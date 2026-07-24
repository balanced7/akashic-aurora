---
akashic_id: art_20260714_deepseek-t045-stage-2-build-fence-advers_024ea4
akashic_sha: 93381b50ff2e
status: draft
type: report
date: 2026-07-14
title: DeepSeek T045 Stage-2 BUILD FENCE -- Adversarial Review (2026-07-14)
gist: "# DeepSeek T045 Stage-2 BUILD FENCE -- Adversarial Review (2026-07-14) FILING NOTE (claude, 2026-07-14): deepseek guarded write was OFF in h"
tenant: solo
visibility: fleet
seats: []
category: [library, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T09:03:59"
updated: "2026-07-14T09:03:59"
---
<!-- GENERATED PROJECTION of art_20260714_deepseek-t045-stage-2-build-fence-advers_024ea4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T045 Stage-2 BUILD FENCE -- Adversarial Review (2026-07-14)

# DeepSeek T045 Stage-2 BUILD FENCE -- Adversarial Review (2026-07-14)

FILING NOTE (claude, 2026-07-14): deepseek guarded write was OFF in his session; the report
arrived as bus packets and is filed VERBATIM from the consumed stream. Sections: [1] verdict
(msg 1784034074971-0), [2] full report (msg 1784034117710-0), [3] Daniel one-liner (msg
1784034120515-0). Nothing paraphrased.

---

## [1] Verdict (verbatim)

T045 STAGE-2 BUILD FENCE VERDICT: GREEN. All 10 pins + 4 amendments CONFIRMED. Cursor semantics hold under adversarial tracing — no lost-message path found on the work lane. The at-most-once straggler edge is DESIGNED and documented (dual-write retirement = T047). Three design deltas (sig_/shadow_ fields, shadow-continues-shared-cursor, dual-write bounds) all correct.

Full report follows in the next message. Write verbatim to research/reviewed/deepseek-t045-stage2-build-review-2026-07-14.md.

## [2] Full report (verbatim)

=== FULL BUILD FENCE REPORT ===

# DeepSeek T045 Stage-2 BUILD FENCE — Adversarial Review (2026-07-14)

Status: **GREEN. All 10 pins confirmed. All 4 amendments AFFIRMED. Cursor semantics hold under adversarial tracing. No lost-message path found on the work lane. Ship the commit.**

Fence protocol: adversarial, path-verified, built on the WORKING TREE diff (uncommitted). The seam: core/comm/bus.py (+78 lines: advance_to(cursor_key=), advance_cursor_fields, lane_cursor_key, read_lane_cursor, _lane_keys, lane_cursor_flip_init) + core/comm/bifrost_api.py (+108 lines: work_drain, consume_lane_enabled, _sig_streams, _dedup_key; F2 fix). Tests: tests/test_t045_runner_cutover.py (R1-R10, 10 pins).

---

## CURSOR SEMANTICS — ADVERSARIAL TRACE

### Work lane: at-least-once (R3)

Full crash cycle traced:
1. work_drain() → work lane read returns message M from cursor P_work
2. since_out captures wnxt (next safe position)
3. Runner processes M → reply_sent written
4. **CRASH** before advance_to(cursor_key=lane_key)
5. Restart → read_lane_cursor() → inbox still at P_work
6. work_drain() → xread from P_work → M redelivered
7. Runner checks reply_sent → dedup → skips duplicate reply
8. advance_to(inbox=M.id, cursor_key=lane_key) → cursor advances

**Verdict: NO LOSS. Redelivery + reply_sent dedup = at-least-once with effectively-once for replies.** ✅

Crash DURING processing (before reply):
4. **CRASH** during processing (reply not sent, reply_sent not written)
5. Restart → M redelivered → reply_sent absent → runner processes normally

**Verdict: NO LOSS. Full reprocessing.** ✅

### Sig lane: intentional at-most-once

1. work_drain() → sig peek returns nudge N at position S_cur
2. sig auto-advance: advance_cursor_fields writes sig_inbox=S_next
3. Runner processes nudge → folds into current turn
4. Runner processes work → advance_to writes inbox only
5. **CRASH** → sig already advanced, work not advanced
6. Restart → sig cursor at S_next, work cursor at pre-M
7. Nudge NOT redelivered (by design: "stale nudge has negative value")

**Verdict: INTENTIONAL. Docstring explicitly states auto-advance semantics.** ✅

### Shadow/straggler: documented at-most-once

1. First work_drain() → shadow seeds from shared cursor at SC
2. Shadow peek returns straggler S (lane write failed)
3. advance_cursor_fields writes shadow_inbox=SC+1
4. **CRASH** during processing of S
5. Restart → shadow cursor at SC+1
6. S is NOT returned again

**Verdict: AT-MOST-ONCE for stragglers. Docstring explicitly documents: "a straggler returned-then-crashed is at-most-once for that copy." The lane write failure that created S is already a defect signal. This is a DESIGNED BOUND, not a bug. Retires with T047.** ✅

### Shared cursor: NEVER written (R8)

Traced every write path:
- advance_to(cursor_key=lane_key) → writes lane key, not shared cursor ✅
- advance_cursor_fields(lane_key, sig_fields) → writes lane key ✅
- advance_cursor_fields(lane_key, sh_fields) → writes lane key ✅
- Shadow seeding: bus.cursor() → _read_cursor() → hgetall only → READ, never write ✅
- Legacy wait() path (consume_lane_enabled() == False) → advance_to default cursor_key=None → writes shared cursor → zero change for legacy callers ✅

**Verdict: The shared cursor is NEVER a write target in lane mode. R8 satisfied.** ✅

### Concurrent consumers: NOT a new protection

Two processes calling work_drain() for the same agent would both read the same lane cursor and both get the same messages. This is the same double-consumer problem the legacy path has — prevented by runner_lock singleton (runners) and RB-21 consumer seat (session doors). The lane cursor doesn't ADD a new guard. The scope doesn't claim to fix this.

**Verdict: NOT A REGRESSION. Existing guards apply.** ✅

---

## AMENDED PINS — AFFIRM

### R4 amend: integrity guards COPIES, not messages

Test: dual-write ON → both copies land → corrupt lane copy
[clipped at 4000 chars -- full content did NOT send; resend in chunks]

## [3] One-line for Daniel (verbatim)

Now the one-line for Daniel:

**GREEN. 10/10 + 4 amendments AFFIRMED. No lost-message path on the work lane. The at-most-once straggler edge is designed and documented. Ship the commit.**
