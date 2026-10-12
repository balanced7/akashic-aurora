# AXI bench: `sha`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 28/30 (93%) | 29/30 (97%) | +3 pp |
| Output tokens, as the reader counts them (median) | 120 | 152 | +32 (+27%) |
| Stdout characters (all runs) | 633 | 788 | +155 (+24%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many rewrite maps does this checkout carry? | `5` | 5/5 | 5/5 |
| How many remaps does the 2026-08-12 map hold? | `1979` | 5/5 | 5/5 |
| Which commit does 00cf320d finally resolve to? Give its SHA. | `['fdccf166e157']` | 5/5 | 5/5 |
| How many of the cited SHAs could not be resolved? | `1` | 5/5 | 5/5 |
| Why could deadbeef1 not be resolved? Answer in a few words. | `['no map']` | 3/5 | 5/5 |
| Is zzzz a valid commit SHA? Answer yes or no. | `no` | 5/5 | 4/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora sha --maps` (exit 0)

```
  2026-07-23                         1,125 remaps  1 dropped  [recorded]
  2026-08-12                         1,979 remaps  0 dropped  [recorded]
  2026-09-26-authorship              4,748 remaps  0 dropped  [recorded]
  2026-09-26-cited-gap                   1 remaps  0 dropped  [reconstructed]
  2026-09-26-unmapped-residue          116 remaps  0 dropped  [reconstructed]
```

`aurora sha 00cf320d 01051640 deadbeef1 --no-remote` (exit 1)

```
  00cf320d  TRANSLATED  3bc123e32bb3 [2026-07-23] -> fdccf166e157 [2026-08-12]
  01051640  TRANSLATED  9cfd2516d7f1 [2026-07-23] -> 93622be228e0 [2026-08-12]
  deadbeef1  UNKNOWN  no map covers it
```

`aurora sha zzzz --no-remote` (exit 1)

```
  zzzz  UNKNOWN  not a commit SHA (need 7-40 hex characters)
```


## After: output

`aurora sha --maps` (exit 0)

```
total: 5
maps[5]{label,remaps,dropped,method,durable}:
  2026-07-23,1125,1,recorded,yes
  2026-08-12,1979,0,recorded,yes
  2026-09-26-authorship,4748,0,recorded,yes
  2026-09-26-cited-gap,1,0,reconstructed,yes
  2026-09-26-unmapped-residue,116,0,reconstructed,yes
help[1]:
  uv run agent_cli.py sha <commit-sha>
```

`aurora sha 00cf320d 01051640 deadbeef1 --no-remote` (exit 1)

```
total: 3
resolved: 2
unresolved: 1
shas[3]{cited,status,now,maps,note}:
  00cf320d,translated,fdccf166e157,2026-07-23 -> 2026-08-12,null
  "01051640",translated,93622be228e0,2026-07-23 -> 2026-08-12,null
  deadbeef1,unknown,null,null,no map covers it
help[1]:
  uv run agent_cli.py sha --maps
```

`aurora sha zzzz --no-remote` (exit 1)

```
total: 1
resolved: 0
unresolved: 1
shas[1]{cited,status,now,maps,note}:
  zzzz,unknown,null,null,not a commit SHA (need 7-40 hex characters)
help[1]:
  uv run agent_cli.py sha --maps
```
