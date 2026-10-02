# Navi half_b — one-spine: the target question, the emit contract, the blind-verifier standing

Fence: `fences/one-spine/brief.md`. Blind half (half_a, half-rill, half-sol unread). I am the
W0.1 schema author and the blind verifier named in `fences/context-system/reconciliation.md`
(W0.1 row: "Navi: conformance to her EBNF, blind to the code"). That standing is intact; the
build starts tonight; RED pins first, in a commit of their own before GREEN (M3), as the
brief's acceptance requires.

---

## ANSWER

**No.** No existing key does what `context.target.v1` does for an `events:raw` record. The
nearest thing in the tree is the RB-4 byref projection (`events:raw:byref:<ref>`,
core/events/event_index.py:42,151), and it is a *mechanism without a grammar*: it will
faithfully index any string a writer puts in `refs[]`, but nothing constrains what those
strings are. The closed ref set, the `work:<name>:` normalization, the digit-suffix line
parsing, the `dir/` trailing-slash marker, the ref-before-path precedence — the things that
make a target *joinable* rather than merely *present* — exist only in the W0.1 spec
(research/in-flight/context-system-navi-m1.md), which is sealed and unbuilt. Proof of the
gap, from the tree: every current emit writes bare, unparseable strings into `refs[]` —
`'commit:e5145a43'` with no `sha:` prefix (scripts/hooks/claude_sessionend.py:~165),
`task:T391` bare (same file), `bus_stream:bifrost:claude` — a non-ref compound that is none
of the six closed kinds (agent/harness/context.py). The byref index indexes them all;
nothing can resolve them. If any existing key already did the job, W0.1 would not be in the
Wave 0 table with my name on it.

So the four gap emits need the contract. Two rules, then the per-kind table.

**The subject rule.** The target of a gap emit is its *subject* — the seat the fact is
about — and that anchor is **derivable** from fields `capture()` already stores:
`agent_id` + `session_id` are top-level record fields (core/events/event_log.py:135-145),
and `seat:<name>` / `session:<sid>` are already members of the W0.1 closed ref set
(research/in-flight/context-system-navi-m1.md, the `ref` production). The context door can
therefore resolve the subject anchor from the record body **without the writer repeating it
in `refs[]`**. Writers that do emit `refs=["seat:<agent>"]` get it picked up by the byref
index for free (event_index.py:77) — an O(1) per-ref lookup that is pure profit, costs one
string, and should be done. But it is an optimization, not the join mechanism. If the
reconciler rules "the subject MUST also ride in refs[] for uniformity," that costs nothing
and breaks nothing; what must not happen is the subject riding in refs[] in a *non-grammar*
spelling like `bifrost:claude`.

**The contract.** For each gap emit, what `context.target.v1` requires:

| gap | kind(s) | subject anchor (derivable) | MUST carry typed, in refs[] | MAY carry |
|---|---|---|---|---|
| 2 worklive | `beat`/`phase`/`wedge` | `seat:<agent>` + `session:<sid>` from agent_id/session_id | **nothing** — detail={phase, since_ts, turn, code_sha} is fact payload, not refs | `sha:<code_sha>` **only if** it is a real resolvable git commit; `session:<sid>` for the byref freebie |
| 4 janitor | `expected`/`retract`/`revoke` | `seat:<agent>` + `session:<sid>` | **nothing** | `session:<sid>` in refs[]; `task:T420` in detail.refs if the slice wants the lineage |
| 3 activity | `activity` | `seat:<agent>` + `session:<sid>` | **nothing** | `session:<sid>` |
| 1 wire | `wire` | `seat:<agent>` + `session:<sid>` **IF the emit site knows it** | **nothing for context.target.v1** — but `session:<sid>` SHOULD ride refs[] whenever known, or `context session:<sid>` shows a session with zero wire facts | `sha:` never; trace-id in detail (it is an opaque provider string, not a house ref) |

Three sharp edges the reconciler should decide explicitly:

1. **Wire's session gap.** `WireJournal._shape` (scripts/wire_journal.py:323-345) records
   `agent` but **no session field**. If Gap 1 emits `kind='wire'` with only agent_id, then
   `context session:<sid>` — the plane W0.6's session-focus resolver reads — shows wire
   silence for every session, falsely. The wire emit SHOULD forward session_id (the runners
   all have it: `seat_session_id()` at scripts/bifrost_runner_*.py). This is not a
   `context.target.v1` requirement — session is a record field, not a ref — but it is the
   one place a gap emit's *omission* would make a W0.6 plane lie by absence.

2. **`code_sha` is a trap.** Heimdall's map puts `code_sha` in the Gap 2 detail, and
   `roster.heartbeat` writes `_liveness_code_sha()` into the beat doc (core/comm/roster.py:144).
   A short sha is exactly the thing `context.target.v1`'s `sha:<hex>` ref exists for — and
   exactly the thing that must NOT be minted blindly, because a stamped sha can be stale
   (`_code_freshness` returns "stale", roster.py:~100) and a bare `code_sha` string in
   detail is *not* the typed `sha:<hex>` the byref index needs. Rule: `sha:<hex>` rides
   refs[] ONLY when the emit site has verified it resolves (`git cat-file -t`); a stale or
   unresolvable sha stays in detail as a string and never becomes a ref. Detail strings are
   facts; refs are promises.

3. **The x-ds-trace-id is not a ref.** Heimdall's Gap 1 route says `refs=[x-ds-trace-id]`.
   Under the closed ref set that string is not one of the six kinds, and W0.1 forbids
   minting new ref kinds in Wave 0 (research/in-flight/context-system-navi-m1.md: "A
   resolver may NOT mint new ref kinds"). It belongs in detail (`detail.trace_id`), where
   `status --depth wire` reads it. If the house later wants trace-id joinable, that is a
   Wave 1+ ref-kind addition through the parent fence, not a Wave 0 shortcut.

Bottom line for the fold: **no gap emit is required to invent target plumbing.** The spine
record already carries the subject; `context.target.v1` already names it; the door resolves
it. What the four welds must do is (a) emit through `capture_event` so agent_id/session_id
land as record fields, (b) keep facts in detail, pointers in refs, and (c) never let a
bare string that *looks* like a ref ride refs[] unless it parses under the EBNF.

---

## EVIDENCE (file:line, verbatim)

The existing nearest key, and what it actually does:

- core/events/event_index.py:17 — `events:raw:byref:<ref>   set   {event_id, ...}          -- exact per-ref lookup (RB-4)`
- core/events/event_index.py:77 — `for ref in (event.get("refs") or []):          # RB-4: exact per-ref lookup` / `self.store.sadd(byref_key(str(ref)), eid)`
  → The index sadds **whatever string is in refs[]**, untyped. The lookup key IS the raw
  string. No grammar, no normalization, no resolution.

The record fields the subject anchor derives from:

- core/events/event_log.py:135-145 — the emitted event dict literal:
  `"agent_id": agent,` / `"session_id": self._clean(session_id),` / `"refs": [str(r) for r in (refs or []) if r],`
  → agent_id and session_id are first-class, always-present (defaulted) fields on every
  events:raw record. `seat:<agent>` and `session:<sid>` need no new plumbing.

The closed ref set they parse under (W0.1 spec, sealed):

- research/in-flight/context-system-navi-m1.md — `ref = "event:" stream ":" entry_id | "sha:" hex{7,40} | "task:T" digit{2,4} | "lesson:" id | "doc:" rel_fwd_path | "session:" sid | "seat:" name | "commit:" hex{7,40}`
  and the law: `A resolver may NOT mint new ref kinds; the set is closed for Wave 0`.

What current emits actually put in refs[] — bare, unparseable, indexed-but-unresolvable:

- scripts/hooks/claude_sessionend.py:~165 — `'commit:e5145a43'` (no `sha:` prefix; fails the `ref` production, falls to `path_anchor`, misresolves or rejects)
- agent/harness/context.py — `bus_stream:bifrost:claude` (a compound that is none of the six kinds)
- scripts/hooks/claude_sessionend.py — `task:T391` (this one DOES parse; it is the exception that proves the rule)

The Gap 1 emit site's shape (what wire records carry today):

- scripts/wire_journal.py:323-345 — `_shape` builds `rec` with `"agent": kw.get("agent") or self.agent`, `"model"`, `"finish_reason"`, `"system_fingerprint"`, token/cache/timing fields, `prompt_sha`/`response_sha` hashes. **No `session_id` field anywhere in the record.**
- scripts/wire_journal.py:46-52 (module docstring) — `"METADATA ONLY, BY CONSTRUCTION. No request or response BODIES are ever written."` — D1 already holds at this layer; the gap emit inherits it for free.

The Gap 2 emit site and its code_sha hazard:

- core/comm/roster.py:110-152 — `heartbeat(ns, agent, session_id, *, phase="idle", ...)` writes the worklive doc: `"phase": str(phase), "beat_ts": now, "since_ts": ..., "seq": ..., "code_sha": _liveness_code_sha()`. The phase/since_ts/sha are all HERE, in one call, keyed by agent+sid8.
- core/comm/roster.py:~100 — `_code_freshness` returns `"current" if stamped == head else "stale"`: a stamped sha can be stale, so a `sha:` ref minted from it unverified is a false promise.

The Gap 4 emit site (the claim file the janitor reconciles):

- core/comm/resume_on_deaf.py:62-77 — `declare_expected` writes `state/wake-expected/{agent}_{sid}.json` with `{"agent", "session_id", "by", "cwd", "declared_at"}`; `retract_expected` unlinks it. Both have agent+session_id in hand at the call — the emit needs no new inputs.

The Gap 3 emit site:

- core/comm/wake_seat.py:421-425 — `touch_activity(agent, session_id, tmp=None)` writes the epoch into the marker. agent+session_id in hand. The map's throttle (one emit per idle→active transition) is a read-side decision the welder makes HERE, at the call, not in the schema.

The receipt the welds must serve (from the brief, this morning's defect):

- fences/one-spine/brief.md (INPUTS) — `"the ear's cold-seat notice fired three times on a live, armed Vandor seat, because the predicate reads a private file on a stale worktree instead of a spine fact."` The acceptance drill: `"one of Daniel's messages in the Vandor channel receiving no cold-seat notice while the seat is armed."` That drill needs `context seat:<vandor>` (or the doctor's equivalent read over the spine) to return the armed beat — which is exactly Gap 2's emit, joined by the derivable `seat:` anchor. No refs[] entry required; the record's own agent_id is the key.

---

## VERDICT ON THE FOLD

V1. [CERTAIN] **One spine: HOLDS** — with one placement correction the reconciler should rule on, not me.

The four gaps and Wave 0 are one spine with one weld order. Heimdall's map and the
context-system reconciliation describe the same substrate from two sides: his `events:raw`
field model `{at, agent_id, session_id, kind, summary, detail, track, refs}` IS the record
the context door reads, and his "the context door and Heimdall's status/timeline are both
read-views over one stream" is the reconciliation's own W0.6 sentence. Welding either side
alone builds the rival assembler both documents warn against. The fold is real.

The correction, stated as a question for the reconciler because the map and the Wave 0 table
genuinely diverge on it: **the map proposes weld order 2-4-1-3 (Gap 2 first, "highest signal,
hooks already exist"); the Wave 0 table is numbered W0.1 schema → W0.2 touch → W0.3 eval →
W0.4 instrument → W0.5 scene → W0.6 door.** These are not in conflict — W0.1/W0.2 are
context-system slices and the gaps are spine emits — but the brief's acceptance says "one
weld order" and someone must say whether Gap 2's emit waits for W0.1's schema (so its refs,
if any, parse from day one) or lands first with a derivable-subject-only contract (refs[]
empty, subject from agent_id/session_id) and gains typed refs when W0.1 exists.

My reading, offered as the blind verifier not the reconciler: **the gap emits do not need
W0.1 to land first**, because their subject anchor is derivable from record fields and my
table above requires nothing in refs[]. Gap 2 can weld on Heimdall's order, tonight, with
empty refs[] and the subject carried by the record itself; when W0.1 lands, the door joins
those already-written records with zero backfill. That is the strongest evidence the fold
holds: the two sides compose without either waiting on the other. But it is the
reconciler's call, and the pre-registered acceptance ("Daniel says 'that's right'") governs.

On scope: the map's scope discipline (no new store, no new writer, no narrative-schema
change, pointers never bodies) and the reconciliation's standing decisions (no second
ledger, session id forwarding, one engine, promotion never automatic) are the same doctrine
in two vocabularies. Nothing in my answer requires violating either.

---

## WHAT I WOULD NOT BUILD

1. **A target field on the record.** The events:raw record shape is the map's own contract
   and the foundation's reserved layer; adding a `target` key forks the schema for no join
   the derivable subject anchor cannot do. The subject IS agent_id+session_id. Do not
   denormalize it into a new field.

2. **A new ref kind for the trace-id, the shard, or the wire segment.** The closed set is
   closed for Wave 0 on purpose (research/in-flight/context-system-navi-m1.md). Trace-id
   joins are a Wave 1+ parent-fence question. Minting `wire:` or `trace:` in a gap emit
   would be exactly the unparseable-refs disease the byref index already suffers from,
   formalized.

3. **Per-5s activity/beat events.** The map says it and I ratify it: the 5s refresh is a
   STATE (TTL key), not an EVENT. Emitting it drowns the firehose and makes every
   `events:{agent}:raw` replay 99% noise. Gap 2 emits on phase CHANGE and WEDGE; Gap 3 on
   idle→active transition; never on the refresh. The wedge-detection seam is Rill's
   question, not mine — but whatever line he names, the emit fires once per transition,
   full stop.

4. **Storing `code_sha` as a `sha:` ref without resolution.** A stale stamped sha that
   parses but does not resolve is worse than no ref — it makes `context sha:<stale>` a
   confident lie. Detail string, or verified ref, never an assumed one.

5. **A wire emit that drops session_id when the runner knows it.** This is the one place an
   omission becomes a lying absence on a W0.6 plane. If the wire emit site cannot reach
   session_id cheaply, say so in the slice's fog[] (UNCHECKABLE), do not silently emit
   agent-only and let `context session:<sid>` render a session with no wire facts.

6. **Any change to the W0.1 grammar to accommodate the gaps.** The grammar is sealed
   (research/in-flight/context-system-navi-m1.md, committed under my name with the
   reconciliation). If a gap emit "needs" a target the grammar cannot express, the emit is
   wrong, not the grammar. My blind-verifier pins for W0.1 tonight (four spellings one key,
   `foo:3.py`, a worktree path, a heredoc, a ref that looks like a path) are unchanged and
   are the RED commit that lands alone before any GREEN.

---

*Navi (kimi) — W0.1 schema author and blind verifier. half_b of the one-spine fence.
Filed once; the bus carries the path.*
