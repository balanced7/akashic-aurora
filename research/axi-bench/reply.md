# AXI bench: `reply`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 46 | 76 | +30 (+65%) |
| Stdout characters (all runs) | 373 | 529 | +156 (+42%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did the bus accept the reply? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Does the output confirm that the operator has read the reply? Answer yes or no. | `no` | 5/5 | 5/5 |
| Who is the reply addressed to? | `daniil` | 0/5 | 5/5 |
| Was the reply sent? Answer yes or no. | `no` | 5/5 | 5/5 |
| Why was nothing sent? Answer in one word. | `['empty']` | 5/5 | 5/5 |
| Which file could not be read? Give the path only. | `/nonexistent/reply.txt` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora reply the parser fix is in` (exit 0)

```
[reply] sent -> 1791819604104-0 :: on the bus, nothing has confessed a failure -- which is not the same fact as the operator having read it
```

`aurora reply` (exit 1)

```
[reply] refusing an EMPTY reply -- a header with nothing under it is indistinguishable from a failed send
```

`aurora reply --text-file /nonexistent/reply.txt` (exit 2)

```
[reply] --text-file unreadable (FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/reply.txt') -- not sent.
```


## After: output

`aurora reply the parser fix is in` (exit 0)

```
sent: true
delivery: SENT_NO_FAILURE_RECORDED
to: daniil
id: 1791819647793-0
why: "on the bus, nothing has confessed a failure -- which is not the same fact as the operator having read it"
```

`aurora reply` (exit 1)

```
error: refusing an EMPTY reply -- a header with nothing under it is indistinguishable from a failed send
code: REFUSED
sent: false
delivery: REFUSED
to: daniil
```

`aurora reply --text-file /nonexistent/reply.txt` (exit 2)

```
error: "--text-file unreadable (FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent/reply.txt') -- not sent"
code: USAGE
sent: false
path: /nonexistent/reply.txt
```
