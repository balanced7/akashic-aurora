# Wave 3 -- reconciled build spec (RB-8..12 + DictStore differential; dual-half, dated)

Status: current  (2026-07-11)
Class: build-spec (the artifact each Wave-3 gated ship cites -- T031 hook 1)
Governs: T029 Wave 3. Build order (claude-ruled, Daniel delegated): RB-8 + differential
harness first, then RB-9/10/11/12 riding the hardened door.
Halves reconciled: research/reviewed/claude-w3-design-2026-07-11.md +
research/reviewed/deepseek-w3-design-2026-07-11.md (both blind; deepseek's delivered whole
via the restored write door, self-verified -- no clip this time).
Slice texts: docs/resilience-battery-slices-2026-07.md lines 136-188.

## Blind convergence (the gate)

Both halves independently: per-title sentinel/head key gated by the C3 CAS primitive
(plain key, NOT hash-field CAS); record-then-claim-then-retire write order; only the race
winner retires; loser cleans up its own record and errors LOUDLY with the winner named;
first-note gated by expected-None/nx; normalization NFC-based at the single write door
with a read-side bridge; validation before write; detector/warning surfaces additive (no
default-read behavior change); deterministic multi-key sort + graceful empty-state;
differential = same op sequence on both backends, divergence is the finding; no auto-merge
of title collisions; no pruning; orphan repair surfaces in doctor, never auto-runs at boot.

## RB-8 -- supersession CAS (BUILDS FIRST)

Mechanism (deepseek's shape adopted -- update_atomic, the existing higher-level primitive,
store.py:194-206; claude's key namespace + retry cap + id fix folded in):

- Sentinel key `mem:decisions:head:{norm_title}` (claude namespace: decisions-scoped so
  experiences/reflections can grow their own heads later; deepseek's bare mem:title:*
  rejected as ambiguous).
- decide() = SINGLE attempt: write record + index, then
  `update_atomic(head_key, _claim, retries=1)` where `_claim(current)` returns dec_id iff
  current is claimable: current == supersedes, OR current is None, OR current names a
  record that is missing/superseded/retired (deepseek FM2 dangling-pointer handling +
  claude Q4 resolution -- retire_decision never touches the sentinel; a retired current is
  claimable by construction). Foreign ACTIVE id -> return None (lose cleanly).
- Loss surfaces TWO ways and both are handled: _claim-None (update_atomic returns the
  winner's id) and CASConflict (the cas cycle itself raced). Either way: the loser retires
  its own just-written record, then raises SupersedeRaceError naming the winner (errors
  that teach).
- Retry policy lives at the DOOR, not in decide() (deepseek: in-decide retry re-gens ids
  and rewrites bodies wastefully): a small `decide_with_retry` helper in agent_memory owns
  re-read-head -> corrected supersedes -> retry, CAP 3 (claude: an uncapped door loop can
  livelock), then fail loud. AUTO-RESOLVE doors use the helper -- cmd_note re-note, wrap
  --focus, wrap where-we-are. An EXPLICIT `--supersedes <id>` BYPASSES it: single-attempt
  decide(), loser fails loud naming the current head -- silently re-pointing a target the
  caller named by id would supersede a record they never chose. [SETTLED 2026-07-11,
  supersedes this paragraph's earlier all-doors wording: claude reconciliation flag ->
  deepseek design-review AFFIRMED ("retrying an explicit target would silently supersede
  the WRONG record") -> impl @b044d6b -> verify GATE GREEN. Door parity remains a check,
  not a hope: scripts/check_door_parity.py covers all four doors.]
- Only the CAS winner retires the old id (closes R-a lost-retire fork; makes the
  _retire_record read-modify-write single-writer in practice, closing R-b).
- Id generation hardened (claude R-c, deepseek missed): ADR_<ts>_<uuid4.hex[:8]> --
  same-second collisions drop ~5 orders; ids stay prefix-sortable.
- Write order record -> claim -> retire (both halves): head-readers never see two actives;
  the scan-reader residual gap is the retire write itself (RB-12 ordering makes it
  render-invisible).
- Orphaned sentinel (crash between record write and claim -- deepseek FM1): DETECTED by a
  doctor scan (walk mem:decisions:head:*, reconcile against records), surfaced, never
  auto-repaired at boot (deepseek cut #4; supersedes claude's auto-heal lean).

Pins (pre-registered, tests/test_w3_supersession_cas.py, committed BEFORE impl):
  1. Interleaved supersede of one title (two handles, deterministic schedule): exactly one
     active head; loser's record auto-retired; SupersedeRaceError names the winner.
  2. Concurrent FIRST notes (both supersedes=None): exactly one active (nx gate).
  3. decide_with_retry: loser retries against the corrected head and SUCCEEDS (chain
     stays linear: C supersedes B supersedes A -- never two claiming A); cap 3 then loud.
  4. Retired/dangling current head is claimable (retire-last-note then re-note works).
  5. Same-second id generation x1000: zero collisions.
  6. Uncontended write: zero retries, plus exactly one extra get+cas round-trip.
  7. Lazy head bootstrap on a pre-head corpus; re-run = no-op (feeds RB-11).

## RB-9 -- title normalization

`_normalize_title = NFC + strip` ONLY (deepseek adopted): NO case-folding, NO internal
whitespace collapse -- case and spacing can carry meaning; precision-first, don't merge
what might be distinct. Claude's casefold recorded as the named escalation path (a future
RB with a dated allowlist) if a real case-collision bites. Stored title = normalized form
(deepseek; simpler than claude's verbatim-display split -- NFC+strip losses are noise).
Read-side comparisons normalize too (both halves: the bridge for pre-RB-9 records).
Deploy-time doctor scan lists pre-existing titles that now normalize equal -- flagged for
manual ruling, never auto-merged (both cut lists).
Pins: trailing-space re-note supersedes clean title; NFC==NFD; case-distinct titles NOT
merged; pre-RB-9 dirty title found by clean re-note; existing ASCII corpus = zero change.

## RB-10 -- supersede-target validation + all-retired detector

Validation BEFORE any write (deepseek order): target must exist, must not be self
(deepseek), and must be ACTIVE -- superseding an already-superseded id is refused with a
teaching error naming the current head (claude; the sentinel would catch it as a race,
but the teaching error beats a generic one).
`get_retired_titles()` as a SEPARATE additive surface (deepseek): vanished title groups
render in notes --all footer, boot one-liner when non-empty, doctor; default get_decisions
unchanged. Scan time-bounded to the 90d window; older vanished groups only via --all
(deepseek FM2).
Review fold-in (deepseek design-review 2026-07-11, MUST for this slice's builder): the
stale-explicit-target refusal is a PRE-READ of the head sentinel in the door's explicit
branch BEFORE decide() -- saves the write+claim+cleanup cycle -- and its teaching error
must NOT advise retrying (that advice is correct only on the decide_with_retry path).
Shapes: stale target -> "refused: explicit target <id> is not the current head (head is
<id2>). Drop --supersedes to auto-resolve, or name the current head." Missing head ->
"no existing note for this title; drop --supersedes for a fresh first note."

Pins: ghost target refused pre-write; self refused; superseded target refused w/ head
named; all-retired title listed; one-active title not listed; stale explicit target
refused pre-write with the no-retry teaching error (review fold-in above).

## RB-11 -- migration idempotency + chain-length warning

Migration pin key `mem:migration:{name}` claimed via cas(None) so concurrent runs cannot
both execute (deepseek); the migration body must ALSO be inherently idempotent -- the pin
is an optimization, not the safety (deepseek FM1). RB-8's lazy head bootstrap re-run =
no-op is pinned here too (claude).
Chain-length warning: RENDER-side line + log (merged), threshold 50, no write-side gate,
no exemptions; threshold becomes a T034 dial when the registry lands (deepseek FM2 tie-in;
until then it is a named constant the T034 manifest will claim).
Pins: double-run no-op (state hash equal); warning fires at 51 not 49; default read path
cost unchanged.

## RB-12 -- deterministic ordering + graceful empty state

Sort key (created_at, title, id) everywhere a list renders (deepseek's title-secondary
adopted over claude's two-key: human-meaningful tiebreak before the opaque id) --
get_decisions, notes, boot RECENT NOTES, memory.md projection. Governing-arc candidate
list pre-sorted by doc path before selection (deepseek -- beyond claude's scope; kills the
same-tier tie instability in _orientation_header, the F2 lineage). Empty-state gap lines
with a scan-distinct [GAP] prefix (deepseek FM2): where-we-are, governing arc, RECENT
NOTES, memory.md projection; boot on an EMPTY store exits 0.
Pins: same corpus -> byte-identical render twice; same-timestamp ties stable across calls
AND across backends; zero-notes boot renders gaps, exit 0.

## DictStore differential

BUILD REALITY (deepseek named it; claude assumed otherwise): an in-memory `DictStore(Store)`
does not exist -- it is built as part of this slice pair. Pure dicts, RLock, atomic cas
under the lock, NO file I/O, NO TTL support v1 (setex/expire/ttl raise NotImplementedError
loudly rather than lying -- deepseek cut #3; decision paths never touch TTL).
Harness tests/test_store_differential.py: op sequences as data; after EVERY op the RETURN
VALUES must match (deepseek rigor: hset returns new-field count, zadd new-member count,
cas bool), and the final full state dump must match. Sequences: (1) the exact RB-8
protocol steps, (2) deterministic two-handle contention schedules (claude), (3) seeded
random op soup, fixed seed (claude), (4) same-score zset ordering (lexicographic by
member -- deepseek pin). Redis-absent -> pytest.skip (both halves; the local suite + ship
gate have Redis).

## Cut list (merged, binding)

No auto-merge of title collisions. No prune verb. No TTL in DictStore v1. No boot-time
auto-repair of sentinels (doctor surfaces, operator rules). No hash-field CAS extension to
the Store contract. No global write lock. No CRDTs.

## Cost (both halves agree)

Supersede write: +1 get +1 cas (~2 round-trips, human-paced path). Boot: unchanged default
reads; detector/warning scans are 90d-bounded and boot-frequency. Uncontended latency
pinned in RB-8 pin 6.

## Verify record -- pair 1: RB-8 + differential (2026-07-11)

GATE GREEN (deepseek [verify], bus delivery; verbatim file persistence requested, part 1
captured by the listener seat): 9/9 spec-fidelity checkpoints; 10/10 pre-registered pins
flipped skip->PASS with zero assertion weakening; four production doors race-safe
(cmd_note explicit = single-attempt decide, cmd_note re-note + wrap --focus + wrap
where-we-are = decide_with_retry); no mem.decide() caller exists outside tests.
3 non-blocking findings, all pre-acknowledged by this spec: (1) orphaned-sentinel doctor
scan deferred (cut list, FM); (2) claim->retire crash window = dual visibility,
self-heals on next re-note, non-forking; (3) threaded smoke runs on DictStore
(RLock-serialized) -- real-Redis interleaving untested, no latency-injector harness
exists (candidate for a later resilience tier). Differential harness LIVE FINDING
verified safe: FileStore/DictStore zset tie-order moved insertion-order -> (score,
member) lexicographic, aligning with Redis's documented contract -- insertion order was
an implementation accident, never a contract; existing consumers already lived with
Redis ordering. Impl @b044d6b.
