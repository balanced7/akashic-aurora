# AXI bench: `compress`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/20 (100%) | 20/20 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 811 | 640 | -171 (-21%) |
| Stdout characters (all runs) | 3,281 | 1,669 | -1,612 (-49%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many switchable harness pieces are there in total? | `20` | 5/5 | 5/5 |
| How many of the pieces are skills? | `5` | 5/5 | 5/5 |
| How many replay runs were read? | `0` | 5/5 | 5/5 |
| Which flag is missing from this compress run command? Give the flag only. | `--max-runs` | 5/5 | 5/5 |

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

`aurora compress pieces` (exit 0)

```
  section:AGENTS.md#at-the-start-of-your-task-run-this-and-r group=AGENTS.md#at-the-start-of-your-task-run-this-and-r
  section:AGENTS.md#when-you-learn-something-worth-keeping-r group=AGENTS.md#when-you-learn-something-worth-keeping-r
  section:AGENTS.md#to-search-memory-mid-task              group=AGENTS.md#to-search-memory-mid-task
  section:AGENTS.md#before-you-edit-a-file-or-run-a-command- group=AGENTS.md#before-you-edit-a-file-or-run-a-command-
  section:AGENTS.md#who-does-what-no-fixed-split           group=AGENTS.md#who-does-what-no-fixed-split
  section:AGENTS.md#bifrost-live-agent-mail-durable-salient- group=AGENTS.md#bifrost-live-agent-mail-durable-salient-
  section:AGENTS.md#session-hygiene-don-t-burn-tokens-on-his group=AGENTS.md#session-hygiene-don-t-burn-tokens-on-his
  section:AGENTS.md#reporting-your-work-communication-contra group=AGENTS.md#reporting-your-work-communication-contra
  section:AGENTS.md#trial-mode-sandbox-recommended-for-your- group=AGENTS.md#trial-mode-sandbox-recommended-for-your-
  section:AGENTS.md#details-optional                       group=AGENTS.md#details-optional
  section:AGENTS.md#if-a-command-errors                    group=AGENTS.md#if-a-command-errors
  section:AGENTS.md#which-command-for-what-when-more-than-on group=AGENTS.md#which-command-for-what-when-more-than-on
  skill:akashic-memory                                     group=skills
  skill:plan-with-the-corpus                               group=skills
  skill:root-cause-before-fixes                            group=skills
  skill:shader-craft                                       group=skills
  skill:verified-done                                      group=skills
  hook:PostToolUse:claude_posttooluse.py                   group=hooks:PostToolUse
  hook:PreToolUse:claude_trace.py                          group=hooks:PreToolUse
  hook:Stop:claude_stop.py                                 group=hooks:Stop
```

`aurora compress telemetry --candidate baseline --scenario T1-abc` (exit 0)

```
  section:AGENTS.md#at-the-start-of-your-task-run-this-and-r 0
  section:AGENTS.md#when-you-learn-something-worth-keeping-r 0
  section:AGENTS.md#to-search-memory-mid-task              0
  section:AGENTS.md#before-you-edit-a-file-or-run-a-command- 0
  section:AGENTS.md#who-does-what-no-fixed-split           0
  section:AGENTS.md#bifrost-live-agent-mail-durable-salient- 0
  section:AGENTS.md#session-hygiene-don-t-burn-tokens-on-his 0
  section:AGENTS.md#reporting-your-work-communication-contra 0
  section:AGENTS.md#trial-mode-sandbox-recommended-for-your- 0
  section:AGENTS.md#details-optional                       0
  section:AGENTS.md#if-a-command-errors                    0
  section:AGENTS.md#which-command-for-what-when-more-than-on 0
  skill:akashic-memory                                     0
  skill:plan-with-the-corpus                               0
  skill:root-cause-before-fixes                            0
  skill:shader-craft                                       0
  skill:verified-done                                      0
  hook:PostToolUse:claude_posttooluse.py                   0
  hook:PreToolUse:claude_trace.py                          0
  hook:Stop:claude_stop.py                                 0
(0 runs read)
```

`aurora compress run --candidate baseline --scenario T1-abc` (exit 2)

```
ERROR: `compress run` needs --candidate, --scenario ... and --max-runs (real runs cost money)
```


## After: output

`aurora compress pieces` (exit 0)

```
root: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a7f65ec701d4c3c3d
total: 20
by_kind:
  section: 12
  skill: 5
  hook: 3
pieces[20]{id,kind}:
  "section:AGENTS.md#at-the-start-of-your-task-run-this-and-r",section
  "section:AGENTS.md#when-you-learn-something-worth-keeping-r",section
  "section:AGENTS.md#to-search-memory-mid-task",section
  "section:AGENTS.md#before-you-edit-a-file-or-run-a-command-",section
  "section:AGENTS.md#who-does-what-no-fixed-split",section
  "section:AGENTS.md#bifrost-live-agent-mail-durable-salient-",section
  "section:AGENTS.md#session-hygiene-don-t-burn-tokens-on-his",section
  "section:AGENTS.md#reporting-your-work-communication-contra",section
  "section:AGENTS.md#trial-mode-sandbox-recommended-for-your-",section
  "section:AGENTS.md#details-optional",section
  "section:AGENTS.md#if-a-command-errors",section
  "section:AGENTS.md#which-command-for-what-when-more-than-on",section
  "skill:akashic-memory",skill
  "skill:plan-with-the-corpus",skill
  "skill:root-cause-before-fixes",skill
  "skill:shader-craft",skill
  "skill:verified-done",skill
  "hook:PostToolUse:claude_posttooluse.py",hook
  "hook:PreToolUse:claude_trace.py",hook
  "hook:Stop:claude_stop.py",hook
help[1]:
  uv run agent_cli.py compress telemetry --candidate baseline --scenario <id>
```

`aurora compress telemetry --candidate baseline --scenario T1-abc` (exit 0)

```
candidate: baseline
runs_read: 0
pieces: 20
help[1]:
  uv run agent_cli.py replay run --candidate baseline --scenario T1-abc --budget-usd 2
```

`aurora compress run --candidate baseline --scenario T1-abc` (exit 2)

```
error: "`compress run` needs --candidate, --scenario ... and --max-runs (real runs cost money)"
code: USAGE
help[1]:
  uv run agent_cli.py compress run --candidate baseline --scenario <id> --max-runs 20
```
