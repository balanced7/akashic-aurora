//! {"name": "studio-object", "kind": "recipe", "cat": "F10", "family": "F", "version": "1.0.0", "order": 64,
//!  "license": "Apache-2.0",
//!  "credits": ["mrange, 'Just a Cube' (https://www.shadertoy.com/view/3XdXRr) and 'Saturday weirdness' (https://www.shadertoy.com/view/43jXWt): the analytic studio, a dark mirror read by its reflections, a floor pool (the technique, read in words; no code taken)",
//!   "tdhooper, 'Glitch Transform' (https://www.shadertoy.com/view/XtyXzW): wrapped key, half-strength shadows and five-tap occlusion on a hero object (read in words)",
//!   "Inigo Quilez, 'outdoors lighting' (https://iquilezles.org/articles/outdoorslighting/): one light per role, shadow on the key, occlusion on the fills only",
//!   "John C. Hart, 'Sphere tracing' (The Visual Computer 12, 1996, https://doi.org/10.1007/s003710050084): the march, and the closest approach as the pixel cone's coverage",
//!   "Inigo Quilez, 'fog' (https://iquilezles.org/articles/fog/): fading the floor into the backdrop so the ground has no edge",
//!   "morimea, 'Cube Lines' (https://www.shadertoy.com/view/NslGRN): a floor that dissolves into the horizon band (read in words)"],
//!  "cost": {"class": "C2", "loop": "one march of min(steps, 256) mapScene calls inside the object's box, 4 for the normal, a soft shadow of at most 48 inside the box, 5 occlusion taps; a floor pixel pays a shadow and the taps only near the box", "tex": 0, "hooks": 2},
//!  "hooks": ["float mapScene(vec3 p)", "vec3 materialAt(vec3 p, vec3 n, float id)"],
//!  "entry": "vec3 studioObject(vec3 ro, vec3 target, vec2 pixel, vec2 res, float lens, float keyTurn, float keyElevation, float boxSize, float backdrop, float fresnelFloor, float metal, float roughness, float shadowAngle, float aoReach, float poolRadius, float floorDrop, float bound, float steps, float omega, int view)",
//!  "params": [
//!   {"name": "lens", "label": "Lens", "unit": "ratio", "range": [1, 8], "default": 3.2, "step": 0.1, "group": "camera",
//!    "uniform": "u_studioObject_lens", "help": "Focal length in image heights: 3 to 6 is the telephoto product shot (flat perspective, jewel-like), 1 to 1.5 a wide, dramatic lens."},
//!   {"name": "keyTurn", "label": "Key direction", "unit": "turns", "range": [0, 1], "default": 0.85, "step": 0.01, "group": "studio",
//!    "uniform": "u_studioObject_keyTurn", "help": "Where the key soft box stands around the object, in turns from +z (toward a camera on +z); the fill stands across from it. The highlight on the object moves with it."},
//!   {"name": "keyElevation", "label": "Key height", "unit": "deg", "range": [5, 85], "default": 48, "step": 1, "group": "studio",
//!    "uniform": "u_studioObject_keyElevation", "help": "How high the key stands above the horizon. Low keys rake across the form and throw long shadows."},
//!   {"name": "boxSize", "label": "Soft-box size", "unit": "rad", "range": [0.05, 1.2], "default": 0.42, "step": 0.01, "group": "studio",
//!    "uniform": "u_studioObject_boxSize", "help": "The soft boxes' half-size as seen from the object: the size of the windows its reflections show."},
//!   {"name": "backdrop", "label": "Backdrop", "unit": "ratio", "range": [0, 1], "default": 0.3, "step": 0.01, "group": "studio",
//!    "uniform": "u_studioObject_backdrop", "help": "How bright the wall behind the object is, against the studio its reflections see: a photographer's black flag behind the subject. 1 shows the dome and horizon as reflections see them; lower keeps black black while the reflections stay bright."},
//!   {"name": "fresnelFloor", "label": "Fresnel floor", "unit": "ratio", "range": [0, 0.6], "default": 0.04, "step": 0.005, "group": "material",
//!    "uniform": "u_studioObject_fresnelFloor", "help": "How much a non-metal reflects head-on: 0.04 is glass and plastic (a dark colour then reads as a dark mirror), 0.5 makes everything polished metal, 0 reflects nothing at all."},
//!   {"name": "metal", "label": "Metal", "unit": "ratio", "range": [0, 1], "default": 0, "step": 0.01, "group": "material",
//!    "uniform": "u_studioObject_metal", "help": "0 is a coloured dielectric lit by the rig; 1 a metal coloured only by what it reflects, tinted by the host's colour."},
//!   {"name": "roughness", "label": "Roughness", "unit": "ratio", "range": [0, 1], "default": 0.15, "step": 0.01, "group": "material",
//!    "uniform": "u_studioObject_roughness", "help": "0 is a mirror polish with crisp soft-box windows; higher blurs the windows (at the same energy) toward satin."},
//!   {"name": "shadowAngle", "label": "Shadow softness", "unit": "deg", "range": [0.3, 30], "default": 6, "step": 0.1, "group": "light",
//!    "uniform": "u_studioObject_shadowAngle", "help": "The key light's angular radius: small is a crisp shadow, large a soft one whose penumbra widens away from the contact."},
//!   {"name": "aoReach", "label": "Occlusion reach", "unit": "world", "range": [0, 1.5], "default": 0.35, "step": 0.01, "group": "light",
//!    "uniform": "u_studioObject_aoReach", "help": "How far the occlusion looks for nearby surfaces, in scene units: about the size of the creases and the contact under the object."},
//!   {"name": "poolRadius", "label": "Floor pool", "unit": "world", "range": [0.2, 4], "default": 1.1, "step": 0.05, "group": "light",
//!    "uniform": "u_studioObject_poolRadius", "help": "The radius of the pool of light on the floor under the object; beyond it the floor fades into the backdrop."},
//!   {"name": "floorDrop", "label": "Floor depth", "unit": "world", "range": [0, 4], "default": 0.62, "step": 0.01, "group": "scene",
//!    "uniform": "u_studioObject_floorDrop", "help": "How far below the target the floor lies; put it just under the object's lowest point for a contact shadow."},
//!   {"name": "bound", "label": "Object bound", "unit": "world", "range": [0.1, 4], "default": 0.75, "step": 0.01, "group": "scene",
//!    "uniform": "u_studioObject_bound", "help": "Half the size of the box around the target that holds the whole object. The march, the shadow rays and the occlusion run only inside it; anything outside it is not drawn."},
//!   {"name": "steps", "label": "March steps", "unit": "count", "range": [16, 256], "default": 96, "step": 1, "group": "quality", "cost": true,
//!    "uniform": "u_studioObject_steps", "help": "The march's step budget per pixel. Too few leaves a halo of floor colour round the silhouette."},
//!   {"name": "omega", "label": "Step factor", "unit": "ratio", "range": [0.3, 1], "default": 1, "step": 0.01, "group": "quality", "cost": true,
//!    "uniform": "u_studioObject_omega", "help": "Below 1 the march takes shorter steps, for a scene whose distances overstate a little (holes, black dots on edges)."},
//!   {"name": "view", "label": "Debug view", "unit": "choice", "group": "debug", "default": 0, "uniform": "u_studioObject_view",
//!    "choices": [{"value": 0, "label": "Picture"}, {"value": 1, "label": "March steps (heat)"}, {"value": 2, "label": "Normals"},
//!                {"value": 3, "label": "Occlusion alone"}, {"value": 4, "label": "Key shadow alone"}, {"value": 5, "label": "Field slice"}],
//!    "help": "Instruments: where the march works hardest, the normals as colour, the occlusion and the shadow on their own, and a slice of mapScene through the target facing the camera."}],
//!  "contract": "The host defines float mapScene(vec3 p), a distance (an sd or sb field) of an object that fits inside the box of half-size `bound` around `target`, and vec3 materialAt(vec3 p, vec3 n, float id), a linear base colour: id 0 for the object, id 1 for the floor. studioObject(ro, target, pixel, res, ...) is linear HDR radiance (tonemap after) for the pixel of a camera at ro looking at target (camLookAt, no roll; camRay with focal = lens; pixel angle camPixelAngle(2 atan(1 / lens), res.y)), in the studio studioObjectRig(keyTurn, keyElevation, boxSize, poolRadius, floorDrop): light-env's neutral studio with the key at keyTurn turns about y from +z and keyElevation degrees up, the fill 0.51 turns round from it at 33.4 degrees. The floor is the plane y = target.y - floorDrop, shaded by studioObjectFloor (rigStudio on a satin of the floor colour, with the key and fill reaching as far as the floor pool and the key scaled by the object's soft shadow, plus the studio's warm pool times the occlusion) and faded by fogExp toward the backdrop beyond the pool radius; the backdrop is backdrop times the studio with its soft boxes and its floor pool off (studioObjectBare), so the floor still meets it at the horizon with no line. The object is found by rmSphereTrace(omega, steps clamped to 1..256) clipped to the box and the floor; its silhouette is aaConeCoverage of the march's smallest d / t, so a near miss mixes the object's shading over what is behind; its shading is studioObjectSurface: rigStudio with diffuse = colour (1 - metal), F0 = mix(fresnelFloor, colour, metal), alpha = roughness^2, the key scaled by visSoftShadow toward the key (angular radius shadowAngle degrees, 48 steps, inside the box only) and the fills and reflection by visAO(aoReach, falloff 0.85). The floor's shadow and occlusion are evaluated only where the box could reach (exactly 1 elsewhere). view 1..5 return the step heat, the normals, the occlusion, the shadow and a field slice (dbgSlice) as display values decoded to linear. Everything is finite for finite input and a calibrated field.",
//!  "note": "The product shot every hero object in the house can stand in: a near-black dome, two soft boxes the reflections show as windows, a pool of light on the floor and a floor that fades into the horizon with no edge. Write the object as mapScene with library parts (sdRoundBox, opSmin, domRigid ...) and its colours as materialAt, then call studioObject once per pixel; the reflections and the diffuse light come from the same studio, so moving the key moves the highlight. Keep base colours dim (0.02 for a glossy black, 0.5 at most for a bright paint) and let the finish's curve take the highlights. Size `bound` to the object and the march, the shadows and the occlusion stay inside it (analytic before iterative: rays that miss the box cost nothing). Hover the object a little above the floor for a soft contact shadow. Wrong looks like a halo of floor colour round the silhouette (steps run out: raise steps or tighten bound), a cut-off object (bound too small), black speckle on lit faces (a field that overstates: lower omega), a floor whose far edge shows a line against the backdrop (fog undone by the host), or a glossy black object that disappears (fresnelFloor 0).",
//!  "debug": ["steps", "normals", "ao", "shadow", "slice"],
//!  "targets": {"glsl": "300es", "needs": []}, "card": "studio-object.card",
//!  "twin": "arsenal/shaders/twins/studio_object.py", "status": "P0",
//!  "exemplars": ["3XdXRr", "43jXWt", "XtyXzW", "XdcyDM", "cs2GWD", "llK3Dy"],
//!  "learn": ["atlas 16.5", "craft secret 1", "craft secret 2", "craft secret 14", "craft secret 23", "study:3XdXRr 5.3", "study:3XdXRr 5.4", "study:XtyXzW 5.12"]}
// Apache-2.0, Akashic Aurora. Written fresh: a wiring of house parts, each credited in its own module.
//
// WHY. A product photographer never moves the kettle to make it look good; she moves the lights. This recipe is the
// studio, and the object is a guest: the host hands over a distance (mapScene) and a colour (materialAt), and the
// studio does the rest the same way every time, so every hero object in the house is lit by one rig and a change to
// the rig relights them all.

// The studio for the knobs: light-env's neutral product-shot studio with the key turned and raised, the fill across.
StudioParams studioObjectRig(float keyTurn, float keyElevation, float boxSize, float poolRadius, float floorDrop) {
    float yaw = TAU * keyTurn;
    float pitch = radians(clamp(keyElevation, 0.0, 89.0));
    vec3 keyDir = vec3(cos(pitch) * sin(yaw), sin(pitch), cos(pitch) * cos(yaw));
    float fillYaw = yaw + 0.51 * TAU;
    float fillPitch = radians(33.4);
    vec3 fillDir = vec3(cos(fillPitch) * sin(fillYaw), sin(fillPitch), cos(fillPitch) * cos(fillYaw));
    float size = clamp(boxSize, 0.05, 1.2);
    return StudioParams(keyDir, vec3(3.6, 3.3, 2.9), fillDir, vec3(0.55, 0.7, 1.0), vec2(size, 0.66 * size), 0.8,
                        vec3(0.008, 0.01, 0.016), vec3(0.07, 0.075, 0.09), vec3(0.32, 0.27, 0.22),
                        max(floorDrop, 0.0), max(poolRadius, 1e-3), 0.3);
}

// The same studio with its soft boxes and its floor pool off: the wall behind the object (the panels are for the
// reflections, and the camera sees the real floor, not the studio's stand-in for it).
StudioParams studioObjectBare(StudioParams sp) {
    StudioParams bare = sp;
    bare.keyCol = vec3(0.0);
    bare.fillCol = vec3(0.0);
    bare.floorCol = vec3(0.0);
    return bare;
}

// The object's surface: the host's colour as a dielectric or a metal, lit by the rig, the key scaled by its shadow.
vec3 studioObjectSurface(vec3 p, vec3 n, vec3 toEye, StudioParams sp, float fresnelFloor, float metal,
                         float roughness, float shadow, float ao) {
    vec3 base = max(materialAt(p, n, 0.0), vec3(0.0));
    float metalness = clamp(metal, 0.0, 1.0);
    float rough = clamp(roughness, 0.0, 1.0);
    vec3 F0 = mix(vec3(clamp(fresnelFloor, 0.0, 1.0)), base, metalness);
    LitSurface surface = LitSurface(base * (1.0 - metalness), F0, rough * rough, vec3(0.0));
    StudioParams lit = sp;
    lit.keyCol *= clamp(shadow, 0.0, 1.0);
    return rigStudio(surface, n, toEye, ao, lit);
}

// The floor at pf: a satin of the host's floor colour; the soft boxes reach it only as far as the pool, the key through
// the object's shadow, and the studio's warm spill pool is darkened by the occlusion (the contact under the object).
vec3 studioObjectFloor(vec3 pf, vec3 toEye, vec3 target, StudioParams sp, float shadow, float ao) {
    vec3 up = vec2(0.0, 1.0).xyx;                            // the floor's normal
    vec3 base = max(materialAt(pf, up, 1.0), vec3(0.0));
    float reach = litFloorPool(pf, target, sp.poolRadius, vec3(1.0)).x;
    StudioParams lit = sp;
    lit.keyCol *= clamp(shadow, 0.0, 1.0) * reach;
    lit.fillCol *= reach;
    LitSurface satin = LitSurface(base, vec3(0.04), 0.5, vec3(0.0));
    vec3 shade = rigStudio(satin, up, toEye, ao, lit);
    return shade + base * litFloorPool(pf, target, sp.poolRadius, sp.floorCol) * clamp(ao, 0.0, 1.0);
}

// The studio-object group: linear radiance for one pixel of a camera at ro looking at target.
vec3 studioObject(vec3 ro, vec3 target, vec2 pixel, vec2 res, float lens, float keyTurn, float keyElevation,
                  float boxSize, float backdrop, float fresnelFloor, float metal, float roughness, float shadowAngle, float aoReach,
                  float poolRadius, float floorDrop, float bound, float steps, float omega, int view) {
    mat3 basis = camLookAt(ro, target, 0.0);
    float focal = max(lens, 0.1);
    vec3 rd = camRay(pixel, res, basis, focal);
    float pixelAngle = camPixelAngle(2.0 * atan(1.0 / focal), res.y);
    vec3 boxHalf = vec3(max(bound, 1e-3));
    if (view == 5) {
        float halfHeight = length(target - ro) / focal;          // the frame's half height at the target's distance
        vec2 onScreen = uvCentered(pixel, res) * halfHeight;
        vec3 onSlice = target + basis[0] * onScreen.x + basis[1] * onScreen.y;
        return srgbDecode(dbgSlice(mapScene(onSlice), 0.1 * boxHalf.x));
    }
    StudioParams sp = studioObjectRig(keyTurn, keyElevation, boxSize, poolRadius, floorDrop);
    float lightAngle = radians(clamp(shadowAngle, 0.05, 60.0));
    int budget = int(clamp(steps, 1.0, 256.0));
    vec3 up = vec2(0.0, 1.0).xyx;

    // what lies behind the object: the floor (an exact plane) fading into the bare studio, or the bare studio
    vec3 behind = litStudioEnv(rd, 0.0, studioObjectBare(sp)) * clamp(backdrop, 0.0, 1.0);
    float tFloor = ixPlane(ro, rd, up, sp.floorDrop - target.y);
    float floorShadow = 1.0;
    float floorAo = 1.0;
    if (tFloor > 0.0) {
        vec3 pf = ro + rd * tFloor;
        vec2 toKey = rmClipToBox(pf, sp.keyDir, target, boxHalf, vec2(1e-3, 1e3));
        if (toKey.x <= toKey.y) {
            floorShadow = visSoftShadow(pf, sp.keyDir, toKey, lightAngle, 48);
        }
        if (sdBox(pf - target, boxHalf) < max(aoReach, 0.0)) {
            floorAo = visAO(pf, up, aoReach, 0.85);
        }
        vec3 ground = studioObjectFloor(pf, -rd, target, sp, floorShadow, floorAo);
        float pastPool = max(length(pf.xz - target.xz) - sp.poolRadius, 0.0);
        behind = fogExp(ground, behind, pastPool, 0.45 / sp.poolRadius);
    }

    // the object: a march clipped to its box and the floor, its silhouette covered by the pixel's cone
    vec2 span = rmClipToBox(ro, rd, target, boxHalf, vec2(0.0, tFloor > 0.0 ? tFloor : 1e4));
    vec4 trace = vec4(0.0, 0.0, 1e10, 0.0);
    if (span.x <= span.y) {
        trace = rmSphereTrace(ro, rd, span, pixelAngle, omega, budget);
    }
    float cover = trace.w > 0.5 ? 1.0 : aaConeCoverage(trace.z, pixelAngle);
    vec3 n = up;
    float shadow = floorShadow;
    float ao = floorAo;
    vec3 picture = behind;
    if (cover > 0.0) {
        vec3 p = ro + rd * trace.x;
        n = nrmTetra(p, nrmEps(trace.x, pixelAngle, 1.0));
        vec3 lifted = p + n * (4.0 * rmEpsilon(trace.x, pixelAngle, 1e-4));    // off its own surface
        vec2 toKey = rmClipToBox(lifted, sp.keyDir, target, boxHalf, vec2(1e-3, 1e3));
        float objectShadow = toKey.x <= toKey.y ? visSoftShadow(lifted, sp.keyDir, toKey, lightAngle, 48) : 1.0;
        float objectAo = visAO(p, n, aoReach, 0.85);
        vec3 surface = studioObjectSurface(p, n, -rd, sp, fresnelFloor, metal, roughness, objectShadow, objectAo);
        picture = mix(behind, surface, cover);
        shadow = mix(floorShadow, objectShadow, cover);
        ao = mix(floorAo, objectAo, cover);
    }
    if (view == 1) {
        return srgbDecode(dbgHeatCount(trace.y, float(budget)));
    }
    if (view == 2) {
        return srgbDecode((0.5 + 0.5 * n) * cover);
    }
    if (view == 3) {
        return srgbDecode(vec3(clamp(ao, 0.0, 1.0)));
    }
    if (view == 4) {
        return srgbDecode(vec3(clamp(shadow, 0.0, 1.0)));
    }
    return picture;
}
