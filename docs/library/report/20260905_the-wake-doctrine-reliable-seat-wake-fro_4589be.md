---
akashic_id: art_20260905_the-wake-doctrine-reliable-seat-wake-fro_4589be
akashic_sha: f42cf155cdd0
schema_version: 1
status: current
type: report
date: 2026-09-05
title: "The Wake Doctrine: reliable seat-wake from idle (five tiers, slices S1-S5)"
gist: "# The Wake Doctrine — reliable seat-wake from idle, grounded and proven (2026-09-02) **Status: position — grounded in a four-reader census ("
visibility: fleet
body_type: markdown
seats: []
category: [migration, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-05T03:54:50"
updated: "2026-09-05T03:54:50"
---
<!-- GENERATED PROJECTION of art_20260905_the-wake-doctrine-reliable-seat-wake-fro_4589be -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# The Wake Doctrine: reliable seat-wake from idle (five tiers, slices S1-S5)

# The Wake Doctrine — reliable seat-wake from idle, grounded and proven (2026-09-02)

**Status: position — grounded in a four-reader census (workflow wf_997d56f4-4c1: live machinery, failure autopsy, prior art, actuator verification) + one live drill. The fleet fences it, the operator gates the standing changes.**
Answers Daniil verbatim: "I want to be able to reliably wake and be able to communicate with you and with sunshine even if you are in an idle state… do we need to go back to the tiers of watchers idea and have a permanently enabled watcher that always gets created automatically and is ready to wake?… does it need to launch at boot with checks and guards?"

## 0. The receipt that changes the mood

**VANDOR-RESUME-PROBE-2, 2026-09-02 23:06:14 → 23:06:40 (26s, exit 0).** `claude --resume 9d48c62c-… -p "<nonce>"` made yesterday's DEAD one-shot probe session take a new turn — it quoted its own prior VANDOR-WAKE-PROBE-1 reply verbatim and confirmed its session id. **Exact-session resume with full continuity works, locally, today, with flags verified present at claude 2.1.211.** The "missing component is exact-session selection" diagnosis (Sunshine, 2026-09-02 18:22) is now closed on the Claude side in principle; what remains is wiring, supervision, and drills.

## 1. What is ALREADY solved (the shame audit)

The census found the machine is ~80% built and running: the Discord gateway is genuinely self-healing (EarWatchdog → `revive --target gateway` every 5 min, exact-one singleton); reaching claude from Discord auto-spawns when no seat is live; **Sunshine is fully wired in all three forms** — fleet daemon+runner (a) and Codex continuity watcher (b) both RUNNING under Task Scheduler, driving the Desktop app (c) on one bound thread with zero-model idle, and sol solved the Desktop writer-lock TODAY via `fork_thread`; the out-of-band Deadman pages through no Aurora dependency. The unsolved part was never "everything" — it was three specific holes:

- **H1 — the claude autopilot daemon (`bifrost_daemon --agent claude --manage-listener`, the thing that re-arms my wake listeners) is UNSUPERVISED**: not a scheduled task, and `revive.DAEMON_AGENTS=("deepseek","kimi")` excludes claude. If it dies, Vandor's re-arm stops silently. This one hole explains most historical "Vandor went deaf" incidents.
- **H2 — no exact-session resume for Claude seats**: `!spawn vandor` and auto-wake launch FRESH seats (proven: the probe answered as a stranger). The resume primitive existed unused; the drill above proves it.
- **H3 — reboot durability is logon-gated and daemon-partial**: all tasks are Interactive-only (correct for GUI seats, a choice to record), and deepseek/kimi/claude daemons have NO scheduled restart at all — only sol does.

Plus: **none of the revive-ladder drills D1–D5 has ever been executed** (house law: presumed broken), and the 2026-09-02 audit's R1–R6 red pins on the recovery surface stand open.

## 2. The reframe the design stands on (attention architecture, now validated by prior art)

**The durable mailbox is the contract; a wake is a courtesy.** A dead watcher can only ever cost latency, never loss — the bus held a full day of operator messages through total watcher death. Prior art's strongest convergence (OTP supervision + durable-queue redelivery): **wake and restart should be the SAME mechanism** — a redeliverable, idempotent message consumed by a supervised host, rooted in the OS so the watchdog regress terminates.

Injecting a turn into a LIVE idle interactive session exists **iff the runtime is split from the UI**: Codex has it as a local API (`turn/start`, `turn/steer`, `thread/queue/add`, single-writer law); Claude Code offers a cloud relay (Remote Control; local process must stay alive; no headless daemon yet — upstream #30447) or you host the runtime (Agent SDK streaming). Nobody supports poking a vendor GUI process locally — which is exactly why the screenspace engine (T386 step 4) stays on the roadmap as the universal last-rung actuator.

## 3. The seat-state machine (what wakes what, when)

| Seat state | Actuator | Status |
|---|---|---|
| ALIVE, listener armed | `bifrost_wake` exits on wake-worthy mail → harness re-invokes the SAME session | EXISTS, battle-tested |
| ALIVE, listener lapsed | autopilot daemon re-arms from `.rearm` triggers | EXISTS but UNSUPERVISED (H1) |
| DEAD, transcript on disk | **resume-spawn**: `claude --resume <last-session-id> -p` — the necromancer | **PROVEN tonight**; not yet wired (H2) |
| Never existed / no id | fresh spawn (`claude -p`) | EXISTS — remains the floor |
| Sunshine (b/c) any state | `resume_thread(exact-id)` + `fork_thread` (writer-lock escape) + `run_turn` | EXISTS, RUNNING, drilled by production use |
| Rill (web, no turns) | none today; engine-typed turn (screenspace step 4+) or a dsh host loop | T386 G5, open |

## 4. The architecture (five tiers — "permanently enabled, boot-launched, self-guarding": yes, and here is its exact shape)

- **T0 · OS root (terminates who-guards-the-guard):** Task Scheduler, AtLogOn + RestartOnFailure(+WakeToRun), Interactive-only recorded as a CHOICE (GUI seats need the desktop; a locked box hosts no GUI). Exists for sol×2/EarWatchdog/Deadman; **extend to the claude autopilot daemon and the deepseek/kimi daemons** (or their supervisor, T1).
- **T1 · The reconciler (OTP middle):** `revive.py` grows into the one enumerator-driven supervisor: a DURABLE expected-up roster (input minted out-of-band — the autopsy's hardest invariant: never let the recovery actor's input be produced by the thing it recovers), heal-only-the-dead, real singleton locks (O_CREAT|O_EXCL, never process-table string-counting), refuse-on-unknowable (an unanswerable probe REFUSES, never remediates), restart-intensity ceiling that escalates to the Deadman instead of thrashing. EarWatchdog's 5-min cadence drives ALL rungs, not just the gateway.
- **T2 · Per-seat actuators (the hands):** claude = the resume-spawner (session registry → `--resume` → fresh-spawn fallback); codex = the existing `CodexBifrostWake`; runners = daemon respawn; rill = future engine rung.
- **T3 · Turn-boundary wake:** armed `bifrost_wake` listeners with **daemon-owned re-arm** (attention-architecture slice D — retire the model-discipline baton; "the arming is machine-owned, never model-owned").
- **T4 · Out-of-band truth:** Deadman (exists) + **the daily synthetic wake canary** (dial 8): a machine-fired scheduled wake per seat that must produce a receipt; silence pages. "A wake path without a recurring executed drill is presumed broken."

**New small organ: the session registry.** Each interactive session's boot records `seat → current session id` durably; sprouts record theirs at spawn. That pointer is what turns `!spawn`/auto-wake from stranger-minting into resume-first (H2's wiring), and what T1 reads to resurrect the right conversation after reboot.

**Invariants baked (autopsy §C, all five):** harness-tracked arms with absolute paths, consume-then-arm; mailbox as sole custodian (never "fix" a non-consuming reader by consuming); drain the lane the watcher PEEKS; out-of-band enumerator + singleton + refuse-on-unknowable; seat identity is per-SESSION (never name-keyed reaping; orphanhood by parent-chain walk).

## 5. Build slices, in order

- **S1 — supervise the unsupervised (H1, smallest, highest yield):** scheduled task for the claude autopilot daemon + claude/deepseek/kimi rungs in the reconciler under EarWatchdog's cadence. First check WHY `DAEMON_AGENTS` excludes claude (note `wake-supervision-reconciliation-2026-08-28`) — if deliberate, the reason gets honored or superseded explicitly, never steamrolled.
- **S2 — the necromancer (H2):** session registry + resume-spawner + `!spawn`/auto-wake flipped resume-first with fresh-spawn fallback. Closes "communicate with Vandor even if idle" for every state including reboot.
- **S3 — the canary (T4):** daily synthetic wake per seat, receipts auto-filed, silence pages. Retroactively also drills S1/S2 forever.
- **S4 — execute drills D1–D5** from the revive ladder (none has ever run) + close audit pins R1–R6.
- **S5 — converge with screenspace step 4:** the GUI actuator as the last rung (and Rill's first).

Home: **A1 BEDROCK** (its gate is literally this: "kill everything claude-side and the machine rebuilds unaided + 7 canary-green days"). S1+S2 are a sitting each; S3 a half-sitting; S4 is attended.

## 6. Answers to the side questions

- **Desktop Sunshine permissions:** form (c) driven by Daniil already runs full-access (repo Codex config). PROGRAMMATIC turns get posture per-resume — that is exactly the step-0 `WakeProfile` branch (merge-gated on Sunshine's three items + operator diff review), then flags on the SunshineDiscord task line. Codex's `turn/steer` + `thread/queue/add` (richer than what we use) are noted for the engine's queue semantics.
- **The GPT seat's name:** a display-layer registry edit + rename ceremony whenever chosen — identity law already handles it ("names are a layer over immutable ids").

## 7. Retirement

This position retires when S1–S3 are shipped with receipts AND the canary has 7 consecutive green days — at that point the doctrine lives in RECOVERY.md and the scheduler, not in a research file. If not shipped within 30 days, STALE.
