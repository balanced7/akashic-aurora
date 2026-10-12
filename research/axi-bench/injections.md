# AXI bench: `injections`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 19/20 (95%) | 20/20 (100%) | +5 pp |
| Output tokens, as the reader counts them (median) | 79 | 83 | +4 (+5%) |
| Stdout characters (all runs) | 359 | 386 | +27 (+8%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many injections were there in the window? | `0` | 5/5 | 5/5 |
| About how many tokens did recall push? | `0` | 5/5 | 5/5 |
| How many hours does the window cover? | `2` | 5/5 | 5/5 |
| How many injections carried a lesson of the conductor family? | `0` | 4/5 | 5/5 |

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

`aurora injections` (exit 0)

```
# INJECTION LEDGER  (last 24h: 0 injection(s), ~0 tokens pushed)
  by family (W54 activation gauge): conductor 0/0
  (none -- either quiet, or nothing cleared the relevance floor)
```

`aurora injections --hours 2` (exit 0)

```
# INJECTION LEDGER  (last 2h: 0 injection(s), ~0 tokens pushed)
  by family (W54 activation gauge): conductor 0/0
  (none -- either quiet, or nothing cleared the relevance floor)
```


## After: output

`aurora injections` (exit 0)

```
window_hours: 24
total: 0
tokens_pushed: 0
by_family:
  conductor: 0
result: "none -- either quiet, or nothing cleared the relevance floor"
help[1]:
  uv run agent_cli.py injections --hours 168
```

`aurora injections --hours 2` (exit 0)

```
window_hours: 2
total: 0
tokens_pushed: 0
by_family:
  conductor: 0
result: "none -- either quiet, or nothing cleared the relevance floor"
help[1]:
  uv run agent_cli.py injections --hours 14
```
