//! {"name": "input-mouse", "kind": "helper", "cat": "L1", "family": "L", "version": "1.0.0", "order": 15,
//!  "license": "Apache-2.0",
//!  "credits": ["Shadertoy's iMouse convention (https://www.shadertoy.com/howto), as the house runtime builds it (arsenal/web/shaderlab/toy-runtime.js, mouseUniform): signs carry the button"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Read a Shadertoy-style mouse vec4 (xy the pointer in pixels; zw where the last click landed, z > 0 while the button is held and w > 0 on the one frame of the click): mouseUntouched is true only for (0, 0, 0, 0), mouseHeld for z > 0, mouseJustClicked for w > 0, mouseDragOrigin is |zw|, the last click in pixels ((0, 0) before any). A click that lands exactly on pixel (0, 0) reads as untouched; nothing else does.",
//!  "note": "The demo pose lives behind mouseUntouched: start-up, thumbnails and every headless render see an untouched mouse, so a shader that orbits with the mouse should show its designed angle there instead of the corner case of a mouse at pixel (0, 0). A drag is mouseHeld plus the distance from mouseDragOrigin; a one-shot action (a ripple, a reseed) wants mouseJustClicked, which is true for exactly one frame. Wrong looks like a thumbnail stuck looking at the floor (no untouched pose), or an action that repeats every frame while the button is down (held used where clicked was meant).",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "input-mouse.card",
//!  "twin": "arsenal/shaders/twins/finish.py", "status": "P0",
//!  "exemplars": ["XtyXzW", "WlVyRV", "XsSGDh", "Ms2XWc", "wsl3WB", "4slGWM"], "learn": ["GP 12"]}
// Apache-2.0, Akashic Aurora. Written fresh from the published convention.
//
// WHY. The mouse arrives as four numbers that pack a whole state machine into their signs, like status bits folded
// into a register. Naming the states once means no shader re-derives them, and the state nobody tests (never touched,
// which is every thumbnail) gets a name of its own.

// Never touched since the page started: show the designed pose.
bool mouseUntouched(vec4 mouse) {
    return all(equal(mouse, vec4(0.0)));
}

// The button is down right now (a drag is in progress).
bool mouseHeld(vec4 mouse) {
    return mouse.z > 0.0;
}

// This is the one frame on which the button went down.
bool mouseJustClicked(vec4 mouse) {
    return mouse.w > 0.0;
}

// Where the last click landed, in pixels; (0, 0) before any click.
vec2 mouseDragOrigin(vec4 mouse) {
    return abs(mouse.zw);
}
