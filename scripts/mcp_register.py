"""T081-W2: make the akashic-aurora MCP door attach from ANY launch cwd.

The door is project-scoped today (<repo>/.mcp.json) with a RELATIVE script path, so a Claude
Code session started anywhere but the repo root gets ZERO akashic tools and shells out
`py agent_cli.py ...` all session (the P1 tax; the W1 transport line prints 'door: CLI-shell'
when this bites -- as it did the whole 2026-07-15 session, launched from C:\\Users\\L5).

The fix is a USER-scoped registration with an ABSOLUTE path. That path is machine-specific, so
it belongs in your Claude Code user config, NOT the committed (public) repo -- which is why this
is a printed command you run once, not a repo edit. This script computes the absolute path from
its own location (portable across machines) and PRINTS the one-liner; it does not touch your
config. Run the printed command, then restart Claude Code.

  py scripts/mcp_register.py            # print the apply command + verification steps
  py scripts/mcp_register.py --json     # print a ready-to-paste mcpServers JSON snippet
"""
import argparse
import json
import os
import sys
from pathlib import Path

MCP_NAME = "akashic-aurora"


def _mcp_path(repo=None):
    repo = repo or Path(__file__).resolve().parent.parent
    return Path(repo) / "ai_setup_mcp.py"


def registration_command(repo=None):
    """The exact `claude mcp add` one-liner, with an ABSOLUTE script path (user-scoped)."""
    return f'claude mcp add --scope user {MCP_NAME} -- py "{_mcp_path(repo)}"'


def registration_json(repo=None):
    """The equivalent mcpServers snippet, for manual config editing if preferred."""
    return {"mcpServers": {MCP_NAME: {"command": "py", "args": [str(_mcp_path(repo))], "env": {}}}}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Print the user-scoped akashic-aurora MCP registration (T081-W2).")
    ap.add_argument("--json", action="store_true",
                    help="print a ready-to-paste mcpServers JSON snippet instead of the command")
    a = ap.parse_args(argv)
    if a.json:
        print(json.dumps(registration_json(), indent=2))
        return 0
    print("# T081-W2: register the akashic-aurora MCP door USER-scoped (attaches from ANY cwd)")
    print("# 1) run this once:")
    print(f"     {registration_command()}")
    print("# 2) restart Claude Code")
    print("# 3) verify: py agent_cli.py boot claude  ->  '# door: MCP-native' (was 'CLI-shell')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
