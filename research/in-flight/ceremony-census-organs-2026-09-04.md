# Ceremony Census — the EXECUTABLE organs (what is built, not what doctrine names)

> Authored by a claude subagent, 2026-09-04, for Daniil's ceremonies-as-feedback-loops directive.
> Method: `py agent_cli.py discover` (100 verbs) + each verb's own `-h`/docstring, `.claude/settings.json`
> (project) + `C:\Users\L5\.claude\settings.json` (user-level hooks), the live Windows Task Scheduler
> registry (10 `AkashicAurora-*` tasks), and script headers under `scripts/` and `scripts/ops/`.
> Every "fired by" claim below cites one of those. Read-only census; this file is its only artifact.

## Legend

- **AUTO** — a hook, scheduled task, logon trigger, or daemon fires it; no seat has to remember.
- **PIGGYBACK** — fires automatically *inside another ceremony*, so it inherits that ceremony's manualness.
- **MANUAL** — exists as code; fires only if a seat remembers. (Boot-surfaced receipts noted where they exist —
  surfacing a receipt is not firing the ceremony.)

## Scoreboard

- Total executable ceremony organs inventoried: **46**
  (23 agent_cli verbs + 16 scripts + 7 registered hook scripts)
- AUTO-fired: **15** (the 7 hook scripts + revive×2 watchdogs, failsafe deadman, transcript archive daily/weekly/at-SessionEnd, ephemeral archive, secret-scan weekly, trader archivist, sol daemon+runner at logon, wake-listener enforcement)
- PIGGYBACK: **2 direct** (arc_scorecard, corpus_digests — both ride wrap) plus the boot-render surfacings (defer queue, suite-baseline line, directive, grounding pointer, draft pointer)
- MANUAL-only: **29** — including every *reflective* ceremony: wrap --commit, episode, reentry, lookback, friction, forecast, season-score, kata, toast, college, suite-baseline record, doctor/pulse/flightdeck/sweep/orient, watch declare, necropsy, dawe census, snapshot_knowledge…

The shape of the house: **the mechanical/liveness layer is automated; the reflective/feedback layer is almost entirely manual-memory-dependent.** Processes get resurrected without anyone asking; lessons about *why* only get distilled if a seat remembers the verb.

---

## A. The automation substrate (what can fire anything at all)

Three firing layers exist. Anything not wired to one of these is manual by construction.

### A1. Claude Code hooks (user-level `C:\Users\L5\.claude\settings.json`; project `.claude/settings.json` registers a subset: trace, posttooluse, stop)

| Seam | Script | What it auto-fires |
|---|---|---|
| SessionStart | `scripts/hooks/claude_sessionstart.py` | light auto-boot whisper + recall pre-warm + stale-watcher reap (janitor) |
| UserPromptSubmit | `scripts/hooks/claude_userpromptsubmit.py` | plan-time recall (top-2, altitude="plan") + one unread-bus line |
| PreToolUse | `scripts/hooks/claude_trace.py` | display-only tool-call trace onto the Bifrost bus |
| PreToolUse (Bash/PS/Edit/Write) | `scripts/hooks/claude_pretooluse.py` | git/lock GUARD + recall-at-action injection (the system-reminder lessons) |
| PostToolUse + PostToolUseFailure | `scripts/hooks/claude_posttooluse.py` | FAIL→SUCCESS flip crediting ("helped") + payload capture |
| Stop (every turn end) | `scripts/hooks/claude_stop.py` | wake-watcher enforcement (BLOCKS an unarmed stop), promise-shaped-ending audit (once/session), **draft keepalive** (refreshes `chronicles/last-session-draft.md`, 600s throttle), idle heartbeat, incarnation-card refresh |
| PreCompact + SessionEnd | `scripts/hooks/claude_sessionend.py` | **auto-draft where-we-are** → `chronicles/last-session-draft.md`; SessionEnd also folds the transcript into one durable `session_signals` event and runs `archive_transcripts.py` |

### A2. Windows Scheduled Tasks (live registry, verified 2026-09-04)

| Task | Fires | Cadence |
|---|---|---|
| AkashicAurora-DaemonWatchdog | `scripts/revive.py --target daemon` | every 5 min |
| AkashicAurora-EarWatchdog | `scripts/revive.py --target gateway` | every 5 min |
| AkashicAurora-Failsafe-Deadman | `scripts/ops/failsafe_watcher.py` | every 10 min |
| AkashicAurora-TranscriptArchive-Daily / -VerifyWeekly | `scripts/ops/archive_transcripts.py` (`--verify` weekly) | daily 12:00 / weekly |
| AkashicAurora-EphemeralArchive-Daily | `scripts/ops/archive_ephemeral.py` | daily 12:05 |
| AkashicAurora-SecretScan-HistoryWeekly | `scripts/checkers/check_secrets.py --history` | weekly |
| AkashicAurora-TraderArchivist | `scripts/trader_archivist.py` | daily 07:30 (header still says "manual for now" — the registry has superseded it) |
| AkashicAurora-SunshineDiscord / -SunshineFleet | `codex_bifrost_wake.py --agent sol ...` / `bifrost_daemon.py --agent sol --spawn-runner ...` | at logon, persistent |

### A3. Daemons / gateway levers

- `scripts/bifrost_daemon.py` — continuous-presence body (singleton lock, managed runner child, circuit breaker). claude-mode manages WAKE LISTENERS; when live, the Stop hook's wakeability check passes via daemon autopilot (`AKASHIC_DAEMON_WAKE`).
- `scripts/bifrost_wake.py` — the wake listener itself; **its absence is enforced**: the Stop hook blocks an unarmed stop (25s loop-guard, twin/tombstone aware).
- Discord gateway (`bifrost_runner_discord.py` + `core/comm/discord_inbound.py`) — operator levers `!status-deep` (= revive --observe), `!revive [target]`, `!spawn`, `!help`; the EarWatchdog resurrects the gateway itself, so the lever survives its own death.
- `scripts/shift_daemon.py` — the autonomous shift cadence (claim → bounded work → land via mirror → shift-state note). **Explicit opt-in launch only**; never attaches silently.

---

## B. The ceremony verbs (agent_cli.py — verb, seam, fired-by, receipt)

### Session bookends & reflection

1. **`wrap`** (cmd_wrap:4028) — *seam:* session/arc close ("distill this session's own commits + lessons + notes into a DRAFT where-we-are").
   *Fired by:* **MANUAL** — no hook runs `wrap`. Its mechanical shadow IS automated (A1: sessionend/stop hooks write `chronicles/last-session-draft.md`; boot prints a one-line pointer). Inside a wrap run, PIGGYBACK fires: `scripts/corpus_digests.py` (digest ratchet), `scripts/arc_scorecard.py` (M-practice scorecard), recall-curate / stale-claims / forge nudges, and the `--route` nudge ("the night shift cannot pre-chew without targets").
   *Receipt:* `where-we-are` note in AgentMemory (curated=False, supersede-by-title; curated-head guard refuses without `--force`); `--focus` → `next-focus` note (the CURRENT DIRECTIVE boot renders); `--grounding` → `grounding-pointer` note; `--route` → resident suggestions for named ledger ids; stale next-focus retired with a confession line.
2. **`episode`** (cmd_episode:4762) — *seam:* session bookends (an episode IS a narrative Chapter with open span + why). *Fired by:* **MANUAL** (the Bifrost UI renders its JSON contract; a human clicking is still a human remembering). *Receipt:* Chapter records in the narrative spine (close → draft chapter; accept → finalized title/desc/why).
3. **`reentry`** (cmd_reentry:9171, T341) — *seam:* the operator's return — "what moved (measured), one open door (his words verbatim + eye address), his move". *Fired by:* **MANUAL-only** (grep: nothing outside `check_door_parity` references it). Runs an eye ingest inline unless `--stale-ok`. *Receipt:* none — stdout render only (READ-only by charter).
4. **`lookback`** (cmd_lookback:5233, P7) — *seam:* before re-deciding a WHY (docs → research/reviewed → notes → promoted → chapters → git, each with a drill pointer). *Fired by:* **MANUAL**. *Receipt:* none (read-only).
5. **`delta`** — *seam:* a seat's own re-entry ("what changed since this agent's last boot"); `--ack` advances the seen mark. *Fired by:* **MANUAL** (boot-adjacent). *Receipt:* seen-mark cursor only.

### Judgment & calibration ceremonies

6. **`forecast`** (cmd_forecast:6077, T375) — *seam:* "register bets at GATES, score at REVIEW, render calibration"; `--dies-when` mandatory ("a bet that cannot die is not a bet"). *Fired by:* **MANUAL at both ends** — no gate hook registers, nothing surfaces OVERDUE except a manual `forecast list --calibration`. *Receipt:* `state/coord/forecasts.jsonl` (append; verdicts hit/miss/partial/voided/residual; outcome_knowable_ts DERIVED from evidence refs).
7. **`season-score`** (cmd_season_score:5505, T165) — *seam:* after a Season round; `--compare` is "the artifact the operator actually rules on". *Fired by:* **MANUAL**. *Receipt:* stdout only; round evidence lives via `scripts/round_archive.py` (deliberately OUTSIDE git — canary-key side of the boundary).
8. **`suite-baseline`** (cmd_suite_baseline:6261, W34) — *seam:* whenever a seat runs the test suite anyway ("NOBODY RUNS THE SUITE AT WRAP — seats produce receipts when they run suites"); `--whose` runs+attributes YOURS/UNKNOWN/INHERITED. *Fired by:* **MANUAL** to record; the receipt line is AUTO-surfaced at boot (`render_boot_line`, agent_cli:1955-1962). *Receipt:* `state/coord/suite_baseline.json` (git-tracked; node-id deltas, never counts).
9. **`kata`** (cmd_kata:9065) — *seam:* after minting/changing a toolbelt alias ("the tool that tells you when your tools are real"). *Fired by:* **MANUAL**. *Receipt:* toolbelt registry evidence level GUESS/INFER → VERIFIED with version + tested_against.
10. **`college`** (cmd_college:6644) — *seam:* teaching a source packet (source → sealed lecture → independent claim audit → teach-back → append-only errata; separate lecturer/auditor seats enforced). *Fired by:* **MANUAL**. *Receipt:* per-course `events.jsonl` (hash-chained, append-only) + sealed `lecture.md` under the college root (`AURORA_COLLEGE_ROOT` overridable); `show` verifies chain integrity.
11. **`scout`** (cmd_scout:5840, T292) — *seam:* read-only pre-flight before starting work ("is a seat mid-flight / has this been done"). *Fired by:* **MANUAL**. *Receipt:* files itself as an UNADJUDICATED verdict under role=Scout, awaiting operator ruling.
12. **`resident`** (cmd_resident:5646, T258) — *seam:* the callsign ceremony (nominate → human ratifies; self-nomination refused at the door). *Fired by:* **MANUAL** (deliberately — ratification is the human's act). *Receipt:* fleet residents registry record.

### Social / play ceremonies

13. **`toast`** (cmd_toast:9093, T099 BETA-2) — *seam:* when a peer's lesson saved you hops ("gratitude with a receipt — HONEST or it does not send"). *Fired by:* **MANUAL**. *Receipt:* DUAL — live bus message + durable note (`toast:*`), both carrying tier VERIFIED or GUESS; refuses an unverifiable receipt without `--force`.
14. **`boop`** (cmd_boop:6782) — *seam:* play ("the smallest verb in the house; the boop answers the booper"). *Fired by:* **MANUAL**. *Receipt:* stdout; `--surface` piggybacks a sweep.

### Awareness / liveness readouts (the glance family — all read-only, all manual)

15. **`doctor`** (cmd_doctor:5152, T030 L2) — fleet liveness graded per the paging table; also renders activation gauge, taxonomy coverage, lapsing grants. *Fired by:* **MANUAL** (`--page` writes deduped bus notes — the only write). Allow-listed in project settings for frictionless use.
16. **`pulse`** (cmd_pulse:9295, W25) — pressure-map ("vitals says who is dying; pulse says where pressure builds"). **MANUAL**, read-only, exit 1 on critical zones.
17. **`flightdeck`** (cmd_flightdeck:9306, W25) — cockpit one-pager composing doctor + pulse + lane-health + locks + commits. **MANUAL**, read-only.
18. **`sweep`** (cmd_sweep:6570) — the awareness snapshot (bus, bench, health, moved) in one bounded block. **MANUAL** (or via `boop --surface`), read-only.
19. **`orient`** (cmd_orient:6588) — awareness + typed focus + landmarks + return tether, renderer-neutral. **MANUAL**, read-only.
20. **`friction`** (cmd_friction:3336, T196a) — the collaboration tax from existing evidence (episodes, dead-rate, time-to-settle, why-they-died partition). **MANUAL**, READ-ONLY pinned.

### Standing-obligation ceremonies

21. **`watch`** (cmd_watch:9371) — *seam:* before an unattended run — "declare a run so SILENCE becomes a finding"; checkpoint while alive; stand down when done. *Fired by:* declaration **MANUAL**; the *judging* half is **AUTO** (A2 failsafe deadman every 10 min, out-of-band by design — "depends on nothing it watches"). *Receipt:* `state/expect/run-active.json`; an alarm posts to the operator's Discord webhook (write-only) with cooldown.
22. **`defer`** (cmd_defer:9410, W33) — *seam:* when you lack the capability a command needs. *Fired by:* filing/discharge **MANUAL**; the queue is AUTO-surfaced at boot (caps-aware render, agent_cli:1946-1954). *Receipt:* `state/coord/defer_queue.json`; discharge REQUIRES a receipt string — "the queue is also the discharge ledger".
23. **`bifrost-standby`** — *seam:* turn end ("the turn-end ritual in ONE verb — drain, seat report, then BLOCK as the wake listener's parent"). *Fired by:* the verb is MANUAL but the obligation is **HOOK-ENFORCED** — an unarmed stop is blocked by claude_stop.py; with the daemon live, autopilot owns wakeability entirely.

---

## C. The drill / scorecard / post-mortem scripts

24. **`scripts/arc_scorecard.py`** (T031 hook 3) — *seam:* wrap time ("the wrap-time M-practice scorecard… A READER, not a gate: always exits 0"). *Fired by:* **PIGGYBACK** — wrap preview runs it (agent_cli:4126-4134); standalone manual. *Receipt:* a scorecard section in the wrap draft output (which M practices FIRED, with metric reads; zero-signal → annotate-me prompt).
25. **`scripts/revive.py`** (T382, revive ladder L2) — *seam:* anything dead ("launch akashic aurora even if nothing is running, from discord"; reconciler, never launcher — all-skip is a boring success). *Fired by:* **AUTO ×2** (DaemonWatchdog + EarWatchdog, 5-min cadence — "the same script IS the OS watchdog") + Discord `!revive`/`!status-deep` + manual. *Receipt:* the printed confession (SAW / SKIPPED / TOUCHED / PROVED), relayable verbatim in-channel; `state/revive.lock` single-flight.
26. **`scripts/ops/failsafe_watcher.py`** — *seam:* the deadman's scheduled body (reads `watch`'s expectation). **AUTO** every 10 min; exit 1 = "tried to speak and could not", never healthy. *Receipt:* Discord webhook alarm + alarmed-mark (cooldown) in the expectation file.
27. **`scripts/necropsy.py`** (W151b) — *seam:* after any unclean death ("P2 every death detected, P3 every death auto-distills WITH the death-delta — the dying session's operative false assumption"). *Fired by:* **MANUAL-ONLY** — no schedule, no hook, only its tests reference it. *Receipt:* draft-flagged recovered save point + death-delta section, ratified by supersession.
28. **`scripts/ops/sweep_drill_keys.py`** (T118) — *seam:* keyspace hygiene after drill runs. **MANUAL** one-shot (dry-run default). *Receipt:* audit file written BEFORE deletion — "reversible from its own receipt".
29. **`scripts/dawe_census.py`** (W164) — *seam:* verb-surface review ("a response that is not an answer is a defect"; a CENSUS, never a gate — exit 0 always). **MANUAL**. *Receipt:* stdout verifiability report.
30. **`scripts/ops/archive_transcripts.py`** / **`archive_ephemeral.py`** — transcript + ephemeral archiving. **AUTO** (daily; weekly `--verify`; also at every SessionEnd via hook). *Receipt:* archives + weekly verify result in the task's LastTaskResult.
31. **`scripts/checkers/check_secrets.py --history`** — secret-scan over history. **AUTO** weekly.
32. **`scripts/trader_archivist.py`** (P0b) — point-in-time capture of deletable sources ("a fetch records when WE knew"). **AUTO** daily 07:30. *Receipt:* `items/<sha16>.html+.meta.json` + append-only `manifest.jsonl`.
33. **`scripts/ops/mem_watch.py`** — black-box host-memory recorder (born from the 62GB OOM with no forensics). *Fired by:* **MANUAL launch** (long-running; not in the task registry). *Receipt:* `state/mem-watch/mem_watch.jsonl` (reboot-surviving, size-capped) + ALERT/WARN stdout.
34. **`scripts/ops/snapshot_knowledge.py`** — knowledge-data snapshot (git holds only code). **MANUAL**; per standing memory the restore path has NO dated drill receipt — presumed broken under the house's own drill doctrine.
35. **`scripts/corpus_digests.py`** — the digest ratchet. **PIGGYBACK** — every wrap runs it (agent_cli:4043-4053); standalone manual (`--themes` to query).
36. **`scripts/shift_daemon.py`** — the autonomous shift cadence. **MANUAL opt-in launch**, then self-cadenced; closes only with real commit SHA + verification. *Receipt:* ledger transitions + shift-state note + commits via mirror.
37. **`scripts/bifrost_daemon.py`** / **`scripts/bifrost_wake.py`** — presence body / wake listener. **AUTO**: sol's daemon at logon; deepseek/kimi/claude daemons resurrected by the DaemonWatchdog rung; wake-listener absence is blocked at every Stop. *Receipt:* heartbeats, seat files, `.reap.log` lines.

---

## D. What boot itself auto-surfaces (the receipts-push half of the loop)

`boot` (SessionStart whisper = AUTO light version; full CLI/MCP boot = drilled first call) renders, fail-open, each with a GAP line when absent: where-we-are head · **CURRENT DIRECTIVE** (`next-focus`, with age-stamp + STALE flag + ledger cross-check) · grounding pointer · **defer queue** (caps-aware) · **suite-baseline receipt line** (age + decay advisory) · ledger state view · last-session-draft pointer · incoming handoffs · unread bus. This is the strongest existing feedback loop: ceremonies whose receipts land in notes/state-coord get *re-read* automatically even though their *firing* is manual.

---

## E. The three biggest automation gaps (code exists; a seat must remember)

1. **`forecast` — the calibration loop has no clock and no gate.** Doctrine (memory: "register at EVERY gate") is drilled, but no hook fires at a gate, nothing scores at review, and OVERDUE bets render only inside a manual `forecast list --calibration` — neither boot nor doctor mentions them. A registry whose overdue rows are invisible is a calibration instrument that silently stops calibrating.
2. **`necropsy` — auto-distill by charter, manual in fact.** Its own docstring claims "P2 every death detected, P3 every death auto-distills", and `classify_session()` is pure and pinned — but no scheduled task or hook runs the census. The house auto-*resurrects* processes (revive, 5-min watchdogs) while the death-*lesson* organ waits for a human to think of it: exactly the silent-failure class the drill doctrine exists to kill.
3. **The closing bookend — wrap --commit / episode close / suite-baseline record.** The mechanical DRAFT is superbly automated (SessionEnd/PreCompact/Stop keepalive), but the *ratified* ceremony — reviewed wrap, `--focus`/`--route` directive for the night shift, episode accept, a fresh suite receipt — fires only on memory. The `[wrap]` routing nudge prints only *inside* wrap, so a seat that never runs wrap never hears it; SessionEnd cannot prompt (the session is already over). Runner-up gaps of the same shape: `reentry` (operator-return has no trigger), and the friction/pulse/flightdeck readouts (no cadence, so trends are sampled only on curiosity).
