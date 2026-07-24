---
akashic_id: art_20260716_t086-seat-wake-hook-lifecycle-prior-art_75f68b
akashic_sha: 14c7180cd37a
status: draft
type: report
date: 2026-07-16
title: "T086 — Seat/Wake/Hook Lifecycle: Prior-Art Grounding (claude half)"
gist: "until your own half is committed. Reconciliation follows both halves; the reconciled doc is the build spec (method-baseline). Directive: not"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_agent-liveness-tier-stuck-lost-agent-fai_8c0d79
    rel: cites
created: "2026-07-16T09:28:41"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260716_t086-seat-wake-hook-lifecycle-prior-art_75f68b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T086 — Seat/Wake/Hook Lifecycle: Prior-Art Grounding (claude half)

until your own half is committed. Reconciliation follows both halves; the reconciled doc
is the build spec (method-baseline).

Directive: note `seat-deepdive-directive` (Daniel verbatim, 2026-07-16 morning).
Method: docs/pillar-analysis-method.md (triangulate → loop-altitude thesis → evidence-
disciplined fixes). Triangulation sources: t073-wake-reconciliation-2026-07-15.md +
docs/agent-liveness-tier-2026-07.md (H1–H6) + docs/failure-ledger-2026-07.md (C1 category)
+ THIS MORNING's live incident chain (C1-5 + amendments — receipts inline below).

---

## Part 1 — What must this system accomplish (requirements, stated testably)

R1 **Reachability.** A work-lane message addressed to an agent reaches a LIVE seat of that
agent in bounded time: seconds when an armed seat exists; one cold-start when none does.
R2 **Single consumer.** At most one session per agent id moves the work-lane cursor at any
instant (no double-consume, no cursor splits).
R3 **Fast failover.** When the consuming seat dies — gracefully OR by crash — takeover
completes in seconds-to-one-minute. (Receipt of current failure: ~30 min unwakeable this
morning while a dead holder aged out.)
R4 **No loss.** At-least-once delivery with idempotent consumers (RB-26); a crash between
read and process must redeliver (liveness-tier H1 — still open, T030).
R5 **Wake = work.** Idle seats wake only for wake-worthy work-lane kinds (T073 P2 ratchet
shipped). Noise floor zero.
R6 **Zero babysitting.** No human action and no model discipline in the arming loop
(Daniel's T073 verbatim: "how do we automate it so you don't have to worry about it").
The mechanism must self-maintain across arbitrary session churn.
R7 **Observability + audit.** Who holds which seat, why, since when — one glance; every
ownership transition is a durable event.
R8 **Session-bounded lifetime.** Everything a session arms dies with the session. A ghost
(armed process or live claim from an ended session) must be unrepresentable.

The loop, end to end: send → route → lane → wake → re-invoke → claim seat → drain →
work → reply/settle → re-arm → idle. The system fails whenever any link breaks AND no
layer confesses at the timescale the sender waits on (liveness-tier framing, held to).

## Part 2 — What it currently does, and the gaps (receipts)

Mechanism today: per-session `bifrost_wake` listener (lane-filtered, detect-don't-consume,
T017) armed as a harness background task whose exit re-invokes the session (Harness Law
L1); turn-end `bifrost-standby` = drain → seat report → block as listener parent (CL-2);
consumer seat = `runner_lock` claim, TTL 1800s, 300s grace, C1-1 evidence ladder
(free_if_dead) on the next claimant's refusal path; stop-hook as watcher-death backstop
(T073 Phase 3); doctor L2 progress-not-presence; daemon (supervisor) PARKED with T075.

Gaps, each with its receipt:

G1 **Session-scoped processes, no session-scoped teardown.** The overnight session ended
08:47; its standby+wake stayed armed holding the seat (C1-5, live today). Violates R8.
G2 **Task-exit resurrection is unconditional.** Killing the ghost's tracked watcher
RE-INVOKED the ended session, which re-armed and re-claimed the seat 8s before my standby
(live today, C1-5 amendment). L1's inverse applies to DEAD sessions — the current design
never states this.
G3 **Liveness is forensic, not maintained.** The seat claim is a passive record; holder
death is PROVEN by the next claimant walking grace(300s) → indeterminate → TTL(1800s).
Receipt: a 25×20s standby retry loop exhausted against a definitely-dead holder;
unwakeable ~30 min. Violates R3. [V1 CONFIRMED — task output on file]
G4 **No election/takeover protocol.** Contenders poll and race; no deterministic handover,
no rank (a live interactive seat cannot outbid a headless zombie). Receipt: lost the 8s
race this morning. [V2 CONFIRMED]
G5 **Seat actions are not epoch-fenced.** RB-21 generations exist on RUNNER locks; the
session consumer seat has token-matched release but (as far as I verified today) no
monotonic epoch checked at consume/cursor-advance time — a resurrected zombie that
re-claims can consume as if current. [V3 PLAUSIBLE — needs a code pass on runner_lock.py
+ consume_inbox before reconciliation treats it as fact]
G6 **No supervisor.** The daemon that owns arm/consume ordering is parked (T075-γ/T077);
re-arming rides model discipline + a stop-hook nag. Violates R6. Receipt: the backstop
fired on me today WHILE a retry loop was in flight (no dedup between backstop and
in-flight contention — the nag can't see the queue). [V4 CONFIRMED]
G7 **At-most-once consume window.** H1 (cursor advances at read) remains open at the
consume seam; T030 unbuilt. Violates R4. [V5 CONFIRMED by code-read lineage in
liveness-tier doc; not re-verified today]
G8 **Hooks teach but cannot repair.** L1 means the hook layer detects unwakeability and
demands the MODEL fix it — correct as a backstop, but it is currently the PRIMARY
re-arm path after any watcher death. Violates R6.

What already matches production practice (credit, keep): lane separation ≈ topic
partitioning; detect-don't-consume ≈ watch-vs-take; WAKE_WORTHY allowlist inversion ≈
default-deny subscription filters; RB-21 generations = correct fencing on the runner
seam; the C1-1 evidence ladder is a reasonable FALLBACK — it is only wrong as the
primary liveness mechanism.

## Part 3 — What is this system most like, and how the real world solved it

**Closest single frame: a single-consumer message group with lease-based leadership and
on-demand (socket-activated) workers.** Three production families each solved one of our
three subproblems; we hand-rolled all three at once and inherited none of their load-
bearing properties.

**A. Coordination services — ZooKeeper / etcd / Chubby / k8s leader election.**
The seat IS a lease-based leader election. The concepts we lack:
- *Ephemeral ownership bound to a liveness channel* (ZK ephemeral znode dies WITH the
  session; etcd lease keepalive): the claim is not a record to be disproven later — it is
  a subscription that lapses the moment the holder stops maintaining it. C1-5 becomes
  unrepresentable.
- *Incumbent-side step-down deadline* (k8s LeaseDuration / RenewDeadline / RetryPeriod):
  the HOLDER must renew by RenewDeadline or stop acting; challengers acquire
  deterministically after LeaseDuration. Responsibility for death-detection moves from
  the arriver (our forensics) to the incumbent (their contract). This is the single
  biggest inversion we need.
- *Death as a watchable EVENT* (ZK watches, etcd watch on the lease key): contenders
  don't poll; they are notified. Our sig lane already exists to carry exactly this.
- Chubby's paper also names our jeopardy/grace tradeoff — grace exists to ride out
  keepalive BLIPS of a live holder, not to protect the claims of dead ones.

**B. Kafka consumer groups — the closest wire-level analog.**
Stable agent id + many incarnations = static group membership (`group.instance.id`) with
rebalance on change. Concepts we lack:
- *Generation/epoch fencing*: every ownership change bumps a generation; commits from an
  old generation are REFUSED. Our zombie re-claim this morning is Kafka's textbook
  zombie-consumer case, solved by epochs, not by liveness guesses. (Kleppmann's
  Redlock critique is the same argument: without fencing tokens, TTL locks are unsafe
  no matter how good the clocks are.)
- *Three separate timeouts for three separate questions*: session.timeout (reachable?
  — background heartbeat), max.poll.interval (progressing? — work loop), rebalance
  timeout (handover bound). We conflate all three into one activity marker + TTL.
  Doctor L2 already wants this split (progress-not-presence); the seat should too.
- *Cursor advance after processing* (commit AFTER work) — H1's fix shape, with SQS
  visibility-timeout as the redelivery model.

**C. Supervision & activation — systemd / Erlang-OTP / inetd.**
- *Session scopes* (systemd-logind cgroups): every process a session spawns lives in its
  scope and is reaped at logout unless it explicitly lingers. G1's fix is a teardown
  CONTRACT, not a cleanup script.
- *Monitors deliver death as a message* (OTP `monitor` → DOWN message): the peer's death
  arrives on the SAME bus work does. Our daemon-as-janitor can emit `seat_expired` /
  `watcher_orphaned` events onto the sig lane — supervision without violating Harness
  Law L1 (it cannot re-arm sessions; it CAN observe, reap, free, and escalate).
- *Watchdog inversion* (systemd WatchdogSec): the SERVICE pings the supervisor; silence →
  supervisor acts. Today our stop-hook nags the MODEL; production inverts the direction.
- *Socket activation* (inetd/systemd): the always-on listener belongs to the durable
  supervisor; workers spawn per event. T073 correctly refuted dispatcher-as-waker (L1);
  the honest adaptation is listener-stays-per-session, SUPERVISION moves to the daemon.

**Loop-altitude thesis (one sentence):** every failure in this class traces to
liveness-as-forensics and lifecycle-as-convention — claims outlive sessions, death must
be proven by the next arriver, and re-arming rides model discipline — where production
systems bind claims to heartbeat channels the incumbent must maintain, emit death as an
event contenders subscribe to, and give lifecycle to a supervisor process.

## Part 4 — Fix classes (slice-shaped; each names its prior-art concept and its pin)

F1 **Ephemeral seats** (ZK/etcd/k8s lease): seat record gains {holder_session, epoch,
renewed_at, renew_deadline}; holder renews every ≤60s from the armed watcher's block loop
(zero new processes — the watcher IS the keepalive); miss renew_deadline → holder must
stop consuming (step-down contract); expiry emits `seat_expired` on the sig lane.
Pin: kill -9 the holder → a contender claims in ≤90s (vs ~30 min today).
F2 **Seat epochs / zombie fencing** (Kafka generation + fencing tokens): monotonic epoch
bumps on every claim; consume/ack/cursor-advance carry it; stale epoch → REFUSED loud.
Pin: a resurrected zombie with a stale epoch cannot move a cursor (replay today's C1-5
as the regression drill).
F3 **Session-scoped teardown** (systemd scope): SessionEnd reaps this session's armed
watchers and RELEASES its seat claims (release > expiry, always). Pin: C1-5
unrepresentable — no armed process outlives its session beyond one block-chunk.
F4 **Daemon as supervisor-janitor, not waker** (OTP monitor + socket-activation split,
honoring the T073 dispatcher verdict): census armed watchers vs live sessions; reap
orphans; free their seats; emit death/orphan events; escalate "no wakeable seat exists"
to a Daniel-visible surface. Never arms a session (L1 stands).
F5 **Three-timeout split** (Kafka): reachable (heartbeat fresh) / progressing (worklive
age, H2's unread reader) / handover bound (<60s target) — three dials, three alarms,
doctor renders all three.
F6 **Consume-after-process** (SQS visibility): H1/T030 at-least-once at the consume seam.
F7 **Backstop dedup**: stop-hook consults the contention/arming state before nagging.
Pin: the nag never fires while an arming attempt or retry loop is in flight.

Sequencing sketch (reconciliation decides): F3+F1 first (they kill today's class at the
root), F2 rides F1's record change, F7 is trivial, F5/F4 next block, F6 = T030 claimed
into this arc. Everything kill-switched + fail-open per pillar §12; every slice replays
this morning's incident chain as its regression drill.

## Honest bounds

- G5/V3 is PLAUSIBLE, not confirmed — needs a code pass before the reconciled spec
  treats it as fact.
- I have not web-verified parameter names/defaults quoted from ZK/etcd/k8s/Kafka;
  concepts are load-bearing here, not the exact numbers. DeepSeek's half carries live
  web grounding (his research_note cache) — divergence there is signal, not error.
- The ccd send_message channel (T073 P13) remains the only seatless-session channel;
  nothing in F1–F7 changes that.
