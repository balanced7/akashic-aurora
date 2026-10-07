# Violet Aero

Open `/piano-wind.html` on the studies server (currently http://127.0.0.1:8799).
A standalone prototype of violet light flowing around a concept supercar.

The separate `/piano-wind-tunnel.html` evolves this into a small 3D fluid study.
It shares the car, studio and light renderer while retaining the original page's
kinematic path mode. The reusable solver, distance volume, forces and tracing API
are documented in [the flow primitives](../lib/flow/README.md). Its worker owns
simulation time; the page renders interpolated instantaneous streamlines and
supports wind direction and air-speed colouring. This is a visual prototype,
not a validated aerodynamic predictor. Verification: `logs/wind-tunnel-20260921`.

## Model

Car Concept from the Khronos glTF Sample Assets collection. Model and textures by
Eric Chadwick / Darmstadt Graphics Group GmbH, 2024, CC BY 4.0. It derives from
Unity Fan's CC0 concept car. Full source links, modification notice, SHA-256 and
the upstream notices are in `../assets/car-concept/ATTRIBUTION.md`.
The 11,778,688-byte GLB is kept locally and unchanged. The Three.js 0.186.0 modules
are loaded from jsDelivr. A model failure surfaces an error rather than a placeholder car.

The runtime points the actual headlights toward negative X, normalizes the model
to 4.8 scene units in length, grounds its tires, and groups static geometry by
material/attribute layout. This model resolves to 23 grouped meshes and 162,766
source vertices. Paint and glass shading are adapted for the studio, with no
transmission render pass; model geometry and textures retain their source detail.

## Flow

Transformed mesh vertices produce 97 conservative height/width cross sections.
A maximum filter followed by smoothing makes a padded envelope. Stream seeds use
an angular fan in the YZ plane and pass outside that envelope with adjustable
clearance. Their X coordinate always advances from front to rear. The curl starts
downstream of the car; small GPU flutter is also restricted to the wake. This is
an authored kinematic visualization, not a CFD solver or a pressure/drag predictor.

Silk uses camera-facing ribbons with soft edges. Spark heads sample the same paths
from a float texture, with age-shaped tails; all streams travel downstream.
Trail length controls the length of illuminated history. The ends flicker and
dissolve into the dark. Mesh buffers are allocated once for up to 108 streams;
only clearance, wake and density changes rewrite the path buffers. Other controls
change shader uniforms, visibility or materials. No full-screen bloom pass.

## Controls and state

Violet silk, Ion storm and Afterglow are starting looks. Speed, trail length,
surface clearance, wake curl, stream count, light style and paint are adjustable.
Portrait, Profile, Above and The wake offer fixed viewpoints; drag to orbit, scroll
to zoom, or enable slow camera orbit. Pause cancels animation scheduling and permits
single redraws for deliberate changes. Hidden tabs stop their loop; reduced-motion
preference starts paused.

Settings and resolution are validated in the URL. Copy this look's link preserves
those controls and paint, but not camera/phase/pause state. It does not read or write
Gyre's browser preset library. Native uses CSS size times device-pixel ratio; 4K fit
preserves aspect in a 3840 x 2160 envelope. Measure 10s measures delivered RAF
intervals after one second of warmup, not GPU execution or physical monitor scanout.
Control/camera/resize/visibility changes cancel an in-progress measurement.

## Verification

`node --test tests/wind_flow.test.mjs` checks envelope coverage, clearance across
all densities at both clearance limits, forward/finite/bounded paths, wake isolation
and URL-value validation. Live DOM diagnostic attributes on the canvas expose model
counts, resource counts and a sampled minimum envelope gap. They do not establish
physical aerodynamic validity. Browser observations and measured limits are in
`logs/wind-study-20260921/results.md` at the repository root.

Follow [the visual quality baseline](../../VISUAL-QUALITY-BASELINE.md) for further work.
