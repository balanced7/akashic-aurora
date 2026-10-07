# DuckDB deep dive, re-run -- lane: capabilities

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent a6edad235f04172e1 (claude-sonnet-5) ran 21:00-21:15 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\capabilities (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index (all 17 original briefs). Read the ones relevant to your lane first. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB. No ClickBench, TPC-H or other big datasets. Use our own ledgers, or generated data under 1 GB.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1). Install nothing anywhere else.
- Every DuckDB connection: SET memory_limit='3GB'; SET threads=4; and a temp_directory inside your lane dir. For Polars, set the environment variable POLARS_MAX_THREADS=4.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\capabilities\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: capabilities. Question: what can current DuckDB (1.5.x stable, 2.0-alpha) actually do for OUR data and constraints? Cover:
- newline-delimited JSON reading: the read_json/read_ndjson options union_by_name, sample_size, maximum_object_size, ignore_errors and format;
- globbing and hive partitioning;
- Parquet + zstd export;
- the Python API: relations, Arrow zero-copy, Polars interop;
- the extensions we would need (json, parquet, fts, vss), and whether they work offline on Windows;
- storage-format stability and backward compatibility across versions: can 1.5 read 1.3 files, and what changes in 2.0;
- WAL and crash safety;
- the known open Windows bugs (for example duckdb-python #613).
Start from duckdb-operational-limits-2026-09-24.md.

## The report (verbatim)

This confirms the report is complete and saved at `C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\capabilities\REPORT.md`. My final answer follows, in full.

---

# DuckDB deep dive -- LANE: capabilities (2026-09-24)

Question: what can current DuckDB (1.5.5 stable / 2.0-alpha) actually do for our 904 JSONL ledgers (364 MB, 969k rows) under our constraints (Windows 11, Python 3.11, several agent processes, no new Docker/servers)? Builds on duckdb-operational-limits, duckdb-json-ingest-evidence, duckdb-licenses, duckdb-local-benchmarks-and-census (2026-09-24) -- not re-litigating memory/write-concurrency/WAL except where a capability test produced new evidence. Local tests: pinned venv (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1, Python 3.11.9), memory_limit=3GB, threads=4, temp_directory in-lane.

## Headline

DuckDB handles our actual 3-shape bus-export schema drift correctly by default -- union_by_name made no measurable difference in three separate tests, which pushes back on the open worry from the census note. The real schema-drift landmine is sample_size (default 20,480): a field that first appears after row 20,480 in a file vanishes from results with zero warning. Parquet+zstd shrinks our ledger data ~4.5x and exports in ~200ms for 224k rows. The Python API (lazy relations, zero-copy Arrow, direct Polars scanning) is as frictionless as advertised. json/parquet are compiled in (zero network, ever); fts/vss are one ~22MB one-time download each, then fully offline -- but fts needs manual reindexing after inserts and DuckDB's own docs call persisted vss/HNSW unsafe across an unexpected shutdown, which matters on a machine that already lost power once tonight.

## Findings

**JSON reading options**

- [measured] union_by_name=false vs =true produced IDENTICAL results in 3 tests: (a) real state/bus-export/*.jsonl, 388 files/223,910 rows, two genuinely different nested fields struct shapes (message vs event); (b) synthetic 2-file type conflict on one key (name VARCHAR vs INTEGER); (c) synthetic asymmetric top-level keys (file B has a column A lacks). Conflicting types for the same name were silently widened to VARCHAR, not errored, either way.
- [sourced] duckdb.org/docs/current/data/json/loading_json.html (fetched today): union_by_name = "Whether the schemas of multiple JSON files should be unified" (default false) -- docs do not specify default behavior without it. My empirical result is the best evidence I have; flagging as a real doc gap, not just a test gap.
- [measured] sample_size default 20,480 silently drops a column that first appears after row 20,480 in a file -- no error, row count unaffected (30,000/30,000 returned), the column simply isn't in the schema. sample_size=-1 (full scan) catches it. This is the concrete mechanism behind "our rows gained fields over time" -- our largest ledger file today is 6,029 rows (events_claude_raw.jsonl, per the census), so we are not bitten yet, but any file crossing ~20k rows is at risk.
- [measured] ignore_errors=false hard-fails the whole read on the first malformed line (reproduced on a frozen copy of session_logs/ledger/recall_outcome.jsonl, "invalid high surrogate in string"). ignore_errors=true recovered 20,000/20,000 rows, 0 reported dropped -- it repairs/passes through bad string content rather than skipping the row. Row counts under ignore_errors=true are not proof of clean data.
- [measured] contradicts [sourced]: docs give maximum_object_size default as 16,777,216 bytes (16 MB, confirmed via duckdb_functions() introspection as a real UINTEGER parameter) -- but a 20 MB object read successfully under the default, and a 2 MB object still succeeded even with an explicit 1 MB cap. Could not get this parameter to reject anything. Unresolved -- see gaps below.
- [measured] format='auto' and format='array' both correctly read a JSON-array file. Forcing format='newline_delimited' on that same file did not error -- it silently returned 1 row instead of 3. Wrong format fails quiet, not loud.

**Globbing + hive partitioning**

- [measured] COPY ... (FORMAT PARQUET, PARTITION_BY (dt, agent)) wrote a real dt=.../agent=.../data_0.parquet tree; read_parquet('.../**/*.parquet', hive_partitioning=true) correctly reconstructed both partition columns with dt auto-typed as DATE. Multi-file JSONL globbing works throughout this report (the 388-file bus-export glob). Windows note: EXPLAIN's box-drawing output crashes Python's print() under the default cp1252 console codepage -- PYTHONIOENCODING=utf-8 fixes it.

**Parquet + zstd export**

- [measured] 223,910 rows (bus-export, unioned): uncompressed parquet 102.19 MB, snappy 45.11 MB, zstd 22.86 MB (about 4.5x vs uncompressed), export 146-221 ms for any codec. Codec confirmed via pyarrow metadata (ZSTD). Roundtrip read_parquet() row count matched exactly. Same order of magnitude as local-benchmarks-and-census's separate 620 MB run (59.3 MB zstd there).

**Python API**

- [measured] con.sql() returns a lazy DuckDBPyRelation: building + chaining .filter().aggregate() took ~0-1 ms (no execution); .fetchall() ran the actual 224k-row group-by in 5.2-5.5 ms.
- [measured] Zero-copy interop needs no registration call: an in-memory pyarrow.Table and a polars.DataFrame were both queried directly by Python variable name (select ... from tbl) via DuckDB's replacement scan.
- [measured] relation.arrow() returns a streaming pyarrow.RecordBatchReader (not a materialized Table) in 1.5.5; relation.fetch_arrow_table() returns a materialized pyarrow.Table directly; relation.pl() returns a polars.DataFrame directly. All schema-preserving, all confirmed working.

**Extensions offline on Windows (json, parquet, fts, vss)**

- [measured] duckdb_extensions() confirms json, parquet, icu are install_mode='STATICALLY_LINKED' -- compiled into the binary, LOAD takes 0.0 ms, zero network ever.
- [measured] fts/vss are NOT_INSTALLED by default. With autoinstall/autoload disabled and no prior cache, LOAD fts fails cleanly ("Extension .../fts.duckdb_extension not found"). A normal INSTALL fetched fts in 676 ms (22.6 MB) and vss in 515 ms (22.4 MB) on this connection, both under the 100 MB guardrail. After that one-time fetch, reloading with autoinstall/autoload OFF succeeded in ~30 ms with zero network: both are genuinely offline-capable after one download, from a plain local file cache, no daemon.
- [measured] FTS smoke test: PRAGMA create_fts_index + fts_main_docs.match_bm25() correctly ranked 3 seed docs; a 4th row inserted after index creation scored NULL (not picked up).
- [sourced] duckdb.org/docs/current/core_extensions/full_text_search.html (fetched today): "The FTS index will not update automatically when the input table changes. A workaround of this limitation can be recreating the index to refresh." Matches the smoke test exactly. 26 stemmers, configurable stopwords/tokenizer.
- [measured] VSS smoke test: HNSW index built on an in-memory table (metric='cosine', hnsw_enable_experimental_persistence=true); array_distance nearest-neighbor query returned the correct 2/3 nearest vectors.
- [sourced] duckdb.org/docs/current/core_extensions/vss.html (fetched today): VSS is still explicitly "an experimental extension"; HNSW needs hnsw_enable_experimental_persistence=true to persist at all on-disk, and without proper WAL-recovery handling an unexpected shutdown "could cause data loss or corruption of the index" -- production use of persisted HNSW is discouraged. Deletes are soft-marked (stale index, needs PRAGMA hnsw_compact_index()). Metrics: l2sq, cosine, ip. The index's RAM does not count toward memory_limit -- another operation outside operational-limits' buffer-manager accounting.

**Storage format stability**

- [sourced] duckdb.org/docs/current/internals/storage.html (fetched today): storage version 68 = v1.5.x, 67 = v1.4.x, 66 = v1.3.x, 65 = v1.2.x. Backward compatibility guaranteed since v0.10: "any DuckDB version released after can read files created by previous versions" -- so yes, 1.5 reads 1.3 files, no export/import needed. Forward compatibility (older version opening a newer file) is only "best effort" and "may be (partially) broken on occasion." The current-docs page does not yet mention 2.0 (consistent with 2.0 still being alpha).
- [sourced] (via operational-limits, corroborated) v2.0's own preview post describes its new default storage format as backward-incompatible, with EXPORT DATABASE / IMPORT DATABASE as the documented migration; storage_compatibility_version can pin the old format per-ATTACH.

**Windows / Python 3.11**

- [measured] Direct proof cp311-win_amd64 wheels exist and work end-to-end: this entire lane ran duckdb 1.5.5 inside Python 3.11.9 with zero compilation or native-dependency friction -- resolves operational-limits' open item #7.
- [sourced] (via operational-limits) duckdb-python #613 (2026-09-06): access violation during concurrent read-only multi-process queries on Windows, reproduced on 1.4.4 and 1.5.5, open at research time; not re-checked tonight.

## What I could NOT verify

- Why union_by_name showed no observable difference in any of my 3 tests -- docs don't specify default (false) behavior for JSON; tested only to 223,910 rows/388 files, cannot rule out divergence at larger scale or with STRUCT/LIST conflicts on the same key.
- What maximum_object_size actually gates -- exists (confirmed via introspection) but never rejected an oversized object, default or explicit override.
- HNSW persistence across an actual restart (close connection, kill process, reopen file) -- built and queried an index in-process but did not test the crash/reopen path the docs warn about.
- Live status of duckdb-python #613 tonight (relied on operational-limits' same-night finding).
- Hive-partition filter pruning plan text -- blocked by a Windows console encoding issue on EXPLAIN; the partitioned read's correctness was verified, the pruning plan itself was not inspected.

## What it means for us

DuckDB's default JSON reading already does the right thing for our actual schema drift -- the union_by_name fear from the interim census note did not reproduce against DuckDB (only against Polars' narrower inference). The one setting worth changing by default is sample_size=-1, since the default silently drops late-arriving columns past row 20,480 -- cheap insurance for files that are currently small but growing. json+parquet need nothing beyond the pip wheel: genuinely zero-footprint, matching "no new servers." fts and vss are one small download each, then fully offline, and both work in a few lines of SQL -- but fts needs an explicit rebuild after inserts and vss's only on-disk persistence path is labeled unsafe by DuckDB itself across an unexpected shutdown, not where I'd park anything we can't afford to lose on a machine that crashed from memory exhaustion tonight. The Python API is exactly the right shape for many agent processes reading the same append-only data read-only, no ingestion step required. Storage format is a non-issue on the 1.x line (backward-compat guaranteed since v0.10); the only migration cost is a one-time EXPORT/IMPORT if/when we move to 2.0.
