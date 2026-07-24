---
akashic_id: art_20260711_wave-3-deepseek-blind-half-rb-8-12-dicts_dc03b7
akashic_sha: 86a0da4d3706
status: draft
type: report
date: 2026-07-11
title: Wave 3 — DeepSeek blind half (RB-8..12 + DictStore differential)
gist: "Class: design + [verify] pre-registration Inputs: slice texts (docs/resilience-battery-slices-2026-07.md:136-188), Daniel's sprint briefing "
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_resilience-battery-sliced-execution-plan_8d660c
    rel: cites
created: "2026-07-11T05:17:35"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260711_wave-3-deepseek-blind-half-rb-8-12-dicts_dc03b7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Wave 3 — DeepSeek blind half (RB-8..12 + DictStore differential)

Class: design + [verify] pre-registration
Inputs: slice texts (docs/resilience-battery-slices-2026-07.md:136-188), Daniel's sprint
briefing (DictStore differential), seam evidence (agent_memory.py:122-157 decide/_retire,
store.py:180-199 cas/update_atomic, store.py:414-416 FileStore cas, agent_cli.py:1048-1120
cmd_note, _orientation_header:937-1009, cmd_notes:1140+), live receipt (tonight's twin
session — a real concurrent writer on this exact store).

---

## RB-8 — CAS on the note-supersession write (no fork under concurrency)

### The exact race

Two processes re-note the same title. Current flow (agent_cli.py:1053-1059 →
agent_memory.py:134-157):

```
P1: get_decisions() → finds "where-we-are" id=ADR_0701_1234
P2: get_decisions() → finds "where-we-are" id=ADR_0701_1234
P1: decide(supersedes="ADR_0701_1234") → hset ADR_0701_5678, zadd, retire ADR_0701_1234
P2: decide(supersedes="ADR_0701_1234") → hset ADR_0701_9012, zadd, retire ADR_0701_1234
```

Result: TWO active notes for "where-we-are" (ADR_0701_5678 and ADR_0701_9012), both
claiming to supersede ADR_0701_1234. The supersession chain forks. No error, no detection.

The twin session tonight was this exact race — two Claude sessions, one repo, simultaneous
notes. Wave 3 owns the write half of that incident.

### Fix mechanism

A per-title sentinel key (`mem:title:{normalized_title}`) that atomically tracks the
current head id. The Store's existing `update_atomic` (store.py:193-205) gates the
supersession write:

In `decide()` (agent_memory.py), after writing the new record and index:

```python
if supersedes:
    sentinel = f"mem:title:{normalize(title)}"
    def _claim(current: str | None) -> str | None:
        if current == supersedes or (current is None and supersedes is None):
            return dec_id          # we own the title
        return None                # lost the race — someone else's id is there

    result = self.store.update_atomic(sentinel, _claim, retries=1)
    if result == dec_id:
        self._retire_record(self.KEY_DECISIONS, supersedes)
    else:
        self._retire_record(self.KEY_DECISIONS, dec_id)   # clean up our record
        raise SupersedeRaceError(
            f"Lost title race for '{title}'; current head is {result}")
```

`cmd_note` catches `SupersedeRaceError`, re-reads decisions to find the winner's id,
and retries the full `decide()` call with the corrected `supersedes` pointer.

**Why `update_atomic` with retries=1, not a raw `cas` call:** `update_atomic` handles the
get-then-cas cycle with the built-in conflict loop. We use retries=1 because we WANT to
detect the race and bounce to the caller — the retry belongs at the cmd_note level where
we re-read decisions. A retry loop inside decide() would re-`_gen_id` and re-write the
body on every conflict, which is wasteful when the body is unchanged.

**Why the sentinel is a separate key, not folded into the decision hash:** The decision
hash (`mem:decisions`) maps id→json and is unsuited for CAS on title identity. A
dedicated key per title gives us a clean CAS target with no hash-structure interference.

### Keys touched

- `mem:title:{normalized_title}` — NEW, per-title sentinel (kv, not hash)
- `mem:decisions` (hash) — existing decision records
- `mem:decisions:idx` (zset) — existing index

### Pinned regression asserts

1. Two concurrent `decide()` calls for the same title with the same `supersedes` → exactly
   one active note survives; the loser's record is auto-retired.
2. Two concurrent FIRST-notes (supersedes=None for both) for the same title → exactly one
   active note; the sentinel creation (`cas(key, None, val)` → nx=True) gates first-note
   as well as re-note.
3. Uncontended write → no retries, no spurious race detection, same latency as today + 1
   additional Redis round-trip (the sentinel CAS).
4. The superseded chain is LINEAR: note C supersedes note B supersedes note A; never two
   notes both claiming to supersede A (the fork this slice closes).

### Cost on the hot path

- +1 `get` + 1 `cas` per `decide()` call (the `update_atomic` internals). For RedisStore
  that's +2 round-trips (~2ms on localhost). For FileStore it's under the existing lock.
- On actual contention: +1 extra `get_decisions()` call + 1 retried `decide()` for the
  loser. Contention is rare (notes are human-paced), so the amortized cost is negligible.

### Failure modes of the fix

- **FM1 — Orphaned sentinel (crash between hset and sentinel CAS):** If the process dies
  after writing the decision record but before the sentinel CAS, the new note exists but
  the sentinel still points at the old id. → A subsequent re-note would supersede the old
  id, missing the intermediate note. The intermediate note remains active and creates a
  fork. Mitigation: a repair scan at boot (`doctor`) that walks `mem:title:*` sentinels
  and reconciles against `mem:decisions` — any decision with a title whose sentinel
  doesn't point to it (and which is not superseded) is a detected orphan.
- **FM2 — Sentinel key drift from reality:** An operator manually deletes a decision
  record via Redis CLI but leaves the sentinel. → The sentinel points to a missing id;
  the next re-note's CAS would compare against a stale pointer. Mitigation: `decide()`
  verifies the sentinel's current value actually exists in `mem:decisions` before
  accepting it as the CAS expected value; if it's a dangling pointer, treat as None.
- **FM3 — Store doesn't support CAS (hypothetical backend):** The `update_atomic` default
  fallback is a non-atomic get-then-set. Under genuine concurrency this can still fork.
  → Document that RB-8 requires an atomic CAS backend; log a warning at store init if
  the backend is the default non-atomic fallback.

---

## RB-9 — Title normalization at the single write door

### The exact race/fault

Titles are compared with `==` (agent_cli.py:1053: `if d.title == title`) with only a
length clip. A trailing space (`"where-we-are "`), a Unicode look-alike (Cyrillic 'е'
for Latin 'e'), or different Unicode normalization forms (NFC vs NFD) mint silent
sibling notes — same semantic title, two independent records, two independent
supersession chains. No error, no detection.

### Fix mechanism

Normalize ONCE at the write door, centralized in `agent_memory.decide()`, BEFORE the
title touches any comparison or storage:

```python
import unicodedata

def _normalize_title(title: str) -> str:
    return unicodedata.normalize("NFC", title).strip()
```

Called at the top of `decide()`. The stored `Decision.title` is the normalized form.

**Read side also normalizes:** In `cmd_note` (agent_cli.py:1053), the comparison becomes
`if _normalize_title(d.title) == normalized_lookup_title` — so re-notes of existing
un-normalized titles (from before RB-9) still match. The stored title stays as-is for
archaeology; normalization on read catches it.

### Keys touched

None new. `mem:decisions` hash fields — the stored `title` value within each decision
JSON changes for new writes (normalized form); existing records are untouched.

### Pinned regression asserts

1. `decide(title="where-we-are ")` and `decide(title="where-we-are")` produce the same
   stored title and the second supersedes the first.
2. NFC vs NFD: `decide(title="café")` (NFC 'é' as one codepoint) and the NFD equivalent
   ('e' + combining acute) produce identical stored titles.
3. A pre-RB-9 note with a trailing space in its title is still found by a re-note with
   the clean title (read-side normalization bridges the gap).
4. Titles that differ ONLY in case are NOT merged — case normalization is NOT applied
   (Python `str.strip()` preserves case; `unicodedata.normalize("NFC", ...)` is
   case-preserving). Case is semantically meaningful in English titles. If this becomes
   a problem, a separate RB can add case-folding with a dated allowlist of exceptions.

### Cost on the hot path

- `unicodedata.normalize("NFC", ...)` is O(n) on title length, single digit microseconds
  for titles <200 chars. Negligible.
- Read-side normalization: applied per-decision in the comparison loop inside cmd_note
  (~30 active notes). O(30) × microseconds ≈ negligible.

### Failure modes of the fix

- **FM1 — Normalization collision (two distinct titles normalize to the same string):**
  Extremely unlikely with NFC+strip alone (no case-folding, no whitespace collapsing).
  If it happens, the second write supersedes the first — which is arguably correct
  behavior for genuinely identical normalized forms. The collision is visible in the
  superseded chain.
- **FM2 — Pre-RB-9 collisions surfaced late:** Existing titles that normalize to the
  same string but were stored before RB-9 will appear as two notes of the same title
  after read-side normalization kicks in. Both would appear as "active" (neither
  superseded the other at write time). → RB-10's all-retired-title detector catches
  these; a one-time doctor scan at RB-9 deploy lists them for manual resolution.

### Rule: write-only or read-too?

**Both.** Normalize at the write door (canonical storage) AND normalize on read-side
comparisons (backward compatibility bridge). This is the only safe combination —
write-only leaves existing un-normalized titles invisible to their corrected re-notes;
read-only leaves future writes still capable of minting near-duplicates.

---

## RB-10 — Supersede-target validation + all-retired-title detector

### The exact faults

**Fault A — Blind supersede target:** `decide(supersedes="ADR_nonexistent")` writes the
new record, then `_retire_record` (agent_memory.py:126-132) does `hget(key, record_id)`
→ returns None → no-op. The new record's `supersedes` field points to a ghost. No error,
no warning. Similarly, `supersedes` pointing at the same id as the new record
(self-supersede) would be nonsense but passes silently.

**Fault B — Vanished title group:** If every record of a title is retired (either
through normal re-notes or manual `--retire`), `get_decisions()` filters them all out
and returns nothing for that title. The title group vanishes silently from boot, notes,
and memory.md — no indication it ever existed. An operator retiring the last note of
"where-we-are" would see the boot header just... drop the line, with no explanation.

### Fix mechanism

**Part A — Validate before write.** In `decide()`, when `supersedes` is given:

```python
if supersedes:
    if supersedes == dec_id:
        raise ValueError(f"Cannot supersede self: {supersedes}")
    existing = self.store.hget(self.KEY_DECISIONS, supersedes)
    if not existing:
        raise ValueError(f"Supersede target not found: {supersedes}")
```

This runs BEFORE the hset/zadd of the new record, so a bad target fails cleanly
before any state is mutated.

**Part B — All-retired-title detector.** A new method on AgentMemory:

```python
def get_retired_titles(self) -> List[dict]:
    """Return titles whose every record is retired (vanished groups).
    Each entry: {title, last_active_id, retired_count, last_retired_at}."""
```

Implementation: scan ALL decisions (include_superseded=True), group by normalized
title, and find groups where `all(d.superseded for d in group)`. Return these as a
list. Called by:
- `cmd_notes` (with `--all` flag or as a footer line)
- Boot header: "N retired title groups: ..." if any exist
- `doctor` output

The default `get_decisions()` continues to filter out superseded records (no behavior
change) — the detector is a SEPARATE surface, not a change to the default read path.

### Keys touched

- `mem:decisions` (hash) — read for validation, read for detector scan

### Pinned regression asserts

1. `decide(supersedes="ADR_nonexistent")` → raises ValueError, no record written.
2. `decide(supersedes=self_id)` → raises ValueError before write.
3. Retiring every note of a title → `get_retired_titles()` includes that title;
   `get_decisions()` returns empty for it (no behavior change).
4. A title with at least one active note → NOT in `get_retired_titles()`.

### Cost on the hot path

- Part A: +1 `hget` per `decide()` call with supersedes. Negligible (~1ms Redis).
- Part B: scan of all decisions (active + superseded) — O(n) where n is total notes
  ever written (currently ~30). Called at boot time and `notes --all`, not on the hot
  path. Acceptable.

### Failure modes of the fix

- **FM1 — Detector produces false positives on freshly-retired-but-about-to-be-replaced
  titles:** The window between retirement and replacement is usually zero (happens in
  the same `decide()` call). But if someone manually `--retire`s a title's last note
  without writing a replacement, the detector correctly flags it. Not a false positive.
- **FM2 — Detector scan cost grows unbounded:** All decisions ever written are scanned.
  At ~30 notes this is trivial. At 10,000 notes, a full scan at every boot is
  unacceptable. → Cap the scan to a lookback window (90 days) matching `get_decisions`
  default; notes older than the window that are all-retired are "cold vanished" and
  surfaced only with `--all`.

---

## RB-11 — Migration idempotency pin + chain-length warning

### The exact faults

**Fault A — Migration double-run:** If the notes migration script is run twice, does it
idempotently no-op or does it duplicate/overwrite state? The existing migration (if any
exists — check `scripts/` or migration paths) lacks an idempotency pin: a marker that
says "migration X already ran, skip." A double-run is plausible during deployment
retries or recovery.

**Fault B — Unbounded superseded chain:** A title like "where-we-are" re-noted daily
for 2 years accumulates 730 retired records — every one is kept for archaeology. No
warning, no visibility. The chain grows silently forever, increasing scan cost for
`get_decisions(days=3650, include_superseded=True)`.

### Fix mechanism

**Part A — Idempotency pin.** Add a migration tracking key to the store:

```
mem:migration:{migration_name} → "done" + timestamp
```

The migration script checks this key before running. If present, skip. If absent,
run migration, then set the key. Uses `cas(key, None, "done")` so two concurrent
migration attempts don't both run.

**Part B — Chain-length warning.** In `get_decisions()` (or a separate check called
at boot), when `include_superseded=True`, group decisions by normalized title and
count superseded records per title. If any title's superseded chain exceeds N
(default: 50), emit a WARNING log: "Title '{title}' has {count} retired records
(chain length > {N}); consider archiving old records."

Not a hard cap — just visibility. The operator decides whether to trim (a `--prune`
verb or manual Redis cleanup, out of scope for this RB).

### Keys touched

- `mem:migration:*` — NEW, migration tracking keys (kv)
- `mem:decisions` (hash) — read for chain-length scan

### Pinned regression asserts

1. Migration script run twice → second run is a no-op; store state unchanged from first.
2. Title with chain length = N → no warning at N-1, warning at N+1.
3. Warning includes the title name, count, and threshold for operator action.
4. Chain-length check does NOT slow down the default `get_decisions()` path
   (include_superseded=False is the common case).

### Cost on the hot path

- Migration idempotency: checked once at migration time, not on the hot path.
- Chain-length warning: only when `include_superseded=True` or at boot. Boot already
  reads decisions for RECENT NOTES; grouping by title and counting is O(n) extra work
  on ~30 notes. Negligible. At scale (thousands of notes), the scan should be
  time-bounded (90 days).

### Failure modes of the fix

- **FM1 — Migration pin key is deleted accidentally:** Someone runs `store.delete("mem:migration:*")`
  → next migration run would re-execute. Mitigation: the migration itself must be
  idempotent (tolerates re-run even without the pin). The pin is a performance
  optimization, not the sole safety mechanism.
- **FM2 — Chain-length warning becomes noise:** Every project hitting 50+ daily wraps
  sees the warning on every boot; operators tune it out. → Make the threshold
  configurable via the manifest (T034 pre-work); default 50 is a reasonable start.
- **FM3 — Chain-length scan at boot grows with total notes:** Same mitigation as
  RB-10 FM2 — time-bound the scan to a rolling window.

---

## RB-12 — Deterministic ordering + graceful empty-state at boot

### The exact faults

**Fault A — Unstable tiebreaker.** `get_decisions()` sorts by `created_at` descending
(agent_memory.py:187). When two notes share the exact same `created_at` (same-second
writes from concurrent sessions — the twin incident again), Python's `list.sort()` is
stable but the input order from `zrangebyscore` is non-deterministic (same-score
members in a Redis zset are ordered lexicographically by member, but the member is the
decision id which is random). Every boot could pick a different "newest" note in a tie.

**Fault B — Governing-arc selection instability.** `_orientation_header`
(agent_cli.py:~990) selects the governing arc from `*-status` notes. The selection
already has a two-tier priority (active-task match > newest-with-doc), but within the
same tier, ties are unstable.

**Fault C — Empty-state crash or wrong output.** If zero `where-we-are` notes exist
(all retired, or fresh install), the boot header and memory.md projection must render
a gap line, not crash or print a confidently-wrong line. The existing code has
try/except blocks (the header already fail-opens), but the specific `where-we-are`
line in the RECENT NOTES section may not handle empty gracefully.

### Fix mechanism

**Part A — Deterministic second sort key.** In `get_decisions()`, change the sort:

```python
decisions.sort(key=lambda x: (x.created_at, x.title, x.id), reverse=True)
```

Three-level sort: created_at (primary) → title (secondary, alphabetical) → id
(tertiary, the `ADR_MMDDHHMMSS_RRRR` id). This is fully deterministic — id is
globally unique, so ties are impossible past the tertiary key. The title as secondary
key gives a human-meaningful tiebreaker before falling back to the opaque id.

**Part B — Governing-arc tiebreaker.** In `_orientation_header`, after building
`candidates`, add a deterministic secondary sort: by doc path (alphabetical). The
existing `next((c for c in candidates if c[0]), None)` already picks the first
matching candidate; with a pre-sorted candidate list, this becomes deterministic.

**Part C — Graceful empty-state.** In `_orientation_header`:
- The `where-we-are` line: if `get_decisions()` returns no `where-we-are` note →
  render: `# where-we-are: (no note yet — record one with `agent_cli note`)`
- The governing arc line: if no candidates → render: `# Governing arc: (none — no active
  arc status notes)`
- The RECENT NOTES section: if zero notes → render: `# (no durable notes yet)`

In `project_notes()` (memory.md generation): if zero items → render `_(no notes yet)_`
(which the existing code at agent_cli.py:945 already does — verify this path works
with an empty get_decisions()).

### Keys touched

None new. Changes are in sort logic and render paths.

### Pinned regression asserts

1. Two notes with identical `created_at` → `get_decisions()` returns them in the same
   order every call (title-then-id tiebreaker is deterministic).
2. Two `*-status` notes with identical timestamps and both matching an active task →
   same governing arc selected every boot.
3. Zero notes in store → boot header renders gap lines, no crash, no exception.
4. Zero `where-we-are` notes → boot header shows the gap line, not a stale or wrong
   line.

### Cost on the hot path

- Sort key tuple: `(created_at, title, id)` instead of single `created_at`. The tuple
  construction is O(1) per item; sort is still O(n log n). No measurable difference
  for ~30 notes.
- Empty-state checks: one extra conditional per render path. Negligible.

### Failure modes of the fix

- **FM1 — Title-as-tiebreaker surprises:** Two notes "AAA-status" and "ZZZ-status" with
  same timestamp — "AAA-status" always wins. If the operator expected newest-by-some-
  other-metric, this is surprising. → Document the sort order in the boot header
  comment so the rule is visible.
- **FM2 — Gap line is mistaken for a real status:** The gap line `"(no note yet)"` is
  clear, but an operator skimming boot might miss it. → Use a distinct prefix like
  `"[GAP]"` to make it visually scan-different from real data lines.
- **FM3 — Governing-arc tiebreaker still unstable across different stores:** If
  RedisStore and FileStore return zset members in different orders for same-score
  entries, the pre-sort in `get_decisions()` fixes this for decisions, but the
  governing-arc selection happens in `_orientation_header` which calls
  `get_decisions()` — so it inherits the fix. No separate instability.

---

## DictStore differential

### Harness shape

A new test class: `tests/test_store_differential.py`. It takes a sequence of Store
operations expressed as a list of call dicts:

```python
Op = dict  # {"method": "hset", "args": [...], "kwargs": {...}, "expect": ...}
```

The harness:
1. Creates an in-memory `DictStore` (a NEW Store subclass — minimal, no file I/O,
   pure Python dicts under the existing Store ABC).
2. Creates a `RedisStore` connected to a test Redis instance.
3. Runs the exact same `Op` sequence against both.
4. After each op, asserts the return value matches between the two stores.
5. After the full sequence, asserts `keys("*")` returns identical sets, and a full
   state dump (`hgetall`, `zrange`, etc.) is identical.

If Redis is unavailable, the test is skipped with `pytest.skip("Redis not available")`.

### Where it lives

`tests/test_store_differential.py` — a pytest file, runnable in CI. Not a standing
guard (it requires a live Redis), but a gate that runs when Redis is present.

### DictStore implementation

A new class `DictStore(Store)` in `core/foundation/store.py`. It is a pure in-memory
implementation with the same semantics as `RedisStore`:
- All data in Python dicts (kv, hash, list, set, zset)
- No file persistence (unlike FileStore)
- Thread-safe via `threading.RLock` (like FileStore)
- `cas` is atomic under the lock (like FileStore's implementation at :414-416)
- `zadd`, `zrangebyscore` use sorted lists or dicts with score as key
- No TTL expiry (or lazy expiry like FileStore)

### Which ops matter most (given the seams)

1. **`hset` / `hget` / `hgetall`** — decision CRUD. The core of agent_memory.
2. **`zadd` / `zrangebyscore`** — decision indexing and time-range scans.
3. **`cas` / `update_atomic`** — the concurrency primitive (RB-8's sentinel). THE
   critical op for correctness. If DictStore's `cas` behaves differently from
   RedisStore's Lua `cas`, RB-8 breaks.
4. **`get` / `set` / `delete` / `exists`** — basic kv ops, sentinel keys.
5. **`keys`** — key scanning (doctor, repair scans).

### Divergence detection

The harness doesn't just compare final state — it compares RETURN VALUES after each
op. Redis `hset` returns the number of NEW fields added; DictStore must match this
exactly. `zadd` returns the number of new members. `cas` returns True/False.

Divergence IS the finding — the test fails if ANY op returns a different value or
if final state differs. This catches semantic drift between the two backends before
it reaches production.

### Pinned regression asserts

1. Identical op sequence against DictStore and RedisStore → identical return values
   for all ops, identical final state.
2. `cas` semantics: `cas(key, None, "val")` succeeds on first write, fails on second
   (nx=True behavior) — both stores agree.
3. `zrangebyscore` with score ranges: identical member ordering for same-score members
   (lexicographic by member — Redis's documented behavior, DictStore must match).
4. `hset` return value: count of NEW fields (not updated fields) — both stores agree.

---

## What I would NOT build (cut list)

1. **Automatic title collision resolution at RB-9 deploy time.** Don't auto-merge
   existing near-duplicate titles. Surface them via RB-10's detector and let the
   operator decide. Auto-merge is too aggressive for data we can't fully inspect.
2. **Chain pruning at RB-11.** Don't add a `--prune` verb or auto-deletion of old
   retired records. The warning is sufficient; pruning is a policy decision best
   made with human judgment.
3. **DictStore TTL/expiry.** DictStore should reject or no-op TTL operations
   (setex, expire, ttl) rather than implementing lazy expiry. TTL is not used in
   the decision/note paths this wave touches; implementing it expands scope
   unnecessarily. If a differential test needs TTL, it should be a separate test
   file.
4. **RB-8 sentinel repair at boot (v1).** The orphaned-sentinel repair scan (FM1)
   is correct to design but should be a `doctor` check, not an automatic repair at
   boot. Automatic repair of drift is itself a risk — surface the finding, let the
   operator run the repair explicitly.
