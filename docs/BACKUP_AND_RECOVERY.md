# Backup & Recovery

Status: current  (2026-07-09, P4: Living ops doc)

Three independent layers protect the system, because code, data and the raw record fail
differently.

| Layer | Protects | Tool | Recover with |
|---|---|---|---|
| **Git** | the **architecture** (code, docs, curated chronicles) | `git` | `git checkout <ref> -- <path>` |
| **Snapshots** | the **knowledge data** (Store, learnings, chronicles) | `scripts/ops/snapshot_knowledge.py` | `... restore <name>` |
| **Transcript archive** | the **raw record** (session JSONL — where the operator's voice lives) | `scripts/ops/archive_transcripts.py` | copy back from `E:`/`F:\Akashic Aurora\transcripts\rolling` |

> **The transcript layer exists because 2026-08-11 proved the first two do not cover it.**
> The harness rotates session transcripts off disk silently. A schema migration in THE EYE
> wiped its index on the belief it was "a projection, rebuildable from source" and destroyed
> events whose source had already rotated away; they were recovered from a Windows shadow
> copy with hours to spare. **Two rules came out of that day and both are load-bearing here:**
> a store is only "rebuildable from source" while the source exists, and *unrecoverable* is a
> claim that needs a search rather than an inference.

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
py scripts/ops/snapshot_knowledge.py snapshot ["note"]   # take a timestamped snapshot
py scripts/ops/snapshot_knowledge.py list                # list snapshots (newest first)
py scripts/ops/snapshot_knowledge.py restore <name>      # roll back (auto-snapshots current first)
py scripts/ops/snapshot_knowledge.py verify              # current canonical key count
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
| Agent corrupted the knowledge store | `py scripts/ops/snapshot_knowledge.py restore <name>` |
| Want a safe sandbox for an agent | set `REDIS_DB=15` (trial mode) |
| Canonical drifted from the 6 baseline lessons | `py scripts/harmonize_knowledge.py rebuild` |
| A session transcript is gone from `~/.claude/projects` | copy it back from `F:\Akashic Aurora\transcripts\rolling` (§4) |
| Transcripts gone AND missing from the archive | **do not conclude they are lost** — `vssadmin list shadows`, then read `\\?\GLOBALROOT\Device\HarddiskVolumeShadowCopyN\Users\...` (no admin needed). Shadow copies are pruned on a rolling schedule, so search the same day. |

## 4. Raw record — the transcript archive

Session transcripts (`~/.claude/projects/*/*.jsonl`) are the one plane neither git nor the
snapshot tool covers, and the harness deletes them on its own schedule without asking.

```
py scripts/ops/archive_transcripts.py            # copy to E: and F:, incremental (~0.02s)
py scripts/ops/archive_transcripts.py --verify   # + SHA256 every archived copy (deep)
py scripts/ops/archive_transcripts.py --status   # what the last run did; copies nothing
```

**Destinations:** `E:\Akashic Aurora\transcripts\rolling` and
`F:\Akashic Aurora\transcripts\rolling` — deliberately OUTSIDE the repo, because these are
unredacted and the repo is public. Source on C:, copies on E: and F: = three different
physical disks.

**Triggers:** a `SessionEnd` hook in `~/.claude/settings.json` (fires when a transcript is
complete) plus scheduled tasks `AkashicAurora-TranscriptArchive-Daily` (12:00, run-when-
available) and `-VerifyWeekly` (Sun 12:30). The hook cannot cover crashes — a safeguards
eject or a driver crash never reaches SessionEnd — which is exactly when the transcript
matters most, so the timer is not redundant with it.

**Three laws**, each earned on 2026-08-11:

1. **Additive-only.** No delete path exists. A mirroring sync would erase the archived copy
   the moment a transcript rotated away — the same disaster, on a schedule, unattended.
   `robocopy /MIR` here would be worse than no backup. Watch the law work: a healthy run
   prints **"82 seen, 94 held."**
2. **Refuse a shrinking source.** Append-only means smaller is corruption, never an update.
   The good copy survives and the run fails loudly.
3. **Be loud.** Dated receipt every run in `state/archive/receipts/`; non-zero exit on any
   refusal, failure, unreachable drive, or unwritable receipt. See `backup_door_never_ran`.

**Known bound:** subagent/workflow transcripts (~361 files) are excluded by default; every
run states the excluded count. `--include-subagents` adds them.

**Restore rehearsal** — do this occasionally rather than trusting the receipts:
```
py scripts/ops/archive_transcripts.py --verify   # proves archive == source, both drives
```
