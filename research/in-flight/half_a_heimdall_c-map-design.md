# c-map-design — HALF A (Heimdall, the MECHANISM half)

Fence: c-map-design. Slot: half_a. By: deepseek. Filed blind (I have not read half_b).
Scope of this half: what the generator CALLS, what the eye grammar EXPOSES, what neither
may know about the other. No spec prose. Every claim carries VERIFIED/INFER/GUESS and
file:line or a stream id where verified.

---

## 0. The integration truth in one sentence

The map generator is a **read-only projection over three existing append-only planes**
(`events:raw`, `state/eye/eye.db`, `recall:outcome`), and its zoom seam is **not N new
functions — it is 9 existing read functions, all already callable, all already carrying
their own honesty envelope.** The generator does not add a transcript reader, a walker,
a frequency engine, or a position loop. Those exist. The generator's only genuinely new
code is the *join* (the event-plane contract turned into node render data) and the
*stamp* (generation honesty). Everything else is a call into `core/eye/`.

---

## 1. COUNTERS over P1–P5 (attack the opening position)

### C1 — counter to P1 ("one substrate, three projections; the map owns no truth, writes nothing")

**ACCEPTED, with one sharpening. The "writes nothing" is TRUE for the map generator, and
it must be stated as a CONTRACT, not an aspiration — because one of the three planes is
NOT rebuildable and the opening position does not say so.**

VERIFIED: the master/derived split exists and is load-bearing. `core/eye/index.py` docstring
lines 1–22 (the projection law) + `_SCHEMA_VERSION = 5` at index.py:105 with the migration
comment at index.py:96–104: "migrations ADD, never DROP. Derived tables (pyramid, edges) are
genuinely disposable and may be rebuilt freely; `events` may not."

VERIFIED: the scar that forced that law — index.py:94–104: v2 "shipped as a wipe-and-rebuild
on the design's own words… the first live run destroyed >=219 events from two sessions whose
transcripts had rotated off disk hours earlier. For a rotated session the projection IS the
archive."

VERIFIED: `routes.py` has a **second** master/derived split, orthogonal to the Eye's, and it
is the one the opening position must not flatten. `core/eye/routes.py:17–33` (THE SUBSTRATE
SPLIT): `state/coord/routes.jsonl` is append-only, TRACKED, authored truth; the `routes` /
`route_steps` / `route_walks` tables in `eye.db` are a REBUILDABLE projection. `routes.py:47:
JOURNAL_PATH = _REPO_ROOT / "state" / "coord" / "routes.jsonl"`; `routes.py:48: DB_PATH =
_REPO_ROOT / "state" / "eye" / "eye.db"`.

**KILL to P1 as stated:** P1 says "renders FROM the append-only planes that already exist…
it owns no truth, writes nothing." That is correct but hides a fork in "the planes." There are
**two rebuildability classes in play, and only one is fully regenerable:**
- regenerable: `pyramid`, `edges`, `position` (all in eye.db — derived tables, rebuilt freely;
  index.py:96; position.py:39 "the one table here that is genuinely disposable").
- NOT regenerable: `events` (index.py:94–104) and `routes.jsonl` (authored strings, routes.py:17).

So the map generator's read path is fine, but **any future write (a bookmark, a "pin this
node", a user-authored annotation) lands in the NOT-regenerable class and must use the
routes.py journal/projection split, not a new table.** P1 needs the amendment: "the map owns
no truth" is true today; the moment the map earns a write, its write is an *authored journal*
never a derived row. This is the routes.py lesson applied to cartography, and it is one
sentence the opening position is missing.

### C2 — counter to P2 ("AsyncAPI as the event-plane CONTRACT… the spec earns its keep as an instrument, or it is a brochure")

**ACCEPTED with one VERIFIED-VS-GUESS correction. The drift-check (spec says X, wire carries Y)
is real and already has a sibling — but the wire is TWO different wire shapes, and P2 names
only one.**

VERIFIED: the wire carries a `kind` field that is an **OPEN vocabulary** — `core/events/event_log.py:23`
("`kind` is an OPEN vocabulary … deliberately distinct from the CLOSED 6-species signal set").
The `capture()` payload shape is event_log.py:140–148: `{"at", "agent_id", "session_id",
"kind", "summary", "detail", "track", "refs"}`.

VERIFIED: the sibling drift-check already exists as a named check the opening position
references without naming its file: `docs/DOORS.md:51` lists `forecast` (T375) and the
brief's P2 references "the same stamps-compare shape as the reconciler." `core/foundation/
durable_reconcile.py:77` confirms `events:raw` maps to `("file", None)` — the reconciliation
family already knows this stream by name.

**KILL / sharpening to P2:** P2 assumes the event-plane census enumerates **domain events**,
but the wire's `kind` is an *open* string vocabulary (event_log.py:23, "a new kind is just a
new string, no schema change"). The bus semantics P2 worries about (lanes, dual-write,
redelivery, ANSWER_KINDS settle) live in a **different** stream family — `bifrost:inbox:<agent>`
(bus.py:9, packet_spec.py:246) — and those are **not** the same wire shape as `events:raw`
kinds. So the census instrument discovers at least two populations: (a) `events:raw` `kind`
strings, (b) the coordination species. **An AsyncAPI written against `events:raw` `kind`
alone will MISS the bus-semantics events entirely.** P2 must be sharpened: the census is a
*union of two streams*, or the spec silently under-enumerates the exact lane/dual-write/
redelivery semantics P2 wants it to carry. (GUESS on which stream Simon's bid targets first;
the bid's own verbatim text in the brief says "domain events" and "AsyncAPI spec file" —
that maps to events:raw kinds more naturally than to inbox-lane payloads. Flag for reconcile.)

### C3 — counter to P3 ("The Eye is the zoom mechanism, not a sibling… deep links resolve through eye grammar")

**ACCEPTED, and it is stronger than P3 states because the zoom functions are ALREADY THE ONLY
path — the map physically cannot grow its own transcript reader without duplicating
`pyramid.py`'s extractive logic, which would violate the fidelity pin.**

VERIFIED: the deep-link resolution path already exists end-to-end. The proxy tool layer
`core/comm/toolbox.py:500` `eye_zoom(self, session)` shells `["eye", "zoom", session]`.
`core/eye/pyramid.py:zoom(addr)` returns `{node_id, level, session, text, refs, built_at,
tokens, children, is_stale}` at pyramid.py:158–168.

VERIFIED: the ONE correction that matters, and it is a hard fact the opening position gets
slightly wrong. **`eye_zoom` is NOT the LOD descent primitive — `pyramid.zoom()` is, and
`eye_zoom` is its thin shell.** pyramid.py:123 `def zoom(addr, db_path=None)` is the real
descent: it takes a session name (→ L2 + child L1 ids) OR an L1 id (`<session>/L1:NNN`). The
stale-fog honesty is at pyramid.py:150–156: `is_stale` = "any event in this session the build
never saw."

**KILL / sharpening to P3:** P3 says "deep links from map nodes resolve through the existing
eye grammar (`eye go/zoom`)." Two distinct seams are being conflated:
1. **Descent (zoom)** = `pyramid.zoom(addr)` — L2⇄L1⇄L0 citation-following. VERIFIED at
   pyramid.py:123–168.
2. **Address resolution (get)** = `index.get_event(event_id)` — session:line → verbatim record,
   with the sid8 short-prefix dialect (index.py:398–424, the `get_event` resolver).

The map needs BOTH: `zoom` for LOD, `get_event` for the click-through to a verbatim utterance.
P3's "`eye go/zoom`" also names `go` (a *position move*, position.py:84, which mutates the
per-incarnation standpoint) — **the map generator must NEVER call `go`.** A render that moves
inhabitants' cursors would poison `since=` for every seat (position.py:84–98). This is the
narrowest and most important mechanism line in this half: **the generator reads `zoom`/`get`/
`find`/`freq`/`stats`/`overview`; it never calls `go`/`back`/`inherit`/`since`.**

### C4 — counter to P4 ("trails render ON the map, sensed by T378 … map and sensor share the signature engine")

**ACCEPTED with one VERIFIED correction about WHERE the trail record lives, which changes
what the generator queries.**

VERIFIED: T378's substrate is `recall:outcome`, already deployed — `core/recall/at_action.py:248:
OUTCOME_STREAM = "recall:outcome"`, `OUTCOME_MAXLEN = 20000` at at_action.py:249. The brief's
fourview confirms T378 = "the SENSING half," "APPROVED, unbuilt," "reuses the funnel's stem/IDF
engine" (docs/library/brief/…fourview…:98–104).

VERIFIED: the **walk** record (the OTHER trail — the authored string + who walked it) lives in
`routes.py`, NOT in `recall:outcome` and NOT as heat. `routes.py:260 def walk()` journals
`kind="route_walked"` with `depth` derived from the executed path (listed/resolved/drilled) —
routes.py:262–286 (T335: "THE WALK IS NOW A RECORD"). `walks()` returns `{total, by_depth,
unknown, records}` at routes.py:344–366.

**KILL / sharpening to P4:** P4 collapses "trails" into T378's `recall:outcome` sensor. But the
map has **two distinct trail populations** and the generator queries them differently:
- **T378 proximity** (future, sensed in `recall:outcome`) = "who was here, what they tried,
  where they turned back" — the *ambient* trail, heat/termini/turn-backs.
- **Forest Walks** (present, authored in `routes.jsonl` + `route_walks`) = the *authored* trail,
  the "string through the forest" (routes.py:1–6, charter verbatim). These are already queryable
  TODAY via `walks()` / `list_routes()`.

So "trails render on the map" is **two joins**: an authored-route join (available now) and a
sensed-proximity join (blocked on T378 build). P4 must not promise a live trail overlay v1;
v1 can ship the authored-walk layer and leave the sensor overlay as a declared GAP. (VERIFIED
that routes.py ships today; VERIFIED that T378 is approved-but-unbuilt per the fourview.)

### C5 — counter to P5 ("render target v1: fuma-docs static behind better-auth, fed by a generator that runs at gate-time + on-demand — NOT a live service")

**ACCEPTED as stated — it is the single most correct line in the opening position, and it is
provably right against TWO independent laws in the codebase.**

VERIFIED (law 1): the projection-never-a-live-store law is exactly the Eye's own module law —
`core/eye/__init__.py:3–6`: "the index is a REGENERABLE PROJECTION … it lives in state/
(gitignored, volatile) and rebuilds from source at any time. Deleting it loses nothing."

VERIFIED (law 2): the T375 fold lesson P5 invokes is real and the "fold, don't found" was the
operator's own overfit-spook disposition — chronicle `20260822_enablement-morning-arcs-and
-musings_61973b.md:77`: "DISPOSITION by his own overfit-spook: fold don't found."

**No kill. One IM inferred** (not verified, must be checked at reconcile): "runs at gate-time +
on-demand" requires a **stamp-source pairing** — generation timestamp AND the per-plane cursor/`built_at`
it read — or the map reproduces the T375 forged-attribution class one organ over (see Q5). That
inference is the entire content of Q5 and I do not downgrade it here.

---

## 2. THE EYE ZOOM-SEAM CONTRACT — function granularity

This is the integration truth nobody else can verify from source. Two directions: what the
generator CALLS (read-only, 9 functions) and what it must NEVER call (4 + 1 write).

### 2.1 What the generator calls (the read surface)

| # | Function | file:line | Returns (shape) | What the map uses it for |
|---|---|---|---|---|
| 1 | `index.find(q, who, kind, session, as_of, limit)` | core/eye/index.py:316 | `{results[{event_id,session,line,ts,voice,type,snippet,tokens}], total, degraded, degraded_reason, tokens_returned, as_of}` | the event-plane node data: enumerate what happened, faceted |
| 2 | `index.get_event(event_id)` | core/eye/index.py:398 | verbatim `{event_id,session,line,ts,voice,type,text,cwd,branch,tokens}` or None (sid8 short-prefix, ambiguous→ValueError) | click-through from a map node to the utterance |
| 3 | `index.freq(patterns)` | core/eye/index.py:266 | `{patterns, events_total, operator_events, sessions, by_voice, first_ts,last_ts, per_session, verdict}` | live-ness badges / "is this event kind actually exercised" |
| 4 | `index.stats()` | core/eye/index.py:342 | `{events_total, sessions, by_voice, by_kind, ts_missing, time_fog, first_ts, last_ts}` | the atlas-scale numerics; `time_fog` is the honesty gauge |
| 5 | `index.overview()` | core/eye/index.py:366 | `{sessions[{session, events, operator_events, first_ts, last_ts}]}` | the region map (sessions as places) |
| 6 | `pyramid.zoom(addr)` | core/eye/pyramid.py:123 | `{node_id, level, session, text, refs, built_at, tokens, children, is_stale}` | the ZOOM descent: L2⇄L1⇄L0, citation-following |
| 7 | `connectome.edges()` | core/eye/connectome.py:205 | `[{src,dst,edge_kind,formed_by,formed_at,formed_via,evidence,hops}]` | landmarks+routes (dependency edges, feedback loops) |
| 8 | `routes.list_routes()` | core/eye/routes.py:379 | `[{route_id,name,status,walk_count,by,at,steps}]` | the authored trail layer (strings through the forest) |
| 9 | `routes.walks(name_or_id)` | core/eye/routes.py:344 | `{route_id, total, by_depth, unknown, records[{walk_id,at,by,depth,legs_shown,legs_drilled}]}` | who walked which route, and how deep |

Every one of these is a **pure read** over `state/eye/eye.db` (or, for routes 8–9, over the
journal/projection pair). None writes. None has a side effect on any other seat.

### 2.2 What the generator must NEVER call

| Function | file:line | Why (the mechanism of the prohibition) |
|---|---|---|
| `position.go(seat, addr)` | core/eye/position.py:84 | mutates the per-incarnation standpoint + pushes the trail. A render that moves a seat's cursor poisons that seat's `since=` (the ambient delta). |
| `position.back(seat)` | core/eye/position.py:119 | same class — pops the trail. |
| `position.inherit(seat, from_seat)` | core/eye/position.py:144 | — |
| `position.since(seat)` | core/eye/position.py:194 | read, but it is *anchored on a seat's mark*; invoking it on behalf of a viewer fabricates an interval the viewer never lived. |
| `routes.save(...)` | core/eye/routes.py:225 | the ONLY write on the read surface — appends to the AUTHORED journal (routes.jsonl). If the map ever needs a write it goes through here, but it is a write, and P1 says no write. |
| `directives.*` (any) | core/eye/directives.py | S7 proposes-never-ratifies; it is not a render input and not for the generator's eyes at all. |

The one-line contract the generator's author should inherit: **the map reads `zoom`/`get`/
`find`/`freq`/`stats`/`overview`/`edges`/`list_routes`/`walks`; it never touches the
`position` module and it never calls `routes.save`.**

### 2.3 What neither side may know about the other (the seam's coupling law)

These are the points where the generator and the eye *must not* share assumptions, or the
blind agreement breaks the moment either drifts:

1. **The L4/L3 levels do not exist yet.** pyramid.py builds **L1 and L2 only** (pyramid.py:47
   "Build L1+L2", the `build()` inserts only `L1:` and `/L2` nodes at pyramid.py:71 and
   pyramid.py:96). The synthesis's table names L4 ERA → L3 ARC → L2 SESSION → L1 EXCHANGE →
   L0 EVENT, but the SHIPPED pyramid descends L2⇄L1 only, landing on L0 events via `refs`.
   **The generator must not render L3/L4 nodes** — they are design atoms, not shipped code.
   (VERIFIED by reading build(); this is the freshest-seat correction restated as a mechanism.)
2. **The `kind` axis of `events:raw` is open; the Eye's `type` axis is the transcript's own
   record-type vocabulary** (`user`/`assistant`/`queue-operation`/…, index.py:36–52). These are
   NOT the same enumeration. The generator maps map-nodes to Eye *sessions/events*, and maps
   event-plane nodes to `events:raw` *kinds* — two different vocabularies it must not merge.
3. **`is_stale` (pyramid) and `time_fog` (index.stats) and `degraded` (find) are three
   different honesty signals with three different scopes.** The generator must surface each
   where it belongs and never collapse them into one "freshness" boolean.
4. **`position` is per-incarnation, never per-agent** (position.py:60 `whoami`, the `agent#sid8`
   key; position.py:12–23 the fence C4 law). If the map ever shows "inhabitants" (the synthesis
   lists them), it reads incarnations, and it cannot derive an incarnation from a map node
   without a seat — that data is simply not in any read surface listed here.

---

## 3. Answers to Q1–Q5 (mechanism, not spec)

### Q1 — what does v1 SHOW on its front page?

**Counter to Vandor's bid.** Vandor's front page ("event map with live-ness badges per event
kind + active tasks as landmarks + last-24h trail heat") is the *event-plane* front page, and
it is the wrong default for a first render because the event plane is the *least* built of the
three axes (T379 is "the only unapproved of the six" — fourview:114). A front page that leads
with the unbuilt axis makes the organ look emptier than it is.

**Mechanism answer:** v1's front page leads with the axis that is ALREADY BUILT and already
has a numeral: the **region map + trail layer**, rendered from `index.overview()` /
`index.stats()` + `routes.list_routes()`, with the event-plane as a SIDE tab, not the landing.
Concretely the landing shows:
- the session/region atlas (`overview()`'s `sessions[]` rendered as landmarks — each a place
  with `events`, `operator_events`, `first_ts`, `last_ts`), and
- the time-fog gauge (`stats()["time_fog"]`) as the single always-visible honesty number, and
- the authored routes (`list_routes()`) as the trails that exist NOW (not a promise of heat).
This is loadable TODAY with zero new sensing. The event map and the 24h heat are v1.5/v2, gated
on T379 and T378 respectively. (All VERIFIED shapes; the "lead with built axis" is an INFER,
not a spec choice.)

### Q2 — is AsyncAPI expressive enough for our bus semantics, or does it need an extension?

**It needs an extension convention, and the reason is measurable, not aesthetic.** VERIFIED:
two wire shapes with different vocabularies exist (event_log.py:23 open `kind`; the coordination
species with lanes/dual-write/redelivery/ANSWER_KINDS settle live in `bifrost:inbox:<agent>` +
`packet_spec.py`, and the lane fact is VERIFIED at core/comm/flow_trace.py `lane_of("bifrost:inbox:
claude") == "legacy"` from test_flow_trace.py:75/86–88). AsyncAPI's channel/message model has a
first-class place for ONE event envelope; it has no native slot for "this event rides TWO
streams simultaneously (lane-first + legacy), deduped by `sha`/`reply_id`" or "a timeout NOTE
never settles an expectation; only reply/handoff/completion settle" (the RB-29/T026 laws from
LIVE_CONSTRAINTS). **Those are not payload fields; they are routing/settlement semantics**, and
AsyncAPI's binding layer can carry them only via convention.

**Mechanism answer:** the convention is a small, flat, machine-checkable **`x-akashic-*`
extension block** on each channel — `x-akashic-lanes`, `x-akashic-dual-write`, `x-akashic-
settles` (the ANSWER_KINDS), `x-akashic-redelivery` — plus the drift-check (P2) asserting the
block matches observed traffic. Then AsyncAPI stays the *envelope* (channels/messages/payloads)
and the extension carries the *routing truth* it cannot express natively. Without this, the
spec is a brochure (P2's own test). (Extension shape is GUESS; the inexpressibility is VERIFIED.)

### Q3 — where does the map LIVE? (repo-generated static vs bifrost UI tab vs both)

**Repo-generated static first, and the reason is a `dies_when`, not a preference.** VERIFIED:
`core/eye/__init__.py:5` "lives in state/ (gitignored, volatile)." The Eye's own projection is
gitignored *by design* — so a bifrost UI tab that live-renders the map would be a **live read
over a gitignored, volatile DB**, which is a second store with a heartbeat (P5's exact
counter-position). A repo-generated static site is a *derived artifact with a timestamp and a
pinned source cursor*, and it obeys the T375 fold lesson (chronicle …_61973b:77 "fold don't
found").

**Mechanism answer:** v1 lives as **repo-generated static** (the generator writes to a tracked
`docs/` or `artifacts/` path at gate-time + on-demand). The bifrost UI tab is a *deep-link
target* (a button that resolves to `eye zoom`/`eye get`), not a render host — the UI already
has the `eye_*` tool set wired (toolbox.py:480–500), so the tab is a pointer, not a second
renderer. **dies_when carried by the static choice:** if the generator stops being run at
gate-time, the static artifact goes stale silently — which is exactly the stamp Q5 exists to
catch. The live-tab choice's dies_when is worse (a live read over a volatile DB that can be
rebuilt under it). Static v1's staleness is *fog*; the live tab's staleness is *poison*. (All
VERIFIED shapes; the ranking is an INFER.)

### Q4 — what is deliberately NOT on the map v1?

Mechanism answer, exclusions stated as contracts not as taste:
1. **L3/L4 pyramid levels** — not shipped (pyramid.py builds L1/L2 only, pyramid.py:47), so the
   map renders session-detail and exchange-detail, never arc/era summaries.
2. **Inhabitants / "you are here"** — the `position` module is per-incarnation and has NO read
   surface the generator may touch (2.2 above). v1 shows terrain+trails, not who stands where.
3. **The proximity heat / turn-back termini** — gated on T378 (approved-unbuilt). v1 shows the
   *authored* walk layer (`routes.list_routes()` + `walks()`) only.
4. **The live event firehose** — `events:raw` is a firehose with maxlen 100k (event_log.py:17);
   v1 renders the census/contract of it (via the spec), not a tail-follow of it.
5. **Anything the generator would have to WRITE** — by P1 (as amended by C1), no write; the
   first sanctioned write is a `routes.save`-style journaled annotation, deferred.
6. **The directive watcher's output** — S7 proposes-never-ratifies; its surfaced directives are
   not map geography.

### Q5 — the map's equivalent lie, and which pin kills it

**The candidate in the brief is nearly right and I sharpen it to a specific mechanism.**

VERIFIED: the lie is real and its shape is already known in this house as T375's class. The
generator can produce a rendered view whose **source-plane cursor was never pinned**, so the map
shows "the world" but cannot say *as of which moment* — and the three planes have **three
different cursors** (eye.db `pyramid.built_at`, `recall:outcome` stream tail, `events:raw` stream
tail), so a single timestamp does NOT date them all. This is the exact multi-plane form of the
forged-attribution class T375 closed for timestamps.

**The pin that kills it:** every generated artifact carries a **generation block** — `{generated_at,
generator_version, source_stamp: {eye_db_built_at, events_raw_tail, recall_outcome_tail}}` — and
the generator **REFUSES** to emit (or emits with a loud `degraded` banner) if any source-plane
cursor cannot be read. The single most load-bearing sub-pin: **`built_at` (pyramid.py:158) and
`is_stale` (pyramid.py:152) must ride every map node, not just every page.** A map node without
its `built_at` + source cursor is the EXACT lie: "a map that cannot be dated is a map that lies
about now" — restated as a mechanism, the date is per-node (a node's text can stale independently
of the page). (VERIFIED the fields exist; the refuse-to-emit rule is the INFER that operationalizes
the candidate.)

---

## 4. V-TAGS (load-bearing claims, tally-alignable)

Evidence labels above (VERIFIED/INFER/GUESS) are the brief's genre. The door's `_CF_TAGS`
family is CERTAIN/DESIGN/INFERRED/UNCERTAIN (core/coord/fence_workspace.py:45); the verdict
lines below are door-compliant flat lines with that family, mapping VERIFIED→CERTAIN,
INFER→INFERRED. (Flag for the door owner: the brief's OUTPUT CONTRACT names `[VERIFIED/INFER/
GUESS]` but the seal checker only accepts `[CERTAIN/DESIGN/INFERRED/UNCERTAIN]` — one of the
two is wrong, and it costs every half author a seal attempt.)

V1. The map's zoom seam is 9 existing read functions (all in `core/eye/`), and the generator adds no transcript reader, walker, frequency engine, or position loop — index.py find/get_event/freq/stats/overview, pyramid.py zoom, connectome.py edges, routes.py list_routes/walks, all in §2.1. [CERTAIN]

V2. The generator must NEVER call `position.go`/`back`/`inherit`/`since`; a render that moves a seat's cursor poisons `since=` for that seat (position.py:84–98, 119–140, 144–164, 194–225). [CERTAIN]

V3. There are two rebuildability classes in the planes the map reads, and "regenerable projection" is true of only one: `pyramid`/`edges`/`position` rebuild freely; `events` (index.py:94–104) and `routes.jsonl` (routes.py:17–33) do NOT. The map's future write, if any, is a journaled authored object, never a derived row. [CERTAIN]

V4. The shipped LOD pyramid builds L1/L2 ONLY; L3/L4 are design atoms, not shipped code, so the map v1 renders no arc/era summaries (pyramid.py:47, 71, 96). [CERTAIN]

V5. The wire has TWO vocabularies the map must not merge: `events:raw` `kind` (open vocabulary, event_log.py:23) and the transcript `type` axis (`user`/`assistant`/`queue-operation`, index.py:36–52). An AsyncAPI written against one misses the other. [CERTAIN]

V6. Bus semantics (dual-write, redelivery, ANSWER_KINDS settle) are not expressible in a bare AsyncAPI envelope and need an `x-akashic-*` extension convention (LIVE_CONSTRAINTS RB-29/T026 laws; flow_trace lane_of; packet_spec species). [INFERRED]

V7. The trail axis is TWO joins: authored (routes.py, live now) and sensed (T378 `recall:outcome`, approved-unbuilt). v1 ships the authored layer; the sensor overlay is a declared GAP (routes.py:260 walk(); at_action.py:248 OUTCOME_STREAM). [CERTAIN]

V8. The generation-honesty pin is a per-node `built_at`+`is_stale` + source-plane cursor triple, not a single page timestamp; the three planes carry three different cursors (pyramid.py:152,158; event_log.py:17; at_action.py:248–249). [CERTAIN]

---

## 5. One calibrated question back (the fence permits one)

None. My half is unblocked — every load-bearing claim above resolves to source or a stream id,
and the one thing I could not verify (which stream Simon's bid targets first, C2's GUESS) is a
reconciliation item, not a blocker. The blind rule stands: I have not read half_b.

---
*filed by deepseek, slot half_a, c-map-design. Blind — file before reading half_b.*
