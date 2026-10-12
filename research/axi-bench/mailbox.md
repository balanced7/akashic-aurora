# AXI bench: `mailbox`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 29/30 (97%) | +13 pp |
| Output tokens, as the reader counts them (median) | 254 | 298 | +44 (+17%) |
| Stdout characters (all runs) | 573 | 602 | +29 (+5%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many messages addressed to bench are still unhandled (not yet consumed)? | `2` | 5/5 | 5/5 |
| How many messages has bench consumed? | `3` | 5/5 | 5/5 |
| Which agents sent the unhandled messages? List them separated by commas. | `['dave', 'erin']` | 5/5 | 4/5 |
| What kind of message did dave send? | `request` | 5/5 | 5/5 |
| What command reads the full body of one of these messages? Give the command only. | `['mailbox', 'bench', '--open']` | 0/5 | 5/5 |
| How many messages are addressed to nobody? | `0` | 5/5 | 5/5 |

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

`aurora mailbox bench` (exit 0)

```
# mailbox bench: unhandled=2 | consumed=3 (index_lag 0, evicted 0)
  [consumed] 16706fae93 request    from alice          ts 2026-10-12T15:36:20.836520+00:00
  [consumed] 1e8f900b21 question   from carol          ts 2026-10-12T15:36:21.979706+00:00
  [consumed] 458ff1f9e6 chat       from bob            ts 2026-10-12T15:36:21.358704+00:00
  [unhandled] 7f5dfe661b request    from dave           ts 2026-10-12T15:36:23.146551+00:00
  [unhandled] 6d40f15222 chat       from erin           ts 2026-10-12T15:36:23.721541+00:00
```

`aurora mailbox nobody` (exit 0)

```
# mailbox nobody: empty (index_lag 0, evicted 0)
```


## After: output

`aurora mailbox bench` (exit 0)

```
agent: bench
total: 5
unhandled: 2
consumed: 3
messages[5]{sha,tier,kind,from,at}:
  0eb3f2a24db4,consumed,request,alice,"2026-10-12 15:37"
  abf84401aba3,consumed,question,carol,"2026-10-12 15:37"
  ae3b427b7a42,consumed,chat,bob,"2026-10-12 15:37"
  199fb590cffe,unhandled,request,dave,"2026-10-12 15:37"
  260c77a0c905,unhandled,chat,erin,"2026-10-12 15:37"
help[3]:
  uv run agent_cli.py mailbox bench --open <sha>
  uv run agent_cli.py mailbox bench --intent <sha> --as act|decline|defer|delegate
  uv run agent_cli.py bifrost-sync bench --consume
```

`aurora mailbox nobody` (exit 0)

```
agent: nobody
total: 0
unhandled: 0
messages: []
```
