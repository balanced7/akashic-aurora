# AXI bench: `seat-identity`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 19/30 (63%) | 30/30 (100%) | +37 pp |
| Output tokens, as the reader counts them (median) | 17 | 17 | +0 (+0%) |
| Stdout characters (all runs) | 406 | 563 | +157 (+39%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which seat id does this session resolve to? | `alice` | 0/5 | 5/5 |
| Where did the identity come from? Answer binding, env or unknown. | `binding` | 5/5 | 5/5 |
| Is this identity bound to this session specifically? Answer yes or no. | `no` | 4/5 | 5/5 |
| What exact command binds this session to its seat id? Give the command only. | `['seat-identity', 'bench', '--session bench-sess-0002']` | 0/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Was a binding removed? Answer yes or no. | `yes` | 5/5 | 5/5 |

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

`aurora seat-identity --session bench-sess-0001` (exit 0)

```
  seat: alice#bench-se   (resolved from: binding)
```

`aurora seat-identity --session bench-sess-0002` (exit 0)

```
  seat: bench#bench-se   (resolved from: env)
  NOTE: from the shared process env, not a per-session binding. If another seat runs in this process profile it resolves identically. Declare to make it yours.
```

`aurora seat-identity` (exit 1)

```
[seat-identity] no session id -- pass --session <uuid> (CLAUDE_CODE_SESSION_ID is unset in this process)
```

`aurora seat-identity --session bench-sess-0001 --clear` (exit 0)

```
[seat-identity] binding cleared for bench-se
```


## After: output

`aurora seat-identity --session bench-sess-0001` (exit 0)

```
seat: alice
session: bench-se
resolved_from: binding
```

`aurora seat-identity --session bench-sess-0002` (exit 0)

```
seat: bench
session: bench-se
resolved_from: env
binding: none
note: "not bound to this session: read from the shared process env, where another seat in this process profile resolves the same; the help command binds it to this session"
help[1]:
  uv run agent_cli.py seat-identity bench --session bench-sess-0002
```

`aurora seat-identity` (exit 1)

```
error: "no session id: CLAUDE_CODE_SESSION_ID is unset in this process"
code: NO_SESSION
help[1]:
  uv run agent_cli.py seat-identity <agent_id> --session <uuid>
```

`aurora seat-identity --session bench-sess-0001 --clear` (exit 0)

```
binding: cleared
session: bench-se
```
