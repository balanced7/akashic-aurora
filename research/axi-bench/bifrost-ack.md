# AXI bench: `bifrost-ack`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/25 (96%) | 24/25 (96%) | +0 pp |
| Output tokens, as the reader counts them (median) | 48 | 86 | +38 (+79%) |
| Stdout characters (all runs) | 575 | 762 | +187 (+33%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the ack recorded? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which kinds of messages can carry acks? List them separated by commas. | `['handoff', 'decision', 'completion', 'blocker']` | 5/5 | 5/5 |
| Which message id was the ack for? | `['1-0']` | 5/5 | 5/5 |
| What trust status does the acking agent have? Answer with one word. | `quarantined` | 5/5 | 4/5 |
| Which command does the output point to for finding the message's full stream id? Give the command name only. | `['promoted']` | 4/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-ack claude 1-0` (exit 1)

```
ERROR: ack refused -- bifrost:1-0 has no promoted record -- only salient messages (handoff/decision/completion/blocker) carry acks
```

`aurora bifrost-ack alice 1-0` (exit 1)

```
ERROR: ack refused -- 'alice' resolves to quarantined -- unknown/expired ids cannot settle asks (fix the grant in security/acl.json)
```

`aurora bifrost-ack claude abcdef12` (exit 1)

```
ERROR: ack refused -- bifrost:abcdef12 has no promoted record -- only salient messages (handoff/decision/completion/blocker) carry acks (note: that looks like a MAILBOX sha ref and no matching message resolved -- the message may be evicted, or the ref is truncated; try the full stream id from promoted/xrange)
```


## After: output

`aurora bifrost-ack claude 1-0` (exit 1)

```
error: "ack refused -- bifrost:1-0 has no promoted record -- only salient messages (handoff/decision/completion/blocker) carry acks"
code: REFUSED
acked: false
help[1]:
  uv run agent_cli.py promoted --limit 10
```

`aurora bifrost-ack alice 1-0` (exit 1)

```
error: ack refused -- 'alice' resolves to quarantined -- unknown/expired ids cannot settle asks (fix the grant in security/acl.json)
code: REFUSED
acked: false
```

`aurora bifrost-ack claude abcdef12` (exit 1)

```
error: "ack refused -- bifrost:abcdef12 has no promoted record -- only salient messages (handoff/decision/completion/blocker) carry acks (note: that looks like a MAILBOX sha ref and no matching message resolved -- the message may be evicted, or the ref is truncated; try the full stream id from promoted/xrange)"
code: REFUSED
acked: false
help[1]:
  uv run agent_cli.py promoted --limit 10
```
