# AXI bench: `gateway`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 15/20 (75%) | 20/20 (100%) | +25 pp |
| Output tokens, as the reader counts them (median) | 35 | 53 | +18 (+51%) |
| Stdout characters (all runs) | 100 | 150 | +50 (+50%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is the Discord gateway running? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many gateway processes are live? | `0` | 5/5 | 5/5 |
| What exact command would start the gateway? Give the command only. | `['gateway restart']` | 0/5 | 5/5 |
| Was the gateway state measured from the process table, or is it unknown? Answer measured or unknown. | `measured` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora gateway status` (exit 1)

```
# gateway: NOT RUNNING (measured: no python process has bifrost_runner_discord.py as an argv token)
```


## After: output

`aurora gateway status` (exit 1)

```
state: not running
count: 0
measured: no python process has bifrost_runner_discord.py as an argv token
help[1]:
  uv run agent_cli.py gateway restart
```
