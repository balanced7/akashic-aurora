# AXI bench: `doctor`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 882 | 885 | +3 (+0%) |
| Stdout characters (all runs) | 2,044 | 1,952 | -92 (-5%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many findings did the doctor report about agents? | `1` | 5/5 | 5/5 |
| Which agent has a finding? | `carol` | 5/5 | 5/5 |
| Is the redis service running? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which services are down? List their names separated by commas. | `['ui:8787', 'daemon']` | 5/5 | 5/5 |
| What command does the doctor suggest for carol's unread mail? Give the command only. | `['bifrost-skip-to-now', 'carol']` | 5/5 | 5/5 |
| How many agents did the doctor examine? | `6` | 5/5 | 5/5 |

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

`aurora doctor` (exit 0)

```
doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2
  [dashboard] carol: OFFLINE — 1 unread but the agent is GONE (no worklive, no runner, no wake seat). The backlog is ghost mail from a retired seat — retire the inbox or ignore.
              drill: uv run agent_cli.py bifrost-skip-to-now carol --by <you> --reason 'ghost mail from a retired seat'  | or ignore: the mail TTLs with the stream
## SERVICES (fleet infrastructure -- what's running)
  [dashboard] service redis: LIVE -- bus backend
  [ banner  ] service ui:8787: DOWN -- bifrost console
              start: uv run scripts/bifrost_ui.py  (Bash run_in_background)
  [ banner  ] service daemon: DOWN -- no live daemon -- seats self-manage wake/consume; the discord outbound pump (daemon-hosted) has NO host
              start: uv run scripts/bifrost_daemon.py --agent <a> --spawn-runner --runner-consume-lane work [--runner-script bifrost_runner_<a>.py]  (runner seats)  |  uv run scripts/bifrost_daemon.py --agent claude --manage-listener  (wake listeners; revive DAEMON_MODE) -- the flag IS the brain: flagless = alpha, REFUSES under a bare runner
## ACTIVATION (recall injections by lesson family, 24h)
  conductor 0/1 · preregistered 1/1
## TAXONOMY (T176 -- a miss must not read as a decision)
  [dashboard] 2 kind(s) live on >1 plane: decision, note
              drill: py -c "from core.comm.kinds import plane_collisions; print(plane_collisions())"
## ACL MISSING -- BOOTSTRAP FLOOR IN FORCE (security/acl.json unreadable at /tmp/axi-bench-r8_loktj/before/security/acl.json)
  [  page   ] claude=super_admin deepseek=admin, every other id QUARANTINED
              drill: restore your LAST acl.json per security/ACL-MOVED-READ-ME.md -- git show <last-commit>:security/acl.json > security/acl.json; on a fresh instance copy security/acl.example.json AND add your own root/super_admin record by hand (an EMPTY valid acl.json quarantines EVERY seat, claude and deepseek included -- narrower than this floor); then uv run agent_cli.py grant --bootstrap
```


## After: output

`aurora doctor` (exit 0)

```
summary: "doctor: 0 page-grade, 0 banner, 1 dashboard across 6 agent(s) | watches 0/2"
findings[1]{grade,agent,line,drill}:
  dashboard,carol,"carol: OFFLINE — 1 unread but the agent is GONE (no worklive, no runner, no wake seat). The backlog is ghost mail from a retired seat — retire the inbox or ignore.","uv run agent_cli.py bifrost-skip-to-now carol --by <you> --reason 'ghost mail from a retired seat'  | or ignore: the mail TTLs with the stream"
services[3]{service,state,detail,start}:
  redis,live,bus backend,null
  "ui:8787",down,bifrost console,uv run scripts/bifrost_ui.py  (Bash run_in_background)
  daemon,down,no live daemon -- seats self-manage wake/consume; the discord outbound pump (daemon-hosted) has NO host,"uv run scripts/bifrost_daemon.py --agent <a> --spawn-runner --runner-consume-lane work [--runner-script bifrost_runner_<a>.py]  (runner seats)  |  uv run scripts/bifrost_daemon.py --agent claude --manage-listener  (wake listeners; revive DAEMON_MODE) -- the flag IS the brain: flagless = alpha, REFUSES under a bare runner"
activation_24h: conductor 0/1 · preregistered 1/1
taxonomy[1]{finding,drill}:
  "2 kind(s) live on >1 plane: decision, note","py -c \"from core.comm.kinds import plane_collisions; print(plane_collisions())\""
acl:
  grade: page
  state: ACL MISSING -- BOOTSTRAP FLOOR IN FORCE
  path: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-af448b9fb785157e3/security/acl.json
  floor: "claude=super_admin deepseek=admin, every other id QUARANTINED"
  drill: "restore your LAST acl.json per security/ACL-MOVED-READ-ME.md -- git show <last-commit>:security/acl.json > security/acl.json; on a fresh instance copy security/acl.example.json AND add your own root/super_admin record by hand (an EMPTY valid acl.json quarantines EVERY seat, claude and deepseek included -- narrower than this floor); then uv run agent_cli.py grant --bootstrap"
help[1]:
  uv run agent_cli.py unwedge carol
```
