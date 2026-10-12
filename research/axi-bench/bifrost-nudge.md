# AXI bench: `bifrost-nudge`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 17/25 (68%) | 23/25 (92%) | +24 pp |
| Output tokens, as the reader counts them (median) | 28 | 47 | +19 (+68%) |
| Stdout characters (all runs) | 265 | 542 | +277 (+105%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent was nudged? | `deepseek` | 3/5 | 4/5 |
| Which nudge mode was used? | `interrupt` | 4/5 | 4/5 |
| Will the nudged agent drop the task it is working on? Answer yes or no. | `no` | 0/5 | 5/5 |
| Which modes are valid? List them separated by commas. | `['interrupt', 'steer', 'inform']` | 5/5 | 5/5 |
| Was the nudge sent? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-nudge claude look at the failing test --to deepseek` (exit 0)

```
[bifrost-nudge:interrupt] -> deepseek (id 1791814892156-0)
```

`aurora bifrost-nudge claude prefer the small fix --to deepseek --mode steer` (exit 0)

```
[bifrost-nudge:steer] -> deepseek (id 1791814892615-0)
```

`aurora bifrost-nudge claude x --to deepseek --mode yell` (exit 2)

```
ERROR: --mode must be interrupt|steer|inform (got 'yell')
```

`aurora bifrost-nudge claude x` (exit 2)

```
ERROR: bifrost-nudge needs --to <agent>. e.g. bifrost-nudge claude --to deepseek "look at X"
```


## After: output

`aurora bifrost-nudge claude look at the failing test --to deepseek` (exit 0)

```
status: sent
to: deepseek
mode: interrupt
id: 1791814923899-0
effect: drops its current work at the next round boundary and switches to this
```

`aurora bifrost-nudge claude prefer the small fix --to deepseek --mode steer` (exit 0)

```
status: sent
to: deepseek
mode: steer
id: 1791814924473-0
effect: folds this into its current task between rounds and keeps going
```

`aurora bifrost-nudge claude x --to deepseek --mode yell` (exit 2)

```
error: "--mode must be interrupt|steer|inform (got 'yell')"
code: USAGE
sent: false
valid_modes[3]: interrupt,steer,inform
```

`aurora bifrost-nudge claude x` (exit 2)

```
error: bifrost-nudge needs --to <agent>
code: USAGE
sent: false
help[1]:
  uv run agent_cli.py bifrost-nudge claude --to <peer> "<what to look at>"
```
