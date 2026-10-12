# AXI bench: `story`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/30 (80%) | 30/30 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 171 | 90 | -81 (-47%) |
| Stdout characters (all runs) | 501 | 672 | +171 (+34%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many chapters does the ai-setup track have? | `2` | 5/5 | 5/5 |
| What is the title of the chapter that has exactly one beat? | `Storage sprint` | 4/5 | 5/5 |
| How many beats does the chapter titled 'check port' have? | `4` | 5/5 | 5/5 |
| How many beats carry the memory theme? | `2` | 5/5 | 5/5 |
| How many chapters contain the theme 'nope'? | `0` | 5/5 | 5/5 |
| What exact command would show the full detail of the chapter titled 'Storage sprint'? Give the command only. | `['story', '--chapter', 'chapter_']` | 0/5 | 5/5 |

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

`aurora story` (exit 0)

```
# Story Atlas
Generated: 2026-10-12T14:18:20.289297+00:00
Tracks: ai-setup
  ai-setup: 2 chapter(s)

ai-setup: 2 chapter(s)
```

`aurora story --track ai-setup` (exit 0)

```
# Track: ai-setup (2 chapters)
  [ai-setup] chapter_3a7e1c698a2c: "check port" (4 beats, 2026-10-12T14:18:18.343396+00:00 -> 2026-10-12T14:18:19.768833+00:00)
  [ai-setup] chapter_7493fb83f1f6: "Storage sprint" (1 beats, 2026-10-12T14:18:20.265269+00:00 -> 2026-10-12T14:18:20.265269+00:00)
```

`aurora story --themes` (exit 0)

```
# Themes
  memory: 2 beat(s)
  evaluation: 1 beat(s)
```

`aurora story --theme nope` (exit 1)

```
No chapters contain theme 'nope'
```


## After: output

`aurora story` (exit 0)

```
generated: "2026-10-12T16:19:02 CEST"
chapters: 2
tracks[1]{track,chapters}:
  ai-setup,2
help[2]:
  uv run agent_cli.py story --track ai-setup
  uv run agent_cli.py story --themes
```

`aurora story --track ai-setup` (exit 0)

```
track: ai-setup
total: 2
chapters[2]{id,title,beats,start,end}:
  chapter_cd63e6227b84,check port,4,"2026-10-12T16:19:00 CEST","2026-10-12T16:19:01 CEST"
  chapter_16055ed858df,Storage sprint,1,"2026-10-12T16:19:02 CEST","2026-10-12T16:19:02 CEST"
help[1]:
  uv run agent_cli.py story --chapter <id>
```

`aurora story --themes` (exit 0)

```
total: 2
themes[2]{theme,beats}:
  memory,2
  evaluation,1
help[1]:
  uv run agent_cli.py story --theme memory
```

`aurora story --theme nope` (exit 0)

```
theme: nope
total: 0
chapters: []
help[1]:
  uv run agent_cli.py story --themes
```
