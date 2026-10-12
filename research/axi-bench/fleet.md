# AXI bench: `fleet`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 32/35 (91%) | 32/35 (91%) | +0 pp |
| Output tokens, as the reader counts them (median) | 428 | 394 | -34 (-8%) |
| Stdout characters (all runs) | 1,304 | 1,619 | +315 (+24%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many models are in the roster? | `8` | 5/5 | 5/5 |
| Which models have the status gated? Give the model names, separated by commas. | `['gpt-oss:20b', 'qwen3-coder:30b']` | 4/5 | 5/5 |
| What is the context window, in tokens, of glm-4.7-flash? | `64000` | 5/5 | 5/5 |
| How many GB of VRAM does qwen3.5:4b need? | `4` | 5/5 | 3/5 |
| Which model tag was selected? | `glm-4.7-flash` | 5/5 | 5/5 |
| Did any model fit the request? Answer yes or no. | `no` | 4/5 | 4/5 |
| Which two flags does `fleet call` need? List them separated by commas. | `['--model', '--prompt']` | 4/5 | 5/5 |

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

`aurora fleet` (exit 0)

```
# FLEET ROSTER  (8 model(s))
  active    glm-4.7-flash        14GB   25tps   ctx=64000  [generalist, research, tool-use, long-context]
  candidate qwen3.5:9b           7GB    ?tps    ctx=32000  [generalist, tool-use, instruction-following, research]
  candidate qwen3.5:4b           4GB    ?tps    ctx=32000  [classify, extract, summarize, instruction-following]
  candidate granite-4.0-h-small  ?GB    ?tps    ctx=32000  [extract, faithful, summarize]
  candidate gemma-3-12b-it       ?GB    ?tps    ctx=32000  [summarize, faithful]
  candidate qwen3-8b             ?GB    ?tps    ctx=32000  [generalist, classify, extract]
  gated     gpt-oss:20b          14GB   9tps    ctx=64000  [reasoning]
            GATED: fluent fabrication citing an unreadable PDF + loop collapse (bakeoff 2026-07)
  gated     qwen3-coder:30b      19GB   ?tps    ctx=64000  [code, generalist, tool-use]
            GATED: citation laundering (bakeoff 2026-07)
```

`aurora fleet select --capability generalist` (exit 0)

```
# FLEET SELECT -> glm-4.7-flash  (active, 14GB, ctx=64000)
  why: capability=generalist + constraints; Won bakeoff round 1 on citation honesty; the fleet default generalist. Spills past 16GB only above ~32K ctx.
```

`aurora fleet select --capability extract` (exit 1)

```
# FLEET SELECT -- nothing fits (capability=extract, max_vram=None, min_context=None, status=active)
```

`aurora fleet call` (exit 2)

```
ERROR: fleet call needs --model TAG and --prompt TEXT
```


## After: output

`aurora fleet` (exit 0)

```
total: 8
models[8]{tag,status,vram_gb,context,capabilities,why_gated}:
  glm-4.7-flash,active,14,64000,generalist research tool-use long-context,null
  "qwen3.5:9b",candidate,7,32000,generalist tool-use instruction-following research,null
  "qwen3.5:4b",candidate,4,32000,classify extract summarize instruction-following,null
  granite-4.0-h-small,candidate,null,32000,extract faithful summarize,null
  gemma-3-12b-it,candidate,null,32000,summarize faithful,null
  qwen3-8b,candidate,null,32000,generalist classify extract,null
  "gpt-oss:20b",gated,14,64000,reasoning,fluent fabrication citing an unreadable PDF + loop collapse (bakeoff 2026-07)
  "qwen3-coder:30b",gated,19,64000,code generalist tool-use,citation laundering (bakeoff 2026-07)
help[2]:
  uv run agent_cli.py fleet select --capability <capability>
  uv run agent_cli.py fleet call --model <tag> --prompt "<text>"
```

`aurora fleet select --capability generalist` (exit 0)

```
selected: glm-4.7-flash
status: active
vram_gb: 14
context: 64000
asked:
  capability: generalist
  status: active
why: Won bakeoff round 1 on citation honesty; the fleet default generalist. Spills past 16GB only above ~32K ctx.
help[1]:
  uv run agent_cli.py fleet call --model glm-4.7-flash --prompt "<text>"
```

`aurora fleet select --capability extract` (exit 1)

```
error: "nothing fits: no model matches the capability and constraints"
code: NO_FIT
asked: "capability=extract, status=active"
help[2]:
  uv run agent_cli.py fleet --capability extract
  uv run agent_cli.py fleet select --capability extract --status candidate
```

`aurora fleet call` (exit 2)

```
error: fleet call needs --model TAG and --prompt TEXT
code: USAGE
help[2]:
  uv run agent_cli.py fleet call --model <tag> --prompt "<text>"
  uv run agent_cli.py fleet
```
