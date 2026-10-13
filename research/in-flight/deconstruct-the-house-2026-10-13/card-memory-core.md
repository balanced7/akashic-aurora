# Teardown card: THE MEMORY CORE (Store + Ledger, the Redis substrate, backups and the mirror)

Date: 2026-10-13. Seat: claude (Vandor), read-only on the house. Method: `teardown-card.md` (this folder) plus
loop altitude from `docs/pillar-analysis-method.md`. Every claim carries a label: **[observed]** with a pointer,
**[inferred]** naming what it rests on, or **[unknown]** naming where I stopped looking.

Scope read: `core/foundation/` (store.py, ledger.py, sqlite_store.py, redis_connection.py, filelock.py,
durable_reconcile.py), `store/docs/` (the atom ledger), `session_logs/` (the live files), the Redis container on
16379 (read-only INFO / CONFIG GET / SCAN only), `scripts/mirror.py`, `scripts/snapshot.py`,
`scripts/ops/snapshot_knowledge.py`, `scripts/ops/archive_ephemeral.py`, `scripts/checkers/check_dual_authority.py`,
`docs/BACKUP_AND_RECOVERY.md`, `docs/RECOVERY.md`, `docs/ARCHITECTURE.md`, `docs/PORTS.md`. Nothing was written to
the house except this file. No Redis write, no git write, no seat touched.

---

## The picture in one paragraph (hardware version)

Think of the memory core as a computer's memory hierarchy. **Redis is the DRAM**: fast, shared by every agent, but it
only saves itself to disk by taking a full photograph every few minutes (no running journal). **SQLite is the SSD**:
slower, but it keeps a write-ahead journal, so a power cut cannot tear it. Every write goes to **both** (like a
write-through cache), and reads come from the fast one. **The Ledger** is the flight recorder: an append-only tape of
"what happened, in order". Some of its tapes are deliberately looped, like a dashcam that overwrites the oldest
footage. **Backups** come in three kinds: full disk images on the same drive (snapshots), a nightly courier to two
other folders on E: and F: (archives), and a shipping dock to GitHub (the mirror, which ships the blueprints and the
library's atom ledger, not the live memory).

**The thesis in one sentence:** the house writes everything twice and checks its copies carefully, but the alarms
that say "the copies have drifted apart" are ringing in rooms nobody walks into. Measured today: the nightly archive
has reported failure on 39 of its last 40 runs, the twin-drift checker reports a 5.4-day tear and has no caller, and
23 lessons plus 64 decision records exist only in Redis, the one copy with no journal.

---

## Row 1: Purpose

- **What it is for:** to answer two questions for every agent in the fleet, durably and fast. "What IS the value of
  X?" (the Store) and "What HAPPENED, in order?" (the Ledger). **[observed]** `core/foundation/__init__.py:13-16`,
  `core/foundation/ledger.py:6-18`, `docs/ARCHITECTURE.md:67-78`.
- **For whom:** every seat (claude, deepseek, kimi, sol, codex, the runners, the MCP door, the hooks that fire on
  every tool call), plus Daniel as the human who gates destructive recovery. **[observed]** the lesson store builds on
  it (`core/learning/learning_store.py:48,306`); the recall hooks write to Ledger streams `recall:surface` and
  `recall:outcome` (`core/recall/at_action.py:237-249`).
- **The outcome that makes it worth keeping:** a lesson learned by one agent at 3 a.m. is still there, intact, for a
  different agent next week, even if Redis died, the power was cut, or a careless command flushed the database. That
  requires the store never to lie about what it holds. **[inferred]** from the guard comments that name "confidently wrong" as the failure genus this layer exists
  to remove (`core/foundation/store.py:1201-1206`, `scripts/checkers/check_dual_authority.py:14-16`).

## Row 2: Observables (measured from outside, today, without trusting the system's self-description)

| What | Measured value | How | Label |
|---|---|---|---|
| Live durable tier | SQLite, selected by `AKASHIC_STORE_BACKEND=sqlite` set in the **User** environment only | PowerShell `[Environment]::GetEnvironmentVariable(...,'User')` | observed |
| Who else sets that switch | nobody: no launcher, script, `.ps1`, scheduled task or `.mcp.json` names it | Grep across `*.py *.ps1 *.json *.cmd *.bat *.xml` (excluding tests, research, backups, worktrees) | observed |
| Redis | v7.4.8, up 4 days, `appendonly no`, `save 3600 1 300 100 60 10000`, last photo 82 s before the read, 2,274 changes pending | `INFO persistence`, `CONFIG GET` | observed |
| Redis size | db 0: 118,258 keys (38,196 with an expiry), 201 MB, `maxmemory 0`, `noeviction`; db 13: 1,229 keys | `INFO keyspace/memory` | observed |
| Redis growth | 19,850 live keys on 2026-08-14 (comment) to 118,282 today, about 6x in two months; biggest families `events:raw` 49,045 and `bifrost:idalias` 45,733 | comment at `core/foundation/redis_connection.py:75-76`; SCAN family count | observed |
| SQLite size | `store_state.db` 82 MB + 4.1 MB `-wal`, 59,006 distinct keys | `ls`, read-only `mode=ro` count | observed |
| JSON twin | `store_state.json` 11.9 MB, last written 2026-10-08 00:36, holds only 218 lessons (SQLite holds 1,602) | `ls`, read-only JSON parse | observed |
| Redis vs SQLite, durable families | lessons: 1,625 vs 1,602 (23 Redis-only, 0 SQLite-only); decisions: 1,175 vs 1,111 (64 Redis-only); story beats: 4,663 vs 4,656 (7 Redis-only); none of them carry an expiry | read-only set difference | observed |
| Ledger files | 756 stream files in `session_logs/ledger/`, 115,307 lines, 0 unparseable | `ls`, JSON parse of every line | observed |
| Atom ledger | `store/docs/*.jsonl`, 1,386 lines, 0 unparseable; 8 new versions uncommitted (+8 / -0), last committed 2026-10-07 | parse, `git diff --numstat` | observed |
| Knowledge snapshots | 20 kept (the cap), newest **2026-09-24**, 19 days old; no scheduled task takes them | `ls backups/snapshots`, `Get-ScheduledTask` | observed |
| Nightly archive | `ok: false` on 39 of the last 40 runs (2026-09-06 to 2026-10-12); the task scheduler shows result 1 | receipts in `state/archive/receipts-ephemeral/` | observed |
| Twin-drift checker | `DIVERGENT-DUAL`: JSON froze 5.4 days ago while the .db moved 0.0 h ago; exit 1 | `py -m scripts.checkers.check_dual_authority` | observed |
| Unpushed code | 76 commits ahead of `origin/master` (origin last at 2026-10-07 by the local tracking ref) | `git rev-list --count` | observed |
| House self-report | `backend: Redis localhost:16379 (+ SQLite mirror)`, learnings 1,866, agent memory 1,175 | `py agent_cli.py status` | observed |

## Row 3: Mechanism (how inputs become what we observe)

**The fail-fast door.** Before any Redis client is built, a raw socket probe with a 0.5 s timeout checks the port,
because on Windows a down Redis used to stall every module for about 48 seconds. Results are cached for 5 seconds.
The port is chosen per checkout (prod 16379, beta 16380, alpha 16381), and an environment override that points one
world at another world's Redis is refused, loudly. **[observed]** `core/foundation/redis_connection.py:6-21,32-37,73-127,149-185`.
The client sends an application-level PING every 30 s on idle connections, because Docker/WSL's relay can keep a dead
connection looking alive. **[observed]** same file `:237-250`.

**Store write path (HybridStore).** Every write goes first to the durable tier, then best-effort to Redis; a Redis
failure is logged as a warning and swallowed. **[observed]** `core/foundation/store.py:876-884`. The durable tier is
chosen by `_file_tier()`: SQLite when `AKASHIC_STORE_BACKEND=sqlite`, otherwise the old JSON FileStore.
**[observed]** `store.py:1198-1232`.

**Store read path.** Reads go to Redis if Redis was reachable **when the store was built**, else to the durable tier.
**[observed]** `store.py:872-874`, `:281-282` (availability is just "a client object exists"). Two consequences,
both **[inferred]** from that code: a process that started while Redis was down stays on the durable tier for its
whole life (its writes never reach Redis until the next boot heal); a process whose Redis dies mid-life keeps sending
reads to Redis and gets exceptions, because there is no fallback on error.

**Compare-and-set (lost-update guard).** Redis does it atomically with a Lua script; on success the value is copied
to the durable tier. **[observed]** `store.py:290-296,895-905`.

**SQLite tier.** WAL mode, `synchronous=NORMAL`, 10 s busy timeout; writes serialise inside the engine across
processes, which is why it replaced FileStore (which lost 295 of 450 writes in a 3-process probe). **[observed]**
`core/foundation/sqlite_store.py:1-20,146-160`. If the connection cannot open, every write returns False without a
log line. **[observed]** `sqlite_store.py:156-160,323-326`. When the SQLite store is **closed**, it exports itself to
the JSON twin as a rollback escrow. **[observed]** `sqlite_store.py:132-136,165-178,245-276`. No production code
path calls `close()` on the canonical store **[observed, bounded]** (grep of `core/ scripts/ agent/ context/` for
`.close()` on store objects finds only the migration tool), so the escrow refreshes only by accident.

**Boot heal.** At boot, `heal_report()` compares key sets. Keys missing in Redis are backfilled from the durable tier;
keys present only in Redis are classified as durable-family drift (calm), ephemeral by design (quiet), or unknown
(loud). Lists that Redis already holds are never overwritten, because that once demoted a 485-lesson index to a
16-lesson fossil. **[observed]** `store.py:971-1126`, scar comment `:995-1011`. The heal only flows one way: it never
copies Redis-only keys down into the durable tier. **[observed]** `store.py:1035-1040`.

**Ledger.** `emit()` appends one JSON line under an OS-arbitrated lock (a sidecar `.lock` file; the kernel releases
it if the holder dies), reading only the file's tail to find the next id. This replaced a whole-file rewrite that lost
410 of 18,170 recall outcomes (2.3%). **[observed]** `core/foundation/ledger.py:190-205,238-267`,
`core/foundation/filelock.py:1-18`, drill `state/drills/2026-09-24-fileledger-append-under-lock.md` (exists).
Streams with a `maxlen` are trimmed once they run 10% past the cap, by rewriting the file to the newest `maxlen` rows.
**[observed]** `ledger.py:318-340`. Caps that matter: `recall:outcome` 20,000, `recall:surface` 6,000, per-agent
event streams 10,000, the main firehose `events:raw` 100,000. **[observed]** `core/recall/at_action.py:238,249`,
`core/events/event_log.py:44-45`. HybridLedger writes the file always and Redis when up, and returns **Redis's** id
when Redis is up. **[observed]** `ledger.py:414-427`. File reads parse the whole file on every `consume()`.
**[observed]** `ledger.py:357-378,222-236`.

**The atom ledger (`store/docs/`).** Each library document version is one appended JSON line per type file; Store keys
hold the fast current state; `rebuild()` restores the Store from the JSONL, so the file is the recovery truth and git
is its history. **[observed]** `core/library/atoms.py:1-13,117-122`. Appends use a plain `open("a")` with no
cross-process lock. **[observed]** `atoms.py:121`. Git is its only off-machine copy. **[observed]** `.gitignore:77-79`;
`archive_ephemeral.py:62-67` does not list `store/docs`.

**Backups, three kinds.**
1. *Knowledge snapshots* (`scripts/ops/snapshot_knowledge.py`): a full type-aware dump of Redis db 0, a WAL-correct
   SQLite copy through the online backup API, the JSON twin, `learnings.jsonl` and `chronicles/`, into
   `backups/snapshots/<stamp>/`, keeping the last 20. **[observed]** `:38-43,46-64,225-254`. It does **not** copy
   `session_logs/ledger/`. **[observed]** `:236-246`. Restore flushes Redis db 0 and refuses prod unless
   `AKASHIC_RESTORE_PROD=yes-flush-production` is set, because a drill once flushed prod by accident.
   **[observed]** `:86-145`. Manual only. **[observed]** no scheduled task (Row 2).
2. *Nightly archives* (`archive_ephemeral.py`, 12:05 daily, and `archive_transcripts.py`, 12:00 daily): additive-only
   copies to `E:\Akashic Aurora\ephemeral` and `F:\Akashic Aurora\ephemeral`, refusing any source that got smaller
   ("append-only means smaller is corruption"), with a dated receipt each run. From `session_logs/` it takes
   **only `.jsonl` files**. **[observed]** `archive_ephemeral.py:62-68`, `docs/BACKUP_AND_RECOVERY.md:109-118`.
   It also exports the Redis bus streams incrementally to `state/bus-export/` first. **[observed]** `:29-31`.
3. *The mirror* (`scripts/mirror.py`): **not a backup.** It is the publish door that commits named paths and pushes to
   the public GitHub repo, guarded by seat checks, an explicit `--push --yes`, and an authorship check. It counts and
   inspects nothing. **[observed]** `mirror.py:1-47`. Its publish-seat list is advisory for any seat that also has a
   shell. **[observed]** `mirror.py:58-73`.

`scripts/snapshot.py` is a fourth thing with a confusing name: it saves the Bifrost **session** (which agents are
running) for resume, not the memory. **[observed]** `scripts/snapshot.py:1,10`.

## Row 4: First principles (each tested: what evidence or law does it rest on?)

| # | Principle | Rests on | Verdict |
|---|---|---|---|
| F1 | Two questions need two primitives: state-by-key and events-in-order. | The classic store + journal pairing; Redis itself models them differently (hash vs stream). `ledger.py:6-15` | **Real.** A definitional split, backed by the backends' own data models. |
| F2 | A durable write must survive a crash mid-write. | SQLite's WAL protocol; the measured 65.6% FileStore loss (`sqlite_store.py:6-10`) | **Real, and now met** for the Store's SQLite tier and for Ledger appends (one line under lock). |
| F3 | Cross-process correctness needs a lock the operating system arbitrates, not one inside one interpreter. | Kernel releases a dead holder's lock (`filelock.py:14-17`); the 2.3% ledger loss and the 65.6% store loss both came from in-process locks | **Real.** Evidence is two measured incidents. |
| F4 | "Redis down" must fail in milliseconds, not 48 seconds. | Windows TCP SYN retransmission behaviour, measured (`redis_connection.py:6-12`) | **Real.** |
| F5 | "File is the source of truth." | Stated at `store.py:954,975,1050` | **FALSE FIRST PRINCIPLE (trap 1).** The code's own scar comment says the premise was false for the lesson corpus (`store.py:997-1003`); `durable_reconcile.py:4-8` measured Redis 540 vs SQLite 455 vs JSON 23 lessons; today Redis holds 23 lessons, 64 decisions and 7 beats the SQLite tier does not. Authority is per-family, not per-backend, and the house already knows this in `durable_reconcile.py`. |
| F6 | "The Ledger is append-only." | `ledger.py:16-18` ("a durable, ordered, replayable record") | **Half true (trap 1).** Lines are only ever appended, but capped streams are trimmed by rewriting the file. The nightly archive takes the first half as an axiom ("smaller is corruption") and the second half breaks it every day (Row 7). |
| F7 | "Hybrid degrades gracefully, no hang when Redis is down." | `docs/ARCHITECTURE.md:76` | **True at start-up only.** Availability is decided once at construction (`store.py:281-282,872-874`); mid-life loss of Redis raises on reads. |
| F8 | A backup is only real once a restore has been rehearsed, with a dated receipt. | House law that an undrilled recovery path is "presumed broken" (`docs/library/report/20260905_the-wake-doctrine-reliable-seat-wake-fro_4589be.md:43,68`); the 2026-08-11 transcript incident (`BACKUP_AND_RECOVERY.md:12-18`) | **Operator's value, well evidenced.** The house holds it, but its knowledge restore has no receipt in `state/drills/` (Row 8). |
| F9 | Copies on the same disk are a copy, not a backup (three copies, two media, one off-site). | The house's own words at `BACKUP_AND_RECOVERY.md:180-181`; the transcript archive's choice of C:, E:, F: as "three different physical disks" (`:99-101`) | **Real, industry-standard,** and applied to transcripts and bus traffic but not to the SQLite store or the snapshots (Row 7). |
| F10 | Redis is single-threaded per command, so each command is atomic. | Redis's documented execution model; `cas()` relies on it (`store.py:290-296`) | **Real** (external law, not re-measured here). |

## Row 5: Capabilities (what you must HAVE to build or run it)

- **Software:** Redis 7 in a Docker container on WSL, published on host port 16379 (`docs/PORTS.md:37`); redis-py;
  Python 3.11; SQLite (standard library) in WAL mode; Windows file locking (`msvcrt`). **[observed]**
- **Storage:** disk E: (repo, SQLite store, ledger, snapshots), disk F: (second archive copy), C: (transcript source),
  the Docker volume for Redis's photographs (location **[unknown]**: I did not inspect Docker). **[observed]** for E:/F:
  from `archive_ephemeral.py:56-59`.
- **Scheduling:** Windows Task Scheduler for the archives (12:00 transcripts, 12:05 ephemeral, Sunday verify).
  **[observed]** `Get-ScheduledTask`.
- **Identity and gates:** `AKASHIC_AGENT_ID` for seat attribution; the world marker for port selection; Daniel's
  consent string for a prod restore; Daniel's word for the default flip and the JSON retirement. **[observed]**
  `snapshot_knowledge.py:114-145`, `mirror.py:93-147`, T118 notes inside the 2026-07-28 snapshot.
- **Off-machine:** GitHub (`balanced7/akashic-aurora`, public) for code and the atom ledger. **[observed]** `mirror.py:2-6`.
- **Skill:** knowing which family is authoritative where (the roster in `durable_reconcile.py`), and knowing that a WAL
  database must be copied with the backup API, never a file copy. **[observed]** `sqlite_store.py:39-45`.

## Row 6: Required steps (rebuild it from nothing; what blocks what)

1. Fail-fast connector and world-aware port resolution. *Blocks everything:* without it every module stalls 48 s when
   Redis is down, and a twin can write into prod.
2. The Store contract plus a crash-safe, cross-process durable tier (SQLite WAL). *Blocks 3.*
3. Redis tier plus the Hybrid dual-write. *Blocks 5.*
4. The Ledger contract plus an append-under-OS-lock file tier, then the Redis stream tier. Independent of 2-3.
5. Boot heal (drift check, backfill Redis from durable, classify Redis-only keys). *Needs 2 and 3.*
6. Per-family authority roster and reconcile, then migration with two-way verify. *Needs 5; blocks any backend flip.*
7. **Every writer on the same durable tier** (the switch set in every launcher, or made the default). *Needs 6.*
   **This is where the house is today: step 7 is incomplete** (Row 7, F-B).
8. WAL-correct snapshots on a schedule, copied to a second disk. *Needs 7, or you back up a split brain.*
9. Off-disk archives with receipts. Built.
10. **A reader for every receipt and checker** (doctor line, staleness budget). Missing.
11. **A restore drill into a twin, with a dated receipt.** Missing. Until it exists, 8 is a hypothesis.

**Critical path:** 7, then 8, then 11. Steps 10 and 11 are the ones that turn "we built it" into "we know it works".

## Row 7: Invariants and failure modes

**Invariants (what must always hold):**
- I1. Every durable-family key in Redis also exists in the durable tier. **Broken today** (23 lessons, 64 decisions,
  7 beats). **[observed]**
- I2. Ledger ids within a stream are contiguous and every line parses. **Holds** (115,307 lines, 0 unparseable).
  **[observed]**
- I3. Only one durable tier is live at a time, or the twins move together. **Broken** (JSON tear 5.4 days, and a
  FileStore-tier writer exists, see F-B). **[observed]**
- I4. The latest restorable snapshot is recent and lives on another disk. **Broken** (19 days old, same disk E:).
  **[observed]**
- I5. A destructive restore against prod needs Daniel's explicit consent. **Holds** by code. **[observed]**
  `snapshot_knowledge.py:132-145`.

**Failure modes found today (most severe first):**

- **F-A. Redis is the only home of some durable records, and Redis keeps no journal.** 23 lessons (including ones
  stamped 2026-10-09) and 64 decision records exist only in Redis, without expiry. **[observed]** Redis saves a
  photograph every 5 minutes under current write rates, so an unclean stop loses up to about 5 minutes **[inferred]**
  from the `save` policy and 2,274 changes in 82 s; a lost Docker volume loses those 94 records (23 + 64 + 7) outright, and the newest
  snapshot (2026-09-24) predates the October ones **[inferred]** from their stamps. *From outside it looks like:*
  nothing, until the day Redis is rebuilt and recall quietly forgets.
- **F-B. Split brain across three durable copies.** 21 of the 23 Redis-only lessons **are** in the JSON twin.
  **[observed]** So at least one writer runs on the old FileStore tier (Redis + JSON, never SQLite). **[inferred]**
  from that overlap plus the fact that only the User environment carries the switch. The JSON's last write
  (2026-10-08) holds 218 lessons, so it was a FileStore process flushing its own partial view, not SQLite's close-time
  echo (which would carry about 1,600). **[inferred]** *From outside:* `status` says "Redis + SQLite mirror" and the
  numbers look healthy (trap 5, Goodhart: it reports the configuration, not the content).
- **F-C. The archive's daily alarm is a false alarm that has trained everyone to ignore it.** The FileLedger trims
  capped streams by rewriting them smaller; the archive's law calls a smaller source corruption and refuses it. Result:
  `ok: false` on 39 of 40 nights, and the archived copies of `recall_outcome`, `recall_surface` and
  `events_claude_raw` froze at their largest size. **[observed]** receipts; row counts sit exactly in the trim band
  (Row 8, P1). No data is actually lost, because the Redis copy of the same streams is exported append-only to
  `state/bus-export/` (56 MB for `recall_outcome`, versus 15 MB in the trimmed file). **[observed]** `ls`. This is
  **trap 3, reductionism**: each part is correct alone (trimming bounds disk; the shrink law caught a real bug on
  2026-08-11, a basename collision between per-agent wire shards, `scripts/ops/archive_transcripts.py:133-138`,
  commit `46016a11`); the failure lives in the pairing. The cost is real anyway: a true shrink, the one the law exists for,
  would now be invisible in a receipt that is always red. **[inferred]**
- **F-D. The drift checker cannot run where it is documented, and nothing calls it.** `py scripts/checkers/check_dual_authority.py`
  crashes with `ModuleNotFoundError: No module named 'core'` (same path bug fixed in `scripts/snapshot.py` on
  2026-07-31). Run as a module it works and reports the 5.4-day tear. No code calls it. **[observed]** both runs; grep.
- **F-E. The reconcile tool would heal the retired twin.** `durable_reconcile.py` hard-codes `FileStore(None)`
  (the JSON) as the durable side, so after the SQLite flip an `--apply` would copy Redis-only lessons into the file
  SQLite never reads. **[observed]** `core/foundation/durable_reconcile.py:297-303`. Same genus as T118 D5, which
  fixed exactly this in `HybridStore.create` (`store.py:860-863`); the house's own lesson
  `backend_selector_must_cover_wrapped_factory_branches_2026_07_28` names it. A latent twin sits in the back-compat
  path at `core/learning/learning_store.py:300-304` (no production caller found, bounded grep).
- **F-F. Snapshots are manual, same-disk, and never restore-drilled.** Newest 2026-09-24; all on E:; no restore
  receipt in `state/drills/`. A disabled "Redis Backup" task (last run 2026-05-05, error 9009) still points at
  `E:\AI-Setup\redis_backup.py`, which no longer exists. **[observed]** The doc's "Verified: deleting a lesson then
  restore brings it back exactly" carries no date or receipt (`BACKUP_AND_RECOVERY.md:69-70`), and the restore code
  has since changed (SQLite branch added). **[observed]** (trap 4: the map is not the territory).
- **F-G. The documented coverage is wider than the wiring.** The backup doc says the archive covers `session_logs/`
  "learnings.jsonl + store state" (`BACKUP_AND_RECOVERY.md:153`); the code takes `.jsonl` only (`archive_ephemeral.py:66`),
  so the 82 MB SQLite store never leaves E: except inside the manual snapshots. Skipping it is *probably right* (a
  file copy of a WAL database is the exact hazard `sqlite_store.py:39-45` warns about), but then something else must
  carry it off-disk, and nothing does. **[observed]** (trap 4).
- **F-H. Mid-life Redis loss turns reads into errors and cursors into replays.** No read fallback after construction
  (F7). HybridLedger hands consumers Redis ids; if a consumer falls back to the file tier, a Redis id fails `int()`
  and becomes cursor 0, replaying the whole stream; the docstring asks consumers to dedupe. And file-tier `consume()`
  parses the whole file per call (35 MB for `events_raw`). **[inferred]** from `store.py:872-887`,
  `ledger.py:43-46,367-378`. Not tested: testing it means stopping Redis.
- **F-I. Smaller items.** Atom appends have no cross-process lock and an average report atom is about 14 KB (larger
  than one write buffer), so two concurrent mints could interleave; 0 torn lines so far. **[inferred]** risk,
  **[observed]** clean today. `scripts/snapshot.py` tells the operator to resume with `py scripts/snapshot.py --resume`,
  which would save a new session snapshot labelled "--resume" (the real door is `py agent_cli.py session --resume`).
  **[observed]** `snapshot.py:9-10,15`, `core/comm/session_state.py:12,37,85`. Redis db 13 holds 1,229 keys that no
  doc names (`docs/PORTS.md` lists db 0 and db 15 only). **[observed]**

### Loop altitude (the value chain, and whether the signal flows back)

| Link | Built? | Does the signal flow back? |
|---|---|---|
| 1. Write: agent writes a lesson / event | yes | n/a |
| 2. Dual-write: durable tier + Redis | yes | **Partly.** A FileStore-tier writer bypasses SQLite (F-B); nothing notices per write. |
| 3. Drift check at boot (`heal_report`) | yes | **Closed one way.** Redis-behind is backfilled. Redis-ahead is printed as "calm, investigate only if growing" and never actuated, by design (Chesterton: the list-clobber scar). Nobody watches whether it grows. |
| 4. Twin-drift checker | built | **Open.** Detects a 5.4-day tear; no caller; standalone run crashes (F-D). |
| 5. Snapshot | built | **Open.** No schedule, no age budget; 19 days stale. |
| 6. Off-disk archive | built, runs nightly | **Open.** Receipt red 39/40 nights; no reader outside the archive scripts (bounded grep of `core/`, `scripts/`, `agent_cli.py`). |
| 7. Restore | built, guarded | **Never closed.** No drill receipt. |
| 8. Operator / doctor | exists | Does not read links 4, 5, 6 or 7. |

**Diagnosis:** a classic designed-open loop (`docs/pillar-analysis-method.md:27-30`): measurement without actuation,
three times over. The pipes are excellent; the alarms have no listener. The house's own lesson already names the cure:
`the_house_reports_what_exists_and_never_what_should_exist_and_does_not` (a staleness budget on things that should
move).

## Row 8: Verification (predictions that could fail, the cheapest test, and what happened)

| # | Prediction (written before the test) | Test | Result |
|---|---|---|---|
| P1 | The three refused ledger files shrink because of `maxlen` trimming, so each holds between its cap and cap + 10%. | `wc -l` on `session_logs/ledger/{recall_outcome,recall_surface,events_claude_raw}.jsonl` | **Held.** 21,522 (band 20,000-22,000); 6,418 (6,000-6,600); 10,552 (10,000-11,000). |
| P2 | The drift checker will flag a tear longer than 24 h. | `py -m scripts.checkers.check_dual_authority` | **Held.** `DIVERGENT-DUAL`, 5.4 days, exit 1. **Surprise:** the documented standalone form crashes (F-D). |
| P3 | Redis still runs without a journal (`appendonly no`); T372 "AOF permanent" has not landed. | `CONFIG GET appendonly`, `INFO persistence` | **Held.** `appendonly no`, `aof_enabled 0`, `save 3600 1 300 100 60 10000`. |
| P4 | The SQLite tier holds every durable-family key that Redis holds. | Read-only set difference (SCAN vs `mode=ro` SQLite) | **FAILED.** 23 lessons, 64 decisions, 7 beats are Redis-only; 0 keys go the other way. |
| P5 | If a FileStore-tier writer caused P4, the Redis-only lessons will be in the JSON twin. | Intersect Redis-only keys with the JSON buckets | **Held.** 21 of 23 lessons are in the JSON. Only 19 of 64 decisions are, so a second path exists (Unknown). |
| P6 | Neither the atom ledger nor the FileLedger has torn lines. | Parse every line | **Held.** 1,386 / 0 and 115,307 / 0. |
| P7 | No scheduled task takes knowledge snapshots. | `Get-ScheduledTask` filtered for Aurora, snapshot, backup | **Held.** None; plus a disabled "Redis Backup" task pointing at a deleted script. |
| P8 | The atom ledger's git diff is additions only. | `git diff --numstat -- store/docs` | **Held.** +8 / -0 across four files. |
| P9 | `status` reports the live Redis + SQLite arrangement. | `py agent_cli.py status` | **Held.** (And it is the Goodhart case: it cannot see P4.) |
| P10 | **Forecast, registered:** the main firehose `events_raw` (53,224 rows, growing about 2,372 a day over the last 14 days) crosses its trim line of 110,000 around **2026-11-06**, and from that night the archive refuses it too. | Recount rows and check the receipt after 2026-11-06 | **Not run** (future). Fails if the write rate changes or the archive rule changes first. |

Read-only throughout. Commands I did **not** run, and why: `durable_reconcile --plan` (builds a FileStore, whose
lazy-expiry path can rewrite the JSON; I confirmed the JSON has 0 expiry entries, so it would probably be safe, but it
is not on the read-only list); any restore or snapshot (they write); anything that stops Redis (needed to test F-H).

---

## Great Sage report

> **Notice.** The memory core has two primitives (Store, Ledger), three tiers (Redis, SQLite, a legacy JSON twin),
> and three backup paths (manual snapshots, nightly archives, the GitHub mirror). Redis runs without a journal
> (`appendonly no`) and holds 118,258 keys, six times its August size. 23 lessons, 64 decision records and 7 story
> beats exist only in Redis; 21 of those lessons also sit in the JSON twin, which froze on 2026-10-08. The SQLite switch
> lives only in the User environment. The nightly archive reported failure on 39 of its last 40 runs, refusing ledger
> files that shrink by design. The twin-drift checker finds a 5.4-day tear, has no caller, and crashes when run as
> documented. The newest knowledge snapshot is 19 days old, on the same disk, and no restore has a dated receipt.
> Ledger and atom files are clean: 116,693 lines, none torn.
>
> **Analysis.** At least one writer still runs on the old JSON tier, so the fleet's memory is split three ways
> (from the 21-of-23 overlap and the env-only switch). Redis has quietly become the most complete copy while being the
> least durable one (from the Redis-only set and the save policy). The archive alarm is a false alarm born of two
> correct rules meeting (trim versus refuse-shrinking), and a permanently red receipt hides the true shrink it exists to
> catch (from the receipts and the trim-band counts). The reconcile tool would heal the wrong file today (from its
> hard-coded FileStore). The common shape: measurement without a reader, three times.
>
> **Unknown.** Which process writes on the JSON tier (I grepped code and configs and read `.mcp.json`; I did not
> inspect live process environments). Where the other 45 Redis-only decisions came from. Whether a restore works
> today (never run). Whether reads crash when Redis dies mid-session (needs Redis stopped). Where Redis's Docker volume
> lives and whether its photographs leave the machine. What owns Redis db 13. When the User switch was set. Whether
> the local `origin/master` ref is current (no fetch).
>
> **Proposal** (smallest first; each part's reason for existing stated before any change to it):
> 1. Fix the checker's import so its documented command runs (two lines, the same fix `snapshot.py` got). It exists to
>    guard the T118 rollback escrow; keep it, make it runnable.
> 2. Give the alarms a reader: one `doctor` row each for archive receipt status, twin-drift, snapshot age and Redis-only
>    durable keys, each with a staleness budget. No data moves.
> 3. Find the JSON-tier writer: have `doctor` (or boot) print each process's durable tier, then set the switch
>    explicitly in every launcher, or take the default flip (Daniel's gate since T118).
> 4. Route `durable_reconcile.py` through `_file_tier()` (the T118 D5 fix, applied to the tool that missed it), then
>    `--plan`, then Daniel's go for `--apply` to bring the 94 Redis-only records (23 lessons, 64 decisions, 7 beats) home to SQLite.
> 5. Teach the archive that capped ledger streams are rolling by design: append by id range, or rely on the
>    `bus-export` copy for those streams. Keep trimming (it bounds disk, and `consume()` reads whole files); keep the
>    refuse-shrinking law (it caught a real bug on 2026-08-11: `scripts/ops/archive_transcripts.py:133-138`, commit
>    `46016a11`). Change only how they meet.
> 6. Decide the JSON twin: wire `close()` so the escrow really refreshes, or retire it formally (Daniel's gate).
> 7. Schedule a WAL-correct snapshot, copy it to F:, and run one restore drill into the Alpha twin with a dated receipt.
>    Delete the dead "Redis Backup" task only after Daniel confirms nothing else should replace it.
> 8. Make Redis's journal permanent (task T372). This is not a runtime switch: `CONFIG SET appendonly yes` does not
>    survive a container restart, because akashic-redis runs with no config file (W258, `docs/WISHLIST.md:1773`).
>    T372 is a container rebuild that moves data (BGSAVE, copy the dump out, recreate with `--appendonly yes` and a
>    proper volume, restore, verify), so it is gated and drilled. More urgent than the backup doc assumed, because
>    its "everything important is dual-written" premise is false today (P4).
> 9. Small fixes: put the atom append under the same file lock the Ledger uses; correct `snapshot.py`'s resume hint;
>    document Redis db 13.
>
> **Verification.** Ten predictions registered. Eight held, one failed (P4: the durable tier is *not* a superset of
> Redis), and one is a forecast for about 2026-11-06 (P10). The failed one is the most important finding on this card.
>
> **Proceed?** NO, not yet: every proposal waits for Daniel. My recommendation is YES on 1, 2 and 3 first (they move
> no data and they would have caught all of this), then 4 and 8 together, because those close the window where 94
> records live only in the copy with no journal.
