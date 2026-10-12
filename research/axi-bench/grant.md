# AXI bench: `grant`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 33/35 (94%) | 35/35 (100%) | +6 pp |
| Output tokens, as the reader counts them (median) | 105 | 111 | +6 (+6%) |
| Stdout characters (all runs) | 895 | 1,110 | +215 (+24%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many grants are stored? | `4` | 5/5 | 5/5 |
| Which role does bob hold? | `restricted` | 3/5 | 5/5 |
| Which agents hold permanent grants? List them separated by commas. | `['bob', 'boss']` | 5/5 | 5/5 |
| Who granted alice her role? | `boss` | 5/5 | 5/5 |
| Was anything written? Answer yes or no. | `no` | 5/5 | 5/5 |
| Did the grant succeed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which role did carol hold before this command? | `member` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora grant` (exit 0)

```
## GRANTS (4) -- source of truth: security/acl.json
  carol                  member       2026-10-12T23:41:53Z   by=boss
      one-day pairing
  alice                  member       2026-10-13T15:41:52Z   by=boss
      bench seat for tests
  bob                    restricted   permanent              by=boss
      read-only helper
  boss                   super_admin  permanent              by=operator
      bench super-admin
```

`aurora grant dave --role member --by boss --reason trial --hours 4 --dry-run` (exit 0)

```
{
  "agent_id": "dave",
  "role": "member",
  "by": "boss",
  "hours": 4.0,
  "permanent": false,
  "caps": null,
  "path_scope": null,
  "reason": "trial"
}
[grant] DRY RUN -- nothing written. Authority guards run on the real call.
```

`aurora grant dave --role member --by alice --reason trial --hours 1` (exit 2)

```
grant REFUSED: 'alice' resolves to role 'member', which does not hold admin.grant. Only a super-admin mints grants. (This door refuses; it does not authenticate -- see the module docstring.)
```

`aurora grant carol --revoke --by boss --reason pairing over` (exit 0)

```
[grant] REVOKED carol (was member) by boss
```


## After: output

`aurora grant` (exit 0)

```
acl: /tmp/axi-grant-dkhm1jnx/acl.json
total: 4
grants[4]{agent,role,expires,by,reason}:
  carol,member,"2026-10-12T23:42:40Z",boss,one-day pairing
  alice,member,"2026-10-13T15:42:40Z",boss,bench seat for tests
  bob,restricted,permanent,boss,read-only helper
  boss,super_admin,permanent,operator,bench super-admin
help[2]:
  uv run agent_cli.py grant <agent_id> --role member --by <your_id> --reason "<why>" --hours 24
  uv run agent_cli.py grant <agent_id> --revoke --by <your_id> --reason "<why>"
```

`aurora grant dave --role member --by boss --reason trial --hours 4 --dry-run` (exit 0)

```
dry_run: true
written: false
would_grant:
  agent_id: dave
  role: member
  by: boss
  hours: 4
  reason: trial
note: "the authority guards run only on the real call, so this does not say it would pass"
help[1]:
  uv run agent_cli.py grant dave --role member --by boss --reason trial --hours 4
```

`aurora grant dave --role member --by alice --reason trial --hours 1` (exit 2)

```
error: "grant refused: 'alice' resolves to role 'member', which does not hold admin.grant. Only a super-admin mints grants. (This door refuses; it does not authenticate -- see the module docstring.)"
code: REFUSED
help[1]:
  uv run agent_cli.py grant --list
```

`aurora grant carol --revoke --by boss --reason pairing over` (exit 0)

```
revoked: carol
was: member
by: boss
reason: pairing over
```
