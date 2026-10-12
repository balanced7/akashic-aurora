# AXI bench: `bifrost-resume`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 9/20 (45%) | 20/20 (100%) | +55 pp |
| Output tokens, as the reader counts them (median) | 7 | 48 | +41 (+586%) |
| Stdout characters (all runs) | 36 | 245 | +209 (+581%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did the resume succeed? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Was the bus paused before this command ran? Answer yes or no. | `yes` | 4/5 | 5/5 |
| Was the bus paused before this command ran? Answer yes or no. | `no` | 0/5 | 5/5 |
| Can the auto-responders take new work now? Answer yes or no. | `yes` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | fail | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-resume` (exit 0)

```
[bifrost] RESUMED
```

`aurora bifrost-resume` (exit 0)

```
[bifrost] RESUMED
```


## After: output

`aurora bifrost-resume` (exit 0)

```
status: resumed
was_paused: true
pause_was: hard
paused_by: user
pause_reason: operator barge-in
auto_responders: free to take new work
```

`aurora bifrost-resume` (exit 0)

```
status: "nothing to resume: the bus was not paused"
was_paused: false
auto_responders: free to take new work
```
