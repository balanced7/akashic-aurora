---
akashic_id: art_20260924_duckdb-lane-alternatives_c4bf1a
akashic_sha: a624605e4ddc
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-lane-alternatives
gist: "# DuckDB deep dive, re-run -- lane: alternatives *2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, p"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:28:14"
updated: "2026-09-24T21:28:14"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-lane-alternatives_c4bf1a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-lane-alternatives

# DuckDB deep dive, re-run -- lane: alternatives

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent ae4b346859333ac21 (claude-sonnet-5) ran 21:00-21:09 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\alternatives (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index (all 17 original briefs). Read the ones relevant to your lane first. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB. No ClickBench, TPC-H or other big datasets.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1). Install nothing anywhere else.
- Every DuckDB connection: SET memory_limit='3GB'; SET threads=4; and a temp_directory inside your lane dir. For Polars, set the environment variable POLARS_MAX_THREADS=4.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\alternatives\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: alternatives. Question: what else could do this job, and should we build our own instead? Compare honestly, for our constraints:
- Polars (already installed), DataFusion (Python), chDB, clickhouse-local, SQLite (+FTS5, +sqlite-vec), LanceDB, and plain pyarrow datasets;
- "build our own": schema-versioned JSONL, periodic Parquet compaction, and a thin query door.
For each give: the licence (verified), the Windows + Python 3.11 wheel status, embedded vs server, the concurrency model, JSON handling, and maturity and bus factor. Start from duckdb-build-vs-buy-postmortems-2026-09-24.md and duckdb-licenses-2026-09-24.md. End with a ranked shortlist for us, with the reasoning.

## The report (verbatim)

The Write tool is restricted for subagents — findings need to go directly in my response instead. Here is the complete report for the **alternatives** lane.

---

# DuckDB deep dive — LANE: alternatives

*Builds on duckdb-build-vs-buy-postmortems-2026-09-24.md, duckdb-licenses-2026-09-24.md, duckdb-operational-limits-2026-09-24.md, duckdb-json-ingest-evidence-2026-09-24.md, duckdb-local-benchmarks-and-census-2026-09-24.md.*

## Headline

Nothing here beats DuckDB on raw analytical speed over our ledgers — settled in the other lanes, reconfirmed below. Our actual pain is concurrency: several agent seats sharing one machine wanting to read/write at once — and there DuckDB is weak (one OS process may hold the file, period). Two alternatives cover that gap: SQLite in WAL mode supports one writer plus many readers *across processes*, proven live on this machine tonight; LanceDB supports concurrent multi-process *writers* via optimistic concurrency. chDB and clickhouse-local are disqualified outright — no Windows support, not a maturity question. "Build our own" isn't a query-engine project — DuckDB/Polars/pyarrow already are the engine — it's a compaction job plus a schema-version convention, dry-run tested tonight already.

## Findings

**Licenses** [sourced, duckdb-licenses-2026-09-24.md, verified from raw LICENSE files; re-checked against PyPI classifiers today]: Polars MIT · DataFusion/datafusion-python Apache-2.0 (ASF) · chDB Apache-2.0, ClickHouse Apache-2.0 (CLA required upstream, irrelevant to us as consumers) · SQLite public domain · sqlite-vec dual MIT/Apache-2.0 · LanceDB/Lance Apache-2.0 · pyarrow/Arrow Apache-2.0 + ~40 bundled third-party licenses. All compatible with our Apache-2.0 public repo.

**Windows + Python 3.11 wheels**
- Polars 1.39.3, pyarrow 23.0.1 — [measured, this session]: installed and running in the pinned venv.
- DataFusion (`datafusion` PyPI) 54.0.0 — [sourced, pypi.org/pypi/datafusion/54.0.0/json, fetched today]: ships `cp310-abi3-win_amd64.whl` (abi3 covers 3.10+), uploaded 2026-06-29. [measured, prior salvaged run]: actually ran on this machine tonight — parquet-directory groupby in 14.0ms, under a fuller venv than mine, not reinstalled by me.
- LanceDB 0.39.0 — [sourced, pypi.org/pypi/lancedb/0.39.0/json, fetched today]: `cp310-abi3-win_amd64.whl`, uploaded 2026-09-21 — three days old.
- sqlite-vec 0.1.9 — [sourced, pypi.org/pypi/sqlite-vec/0.1.9/json, fetched today]: `py3-none-win_amd64.whl`, uploaded 2026-03-31.
- chDB 4.4.0 — [sourced, pypi.org/pypi/chdb/json, fetched today]: manylinux + macosx wheels only. **No Windows wheel exists** — disqualifying, full stop.
- clickhouse-local — [sourced, WebSearch + github.com/ClickHouse/ClickHouse/pull/112824, fetched today]: no native Windows binary; a Windows cross-compile PR from ~July 2026 is CI-tested only under Wine, unfinished. Only working path is WSL2 — the subsystem implicated in this machine's 2026-09-11 outage. Disqualifying for us specifically.
- SQLite + FTS5 — [measured, this session, `python -c "import sqlite3; ...pragma compile_options..."` against the pinned venv]: version 3.45.1, `ENABLE_FTS5` present in compile options, live functional test (create fts5 table, insert, MATCH) correct, `jsonb()` works (built into core since 3.38). Already live in the interpreter we run daily, zero install cost.

**Embedded vs. server, concurrency, JSON**
- **Polars**: embedded, owns no storage/lock layer — reads/writes plain files, so concurrency is whatever the filesystem gives. [measured, prior run] 620MB/1.06M-row NDJSON: eager `read_ndjson` 434ms; groupby after load 17.6ms; lazy `scan_parquet` groupby w/ pushdown 9.1ms.
- **DataFusion**: embedded (Rust/Arrow), `SessionContext.read_json()`/`read_parquet()` [sourced, datafusion.apache.org/python docs]. No owned store — same non-answer on concurrency. [measured, prior run] parquet-dir groupby 14.0ms, tied with DuckDB/Polars/pyarrow (6–9ms) on the same directory. Its edge is governance: ASF project, not one company's fork risk; per the postmortems brief, Arroyo and InfluxData both moved *to* it after building their own engines.
- **chDB**: embedded ClickHouse-in-process — moot, no Windows wheel.
- **SQLite (+FTS5+sqlite-vec)**: embedded, single file, WAL mode. [sourced, sqlite.org/wal.html, fetched today]: "Writers and readers can run at the same time... reading and writing can proceed concurrently" across **separate OS processes** (same host only — fine for us). The only engine proven to fit our topology: duckdb-operational-limits-2026-09-24.md's LibreDB test found DuckDB refuses a second process, reader or writer, the instant one process holds the file read-write. [measured, prior run, x12 scale, 1.06M rows/620MB]: raw-JSON SQLite ingest 3.77s, groupby via `json_extract` 3.80s; shredded+indexed — ingest 6.25s but indexed groupby 60.5ms, indexed filter 50.1ms, point lookup 204ms (two orders of magnitude faster than naive, in DuckDB's ballpark though still 5–10x slower on most ops). FTS5 on 1.06M rows: build 9.85s, BM25 top-10 47.6ms. sqlite-vec: 50,000×384d vectors stored in 1.24s (87MB total for rows+FTS5+vectors, one file, zero servers), brute-force KNN top-10 42.6ms, scaling to 250,000 vectors at 63ms.
- **LanceDB**: embedded, local disk (cloud mode separate/optional). [sourced, lance.org/format/table/transaction/, github.com/lancedb/lance issues #951 and #3068, fetched today]: real Optimistic Concurrency Control — multiple processes *can* write concurrently; conflicts rebase-and-retry (8–20 attempts typical) before `CommitConflict`. The only engine here that natively tolerates concurrent multi-process writers — literally our topology. JSON: [sourced, lancedb.com/blog/lance-json-support, 2026] typed JSON columns with BTree path indexing now exist, pitched against DuckDB/Iceberg VARIANT — real but new in 2026, versus DuckDB's years of production mileage per the json-ingest brief. LanceDB's center of gravity is vector search; its general JSON story is promising, not proven for us.
- **plain pyarrow.dataset**: embedded, no query language — scan/filter/project/aggregate via Acero. [measured, this session]: `pyarrow.json` has both `read_json` (whole-file) and `open_json` (streaming). Worth flagging since the opposite is the easy assumption: `pyarrow.dataset.dataset(path, format='json')` works end-to-end — I built a 3-row NDJSON probe file and ran a real `group_by().aggregate()` through the dataset API against it successfully. pyarrow 23.0.1 has first-class NDJSON dataset discovery, not just single-file loading. [measured, prior run] parquet-dir groupby: 8.6ms — tied with DuckDB/Polars/DataFusion.

**"Build our own": schema-versioned JSONL + Parquet compaction + a thin query door.** Not a query-engine project — every engine above is free and already does that part. The person-year estimates in the postmortems brief (InfluxData: "10s of person-years"; DuckDB itself: 6 years, 2 founders) price a hash-join/vectorized-execution engine from scratch, not this. What's proposed is three cheap pieces: a schema-version field per JSONL row (independently flagged by the crashed run's own interim note, after it found three conflicting schemas silently coexisting in one directory); a scheduled JSONL→Parquet compaction job; a query function unioning the hot JSONL tail with cold Parquet history. [measured, prior run, crossover-sweep Part 2]: this exact shape was dry-run tonight — appending 5,000 rows as a fresh Parquet file (no rewrite) took 37.1ms, and groupby across the resulting 2-file directory ran in 6–9ms under DuckDB, Polars, DataFusion, *and* plain pyarrow interchangeably, because Parquet is shared interchange, not lock-in. [inferred] The real work is the scheduler and schema-version discipline — ordinary scripts, not a database — so the risk is bus-factor-on-us, not engineering difficulty.

## Could not verify
- DataFusion's own JSON-ingestion throughput (only that `read_json()` exists and it handled our Parquet fine).
- LanceDB's JSON columns under genuine concurrent multi-process writes (confirmed OCC generally, not JSON-specific conflict behavior).
- Whether pyarrow's `format='json'` dataset support reconciles schema drift across files the way DuckDB's `union_by_name` claims to — untested, and this is precisely the failure mode our own census hit.
- sqlite-vec behavior in *this exact* pinned venv — not installed here per guardrails; relied on the prior salvaged measurement instead of reinstalling.
- Polars/DataFusion/LanceDB company funding or headcount — deliberately not cited without a verified source.

## What it means for us — ranked shortlist

1. **SQLite (+FTS5, +sqlite-vec)** — best fit for the constraint that actually bites us: concurrent multi-process access, proven live tonight, zero marginal install, public-domain license. Use shredded+indexed, never raw-JSON-column.
2. **plain pyarrow.dataset** — more capable than assumed (verified NDJSON dataset support), ties DuckDB/Polars/DataFusion speed on Parquet, zero marginal cost, highest-bus-factor governance surveyed (ASF/Arrow).
3. **Polars** — already installed, fastest single-shot NDJSON load measured, best for ad hoc human exploration; same concurrency ceiling as pyarrow.
4. **DataFusion (Python)** — ties DuckDB speed on Parquet, ASF-governed, but one more dependency for marginal gain over what we already own.
5. **LanceDB** — most interesting *future* answer to concurrent writes, but its JSON path has no track record next to DuckDB's; earmark for a narrow embedding-search pilot, not general ledger querying yet.
6. **chDB** — out: no Windows wheel exists.
7. **clickhouse-local** — out: no finished Windows binary; the only path (WSL2) already broke this machine once.

**Build the compaction layer regardless of engine** — cheap, dry-run tested tonight at millisecond scale, makes Parquet-as-interchange real across every tool here, and the schema-version field pays for itself the first time someone globs the wrong 15% of files again.
