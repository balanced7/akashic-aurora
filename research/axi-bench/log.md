# AXI bench: `log`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/20 (100%) | 20/20 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 12 | 43 | +31 (+258%) |
| Stdout characters (all runs) | 80 | 253 | +173 (+216%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the beat recorded? Answer yes or no. | `yes` | 5/5 | 5/5 |
| What kind of beat was recorded? Give the kind only. | `decision` | 5/5 | 5/5 |
| Which database was picked for the ledger, according to the beat? | `['postgres']` | 5/5 | 5/5 |
| Did the caller give this beat a real summary? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora log decision --summary picked Postgres over SQLite for the ledger --source bench:design` (exit 0)

```
[OK] decision: picked Postgres over SQLite for the ledger
```

`aurora log note` (exit 0)

```
[OK] note: no summary
```


## After: output

`aurora log decision --summary picked Postgres over SQLite for the ledger --source bench:design` (exit 0)

```
recorded: true
kind: decision
beat_id: beat_1791820663_2772
summary: picked Postgres over SQLite for the ledger
```

`aurora log note` (exit 0)

```
recorded: true
kind: note
beat_id: beat_1791820664_1667
summary: no summary
warning: no --summary given; the beat was stored as 'no summary'
```
