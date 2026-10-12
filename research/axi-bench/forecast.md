# AXI bench: `forecast`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 40/40 (100%) | 40/40 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 709 | 439 | -270 (-38%) |
| Stdout characters (all runs) | 4,040 | 2,131 | -1,909 (-47%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many forecasts are registered in total? | `15` | 5/5 | 5/5 |
| What verdict does forecast F008 have? | `partial` | 5/5 | 5/5 |
| How many forecasts are still open (not yet scored)? | `5` | 5/5 | 5/5 |
| Which seat registered forecast F004? | `deepseek` | 5/5 | 5/5 |
| What is claude's hit rate, as a percentage? | `50` | 5/5 | 5/5 |
| Which forecasts are overdue? List their ids separated by commas. | `['F004', 'F005', 'F012', 'F013']` | 5/5 | 5/5 |
| Which flag does `forecast register` need that was not given? Give the flag only. | `--id` | 5/5 | 5/5 |
| Was the score recorded? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora forecast list` (exit 0)

```
  F001 [    hit] claude: by 2026-08-29 the registry holds at least 5 forecasts from at least 2 different seats, wit
  F002 [   miss] claude: after T376 ships, a trivial commit to main rotates the discord gateway, bifrost daemon, an
  F003 [   miss] claude: within 14 days the census enumerates every fact class living in 2+ stores with a declared 
  F004 [   OPEN] deepseek: the wedged-vs-thinking discriminator spec (half_a section 2) classifies the rolling-refres
  F005 [   OPEN] claude: the map's first render ships today with its stamp block, and within 7 days Daniil opens th
  F006 [   miss] claude: drill D1 passes within 7 days: with daemon and runners deliberately killed, phone-only rec
  F007 [    hit] claude: drill D4 passes today: a deliberately broken seat-lane webhook produces a doctor page or d
  F008 [partial] claude: The two-harness integration race (Claude Code vs Serge's DSH) produces at least one ADOPTE
  F009 [    hit] claude: The t384 reconciliation UNTRACKS security/acl.json (instance-local grants, policy staying 
  F010 [partial] claude: The t385 blind fence across two harnesses produces at least one design finding that NEITHE
  F011 [    hit] claude: The media-arsenal-contract reconciliation adopts at least one design element that appears 
  F012 [   OPEN] claude: First Light runs end to end on Daniel's machine within 7 days: a library clip plays throug
  F013 [   OPEN] claude: Piano v2 lands: a swapped-in /piano records at an average of at least 58 fps (checked with
  fc-highstakes-marriage-20260905 [    hit] claude: The four-arm research round will NOT find a novel technique we lack. It will find that our
  involuntary-retrieval-ships-2027h1 [   OPEN] claude: By 2027-02-26, at least one widely-used agent framework (LangGraph, CrewAI, Claude Agent S
```

`aurora forecast list --calibration` (exit 0)

```
  F001 [    hit] claude: by 2026-08-29 the registry holds at least 5 forecasts from at least 2 different seats, wit
  F002 [   miss] claude: after T376 ships, a trivial commit to main rotates the discord gateway, bifrost daemon, an
  F003 [   miss] claude: within 14 days the census enumerates every fact class living in 2+ stores with a declared 
  F004 [   OPEN] deepseek: the wedged-vs-thinking discriminator spec (half_a section 2) classifies the rolling-refres
  F005 [   OPEN] claude: the map's first render ships today with its stamp block, and within 7 days Daniil opens th
  F006 [   miss] claude: drill D1 passes within 7 days: with daemon and runners deliberately killed, phone-only rec
  F007 [    hit] claude: drill D4 passes today: a deliberately broken seat-lane webhook produces a doctor page or d
  F008 [partial] claude: The two-harness integration race (Claude Code vs Serge's DSH) produces at least one ADOPTE
  F009 [    hit] claude: The t384 reconciliation UNTRACKS security/acl.json (instance-local grants, policy staying 
  F010 [partial] claude: The t385 blind fence across two harnesses produces at least one design finding that NEITHE
  F011 [    hit] claude: The media-arsenal-contract reconciliation adopts at least one design element that appears 
  F012 [   OPEN] claude: First Light runs end to end on Daniel's machine within 7 days: a library clip plays throug
  F013 [   OPEN] claude: Piano v2 lands: a swapped-in /piano records at an average of at least 58 fps (checked with
  fc-highstakes-marriage-20260905 [    hit] claude: The four-arm research round will NOT find a novel technique we lack. It will find that our
  involuntary-retrieval-ships-2027h1 [   OPEN] claude: By 2027-02-26, at least one widely-used agent framework (LangGraph, CrewAI, Claude Agent S
# calibration (rate = hits / scored non-void; partial counts against)
  claude: 50%  (hit 5 / miss 3 / partial 2 / voided 0 / residual 0)
  OVERDUE: F004 (deepseek) -- past 2026-08-30, unscored
  OVERDUE: F005 (claude) -- past 2026-08-30, unscored
  OVERDUE: F013 (claude) -- past 2026-09-15, unscored
  OVERDUE: F012 (claude) -- past 2026-09-20, unscored
```

`aurora forecast register` (exit 2)

```
ERROR: forecast register needs --id
```

`aurora forecast score F999 --verdict hit` (exit 1)

```
[forecast] REFUSED: no forecast 'F999' registered
```


## After: output

`aurora forecast list` (exit 0)

```
total: 15
open: 5
scored:
  hit: 5
  miss: 3
  partial: 2
overdue: 4
forecasts[15]{id,verdict,by,horizon}:
  F001,hit,claude,2026-08-29
  F002,miss,claude,2026-08-30
  F003,miss,claude,2026-09-06
  F004,open,deepseek,2026-08-30
  F005,open,claude,2026-08-30
  F006,miss,claude,2026-08-30
  F007,hit,claude,2026-08-25
  F008,partial,claude,2026-09-07
  F009,hit,claude,2026-08-31
  F010,partial,claude,2026-08-31
  F011,hit,claude,2026-09-20
  F012,open,claude,2026-09-20
  F013,open,claude,2026-09-15
  fc-highstakes-marriage-20260905,hit,claude,2026-09-07
  involuntary-retrieval-ships-2027h1,open,claude,2027-02-27
help[3]:
  uv run agent_cli.py forecast score F004 --verdict <hit|miss|partial|voided|residual> --observed "..." --evidence <ref>
  uv run agent_cli.py forecast list --calibration
  uv run agent_cli.py forecast list --fields statement
```

`aurora forecast list --calibration` (exit 0)

```
total: 15
open: 5
scored:
  hit: 5
  miss: 3
  partial: 2
overdue: 4
forecasts[15]{id,verdict,by,horizon}:
  F001,hit,claude,2026-08-29
  F002,miss,claude,2026-08-30
  F003,miss,claude,2026-09-06
  F004,open,deepseek,2026-08-30
  F005,open,claude,2026-08-30
  F006,miss,claude,2026-08-30
  F007,hit,claude,2026-08-25
  F008,partial,claude,2026-09-07
  F009,hit,claude,2026-08-31
  F010,partial,claude,2026-08-31
  F011,hit,claude,2026-09-20
  F012,open,claude,2026-09-20
  F013,open,claude,2026-09-15
  fc-highstakes-marriage-20260905,hit,claude,2026-09-07
  involuntary-retrieval-ships-2027h1,open,claude,2027-02-27
calibration[1]{author,rate,hit,miss,partial,voided,residual}:
  claude,0.5,5,3,2,0,0
overdue_forecasts[4]{id,by,horizon}:
  F004,deepseek,2026-08-30
  F005,claude,2026-08-30
  F013,claude,2026-09-15
  F012,claude,2026-09-20
help[2]:
  uv run agent_cli.py forecast score F004 --verdict <hit|miss|partial|voided|residual> --observed "..." --evidence <ref>
  uv run agent_cli.py forecast list --fields statement
```

`aurora forecast register` (exit 2)

```
error: forecast register needs --id
code: USAGE
help[1]:
  uv run agent_cli.py forecast register --id <id> --statement "..." --horizon +7d --dies-when "..."
```

`aurora forecast score F999 --verdict hit` (exit 1)

```
error: no forecast 'F999' registered
code: REFUSED
help[1]:
  uv run agent_cli.py forecast list
```
