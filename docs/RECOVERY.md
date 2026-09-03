# RECOVERY — the chain, link by link: LOOK, SMELL, REACH, PROVE
#
# v1.1 — permission-audited LIVE by Heimdall (deepseek), 2026-08-23:
# research/in-flight/recovery-runbook-audit-heimdall-2026-08-23.md. Every
# lever below was attempted from a CLI-only seat with verbatim receipts;
# the eight ranked deltas from that audit are folded in.

**Audience: a seat trying to bring the house back.** The chain is ordered
inbound→outbound; healing follows dependency order. Four moves per link:
LOOK (probe + healthy shape), SMELL (failure signatures), REACH (lever +
permission tier), PROVE (how you know it took). Tiers: [read] any seat ·
[exec] raw shell rights (claude-tier or a rescue-profile sprout) ·
[secrets] .secrets access.

## READ THIS FIRST if you are a CLI-only seat (runners, cold sprouts)

Your exec door allows FOUR families and refuses everything else BEFORE verb
checks: pytest · `py agent_cli.py <verb>` (a ~27-verb READ allowlist) ·
play_sandbox · mirror.py. Two refusal classes with DIFFERENT error strings:
the SHELL-META guard (any `; | & > < $ ( )` backtick or newline — fires
FIRST, so a refused one-liner is not evidence the verb is blocked) and the
FAMILY guard. **Your six proven-live probes: `status`, `pulse`, `doctor`,
`flow`, `locks`, `events`.** `roster`, `gateway`, `docker`, `py -c` and all
process levers REFUSE you: you are a diagnostician, not a surgeon — diagnose
loudly on the bus and route levers to a claude-tier seat or the operator.
PREFLIGHT (Heimdall's closing lesson): check `doctor` for STALE-CODE on your
own seat before trusting any lever's cited behavior — you may be running
code older than the runbook.

**Triage order: ear → substrate → daemon → runners → wake → mouth.**

---

## 1. THE EAR — Discord gateway (alive or no phone recovery exists)

- LOOK [exec]: `py agent_cli.py gateway status` → live pid(s).
  CLI-only fallback [read]: `py agent_cli.py doctor` — the discord agent's
  liveness lines. Log: `tail state/logs/discord-gateway.log`.
  Healthy looks like: `[discord-in] listening as Akashic Aurora`.
- SMELL: no pid; log ends in traceback; operator messages get no 📨.
- REACH [exec]: `py agent_cli.py gateway restart` (detached, stdio→log).
  PLANNED (L1): OS Scheduled Task auto-resurrection.
- PROVE: the "listening as" line reappears; an operator message gets 📨.
  Healthy looks like: 📨 within ~2s of send.

## 2. THE SUBSTRATE — Redis (akashic-redis, 16379)

- LOOK [exec]: `docker ps --filter name=akashic` → Up.
  CLI-only fallback [read]: `py agent_cli.py status` — it renders at all
  only when the substrate answers. Healthy looks like: a full status render.
- SMELL: every verb prints bus OFFLINE; ConnectionError; container Exited.
- REACH [exec]: `docker start akashic-redis` — START, never restart (start
  is a no-op on a running container; restart bounces a healthy substrate
  and drops every client).
- PROVE: `py agent_cli.py status` renders again.

## 3. THE DAEMON — bifrost_daemon (spawns + supervises runners)

- LOOK [read]: `py agent_cli.py doctor` → no daemon-dead page; daemon
  process in the table [exec to list processes].
  Healthy looks like: children respawn after crashes without human hands.
- SMELL: runners die and STAY dead; doctor pages the daemon. **LANDMINE
  (audit-verified): the daemon's spawn path hardcodes the deepseek runner
  script regardless of --agent — a kimi daemon spawning a child whose log
  says `[deepseek-runner]` is this bug (lesson
  daemon_spawn_runner_hardcodes_deepseek_script; unfixed at v1.1).**
- REACH [exec]: `py scripts/bifrost_daemon.py --agent <agent>
  --spawn-runner` (the flag IS the brain). Lane env: NOT required here —
  the daemon passes its env and the child self-defaults
  (BIFROST_CONSUME_LANE setdefault, bifrost_runner_deepseek.py:1401).
  NOTE: the daemon passes --allow-write to its child (I6) — daemon-spawned
  runners are NOT read-only, despite the old assumption.
- PROVE: daemon in the process table; roster/pulse shows children arriving.

## 4. THE RUNNERS — deepseek / kimi / (sol, gemini)

- LOOK [exec]: `py agent_cli.py roster` → [LIVE] rows, fresh beats.
  CLI-only fallback [read]: `py agent_cli.py pulse` — lane depths + normal/
  absent per agent substitutes for roster. Healthy looks like:
  `normal: claude, deepseek, kimi (backlog=0)`.
- SMELL: [DEAD]/[STALE] rows; climbing backlog; asks unanswered; STALE-CODE
  lines (a live runner behind HEAD — restart to pick up fixes).
- REACH [exec]: prefer the daemon (link 3). Direct relaunch only if the
  daemon path is out: `py scripts/bifrost_runner_deepseek.py --agent
  deepseek` — carry the seat's lane env on a DIRECT relaunch (safety net;
  the child self-defaults to work since the setdefault era). NEVER through
  a truncating pipe (RB-28: `| head` kills runners).
- PROVE: roster/pulse LIVE; a one-line ask gets a reply.

## 5. THE CLAUDE SEAT + WAKE — the interactive/spawned brain

- LOOK [exec to list processes]: a `bifrost_wake.py --agent claude
  --session <sid>` process exists for a LIVE session.
  CLI-only signal [read]: operator messages walking 📨→🤔 = a seat is
  consuming; 📨-only forever = no seat has hands (the 2026-08-23 signature:
  "Where did the response go?").
- REACH: [exec] from the repo root, arm for a live session as a BACKGROUND
  task (never inline), lanes drained first:
  `BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync claude --consume`
  then legacy, then
  `BIFROST_WAKE_LANE=work py scripts/bifrost_wake.py --agent claude
  --session <sid>`.
  No live session → from Discord: `!spawn <task>` [operator word]; the
  sprout lands with CLI hands (proven 2026-08-23: agent_cli write verbs via
  Bash WORK unattended; MCP may refuse). PLANNED (L4): daemon auto-spawn.
- PROVE: a test message walks 📨→🤔 within seconds.

## 6. THE MOUTH — outbound feed + webhooks (bus → operator's channel)

- LOOK [read]: `py agent_cli.py events --kind discord_feed_post_failed` —
  fresh events = the mouth is dying LOUDLY (post-2026-08-23 fix; before
  that it died silently while counting dead posts as forwarded).
  Healthy looks like: zero recent post-failed events AND replies visibly
  landing in-channel.
- SMELL: seats answer on the bus, the operator's channel shows nothing —
  THE incident signature; post-failed events accumulating.
- REACH: [secrets] verify/replace `.secrets/discord_channel_<seat>.url`;
  [exec] restart the feed's host (the daemon, link 3). PLANNED (L2): the
  gateway's direct-socket confessions bypass webhooks entirely.
- PROVE: a bus reply to the operator renders in his channel (the ladder's
  ✅ on his message is the machine-readable form).

## 7. BEFORE ANY KILL — the discriminator (Heimdall's drop-in, verbatim)

A long-quiet runner is THINKING (blocked in a model call), WEDGED (blocked
in dead I/O — write/flush/socket), or an INSTRUMENT-FAULT (beat fresh +
pulse dead + healthy wait). The tiebreaker is the MainThread STACK, never
the timeout: `wedged` requires positive evidence the thread is blocked
writing its own output (streams.py / _stream_turn / flush / socket recv).
Killing a thinker costs a turn + warm cache + an RB-26 redelivery; letting
a wedge sit self-heals. So fail toward THINKING — a seat that cannot
collect the stack (py-spy is a raw-exec tool, not a CLI-only lever) can
never justify a kill and must default to thinking. `instrument_fault` =
fix the liveness ORGAN (the two organs disagree), not the worker — this is
the 2026-08-23 gateway signature, not a wedge. Decision rule in code:
`core/comm/wedge_discriminator.py` (t376 half_a §2.3).

---

## The verification matrix (three tiers)

- PROBES: the LOOK column — safe anytime; `!status-deep`/`revive --observe`
  (L2 build) will one-command the lot.
- PINS: feed honesty (test_discord_feed_honesty), the ladder (test_t380_*),
  metabolism contracts (test_t376_*), the map (test_t381_*).
- DRILLS (the only end-to-end truth; dated receipts): D1 kill daemon+
  runners → phone `!revive`; D2 kill the ear → OS resurrection; D3 sprout
  proves hands in 60s; D4 break a webhook → doctor pages in one round; D5
  double-`!revive` on a healthy house → both boring.
  STATUS (corrected 2026-09-02; this line previously said "none executed" while
  the drill ledger held five dated PASSes — the runbook contradicted its own
  receipts): per `state/drills/2026-08-23-revive-drills.md` — D2 PASS 08-23
  18:12:12 · D4 PASS 08-23 (seat-lane path ONLY; global lane never exercised) ·
  D5 PASS 08-23 ×2 · D1 HALF (script-level PASS; phone-level `!revive` never
  run) · D3 PASS by incident evidence (retroactive). Still owed: phone-level D1,
  D4's global lane, and re-runs on the CURRENT daemon-armed wake topology, which
  has zero receipts of its own and is presumed broken until drilled (house law).

## Standing gaps v1.1 is honest about

!revive/!status-deep, the OS supervisor, and the daemon-necromancer are
DESIGN (revive-ladder plan, gate-pending). The daemon's hardcoded-script
landmine (link 3) is KNOWN-UNFIXED. The runner read-allowlist lacks
`roster`/`gateway` (diagnostician seats deserve those eyes — filed as a
wish). Until the ladder lands: phone-only recovery = `!spawn` + this
runbook in the sprout's hands.
