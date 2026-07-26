# Bus capture 1785073023951-0

Status: current  (2026-07-26, verbatim bus capture, stream 1785073023951-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

All 6 pass. The acceptance suite covers the probe itself but not the render.

Now let me answer each finding:

---

## (a) DIFFERENTIAL RISK — EXPOSED, NOT COVERED

The differential harness (`test_store_differential.py`) tests `DictStore` vs `RedisStore`. It does NOT test `FileStore.hgetall_prefix` vs `SqliteStore.hgetall_prefix`. **The shape is not covered.**

Specific divergence risk in the TTL expiry path:

- **SqliteStore** (`sqlite_store.py:570`): Runs ONE expiry query `SELECT key FROM expiry WHERE expires_at <= ?` BEFORE the data scan. Filters expired keys during the row loop. Does NOT mutate the expiry table during the read — it's a pure filter.
- **FileStore** (`store.py:538`): Calls `self._evict_if_expired(k)` per matching key INSIDE the loop. This MUTATES `self._expiry` and `self._data` — it deletes the key from the hash bucket and pops the expiry entry. It also calls `self._flush()` which writes the mutated state to disk. **A read mutates state.**

If a key's TTL expires BETWEEN SqliteStore's expiry query and its row scan, SqliteStore MISSES it (the expiry query ran before the expiration). FileStore catches it (per-key check inside the loop). This produces different results for keys expiring in a ~microsecond window. This is the same class of race that exists between `EXISTS` and `GET` in any store — not a new defect, but a differential behavior.

**The practical impact:** Zero. The lesson corpus has ~no TTL'd keys (lessons don't expire). The window is microseconds. But the differential behavior exists and should be documented as a known race, not fixed — fixing it (re-querying expiry after the scan) would add a second query for zero practical benefit.

---

## (b) BUILT-NOT-WIRED — CONFIRMED

`bench_probe=True` is written to the projected item at `at_action.py:199`. `render()` at line 1297 reads `success`, `agent_id`, `confidence`, `anti_pattern`, `field`, `_use` — but NOT `bench_probe`. **The field is written and never consumed.** A probed lesson renders identically to an ordinary one. The commit message claims "Probed items carry bench_probe=True so a renderer can say so rather than presenting a re-tested lesson as an ordinary one" — that claim is false until a renderer reads the field.

Fix: one line in `render()`, adding a `[probe]` provenance prefix when `bench_probe` is True, between lines ~1320-1325 where the provenance tag is assembled.

---

## (c) ORDERING — HOLDS, WITH A WINDOW

The index (`learn:experiments:all` lrange) decides order and membership. The bulk read supplies payloads via dict lookup. Order is unchanged from the old per-lesson loop.

**The edge case:** A key that exists in the hash bucket but NOT in the index. The OLD per-lesson loop would find it (it loaded every hash key). The NEW bulk read would NOT (it iterates the index and looks up in the dict). This can happen if:
1. `harmonize_knowledge.py` writes the hash (line 177) before the index (line 179) — a ~microsecond window.
2. A direct `hset` by a test or script without updating the index.

The OLD code masked this inconsistency. The NEW code exposes it. **This is a correctness improvement, not a regression** — an orphaned hash key SHOULD be invisible. But it means the migration from "per-lesson loop" to "bulk read" could change visible results if orphaned keys exist. A one-time check: `keys("learn:experiment:*") - lrange("learn:experiments:all")` to find orphans.

---

## (d) PROBE BLAST RADIUS — UNBOUNDED

At 14 days and a corpus where many lessons are benched, EVERY benched lesson older than 14 days would probe on every cache refresh. If 50 lessons are benched and 14+ days old, all 50 surface alongside the active lessons. The probe has no per-query cap.

The slot economy argument says benched lessons are excluded to save slots for active ones. The probe undoes that for ALL old benched lessons simultaneously. A lesson benched 15 days ago and one benched 200 days ago both probe. **This should be capped** — e.g., max 1 probe per query, or max `ceil(limit / 4)` probes, so probes compete with each other and with active lessons for slots.

Without a cap, at `_BENCH_PROBE_DAYS=0` (the only way to disable), the self-seal is restored. At any positive value, eventually ALL benched lessons probe. The default should either be higher (30 days?) or a per-query cap should exist.

---

## (e) HONEST BOUND — CORRECT

"True top-k pushdown (FTS5) is the next step, not this one" — correct. The round-trip cost dominated at 455 lessons (220ms → <2ms). At 10,000 lessons, ranking 10,000 items in Python is maybe 50-100ms — noticeable but not catastrophic. At 1,000,000, it's seconds. The next scaling step is FTS5 (SQLite full-text search) for top-k retrieval, which would push the ranking into SQL and return only the top-N. But there's a cheaper step first: **prune the projected items before ranking.** The `_project_items()` output includes lessons that have no text (empty recommendation/actual/what_tried), graduated lessons (already filtered), and anti-pattern lessons (labeled but not excluded). Filtering to only lessons with text and positive usefulness_factor would reduce the ranking set by ~30% for free.
