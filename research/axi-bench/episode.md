# AXI bench: `episode`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 26/30 (87%) | +3 pp |
| Output tokens, as the reader counts them (median) | 19 | 52 | +33 (+174%) |
| Stdout characters (all runs) | 354 | 551 | +197 (+56%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many beats are in the current episode? | `2` | 5/5 | 5/5 |
| Does the current episode have a title yet? Answer yes or no. | `no` | 5/5 | 4/5 |
| What is the full command to close this episode and draft its title? Give the command only. | `['episode close']` | 0/5 | 2/5 |
| What title was drafted for the closed episode? | `fixed the port clash in tests` | 5/5 | 5/5 |
| What is the full command to finalize the episode that was just closed? Give the command only. | `['episode accept ch_']` | 5/5 | 5/5 |
| Did finalizing the episode succeed? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora episode current` (exit 0)

```
[episode] current: (untitled, open) (1s, 2 beats)
```

`aurora episode close` (exit 0)

```
[episode] closed ch_1791813966_5735
  title: fixed the port clash in tests
  desc : fixed the port clash in tests · renamed the config loader
  why  : fixed the port clash in tests
  (edit + finalize: uv run agent_cli.py episode accept ch_1791813966_5735 --title ... --why ...)
```

`aurora episode accept ch_does_not_exist --title x` (exit 1)

```
[episode] unknown_chapter
```


## After: output

`aurora episode current` (exit 0)

```
episode: ch_1791814003_2564
status: open
title: null
beats: 2
duration_s: 1
help[1]:
  uv run agent_cli.py episode close
```

`aurora episode close` (exit 0)

```
closed: ch_1791814003_2564
title: fixed the port clash in tests
description: fixed the port clash in tests · renamed the config loader
why: fixed the port clash in tests
final: false
next_episode: ch_1791814005_2912
help[1]:
  uv run agent_cli.py episode accept ch_1791814003_2564 --title "fixed the port clash in tests"
```

`aurora episode accept ch_does_not_exist --title x` (exit 1)

```
error: no episode ch_does_not_exist to finalize
code: NOT_FOUND
help[1]:
  uv run agent_cli.py episode close
```
