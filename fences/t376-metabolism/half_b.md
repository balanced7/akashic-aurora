# T376 half_b — ADVERSARIAL PASS (Navi / kimi, 2026-08-23 night)

Blind from half_a. Scope per brief: break P4 (breaker interaction), P5
(in-flight gaps), Q2 (gateway lock under reconnect race). Numbered
refutations with reproduction sketches; no design prose. Labels
VERIFIED (file:line) / INFER / GUESS; load-bearing claims tagged V1..Vn.

---

## R1 — P4 as written protects the WRONG process's breaker [V1, VERIFIED]

P4 says: "the daemon's 3-crashes/5min breaker must not count metabolism
exits ... The exit reason rides the worklive phase ('restarting') and the
breaker reads it."

The 3-crashes/5min breaker is NOT in the daemon. It is in
`scripts/bifrost_child.py:ManagedChild._handle_exit` (breaker_window_s=300,
breaker_max=3 defaults at lines ~133-134; trip logic at
`scripts/bifrost_child.py:262-270`). It counts the CHILD's (runner's)
exits, not the daemon's. And the exit-reason channel P4 proposes — the
worklive phase — is written by the CHILD
(`core/comm/self_restart.py:191` — `liveness.worklive(agent).set("restarting",
...)`), while the breaker lives in the PARENT. Between the child setting
phase "restarting" and exiting, the parent's breaker never reads worklive
at all: `_handle_exit` (bifrost_child.py:249-270) reads only the exit CODE.
Grep of bifrost_child.py for `phase|worklive|crash|breaker` outside the
breaker itself: zero reads of the child's worklive record anywhere in the
supervision path [INFER from grep nil; VERIFIED nil result, two probe
patterns].

**Reproduction sketch (pure, no repo/redis):** instantiate
`ManagedChild(["py","-c","raise SystemExit(1)"])`; call `poll()` 3 times
with `breaker_window_s=300`; observe `_tripped=True`. Now repeat with the
child setting a phase file named "restarting" before `SystemExit(1)` —
breaker still trips: the mechanism is code-blind by construction. The P4
fix as specified ("breaker reads the phase") requires a NEW cross-process
read (parent reads child worklive, with the TTL/race that carries) that
exists nowhere today. P4 is a requirement statement wearing a mechanism's
clothes. NOT FALSE — but UNMECHANIZED as written; the fence's reconciled
design must name who reads what, or it ships as a comment.

**Severity: LOAD-BEARING.** The whole "planned exit is not a crash" claim
currently rests on a read nobody performs.

---

## R2 — P4's premise is HALF-WRONG, and the true half is worse [V2, VERIFIED]

Two sub-findings, both verified in `_handle_exit` (bifrost_child.py:249-270):

(a) **Exit 0 never enters the crash deque.** `if code == 0:` clears
`_crashes` and sets `_next_spawn_at = float("inf")` — the N1
"benign exit = deliberate handover" path. A planned metabolism exit that
returns 0 CANNOT trip the breaker. So for the well-mannered case, P4's
feared sequence (rolling refresh trips the breaker) does not exist. P4
attacks a phantom — IN THE DELTA PATH, see (c).

(b) **Exit 0 is the death of the runner, permanently.** The same N1 path
sets `_next_spawn_at = inf`: "never auto-respawn" (comment at
bifrost_child.py:257). The daemon becomes "presence-only until restart"
(docstring, bifrost_child.py:126-128). So the daemon-supervised runner
that performs a textbook self_restart ceremony — `maybe_self_restart`
spawns the successor, worklive phase "restarting", clean `return` from the
main loop, exit 0 — leaves the daemon holding a corpse it will NEVER
replace. Succession survives ONLY because `respawn_self()`
(self_restart.py:160-183) spawns the successor detached BEFORE the elder
exits, and the successor takes the runner lock via generation fencing
("standing down via runner-lock takeover", self_restart.py:196). P3 says
"successor takes the lock at a higher generation" — but never says the
SUCCESSOR MUST BE SELF-SPAWNED BY THE DYING ELDER, because the supervisor
will not spawn anything after exit 0. If any future adoption path lets the
daemon (not the elder) do the respawning — the natural reading of "wire
maybe_self_restart at its loop boundary" for the DAEMON's own slice (P2:
"daemon first") — the first planned rotation of a supervised runner is
also the last: handover-permanent by mechanism.

(c) **The alpha path has no N1.** bifrost_daemon.py:287 comment: "alpha
path: daemon holds the runner lock directly". In alpha mode the daemon IS
the runner host; a metabolism exit of the daemon's own loop is a process
death, and whatever supervises the DAEMON (nothing in-tree — INFER) counts
it. P4's breaker concern is real THERE, not in delta. The brief conflates
two supervision topologies; the fix differs per path.

**Reproduction sketch:** script A (child): set phase file, exit 0.
Parent: ManagedChild around A. After poll() returns 0: `child.tripped` is
False (P4's fear refuted), `child._next_spawn_at == inf` and
`child.spawn()` returns None forever (the real bug proven). Then
`child._tripped = False; child._next_spawn_at = 0; child.spawn()` — the
ONLY recovery is external mutation of supervisor state, i.e. a human.

**Severity: FIRST-SIGN for the drill.** P6's rolling-refresh drill with
before/after PIDs catches this instantly (runner pid never returns). Which
means: as specced, the FIRST run of the acceptance drill has a known-fail
mode unless the design names the respawn owner.

---

## R3 — P5's in-flight contracts have hole(s) you can drive a reply through [V3, VERIFIED + INFER]

P5 lists: runners gate on in_flight (exists — `should_restart(...,
in_flight)`, self_restart.py:75-76). The gateway gates on
"relay-in-progress AND a non-empty ladder op queue". Verified against
`scripts/bifrost_runner_discord.py`:

(a) **The ladder tracker is process-memory.** `_ladder_msgs` dict
(line ~420, 438, 442: `entry = _ladder_msgs.get(op["discord_msg_id"])`,
pops on terminal/NotFound). The op QUEUE source is polled from bus meta
(ladder poll at ~407-415), but the message-handle mapping
(discord_msg_id -> discord Message object) is in-RAM. A metabolism restart
of the gateway mid-ladder loses the MAPPING even if the queue is durable:
the successor re-polls ops for messages it can no longer resolve to
channel/message objects [VERIFIED the in-RAM dict; INFER that op payloads
lack a re-fetch path — the tracker stores Message objects, not
(channel_id, message_id) pairs with rehydration]. P5's "gates on non-empty
ladder op queue" prevents restarting DURING a pending op, but a restart
between ✅-posted and the next op generation still orphans the tracker.
Loss named: **ladder reaction state for every message heard in the current
process lifetime** (T380's receipt chain — the exact feature Daniil asked
for by name — silently stops advancing on all in-flight conversations).

(b) **Reply-in-progress is NOT gated by anything in P5's list.** The
gateway's outbound path (send at ~497: "send FAILED") is not in the P5
gate list — the list covers relay-IN (inbound enqueue) and ladder ops, not
a reply being composed/posted to Discord at the moment of rotation. A
wedged-trigger restart (Q1's discriminator mis-fires during a long discord
API call — heartbeat-blocked warning threshold is 10s per line 72's
comment) kills the process between bus-read and discord-post:
**duplicate on respawn** (bus expectation still armed, redrive fires,
RB-29) or **silent loss** (reply posted, ack not written). [INFER —
depends on where the ack lands, which I did not verify this round.]

(c) **Runners: in_flight gates the TURN, not the SPAWN.**
bifrost_runner_discord.py owns a sprout subsystem (spawn at ~313, "SPAWN
STILLBORN" tracking at ~310-362, "still breathing after" at ~349). A
gateway or daemon restart while a sprout is mid-flight orphans the
stillborn-watch: the stillbirth notice path ("could not reach the loop to
confess" ~362) already confesses fragility TODAY. P5's daemon gate covers
"child-spawn-in-progress" (good) but the GATEWAY's sprout-in-progress is
unnamed in the contract. [VERIFIED the sprout exists in the gateway;
INFER that P5's gateway gate omits it.]

**Severity: (a) LOAD-BEARING (it eats today's shipped feature), (b)
SENSITIVE, (c) SENSITIVE.**

---

## R4 — Q2: under a Discord reconnect race, BOTH lock shapes lose the ear in one direction or double it in the other [V4, INFER on mechanism, VERIFIED on absence]

Verified absence: no singleton lock exists in the gateway today (brief
says verify; grep across scripts/ for the gateway holding any lock:
nil — the only lock machinery is DaemonLock (bifrost_child.py:33) and
runner_lock.py, neither referenced by bifrost_runner_discord.py).

The race Vandor asked me to break: reconnect storm while a successor is
mid-rotation. Discord.py's internal reconnect resumes the session on the
SAME websocket generation; the process holds no fence token Discord-side.
Two processes each running `client.start(token)` both receive dispatch
events — Discord delivers to every connected shard/session; the
idempotency must be OURS [INFER: standard gateway semantics; the R1
allowlist listener at ~450 and on_message enqueue at ~549 contain no
dedupe-by-generation visible in this pass].

Sequence: (1) elder gateway starts planned rotation, spawns successor;
(2) successor acquires `bifrost:daemon:discord`-shaped lock (whatever
shape wins Q2); (3) elder's discord.py client is still inside its
auto-reconnect backoff — it has NOT exited, because client.start()
owns its own reconnect loop and does not know about our lock; (4) both
processes' on_message fire for the same Discord message; (5) both enqueue
to the bus. The inbound dedupe is by sha/reply_id per T039a — **but two
gateway processes generate DIFFERENT bus ids for the same Discord message
id** [INFER: enqueue at ~549 stamps a fresh bus id; the Discord message id
rides in meta (discord_msg_id at ~526) — dedupe key availability at the
CONSUME side unverified]. The ladder's reaction bookkeeping (R3a) then
double-reacts or splits state across two process memories.

The killing observation: **the lock only serializes OUR side. It does not
revoke the elder's EAR.** Any lock shape (runner_lock reuse, DaemonLock,
third thing) must be paired with an explicit `client.close()` in the
elder BEFORE lock release, and the fencing check must sit INSIDE the
discord.py event path (per-event lock re-read), not at startup — or the
reconnect race double-relays for the full duration of the elder's
shutdown window. None of the three Q2 candidates states this. [INFER —
the event path (on_message ~544-554) shows no lock re-read; I did not
trace client.start()'s ownership of the event loop this round.]

**Severity: LOAD-BEARING for P2's gateway slice** — "lock-first,
restart-wire second" is right, but the lock alone is half the mechanism;
the elder's ear must be closed by handshake, not by assumption.

---

## R5 — Q5 answer the brief didn't ask me for, but the attack surface demands: the organ refuses anything whose SUPERVISOR it cannot notify [INFER]

P4/P3 presume the worklive phase is the succession channel. R1 shows the
parent never reads it. Until the parent reads the phase (or the breaker
counts codes with a documented exemption), ANY supervised process whose
exit codes are meaningful to its supervisor is a restart the organ must
REFUSE — fail-direction keep-running already covers unknown stamps; add
"unknown supervisor contract". One line, costs nothing, closes R1's hole
while the real mechanism is built.

---

## Could NOT break

- **P1 (extend, don't sibling).** Attacked on the primitives-once claim:
the wedged trigger needs queue-depth + pulse-age inputs self_restart's
pure decision core doesn't take today, so "no new module" means growing
`gather()` — but that is exactly what the module's own shape invites
(self_restart.py:131-158, best-effort holes -> keep-running). The
extension point is honest. Holds.
- **P6 (drill is the receipt).** Tried to construct "drill passes but
system broken": before/after pids + shas don't prove the LADDER survived
(R3a) or that no double-relay occurred during the window (R4). So the
drill as specced is INSUFFICIENT, not wrong — add two assertions (ladder
state continuity across rotation; zero double-enqueue by discord_msg_id)
and it holds. Flagged, not broken.
- **Fail-direction keep-running** (self_restart.py:84-98, P8 try/except
around every input). No path found where a confused sensor forces a
restart; every hole declines. Holds.

## One calibrated question back (per rules of engagement)

For Vandor at reconcile: R2(b) — do you read the N1 `_next_spawn_at=inf`
handover as a FEATURE for delta-mode rotation (daemon deliberately stays
out of the way while the self-spawned successor takes the runner lock),
or as a latent permanent-stand-down? The design's answer decides whether
the daemon slice needs a "reclaim on successor-death" arm or whether
self-spawn-before-exit is load-bearing forever.

## Files verified this round

- scripts/bifrost_child.py:33 (DaemonLock), :120-157 (spawn), :249-270
  (_handle_exit: N1 + breaker), docstring :15-19.
- core/comm/self_restart.py:71-98 (should_restart), :131-158 (gather),
  :160-183 (respawn_self), :185-198 (maybe_self_restart, :191 phase write).
- scripts/bifrost_runner_discord.py:137 (agent id), :310-362 (sprouts),
  :407-444 (ladder poll + _ladder_msgs), :497 (send path), :544-554
  (on_message enqueue).
- scripts/bifrost_daemon.py:178-287 (delta path, breaker callout :277),
  :287+ (alpha path), :515-534 (stand-down/clean exit).
- Nil-greps (VERIFIED absences): gateway holding any lock; bifrost_child
  reading worklive/phase in the supervision path.

— Navi (kimi), fence t376-metabolism half_b. Kills credited at reconcile;
red is a gem.
