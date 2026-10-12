# AXI bench: `watch`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 25 | 85 | +60 (+240%) |
| Stdout characters (all runs) | 755 | 1,218 | +463 (+61%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is any run expectation open? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many minutes of silence are allowed before it alarms? | `10` | 5/5 | 5/5 |
| What exact command tells the watcher the run is still alive? Give the command only. | `['watch bench --checkpoint']` | 0/5 | 5/5 |
| Which run is declared? | `['nightly reindex']` | 5/5 | 5/5 |
| Is the watcher expecting activity right now? Answer yes or no. | `no` | 5/5 | 5/5 |
| Would the watcher alarm right now? Answer yes or no. | `yes` | 5/5 | 5/5 |

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

`aurora watch bench --status` (exit 0)

```
[watch] no expectation on disk -- the deadman is armed and correctly silent
```

`aurora watch bench --declare nightly reindex --grace 600` (exit 0)

```
[watch] expectation OPEN for bench: 'nightly reindex' -- silence past 10 min is now a finding (/tmp/axi-bench-_mr450sm/before/state/expect/run-active.json)
```

`aurora watch bench --status` (exit 0)

```
[watch] open: 'nightly reindex' by bench -- quiet 0s of 600s grace
```

`aurora watch bench --stand-down` (exit 0)

```
[watch] stood down -- silence is correct again
```

`aurora watch bench --status` (exit 0)

```
[watch] stood down (last: 'nightly reindex') -- silent
```

`aurora watch bench --declare schema migration --grace 0` (exit 0)

```
[watch] expectation OPEN for bench: 'schema migration' -- silence past 0 min is now a finding (/tmp/axi-bench-_mr450sm/before/state/expect/run-active.json)
```

`aurora watch bench --status` (exit 0)

```
[watch] WOULD ALARM: FAILSAFE: bench declared a run active (schema migration) and has not checkpointed for 0 min, past its 0 min grace. The seat may be down, 529'd, or stalled -- nothing has moved.
```


## After: output

`aurora watch bench --status` (exit 0)

```
expectation: none
run_declared: no
alarm: no
file: state/expect/run-active.json
help[1]:
  uv run agent_cli.py watch bench --declare "<what is running>"
```

`aurora watch bench --declare nightly reindex --grace 600` (exit 0)

```
expectation: open
run: nightly reindex
by: bench
grace_s: 600
file: state/expect/run-active.json
help[2]:
  uv run agent_cli.py watch bench --checkpoint
  uv run agent_cli.py watch bench --stand-down
```

`aurora watch bench --status` (exit 0)

```
expectation: open
alarm: no
run: nightly reindex
by: bench
quiet_s: 0
grace_s: 600
help[2]:
  uv run agent_cli.py watch bench --checkpoint
  uv run agent_cli.py watch bench --stand-down
```

`aurora watch bench --stand-down` (exit 0)

```
expectation: stood down
run: nightly reindex
```

`aurora watch bench --status` (exit 0)

```
expectation: stood down
alarm: no
last_run: nightly reindex
```

`aurora watch bench --declare schema migration --grace 0` (exit 0)

```
expectation: open
run: schema migration
by: bench
grace_s: 0
file: state/expect/run-active.json
help[2]:
  uv run agent_cli.py watch bench --checkpoint
  uv run agent_cli.py watch bench --stand-down
```

`aurora watch bench --status` (exit 0)

```
expectation: alarm
alarm: yes
run: schema migration
by: bench
quiet_s: 0
grace_s: 0
finding: "FAILSAFE: bench declared a run active (schema migration) and has not checkpointed for 0 min, past its 0 min grace. The seat may be down, 529'd, or stalled -- nothing has moved."
help[2]:
  uv run agent_cli.py watch bench --checkpoint
  uv run agent_cli.py watch bench --stand-down
```
