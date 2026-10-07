# DuckDB deep dive -- fan-out index (17 agents, 2026-09-24)

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" Which agents finished, which were cut off, and each one's full brief. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

| agent | local span | status | report |
|---|---|---|---|
| aca6bd957a46cddf1 | 19:43-20:24 | cut off | (none -- partial work only in transcript) |
| a29b173363ec1de8f | 19:43-20:21 | cut off | (none -- partial work only in transcript) |
| a3ea1014fea4c7b97 | 19:44-20:23 | cut off | (none -- partial work only in transcript) |
| a254eeeb659eed119 | 19:45-19:59 | FINISHED | duckdb-operational-limits-2026-09-24.md |
| a9e6cf2c4f2a948cd | 19:45-20:22 | cut off | (none -- partial work only in transcript) |
| ac03edf4b7fdb15b6 | 19:45-19:53 | FINISHED | duckdb-licenses-2026-09-24.md |
| abf02ddd76ddc4ae3 | 19:45-20:24 | cut off | (none -- partial work only in transcript) |
| a688c8cd1cd0d7e42 | 19:47-19:53 | cut off | (none -- partial work only in transcript) |
| a9aaf9780dd51d339 | 19:47-20:23 | cut off | (none -- partial work only in transcript) |
| a4fb6949817e220e2 | 19:48-19:58 | FINISHED | duckdb-json-ingest-evidence-2026-09-24.md |
| a04008f5ab760e981 | 19:48-20:23 | cut off | (none -- partial work only in transcript) |
| af810b435734000c0 | 19:48-20:11 | FINISHED | duckdb-build-vs-buy-postmortems-2026-09-24.md |
| ab19e773fa74b9246 | 20:07-20:23 | cut off | (none -- partial work only in transcript) |
| a7fa0c1b2e25b3f84 | 20:08-20:24 | cut off | (none -- partial work only in transcript) |
| a0748f20a0cffa8f6 | 20:08-20:23 | cut off | (none -- partial work only in transcript) |
| a786400d5d2ad6fcf | 20:10-20:24 | cut off | (none -- partial work only in transcript) |
| a4234aa9655e1fcd3 | 20:11-20:24 | cut off | (none -- partial work only in transcript) |

## Full briefs

### aca6bd957a46cddf1 (cut off)

Deep-dive DuckDB as of 2026-09-24. Use WebSearch and WebFetch extensively — current information with sources and measured numbers, not priors. Verify the license from the actual repo LICENSE file, not a blog.

Target environment, which constrains everything: Windows 11 desktop, Python 3.11 PINNED (3.12 is reserved for a separate ROCm audio venv), AMD GPU (ROCm, no CUDA), consuming project is Apache-2.0 and PUBLIC, and the operator strongly prefers NO new Docker containers (a kernel-pool outage took WSL and Docker down on this machine on 2026-09-11, and an existing SearXNG container is already a maintenance surface).

Cover:

1. WHAT DUCKDB ACTUALLY IS AND IS NOT. In-process OLAP, columnar, vectorized. Where it beats SQLite and where SQLite still wins. Be precise about the OLAP/OLTP split and concurrency model — specifically: what happens with multiple processes/writers, since several agent processes share one machine here and would all want to read/write. Single-writer? MVCC? What are the actual documented limits?

2. THE FEATURES THAT MATTER FOR QUERYING APPEND-ONLY LOGS. We have JSONL ledgers (bus events, fetch receipts, lessons, task state) and Parquet is not currently used. Can DuckDB query JSONL/NDJSON in place without ingest? What about globbing many files, schema inference, and schema DRIFT across a file's lifetime (our JSONL rows have gained fields over time — this matters a lot)? Full-text search extension? Vector/embedding support (VSS)? What's its story for incremental/streaming append?

3. VERSION AND STABILITY. What's the current version, what changed recently, and critically: is the on-disk file format stable across versions now, or does upgrading still require export/import? That has bitten people historically — get the current answer with a source.

4. PYTHON 3.11 + WINDOWS. Confirm wheels exist. Install footprint. Any native-dependency pain. Does it need a compiler?

5. MEASURED PERFORMANCE on realistic small-to-medium data (millions of rows, not TPC-H marketing). Find independent benchmarks, and flag vendor-published ones as such.

6. THE HONEST LIMITS. When is DuckDB the wrong tool? Memory behaviour on larger-than-RAM data, write concurrency, operational gotchas, anything about long-running processes holding connections.

Return a structured assessment with a clear recommendation, explicit about what you could NOT verify.

### a29b173363ec1de8f (cut off)

Research the ALTERNATIVES to DuckDB and the honest build-vs-buy question, as of 2026-09-24. Use WebSearch and WebFetch extensively — current info with sources. Verify licenses from actual repo LICENSE files.

Context: Windows 11, Python 3.11 pinned, Apache-2.0 public project, strong preference for NO new Docker containers. The data is append-only JSONL ledgers on local disk (events, receipts, lessons, task state) plus a Redis instance already in use for live state. The question the operator asked is literally "how we can leverage it OR BUILD AN EQUIVALENT FOR OURSELVES" — so take the build option seriously rather than dismissing it.

Cover:

1. THE IN-PROCESS ANALYTICAL FIELD: DuckDB, chDB (ClickHouse in-process), Polars, Apache DataFusion (+ its Python bindings), Apache Arrow, and SQLite (with and without extensions). For each: license from the real LICENSE file, Windows + Python 3.11 wheel availability, install footprint, and what it is genuinely best at. Include anything new in 2025-2026.

2. SQLITE AS THE DARK HORSE. It is already everywhere, needs nothing, and has FTS5 for full-text and JSON1 for JSON. Where does plain SQLite actually fall short for analytical queries over millions of JSONL rows, and where is "just use SQLite" the correct boring answer? Find measured comparisons, not opinions.

3. WHAT "BUILD AN EQUIVALENT" WOULD ACTUALLY MEAN. Be concrete and honest: what does a columnar vectorized query engine involve, and what is the realistic minimum useful subset a small project could build (e.g. a JSONL→index→query layer, not a database)? What do people who tried this report? I want a real answer about scope, not a reflexive "never build it".

4. THE MIDDLE PATH. Is there a shape where we use Parquet as the storage format and something light as the query layer, keeping the data readable by many tools? What does Arrow buy us as an interchange format independent of engine choice?

5. AGENT-MEMORY / RAG ANGLE: is anyone using these engines as the substrate for agent memory or retrieval in 2026? Vector search support in each (DuckDB VSS, sqlite-vec, etc.) — licenses and maturity.

Return a structured comparison with a clear recommendation on leverage-vs-build, explicit about what you could NOT verify.

### a3ea1014fea4c7b97 (cut off)

Research task: find MEASURED, INDEPENDENT performance benchmarks for DuckDB as of September 2026. Use WebSearch and WebFetch extensively (load them via ToolSearch with query "select:WebSearch,WebFetch" first). Do NOT rely on your priors — everything you report must come with a URL.

I need numbers for realistic small-to-medium data — millions of rows, single desktop machine — NOT TPC-H/TPC-DS marketing charts. Specifically hunt for:

1. Independent third-party benchmarks (blog posts, academic papers, community repos) comparing DuckDB vs SQLite, vs pandas, vs Polars, vs ClickHouse-local, vs plain Python/JSON parsing. Prioritize ones that state hardware, dataset size, row counts, and wall-clock seconds.
2. ClickBench (clickbench.com) results — note that it's hosted by ClickHouse (a competitor), so flag the vendor bias direction. Get actual relative numbers for DuckDB if you can.
3. The h2oai db-benchmark (duckdblabs/db-benchmark fork) — note this fork is maintained by DuckDB Labs, so flag it as vendor-published. Get groupby/join timings at the 0.5GB and 5GB scales.
4. JSON/JSONL specific benchmarks: how fast does DuckDB's read_json/read_ndjson parse newline-delimited JSON compared to Python's json module, pandas.read_json, or jq? Anything measuring rows/sec or MB/s.
5. Benchmarks on WINDOWS specifically, if any exist — most are Linux. Note if you find evidence of Windows being slower.
6. Any benchmark showing DuckDB performance DEGRADING or losing — e.g. to SQLite on point lookups / small queries, or high per-query startup overhead, or single-row insert throughput.

For each benchmark report: the URL, who published it (and whether they have a stake in the outcome), the date, hardware, dataset, and the actual numbers. Explicitly tell me which claims you could NOT verify with a primary source. Be skeptical — if a blog cites a number without methodology, say so.

Return your findings as your final message (no files). Be detailed and quantitative.

### a254eeeb659eed119 (FINISHED)

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

### a9e6cf2c4f2a948cd (cut off)

Today is 2026-09-24. You are gathering EVIDENCE ONLY (numbers and sources, no recommendation). Load web tools first: ToolSearch query "select:WebSearch,WebFetch".

TASK: Find MEASURED, sourced comparisons (not opinions) of SQLite vs DuckDB (and vs Polars/chDB/DataFusion where available) for ANALYTICAL queries over millions of rows. I need actual numbers with URLs.

Specifically hunt for:
1. The DuckDB team's own published SQLite comparison and any independent replications. Also "duckdb vs sqlite benchmark" posts from 2024, 2025, 2026 with actual timings and row counts.
2. ClickBench (benchmark.clickhouse.com / github.com/ClickHouse/ClickBench) — the current standings as of 2026 for DuckDB, chDB, SQLite, Polars, DataFusion, and what hardware/dataset (hits, 100M rows). Report relative numbers. Note ClickBench is run by ClickHouse (conflict of interest) — say so.
3. TPC-H / H2O.ai db-benchmark (now maintained by DuckDB Labs at duckdblabs.github.io/db-benchmark/) — current results for Polars vs DuckDB vs DataFusion at 5GB/50GB scale as of 2025/2026.
4. Any measured data on SQLite FTS5 performance at scale (millions of docs): index size ratio, query latency, and known limits. Search sqlite.org/fts5.html for documented limitations.
5. SQLite JSON1 / JSONB performance: SQLite 3.45 (Dec 2023) introduced JSONB. Find measured speedups and current SQLite version as of 2026. Check sqlite.org/changes.html or releaselog.
6. Measured numbers on JSON/JSONL ingestion throughput: DuckDB read_json_auto vs SQLite json_each vs Polars scan_ndjson. Any benchmark posts.
7. Any benchmark where SQLite WINS or is adequate — point lookups, small data, write throughput, single-row inserts. I specifically want the honest "where SQLite is fine" evidence.
8. Storage size comparisons: JSONL vs SQLite table vs Parquet (zstd) vs DuckDB native for the same dataset. Compression ratios with sources.

For each finding give: the number, the dataset/row count, the hardware if stated, the date, and the URL. Flag benchmarks that are vendor-run. Flag anything you could not verify. Do NOT summarize into a recommendation — just the evidence table.

### ac03edf4b7fdb15b6 (FINISHED)

Today is 2026-09-24. You are gathering EVIDENCE ONLY (no judgment, no recommendation). Use WebFetch/WebSearch heavily. Load them first with ToolSearch query "select:WebSearch,WebFetch".

TASK: Verify the ACTUAL license of each project below by fetching the RAW LICENSE file from its real repository (raw.githubusercontent.com/... /LICENSE or /LICENSE.txt or /COPYING). Do NOT trust a README badge, a PyPI classifier alone, or a blog post — fetch the actual license text and report the first ~5 lines plus which license it is (Apache-2.0 / MIT / BSD-3 / PSF / public domain / dual, etc.) and the copyright holder line. Also note if there is a separate license for extensions or a CLA.

Projects and repos:
1. DuckDB — github.com/duckdb/duckdb (LICENSE) — AND separately the DuckDB `vss` extension (github.com/duckdb/duckdb-vss) and `fts` extension, and duckdb-python bindings repo (github.com/duckdb/duckdb-python) if it exists as a separate repo in 2026.
2. chDB — github.com/chdb-io/chdb (LICENSE) — and note that it embeds ClickHouse: fetch github.com/ClickHouse/ClickHouse LICENSE too. Report BOTH. ClickHouse is Apache-2.0 but confirm from the file.
3. Polars — github.com/pola-rs/polars (LICENSE)
4. Apache DataFusion — github.com/apache/datafusion (LICENSE) and its Python bindings github.com/apache/datafusion-python (LICENSE)
5. Apache Arrow — github.com/apache/arrow (LICENSE.txt) and arrow-rs if relevant
6. SQLite — sqlite.org copyright page (https://www.sqlite.org/copyright.html) — public domain; confirm exact wording
7. sqlite-vec — github.com/asg017/sqlite-vec (LICENSE) — note it may be dual Apache-2.0/MIT
8. sqlite-vss (the older one) — github.com/asg017/sqlite-vss (LICENSE) and its status (deprecated?)
9. Apache Iceberg / pyiceberg if you have time — github.com/apache/iceberg-python
10. LanceDB / Lance — github.com/lancedb/lancedb and github.com/lancedb/lance (LICENSE)
11. sqlite3 in CPython stdlib — note the module is PSF-licensed wrapper over public-domain SQLite; check what SQLite version ships with CPython 3.11 on Windows (search for it).
12. Any "DuckDB license change" or "relicensing" news in 2025-2026 — search explicitly for whether DuckDB changed license or introduced a commercial/BSL component (DuckDB Labs, MotherDuck). Report facts only.

Report as a compact table: project | repo URL of LICENSE fetched | license identified | copyright holder | notes. Flag anything you could NOT fetch. Include exact URLs.

### abf02ddd76ddc4ae3 (cut off)

Today is 2026-09-24. EVIDENCE ONLY, with sources. Load web tools: ToolSearch query "select:WebSearch,WebFetch".

TASK: Find first-hand accounts and authoritative material on what it ACTUALLY takes to build a columnar/vectorized query engine or a lightweight query layer, so I can give an honest scope estimate rather than a reflexive "never build it".

Hunt for:
1. Andy Pavlo / CMU 15-721 "Advanced Database Systems" course material on vectorized execution, and the MonetDB/X100 paper "MonetDB/X100: Hyper-Pipelining Query Execution" (Boncz, Zukowski, Nes 2005) — the foundational vectorized-execution paper DuckDB is based on. Get the key claims about vector size (~1024 tuples) and why it beats tuple-at-a-time.
2. "How Query Engines Work" by Andy Grove (the DataFusion creator) — his book about building a query engine from scratch. What does he say the minimum components are? Find the table of contents / chapter list. URL: likely howqueryengineswork.com or github.com/andygrove/how-query-engines-work.
3. DuckDB's own published stats: lines of code, number of contributors, years of development, team size at DuckDB Labs. Search for "duckdb lines of code" and the DuckDB paper "DuckDB: an Embeddable Analytical Database" (Raasveldt & Mühleisen, SIGMOD 2019) and the 2024/2025 follow-ups.
4. Blog posts by people who BUILT a small query engine or analytical layer themselves — e.g. "I built a database", "writing a query engine in Rust/Python", "toy columnar database". Especially anyone who reports how long it took and what they got wrong. Look for posts from 2023-2026.
5. The specific hard parts people report: query planning/optimization, join algorithms (hash join, spilling to disk), out-of-core/larger-than-memory execution, correct NULL semantics, decimal/date types, string handling, parallelism. Find sources that enumerate these.
6. The "minimum useful subset" evidence: projects that are deliberately NOT full databases but do the indexing job — e.g. Python's `ijson`, `orjson`, jsonl indexing libraries, `tantivy`/`tantivy-py`, `Whoosh`, `bm25s`, simple inverted-index libs, `numpy`+`mmap` approaches, `zstd` seekable frames, `pyarrow.dataset` partition pruning. Which of these are maintained in 2026, licenses, and Windows/Python 3.11 wheel availability.
7. Any account of a team who built their own and later ripped it out for DuckDB/ClickHouse (or vice versa). Postmortems are gold.
8. Rough numbers on how long a hash-join + filter + aggregate engine over Parquet takes to build — any source that estimates effort.

Report findings with URLs, dates, and direct quotes where they are load-bearing. No recommendation — evidence only.

### a688c8cd1cd0d7e42 (cut off)

You are gathering EVIDENCE ONLY — measured, sourced numbers with URLs. No recommendations, no opinions. Today is 2026-09-24.

First load web tools: ToolSearch with query "select:WebSearch,WebFetch".

TASK: Find MEASURED benchmark evidence for where SQLite WINS or is fully adequate versus DuckDB (and Polars/DataFusion where available). This is the honest "SQLite is fine here" counter-evidence hunt. Specifically:

1. Point lookups / indexed single-row SELECT by primary key — any benchmark showing SQLite faster than DuckDB. Look for the DuckDB docs' own admissions, e.g. duckdb.org/docs "DuckDB is not intended for OLTP / high-volume single-row updates". Quote exact wording and URL.
2. Single-row INSERT / write throughput and transaction rates. SQLite's own speed claims: check sqlite.org/fasterthanfs.html (SQLite reads small blobs ~35% faster than filesystem, ~20% less space — get the EXACT figures, test setup, and date), sqlite.org/np1queryprob.html, and sqlite.org/whentouse.html.
3. Benchmarks where DuckDB is SLOWER than SQLite: small result sets, small datasets (thousands of rows), high-frequency small writes, concurrent writers, insert-heavy loops. Search e.g. "duckdb slower than sqlite insert", "duckdb single row insert performance", "duckdb OLTP benchmark".
4. DuckDB's documented concurrency limits (single-process write, one writer) — find the exact statement in duckdb.org docs about concurrency and multiple processes.
5. Any blog post or forum thread with actual timings showing SQLite beating DuckDB, with row counts.

Also check https://www.lukas-barth.net/blog/sqlite-duckdb-benchmark/ — it is reported to benchmark "simple queries" and may show SQLite winning on some. Extract its actual numbers, query types, row counts, hardware, and date.

For EACH finding report: the number, the dataset/row count, hardware if stated, the date, and the URL. Flag vendor-run benchmarks (SQLite.org is vendor for SQLite; duckdb.org is vendor for DuckDB). Flag anything you could NOT verify (e.g., page unreachable, number only appears in an aggregator's summary and not on the source page).

Return a plain evidence list in your final message. Do NOT write any files. Do NOT give a recommendation.

### a9aaf9780dd51d339 (cut off)

You are gathering EVIDENCE ONLY — measured, sourced numbers with URLs. No recommendations. Today is 2026-09-24.

First load web tools: ToolSearch with query "select:WebSearch,WebFetch".

TASK: Find MEASURED storage size / compression comparisons for the SAME dataset stored as: raw JSON/JSONL, CSV, SQLite table, Parquet (especially zstd and snappy codecs), and DuckDB native format. I need compression ratios with sources.

Hunt specifically for:
1. ClickBench's published data sizes — the "hits" dataset (99,997,497 rows) in TSV vs Parquet vs each engine's native format. The ClickBench repo (github.com/ClickHouse/ClickBench) states the uncompressed TSV size and the Parquet size; get exact byte/GB figures. Also DuckDB's and SQLite's stored size for that dataset if published in the ClickBench results.
2. DuckDB blog posts on storage/compression: search duckdb.org for posts on lightweight compression (FSST, ALP, dictionary, RLE), e.g. "duckdb.org/2022/10/28/lightweight-compression", "duckdb.org ALP floating point compression", and any post giving before/after sizes. Get exact compression ratios.
3. Parquet zstd vs snappy vs uncompressed measured ratios — any benchmark post with the same dataset in each codec and resulting file sizes.
4. JSON/JSONL vs Parquet size reduction — measured numbers (e.g., "X GB JSONL became Y GB Parquet").
5. SQLite database file size vs the source CSV/JSON for the same data — any measured figure. Also SQLite's own sqlite.org/fasterthanfs.html claim about space usage, and the sqlite-zstd / ZSTD-compressed SQLite figures if measurable.
6. DuckDB native .duckdb file size vs Parquet for the same data — any measured comparison.

For EACH finding report: the exact sizes, the dataset and row count, the compression codec, the date, and the URL. Flag vendor-run benchmarks (duckdb.org = DuckDB vendor, ClickHouse = ClickBench owner, sqlite.org = SQLite vendor). Flag anything you could NOT verify on the source page.

Return a plain evidence list in your final message. Do NOT write any files. Do NOT give a recommendation.

### a4fb6949817e220e2 (FINISHED)

You are gathering EVIDENCE ONLY — measured, sourced numbers with URLs. No recommendations. Today is 2026-09-24.

First load web tools: ToolSearch with query "select:WebSearch,WebFetch".

TASK: Find MEASURED JSON / JSONL / NDJSON ingestion and query throughput numbers comparing:
- DuckDB read_json_auto / read_ndjson
- SQLite json_each / json_tree / the JSON1 extension, and SQLite JSONB (introduced in SQLite 3.45.0, 2024-01-15)
- Polars scan_ndjson / read_ndjson
- (optional) ClickHouse/chDB JSONEachRow, pandas read_json

Hunt specifically for:
1. The DuckDB blog post on JSON support and any follow-ups with timings: search duckdb.org for "Shredding Deeply Nested JSON, One Vector at a Time" (duckdb.org/2023/03/03/json.html) and any newer JSON post. Extract: dataset, file size, row/record count, seconds to ingest, hardware, and any comparison to other tools.
2. Measured SQLite JSONB speedups vs JSON text. The SQLite 3.45.0 release (2024-01-15) introduced JSONB. Find any MEASURED numbers — check sqlite.org/json1.html (the JSONB section), sqlite.org/draft/jsonb.html, the sqlite-users mailing list / sqlite.org/forum, and blog posts benchmarking json_extract vs jsonb_extract. Get exact speedup multiples, dataset sizes, and dates. Note that SQLite's own claims are vendor-run.
3. Polars scan_ndjson / read_ndjson throughput benchmarks with MB/s or seconds for a stated file size.
4. Any head-to-head post benchmarking JSON ingestion across DuckDB vs Polars vs pandas vs SQLite with a shared dataset.
5. Any measured numbers on DuckDB's JSON type vs VARCHAR storage, or its automatic schema inference cost (sample_size parameter).

For EACH finding report: the number (seconds, MB/s, or speedup multiple), the dataset and record count, the file size, hardware if stated, the date, and the URL. Flag vendor-run benchmarks. Flag anything you could NOT verify on the source page — especially be suspicious of numbers that only appear in AI-generated-looking listicles; try to trace them to a primary source and say so if you cannot.

Return a plain evidence list in your final message. Do NOT write any files. Do NOT give a recommendation.

### a04008f5ab760e981 (cut off)

EVIDENCE-ONLY research task. Today is 2026-09-24. You have WebSearch and WebFetch available (load them first with ToolSearch query "select:WebSearch,WebFetch"). Do NOT make recommendations — gather evidence with URLs, dates, version numbers, and direct quotes.

GOAL: Survey the "minimum useful subset" libraries — projects that are deliberately NOT full databases but do the indexing/scanning job. For EACH library below, find: (a) current version and last release date as of 2026, (b) whether it is actively maintained in 2026, (c) license, (d) Windows + CPython 3.11 wheel availability on PyPI (check the PyPI "Download files" / classifiers for cp311 + win_amd64 wheels), (e) one sentence on what job it actually does.

Libraries to check:
1. ijson (streaming JSON parser)
2. orjson (fast JSON serialization)
3. tantivy-py (Python bindings for the Tantivy Rust full-text search engine) and tantivy itself
4. Whoosh (pure-Python search) — and note whether it is dead / whether Whoosh-Reloaded is the maintained fork
5. bm25s (fast BM25 in Python/numpy/scipy)
6. rank_bm25
7. pyarrow — specifically pyarrow.dataset partition pruning / predicate pushdown, and what it can and cannot do
8. zstandard python bindings + "seekable format" / seekable frames (note: is the seekable format available from Python? This is a known gap — check carefully and report what you find)
9. numpy memmap / np.memmap for out-of-core arrays
10. sqlite FTS5 (built into CPython's sqlite3?) — check whether the stdlib sqlite3 on Windows CPython 3.11 ships with FTS5 enabled
11. duckdb python package itself (version, wheel availability, license) — for comparison
12. polars (version, license, wheels) — for comparison
13. lancedb / lance format — if it appears relevant
14. Any maintained "jsonl index" / "jsonl random access" library (search for: jsonl indexing library python random access line offset index)

Use PyPI JSON API where useful: https://pypi.org/pypi/<name>/json gives version + release info, and https://pypi.org/project/<name>/#files shows wheels. WebFetch on the PyPI JSON endpoint is efficient.

Report as a compact table-like list per library with the URLs you used. Flag clearly anything you could NOT verify. Direct quotes where load-bearing.

### af810b435734000c0 (FINISHED)

EVIDENCE-ONLY research task. Today is 2026-09-24. You have WebSearch and WebFetch available (load them first with ToolSearch query "select:WebSearch,WebFetch"). Do NOT make recommendations — gather evidence with URLs, publication dates, and DIRECT QUOTES. Postmortems are the goal.

GOAL: Find first-hand accounts of teams who BUILT their own query engine / analytical storage layer / custom columnar store and later RIPPED IT OUT and replaced it with DuckDB, ClickHouse, Polars, or DataFusion — or the reverse (replaced a vendor engine with something they built). Engineering-blog postmortems, conference talks, HN threads with author participation.

Search angles to try (use many):
- "we replaced our custom query engine with DuckDB"
- "we built our own database and regretted it"
- "migrating from our in-house analytics engine to ClickHouse"
- "we rewrote our query layer" postmortem
- "why we stopped building our own" database engine
- "replaced pandas with DuckDB" / "replaced our custom aggregation engine"
- "lessons learned building a database" 2023 2024 2025 2026
- Hacker News: "Show HN" toy database / query engine posts where the author reports effort in the comments
- "we moved off DuckDB" / "why we left ClickHouse" (the reverse direction)
- Companies known for this: Sentry, Cloudflare, Grafana, PostHog, Motherduck, Fivetran, Hex, Rill Data, Turso, Evidence.dev, Ibis, SigNoz, Quesma, Tinybird

ALSO hunt for: any source that estimates HOW LONG it takes to build a hash-join + filter + aggregate engine over Parquet. Look for people stating person-months / person-years, or "it took me N weekends", or blog series where the author dates their posts so elapsed time can be inferred.

For each find, report: URL, author, date, and the load-bearing DIRECT QUOTE about effort, duration, team size, or what broke. Prioritize 2023-2026. Flag anything you could not verify or where the date is uncertain.

### ab19e773fa74b9246 (cut off)

Today is 2026-09-24. EVIDENCE ONLY with URLs and dates. Load web tools: ToolSearch query "select:WebSearch,WebFetch".

TASK: Research who is actually using in-process analytical engines as the substrate for AGENT MEMORY and RETRIEVAL in 2025-2026, and the current state of vector search in each.

Part A — vector search extensions, maturity and license:
1. **DuckDB VSS extension** — is it still "experimental" in 2026? Fetch github.com/duckdb/duckdb-vss README and duckdb.org/docs/stable/core_extensions/vss (or current URL). Key questions: does the HNSW index persist to disk (there was a known limitation requiring `SET hnsw_enable_experimental_persistence=true`)? Is that still the case in DuckDB 1.5.x? Does it support deletes/updates? What is the index build memory profile?
2. **sqlite-vec** — current version, is it still pre-1.0? Fetch github.com/asg017/sqlite-vec README. Does it have ANN (approximate) indexing yet, or is it still brute-force/exhaustive KNN? There was a roadmap promising IVF/HNSW. What is the current status, and what row counts is brute force practical to? Any published benchmarks. Also: is the project still actively maintained in 2026 (last commit/release date)? Note Alex Garcia's employment/funding status if stated publicly.
3. **LanceDB / Lance format** — maturity, is it embedded (no server)? Windows support? What is the actual disk format and does it interop with Parquet/Arrow?
4. **Other 2025-2026 embedded vector options**: usearch, hnswlib, faiss (Windows wheels?), chromadb (still embedded?), Qdrant embedded mode, pgvector (needs Postgres so out of scope but note), turbopuffer, Vectorlite (sqlite ext). For each: license, Windows+py3.11 wheel, maintained?
5. **DuckDB full-text search (fts extension)** vs SQLite FTS5 vs tantivy vs bm25s — for BM25 keyword retrieval. Which are production-usable in-process on Windows?

Part B — agent memory in practice:
6. Search for 2025-2026 writeups of agent memory systems built on DuckDB, SQLite, or Parquet. Terms: "agent memory duckdb", "sqlite agent memory", "sqlite-vec agent memory", "LLM memory layer sqlite", "episodic memory store LLM local". Find real projects (mem0, Letta/MemGPT, Zep, Cognee, LangGraph checkpointer/store, Claude Code's own memory, OpenAI Swarm) and note what STORAGE each actually uses. Is anyone using DuckDB for this?
7. Is there 2025-2026 evidence on **hybrid retrieval** (BM25 + vector + recency/metadata filters) being the winning pattern for agent memory, vs pure vector? Find sources with measurements if possible — e.g. BEIR results showing BM25 competitive, or reranking papers.
8. Any evidence about the scale at which pure brute-force vector search stops being fine (e.g. "under 100k vectors just brute force it") — with numbers.

Report as evidence tables with URLs and dates. Flag vendor-authored content. No recommendation.

### a7fa0c1b2e25b3f84 (cut off)

Today is 2026-09-24. You have web tools available via ToolSearch — load them FIRST with: ToolSearch query "select:WebSearch,WebFetch".

RESEARCH TASK (evidence only, URLs + dates required, no recommendations):

Find 2025-2026 evidence of what STORAGE BACKEND real agent-memory / LLM-memory systems actually use. For each project below, establish the concrete persistence layer (SQLite? DuckDB? Postgres+pgvector? Parquet? Redis? proprietary?), whether it's embedded/in-process or server-based, the vector index used, and cite the URL + date (docs page, GitHub README, release notes, blog post).

Projects to cover (find the actual storage, from primary sources — docs or source code, not secondhand blog claims):
1. mem0 (mem0ai) — what vector store + what history DB? (I believe it uses SQLite for history + pluggable vector store — VERIFY and cite)
2. Letta (formerly MemGPT) — storage layer, SQLite vs Postgres, pgvector?
3. Zep / Graphiti — storage (Neo4j? FalkorDB? Postgres?)
4. Cognee — storage backends supported (does it support DuckDB, LanceDB, Kuzu?)
5. LangGraph checkpointer + BaseStore / langgraph-store — what backends ship officially (SQLite, Postgres, in-memory)? Does the Store support vector search and with what index?
6. LlamaIndex / Llama-Index memory modules and Chroma/DuckDB integrations
7. Claude Code's own memory (CLAUDE.md / memory tool) — what is it actually, files or a DB? Cite Anthropic docs.
8. OpenAI Swarm / Agents SDK — does it have persistent memory at all, and what storage?
9. Any others you find that matter in 2025-2026: e.g. Memori (GibsonAI), MemMachine, Supermemory, Byterover, Engram, txtai, Chroma, Redis agent memory server, AWS AgentCore Memory.

SPECIFIC QUESTION TO ANSWER EXPLICITLY: **Is ANYONE using DuckDB as the substrate for agent memory / retrieval?** Search terms: "agent memory duckdb", "duckdb llm memory", "duckdb agent retrieval", "duckdb vss agent", "duckdb rag 2026". Report what you find, including small/indie projects, blog posts, and HN/Reddit discussions — and note where DuckDB is used for ANALYTICS over agent logs vs as the live memory substrate. Distinguish the two.

Also note: any 2025-2026 writeups of "sqlite-vec agent memory" / "LLM memory layer sqlite" / "episodic memory store LLM local".

FLAG vendor-authored content explicitly (i.e. a blog post by the company that makes the product).

Output: markdown evidence tables with columns: Project | Storage substrate | Embedded or server | Vector index | Source URL | Date | Vendor-authored?
Then a short section answering the DuckDB question with the actual evidence found (or explicitly: "no significant evidence found, here is what searching turned up").

Do NOT write any files. Return findings as your final message.

### a0748f20a0cffa8f6 (cut off)

Today is 2026-09-24. You have web tools available via ToolSearch — load them FIRST with: ToolSearch query "select:WebSearch,WebFetch".

RESEARCH TASK (evidence only, URLs + dates required, no recommendations). Two questions:

=== Q1: HYBRID RETRIEVAL vs PURE VECTOR ===
Find 2025-2026 evidence (papers, benchmarks, engineering writeups with MEASUREMENTS) on whether hybrid retrieval — BM25/keyword + dense vector + recency/metadata filters, usually fused with Reciprocal Rank Fusion (RRF) — outperforms pure dense vector retrieval. Specifically hunt for:
- BEIR benchmark results showing BM25 competitive with or beating dense retrievers on out-of-domain tasks (cite the original BEIR paper AND any 2024-2026 follow-ups/updates). Get the actual nDCG@10 numbers where you can.
- MTEB retrieval leaderboard state in 2025-2026 and any critiques of it.
- Reciprocal Rank Fusion: the original Cormack et al. 2009 paper, plus 2024-2026 measurements of RRF gains over single retrievers (Elastic, Weaviate, Azure AI Search, OpenSearch all published numbers — get them, and FLAG them as vendor-authored).
- Reranking (cross-encoder / ColBERT / Cohere Rerank / bge-reranker) measured gains on top of hybrid.
- Any 2025-2026 papers or posts specifically about retrieval for AGENT MEMORY (not generic RAG) — e.g. does recency weighting / temporal decay matter, is there measured evidence? Look for "A-Mem", "MemGPT evaluation", "LongMemEval", "LoCoMo" benchmark results, "memory benchmark agents 2026".
- Any counter-evidence: papers arguing hybrid is NOT worth the complexity, or that BM25 alone is enough, or that long-context beats retrieval.

=== Q2: WHEN DOES BRUTE-FORCE VECTOR SEARCH STOP BEING FINE? ===
Find concrete NUMBERS on the scale at which exhaustive/flat/brute-force KNN vector search stops being practical and you need ANN (HNSW/IVF). Hunt for:
- sqlite-vec published benchmarks (Alex Garcia's posts + GitHub benchmarks) — latency at 100k / 500k / 1M vectors at various dimensions.
- FAISS documentation guidance on "when to use IndexFlat" vs IVF/HNSW (the FAISS wiki "Guidelines to choose an index" page has explicit thresholds — get them).
- usearch / hnswlib benchmark numbers.
- Any "just brute force it under N vectors" advice from credible engineering sources with the actual N and the latency measured, in 2024-2026.
- The arithmetic reality: brute force over N vectors of D dims = N*D float ops; find sources that state achievable throughput (GB/s memory bandwidth bound) so the scaling is derivable.
- Note dimension effects (384 vs 768 vs 1536 vs 3072) on the brute-force threshold.

Output: markdown evidence tables with URL + date + vendor-flag for every claim. Include actual numbers wherever available. Be explicit when you could NOT find a number rather than estimating.

Do NOT write any files. Return findings as your final message.

### a786400d5d2ad6fcf (cut off)

Today is 2026-09-24. Load web tools FIRST: ToolSearch query "select:WebSearch,WebFetch".

RESEARCH TASK (evidence only, URLs + dates, no recommendations). Target platform context that matters for every answer: **Windows 11 x64, Python 3.11, in-process/embedded (NO server process)**.

Build an evidence table for each of these embedded/in-process vector search options. For EACH, establish from PRIMARY sources (PyPI page, GitHub README, official docs, release history):
- Current version + release date (and date of last commit/release — is it maintained in 2026?)
- LICENSE (exact: MIT, Apache-2.0, BSD, AGPL, BSL, proprietary?)
- **Does a prebuilt Windows x64 wheel for CPython 3.11 exist on PyPI?** Check the PyPI "Download files" listing for win_amd64 + cp311 tags. This is critical — say YES/NO/UNCLEAR with evidence.
- Embedded (in-process library) vs requires a server/daemon process
- Index types supported (flat/brute-force, HNSW, IVF, DiskANN, PQ/quantization)
- Anything notable about persistence, deletes/updates, memory profile, filtering

Options to cover:
1. **usearch** (unum-cloud/usearch)
2. **hnswlib** (nmslib/hnswlib) — note: is it still maintained? Last release?
3. **faiss** (facebookresearch/faiss) — the Windows wheel question is the big one. Is there an official `faiss-cpu` wheel for Windows on PyPI? Who publishes it (kyamagu/faiss-wheels vs official)? What Python versions? Check PyPI faiss-cpu download files.
4. **chromadb** — is it STILL embeddable/in-process in 2026, or has it moved to client-server only? What did Chroma Cloud change? What index does it use now? License changes?
5. **Qdrant** — is there a genuine embedded/in-process mode for Python in 2026, or only `:memory:`/local-file mode in qdrant-client? What are its limits? License (Apache-2.0? any BSL move?)
6. **Vectorlite** (a SQLite extension, 1yefuwang1/vectorlite) — status, maintained? Windows? It wraps hnswlib I believe. Last release date.
7. **turbopuffer** — is it a hosted service only? (note as out-of-scope-if-so, with evidence)
8. **pgvector** — note that it requires a Postgres server, so it's out of scope for embedded; but confirm whether any embedded-Postgres option (pglite, pgserver, embedded-postgres-binaries) makes it viable in-process on Windows in 2026.
9. **LanceDB / lance format** — version, license, truly embedded (no server)?, Windows wheel for py3.11?, the on-disk format, and does it interoperate with Parquet/Arrow (can you read a Lance dataset with pyarrow/DuckDB)? Is there a DuckDB<->Lance integration?
10. Any others worth noting in 2026: e.g. `voyager` (Spotify), `annoy` (still maintained?), `milvus-lite`, `txtai`, `sqlite-vss` (the OLD deprecated one by Alex Garcia — confirm it is deprecated/superseded by sqlite-vec and cite that).

FLAG vendor-authored content (a company blogging about its own product).

Output: one big markdown table plus per-item notes where the table can't hold the nuance. URL + date on every claim. Where you cannot confirm something (especially Windows wheels), say "UNCONFIRMED" rather than guessing.

Do NOT write any files. Return findings as your final message.

### a4234aa9655e1fcd3 (cut off)

Today is 2026-09-24. Load web tools FIRST: ToolSearch query "select:WebSearch,WebFetch".

RESEARCH TASK (evidence only, URLs + dates, no recommendations). Platform context: **Windows 11 x64, Python 3.11, in-process / embedded, no server daemon.**

Compare the realistic options for BM25 / keyword (lexical) retrieval running IN-PROCESS on Windows. For each, from PRIMARY sources (official docs, GitHub README, PyPI):

1. **DuckDB `fts` extension** — fetch https://duckdb.org/docs/stable/core_extensions/full_text_search (or current URL). Key questions: is it BM25? Is the index a materialized snapshot that must be REBUILT after inserts (I believe `PRAGMA create_fts_index` builds a static index — CONFIRM and quote)? Does it auto-update on INSERT/UPDATE/DELETE? What stemmers/stopwords? Is it experimental? Does it persist? Quote limitations verbatim.

2. **SQLite FTS5** — fetch https://sqlite.org/fts5.html. Key questions: is BM25 built in (the `bm25()` auxiliary function)? Is it incrementally maintained on insert/update/delete (via triggers or contentless/external-content tables)? Is FTS5 compiled into the SQLite that ships with CPython 3.11 on Windows by default — this matters a lot, so find evidence about Python's bundled SQLite build flags (SQLITE_ENABLE_FTS5) on Windows. Also note the `contentless_delete` option and unicode61/trigram tokenizers. Any 2025-2026 changes.

3. **tantivy / tantivy-py** — license, maintained?, Windows+py3.11 wheel on PyPI?, is it BM25, is it embedded, how does the index persist, does it support incremental updates/deletes? Current version + date.

4. **bm25s** (xhluca/bm25s) — the pure-Python/scipy BM25 library. Current version, license, maintained?, published benchmark numbers (it claims big speedups over rank_bm25 — get the actual numbers and the source). Is the index persistable? Memory profile? Does it support incremental add/delete or is it batch-build-only?

5. **rank_bm25** — status, maintained in 2026?, performance reputation.

6. Any others: `Whoosh`/`whoosh-reloaded`, `pylucene`, `Xapian`, Meilisearch/Typesense embedded modes, `retriv`, `PyTerrier`, or `bm25-sparse`. Note which are viable in-process on Windows.

ALSO: find any 2025-2026 published comparison/benchmark of these (speed, index size, quality). And find whether DuckDB's FTS BM25 scoring has known quality issues or deviations from standard BM25.

Output: markdown evidence table (Tool | Algorithm | Embedded? | Windows+py3.11? | Incremental updates? | License | Version+date | Source URL) plus notes. FLAG vendor-authored content. Say "UNCONFIRMED" rather than guessing.

Do NOT write any files. Return findings as your final message.
