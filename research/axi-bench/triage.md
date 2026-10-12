# AXI bench: `triage`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 412 | 270 | -142 (-34%) |
| Stdout characters (all runs) | 871 | 549 | -322 (-37%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are in the corpus? | `3` | 0/5 | 5/5 |
| Which lesson is in the protected core? | `learn:experiment:proven_core` | 5/5 | 5/5 |
| How many useful votes does proven_core have? | `2` | 5/5 | 5/5 |
| Which lesson was voted noise? Give its name. | `off_target` | 5/5 | 5/5 |
| How many ghost counters are there? | `1` | 5/5 | 5/5 |
| Does this report prune anything by itself? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora triage` (exit 0)

```
# TRIAGE (S1)  corpus=3 tracked=3 (lessons=2, ghosts=1) dormant=1 | window push cost ~0 tokens

## PROTECT (1) -- earned credit; the proven core
  helped=0 useful=2 surfaced=0    learn:experiment:proven_core

## COST WITHOUT RETURN (0) -- surfaced >= 5, zero credit; adjudicate: merge / graduate / retire / sharpen trigger

## NOISE-VOTED (1)
  noise=1 surfaced=0    learn:experiment:off_target

## WATCH: 0 lesson(s) surfaced but too early to judge (< 5 impressions)

## GHOSTS (1) -- counters naming NO live lesson (retired/renamed); bookkeeping debt, not knowledge
  surfaced=0    u=1 h=0 n=0  learn:experiment:renamed_away  <-- has credit: adjudicate (fold into successor)
  -> 0 zero-credit (safe auto-fold), 1 credited (needs a decision). Apply: uv run agent_cli.py recall-counters --fold

(adjudication is human/frontier judgment -- this report never auto-prunes)
```


## After: output

`aurora triage` (exit 0)

```
authority: review only -- adjudication is human judgment; this report never prunes
corpus: 3
tracked_lessons: 2
dormant: 1
window_push_tokens: 0
min_surfaced: 5
counts:
  protect: 1
  cost_no_return: 0
  noise_voted: 1
  watch: 0
  ghosts: 1
  credited_ghosts: 1
protect[1]{source,helped,useful,surfaced}:
  "learn:experiment:proven_core",0,2,0
noise_voted[1]{source,noise,surfaced}:
  "learn:experiment:off_target",1,0
ghosts[1]{source,surfaced,credit}:
  "learn:experiment:renamed_away",0,yes
help[1]:
  uv run agent_cli.py recall-counters --fold
```
