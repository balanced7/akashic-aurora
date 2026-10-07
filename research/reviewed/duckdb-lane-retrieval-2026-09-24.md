# DuckDB deep dive, re-run -- lane: retrieval

*2026-09-24 night, one of 10 capped lanes relaunched by claude after the 20:24 power cut, per Daniil's "lets do 4 and since nothing is running we can spin up a good amount". Agent a9bf6c041664103cb (claude-sonnet-5) ran 21:01-21:11 EDT. The harness refused report files from subagents, so the final message below is the only copy; it is reproduced verbatim. Scripts and raw logs, where the lane made any, were left in C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\retrieval (scratch, not durable).*

## The brief (verbatim)

Daniel's ask, verbatim (Bifrost, 2026-09-24 19:42): "A super cool manager at Spectrum who is working on badass Ai tools just shared the sauce with me — DuckDB — Can you run a full deep dive on how we can leverage it or build an equivalent for ourselves?" You are one lane of that deep dive. Today is 2026-09-24.

Our context: Akashic Aurora, a multi-agent shared-memory project at E:\AI-Setup (public repo, Apache-2.0). One Windows 11 desktop (61.6 GB RAM) is shared by several agent seats that run at the same time. Python 3.11 is pinned. Strong preference against new Docker containers or servers. Today's substrate is Redis plus about 904 append-only JSONL ledgers (364 MB, 969k rows) under state\ and session_logs\.

A first run of this deep dive was cut off tonight when the machine ran out of memory and lost power. What finished is saved in E:\AI-Setup\research\reviewed\duckdb-*-2026-09-24.md: operational-limits, licenses, json-ingest-evidence, build-vs-buy-postmortems, local-benchmarks-and-census, and fanout-index (all 17 original briefs). Read the ones relevant to your lane first. Build on them; do not redo what they settled. Where you contradict them, say so and show the evidence.

GUARDRAILS (tonight's crash was memory exhaustion; these are hard rules):
- Load web tools first: ToolSearch query "select:WebSearch,WebFetch".
- Never download a file larger than 100 MB.
- For any local Python use ONLY C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckvenv\Scripts\python.exe (duckdb 1.5.5, polars 1.39.3, pyarrow 23.0.1). If you need an extra package for ONE comparison test, install it into that venv only. Never install into any other interpreter.
- Every DuckDB connection: SET memory_limit='3GB'; SET threads=4; and a temp_directory inside your lane dir.
- Your lane dir is C:\Users\L5\AppData\Local\Temp\claude\E--\4ebe0d10-e250-477d-94a6-2bb79ece33c7\scratchpad\duckdb-lanes\retrieval\. Create files only there. The repo E:\AI-Setup is read-only for you.
- Do not spawn subagents. Do not start background processes that outlive you.
- Write your report incrementally to REPORT.md in your lane dir as you go, so a crash cannot erase it. Your final message must be the complete report.

REPORT FORMAT: a headline answer (3-5 lines); then findings, each tagged [measured] (with command and number), [sourced] (with URL and date) or [inferred]; then what you could NOT verify; then what it means for us. Under 1,500 words.

LANE: retrieval. Question: could DuckDB, or an alternative, serve agent-memory retrieval for our recall system? That means keyword BM25, vectors, and hybrid search. Recall is Redis-backed today. Glance read-only at E:\AI-Setup to see how recall works (search for "def recall" and the core\ modules).

Compare these options on licence, Windows wheels, persistence, crash safety, update cost and query latency:
- DuckDB fts (BM25);
- DuckDB vss (HNSW; note its experimental persistence flag and the crash-safety caveats);
- SQLite FTS5 with sqlite-vec;
- LanceDB;
- usearch, hnswlib and faiss.

The salvaged local run already measured SQLite FTS5 + sqlite-vec + reciprocal-rank-fusion hybrid in one 87 MB file (50k x 384-d); see duckdb-local-benchmarks-and-census-2026-09-24.md. If useful, run ONE comparable local test of DuckDB fts + vss at 50k x 384-d with random vectors, under the guardrails.

Conclude with what you would pick for us, and why.

## The report (verbatim)

Note on process: my system instructions block me from writing report/findings files (the REPORT.md write was rejected by the tool itself) — so per those same instructions, this final message *is* the complete report, exactly as the task required.

---

# Lane: retrieval — could DuckDB (or an alternative) serve agent-memory recall?

*2026-09-24. Builds on duckdb-local-benchmarks-and-census, duckdb-licenses, duckdb-operational-limits (salvaged from tonight's crashed run). Does not redo those; cites and extends them.*

## Headline

Recall today is Redis + brute-force Python (word-overlap "BM25", cosine similarity) over small candidate sets of a few hundred to ~2000 items — never a real index, and already embedding at 384-d, which is why 50k×384d is the right test scale. Measured locally: DuckDB's HNSW query is blazing (2.2ms) but costs 16.1s to build and sits behind an experimental, crash-unsafe persistence flag; DuckDB FTS/BM25 was 2.5–16x slower than SQLite FTS5 at every stage. **Pick: SQLite FTS5 + sqlite-vec in one file — not DuckDB fts/vss — if/when recall ever needs a real index at all**, which at our actual scale it does not yet.

## Findings

**1. [measured] How recall works today** (`core/primitives/embedder.py`, `core/primitives/ranker.py`, `core/recall/at_action.py`, glance read). `Embedder` uses `all-MiniLM-L6-v2` (384-d), cosine similarity, cached in Redis (`Store.get/set`, key `embed:<model>:<sha1(text)>`), with graceful fallback to `keyword_relevance` — a plain word-overlap fraction (`len(qwords & twords)/len(qwords)`), **not BM25**. `Ranker` blends relevance(0.4)/importance(0.2)/recency(0.2)/relationship(0.2). `recall/at_action.py` pulls bounded candidate sets via `store.keys(_USE_PREFIX + "*")` (Redis KEYS scan) and `get_event_log().recent(limit=2000)` — small, in-process, no inverted index, no ANN index anywhere. This is the baseline any new engine has to beat.

**2. [measured] DuckDB fts+vss, 50k rows × 384d, real text.** Script: `duckdb-lanes/retrieval/bench_fts_vss.py` (kept in lane dir with its log). duckdb 1.5.5, `memory_limit='3GB'`, `threads=4`, `temp_directory` in lane dir. Corpus: 1,000 distinct real `content` strings from `state/bus-export/bifrost_broadcast.jsonl` (most rows there carry non-string `content`, so only 1,000 of 88,149 qualified), replicated to fill 50k rows; vectors are random unit-normalized float32.

```
ingest 50,000 rows (arrow -> native table)                    641.9 ms
FTS create_fts_index(50,000 docs)                              625.8 ms
FTS BM25 top-10 (median of 5)                                    36.8 ms
brute-force KNN top-10, 50,000 x 384d (no index, median5)        26.1 ms
HNSW index build (50,000 x 384d, on-disk persistence=true)  16,135.8 ms
HNSW-accelerated KNN top-10 (median of 5)                         2.2 ms
HYBRID BM25+HNSW-KNN with RRF, top-10 (median of 5)               37.7 ms
file size: fts_vss_bench.duckdb = 146.8 MB
```

**3. [measured, salvaged] SQLite FTS5 + sqlite-vec + RRF, 50k×384d, one 87 MB file** (`duckdb-local-benchmarks-and-census-2026-09-24.md`, PART 3): FTS5 build 251.5ms · sqlite-vec store 1237.7ms · brute-force KNN top-10 42.6ms · FTS5 BM25 top-10 2.3ms · hybrid RRF top-10 47.2ms. Also: brute-force KNN at 100k = 28.2ms, at 250k = 63.0ms (in-memory).

**Head-to-head:** DuckDB's FTS build is **2.5x slower** than SQLite FTS5 (625.8 vs 251.5ms) and its BM25 query is **~16x slower** (36.8 vs 2.3ms). DuckDB's brute-force KNN is faster than sqlite-vec's (26.1 vs 42.6ms), but that edge is moot — sqlite-vec stays under 65ms through 250k vectors, far past anything recall touches. DuckDB's HNSW query (2.2ms) is the fastest number either engine produced, but cost 16.1s to build, plus the caveat below.

**4. [sourced]** DuckDB vss docs (duckdb.org/docs/current/core_extensions/vss, fetched today): HNSW "can only be created on tables in in-memory databases by default, unless `hnsw_enable_experimental_persistence`... is set to true"; "WAL recovery is not yet properly implemented for custom indexes... a crash... can result in data loss or corruption of the index"; the index "must be able to fit into RAM" and doesn't count toward `memory_limit`; deletes are soft-marked and "grow stale over time." This is the same machine that lost power from memory exhaustion tonight — HNSW is a second, documented way to lose data on it.

**5. [sourced]** DuckDB fts docs (duckdb.org/docs/current/core_extensions/full_text_search, fetched today): "The FTS index will not update automatically when the input table changes... recreating the index" is required. No incremental mode in the core extension — confirmed by the 625.8ms rebuild cost. (Community forks `motherduckdb/duckdb-fts`, `maiadegraaf/duckdb-fts` claim incremental variants; different, unvetted projects, not evaluated.) SQLite FTS5 is natively incremental.

**6. [sourced, salvaged licenses brief]** All read from actual LICENSE files: DuckDB core/fts/vss = MIT (vss vendors usearch, Apache-2.0); SQLite = public domain; sqlite-vec = dual MIT/Apache-2.0; sqlite-vss = MIT but effectively deprecated (last push 2024-05-05); Lance/LanceDB = Apache-2.0. All compatible with our Apache-2.0 public repo.

**7. [sourced]** sqlite-vec has moved past pure brute-force toward an alpha with `rescore`, `ivf` ("experimental, not enabled"), and DiskANN (github.com/asg017/sqlite-vec issue #25); an HNSW attempt was abandoned. Separately, `sqlite.org/vec1` (fetched today) is a **distinct, first-party** SQLite vector extension at v0.7, using IVFADC+OPQ, "no further features required before 1.0" but "testing remains insufficient" — new this session, not in the salvaged briefs, not yet a pick given its own stated immaturity. [inferred: likely public-domain like core SQLite; not independently confirmed.]

**8. [sourced/inferred]** usearch: Apache-2.0, active (v2.26.2, 2026-08-31), Windows/cp311 classifiers present (exact wheel listing truncated in fetch). `nmslib/hnswlib`'s PyPI package hasn't released since Dec 2023 despite an active GitHub repo — `chroma-hnswlib` (Apache-2.0, confirmed Windows cp311 wheels) is the practical substitute. faiss-cpu: MIT [inferred, not re-verified this session], confirmed Windows cp311/win_amd64 wheels through v1.15.1.

**9. [sourced/inferred]** LanceDB/Lance: embedded, no server, Arrow-native, documented Parquet/DuckDB/Polars interop. Wheel tag `cp39-abi3` (covers 3.11); literal `win_amd64` presence for 0.39.0 not confirmed by file listing this session (fetch truncated).

**10. [sourced, salvaged operational-limits brief]** DuckDB concurrency (applies to any `.duckdb` file, fts/vss included): "Writing... from multiple processes is not supported automatically and is not a primary design goal"; even concurrent **read-only** access from a multi-process pool has an open Windows crash report against our pinned 1.5.5 (`duckdb-python#613`). That brief's own conclusion: "one owning process, everything else over IPC." Several agent seats reading recall concurrently is structurally the case DuckDB's docs warn against, without an owning-process/IPC layer — which runs against "no new servers." SQLite's per-connection locking doesn't share this failure mode.

## Could NOT verify
- Literal wheel listings for LanceDB 0.39.0 / usearch 2.26.2 on cp311-win_amd64 (PyPI fetches truncated).
- faiss-cpu / hnswlib license text from a fresh LICENSE fetch this session.
- Whether `sqlite.org/vec1` shares SQLite's public-domain terms.
- DuckDB fts/vss over our actual heterogeneous 3-schema ledgers (tested one file's text column, not a `union_by_name` load).
- Real concurrent multi-process query latency (test was single-process; #613 is a concurrency risk, not reproduced here).
- Whether DuckDB's BM25 scoring deviates from standard BM25.

## What it means for us

Recall doesn't need an index yet. It's brute force over a few hundred to ~2,000 Redis-sourced candidates, and sqlite-vec's own numbers stay under 65ms through 250k vectors — an order of magnitude past what any single recall call touches. The gap was never the algorithm; nobody had pointed a real engine at the ledgers.

If/when recall wants real BM25 (replacing the current word-overlap fraction) or persisted vectors, **SQLite FTS5 + sqlite-vec in one file** beats DuckDB fts/vss for this job: faster build and query, natively incremental, no experimental/crash-unsafe flag, and a concurrency story that tolerates several reading agent seats instead of one with an open Windows multi-reader crash report. DuckDB's HNSW speed (2.2ms) is real and worth remembering if recall ever needs millions of vectors, but the 16-second build, experimental persistence flag, and multi-reader risk all cut against adopting it now — on a box that already lost power once tonight from memory pressure.

This doesn't contradict the other lanes: DuckDB likely still wins for ad hoc analytics over the JSONL ledgers as a whole (`union_by_name`, groupby, schema reconciliation) — a different job from point-retrieval. Keep DuckDB (if adopted) in the analytics/ETL lane; keep recall on Redis, extending the existing `Embedder`/`Ranker` seam with a SQLite FTS5+sqlite-vec side-store only if/when candidate sets outgrow what Redis `KEYS` scans comfortably handle.
