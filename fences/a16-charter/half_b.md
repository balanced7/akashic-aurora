# A16 charter — half_b (deepseek, blind)

> Written blind. I read: `brief.md`, `daniel-asks-2026-10-22.md`, `docs/WISHLIST.md` W266-W295 (filed 2026-10-22), `arsenal/keylab/README.md`, `docs/ORG.md`, `docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md` (§5 = the A15 precedent), `docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md`, `docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md`, `docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md`.
> I did **not** open `half_a.md`, nor any `vision-*` / `keylab-lit-*` synthesis. One disclosure (evidence-hygiene, not a leak of intent): a grep over WISHLIST for W266-W297 surfaced *gist fragments* of `docs/library/design/20261022_keylab-lit-vision-v2_c76424.md` (its headline names "11 pillars, a hub spine, 9 waves, 13 ratification questions, 23 probes"). I did not open the file, and I have purged those fragments from my reasoning below. My verdicts rest only on the allowed inputs listed above.
> Tags are exactly one of [CERTAIN] [DESIGN] [INFERRED] [UNCERTAIN]. Line numbers are only cited where I read that line.

---

V1. [CERTAIN] The arc exists. The KeyLab work is not a set of tracks inside an existing arc — it is a new instrument with its own substrate (uncommitted `arsenal/keylab/`, a WinMM/ctypes MIDI driver, a live beat engine, a chord namer, a measured LED ceiling) plus a wish-cluster (W266-W295) that no existing arc's mandate reaches. Daniel's words — "Feel free to commit, if it deserves its own arc for proper workflow then lets do another arc" — are a provisional yes delivered through the engineer in the room, and per `brief.md` the A15 precedent resolves any ambiguity about what a "proper workflow" is. This deserves its own arc.
Resolving citations:
- fences/a16-charter/brief.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:28
- arsenal/keylab/README.md
- docs/WISHLIST.md:1781

---

V2. [DESIGN] The arc's mandate is single and load-bearing: make the KeyLab 88 mk3 a house instrument — the hands and second screen of the pages — not a peripheral demo. Concretely: (a) land `arsenal/keylab/` as a committed, pinned, receipted package; (b) a hub that owns the single "KeyLab 88 mk3 DAW" port and renders scene state to pads, LCD and LEDs on one colour language; (c) the pages (piano, First Light, Play, VFX Bench) drive that display with menus and adaptive colour; (d) the sound-craft room that hosts instruments/effects and round-trips with FL; (e) a measured, receipted account of the device's true limits. I put (a) and (b) and (e) inside the arc because they are the substrate every other pillar draws on, and I put (d) inside the arc because Daniel named it twice with product energy — "we may have a product on our hands" and "low latency audio play space... can you imagine the workflows and collaboration." The mandate is the instrument, the room, and the honest receipts; the content-engineering and collaboration-site asks are the arc's tail, not its spine.
Resolving citations:
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:24
- arsenal/keylab/README.md
- docs/WISHLIST.md:1781

---

V3. [DESIGN] Why an arc and not tracks inside media-suite: media-suite already carries an ergonomics track (H) and a now-playing/presentation/content cluster, but its spine is *surfaces and content*; the KeyLab is *a physical instrument with a port and a hardware-freeze cliff*. Tracks inside media-suite would inherit media-suite's width accounting and its "one Daniel touch per gated step" cadence — both wrong for something whose first N slices are port-ownership, hardware receipts, and a licence call, none of which media-suite touches. An arc also gives the work the one thing a track cannot: its own Gate and its own Play phase that Daniel can judge ("beautifully, flawlessly rendered, 0 flicker") rather than a content-suite milestone. The arc exists because the *object of verification* is physical hardware, not a page.
Resolving citations:
- docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md

---

V4. [DESIGN] Boundary against A12 THE FACE: A12 is the Bifrost UI — the operator watches a fleet round in a browser. The KeyLab arc is a *second screen for the pages*, rendering on a device A12 never addresses. The two share a colour-language concern ("adaptive beautiful coloring") but they are different outputs: A12 renders to a web viewport; this arc renders to a physical LED/LCD device through a port it owns. The clean seam is the hub: this arc's hub (`arsenal serve`) is the thing that owns the port and emits scene state; A12 may *read* that state but never *owns the port*. I draw the line at the port, not at the colour schema — a shared palette module is a dependency both can import, not an authority either owns alone.
Resolving citations:
- docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md

---

V5. [DESIGN] Boundary against media-suite: media-suite owns the pages' *content and presentation* (piano, First Light, Play, now-playing, facts, the VFX Bench as a screen experience). This arc owns the *instrument binding* — which keys/faders/pads reach which page control, and how the pages' state lands on physical pads/LCD. The VFX Bench is the hardest case: it appears in both. I resolve it by output plane — the VFX Bench *on screen* stays media-suite; the VFX Bench *on the KeyLab strip* (faders/encoders/pads mapping to VFX params) is this arc. The arc supplies the "VFX device" binding; media-suite supplies the VFX itself. Neither arc may silently own the other's half.
Resolving citations:
- docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:25

---

V6. [DESIGN] Tracks. I propose six, ordered substrate-first, with the observed hardware facts as the load-bearing spine: (T1) **Land and licence** — commit `arsenal/keylab/` by named paths, resolve the aubio GPLv3 call before any aubio-importing file is committed, pin the measured limits as tests, add the keylab tests dir (the sustain fix is unpinned). (T2) **The hub and the port** — one owner of the "KeyLab 88 mk3 DAW" port, a paced writer, scene state, leases. (T3) **Light language and control** — the colour schema snapped to what the LEDs actually render (saturated blues/purples/magentas/pinks/reds read; warm low-saturation washes to white), the 9-5-1 pad grid truth, menus on the native LCD widget, modes/banks exposed. (T4) **The beat/BPM engine** — seeded and refined BPM, the beat march, the chord DB, track position. (T5) **The sound room** — host instruments/effects, export/import with FL, the FL mixer preset/effect-chain parser, detached or alongside FL. (T6) **Content and the Commons** — the tour episode, session capture, attract mode, and (gated, later) the FLP template/collaboration site and the DAW conversion kit. I deliberately rank T5 *after* T3-T4 because the room's "IMPORT to FL" promise depends on T2's port discipline and T3's palette existing, and the collaboration site (W268) is the arc's public tail, gated hardest.
Resolving citations:
- arsenal/keylab/README.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:18
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:24

---

V7. [CERTAIN] Width under ORG: one build watch, one design watch, *on different planes*, never two builds — and the two-watch cap stands (ratified prose, `org-width-ruling` 369243 re-stamped 2026-09-04). This arc admits exactly one build lane at a time; the beat engine (T4) and the room (T5) must not both be under active construction simultaneously because both touch the port-adjacent process and the tree. The arc's own charter should carry the `pauses:` field naming what waits when a second lane opens, so the mechanical width gauge (not a seat's memory) is what refuses the third watch. I do not invent a third lane; I state the cap as law the arc inherits.
Resolving citations:
- docs/ORG.md

---

V8. [DESIGN] First slice, acceptance pre-registered before any build: the first slice is **land `arsenal/keylab/` with receipts and a licence call** — not a new feature. Acceptance, pre-registered: (a) the aubio-licence question is *answered in the record* (a ruling or a documented hold) before any file importing aubio is committed, because committing a GPLv3 dependency into the Apache tree is irreversible in a way a feature is not; (b) `arsenal/keylab/` is committed by named paths with the measured facts (12-safe / ~36-freeze, the pad grid, the colour wash, the timing) turned from inline comments into pinned tests or a report atom; (c) the sustain fix (CC64) has a RED/GREEN pytest so it cannot regress silently; (d) every fact in README's "Confirmed facts" table bears a dated, eyes-on-from-Daniel receipt line. This slice is the substrate; it is why the arc can later say "flawlessly rendered, 0 flicker" with a receipt in hand. No feature is built in slice 1.
Resolving citations:
- arsenal/keylab/README.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:16

---

V9. [DESIGN] Seats. The port and the LED-sender half is one seat's lane (the engineer who already built and hardware-confirmed `protocol.py`/`winmidi.py`/`ledframe.py`/`beatsync.py`); the beat/BPM/seed lane is a *different* seat's lane, built against the hub's intent API and **provably never opening the port** (it must be import-free of `winmidi`/`protocol`, so the boundary is checkable by import graph, not by promise). Per ORG's B2, the contrarian on any watch is whoever did not build the thing — so the sender-seat and the beat-seat are mutually the other's contrarian by construction, which is exactly the separation the hardware's freeze-cliff demands. Understudy (B3) is named in the charter; a seat that can drive the port is a bus-factor of one until an understudy is named.
Resolving citations:
- docs/ORG.md
- arsenal/keylab/README.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md

---

V10. [DESIGN] Risks, named and ordered. (R1) **The device hard-freezes on ~36 SysEx in a burst; 12 is safe.** Every emitting path must pace under the cliff, and the cliff itself must be re-measured (burst × gap) rather than inherited as a guess — a freeze is a power-cycle for Daniel, not a test failure. (R2) **The aubio GPLv3 licence.** Committing it wrong contaminates the Apache tree; it must be decided before T1 closes. (R3) **Port contention with FL Studio.** FL's Arturia script writes the same pads/screen; "close FL first" is a manual precondition, not a solved coexistence — the arc risks fighting the DAW it's trying to serve. (R4) **Warm-colour wash.** A palette that looks right in the browser photographs white on the device; the palette must pre-snap to colours the LEDs render, or the "adaptive beautiful coloring" promise fails on the actual hardware. (R5) **Scope gravity.** The asks span a physical instrument, a sound room, a collaboration site, and content — the collaboration site (W268) and OBS (W293) could each drag the arc into public-hosting and external-integration territory that needs Daniel's separate yes, and I flag them as gated-tail, not spine.
Resolving citations:
- arsenal/keylab/README.md
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:3
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md:23

---

V11. [INFERRED] What only Daniel decides. (1) The arc's **name and rank** — he ratifies both at the end of the ceremony, as the A15 precedent and the appetite-ranking instrument both record, and I do not propose a name in a blind half whose whole point is that the two halves diverge before reconciliation. (2) Whether the first build is **light-first** — i.e. land the package and the hub and the pages' colour/menus before the sound room — which is a build-order call only his excitement can settle against the spine. (3) Whether to spend his one physical-verdict budget on the **LED-ceiling bench sweep** (burst × gap, with him watching the pads stall/freeze) — the receipts require his eyes on the hardware. (4) The **hard gates** already queued elsewhere and re-opened by this arc: installing Carla/pip/the MIDI Services SDK outside the repo, writing into FL's folders, registering the MCP door, and anything public. (5) The licence call's *outcome* if it is a judgement call rather than a mechanical one. (6) OBS, the collaboration site, and the DAW conversion kit as scoped-in or scoped-out of A16 versus a later arc.
Resolving citations:
- docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md
- docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md
- fences/a16-charter/brief.md

---

V12. [CERTAIN] The arc is new-ceremony, not re-file. `arsenal/keylab/` is untracked and in no atom, task, or wish — the brief and the WISHLIST both record that the ledger had zero KeyLab surface before today. That means A16 is not retrofitting an existing arc's backlog; it is the first filing of a substrate that has been quietly built to the point of "it genuinely works on the hardware, untracked." The proper-workflow answer to "lets do another arc" is: mint it, land the substrate, pin the receipts — and make the *first* Gate the fact that the thing already lights and names chords, now made durable instead of ephemeral.
Resolving citations:
- arsenal/keylab/README.md
- fences/a16-charter/brief.md

---

*(blind half ends — reconciliation is the next ceremony step, untouched by this slot)*
