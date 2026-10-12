# AXI bench: `replay`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/30 (80%) | 29/30 (97%) | +17 pp |
| Output tokens, as the reader counts them (median) | 21 | 87 | +66 (+314%) |
| Stdout characters (all runs) | 283 | 757 | +474 (+167%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many candidate harnesses are listed? | `2` | 5/5 | 5/5 |
| Which harness does the candidate codex-low use? | `codex-cli` | 5/5 | 4/5 |
| What effort level is opus-high set to? | `high` | 4/5 | 5/5 |
| Did the replay run start? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which Redis db number should be passed instead so the run is allowed? Give the number only. | `15` | 0/5 | 5/5 |
| Which flag is missing from this replay run command? Give the flag only. | `--scenario` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora replay candidates` (exit 0)

```
  codex-low            codex-cli    model=gpt-5 effort=low  
  opus-high            claude-code  model=claude-opus-5-5 effort=high  more effort fixes more scenarios
```

`aurora replay run --candidate opus-high --scenario T1-abc --redis-db 0` (exit 2)

```
ERROR: --redis-db 0 is the live store; a replay never runs there
```

`aurora replay run --candidate opus-high` (exit 2)

```
ERROR: `replay run` needs --candidate C --scenario S
```


## After: output

`aurora replay candidates` (exit 0)

```
total: 2
candidates[2]{name,harness,model,effort,hypothesis}:
  codex-low,codex-cli,gpt-5,low,null
  opus-high,claude-code,claude-opus-5-5,high,more effort fixes more scenarios
help[2]:
  uv run agent_cli.py replay run --candidate codex-low --scenario <id> --budget-usd 2
  uv run agent_cli.py replay new --candidate <name> --harness codex-cli --model <model>
```

`aurora replay run --candidate opus-high --scenario T1-abc --redis-db 0` (exit 2)

```
error: "--redis-db 0 is the live store; a replay never runs there"
code: LIVE_DB_REFUSED
help[1]:
  uv run agent_cli.py replay run --candidate opus-high --scenario T1-abc --redis-db 15
```

`aurora replay run --candidate opus-high` (exit 2)

```
error: `replay run` needs --candidate C --scenario S
code: USAGE
help[2]:
  uv run agent_cli.py replay run --candidate opus-high --scenario <id> --budget-usd 2
  uv run agent_cli.py corpus list --status accepted
```
