# AXI bench: `clobber-scan`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 23/25 (92%) | 25/25 (100%) | +8 pp |
| Output tokens, as the reader counts them (median) | 93 | 128 | +35 (+38%) |
| Stdout characters (all runs) | 229 | 279 | +50 (+22%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many unguarded control-key writes were found? | `3` | 5/5 | 5/5 |
| On which line numbers are the unguarded writes? List them separated by commas. | `['5', '14', '15']` | 4/5 | 5/5 |
| Which control family does the write on line 14 touch? | `cursor` | 4/5 | 5/5 |
| Is the control.resume() call on line 10 flagged? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many unguarded control-key writes were found? | `0` | 5/5 | 5/5 |

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

`aurora clobber-scan /tmp/axi-clobber-pu3y618r/ceremony.py` (exit 1)

```
clobber-scan: 3 unguarded control-key write(s)
  L5 [pause]: c.set(_pause_key(), "1")
  L14 [cursor]: c.delete(_cursor_key(lane))
  L15 [drain]: c.set(_drain_key(lane), "1")
```

`aurora clobber-scan /tmp/axi-clobber-pu3y618r/clean.py` (exit 0)

```
clobber-scan: clean -- no unguarded control-key writes
```


## After: output

`aurora clobber-scan /tmp/axi-clobber-pu3y618r/ceremony.py` (exit 1)

```
findings: 3
writes[3]{line,family,snippet}:
  5,pause,"c.set(_pause_key(), \"1\")"
  14,cursor,c.delete(_cursor_key(lane))
  15,drain,"c.set(_drain_key(lane), \"1\")"
review: "no same-family read-guard earlier in the function: add a was_/is_ guard or confirm intent"
```

`aurora clobber-scan /tmp/axi-clobber-pu3y618r/clean.py` (exit 0)

```
findings: 0
```
