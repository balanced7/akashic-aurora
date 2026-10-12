# AXI bench: `grade`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 18/25 (72%) | 25/25 (100%) | +28 pp |
| Output tokens, as the reader counts them (median) | 64 | 101 | +37 (+58%) |
| Stdout characters (all runs) | 328 | 691 | +363 (+111%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What is the smallest pass-rate change, in percentage points, that this design detects at 80% power? Give the number only. | `17.5` | 5/5 | 5/5 |
| How many person labels exist for the quality grader? | `2` | 3/5 | 5/5 |
| Is the quality grader calibrated, so its verdicts count? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many runs were graded? | `0` | 5/5 | 5/5 |
| What is the overall (Pareto) verdict of opus-high against baseline? | `no difference shown` | 0/5 | 5/5 |

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

`aurora grade power --scenarios-n 40 --trials 3 --delta 0.15` (exit 0)

```
40 scenarios x 3 trials: detects a pass-rate change of 17.5 points at 80% power; power for 15 points: 0.66
```

`aurora grade agreement` (exit 0)

```
{"criterion": "quality", "n": 2, "agreement": 0.5, "calibrated": false}
{"criterion": "process", "n": 1, "agreement": 1.0, "calibrated": false}
```

`aurora grade run --candidate baseline --scenario T1-abc` (exit 0)

```
no runs to grade
```

`aurora grade compare --candidate opus-high --against baseline --scenario T1-abc` (exit 0)

```
opus-high vs baseline on 0 scenario(s): no difference shown
```


## After: output

`aurora grade power --scenarios-n 40 --trials 3 --delta 0.15` (exit 0)

```
scenarios: 40
trials: 3
target_power: 0.8
min_detectable_change_points: 17.5
change_points: 15
power_for_change: 0.66
```

`aurora grade agreement` (exit 0)

```
graders[2]{criterion,n,agreement,calibrated}:
  quality,2,0.5,false
  process,1,1,false
needs: 10+ labels at 80%+ agreement with a person
help[1]:
  uv run agent_cli.py grade label --criterion quality --person <call> --judge-call <call>
```

`aurora grade run --candidate baseline --scenario T1-abc` (exit 0)

```
candidate: baseline
scenarios[1]: T1-abc
graded: 0
runs: []
help[1]:
  uv run agent_cli.py replay run --candidate baseline --scenario T1-abc --budget-usd 2
```

`aurora grade compare --candidate opus-high --against baseline --scenario T1-abc` (exit 0)

```
b: opus-high
a: baseline
scenarios: 0
pareto: no difference shown
wins: []
losses: []
criteria: []
help[1]:
  uv run agent_cli.py grade run --candidate opus-high --scenario T1-abc
```
