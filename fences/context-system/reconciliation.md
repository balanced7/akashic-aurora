# Reconciliation -- context-system (the Wave 0 build spec)

**By:** claude (Vandor), conducting. **Written** 2026-09-30 00:40 local, after every filed half was sealed
or committed and after `fence pv` ran (19 verified, 4 MISSING, acknowledged by name in section 5).

**What was read, in order, and when.** The brief (mine, sealed 22:37 09-29). half_a, Heimdall, sealed
22:41. half-sol, Sunshine, filed 23:42 from his production checkout and committed verbatim (31fdb58a);
he read the brief from the git object `1d320009:fences/context-system/brief.md` because his checkout lacks
the directory, and read no peer half. half_b, Navi, sealed 23:56 -- her runner dies at 600 s, so she filed
in three pieces and the door's `write_slot` overwrote each with the next (core/coord/fence_workspace.py:
104-114; docs/WISHLIST.md 2026-09-30); the slot holds piece 3 (the verdict lines) and pieces 1 and 2 are
`research/in-flight/context-system-navi-m1.md` (A7+B1 as one schema, `context.target.v1`) and
`context-system-navi-m2.md` (B4 resolver ladder, E1 field list), which she filed herself and which this
reconciliation cites as her half. **half-rill.md was not filed** by 00:30; Rill's seat is LIVE and idle on
the roster, nudged 00:05. His lane (A4, A6) is Wave 1 and nothing in Wave 0 depends on it (section 7).
Daniel's ADDENDUM 1 (E6 addressable rows, E7 modification verbs, B6 refs-not-prose) reached the seats
mid-round; Navi folded it in; Sunshine's M4 and Heimdall's V9 cover parts of it; the rest is graded here.

**Method.** Three halves, thirty-two slices. Where all three say `keep`, the verdict line below carries
the strongest false-if among them and the tag of the least certain half. Where they differ, the line says
who said what and decides by the brief's own laws (reinforce not invent; no second ledger; zero-is-not-no;
telemetry never costs a tool call) or by a command; nothing below is a defence of the brief. Disagreements
that stay real are recorded as real in section 3.

## 1. Verdict lines (one per slice; the door's `V<n>.` form, the brief's slice id in the body)

V1. [CERTAIN] A1 claude hook touch capture -- keep, BUILD FIRST (three halves) / evolves core/events/event_log.py capture() with kind="touch" and agent/harness/hooks/claude_posttooluse.py, which already receives the path and session_id and forwards neither (session_focus.py:206-235) / write-cost one fail-open capture per hook fire, ~4 Redis commands, ~6 on an eviction (Heimdall's count) / read-cost one byref lookup at context time / false-if a duplicate project+user hook emits two touches, or a failed or refused edit renders as a touch that changed the file (Sunshine), or the extractor mints a target the tool did not touch (Navi).
V2. [CERTAIN] A2 runner toolbox reads/exec/search -- keep, Wave 1, Sunshine's diff plan is the spec / evolves core/comm/toolbox.py _record_file_provenance (:1417-1436, the live write capture) generalised to touch.v1 with action; historical file_edit rows stay immutable and read as legacy action=write / write-cost +1 capture per runner read, exec, search, fetch; targets capped with total and truncated counts / read-cost same byref / false-if capture latency or failure can change a tool result, or one write call emits file_edit AND touch.
V3. [DESIGN] A3 Codex and Cursor parity, hook-tree drift -- keep with Heimdall's merge inside it, Wave 1 / evolves agent/harness/hooks/* as the ONE canonical tree (owner: claude, named here because Heimdall's false-if was "nobody owns the singleton") with scripts/hooks/* as shims that carry no policy; .claude/settings.json's PostToolUse matcher widened to the read, search and fetch tools and PowerShell; Sunshine's per-harness parity fixture (one edit, read, search, command projecting to identical touch.v1 fields) is the gate / write-cost one deduplicated touch per native event / read-cost CI only / false-if a shim grows behaviour, or Cursor emits before a captured payload fixture proves its field mapping.
V4. [INFERRED] A4 DSH plugin touches -- keep, Wave 1, Rill's lane (half-rill pending) / evolves the DSH plugin tool path / write-cost one fail-open capture per plugin-mediated action / read-cost same / false-if the plugin has no reliable target field and a phantom is synthesised, or seat and session are inferred from another subject (Sunshine).
V5. [CERTAIN] A5 sizing and cost -- SPLIT (Sunshine, Navi) into A5a measure and A5b choose; Heimdall's design is A5b's answer, gated on A5a's number / evolves core/events/event_log.py + event_index.py + the PHYSICS manifest / write-cost A5a: `context --stats` measures touches per hour, commands per touch, refs per touch, p95 hook latency, ring retention and the drop counter over 24 h of the claude hook alone; A5b: if touches would shrink the chronicle's horizon (Heimdall: ~5x at four touches per other event), the touch rides its own bounded ring through the same capture door and the same read door, with retention_ms printed on every card / read-cost "last N of X" is O(retention-count) on the bare byref set today (Heimdall); a per-ref capped last-N list makes it O(N) and ships with A1 / false-if a convenience ring becomes a second authority (Sunshine), or the chronicle is evicted by telemetry before the projection exists, or the card says "3h ago" against a ring that trimmed 2h ago.
V6. [DESIGN] A6 derived check-in -- keep, Wave 1, Rill's lane / evolves core/coord/session_focus.py current() (infer the task from the operator's ask, the fence being written, the bench item) / write-cost one write when confidence clears a stated floor (Sunshine), zero on the touch itself / read-cost O(1) / false-if a guess renders as declared focus: the touch carries task_source in {focus, inferred, overridden, none} (Navi's M1) so misattribution is auditable, correction is append-only (E7), and the seat's override is a first-class field, not a ritual.
V7. [CERTAIN] A7 target grammar -- keep, Wave 0, Navi's `context.target.v1` is the schema / evolves session_focus's path handling and EventIndex refs; ONE normaliser module every harness calls (Heimdall's M3, Sunshine's shared helper) / write-cost parse and normalise per target, no I/O but one cached `git worktree list` per process / read-cost zero, targets arrive typed / false-if two harnesses normalise one path two ways, or a worktree path stays unprefixed (`work:<name>:` is the one name), or a heredoc yields fabricated targets instead of zero targets plus `targets_incomplete`.
V8. [CERTAIN] B1 anchor grammar -- keep, Wave 0, the same schema as A7 (one type for both slots) / evolves core/coord/orient.py _parse_target (:38, the typed-destination precedent; half_a's `core/eye/ground.py` does not exist, see section 5) / write-cost zero / read-cost one strict parse, loud on ambiguity / false-if untyped text is guessed into an anchor instead of routed to cast, or file:line loses its worktree.
V9. [DESIGN] B2 one resolver per plane -- keep, Wave 0 for six planes, Wave 1 for the rest / evolves git log and blame, scripts/authorship_ledger.py who, EventIndex events_for_ref, lessons files_affected, locks, session focus (Wave 0); the Eye, recall surfacings, docs, chronicle atoms (Wave 1) / write-cost zero / read-cost each resolver capped in rows and time and composed concurrently (Sunshine) / false-if a resolver returns [] and the scene prints "no touch" instead of a typed state (ok, empty, UNCHECKABLE, error), or one slow plane blocks L0/L1, or a resolver hides its blind spot.
V10. [DESIGN] B3 time scope -- keep, Wave 2 / evolves the joined rows' own timestamps (git author-date, event at, lesson created, Eye known_at) / write-cost zero / read-cost one bucket pass / false-if buckets imply equal coverage when git covers months and the touch ring covers hours, or event time, knowledge time and observation time collapse into one stamp (Sunshine).
V11. [CERTAIN] B4 organ map -- keep, Wave 1, Navi's four-rung ladder is the spec / evolves docs/MODULE_INDEX.md, ARCHITECTURE.md, PHYSICS.md and a ten-row table for docs, fences, research, arsenal, state, tests / write-cost zero at capture, a read-time projection cached by mtime / read-cost one dict lookup / false-if a path in no rung is guessed an organ instead of returning UNKNOWN with the failed rung, or INDEX and ARCHITECTURE drift and the fallback shows dir-as-layer without fog.
V12. [CERTAIN] B5 cross-plane stable ids -- REFUSED as scoped here (Navi), with one exception: session_id forwarding is this round's, see V33 / evolves the parent fence cross-plane-join's deliverable, which this round consumes and does not rebuild / write-cost zero here / read-cost joins by key / false-if a join is by text (Heimdall, Sunshine, Navi agree), or a lesson keys on the mutable SHA rather than the authorship ledger's rewrite-stable key (Heimdall B5.3, filed to the parent fence).
V13. [CERTAIN] C1 eval set -- keep, BUILD FIRST (three halves) / evolves the recall bench precedent (the dissent slice's gold set) / write-cost 40 immutable moments with adjudicated answers / read-cost one reproducible run printing recall@5, precision@3, chrome share / false-if the answer set is written and graded by the seat that owns the trigger (Sunshine): Navi adjudicates, blind to the trigger's code.
V14. [DESIGN] C2 learn derives files_affected -- keep, Wave 1, gated on A1 / evolves learn's intake (39 of 1,526 carry files_affected) / write-cost one recent-touch read at learn time / read-cost zero / false-if a file the seat merely read is asserted as the lesson's scope: derived files are candidates stamped `source: touches`, confirmation is a separate act (Sunshine).
V15. [DESIGN] C3 lessons into the shelf engine -- keep, Wave 2 / evolves core/manuals/shelf.py's engine (SQLite FTS5, MiniLM, RRF, floor), retiring the %TEMP% JSON cache only after latency parity (Navi) / write-cost one embed per learn, one backfill / read-cost one capped hybrid query / false-if the shelf becomes authority over the canonical lessons, or the FTS text and the embedding disagree silently.
V16. [DESIGN] C4 cast -- keep, Wave 2 / evolves the shelf query door as one door over lessons, manuals, docs, notes, bus / write-cost zero / read-cost the expensive branch, char-capped / false-if "available" and "relevant" are conflated or a question anchor is answered by grep.
V17. [DESIGN] C5 intent queries and caps -- keep, Wave 2 / evolves core/recall/at_action.py / write-cost one surfacing receipt per firing / read-cost per-firing caps, chrome once per session / false-if verbs-as-a-shelf re-ranks the whole shelf per firing, or inherited task text outweighs the current operator sentence.
V18. [CERTAIN] C6 objective outcomes -- keep, Wave 3, Heimdall's S2 spec is the owner doc / evolves design/s2-recall-outcome-adjudicator-spec.md and at_action.py's impression and stage log; the observer is READ-ONLY and writes observations (COMPLIED, VIOLATED, INAPPLICABLE, UNKNOWABLE) with a cited Eye address, never verdicts / write-cost one observation per prevention candidate / read-cost a render over the stage log / false-if temporal adjacency is called causality, non-action is graded failure, UNKNOWABLE enters a rate, or credit is flip-only again (Navi).
V19. [DESIGN] C7 promotion to gates -- keep, Wave 3, NEVER automatic (Sunshine's refusal, Heimdall's spec, Navi's false-if all say so) / evolves the door rule engine from a lesson's refusal_shape / write-cost a shadow proposal, negative controls, operator ratification, a versioned gate with rollback / read-cost O(1) gate check with a drillable evidence pointer / false-if a telemetry score acquires the power to block, or a resident promotes its own lesson.
V20. [DESIGN] D1 Eye tool records -- MERGE (Sunshine): the Eye ingests touches as a projection of the canonical touch events, one identity, batched; Wave 1 / evolves core/eye/index.py ingest / write-cost an asynchronous projection, no second per-tool write / read-cost eye find with the grammar it has / false-if the Eye and the ledger mint two identities for one touch and a context read sums both (Heimdall's false-if becomes the pin).
V21. [DESIGN] D2 docs and research retrieval -- decided: ONE engine, the shelf's (Heimdall, Sunshine); Wave 2; Navi's split resolves to D2 = ingest only / evolves the C3 engine with Eye citations joining by source id / write-cost an incremental doc index at commit / read-cost one ranked cited query / false-if two SQLite rankers disagree, or internal documents cross a visibility boundary.
V22. [CERTAIN] D3 time-fog and known_at -- keep, and PULLED FORWARD (Heimdall): its minimal form ships in Wave 0 with E1 / evolves every read path's honesty suffix; in Wave 0 every plane row carries its coverage window and the touch ring its retention_ms / write-cost zero / read-cost one fog line / false-if unknown coverage renders as zero, or an L0 line says "last touched 3h ago" when the ring trimmed at 2h.
V23. [CERTAIN] E1 context.scene.v1 -- keep, Wave 0, Navi's field list is the schema (context-system-navi-m2.md), with E6 folded in: rows[] carry refs from the closed set {event:, sha:, task:, lesson:, doc:, session:} / evolves core/coord/orient.py's scene idiom (SCHEMA, _landmark, _epistemic, _assert_pure) / write-cost zero / read-cost stdlib validation / false-if a renderer demands a field a plane cannot supply and synthesises it (state=UNCHECKABLE is the honest row), or rendered strings enter the schema.
V24. [DESIGN] E2 the context door -- keep, Wave 0 at L0/L1 / evolves agent_cli.py's door pattern and the MCP twin under check_door_parity / write-cost none on reads beyond bounded observation counters / read-cost L0 and L1 on a fixed resolver budget (the brief's seven lookups plus one git log, MEASURED by the door itself, Navi's M2), L2 receipts, L3 raw; a question anchor delegates to cast / false-if L1 shows a leading question instead of all five at once (the addendum), or MCP fields drift from CLI.
V25. [DESIGN] E3 renderers -- keep, Wave 2 / evolves the CLI card, MCP JSON, a standalone Bifrost module plus a snippet for Heimdall (bifrost_ui.py is his), a flightdeck section / write-cost zero / read-cost render only / false-if a renderer re-queries a plane instead of consuming one scene, or drops fog or authority.
V26. [CERTAIN] E4 Discord projection -- keep, Wave 3, Sunshine's contract is the spec verbatim (pure renderer over an existing scene, 1,900-char budget, fold order that never drops anchor, scene id, span or fog, mentions off, T385 fail-closed private route, idempotency on message id + scene id + level) / evolves the Discord reply shape / write-cost one causal reply envelope / read-cost O(scene rows) / false-if the card re-queries Discord-side, leaks raw touch data, or widens a missing private route to global.
V27. [DESIGN] E5 boot L0 lines -- keep, Wave 3, parity measured before the raw-journal peek is removed (Sunshine) / evolves the boot header / write-cost zero / read-cost the seat's own cached L0, not a fresh join (Navi) / false-if a seat's own touches read as "the world" and a sibling's work on the same file is skipped (Heimdall).
V28. [CERTAIN] F1 pins per slice -- keep, every wave / evolves payload-truth fixtures and the live-corpus-probe discipline / write-cost the pins / read-cost CI plus one declared live probe / false-if a pin is written against a drifted fixture, or a test touches prod.
V29. [CERTAIN] F2 drills with receipts -- keep, every wave / evolves the house drill pattern / write-cost one reproduction per slice / read-cost a structural compare of scene facts, never prose (Sunshine) / false-if the verifying seat is the building seat or reads the pins first.
V30. [CERTAIN] F3 gates -- keep, Wave 0 for the context door / evolves check_wiring, check_door_parity and the guardrail ratchet (LOOSE fence dirs counted, per the wish) / write-cost checker maintenance / read-cost commit-time scans / false-if a door has no MCP twin, or a gate is wired and nobody fails it.
V31. [DESIGN] F4 privacy and cost -- SPLIT (Sunshine): F4a redaction and minimisation at capture with loss counters, ships with A1 in Wave 0; F4b the cost manifest and `context --stats`, ships as A5a's instrument in Wave 0 / evolves the internal-plane constraint, PHYSICS bounds, the capture BoundaryOutcome / write-cost redaction before capture and one counter per drop / read-cost the stats verb / false-if a raw command, secret or absolute host path enters a touch, a public surface can query internal rows, or averages hide p95 amplification.
V32. [DESIGN] F5 contract doc -- keep, Wave 3 but a stub lands with Wave 0 / evolves docs/context-system.md on the presentation-primitives pattern / write-cost one versioned update per accepted wave / read-cost one document / false-if it documents later waves as live, or restates authority the schema and pins already hold.

Missing slices, from the three halves and the addendum, each decided:

V33. [CERTAIN] M-a session_id forwarding (Heimdall M1) -- missing, BUILD FIRST with A1: the hook receives `session_id` and passes it to record_call and _beat_seat but never to capture_event, so every existing file_edit, command and learning event is unjoinable to the Eye at 0.0% fill / evolves agent/harness/hooks/claude_posttooluse.py and event_log.capture(session_id=) / write-cost zero, a field already in hand / read-cost zero / false-if the 200-char clip or an "unknown" default counts as fill (report non-default fill).
V34. [CERTAIN] M-b stable event identity (Heimdall M2, Sunshine M3) -- missing, Wave 0: attempt_id = harness + session + native tool_use or event id; capture is idempotent on it / evolves codex_common.dedup_should_skip and EventLog ingestion / write-cost one key per touch / read-cost zero / false-if five harnesses see one call and "who touched X last" sums it twice with disagreeing stamps.
V35. [CERTAIN] M-c one target normaliser (Heimdall M3; Navi's schema; Sunshine's helper) -- missing, Wave 0, it is V7's module / evolves session_focus's normalize_target / write-cost O(len) / read-cost zero / false-if `file:x`, `x`, `./x` and `E:/AI-Setup/x` are four keys for one file.
V36. [DESIGN] M-d eviction-honest reads (Heimdall M4, Sunshine M5, Navi M2) -- missing, Wave 0: known_since and retention on every plane row, a drop counter rendered as fog, and the door pricing its own L1 in `context --stats` / evolves the scene's fog and the stats verb / write-cost one counter / read-cost one line / false-if "no touch" means both "none happened" and "the instrument was down".
V37. [CERTAIN] M-e outcome and attempt contract (Sunshine M1) -- missing, Wave 0 fields of touch.v1: attempt_id, outcome in {succeeded, failed, refused, interrupted, unknown}, duration_ms / evolves the event detail and the hook's outcome accounting / write-cost three scalars / read-cost a filter / false-if a refused edit teaches that it changed the file.
V38. [CERTAIN] M-f capture-time minimisation (Sunshine M2) -- missing, Wave 0, it is F4a / evolves the hook and toolbox boundary guards / write-cost redaction per capture / read-cost zero / false-if a command line, a query string or a worktree's absolute path is stored raw.
V39. [DESIGN] M-g legacy compatibility and append-only correction (Sunshine M4) -- missing; the read half is Wave 0 (file_edit reads as legacy action=write, never rewritten, never synthesised), the correction half is E7 / evolves EventLog refs and pointer honesty / write-cost zero in Wave 0 / read-cost one compatibility branch / false-if history is rewritten or reads are invented.
V40. [DESIGN] M-h surface authorisation matrix (Sunshine M6) -- missing, Wave 1 with E3 / evolves ACL and renderer policy: which touch fields survive CLI, MCP, UI, Discord, flightdeck / write-cost a table / read-cost one filter / false-if a safe anchor makes its raw rows safe.
V41. [CERTAIN] M-i task_source (Navi M1) -- missing, Wave 0 field, see V6 / evolves the touch record / write-cost one enum / read-cost zero / false-if misattribution is silent.
V42. [CERTAIN] M-j worktree writes land on the machine plane (Navi M3) -- missing, Wave 0 pin: a touch captured inside any worktree is written to the shared substrate (akashic-redis 16379) with a `work:<name>:` target, never to per-checkout state / evolves core.world's substrate resolution / write-cost zero / read-cost zero / false-if worktree work is invisible again.
V43. [CERTAIN] E6 addressable rows (addendum) -- folded into E1 (V23) and B2 (V9): every row carries one ref from the closed set; a plane that cannot mint a ref puts the row in fog[] / evolves the scene / write-cost zero / read-cost zero / false-if a row is prose a seat cannot act on.
V44. [DESIGN] E7 modification verbs (addendum) -- missing, Wave 1: retask a touch, link or unlink a lesson to an anchor, correct a seat attribution, mark a doc relevant or not, pin or widen the time scope -- each a WRITE through the owning plane's own door that leaves a ledger event, each an append-only link (Sunshine M4), never a rewrite / evolves session_focus (retask), learn (link), the authorship ledger's rekey (attribution), the scene's pins / write-cost one event per verb / read-cost the corrected row shows both readings / false-if a verb launders provenance: an attribution change is refused unless the actor is the human or the seat being credited, and every correction keeps the original visible.
V45. [CERTAIN] B6 refs not prose (addendum) -- folded into V9 and V23; Navi's closed ref set is the rule and resolvers may not mint kinds / evolves the resolvers' return shape / write-cost zero / read-cost zero / false-if a resolver returns a title where a key was possible.

## 2. Build first, and what is refused

The three halves voted A1 (Heimdall, Navi), C1 (Sunshine, Navi), A5a (Sunshine) and session_id (Heimdall,
as A1's same seam). All four are Wave 0, and the order inside Wave 0 is: **the schema first** (V7/V8, so
every capture writes typed targets from day one), **then A1 with session_id, attempt_id, outcome,
task_source and redaction** (V1, V33, V34, V37, V38, V41, V42), **C1 in parallel** (V13, it needs nothing
from A1), **then the stats instrument** (V5 A5a, V36), **then the scene and the door** (V23, V24, V22
minimal) over the six Wave 0 planes.

Refusals honoured: Heimdall's -- the touch is not a new ledger kind with its own capture path; it enters
through `capture()` and is read through `events_for_ref`, and whatever ring it lives on is storage, not
authority. Sunshine's -- C7 never promotes automatically. Navi's -- B5 stays with the parent fence, which
this round consumes; V33 is the one line that was always this round's because it lives in the hook this
round rewrites. One refusal of my own: Sunshine's "measure before fleet-wide hooks" and Navi's "A1 first"
are both honoured by turning on ONE harness (the claude hook) in Wave 0, measuring it for 24 hours through
A5a, and letting Wave 1 turn on the runner, Codex and DSH harnesses with the numbers in hand.

## 3. Disagreements recorded as real

- **The authorship ledger** (Heimdall's framing verdict): a correction layer of 813 rows at commit
  granularity, not a peer of the Eye. Accepted as a description; rejected as a demotion: it answers "who
  touched it last" for every commit since the post-commit hook, which is the only plane that answers it
  today at all, so it stays a plane row -- with its coverage window printed, which is the honesty the
  framing asked for.
- **A5's home** (Heimdall: keep, sized, own ring; Sunshine: measure first; Navi: split): resolved by
  splitting. Heimdall's numbers stand as the design's basis (4-6 commands per touch, 0.46 commands/s at
  10,000 touches a day, a ~5x horizon collapse if the chronicle shares the ring, O(retention-count) reads
  on the bare byref set); Sunshine's rule stands as the gate (the ring choice is made on a measured rate,
  not an estimate). Both are right about different things and the split says which.
- **B5** (Heimdall keep, Navi refuse): Navi's refusal wins on the brief's own law (this round consumes the
  parent fence's keys); Heimdall's B5.1 wins as V33 because it is a hook-path change; his B5.2 (one
  canonical prefix per referent class, a read-side shim for the untyped spelling) and B5.3 (commits keyed
  by the ledger's rewrite-stable key) are filed to the parent fence as inputs, not built here.
- **D1** (Heimdall keep with a double-count false-if; Sunshine merge): merge wins; the false-if is the pin.
- **D2** (Heimdall one engine; Sunshine merge; Navi split): one engine, the shelf's.
- **D3's wave** (Heimdall: pull forward; brief: Wave 3): pulled forward in its minimal form.
- **The verdict-line convention**: the brief promised `V<piece><n>.`; the checker accepts `V<n>.`. Heimdall
  and Navi renumbered; Sunshine kept `VA1.` (his half sits beside the door and was never going to seal
  through it). Filed on docs/WISHLIST.md 2026-09-30; this reconciliation uses the checker's form.
- **`fence write` overwrote Navi's pieces**: a door defect, not hers; filed on docs/WISHLIST.md 2026-09-30
  and recorded here so the seal's contents are not mistaken for her whole half.

## 4. Wave 0 -- the build spec (each slice ships claude+seat fenced, with a pin and a drill receipt)

| slice | what lands | files | verifier and drill |
|---|---|---|---|
| W0.1 the schema (V7, V8, V35) | `context.target.v1` exactly as research/in-flight/context-system-navi-m1.md: EBNF, `work:<name>:` prefix from `git worktree list`, `file:<path>:<line>[:<col>]` with digit-suffix parsing, `dir/` by trailing slash, url, verb, the closed ref set, ref-before-path precedence; the Bash/PowerShell extraction contract (READ, WRITE, EXEC, SEARCH; pipeline stages walked; heredoc wrappers yield zero targets plus `targets_incomplete`) | one module under core/coord/ (the builder names it; one module, every harness imports it) + tests | Navi: conformance to her EBNF, blind to the code; pins: four spellings one key, `foo:3.py`, a worktree path, a heredoc, a ref that looks like a path |
| W0.2 the touch (V1, V33, V34, V37, V38, V41, V42, F4a) | `capture(kind="touch", refs=[typed], session_id=, detail={schema: "touch.v1", harness, tool, action, targets, targets_total, targets_truncated, attempt_id, outcome, duration_ms, task, task_source, cwd (repo-relative), worktree})` from agent/harness/hooks/claude_posttooluse.py for Read, Edit, Write, NotebookEdit, Bash, PowerShell, Grep, Glob, WebFetch; session_id forwarded on every capture_event in the hook path; fail-open with a drop counter; nothing raw stored; the per-ref capped last-N list written beside the index; the touch ring's maxlen declared in PHYSICS | agent/harness/hooks/claude_posttooluse.py, .claude/settings.json (matcher), core/events/event_log.py and event_index.py, a small core/events/touch.py helper the runner reuses in Wave 1 | Heimdall: the write cost per touch in Redis commands and the ring's retention after 24 h, blind, against his lane; Sunshine: the redaction and outcome pins (a refused edit is `outcome=refused`, no raw command in any record) |
| W0.3 the eval set (V13) | 40 blind moments with a known right lesson (the 2026-08-08 misses M1-M4, the flips, the "tappable button vs hit target" class, this week's lessons); `py agent_cli.py recall-bench` prints recall@5, precision@3, chrome share, and the baseline number is committed with the set | tests/fixtures/recall_eval/ + the verb | Navi adjudicates the answer set blind to the trigger; the receipt is the baseline number |
| W0.4 the instrument (V5 A5a, V36, F4b) | `context --stats`: touches per hour by seat, commands per touch, refs per touch, p95 hook latency, ring retention_ms, drop counter, and the L1 cost of the receipt anchor; run for 24 h before Wave 1 | agent_cli.py + core/events/ | Heimdall reads the 24 h number and rules A5b (shared firehose or own ring) |
| W0.5 the scene (V23, V22 minimal, V43, V45) | `context.scene.v1` per research/in-flight/context-system-navi-m2.md: schema, subject, anchor, level, generated_at, planes[] {plane, state in ok/empty/UNCHECKABLE/error, summary, rows[] each with one closed-set ref, cost, fog with the plane's coverage window, receipts[]}, span, fog[], epistemic, drill, effects=[] | one module beside core/coord/orient.py + a stdlib validator + fixtures | Navi: field parity with her list; pin: a renderer that asks for an unsupplied field gets UNCHECKABLE, never a synthesised value |
| W0.6 the door (V24, V9 six planes, V30) | `py agent_cli.py context <anchor> [--level 0\|1] [--since] [--planes]` and the MCP twin; planes: git (log; blame at file:line), authorship ledger, touches (the ring plus legacy file_edit as action=write), lessons by files_affected, locks, session focus; each resolver capped in rows and time; L1 shows all five questions at once; a question anchor returns UNCHECKABLE with the drill `find` until cast lands; check_door_parity green | agent_cli.py, ai_setup_mcp.py, core/coord/ | F2: a second seat (Sunshine, from a runner seat) reproduces the L1 card for `file:arsenal/practice.py` and compares scene facts field by field; the receipt is the two scenes and the diff |
| W0.7 the stub doc (V32) | docs/context-system.md: the schema names, the ring and its retention, the five questions and which plane answers each, the Wave table | docs/ | pv over this reconciliation's cites |

Receipt for Wave 0 as a whole: the L1 card for `file:arsenal/practice.py` reproduced by a second seat, and
`context --stats` after 24 hours of the claude hook. Wave 1 does not open without both.

## 5. M1-PV: the four MISSING citations, acknowledged by name

- half_a `core/eye/ground.py` -- does not exist; the typed-destination parser half_a meant is
  core/coord/orient.py:38 `_parse_target` (V8 above cites it).
- half_a `core/recall/outcome_observer.py` -- proposed by C6's spec, not a file yet (V18).
- half_a `docs/context-system.md` -- F5's deliverable, not a file yet (V32, W0.7).
- half_a `AI-Setup/conversation.py` -- an illustrative path in M3's four-spellings example, not a cite.
Sunshine's half sits beside the door and pv does not walk it; its load-bearing claims were checked by hand:
`.claude/settings.json`'s PostToolUse matcher and the shim at scripts/hooks/codex_posttooluse.py are as he
says; `toolbox.py:1436` is the brief's own measurement and matches Navi's :1417 `_record_file_provenance`.

## 6. Later waves (each re-fences before it ships; the spec here is the inputs)

- **Wave 1:** A2 and A3 (Sunshine's diff plans verbatim), A4 and A6 (Rill's lane, his half as input), B2's
  remaining resolvers, B4 (Navi's ladder), C2, D1 (merged), E7 and M-h. Receipt: the same card from a
  runner seat, a Codex seat and the DSH seat shows their own touches.
- **Wave 2:** C3, C4, C5, D2 (one engine), B3, E3. Receipt: recall@5 moves against W0.3's set; the Bifrost
  panel shows the card.
- **Wave 3:** C6 (S2 observer), C7 (ratified only), B5 (parent fence), D3 full, E4 (Sunshine's contract),
  E5, F5. Receipt: a lesson retired by objective precision; a promoted gate refuses at a door.

## 7. Open items, dated

- **half-rill.md** not filed at 00:30 09-30. Rill's lane is Wave 1; when his half lands it is folded by a
  dated addendum beside this file, never by editing sealed text; if it has not landed when Wave 1 fences,
  A4 and A6 open with claude+Heimdall and Rill verifies.
- **Navi's pieces 1 and 2** live outside the slot (research/in-flight/context-system-navi-m1.md, -m2.md);
  committed under her name with this reconciliation.
- **The parent fence** cross-plane-join receives Heimdall's B5.2 and B5.3 as inputs.

## Disclosed

I wrote the brief, so the verdicts above grade my own map; every `split`, `merge`, `refuse` and pulled-
forward slice is a place the map was wrong. I read half_a, half-sol and Navi's three pieces only after
each was sealed or committed, and read no half before its author said it was done.
