# AXI bench: `promoted`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 21/30 (70%) | 30/30 (100%) | +30 pp |
| Output tokens, as the reader counts them (median) | 1,904 | 1,880 | -24 (-1%) |
| Stdout characters (all runs) | 973 | 836 | -137 (-14%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many durable messages are listed? | `3` | 5/5 | 5/5 |
| Who sent the handoff, and to whom? Answer as sender,recipient. | `['alice', 'bob']` | 5/5 | 5/5 |
| On which day will the v2 parser ship? | `friday` | 5/5 | 5/5 |
| How many of these messages are unhandled? Answer with a number. | `0` | 0/5 | 5/5 |
| Does this output show every durable message? Answer yes or no. | `no` | 5/5 | 5/5 |
| What exact command would show more of the durable messages? Give the command only. | `['promoted', '--limit']` | 1/5 | 5/5 |

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

`aurora promoted` (exit 0)

```
# 3 durable Bifrost message(s) (salient bus -> Ledger)
  [blocker] dave -> alice  2026-10-12T14:26:57
    blocked on the staging database credentials
    ref: event:events:raw:1791815217278-0
  [decision] carol -> bob  2026-10-12T14:26:56
    decision: we ship the v2 parser on Friday
    ref: event:events:raw:1791815216364-0
  [handoff] alice -> bob  2026-10-12T14:26:55
    handing off the cache refactor; tests in tests/test_cache.py are green
    ref: event:events:raw:1791815215866-0

Drill: uv run agent_cli.py events --get <ref>
```

`aurora promoted --limit 2` (exit 0)

```
# 2 durable Bifrost message(s) (salient bus -> Ledger)
  [blocker] dave -> alice  2026-10-12T14:26:57
    blocked on the staging database credentials
    ref: event:events:raw:1791815217278-0
  [decision] carol -> bob  2026-10-12T14:26:56
    decision: we ship the v2 parser on Friday
    ref: event:events:raw:1791815216364-0

Drill: uv run agent_cli.py events --get <ref>
  (+ older salient records beyond this page -- raise --limit)
```


## After: output

`aurora promoted` (exit 0)

```
count: 3
unhandled: 0
unhandled_after_h: 6
messages[3]{ref,kind,from,to,text}:
  "event:events:raw:1791815267325-0",blocker,dave,alice,blocked on the staging database credentials
  "event:events:raw:1791815266254-0",decision,carol,bob,"decision: we ship the v2 parser on Friday"
  "event:events:raw:1791815265737-0",handoff,alice,bob,handing off the cache refactor; tests in tests/test_cache.py are green
help[1]:
  uv run agent_cli.py events --get <ref>
```

`aurora promoted --limit 2` (exit 0)

```
count: 2
more: true
unhandled: 0
unhandled_after_h: 6
messages[2]{ref,kind,from,to,text}:
  "event:events:raw:1791815267325-0",blocker,dave,alice,blocked on the staging database credentials
  "event:events:raw:1791815266254-0",decision,carol,bob,"decision: we ship the v2 parser on Friday"
help[2]:
  uv run agent_cli.py events --get <ref>
  uv run agent_cli.py promoted --limit 4
```
