# AXI bench: `note`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 24/25 (96%) | -4 pp |
| Output tokens, as the reader counts them (median) | 48 | 42 | -6 (-12%) |
| Stdout characters (all runs) | 315 | 370 | +55 (+17%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did this note replace an earlier note with the same title? Answer yes or no. | `yes` | 5/5 | 4/5 |
| According to the note, what comes next? Answer in a few words. | `['ledger table']` | 5/5 | 5/5 |
| Where was this decided, according to the note's context? | `['monday']` | 5/5 | 5/5 |
| Was a note found? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which command lists the notes that do exist? Give the command only. | `['notes']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora note alice --title where-we-are --note Wave 3 done; next: migrate the ledger table. --context decided at the Monday sync` (exit 0)

```
[OK] noted 'where-we-are' (id ADR_1012173922_70356d52) - superseded prior ADR_1012173921_6b9f61e6
```

`aurora note alice --get where-we-are` (exit 0)

```
# where-we-are  (id ADR_1012173922_70356d52, 2026-10-12T17:39:22.498692)
Wave 3 done; next: migrate the ledger table.

[context] decided at the Monday sync
```

`aurora note alice --get never-existed` (exit 1)

```
ERROR: no note with id or title 'never-existed' (see: notes)
```


## After: output

`aurora note alice --title where-we-are --note Wave 3 done; next: migrate the ledger table. --context decided at the Monday sync` (exit 0)

```
noted: where-we-are
id: ADR_1012173954_e4223797
superseded: ADR_1012173953_ad043cbf
```

`aurora note alice --get where-we-are` (exit 0)

```
title: where-we-are
id: ADR_1012173954_e4223797
at: "2026-10-12T17:39:54.419834"
status: active
note: "Wave 3 done; next: migrate the ledger table."
context: decided at the Monday sync
```

`aurora note alice --get never-existed` (exit 1)

```
error: no note with id or title 'never-existed'
code: NOT_FOUND
help[1]:
  uv run agent_cli.py notes
```
