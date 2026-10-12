# AXI bench: `fence`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 29/30 (97%) | -3 pp |
| Output tokens, as the reader counts them (median) | 104 | 133 | +29 (+28%) |
| Stdout characters (all runs) | 700 | 984 | +284 (+41%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many fences exist? | `3` | 5/5 | 5/5 |
| Which fence is closed? Give its id. | `t070-closed` | 5/5 | 5/5 |
| Which slots of fence t054-design are sealed? List them separated by commas. | `['brief', 'half_a']` | 5/5 | 5/5 |
| Who wrote the half_b slot? | `deepseek` | 5/5 | 4/5 |
| How many citations did the PV pass find missing? | `1` | 5/5 | 5/5 |
| How many M1-BRIEF sections are missing from the brief that could not be sealed? | `3` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora fence list` (exit 0)

```
  [open] t054-design (full) -- Should routing move into the bus?  sealed: brief,half_a
  [open] t060-lite (lite) -- Is the wake seat per session?  sealed: -
  [CLOSED] t070-closed (full) -- Retire the HMAC bridge?  sealed: brief,half_a,half_b,reconciliation
```

`aurora fence status t054-design` (exit 0)

```
# fence t054-design (full) -- Should routing move into the bus?
  brief            SEALED by claude
  half_a           SEALED by kimi
  half_b           written by deepseek
  reconciliation   empty
  pv: 1 missing @ 2026-10-12T15:44:05.453400+00:00
  closed: False
```

`aurora fence seal t060-lite --slot brief --by sol` (exit 1)

```
REFUSED: t060-lite/brief cannot seal:
  - M1-BRIEF section missing: RULES OF ENGAGEMENT
  - M1-BRIEF section missing: THE QUESTION
  - M1-BRIEF section missing: OUTPUT CONTRACT
```


## After: output

`aurora fence list` (exit 0)

```
total: 3
open: 2
closed: 1
fences[3]{id,status,tier,sealed,question}:
  t054-design,open,full,brief half_a,Should routing move into the bus?
  t060-lite,open,lite,"-",Is the wake seat per session?
  t070-closed,closed,full,brief half_a half_b reconciliation,Retire the HMAC bridge?
help[2]:
  uv run agent_cli.py fence status <fence_id>
  uv run agent_cli.py fence open <fence_id> --question "..."
```

`aurora fence status t054-design` (exit 0)

```
fence: t054-design
tier: full
question: Should routing move into the bus?
closed: false
slots[4]{slot,state,by}:
  brief,sealed,claude
  half_a,sealed,kimi
  half_b,written,deepseek
  reconciliation,empty,null
pv_missing_citations: 1
help[1]:
  uv run agent_cli.py fence seal t054-design --slot half_b
```

`aurora fence seal t060-lite --slot brief --by sol` (exit 1)

```
error: t060-lite/brief cannot seal
code: REFUSED
problems[3]: "M1-BRIEF section missing: RULES OF ENGAGEMENT","M1-BRIEF section missing: THE QUESTION","M1-BRIEF section missing: OUTPUT CONTRACT"
help[1]:
  uv run agent_cli.py fence write t060-lite --slot brief --file <path> --by sol
```
