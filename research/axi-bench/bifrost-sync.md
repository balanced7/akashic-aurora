# AXI bench: `bifrost-sync`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 29/35 (83%) | 35/35 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 807 | 305 | -502 (-62%) |
| Stdout characters (all runs) | 4,908 | 1,639 | -3,269 (-67%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many unread messages does bench have? | `4` | 5/5 | 5/5 |
| Which agent sent the request message? | `alice` | 5/5 | 5/5 |
| How many of the unread messages are asks that need a reply (requests or questions)? | `2` | 5/5 | 5/5 |
| What exact command marks bench's unread messages as read (acknowledges them)? Give the command only. | `['bifrost-sync', 'bench', '--consume']` | 0/5 | 5/5 |
| What exact command shows the full body of dave's message? Give the command only. | `['bifrost-fetch', '--get']` | 5/5 | 5/5 |
| How many messages were consumed? | `4` | 5/5 | 5/5 |
| How many unread messages does nobody have? | `0` | 4/5 | 5/5 |

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

`aurora bifrost-sync bench` (exit 0)

```
# bifrost-sync for bench

## UNREAD BIFROST (live bus)
  4 unread (work-lane, peek -- use bifrost_inbox or `uv run agent_cli.py bifrost-sync --consume` to ack): [2 asks / 2 fyi]
  [request] from alice: please review core/a.py before merge
  [chat] from bob: FYI the build is green
  [question] from carol: what port does redis use?
  [chat] from dave: Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path ...[truncated]  [full body: bifrost-fetch --get 1791814916975-0]
```

`aurora bifrost-sync bench --consume` (exit 0)

```
# consumed 4 message(s) for bench
  [request] from alice: please review core/a.py before merge
  [chat] from bob: FYI the build is green
  [question] from carol: what port does redis use?
  [chat] from dave: Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path ...[truncated]  [full body: bifrost-fetch --get 1791814916973-0]
  (4 seen receipt(s) recorded -- declare intent with `mailbox bench --intent <sha> --as act|decline|defer|delegate`)
```

`aurora bifrost-sync nobody` (exit 0)

```
# bifrost-sync for nobody

## UNREAD BIFROST (live bus)
  (no new messages -- peek only; cursor unchanged)
```


## After: output

`aurora bifrost-sync bench` (exit 0)

```
agent: bench
bus: online
unread: 4
scope: work lane
asks: 2
fyi: 2
messages[4]{id,kind,from,text}:
  1791814962028-0,request,alice,please review core/a.py before merge
  1791814962571-0,chat,bob,FYI the build is green
  1791814963070-0,question,carol,what port does redis use?
  1791814963559-0,chat,dave,"Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer... (truncated, 2679 chars total)"
help[2]:
  uv run agent_cli.py bifrost-sync bench --consume
  uv run agent_cli.py bifrost-fetch --get 1791814963559-0
```

`aurora bifrost-sync bench --consume` (exit 0)

```
agent: bench
consumed: 4
asks: 2
fyi: 2
messages[4]{id,kind,from,text}:
  1791814962025-0,request,alice,please review core/a.py before merge
  1791814962567-0,chat,bob,FYI the build is green
  1791814963069-0,question,carol,what port does redis use?
  1791814963558-0,chat,dave,"Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer: keep the write path synchronous. Design notes for the cache layer... (truncated, 2679 chars total)"
seen_receipts: 4
help[2]:
  uv run agent_cli.py bifrost-fetch --get 1791814963558-0
  uv run agent_cli.py mailbox bench --intent <sha> --as act|decline|defer|delegate
```

`aurora bifrost-sync nobody` (exit 0)

```
agent: nobody
bus: online
unread: 0
messages: []
help[1]:
  uv run agent_cli.py promoted --limit 5
```
