# T073 Wake & Communicate Robustness — Claude Half (BLIND) — 2026-07-15

Status: blind half of the fenced dual design; deepseek's half:
deepseek-t073-wake-design-2026-07-15.md. Public inputs both halves may cite: the T072
task text, the twin's four-point sketch, tonight's incident inventory. Daniel's
directive verbatim lives in the T073 task text.

## 1. The harness laws (verified tonight, not assumed)

L1. A Claude Code session is re-invoked by exactly three things: a USER turn, a
    background task IT launched completing, and nothing else. Hook-spawned processes
    are invisible to the harness (this is WHY the stop-hook demands a manual Bash arm
    -- a hook cannot arm a tracked seat on the session's behalf).
L2. NEW (schema-verified tonight): the ccd session-management MCP gives sessions
    harness-tier addressing -- `list_sessions` enumerates live sibling sessions;
    `send_message(session_id, text)` delivers INTO a target session as a labelled user
    turn, WAKING it if idle. Every send is user-confirmed (Daniel sees twin traffic --
    a feature at twin frequency, not a bug).
L3. RemoteTrigger (investigated, ruled out for this): it creates/runs claude.ai CLOUD
    routines -- a respawn channel for scheduled cloud agents, not a local-session wake.
L4. The runner class needs none of this: an in-process loop wakes on its own consume.

## 2. Root-cause split of "the chore"

The loop is NOT one problem. Tonight's ~15 re-arms decompose:
  (a) seats fired on NOISE -- legacy dual-write twins (~9 firings; dies with T047
      retirement), self-frm ack copies (2; dies with read-by-position discipline),
      already-handled verdict twins (pre-T066 sends, tail now protected);
  (b) quiet-deadline exits (30-min idle default) -- benign but each demands a re-arm;
  (c) twin-wake impossibility (self-frm skip) -- Daniel hand-bridged; L2 now covers it.
Kill (a) and (b) and the seat arms ONCE per session; (c) moves to the harness channel.

## 3. The design: SEAT-ARMS-ONCE + DISPATCHER-FILTERS-EVERYTHING

The arm cannot be removed (L1: only the session can launch its own tracked task). So
make ONE arm last the whole session by making the signal source noise-free:

- **The Dispatcher becomes the sole bus watcher** (core/comm/dispatcher.py already
  exists -- Mesh W2, "one resident process turns doorbell notices into wakes").
  Supervised per RB-28 launcher-owned lifecycle (T030 covers its crash story; the
  launcher restarts it; its lock steals dead-pid holders per the runner_lock lesson's
  better-fix). It consumes/classifies ALL mail centrally: kinds, lanes, twins,
  incarnation targets, dedup -- the wake-worthiness logic lives in ONE place instead
  of every listener.
- **Per-incarnation signal keys**: dispatcher writes `bifrost:wake:signal:<agent>#<session8>`
  (a blocking list push) ONLY for true work addressed to that incarnation (or anycast
  to the seat-holder, per the twin's addressing sketch).
- **The seat becomes trivial**: each session arms ONE listener at session start that
  BLPOPs its own signal key with a very long deadline. It cannot fire spuriously --
  the dispatcher never pushes noise. One arm, session-lifetime coverage; the stop-hook
  check becomes "is my signal-seat alive" and stops nagging mid-session.
- **Twin traffic**: low-frequency coordination pings ride L2 (send_message -- wakes
  even a seatless session, Daniel-visible); payloads stay on the bus/ledger (durable).
  Sibling detection at boot = `list_sessions` + incarnation cards (twin sketch pt 1).
- **Failure honesty**: dispatcher down -> sessions fall back to today's direct-bus
  seats automatically (the listener probes the dispatcher heartbeat at arm time; the
  strangler keeps both paths until soak proves the dispatcher). Watch-the-watcher =
  launcher + doctor L2 (both exist).

## 4. Migration (strangler, T045 pattern)

S1 dispatcher consumes lanes + writes signal keys (dual-run; seats still direct).
S2 wake listener gains --signal mode (BLPOP key, probe-fallback to direct).
S3 stop-hook checks signal-seat OR dispatcher-heartbeat; re-arm demands end.
S4 twin channel: [twin-sync] pings move to send_message; bus keeps payloads.
S5 retire direct-bus watching (with T047 legacy retirement).

## 5. Pins (sketch)

W1 dispatcher pushes exactly one signal per wake-worthy message (dedup'd, kind/lane
   filtered; a noise kind NEVER signals). W2 a signal-seat survives N noise messages
   without firing (the tonight-class regression). W3 dispatcher crash -> launcher
   restart < deadline; meanwhile arm-time probe falls back to direct mode. W4
   incarnation addressing: #session mail signals only that incarnation; anycast
   signals only the seat-holder. W5 the stop-hook accepts a live signal-seat. W6
   twin ping via send_message wakes an idle sibling (manual drill with Daniel's
   confirm). W7 one-arm property: a full simulated session (boot->N turns->idle)
   arms exactly once.
