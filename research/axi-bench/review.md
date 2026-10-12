# AXI bench: `review`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 29/30 (97%) | +13 pp |
| Output tokens, as the reader counts them (median) | 14 | 40 | +26 (+186%) |
| Stdout characters (all runs) | 342 | 608 | +266 (+78%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many items are waiting for review? | `2` | 5/5 | 5/5 |
| How many reviewers must accept the codex-low item before it is accepted? | `1` | 4/5 | 5/5 |
| Which candidate is the opus-high item compared against? | `baseline` | 4/5 | 5/5 |
| How many applied changes are under watch? | `0` | 4/5 | 5/5 |
| How many person/grader disagreements are recorded? | `0` | 5/5 | 5/5 |
| Does the review item nope-123456 exist? Answer yes or no. | `no` | 3/5 | 4/5 |

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

`aurora review list` (exit 0)

```
  opus-high-b0ac33             opus-high vs baseline  no difference shown  needs 1  expires 2026-10-19T15:39:34+00:00
  codex-low-e7ec2d             codex-low vs baseline  no difference shown  needs 1  expires 2026-10-19T15:39:35+00:00
```

`aurora review watch` (exit 0)

```
nothing applied under watch
```

`aurora review disagreements` (exit 0)

```
no person/grader disagreements recorded
```

`aurora review show nope-123456` (exit 1)

```
ERROR: "no review item 'nope-123456'"
```


## After: output

`aurora review list` (exit 0)

```
pending: 2
items[2]{id,candidate,against,verdict,needs,expires}:
  codex-low-ec6227,codex-low,baseline,no difference shown,1,"2026-10-19T15:40:13+00:00"
  opus-high-e8ae74,opus-high,baseline,no difference shown,1,"2026-10-19T15:40:13+00:00"
help[2]:
  uv run agent_cli.py review show codex-low-ec6227
  uv run agent_cli.py review decide codex-low-ec6227 --reviewer <you> --decision accept|reject|more_runs --reason <why>
```

`aurora review watch` (exit 0)

```
watching: 0
items: []
help[1]:
  uv run agent_cli.py review list
```

`aurora review disagreements` (exit 0)

```
total: 0
disagreements: []
```

`aurora review show nope-123456` (exit 1)

```
error: no review item 'nope-123456'
code: NOT_FOUND
help[1]:
  uv run agent_cli.py review list
```
