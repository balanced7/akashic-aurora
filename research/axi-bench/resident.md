# AXI bench: `resident`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/35 (69%) | 35/35 (100%) | +31 pp |
| Output tokens, as the reader counts them (median) | 47 | 97 | +50 (+106%) |
| Stdout characters (all runs) | 673 | 1,145 | +472 (+70%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What is alice's callsign? | `Lantern` | 1/5 | 5/5 |
| Which role is alice operating as right now? | `Jester` | 3/5 | 5/5 |
| Who ratified alice's callsign? | `operator` | 5/5 | 5/5 |
| Is carol's callsign ratified yet? Answer yes or no. | `no` | 5/5 | 5/5 |
| What command would ratify carol's callsign? Give the command only. | `['resident ratify carol', '--callsign ember']` | 0/5 | 5/5 |
| How many residents are on the roster? | `2` | 5/5 | 5/5 |
| Did the nomination succeed? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora resident show alice` (exit 0)

```
# scouts | blue | 7 - Lantern
  earned by: alice_port_fix
  ratified by operator
  operating as: Jester (Red / ex7) [assigned] by bob
```

`aurora resident show carol` (exit 0)

```
# carol has 1 nomination(s) on record but NONE ratified yet.
  [nominated] 'Ember' by bob -- receipts: carol_note
```

`aurora resident roster` (exit 0)

```
# all residents: 2
  scouts | blue | 7 - Lantern
  carol
```

`aurora resident roles` (exit 0)

```
  alice 'Lantern' -- Jester (Red / ex7) [assigned] by bob
```

`aurora resident nominate dave --callsign Moss --receipt alice_port_fix --by bob` (exit 1)

```
[resident] refused: receipt 'alice_port_fix' was authored by 'alice', not by the nominee 'dave'. Ceremony rule 2 -- the receipt must come from the RECIPIENT's archive. A receipt someone else wrote is a recollection about them, which is the [M]-tag error: it must mean 'I have the receipt', never 'I remember'.
```


## After: output

`aurora resident show alice` (exit 0)

```
agent: alice
callsign: Lantern
designation: scouts | blue | 7 - Lantern
earned_by[1]: alice_port_fix
ratified_by: operator
operating_as:
  role: Jester
  side: Red
  exercise: ex7
  provenance: assigned
  by: bob
```

`aurora resident show carol` (exit 0)

```
agent: carol
ratified: false
nominations[1]{state,callsign,by,receipts}:
  nominated,Ember,bob,carol_note
help[1]:
  uv run agent_cli.py resident ratify carol --callsign Ember --by <you>
```

`aurora resident roster` (exit 0)

```
total: 2
residents[2]{agent,callsign,designation,ratified}:
  alice,Lantern,scouts | blue | 7 - Lantern,true
  carol,Ember,null,false
help[2]:
  uv run agent_cli.py resident show <agent>
  uv run agent_cli.py resident roles
```

`aurora resident roles` (exit 0)

```
total: 1
assignments[1]{agent,role,side,exercise,provenance,by}:
  alice,Jester,Red,ex7,assigned,bob
help[1]:
  uv run agent_cli.py resident show alice
```

`aurora resident nominate dave --callsign Moss --receipt alice_port_fix --by bob` (exit 1)

```
error: "refused: receipt 'alice_port_fix' was authored by 'alice', not by the nominee 'dave'. Ceremony rule 2 -- the receipt must come from the RECIPIENT's archive. A receipt someone else wrote is a recollection about them, which is the [M]-tag error: it must mean 'I have the receipt', never 'I remember'."
code: REFUSED
help[1]:
  uv run agent_cli.py resident roster
```
