# AXI bench: `ground`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/30 (67%) | 30/30 (100%) | +33 pp |
| Output tokens, as the reader counts them (median) | 0 | 461 | n/a |
| Stdout characters (all runs) | 2,677 | 2,749 | +72 (+3%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What is the state of the EXERCISED rung? Give one word. | `partial` | 0/5 | 5/5 |
| How many blind spots does the result report? | `2` | 0/5 | 5/5 |
| How many lessons by this seat were observed? | `2` | 5/5 | 5/5 |
| Was an identity verdict computed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Who handed work to this seat? | `alice` | 5/5 | 5/5 |
| What must be added to the command for seat grounding to run? Give the flag only. | `['--continuity']` | 5/5 | 5/5 |

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

`aurora ground verb:recall` (exit 0)

```

```

`aurora ground seat:bench --continuity` (exit 0)

```
# ground seat:bench --continuity
  observed 2026-10-12T16:14:20.111905Z | effects: none
  IDENTITY VERDICT: NOT COMPUTED -- continuity evidence is not an identity verdict; only the ratified resident registry may supply a designation, and no region can nominate or ratify one

## DESIGNATION  ABSENT [ratified_resident_registry]  shown 0/0
  no ratified resident designation observed in the authoritative read; this does not claim that the seat or its history does not exist
  source: core/fleet/residents.py:get + history (exact seat key)
  drill: uv run agent_cli.py resident show bench

## LESSONS  OBSERVED [exact_lesson_authorship]  shown 2/2
  exact subject-authored lessons; these are self-receipts, not a designation
  source: LearningStore learn:agent:bench exact index
  - cache_fix: a  [learn:experiment:cache_fix]
  - port_clash: check port 16379  [learn:experiment:port_clash]
  drill: uv run agent_cli.py recall --full learn:experiment:cache_fix --json

## NOTES  ABSENT [subject_scoped_not_author_verified]  shown 0/0
  no matching notes observed within this source and its stated bounds; absence is not nonexistence
  source: AgentMemory active decision heads, 3650-day read window
  BLIND: scratch title prefix scopes a note but the record has no author field
  drill: use the bound ToolBox memory_recall door for bench

## HANDOFFS  OBSERVED [directional_attribution]  shown 1/1
  exact inbound/outbound handoffs; direction is preserved and inbound prose is not self-authorship
  source: AgentSignalLedger canonical replay (cap 10000)
  - inbound alice -> bench: finish the AXI batch  [agent-signal:1791821658505-0]
  drill: inbound: uv run agent_cli.py handoff bench --list --to bench --json; outbound has no dedicated CLI reader, so use this grounded region

## ARTIFACTS  ABSENT [header_attribution_not_authorship]  shown 0/0
  no matching artifacts observed within this source and its stated bounds; absence is not nonexistence
  source: AtomFamily.find full current corpus; exact header.seats membership
  drill: no dedicated exact atom read door; use the atom:<id> source shown by this region

## MOVEMENT  OBSERVED [telemetry_attribution_not_identity]  shown 2/2
  exact agent telemetry attribution; activity is not identity authority
  source: EventLog per-agent stream events:bench:raw
  - 2026-10-12T16:14:18.107538+00:00 learning: lesson: cache_fix  [event:events:bench:raw:1791821658110-0]
  - 2026-10-12T16:14:17.685822+00:00 learning: lesson: port_clash  [event:events:bench:raw:1791821657688-0]
  drill: uv run agent_cli.py events --get event:events:bench:raw:1791821658110-0 --json
```

`aurora ground seat:bench` (exit 2)

```
ERROR: seat grounding requires the explicit --continuity mode
```


## After: output

`aurora ground verb:recall` (exit 0)

```
target: "verb:recall"
subject: bench
observed_at: "2026-10-12T16:14:56.832271Z"
effects: none
rungs[6]{rung,state,claim,source}:
  declared,observed,door-parity manifest classifies recall as shared,scripts/checkers/check_door_parity.py (live manifest and AST census)
  reachable,observed,all 3 declared door addresses are present,scripts/checkers/check_door_parity.py (live manifest and AST census)
  authorized,unknown,effective grant was compared only where a subject gate is mechanically known,security/acl.json via core.trust.registry.resolve + door implementations
  wired,observed,"every declared endpoint resolves to a callable, advertised handler",live parser defaults + MCP callables + ToolBox method/schema
  exercised,partial,102 test file(s) reference the verb; this scan does not establish that they ran or passed,tests/test_*.py bounded lexical reference scan (not execution)
  proven,unknown,no canonical fresh runtime receipt resolver currently maps this verb to a successful execution,"canonical runtime receipt resolver: unavailable"
blind_total: 2
blind[2]: "fresh runtime proof: no canonical verb-to-receipt resolver",test reference scan was truncated
help[1]:
  uv run scripts/checkers/check_door_parity.py --report
```

`aurora ground seat:bench --continuity` (exit 0)

```
target: "seat:bench"
observed_at: "2026-10-12T16:14:57.755691Z"
effects: none
identity_verdict: not computed
identity_claim: "continuity evidence is not an identity verdict; only the ratified resident registry may supply a designation, and no region can nominate or ratify one"
regions[6]{region,state,authority,shown,matched}:
  designation,absent,ratified_resident_registry,0,0
  lessons,observed,exact_lesson_authorship,2,2
  notes,absent,subject_scoped_not_author_verified,0,0
  handoffs,observed,directional_attribution,1,1
  artifacts,absent,header_attribution_not_authorship,0,0
  movement,observed,telemetry_attribution_not_identity,2,2
items[5]{region,item}:
  lessons,"cache_fix: a [learn:experiment:cache_fix]"
  lessons,"port_clash: check port 16379 [learn:experiment:port_clash]"
  handoffs,"inbound alice -> bench: finish the AXI batch [agent-signal:1791821696397-0]"
  movement,"2026-10-12T16:14:56.054675+00:00 learning: lesson: cache_fix [event:events:bench:raw:1791821696057-0]"
  movement,"2026-10-12T16:14:55.650814+00:00 learning: lesson: port_clash [event:events:bench:raw:1791821695654-0]"
blind[1]: "notes: scratch title prefix scopes a note but the record has no author field"
help[2]:
  uv run agent_cli.py recall --full learn:experiment:cache_fix --json
  uv run agent_cli.py events --get event:events:bench:raw:1791821696057-0 --json
```

`aurora ground seat:bench` (exit 2)

```
error: seat grounding requires the explicit --continuity mode
code: USAGE
help[1]:
  uv run agent_cli.py ground seat:bench --continuity --agent bench
```
