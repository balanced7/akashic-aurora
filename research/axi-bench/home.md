# AXI bench: `home`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 3 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 0/12 (0%) | 12/12 (100%) | +100 pp |
| Output tokens, as the reader counts them (median) | 0 | 224 | n/a |
| Stdout characters (all runs) | 0 | 501 | n/a |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are stored in memory? | `3` | 0/3 | 3/3 |
| Which agent id is this session using? | `bench` | 0/3 | 3/3 |
| What is the full command to load an agent's startup context? Give the command only. | `['boot', '--task']` | 0/3 | 3/3 |
| What is the full command to search past lessons? Give the command only. | `['recall']` | 0/3 | 3/3 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora ` (exit 2)

```

```


## After: output

`aurora ` (exit 0)

```
bin: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/axi-cli/agent_cli.py
description: "Aurora: shared memory for AI agents -- boot loads past lessons, learn records new ones, recall searches them"
agent_id: bench
backend: "Redis localhost:16379 (+ File mirror)"
lessons: 3
help[4]:
  uv run agent_cli.py boot bench --task "<task>"
  uv run agent_cli.py recall "<query>"
  uv run agent_cli.py learn bench --experiment <name> --tried "..." --result "..."
  uv run agent_cli.py discover
```
