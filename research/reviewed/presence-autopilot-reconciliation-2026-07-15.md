# Presence Autopilot — Reconciliation (claude ⋈ deepseek) — 2026-07-15

Status: reconciled design. Halves: deepseek-presence-autopilot-2026-07-15.md
(BLIND) + claude-presence-autopilot-2026-07-15.md (BLIND — written before his
landed; both are clean, first fully-blind fence since the t060 exposure).
Daniel directive verbatim in note `presence-autopilot-directive`. Build slices
cite THIS document.

## Convergences (both halves blind → strong evidence)

1. **The daemon is the autopilot** — sole owner of arm/claim/stand-down; the
   operator's surface shrinks to "start the daemon once" (his §2, my thesis).
2. **Trigger FILES are the daemon⇄stop-hook control surface** — we converged on
   the mechanism from opposite directions, which is the strongest possible
   signal: his `.rearm` (stop-hook → daemon: "spawn me a listener") and my
   `.trigger` (daemon → session: "mail waiting") are the SAME pattern, both
   directions ship. Filesystem is the queue; 0.2s tick bounds latency.
3. **Stop-hook transforms, never dies** — `daemon_is_live()` fast-path (one
   Redis GET) when the daemon runs; byte-identical legacy path when it doesn't;
   promise audit + K7 stamp survive forever. Kill switch AKASHIC_DAEMON_WAKE=0.
   His once-per-session LATCHED nag ("start the daemon") adopted — nudge, not
   block.
4. **Marker janitor lives in the daemon** (always-on, sees all its agent's
   markers; the session hook only sees its own).
5. **Presence card `runtimes` field is the status surface** — no new keys, no
   new dashboard; read_cards/whisper/doctor already render cards. Runner-down
   becomes visible in ≤8s (one heartbeat) instead of 6h.
6. **Ruling 1 untouched**: the autopilot supervises; it never consumes.

## Rulings on divergences

R1. **Marker-sweep threshold: his 30min is WRONG, and today's reap log proves
    it** — claude's own LIVE session sat at 46m-stale markers this afternoon
    (K7 idle-session immunity exists for exactly this). A 30min sweep would
    erase idle-but-alive sessions from sibling visibility. RECONCILED RULE:
    sweep a marker only when (a) NO matching `.pid` seat exists for its sid AND
    (b) age > 24h. Seat-aware + generous — markers are cheap; ghost siblings
    and broken K7 fast-paths are not.

R2. **Session wake signal: his ccd-channel claim (V4 "CERTAIN") is a
    future-target, not a fact** — `mcp__ccd_session_mgmt__send_message` is a
    tool SESSIONS call; no daemon-side (plain python) caller is named in his
    half. M1-PV discipline: the claim needs a live probe before A2 builds on
    it. GATE: A2 opens with a 15-minute probe — can an external process
    deliver a message that re-invokes an idle session? If YES → his ccd path
    (cleaner). If NO → claude's fallback: one TINY harness-tracked waiter per
    session (200ms trigger-file poller, no bus imports, no seat, immune to the
    seat-write race) — the harness re-invoke coupling is preserved with a
    process two orders of magnitude simpler than the listener.

R3. **His listener-adoption path ADOPTED** (daemon wraps a harness-spawned
    listener via PID-only monitor) — claude's half lacked it; it makes the
    strangler window seamless.

R4. **Storm hygiene (T076, approved) joins the wave as its own slice** — his
    half scoped it out; Daniel's directive scopes it in. Auto-settle consults
    task state at the expectations sweep (RB-29 compatibility is the slice's
    first pin); the skip verb stays a HUMAN/super-admin verb forever (claude V5,
    unopposed).

R5. **Benign-exit semantics carry over from δ N1 unchanged** — a listener that
    woke its session stays down until the next `.rearm`; no respawn churn.

## Reconciled slice plan (strangler; pins pre-registered RED per slice)

| Slice | What | Owner | Ledger |
|---|---|---|---|
| A1 | Autopilot core: `daemon_is_live()` + stop-hook fast-path & latched nag + `.rearm` poll→spawn + seat-aware marker janitor (R1 rule) + card `runtimes` field | claude builds, deepseek verifies | T075 (γ-scope) |
| A2 | Listener as ManagedChild + wake-signal per R2 probe outcome + adoption path (R3) | claude builds, deepseek adversarial-drills | T075 (γ) |
| A3 | Runner-down visibility: doctor flag + whisper SIBLINGS render + 10-min re-escalation broadcast | deepseek builds, claude verifies | T077 |
| A4 | T076 storm hygiene: pending gauge (deepseek) + ledger-closed auto-settle at expectations sweep (claude — scarred-seam adjacency) + `bifrost-skip-to-now` verb (claude, ACL-gated) | split as noted | T076 |
| A5 | Adopt-and-forget polish + one-page runbook + ε handoff (Task Scheduler starts daemons) | joint | T077 |

## What deliberately does not change (union, no dissent)

bus.py, runner_lock.py, consume path/cursors, wake listener watch() internals,
seat-file convention, clean-death trio, incarnation cards, ManagedChild class,
TTL crash nets, kill-switch doctrine, quarantine (no daemon for quarantined ids).

## Confidence

Convergences: HIGH (blind double-hit on mechanism level). R1: HIGH (live
evidence same-day). R2: the probe decides — both branches are buildable. A1 is
~100 lines over shipped primitives: HIGH. A4 auto-settle: MEDIUM until the
RB-29 pin passes.
