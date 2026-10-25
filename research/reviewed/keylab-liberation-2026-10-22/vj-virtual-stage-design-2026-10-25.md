# Virtual Stage design: our own show engine for the VJ rig (2026-10-25)

Workflow run wf_324eb0ef-7bf (task w0fkmktm1), the architect stage, written from the four research lanes (vj-virtual-stage-research-2026-10-25.md). Daniel, verbatim: "Also I want us to recreate that set or something similar with no fewer lasers and fog machines and lights. This will require research to find out how those things are wired and animated so we can build our own routines for this. They were able to do this in real life, surely in a 3d space we can come up with even more incredible and cinematic visual expirences! the arial shots they get we can use as suggestions for camera flypaths"

Verbatim; local paths shortened to <scratch> and <worktrees>. Qlimax footage, frames and downloaded specs stay in local scratch, never in this repo.

---

## The design (verbatim)

# The Virtual Stage: "Source"

This is the architect's design, dated 2026-10-24. It draws on:

- the four research lanes: lighting control; lasers, fog and kinetics; previz rendering; the Qlimax 2014 rig and camera;
- the repository as it stands today;
- checks I ran myself, listed in section 9.

Daniel's words (verbatim):

> "Also I want us to recreate that set or something similar with no fewer lasers and fog machines and lights. This will require research to find out how those things are wired and animated so we can build our own routines for this. They were able to do this in real life, surely in a 3d space we can come up with even more incredible and cinematic visual expirences! the arial shots they get we can use as suggestions for camera flypaths"

About Qlimax 2014:

> "I have not seen a better light show since ... this is the one I want us to land".

---

## 0. In plain words

We are building a concert hall inside the computer, with a show rig in it that behaves like real gear.

**What is in the rig**
- Every light is a real kind of fixture with the controls a real one has: pan, tilt, zoom, colour wheel, gobo, prism, frost and strobe.
- Each light moves no faster than a real motor can.
- Lasers split their power between their beams, as real projectors do. One hot beam is blinding; a fan of 24 beams is a lace.
- Haze shows the beams the way a hazer does. Beams pointing toward the camera blaze, and beams seen side-on are faint, as in the GelreDome.
- The DNA strand hangs from hoists that move at hoist speed.
- CO2 runs out of gas, a gerb fires once, and a spark machine has to warm up.
- The real limits are what make the big moments land.

**How you play it**
- You play it the way the Defqon.1 lighting designer plays a festival: about 90% live, firing prepared building blocks to the beat.
- Pads fire looks and effects.
- Faders are the masters for the strand, the beams, the pixels, the lasers, the haze and the speed.
- Knobs set spread and phase.
- Every move is measured in beats and locked to the engine's beat and to your Tap button.
- A routine is a few lines of data, the way designers write cues: which group, which look, which motion, how it spreads across the rig, and over how many beats.

**How it is filmed**
- A virtual camera crew uses the shots from the official Qlimax videos: the front-of-house lock-off, the crowd's view, the worm's-eye shot up the strand, the high tribune three-quarter view.
- It adds shots nobody in the room could get:
  - flying down the strand;
  - threading the rings exactly on the ONE;
  - circling the head;
  - looking straight down on the turning helix.
- It cuts or glides on bar lines and drops. The dial and knobs give you a manual camera whenever you want one.

**What 3D adds beyond real life**
- The strand can turn a full DNA twist; the real two-hoist rungs stop at about ±50°.
- Lasers can ride the rungs.
- CO2 plumes catch the green lasers.
- Effects can spread by any geometry: along the helix, around the rings, or outward from the DJ.
- The VJ scenes can be pixel-mapped onto the rings and the figure.
- There are more fixtures than the real show had: about 290 moving heads against roughly 100, and 53 laser projectors against about 11. The full count table is in section 6.8.

**The first slice (v0)**, which we can look at:
- the hall;
- a dozen real-parameter beam lights in haze;
- one strand of twelve rungs with cubes and dot strips moving in a wave;
- both laser banks driven by Lasers v2;
- the four-ring spiral;
- one flypath down the strand, arriving on the downbeat;
- everything on the beat;
- the flash limiter judging every frame.

**One question for you** is in section 10: should Source move like the real rig first, with dream moves saved for big moments, or the other way round?

---

## 1. Decisions at a glance

| Area | Decision | Why (evidence) |
|---|---|---|
| Renderer | **three.js r186 classic `WebGLRenderer` (WebGL2), with shaders written in GLSL and composed from the house library (`arsenal/web/glsl`).** The renderer sits behind a narrow FrameState contract, so a WebGPU renderer can be added later without touching the rig, programmer or camera. | (1) WebGPU does not exist in our headless receipts. On this machine headless Chrome 155 under SwiftShader reports WebGPU "unavailable_software", and the hdr-check run with `--enable-unsafe-webgpu --use-webgpu-adapter=swiftshader` logged "No available adapters" (`scratchpad/hdr/probe-result.json`, `scratchpad/hdrcheck/out-run4.txt`). A WebGPU live path would have no receipts. (2) Daniel's library rule from 2026-10-13: tweak one module and every surface updates. GLSL composes `volume/phase.glsl` (phaseHG), `volume/integrate.glsl`, `light/glow.glsl`, `post/display-out.glsl` and `post/dither.glsl` directly. TSL cannot. (3) A shared GL context with `vj.html` makes the stage a VJ set. Look v2, the gate v2 limiter (`vj-limiter.js`, WebGL2 only), the transitions and the VJ scenes as LED media are then reused unchanged. (4) The piano already runs r186 `WebGLRenderer` (`piano.js:441`). This **overrules the previz lane's WebGPURenderer/TSL verdict**; see section 4.1. |
| HDR | We render scene-linear HDR from day one. **HDR output** (brighter than white on the OLED) is a whole-rig Look v2 decision, not a stage decision. | The only shipping route to brighter-than-white output in Chrome is a WebGPU canvas in `rgba16float` with extended tone mapping (`hdr-check.js:3-9`). WebGL `drawingBufferToneMapping` exists in Chrome 155 only behind `--enable-experimental-web-platform-features` (probe: false by default, true with the flag). When it ships, the whole VJ page, the stage included, gains HDR output with no renderer change. |
| Hosts | v0 is a standalone `arena.html`. In v1 the arena becomes a set kind inside `vj.html`, on the shared GL context. Both hosts use the same modules. | v0 avoids colliding with the Look v2 lane, which is editing `vj.js`. v1 gives Daniel the stage as one more set he can switch to mid-show. |
| Name | The code name is **arena**: `arsenal/web/arena/…`. | `vj-stage.js` already exists; it holds the transitions and the look. |
| Scene format | `arsenal.arena/v1`, our own JSON in the shape of MVR and GDTF. Fixture types carry GDTF attribute names. Instancing generators expand a whole rig from a few lines. | A rig is data, not code. A GDTF/MVR import becomes a mapping job later. We write our own parser and never paste spec text. |
| Programming | A console-grade effects engine: one Spread object that covers MA MAtricks, ChamSys spread and Hog fan; speeds measured in beats; cue lines shaped like grandMA3 recipes; HTP dimmers and LTP for everything else; slew physics from GDTF's RealFade and RealAcceleration. | Every console's effects engine is the same machine under different names (lighting lane, section 4). The Q-dance practice is busking plus timecoded set pieces. |
| Clock | **One beat position for everything**: the page grid from Lasers v2 spec section 3.2, `pos(t)`, using the beat, `bar`, `ver` and tap fields from the S1 clock slice. Lasers, fixtures, kinetics and camera all read it. | Lasers v2 already prefers a clock's `posAt` when one is present (`vj-lasers.js:759`). Two grids would drift apart. |
| Lasers | The Lasers v2 engine stays the single brain. A pure adapter, `lasers3d.js`, maps its 21 heads onto 21 3D projectors. Its beams become 3D rays and its figures become sheets: a circle becomes a cone tunnel. Follower projectors multiply the light. | This reuses every pattern, gate, tier, order, colour mode and safety rule already built. |
| Flash safety | Three layers: (1) the FlashGate grants the deliberate full flashes; (2) a predictive governor keeps fixtures, pixels and camera cuts inside the budget before rendering; (3) the gate v2 limiter judges the final frame. The receipt is zero final-limiter interventions. | This is the house rule: at most 3 flashes a second, plus the saturated-red rule. Section 3.10 has a new rule found while designing. |
| Camera | Shots are data, drawn from the observed vocabulary plus our flypaths. A director infers the section, cuts on bars and holds through pyro. Manual mode uses the dial and knobs. | The rig lane's footage study: `camera-paths.json`. |
| Scale | Source v1 has about 290 moving heads, about 9,000 LED pixels, 53 laser projectors, 18 atmosphere units, 16 CO2 jets, 40 flames, 84 gerb mounts and 12 cold-spark units. That is at least the reconstructed real counts, then more. | Section 6.8. |

---

## 2. The model

### 2.1 Frame and units

- **Frame.** The origin is on the floor at the centre of the stage lip.
  - +x is house right: the audience's right when facing the stage.
  - +y is up.
  - +z runs out over the crowd.
  - This is three.js's right-handed frame, and the front-of-house camera looks down −z. It is identical to the rig lane's `rig-layout.json`.
- **Units.** Metres, degrees, and levels from 0 to 1. Time is in **beats** (seconds allowed as `{s: …}`). Colours are linear RGB, or a theme role (A, B, W).
- **MVR/GDTF bridge (v2).** GDTF and MVR are right-handed and Z-up, with X running left to right, Y into the screen, and 1 unit = 1 mm (verified in the spec copies: `gdtf-spec.md:202`, `mvr-spec.md:813`). The mapping is `three = (x, z, −y) / 1000`.
  - That matrix has determinant +1, so it is a proper rotation.
  - MVR's +Y (upstage) becomes our −z (behind the stage line).
  - This corrects the garbled line in the lighting lane's report.

### 2.2 Fixture types

Each type is a GDTF-shaped record:
- a geometry tree: Body, then Yoke (the Pan axis), then Head (the Tilt axis), then Beam or Pixel;
- attribute definitions: name, range, unit, home, snap or fade, `realFade` (seconds for a full-range move), `realAccel` (seconds from stop to full speed), HTP or LTP merge, and `flashRisk`;
- a beam definition.

The types are generic personalities we write ourselves from published class specifications. They are not copies of any manufacturer's personality. Travel times marked "est." are estimates until they are measured from footage or datasheets.

| Type | Class | Key parameters (our generic values) |
|---|---|---|
| `beam-7r` | Narrow beam head (Sharpy class [S7]) | Pan −270..+270° (realFade 2.2 s est.); Tilt −135..+135° (1.4 s est.); realAccel 0.2 s est.; Zoom 0.5–4°; Dimmer 16-bit HTP; Shutter1 (closed/open) + Shutter1Strobe 0.5–20 Hz (flashRisk local; unison runs go through the governor); Color1 wheel of 14 slots (snap, or proportional half-colours; 0.12 s per slot; rainbow spin); CTO; Gobo1 of 17 static slots (snap) + shake; Prism1 8-facet circular 12° + Prism1PosRotate; Frost1 0–1; Focus1. Beam type Spot, lens radius 0.07 m, 10,000 lm est. |
| `spot-hx` | Hybrid beam/spot head (MegaPointe class [S6]) | Pan 540°; Tilt 265°; Zoom 1.8–42°; CMY + 14-slot wheel + CTO; a static and a rotating gobo wheel (index or rotate); two prisms (6-facet linear, 8-facet circular); light and medium frost; iris; strobe (slow to fast, pulse, random); Dimmer 16-bit. |
| `wash-z` | LED wash with zoom | Pan 540°; Tilt 270°; Zoom 5–55°; ColorAdd R/G/B/W; Dimmer; strobe. Beam type Wash (soft edge). |
| `strobe-a` | LED strobe panel (Atomic class [S8]) | Dimmer; StrobeFrequency 0.3–16.7 Hz; StrobeDuration 7–650 ms; an RGB aura cell. flashRisk **full**: it only fires through the FlashGate or as a sparkle. |
| `blinder-2` | Two-cell warm blinder | Dimmer per cell. flashRisk full. |
| `px-bar-32` | Linear pixel bar, 1.0 m | 32 cells, ColorAdd_R/G/B per cell (GDTF GeometryReference with Breaks). |
| `px-matrix-8` | Square matrix mounted as a diamond | 8×8 cells. |
| `px-dots-12` | Warm-white dot strip | 12 cells, white and amber. |
| `cube-6` | Translucent cube lit from inside, 1.1 m | 6 face cells. Rendered as an emissive box with a soft internal falloff. |
| `slat-8` | Ring slat | 8 cells along the slat. |
| `rim-strip` | Ring outline | One cell per 0.25 m. |
| `facet-skin` | The figure's surface | One cell per facet, plus a seam glow. |
| `laser-10w` | RGB show laser | Scan ±30°; 40 kpps; R 2 W / G 3 W / B 3 W; divergence 0.6 mrad full angle; 3 mm aperture; a scanner model (second order plus slew); roles aerial, curtain, truss-down, ring, burst [L1, L11]. Driven by Lasers v2, as a core head or a follower. |
| `hazer` | Oil or fluid hazer [F2] | Haze1 0–1; fan. Warm-up 8 min, compressible in Source mode. Room lag τ ≈ 30 s est.; fluid budget. |
| `fogger` | Fog burst | Fog1 bursts, then a heater recovery time. |
| `lowfog` | Chilled ground fog [F4] | Output 0–1. Layer 0.3–1 m deep, τ ≈ 40 s est. |
| `co2-jet` | CO2 jet [C1, C2] | Valve open for at most 3 s per burst; 0.5 kg/s; a 30 kg cylinder; plume about 8 m × f(RH); LED plume light. |
| `gerb` | Pyro gerb [P4, P5] | One shot only; named seconds × height (for example 4 s × 3.7 m); silver or gold; mount up, diagonal or waterfall; leaves a smoke puff. |
| `spark-cold` | Cold spark machine [P1] | Preheat 300 s (compressible in Source mode); 10 height steps, 1.5–5 m; at most 30 s of continuous firing, then a forced rest. |
| `flame` | Flame projector [P6, P10] | A safety channel must be armed. Height 3–8 m; fuel budget; minimum gap of 1 per beat per unit (est.). |
| `hoist` | Kinetic axis [K1–K4] | 16-bit position (mm); vmax 0.5 m/s, amax 0.4 m/s², jerk 2 m/s³ (est.); soft limits; a group window. |
| `tilt-axis` | Ring tilt | 6°/s realistic (rig lane), with S-curve moves. |
| `trolley` | Dream only | x/z travel, so rungs can slide along the strand. |

**Colour systems.**
- Wheel and CMY fixtures resolve to linear RGB through their filter tables, with snap or half-colour behaviour on the wheel. A half-colour split beam is a v1 render feature.
- LED fixtures add R, G, B and W.
- Presets say **theme roles**: `col.A`, `col.B`, `col.W`, `col.split`. These resolve each frame through `vj-themes.js` `themeLook()`. Beams use the theme's `beam` pair, pixels its A and B, and white-hot is W.

### 2.3 Pixel fixtures are fixtures

- Every LED cell is a fixture cell with ColorAdd_R/G/B and a Dimmer.
- A cell carries its world position, so a spread can order cells by any geometry, the same as moving heads.
- LED content reaches the cells three ways:
  1. **Group effects** spread over the cells.
  2. **Field effects** evaluate a function of world position and beat position. Examples: a plane sweeping along any axis, a sphere expanding from a point, a chase by helix parameter, the polar DNA chase seen around the rings in the Noisecontrollers show at 160–180 s, a crackle, a dot spiral.
  3. **Media mapping** samples a texture through a projection: planar from front of house, polar on the rings, UV on the figure's facets.
- In v1 the texture can be any VJ set, rendered on the shared GL context at no copy cost.

### 2.4 Atmosphere: one shared medium

- **Base haze.** σs(x, t) = σ0·H(t)·(1 + a·n(x − w·t)) + Σ puffs.
  - H(t) is the haze master, run through the machines' lag.
  - n is our own tileable 64³ noise, advected by a slow wind of 0.1–0.5 m/s.
  - The albedo is about 1, so σt ≈ σs.
- **Phase function.** Henyey–Greenstein with g = 0.75 for haze and g = 0.85 for fog and CO2 [F6].
- **Ranges** (Koschmieder, V = 3.912/σ [F11]):
  - arena haze: σ from 0.003 to 0.02 m⁻¹, a visibility of about 1,300 m down to about 200 m;
  - a local fog burst: up to 0.26 m⁻¹, a visibility of 15 m. **Never denser than that**, which is the whiteout guard (receipt F1).
- **Puffs.** Up to 32 spheres of density, from fog shots, CO2 and pyro smoke. Each has a position, radius, density, decay τ and a cold tag (cold puffs sink).
- **Low fog.** An analytic height layer with exponential falloff, plus a 2D flow texture.
- The beams, the lasers and the fog bodies all sample this one medium. A laser therefore flares where it crosses a CO2 plume with no special case.

### 2.5 Kinetics

**Axis.** Each axis has a position, vmax, amax, dmax and jerk; soft limits; speed priority or time priority; a delay; and a group window.

**Element.** An element is a rigid body hung from 1 to 4 pickups:
- 1 pickup gives height only;
- 2 give height plus roll about the strand axis, with roll θ = asin(Δz/L);
- 3 give height, roll and pitch;
- a trolley adds x/z travel.

Children are fixtures, pixels, gerbs, flames and lasers. They inherit the element's pose. A child can also aim in **world-locked** mode, tracking a focus point the way consoles use PosiStageNet [K11]: its pan and tilt are solved each frame from the element's live pose.

**Limit filter.** Formation targets go through a jerk-limited S-curve follower on each axis [K13]. Nothing can ask for physically impossible motion. Dream mode multiplies the limits and keeps the S-curves and the settle, so the mass still reads.

**Landing on a beat (time priority).**
- An axis's minimum move time is T = D/v + v/a when D ≥ v²/a, and 2√(D/a) otherwise.
- Example: a 6 m move at 0.4 m/s and 0.4 m/s² takes 16 s, which is 10 bars at 150 BPM. I checked this arithmetic.
- A formation move takes the largest T over its axes, rounds it up to the next bar or phrase line, and runs every axis so they all arrive together, on the ONE.

**Settle.** After a stop there is a damped settle of 0.5–2 s (est.). True pendulum swing applies only to items moved horizontally (T = 2π√(L/g)).

**Real versus dream** (presets; the multipliers are Daniel's call):

| | Real ("Qlimax mode") | Dream ("Source mode") |
|---|---|---|
| Hoists | 0.5 m/s, 0.4 m/s² | ×3 |
| Rung roll | ±50° | unlimited, continuous spin |
| Rung yaw and travel | none | trolleys and yaw |
| Ring tilt | 6°/s | 20°/s, plus spin about the ring's own axis ("chopper") |
| Cold-spark preheat | 300 s | 30 s |
| CO2 burst cap, pyro inventory | always enforced | always enforced (scarcity is the point) |

### 2.6 Groups, grids and focus points

- **Groups.** A group is a selector over the expanded rig, for example `rung.*/beam-7r`. It has a selection grid (x, y, z indices, as in grandMA3) and a centre.
- **Spread orders.** Spreads can order a group by:
  - `index`, `gridX`, `gridY`, `gridZ`;
  - world `x`, `y`, `z`;
  - `azimuth` and `radius` about the centre;
  - `helix` (the parameter along the strand);
  - `distanceTo(point)`;
  - `camera`: screen x from the live camera, so a chase always runs left to right on screen. This one is beyond real.
- **Focus points.** `dj`, `head`, `crowd-centre`, `pit`, `roof`, `foh`, `ring-hub`.

### 2.7 The scene file, `arsenal.arena/v1`

The top-level keys are:
- `format`, `name`, `units`, `frame`, `seed`;
- `venue`;
- `types`: the fixture types;
- `objects`: structures, elements and their child fixtures, with `repeat` generators;
- `groups`, `focus`, `presets`, `effects`, `formations`, `sequences`, `playbacks`;
- `lasers`: the mapping of Lasers v2 heads to projectors, plus followers;
- `atmos`, `sfx`;
- `cameras`: shots;
- `show`: the section playbooks, the pad page, the fader map and the mode (real or dream).

`expandScene()` turns this into flat typed arrays deterministically. `py -m arsenal …`-style tooling, or `node … expand`, can print the expanded rig for inspection.

Abridged excerpt (valid JSON):

```json
{
  "format": "arsenal.arena/v1",
  "name": "Source v0",
  "units": { "length": "m", "angle": "deg", "time": "beats" },
  "frame": "origin floor at stage-lip centre; +x house right, +y up, +z over the crowd",
  "seed": 2014,
  "venue": { "floor": { "x": [-38, 38], "z": [-24, 96] }, "roof_y": 38, "grid_y": 33,
             "stands": { "rake_deg": 30, "top_y": 30 }, "crowd": { "floor": 18000, "stands": 12000 } },
  "types": {
    "beam-7r": {
      "geometry": { "kind": "Body", "children": [ { "kind": "Yoke", "axis": "Pan", "children": [
        { "kind": "Head", "axis": "Tilt", "offset": [0, -0.32, 0], "children": [ { "kind": "Beam", "radius": 0.07 } ] } ] } ] },
      "beam": { "type": "Spot", "angle": [0.5, 4.0], "field_over_beam": 1.15, "flux_lm": 10000,
                "prisms": [ { "facets": 8, "layout": "circular", "spread_deg": 12 } ] },
      "attrs": {
        "Pan":    { "min": -270, "max": 270, "home": 0, "unit": "deg", "real_fade": 2.2, "real_accel": 0.2 },
        "Tilt":   { "min": -135, "max": 135, "home": 0, "unit": "deg", "real_fade": 1.4, "real_accel": 0.2 },
        "Dimmer": { "min": 0, "max": 1, "unit": "level", "bits": 16, "merge": "HTP", "real_fade": 0.08 },
        "Zoom":   { "min": 0.5, "max": 4.0, "unit": "deg", "real_fade": 0.6 },
        "Shutter1Strobe": { "min": 0.5, "max": 20, "unit": "Hz", "flash_risk": "local" },
        "Color1": { "wheel": 14, "modes": ["snap", "half"], "slot_time": 0.12 },
        "Gobo1":  { "wheel": 17, "snap": true },
        "Prism1": { "slots": 2, "snap": true }, "Prism1PosRotate": { "min": -1, "max": 1, "unit": "rev/s" },
        "Frost1": { "min": 0, "max": 1 }, "Focus1": { "min": 0, "max": 1 }
      },
      "estimate": "generic class personality; travel times estimated"
    }
  },
  "objects": [
    { "id": "rung", "kind": "element", "repeat": { "count": 12, "z": { "from": 4.0, "step": 3.6 } },
      "pickups": [[-4.3, 0, 0], [4.3, 0, 0]], "dof": ["y", "roll"], "axis_type": "hoist",
      "home": { "y": 20, "roll": 0 }, "limits": { "y": [8, 22], "roll": [-50, 50] },
      "mesh": "procedural:rung-v1",
      "children": [
        { "type": "cube-6",     "at": [[-4.5, 0, 0], [4.5, 0, 0]], "tags": ["backbone"] },
        { "type": "px-dots-12", "at": [[-3.6, 0, 0], [3.6, 0, 0]] },
        { "type": "px-bar-32",  "at": [[-2.2, 0, 0], [2.2, 0, 0]] },
        { "type": "beam-7r",    "at": [[0, -0.6, 0]], "rot": [180, 0, 0] }
      ] }
  ],
  "groups": {
    "strand.heads": { "select": "rung.*/beam-7r", "grid": { "x": "local.x", "z": "rung.index" } },
    "strand.cubes": { "select": "rung.*/cube-6" }
  },
  "effects": {
    "strand-wave": { "attrs": ["Dimmer"], "form": "sine", "size": 0.5, "measure": 4,
                     "phase": { "order": "helix", "from": 0, "to": 360, "cyclic": true } }
  },
  "formations": {
    "wave": { "rung": { "y": { "gen": "sine", "centre": 15, "size": 3, "measure": 32,
                                "phase": { "order": "index", "from": 0, "to": 360, "cyclic": true } }, "roll": 0 } }
  }
}
```

---

## 3. The programming layer

### 3.1 The clock: one beat position

- `grid.js` implements the page grid from Lasers v2 spec section 3.2: pos(t) = anchor + (t − t_anchor)/period.
  - When `ver` changes, it re-anchors hard at that beat.
  - If |e| ≤ 0.25 beat, it slews by stretching the next beat by up to ±10%; pos never runs backward.
  - If |e| > 0.25 beat, it re-anchors hard.
  - It also reports `bar` (1–4, from S1's `bar`/`bar_src`), `phrase` (8 bars, counted from the last drop or from a tap on the ONE; a guess otherwise) and the confidence ladder L0–L3.
- Light is evaluated at the presentation time, `tEval = rafNow + presentLagMs`, as Lasers v2 does.
- The same object is handed to the `LaserEngine` as its clock, which prefers `posAt` (verified), so the lasers, fixtures, kinetics and camera never disagree.
- If another lane lands a shared `vj-grid.js` first, the arena uses it instead.

### 3.2 State, merge and masters

- State is held per frame as structure-of-arrays typed arrays: fixture × attribute, plus pixel × RGBA.
- The order of evaluation is:
  1. playbacks, which advance cues with fade and delay spreads;
  2. merge: Dimmer is HTP × the playback master; every other attribute is LTP by priority, then by last activation;
  3. Flash, Temp and Swap on top;
  4. effects;
  5. submasters, grand master, blackout;
  6. colour resolve (theme roles, then the fixture's colour system, then the red rule);
  7. physics;
  8. FrameState.
- At Source v1 scale this is about 300 heads × 20 attributes plus 9,000 pixels × 4 per frame, a few milliseconds of JavaScript. The cost lives on the GPU.

### 3.3 Presets

Presets are organised by GDTF feature group: Dimmer, Position, Colour, Gobo, Beam, Focus.

Position presets can be:
- **absolute**: pan and tilt values;
- **fanned**: from/to values with a Spread;
- **world-locked**: aim at a focus point, solved every frame for fixtures riding kinetics.

### 3.4 The effects engine

```ts
type Waveform = 'sine'|'cos'|'triangle'|'rampUp'|'rampDown'|'square'|'pulse'|'stepN'|'random'
  |'flicker'|'circle'|'figure8'|'ballyhoo'|'spiral';
interface Spread {                 // one object = MA MAtricks / ChamSys spread / Hog fan
  order: 'index'|'gridX'|'gridY'|'gridZ'|'x'|'y'|'z'|'azimuth'|'radius'|'helix'|'distance'|'camera'|'random';
  block?: number;                  // n neighbours share a value  (MA Block = ChamSys Segments = Hog Buddying)
  repeat?: number;                 // pattern restarts every n     (MA Group = ChamSys Parts = Hog Segments)
  wings?: number; mirror?: boolean;
  shuffle?: number; reshuffleEvery?: Dur; shift?: number; reverse?: boolean; invert?: boolean;
  from: number; to: number; cyclic: boolean;   // cyclic phase: u = i/N (0 and 360 coincide); fans and delays: u = i/(N-1)
}
interface Effect {
  attrs: Attr[]; form: Waveform | { steps: Step[] };   // steps: grandMA3 phaser steps with width, transition, accel, decel
  mode: 'relative'|'absolute'; add: 'normal'|'plus'|'minus'|'abs';
  size: number; width?: number; transition?: number; floor?: number;  // floor: the lowest level of a dimmer pulse (3.10)
  measure: number;                  // beats per cycle
  speedMaster: string; scale?: number;               // x2, /2, /3, /4, /8
  phase: Spread; direction?: 'fwd'|'back'|'bounce'; shots?: number;
  fadeIn?: Dur; fadeOut?: Dur; flashRisk?: 'none'|'local'|'full';
}
```

**Evaluating a spread.**
1. Order the group by `order`.
2. Fold it into wings, mirroring alternate wings if `mirror` is set.
3. Collapse each block of neighbours to one index.
4. Take the index modulo `repeat`.
5. Normalise to u (cyclic divides by N; one-shot fans and delays by N−1).
6. Apply the seeded shuffle, then shift, then reverse.
7. The value is `from + u·(to − from)`.

The result is cached per (group, spread) pair. Orders that depend on geometry or the camera are recomputed only when their inputs move.

**Phase.** Each effect keeps an accumulator: φ += Δpos·scale/measure each frame. Fixture i reads x = frac(φ + phase_i). This rule set keeps effects beat-locked through tempo changes, speed changes and taps:
- **Never compute t·bpm.** A tempo change must not make the phase jump.
- **Speed-scale changes land on the next beat line.** Changes of ×4 or more land on the next bar. At that line the accumulator is re-anchored to `frac(pos·scale/measure)`.
- **A `ver` re-anchor (a tap) re-anchors every accumulator at that beat.**

**The vocabulary.**
- The lighting lane's 22 musical defaults:
  - dimmer: chase, wave, kick pulse;
  - position: fan breathe, tilt saw, crossing X, circle, figure 8, ballyhoo, fly-out;
  - pixels and colour: ripple, helix, colour bump, rainbow roll;
  - beam and texture: sparkle, strobe burst, zoom punch, iris pinch, prism spin, gobo shake;
  - kinetics and atmosphere: kinetic wave, haze push.
- Our additions, possible only in 3D:
  - **plane sweep**: a light plane passes through the rig along any axis;
  - **sphere ripple** from any point;
  - **helix chase**: phase by helix parameter, two wings 180° apart, so the two backbones answer each other;
  - **camera chase**: on-screen left to right, whatever the camera.

### 3.5 Physics

- Each attribute follows its target through a slew limit: maximum velocity = range/realFade and acceleration = maxVelocity/realAccel.
- Snap attributes jump: wheel slots, gobo selection, shutter.
- **Move in black** (Early, Late, None, as in grandMA3 [S19]) repositions an attribute while its dimmer is at 0, so nobody sees a head swing into place.
- Kinetics use the limit filter from section 2.5.

### 3.6 Cues, sequences, playbacks and routines

**A cue line** is a grandMA3 recipe line [S20]. It names a group, then optionally:
- a preset;
- values;
- an effect;
- a fade and a delay, each optionally spread across the group;
- a kinetic formation, with `land` set to `bar`, `phrase` or `{beat: n}`;
- an SFX fire;
- a laser instruction (`laser.section`, `laser.bank`, `laser.pattern`).

**A cue** has parts and a trigger. Triggers are `go`, `follow`, `time`, `beat`, `bar`, `phrase`, `sound` (a band and threshold) or `timeline`. Each cue also has an MIB mode.

**A sequence** is a cue list or a chaser, with tracking, wrap, priority and a restart mode.

**A playback** binds a sequence to a pad, a fader, both, or the director. It has a quantize setting (`now`, `beat`, `bar`, `phrase`) and an action (`go`, `flash`, `temp`, `toggle`, `swap`, `kill`).

**A routine** is a named bundle of cue lines plus the sections it suits. It is what Daniel writes. **A timeline** is a bar-addressed list of cues for timecoded set pieces (the "endshow"), triggered by a pad or a section.

Authoring loop:
1. Edit JSON.
2. `arena.html?engine=…` hot-reloads the set.
3. The knobs change live effect parameters.
4. In v1, "store" (holding Record plus a pad) writes the current look to a pad, and "export" downloads the set's JSON.

### 3.7 Song structure

**Sections** use the Lasers v2 vocabulary: intro, anti, groove, build, drop, climax, break, outro, and so on.
- `sections.js` estimates the section from the energy, bass and hits, using the rig lane's rules (camera-paths.json, `section_detection_from_vj_engine`).
- Pads override it: BUILD and DROP NOW.
- The one estimate feeds the programmer's section playbooks, `LaserEngine.setSection()`, the ThemeDirector and the camera director.

**The grammar** (the lane's proposal, adopted):
- **Build** over 8 or 16 bars:
  - the speed scale doubles every 4 bars on bar lines;
  - pulse widths narrow;
  - tilts converge up onto the head;
  - zoom narrows;
  - saturation drains toward white;
  - lasers switch to the `build` patterns (ladder, tunnel, cone);
  - the haze push starts 8 bars before the drop;
  - "the sky comes down": the kinetics lower the strand in time priority, landing on the ONE;
  - the last beat before the drop is black.
- **Drop:**
  - a Go quantized to the downbeat;
  - unison Kick lift plus Fly-out;
  - CO2 and the gerb row, if armed;
  - lasers switch to `drop`;
  - the formation lands, for example the star cluster;
  - the camera hard-cuts to the widest hero shot and holds it for 2 bars.
- **Breakdown:** wave, rainbow roll, the helix turns (and spins in dream mode), long camera glides.
- **Contrast** [S32]: optionally, one drop in N is darkness and a single beam. N is Daniel's call.

### 3.8 The KeyLab map (proposed defaults; Daniel's call)

All numbers are as inferred from Arturia's FL script, and everything stays learnable on touch, as in `vj.html`.
- **Faders** are absolute and never change layers, so there are no pickup jumps.
- **Knobs** are relative, so layering them is safe.

| Control | Arena (standalone host) |
|---|---|
| Pads 1–4 (row 1) | 1 KICK (a Flash playback: strand cubes and beams lift; velocity sets size) · 2 LASERS (exactly Lasers v2 pad 2: retrigger tiers, hold = gate) · 3 CO2 (held up to 3 s; velocity = number of jets) · 4 FIRE (tap = gerb salvo, hold = flame chase on beats; only when armed) |
| Pads 5–8 (row 2) | 5 SPARKLE (held; full unison strobes only through the FlashGate) · 6 FLY-OUT (one-shot radial burst) · 7 NEXT LOOK (Go+ on the section's cue list, on the bar) · 8 FORMATION (next kinetic formation, lands on the phrase) |
| Pads 9–12 (row 3) | 9 BUILD (start the build grammar; press again to cancel) · 10 DROP NOW (on the next downbeat) · 11 KILL (black on the next beat; press again to bring it back) · 12 DAMPEN (tap) / CHOKE (hold) |
| Faders 1–9 | F1 Strand · F2 Beams (truss, towers, PA, lip) · F3 Pixels (rings, figure, cubes, bars) · F4 Lasers · F5 Haze (a target level that moves over minutes) · F6 Speed (detents at ¼, ½, 1, 2, 4; beat-locked) · F7 Theme (vj-themes FaderPicker detents) · F8 Camera energy (low = long glides, high = cut on every bar at drops) · F9 Grand master |
| Knobs 1–9 | K1 Spread (0 = unison, 1 = as programmed, 2 = double) · K2 Size · K3 Wings (detents 1–4, mirrored) · K4 Block (1–4) · K5 Zoom trim · K6 Strand height trim · K7 Laser reach (the depth ratio k, section 4.3) · K8 Bass react · K9 Camera nudge (a ±30° orbit offset in auto) |
| Dial | Turn = choose the next shot; click (CC 117, inferred) = take it on the next beat. Double-click = **manual camera**: K1 yaw, K2 height, K3 distance, K4 FOV, K5 roll, K6 glide time, and the dial picks the look-at point. Back (CC 40, inferred) returns to the auto director, which resumes with a glide on the next bar. |
| Tap (CC 23, DAW port) | Handled by the engine (S1): one tap re-phases the beat, four take over tempo and phase. The arena re-anchors on `ver`. |

**In the vj.html host (v1):**
- The arena set claims pads 1–10 as native (`"accents":{"native":[1,…,10]}`). The page keeps 11 (kill) and 12 (next set).
- The page's faders keep their meaning: `bright` becomes the grand master, `accent` the accents, `strobeRate` the sparkle rate, and so on.
- Set knobs k1–k8 become arena knobs K1–K8.
- The page's dial keeps scene browsing, so the camera has to move to another control. Proposal: K9, or the arena's own panel.

### 3.9 Signature routines (written as data in `source.json`)

1. **Helix Turn** (breakdown):
   - strand heads run Circle (Pan and Tilt) with helix order 0→720°, two mirrored wings, over 8 beats;
   - cubes run a Wave with helix order;
   - formation `helix` with a roll step of 15°, landing on the phrase;
   - in dream mode, continuous spin at 36° per rung.
2. **Star Bloom** (build into drop):
   - the front 6 rungs lower to the pit at rolls 0, 30, 60, 90, 120 and 150° (the mandala), landing on the ONE;
   - Fly-out by azimuth on the drop;
   - violet radial fans;
   - gerbs from both cubes.
3. **Truss Fan and Tilt Saw** (groove): truss rows breathe in a fan (mirrored wings) plus a Tilt rampUp on the kick, in the theme's beam B.
4. **Cube Ripple**: a sphere ripple from the DJ; delay spread by radius over 2 beats; magenta.
5. **Dot Chase**: dot strips chase Centre-In along each rung's arms, with a block of 2.
6. **Laser Lattice**: Lasers v2 `cross` and `scissors` on Bank B plus Bank A, k = 0.6, in haze; mostly green (theme-dependent).
7. **Spiral Ring**: a polar field on the four or five rings. The DNA chase runs around the rims and the slats step on the beat. Stepped tilts give the spiral pose.
8. **The Sky Comes Down** (build): the strand lowers from 20 m to 9 m in time priority over the build. This is the Qlimax "four-minute rise" played in reverse at phrase scale.
9. **Fire Crown** (finale): a flame chase down the strand (one rung per beat), the crown gerbs, all CO2 on the ONE, and a wide camera held through it.
10. **Contrast Drop**: everything black except one hot beam from the hero laser for 1 bar, then the full drop.

### 3.10 Flash safety in the programmer (a new rule)

**The new rule: a unison beat pulse is a lift, not a flash.** Gate v2 forces a 2 s rest after 5 s in which some window carries at least 4 full-size transitions a second. A full-size transition is a swing of 0.09 or more in relative luminance (`vj-gate.js` LIMIT: TH_REST, REST_COUNT 4, RUN_S 5, REST_S 2).
- A unison 0→100% dimmer pulse on every beat at 150 BPM is 5 transitions a second.
- If it lights a quarter of the frame or more, it trips the rest within 5 s, and the limiter takes over the frame.
- So unison dimmer effects default to `floor ≥ 0.6` (from 60% to 100%).
- Full-depth pulses are allowed only as chases, with a phase spread of 90° or more, so that no quarter-frame window swings in unison.
- The governor enforces this.

**The red rule.** Saturated red (R/(R+G+B) ≥ 0.8) is held, never strobed, per the vj-themes rule. While an effect with flashRisk local or full drives a fixture, a red colour on it is swapped for the theme's flicker role, as Lasers v2 does.

**The governor** (`governor.js`, v1). Each frame, before rendering:
1. Project every lit fixture's beam (8–16 points along the visible axis, with its width), its emitter, its pixels, and the projected Lasers v2 segments through the live camera into a 64×36 predicted-luminance grid.
2. Feed `cellSums()` of that grid to a JS `FlashLimiter` (vj-gate.js) in advice mode.
3. If a window would be held:
   - unison flash-risk effects become a desynchronised sparkle;
   - pulse transitions soften;
   - accent levels for that window's fixtures drop;
   - the camera director defers a cut whose predicted exposure jump is 0.07 or more.
4. Deliberate full flashes (unison strobe bursts, the CO2 whiteout, flame salvos, a drop cut into a bright shot) ask the page's FlashGate first.

Receipts:
- the predicted and metered cell luminance correlate at 0.9 or better over the scripted sequence;
- the final limiter records **zero interventions**.

---

## 4. The renderer

### 4.1 The choice, and why it overrules the previz lane

The previz lane's research is right on technique: analytic cones, ribbons at least one pixel wide, a shared density field, Karis bloom, and no TAA or motion blur on beams. Its platform verdict (WebGPURenderer with TSL) does not survive four checks:

1. **Receipts.** WebGPU is unavailable in headless SwiftShader here, even with the unsafe flags. "No available adapters" is logged in `hdrcheck/out-run4.txt`, and featureStatus reads `webgpu: unavailable_software`. Every receipt would test the fallback backend only. The live path would ship unreceipted, against the drill doctrine.
2. **The house library.** TSL cannot compose the house GLSL modules. Daniel's 2026-10-13 rule is that every surface composes from them.
3. **Integration.** On WebGPU, the limiter (`vj-limiter.js`, raw WebGL2), Look v2 (GLSL) and the VJ scenes used as LED media would each need a port plus parity receipts, and the VJ scenes would need a copy across APIs every frame. On the shared WebGL2 context, all of them are reused as they are.
4. **HDR.** HDR output is the one real WebGPU advantage. It is a rig-wide Look v2 question, and the WebGL route is already in Chrome behind a flag.

**The base, therefore.**
- three.js r186 `WebGLRenderer`, at the same pinned version as the piano.
- `ShaderMaterial` and `RawShaderMaterial` using GLSL 3, composed through `modlib.js`.
- Scene-linear HDR goes into RGBA16F targets.
- The renderer shares the host's GL context. It calls `renderer.resetState()` before and after its own passes, and its result is copied into the host's target with `blitFramebuffer`.
- **Keep the door open.** The renderer consumes only FrameState (section 4.7). A "renderer B" on WebGPURenderer/TSL can be added in v2 if HDR through WebGPU or compute at a scale of a million particles is wanted. It would need its own receipts, and those would require a real-GPU receipt path.

**Spike S0 decides this before anything else is built** (section 8). If three r186 cannot share the context with the house finish chain and limiter on SwiftShader, we fall back to the previz lane's plan: WebGPURenderer forced onto its WebGL2 backend, with TSL.

### 4.2 The frame graph (WebGL2)

1. **CPU.** The programmer, kinetics, Lasers v2 plus lasers3d, SFX, the director and the governor produce a FrameState. The CPU also uploads the instance buffers and the LED texture (RGBA16F, 128×128 in v0 and 256×128 in v1).
2. **Opaque pass** (4× MSAA RGBA16F with a depth texture). It draws:
   - the venue, trusses, rungs and figure;
   - the crowd: 30,000 instanced silhouettes, with hands animated by energy and hits, and tiny phone-screen emitters in breakdowns;
   - the LED emitters: dots, cubes, bars, slats, rims and facets;
   - a few hero lights for surfaces.
3. **Depth downsample** to a half-resolution min/max depth.
4. **Wide beams** (half resolution, additive):
   - instanced cone proxies are drawn with back faces only, so the camera can sit inside a beam;
   - the fragment shader intersects the view ray with the cone analytically, clipped by scene depth;
   - the in-scatter is integrated as in section 4.3;
   - gobo and prism arrive in v1.
5. **Thin beams and lasers** (full resolution, additive): ribbons at least 1 px wide, coverage-scaled; sheets; dots where beams hit surfaces.
6. **Fog bodies** (v1): CO2, fog puffs and pyro smoke, ray-marched at quarter resolution in 16–24 steps against the shared medium.
7. **Particles** (v1): gerb and cold-spark sparks as instanced velocity-stretched sprites whose motion is a pure function of time since launch (no state, deterministic); flames as emissive volumetric billboards.
8. **Composite**: a depth-aware bilateral upsample of the beams [Kopf], plus lasers, particles and fog, giving scene-linear HDR.
9. **Finish**, owned by the host: bloom (Look v2's `post/bloom.glsl`), then `post/display-out.glsl`, then `post/dither.glsl`, then the gate v2 limiter, then the canvas.

### 4.3 Techniques and the physical laws

**Wide beams.** The in-scatter integral is L = ∫ σs(x) · I(ω)/r² · p_HG(cos θ) · T ds.
- Its 1/r² part along the segment has a closed form, a difference of arctangents [Macklin; Sun et al. 2005].
- The phase, the beam profile, the gobo and the haze noise are sampled at 4–8 stratified points with blue-noise jitter. The jitter is spatial only: no temporal reuse on beams.
- The profile runs from the beam angle (50%) to the field angle (10%), per GDTF.
- A beam narrower than about 6 px on screen moves to the thin path.

**Thin beams and lasers.** On-screen radiance is L_px ≈ σs · p_HG(θ) · Φ · T / (d · sin γ · a · w).
- a is the angular size of a pixel and w is the ribbon width in pixels.
- Physical width = aperture + divergence × distance. The drawn width is the larger of that and 1 px, plus a 1 px fringe, with intensity scaled by coverage ["phone-wire AA", Persson].
- The receipt (L4) checks the law on a synthetic scene. With g = 0.75, p(30°)/p(90°) = 14.4, so a beam seen 30° off its axis is 28.9 times brighter than the same beam side-on, and p(0°)/p(90°) = 125. I checked these numbers.

**What the physics means for the camera.**
- Shots that look into the emitters blaze; side and aerial shots are dimmer by 10 to 60 times.
- Each shot therefore carries its own exposure (EV). We never fake beam brightness.

**LED emitters.** Instanced emitters take their colour from the LED texture. The pixel grid is filtered with derivatives, so aerial shots show no moiré [Golus]. Bloom is what makes them read as lights.

**Structure and figure.** Cheap physically based shading, mostly dark, lit by spill.
- The shared medium carries an "ambient bounce" estimate: the mean beam power in the room tints the haze glow.
- The figure's facets are pixel-mapped emitters with glowing seams.

**Temporal stability.**
- 4× MSAA on geometry and analytic coverage on lines.
- **No TAA and no motion blur on beams or lasers** (Lasers v2 rule 4).
- Exposure is fixed per shot. Auto-exposure would pump on strobes and manufacture flashes.
- Camera cuts reset all temporal history.

### 4.4 Look v2 and HDR

- The arena writes finite, non-negative scene-linear light, with no tone curve, no `pow` and no clamp. This is the strip-v2 header contract `"output":"hdr"` from the Look v2 plan.
- Look v2 owns bloom, the display curve and dither. The arena never tone-maps.
- **HDR output, v2** (Daniel's call on timing):
  - either WebGL `drawingBufferStorage(RGBA16F)` plus `drawingBufferToneMapping({mode:"extended"})` once Chrome ships it (or under the flag, for a trial on his machine with the hdr-check page);
  - or renderer B on WebGPU.
- Either way the limiter must first meter in cd/m² against BT.1702-3's HDR thresholds, with the reference white agreed with the limiter's owner.

### 4.5 Budgets (estimates until the real-GPU bench)

Targets: 1080p, 60 Hz, an RX 6600-class card (8.9 TFLOPS, 224 GB/s, 32 MB Infinity Cache).

| Stage | Cap (Source v1) | Est. ms |
|---|---|---|
| CPU: programmer, kinetics, lasers3d, SFX, governor, director | 300 heads, 9k pixels, 1.3k laser segments | 2–3 (CPU, overlaps the GPU) |
| Upload | about 250 KB per frame | 0.1 |
| Opaque, 4× MSAA | 1.5M triangles, ≤100 draws, 9k emitters, 30k crowd | 1.8–2.5 |
| Depth downsample | — | 0.1 |
| Wide beams, half resolution | 900 cone instances (heads × prism) | 1.5–2.5 |
| Thin beams and lasers, full resolution | 1,300 segments plus sheets | 0.5–1.0 |
| Fog bodies, quarter resolution | 32 puffs, 24 steps | 0.5–1.0 |
| Particles | 100k sparks, 20k flame sprites | 0.5 |
| Composite and upsample | — | 0.3 |
| Bloom (Look v2) | 6 mips | 0.5 |
| Display, dither, limiter | — | 0.6 |
| **GPU total** | | **about 7–10, target ≤ 11** |

- **GPU memory** is about 150 MB. The 1080p RGBA16F target is 16.6 MB; at 4× MSAA with depth it is about 100 MB.
- **The quality ladder** steps on measured frame time (`EXT_disjoint_timer_query_webgl2` when available), with 2 s of hysteresis:
  1. beams from ½ to ⅓ resolution;
  2. fog bodies off, replaced by an analytic height fog;
  3. MSAA from 4× to 2×;
  4. bloom from 6 mips to 4;
  5. render scale 0.85.
- **Never reduced**: fixture and laser counts (Daniel: "no fewer"), the limiter, the red rule.
- **Receipt tier**: SwiftShader, 640×360, a virtual 60 fps clock, a fixed seed.

### 4.6 The flash limiter on the final frame

- The host's gate v2 limiter (`createLimiter(gl)`, then `run(tex, w, h, dt)`) is the last pass of every frame, on the same context. Without float targets it throws, and the page runs its safe mode, as `vj.html` does.
- Lasers v2's own area budgets stay in force:
  - fast gates: 15% of a window and 8% of the frame;
  - single onsets: 22% and 10%.
- In 3D, the engine's `_fitHit` must estimate area through the live camera. That needs a small hook in Lasers v2: an optional `opts.areaProject(seg, n) → seg2d`, which `lasers3d` supplies by projecting the 3D segments and feeding them to the existing `estimateArea()`. This is a request to the Lasers v2 lane: about five lines, with its own test.
- **Camera exclusion** [L9, L14 as look rules]:
  - any laser whose axis passes within 2° of the camera is attenuated;
  - it may cross the camera only while moving;
  - its glare disc counts in the area estimator.

### 4.7 The FrameState contract (the renderer never sees music)

```ts
interface FrameState {
  t: number; pos: number; bar: number; section: string; seed: number;
  nodes: Float32Array;    // world 3x4 matrices of every element and fixture base (kinetics + parent chain)
  heads: Float32Array;    // 16 per head: pan, tilt, dimmer, r, g, b, zoomDeg, frost, iris, gobo, goboRot,
                          //              prism, prismRot, shutter, focus, flags
  pixels: Float32Array;   // 4 per LED cell: r, g, b, a (linear HDR)
  lasers: Float32Array;   // 16 per 3D segment: origin xyz, end xyz, power rgb, width0, divergence, kind, flags
  medium: { sigma: number; g: number; wind: [number, number, number]; noiseAmp: number;
            puffs: Float32Array /* 8 per puff */; lowFog: [number, number] };
  sfx: Float32Array;      // emitters: pose, type, t since fire, params (CO2, gerb, cold spark, flame)
  camera: { pos: [number, number, number]; quat: [number, number, number, number]; hfov: number;
            ev: number; cut: boolean };
}
```

Given the same scene file, event log and seed, FrameState is deterministic. That property is what makes the hash receipts possible.

---

## 5. The camera

### 5.1 The rig

A shot has:
- a `kind`: `static`, `path`, `orbit`, `track`, `handheld`, `attached` (riding an element; for example UNDER_RUNG_ICON rolls with the rung) or `follow`;
- separate centripetal Catmull–Rom curves for position and look-at, with minimum-jerk easing [Gebhardt et al. 2018];
- an `hfov` value or curve, plus roll;
- a length in bars;
- an `arrive` constraint (`downbeat`, `phrase`, `{beat}`);
- an exposure EV;
- the sections it suits;
- handheld noise: 0.3–0.5 Hz, 0.6° yaw and pitch, 0.3° roll.

Progress along a path is driven by the beat position: u = ease((pos − pos₀)/(pos_arrive − pos₀)). A flythrough therefore arrives on the ONE whatever the tempo does.

Virtual drone limits (dream-capable): 15 m/s and 5 m/s², with C2-continuous paths.

### 5.2 Vocabulary

The shots below come from the rig lane's footage study, plus our flypaths. Positions use the rig frame.

| Shot | Source | Use |
|---|---|---|
| FOH_HOLD_ZOOM: (0, 4.5, 50), hfov 46°→34° over 4–8 bars | footage | reveals; drop downbeats |
| CROWD_POV: (±6–10, 2.1, 18–32), 55°, handheld, hand and phone silhouettes | footage | between everything |
| DETAIL_INSERT: 12°, a cube face, a laser aperture, a pixel bar, sparks | our stand-in for the footage's face inserts | punctuation, ½–1 bar |
| DJ_OTS: (1.2, 4, −7) looking out at the crowd, 85° | footage | drops |
| TRIBUNE_34: (−30, 18, 42), 40°, the look point panning down the strand | footage (ref-22) | the strand as a line and a helix |
| ROOF_ESTABLISH: (0, 30, 88), 60° | footage | section openings |
| TUNNEL_UP: (0, 1.8, 46) looking up the strand, 75° | footage (ref-19) | drops |
| WING_LOW: (−24, 3, −1), 60°, dolly | footage | ring tilts in 3D |
| PROP_FRAME: through **our own sigil** on a pole near FOH | footage, our prop | drops |
| JIB_TILTDOWN: crown to DJ in about 6 s | footage | end of a breakdown |
| STARBURST: on a fixture cluster's beam axis | footage | peaks, 1 bar |
| STRAND_FLYTHROUGH: 2.9 m/s over 16 bars, rolling with the helix, arriving inside the inner ring on the downbeat | ours | breakdown into drop |
| HELIX_CORKSCREW: 8 m radius, one turn per 4 rungs | ours | helix breakdowns |
| RING_THREAD: crossing the ring plane exactly on the ONE | ours | drops |
| HEAD_ORBIT: 26 m radius, a 120° arc at 7–15°/s | ours | ring poses |
| CRANE_RISE_REVEAL: from crowd height to 26 m over the last 4 bars of a build | ours | build |
| TOPDOWN_GODVIEW: (0, 31, 22) looking straight down, turning 10–15° per bar | ours | helix, flame finale |
| SIDE_TRACK_PARALLEL: x = −14, tracking along the strand | ours | gerb fountains |
| PULLBACK_OUTRO: 16 bars | ours | end of set |

### 5.3 The director (`director.js`)

**Choosing shots.** The section picks candidate shots by weight. A seeded deck, as in Lasers v2, keeps shots from repeating.

**Shot lengths and cuts** (from the rig lane's measured cut grammar):
- **Breakdown:** shots of 8–16 bars; dissolves at phrase ends.
- **Build:** shot length shortens 4 → 2 → 1 → ½ bar while the camera pushes in or rises, and the FOV narrows by 10–20%.
- **Drop:** a hard cut on the downbeat to the widest hero shot, held for 2 bars. After that, alternate hero, crowd, strand and detail every 1–2 bars, **never faster than every 2 beats**.
- **Pyro:** hold a wide shot for the whole burst; no cuts while fire is in frame.
- Every cut is quantized to the beat grid; the lead time is taken from the engine's look-ahead.

**Exposure matching.** The governor predicts the incoming shot's luminance per window.
- If the jump would be 0.07 or more in any window of a quarter of the screen, the director adjusts the incoming shot's EV, or defers the cut to the next bar.
- On the drop, one big jump may be granted by the FlashGate as that second's flash.

**Collisions.** The camera stays at least 1.5 m from rungs, cubes and rings, and never inside a flame cone (2 m radius, 6 m tall) during fire cues. Paths are pre-checked against the kinetic poses scheduled along them.

**Fader 8 (camera energy)** biases the shot length and the choice between cutting and gliding.

### 5.4 Manual mode

The dial and knobs work as in section 3.8. In manual mode the director still:
- quantizes takes to the beat;
- enforces collisions;
- runs exposure matching.

Back hands control to the auto director with a glide of 1 bar.

---

## 6. The first set: "Source"

Source is our own hall and our own rig, in the spirit of Qlimax 2014. There is no Q-dance logo, no star prop, and no replica of the figure or of Alex Grey's painting.

### 6.1 The hall

- A closed oval arena: floor x −38..38 and z −24..96, roof at 38 m, a roof grid of trusses at 33 m that catches beam ends.
- Stands raked at 30° on three sides.
- 18,000 people on the floor and 12,000 in the stands, as instanced silhouettes with impostors in the distance.
- An end stage at −z with a 2 m deck, 48 m wide.
- **Our own sigil** (seven points in a double ring, the house design from Ritual Fire) stands on a pole near FOH as the foreground prop.

### 6.2 The figure, "the Source" (our design)

- A seated, faceted, crystalline being about 24 m tall, bigger than the real one (about 16 m).
- Its hands are raised and cupped around a glowing core above the DJ booth in its lap. Its head is lifted.
- The forehead has an aperture that houses the **HERO laser**: the hero fires from the third eye.
- About 800 flat facets, each a pixel (`facet-skin`), with light running along the seams.
- A crown of 12 gerbs; 12 uplight washes inside the base.
- The mesh is generated procedurally from a seed (`procedural:figure-v1`). It can later be replaced by a model authored in Blender.
- The design is for Daniel to sign off (section 10).

### 6.3 The rings

- Five concentric rings, 32, 24, 17, 11 and 6 m across, centred at (0, 14, −11), behind the head. The real show had four.
- Each ring is built from radial slats at a pitch of 7.5°: 48 slats × 8 pixels, plus a lit outline on both edges.
- Each ring has its own tilt axis (left to right). The outer ring needs a lean of at least 40°.
- The ring poses:
  - **spiral**: stepped tilts, for example 55, 40, 25, 10 and 0°;
  - **sunburst**: all tilted together;
  - **halo**: the inner ring flat at eye level;
  - **chopper**: opposed tilts plus a rim chase, with spin in dream mode.
- 40 gerbs on the outer two rims.
- 8 follower lasers, at 45° steps on the outer ring.
- Kabuki opener (v2): a white curtain lit amber, with the ring pixels glowing through it, falls at the reveal.

### 6.4 The strand

- **v1 has 16 rungs** (the real show had 12) at z = 4.0 + 3.6·i, so the strand runs to 58 m.
- **Each rung**, from the centre outward:
  - a diamond frame holding an 8×8 matrix;
  - two straight segments, each carrying a 32-pixel bar;
  - two X nodes, each with a 12-dot strip;
  - two 1.1 m cubes, 9 m apart from cube to cube: the backbones.
- **Under each rung:** 8 heads (6 `beam-7r` and 2 `wash-z`).
- **On top of each rung:** 2 flames, 2 gerb mounts and a spark-waterfall line.
- **Lasers:** one follower laser per rung, a dream addition that rides the kinetics, with BEYOND's kinetic plugin as the real precedent [K5].
- **Hoists:** 2 pickups at x = ±4.3, giving height (8–22 m) and roll.
- **Formations:**
  - ceiling, wave, helix, zigzag, parallel tilt, low line, star/mandala, ladder, solo;
  - **dream only**: true continuous helix spin; corkscrew wave; bloom (rungs fan out in yaw); slide (rungs travel on trolleys); and in v2, unzip (each rung splits into two half-rungs that separate).
- **Backbone ribbons** (v2, dream only): LED dot ribbons joining cube to cube along each helix strand, with chases running along the backbones.

### 6.5 The beam rig

| Position | Heads |
|---|---|
| Three upstage overhead truss rows, 16 `beam-7r` each | 48 |
| One overhead row of `spot-hx` | 16 |
| Four side towers, 8 heads each | 32 |
| PA fingers: 6 hangs × 4 | 24 |
| Stage-lip floor row of `beam-7r`, between the lasers | 24 |
| Delay and FOH towers: 4 × 4, firing back toward the stage over the crowd | 16 |
| Under the strand rungs | 128 |
| **Total moving heads** | **288** |

The stage lip also carries 24 `strobe-a` units and 16 `blinder-2` units.

### 6.6 Lasers (53 projectors)

**The core 21 match the Lasers v2 topology one for one:**
- Bank A: 8 on the front overhead truss, y ≈ 22, z ≈ −2.
- Bank B: 8 on the stage lip at y 2.3, x = ±2.5, ±7.5, ±12.5 and ±17.5 (the real layout).
- Towers: SL1 and SL2 at (−22, 6 and 14, −2); SR1 and SR2 mirrored on the right.
- HERO: the figure's third eye.

**Followers (32):** 16 on the rungs, 8 on the ring, and 8 on the FOH towers firing back.
- In v1 a follower copies its core head's current beams in its own local frame, with no delay.
- In v2 the copies can be delayed by spread order, for example along the helix.

**The 3D mapping** (`lasers3d.js`):
- A Lasers v2 BEAM segment from head h, (x0,y0)→(x1,y1), becomes the 3D ray d = normalize(r_h·Δx + u_h·Δy + f_h·k_h·|Δ|) from the projector's position.
  - r_h, u_h and f_h are the projector's right, up and forward axes.
  - k_h is the **reach** (depth ratio), set per role and scaled by K7: Bank B 0.6 (the laser ceiling over the crowd), Bank A 0.9, towers 0.4, hero 1.0.
  - With k = 0, the front-of-house camera sees the 2D picture; k > 0 throws the beams over the crowd.
  - A ray ends where a CPU raycast against the collision proxies hits something (roof plane, walls, stands, floor and crowd plane, and the bounding volumes of the rings and figure). A dot is drawn there.
- **FIGURE segments become sheets**: triangles from the hero through each stroke. A circle becomes a cone tunnel, which is what a real scanned figure does in haze.
- **Vibrate** becomes a ringing displacement perpendicular to each beam, plus a soft band whose width is the `blur`.
- **The 2D halo is dropped.** In 3D the halo comes from haze scatter and bloom.
- **Power.** Each projector's channel power is shared among its beams in proportion to the Lasers v2 intensities, so Σ P_b ≤ P (receipt L2). The default is physical sharing (γ = 1); Daniel can choose a "show" exponent (γ = 0.5).
- **Red is never emitted** (Lasers v2 rule).

### 6.7 Atmosphere and SFX

| Unit | Count and placement |
|---|---|
| Hazers | 8: stage left and right ×2, roof ×2, FOH ×2, delay towers ×2. Pre-haze at 10–15% before doors; base haze moves over minutes, never per beat. |
| Foggers | 4 on the stage, for burst shots before drops |
| Low fog | 6 units along the deck front, for intros and breakdowns |
| CO2 | 16 jets: 8 on the deck, 8 at the ring base. At most 3 s per burst, from cylinders; pre-fired ⅛ beat early so the plume is full on the beat; plume LEDs on 1 s before and held 6 s after. |
| Flames | 40: 8 on the deck front, 32 on the strand. Armed, fuel-budgeted, with a minimum gap. |
| Gerbs | 84 mounts (32 strand, 40 rings, 12 crown), 3 shots each, one-shot inventory, armed |
| Cold sparks | 12 (deck front and the figure's hands). Preheat; at most 30 s of continuous firing. These are post-2014 technology [P3]; the 2014 sparks were gerbs, with smoke. |

### 6.8 Counts

| | Qlimax 2014 (reconstructed; counts low confidence) | Source v1 | Source XL (v2) |
|---|---|---|---|
| Moving heads | about 104 (72 strand + 12–24 PA + 8 wing) | 288 | about 600 |
| LED pixels | about 3,500 est. | about 8,900 (about 53 RGB universes at 170 pixels each) | about 20,000 |
| Strobes and blinders | about 12 | 40 | 80 |
| Laser projectors | about 11 | 53 | about 100 |
| Hazers, foggers, low fog | unknown (dense, even haze) | 18 | 24 |
| CO2 jets | about 8 | 16 | 32 |
| Flames | about 32 | 40 | 64 |
| Gerb mounts | about 61 | 84 | 160 |
| Kinetic axes | about 24 hoists + 4 ring tilts | 32 hoists + 5 tilts | two crossing strands, 64 + 10 |

### 6.9 The set arc

This follows the real shows' two-act shape: rings and lasers carry the first half, and the strand takes over after the first climax.

1. **Curtain** (v2): amber, with ring pixels glowing through.
2. **Rings and lasers:** the spiral pose, the laser lattice, the crown and the jib tilt-down.
3. **The DNA chase on the rings:** a build into drop 1, with ring gerbs.
4. **The strand as hero:** ceiling, then helix, then star cluster, with gerbs from every cube.
5. **Dream moment:** the helix spins.
6. **Fire Crown finale.**
7. **Pull-back outro.**

---

## 7. How it joins the rig

```
KeyLab + music -> vj.py engine (SSE /api/events; beat ~250 ms ahead, bar, ver, tap, energy, hits, chords, key, tension, pads, ctl)
  -> page: EngineLink -> Grid (one beat position, spec 3.2)
       -> Programmer (fixtures, pixels; themes via vj-themes) ---+
       -> Kinetics (poses) ------------------------------------+
       -> Lasers v2 engine -> lasers3d (3D projectors) --------+--> FrameState -> arena renderer (three.js r186, house GLSL)
       -> SFX + medium ----------------------------------------+        -> scene-linear HDR target
       -> Sections -> Director (camera), Governor (flash budget) +       -> Look v2 finish -> gate v2 limiter -> canvas
```

**Host 1, v0: `arena.html`.**
- Its own canvas and WebGL2 context.
- The same imports as `vj.html`: `vj-core.js` (EngineLink, BeatClock, parseEvent, FlashGate, control maps, DemoScript), `vj-lasers.js`, `vj-themes.js`, `vj-gate.js` and `vj-limiter.js`, `modlib.js`.
- A temporary finish chain: Look v2's `post/bloom.glsl` if it has landed, otherwise written *as* that module in coordination with the Look v2 lane (one bloom in the house); then display-out, dither and the limiter.
- URL options: `?engine=` (default 8794; receipts use the test band), `?demo=1`, `?set=source`, `?quality=`.

**Host 2, v1: a set kind inside `vj.html`.**
- `renderSet()` gains a branch for `set.kind === "arena"`, about 20 lines:
  1. `arena.render(gl, …)` draws into its own RGBA16F target;
  2. `blitFramebuffer` copies the result into the set's FBO;
  3. `resetState()` runs before and after.
- The set's header declares `"output":"hdr"` and its native pads.
- What that buys:
  - Look v2, the limiter, the theme director, the HUD and the transitions apply unchanged;
  - the zoom-through transition can fly into the arena;
  - **the VJ sets become the media server**: the arena samples any set's FBO texture for the rings, the figure and the cubes, on the same context, at no copy cost;
  - **one LaserEngine for the whole page**: pad 2 drives the 2D overlay on 2D sets and the 3D projectors on the arena.

**The engine.**
- v0 needs no engine change: S1's `bar`, `ver`, `src` and the tap events are enough.
- Later, an optional section hint, as a request to the vj.py lane.
- Receipts never touch 8793 or 8794: they use a replay engine or a scripted event log on the test band.

**Themes.** Theme roles resolve through `themeLook()`. Theme changes land on bars and phrases through the ThemeDirector. The red rule comes from `isSaturatedRed()`.

---

## 8. The build plan

### Prerequisites

1. **An integration branch** holding:
   - gate v2 (worktree `wf_44df4b8b-2ce-1`: `vj-gate.js`, `vj-limiter.js`);
   - Lasers v2 (`wf_efff698b-848-1`);
   - themes (`wf_efff698b-848-2`);
   - the beat clock S1 (`wf_efff698b-848-3`).
   None of these is on master yet. The arena branches from that integration branch, **never master, never pushed**, with no attribution trailers in commits.
2. **Ports.** Claim test-band ports 8980 (the `arena_verify` static server) and 8981 (a replay engine) in `docs/PORTS.md`. Ports 8931–8934, 8941, 8947, 8961, 8962 and 8975 are already in use by other lanes.
3. **GPU receipts** run under `arsenal/lanes/gpu_lock.mjs run`: headless only, `--use-angle=swiftshader`, one instance at a time.
   - The PC was at 68.1 h of uptime when I checked; the memory-pressure window is 82–92 h. Run the SwiftShader receipts early.
   - The real-GPU bench belongs after a fresh boot, with Daniel present.
4. **three.js.** Vendor r186 (MIT, with its licence file) under `arsenal/web/lib/three-r186/`, so a show never depends on jsDelivr. The piano loads it from the CDN today (`piano.html:24`).
5. **Licence.** All code is our own. three.js is MIT. We learn from QLC+ (Apache-2.0) but write our own. Nothing from BlenderDMX (GPL), the Shadertoy corpus or the GDTF spec text is copied. Open Fixture Library data is MIT and needs attribution if we use it.
6. **House practice.** Every slice is fenced with DeepSeek and verified per `verified-done`.

### File layout

```
arsenal/web/arena.html, arena.js, arena.css     host 1
arsenal/web/arena/rig.js          scene format: validate, expand, MVR bridge            (pure)
arsenal/web/arena/grid.js         one beat position (spec 3.2), bar, phrase, ladder     (pure)
arsenal/web/arena/programmer.js   spreads, effects, presets, cues, playbacks, merge, masters, physics (pure)
arsenal/web/arena/kinetics.js     axes, elements, formations, limit filter, time priority (pure)
arsenal/web/arena/sfx.js          hazers, fog, low fog, CO2, gerbs, cold sparks, flames  (pure)
arsenal/web/arena/lasers3d.js     Lasers v2 -> 3D projectors, energy, exclusion, area projection (pure)
arsenal/web/arena/sections.js     section estimator                                     (pure)
arsenal/web/arena/director.js     shots, cut and glide grammar, manual mode             (pure)
arsenal/web/arena/governor.js     predictive flash budget (uses vj-gate.js)             (pure)
arsenal/web/arena/render/         three.js renderer; GLSL through modlib
arsenal/web/arena/sets/source-v0.json, source.json
arsenal/web/glsl/volume/beam-cone.glsl, volume/beam-line.glsl   new house modules (Apache, written fresh)
tests/arena_*.test.mjs            node --test
arsenal/lanes/arena_verify.mjs    headless receipts
```

### v0: the working slice

v0 contains:
- the hall, plus a simple crowd;
- **12 `beam-7r` heads**, one under each rung. The full parameter set is modelled; dimmer, colour, pan, tilt, zoom and shutter are rendered, while gobo, prism and frost are modelled but not drawn until v1.
- **one strand of 12 rungs** with cubes, dot strips and bars, moving in the `wave` formation (real limits);
- the **21 Lasers v2 projectors** (Bank A, Bank B, towers, hero) with followers off;
- **4 rings** in the static spiral pose with a polar chase;
- uniform haze plus noise;
- one flypath (STRAND_FLYTHROUGH, arriving on the downbeat) plus FOH_HOLD;
- pads 1 (KICK lift), 2 (LASERS), 6 (FLY-OUT) and 10 (DROP NOW);
- faders F1, F4, F5, F6 and F9.

| Slice | Content | Size | Receipt (done when) |
|---|---|---|---|
| **S0 spike** | three r186 `WebGLRenderer` on a shared context renders into an RGBA16F target; display-out plus `vj-limiter.js` run on the same context after `resetState()` | S | On SwiftShader: no GL errors; a stable pixel hash across 2 runs; the limiter's `frames()` advances; frame time at 640×360 logged. **Decides section 4.1.** |
| S1 rig | `rig.js`, `source-v0.json` | M | Schema errors caught; deterministic expansion counts (12 heads, 12 rungs, 24 cubes, dots, bars, ring pixels, 21 projectors); the MVR matrix has determinant +1 and round-trips |
| S2 grid and programmer | `grid.js`, `programmer.js` | L | The spread table matches (MA Block = ChamSys Segments = Hog Buddying, and so on) on identical offset arrays; phase is continuous through a 150→160 BPM ramp and a ×2 change on a beat line; a tap re-anchors at a beat; HTP/LTP merge cases; slew never exceeds the realFade/realAccel limits; MIB moves only at dimmer 0; unison pulses respect `floor ≥ 0.6` |
| S3 kinetics | `kinetics.js` | M | **K1**: vmax, amax and jerk are never exceeded; a time-priority formation lands within ±1 frame of its target beat at 150 BPM; the roll limit is held in real mode |
| S4 lasers3d | adapter plus the Lasers v2 `areaProject` hook (a request to that lane) | M | Seen from FOH at k = 0, the 3D beams match the Lasers v2 2D picture within a mean angle error of 3°; **L2** energy: per-beam share within 1% and the sum never above P; red never emitted; the camera-exclusion cone works |
| S5 renderer | the passes in section 4.2 except fog bodies and particles; new `beam-cone` and `beam-line` modules | L | Determinism hash: the same event log gives the same frames, twice; **L4**: beam brightness against view angle follows HG × 1/sin θ within 10% on a synthetic scene; thin-line shimmer: with the minimum-1 px ribbons, the per-pixel temporal variance on a slowly rotating fan is at least 3× lower than without; the licence-line check exits 0 |
| S6 director | flythrough plus FOH hold, cuts on the bar, manual orbit | S | Arrival on the downbeat within ±1 frame; cuts on bar lines; no cut faster than 2 beats |
| S7 page | `arena.html`: engine link, demo fallback, pad and fader subset, HUD | M | Loads with `?engine=http://127.0.0.1:8981` (replay) and `?demo=1` |
| S8 safety and beat lock | the scripted 3-minute v0 sequence (kicks, Lasers v2 pad storms, flypath and cuts) | M | **Zero final-limiter interventions**; zero red flashes; the KICK lift lands on the scheduled beat frame ±1 over 64 beats |
| S9 look | a private contact sheet of v0 against ref-19, 20, 22 and 24 (scratch only, never committed) | S | Daniel's eye |
| S10 real-GPU bench | 60 s at 1080p on the RX 6600, **with Daniel present** | S | p50 and p99 frame time and a per-pass breakdown; the budgets in section 4.5 replaced by measurements |

### v1: Source at full scale, in the rig

- **Rig:** the full Source rig from section 6 (16 rungs, 5 rings with tilt kinetics, the figure, all beam positions, 53 lasers with followers).
- **Renderer:** gobo, prism and frost; half-colour beams; world-locked aim; MIB; fog bodies; particles.
- **Atmosphere and SFX:** the shared medium with puffs; CO2, gerbs, cold sparks and flames.
- **Programming:** the governor; the full effects vocabulary; the 10 signature routines; section playbooks.
- **Camera:** the full director with section inference, the whole vocabulary and exposure matching; the full KeyLab map with manual camera.
- **Hosts:** **host 2** (the arena as a `vj.html` set, with the VJ sets as LED media and one shared LaserEngine).

Receipts:
- the lasers lane's L1 (scanner model reproduces the ILDA test pattern at 30k and 8°, and visibly fails at 15°) and L3 (ILDA format 4/5 round trip, if the relay is chosen);
- **C1**: CO2 bursts last at most 3 s, the tank is enforced, the attack takes at least 100 ms, and each shot is at most 1 flash;
- **P1**: a gerb cannot refire; a cold spark refuses to fire without preheat and stops at 30 s;
- **F1**: σ never exceeds 0.26 m⁻¹;
- **K1** at full scale;
- governor parity (r ≥ 0.9);
- **S1**: zero interventions over a scripted 3-minute Qlimax-style sequence with every effect type;
- host 2 passes the existing `vj_storm` and `vj2_verify` phases with the arena set included, plus transitions in and out of the arena and the native pads;
- the real-GPU bench at Source v1 scale.

### v2: beyond real, and HDR

- **Dream mode** in full: helix spin, trolleys and yaw, unzip, backbone ribbons, the chopper rings, delayed followers, lasers reflecting off mirror cubes.
- **The kabuki opener.**
- **Source XL** counts.
- **HDR output:** the WebGL flag route or renderer B. The limiter meters in cd/m² to BT.1702-3, with parity.
- **The medium volume** with light deposition: plumes glow where beams cross them.
- **Timeline set pieces** (endshow authoring); storing routines from the KeyLab.
- **Optional:** an MVR/GDTF importer (our own parser) and an Art-Net, sACN or IDN relay on a test-band port. Daniel's call.

Receipts:
- dream multipliers still respect S-curves and the settle;
- HDR limiter parity;
- the XL budget on the real GPU;
- a round trip of our own MVR export.

---

## 9. What I verified, corrections, and risks

**Verified myself**
- **Renderer platform:**
  - headless WebGPU is unavailable here (two probes);
  - brighter-than-white output in Chrome currently means a WebGPU extended canvas (`hdr-check.js`);
  - WebGL `drawingBufferToneMapping` appears only under the experimental flag in Chrome 155 (`probe-result.json`);
  - in r186's `three.webgpu.js`, `outputType: HalfFloatType` gives an `rgba16float` canvas with extended tone mapping, and `forceWebGL`, `getFallback`, `context`, `resetState`, `RenderPipeline` and `trackTimestamp` all exist (lines 87313, 74035, 61731, 74226, 63968, 90575).
- **Repo interfaces:**
  - Lasers v2: 21 heads, `MAX_SEGMENTS` 512, the BUDGET and FRAME_RULES, `posAt` preferred, `estimateArea` used inside `_fitHit` (`vj-lasers.js:94-110, 196-225, 759, 1116`);
  - gate v2: LIMIT values, 18 windows, the REST rule, `createLimiter(gl)` and `run()` (`vj-gate.js:53-90`, `vj-limiter.js:430-502`);
  - the engine's SSE contract and the S1 beat fields;
  - the control CCs;
  - the house GLSL functions `phaseHG`, `volTransmittance`, `glowLorentz` and `glowTwoGauss`, plus display-out and dither. **`post/bloom.glsl` does not exist yet.**
  - `vj-stage.js` name collision, hence `arena`.
- **The set, from the frames:** the twelve "DNA replicas" are rungs across the hall axis with lit cubes at both ends, X nodes, dot strips and pixel bars. They roll about the strand axis (zigzag and helix), lower into the star cluster, and fire gerbs from both cubes. This is the Noisecontrollers show at 300–419 s plus Daniel's frames. Private contact sheets are at `<scratch>/arch/daniel_sheet.jpg` and `…/arch/strand_sheet.jpg` (scratch only).
- **Arithmetic:** DMX at 44 Hz; 170 RGB pixels per universe; the laser power share (216 points, 139 Hz, 3.7% per beam); HG ratios of 14.4, 28.9 and 125; Koschmieder visibilities of 15 m, 200 m and 1,300 m; the 16 s / 10-bar move; 8 s for a 4 m winch drop.
- **Coordinates:** GDTF and MVR axes and units, from the spec copies.

**Corrections to the lanes**
- **Previz lane:** the platform verdict is overruled (section 4.1); the technique stands. Also, a 3.8° beam at 40 m is about 110 px wide at hfov 60° and 1080p, not 67 px. This does not change the 6 px rule for switching to the thin path.
- **Lighting lane:**
  - the "hexagonal truss nodes" are cubes seen corner-on, plus X nodes;
  - the "overhead rows" in ref-18 to ref-23 are the strand's own under-rung heads;
  - the MVR mapping is (x, z, −y)/1000.
- **Lasers lane:** the `INDEX.md` line about a hologram, an aerialist and a choir is attributed to Qlimax 2019. I did not re-verify this; it goes to Daniel.

**Risks**
1. The S0 spike (shared context, the WebGL2 backend's state) is the first gate.
2. Every ms figure is an estimate until the S10 bench.
3. Lasers v2 needs the `areaProject` hook.
4. The arena depends on four unmerged branches.
5. The scale of the Qlimax reconstruction is ±30%. Source is our own design, so this only affects the "real mode" comparisons.
6. The governor's prediction has to be calibrated against the renderer. The parity receipt guards it.

---

## 10. Daniel's calls

**The one question.** Should Source move like the real rig first (hoists at 0.5 m/s, rungs rolling at most ±50°, spark machines that need warming up), with dream moves (a full DNA spin, sliding rungs, spinning rings) saved as cues for the big moments? Or should it be dream-first?

My recommendation is real-first. The impossible moment lands harder after the room has felt physical, as the strand did in the second act at Qlimax.

**Defaults you can override:**
1. The KeyLab map in section 3.8 (pads, faders, dial, manual camera).
2. Laser power: physical sharing between beams (default) or the brighter "show" sharing.
3. Contrast drops: one drop in N goes dark with a single beam. Proposed N = 4, off by default.
4. HDR output: wait for Chrome, try the experimental flag with the hdr-check page on your machine, or a WebGPU renderer in v2.
5. The 60-second real-GPU bench, with you present, after a fresh boot.
6. Signing off the figure (a seated crystal being, the hero laser in its third eye) and the FOH sigil.
7. Vendoring three.js locally, so there is no CDN at showtime.
8. The `INDEX.md` hologram, aerialist and choir line (reported as 2019).

---

## Sources this design rests on

**Standards and specifications**
- S1: ANSI E1.11 DMX512-A, https://tsp.esta.org/tsp/documents/docs/E1-11.pdf
- S3: ANSI E1.31 sACN, https://tsp.esta.org/tsp/documents/docs/E1-31-2016.pdf
- S2: Art-Net 4, https://art-net.org.uk/downloads/art-net.pdf
- S4: GDTF (DIN SPEC 15800), https://github.com/mvrdevelopment/spec/blob/main/gdtf-spec.md
- S5: MVR (DIN SPEC 15801), https://github.com/mvrdevelopment/spec/blob/main/mvr-spec.md
- ITU-R BT.1702-3, https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1702-3-202311-I!!PDF-E.pdf
- WCAG 2.3.1, https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html

**Fixtures and devices**
- S6: Robe MegaPointe DMX protocol, https://cdn.stormltd.co.uk/content/2018/09/Robe_megaPointe_DMX.pdf
- S7: OFL, Clay Paky Sharpy, https://open-fixture-library.org/clay-paky/sharpy
- S8: Martin Atomic 3000 LED, https://www.martin.com/en-US/products/atomic-3000-led
- F2: MDG ATMe datasheet, https://www.christielites.com/file_uploads/Product-data-sheet_ATMOSPHERE_ATMe.pdf
- C1: MagicFX CO2 Jet manual, https://www.proscene.ch/data/web/proscene.ch/uploads/database/D00800/manual_co2_jet.pdf
- C2: CO2 Jet II specifications, https://entertainmenteffects.co.uk/special-effects-hire/co2-jet-hire/co2-jet/
- P1: Sparkular PRO manual, https://audioeffetti.com/product/documents/SPK/PRO-01.pdf
- P3: Sparkular product overview (the 2016 debut), https://sparkular-fx.com/index.php/en/product-overview/sparkular
- P4: Gerb, https://en.wikipedia.org/wiki/Gerb_(pyrotechnic)
- P5: Le Maitre, long-duration gerbs, https://lemaitreltd.com/products/pyrotechnics/prostage-ii/jets-gerbs-waterfalls/long-duration-gerbs/
- P6: OFL, MagicFX Stage Flame, https://open-fixture-library.org/magicfx/stage-flame
- P10: MagicFX Stage Flame, https://magicfx.com/products/stage-flame

**Consoles**
- grandMA3 Phasers, https://help.malighting.com/grandMA3/2.0/HTML/phaser.html
- grandMA3 MAtricks, https://help.malighting.com/grandMA3/2.0/HTML/matricks.html
- S19: grandMA3 Move In Black, https://help.malighting.com/grandMA3/2.2/HTML/cue_mib.html
- S20: grandMA3 Recipes, https://help.malighting.com/grandMA3/2.2/HTML/recipes.html
- ChamSys MagicQ FX engine, https://docs.chamsys.co.uk/magicq/1.9.9.x/manual/FX_engine.html
- Hog 4 Fanning, https://www.etcconnect.com/webdocs/controls/hog4/content/06_FixtureParameters/Fanning.htm

**Practice**
- S31: ALIA, Defqon.1 Australia busking, https://alia.com.au/defqon-1s-spectacular-10-year-anniversary/
- S32: Hardnews, the Defqon.1 endshow documentary, https://hardnews.nl/en/3voor12-documentary-reveals-the-creative-process-behind-the-defqon-1-endshow/
- Syncronorm, Qlimax 2023 interview, https://www.syncronorm.com/newsitem/qlimax-2023-interview

**Lasers**
- L1: Pangolin, scanners and the ILDA test pattern, https://pangolin.com/blogs/news/laser-scanners-the-ilda-test-pattern
- L9: Pangolin wiki, projection zones, https://wiki.pangolin.com/doku.php?id=beyond%3Aprojection_zones-new
- L11: Pangolin, Clubmax 3000 FB4, https://pangolin.com/products/clubmax-3000-fb4
- L14: Laser show safety FAQ, https://www.lasershowsafety.info/faq.html
- K5: Pangolin wiki, BEYOND Kinetic Lights plugin, https://wiki.pangolin.com/doku.php?id=beyond:kinetic_lights

**Kinetics**
- K1: Kinesys Vector manual, https://www.christielites.com/file_uploads/Vector-User-Manual.pdf
- K2: Kinesys products, https://kinesys.com/products/
- K3: CyberMotion datasheet, https://www.cybermotion-rental.us/media/CyberMotion-Specification-sheet-2017.pdf
- K4: Kinetic Lights Winch L, https://www.kinetic-lights.com/winch-l
- K11: PosiStageNet, https://www.shadowcontrols.com/posistagenet/
- K13: S-curve motion profiles, https://www.technosoftmotion.com/ESM-um-html/motion_module_scurve_profile.htm

**Rendering**
- Sun et al. 2005, https://www.cs.columbia.edu/~bosun/sig05.htm
- Macklin, https://blog.mmacklin.com/2010/06/10/faster-fog/
- Persson, phone-wire AA, https://www.geeks3d.com/20120626/phone-wire-anti-aliasing-dx10-demo/
- Golus, grid shader, https://bgolus.medium.com/the-best-darn-grid-shader-yet-727f9278b9d8
- Jimenez 2014, https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/
- Kopf et al., joint bilateral upsampling, https://johanneskopf.de/publications/jbu/
- F6: Colombi and Louedec 2013 (HG g values), https://arxiv.org/pdf/1310.1702
- F11: Koschmieder, https://en.wikipedia.org/wiki/Visibility
- Gebhardt et al. 2018 (camera-path smoothness), as cited by the rig lane
- QLC+ 3D view (Apache-2.0, learn only), https://github.com/mcallegari/qlcplus/tree/master/qmlui/qml/fixturesfunctions/3DView
- Unreal DMX, https://dev.epicgames.com/documentation/en-us/unreal-engine/dmx-mvr-import-and-export-in-unreal-engine
- Depence, https://www.syncronorm.com/products/depence2/visualization/overview

**Qlimax 2014**
- Hardstyle Mag, https://hardstylemag.com/qlimax-2014/
- Festivalling, https://festivalling.com/reports/qlimax-the-source-code-of-creation-report/
- Hard News, https://hardnews.nl/en/is-this-the-inspiration-for-the-qlimax-stage/
- The official Q-dance videos BtDJuU7_6K4, p5WyC1N2QoA and PnT0ANjjB88, and the Eventions build time-lapse rKN2g4u_RgY, viewed privately.

**Lane working files (scratch, not committed)**, all under `<scratch>/`:
- `stage/rig/rig-layout.json`, `stage/rig/camera-paths.json`, `stage/rig/NOTES.md`
- `lightwire/`, `fx/`, `previz/`, `hdr/`, `hdrcheck/`
- `arch/` (my contact sheets)
