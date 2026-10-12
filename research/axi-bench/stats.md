# AXI bench: `stats`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 302 | 320 | +18 (+6%) |
| Stdout characters (all runs) | 969 | 889 | -80 (-8%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are in the corpus? | `3` | 5/5 | 5/5 |
| How many repeats (a lesson violated again) are recorded? | `1` | 5/5 | 5/5 |
| Which lesson was violated again? Give its name only. | `git_blanket_staging` | 5/5 | 5/5 |
| What is the full command to run the pack replay? Give the command only. | `['-m core.recall.pack_replay']` | 5/5 | 5/5 |
| Over how many hours is this silence window measured? | `24` | 5/5 | 5/5 |

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

`aurora stats` (exit 0)

```
RECALL-VALUE FUNNEL  (all-time counters + a recent window)
  corpus: 3 lesson(s), 0 tracked by recall
  surfaced impressions: 0 | votes: useful=0 noise=0
  helped credits (flips that credited a surfaced lesson): 0
  lessons with a track record (helped or useful > 0): 0
  REPEATS (lesson existed, mistake happened anyway): 1  -- a FLOOR: only what someone noticed, never a rate
    1x  git_blanket_staging
    by what recall did: {'unrecorded': 1}  (fired = reading failure; suppressed = targeting failure)
  last 24h: flips=0 (credited=0, corpus-gap=0) | lessons recorded=3 | lessons-per-flip=None
  push cost last 24h: 3 injection(s), ~495 tokens -- `injections` for the ledger
```

`aurora stats --silence` (exit 0)

```
# RECALL SILENCE (R2 denominator, last 24h)
  calls 811 | fired 5 | silent 806 (99% -- census floor: >=27% once the gate lands)
    floor_silent       794
    excluded_silent    10
    empty_query        2
  pack replay (frozen-30 vs the reconciled bar): uv run -m core.recall.pack_replay
```


## After: output

`aurora stats` (exit 0)

```
corpus_lessons: 3
tracked_by_recall: 0
surfaced_impressions: 0
votes_useful: 0
votes_noise: 0
helped_credits: 0
lessons_with_track_record: 0
repeats: 1
repeats_are: "lesson existed, mistake happened anyway -- a FLOOR, never a rate"
most_violated[1]{lesson,times}:
  git_blanket_staging,1
repeats_by_recall_outcome:
  unrecorded: 1
recall_outcome_means: fired = reading failure; suppressed = targeting failure
window:
  hours: 24
  flips: 0
  flips_credited: 0
  flips_corpus_gap: 0
  lessons_recorded: 3
  lessons_per_flip: null
push_cost:
  injections: 3
  tokens_approx: 495
help[2]:
  uv run agent_cli.py injections
  uv run agent_cli.py stats --days 7
```

`aurora stats --silence` (exit 0)

```
window_hours: 24
calls: 819
fired: 5
silent: 814
silent_pct: 99
census_floor: >=27% silent once the gate lands
by_reason:
  floor_silent: 802
  excluded_silent: 10
  empty_query: 2
help[1]:
  uv run python -m core.recall.pack_replay
```
