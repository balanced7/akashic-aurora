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


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


def _cli() -> str:
    """The CLI as a printed command names it: `aurora` under the installed launcher, else
    `<_pyl()> agent_cli.py` (core.paths.cli_command)."""
    import os as _os

    return "aurora" if (_os.getenv("AURORA_LAUNCHER") or "").strip() else f"{_pyl()} agent_cli.py"


MCP_NAME = "akashic-aurora"


def _mcp_path(repo=None):
    repo = repo or Path(__file__).resolve().parent.parent
    return Path(repo) / "ai_setup_mcp.py"


def _launch(repo=None):
    """The interpreter prefix for the MCP server: the `py` launcher on Windows (as always);
    elsewhere `py` does not exist, so uv -- by ABSOLUTE path, since an MCP host started from a
    desktop app may not share the shell's PATH -- running inside the repo's project so the
    server's dependencies come with it. No uv: the interpreter running this script."""
    if os.name == "nt":
        return ["py"]
    import shutil

    repo = Path(repo) if repo else Path(__file__).resolve().parent.parent
    uv = shutil.which("uv")
    if uv and (repo / "pyproject.toml").exists():
        return [uv, "run", "--project", str(repo)]
    return [sys.executable]


def _installed_launcher():
    """The installed `aurora` launcher (aurora-cli/), whose `aurora mcp` outlives upgrades."""
    try:
        from core.paths import launcher

        return launcher()
    except Exception:
        return None


def registration_command(repo=None):
    """The exact `claude mcp add` one-liner, with an ABSOLUTE script path (user-scoped)."""
    import shlex

    exe = _installed_launcher()
    if exe:
        return f"claude mcp add --scope user {MCP_NAME} -- {shlex.quote(exe)} mcp"

    launch = " ".join(shlex.quote(a) for a in _launch(repo))
    return f'claude mcp add --scope user {MCP_NAME} -- {launch} "{_mcp_path(repo)}"'


def registration_json(repo=None):
    """The equivalent mcpServers snippet, for manual config editing if preferred."""
    exe = _installed_launcher()
    if exe:
        return {"mcpServers": {MCP_NAME: {"command": exe, "args": ["mcp"], "env": {}}}}
    launch = _launch(repo)
    return {"mcpServers": {MCP_NAME: {"command": launch[0], "args": [*launch[1:], str(_mcp_path(repo))], "env": {}}}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print the user-scoped akashic-aurora MCP registration (T081-W2).")
    ap.add_argument(
        "--json", action="store_true", help="print a ready-to-paste mcpServers JSON snippet instead of the command"
    )
    a = ap.parse_args(argv)
    if a.json:
        print(json.dumps(registration_json(), indent=2))
        return 0
    print("# T081-W2: register the akashic-aurora MCP door USER-scoped (attaches from ANY cwd)")
    print("# 1) run this once:")
    print(f"     {registration_command()}")
    print("# 2) restart Claude Code")
    print(f"# 3) verify: {_cli()} boot claude  ->  '# door: MCP-native' (was 'CLI-shell')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
