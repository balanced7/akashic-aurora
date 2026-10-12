# AXI bench: `compare`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 16/30 (53%) | 30/30 (100%) | +47 pp |
| Output tokens, as the reader counts them (median) | 0 | 112 | n/a |
| Stdout characters (all runs) | 397 | 747 | +350 (+88%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What kind of key does the files:tracked domain use? | `path` | 4/5 | 5/5 |
| How many comparable domains are listed? | `7` | 5/5 | 5/5 |
| How many keys are in both sides? | `3` | 5/5 | 5/5 |
| Is this comparison result reliable? Answer yes or no. | `yes` | 1/5 | 5/5 |
| Was the comparison carried out? Answer yes or no. | `no` | 1/5 | 5/5 |
| What kind of key does the verbs:cli domain use? | `verb` | 0/5 | 5/5 |

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

`aurora compare --list` (exit 0)

```
# comparable domains (only like key-types may be diffed)
  files:touched      keys: path
  files:tracked      keys: path
  lessons:all        keys: lesson
  terms:code         keys: term
  terms:lexicon      keys: term
  verbs:cli          keys: verb
  verbs:mcp          keys: verb
```

`aurora compare lessons:all lessons:all` (exit 0)

```
# lessons:all (3) vs lessons:all (3)  keys=lesson

only in lessons:all (0):

only in lessons:all (0):

in both: 3
```

`aurora compare verbs:cli files:tracked` (exit 2)

```

```


## After: output

`aurora compare --list` (exit 0)

```
total: 7
note: only domains with the same key type can be compared
domains[7]{domain,keys}:
  "files:touched",path
  "files:tracked",path
  "lessons:all",lesson
  "terms:code",term
  "terms:lexicon",term
  "verbs:cli",verb
  "verbs:mcp",verb
help[1]:
  uv run agent_cli.py compare files:touched files:tracked
```

`aurora compare lessons:all lessons:all` (exit 0)

```
a: "lessons:all"
b: "lessons:all"
key_type: lesson
reliable: true
counts:
  a: 3
  b: 3
  only_a: 0
  only_b: 0
  both: 3
identical: true
only_a: []
only_b: []
```

`aurora compare verbs:cli files:tracked` (exit 2)

```
error: "refusing to compare 'verbs:cli' (verb) with 'files:tracked' (path) -- different kinds of key, so any difference would be large, confident and meaningless"
code: REFUSED
key_types:
  "verbs:cli": verb
  "files:tracked": path
help[1]:
  uv run agent_cli.py compare --list
```
