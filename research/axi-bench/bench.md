# AXI bench: `bench`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/20 (100%) | 20/20 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 14 | 47 | +33 (+236%) |
| Stdout characters (all runs) | 185 | 458 | +273 (+148%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many asks are parked on bench's triage bench? | `0` | 5/5 | 5/5 |
| Was the message parked? Answer yes or no. | `no` | 5/5 | 5/5 |
| What must be added to this command for park to work? Answer in a few words. | `['stream id']` | 5/5 | 5/5 |
| Was a parked ask with that id found on the bench? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora bench bench` (exit 0)

```
# triage bench: bench -- empty (fresh mail flows)
```

`aurora bench bench park 9999999999999-0` (exit 1)

```
[bench] no message 9999999999999-0 on bench's inbox streams
```

`aurora bench bench park` (exit 2)

```
[bench] park needs an inbox stream id
```

`aurora bench bench unpark abcdef123456` (exit 1)

```
[bench] no parked entry abcdef123456
```


## After: output

`aurora bench bench` (exit 0)

```
agent: bench
parked: 0
bench: []
help[1]:
  uv run agent_cli.py bifrost-sync bench
```

`aurora bench bench park 9999999999999-0` (exit 1)

```
error: no message 9999999999999-0 on bench's inbox streams
code: NOT_FOUND
help[1]:
  uv run agent_cli.py mailbox bench
```

`aurora bench bench park` (exit 2)

```
error: park needs an inbox stream id
code: USAGE
help[2]:
  uv run agent_cli.py mailbox bench
  uv run agent_cli.py bench bench park <stream-id> --reason stale
```

`aurora bench bench unpark abcdef123456` (exit 1)

```
error: no parked entry abcdef123456
code: NOT_FOUND
help[1]:
  uv run agent_cli.py bench bench
```
