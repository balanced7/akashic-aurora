# AXI bench: `packet-trace`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 70 | 53 | -17 (-24%) |
| Stdout characters (all runs) | 499 | 390 | -109 (-22%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which lane does a handoff packet route to? | `work` | 5/5 | 5/5 |
| Which lane does a narration packet route to? | `trace` | 5/5 | 5/5 |
| Which rule decided the route? | `kind:handoff` | 5/5 | 5/5 |
| Does the router have a lane mapped for bogus_kind? Answer yes or no. | `no` | 5/5 | 5/5 |
| Does this route decision change how messages are delivered today? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora packet-trace handoff` (exit 0)

```
# PACKET ROUTE -- handoff
  lane: work
  rule: kind:handoff
  mode: shadow (observation only; no delivery behavior changes)
  policy: kind-lane:8b1a0308b554
```

`aurora packet-trace narration` (exit 0)

```
# PACKET ROUTE -- narration
  lane: trace
  rule: kind:narration
  mode: shadow (observation only; no delivery behavior changes)
  policy: kind-lane:8b1a0308b554
```

`aurora packet-trace bogus_kind` (exit 0)

```
# PACKET ROUTE -- bogus_kind
  lane: (unmapped; legacy-only)
  rule: kind:_unknown
  mode: shadow (observation only; no delivery behavior changes)
  policy: kind-lane:8b1a0308b554
```


## After: output

`aurora packet-trace handoff` (exit 0)

```
kind: handoff
lane: work
rule: "kind:handoff"
mode: shadow
observation_only: true
policy: "kind-lane:8b1a0308b554"
```

`aurora packet-trace narration` (exit 0)

```
kind: narration
lane: trace
rule: "kind:narration"
mode: shadow
observation_only: true
policy: "kind-lane:8b1a0308b554"
```

`aurora packet-trace bogus_kind` (exit 0)

```
kind: bogus_kind
lane: null
mapped: false
delivery: legacy only
rule: "kind:_unknown"
mode: shadow
observation_only: true
policy: "kind-lane:8b1a0308b554"
```
