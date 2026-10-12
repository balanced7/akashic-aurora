# AXI bench: `repeat`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 24/25 (96%) | +16 pp |
| Output tokens, as the reader counts them (median) | 210 | 88 | -122 (-58%) |
| Stdout characters (all runs) | 964 | 902 | -62 (-6%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Against which lesson was the repeat recorded? | `stage_paths` | 5/5 | 5/5 |
| How many repeats are recorded in total? | `3` | 5/5 | 5/5 |
| Which lesson was violated most often? | `stage_paths` | 5/5 | 4/5 |
| How many repeats happened while recall had fired? | `2` | 5/5 | 5/5 |
| Was the repeat recorded? Answer yes or no. | `no` | 0/5 | 5/5 |

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

`aurora repeat stage_paths --what staged everything again --recall-outcome fired --agent bob` (exit 0)

```
[repeat] recorded against 'stage_paths' -- 0.0 hours after it was learned
     the count is a floor over what was NOTICED; a short gap means prose is the wrong instrument and a gate is the right one
```

`aurora repeat --report` (exit 0)

```
# repeats: 3 recorded -- counts only repeats that were NOTICED; the true denominator is unknown
  what recall did at the moment of the repeat:
    fired                                          2
    silent                                         1
    (fired = a READING failure · silent/suppressed = a TARGETING failure)
  most violated:
    stage_paths                                              x2
    port_check                                               x1
  ELAPSED between learning and violating (worst first):
       0.0h ago-learned  port_check                                     [silent]
       0.0h ago-learned  stage_paths                                    [fired]
       0.0h ago-learned  stage_paths                                    [fired]
```

`aurora repeat no_such_lesson --what x` (exit 2)

```

```


## After: output

`aurora repeat stage_paths --what staged everything again --recall-outcome fired --agent bob` (exit 0)

```
recorded: stage_paths
after_learning: 0.0h
note: "a floor over what was noticed; a short gap says a gate, not prose, is the right instrument"
help[1]:
  uv run agent_cli.py repeat --report
```

`aurora repeat --report` (exit 0)

```
total: 3
caveat: counts only repeats that were NOTICED; the true denominator is unknown
by_recall_outcome:
  fired: 2
  silent: 1
outcome_key: fired = a reading failure; silent or suppressed = a targeting failure
most_violated[2]{lesson,repeats}:
  stage_paths,2
  port_check,1
fastest_broken[3]{lesson,after,recall}:
  port_check,0.0h,silent
  stage_paths,0.0h,fired
  stage_paths,0.0h,fired
help[2]:
  uv run agent_cli.py recall --full learn:experiment:stage_paths
  uv run agent_cli.py recall-prevention
```

`aurora repeat no_such_lesson --what x` (exit 2)

```
error: "no lesson named 'no_such_lesson' -- a repeat is evidence about a lesson, and a dangling one inflates a count nobody can audit"
code: NOT_FOUND
help[1]:
  uv run agent_cli.py recall "no_such_lesson"
```
