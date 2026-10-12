# AXI bench: `kit`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 1,061 | 393 | -668 (-63%) |
| Stdout characters (all runs) | 3,868 | 2,418 | -1,450 (-37%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many entries does the recovery-kit have? | `4` | 5/5 | 5/5 |
| What evidence level does the drain-decide entry carry? | `VERIFIED` | 5/5 | 5/5 |
| Which entry replaced an alias that already existed? Give its name only. | `standby-hard` | 5/5 | 5/5 |
| Which entries were refused? List them separated by commas. | `['vitals', 'premise-check']` | 5/5 | 5/5 |
| Did the second install change any entry? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which kits are available? Give the names only. | `['recovery-kit']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora kit bench --show` (exit 0)

```
{
  "name": "recovery-kit",
  "version": 2,
  "why": "the wake-loop/straggler/stall recovery floor, installable on any seat in one call. Harvested cross-seat 2026-07-21: claude's standby-hard (30+ live receipts), kimi's drain-decide (kata-VERIFIED), deepseek's vitals + premise-check (the eyes). The kit's thesis: recovery is a LOADOUT, not a memory -- a seat that has it installed never hand-types the ceremony.",
  "entries": [
    {
      "name": "standby-hard",
      "steps": [
        [
          "bifrost-pause",
          "--reason",
          "kit-standby",
          "--by",
          "$SELF$",
          "--ttl",
          "120"
        ],
        [
          "bifrost-skip-to-now",
          "$SELF$",
          "--by",
          "$SELF$",
          "--reason",
          "kit-standby-ceremony"
        ],
        [
          "bifrost-resume"
        ]
      ],
      "evidence": "VERIFIED",
      "tested_against": "kata-20260721-020106",
      "why": "claude's, 30+ live receipts: pause+skip+resume, the wake-loop breaker. ttl 120 self-heals a mid-ceremony crash (deepseek find 2026-07-21).",
      "family": "ENGINEERS"
    },
    {
      "name": "drain-decide",
      "steps": [
        [
          "bifrost-sync",
          "$SELF$",
          "--consume"
        ],
        [
          "bifrost-pause",
          "--reason",
          "drain-decide",
          "--by",
          "$SELF$",
          "--ttl",
          "120"
        ],
        [
          "bifrost-skip-to-now",
          "$SELF$",
          "--by",
          "$SELF$",
          "--reason",
          "straggler-triage"
        ],
        [
          "bifrost-resume"
        ]
      ],
      "evidence": "VERIFIED",
      "tested_against": "kata-20260721-020107",
      "why": "kimi's, kata-VERIFIED: consume-then-skip, the straggler triage. ttl 120 self-heals (same graduation as standby-hard).",
      "family": "ENGINEERS"
    },
    {
      "name": "vitals",
      "steps": [
        [
          "doctor"
        ],
        [
          "bifrost_dashboard"
        ]
      ],
      "evidence": "GUESS",
      "why": "deepseek's: is anyone dying silently. The kit's eyes-before-hands law.",
      "family": "LIFEWORKERS"
    },
    {
      "name": "premise-check",
      "steps": [
        [
          "doctor"
        ],
        [
          "delta",
          "$SELF$"
        ],
        [
          "bifrost-inbox"
        ]
      ],
      "evidence": "GUESS",
      "why": "deepseek's: is the system's story about itself true. C9-1's killer.",
      "family": "SENTINELS"
    }
  ]
}
```

`aurora alias bench mint standby-hard --step doctor` (exit 0)

```
[alias] minted standby-hard v1 [GUESS] (UNSORTED) (1 step(s)) -- run: uv run agent_cli.py run bench standby-hard
```

`aurora kit bench` (exit 1)

```
# kit install: recovery-kit v2 -> bench's belt
  [ok] standby-hard       superseded -> v2  [VERIFIED]
  [ok] drain-decide       minted  [VERIFIED]
  [REFUSED] vitals             REFUSED (ValueError: unknown verb 'bifrost_dashboard' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities))
  [REFUSED] premise-check      REFUSED (ValueError: unknown verb 'bifrost-inbox' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities))
kit installed with REFUSALS (see above)
```

`aurora kit bench` (exit 1)

```
# kit install: recovery-kit v2 -> bench's belt
  [ok] standby-hard       no-op (exact re-install)  [VERIFIED]
  [ok] drain-decide       no-op (exact re-install)  [VERIFIED]
  [REFUSED] vitals             REFUSED (ValueError: unknown verb 'bifrost_dashboard' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities))
  [REFUSED] premise-check      REFUSED (ValueError: unknown verb 'bifrost-inbox' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities))
kit installed with REFUSALS (see above)
```

`aurora kit bench nope-kit` (exit 2)

```
[kit] unknown kit 'nope-kit' -- available: recovery-kit
```


## After: output

`aurora kit bench --show` (exit 0)

```
kit: recovery-kit
version: 2
why: "the wake-loop/straggler/stall recovery floor, installable on any seat in one call. Harvested cross-seat 2026-07-21: claude's standby-hard (30+ live receipts), kimi's drain-decide (kata-VERIFIED), deepseek's vitals + premise-check (the eyes). The kit's thesis: recovery is a LOADOUT, not a memory -- a... (truncated, 358 chars total)"
total: 4
entries[4]{name,family,evidence,steps}:
  standby-hard,ENGINEERS,VERIFIED,bifrost-pause -> bifrost-skip-to-now -> bifrost-resume
  drain-decide,ENGINEERS,VERIFIED,bifrost-sync -> bifrost-pause -> bifrost-skip-to-now -> bifrost-resume
  vitals,LIFEWORKERS,GUESS,doctor -> bifrost_dashboard
  premise-check,SENTINELS,GUESS,doctor -> delta -> bifrost-inbox
help[1]:
  uv run agent_cli.py kit bench recovery-kit
```

`aurora alias bench mint standby-hard --step doctor` (exit 0)

```
alias: standby-hard
result: minted
version: 1
evidence: GUESS
family: UNSORTED
steps: 1
help[2]:
  uv run agent_cli.py run bench standby-hard
  uv run agent_cli.py kata bench standby-hard
```

`aurora kit bench` (exit 1)

```
kit: recovery-kit
version: 2
seat: bench
status: installed with refusals
changed: 2
minted: 1
superseded: 1
refused: 2
entries[4]{name,result,evidence,reason}:
  standby-hard,superseded to v2,VERIFIED,null
  drain-decide,minted,VERIFIED,null
  vitals,refused,null,"unknown verb 'bifrost_dashboard' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities)"
  premise-check,refused,null,"unknown verb 'bifrost-inbox' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities)"
help[2]:
  uv run agent_cli.py alias bench list
  uv run agent_cli.py run bench standby-hard --dry
```

`aurora kit bench` (exit 1)

```
kit: recovery-kit
version: 2
seat: bench
status: already installed; nothing changed; some refused
changed: 0
unchanged: 2
refused: 2
entries[4]{name,result,evidence,reason}:
  standby-hard,unchanged,VERIFIED,null
  drain-decide,unchanged,VERIFIED,null
  vitals,refused,null,"unknown verb 'bifrost_dashboard' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities)"
  premise-check,refused,null,"unknown verb 'bifrost-inbox' -- sugar-only: every step must be an existing agent_cli verb (registry cannot mint capabilities)"
help[2]:
  uv run agent_cli.py alias bench list
  uv run agent_cli.py run bench standby-hard --dry
```

`aurora kit bench nope-kit` (exit 2)

```
error: unknown kit 'nope-kit'
code: USAGE
available[1]: recovery-kit
help[1]:
  uv run agent_cli.py kit bench recovery-kit --show
```
