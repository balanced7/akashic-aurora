# Studio: reconciled build spec (2026-10-12, Vandor)

Inputs: STUDIO-DESIGN.md (design + skeptic corrections), FENCE-heimdall-2026-10-12*.md (verbatim fence),
..\primitives\PRIMITIVES-SPEC.md (landing), Daniel's asks tonight (verbatim in the fence request).
Daniel asleep, full autonomy tonight; local commits only; never push.

## Decisions

1. **The studio is a projection of the existing arsenal family, not a sibling pipeline.** Before writing any new
   module, the builder files a one-page "does the arsenal already do this" sheet naming, per primitive, REUSE
   (arsenal.storyboard, arsenal.present + present/scene.py + targets, arsenal.mediatypes + arsenal.registry +
   arsenal/modules/*.json, arsenal.jam align/cards/resolve/tempomap, arsenal.take, arsenal.tiktok, arsenal.timebase,
   arsenal.analysis, arsenal.replay, arsenal.stt) or EXTEND (with the reason). No second module/port/receipt idiom.
2. **Master project file = the board** (the storyboard schema with the fact-binding doctrine: raw digits refused,
   every on-screen number carries an evidence class). OTIO = export door only.
3. **v0 = Daniel's explicit ask**, expressed over the module system: media ingest by drag-and-drop, a timeline with
   one video track + several audio tracks, trim handles (lossless keyframe trim + exact re-encode trim), per-track
   gain/mute, a metadata panel (probe + catalog), ffmpeg render, the review view. Timeline state lives in the board
   (or a board-projected timeline document) with ONE writer at a time; the web UI and the studio MCP edit the same file.
4. **UI: no fourth bespoke web page.** Extend the existing Studio surface (arsenal/web/piano/studio/, replay.html)
   or the present family's web target; reuse the house look (first-light.css, workbench style).
5. **Masks/alpha = thin v0 slice:** SAM 2.1 still-frame masks only if cheap; the three measured alpha export presets
   (WebP via Pillow for soft alpha, APNG, WebM-alpha from RGBA readback) as modules. No video tracking in v0.
6. **GPU:** one locking story -- reconcile a resident model worker with arsenal/GPU-LOCK.md + lanes/gpu_lock.mjs;
   no spawn-per-job GPU processes (the ROCm probe hung on exit).
7. **League capture deadline (patch 26.21 on 2026-10-21) is the riskiest assumption.** v0 ships the MANUAL capture
   run-sheet as a first-class artifact (14 takes, plates at every freeze time, 4K HUD-off) plus a Replay API driver
   with a dry-run and a swagger fetch -- to be PROVEN when Daniel opens the replay. `capture_take` automation only
   once the driver is real. OBS changes are Daniel's (exact values in STUDIO-DESIGN Part 3.3).
8. **Not built:** a second registry idiom; Diffusion Studio adoption (one-evening evaluation with Daniel's download
   yes; never shape v0's data model around its JSX); capture automation without a proven driver.

## Tonight's build order
A. Arsenal reuse sheet (REUSE/EXTEND per primitive).
B. Primitives v0 as arsenal modules + functions + CLI verbs + MCP tools, each tested against ground truth we hold.
C. Editor v0 (ingest, timeline, multi-track audio, trim, metadata, render) on the board, in the existing Studio UI.
D. Capture run-sheet + Replay API driver (dry-run) + swagger fetch script, ready for Daniel.
Each step: tests pass (node + pytest for touched areas), LF line endings, locks, recall-at, local commit.
