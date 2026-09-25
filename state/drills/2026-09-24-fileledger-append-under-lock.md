# DRILL RECEIPT — FileLedger appends under a cross-process lock (L0)

**Date:** 2026-09-24, about 22:00 EDT
**Organ:** `core/foundation/ledger.py` FileLedger.emit
**Commits:** e711e4b3 (pins, red), de217307 (fix), and the fence fix that lands with this receipt
**Drilled by:** claude (Vandor), on Daniil's "yes greenlight on l0".
**Result:** PASS on this checkout. It is NOT live in seats that are already running, and not in the worktree
services. See "NOT proven".

## Why

The DuckDB deep dive's fit lane (`research/reviewed/duckdb-lane-fit-2026-09-24.md`) compared
`session_logs/ledger/*.jsonl` with the Redis copies exported to `state/bus-export` for 09-10 to 09-24:

- 410 of 18,170 recall outcomes (2.3%) never reached the file.
- 36 of 1,430 firehose events never reached the file.
- Almost every loss sat within 0.5 s of another write.

The cause was the old `emit()`. It read the whole file, rewrote it through one fixed tmp name, and swapped it in
with `os.replace`. The only guard was a `threading.RLock`, which no other process can see.

## Method and observations

1. **Pins, red first.** `tests/test_ledger_cross_process.py` runs real processes, not threads. Against the old
   code (e711e4b3), 5 of its 6 tests failed:
   - rows lost;
   - duplicate ids;
   - a trim race;
   - a full rewrite on every emit;
   - rows lost while a reader simply held the file open. Windows denied the `os.replace`
     (`[WinError 5] Access is denied`), 5 of 6 new rows vanished, and the only trace was a log line.
2. **Fix (de217307).** Every emit now holds `core.foundation.filelock` for the stream, reads only the file's tail
   to get the next id, and appends one line. Trimming happens occasionally under the same lock, and a failed
   trim is retried later. 12 of 12 tests passed, and 95 neighbouring ledger and event tests passed.
3. **Soak.** 8 processes × 400 emits ran concurrently while a reader opened the file 296 times: 3,200 of 3,200
   rows landed, with 0 duplicate ids, the file in id order, and every returned id unique. Throughput was about
   2,970 emits per second.
4. **Killed lock holder.** A second writer blocked while the holder was alive. After the holder was killed, the
   writer emitted within about 1 second. Windows releases the lock when its holder dies, so nothing can go stale.
5. **Latency on a copy of the real 13.5 MB `recall_outcome.jsonl`, with maxlen 20,000.** Median 0.36 ms per
   emit, p95 0.46 ms, max 0.8 ms. The fit lane measured about 166 ms for the old whole-file rewrite, so this is
   roughly 460 times faster.
6. **The fence finding was fixed and pinned.** See below. 13 of 13 tests pass.

## Fence (DeepSeek, verbatim)

`py agent_cli.py ask`, deepseek-v4-pro, 7144+17796 tok, 271 s:

> 1. BLOCKER `ledger.py:259` with `ledger.py:240` — if `filelock.exclusive(path)` at `ledger.py:243` raises `LockTimeout` before `_tail_state`, `last_id` is still `0`, so emit returns `"0"` for an event that was never appended; this can lose a row and contradicts the comment at `ledger.py:257`.
> 2. OK `ledger.py:243-244` — writers are serialized by the cross-process lock; normal writer/writer interleaving cannot append concurrently.
> 3. OK `ledger.py:247-250` — append is one JSONL line under the lock; a killed writer leaves a torn tail, and the next writer prepends a newline, so lines do not glue together.
> 4. OK `ledger.py:262-295` — `_tail_state` chunk carry logic is correct across chunk boundaries; `pos == 0` is the only case where `pieces[0]` is parsed.
> 5. OK `ledger.py:286-293` — CRLF endings are safe because `raw.strip()` removes trailing `\r` before `json.loads`.
> 6. OK `ledger.py:269-273` — empty or missing file returns `(0, False)`.
> 7. OK `ledger.py:310-330` — trim runs under the same lock, uses a per-pid/tid tmp file, and defers on `os.replace` failure; failure does not raise out of emit.
> 8. OK `ledger.py:349-357` — `consume` does not busy-spin or hang; wait is capped at 1000ms.

**Disposition (claude): finding 1 ACCEPTED.** A caller would take a returned `"0"` as a cursor and replay the
whole stream. Emit now returns:

- the appended id, if the row landed and only the trim failed;
- otherwise the newest id already on disk, read without the lock.

Pinned by `test_a_lock_timeout_returns_the_newest_id_not_zero`.

## NOT proven — read before trusting

1. **Running seats still run the old code.** Python does not reload a module in a running process. Daemons,
   runners, MCP servers and the gateway write the old way until they restart. While old and new writers run
   together, the old writers can still lose rows the old way.
2. **The worktree services are untouched.** SunshineFleet and the Discord production runtime run from the
   `sunshine-discord-split` worktree with their own code and their own `data_root()`. They need this fix
   carried over, a restart, and a decision on where their data lives. Setting `AI_SETUP` would also move their
   **code** root, because `repo_root()` honours it when it points at a repo. That is a production change, so it
   is gated separately.
3. **POSIX locking (fcntl) was not drilled.** It was not exercised on this Windows machine.
4. **Old files are not repaired.** Rows already lost stay lost. The Redis exports in `state/bus-export` still
   hold most of them.
