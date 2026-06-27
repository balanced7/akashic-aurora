# Backup & Recovery

Two independent layers protect the system, because code and data fail differently.

| Layer | Protects | Tool | Recover with |
|---|---|---|---|
| **Git** | the **architecture** (code, docs, curated chronicles) | `git` | `git checkout <ref> -- <path>` |
| **Snapshots** | the **knowledge data** (Store, learnings, chronicles) | `scripts/snapshot_knowledge.py` | `... restore <name>` |

## 1. Code / architecture — Git

The whole layered system (`core/`, `context/`, `agent/`, `agent_cli.py`, `scripts/`,
`tests/`, `docs/`, `chronicles/`) is committed. `.gitignore` keeps out the ~17 GB of
third-party bulk (`ComfyUI-Zluda/`, `dockerized-ai/`, models, venvs) and the volatile
knowledge data (that's the snapshot tool's job).

**If an agent deletes or breaks a code file:**
```
git status                                   # see what changed
git checkout HEAD -- core/foundation/store.py   # restore one file
git checkout HEAD -- .                        # restore everything (DANGER: drops all uncommitted work)
```
Every file from before the refactor is also recoverable from history (`git log`,
`git show <oldcommit>:<path>`).

**Baseline commit:** the post-refactor architecture lives on branch
`architecture-baseline-2026-06-27`. Merge to `master` and push to GitHub
(`origin` = balanced7/ai-setup) for an off-machine copy when ready. NOTE: the `.git`
history still carries large blobs from old commits (~2 GB) — a GitHub push may need a
history cleanup (`git filter-repo`) first; local recovery is unaffected.

## 2. Knowledge / data — snapshots

The live knowledge (Redis db 0 + `session_logs/store_state.json` + `learnings.jsonl`
+ `chronicles/`) is **not** in git. Snapshot it instead:

```
py scripts/snapshot_knowledge.py snapshot ["note"]   # take a timestamped snapshot
py scripts/snapshot_knowledge.py list                # list snapshots (newest first)
py scripts/snapshot_knowledge.py restore <name>      # roll back (auto-snapshots current first)
py scripts/snapshot_knowledge.py verify              # current canonical key count
```

Snapshots are self-contained dirs under `backups/snapshots/<timestamp>/`; the last 20
are kept. **`restore` always snapshots the current state first**, so a restore is itself
reversible. Verified: deleting a lesson then `restore` brings it back exactly.

**Recommended habit:** snapshot before letting an unfamiliar agent write to canonical,
or run it on a schedule. Or have the agent use **trial mode** (`REDIS_DB=15`, see
`AGENTS.md`) so it can't touch canonical at all.

## Quick recovery recipes

| Situation | Fix |
|---|---|
| Agent deleted a code file | `git checkout HEAD -- <path>` |
| Agent corrupted the knowledge store | `py scripts/snapshot_knowledge.py restore <name>` |
| Want a safe sandbox for an agent | set `REDIS_DB=15` (trial mode) |
| Canonical drifted from the 6 baseline lessons | `py scripts/harmonize_knowledge.py rebuild` |
