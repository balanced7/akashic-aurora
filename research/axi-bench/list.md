# AXI bench: `list`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 3 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 12/12 (100%) | 12/12 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 912 | 575 | -337 (-37%) |
| Stdout characters (all runs) | 2,056 | 1,249 | -807 (-39%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are stored in memory in total? | `28` | 3/3 | 3/3 |
| Does this output show every stored lesson? Answer yes or no. | `no` | 3/3 | 3/3 |
| Which category is the lesson filler_07 in? | `testing` | 3/3 | 3/3 |
| How many lessons does this output show? | `25` | 3/3 | 3/3 |

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

`aurora list` (exit 0)

```
# 28 all lessons
  - [docs] filler_28: Lesson number 28. (source: learn:experiment:filler_28)
  - [testing] filler_27: Lesson number 27. (source: learn:experiment:filler_27)
  - [docs] filler_26: Lesson number 26. (source: learn:experiment:filler_26)
  - [testing] filler_25: Lesson number 25. (source: learn:experiment:filler_25)
  - [docs] filler_24: Lesson number 24. (source: learn:experiment:filler_24)
  - [testing] filler_23: Lesson number 23. (source: learn:experiment:filler_23)
  - [docs] filler_22: Lesson number 22. (source: learn:experiment:filler_22)
  - [testing] filler_21: Lesson number 21. (source: learn:experiment:filler_21)
  - [docs] filler_20: Lesson number 20. (source: learn:experiment:filler_20)
  - [testing] filler_19: Lesson number 19. (source: learn:experiment:filler_19)
  - [docs] filler_18: Lesson number 18. (source: learn:experiment:filler_18)
  - [testing] filler_17: Lesson number 17. (source: learn:experiment:filler_17)
  - [docs] filler_16: Lesson number 16. (source: learn:experiment:filler_16)
  - [testing] filler_15: Lesson number 15. (source: learn:experiment:filler_15)
  - [docs] filler_14: Lesson number 14. (source: learn:experiment:filler_14)
  - [testing] filler_13: Lesson number 13. (source: learn:experiment:filler_13)
  - [docs] filler_12: Lesson number 12. (source: learn:experiment:filler_12)
  - [testing] filler_11: Lesson number 11. (source: learn:experiment:filler_11)
  - [docs] filler_10: Lesson number 10. (source: learn:experiment:filler_10)
  - [testing] filler_09: Lesson number 9. (source: learn:experiment:filler_09)
  - [docs] filler_08: Lesson number 8. (source: learn:experiment:filler_08)
  - [testing] filler_07: Lesson number 7. (source: learn:experiment:filler_07)
  - [docs] filler_06: Lesson number 6. (source: learn:experiment:filler_06)
  - [testing] filler_05: Lesson number 5. (source: learn:experiment:filler_05)
  - [docs] filler_04: Lesson number 4. (source: learn:experiment:filler_04)
# 25 of 28 lesson(s) shown; `recall --json` with the same query returns all matches
```


## After: output

`aurora list` (exit 0)

```
total: 28
shown: 25
lessons[25]{name,category,status,lesson}:
  filler_28,docs,active,Lesson number 28.
  filler_27,testing,active,Lesson number 27.
  filler_26,docs,active,Lesson number 26.
  filler_25,testing,active,Lesson number 25.
  filler_24,docs,active,Lesson number 24.
  filler_23,testing,active,Lesson number 23.
  filler_22,docs,active,Lesson number 22.
  filler_21,testing,active,Lesson number 21.
  filler_20,docs,active,Lesson number 20.
  filler_19,testing,active,Lesson number 19.
  filler_18,docs,active,Lesson number 18.
  filler_17,testing,active,Lesson number 17.
  filler_16,docs,active,Lesson number 16.
  filler_15,testing,active,Lesson number 15.
  filler_14,docs,active,Lesson number 14.
  filler_13,testing,active,Lesson number 13.
  filler_12,docs,active,Lesson number 12.
  filler_11,testing,active,Lesson number 11.
  filler_10,docs,active,Lesson number 10.
  filler_09,testing,active,Lesson number 9.
  filler_08,docs,active,Lesson number 8.
  filler_07,testing,active,Lesson number 7.
  filler_06,docs,active,Lesson number 6.
  filler_05,testing,active,Lesson number 5.
  filler_04,docs,active,Lesson number 4.
help[2]:
  uv run agent_cli.py recall --full learn:experiment:<name>
  uv run agent_cli.py list --limit 28
```
