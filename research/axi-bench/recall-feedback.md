# AXI bench: `recall-feedback`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 33 | 45 | +12 (+36%) |
| Stdout characters (all runs) | 352 | 365 | +13 (+4%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the vote recorded? Answer yes or no. | `yes` | 5/5 | 5/5 |
| In which domain was the lesson credited? | `vfx` | 5/5 | 5/5 |
| Will this lesson now surface in every domain? Answer yes or no. | `yes` | 5/5 | 5/5 |
| How many useful votes does this lesson have now? | `2` | 0/5 | 5/5 |
| What kind of vote was recorded: useful or noise? | `noise` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora recall-feedback --source learn:experiment:tonemap_order --useful --domain vfx` (exit 0)

```
[recall-feedback] recorded: useful <- learn:experiment:tonemap_order (domain: vfx)
```

`aurora recall-feedback --source learn:experiment:tonemap_order --useful --domain system` (exit 0)

```
[recall-feedback] recorded: useful <- learn:experiment:tonemap_order (domain: system)
[recall-feedback] this lesson has now earned credit in 2+ domains -- it is DOMAIN-GENERAL and will surface everywhere.
```

`aurora recall-feedback --source learn:experiment:noisy_one --noise` (exit 0)

```
[recall-feedback] recorded: noise <- learn:experiment:noisy_one
```


## After: output

`aurora recall-feedback --source learn:experiment:tonemap_order --useful --domain vfx` (exit 0)

```
recorded: useful
source: "learn:experiment:tonemap_order"
domain: vfx
useful_votes: 1
noise_votes: 0
```

`aurora recall-feedback --source learn:experiment:tonemap_order --useful --domain system` (exit 0)

```
recorded: useful
source: "learn:experiment:tonemap_order"
domain: system
useful_votes: 2
noise_votes: 0
domain_general: "yes -- credited in 2+ domains, it now surfaces everywhere"
```

`aurora recall-feedback --source learn:experiment:noisy_one --noise` (exit 0)

```
recorded: noise
source: "learn:experiment:noisy_one"
useful_votes: 0
noise_votes: 1
```
