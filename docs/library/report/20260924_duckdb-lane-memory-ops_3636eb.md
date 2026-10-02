---
akashic_id: art_20260924_duckdb-lane-memory-ops_3636eb
akashic_sha: 741587c49da9
schema_version: 1
status: current
type: report
arc: duckdb-deep-dive
date: 2026-09-24
title: duckdb-lane-memory-ops
gist: "# DuckDB deep dive, re-run -- lane: memory-ops *2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per"
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-24T21:31:42"
updated: "2026-09-24T21:31:42"
---
<!-- GENERATED PROJECTION of art_20260924_duckdb-lane-memory-ops_3636eb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# duckdb-lane-memory-ops

# DuckDB deep dive, re-run -- lane: memory-ops

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent acf5c610a28e509da (claude-opus-5-5) ran 21:01-21:30 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\memory-ops (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight: the machine ran out of memory (commit near its 124 GB limit, 1 fps cursor) and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md. Read operational-limits and local-benchmarks-and-census first. Build on them; do not redo what they settled.

GUARDRAILS (this lane deliberately measures memory; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- For local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1; psutil is available through system site-packages). Install nothing anywhere else.
- NEVER run DuckDB with its default memory_limit. Always set memory_limit explicitly (at most 3GB) and threads at most 4, with temp_directory inside your lane dir. Run one measurement process at a time. Abort any run whose working set passes 4 GB.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\memory-ops\. Create files only there. The ledgers in E:\AI-Setup are READ-ONLY.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: memory-ops. Question: how do we run DuckDB and Polars SAFELY on this one shared 62 GB machine, where several agents may each start a process?

Research the defaults and behaviour:
- DuckDB's memory_limit default (about 80% of RAM, PER PROCESS);
- its threads default (all cores);
- spilling to temp_directory, which operators can and cannot spill, and behaviour under OS memory pressure on Windows;
- Polars' streaming engine, and the memory profile of eager versus lazy.

Then MEASURE locally on our real ledgers (E:\AI-Setup\state\bus-export\*.jsonl). Sample the child process with psutil and record the peak working set and the peak private bytes of one realistic query (a group-by plus a filter over all bus-export files) at memory_limit 512MB, 1GB and 3GB. Do the same for the Polars lazy and streaming equivalents.

Conclude with house settings: memory_limit, threads, temp_directory, and a per-process budget formula for N concurrent agents. Add a one-paragraph "how not to crash the machine" rule.

## The report (verbatim)

Everything we saw fits a simple rule. Always cap DuckDB explicitly, keep Polars out of long-running agents, and wrap any heavy query in a Windows Job Object. A Job Object is a hard memory ceiling that Windows enforces on one process.

I could not write REPORT.md because the harness blocks report files from subagents, so this message is the whole report. The raw data (50 runs) is in `...\scratchpad\duckdb-lanes\memory-ops\results.jsonl`, along with `probe.py`, `runner.py` and `logs\`. "MB" below means MiB.

## Headline
- **The defaults are the danger.** Every DuckDB database instance defaults to a 50 GiB memory cap and 32 threads on this box. Polars defaults to 32 threads and has no memory cap at all.
- **An explicit DuckDB `memory_limit` held.** In all 23 capped runs, peak private bytes stayed within the cap plus 120 MB. Every failure came back as an ordinary error the caller can catch.
- **Polars 1.39.3 can neither cap nor spill to disk.** On a group-by with millions of distinct groups, its streaming engine used more memory than its in-memory engine. A Polars process also keeps its peak memory after the query finishes.
- **House rule:** DuckDB at 1 GiB and 2 threads per process. Heavy work runs in a short-lived child process under a Job Object cap, and a machine-wide slot count limits how many run at once.

## Findings
**Defaults**
1. **[sourced+measured] The DuckDB default is 50.0 GiB and 32 threads per instance here.**
   - Source (DuckDB v1.5.5, `src/common/file_system.cpp` and `src/main/config.cpp`, read 2026-09-24): on Windows the default is 80% of *installed* RAM from `GetPhysicallyInstalledSystemMemory`, with KB multiplied by 1000. Threads = `std::thread::hardware_concurrency()`. Container and cluster limits are only checked on Linux. The docs say "80% of RAM" and "# CPU cores" (duckdb.org/docs/current/configuration/overview).
   - Inputs measured on this machine: 67,108,864 KB installed, so the default is 53,687,091,200 B = 50.0 GiB per instance, and threads = 32.
   - The default ignores the 42-45 GiB other processes had already committed tonight. Three default instances could legally claim 150 GiB against a 123.6 GiB commit limit.
   - I worked the value out from source and did not open DuckDB with defaults, per the guardrail.
2. **[measured] The cap is per instance, not per process.** Two `duckdb.connect(':memory:')` instances at 512MB each, in one process, peaked at 1,049 MB.
3. **[measured] Size units are decimal.** `'1GB'` means 953.6 MiB. `'1GiB'` is accepted and exact.

**Realistic query.** All 388 bus-export files (160.2 MB, 223,910 rows), filtered on `ts >= '2026-09-01' AND kind <> 'trace'` and grouped by `frm, kind`. Every engine returned the same 130 rows. Peaks are the process's own OS-recorded peaks; a 20 ms psutil sampler acted as the 4 GB watchdog. The file cache was warm.

| engine | threads | peak WS | peak private | s |
|---|---|---|---|---|
| DuckDB 512MB / 1GB / 3GB | 4 | 156/156/157 | 180/180/180 | 0.05 |
| DuckDB 1GB | 2 / 1 | 116 / 80 | 106 / 67 | 0.08 / 0.16 |
| Polars lazy (in-memory) | 4 / 1 | 223 / 202 | 333 / 259 | 0.15 / 0.37 |
| Polars streaming | 4 / 1 | 128 / 112 | 120 / 82 | 0.13 / 0.37 |
| Polars eager | 4 | 244 | 320 | 0.38 |

WS is working set (memory actually touched); private is committed memory.

4. **[measured] At our data size, threads decide memory, not the cap.** Each DuckDB thread costs about 38 MB for a JSON scan, and repeat runs agreed within 2 MB. [inferred] At the default 32 threads, this query would need about 1.2 GB.

**Stress query.** The same files multiplied 12× (`CROSS JOIN range(12)`), grouped by `stream, id, rep` with `any_value(payload)`: 2,543,544 groups carrying 0.99 G characters.

5. **[measured] GROUP BY spills to disk, but not when each group carries a large string.**
   - DuckDB at 512MB (1, 2 and 4 threads) and at 1GB (1 and 4 threads, also with `preserve_insertion_order=false`) failed. The error was `Out of Memory Error: failed to allocate data of size 16.0 MiB (944.9 MiB/953.6 MiB used)`, after spilling up to 268 MB.
   - 2GB succeeded: 1.03 s, 552 MB spilled, 2,012 MB private.
   - 3GB succeeded: 0.89 s, 215 MB spilled, 2,981 MB private.
   - The same group keys without the string payload finished at 512MB (524 MB).
   - `string_agg` failed cleanly at its 512MB cap (508 MB).
   - This matches the DuckDB tuning guide, which says `list()` and `string_agg()` "do not support offloading to disk". It also matches issue #14132 from the earlier lane, now seen on 1.5.5.
6. **[measured] Spill files went to the configured directory.** They landed on C: while the working directory was E:, so the temp-directory bug #14735 did not reproduce.
7. **[measured] DuckDB returns memory to Windows promptly.** After a query that peaked at 2,966 MB, private memory was 45 MB with the connection still open. Do not budget from its own `system_peak_buffer_memory` metric: it reported 5.6 GB for that run.
8. **[measured] Commit, not working set, is what fills the 124 GB limit.** At the 3GB cap DuckDB committed 2,981 MB but touched 1,964. Polars committed 3,484 MB and touched 2,155.

**Polars**
9. **[sourced+measured] Our Polars 1.39.3 has no memory cap and no spill.**
   - `collect()` defaults to the in-memory engine; streaming is opt-in.
   - Spill-to-disk arrived in 1.40.0, published 2026-04-18 (github.com/pola-rs/polars/releases/tag/py-1.40.0). Our installed binary contains the text "not implemented: spilling to disk".
   - The thread pool is fixed "before process start" (docs.pola.rs, `thread_pool_size`).
   - Issue #29430 (opened 2026-09-22) reports that on the development branch the spill accounting drifts until spilling stops.
10. **[measured] Streaming did not bound memory here.**
    - At 12×, the in-memory engine used 3,484 MB.
    - Streaming was killed by my 4 GB guard at 4 threads (4,230 MB) and again at 1 thread (3,897 MB).
    - At 4×, streaming used 1,598 MB against in-memory's 1,380.
    - Polars' verbose log confirmed real streaming group-by nodes, with no fallback to the in-memory engine.
11. **[measured] Polars keeps its peak.** After returning a one-row result, private memory was still 1,621 MB (streaming) and 1,312 MB (in-memory) 15 s later. Setting `MIMALLOC_PURGE_DELAY=0` did not help. The binary uses the mimalloc allocator. Related: Polars issue #23128.

**Windows**
12. **[sourced+measured] Neither engine notices when the whole machine runs low.** Microsoft's page-file sizing article (updated 2026-02-12) says commit "can't exceed the system commit limit", which is RAM plus all page files. A system-managed page file grows once commit passes 90% of the limit. Neither binary uses Windows' low-memory notification functions. [inferred] Heavy paging starts before the limit is reached, which fits the 1 fps cursor.
13. **[measured] A Job Object cap works as the backstop.**
    - Its `ProcessMemoryLimit` is "the limit for the virtual memory that can be committed by a process" (Microsoft Learn, `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`).
    - With a 1 GiB cap and DuckDB set to 3GB, DuckDB raised `Out of Memory Error: Allocation failure` and peaked at 1,011 MB. The process exited normally.
    - Under the same cap, Polars printed `memory allocation of 16777216 bytes failed` and the process was aborted (exit code 0xC0000409).
    - The machine survived both.
14. **[measured] Two traps for any memory watchdog.**
    - On Windows, `venv\Scripts\python.exe` is a small launcher, so psutil on `Popen.pid` watches a 4 MB stub. The watchdog has to follow the child process tree.
    - Output pipes must be drained while the child runs. A chatty Polars child filled its pipe and hung my runner until I killed it; no processes were left behind.

## Could NOT verify
- A real machine-wide commit exhaustion (not reproduced on purpose), or DuckDB running with its defaults (guardrail).
- Memory at 32 threads; the 1.2 GB figure is extrapolated from 1, 2 and 4 threads.
- Spilling in Polars 1.40 or later, which is not installed here.
- Whether DuckDB still deletes its own temp directory (issue #5878).
- Timings: they are warm-cache and the machine was shared, so treat them as indicative only.

## What it means for us
**House settings** for every DuckDB connection, with one instance per process:
```python
{"memory_limit": "1GiB",  # heavy jobs up to "3GiB", taking 2-3 slots
 "threads": 2,            # 4 max
 "temp_directory": r"<physical disk, outside repo>\duckdb-tmp\<agent>-<pid>",  # never X:\ (RAM disk)
 "max_temp_directory_size": "20GiB"}
```
For Polars, set `POLARS_MAX_THREADS=2` before import, and run it only in short-lived child processes.

**Budget for N agents running queries at once:**
- **Pool** = min(Available, RAM − Committed) − 8 GiB, read before starting. Tonight that is about 9-11 GiB. Treating every committed byte as if it were in RAM keeps the machine out of paging.
- **Per-process ceiling** = 1.25 × memory_limit + 0.25 GiB, set as the Job Object cap. The measured overhead above the cap was at most 120 MB; the rest is margin for operations DuckDB documents as bypassing its limit.
- **memory_limit** = min(3 GiB, (Pool/N − 0.25) / 1.25). With a 10 GiB pool: 2 agents get 3 GiB, 4 get 1.8, 6 get 1.1, and 8 get 0.8. The 1 GiB default fits 6 processes.
- **Polars** gets a Job Object cap drawn from the same pool. When it runs over, expect the process to be killed rather than an error.

**How not to crash the machine.** Never open DuckDB or Polars with defaults here. Three default DuckDB instances can each claim 50 GiB and 32 threads, which together exceed the whole 124 GiB commit limit. Always set `memory_limit` in GiB, `threads`, a private `temp_directory` and `max_temp_directory_size`, and open one instance per process. Before any heavy query:
- take a slot from a machine-wide counter (a Redis lock sized by the formula above);
- confirm that available memory exceeds 8 GiB plus this job's ceiling;
- run the query in a short-lived child process inside a Job Object capped at 1.25 × memory_limit + 0.25 GiB.

A runaway query then dies alone: the agent gets a DuckDB error or a Polars exit code, and the desktop stays alive. Keep Polars out of long-lived agents, because it holds on to its peak memory. Any watchdog must follow the process tree, not the launcher PID.
