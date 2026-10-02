---
akashic_id: art_20260924_duckdb-lane-benchmarks_27a8fa
akashic_sha: 389f44cd38e7
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-lane-benchmarks
gist: "# DuckDB deep dive, re-run -- lane: benchmarks *2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:28:14"
updated: "2026-09-24T21:28:14"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-lane-benchmarks_27a8fa -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-lane-benchmarks

# DuckDB deep dive, re-run -- lane: benchmarks

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent acbbea7dd3c4c45f2 (claude-sonnet-5) ran 21:00-21:08 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\benchmarks (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index (all 17 original briefs). Read the ones relevant to your lane first. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB. No ClickBench, TPC-H or other big datasets, not even to read their size or tail. (Tonight a range request for the tail of a 16 GB file was ignored by the server and the whole file started streaming.) Read published results only.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe. Install nothing anywhere else.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\benchmarks\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: benchmarks. Question: what do INDEPENDENT, MEASURED benchmarks say about DuckDB versus Polars, DataFusion, chDB/ClickHouse and SQLite as of September 2026? Cover:
- ClickBench;
- the db-benchmark suite (formerly H2O, now run by DuckDB Labs, so flag the conflict of interest);
- TPC-H at SF1-100;
- any JSON-specific benchmarks.
For each result give who ran it, when, the hardware, the versions, and whether it is vendor-run or stale. The salvaged local-benchmarks file lists ClickBench result dates per system; use it to judge freshness. Start from duckdb-json-ingest-evidence-2026-09-24.md. Keep what applies at our scale (about 1M rows, 364 MB, many small files) separate from what applies at 100M+ rows.

## The report (verbatim)

## Lane: benchmarks — independent, measured DuckDB comparisons (Sept 2026)

Note: my tooling blocked writing REPORT.md to the lane directory (subagents here return findings as text, not report files) — so this message *is* the complete report, per the "final message must be the complete report" fallback.

### Headline

The four flagship public suites (ClickBench, db-benchmark, TPC-H/PDS-H, JSONBench) confirm DuckDB is a genuinely fast engine — but all four run at 10M–1B rows on Linux cloud boxes or Macs, not our regime. None tests our actual shape: ~1M rows across 904 small, schema-drifted JSONL files, on Windows. Our own already-salvaged local bench is the only evidence that matches our scale, and it's favorable: DuckDB queries land in single-digit milliseconds once loaded; even raw-JSONL queries with no import stay sub-250ms at 1M rows. Freshness is a live problem too: DuckDB's ClickBench entries are ~4.5 months stale, SQLite's are 14+ months stale, while ClickHouse (which hosts the benchmark) refreshes same-day.

### Findings

**ClickBench**
- **[sourced]** clickhouse.com/resources/engineering/fastest-olap-databases (dated 2026-05-27, fetched today). Hardware c6a.4xlarge (16vCPU/32GB), dataset = ClickBench `hits` table, 100GB/99.9M rows/105 cols. ClickHouse: median hot latency 148ms, 32/43 query wins, 0 failures, 5min load. DuckDB: median 348ms (2.35x ClickHouse), 10/43 wins, 0 failures, 2min load. Page self-discloses the conflict: "ClickHouse maintains both ClickBench and this page."
- **[measured/sourced]** Per-system result-refresh dates, salvaged from `duckdb-local-benchmarks-and-census-2026-09-24.md` (lines 905-932) and cross-checked by me via `github.com/ClickHouse/ClickBench/blob/main/CHANGELOG.md`, which confirms a 2026-05-11 "re-run 88 systems on every machine" event: DuckDB variants (duckdb/duckdb-parquet/duckdb-memory/duckdb-dataframe) last refreshed 2026-05-09 to 2026-05-11 (~4.5 months stale); ClickHouse refreshed today, 2026-09-24 (near-continuous back through July); chDB last 2026-08-16; Polars/pandas last 2026-08-24; **SQLite only ever refreshed 3 times — 2022-07-01, 2025-07-11, 2025-07-12** (14+ months stale; couldn't determine if that's neglect or an inability to finish the query set).
- **[sourced, vendor-run/DataFusion]** Apache DataFusion blog, 2024-11-18, Andrew Lamb, DataFusion 43.0.0, c6a.4xlarge, 14GB Parquet subset (not the full hits run): DataFusion beats DuckDB/chDB/ClickHouse-on-Parquet hot, but its own footnote admits DuckDB is faster cold. No absolute numbers extractable (chart image only). Nearly 2 years stale.
- **[inferred]** DuckDB's last full refresh predates the DuckDB 2.0 preview (2026-08-17), so today's public DuckDB ClickBench numbers reflect a pre-2.0 build.

**db-benchmark** (formerly H2O.ai, now run by DuckDB Labs — the conflict of interest the brief flagged)
- **[sourced]** duckdblabs.github.io/db-benchmark/, fetched today: "maintained by DuckDB Labs... took over from H2O.ai in 2023," confirmed in the vendor's own words. Scales 0.5/5/50GB (aka 1e7/1e8/1e9 rows). Hardware: "small" = c6id.4xlarge 16c/32GB; "x-large" = c6id.metal 128c/250GB. Latest report generated 2026-08-17, ~71.9hr runtime.
- **Gap:** no numeric group-by/join table extractable — results render as charts/images, same failure mode the JSON lane hit on Polars' own benchmark page.
- **[do not trust]** A circulating "DuckDB 2.3s vs Polars 3.3s on 5GB, Pandas OOM" figure has no traceable primary source — structurally identical to the fabricated Polars-NDJSON number the JSON lane already caught and discarded. Flagging, not using.

**TPC-H, SF1-100**
- **[sourced, vendor-run/Polars]** pola.rs/posts/benchmarks/, 2025-06-01, author Ritchie Vink (Polars' creator). PDS-H, "a derivative of TPC-H, not the official benchmark." Hardware c7a.24xlarge, 96vCPU/192GB, Ubuntu 22.04 LTS. Versions: Polars 1.30.0, DuckDB 1.3.0 (no DataFusion/ClickHouse tested). **SF-10**: Polars-streaming 3.89s · DuckDB 5.87s · Polars-in-memory 9.68s. **SF-100**: DuckDB **19.65s** · Polars-streaming 23.94s · Polars-in-memory **152.27s** (falls over — memory/cache-bound at 100GB). DuckDB 1.3.0 is ~1 year of releases behind current (1.5.5 stable/2.0 preview).
- **[sourced, disclosed COI]** ibis-project.org/posts/ibis-bench/, 2024-06-24 (>2yr stale). TPC-H-derivative, SF 1-128. Hardware GCP n2/n2d/c3 + M1/M2 Max MacBooks. Author discloses working at Voltron Data, described in-page as a DuckDB Foundation Gold Supporter. At SF128, DuckDB finished all 22 queries; Polars-via-Ibis finished 11.
- **[sourced, disclosed vendor bias]** docs.coiled.io/blog/tpch.html, base 2024-05-14, refreshed 2025-06-17. SF 10-10000. Hardware MacBook M1 + AWS M6i (32vCPU/128GB to 1280vCPU/5TB). Coiled sells Dask and says so outright: "we like Dask and know how to use it better... DuckDB: no one [tuned it]." Headline: "no project wins" universally. No extractable numeric table.
- **[too stale to use]** github.com/JayjeetAtGithub/datafusion-duckdb-benchmark pits DataFusion 32.0.0 vs **DuckDB 0.9.1** (~Sept 2023 build) — excluded as current evidence.

**JSON-specific** — already covered thoroughly by the finished `duckdb-json-ingest-evidence-2026-09-24.md` lane; summarizing rather than redoing:
- **[sourced]** DuckDB blog (2023-03-03/upd. Dec 2024, M1 Mac 16GB): 2.5-3.4GB/s on `count(*)` over GH Archive JSON — not full ingest, no cross-tool comparison.
- **[sourced, vendor/ClickHouse]** JSONBench (DuckDB 1.1.3, m6i.8xlarge): explicitly skips ingestion timing, measures storage+query only. DuckDB used 472GB for a ~425-482GB dataset vs ClickHouse's 99GB — consistent with DuckDB storing JSON as VARCHAR internally.
- **[sourced, vendor/NVIDIA]** 2025-02-20, H100+2TB-RAM host, 8.2GB synthetic JSONL: DuckDB ~130MB/s (62.9s), well behind tuned pyarrow (0.5-1.2GB/s); no Polars/SQLite in this one.
- **[verified gap]** No credible Polars NDJSON throughput number exists anywhere; the one widely-echoed figure traces to one unreachable site and reads as fabricated.
- **[sourced]** SQLite JSONB speedup claims range 2-3x (vendor, no methodology) to 5-25x (DoltHub, read-path, 2024-11-18) — published size-savings figures disagree nearly 10x across sources (5-10% vendor vs ~34% DoltHub).

### What our scale looks like vs. what these benchmarks test

None of ClickBench (100M rows/one table), db-benchmark (10M-1B rows), or TPC-H SF10-100 (10-100GB) resemble our shape: ~1M rows, 364MB, 904 small files, 3 schemas, Windows. The only on-scale evidence is our own salvaged local run (x12-scale bench, 1,057,788 rows/620MB, under load from 11-14 concurrent agents — indicative, not clean-room): DuckDB ingest 2.55s; groupby/filter/aggregate 8-20ms once loaded; querying raw JSONL directly (no import) 237.9ms vs 19.5ms over pre-exported Parquet — ~12x parse overhead, still comfortably sub-second. The crossover sweep in that file shows SQLite-indexed beating DuckDB below ~150K rows and losing ~8x by 1.06M rows — a genuine our-scale datapoint none of the four public suites offer. Caveat: that file's substring-scan hit counts disagree between engines (SQLite 74,736 vs DuckDB/Polars 2,052, likely case-sensitivity, unverified) — treat that one row as not yet apples-to-apples; groupby/filter timings aren't affected.

The gap that matters most: none of the four public suites test many-small-heterogeneous-files or schema drift — our exact pattern. That's answered only by our own local lane's discovery of three incompatible schemas in one directory; DuckDB's `union_by_name` fix for it remains **unverified**, per that file's own note.

### Could NOT verify
- Exact db-benchmark 0.5/5GB numeric timings (chart-only page; didn't download underlying results, per the no-large-files guardrail).
- One unified ClickBench table with SQLite/Polars/DataFusion/chDB numbers beside DuckDB/ClickHouse on the identical full run.
- Whether SQLite's stale ClickBench entry is neglect or an inability to finish the query set.
- Any TPC-H-family run on current DuckDB (1.5.x/2.0) — freshest found used 1.3.0.
- Any Windows datapoint across all four benchmark families — all ran on Linux cloud instances or Macs.

### What it means for us

These four suites answer "which engine wins at 10M-1B rows on a big Linux box" — useful only as a sanity check that DuckDB isn't a fluke (it isn't: real ClickBench wins, TPC-H numbers competitive with Polars even at SF100). They aren't evidence about whether DuckDB helps us. Trust our own already-measured local numbers for the actual sizing decision, and treat db-benchmark's DuckDB-Labs authorship and ClickBench's ClickHouse authorship as reasons to prefer our unconflicted local crossover sweep — which already answers the one question those suites can't: where SQLite stops being enough at our row counts (~150K), not theirs.
