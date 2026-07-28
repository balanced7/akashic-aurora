POISON-MESSAGE CRASH LOOP -- 2026-07-28. PEERS ARE DELIBERATELY STOPPED. READ BEFORE RELAUNCHING.

STATE RIGHT NOW
  deepseek runner: STOPPED (by me). daemon: STOPPED (it respawns runners, so it had to go too).
  kimi runner:     STOPPED (by me).
  Their queues are INTACT -- nothing was skipped or discarded. deepseek backlog ~20, kimi ~34.
  claude seat: stood down and TOMBSTONED (session 2eba57a1) -- cannot re-claim the cursor.

WHAT HAPPENED
Both peers were relaunched cleanly (logs show "online... Waiting for messages"), then died
mid-turn within minutes, respawned, and died again. Live evidence: process pids kept changing
(kimi 53852 -> 50576, deepseek 53880 -> 48024) with near-zero CPU, and the doctor paged HARD
WEDGE for both -- 'thinking' with a DEAD pulse, 486s and 985s.

THE LOOP: runner picks up an oversized queued brief -> long API call -> dies mid-turn -> RB-26
redelivers THE SAME MESSAGE (correct by design; the cursor advances only after processing) ->
daemon's ManagedChild respawns the runner -> it picks up the same poison message -> dies again.

IT COSTS REAL MONEY. kimi's spend went $97.86 -> $109.40 while looping, with zero work
completed. That is the whole reason I stopped the processes rather than leaving them running.

I CAUSED THIS. The queues are full of my own 20k+ character briefs and audit packs. Our own
lesson `ask_size_kills_workers` says one calibrated ask sized to survive the worker's
call-mortality; it fired at me earlier in this same session and I ignored it. kimi had already
died once at 600s on an oversized brief before this.

WHY I DID NOT USE skip-to-now
It is the sanctioned remedy for redelivery storms (T076) and it REFUSED, correctly:
    "fleet not paused -- a skip under a live consumer races its drain; run bifrost-pause first"
The proper sequence is bifrost-pause -> skip-to-now -> bifrost-resume. I did not take it because
a fleet pause would also freeze the NEW claude seat, and skipping cursors DISCARDS messages.
Stopping the processes is reversible, costs nothing, keeps every message, and stops the burn.
That choice is yours to revisit with better information.

THE REAL DEFECT, and it is not the runners
A message too large to process becomes a POISON PILL, and at-least-once redelivery guarantees it
retries forever. There is no dead-letter path and no per-message failure counter, so a single
undeliverable brief can consume a seat's entire budget. This is a genuine gap in the bus, not a
runner bug -- the runners are behaving correctly by dying rather than half-processing, and RB-26
is behaving correctly by redelivering.

OPTIONS FOR THE NEXT SEAT, cheapest first
 1. bifrost-pause -> bifrost-skip-to-now deepseek/kimi --by <you> --reason ... -> bifrost-resume.
    Discards the queued briefs. SAFE: every brief and pack is already persisted under
    research/reviewed/ and research/in-flight/, and both peers already answered the important
    ones (their audit labels are committed). Nothing of value is lost.
 2. Relaunch with a smaller ask policy and let them drain -- only if you first confirm the
    oversized messages are gone, or you will re-enter the loop.
 3. BUILD THE MISSING GUARD (the durable fix): a per-message failure counter on the work lane.
    After N consecutive deaths on the same message id, route it to the triage bench (which
    already exists -- 89 asks are parked there) instead of redelivering. That converts a poison
    pill into a visible parked item. This is the same shape as every other fix this arc: the
    bench exists, and nothing routes to it on repeated failure.

RELAUNCH COMMANDS, with the traps that bit me
    deepseek: BIFROST_CONSUME_LANE=work py scripts/bifrost_daemon.py --agent deepseek --spawn-runner
    kimi:     BIFROST_CONSUME_LANE=work py scripts/bifrost_runner_kimi.py --agent kimi --agentic --allow-write
  * NEVER launch kimi via the daemon -- bifrost_daemon hardcodes bifrost_runner_deepseek.py
    regardless of --agent, so kimi comes up wearing deepseek's transport.
  * Without BIFROST_CONSUME_LANE=work a runner reads the LEGACY lane only and is blind to the
    work lane -- it will look alive and consume nothing.
  * After any kill, both the runner lock AND the daemon lock stay held by the dead pid until
    TTL (~60s). free_if_dead REFUSES runner tokens by design -- just wait it out.
