# RECOVERY — the chain, link by link: LOOK, SMELL, REACH, PROVE

**Audience: a seat with permissions trying to bring the house back.** Read
top to bottom; the chain is ordered inbound→outbound, and healing follows
dependency order. Every link has four moves: LOOK (the probe and its healthy
shape), SMELL (what broken looks like), REACH (the lever, with its
permission tier), PROVE (how you know the fix took). Levers are tagged:
[read] = any seat · [exec] = Bash/process rights · [secrets] = .secrets
access (claude-tier). Incident-proven fact (2026-08-23, the vandor sprout):
plain `py agent_cli.py` verbs via Bash WORK from unattended sprouts; MCP
tools may be gated — reach for the CLI first.

**The one-glance triage order:** ear → substrate → daemon → runners → wake →
mouth. If you can read this file, you have a filesystem; start at link 1.

---

## 1. THE EAR — Discord gateway (must be alive for any phone recovery)

- LOOK [read]: `py agent_cli.py gateway status` → live pid(s).
  Log: `tail state/logs/discord-gateway.log` → "listening as Akashic Aurora".
- SMELL: no pid; log ends in a traceback; operator messages get no 📨.
- REACH [exec]: `py agent_cli.py gateway restart` (detached relaunch,
  stdio→log). PLANNED (L1): OS Scheduled Task auto-resurrects it.
- PROVE: log shows "listening as"; a test message from the operator gets 📨
  within seconds.

## 2. THE SUBSTRATE — Redis (akashic-redis, port 16379)

- LOOK [read]: `docker ps --filter name=akashic` → Up;
  `py -c "import sys;sys.path.insert(0,'.');from core.comm.bus import Bus;print(Bus('probe')._client.ping())"` → True.
- SMELL: container Exited; every CLI verb prints bus OFFLINE; ConnectionError.
- REACH [exec]: `docker start akashic-redis` — START, never restart: start
  on a running container is a no-op (safe); restart bounces a healthy
  substrate and drops every client.
- PROVE: ping True; `py agent_cli.py status` renders.

## 3. THE DAEMON — bifrost_daemon (spawns and supervises runners)

- LOOK [read]: process table has `bifrost_daemon.py`; `py agent_cli.py
  doctor` has no daemon-dead page; DaemonLock holder fresh.
- SMELL: runners die and stay dead (nobody respawns); doctor pages the
  daemon; no bifrost_daemon.py process.
- REACH [exec]: `BIFROST_CONSUME_LANE=work py scripts/bifrost_daemon.py
  --agent <agent> --spawn-runner` (the --spawn-runner flag IS the brain — a
  daemon without it supervises nothing; and the launch line MUST carry the
  lane env or the child drains ghost mail — lessons daemon_needs_spawn_runner
  + relaunch_must_carry_the_lane_env). One per agent as configured.
- PROVE: daemon process present; roster shows its children arriving.

## 4. THE RUNNERS — deepseek / kimi / (sol, gemini) seats

- LOOK [read]: `py agent_cli.py roster` → [LIVE] rows with fresh beats;
  `py agent_cli.py pulse` → normal lanes.
- SMELL: [DEAD]/[STALE] rows; backlog climbing; asks unanswered; doctor
  "beat fresh but NO progress pulse" = alive-not-working (see link 7 of the
  t376 discriminator before killing anything — a thinker looks like a wedge).
- REACH [exec]: prefer the daemon (link 3) — it respawns its children.
  Direct relaunch if the daemon path is out:
  `py scripts/bifrost_runner_deepseek.py --agent deepseek` WITH the seat's
  lane env (BIFROST_CONSUME_LANE as configured) — a runner relaunched
  without its lane env drains ghost mail (lesson
  runner_relaunch_without_lane_env_drains_ghost_mail). NEVER through a
  truncating pipe (| head kills runners; RB-28).
- PROVE: roster LIVE; send a one-line ask; a reply arrives.

## 5. THE CLAUDE SEAT + WAKE — the interactive/spawned brain

- LOOK [read]: a `bifrost_wake.py --agent claude --session <sid>` process
  exists for a LIVE session (check the process table); roster shows a claude
  incarnation with a fresh beat.
- SMELL: operator messages pile at 📨 with no 🤔 ever (the ladder tells you
  from the phone!); "Where did the response go" — the 2026-08-23 signature.
- REACH: [exec] arm for a live session:
  `BIFROST_WAKE_LANE=work py E:/AI-Setup/scripts/bifrost_wake.py --agent
  claude --session <sid>` as a BACKGROUND task (never inline; drain work+
  legacy lanes first: `BIFROST_CONSUME_LANE=work py agent_cli.py
  bifrost-sync claude --consume`, then legacy). No live session at all →
  from Discord: `!spawn <task>` [operator]; the sprout lands with CLI hands.
  PLANNED (L4): the daemon auto-spawns on wake-worthy mail + no live seat.
- PROVE: a test message walks 📨→🤔 within seconds of the arm.

## 6. THE MOUTH — outbound feed + webhooks (bus → operator's channel)

- LOOK [read]: `py agent_cli.py events --kind discord_feed_post_failed`
  (fresh events = the mouth is dying LOUDLY now — fixed 2026-08-23; before
  that it died silently). The seat-lane webhook files:
  `.secrets/discord_channel_<seat>.url` exist [secrets to read].
- SMELL: seats answer on the bus but the operator's channel shows nothing;
  post-failed events accumulating. HISTORY: this exact smell was the
  2026-08-23 incident — the feed used to COUNT dead posts as forwarded.
- REACH: [secrets] verify/replace the webhook url file; [exec] restart the
  feed's host process (the daemon, link 3). The gateway's direct-socket
  confessions (PLANNED L2) bypass webhooks entirely.
- PROVE: a bus reply to the operator renders in his channel (human eye or
  the ladder's ✅ on his message).

## 7. WHEN IN DOUBT — the discriminator, before any kill

A long-quiet runner may be THINKING (blocked in a model call), WEDGED
(blocked in dead I/O), or an INSTRUMENT FAULT (liveness organs disagreeing).
`core/comm/wedge_discriminator.py` holds the decision rule (t376 half_a §2):
py-spy the MainThread BEFORE any kill; fail toward thinking. Killing a
thinker costs a turn, a warm cache, and hides an instrument defect.

---

## The verification matrix (what proves the chain, three tiers)

- PROBES (safe anytime — the LOOK column above): one command per link;
  `!status-deep` / `revive --observe` will one-command the lot (L2 build).
- PINS (in the suite): feed honesty (test_discord_feed_honesty), ladder
  (test_t380_*), metabolism contracts (test_t376_*), map (test_t381_*).
- DRILLS (destructive, scheduled, dated receipts — the only end-to-end
  truth): D1 kill daemon+runners → phone !revive; D2 kill the ear → OS
  resurrection; D3 sprout proves hands in 60s; D4 break a webhook → doctor
  pages in one round; D5 double-!revive on a healthy house → both boring.
  STATUS: none executed yet — by house law every path above is PRESUMED
  BROKEN until its drill receipt exists.

## Standing gaps this runbook is honest about

!revive/!status-deep are DESIGN (the revive-ladder plan, gate-pending); the
OS supervisor for the ear is DESIGN; the daemon-necromancer is DESIGN. Until
they land, phone-only recovery = !spawn + this runbook in a sprout's hands.
