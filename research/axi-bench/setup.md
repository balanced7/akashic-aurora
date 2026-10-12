# AXI bench: `setup`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 1,714 | 1,460 | -254 (-15%) |
| Stdout characters (all runs) | 3,956 | 2,936 | -1,020 (-26%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did this run write anything to disk? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which agent id would the Claude Code seat write memory as? | `benchseat` | 5/5 | 5/5 |
| How many codex hooks would be registered? | `5` | 5/5 | 5/5 |
| Whose name would go on commits that agents make? Give the name only, without the email. | `Bench Person` | 5/5 | 5/5 |
| What command changes, later, whose name goes on agent commits? Give the command only. | `['setup', '--operator']` | 5/5 | 5/5 |
| Would the akashic-aurora MCP tools be registered user-wide by this run? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora setup --yes --dry-run --harness claude --harness codex --scope project --project /tmp/axi-setup-2ms43dl8 --agent-id benchseat --operator Bench Person <bench@example.com>` (exit 0)

```
Akashic Aurora setup. Each step shows the command that does the same thing later.
DRY RUN: nothing will be written.
[1/5] OS: linux; repo: /tmp/axi-bench-tlj2g_wj/before
[1/5] harnesses found: claude, cursor
        claude: register Aurora's hooks for every project (user), one project (project), or skip? [user/project/skip] -> project
[2/5] claude hooks: project
[hooks] 10 hook(s) registered in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json
        -> later: uv run agent_cli.py hooks install --harness claude --scope project --project "/tmp/axi-setup-2ms43dl8"
        -> later: uv run agent_cli.py hooks disable --harness claude --scope project --project "/tmp/axi-setup-2ms43dl8"    # off, remembered; `hooks enable --harness claude --scope project --project "/tmp/axi-setup-2ms43dl8"` brings them back
        codex: register Aurora's hooks for every project (user), one project (project), or skip? [user/project/skip] -> project
[2/5] codex hooks: project
[hooks] 5 hook(s) registered in /tmp/axi-setup-2ms43dl8/.codex/hooks.json
        -> later: uv run agent_cli.py hooks install --harness codex --scope project --project "/tmp/axi-setup-2ms43dl8"
        -> later: uv run agent_cli.py hooks disable --harness codex --scope project --project "/tmp/axi-setup-2ms43dl8"    # off, remembered; `hooks enable --harness codex --scope project --project "/tmp/axi-setup-2ms43dl8"` brings them back
        agent id this Claude Code seat writes memory as (AKASHIC_AGENT_ID)? -> benchseat
[3/5] AKASHIC_AGENT_ID=benchseat would be set in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json
        -> later: edit "env": {"AKASHIC_AGENT_ID": "..."} in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json
        whose name goes on commits agents make (Name <email>)? -> Bench Person <bench@example.com>
[3/5] operator would be Bench Person <bench@example.com> in /tmp/axi-bench-tlj2g_wj/data/state/identity/operator.json
        -> later: uv run agent_cli.py setup --operator "Name <email>"   # change whose name goes on agent commits
[4/5] this repo's .mcp.json already gives Claude Code the akashic-aurora tools when launched here.
        register them user-wide, so every Claude Code session gets them? [y/n] -> n
        -> later: uv run scripts/mcp_register.py   # prints: claude mcp add --scope user akashic-aurora -- /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.venv/bin/uv run --project /tmp/axi-bench-tlj2g_wj/before "/tmp/axi-bench-tlj2g_wj/before/ai_setup_mcp.py"
        install the repo's git hooks (pre-commit guardrails, commit-msg lint)? [y/n] -> y
[5/5] would run scripts/githooks/install_git_hooks.py
        -> later: uv run scripts/githooks/install_git_hooks.py

Done. Where things stand:
  claude  project (shared) /tmp/axi-bench-tlj2g_wj/before/.claude/settings.json
    3 installed
      not registered in any claude file: PostToolUseFailure:claude_posttooluse.py, PreCompact:claude_sessionend.py, PreToolUse:claude_browser_guard.py, PreToolUse:claude_pretooluse.py, SessionEnd:claude_sessionend.py, SessionStart:claude_sessionstart.py, UserPromptSubmit:claude_userpromptsubmit.py (fix: agent_cli.py hooks install --harness claude --scope user)
  codex   project          /tmp/axi-bench-tlj2g_wj/before/.codex/hooks.json
    5 installed
  cursor  project          /tmp/axi-bench-tlj2g_wj/before/.cursor/hooks.json
    6 installed

The commands you just met:
  uv run agent_cli.py hooks status                       # what is registered where
  uv run agent_cli.py hooks disable --scope user         # switch user-level hooks off (remembered)
  uv run agent_cli.py hooks enable --scope user          # ...and back on
  uv run agent_cli.py discover [word]                    # every verb, one line each
  uv run agent_cli.py discover --semantic "<need>"       # does something already do this?
  uv run agent_cli.py boot <agent_id> --task "..."       # start of every task (AGENTS.md)
```


## After: output

`aurora setup --yes --dry-run --harness claude --harness codex --scope project --project /tmp/axi-setup-2ms43dl8 --agent-id benchseat --operator Bench Person <bench@example.com>` (exit 0)

```
dry_run: true
steps[11]{step,did}:
  1/5,"OS: linux; repo: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492"
  1/5,"harnesses found: claude, cursor"
  2/5,"claude hooks: project"
  hooks,10 hook(s) registered in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json
  2/5,"codex hooks: project"
  hooks,5 hook(s) registered in /tmp/axi-setup-2ms43dl8/.codex/hooks.json
  3/5,AKASHIC_AGENT_ID=benchseat would be set in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json
  3/5,operator would be Bench Person <bench@example.com> in /tmp/axi-bench-tlj2g_wj/data/state/identity/operator.json
  4/5,this repo's .mcp.json already gives Claude Code the akashic-aurora tools when launched here.
  4/5,not registered user-wide
  5/5,would run scripts/githooks/install_git_hooks.py
later[8]{command,does}:
  "uv run agent_cli.py hooks install --harness claude --scope project --project \"/tmp/axi-setup-2ms43dl8\"",null
  "uv run agent_cli.py hooks disable --harness claude --scope project --project \"/tmp/axi-setup-2ms43dl8\"","off, remembered; `hooks enable --harness claude --scope project --project \"/tmp/axi-setup-2ms43dl8\"` brings them back"
  "uv run agent_cli.py hooks install --harness codex --scope project --project \"/tmp/axi-setup-2ms43dl8\"",null
  "uv run agent_cli.py hooks disable --harness codex --scope project --project \"/tmp/axi-setup-2ms43dl8\"","off, remembered; `hooks enable --harness codex --scope project --project \"/tmp/axi-setup-2ms43dl8\"` brings them back"
  "edit \"env\": {\"AKASHIC_AGENT_ID\": \"...\"} in /tmp/axi-setup-2ms43dl8/.claude/settings.local.json",null
  "uv run agent_cli.py setup --operator \"Name <email>\"",change whose name goes on agent commits
  uv run scripts/mcp_register.py,"prints: claude mcp add --scope user akashic-aurora -- /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.venv/bin/uv run --project /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492 \"/mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/ai_setup_mcp.py\""
  uv run scripts/githooks/install_git_hooks.py,null
hooks[4]{harness,scope,installed,path}:
  claude,project (shared),3,/mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.claude/settings.json
  claude,project,7,/mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.claude/settings.local.json
  codex,project,5,/mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.codex/hooks.json
  cursor,project,6,/mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a5e72da4a0e872492/.cursor/hooks.json
help[1]:
  uv run agent_cli.py setup --yes --harness claude --harness codex --scope project --project /tmp/axi-setup-2ms43dl8 --agent-id benchseat --operator 'Bench Person <bench@example.com>'
```
