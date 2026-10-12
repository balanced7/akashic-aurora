# AXI bench: `lock`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 15/25 (60%) | 24/25 (96%) | +36 pp |
| Output tokens, as the reader counts them (median) | 18 | 58 | +40 (+222%) |
| Stdout characters (all runs) | 197 | 455 | +258 (+131%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did alice get the lock on core/a.py? Answer yes or no. | `yes` | 5/5 | 5/5 |
| What token number does the lock carry? | `2` | 5/5 | 4/5 |
| Was this a brand-new lock, or a refresh of a lock alice already held? Answer new or refreshed. | `refreshed` | 0/5 | 5/5 |
| Which agent holds the lock on docs/x.md? | `bob` | 5/5 | 5/5 |
| What exact command releases this lock when alice is done? Give the command only. | `['unlock', 'alice', 'core/a.py']` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora lock alice core/a.py --ttl 600` (exit 0)

```
[lock] held: core/a.py  (you=alice, token 2)
```

`aurora lock alice core/a.py --ttl 300` (exit 0)

```
[lock] held: core/a.py  (you=alice, token 2)
```

`aurora lock alice docs/x.md` (exit 1)

```
[lock] DENIED: docs/x.md is held by bob (token 1). Edit a file you hold, or request a handoff via the bus.
```


## After: output

`aurora lock alice core/a.py --ttl 600` (exit 0)

```
lock: acquired
path: core/a.py
agent: alice
ttl_s: 600
token: 2
help[1]:
  uv run agent_cli.py unlock alice core/a.py
```

`aurora lock alice core/a.py --ttl 300` (exit 0)

```
lock: refreshed
path: core/a.py
agent: alice
ttl_s: 300
token: 2
help[1]:
  uv run agent_cli.py unlock alice core/a.py
```

`aurora lock alice docs/x.md` (exit 1)

```
error: docs/x.md is held by bob
code: LOCK_HELD
path: docs/x.md
held_by: bob
token: 1
help[2]:
  uv run agent_cli.py locks alice
  uv run agent_cli.py bifrost-send alice "may I take docs/x.md?" --to bob --kind request
```
