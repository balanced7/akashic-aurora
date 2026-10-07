# DuckDB deep dive, re-run -- lane: fit

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent afeb99295b50a166e (claude-opus-5-5) ran 21:01-21:19 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\fit (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md. Read local-benchmarks-and-census (the interim note and the measured numbers) and build-vs-buy-postmortems first.

GUARDRAILS (hard rules):
- This lane is READ-ONLY on E:\AI-Setup. Do not edit, commit, or run any agent_cli verb that writes (learn, note, handoff, bifrost-send, doc, task, wish, lock). Read-only verbs such as --help, status, recall and lookback are fine.
- The Glob tool returns empty on E:\ drive paths. Use the Grep tool or PowerShell to find files.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\fit\. Create files only there.
- Do not spawn subagents.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings with file:line citations, each tagged [read] (seen in code) or [inferred]; then what you could NOT verify; then the design. Under 1,800 words.

LANE: fit. Question: how would this plug into Akashic Aurora specifically? Do a read-only study of E:\AI-Setup, starting with docs\ARCHITECTURE.md and AGENTS.md. Find:
1. which code writes the JSONL ledgers (grep for .jsonl writers under core\, scripts\ and agent\), and their formats;
2. which read paths would benefit from a query engine, such as the "eye" transcript index, recall stats, bus analytics ("who talks most"), and doctor/roster history;
3. existing Polars, pyarrow and sqlite usage;
4. how new verbs and doors are added (agent_cli verbs, MCP tools in the MCP server).

Then sketch a "ledger lake": schema-versioned JSONL, periodic Parquet compaction, a query door, and which engine sits behind it. Name the smallest first slice that would prove value, its acceptance test, and its risks. Respect the house conventions you find (pinned Python 3.11, no new containers, the door contract).

## The report (verbatim)

The fit lane is finished. The harness refused my incremental REPORT.md ("Subagents should return findings as text, not write report files"), so this message is the whole report. The read-only probe scripts are in the lane dir as `probe_*.py`.

Tags: **[read]** means seen in code. **[measured]** means a read-only probe I ran tonight (not one of the two tags you asked for, but measurements are neither seen in code nor inferred). **[inferred]** means reasoning I did not check.

## Headline
- At today's size, speed is not the reason to add DuckDB. Plain Python answers "who talks most" over the whole bus export (223,910 rows) in 0.72 s. What we lack is answers we can trust.
- The biggest finding: FileLedger, the file half of the "durable record", **drops rows**. From 09-10 to 09-24 it lost 410 of 18,170 recall outcomes and 36 of 1,430 firehose events (about 2.3% and 2.5%). Almost every loss happened within 0.5 s of another write to the main file. Services running from worktrees also wrote another 88 outcomes and 58 events into their own worktree folders instead of the main one.
- Recommendation: build a thin "ledger lake". Every answer shows where its rows came from and what is missing. Parquet files are the long-term archive. DuckDB runs in memory as an optional engine behind the door, with a stdlib twin that must give identical answers. Fix FileLedger's write path in parallel.

## Findings

**A. Who writes the ledgers, and in what shape**
1. **FileLedger writes `session_logs/ledger/<stream>.jsonl`** as `{"id": seq, "event": {...}}`.
   - Every emit reads the whole file, appends one row, trims to the cap and rewrites the file via tmp + `os.replace` (`core/foundation/ledger.py:216-236`) [read].
   - It is guarded only by a `threading.RLock` (`:190`), with no cross-process lock. Write errors are logged and swallowed (`:235-236`) [read].
   - Replaying that cycle on copies of the files costs 166 ms per emit for `recall_outcome` (14 MB) and 206 ms for `events_raw` (18 MB). Appending one line costs 0.1 ms [measured, on C: copies].
2. **The losses, broken down.** I compared each FileLedger file with the Redis copy in `state/bus-export`, over 09-10 to 09-24 15:00 UTC [measured]:
   - **Recall outcomes:** 498 rows missing from the main file. 88 sit in the `sunshine-discord-split` worktree's own ledger. 410 are in no file at all, and all 410 had a main-file write within 0.5 s (7% of kept rows do).
   - **Firehose events:** 94 missing. 58 are in the worktree; 36 are in no file, 33 of them within 0.5 s of a main-file write.
   - **Likely cause of the losses:** the unlocked read-modify-rewrite [inferred].
   - **Cause of the worktree split:** `data_root()` is derived from the running checkout (`core/paths.py:113-126`), and the worktree's `run_aurora_service.py` sets no `AI_SETUP` [read]. The production scheduled tasks (SunshineFleet and others) run from that worktree [measured].
   - This is the same defect as `core/world.py:10`'s "second BODY wired to the SAME BRAIN", one level down. It is also the twin of the FileStore defect the house measured at 65.6% loss and fixed with SqliteStore (`core/foundation/sqlite_store.py:5-16`) [read].
   - Sol's shadow-shelf fence already refused FileLedger over the rewrite cost (`fences/shadow-shelf-substrate/half_b.md:28`) [read]. The loss measurement is new.
3. **Caps trim the "durable" record.**
   - `events:raw` keeps 100k rows and each per-agent stream 10k (`core/events/event_log.py:43-45`). `recall:outcome` keeps 20k and `recall:surface` 6k (`core/recall/at_action.py:237-249`) [read].
   - The outcome comment says 20k is "roughly two months". The file actually holds 09-07 23:45 to 09-24 21:03: 17 days at about 1,180 rows per day [measured].
4. **The bus export (`scripts/ops/archive_ephemeral.py:84-139`)** is a true append with a per-stream cursor [read]. It runs daily at 12:05 (task `AkashicAurora-EphemeralArchive-Daily`) [measured].
   - Every row has the same outer wrapper: `{stream, id, exported_at, fields}` [read].
   - Inside `fields` there are two shapes. Bifrost packets carry `frm`, `to`, `kind`, `content` and so on, stamped with version 2 plus length and hash (`core/comm/packet_spec.py:41,104-114`). Ledger streams carry `{"data": "<json string>"}`, JSON nested inside a string (`ledger.py:147`) [read].
   - It holds recall outcomes back to 08-08 (40,784 rows). It is the only long series that exists [measured].
5. **About two dozen other append-mode writers**, each with its own ad-hoc row format. Examples: web receipts (`core/web/door.py:35`), routes (`core/eye/routes.py:63`) and atoms (`core/library/atoms.py:117-119`) [read].
   - FileLedger rows and the event and recall payloads carry no schema version [read].
   - Bifrost packets do carry one, with a written rule: "consumers downgrade unknown versions, they do not drop" (`packet_spec.py:122-124`) [read].
6. **Broken-character trap:** 61 of 289,986 rows contain a lone UTF-16 surrogate (a broken half of an emoji-style character). 15 are at line level and 46 are inside the nested JSON strings [measured]. Python accepts them; DuckDB's strict reader hard-failed on one (census); Parquet string columns cannot hold them [inferred].
7. **Duplicate-message trap:** 25,956 of 160,948 message rows (16%) are the same message exported once per lane or inbox stream [measured]. A naive `GROUP BY frm` over-counts.

**B. Read paths that would benefit**
- **Prevention trend (high).** `durable_outcomes` and `prevention_rate_durable(days=30)` (`at_action.py:1107-1138`) are only called from tests. If wired up, a 30-day request would silently get 17 days [read/measured].
- **Bus analytics (high for expressiveness, low for speed).** The only reader is `archive_ephemeral.search` (`:152-183`), a full Python scan that reads each whole file. No door answers "who talks most" [read].
- **The Eye (keep it on SQLite).** It is SQLite WAL + FTS5 (`core/eye/index.py:200-224`) with 44,525 events across 1,466 sessions [measured]. Full-text search is SQLite's strength.
  - What a query engine adds is a cross-plane join. 17 of 18 recall-outcome session ids (97.4% of rows) match an Eye session [measured].
  - That is the join `core/recall/prevention.py:39-40` says the "complied" verdict needs (medium-high value).
- **Evicted firehose pointers (medium).** `EventLog.resolve` answers "aged out" (`event_log.py:220-244`). A Parquet archive would let it answer "archived" instead.
- **Turn-duration history (medium).** turn_metrics calls the firehose its "durable analytics tail" (`core/comm/turn_metrics.py:9-14,130`). Its only reader takes the latest row (`core/comm/doctor.py:942-974`), so trends go unanswered.
- **Roster and doctor (low).** They hold live state only; no history is kept.
- **Recall stats trend (low).** `funnel.trend` scans the newest 5,000 events (`core/recall/funnel.py:35`), which is fine at about 100 events a day.

**C. Existing engines**
- No Polars, pyarrow, pandas or DuckDB import appears anywhere in repo code [read, grep].
- On the pinned Python 3.11.9: polars 1.39.3, pyarrow 23.0.1 and pandas 3.0.2 are installed; duckdb is not; SQLite is 3.45.1 [measured].
- `requirements.txt:3-5` says the core runs on the stdlib alone and extras are optional [read].
- SQLite is the house's durable engine: SqliteStore, `eye.db`, and the T370 shadow shelf, which refused FileLedger (`research/in-flight/t370-shadow-shelf-pilot-2026-08-28.md:73`) [read].
- The July storage sweep dismissed DuckDB as "wrong shape for KV" (`research/reviewed/storage-engine-sweep-2026-07-26.md:56`) [read]. That fits a read-side-only role.

**D. How verbs and doors are added**
- **CLI:** a `cmd_<verb>(args)` function plus `sub.add_parser` in `agent_cli.py` [read].
- **MCP twin:** an `@mcp.tool()` async wrapper around `_athread(_run, agent_cli.cmd_x)`. Reads run unlocked; writes pass `lock=True` (`ai_setup_mcp.py:163-172,245-264`) [read].
- **Argument defaults:** every new `args` attribute goes into `_ARG_DEFAULTS` (`:178-242`), pinned by `tests/test_mcp_arg_defaults_parity.py` [read].
- **Door manifest:** each verb is classified in the MANIFEST of `scripts/checkers/check_door_parity.py:107-113`. A shared verb also needs ToolBox coverage or a written exemption (`:14-20`) [read].
- **Architecture map:** a new `core/` subpackage needs one line in `docs/ARCHITECTURE.md` or `check_comprehensibility` fails (`:223-238`) [read].
- **Optional engines:** import lazily and name which engine answered (`:127-128`, `:191-194`) [read].
- **Results:** return three states (done, partially, failed) via `BoundaryOutcome` (`core/outcome.py`). `EventQuery` turning exceptions into `[]` (`core/events/event_query.py:80-81,107-108,132-133`) is the pattern to avoid [read].
- **Named questions** can be toolbelt macros (`core/toolbelt/registry.py:7-17`) [read].

## Could not verify
- The exact mechanism of the 410 and 36 losses. The unlocked rewrite and a Windows `os.replace` refused while another process holds the file both fit the timing signature; neither was reproduced.
- Whether every worktree ledger was found. I checked three worktrees plus Alpha and Sandbox; `es.exe` is not on PATH.
- DuckDB itself, since it is not installed:
  - a Python 3.11 wheel for 1.5.x;
  - locking down a query with `enable_external_access=false` plus `allowed_directories`;
  - installing the sqlite extension offline;
  - many in-memory processes at once on Windows (duckdb-python #613 is still open, though it involves a database file).
- The census totals (904 files, 968,929 rows) against my count (1,797 files, 324 MB across `state`, `session_logs` and `store`). The scopes differ and I did not reconcile them.
- Emit timings were taken on C: copies, not on E:.

## Design: the ledger lake
Principles: a thin reader over open formats; **never a `.duckdb` file**; never delete a source.

1. **Hot tail.** Keep today's JSONL. `HybridLedger.emit` adds two keys: `"v"` (schema version) and `"uid"` (one id minted once and shared by the file and Redis rows, so they dedupe exactly).
   - **Prerequisite slice L0:** FileLedger appends one line under `core.foundation.filelock`, reading only the file's tail to get the next id. Trimming happens under the lock, only once the file passes twice its cap.
   - Production services set `AI_SETUP` to the production data root.
2. **Shapes registry** (`core/lake/shapes.py`). Each stream family gets explicit columns, types and a version. The lake never globs across families, which makes the census's three-schemas-in-one-directory failure impossible. Unknown shapes go to quarantine and are counted.
3. **Compaction** (`scripts/ops/lake_compact.py`). It is scheduled after the 12:05 export and runs as a single writer under a filelock.
   - It unions the bus export with every known FileLedger root.
   - It dedupes by `uid`, or by a per-family content key for old rows.
   - It repairs broken surrogate characters to U+FFFD and counts them.
   - It writes zstd Parquet with pyarrow and an explicit schema to `state/lake/segments/<stream>/<yyyy-mm>/`, via tmp then replace.
   - It updates `manifest.json` with rows per source, disagreements, repairs and cursors.
   - Segments are never rebuilt or dropped, following the Eye's rule (`core/eye/index.py:91-104`).
4. **Query door `lake`.**
   - Subcommands: `status` (the manifest), `ask <named question>` (a SQL template plus a stdlib twin), and later `sql` (CLI-only, operator-gated).
   - Engine: DuckDB `:memory:`, opened and closed on every call, with about 1 GB memory limit and 4 threads. Spill goes to a disk-backed directory, not the X: ramdisk, because spilling into RAM defeats the purpose.
   - Hot JSONL is parsed by Python and handed to DuckDB as Arrow, so both engines share one parser. Parquet is read natively.
   - Fallback when DuckDB is absent: stdlib, plus pyarrow for Parquet.
   - Every answer carries a coverage frame (sources, rows each, time span, disagreements, repairs, lag, engine used) and a `BoundaryOutcome`.
   - Why DuckDB over the Polars we already have: agents write SQL fluently; SQL's JSON operators read the nested `fields.data`; and `ATTACH eye.db (READ_ONLY)` enables the Eye join. Because the archive is Parquet, the engine can be swapped later without moving data.

**Smallest first slice (L1):** `py agent_cli.py lake ask prevention --days N [--engine duckdb|stdlib|both]` plus an MCP twin `lake_ask`. It covers the `recall:outcome` family only, is read-only, and does no compaction.

**Acceptance tests (registered before the build):**
1. `--engine both` gives identical per-week with-lesson and without-lesson counts from both engines.
2. On a frozen copy of today's files, the 09-10 to 09-24 15:00 UTC window unions to **18,199 rows**, split as 18,170 Redis, 17,701 main file, 88 worktree, 410 lost from files, 29 only in the file.
3. `--days 60` reports "earliest 2026-08-08" instead of silently shrinking the window.
4. Six parallel processes × 20 runs produce no crash and identical output, and main-file loss does not rise.
5. The door-parity, MCP-defaults, boundaries and comprehensibility checks stay green, and peak memory stays under 500 MB.

**Risks:**
- Content-key dedup is only approximate for legacy rows that have no `uid`.
- Until L0 lands, the lake's own reads could make FileLedger's replace fail on Windows. The lake should prefer the bus export, or open FileLedger files with delete-sharing allowed.
- The daily export means up to 24 hours of lag; the coverage frame must state it.
- DuckDB on Windows is not fully mature (#613 is open), which is why the stdlib twin exists.
- Scope creep into becoming a database team.

**Next slices:**
- L2: compaction plus `lake sql`.
- L3: the Eye join for the "complied" verdict.
- L4: named bus-analytics questions, deduped by message hash.
