# Sweep: who else never got `core/foundation/filelock.py`

2026-10-02, claude/Vandor. Closes the class, so nobody sweeps it again from zero.

## Why this exists

`core/foundation/filelock.py` was born 2026-08-26 from the third instance of one defect:
a whole-file read-modify-write with no cross-process lock, where the loser's write vanishes
silently. `ledger.py` adopted it 2026-09-24 (the DuckDB dive had measured the unlocked version
losing 410 of 18,170 recall outcomes); `remote_relay.py`, `task_ledger.py` and `college.py`
followed.

This morning `cmd_wish` was measured losing **6 of 40** concurrent wishes and got the lock
(`bbdc3584`). The lesson filed straight after —
`when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it` — says: at the moment a shared
primitive lands, grep the tree for the UNFIXED SHAPE, because the sites diagnosed *before* the
primitive existed never get revisited by anyone. This is that sweep, taken on my own advice.

## Method

Scanned 519 `.py` files under `core/`, `scripts/`, `agent/`, `arsenal/`, `agent_cli.py`,
`ai_setup_mcp.py` (excluding `tests/`, worktrees, `__pycache__`). Flagged any function
containing both a whole-file read (`read_text` / `json.load` / `readlines` / `yaml.safe_load`)
and a whole-file write (`write_text` / `json.dump` / `yaml.safe_dump` / `writelines`) with no
lock token (`filelock` / `exclusive(` / `flock` / `msvcrt.locking` / `LOCK_EX`) anywhere in the
body. 24 candidates.

The grep is the cheap half. The verdict needs the question the grep cannot ask: **is this file
written by more than one process at a time, and what is lost when it is?**

## Verdicts

### REAL — fixed (1)

| site | what was measured |
|---|---|
| `agent_cli.py` `cmd_wish_curate` | The SECOND door onto `docs/WISHLIST.md`. A lock excludes only the writers that take it, so for most of today the ledger had one locked door and one open one. Four filings against four curations per round: **writes lost** (prints `folded W##`, exits 0, row overwritten) and **reads torn** (`write_text` truncates before writing, so a peer sees the file without its `## Folded` anchor and refuses with "structure drifted — file by hand" on damage the ledger never had). Pinned `12fd603a`, fixed `aad65801`, mutation-tested. |

### SAFE BY DESIGN — and the reason matters more than the verdict (5)

A sweep that only says "safe" invites the next sweep to redo it. Each of these is safe for a
*specific, durable* reason; if the reason changes, the verdict changes.

- **`agent/harness/dsh_plugin/bridge.py` `cmd_wake_check`** — writes `wm_path + ".tmp"` then
  `os.replace`. Atomic: no torn read is possible. **But note the shape**: a FIXED temp name plus
  `os.replace` is *exactly* what filelock's own docstring describes as the birth defect ("each
  wrote a temp file with the SAME fixed name, and raced os.replace"). What saves it here is that
  the DSH wake timer is a singleton organ, not that the pattern is sound. **If that timer ever
  runs twice concurrently, two writers interleave bytes into one `.tmp` and the watermark
  corrupts.** Cheapest durable fix if it ever doubles: give the temp a pid/uuid suffix.
- **`scripts/githooks/pre_commit.py` `ensure_baseline`** — refuses outright on an unreadable
  baseline ("a corrupt ratchet must not be silently replaced"), so a torn read is loud. A lost
  adoption self-heals at the next commit.
- **`core/recall/at_action.py` `_cached_items`** — not a read-modify-write at all: it is
  read-OR-rebuild-and-overwrite with a derived projection. Concurrent writers each write a
  complete valid file; a torn read raises in `json.load` and falls through to the documented
  stale-fallback.
- **`core/comm/toolbox.py` `edit_file` / `write_file`** — guarded by `_prewrite`, which refuses
  when **another agent holds the advisory path-lock** (C2 coordination). A different and more
  appropriate mechanism than filelock: it arbitrates *intent* between seats, not just bytes.
  Residual, narrow: two writes under the same agent id, or an agent write racing a plain CLI
  process that never claims the advisory lock, still race at byte level.
- **`scripts/githooks/coauthor.py` `ensure_operator_coauthor`** — git serialises commits on
  `.git/index.lock` upstream of the hook. (Observed live during this very sweep: a `git stash
  pop` refused with `Unable to create '.git/index.lock'`. Git handles the class correctly — it
  **refuses loudly** rather than losing the write. Good contrast with the door I just fixed.)

### LOW HARM — real race, fail-soft by design, not worth a lock (4)

All session-scoped (`<session_id>.json`), all wrapped in bare `try/except: pass`, all with
readers that return a default on failure. Within one session these DO race, because parallel
tool calls in one assistant turn fire concurrent hook processes.

- `agent/harness/hooks/claude_posttooluse.py` `_mark_failure_processed` — loses a dedup
  watermark → one duplicate nudge.
- `scripts/hooks/claude_posttooluse.py` `_mark_failure_processed` — **the same function at the
  same line number in a second file.** The twins are already known debt; there is a held patch
  named `unify-diverged-hook-file-twins.red.patch`. Any fix here must land in both or the twins
  drift further.
- `agent/harness/nudge.py` `mark_nudged` — loses a nudge record → the cap of 3 can be exceeded.
- `core/recall/at_action.py` `_set_outcome` — session-local dedup marker only. **Not** the
  outcomes ledger; the durable JSONL is appended elsewhere. Losing one costs a redundant
  FAIL→SUCCESS re-evaluation.

The code states the governing constraint itself: *"a PostToolUse hook must never affect the
action"*. Adding a blocking lock to the hottest path in the house to protect a dedup marker
would trade a cosmetic duplicate for a real stall. Leave them.

### FALSE POSITIVES — single-writer or mis-sliced (14)

`agent_cli.py:cmd_ask`, `arsenal/__main__.py:main` (both mis-sliced by the crude
function-boundary regex — 398 and 338 lines); `core/web/door.py:fetch`;
`scripts/capture_apple_hig.py` ×2; `scripts/checkers/check_rewrite_maps.py:report`;
`scripts/harmonize_knowledge.py:phase_backup`; `scripts/ops/archive_ephemeral.py` ×2;
`scripts/ops/redact.py:apply`; `scripts/rewrite_recover.py:cmd_capture`;
`scripts/season_fan_calibration.py:_finalize_archive`; `scripts/yt_captions.py:fetch`.
Manual one-shots and caches with a single writer by construction.

## One thing found that is NOT this class

`core/recall/at_action.py` assigns `_OUTCOME_DIR` **twice** at module level — line 89
(`os.getenv("AKASHIC_RECALL_STATE_DIR") or _CACHE_DIR`) and line 921
(`os.path.join(_CACHE_DIR, "outcome")`). The second wins.

I nearly reported this as "the env var is silently dead". **It is not** — `_CACHE_DIR` already
honours `AKASHIC_RECALL_STATE_DIR`, so test isolation holds; verified by import. Line 89 is
simply dead, and the only live effect is that `recall_outcomes.jsonl` sits in
`<state>/outcome/` beside the per-session markers rather than at `<state>/`. One latent edge:
`prune_state` deletes anything in that directory older than 7 days, so a ledger that goes
untouched for a week is removed despite `_OUTCOME_MAX_BYTES` implying size-based retention. In
practice it is appended continuously and its mtime never ages. **Not worth a slice; recorded so
the next reader does not re-derive it.**

## What the sweep cost, and what it is worth

One real defect, in the door that records our own friction, found within hours of filing the
lesson that says to look. The grep took a minute; the verdicts took the afternoon. That ratio is
the actual finding: **the shape is cheap to list and expensive to judge**, so the list is worth
keeping — this file is the judgement, so the next primitive's sweep starts from 24 triaged sites
instead of 519 files.
