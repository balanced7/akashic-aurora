# AXI bench: `find`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 1,738 | 204 | -1,534 (-88%) |
| Stdout characters (all runs) | 621 | 946 | +325 (+52%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What is the full path of the match? | `/usr/local/bin/starship` | 5/5 | 5/5 |
| Was this answered by the Everything index or by a directory walk? Answer index or walk. | `walk` | 5/5 | 5/5 |
| How many matches were found? | `0` | 5/5 | 5/5 |
| Could more matches exist than the ones listed? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Is 'biggest' one of the allowed presets? Answer yes or no. | `yes` | 5/5 | 5/5 |

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

`aurora find starship` (exit 0)

```
1 match(es) for 'starship'  [engine: walk, walked 1030 dir(s) under 3 root(s) in 0.06s]:
/usr/local/bin/starship
```

`aurora find zz_no_such_file_qq` (exit 0)

```
(no matches for 'zz_no_such_file_qq' -- the walk COMPLETED: walked 1030 dir(s) under 3 root(s) in 0.06s. Not present under those roots.)
```

`aurora find rocm --limit 3` (exit 0)

```
3 match(es) for 'rocm'  [engine: walk, walked 54 dir(s) under 2 root(s) in 0.0s]  [BOUNDED -- more may exist beyond the budget]:
/opt/rocm-7.2.4/.info/version-rocm
/opt/rocm-7.2.4/.info/version-rocm-hip
/opt/rocm-7.2.4/.info/version-rocm-developer-tools
```

`aurora find starship --preset nope` (exit 2)

```
ERROR: unknown preset 'nope' -- allowed: biggest, files, folders, newest, oldest, recent, recently-changed, smallest
```


## After: output

`aurora find starship` (exit 0)

```
query: starship
engine: walk
searched: 1030 dirs under 3 roots in 0.05s
complete: true
total: 1
matches[1]{path,exact}:
  /usr/local/bin/starship,true
```

`aurora find zz_no_such_file_qq` (exit 0)

```
query: zz_no_such_file_qq
engine: walk
searched: 1030 dirs under 3 roots in 0.06s
complete: true
total: 0
matches: []
help[1]:
  uv run agent_cli.py find zz_no_such_file_qq --path
```

`aurora find rocm --limit 3` (exit 0)

```
query: rocm
engine: walk
searched: 54 dirs under 2 roots in 0.0s
complete: false
note: "the search stopped early (--limit or its time budget): more may exist, and a miss is not evidence of absence"
total: 3
matches[3]{path,exact}:
  /opt/rocm-7.2.4/.info/version-rocm,false
  /opt/rocm-7.2.4/.info/version-rocm-hip,false
  /opt/rocm-7.2.4/.info/version-rocm-developer-tools,false
help[1]:
  uv run agent_cli.py find rocm --limit 12
```

`aurora find starship --preset nope` (exit 2)

```
error: unknown preset 'nope'
code: USAGE
allowed[8]: biggest,files,folders,newest,oldest,recent,recently-changed,smallest
help[1]:
  uv run agent_cli.py find starship --preset recent
```
