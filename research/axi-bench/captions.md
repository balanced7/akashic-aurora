# AXI bench: `captions`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 14/15 (93%) | 14/15 (93%) | +0 pp |
| Output tokens, as the reader counts them (median) | 89 | 104 | +15 (+17%) |
| Stdout characters (all runs) | 248 | 221 | -27 (-11%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Were any caption files written? Answer yes or no. | `no` | 4/5 | 4/5 |
| Which tool is missing? Give its name only. | `yt-dlp` | 5/5 | 5/5 |
| What exact command installs the missing tool? Give the command only. | `['install', 'yt-dlp']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora captions https://www.youtube.com/watch?v=aaaaaaaaaaa` (exit 2)

```
yt-dlp is not importable from this interpreter. Install it into the fleet python:
    py -3.11 -m pip install yt-dlp
(then retry; the verb calls `<this python> -m yt_dlp`, so the install must land in the same interpreter family the CLI runs under)
```


## After: output

`aurora captions https://www.youtube.com/watch?v=aaaaaaaaaaa` (exit 2)

```
error: yt-dlp is not importable from this interpreter
code: YTDLP_MISSING
help[1]:
  uv pip install --python /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a36921c04653397c1/.venv/bin/python yt-dlp
```
