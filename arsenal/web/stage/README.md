# Virtual Stage v0 ("Source")

A concert hall inside the computer, with a show rig that behaves like real gear, in the spirit of Qlimax 2014 "The
Source Code of Creation". This is the first slice (v0) of the design dated 2026-10-24 (the architect's "The Virtual
Stage: Source"). The design calls its code name `arena`; this lane's brief put the page under `stage/`.

Open it from the Arsenal server:

- `http://127.0.0.1:8793/web/stage/index.html?demo=1` plays the built-in demo show at 150 BPM. The demo runs intro,
  build, drop and break, with its own pad presses and camera flypaths.
- `http://127.0.0.1:8793/web/stage/index.html` listens to the VJ engine on 8794. Its beats drive the clock, and the
  KeyLab's pads and faders play the stage. The engine is only read from: the page never posts to it.

| Control | What it does |
|---|---|
| Pad 1 / key `1` | KICK: the strand's cubes and heads lift on the beat. An early press waits for the line. |
| Pad 2 / key `2` | LASERS: a hit. The tier depends on how soon it follows the last one. Holding it gates the lasers on quarter notes. |
| Pad 6 / key `6` | FLY-OUT: the truss and lip beams burst outward from the centre. |
| Pad 10 / key `0` | DROP NOW: the drop starts on the next downbeat. |
| F1, F4, F5, F6, F9 | Strand master, lasers, haze target (it moves over minutes), speed (detents 1/4 to 4), grand master. The sliders in the HUD do the same. |
| `C` / `Esc` | Hold the next camera shot / give the camera back to the director. |
| `H`, `F` | Hide the HUD, go full screen. |

## Files

| File | Holds |
|---|---|
| `sets/source-v0.json` | The rig as data (`arsenal.arena/v1`): types, objects with repeat generators, groups, effects, formations, looks, lasers, atmosphere, themes, camera shots and sequences, the show. |
| `rig.js` | Validates the scene and expands it deterministically. Also the MVR bridge and the head geometry. |
| `grid.js` | The one beat position for everything, plus the demo clock. |
| `effects.js` | Spreads (MA, ChamSys and Hog in one object), waveforms, and beat-locked phase accumulators. Also the unison floor rule. |
| `programmer.js` | Looks, effects, pads (HTP), masters, theme colours, the colour wheel, and motor physics. |
| `kinetics.js` | The hoists (jerk-limited), the formations, and time-priority landing on bar lines. |
| `lasers.js`, `lasers3d.js` | A minimal laser brain on the Lasers v2 contract, mapped onto 21 projectors in 3D with physical power sharing. |
| `atmos.js` | The haze medium: the hazers, the lag, the cap, and our own tileable noise. |
| `camera.js` | Shots as data, centripetal Catmull-Rom paths driven by the beat position, and the director that cuts on bars. |
| `show.js` | Sections, the demo plan, and DROP NOW. |
| `flash.js` | The final-frame flash limiter: at most 3 flashes a second, red included. |
| `render.js`, `shaders.js` | The three.js r186 renderer and our own GLSL, composed with the house library. |

Tests: `node --test tests/stage_*.test.mjs`. The browser receipt: `node arsenal/lanes/stage_verify.mjs`. It runs
headless SwiftShader only, under the house GPU lock, on the test band.
