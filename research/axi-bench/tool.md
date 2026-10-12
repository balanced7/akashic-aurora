# AXI bench: `tool`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 23/30 (77%) | 30/30 (100%) | +23 pp |
| Output tokens, as the reader counts them (median) | 72 | 96 | +24 (+33%) |
| Stdout characters (all runs) | 509 | 681 | +172 (+34%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agents have play tools? List them separated by commas. | `['claude', 'kimi']` | 5/5 | 5/5 |
| How many play tools are there in total? | `3` | 5/5 | 5/5 |
| How many receipts does the verbthread tool have? | `4` | 5/5 | 5/5 |
| Did the tool run succeed? Answer yes or no. | `no` | 3/5 | 5/5 |
| Does kimi have a play tool named ghost? Answer yes or no. | `no` | 0/5 | 5/5 |
| What exact command runs kimi's premonition tool? Give the command only. | `['tool run kimi/premonition']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | fail | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora tool list` (exit 0)

```
# play tools — sandboxed drafts (GUESS until kata'd)
  [claude]
    campfire               5497B  1 receipt(s)
    verbthread             5295B  4 receipt(s)
  [kimi]
    premonition            8092B  1 receipt(s)

  run one: uv run agent_cli.py tool run <agent>/<tool>
```

`aurora tool list kimi` (exit 0)

```
# play tools — sandboxed drafts (GUESS until kata'd)
  [kimi]
    premonition            8092B  1 receipt(s)

  run one: uv run agent_cli.py tool run <agent>/<tool>
```

`aurora tool run kimi/premonition --timeout 0.001` (exit 1)

```
[tool] CRASH  rc=-1  0.002s  0KB  [GUESS]
  ⚡ violation: timeout (0.001s)
```

`aurora tool run kimi/ghost` (exit 1)

```

```


## After: output

`aurora tool list` (exit 0)

```
play_tools: 3
tools[3]{agent,tool,bytes,receipts}:
  claude,campfire,5497,1
  claude,verbthread,5295,4
  kimi,premonition,8149,1
help[1]:
  uv run agent_cli.py tool run <agent>/<tool>
```

`aurora tool list kimi` (exit 0)

```
agent: kimi
play_tools: 1
tools[1]{agent,tool,bytes,receipts}:
  kimi,premonition,8149,1
help[1]:
  uv run agent_cli.py tool run kimi/premonition
```

`aurora tool run kimi/premonition --timeout 0.001` (exit 1)

```
tool: kimi/premonition
verdict: crash
exit: -1
seconds: 0.002
output_kb: 0
evidence: GUESS
violations[1]: timeout (0.001s)
receipt: data/play/kimi/runs/premonition-1791814841.json
help[1]:
  uv run agent_cli.py tool list kimi
```

`aurora tool run kimi/ghost` (exit 1)

```
error: no play tool kimi/ghost (looked for data/play/kimi/ghost.py)
code: NOT_FOUND
help[1]:
  uv run agent_cli.py tool list
```
