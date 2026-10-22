# a16-charter, reconciliation (claude)

Inputs: half_a (claude), half_b (deepseek, written blind), the M1-PV report (34 citations verified,
0 MISSING), and Daniel's answers of 2026-10-22, which arrived while the fence was open and are
recorded verbatim in research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md.
Where Daniel ruled, his ruling outranks both halves. Where he has not ruled yet, it says so.

## Evidence hygiene

- M1-PV: 34 verified, 0 MISSING. No section is retired.
- half_b's disclosure: a grep over the wishlist surfaced headline fragments of the draft vision; the
  file itself was not opened, and the fragments were purged from its reasoning. Accepted. The exposure
  was at headline level, half_a was never seen, and the halves diverge in substance (tracks, the first
  slice, palette ownership), which is the evidence that independence held.
- One fact correction. half_b V1 calls arsenal/keylab "uncommitted", and V12 says it is "untracked and
  in no atom, task, or wish". As of this fence that is false: commit c37ff191 tracks the nine files of
  arsenal/keylab (git ls-files, 2026-10-22), wishes W266-W297 are filed in docs/WISHLIST.md (W266 at
  line 1781), and five report atoms plus two drafts exist. The commit is local only. V12's substance
  survives the correction: A16 files new work and does not re-file another arc's backlog.

## Divergence ledger

| Topic | half_a | half_b | Resolution |
|---|---|---|---|
| Name | working name "The Lit Console", Daniel decides | abstains on purpose | Daniel ruled: **KeyLab Control Center** |
| Tracks | three watches: K Light, R Engine Room, C Commons | six work packages T1-T6, substrate first | both: B's six packages grouped under A's three watches (V5) |
| Palette | A16 owns the device side (LED-safe snapping), the canon lives elsewhere | a shared module both arcs import, owned by neither alone | B's wording adopted; A16 owns only the LED-safe snap table (V3) |
| First slice | pins, the warm-to-white fix, the gamut probe, six probes, a kill drill | land with receipts and a licence call, no feature in slice 1 | merged (V7); the fix and the probe are repairs and measurements, not features |
| Licence timing | out of process or replace; push waits on the call | decide before any aubio file is COMMITTED | re-scoped to "before PUSH", since the commit already happened (V7a) |
| Beat-lane boundary | "never opening the port" (a promise) | checkable by the import graph | B adopted, as a pinned test (V8) |
| Understudy | not named | required (ORG B3) | named at the hub's birth in W1; until then the bus factor of one is stated (V8) |
| Rank | Daniel decides | Daniel decides | Daniel: "fold it in", read as counting toward A12; confirmation pending (V4) |
| Order | K first, implied | Daniel decides light-first vs sound-first | Daniel ruled: **lights first** |
| FL coexistence | probe P1 first | "close FL first" is a manual precondition, not a solution | Daniel ruled: our own script with handoff modes (V10) |

## Verdicts

V1. [CERTAIN] — A16 is its own arc, named "KeyLab Control Center" by Daniel. Both halves argue for an arc rather than tracks (half_a V2; half_b V1 and V3), and both give the same reason: the thing under verification is physical hardware with a port and a freeze cliff, not a page.
Resolving citations: fences/a16-charter/half_a.md, fences/a16-charter/half_b.md, research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md

V2. [DESIGN] — Mandate (half_b V2's sentence, half_a V1's scope): make the KeyLab 88 mk3 a house instrument, the hands and second screen of the pages, not a peripheral demo. The scope is his asks. The spine is the landed package, the hub, the light language, the pages' binding and honest receipts. The sound room is inside the arc. The Commons is the gated tail.
Resolving citations: fences/a16-charter/half_b.md, fences/a16-charter/half_a.md, research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md

V3. [DESIGN] — Boundary: the port is the seam, as both halves draw it.

A16 owns:
- the hub, the only writer of the DAW port;
- the intent API, the scene model, leases and the input plane;
- the LED-safe snap table;
- the FL handoff script;
- the sound room's supervision and the pad sampler.

A16 does not own:
- the pages (media-suite);
- /vfx and the Bifrost UI (A12);
- the palette canon, which is a shared module both arcs import.

The VFX Bench splits by output plane (half_b V5): on screen it belongs to media-suite, on the KeyLab strip to A16.
Resolving citations: fences/a16-charter/half_a.md, fences/a16-charter/half_b.md

V4. [UNCERTAIN] — Rank. Daniel answered Q2 with "lets fold it in". I read that as counting A16 toward A12 THE FACE, which is #4 in his appetite order, while A16 keeps its own number and fence. The confirmation was asked on Discord (bus 1792692188872-0). Until he confirms, A16 holds no rank of its own and is not minted.
Resolving citations: research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md, docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md

V5. [DESIGN] — Tracks: half_b's six work packages, grouped under half_a's three watches.
- K "Light" holds:
  - T1, land and licence;
  - T2, the hub and the port;
  - T3, the light language and controls, which now absorbs W293-W297, the FL handoff script and the preset maker;
  - T4, beat and BPM, as a delegated lane.
- R "Engine Room" holds T5, the sound room.
- C "Commons" holds T6. It is gated, and Daniel's answer is pending.

Daniel ruled the order: lights first. That means T1, then T2, then T3, with T4 running alongside, and T5 after.
Resolving citations: fences/a16-charter/half_b.md, fences/a16-charter/half_a.md, research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md

V6. [CERTAIN] — Width follows docs/ORG.md, as both halves state: one build watch (K) and one design watch (R, which runs probes only). Adopted from half_b V7:
- T4 and T5 are never both under construction;
- the charter carries a pauses: field, so a mechanical gauge refuses a third watch, not anyone's memory.
Resolving citations: docs/ORG.md, fences/a16-charter/half_b.md

V7. [DESIGN] — W0, the first slice. Acceptance is merged from both halves and pre-registered here, before anything is built.

(a) The package is landed (c37ff191). The licence ruling is recorded before any PUSH: half_b's "before commit" is re-scoped, because the commit already happened. Today the exposure is small: beatsync imports aubio lazily inside run() (arsenal/keylab/beatsync.py:61), aubio is not vendored, and it is in no requirements file. Daniel's answer is pending on a plain-words explanation.

(b) Pins pass in a clean worktree at HEAD, against a fake WinMM sink:
- CC64 sustain, RED then GREEN;
- the GRID, where chordview, the twin and the scene agree on 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4;
- the burst property: no mix of producers exceeds 12 packets per window.

(c) Every confirmed fact in the README carries a dated receipt line, sourced from the session record of 2026-10-22. This is half_b V8(d) without spending Daniel's eyes a second time.

(d) The warm-to-white colour fix is accepted when a phone photo shows the root distinguishable from the third. The LED gamut probe yields an LED-safe table with a dated photo receipt. Both stay in W0 because Daniel ruled that themes are the palette root, and every theme must snap to that table (half_b R4).

(e) Probes P1, P2, P5, P13, P14 and P17 each carry a dated receipt.

(f) Kill drill: an over-budget burst, then a power cycle, then resync() restores the frame, with a dated receipt.

None of these is a new feature, which honours half_b's "no feature in slice 1".
Resolving citations: arsenal/keylab/beatsync.py:61, arsenal/keylab/chordview.py, arsenal/keylab/ledframe.py, arsenal/keylab/README.md, fences/a16-charter/half_b.md

V8. [DESIGN] — Seats. claude conducts, is the sole committer and holds the port seat. deepseek holds the beat lane (T4). That boundary becomes a pinned test: no module in the beat lane may import winmidi or protocol (half_b V9), and each seat is the other's contrarian by construction. The understudy is named when the hub is born in W1. Until then the bus factor is one, and this line says so.
Resolving citations: fences/a16-charter/half_b.md, docs/ORG.md, arsenal/keylab/beatsync.py

V9. [DESIGN] — The hub is its own service, reachable from the piano server's UI (Daniel, Q6). Other agents reach it through an MCP door (Q10). On latency, his rule is "as fast as we can go" (Q11). Fast still means inside the freeze ceiling: the burst governor is never optional (half_a V10, half_b R1).
Resolving citations: research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md, arsenal/keylab/ledframe.py

V10. [DESIGN] — FL. Daniel ruled for our own script with handoff modes, so that nothing requires tiptoeing around FL (Q5). It is built as house-authored code, not as a modified copy of Arturia's file. Arturia's script is their code; the protocol facts we learned from it are not, so only house-authored code can live in the public repo. That adjustment was flagged to Daniel (bus 1792692188872-0). The modes are:
- FL drives;
- Aurora drives;
- shared, where FL keeps transport and mixer and Aurora gets the pads and screen.

A key combo switches between them. W266 already gates the script behind the JamProbe drill, because FL 26.1.3 lists freezes when scripts call FL functions.
Resolving citations: docs/WISHLIST.md:1781, research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md

V11. [DESIGN] — Themes. Daniel ruled "Both" (Q8): the piano's note colours, the patch-bay look and Aurora Void all become presets, each snapped to the W0(d) gamut table. He also asked for a preset maker: faders pick colours, pads save or step to the next element, and the LCD shows what is being edited.
Resolving citations: research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md

V12. [DESIGN] — Design docs, not wishes (Q14). W293-W297 and the preset maker each become a library design doc with numbered requirements and deliverables before anything is built. They enter T3. The wishes stay as the record of the ask.
Resolving citations: docs/WISHLIST.md, research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md

V13. [INFERRED] — Risks: the union of both halves, plus two found here.
1. The freeze cliff: about 36 packets in one burst freezes the device, and 12 is safe.
2. The GPL dependency, now a push-gate item.
3. FL contention, handled by the handoff script and probe P1.
4. The warm-colour wash, handled by W0(d).
5. Scope gravity.
6. The hub as a single point of failure: a dead-man blackout plus a heartbeat.
7. New: the FL script's copyright, handled by house-authored code only.
8. New: the scope of a public push. A push sends every commit ahead of origin/master, which is 104 commits back to 2026-10-07, not only the KeyLab pair. Daniel was asked about the scope, and nothing is pushed before he answers.
Resolving citations: fences/a16-charter/half_a.md, fences/a16-charter/half_b.md, arsenal/keylab/README.md

V14. [CERTAIN] — What only Daniel decides, and its state on 2026-10-22.

Ruled:
- the name;
- the order;
- the hub's home;
- FL handoff;
- the MCP door;
- latency;
- themes;
- design docs;
- downloads.

Open:
- confirmation of the rank;
- the push scope;
- the licence path, Q9;
- the meaning of the "manual bund method", Q12;
- the Commons, Q13;
- the downloads folder (proposed: E:\Aurora-Tools\).

A16 is minted (atoms labelled, entered in the program) only after the rank is confirmed, per the A15 precedent.
Resolving citations: research/reviewed/keylab-liberation-2026-10-22/daniel-answers-2026-10-22.md, docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md
