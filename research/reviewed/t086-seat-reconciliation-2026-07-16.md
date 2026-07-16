# T086 Seat/Wake/Hook Lifecycle — Reconciliation (claude ⋈ deepseek) — 2026-07-16

Status: reconciled build spec (halves: claude-seat-priorart-2026-07-16.md,
deepseek-seat-priorart-2026-07-16.md). Build cites THIS document. Daniel's directive
verbatim in note `seat-deepdive-directive`. Method: pillar-analysis-method.md.

## The answer to Daniel's question

Our mechanism is a **single-consumer message group with lease-based leadership and
on-demand workers** — concretely: systemd-logind session scopes + Kubernetes node leases,
hybridized (deepseek's framing), with Kafka consumer-group fencing at the cursor already
built (RB-21 L1b — textbook Kleppmann, keep at all costs).

## Reconciled thesis (both halves converged blind)

**Liveness and lifecycle are two different problems and we solved neither as itself.**
Liveness must be a maintained channel (holder renews; death = stale renewal, detected in
seconds), not forensic inference by the next arriver (today: 300s grace → indeterminate →
1800s TTL ≈ 30-min unwakeable windows, receipt on file). Lifecycle must be a session-scoped
cascade (SessionEnd kills the scope; a ghost watcher is unrepresentable), not a convention
the model remembers. The C1-1 evidence ladder stays as BACKSTOP; the lease check becomes
the fast path. Fencing (RB-21) already guards the cursor and survives every change here.

## Blind convergences (adopted without debate)

1. **Lease-as-channel** (claude F1 = deepseek B): holder writes renewTime on heartbeat;
   successor frees on `renewTime + LEASE_TTL < now`. Tiers: runner 60s, CLI/harness session
   300s. Ladder = backstop only.
2. **Session-scoped teardown** (claude F3 = deepseek A): SessionEnd cascades to the
   session's armed watchers and claims. Target: C1-5 unrepresentable.
3. **ZK ephemerality** (both): wake-seat files + session-tied keys evaporate with their
   session rather than being reaped by cleanup code.
4. **Observable seat state in one call** (claude F5/R7 = deepseek E): extend the CL-2
   standby report with lease age + liveness verdict + pending count; doctor renders the
   reachable/progressing split (worklive age = H2's long-missing reader).
5. **Fencing already correct** (deepseek §3 resolves claude V3-PLAUSIBLE): RB-21 L1b
   generation fence at the guarded-cursor Lua is Kleppmann's fencing token, at the
   resource. Build-time task: audit epoch coverage of any OTHER seat-scoped write doors;
   extend only where a gap is proven.

## Divergences, resolved

**D1 — Who owns the watcher (deepseek C: daemon supervises everything; claude F4: daemon
is janitor only).** RESOLVED BY SEAT TYPE. Harness Law L1 stands: only a session-launched
background task can re-invoke that session — so for HARNESS seats the wake watcher MUST
stay session-spawned; the daemon supervising it would orphan the wake path. For the RUNNER
seat there is no harness re-invoke: deepseek's daemon-as-supervisor is correct and is the
T075 M1 architecture. Split: **runner subtree → daemon-supervised (OTP one_for_one);
harness watchers → session-spawned + daemon-as-janitor** (census armed watchers vs live
sessions; reap orphans; free their seats; emit `watcher_orphaned`/`seat_expired` events on
the sig lane; escalate "no wakeable seat" to a Daniel-visible surface; NEVER arms sessions).

**D2 — SessionEnd kill mechanism (deepseek A: SIGTERM cascade, resurrection "suppressed
because the session is ending" — hypothesis; claude receipt: killing a tracked watcher
RESURRECTED an ended session TODAY).** RESOLVED: mechanism-of-record is the **session
tombstone**, not signal games. What actually worked this morning was durable state (the
ghost read C1-5 in the ledger and stood down). So: SessionEnd writes `session:ended:<sid>`
(tombstone) FIRST, then reaps. Every watcher/standby checks the tombstone at spawn AND at
wake: tombstoned → release claims, exit silently (a resurrected turn reads it and ends
unarmed — no judgment required). free_if_dead consults the tombstone FIRST: tombstoned
holder = DEAD, skip grace entirely (this alone would have cut today's 30 min to seconds).
SIGTERM cascade stays as the cleanup attempt; the tombstone is the correctness guarantee.

**D3 — Reply dedup vs at-least-once (deepseek D vs claude F6/H1).** BOTH, distinct slices:
D closes C1-4 (durable answered-set, Kafka committed-offset shape) now; H1's in-flight
redelivery window stays T030's charter, cross-referenced, not duplicated here.

**D4 — Backstop dedup (claude F7, harness-side; absent from deepseek's half — invisible
from his seat).** ADOPTED: the stop-hook consults contention/arming state before nagging
(it fired mid-retry-loop today).

## Build slices (order, owner, pre-registered pins)

**S1 — Tombstone + SessionEnd cascade** (claude lane: claude_sessionend.py, wake_seat.py,
runner_lock.py; deepseek cross-verifies).
Pins: S1a ghost-drill — end a session with an armed standby; watcher gone or self-retired
≤3s; seat FREE immediately (tombstone path, no grace). S1b resurrection-drill — force a
task-exit re-invoke of an ended session; the resurrected turn reads the tombstone and ends
unarmed touching nothing (replay of this morning as regression). S1c fail-open — tombstone
store unreachable → behavior identical to today (never blocks a live session).

**S2 — Lease fast-path in free_if_dead** (claude lane; deepseek cross-verifies; his pins
B1/B2 adopted verbatim).
Pins: B1 fresh-lease-not-freed; B2 stale-lease-freed-instantly (no grace/stale gates);
S2c ladder-backstop-preserved when renewTime missing (legacy holders).

**S3 — Backstop dedup** (claude lane, trivial): stop-hook nag suppressed while an arming
attempt/contention is in flight. Pin: no nag during an active retry/claim window.

**S4 — Observable seat state** (joint: standby report + doctor + bifrost_dashboard).
Pin E1 (deepseek, verbatim): report includes "lease: fresh (12s)" / "stale (67s,
fast-free eligible)"; plus reachable-vs-progressing split rendered (worklive age).

**S5 — Runner subtree under daemon supervision** (deepseek lane; claude cross-verifies;
UNPARKS the relevant scope of T075-γ under this arc's fence). Pin C1 (his, verbatim):
SIGTERM to daemon → runner + standby + wake children gone ≤5s.

**S6 — Durable reply dedup** (deepseek lane). Pin D1 (his, verbatim): answered handoff
redelivered after runner restart is skipped with a note, not re-answered.

**S7 — Epoch-coverage audit** (claude lane, audit-then-extend): enumerate seat-scoped
write doors; prove RB-21 coverage or extend; pin per gap found (replay C1-5 zombie
re-claim as the drill for any door extended).

Sequencing: S1 → S2 (kills today's class at the root, then makes crash-freeing fast) →
S3 (trivial) → S4 → S5/S6 (parallel, per-lane) → S7. Everything kill-switched + fail-open
(pillar §12); every slice replays the morning's incident chain as its regression drill.

## Honest bounds

- L1-resurrection semantics under SessionEnd remain empirically fuzzy (D2) — S1b's drill
  settles them; the tombstone makes correctness independent of the answer.
- Lease tiers (60s/300s) are engineering estimates, not replay-calibrated; S2 lands them
  as env dials (AKASHIC_LEASE_TTL_RUNNER/_SESSION) and doctor observes real renewal
  cadence before we tighten.
- deepseek's half is web-era-current on k8s/systemd/ZK parameter names; claude's quotes
  concepts from training — where they disagreed on numbers, his cited values won.
