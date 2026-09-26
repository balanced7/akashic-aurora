# ANNEX B — measured evidence, and TWO CORRECTIONS to the brief

**Filed 2026-09-26 by claude.** Source: a 15-agent measurement workflow (7 lanes, each measured
then independently re-run by a second agent, plus a completeness critic). 2.27M tokens, 813 tool
uses, 0 agent errors, 56 minutes.

I told you in §3.9 this annex would be additive and that nothing in §3.1–3.8 was expected to be
overturned. **That was wrong. Two claims in the brief are materially false, and one of them
changes the design question.** Read this section before you finalise. If you have already sealed,
say so and say what it would have changed.

---

## CORRECTION 1 — the connectome holds ZERO edges. The typed edge graph does not exist.

Brief §3.1 said *"The edge graph already exists, and it is typed."* Measured:

- **`edges` table in the live store (`state/eye/eye.db`) holds 0 rows.** All eight `formed_via`
  values count zero. The same database holds 48,702 events, 1,511 sessions and 379,953 chain rows,
  so the corpus is present and only the edge projection is empty.
- **`eye trace` never reaches the `--formed-via` filter.** It hits the empty-connectome guard at
  `agent_cli.py:2717-2720` and exits 2, identically with and without a filter. (The measuring
  agent's first probe reported exit 0 — because `$?` was `head`'s status through a pipe. Re-measured
  without the pipe: exit 2.)
- **Five of the eight edge kinds have no writer anywhere in the repo.** `fence`, `recall-firing`,
  `fan`, `supersession`, `manual` appear only in the `FORMED_VIA` vocabulary tuple
  (`connectome.py:59`) and the `_EVIDENCE_OF` lookup (`:70-71`). Exactly one module writes edges
  (`core/eye/connectome.py`), at three sites, one per kind: `follows`/transcript (:137-141),
  `same_utterance`/text-identity (:159-163), `adjacent`/adjacency (:185-189).
- **A full rebuild still produces none of the five.** `connectome.build()` against a byte copy of
  the live db (30.9s) yields 36,876 edges: transcript 33,397 / text-identity 3,078 / adjacency 401,
  and **0** for fence, recall-firing, fan, supersession, manual.
- **`--formed-via text-identity` can never match a step even on a built corpus** — the walk
  restricts to `edge_kind IN ('follows','adjacent')` (`connectome.py:278,281`) and text-identity is
  carried exclusively by `same_utterance`. Net on a fully built corpus: 2 of 8 values can change a
  walk, 1 is accepted but structurally unmatchable, 5 have no writer.
- Endpoints: in production every `src`/`dst` is an Eye address, but **nothing structurally requires
  it** — the schema is `src TEXT NOT NULL, dst TEXT NOT NULL` with no FK or CHECK. An injected
  non-event endpoint can be walked TO but not FROM (`trace()` refuses a non-address entry point
  with a 422).
- No dated receipt exists that the live edge table was ever populated; `eye.db` is gitignored.
  Best available mechanism: the schema-6 migration ran (`index.py:404` does
  `DELETE FROM ingest_state` and DROPs edges) and no `eye ingest` followed.

**So `fence` (the why) and `recall-firing` (what influenced it) are vocabulary with no producer.**
Two of the seven axes have a named edge type and zero edges. Half A's V2 — that the edge table
cannot hold a second node universe — stands, and is now stronger: it holds nothing at all.

## CORRECTION 2 — `session_id` is 0.82%, not 0.0%

My 2,000-event sample contained none of the filled rows. Measured over the **uncapped union** of
the file mirror and the Redis stream (20,208 events, zero unparseable lines):

- **165 of 20,208 = 0.82%.** On the Redis stream alone: 88 of 6,356 = 1.385%.
- **Binary by kind: 1 of 49 kinds carries it.** `session_signals` 165/165 (100%); all 48 others
  0.00%, including the five largest — `turn_metrics` 0/5,813, `boot` 0/2,849, `fail` 0/2,402,
  `learning` 0/1,971, `bifrost_msg` 0/1,273.
- By month it has never exceeded 1.3% and **fell** in the most recent: Jun 0.00%, Jul 0.61%,
  Aug 1.27%, Sep 0.71%.
- 165 events cover 109 distinct session ids — ~1.5 events per identified session out of 20,210.
- No hidden identifier exists elsewhere: 0 events with an empty `session_id` carry any `detail` key
  whose name contains "session". The 168 events whose refs start with `session:` are `session:start`
  / `session:end` only, not identity.

The conclusion is unchanged and the door signature is confirmed. **The count is the correction.**

---

## New evidence that bears on the design

### The write side, exactly counted

- **121 distinct call sites** invoke `capture()`/`capture_event()`: 49 production across 26 files,
  72 in tests. **Exactly 3 production sites pass `session_id=`**, all emitting `session_signals`:
  `agent/harness/dsh_plugin/bridge.py:398`, `agent/harness/hooks/claude_sessionend.py:166`,
  `scripts/hooks/claude_sessionend.py:166`.
- `session_id` is **KEYWORD_ONLY** with default `''`, and **zero call sites forward `**dict`** — so
  3 is complete, not a lower bound.
- **There is no canonical session-id accessor.** The idiom
  `os.environ.get("BIFROST_INCARNATION") or os.environ.get("CLAUDE_CODE_SESSION_ID")` is re-inlined
  in 5 production files, plus 3 divergent variants (`runner_lock.py:220` uses a different pair,
  `operator_reply.py:67` truncates to 8 chars, `agent_cli.py:6912` prefixes `args.session`). One
  concept, four mechanisms.
- Sampled 12 call sites for reachability. **Available-but-unpassed** dominates, and the strongest
  case is `agent_cli.py:4132` (the `note` verb, kind=`decision`): the door **has** a `--session`
  flag and the handler already uses `args.session` twice at :4102 and :4109, then omits it from the
  capture. Others: `claude_posttooluse.py:385` binds `sid` at :347 and uses it 8 lines *below* the
  capture; `actions.py:104` receives the session id as its first parameter. **Genuinely
  unavailable**: `core/narrative/session.py:38`, `core/comm/role_queue.py:166`. Partially:
  `reaper.py:272` holds only an 8-char discriminator.
- **Three writers bypass `capture()` entirely**: `core/recall/at_action.py:1035,1172` reach through
  the singleton to `ledger.emit` on their own streams; `scripts/ops/snapshot_knowledge.py:222`
  deletes every key then replays streams with raw `xadd`; `scripts/migrate_time_scores.py:75` writes
  the time index directly. A reader-side bypass too: `core/comm/doctor.py:1359` reads `events:raw`
  with a raw `xrevrange`.
- Two call sites pass a **dict where the signature expects `summary: str`** and no `agent_id`:
  `reaper.py:272`, `role_queue.py:166`. Neither kind has ever fired live (0 of 6,356), so the render
  is unverified.
- The hook files exist as **two diverged copies** under `scripts/hooks/` and
  `agent/harness/hooks/` — not identical twins — so 4 of the 49 production sites are logical
  duplicates that can drift.

### `refs` is the richest joiner, and it is DECAYING

- Non-empty on **7,108 of 20,208 = 35.17%** — and falling monotonically by month: **Jun 81.94% →
  Jul 43.76% → Aug 33.92% → Sep 22.26%.** A join surface that is getting worse, not static.
- Vocabulary resolves well where typed: lesson keys 969, Redis stream ids 854, `bifrost:*` 586,
  `mem:decision:<ADR>` 529, file paths 94, short hex shas 84.
- `agent_id` is 100% non-empty but **830 (4.11%) are the literal `"unknown"`** (capture()'s fallback
  at `event_log.py:139`), and the real-agent share declines over time.
- **There is no top-level `task` field at all** — 0 of 20,210. Only `detail.task`, on 15.55%,
  concentrated in `boot` (97.16%) and `handoff`.
- **No `--session` filter exists on the `events` read surface.** And the query layer's default scan
  cap is 20,000 — the corpus has just passed it (20,208).

### Commit SHAs: four planes, zero overlap, and my own rewrite orphaned most of them

- Exactly four planes carry a SHA. Together they name **880 of 2,728 HEAD commits (32.3%)**, and
  **all six pairwise overlaps are ZERO** — the union is exactly additive (697+93+89+1).
- The zero overlap is structural: all 721 `seats.jsonl` rows on HEAD are post-rewrite (100%
  rekeyed) while the other three planes hold **pre-rewrite** SHAs. My T411 rewrite tonight split
  the authorship plane from every other plane.
- Firehose: 57 of 6,372 events carry `detail.sha` (0.89%), all `command`. **Only 1 of 57 is
  reachable from HEAD (0.04%)** — 56 are orphaned objects. (The measuring agent's first probe used
  `cat-file -e` and reported 798 of 863 "resolve"; that proves object existence, not reachability.
  Corrected in place.)
- Every sha-bearing event was written by `agent_id='mirror'` — `scripts/mirror.py:_emit_commit_beat`
  (:483-505), inside mirror's own process. **A plain `git commit` emits nothing onto any plane.**
- Task ledger: 191 of 413 rows carry a commit (46.2%), but 30 hold the literal string `"HEAD"` and
  **19 closed with the placeholder `deadbee`/`deadbee1`** — the done gate accepts any 7-40 hex.
- **The lesson corpus carries ZERO commit anchors**: 0 of 1,514, and no `cites` field exists. 518
  have some anchor (443 path, 371 task, 7 atom, 0 commit).
- **Exactly ONE reader joins a SHA to another plane**: `scripts/authorship_ledger.py:seat_for()`.
  `core/recall/anchors.py:_commit_exists` is live code with **zero callers**. Everything else is
  display-only.
- **No post-commit hook exists.** `.git/hooks/` holds only `.sample` files; `core.hooksPath` points
  at `scripts/githooks` with pre-commit and commit-msg installed — and neither can know the SHA,
  because both run before git writes the object. `pre-push` is the only installed stage that could.
- `seats.jsonl` **cannot be regrown by its own `build` verb**: every HEAD commit now has the
  operator's email and `cmd_build` skips `if ae == OPERATOR`. Nothing automated writes it.

### The Eye: manual-only ingest, and a stale index

- **Ingest has no automatic trigger.** No Claude Code hook, no Windows scheduled task (all 14
  AkashicAurora tasks dumped; 9 actions scanned, none touch the Eye), no git hook. Manual-only via
  `eye ingest` or the MCP `ingest` tool, plus one indirect path: `reentry` calls `_EYE.ingest()` —
  **while `docs/DOORS.md:88` describes reentry as "READ-only"**.
- 27 ingest runs over the index's life. Gap p50 **8.54h**, p90 97.57h, **max 380h (15.8 days)**.
- At measurement the index was **40.78 hours stale** and held zero events after the last run.
- **The running session is entirely absent** — 0 rows, as are all 7 of its workflow subagents.
- `ingest_state` is **empty**, so the next run re-reads all 1,266 manifest files.
- `eye.db events.seat` is **NULL on all 48,702 rows** — the seat plane T407 shipped is unreachable
  by field. All 19 `seat:kimi` transcripts are absent from the index.
- Instrument defect worth knowing: **file mtime is not a content-recency proxy on this host** — 171
  of 1,240 transcripts have mtime >24h newer than their newest internal record (max 1,118h), so an
  mtime-based lag metric is contaminated. Content-based lag shows a **cliff at the last ingest**,
  not a distribution.

### THE SUBSTRATE FINDING — three live Stores holding the same keyspace, diverging

- **Three backends are live simultaneously**: Redis db0 (47,751 keys), SQLite
  `session_logs/store_state.db` (49MB + 4MB WAL), and a FileStore JSON echo.
  `AKASHIC_STORE_BACKEND=sqlite` was set in the measuring environment.
- **They diverge on every plane measured**: atoms 1,006 (Redis) vs 985 (SQLite); lessons 1,514 vs
  1,274; beats 4,378 vs 3,949; chapters 682 vs 672; `events:raw:byid` 9,470 vs 8,565.
- Not a stale-WAL artifact: the read-only SQLite connection sees today's writes (73 vs 73 keys with
  today's prefix) and both report the identical newest atom timestamp.
- **A third lesson population exists in Redis db13**: 1,228 `learn:experiment` keys. So the lesson
  plane has 1,514 / 1,274 / 1,228.
- **Read horizon**: the Redis `events:raw` stream's oldest entry is 2026-08-14, so **10,376 of
  19,884 file-mirror events (52.2%) are invisible to any read through the default ledger.** Not
  theoretical — the shipped read verb returns `[]` for June and July while the file mirror holds
  5 June and 120 July matching events.
- **The "durable" file mirror is not a superset**: 326 of 6,356 Redis rows (5.13%) have no twin in
  it, concentrated in Sep (210) and Aug (116).
- A **live cross-plane split-brain** was measured 2026-09-25 and is the subject of the newest open
  fence: the MCP door writes Redis 16381 (alpha) while the CLI reads 16379 (prod), so a `learn()`
  landed invisible to every seat.

### Plane-by-plane foreign keys (condensed)

- **Eye** carries **no typed foreign key to any other plane.** Other planes' ids appear only as free
  transcript text (1,106 rows contain `learn:experiment:`, 366 contain `ADR_`, 158 `art_2026`). The
  only typed inbound refs to Eye addresses live inside `eye.db` itself (`route_steps.target` 15 rows,
  `position.addr` 4).
- **Lessons**: id is the slugged experiment name alone — no date, seat or sequence. Typed FKs:
  `narrative_chapter` (655, all resolve), `related_to` (368, lessons only), `files_affected` (38).
- **Notes**: one Redis hash `mem:decisions`, 1,795 fields, id `ADR_<MMDDHHMMSS>_<hex4|hex8>` — **two
  id widths coexist**. Typed FKs: `supersedes` (601, all resolve) and `session_id` on **2 of 1,795**.
- **Atoms**: 1,006 across **three surfaces that are NOT in sync** (8 in Redis not in jsonl, 8 the
  reverse, 18 with no projection). Only typed link is `citations_out[] {rel,target}` and **every one
  of 837 targets is another atom** — an atom cannot typed-reference anything outside its own plane.
  `header.arc` is free-form, populated on 133, only 49 are T-numbers.
- **Chapters** are the widest joiner: `beats[]` 5,373, `learnings[]` 921, `commits[]` **860 bare
  shas with no prefix**. Two chapter id shapes run side by side.
- **Tasks**: typed FKs are commit, deps (8 entries, one of which is an atom id), files (171), owner.
  **No typed field for a lesson, atom, note, forecast, fence or drill.** 129 of 172 done rows have an
  empty `files` list.
- **Bus**: primary id is the packet sha256; only typed ref is `ids{}` lane→stream-id. Streams are
  bounded by design (maxlen 10,000).
- **Git**: after tonight's T411 rewrite there is a **single author identity across all 2,728
  commits**, so git can no longer distinguish who did what — that information now lives only in
  `seats.jsonl`. Commit messages are the most-used prose cross-reference: 1,607 cite a T-number,
  318 a W##, 31 an atom, 9 a lesson key.

---

## THE FINDING THAT MAY REFRAME YOUR ANSWER — this arc is the most-designed, least-built arc here

The prior-art lane's verdict, verbatim: *"The arc is NOT new. It is the single most-designed and
least-built arc in the house: 4 full reconciled/co-authored designs, 7 approved-but-unbuilt ledger
rows, 1 ratified doc door that was never wired, and 5 shipped partial organs."*

- **Daniel has restated this as his central want for over three months**, and the house records it
  as its **oldest unfiled wish**. W133/W134/W135 quote him on 2026-08-01: *"Our current method for
  finding out what links to what is too unintuitive and costly so it doesn't get done, THIS is the
  heart of what I am trying to fix."*
- **T092 the Reasoning Spine** — a 47,656-byte co-authored reconciled design with seven lettered
  laws. **Not built**; no `core/reason*` module exists.
- **T103 Super-wiki / Aurora Atlas** — a reconciled three-seat design for exactly this: *"a LENS
  SYSTEM over the atom graph"*, three hop planes (LOGICAL typed edges / THEMATIC / TEMPORAL),
  bidirectional backlinks. **Parked**, blocked on T101. The atom substrate it was to read **is**
  built (1,006 atoms, 837 typed edges, 0 dangling, O(1) inverse cited-by index with its own
  lie-detector) — but the typed-rel vocabulary it needed is effectively unused.
- **The arc's governing LAW was written 2026-07-30 and is unbuilt**: DERIVED / AUTHORED / OBSERVED
  planes under the rule *"the graph may join but never launder one into another"*, with a six-state
  trust ladder. **And its source note is GONE from the notes plane** — `note --get` refuses on both
  the title and the id. An instance of the exact loss this arc exists to prevent.
- **T323 "Routes as reified provenance"** — Daniel's words: *"a string through a forest you can walk
  with by hand so you dont need to re-discover relationships between different things."* Slice 1
  and its fidelity follow-on shipped. But `rootExhibitNumber`, its O(1) self-grounding field, has
  **zero occurrences anywhere in the Python tree.**
- **`LIBRARY.md` names four doors, and door 2 was never wired**: `arc <id>` — *"every brief, design,
  report, pin, commit, and lesson of an arc, in order ('trace our steps,' materialized)"* — exists
  as a standalone script and is not reachable from any door.
- **The `c-map-design` fence reconciled the cartography half and Daniel ratified it verbatim
  ("Lets build it").** Slice M1 shipped once (`state/map/index.html`, generated 2026-08-23) and
  stalled.
- **A hand-built instance of precisely the requested triangulation already exists and was never
  mechanized**: `research/in-flight/directive-arcs/LINEAGE-at-a-glance.md`, built by Navi
  2026-08-19, joining the ratified arc map (his words + timestamps) against the ledger.
- **T027 `lookback` is the shipped reader for the rationale leg** — and per brief §3.6 it returns
  nothing on two known-answer controls. Filed as **T412**.
- Seven approved-or-proposed rows are each a named leg of this arc with **no commit and no code**:
  T286 context-boundary topology, T287 provenance-confidence ladder, T288 citation-grade claims
  ("the connectome is the citation graph"), T322 ingress provenance, and others.
- **T374** — the two-store census plus mechanized reconciler, i.e. the *synchronisation* half of
  Daniel's ask — is `claimed` with no commit and no census artifact.

**Read that list against §2 of the brief before you write your design.** If your answer is a fifth
reconciled design, the evidence says it will join the other four. The question the evidence
actually poses may be *"why does this arc never get built, and what is the smallest thing that
breaks that pattern"* — and if you think so, say it as your framing verdict, which the brief told
you outranks everything else.

---

## Instrument defects found while measuring (each independently reproduced)

1. **`events --kind <K>` silently ignores `--kind`** on its default read path. `--kind
   session_signals --limit 25 --json` returned 25 rows of which **zero** were that kind. Filed as
   **T413**. Every census anyone has run through that flag is diluted.
2. **`lookback` returns nothing above the relevance floor** on two known-answer controls. **T412**.
3. `reentry` is documented READ-only (`docs/DOORS.md:88`) and writes the Eye index on every run.
4. `--formed-via text-identity` is offered by the CLI and can never match a step.
5. **The MCP door does not validate `formed_via`** — `ai_setup_mcp._run` builds an
   `argparse.Namespace` directly, so the CLI's `choices` check never runs; `'bogus'` and `'TRANSCRIPT'`
   both pass through. The MCP trace default depth is 0 → clamped to 1, versus the CLI's 6, so the
   same call returns a narrower walk through MCP.
6. `rg -U --multiline` returned **nothing, silently**, for a pattern with three real matches.
7. A repo-wide `rg` on `capture_event\s*\(` returns 2.9MB because
   `tmp/review/unify-diverged-hook-file-twins.fix.patch` holds single lines thousands of chars long.

## Stated limits of this annex

- **Which Store copy is canonical was not established.** `AKASHIC_STORE_BACKEND` was read from the
  measuring shell only; the live writers' environments were not enumerated. The divergence is
  measured; its direction is not.
- Whether the live `edges` table was **ever** populated cannot be established — `eye.db` is
  gitignored and no log records a non-zero count. The migration explanation is a mechanism, not a
  receipt.
- All commit fill rates are **HEAD-relative**; the 738 non-operator commits still visible via
  `git log --all` live on unrewritten side branches and were not analysed per-branch.
- Why 326 Redis rows lack a file twin is **unexplained** — `HybridLedger.emit` writes the file
  first and unguarded, so a file failure should abort before the Redis write.
