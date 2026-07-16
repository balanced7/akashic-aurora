# T086 Seat/Wake/Hook Prior-Art Deep-Dive — DeepSeek half (2026-07-16)

Status: BLIND HALF. Do NOT read research/reviewed/claude-seat-priorart-2026-07-16.md until
reconciliation. Filed 2026-07-16 ~09:45 under the seat-deepdive-directive (Daniel, verbatim).

Charter: "find out what system our mechanism is most like, do a deep dive into the concepts
that make similar production-grade systems robust, and let's implement their fixes."

## 1. REQUIREMENTS — what the wake/seat/hook system must accomplish

Testably defined:

R1. **At-most-one consumer per agent id.** Two runners sharing one Redis cursor silently lose
    mail (the race the runner_lock was built to prevent). The seat MUST guarantee that at most
    one process can advance the cursor at any time.

R2. **Liveness = maintained channel, not forensic inference.** An outsider must be able to
    distinguish "alive and working" from "dead and blocking" WITHOUT building a case — the
    holder emits a heartbeat, and death is the ABSENCE of that heartbeat after a short window.
    Today's C1-1 free_if_dead evidence ladder is good but FORENSIC (300s grace + 900s stale
    = up to 15 min of uncertainty). Production systems make this a 30-60s channel.

R3. **Session-scoped process lifecycle.** A session's armed watchers, standby listeners, and
    runner children MUST die when the session ends. Today's C1-5 (ghost wake seat surviving
    SessionEnd) proves this is not currently enforced. The session is the lifecycle owner;
    its children inherit its lifetime.

R4. **Crash is a first-class event, not a condition to prove.** When a holder dies, the system
    must FREE the seat within seconds (not minutes), with an auditable event, and WITHOUT
    requiring the successor to build an evidence case. Today: the C1-1 evidence ladder is the
    crash path — it works but is slow (grace_s=300s). Design goal: < 60s from crash to
    successor claiming.

R5. **Fencing at the resource, not the lock.** A stale holder (one whose lock was freed but
    whose process hasn't noticed yet) must be UNABLE to corrupt the cursor. We have this today
    (L1b generation fence on cursor writes). This must survive all changes: if we shorten
    TTLs or add faster crash detection, fencing must still hold.

R6. **No silent mail loss.** RB-26 (at-least-once handling) is the contract. If a runner dies
    mid-consume, its successor must redeliver. Today: the cursor is advanced AFTER processing
    (T014), but redelivery dedup is in-memory only → redelivery storms (C1-4).

R7. **Observable state.** The system must answer "who holds the seat, are they alive, is there
    mail waiting, is the consumer wedged" in ONE call. Today: assembled from 3-4 calls. CL-2
    standby consolidates drain+report+arm into one verb; the seat status itself is still
    fragmented.

## 2. CURRENT + GAPS — how it works today and where it breaks

### Architecture: three lock tiers, three keys

```
bifrost:daemon:<agent>     — DaemonLock (bifrost_child.py): singleton guard for the daemon process.
                              Heartbeat-refreshed TTL. Prevents twin daemons from spawning duplicate
                              runner children.

bifrost:runner:<agent>     — runner_lock (core/comm/runner_lock.py): guards the consume path.
                              Held by the runner process (heartbeat every loop iteration, TTL 20s)
                              OR by a CLI session (claim_consumer, TTL 1800s). RB-21 generation
                              fence on cursor writes. free_if_dead (C1-1) probes the evidence
                              ladder and frees crash-held seats.

bifrost_wake_<agent>_<sid>  — wake seat files (wake_seat.py): a .pid file + .alive marker in
                              tempdir. The armed wake listener blocks here. CL-2 standby
                              drains then arms. C1-5: nothing reaps these at SessionEnd.
```

### The gap chain (C1-5 → C1-1 → C1-2 → C1-4)

The morning's live incident (C1-5 + its AMENDED block) is the Exhibit A that connects all gaps:

1. **Session ends.** SessionEnd closes the episode (W8B) and drafts the chronicle. But the
   session's `bifrost-standby` (pids 35536/49316) and `bifrost_wake` child (49252) stay armed.
   → **GAP: no session-scoped teardown of armed watchers (R3 failure).**

2. **Ghost holds the seat.** Next morning: a peer sends mail. The ghost watcher wakes, but its
   session is ended — the mail has nowhere to go. The live morning seat (claude 69d664e5) runs
   standby → `consume_inbox` → seat_held because C1-1's evidence ladder sees:
   - activity marker? Not touched since session end → stale.
   - listener pid? pid 49252 is STILL RUNNING → `listener-alive` → ALIVE verdict.
   → **GAP: the liveness ladder can't distinguish "pid alive" from "session behind pid ended."**
     The watcher process outlives its session. R3 is the root cause; R4 is the symptom.

3. **Interim rule fails.** "Kill the ghost watcher." → Harness Law L1: killing a tracked
   watcher RE-INVOKES the session. The ended session resurrects, re-arms, re-claims the seat.
   → **GAP: process lifecycle is harness-tracked, not session-scoped. The harness doesn't know
     the session ended.**

4. **Seat held by definitely-dead holder.** After the ghost finally ends unarmed, the STALE
   claim on `bifrost:runner:claude` still blocks. 25 standby retries × 20s = ~8 min of
   "seat held." Then free_if_dead ages through grace (300s) → indeterminate → TTL. The agent
   is unwakeable for ~30 min while a provably-dead holder's claim ages out.
   → **GAP: crash detection is FORENSIC, not channel-based. 300s grace + 900s stale = up to
     15 min before the seat frees automatically. R4 failure.**

### T073's partial fix + what's still broken

The T073 wake-robustness reconciliation landed Phase 1 (incarnation protocol) and Phase 2
(WAKE_WORTHY allowlist). These fix twin-wake and noise — but they do NOT touch the seat
lifecycle. The long-lived watcher (Phase 3, parked) would reduce the arm/drain frequency
but doesn't change who holds the seat or how it's freed. The C1-5 ghost-watcher class
survives all of T073: a long-lived watcher from a dead session still holds the seat.

### The daemon (T075 M1-alpha, PARKED)

The daemon code exists (`scripts/bifrost_daemon.py`) and provides the right architecture
for R2-R4: a supervised runner child with circuit-breaker restart, stable identity, and
clean exit on signal. But it's parked behind T047 + its own fence, and it ONLY manages the
runner — it doesn't touch the wake seat or the session standby. The daemon is the right
HOME for session-scoped lifecycle (R3) — it just needs to own the wake/standby children
too, and SessionEnd needs to signal it.

## 3. PRIOR ART — what our system is most like

### Our system IS: systemd-logind session scopes + Kubernetes node leases, hybridized

**systemd-logind**: manages user sessions. Each session gets a scope (cgroup) that tracks
ALL processes launched within it. When the session ends (logout), `KillUserProcesses=yes`
nukes the scope — no orphaned processes. `loginctl enable-linger` allows processes to
survive logout (opt-in, not default). The session ID is carried on every process. SessionEnd
is a single event that cascades to everything in the scope.

→ Our gap: we have NO session scope. Our "session" is a harness concept, not a lifecycle
mechanism. The session's children (standby, wake watcher, runner) don't know they belong
to a session. When the session ends, nothing reaps them.

**Kubernetes node leases**: every kubelet heartbeats into a Lease object in the
`kube-node-lease` namespace every 10s. The node controller watches these leases. If a
lease isn't renewed for `node-monitor-grace-period` (default 40s), the node is marked
`NotReady`. After `pod-eviction-timeout` (default 5m), pods are evicted. The key design:
- Liveness IS renewal. Death IS absence of renewal. Nobody has to prove a node died.
- The lease object is the single source of truth. There's no evidence ladder.
- `spec.renewTime` is updated by the holder; the controller just reads it.
- Fencing: pods are evicted after the grace period; a resurrected node doesn't get them back.

→ Our gap: our "lease" is the `bifrost:runner:<agent>` key with a TTL. But it's FORENSIC —
the successor has to prove the holder is dead (evidence ladder). K8s makes this a CHANNEL:
the holder writes `renewTime`, the successor reads it, and a stale `renewTime` IS the death
signal. We already have the `ts` field on the lock value and a `heartbeat()` that refreshes
it — but free_if_dead doesn't use `ts` staleness alone as a death signal; it builds a
multi-step evidence ladder. The fix: make the holder's `ts` the primary liveness signal,
with a short grace period.

### Three other production systems, mapped

**ZooKeeper ephemeral znodes.** A client creates an ephemeral znode that lives as long as
the client's session. The session is maintained by heartbeat. If the heartbeat stops
(session timeout), ALL ephemeral znodes for that session are AUTOMATICALLY deleted by the
ZK server. This is the ideal pattern for our wake seats: the wake seat file should be an
ephemeral resource tied to the session's lifetime. When the session ends (or crashes), the
seat evaporates. Nobody has to "reap" anything — the server/controller does it atomically.

→ Our gap: our wake seats are temp files, not session-tied resources. Closing the session
doesn't delete them. C1-5 is the direct consequence.

**Erlang/OTP supervisor trees.** Processes are organized into supervision trees. A
supervisor spawns children with a restart strategy (`one_for_one`, `one_for_all`). If a
child crashes, ONLY the supervisor restarts it — the restart policy is centralized. A
child never restarts itself. The supervisor's own lifecycle governs the subtree: kill the
supervisor, the whole tree dies.

→ Our gap: our "children" (standby, wake watcher, runner) are spawned by different
parents (harness hooks, the daemon, CL-2 standby). No single parent owns the full subtree.
The daemon SHOULD be the supervisor — but it only manages the runner child. The wake
watcher and standby are spawned ad-hoc. Harness Law L1 (only a session can re-invoke a
session) is the inverse of OTP: the CHILD restarts the PARENT, not the other way around.

**Redis Redlock + Kleppmann fencing tokens.** The key insight from Martin Kleppmann's
critique of Redlock: a lock without a fencing token is unsafe. Even if the lock TTL is
correct, a paused process (GC, network blip) can wake up after its lock expired and
corrupt the resource. The fix: every lock acquisition mints a MONOTONIC fencing token,
and the RESOURCE (not the lock) validates it. If a write arrives with token N but the
resource's stored token is N+1, the write is REFUSED.

→ Our implementation: RB-21 L1b already does this. `_TENURE_GEN` mints a generation on
every `acquire()`, and the guarded cursor Lua (`bus.py:669`) checks `gen < stored →
STALE_GENERATION`. This is textbook Kleppmann and is the single best-designed part of our
seat system. It must survive ALL other changes.

## 4. FIX CLASSES — slice-shaped, with prior-art concepts and pre-registered pins

### FIX-CLASS A: Session-scoped process lifecycle (systemd-logind scopes + ZK ephemeral znodes)

**Concept:** Every process spawned by a session carries the session ID. SessionEnd is a
CASCADING event that terminates all children in the session scope. ZooKeeper ephemeral:
the wake seat is a session-tied resource; when the session ends, it auto-deletes.

**Slice: session_scope.** `session_exit.py` clean_death (T075 M1-beta) already reaps the
activity marker and listener pid file. Extend it: BEFORE deleting those files, SEND a
shutdown signal to the standby/wake processes carrying that session_id. The signal is
SIGTERM → wait 2s → SIGKILL (the systemd pattern). The harness respects the signal;
Harness Law L1's resurrection is suppressed because the session itself is ending
(contrast: killing from outside the session triggers L1; the session ending itself is
the ONE valid shutdown path).

**Pin A1:** `test_session_end_reaps_standby_child` — start a standby, end the session,
assert standby pid is gone within 3s.

### FIX-CLASS B: Liveness as a maintained channel (K8s node leases)

**Concept:** The seat holder writes `renewTime` on every heartbeat (already happening!).
A successor reads `renewTime` and compares against NOW. If `renewTime + lease_duration <
NOW`, the seat is FREE — no evidence ladder needed. The lease_duration is SHORT (30-60s
for runners; 300s for CLI sessions — they can't heartbeat at 10s intervals). The C1-1
free_if_dead evidence ladder stays as the BACKSTOP for when the lease check is
inconclusive (network partition, clock skew), but the FAST PATH is the lease staleness
check.

**Slice: lease_channel.** `runner_lock` gains a `LEASE_TTL` (60s for runners, 300s for
sessions). `heartbeat()` writes `renewTime` into the lock value. `free_if_dead` checks
`renewTime` FIRST: if `renewTime + LEASE_TTL < now` → seat is FREE (fast path, no
evidence ladder). If lease is fresh → evidence ladder (slow path, unchanged). Adds a
`is_lease_current()` helper.

**Pin B1:** `test_fresh_lease_not_freed` — heartbeat every 10s, try to free after 30s;
seat still held.
**Pin B2:** `test_stale_lease_freed_fast_path` — stop heartbeat, wait `LEASE_TTL+1`, free
succeeds instantly (no grace/stale gates).

### FIX-CLASS C: Single supervisor owns the subtree (OTP supervisor trees)

**Concept:** The daemon (or the session's main process) is the supervisor. ALL children
(standby, wake watcher, runner) are spawned as managed children with a restart strategy.
When the supervisor dies, the subtree dies. No child outlives its parent.

**Slice: daemon_supervisor.** The daemon (`bifrost_daemon.py`) becomes the single parent
for: (a) the runner child (already), (b) the standby listener (new — the daemon calls
CL-2 standby's listen path), (c) the wake watcher (moved from harness-hook-spawned to
daemon-managed). The daemon listens for SessionEnd via the existing signal handler;
on SessionEnd, it terminates all children (Fix-Class A). The daemon's own lifecycle
is governed by the launcher.

**Pin C1:** `test_daemon_children_die_on_sigterm` — send SIGTERM to daemon, assert
runner + standby + wake pid are gone within 5s.

### FIX-CLASS D: Durable reply dedup (Kafka consumer offsets)

**Concept:** Kafka consumers commit offsets durably. On restart, they resume from the
last committed offset — no redelivery of already-handled messages. We need the same
for the runner: a durable record of "I answered message X" that survives restart.

**Slice: reply_dedup.** The `reply_sent` prefix in `bifrost_runner_deepseek.py:84` is
already the right shape. Make it durable (write to the Store, not just in-memory dict).
On consume, before answering, check: has this message ID been answered? If yes → skip
(emit a note, don't re-answer). This closes C1-4 (redelivery storms) without changing
the cursor commit behavior.

**Pin D1:** `test_reply_dedup_survives_restart` — answer a handoff, kill the runner,
restart, same handoff redelivers; second runner skips it.

### FIX-CLASS E: Observable seat state (CL-2 standby report, extended)

**Concept:** `bifrost-standby` already reports drain + seat state. Extend it to answer:
"who holds the seat, lease age, liveness verdict (fresh/stale/dead), pending mail count,
expectations sweep result" — the full R7 one-call interface. Builds on CL-2's report
block with the lease staleness data from Fix-Class B.

**Pin E1:** `test_standby_report_includes_lease_age_and_verdict` — standby output
includes "lease: fresh (12s)" or "lease: stale (67s, fast-free eligible)."

### Sequencing

A (session scope) → B (lease channel) → E (observable state) → C (daemon supervisor) →
D (reply dedup). A must land first: C1-5 is the live incident and A closes the class.
B makes the crash path fast. E makes everything observable. C is the structural fix
(daemon owns the subtree). D closes C1-4.

## 5. LOOP-ALTITUDE THESIS

"Our seat system confuses liveness (is the holder alive?) with lifecycle (who owns the
holder's processes?). Production systems keep these separate: systemd owns the lifecycle
(session scopes); K8s leases own the liveness (heartbeat channel). We need to adopt both:
session-scoped process groups + lease-as-channel, then the evidence ladder becomes a
backstop, not the primary path."

## TOP 3 PRIOR-ART CONCEPTS

1. **K8s node leases — liveness as renewal channel.** The holder writes `renewTime`;
   death = stale `renewTime`. 30-60s, not 300s. Free the seat when the lease expires,
   not when the evidence ladder completes. Keep the ladder as the BACKSTOP.

2. **systemd-logind session scopes — lifecycle cascade.** Every process is session-tagged.
   SessionEnd kills the scope. No ghost watchers. Solves C1-5 at the root.

3. **ZooKeeper ephemeral znodes — auto-delete on session end.** The wake seat file is an
   ephemeral resource. When the session ends (or crashes), it vanishes automatically.
   No reaper needed. The same mechanism should govern all session-tied Redis keys.
