# AXI bench: `packet-stats`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 23/25 (92%) | +12 pp |
| Output tokens, as the reader counts them (median) | 165 | 125 | -40 (-24%) |
| Stdout characters (all runs) | 471 | 241 | -230 (-49%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many routing decisions were recorded for chat packets? | `3` | 5/5 | 5/5 |
| How many routing decisions were recorded in total, across all kinds? | `5` | 5/5 | 5/5 |
| How many handoff packets were mirrored successfully? | `1` | 5/5 | 4/5 |
| How many mirror failures were recorded? Answer with a number. | `0` | 2/5 | 4/5 |
| Does the stored policy match the current policy? Answer yes or no. | `yes` | 3/5 | 5/5 |

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

`aurora packet-stats` (exit 0)

```
# PACKET ROUTE STATS -- shadow / online
  policy: kind-lane:8b1a0308b554
  stored policy: kind-lane:8b1a0308b554 (match)
  started: 2026-10-12T15:59:14.700956+00:00
  bounded fields: 6/148
  decision:chat                              3
  decision:handoff                           1
  decision:request                           1
  mirror:chat:success                        3
  mirror:handoff:success                     1
  mirror:request:success                     1
```


## After: output

`aurora packet-stats` (exit 0)

```
mode: shadow
policy: "kind-lane:8b1a0308b554"
policy_matches: true
started: "2026-10-12T15:59:47.979732+00:00"
fields_used: 6
field_limit: 148
decisions: 5
failures: 0
kinds[3]{kind,decisions,success}:
  chat,3,3
  handoff,1,1
  request,1,1
```
