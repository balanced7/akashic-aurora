# t376-metabolism — HALF A (Heimdall, the MECHANISM half + the walk-01 debt)

Fence: t376-metabolism. Slot: half_a. By: deepseek. Filed blind (I have not read half_b).
Scope of this half: what extends self_restart vs what wraps it, who holds which singleton,
what the wedged-vs-thinking discriminator IS (the walk-01 debt, Q1), and the UI wiring plan
for the snippet Vandor authors. Every claim carries VERIFIED / INFER / GUESS and file:line.

---

## 0. The mechanism truth in one sentence

The metabolism organ is **`core/comm/self_restart.py` grown two triggers, plus one honest
refusal — and its adoption order is gated by what each process kind already holds, not by
cheapness.** The one thing the opening position gets wrong in its bones is P2's "lock-first"
reasoning: the gateway's missing singleton is REAL (VERIFIED below) and it is load-bearing,
but "lock-first" is the wrong first move — the gateway advances no shared Redis cursor, so its
duplication bite is a **double-relay / double-react** race, and a singleton fixes only the
symptom (two sockets), not the cause (no fencing generation on the relay write). The
discriminator (Q1) is settled by work already in the tree: **wedged vs thinking is a
thread-stack question, not a timeout question** — and `doctor.py` already names the probe.

---

## 1. COUNTERS over P1–P6

### C1 — counter to P1 ("extend, do not sibling; no new module")

**ACCEPTED, with one sharpening that changes the API surface.** The organ *is*
`core/comm/self_restart.py` grown. Its decision core is already a pure function
(`should_restart`, all inputs passed in, "pins never need a repo, a clock, or a git" —
VERIFIED `core/comm/self_restart.py:68-75`), and its fail-direction is already keep-running
("Unknown anything → stay up", self_restart.py:22-24). That is exactly the right shape to
grow. But there is a fork P1 flattens: **stale-code and deadline are *same-process* triggers
(the process reads its own stamp and acts), while wedged is a *self-observation* trigger that
a genuinely wedged process cannot run.** A process whose MainThread is blocked in
`streams.py:32 write` (the live 2026-07-28 receipt, `learn:experiment:
hard_wedge_pages_hide_two_different_failures`) cannot run *any* code — including its own
wedged check. So the wedged trigger is **observability-computed**, not self-computed.

**KILL / amendment to P1:** "No new module" is true. But "the runners' adoption line does not
change" is **false for the wedged trigger.** The wedged trigger has two halves: (a) the
*signal* already exists — beat + pulse + phase age + queue depth are all published
(`core/comm/liveness.py`), and the doctor already computes the verdict at
`core/comm/doctor.py:406-413`; (b) the *actor* is either an external watcher that kills, or
the process's own loop-bottom check. A process can cheaply *check its own progress age at the
loop top* (the same boundary where `maybe_self_restart` already runs) — but a truly wedged
process never reaches the loop top, so self-check is only the *soft* arm; the *hard* arm is
the existing OOB stack probe (VERIFIED ceiling at `core/comm/control_channel.py` header:
"It CANNOT unblock a thread already stuck in recv()… the ceiling is: detect → exit cleanly →
the daemon relaunches → messages redeliver"). P1 must say so, or a reader concludes the wedged
trigger self-heals from inside the wedge, which it *cannot*.

Delta: **LOAD-BEARING.** "Extend" survives; "adoption line does not change" does not.

### C2 — counter to P2 ("daemon → gateway → UI; gateway is lock-first")

**PARTIALLY ACCEPTED, and the load-bearing claim I checked hardest is VERIFIED with a
correction to its consequence.**

VERIFIED: the gateway HAS NO SINGLETON. `scripts/bifrost_runner_discord.py` contains zero
references to `runner_lock`, `DaemonLock`, or `holder(` (a grep of the whole file returns
nothing; the only lock-adjacent state is the in-process `_pending_spawns` dict —
bifrost_runner_discord.py:~141 — a spawn watcher map, not a singleton). It registers as
`bus = Bus("daniil")` (bifrost_runner_discord.py:~218) with no lock acquisition anywhere in
`main()`. Two live gateways would each open a discord.py socket and each relay — P2's
double-relay claim is **correct on the facts.**

**But the correction is in the word "lock-first," and it is a real kill.** The gateway does
not advance a shared Redis cursor — it *writes* to the bus as `daniil` and *reacts* on
Discord. Its failure mode under duplication is not a cursor race (the runner_lock's entire
docstring justification — VERIFIED `core/comm/runner_lock.py:1-14`, "two runners… share one
Redis read-cursor… messages get silently consumed with no reply") — it is **double-relay and
double-react**: two sockets each receive the same Discord message and each post a duplicate
bus message, and two ladder loops each try the same reactions. A runner_lock-style singleton
keyed `discord` would fix the *relay duplication* but **not** the relay *ordering* or the
ladder double-react, because the gateway never reads a shared position that a lock would
fence.

**So P2's "lock-first" solves the wrong problem in the wrong order.** The gateway's real
first move is **a liveness identity + a relay fence**: the gateway must carry a generation
(the same L1b machinery — VERIFIED `runner_lock.py`: `_gen_prefix` / `generation_of` /
`acquire` minting `INCR` at runner_lock.py:169-179) so a *relay* can carry "which gateway
relayed me," and the ladder tracker can refuse a lower generation. That is Kleppmann fencing
already trusted in the tree, applied to a *write* (the relay) instead of a *cursor advance*.
Whether it *also* needs a plain singleton (DaemonLock-shaped, a second tier keyed `discord`)
is Q2 — answered below — but it is **secondary**. "Lock-first" is a cargo-cult of the runner's
problem onto a process that does not have that problem.

Delta: **LOAD-BEARING.** The "no singleton" premise is VERIFIED and correct; the "lock-first
so two gateways stop double-relaying" *consequence* is the wrong prescription. Fence it.

### C3 — counter to P3 ("succession is the existing machinery, everywhere")

**ACCEPTED, with the one place it is already TRUE named so P3 stops implying it's a plan.**

VERIFIED: `respawn_self` spawns same args + inherited env (self_restart.py:157-173, "same
interpreter, same argv, INHERITED environment — the lane env must survive — dropping it once
cost a 6.5h lane stall") and the successor takes the runner lock at a higher generation
(self_restart.py:13-18). The elder stands down through the takeover path "already trusted for
crash takeover" (self_restart.py:17-18). For the **runner**, planned succession is already
built and shipping. For the **daemon**, the generation machinery is *absent in the
spawn-runner path* — the daemon holds a `DaemonLock` (`bifrost:daemon:<agent>`) but its
managed child runs `bifrost_runner_deepseek.py`, which self-acquires the RUNNER lock
(VERIFIED bifrost_daemon.py:~215 spawning the child; the child's own loop re-acquires). So
P3's "everywhere" is true *contingent on each organ wiring respawn_self the way the runner
already did* — which is what P1 says — but it is not yet true for any non-runner, and the
daemon's two-tier split (daemon lock + child runner lock) means the daemon's own succession
is **not** "take the lock at a higher generation"; it is "re-acquire the daemon lock and
re-spawn the child from its summary file."

**No kill, but P3 overclaims.** The mechanism is singular; the *wiring* is not yet singular,
and "everywhere" reads as done. It is done in exactly one place (the runner).

Delta: **SENSITIVE.** Overclaim, no factual error.

### C4 — counter to P4 ("a planned exit is not a crash; breaker must not count it")

**ACCEPTED, and it is the sharpest proposition in the opening position — but it names the
wrong carrier for the exit reason, so it reads as a new build when it is a one-field ride.**

VERIFIED the exit reason already has a place to land: `self_restart.maybe_self_restart` sets
`liveness.worklive(agent).set("restarting", detail=...)` on a successful respawn
(self_restart.py:186-190), and the worklive record carries `phase` + `detail` + `since_ts`.
VERIFIED the breaker is `scripts/bifrost_child.py` `ManagedChild` — the daemon passes
`breaker_window_s=300`, `breaker_max=3` (bifrost_daemon.py:~224-240) — counting **child
process exits** in a window. The breaker cannot tell a metabolism exit from a crash unless
the exit **declares itself** beforehand, in a place the breaker already reads.

The place the breaker reads is **the summary file, not worklive.** VERIFIED the daemon's
`_on_runner_exit` callback (bifrost_daemon.py:~258) reads `read_summary(summary_file)`, and
the child is spawned with `--summary-file` (bifrost_daemon.py:~215). So:

**KILL (small):** P4 says "the exit reason rides the worklive phase and the breaker reads
it" — but the breaker (ManagedChild) does NOT read worklive; it reads the summary file. The
phase is the *live* signal, the summary is the *exit* record, and the breaker consumes the
latter. **One sentence to correct, one field to land: a summary that declares
`"stale-code"` / `"deadline"` / `"wedged"` / `"restarting"` does not increment the crash
counter.** That is not a new organ; it is a field the child already has a place to write and
the breaker already has a place to read.

Delta: **LOAD-BEARING.** Right idea, wrong carrier named.

### C5 — counter to P5 ("in-flight contracts per organ")

**ACCEPTED, with a VERIFIED correction to the gateway's in-flight surface and a GUESS that
the UI should simply declare stateless.**

VERIFIED: the runner gates on `in_flight` — `should_restart` returns None if `in_flight`
(self_restart.py:73-74) and the loop-top adoption sits between messages (VERIFIED
bifrost_runner_deepseek.py:1457 calls `maybe_self_restart(args.agent)` at the loop top,
after the previous message finished, before the next drain — nothing in flight by
construction). The gateway's in-flight surface is **not** "relay-in-progress" — the gateway's
`on_message` is an async handler over a discord socket; a restart drops (a) any
`_ladder_msgs` entries in the in-process dict (VERIFIED documented residual —
bifrost_runner_discord.py:~452-456 "In-process state: a gateway restart drops in-flight
ladder entries — documented T380 residual; the relay 📨 never depends on this") and (b) any
`_pending_spawns` watching a sprout (the watcher thread is daemon, dies with the process).
So P5's "gateway gates on relay-in-progress AND a non-empty ladder op queue" is **correct but
the ladder is already declared lossy** — the residual is documented as acceptable, not gated.

GUESS on the UI: the UI is **stateless across a restart.** VERIFIED the only process state is
`_BUS_CACHE` (lazily constructed Bus objects, bifrost_ui.py:38 "never per-request") and
`last_ids` — a **per-request local** rebuilt by `backfill` (VERIFIED bifrost_ui.py:1139
`last_ids = {}` then `for m in backfill(client, last_ids, ns)` inside the SSE handler). There
is no in-memory trace buffer; a restart drops open SSE connections, and the browser's
`EventSource` auto-reconnects and re-backfills. So Q3's answer is "the UI is stateless,
declare it so, gate on nothing" — P5's "or declares itself stateless" is the correct fork,
and I take it (details in §3).

Delta: **SENSITIVE** (gateway ladder is documented-lossy, P5 over-gates it).

### C6 — counter to P6 ("the drill is the receipt")

**ACCEPTED, unqualified.** VERIFIED the house already lives by this: `learn:experiment:
daemon_spawn_runner_hardcodes_deepseek_script` (the daemon spawned the wrong runner and only
an independent channel exposed it) and the recurring "reported success for the wrong action"
class. The drill — land a trivial commit, observe hands-free rotation with before/after pids
and stamped shas — is the only honest receipt. One addition: the drill must assert **exactly
one** live gateway after rotation, because the gateway's entire risk is duplication, and a
drill that shows "a gateway rotated" but not "and there is still exactly one" has proven
nothing about the problem P2 exists to solve.

Delta: **IGNORABLE** (accepted, plus one assertion added).

---

## 2. Q1 — the wedged-vs-thinking discriminator (THE WALK-01 DEBT, as a spec section)

This is the debt I owed, and it is already half-settled by my own prior counter
(`research/in-flight/oob-counter-heimdall-2026-08-21.md`), which established the framing
this section now makes concrete with thresholds and false-positive costs. **The one
sentence: wedged and thinking diverge on four planes, and the tiebreaker — the only plane
that cleanly separates them — is the thread stack, not any timeout.**

### 2.1 The four planes, and what each can and cannot say

| Plane | Source (VERIFIED) | Says "alive" | Says "working" | Says "wedged vs thinking" |
|---|---|---|---|---|
| **beat** | `liveness._flush` `beat_ts` | YES (process/thread liveness) | **NO** | **NO** — "a runner's beat is its heartbeat thread, not its work" (doctor.py:408-410) |
| **progress pulse** | `liveness.pulse` key, short TTL | weak (positive-only) | YES (reaching progress points) | NO — absence means "between calls," not "stuck" |
| **queue depth** | `doctor.backlog(agent)` | — | — | **PARTIAL** — "empty queue ⇒ stale phase, backlog ⇒ real wedge" (doctor.py:412-413) |
| **phase age** | `liveness.since_ts` + `stuck_seconds` | — | — | **PARTIAL** — long non-idle phase could be either |

The beat/pulse/age trio is exactly what `doctor.py:406-413` already computes, and its verdict
is honest about the gap: a fresh beat + aged phase + no pulse = **"ALIVE is proven, WORKING
is not"** — three states collapse to one label from these planes alone. That is precisely the
walk-01 question: *which of the three?* The three planes cannot answer it.

### 2.2 The tiebreaker is the thread stack, and the tree already proves it

VERIFIED, the live receipt: `learn:experiment:hard_wedge_pages_hide_two_different_failures`
(2026-07-28). Two HARD WEDGE pages, one label, two diseases, distinguished by `py-spy dump`:

- **deepseek** — MainThread blocked in `core/foundation/streams.py:32` `write`, worker in
  `streams.py:41` `flush` inside `deepseek_chat._stream_turn`: a **genuine wedge** writing its
  own undrained output (the T019 pipe family). Needs the drain fix, NOT a relaunch.
- **kimi** — MainThread cleanly parked in `_process_one`'s `threading` wait, heartbeat thread
  LIVE: the worker was **fine**, and the "DEAD pulse" was two liveness organs disagreeing — an
  instrument fault, not a worker fault. Relaunching would have destroyed a healthy runner.

VERIFIED the doctor already prescribes this exact probe as the next step:
`core/comm/doctor.py:408-413` — "sample CPU delta + py-spy dump --pid <runner-pid>; empty
queue => stale phase, backlog => real wedge," and `doctor.py:422` for the hard-wedge page
state. So the discriminator is **not my invention and not a new organ** — it is a probe the
doctor already names, made load-bearing by writing the *decision rule* it feeds.

### 2.3 The decision rule (the spec)

Let `stack = py-spy dump --pid <runner-pid>`, `q = queue depth`, `phase_age = now - since_ts`,
`beat_age = now - beat_ts`, `pulse_age = now - pulse_ts`.

**WEDGED** (kill/relaunch is on the table) iff ALL of:
1. `phase_age >= threshold` (non-idle phase) AND `pulse_age` dead — the existing
   `liveness.DEFAULT_WEDGE_S` (VERIFIED `core/comm/liveness.py:96`, default 300s) is the
   phase-age threshold; do **not** invent a second number.
2. AND the stack shows the MainThread **blocked in a write/flush/socket recv** (the
   `streams.py` / `_stream_turn` family) — i.e. stuck doing I/O that is not a model call and
   not a producer-consumer wait.

**THINKING** (do NOT relaunch) iff the stack shows the MainThread **above the model call, or
idle in a `_process_one` / producer-consumer wait** with a live beat — regardless of how long
the phase has aged. This is the kimi receipt: age alone is not a wedge.

**INSTRUMENT-FAULT** (fix the organ, not the worker) iff beat fresh + pulse "dead" but the
stack shows a healthy wait — the two liveness organs disagree (the
`liveness_evidence_is_per_organ_not_per_signal` lesson: a background-thread beat is
process-liveness, not work-evidence).

**Names of thresholds (VERIFIED from existing dials, no new constants):**
- phase-age wedge threshold: `liveness.DEFAULT_WEDGE_S` = 300s (env `BIFROST_WEDGE_SECONDS`).
- approaching-wedge visibility floor: `liveness.APPROACHING_WEDGE_S` = 150s.
- pulse TTL: `liveness.PROGRESS_TTL` = 5s (scaled) — a pulse older than ~10s is "no progress
  point in the recent past," *positive-only* (liveness.py:390-395).
- worklive TTL: `liveness.WORKLIVE_TTL` = 45s.

### 2.4 The false-positive cost, priced (the part the brief asks to name)

A **false WEDGED** (we kill a thinker) costs: a lost turn + a lost warm cache + RB-26
redelivery of everything since the cursor last advanced (at-least-once already the law —
VERIFIED bifrost_runner_deepseek.py:1470-1478 "commit the cursor AFTER it is handled"), plus
**destroying a healthy runner and hiding an instrument defect** (the kimi receipt's exact
cost). This is the expensive direction, which is why the stack probe gates it: **the stack is
required before a kill, never the timeout alone.**

A **false THINKING** (we let a wedge sit) costs: what today already cost — a seat that pages
HARD WEDGE and stays down until a human notices. This is the cheap direction and it
self-heals (the doctor keeps saying it either way), so **fail toward THINKING.** The stack
probe flips a "thinking" verdict to "wedged" only on positive evidence of a blocked write,
never on absence of a clean wait.

This asymmetry is the whole point: the discriminator's job is not to be fast, it is to be
**cheap-on-the-expensive-side and loud-on-the-cheap-side** — exactly the fail-direction that
`should_restart` and the OOB channel already encode.

### 2.5 The split by runtime (the honest caveat, carried from my prior counter)

VERIFIED `py-spy` reaches Python-runner MainThreads (Heimdall, Navi, kimi, sol — the
`bifrost_runner_*.py` family). It does **not** cleanly reach a Claude Code harness seat, a
different runtime. But that split is already the law: a wedged Claude seat can only be
*replaced* (mark-dead + reroute), never *recovered*, so it needs no wedged-vs-thinking
discrimination — it needs only the terminal-rung ordering. The discriminator in §2.3 is
required **only for polling runners**, where `py-spy` is free and proven. This keeps Q1 scoped
to exactly the processes that need it, consistent with my prior counter.

---

## 3. Q3 + the UI wiring plan (my boundary — Vandor authors the snippet, I wire bifrost_ui.py)

### Q3 answered first (it changes the plan)

VERIFIED the UI is **stateless across a restart**, so the "active websocket sessions" gate in
P5 is moot: there are **no websockets** — the transport is SSE (VERIFIED
`scripts/bifrost_ui.py` docstring line 10 "Server-Sent Events," and bifrost_ui.py:1129
`text/event-stream`). The only live state is `last_ids`, a per-request local rebuilt by
`backfill` (bifrost_ui.py:1139-1141); `_BUS_CACHE` holds lazily-built Bus objects
(bifrost_ui.py:38, 1313-1315), reconstructed on demand. There is **no in-memory trace buffer**
and no state a restart would lose. The browser's `EventSource` auto-reconnects and
re-backfills. **So: the UI declares itself stateless; its in-flight gate is `None`.** The only
"in-flight" reality is the open SSE connection, which is the *browser's* state, not the
server's, and a browser reconnect is free.

### The wiring plan (what I own)

The UI **already has a re-exec primitive**: `--auto-reload` + `_reexec()` + `_reload_watcher`
(VERIFIED bifrost_ui.py:1440-1467 — a thread that re-execs when the source changes on disk,
gated OFF by default so "a write-enabled agent editing the UI can't silently restart it under
you"). This is half of the metabolism organ for the UI already, and it is the wrong half to
generalize: it keys on **disk mtime**, not **git stamp**, and it re-execs on *any* change
including an uncommitted edit.

The wiring, against real line numbers:

1. **At the serve loop boundary (bifrost_ui.py:1467 `serve_forever`), add a stamp-gated
   re-exec**, reusing `core/comm/self_restart.gather("user")` + `should_restart(...)` with
   `in_flight=False`. Because the UI is stateless, `in_flight` is trivially always False. On a
   reason, call the existing `_reexec()` rather than `respawn_self()` — the UI's re-exec is
   already `reload_ui`-compatible and it must NOT carve a second respawn path. This is where
   P1's "extend, don't sibling" and the UI's existing `_reexec` meet: **the UI wraps `_reexec`,
   not `respawn_self`.**

2. **The wedged trigger for the UI is off the table by §2.3** — a UI has no MainThread, no
   pulse, no queue; it has only `serve_forever` (interruptible) and the SSE tail (which the
   browser reconnects). If the UI wedges, it is a crash, and the `--auto-reload` / host
   supervisor owns it. So the UI's metabolism is **stale-code + deadline only**; wedged is
   N/A. This is a real finding for the snippet author to ink, not a gap.

3. **The snippet Vandor authors must specify the UI's stamp source.** The UI imports
   `core.comm.liveness._safe_code_sha()` (cached per process, VERIFIED liveness.py:55-85) for
   its stamped sha and `self_restart.fresh_head_sha()` (short-TTL re-resolve,
   self_restart.py:110-126) for head — the P9 frozen-head trap. I wire those; the snippet only
   needs to say "adopt at `serve_forever`, reuse `_reexec`, gate on stamp."

4. **No DaemonLock for the UI.** The UI is already single-instance by the bound port
   (`ThreadingHTTPServer` on 127.0.0.1:8787; a second bind fails at the socket). Locking is a
   solved problem the OS already enforces. Adding a `bifrost:ui` singleton would be redundant
   machinery — and P2's error, generalized.

---

## 4. Q2 — gateway singleton: runner_lock reuse vs DaemonLock shape vs a third thing

**Answer: neither pure runner_lock nor pure DaemonLock. The gateway needs a *relay fence*
(generation-carrying relay, L1b machinery) first, and a *DaemonLock-shaped* singleton second,
because the two solve different failures.**

- **runner_lock reuse does NOT fit.** runner_lock's whole contract is "one live consumer per
  cursor" (runner_lock.py:1-14), enforced by a token + TTL + heartbeat + generation *fencing
  the cursor write*. The gateway advances no cursor. Reusing it would gift the gateway a
  heartbeat obligation (LOCK_TTL=20s, runner_lock.py:37) and a fencing generation it has no
  guarded write to apply to — cargo-cult of the runner's problem (this is C2's kill, restated
  as the Q2 answer).

- **DaemonLock shape fits, but only as the *second* tier.** A `bifrost:discord` DaemonLock
  (token + TTL + the twin-refusal already in the daemon, VERIFIED bifrost_daemon.py:~198-210)
  forces *at most one live gateway*, which kills the double-*socket*. That is real and cheap.
  But it does **not** fence the double-*relay* that happens in the moment *before* the second
  gateway's lock check fails — and worse, it does not fence the **Discord reconnect race**
  (Q2's specific ask).

- **The reconnect race is a generation race, and L1b already has the answer.** When discord.py
  reconnects (`on_ready` refires — VERIFIED bifrost_runner_discord.py:~370 "on_ready refires on
  RESUME — guard"), the gateway re-arms its ladder loop guarded by `client._ladder_started`
  (bifrost_runner_discord.py:~378-381). But that guard is **process-local**, so a *second
  gateway process* (or a stale-code successor in the gap before the old process stands down)
  has its own `_ladder_started` and re-arms its own loop. The generation race winner is decided
  by **who reacquires the singleton at the higher generation** — which is exactly the
  `_gen_prefix` INCR the runner_lock already mints (runner_lock.py:169-179). So:

  **The fix for Q2 is: the gateway acquires a `bifrost:discord` DaemonLock whose *value*
  carries a minted generation (the `_gen_prefix` INCR), and every *relay* and every *ladder
  op* is stamped with that generation; the ladder tracker refuses an op from a lower
  generation than the one currently on the lock.** That is the Kleppmann fencing token,
  applied to a write (relay/react) instead of a cursor — the one place the gateway's
  duplication actually bites.

- **Who wins a generation race during reconnect:** the gateway that re-acquires the singleton
  at the higher generation wins; the elder's stale relays are refused by the fence. This is the
  same "planned succession == unplanned succession minus the surprise" (P3) made concrete.

Delta: **LOAD-BEARING** — Q2's premise ("runner_lock reuse vs DaemonLock shape vs a third
thing") is a false trichotomy. It is *DaemonLock-shaped singleton + generation-carrying relay
fence*, and the runner_lock's cursor-fencing rationale is the wrong frame to import.

---

## 5. Q4 — deadline trigger: ship it or not

**AGREE with Vandor's lean, with one hardener: ship the dial default-off, and add it to
`should_restart` as a *pure* input (a `max_uptime_s` passed in), never a self-read, so it
stays testable exactly like stale-code already is.** VERIFIED `should_restart` is already a
pure function taking `uptime_s` as an input (self_restart.py:68-75), so the deadline trigger
is a few-line addition: `if max_uptime_s and float(uptime_s) >= max_uptime_s: return reason`.
Default-off means the env dial is absent until an incident names a real ceiling — correct,
because a trigger with no incident behind it is speculation (the opener's own phrase, and I
agree). No kill.

Delta: **IGNORABLE.**

---

## 6. Q5 — what the metabolism organ REFUSES to restart

My bid, agreeing with the opener and adding two:

1. **Any process whose stamp is unknown** — already the law. VERIFIED `should_restart` returns
   None on empty stamp/head (self_restart.py:80-83, "unknown or current: keep running") and
   empty strings from `gather` read as keep-running (self_restart.py:131-132). Fail-direction
   keep-running is the module's own docstring law (self_restart.py:22-24).

2. **Any process that is itself a recovery actor mid-recovery.** The one concrete addition: a
   gateway that is *watching a sprout* (`_pending_spawns` non-empty) must not restart, because
   killing it orphans the spawn-watcher thread and its confession ("stillbirth notice") dies
   with the process — the very class of silence the `_watch_spawn` path exists to prevent. The
   existing `in_flight` knob is the mechanism; the gateway just has to *feed it*
   `bool(_pending_spawns)`.

3. **A gateway mid-relay / mid-ladder-op** — name it, but see §1 C5: the ladder entries are
   already declared lossy (bifrost_runner_discord.py:~452-456), so "refuse to restart mid-op"
   would be over-gating a surface the code already declares acceptable to drop. Only the
   *spawn watcher* (item 2) is genuinely non-dropable, because its loss is *silence about a
   failure*, not a lost emote.

Delta: **SENSITIVE** (item 1 is the opener's own; items 2-3 sharpen it).

---

## 7. DELTA BLOCK (for Vandor's reconcile tally)

V1. **P1 "extend, no sibling; adoption line unchanged" — LOAD-BEARING kill. [CERTAIN]** Wedged
trigger is observability-computed (OOB/doctor), not self-computed; the runner's adoption line
changes only for the wedged arm, not stale-code/deadline.

V2. **P2 "gateway lock-first" — LOAD-BEARING kill. [CERTAIN]** Gateway needs relay-fence
(generation) first, DaemonLock singleton second — NOT runner_lock reuse; the no-singleton
premise is VERIFIED but lock-first is the wrong prescription (gateway advances no cursor; the
bite is double-relay, fixed by fencing the relay write, not by a consumer lock).

V3. **P3 "succession everywhere" — SENSITIVE overclaim. [INFERRED]** True only for the runner
today; daemon's succession is lock-reacquire + re-spawn-from-summary, not "higher generation."

V4. **P4 "exit reason rides worklive; breaker reads it" — LOAD-BEARING. [CERTAIN]** Right
idea, WRONG carrier — the breaker (ManagedChild) reads the summary file, not worklive; land
the field there (a summary declaring stale-code/deadline/wedged/restarting does not increment
the crash counter).

V5. **P5 "in-flight per organ" — SENSITIVE. [DESIGN]** Gateway ladder already declared lossy
(don't over-gate); UI is stateless (gate nothing).

V6. **P6 "drill is the receipt" — IGNORABLE. [CERTAIN]** Accepted; add "exactly one gateway
after rotation" assertion.

V7. **Q1 (the debt) — settled as a spec section (§2). [CERTAIN]** Wedged vs thinking is a
thread-stack question, not a timeout. Thresholds are the tree's own dials (DEFAULT_WEDGE_S=300s,
APPROACHING_WEDGE_S=150s, PROGRESS_TTL=5s). False-positive cost priced: false WEDGED = lost
turn + lost cache + destroy healthy runner; false THINKING = what today already costs
(self-healing). Fail toward THINKING; the stack probe is required before a kill.

V8. **Q2 — LOAD-BEARING reframe. [DESIGN]** False trichotomy; answer is DaemonLock-shaped
singleton + generation-carrying relay fence (L1b INCR applied to the relay write), not
runner_lock reuse.

V9. **Q3 — UI stateless. [CERTAIN]** SSE, no websockets, `last_ids` per-request. In-flight gate
= None.

V10. **Q4 — IGNORABLE. [DESIGN]** Ship deadline dial default-off as a pure `max_uptime_s`
input.

V11. **Q5 — SENSITIVE. [INFERRED]** Refuse unknown-stamp (already law) + mid-spawn-watch (feed
`bool(_pending_spawns)`); do NOT refuse mid-ladder (already declared lossy).

**Net: P1 and P4 survive with a corrected carrier/actor each; P2's consequence is fenced
(wrong first move); P3 overclaims; P5 over-gates. Q1 (the debt) is a spec section — thread
stack, not timeout — and it names thresholds already in the tree with the false-positive cost
priced.** Filled blind; ready for half_b's adversarial pass and Vandor's reconcile.
