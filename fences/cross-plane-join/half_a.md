V1. The event plane and the Eye are two distinct stores (Redis firehose + JSONL ledger vs state/eye/eye.db SQLite) with no shared join key written by any caller -- session_id is filled 0.0% across all 17 event kinds, confirmed live on a handoff event captured minutes ago. [CERTAIN]
V2. The connectome's edge table keys are Eye event addresses (session:line) ONLY -- there is no edge that connects a transcript event to a commit, a file, a task, or a lesson, and extending it would require a second node universe it was never built to hold. [CERTAIN]
V3. The single highest-leverage, cheapest fix is threading session_id through the event capture door (it is already a parameter on EventLog.capture at event_log.py:108 and is already passed to mem.decide at agent_cli.py:4102, but never to any capture_event/capture call), which turns the event plane into the same address space the Eye already indexes. [DESIGN]
V4. The join layer should be a typed resolver vocabulary over ground's existing target grammar (verb:/seat:), NOT a new plane and NOT a new edge class in the connectome -- the connectome holds utterance-to-utterance edges, and cross-plane linkage is a different category of edge that belongs at the resolver, not baked into the transcript walk. [DESIGN]
V5. "Reliable and performant" is already half-bought: the read path (byref index at event_index.py, the authorship ledger, the sha resolver, the eye.db index) is fast; the write path is where the debt is, and it is a one-line-per-call-site debt, not a new-index debt. [INFERRED]

---

## 1. VERDICT ON THE FRAMING

The brief is asking the right question but diagnosing the wrong wound, and it under-sells one
measurement that should be the headline.

Daniel said "I know we already have this" and asked to REINFORCE. The brief's evidence pack
correctly proves the pieces exist scattered across four planes (eye.db, the event firehose, the
authorship ledger, the rewrite-maps). What it does not say out loud -- and what changes the
design -- is this:

**The house does not have a linkage problem. It has a MISSING-WRITER problem for exactly one
field, plus a MISSING-RESOLVER-TYPE problem for exactly one class of address.**

The load-bearing fact is section 3.3: `session_id` is `""` on **all 17 event kinds**, confirmed
not by recall but by reading the raw record. I re-ran it live: a `handoff` event captured minutes
ago (id `1790455207902-0`, agent `claude`, at `2026-09-26T20:40:07`) carries `"session_id": ""`
and `"refs": []`. That is not "sparse" fill; that is a **door signature**: the parameter exists
(`event_log.py:108` `session_id: str = ""`), the write path cleans and stores it
(`event_log.py:142`), and **no caller passes it**. Meanwhile the SAME session id is ALREADY passed
to the memory/decision plane at `agent_cli.py:4102` (`session_id=args.session or ""`). So the
session id is in the process's hands at write time; it is simply never carried into the event
plane.

That reframes the whole ask. The expensive, scary, "build a new plane" answer Daniel is
implicitly warning against ("without building a new plane") is not required. Reinforcing the
linkage is:

1. **Write-time**: thread `session_id` (and make the ref vocabulary typed, see V4) through the
   ~15 capture call sites. Cheap, additive, reversible.
2. **Read-time**: extend `ground`'s target grammar with the join types that already have records
   (`commit:`, `file:`, `task:`, `lesson:`, `atom:`, `seat:`), so a seat triangulates by asking
   the resolver "show me everything that points at X" instead of knowing which door to walk.

The seven axes he named are the right acceptance surface. But three of them ("patterns", "the
why", "what influenced it") are ALREADY served by the Eye (`eye freq`, `lookback`, `knowledge-map`,
`eye trace`) -- they do not need a join, they need the OTHER FOUR (things / provenance /
who-did-what-when / what-influenced-it) to resolve into their address space. The join's job is not
to add meaning-axes; it is to make the existing meaning-axes addressable from the thing-axes.

**One correction to the evidence pack, offered as a finding not a dispute:** section 3.3 says the
door "offers the parameter; no caller passes it." That is nearly right, but I found the parameter
IS passed -- to a DIFFERENT plane. `agent_cli.py:4102` and `4109` pass `session_id=args.session or ""`
into `mem.decide`/`decide_with_retry`. So the session id is not "unavailable at the capture sites";
it is **already being threaded to the memory plane at the exact same CLI verb layer that could
thread it to the event plane**. The gap is narrower than the pack implies, which makes the fix
both cheaper and more embarrassing. (If the annex's lane "every capture() call site and whether a
session id was reachable-but-unpassed" confirms any site where the id is genuinely NOT reachable,
that is the real scope; I could not find one.)

## 2. THE DESIGN

### 2.1 Write-side: thread session_id through the capture door (the one-field fix)

`EventLog.capture` already accepts and stores `session_id`. The fix is at the call sites. The
canonical ones to change, each a one-line addition (`session_id=<the id in scope>`) or, better, a
single default resolved inside the door:

- `get_event_log()` is a module singleton. It has no notion of session. The RIGHT place to close
  the loop is a context the harness already maintains: `CLAUDE_CODE_SESSION_ID` /
  `CLAUDE_SESSION_ID` env (read at `agent_cli.py:6449` and `6912` today) and `args.session`.
  Add a `_ambient_session_id()` helper in `event_log.py` that reads those env vars as the
  default, so `capture_event` fills `session_id` WITHOUT every call site changing.

Concretely, the smallest correct change:

- `event_log.py`: add
  `def ambient_session_id() -> str:` returning the first non-empty of
  `CLAUDE_CODE_SESSION_ID`, `CLAUDE_SESSION_ID`, else the bus identity's incarnation if set,
  else `""`. Default `capture()`'s `session_id` param to call this instead of `""`.
- Keep the `session_id=""` parameter for tests that must pass `""` explicitly (three-state
  honesty: an empty id after this change means "genuinely no session in scope", not "nobody wired
  it" -- but that distinction must be re-measured per the NON-DEFAULT fill law, not assumed).

This is the line that makes the event plane joinable to the Eye at all, and it costs nothing at
read time.

### 2.2 Write-side: make the untyped refs honest (281 of 3000)

Section 3.2 found 281 untyped refs that are Redis stream ids -- the SAME referent as `bifrost:`,
spelled bare. This is exactly the house law `token_level_tools_cannot_detect_forked_semantics_by_construction`:
one concept (a bus message id), two spellings (`bifrost:<id>` and bare `<id>`), invisible to every
token-level tool. Fix at the TWO writers that emit bare ids:

- `expectations.py` `_emit_dead` / `_emit_settled` (around lines 205-260) currently
  `refs=[str(orig_id)]` -- the bare stream id. Change to `refs=[f"bifrost:{orig_id}"]`.
- Confirm the same for the settle/echo path.

This is a one-concept-one-spelling normalization, not a schema change. It is the cheapest way to
make the `events_for_ref` door return the complete set instead of two disjoint halves of it.

### 2.3 Read-side: extend ground's target grammar -- the join resolver

Section 3.5 is the gem of the pack and the brief slightly buries it: `ground --help` already says
"typed target: `verb:<name>` or `seat:<id>`". That is a **universal-address resolver with two
types wired**. The join is NOT a new plane; it is **new target kinds on the resolver that already
exists**, each resolving through the records that already exist:

| target kind | resolves through | record that already exists |
|---|---|---|
| `commit:<sha>` | `scripts/authorship_ledger.py who`, `sha` resolver (T410 rewrite-maps), `git:` refs on command events | authorship ledger `state/authorship/seats.jsonl` (813 rows) |
| `file:<rel>` | `event_query.events_for_ref('file:<rel>')` | `_record_file_provenance` at `toolbox.py:1417` (shipped, pinned) |
| `lesson:<exp>` | `agent_cli recall --full learn:experiment:<name>` + `learn:` refs | 235 `learn:` refs in the sample |
| `task:<id>` | task ledger | git-durable ledger (171 done / 26 active at boot) |
| `seat:<id>` | already wired in ground (continuity) | incarnation cards, per-agent event stream |
| `session:<id>` | (this design's whole point) the event plane keyed by the now-filled session_id | the Eye's own session dimension |

The resolver returns, for each target, the SAME shape `ground` already returns (rungs of
evidence), plus the cross-plane fan-out: "what events, files, commits, lessons, tasks point at
this." That is the triangulation Daniel is asking for, and it is a view over existing records, not
a new store.

### 2.4 What I would NOT do: bend the connectome into a cross-plane graph

This is where I expect to diverge from half_b, and deliberately. The connectome
(`core/eye/connectome.py`) is a beautiful, careful organ whose node identity is `event_id =
"<session>:<line>"` -- an address **inside the transcript plane only**. Its edge kinds
(`follows` / `same_utterance` / `adjacent`) are all utterance-to-utterance relations with a
recorded/derived/inferred evidence grade. Adding a `commit` or `file` node is not "extending the
connectome"; it is introducing a second node universe into a table whose `src`/`dst` TEXT PRIMARY
KEY would then silently accept both `session:line` and `git:sha12` and `file:rel` in the same
columns -- the exact forked-identifier coercion the house law
`corpus_digest_path_is_not_a_universal_join_key` forbids. The connectome should stay
utterance-scoped. The join belongs at the resolver, where each target TYPE declares which records
back it, and where `UNKNOWN` is first-class.

## 3. ORDERING, WITH THE REASON

**This is a strict ladder; every rung produces the fuel the next burns. State it because the
reconciler is the only one positioned to see the whole ladder.**

1. **`ambient_session_id()` + default in `capture()`** (2.1). REASON: this is the PRODUCER.
   Nothing else can be read-side-verified until events carry a session id. It is also the only
   rung with a forward-only cost -- old events keep `""`, which is honest (three-state: "captured
   before the fix" ≠ "no session"), and the NON-DEFAULT fill law warns us to measure fill-over-nondefault,
   not fill-over-empty, from this point on.
2. **Untyped-ref normalization** (2.2). REASON: independent of (1) but cheap and it removes the
   forked-spelling ambiguity the resolver would otherwise have to special-case. It burns nothing
   from (1), but (1) and (2) together make `events_for_ref` a clean door.
3. **`commit:` and `file:` resolver kinds** (2.3). REASON: these are the two thing-axes with the
   most already-shipped backing (authorship ledger + file_provenance slice). They are the
   proof-of-value before touching `lesson:`/`task:` which carry more heterogeneous ids.
4. **`session:` resolver kind + the Eye-freshness guarantee** (2.3 + out-of-scope note). REASON:
   this is the payoff -- "triangulate quickly between things, meanings, provenance" -- and it
   only makes sense once (1) is live, because the session is the key that joins the event plane
   to the Eye's transcript plane in the first place.

The dependency to state explicitly: **(1) is a build-order precondition for (4), and (3) is the
falsifiable proof that the resolver approach works at all, so it must land before the full
vocabulary.** If someone proposes landing the resolver kinds first and backfilling session_id
after, they are building the read surface before the write fuel exists -- the "built ≠ wired"
law in reverse.

## 4. WHAT I WOULD NOT BUILD, AND WHY

**A cross-plane edge table.** The house's own maxim -- "gate evolution beats a new organ" -- plus
the specific forked-id hazard in 2.4 makes a new SQLite/Redis table of `(thing_a, thing_b,
edge_kind)` a category error: it is a regenerable projection masquerading as durable history, and
it would immediately re-ask every question the authorship ledger already answered once about
surviving rewrites. The resolver is the organ; the records are the store.

**A session_id backfill of history.** Do NOT write a script that scans `events_raw.jsonl` and
guesses session ids from timestamps. That launders an inference as a record, which is precisely
the class the Eye exists to refuse (see connectome's `adjacent` grade). Old events keep `""` and
read as "pre-fix"; the column is forward-only.

**Normalizing the heterogeneous ref prefixes (`learn:`, `mem:`, `claude:`, `agent_cli:`) into one
scheme.** The house law against coercing heterogeneous ids into one key says keep them per-corpus
and publish coverage WITH `UNKNOWN`. The only normalization worth doing is the 2.2 one, because
that is one CONCEPT in two spellings, not two concepts.

**Any UI/dashboard.** Out of scope by the brief; also the join must be correct before it is
rendered.

## 5. THE CHEAPEST EXPERIMENT THAT WOULD FALSIFY MY OWN DESIGN

One command, run after rung (1) lands:

```
py agent_cli.py events --limit 2000 --json | py -c "import json,sys; r=json.load(sys.stdin); print(sum(1 for x in r if (x.get('session_id') or '').strip()), 'of', len(r))"
```

If, after `ambient_session_id()` is wired and a live session has run, this still prints `0 of
2000`, then the session id is NOT reachable at the capture sites through the env/args path I
assumed, and my whole design collapses to "the id has no writer anywhere on the event path,"
forcing a different mechanism (e.g. the harness hook at `scripts/hooks/claude_posttooluse.py`
must stamp it, which is a heavier and riskier change). Conversely if it prints a NON-zero number
that is still far below the non-default fill rate of `agent_id` (which is ~100%), that is a
half-wired door and proves the ambient default is not being honored by the bus/daemon paths,
which is a wiring bug, not a design bug. **This experiment is one line and it settles the single
riskiest assumption in the design.** I cannot think of a cheaper falsifier.

(A secondary falsifier: `py agent_cli.py events --get event:events:raw:<newid>` after a session
run, checking `session_id` in the payload is the actual id and not the empty string -- confirms
the STORE keeps what the door now passes.)

## 6. COST

- **Per-write**: one `os.getenv` read per `capture()` (two env lookups, no I/O). Negligible. The
  ref normalization (2.2) is a string-prefix change at two writers, zero marginal cost.
- **Per-read**: the resolver kinds are all index-backed already -- `events_for_ref` is O(refs)
  via the byref set (`event_index.py` `BYREF_PREFIX`), `authorship_ledger.py who` is a JSONL
  lookup keyed by sha AND by `(author-date, subject)`, `sha` is a rewrite-map chain walk. No new
  read path needs a scan. The Eye-freshness delta (see below) is the only read cost and it is
  bounded by ingest, not by the join.
- **Storage growth**: one `session_id` string per event (a UUID-ish, ~40 bytes) + the normalized
  `bifrost:` prefix (2 bytes × 281 refs). Effectively zero against CANONICAL_MAXLEN=100k bounded
  firehose. No new tables.
- **At 10x corpus**: the firehose is already bounded (maxlen), the byid/byref indexes are already
  lockstep-evicted (`_trim` in `event_index.py`), the eye.db index is incremental by (mtime,
  line-cursor). The resolver scales linearly with per-target fan-out, not with corpus size,
  because every backing store is already indexed by the thing being resolved. The one thing that
  grows is the Eye ingest time (0.7s full corpus today), which is out of scope but is the only
  term that could make "quick access to in-depth analysis" slow at 10x.

## 7. WHAT I COULD NOT CHECK

- **Whether a session id is reachable at EVERY capture site.** I confirmed it is reachable at the
  CLI/narrative/comm layers (env + `args.session` + bus identity), but the annex lane "every
  capture() call site and whether a session id was reachable-but-unpassed" is the authoritative
  census and it is not in front of me as of this writing. If it finds a site inside a subprocess
  with no env passthrough, rung (1) is incomplete as designed and I flag that now rather than
  discover it late. **[INFERRED pending annex]**
- **The Eye's real ingest lag.** I read the docstring claim (0.7s full corpus, incremental by
  mtime/cursor) but did not re-measure `eye find <fresh-commit>` myself. Section 3.4's "0 hits for
  a commit made hours earlier" is the brief's measurement, and if my design's freshness story
  rests on it, I should have re-run it. I did not, for time; the guarantee my design needs from
  ingest is "an event captured this session is findable this session," and whether the current
  ingest honors that is an open question I am handing to the reconciler. **[UNCERTAIN]**
- **Whether `lookback`'s two control failures (3.6) are the relevance floor, the layer set, or the
  index.** I did not diagnose it. It is in scope per the brief and it matters to the "the why"
  axis, but it is orthogonal to the join -- a broken meaning-organ stays broken whether or not
  the join is fixed, and fixing the join does not fix it. I am explicitly NOT folding it into my
  design; it is a parallel defect, and conflating it with the join would let a broken instrument
  pass under a join-green gate.
- **The exact shape of `sha`'s AMBIGUOUS/DROPPED outputs across all three rewrites.** I trust it
  exists (it is in my tool surface) but I did not audit whether every cited SHA in the chronicle
  resolves. The `commit:` resolver kind inherits whatever hole that audit would find.

---

### Annex note

The seven-lane evidence annex (3.9) had not landed when I wrote this. It is additive and, per the
brief, not expected to overturn 3.1-3.8. The ONE thing I explicitly flagged as pending on it is
the per-call-site session-id reachability census (section 7, first item) -- if it lands before I
seal, I will re-verify and amend; if it lands after, this sentence is the record of what it would
have changed and did not.
