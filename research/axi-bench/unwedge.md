# AXI bench: `unwedge`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 24/25 (96%) | +16 pp |
| Output tokens, as the reader counts them (median) | 60 | 107 | +47 (+78%) |
| Stdout characters (all runs) | 382 | 457 | +75 (+20%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What is carol's status, in one word? | `down` | 0/5 | 5/5 |
| How many messages wait in carol's work backlog? | `1` | 5/5 | 5/5 |
| What command does the output recommend running? Give the command only. | `['bifrost_runner_deepseek.py', '--agent carol']` | 5/5 | 5/5 |
| Is a runner process alive for alice? Answer yes or no. | `no` | 5/5 | 5/5 |
| Does the output report any page-grade findings for alice? Answer yes or no. | `no` | 5/5 | 4/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora unwedge carol` (exit 1)

```
carol: no runner process found (no live lock, no presence)
  recommendation: start: uv run scripts/bifrost_runner_deepseek.py --agent carol --agentic
  lane depths: legacy=1, work=1, work_backlog=1
  runner: absent
```

`aurora unwedge alice` (exit 1)

```
alice: no runner process found (no live lock, no presence)
  recommendation: start: uv run scripts/bifrost_runner_deepseek.py --agent alice --agentic
  runner: absent
```


## After: output

`aurora unwedge carol` (exit 1)

```
agent: carol
status: down
verdict: "carol: no runner process found (no live lock, no presence)"
recommendation: "start: uv run scripts/bifrost_runner_deepseek.py --agent carol --agentic"
runner: absent
lane_depths:
  legacy: 1
  work: 1
  work_backlog: 1
```

`aurora unwedge alice` (exit 1)

```
agent: alice
status: down
verdict: "alice: no runner process found (no live lock, no presence)"
recommendation: "start: uv run scripts/bifrost_runner_deepseek.py --agent alice --agentic"
runner: absent
```
