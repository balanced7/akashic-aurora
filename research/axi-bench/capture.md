# AXI bench: `capture`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 81 | 90 | +9 (+11%) |
| Stdout characters (all runs) | 465 | 863 | +398 (+86%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many messages from alice were captured? | `2` | 5/5 | 5/5 |
| What is step 3 of the migration plan? | `['flip', 'reader']` | 5/5 | 5/5 |
| How long does the copy step take, in minutes? | `40` | 5/5 | 5/5 |
| How many characters were persisted? | `17` | 5/5 | 5/5 |
| Was the requested message found? Answer yes or no. | `no` | 5/5 | 5/5 |
| What flag reads the newest messages from one sender instead of a stream id? Give the flag only. | `--from-agent` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora capture --from-agent alice --count 5` (exit 0)

```
===== 1791820112765-0 | alice [chat] | 49 chars =====
second note: the copy step takes about 40 minutes
===== 1791820112285-0 | alice [handoff] | 108 chars =====
Migration plan:
1. freeze writes
2. copy the tables
3. flip the reader to the new store
Rollback: flip back.
```

`aurora capture --from-agent bob --persist /dev/null` (exit 0)

```
===== 1791820113228-0 | bob [chat] | 17 chars =====
unrelated chatter
[capture] persisted 17 chars -> /dev/null
```

`aurora capture 9999999999999-0` (exit 1)

```
[capture] no match for 9999999999999-0
```

`aurora capture` (exit 2)

```
[capture] give a stream id or --from-agent
```


## After: output

`aurora capture --from-agent alice --count 5` (exit 0)

```
count: 2
messages[2]{id,from,kind,chars,body}:
  1791820156377-0,alice,chat,49,"second note: the copy step takes about 40 minutes"
  1791820155881-0,alice,handoff,108,"Migration plan:\n1. freeze writes\n2. copy the tables\n3. flip the reader to the new store\nRollback: flip back."
help[1]:
  uv run agent_cli.py capture --from-agent alice --count 5 --persist <path>
```

`aurora capture --from-agent bob --persist /dev/null` (exit 0)

```
count: 1
messages[1]{id,from,kind,chars,body}:
  1791820156827-0,bob,chat,17,unrelated chatter
persisted: /dev/null
persisted_chars: 17
```

`aurora capture 9999999999999-0` (exit 1)

```
error: no message 9999999999999-0 in bench's inbox streams
code: NOT_FOUND
help[2]:
  uv run agent_cli.py mailbox bench
  uv run agent_cli.py bifrost-fetch --get <stream-id> --agent <agent_id>
```

`aurora capture` (exit 2)

```
error: give a stream id or --from-agent
code: USAGE
help[2]:
  uv run agent_cli.py capture <stream-id>
  uv run agent_cli.py capture --from-agent <agent_id> --count 3
```
