# Deploying Akashic Aurora

Status: current  (2026-07-09, P4: Living ops doc)

How to stand up Akashic Aurora on your own machine. It's deliberately easy: the **core runs on the
Python standard library alone** and degrades gracefully when optional infrastructure (Redis) is absent.

> **Launcher:** the primary path is uv on every OS: `uv sync` once, then `uv run <script>` /
> `uv run python ...`. Many examples below are written with `py` (the Windows launcher), the fallback
> when uv is not installed; with uv type `uv run` in its place, and without uv on macOS/Linux use
> `python3`. Everything else is identical.

---

## 1. Requirements

- **Python 3.11+** (the floor in `pyproject.toml`; `uv` runs the pinned 3.12 from `.python-version`).
- **git**.
- **No Redis server needed.** If one is running the system uses it; if not, the bus runs on an
  embedded, SQLite-persisted Redis that starts itself (§5).
- *Optional:* **Claude Code** (or Cursor) — if you want the agent-facing features (recall-at-action, the
  coordination guards).

Memory (boot / learn / recall) runs on the standard library alone. The bus, the MCP door, the runners
and the test suite need the packages in `requirements.txt` / `pyproject.toml` — Python packages only.

## 2. Quick start

```bash
git clone https://github.com/balanced7/akashic-aurora.git
cd akashic-aurora

# Primary, any OS: uv installs the locked environment (uv.lock) on the pinned Python (.python-version)
uv sync
uv run agent_cli.py status

# Fallback without uv (the Windows `py` setup):
py -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
py -m pip install -r requirements.txt
```

`requirements.txt` and `requirements/gemini-web.txt` are generated from `uv.lock` for pip consumers
(`uv run poe lock`; `uv run poe lock-check` fails if they are stale). Never hand-edit them.

## 3. Verify the install

```bash
uv run bootstrap.py --agent-init  # prints JSON: the init command, the python cmd, Redis status, lesson count
uv run poe gate                   # the local gate: format, lint, types, lock, deps, guardrails, fast tests
uv run poe test                   # the full suite (REDIS_DB=15), with coverage
```

Fallback without uv (Windows): `py bootstrap.py --agent-init`, `py -m pytest -q` (needs pytest),
`py scripts/checkers/check_boundaries.py` (architecture guardrail, should exit 0).

If `bootstrap.py --agent-init` prints a JSON blob and `uv run poe gate` passes (on the fallback:
`check_boundaries` says PASS), you're up.

## 4. Use it

The whole system is reached through one door — `agent_cli.py`:

```bash
py agent_cli.py boot <your_agent_id> --task "what you're doing"   # load relevant context (warms recall)
py agent_cli.py learn <your_agent_id> --experiment NAME \
    --tried "what you did" --result "what happened" --recommend "what's next"
py agent_cli.py recall "keyword"                                  # search past lessons
py agent_cli.py recall-at --path <file>                           # lessons/locks relevant to a file
py agent_cli.py status                                            # backend + lesson counts
py agent_cli.py story                                             # the chronicled narrative
```

Read [`AGENTS.md`](../AGENTS.md) for the full agent contract and [`bootstrap.md`](../bootstrap.md) to orient.

## 5. Redis (nothing to install)

Every process talks Redis protocol to the store and the Bifrost bus (mail, wake listeners, handoffs,
presence). You do not need to install Redis:

- **No Redis server on this machine:** the first process that needs one starts an **embedded Redis**
  — a pure-Python server (fakeredis, with Lua via lupa) on the same port, persisting every change to
  `state/redis-embedded/<port>.sqlite3` within a fraction of a second. It is started detached and keeps
  running for every later process. `py -m core.foundation.embedded_redis --status` shows who serves
  each world port.
- **A real Redis server:** used as-is. The first answer is recorded (`state/redis-backend`), so a real
  Redis that is briefly down is never replaced by an embedded one that would split the bus in two.
- **Choose explicitly:** `AKASHIC_REDIS_BACKEND=embedded` or `=external`.

To use a real Redis instead:

- **Default endpoint:** `localhost:16379` (declared in `config.py`), overridable with the `REDIS_HOST` /
  `REDIS_PORT` environment variables.
- **Run one that matches the default:**

  ```bash
  docker run -d --name akashic-redis -p 16379:6379 redis:7
  ```

  (maps host port 16379 → Redis's in-container 6379). Or point the system at any Redis you already run:
  `REDIS_PORT=6379 py agent_cli.py status`.
- **Sandbox for experiments:** set `REDIS_DB=15` to keep all reads/writes off the canonical database (db 0).

## 6. Recall-at-action (Claude Code hooks)

Akashic Aurora can surface the right lessons + peer-lock warnings **at the moment you edit a file** via a
Claude Code `PreToolUse` hook, and pre-warm its cache at session start. There are two ways to wire it.

### Option A — launch Claude from the repo (zero setup)
The repo ships a project-level [`.claude/settings.json`](../.claude/settings.json) with the hooks already
wired (relative paths). Launch Claude Code **from the repo directory** and recall-at-action + the git/lock
guards are live. **On macOS/Linux**, change the hook command `py` → `python3` in that file.

### Option B — fire from any directory (the "read bootstrap" flow)
Register the hooks in your **user-level** settings (`~/.claude/settings.json`) with **absolute** paths and a
scope guard so they're silent outside this repo. Adjust the path and use `python3` on macOS/Linux:

```json
{
  "env": { "AKASHIC_AGENT_ID": "your_agent_id" },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",                  "hooks": [{ "type": "command", "command": "py /abs/path/to/akashic-aurora/scripts/hooks/claude_pretooluse.py" }] },
      { "matcher": "Edit|Write|NotebookEdit","hooks": [{ "type": "command", "command": "py /abs/path/to/akashic-aurora/scripts/hooks/claude_pretooluse.py" }] }
    ],
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "py /abs/path/to/akashic-aurora/scripts/hooks/claude_sessionstart.py" }] }
    ]
  }
}
```

The hook is a **silent no-op outside the repo**, **fail-open** (never blocks an action), capped, and
faithfulness-gated. Knobs:

- `AKASHIC_AGENT_ID` — your agent's id (lets the lock guard tell your edits from a peer's).
- `AKASHIC_RECALL_AT_ACTION=0` — turn recall injection off.
- `AKASHIC_RECALL_CACHE_TTL` — recall cache freshness in seconds (default 120).

Mark which recalled lessons actually helped so ranking improves over time:
`py agent_cli.py recall-feedback --source learn:experiment:NAME --useful` (or `--noise`).

## 7. Multi-agent (optional)

Two agents (e.g. Claude + Cursor) can share one substrate. Give each a distinct `AKASHIC_AGENT_ID`, run a
shared Redis (§5), and they coordinate via advisory path-locks and the message bus. See
[`docs/library/design/20260709_concurrent-agents-reinforcing-two-peers_5f6723.md`](concurrency-design.md).

## 8. Machine-specific paths (environment variables)

Nothing in the code names a drive or a user folder. The repo root is derived from where the code
lives, and the sibling world checkouts (`<name>-Beta`, `<name>-Alpha`) from the repo root. Paths
that are genuinely a fact about one machine come from these variables. Lists are absolute paths
separated by `;` on Windows and `:` elsewhere; relative entries are ignored with a warning.

| Variable | What it sets | When unset |
|---|---|---|
| `AKASHIC_TRANSCRIPT_ARCHIVE_ROOTS` | Where `scripts/ops/archive_transcripts.py` copies transcripts, and where the transcript index reads them. Unredacted — keep these **outside the repo**, ideally on separate physical disks. | The archiver refuses to run. |
| `AKASHIC_EPHEMERAL_ARCHIVE_ROOTS` | Where `scripts/ops/archive_ephemeral.py` archives bus exports and state. | The archiver refuses to run. |
| `AKASHIC_SEARCH_ROOTS` | Folders the file search walks when Everything isn't installed. | Windows: `%LOCALAPPDATA%`, `%APPDATA%`, `%USERPROFILE%`, Program Files. Elsewhere: `~/.local`, `~/bin`, `/usr/local`, `/opt`, `/Applications`, then `~`. |
| `ES_EXE` | Path to Everything's `es.exe` (Windows). | Found on `PATH` or in the standard install folders. |
| `AKASHIC_CHECKOUT_<WORLD>` | A world's checkout (`PROD`, `BETA`, `ALPHA`) when it isn't a sibling folder. | Derived from the repo root. |
| `AI_SETUP` | Overrides where instance data lives (see `core/paths.py`). | Data lives in the repo. |

Example (Linux, archives on two mounted disks):

```bash
export AKASHIC_TRANSCRIPT_ARCHIVE_ROOTS="/mnt/disk1/aurora/transcripts:/mnt/disk2/aurora/transcripts"
```

### Windows: symlinks for the skills folder

`.claude/skills` is a git symlink to `.agents/skills` (one source for Claude Code and Codex
skills). Without symlink support git writes it as a one-line text file and Claude Code loads no
skills. Enable Developer Mode, then run `git config core.symlinks true` and
`git checkout -- .claude/skills`.

### Keeping the original Windows machine (`E:\AI-Setup`) working

These variables replaced literals that were written for that machine. After it pulls the
2026-10-01 portability commits, do the following there, or its backups stop.

**Required. Without these, both archivers exit with code 2 and copy nothing.** Set them as
persistent *user* variables. Scheduled tasks only see the new values after you sign out and back
in, or reboot.

```powershell
setx AKASHIC_TRANSCRIPT_ARCHIVE_ROOTS "E:\Akashic Aurora\transcripts\rolling;F:\Akashic Aurora\transcripts\rolling"
setx AKASHIC_EPHEMERAL_ARCHIVE_ROOTS  "E:\Akashic Aurora\ephemeral;F:\Akashic Aurora\ephemeral"
```

The transcript index (`core/eye/index.py`) reads the transcript archive through the same
variable. If the variable is unset, the index sees no archive.

**Only needed to keep the old file-search coverage.** Without Everything, the fallback walk used
to include `C:\Tools` and `C:\ffmpeg`, and it looked for `es.exe` in `C:\Tools\Everything`. The
new defaults leave all three out. Setting `AKASHIC_SEARCH_ROOTS` replaces the default list rather
than adding to it, so list every folder you want walked:

```powershell
setx AKASHIC_SEARCH_ROOTS "%LOCALAPPDATA%;%APPDATA%;%USERPROFILE%;C:\Program Files;C:\Program Files (x86);C:\Tools;C:\ffmpeg"
setx ES_EXE "C:\Tools\Everything\es.exe"   # only if es.exe lives there and is not on PATH
```

**Check these after pulling:**

- **Claude Code hooks** (`.claude/settings.json`). The trace, post-tool-use and stop hooks used to
  run `pyw <script>`. They now run a bash-syntax `uvw`/`uv run -p 3.12 --gui-script` command.
  That needs `uv` on `PATH` (`uvw.exe` ships with uv on Windows) and a shell that understands
  `$(...)` and `VAR=value cmd`. Run one session and confirm the trace hook still writes. If it
  doesn't, point the three commands back at `pyw` in a machine-local
  `.claude/settings.local.json`.
- **Codex identity pointer** (`.codex/config.toml`). `AKASHIC_IDENTITY_POINTER` is now
  repo-relative. Check that Sunshine's boot still finds the identity history file. If it
  doesn't, set it back to the absolute `E:/AI-Setup/...` path in a local override.
- **Re-running `scripts/install_sunshine_discord_tasks.ps1`**. `-PythonExe` now defaults to the
  first `python.exe` on `PATH`, not `C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe`.
  Tasks that are already registered keep the path they were registered with. If you re-install and a
  different Python comes first on `PATH`, pass `-PythonExe` explicitly.
- **MCP templates** (`scripts/static/mcp/*.json`). These now contain `/abs/path/to/...`
  placeholders and use `uv`. The configs already installed on the machine are unchanged. If you
  copy a template again, fill in `E:\\AI-Setup`.

**Nothing to do:** `E:\AI-Setup-Beta` and `E:\AI-Setup-Alpha` are still found as siblings of the
checkout. The repo and data roots, and the recall state directory (`%TEMP%`), resolve to the same
places as before.

## 9. Troubleshooting

- **`python` not found (Windows):** use `py`, not `python`.
- **Which Redis am I on?** `py -m core.foundation.embedded_redis --status` (`embedded`, `redis`, or `down`).
  The embedded server logs to `state/redis-embedded/<port>.log`.
- **A command erred:** it prints `ERROR: …` with a one-line reason and a usage example, and exits non-zero.
- **Back up / restore knowledge:** `py scripts/ops/snapshot_knowledge.py snapshot` (data is intentionally not in git).

## License

Apache License 2.0 — see [`LICENSE`](../LICENSE) and [`NOTICE`](../NOTICE).
