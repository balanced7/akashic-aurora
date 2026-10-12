# AXI bench: `bifrost-drain`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/20 (100%) | 20/20 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 46 | 62 | +16 (+35%) |
| Stdout characters (all runs) | 137 | 168 | +31 (+23%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which runner was asked to drain? | `deepseek` | 5/5 | 5/5 |
| After how many seconds does the request clear itself if the runner ignores it? | `300` | 5/5 | 5/5 |
| Does the runner abandon the message it is working on? Answer yes or no. | `no` | 5/5 | 5/5 |
| What should be done once the runner has exited? Answer with one verb. | `['relaunch']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-drain claude --to deepseek --reason new code landed` (exit 0)

```
[drain] requested for deepseek (self-clears in 300s if unhonored) -- the runner exits clean at its next loop top; relaunch when it lands
```


## After: output

`aurora bifrost-drain claude --to deepseek --reason new code landed` (exit 0)

```
status: requested
runner: deepseek
clears_in_s: 300
runner_will: "finish the message in hand, release its lock, exit 0"
after_exit: relaunch it
reason: new code landed
```
