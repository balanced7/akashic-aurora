# DuckDB deep dive, re-run -- lane: concurrency

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent a84505f74c1dfe640 (claude-opus-5-5) ran 21:01-21:23 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\concurrency (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index (all 17 original briefs). Read the ones relevant to your lane first. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1). Install nothing anywhere else.
- Every DuckDB connection: SET memory_limit='3GB'; SET threads=4; and a temp_directory inside your lane dir.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\concurrency\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents. Any helper process you start must end before you finish; kill it if it hangs.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: concurrency. Question: several agent seats on one machine will want to read the same data while something appends. What exactly does DuckDB allow?

Research:
- the documented model: one read-write process OR many read-only processes, plus in-process multi-threading;
- how file locking behaves on Windows;
- what a second process sees while a writer holds the file;
- ATTACH ... (READ_ONLY);
- the status of any multi-writer or server mode, with dates: DuckLake, the "quack" work, any httpserver extension, MotherDuck.

Then VERIFY LOCALLY on this Windows machine with two short Python processes (venv interpreter). A writer holds a .duckdb file open, and a reader tries read_only and read_write connects and ATTACHes. Record the exact error messages and timings. Also test the lock-free alternative: readers querying a directory of Parquet files while a "compactor" process writes a new Parquet file into it (write to a temp name, then rename). Do readers ever see a torn file? Keep the data tiny (under 50 MB).

Finish with the 2-3 access patterns that fit N seats, with their trade-offs.

## The report (verbatim)

Pointing DuckDB straight at our JSONL ledgers came through my tests clean. Having several seats share one `.duckdb` file failed in both directions. Everything below is from duckdb 1.5.5 on this machine, with the guardrails applied: 3 GB memory, 4 threads, extension downloads off. The scripts and raw results are in `C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\concurrency\` (`results\*.json`). Other lanes were running at the same time, so treat timings as indicative. The harness refused `REPORT.md` because subagents can't write report files, so that `results` folder is the crash-safe record instead.

## Headline
- **One file, one mode at a time.** A DuckDB file can be open by one read-write process (which may run many threads) or by any number of read-only processes, never both.
- **Windows enforces it hard.** While a writer has the file open, every other process fails in 75–128 ms. That includes read-only connects, `ATTACH … (READ_ONLY)`, and even a plain file read or copy.
- **Taking turns fails too.** With 8 busy readers, a writer got 1 append done in 8 seconds.
- **For several seats**, three setups work: read the ledger files directly, have one process own the database, or have that owner publish read-only snapshots. Quack (DuckDB's server mode) is beta and I couldn't test it.

## Findings

**The lock**

1. **[sourced]** The current concurrency docs (https://duckdb.org/docs/current/connect/concurrency, fetched 2026-09-24) now say multi-process writes are "supported through the Quack remote protocol" (beta, "mature by DuckDB v2.0 in fall 2026"). For a stable setup they recommend DuckLake with a PostgreSQL catalog.
   - **This corrects operational-limits.** Its quote "not a primary design goal" comes from the 1.4 LTS page (`/docs/lts/…`), not the current one.

2. **[sourced]** DuckDB's source (`raw.githubusercontent.com/duckdb/duckdb/v1.5.5/src/common/local_file_system.cpp`) shows how Windows locking works:
   - A writer opens the file with no sharing at all. A reader allows other readers only.
   - Every open also allows other processes to delete or rename the file.
   - The "who holds it" part of the error comes from the Windows Restart Manager.
   - On Linux/macOS it is an advisory lock instead.
   - This answers operational-limits open question #5: on Windows the lock is enforced for opening the file, but not for deleting or renaming it.

3. **[measured]** `lock_matrix.py`: one process holds the file, and a fresh process tries each kind of access.

| What holds the file | Read-only connect or ATTACH | Read-write connect or ATTACH | Plain read or copy |
|---|---|---|---|
| A writer that is appending | FAIL | FAIL | FAIL (`PermissionError [Errno 13]`) |
| 1–2 read-only processes | OK, about 8 ms | FAIL | OK |

   - The Windows error, verbatim: `IO Error: Cannot open file "…\lock_test.duckdb": The process cannot access the file because it is being used by another process.` then `File is already open in C:\…\python.exe (PID 38268)`. It lists every holder's PID.
   - Three read-only processes ran at once with no problem. That closes operational-limits open question #1.
   - It confirms LibreDB's finding and issue #17158 on Windows: while a writer holds the file, read-only processes are refused.

4. **[measured]** A failed open is slow (`failcost.py`, two runs):

| Read-only processes holding the file | Failed read-write open |
|---|---|
| 1 | 58–85 ms |
| 4 | 90–199 ms |
| 8 | 123–312 ms |

   A successful open-and-close takes 8–13 ms, so retry loops can't poll quickly.

5. **[measured]** Killing a writer leaves no stuck lock (`lock_matrix.py`, scenario S5).
   - I killed a writer outright while 5,000 of its rows were only in the 80 KB write-ahead log (WAL).
   - A read-only open succeeded 10 ms later, on the first try, and saw all 15,000 rows.
   - The `.wal` file stayed on disk until the next read-write open cleared it.

6. **[measured]** The lock protects the open file, not its name (`lock_extra.py`).
   - Another process **deleted** the live database while the writer was appending. The writer showed no error and exited normally, and nothing was left on disk: all 12,000 rows were silently lost.
   - A **rename** also succeeded. A second writer then created a new, empty database at the original path while the first kept writing to the renamed file.

7. **[measured]** Within a single process (`inproc.py`):
   - Opening read-write then read-only on the same file fails: `Connection Error: Can't open a connection to same database file with a different configuration than existing connections`.
   - Attaching a file that is already open fails: `Binder Error: Unique file handle conflict…`. That is the pattern behind corruption bug #14421, now refused.
   - Two read-only ATTACHes of the same file work.
   - Two transactions updating the same row fail with `TransactionContext Error: Conflict on update!`, not the wording in the docs.

8. **[measured]** Threads inside one process, 5-second runs:
   - One appending thread plus 4 reader threads: 736 appends/s (100 rows each) and 3,494 reads/s. Reads took 1.19 ms at the median and 1.64 ms at p95. No half-written batches, no count going backwards, no errors.
   - Two appending threads: 968 appends/s with no conflicts.

9. **[measured]** Taking turns on one file (open, work, close, retry with a random short wait; `timeshare.py`, 8-second runs):

| Setup | Writer appends | Writer wait |
|---|---|---|
| 1 writer, 3 busy readers | 17 | median 180 ms, max 2.7 s |
| 1 writer, 8 busy readers | 1 | 8,024 ms |
| 1 writer, 8 readers pausing 250 ms | 98 | p95 63 ms |

   In the last case readers waited up to 1.08 s. Readers can share with each other, so the file is never free for the writer.

**Reading files directly (no database file)**

10. **[measured]** A folder of Parquet files, with 3 reader processes querying it in a loop (`pq_test.py`).
    - The writer wrote each new file under a temporary name, then renamed it into the folder. Over 250 new files and 1,486 queries there were no errors and no half-written reads.
    - As a comparison, writing straight to the final name with pyarrow broke 439 of 1,761 queries (`No magic bytes found at end of file`, `…too small to be a Parquet file`). Every one was an error; none returned a wrong answer.

11. **[measured]** Merging files is the real danger.
    - The merge step combined 20 files into one, renamed it in, then deleted the 20 originals.
    - With a 30 ms pause before the deletes, **59 of 297 answers silently counted rows twice**.
    - Another 15 queries failed with `The system cannot find the file specified.`
    - A folder of files is not a consistent snapshot.

12. **[measured]** What another process can do while a reader is mid-scan (6.4-second scan; `pq_extra.py`, `snapshot_cost.py`):
    - Renaming or deleting the file worked, and the reader still returned the correct 800,000 rows.
    - Overwriting the file's name with `os.replace` failed with `PermissionError [WinError 5] Access is denied`. The same happened for an open `.duckdb` snapshot.

13. **[measured]** Our actual ledgers (`jsonl_test.py`, `jsonl_stale.py`).
    - One process appended 2,324 lines using the repo's own `with open(p, "a")` pattern; 121 lines were over 8 KiB.
    - Meanwhile 3 DuckDB processes queried the files with `read_json`: 10,049 queries, no errors, no half-written lines, and no appends were blocked.
    - Reusing one connection, append-then-count gave the up-to-date answer 300 times out of 300.

14. **[measured]** Cost of publishing a snapshot of 150,000 ledger-shaped rows:
    - Copying into a new `.duckdb` file: 92–94 ms (5.5 MB).
    - Exporting to Parquet: 28–29 ms.
    - A reader opening the snapshot read-only: 8.2 ms.

**Server and multi-writer options**

15. **[sourced]** Quack:
    - Announced 2026-05-12 (https://duckdb.org/2026/05/12/quack-remote-protocol): "multiple concurrent writers", about 5,500 small writes per second on 8 threads, no SSL by default.
    - Shipped as a beta extension in v1.5.3 (2026-05-20).
    - Its FAQ (https://duckdb.org/quack/faq) says stable "as part of DuckDB v2.0 in September 2026". The concurrency page says "fall 2026". DuckDB's own dates don't agree.
    - By default it only accepts local connections and needs a token.
    - Issue #25069 (2026-08-28) shows someone running a Quack server on Windows 11 with a 2.0 alpha build before a login bug broke it. That weakens operational-limits' claim that the alpha has no Windows extensions.

16. **[sourced]** DuckLake v1.0 (https://ducklake.select/2026/04/13/ducklake-10/, 2026-04-13) is described as "production-ready". Its catalog guide:
    - DuckDB as the catalog: "single client".
    - SQLite as the catalog: "multiple local clients". It opens and closes the catalog for each query and retries when locked.
    - PostgreSQL as the catalog: multi-user.
    - Writes of 10 rows or fewer are stored in the catalog instead of as new files. In effect, it is finding 11 done properly.

17. **[sourced]** The community `httpserver` extension (Query.Farm) is labelled "experimental and potentially unstable". MotherDuck Read Scaling (announced 2024-12-04) is cloud-only; its read copies "can lag a bit behind".

## What I could not verify
- **Quack and DuckLake locally.** Neither is installed, and downloading them needs your explicit OK, so I didn't.
- **Linux and macOS.** Behaviour there is inferred from the source only.
- **Crashes mid-append.** An append that dies halfway could still leave a partial last line in a JSONL file.
- **Other untested ground:** runs lasting hours, synced or network folders, and MotherDuck's replica limits (I only saw those in search snippets).

## What it means for us
Our append-only JSONL is already the easiest input DuckDB can have when many processes read at once, and every seat could query it today. A shared `.duckdb` file only works if exactly one process owns it. Cleanup scripts must never touch `*.duckdb` or `*.wal` files (finding 6).

**Setups that work for several seats:**
- **1. Read the files directly (default).** Seats keep appending JSONL, and any seat runs DuckDB or Polars on the files where they are.
  - For: no lock, no server (finding 13).
  - Against: every query re-reads the JSON, and there are no indexes.
  - Older history can go into Parquet files that are written once, under a temporary name then renamed (finding 10), and never rewritten.
  - Merge files only behind a manifest file that is itself swapped in by rename, or through DuckLake with SQLite once that has been tested.
- **2. One owner process, everyone else asks it.** One process holds the `.duckdb` read-write, and seats query it through inter-process calls; the existing door process already serializes writes.
  - For: about 3,500 reads/s alongside appends, all consistent (finding 8).
  - Against: it is a single point of failure, it carries the long-running WAL and memory risks from operational-limits, and it is effectively a server.
  - Quack is DuckDB's built-in version of this setup and isn't stable yet.
- **3. The owner publishes read-only snapshots.** It writes versioned files (`snap_000123.duckdb` or `.parquet`) plus a pointer to the newest, and readers open that one read-only, many processes at once.
  - Data is as stale as the publish interval.
  - Every publish is a full copy; I estimate about 0.6 s per `.duckdb` snapshot at our 969k rows, scaling linearly from finding 14.
  - Filenames must be versioned, because overwriting an open file fails on Windows (finding 12). Old snapshots can be deleted while readers still have them open.

**Avoid** having several seats share one `.duckdb` file (findings 3 and 9).
