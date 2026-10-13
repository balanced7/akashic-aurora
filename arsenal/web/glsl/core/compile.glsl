//! {"name": "core-compile", "kind": "helper", "cat": "A2", "family": "A", "version": "1.0.0", "order": 12,
//!  "license": "Apache-2.0",
//!  "credits": ["Fabrice Neyret, 'Avoiding compiler crash or endless compilation' (https://shadertoyunofficial.wordpress.com/2017/11/19/avoiding-compiler-crash-or-endless-compilation/): the unroll barrier, a bound the compiler cannot prove constant"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "unrollBarrier(n, frame) is n + min(frame, 0): exactly n whenever frame >= 0 (pass iFrame or the host's frame counter, which never goes negative), and a value the compiler cannot know in advance, so a loop bounded by it stays a loop instead of being copied out n times.",
//!  "note": "Compile time is a cost on this host. ANGLE turns WebGL into Direct3D, and its compiler loves to unroll: a 64-step march that calls an 8-octave noise becomes 512 copies of the noise body, which has been measured at seven seconds of frozen browser on the first frame. Bound the big loops with unrollBarrier(steps, iFrame) and keep each body small. Leave short loops (4 to 8 trips over a tiny body) alone: unrolling those is a win. Wrong looks like a page that hangs on first draw, a 'too many registers' compile error, or a loop that runs a different number of times than asked (a negative frame).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-compile.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": ["tsScDG"], "learn": ["GP 4.3", "GP 8.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the article credited above.
//
// WHY. A GPU has no call stack, so every function is pasted inline, and a loop with a constant bound is usually pasted
// out once per trip as well. Nested loops multiply the paste. This one line is the switch that says "leave it as a
// loop", and the house wants it in one place with its reason, not as a magic min(iFrame, 0) scattered through files.

// n at run time; unknowable at compile time. frame is the host's frame number, which is never negative.
int unrollBarrier(int n, int frame) {
    int neverBelowZero = min(frame, 0);
    return n + neverBelowZero;
}
