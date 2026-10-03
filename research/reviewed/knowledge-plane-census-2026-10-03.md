# Knowledge plane census - Akashic Aurora, 2026-10-03

Six blind agents, one plane each, ~1.0M tokens, 445 tool uses. Every number is MEASURED
with the command shown; a figure that could not be produced is reported as NOT MEASURED.
Commissioned for Daniel's ask: a filing/storage/access schema so the right information
lives in the right place. This file is the evidence; the schema is a separate document.

---

## The lesson corpus (`learn:experiment:*` on akashic-redis via HybridStore) and its own field utilisation — the one plane that already reaches a seat, measured 2026-10-03 against E:\AI-Setup.

**CERTAIN: 57.7% of all lesson prose (1,110,094 of 1,924,634 characters) is invisible to the at-action ranker, because `_project_items` picks exactly ONE text field per lesson — the first of (recommendation, actual, what_tried) — and `recommendation` wins on 1,509 of 1,562 rows (96.6%), so `actual` (1,478 rows, 726,002 chars) and `what_tried` (1,508 rows, 384,092 chars) are never matched against any query. Command: scratchpad/census3.py, replaying the exact loop at core/recall/at_action.py:367-372 over `get_learning_store().load_all_learnings_from_store()`.**

### Lesson hash plane — `learn:experiment:<experiment_name>` Redis hashes, HybridStore(Redis akashic-redis:16379 + FileStore), physical file half under E:\AI-Setup\store (10 entries, 17.3 MB)

- volume: 1,562 records. Command: `py -c "...get_learning_store().load_all_learnings_from_store()"` → len = 1562; cross-checked `store.hgetall_prefix('learn:experiment:')` → 1562 and `store.lrange('learn:experiments:all',0,-1)` → 1562 (1562 unique, 0 duplicate ids). CERTAIN.
- identifier: `experiment_name` — a free-text, writer-authored slug, also used verbatim as the join key `recall:use:learn:experiment:<name>` and as the rendered `source`.  (key stability: **mutable**)
- index: learn:experiments:all (list, 1562) for order+membership; learn:experiments:success (zset, 1541 — 25 ids MISSING); learn:category:* (83 keys, 1537 ids covered — 25 MISSING); learn:agent:* (60 keys, only 960 of 1562 ids — 602 MISSING, 38.5% of the corpus invisible to agent lookup; learn:agent:claude holds 365 against 818 claude-authored rows); learn:anti_patterns (set, 58). NO index exists on domain, file, date, trigger, chapter or tag: `store.keys('learn:domain:*' | 'learn:file:*' | 'learn:date:*' | 'learn:trigger:*' | 'learn:chapter:*' | 'learn:tag:*')` each returned 0 keys. Commands in scratchpad/census4.py. CERTAIN.
- reach: **partial**
- underused fields: Fill rates over all 1,562 rows (scratchpad/census_lessons.py). STRUCTURALLY DEAD (<7%): expected 93 = 6.0%; benched 56 = 3.6%; anti_pattern 52 = 3.3%; files_affected 41 = 2.62% (verifies the 10-01 doc's '39 of 1,526' — unchanged after three Wave-0 slices); root_cause 39 = 2.5%; metrics 32 = 2.0% (31 of those are a single vfx chunk_fingerprint key); graduated 3; enforced_by 3; forge_rejected 4; forge_proposal 1 (and that one is EMPTY). PRESENT-BUT-NON-DISCRIMINATIVE: category 84 distinct but 826 = 52.9% 'uncategorized', 34 categories occur exactly once, only 1,392 rows sit in a category with >=10 members; success is 90.5% 'yes' (1,414 yes / 72 partial / 48 no / 28 empty), so the success-derived `importance` is the same value on 90.5% of the corpus; domain 3 distinct values (system 793, empty 695, vfx 74) — verifies the 10-01 doc's '3 labels across 1,529' — and only 74 rows = 4.74% carry a domain OTHER than the inferred default, so D5 cross-domain scoping has 4.74% of the corpus to work with; confidence is 79.4% 'medium' and its vocabulary is SPLIT — 1,240 'medium' / 257 'high' / 37 numeric strings ('0.85','0.9','0.95','0.8') that no comparison handles. FAILURE RECORDS ARE HOLLOW: of the 48 lessons with success='no', 25 carry an anti_pattern and only 3 carry a root_cause.

### `experiment_name` as a naming system (the primary key's own structure)

- volume: 1,535 distinct names over 1,534 named rows, 0 collisions. Command: scratchpad/census_lessons.py / census2.py. CERTAIN.
- identifier: the slug itself  (key stability: **mutable**)
- index: NONE on any component of the name — there is no prefix, namespace or date index
- reach: **pull-only**
- underused fields: There is NO convention. 704 distinct first-tokens, 488 of them occurring exactly once; top prefixes are the English words 'a' (108), 'the' (30), 'an' (10). Separators: underscore in 1,519, hyphen 45, colon 32, space 5. Only 16 names carry a date and 0 carry a slice id (T\d+); 0 match the auto-generated `exp_<iso>` fallback. Names run 0-102 chars, mean 42.8 — 5 are full English sentences ('BeatLog.emit explicit track skips track registration'). The primary key is therefore unparseable: nothing can be grouped, scoped or ranged by it. CERTAIN.

### Ghost records — index entries whose hash holds ONLY the narrative stamp, no lesson body

- volume: 28 records = 1.79% of the corpus. Command: `allids = store.lrange('learn:experiments:all',0,-1)`; `raw = store.hgetall_prefix('learn:experiment:')`; count ids where 'experiment_name' not in raw[...] → 28. Their hashes contain exactly {narrative_chapter, narrative_track}. CERTAIN.
- identifier: the index id (e.g. `windows_powershell_sha256_hex_compat_2026_07_30`, `user_mail_is_mail_not_consume_queue_2026_07_30`) — real-looking lesson names with no content behind them  (key stability: **mutable**)
- index: fully indexed in learn:experiments:all (they occupy 28 live slots) but absent from learn:experiments:success and learn:category:* — they are exactly the 25-28 ids missing from those two indexes
- reach: **dark**
- underused fields: This is measured knowledge LOSS, not an empty field: 26 of the 28 were surfaced to a seat 147 times in total and 10 of them earned an explicit judgment, which their `recall:use:` counters still hold — so a reader once read a body that is now gone. Command: for each ghost, `store.get('recall:use:learn:experiment:'+id)` → 26 with surfaced>0, 147 surfacings, 10 judged. They also drag the whole-corpus fill rate down by 1.8 points, which is why every canonical field tops out at 98.2% rather than 100%. CERTAIN that the bodies are absent now; LIKELY that they were written and later lost rather than never written (the surfacing counters are the evidence).

### The narrative stamp — `narrative_chapter` / `narrative_track` fields, written by core/narrative/chapter_lifecycle.py:107

- volume: 1,474 of 1,562 rows = 94.37% fill, 315 distinct chapter ids, 5 track values (ai-setup 1342, research 78, unknown 46, vision 5, voice 3). Command: scratchpad/census2.py. CERTAIN.
- identifier: `chapter_<12 hex>` — a content-independent minted id  (key stability: **stable**)
- index: NONE on the lesson side (`learn:chapter:*` → 0 keys). The target side exists: `store.keys('narr:chapter:*')` → 906 records.
- reach: **dark**
- underused fields: This is the best-populated and best-formed axis on the plane and NOTHING reads it. The join is perfect: all 315 chapter ids on lessons resolve to a live `narr:chapter:*` record, 0 dangling (command: set(chapter ids) & set(live narr:chapter keys) → 315, difference → 0). 591 chapters exist that no lesson points at. `grep -rln narrative_chapter core/` returns exactly ONE file — chapter_lifecycle.py, the writer. It appears in zero retrieval modules: not in core/recall/at_action.py, not in core/context/relevance_budget.py. A free episode/time/theme axis with 94% coverage and 100% referential integrity, used by no reader. CERTAIN.

### `related_to` / `related_stamped` — the lesson-to-lesson edge set, JSON string on the hash

- volume: 372 rows = 23.82%. Degree histogram {1:199, 2:80, 3:43, 4:28, 5:22} ≈ 790 edges. Command: scratchpad/census2.py. CERTAIN.
- identifier: edges carry `{experiment_name, dims, matched}` — they point by the same mutable slug  (key stability: **mutable**)
- index: NONE — no reverse index; the edges are only readable by loading the whole corpus and parsing each JSON blob
- reach: **dark**
- underused fields: Read by exactly one module, core/recall/knowledge_map.py:75, which is a visualisation surface. Neither ranker traverses it: no graph expansion, no neighbour boost, no `related_to` term anywhere in core/recall/at_action.py or core/context/relevance_budget.py. A 790-edge graph over a quarter of the corpus that contributes nothing to retrieval. CERTAIN.

### Judgment plane — `recall:use:<source>` JSON counters (the input to usefulness_factor and to D5 cross-domain promotion)

- volume: 1,456 keys. Totals: surfaced 24,641 / useful 503 / noise 39 / helped 131 / engaged 1,065. Command: `store.keys('recall:use:*')` then json.loads of each. CERTAIN.
- identifier: `learn:experiment:<experiment_name>` — the lesson's mutable slug embedded in the key string  (key stability: **mutable**)
- index: NONE beyond the key prefix; a full `keys('recall:use:*')` scan is the only enumeration
- reach: **partial**
- underused fields: Judgment rate is 2.73% — (503+39+131)/24,641 = 673/24,641 — which confirms and slightly updates the 2.2% (532/24,344) recorded in the usefulness_factor docstring on 10-02. 394 lessons = 25.2% of the corpus carry any judgment at all; 107 lessons have no `recall:use` key whatsoever. `useful_domains` is the input to D5 cross-domain promotion and exactly ONE lesson in the whole corpus has reached the >=2-domain threshold, so that mechanism has fired once ever. `engaged` is the second-largest signal at 1,065 and is deliberately not a ranking input (at_action declines it; core/recall/curator.py counts it among _CREDIT_FIELDS — the two disagree, per the 10-02 docstring). JOIN DRIFT IS LIVE: 29 of the 1,456 keys point at no existing lesson. CERTAIN.

### What the at-action ranker actually scores — the projection at core/recall/at_action.py:345-397 feeding core/primitives/ranker.py

- volume: 1,478 of 1,562 rows reach the ranker (56 benched are dropped, 28 ghosts have no text). Command: scratchpad/census5.py, a read-only reimplementation of _project_items (no cache write, no surface bump). CERTAIN.
- identifier: item['source'] = `learn:experiment:<experiment_name>`; items are also keyed by their text in the `by_text` map (7 texts collide across 47 lessons)  (key stability: **mutable**)
- index: a TTL disk cache of the projection; no inverted index, no embeddings — relevance is IDF-weighted bag-of-words over tokens of length >3
- reach: **pushed**
- underused fields: The Ranker blends relevance .4 / importance .2 / recency .2 / relationship .2. TWO of those four weights are effectively constant on this corpus: `relationship_type` is never set on a lesson item, so every lesson scores the neutral 0.5 (20% of the score is a constant); `importance` is binary from success and 1,414 of 1,562 = 90.5% share the value 4 (a further ~20% near-constant). Recency uses a 14-day half-life while 1,141 of 1,562 rows = 73% are dated 2026-07 or 2026-08, i.e. 60+ days old → exp(-60/14) ≈ 0.014, so recency is ~0 for three quarters of the corpus. That leaves relevance doing nearly all the discriminating. CARRIED BUT UNUSED by the score: anti_pattern, confidence, agent_id, field, success-as-anything-but-importance — all projected for display/provenance only. NEVER CARRIED AT ALL: category (0 occurrences of 'category' in at_action.py), root_cause, files_affected, related_to, narrative_chapter, metrics, expected. The trigger clause carries 0.6 of the relevance weight and is present on 1,005 of 1,562 = 64.3% (66.6% of rows that have a recommendation); its adoption is NOT monotonic — by month: 2026-06 0%, 07 76%, 08 70%, 09 54%, 10 94%. CERTAIN.

### What the boot-time ranker scores — core/context/relevance_budget.py base_score, the 5-tier ladder under a 2,000-char budget

- volume: scored over all 1,562 rows minus 3 graduated. Command: scratchpad/census3.py, evaluating rb._text_of / rb._TASK_ID / rb._RB_ID / rb._PATHISH against each record. CERTAIN.
- identifier: `experiment_name`, used as the rendered `source` and as the credit_fn key  (key stability: **mutable**)
- index: NONE — select_within_budget does a full corpus scan and sort on every boot
- reach: **pushed**
- underused fields: Measured CEILINGS — the share of the corpus that could EVER reach each tier, regardless of the task: tier 1.0 (T\d\d\d in both task and lesson) 203 rows = 13.00%; tier 0.8 (category 'constraint*' or an RB-\d+ token) 24 rows = 1.54%; tier 0.7 (file-path overlap) 460 rows = 29.45% of which only 41 = 2.62% come from the `files_affected` field the tier was designed around — the other 419 match by a path happening to appear in free prose; tier 0.5 (category words all present in the task text) is dead for the 826 rows = 52.88% labelled 'uncategorized' and impossible for 29 rows whose category has no word tokens. So three of the four non-zero tiers are reachable by under a third of the corpus and the ladder collapses to its 0.0 default for most lessons, where only recency (a <=0.05 additive tiebreak, and `_ts()` returns 0.0 for 28 rows) and the usefulness multiplier separate them. `_text_of` reads only (experiment_name, category, what_tried, recommendation) — `actual`, the longest field at median 440 chars and 96.2% fill, is invisible to boot ranking too, as are root_cause and anti_pattern. CERTAIN.

### Live retrieval probe — what the floor actually admits (AKASHIC_RECALL_FLOOR=0.20)

- volume: 8 representative queries + 120 real core/*.py paths, scored against the 1,478 active items. Command: scratchpad/census5.py (read-only reimplementation; recall_at itself not called, to avoid bumping surfaced counters). CERTAIN.
- identifier: the query is the raw Bash/PowerShell command string, or the Edit/Write file_path (user-level hook: scripts/hooks/claude_pretooluse.py, matchers `Bash|PowerShell` and `Edit|Write|NotebookEdit` in C:\Users\L5\.claude\settings.json)  (key stability: **mutable**)
- index: none; every call ranks the full projected corpus
- reach: **pushed**
- underused fields: UPDATE to the 10-01 doc, which said the push is 'keyed on the Bash command line': it is now ALSO keyed on file_path for Edit/Write/NotebookEdit. But the path key has nothing structured to land on — only 187 of 1,478 ranked texts = 12.7% contain any file-path token at all (137 distinct paths). Paths are matched as a bag of words (tokens of length >3), not as paths: the query 'core/recall/at_action.py' scores 1.000 on a lesson about KB-maintenance belief revision, because it matched 'core'/'recall'/'action'. Per-query counts clearing the floor: core/recall/at_action.py → 26; core/learning/learning_store.py → 27; scripts/bifrost_daemon.py → 26; pytest tests/test_recall_at.py -q → 37; grep -rn files_affected core/ → 24; `git commit -m 'fix'` → 0, max relevance 0.174, NOTHING clears the floor on one of the most consequential commands in the house. Sweeping 120 real core/*.py paths reaches 559 distinct lessons = 37.8% of the active corpus, so 62.2% of active lessons cannot be reached by ANY core file path. CERTAIN.

**Joins:**
- lesson <-> judgment counters via `experiment_name` (recall:use:learn:experiment:<name>): WORKS but LEAKS. 1,456 keys against 1,562 lessons; 29 keys = 2.0% point at no existing lesson and 107 lessons have no counter at all. The key is a mutable writer-authored slug, so every rename silently forks a lesson's credit history. Command: set difference of `store.keys('recall:use:*')` against the loaded experiment_names. CERTAIN.
- lesson <-> chronicle chapter via `narrative_chapter`: WORKS PERFECTLY AND IS UNUSED. 315 distinct ids on 1,474 lessons (94.4%), 315/315 resolve to a live `narr:chapter:*` record, 0 dangling; 906 chapters exist, 591 unreferenced. The id is a minted `chapter_<hex>`, i.e. STABLE. `grep -rln narrative_chapter core/` returns only the writer. CERTAIN.
- lesson <-> touch plane (what a seat actually touched) via `session_id`: BLOCKED, and it is the most expensive blockage. The touch side is healthy — `events:raw` XLEN 10,197, 2,492 touch records, 100% of them carry session_id, 699 carry real file targets over 371 distinct paths. The lesson side has NO session_id field: enumerating every key across all 1,562 records yields 28 distinct field names and session_id is not among them. So the house knows exactly which files a seat touched while it learned something, and cannot attach that to the lesson. CERTAIN.
- lesson <-> code/files via `files_affected`: BLOCKED IN PRACTICE at 41 of 1,562 = 2.62% (verifies the standing 39/1,526 and shows three Wave-0 slices did not move it), 79 distinct paths. The key is a repo-relative path — MUTABLE, dies on any rename or move; core/git/rewrite_map.py exists but no rewrite hook touches this field. core/coord/scene.py:52 already names this as the reason there is no lesson resolver. CERTAIN.
- lesson <-> domain scope (D5 cross-domain promotion) via `domain`: NEAR-DEAD. 3 distinct values; only 74 rows = 4.74% carry anything but the inferred default 'system'; and the earned path (useful_domains >= 2) has promoted exactly 1 lesson ever. Re-running infer_domain over the corpus reproduces the stored value on 851 of 867 labelled rows, so the field is mostly re-derivable and carries almost no independent information. CERTAIN.
- lesson <-> lesson via `related_to`: EXISTS AND IS UNTRAVERSED. ~790 edges over 372 rows (23.8%); read only by core/recall/knowledge_map.py (visualisation). Neither ranker expands a neighbourhood. Edges point by the mutable slug. CERTAIN.
- lesson <-> task/slice id via T\d{3}: WORKS BUT THIN — 203 rows = 13.00% contain a task id anywhere in (experiment_name, category, what_tried, recommendation). This is the ONLY exact-identifier join the boot ladder has, and it is the tier it weights highest (1.0). CERTAIN.
- lesson <-> agent via learn:agent:*: BROKEN BY INDEX DRIFT. 960 of 1,562 ids are in an agent list; learn:agent:claude holds 365 against 818 claude-authored rows. The hash plane has the answer (agent_id, 98.2% fill, 60 distinct) but the index that would make it a cheap query is 38.5% short. CERTAIN.

**Biggest waste:** 1,110,094 characters of lesson prose — 57.7% of the corpus's total text — that no query is ever matched against. `core/recall/at_action.py:367-372` takes the FIRST of (recommendation, actual, what_tried) and stops, so `actual` (1,478 rows, 726,002 chars, median 440, the longest field in the schema and the only one that records what was OBSERVED rather than advised) and `what_tried` (1,508 rows, 384,092 chars) are carried in the record, loaded on every call, and then discarded at the ranking seam. `core/context/relevance_budget.py:_text_of` independently drops `actual` too. Second place, and the better-formed loss: `narrative_chapter` — 1,474 rows at 94.37% fill, 315 chapter ids, 315/315 resolving to live chronicle records with zero dangling edges, a STABLE minted id, written by one module and read by none. It is the only high-coverage, referentially-sound, rename-proof axis on the plane, and it is worth more than `category` (52.9% 'uncategorized'), `domain` (4.74% non-default) and `files_affected` (2.62%) put together.

**Not measured:** Retrieval QUALITY. I measured how many lessons clear the 0.20 floor, not whether the right one is at rank 1. The recall bench (core/recall/bench.py) was not run — the task forbade pytest, and the usefulness_factor docstring's own 25-moment numbers are the only precision evidence in hand and they are secondhand.; Whether any lesson has ever been RENAMED. I established that `experiment_name` is a free-text slug and that 29 recall:use keys are orphaned (consistent with renames, deletions, or the 28 ghosts), but I found no rename ledger to query and did not attempt to reconstruct one from the event stream. The 'mutable' key_stability verdict is CERTAIN as a property of the schema (nothing pins the name), LIKELY as an observed event.; The FileStore half of HybridStore. E:\AI-Setup\store is 17.3 MB / 10 entries and E:\AI-Setup\session_logs is 163.2 MB / 1,047 entries, but I did not verify that the file plane agrees with Redis, so the 2.3% FileLedger loss recorded in memory is neither confirmed nor refuted here.; Token cost of the lesson surface. I did not measure how many characters the boot lesson section or the at-action injection actually spends, nor how the 2,000-char budget is consumed in practice.; Staleness of the at-action TTL disk cache against the live store — I deliberately reimplemented the projection read-only rather than calling _cached_items, so I never compared the two.; The injection and outcome ledgers (`recall:surface`, `recall:outcome` streams) were not read. The 10-01 doc's '7,219 outcome rows in a week, every one outcome: None' is therefore NOT re-verified; I only measured the aggregate counters those rows feed.; Whether the 28 ghost records' bodies are recoverable from session_logs, the legacy learnings.jsonl, or a git-tracked export. I established the loss, not its reversibility.; Any other knowledge plane. This census covers the lesson corpus only; docs/, the chronicle, notes, handoffs, gate_rules, verbs and the term registry were touched only where they sit on the far side of a join I was testing.

---

## The dark document planes at E:/AI-Setup — fences, rulings, library atoms, notes, research/reviewed, research/in-flight, chronicles, charters, design/. Measured 2026-10-03, read-only; every number below has its command printed beside it.

**CERTAIN — The filing schema Daniel is asking for already exists, is populated, is indexed, and has no door. The library holds 1,019 distinct atoms (`py -c "... st.zrange(IDX_ALL,0,-1)" -> 1019`) with `category` filled on 1,363 of 1,377 records = 99.0% across 24 labels, `type` and `status` 100%, and live Redis facet indexes (`artifact:index:category:method`=325, `:bus`=335, `:type:report`=597, `:status:draft`=399) whose backlink index shows ZERO drift (`fam.verify_backlink_index()` -> 0 rows). `AtomFamily.find(type_, arc, category, status)` implements exact facet intersection — and it has no CLI subcommand (`grep -n "dsps.add_parser" agent_cli.py` -> only new|adopt|arc) and no MCP tool (`grep -oE "^async def [a-z_]+" ai_setup_mcp.py` -> has `adopt`, has `knowledge_map`, has NO `lookback` and no doc search). Compare the lesson plane's 3 domain labels across 1,529 lessons: the library solved the domain-axis problem 1,300 atoms ago and nobody can ask it a question.**

### Library atoms. Truth: store/docs/*.jsonl (append-only version events) 9 files / 17,333,462 bytes. Live state: Redis via core/foundation/store.create_store, keys artifact:<id> + artifact:index:<facet>:<value> + IDX_ALL zset. Human face: docs/library/<type>/*.md projections, 1,015 files / 12,551,533 bytes.

- volume: 1,377 version events across 7 type files (`for f in store/docs/*.jsonl; do wc -l < $f; done` -> brief 85, chronicle 35, contract 5, design 462, map 6, report 778, ruling 6); 1,019 DISTINCT atom ids (python dedupe by d['id']); 1,019 members in IDX_ALL (`st.zrange(IDX_ALL,0,-1)`); 1,015 projection .md on disk (`find docs/library -type f | wc -l`). Drift: 1019 indexed - 1015 projections = 4 atoms with no file.
- identifier: art_<YYYYMMDD>_<slug(title,40)>_<sha6(title|ts|seats)>  (core/library/atoms.py:178). Projection filename is derived from it. body_sha = sha12(body).  (key stability: **stable**)
- index: A REAL INDEX, three of them: (1) Redis facet sets type/status/arc/category + inverse sets cited-by/supersedes, intersected by AtomFamily.find(); verify_backlink_index() returned 0 drift rows this run. (2) docs/SHELVES.md and docs/ARCS.md — these ARE directory listings, auto-generated by scripts/generators/gen_library.py, generated 2026-07-24, 655 entries each (`grep -c "docs/library/" docs/SHELVES.md` -> 655) against 1,015 files today, so 360 atoms (35.5%) are missing from the house's own library index while both files self-declare `Status: current`; 47 library files are newer than SHELVES.md (`find docs/library -name '*.md' -newer docs/SHELVES.md | wc -l`). (3) the `docs` layer of core/recall/lookback.py: flat lexical over the first BODY_CHARS=12,000 chars of the projection markdown.
- reach: **partial**
- underused fields: arc 144/1377 = 10.5%; seats 192 = 13.9%; body_type 342 = 24.8%; schema_version 342 = 24.8%; supersedes 1 (0.1%), superseded 4 (0.3%) — bitemporal machinery present, essentially unused; citations_out 393 = 28.5%, and 390/1019 = 38.3% of atoms have an inbound citation in the cited-by index. The two that ARE filled and wasted: category 99.0% / 24 labels and type 100% / 7 types, both indexed, neither queryable from any seat door. Separately, lookback reads the PROJECTION's flat text and resolves `class` on only 2 of 1,060 docs-layer items (99.8% 'unclassed'), so the YAML front matter carrying type/arc/category/seats/visibility is ignored by the one verb that actually reaches these files. 399/1019 atoms (39%) are status:draft. 473/1060 docs-layer items (44.6%) read as 'unstamped'. 321/1015 projections (31.6%) exceed 12,000 chars and are truncated; 68.6% of library bytes are indexed.

### Fences — the house's blind-halves design rulings. fences/<slug>/{brief,half_a,half_b,reconciliation}.md + fence.json. Plain files on disk, no store, no Redis.

- volume: 28 fence dirs, 166 files, 3,968,478 bytes (`find fences -type f | wc -l`; python os.walk sum). 118 .md / 1,329,210 bytes / 17,053 lines (`find fences -type f -name '*.md' | xargs wc -l | tail -1`). 21 reconciliation.md = 2,665 lines (`find fences -name reconciliation.md | wc -l`). 41 json, 7 jpg.
- identifier: the directory slug (human-chosen, e.g. `context-system`) plus the slot filename. No per-record id, no header block, no category, no arc, no gist. fence.json carries id/question/tier/seals/authors/pv only.  (key stability: **stable**)
- index: NONE in any retrieval sense. `py agent_cli.py fence list` prints a directory listing: id, tier, first 60 chars of the question, which slots are sealed. It indexes no content. Worse, it only sees dirs with a fence.json: 22 of 28 (`find fences -name fence.json | wc -l` -> 22), so 6 fences are invisible to their own plane's index — comms-loop, eye-preset-register, identity-activation (which holds a SEALED reconciliation.md), screenspace, watcher-reliability, world-consolidation. `grep -rn "fences" core/recall/*.py` returns exactly one hit and it is a docstring: fences are in no recall corpus at all.
- reach: **dark**
- underused fields: There are no fields to underuse — that is the finding. fence.json has no category, arc, gist, citations or body index. Adoption into the library, which would give them all of that, has not happened: 1 of 118 fence .md files and 0 of 21 reconciliations have an exact-prefix atom twin (python prefix match of normalised first 300 chars against all 1,019 atom bodies). CONFIRMED BY PROBE: `py agent_cli.py lookback "task_source inferred overridden declared focus misattribution auditable"` returned 7 hits, 0 of them the 2 true files that grep finds (fences/context-system/half_b.md, fences/context-system/reconciliation.md). 20 of 28 fences mention session_id; none are reachable.

### research/reviewed — the plane house doctrine says must hold full-fidelity peer reports. Plain files.

- volume: 213 files / 12,914,061 bytes total (`find research/reviewed -type f | wc -l`). Of those: 120 top-level .md / 1,914,001 bytes / 20,210 lines — the only ones any code looks at; 29 .md inside 8 subdirectories; 9 non-.md top-level; plus 24 .log, 19 .jsonl, 15 .json, 3 .py.
- identifier: the file path. Nothing else — no header id, no atom id, no front matter.  (key stability: **mutable**)
- index: A path exists and it indexes 0.50% of the bytes. core/recall/lookback.py:_research_items calls `_read_head(p, 80)` where the signature is `_read_head(path, chars=BODY_CHARS)` and BODY_CHARS=12000 — so research passes 80 CHARACTERS, not 80 lines. Verified live: `py -c "...max(len(i['text']) for i in lb._research_items())"` -> 80. 120 files x 80 = 9,600 chars indexed over 1,914,001 bytes = 0.50%. The loader is `os.listdir(research/reviewed)` filtered to `.md`, so the 8 subdirectories (29 .md, including origin-2026-04-13 and origin-prelog-2026-04-11) and all 9 non-.md top-level files are not scanned at all. And the layer is CLI-only: `grep -c "def lookback" ai_setup_mcp.py` -> 0, and core/recall/knowledge_map.py imports only `_docs_items, _note_items` — so from the MCP door that Claude Code seats actually use, research/reviewed does not exist in any form.
- reach: **partial**
- underused fields: No fields exist. The measurable waste is adoption: 45 of 120 top-level .md (37.5%) have an exact-prefix atom twin in the library and are therefore reachable at 12,000 chars through the docs layer; the other 75 (62.5%) are reachable only by their first 80 characters, i.e. their title line. CONFIRMED BY PROBE: `py agent_cli.py lookback "two consecutive reds before page single red is banner tier"` returned 0 research hits although grep finds the phrase in research/reviewed/deepseek-door-probe-attack-2026-07-26.md, research/reviewed/deepseek-recall-validity-round1-2026-07-27.md and research/reviewed/origin-prelog-2026-04-11/operator-spine-2026-04-11_2026-08-16.md. CONTRAST PROBE: `lookback "one writer or many readers never both"` DID surface docs/library/report/20260924_duckdb-deep-dive-synthesis_a17a3d.md (rel 0.727) — the adopted twin — while the identical research source stayed invisible. Adoption, not ranking, is the variable.

### research/in-flight — working peer reports not yet reviewed. Plain files.

- volume: 926 files / 35,956,267 bytes, of which 486 .md (`find research/in-flight -type f | wc -l`; `-name '*.md' | wc -l`; du -sh -> 37M). For scale this is 2.9x the whole library projection plane by bytes.
- identifier: the file path.  (key stability: **mutable**)
- index: NONE. No layer in core/recall/lookback.py (LAYERS = docs, charters, research, notes, promoted, chapters, git — `research` resolves to research/reviewed only). No atoms. No listing. grep or `py agent_cli.py find` (Everything/es.exe, filename only) are the entire access surface.
- reach: **dark**
- underused fields: n/a — no schema at all. Note that the first-pass receipt the 10-01 diagnosis itself cites lives here (research/in-flight/recall-experience-round-2026-10-01/first-pass-easy-vs-thorough.md) and is reachable only because a copy was adopted as docs/library/report/20261001_first-pass-easy-vs-thorough_627c36.md.

### Rulings — split across two homes that do not know about each other. (a) docs/library/ruling/*.md + store/docs/ruling.jsonl; (b) fences/*/reconciliation.md.

- volume: (a) 6 projection files / 6 jsonl records / 5 in the Redis type index (`st.smembers(artifact:index:type:ruling)` -> 5). (b) 21 reconciliation.md / 2,665 lines. Total ruling corpus the house actually produced: 27 documents, of which 5 are indexed. `ls docs/library/ruling/`; `find fences -name reconciliation.md | wc -l`.
- identifier: (a) art_ id, stable. (b) the fence directory slug — and the slot file is overwritten in place by `fence write`, so a reconciliation has no version history and no supersession record.  (key stability: **mutable**)
- index: (a) the atom facet index — 5 of 6 rulings, and `type=ruling` is only queryable from Python. (b) nothing. There is no ruling registry, no verdict store on disk (`ls state/` shows drill scratch, no verdicts), and `adjudicate`/`verdict_file` write to the lesson plane, not here.
- reach: **dark**
- underused fields: The ruling type exists in the taxonomy and 5 atoms use it, against 21 reconciliations that are rulings in everything but filing. 0 of the 21 are adopted. This is the plane with the highest value-per-byte in the census and the lowest coverage.

### Notes — core/learning/agent_memory decisions (ADR records), Redis-backed.

- volume: 1,877 records (`get_agent_memory().get_decisions(days=3650, include_superseded=True)` -> 1877); 662 superseded (35.3%); ~5.38 MB of stored text. Title namespaces: 1,175 unprefixed, 552 `scratch:`, 67 `handoff-spill:`, 18 `save:`, 9 `toast:`, 6 `research:`, 5 `fence-in-flight:`.
- identifier: ADR_<MMDDHHMMSS>_<hash8>, e.g. ADR_1001232354_20b345ec.  (key stability: **stable**)
- index: The `notes` layer of lookback and of knowledge_map (so this plane IS on the MCP door via knowledge_map). Text indexed = title + decision = 5,149,877 of 5,382,336 stored chars = 95.7%. This is the BEST-indexed plane measured. Also `notes --all` / the `notes` MCP tool.
- reach: **pull-only**
- underused fields: session_id 3 of 1,877 = 0.2% — the join key the whole Wave 0 context door is built around is empty here. rationale 0.0%, alternatives 0.0% (both fields exist on the dataclass and are never written). context 35.2%. curated 53.9%. supersedes 33.7%. And there is NO category, arc, domain or trigger field on a note at all, which is why Daniel's verbatim steers (552 of them filed as `scratch:`) can be found but can never be pushed at a moment.

### Chronicles — chronicles/story.index.json (derived index) + story.md (projection) + 8 smaller json/md. chronicles/ = 12 files / 8,164,109 bytes.

- volume: 458 chapters (`json.load(story.index.json)['chapters']` -> 458), 4,450 beats, 5 tracks (ai-setup 390, research 43, unknown 13, vision 9, voice 3). story.md 979,007 bytes / 7,299 lines. story.index.json 1,559,006 bytes, generated_at 2026-10-02T01:08:15Z.
- identifier: chapter_<hex12>, e.g. chapter_f6c22117c0b0.  (key stability: **stable**)
- index: The `chapters` layer of lookback (NOT of knowledge_map — knowledge_map imports only docs and notes, so chapters are off the MCP door). Indexed text = title + summary only = 918,180 of 1,382,286 chapter-JSON chars = 66.4%. The 4,450 beats, the learnings arrays and the commits arrays are never searched.
- reach: **pull-only**
- underused fields: `why` 0.0%, `final` 0.0%, `valid_to` 0.0% (bitemporal field, never closed). learnings 316/458 = 69.0% — a real chapter->lesson join sitting in JSON that no retrieval surface reads. commits 153/458 = 33.4% — a real chapter->git join, same situation. `relates` is 100% filled but every edge is the same shape (part_of -> narr:track:<name>), so the connectome here carries one kind of edge and no intellectual edges.

### design/ — build specs. 4 .md / 38,658 bytes among 145 files / 11 MB (the remaining 141 are vfx json, chunks, thumbs, snaps — assets, not documents).

- volume: `find design -type f | wc -l` -> 145; `-name '*.md'` -> 4: CONTRACT.md, s2-recall-outcome-adjudicator-spec.md, suite-verb-family-spec.md, t196-ask-transaction-spec.md.
- identifier: the file path.  (key stability: **mutable**)
- index: NONE for the directory — design/ is in no LAYERS entry. 2 of the 4 .md have an atom twin and are reachable through that twin only.
- reach: **partial**
- underused fields: CONFIRMED BY PROBE: `py agent_cli.py lookback "settlement idempotent per reply atomic Lua transition redrive"` returned docs/library/design/20260805_t196-ask-transaction-spec_b59657.md at rel 0.817 and never returned design/t196-ask-transaction-spec.md, although grep finds the phrase in both. Adoption is the whole difference between reachable and dark, and it is the cheapest lever in this census.

### charters/ — seat CHARTER/INTERIORITY/QUESTIONS, the corpus of what was MEANT. 13 entries, 21 .md / 168,735 bytes.

- volume: `find charters -type f -name '*.md' | wc -l` -> 21; lb._charter_items() -> 21 items.
- identifier: the file path (charters/<seat>/<FILE>.md).  (key stability: **mutable**)
- index: Its own `charters` layer in lookback at the full 12,000-char head — deliberately separate from `docs` so it does not compete for the same PER_LAYER slots. CLI-only (not in knowledge_map, not on MCP).
- reach: **pull-only**
- underused fields: Status is inferred from text, not declared; a retired seat's charter is distinguished only by the literal string 'RETIRED' in the first 600 chars.

### The push surface, measured for completeness because it bounds every plane above. agent/harness hooks -> core/recall/at_action.recall_at(); agent_cli boot -> GROUND FIRST line.

- volume: recall_at composes exactly three sources: _lessons() + _locks() + _verbs() (core/recall/at_action.py:1799-1840). Zero document planes. boot emits exactly one document-plane item: `# GROUND FIRST: <pointer>` clipped to 160 chars with an age stamp at GROUNDING_FRESH_DAYS=7 and a path-resolvability check (agent_cli.py:1769-1778).
- identifier: GROUND FIRST is a hand-set free-text string, not a query and not a key.  (key stability: **none**)
- index: n/a. `grep -rn "lookback|knowledge_map" --include=*.py` outside core/recall shows the only non-CLI callers are cmd_lookback, cmd_knowledge_map, the MCP knowledge_map tool, and a help string in agent/harness/codex_bifrost_wake.py. Neither verb is called by boot, by any hook, or by any daemon.
- reach: **pushed**
- underused fields: 1 of 10 document planes reaches a seat without the seat asking, and the thing that reaches it is a 160-character hand-typed pointer. The 10-01 claim 'one cell and a dozen dark planes' is CONFIRMED at the push layer exactly as written; what has changed is only that the PULL layer is richer than that doc credits.

**Joins:**
- atom <-> atom via citations_out / the cited-by inverse set: WORKS, and it is the only healthy join in the census. 393 of 1,377 records carry citations_out (28.5%); 390 of 1,019 atoms (38.3%) have at least one inbound citation; fam.verify_backlink_index() returned 0 drift rows; lineage() and resolve_current() carry backlinks across supersession. Key is the art_ id — stable.
- atom <-> research/reviewed via a path string: BLOCKED. 403 of 1,015 projections mention `research/` (grep -rl), but the reference is a repo-relative file path — MUTABLE, broken by any rename — and nothing resolves it. The reverse direction barely exists: only 4 of 213 research/reviewed files cite an art_ id. There is no resolver, no index, and no typed relation.
- fence <-> anything: BLOCKED, in both directions. 0 of 166 fence files cite an art_ id. 22 cite a research/ path and 12 cite a learn:experiment: id, but no index reads either, and fence.json carries no citation field. The 10-01 doc's 'cross-plane ids stay with the parent fence' decision is therefore currently unimplementable: the parent fence has no id that anything else can hold.
- atom <-> lesson via learn:experiment:<name>: PARTIAL. 36 of 1,015 projections (3.5%) cite a lesson source string. The lesson name is STABLE (it is the dedup/idempotency key per house doctrine), so this join would work — but there is no inverse index, so it is a grep, not a join.
- chapter <-> lesson via chapters[].learnings: EXISTS IN THE DATA, UNREACHABLE. 316 of 458 chapters (69.0%) carry a learnings array and 153 (33.4%) carry commits. Both are typed, both are stable keys (lesson name, git sha), and the only retrieval surface over chapters indexes title+summary and drops them.
- note <-> session / the Eye: BLOCKED. session_id is filled on 3 of 1,877 notes = 0.2%. Same key, same cause as the 0.0% in the 10-01 table; W0.2 landed for touches, not for notes.
- projection file <-> atom record: WORKS but drifts. The projection filename is derived from the art_ id, so the join is exact. Counted: 1,019 atoms indexed vs 1,015 .md on disk = 4 atoms with no projection. Not measured: whether the 1,015 bodies still match their atoms' body_sha.
- any plane <-> any plane via title or date: BLOCKED by design, and worth naming because it is the tempting shortcut. Three of the four largest planes key on a mutable file path, and the atom id bakes the title in (art_<date>_<slug40>_<sha6(title|ts|seats)>), so a retitle mints a NEW id rather than renaming the old one. Title is not a key here; the supersession chain is.

**Biggest waste:** Two, and they are different kinds. (1) HIGHEST VALUE PER BYTE: the 21 sealed fence reconciliations — 2,665 lines inside fences/ (166 files, 3,968,478 bytes total; 118 .md, 1,329,210 bytes). These are the house's peer-verified design rulings, every one produced by blind halves and a reconciliation pass, and they have no id, no header, no category, no atom, no corpus membership and no index beyond a directory listing that cannot even see 6 of the 28 fences. 0 of 21 are adopted; 1 of 118 fence .md files is. A probe for a concept that exists only in a fence returned 7 hits and none of them the fence. (2) LARGEST RAW MASS: research/in-flight at 926 files / 35,956,267 bytes / 486 .md — 2.9x the entire library projection plane by bytes, with zero index of any kind. And the cheapest single fix the census found is neither of those: research/reviewed is indexed at 80 characters per file because `_read_head(p, 80)` passes a CHAR count where the default is BODY_CHARS=12000 — 0.50% of 1,914,001 bytes. Raising one integer makes 75 unadopted peer reports (62.5% of the plane) content-searchable; adoption makes them joinable.

**Not measured:** Lesson-plane figures (the 1,529 lessons, 3 domain labels, 2.3% judged surfacings, 0 votes). Out of this plane's scope and not re-run — the 10-01 numbers are carried forward unverified, not confirmed.; The Eye / transcripts (51,753 events) and the connectome's 39,358 edges. Not re-counted this run.; Retrieval QUALITY over the document planes: no recall@5 / precision@3 number exists for docs, because core/recall/bench.py's eval set is the 40 lesson moments from W0.3. There is no document eval set, so every reach claim here is binary (surfaced / did not surface) from 3 hand-built probes, not a rate.; Whether the 1,015 projection bodies still match their atoms' body_sha — i.e. store-vs-projection drift. fam.verify_backlink_index() covers citations only.; Whether the Redis atom index rebuilds correctly from store/docs/*.jsonl. AtomFamily.rebuild() exists and was NOT exercised (it writes).; The manuals shelf (FTS5 + MiniLM + RRF, the one engine that reportedly works) — its corpus size, its coverage, and whether it could index these planes unchanged. Not touched this run.; Token cost per retrieval path. lookback defaults to PER_LAYER=3 over 7 layers and knowledge-map to 6; the docs layer alone holds 1,060 items competing for 3 slots, but I did not measure the token size of a typical answer or what a seat pays to widen it.; Duplicate overlap between research/in-flight and research/reviewed, and between either and the library projections. Only exact-prefix (first 300 normalised chars) matching was run; near-duplicates and partially-edited adoptions would read as misses.; git / authorship-ledger joins to any document plane. Not attempted.; Whether boot's GROUND FIRST pointer currently resolves. `boot` records a session, so it was not run; the mechanism was read from source only.; Anything behind pytest or redis db 15 — excluded by the run's rules.

---

## The event/observation planes of Akashic Aurora (E:/AI-Setup), measured 2026-10-03 ~10:50-11:05 EDT: the Eye (transcript events + connectome + chain + pyramid), touch.v1, the events:raw firehose and its time index, the injection ledger (recall:surface + inj/), the stage/outcome ledger (recall:outcome + stage/), the recall call-outcome ledger (recall_outcomes.jsonl), impressions/flips, session signals, agent:events handoffs, and the dsh door capture log. All reads read-only; no mutating verb, no pytest, db15 never opened.

**The target axis is two mutually unintelligible vocabularies, so the join Wave 0 is being built on does not currently exist: 0 of 365 normalised touch target keys appear among recall:outcome's 17,733 target keys (intersection computed raw AND again after stripping the p:/c: prefix and case-folding). Inside touch itself the W0.1 `work:` form appears on 16 of 1,011 targets (1.6%) and was emitted only between 2026-10-02 00:17 and 2026-10-02 00:54 -- every touch in the 34 hours since carries a bare repo-relative path with no repository qualifier. Command: py script over r.xrange('events:raw') + r.xrange('recall:outcome'), set intersection.**

### The Eye, transcript events. SQLite table `events` (+ events_fts FTS5, chain, pyramid) in E:\AI-Setup\state\eye\eye.db -- 313,442,304 bytes, WAL, gitignored by `state/*` (git ls-files state/eye returns empty), local disk only, no backup found.

- volume: 51,753 events over 1,673 distinct sessions; 411,866 chain rows; 6,119 pyramid nodes (L1 4,608 / L2 1,511); 1,400 transcript files tracked in ingest_state. voice: agent 30,567 / system 12,900 / operator 8,286. Commands: sqlite3.connect('file:E:/AI-Setup/state/eye/eye.db?mode=ro',uri=True) then SELECT COUNT(*) FROM events / SELECT COUNT(DISTINCT session) FROM events / SELECT voice,COUNT(*) FROM events GROUP BY voice. STALENESS: SELECT MAX(ts),MAX(indexed_at) FROM events = 2026-10-01 09:17 both; COUNT WHERE ts > now-86400 = 0; last 7d = 2,077. At a wall clock of 2026-10-03 10:53 the transcript plane is 2.07 days behind. 51,753 is EXACTLY the figure in the 2026-10-01 doc -- CERTAIN that no ingest has run since.
- identifier: event_id (TEXT PRIMARY KEY); session (the harness session uuid); uuid / parent_uuid (72.2% / 69.4% nonempty). All stable across rewrites; `line` is the one mutable field (a positional offset into a transcript jsonl).  (key stability: **stable**)
- index: FTS5 over `text` only (events_fts, 51,753 rows) plus the event_id PK autoindex. sqlite_master shows NO index on session, ts, voice, type, seat or branch -- every per-session, per-seat or time-window query is a full scan of 51,753 rows in a 313 MB file. Command: SELECT name,tbl_name,sql FROM sqlite_master WHERE type='index'. REACH DETAIL: pull-only AND pull-REFRESHED -- grep over scripts/hooks/ and agent/harness/hooks/ for 'eye ingest'/'eye_ingest' found no caller and no scheduled task references it, so nothing pushes the Eye at a seat and nothing keeps it current.
- reach: **pull-only**
- underused fields: `seat` nonempty on 240 of 51,753 rows = 0.5%, and SELECT seat,COUNT(*) GROUP BY seat returns exactly one value ('kimi', 240) -- the per-seat axis of the transcript plane does not exist. cwd 72.2%, branch 72.2%, uuid 72.2%, parent_uuid 69.4% (the 27.8% gap is the queue-operation / user-message records, which therefore cannot be chained).

### The Eye's connectome. SQLite table `edges` in the same eye.db (schema at core/eye/connectome.py:77-83, rebuilt wholesale by build() on every ingest).

- volume: 39,358 edges -- EXACTLY the figure in docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md, confirming no rebuild since 2026-10-01. By edge_kind: follows 35,700 / same_utterance 3,249 / adjacent 409. By formed_via: transcript 35,700 / text-identity 3,249 / adjacency 409. By evidence: recorded 35,700 / derived 3,249 / inferred 409. MIN/MAX formed_at = 2026-06-16 .. 2026-10-01 09:17. Commands: SELECT edge_kind,COUNT(*) FROM edges GROUP BY edge_kind; same for formed_via and evidence.
- identifier: composite PRIMARY KEY (src, dst, edge_kind), where src and dst are event_ids  (key stability: **mutable**)
- index: edges_src ON edges(src), edges_dst ON edges(dst). No index on edge_kind or formed_via. KEY-STABILITY DETAIL: build() runs DELETE FROM edges and rewrites the whole table on each ingest, and src/dst derive from transcript position, so no edge identity survives a re-ingest. REACH DETAIL: `eye trace` is the only reader and it is a pull verb; scripts/checkers/check_organ_canaries.py:136 already carries a RED canary for this organ.
- reach: **dark**
- underused fields: VERIFIED, and sharper than the 10-01 claim: of the five MIND-formed values declared in core/eye/connectome.py:57 FORMED_VIA -- fence, recall-firing, fan, supersession, manual -- ALL FIVE have 0 edges of 39,358 (0.000%). Every edge in the house's idea graph is positional or textual; not one records an influence a mind formed. `hops` and `formed_by` carry only the two synthetic writers (eye-indexer, harness).

### touch.v1 (shipped 2026-10-02, W0.2). Redis stream `events:raw` on 127.0.0.1:16379 db0, kind='touch'; the whole record is one JSON blob in a single stream field named `data`.

- volume: 2,477 touch records in the ring, first 2026-10-02 04:16, last live during this run. Command: r.xrange('events:raw') filtered on kind=='touch'. Cross-check: `py agent_cli.py context --stats` reports 818 touches in the 24h window at 34.08/h, SESSION COVERAGE 906/979 = 92.5%, TARGETS PER TOUCH mean 0.5893 / p50 0.0 / p95 2.0 / max 9.0, COULD NOT SEE IN 11.0%, TRUNCATED AT CAP 0.0%, RING RETENTION 1345.255h, TOUCHES DROPPED 74.
- identifier: session_id (nonempty on 2,438/2,438 = 100% of touch rows inside events:raw) plus detail.targets[].key. The session_id is stable; the TARGET KEY is mutable and bifurcated -- 995 of 1,011 targets carry a bare repo-relative path ('core/coord/target.py'), 16 carry the W0.1 form ('work:E:-AI-Setup:core/events/touch.py'), the work: prefix appearing only between 2026-10-02 00:17 and 00:54. 299 distinct keys, 53.8% seen exactly once, 77 targets have an EMPTY key string.  (key stability: **mutable**)
- index: NONE. A Redis stream is indexed by entry id (time) only; there is no secondary index on session_id, kind, agent_id or target. Every question of the form 'what did session X touch' is a full XRANGE of the stream plus a JSON parse of every row in Python. REACH DETAIL: `context --stats` reads it; nothing pushes a touch, or anything derived from one, into a seat's context.
- reach: **pull-only**
- underused fields: detail.targets nonempty on 681 of 2,438 rows = 6.7% of events:raw: 1,454 touches (58.7%) recorded targets==[] (read, touched nothing) and 329 (13.3%) recorded targets==None (unknowable). `work` is set on 16 of 969 targets = 1.7%, so the worktree axis W0.1 exists for is effectively unpopulated. harness ('claude-code') and session_source ('payload') are constant across 100% of rows and carry zero bits. Coverage is ONE agent (agent_id='claude', 2,477/2,477) and ONE distinct session_id.

### The raw event firehose: Redis stream `events:raw` db0, ring maxlen 100,000 (core/events/event_log.py:44), with per-agent mirrors events:{agent}:raw at maxlen 10,000.

- volume: 10,290 entries, span 2026-08-14 01:52 -> live (50.4 days), 37 distinct `kind` values, 1,665 rows added in the last 24h -> the 100k ring fills in ~54 days. Per-agent: claude 5,537, deepseek 2,034, kimi 1,513, sol 487, dsh_agent 134, codex 81, unknown 73, grok 69, codex_root 62, mirror 57, astra 36. Commands: XLEN events:raw; r.xinfo_stream('events:raw'); r.scan over events:*. DATA LOSS: xinfo_stream reports entries-added=10,290 and max-deleted-entry-id=0-0, i.e. the stream has NEVER been trimmed and has only ever received 10,290 entries -- yet its own time index reaches back to 2026-07-16, a month before the stream's oldest entry. The canonical firehose was recreated/lost around 2026-08-14. CERTAIN that it happened; cause NOT MEASURED.
- identifier: session_id + agent_id + refs (the followable event:<stream>:<id> pointer); stable where present  (key stability: **stable**)
- index: `events:raw:tindex`, a zset of event_id -> at-epoch (core/events/event_index.py), 13,338 members, oldest score 2026-07-16, newest live; plus events:raw:byid:* (13,333 keys) and events:raw:byref:* (3,709 keys). DIVERGENCE, measured by set difference between r.xrange ids and r.zrange('events:raw:tindex',0,-1): 3,555 of 13,338 index entries = 26.7% point at events no longer in the stream, and 438 of 10,221 stream entries = 4.3% are absent from the index. The only O(log n) path into the firehose is both over- and under-complete. REACH DETAIL: read by the `events` verb only.
- reach: **pull-only**
- underused fields: session_id nonempty on 2,845 of 10,137 rows = 28.1% all-time, up from the 10-01 doc's 0.0% -- but it comes from exactly THREE kinds: touch 2,438/2,438 (100%), session_signals 89/89 (100%), phase 318/518 (61.4%). Every other kind is 0.0%, including boot (1,437 rows), fail (1,299), learning (713), expectation_settled_answered (402), decision (393), file_edit (202), handoff (145), turn_metrics (1,553), flip (40). The `track` field is present on 100% of rows and nonempty on 0 of 10,137 -- a completely dead axis. `refs` 28.1%.

### The injection ledger -- the record of the house's ONE push path. Durable mirror: Redis stream `recall:surface`, maxlen 6,000 (core/recall/at_action.py:237-238). Observability twin: per-session files C:\Users\L5\AppData\Local\Temp\akashic_recall\inj\<session_id>.jsonl, pruned at 7 days by prune_state().

- volume: Redis: 6,004 entries, AT CAP; entries-added=9,896, so 3,892 injections (39.3% of everything ever pushed) have already been evicted; span 2026-08-26 01:21 -> live, 38.4 days. Files: 10 files, 1,687 rows, 2026-09-04 -> 2026-10-03, 961 KB. Commands: XLEN/XINFO recall:surface; wc -l over inj/*.jsonl. Push cost: `py agent_cli.py injections` reports 91 injections / ~29,290 tokens in the last 24h; `py agent_cli.py stats` reports 68 injections / ~20,547 tokens for the same stated window -- the two verbs disagree and I did not reconcile them.
- identifier: Redis `sid` nonempty on 6,001/6,001 = 100%, 92 distinct (STABLE); target `t` nonempty 96.2% but MUTABLE -- 5,319 distinct values, the c: form storing the entire lowercased command text. The file twin has NO session field at all and is keyed only by filename.  (key stability: **mutable**)
- index: none beyond stream time order; the file twin has none at all. REACH DETAIL: this plane IS the record of the one push (recall-at PreToolUse -> seat context) rather than a plane that is itself pushed; it is read back only by the `injections` and `stats` verbs.
- reach: **pull-only**
- underused fields: the file twin's lack of a session_id field means a merged read of the two twins silently loses the session on 1,687 rows unless the filename is carried by hand. `s` (the surfaced lesson sources) is the only edge from this plane to the lesson corpus.

### The stage / resolved-outcome ledger. Durable mirror: Redis stream `recall:outcome`, maxlen 20,000 (core/recall/at_action.py:248-249). Twin: C:\Users\L5\AppData\Local\Temp\akashic_recall\stage\<session_id>.jsonl.

- volume: Redis: 20,004 entries, AT CAP; entries-added=47,289, so 27,285 resolved outcomes (57.7% of everything ever recorded) have ALREADY been evicted; span only 18.5 days (oldest 2026-09-14). Files: 15 files, 27,476 rows, 2026-08-24 -> 2026-10-03, 16,396 KB, largest single file 9,985,290 bytes. RETENTION: _STAGE_DIR is absent from prune_state()'s directory list (core/recall/at_action.py:476-477, which names _SEEN_DIR, _IMP_DIR, _OUTCOME_DIR, _TXW_DIR, _PAYLOAD_DIR, _NUDGE_DIR, _FLIP_DIR, _INJ_DIR) -- the stage files are never pruned and are the only surviving copy of the 27,285 rows Redis dropped. Commands: XLEN/XINFO recall:outcome; a py json scan over stage/*.jsonl.
- identifier: Redis `sid` 20,002/20,002 = 100% (20 distinct, STABLE); target `t` 100% present and catastrophically MUTABLE -- 17,733 distinct keys over 20,000 rows, 17,190 (96.9%) seen exactly once, mean key length 496 chars, p50 263, p95 1,797, max 34,366, with 17,307 distinct c: command keys against 426 p: path keys. The file twin carries at/t/ok/surfaced/s/flipped/credited/agent and NO sid field -- session lives only in the filename.  (key stability: **mutable**)
- index: none. The target axis is effectively a hash of raw command text: it cannot aggregate, cannot survive an argument change, and cannot be matched to a path. REACH DETAIL: nothing reads it into a seat; prevention.py and `stats` read it on demand.
- reach: **dark**
- underused fields: `s`, the surfaced-lesson list that is the ONLY link from an outcome back to what recall did, is nonempty on 2,772 of 20,002 Redis rows (13.9%) and 3,384 of 27,476 file rows (12.3%). 87% of resolved outcomes can neither credit nor discredit anything. No row in either twin carries an `outcome` label field at all (a py scan of o.get('outcome') over all 27,476 file rows returned None 27,476 times).

### The recall CALL-outcome ledger (R2 slice 0, the denominator for 'did recall fire'). Single file C:\Users\L5\AppData\Local\Temp\akashic_recall\outcome\recall_outcomes.jsonl -- a 4,000,000-byte ring that drops its oldest half on overflow (_OUTCOME_MAX_BYTES, core/recall/at_action.py:91).

- volume: 15,411 rows, 3,697,836 bytes = 92.4% of the ring full (the next overflow silently deletes ~7,700 rows), span 2026-09-17 03:23 -> 2026-10-03 10:52 = 16.3 days. Commands: wc -l; a py json field scan. Fields: at / outcome / reason / q / n_items / agent / query_shape / excl_kind / excl_counts.
- identifier: NONE -- and this is the finding. The rows carry no session id, no target and no event id. The only handles are a float timestamp and an agent string.  (key stability: **none**)
- index: none. REACH DETAIL: read only by `py agent_cli.py stats`.
- reach: **dark**
- underused fields: `agent` nonempty on 13,581/15,411 = 88.1% (1,830 rows cannot even be attributed to a seat); `reason` 75.0%; `excl_kind` and `excl_counts` 48.2%. This is the one plane in the whole census that can be joined to nothing at all -- and it is the plane holding the silence data the funnel's honesty depends on.

### Impressions and flips -- the contrastive FAIL->SUCCESS credit path. C:\Users\L5\AppData\Local\Temp\akashic_recall\imp\<session>.jsonl and flips\<session>.jsonl. Both pruned at 7 days by prune_state().

- volume: imp: 10 files, 1,598 rows, 861 KB, fields exactly {t, s}. flips: 1 file, 1 row, 176 bytes, written 2026-10-02. Cross-check from `py agent_cli.py stats`: 131 helped credits all-time against 24,614 surfaced impressions; last 24h flips=0, credited=0, corpus-gap=0. Commands: ls + wc -l over imp/ and flips/; py agent_cli.py stats.
- identifier: filename session id (stable) + target `t`, which is the same p:/c: key as the stage plane and inherits its 96.9%-seen-once problem  (key stability: **mutable**)
- index: none. REACH DETAIL: read only by the JIT learn nudge and the wrap-time candidate-lesson draft, never surfaced to a seat as knowledge.
- reach: **dark**
- underused fields: the entire flip plane is ONE surviving row. An impression row carries only {t, s}: no timestamp, no agent, no altitude, so a surviving impression cannot be dated or attributed once its session file is pruned.

### Session signals (core/renew/session_signals.py, folded by scripts/hooks/claude_sessionend.py). Durable: `events:raw` kind='session_signals'. Scratch: akashic_recall\session_signals\ (NOT in prune_state's list).

- volume: 89 events in Redis, 2026-08-10 -> 2026-10-02; 50 distinct session ids. The file directory holds exactly 1 file of 13 bytes. Commands: r.xrange('events:raw') filtered on kind; ls -la on the directory.
- identifier: session_id, nonempty on 89/89 = 100%  (key stability: **stable**)
- index: none. REACH DETAIL: no verb reads this plane back into a seat.
- reach: **dark**
- underused fields: 89 folded sessions over 54 days against 1,673 sessions in the Eye = 5.3% session coverage. The signal x label correlation dataset this sensor exists to accrue has 89 rows and, per the house's own lesson renew_stranda_health_signals, no durable ground-truth label to correlate against.

### Handoff signals: Redis stream `agent:events` (the CLOSED 6-species coordination firehose) plus `agent:claude:events`.

- volume: agent:events 145 entries, span 2026-08-14 01:51 -> 2026-10-02 08:15 (49.3 days); agent:claude:events 113. All 145 rows are signal_type='handoff'. Commands: XLEN/XINFO agent:events; a py parse of the data blob.
- identifier: session_id 145/145 = 100%, plus agent_id and target_agent  (key stability: **stable**)
- index: none. REACH DETAIL: this is the only non-lesson plane that is pushed -- boot surfaces the latest handoff addressed to you, and only the latest, so the other 144 rows are unreachable without a pull verb. Hence 'partial'.
- reach: **partial**
- underused fields: `blockers` nonempty on 13 of 145 = 9.0%; `context` collapses to a single free-text `context.note` on 144 of 145, so the structured coordination schema is in practice one prose field. Five of the six declared species (action, decision, blocker, completion, learning) have zero rows on this stream.

### The dsh (Rill) door capture log. A single flat file C:\Users\L5\AppData\Local\Temp\akashic_recall\payloads_dsh\captures.jsonl. `payloads_dsh` is NOT in prune_state()'s directory list, so nothing has ever deleted from it.

- volume: 2,462,630 rows, 300,193,359 bytes (293 MB) -- by volume the largest store in this census, 7.4x the row count of the entire Eye. Span 2026-08-24 -> 2026-10-02 (39.4 days). Command: a line-by-line json scan in py (open(p,'rb') + json.loads per line) counting rows, kinds and keys. Kind breakdown: session-event 2,459,790 / post-execute 2,308 / wake-splice-observed 293 / wake-poke-failed 150 / door-ready 33 / wake-woke 30 / wake-poke 12 / door-exit 4 / door-respawn 4 / five more under 3 each.
- identifier: `sid` nonempty on 2,460,276 rows = 99.9% (sampled form 'session-c83f6c44-...')  (key stability: **stable**)
- index: NONE -- 293 MB of unindexed flat JSONL on a temp volume. REACH DETAIL: no verb in the repository reads this file.
- reach: **dark**
- underused fields: 2,459,790 of 2,462,630 rows (99.885%) are kind='session-event' carrying only {at, kind, type, sid} -- pure volume with no payload. `tool` is present on 2,308 rows = 0.09%, `argKeys` and `isError` likewise. The informative sliver is those 2,308 post-execute records: the dsh seat's complete tool-execution history, 17x larger than that seat's entire presence in the house firehose (events:dsh_agent:raw holds 134 rows).

### Hook-owned per-session scratch, all under C:\Users\L5\AppData\Local\Temp\akashic_recall\: seen/ (anti-repeat sets), txw/ (transcript-failure watermarks), payloads/ (captured payload samples), nudge/ (learn-nudge rate limit), payloads_cursor/. All except payloads_cursor are pruned at 7 days by prune_state(), which runs at every SessionStart (scripts/hooks/claude_sessionstart.py:64, agent_cli.py:340).

- volume: seen: 11 files / 3,471 lines / 274 KB. txw: 6 files / 342 KB (largest 225,512 bytes). payloads: 200 files / 960 KB. nudge: 1 file / 0 lines. payloads_cursor: 1 file / 1 KB. Also lesson_items.json, the warm recall cache, 1,436,634 bytes, rewritten during this run. Commands: ls -la and wc -l per directory.
- identifier: filename = session id (seen/, txw/) or <epoch_ms>_<Tool>_<pid> (payloads/). The seen/txw session ids are stable; the payload filenames carry a pid, which is mutable and meaningless across reboots -- hence 'mutable' for the plane as a whole.  (key stability: **mutable**)
- index: none. REACH DETAIL: this is the hook's own working memory, read by no verb and surfaced to no seat.
- reach: **dark**
- underused fields: the payload samples are the only place a tool call's actual arguments are retained, and they are named by pid rather than by session or target, so 200 files cannot be grouped by what they were about. nudge/ holds 0 lines.

**Joins:**
- touch.v1 <-> the Eye via the harness session uuid: KEY COMPATIBLE, CURRENTLY EMPTY. The namespaces are proven identical -- recall:surface's 92 sids intersect eye.db's 1,673 sessions at 90 (97.8%), and the file planes intersect it at 77-87% (inj 8/10, stage 13/15, imp 8/10, seen 9/11, txw 5/6). But touch holds exactly 1 distinct session id and the Eye has not ingested since 2026-10-01 09:17, so the measured overlap today is 0 of 1. A staleness failure, not a schema failure: fixed by running ingest, not by redesign.
- touch.v1 <-> the recall planes via target: BLOCKED, AND THIS IS THE HEADLINE. 0 of 365 normalised touch target keys appear among recall:outcome's 17,733 target keys (intersection computed raw and again after stripping the p:/c: prefix and case-folding). Two vocabularies: touch emits `work:E:-AI-Setup:core/events/touch.py` or, since 2026-10-02 00:55, bare `core/coord/target.py`; recall emits `p:e:\ai-setup\core\events\touch.py` or `c:<entire lowercased command line>`. normalize_target() in core/recall/at_action.py:931 and context.target.v1 in core/coord/target.py are two independent normalisers and nothing reconciles them.
- recall:surface <-> recall:outcome via target `t`: WORKS -- 2,249 shared keys. The only target-keyed join in the house that currently resolves, and it joins 'what was pushed' to 'what happened next'. Both sides are mutable keys, so it holds only for byte-identical command repeats; 96.9% of stage keys are seen exactly once, so the join covers a small minority of rows.
- recall_outcomes.jsonl <-> ANY other plane: BLOCKED, STRUCTURALLY. 15,411 rows carrying neither a session id nor a target nor an event id. The plane that holds the silence denominator -- fired vs floor_silent vs excluded_silent vs empty_query -- cannot be attached to the session, the action, the file or the lesson it concerns. One added field would fix it.
- The file twins <-> their Redis twins via session: WORKS, BY FILENAME ONLY. inj/, stage/, imp/, flips/, seen/, txw/ are all keyed by session id in the filename and none carries a session field inside the rows. Any merge that reads rows without carrying the filename silently loses the session on 1,687 + 27,476 + 1,598 rows.
- The non-touch kinds of events:raw <-> any session-scoped plane: BLOCKED. boot (1,437), fail (1,299), learning (713), expectation_settled_answered (402), decision (393), file_edit (202), handoff (145), turn_metrics (1,553) and flip (40) carry session_id at 0.0%. W0.2 forwarded the session id into exactly three kinds; `context --stats` shows the same gap inside its own 24h window (boot 0/23, boot_unverified 0/22, fail 0/18, learning 0/4, episode_suggestion 0/4, expectation_dead 0/2).
- events:raw <-> its own time index via event id: PARTIALLY BROKEN. 3,555 of 13,338 index entries (26.7%) are dangling and 438 of 10,221 stream entries (4.3%) are unindexed. xinfo_stream reports entries-added=10,290 with max-deleted-entry-id=0-0, so the stream was recreated around 2026-08-14 while the index survived -- 13,333 payloads still sit in events:raw:byid:* for events the firehose no longer has.
- The connectome <-> fences, lessons, recall firings or supersessions: IMPOSSIBLE TODAY. All five mind-formed formed_via values (fence, recall-firing, fan, supersession, manual) have 0 edges of 39,358. There is no writer, so there is nothing to join.
- agent:events handoffs <-> the Eye via session_id: PLAUSIBLE (both 100% session-keyed, same uuid namespace) but NOT MEASURED this run.
- payloads_dsh/captures.jsonl <-> anything via `sid`: PLAUSIBLE -- 99.9% of 2.46M rows carry a sid -- but the sampled form is 'session-c83f6c44-...' (a prefixed variant of the bare uuid the other planes use), and whether anything strips that prefix was NOT MEASURED.

**Biggest waste:** By value: the stage ledger. 27,476 resolved action outcomes in 15 never-pruned files totalling 16,396 KB, plus a 20,004-row Redis twin that has already evicted 27,285 of the 47,289 rows it ever received. It is the only record in the house of what actually happened after an action -- ok, flipped, credited, per target, per session -- and it is the dataset prevention, promotion-to-gates and the S2 adjudicator all depend on. Nothing reads it into a seat, it has no index, its `s` field (the only edge back to the lesson that was surfaced) is populated on 12.3% of rows, and its target key does not join to touch at all (0 of 365). By raw volume: payloads_dsh/captures.jsonl, 2,462,630 rows and 300,193,359 bytes of unindexed JSONL on a temp volume that no verb in the repository reads -- of which the genuinely valuable part is 2,308 post-execute records holding the dsh seat's entire tool history, 17x what that seat has in the house firehose (134 rows).

**Not measured:** p95 hook latency for touch.v1 -- `context --stats` names it UNCHECKABLE itself: the PostToolUse payload carries no duration and touch.v1 stamps none.; anchor_resolve_cost_ms -- `context --stats` names it UNCHECKABLE: the context door (W0.6) does not exist, so there is no call to time.; The CAUSE of the events:raw / tindex divergence. That the firehose was recreated around 2026-08-14 is CERTAIN (entries-added=10,290 equals its current length while the index reaches to 2026-07-16). Whether it was a power pull (the house took two, 2026-09-11 and 2026-09-24), an explicit XTRIM, or an RDB reload is SPECULATIVE. Redis runs RDB-only (appendonly=no, save '3600 1 300 100 60 10000', 7,659 changes unsaved at read time), so up to 60s of writes are lossy on a hard kill -- consistent, not proof.; The disagreement between `py agent_cli.py injections` (91 injections, ~29,290 tokens, last 24h) and `py agent_cli.py stats` (68 injections, ~20,547 tokens, last 24h), run ~10 minutes apart. Sliding windows explain part of it; I did not reconcile the two readers.; db13 (1,229 keys) and db15 (1,104 keys) -- not opened. db15 is the test db and the brief forbade touching it.; Whether touch records from seats other than claude were ever written and lost. events:raw has never trimmed (max-deleted-entry-id=0-0, 10,290 < maxlen 100,000), so LIKELY none exist, but a stream recreation would hide them and I did not check the dsh/kimi/sol hook sources for a touch call site.; recall-bench was not RUN. The eval set exists at tests/fixtures/recall_eval/moments.json with 25 moments seeded against a declared target of 40 (16 of the 25 carry a `measured` field), so W0.3's instrument is built and 62.5% populated, but this run produced no recall@5 / precision@3 number.; The lesson corpus itself (1,562 lessons, 1,453 tracked by recall, per `stats`) -- out of this plane. The 10-01 doc's three-domain-labels and 39-of-1,526-with-files_affected figures were NOT re-measured.; The manuals shelf, library atoms, fences, notes, the authorship ledger and git -- other planes, outside this brief.; Any retention policy for eye.db. No prune caller was found and none is declared; the file is 313 MB, untracked (state/* is gitignored, git ls-files state/eye is empty), and I found no backup. That it is unbacked is LIKELY, not CERTAIN -- I did not search backups/ exhaustively.; Whether `phase`'s 61.4% all-time session_id rate is a rollout boundary. In the 24h window `context --stats` shows phase at 88/88 = 100%, so the all-time 318/518 LIKELY reflects records written before the forwarding landed, but I did not split the series by timestamp.

---

## code, provenance and the governance ledgers — git history, state/authorship/seats.jsonl, docs/MODULE_INDEX.md, core/fleet/seat_model.py, state/coord/tasks.json, state/coord/forecasts.jsonl, docs/WISHLIST.md, state/coord/suite_baseline.json (measured at E:/AI-Setup, master @d13fc3c7, 2026-10-03)

**CERTAIN: git carries zero seat provenance — all 2,847 master commits have author AND committer `61030820+balanced7@users.noreply.github.com` (`git log HEAD --format=%ae | sort | uniq -c` returns one line, 2847). The authorship ledger is the only plane that answers "which seat built this"; it covers 813 of 2,847 master commits (28.6%), its rewrite-stable key beats the sha by 16.7 points (93.8% unique / 0.0% ambiguous vs 77.1% exact sha), and it has exactly one consumer in the whole repository: its own build script. Same shape, second number: 81 of 172 done tasks (47.1%) carry a shipping receipt whose sha names no commit on master.**

### git commit history — the object DB at E:/AI-Setup/.git (the repo IS a git worktree despite the harness env saying otherwise; `git rev-parse --is-inside-work-tree` → true)

- volume: 2,847 commits on master, 5,701 across all refs, 20 local branches + 1 remote (beta). 4,397 tracked files; 1,643 tracked .py; 1,916 tracked .md. Range 2026-04-15 → 2026-10-03. Cmds: `git rev-list --count HEAD`; `git rev-list --count --all`; `git ls-files | wc -l`; `git ls-files '*.py' | wc -l`
- identifier: commit sha (40 hex), plus the SUBJECT LINE as a de-facto second identifier. The sha is mutable and provably so: `py agent_cli.py sha --maps` lists FIVE rewrite maps totalling 7,969 remaps (2026-07-23: 1,125 remaps/1 dropped; 2026-08-12: 1,979; 2026-09-26-authorship: 4,748; 2026-09-26-cited-gap: 1; 2026-09-26-unmapped-residue: 116) and two of the five are marked [reconstructed] — reverse-engineered after the fact, not recorded. The subject line by contrast is STABLE: the authorship ledger's (author-date, subject) key shows 0 drift over 935 rows (`py scripts/authorship_ledger.py verify` → 'stable key disagrees: 0'). CERTAIN.  (key stability: **mutable**)
- index: git's own commit graph plus `--grep`/`-S`. NO project-level index. The one cross-plane edge set that exists — 908 master commit subjects carrying a T### id — is reachable only by `git log --grep`.
- reach: **partial**
- underused fields: the author/committer axis is 100% dead as attribution: 2,847/2,847 master commits read `balanced7` on BOTH fields. This is deliberate (Daniel's 2026-09-26 ruling, implemented by T410's rewrite), but it means git's only built-in provenance field now carries 0 bits of seat information and its replacement plane covers 28.6% of it. Boot pushes exactly one commit (the latest done task's 8-char prefix, agent_cli.py ~l.2135); nothing else from git reaches a seat.

### authorship ledger — E:/AI-Setup/state/authorship/seats.jsonl (JSONL, 360,304 bytes, written by scripts/authorship_ledger.py)

- volume: 935 rows, 0 parse failures, spanning 2026-04-15T05:21:48 → 2026-10-03T14:29:31. Seats: claude 548, operator-unconfigured-git 164, sol 98, dsh_agent 88, deepseek 23, kimi 8, codex_root 4, sunshine 2. Cmd: `wc -l state/authorship/seats.jsonl` plus a py json pass over every line.
- identifier: DELIBERATELY DUAL — `sha` (mortal) and the stable key `(at, subject)` composed from two fields a rewrite does not touch. THIS WAS THE TASK'S SPECIFIC QUESTION; joined against master's 2,847 commits: sha EXACT 721/935 = 77.1%; sha by PREFIX 837/935 = 89.5%; stable key UNIQUE 877/935 = 93.8%, MISSING 58 = 6.2%, AMBIGUOUS 0 = 0.0%. CERTAIN — the stable key beats the sha by 16.7 points and never collides on master. Caveat: single-branch only — matched against --all it is ambiguous for 727/935 (77.8%) because backup branches duplicate (at,subject). Separate CERTAIN defect: the ledger stores two sha widths (813 rows at 40 chars, 122 at 12 chars — exactly the rows carrying `seat_source`) while `cmd_verify` builds its lookup from full `%H`, so verify reports all 122 as 'SHA names no commit here' and advises a rekey that is not needed. The verifier's own join is broken by the ledger's own abbreviation.  (key stability: **stable**)
- index: NONE. 935-line linear scan on every read; `seat_for()` does a Python startswith over the whole list.
- reach: **dark**
- underused fields: seat_source 122/935 = 13.0%; key_says 11 = 1.2%; map_says 11 = 1.2%; key_refreshed 1 = 0.1%; seat_name/seat_email/rekey 813 = 87.0%; was_sha 772 = 82.6%. Coverage is the real gap: 813 of 2,847 master commits (28.6%) have a row, so 2,034 master commits (71.4%) have seat attribution in NEITHER plane. On reach: a repo-wide grep for `authorship_ledger|seats.jsonl` in .py finds ONE file — scripts/authorship_ledger.py itself (plus a prose mention at core/comm/seat_identity.py l.242 and 9 fence/research docs). No agent_cli verb, not in boot, not in recall-at; core/coord/scene.py lists `authorship` as a PLANE and hard-codes it UNCHECKABLE.

### module index — E:/AI-Setup/docs/MODULE_INDEX.md (auto-generated from each module's line-1 docstring by scripts/generators/gen_arch_index.py)

- volume: 393 lines, 332 modules across 26 sections. Cmd: `wc -l docs/MODULE_INDEX.md` plus a parse of the `## <dir>/ (N modules)` / `- \`file.py\` — docstring` grammar.
- identifier: file path relative to repo root — mutable: a rename drops a row silently. Bounded in practice, because the generator rebuilds from the tree and scripts/checkers/check_comprehensibility.py has a staleness gate; but any stored reference TO an index line dies on rename.  (key stability: **mutable**)
- index: it IS an index, and nothing indexes it. Grep only. One structured consumer: core/coord/capability_search.py DEFAULT_FILES = ('docs/MODULE_INDEX.md',), an LLM-over-the-file 'does this already exist?' verb. core/recall/lookback.py lists it in REFERENCE_DOCS.
- reach: **pull-only**
- underused fields: FRESH, not stale — 0 of 332 listed modules are missing from disk, and `git rev-list --count b44be4e..HEAD -- '*.py'` = 0, so nothing has changed under it since its last regen (today 03:37). The gap is SCOPE: core/ 240/245 non-init .py = 98.0%; scripts/ 84/148 = 56.8%; root 8/8; tests/ 0/797; research/ 0/227; arsenal/ 0/53; agent/ 0/34. Whole repo 332/1,643 tracked .py = 20.2%. The 797 test modules — where this house keeps its executable specifications — are 0% indexed. Never pushed at boot or by recall-at; the pull is a verb a seat must know to choose.

### seat_model — core/fleet/seat_model.py (200 lines); pin half = state/coord/seat_model.json, self-report half = Redis `seat:model:{agent}:{session}` with a 900 s TTL

- volume: ZERO ROWS IN BOTH HALVES. `ls state/coord/seat_model.json` → No such file or directory. A Redis SCAN for `seat:model:*` on akashic-redis localhost:16379 → 0 keys. CERTAIN.
- identifier: (agent, session) for the self-report, agent for the pin — nothing is stored, so nothing has a key  (key stability: **none**)
- index: none
- reach: **dark**
- underused fields: the whole plane. The 2026-10-01 map filed this as primitive #11, 'model provenance on lessons — plane exists, unjoined'. CERTAIN correction: it is not unjoined, it is EMPTY. A mid-session model swap currently launders into the corpus with nothing anywhere recording it, and the join designed to stop that has no left-hand side. Grep for `seat_model` across agent_cli.py, core/recall/at_action.py, core/context/*.py and agent/harness/ returns no hits.

### task ledger — E:/AI-Setup/state/coord/tasks.json (786,774 bytes; a dict {seq, rev, tasks[]} with a .lock sibling; read through core/coord/task_ledger.state_view())

- volume: 424 tasks, seq 424, rev 458, ids T001–T424, 0 duplicate ids. status: done 172, proposed 114, abandoned 52, approved 39, parked 18, claimed 15, verifying 12, in_progress 2. Cmd: `py -c` json load plus Counter.
- identifier: T-id (T###) — the strongest identifier on this plane: 424 ids, zero duplicates, never reused, untouched by all three history rewrites. CERTAIN.  (key stability: **stable**)
- index: none persistent. state_view() buckets the whole 787 KB list in-process on every call.
- reach: **pushed**
- underused fields: desc 424 exist / 0 populated = 0.0%; self_verified 176 exist / 0 populated = 0.0%; deps 13 = 3.1%; reviewed_by 177 exist / 26 populated = 6.1%; files 95 = 22.4% (106 distinct paths, 87 = 82.1% still in tree); acceptance 110 = 25.9%; commit 191 = 45.0%; verified_by 191 = 45.0%. The `commit` field is the dead join: length histogram {7 chars: 128, 4 chars: 30, 8 chars: 33} — THIRTY receipts are four hex characters. On reach, a CERTAIN correction to the 2026-10-01 map which listed this among the dark planes: it is the one governance ledger that reaches a seat involuntarily — the boot header prints counts (done/active/next/blocked/proposed with a STALE flag), the top 3 active tasks with id+title+status+owner and the top 2 next; also consumed by agent/harness/delta.py, agent/harness/hooks/claude_pretooluse.py and core/context/world_snapshot.py.

### forecast registry — E:/AI-Setup/state/coord/forecasts.jsonl (append-only, written by core/coord/forecast_registry.py, door = `py agent_cli.py forecast`)

- volume: 29 records: 17 `register`, 12 `score`. 17 distinct registered ids; 12 scored; 6 registered and never scored, of which 4 are past their horizon_ts. Verdicts: hit 5, miss 4, partial 2, voided 1. Last write 2026-10-02T06:31. Cmd: `wc -l state/coord/forecasts.jsonl` plus a py pass keyed on `kind`.
- identifier: a writer-chosen slug — but register rows call it `id` and score rows call it `forecast_id`. TWO FIELD NAMES FOR ONE KEY IN ONE FILE. The slug itself is stable (chosen, not derived), yet one of the 12 score rows (`corpus-is-one-directional-2026-08-26`) has no register row at all — an orphan verdict. CERTAIN.  (key stability: **stable**)
- index: none. 29-line scan.
- reach: **pull-only**
- underused fields: task_ref 13/17 = 76.5% populated, and the populated values mix three id spaces as free text: T374/T375/T376/T381/T382/T392/T399, plus 'W0.3', plus 'adjudication-loop cycle 1'. There is no typed foreign key, so a forecast cannot be walked to from its task; 4 of 17 registers carry no task_ref at all. registered_by is claude 16 / deepseek 1 — a one-seat organ, against a standing ritual of 'register at EVERY gate'. Reached only by `py agent_cli.py forecast --calibration`; not in boot, not in recall-at.

### docs/WISHLIST.md — the standing ergonomics ledger (markdown; written through `py agent_cli.py wish` / `wish-curate` under docs/WISHLIST.md.lock, which rewrites the whole file)

- volume: 1,796 lines, 263 wish items: open [ ] 227, folded [x] 36, declined [~] 0. 45 items name a T-number fold. Last touched 2026-10-03 10:06. Cmd: regex count of `^- \[[ x~]\]` lines plus a status Counter.
- identifier: W-id (W##) — AND IT IS NOT UNIQUE, which is a hard defect. 263 items carry a leading W-id but only 248 are distinct: fifteen ids are each used twice (W00, W57, W58, W59, W60, W61, W62, W63, W64, W65, W66, W67, W68, W69, W211). Two unrelated wishes both answer to 'W211'. Any W-keyed join returns the wrong row for ~5.7% of items, silently. CERTAIN.  (key stability: **mutable**)
- index: none. Markdown grep. The write path parses the file by anchor heading and REFUSES if the '## Folded' anchor moves (agent_cli.py l.2480), so the structure is load-bearing and unvalidated anywhere else.
- reach: **pull-only**
- underused fields: the declared format is `- [ ] W## (date, seat) — the wish`, and it is not being followed: only 5 of 263 items (1.9%) carry a parseable `(20YY-MM-DD` date and 0 yielded a seat to the documented pattern (most use a bare `(09-25, deepseek/Heimdall)` short-date form instead). 'When was this friction felt' and 'who felt it' are present in prose and extractable by nothing. Declined = 0 of 263. 134 distinct W-ids DO appear in master commit subjects (`git log HEAD --format=%s | grep -oE '\bW[0-9]{2,3}\b' | sort -u | wc -l`), so the same untyped subject-line convention that carries T-ids also carries W-ids.

### suite baseline — E:/AI-Setup/state/coord/suite_baseline.json (20,159 bytes; read through core/coord/suite_baseline.py)

- volume: 100 recorded known-failure nodes across 34 distinct test files, written 2026-09-09T00:25:48 by seat claude. Top files: test_captions_gate_red.py 16, test_recall_dimension_recurrence_red.py 16, test_web_door_contract_red.py 11. All 34 named test files still exist on disk. Cmds: `py -c` json load; `py agent_cli.py suite-baseline claude --show`.
- identifier: the anchor commit sha `5ba81ba6` — MUTABLE AND ALREADY DEAD: it resolves against `git rev-list --all` but NOT against `git rev-list HEAD`. The 2026-09-26 rewrite carried it off master, so the ratchet's anchor no longer names a commit on the branch it gates. Node ids are the stable half: 34/34 files survive and a node id only dies on a test rename. CERTAIN.  (key stability: **mutable**)
- index: none, and none needed at this size — a flat list of 100 nodes.
- reach: **pushed**
- underused fields: `lane` is 96/100 empty = 4.0% populated (T093 ×3, T275 ×1), so 'which slice owns this known failure' is unanswerable for 96 of 100. The 100 failures are a 590.6-hour-old claim, NOT re-measured this run (pytest was out of scope by instruction). Best-behaved organ on this plane: `render_boot_line()` puts one line in every boot header and that line confesses its own age and rot — '# suite baseline @5ba81ba (590.6h old, by claude): 100 known failure(s) -- 1 classified lane(s) since closed (T275): re-run advised'. Deadest key, most honest reach.

### SUPPORTING PLANE, measured because it is the designed join — the event/touch stream on akashic-redis localhost:16379 (`events:raw` stream, `events:raw:byid:*` strings, `events:raw:byref:*` index)

- volume: events:raw stream = 10,199 entries; 13,316 byid keys; 3,707 distinct byref keys. Kinds: touch 2,494, turn_metrics 1,553, boot 1,437, fail 1,301, learning 713, phase 518, file_edit 202. Agents: claude 5,446, deepseek 2,034, kimi 1,513, sol 487. Cmds: Redis XRANGE + SCAN; `py agent_cli.py context --stats --hours 168`.
- identifier: a context.target.v1 anchor string, used as the byref key suffix — and the namespace holds EIGHT ref schemes at once: plain path 1,183, `learn:` 954, `mem:` 555, `bifrost:` 551, `git:` 208, `file:` 113, `beat:` 93, `work:<tree>:` 13, url 2. `learn:` is stable and resolves perfectly (954/954). `git:` is a mutable sha and is dead (see joins). Plain path vs `file:` vs `work:` are three spellings of one thing — exactly the problem W0.1 exists to fix, still live in the index: 9 canonical paths are reached by more than one raw spelling. CERTAIN.  (key stability: **mutable**)
- index: events:raw:byref:* IS the only real cross-plane index in this house — one Redis key per target fanning out to its events (sampled 800 keys: min 1, p50 1, p90 1, max 45).
- reach: **pushed**
- underused fields: W0.2 LANDED AND WORKS, and it moves the 2026-10-01 number: session coverage over 168 h = 2,885/3,957 = 72.9%, where the pre-W0.2 figure was 89/6,918 of a single kind and the 10-01 doc said 0.0%. By kind: touch 2,566/2,566 = 100%, phase 318/518 = 61%, and fail/boot/turn_metrics/file_edit/boot_unverified/learning all 0%. Also: 12.9% of commands are 'could not see in' (reported null, never zero), 0.0% truncated at the 32-target cap, 131 touches dropped, ring retention 1,345 h. The gaps: only 79 of 1,643 tracked .py (4.8%) have any event ref, core/ 37/271 = 13.7%; and the index is dirty — of 1,300 distinct path-shaped refs, 169 (13.0%) are live tracked files, 72 (5.5%) exist untracked, 68 (5.2%) are directory-shaped, 43 (3.3%) are shell/glob junk (`*/`, `$d/`, `(197/`, `*/node_modules/`), 36 (2.8%) are file-shaped and gone, and 912 (70.2%) are not paths at all. The target extractor is minting non-targets into the house's only cross-plane index.

**Joins:**
- task ledger <-> git via a T-id in the commit SUBJECT: WORKS, and it is the strongest join measured this run. 908 of 2,847 master commit subjects (31.9%) carry a T###; 304 distinct tokens appear and 304 of 304 (100.0%) are real task ids — zero phantoms; 304 of 424 tasks (71.7%) are reachable from at least one commit. Key is STABLE: the subject line survived all three rewrites, confirmed by the authorship ledger's (at,subject) key showing 0 drift on 935 rows. It strictly beats the typed field — 140 tasks are findable by subject grep but carry no `commit` value, versus 27 the other way. CERTAIN. Blocked only by having no index: `git log --grep` is the sole walk.
- task ledger <-> git via the typed tasks[].commit field: BLOCKED, 52.4% dead. 191 of 424 tasks carry a commit; 91 (47.6%) resolve on master. On DONE tasks it is sharper — 172 done, all 172 carry a commit, 91 resolve, so 81 done tasks (47.1%) carry a shipping receipt that names nothing on the branch. Cause: the sha is mutable and 7,969 remaps have happened across five rewrite maps. Partly recoverable — `py agent_cli.py sha --no-remote <the 100 dead>` returns TRANSLATED for 51 and UNKNOWN for 49 — but nothing in boot, scene.py or any join path calls the chase, and the boot header prints the raw dead 8-char prefix. CERTAIN that 100 fail; LIKELY (3 of 3 spot-checked with `git merge-base --is-ancestor` land on master) that the 51 translations are good.
- authorship ledger <-> git via the rewrite-stable (at, subject) key: WORKS, and nothing uses it. 877 of 935 rows (93.8%) find exactly one master commit, 58 (6.2%) find none, 0 (0.0%) are ambiguous, and `verify` reports 0 stable-key disagreements. The sha route on the same rows: 721 exact (77.1%), 837 by prefix (89.5%). CERTAIN — the designed join is built, correct, 16.7 points better than the sha, and has zero consumers; scene.py hard-codes the authorship plane as UNCHECKABLE. Caveat: single-branch only — against --all the key is ambiguous for 727 of 935 (77.8%) because backup branches duplicate (at,subject).
- lessons <-> git/authorship via a sha: BLOCKED — THE KEY DOES NOT EXIST, which corrects the 2026-10-01 doc. Measured over all 1,562 lesson hashes: typed `sha` fields 0, `commit` 0, `commit_sha` 0, `task` 0, `task_ref` 0, `session_id` 0, `organ` 0, `subsystem` 0, `door` 0. A lesson keys on `experiment_name` (writer-chosen slug, 1,534/1,562 populated, stable) and on `files_affected`. 221 lessons (14.1%) mention a hex token in free prose and 263 (16.8%) mention a T### in free prose (181 distinct T-ids), but none of it is typed, indexed or parsed by anything. So 'lessons key on mutable SHAs rather than the authorship ledger's rewrite-stable key' is wrong in letter and right in spirit: they key on neither. CERTAIN.
- lessons <-> code via files_affected: BLOCKED BY EMPTINESS, NOT BY ROT — and that inverts the assumption in the brief. 41 of 1,562 lessons (2.6%) carry at least one path (the 10-01 doc said 39 of 1,526; two days and three Wave-0 slices have not moved it). Those 41 name 103 path mentions, 79 distinct. Of the 79 distinct paths, 72 (91.1%) STILL EXIST in the tree today; 40 of the 41 lessons have at least one live path; exactly ONE lesson has all paths dead. CERTAIN — renamed paths are a rounding error here. The join does not fail because paths rot, it fails because 97.4% of the corpus never wrote one.
- events/touches <-> git via sha refs: DEAD, 0.3%. The byref index holds 293 sha-shaped refs (208 properly schemed `git:<12 hex>` plus 85 bare 8-hex written with no scheme at all). 194 (66.2%) resolve against `git rev-list --all`; exactly 1 (0.3%) resolves against `git rev-list HEAD`. The cleanest possible demonstration of the mutable-key thesis: the house's own event index points almost entirely at commits surviving only on orphan and backup branches. CERTAIN.
- events/touches <-> code via path refs: PARTIAL AND DIRTY. 1,308 path-shaped refs, 1,300 distinct after normalising `work:<tree>:` and `file:` prefixes away; only 169 (13.0%) are live tracked files. Tree coverage: 79 of 1,643 tracked .py (4.8%) have any event ref; core/ 37 of 271 (13.7%). Nine canonical paths are still reached by more than one raw spelling, so W0.1's unification is specified but not retroactive over the live index. CERTAIN.
- events/touches <-> lessons via `learn:` refs: WORKS PERFECTLY AND IS UNUSED. 954 `learn:` refs in the byref index; 954 of 954 (100.0%) name a lesson live in `learn:experiments:all`. The one cross-plane scheme in this house with flawless resolution, and no retrieval path routes through it. CERTAIN.
- lessons <-> seat_model (primitive #11, model provenance on lessons): IMPOSSIBLE, not merely unwired — the right-hand side has 0 rows. The pin file state/coord/seat_model.json does not exist and a SCAN for `seat:model:*` returns 0 keys. CERTAIN.
- forecast registry <-> task ledger via task_ref: PARTIAL. 13 of 17 registers populate it, and the values mix three id spaces as free text (T374…T399, 'W0.3', 'adjudication-loop cycle 1'). Compounding it, register rows name the key `id` and score rows name it `forecast_id`, and 1 of the 12 score rows is an orphan with no matching register. CERTAIN.
- WISHLIST <-> anything via a W-id: BLOCKED BY A NON-UNIQUE KEY. 263 items, 248 distinct ids, 15 ids used twice each (W00, W57–W69, W211). 134 distinct W-ids also appear in master commit subjects, so a W-id join would silently resolve to the wrong wish for the colliding ~5.7%. Compounding it, only 5 of 263 items (1.9%) carry a date in the documented format and 0 yield a seat, so the two axes that would disambiguate are unextractable. CERTAIN.
- module index <-> code: WORKS AND IS FRESH, but covers 20.2% of the tree. 332 modules listed, 0 of 332 missing from disk, 0 .py commits since its last regen. core/ 98.0%, scripts/ 56.8%, root 8/8, tests/ 0 of 797, research/ 0 of 227, arsenal/ 0 of 53, agent/ 0 of 34. Its one structured consumer is core/coord/capability_search.py, a pull-only verb. CERTAIN.
- SIDE FINDING on the lesson corpus's own integrity, measured in passing: 28 of the 1,562 ids in `learn:experiments:all` (1.8%) point at hashes holding ONLY `narrative_chapter` and `narrative_track` — no experiment_name, no what_tried, no recommendation. They are ghosts that every count serves as real lessons (e.g. `windows_powershell_sha256_hex_compat_2026_07_30`). The true corpus is 1,534. CERTAIN.

**Biggest waste:** The T-id-to-commit-subject edge set: 908 master commit subjects carrying a T### id, resolving to 304 distinct real task ids at 100.0% precision (304 of 304 tokens are genuine T001-T424 ids; zero phantoms), covering 304 of 424 tasks (71.7%). It is the largest, most precise, and ONLY rewrite-stable cross-plane join this house already owns — the subject line is untouched by all three history rewrites and 7,969 remaps — and the sole way to walk it is `git log --grep`. Nothing indexes it; scene.py's git resolver does not use it; the task ledger instead stores a typed `commit` sha that is 52.4% dead. Today, with no new capture path, it would answer "what shipped for T###", "which tasks touched this file" (via those commits' diffs), and — chained through the authorship ledger's 93.8%-unique stable key — "which SEAT shipped T###", which is otherwise unanswerable because git's author field reads `balanced7` on all 2,847 master commits. Runner-up, same shape, smaller: the authorship ledger itself — 935 rows, the only surviving seat provenance in the house, a verified rewrite-stable key with 0.0% ambiguity, exactly one consumer in the entire repository (its own build script), and scene.py hard-coding its plane as UNCHECKABLE.

**Not measured:** Whether the 2,034 master commits with no authorship row (71.4%) are genuinely operator work or lost seat work. The pre-rewrite author field is gone from master; it may survive on `backup/pre-detangle-20260928` or `pre-rewrite-backup`. I did not reconstruct it. This is the single largest unknown on the plane.; Whether all 51 TRANSLATED task-ledger shas actually land on master. 3 of 3 spot-checked with `git merge-base --is-ancestor` returned YES, so LIKELY; the remaining 48 are untested.; The current suite state. The baseline's 100 failures are a 590.6-hour-old claim, not a present measurement — running pytest was out of scope by instruction — so whether those 100 still fail, and how many NEW failures exist, is unknown.; Read telemetry on the file-resident planes. No instrument records a read of seats.jsonl, tasks.json, MODULE_INDEX.md, WISHLIST.md or forecasts.jsonl. The touch plane would be the proxy and it covers 4.8% of tracked .py, so 'how often does anyone actually consult the authorship ledger' is NOT MEASURED — I can only say it has one code consumer.; Whether WISHLIST's `declined = 0 of 263` means the DECLINE half of the charter has never once fired, or that declined wishes were deleted in violation of the never-delete rule. Distinguishing these needs a git-history walk of that file, which I did not run.; Near-duplicate / semantic-collision rate on `experiment_name`, the lesson corpus's primary key. Exact duplicates are impossible (it is the hash key), but semantically duplicate slugs — which would make the dedup-equals-idempotency contract leak — were not measured.; p95 hook latency and anchor-resolve cost. `context --stats` names both UNCHECKABLE itself: the PostToolUse payload carries no duration and touch.v1 does not stamp one, and the W0.6 context door that would resolve an anchor does not exist yet.; The reverse coverage direction on authorship: how many master commits are findable BY the stable key but absent FROM the ledger. I measured ledger-to-git (93.8%), not git-to-ledger beyond the raw 28.6% row count.; The fences / library-atom / research document planes were SIZED only, not profiled: 28 fence directories, 118 fence .md, 22 fence.json (so 6 fence dirs carry no fence.json — the 2026-09-28 wish's defect, still present); 1,015 library atoms under docs/library; 652 .md under research; 1,200 .md under docs; 1,916 tracked .md repo-wide. Their keys, indexes and fill rates are outside this plane's brief and were not measured.; What the 85 bare 8-hex refs in the byref index actually are (library atom ids? session ids?). Only 1 of 85 resolves as a commit on any ref, so they are not shas; their namespace was not identified.; Redis dbsize moved from 58,383 to 58,744 between two reads minutes apart, so another process is writing the store live. Every Redis count here is point-in-time, not quiesced.

---

## Identifiers and joinability — every id namespace in the house, its stability, its index, and the join graph between planes. Measured 2026-10-03 against E:/AI-Setup, redis akashic-redis:16379 db0, state/eye/eye.db, state/manuals/manuals.db, state/coord/tasks.json, store/docs/*.jsonl. Read-only throughout; no pytest, no db15 flush, no mutating verb.

**The house sealed a reference vocabulary of eight kinds (event, sha, task, lesson, mem, doc, session, seat — core/coord/target.py REF_KINDS, W0.1) and 88.3% of the references actually written to the ledger do not speak it: of 4,780 refs on 13,408 events:raw rows, only `mem:` (559, 11.7%) is a sealed kind, while `learn:` (1,023), `bifrost:` (598), `git:` (208), `file:` (206), `beat:` (93) and ~300 bare paths use a different spelling for the same thing. CERTAIN. The schema and the data disagree about the name of every join.**

### Lesson corpus — redis hashes, one per lesson, akashic-redis:16379 db0

- volume: 1,562 keys; 1,534 carry experiment_name. Cmd: python -c redis.scan_iter(match='learn:experiment:*') | len
- identifier: experiment_name, free-form prose used verbatim as the redis key suffix. 1,474 snake_case, 45 kebab, 13 with uppercase, 5 with literal spaces, 32 whose name itself contains ':' (e.g. learn:experiment:research:web:es_exe_full_capability_surface), max length 102 chars.  (key stability: **mutable**)
- index: learn:category:* (83 sets) and learn:agent:* (60 lists) only. NO full-text and NO vector index. Retrieval is a linear scan of learn:experiments:all with per-record HGETALL and Python token-overlap scoring (core/learning/learning_store.py:821 search_learnings_by_keyword) — 1,562 record loads per query. Semantic index for the whole house is embed:all-MiniLM-L6-v2:* = 82 keys.
- reach: **pushed**
- underused fields: files_affected: field present on 465 (29.8%), holds >=1 actual path on 41 (2.6%) — 79 distinct paths, 90.3% of which resolve on disk. domain: 3 distinct values across the corpus (system 793, ABSENT 695, vfx 74), so the cross-domain promotion code cannot fire. category: 826 of 1,562 (52.9%) are literally 'uncategorized'. root_cause 2.5%, metrics 2.0%, expected 6.0%, anti_pattern 3.3%. NO field exists for session_id, model, task, sha, organ, subsystem or door. Source pointer round-trips exactly for 1,503/1,562 (96.2%); 59 do not.

### Task ledger — state/coord/tasks.json, single 786,774-byte JSON file under a .lock

- volume: 424 tasks. Cmd: py -c json.load(tasks.json)['tasks'] | len. Status: done 172, proposed 114, abandoned 52, approved 39, parked 18, claimed 15, verifying 12, in_progress 2
- identifier: T### — uniform, 424 of 424 match the shape T\d+ exactly. Minted by the ledger's seq counter. Globally unique within the file.  (key stability: **stable**)
- index: NONE. Whole-file read, linear scan, CAS on a seq watermark.
- reach: **pull-only**
- underused fields: desc: exists on 424 (100%), populated on 0 (0.0%) — every task in the house has an empty description field. deps 3.1% (13 of 424), so there is no dependency graph. files 22.4%, acceptance 25.9%, reviewed_by 6.1%, self_verified 0.0% (exists on 176, populated on none). commit 45.0% (191), and 19 of those 191 are the literal placeholder 'deadbee'/'deadbee1', so the task->git join resolves for 172 of 191 = 90.1% (cmd: git cat-file -t <sha> per row).

### Wishlist — docs/WISHLIST.md, flat markdown, append-only by convention

- volume: 263 wish lines (227 open '- [ ] W', 36 folded '- [x] W', 0 declined). Cmd: grep -c '^- \[ \] W' docs/WISHLIST.md etc.
- identifier: W## minted by hand in prose. Highest is W250, but only 253 distinct W-ids appear across 263 entries — the namespace has collisions and/or gaps and nothing checks.  (key stability: **mutable**)
- index: NONE — grep only.
- reach: **dark**
- underused fields: There are no fields. The convention line ('Trigger: what hurt. Land: suggested arc/place.') is prose inside the bullet, so trigger and landing-place are unqueryable at 0% structured fill. No link to a T-id except as text.

### Library atoms — store/docs/{brief,chronicle,contract,design,map,report,ruling}.jsonl, append-only versioned log, rendered twins under docs/library/<type>/

- volume: 1,377 rows, 1,019 unique atom ids, 1,015 rendered files. Cmd: wc -l store/docs/*.jsonl + python set(id). Per type: report 778/595/598, design 462/321/314, brief 85/58/58, chronicle 35/28/28, map 6/6/6, ruling 6/6/6, contract 5/5/5. Net gap 4 (design +7 atoms with no file, report -3 files with no atom).
- identifier: art_YYYYMMDD_<title-slug>_<hash6>, e.g. art_20260723_claude-audit-live-announce-2026-07-23_db35c3. The id embeds both the creation date and the title slug.  (key stability: **mutable**)
- index: artifact:index:* = 465 redis sets across 7 facets: cited-by 390, arc 38, category 24, type 7, status 4, supersedes 1, all 1. No full-text, no vectors.
- reach: **pull-only**
- underused fields: header.arc populated 10.5%, header.seats 13.9% — the two axes that would let an atom be found by what it belongs to. supersedes populated on 1 of 1,377 (0.1%) and header.status='superseded' on 6, while 601 atoms (43.6%) sit at status 'draft' forever. citations_out on 393 atoms (28.5%), 854 citation edges total, and ALL 854 point at another art_ id — zero point at a lesson, task, sha, file or session. The library is a closed graph.

### Event ledger — redis stream events:raw plus a parallel events:raw:byid:* key index, db0

- volume: Stream XLEN 10,294; byid keys 13,408. Cmd: r.xlen('events:raw') and scan_iter('events:raw:byid:*'). 3,555 ids are in byid but NOT in the stream; 438 are in the stream but not byid. Stream oldest entry 2026-08-14 01:52; byid holds rows back to 2026-07.
- identifier: <ms13>-<seq> redis stream id (13,397 of 13,412 conform; 24 are bare integers like '10122' that break the shape).  (key stability: **stable**)
- index: Stream order only — time-ordered, no secondary index by kind, agent or session. The byid set is exact-lookup only.
- reach: **pull-only**
- underused fields: session_id: 2,913 of 13,286 = 21.9% corpus-wide, and it is carried by exactly three kinds — touch 2,467/2,467 (100%), session_signals 128/128 (100%), phase 318/518 (61.4%). Every other kind is 0.0%: learning (1,023 rows), boot (1,886), fail (1,775), decision (552), bifrost_msg (489), file_edit (202), handoff (193), command (206). By month: Jul 0.5%, Aug 1.6%, Sep 1.3%, Oct 79.9% — W0.2 moved the number but only on its own kind. track: 0.0% populated on every sampled row. The time-range path (xrange, which context --stats uses) silently cannot see the 3,555 pre-08-14 events.

### Touch plane (touch.v1) — same ledger, kind='touch', emitted by agent/harness/hooks/claude_posttooluse.py

- volume: 2,483 rows, first 2026-10-02T04:16, last 2026-10-03T14:57 — the plane is 2 days old. Cmd: filter events:raw:byid rows on kind=='touch'. House instrument agrees: py agent_cli.py context --stats reports 1,100 touches in the last 24h at 45.83/h, 131 dropped.
- identifier: detail.targets[].key — the context.target.v1 normalised repo-relative path, with a work:<root>: prefix on worktrees. 291 distinct target keys over 980 target instances.  (key stability: **stable**)
- index: NONE as such — resolved by scanning the ledger. The only live consumer is core/coord/scene.py's touches plane.
- reach: **pushed**
- underused fields: targets: only 694 of 2,474 touches (28.1%) carry >=1 target; the house's own meter reports mean=0.63 and p50=0.0, i.e. THE MEDIAN TOUCH NAMES NO TARGET. By tool: Edit 68/68 and Write 34/34 are perfect, Bash 572/2,241 (25.5%) and PowerShell 20/131 (15.3%) are not. Of 980 target instances 795 (81.1%) resolve to a real path, 110 (11.2%) do not (the Bash parser emits regex fragments as kind='dir': '^/' x10, 's/.*::/' x3, '()0-9]+:.*%/', '<title>[^<]*</'), and 75 (7.7%) are the empty string. session_id is 100% populated but has cardinality ONE across all 2,483 rows (428ba6c4-…, this seat), and that id has 0 rows in eye.db — the join W0.2 exists to make does not currently resolve for a single row.

### Eye transcript index — state/eye/eye.db, SQLite, 313,442,304 bytes

- volume: events 51,753 rows / 74.0 MB of text across 1,673 distinct sessions, 2026-06-16 to 2026-10-01 09:17 (ingest is 2 days stale as of this run). chain 411,866, pyramid 6,119 (L1 4,608 / L2 1,511). Cmd: sqlite3 read-only count(*) per table.
- identifier: event_id = '<session-uuid>:<line>'. session is the harness UUID (stable); line is the ordinal in the transcript JSONL (not).  (key stability: **mutable**)
- index: events_fts (fts5 over text) — one of only TWO full-text indexes in the entire house (cmd: grep -rn 'fts5' --include=*.py). Critically there is NO index on events(session), events(ts) or events(voice): the only index on the table is the autoindex on the event_id primary key, so every session-scoped or time-ranged query is a full scan of 51,753 rows.
- reach: **pull-only**
- underused fields: seat: 240 of 51,753 = 0.5%, and all 240 say 'kimi' — the transcript corpus is effectively unattributable to a seat. cwd/branch/uuid 72.2%, parent_uuid 69.4%. The 8,286 operator utterances (Daniel's own words, 29.3 MB, ~7.3M tokens) carry seat on 0 rows.

### Eye connectome — edges table inside eye.db

- volume: 39,358 edges. Cmd: select edge_kind, count(*) from edges group by 1 — follows 35,700, same_utterance 3,249, adjacent 409. formed_via: transcript 35,700, text-identity 3,249, adjacency 409.
- identifier: src/dst are event_ids ('<session-uuid>:<line>'), PK (src,dst,edge_kind).  (key stability: **mutable**)
- index: edges_src and edges_dst B-trees — the only hand-built indexes in eye.db.
- reach: **dark**
- underused fields: ZERO edges of any intellectual kind. All 39,358 are mechanical adjacency derived from transcript order or exact text identity. None of the four kinds the design calls for (fence, recall-firing, fan, supersession) exist — confirming the 2026-10-01 claim by direct measurement. The graph records who sat next to whom, never what influenced what.

### Manuals shelf — state/manuals/manuals.db, SQLite, 13,258,752 bytes

- volume: 211 docs, 1,992 chunks, 1,992 chunk_vecs. Cmd: select shelf, count(*) from docs group by 1 — apple-hig 172, one-ui 37, one-ui-2019-pdf 2.
- identifier: doc_id INTEGER autoincrement; docs.source is UNIQUE (an absolute Windows path under state/manuals/raw/).  (key stability: **mutable**)
- index: chunks_fts (fts5) + chunk_vecs (MiniLM embeddings) + RRF fusion with a floor — the ONLY hybrid retrieval engine in the house, and the only plane with a blind eval (39 of 40 questions right in the top 5, 2026-09-24).
- reach: **pull-only**
- underused fields: Not a fill-rate problem — a coverage problem. All 211 indexed documents are third-party UI guidelines. ZERO of the house's own 2,177 markdown/text/json files under docs/, research/, fences/ and chronicles/ (40.8 MB) are in it. The best retrieval machine we own is pointed entirely away from our own knowledge.

### Notes / decisions — redis mem:decisions:head:* pointing at ADR records, db0

- volume: 1,144 keys, 1,143 heads + 1 index. Cmd: scan_iter('mem:decisions:*'). Kinds: scratch 504, handoff-spill 65, save 14 (the remaining 560 heads use a different second segment). Authors: kimi 273, deepseek 224, claude 68, dsh_agent 8, deepseek-review 4, sol 3.
- identifier: mem:decisions:head:<kind>:<agent>:<hand-written-slug> resolving to ADR_<MMDDHHMMSS>_<hash8>, e.g. ADR_0824204851_703fb474.  (key stability: **mutable**)
- index: mem:decisions:idx only. No full-text, no vectors, no index by date or topic.
- reach: **partial**
- underused fields: The slug is the entire semantic payload of the key and it is hand-typed, so the only queryable axes are kind and agent. Notes are reachable at boot via load_decisions_applicable_to_task (core/context/aggregator.py:100) and nowhere else — never at the moment of action.

### Chronicle beats — redis narr:beat:* with narr:chapter:*, narr:track:*, narr:theme:*

- volume: 4,567 beats, 906 chapters, 10 tracks, 6 themes. Cmd: scan_iter per pattern. Kinds: learning 1,852, decision 1,125, commit 902, handoff 272, mark 228, note 139, session 40, milestone 9.
- identifier: beat_<epoch10>_<seq>, e.g. beat_1787556147_1884. Minted by BeatLog.  (key stability: **stable**)
- index: By chapter and track only (narr:chapter:* 906, narr:track:* 10).
- reach: **partial**
- underused fields: relates[] 24.7%, themes[] 24.9% — three quarters of the narrative has no stated relation to anything else. Track is 91.7% one value ('ai-setup' 4,190 of 4,567), so the track axis separates almost nothing. The source field IS the plane's redeeming feature: 1,854 point at learn:, 1,089 at mem:, 903 at git:, 285 at handoff:, 226 at episode: — this is the only place in the house where four planes are already named side by side in one row.

### Bus — redis bifrost:* (mailbox, idalias, inbox, session, work), db0, ephemeral by design

- volume: 29,094 bifrost:* keys — the single largest namespace in db0 (58,390 keys total). bifrost:idalias 18,285 + 514 more under per-runner prefixes, bifrost:mailbox 10,459. Cmd: scan_iter + two-segment prefix rollup.
- identifier: redis stream ids aliased through bifrost:idalias:<ms13>-<seq>. Per-runner namespaces (bifrost_d224_571e9291:*, t-w43-*, t-w16-*) fork the namespace 30+ ways.  (key stability: **mutable**)
- index: Per-recipient mailbox fan-out only.
- reach: **pushed**
- underused fields: 18,799 idalias keys exist purely to translate between two id spellings for the same message — 32% of the entire keyspace is a translation table, which is itself the measurement that the id namespace was never unified. Durable projection of bus traffic into the ledger is 489 bifrost_msg rows, 0% of them carrying session_id.

### Authorship ledger — state/authorship/seats.jsonl, append-only, 360,304 bytes

- volume: 935 rows. Cmd: wc -l / json per line. Written by scripts/githooks/post_commit.py, read by core/comm/seat_identity.py, scripts/mirror.py, both githooks.
- identifier: sha (12-char), plus `rekey` on 87.0% and `was_sha` on 82.6% — the rewrite-stable key that survives a rebase.  (key stability: **stable**)
- index: NONE — linear scan of the jsonl.
- reach: **dark**
- underused fields: This is the most wasted STRUCTURE in the house rather than the most wasted content: the rewrite-stable key exists, is populated on 87% of rows, and NOTHING outside the git hooks reads it. core/coord/scene.py:55 names this exact gap in its own fog line — the authorship plane resolves UNCHECKABLE on every context query because the join was never wired. seat_source populated 13.0%, so for 87% of commits we cannot say how the seat was determined.

### Forecast registry — state/coord/forecasts.jsonl

- volume: 29 event rows (register 17, score 12) over 18 distinct forecast ids. Cmd: json per line + set of id.
- identifier: THREE incompatible shapes in one 18-member namespace: F006/F001/F009 (sequential), F-recall-margin-rule/F-recall-floor-078 (slug), fc-highstakes-marriage-20260905 (prefix+slug+date).  (key stability: **mutable**)
- index: NONE.
- reach: **dark**
- underused fields: task_ref is the one real join (e.g. 'W0.3') and it points at wave-slice labels, not at T-ids, so the forecast plane cannot join the task ledger. 12 of 17 registered forecasts have been scored; the standing memory rule says register at EVERY gate and 29 total events across the project's life is the measure of how often that happens.

### Fences — fences/<slug>/ directories of markdown

- volume: 28 fences, 159 text files, 3,968,478 bytes. Cmd: ls fences | wc -l; find fences -type f.
- identifier: a hand-chosen directory slug (context-system, one-spine, wake-origin, t385-recall-trigger …). Six of 28 embed a T-id in the slug; the rest do not.  (key stability: **mutable**)
- index: NONE — grep only.
- reach: **dark**
- underused fields: Fences hold the reconciliations — the sealed design intent and Daniel's rulings. The 2026-10-01 easy-vs-thorough pass measured other-plane reach at 0 of 62 records, and the session_id row of that table is the proof: the fact the entire context-system round rests on exists in SEVEN fence files and ZERO lessons, and the easy tools answered with six unrelated lessons instead of an honest zero. Nothing in a fence carries a target key, a T-id field, or a date field a query could filter on.

### Seat / agent identity — no registry; the string is written verbatim by each writer

- volume: THREE disagreeing namespaces: 59 distinct agent_id on lessons, 71 distinct agent_id on the ledger, 8 distinct seat on the authorship ledger. 63 ledger values are absent from the authorship set. Cmd: set comparison across the three stores.
- identifier: a bare string. Observed drift in one namespace: claude vs claude#428ba6c4 vs claude#bb86400e vs claude-probe3; codex vs codex_root vs codex_root_019fab2d vs codex-01a09757 vs codex_bus_context; astra vs asta; sol vs sunshine.  (key stability: **mutable**)
- index: learn:agent:* (60 lists) indexes the lesson side only.
- reach: **partial**
- underused fields: 'seat' is one of the eight sealed REF_KINDS and there is no authority that mints or validates one. The authorship ledger's 8 values are the closest thing to a canonical set and nothing joins to it. No plane anywhere records the MODEL behind a seat, so a mid-session model swap launders into the corpus unlabelled.

### Recall feedback counters — redis recall:use:<lesson-pointer>

- volume: 1,456 tracked lessons; 24,676 total surfacings. Cmd: mget over scan_iter('recall:use:*') and sum each field.
- identifier: the lesson pointer verbatim as the key suffix — inherits every instability of experiment_name.  (key stability: **mutable**)
- index: NONE.
- reach: **pull-only**
- underused fields: engaged 1,065 (4.32% of surfacings), useful votes 503 (2.04%), helped/auto 131 (0.53%), noise 39. ANY judgment at all: 1,738 of 24,676 = 7.04% (the 2026-10-01 doc's 2.3% is now stale and the honest number is better than it claimed, but 92.96% of surfacings are still unjudged). 322 of 1,456 lessons (22.1%) have ever earned a useful vote; 78 of 1,534 named lessons have never been surfaced once. Retirement, the usefulness factor and cross-domain promotion all consume this signal.

### Loose repository prose — docs/ research/ fences/ chronicles/ design/ charters/ private/, plain files on disk

- volume: 2,177 text files, 40,829,595 bytes across docs+research+fences+chronicles alone. Cmd: find per dir, stat -c%s summed. research/ is the largest at 790 files / 49.0 MB (445 in-flight, 137 reviewed); docs/ 1,217 files / 16.8 MB; chronicles/ 11 files / 8.2 MB; design/ 11 files / 10.3 MB; private/ 117 files / 8.7 MB.
- identifier: the file path. docs/library/<type>/<YYYYMMDD>_<slug>_<hash6>.md for the 1,015 rendered atoms; everything else is a hand-typed filename.  (key stability: **mutable**)
- index: NONE for the ~1,160 non-atom files. Grep and `find` only. The house's own 2026-10-01 pass measured other-plane reach at 0 of 62 for three test concepts.
- reach: **dark**
- underused fields: Typed headers (Status/Class/Type/Author) exist as a convention in docs/LIBRARY.md and are prose, not fields — unqueryable. The research/in-flight directory is 445 files of which a large share are scratch artifacts (_fork_results.json, _claim_rows.json, _holo_prompts.json) sitting in the same namespace as sealed reconciliations, with nothing distinguishing them.

### Recall eval set — tests/fixtures/recall_eval/moments.json (schema recall_eval.v1)

- volume: 25 of a target 40 moments seeded (was 0 at the 2026-10-01 diagnosis). Cmd: json.load | len(moments). Batches: seed-claude-4 (M1-M4, not blind), navi-1/2/3 (N1-N21, blind). Three more batches outstanding.
- identifier: M#/N# hand-assigned per batch.  (key stability: **stable**)
- index: N/A — it is the answer key, scored by core/recall/bench.py (py agent_cli.py recall-bench).
- reach: **pull-only**
- underused fields: measured present on 16 of 25, also_acceptable on 6, abstain_why on 6. The set's own metadata records the sharpest structural finding in the house: two moment pairs carry BYTE-IDENTICAL triggers, which caps recall@1 at 83% by construction — the trigger, not the engine, is the bottleneck. The ground-truth `expect` field points at a lesson by experiment_name, so the answer key inherits the mutable lesson key.

**Joins:**
- touch <-> git via the normalised path key: WORKS. Verified live — `py agent_cli.py context "file:core/recall/at_action.py" --level 1` returned 12 commits and 12 touches on the same anchor, each with a sha: receipt. These are the only two of the door's six planes that resolve.
- touch <-> eye transcript via session_id: BLOCKED IN PRACTICE though the key exists. All 2,483 touch rows carry a session_id (100%) but it has cardinality ONE, and that id has 0 rows in eye.db (cmd: select count(*) from events where session='428ba6c4-…' -> 0). Across the whole ledger only 168 of 2,952 session-carrying rows (5.7%) name a session the Eye holds; 72 of 150 distinct ids match but they are the low-volume ones. The Eye's ingest also stops at 2026-10-01 09:17 while the touch plane begins 2026-10-02, so the two planes do not yet overlap in time.
- lesson <-> file/touch/git via files_affected: BLOCKED. 41 of 1,562 lessons (2.6%) carry a path. core/coord/scene.py:52 refuses the join in its own words and the number it cites (39 of 1,526) is now 41 of 1,562. This is the join the whole context door was built for and it is the one that cannot fire.
- lesson <-> task via a T-id: BLOCKED. No task field exists on any lesson. 263 of 1,562 lessons (16.8%) mention a T-id somewhere in free prose, naming 181 distinct ids — recoverable only by regex over the body, never by lookup.
- lesson <-> session/transcript: BLOCKED, no key. The lesson schema has no session_id, so no lesson can ever be traced back to the conversation that produced it.
- lesson <-> model provenance: BLOCKED, no key on either side. 59 distinct agent_id values on lessons and no model field anywhere; seat_model's self-report is never written to the corpus.
- task <-> git via tasks.commit: WORKS AT 90.1%. 191 of 424 tasks carry a sha and 172 resolve (cmd: git cat-file -t per row). The 19 failures are the literal placeholder string 'deadbee'/'deadbee1' in T249, T294, T296, T300, T303, T304, T307, T308 and 11 others — a poisoned value, not a missing one, which is worse because it passes a non-empty check.
- git <-> authorship ledger via sha and the rewrite-stable `rekey`: POSSIBLE AND UNUSED. 935 rows, rekey populated on 87.0%, was_sha on 82.6%. Read today by exactly five files, all of them git plumbing (core/comm/seat_identity.py, scripts/authorship_ledger.py, scripts/mirror.py, scripts/githooks/{pre,post}_commit.py). core/coord/scene.py:55 names it UNCHECKABLE — the one rewrite-stable key in the house is not wired to anything that asks questions.
- atom <-> atom via citations_out: WORKS. 854 citation edges over 393 atoms (28.5%), rel kinds cites 791 / discusses 52 / derives-from 8 / supports 3, indexed as artifact:index:cited-by (390 sets).
- atom <-> any other plane: BLOCKED ABSOLUTELY. All 854 citation targets start with 'art_' (cmd: counted targets not matching ^art_ -> 0). No atom cites a lesson, a task, a sha, a file or a session. The library is a closed graph with 1,019 nodes.
- ledger event <-> any plane via refs[]: MOSTLY BLOCKED. 3,932 of 13,286 rows (29.6%) carry a ref at all, and of 4,780 ref strings only 559 (11.7%) use a sealed REF_KIND. The rest use parallel spellings for the same concepts — learn: where the schema says lesson:, git: where it says sha:, file: where it says doc:, beat: where it says event: — plus ~300 bare paths with no kind prefix.
- chronicle beat <-> lesson/note/git via beat.source: WORKS, and is the best-kept join in the house. 4,567 beats, source resolves to learn: 1,854, mem: 1,089, git: 903, handoff: 285, episode: 226. This is the only plane that already names four other planes in one row — and nothing queries it that way.
- note <-> anything: BLOCKED. mem:decisions keys carry only kind/agent/hand-typed-slug. No target, no task, no sha, no session.
- fence <-> anything: BLOCKED. 28 fences, 159 files, zero structured fields. The 2026-10-01 pass measured 0 of 62 other-plane records surfaced for three probe concepts, and session_id is the proof case: present in 7 fence files, 0 lessons.
- wish <-> task via a folded T-number: PARTIAL AND PROSE-ONLY. 36 of 263 wishes are marked folded and the T-number lives inside the bullet text; nothing parses it.
- forecast <-> task via task_ref: BLOCKED BY VOCABULARY. task_ref holds wave-slice labels ('W0.3'), not T-ids, so the 29-row forecast registry cannot reach the 424-row task ledger.
- lock <-> file: BLOCKED. Locks key on their own lowercased path spelling — one of the four live spellings of a single file that W0.1 exists to unify (core/coord/scene.py:57).
- session focus <-> file: BLOCKED BY DESIGN FOR NOW. core/coord/session_focus.py matches by substring; the W0.1 spec deliberately keeps it out of the typed plane because its false hits are the class it already owns (scene.py:60).
- THE SINGLE KEY WHOSE ABSENCE BLOCKS THE MOST: a context.target.v1 normalised target key stamped on a record AT WRITE TIME. The normaliser is built (core/coord/target.py, W0.1) and exactly one plane emits it — the 2-day-old touch stream, where the median row still carries zero targets (p50=0.0, mean=0.63, measured by py agent_cli.py context --stats). It is absent from lessons (2.6%), tasks (22.4%), atoms (0%), notes (0%), fences (0%), wishes (0%) and locks (own spelling). Four of the context door's six planes — lessons, authorship, locks, focus — are blocked on this one key, and so are at least eight of the joins above. Runner-up: session_id on the kinds that are not touch (0.0% on learning, boot, fail, decision, file_edit, handoff, bifrost_msg), which blocks every join between what a seat DID and what a seat LEARNED.

**Biggest waste:** Daniel's own words: 8,286 operator utterances in state/eye/eye.db totalling 29,277,232 characters (~29.3 MB, roughly 7.3M tokens) — measured by `select count(*), sum(length(text)) from events where voice='operator'`. Nothing can push them. They are reachable only by `eye find` / `freq`, which a seat must know to run; the events table has NO index on session, ts or voice, so every scoped query is a full scan of 51,753 rows; 0 of the 8,286 carry a seat attribution; and the Eye's ingest is frozen at 2026-10-01 09:17, so the two most recent days are not in it at all. The knowledge type Daniel named himself — "recalls to help you remember what you wanted to remember WHEN you wanted to remember it" — is the largest single body of text in the house and the only push path we own (the PreToolUse recall-at hook) reads one plane, learn:experiment:*, and never this one. Close second, and the cheaper fix: 2,177 of our own documents (40.8 MB under docs/, research/, fences/, chronicles/) have no index of any kind, while the one hybrid FTS5+MiniLM+RRF engine we built and proved at 39-of-40 blind questions is pointed at 211 third-party Apple HIG and One-UI pages. We own a working retrieval machine and have aimed all of it away from ourselves.

**Not measured:** Current recall@5 / precision@3 / chrome share. `py agent_cli.py recall-bench` exists and the 25-moment answer key is seeded, but running it drives the live recall engine, which increments recall:use:* surfaced counters — a write. This run was read-only, so the bench was not run. It is the single cheapest number to add and it takes one command.; p95 hook latency on the touch path. The house's own instrument refuses it by name: `context --stats` prints 'p95_hook_latency_ms = UNCHECKABLE — the PostToolUse payload carries no duration and touch.v1 does not stamp one yet'.; anchor_resolve_cost_ms. Same instrument, same honest refusal — W0.6's resolver timing has no call to time because the remaining four planes are unbuilt.; What fraction of the 2,177 loose docs/research/fences/chronicles files a seat can actually find. There is no index to query, so there is no denominator to measure against. The only existing datapoint is the 2026-10-01 three-concept pass (other-plane reach 0 of 62) and three concepts is not a census.; Whether the touch plane's single session_id is one genuinely long session or a stamping defect. Measured: 2,483 rows spanning 2026-10-02T04:16 to 2026-10-03T14:57 all carry 428ba6c4-…, and the Eye holds 0 rows for it. Distinguishing 'one 35-hour session' from 'session id cached at the wrong moment' needs the harness's own session log, which was not read this run.; Lesson-corpus staleness: how many of the 1,562 lessons name a file, flag or verb that no longer exists. Only files_affected was resolved (93 of 103 paths, 90.3%) and that covers 2.6% of the corpus; the claim bodies were not checked.; Row-level duplication inside the 1,377-row atom log (1,019 unique ids means 358 rows are later versions, but no diff was taken, so how much is real revision vs re-render is unknown).; db13 (1,229 keys) and db15 (1,104 keys) on akashic-redis were enumerated at the keyspace level only. db15 was left strictly alone per the run's instruction; db13 was not opened.; session_logs/store_state.db (55 MB: hash 24,748 / kv 21,148 / zset 24,090 / set_members 10,938 / list 2,571) was counted but not interpreted — it is the FileStore mirror of redis and whether it is current, stale or divergent from db0 was not tested. dockerized-ai/knowledge/knowledge.db is 0 bytes and will not open (legacy).; Whether the 3,555 events present in events:raw:byid but absent from the events:raw stream are recoverable or orphaned. The gap is measured; its cause (stream MAXLEN trim vs failed write) was not traced.

---

## Retrieval surfaces (the "right place" half): every way a seat can currently find something, measured against the knowledge planes they do and do not cover. E:/AI-Setup, measured 2026-10-03.

**10 of the 110 CLI verbs are read surfaces over the ONE lesson plane (1,562 rows); ZERO verbs reach the fence plane (28 rounds, 21 sealed reconciliations, 160 files, 3.78 MB of adjudicated design rulings). Measured by probing a phrase that exists in exactly one file in the tree, a fence addendum ("machine-diary design", ground truth: 1 file, plane=fences): recall returned 11 lessons, knowledge-map 26 items, lookback 17 items, events --search 10, manual search 8 -- and not one of the 62 returned items was the file. Five surfaces answered; none answered correctly; none said zero. Commands: `py agent_cli.py recall "machine-diary design" --json` etc., ground truth by python walk over docs/ research/ fences/ chronicles/ charters/ design/.**

### recall-at -- THE one push path. Hook on every tool call; reads the lesson store (redis db0 learn:experiment:*) + gate_rules + the verb registry (research/in-flight/_verbs_snapshot.txt). Keyed on the Bash command line / path, not on intent.

- volume: 1,562 lessons reachable; 91 injections / 29,290 tokens in the last 24 h (`py agent_cli.py injections --hours 24 --json`). It fired 6 times unprompted during this census, visible in the hook output.
- identifier: the command string or path the seat is about to run; matches lessons by `learn:experiment:<experiment_name>`  (key stability: **stable**)
- index: NONE -- linear keyword/path overlap over all 1,562 lessons per call. core/recall/at_action.py:12 states it outright: "keyword/path-first relevance via the shared Ranker (no embedding on the hot path)".
- reach: **pushed**
- underused fields: the axes it could rank on and cannot: domain 867/1,562 = 55.5% filled but only 3 distinct values (system 793, empty 695, vfx 74); category 1,534/1,562 present but 826 of those are the literal string "uncategorized" (52.9%); files_affected 41/1,562 = 2.6%; root_cause 39 = 2.5%; anti_pattern 52 = 3.3%; related_to 372 = 23.8%. No model-id field exists at all. Command: python redis scan over learn:experiment:*, counting non-empty values per field.

### recall -- pull search over the lesson store only (redis db0 learn:experiment:*)

- volume: 1,562 lessons searched; 24,655 lifetime surfaced impressions, 503 useful votes + 39 noise = 542 judged = 2.20% (`py agent_cli.py stats --days 7 --json`; the standing doc said 2.3% of 23,333)
- identifier: free-text query -> keyword overlap against recommendation/what_tried/actual text  (key stability: **stable**)
- index: NONE -- linear scan. core/learning/agent_memory.py:447: "Find similar past experiences (keyword overlap; richer retrieval is Phase C)."
- reach: **pull-only**
- underused fields: DOES NOT REPORT AN HONEST ZERO. `py agent_cli.py recall "zzqqxx nonexistent term 9f3k" --json` returns 5 lessons, 15,559 chars, for a string that exists nowhere in the tree. Duplicated effort: recall, recall-at, knowledge-map, list, triage, stats, recall-bench, recall-counters, recall-curate and recall-prevention are ten read surfaces over this single plane.

### recall-bench (W0.3, landed 2026-10-02) -- the eval set. data/ answer key, 25 seeded moments against the lesson store.

- volume: 25 seeded of a target 40; 18 scored. recall@1 = 22.2%, recall@5 = 27.8%, chrome share 3.2%. Ceiling: delivered 5, rankable 10, unmatchable 3, reachable 15 of 18 = 83.3% at probe depth 200. Command: `py agent_cli.py recall-bench --json`.
- identifier: moment id (M1-M4, N1-N21) -> one labelled right-answer lesson source key  (key stability: **stable**)
- index: n/a (it is the instrument, not a corpus)
- reach: **pull-only**
- underused fields: THE NUMBER THAT MATTERS: abstention 0 correct of 6 abstain moments = 0.0%. The bench contains six moments whose right answer is silence and the engine was right zero times. It also self-reports precision@3 as UNCHECKABLE with the reason, which is the honesty standard the other surfaces do not meet.

### knowledge-map -- walks lessons + notes + docs. Loaders imported verbatim from core/recall/lookback.py (its own docstring: "one projection, two faces").

- volume: corpus 3,986 items (measured by calling each LAYERS loader: docs 1,060, charters 21, research 120, notes 1,877, promoted 200, chapters 458, git 250)
- identifier: free-text topic -> token overlap; edges walked via lessons' related_to  (key stability: **stable**)
- index: NONE -- re-reads 1,060 markdown file heads from disk on every call (3.3 s measured)
- reach: **pull-only**
- underused fields: edge-walk starves: lessons with related_to = 372/1,562 = 23.8%. DOES NOT REPORT AN HONEST ZERO: nonsense control returns counts {surface: 11, archive: 2} = 13 fabricated items. Duplicates lookback's entire corpus loader.

### lookback -- the rationale corpus. LAYERS = docs, charters, research, notes, promoted, chapters, git. Physically: docs/*.md (44 of 51, after 3 REFERENCE_DOCS and 4 self-declared reference-class drops: DOORS.md, MAP.md, PHYSICS.md, PRIOR_ART.md) + AGENTS.md + docs/library/<type>/*.md (1,015) + charters (21) + research/reviewed/*.md top level only (120) + redis notes/promoted/chapters + 250 git subjects.

- volume: 3,986 items. House markdown on disk in the same roots = 2,021 files; the corpus reaches 1,201 of them = 59.4%. Commands: direct call of each LAYERS loader; os.walk counts per root.
- identifier: free-text question -> IDF-weighted token overlap, layered  (key stability: **stable**)
- index: NONE -- full filesystem rescan per query (2.5 s measured)
- reach: **pull-only**
- underused fields: NOT SWEPT, measured file counts: fences 118 .md (+42 json/other), research/in-flight 486, docs/_archive 134, research/reviewed subdirectories 29 (120 of 149 reached), chronicles 6, arsenal 20, design 4, and every .py in the tree. Nonsense control still returns 3 items.

### manual search -- the manuals shelf, state/manuals/manuals.db (13.3 MB SQLite). FTS5 porter + MiniLM vectors + RRF fusion + a 0.25 cosine floor. THE ONLY SEMANTIC RETRIEVAL IN THE HOUSE.

- volume: 211 docs / 1,992 chunks / 1,992 vectors, all model all-MiniLM-L6-v2, all ingested in one 27-second window on 2026-09-24T22:29. Shelves: apple-hig 172, one-ui 37, one-ui-2019-pdf 2. Commands: sqlite counts; `py agent_cli.py manual search ... --json`.
- identifier: chunk_id integer, doc source URL unique  (key stability: **stable**)
- index: FTS5 (chunks_fts, 1,992 rows) + dense vectors (chunk_vecs, 1,536-byte float32) + RRF. The only real index over text in the house besides the Eye.
- reach: **pull-only**
- underused fields: IT COVERS ZERO HOUSE KNOWLEDGE. 1,992 chunks of Apple HIG and Samsung One UI; 0 lessons, 0 docs, 0 fences, 0 notes. The engine the reach map calls primitive #6 is built and pointed at someone else's manuals. It also mislabels its own abstention: when the vector channel correctly returns nothing above floor it prints "no passages are embedded yet (run manual ingest)" (core/manuals/shelf.py:455) although 1,992 vectors are present -- and the BM25 channel has no floor, so the nonsense control still returns 4 hits at score 0.016.

### eye find / freq / get -- the transcript plane. state/eye/eye.db, 313 MB SQLite, FTS5 over every event.

- volume: 51,753 events, 1,673 sessions, 39,358 edges, 6,119 pyramid nodes. 8,286 of the events are Daniel's voice (voice='operator'). Commands: `py agent_cli.py eye stats`; sqlite counts.
- identifier: <session-uuid>:<line> address; stable per transcript file  (key stability: **stable**)
- index: FTS5 events_fts (51,753 rows) -- phrase/lexical only; the grammar is still S1
- reach: **pull-only**
- underused fields: seat 240/51,753 = 0.5% -- you cannot ask "what did THIS seat already conclude". Edges: 35,700 'follows' + 3,249 'same_utterance' + 409 'adjacent' = 39,358, and ZERO of the four intellectual kinds (fence, recall-firing, fan, supersession) the reach map names. Pyramid has L1 (4,608) and L2 (1,511) and NO L3. CURRENCY: newest event 2026-10-01T13:17Z, 49.8 h stale; 135 of 1,401 transcripts on disk were never ingested; 29 ingested files have moved since. BEST BEHAVIOUR IN THE HOUSE: honest zero with its scope and cost named -- `eye find` on the nonsense control prints "[eye] 0/0 hit(s), ~0 tok"; `eye freq` prints "VERDICT: UNHEARD".

### context <anchor> --level 1 (W0.5/W0.6, landed 2026-10-02) -- the designed cross-plane door. Reads git log, the touch stream (redis events:raw), and declares the rest.

- volume: On `file:core/comm/toolbox.py`: 12 commits + 8 touches returned, 4 planes refused. It self-reports "epistemic unknown (2 of 6 planes joined)" and "FOG: 4 of 6 planes not joined yet: lessons, authorship, locks, focus". Command: `py agent_cli.py context "file:core/comm/toolbox.py" --level 1`.
- identifier: context.target.v1 normalised key (core/coord/target.py, W0.1 DONE, 73 pins) -- a repo-relative path  (key stability: **stable**)
- index: NONE -- scans the touch event keys per call
- reach: **partial**
- underused fields: This is the only surface that refuses honestly per plane and prints the REASON each join is missing. Its four UNCHECKABLE lines are the join map, self-reported: lessons can't join because files_affected is 2.6% filled; authorship can't join because the rewrite-stable key is unwired (Heimdall's B5.3); locks can't join because lock keys use their own lowercased spelling; focus can't join because it matches by substring.

### context --stats -- the meter over the touch stream (W0.4)

- volume: 24 h window: SESSION COVERAGE 1,083/1,167 = 92.8%; touch 995/995 = 100%, phase 88/88 = 100%, fail 0/29, boot 0/23, learning 0/4 = 0%. TOUCHES DROPPED 109. Ring retention 1,345 h. Command: `py agent_cli.py context --stats --hours 24`.
- identifier: session_id (claude-code session UUID) + touch.v1 target key  (key stability: **stable**)
- index: NONE
- reach: **partial**
- underused fields: TARGETS PER TOUCH mean 0.6056, p50 = 0.0 -- more than half of all touches resolve to NO target, so the majority of the new join plane carries no join key. COULD NOT SEE IN 10.6% (honestly reported as null, never as zero). Corpus-wide the touch plane is 2,445 events spanning exactly two days (2026-10-02 and 10-03) and ONE distinct session_id -- this session's. Every other seat's harness emits nothing.

### events --search -- the raw firehose, redis db0 events:raw:byid:* + 127 per-agent streams

- volume: 13,262 byid records + 29,868 stream entries across 127 bifrost streams. Kinds: turn_metrics 2,435, touch 2,445, boot 1,886, fail 1,773, learning 1,023, decision 552. Commands: python redis scan; `py agent_cli.py events --search ... --json`.
- identifier: redis stream id <ms>-<seq>; refs[] carries plane refs (29.6% of records have one)  (key stability: **stable**)
- index: NONE -- substring over event summaries
- reach: **pull-only**
- underused fields: session_id overall 2,812/13,181 = 21.3%, and that is entirely the new touch work: 100% on touch and session_signals, 61.4% on phase, 0.0% on all 16 other kinds including boot, fail, learning and decision. By month: 2026-07 0.5%, 08 1.6%, 09 1.3%, 10 79.6%. track 0/13,181 = 0.0%. WORST HONEST-ZERO FAILURE MEASURED: the nonsense control returns 20 items / 26,576 chars, MORE than the real probe returned.

### notes / the decisions plane -- redis hash mem:decisions (1 key, 1,878 fields) + 1,143 mem:decisions:head:<title> pointers + a 1,877-member zset index

- volume: 1,878 notes. By month: 2026-06 17, 07 908, 08 540, 09 371, 10 42. Command: python redis hgetall('mem:decisions'), json-parse each.
- identifier: ADR_<MMDDHHMMSS>_<hash>, with a title->id head pointer  (key stability: **mutable**)
- index: a zset by created_at. NO text index and NO query verb: `notes` takes only --limit/--days/--project/--all. `py agent_cli.py notes --json --limit 5` returned 1,215 notes and 3.4 MB -- the limit is not honoured and there is no way to ask a question of this plane except through lookback/knowledge-map.
- reach: **pull-only**
- underused fields: status: 1,878 of 1,878 are the single value "accepted" -- zero discriminating power. rationale: present on 100%, NON-EMPTY on 0. consequences: present on 100%, NON-EMPTY on 0. session_id 3/1,878 = 0.2%. context 661 = 35.2%. The title is the mutable key: re-noting the same title overwrites, so a renamed note orphans its head pointer.

### the library -- docs/library/<type>/*.md on disk PLUS a real faceted index in redis (artifact:<id> bodies + artifact:index:* sets)

- volume: 1,015 files on disk / 1,019 atoms indexed. Facets: type 7 values x 1,019 memberships (report 598, design 314, brief 58, chronicle 28, map 6, ruling 6, contract 5), status 4 x 1,019, category 24 values x 2,663 memberships (multi-label), arc 38 values x 134, cited-by 390 edges. Commands: `redis zcard artifact:index:all`; scard per facet; find docs/library -name '*.md'.
- identifier: akashic_id (art_<date>_<slug>_<hash>) plus akashic_sha content hash, in a typed YAML header on every atom  (key stability: **stable**)
- index: THE ONLY FULLY-FACETED STABLE-ID INDEX IN THE HOUSE -- and no retrieval surface reads it. grep for 'artifact:index' across the tree returns only core/library/atoms.py (the writer) and core/foundation/durable_reconcile.py. lookback and knowledge-map reach the same atoms by re-reading the files off disk and scoring tokens, ignoring type, status, category, arc and cited-by entirely.
- reach: **partial**
- underused fields: arc 134/1,019 = 13.1% -- the one axis that would answer "everything about T418" is 87% empty. The 390 cited-by edges are a citation graph nothing walks.

### find -- filename search over the whole machine via Search Everything (es.exe)

- volume: sub-second, whole-machine. `py agent_cli.py find session_id --limit 10 --format json` -> 2 hits; nonsense control -> 0 hits.
- identifier: filename substring / regex  (key stability: **mutable**)
- index: the Everything NTFS index (external, live)
- reach: **pull-only**
- underused fields: names only, never content. Honest zero: YES. This is why Navi could not find her own prior-art sweep -- `find` would have found the filename, nothing searches the body.

### sift -- the nested ask over SOURCE CODE (planes=['source'])

- volume: `py agent_cli.py sift "machine-diary design" --dry-run --json` -> occ=0 files=0, and it says why
- identifier: term occurrences in source  (key stability: **mutable**)
- index: NONE -- ripgrep-shaped scan, then a model fan
- reach: **pull-only**
- underused fields: BEST ZERO IN THE HOUSE and it should be the template: it prints "BLIND: PLANE: this pack contains ['source'] only. A term can be coherent in source and forked in docs..." and "BLIND: EXCLUDED BY PLANE, not absent: out-of-corpus=1". It names the plane boundary rather than pretending the absence is the world. But it covers only source, and costs a model fan.

### discover / discover --semantic -- the verb plane, research/in-flight/_verbs_snapshot.txt

- volume: 110 verbs (`py agent_cli.py discover --json` -> 110 items). --semantic routes to deepseek-v4-pro at $0.00913 per question.
- identifier: verb name  (key stability: **stable**)
- index: NONE lexically (honest zero: both probe and control return 0); the semantic path is an LLM read of a flat snapshot, not an index
- reach: **pushed**
- underused fields: this plane IS pushed -- recall-at injects '[verb]' lines into the hook output, observed twice during this census. The reach map's complaint that it is 'too loud' is the same mechanism.

### the FENCE plane -- fences/<round>/{brief,half_a,half_b,half-sol,reconciliation}.md + fence.json + pv_report.json

- volume: 28 rounds, 21 with a sealed reconciliation.md, 160 files, 3.78 MB. Commands: os.listdir over fences/; os.walk byte sum.
- identifier: fence directory name (e.g. 'context-system'); fence.json carries no state field on any of the 22 that parse  (key stability: **mutable**)
- index: NONE
- reach: **dark**
- underused fields: ZERO SURFACES. Not in lookback's LAYERS, not in knowledge-map, not in the Eye, not an atom: 0 of 28 fence directory names match any of the 1,019 library atom titles. The only way in is the harness's own ripgrep, which is outside the house's accounting entirely. This is where every adjudicated design ruling and every Wave-0 build spec lives.

### research/in-flight -- live halves, counters, prior-art sweeps

- volume: 486 .md / 6.85 MB (os.walk). research/reviewed by contrast: 149 files, of which lookback loads the 120 at top level and misses the 29 in subdirectories.
- identifier: filename  (key stability: **mutable**)
- index: NONE
- reach: **dark**
- underused fields: Probe "anti-popularity prior" exists in exactly one file, research/in-flight/recall-the-anti-popularity-prior-2026-10-02.md. recall returned 2 lessons, knowledge-map 26 items, lookback 21 items (including three research/reviewed/ prior-art files on the same subject) -- and none of them was the file. The reviewed shelf is indexed; the in-flight shelf, where today's thinking lives, is not.

### the authorship ledger -- state/authorship/seats.jsonl

- volume: 935 rows, 360 KB, each carrying sha + was_sha + seat + seat_email + committer_email
- identifier: sha, with was_sha giving the rewrite-stable mapping across the three history rewrites  (key stability: **stable**)
- index: NONE -- a flat jsonl
- reach: **dark**
- underused fields: THE REWRITE-STABLE KEY THE WHOLE HOUSE NEEDS ALREADY EXISTS HERE AND NOTHING JOINS TO IT. `context --level 1` names it as its own second UNCHECKABLE plane. 2,847 commits in the repo against 935 ledger rows = 32.8% coverage.

### the bus -- 127 redis streams + bifrost:mailbox (10,459 keys) + bifrost:idalias (18,847 keys)

- volume: 29,868 stream messages. Surfaces: bifrost-sync (inbox peek), promoted (durable salient only), capture (by stream id), flow, mailbox.
- identifier: redis stream id; idalias maps short ids  (key stability: **mutable**)
- index: NONE over message text
- reach: **partial**
- underused fields: lookback reaches 200 promoted messages of 29,868 = 0.67%. There is no text search over the bus at all; `capture` needs the id you already have.

### the chronicle -- redis narr:beat (4,567) / narr:chapter (906) / narr:track (10) / narr:theme (6) + chronicles/story.index.json (1.56 MB)

- volume: 4,567 beats. Surfaces: story (--chronicle/--track/--theme/--at), timeline, lookback's chapters layer (458 of 906 = 50.6%).
- identifier: beat_<epoch>_<seq>; chapter_<hash>  (key stability: **stable**)
- index: per-track and per-theme redis indexes only
- reach: **partial**
- underused fields: themes populated on 1,139/4,567 beats = 24.9%; relates on 1,126 = 24.7%. Only 6 themes exist for 4,567 beats (memory 486, evaluation 383, logging 204, narrative 148, routing 131, design 8) -- the same collapse as the lesson domain axis.

**Joins:**
- touch <-> the Eye via session_id: BLOCKED, and not by key shape. Both sides use the claude-code session UUID. But all 2,445 touch events carry exactly ONE distinct session_id (this session's, 428ba6c4-...), and 0 of them match any of the Eye's 1,673 session ids -- because the Eye's newest event is 2026-10-01T13:17Z, 49.8 h stale, and the touch plane only began emitting on 2026-10-02. The join is a cron problem, not a schema problem: ingest the Eye and it closes.
- lesson <-> file via files_affected: BLOCKED by emptiness. 41 of 1,562 lessons carry the field = 2.6%. `context --level 1` refuses this join in its own words and names the same reason.
- lesson <-> file via touch targets (the W0.2 replacement route): PARTIALLY BLOCKED. The targets are normalised through context.target.v1 and are clean where present, but targets-per-touch has p50 = 0.0 (mean 0.6056) -- more than half of all touches carry no target, and 10.6% are honestly reported as unknowable. Command: `py agent_cli.py context --stats --hours 24`.
- lesson <-> its own usage counters via source key: WORKS. 1,455 of 1,457 recall:use keys resolve to a live lesson; 2 ghosts = 0.1% (triage's stricter definition says 29). The lesson key learn:experiment:<experiment_name> is a human-authored slug and is in practice stable. 107 of 1,562 lessons have no counter at all.
- lesson <-> model id: IMPOSSIBLE. The field does not exist. 1,562 lessons carry agent_id (claude 818, deepseek 174, kimi 106, sol 96, ...) and nothing records which model sat in that seat, so a mid-session model swap launders into the corpus unrecorded.
- git commit <-> seat via the authorship ledger's was_sha: EXISTS AND UNWIRED. state/authorship/seats.jsonl has 935 rows carrying both sha and was_sha across three history rewrites; 2,847 commits in the repo = 32.8% covered; no retrieval surface reads the file. `context --level 1` lists it as UNCHECKABLE with the reason 'wiring it is Heimdall's B5.3'.
- library atom <-> arc: WORKS WHERE FILLED, 134 of 1,019 = 13.1%. The facet index is real (38 arcs, sets in redis) and no surface queries it; lookback and knowledge-map re-read the same 1,015 files off disk and score tokens instead.
- library atom <-> library atom via cited-by: WORKS, 390 edges in redis, walked by nothing.
- lesson <-> lesson via related_to: PARTIAL, 372 of 1,562 = 23.8%. knowledge-map's edge-walk is the only consumer and starves on the other 76%.
- Eye event <-> seat via the seat column: BLOCKED. 240 of 51,753 = 0.5% filled. Every seat's request for 'my own prior verdicts when I re-enter this territory' dies on this column.
- Eye event <-> anything via an idea edge: IMPOSSIBLE TODAY. 39,358 edges, 100% mechanical (follows 35,700, same_utterance 3,249, adjacent 409), zero of the four intellectual kinds.
- fence <-> library atom via adoption: 0 of 28. No fence round's name matches any of the 1,019 atom titles, so sealing a reconciliation does not place it on any indexed shelf.
- note <-> session via session_id: BLOCKED. 3 of 1,878 = 0.2%.
- event <-> session via session_id, outside touch: BLOCKED. 0.0% on boot, fail, learning, decision, bifrost_msg, handoff, command, file_edit and every other kind; 21.3% overall and all of it is the two-day-old touch work.
- DUPLICATED EFFORT 1 -- the lesson plane: 10 read surfaces (recall, recall-at, knowledge-map, list, triage, stats, recall-bench, recall-counters, recall-curate, recall-prevention) over 1,562 rows, every one of them a fresh linear keyword scan, none of them sharing an index.
- DUPLICATED EFFORT 2 -- the docs/notes corpus: knowledge-map imports _docs_items and _note_items verbatim from lookback and says so in its own docstring ('one projection, two faces'). Two verbs, one 3,986-item filesystem rescan each, 2.5-3.3 s per call, no cache.
- DUPLICATED EFFORT 3 -- three independent text engines: FTS5 over transcripts (eye.db, 51,753 rows), FTS5 + MiniLM + RRF + a 0.25 floor over manuals (manuals.db, 1,992 chunks), and token-overlap scans over everything else. The good engine is pointed at Apple's HIG; the house's own knowledge gets the weakest of the three.
- HONEST-ZERO LEDGER, nonsense control 'zzqqxx nonexistent term 9f3k' (ground truth: 0 files anywhere): eye find 0 and says so; eye freq 'VERDICT: UNHEARD'; find 0 hits; discover 0; sift names the plane it searched and the one it did not. AGAINST: recall 5 items, knowledge-map 13, manual search 4, lookback 3, events --search 20. Five surfaces fabricate; five abstain honestly. recall-bench scores the abstention arm at 0 correct of 6.

**Biggest waste:** The FENCE PLANE: 28 adjudicated rounds, 21 sealed reconciliations, 160 files, 3.78 MB, measured by os.walk over fences/. It holds the house's design intent -- the halves, the reconciliations, and the Wave-0 build specs the current work is executing from -- and ZERO of the 110 verbs read it. It is not in lookback's seven LAYERS, not in knowledge-map, not ingested by the Eye, and 0 of its 28 round names correspond to any of the 1,019 indexed library atoms, so sealing a reconciliation does not shelve it anywhere retrievable. Proof: the phrase "machine-diary design" occurs in exactly one file in the tree, fences/context-system/addendum-2026-10-02-the-fold.md; five surfaces were asked and returned 62 items between them, none of which was the file, and none of which said zero. The only way into this plane is the harness's own ripgrep -- a tool the house does not own, does not meter, and cannot push. Runner-up by volume: research/in-flight, 486 files / 6.85 MB, equally dark while its sibling research/reviewed (120 files) is indexed -- today's thinking is unreachable and last month's is not.

**Not measured:** scout, orient, glance, zoom, trace, ground, college, story --at and timeline: NOT PROBED. scout and sift (live, not --dry-run) spend model calls, and the census was held read-only and cheap. Their plane coverage is read from DOORS.md declarations, not from a run.; MCP-door vs CLI-door parity: NOT MEASURED. Every probe went through `py agent_cli.py`. Whether mcp__akashic-aurora__recall returns the same ranking as the CLI for the same query is unverified, and the MCP door is how three of the five seats actually retrieve.; Per-surface token cost: NOT MEASURED except where the surface prints it itself (eye find reports ~tok per answer; injections reports 29,290 tokens/24 h; discover --semantic reports $0.00913). recall, knowledge-map and lookback print no cost, so the price of a pull is unknown.; recall precision: UNCHECKABLE and the bench says so in its own output -- the eval set carries one labelled right answer per moment, not a labelled relevant-set, so any precision@3 would be recall@3 renamed. 15 of the 40 target moments are still unwritten (batches 4-6 outstanding).; Whether any seat other than claude emits touches: measured as a single distinct session_id across 2,445 events, but the reason is NOT measured -- it could be that no other harness has the hook installed, or that the other seats simply did not run in the 2026-10-02/03 window the ring covers.; Why 109 touches were dropped in the last 24 h (`context --stats` reports the count and not the cause).; p95 hook latency and anchor-resolve cost: the instrument itself names these UNCHECKABLE -- the PostToolUse payload carries no duration and touch.v1 does not stamp one.; The 135 un-ingested transcripts: counted, not sized. How many events and how much of Daniel's verbatim voice is sitting outside the Eye's FTS index is unknown.; Ground truth for the coverage probes covers .md/.json/.txt under docs, research, fences, chronicles, charters and design only. Source code bodies (20,450 .py files) were not scanned for the probe phrases, so 'exists in exactly one file' is bounded to the prose tree.; Whether the 1,019-atom facet index is stale relative to the 1,015 files on disk (4-atom discrepancy, cause not chased).; Recall quality for the OTHER seats: recall-bench scores one engine against one answer key; no per-seat recall number exists, and four of the five testimonies in the standing doc are about a seat failing to reach its OWN prior work.

---
