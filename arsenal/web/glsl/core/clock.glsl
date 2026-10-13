//! {"name": "core-clock", "kind": "helper", "cat": "A3", "family": "A", "version": "1.0.0", "order": 14,
//!  "license": "Apache-2.0",
//!  "credits": ["Ryan Geiss, 'MilkDrop preset authoring' (https://www.geisswerks.com/milkdrop/milkdrop_preset_authoring.html): the feedback-with-decay model whose per-frame decay clkKeep turns into a per-second one"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "clkPhase(t, hz) is fract(hz * t) in cycles, in [0, 1) for t and hz >= 0, and only as fine as t itself: the host keeps t small by wrapping it (a float clock after one day of uptime is 8 ms coarse). clkKeep(keepPerSecond, dt) is the per-frame factor that keeps keepPerSecond of a value each second at any frame rate: 1 when dt <= 0, 0 when keepPerSecond <= 0. clkAlpha(dt, tau) is the blend weight 1 - exp(-dt / tau) of a one-pole smoother with time constant tau seconds: 0 when dt <= 0, 1 when tau <= 0.",
//!  "note": "83 of the 103 multipass shaders in the corpus decay per frame, so on this 240 Hz display they fade four times faster than their authors saw at 60 Hz. Say every rate per second and let these turn it into this frame's factor: clkKeep for a fade (Oscillo Donut's phosphor, 0.85 per frame at 60 Hz, is a keep of 0.85^60 per second), clkAlpha for a smoother chasing a target. clkAlpha is an RC low-pass: tau is the resistor times the capacitor, and after tau seconds the output has covered 63 percent of a step. In an 8-bit buffer a per-frame factor close to 1 stalls (0.98 sticks near 10 percent grey): use a float target or subtract a small floor. Wrong looks like trails whose length changes with the monitor, or motion that stutters after the page has been open for days (the phase computed from a huge t).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "core-clock.card", "twin": "arsenal/shaders/twins/core.py",
//!  "status": "P0", "exemplars": ["WlVyRV", "ldSfWV", "ttScDc"], "learn": ["GP 5.5", "GP 5.7", "WS 2.2", "WS 3.1"]}
// Apache-2.0, Akashic Aurora. Written fresh from the mathematics (the house research GP 5.5 and 5.7, WS 2.2 and 3.1).
//
// WHY. A frame is not a unit of time. The same shader runs at 60, 144 and 240 frames a second on the screens in this
// house, and anything that integrates per frame (a trail that fades, a value that eases toward a target) changes its
// look with the monitor unless its rate is stated per second and converted each frame.

// The phase of a hz-cycles-per-second oscillation at time t, in cycles: 0 at the start of a cycle, approaching 1 at
// its end. t should be wrapped by the host; the float spacing of t sets how finely the phase can move.
float clkPhase(float tWrapped, float hz) {
    float cycles = hz * tWrapped;
    return fract(cycles);
}

// The factor to multiply by this frame so that keepPerSecond of the value survives each second, whatever the frame
// rate: keepPerSecond ^ dt. With no time passed nothing fades; with nothing kept everything goes.
float clkKeep(float keepPerSecond, float dt) {
    if (dt <= 0.0) {
        return 1.0;
    }
    if (keepPerSecond <= 0.0) {
        return 0.0;
    }
    return pow(keepPerSecond, dt);
}

// How far a one-pole smoother moves toward its target this frame: value = mix(value, target, clkAlpha(dt, tau)).
// tau is in seconds; a tau of zero (or less) snaps straight to the target.
float clkAlpha(float dt, float tau) {
    float elapsed = max(dt, 0.0);
    float timeConstant = max(tau, 1e-9);
    return 1.0 - exp(-elapsed / timeConstant);
}
