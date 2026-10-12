# AXI bench: `recall-at`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 215 | 140 | -75 (-35%) |
| Stdout characters (all runs) | 1,369 | 1,458 | +89 (+7%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent wrote the bus_restart lesson? | `alice` | 5/5 | 5/5 |
| Did the bus_restart lesson's author report that it worked, partly worked, or is it unverified? Answer worked, partial or unverified. | `partial` | 5/5 | 5/5 |
| Which agent holds a lock on this path? | `bob` | 5/5 | 5/5 |
| How many relevant lessons cleared the floor in total? | `2` | 5/5 | 5/5 |
| How many relevant lessons were found? | `0` | 5/5 | 5/5 |
| What exact command shows the complete record of the lesson shown? Give the command only. | `['--full', 'learn:experiment:bus_restart']` | 5/5 | 5/5 |

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

`aurora recall-at --command bus hangs at start restart embedded redis` (exit 0)

```
Recall-at-action (Akashic) - facts relevant to what you're about to do:
[partial alice advice] Use when the bus hangs at start: restart the embedded redis before retrying. (source: learn:experiment:bus_restart)
[worked carol] Use when the bus hangs at start: read the embedded redis log first. (source: learn:experiment:bus_hang_logs)
[verb] `uv run agent_cli.py start` — start one course and designate different lecturer/auditor seats
[legend] worked=self-reported | helped=auto credit | useful=vote | unverified=unconfirmed | anti-pattern=known-bad | advice=forward-looking
```

`aurora recall-at --command bus hangs at start restart embedded redis --limit 1` (exit 0)

```
Recall-at-action (Akashic) - facts relevant to what you're about to do:
[partial alice advice] Use when the bus hangs at start: restart the embedded redis before retrying. (source: learn:experiment:bus_restart)
[verb] `uv run agent_cli.py start` — start one course and designate different lecturer/auditor seats
... 1 of 2 relevant lesson(s) shown — `recall-at --limit 2` for the rest, or `recall --full <source>` for any one's whole record
[legend] worked=self-reported | helped=auto credit | useful=vote | unverified=unconfirmed | anti-pattern=known-bad | advice=forward-looking
```

`aurora recall-at --path core/comm/bus.py` (exit 0)

```
Recall-at-action (Akashic) - facts relevant to what you're about to do:
[lock] bob holds an advisory lock on this path — coordinate before editing
```

`aurora recall-at --command zzzq qqqz` (exit 0)

```
# recall-at-action: nothing relevant (silence beats a weak hint)
```


## After: output

`aurora recall-at --command bus hangs at start restart embedded redis` (exit 0)

```
command: bus hangs at start restart embedded redis
total: 2
lessons[2]{status,by,lesson,source}:
  partial advice,alice,"Use when the bus hangs at start: restart the embedded redis before retrying.","learn:experiment:bus_restart"
  worked,carol,"Use when the bus hangs at start: read the embedded redis log first.","learn:experiment:bus_hang_logs"
verbs[1]{verb,purpose}:
  start,start one course and designate different lecturer/auditor seats
legend: "worked=the author's own report; advice=a suggestion, not an observation"
help[2]:
  uv run agent_cli.py recall --full learn:experiment:bus_restart
  uv run agent_cli.py recall-feedback --source learn:experiment:bus_restart --useful
```

`aurora recall-at --command bus hangs at start restart embedded redis --limit 1` (exit 0)

```
command: bus hangs at start restart embedded redis
total: 2
shown: 1
lessons[1]{status,by,lesson,source}:
  partial advice,alice,"Use when the bus hangs at start: restart the embedded redis before retrying.","learn:experiment:bus_restart"
verbs[1]{verb,purpose}:
  start,start one course and designate different lecturer/auditor seats
legend: "advice=a suggestion, not an observation"
help[2]:
  uv run agent_cli.py recall --full learn:experiment:bus_restart
  uv run agent_cli.py recall-at --command 'bus hangs at start restart embedded redis' --limit 2
```

`aurora recall-at --path core/comm/bus.py` (exit 0)

```
path: core/comm/bus.py
total: 0
locked_by[1]: bob
help[1]:
  uv run agent_cli.py locks
```

`aurora recall-at --command zzzq qqqz` (exit 0)

```
result: nothing relevant (silence beats a weak hint)
command: zzzq qqqz
total: 0
help[1]:
  uv run agent_cli.py recall "<keyword>"
```
