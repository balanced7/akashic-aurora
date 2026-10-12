# AXI bench: `learn`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 155 | 186 | +31 (+20%) |
| Stdout characters (all runs) | 588 | 684 | +96 (+16%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the lesson recorded? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which existing lesson does the new lesson overlap with? Give its name only. | `port_clash` | 5/5 | 5/5 |
| On how many of the 5 dimensions does it overlap that lesson? | `3` | 5/5 | 5/5 |
| What exact command would tag this failure as a known anti-pattern? Give the command only. | `['tag-anti-pattern alice', '--experiment port_clash_again']` | 5/5 | 5/5 |
| Was a lesson recorded? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which flag must be added for the command to work? Give the flag only. | `['--experiment']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora learn alice --experiment port_clash_again --tried ran the suite --result hung at start --recommend Use when tests hang at start: check port 16379 is free. --category performance --success no` (exit 0)

```
[OK] recorded lesson 'port_clash_again' (category: performance, success: no)
[hint] if this failure names a reusable known-bad, tag it so recall can warn others:
       uv run agent_cli.py tag-anti-pattern alice --experiment port_clash_again --name suite   (edit the name if a better fits)
[i] related lesson: 'port_clash' (3/5 dims) -- consolidation-pass candidate. Edge stamped on this record (related_to).
```

`aurora learn alice --tried something` (exit 2)

```
ERROR: need --experiment and at least one of --tried/--result.
Example: uv run agent_cli.py learn me --experiment cache_fix --tried "memoize" --result "+50%" --recommend "use it"
```


## After: output

`aurora learn alice --experiment port_clash_again --tried ran the suite --result hung at start --recommend Use when tests hang at start: check port 16379 is free. --category performance --success no` (exit 0)

```
recorded: true
lesson: port_clash_again
category: performance
success: no
related:
  lesson: port_clash
  dims: 3/5
  advice: consolidation-pass candidate
  edge: stamped (related_to)
anti_pattern_hint: "tag it if this failure names a reusable known-bad, so recall warns others (edit the drafted name)"
help[2]:
  uv run agent_cli.py tag-anti-pattern alice --experiment port_clash_again --name suite
  uv run agent_cli.py recall --full learn:experiment:port_clash
```

`aurora learn alice --tried something` (exit 2)

```
error: "no lesson was written: need --experiment and at least one of --tried/--result"
code: USAGE
help[1]:
  uv run agent_cli.py learn alice --experiment cache_fix --tried "memoize" --result "+50%" --recommend "use it"
```
