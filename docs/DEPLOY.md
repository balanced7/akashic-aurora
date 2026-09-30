# Deploying Akashic Aurora

Status: current  (2026-07-09, P4: Living ops doc)

How to stand up Akashic Aurora on your own machine. It's deliberately easy: the **core runs on the
Python standard library alone** and degrades gracefully when optional infrastructure (Redis) is absent.

> **Windows vs. macOS/Linux:** examples use `py` (the Windows launcher). On macOS/Linux use `python3`
> everywhere instead. Everything else is identical.

---

## 1. Requirements

- **Python 3.11+** (developed on 3.11.9).
- **git**.
- *Optional:* **Redis** — only for cross-process / multi-agent sharing and speed. Without it the system
  uses local files automatically.
- *Optional:* **Claude Code** (or Cursor) — if you want the agent-facing features (recall-at-action, the
  coordination guards).

No third-party Python packages are required for a first run.

## 2. Quick start

```bash
git clone https://github.com/balanced7/akashic-aurora.git
cd akashic-aurora

# (optional but recommended) an isolated environment
py -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate

# (optional) install Redis client + pytest; the core works without this
py -m pip install -r requirements.txt
```

## 3. Verify the install

```bash
py bootstrap.py --agent-init     # prints JSON: the init command, the python cmd, Redis status, lesson count
py -m pytest -q                  # the full quality gate (needs pytest)
py scripts/checkers/check_boundaries.py   # architecture guardrail (should exit 0)
```

If `bootstrap.py --agent-init` prints a JSON blob and `check_boundaries` says PASS, you're up.

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

## 5. Redis (optional)

Redis unlocks cross-process sharing (multiple agents) and is faster than the file fallback. The system
probes its configured endpoint at startup and **silently falls back to local files** if none is reachable
— so this step is entirely optional.

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

## 9. Troubleshooting

- **`python` not found (Windows):** use `py`, not `python`.
- **Redis warnings / "backend: File":** expected when no Redis is reachable — the system is using files. Harmless.
- **A command erred:** it prints `ERROR: …` with a one-line reason and a usage example, and exits non-zero.
- **Back up / restore knowledge:** `py scripts/ops/snapshot_knowledge.py snapshot` (data is intentionally not in git).

## License

Apache License 2.0 — see [`LICENSE`](../LICENSE) and [`NOTICE`](../NOTICE).
