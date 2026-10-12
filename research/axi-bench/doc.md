# AXI bench: `doc`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/30 (80%) | 30/30 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 28 | 81 | +53 (+189%) |
| Stdout characters (all runs) | 554 | 814 | +260 (+47%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which subcommands does the doc command offer? List them separated by commas. | `['new', 'adopt', 'arc']` | 0/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which atom types does doc new accept? List them separated by commas. | `['contract', 'map', 'design', 'brief', 'report', 'chronicle', 'ledger', 'ruling']` | 4/5 | 5/5 |
| Which type did the command reject? Give the type only. | `bogus` | 5/5 | 5/5 |
| Which atom id could not be found? Give the id only. | `art_20990101_nope_000000` | 5/5 | 5/5 |
| Did the adopt succeed? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora doc` (exit 1)

```

```

`aurora doc new --title probe-x` (exit 2)

```
[doc] REFUSED: --type and --title are required (--from-bus infers type from the message kind)
  atom types: contract map design brief report chronicle ledger ruling
  example: uv run agent_cli.py doc new --type report --title fence-x --seats claude --body-file x.md
```

`aurora doc new --type bogus --title probe-x --body y` (exit 2)

```
[doc] REFUSED: type 'bogus' not in DOC_TYPES ('contract', 'map', 'design', 'brief', 'report', 'chronicle', 'ledger', 'ruling') -- machine/file kinds stay files
```

`aurora doc arc art_20990101_nope_000000 newlabel` (exit 2)

```
[doc] REFUSED: cannot relabel unknown atom art_20990101_nope_000000
```

`aurora doc adopt /nonexistent/axi-bench-nope.md` (exit 2)

```
[doc] REFUSED: no such file: /nonexistent/axi-bench-nope.md
```


## After: output

`aurora doc` (exit 2)

```
error: "doc needs a subcommand: new, adopt or arc"
code: USAGE
help[2]:
  uv run agent_cli.py doc new --type report --title <slug> --seats <you> --body-file <file.md>
  uv run agent_cli.py doc --help
```

`aurora doc new --title probe-x` (exit 2)

```
error: "--type and --title are required (--from-bus infers type from the message kind)"
code: USAGE
atom_types[8]: contract,map,design,brief,report,chronicle,ledger,ruling
help[1]:
  uv run agent_cli.py doc new --type report --title fence-x --seats claude --body-file x.md
```

`aurora doc new --type bogus --title probe-x --body y` (exit 2)

```
error: "refused: type 'bogus' not in DOC_TYPES ('contract', 'map', 'design', 'brief', 'report', 'chronicle', 'ledger', 'ruling') -- machine/file kinds stay files"
code: REFUSED
```

`aurora doc arc art_20990101_nope_000000 newlabel` (exit 2)

```
error: "refused: cannot relabel unknown atom art_20990101_nope_000000"
code: REFUSED
```

`aurora doc adopt /nonexistent/axi-bench-nope.md` (exit 2)

```
error: "refused: no such file: /nonexistent/axi-bench-nope.md"
code: NOT_FOUND
```
