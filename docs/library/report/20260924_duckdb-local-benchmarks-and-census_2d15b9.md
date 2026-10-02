---
akashic_id: art_20260924_duckdb-local-benchmarks-and-census_2d15b9
akashic_sha: 45d76e6067a0
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-local-benchmarks-and-census
gist: "# DuckDB deep dive -- the local half: census, benchmarks, and what our own data revealed *2026-09-24, DuckDB deep-dive fan-out (17 agents), "
visibility: fleet
body_type: markdown
seats: [claude]
category: [migration, bus, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:00:24"
updated: "2026-09-24T21:00:24"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-local-benchmarks-and-census_2d15b9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-local-benchmarks-and-census

# DuckDB deep dive -- the local half: census, benchmarks, and what our own data revealed

*2026-09-24, DuckDB deep-dive fan-out (17 agents), launched per Daniil's Bifrost ask at 19:42: "Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" This file holds the measurements taken ON THIS MACHINE against our own ledgers. Salvaged verbatim by claude after the 20:24 power cut, from session bee0f118-f0f5-4b8a-a0d8-66aee48f3df1.*

## Caveats found while salvaging (claude, 2026-09-24 night)

- The substring-scan hit counts disagree between engines: SQLite 74,736 vs DuckDB/Polars 2,052 on the same input. Most likely SQLite LIKE is case-insensitive for ASCII while DuckDB/Polars `contains` is case-sensitive -- UNVERIFIED. Until settled, the substring timings are not apples-to-apples.
- 13 of the 17 agents, including both lead lanes, were cut off by the power cut; no synthesis was written. See duckdb-fanout-index-2026-09-24.md.
- The benchmarks ran while 11-14 agents were active on a machine 83 h into uptime; timings are indicative, not clean-room.

## Interim census note (sent to Daniil on Bifrost 19:50, verbatim)

```text
Deep dive is running on two lanes (DuckDB itself; alternatives + the build-it-ourselves
question). While they work I measured OUR side, because whether DuckDB helps depends on what
our data actually looks like -- and what I found makes the case better than any benchmark would.

## WHAT WE HAVE

    904 JSONL ledger files · 363.9 MB · 968,929 rows

Bus exports, recall outcomes, traces, event logs, fetch receipts, the doc store. All
append-only. Nearly a million rows nobody can currently ask a question of, because the only
tools are grep and a Python loop.

## THE FINDING, and it is a live instance of this week's theme

I pointed Polars (already installed, 1.39.3 -- we have a columnar engine and have never aimed it
at our own ledgers) at every bus-export file at once:

    223,910 rows scanned in 0.08 seconds

Then I asked "who talks most" and it failed: `unable to find column "frm"`. Polars had inferred
the schema as Struct({'data': String}).

But the actual first row of the biggest file has fields
['frm','to','kind','content','ts','meta','parts','v','len','sha'].

So I counted the shapes across all 388 files:

    328 files   content, frm, kind, len, meta, parts, sha, to     <- messages
     59 files   data                                              <- events, a different shape
      1 file    content, frm, kind, meta, parts, to, ts, v        <- traces

THREE DIFFERENT SCHEMAS IN ONE DIRECTORY. A naive glob unified them, picked the 59-file
minority, and then could not find a column that 328 files have.

That is not "Polars is bad". It is the exact failure we have been chasing all week, wearing new
clothes: A SURFACE ANSWERING CONFIDENTLY FROM A PARTIAL VIEW. It did not say "these files
disagree"; it produced one schema, silently, and the disagreement only surfaced because I asked
for a column that happened to be missing. Had I asked for `content` -- present in 329 of 388 --
I would have gotten answers for 85% of the data and never known the other 15% was excluded.

## WHY THIS SHARPENS THE DUCKDB QUESTION RATHER THAN ANSWERING IT

DuckDB has `union_by_name=true` precisely for this: reconcile columns by NAME across files
instead of collapsing to one inferred shape. If that works as documented, it is not a
convenience -- it is the difference between a query engine that tells the truth over
heterogeneous logs and one that quietly narrows. I have asked the research lane to verify it
rather than take the docs' word.

Three things I want the deep dive to settle before I recommend anything:

  1. SCHEMA RECONCILIATION over heterogeneous JSONL -- does union_by_name actually hold, and
     what does it do with genuinely conflicting TYPES for the same name?
  2. MULTI-PROCESS ACCESS. Several agent seats share this machine and would all want to read.
     DuckDB's concurrency model matters more for us than its speed.
  3. WHETHER WE NEED IT AT ALL, given Polars and PyArrow are already installed and DuckDB is
     not. "We already own a columnar engine and never pointed it at the ledgers" is a real
     possible answer, and it costs nothing.

One thing I can say already regardless of which engine wins: THE LEDGERS SHOULD PROBABLY CARRY
A SCHEMA VERSION. Three shapes accumulated without anyone deciding to have three, and no reader
can currently tell which shape it is holding without sniffing. That is fixable cheaply and
independently of this whole question.

Full report when both lanes land.

-- Vandor
```

## Full bench, x12 scale (1,057,788 rows, 620 MB) -- SQLite raw/shredded/FTS5, DuckDB, Polars, DataFusion

*background task bsrc8w568, verbatim output*

```text
EXIT=0
INPUT: 1,057,788 rows, 620.0 MB  (scale x12)

SQLite A - raw JSON TEXT column + json_extract at query time
    ingest                                          3767.3 ms
    groupby frm,kind (json_extract)                 3798.2 ms
    filter+count on ts prefix                       1154.3 ms
    substring scan in content                       1333.5 ms
  -> size 687.2 MB   top=[('claude', 'trace', 805380), ('deepseek', 'trace', 124032)]  ts_hits=466,332  substr=74,736

SQLite B - shredded typed columns + indexes (the 'do it properly' version)
    ingest (python json parse + shred)              6245.4 ms
    create indexes (kind,frm),(ts)                  1279.5 ms
    groupby frm,kind (indexed)                        60.5 ms
    filter+count on ts prefix (indexed)               50.1 ms
    substring scan in content                        304.5 ms
    sum(len) group by kind                           303.0 ms
    point lookup by id (indexed scan)                204.2 ms
  -> size 378.2 MB  ts_hits=466,332 substr=74,736

SQLite C - FTS5 full-text index over content
    build FTS5 index                                9848.4 ms
    MATCH 'Bifrost' count                              1.9 ms
    MATCH ranked top-10 bm25                          47.6 ms
    optimize                                         918.8 ms
  -> size 255.8 MB  match_hits=74,640

DuckDB - read_json_auto / native store / parquet
    ingest via read_json_auto -> native table       2551.2 ms
    groupby frm,kind                                  10.0 ms
    filter+count on ts prefix                          8.9 ms
    substring scan in content                         13.3 ms
    sum/avg(len::int) group by kind                    8.4 ms
    export -> parquet(zstd)                          460.4 ms
    groupby DIRECTLY over parquet (no import)         19.5 ms
    groupby DIRECTLY over raw jsonl (no import)      237.9 ms
  -> duckdb file 256.0 MB | parquet+zstd 59.3 MB  ts_hits=466,332 substr=2,052


Polars - scan_ndjson / parquet
    read_ndjson -> DataFrame (eager)                 434.3 ms
    groupby frm,kind                                  17.6 ms
    filter+count ts prefix                            19.1 ms
    substring scan content                            20.2 ms
    write parquet(zstd)                              260.1 ms
    LAZY scan_parquet groupby (projection pushdown)       9.1 ms
    LAZY scan_ndjson groupby                         412.7 ms
  -> parquet 66.8 MB  ts_hits=466,332 substr=2,052

DataFusion
    register parquet + groupby                        14.0 ms
    filter+count over parquet                         19.0 ms
    substring scan over parquet                       45.1 ms

=== SIZES ON DISK ===
  input.jsonl                   620.0 MB
  sqlite raw-json               687.2 MB
  sqlite shredded+idx           378.2 MB
  sqlite FTS5                   255.8 MB
  duckdb native                 256.0 MB
  parquet zstd (duckdb)          59.3 MB
  parquet zstd (polars)          66.8 MB

[exited with code 0]
```

## Crossover sweep, append-only cost, and BM25 + vector retrieval on one SQLite file

*background task bdnfdskdk, verbatim output*

```text
EXIT=0
==========================================================================
PART 1  CROSSOVER SWEEP - groupby(frm,kind) + filter, SQLite(indexed) vs DuckDB
==========================================================================
      rows      MB |  SQLite gb  DuckDB gb |  SQLite filt  DuckDB filt |  SQLite sum  DuckDB sum
    88,149      52 |       5.6m       7.6m |         2.6m         1.7m |       10.9m        6.0m
   264,447     155 |       9.4m       6.6m |         8.4m         4.0m |       44.0m        4.4m
   528,894     310 |      34.6m       8.5m |        26.5m         4.2m |       83.7m        4.5m
 1,057,788     620 |      50.5m       6.1m |        38.0m         4.7m |      261.4m        3.6m

==========================================================================
PART 2  APPEND-ONLY: cost of adding ONE day of new events to an existing store
==========================================================================
existing: 528,894 rows / 310 MB   increment: 5,000 rows / 3.0 MB
  SQLite  append 5k rows (indexed table, WAL)                 36.0 ms   -> 119 MB
  DuckDB  append 5k rows into native table                    38.0 ms   -> 6 MB
  Parquet write NEW batch as its own file (no rewrite)        37.1 ms   -> 3 MB total
  DuckDB  groupby across the parquet DIRECTORY (2 files)       6.0 ms
  Polars  lazy groupby across same parquet directory           8.1 ms
  DataFusion groupby across same parquet directory             8.6 ms
  PyArrow  dataset groupby, NO query engine                    8.6 ms

==========================================================================
PART 3  RETRIEVAL: BM25 (FTS5) + brute-force vector KNN (sqlite-vec) on ONE sqlite file
==========================================================================
  FTS5 index 50,000 docs                                      251.5 ms
  sqlite-vec store 50,000 x 384d float32 vectors             1237.7 ms   -> 87 MB total
  brute-force KNN top-10 over 50,000 vectors                  42.6 ms
  FTS5 BM25 top-10                                            2.3 ms
  HYBRID BM25+KNN with reciprocal-rank fusion, top-10        47.2 ms

  one sqlite file holds rows + BM25 + vectors: 87 MB, zero servers, zero containers

  brute-force KNN top-10 over 100,000 x 384d vectors       28.2 ms  (in-memory)
  brute-force KNN top-10 over 250,000 x 384d vectors       63.0 ms  (in-memory)

[exited with code 0]
```

## DuckDB read_json_auto over session_logs/ledger/*.jsonl -- strict vs ignore_errors

*background task bxovpczww, verbatim output*

```text
-- WITHOUT ignore_errors (does it hard-fail?) --
   HARD FAIL -> Invalid Input Error: Malformed JSON in file "E:\AI-Setup\session_logs\ledger\recall_outcome.jsonl", at byte 566 in line 221: invalid high surrogate in string. 

LINE 1: select count(*) from read_json_auto('E:/AI-Setup/session_logs/ledger/*.jsonl...
                             ^

-- per-file: duckdb count vs raw line count --
   agent_agent_0_events.jsonl         raw=      8  duckdb=      8
   agent_agent_1_events.jsonl         raw=      8  duckdb=      8
   agent_agent_2_events.jsonl         raw=      8  duckdb=      8
   agent_agent_3_events.jsonl         raw=      8  duckdb=      8
   agent_agent_4_events.jsonl         raw=      8  duckdb=      8
   agent_agent_5_events.jsonl         raw=      8  duckdb=      8
   agent_agent_6_events.jsonl         raw=      8  duckdb=      8
   agent_agent_7_events.jsonl         raw=      8  duckdb=      8
   agent_agent_8_events.jsonl         raw=      8  duckdb=      8
   agent_agent_9_events.jsonl         raw=      8  duckdb=      8
   agent_agent_a_architect_events.jsonl raw=      6  duckdb=      6
   agent_asta_events.jsonl            raw=      2  duckdb=      2
   agent_claude-probe3_events.jsonl   raw=      1  duckdb=      1
   agent_claude_events.jsonl          raw=    208  duckdb=    208
   agent_codex_events.jsonl           raw=      2  duckdb=      2
   agent_codex_explain_events.jsonl   raw=      4  duckdb=      4
   agent_codex_nudge_audit_events.jsonl raw=      1  duckdb=      1
   agent_codex_rescue_events.jsonl    raw=      1  duckdb=      1
   agent_codex_root_019fab2d_events.jsonl raw=      4  duckdb=      4
   agent_codex_t093_audit_events.jsonl raw=      1  duckdb=      1
   agent_codex_t093_git_cancel_events.jsonl raw=      1  duckdb=      1
   agent_codex_t093_race_audit_events.jsonl raw=      1  duckdb=      1
   agent_codex_t093_second_review_events.jsonl raw=      1  duckdb=      1
   agent_codex_yousef_audit_events.jsonl raw=      1  duckdb=      1
   agent_cursor_events.jsonl          raw=     10  duckdb=     10
   agent_dsh_agent_events.jsonl       raw=     15  duckdb=     15
   agent_events.jsonl                 raw=    332  duckdb=    332
   agent_kimi_events.jsonl            raw=      6  duckdb=      6
   agent_opal_events.jsonl            raw=      1  duckdb=      1
   agent_opencode_test_events.jsonl   raw=      2  duckdb=      2
   agent_rill_events.jsonl            raw=      1  duckdb=      1
   agent_sol_events.jsonl             raw=     11  duckdb=     11
   agent_test_agent_1_events.jsonl    raw=     10  duckdb=     10
   agent_test_agent_2_events.jsonl    raw=      8  duckdb=      8
   agent_test_agent_3_events.jsonl    raw=      6  duckdb=      6
   agent_test_agent_learner_events.jsonl raw=      6  duckdb=      6
   events_T197DRILLb39b_raw.jsonl     raw=      1  duckdb=      1
   events_a_raw.jsonl                 raw=     83  duckdb=     83
   events_agentA_raw.jsonl            raw=     22  duckdb=     22
   events_agentB_raw.jsonl            raw=     22  duckdb=     22
   events_agent_picker_ux_raw.jsonl   raw=      1  duckdb=      1
   events_agent_x_raw.jsonl           raw=     21  duckdb=     21
   events_alice_raw.jsonl             raw=     30  duckdb=     30
   events_analysis-agent_raw.jsonl    raw=      1  duckdb=      1
   events_arc-check_raw.jsonl         raw=      1  duckdb=      1
   events_asker_raw.jsonl             raw=     76  duckdb=     76
   events_asta_raw.jsonl              raw=     12  duckdb=     12
   events_astra_raw.jsonl             raw=     36  duckdb=     36
   events_b_raw.jsonl                 raw=    151  duckdb=    151
   events_beat_agent_raw.jsonl        raw=     24  duckdb=     24
   events_c7-4-class-pin_raw.jsonl    raw=     75  duckdb=     75
   events_c_raw.jsonl                 raw=     40  duckdb=     40
   events_census_raw.jsonl            raw=     48  duckdb=     48
   events_claude-probe3_raw.jsonl     raw=      5  duckdb=      5
   events_claude-probe4_raw.jsonl     raw=      1  duckdb=      1
   events_claude-probe5_raw.jsonl     raw=      1  duckdb=      1
   events_claude-probe6_raw.jsonl     raw=      2  duckdb=      2
   events_claude-probe7_raw.jsonl     raw=      1  duckdb=      1
   events_claude_design_raw.jsonl     raw=     28  duckdb=     28
   events_claude_raw.jsonl            raw=  6,029  duckdb=   6029
   events_codex-01a09757_raw.jsonl    raw=      2  duckdb=      2
   events_codex-door-debug_raw.jsonl  raw=      1  duckdb=      1
   events_codex-flush-probe_raw.jsonl raw=      1  duckdb=      1
   events_codex-mcp-isolate_raw.jsonl raw=      1  duckdb=      1
   events_codex-piano_raw.jsonl       raw=     10  duckdb=     10
   events_codex-voice_raw.jsonl       raw=      1  duckdb=      1
   events_codex_019f9924_raw.jsonl    raw=     38  duckdb=     38
   events_codex_019faa7a_raw.jsonl    raw=      1  duckdb=      1
   events_codex_bifrost_3d_design_raw.jsonl raw=      1  duckdb=      1
   events_codex_bifrost_ui_map_raw.jsonl raw=      1  duckdb=      1
   events_codex_crash_probe_raw.jsonl raw=      8  duckdb=      8
   events_codex_deepseek_cli_fan_raw.jsonl raw=      2  duckdb=      2
   events_codex_explain_raw.jsonl     raw=    177  duckdb=    177
   events_codex_eye_longitudinal_raw.jsonl raw=      2  duckdb=      2
   events_codex_frontier_019f6e7e_raw.jsonl raw=      6  duckdb=      6
   events_codex_identity_ui_trace_raw.jsonl raw=      1  duckdb=      1
   events_codex_ledger_reality_raw.jsonl raw=      1  duckdb=      1
   events_codex_nudge_audit_raw.jsonl raw=      3  duckdb=      3
   events_codex_raw.jsonl             raw=     97  duckdb=     97
   events_codex_rescue_raw.jsonl      raw=      5  duckdb=      5
   events_codex_rill_relaunch_raw.jsonl raw=      6  duckdb=      6
   events_codex_root_019fab2d_raw.jsonl raw=    168  duckdb=    168
   events_codex_root_raw.jsonl        raw=    139  duckdb=    139
   events_codex_router_audit_raw.jsonl raw=      1  duckdb=      1
   events_codex_runner_trace_raw.jsonl raw=      1  duckdb=      1
   events_codex_t093_audit_raw.jsonl  raw=      5  duckdb=      5
   events_codex_t093_git_cancel_raw.jsonl raw=      3  duckdb=      3
   events_codex_t093_race_audit_raw.jsonl raw=      3  duckdb=      3
   events_codex_t093_review_raw.jsonl raw=      1  duckdb=      1
   events_codex_t093_second_review_raw.jsonl raw=     13  duckdb=     13
   events_codex_t125_ruling_raw.jsonl raw=      3  duckdb=      3
   events_codex_trellis_raw.jsonl     raw=      3  duckdb=      3
   events_codex_yousef_audit_raw.jsonl raw=      3  duckdb=      3
   events_codex_yousef_reader_raw.jsonl raw=      1  duckdb=      1
   events_composer_raw.jsonl          raw=      3  duckdb=      3
   events_cursor_grok_raw.jsonl       raw=     16  duckdb=     16
   events_cursor_pull_02ac15_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_07a58f_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_09c134_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_104244_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_21c99c_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_23c9e6_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_2e3695_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_3d8b7f_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_435a62_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_53843e_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_5d4867_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_7d10de_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_7dd1ac_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_927ffd_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_a04a27_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_ac1975_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_aeb1c0_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_b69bb9_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_cf7612_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_d5302f_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_de422b_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_e24f08_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_e71768_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_fca8dd_raw.jsonl raw=      1  duckdb=      1
   events_cursor_pull_ffe73f_raw.jsonl raw=      1  duckdb=      1
   events_cursor_raw.jsonl            raw=     57  duckdb=     57
   events_d3a-4ddf0a71_raw.jsonl      raw=     21  duckdb=     21
   events_d3a-7a1b6b11_raw.jsonl      raw=      1  duckdb=      1
   events_d3a-7ab26fe9_raw.jsonl      raw=     12  duckdb=     12
   events_d3a-cfdcb65f_raw.jsonl      raw=     23  duckdb=     23
   events_d3a-d9b54722_raw.jsonl      raw=     12  duckdb=     12
   events_d3b-4ddf0a71_raw.jsonl      raw=     13  duckdb=     13
   events_d3b-7ab26fe9_raw.jsonl      raw=      8  duckdb=      8
   events_d3b-cfdcb65f_raw.jsonl      raw=     13  duckdb=     13
   events_d3b-d9b54722_raw.jsonl      raw=     14  duckdb=     14
   events_deepseek-plumbing_raw.jsonl raw=     38  duckdb=     38
   events_deepseek-red_raw.jsonl      raw=     31  duckdb=     31
   events_deepseek-review_raw.jsonl   raw=     88  duckdb=     88
   events_deepseek-ui_raw.jsonl       raw=     31  duckdb=     31
   events_deepseek_raw.jsonl          raw=  5,807  duckdb=   5807
   events_discord_raw.jsonl           raw=     80  duckdb=     80
   events_door-probe-cli_raw.jsonl    raw=      1  duckdb=      1
   events_door-probe_raw.jsonl        raw=    187  duckdb=    187
   events_downagent_raw.jsonl         raw=     44  duckdb=     44
   events_drill-00f77aed_raw.jsonl    raw=      1  duckdb=      1
   events_drill-02edcf98_raw.jsonl    raw=      1  duckdb=      1
   events_drill-0844874e_raw.jsonl    raw=      1  duckdb=      1
   events_drill-08e1d08b_raw.jsonl    raw=      1  duckdb=      1
   events_drill-09640044_raw.jsonl    raw=      1  duckdb=      1
   events_drill-14b67760_raw.jsonl    raw=      1  duckdb=      1
   events_drill-17d3bba6_raw.jsonl    raw=      1  duckdb=      1
   events_drill-1aa19e8e_raw.jsonl    raw=      1  duckdb=      1
   events_drill-1ecadfb5_raw.jsonl    raw=      1  duckdb=      1
   events_drill-1fb9702f_raw.jsonl    raw=      1  duckdb=      1
   events_drill-1fba2278_raw.jsonl    raw=      1  duckdb=      1
   events_drill-2f7d34bd_raw.jsonl    raw=      1  duckdb=      1
   events_drill-3a34a75f_raw.jsonl    raw=      1  duckdb=      1
   events_drill-3a75d717_raw.jsonl    raw=      1  duckdb=      1
   events_drill-40ef814c_raw.jsonl    raw=      1  duckdb=      1
   events_drill-41478793_raw.jsonl    raw=      1  duckdb=      1
   events_drill-4297b888_raw.jsonl    raw=      1  duckdb=      1
   events_drill-441d5de0_raw.jsonl    raw=      1  duckdb=      1
   events_drill-4580c9e5_raw.jsonl    raw=      1  duckdb=      1
   events_drill-45ab319f_raw.jsonl    raw=      1  duckdb=      1
   events_drill-494f2b76_raw.jsonl    raw=      1  duckdb=      1
   events_drill-512853ff_raw.jsonl    raw=      1  duckdb=      1
   events_drill-5ef33bed_raw.jsonl    raw=      1  duckdb=      1
   events_drill-65b6461a_raw.jsonl    raw=      1  duckdb=      1
   events_drill-6ac46607_raw.jsonl    raw=      1  duckdb=      1
   events_drill-81f2c1f6_raw.jsonl    raw=      1  duckdb=      1
   events_drill-84ebdc2c_raw.jsonl    raw=      1  duckdb=      1
   events_drill-8971e718_raw.jsonl    raw=      1  duckdb=      1
   events_drill-9629d7e0_raw.jsonl    raw=      1  duckdb=      1
   events_drill-995f9e5f_raw.jsonl    raw=      1  duckdb=      1
   events_drill-a14ecff5_raw.jsonl    raw=      1  duckdb=      1
   events_drill-a7cd48e9_raw.jsonl    raw=      1  duckdb=      1
   events_drill-ad788c32_raw.jsonl    raw=      1  duckdb=      1
   events_drill-af926b7d_raw.jsonl    raw=      1  duckdb=      1
   events_drill-b040600f_raw.jsonl    raw=      1  duckdb=      1
   events_drill-b53f9a84_raw.jsonl    raw=      1  duckdb=      1
   events_drill-bd4209cf_raw.jsonl    raw=      1  duckdb=      1
   events_drill-c121ef56_raw.jsonl    raw=      1  duckdb=      1
   events_drill-cbf0283b_raw.jsonl    raw=      1  duckdb=      1
   events_drill-cfa0d8b8_raw.jsonl    raw=      1  duckdb=      1
   events_drill-d00fc8ea_raw.jsonl    raw=      1  duckdb=      1
   events_drill-d52824fd_raw.jsonl    raw=      1  duckdb=      1
   events_drill-d9ceaaf4_raw.jsonl    raw=      1  duckdb=      1
   events_drill-db137fe0_raw.jsonl    raw=      1  duckdb=      1
   events_drill-db49db72_raw.jsonl    raw=      1  duckdb=      1
   events_drill-e12bb349_raw.jsonl    raw=      1  duckdb=      1
   events_drill-ee0c0a59_raw.jsonl    raw=      1  duckdb=      1
   events_drill-eecfa6e0_raw.jsonl    raw=      1  duckdb=      1
   events_drill-f32d24a5_raw.jsonl    raw=      1  duckdb=      1
   events_drill-fd6162ab_raw.jsonl    raw=      1  duckdb=      1
   events_drill-ffb6656c_raw.jsonl    raw=      1  duckdb=      1
   events_drill-ffbf3c3e_raw.jsonl    raw=      1  duckdb=      1
   events_drill-w1-0a58f0cc_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-0b11d426_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-34db312a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-3cd7d51d_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-492157b4_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-6d271adc_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-7b404b79_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-83c458e3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-84e95a52_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-8666c2b3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-880d6c63_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-88594682_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-8950fa93_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-9a9aa1cf_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-9d00ecbe_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-a487b31e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-a7dca1b1_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-a891ac9f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-ae2ec1fe_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-bc312def_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-c282cc99_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-c4f6476d_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-ce61eb64_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-cfbbf5e0_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-df619530_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-dfbabb9a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-f0a0e034_raw.jsonl raw=      1  duckdb=      1
   events_drill-w1-f412d6e7_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-0f17b798_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-15925cc8_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-21c3228d_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-3a3c278e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-3cb9b922_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-4432010c_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-44808aaf_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-490bfa8a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-5755b35f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-73ee37b1_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-7674db9e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-78f47f66_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-7a3c94c3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-8a9487be_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-8df21b0a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-8f11abcf_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-bb45409e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-bbf269de_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-bfe352a9_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-c4417ed3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-d1f19d1d_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-d420567f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-d49d7008_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-da30fa00_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-e4234280_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-e905cba6_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-e98122df_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-f6b0f591_raw.jsonl raw=      1  duckdb=      1
   events_drill-w2-f861707f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-05918ff8_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-0871dd55_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-0b0d13c2_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-17503d85_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-1d8edd51_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-1f1dee64_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-407365df_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-5ae48cc7_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-6137911e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-63843315_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-6a945293_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-705dd8e1_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-70e43e05_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-72707b2e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-753b630c_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-8004e461_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-826cb3e9_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-846ea6d0_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-8ba43f75_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-aa748553_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-b10ed9a1_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-b757dd0b_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-be191d7c_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-c65ed335_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-c6baabdf_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-c8a032b0_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-cbb382fe_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-d15ba0ae_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-d20ac93e_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-e7e93ae5_raw.jsonl raw=      1  duckdb=      1
   events_drill-w3-f9970764_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-0908b475_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-0a44d8e0_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-103e1d4a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-2a4fb0f3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-2b43a086_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-2bf7eb31_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-3189989a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-5fc9f0c4_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-66f87097_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-6b91e385_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-877ffacc_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-87cb34c8_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-9265b6a1_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-9ca9309a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-ac9dfd90_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-ba5ab95f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-bf6d236c_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-c3e69873_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-c7c5db4f_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-c91663e3_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-d12c7903_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-dc7b139b_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-dcebc3bf_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-dd9242ce_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-e13d613a_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-e15a8a4b_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-e741a406_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-e8188323_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-ec8e0360_raw.jsonl raw=      1  duckdb=      1
   events_drill-w4-f01c5ac2_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-068dcf2b_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-08f1d87f_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-13461c1c_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-17818983_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-1a9d3193_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-212d50b8_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-21ddc11e_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-269e4196_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-40cd9d69_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-4698ed7c_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-47c7a865_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-4cc23448_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-4fcc8078_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-51ccdb06_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-598e5f17_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-68425c5c_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-6ced61d9_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-6e5a47e7_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-7e8cf331_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-8f6acea7_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-95890638_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-9643b17c_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-9915ff26_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-a32b388b_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-a350d4ec_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-ae0eca5d_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-b1e83da9_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-c81a46a4_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-daa5af97_raw.jsonl raw=      2  duckdb=      2
   events_drill-w5-fafb9755_raw.jsonl raw=      1  duckdb=      1
   events_drill-w5-fb599875_raw.jsonl raw=      2  duckdb=      2
   events_dsh_agent_raw.jsonl         raw=    165  duckdb=    165
   events_dup_agent_raw.jsonl         raw=     84  duckdb=     84
   events_ergo-measure-1_raw.jsonl    raw=      1  duckdb=      1
   events_ergo-measure-2_raw.jsonl    raw=      1  duckdb=      1
   events_ergo-measure-3_raw.jsonl    raw=      1  duckdb=      1
   events_flow_00d69eb5_raw.jsonl     raw=      2  duckdb=      2
   events_flow_066ac1a8_raw.jsonl     raw=      2  duckdb=      2
   events_flow_254cace4_raw.jsonl     raw=      2  duckdb=      2
   events_flow_3636662e_raw.jsonl     raw=      2  duckdb=      2
   events_flow_721520b0_raw.jsonl     raw=      2  duckdb=      2
   events_flow_8277f036_raw.jsonl     raw=      2  duckdb=      2
   events_flow_c7539ddf_raw.jsonl     raw=      2  duckdb=      2
   events_flow_c869988e_raw.jsonl     raw=      2  duckdb=      2
   events_flow_dad49a01_raw.jsonl     raw=      2  duckdb=      2
   events_flow_e5580d3a_raw.jsonl     raw=      2  duckdb=      2
   events_gemini_raw.jsonl            raw=      2  duckdb=      2
   events_glm_local_raw.jsonl         raw=      3  duckdb=      3
   events_grok_raw.jsonl              raw=     70  duckdb=     70
   events_kimi__raw.jsonl             raw=     14  duckdb=     14
   events_kimi_raw.jsonl              raw=  2,261  duckdb=   2261
   events_l1probe_raw.jsonl           raw=      1  duckdb=      1
   events_mcp-boot-regression-0350854f34e4_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-05258c0981cf_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-07305da2d82c_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-088f4fc0adbc_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-091f09ca4dd4_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-0b0338d080e7_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-0b0c0ba497bb_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-171ce4258881_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-18257fbf9e00_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-1d97404ca848_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-2cfc6d5bf300_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-31d08d40e34b_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-38e415f68e0f_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-396aa221e207_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-403586c598be_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-41bd781b0e26_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-423f52252c3b_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-459685dad3f1_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-49262adb9857_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-49b9b332e27c_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-4c977cb073c1_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-4fbf8f9aa2ac_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-52fe6bef59e2_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-53566d82f135_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-56cc4d554ef2_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-5832e6fc9174_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-5f70bfe2b311_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-67a3fecce872_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-6878bd35e0ee_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-68c91ebc0575_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-68ee166d39d9_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-6deb02364364_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-711445846134_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-7b3aab05b4c0_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-7bbb8457350a_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-7ccd2a752bfe_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-83ca9e8bc7d4_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-85b0c710b16a_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-8a8933b99a9f_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-92ed1c244252_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-94402a09053b_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-959b6124c65d_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-9756d507ea5c_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-985b43e80546_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-9d50e2fe794e_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-9f363902e4bb_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-9fcfe1647d5a_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-a7089f6a4d71_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-abd87c2161f4_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-ae95b547078d_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-bf68749c843a_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-c0194b9dfe41_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-c0d38eda172b_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-c16046eb59d9_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-c4fb2f56cce0_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-c75c5661590f_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-c7ecf34384c1_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-c8272dd81a87_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-cb17ec6f568f_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-d26a4f58b903_raw.jsonl raw=      1  duckdb=      1
   events_mcp-boot-regression-d6da45fedd5d_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-d9bc1cbdd563_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-d9d40493b1b5_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-ddd8d4dc78cd_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-e3721d5028ec_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-ea4d609f8c33_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-eb717d8fe04f_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-edfea8c8a958_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-f6b64a56190a_raw.jsonl raw=      2  duckdb=      2
   events_mcp-boot-regression-f77a0f202d25_raw.jsonl raw=      2  duckdb=      2
   events_messy_agent_raw.jsonl       raw=     27  duckdb=     27
   events_mirror_raw.jsonl            raw=    868  duckdb=    868
   events_newborn-gauntlet-1_raw.jsonl raw=      5  duckdb=      5
   events_opal_raw.jsonl              raw=      1  duckdb=      1
   events_operator_raw.jsonl          raw=     15  duckdb=     15
   events_opus-engineer_raw.jsonl     raw=     21  duckdb=     21
   events_p4_scout_wearer_raw.jsonl   raw=     18  duckdb=     18
   events_p6_deep_raw.jsonl           raw=      8  duckdb=      8
   events_parallax_transcript_raw.jsonl raw=      2  duckdb=      2
   events_pintest_raw.jsonl           raw=     31  duckdb=     31
   events_poison_audit_raw.jsonl      raw=      1  duckdb=      1
   events_probeagent_raw.jsonl        raw=      1  duckdb=      1
   events_raw.jsonl                   raw= 19,545  duckdb=  19545
   events_rb25-soak-driver_raw.jsonl  raw=      3  duckdb=      3
   events_rb25-soak-runner_raw.jsonl  raw=     39  duckdb=     39
   events_rb25-storm-driver-2b04a8d97d9a_raw.jsonl raw=      2  duckdb=      2
   events_rb25-storm-driver-47ecc3f46b58_raw.jsonl raw=      2  duckdb=      2
   events_rb25-storm-driver-8a4d414e2a81_raw.jsonl raw=      2  duckdb=      2
   events_rb25-storm-driver-96f4b3b4c389_raw.jsonl raw=      2  duckdb=      2
   events_rb29snd-08865b05_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-1f35cd06_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-20fd05b9_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-45113c21_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-5af80e8f_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-7eda3abc_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-9bf1a3c5_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-a6f577f5_raw.jsonl  raw=      1  duckdb=      1
   events_rb29snd-deb9f11f_raw.jsonl  raw=      2  duckdb=      2
   events_rb29snd-e75b3bed_raw.jsonl  raw=      2  duckdb=      2
   events_rill_raw.jsonl              raw=     10  duckdb=     10
   events_seeder_raw.jsonl            raw=     46  duckdb=     46
   events_slice2agent_0a0104dd_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_16502cf2_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_40481fa7_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_4b4026e4_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_6d73b6ee_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_8d89b236_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_920cf16c_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_a0b78b74_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_f044928d_raw.jsonl raw=      1  duckdb=      1
   events_slice2agent_ff7eaae9_raw.jsonl raw=      1  duckdb=      1
   events_smoke-a1b2c3d4_raw.jsonl    raw=      1  duckdb=      1
   events_sol_raw.jsonl               raw=    339  duckdb=    339
   events_some_unregistered_seat_raw.jsonl raw=     12  duckdb=     12
   events_sonnet-probe_raw.jsonl      raw=      1  duckdb=      1
   events_stream_audit_raw.jsonl      raw=      1  duckdb=      1
   events_sunshine_raw.jsonl          raw=     10  duckdb=     10
   events_system_raw.jsonl            raw=    170  duckdb=    170
   events_t-storm-clr-0d47d2_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-16937e_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-24489e_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-25a84b_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-334756_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-3f0fce_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-47e360_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-5b78ec_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-669264_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-83a4dd_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-842fc1_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-8972c6_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-9c6fcb_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-a4c6d4_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-c26aab_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-cb792c_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-e39e30_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-e9a237_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-clr-ebf3d6_raw.jsonl raw=      1  duckdb=      1
   events_t-storm-dbg2_raw.jsonl      raw=      1  duckdb=      1
   events_t076-4f616b74_raw.jsonl     raw=      1  duckdb=      1
   events_t076-538defa2_raw.jsonl     raw=      1  duckdb=      1
   events_t076-58145239_raw.jsonl     raw=      1  duckdb=      1
   events_t076-5e14447d_raw.jsonl     raw=      1  duckdb=      1
   events_t076-5ea0cbfe_raw.jsonl     raw=      1  duckdb=      1
   events_t076-60b42fae_raw.jsonl     raw=      1  duckdb=      1
   events_t076-8524a83c_raw.jsonl     raw=      1  duckdb=      1
   events_t076-860a77c5_raw.jsonl     raw=      1  duckdb=      1
   events_t076-8c210283_raw.jsonl     raw=      1  duckdb=      1
   events_t076-a4d0c41b_raw.jsonl     raw=      1  duckdb=      1
   events_t076-b5c89b78_raw.jsonl     raw=      1  duckdb=      1
   events_t076-bce9f0dd_raw.jsonl     raw=      1  duckdb=      1
   events_t076-c379083d_raw.jsonl     raw=      1  duckdb=      1
   events_t076-cb82b614_raw.jsonl     raw=      1  duckdb=      1
   events_t076-cd3599f5_raw.jsonl     raw=      1  duckdb=      1
   events_t076-fba7c2d6_raw.jsonl     raw=      1  duckdb=      1
   events_t076-fc2ecc6c_raw.jsonl     raw=      1  duckdb=      1
   events_t076-ff87ec5e_raw.jsonl     raw=      1  duckdb=      1
   events_t083c1-0875c44a_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-16309929_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-1a30fe91_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-1a43bcbf_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-21a69537_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-26c95a8d_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-277ad1bf_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-2b78fd92_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-37d10a3f_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-3b4195d1_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-3ba2c389_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-4c537482_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-5093c5fa_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-5d63b934_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-65abf2a1_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-682cdd79_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-68c98886_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-6bc8a93f_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-6e2ecdb1_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-6f8bf9c5_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-75d13e0c_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-78f465ff_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-7df85d11_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-7f2decd5_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-80eb97cd_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-98db5774_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-9ce04a4c_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-9e3645d2_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-a045ff71_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-ad34c058_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-b48e96be_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-b9f69ac2_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-bf0cfaf4_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-c32a2b92_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-c61da7f6_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-c8174398_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-d016e289_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-ddd924c0_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-e2ba81e6_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-ee0418df_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-ef7066f3_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-f077a65b_raw.jsonl   raw=      1  duckdb=      1
   events_t083c1-f1073805_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-07ad1a7e_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-1692f06c_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-37252bc7_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-404a69d9_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-44f724ac_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-452fb81f_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-490d62ad_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-55adec81_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-5976d79a_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-5e9f5bb9_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-6666cc2e_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-7220b28c_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-7316853d_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-8548c9ea_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-8e99340a_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-92847172_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-9cc0d724_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-a3bf1a0b_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-a771858a_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-a888ffac_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-b88b1a5e_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-c50082a9_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-c5bb68a9_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-c6714b57_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-cf10ae02_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-d349e38f_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-eaef7db2_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-eaf1cc79_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-f45c6442_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-f74f56fb_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-fa6385be_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-fa649a9f_raw.jsonl   raw=      1  duckdb=      1
   events_t086s1-fece0b26_raw.jsonl   raw=      1  duckdb=      1
   events_t11706d883_raw.jsonl        raw=      1  duckdb=      1
   events_t1170ee837_raw.jsonl        raw=      1  duckdb=      1
   events_t11710d2d6_raw.jsonl        raw=      1  duckdb=      1
   events_t1171aad9d_raw.jsonl        raw=      1  duckdb=      1
   events_t1171ad7f0_raw.jsonl        raw=      1  duckdb=      1
   events_t1171d86a4_raw.jsonl        raw=      1  duckdb=      1
   events_t1172299bd_raw.jsonl        raw=      1  duckdb=      1
   events_t117236db0_raw.jsonl        raw=      1  duckdb=      1
   events_t1172570f8_raw.jsonl        raw=      1  duckdb=      1
   events_t117366b3c_raw.jsonl        raw=      1  duckdb=      1
   events_t11736d6db_raw.jsonl        raw=      1  duckdb=      1
   events_t117370704_raw.jsonl        raw=      1  duckdb=      1
   events_t117370c12_raw.jsonl        raw=      1  duckdb=      1
   events_t117377a61_raw.jsonl        raw=      1  duckdb=      1
   events_t117395e0b_raw.jsonl        raw=      1  duckdb=      1
   events_t1173cfc63_raw.jsonl        raw=      1  duckdb=      1
   events_t1174006cd_raw.jsonl        raw=      1  duckdb=      1
   events_t1174a6a57_raw.jsonl        raw=      1  duckdb=      1
   events_t1174d1dae_raw.jsonl        raw=      1  duckdb=      1
   events_t1174e121c_raw.jsonl        raw=      1  duckdb=      1
   events_t117558990_raw.jsonl        raw=      1  duckdb=      1
   events_t117607d01_raw.jsonl        raw=      1  duckdb=      1
   events_t1176273eb_raw.jsonl        raw=      1  duckdb=      1
   events_t117636f14_raw.jsonl        raw=      1  duckdb=      1
   events_t117646e22_raw.jsonl        raw=      1  duckdb=      1
   events_t11767908a_raw.jsonl        raw=      1  duckdb=      1
   events_t1176b6d5d_raw.jsonl        raw=      1  duckdb=      1
   events_t1176fe11f_raw.jsonl        raw=      1  duckdb=      1
   events_t1176ff68e_raw.jsonl        raw=      1  duckdb=      1
   events_t1177cbda6_raw.jsonl        raw=      1  duckdb=      1
   events_t1177cbfbb_raw.jsonl        raw=      1  duckdb=      1
   events_t1177d6ee7_raw.jsonl        raw=      1  duckdb=      1
   events_t11782f250_raw.jsonl        raw=      1  duckdb=      1
   events_t117855e98_raw.jsonl        raw=      1  duckdb=      1
   events_t117861298_raw.jsonl        raw=      1  duckdb=      1
   events_t117896edb_raw.jsonl        raw=      1  duckdb=      1
   events_t1178c56c4_raw.jsonl        raw=      1  duckdb=      1
   events_t1178e77c5_raw.jsonl        raw=      1  duckdb=      1
   events_t11791f8c1_raw.jsonl        raw=      1  duckdb=      1
   events_t11792f96d_raw.jsonl        raw=      1  duckdb=      1
   events_t1179b2e4f_raw.jsonl        raw=      1  duckdb=      1
   events_t1179bbcf3_raw.jsonl        raw=      1  duckdb=      1
   events_t1179f3353_raw.jsonl        raw=      1  duckdb=      1
   events_t117a1792e_raw.jsonl        raw=      1  duckdb=      1
   events_t117a9275a_raw.jsonl        raw=      1  duckdb=      1
   events_t117a97328_raw.jsonl        raw=      1  duckdb=      1
   events_t117ae06cd_raw.jsonl        raw=      1  duckdb=      1
   events_t117b13547_raw.jsonl        raw=      1  duckdb=      1
   events_t117b6eb4e_raw.jsonl        raw=      1  duckdb=      1
   events_t117b705c6_raw.jsonl        raw=      1  duckdb=      1
   events_t117be233c_raw.jsonl        raw=      1  duckdb=      1
   events_t117c030f4_raw.jsonl        raw=      1  duckdb=      1
   events_t117c0980e_raw.jsonl        raw=      1  duckdb=      1
   events_t117c30bb7_raw.jsonl        raw=      1  duckdb=      1
   events_t117c32c8d_raw.jsonl        raw=      1  duckdb=      1
   events_t117c7628c_raw.jsonl        raw=      1  duckdb=      1
   events_t117c97ecc_raw.jsonl        raw=      1  duckdb=      1
   events_t117c9944a_raw.jsonl        raw=      1  duckdb=      1
   events_t117c9daec_raw.jsonl        raw=      1  duckdb=      1
   events_t117cd5818_raw.jsonl        raw=      1  duckdb=      1
   events_t117d0ca81_raw.jsonl        raw=      1  duckdb=      1
   events_t117d3a03f_raw.jsonl        raw=      1  duckdb=      1
   events_t117df2705_raw.jsonl        raw=      1  duckdb=      1
   events_t117e3d483_raw.jsonl        raw=      1  duckdb=      1
   events_t117e47869_raw.jsonl        raw=      1  duckdb=      1
   events_t117e6f431_raw.jsonl        raw=      1  duckdb=      1
   events_t117e74901_raw.jsonl        raw=      1  duckdb=      1
   events_t117e8c043_raw.jsonl        raw=      1  duckdb=      1
   events_t117e96384_raw.jsonl        raw=      1  duckdb=      1
   events_t117e978e5_raw.jsonl        raw=      1  duckdb=      1
   events_t117e992fd_raw.jsonl        raw=      1  duckdb=      1
   events_t117f86a19_raw.jsonl        raw=      1  duckdb=      1
   events_t117f8e00f_raw.jsonl        raw=      1  duckdb=      1
   events_t196csnd-370ccb86_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-4190434a_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-4ba4f4b6_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-66f4e7b8_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-df3e22b4_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-e75db724_raw.jsonl raw=      1  duckdb=      1
   events_t196csnd-ea0ba7dd_raw.jsonl raw=      1  duckdb=      1
   events_tester_raw.jsonl            raw=     12  duckdb=     12
   events_unknown_raw.jsonl           raw=    837  duckdb=    837
   events_user_raw.jsonl              raw=     49  duckdb=     49
   events_w13-probe_raw.jsonl         raw=     50  duckdb=     50
   events_wrap_raw.jsonl              raw=     22  duckdb=     22
   recall_outcome.jsonl               raw= 20,000  duckdb=  20000
   recall_surface.jsonl               raw=  6,000  duckdb=   6000

-- are the dropped lines valid JSON per python? --
```

## Row-count parity: per-file DuckDB counts vs raw line counts

*background task bpgjyrghb, verbatim output*

```text
=== sum of per-file duckdb counts vs per-file raw counts ===
raw_sum=66024  duckdb_sum=66024  diff=0

=== do any ledger files lack a trailing newline? (wc -l undercounts those) ===
```

## ClickBench result-file dates per system (how fresh are the public numbers)

*background task bqlf7idc0, verbatim output*

```text
=== duckdb ===
20220701, 20221115, 20221204, 20221205, 20230926, 20241126, 20250205, 20250522, 20250710, 20250711, 20250712, 20250830, 20250831, 20250916, 20251009, 20251026, 20260509, 20260510, 20260511, 
=== duckdb-parquet ===
20221115, 20230926, 20241127, 20250205, 20250710, 20250711, 20250712, 20250828, 20250830, 20250831, 20250916, 20251009, 20251026, 20260509, 20260510, 20260511, 
=== duckdb-memory ===
20241126, 20250710, 20250712, 20250830, 20250831, 20250916, 20251009, 20260511, 
=== duckdb-dataframe ===
20240909, 20241127, 20250907, 20250916, 20251009, 20251214, 20251215, 20260219, 20260511, 
=== clickhouse ===
20160601, 20200812, 20220701, 20221004, 20221010, 20221018, 20221019, 20221021, 20221022, 20221118, 20230213, 20230214, 20230215, 20230227, 20230314, 20230609, 20230727, 20230901, 20231209, 20240131, 20240207, 20240213, 20241106, 20250409, 20250608, 20250609, 20250620, 20250710, 20250711, 20250712, 20250817, 20250830, 20250831, 20251009, 20251103, 20251219, 20260203, 20260210, 20260309, 20260327, 20260501, 20260505, 20260507, 20260508, 20260509, 20260510, 20260511, 20260516, 20260624, 20260719, 20260720, 20260721, 20260722, 20260723, 20260724, 20260725, 20260726, 20260727, 20260728, 20260729, 20260730, 20260731, 20260801, 20260802, 20260803, 20260804, 20260805, 20260806, 20260807, 20260808, 20260809, 20260810, 20260811, 20260812, 20260813, 20260814, 20260815, 20260816, 20260817, 20260818, 20260819, 20260820, 20260821, 20260822, 20260823, 20260824, 20260825, 20260826, 20260827, 20260828, 20260829, 20260830, 20260831, 20260901, 20260902, 20260903, 20260904, 20260905, 20260906, 20260907, 20260908, 20260909, 20260910, 20260911, 20260912, 20260913, 20260914, 20260915, 20260916, 20260917, 20260918, 20260919, 20260920, 20260921, 20260922, 20260923, 20260924, 
=== chdb ===
20230403, 20230505, 20231203, 20240704, 20241212, 20250710, 20250711, 20250712, 20250830, 20250831, 20251110, 20260221, 20260309, 20260505, 20260509, 20260510, 20260511, 20260813, 20260816, 
=== sqlite ===
20220701, 20250711, 20250712, 
=== pandas ===
20240909, 20260218, 20260824, 
=== polars ===
20240909, 20241129, 20241215, 20250712, 20250830, 20260114, 20260218, 20260509, 20260510, 20260511, 20260813, 20260824, 
=== polars-dataframe ===
20241129, 20250710, 20250711, 20250712, 20250830, 20251214, 20251215, 20260114, 20260218, 20260509, 20260510, 20260813, 20260824, 

[exited with code 0]
```

## Vector-search libraries: last commit and latest release (GitHub API)

*background task bz4paaq7o, verbatim output*

```text
unum-cloud/usearch | last_default_commit=2026-08-31T22:40:51Z | latest_release=v2.26.2 @ 2026-08-31T22:40:54Z
nmslib/hnswlib | last_default_commit=2026-09-14T11:48:05Z | latest_release=v0.9.0 @ 2026-03-28T22:48:34Z
facebookresearch/faiss | last_default_commit=2026-09-24T21:08:11Z | latest_release=v1.15.1 @ 2026-09-16T19:24:02Z
kyamagu/faiss-wheels | last_default_commit=2026-06-08T01:49:09Z | latest_release=v1.13.2 @ 2025-12-23T23:48:21Z
chroma-core/chroma | last_default_commit=2026-09-24T20:25:26Z | latest_release=1.5.9 @ 2026-05-05T05:55:40Z
qdrant/qdrant | last_default_commit=2026-09-03T12:36:18Z | latest_release=v1.19.1 @ 2026-09-04T07:59:14Z
1yefuwang1/vectorlite | last_default_commit=2026-06-23T11:41:44Z | latest_release=v0.2.0 @ 2024-08-19T14:10:40Z
pgvector/pgvector | last_default_commit=2026-09-22T18:39:20Z | no_release_or_ERR
lancedb/lancedb | last_default_commit=2026-09-24T15:47:00Z | latest_release=v0.39.0 @ 2026-09-17T20:59:02Z
lancedb/lance | last_default_commit=2026-09-24T18:08:39Z | latest_release=v12.0.0 @ 2026-09-17T16:25:11Z
spotify/voyager | last_default_commit=2026-03-01T06:05:51Z | latest_release=v2.1.1 @ 2025-09-23T12:26:10Z
spotify/annoy | last_default_commit=2025-10-29T14:08:37Z | latest_release=v1.17.2 @ 2023-04-10T15:01:29Z
milvus-io/milvus-lite | last_default_commit=2026-08-25T02:52:19Z | latest_release=v3.2.1 @ 2026-08-25T02:56:07Z
asg017/sqlite-vss | last_default_commit=2024-05-05T20:00:16Z | latest_release=v0.1.2 @ 2023-08-06T02:26:05Z
```

## Source: bench.py

```python
"""Real-data benchmark: Akashic ledger JSONL -> query engines. Windows, py3.11."""
import json, os, sqlite3, sys, time, pathlib, shutil, gc

SRC = pathlib.Path(r"E:\AI-Setup\state\bus-export\bifrost_broadcast.jsonl")
WORK = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".") / "bench"
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 1
if WORK.exists(): shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True, exist_ok=True)

def mb(p):
    p = pathlib.Path(p)
    if p.is_dir(): return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())/1048576
    return p.stat().st_size/1048576 if p.exists() else 0.0

class T:
    def __init__(s,label): s.label=label
    def __enter__(s): gc.collect(); s.t=time.perf_counter(); return s
    def __exit__(s,*a): s.d=time.perf_counter()-s.t; print(f"  {s.label:<46} {s.d*1000:9.1f} ms")

# ---- build the input (scaled by replication, distinct ids) ----
SRCF = WORK/"input.jsonl"
n = 0
with open(SRCF,"w",encoding="utf-8") as out, open(SRC,encoding="utf-8") as f:
    base = f.readlines()
for rep in range(SCALE):
    with open(SRCF,"a",encoding="utf-8") as out:
        for ln in base:
            # perturb id per replica so ids stay unique (avoids unrealistic dedup on the key)
            out.write(ln.replace('"id": "1786', f'"id": "{rep:04d}86', 1) if rep else ln); n += 1
print(f"INPUT: {n:,} rows, {mb(SRCF):.1f} MB  (scale x{SCALE})\n")

results = {}

# ================= SQLite: naive (whole line as TEXT json) =================
print("SQLite A - raw JSON TEXT column + json_extract at query time")
db = WORK/"a.db"
con = sqlite3.connect(db); con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=off")
con.execute("create table ev(line text)")
with T("  ingest"):
    with open(SRCF,encoding="utf-8") as f:
        con.executemany("insert into ev values(?)", ((l,) for l in f))
    con.commit()
results["sqlite_raw_ingest"]=_=None
with T("  groupby frm,kind (json_extract)"):
    r=con.execute("select line->>'$.fields.frm' a, line->>'$.fields.kind' b, count(*) from ev group by 1,2 order by 3 desc limit 5").fetchall()
with T("  filter+count on ts prefix"):
    c=con.execute("select count(*) from ev where line->>'$.fields.ts' like '2026-08%'").fetchone()
with T("  substring scan in content"):
    c2=con.execute("select count(*) from ev where line->>'$.fields.content' like '%Bifrost%'").fetchone()
print(f"  -> size {mb(db):.1f} MB   top={r[:2]}  ts_hits={c[0]:,}  substr={c2[0]:,}")
con.close(); print()

# ================= SQLite: shredded columns + index =================
print("SQLite B - shredded typed columns + indexes (the 'do it properly' version)")
db2 = WORK/"b.db"
con = sqlite3.connect(db2); con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=off")
con.execute("create table ev(id text, frm text, to_ text, kind text, ts text, len int, content text, meta blob)")
def rows():
    with open(SRCF,encoding="utf-8") as f:
        for l in f:
            d=json.loads(l); fl=d.get("fields",{})
            yield (d.get("id"), fl.get("frm"), fl.get("to"), fl.get("kind"), fl.get("ts"),
                   int(fl.get("len") or 0), fl.get("content"), fl.get("meta"))
with T("  ingest (python json parse + shred)"):
    con.executemany("insert into ev values(?,?,?,?,?,?,?,jsonb(?))", rows()); con.commit()
with T("  create indexes (kind,frm),(ts)"):
    con.execute("create index i1 on ev(kind,frm)"); con.execute("create index i2 on ev(ts)"); con.commit()
with T("  groupby frm,kind (indexed)"):
    r=con.execute("select frm,kind,count(*) from ev group by 1,2 order by 3 desc limit 5").fetchall()
with T("  filter+count on ts prefix (indexed)"):
    c=con.execute("select count(*) from ev where ts like '2026-08%'").fetchone()
with T("  substring scan in content"):
    c2=con.execute("select count(*) from ev where content like '%Bifrost%'").fetchone()
with T("  sum(len) group by kind"):
    s=con.execute("select kind,sum(len),avg(len) from ev group by 1 order by 2 desc limit 3").fetchall()
with T("  point lookup by id (indexed scan)"):
    con.execute("select * from ev where id=?", (r and base[0] and json.loads(base[0])['id'],)).fetchall()
print(f"  -> size {mb(db2):.1f} MB  ts_hits={c[0]:,} substr={c2[0]:,}")
con.close(); print()

# ================= SQLite FTS5 =================
print("SQLite C - FTS5 full-text index over content")
db3 = WORK/"c.db"
con = sqlite3.connect(db3); con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=off")
con.execute("create virtual table ft using fts5(content, frm, kind, tokenize='unicode61')")
def rows2():
    with open(SRCF,encoding="utf-8") as f:
        for l in f:
            fl=json.loads(l).get("fields",{})
            yield (fl.get("content"), fl.get("frm"), fl.get("kind"))
with T("  build FTS5 index"):
    con.executemany("insert into ft values(?,?,?)", rows2()); con.commit()
with T("  MATCH 'Bifrost' count"):
    c=con.execute("select count(*) from ft where ft match 'Bifrost'").fetchone()
with T("  MATCH ranked top-10 bm25"):
    rr=con.execute("select frm,kind,bm25(ft) from ft where ft match 'Bifrost OR wake' order by bm25(ft) limit 10").fetchall()
with T("  optimize"):
    con.execute("insert into ft(ft) values('optimize')"); con.commit()
print(f"  -> size {mb(db3):.1f} MB  match_hits={c[0]:,}")
con.close(); print()

# ================= DuckDB =================
print("DuckDB - read_json_auto / native store / parquet")
import duckdb
ddb = WORK/"d.duckdb"
con = duckdb.connect(str(ddb))
with T("  ingest via read_json_auto -> native table"):
    con.execute(f"create table ev as select * from read_json_auto('{SRCF.as_posix()}')")
with T("  groupby frm,kind"):
    r=con.execute("select fields.frm, fields.kind, count(*) c from ev group by 1,2 order by c desc limit 5").fetchall()
with T("  filter+count on ts prefix"):
    c=con.execute("select count(*) from ev where fields.ts::varchar like '2026-08%'").fetchone()
with T("  substring scan in content"):
    c2=con.execute("select count(*) from ev where fields.content like '%Bifrost%'").fetchone()
with T("  sum/avg(len::int) group by kind"):
    s=con.execute("select fields.kind, sum(try_cast(fields.len as bigint)) t from ev group by 1 order by t desc nulls last limit 3").fetchall()
pq = WORK/"ev.parquet"
with T("  export -> parquet(zstd)"):
    con.execute(f"copy ev to '{pq.as_posix()}' (format parquet, compression zstd)")
with T("  groupby DIRECTLY over parquet (no import)"):
    r2=con.execute(f"select fields.frm, fields.kind, count(*) c from '{pq.as_posix()}' group by 1,2 order by c desc limit 5").fetchall()
with T("  groupby DIRECTLY over raw jsonl (no import)"):
    r3=con.execute(f"select fields.frm, count(*) c from read_json_auto('{SRCF.as_posix()}') group by 1 order by c desc limit 3").fetchall()
con.close()
print(f"  -> duckdb file {mb(ddb):.1f} MB | parquet+zstd {mb(pq):.1f} MB  ts_hits={c[0]:,} substr={c2[0]:,}")
print(); print()

# ================= Polars =================
print("Polars - scan_ndjson / parquet")
import polars as pl
with T("  read_ndjson -> DataFrame (eager)"):
    df = pl.read_ndjson(SRCF)
with T("  groupby frm,kind"):
    g = df.unnest("fields").group_by(["frm","kind"]).len().sort("len",descending=True).head(5)
with T("  filter+count ts prefix"):
    cc = df.unnest("fields").filter(pl.col("ts").cast(pl.String).str.starts_with("2026-08")).height
with T("  substring scan content"):
    c2 = df.unnest("fields").filter(pl.col("content").str.contains("Bifrost",literal=True)).height
ppq = WORK/"pl.parquet"
with T("  write parquet(zstd)"):
    df.unnest("fields").write_parquet(ppq, compression="zstd")
with T("  LAZY scan_parquet groupby (projection pushdown)"):
    g2 = pl.scan_parquet(ppq).group_by(["frm","kind"]).len().sort("len",descending=True).head(5).collect()
with T("  LAZY scan_ndjson groupby"):
    try:
        g3 = pl.scan_ndjson(SRCF).select(pl.col("fields")).collect().height
    except Exception as e:
        print("   scan_ndjson err:", str(e)[:80])
print(f"  -> parquet {mb(ppq):.1f} MB  ts_hits={cc:,} substr={c2:,}")
print()

# ================= DataFusion =================
print("DataFusion")
try:
    from datafusion import SessionContext
    ctx = SessionContext()
    with T("  register parquet + groupby"):
        ctx.register_parquet("ev", str(ppq))
        rr = ctx.sql("select frm, kind, count(*) c from ev group by 1,2 order by c desc limit 5").collect()
    with T("  filter+count over parquet"):
        rr2 = ctx.sql("select count(*) from ev where arrow_cast(ts,'Utf8') like '2026-08%'").collect()
    with T("  substring scan over parquet"):
        rr3 = ctx.sql("select count(*) from ev where content like '%Bifrost%'").collect()
except Exception as e:
    print("  DataFusion error:", str(e)[:200])
print()

print("=== SIZES ON DISK ===")
for lbl,p in [("input.jsonl",SRCF),("sqlite raw-json",WORK/"a.db"),("sqlite shredded+idx",WORK/"b.db"),
              ("sqlite FTS5",WORK/"c.db"),("duckdb native",ddb),("parquet zstd (duckdb)",pq),("parquet zstd (polars)",ppq)]:
    print(f"  {lbl:<26} {mb(p):8.1f} MB")
```

## Source: bench2.py

```python
"""Crossover + append-only + hybrid-retrieval benchmark."""
import json, sqlite3, sys, time, pathlib, shutil, gc, struct, os
SRC = pathlib.Path(r"E:\AI-Setup\state\bus-export\bifrost_broadcast.jsonl")
W = pathlib.Path(sys.argv[1])/"bench2"
if W.exists(): shutil.rmtree(W, ignore_errors=True)
W.mkdir(parents=True, exist_ok=True)
base = open(SRC, encoding="utf-8").readlines()
def mb(p):
    p=pathlib.Path(p)
    if p.is_dir(): return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())/1048576
    return p.stat().st_size/1048576 if p.exists() else 0.0
def tm(fn, n=3):
    best=1e9
    for _ in range(n):
        gc.collect(); t=time.perf_counter(); fn(); best=min(best,time.perf_counter()-t)
    return best*1000

import duckdb, polars as pl

# ============ PART 1: crossover sweep ============
print("="*74)
print("PART 1  CROSSOVER SWEEP - groupby(frm,kind) + filter, SQLite(indexed) vs DuckDB")
print("="*74)
print(f"{'rows':>10} {'MB':>7} | {'SQLite gb':>10} {'DuckDB gb':>10} | {'SQLite filt':>12} {'DuckDB filt':>12} | {'SQLite sum':>11} {'DuckDB sum':>11}")
for scale in (1, 3, 6, 12):
    f = W/f"in{scale}.jsonl"
    with open(f,"w",encoding="utf-8") as o:
        for rep in range(scale):
            for ln in base: o.write(ln.replace('"id": "1786', f'"id": "{rep:04d}86',1) if rep else ln)
    nrows = len(base)*scale
    # sqlite shredded
    db=W/f"s{scale}.db"; con=sqlite3.connect(db)
    con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=off"); con.execute("pragma cache_size=-200000")
    con.execute("create table ev(id text, frm text, kind text, ts text, len int, content text)")
    def rws():
        with open(f,encoding="utf-8") as fh:
            for l in fh:
                d=json.loads(l); fl=d.get("fields",{})
                yield (d.get("id"), fl.get("frm"), fl.get("kind"), fl.get("ts"), int(fl.get("len") or 0), fl.get("content"))
    con.executemany("insert into ev values(?,?,?,?,?,?)", rws()); con.commit()
    con.execute("create index i1 on ev(kind,frm)"); con.execute("create index i2 on ev(ts)"); con.commit()
    s_gb=tm(lambda: con.execute("select frm,kind,count(*) from ev group by 1,2 order by 3 desc limit 5").fetchall())
    s_f =tm(lambda: con.execute("select count(*) from ev where ts like '2026-08%'").fetchone())
    s_s =tm(lambda: con.execute("select kind,sum(len),avg(len) from ev group by 1 order by 2 desc limit 3").fetchall())
    con.close()
    # duckdb native
    dd=W/f"d{scale}.duckdb"; dcon=duckdb.connect(str(dd))
    dcon.execute(f"create table ev as select fields.frm frm, fields.kind kind, fields.ts::varchar ts, try_cast(fields.len as bigint) len, struct_extract(fields, 'content') AS body from read_json_auto('{f.as_posix()}')")
    d_gb=tm(lambda: dcon.execute("select frm,kind,count(*) c from ev group by 1,2 order by c desc limit 5").fetchall())
    d_f =tm(lambda: dcon.execute("select count(*) from ev where ts like '2026-08%'").fetchone())
    d_s =tm(lambda: dcon.execute("select kind,sum(len),avg(len) t from ev group by 1 order by 2 desc limit 3").fetchall())
    dcon.close()
    print(f"{nrows:>10,} {mb(f):>7.0f} | {s_gb:>9.1f}m {d_gb:>9.1f}m | {s_f:>11.1f}m {d_f:>11.1f}m | {s_s:>10.1f}m {d_s:>10.1f}m")
    for p in (db, dd, f):
        try: os.remove(p)
        except Exception: pass
    for suf in ("-wal","-shm"):
        try: os.remove(str(db)+suf)
        except Exception: pass

# ============ PART 2: append-only pattern ============
print()
print("="*74)
print("PART 2  APPEND-ONLY: cost of adding ONE day of new events to an existing store")
print("="*74)
BIG = W/"big.jsonl"; NEW = W/"new.jsonl"
with open(BIG,"w",encoding="utf-8") as o:
    for rep in range(6):
        for ln in base: o.write(ln.replace('"id": "1786', f'"id": "{rep:04d}86',1) if rep else ln)
with open(NEW,"w",encoding="utf-8") as o:
    for ln in base[:5000]: o.write(ln.replace('"id": "1786','"id": "9986',1))
print(f"existing: {len(base)*6:,} rows / {mb(BIG):.0f} MB   increment: 5,000 rows / {mb(NEW):.1f} MB")

def shred(path):
    with open(path,encoding="utf-8") as fh:
        for l in fh:
            d=json.loads(l); fl=d.get("fields",{})
            yield (d.get("id"), fl.get("frm"), fl.get("kind"), fl.get("ts"), int(fl.get("len") or 0), fl.get("content"))

db=W/"ap.db"; con=sqlite3.connect(db)
con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=normal")
con.execute("create table ev(id text, frm text, kind text, ts text, len int, content text)")
con.executemany("insert into ev values(?,?,?,?,?,?)", shred(BIG)); con.commit()
con.execute("create index i1 on ev(kind,frm)"); con.commit()
t=time.perf_counter(); con.executemany("insert into ev values(?,?,?,?,?,?)", shred(NEW)); con.commit()
print(f"  SQLite  append 5k rows (indexed table, WAL)            {(time.perf_counter()-t)*1000:9.1f} ms   -> {mb(db):.0f} MB")
con.close()

dd=W/"ap.duckdb"; dcon=duckdb.connect(str(dd))
dcon.execute(f"create table ev as select fields.frm frm, fields.kind kind, fields.ts::varchar ts from read_json_auto('{BIG.as_posix()}')")
t=time.perf_counter()
dcon.execute(f"insert into ev select fields.frm, fields.kind, fields.ts::varchar from read_json_auto('{NEW.as_posix()}')")
print(f"  DuckDB  append 5k rows into native table               {(time.perf_counter()-t)*1000:9.1f} ms   -> {mb(dd):.0f} MB")
dcon.close()

# parquet-per-batch (the 'middle path')
PD = W/"parts"; PD.mkdir(exist_ok=True)
dcon=duckdb.connect()
dcon.execute(f"copy (select fields.frm frm, fields.kind kind, fields.ts::varchar ts from read_json_auto('{BIG.as_posix()}')) to '{(PD/'p000.parquet').as_posix()}' (format parquet, compression zstd)")
t=time.perf_counter()
dcon.execute(f"copy (select fields.frm frm, fields.kind kind, fields.ts::varchar ts from read_json_auto('{NEW.as_posix()}')) to '{(PD/'p001.parquet').as_posix()}' (format parquet, compression zstd)")
tap=(time.perf_counter()-t)*1000
print(f"  Parquet write NEW batch as its own file (no rewrite)   {tap:9.1f} ms   -> {mb(PD):.0f} MB total")
glob=(PD/'*.parquet').as_posix()
q=tm(lambda: dcon.execute(f"select frm,kind,count(*) c from '{glob}' group by 1,2 order by c desc limit 5").fetchall())
print(f"  DuckDB  groupby across the parquet DIRECTORY (2 files) {q:9.1f} ms")
q2=tm(lambda: pl.scan_parquet(glob).group_by(["frm","kind"]).len().sort("len",descending=True).head(5).collect())
print(f"  Polars  lazy groupby across same parquet directory     {q2:9.1f} ms")
try:
    from datafusion import SessionContext
    ctx=SessionContext(); ctx.register_parquet("ev", str(PD))
    q3=tm(lambda: ctx.sql("select frm,kind,count(*) c from ev group by 1,2 order by c desc limit 5").collect())
    print(f"  DataFusion groupby across same parquet directory       {q3:9.1f} ms")
except Exception as e: print("  DataFusion dir err:", str(e)[:120])
# and read one parquet file with plain pyarrow (no engine at all)
import pyarrow.dataset as ds, pyarrow.compute as pc
q4=tm(lambda: ds.dataset(str(PD), format="parquet").to_table(columns=["frm","kind"]).group_by(["frm","kind"]).aggregate([([],"count_all")]))
print(f"  PyArrow  dataset groupby, NO query engine              {q4:9.1f} ms")
dcon.close()

# ============ PART 3: hybrid retrieval ============
print()
print("="*74)
print("PART 3  RETRIEVAL: BM25 (FTS5) + brute-force vector KNN (sqlite-vec) on ONE sqlite file")
print("="*74)
import sqlite_vec, random
N = 50000
texts = [json.loads(l).get("fields",{}).get("content") or "" for l in base[:N]]
db=W/"hy.db"; con=sqlite3.connect(db); con.enable_load_extension(True); sqlite_vec.load(con); con.enable_load_extension(False)
con.execute("pragma journal_mode=WAL"); con.execute("pragma synchronous=off")
con.execute("create virtual table ft using fts5(content)")
t=time.perf_counter(); con.executemany("insert into ft values(?)", ((x,) for x in texts)); con.commit()
print(f"  FTS5 index {N:,} docs                                  {(time.perf_counter()-t)*1000:9.1f} ms")
DIM=384
random.seed(0)
con.execute(f"create virtual table vec using vec0(id integer primary key, emb float[{DIM}])")
t=time.perf_counter()
con.executemany("insert into vec(id,emb) values(?,?)",
    ((i, struct.pack(f"{DIM}f", *[random.random() for _ in range(DIM)])) for i in range(N)))
con.commit()
print(f"  sqlite-vec store {N:,} x {DIM}d float32 vectors          {(time.perf_counter()-t)*1000:9.1f} ms   -> {mb(db):.0f} MB total")
qv = struct.pack(f"{DIM}f", *[random.random() for _ in range(DIM)])
kn=tm(lambda: con.execute("select id,distance from vec where emb match ? and k=10 order by distance",(qv,)).fetchall(), n=5)
print(f"  brute-force KNN top-10 over {N:,} vectors             {kn:9.1f} ms")
bm=tm(lambda: con.execute("select rowid,bm25(ft) from ft where ft match 'Bifrost OR wake' order by bm25(ft) limit 10").fetchall(), n=5)
print(f"  FTS5 BM25 top-10                                      {bm:9.1f} ms")
def hybrid():
    a=con.execute("select rowid,bm25(ft) from ft where ft match 'Bifrost OR wake' order by bm25(ft) limit 50").fetchall()
    b=con.execute("select id,distance from vec where emb match ? and k=50 order by distance",(qv,)).fetchall()
    rr={}
    for r,(i,_) in enumerate(a): rr[i]=rr.get(i,0)+1/(60+r+1)
    for r,(i,_) in enumerate(b): rr[i]=rr.get(i,0)+1/(60+r+1)
    return sorted(rr.items(), key=lambda x:-x[1])[:10]
hy=tm(hybrid, n=5)
print(f"  HYBRID BM25+KNN with reciprocal-rank fusion, top-10   {hy:9.1f} ms")
con.close()
print(f"\n  one sqlite file holds rows + BM25 + vectors: {mb(db):.0f} MB, zero servers, zero containers")

# scale vector brute force
print()
for n in (100_000, 250_000):
    con=sqlite3.connect(":memory:"); con.enable_load_extension(True); sqlite_vec.load(con); con.enable_load_extension(False)
    con.execute(f"create virtual table vec using vec0(id integer primary key, emb float[{DIM}])")
    con.executemany("insert into vec(id,emb) values(?,?)",
        ((i, struct.pack(f"{DIM}f", *[random.random() for _ in range(DIM)])) for i in range(n)))
    k=tm(lambda: con.execute("select id,distance from vec where emb match ? and k=10 order by distance",(qv,)).fetchall(), n=5)
    print(f"  brute-force KNN top-10 over {n:>7,} x {DIM}d vectors  {k:9.1f} ms  (in-memory)")
    con.close()
```
