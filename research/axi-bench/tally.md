# AXI bench: `tally`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 28/30 (93%) | 29/30 (97%) | +3 pp |
| Output tokens, as the reader counts them (median) | 975 | 173 | -802 (-82%) |
| Stdout characters (all runs) | 545 | 507 | -38 (-7%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many questions do all counters agree on? | `2` | 5/5 | 5/5 |
| Which question ids are in conflict? List them separated by commas. | `['Q2']` | 3/5 | 4/5 |
| What verdict did deepseek give on Q2? | `KILL` | 5/5 | 5/5 |
| How many counters were found? | `3` | 5/5 | 5/5 |
| Which file names the opening but is not a counter? Give the file name only. | `sol-brief.md` | 5/5 | 5/5 |
| How many counters were found for this opening? | `0` | 5/5 | 5/5 |

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

`aurora tally /tmp/axi-tally-zn_ese07/research/seat-routing-opening-2026-10.md --research-dir /tmp/axi-tally-zn_ese07/research` (exit 0)

```
# tally: seat-routing-opening-2026-10.md  (3 counter(s): claude, deepseek, kimi)
  q     claude    deepseek  kimi      = status
  Q1    KEEP      KEEP      KEEP      = AGREE
  Q2    AMEND     KILL      AMEND     = CONFLICT
  Q3    KILL      KILL      KILL      = AGREE
  Q4    YES       -         YES       = partial
  -- 2 agree / 1 conflict / 1 partial / 0 open
  (mentions, not counters: sol-brief.md)
```

`aurora tally /tmp/axi-tally-zn_ese07/empty/lonely-opening-2026-10.md --research-dir /tmp/axi-tally-zn_ese07/empty` (exit 0)

```
# tally: lonely-opening-2026-10.md  (0 counter(s): none)
  q       = status
  Q1      = open
  -- 0 agree / 0 conflict / 0 partial / 1 open
```


## After: output

`aurora tally /tmp/axi-tally-zn_ese07/research/seat-routing-opening-2026-10.md --research-dir /tmp/axi-tally-zn_ese07/research` (exit 0)

```
opening: seat-routing-opening-2026-10.md
counters: 3
agree: 2
conflict: 1
partial: 1
open: 0
questions[4]{q,claude,deepseek,kimi,status}:
  Q1,KEEP,KEEP,KEEP,AGREE
  Q2,AMEND,KILL,AMEND,CONFLICT
  Q3,KILL,KILL,KILL,AGREE
  Q4,YES,"-",YES,partial
mentions[1]: sol-brief.md
```

`aurora tally /tmp/axi-tally-zn_ese07/empty/lonely-opening-2026-10.md --research-dir /tmp/axi-tally-zn_ese07/empty` (exit 0)

```
opening: lonely-opening-2026-10.md
counters: 0
agree: 0
conflict: 0
partial: 0
open: 1
questions[1]{q,status}:
  Q1,open
help[1]:
  uv run agent_cli.py tally /tmp/axi-tally-zn_ese07/empty/lonely-opening-2026-10.md --research-dir <dir>
```
