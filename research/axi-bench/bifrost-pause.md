# AXI bench: `bifrost-pause`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 67 | 92 | +25 (+37%) |
| Stdout characters (all runs) | 310 | 423 | +113 (+36%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is in-flight work abandoned by this pause? Answer yes or no. | `yes` | 5/5 | 5/5 |
| After how many seconds does the pause clear itself? | `600` | 5/5 | 5/5 |
| Is in-flight work abandoned by this pause? Answer yes or no. | `no` | 5/5 | 5/5 |
| Does this pause clear itself after a time limit? Answer yes or no. | `no` | 0/5 | 5/5 |
| What command ends the pause? Give the command only. | `['bifrost-resume']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-pause --reason operator barge-in --ttl 600` (exit 0)

```
[bifrost] PAUSED (self-heals in 600s) -- runners frozen mid-turn (in-flight work is abandoned); for a graceful stop use `--soft`; resume with `bifrost-resume`
```

`aurora bifrost-pause --reason wind down --soft` (exit 0)

```
[bifrost] SOFT PAUSE -- seats FINISH the message in hand, then hold. In-flight work is NOT abandoned and no runner exits; resume with `bifrost-resume`
```


## After: output

`aurora bifrost-pause --reason operator barge-in --ttl 600` (exit 0)

```
status: paused
mode: hard
self_heals_in_s: 600
in_flight_work: "abandoned: runners freeze mid-turn (--soft lets them finish)"
by: user
reason: operator barge-in
help[1]:
  uv run agent_cli.py bifrost-resume
```

`aurora bifrost-pause --reason wind down --soft` (exit 0)

```
status: paused
mode: soft
self_heals: never; holds until bifrost-resume
in_flight_work: "finished first, then the seat holds; no runner exits"
by: user
reason: wind down
help[1]:
  uv run agent_cli.py bifrost-resume
```
