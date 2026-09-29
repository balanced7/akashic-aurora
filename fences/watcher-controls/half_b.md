# half_b — the controls lens graded against our seams (claude / Vandor)

**Filed** 2026-09-29 through the door, slot half_b. **Disclosure first:** Heimdall's bus report of
his sealing (mailbox 962aec586c, 04:13Z) reproduced his ten verdict lines, and I read that message
before writing this. So this half is blind on his prose and NOT blind on his headline. Where it
matters I say what I had already committed to on the bus at 04:12Z, before his message: V3 drops
voting, V9 is not windup, first-scan names a moment and carries no load. Nothing below was changed
after reading his lines; the reconciliation will diff them anyway.

V1. [CERTAIN] ISA-18.2 alarm state machine + rationalization + EEMUA KPIs -- maps to core/comm/mailbox.py:50 (INTENTS = act/decline/delegate/defer: an intent vocabulary with no active/cleared axis; `mailbox --open` is an ACK that the cursor treats as return-to-normal), :804 declare_intent; core/comm/triage_park.py:40 park() (shelving with no expiry); core/toolbelt/registry.py:83,204 (the rationalization law, enforced for aliases, absent for pages); KPIs from core/comm/flow_trace.py:148 and core/comm/engine_vitals.py:89 / cost medium (state machine) + small (gate) + small (KPIs) / order 2 for gate+KPIs, 4 for the state machine / false-if ack ever clears, or a page is admitted whose remedy is not a parser verb, or chatter is treated as a rate problem: the 22 pages were re-ACTIVATIONS (scripts/bifrost_child.py:172-175 re-arms the breaker after 300 s with the cause uncleared), and the fix is clear-then-re-activate, never a clock.
V2. [CERTAIN] R_TRIG over the obligation set; first-scan as the NAME of the arm moment only; seal-in latch = owe/settle; RETAIN = obligation durable, attention volatile -- maps to scripts/bifrost_wake.py:354 watch() (a level detector, correct as it stands) and :404-410 (the reverted arm-time baseline sweep: an edge mistaken for the level, the house's own receipt for the trap), with the per-session read cursor (T095 / T106-A1, Sol's seam) as R_TRIG's memory on the CONSUME side / cost small-medium / order 1 / false-if the first-scan bit is shown as the check itself (it names RUN entry; the read under it is a level read), or R_TRIG is put on the detector (it belongs to the consume handoff).
V3. [DESIGN] SIS as process discipline, not physics: PFD (a missed real wake) and spurious-trip rate (three arms that fired within seconds) as the round's two numbers; proof-test intervals = drill receipts with dates; bypass management = time-boxed grants (the deleted --force-foreign read) -- maps to fences/watcher-reliability/brief.md:17-26 (the three arms), scripts/githooks and security grants / cost small / order 6 / false-if VOTING is built over the worklive keys: core/comm/liveness.py:258-259 says a runner writes both keys and an interactive seat only the suffixed one -- one quantity, two namespaces, non-total writers; 1oo2 hides the both-stopped case, 2oo2 trips every interactive seat by construction; the remedy is one reader learning the aggregate plus quality on the read (V6). Conceded to Heimdall's first attack.
V4. [CERTAIN] CIP change-of-state with a cyclic heartbeat; PROFIsafe consecutive number and watchdog -- maps to scripts/bifrost_wake.py:354 (pure change-of-state: silence is ambiguous), the twins (brief: 30 on the second arm; the S0-gamma `seen` sidecar) = the consecutive-number check missing on the consumer, meta.deadline (proposed, deck slide 21) = the watchdog / cost small / order 3 / false-if none: the transport is already treated as unreliable; the heartbeat the watcher lacks is the daemon's presence beat (liveness.py:176), already written -- wire it, do not invent one.
V5. [DESIGN] PackML seat states, five of the seventeen only (Idle / Execute / Held / Suspended / Stopped) -- maps to core/comm/liveness.py phases (running / idle / sync / offline, written by three harnesses), scripts/bifrost_child.py:114 ("restart | pause (breaker trip) | deliberate stop") = Held and Stopped, unnamed on the bus / cost medium / order 8 / false-if adopted wholesale (seventeen states for a seat is theatre), or if Held lives on a plane presence does not: the kimi case recurs.
V6. [CERTAIN] OPC quality codes on every liveness read, with ONE reader of ONE aggregate -- maps to core/comm/liveness.py:176 (the bare-key write), :225-268 live_incarnations() ("Absence of a KEY is not absence of a SEAT", built 2026-08-20 and deliberately not folded into read()), core/comm/roster.py:349-353 (the reader that splits tails on "#"), and the page grade in core/comm/doctor.py (Heimdall: :729-737; the UNMANNED string's mint is not in core/comm, agent_cli.py or scripts and is pinned by command in the reconciliation) / cost small / order 1, beside V2 / false-if a Bad read is ever rendered as a zero (the dsh_agent page), or a second WRITER is added instead of the one reader learning the aggregate.
V7. [DESIGN] ISA-101 alarm summary as the boot header -- maps to agent_cli.py:10074 cmd_flightdeck, :10063 cmd_pulse, the SessionStart hook's [PAGE] lines, core/comm/pager.py:98 unread_pages() (a peek, newest first: a journal, not a summary) / cost small / order 5 / false-if the "summary" is bifrost-sync's raw peek under a heading; it is counts by priority and age, oldest open first, on every boot.
V8. [CERTAIN] permit-to-work = the obligation record -- maps to NONE as one record; today four places: the mailbox intent (mailbox.py:804), the bench (triage_park.py:40), the answers link (meta.answers via bifrost-send --answers), and wake-seat / cost medium / order 4, the same build as V1's state machine (the record IS that machine's row: owner, state, deadline, shelved_until, cleared_by) / false-if built as a fifth store beside the four instead of the one the four derive from.
V9. [UNCERTAIN] anti-windup -- maps to scripts/bifrost_child.py:172-175 (the breaker re-arm) and :184 spawn() (no runner_lock.holder permissive on respawn; the boot path has it at scripts/bifrost_daemon.py:397-411) / cost small, two lines / order 1, rides with V2 / false-if named as windup: no integrator exists; the 22 pages were re-trips of an uncleared cause, a self-resetting trip, and machine safety's rule is reset-after-clear, which is V1's clear-then-re-activate. Conceded to Heimdall's second attack; the name survives only as the label on a two-line fix.
V10. [CERTAIN] one-this-week = V2 plus V9's two lines: the per-session read cursor as R_TRIG's memory on the consume side, and the breaker re-arm gated on the cause having cleared -- removes the acute pain measured on 2026-09-28: three arms that fired within seconds, 30 twins on the third, eight operator chats drowned in replay, and a 22-page flood; it is what makes a watcher HOLD, which Daniel asked for four times on the bus that day. V6 is the second pick and small enough to ride the same week (it removes the chronic false UNMANNED page); the rationalization gate from V1 is third (it refuses the page whose remedy is not a verb and gives `reroute` its first customer).

## What the ten lines say when read together

Three of the nine map onto seams we already own and were merely never wired to each other: the
watcher is already a level detector (V2), the incarnation aggregate is already built (V6), and the
sugar-only refusal is already the rationalization law (V1's gate). Two are one record wearing two
names (V1's state machine and V8's permit): build once. Two are corrections to the lens itself,
conceded on the bus (V3's voting, V9's windup). One is a name we may keep and must not lean on
(first-scan). One is next season (V5).

The build order this half proposes for the reconciliation, each item claude+Heimdall fenced with a
drill receipt before it is called done:

1. **Hold** (V2 + V9): the per-session read cursor on the consume side, and `bifrost_child.py`
   re-arming only after `runner_lock.holder()` is free, paging once per activation. Drill: arm
   three times against a 30-message backlog; the watcher holds; the daemon with a foreign runner
   goes idle and pages zero times in an hour.
2. **Read one liveness** (V6): the page grade and the roster read `live_incarnations()`; every row
   carries Good / Uncertain / Bad; Bad never renders as absent. Drill: an interactive seat idle for
   ten minutes pages nothing; a seat whose beat aged out pages UNMANNED with quality Bad.
3. **Refuse the page** (V1 gate): a page registers only with `remedy: <argv>` whose verb is in
   `build_parser()`; the UNMANNED page is refused until `reroute` exists. Drill: register a page
   with remedy `reroute` today; it refuses with the same sentence the alias registry uses.
4. **Count** (V1 KPIs): alarms per seat-hour, flood fraction, stale > 24 h, top-ten bad actors,
   priority mix, from `flow_trace()`; one line on `flightdeck` and `pulse`. Drill: the 22-page
   daemon flood appears as bad actor #1 within an hour of replaying the ledger.
5. **Name the debt** (V1 state machine = V8 record): one durable obligation row; ack != clear;
   shelve with expiry (the bench, typed); `owe` / `settle` / `reroute` as the verbs over it. Drill:
   RB-26 crash redelivery re-activates an obligation with no arrival; a watcher armed after the
   crash wakes.
6. **Summarise** (V7), 7. **Measure both directions** (V3), 8. **Name the states** (V5).

## What this half does not know

- The exact line that builds the UNMANNED string: not in `core/comm/*.py`, `agent_cli.py` or
  `scripts/*.py` by grep; Heimdall points at the doctor's page grade. Pinned by command in the
  reconciliation, because V6 is wrong if the emitter still reads the bare key after the reader is
  fixed.
- Whether the consume-side cursor already exists in part (the S0-gamma `seen` sidecar): item 1's
  cost depends on it.
- The KPI denominators (seat-hours: which plane counts as "on shift") -- V6 decides that.
