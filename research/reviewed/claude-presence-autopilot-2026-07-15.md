# Presence Autopilot — claude blind half — 2026-07-15

Status: BLIND design half (deepseek's half not read). Daniel directive verbatim in
note `presence-autopilot-directive`. Inputs: today's live receipts (~15 manual
re-arms, 6+ stop-hook blocks on seat races, the 562-echo cursor surgery, ~180
stale .alive markers, a 6h-invisible dead runner, one read-only relaunch).
Constraints honored: t060-m1-reconciliation rulings 1-7; strangler; kill-switches.

## Thesis

Every chore Daniel named is one loop at the wrong ALTITUDE: a turn-based session
doing PROCESS-LIFECYCLE work per turn. The daemon tier (α/β/δ, now in tree) exists
precisely to hold that loop. The autopilot = γ finished + four absorbers, so that
arm/claim/stand-down become daemon reflexes, and a session's only remaining duty
is: read mail when woken, work, end. Zero lifecycle verbs in a session's day.

## A. Daemon-owned listener (γ core, unchanged from reconciliation)

`bifrost_daemon --agent claude` gains a second ManagedChild tier: the wake
listener. Daemon re-arms it on EVERY exit (wake-worthy exit included) — the
listener never needs a session or a stop hook to arm it again. Benign-exit
semantics per δ's N1: a listener that stood down (displaced seat) is a handover,
not a crash — no breaker count.
[DESIGN: scripts/bifrost_daemon.py --manage-listener]

## B. Session wake channel — trigger file + UserPromptSubmit, NOT ccd-exclusive

The daemon must wake HARNESS SESSIONS it does not own. Today the harness wakes me
via run_in_background task completion — that coupling is the ROOT of the arm
chore (the listener must be MY child to re-invoke me). Proposal: invert via the
EXISTING trigger-file pattern (T073 P8 shipped it for self-cycles): on wake-worthy
mail the daemon writes `bifrost_wake_<agent>_<sid>.trigger`; the harness side
needs exactly ONE hook change — the UserPromptSubmit/SessionStart hooks already
run per turn and the stop hook already polls state; a stop-hook that sees a fresh
trigger reports "mail waiting" instead of blocking on arming. A session that's
mid-work picks mail up at its natural next hook firing. An IDLE session still
needs one harness-tracked waiter — but now it can be a TINY trigger-file poller
(200ms loop, no bus import, no seat) spawned ONCE per session, immune to the
seat-write race because the DAEMON owns the seat.
[DESIGN: core/comm/wake_trigger.py + hook edits]

## C. Stop-hook downgrade (γ's kill-switched fast path, sharpened by today)

Today's 6 blocks were all the same race: listener exits on mail in the
notification gap → hook sees no seat → demands re-arm. With A+B: hook checks
(1) daemon seat alive → PASS silently (daemon owns wakeability); (2) fresh
trigger file → PASS with "mail waiting — next turn reads it"; (3) neither →
today's backstop text. AKASHIC_DAEMON_WAKE=0 restores current behavior wholesale
(ruling 4).
[DESIGN: scripts/hooks/claude_stop.py fast path]

## D. Storm hygiene (T076, approved today)

1. Pending gauge: daemon heartbeat samples `pending()`; > threshold (default
   150) for its agent → ONE `blocker` broadcast naming count + oldest-id age.
2. Ledger-closed auto-settle: the expectations sweep consults task state — a
   redrive whose task is DONE settles silently. Kills storm FORMATION.
3. Sanctioned skip: `agent_cli bifrost-skip-to-now <agent>` = today's surgery as
   a verb (pause → tails → resume → ledger event). Super-admin ACL-gated.
[DESIGN: T076 slices 1-3]

## E. Janitor completion (markers + capability visibility)

1. `.alive` markers: β's trio removes the OWN-session pair; the wake_seat janitor
   additionally sweeps markers with no matching seat AND age > 7d (today: ~180).
2. Runner-down visibility: doctor gains a fleet-liveness line (runner lock holder
   ts age per agent); daemon δ already broadcasts breaker trips; add a daemon
   boot line naming granted-vs-launched capabilities (read-only relaunch would
   have been visible in one line today).
[DESIGN: wake_seat.janitor + agent_cli doctor]

## F. What deliberately does NOT change

Consume path (ruling 1) — the autopilot never touches cursors (D3 is a VERB a
human/super-admin runs, not automation); runner_lock API; the stop hook's
promise-audit; quarantined agents get no daemon (RB-25 F1); TTLs stay the crash
net everywhere.

## Bootstrap order (the chicken-and-egg deepseek will ask about)

Host anchor (ε, Task Scheduler) starts daemons at login; a daemon that finds NO
harness session simply holds presence + listener; the FIRST session of the day
does zero arming (daemon already has it). Before ε lands: one `py scripts/
bifrost_daemon.py --agent claude --manage-listener` in the morning replaces ~15
per-turn arms. Strangler: sessions keep the old arm path behind the C kill-switch
until a week of quiet.

## V-line verdicts

- V1. The arm chore's root is listener-as-session-child; daemon ownership removes
  it structurally, not cosmetically. [CLAIM — today's 15 arms are the evidence]
- V2. Trigger-file wake needs no new transport and reuses T073's shipped P8
  mechanism. [GROUNDED — trigger file exists at scripts/bifrost_wake.py P8 path]
- V3. Storm auto-settle at the expectations sweep kills formation, not symptoms.
  [CLAIM — RB-29 compatibility must be checked in reconciliation]
- V4. Marker sweep is safe at 7d/no-seat because markers only feed liveness
  fallback displays. [GROUNDED — wake_seat.py reads markers for K7 + siblings]
- V5. bifrost-skip-to-now stays a human verb, never a daemon reflex. [PRINCIPLE —
  the scarred seam gets automation only via its own future fence]
- V6. Build targets tagged [DESIGN] above are the slice list for the ledger after
  reconciliation. [DESIGN]
