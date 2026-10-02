---
akashic_id: art_20260924_duckdb-json-ingest-evidence_bacde9
akashic_sha: 83869e3f6431
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-json-ingest-evidence
gist: "# DuckDB deep dive -- measured JSON/JSONL ingestion and query throughput *2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Dan"
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, bus, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:00:23"
updated: "2026-09-24T21:00:23"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-json-ingest-evidence_bacde9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-json-ingest-evidence

# DuckDB deep dive -- measured JSON/JSONL ingestion and query throughput

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" Agent a4fb6949817e220e2 ran 19:48-19:58 local and finished; full answer verbatim. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

## The question (verbatim brief)

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

## The answer (verbatim)

Evidence gathered. Compiling.

## EVIDENCE LIST — measured JSON/JSONL ingestion & query throughput

---

### 1. DuckDB — "Shredding Deeply Nested JSON, One Vector at a Time" (VENDOR-RUN)

**URL:** https://duckdb.org/2023/03/03/json.html
**Date:** 2023-03-03, author Laurens Kuiper. Page carries an "Updated December 2024" note.
**Hardware:** "a 2020 MacBook Pro with an M1 chip and 16 GB of memory"
**Dataset:** GH Archive, 2023-02-08, 24 hourly files. 2.3 GB gzipped; 18,396,198,934 bytes (~18.4 GB) uncompressed; 4,434,953 events.

| Operation | Time |
|---|---|
| `SELECT count(*) FROM 'gharchive_gz/*.json.gz'` (gzipped) | ~7.3 s |
| Same on uncompressed | ~5.4 s ("almost 2 seconds faster") |
| Count grouped by event type | ~7.4 s |
| `CREATE TABLE events AS SELECT * EXCLUDE (payload) …`, in-memory | ~9 s |
| Same, on-disk | ~13 s → DB size 444 MB |
| PR-events table with nested payload struct, in-memory | ~9 s (~8.5 s with `preserve_insertion_order = false`) |
| Same, on-disk | ~36 s (~27 s with `preserve_insertion_order = false`) → DB size 478 MB |

Derived (mine): 18.4 GB / 7.3 s ≈ **2.5 GB/s** on the gzipped count; 18.4 GB / 5.4 s ≈ **3.4 GB/s** uncompressed. Note this is a `count(*)`, not a full materialization.

**Important negative:** the post contains **no comparison to any other tool** (no pandas, ClickHouse, SQLite, Polars, jq). It states DuckDB uses **yyjson** internally. I found **no newer DuckDB blog post on JSON** — searches on duckdb.org returned only this post plus docs pages and the v2.0 preview.

---

### 2. SQLite JSONB — all claims traced

**2a. SQLite's own claims are vendor-run and thinly sourced.**

- https://sqlite.org/forum/forumpost/8687d4ad36b14ce9 — "JSONB — Request for evaluation and comment", D. Richard Hipp (drh), **2023-10-10**: `json_extract()` and `->` / `->>` are "**more than twice as fast**" when the LHS is JSONB; JSONB is "about **5% or 10% less disk space**, on average." **No dataset, no size, no methodology.**
- https://sqlite.org/forum/forumpost/fa6f64e3dc1a5d97 — "JSONB has landed", drh, **2023-12-05**: "you might see a **3-times performance improvement**, at least for the JSON-intensive operations"; "about 5% or 10% smaller"; non-JSON workloads "perhaps slightly (1%) faster." Points at "measurement scripts in the test/json subdirectory of the source tree" — **the numbers themselves are not published**, only the scripts (`json-speed-check.sh`, https://sqlite.org/src/dir?name=test%2Fjson).
- https://sqlite.org/json1.html — the JSONB section says only "smaller and faster than text JSON - **potentially several times faster**." **No numbers, no methodology.** So sqlite.org itself publishes *no* reproducible measurement.

**2b. Third-party measurement — Roger Binns, SQLite forum** (independent, not SQLite dev)
**URL:** https://sqlite.org/forum/forumpost/28e21085f9c6a4e7 — **2025-10-03 23:20:41**
CPU seconds, data from the `randomjson` extension plus Unicode text, SQLite fossil head:
- Python object → JSON text: **1.20 s**
- SQLite JSON → JSONB: **0.80 s**
- SQLite JSONB → JSON: **0.22 s**
- Python JSON text → Python object: **1.35 s**
- (his own) Python object → JSONB: **0.13 s**; JSONB → Python object: **0.48 s**
- **"The JSONB is 80% of the size of the JSON UTF8 bytes."** (i.e. ~20% smaller — larger than drh's 5–10% claim)
**Gap:** no file size, no record count, no hardware stated.

**2c. Third-party measurement — DoltHub, "JSON Showdown: Dolt vs SQLite"** (VENDOR-RUN for Dolt; SQLite numbers are third-party-measured)
**URL:** https://www.dolthub.com/blog/2024-11-18-json-sqlite-vs-dolt/
**Date:** 2024-11-18, Nick Tobey. **Hardware:** Apple M2 Pro, 32 GB RAM. **SQLite version not stated; no repetition count / harness stated.**
Dataset: Von Neumann ordinal documents generated by a recursive CTE, sized 64 KB × 8092 … 16 MB × 32 (total DB held roughly constant, ~436 MB text JSON).

This is the **best measured JSONB-vs-JSON-text evidence I found.** Seconds, SQLite JSON → SQLite JSONB:

| Doc size | Extract sub-value | Filter on key | Order by key | Create index | Copy w/ minor change |
|---|---|---|---|---|---|
| 64 KB × 8092 | 1.354 → **0.064** (21×) | 1.277 → **0.059** (22×) | 1.291 → **0.062** (21×) | 1.396 → **0.082** (17×) | 2.557 → **0.312** (8.2×) |
| 256 KB × 2048 | 1.316 → **0.055** (24×) | 1.326 → **0.053** (25×) | 1.283 → **0.054** (24×) | 1.300 → **0.060** (22×) | 2.853 → **0.572** (5.0×) |
| 1 MB × 512 | 1.412 → **0.056** (25×) | 1.353 → **0.055** (25×) | 1.312 → **0.053** (25×) | 1.361 → **0.062** (22×) | 2.997 → **0.601** (5.0×) |
| 4 MB × 128 | 1.390 → **0.067** (21×) | 1.394 → **0.070** (20×) | 1.381 → **0.067** (21×) | 1.380 → **0.074** (19×) | 2.870 → **0.411** (7.0×) |
| 16 MB × 32 | 1.958 → **0.180** (11×) | 1.936 → **0.189** (10×) | 1.933 → **0.210** (9.2×) | 1.923 → **0.183** (11×) | 3.614 → **0.732** (4.9×) |

(Speedup multiples are my arithmetic on their published numbers.) **These are 5×–25×, far above SQLite's own "2× / 3×" claim** — but note these are *read-path* queries on already-JSONB-encoded data, so the parse cost is fully avoided.

Disk space (units appear to be MB): SQLite JSON **436–437**, SQLite JSONB **286–299** → **JSONB ≈ 65–69% of text JSON size**, i.e. ~34% smaller. **This contradicts SQLite's own "5% or 10% smaller" claim** and also Binns' 80%. Flagging the three-way disagreement.

**Could not verify:** the blog's Test 1 (export) and Test 2 (**import/ingestion**) results are published **as graphs only — no numeric table**. So there is no extractable SQLite JSON *ingestion* number from this source.

**2d. Measured JSON perf regression (context, not JSONB)**
https://sqlite.org/forum/forumpost/15d6bd9cd37202a7 — a ~16% cachegrind regression / "~20% increase in time" on an `INSERT … json_each()` over a 200,000-object JSON array, between a July 21 snapshot and check-in 01d52232; fixed by check-in 837f2907e10b026f. Same thread: a different production JSON query was "about twice as fast" with the new code.

---

### 3. Polars `scan_ndjson` / `read_ndjson` — NO CREDIBLE MEASURED THROUGHPUT FOUND

This is a genuine gap, and I want to be explicit about it.

- **Polars publishes no NDJSON benchmark.** https://pola.rs/posts/benchmarks/ is PDS-H (TPC-H-derived, Parquet), not JSON. I checked https://pola.rs/posts/polars-in-aggregate-juli24/ (2024-07-25) and https://pola.rs/posts/polars-in-aggregate-apr26/ (2026-04-16): both mention NDJSON only as *features* — file caching for `scan_*`, the new sink pipeline for NDJSON/CSV/IPC in 1.37, cloud streaming for `scan_ndjson()`/`scan_lines()` in 1.39 — with **zero timings, MB/s, or memory figures** for NDJSON.
- **Docs** (https://docs.pola.rs/user-guide/io/json/, https://docs.pola.rs/api/python/stable/reference/api/polars.scan_ndjson.html) make only qualitative claims: NDJSON "can be read … in a much more performant way than standard json"; `read_ndjson().lazy()` is "an antipattern"; pass a path, not a file object.

**⚠️ UNVERIFIED — likely AI-generated SEO content.** The widely-echoed figure "**500 MB NDJSON: Polars `read_ndjson` 2.3 s vs pandas `read_json(lines=True)` 18.7 s, 8×, 40% less memory**" traces to exactly **one** page: https://www.application-architect.com/posts/how-to-read-json-files-in-polars/. I **could not load it** — the site's TLS certificate has expired. It appears in no primary source, states no hardware, no dataset, no Polars/pandas version, no date, and no author I could identify. **Treat as fabricated until proven otherwise.** Same for the circulating "scan_ndjson reduces memory 10x or more" line — no primary source.

- Nearest primary-ish Polars memory datapoint: https://github.com/pola-rs/polars/issues/21703 ("Can't load JSON file > 4GB in size") — a user reports DuckDB loading larger JSON with roughly **1/4 the RAM** of Polars. Anecdotal bug-report, no controlled measurement.

---

### 4. Head-to-head JSON ingestion across tools

**4a. NVIDIA — "JSON Lines reading with pandas 100x faster using NVIDIA cuDF" (VENDOR-RUN for cuDF; the pandas/pyarrow/DuckDB numbers are third-party-measured)**
**URL:** https://developer.nvidia.com/blog/json-lines-reading-with-pandas-100x-faster-using-nvidia-cudf/
**Date:** 2025-02-20. Authors: Karthikeyan Natarajan, Shruti Shivakumar, Gregory Kimball.
**Hardware:** NVIDIA H100 80 GB HBM3; Intel Xeon Platinum 8480CL, 2 TB RAM.
**Dataset:** 28 synthetic JSON Lines files, **8.2 GB total**, 200,000 records per file, 2–200 columns across seven configurations, file sizes ~10 MB to 1.5 GB, types `list<int>`, `list<str>`, `struct<int>`, `struct<str>`.

Total runtime over all 28 files:

| Library | Time (s) | Derived avg throughput (mine: 8.2 GB ÷ t) |
|---|---|---|
| pylibcudf | **1.5** | ~5.5 GB/s |
| cudf.pandas | **2.1** | ~3.9 GB/s |
| pyarrow (20 MB block, tuned) | **6.9** | ~1.2 GB/s |
| pyarrow (default) | **15.2** | ~540 MB/s |
| **DuckDB** | **62.9** | **~130 MB/s** |
| pandas (pyarrow engine) | **130** | ~63 MB/s |
| pandas (default) | **281** | ~29 MB/s |

Their stated per-configuration throughput ranges: cudf 2–6 GB/s; pyarrow 2–3 GB/s (5–20 cols), 0.6 GB/s (200 cols); **DuckDB 0.5–1 GB/s**; pandas-pyarrow ~70–100 MB/s; pandas-default ~40–50 MB/s. Speedups they state: cudf.pandas **133×** vs pandas default, **60×** vs pandas-pyarrow; pylibcudf **4.6×** vs pyarrow.

**⚠️ Internal inconsistency worth flagging:** their per-config DuckDB range (0.5–1 GB/s) cannot be reconciled with 62.9 s for 8.2 GB (~130 MB/s) unless total time is dominated by the wide-schema (200-column) files. Same tension for pandas. So the aggregate table and the throughput ranges are measuring different slices. **No Polars and no SQLite in this benchmark.**

**4b. ClickHouse JSONBench — "The billion docs JSON Challenge" (VENDOR-RUN by ClickHouse)**
**URL:** https://clickhouse.com/blog/json-bench-clickhouse-vs-mongodb-elasticsearch-duckdb-postgresql · repo https://github.com/ClickHouse/JSONBench
**Hardware:** AWS EC2 m6i.8xlarge — 32 cores, 128 GB RAM, 10 TB gp3, Ubuntu 24.04.
**Versions:** ClickHouse 25.1.1, MongoDB 8.0.3, Elasticsearch 8.17.0, **DuckDB 1.1.3**, PostgreSQL 16.6.
**Dataset:** Bluesky event stream, NDJSON. Blog says **482 GB uncompressed / 124 GB zstd**; the GitHub README says **125 GB compressed / "up to 425 GB" uncompressed** — ⚠️ the two ClickHouse sources disagree on uncompressed size.
Docs actually loaded at 1B scale: ClickHouse 999,999,258; MongoDB 893,632,990; Elasticsearch 999,998,998; **DuckDB 974,400,000**; PostgreSQL 804,000,000.

Storage after load (1B docs, best compression): ClickHouse (zstd) **99 GB** · MongoDB (zstd) **158 GB** · Elasticsearch (no `_source`, zstd) **220 GB** · **DuckDB (automatic compression) 472 GB** · PostgreSQL (lz4) **622 GB**.

Query times (1B): Q① count aggregation — ClickHouse 405 ms cold / 394 ms hot; Elasticsearch ~5 s; MongoDB ~16 min; **DuckDB ~1 hour**; PostgreSQL ~1 hour. Q② count + count_distinct — ClickHouse 11.85 s cold / 5.63 s hot; Elasticsearch 51.49 s cold / 45.51 s hot; **DuckDB ~1 hour**; MongoDB ~6 h; PostgreSQL ~9 h.

**⚠️ CRITICAL LIMITATION, stated by the benchmark itself:** the JSONBench README says *"The benchmark does not record data loading times. While it was one of the initial goals, many systems require a finicky multi-step data preparation process, which makes them difficult to compare."* So **JSONBench yields no ingestion-time numbers at all** — only storage size and query time. The repo also does not document which DuckDB ingestion path was used.

**4c. Third-party re-run:** https://greptime.com/blogs/2025-03-18-jsonbench-greptimedb-performance (2025-03-18, GreptimeDB — vendor-run for Greptime) re-runs JSONBench across ClickHouse, Elasticsearch, MongoDB, DuckDB, PostgreSQL, VictoriaLogs, StarRocks, SingleStore on m6i.8xlarge. **Results are presented as charts, not numeric tables** — I could not extract per-system seconds. Only stated figures: Q1 count ~165 ms at 100M docs computed from scratch; 4.522 ms with streaming Flow.

**4d. ClickHouse FastFormats — JSONEachRow ingestion (VENDOR-RUN)**
**URL:** https://fastformats.clickhouse.com/ · repo https://github.com/ClickHouse/FastFormats · raw result https://github.com/ClickHouse/FastFormats/blob/main/results/http_jsoneachrow_100000_unsorted_no_compression.json
Dataset: ClickBench web-analytics. Config: HTTP, JSONEachRow, 100 inserts × 100,000 rows = **10,000,000 rows**, no compression. Client m6i.8xlarge + 10 TB gp3; server ClickHouse Cloud 24.10, 30 vCPU / 120 GiB RAM × 3 replicas.
Raw measured values: total time incl. client loop **152 s**; total received bytes **23,007,797,971** (21.43 GiB); total written compressed **1,654,404,192** (1.54 GiB); median insert duration **1,292 ms**; median network-receive **359.28 ms**; median storage-write **248.57 ms**; median memory **435,248,594 B**; median CPU **1,599.46 ms**/insert; 6 threads.
Derived (mine): **~65,800 rows/s**, **~151 MB/s** ingest, ~13.9:1 compression. ⚠️ I corrected the automated extraction here — it produced "65.8 million rows/s" and "587 MiB/s", both wrong by ~1000× and ~4× respectively.

**4e. Altinity KB — format ingestion comparison (third-party, Altinity)**
**URL:** https://kb.altinity.com/altinity-kb-schema-design/ingestion-performance-and-formats/
100,000,000 rows × 3 columns (String, UInt64, Float64), `Engine=Null` so it measures **parsing only**:
Native 2.359 s real / 1.945 s user · TSV 2.693 / 14.066 · RowBinary 3.744 / 4.245 · CSV 3.296 / 18.145 · Parquet 4.905 / 5.478 · **JSONEachRow 8.872 / 30.235** · Avro 11.491 / 12.166.
Their conclusion: *"JSONEachRow is the worst format (user 0m30.235s) for this synthetic dataset. Native is the best."*
**Gap:** no hardware, no ClickHouse version, no date, no file size stated on the page.

---

### 5. DuckDB JSON type vs VARCHAR storage; schema-inference cost

- **Primary, factual (not a benchmark):** DuckDB docs — `read_json` / `read_json_auto` `sample_size` **default 20480**, described as "Option to define number of sample objects for automatic JSON type detection. Set to -1 to scan the entire input file"; `maximum_object_size` default **16777216** bytes. https://duckdb.org/docs/current/data/json/loading_json.html (the `/docs/stable/…` and `.md` URLs 404 or return redirect stubs — use `/docs/current/`). **The docs contain no measurement of schema-inference cost, and I found no benchmark anywhere quantifying the cost of `sample_size` = 20480 vs -1.**
- **The JSON logical type is physically stored as VARCHAR.** I could not get a clean quote — https://duckdb.org/docs/stable/data/json/json_type returned only a redirect stub and the `.md` variant 404s. The statement appears in search-index excerpts of the DuckDB docs ("logically similar to VARCHAR… Physically, the data is stored as a VARCHAR") but **I could not verify it on the rendered source page.** Flagging as unconfirmed-on-page.
- **Indirect but real measurement of the same fact:** JSONBench 4b above — DuckDB 1.1.3 needed **472 GB** of storage for a dataset whose raw NDJSON is ~425–482 GB, vs ClickHouse's 99 GB. ClickHouse's own framing: DuckDB stores JSON as *"plain strings rather than being decomposed or optimized for columnar storage."* Vendor-run and adversarial, but the storage figure is consistent with the VARCHAR-storage claim.
- **⚠️ UNVERIFIED / NOT AN OFFICIAL SOURCE:** https://duckdblab.org/en/post/duckdb-variant-type/ claims DuckDB VARIANT is "**5–10× faster than JSON text**" with "**~40% less space**", citing 10M rows of "simulated event logs", AMD Ryzen 9 7950X / 64 GB DDR5, DuckDB v1.5.0, "JSON text ~2 GB → VARIANT ~1.2 GB", "Full Scan + Nested Extract: JSON Text 8.4 s → VARIANT 0.9 s (9.3× speedup)". **duckdblab.org is NOT duckdb.org** — its own footer says "© 2026 DuckDB Lab — Independent DuckDB Technical Blog." No author name, simulated data, no dataset link, no generation script, no reproduction path. **Do not treat as a DuckDB source.** Other pages on that domain (`duckdb-json-nested-data`, `duckdb-json-auto-parse`) similarly surface in search with round-number claims like "3–10× faster than Python-based ingests" that trace to no primary source.
- **The official DuckDB v2.0 preview** (https://duckdb.org/2026/08/17/duckdb-20-highlights, 2026-08-17) describes VARIANT qualitatively only ("JSON on steroids", "compresses well in storage and executes fast in queries") — **no JSON/VARIANT numbers.** Its only benchmarks are unrelated: recursive-CTE reachability 4.90 s (v1.5.4) → 0.12 s (v2.0), and 2.2–2.6× on timezone/collation.

---

### 6. Head-to-head that turned out NOT to be about JSON (checked and excluded)

Several results that look on-topic are CSV/Parquet benchmarks with no JSON path, and circulating "JSON" numbers attributed to them are not in them: https://pola.rs/posts/benchmarks/ (PDS-H/Parquet), https://www.codecentric.de/en/knowledge-hub/blog/duckdb-vs-dataframe-libraries, https://ibis-project.org/posts/ibis-bench/. Medium/DEV listicles ("10 DuckDB Benchmarks That Challenge Warehouses", "We Benchmarked Pandas vs Polars vs DuckDB: Jaw-Dropping Results", "Polars vs Pandas 2026: 15x Speed Gap") produced figures like "3–10× faster than Python-based ingests", "2–10× wall-clock improvement staging to local SSD", "5×–50× on aggregation" — **none trace to a primary source and none are JSON-specific. I recommend discarding all of them.**

---

### Summary of what is NOT available (verified gaps)

1. **No published Polars NDJSON throughput number from any credible source.** The only circulating figure (2.3 s vs 18.7 s on 500 MB) is single-sourced to a site I could not load and that shows every sign of AI-generated SEO.
2. **No JSON-ingestion head-to-head that includes all four of DuckDB, Polars, pandas and SQLite on a shared dataset.** NVIDIA's covers DuckDB/pandas/pyarrow/cuDF but not Polars or SQLite. JSONBench covers DuckDB but deliberately does not time ingestion.
3. **SQLite publishes no reproducible JSONB benchmark** — only scripts and prose claims. The only hard JSONB-vs-JSON numbers are DoltHub's (query-side, 5–25×) and Binns' (conversion-side), and the three sources **disagree on the size saving** (5–10% per SQLite, 20% per Binns, ~34% per DoltHub).
4. **No measurement anywhere of DuckDB's `sample_size` schema-inference cost.**
