# The house GLSL library

One folder of GLSL modules that every visual surface composes from: the piano pages, First Light, the VFX bench, the
shader lab. Change a module here and every surface that uses it changes with it, which is what Daniel asked for on
2026-10-13: "tweak one module and have everything update".

The machinery lives in `arsenal/shaders/modules.py` (Python) and `modlib.js` (the browser twin, held byte-identical by
`tests/test_glsl_modules.py`). The door is `py -m arsenal shader lib list|show|compose|lint|manifests`.

## A module

A `.glsl` file in `arsenal/web/glsl/<category>/`. Its leading `//!` lines are one JSON header:

```glsl
//! {"name": "smin-poly", "kind": "helper", "cat": "sdf-ops", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Inigo Quilez, 'smooth minimum' (iquilezles.org/articles/smin): the technique"],
//!  "cost": "O(1)",
//!  "note": "Blends two distances with a rounded seam of width k. Use it wherever two shapes should read as one material."}
float sminPoly(float a, float b, float k) { ... }
```

| field | meaning |
|---|---|
| `name` | unique across the library and the bench chunks (`design/vfx-chunks/`) |
| `kind` | `helper` (functions and consts: composable) or `recipe` (a composite of helpers with UI-facing params); bench snippet kinds (`source`, `modifier`, `domain`, `blend`, `mask`) live in `design/vfx-chunks/` |
| `cat` | the category (see below) |
| `order` | tie-break when two modules have no dependency between them (lower first); helpers 10-30, recipes 50+ |
| `license` | `Apache-2.0` for house code. Nothing from the private Shadertoy corpus is ever copied here |
| `credits` | who taught the technique, with a link; `[]` only for genuinely original work |
| `cost` | the cost class: `O(1)`, `per-octave`, `per-step`, `per-sample`, with the loop counts that set it |
| `note` | the craft note: when to reach for it and what it looks like when it is wrong |
| `needs` | optional: modules or functions needed that the code does not call by name (e.g. a shared const) |
| `params` | recipes only: `[{name, unit, range:[lo,hi], default, uniform}]`; each becomes a UI control on every surface. The uniform is named `u_<recipeCamel>_<param>` (`u_auroraBand_hemHeight`, `u_neonLine_widthPx`), so two recipes on one page never collide |
| `hooks` | optional: the prototypes of functions the module calls and its host must define (see Hooks below) |
| `in` / `out` | optional typed ports (`vec3`, `float`, ...) when the module can sit in a bench chain |

Dependencies are read from the code: a module that calls a function another module defines depends on it. You never
list a dependency twice.

## Hooks

A hook is a function a module calls but does not define, because only the host knows it: the scene a marcher walks
(`float mapScene(vec3 p)`), the density a volume march reads (`float densityAt(vec3 p)`), a surface's colour
(`vec3 materialAt(vec3 p, vec3 n, float id)`). The module lists the prototype in its header's `hooks`, and the composer
writes each prototype once, ahead of the code that calls it.

**A host that composes a module declaring a hook defines that hook, even if it never calls the function that uses it;
a stub is fine** (`float mapScene(vec3 p) { return 1e9; }`, `float densityAt(vec3 p) { return 0.0; }`). WebGL refuses
to link a program in which a defined function calls an undefined one, and a module is composed whole: a sky that only
wants `rmJitterStart` from `ray/march.glsl` still carries `rmSphereTrace`, which calls `mapScene`. A recipe that composes
such a module repeats the obligation in its own `hooks`, so its host sees it in one place (aurora-sheets lists both
`mapScene` and `densityAt`, and its card defines the stubs). The composer does not prune unreachable functions: that,
or splitting the hook-free helpers into their own modules, is a later ruling (Vandor, 2026-10-13).

## Conventions (so modules compose without surprises)

- **Fragments, not programs.** No `#version`, no `precision`, no `main`. The host template owns line 1 and declares
  `precision highp float;` (`mediump` bands our hashes; shader-craft floor 8). `py -m arsenal shader lib lint` checks.
- **Pure functions.** Helpers take everything they need as arguments and touch no globals. Only recipes declare
  uniforms, and every uniform is a declared param, so the UI and every host can bind it.
- **The frame.** 2D work takes `p` centred and aspect-true with y up: `(2.0*fragCoord - res.xy) / res.y`, the bench's
  frame. 3D work is right-handed with y up; a camera looks down its own -z.
- **Names** follow the field's common tongue so a reader who learned from Inigo Quilez or the Book of Shaders feels at
  home: `sdBox`, `sdSphere`, `sminPoly`, `hash33`, `noiseValue3`, `fbm3`, `palette`. `hashNM` maps N input dimensions to
  M outputs.
- **Analytic before iterative.** A closed-form intersection or an analytic derivative beats a loop that approximates
  it. Loops have constant bounds; the bound is in the header's `cost`.
- **Derivatives only of continuous values** (`fwidth` of a cell id shreds rows; shader-craft floor 6). Static per-pixel
  jitter breaks banding; per-frame jitter is crawling grain.
- **Colour.** Work in linear light, tonemap once at the end, encode to the display last.
