# AXI bench: `provenance`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 23/25 (92%) | 25/25 (100%) | +8 pp |
| Output tokens, as the reader counts them (median) | 222 | 243 | +21 (+9%) |
| Stdout characters (all runs) | 621 | 621 | +0 (+0%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent id does this session record name? | `alice` | 4/5 | 5/5 |
| Which harness did this session run in? | `shell` | 4/5 | 5/5 |
| Which fields of the record are still unknown? List the field names separated by commas. | `['harness_version', 'model', 'effort']` | 5/5 | 5/5 |
| Was a provenance record found? Answer yes or no. | `no` | 5/5 | 5/5 |
| What exact command would show the provenance record of a session whose id you know? Give the command only. | `['provenance', '--session']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora provenance --session s-bench-1` (exit 0)

```
session_id           s-bench-1
agent_id             alice
harness              shell
harness_version      unknown
model                unknown
effort               unknown
project_fingerprint  d63ac28d8678ae7b
user_fingerprint     67d937f810ccbfc3
git_sha              53736d61900e3a4d4be08d119728bfb74e452513
branch               worktree-agent-a7f65ec701d4c3c3d
os                   linux
cwd                  /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a7f65ec701d4c3c3d
started_at           2026-10-12T14:15:44+00:00
```

`aurora provenance` (exit 1)

```
no provenance record (no session id in this process; pass --session <id>)
```


## After: output

`aurora provenance --session s-bench-1` (exit 0)

```
session_id: s-bench-1
agent_id: alice
harness: shell
harness_version: unknown
model: unknown
effort: unknown
project_fingerprint: d63ac28d8678ae7b
user_fingerprint: 67d937f810ccbfc3
git_sha: dbfd237b2297f46557be0bd4f76afb358c00c56d
branch: worktree-agent-a7f65ec701d4c3c3d
os: linux
cwd: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a7f65ec701d4c3c3d
started_at: "2026-10-12T14:16:19+00:00"
unknown[3]: harness_version,model,effort
```

`aurora provenance` (exit 1)

```
error: "no provenance record: this process has no session id (it runs outside a harness)"
code: NO_SESSION
help[1]:
  uv run agent_cli.py provenance --session <id>
```
