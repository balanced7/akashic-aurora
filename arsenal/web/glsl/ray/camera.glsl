//! {"name": "ray-camera", "kind": "helper", "cat": "E2", "family": "E", "version": "1.0.0", "order": 20,
//!  "license": "Apache-2.0",
//!  "credits": ["Jamie Wong, 'Ray marching and signed distance functions' (https://jamie-wong.com/2016/07/15/ray-marching-signed-distance-functions/): the look-at camera built from a forward direction and an up hint",
//!   "Benjamin Keinert et al., 'Enhanced sphere tracing' (STAG 2014, https://doi.org/10.2312/stag.20141233): the pixel as a cone, its radius growing with distance",
//!   "Wikipedia, 'Frenet-Serret formulas' (https://en.wikipedia.org/wiki/Frenet%E2%80%93Serret_formulas): a path's acceleration points into the turn, so an up vector leaned along it banks",
//!   "Wikipedia, 'Distortion (optics)' (https://en.wikipedia.org/wiki/Distortion_(optics)): the radial 1 + k r^2 lens model"],
//!  "cost": {"class": "C0", "loop": "none", "tex": 0},
//!  "contract": "Right-handed, y up; a camera looks down its own -z. A basis is a mat3 whose columns are the camera's right, up and back (-forward) in the world. camLookAt aims from ro at target; roll turns the camera counter-clockwise about its view direction by roll radians (right' = cos right + sin up), so the picture's horizon tilts clockwise; looking straight up or down (|forward.y| > 0.999) it swaps its up hint for +z. camRay returns the unit world ray through a pixel (fragCoord is gl_FragCoord.xy, the pixel centre) for an image plane spanning -1 to 1 vertically at distance focal: the vertical field of view is 2 atan(1 / focal). camPixelAngle(fovY, heightPx) = 2 tan(fovY / 2) / heightPx, the angle one pixel spans at the centre (2 / (heightPx * focal) for camRay's frame): the footprint at distance t is t times it. camOrbit returns a position radius from target: with the mouse untouched (mouse01 = 0, Shadertoy's iMouse before a click) it turns by autoYaw radians at 0.3 radians above the horizon, otherwise mouse x sweeps a whole turn and mouse y tilts from -1.4 to 1.4 radians. camOrthoRay moves ro (in: the camera's position; out: this pixel's origin) by p * scale across the image plane and returns the shared forward direction. pathLissajous3 is amp * sin(freq t) per axis, or amp * t on an axis whose freq is 0 (the flight axis), with its exact velocity and acceleration. camBanked is a basis facing along vel whose up hint (0, 1, 0) is leaned by bankGain * acc, so it banks into turns; with no acceleration it is level. camBarrel scales screen coordinates by 1 + k |p|^2: k > 0 bulges like curved glass when the result is used to look an image up, k < 0 pinches.",
//!  "note": "Everything in a 3D shader is measured from the camera, so measure it once. The pixel angle is the most important number here: every hit epsilon, normal epsilon and level of detail is t times it, and a shader that hard-codes 0.001 instead sparkles in the distance and blobs up close. A long lens (focal 3 to 6) is the telephoto jewel look; a short one (1 to 1.5) the speed of a tunnel. Give an orbit an auto-yaw so a thumbnail rendered before anyone clicks shows a pose, not iMouse zero. Fly a camera along an analytic path with exact derivatives (pathLissajous3, then camBanked): finite differences of a path jitter the view. Wrong looks like a mirrored world (a left-handed basis), stretched circles (a ray not normalised, or x divided by the width), a camera that snaps when it passes overhead (the up hint switching), or a horizon that rolls the wrong way.",
//!  "targets": {"glsl": "300es", "needs": []}, "card": "ray-camera.card", "twin": "arsenal/shaders/twins/ray.py",
//!  "status": "P0",
//!  "exemplars": ["WdB3Dw", "tsScDG", "XsjXRm", "MfjyWK", "ttScDc", "XtyXzW", "WlVyRV", "XsSGDh", "llVXRd", "XdcyDM", "cs2GWD", "7cjGRR", "XtS3DD", "ldSfWV", "NlK3Wt"],
//!  "learn": ["SR 5.1", "study:cs2GWD 6.9", "study:MfjyWK 6.4", "CP 7.2"]}
// Apache-2.0, Akashic Aurora. Written fresh from the geometry and the public sources credited above.
//
// WHY. A pinhole camera is three lines of maths, and every 3D shader retypes them with its own sign conventions. Written
// once: a right-handed basis whose -z looks at the subject, a ray through each pixel's centre, and the angle one pixel
// spans, which every distance-dependent epsilon in the ray modules is measured against.

// The basis of a camera at ro looking at target, rolled counter-clockwise by roll radians about the view direction.
mat3 camLookAt(vec3 ro, vec3 target, float roll) {
    vec2 zeroOne = vec2(0.0, 1.0);                      // the axes by swizzle: .yxx is x, .xyx is y, .xxy is z
    vec3 ahead = safeNormalize(target - ro, -zeroOne.xxy);
    vec3 upHint = abs(ahead.y) > 0.999 ? zeroOne.xxy : zeroOne.xyx;
    vec3 rightward = safeNormalize(cross(ahead, upHint), zeroOne.yxx);
    vec3 upward = cross(rightward, ahead);
    float cosRoll = cos(roll);
    float sinRoll = sin(roll);
    return mat3(cosRoll * rightward + sinRoll * upward, cosRoll * upward - sinRoll * rightward, -ahead);
}

// The unit world ray through the pixel at fragCoord: the house 2D frame (y from -1 to 1) on an image plane focal units
// in front of the eye.
vec3 camRay(vec2 fragCoord, vec2 res, mat3 basis, float focal) {
    vec2 screen = uvCentered(fragCoord, res);
    vec3 throughPixel = basis * vec3(screen, -focal);
    return normalize(throughPixel);
}

// The angle one pixel spans at the centre of the image, for a vertical field of view fovY over heightPx pixels.
float camPixelAngle(float fovY, float heightPx) {
    return 2.0 * tan(0.5 * fovY) / heightPx;
}

// A position radius from target. Untouched (mouse01 = 0), it turns by autoYaw (pass an angle, say 0.2 * time) at a
// pleasing height; once clicked, the mouse alone decides.
vec3 camOrbit(vec2 mouse01, float autoYaw, float radius, vec3 target) {
    bool untouched = dot(mouse01, mouse01) < 1e-10;
    float yaw = untouched ? autoYaw : (mouse01.x - 0.5) * TAU;
    float pitch = untouched ? 0.3 : (mouse01.y - 0.5) * 2.8;
    vec3 around = vec3(cos(pitch) * sin(yaw), sin(pitch), cos(pitch) * cos(yaw));
    return target + radius * around;
}

// An orthographic ray: every pixel looks the same way, from a point moved across the image plane, so things keep their
// size at any distance (the product-shot look). ro comes in as the camera's position and leaves as this pixel's origin.
vec3 camOrthoRay(vec2 p, mat3 basis, float scale, inout vec3 ro) {
    ro += basis * vec3(p * scale, 0.0);
    return -basis[2];
}

// A flight path: each axis swings amp * sin(freq * t), except an axis whose freq is 0, which flies straight at amp
// units per second. Velocity and acceleration are its exact derivatives.
vec3 pathLissajous3(float t, vec3 amp, vec3 freq, out vec3 vel, out vec3 acc) {
    vec3 flies = vec3(lessThanEqual(abs(freq), vec3(1e-6)));
    vec3 phase = freq * t;
    vec3 swing = sin(phase);
    vel = mix(amp * freq * cos(phase), amp, flies);
    acc = mix(-amp * freq * freq * swing, vec3(0.0), flies);
    return mix(amp * swing, amp * t, flies);
}

// A camera basis that faces along vel and banks into turns: the up hint is leaned along the acceleration, which points
// to the inside of the curve.
mat3 camBanked(vec3 vel, vec3 acc, float bankGain) {
    vec2 zeroOne = vec2(0.0, 1.0);
    vec3 ahead = safeNormalize(vel, -zeroOne.xxy);
    vec3 leaning = zeroOne.xyx + bankGain * acc;
    vec3 rightward = safeNormalize(cross(ahead, leaning), zeroOne.yxx);
    vec3 upward = cross(rightward, ahead);
    return mat3(rightward, upward, -ahead);
}

// Radial lens distortion of screen coordinates: the centre stays, a point r from it moves to r (1 + k r^2).
vec2 camBarrel(vec2 p, float k) {
    float radiusSq = dot(p, p);
    return p * (1.0 + k * radiusSq);
}
