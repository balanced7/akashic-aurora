---
akashic_id: art_20260924_duckdb-lane-schema_3a56af
akashic_sha: 3f89cf9022f4
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-lane-schema
gist: "# DuckDB deep dive, re-run -- lane: schema *2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Dan"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:28:15"
updated: "2026-09-24T21:28:15"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-lane-schema_3a56af -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-lane-schema

# DuckDB deep dive, re-run -- lane: schema

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent a318cfa64b884c8de (claude-opus-5-5) ran 21:01-21:21 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\schema (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census (read this one first), and fanout-index. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools if needed: ToolSearch query "select:WebSearch,WebFetch".
- For local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1). Install nothing anywhere else.
- Every DuckDB connection: SET memory_limit='3GB'; SET threads=4; and a temp_directory inside your lane dir. For Polars, set the environment variable POLARS_MAX_THREADS=4.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\schema\. Create files only there. The ledgers in E:\AI-Setup are READ-ONLY; copy a file into your lane dir if you need to change it.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: schema. Question: can we get CORRECT answers out of our real, messy ledgers?

Known so far:
- The census found three record shapes in E:\AI-Setup\state\bus-export\*.jsonl: 328 files of messages, 59 files with a "data" field, and 1 trace file.
- Polars silently picked the minority schema.
- DuckDB hard-failed on a malformed line in E:\AI-Setup\session_logs\ledger\recall_outcome.jsonl (line 221, invalid high surrogate).

Experiment locally:
1. DuckDB read_json_auto / read_ndjson over all bus-export files, with union_by_name=true, sample_size=-1 and format='newline_delimited'. Report which columns result, what the nested "fields" becomes, whether each shape's rows survive, and per-shape row counts against raw line counts.
2. Conflicting types for the same field name: what does DuckDB do?
3. ignore_errors: how many lines does it drop, and does it report them anywhere?
4. The same questions with Polars (explicit schema, infer_schema_length=None) and with pyarrow.json.
5. Settle the substring discrepancy in the salvaged benchmark: SQLite found 74,736 hits and DuckDB/Polars found 2,052 on the same input. Find the query in bench.py (reproduced in the local-benchmarks file), rerun it with explicit case handling, and report exact counts. Is it case sensitivity or something else?

Conclude: which engine gives CORRECT answers over heterogeneous logs, what configuration that takes, and what a schema-version field in our ledgers would buy.

## The report (verbatim)

Five of five parse-error cases report line N+1: four synthetic files plus the real events_claude_raw.jsonl row. Transform (unknown-key) errors reported correct line numbers. All experiments are done, so here is the full report.

# Schema lane: can we get correct answers out of our real, messy ledgers?

*The harness blocked a REPORT.md from this subagent, so this message is the report. Every script and its raw output (`*_out.txt`) is in `C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\schema\`, next to a 52 MB snapshot of `session_logs\ledger` (`snap_ledger\`). All guardrails held: 3 GB memory limit, 4 threads, temp directory in the lane, nothing left running.*

## Headline
- **DuckDB is the only engine of the three that returns correct answers and stays queryable on our ledgers.** That needs `read_json(glob, format='newline_delimited', union_by_name=true, sample_size=-1)` with no `ignore_errors`. With that setting it matched Python's json module exactly on all 388 bus-export files. DuckDB's defaults silently drop data, and so do Polars (even with `infer_schema_length=None`) and `pyarrow.dataset`.
- **`ignore_errors` never removes a line.** Each bad line comes back as a row of NULLs, so `count(*)` hides the loss, and nothing reports it.
- **Our data is a bigger risk than the choice of engine.** Three defects give wrong answers in every engine: 62 broken-text values from a Windows decoding bug, `at` written as a number in some files and as a date string in others, and `content` encoded as JSON twice.
- **The substring discrepancy is case sensitivity and nothing else.** Every engine gives 2,052 hits when matching case exactly and 74,736 when ignoring case.

## Findings

**What the data really contains (checked with Python's json module)**
1. [measured] `census.py`: bus-export has 388 files, 223,910 lines, and no invalid JSON. `fields` comes in five key sets: 100,151 rows (10 keys, including `ts` and `v`), 62,962 (`data` only), 60,734 (trace rows with no `len`/`sha`), 59 (with `spot_tick`) and 4 (with `frag`). **This corrects the census:** its 328-file shape does include `ts` and `v`, and two rare shapes exist. Every value in `fields` is a string. `content`, `data`, `meta` and `parts` are themselves JSON stored inside those strings.
2. [measured] `probe2.py`: `session_logs\ledger` (snapshot: 681 files, 66,058 rows) has 16 rows containing invalid text characters (lone surrogates such as `\udc9d`) right after garbled text like `â€`.
   - This is UTF-8 that some writer decoded as Windows cp1252 using Python's `surrogateescape` handler. It is a writer bug.
   - bus-export holds 46 more of these inside its double-encoded strings.
   - Python accepts all of them without complaint; DuckDB, Polars and pyarrow all reject them.
3. [measured] Real type conflicts:
   - `event.at`: a number in 26,000 rows (2 files), an ISO date string in 39,330 rows (643 files).
   - `event.success`: true/false in 35 rows, "yes"/"no"/"partial" in 9.
   - `data.at`: a number in 49,820 rows, a string in 12,728.
   - `event.detail.ts` is sometimes a string and sometimes a number; `event.detail.content` is sometimes an object and sometimes a string (both surfaced by pyarrow's error messages).
4. [measured] recall_outcome.jsonl is not append-only. It is a 20,000-row window that gets rewritten: its first id moved from 26,761 to 26,775 in about a minute. The salvaged "line 221" error is the same bad rows, which have since moved.

**Q1: union_by_name over bus-export** (`duck1.py`)
5. [measured] With `union_by_name=true, sample_size=-1`, DuckDB matched the ground truth exactly:
   - 223,910 rows, and all 388 per-file counts equal the Python counts;
   - all 13 per-key non-null counts are exact;
   - an md5 over every `content`, `data` and `meta` value is identical to Python's.

   `fields` becomes a STRUCT of 13 text columns, with `ts` auto-typed as TIMESTAMP. It took 738 ms against 151 ms for the default (describe plus count; timings indicative).
6. [measured] The default read keeps every row but silently leaves out `frag` and `spot_tick` (63 values). `sample_size=-1` alone does not fix this; what fixes it is sampling every file, via `union_by_name` or `maximum_sample_files` of at least the file count. [sourced] The default is 32 files (duckdb.org/docs/current/data/json/loading_json.html, read 2026-09-24). On the ledgers, default sampling leaves out 16 of 50 `event` keys: 412,575 values, including `event.at` in 65,320 rows.
7. [measured] **Whether DuckDB errors depends on the query, not the data.** An unknown key raises an error only when the query reads every top-level column.
   - `CREATE TABLE AS SELECT *` fails with an exact location: bifrost_inbox_kimi.jsonl, line 507, unknown key `frag`.
   - `SELECT fields …` drops the key silently (confirmed by bisecting in `matrix3.py` through `matrix7.py`).
   - With an explicit `columns=` schema, undeclared keys vanish even under `SELECT *` (the docs say read_json "excludes columns that we don't specify").

**Q2: conflicting types for the same field**
8. [measured] DuckDB (with the union setting) types every conflicting field as JSON, losslessly: all 25,992 surviving numeric `at` values match the file text exactly. Comparing a JSON column to a plain value raises an error, which is good. But the obvious workaround, `event.at->>'$' >= '2026-09-01'`, returns 11,088. Converting both the numbers and the date strings gives 34,656, and Python agrees exactly. The easy query undercounts by 68% with no warning.
9. [measured] `matrix.py`, a field that changes from integer to string after row 30,000:

   | Reader | Result |
   |---|---|
   | DuckDB default | Errors |
   | DuckDB `sample_size=-1` | Types it JSON and keeps the value |
   | DuckDB `ignore_errors` | Turns the row into NULLs |
   | Polars default | Errors |
   | Polars `infer_schema_length=None` | Converts everything to strings (`'29998'`, `'true'`), losing the types |
   | Polars `ignore_errors` | Silently NULLs the value |
   | pyarrow | Errors ("changed from number to string") |

10. [measured] Timestamps:
    - DuckDB leaves a mix of timestamps with and without a timezone as text, which is safe.
    - DuckDB converts timestamps that all carry an offset to UTC and discards the offset.
    - pyarrow converts a mix to one timestamp type and silently treats the timestamp without a zone as UTC.

**Q3: ignore_errors** (`duck2.py`, `matrix.py`, `lineno.py`)
11. [measured] DuckDB drops 0 lines. The 16 bad lines come back as rows of NULLs: `count(*)` is 66,058 (the raw count) while `count(id)` is 66,042, and the missing ids are exactly the 16 broken-text rows.
    - There is no warning, and DuckDB has no option to collect rejected JSON lines. I checked its full parameter list; the docs only say "ignore parse errors".
    - **This corrects the salvaged parity check** (raw count equals DuckDB count for recall_outcome.jsonl). It used `count(*)` with `ignore_errors` on, so it could not have seen any loss.
12. [measured] `ignore_errors` also turns the whole row into NULLs for:
    - a line cut short by a power loss;
    - a zero-filled file tail;
    - invalid UTF-8 bytes;
    - a UTF-8 byte-order mark (the file's first row is lost; PowerShell 5.1 writes these by default).

    Without `ignore_errors`, parse errors name the file but report the line as N+1 (5 of 5 cases).
13. [measured] Polars' `ignore_errors` only covers schema mismatches (its docstring agrees). Malformed JSON still fails, and the error gives neither file nor line ("InvalidUnicodeCodepoint at character 469"). pyarrow has no skip option at all.

**Q4: Polars and pyarrow**
14. [measured] Polars 1.39.3, with defaults and with `infer_schema_length=None`, takes the schema from the first file only: `Struct({'data'})`.
    - 160,948 of 223,910 rows (72%) come back with every `fields` value NULL, while the row count still matches.
    - An explicit schema gives exact results, with an identical md5. An explicit schema that leaves keys out drops them silently.
    - On the ledgers every inference mode fails outright (`reasoning: String != Null`). Reading files one at a time and combining them with `diagonal_relaxed` loads only 11,851 of 66,058 rows.
15. [measured] pyarrow 23.0.1: `ds.dataset` loses the same 72% from the first file's schema.
    - Reading each file with `read_json` and combining with `concat_tables(promote_options='permissive')` gives exact results.
    - `unexpected_field_behavior='error'` is the only setting in any of the three engines that refuses undeclared keys.
    - On the ledgers 13 of 681 files fail and only 5,440 of 66,058 rows load. Invalid UTF-8 is accepted silently.

**Q5: substring discrepancy** (`sub1.py`, on the first 88,149 lines of bifrost_broadcast.jsonl, the benchmark's base)
16. [measured] It is case sensitivity and nothing else.
    - Case-sensitive: 171 rows in every engine (DuckDB LIKE and contains, Polars literal, SQLite instr, GLOB and `case_sensitive_like=ON`, Python). Times 12 that is **2,052**.
    - Case-insensitive: 6,228 in every engine (SQLite default LIKE, DuckDB ILIKE, lower and `(?i)`, Polars `(?i)`, Python). Times 12 that is **74,736**.
    - ASCII-only and full Unicode case folding give the same count.
    - SQLite full-text search (FTS5) gives 6,220, times 12 is 74,640. The 8 missing rows contain the word only inside the longer words `bifrostapi` and `codexbifrostwake`.

    [sourced] SQLite's LIKE ignores case for ASCII by default, and GLOB is case-sensitive (sqlite.org/lang_expr.html, read 2026-09-24). So the salvaged substring timings compare different queries; DuckDB should be re-timed with ILIKE.
17. [measured] Double encoding: searching for an em dash finds 0 rows in `content` as stored, and 34,947 after decoding a second time. This holds in every engine. In DuckDB the second decode needs `try()`: `json_valid` flags 13 `content` and 37 `data` values, which are the 4 fragment rows plus the 46 broken-text values.

## Could not verify
- Whether DuckDB's query-dependent errors and N+1 line numbers are intended. The docs say nothing; I tested only 1.5.5.
- Whether reads can see a half-written recall_outcome.jsonl while it is being rewritten (the concurrency lane's question).
- Which writer produces the cp1252 garbled text.
- The cost of `union_by_name` over the full 364 MB; I measured only bus-export (160 MB).
- JSONL files under `state\` outside bus-export were not checked.

## What it means for us
1. **Engine:** use DuckDB through one shared view built on `union_by_name=true, sample_size=-1`, reading snapshots of the rolling-window files. Never use `ignore_errors` when producing an answer. Check every result two ways:
   - `count(*) - count(id)` must be 0;
   - a key-set census with `json_keys` (171 ms) must match the list of known shapes.
2. **Fix the writers, because no reader can:**
   - the `surrogateescape` decoding bug (62 values);
   - one type per field, with ISO-8601 UTC for every `at`;
   - stop double-encoding `content`;
   - write with `allow_nan=False` and no byte-order mark;
   - write-then-rename for the rolling windows.
3. **Schema version:** we already have `v`, but it reads `'2'` across four different shapes, so it tells a reader nothing. A real schema field (for example `bus.msg/3`), bumped on any key or type change and checked at write time, would give us three things:
   - an explicit schema per version, and explicit schemas were exact in all three engines;
   - a one-line alarm for unknown versions, in place of sniffing keys;
   - the right conversion of `at` per version, which removes the 68% undercount by construction.

   It would not fix bad bytes; only validating at the writer does that.
