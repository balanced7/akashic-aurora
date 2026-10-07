# Flow primitives

A small, renderer-independent visual fluid toolkit. Original implementation informed
by [Bridson and Muller-Fischer's SIGGRAPH 2007 notes](https://www.cs.ubc.ca/~rbridson/fluidsimulation/fluids_notes.pdf)
and [GPU Gems 3, chapter 30](https://developer.nvidia.com/gpugems/gpugems3/part-v-physics-simulation/chapter-30-real-time-simulation-and-rendering-3d-fluids).
No Three.js imports, DOM, global timers, dependencies, or car materials in these primitives.

## Pieces

- `DistanceVolume`: transferable Float32 signed-distance grid, trilinear sampling,
  surface normals and projection to a chosen clearance. `fromFunction` voxelizes an
  analytic shape and computes a separable Euclidean distance transform. `serialize`
  returns plain metadata and a typed array, suitable for structured cloning/transfer.
- `bakeColumnHull`: triangle-soup adapter for exterior objects. It rasterizes top and
  bottom vertical intersections and seals the column between them. This retains the
  curved roof/bonnet outline but bridges stacked surfaces, cabins and overhangs. It is
  **not** a general watertight mesh voxelizer. Use a different SDF adapter for caves,
  tunnels, thin open surfaces or detailed wheel-well flow.
- `FluidGrid`: a 3D staggered MAC velocity grid, semi-Lagrangian velocity transport,
  optional acceleration callback, and diagonally preconditioned conjugate-gradient
  pressure projection. Six-neighbour solid-face constraints forbid normal flow into
  obstacles. Fixed horizontal flow is prescribed on outer faces; top/bottom normal
  flow is zero. Keep solid objects away from side/inlet/outlet boundaries. The same
  boundary convention should not be blindly reused for a closed room or free surface.
- `oscillatingWake`: configurable local force. Strength zero is no force. It adds
  artistic stirring; it is not an aerodynamic turbulence model.
- `fanSeeds`, `traceStreamlines`: configurable emitter frame or explicit xyz seeds,
  midpoint/RK2 tracing, arc-length resampling, SDF clearance, and sampled speed in the
  fourth component. The default stopping plane is downstream X. These are instantaneous
  streamlines, **not particle history/pathlines**. A renderer may animate illumination
  along them independently of the field's time.

## Minimal reuse (no car or renderer)

```js
import {FluidGrid} from './fluid-grid.mjs';
import {DistanceVolume} from './distance-volume.mjs';
import {traceStreamlines} from './streamlines.mjs';

const sphere = (x, y, z) => Math.hypot(x, y - 1, z) - 0.7;
const body = DistanceVolume.fromFunction({
  nx: 48, ny: 40, nz: 40, h: 0.06, origin: [-1.4, -0.1, -1.2]
}, sphere);
const air = new FluidGrid({
  nx: 32, ny: 16, nz: 24, h: 0.2, origin: [-3, 0, -2.4],
  distance: sphere, wind: [1, 0, 0]
});
air.project(180); // Initial body deflection, before transporting the field.
air.step(0.05, {iterations: 90});
const windAtLeaf = air.velocity(-1, 1.2, 0); // Scene units per simulated second.
const {paths} = traceStreamlines(air, body, {
  seeds: [[-2.6, 1.4, 0], [-2.6, 0.6, 0.5]],
  segments: 160, end: 2.9, clearance: 0.09
});
console.log(windAtLeaf, paths, air.diagnostics());
```

For a leaf, spark or game entity, use `velocity(x,y,z,out)` as input to its own
integration/drag response. Body movement requires rebuilding the static solid mask in
this first backend. Mass, lift, drag coefficients, moving-boundary coupling, acoustic
propagation, and free-surface liquids are not implemented. The pressure array `q` is a
pressure **impulse** (`pressure * dt / density`), not a calibrated pressure in pascals.

## Numerical and scheduling contract

All axes use one cell spacing `h`; Y is up. Step duration must be finite, positive,
and at most 0.1 seconds. Semi-Lagrangian transport is dissipative. Pressure iterations
are capped; diagnostics expose the residual and actual remaining divergence rather
than claiming exact incompressibility. Static geometry and Float32 numerical error
limit physical fidelity. Sub-grid SDF projection is a tracer rendering safeguard; it
does not increase the fluid solver's boundary resolution or validate aerodynamic loads.

The Violet tunnel uses an 88 x 28 x 48 grid at 0.14 scene units, a finer 0.045-unit
surface volume, and a 0.065-second simulation step. Its worker runs as fast as its
bounded jobs permit, with a minimum yield between jobs. Simulation time is therefore
distinct from wall time. Rendering remains independent and interpolates successive
streamline snapshots over 0.45 seconds. Interpolated snapshots are a presentation
approximation, not an integration trajectory. Display speed colours use the latest
snapshot. Lighting colour/intensity are artistic mappings, not measurement units.

The scene-specific worker and browser lifecycle adapter are in
`../../piano/wind-tunnel-worker.mjs` and `../../piano/wind-tunnel.mjs`. They own mesh
conversion, emitter placement, wake location, message revisions, visibility/pause and
disposal. Older revisions cannot replace current requested settings. A pause command
is serviced after the current bounded worker job, while the renderer freezes immediately.
Explicit control changes while paused can publish one new still frame.

Run `node --test tests/fluid_primitives.test.mjs tests/wind_flow.test.mjs` from the repo
root. Tests exercise a sphere, wedge and block, uniform flow including sample borders,
projection residuals, zero solid-face velocity, finite stepping, and tracer clearance.
The browser still needs inspection: these tests cannot certify visual quality or fps.

## Record once, animate in 3D

The tunnel's **Flow recordings** panel captures 8, 16 or 24 seconds of active motion.
Each fresh solver publication records its instantaneous streamline XYZ/speed samples
and the full staggered U/V/W/pressure-impulse field. Pausing the view pauses capture
time. Completed takes are automatically saved under unique IDs in this browser's
IndexedDB library; **Save file** exports a portable `.flowclip`, and **Load file**
imports one. A `?take=…` link refers to that origin's local library, not a hosted file.
If browser storage fails, the current take remains playable and exportable.

Replay stops the solver and interpolates the two bracketing path snapshots on the
GPU. The camera, light treatment, paint and illumination speed remain editable.
The timeline also redraws while paused. **Forward once** preserves recorded active
timing and stops at the end; **Back & forth** eases through the recording and reverses
it for a continuous artistic animation. It is not a seamless forward simulation loop.
Field samples and streamline morphs are temporally interpolated approximations.

`flow-clip.mjs` has no renderer, DOM or browser-storage dependency:

```js
import {FlowClip} from './flow-clip.mjs';

const clip = new FlowClip(arrayBuffer); // Validates before use.
const {a, b, alpha} = clip.bracket(seconds);
const previous = clip.decodeFrame(a, 'paths'); // xyzw, w = sampled speed
const next = clip.decodeFrame(b, 'paths');
const [u, v, w, pressureImpulse] = clip.sampleField(seconds, x, y, z);
// Use velocity as input to a leaf, particle, cloth or other effect's own dynamics.
```

The versioned binary format uses `FLOWCLP1`, a JSON metadata header, and 16-bit
per-channel quantization with stored global bounds. It preserves actual irregular
capture timestamps, solver timestamps, grid convention, scene settings, camera and
illumination phase. Field layout is interleaved U/V/W/Q at every storage index; the
sampler respects the MAC face offsets and cell-centred Q convention. Samples beyond
the volume clamp to its edge. These fields are not aerodynamic load measurements,
and the file does not contain a complete solver restart state or embedded car asset.

Imports validate an integrity checksum, finite values, layout, bounded dimensions,
timestamps and exact payload length, with a 128 MiB limit. The checksum detects
damage; it is not authentication. Encoding runs in a worker. Playback decodes only
the current path pair and can sample quantized fields directly without decoding a
whole volume. The scene adapter additionally checks model/layout compatibility.

Run `node --test tests/flow_clip.test.mjs tests/fluid_primitives.test.mjs tests/wind_flow.test.mjs`
for quantization error bounds, round trips, nonuniform time interpolation, staggered
field sampling, invalid data, playback endpoints and the existing solver checks.
