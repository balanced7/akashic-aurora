//! {"name": "core-const", "kind": "const", "cat": "A1", "family": "A", "version": "1.0.0", "order": 10,
//!  "license": "Apache-2.0", "credits": [],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "PI, TAU, PHI and SQRT3, each written to twenty-four decimal places so the compiler rounds it to the nearest float32 (the twin holds those exact values); defined once, for every module in the library.",
//!  "note": "One reference voltage for the whole board: a module that names TAU depends on this module, and the composer brings it along, so no module carries its own slightly different copy. Use TAU for whole turns (angle = TAU * turns) and PI for half turns. PHI is the golden ratio (PHI * PHI = PHI + 1), the most irrational step there is, which is why golden-angle spirals never line up into spokes. SQRT3 is the height of an equilateral triangle per unit side, times two: the hexagon and triangle lattices are built on it. Wrong looks like a circle whose dashes do not meet at the seam, or a golden spiral whose last squares leave a gap.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-const.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": [], "learn": ["GP 5"]}
// Apache-2.0, Akashic Aurora. Written fresh: these are the numbers themselves.
//
// WHY. Every surface draws circles, spirals and lattices, and each used to carry its own PI, some to five digits and
// some to twelve. Defined once here, the composer resolves them like any other dependency: a module that uses TAU
// anywhere (not only in a call) is given this module first.

// Half a turn, in radians.
const float PI = 3.141592653589793238462643;

// The square root of three: an equilateral triangle of side 1 stands SQRT3 / 2 tall.
const float SQRT3 = 1.732050807568877293527446;

// A whole turn: 2 PI radians. An angle in turns becomes radians as TAU * turns.
const float TAU = 6.283185307179586476925287;

// The golden ratio, (1 + sqrt 5) / 2. PHI * PHI = PHI + 1 and 1 / PHI = PHI - 1.
const float PHI = 1.618033988749894848204586;
