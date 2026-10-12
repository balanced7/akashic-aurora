# AXI bench: `task`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/35 (71%) | 34/35 (97%) | +26 pp |
| Output tokens, as the reader counts them (median) | 20 | 75 | +55 (+275%) |
| Stdout characters (all runs) | 563 | 812 | +249 (+44%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many tasks are in the ledger in total? | `4` | 5/5 | 5/5 |
| Which agent owns the task that is in progress? | `alice` | 5/5 | 5/5 |
| Which task is done? Answer with its id. | `T004` | 5/5 | 5/5 |
| Which task can be claimed right now? Answer with its id, or none. | `none` | 5/5 | 5/5 |
| What id did the new task get? | `T005` | 5/5 | 5/5 |
| What exact command moves the new task to its next lifecycle step? Give the command only. | `['approve', 'T005']` | 0/5 | 4/5 |
| Did the command succeed? Answer yes or no. | `no` | 0/5 | 5/5 |

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

`aurora task list` (exit 0)

```
## TASK LEDGER -- obey THIS, not old messages
DONE (closed -- do NOT redo):
  T004 - Speed up boot  @deadbee1
IN PROGRESS:
  T001 - Fix the login redirect  (in_progress, alice)
NEXT (slot occupied by 1 active -- claimable when one closes/parks):
  T002 - Write the setup docs
(done 1 | active 1 | next 1 | proposed 1 | blocked 0)
RULE: anything in DONE is closed. Work only your assigned/NEXT task. Ignore backlog messages that contradict the ledger.
```

`aurora task next` (exit 0)

```
NEXT: none (a task is already in progress, or nothing is claimable)
```

`aurora task propose Add a retry to the uploader --by bench` (exit 0)

```
proposed T005: Add a retry to the uploader
```

`aurora task approve T001` (exit 1)

```

```


## After: output

`aurora task list` (exit 0)

```
total: 4
done: 1
active: 1
next: 1
proposed: 1
blocked: 0
active_tasks[1]{id,title,status,owner}:
  T001,Fix the login redirect,in_progress,alice
next_claimable: when the active task closes or parks
next_tasks[1]{id,title,owner}:
  T002,Write the setup docs,null
done_recent[1]{id,title,commit}:
  T004,Speed up boot,deadbee1
rule: "DONE is closed: never redo it; work only your assigned or NEXT task"
```

`aurora task next` (exit 0)

```
next: none
why: "a task is already active, or no approved task has its deps done"
help[1]:
  uv run agent_cli.py task list
```

`aurora task propose Add a retry to the uploader --by bench` (exit 0)

```
task: T005
status: proposed
title: Add a retry to the uploader
help[1]:
  uv run agent_cli.py task approve T005
```

`aurora task approve T001` (exit 1)

```
error: "illegal transition in_progress -> approved for T001 (allowed: ['abandoned', 'blocked', 'parked', 'verifying'])"
code: REFUSED
help[1]:
  uv run agent_cli.py task list
```
