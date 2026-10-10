# aurora

The `aurora` command runs [Akashic Aurora](https://github.com/balanced7/akashic-aurora), the shared memory and coordination layer for coding agents, from any terminal, without a checkout. `aurora <verb>` does what `uv run agent_cli.py <verb>` does in the repo.

## Install

| where | one line |
|---|---|
| macOS, Linux | `curl -fsSL https://github.com/balanced7/akashic-aurora/releases/latest/download/install.sh \| sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://github.com/balanced7/akashic-aurora/releases/latest/download/install.ps1 \| iex"` |
| uv | `uv tool install akashic-aurora-cli` |
| pipx | `pipx install akashic-aurora-cli` |
| try it without installing | `uvx --from akashic-aurora-cli aurora discover` |

Then run `aurora setup`. It wires your agent harness (hooks, the MCP server, your agent id) and prints the command behind each step.

## How it works

The launcher is a small, standard-library-only Python package. On first use, it downloads the Aurora release bundle that matches its own version: the repo tree at that tag. It checks the bundle's sha256, then builds the bundle's locked environment with uv. After that, every call runs that environment's Python directly.

| path | what lives there |
|---|---|
| `~/.aurora/versions/<X.Y.Z>/` | the program: one release bundle and its `.venv` |
| `~/.aurora/data/` | your memory: lessons, session logs, the embedded Redis files. Upgrades never touch it. |
| `~/.aurora/world` | optional: `prod` (the default), `beta` or `alpha` |

| command | what it does |
|---|---|
| `aurora <verb> ...` | any of Aurora's ~110 verbs (`aurora discover` lists them) |
| `aurora mcp` | the MCP server, for `claude mcp add --scope user akashic-aurora -- aurora mcp` |
| `aurora self version` | the launcher version, the program it runs, and where state lives |
| `aurora self update` | install the newest release |
| `aurora self prune` | delete bundles of other versions |
| `aurora self uninstall [--purge]` | delete the bundles; `--purge` also deletes your memory |

| variable | effect |
|---|---|
| `AURORA_REPO=<checkout>` | run a checkout instead of a bundle, with its state beside its code, as `uv run agent_cli.py` does |
| `AURORA_HOME` | move `~/.aurora` |
| `AKASHIC_WORLD` | override the world for one command |

Inside a checkout, `uv run aurora <verb>` uses that checkout.
