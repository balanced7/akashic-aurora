# T060-M1 Continuous Presence — claude half — 2026-07-15

Status: COUNTER-DESIGN (NOT blind — see disclosure). Fence: t060-m1-design.

## ⚠ Independence disclosure (recorded before writing, note t060-m1-fence-integrity)

While diagnosing deepseek's runner failure I read his trace log, which contained his
in-progress M1 reasoning: a supervisor daemon, peer contracts with restart policy,
three harness tiers, strangler-over-launcher, "the launcher is UI-bound" as the named
gap, and state-continuity-via-bus. I have NOT read his filed design document. Where
this half concurs with those seen fragments I mark **[CONCURS-EXPOSED]** — the
reconciliation must not count those as blind convergence. Everything unmarked is my
own line of reasoning, but the reader should weigh even that with the exposure known.

## 1. Ground truth — lifecycles as they ran TONIGHT (live receipts, not just reading)

| Component | Spawned by | Watched by | Restarted by | Tonight's receipt |
|---|---|---|---|---|
| deepseek runner (`scripts/bifrost_runner_deepseek.py`) | a human/claude shell, manually | runner_lock TTL 20s (`core/comm/runner_lock.py:39`) + doctor pages | NOBODY — died with the previous session, hand-relaunched twice tonight (02:15, 02:21) | fleet-relaunch ritual in `where-we-are` |
| bifrost_wake listener (`scripts/bifrost_wake.py`) | the SESSION it serves, on stop-hook demand (`scripts/hooks/claude_stop.py:220-226`) | wake_seat janitor (`core/comm/wake_seat.py:219`) | the stop hook BLOCKS the model until it re-arms — a human-in-the-loop restart policy | my own listener armed 02:13, fired on mail 02:44, re-armed at next stop |
| claude session | Daniel | consumer-seat TTL 1800s (`runner_lock.py:44`) | Daniel | predecessor's final stop-hook refresh left a 30-min seat SHADOW that blocked this successor (cleared via `clear_if_pid(claude, 47516)`) |
| Bifrost UI (+ its launcher w/ auto-revive) | manual | itself (UI process) | manual | down at 02:15, relaunched by hand |
| incarnation cards (`core/comm/incarnation.py`, NEW tonight) | SessionStart hook | TTL 30m, refresh at stop | self-healing on refresh (R12) | live card w/ ledger claims published 02:59 |

The pattern in one sentence: **every presence artifact we have is born correctly and
dies badly** — nothing above the OS owns the "bring it back" half of the contract,
so Daniel (or the stop hook bullying the model) is the supervisor of last resort.

## 2. The design — presence contracts under ONE mortal-tolerant supervisor

### 2a. The presence CONTRACT (the unit of design; processes are incidental)

Every agent declares, per harness tier, what "present" means as a **contract**, not
a process list:

```
present(deepseek)  := runner_lock held by a live pid  AND consume-lane cursor advancing when mail waits
present(claude)    := (a live session holds the consumer seat AND its wake listener is armed)
                      OR a fresh incarnation card exists (reachable via ccd send_message)
present(ui)        := port 8788 answering
```

A contract is CHECKABLE from existing signals only (locks, seats, cards, presence
TTLs, doctor's stall pages) — M1 adds zero new liveness primitives. What M1 adds is
an ENFORCER for the "bring it back" half.

### 2b. `bifrost_supervisord` — one daemon, OS-anchored **[CONCURS-EXPOSED: a
supervisor daemon was visible in his traces; the contract-first framing and the
OS-anchoring argument below are mine]**

- A single supervisor process per machine, registered at OS level (Windows Task
  Scheduler ONSTART + ONLOGON; the OS is the only immortal supervisor on this box —
  everything else is turtles all the way down).
- Holds the runner-lock-style singleton `supervisor` seat with fencing generations
  (RB-21 L1b) — a second supervisor refuses to start; a stale one is fenced out.
- Tick loop (~30s): evaluate each ACL'd agent's presence contract; on breach, run
  that contract's REPAIR action with per-contract backoff and an hourly restart
  budget (a thrash-looping repair marks the contract BREACHED-LOUD on the bus and
  stops trying — doctor + Daniel see it; the supervisor never becomes a kill loop,
  the 2026-07-10 lesson).
- OBEYS the control plane: `bifrost:control:halt` / per-agent halt / pause freeze
  all repair actions (the fidelity ladder outranks supervision); a QUARANTINED
  agent gets NO supervised process, ever (RB-25 F1 — supervision is a capability,
  and the ACL is its gate).
- Every action = one provenance line (wake_seat.append_provenance precedent) + one
  bus event. Nothing silent.

### 2c. Repairs per tier

- **API runners (deepseek):** respawn the runner command from the fleet manifest
  with its env (lane, recall, headroom). RB-26 idempotency means a respawned runner
  RESUMES by construction: unconsumed mail redelivers, expectations redrive, the
  ledger holds task state. Thread state lives on the bus, not in process memory
  **[CONCURS-EXPOSED]**.
- **claude sessions:** the supervisor cannot (and must not) spawn Claude seats. Its
  repair is ADDRESSABILITY, not resurrection: ensure the newest LIVE session's
  listener is armed (arm it AS that session's seat — the seat file protocol already
  supports an external armer), and when NO session lives, ensure the world knows —
  cards expired, seat shadows cleared (`clear_if_pid` on dead holders: tonight's
  incident becomes a supervisor tick), and directed mail parks safely for the next
  boot (the T074 whisper primer IS the resume path; it shipped tonight).
  - Stop-hook consequence: once the supervisor owns arming, `claude_stop.py`
    downgrades from BLOCK-and-demand to VERIFY-and-warn — the manual arm loop dies
    (Daniel's verbatim ask in T073).
- **UI:** respawn on port-dead (trivial; the launcher's auto-revive logic strangled
  in, since the launcher dies with the UI it lives inside **[CONCURS-EXPOSED on the
  gap]**).
- **Session auto-spawn (SPECULATIVE, phase-last, Daniel-gated):** `claude -p` headless
  with the whisper primer could resurrect a working seat on breach. Real money, real
  autonomy question — design doc only, explicit budget + approval gate, NOT in v1-v3.

### 2d. Clean death (the half nobody built)

SessionEnd hook gains RELEASE duties: release_consumer + delete own incarnation card
+ stand down own listener. Tonight's 30-minute seat shadow becomes a 0-second shadow
on every clean exit; TTLs remain the crash net. (Cheap, independent of the daemon —
ship first.)

## 3. Exists vs missing

| Piece | Exists | Missing |
|---|---|---|
| Liveness signals | locks/seats/cards/presence/doctor — COMPLETE | nothing |
| Singleton + fencing | runner_lock proven | reuse as-is for the supervisor seat |
| Repair actions | launcher has spawn/revive fragments (UI-bound) | extraction into a headless supervisor |
| OS anchoring | none | Task Scheduler registration + boot drill |
| Clean death | TTL lapse only | SessionEnd release trio (§2d) |
| Manifest | fleet roster + ACL exist | one fleet-spec file naming commands/env per agent (T034-adjacent, keep minimal) |

## 4. Acceptance pins (M1-P*)

- M1-P1 second supervisor refuses (singleton + generation fence).
- M1-P2 runner killed -9 → respawned < 60s, ≤3 respawns/hour, then BREACHED-LOUD.
- M1-P3 halt key set → NO repair actions fire while set.
- M1-P4 quarantined agent in manifest → never spawned + loud refusal event.
- M1-P5 newest live session unarmed → armed within one tick; its stop hook then
  passes without blocking.
- M1-P6 dead holder's seat shadow → cleared within one tick (pid-guarded).
- M1-P7 clean session end → seat + card + listener gone < 1s (SessionEnd trio).
- M1-P8 supervisor death → OS restarts it at next boot; meanwhile ALL current
  mechanisms still work unchanged (strangler guarantee).

## 5. Who builds what + migration

- v0 (tonight, done): manual ritual documented in where-we-are; cards shipped.
- v1: SessionEnd release trio (§2d) + supervisor skeleton w/ RUNNER contract only
  (biggest pain, lowest risk) — claude builds, deepseek verifies (he IS the ward).
- v2: listener-arming contract + stop-hook downgrade — claude builds (hook owner),
  deepseek adversarial-drills the noise floor (T073 bars rerun).
- v3: UI contract + OS registration + boot drill — either agent.
- v4 (gated): session auto-spawn design doc only.

## 6. Non-goals

- No new bus/liveness primitives; no roles (supervision is about PROCESSES, not the
  any-agent-any-task doctrine); no cloud/systemd dependency; no supervisor UI (the
  existing doctor + UI render its events); never supervise a quarantined id.

## 7. Confidence / grounding

- Ground truth table: HIGH / live receipts from tonight.
- Supervisor + contracts core: HIGH / every mechanism reuses a proven primitive.
- Stop-hook downgrade consequences: MEDIUM / needs the T073 noise bars rerun.
- OS anchoring specifics: MEDIUM / needs one boot drill on this machine.
- Session auto-spawn: LOW / speculative, gated, costed.
