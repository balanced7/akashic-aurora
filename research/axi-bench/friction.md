# AXI bench: `friction`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/25 (96%) | 25/25 (100%) | +4 pp |
| Output tokens, as the reader counts them (median) | 415 | 290 | -125 (-30%) |
| Stdout characters (all runs) | 858 | 500 | -358 (-42%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many of bench's asks are still open? | `2` | 5/5 | 5/5 |
| How many of bench's asks were answered? | `2` | 5/5 | 5/5 |
| Which peers still have an open ask from bench? List them separated by commas. | `['bob', 'dave']` | 5/5 | 5/5 |
| What is the dead rate, as a percentage? | `0` | 4/5 | 5/5 |
| Did any ask die? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora friction bench` (exit 0)

```
# friction -- bench (window 168h)
open 2 | answered 2 | echo 0 | dead 0 | dead-rate 0.0%
time-to-settle p50 2.0s p90 2.9s
by peer (worst first):
  alice                  answered   1 | dead   0 | echo   0 | open   0 | dead-rate   0% | median 3s
  bob                    answered   0 | dead   0 | echo   0 | open   1 | dead-rate  n/a | median n/a
  carol                  answered   1 | dead   0 | echo   0 | open   0 | dead-rate   0% | median 2s
  dave                   answered   0 | dead   0 | echo   0 | open   1 | dead-rate  n/a | median n/a
  ANSWERED        1791814493363-0 -> alice | took 2.9s | redrives 0
  ANSWERED        1791814494300-0 -> carol | took 2.0s | redrives 0
  OPEN.DISPATCHED 1791814493819-0 -> bob | age 2.9s | redrives 0 | deadline in 1797.1s
  OPEN.DISPATCHED 1791814494790-0 -> dave | age 1.9s | redrives 0 | deadline in 1798.1s
```


## After: output

`aurora friction bench` (exit 0)

```
agent: bench
window_h: 168
open: 2
answered: 2
echo: 0
dead: 0
dead_rate: 0
settle_p50_s: 1.9
settle_p90_s: 2.9
peers[4]{peer,open,answered,dead,dead_rate}:
  alice,0,1,0,0
  bob,1,0,0,null
  carol,0,1,0,0
  dave,1,0,0,null
episodes: 4
asks[4]{ask_id,peer,status,secs,redrives}:
  1791814530453-0,bob,open (dispatched),2.8,0
  1791814531362-0,dave,open (dispatched),1.9,0
  1791814529964-0,alice,answered,2.9,0
  1791814530915-0,carol,answered,1.9,0
help[1]:
  uv run agent_cli.py bifrost-sync bench
```
