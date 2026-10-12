# AXI bench: `notes`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 200 | 240 | +40 (+20%) |
| Stdout characters (all runs) | 986 | 1,185 | +199 (+20%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many active notes are there? | `3` | 5/5 | 5/5 |
| Is the open-docket note shown in full here? Answer yes or no. | `no` | 5/5 | 5/5 |
| What exact command prints the full open-docket note? Give the command only. | `['--get', 'open-docket']` | 0/5 | 5/5 |
| How many notes are listed, superseded ones included? | `4` | 5/5 | 5/5 |
| Which note title has an older, superseded version? Give the title only. | `where-we-are` | 5/5 | 5/5 |

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

`aurora notes` (exit 0)

```
# 3 active note(s)
  [2026-10-12] release-plan: Ship 2.0 on Friday after the soak.   (id ADR_1012174221_a89e68f5)
  [2026-10-12] open-docket: Open docket: (1) migrate the ledger table to the new schema, (2) retire the legacy bus lane once the dual-write window closes, (3) re-run ...[truncated]   (id ADR_1012174220_c3068867)
  [2026-10-12] where-we-are: Wave 3 done; next: migrate the ledger table.   (id ADR_1012174220_e0db6b03)
```

`aurora notes --all` (exit 0)

```
# 4 note(s) incl. superseded
  [2026-10-12] release-plan: Ship 2.0 on Friday after the soak.   (id ADR_1012174221_a89e68f5)
  [2026-10-12] open-docket: Open docket: (1) migrate the ledger table to the new schema, (2) retire the legacy bus lane once the dual-write window closes, (3) re-run ...[truncated]   (id ADR_1012174220_c3068867)
  [2026-10-12] where-we-are: Wave 3 done; next: migrate the ledger table.   (id ADR_1012174220_e0db6b03)
  [2026-10-12] [superseded] where-we-are: Wave 2 done; next: the payment refactor.   (id ADR_1012174219_b4f2b3c2)
```


## After: output

`aurora notes` (exit 0)

```
scope: active
total: 3
notes[3]{date,title,note,id}:
  2026-10-12,release-plan,Ship 2.0 on Friday after the soak.,ADR_1012174256_8445c3ea
  2026-10-12,open-docket,"Open docket: (1) migrate the ledger table to the new schema, (2) retire the legacy bus lane once the dual-write window closes, (3) re-run th... (truncated, 194 chars total)",ADR_1012174256_4b515520
  2026-10-12,where-we-are,"Wave 3 done; next: migrate the ledger table.",ADR_1012174255_9b2675a7
help[1]:
  uv run agent_cli.py note bench --get open-docket
```

`aurora notes --all` (exit 0)

```
scope: active and superseded
total: 4
notes[4]{date,title,note,id,status}:
  2026-10-12,release-plan,Ship 2.0 on Friday after the soak.,ADR_1012174256_8445c3ea,active
  2026-10-12,open-docket,"Open docket: (1) migrate the ledger table to the new schema, (2) retire the legacy bus lane once the dual-write window closes, (3) re-run th... (truncated, 194 chars total)",ADR_1012174256_4b515520,active
  2026-10-12,where-we-are,"Wave 3 done; next: migrate the ledger table.",ADR_1012174255_9b2675a7,active
  2026-10-12,where-we-are,"Wave 2 done; next: the payment refactor.",ADR_1012174255_2e85c1af,superseded
help[1]:
  uv run agent_cli.py note bench --get open-docket
```
