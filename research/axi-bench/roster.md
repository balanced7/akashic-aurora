# AXI bench: `roster`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 22/30 (73%) | 30/30 (100%) | +27 pp |
| Output tokens, as the reader counts them (median) | 281 | 182 | -99 (-35%) |
| Stdout characters (all runs) | 838 | 611 | -227 (-27%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many seats does the roster list? | `2` | 5/5 | 5/5 |
| What state is alice's seat in? | `LIVE` | 1/5 | 5/5 |
| Which phase was bob's seat in at its last beat? | `sync` | 5/5 | 5/5 |
| Is any agent churning? Answer yes or no. | `no` | 1/5 | 5/5 |
| Does this roster check whether the seat's process is actually alive? Answer yes or no. | `no` | 5/5 | 5/5 |
| What command checks the things this roster does not? Give the command only. | `['doctor']` | 5/5 | 5/5 |

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

`aurora roster` (exit 0)

```
# seat roster (bifrost) -- 2 seat(s)
  [LIVE ] alice#benchsea           phase=sync       beat=   1.4s seq=1     have: legacy_inbox_shared@0,seat_inbox@0,reaper@0,lane_inbox_shared@0
  [LIVE ] bob#benchsea             phase=sync       beat=   0.7s seq=1     have: legacy_inbox_shared@0,seat_inbox@0,reaper@0,lane_inbox_shared@0
  checked:     bifrost:worklive:<agent>#<sid8> keys (TTL 180s, fresh<= 45s) + cursor positions (have-summary)
  NOT checked: process liveness (a beating loop can host a wedged model) | wake watcher armed | runner locks | role-queue claims -- doctor covers those
```

`aurora roster --by-agent` (exit 0)

```
# seat roster BY AGENT -- 2 agent(s) (raw incarnations: `roster` without --by-agent)
  [LIVE ] alice                #benchsea  beat=     1.9s phase=sync      dead=0  
  [LIVE ] bob                  #benchsea  beat=     1.2s phase=sync      dead=0
```


## After: output

`aurora roster` (exit 0)

```
namespace: bifrost
seats: 2
live: 2
seat_rows[2]{seat,state,phase,beat_age_s,code}:
  alice#benchsea,LIVE,sync,1.1,current
  bob#benchsea,LIVE,sync,0.5,current
checked: "worklive keys (TTL 180s, fresh <= 45s) and cursor positions"
not_checked: "process liveness, wake watcher, runner locks, role-queue claims (doctor covers those)"
help[1]:
  uv run agent_cli.py doctor
```

`aurora roster --by-agent` (exit 0)

```
namespace: bifrost
agents: 2
by_agent[2]{agent,state,live_seat,beat_age_s,dead,recent_deaths,churning}:
  alice,LIVE,benchsea,1.5,0,0,false
  bob,LIVE,benchsea,0.9,0,0,false
help[2]:
  uv run agent_cli.py roster
  uv run agent_cli.py doctor
```
