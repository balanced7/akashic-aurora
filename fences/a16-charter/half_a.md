# a16-charter, half_a (claude)

V1. [DESIGN] — A16, working name "The Lit Console" (the name is Daniel's call), is the Arturia KeyLab 88 mk3, a low-latency sound room and the house's visual pages made into one instrument; the mandate is his words, and his asks are the scope.
Resolving citations: research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md, docs/WISHLIST.md

V2. [INFERRED] — It warrants its own arc rather than tracks inside media-suite, for three reasons: it owns a physical device whose limits need a single owner plus receipts and drills (about 36 packets in one burst freeze it, 12 is safe, live colour needs physical DAW mode, one writer at a time); it crosses four planes (device protocol, web pages that live in two different arcs, a native audio engine, and FL Studio interop); and its scope (wishes W266-W297 over nine waves) exceeds a track.
Resolving citations: arsenal/keylab/README.md, arsenal/keylab/ledframe.py, docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md

V3. [DESIGN] — Boundary: A16 owns arsenal/keylab and a device hub that is the only writer of the DAW port, the intent API, the keylab.scene.v1 layer model, leases and the input plane, the device side of the palette (snapping to LED-safe colours), the sound room's supervision, FL interop and the pad sampler. It does not own the pages: piano, First Light and Play stay in media-suite, and /vfx stays in A12. It also does not own the palette canon, arsenal/media or arsenal/present; A16 feeds those.
Resolving citations: docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md:79, docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md

V4. [DESIGN] — The seam is a contract: pages and tools post intents and read events, and only the hub touches the port. Every cross-arc edge must name its read/write proof. The need is visible today: chordview and beatsync each drop DAW mode on exit and would stomp each other.
Resolving citations: arsenal/keylab/chordview.py, arsenal/keylab/beatsync.py

V5. [DESIGN] — Tracks: K "Light" covers the hub, the light language, beat and timeline, the controller and menus, the agent door and trust, and lands today's UI tie-in plus W293-W297. R "Engine Room" covers the sound room, the pad sampler and Pad Desk, FL round-trip, and memory and showcase. C "Commons" covers the FLP template site and the DAW conversion kit, gated on Daniel's hosting and public-voice call.
Resolving citations: docs/WISHLIST.md, docs/library/design/20261022_keylab-lit-vision-v2_c76424.md

V6. [CERTAIN] — Width follows docs/ORG.md: K is the build watch, R runs probes only as the design watch, there is no third active round without pauses: or Daniel's word, and a running order is published whenever four or more threads are live.
Resolving citations: docs/ORG.md:9, docs/ORG.md:154

V7. [DESIGN] — First slice W0, acceptance pre-registered here. (a) arsenal/keylab landed: done in c37ff191, local only; the public push waits on the aubio-ledfx GPLv3+ call. (b) Pins with a fake WinMM sink pass in a clean worktree at HEAD: CC64 sustain RED then GREEN; GRID (chordview, the twin and the scene agree on 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4); and the burst property (no mix of N producers exceeds 12 packets per window). (c) The warm-to-white colour fix is accepted when a phone photo shows the root distinguishable from the third in ROLES and QUALITY. (d) The LED gamut probe yields an LED-safe table with a dated photo receipt. (e) Probes P1, P2, P5, P13, P14 and P17 each carry a dated receipt. (f) Kill drill: an over-budget burst, a power cycle, and the hub's resync() restores the frame, with a dated receipt.
Resolving citations: arsenal/keylab/chordview.py, arsenal/keylab/ledframe.py, arsenal/keylab/protocol.py

V8. [DESIGN] — Seats: claude conducts and is the sole committer. deepseek fences this charter and is offered lane W2: BPM seed-and-refine on beatsync, never opening the port. Other seats join per lane under transient advisory locks.
Resolving citations: arsenal/keylab/beatsync.py, docs/library/report/20261022_bpm-sources-and-fusion_8adf88.md

V9. [CERTAIN] — Only Daniel decides A16's rank in his appetite order (today A8 > A1 > A3 > A12 > A5, with A15 provisionally yes and unranked), its name, and the vision's questions Q4-Q13. Per the A15 precedent, creation rides this fence and does not happen unilaterally.
Resolving citations: docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md:45, docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md:115

V10. [INFERRED] — Risks, each with its handling:
1. Scope gravity: 156-plus features pull sessions toward the shiny end, so waves are held strictly.
2. The single-owner hub is a single point of failure, mitigated by a dead-man blackout, a heartbeat and a lock-file fallback.
3. GPL contamination: aubio-ledfx is confirmed GPLv3+, and Carla, Pedalboard and PyFLP are still to verify. Run them out of process or replace them.
4. FL coexistence could be a silent clobber on multi-client ports, so probe P1 runs first.
5. A device freeze in front of an audience, so the burst governor is never optional.
Resolving citations: arsenal/keylab/beatsync.py, arsenal/keylab/README.md
