# HOUSE ROUND — context-system · half_a (Heimdall / deepseek)

Blind half. Same brief, any code read. Nothing here was written with the other half in view,
and nothing here is softened toward it. Divergence is the product.

Grounding note up front: I have read, this session, the actual code the map grades —
`core/coord/session_focus.py:206`, `core/comm/toolbox.py:1436`, `core/events/event_log.py`,
`core/events/event_index.py`, `agent/harness/hooks/claude_posttooluse.py`,
`scripts/authorship_ledger.py`, and `design/s2-recall-outcome-adjudicator-spec.md`. Every number
below is measured or read, not recalled. Where a claim rests on code I cite file:line.

---

## 1. FRAMING VERDICT (the thing that outranks everything)

The brief asks the right question and the map is broadly the right map. But the map over-credits
one plane and under-names one existing plane, and both errors are load-bearing:

**The authorship ledger is a thin plane, not a six-plane peer.** It is 813 rows of
`sha → seat` (`state/authorship/seats.jsonl`), keyed on a field git was about to be rewritten
away from — a *correction* layer, not a provenance organ. The brief's "six planes" list elevates
it to sibling of the Eye and the lesson corpus. It is not. It answers one of Daniel's five
questions ("who touched it last") only at commit granularity and only for commits made after the
post-commit hook landed (the brief itself admits `500daeee → claude` is the first answered row).
Every other "who touched" question must come from the TOUCH, which does not exist yet. Grade the
map with that in mind: slices that "join the authorship ledger" are joining a mostly-empty future
plane; slices that join git + touches + lessons are joining the planes that actually answer today.

**`session_id` is reachable-but-unpassed, not absent.** The parent fence's evidence pack reports
0.0% session_id fill on the event plane and calls the door unbuilt. I read
`claude_posttooluse.py` this session: `main()` receives `data.get("session_id")` from the Claude
Code payload and passes it to `record_call` (`session_focus.record_call(data.get("session_id"), …)`),
and `_beat_seat` resolves the SAME payload field as ground truth over env. The field *arrives* in
the hook's hands every call; no `capture()` site forwards it to the event plane. That is a wiring
defect, not a data defect — and it is the single cheapest high-value fix in the entire round,
because it is what turns every existing `file_edit` / `command` / `learning` event from
"who, what, when" into "who, what, when, *in which session*", enabling the Eye join B5 needs
with zero new capture. I flag it as B5's kernel and as the first build.

**"Teaches something false" is underused in the map.** Several slices (B3's timeline, D2's doc
ranking, E2's L0 line) will happily print a confident answer from a plane whose coverage window is
narrow (the firehose caps at 100k; touches will outnumber every other kind and evict themselves in
hours). A "last touched" answer that silently reads "last touched *since the firehose trimmed*" is
false at exactly the moment Daniel looks. D3 (time-fog) is deferred to wave 3, but the fog is
*created* in wave 0 by A5's eviction. I name this in the A5 verdict as `false-if`.

---

## 2. VERDICT LINES (one per slice, the seal checker's format)

> NOTE on numbering: the brief's OUTPUT CONTRACT writes the shape `V<piece><n>.` with `<piece>`
> = A–F, but the door's own seal checker (`core/coord/fence_workspace.py` `_VERDICT_RE`) matches
> `^\s*V\d+[.)]\s` — a bare digit, not a letter. I number V1..V31 below (checker-compliant) and
> keep the piece+slice id (A1 etc.) in the line body so the brief's convention stays readable.
> Flagged to the reconciler as a brief-vs-checker mismatch, not a defect in the half.

### Piece A — the touch

V1. [CERTAIN] A1 capture touch -- keep / evolves core/events/event_log.py capture() (new kind, not a new store) / write-cost 1 capture_event() per hook fire (~2,000 this session; O(1) + one byref sadd + one tindex zadd) / read-cost events_for_ref(file:X) later / false-if tool_input file_path is http/CWD-relative and not normalized to repo-relative, so "who touched X" keyed on a path the grep never wrote.

V2. [CERTAIN] A2 runner reads/exec/search -- keep / evolves core/comm/toolbox.py _record_file_provenance (generalize file_edit to a touch kind with action) / write-cost +~3 capture()/tool call beside the existing 1 / read-cost same as A1 / false-if the runner seats' reads are captured but claude's are not, and a seat is told "last touched by sol" when claude is simply uncaptured.

V3. [DESIGN] A3 Codex/Cursor parity + drift close -- merge / evolves agent/harness/hooks/* + scripts/hooks/* (ONE file + a shim, per the brief's own "8 diff lines") / write-cost 0 net (fewer trees) / read-cost 0 / false-if the shim drifts a third time because nobody owns the singleton — name the owner in the slice, don't leave it implicit.

V4. [INFERRED] A4 DSH touches -- keep / evolves the DSH plugin tool path (Rill's harness) / write-cost 1 capture() per plugin tool, only where the plugin already serializes a target / read-cost same as A1 / false-if Rill's plugin has no reliable target field and we synthesize a phantom one.

V5. [CERTAIN] A5 sizing + cost stream -- keep (my lane; sized below) / evolves core/events/event_log.py + event_index.py (a convenience stream, NOT a ledger kind) / write-cost 1 zadd + 1 sadd amortized, eviction O(k) on trim / read-cost smembers(ref) = O(members) then per-id get = O(1) each / false-if the touch stream shares CANONICAL_MAXLEN and evicts the chronicle (touches dwarf every other kind).

V6. [DESIGN] A6 derived check-in -- keep / evolves core/coord/session_focus.py current() (infer task when none is set) / write-cost 0 extra (piggybacks the A1 capture) / read-cost 0 / false-if the inferred task is wrong and the seat never notices because the override is buried.

V7. [CERTAIN] A7 target grammar -- keep / evolves core/coord/session_focus.py touches() + normalize_target (the two places a target is already reduced to a string) / write-cost 0 (a normalization function, not a capture) / read-cost 0 / false-if two harnesses normalize the same path differently and "file:x" and "x" fail to join (the parent fence's forked-semantics law).

### Piece B — anchors and joins

V8. [CERTAIN] B1 anchor grammar -- keep / evolves core/eye/ground.py target vocabulary (orient's typed targets: extend `verb:`/`seat:` with the six anchor types) / write-cost 0 / read-cost 0 / false-if the grammar accepts an untyped string and guesses (the brief's own "never guessed" rule).

V9. [DESIGN] B2 one resolver per plane -- keep / evolves existing doors (git log/blame, events_for_ref, authorship_ledger.who, lesson files_affected, eye find, recall surface) — each resolver is a read adapter, no new store / write-cost 0 (read-only) / read-cost 7 indexed lookups + 1 git log for L1 / false-if a resolver silently returns [] and the scene prints "no touch" instead of "unchecked" (zero-is-not-no law).

V10. [DESIGN] B3 time scope -- keep / evolves the joined rows' `at` fields (git author-date, event at, lesson created) / write-cost 0 / read-cost O(joined) sort / false-if the bucket timeline implies equal coverage across planes when the firehose covers hours and git covers months.

V11. [DESIGN] B4 organ map -- keep / evolves docs/MAP.md + MODULE_INDEX.md + PHYSICS.md (a read projection, regenerated, not a new fact) / write-cost 0 (rebuild on demand) / read-cost O(1) lookup / false-if a path lands in no organ and the scene invents one (a regenerable projection must say "no organ", not guess).

V12. [CERTAIN] B5 cross-plane stable ids -- keep (my half + Navi's; the parent fence's deliverable, detailed below) / evolves core/events/event_log.py capture() session_id (forward it; it is reachable-but-unpassed today) / write-cost 0 (pass a field already in hand) / read-cost 0 / false-if joins are by text (path/title/timestamp) rather than stable key — the parent fence's settled law.

### Piece C — the knowledge index

V13. [CERTAIN] C1 eval set -- keep, build first / evolves recall's bench (a new verb over the shelf) / write-cost 0 (hand-authored 40 rows) / read-cost recall@5 over 40 rows / false-if the "known right lesson" set is written by the seat that owns the lessons and self-grades.

V14. [DESIGN] C2 learn derives files_affected from touches -- keep / evolves core/learning learn path (needs A1 first, exactly as the dependency graph says) / write-cost 1 read of recent touches at learn time / read-cost 0 / false-if a lesson is stamped with a file the seat merely read, not the file the lesson is ABOUT.

V15. [DESIGN] C3 lessons into the shelf engine -- keep / evolves core/recall shelf (SQLite FTS5 + MiniLM + RRF); retires the %TEMP% JSON cache / write-cost O(embeds) per learn, one-time backfill over 1,526 lessons / read-cost FTS + vector, already capped / false-if the embed and the FTS text disagree silently (two representations of one lesson).

V16. [DESIGN] C4 cast -- keep / evolves the shelf query door (one door over lessons/manuals/docs/notes/bus) / write-cost 0 / read-cost the expensive branch, already char-capped / false-if "why" (the expensive question) returns unranked noise because the ranking is on "available" not "relevant".

V17. [DESIGN] C5 recall-at INTENT queries -- keep / evolves core/recall/at_action.py intent surface / write-cost 0 / read-cost per-firing caps, chrome once per session / false-if verbs-as-their-own-shelf re-ranks the whole shelf per firing and blows the read budget.

V18. [CERTAIN] C6 objective outcomes -- keep (my lane; the redesign's S2, owner claude's spec already exists) / evolves design/s2-recall-outcome-adjudicator-spec.md + core/recall/at_action.py _log_outcome_stage + shadow_shelf (the observer is READ-ONLY, writes observations not verdicts) / write-cost 1 observation record per prevention candidate / read-cost render over the stage log / false-if the observer writes a verdict (fence r2 H-C1: adjudication is operator-only).

V19. [CERTAIN] C7 promotion to gates -- keep (the redesign's S1) / evolves the S2 verdict VIOLATED → a `refusal_shape` → the door rule engine / write-cost 0 (human/curator act, per the spec's no-auto-steeer law) / read-cost 0 / false-if a resident grades its own lesson into a gate (recall must not grade recall).

### Piece D — the Eye

V20. [CERTAIN] D1 ingest tool records -- keep / evolves core/eye/index.py ingest (kind=tool with targets) / write-cost 1 ingest per tool record / read-cost eye find by target / false-if "touched" is double-counted because touches (A) are ALSO ingested into the Eye, and one context read sums both.

V21. [DESIGN] D2 docs/research on a shelf -- keep / evolves one SQLite engine (the halves decide one-vs-two; I argue ONE engine, the shelf's, with the Eye as a read projection — two engines means two "ranked cited answer" surfaces that will disagree) / write-cost O(doc) index on change / read-cost FTS rank / false-if the Eye and the shelf rank the same doc differently and it reads as contradiction.

V22. [CERTAIN] D3 time-fog known_at honored -- keep, and PULL EARLIER / evolves every read path's honesty suffix (the resolve() aged-out message already exists at event_log.py) / write-cost 0 / read-cost 0 / false-if it ships in wave 3 while A5's eviction ships in wave 0 and the L0 line says "last touched 3h ago" when the firehose trimmed 2h ago.

### Piece E — the door and scene

V23. [CERTAIN] E1 scene.v1 -- keep / evolves the orient/present scene idiom (renderer-neutral, stdlib-only) / write-cost 0 (a validated struct) / read-cost 0 / false-if the scene carries rendered strings rather than fields, so Discord and CLI and Bifrost each re-render and drift.

V24. [CERTAIN] E2 the door -- keep / evolves agent_cli.py context verb + the MCP twin (door parity) / write-cost 0 / read-cost L0/L1 cheap, L3 raw / false-if the MCP twin and CLI fall out of field parity (the F3 gate exists to catch this).

V25. [DESIGN] E3 renderers -- keep / evolves scripts/bifrost_ui.py (a standalone module + snippet; my lane's UI surface) / write-cost 0 (render against scene fields) / read-cost 0 / false-if the Bifrost panel reaches the stores directly instead of through the scene and renders a different truth than the CLI.

V26. [DESIGN] E4 Discord projection -- keep / evolves the Discord reply shape (Sunshine's split) / write-cost 0 / read-cost 0 / false-if the Discord card is a re-rendered L1 that omits a plane the CLI shows (same scene, different field subset).

V27. [DESIGN] E5 boot L0 -- keep / evolves the boot header (replace the raw-journal peek) / write-cost 0 / read-cost the seat's own L0 lines once per boot / false-if a seat's boot reads its own prior touches as "the world" and skips a sibling's work on the same file.

### Piece F — integration and verification

V28. [CERTAIN] F1 pins per slice -- keep / evolves each slice's test file (payload-truth + live-corpus-probe discipline) / write-cost 0 net (pins are the gate) / read-cost 0 / false-if a pin is written against a fixture that drifted from the live payload (the exact thing payload-capture exists to prevent).

V29. [CERTAIN] F2 drills + receipts -- keep / evolves the house drill pattern / write-cost 0 (one seat reproduces) / read-cost 0 / false-if the verifying seat reads the slice's pins first and merely confirms (blind is the point).

V30. [CERTAIN] F3 gates -- keep / evolves check_wiring + check_door_parity / write-cost 0 / read-cost 0 / false-if the gate is wired but nobody fails it (built ≠ wired, the reverse direction).

V31. [CERTAIN] F4 privacy + cost + stats -- keep (my lane) / evolves context --stats / write-cost 0 (caps declared in manifest) / read-cost prints the measured write/read cost / false-if the stats are declared not measured, and the manifest says "O(1)" while the index does a full smembers scan.

V32. [DESIGN] F5 contract doc -- keep / evolves docs/context-system.md (one markdown, the presentation-primitives idiom) / write-cost 0 / read-cost 0 / false-if it documents intent not field truth and drifts like the docs the parent fence warns are rotted.

---

## 3. THE SLICES THIS MAP IS MISSING

M1. [CERTAIN] **session_id forwarding** — the map has no slice that closes the parent fence's highest-value gap (0.0% session_id fill). It is buried inside my B5, but it deserves its own slice because it is the ONE write-side change that unblocks the Eye join for every existing event with zero new capture. Build it in wave 0, before A2/A3/A4 even finish, because it makes the *already-captured* events joinable.

M2. [CERTAIN] **touch deduplication / idempotency** — five harnesses capture the same tool call (a hook fires, the runner also captures, the Eye ingress also sees it). Without a dedupe key (session + tool_use_id or seq), "who touched X last" sums the same action twice and the timestamps disagree. The RB-26 crash-redelivery law (idempotent consumers) applies to capture, and the map names no such slice.

M3. [DESIGN] **the touch's TARGET normalization, separate from A7's grammar** — A7 gives the vocabulary; nothing gives the *normalizer* the harness adapters all call, so `file:conversation.py` and `conversation.py` and `E:/AI-Setup/conversation.py` and `./conversation.py` are four keys for one file. This is the forked-semantics law made literal, and it must be one owned function, tested by the same fixtures, not re-derived in five hooks.

M4. [DESIGN] **anchor canonicalization + a "who touched it last" read that is honest about eviction** — B2 resolvers answer, but nothing guarantees the joined answer states its own coverage window in the same shape (D3 does time-fog, but D3 is wave 3 and A5's eviction is wave 0). A `known_since`/`retention` field on the touch stream's read, surfaced in the scene, is a distinct slice the map folds into D3 too late.

---

## 4. THE TWO I WOULD BUILD FIRST

**M1 (session_id forwarding) + A1 (the touch capture).** They are the same seam. The hook already
holds `session_id` and the target in its hands every call (`claude_posttooluse.py` resolves the
payload's session_id as ground truth over env) and yet captures neither on the event plane — one
`capture()` call gets both. M1 alone makes every existing `file_edit`/`command` joinable to the
Eye (the parent fence's whole point); A1 adds the missing action axis (read/write/exec) so "who
touched it last" stops meaning "who *wrote* it last". Neither invents a plane; both land on the
one ledger the constraints already name. Everything downstream — C2, B2, E2's touches row — burns
their fuel.

## 5. THE ONE I WOULD REFUSE

**I would refuse to build the touch as a NEW LEDGER KIND / new stream with its own capture path.**
The brief correctly hedges ("the halves decide"), and I decide no. Three reasons, two from the
constraints and one from the code I read:

1. The constraints already bind it: "no second ledger — a touch is an input to the one ledger, as
   `record_call` and `toolbox.capture` already say of themselves." A touch is exactly the event
   `record_call` already receives and discards; a new kind string on the existing `capture(kind=…)`
   door is the input, not a new organ.
2. The read model already exists: `event_index.events_for_ref(ref)` does the exact "every event
   carrying ref R" lookup a touch needs, and `byref` already shrinks in lockstep with eviction
   (my own RB-4 mandate). A new ledger kind would either duplicate that read model or — worse —
   bypass it and answer "who touched X" from a stream the byref index does not see, producing a
   third answer that disagrees with the other two.
3. A new kind carries a **cost**: the touch stream outnumbers every other kind, so if it rides a
   separate stream it must be sized separately and the firehose cannot evict it — but the moment
   it is a *separate* stream, "the chronicle" and "the touches" have different retention and
   "who touched X last" silently changes its own horizon as the touch stream fills. One stream,
   one kind, one index, one retention; the *convenience* is a per-agent-touch stream for the hot
   read, not a separate plane.

What I *would* build instead is the sidecar-shaped compromise in my A5 lane below: a `touch`
kind on the one firehose (so the ref index answers it), plus a dedicated per-ref touch *index*
sized so its eviction is visible and honest, never a second ledger.

---

## 6. LANE — A5, sized with numbers

The question A5 answers: touches will outnumber every other kind; the 100k firehose must not
evict the chronicle; what does the stream cost per write and per read, and where does the
touch live?

**Where it lives (the case is above, the numbers here):** the touch is a `kind="touch"` on the
ONE firehose (`events:raw`, existing `event_log.capture`), with `refs=[file:<rel>, …]` so the
existing `event_index.events_for_ref` answers "who touched X" with zero new store. The
*convenience* is two things: (a) a bounded per-agent touch stream (a ledger stream, not a plane),
and (b) an optional per-ref touch *window* (last-N by ref) kept as a capped list, because the
firehose's byref set grows unbounded per ref until the event ages out.

**Write cost, per touch (one tool call):**
- `ledger.emit(events:raw)` — O(1) append, maxlen trim fires only when the stream is at cap
  (`event_log.capture`).
- `ledger.emit(events:<agent>:raw)` — O(1) append (per-agent convenience, `PER_AGENT_MAXLEN=10k`).
- `event_index.add` — 1 `set(byid)` + 1 `zadd(tindex)` + 1 `sadd(byref:<ref>)` per ref in
  `refs` (a touch typically carries 1–3 refs). Amortized O(refs) Redis ops. On trim (stream at
  cap), eviction is O(k) where k = overflow count (typically 1 per add): the `_trim` does a
  `zrange(0, overflow-1)`, then per evicted id an `smembers(byref)` + `srem` + optional `del`.
  **So a touch's write cost is ~4–6 Redis commands when it is the 100,001st event and it forces
  one eviction; ~4 otherwise.** Never raises, never blocks (the `BoundaryOutcome.prevent` path
  already guarantees a partial/index-lag is not a lost event).

**Sizing the touch stream (numbers, not adjectives):** the brief counts ~2,000 calls this
session, the fleet more. If the fleet does 10,000 touches/day, the 100k firehose holds ~10 days
of ALL events today; adding touches at a ratio of, say, 4 touches per 1 non-touch event means the
firehose now fills ~5× faster and its whole horizon collapses from ~10 days to ~2 days. That is
the eviction cost the map must name: **the touch kind shrinks the chronicle's time window by
~5×**, so the touch must NOT share `CANONICAL_MAXLEN` with the chronicle — it needs its own
bounded stream (e.g. `events:touch` with its own `TOUCH_MAXLEN`, and the per-agent touch stream
at ~10× that, because "who touched X *last*" wants recency, not a decade).

**Read cost of "last N touches of X":**
- The existing `events_for_ref(ref)` is `smembers(byref_key(ref))` → O(m) where m = every event
  carrying that ref *within the firehose's retention* — then a per-member `get(byid)` (O(1) each)
  and a sort. For a hot file touched 500× in retention, that is 500 `smembers` entries returned +
  500 `get`s + sort = **O(m) Redis round-trips, ~1 per member**, because the byref set is a bare
  set with no recency sub-index. This is the A5 read cost the map must not hide: **"last N
  touches of X" is currently O(retention-count), not O(N)**, and it degrades linearly as a file
  gets touched more.
- The fix A5 owns: a per-ref *capped list* (last-N, e.g. `events:touch:last:<ref>` as a
  `ltrim`-bounded list of event ids) written at capture time (1 `rpush` + 1 `ltrim` per touch on
  a hot ref), so the read becomes `lrange(... , 0, N-1)` = **O(N), independent of how often the
  file was touched**. Write cost rises by ~2 commands per touch on a *hot* ref only; cold refs
  stay O(1). This is the "edges written at write time cost nothing at read time" law, applied.

**Eviction policy:** touch stream is FIFO by `at` (append-only, `maxlen`), exactly like the
firehose; the per-ref last-N list is `ltrim`-bounded to N (default 50). A touch carries its own
`at` and its `ref`, so eviction is by age, not by ref — a cold file's touches age out of the
stream but the list was already trimmed to N, so there is nothing further to reconcile. The one
honesty A5 must add: **`events:touch` has a `retention_ms` field** (the span its maxlen covers at
the current touch rate), surfaced by `context --stats` and printed ON the L0/L1 card, so "last
touched 3h ago" is never false against a stream that trimmed 2h ago.

**The number that gates A1's stream choice:** at 10,000 fleet touches/day × ~4 Redis commands =
40,000 commands/day ≈ 0.46 commands/sec steady-state, with bursts of ~5/s during a hot round.
That is trivially within Redis's budget, which is the real answer to "is this too expensive to
write": no, at any plausible fleet size, and the failure mode (index lags, event still on the
firehose) is already handled. **The read path is the one that needs the capped list, not the
write path.**

---

## 7. LANE — C6/C7, specified as the redesign's owner

The 09-05 redesign's S2 spec already exists and is the owner doc; I re-read it this session
(`design/s2-recall-outcome-adjudicator-spec.md`). C6 and C7 are NOT new machinery — they are the
spec's build order, and my lane is to say exactly where each meets the context-system round.

**C6 = S2 (the observer).** Owns the join already named at `core/recall/at_action.py:849`
(`mark_impression(session_id, target, sources)` — "the outcome-join key") and the stage log at
`:973` (`_log_outcome_stage`, which already delineates PREVENTION vs CONTROL). C6 builds
`core/recall/outcome_observer.py`: read-only, joins impressions (lesson × action × session) to
the Eye transcript, produces four OBSERVATIONS — `COMPLIED` (prescribed shape appears), `VIOLATED`
(forbidden shape appears anyway), `INAPPLICABLE` (situation never arose), `UNKNOWABLE` (transcript
can't settle) — each with a cited Eye address, into Sunshine's `shadow_shelf` observation
register. The denominator law is non-negotiable: precision = `COMPLIED + VIOLATED + INAPPLICABLE`;
`UNKNOWABLE` is excluded from every rate and reported as coverage; no lesson retires on a sample
whose UNKNOWABLE share exceeds its settled share. C6's connection to THIS round is the Eye join
(B5): the observer can only credit `COMPLIED` against the action *actually taken*, which the Eye
supplies, and the Eye only becomes reachable from a recall impression once session_id is forwarded
(M1, above) — so **C6 is downstream of M1**, one more reason M1 is build-first.

**C7 = S1 (promotion).** A lesson whose `refusal_shape` keeps earning `VIOLATED` observations
(fired-then-violated, success was luck) is a promotion *candidate*, not a promotion. C7 ships the
promotion path: `VIOLATED` count crossing a threshold (with a control arm, not a bare tally) → a
curator/operator review → the `refusal_shape` becomes a door rule in the gate engine. The one
thing C7 must NOT do, and which the spec rules, is auto-promote: adjudication is operator-only
(`core/fleet/verdicts.py:156`), a resident-authored promotion is refused loudly, and recall must
not grade recall (`rearm_actor_is_a_trigger_consumer_not_a_deadman`). C7 is the far end of the
pipeline — the "what influenced it" axis closing the loop with a *gate*, not a suggestion — and
it ships last (wave 3), exactly because a gate promoted on thin objective evidence is worse than
no gate.

---

## 8. LANE — B5 (cross-plane-join, my half of the parent fence)

B5 is the parent fence's own deliverable and where the two fences meet. The parent fence's seven
axes are answered by joins-by-stable-key, never by text. My half's contribution is the write-side
kernel; Navi's is the key schema. Three claims:

**B5.1 — session_id is the missing universal join key, and it is reachable but unpassed.**
`event_log.capture` declares `session_id: str = ""` (`event_log.py:142`); the parent fence
measured 0.0% fill; I read this session that `claude_posttooluse.py` *receives* the payload's
`session_id` and resolves it as ground truth over env, but forwards it only to `record_call` and
`_beat_seat` — never to `capture_event`. One line closes it. This is the highest-leverage
reinforcement possible because it retroactively makes every *future* event joinable to the Eye,
and the Eye is the plane that answers "meaning, why, influence" — the three axes no other plane
can. Fix: forward `session_id` (and `agent_id`) into every `capture_event` in the hook path, and
treat `_clean`'s 200-char clip + "unknown" default as a door that must report its own fill
(non-default fill, per the law, not fill).

**B5.2 — the ref type vocabulary has one concept spelled two ways, and it must be bound once.**
The parent fence measured 281 untyped refs that are Redis stream ids — the same referent as
`bifrost:<id>`, one concept two spellings (`token_level_tools_cannot_detect_forked_semantics_by_construction`).
B5's half of the reinforcement is: a single canonical prefix per referent-class, a shim that
rewrites the untyped spelling on read (never on write — the raw event is immutable), and a
lexicon entry that BINDS the concept to its two tokens so the token-level tools can see the fork.
This is reinforcement, not invention: the prefixes (`learn:`, `file:`, `git:`, `bifrost:`) already
exist and are categorically filled (the parent fence's own 25.4%→categorical correction).

**B5.3 — joins are by key, and the key is the *stable* id, not the mutable one.**
`session ↔ seat ↔ commit ↔ task ↔ lesson`: commit is the dangerous one, because a history rewrite
mints a new SHA and orphan the old. The authorship ledger already solves this (`keyed two ways:
sha + (author-date, subject)`, survives a rewrite; `rekey` confirms by two routes and refuses on
disagreement). B5 must NOT introduce a second commit-key; it must *point every other plane's
commit reference at the ledger's stable key* so a lesson citing `git:edfa39babff8` stays
resolvable across a rewrite through `py agent_cli.py sha <old>`. A join that keys on the mutable
SHA becomes false at the next rewrite; that is a `false-if` on every slice that cites a commit.

---

## 9. WHAT I COULD NOT CHECK

- The DSH plugin's actual tool-serialization shape (A4) — Rill owns it; I read the harness hook
  and the runner toolbox, not the plugin.
- The Eye's ingest lag and whether `kind=tool` records would reach `eye find` fast enough for the
  "freshest work" case the parent fence flagged (`eye find <hours-old commit>` → 0 hits). Annex B
  was promised and had not landed when I sealed.
- Whether `locks` has a real resolver or is `agent_cli.py locks` reading a Redis key that is
  itself a candidate for a shelf — I did not chase it; it is a small plane.
- The exact fleet touch-per-day rate — I used the brief's 2,000/session as the only hard number
  and scaled from it; the real number settles A5's `TOUCH_MAXLEN` and is a `context --stats`
  measurement, not a guess I am willing to hard-code.

---

*Heimdall / deepseek — half_a, sealed blind.*
