# AXI bench: `wish-curate`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 334 | 269 | -65 (-19%) |
| Stdout characters (all runs) | 1,002 | 959 | -43 (-4%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many wishes are open? | `5` | 5/5 | 5/5 |
| How many wishes have been folded? | `2` | 5/5 | 5/5 |
| Which is the oldest open wish? Give its id only. | `W01` | 5/5 | 5/5 |
| Who filed wish W03? | `deepseek` | 5/5 | 5/5 |
| What command declines wish W02? Give the command only. | `['wish-curate bench', '--id w02', '--as decline', '--reason']` | 5/5 | 5/5 |
| Was the wish declined? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora wish-curate bench` (exit 0)

```
# wishlist: 5 open | 2 folded | 0 declined
#   DECLINE HAS NEVER BEEN USED. With it unused, 'open' means both 'queued' and
#   'never', and the two render identically -- which is why filing stops.
#
# the 3 oldest open, awaiting a disposition:
  W01    (07-18, claude) Make recall faster on big stores.
  W02    (07-20, kimi) Show lock ttl in human units.
  W03    (08-01, deepseek) Doctor should name the dead seat.

# dispose of one with:
#   uv run agent_cli.py wish-curate bench --id W## --as fold --task T### [--reason ...]
#   uv run agent_cli.py wish-curate bench --id W## --as keep --reason '<why still>'
#   uv run agent_cli.py wish-curate bench --id W## --as decline --reason '<why not>'
# a DECLINE is the loop working. Nothing is ever deleted -- declined wishes teach too.
```

`aurora wish-curate bench --id W77 --as keep --reason still wanted` (exit 2)

```
[wish-curate] REFUSED: no wish W77 in the ledger -- refusing rather than silently doing nothing
```

`aurora wish-curate bench --id W01 --as decline` (exit 2)

```
[wish-curate] REFUSED: decline needs --reason: an undeclared decline is exactly the silent state this verb exists to end
```


## After: output

`aurora wish-curate bench` (exit 0)

```
open: 5
folded: 2
declined: 0
note: "decline has never been used: with it unused, 'open' means both 'queued' and 'never', and the two render identically -- which is why filing stops"
shown: 3
oldest_open[3]{id,filed,by,wish}:
  W01,07-18,claude,Make recall faster on big stores.
  W02,07-20,kimi,Show lock ttl in human units.
  W03,08-01,deepseek,Doctor should name the dead seat.
help[3]:
  uv run agent_cli.py wish-curate bench --id W## --as fold --task T###
  uv run agent_cli.py wish-curate bench --id W## --as keep --reason '<why still>'
  uv run agent_cli.py wish-curate bench --id W## --as decline --reason '<why not>'
```

`aurora wish-curate bench --id W77 --as keep --reason still wanted` (exit 2)

```
error: "refused: no wish W77 in the ledger -- refusing rather than silently doing nothing"
code: REFUSED
help[1]:
  uv run agent_cli.py wish-curate bench
```

`aurora wish-curate bench --id W01 --as decline` (exit 2)

```
error: "refused: decline needs --reason: an undeclared decline is exactly the silent state this verb exists to end"
code: REFUSED
help[1]:
  uv run agent_cli.py wish-curate bench
```
