# AXI bench: `wish`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 96 | 66 | -30 (-31%) |
| Stdout characters (all runs) | 295 | 430 | +135 (+46%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the wish filed? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which agent is the new wish attributed to? | `bench` | 0/5 | 5/5 |
| Which wish id appears more than once in the ledger? Give the id only. | `W02` | 5/5 | 5/5 |
| Was a wish filed? Answer yes or no. | `no` | 5/5 | 5/5 |
| What does the command need that was missing? Answer in a few words. | `['text']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora wish bench Make the status verb faster --trigger status took 9s` (exit 0)

```
[wish] WARNING: this ledger's id space has COLLIDED -- W02 each appear more than once, so citing them is ambiguous. Filing anyway; re-number at the next curation.
[wish] filed W04 (bench) -> WISHLIST.md -- cite W04 at the next gate curation
```

`aurora wish bench` (exit 2)

```
[wish] REFUSED: empty wish (pass text or --text-file)
```


## After: output

`aurora wish bench Make the status verb faster --trigger status took 9s` (exit 0)

```
filed: W05
by: bench
ledger: WISHLIST.md
warning: "the ledger's id space has COLLIDED: W02 each appear more than once, so citing them is ambiguous; re-number at the next curation"
cite: cite W05 at the next gate curation
help[1]:
  uv run agent_cli.py wish-curate bench
```

`aurora wish bench` (exit 2)

```
error: "empty wish: pass the wish text or --text-file"
code: USAGE
help[1]:
  uv run agent_cli.py wish bench "<what would have helped>" --trigger "<what hurt>"
```
