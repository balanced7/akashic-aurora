# AXI bench: `flightdeck`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 2,037 | 2,165 | +128 (+6%) |
| Stdout characters (all runs) | 2,360 | 1,972 | -388 (-16%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many agents does the flightdeck list? | `6` | 5/5 | 5/5 |
| Does carol have a work lane? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many locks does alice hold? | `0` | 5/5 | 5/5 |
| What is carol's status in the detail section, in one word? | `down` | 5/5 | 5/5 |
| What command shows the full detail for one agent? Give the command only. | `['flightdeck', '--agent']` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora flightdeck` (exit 0)

```
══ FLEET FLIGHTDECK ══

composed_of: doctor + pulse + lane_health + locks + commits + asks + turns + last_turn

doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2
pulse: no lane-mode agents (6 agent(s), all legacy)

AGENT          PULSE      STATUS                 LANE                   LOCKS
------------------------------------------------------------------------------------------
alice          absent     ok                     legacy                 0
alice#benchsea absent     ok                     legacy                 0
bench          absent     ok                     legacy                 0
bob            absent     ok                     legacy                 0
bob#benchsea   absent     ok                     legacy                 0
carol          absent     ok                     legacy                 0

── open asks (asks) ──
  bench: 1 open

── in-flight turns (turns) ──
  alice#benchsea: sync 2.2s (?)
  bob#benchsea: sync 1.6s (?)
```

`aurora flightdeck --agent carol` (exit 0)

```
══ FLEET FLIGHTDECK ══

composed_of: doctor + pulse + lane_health + locks + commits + asks + turns + last_turn + unwedge

doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2
pulse: no lane-mode agents (6 agent(s), all legacy)

AGENT          PULSE      STATUS                 LANE                   LOCKS
------------------------------------------------------------------------------------------
alice          absent     ok                     legacy                 0
alice#benchsea absent     ok                     legacy                 0
bench          absent     ok                     legacy                 0
bob            absent     ok                     legacy                 0
bob#benchsea   absent     ok                     legacy                 0
carol          absent     ok                     legacy                 0

── open asks (asks) ──
  bench: 1 open

── in-flight turns (turns) ──
  alice#benchsea: sync 3.2s (?)
  bob#benchsea: sync 2.7s (?)

── carol detail ──
  status: down
  verdict: carol: no runner process found (no live lock, no presence)
  recommendation: start: uv run scripts/bifrost_runner_deepseek.py --agent carol --agentic
    [dashboard] carol: OFFLINE — 1 unread but the agent is GONE (no worklive, no runner, no wake seat). The backlog is ghost mail from a retired seat — retire the inbox or ignore.
```


## After: output

`aurora flightdeck` (exit 0)

```
composed_of[8]: doctor,pulse,lane_health,locks,commits,asks,turns,last_turn
doctor: "doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2"
pulse: "pulse: no lane-mode agents (6 agent(s), all legacy)"
agents[6]{agent,pulse,status,findings,lane,locks}:
  alice,legacy,ok,0,legacy,0
  alice#benchsea,legacy,ok,0,legacy,0
  bench,legacy,ok,0,legacy,0
  bob,legacy,ok,0,legacy,0
  bob#benchsea,legacy,ok,0,legacy,0
  carol,legacy,ok,1,legacy,0
open_asks[1]{agent,open,redriving,overdue}:
  bench,1,0,0
turns_in_flight[2]{agent,phase,elapsed_s,kind}:
  alice#benchsea,sync,2.3,?
  bob#benchsea,sync,1.7,?
commits_6h: 15+
recent_commits[5]: d1b8e9fc wip unwedge,3fa0342b wip doctor,2d3cdaf1 wip roster,3468b3bc wip task,03aaef2e wip focus
help[1]:
  uv run agent_cli.py flightdeck --agent <agent>
```

`aurora flightdeck --agent carol` (exit 0)

```
composed_of[9]: doctor,pulse,lane_health,locks,commits,asks,turns,last_turn,unwedge
doctor: "doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2"
pulse: "pulse: no lane-mode agents (6 agent(s), all legacy)"
agents[6]{agent,pulse,status,findings,lane,locks}:
  alice,legacy,ok,0,legacy,0
  alice#benchsea,legacy,ok,0,legacy,0
  bench,legacy,ok,0,legacy,0
  bob,legacy,ok,0,legacy,0
  bob#benchsea,legacy,ok,0,legacy,0
  carol,legacy,ok,1,legacy,0
open_asks[1]{agent,open,redriving,overdue}:
  bench,1,0,0
turns_in_flight[2]{agent,phase,elapsed_s,kind}:
  alice#benchsea,sync,3.4,?
  bob#benchsea,sync,2.9,?
commits_6h: 15+
recent_commits[5]: d1b8e9fc wip unwedge,3fa0342b wip doctor,2d3cdaf1 wip roster,3468b3bc wip task,03aaef2e wip focus
detail:
  agent: carol
  status: down
  verdict: "carol: no runner process found (no live lock, no presence)"
  recommendation: "start: uv run scripts/bifrost_runner_deepseek.py --agent carol --agentic"
  findings[1]: "[dashboard] carol: OFFLINE — 1 unread but the agent is GONE (no worklive, no runner, no wake seat). The backlog is ghost mail from a retired seat — retire the inbox or ignore."
```
