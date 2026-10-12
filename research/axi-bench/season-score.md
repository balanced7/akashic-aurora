# AXI bench: `season-score`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 34/35 (97%) | 35/35 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 165 | 189 | +24 (+15%) |
| Stdout characters (all runs) | 3,164 | 1,852 | -1,312 (-41%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many points does alice have in total? | `4` | 5/5 | 5/5 |
| How many claims were left unscored? | `1` | 5/5 | 5/5 |
| Which player's claim was unscored? | `carol` | 4/5 | 5/5 |
| Which player ranks first under v2_aixcc? | `bob` | 5/5 | 5/5 |
| Do the two policies rank the players in a different order? Answer yes or no. | `yes` | 5/5 | 5/5 |
| What is bob's delta between the two policies? | `4` | 5/5 | 5/5 |
| Which scoring policy is the default? | `v1_doc` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora season-score --round-file /tmp/axi-season-5d6_o_tl/round.json` (exit 0)

```
## ROUND SCORE (policy v1_doc, 1 unscored)
  alice                4
  bob                  3
  carol               -1
  [unscored] carol k4: unscored: no resolvable evidence lines
```

`aurora season-score --round-file /tmp/axi-season-5d6_o_tl/round.json --compare` (exit 0)

```
## SCORING POLICY DIFF -- same claims, both rule sets
  alice            v1=    4  v2=    4  delta=   +0
  bob              v1=    3  v2=    7  delta=   +4
  carol            v1=   -1  v2=   -1  delta=   +0

  rank v1_doc  : alice > bob > carol
  rank v2_aixcc: bob > alice > carol
  ^ the proposals CHANGE THE ORDER -- this is the decision, not a tuning knob
```

`aurora season-score --policies` (exit 0)

```

## v1_doc  [DEFAULT]
Exactly the committed table, section 1.6. Pinned so the design doc stays executable.

## v2_aixcc  [PROPOSED]
PROPOSED (W2), not the default. Four changes, each with a reason: (1) UPTIME AS A SCORED AXIS -- AIxCC scores availability because a competitor that is down contributes nothing; here a wedged seat currently scores the same as a live player who found nothing, which is the exact ambiguity T155 was filed about. (2) GRADUATED ACCURACY PENALTY replacing the flat -2 -- a flat penalty is regressive: it is trivial for a high-volume player and severe for a careful one, so it taxes care rather than inaccuracy. Scale by the player's own refuted RATE. (3) DUPLICATE DECAY rather than a hard zero -- a hard zero makes independent near-simultaneous discovery worthless, which suppresses exactly the corroboration that makes a finding trustworthy. (4) VALUE WEIGHTING -- a confirmed finding that is later FIXED is worth more than one that sits on the board.

## v3_confidence_priced  [PROPOSED]
PROPOSED 2026-08-07, NOT the default -- same standing as v2_aixcc, and it carries v2's four changes plus one more. Closes the HEDGE EXPLOIT (T221), found by attacking this scorer before the season ran: a player with 3 real finds and THIRTY wrong claims, every one marked low-confidence, outscored a player with the same 3 finds and one wrong high-confidence claim -- 6 to 4 under v1_doc, 6 to 5 under v2_aixcc, and unbounded in both (300 wrong claims cost exactly what 30 do, which is nothing). CAUSE: refuted_low_confidence=0 gives an honestly-flagged wrong claim downside protection, which is right; but a CONFIRMED low-confidence claim still earns FULL points, so the protection is free. In competition terms that is a free option, and a free option is always exercised -- the dominant strategy becomes hedge everything, spray, keep the hits. TWO KNOBS, and they must move together. (1) low_confidence_credit prices the option: a hedged claim that lands earns less than one its author stood behind, so confidence becomes a real trade rather than a free put. (2) low_confidence_free_misses bounds the volume: the first few honest misses stay free -- that is the whole point of the floor and it must survive -- but the exemption stops being infinite. WHY BOTH: pricing alone still lets a hedger spray at zero downside, and bounding alone makes honest uncertainty expensive without making confidence worth anything. The failure mode to avoid is over-correcting into punishing flagged doubt, which buys FALSE CONFIDENCE -- strictly worse than noise, because noise is filterable and false confidence is not.
```


## After: output

`aurora season-score --round-file /tmp/axi-season-5d6_o_tl/round.json` (exit 0)

```
policy: v1_doc
claims: 6
unscored: 1
totals[3]{player,points}:
  alice,4
  bob,3
  carol,-1
unscored_claims[1]{player,dedupe_key,reason}:
  carol,k4,"unscored: no resolvable evidence lines"
help[2]:
  uv run agent_cli.py season-score --round-file /tmp/axi-season-5d6_o_tl/round.json --compare
  uv run agent_cli.py season-score --round-file /tmp/axi-season-5d6_o_tl/round.json --json
```

`aurora season-score --round-file /tmp/axi-season-5d6_o_tl/round.json --compare` (exit 0)

```
players[3]{player,v1_doc,v2_aixcc,delta}:
  alice,4,4,0
  bob,3,7,4
  carol,-1,-1,0
rank_v1_doc[3]: alice,bob,carol
rank_v2_aixcc[3]: bob,alice,carol
order_changed: true
help[2]:
  uv run agent_cli.py season-score --policies
  uv run agent_cli.py season-score --round-file /tmp/axi-season-5d6_o_tl/round.json --policy v2_aixcc
```

`aurora season-score --policies` (exit 0)

```
policies[3]{policy,status,notes}:
  v1_doc,default,"Exactly the committed table, section 1.6. Pinned so the design doc stays executable."
  v2_aixcc,proposed,"PROPOSED (W2), not the default. Four changes, each with a reason: (1) UPTIME AS A SCORED AXIS -- AIxCC scores availability because a competitor that is down contributes nothing; here a wedged seat currently scores the same as a live player who found nothing, which is the exact ambiguity T155 was filed about. (2) GRADUATED ACCURACY PENALTY replacing the flat -2 -- a flat penalty is regressive: it i... (truncated, 848 chars total)"
  v3_confidence_priced,proposed,"PROPOSED 2026-08-07, NOT the default -- same standing as v2_aixcc, and it carries v2's four changes plus one more. Closes the HEDGE EXPLOIT (T221), found by attacking this scorer before the season ran: a player with 3 real finds and THIRTY wrong claims, every one marked low-confidence, outscored a player with the same 3 finds and one wrong high-confidence claim -- 6 to 4 under v1_doc, 6 to 5 under... (truncated, 1605 chars total)"
help[1]:
  uv run agent_cli.py season-score --round-file <round.json> --compare
```
