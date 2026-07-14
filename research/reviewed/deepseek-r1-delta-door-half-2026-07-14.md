# DeepSeek R1 Delta Door — Design Half (blind, 2026-07-14)

Status: BLIND half (M1 full fence; do not read claude's half until mine is committed)
Tier: FULL FENCE (M1-LITE gate 1a: new coordination-adjacent capability)
Confidence tags: CERTAIN / DESIGN / INFERRED / UNCERTAIN per M1-CF
Inputs: as listed in research/r1-delta-door-design-brief-2026-07-14.md §(2)

---

## REFUTE-FIRST: candidates considered and rejected

### R1. Store key with a JSON blob of positions
**Rejected.** CERTAIN. The Store is a flat key-value surface; a JSON blob would need
read-modify-write for every field update, which means either full-blob CAS (non-atomic
across fields) or accepting races. The lane cursor hash pattern (Redis HSET per field,
guarded by advance_cursor_fields Lua) already solves multi-field position tracking
with per-field atomic advances and generation fencing. A new flat key would duplicate
all of that worse.

### R2. Per-turn mark advance
**Rejected.** CERTAIN. If the mark advances after every drain, the delta shrinks to
"what happened in the ~10 seconds since your last tool call." The agent's OWN actions
(the files it read, the notes it wrote) pollute the delta. The mark must advance at
BOOT time — before the agent acts — so the NEXT boot sees only what happened BETWEEN
sessions. Per-turn is also wrong for the session-consume leg: a session door's consume
would advance the mark, making the runner's next boot miss everything the session saw.

### R3. Git-only high-water mark
**Rejected.** CERTAIN. The wishlist mandate (S1) explicitly calls for "last-seen
commit + ledger revision + bus cursor(s) + note versions." Git alone covers exactly
one of four sources. An agent that only knows the commit range still burns tool calls
on `task list` diffing and `bifrost-sync` archaeology. The mark must span ALL sources
or the delta is incomplete and the archaeology tax moves, not shrinks.

### R4. Mark lives in a knowledge_note
**Rejected.** DESIGN. A knowledge_note is write-once with supersession — reading the
"current" mark requires scanning titles and decoding content. The lane cursor hash is
a named, structured, per-agent Redis key with exactly six fields and atomic advance.
Notes are human-readable prose; the mark is machine-compared positions. Mixing them
would create a parse-contract between the mark writer (boot harness) and the delta
renderer — fragile and untyped.

---

## DECISION 1: the high-water mark — what it records, where it lives, when it advances

### D1a. WHAT the mark records (six positions)

| Field | Source | What it means |
|-------|--------|---------------|
| `git_commit` | `git rev-parse HEAD` | Last-seen commit SHA |
| `ledger_rev` | task ledger format_state() checksum or seq | Last-seen ledger revision |
| `notes_head` | AgentMemory: highest supersession chain head across decisions+experiences | Last-seen note version (any title supersession advances this) |
| `inbox` | shared cursor inbox position | Last-seen legacy inbox (for agents still on the shared cursor during strangler) |
| `bc` | shared cursor bc position | Last-seen legacy broadcast |
| `lane_hash` | lane cursor hash fingerprint (all six fields) | Last-seen lane cursor state — a single compound fingerprint |

**CERTAIN** (citation-grounded to existing seams):
- `git_commit`: `subprocess.run(["git", "rev-parse", "HEAD"])` — the same pattern
  `scripts/deepseek_chat.py:_git()` already uses (line ~365).
- `ledger_rev`: `core/coord/task_ledger.py` has a `_seq` counter (line ~87) and a
  `format_state()` render; a revision is either the seq number or a hash of the
  serialized task dict. Prefer seq — it's monotonic, cheap, and the ledger already
  maintains it.
- `notes_head`: `core/learning/agent_memory.py` stores decisions and experiences in
  Redis hashes with `supersedes` pointers (line ~93, ~167). The "head" of the chain
  is the record with `superseded=False` for the most-recently-created timestamp.
  Read: `get_decisions(days=N)` + `get_experiences(days=N)`, take the max `created_at`
  or a concatenated fingerprint of all active titles+created_at values.
- `inbox`/`bc`: `core/comm/bus.py` shared cursor via `bus.cursor()` or `bus._read_cursor()`
  (line ~652 pattern — `_read_cursor` returns the shared hash).
- `lane_hash`: `bus.read_lane_cursor()` returns all six fields (`core/comm/bus.py:681-686`).
  Hash them together (SHA-256 of the concatenated field values) into a single fingerprint.
  This captures all lane-cursor state in one comparable value — a lane advance on ANY field
  changes the fingerprint.

**Why six and not more:** the wishlist's S1 mandate names four categories (commit, ledger,
bus cursor, notes). The bus cursor splits into shared + lane because the strangler is live:
legacy-path agents track the shared cursor; lane-mode agents track the lane fingerprint.
When the strangler retires (T047), `inbox`/`bc` drop and the lane_hash becomes the sole
bus position. Notes are versioned by supersession — a single "head" fingerprint captures
all note changes without enumerating titles.

**Why not include:** file modification times, Store keys, presence roster, lock table.
The delta door is NOT a full system diff — it is "what should I pay attention to since I
was last here." Files changed are surfaced via the git range (commits touch files); Store
keys are internal state; presence and locks are live queries, not deltas (query them on
demand, they don't benefit from a mark). Adding more fields increases false-positive
delta noise — every Store key touch would flag the delta, and the agent would learn to
ignore it. The mark must be the MINIMAL set that eliminates archaeology.

### D1b. WHERE the mark lives

The mark lives in a NEW lane-cursor-style Redis hash:

```
{ns}:delta:mark:{agent}
```

Fields: `git_commit`, `ledger_rev`, `notes_head`, `inbox`, `bc`, `lane_hash`.

**CERTAIN.** This pattern already exists: `bus.lane_cursor_key()` returns
`"{ns}:cursor:lane:{agent}"` (`core/comm/bus.py:667-675`). The delta mark key follows
the same `{ns}:delta:mark:{agent}` convention. The lane cursor hash has six fields
advanced atomically via `advance_cursor_fields` with a Lua guard (`core/comm/bus.py:644-665`).
The delta mark uses the SAME pattern: an HSET key with per-field values, written atomically
at boot time via a store.set() (no guard needed — the mark is boot-owned, not contended).

**Why Redis and not Store:** the Store is a general-purpose key-value surface with
optimistic concurrency (CAS). The delta mark is an agent-owned, boot-written, read-only-
by-others structure — no CAS needed, no contention. Redis HSET is the right primitive:
atomic multi-field write without a Lua script, and the lane cursor already proves the
pattern works.

**Why not the lane cursor hash itself:** the lane cursor tracks CONSUMPTION progress
(advances on every drain). The delta mark tracks AWARENESS (advances once at boot).
Mixing them would mean a drain that moves the cursor also moves the delta baseline,
which is D1c's rejection of per-turn advancement. Separation of concerns: cursor =
what I've consumed; mark = what I knew at boot. They serve different consumers (the
drain loop vs the delta renderer) and advance on different schedules.

### D1c. WHEN the mark advances

**At boot, BEFORE the agent's first tool call, and NOT during the session.**

Concretely: the boot assembly (`agent/harness/context.py:build_autoboot_context` or its
full-boot counterpart) reads current positions, writes the mark, THEN injects the delta
into the boot context. The agent's own session never touches the mark.

**CERTAIN.** Advancing at boot means:
- The NEXT boot sees everything that happened AFTER this boot (including this session's
  own outputs — which is correct: "what did Claude do while I was gone" includes Claude's
  commits and notes).
- The agent's own tool calls during the session do NOT advance the mark (= no self-
  pollution of the delta).
- The session-consume leg (which also boots) gets its own mark; the runner's next boot
  sees the session's effects too.

The boot assembly already has access to all six position sources: git (subprocess),
ledger (import `TaskLedger`), notes (import `AgentMemory`), cursors (import `Bus`). The
mark write is one additional `store.hset()` call at the end of the boot assembly, after
all position reads.

**What about a crash during boot?** If the mark is written but the agent never acts,
the delta is "empty" on next boot — the positions haven't moved. That's harmless: an
empty delta is one line ("no changes since your last boot"), not a error. The mark
doesn't need to be rolled back on boot failure.

**What about twin sessions?** Two runners for the same agent boot simultaneously. Both
read positions, both write the mark. The second write overwrites the first. The delta
on the NEXT boot uses whichever mark survived — either is a valid snapshot of "what
the agent knew at its last boot." The mark is a fuzzy high-water mark, not a
transactional checkpoint — twin sessions are a rare edge case and the worst outcome is
a slightly larger delta (the earlier session's mark leads to more "new" items on next
boot — all of which ARE new to the later-session runner). Harmless over-delivery.

---

## DECISION 2: the RENDER — what `delta <agent>` shows

### D2a. FORMAT: one block per moved source

```
delta deepseek  (since 2026-07-14 08:22 UTC, commit 9f7a72d → c9d511b)

  git:     3 commits by claude
           c9d511b T049 fence-protocol v2 MERGED
           83677cb T045 wiring-fence report filed
           ec802c4 T049 fence-protocol v2 MERGED into method baseline

  ledger:  2 transitions
           T045 in_progress → done
           T049 verifying → done

  notes:   1 updated
           "where-we-are" superseded 2026-07-14

  bus:     1 promoted message
           [decision] claude → *: T049 fence ratified by Daniel directive

  lane:    3 advances (inbox +2, sig_inbox +1)
```

**DESIGN.** The format is a structured block, not a narrative. Every source that moved
gets a section. Sources that didn't move are OMITTED (silence = no news — the agent
skips scanning empty sections). The header line anchors the delta in time and commit
range so the agent knows its baseline without checking the mark.

### D2b. SIZE BUDGET

The delta block has a DECLARED budget of 1200 characters. If the full render exceeds
it, the renderer:
1. Caps each section to its proportional share of the remaining budget.
2. Truncates the longest section last.
3. Appends a PULL POINTER: `[delta truncated: 3 more commits, 1 more note — full
   delta: py agent_cli.py delta deepseek --full]`

**DESIGN.** This is the packet law (T043) applied to boot context: "never silently
truncated." The 1200-char budget is chosen because the boot context already has a
token budget; the delta block replaces the archaeology sections (see D3) and must
fit within what it displaces. The pull pointer follows the same pattern as the
recall-at "X more" pointer — one command to get the full delta.

**Why not a token budget:** the boot assembly works in characters, not tokens. A
token-accurate count requires a tokenizer matching the model in use — the harness
doesn't have one. 1200 characters is ~400 tokens for most models, which is
proportional to the archaeology it replaces (the "where-we-are" note +
ledger block + "recent notes" block in my current boot is roughly that size).

### D2c. PER-SOURCE RENDER DETAIL

**Git:** `git log <last_commit>..HEAD --pretty=format:"%h %s" --max-count=12`. If
the range is empty (same commit), omit the section. If the range is backwards
(rebase/rollback — see D5), render: `git: HEAD moved backwards (c9d511b → 9f7a72d);
3 commits were rebased out. Range: py agent_cli.py git-log 9f7a72d..c9d511b`

**Ledger:** compare `format_state()` before/after. Render each transition as
`<task_id> <old_status> → <new_status>`. If the ledger has no seq field, compute a
fingerprint of the serialized task dict and compare. Only show transitions (status
changes), not tasks that stayed in the same state.

**Notes:** compare `notes_head` fingerprint. If different, query which titles have
newer `created_at` values than the mark timestamp. Render: `N updated:` followed by
titles. Never render note bodies — the delta is a scan, not a read; the agent drills
into specific notes with `knowledge_recall`.

**Bus (promoted):** compare the `lane_hash` or `inbox`/`bc` positions. If the lane
advanced, query promoted events between the old and new positions. Render: `N promoted
message(s):` with one-line summaries. Only SALIENT kinds (handoff/decision/completion/
blocker) — the promoter (`core/comm/promoter.py:21`) already classifies these.

**Lane:** the lane_hash fingerprint comparison. If different, render the per-field
deltas as human-readable counts: "inbox +2, sig_inbox +1" etc. The lane hash itself
is opaque — the render decompresses it into readable field deltas.

---

## DECISION 3: BOOT/WAKE integration — what the delta replaces

### D3a. BOOT: the delta REPLACES the archaeology sections

Currently, my boot context has:
- "CURRENT DIRECTIVE" — keep.
- "where-we-are" block — **REPLACED by delta.ledger** (the transitions ARE what
  happened).
- "RECENT NOTES" — **REPLACED by delta.notes** (supersessions ARE the recent note
  activity).
- "ARCH SLICE" — keep (static, doesn't change between boots).
- "LESSONS / CONTEXT" — keep (knowledge injection, not archaeology).
- "RECENT DECISIONS" — **REPLACED by delta.bus** (promoted messages ARE the recent
  decisions that survived the bus).

The delta block is injected at the TOP of the boot context, right after the door
contract (AGENTS.md reference), as a compact "Since your last boot:" section. The
displaced sections are DROPPED from the boot entirely when a delta mark exists (=
returning agent). A newborn agent (no delta mark) gets the full boot — the delta is
an optimization for continuity, and continuity requires a prior boot.

**DESIGN.** The boot shrink is roughly: -800 chars of archaeology, +300 chars of
delta. Net savings: ~500 chars per boot for a returning agent. Over 10 boots/day,
that's 5000 chars the agent doesn't re-read stale information.

### D3b. WAKE: the wake report gains a delta line

Currently, the wake listener arms, detects mail, and the runner boots. The wake
report injects `collect_boot_bifrost` output. With the delta door, the wake report
gains ONE LINE:

```
[akashic] delta since your last wake: 2 commits, 1 ledger transition — py agent_cli.py delta deepseek
```

**DESIGN.** The wake report is already compact (`bifrost_pull.py:205-230`). Adding a
full delta block would bloat it. A one-line summary with a pull pointer keeps the
wake lean while the agent can still decide "do I need the full delta before acting?"
If the delta is large (many commits, many transitions), the agent can run `delta`
before its first tool call to orient. If it's empty or small, the agent proceeds
immediately.

### D3c. The delta is PULL, not PUSH

The delta is never automatically injected at full detail into wake. It is always a
summary + pointer in the wake path; the full delta is always one command away
(`delta <agent>`). This prevents the delta from becoming its own archaeology
problem — an 800-char delta block injected into every wake becomes background
noise, and the agent learns to skim it, defeating the purpose.

**CERTAIN** (grounded in the wake_listener_detect_not_consume lesson: watchers
detect, they don't consume; the wake listener's job is to say "something happened,"
not to render a full report).

---

## DECISION 4: COST bound — cheaper than the archaeology it replaces

### D4a. THE METRIC

The delta door's cost is measured as **tool calls avoided per boot**. The current
archaeology tax is ~3-5 tool calls per boot (git_log + knowledge_recall for
where-we-are + bifrost_sync for bus mail + read_file for the last-session draft).
The delta door replaces those with ZERO tool calls — the delta is pre-computed at
boot assembly time and injected into context.

**CERTAIN.** This is the only honest metric: the delta door's value is not in
"characters saved" but in "tool calls not spent on orientation." Every tool call
avoided is budget the agent spends on the task instead.

### D4b. COMPUTATION COST

All six position reads are O(1) Redis operations or O(1) subprocess calls:
- `git rev-parse HEAD`: ~5ms subprocess.
- `TaskLedger.format_state()`: reads from the Redis mirror (`REDIS_LEDGER_KEY`,
  `task_ledger.py:39`), ~1ms.
- `AgentMemory.get_decisions(days=1)` + `get_experiences(days=1)`: HGETALL on
  two Redis hashes, ~2ms.
- `bus.cursor()` or `bus._read_cursor()`: HGETALL on one key, ~1ms.
- `bus.read_lane_cursor()`: HGETALL on one key, ~1ms.

Total mark read: ~10ms. Mark write (HSET of 6 fields): ~1ms. Total boot overhead:
~11ms. The delta RENDER (git log range, ledger diff, note scan, promoted query) is
computed LAZILY — only when `delta <agent>` is called, not at boot time. Boot only
writes the mark; the render is on-demand.

**DESIGN.** This preserves the boot's speed: the mark write is a fixed ~11ms tax
regardless of how much changed. The render cost scales with "how much happened,"
which is correct — busy arcs produce larger deltas, and the agent decides whether
to pay the render cost by calling `delta`.

### D4c. FAILURE MODE: the render is always cheaper than manual archaeology

Worst case: a month has passed, 200 commits, 50 ledger transitions, 30 notes
updated. The delta render reads git log (200 entries, ~20ms), ledger diff (~5ms),
note scan (~5ms), promoted query (~10ms). Total: ~40ms. One tool call.

Manual archaeology for the same: `git_log(max_count=30)` + `git_log(max_count=30)`
again (because 30 isn't enough) + `knowledge_recall("where-we-are")` +
`bifrost_sync` + `read_file("chronicles/last-session-draft.md")`. That's 5+ tool
calls and 4+ round trips.

The bound: **the delta door must NEVER cost more tool calls than the archaeology
it replaces.** Even in the heaviest arc, the delta is always ONE command (or zero
when pre-injected at boot). The computation cost is irrelevant — it's measured in
milliseconds vs the seconds of round-trip latency the agent pays for manual
archaeology.

**CERTAIN.** This is trivially met: the delta is either pre-injected (0 tool calls)
or one `delta` command (1 tool call). Archaeology is always 3+ tool calls. The
delta wins for any amount of change.

---

## DECISION 5: FAILURE MODES

### D5a. Stale mark

**Scenario:** The mark was written at boot but the agent crashed before acting. The
next boot sees the stale mark and renders "no changes" (the mark equals current
positions). The agent proceeds without archaeology — but nothing actually changed,
so archaeology would also have found nothing. **Harmless.** The mark being slightly
ahead of the agent's actual last action is always safe: the delta shows LESS than
what actually happened, never MORE. The agent doesn't miss anything critical because
critical things (commits, ledger transitions, notes) change positions — a stale mark
means the agent sees them as "not new" when they ARE new. Wait — that's wrong.

**CORRECTION (self-refute):** A stale mark IS dangerous. If the mark was written at
boot but the agent never saw the boot context (crash before prompt delivery), the
NEXT boot's delta is empty — and the agent misses everything that happened between
the two boots. The agent skips archaeology, but archaeology would have found real
changes.

**Fix: write the mark AFTER the boot context is delivered to the agent, not before.**
Concretely: the runner writes the mark after printing the system prompt (after the
agent receives it). If the runner crashes between prompt delivery and mark write,
the next boot sees no mark (newborn path — full boot) or the OLD mark (showing
everything since the last SUCCESSFUL boot). Either is correct. The mark must lag
the agent's actual last-seen context, not lead it.

**DESIGN.** This is implementable: the runner already has a post-boot phase where it
calls `work_drain`. The mark write goes AFTER the system prompt is printed to stdout
but BEFORE the first `work_drain` — the agent has received context, so the mark
captures what it saw.

### D5b. Mark loss

**Scenario:** The Redis key `{ns}:delta:mark:{agent}` is evicted or flushed. The
next boot sees no mark → newborn path → full boot. The agent pays the full
archaeology tax for ONE boot, then gets a new mark. **Harmless.** The mark is a
cache, not a durability requirement. The system degrades to current behavior
(full boot every time), which is already the baseline.

**CERTAIN** (grounded in the Redis ephemerality contract: `core/comm/bus.py:19` —
"ephemeral transport only; the durable record is a separate Ledger projection."
Same principle: the mark is ephemeral optimization; loss degrades gracefully).

### D5c. Twin sessions

**Scenario:** Two runners for the same agent boot simultaneously. Both read
positions, deliver boot context, write the mark. The second write overwrites the
first. Whichever mark survives, the NEXT boot's delta uses it. If the earlier
session's mark survives (the second session's write was overwritten), the delta
on the third boot includes everything from BOTH prior sessions. **Harmless.**
The delta over-delivers (shows more than the bare minimum), which is always safe —
the agent sees "more things happened" and investigates, vs missing something.

**CERTAIN.** Twin sessions are already a detected-and-refused condition for
consumers (S4 single-consumer gate, `test_t045_runner_cutover.py` S4 test). For
non-consumer agents (session doors, ephemeral queries), twin sessions are
possible but rare. The mark's idempotent overwrite is correct: any mark from a
completed boot is a valid "last known state."

### D5e. Backwards movement (rebase/rollback)

**Scenario:** A commit range where `HEAD` is an ancestor of the mark's commit
(a rebase dropped commits, or a `git reset` rolled back). The git range
`<mark_commit>..HEAD` is empty or invalid.

**Behavior:** The delta render detects this (HEAD is not a descendant of the
mark commit) and renders:

```
git: HEAD moved backwards (c9d511b → 9f7a72d); 3 commits were rebased out.
     Range before rollback: py agent_cli.py git-log 9f7a72d..c9d511b
```

The mark is NOT updated — the agent must decide whether to reset its mark or
keep it (the agent may want to re-read the rebased-out commits). The backwards
movement is LOUD (it's a rare event that deserves attention) but not an error.

**DESIGN.** The alternative — automatically resetting the mark to HEAD on
rollback — would silently discard the rebased-out range. The agent should know
that history moved under it. The pull pointer lets the agent inspect the
dropped commits if needed.

### D5f. A source that disappeared entirely

**Scenario:** The ledger is wiped, the lane cursor hash is deleted, the note
store is flushed. One or more position sources are missing at render time.

**Behavior:** Each field is independently fail-soft. If `git_commit` can't be
resolved, the section renders: `git: (unavailable — git repository not readable)`.
If the lane cursor hash is missing, the section renders: `lane: (no lane cursor —
newborn agent or lane hash expired)`. The delta block still renders all available
sources — a missing source doesn't blank the whole delta.

**CERTAIN.** This is the same fail-soft pattern as `build_autoboot_context`
(`agent/harness/context.py:56` — "each data pull is independently fail-soft:
a broken piece drops out, it never blanks the rest"). Every source read is
wrapped in try/except; a failed read renders an `(unavailable)` line.

---

## DECISION 6: the `delta` verb door

### D6a. SURFACE

A NEW CLI verb: `py agent_cli.py delta <agent>` — the one command that renders
the full delta. Underneath, it calls `DeltaRender(agent_id).render()` which reads
the mark, reads current positions, and formats the block per D2.

Also available as a ToolBox tool (`delta` or `knowledge_delta`) so the agent
can call it mid-session — useful when the agent wants to check "did anything
change while I was working" without ending its turn.

**DESIGN.** A dedicated verb is the right surface: it's discoverable
(`agent_cli.py help` lists it), it's one command, and it follows the existing
pattern of `boot`, `bifrost-sync`, `task list` — each is one verb that renders
one view.

### D6b. CACHING

The full delta render is cached for 30 seconds (same TTL as turn_metrics
`EST_CACHE_TTL`, `core/comm/turn_metrics.py:49`). If the agent calls `delta`
twice within 30 seconds (e.g., the delta is in boot context AND the agent
calls `delta` to double-check), the second call returns the cached render.
The cache key is `{ns}:delta:render:{agent}`.

**DESIGN.** The 30-second cache matches the turn_metrics pattern and prevents
the boot assembly's pre-computed delta (injected into context) from being
recomputed if the agent immediately calls `delta`. After 30 seconds, the
cache expires — a new `delta` call re-reads current positions and may show
new changes (e.g., Claude committed while the agent was reading the delta).

---

## DECISION 7: migration — newborn vs established agent

### D7a. NEWBORN (no delta mark)

A newborn agent has no `{ns}:delta:mark:{agent}` key. The boot assembly skips
the delta block entirely — the agent gets the FULL boot (current behavior).
The boot assembly writes the mark AFTER delivering context, so the NEXT boot
gets a delta.

**CERTAIN.** This is D5a's mark-lag principle: the mark is written at boot
completion, so the agent must have seen the full context before the mark
exists. A newborn's first boot is always full; every subsequent boot is delta-
augmented.

### D7b. MIGRATING (from pre-delta to post-delta)

When the delta door ships, all existing agents are newborns — no delta marks
exist. The first boot after deployment writes the mark; the second boot gets
the delta. No migration script needed — the mark is created lazily on first
boot.

**CERTAIN.** Same pattern as the lane cursor: `lane_flip_if_migrating`
(`core/comm/bus.py:742-757`) detects a virgin lane cursor and seeds it once.
The delta mark detects a missing key and writes it at boot completion. No
explicit migration — the system bootstraps itself.

---

## DECISION 8: what the delta door does NOT do

### D8a. Does NOT replace the full boot

The delta augments the boot; it does not replace it. Static context (arch slice,
lesson injections, the door contract) is still in the boot. The delta only
displaces the archaeology sections that answer "what changed." An agent that
needs the full world-state can still run `boot --full`.

### D8b. Does NOT track file-level changes (only commit-level)

The delta shows which COMMITS landed, not which FILES changed. File-level
tracking would require a mark per file (hundreds of marks) or a git diff
between the mark commit and HEAD (potentially large). Commit-level is
proportional: the number of commits is the right granularity for "what
happened." An agent that wants file-level detail runs `git diff <range>`.

### D8c. Does NOT auto-advance on mid-session changes

If Claude commits while DeepSeek is mid-session, the delta mark does NOT move.
DeepSeek's NEXT boot will see Claude's commit — but DeepSeek's CURRENT session
won't see a mid-session delta injection. Mid-session change notification is a
separate concern (the sig lane + steer-kind already carry mid-session signals;
this is orthogonal to the delta door).

### D8d. Does NOT store rendered deltas in the Ledger

The delta is an ephemeral view, not a durable record. The mark is durable
(Redis with the same persistence as lane cursors), but the rendered delta
block is computed on demand and never stored. The Ledger already records
WHAT happened (events, commits, transitions); the delta is a VIEW of those
records from one agent's perspective — it adds no new durable facts.

---

## SUMMARY

The delta door is an AGENT-OWNED high-water mark (six positions in a
lane-cursor-style Redis hash) written at boot completion, a structured
render (one block per moved source, 1200-char budget with pull pointer),
boot/wake integration (replaces archaeology sections in boot, adds one
summary line to wake), and a bounded cost model (always ≤1 tool call vs
3-5 for manual archaeology). Failure modes are all fail-safe: stale mark
is prevented by mark-lag (write after context delivery), mark loss degrades
to full boot, twin sessions over-deliver harmlessly, backwards movement is
loud, and missing sources are individually fail-soft.

Per the wishlist S1 mandate: "ONE mechanism serving 'what changed since I
was last here' for every agent." This design serves all agents from one
key pattern, one render path, one verb.
