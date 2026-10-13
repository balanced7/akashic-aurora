# Teardown card: the bus and the seats (Bifrost, the wake ladder, doctor and pager, the runners)

Status: in-flight teardown, 2026-10-13. First calibration run of the teardown card
(`teardown-card.md`, draft v1), on the house itself, at Daniel's "I love your deconstruct the house, yes!"
Method: read-only. Code read, cheap reads of live state, and replays of the doctor's own pure function in an
isolated namespace against an in-memory fake store (the same seam the repo's tests use). Nothing in the house
was written. Scratch probe: `teardown_probe.py` in the session's own scratch folder (not kept).

Label key: **[obs]** observed, with a pointer · **[inf]** inferred, naming what it rests on · **[unk]** unknown,
with where the search stopped.

> **Thesis in one sentence.** The pipes are sound and heavily drilled, but the alarm is wired to the wrong
> clock: the doctor reads "how long has this seat been in this phase" from a field that actually means "how long
> has this seat been beating at all", and it demands a heartbeat every 45 seconds from a seat whose heartbeat is
> only as frequent as its tool calls, so a healthy seat doing one long job looks dead, and the page re-fires on
> every tool call because retraction also resets the "already paged this hour" stamp.

Hardware picture for the whole card: the **bus** is the interconnect (a ring or PCIe fabric); each **seat** is a
core on it; a **runner** is the firmware that turns a stateless accelerator (an API model) into a bus device;
the **wake listener** is the interrupt line that pulls an idle core out of sleep; the **doctor** is the watchdog
timer; the **pager** is the non-maskable interrupt that reaches the human operator.

---

## Row 1. Purpose

| claim | label |
|---|---|
| Bifrost is "the agent nervous system": how live agents talk, are steered, and are kept alive. One sentence of the house: "a message bus lets multiple agents work together ... and a supervision layer keeps them alive." | [obs] `docs/ARCHITECTURE.md:17-19, 94-105` |
| For whom: the model seats (claude, deepseek, kimi, sol, gemini, codex, dsh) and Daniel as operator, who talks to them through the console, Discord and the CLI. | [obs] `scripts/bifrost_runner_*.py` docstrings; `scripts/bifrost_runner_discord.py` docstring |
| The wake ladder's purpose, in Daniel's spirit: "the seat is a durable thing the house can re-open, not a desktop window that must stay up." | [obs] `core/comm/resume_on_deaf.py` docstring (T420, 2026-10-01) |
| The doctor and pager's purpose: be the READER of liveness signals ("progress, not presence") and get page-grade findings to a human; born from the 2026-07-10 mail-loss forensics, where "every liveness surface truthfully said alive and idle while an ask was dead". | [obs] `core/comm/doctor.py:1-11`; `core/comm/pager.py:1-11` |
| **Outcome that makes it worth keeping:** (a) a message to a seat reaches a live reader and gets answered; (b) an idle seat wakes on mail it should answer and only that mail; (c) the human is paged only when a human is truly needed, and never misses a real page. (c) is the outcome failing tonight. | [inf] from the four purposes above plus W263 |

## Row 2. Observables (what we can see from outside, without trusting its self-description)

All readings taken 2026-10-13 between roughly the first and last tool call of this teardown.

| observable | reading | label |
|---|---|---|
| Size | 74 modules in `core/comm/` (28,029 lines) + `scripts/bifrost_*.py` (14,713 lines) = 42,742 lines | [obs] `wc -l` |
| Churn | 503 commits touch `core/comm` or `scripts/bifrost_*.py` since 2026-07-01; 38 of them touch `doctor.py` | [obs] `git log --oneline --since=2026-07-01` |
| Test pins | 358 test files import `core.comm`; 119 mention wedge, doctor or pager | [obs] `grep -l` over `tests/` |
| Store | Redis on 16379 + SQLite mirror; 1,866 lessons | [obs] `py agent_cli.py status` |
| Seats (roster) | 34 seat records; 5 LIVE agents: claude (this session's own seat), deepseek#66756-de, discord#43412-di, dsh_agent#4cd06dad, kimi#7284-kim | [obs] `py agent_cli.py roster`, `roster --by-agent` |
| Pressure (pulse) | dsh_agent CRITICAL (backlog 131); claude 2, deepseek 0, kimi 0 normal | [obs] `py agent_cli.py pulse` |
| Doctor findings now (read-only replay of `examine()` per agent) | 12 known agents, **0 page-grade**, 18 dashboard | [obs] scratch read, see Row 8 V7 |
| Live pager | 0 pages standing on `bifrost:pages` | [obs] `pager.unread_pages()` (a peek; never consumes) |
| Wake receipts, claude | 24 h: 15 wakes, all with mail. 7 days: 76 wakes, 64 with mail, 12 deadline cycles, 0 held below the tier floor | [obs] `wake_seat.wake_receipts_summary('claude')`; file `state/wake-receipts/claude.jsonl` |
| Dual-write | still ON; every message is written twice (claude: work lane 1,754 entries, legacy inbox 1,800) | [obs] `packet_spec.dual_write_enabled()` = True; `lane_depths('claude')` |
| Broadcast stream | 10,011 entries against a 10,000 cap (approximate trim) | [obs] `XLEN bifrost:broadcast`; `core/comm/bus.py:38` |
| Advisory locks | 3 held, each **5,212,290 s (60 days) old** with a stated ttl of 900 s, on pytest temp paths | [obs] `py agent_cli.py locks` |
| Stale code on a live seat | discord#43412-di (process started 2026-10-09, "60 commits have landed since") | [obs] roster STALE-CODE line + doctor stale_code finding |

## Row 3. Mechanism (how inputs become what we observe)

**The bus.** Redis Streams. Each agent has its own inbox stream; a shared broadcast stream is read by every
agent from its own cursor, so a broadcast reaches all agents (the old shared consumer group load-balanced, so a
"broadcast" reached one). Cursors live in a Redis hash, "offset semantics without consumer-group coupling".
Streams are capped (10,000). The bus is ephemeral; salient kinds (handoff, decision, completion, blocker) are
promoted into the durable ledger. Since T039/T045 there are lanes (`work`, `sig`, `trace`) and every send is
dual-written to the legacy inbox and the lane. [obs] `core/comm/bus.py` docstring, `:37-38`;
`core/comm/promoter.py` docstring; `core/comm/packet_spec.py:187, 335-338`

**The runners.** A stateless API model has no process and no inbox, so a runner is "its body": it registers
presence, blocks on the agent's inbox, calls the provider, posts the reply. One file per species: deepseek
(1,720 lines), kimi, gemini, sol, discord, plus the original `bifrost_runner.py`. A singleton runner lock keyed by
agent id stops two processes sharing one cursor (two readers on one offset silently eat each other's mail).
The daemon (`bifrost_daemon.py`) supervises a runner as a managed child with a circuit breaker (3 crashes in
300 s = trip) and restarts stale-code runners (`self_restart.py`). [obs] runner docstrings;
`core/comm/runner_lock.py` docstring; `scripts/bifrost_child.py` docstring; `core/comm/self_restart.py` docstring

**The seats and their liveness card.** Each seat has a "worklive" record in Redis,
`bifrost:worklive:<agent>#<sid8>`, holding `phase` (what it says it is doing), `beat_ts` (last heartbeat),
`since_ts` and `seq`. Writers of a Claude Code seat's card: the PreToolUse trace hook (phase = running/reading/...),
the PostToolUse hook (phase = thinking), the Stop hook (phase = idle), the armed wake listener (phase = idle, every
inner block), and `bifrost-sync` (phase = sync). [obs] `core/comm/roster.py:14, 110-161`;
`agent/harness/hooks/_activity.py:66-93`; `scripts/hooks/claude_trace.py:50-51`;
`scripts/hooks/claude_posttooluse.py:345-346`; `scripts/hooks/claude_stop.py:333-342`; `scripts/bifrost_wake.py:650-672`

The key line: `roster.heartbeat` writes `"since_ts": float(prev.get("since_ts") or now)`, so **since_ts never
moves on a phase change**; it resets only when the key expires (180 s without any beat). The liveness module's own
contract says the opposite: "since_ts -- epoch when the CURRENT phase began (moves only on a phase change)".
[obs] `core/comm/roster.py:143` vs `core/comm/liveness.py:12`. The house already knew this for runners: "phase
age == incarnation age" [obs] `tests/test_runner_clean_exit_retracts_card.py:10-12`.

**The wake ladder.** A turn-based seat cannot wake itself. `bifrost-standby` drains, declares the session
"expected-up", then parents the wake listener as a harness-tracked background task; when wake-worthy mail
arrives the listener exits and the harness starts a new turn. A tier floor (operator 0, directed ask 1,
settlement 2, ambient 3) keeps informational backlog from firing the watcher. If the window is gone,
resume-on-deaf uses `claude -p --resume <sid>` to take a turn on the exact session. The Stop hook refuses to let
a session go idle without an armed listener. [obs] `agent_cli.py:6845-6907`; `core/comm/wake_tiers.py:48-51`;
`core/comm/resume_on_deaf.py` docstring; `scripts/hooks/claude_stop.py` docstring

**The doctor and the pager.** A doctor round (`examine_fleet`) runs on every `py agent_cli.py boot` (seats that
boot, and every runner's onboarding, which shells out to boot), on `py agent_cli.py doctor`, and inside
`flightdeck`; those are its only callers. [obs] grep of `examine_fleet(` outside tests;
`scripts/bifrost_runner_deepseek.py:548` (and the same line in the kimi, gemini and sol runners) For each agent it computes
`stuck = now - since_ts`; for a seat id (`agent#` + 8 hex) it accepts a fresh worklive beat (within
max(45 s, 10 s) = 45 s) as proof of life. Non-idle phase + `stuck` >= 300 s + no proof of life = **HARD WEDGE,
page grade**. Page-grade findings go to the pager (a capped Redis list) **unconditionally**; `--page` only adds a
fleet bus note. The UserPromptSubmit hook renders every standing page into every prompt. When the condition
clears, the next round retracts the page **and deletes the hourly dedup stamp**, "so a condition that resolves
and RECURS inside the window pages again". [obs] `agent_cli.py:507-508, 5838`; `core/comm/doctor.py:334, 377-391,
419-423, 1604-1607, 1640-1642, 1663-1665, 1713-1716, 1746-1757`; `core/comm/liveness.py:85, 88`;
`core/comm/roster.py:47`; `scripts/hooks/claude_userpromptsubmit.py` `build_page_lines`

Put together, the false page of tonight is fully mechanical [inf, confirmed by replay V1-V3]: a seat that has
been beating continuously for hours has `stuck` = hours whatever it is doing; the first tool call that runs past
45 s (a 2-minute commit behind a slow pre-commit hook) leaves the beat stale; the next doctor round pages HARD
WEDGE; the tool call lands, the beat freshens, the next round retracts the page and wipes the dedup stamp; the
next long call pages again. A page every few minutes for as long as the work continues.

## Row 4. First principles (each tested: what evidence or law does it rest on?)

| principle | evidence or law | axiom or assumption? | label |
|---|---|---|---|
| Two readers advancing one offset race and silently lose messages; so at most one consumer per cursor. | Shared-offset consumption semantics (Redis Streams XREAD with client-side cursors); observed live per the module docstring | **Axiom** (a property of the protocol) | [obs] `core/comm/runner_lock.py` docstring |
| A broadcast must be read from per-reader cursors, not one shared consumer group, or it load-balances to one reader. | Redis Streams consumer-group semantics | **Axiom** | [obs] `core/comm/bus.py` docstring |
| Presence proves the process, never the work. | 2026-07-10 mail-loss forensics; a runner's heartbeat thread kept beating while its main thread hung in a flush (caught with py-spy) | **Axiom** (logically true: a separate beat thread is independent of the work thread) | [obs] `core/comm/doctor.py:7-9, 361-365` |
| A turn-based seat cannot wake itself; only the exit of a background task it launched, or a vendor session resume, can start its turn. | The Claude Code harness's behaviour; resume proven in a drill (26 s) | **Contingent constraint** (true of today's vendor harness, not a law; it could change under us) | [obs] `scripts/bifrost_wake.py` docstring; `core/comm/resume_on_deaf.py` docstring |
| Every page must be urgent and actionable; a page that fires on healthy seats trains people to ignore pages. | Google SRE book, ch. 6 ("Monitoring Distributed Systems"), cited as the reconciled paging table | **Axiom of the operator's values** (sourced) | [obs] `core/comm/doctor.py:10-13`; `doctor.py:1700-1702` |
| **"A seat is single-threaded per turn, so its beat IS work evidence."** | Asserted in the doctor's seat privilege | **FALSE FIRST PRINCIPLE (trap 1).** Today one seat key was beaten by several concurrent actors: during a single 16-second sleep of mine (no tool calls), this session's own claude seat went seq 95 to 112 and its phase cycled thinking / reading / running. | [obs] `core/comm/doctor.py:366-369`; live samples, Row 8 V5. [inf] the other writers are most likely the workflow's sibling subagents sharing the parent's session id: this session's scratch folder is keyed by that same session id, the expected-up record and wake seat for it were armed "by harness" (the parent's standby), and the roster shows one LIVE claude seat while several agents run |
| **"since_ts is when the current phase began."** | The liveness module's contract | **FALSE in the seat and runner-incarnation writer (trap 1).** For those records it is "start of the current unbroken beating streak". | [obs] `core/comm/liveness.py:12` vs `core/comm/roster.py:143`; live read V4 |
| **"A live seat beats at least every 45 s."** | Implied by the doctor's window `max(FRESH_S, PROGRESS_TTL*2)` | **Assumption.** A seat beats only when a hook fires; the gap is as long as its longest single tool call or model generation, which is unbounded. MCP tools, and Read/Glob/Grep on the PostToolUse side, do not beat at all. | [obs] `core/comm/doctor.py:385-386`; hook matchers in both settings files |
| Fail toward the cheaper error. The wake janitor fails toward "alive" (a false-dead re-opens the kill loop); the wedge discriminator fails toward "thinking" (a false wedge kills a thinker). | Cost asymmetry, argued in each module | **Axiom of the operator's values**, but the seat page path fails the other way: a stale beat resolves to WEDGED. | [obs] `core/comm/wake_seat.py` docstring K8; `core/comm/wedge_discriminator.py` docstring; [inf] from `doctor.py:415-423` |

## Row 5. Capabilities (what you must HAVE to build or run it)

| capability | label |
|---|---|
| Redis with Streams on 16379 (and a fail-soft file path when it is down) | [obs] `py agent_cli.py status`; `docs/ARCHITECTURE.md:59` |
| Python 3.11 and the `py` launcher; py-spy for runner stacks | [obs] runner shebangs; `core/comm/wedge_discriminator.py` docstring |
| The Claude Code harness: hook events (PreToolUse, PostToolUse, Stop, UserPromptSubmit, SessionStart, SessionEnd), background-task re-invoke, and `claude -p --resume` with a vaulted OAuth token | [obs] settings hook registrations; `core/comm/resume_on_deaf.py` docstring |
| Provider access per runner: DeepSeek, Kimi, OpenAI Responses (Sol), Gemini web or API, a Discord bot token | [obs] runner docstrings |
| Windows process tooling: WMI parent-chain walk for orphan proof, process creation times against pid recycling | [obs] `core/comm/wake_seat.py` docstring K7 |
| A test discipline of pre-registered pins (358 test files touch the bus) and dated drill receipts | [obs] Row 2 |
| The operator's attention, which is the scarce resource the pager spends | [inf] from the pager's purpose |

## Row 6. Required steps (build order from nothing; the critical path)

1. Storage: Store + Ledger over Redis with file fallback. Blocks everything. [obs] `docs/ARCHITECTURE.md:55-59`
2. Bus: per-agent inbox streams, broadcast with per-reader cursors, send/receive, caps. [obs] `bus.py`
3. Runner singleton lock, BEFORE a second runner can ever exist (the lock exists because the race was hit live). [obs] `runner_lock.py`
4. One runner (wait, bridge to the model, reply) with a liveness card and a progress pulse on its real work points. [obs] `liveness.py`
5. Wake listener for turn-based seats, plus the Stop-hook invariant that a seat never idles unarmed. [obs] `bifrost_wake.py`, `claude_stop.py`
6. **Liveness semantics, defined and honoured by every writer** (what phase, beat and since_ts mean, and how often each kind of seat can beat). [inf] this is the step the house did not do as a step: the doctor shipped 2026-07-11 [obs] commit c6265788, seats first beat per tool call 2026-08-02 [obs] `tests/test_seat_beat_retracts_wedge.py:3`, and the meaning of since_ts for seats was never reconciled.
7. Doctor (the reader) and pager (the human channel) with retraction. Depends on step 6 being right.
8. Daemon supervision, circuit breaker, self-restart on stale code.
9. Lanes and the dual-write migration; tier floor.
10. Resume-on-deaf (needs the credential vault and the expected-up record).

Critical path: 1, 2, 3, 4 for runners; 1, 2, 5 for seats; both then 6, then 7. **Building 7 before 6 is the
house's actual order, and the false-page history is the cost of that order.** [inf] from the dates above and
the receipt list in Row 7.

## Row 7. Invariants and failure modes

| invariant | how it breaks | what a break looks like from outside | status today | label |
|---|---|---|---|---|
| I1 One consumer per cursor | a second runner for the same id | mail consumed with no reply | Held for the four modern runners. **Gap:** the launcher's built-in "gemini" spec launches `bifrost_runner.py`, which takes no runner lock (0 occurrences); gemini is parked, so the exposure is dormant | [obs] `core/comm/launcher.py:160-167`; grep table; `doctor.py:577` ("gemini (parked)") |
| I2 Every page is urgent, actionable, and retracts when resolved | stale beat during long work on an aged seat; retraction wipes the dedup so the flap re-pages | `[PAGE] ... HARD WEDGE` lines on a seat that is visibly working | **Broken (W263).** Reproduced by replay. Eight dated receipts of the same family, each fixed at a different reader: 07-28 seat beat accepted, 08-01 idle beat at turn end, 08-02 beat per tool call, 08-10/11 succession retraction, 08-17 runner incarnations lose the seat privilege, 08-26 clean runner exit retracts its card, 09-24 roster socket reuse, 10-13 W263 | [obs] `tests/test_doctor_wedge_vs_beat.py:3`, `claude_stop.py:254-257`, `_activity.py:68-76`, `test_t282_succession_retracts_page.py:6`, `doctor.py:370-376`, `test_runner_clean_exit_retracts_card.py:3-5`, `test_roster_connection_reuse.py:3`, `docs/WISHLIST.md:1778` |
| I3 A page can be acknowledged | no door | the page text says "then ack", names no verb | **Broken.** `pager.ack_pages` and `pager.clear_key` have no human-reachable caller; the only production callers are the doctor's own reconcile and the daemon | [obs] `core/comm/pager.py:133-134`; grep (bounded: every `*.py` outside `tests/` and worktrees) |
| I4 A page leaves a record | pager is a capped Redis list; retraction deletes | tonight's 40 minutes of pages left no trace in the store | **Broken by construction.** `pager.page` writes no ledger event; without `--page` no bus note either | [obs] `pager.py:43-64`; `doctor.py:1760-1761` |
| I5 TTL'd liveness and lock keys expire | something writes them without expiry | immortal DEAD rows in the roster; 60-day-old locks | **Broken for a cohort:** 12 of 34 seat death-witness keys and 3 path locks have no TTL (-1), all last written 60 to 61 days ago (2026-08-12 to 08-14), though their writers set expiry | [obs] Redis TTL reads; `roster.py:103, 152-155`; `locks.py:110` |
| I6 A live process runs current code | stale runner not restarted | STALE-CODE on a LIVE seat | Held for deepseek and kimi. **Broken for discord:** its runner does not import `self_restart`, and the live discord seat is 60 commits behind since 2026-10-09 | [obs] grep table; roster; doctor stale_code finding |
| I7 The gauges agree about one agent (T155) | each gauge keys a different record | three verdicts for one agent | **Broken for dsh_agent:** roster LIVE (seat #4cd06dad, beat 4 s), pulse CRITICAL (backlog 131), doctor "OFFLINE ... GONE (no worklive, no runner, no wake seat)" on the bare id plus "lane HELD ... not a stall" | [obs] Row 2 readings; `doctor.py:263-280` (presence check ignores incarnation cards) |
| I8 Counts are counts | a capped read reports the cap | "50 unread" for two different agents | The backlog probe reads at most 50 entries, so 50 means "50 or more". It also calls the human operator's inbox (daniil) "ghost mail from a retired seat" and offers a skip-to-now drill that would advance past mail addressed to Daniel | [obs] `doctor.py:124`; doctor read V7 |

## Loop altitude (value chains, and whether the signal flows back)

**Chain A, the alarm loop.** seat activity, hook event, worklive card, doctor round, grade, pager list, prompt
render, seat relays to Daniel, Daniel acks, and back to the thresholds.

- Activity to card: open in two places. Tools outside the hook matchers do not beat [obs settings]; the card blends
  every actor sharing a session id [obs V5].
- Card to grade: the grade reads `since_ts` under a meaning the writer does not honour [obs Row 3].
- Grade to pager to retraction: **closed, but with no debounce**, so it oscillates (a level-triggered interrupt with
  no hysteresis) [obs V3]. The stalled-consumer page has hysteresis (180 s first-seen); the wedge page has none
  [obs `doctor.py:56, 472-479` vs `391-423`].
- Daniel back to the system: **designed-open.** No ack verb, no "this page was false" vote, no durable page history,
  so page precision is never measured and no threshold ever learns from a false page [obs I3, I4]. The house
  measures recall precision through its funnel; it does not measure page precision [inf, from the funnel's
  existence in boot vs no page counter found in `doctor.py`/`pager.py`].

**Chain B, the message loop.** send (dual-written), tier floor, wake listener, turn, drain, handle, reply,
settlement, sender wakes. Closed and drilled; wake receipts ride every arm [obs `agent_cli.py:6894-6900`]. The
receipts are displayed, not acted on, and that is by doctrine ("fixed, named thresholds, no auto-threshold
magic", `doctor.py:35-36`), so this is a designed display, not a defect. One open question: 0 messages held
below the floor in 7 days [obs] could mean the floor never had work, or that it is not recording [unk].

**Chain C, the code-freshness loop.** commit, HEAD moves, process stamps the commit it runs, roster and doctor
flag STALE-CODE, `self_restart` restarts between turns. Closed for the four API runners and the daemon; **open
for the discord runner** [obs I6].

## The five traps, as seen here

1. **False first principles.** "A seat is single-threaded per turn" and "since_ts is the phase start" are both
   assumptions dressed as axioms; both fail on live data (Row 4).
2. **Chesterton's fence.** Every part the proposals touch exists for a reason, stated below: the 300 s wedge
   threshold (a real runner hang must page), the 45 s beat window (a runner's beat thread must not mask a hang),
   retraction wiping the dedup (a resolved page rendered into every prompt for nine hours on 2026-07-27, and "a
   flapping consumer is a signal"), the dual-write (migration safety for the lane cutover), `bifrost_runner.py`
   (the free web Gemini path), the TTL-less key cohort (cause unknown, so not to be deleted blind).
3. **Reductionism.** The false page lives in the loop, not in any part: hook cadence times shared session id times
   since_ts meaning times a fixed window times retraction wiping the dedup. Eight fixes each corrected one part;
   the loop kept producing the page.
4. **The map is not the territory.** `doctor --help` says `--page` is what emits pages; in the territory every
   doctor round writes the human pager and only the bus note is optional (`agent_cli.py:9476` vs `doctor.py:1746-1757`).
   **This also means the brief that launched this teardown is mistaken in one rule:** it lists "doctor WITHOUT
   --page" as a read-only verb. It is not: a round can push or retract pages in Daniel's live seats and writes
   dedup and hysteresis keys. I declined to run it and used a read-only equivalent (`examine()` per agent with a
   non-writing hysteresis probe). The call on whether that rule changes is Daniel's.
5. **Goodhart.** (a) W263's evidence that the seat was alive is `pulse claude` reading normal; pulse measures lane
   pressure, not liveness, so it agrees with life without proving it. (b) Every live runner currently shows
   "ALIVE is proven, WORKING is not" (deepseek, kimi, discord), because runner phases are hard-coded 'running' for
   the process's whole life; a line that is always on carries no information. (c) The wedge pins verify
   `examine()` on synthetic records; none replays a long single tool call (bounded search: test files mentioning
   HARD WEDGE, none mention a long or single tool call or pre-commit), so the pins stay green while the live system
   pages falsely.

## Row 8. Verification (predictions that could fail, the test, and what came back)

| # | prediction (stated before the test) | cheapest test | result | held? |
|---|---|---|---|---|
| V1 | The false page is a 45-second cliff: a seat aged in 'running' pages HARD WEDGE when its beat is older than 45 s and is "working" when 45 s or fresher. | `doctor.examine('claude#abcdef12')` with injected records, phase age 3,600 s, beat ages 10 / 40 / 44 / 46 / 70 / 120 s | 10, 40, 44 s: `working` dashboard. 46, 70, 120 s: `hard_wedge` page. Page drill for a seat reads "py-spy dump --pid <runner-pid> \| relaunch the runner", which is not actionable for a Claude Code seat | **held** |
| V2 | A doctor round without `--page` still writes the human pager. | `examine_fleet([seat], page_notes=False)` against an in-memory fake store | fake store got `set doctor_escalated:...:hard_wedge` then `lpush pages`; the rendered prompt line ends "relay via PushNotification if Daniel may be away, then ack" | **held** |
| V3 | Retraction wipes the hourly dedup, so a flapping beat re-pages on every flap. | 5 rounds, beats alternating 70 s / 5 s / 70 s / 5 s / 90 s | 3 pager pushes in 5 rounds; standing pages 1, 0, 1, 0, 1 | **held** |
| V4 | On the live store, a seat's since_ts does not move when its phase changes. | read my own seat card twice | phase 'running' set under 1 s earlier, since_ts 124 s old, seq 17; later phase 'thinking', since_ts 157 s, seq 75 | **held** |
| V5 | The doctor's axiom holds: a seat is single-threaded, so while I sleep inside one tool call its seq does not advance and its phase does not change. | sample my seat card every 2 s for 16 s inside one Bash call | seq 95, 96, 96, 101, 104, 109, 111, 112; phase thinking, reading, reading, running, running, thinking, thinking, running | **failed (the axiom is false here)** |
| V6 | No human-reachable door acks or clears a page. | grep callers of `ack_pages` / `clear_key` in every `*.py` outside tests and worktrees | only `doctor.py:1713` (auto-retract) and `bifrost_daemon.py:794` (runner_down) | **held** (bounded to Python doors) |
| V7 | Right now, with no long tool call in flight anywhere visible, the doctor would raise no page. | `examine()` per known agent with a read-only hysteresis probe; peek of the live pager | 12 agents, 0 page-grade, 18 dashboard; live pager empty | **held** |
| V8 | The gauges agree about each live agent (the T155 acceptance). | compare roster, pulse and the doctor read for dsh_agent | LIVE / CRITICAL / GONE-and-HELD | **failed** |
| V9 | Every seat death-witness and lock key carries an expiry. | `TTL` on `bifrost:seatseen:*` and `bifrost:lock:*` | 12 of 34 seatseen keys and 3 locks at TTL -1; all last written about 60 days ago | **failed** |
| V10 | `self_restart` keeps every live runner on current code. | roster STALE-CODE lines for LIVE seats | deepseek and kimi current; discord 60 commits behind | **failed for discord** |
| V11 | The proposed since_ts fix silences the commit case and keeps a real hang paging. | replay: since_ts reset on phase change | 2-min commit: silent. 4-min tool call: approaching_wedge (dashboard). 7-min hang with no hook: hard_wedge page. Today's behaviour on the same commit: page | **held** (and it shows the fix alone does not cover calls over 300 s) |

---

## Great Sage report

> **Notice.** The bus, the runners and the wake ladder are working: 0 standing pages and 0 page-grade findings
> now (V7); claude woke 15 times in 24 hours, every time with mail (`state/wake-receipts/claude.jsonl`); four
> modern runners hold the singleton lock and self-restart on stale code. The HARD WEDGE page keys on
> `stuck = now - since_ts` (`doctor.py:334, 391`), but the seat writer never moves since_ts on a phase change
> (`roster.py:143`, against `liveness.py:12`); a seat's proof of life is a beat no older than 45 s
> (`doctor.py:385-386`); a seat only beats when a hook fires; retraction deletes the hourly dedup
> (`doctor.py:1664, 1716`). One live seat record was written by several actors at once (V5). A doctor round
> writes the pager without `--page` (V2). No door acks a page (V6) and no page leaves a durable record
> (`pager.py:43-64`). Fifteen keys last written 2026-08-12 to 08-14 have no expiry (V9). The discord runner is
> 60 commits stale (V10). dsh_agent gets three different verdicts from three gauges (V8).
>
> **Analysis.** W263 is not a threshold problem; it is a meaning problem. Because since_ts means "beating since"
> for seats (V4), every seat older than five minutes is permanently "aged", and the only thing standing between a
> healthy seat and a page is a 45-second window that any long tool call or long generation will exceed (V1). The
> retraction design, written for flapping consumers, turns that into a page every few minutes (V3). Eight earlier
> fixes each patched one reader of this record (Row 7, I2); the root, the record's meaning and the seat's real
> beat cadence, was never reconciled, because the doctor was built (07-11) before seats beat at all (08-02). Several
> writers on one seat record (V5; most likely workflow subagents sharing the parent's session id) mean the same
> record can also over-report life and mask a real stall of the parent, so the error runs in both directions. The open half of the loop is human feedback:
> nothing counts false pages, so nothing can learn from them.
>
> **Unknown.** What fired tonight's doctor rounds (boots of fanned-out sessions are the likeliest; pages leave no
> durable record, so this cannot be checked after the fact). Whether the parent's long-running workflow or agent
> tool calls produce hook events at all (the matchers list `Task`, not `Agent`; `_activity.py:40` knows both
> names). Whether the double registration of the trace, PostToolUse and Stop hooks (user-level `scripts/hooks/`
> and repo-level `agent/harness/hooks/`, which have drifted: pretooluse 48 lines, userpromptsubmit 22, trace 8)
> double-beats a seat; the shared session blurred the measurement. Why the fifteen keys lost their expiry. Why
> the discord runner was left out of self-restart (it owns the gateway socket, so it may be deliberate). Why 0
> messages were held below the tier floor in 7 days. Search boundary: Python code under `core/`, `scripts/`,
> `agent/`, `tests/`, both settings files, and the live Redis keys named above; not read: transcripts, the
> Discord side, the UI JavaScript beyond grep, and anything private.
>
> **Proposal** (smallest first; each keeps the fence it touches):
> 1. Name the ack in the page text, and add the door it names: one verb that calls `pager.clear_key(<key>)`
>    (W263 point 3). The fence kept: fleet-wide `ack_pages()` stays unused, because it would discard other
>    agents' live pages (`pager.py:47-50`).
> 2. Give a seat page its own drill: a seat (`agent#` + 8 hex) has no runner pid; say "check the session's last
>    tool call and its age" instead of "py-spy ... relaunch the runner".
> 3. Fix the `doctor --help` text so it says every round writes the human pager, and offer a pure-read mode
>    (`examine()` with read-only probes already exists; V7 used it).
> 4. Make since_ts honour its contract in `roster.heartbeat`: reset it when the phase changes. The fence kept: a
>    seat stuck in ONE phase still ages, so a real hang still pages (V11). Runner incarnations are unaffected
>    because their phase never changes.
> 5. Give the seat wedge page the hysteresis the stalled-consumer page already has (the condition must hold
>    across two rounds or about 180 s before paging). The fence kept: retraction still clears the dedup, so a
>    genuinely recurring wedge pages again.
> 6. Treat a stale beat inside a known tool call as unknown, not dead: PreToolUse stamps the tool and its timeout,
>    and the doctor grades "inside a tool call N s old" as dashboard until the timeout passes (W263 point 2;
>    needed because proposal 4 alone still pages a 5-minute test run, V11).
> 7. Close the human half of the loop: write each page and its retraction to the ledger, and show "pages 24 h:
>    N, retracted while the seat kept progressing: M" on the doctor line. That turns page precision into a number
>    the house can watch.
> 8. Investigate, do not delete: the shared session id across subagents (a per-subagent seat identity, or a
>    "shared seat" mark the doctor respects); the TTL-less key cohort; the discord runner's exclusion from
>    self-restart; the doctor's presence check ignoring incarnation cards (dsh_agent's three verdicts); the
>    50-entry backlog ceiling and the human inbox labelled "a retired seat"; and the lockless `bifrost_runner.py`
>    still named by the launcher's gemini spec.
>
> **Verification.** Eleven predictions were run. Held: V1 the 45-second cliff, V2 the round writes the pager,
> V3 the flap re-pages, V4 since_ts ignores phase changes, V6 no ack door, V7 no page right now, V11 the
> since_ts fix silences the commit case and keeps the hang. Failed, and each failure is a finding: V5 (the
> single-thread axiom), V8 (gauge agreement), V9 (key expiry), V10 (discord freshness).
>
> **Proceed?** YES / NO: Daniel's gate. Every proposal above waits for him; proposals 1 to 3 are text-sized,
> 4 to 6 change what pages, 7 adds a record, 8 is investigation only.
