# The Revive Ladder — cold-starting Akashic Aurora from a phone
# (battle plan, 2026-08-23, from the evening's live-fire drill)

Daniil's doctrine sentence, verbatim: "I want to be able to launch akashic
aurora even if nothing is running from discord. In my mind that is what a
truly fault tolerant design would have."

## The incident, reconstructed with receipts

Redis never died (uptime 2.4d). The gateway relayed every message (real bus
ids throughout). What actually failed, in order:
1. **Vandor's wake watcher had lapsed** (per-session watcher, 4h self-cycle,
   no re-arm during the map-build turns) — the claude seat went deaf. First
   domino: "Where did the response go? It's not in the vandor chat."
2. **The rescue sprouts worked better than anyone knew** — the !spawn'd
   vandor sprout (spawn-1787516635) falsified the first theory, root-caused
   the REAL bug, filed notes/lessons/handoffs, and replied to Daniil on the
   bus. It had hands via plain agent_cli Bash verbs (and corrected the stale
   lesson claiming MCP was the safe door — it is the reverse).
3. **The feed ate the answers**: discord_feed.pump()'s seat-lane branch
   swallowed webhook failures (bare except), advanced the cursor, and counted
   the post as forwarded. Every reply — including the sprout's own answer
   about this bug — could die silently while the feed reported success. From
   the phone: total silence = "bifrost is down."
4. **The runners could diagnose but not repair** (exec tier: "Do you have
   exec? It thought we gave it to you") — no process-control lever.

SHIPPED SAME DAY: the feed-honesty fix (failures counted/confessed/journaled,
pin green, 8a416d5d) + the incident-born `gateway status|restart` CLI verb
(Heimdall) classified into the door manifest. Retired: cursor-position-as-
delivery-receipt (it proved attempt, never delivery).

## The ladder (design)

**L0 — the mouth must not lie.** DONE (above). Follow-up slice: a doctor line
reading discord_feed_post_failed events, so a dying webhook pages within one
round instead of waiting for a human to feel the silence.

**L1 — the ear is the ONE always-on organ.** The gateway gets OS-grade
resurrection: a Windows Scheduled Task (at-logon + restart-on-failure)
supervises bifrost_runner_discord.py. Requirement to verify + pin: the
gateway BOOTS AND SERVES CONTROL WORDS with Redis fully down (Bus offline
tolerated at construction; !spawn and the L2 levers touch no bus by design).
Everything else in the house may die; the ear comes back by the OS's hand.

**L2 — the !revive family (no-bus control words, roots only).** Extends the
!spawn precedent (a control word is a hand on a lever, not a message):
- `!revive` — scripts/revive.py, the omnibus: docker start containers →
  redis ping → bifrost daemon (which spawn-runners) → roster verify → per-
  rung confession IN-CHANNEL via the gateway's direct discord.py send
  (webhooks and the feed may be dead; the socket is the one mouth that
  cannot be, while the ear lives).
- `!revive redis|daemon|runners|gateway` — targeted rungs; the gateway rung
  rides the T376 sentinel (make-before-break, S3b) so the ear never
  guillotines itself mid-reply.
- `!status-deep` — no-bus doctor-lite: process table + docker ps + redis
  ping, answered in-channel.
- SECURITY SHAPE (the R3 amendment, needs Daniil's explicit ratification):
  each control word maps to ONE fixed script with ZERO argument passthrough
  from message content; roots only; every invocation confessed in-channel
  and journaled to a file (bus copy on recovery). Reach stays reach; the
  levers are enumerated, auditable, and his.

**L3 — sprouts with hands.** Per the launch-line lesson (grant flags must
ride the launch line): !spawn gains a rescue permission profile — a settings
file allowlisting exactly the recovery verbs (py agent_cli.py *, scripts/
revive.py, docker start/ps, git status) so a rescue sprout can ACT, not just
diagnose. Proof-of-hands in its first minute: run one allowlisted command,
confess the result (bus if alive; else a dead-drop file the gateway's
confession loop watches and speaks in-channel).

**L4 — kill the single point of sleep.** The daemon becomes the claude
seat's necromancer: wake-worthy claude mail + NO live claude watcher/seat →
the daemon spawns a rescue sprout (bounded, once per N minutes, jittered).
The lapsed-watcher domino class dies structurally instead of by discipline.

**L5 — the drills (nothing is real until drilled, dated receipts):**
- D1: kill daemon+runners (ear lives) → phone-only `!revive` → full house,
  receipt with timings.
- D2: kill the ear too → OS supervisor resurrects it → D1 completes.
- D3: `!spawn` rescue sprout proves hands in 60s, confessed to the channel.
- D4: break the webhook deliberately → the doctor pages within one round
  (L0's follow-up proven).
Forecasts registered on D1 and D4 at this plan's gate.

## L2 IDEMPOTENCY DOCTRINE (Daniil's question, 2026-08-23: safe when docker
## is already running -- answered as design law)

!revive is a RECONCILER, never a launcher: observe -> skip-if-healthy ->
heal-only-the-dead -> verify, per rung, in dependency order (redis -> daemon
-> runners), stopping at any rung that fails verification. Probes are the
organs' REAL health signals (PING, DaemonLock holder + heartbeat age, roster
beats), never process-name existence. Heals use the gentlest sufficient
lever: docker START (no-op on running, NEVER restart on the default path),
spawn-only-when-no-live-holder. Bare !revive can kill NOTHING; supersession
exists only in targeted form and rides T376 make-before-break. Robustness
under races: single-flight revive lock + per-rung cooldown (belt), and the
house's own singleton machinery absorbs any over-spawn that slips through
(DaemonLock twin-refusal, runner lock contest, S3a relay dedupe) --
suspenders. Every run confesses what it SAW before what it did; an all-skip
run is a successful, boring run. !status-deep = the observe phase alone.
Same doctrine as the T374 store reconciler and Kubernetes level-triggered
convergence: compare declared vs observed, heal only the delta, never touch
the living. PINS: P-idem (healthy house -> identical pids, all-skip),
P-race (concurrent revives -> one converges), P-partial (only the dead rung
acts). DRILL D5: !revive twice back-to-back on a healthy house from the
phone, both runs boring, dated receipt.

## Sequencing

L0 shipped. L1+L2 are one build slice (mine, next) — the scheduled task, the
revive script, the control words, the in-channel confession path. L3 is a
launch-line flag + settings file (small). L4 is a daemon slice (Heimdall's
domain, folds into T376's family). L5 gates everything and scores the bets.

Gate: this plan + the R3 amendment await Daniil's word. His sentence at the
top is the acceptance bar the drills prove.
