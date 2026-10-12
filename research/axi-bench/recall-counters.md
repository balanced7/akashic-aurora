# AXI bench: `recall-counters`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 29/30 (97%) | 30/30 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 117 | 122 | +5 (+4%) |
| Stdout characters (all runs) | 539 | 379 | -160 (-30%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many bare-slug counters would be merged? | `0` | 5/5 | 5/5 |
| How many credited ghost counters are kept? | `2` | 5/5 | 5/5 |
| Which credited ghosts are kept? List their sources separated by commas. | `['learn:experiment:renamed_away', 'learn:experiment:retired_rule']` | 5/5 | 5/5 |
| Did this run change anything? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many zero-credit ghosts were pruned? | `0` | 5/5 | 5/5 |
| What exact command applies the fix? Give the command only. | `['recall-counters', '--fold']` | 4/5 | 5/5 |

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

`aurora recall-counters` (exit 0)

```
# COUNTER HYGIENE (S2a)  -- report only; apply with --fold
  bare-slug counters to merge : 0   []
  zero-credit ghosts to prune : 0   []
  credited ghosts (KEPT; S2 adjudicates): 2   ['learn:experiment:renamed_away', 'learn:experiment:retired_rule']
```

`aurora recall-counters --fold` (exit 0)

```
[OK] folded 0 bare-slug counter(s) into canonical keys.
[OK] pruned 0 zero-credit ghost(s): []
[!] KEPT 2 credited ghost(s) -- these carry earned signal and
    need an S2 decision (fold credit into the successor lesson): ['learn:experiment:renamed_away', 'learn:experiment:retired_rule']
```


## After: output

`aurora recall-counters` (exit 0)

```
mode: report only
bare_slugs_to_merge: 0
ghosts_to_prune: 0
credited_ghosts_kept: 2
credited_ghosts[2]: "learn:experiment:renamed_away","learn:experiment:retired_rule"
help[2]:
  uv run agent_cli.py recall-counters --fold
  uv run agent_cli.py triage
```

`aurora recall-counters --fold` (exit 0)

```
merged: 0
pruned: 0
credited_ghosts_kept: 2
credited_ghosts[2]: "learn:experiment:renamed_away","learn:experiment:retired_rule"
```
