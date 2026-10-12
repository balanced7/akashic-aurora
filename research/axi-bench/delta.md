# AXI bench: `delta`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 14/20 (70%) | 20/20 (100%) | +30 pp |
| Output tokens, as the reader counts them (median) | 61 | 102 | +41 (+67%) |
| Stdout characters (all runs) | 279 | 355 | +76 (+27%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Have the project notes been updated since alice's last boot? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which command shows the notes that changed? Give the command only. | `['agent_cli.py notes']` | 4/5 | 5/5 |
| What exact command marks these changes as seen for alice? Give the command only. | `['delta alice', '--ack']` | 0/5 | 5/5 |
| Does carol have a delta mark yet? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora delta alice` (exit 0)

```
[delta alice] since your last boot (a5328d5 -> ?):
  git: (unavailable -- repository not readable)
  notes: updated since your mark -- uv run agent_cli.py notes
```

`aurora delta carol` (exit 0)

```
[delta carol] no mark yet (newborn) -- the mark writes at your next boot; until then the full boot is the orientation
```


## After: output

`aurora delta alice` (exit 0)

```
agent: alice
state: moved
head: a5328d5 -> a5328d5 (at your last boot -> now)
moved_since_last_boot[1]{area,change}:
  notes,updated since your mark -- uv run agent_cli.py notes
help[1]:
  uv run agent_cli.py delta alice --ack
```

`aurora delta carol` (exit 0)

```
agent: carol
state: newborn
note: no mark yet -- the mark writes at your next boot; until then the full boot is the orientation
```
