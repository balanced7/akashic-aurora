---
akashic_id: art_20260924_duckdb-operational-limits_1949a7
akashic_sha: 96643a68a374
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-operational-limits
gist: "# DuckDB deep dive -- honest operational limits and gotchas *2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:00:22"
updated: "2026-09-24T21:00:22"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-operational-limits_1949a7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-operational-limits

# DuckDB deep dive -- honest operational limits and gotchas

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" Agent a254eeeb659eed119 ran 19:45-19:59 local and finished; full answer verbatim. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

## The question (verbatim brief)

Research task: find the HONEST OPERATIONAL LIMITS and real-world gotchas of DuckDB as of September 2026 (current stable is v1.5.5, v2.0-alpha exists). Use WebSearch and WebFetch extensively (load them via ToolSearch with query "select:WebSearch,WebFetch" first). Everything must come with a URL — no priors.

Context that shapes what matters: a Windows 11 desktop, Python 3.11, several long-running agent processes on one machine that would all want to read and write the same database file.

Dig into:

1. MEMORY BEHAVIOUR. What actually happens with larger-than-RAM data? Search the DuckDB docs on memory management / out-of-core / spilling to disk (temp_directory, memory_limit settings). Find GitHub issues and blog posts where people hit "Out of Memory Error" despite the spilling claims. Which operations can NOT spill to disk? (I've heard some aggregate/window/join paths are memory-hungry.) Get the current documented answer plus real complaints.

2. WRITE CONCURRENCY IN PRACTICE. Find GitHub issues / StackOverflow / Reddit threads from people who tried to have multiple processes write to one DuckDB file. What error messages do they get? Search for the exact error text people report (something like "Could not set lock on file" / "Conflicting lock is held"). How do people work around it? Is there a documented "Quack" protocol or CONNECT client/server mode in v1.5.x/v2.0 that changes this, and what's its maturity?

3. LONG-RUNNING PROCESSES holding connections. Any known issues with connections held open for hours/days? Memory growth, file handle leaks, WAL growth, checkpointing behaviour? Search for duckdb WAL checkpoint growth issues, and whether an open write connection blocks other readers.

4. WINDOWS-SPECIFIC issues. Search GitHub issues for DuckDB problems on Windows: file locking differences, path handling, antivirus interactions, temp directory issues, crashes. Note that this machine has Windows Defender DISABLED, so AV interference is less relevant, but report what you find anyway.

5. WHEN IS DUCKDB THE WRONG TOOL? Find credible write-ups (including from DuckDB themselves — they have a docs page or FAQ about this) about workloads DuckDB is bad at: high-frequency small writes, OLTP, many concurrent writers, tiny point lookups, serving as an application backend database.

6. Any notable data-loss, corruption, or crash-recovery reports. Search GitHub issues for duckdb database corruption / "Serialization Error" / recovery after crash.

For each finding: URL, date, who said it, and whether it's the official docs, a maintainer, or an anonymous user. Explicitly list what you could NOT verify. Prefer recent (2025-2026) material and say when a complaint was against an old version that may be fixed.

Return your findings as your final message (no files). Be specific and quote error messages verbatim where you find them.

## The answer (verbatim)

I have comprehensive coverage. Here are the findings.

---

# DuckDB honest operational limits — research as of 2026-09-24

**Version landscape (verified):** v1.5.5 stable, released 2026-07-22 ([announcement](https://duckdb.org/2026/07/22/announcing-duckdb-155), DuckDB team). v1.4.3 is the LTS line ([announcement](https://duckdb.org/2025/12/09/announcing-duckdb-143)). v2.0-alpha "Cyanoptera" released 2026-09-02, targeting **second half of October 2026** ([try-v2.0-alpha](https://duckdb.org/2026/09/02/try-duckdb-20-alpha), DuckDB team).

---

## 1. Memory behaviour — what actually happens

### Documented behaviour (official)

[Memory Management in DuckDB](https://duckdb.org/2024/07/09/memory-management) — **Mark Raasveldt (DuckDB co-creator/maintainer), 2024-07-09**:
- `memory_limit` defaults to **80% of physical RAM**
- `temp_directory` defaults to `<dbfile>.tmp` (persistent mode) or `.tmp` (in-memory mode)
- `max_temp_directory_size` defaults to **90% of remaining disk space**
- Out-of-core is supported for: aggregations with many groups, high-cardinality `DISTINCT`, joins where both sides exceed memory, sorting, window functions

[Limits page](https://duckdb.org/docs/current/operations_manual/limits) (official) contains the load-bearing caveat: memory usage is *"80% of RAM"* and **"This limit only applies to the buffer manager."** Anything outside the buffer manager is uncapped.

The [Out-of-Memory Issues guide](https://duckdb.org/docs/current/guides/performance/oom) states it plainly: *"some of DuckDB's operations circumvent the database's buffer manager and thus they can reserve more memory than allowed by the memory limit."*

### What canNOT spill — the documented answer

[Tuning Workloads](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads) (official, current) is the best source and confirms your suspicion:

- Blocking operators that buffer full input: **GROUP BY, JOIN, ORDER BY, OVER (PARTITION BY / ORDER BY)**
- *"If multiple blocking operators appear in the same query, DuckDB may still throw an out-of-memory exception"*
- **`list()` and `string_agg()` "do not support offloading to disk"**
- **Aggregate functions that use sorting "can cause an out-of-memory exception when run on large datasets"**

[Indexes docs](https://duckdb.org/docs/current/sql/indexes) (official, current): **"ART indexes must currently be able to fit in memory during index creation."** and *"Avoid creating ART indexes if the index does not fit in memory during index creation."* ART indexes are **automatically created for every UNIQUE or PRIMARY KEY column**. This is a live restriction in the current docs, not a historical one.

[Out of Memory Errors troubleshooting](https://duckdb.org/docs/lts/guides/troubleshooting/oom_errors) (official, 1.4 LTS) gives the canonical error shape:
> `Out of Memory Error: failed to pin block of size 256.0 KiB (476.7 MiB/476.8 MiB used)`

Official mitigations: `SET threads = ...` (lower), `SET preserve_insertion_order = false`, `SET memory_limit` to **50–60%** rather than the 80% default *"because some operations bypass the buffer manager"*, and break queries into subqueries.

### Real complaints

| Issue | Who / date / version | Verbatim | Status |
|---|---|---|---|
| [#14132](https://github.com/duckdb/duckdb/issues/14132) | **Marco Slot (Crunchy Data)** — 2024-09-26, v1.1.1 | `Out of Memory Error: could not allocate block of size 256.0 KiB (3.7 GiB/3.7 GiB used)` — GROUP BY / DISTINCT where the *values* (long strings, MD5 hashes) are large, not the keys | Closed, labeled **reproduced** |
| [#14142](https://github.com/duckdb/duckdb/issues/14142) | rmx90210 (user) — 2024-09-27, v1.1.1 | `Out of Memory Error: failed to offload data block of size 34.7 MiB (187.3 GiB/187.3 GiB used). This limit was set by the 'max_temp_directory_size' setting.` — with 187 GiB of disk actually free | Closed |
| [#14339](https://github.com/duckdb/duckdb/issues/14339) | wonb168 (user) — 2024-10-12, v1.0.0 | PIVOT consumed **~90 GB** on an 8.9 GB database (780M rows, 47 feature codes) | **STILL OPEN** |
| [#9119](https://github.com/duckdb/duckdb/issues/9119) | user | "pivot consume a lot of memory" | — |
| [#16229](https://github.com/duckdb/duckdb/issues/16229) | user | Out-of-memory error when creating index | — |
| [#15420](https://github.com/duckdb/duckdb/issues/15420) | user | ART index creation takes too much memory | — |
| [#19468](https://github.com/duckdb/duckdb/issues/19468) | rayGoMoon (user) — **2025-10-22, v1.4.1** | UNIQUE-constrained table with ~1,500 stable rows grew the file to **1.2 GB in 24 h** under repeated update/delete; same data as Parquet = 400 KB; dropping the UNIQUE constraint kept it at 2.3 MB. VACUUM and CHECKPOINT did not reclaim. | Closed |

**PIVOT specifically:** the reason is that PIVOT internally uses `list()`, which is on the documented cannot-spill list. That makes the #14339 report structural rather than a bug.

### The one that should worry you most

[**#25702** — "Incorrect results: hash join silently drops rows when the build side spills to disk"](https://github.com/duckdb/duckdb/issues/25702) — **Ke Han (Purdue University), 2026-09-14**. Expected 3,000,000 rows, got **480,000**, no error, no warning. Root cause quoted from the report:

> "The join key values that survive are exactly those whose partitions were built in the first round of the external build; every row of the remaining keys is discarded by a Bloom filter that was pushed into the probe-side scan before the later rounds ran."

Affects INNER, SEMI, EXISTS and `IN (subquery)` when memory pressure forces external processing. Workaround: disable join filter pushdown. **Reporter states v1.5.5 was correct** — this is against main branch commit `8bc48eb`, i.e. the v2.0 line. Open, PR #25718 linked. This is a *silent wrong answer* class of bug in exactly the spill path, and it is ten days old.

v1.5.5's own release notes fixed a related one: *"segfault in external hash aggregate when radix bits grow after going external"* (#23757).

**Documentation ambiguity:** [duckdb-web #2859](https://github.com/duckdb/duckdb-web/issues/2859) (soerenwolfers, 2024-05-12, closed, assigned to maintainer szarnyasg, labeled **high-priority documentation bug**) flags that the docs contradict themselves on whether `:memory:` connections spill by default. The tuning guide says in-memory mode *cannot* spill unless you `SET temp_directory`; the config page says `temp_directory` already defaults to `.tmp`. **Set it explicitly and don't rely on the default.**

---

## 2. Write concurrency in practice

### The model (official)

[Concurrency docs](https://duckdb.org/docs/current/connect/concurrency) — exactly two supported configurations:
1. **One** process reads and writes, or
2. **Multiple** processes read, **none** writes (`access_mode = 'READ_ONLY'`)

Verbatim: **"Writing to DuckDB from multiple processes is not supported automatically and is not a primary design goal."**

Within a single process, MVCC + optimistic concurrency control does work well: *"Appends will never conflict, even on the same table"*; different threads can update different tables or different rows. Same-row conflict gives:
> `Transaction conflict: cannot update a table that has been altered!`

The docs' advice is simply to rerun the transaction.

The docs also carry a warning directly relevant to you: exercise care with DuckDB files in shared directories, network storage, or across filesystems, as file lock handling may be affected.

### The error text people actually report

> `IO Error: Could not set lock on file "<path>": Conflicting lock is held in <process> (PID nnn)`

On Windows the same situation surfaces differently:
> `IO Error: Cannot open file "...\mydb.duckdb": The process cannot access the file because it is being used by another process.`

and a third variant reported in production write-ups:
> `Database "mydb.duckdb" is already opened by another process.`
> — [Running DuckDB in Production](https://www.dench.com/blog/duckdb-in-production), Mark Rachapoom (third-party blog), 2026-03-26

Reports:
- [**#17158**](https://github.com/duckdb/duckdb/issues/17158) — ChuckJonas (user), **2025-04-16, v1.2.1 / Python client 1.2.2**: `IO Error: Could not set lock on file "/data/extract/extract.db": Conflicting lock is held` **even with `read_only=True`**, because the DuckDB UI held the file. **Still open, "needs triage."**
- [#13079](https://github.com/duckdb/duckdb/issues/13079) — conflicting lock under FastAPI/Uvicorn `reload=True` (goes away with reload off).
- [#15641](https://github.com/duckdb/duckdb/issues/15641) — Paul Austin (Automutatio), 2025-01-09, v1.1.0, Windows: `Cannot open file "P:\2025-01-09_Log.json": The process cannot access the file because it is being used by another process.` Reporter's own note: *"Windows likes to lock files."* Still under review.
- [Discussion #12296](https://github.com/duckdb/duckdb/discussions/12296) — davetapley, 2024-05-28. **This one matters a lot for long-running Python agents.** A caught DuckDB exception object holds an implicit reference to the connection. If you return or store the exception, the connection never closes and the file lock is never released: `IO Error: Could not set lock on file "/tmp/duck_raise.duckdb"`. Fix is to never return/retain caught DuckDB exceptions — return `None` or a status value.
- [duckdb-go #185](https://github.com/duckdb/duckdb-go/issues/185) — unclosed prepared statements mean `Conn.Close()` and `DB.Close()` both return nil while *"the DuckDB instance, its worker threads and the file lock survive."* Same class of leak exists in [duckdb-node #111](https://github.com/duckdb/duckdb-node/issues/111) and [beekeeper-studio #3010](https://github.com/beekeeper-studio/beekeeper-studio/issues/3010).

### The finding that breaks the naive multi-agent plan

[LibreDB, "One DuckDB file admits one process, readers included"](https://libredb.org/blog/duckdb-single-process-file-lock/) — **third-party vendor blog, 2026-06-22, tested against v1.5.5**. Their measured matrix, all **while a writer held the file open**:

| Scenario | Result |
|---|---|
| Second read-write handle, same process | Allowed |
| `DuckDBInstance.fromCache` on same file, same process | Allowed |
| Second `access_mode: 'READ_ONLY'` handle, same process | Allowed, genuinely read-only |
| Second read-write **process** | `IO Error: Could not set lock on file ...: Conflicting lock is held in ... (PID nnn)` |
| Second read-only **process** | **Refused with the same lock error** |

Their conclusion: *"a DuckDB file admits exactly one operating-system process."* This matches the independently-filed #17158. **So "one writer plus many readers across processes" is not actually available while the writer holds the file** — the official docs' "multiple readers" case requires that *nobody* has it open read-write.

### Workarounds — the official list

From the [concurrency docs](https://duckdb.org/docs/current/connect/concurrency):
1. Cross-process mutex; open read/write, do the work, close
2. Retry-with-backoff on connect
3. Keep the write path in Postgres/MySQL/SQLite and use DuckDB's scanner extensions to query it
4. Stage writes as Parquet/CSV, read many files with DuckDB
5. A single web server / owning process that serializes all access
6. **DuckLake with Postgres as catalog** — the docs' recommendation for a stable multi-writer setup
7. **Quack**

### Quack / CONNECT maturity — the honest read

- [Quack announcement](https://duckdb.org/2026/05/12/quack-remote-protocol), DuckDB team, **2026-05-12**. Native client/server RPC, Arrow-based. Explicitly supports **multiple concurrent writers** across processes/machines. Auth is a random token generated at startup. Verbatim: *"Quack does not use SSL by default, because it is a bit silly to bring all that infrastructure and add dependencies just for localhost communication."* Stated ceiling: beyond ~8 parallel threads you hit *"a current limitation of DuckDB itself in concurrent insertions per second into the same table."*
- [v1.5.3 announcement](https://duckdb.org/2026/05/20/announcing-duckdb-153), DuckDB team, 2026-05-20 — Quack ships as a **core extension** (autoinstalled/autoloaded), but verbatim: **"Quack is still in beta state and breaking changes may happen in the protocol, in function names, etc."**
- [v2.0 preview](https://duckdb.org/2026/08/17/duckdb-20-highlights), **Mark Raasveldt and Hannes Mühleisen**, 2026-08-17 — Quack *"graduates to stable in v2.0."*
- [v2.0-alpha](https://duckdb.org/2026/09/02/try-duckdb-20-alpha), 2026-09-02 — quack extension goes 0.x → 1.0. But: **"DuckDB alpha clients are explicitly not production-ready"**, and critically for you: **"Extensions are not yet available for the Windows client."**
- [Deployment docs](https://duckdb.org/docs/current/quack/setup/deployment) currently document exactly **one** recipe: AWS EC2 + CloudFormation + nginx + Let's Encrypt. No Windows recipe, no local-daemon recipe, no stated concurrency guarantees.

**Bottom line on Quack:** it is the right-shaped answer to your problem and it is beta today, stable "in v2.0" which is ~October 2026, with no Windows extension build in the alpha and no documented non-AWS deployment path. Not something to build several long-running agents on this month.

---

## 3. Long-running processes holding connections

### WAL and checkpointing

[Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions) — **Raasveldt & Mühleisen, 2024-10-30** (official):
- Checkpoint happens automatically when the WAL reaches a limit, **default 16 MB**, and at database shutdown
- **`FORCE CHECKPOINT` will "abort (rollback) any active transactions"**
- MVCC keeps one version entry per 2,048-row batch; readers pick a version via undo buffers

[CHECKPOINT docs](https://duckdb.org/docs/current/sql/statements/checkpoint) (official): plain `CHECKPOINT` **fails if there are running transactions**. That is the core long-running-process hazard: a connection held open for hours can keep a transaction alive, checkpoints keep failing, and the WAL keeps growing.

### Real reports

- [**#9150**](https://github.com/duckdb/duckdb/issues/9150) — **Anshul Khandelwal (Rill Data), 2023-09-28, v0.8.1/0.9.0**: `.db.wal` *"intermittently explodes in size"* during ingestion when any concurrent read/write runs — a 50 GB database paired with a **500 GB WAL**. Only with disk-resident queries; `SELECT 1` doesn't trigger it. **Closed via PRs #11918 and #9236** — old version, believed fixed, but it is the canonical illustration of the failure mode.
- [**#17006**](https://github.com/duckdb/duckdb/issues/17006) — TnzGit (user), **2025-04-06, v1.2.1, Windows x64**: DuckDB **hangs on commit** when `wal_autocheckpoint` (set to 4 MiB) is reached during bulk inserts. Reporter had to wrap commits in a thread with a 30-second timeout. **Still open, "needs triage."** Windows *and* long-running *and* checkpoint — all three of your risk axes at once.
- [#9721](https://github.com/duckdb/duckdb/issues/9721) — "Is the checkpoint size parameter a lie?"
- [#10002](https://github.com/duckdb/duckdb/issues/10002) — `*.wal` not cleaned up right after `connection.close`

### Memory growth over hours

- [**#20569**](https://github.com/duckdb/duckdb/issues/20569) — **Yakko Majuri (Skald Labs), 2026-01-16, DuckDB 1.4.3 LTS**, both Python (`duckdb 1.4.3`) and Node (`@duckdb/node-api 1.4.3-r.3`). Node: *"rss will go up forever"* on repeated `SELECT 42`. Python: 239.8 MiB still resident after `DROP TABLE` **and** closing the connection. Reporter links two prior unresolved cases. *(Status ambiguous in the rendered page — see "could not verify" below.)*
- [#14983](https://github.com/duckdb/duckdb/issues/14983) — memory grows unbounded when upserting rows whose strings exceed 12 characters
- [#13037](https://github.com/duckdb/duckdb/issues/13037) — DuckDB retains a reference to a reused Python DataFrame
- [#18031](https://github.com/duckdb/duckdb/issues/18031) — memory leak in parallel insertion
- [#10034](https://github.com/duckdb/duckdb/issues/10034) — OOM after repeated queries despite sufficient memory
- v1.5.5 release notes did fix an **"eviction node memory leak"** and a **"deadlock in TemporaryMemoryManager"**

### File handles

[C API Startup & Shutdown docs](https://duckdb.org/docs/lts/clients/c/connect) (official): every connection must be explicitly disconnected and the database explicitly closed *"to avoid memory and file handle leaking."* Higher-level clients inherit this — see duckdb-go #185 and duckdb-node #111 above.

### Does an open write connection block readers?

**Across processes: yes, apparently completely** (LibreDB v1.5.5 matrix + #17158). **Within one process: no** — MVCC gives readers a consistent snapshot without blocking. This is the single most important architectural fact for your setup.

### Large-file cost

[Working with Huge Databases](https://duckdb.org/docs/current/guides/performance/working_with_huge_databases) (official): checkpointing after adding **a few rows** to a TPC-H SF1000 database takes **~5 seconds**. On Linux, XFS is recommended for large files. **No Windows/NTFS guidance is given at all.**

---

## 4. Windows-specific

Windows Defender being disabled removes one class of problem but not the ones below.

- [**duckdb-python #613**](https://github.com/duckdb/duckdb-python/issues/613) — MiamiPavel (independent user), **2026-09-06** (18 days ago). **Access violation `0xC0000005` (INVALID_POINTER_READ) in `_duckdb.cp313-win_amd64.pyd` during concurrent read-only queries.** Windows 11 Pro build 22631, Python 3.13, 8 cores. **Reproduced on DuckDB 1.4.4 *and* 1.5.5**, on two separate Windows machines. Trigger: *"Multi-process worker pool doing concurrent read-only queries against a DuckDB file with the spatial extension"* — no writes, no concurrent writers. Crashes cluster at batch start and client disconnect. **Open, no maintainer reply visible.** The reporter also notes Windows wheels ship **no version resource and no PDBs**, so crash dumps can't be symbolicated. This is the closest thing to your exact scenario that exists in the tracker, and it is unresolved.
- [**#20384**](https://github.com/duckdb/duckdb/issues/20384) — HarshJainCodes, **2026-01-05, v1.4.3, Windows 11**: `IO Error: No files found that match the pattern "C:\Studies\tenants\...\FullKeyInfo.parquet"` on **long paths, even with Windows long-path support enabled**. Closed, PR #20983.
- [**#14735**](https://github.com/duckdb/duckdb/issues/14735) — YarShel, 2024-11-06, v1.1.0, **Windows 10**: setting `temp_directory` to a different drive (C: → E:) is **silently ignored in Python**; spilling continued to C:. Closed. Relevant if you plan to point spill at a fast scratch volume — **verify it actually landed there**.
- [**#5878**](https://github.com/duckdb/duckdb/issues/5878) — DuckDB **deletes the `temp_directory` path itself**, not just its contents, so the directory no longer exists afterwards. Do not point `temp_directory` at a directory you care about.
- [#15641](https://github.com/duckdb/duckdb/issues/15641) — can't read JSON/CSV files that another Windows app holds open (Windows advisory locking).
- [duckdb-ui #109](https://github.com/duckdb/duckdb-ui/issues/109) — Windows Explorer "Copy as Path" produces `"F:\scan.db"` with quotes; DuckDB treats the quotes as part of the filename.
- [DuckDB.NET #271](https://github.com/Giorgi/DuckDB.NET/issues/271) — access violation in `DuckDB.DLL` on Windows, 2025-05-10.
- v1.5.2 release notes fixed *"missing extension static libs in Windows MinGW bundle"*.
- **v2.0-alpha: "Extensions are not yet available for the Windows client."**
- Antivirus: I found **no DuckDB-official statement** about AV interference, and no DuckDB GitHub issue attributing a failure to Windows Defender specifically. The temp-directory "access denied" material I found was generic Windows advice, not DuckDB-specific. Your disabled-Defender posture is fine; there's simply nothing to report here.

---

## 5. When DuckDB is the wrong tool

**Official sources:**
- [FAQ](https://duckdb.org/faq): DuckDB is *"a single-node database system, hence it makes use of vertical scalability."* For multi-client scenarios it points at DuckLake+Postgres or Quack. Notably, the FAQ has **no "when not to use DuckDB" section** — I looked.
- [Concurrency docs](https://duckdb.org/docs/current/connect/concurrency): multi-process writes *"not a primary design goal."*
- [Limits](https://duckdb.org/docs/current/operations_manual/limits): no practical file-size limit — *"database files using 15 TB+ of disk space and they work fine"*, though connections and checkpoints get slower. BLOB and string cap at 4 GB; array size 100,000; 128 GB per vector.

**Third-party consensus (2026 write-ups, all non-official):**
- Wrong tool for: point lookups, single-row updates, high-frequency small writes, strict per-row transactional guarantees, live streaming ingestion, many concurrent writers, and serving as an application backend under concurrent load.
- [DuckDB vs SQLite 2026](https://tech-insider.org/duckdb-vs-sqlite-2026/) claims DuckDB is **14x–124x slower than SQLite on point lookups** — *treat this number with suspicion; it's an anonymous SEO-ish site and I could not corroborate the figure against a reputable benchmark.* The direction is corroborated by [Better Stack](https://betterstack.com/community/guides/scaling-python/duckdb-vs-sqlite/) and [DataCamp](https://www.datacamp.com/blog/duckdb-vs-sqlite-complete-database-comparison): columnar storage must reconstruct rows from separate column segments, so single-row access carries real overhead.
- The recurring recommended pattern across every production write-up: **one owning process holds the file read-write and serializes all access; everything else talks to it over IPC/RPC, or reads periodic snapshot copies.**
- [Is DuckDB Production-Ready?](https://talkdatatomelol.substack.com/p/is-duckdb-production-ready), [DuckDB in Production](https://www.dench.com/blog/duckdb-in-production), [Hikmah Technologies](https://hikmahtechnologies.com/blog/is-duckdb-safe-for-production/) all converge on: *almost every "DuckDB isn't production-ready" story traces back to concurrency.*

---

## 6. Data loss, corruption, crash recovery

**Official:** [Crashes guide](https://duckdb.org/docs/current/guides/troubleshooting/crashes) — `SIGSEGV`/`SIGABRT` *"should never occur"*. Internal errors (e.g. `Attempted to access index 3 within vector of size 3`) put DuckDB into a **restricted/invalidated mode where all subsequent operations fail**. Recovery after a crash: restart on the same file; DuckDB replays the `.wal` and checkpoints.

**Reports:**
- [**#14421**](https://github.com/duckdb/duckdb/issues/14421) — Rob Jackson, 2024-10-17, v1.1.2: opening the same on-disk database **both directly and via `ATTACH` within one process** corrupts it. `Serialization Error: Failed to deserialize: field id mismatch, expected: 100, got: 0`. **Closed via PR #18857.** Worth knowing because the "one owning process" pattern can easily drift into this shape.
- [**#9667**](https://github.com/duckdb/duckdb/issues/9667) — "Low disk space can result in database corruption": a large write with insufficient disk can leave the database corrupt and unusable.
- [spiceai #13985](https://github.com/spiceai/spiceai/issues/13985) — a checkpoint hitting `ENOSPC` left the `.duckdb` file corrupt rather than failing the transaction and preserving the last consistent state. Paired with [spiceai #14358](https://github.com/spiceai/spiceai/issues/14358): after invalidation the connection pool reported every connection healthy while all queries failed.
- [#17461](https://github.com/duckdb/duckdb/issues/17461) — Serialization error when the DuckDB file lives in a **Dropbox** folder. Generalizes: do not put the file under any sync client (OneDrive included).
- [duckdb-java #28](https://github.com/duckdb/duckdb-java/issues/28) — `Serialization Error: Failed to deserialize: expected end of object, but found field id: 103`
- [#3762](https://github.com/duckdb/duckdb/issues/3762) — `Serialization Error: Attempting to read a required field, but field is missing` (DBeaver)
- [#5488](https://github.com/duckdb/duckdb/issues/5488) — "Reproducible data corruption on simple insert" (old)
- **v1.5.5 fixed**: RLE corruption false positives, DROP COLUMN metadata corruption, min/max aggregate stats when row groups are filtered.
- **v2.0 adds** *"stronger corruption validation"* to the new storage format ([v2.0 preview](https://duckdb.org/2026/08/17/duckdb-20-highlights)).

**Storage-format migration warning:** [Storage Versions and Format](https://duckdb.org/docs/current/internals/storage) — v1.5.x is storage version 68. v2.0 bumps the **default** to storage format v2.0.0, described in the v2.0 preview as a backwards-incompatible change, with the documented migration being `EXPORT DATABASE` under the old version then `IMPORT DATABASE` under the new. `STORAGE_VERSION` can be pinned per-`ATTACH` or via `storage_compatibility_version`.

---

## What I could NOT verify

1. **Whether two read-only processes can coexist on one file when no writer holds it.** Official docs say yes; LibreDB's matrix explicitly only tested "while a writer held the file open" and did not test reader+reader. I found no Windows-specific test of this at all. **Test this yourself before designing around it** — it's the pivot point for your architecture.
2. **Current status of the #20569 memory leak.** The rendered page gave contradictory signals ("Closed" badge + "under review" label + no fix confirmation). Treat as unresolved until you check.
3. **Whether hash-join spill bug #25702 can reach v1.5.5.** The reporter says v1.5.5 returned correct results and the bug is on main. I could not independently confirm 1.5.5 is unaffected.
4. **Maintainer positions on most issues.** WebFetch returns rendered page excerpts; on several issues (#17158, #14142, #20569, #14339, #613, #17006) no maintainer reply was visible, which is not the same as none existing.
5. **DuckDB's Windows file-lock implementation** (LockFileEx vs. something else, mandatory vs. advisory, behaviour on abrupt process kill). Not documented anywhere I found. Given long-running agents that may be killed, this matters — expect stale locks after a hard kill and plan a lock-clearing path.
6. **Whether v2.0 can open a v1.5 file read-only without EXPORT/IMPORT.** Sources conflict; the official storage compatibility table stops at v1.5.x/version 68 and does not mention v2.0.
7. **Python 3.11 Windows wheel for 1.5.5 specifically.** A DeepWiki page says the matrix covers 3.10–3.13; I did not confirm on PyPI directly. Note #613's crash was on 3.13, so 3.11 is untested territory for that particular bug.
8. **Any AV/Defender-specific DuckDB issue.** None found. The absence is itself the finding.
9. **The 14x–124x point-lookup figure** — single low-credibility source, uncorroborated.

---

## The three things I'd act on

1. **Do not let several agent processes open one DuckDB file.** Cross-process reader+writer coexistence appears not to work at all (LibreDB v1.5.5 + #17158), and even pure concurrent read-only access from a multi-process pool is an open Windows crash report against 1.5.5 ([duckdb-python #613](https://github.com/duckdb/duckdb-python/issues/613), 18 days old). One owning process, everything else over IPC.
2. **Quack is the designed answer and is not ready for you yet.** Beta per DuckDB's own words, stable "in v2.0" (~Oct 2026), **no Windows extensions in the v2.0 alpha**, and the only documented deployment recipe is AWS EC2.
3. **If you keep connections open for hours, the WAL is your failure mode.** Plain `CHECKPOINT` fails while transactions run, `FORCE CHECKPOINT` rolls them back, and #17006 is an open Windows hang on checkpoint. Instrument WAL size and make checkpointing an explicit scheduled act, not an assumption.

### Sources

[Memory Management in DuckDB](https://duckdb.org/2024/07/09/memory-management) · [Tuning Workloads](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads) · [Out of Memory Errors](https://duckdb.org/docs/lts/guides/troubleshooting/oom_errors) · [Out-of-Memory Issues](https://duckdb.org/docs/current/guides/performance/oom) · [Limits](https://duckdb.org/docs/current/operations_manual/limits) · [Indexes](https://duckdb.org/docs/current/sql/indexes) · [Concurrency](https://duckdb.org/docs/current/connect/concurrency) · [FAQ](https://duckdb.org/faq) · [Crashes](https://duckdb.org/docs/current/guides/troubleshooting/crashes) · [Storage Versions and Format](https://duckdb.org/docs/current/internals/storage) · [Working with Huge Databases](https://duckdb.org/docs/current/guides/performance/working_with_huge_databases) · [CHECKPOINT](https://duckdb.org/docs/current/sql/statements/checkpoint) · [Analytics-Optimized Concurrent Transactions](https://duckdb.org/2024/10/30/analytics-optimized-concurrent-transactions) · [External Aggregation](https://duckdb.org/2024/03/29/external-aggregation) · [Quack Remote Protocol](https://duckdb.org/2026/05/12/quack-remote-protocol) · [Quack Deployment](https://duckdb.org/docs/current/quack/setup/deployment) · [DuckDB 1.5.3](https://duckdb.org/2026/05/20/announcing-duckdb-153) · [DuckDB 1.5.5](https://duckdb.org/2026/07/22/announcing-duckdb-155) · [Preview of v2.0](https://duckdb.org/2026/08/17/duckdb-20-highlights) · [Try v2.0-alpha](https://duckdb.org/2026/09/02/try-duckdb-20-alpha) · [C API Startup & Shutdown](https://duckdb.org/docs/lts/clients/c/connect) · [#25702](https://github.com/duckdb/duckdb/issues/25702) · [#20569](https://github.com/duckdb/duckdb/issues/20569) · [#20384](https://github.com/duckdb/duckdb/issues/20384) · [#19468](https://github.com/duckdb/duckdb/issues/19468) · [#17461](https://github.com/duckdb/duckdb/issues/17461) · [#17158](https://github.com/duckdb/duckdb/issues/17158) · [#17006](https://github.com/duckdb/duckdb/issues/17006) · [#15641](https://github.com/duckdb/duckdb/issues/15641) · [#14735](https://github.com/duckdb/duckdb/issues/14735) · [#14421](https://github.com/duckdb/duckdb/issues/14421) · [#14339](https://github.com/duckdb/duckdb/issues/14339) · [#14142](https://github.com/duckdb/duckdb/issues/14142) · [#14132](https://github.com/duckdb/duckdb/issues/14132) · [#13079](https://github.com/duckdb/duckdb/issues/13079) · [#9667](https://github.com/duckdb/duckdb/issues/9667) · [#9150](https://github.com/duckdb/duckdb/issues/9150) · [#5878](https://github.com/duckdb/duckdb/issues/5878) · [Discussion #12296](https://github.com/duckdb/duckdb/discussions/12296) · [duckdb-python #613](https://github.com/duckdb/duckdb-python/issues/613) · [duckdb-web #2859](https://github.com/duckdb/duckdb-web/issues/2859) · [duckdb-go #185](https://github.com/duckdb/duckdb-go/issues/185) · [duckdb-skills #11](https://github.com/duckdb/duckdb-skills/issues/11) · [spiceai #13985](https://github.com/spiceai/spiceai/issues/13985) · [LibreDB lock analysis](https://libredb.org/blog/duckdb-single-process-file-lock/) · [DuckDB in Production](https://www.dench.com/blog/duckdb-in-production) · [Is DuckDB safe for production?](https://hikmahtechnologies.com/blog/is-duckdb-safe-for-production/)
