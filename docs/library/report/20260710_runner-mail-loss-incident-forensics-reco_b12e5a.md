---
akashic_id: art_20260710_runner-mail-loss-incident-forensics-reco_b12e5a
akashic_sha: 459b9d6f0b1f
status: current
type: report
date: 2026-07-10
title: Runner mail-loss incident -- forensics record (2026-07-10 evening)
gist: "Class: evidence Scope: pure evidence + timeline. No diagnosis, no fix design (those live in the fenced analysis docs). This record doubles a"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T21:03:54"
updated: "2026-07-10T21:03:54"
---
<!-- GENERATED PROJECTION of art_20260710_runner-mail-loss-incident-forensics-reco_b12e5a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Runner mail-loss incident -- forensics record (2026-07-10 evening)

Class: evidence
Scope: pure evidence + timeline. No diagnosis, no fix design (those live in the fenced
analysis docs). This record doubles as the live-drill exhibit for the RB-25 kill
condition "one runner killed mid-burst; no message lost without an acknowledgement" --
which tripped, for real, by accident, tonight.

## What the user saw
claude sent deepseek a design-review ask on the live bus at 20:41 and waited. No reply,
no ack, no review file for 15+ minutes. Question raised: "is deepseek stuck?"

## Timeline (all times local, 2026-07-10; ids are bus stream ids)

- 20:25:44  deepseek runner v1 launched by claude as a harness background task, routed
            THROUGH a truncating pipe: `py scripts/bifrost_runner_deepseek.py --agentic
            --think 2>&1 | Select-Object -First 30`. (The pipe is the murder weapon.)
- 20:27     claude sends the RB-4 ask via `agent_cli.py handoff` -- the DURABLE boot-lane
            verb. A live runner never reads that lane (surfaces at next boot only).
            Recorded as lesson handoff_two_lanes_boot_vs_bus.
- 20:30-39  Two full pytest runs emit real conductor `ledger_update` broadcasts onto the
            live bus (test-fixture pollution; fixed the same evening by the autouse
            `_no_live_bus` guard, commit 068f65e). Runner v1 folds them: its log shows
            exactly 2 startup lines + 28 fold lines = 30 stdout objects -- the pipe's
            exact capacity. The 31st write will kill it.
- 20:41:25  claude sends the ask properly on the live bus: kind=handoff,
            id 1783730485458-0 (bifrost-send).
- ~20:41:26 Runner v1's poll cycle consumes it: `bus.wait(timeout_ms=1500, advance=True)`
            advances deepseek's shared inbox cursor to 1783730485458-0 (verified below).
            _process_one passes the fold/should_answer/hops/rate gates and reaches its
            first per-message print (`<- claude [handoff] ...`, runner line ~318) -- the
            31st stdout object. PowerShell's `Select-Object -First N` stops the pipeline
            and kills the upstream process ON that write. Death lands in the window
            AFTER consume, BEFORE responder/reply/ack/error-note.
- 20:41:4x  Harness reports runner v1 dead (exit 255). No traceback -- pipe-stop kill.
- 20:42:35  Runner v2 launched clean (no pipe), pid 73012. Cursor already PAST the
            handoff -> v2 idles, correctly, forever. The ask is gone.
- 20:45-57  Probes (below) establish the ground truth.
- 21:0x     Ask re-sent as id 1783731739202-0; v2 picked it up normally.

## Probes and artifacts (what ruled what out)

1. Singleton lock: holder = {pid 73012, ts 20:54:58} -- lock renewed seconds before the
   probe. Process ALIVE and heartbeating.
2. CPU: 3.375s total over ~13 min; delta over a 6s window = 0. No local compute.
3. Sockets (Get-NetTCPConnection, pid 73012): ONLY loopback Redis :16379 established.
   NO outbound API connection -> no model call in flight. (Sampled twice.)
4. Cursor hash for deepseek: {'inbox': '1783730485458-0', 'bc': '1783731401359-0'} --
   inbox cursor EQUALS the lost handoff id: consumed, exactly once, by SOMETHING.
5. py-spy dump (pid 73012):
     MainThread: main -> bus.wait -> _drain -> redis xread (blocked, normal idle poll)
     Thread-3 (_heartbeat): waiting its 5s tick
   NO worker/_call thread -> v2 never processed the message at all.
6. Raw stream reads (xrevrange, bypassing every cursor):
     bifrost:inbox:claude newest entry = 1783728435183-0 (deepseek's F4-arc reply,
     ~4h older). NO reply, NO timeout note, NO error note after 20:41 exists anywhere.
7. Runner v1's captured log ends at exactly line 30 (2 startup + 28 folds), no
   traceback -- consistent only with the pipe-stop kill on write 31.
8. Runner v2's stdout: EMPTY after 15 min -- python block-buffers stdout to a non-TTY;
   its startup lines sat in the buffer the whole time (observability gap, not a fault).

## Why every liveness signal said "fine"

- Presence + singleton lock are refreshed by an INDEPENDENT daemon heartbeat thread
  (runner ~line 482: kept fresh "even mid-wedge", by design, so long replies don't
  drop the agent from the roster). They prove process-alive, never loop-progress.
- worklive (L1 phase tracker) flips to "handling" at runner line ~329 -- AFTER the
  print that died. v1 died still reading "idle"; v2 is genuinely idle. No layer lies,
  and no layer can see a message that was consumed with no phase flip.
- The P6 ack tier WOULD have confessed: a directed handoff with no ack renders
  UNHANDLED after DIRECTED_UNHANDLED_HOURS=2 in promoted()/boot. Detection exists at
  the hours-scale; nothing redelivers at any scale.

## The two-lane detour (contributing, not causal)
The 20:27 durable-lane handoff cost ~14 minutes of "why is he silent" before the live
bus copy was sent at 20:41. Two lanes, one verb name. Lesson recorded.

## Cross-references
- RB-25 (resilience-battery-slices) concurrency-storm kill condition: "one runner
  killed mid-burst; no message lost without an acknowledgement" -- TRIPPED LIVE.
- T014 per-message isolation protects against EXCEPTIONS mid-batch, not process death.
- T017 detect-dont-consume fixed the WATCHER side of silent consumption; the runner's
  own consume-then-die window was out of its scope.
- T019 pipe drainers protect launcher-managed children; this runner was launched as an
  ad-hoc background shell, outside the launcher's protections.
- Lessons minted tonight: powershell_head_pipe_kills_runner, handoff_two_lanes_boot_vs_bus.
