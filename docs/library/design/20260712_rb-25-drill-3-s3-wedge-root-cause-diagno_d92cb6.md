---
akashic_id: art_20260712_rb-25-drill-3-s3-wedge-root-cause-diagno_d92cb6
akashic_sha: 338f4b2efc90
status: draft
type: design
date: 2026-07-12
title: "RB-25 drill 3 \"S3 wedge\" -- root-cause diagnosis (claude BLIND half), 2026-07-12"
gist: "# RB-25 drill 3 \"S3 wedge\" -- root-cause diagnosis (claude BLIND half), 2026-07-12 Fenced dual diagnosis, claude half. Written before deepse"
tenant: solo
visibility: fleet
seats: []
category: [method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_rb-25-drill-3-concurrency-storm-claude-e_d3e126
    rel: cites
created: "2026-07-12T17:18:28"
updated: "2026-07-23T21:42:09"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-drill-3-s3-wedge-root-cause-diagno_d92cb6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-25 drill 3 "S3 wedge" -- root-cause diagnosis (claude BLIND half), 2026-07-12

# RB-25 drill 3 "S3 wedge" -- root-cause diagnosis (claude BLIND half), 2026-07-12

Fenced dual diagnosis, claude half. Written before deepseek's independent half. CORRECTS the S3
finding in research/reviewed/claude-rb25-drill3-execution-2026-07-12.md. Daniel-directed
(blind-diagnose + propose fix; deepseek cross-checks when back online).

## Retraction

My execution record claimed: *"a non-virgin runner started against a backlog consumes nothing --
a successor cannot drain the corpse."* **That is WRONG.** A fresh runner drains a dead runner's
backlog cleanly. The successor-recovery mechanism WORKS.

## True root cause (evidence, not inference)

During the storm burst, runner A's reply **RateLimiter** (`control.RateLimiter()`, wired at
bifrost_runner_deepseek.py:733) tripped and set a **GLOBAL pause**:

```
bifrost:control:paused = {"reason":"d3a-d9b54722 hit reply rate limit","by":"d3a-d9b54722",
                          "ts":"2026-07-12T13:32:33"}   ttl ~2400s
```

From that instant every runner's loop hit the top-of-loop gate `if control.is_halted(args.agent):`
(bifrost_runner_deepseek.py:770) -> `register + sleep(0.4) + continue`, SILENTLY, forever. Measured
`is_halted(...) == True` for `d3a`, `d3b`, AND a fresh-random id, in BOTH the drill and the live
`bifrost` namespace. So:
- runner A answered ~20, tripped its own limit, then froze;
- runner B's successor never consumed (frozen);
- my post-storm probe (10 min later) never consumed (pause still within TTL);
- the S1 "tail" (9 in A + 16 in B) is exactly the mail that arrived after the pause tripped.

**Confirmation (decisive):** cleared the pause (`control.resume()`), then started a fresh runner
against the still-intact 16-message `d3b` backlog. It drained to **0 in ~2s** (consume+echo lines
for request-044, chat-047, request-050, and the earlier nudge). `is_halted` was False throughout.
The wedge is 100% the global pause; there is NO backlog-drain bug.

Why my earlier direct `bus.wait()` probe "worked" while the runner didn't: `wait()` bypasses the
`is_halted` gate. The runner freezes BEFORE `wait()`; a raw `wait()` call never sees the gate.

## Findings (corrected)

**F1 -- drill-invalidating.** The storm's own burst (~20 msg/s, ~24 echo replies) trips the reply
RateLimiter, which the runaway-loop guard escalates to a GLOBAL pause. This froze the fleet
mid-drill, so **S3 and S5 were never actually exercised** (the successor and the handoff replies
were paused, not tested). S1/S2/S4 still stand (below).

**F2 -- isolation defect (drill can freeze production).** `control.PAUSE_KEY`, `HALT_PREFIX`,
`NARRATION_KEY` are hardcoded to `NS = "bifrost"` (control.py:33-36), ignoring `BIFROST_NAMESPACE`.
So a DRILL runner tripping the limit paused the LIVE bus -- I had to clear it. The drill's
stream/presence/cursor isolation does NOT extend to the control plane. **A drill can freeze the
real fleet.** This is independent of F1 and worth its own fix regardless.

**F3 -- design tension (for deepseek's half; the deep one).** The runaway-loop guard
(reply-rate -> GLOBAL pause) is anti-correlated with concurrency-storm recovery: a legitimate burst
of work looks like a runaway loop, trips the guard, and pauses the very successor whose job is
recovery. Global pause is the wrong blast radius for one agent's rate trip.

## Proposed fixes (claude half -- deepseek cross-checks)

**Fix A (F2, high-value, low-risk, do first). -- LANDED (claude half; deepseek review pending).**
Namespace-scope the control plane: `_pause_key()`/`_halt_prefix()`/`_narration_key()`/
`_activity_prefix()` now derive from `os.environ.get("BIFROST_NAMESPACE", "bifrost")` (read per-call),
exactly like `Bus.ns`. A drill pause stays in `rb25drill3` and can never touch production. Default
`bifrost` behavior preserved (no external importers of the old constants; verified). Test:
`tests/test_control_namespace_isolation.py` -- 3 pins (key-names follow ns; pause in ns A doesn't
pause ns B; is_halted respects ns for both global pause and per-agent halt), all green; killwindow
drill regression 6/6. deepseek: please cross-check `core/comm/control.py` before this is considered
sealed.

**Fix B (F1, drill-enabling).** Exempt `AKASHIC_DRILL_ECHO` runners from the reply RateLimiter (same
escape pattern as F1/F2 quarantine + seed-at-tail already use). The echo responder is deterministic
and offline -- it cannot meaningfully "run away," and the drill's whole purpose is to burst. Without
this, the storm can never test its own second half. (Fix A alone is NOT enough -- a namespaced pause
still freezes the drill fleet mid-storm; B is what lets the burst complete.)

**Fix C (harness, mine).** `rb25_drill3_orchestrate.py` must assert `control.is_paused() == False`
at start and re-check after the burst; if a pause is set mid-run, mark the run **INVALID** loudly
instead of silently emitting S3/S5 reads. A drill that can be silently frozen must detect it. I will
land this in the harness now.

## Design question for deepseek's independent half

Given F3: should the runaway-loop guard **quarantine the offending agent** (a per-agent halt via
`HALT_PREFIX`, the machinery already exists) instead of a **global pause**? And how should it tell a
legitimate burst from a real runaway -- reply-fanout to DISTINCT peers vs a reply-storm to ONE
sender, or a self-referential hop chain (the MAX_HOPS guard already covers that latter case)? Your
call decides whether Fix B is "exempt the drill" or "narrow the guard's blast radius for everyone."

## Impact on drill 3 grades

**VALID RE-RUN (storm 4ddf0a71, 2026-07-12): ALL FIVE BARS PASS.** With the drill-local rate-limit
raise (the Fix B form, in the orchestrator's child env so the deterministic echo burst no longer
trips the runaway guard) and Fix A ensuring the drill touches only its own control plane, the storm
finally exercised recovery end-to-end. Evidence: research/reviewed/rb25-drill3-evidence-4ddf0a71.json
(`paused_during_burst=False` -> the read is valid, not a frozen fleet).

- S1 no-unacked-loss: **PASS** -- 29 requests, 0 lost, **29 answered, 0 unconsumed, 0 unaccounted**.
- S2 no-phantom-wake: **PASS** -- both twin watchers stayed blocked through the trace/steer flood.
- S3 cursor-passes-the-corpse: **PASS** -- successor acquired a fresh seat (pid differs, lock cleared)
  and its cursor ADVANCED past the corpse's (inbox ...028362 -> ...031679): it drained the dead
  runner's backlog. Direct refutation of my retracted "wedge" claim.
- S4 single-consumer: **PASS** -- dup-id runner refused at the lock.
- S5 duplicate-discipline: **PASS** -- both redelivered handoffs answered EXACTLY once.

Live `bifrost:control:paused` stayed `None` throughout (Fix A holding). Drill 3 execution is COMPLETE
and clean; **deepseek's independent verify is the remaining gate** (fence). F3 (production
runaway-guard redesign: quarantine vs global pause) stays open as its OWN item -- it is NOT a drill
blocker. Engine-first still holds: T029 also needs **drill 4 (72h soak)**, which needs Daniel's
soak-gating ruling, before it certifies and the packet-substrate BUILD opens.
