# AXI bench: `suite-baseline`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 61 | 95 | +34 (+56%) |
| Stdout characters (all runs) | 368 | 643 | +275 (+75%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many known failures does the recorded baseline hold? | `100` | 5/5 | 5/5 |
| At which commit sha was the baseline recorded? | `5ba81ba` | 5/5 | 5/5 |
| How many NEW failures does this run have against the baseline? | `1` | 5/5 | 5/5 |
| Which test is the new failure? Give its node id. | `test_parser_roundtrip.py::test_new_flag_survives` | 5/5 | 5/5 |
| How many of this run's failures were already in the baseline? | `2` | 5/5 | 5/5 |
| Which flag must be given to record or check a baseline? Give the flag only. | `--from-file` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora suite-baseline bench --show` (exit 0)

```
# suite baseline @5ba81ba (807.2h old, by claude): 100 known failure(s) -- 1 classified lane(s) since closed (T275): re-run advised (classification rots even when the receipt is young)
```

`aurora suite-baseline bench --check --from-file /tmp/axi-suite-zkgq_38e/pytest.txt` (exit 1)

```
[suite-baseline] vs baseline: 1 NEW, 98 fixed, 2 inherited
  NEW: tests/test_parser_roundtrip.py::test_new_flag_survives
```

`aurora suite-baseline bench` (exit 2)

```
[suite-baseline] need --from-file <pytest output> (or --show)
```


## After: output

`aurora suite-baseline bench --show` (exit 0)

```
sha: 5ba81ba
seat: claude
age_h: 807.3
failures: 100
closed_lanes[1]: T275
advice: re-run and re-record (classification rots)
help[1]:
  uv run agent_cli.py suite-baseline bench --check --from-file <pytest output>
```

`aurora suite-baseline bench --check --from-file /tmp/axi-suite-zkgq_38e/pytest.txt` (exit 1)

```
new: 1
fixed: 98
inherited: 2
new_failures[1]: "tests/test_parser_roundtrip.py::test_new_flag_survives"
help[1]:
  uv run agent_cli.py suite-baseline bench --whose "tests/test_parser_roundtrip.py::test_new_flag_survives"
```

`aurora suite-baseline bench` (exit 2)

```
error: "need --from-file <pytest output> (or --show, or --whose)"
code: USAGE
help[2]:
  uv run agent_cli.py suite-baseline bench --from-file <pytest output>
  uv run agent_cli.py suite-baseline bench --show
```
