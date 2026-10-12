# AXI bench: `scout`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 14/25 (56%) | 25/25 (100%) | +44 pp |
| Output tokens, as the reader counts them (median) | 108 | 216 | +108 (+100%) |
| Stdout characters (all runs) | 255 | 802 | +547 (+215%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did the scout produce an answer? Answer yes or no. | `no` | 4/5 | 5/5 |
| Which credential is missing for the scout to answer? Answer in a few words. | `['deepseek']` | 5/5 | 5/5 |
| How many in-flight tasks did the scout's pack hold? | `24` | 5/5 | 5/5 |
| What is the full command to adjudicate the verdict this scout filed? Give the command only. | `['resident adjudicate scout-']` | 0/5 | 5/5 |
| Did the resident scout run? Answer yes or no. | `no` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora scout is anyone working on core/axi --blind` (exit 1)

```
# scout [blind] ask scout-024f03801bf8  (pack: in_flight=24, locks=0, recently_done=12, scout_memory=0)
(no answer -- no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the deepseek door is closed, which is a configuration state and not a model failure)
```

`aurora scout is anyone working on core/axi` (exit 1)

```

```


## After: output

`aurora scout is anyone working on core/axi --blind` (exit 1)

```
ok: false
tier: blind
ask_id: scout-e2a6eb998985
answer: null
why: "no DEEPSEEK_API_KEY and no .secrets/deepseek.key -- the deepseek door is closed, which is a configuration state and not a model failure"
pack:
  in_flight: 24
  locks: 0
  recently_done: 12
  scout_memory: 0
verdict: "filed, unadjudicated"
help[2]:
  uv run agent_cli.py secret deepseek.key
  uv run agent_cli.py resident adjudicate scout-e2a6eb998985 --outcome confirmed|refuted --by <operator>
```

`aurora scout is anyone working on core/axi` (exit 1)

```
error: "refused: 'deepseek' is not a resident (no ratified designation), so there is no identity sheet to carry a role. Run the ceremony first: uv run agent_cli.py resident nominate deepseek --callsign <name> --receipt <their lesson> --by <peer>"
code: REFUSED
help[1]:
  uv run agent_cli.py scout "is anyone working on core/axi" --blind
```
