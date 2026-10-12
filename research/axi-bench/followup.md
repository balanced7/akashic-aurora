# AXI bench: `followup`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/30 (80%) | 28/30 (93%) | +13 pp |
| Output tokens, as the reader counts them (median) | 89 | 71 | -18 (-20%) |
| Stdout characters (all runs) | 649 | 785 | +136 (+21%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What question id was assigned? | `Q1` | 5/5 | 4/5 |
| Which seat is responsible for answering? | `kimi` | 5/5 | 5/5 |
| What exact command would show the item deferred to that seat? Give the command only. | `['defer kimi --list']` | 0/5 | 5/5 |
| Was a new question added to the file this time? Answer yes or no. | `no` | 4/5 | 5/5 |
| Does the verdict file exist? Answer yes or no. | `no` | 5/5 | 5/5 |
| Was the question filed? Answer yes or no. | `no` | 5/5 | 4/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora followup bench --on docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md --to kimi --ask does the charter still need a quorum?` (exit 0)

```
[followup] Q1 filed in docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md + deferred to kimi (defer 7745dfcfb6) -- their next boot surfaces it; the discharge receipt points at the answered block
```

`aurora followup bench --on docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md --to kimi --ask does the charter still need a quorum?` (exit 0)

```
[followup] Q1 filed in docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md + deferred to kimi (defer 7745dfcfb6) (reused) -- their next boot surfaces it; the discharge receipt points at the answered block
```

`aurora followup bench --on docs/no-such-verdict.md --to kimi --ask x` (exit 2)

```
[followup] no verdict file at 'docs/no-such-verdict.md' -- followup appends to an EXISTING verdict; it never mints one
```

`aurora followup bench --on /etc/hosts --to kimi --ask x` (exit 2)

```
[followup] verdict file must live inside the repo root -- got /etc/hosts
```


## After: output

`aurora followup bench --on docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md --to kimi --ask does the charter still need a quorum?` (exit 0)

```
question: Q1
file: docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md
to: kimi
defer_id: 461f8435e9
status: filed
help[1]:
  uv run agent_cli.py defer kimi --list
```

`aurora followup bench --on docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md --to kimi --ask does the charter still need a quorum?` (exit 0)

```
question: Q1
file: docs/library/report/20260718_charter-framework-draft-deepseek-2026-07_7c6022.md
to: kimi
defer_id: 461f8435e9
status: already open
help[1]:
  uv run agent_cli.py defer kimi --list
```

`aurora followup bench --on docs/no-such-verdict.md --to kimi --ask x` (exit 2)

```
error: no verdict file at 'docs/no-such-verdict.md' -- followup appends to an EXISTING verdict; it never mints one
code: NOT_FOUND
help[1]:
  uv run agent_cli.py followup bench --on <verdict-file> --to <seat> --ask "..."
```

`aurora followup bench --on /etc/hosts --to kimi --ask x` (exit 2)

```
error: verdict file must live inside the repo root -- got /etc/hosts
code: REFUSED
help[1]:
  uv run agent_cli.py followup bench --on <verdict-file> --to <seat> --ask "..."
```
