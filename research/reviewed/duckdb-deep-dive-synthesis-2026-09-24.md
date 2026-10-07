# DuckDB deep dive -- synthesis

*2026-09-24, written by claude (Vandor) for Daniil's Bifrost ask of 19:42: "A super cool manager at Spectrum who is
working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can
leverage it or build an equivalent for ourselves?" The first run (17 agents) was cut off by the 20:24 power cut. Its
four finished reports were salvaged, and the dive was re-run as ten memory-capped lanes. The judgment below is
mine. Every number traces to a lane report listed under Sources.*

## The answer

1. **Use DuckDB as a read-only lens over our files.** Open it in memory for each query and close it after. Do
   not use it as a database file, and do not make it the substrate.
2. **Fix our ledgers first.** Tonight's lanes found that our own data is a bigger risk than any engine choice.
   One ledger writer loses about 2.3% of its rows. There is also text corruption, fields with mixed types,
   double-encoded JSON, and a version field that does not identify a version.
3. **Do not build a query engine.** Build three thin layers that any engine can use: a ledger contract, a
   Parquet archive where each file is written once, and one query door whose answers a second engine
   cross-checks.
4. **Keep recall on Redis.** It does not need an index yet. If it ever does, use SQLite FTS5 with sqlite-vec,
   not DuckDB's fts and vss extensions.
5. **"The sauce" is most likely agents querying real files with SQL instead of guessing.** DuckDB shipped
   Claude Code skills for exactly this on 16 September. We can adopt the pattern now.

## What our own data revealed (only we could measure this)

| Defect | Evidence | Lanes |
|---|---|---|
| FileLedger drops rows | 410 of 18,170 recall outcomes and 36 of 1,430 firehose events (09-10 to 09-24) never reached the file. The losses cluster within 0.5 s of another write. Every emit reads, modifies and rewrites the whole file (`core/foundation/ledger.py:216-236`), guarded only by an in-process `threading.RLock` (`:190`), with nothing that locks between processes. | fit |
| Writes split by worktree | Another 88 outcomes and 58 events landed in a worktree's own ledger, because `data_root()` follows the checkout and those services set no `AI_SETUP`. | fit |
| Text corruption | 62 values contain lone surrogates, left by a writer that decodes UTF-8 as cp1252 with `surrogateescape`. Python accepts them; DuckDB, Polars and pyarrow all reject them. | schema, skeptic |
| Mixed types | `at` is a number in some files and an ISO string in others. The obvious date filter undercounts by 68%. | schema |
| Double encoding | `content` is JSON stored inside a string. A search over the stored text misses 34,947 matching rows. | schema |
| A version that isn't one | `v` reads "2" across four different shapes. bus-export has five `fields` shapes, not three. | schema, skeptic |
| Duplicates | 16% of message rows are one message exported once per lane, so a naive `GROUP BY frm` over-counts. | fit |
| Windows called durable | `recall_outcome.jsonl` is a 20,000-row window, about 17 days, not the "two months" its comment claims. It is rewritten in place. | fit, schema |

## What DuckDB does with that data

- **Correct only with the right settings.** `read_json(glob, format='newline_delimited', union_by_name=true,
  sample_size=-1)` matched Python's `json` exactly over all 388 bus-export files: 223,910 rows, identical
  per-file counts, identical md5 over every payload. [schema]
- **Silently wrong with the defaults.** DuckDB samples only 20,480 rows and 32 files, so late or rare keys
  vanish. On the ledgers that was 16 of 50 event keys, or 412,575 values. [schema, capabilities, skeptic]
- **`ignore_errors` does not skip bad lines.** It returns them as all-NULL rows, which `count(*)` cannot see,
  and 1.5.5 has no rejects table for JSON. Truncated lines, zero-filled tails, invalid UTF-8 and a
  byte-order mark all become silent NULL rows. [schema, skeptic]
- **Errors depend on the query.** `SELECT *` fails on an unknown key, while `SELECT fields` drops it without a
  word. [schema]
- **It is not SQLite.** LIKE is case-sensitive in DuckDB and case-insensitive in SQLite, which fully explains
  the salvaged 74,736 vs 2,052 mismatch (6,228 vs 171 over one 88,149-row file). Integer division, `1/0`, NULL
  ordering and integer overflow also differ. [schema, skeptic]
- **It is fast.** Once loaded, group-bys over 1.06M rows take 6-10 ms. Querying raw JSONL directly takes
  about 240 ms. Parquet with zstd is about 4.5 times smaller. [local benchmarks, capabilities]

## Concurrency on this machine

- **A `.duckdb` file on Windows allows one writer or many readers, never both.** A writer shuts out every
  other process, even a plain file copy. Taking turns starved the writer: with 8 busy readers it managed 1
  append in 8 seconds. [concurrency]
- **The lock guards the open file, not its name.** Another process deleted a live database while it was
  being written, and all 12,000 rows were silently lost. Cleanup scripts must never touch `*.duckdb` or
  `*.wal`. [concurrency]
- **Reading our JSONL directly while seats append is safe.** 10,049 queries ran with no errors and no torn
  lines. [concurrency]
- **Parquet folders are safe only under discipline.** Write each file under a temporary name, then rename it
  into place. Merging files without a manifest double-counted 59 of 297 answers without any error.
  [concurrency]
- **There is an open Windows crash.** duckdb-python #613 reports access violations with concurrent read-only
  processes, and nobody has fixed it. [operational-limits, skeptic]

## Memory (tonight's lesson)

- **The defaults are the danger.** On this machine every DuckDB instance defaults to a 50 GiB memory cap and 32
  threads. The cap is 80% of *installed* RAM, and it ignores what other processes have already committed.
  Three default instances could claim 150 GiB against a 124 GiB commit limit. The cap applies per instance,
  not per process. Polars 1.39.3 has no memory cap and cannot spill to disk. Its streaming engine used *more*
  memory than its in-memory engine on a high-cardinality group-by, and it keeps its peak memory after the
  query returns. [memory-ops]
- **Explicit caps hold.** In 23 capped runs, peak private bytes stayed within `memory_limit` plus 120 MB, and
  every failure came back as a catchable error. A group-by whose groups each carry a large string cannot
  spill, so it fails at 512 MiB to 1 GiB and needs 2-3 GiB. DuckDB returns memory to Windows promptly after a
  query. [memory-ops]
- **A Windows Job Object is a real backstop.** It caps a single process's commit. Under a 1 GiB Job cap,
  DuckDB raised an out-of-memory error, Polars was aborted, and the machine was fine both times. [memory-ops]
- **House settings.**
  - Every DuckDB connection: `memory_limit='1GiB'` (heavy jobs up to `'3GiB'`), `threads=2` (at most 4), a
    private `temp_directory` on a physical disk outside the repo (never the X: RAM disk), and
    `max_temp_directory_size='20GiB'`, with one instance per process.
  - Polars: `POLARS_MAX_THREADS=2` before import, and only in short-lived child processes.
  - Budget for N concurrent queries:
    - pool = min(Available, RAM - Committed) - 8 GiB;
    - memory_limit = min(3 GiB, (pool/N - 0.25) / 1.25);
    - Job cap = 1.25 × memory_limit + 0.25 GiB. [memory-ops]
- **Input for Daniel's fleet-level design (item 3, which he is still thinking over).** The measured ingredients
  are these:
  - a machine-wide count of memory slots;
  - a Job Object cap on each heavy child process, so a runaway dies alone;
  - the commit signal the upgraded mem_watch now records every five minutes.

  This is not a proposal. The design is his.

## The plan, as slices

- **L0, the ledger write path (no engine involved).** FileLedger appends one line under a file lock, reading
  only the tail for the next id and trimming under the lock once past twice its cap. Worktree services get
  `AI_SETUP` so every row lands in one place. Acceptance: a two-process soak loses 0 rows, and the fit lane's
  10 September to 24 September gap does not recur.
- **L0b, the writers.** Reject invalid UTF-8 at write time. One type per field, with ISO-8601 UTC for every
  `at`. Stop double-encoding `content`. A real schema id per stream (for example `bus.msg/3`), checked at
  write time. A `uid` shared by the file row and the Redis row, so they dedupe exactly.
- **L1, the first read.** `lake ask prevention --days N --engine both`.
  - DuckDB opens in memory for each call, with a pinned version, capped memory and threads,
    `union_by_name=true`, `sample_size=-1` and no `ignore_errors`.
  - A stdlib and pyarrow twin must return the same answer.
  - A coverage frame travels with every answer: sources, rows per source, time span,
    `count(*) - count(id) = 0`, and a census of the key sets seen.
  - Acceptance tests are pre-registered in the fit lane.
- **L2, the archive.** Compaction to Parquet with pyarrow: files written once, under a temporary name then
  renamed, with a manifest swap instead of merge-and-delete. Add `lake sql`, CLI-only.
- **L3, the join.** Join recall outcomes to Eye transcripts, which gives the "complied" verdict that
  `core/recall/prevention.py` says it needs.
- **Optional, later.**
  - A Parquet snapshot the Bifrost console queries in the browser with DuckDB-Wasm.
  - Schema-grounded query tools for agents: list, describe and sample, plus one retry driven by DuckDB's
    candidate-binding errors. This is the pattern from DuckDB's Claude Code skills.

## What not to do

- Share a `.duckdb` file between seats.
- Keep anything we cannot lose in DuckDB's vss/HNSW persistence. DuckDB's own docs call it experimental and
  unsafe across a crash.
- Use `ignore_errors` to produce answers.
- Store data in DuckDB's file format before 2.0 settles. 2.0.0 is due on 21 October with a storage-format bump,
  and support for 1.5 ends on 1 November. L1 never writes a `.duckdb` file, so this does not block it.
- Build our own engine. The postmortems lane found teams that built engines and later ripped them out.

## Where the lanes disagreed, and how I settled it

- **Whether `union_by_name` changes anything.** Capabilities saw no difference. Schema showed that default
  sampling drops rare keys across 388 files, measured against ground truth. Schema's settings win.
- **When to adopt.** Skeptic says don't adopt now; fit says build the lake with DuckDB behind a door. Both put
  the contract first and give DuckDB the same read-only, capped, twin-checked role. They differ only on
  timing, and L0 comes first either way.
- **SQLite first?** Alternatives ranks SQLite first because it can take concurrent writes. That is right for
  anything written concurrently. The lake's reads never need a shared writable store.

## Evidence that would change this

- A 72-hour soak with at least 4 seats querying at once and no access violations would justify wider use.
  #613 reproducing here would push the reads to pyarrow and the stdlib only. [skeptic]
- The house's ten most common ledger questions, each answered in one statement by DuckDB where the
  alternatives need much more code. [skeptic]

## Fence (DeepSeek, three passes, verbatim)

The helper's per-call evidence budget clipped the first pass, so I split the check into three passes with narrower
file sets. Findings are reproduced verbatim; my disposition follows.

**Pass 1.** Synthesis, schema and fit (clipped); skeptic, concurrency and memory-ops skipped by budget. -- 12671+13722 tok | $0.037020 | 167.72s | deepseek-v4-pro

> 1. BLOCKER — L28: “every emit does an unlocked read-modify-rewrite” — fit lane says FileLedger is guarded by a `threading.RLock` (`core/foundation/ledger.py:190`); only cross-process locking is absent, so “unlocked” overstates.
> 2. BLOCKER — L42: “DuckDB samples only 20,480 rows and 32 files” — the attached schema lane gives the 32-file default and the 16/50 key loss (`duckdb-lane-schema:75`), but not the 20,480-row figure.
> 3. BLOCKER — L49: “Integer division, `1/0`, NULL ordering and integer overflow also differ” — not supported by the attached schema lane; that lane only measures LIKE case sensitivity (`duckdb-lane-schema:124-130`).
> 4. OK — L28 row-loss numbers 410/18,170 and 36/1,430 match fit lane measurements (`duckdb-lane-fit:49-50`).
> 5. OK — L29 “88 outcomes and 58 events” match fit lane (`duckdb-lane-fit:49-50`).
> 6. OK — L30 “62 values contain lone surrogates … DuckDB, Polars and pyarrow all reject them” matches schema lane (`duckdb-lane-schema:57-59`).
> 7. OK — L31 the obvious date filter undercounts by 68% matches schema lane (`duckdb-lane-schema:82`).
> 8. OK — L35 “20,000-row window … about 17 days … rewritten” matches fit and schema (`duckdb-lane-fit:57`, `duckdb-lane-schema:66`).
> 9. OK — L39 and L44 DuckDB correctness setting and `ignore_errors` all-NULL behavior match schema lane (`duckdb-lane-schema:69-72`, `duckdb-lane-schema:101-108`).
> 10. OK — No recommendation in the synthesis contradicts the attached fit/schema measurements; later synthesis claims (L52 benchmarks, L57-68 concurrency, L73-93 memory, L133 storage-format dates) cite lanes not attached, so I cannot check those here.

**Pass 2.** Synthesis, skeptic, and memory-ops (clipped); concurrency skipped by budget. -- 12784+6359 tok | $0.020957 | 81.89s | deepseek-v4-pro

> 1. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:30` “62 values contain lone surrogates…” — qualitative corruption/misencoding supported at `duckdb-lane-skeptic-2026-09-24.md:48-51`, but skeptic measured 7 bad rows in one frozen file; the 62 figure is not in the attached lane.
> 2. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:33` “…bus-export has five `fields` shapes, not three.” — supported at `duckdb-lane-skeptic-2026-09-24.md:52`.
> 3. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:42-43` “DuckDB samples only 20,480 rows…” — 20,480 supported at `duckdb-lane-skeptic-2026-09-24.md:46`; “32 files” and “16 of 50 event keys / 412,575 values” are not in attached skeptic.
> 4. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:44-46` “`ignore_errors` does not skip bad lines… all-NULL rows… no rejects table” — supported by `duckdb-lane-skeptic-2026-09-24.md:50-51`.
> 5. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:49-51` LIKE case sensitivity and SQLite vs DuckDB semantics — supported exactly at `duckdb-lane-skeptic-2026-09-24.md:78-83`, including 6,228 vs 171 and 74,736 vs 2,052.
> 6. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:73-78` 50 GiB / 32 threads defaults, per-instance cap, Polars no cap/spill, streaming memory behavior — supported at `duckdb-lane-memory-ops-2026-09-24.md:49-54,85-95`.
> 7. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:79-83` capped runs within limit +120 MB, large-string group-by spill failure, prompt memory return — supported at `duckdb-lane-memory-ops-2026-09-24.md:43,73-81`.
> 8. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:84-89` Job Object backstop with DuckDB error and Polars abort — supported at `duckdb-lane-memory-ops-2026-09-24.md:99-103`.
> 9. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:90-93` house settings and budget formula — match `duckdb-lane-memory-ops-2026-09-24.md:116-130` exactly.
> 10. OK — `duckdb-deep-dive-synthesis-2026-09-24.md:149-152` evidence that would change the verdict — supported at `duckdb-lane-skeptic-2026-09-24.md:119-125`.
> No blockers found in the attached skeptic and memory-ops portions. Synthesis lines 55-69 cite only the concurrency lane, which is not attached, so I could not verify those.

**Pass 3.** Synthesis and concurrency. -- 8626+8251 tok | $0.022814 | 100.27s | deepseek-v4-pro

> 1. OK — “A `.duckdb` file on Windows allows one writer or many readers, never both. A writer shuts out every other process, even a plain file copy. Taking turns starved the writer: with 8 busy readers it managed 1 append in 8 seconds.” Supported by `duckdb-lane-concurrency-2026-09-24.md:42-45` and finding 9 at `:101-107` (8,024 ms ≈ 8 s).
> 2. OK — “The lock guards the open file, not its name. Another process deleted a live database while it was being written, and all 12,000 rows were silently lost. Cleanup scripts must never touch `*.duckdb` or `*.wal`.” Supported by finding 6 at `:87-90` and the final recommendation at `:161`.
> 3. OK — “Reading our JSONL directly while seats append is safe. 10,049 queries ran with no errors and no torn lines.” Supported by finding 13 at `:127-130`; 10,049 queries is exact.
> 4. OK — “Parquet folders are safe only under discipline. Write each file under a temporary name, then rename it into place. Merging files without a manifest double-counted 59 of 297 answers without any error.” Supported by findings 10-11 at `:113-121`; “without a manifest” is inferred from the lane’s manifest recommendation at `:167-168`, but it matches the tested merge-and-delete setup.
> 5. OK but not fenced here — “There is an open Windows crash. duckdb-python #613 reports access violations with concurrent read-only processes, and nobody has fixed it.” This line cites operational-limits/skeptic, not `[concurrency]`; `duckdb-lane-concurrency-2026-09-24.md` never mentions #613, so it cannot be checked against the attached lane.
> 6. Plainly: nothing is blocking among the synthesis lines that cite `[concurrency]`.

**Disposition (claude).**
- Pass 1 #1, ACCEPTED: "unlocked" overstated it. FileLedger holds an in-process `threading.RLock`
  (`ledger.py:190`) and has no lock between processes. The line was reworded before adoption.
- Pass 1 #2 and #3, DECLINED: the budget skipped the lanes that support both claims. Pass 2 confirmed them:
  - the 20,480-row default is at skeptic line 46, and the capabilities lane measured it too;
  - the division, `1/0`, NULL-order and overflow differences are at skeptic lines 78-83.
- Pass 2 #1, a note that needs no change: the 62 lone surrogates are the schema lane's count (16 in session_logs
  plus 46 in bus-export). The skeptic lane saw 7 in one frozen file. The line cites both lanes.
- No blockers remain.

## Sources (all in research/reviewed/)

- **First run, salvaged:**
  - `duckdb-operational-limits-2026-09-24.md`
  - `duckdb-licenses-2026-09-24.md`
  - `duckdb-json-ingest-evidence-2026-09-24.md`
  - `duckdb-build-vs-buy-postmortems-2026-09-24.md`
  - `duckdb-local-benchmarks-and-census-2026-09-24.md`
  - `duckdb-fanout-index-2026-09-24.md`
- **Re-run lanes:** `duckdb-lane-{capabilities,alternatives,benchmarks,concurrency,schema,retrieval,fit,memory-ops,skeptic,ecosystem}-2026-09-24.md`
