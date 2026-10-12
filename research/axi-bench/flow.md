# AXI bench: `flow`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 21/25 (84%) | 25/25 (100%) | +16 pp |
| Output tokens, as the reader counts them (median) | 251 | 205 | -46 (-18%) |
| Stdout characters (all runs) | 1,671 | 1,272 | -399 (-24%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many flows are in the window? | `4` | 5/5 | 5/5 |
| Who did carol send the handoff to? | `dave` | 5/5 | 5/5 |
| How many flows touch alice? | `3` | 5/5 | 5/5 |
| How many flows does this output show? | `2` | 1/5 | 5/5 |
| What exact command would show every flow? Give the command only. | `['flow', '--limit']` | 5/5 | 5/5 |

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

`aurora flow` (exit 0)

```
# FLOW TRACE -- last 6h   (4 flow(s) | 4 msg(s) | 8 observed | 4 duplicated | window dropped 0)

[flow 1791820352386-0]  1 msg, span single
        0ms  [legacy,work] erin -> alice  chat  175B  x2 COPIES
             '"status: idle"'

[flow 1791820351896-0]  1 msg, span single
        0ms  [legacy,work] carol -> dave  handoff  194B  x2 COPIES
             '"handing off the parser work"'

[flow 1791820351445-0]  1 msg, span single
        0ms  [legacy,work] bob -> alice  chat  187B  x2 COPIES
             '"the build is green on main"'

[flow 1791820351021-0]  1 msg, span single
        0ms  [legacy,work] alice -> bob  request  189B  x2 COPIES
             '"please review core/a.py"'
```

`aurora flow alice` (exit 0)

```
# FLOW TRACE -- last 6h touching alice   (3 flow(s) | 4 msg(s) | 8 observed | 3 duplicated | window dropped 0)

[flow 1791820352386-0]  1 msg, span single
        0ms  [legacy,work] erin -> alice  chat  175B  x2 COPIES
             '"status: idle"'

[flow 1791820351445-0]  1 msg, span single
        0ms  [legacy,work] bob -> alice  chat  187B  x2 COPIES
             '"the build is green on main"'

[flow 1791820351021-0]  1 msg, span single
        0ms  [legacy,work] alice -> bob  request  189B  x2 COPIES
             '"please review core/a.py"'
```

`aurora flow --limit 2` (exit 0)

```
# FLOW TRACE -- last 6h   (4 flow(s) | 4 msg(s) | 8 observed | 4 duplicated | window dropped 0)

[flow 1791820352386-0]  1 msg, span single
        0ms  [legacy,work] erin -> alice  chat  175B  x2 COPIES
             '"status: idle"'

[flow 1791820351896-0]  1 msg, span single
        0ms  [legacy,work] carol -> dave  handoff  194B  x2 COPIES
             '"handing off the parser work"'

  (+2 more flow(s) -- raise --limit)
```


## After: output

`aurora flow` (exit 0)

```
window: 6h
flows: 4
messages: 4
observed: 8
duplicated: 4
dropped_by_window: 0
rows[4]{id,answers,from,to,kind,gap,copies,text}:
  1791820387418-0,null,erin,alice,chat,0s,2,"status: idle"
  1791820386912-0,null,carol,dave,handoff,0s,2,handing off the parser work
  1791820386503-0,null,bob,alice,chat,0s,2,the build is green on main
  1791820386040-0,null,alice,bob,request,0s,2,please review core/a.py
help[1]:
  uv run agent_cli.py bifrost-fetch --get <id> --agent <to>
```

`aurora flow alice` (exit 0)

```
window: 6h
agent: alice
flows: 3
messages: 4
observed: 8
duplicated: 3
dropped_by_window: 0
rows[3]{id,answers,from,to,kind,gap,copies,text}:
  1791820387418-0,null,erin,alice,chat,0s,2,"status: idle"
  1791820386503-0,null,bob,alice,chat,0s,2,the build is green on main
  1791820386040-0,null,alice,bob,request,0s,2,please review core/a.py
help[1]:
  uv run agent_cli.py bifrost-fetch --get <id> --agent <to>
```

`aurora flow --limit 2` (exit 0)

```
window: 6h
flows: 4
shown: 2
messages: 4
observed: 8
duplicated: 4
dropped_by_window: 0
rows[2]{id,answers,from,to,kind,gap,copies,text}:
  1791820387418-0,null,erin,alice,chat,0s,2,"status: idle"
  1791820386912-0,null,carol,dave,handoff,0s,2,handing off the parser work
help[2]:
  uv run agent_cli.py flow --window 6h --limit 4
  uv run agent_cli.py bifrost-fetch --get <id> --agent <to>
```
