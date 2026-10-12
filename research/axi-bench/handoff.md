# AXI bench: `handoff`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 83 | 108 | +25 (+30%) |
| Stdout characters (all runs) | 397 | 506 | +109 (+27%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent will receive this handoff? | `alice` | 5/5 | 5/5 |
| How many blockers were flagged with the handoff? | `2` | 0/5 | 5/5 |
| When will the receiving agent see this briefing? Answer in a few words. | `['boot']` | 5/5 | 5/5 |
| How many handoffs are addressed to alice? | `3` | 5/5 | 5/5 |
| Who asked alice to rotate the staging keys? | `carol` | 5/5 | 5/5 |
| How many handoffs are addressed to dave? | `0` | 5/5 | 5/5 |

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

`aurora handoff bench --to alice --task finish the ledger migration --note schema done, data copy pending --blocker staging DB is read-only || waiting on DBA` (exit 0)

```
[OK] handoff bench -> alice: finish the ledger migration
  (the target's next `boot` will surface this as its briefing)
```

`aurora handoff alice --list` (exit 0)

```
# 3 handoff(s) addressed to 'alice' (newest last)
  - from bob: review the ledger migration PR  | CI is green
  - from carol: rotate the staging keys
  - from bench: finish the ledger migration  | schema done, data copy pending
```

`aurora handoff dave --list` (exit 0)

```
# 0 handoff(s) addressed to 'dave' (newest last)
```


## After: output

`aurora handoff bench --to alice --task finish the ledger migration --note schema done, data copy pending --blocker staging DB is read-only || waiting on DBA` (exit 0)

```
recorded: true
from: bench
to: alice
task: finish the ledger migration
blockers: 2
delivery: alice's next boot surfaces this as its briefing
```

`aurora handoff alice --list` (exit 0)

```
to: alice
total: 3
order: newest last
handoffs[3]{from,task,note}:
  bob,review the ledger migration PR,CI is green
  carol,rotate the staging keys,null
  bench,finish the ledger migration,"schema done, data copy pending"
help[1]:
  uv run agent_cli.py boot alice
```

`aurora handoff dave --list` (exit 0)

```
to: dave
total: 0
handoffs: []
help[1]:
  uv run agent_cli.py handoff <agent> --to dave --task "..."
```
