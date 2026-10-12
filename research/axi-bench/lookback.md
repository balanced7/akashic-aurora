# AXI bench: `lookback`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 24/25 (96%) | -4 pp |
| Output tokens, as the reader counts them (median) | 208 | 171 | -37 (-18%) |
| Stdout characters (all runs) | 612 | 663 | +51 (+8%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many hits did the lookback return? | `2` | 5/5 | 5/5 |
| Is the hit about the old cache design current or retired? Answer current or retired. | `retired` | 5/5 | 5/5 |
| According to the top hit, what was quokkadb picked over? | `leveldb` | 5/5 | 4/5 |
| Which corpus layer did the hits come from? | `notes` | 5/5 | 5/5 |
| How many hits did the lookback return? | `0` | 5/5 | 5/5 |

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

`aurora lookback why quokkadb --layers notes` (exit 0)

```
# lookback: why quokkadb

## notes
  [current] mem:decision:ADR_1012174359_1ea2d00f  (rel 1.0)
      Chose quokkadb for the embedded store We picked quokkadb over leveldb because it ships with python and survives crashes
      drill: notes --all (id ADR_1012174359_1ea2d00f)
  [retired] mem:decision:ADR_1012174400_f3acb51f  (rel 1.0)
      ...ld cache design The quokkadb cache layer was dropped in favour of redis
      drill: notes --all (id ADR_1012174400_f3acb51f)
```

`aurora lookback zebra unicorn --layers notes` (exit 0)

```
# lookback: nothing above the relevance floor for: 'zebra unicorn'
  (try different terms; layers: docs,research,notes,promoted,chapters,git)
```


## After: output

`aurora lookback why quokkadb --layers notes` (exit 0)

```
question: why quokkadb
layers[1]: notes
total: 2
hits[2]{layer,status,score,excerpt,drill}:
  notes,current,1,Chose quokkadb for the embedded store We picked quokkadb over leveldb because it ships with python and survives crashes,notes --all (id ADR_1012174433_93f0d0ed)
  notes,retired,1,...ld cache design The quokkadb cache layer was dropped in favour of redis,notes --all (id ADR_1012174434_c12944ea)
```

`aurora lookback zebra unicorn --layers notes` (exit 0)

```
question: zebra unicorn
layers[1]: notes
total: 0
note: nothing above the relevance floor
hits: []
help[2]:
  uv run agent_cli.py lookback <other words>
  uv run agent_cli.py lookback zebra unicorn --layers docs,charters,research,notes,promoted,chapters,git
```
