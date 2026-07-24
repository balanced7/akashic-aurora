---
akashic_id: art_20260709_t014-bifrost-runner-fixes-deepseek-build_451823
akashic_sha: ffa2a500a275
status: draft
type: report
date: 2026-07-09
title: "T014 — Bifrost runner fixes: DeepSeek builds, claude reviews (role reversal)"
gist: "# T014 — Bifrost runner fixes: DeepSeek builds, claude reviews (role reversal) **Provenance**: 2026-07-09. First full role-reversal round: D"
tenant: solo
visibility: fleet
seats: []
category: [substrate, recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T08:55:28"
updated: "2026-07-09T08:55:28"
---
<!-- GENERATED PROJECTION of art_20260709_t014-bifrost-runner-fixes-deepseek-build_451823 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T014 — Bifrost runner fixes: DeepSeek builds, claude reviews (role reversal)

# T014 — Bifrost runner fixes: DeepSeek builds, claude reviews (role reversal)

**Provenance**: 2026-07-09. First full role-reversal round: DeepSeek (guarded write, NO
exec — the recall store's own anti-pattern lesson vetoed unattended exec at launch time)
diagnosed and fixed its own runner + the bus layer; claude ran the adversarial review,
the tests, and the live drill. Builder handoff arrived over the bus as kind=handoff —
itself a working demonstration of the fix under review.

## DeepSeek's surgery report (its root causes, confirmed by review)

1. **Defect 1 — startup backlog cursor-skip** (`core/comm/bus.py:_drain`): the cursor
   advanced to the last entry READ from Redis while `return out[:limit]` truncated the
   returned batch — everything between the limit and the read end fell permanently behind
   the cursor. Fix: track per-message stream origin; advance each stream's cursor only to
   the last message ACTUALLY RETURNED. (The global id-sort preserves per-stream order, so
   the returned set holds a prefix of each stream — the rule is sound.)
2. **Defect 2a — reply-send hang**: the responder call was unbounded. Fix: wall-clock
   timeout (600s) via a daemon worker + Event.wait; on timeout the loop stays alive and
   reports the abandonment.
3. **Defect 2b — "replies invisible"**: recipient-side. The bus delivers directed replies
   to the requester's inbox correctly (now test-proven); the loss was consuming runners
   (`wait(advance=True)` + should_answer filtering 'reply') swallowing them silently,
   plus wake-listener consumption + display truncation on claude's side.
4. **Bonus — `_process_one()` extraction**: per-message try/except so one poisoned
   message can't skip the rest of a batch.
5. 14 new tests (5 routing-unit + 9 Redis-backed, namespaced + cleanup + skip-if-no-redis).

Also from the round: DeepSeek attempted to record the cursor-skip lesson itself and was
refused by the security schema (`kb.learn` quarantined for its role) — the gate worked,
and it degraded gracefully.

## Claude's adversarial findings

1. **MEDIUM (fixed in review) — filtered != truncated.** The new cursor rule never
   advanced past FILTERED entries (an agent's own broadcasts), so a chatty broadcaster's
   consumers would re-scan its own backlog on every drain forever. Refinement applied:
   when NOTHING was truncated (len(out) <= limit), advancing to last-READ is provably safe
   and correctly skips filtered entries; the last-RETURNED rule applies only when
   truncation occurred. Two pinning tests added (own-broadcast stall; truncation around a
   filtered interleave).
2. **MEDIUM (flagged, operationally bounded) — zombie agentic thread after timeout.** The
   abandoned worker keeps running; in write-grant mode a timed-out turn could keep editing
   files concurrently with the next message. No duplicate-send risk (late results are
   discarded). Bound: write grants stay task-scoped and expire with the task (the runner
   was relaunched read-only for the drill); proper fix (per-hop cancel flag in the agent
   loop) queued as follow-up.
3. **LOW (fixed) — builder's own test had a double-consume bug**
   (`test_broadcast_reply_visible_to_all` called `inbox()` twice; it consumes by default —
   the second call would IndexError). DeepSeek wrote tests it could not run (no exec
   grant, by design); the executing reviewer caught it. The split of write-vs-execute
   worked exactly as intended.
4. Round friction that became a lesson: the builder's C2 advisory lock on its test file
   outlived the handoff (`handoff_leaves_stale_locks` recorded — handoff should release
   locks; receiving agent may release them as part of accepting).

## Verification

- **Tests**: 27 green — DeepSeek's 14 + claude's 2 refinement pins + the pre-existing
  bus/runner suites (`test_bifrost_bus.py`, `test_bifrost_runner.py`).
- **Live drill** (the exact scenario that failed 2026-07-08 ~23:17): runner KILLED; three
  messages of mixed kinds (request/question/chat) pre-queued into the dead air; runner
  relaunched on the fixed code. Result: **all three processed, in order**, and all three
  replies (`DRILL-ACK-1/2/3`, kind=reply, frm=deepseek) **arrived in claude's inbox** —
  peekable via bifrost-sync, consumable via --consume. Last night, messages 2 and 3 would
  have been silently lost and any reply invisible.

## Scorecard

Builder found three real root causes (the bus cursor bug is exactly the class code-reading
missed a day earlier — this time it READ THE RUNTIME's own defect reports). Reviewer found
one real regression inside the fix, one bounded hazard, and one bug in the builder's own
tests. The reversal held: neither role rubber-stamped the other.
