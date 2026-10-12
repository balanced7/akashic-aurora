# AXI bench: `recall-curate`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 34/35 (97%) | 34/35 (97%) | +0 pp |
| Output tokens, as the reader counts them (median) | 64 | 83 | +19 (+30%) |
| Stdout characters (all runs) | 869 | 885 | +16 (+2%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are in the corpus? | `3` | 5/5 | 4/5 |
| How many lessons are still competing for recall surface slots? | `2` | 5/5 | 5/5 |
| How many lessons would be benched? | `0` | 5/5 | 5/5 |
| How many credited ghost counters are kept for a decision? | `1` | 5/5 | 5/5 |
| What is the verdict for the c5 no-go criterion? | `clear` | 5/5 | 5/5 |
| How many optimizer proposals are pending? | `0` | 4/5 | 5/5 |
| What does the command need that was not given? Name the flag. | `['--draft']` | 5/5 | 5/5 |

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

`aurora recall-curate` (exit 0)

```
[recall-curate] corpus 3 | on-surface 2 | bench-candidates 0 | unbench 0 | ghost counters to prune 0 (+1 credited ghosts kept for adjudication)
```

`aurora recall-curate --apply` (exit 0)

```
[recall-curate] corpus 3 | on-surface 2 | bench-candidates 0 | unbench 0 | ghost counters to prune 0 (+1 credited ghosts kept for adjudication)
[recall-curate] APPLIED: benched 0, unbenched 0, ghost counters pruned 0
```

`aurora recall-curate --forge-proposals` (exit 0)

```
[forge-proposals] none pending
```

`aurora recall-curate --forge-check keep_one` (exit 2)

```
ERROR: --forge-check needs --draft FILE (the proposed recommendation text).
Example: uv run agent_cli.py recall-curate --forge-check keep_one --draft new_text.md
```

`aurora recall-curate --forge-audit` (exit 0)

```
[forge-audit] flips 0 | targets replayable n/a | credited lessons 0 (>=2 ctx: 0) | rehab candidates 0 (coverage n/a) | ledger retention Noned
  fidelity: 0/0 ledgered sources re-surface on replay (n/a)
  c1_fidelity: NA
  c2_rehab_coverage: NA
  c3_credited_coverage: NA
  c5_no_go: clear
  c4_fallback: not needed
```


## After: output

`aurora recall-curate` (exit 0)

```
corpus: 3
on_surface: 2
to_bench: 0
to_unbench: 0
ghosts_to_prune: 0
credited_ghosts_kept: 1
result: nothing to curate
help[1]:
  uv run agent_cli.py triage
```

`aurora recall-curate --apply` (exit 0)

```
corpus: 3
on_surface: 2
to_bench: 0
to_unbench: 0
ghosts_to_prune: 0
credited_ghosts_kept: 1
applied:
  benched: 0
  unbenched: 0
  ghosts_pruned: 0
```

`aurora recall-curate --forge-proposals` (exit 0)

```
pending: 0
help[1]:
  uv run agent_cli.py recall-curate --forge-propose
```

`aurora recall-curate --forge-check keep_one` (exit 2)

```
error: "--forge-check needs --draft FILE (the proposed recommendation text)"
code: USAGE
help[1]:
  uv run agent_cli.py recall-curate --forge-check keep_one --draft new_text.md
```

`aurora recall-curate --forge-audit` (exit 0)

```
flips: 0
flip_targets_replayable: null
credited_lessons: 0
credited_in_2_plus_contexts: 0
rehab_candidates: 0
rehab_coverage: null
ledger_retention_days: null
fidelity:
  agreed: 0
  checked: 0
  rate: null
verdicts:
  c1_fidelity: NA
  c2_rehab_coverage: NA
  c3_credited_coverage: NA
  c5_no_go: clear
  c4_fallback: not needed
```
