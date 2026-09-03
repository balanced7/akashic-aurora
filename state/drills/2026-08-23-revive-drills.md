# Revive-ladder drills — dated receipts, 2026-08-23 evening
# Gate: Daniil verbatim "Lets run the drills" (gate-2026-08-23-revive-ladder-ratified)
# Executor: claude (Vandor), session 3e5f0bdf. All outputs verbatim from live runs.

## D4 — a dying mouth pages within one doctor round: **PASS**

Method: installed a corpse webhook (`http://127.0.0.1:1/dead-drill-d4`) into
`.secrets/discord_channel_vandor.url` (original backed up), sent a real bus
reply claude→daniil (mid 1787522760079-0), pumped the feed directly.

Receipts:
- stderr confession: `[discord-feed] POST FAILED (seat-lane) mid=1787522760079-0
  frm=claude to=daniil (ConnectionError: HTTPConnectionPool(host='127.0.0.1',
  port=1) ...)`
- pump outcome: `forwarded=0 failed=1` (the dead post counted as DEAD).
- doctor, next round: `[dashboard] feed: 1 Discord post failure(s) in the last
  hour (seat-lane: ConnectionError...) -- replies may not be reaching the
  operator` with drill pointer.
- webhook RESTORED from backup; backup file removed.

Contrast with 2026-08-23 morning: the identical failure was INVISIBLE (bare
except, cursor advanced, counted as forwarded). F007's bet: within one round —
HIT (scored separately with this receipt's commit as evidence).

## D5 — double-revive on a healthy house, both boring: **PASS**

`py scripts/revive.py` twice, back to back. Both runs:
`all rungs healthy or deferred -- touched NOTHING (a boring run is a
successful run)`. Zero heals, zero state changes. The idempotency doctrine
(reconciler-not-launcher) held on production, twice.

## D1 (script-level) — kill daemon+runners, one converge recovers: **PASS**

Quiesce check: pulse normal, all backlogs 0. Killed pids 15448 (daemon),
58952 (kimi runner), 692 (deepseek runner) deliberately.

Converge output: SAW redis OK / daemon DEAD / runners 0-of-2 / gateway OK →
HEAL daemon (detached-spawn deepseek, detached-spawn kimi) → PROVE daemon
verified alive. Runners rung correctly NOT healed directly (the daemon owns
its children). ~20s later: observe all-OK (2 daemons, 2/2 runners), pulse
normal. Recovery wall-clock: under one minute, one command.

NOTE: the phone-level D1 (Daniil sends `!revive` from Discord, F006's bet)
remains OPEN — the lever is live on the gateway as of tonight's rotation.

## D2 — kill the ear, the OS resurrects it: receipt appended below

**PASS.** Watchdog: Windows Scheduled Task AkashicAurora-EarWatchdog, every
5 min, running revive.py --target gateway (the reconciler IS the supervisor
-- 288 daily runs against a healthy ear cost nothing by P-idem). Ear killed
(pid 9848) at 18:07:58, hands off. Resurrected by the OS at 18:12:12 --
twelve seconds into the watchdog's first window, zero human hands. And the
functional proof arrived unprompted: the operator's next Discord message
rode the RESURRECTED ear straight through relay and wake -- the chain heard,
not merely existed.

## D3 — sprout proves hands: **PASS BY INCIDENT EVIDENCE** (retroactive)

The 2026-08-23 morning incident's vandor sprout (spawn-1787516635.log)
falsified a theory, root-caused the feed bug, and filed notes/lessons/
handoffs via agent_cli within its first minutes — hands proven under real
fire, better than any staged drill. !spawn's default "arm" mode (acceptEdits
+ allowed tools on the launch line) is the shipped mechanism. A staged
re-drill remains available but the incident receipt stands.
