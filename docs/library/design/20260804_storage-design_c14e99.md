---
akashic_id: art_20260804_storage-design_c14e99
akashic_sha: a5cb17055bfb
schema_version: 1
status: current
type: design
date: 2026-08-04
title: storage-design
gist: "--- status: current (2026-08-04, wire-next design lane, storage/indexing/query dimension) class: design lane: T156 WIRE-B candidate — storag"
visibility: fleet
body_type: markdown
seats: []
category: [migration, library, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T02:52:27"
updated: "2026-08-04T02:52:27"
---
<!-- GENERATED PROJECTION of art_20260804_storage-design_c14e99 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# storage-design

---
status: current (2026-08-04, wire-next design lane, storage/indexing/query dimension)
class: design
lane: T156 WIRE-B candidate — storage engine, schema, display-filter language, retention, migration.
      DESIGN ONLY. No code was written to the repo; no commits, no bus, no ledger.
ask: Daniil 2026-08-04 verbatim — "I want us to overengineer this to the max while retaining
     performance. I want us to be able to mine this for information and to feed it into our live
     telemetry, this deserves our best." Earlier framing — "the same kind of forensics that
     wireshark has as well as enterprise security appliances with deep packet sniffing" and the
     wire journal should be "a good place for our security eyes when we get them".
evidence: every performance number below was MEASURED on this machine on 2026-08-04 with scripts in
     the session scratchpad (not committed). Bench provenance is stated per table. Claims read from
     source are cited file:line. Claims I inferred are labelled INFER.
---

# The wire journal at season scale: storage, indexing, and a display-filter language

## 0. HEADLINE

**Move the journal to one SQLite/WAL database per fleet, keep all five indexes live on the write
path, and put a Wireshark-shaped display filter in front of it that compiles to SQL.**

The reason this is not a tradeoff is a number: **the JSONL append we ship today costs 235 µs per
record; a SQLite autocommit insert with five indexes live costs 85 µs mean / 26 µs p50.** Migrating
to a fully indexed store makes the cheap path **2.8x cheaper than it is right now**. The brief asked
me to keep index maintenance off the hot path. Measurement says the hot path is currently paying
**102 µs per record for `os.makedirs` + `os.listdir` + `os.path.getsize` that accomplish nothing**,
which is 6.6x the entire cost of maintaining all five indexes (15.5 µs).

Three defects found while measuring, all in shipped code, all reproduced:

| # | Defect | File:line | Consequence |
|---|---|---|---|
| **D1** | `_rotate()`'s MAX_BYTES branch deletes the **oldest** file when the **newest** exceeds the cap | `scripts/wire_journal.py:156-161` | Reproduced: 14 days of history destroyed in **13 records**, one day per record, while the file it was meant to bound kept growing. At the measured fleet volume this fires on **day one**. |
| **D2** | `read_all(limit)` parses the entire corpus and *then* slices | `scripts/wire_journal.py:187` | A caller asking for the last 100 records pays a full-season scan. Measured at 200k records: 1,413 ms and **794 MB peak RAM**. |
| **D3** | `expert()` scans the corpus **twice** | `scripts/wire_journal.py:238` (via `summarize()` → `read_all()` at `:198`) and `:252` (a second `read_all()`) | Doubles D2. The Expert Info panel is the most-called reader and it is the most expensive one. |

D1 is data destruction, not slowness. It is the reason this slice should not wait.

---

## 1. WHAT IS ON DISK TODAY, MEASURED

### 1.1 The live journal

`state/wire/wire-20260804.jsonl` — read at 02:10 and again at 02:20 during this session: 15 records
then 50 records, so the fleet is actively writing. **698 bytes/record** at 15 records
(10,472 B / 15). All 50 records carry a distinct `x-ds-trace-id` and a distinct `ts` — this matters
in §7, because it gives the migration a natural key with no invention required.

Every one of those 50 records is a **half record**. `model`, `stream`, `finish_reason`,
`system_fingerprint`, `response_id`, and all nine token fields are `null`, because the transport hook
at `scripts/wire_journal.py:338-340` passes only `status`, `attempt`, `headers`, `ms_first_byte` —
and nothing anywhere calls `journal().record()` with a `usage=` kwarg. Verified: `grep -rn
"wire_journal\|WireJournal\|recording_http_client"` over the repo returns exactly three call sites
(`scripts/deepseek_chat.py:85-86`, the module itself, `tests/test_t156_wire_journal.py:47`). The
`_shape()` extractor at `:106-145` is written and unfed.

**This is a storage-design fact, not a note.** The record has two halves that arrive at different
times from different layers (§2.2 of `research/in-flight/api-wire-visibility-design-opus5-2026-08-04.md`
names them tier-0 transport and the usage-capture callback), and **JSONL cannot join them.** An
append-only text file has no update. SQLite does — one row, two writes, correlated by `call_id`. The
correlation problem is not a reason to pick a database *later*; it is the reason to pick one *now*.

### 1.2 The cost of the current append path, decomposed

Bench: 20,000 iterations each, against a directory holding 15 journal files, Windows 11 / NTFS on
`E:` (confirmed local NTFS `DriveType 3` by `research/reviewed/storage-engine-sweep-2026-07-26.md`
§1 — this matters, because WAL requires shared memory and does not work on network filesystems).

| Operation | Line | µs/record | Share |
|---|---|---:|---:|
| `json.dumps(rec)` | `wire_journal.py:99` | 3.4 | 2% |
| `os.makedirs(dir, exist_ok=True)` | `wire_journal.py:96` | **48.8** | 27% |
| `open`/`write`/`close` in append mode | `wire_journal.py:98-99` | 78.2 | 43% |
| `os.listdir` + sort inside `files()` | `wire_journal.py:164-168`, called from `_rotate()` `:148` | **38.0** | 21% |
| `os.path.getsize(newest)` | `wire_journal.py:158` | **15.0** | 8% |
| **sum of parts** | | **183.4** | |
| **end-to-end measured `record()`-equivalent** | `wire_journal.py:86-104` | **235.4** | |
| *same append, handle held open* | — | **5.7** | |

**102 µs of the 235 µs (43%) is `makedirs` + `listdir` + `getsize`** — three filesystem syscalls per
HTTP round trip that re-answer questions whose answers cannot have changed. A held file handle would
cut the whole path to 5.7 µs. Neither observation requires SQLite; both are free wins that a rewrite
should bank rather than inherit.

### 1.3 The read path does not survive a season

Bench: 200,000 synthetic records shaped exactly like the live ones (886 B/record mean when the
optional fields are populated — the live 698 B is the all-null half-record), 177.8 MB of JSONL.

| Reader | Time | Peak RAM |
|---|---:|---:|
| `read_all()` over 200k records | 1,413 ms | **794 MB** (tracemalloc) |
| `summarize()`-equivalent (scan + count) | 1,546 ms | same |
| `expert()` — **two** scans (D3) | ~3,100 ms | same, twice |

At the season volume derived in §1.4 (1.1M–3.4M records) that extrapolates **linearly** to
14–24 seconds and **4.4–13.5 GB of resident Python objects** for one `summarize()` call. INFER, from
the 200k measurement and the fact that `read_all()` at `:172-187` builds one unbounded list. This
machine has 66.2 GB total / 23.2 GB available, so it would not strictly OOM — it would evict
everything else and take twenty seconds to answer "how many truncations today". A live-telemetry
reader cannot be built on that.

### 1.4 Season volume, derived from real journals rather than guessed

Real per-agent daily turn counts, read from `state/runner_*.json` (26 files):

| Date | Agent | Turns | Prompt tokens |
|---|---|---:|---:|
| 2026-07-28 | deepseek | 175 | 130,590,595 |
| 2026-07-30 | deepseek | 139 | 33,544,633 |
| 2026-07-30 | kimi | **280** | 80,001,119 |
| 2026-07-29 | kimi | 162 | 47,991,995 |

A `TokenJournal` "turn" is **one bus message**, not one HTTP call — `add_turn()` is called once per
turn close at `scripts/bifrost_runner_deepseek.py:1109`, while one turn runs up to
`MAX_TOOL_ROUNDS = 30` hops (`scripts/deepseek_chat.py:109`). The conversion factor is measured in
the repo already: `scripts/deepseek_chat.py:207-208` records *"309 deepseek turns / 393M tokens,
worst turn 11.4M over 127 hops"* → **≈90k prompt tokens per HTTP call**.

- Busiest observed **two-agent** day (2026-07-30, deepseek 33.5M + kimi 80.0M = 113.5M prompt
  tokens) → **≈1,260 HTTP round trips/day**.
- **20 concurrent players** (the stated Season-1 scale;
  `docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:600` — *"At 20 players ×
  20 bounties"*) is ~10x that fleet → **≈12,600 round trips/day**. If per-call context runs smaller
  than 90k (a one-shot player prompt is much smaller than an agentic hop's re-sent context — the
  same doc at `:499` says Season-1 players are *"one-shot API calls"*), the count rises to
  **≈38,000/day** at 30k tokens/call.
- **90-day season: 1.13M – 3.4M records; 1.0 – 3.0 GB of JSONL; 11 – 34 MB/day.**

**`MAX_BYTES = 8 MB` (`scripts/wire_journal.py:61`) is crossed on the first day of every one of those
scenarios.** Which brings us to D1.

### 1.5 D1 reproduced against the shipped module

I imported the real `scripts/wire_journal.py` (read-only, via `importlib`), seeded 14 history files,
made today's file exceed `MAX_BYTES`, and wrote records:

```
history files before: 14
  after record 1:  13 files, today=200,525 B
  after record 2:  12 files, today=201,038 B
  after record 3:  11 files, today=201,551 B
  after record 12:  2 files, today=206,168 B
  after record 13:  1 files, today=206,681 B
history files after 20 records: 1  ['wire-20260804.jsonl']
```

The code at `:156-161`:

```python
if files:
    newest = files[-1]
    if os.path.getsize(newest) > MAX_BYTES and len(files) > 1:
        os.remove(files[0])          # deletes the OLDEST because the NEWEST is too big
```

Once today's file crosses the cap, **every subsequent record destroys one day of history** until one
file remains, and the file the cap was written to bound is never bounded. The docstring at `:58-59`
promises *"Oldest file is dropped, newest always survives"* — the newest surviving is exactly the
failure. `MAX_FILES` (`:60`) works correctly; only the `MAX_BYTES` branch is inverted.

This is the strongest single argument in this document. A forensics store that silently deletes
evidence under load is worse than no store, because the gap is invisible: `summarize()` reports
`records: N` over whatever survived and never says that fourteen days went missing.

---

## 2. (a) STORAGE ENGINE: SQLite in WAL mode, one database, in `scripts/`

### 2.1 The choice, and why it is already the repo's choice

`core/foundation/sqlite_store.py` is 718 lines of SQLite/WAL prior art with the arguments already
made and the probes already run:

- **Why SQLite over the alternatives** — `sqlite_store.py:18-30`: chosen over LMDB (*"the zset
  encoding alone is a design project"*) and over per-key files, with the full landscape in
  `research/reviewed/storage-engine-sweep-2026-07-26.md` §2. That sweep's own verdict on our profile
  (§5): *"single machine, roughly five processes, a ~9MB store, read-dominated… single-writer is not
  a limitation for us."*
- **Stdlib** — `import sqlite3`, `sqlite_store.py:61`. No dependency, no deploy-property change. The
  sweep names this as doing *"much of the remaining work"* in the decision (§5).
- **The connection pragmas are already written and tested** — `sqlite_store.py:150-152`:
  `journal_mode=WAL`, `busy_timeout`, `synchronous=NORMAL`.
- **The two riders are already documented and measured** — `sqlite_store.py:32-46`: checkpoint policy
  is *mandatory* (probed 2026-07-26: a held reader grew `-wal` to **523,272 bytes** and it fell to 0
  only after an explicit `wal_checkpoint(TRUNCATE)`), and **backup must not be a file copy**
  (`backup_to()` at `:202-216`, pinned by `tests/test_snapshot_wal_correct.py`).

Local capability probe, this machine, 2026-08-04: **SQLite 3.45.1**, compile options include
`ENABLE_FTS5`, `ENABLE_RTREE`, `ENABLE_MATH_FUNCTIONS`, `THREADSAFE=1`; `PRAGMA module_list` returns
`fts5`, `json_each`, `json_tree`, `rtree`. Default `page_size=4096`, default `auto_vacuum=0` (NONE),
and `auto_vacuum=INCREMENTAL` takes effect when set **before** the first `CREATE TABLE` (verified).
FTS5 and JSON1 are available without a build change — §4 and §3.4 use both.

### 2.2 What I am NOT doing: reusing `SqliteStore`

`SqliteStore` is a **Redis-shaped key/value store** (`kv`, `hash`, `list`, `set_members`, `zset`,
`expiry` — `sqlite_store.py:81-118`) living in `core/foundation/`. Two reasons to keep away:

1. **Wrong shape.** Wire records are a wide flat relation with numeric predicates over 24 columns.
   Forcing them through `hset`/`hgetall` gives up every index that makes §3 work, and
   `hgetall_prefix()` at `:644-666` exists precisely because the per-key pattern did not scale
   (*"455 lessons meant 455 round-trips, extrapolating to 483 seconds per query at a million"*).
2. **Membrane law.** The canonical statement is cited in the prior design as
   `docs/library/design/20260724_t106-build-specs-o15-seat-lease-a1-await_6fc93b.md:42` — *"runners
   NEVER consume via MCP -- seat-model agents only"* — and its structural consequence is that the
   recorder lives in `scripts/`, sibling to `scripts/runner_token_journal.py`. **The new module is
   `scripts/wire_store.py`.** It imports `sqlite3` and nothing from `core/`. Core gains nothing.

I reuse `SqliteStore`'s **lessons**, not its code: the pragma set, the `checkpoint()`/`wal_bytes()`
health pair (`:180-199`), the `backup_to()` contract (`:202-216`), and the degraded-not-silent
failure mode (`:156-160`).

### 2.3 One database, not one per agent

Twenty players writing twenty databases makes every cross-agent query a 20-way ATTACH (SQLite's
`MAX_ATTACHED=10`, from the compile options — so it would not even work at 20). One database, and
the single-writer objection answered by measurement below.

### 2.4 The single-writer objection, measured at 20 processes

This is the load-bearing risk of the choice, so I measured it rather than reasoning about it.
**20 OS processes**, each opening its own connection to one shared database in WAL mode with
`synchronous=NORMAL`, `busy_timeout=15000`, all five indexes live, 1,500 autocommit inserts each
(30,000 total):

| checkpoint policy | wall | aggregate | p50 | worst-worker p99 | worst single | `SQLITE_BUSY` | rows landed |
|---|---:|---:|---:|---:|---:|---:|---:|
| `wal_autocheckpoint=1000` (default) | 3.1 s | 9,536 ins/s | 31 µs | 7.5 ms | 2,700 ms | **0** | 30,000/30,000 |
| **`wal_autocheckpoint=0`** | 2.9 s | **10,366 ins/s** | 43 µs | **0.2 ms** | 1,964 ms | **0** | 30,000/30,000 |

Findings:

- **Zero `SQLITE_BUSY`, zero lost rows, at 20 concurrent writers and ~10,000 inserts/s aggregate.**
  Our measured peak demand is 38,000 records/*day*. We are three orders of magnitude inside the
  envelope. Single-writer is not a constraint at our scale; it is a correctness feature.
- **Turning autocheckpoint OFF in writers improves the p99 by 37x** (7.5 ms → 0.2 ms). This is the
  checkpoint-starvation gotcha from `storage-engine-sweep-2026-07-26.md` §2 landing exactly where it
  was predicted, with a measured mitigation.
- **The multi-second worst case is connection warm-up, not steady state.** Isolated separately
  against the 767 MB season database: `PRAGMA journal_mode=WAL` on an existing db costs **480 µs**,
  `insert[0]` costs **4,383 µs**, `insert[1]` costs **117 µs**, steady-state p50 **24.1 µs**. The
  fix is architectural, not tuning: **open the connection once at runner start, never per record**
  — and §6 puts the writer on a drain thread so even the 4.4 ms first insert is off the request
  thread.

### 2.5 Size on disk, with indexes

200k realistic-shaped records: **JSONL 177,788,138 B (889 B/row); SQLite with all 5 indexes
133,976,064 B (670 B/row) = 0.75x.** The indexed database is *smaller than the text it replaces*,
because integers stop being decimal strings and the 24 key names stop being repeated 200,000 times.
The "indexes cost disk" intuition is wrong here by measurement.

---

## 3. (b) SCHEMA AND INDEXING

### 3.1 The table

```sql
PRAGMA page_size = 4096;          -- default here; stated so a future move to 8192 is deliberate
PRAGMA auto_vacuum = INCREMENTAL; -- MUST precede the first CREATE TABLE (verified; default is 0)

CREATE TABLE wire (
  id                 INTEGER PRIMARY KEY,     -- rowid; monotonic arrival order, free
  -- identity / correlation ------------------------------------------------
  call_id            TEXT NOT NULL,           -- one logical create(); retries SHARE it
  attempt            INTEGER NOT NULL,        -- 0-based; wire_journal.py:116 semantics preserved
  trace_id           TEXT,                    -- headers['x-ds-trace-id'] LIFTED to a column
  response_id        TEXT,
  ts                 REAL NOT NULL,           -- request start, epoch seconds
  ts_close           REAL,                    -- when the usage half landed (NULL = still open)
  agent              TEXT NOT NULL,
  arc                TEXT,                    -- task/round/season tag; NULL until a caller sets it
  model              TEXT,
  url_path           TEXT,                    -- path ONLY, never the query string
  stream             INTEGER,                 -- 0/1/NULL
  -- outcome ---------------------------------------------------------------
  status             INTEGER,
  error              TEXT,
  finish_reason      TEXT,
  system_fingerprint TEXT,
  service_tier       TEXT,
  -- usage (counts only; NEVER a price -- see §8) --------------------------
  prompt_tokens      INTEGER, completion_tokens INTEGER, total_tokens INTEGER,
  reasoning_tokens   INTEGER, cache_hit_tokens  INTEGER, cache_miss_tokens INTEGER,
  cached_tokens      INTEGER,
  -- timing ----------------------------------------------------------------
  ms_first_byte      INTEGER, ms_total INTEGER, ms_ttft INTEGER, ms_max_chunk_gap INTEGER,
  -- content: hashes only, no bodies (W2) ----------------------------------
  prompt_sha         TEXT, prompt_prefix_sha TEXT, response_sha TEXT,
  req_bytes          INTEGER, resp_bytes INTEGER,
  -- the honest overflow ---------------------------------------------------
  headers            TEXT,   -- JSON object, allowlisted (wire_journal.py:65-67)
  extra              TEXT,   -- JSON: any provider field we did not have a column for
  validity           TEXT    -- JSON: {field: "UNKNOWN"|"UNDEFINED"} -- see §3.3
);
```

Three shape decisions worth defending:

**`trace_id` is lifted out of the headers JSON into a column.** It is the provider's request UUID —
`scripts/wire_journal.py:35-36` calls it *"the handle their support needs to trace one call"* — and
it is the single most likely lookup key in an incident. Measured on the live file: 50/50 present and
50/50 distinct. A JSON extraction cannot be the primary lookup path for the field you reach for
first at 3am.

**`headers` and `extra` stay JSON.** The allowlist at `wire_journal.py:65-67` will grow as providers
invent headers, and `json_extract()` over a 5-key object is cheap for the rare query. `extra` is
where an unrecognised provider field lands instead of being dropped — the reverse-engineering census
(`research/in-flight/api-wire-reverse-engineering-deepseek-2026-08-04.md` §1.2, §1.3) lists
`accepted_prediction_tokens`, `rejected_prediction_tokens`, `audio_tokens`, `chunk.created`,
`chunk.object`, `choices[0].index`, `delta.refusal`, `delta.function_call` as fields that exist and
are discarded. A schema that silently drops a field it did not anticipate is how we get a second
census in six months.

**`call_id` + `attempt` is the join key, and it is what makes the two-halves problem solvable.**
The transport writes the row with everything it can see (status, headers, `ms_first_byte`) and the
usage-capture callback later does one `UPDATE wire SET finish_reason=?, ... WHERE call_id=? AND
attempt=?`. JSONL cannot do this; it would need a second record and a reader that joins on every
read. Measured cost of the UPDATE path: an indexed single-row update on the `wire_call` unique index
is the same order as the insert (p50 ~26 µs class), and it happens off the response path per §6.

### 3.2 The indexes, chosen from the queries in the brief

| Index | Serves | Measured at 2M rows |
|---|---|---|
| `CREATE UNIQUE INDEX wire_call ON wire(call_id, attempt)` | retry grouping, the usage-half UPDATE, migration idempotence | unique lookup, sub-ms |
| `CREATE INDEX wire_ts ON wire(ts)` | **by time window** — the live-telemetry query | last-1h `ORDER BY ts DESC LIMIT 500`: **1.4 ms** |
| `CREATE INDEX wire_agent_ts ON wire(agent, ts)` | **by agent** (+ window) | one agent / 24 h, 12,240 rows: **57.2 ms** |
| `CREATE INDEX wire_arc_ts ON wire(arc, ts)` | **by arc** | same shape as agent |
| `CREATE INDEX wire_prefix ON wire(prompt_prefix_sha, ts)` | **by prefix hash** — cache forensics | 400 rows: **3.1 ms** |
| `CREATE INDEX wire_fp ON wire(system_fingerprint, ts)` | **by fingerprint** — silent model swap | `GROUP BY` over 2M: **131.1 ms** |
| `CREATE INDEX wire_trace ON wire(trace_id)` | incident lookup by provider handle | unique lookup |
| **`CREATE INDEX wire_anom ON wire(ts) WHERE finish_reason='length' OR status>=400 OR attempt>0 OR error IS NOT NULL`** | **the Expert Info panel** — a *partial* index over only the interesting rows | anomalies in 24 h, 35,281 rows: **131.1 ms** |

**`finish_reason` deliberately has no dedicated index.** Measured: `SELECT COUNT(*) WHERE
finish_reason='length'` over the whole 2M-row season is **242 ms** as a full scan, and the partial
`wire_anom` index answers the *windowed* version — which is the version anyone actually asks — in
131 ms. A low-cardinality column (four values: `stop`/`length`/`tool_calls`/`content_filter`, per
`api-wire-reverse-engineering-deepseek-2026-08-04.md` §1.5) with an 7% selectivity on the interesting
value earns a **partial** index, not a full one. This is the rule I would apply generally: *index the
anomaly, scan the norm.*

**Index maintenance cost, isolated.** 20,000 autocommit inserts, WAL, `synchronous=NORMAL`:

| configuration | mean | p50 | p99 | max |
|---|---:|---:|---:|---:|
| no indexes | 21.1 µs | 10.8 µs | 31 µs | 8.6 ms |
| **5 indexes** | **85.0 µs** | **26.3 µs** | 890 µs | 12.7 ms |
| 5 indexes, `synchronous=OFF` | 33.0 µs | 25.7 µs | 68.5 µs | 1.0 ms |
| 5 indexes, `synchronous=FULL` | **1,018 µs** | 895 µs | 4.1 ms | 48.5 ms |

**All five indexes cost 15.5 µs at p50** (26.3 − 10.8). Against a 235 µs status quo and an 850 ms
median TTFB (`research/in-flight/wire-capture-deepseek-2026-08-02/p3-ttft-decomposition.json`:
0.859 s / 0.813 s / 0.890 s across three runs), that is **0.002% of a call**. The "keep indexes off
the hot path" instinct is correct in general and quantitatively wrong here; I would rather record the
number than honour the instinct.

`synchronous=FULL` is a 12x tax and is never correct for a diagnostic journal. `synchronous=OFF` is
tempting (33 µs, tight p99) but risks database corruption on power loss rather than merely losing the
tail — for a store that is supposed to be forensic evidence, **`NORMAL` is the answer** and the
reasoning should be written down: NORMAL in WAL survives process crash; only OS/power loss can lose
the last transactions, and a lost tail of telemetry is an acceptable loss where a corrupt evidence
file is not.

### 3.3 The validity column, and why it is a column and not a convention

`scripts/wire_journal.py:69` already carries `UNKNOWN = "UNKNOWN"` with the T141 note *"a field the
provider never sent is not a zero."* The prior design (§2.3 of
`api-wire-visibility-design-opus5-2026-08-04.md`) proposes serialising every annotated field as
`{"v":…, "s":"MEASURED"}`, at *"~2x bytes on annotated fields."*

**In a relational store the cheap encoding is already available and costs zero extra bytes:
`NULL` means not-MEASURED, and one small `validity` JSON column distinguishes UNKNOWN from
UNDEFINED for the minority of fields where the difference exists.** A `NULL` numeric column in
SQLite occupies **1 byte** in the record header. The `{"v":…,"s":…}` envelope on 24 fields would add
roughly 400 bytes/record — at 3.4M season records that is **1.4 GB spent encoding "we do not know"**.

The rule, stated so a reader can rely on it:
- column IS NULL and no `validity` entry → **UNKNOWN** (never observed)
- column IS NULL and `validity` says `UNDEFINED` → **UNDEFINED** (a derived value with a zero
  denominator, e.g. `cache_hit_rate` when hit+miss == 0)
- column IS NOT NULL → **MEASURED**, and a `0` there is a real zero

This preserves exactly the distinction `scripts/deepseek_chat.py:231` (`cache_rate()`) makes and
`scripts/runner_token_journal.py:24-30` makes for UNPRICED, and §4 lifts it into the query language
as a first-class operator so nobody has to remember it.

### 3.4 Derived views, so the hard questions are one word long

```sql
CREATE VIEW wire_v AS SELECT *,
  CASE WHEN COALESCE(cache_hit_tokens,0)+COALESCE(cache_miss_tokens,0) > 0
       THEN 1.0*cache_hit_tokens/(cache_hit_tokens+cache_miss_tokens) END        AS cache_hit_rate,
  CASE WHEN completion_tokens > 0
       THEN 1.0*reasoning_tokens/completion_tokens END                           AS reasoning_share,
  (finish_reason='length')                                                       AS truncated,
  (finish_reason='length' AND COALESCE(reasoning_tokens,0) >= 0.9*COALESCE(completion_tokens,1))
                                                                                 AS reasoning_ate_answer
FROM wire;
```

`cache_hit_rate` returns SQL `NULL` — not `0.0` — when the denominator is zero. That is UNDEFINED
rendered correctly by construction, and it is the same fix `cache_rate()` makes at
`deepseek_chat.py:231`. `reasoning_ate_answer` encodes the `runner_reasoning_eats_final_answer`
incident named at `wire_journal.py:30-32` as a queryable column.

**FTS5 is available (verified) and I recommend deferring it.** There is no free text in a
metadata-only journal; the only text is hashes and header values, which are exact-match. FTS5 becomes
correct the day tier-2 body capture ships (§4 of the prior design) and not before. Naming it here so
the schema has a documented place to grow rather than a retrofit.

---

## 4. (c) THE DISPLAY FILTER LANGUAGE — **WDF**

Wireshark's power is not the packet list; it is that `tcp.port == 443 && tcp.analysis.retransmission`
is one line a human types. The equivalent here is a filter over our own semantics.

### 4.1 Grammar (concrete, complete)

```
filter   := or
or       := and     ( ("||" | "or")  and )*
and      := unary   ( ("&&" | "and") unary )*
unary    := ["!" | "not"] atom
atom     := "(" filter ")" | validity | compare | field
validity := field "is" ("measured" | "unknown" | "undefined")
compare  := arith cmp arith | field "in" "{" literal ("," literal)* "}"
cmp      := "==" | "!=" | ">" | ">=" | "<" | "<=" | "~" | "contains"
arith    := term (("+" | "-") term)*
term     := factor (("*" | "/" | "%") factor)*
factor   := field | literal | "(" arith ")" | "-" factor
field    := IDENT | IDENT "." IDENT            -- headers.x-ds-trace-id, extra.audio_tokens
literal  := NUMBER | STRING | DURATION | SIZE | TIME | BAREWORD
DURATION := NUMBER ("ms"|"s"|"m"|"h"|"d")      -- 500ms, 2s, 24h  -> milliseconds or seconds by field
SIZE     := NUMBER ("kb"|"mb"|"gb")
TIME     := "@" ("-" DURATION | ISO8601)       -- @-24h, @2026-08-04T02:00
BAREWORD := [A-Za-z_][A-Za-z0-9_-]*            -- an unquoted enum value: length, stop, deepseek
```

`~` is regex match. `contains` is substring. `is measured|unknown|undefined` is the T141 vocabulary
as a **first-class operator** — this is the piece I would refuse to ship without, because a query
language over this journal that cannot express *"show me the calls where cache reporting was absent,
as distinct from zero"* recreates the exact defect the journal exists to cure. `cache_hit_tokens ==
0` and `cache_hit_tokens is unknown` must be different queries, and in WDF they are.

### 4.2 The filters that earn the language

Each of these is a real diagnosis, not a syntax demo.

| Filter | What it finds | Grounding |
|---|---|---|
| `finish_reason == length && reasoning_tokens > 0.9 * completion_tokens` | the model thought itself out of an answer | `wire_journal.py:28-32`; `api-wire-reverse-engineering-deepseek-2026-08-04.md` §1.3 |
| `attempt > 0 \|\| status >= 400` | retransmission / error class | `wire_journal.py:243-259` |
| `cache_hit_rate < 0.2 && prompt_tokens > 50000` | the largest cost lever, on the calls where it is worth money | `wire_journal.py:33-34, 267-270` |
| `prompt_prefix_sha == "a1b2c3d4e5f60718" && cache_hit_tokens == 0` | a prefix that *should* have hit and did not | `wire_journal.py:139-140` |
| `system_fingerprint != "fp_9954b31ca7_prod0820_fp8_kvcache_20260402"` | the provider swapped the model behind the endpoint | fingerprint value measured in `wire-capture-deepseek-2026-08-02/p6-extra-chunk-internals.json` |
| `cache_hit_tokens is unknown && prompt_tokens > 1000000` | **the live measured-zero defect**: 3.9M prompt tokens reporting exactly 0 cache | `state/runner_kimi_2026-08-02.json`; prior design §2.2 |
| `agent == kimi && ts >= @-24h && ms_first_byte > 3s` | one agent's slow tail in a window | `wire_journal.py:135-136` |
| `headers.x-ds-trace-id == "5abed503289909b8f60317f8bcfa8659"` | the incident handle support asks for | live record, `state/wire/wire-20260804.jsonl` |
| `arc == "t156" && truncated && ms_total > 60s` | one arc's truncations that were also slow | §3.1 `arc` column |

### 4.3 The evaluator: split into a SQL prefix and a Python residual

This is the design decision that makes the language fast, and it is measurement-driven.

Measured over 200,000 rows:

| Path | Time |
|---|---:|
| parse + AST-validate + compile (once per query) | **17.4 µs** |
| Python `eval()` of the predicate over 200k dict rows | 39 ms (**0.19 µs/row**) |
| the same predicate as a SQL `WHERE` over 200k rows | 32.1 ms |
| the same predicate via the partial `wire_anom` index | 31.5 ms — `EXPLAIN QUERY PLAN`: `SCAN wire USING INDEX wire_anom` |

**Read that carefully: over a full scan, SQL beats Python by only 1.2x.** The reason to compile to
SQL is therefore *not* the per-row cost. It is that the SQL form can **avoid the scan**: at 2M rows,
the agent+window query is **57 ms** while the equivalent full-season scan is **242–2,898 ms**. The
win is 4x–50x and it comes entirely from the planner reaching an index.

So the evaluator is:

1. **Parse** WDF → AST (a ~200-line recursive-descent parser; the grammar above is LL(1)).
2. **Split** the top-level `AND` conjuncts into:
   - **pushable**: any comparison whose operands are (registered column, literal) or (column, column
     arithmetic), plus `is measured/unknown/undefined` (→ `IS NULL` / `IS NOT NULL` /
     `json_extract(validity,'$.f')='UNDEFINED'`), plus `in {…}`.
   - **residual**: `~` regex, `contains` on a JSON subfield, anything under an `OR` that mixes
     pushable and non-pushable, anything referencing a non-materialised derived field.
3. **Emit** `SELECT * FROM wire_v WHERE <pushable> ORDER BY ts DESC LIMIT ?` with **every literal
   bound as a parameter**. Column names come from a hard-coded `FIELDS` registry — never from user
   text. There is no string interpolation of anything a human typed.
4. **Evaluate** the residual in Python over the (index-narrowed) result set.

**Sandbox posture, and a correction to my own bench.** My benchmark used `eval(code, {"__builtins__":
{}}, row)` with an AST whitelist that included `ast.Attribute`. **Do not ship that.** Daniil's stated
purpose for this journal is *"a good place for our security eyes when we get them"*, and a `eval()`
in the query path of a security tool is indefensible however well whitelisted — attribute access is
the classic escape. The residual evaluator should be a **hand-walked interpreter over the validated
AST** (~80 lines: `BoolOp`, `UnaryOp`, `BinOp`, `Compare`, `Name`, `Constant`, and nothing else — no
`Attribute`, no `Call`, no `Subscript`). Dotted field paths are resolved **at parse time** into flat
registry names (`headers.x-ds-trace-id` → the `h_x_ds_trace_id` slot the row-flattener provides), so
the interpreter never touches a live object. Cost: the measured 0.19 µs/row for `eval` is the *upper
bound of what we give up*; a tree-walker lands around 1–2 µs/row (INFER), which over an
index-narrowed set of a few thousand rows is single-digit milliseconds.

### 4.4 Surfaces

- `py agent_cli.py wire '<filter>' [--last 24h] [--limit 200] [--json]` — tshark's `-Y`.
- `py agent_cli.py wire --expert` — the Expert Info panel, now one indexed query instead of two full
  scans (D3).
- A saved-filter file (`state/wire/filters.wdf`, one `name = filter` per line) so the diagnoses in
  §4.2 become named verbs rather than remembered strings. This is the mechanism by which a filter
  someone wrote at 3am survives to be reused.

---

## 5. (d) RETENTION AND ROTATION THAT A SEASON CANNOT BLOW UP

### 5.1 Three tiers, and only the bottom one expires

| Tier | Contents | Bound | Measured |
|---|---|---|---|
| **`wire`** (raw) | every round trip, full row | rolling: **30 days OR 2 GB, whichever binds first** | at 38k rec/day × 670 B = **25 MB/day**; 30 days = 765 MB |
| **`wire_anomaly`** | rows where `finish_reason='length' OR status>=400 OR attempt>0 OR error IS NOT NULL OR` fingerprint-change | **never expires within a season** | synthetic anomaly rate 14.2% (28,368/200,000) with a deliberately pessimistic mix (3% error, 5% retry, 7% length); the real fleet rate is lower |
| **`wire_hourly`** (rollup) | `(hour, agent, model)` → count, tokens, cache hit/miss, truncations, errors, retries, reasoning, mean TTFB | **never expires** | 2M raw rows → **19,500 rollup rows (103:1)**; build **1.8 s**; a whole-season rollup query reads it in **3.4 ms vs 2,898 ms** against raw — **853x** |

**This is what makes the season safe.** The raw rows expire and the *shape* survives forever at
~1 MB/season. A question like "did cache hit rate degrade after the fingerprint changed in week 3"
is answerable from `wire_hourly` a year later, having spent a megabyte.

### 5.2 The rotation contract, written as the inverse of D1

Three invariants, each of which D1 violates, each of which should be a pin:

1. **A size check on X may only delete X's own oldest rows.** Never "the newest file is too big, so
   delete the oldest file" (`wire_journal.py:156-161`).
2. **Retention deletes by AGE and BYTES, and the byte bound is enforced by deleting oldest-first
   until under the bound** — with a floor: never delete below `MIN_RETAIN_ROWS` (say 10,000) no
   matter what the byte cap says, so a single pathological day cannot leave the store empty.
3. **Every deletion is COUNTED and reported.** `summarize()` gains `expired_records` and
   `expired_through_ts`. Silent deletion of evidence is D1's actual harm; the fix is not only to
   delete correctly but to say so. This is the same rule as `self.dropped` at `wire_journal.py:103`
   — *"fail-open is only honest when the failures are visible"* (`:47`).

### 5.3 Where retention runs, and what it costs

Measured on the 2M-row / 767 MB season database:

| Operation | Cost |
|---|---:|
| `DELETE FROM wire WHERE ts < ?` (600,000 rows, 30%) | **5.0 s** |
| `VACUUM` afterwards | **2.7 s**, 768 MB → 538 MB |
| `PRAGMA wal_checkpoint(TRUNCATE)` | ms-class when unblocked (`sqlite_store.py:189-199`) |

**5 seconds and 2.7 seconds are cold-path costs and must never touch a runner.** Retention runs:

- from an explicit `py agent_cli.py wire --retain` verb, and
- opportunistically at process close, guarded by a "not more than once per hour" stamp,

never inline in `record()`. And `VACUUM` needs ~2x the database size in temporary free space — which
is why the schema sets `auto_vacuum=INCREMENTAL` before the first table (verified to require exactly
that ordering), so the maintenance verb can call `PRAGMA incremental_vacuum(N)` and reclaim in bounded
chunks instead of a full rewrite.

### 5.4 Backup, because this is now a database

`sqlite_store.py:41-46` states the rule and names the two scripts that violated it. It applies
verbatim here: **`shutil.copy2` of a WAL database leaves the `-wal` behind and yields a stale or
corrupt snapshot while reporting success.** `scripts/wire_store.py` gets a `backup_to()` wrapping
`sqlite3.Connection.backup()` (`sqlite_store.py:202-216`), and the pin already exists as a pattern in
`tests/test_snapshot_wal_correct.py`. `state/*` is gitignored (`.gitignore:108`) and `*.jsonl` at
`.gitignore:50`, so neither the old journal nor the new database can be committed by accident — but a
`.db` is now a thing an operator might reasonably try to copy, and the docstring must say not to.

---

## 6. (e) HOW THE CHEAP PATH STAYS CHEAP

### 6.1 The premise is inverted by measurement, and I want that on the record

The brief says: *"do not put index maintenance on the hot path."* Measured:

```
  today's JSONL append ............................. 235.4 µs   <-- what runs right now
  SQLite insert, 5 indexes live, autocommit ......... 85.0 µs mean / 26.3 µs p50
  ...of which index maintenance is ................. 15.5 µs
  queue.put(tuple) onto a drain thread ............... 2.17 µs
```

Moving to a fully indexed database is **not** a cost to be mitigated. It is a **2.8x speedup** on the
path in question. The thing to remove from the hot path is not index maintenance; it is
`os.makedirs` + `os.listdir` + `os.path.getsize` (**102 µs**, §1.2).

### 6.2 The architecture anyway: a bounded queue and one drain thread

Means are not the risk; **tails** are. The p99 with default autocheckpoint is 890 µs and the max on a
767 MB database was 53.8 ms. Four measures, in order of importance:

1. **The recorder enqueues; a single daemon thread writes.** Hot-path cost becomes **2.17 µs
   measured** — 108x cheaper than today — and every SQLite tail, checkpoint stall and 4.4 ms
   first-insert warm-up moves off the request thread entirely.
2. **`PRAGMA wal_autocheckpoint=0` in every writer.** Measured 37x p99 improvement (7.5 ms →
   0.2 ms) at 20 concurrent processes. One designated process — the CLI reader, the doctor, or a
   maintenance verb — runs `wal_checkpoint(TRUNCATE)` and reports `wal_bytes()` as a health signal,
   exactly as `sqlite_store.py:180-199` does. The prior probe's 523,272-byte held-reader WAL
   (`sqlite_store.py:36-38`) is the failure this prevents.
3. **`synchronous=NORMAL`, never `FULL`** (measured 12x tax) and never `OFF` (corruption risk on a
   file that is supposed to be evidence).
4. **The queue is BOUNDED and overflow is COUNTED.** `maxsize` ~10,000 records (≈7 MB of tuples). On
   overflow the record is dropped and `self.dropped` increments — the same counter and the same rule
   as `wire_journal.py:102-104`. An unbounded queue turns a stalled writer into an OOM; a silent
   bounded one turns it into a lie.

### 6.3 Where the index actually gets maintained

Since indexes ride along at 15.5 µs, there is no deferred-indexing scheme to build. But the escape
hatch is measured and cheap if we ever want it: **`CREATE INDEX` on 200k rows takes 186 ms; on 2M
rows, all five take 4.8 s.** So "bulk load unindexed, index afterwards" is available for backfills
and migration (§7) — 2M rows load in **9.6 s** unindexed — and is simply unnecessary for steady state.

### 6.4 The reader path stays cheap too

`read_all()` must not survive the migration in its current form. `read_all(limit)` at
`wire_journal.py:187` slices *after* parsing everything; the replacement is
`SELECT ... ORDER BY ts DESC LIMIT ?`, measured at **1.4 ms for the last 500 rows out of 2M**. And
`expert()` collapses from two full scans (D3) to one indexed pass over `wire_anom` plus one
`wire_hourly` read.

---

## 7. (f) MIGRATION FROM THE JSONL ALREADY BEING WRITTEN

### 7.1 The window is now and it is small

`state/wire/wire-20260804.jsonl` held 15 records at 02:10 and 50 at 02:20. **The entire corpus to
migrate is currently under 40 KB.** Every day this waits, the migration gets more expensive and D1
gets more chances to destroy the thing being migrated.

### 7.2 The natural key, verified rather than invented

`(trace_id)` where present, else `(ts, status, ms_first_byte)`. Verified on the live file: **50/50
records carry `headers['x-ds-trace-id']`, 50/50 distinct; 50/50 `ts` distinct.** Import is
`INSERT OR IGNORE` against `UNIQUE(call_id, attempt)` with `call_id` synthesised from the trace id for
historical rows, so **the importer is idempotent and can be run repeatedly during the dual-write
window without duplicating a row.**

### 7.3 Six steps, each independently reversible

1. **`scripts/wire_store.py` lands with the schema, the pins, and `import_jsonl()`.** Nothing calls it
   yet. `import_jsonl` maps the 24 known keys to columns and puts every unrecognised key into
   `extra` — a record from a future writer must not be silently truncated on the way in.
2. **`AKASHIC_WIRE_BACKEND` ∈ `{jsonl, sqlite, both}`, default `both`.** Dual write. This is the
   escrow, and it is cheaper than `SqliteStore`'s (`sqlite_store.py:131-136`) because the old format
   *is* the escrow — no export step, no staleness window, no `check_dual_authority`-shaped watcher
   needed for the rollback path.
3. **A parity checker** — `scripts/checkers/check_wire_parity.py`, modelled on
   `scripts/checkers/check_dual_authority.py` (named at `sqlite_store.py:135`): for each day, assert
   `COUNT(sqlite WHERE date=d) == COUNT(jsonl lines for d)` and that the natural keys are set-equal.
   A mismatch is loud.
4. **The existing acceptance runs unchanged.** `tests/test_t156_wire_journal.py` pins W1–W7
   (`:31-38`). Every one of those tests constructs `WireJournal(journal_dir=...)` and calls
   `record()`/`read_all()`/`summarize()`/`expert()`. **The SQLite backend must pass that file
   byte-for-byte with only the constructor argument changed** — that is a differential harness in
   miniature, and the repo has the precedent (`sqlite_store.py:669-682` keeps `fnmatch` rather than
   SQLite `GLOB` *specifically* so the FileStore differential harness stays honest).
5. **Import the historical JSONL**, verify parity, then flip the default to `sqlite`. Keep the JSONL
   files on disk — do not delete them at cutover. They are the rollback.
6. **Retire the JSONL writer** in a later slice, once a full retention cycle has run against SQLite
   and `wal_bytes()` has been observed healthy.

**Two corrections to step 5 that the corpus already paid for.** The lesson
`reversible_cutover_requires_post_flip_reverse_path` (2026-07-28) says a cutover is only reversible
if you **write data after the flip and then verify the reverse path can read it** — and my step 5 as
written fails that test: once the default is `sqlite`, rows written after the flip exist only in the
database, so "the JSONL is the rollback" is true of history and false of everything since. The fix is
to keep `both` as the default until step 6 and treat the `sqlite`-only flip as the *retirement*
event, not a separate earlier one; or, if a `sqlite`-only window is wanted for measurement, ship an
`export_jsonl()` that regenerates the old format from the database and pin it with a
write-after-flip → export → read-back test. The second lesson,
`backend_selector_must_cover_wrapped_factory_branches`, applies to the selector itself: the client is
built through a wrapped branch at `scripts/deepseek_chat.py:83-89` where `AKASHIC_WIRE=0` silently
returns the ordinary client, so a `AKASHIC_WIRE_BACKEND` check that lives only in `wire_store.py`
will report a backend that the factory never actually reached. The selector's status must be derived
from what the factory *did*, not from what the env var *says*.

### 7.4 What the migration fixes for free

D1, D2 and D3 all disappear as a side effect: rotation becomes `DELETE … WHERE ts < ?` with the
invariants of §5.2, `read_all(limit)` becomes `LIMIT`, and `expert()` becomes one query. It is worth
saying plainly that **fixing D1 in place inside `_rotate()` is a two-line change and should happen
immediately regardless of whether this whole design is adopted.** Do not let a good design hold a
data-destruction bug hostage.

---

## 8. THE READERS, NAMED — BECAUSE A WRITER WITHOUT ONE IS THE DEFECT

`core/coord/cognitive_metrics.py` is the standing warning cited by both prior documents: 16 public
functions, 4 live, 12 dead, and `dump()`/`dump_all()` called only by tests. Four named readers:

1. **`py agent_cli.py wire '<filter>'`** — §4.4. The primary human door.
2. **A doctor line.** `core/comm/doctor.py:1069-1116` (`_token_cost_line`) is the exact precedent:
   it reads a `scripts/` journal, derives, and renders a *visible gap* (`UNPRICED (… — no rate in
   PRICES)`, `:1114`) rather than a plausible number. The wire line renders the `expert()` findings
   the same way, including `UNKNOWN` states.
3. **The Bifrost UI pane.** Per the standing boundary, **DeepSeek owns `scripts/bifrost_ui.py`
   integration; I author a standalone `scripts/wire_query.py` and hand over a snippet** — the UI
   calls one function returning a JSON list, and the last-1h query behind it is **1.4 ms measured**,
   which is what makes it viable as a live-telemetry pane rather than a report.
4. **The Season-1 leaderboard join.**
   `docs/library/report/20260804_game-arc-season1-mechanics-opus5_b864f1.md:470-477` specifies the
   leaderboard *joins* behaviour from `cognitive_metrics` and money from `TokenJournal`, *"keyed on
   agent id and time window"*. `wire_hourly` is exactly that key shape — `(hour, agent, model)` —
   and supplies per-call ground truth (truncations, retries, cache split, fingerprint) that neither
   of the other two organs has.

**Money stays in `TokenJournal`.** `scripts/runner_token_journal.py:56-65` remains the sole `PRICES`
table and `price_of()` at `:79` the sole pricing door. `scripts/wire_store.py` holds **no price
literal, no rate, no `cost` symbol, and does not import `runner_token_journal`** — pinnable by AST
check, and the prior design already names that pin (P8). The wire store emits counts; if a cost
question needs wire data, `TokenJournal` grows a reader.

---

## 9. PERFORMANCE BUDGET

Per API call, added by this design, all measured except where marked:

| Path | Cost | Note |
|---|---:|---|
| hot path (request thread), with drain thread | **2.17 µs** | `queue.put`; **−233 µs vs today** |
| hot path, synchronous fallback (no thread) | **85 µs** mean / 26 µs p50 | still **−150 µs vs today** |
| drain thread, per record | 85 µs mean, 890 µs p99 | off the request thread |
| usage-half `UPDATE` | ~26 µs p50 (INFER: same index class as insert) | off the request thread |
| retention / VACUUM | 5.0 s / 2.7 s per 600k rows | **cold path only**, ≤ once/hour |
| `wire_hourly` rebuild | 1.8 s per 2M rows | cold path; incremental rebuild is per-hour, ~1 ms |
| **net change to the request path** | **−233 µs per call (−99%)** | against an 850 ms median TTFB, both are noise; the point is that the direction is negative |

Memory: the drain queue is bounded at 10,000 records ≈ 7 MB. The reader no longer materialises the
corpus — **794 MB peak at 200k records today → bounded by `LIMIT`**.

Disk: **670 B/record with all indexes** (0.75x the current JSONL). 30-day raw retention at the
20-player peak = **765 MB**; anomalies + rollups add < 100 MB and never expire.

---

## 10. CONTRADICTIONS, RECORDED NOT RESOLVED

1. **The prior design's membrane pin P9 forbids a pattern the repo already uses.**
   `api-wire-visibility-design-opus5-2026-08-04.md` §6 P9 asserts *"nothing under `core/` imports
   `scripts.wire_journal`"*. But `core/comm/doctor.py:1099` already does
   `from scripts.runner_token_journal import TokenJournal` — the very precedent I cite for reader #2.
   Either P9 needs an explicit dashboard carve-out, or the doctor line must live outside `core/`.
   **I am not resolving this**; it belongs to whoever owns the membrane statement, and I note that
   `docs/LIVE_CONSTRAINTS.md` is 22 lines and contains no occurrence of "runner", "membrane",
   "storage" or "sqlite" — the law is real and uncodified, which is how this ambiguity persists.

2. **The prior design's `{"v":…,"s":…}` envelope vs. my NULL + `validity` column.** Both encode T141
   honestly. Mine costs ~1 byte/absent field and needs a documented convention; theirs is
   self-describing and costs ~400 bytes/record (≈1.4 GB/season, INFER from field count). I chose
   bytes. If a synthesiser prefers self-description, the SQL layer can *emit* the envelope shape at
   read time from the same information — the two are convertible, and I would rather store the cheap
   form and render the explicit one.

3. **`wire_journal.py`'s docstring vs. its behaviour on rotation.** `:58-59` promises *"Oldest file
   is dropped, newest always survives"*. Measured (§1.5), the newest surviving is the bug. A
   docstring that describes the intent while the code inverts it is worse than an undocumented
   function, because the reader stops checking.

4. **My own benchmark used `eval()` with `ast.Attribute` whitelisted.** §4.3 recommends against
   shipping that. The 0.19 µs/row figure is therefore an **upper bound on the performance of a safe
   implementation**, not a measurement of the recommended one.

5. **Anomaly rate.** My 14.2% figure comes from a synthetic mix chosen to be pessimistic (3% non-2xx,
   5% retry, 7% `length`). The live journal's 50 records are **100% status 200, 0 retries, 0
   truncations** — a sample far too small to contradict anything, but honest to state: I sized
   `wire_anomaly` against a rate nobody has measured on real fleet traffic.

6. **`arc` has no source today.** I put an `arc` column in the schema and indexed it because the
   brief names "by arc" as a query that matters. Nothing in the current code path knows an arc. It
   would have to be injected the way `agent` is (`wire_journal.py:81`, from `BIFROST_AGENT`) — via an
   env var or a client-construction argument. **Until someone sets it, `arc` is UNKNOWN on every
   row**, and an index on an all-NULL column is free but useless. Naming the gap rather than
   pretending the query works.

---

## APPENDIX — WHAT I DID NOT VERIFY

**Measured, and how.** Every number in §1.2, §1.3, §1.5, §2.4, §2.5, §3.2, §4.3, §5.1, §5.3, §6.1
and §9 was produced by five benchmark scripts written to the session scratchpad on 2026-08-04
(Windows 11, `E:` local NTFS, Python with SQLite 3.45.1, 66.2 GB RAM / 23.2 GB free). They were **not
written into the repo** and are not committed. Anyone reproducing should expect variance on the
tail numbers (p99, max) in particular — those are the ones sensitive to what else the machine is
doing, and the machine was running the live fleet during the benchmarks.

**Not verified:**

- **I did not run any of this against the real runner.** Every SQLite number comes from synthetic
  rows shaped like the real ones, not from a live `deepseek_chat` call. In particular the **2.17 µs
  queue-enqueue path is a microbenchmark of `queue.SimpleQueue.put`, not of a working recorder** —
  the real thing must also build the tuple, and I did not measure the tuple build separately from
  the `json.dumps` it replaces.
- **The usage-half `UPDATE` is unmeasured.** §3.1 and §9 assert it is the same cost class as an
  indexed insert. That is INFER from index structure, not a measurement. It is also the *only* part
  of the design that depends on a component that does not exist yet — nothing calls
  `journal().record()` with a `usage=` kwarg anywhere in the repo today (verified by grep), so the
  two-halves join has never been exercised in any form.
- **I did not test the 20-process contention with a long-lived READER holding a transaction open.**
  That is the exact shape `sqlite_store.py:34-39` warns about and measured at 523,272 bytes of
  ungrowable WAL. My contention test had 20 writers and no held reader. The UI is a held reader. This
  is the highest-value follow-up probe and I would not ship without it.
- **Season volume is a derivation, not a measurement.** The 12,600–38,000 records/day band rests on
  a 90k-tokens-per-HTTP-call factor read from a comment (`deepseek_chat.py:207-208`) and a ×10
  scaling from a two-agent fleet to twenty players. Both could be wrong by 3x in either direction.
  The 2M-row benchmark was chosen to sit in the middle of that band; if the real number is 10M the
  full-scan queries (242 ms, 2,898 ms) degrade linearly while the indexed ones (1.4 ms, 3.1 ms,
  57 ms) do not — which is an argument for the design, but it is an extrapolation.
- **I did not implement or test the WDF parser.** The grammar in §4.1 is written, not built. I
  benchmarked the *evaluation* stage using a Python `eval` stand-in and the *SQL* stage using
  hand-written SQL. **The split-into-pushable-and-residual step — the actual novel piece — is
  unbuilt and unmeasured.** Its correctness (does the split preserve semantics under `OR`?) is the
  thing most likely to be subtly wrong.
- **I did not verify FTS5 behaviour**, only its availability (`PRAGMA module_list`). §3.4 defers it
  and that deferral is untested either way.
- **Windows append atomicity.** §1.2 measures the current per-record open/append/close but I did not
  test whether concurrent appends from 20 processes to one JSONL file interleave cleanly. Records are
  ~886 B (under the 4 KB that is conventionally assumed atomic), so it probably holds — but "probably
  holds" is exactly the class of assumption the SQLite path makes unnecessary, and I am flagging that
  **the current JSONL design has a multi-writer correctness question nobody has answered**, not just
  a performance one.
- **`arc`, `ms_ttft`, `ms_max_chunk_gap`, `req_bytes`, `resp_bytes`, `url_path` have no producer.**
  They are in the schema because the brief and the probe battery say they are obtainable
  (`p2-byte-chunks.json` has per-chunk arrival timings; `p3-ttft-decomposition.json` has TTFT). I did
  not verify that any of them can be captured without consuming the SSE stream the runner needs —
  which the prior design calls *"the single real engineering hazard"* (§1). Columns are cheap; the
  producers are somebody's slice and I did not price them.
- **I read `wire_journal.py` (343 lines) and `runner_token_journal.py` (248 lines) in full.** I read
  `sqlite_store.py` in full. I did **not** read `bifrost_ui.py`, `agent_cli.py` (4,800+ lines), or the
  four runners in full — my claims about them come from targeted greps, which can miss.
