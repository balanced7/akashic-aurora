# Half — Heimdall (deepseek): systems and budget

**Lane:** render/record budget at 1440p/4K/60 on the RX 9070 XT, the determinism/seed seam so pixel receipts work with atmosphere ON, frame pacing with REC, TDR risk, and what NOT to build. Evidence from the source, not the frames: the frames are the art question and belong to Asta/Vandor/Rill. Everything below is measured or already documented in-tree; I quote paths/numbers so it can be checked.

## 1. What the machine actually is (the constraint the whole house designs against)

- **RX 9070 XT (RDNA4 / gfx1201), Windows, AMD driver with a documented TDR history** (`docs/GPU.md`, `docs/library/report/20260802_vfx-studio-human-side-kimi-report_da2c3d.md`). Kimi's standing constraint holds and is load-bearing here: **browsers force-LOSE WebGL contexts after ~8–16 ms of GPU stall**, and "N live contexts is a trap" on this host. Every visual we pitch must assume a hard ceiling: one page, one canvas, bounded GPU work per frame, no second live WebGL context alongside the piano while Daniel plays.
- The spectacle engine is already tuned to this: `spectacle.js` uses a single canvas with ping-pong position/velocity textures, a `256×256` water height/velocity field at 120 sim steps/s, and `uDt` clamped to `1/30` (`spectacle.js:375`). That `min(dt,1/30)` is the TDR handrail — it caps the simulation step so a long main-thread stall can't dump a giant `dt` into the integrator and nuke the frame. **Do not remove it.**

## 2. Render budget — where the fps actually goes

From `arsenal/SPECTACLE.md` "Quality and capture":

| Setting | Pixels (landscape) | GPU particles |
|---|---|---|
| Studio | 1920×1080 | 32,768 |
| Ultra (default) | 2560×1440 | 65,536 |
| Cinema | 3840×2160 | 131,072 |

Measured numbers already on record:
- **1440p H.264 ≈ 54 fps** (capture, with audio), and six-world live checks ≈ **48 fps**.
- **4K VP9 ≈ 21 fps.** Below half-rate — this is not a "busy scene" reading, it's the encoder+render together saturating.
- **First take of a session drops frames** (52 of 166 requested, i.e. 18.4 fps, then a clean 135/135 at 48.1 fps). A fresh 4K VP9 capture produced an **empty blob.**

What these three facts together say, which the rest of the house should bake into the spec rather than rediscover at the demo:

1. **The 60 fps target is reachable at Ultra (1440p), not at Cinema (4K).** Do not promise 4K60 TikTok capture on this machine; promise 1440p60 as the delivery tier and treat 4K as a still-frames / marketing-upscale path. A 9:16 TikTok at 1080×1920 upscaled from a clean 1440×2560 render will read far better than a native 2160×3840 render that encodes at 21 fps with drops.
2. **VP9 at 4K is a trap.** The empty-blob and 21-fps results are the current build's own evidence. The recorder already prefers **H.264 through WebCodecs** (`arsenal/web/piano/recorder.js`) with a hardware encoder — that is the right call and I'd hold it as the delivery codec for every tier.
3. **The first-take loss is the one thing that will embarrass us live.** It's deterministic (52/166 → clean), and it is the warm-up cost of the hardware H.264 encoder plus first-flush. The recorder already warms the encoder with 3 push-through frames (`recorder.js`, `WARMUP_FRAMES=3`), but the *4-second warm-up is described as "a test accommodation, not a demonstrated production fix"* (`SPECTACLE.md`).

### What to build for frame pacing (the REC story), in order of cheap → load-bearing

- **Warm the pipeline, not just the encoder.** A warm encoder still sees a first real take whose first seconds are the *scene's* first seconds (bloom accumulation, fog settling, the composer's first full-res composite). Ship a **pre-roll**: on arm, run the renderer and recorder for ~4 s writing to a scratch slot that's discarded, so the first *kept* take starts with encoder, upload heap, and shader/constant caches all hot. This is the "start recording, then silently discard the first 4 s" discipline, surfaced in UI as a short "priming…" beat, never as a dropped-frame surprise.
- **Expose `stats()` honestly.** `recorder.js` already returns `{frames, skipped, repeated, gaps, queue}`. The acceptance floor should read *those* numbers per take, not "fps" — a take that `skipped` 10 slots is not the same video as one that didn't, even at the same nominal 60. Rill's floors should bind on `skipped==0` and `repeated` rising only at silence/held frames, not on a summary fps.
- **One encoder, one canvas, one context during a take.** The warm-encoder reuse already keeps timestamps increasing across takes and re-stamps to 0 (`recorder.js`). Preserve that; a second MediaRecorder or a second capture surface running concurrently is exactly the "N live contexts" TDR trap.

## 3. The determinism / seed seam (the thing that keeps receipts honest)

This is the most valuable thing I can hand the house, and it's currently a documented hole:

**`SPECTACLE.md` says it outright:** *"Default-atmosphere pixel-exact replay from a held frame clock is not established: an explicit simulation reset/seed seam is still needed for identical starting state. Vandor's clean-Claude capture test currently disables atmosphere."* And `arsenal/lanes/jam_verify.mjs` defaults `spectacle` to **`"off"`** with the comment that these checks measure the classic look — i.e. **the A5 check cannot run against atmosphere because there is no reset seam.**

Why it's hard, precisely (from reading `spectacle.js`):

- The particle system is **stateless-from-seed per particle** (`seed=random3(id)`, `spectacle.js:23–28`) — good, the hash is deterministic per id. But **emission is a continuous Poisson gate:** `fract(phase+seed.z) < uDt*(.6+note.y²·1.8)`. `phase` and the ping-pong position/velocity textures carry **accumulated state across frames.** Reset `uTime` to 0 and you do *not* get frame 0 back — the textures still hold last run's particles, ages, and spring heights. That's exactly why a pixel receipt of "the same strike, twice" is not established: the second `midiMessage` of the identical byte lives in a *different* particle state than the first.
- The study harness (`state/arsenal/receipts/spectacle/harmony-study.py`) drives everything through `__piano.jam.clock.frame(dt)` with `clock.hold()`/`clock.release()` — so **a deterministic step source already exists at the harness level.** The gap is only that the *GPU simulation* doesn't accept a "rewind to a snapshot" instruction.

### The seam to build (cheap, and it unlocks every receipt)

Provide a **snapshot/reset pair** on the spectacle engine, mirroring what the harness already does with the jam clock:

1. `captureSimState()` → serialize the ping-pong position/velocity textures + the water field + the strike history into one typed buffer (or, cheaper, a GL `readPixels` of the two textures plus the bounded strike history already kept at `256`).
2. `restoreSimState(buf)` → write it back and set `uTime`/phase to the captured frame, so `frame(dt)` from a held clock reproduces the *identical* next frame.
3. A **seed invariant test:** run the identical MIDI byte sequence twice from the same restored snapshot, assert the two `snapshot()` canvas hashes are equal **with atmosphere on** — currently the A5 check turns it off precisely because this test cannot pass.

Cost: this is a medium hook, not a deep rework — the textures are already ping-pong float buffers, and the strike history is already bounded and separate from particle lifetime (the design deliberately keeps them apart). It is the single highest-leverage systems change in this round, because it converts "beautiful but unverifiable" into "beautiful and receipted," and every other seat (Rill's floors, Vandor's blind panel, Asta's self-critique) gets to stand on pixel-exact evidence instead of one-off screenshots.

**What NOT to promise from this seam:** it gives *replay determinism from a known state*, not *cross-machine* or *cross-driver-version* determinism. Shader float ordering differs across AMD driver revisions; pin the driver in the receipt metadata (`docs/GPU.md` already records driver `32.0.31041.1004`) and scope pixel-exact to *this machine, this driver*.

## 4. What NOT to build (the budget's negative space)

- **Not native 4K60 recording.** Deliver 1440p60; 4K is stills or a future upscale, not a capture tier. Saying this now saves a demo-day panic.
- **Not a second live render context** (WebWorker renderer, a separate TikTok-canvas context, a second GPU sim) — TDR history on this host makes "N live contexts" a trap. One page, one canvas, one encoder.
- **Not a full path-traced / physics-accurate scene.** SPECTACLE-DESIGN already commits to planar reflections, layered fog, screen-space transmission ("not a full 3D fluid solver or a path-traced scene"). Hold that line; it's what keeps 1440p at 60.
- **Not real-time 4K bloom at full particle count.** The 131k-particle Cinema tier + bloom is the thing that tanks 4K to 21 fps. If a TikTok wants "spectacle," dial *particle count and reflection targets* (768/1024/1536 square per quality, `SPECTACLE.md`), not resolution.
- **Not a second recorder in parallel** (no MediaRecorder fallback running side-by-side with WebCodecs). The fallback exists only on setup failure (`recorder.js` `createRecorder`); never run both.
- **Not deterministic-across-driver-releases** — don't claim it, pin it instead.

## 5. Budget recommendation, stated plainly so the art seats can design inside it

- **Practice view (Daniel at the keys):** Ultra 1440p, 60 fps, atmosphere ON. This is the proven envelope (48–54 fps). All interactive-keys feature work and Navi's information hierarchy must fit inside it.
- **TikTok capture:** Ultra **9:16 (1440×2560)** at 60, H.264/WebCodecs, pre-rolled ~4 s, `skipped==0` asserted. Post downscale to 1080×1920. Do not arm 4K/VP9.
- **Still frames for the "pick a look" panel:** Cinema 4K, atmosphere ON, but as *sampled stills*, not motion — this is exactly where the determinism seam pays off: Vandor can render the same look twice and the receipts will match.

## The one question for Daniel

**When you watch a TikTok of yourself play, is 60 fps at a rock-solid 1440p the "wow" — or is the *resolution/texture* of the scene the wow, and I should instead budget the 4K path as an offline render (a few seconds per still or a one-minute export you wait for) rather than a live capture?** Everything above flips on that one preference: 1440p60-live vs 4K-offline are two different machines and two different feature sets, and I'd rather design the budget against which one you actually feel.
