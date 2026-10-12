# AXI bench: `audit`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 2,069 | 1,056 | -1,013 (-49%) |
| Stdout characters (all runs) | 4,578 | 1,950 | -2,628 (-57%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many rows have the verdict DRIFT in total? | `17` | 5/5 | 5/5 |
| What verdict does the entry deepseek:parse-gate have? | `MATCH` | 5/5 | 5/5 |
| Which rule fired for the entry deepseek:vitals? | `sugar-only` | 5/5 | 5/5 |
| How many rows did the stale-receipt rule fire on? | `14` | 5/5 | 5/5 |
| What verdict does the SPEND domain's only row have? | `UNKNOWN` | 5/5 | 5/5 |
| Which domain names can be audited? List them separated by commas. | `['VERBS', 'SPEND', 'LEXICON']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora audit` (exit 0)

```
# audit — 31 row(s) across 3 domain(s)
# verdicts: 13 MATCH, 17 DRIFT, 1 UNKNOWN
# ground-truth source: registry

[VERBS] 23 row(s) (6M/17D/0U)
  DRIFT   claude:standby-hard      [stale-receipt] registry claims VERIFIED but kata receipt kata-20260721-020106 (02:01:06) is older than updated_at 2026-07-21T02:04:56
  DRIFT   claude:ask-peer          [stale-receipt] registry claims VERIFIED but kata receipt kata-20260721-005225 (00:52:25) is older than updated_at 2026-07-21T00:55:11
  DRIFT   claude:ask-peer          [argparse-eaten] argparse-eaten token(s): step[1][10] — the '--' positional separator is silently consumed; delivered text is not what was written
  DRIFT   claude:drain-decide      [stale-receipt] registry claims VERIFIED but kata receipt kata-20260721-020107 (02:01:07) is older than updated_at 2026-07-21T02:04:56
  DRIFT   claude:cycle-open        [stale-receipt] registry claims VERIFIED but kata receipt kata-20260827-194259 (19:42:59) is older than updated_at 2026-08-27T23:42:59.657072+00:00
  DRIFT   claude:cycle-tie-up      [stale-receipt] registry claims VERIFIED but kata receipt kata-20260827-194300 (19:43:00) is older than updated_at 2026-08-27T23:43:00.276388+00:00
  DRIFT   claude:cycle-reflect     [stale-receipt] registry claims VERIFIED but kata receipt kata-20260827-194300 (19:43:00) is older than updated_at 2026-08-27T23:43:00.865995+00:00
  DRIFT   claude:cycle-land        [stale-receipt] registry claims VERIFIED but kata receipt kata-20260827-194301 (19:43:01) is older than updated_at 2026-08-27T23:43:01.481936+00:00
  MATCH   claude:calibrate         VERIFIED receipt session 25cd3074, 2026-08-26: both steps run clean; forecast list renders 14 registered with 4 scored (3 hit, 1 voided) and stats renders the coverage/quality pair plus REPEATS updated 03:31
  DRIFT   deepseek:scar-springboard [stale-receipt] registry claims VERIFIED but kata receipt kata-20260720-232707 (23:27:07) is older than updated_at 2026-07-20T23:48:10
  DRIFT   deepseek:orient          [stale-receipt] registry claims VERIFIED but kata receipt kata-20260720-232707 (23:27:07) is older than updated_at 2026-07-20T23:48:10
  MATCH   deepseek:parse-gate      VERIFIED receipt kata-20261001-093758 updated 07:37
  MATCH   deepseek:toast           VERIFIED receipt kata-20261001-093758 updated 07:37
  MATCH   deepseek:muse            VERIFIED receipt kata-20261001-093758 updated 07:37
  DRIFT   deepseek:premise-check   [sugar-only] step[2] verb 'bifrost-inbox' is not a known agent_cli verb (121 verbs in parser)
  MATCH   deepseek:nightcap        GUESS updated 04:35
  DRIFT   deepseek:vitals          [sugar-only] step[1] verb 'bifrost_dashboard' is not a known agent_cli verb (121 verbs in parser)
  DRIFT   dsh_agent:rillsitrep     [stale-receipt] registry claims VERIFIED but kata receipt kata-20260825-203133 (20:31:33) is older than updated_at 2026-08-26T00:31:33.185010+00:00
  MATCH   kimi:drain-decide        VERIFIED receipt kata-20260721-020107 updated 02:01
  DRIFT   kimi:fence               [stale-receipt] registry claims VERIFIED but kata receipt kata-20260720-233836 (23:38:36) is older than updated_at 2026-07-20T23:48:10
  DRIFT   kimi:boot-now            [stale-receipt] registry claims VERIFIED but kata receipt kata-20260720-233836 (23:38:36) is older than updated_at 2026-07-20T23:48:10
  DRIFT   sol:pressure             [stale-receipt] registry claims VERIFIED but kata receipt kata-20260826-234516 (23:45:16) is older than updated_at 2026-08-27T03:48:19.972179+00:00
  DRIFT   sol:dosage               [stale-receipt] registry claims VERIFIED but kata receipt kata-20260826-234842 (23:48:42) is older than updated_at 2026-08-27T04:41:01.425625+00:00

[SPEND] 1 row(s) (0M/0D/1U)
  UNKNOWN kimi:spend               spend meter sidecar unreadable — no spend rows computable

[LEXICON] 7 row(s) (7M/0D/0U)
  MATCH   confidence::learning_loader.py categorical high/medium/low -> boot importance 5/3/2
  MATCH   confidence::tagging.py   a FINITE float clamped to [0,1] on the narrative plane
  MATCH   drained::bus.py          the agent-keyed cursor -- inbox + broadcast position
  MATCH   drained::bus.py          the per-incarnation seat cursor (T108)
  MATCH   drained::bus.py          the lane consumer's durable cursor (T039/T045)
  MATCH   undetectable::canary_oracle.py the planted shape the gate cannot see (class definition)
  MATCH   undetectable::canary_oracle.py score_v2's reading: reaching one is a CAPABILITY observation, not contamination
```

`aurora audit --domain nope` (exit 0)

```
[audit] unknown domain(s) ['NOPE'] -- available: VERBS, SPEND, LEXICON
```


## After: output

`aurora audit` (exit 0)

```
total: 31
match: 13
drift: 17
unknown: 1
ground: registry
domains[3]{domain,rows,match,drift,unknown}:
  VERBS,23,6,17,0
  SPEND,1,0,0,1
  LEXICON,7,7,0,0
by_rule:
  "stale-receipt": 14
  "argparse-eaten": 1
  "sugar-only": 2
  "meter-missing": 1
rows[31]{domain,entry,verdict,rule}:
  VERBS,"claude:standby-hard",DRIFT,stale-receipt
  VERBS,"claude:ask-peer",DRIFT,stale-receipt
  VERBS,"claude:ask-peer",DRIFT,argparse-eaten
  VERBS,"claude:drain-decide",DRIFT,stale-receipt
  VERBS,"claude:cycle-open",DRIFT,stale-receipt
  VERBS,"claude:cycle-tie-up",DRIFT,stale-receipt
  VERBS,"claude:cycle-reflect",DRIFT,stale-receipt
  VERBS,"claude:cycle-land",DRIFT,stale-receipt
  VERBS,"claude:calibrate",MATCH,null
  VERBS,"deepseek:scar-springboard",DRIFT,stale-receipt
  VERBS,"deepseek:orient",DRIFT,stale-receipt
  VERBS,"deepseek:parse-gate",MATCH,null
  VERBS,"deepseek:toast",MATCH,null
  VERBS,"deepseek:muse",MATCH,null
  VERBS,"deepseek:premise-check",DRIFT,sugar-only
  VERBS,"deepseek:nightcap",MATCH,null
  VERBS,"deepseek:vitals",DRIFT,sugar-only
  VERBS,"dsh_agent:rillsitrep",DRIFT,stale-receipt
  VERBS,"kimi:drain-decide",MATCH,null
  VERBS,"kimi:fence",DRIFT,stale-receipt
  VERBS,"kimi:boot-now",DRIFT,stale-receipt
  VERBS,"sol:pressure",DRIFT,stale-receipt
  VERBS,"sol:dosage",DRIFT,stale-receipt
  SPEND,"kimi:spend",UNKNOWN,meter-missing
  LEXICON,"confidence::learning_loader.py",MATCH,null
  LEXICON,"confidence::tagging.py",MATCH,null
  LEXICON,"drained::bus.py",MATCH,null
  LEXICON,"drained::bus.py",MATCH,null
  LEXICON,"drained::bus.py",MATCH,null
  LEXICON,"undetectable::canary_oracle.py",MATCH,null
  LEXICON,"undetectable::canary_oracle.py",MATCH,null
help[2]:
  uv run agent_cli.py audit --fields detail
  uv run agent_cli.py alias claude history standby-hard
```

`aurora audit --domain nope` (exit 2)

```
error: unknown domain(s) NOPE
code: USAGE
available[3]: VERBS,SPEND,LEXICON
help[2]:
  uv run agent_cli.py audit --domain VERBS
  uv run agent_cli.py audit
```
