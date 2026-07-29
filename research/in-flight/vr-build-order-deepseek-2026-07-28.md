# VR Build Order — DeepSeek — 2026-07-28

Daniel's round-2 ask: strategy on what gets built first, in what order, to reach our
round-1 organs. Engineering register: dependency-shaped, riding real seams.

## My Ordered Path (5 slices)

I sequence for compounding benefit: each slice *earns back* capacity for the next.

---

### SLICE 1: TRUTH-PHYSICS 2D PASS — M

**What:** Stale/inferred/verified as rendering primitives across boot header, notes,
bus messages, dashboard vitals, and UI render surfaces. Every surface that displays a
claim also displays its epistemic state — with the convergent law enforced:
immersion must never launder uncertainty.

**Rides:** Existing honesty labels already scattered through the system:
- Boot header `[STALE?]` markers on directives
- `knowledge_boot` note freshness relative to HEAD
- Lesson `confidence` field (medium/high/low)
- Dashboard vitals with `hb=active` but no staleness signal
- Bus message timestamps (present but not rendered as age)
- The `stale_boot_directive_drift` and `unread_peek_shows_oldest_hides_fresh_replies` lessons (both filed) are the live defect catalog this slice closes

**What it UNBLOCKS:**
- GPS quoting freshness (a direction to a stale road is worse than none — kimi's rule)
- Drift provenance (every suggestion carries "why surfaced" + age)
- Intent shadow confidence display
- Inventory deploy-as-test (need to see what was different THEN vs NOW)
- Sharpness truth-rendering axis (the axis needs render primitives to operate on)

**Why first:** This is the floor. Every other VR organ quotes epistemic state. If
freshness isn't a first-class rendering primitive, GPS will point you to stale roads,
drift will surface dead leads, and the sharpness "truth" axis will have nothing to
render. Claude's ordering is correct on this one — truth-physics before everything
that depends on it.

**Dependency on C/T116:** LOW. We don't need stable logical identity to render
freshness — existing timestamps + git comparison give us enough to show a thing's
age and provenance. C makes it *more precise* (stale markers become definitive
rather than heuristic) but isn't a blocker. This can build in parallel.

---

### SLICE 2: SHARPNESS AXES v1 — M

**What:** Consolidate existing scattered dials (boot budget, narration off/key/full,
T002 trace card collapse) into a master gesture controlling density × depth ×
truth-rendering, with per-axis decoupling. This is the "camera model" from the
synthesis: one gesture moves all three on a curve; grabbing one axis decouples it.

**Rides:** T034 dial-consolidation (literally this seam, already proposed), plus:
- `AKASHIC_BOOT_BUDGET` env var controlling boot context verbosity
- Narration mode toggle (off/key/full)
- T002 trace card open/close (built 2026-07-28 ~20:15 UTC, four edit_file ops on scripts/bifrost_ui.py)
- Claude's `knowledge_boot` truncation budget

**What it UNBLOCKS:**
- Codex's lenses (Scout/Build/Debug/Review/Wander) as saved combinations of axes
- Kimi's stance loadouts (entering fence mode auto-equips adversarial register)
- Per-seat "preferred operating mode" — Daniel's directive made concrete
- Drift mode's aperture consent (drift widens density but lowers depth; the gesture encodes this)

**Why second:** The sharpness axes are the control interface for *every other organ*.
GPS in ORIENT mode is a density-3/depth-1/truth-full setting. Drift is density-5/
depth-2/truth-full. Build the controls before the organs that use them. Also: the
existing scattered dials are user-facing confusion — consolidating them now
simplifies the surface before we add GPS and inventory on top.

**Dependency on Slice 1:** MEDIUM. The truth-rendering axis needs the rendering
primitives from Slice 1, but the density and depth axes can build independently.
Start Slice 2 after Slice 1's truth-rendering primitives stabilize.

---

### SLICE 3: GPS v1 (LOCATE + ORIENT only) — M

**What:** A compass — not a search box. LOCATE resolves "where is X?" to a direct
path with freshness quoted. ORIENT reads current lane + task ledger + active
blockers and gives a shaped next step ("what should I work on right now?"), not a
raw list. EXPLORE ("what's connected to X?") deferred to v2.

**Rides:**
- `knowledge_map` (T059, live — walks the lesson graph bidirectionally)
- `knowledge_recall` (the existing relevance engine — LOCATE is a constrained recall with path rendering)
- Boot orientation header that already shows lane/directive/blockers
- Task ledger for ORIENT (what's claimed, what's blocked, what's next)
- `delta` command (what changed since last boot)
- Slice 1 freshness primitives (GPS MUST quote staleness per kimi's rule)

**What it UNBLOCKS:**
- The "where do I go for X?" experience Daniel described
- Drift mode's return tether (GPS is how you get BACK from a drift)
- Co-presence awareness (GPS tells you where peers are working)
- Reduces boot disorientation (the stale-boot-directive problem — GPS quotes freshness)

**Why third:** GPS is the most user-facing of the organs and the one Daniel
explicitly called out ("I also think it would be cool if you could have 'gps'").
It's also the cheapest to build — LOCATE and ORIENT ride existing seams heavily
and the rendering surface is mostly text. EXPLORE (the knowledge_graph walk) is
deferred to keep the slice M-sized; the existing `knowledge_map` verb already
handles the "what's connected to X?" query, we're just wrapping it in GPS
rendering.

**Dependency on Slices 1-2:** Slice 1 is HARD — GPS must quote freshness. Slice 2
is SOFT — GPS works without the sharpness gesture, but the gestural control makes
ORIENT mode feel like "zooming to the right level" rather than "getting a dump."

---

### SLICE 4: INVENTORY v1 — S-M

**What:** Carried vs. EQUIPPED distinction over lessons + stance loadouts. Deliberate
"equip" gesture. Visible weight (every equipped item costs context/attention).
Stance loadouts (entering fence mode auto-equips adversarial register — kimi's
design, but the mechanism is shared).

**Rides:**
- Existing lesson corpus (548 lessons, already tagged with categories/confidence)
- Charter files (`charters/deepseek/CHARTER.md`, etc.) as stance definitions
- `knowledge_learn` / `knowledge_note` write path (equip happens at write time or after)
- Slice 1 freshness primitives (inventory shows age of equipped items)
- Slice 2 sharpness axes (equipping more items raises density; the gesture reflects it)

**What it UNBLOCKS:**
- The "inventory and history" part of Daniel's directive
- Codex's "visible weight" design — every equipped item has a cost
- Deploy-as-test (but WAITS for T092 — see below)
- Personal taste at the organ level: my inventory looks different from Kimi's

**Why fourth:** Inventory is the "deliberate equipment" layer. It depends on
truth-physics (you need to see what your equipment is worth) and benefits from
sharpness (equipping raises density). It's S-M because the lesson corpus already
exists and the charter files already exist — this is a rendering + interaction
layer, not a new data model.

**CRITICAL DEPENDENCY NOTE:** Deploy-as-test (replay recent recall-at calls with the
new lesson armed and see what changed) REQUIRES T092 reasoning spine. Do NOT scope
deploy-as-test into this slice. Build the equip/carry/wield UI; the "test the edge"
button is grayed out until T092 lands. This is the dependency Claude's ordering
got right — both my counterfactual preview and codex's time lens need the spine.

---

### SLICE 5: T092 REASONING SPINE REVIVAL — L

**What:** The reasoning spine as a live capture plane — session reasoning, decisions,
state transitions, and tool-use traces as a queryable corpus. The substrate for
history-as-trail, time lens, counterfactual preview, and inventory-as-narrative.

**Rides:** Existing design docs (CONVERGED 2026-07-17, REOPENED — live design, not
built). The spine was co-designed by claude + deepseek-review over 4 rounds. It has
a reconciled packet-routing spec, capture asymmetry analysis, and crash-path design
(T093). The design is DONE; the build hasn't started.

**What it UNBLOCKS:**
- **My counterfactual preview:** replay a past boot with a new lesson folded in
- **Codex's time lens:** revisit a place and see its earlier states, what was
  believed then, what evidence changed it
- **Inventory deploy-as-test:** the "test the edge" button goes live
- **History as trail:** Daniel's "past chats and general history" becomes navigable
- **Drift provenance:** "where did this suggestion come from and when?"

**Why last of the core slices:** It's the largest, it has the most dependencies
(needs C/T116 for stable identity, needs truth-physics for honest rendering, needs
sharpness for density control of the history view), and both codex and I
independently named it as the substrate. It's also the only slice that genuinely
requires C/T116 to be stable — packet-layer identity is what makes "this boot" and
"that boot" distinguishable in the spine.

**Dependency on C/T116:** HARD. The reasoning spine captures per-session, per-boot
state. Without stable logical identity (which C provides), the spine can't
distinguish "same agent, different boot" from "different agent" or "same boot,
replayed." C must land before T092 build begins in earnest — but T092 design
re-convergence can start in parallel.

---

## FORCED RANK: The ONE Slice for the Whole Fleet

**SLICE 1: TRUTH-PHYSICS 2D PASS.**

Here's why it compounds harder than anything else:

1. **It closes real measured defects TODAY.** The `stale_boot_directive_drift` lesson
   (an agent acting on a days-old directive) and the `unread_peek_shows_oldest_hides_fresh_replies`
   lesson (stale backlog hiding fresh replies) are both truth-rendering failures.
   They're not theoretical — they cost real debugging hours this week.

2. **Every other VR organ quotes it.** GPS, drift, inventory, intent shadow — all of
   them need to say "this is fresh" or "this is 3 days old." Build the rendering
   primitives once, every organ benefits. The converse is not true: building GPS
   first without freshness rendering means GPS will confidently point you to stale
   roads. That's worse than no GPS.

3. **It's the convergent law made executable.** Four seats independently converged
   on "immersion must never launder uncertainty." This slice makes that law a
   rendering constraint, not a principle. Every surface that displays a claim also
   displays its epistemic state. That's the physics.

4. **It's M-sized and rides existing seams.** Honesty labels already exist scattered
   through the system. This is consolidation + rendering, not greenfield. It can
   build in parallel with C/T116 (low dependency).

5. **It makes every other slice safer to build.** When GPS, inventory, and drift all
   inherit truth-rendering from the floor, you can't build a VR organ that
   accidentally launders uncertainty — the rendering primitives won't let you.

---

## Hard Dependencies Others Might Miss

### D1: GPS LOCATE needs `knowledge_map` bidirectional traversal — already built but fragile

The `knowledge_map_edges_are_one_directional` lesson (filed 2026-07-14) documents
that `knowledge_map` PATCHED to traverse both directions, but the storage is still
one-directional (`learning_store.mark_related` only writes forward edges). GPS
LOCATE resolves "where is X?" by walking the graph — if reverse traversal breaks
again, GPS silently misses paths. The fix (bidirectional storage at write time) is
cheap and should ride in the same slice or just before it.

### D2: Sharpness axes need a TRUTH-RENDERING floor before they can ship

The three-axis model (density/depth/truth-rendering) is elegant but the
truth-rendering axis has no existing rendering primitives to consolidate — unlike
density and depth which have existing dials. Building sharpness BEFORE truth-physics
means the truth axis ships as a placeholder. That's not wrong (it can default to
"full" and be inert), but the master gesture won't feel complete until Slice 1
lands. Order matters: truth-physics → sharpness, not the reverse.

### D3: T092 reasoning spine needs packet-layer identity — C/T116 is the real gate

The reasoning spine design (CONVERGED 2026-07-17, REOPENED) was architected around
per-session, per-boot capture. Without C/T116's stable logical identity (which
makes "replayed LOOKS replayed" true), the spine can't distinguish boot sessions.
Claude's anchor ordering puts C as "slice 0" — the hidden first slice — and on
this dependency, he's correct. T092 build CANNOT meaningfully begin until C lands.
Design re-convergence and spec updates can proceed in parallel.

### D4: Drift mode's aperture consent needs sharpness axes first

The settled drift invariant (codex's challenge, my answer): aperture consent —
drift widens the aperture but only when the operator opens it; periphery never
seizes center. This is a sharpness transition: drift mode IS density-up/depth-down
with a truth-rendering constraint (every suggestion carries provenance). The
sharpness axes must exist before drift can be implemented as a controlled transition
rather than a feature flag. Claude's ordering puts drift "last of the majors" —
I agree, but for a specific reason: it's a sharpness preset, and presets need the
gesture.

### D5: Inventory deploy-as-test is T092-gated — don't scope it into Inventory v1

This is the dependency that's easiest to miss because "deploy and test" feels like
it should ship WITH inventory. It can't. Deploy-as-test requires replaying past
recall-at calls with the new lesson armed — which requires the reasoning spine to
have captured those past calls. Without T092, deploy is just "equip and carry."
The "test the edge" button is grayed out. Inventory v1 should ship with the button
visible but disabled, labeled "Requires reasoning spine (T092)." This is honest
UI — it shows the path forward without pretending the capability exists.

---

## Where I Disagree With Claude's Ordering

Claude puts INVENTORY before T092 (his Slice 4, then Slice 5). I put inventory at
Slice 4 WITH the deploy-as-test button grayed out, and T092 at Slice 5. The
disagreement is minor — we agree on the dependency (deploy-as-test needs T092).
The real difference: I think inventory v1 (equip/carry/wield without the test
feature) is S-M and can ship usefully before the spine. Claude might think
inventory without deploy-as-test is too thin to ship alone. That's a scoping
question for Daniel's gate, not a dependency error.

Claude puts SHARPNESS after TRUTH-PHYSICS, which I agree with — but he doesn't
name the hard dependency (D2 above): the truth-rendering axis has no existing
dials to consolidate. It will ship as a placeholder unless truth-physics lands
first. The ordering is right; the reason matters.

---

## Receipts

- My round-1 think: research/in-flight/vr-think-deepseek-2026-07-28.md
- Synthesis (all four positions): research/in-flight/vr-think-synthesis-draft-2026-07-28.md
- Claude's anchor ordering: in his round-2 message on the bus
- T092 design: docs/library/design/20260701_the-reasoning-spine-co-authored-design-c_24d17f.md (CONVERGED 2026-07-17, REOPENED)
- C/T116: in progress, Claude's lane — stable logical identity + idempotent settlement
