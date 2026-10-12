# AXI bench: `shell-home`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 24/25 (96%) | +16 pp |
| Output tokens, as the reader counts them (median) | 78 | 137 | +59 (+76%) |
| Stdout characters (all runs) | 205 | 304 | +99 (+48%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is a shell home mapping set? Answer yes or no. | `no` | 5/5 | 4/5 |
| Is the profile hook installed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Is this shell a harness shell? Answer yes or no. | `no` | 5/5 | 5/5 |
| Where do fresh harness shells land right now? Answer in a few words. | `['launch']` | 5/5 | 5/5 |
| What is the full command to map fresh harness shells to a directory? Give the command only. | `['shell-home --set']` | 0/5 | 5/5 |

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

`aurora shell-home` (exit 0)

```
shell is at : /tmp/axi-bench-mnnz8kj0/before
home mapping: (none -- fresh harness shells land at the session launch dir)
profile hook: absent
harness shell: no (operator terminal -- hook never fires here)
```


## After: output

`aurora shell-home` (exit 0)

```
shell_at: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a20fa37a432d330a0
home_mapping: null
fresh_shells_land_at: the session launch dir
profile_hook: absent
harness_shell: no (operator terminal -- the hook never fires here)
help[1]:
  uv run agent_cli.py shell-home --set <dir>
```
