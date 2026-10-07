# DuckDB deep dive, re-run -- lane: skeptic

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent a1071a496537e2b6c (claude-opus-5-5) ran 21:01-21:18 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\skeptic (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index. Read them all. They are your opponents' evidence.

GUARDRAILS (hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe, with DuckDB memory_limit at most 3GB and threads at most 4. Install nothing anywhere else.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\skeptic\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then the verdict conditions. Under 1,500 words.

LANE: skeptic. Question: what is the strongest honest case AGAINST adopting DuckDB here? The interim note asked "whether we need it at all, given Polars and PyArrow are already installed and DuckDB is not." Steelman these four claims:
1. The real problem is schema discipline, not the engine.
2. Polars, pyarrow and SQLite already cover the need.
3. A new binary dependency costs wheel size, Windows bugs, storage-format churn and upgrade risk.
4. The house ethos prefers fewer moving parts.

Look for evidence both ways, on the web and in the salvaged reports. Output: the case against at full strength; the costs, with numbers where possible; the conditions under which DuckDB clearly wins; and the specific evidence that would flip your verdict. Be fair. A strawman is worthless to us, and so is contrarianism for its own sake.

## The report (verbatim)

## Skeptic lane: the case against adopting DuckDB (2026-09-24)

**Headline.** Don't adopt DuckDB now, either as a substrate or as the default reader. At our scale (950,685 JSONL rows today, and bus-export growing about 5k rows/day), engines we already have answer typical questions in under 300 ms once the data is loaded. This dive started because a reader answered confidently while seeing only part of the data. On our own data, DuckDB's default settings do the same thing. Fix the ledger contract first: it works with any engine and adds no binaries. After that, DuckDB is worth having only as a read-only query tool that never keeps a database file, under the conditions at the end. Two parts of the case against turned out weak: install size and import time.

### Findings

**Claim 1: the real problem is schema discipline, not the engine. Strong.**
- [measured] **New fields at the end of a file get dropped.** I copied the real 88,149-row `bifrost_broadcast.jsonl` and appended 500 rows with one new top-level key and one new key inside `fields`.
  - DuckDB with defaults showed neither new column, yet `count(*)` returned 88,649.
  - Polars with defaults did the same.
  - pyarrow with defaults showed both keys, 500 of 500.
  - `sample_size=-1` (DuckDB) and `infer_schema_length=None` (Polars) fix it.
  - Append-only ledgers gain new fields exactly there, at the end of long-lived files. (`m7_tailkey`)
- [sourced] DuckDB samples 20,480 rows by default. The docs don't say what happens to keys outside the sample, or what `ignore_errors` does to a bad row. (https://duckdb.org/docs/current/data/json/loading_json, fetched 2026-09-24)
- [measured] **A writer bug, and silent loss.**
  - `session_logs/ledger/recall_outcome.jsonl` is a live window that keeps the latest 20,000 rows. That is why DuckDB's error line moved between runs (221, then 26, then 14).
  - In a frozen copy, 7 rows contain garbled text in `$.event.t` (for example `âš ï¸\udc8f`), meaning the writer decoded text with the wrong encoding. Python's `json` accepts these rows. DuckDB in strict mode, Polars and pyarrow all refuse the file.
  - DuckDB with `ignore_errors=true` returns all 20,000 rows, but exactly those 7 come back entirely NULL, including their valid `id`. The salvaged row-count check (`raw_sum=66024 duckdb_sum=66024 diff=0`) therefore could not detect the loss.
  - DuckDB 1.5.5's JSON reader has no rejects table (`store_rejects` gives "Invalid named parameter"). Reading each line as text and running `json_valid` does flag exactly 7 of 20,000, but someone has to build that. (`m3c_snapshot`, `m6_rejects`)
- [measured] bus-export holds 5 different `fields` shapes across 223,910 rows, not the 3 the census found. Nothing in a row records which shape it is.
- [measured, from reading code] **The house already runs this pattern.** `core/eye/index.py` loads JSONL into SQLite with full-text search (FTS5), picks up only new lines on each run, carries a `schema_version`, and has a coverage contract that "refuses to claim wholeness past a gap". Its `eye.db` is 247.4 MB.

**Claim 2: Polars, pyarrow and SQLite already cover the need. Strong for pyarrow and SQLite; Polars is the weak leg.**
- [measured] pyarrow matches DuckDB's `union_by_name` (merging files by column name) on the real 388-file bus-export directory.
  - pyarrow, reading each file with `read_json` and then `concat_tables(promote_options="permissive")`: 223,910 rows, `frm` 160,948, `data` 62,962, all 13 keys inside `fields`, in 290 ms.
  - DuckDB: identical counts, including the rare keys `spot_tick` 59 and `frag` 4, in 339 ms. (`m3_drift`, `m3b_followup`)
- [measured] Polars cannot do this. Over the directory it inferred `Struct({'data': String})` even with `infer_schema_length=None`, then raised `StructFieldNotFoundError: frm`. That point goes to DuckDB.
- [measured, salvaged run under load] Once data is in Parquet, the engine barely matters: a group-by over the Parquet directory took 6.0 ms in DuckDB, 8.1 ms in Polars and 8.6 ms in bare pyarrow. At 1,057,788 rows, indexed SQLite ran group-by / filter / sum-by-group in 50.5 / 38 / 261 ms, against DuckDB's 6.1 / 4.7 / 3.6 ms. DuckDB is 8 to 70 times faster, but both are fast enough to use interactively.
- [measured] SQLite 3.45.1 ships with Python and includes FTS5 and JSONB. It is already imported by five production modules, and four of them in `core/` run in WAL mode. The house Python has Polars 1.39.3 and pyarrow 23.0.1 but not DataFusion or sqlite-vec; the salvaged benchmark loaded those from somewhere else.

**Claim 3: a new binary dependency has real costs. Mixed; size is not one of them.**
- [measured, sourced] **Size is a weak argument.**
  - The cp311 Windows wheel is 13,156,986 bytes with no required dependencies (https://pypi.org/pypi/duckdb/1.5.5/json, uploaded 2026-07-22).
  - Installed, DuckDB takes 36.7 MB. Polars and pyarrow, already installed, take 249.4 MB together.
  - Import plus connect adds 68 ms, against 190 ms for Polars, 388 ms for pyarrow and 4.7 ms for sqlite3.
  - In a clean test, the JSON and Parquet support is built into the wheel.
  - The fts, vss and httpfs extensions are separate 22-28 MB downloads for each DuckDB version. They land in `%USERPROFILE%\.duckdb`, outside any virtual environment, and tonight's cut-off run already left 120 MB there.
  - DuckDB installs extensions automatically by default (`autoinstall_known_extensions=true`; https://duckdb.org/docs/current/configuration/overview).
- [sourced] **A forced upgrade within about 8 weeks.**
  - Community support ends on 2026-11-01 for 1.5, and on 2026-11-17 for 1.4 LTS (the current long-term-support line). Version 2.0.0 is scheduled for 2026-10-21 (https://duckdb.org/release_calendar).
  - v2.0 "bumps the default storage format version to v2.0.0" and comes with "a small set of breaking changes" (https://duckdb.org/2026/08/17/duckdb-20-highlights).
  - The 2.0 alpha: "Extensions are not yet available for the Windows client", and alpha clients are "explicitly not production-ready" (https://duckdb.org/2026/09/02/try-duckdb-20-alpha).
- [sourced] **Windows crashes keep recurring.**
  - duckdb-python #613 was opened 2026-09-06 and is still open with no maintainer reply visible today. It reports memory access violations during concurrent read-only queries from multiple processes, on both 1.4.4 and 1.5.5, 38 crashes in one day, with the spatial extension loaded.
  - duckdb #21602 (2026-03-24) was an access violation that appeared in 1.5.0 and 1.5.1 but not in 1.4.x.
- [measured] **The same SQL gives different answers.** Of the 6 probes that ran on both SQLite and DuckDB, 5 disagreed:
  - `LIKE '%Bifrost%'` over the same 88,149 rows: 6,228 in SQLite, 171 in DuckDB, because SQLite's LIKE ignores case. This explains the salvaged 74,736 vs 2,052 caveat.
  - `7/2`: 3 in SQLite, 3.5 in DuckDB.
  - `1/0`: NULL in SQLite, `inf` in DuckDB.
  - NULLs sort first in SQLite and last in DuckDB.
  - A sum that overflows 64-bit integers: DuckDB widens the type and returns 9,223,372,036,854,775,808, while SQLite raises "integer overflow". (`m2_semantics`)

**Claim 4: the house prefers fewer moving parts. Strong for a shared database file, weak if DuckDB never keeps one.**
- [measured] Windows lock matrix on 1.5.5:
  - While any process has the file open for writing, no other process can open it, even read-only ("being used by another process").
  - Three read-only processes can share it when nobody is writing. This settles the salvaged report's biggest open question.
  - SQLite in WAL mode, as a control: another process reads normally while a write transaction is open.
  - So a DuckDB file shared by several seats needs one owning process in front of it, which is a server. (`m4_lock`)
- [sourced] By default each process that embeds DuckDB may use 80% of RAM and every CPU core (configuration overview). On a shared 61.6 GB machine that lost power to memory exhaustion tonight, every call site has to cap both.

**Where the case against is weak.**
- If DuckDB only queries files in memory and never keeps a database file, the lock, write-ahead-log and storage-format risks go away.
- `union_by_name` works on our data where Polars fails. SQL over raw files is the easiest surface for agents. Strict mode fails loudly. DuckDB is fast.
- The licence is MIT, and the code belongs to the DuckDB Foundation. DuckDB's company is joining AWS (announced 2026-08-26) with "no changes for our projects' roadmap, licensing, and governance model".
- SQLite has its own costs: a load step, and a WAL file that "will grow without bound" if some reader is always active (https://www.sqlite.org/wal.html).

### What I could NOT verify
- DuckDB's memory behaviour here without a cap; the guardrail limited it to 3 GB.
- Whether #613 happens on Python 3.11 without the spatial extension. I ran no multi-day test.
- Whether 2.0.0 will be a long-term-support release, or will ship Windows extensions at launch.
- Real growth. bus-export went from about 4.1k to 5.2k rows/day (August 8-31 vs September 1-24). That is only 7 weeks of history, and the underlying streams may be capped.

### Verdict conditions
**Now: don't adopt.** Land the contract first:
- a version field on every row;
- a check in the writer that rejects text that isn't valid UTF-8 (it would have stopped the 7 blanked rows);
- a declared schema for each stream;
- an eye-style index built from the ledgers.

That is days of work, adds no new binaries, and helps whichever reader wins.

**DuckDB clearly wins if any of these holds:**
1. Agents need ad-hoc joins or window queries across ledgers weekly or more often, and building an index per question becomes the bottleneck.
2. A type of query takes more than about 2 s on SQLite or pyarrow. [inferred] Sum-by-group took 261 ms at 1.06M rows, which suggests about 2.5 s near 10M rows. Counting bus-export alone, that is about 5 years away at a flat 5.2k rows/day, or about a year if the August-to-September growth (+28%) compounds every month.
3. It is used only to query files, behind one shared helper that pins the version, caps memory and threads, and uses `sample_size=-1` or declared columns.

**Evidence that would flip me to "adopt now":**
- A 72-hour test on this machine with at least 4 seats running DuckDB queries over the ledgers at once, and no access violations.
- The house's 10 most common real ledger questions, where DuckDB answers each in one statement and pyarrow or SQLite needs much more code or gets it wrong.
- v2.0 shipping Windows extensions, with a long-term-support line to pin.
- A JSON rejects table in DuckDB.

**Evidence that would harden the "no":** #613 reproducing on this machine with our workload.

The harness blocked me from writing `REPORT.md` as a subagent, so this message is the report. The measurement scripts and their logs, which serve as the crash-safe record, are in `C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\skeptic\`:
- `guard.py` (the shared memory, thread and no-download limits)
- `m1_env`, `m1b_cleanroom`, `m2_semantics`, `m3_drift`, `m3b_followup`, `m3c_snapshot`, `m4_lock`, `m5_growth`, `m6_rejects`, `m7_tailkey` (each as `.py` and `.log`)
- `snap_recall_outcome.jsonl`, the frozen copy that contains the 7 bad rows
