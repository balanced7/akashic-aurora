# Storage engine sweep — claude's half

Status: current
Class: research

Daniel's ask, verbatim: *"Lets do a round of research on what else like sql we could use that
would fulfill many of our requirements. It needs to be performant, versatile and scalable.
Potentially we can even have it interface directly to redis and have it be a part of our cache
tier system. lets see what everyone thinks and finds"*

Three angles were split to avoid triplicating one search: **kimi** has the failure modes and
the requirements interrogation, **deepseek** has the integration cost against our real
interface, **this document is the landscape sweep**. It is one third of the answer.

**Evidence grades.** VERIFIED-LOCAL = measured on this machine, command in the text.
VERIFIED-PRIMARY = from the project's own docs. SECONDHAND = search summaries, not read
end-to-end.

---

## 1. Two things I verified locally, and one of them is a break nobody had priced

**E: is a local NTFS disk (`DriveType 3`).** VERIFIED-LOCAL. This matters more than it sounds:
the single most-cited SQLite objection is that **WAL mode does not work on network
filesystems** — it requires shared memory, and NFS/CIFS break it. That objection does not
apply to our store location. deepseek's related caveat (`msvcrt.lockf` unreliable on network
drives) is likewise not binding *here*, though it stays true for any future networked deploy.

**The backup and restore path would silently break under any WAL-mode engine.**
VERIFIED-LOCAL, and this is the finding of my half:

- `scripts/ops/snapshot_knowledge.py:105` — `shutil.copy2(STORE_FILE, dest / "store_state.json")`
- `scripts/ops/snapshot_knowledge.py:153-156` — **restores** by copying it back
- `scripts/harmonize_knowledge.py:78` — same `copy2` for its own backup

SECONDHAND but unambiguous in SQLite's own guidance: *never copy a WAL-mode database by
copying just the `.db` file — the latest data lives in the `-wal`, and without it your copy is
stale or corrupt.*

So a storage swap breaks backup **and restore**, and it breaks them in the worst available
way: the copy still succeeds, the file still exists, and it is silently incomplete. A backup
that reports success and restores stale data is worse than no backup, and the memory records
this restore as *proven*. **Any migration must convert these to `sqlite3.Connection.backup()`
(stdlib, online, WAL-correct) in the same slice, or we trade a write-loss defect for a
recovery-loss defect.**

## 2. The field

SECONDHAND unless marked.

| engine | concurrency model | stdlib? | fit here |
|---|---|---|---|
| **SQLite + WAL** | one writer, concurrent readers, ACID | **yes** (3.45.1, VERIFIED-LOCAL) | strong |
| **LMDB** | MVCC, mmap zero-copy reads, **multi-process safe by design**, readers never block writers, one writer | no | strong on reads, adds a dep |
| **RocksDB / LevelDB** | LSM, built for many-core servers, write-amplified, memory-hungry | no | over-engineered for 9MB |
| **DuckDB** | columnar/analytical | no | wrong shape for KV |
| **dbm** | stdlib, but no concurrency guarantees | yes | does not solve the defect |
| **diskcache** | pure-Python, SQLite-backed, built for process-safe caching | no | interesting as prior art |

**SQLite's real gotchas**, which matter more than the feature list:

- **One writer at a time, even in WAL.** Concurrent write transactions are not possible;
  contention surfaces as `SQLITE_BUSY` / "database is locked".
- **Checkpoint starvation** — if there is always at least one active reader, the checkpoint
  never completes and the WAL grows without bound. A long-lived reader process (a runner, the
  UI) is exactly the shape that triggers this. Needs an explicit checkpoint policy.
- WAL cannot be used on a read-only database file (no `-shm`).

**LMDB's distinguishing property** is that multi-process sharing is its design centre rather
than a mode: readers are lock-free mmap lookups and never block the writer. For a read-heavy
workload — which ours is, recall being the hot path — that is the better read story. The cost
is a non-stdlib dependency.

## 3. What the peer field actually chose

SECONDHAND, and consistent across sources: **Letta** uses Postgres or SQLite; **mem0**
recommends SQLite or Postgres for structured data alongside a vector store; **Hermes** (Feb
2026) uses SQLite with FTS5. The 2026 pattern is *SQLite or Postgres for structured state,
plus a vector index for semantic search*.

**Nobody in the agent-memory field is hand-rolling a JSON file store.** That is the honest
headline of this half, and it is the same shape as the oxlint/ruff finding from the earlier
sweep: we keep discovering we are building something the field already standardised on.

## 4. The versatility argument, which is Daniel's second criterion

SQLite is the only candidate that could *consolidate* rather than merely replace:

- **FTS5** — full-text search, built in. Our `lookback` verb currently does keyword search
  across layered corpora by hand.
- **`sqlite-vec`** — vector search as an extension. We already have an embedder and a ranker.
- **The store itself** — kv/hash/list/set/zset over rows.

Three organs we maintain separately could become one engine with one durability story. That is
a real answer to "versatile," and it is not available from LMDB or dbm.

## 5. On "scalable", and a reframe I want challenged

Our actual profile: **single machine, roughly five processes, a ~9MB store, read-dominated.**
Against that, most of this candidate list is over-engineering, and *single-writer is not a
limitation for us* — it is sufficient. The requirement is **correctness under five processes**,
not throughput under load.

If that reframe is right, the field narrows to **SQLite vs LMDB vs keep-files-and-lock**, and
the deploy constraint (core = stdlib-only, no required deps; Redis optional) does much of the
remaining work: SQLite is stdlib, LMDB is not. Choosing LMDB means either changing a deploy
property or keeping two implementations — and we already know from the differential harness
what two implementations of the same semantics cost.

I have asked kimi to attack this reframe specifically, because shrinking the problem is how
you make your preferred answer win.

## 6. Daniel's Redis / cache-tier question

He asks whether the engine could *"interface directly to redis and be part of our cache tier
system."* I think that hides a fork worth naming rather than a detail:

- **(a) File tier becomes a real L2** under Redis's L1, with *defined* coherence between them
  — which is the write-through pattern, and note we already have a Hybrid store doing
  Redis-authoritative-then-heal informally.
- **(b) Redis becomes sole truth** and the file tier becomes a cold archive.

These are different systems with different failure modes, and **(b) changes a deploy property**
— Redis is currently optional, and the no-Redis path is a supported deployment. Any
recommendation for (b) has to say that out loud rather than treat it as an implementation
detail. Routed to kimi as its third question.

## 7. What this half does NOT establish

- No benchmark was run. Every performance claim here is secondhand and none is ours.
- Integration cost is deepseek's half and is not priced here — particularly how five Redis
  structures map onto rows, and how many call sites depend on `FileStore` semantics.
- Migration reversibility is unaddressed. If we cannot roll back, the bar for choosing rises.
- Expiry/TTL ownership after a swap is open: Redis has native TTL, SQLite has none.

## Sources

- [SQLite — Write-Ahead Logging](https://sqlite.org/wal.html)
- [SQLite concurrent writes and "database is locked"](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/)
- [lmdb documentation](https://lmdb.readthedocs.io/en/latest/)
- [LMDB vs RocksDB](https://stackshare.io/stackups/lmdb-vs-rocksdb)
- [Mozilla — Design Review: Key-Value Storage](https://mozilla.github.io/firefox-browser-architecture/text/0015-rkv.html)
- [Agent memory frameworks compared, 2026](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/)
- [AI agent memory architecture: from SQLite to vector DBs](https://www.shareuhack.com/en/posts/ai-agent-memory-architecture-indie-maker-2026)
