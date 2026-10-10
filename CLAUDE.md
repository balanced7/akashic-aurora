# CLAUDE.md

@AGENTS.md

Claude Code notes on top of the shared contract above:

- Skills live in `.agents/skills/` (one source for every harness); `.claude/skills` is a symlink to it.
- Hooks: `uv run agent_cli.py hooks status` shows what is wired; `setup` or `hooks install` wires it.
- Unsure a command exists? `uv run agent_cli.py discover [word]`, or the MCP `discover` tool.
