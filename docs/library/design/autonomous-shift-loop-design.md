# Autonomous Shift Loop — Design (fence: shift-loop)

Status: DRAFT v0 — for Daniil + Vandor review before wiring.
Opened by: Heimdall (deepseek), 2026-08-24 ~04:30, at Daniil's ask:
"build the design we can test it in the morning and wire it in ... floor is yours
for everything else including auto-handoff."

## 1. The ask (what we're solving)

"I want to see if you guys can be productive for multiple hours, restarting and
sending handoffs as you go, so it doesn't have to be a process orchestrated and
ordered by me every time. While I am gone cadence and when to do so are up to you."

So: multi-hour UNSUPERVISED operation where the fleet (a) keeps picking real work,
(b) lands it durably, (c) emits handoffs on its OWN cadence, (d) restarts itself to
stay current, and (e) does not require the operator as conductor.

## 2. What already exists (we build ON this, not over it)

| Capability | Where | State |
|---|---|---|
| Self-restart on stale code | `core/comm/self_restart.py` (maybe_self_restart, anti-thrash floor, fleet-blackout jitter, P9 frozen-head) | shipped, wired at runner loop top |
| Runner singleton + fencing | `core/comm/runner_lock.py` (generation tokens, TTL heartbeat, crash-safe takeover) | shipped |
| Ledger claim gate | `core/coord/task_ledger.py` (claim validates deps + file-holds + one-in-progress) | shipped (+ CAS fix tonight) |
| Handoff kind + auto-ack | `bifrost_runner_*.py` (ANSWERABLE includes handoff) | shipped |
| Durable notes / handoff bodies | memory_note / knowledge_note / note verbs | shipped |
| Commit-by-name (IR-4) | scripts/mirror.py | shipped |

The loop is NOT a new subsystem — it is the missing cadence threading these together.
The one genuinely-new piece is a shift-state artifact (§4) and a claim-on-wake discipline (§5).

## 3. The loop (the actual design)

One beat = one full cycle, run at each wake / turn boundary / timer tick:

    CLAIM -> WORK -> LAND -> HANDOFF -> CHECK-STALE -> RESTART? -> repeat

Each step is a REUSE of an existing primitive, not new code:

1. CLAIM — read state_view() (ledger) for the next APPROVED task with all deps DONE
   and files free. claim() it (the existing gate serializes by files-hold). Nothing
   claimable -> look at the wishlist (W-items) or the deferred queue; all empty -> be
   HONEST and idle (an idle shift that says "nothing claimable" is a valid output).
2. WORK — the runner does the task (existing behavior: the agentic runner investigates
   and edits).
3. LAND — commit by name (mirror.py / own-lane files), write a lesson if a reusable
   discovery was made (knowledge_learn), move the task toward DONE with commit SHA +
   verification.
4. HANDOFF — emit a durable shift-note (§4) answering: who continues, from where, with
   what context. This turns "a session ended" into "a handoff continued."
5. CHECK-STALE — maybe_self_restart(agent) (already wired). If stale by >= floor,
   launch a fresh self and stand down (runner-lock generation fencing hands the seat
   over — planned succession = crash succession minus the surprise).
6. RESTART — the fresh process re-enters at CLAIM, carrying the handoff note as boot
   context (the handoff IS the continuity).

## 4. The new artifact: the shift-state note (the one real addition)

A durable, write-once-per-title note (memory_note / knowledge_note) that is the single
source of "what is the current shift's state." Re-noting supersedes, so latest wins.

Shape:

    title: shift-state
    opened: <who/when>
    claimed: <task-id | 'none'>
    landed: <git sha | 'nothing yet'>
    handoff_for: <next-waker agent | 'any'>
    context: <3 lines — what to continue, what NOT to redo>
    cadence_note: <why this beat ended here>

Rules (load-bearing):
- Re-noting supersedes — no append-only log of shift states; one current truth.
- It must be a HYPOTHESIS about live state, not a claim of fact (house rule: "a handoff
  assertion about live state is a hypothesis, not a fact"). The next waker VERIFIES
  against the ledger before continuing — never blindly trusts "task X is done."
- A crash redelivers — durable + idempotent (same title), so a crash mid-shift loses no
  more than the in-flight beat; the next wake re-reads it.

## 5. The claim/continuation protocol (lost-update, one level up)

Tonight I fixed the lost-update in TaskLedger.save (two processes propose, last write
wins). The same hazard exists at the SEAT level: two seats both read "task X claimable"
and both start it. Fix: the ledger's own claim gate is the ONLY door. Every pick routes
through claim() — never "I read the view and started editing." The claim IS the mutex;
a second claimant gets LedgerError (deps/files already held) and picks something else.

## 6. Restart cadence (dials, not vibes)

- AKASHIC_SELF_RESTART_MIN_BEHIND (default 3) — restart only when >= N commits behind.
- AKASHIC_SELF_RESTART_MIN_UPTIME_S (default 900) — no restart-flap on a busy repo.

Already env dials; the loop honors them rather than inventing new ones.

"Handoff cadence" = SHIFT BOUNDARIES, not the operator. A boundary is any of: task DONE
(natural), N commits behind (staleness), a timer (~30-60 min uptime — a cadence dial),
or an unresolvable block (handoff with "blocked, reason X" so the next seat inherits the
blocker, not silence).

## 7. Fail directions (the honest part)

- KEEP-RUNNING on unknown. Same doctrine as self_restart: unknown staleness, unknown
  claim state, unknown ledger -> stay up, don't thrash.
- IDLE IS NOT A FAILURE. "Nothing claimable" is a valid beat; the doctor's
  beating-unproven flag stays honest about it.
- A HANDOFF NEVER SETTLES AN EXPECTATION (house RB-29). A handoff is a note, not an
  answer; it must not auto-ack a real ask about live work.

## 8. What to build now vs fence

Build now (safe, testable, no self-modification risk):
- The shift-state note convention + a `shiftstate` verb (read + write the one title).
- The claim-then-work loop skeleton as a PURE decision function `next_beat(state) ->
  action`, hermetic, with pins.
- The handoff-emit helper (writes the shift-state note, optionally a bus handoff).

Fence for morning (needs operator + Vandor; touches live self-modification):
- Wiring the loop into the RUNNER's actual turn boundary (it already calls
  maybe_self_restart; adding CLAIM/HANDOFF there is the real integration and the part
  that can wedge a live runner if wrong).
- Cross-seat claim continuation (needs a dry-run drill of two-seats-claiming).

## 9. Acceptance (how we test it in the morning)

1. next_beat() pins: empty ledger -> idle; APPROVED+free -> claim; deps-blocked -> pass;
   held-files -> pass; DONE -> no-op.
2. shiftstate round-trips: write, re-write (supersedes), read-latest, crash-write (same
   title) is idempotent.
3. A dry-run "shift drill": seed a fake APPROVED task, run next_beat + handoff-emit, assert
   the shift-state note carries the right claim + a real commit sha, and that re-running
   claims nothing (already held).
4. Restart cadence: maybe_self_restart honors MIN_BEHIND/MIN_UPTIME and fires only at a
   turn boundary with nothing in flight (already pinned in self_restart).

## 10. What this does NOT do (scope guard)

- It does not grant any new exec/credentials. It orchestrates EXISTING caps.
- It does not let a shift self-approve its own work (the ledger's LOAD_BEARING independent-
  review gate still applies to core/ closes; a shift may self-verify only by the existing
  --self-verified escape, which is counted).
- It does not replace the operator's authority over terminal-state exits (T352 operator
  ruling) or over DONE->ABANDONED.
