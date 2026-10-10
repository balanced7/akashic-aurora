// Crystal Grand — arsenal/web/piano/instruments/glass-piano.js  (ES module, a piano instrument, no imports)
//
// A cast-acrylic grand built around the host's 88-key span. The case (rim, lid, legs, lyre, key blocks, keybed, key slip,
// fallboard, music desk) is clear MeshPhysicalMaterial transmission; the action inside is opaque and visible through it:
// a gold plate with a hammer gap, a spruce soundboard, 229 strings, 88 hammers, 68 dampers, tuning pins, three pedals.
//
// Proportions: Kawai CR-40A class (L 1850 x W 1500 x H 1000 mm, spec.md section 2 GLASS PIANO), key tops 715 mm above the
// floor. Host units: 1 unit = one white-key pitch = 23.57 mm (52 whites = 1225.7 mm), key tops at y = 0, white fronts at
// z = +3.1, key backs at z = -3.1.
//
// Reactive (everything decays; nothing glows at rest):
//  - hammers: a struck key throws its hammer up to the string (faster the harder), it rebounds to check height while the
//    key is held and falls back on release. The felt tip flashes the note colour, v^2 peak over the bloom threshold,
//    exp(-age / 0.28 s), with a faint held floor under the threshold.
//  - strings: the struck note's strings take its colour AND start vibrating, and both last exactly as long as the page
//    says the sound does (state.sounding): a flash, a prompt decay, a pitch-dependent aftersound, then a velocity-scaled
//    floor held for the whole note, finger or pedal, and a 0.30 s damping fade at its end. The vibration is drawn as a
//    translucent long-exposure blur (Dune's ornithopter wings), wide and slow in the bass, a fine shimmer at the top.
//    They are screen-space ribbons in the OPAQUE list under CustomBlending, so they survive the transmission pass.
//    Tuning table below, under "the string light envelope and the vibration blur".
//  - dampers: lift while their key is held or the sustain pedal is down; the right pedal dips with the pedal.
//  - case: clear cast acrylic (white base, a faint cool attenuation over 400 mm, 15 mm walls, 25 mm legs and lyre). A
//    cool-white fresnel edge (in crystal, no environment map) outlines the silhouettes; strikes tint only the sharpest
//    edges toward the notes' colours, capped under the bloom threshold, so the body never fills with colour. The other
//    glass looks (options.glass, below) change how the case is drawn, never the action inside it.
//  - music desk: the chord name (state.chord.name, our own text) is etched in the chord's colour, flares on a change.
//
// Integration notes for the host: the instrument brings its own keybed, key blocks and key slip, so the host's lacquer
// stage body should hide while it is mounted (hints.hideStageBody). The legs reach a floor 715 mm below the key tops
// (hints.floorY = -30.33); the host floor at y = -2.3 would cut them. Nothing in front of z = -3.55 rises above the key
// tops, so the host's trails (emitted at z = -3.42) are never hidden by the glass.
// Options (ctx.options or setOptions): lid "auto" (off on the page, long prop in the lab's hero view) | "long" |
// "short" | "closed" | "off" (a portrait framing never raises it past "short"); desk true | false; edge 0..2 (fresnel edge
// strength, default 1; it scales every look's edge light); glass, one of these (handle.optionsSpec lists them in this
// order for the Studio menu; an unknown value mounts crystal; the numbers are in GLASS_LOOKS and the blocks above it):
//   "crystal"     clear acrylic, a cool fresnel edge, no reflections: the original look, unchanged
//   "studio"      Studio crystal: the same acrylic lit like a product photograph, with a reflection map of its own;
//                 42 mm legs (STUDIO)
//   "lens"        Lensing edges: a stylised thick-crystal edge; silhouettes bend hard and take a faint aqua tint (LENS)
//   "prism"       Prism: cut crystal, ior 1.60, dispersion 1.5, 19 mm walls and 15 mm panes, the host studio's lines
//                 along the cuts (PRISM)
//   "satin"       Satin: sandblasted faces; polished bevels, rods and key blocks; the panes over the action stay clear
//                 windows, the music desk's top edge frosted in (SATIN)
//   "smoked"      Smoked glass: grey-violet, a wall passes about 51 % of what is behind it and the panes over the action
//                 about 74 %, mirrors a studio of its own (SMOKE)
//   "lightguide"  Light guide: edge-lit acrylic; each note's colour pools under its key and runs along the bevels (LG)
//   "fast"        plain alpha blend, no transmission pass
// studio, prism, satin, smoked and the light guide draw the leg glass DoubleSide with only the three legs keeping their
// far faces, so the tail leg shows standing on its brass caster through the key slip (crystal, lens and fast do not;
// see "Glass behind glass" above GLASS_LOOKS).

const MM = 1225.7 / 52;
const DEG = Math.PI / 180;
const KEY_STYLE = Object.freeze({ whiteColor: 0xe8e4db, blackColor: 0x0b0c10, capHeight: null, frontLip: 0.28 });
const HINTS = Object.freeze({ hideStageBody: true, floorY: -715 / MM });

const G = Object.freeze({
  halfW: 31.82, rimTh: 1.3, rimBottom: -3.2, rimTop: 11.5, front: -3.6,
  blockInner: 26.12, blockFront: 3.85, bedTop: -0.85, bedBottom: -2.3,
  strY: 2.4, bassStrY: 2.9, agraffeZ: -9.4, strikeZ: -12.3, shank: 5.2, pivotY: -0.99, restTop: 0.4,
  damperZ: -15.6, plateY0: 1.3, plateY1: 1.9, gap0: -9.6, gap1: -16.8, boardY: -1.6,
  lidTh: 0.55, lidFrontZ: -8.8, floorY: -715 / MM,
});
const LID_ANGLE = { long: 38, short: 10, closed: 0, off: 0 };
const GLOW = { peak: 5.0, tau: 0.28, held: 0.3 };
// ---- the string light envelope and the vibration blur ----
// Daniel, 2026-09-17: "the color decay doesn't fully match the sustain of the length of the note ... the decay should be
// slower and have a higher floor", and "notes that are lower could have more of a blur and vibration similar to the wings
// in the helicopters from the movie Dune". The same model as the concert grand's, tuned the same way, so the two
// instruments answer a held pedal identically; only the gains differ, because the crystal's strings sit on gold and are
// NOT its bloom source (the hammer felt is, GLOW.peak above — the strings stay under the 0.9 luminance line at fff).
//
//   name             what it is                                                       value
//   PEAK_EXP         body height at the strike = v^PEAK_EXP  (v = vel/127)            1.35
//   FLASH_EXP        the strike transient's height = v^FLASH_EXP                      2.0
//   TAU_FLASH        the transient's decay                                            0.09 s
//   FLOOR_LO/HI      the floor the body settles on, as a share of the strike body     0.33 at vel 1 -> 0.50 at vel 127
//                    (42 % at vel 64, 46 % at vel 96), held for the WHOLE sound
//   AFTER_SHARE      how much of the above-floor body is in the slow aftersound       0.55
//   TAU_PROMPT       the prompt decay, a real string's first fast loss                1.00 s at A0 -> 0.45 s at C8
//   TAU_AFTER        the aftersound: bass rings for seconds, treble does not          7.0 s at A0 -> 1.2 s at C8
//                    (at C4: prompt 0.70 s, aftersound 3.2 s)                         geometric in pitch
//   TAU_DAMP         the damper landing, when the sound ENDS: the fall's time constant 0.16 s
//   DAMP_FADE        and the window that closes that fall to exactly 0, so the light   0.30 s
//                    never outlives the sound. Level at the release x1, +0.05 s 0.68,
//                    +0.1 s 0.41, +0.15 s 0.21, +0.2 s 0.09, +0.25 s 0.03, +0.3 s 0.
//                    A fade, not a snap: the steepest 60 fps step is 11 % of the level
//                    at the release, and the window lands with zero slope.
//   TAU_VIB_OFF      the blur dies faster than the light: the damper stops the string 0.07 s
//   STR_BODY/FLASH   string colour = base + noteColor * (body * 1.10 + flash * 0.45)  (1.10 is the old STR.peak, so a
//                    strike is as bright as it ever was; at fff the pair reach 0.85 luminance, under the 0.9 bloom line)
//   AMP_BASS/TREBLE  swing half-amplitude at full body, world units, geometric in     0.38 -> 0.038 units
//                    pitch (0.135 at C4). On screen at 16:9 Ultra: about 8.5 framing   (the same numbers the concert
//                    px at A0, 3.4 at C4, 1 at C7. Measured perpendicular px/unit at   grand uses — the two cameras put
//                    the string band: 22.3 / 22.8 / 25.3 / 28.3 (A0/A1/C4/C7).         a unit within 15 % of each other)
//   AMP_EXP          amplitude = AMP(pitch) * body^AMP_EXP: it narrows as the note settles, and never stops while it sounds
//   VIB_HZ           the blur envelope's visual breathing rate, never the real pitch  3.1 Hz (bass) -> 9.5 Hz (top)
//   VIB_WOBBLE       a slow drift of the blur's centre, as a share of its width, so it reads as alive and not as a bar
//   VIB_DETUNE       the unison strings' rates differ by this much, so they beat against each other as real unisons do
//   BLUR_CONSERVE    how much of the string's light is spread rather than added as it widens (1 = conserved exactly,
//                    0 = same peak at any width). 0.45 keeps a wide blur luminous and every pixel of it dimmer than the
//                    string at rest, which is what keeps the bloom out of it.
//   STRING_MIN_PX    the ribbon's half-width floor in drawing-buffer pixels, under the string's own STRING_W/2
// The old string model, kept only as the record of what it was: peak 1.1 now lives in STR_BODY_GAIN, and the two decays
// (0.35 s dry, 1.8 s wet) are what Daniel's "the colour decay doesn't match the sustain" was about.
const PEAK_EXP = 1.35, FLASH_EXP = 2;
const FLOOR_LO = 0.33, FLOOR_HI = 0.50;
const AFTER_SHARE = 0.55;
const TAU_PROMPT_BASS = 1.00, TAU_PROMPT_TREBLE = 0.45;
const TAU_AFTER_BASS = 7.0, TAU_AFTER_TREBLE = 1.2;
const TAU_FLASH = 0.09, TAU_DAMP = 0.16, DAMP_FADE = 0.30, TAU_VIB_OFF = 0.07;
const STR_BODY_GAIN = 1.10, STR_FLASH_GAIN = 0.45;
const AMP_BASS = 0.38, AMP_TREBLE = 0.038, AMP_EXP = 0.8;
const VIB_HZ_BASS = 3.1, VIB_HZ_TREBLE = 9.5, VIB_WOBBLE = 0.22, VIB_DETUNE = 0.06;
const BLUR_DENS_CAP = 3.0, BLUR_DENS_NORM = 0.69, BLUR_CONSERVE = 0.45, STRING_MIN_PX = 0.55;
const pitchOf = (m) => (m - 21) / 87;                    // 0 at A0, 1 at C8
const overPitch = (m, lo, hi) => lo * Math.pow(hi / lo, pitchOf(m));
// Clear cast acrylic. Judge 2026-09-15: the old body read purple, because a broad fresnel term carried the chord's strike
// tint across whole faces. Now the base is white, the attenuation a faint cool grey over 400 mm, and the walls 15 mm
// (25 mm in the legs and lyre).
const GLASS = { color: 0xffffff, roughness: 0.03, ior: 1.49, thickness: 15 / MM, legThickness: 25 / MM,
  attenuationColor: 0xdfe6ef, attenuationDistance: 400 / MM, fastColor: 0xdfe6ef, fastOpacity: 0.16 };
// The edge is cool white at 0.12 and tight (pow 5.5), so it outlines silhouettes. The strike tint rides pow 10 and is
// capped at luminance 0.09 and at 0.15 per channel. Render 2026-09-15 q2: under a luma-only cap a blue/violet chord
// kept about 1.0 in blue, since blue carries only 0.07 of the luma weight, and at pow 7 that filled the grazing lid
// underside navy.
const EDGE = { color: 0xcfe0ff, gain: 0.12, pow: 5.5, strikePow: 10.0, strikeGain: 0.05, tau: 1.1, maxLuma: 0.09, maxChannel: 0.15 };
const f4 = (x) => x.toFixed(4);   // a number written into GLSL

// ---- the glass looks (options.glass) ----
// Daniel, 2026-10-09: "Can we make the glass look more like glass and try a few different shaders? i didn't realize that
// was the foot of the grand" (the tail leg's brass caster, seen through the clear key slip). Every look keeps the same
// rules, because three r186 enforces them silently when they are broken:
//  - transmission > 0 with transparent false. Three's transmission pass draws the background and the OPAQUE list into
//    what the glass refracts; a transparent glass would drop out of the others' view. Only "fast" alpha-blends.
//  - one program per look, keyed "glass-piano-<shader>" (crystal and fast share "glass-piano-crystal", as always).
//  - every compile installs EVERY look's uniforms. Three keeps the uniforms object of a material's LAST compile, and a
//    program taken back from its cache runs on that object (WebGLRenderer.getProgram, WebGLUniforms.seqWithValue), so a
//    look-only uniform would go missing after a round trip through another look.
//  - each look is a COMPLETE record (GLASS_LOOKS), so a switch never leaves a field of the last look behind, and crystal
//    and fast are exactly what they always were.
//  - nothing glows at rest and no face fills with note colour. The bloom line (0.94 under spectacle, 0.9 on the page) is
//    on LINEAR luminance: the composer's RenderPass draws with NoToneMapping into a render target (WebGLPrograms), and
//    OutputPass tone-maps afterwards.
// Glass behind glass: the pass above holds no glass at all, so in crystal the tail leg is invisible through the key slip
// and keybed, and in the 9:16 follow view its brass caster shows alone under the key slip (Daniel took it for a pedal).
// legSide "double" (studio, prism, satin, smoked, light guide) draws the leg glass DoubleSide: r186
// renderTransmissionPass then draws the BACK faces of a DoubleSide transmissive object into that pass (WebGLRenderer.js
// near line 2091: the material flipped to BackSide and back; skipped where the browser exposes
// WEBGL_multisampled_render_to_texture, three issue 28131), so the far half of the tail leg shows above its caster
// through the key slip. Round 2 drew every part of the leg draw that way; from the 9:16 camera the left lyre post's far
// faces crossed the caster and lensed a second, smaller one below it, a lit key hung under the slip at the right post,
// and in the lab close a gold sliver showed. Round 3 keeps the far faces of the three legs only (NEAR_ONLY, below), and
// a far face refracts a quarter of the leg's path (LEG_FAR_PATH), so the tail leg reads as a column standing on its
// caster, not as a tile of the key colour above it. The column shows when the follow camera holds the caster low in the
// key slip; when it holds it high, under the keys, the leg rises behind the opaque keys and no look can show it.
// Receipts beside NEAR_ONLY. Cost: +0.7 ms at Cinema (round 1's measurement, not re-timed); the two flips mark the leg
// material for an update every frame. Not crystal (its pixels are the reference), not lens (left as round 1 built it),
// and not fast: it alpha-blends, so a second face would double its veil.

// "studio" (Studio crystal): the same acrylic, lit the way a product photograph lights a clear grand. The host's studio
// puts its four strips where this case almost never mirrors them from the 22-degree follow camera (the desk mirrors
// +9..+15 deg toward the player, the key slip and fallboard -18..-25, a column -22..-30), so studio carries a map of its
// own (acrylicStudio, below). What it mirrors is soft-kneed (max channel 0.40, easing to at most 0.70) and the clearcoat
// is off. The music desk mirrors at half the walls' intensity (3), and the softbox it mirrors peaks at rgb(110,110,114)
// and ends at 17 deg, so its sheen sits on the desk's top edge instead of a grey card over the bass strings (the desk
// box at 9:16 Cinema, mean sRGB levels against crystal: round 1 +34 %, round 2 +4 % (+6 % in linear light)). The legs
// are 42 mm columns (round 1's 60 mm read as dashed hairlines): roughness 0.12,
// so a strip on the turned legs and lyre is a soft stripe rather than a crawling sub-pixel line (it also blurs the
// view through them by about 1.5 px at Cinema), and a faint inner density, attenuation over 150 mm (a leg passes 0.92,
// 0.94, 0.96). Clearcoat 0 also drops the coat's second specular lobe (key-light glints about 0.63x crystal's near
// normal incidence, about equal at grazing) and the coat's (1 - 0.6 Fcc) dimming of everything under it, emissive
// included: edgeMul leaves the cool edge at about 0.77x crystal's on screen, and strikeMul keeps the note tint where
// crystal has it (that factor, averaged over the strike's pow-10 lobe, is 0.58). The knee is GLSL constants, never
// uniforms. legThickness also thickens the lyre posts and braces (20-25 mm and 10 mm across): judge by
// eye. Cost: no pass; per glass fragment one IBL radiance and one irradiance fetch and the knee, minus the clearcoat lobe
// (6.19 vs 6.16-6.18 ms a frame at Cinema 9:16 on the RX 9070 XT); once, a canvas paint and a PMREM bake (6 MB).
const STUDIO = { envMapIntensity: 6, deskEnvMapIntensity: 3, clearcoat: 0, legThickness: 42 / MM, legRoughness: 0.12,
  legAttenuationDistance: 150 / MM, edgeMul: 0.5, strikeMul: 0.6 };
// The cool strip behind maps onto the 0.45 rim round-over as a sub-pixel line; if it crawls under the moving follow
// camera, dim it to "rgb(110,122,160)" (more canvas blur cannot widen a line the geometry makes sub-pixel, and more
// roughness would also blur the view through the glass). Round 2 leaves it: only a motion capture can say it crawls.
const STUDIO_HORIZON = "rgb(176,196,255)";
const STUDIO_KNEE = `{ // studio: a soft knee on the mirrored environment
  const float K0 = 0.40, K1 = 0.70;
  float sl = max3( reflectedLight.indirectSpecular );
  if ( sl > K0 ) reflectedLight.indirectSpecular *= ( K0 + ( K1 - K0 ) * ( 1.0 - exp( - ( sl - K0 ) / ( K1 - K0 ) ) ) ) / sl;
}
#include <aomap_fragment>`;

// "lens" (Lensing edges): a stylised thick-crystal look. Face-on the walls stay as clear as crystal; toward every
// silhouette the transmission ray is lengthened by up to LENS.addMM, so rounds, rods and side walls bend what is behind
// them, and the longer path deepens a faint aqua Beer-Lambert tint. (A real flat 15 mm wall displaces the image by at
// most about 12 mm even at 80 deg, and three already gives about 9 mm there: this exaggerates the edges on purpose.)
// Added path = addMM * (1 - |n.v|)^pow, the SAME millimetres on walls and legs, additive and not a multiplier: x(1 + 4
// shape) on the 25 mm legs reached 125 mm and pulled the brass pedals into the pedal-box top.
//   walls 15 mm: x1.00 at 20 deg, x1.11 at 40, x1.71 at 60, x2.40 at 70, x3.48 at 80, x4.66 at 88
//   legs  25 mm: x1.00 at 20 deg, x1.06 at 40, x1.42 at 60, x1.84 at 70, x2.49 at 80, x3.20 at 88
// Beer transmittance (R, G, B): wall face-on (0.975, 0.994, 0.989), at the silhouette (0.881, 0.969, 0.945); crystal's
// face-on wall (0.989, 0.991, 0.995). The edge line and the strike tint move into the transmission chunk (lensHook), so
// lens draws no second edge. Cost: no pass; refraction fetches unchanged (8), about 15 ALU, the host map's 3 cube lookups.
const LENS = {
  addMM: 60,                       // extra path at a true silhouette, mm. 45 subtle .. 90 strong; above ~90 the front-object
                                   // ghosts (the plate brackets on the spine's top round) detach into notches
  pow: 2.5,                        // 2 = a broader ramp, 3 = only the last ~20 deg
  blur: 0.06,                      // extra transmission roughness at the silhouette (about +0.6 mip): soft, no shimmer
  pipe: 2.0,                       // the edge line's Beer path = 2 x the lensed thickness
  attenuationColor: 0xbdeddf,      // sRGB; linear (0.507, 0.844, 0.737) over 400 mm
  attenuationDistance: 400 / MM,
  edgeGain: 0.10,                  // white edge line x the Beer tint: luminance 0.090 at a wall silhouette (crystal's 0.089)
  envIntensity: 0.15,              // the host map. 0.20 stacks to ~0.97 linear at grazing with the strike and what shows
                                   // through (a static line over the bloom line); 0.15 is ~0.77. 0 = pure lensing
};
const LENS_DECL = "uniform vec3 uLensEdge;\nuniform float uEdgePow;\nuniform vec3 uStrike;\nuniform float uStrikePow;\n" +
  "uniform float uLensAdd;\nuniform float uLensPow;\nuniform float uLensBlur;\nuniform float uLensPipe;\n";
const LENS_ANCHOR = "vec4 transmitted = getIBLVolumeRefraction(";
// Inserted into r186 transmission_fragment just before its getIBLVolumeRefraction( call, where material.thickness,
// .attenuationColor and .attenuationDistance are set and pos, v, n exist. That call turns material.thickness into BOTH the
// refraction offset (normalize(refract(-v, n, 1/ior)) * thickness * modelScale) and the Beer path; material.roughness there
// sets only the transmission mip and the (1 - F) term, and nothing after the chunk reads it. totalEmissiveRadiance is read
// only afterwards (outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance), so moving the edge here is exact.
const LENS_GLSL = `
	// glass-piano lens: the transmission ray lengthens toward the silhouette
	float lensFr = 1.0 - clamp( abs( dot( n, v ) ), 0.0, 1.0 );
	float lensShape = pow( lensFr, uLensPow );
	material.thickness += uLensAdd * lensShape;
	material.roughness = min( material.roughness + uLensBlur * lensShape, 1.0 );
	{
		// the edge line, tinted by the same Beer law over pipe x the lensed path
		float lensPath = material.thickness * length( modelMatrix[ 0 ].xyz ) * uLensPipe;
		vec3 lensT = exp( log( max( material.attenuationColor, vec3( 1e-4 ) ) ) * ( lensPath / material.attenuationDistance ) );
		totalEmissiveRadiance += uLensEdge * lensT * pow( lensFr, uEdgePow ) + uStrike * pow( lensFr, uStrikePow );
	}
`;

// "prism": heavy flint, cut crystal. ior 1.60 (F0 0.053, acrylic's 1.49 gives 0.039); dispersion 1.5, so r186 refracts
// r/g/b at ior -/+ (ior - 1) * 0.025 * dispersion = 1.578 / 1.600 / 1.623, about 2x real flint: on curves and
// silhouettes only, and about a fifth of round 1's fringe (dispersion 4 at 30.6 mm put 3-4 px rainbows on the dampers
// and moire on the tuning pins in the lab close). The rim walls are 19 mm. The panes over the action (key slip,
// fallboard, desk rest, music desk) refract as crystal does: 15 mm, ior 1.49, no dispersion (round 2 gave them prism's
// ior and dispersion, and the key slip blew the brass caster's highlight up into a warm-white blob on its lower edge,
// 5.6x crystal's pixels over 200 sRGB levels, right where Daniel misread the caster), so the hammers behind the
// fallboard move as crystal's do (round 1's 30.6 mm at ior 1.70 moved them 0.21 units and doubled the harmony pearls in
// front of the rim); they keep flint's F0. The legs, lyre and pedal box 45 mm. Clearcoat 0, one surface; the host studio
// at 0.35, 1.8x and in colour along the cuts and 0.3x and neutral on the flat faces (round 1's 0.6 and round 2's 0.35
// laid the host's warm strip on the 16:9 treble wall as a tan card, +39 and +18 sRGB levels over its neighbour; round 3
// +4). The shader finds the cuts from screen derivatives (bend per world unit, so the
// mask is the same at Studio and Cinema): the round-overs and bevels carry a faint cool line (cut gain 0.25) and brighter
// strips, and the chord tint goes on the silhouettes and the SHARP bevels only (radius 0.25 or less), never the rim-top
// round-over band. Every reflection is soft-kneed against the pixel's own headroom, so it never pushes a pixel past 0.86.
// Without clearcoat the silhouette edge is up to 2.5x crystal's at the extreme rim (still under bloom). Geometry
// roughness makes the bevels softer at Studio than at Cinema: judge them at Cinema. Cost: no pass; dispersion takes 3
// refraction rays (24 fetches instead of 8: the define is on for any dispersion above 0), the host map 2-4 more, 4
// derivatives; unmeasured, about 3.5x the glass texture traffic. Measure Cinema 9:16 on the RX 9070 XT before offering it.
const PRISM = { ior: 1.60, dispersion: 1.5, thickness: 19 / MM, paneThickness: GLASS.thickness, legThickness: 45 / MM,
  envMapIntensity: 0.35, cut: 0.25, flatEnv: 0.3, cutEnv: 1.8 };
// The panes take crystal's thickness, ior and no dispersion in the transmission chunk (the walls and panes are one
// material, one draw). three fills material.ior and .dispersion in lights_physical_fragment, and this chunk hands them
// to getIBLVolumeRefraction, so only the refraction through the panes changes: their reflection keeps flint's F0.
const PRISM_TX_THICKNESS = `material.thickness = thickness * mix( 1.0, ${f4(PRISM.paneThickness / PRISM.thickness)}, glassWindow() );
	material.ior = mix( material.ior, ${f4(GLASS.ior)}, glassWindow() );
	material.dispersion *= 1.0 - glassWindow();`;
// Appended after three's transmission chunk, which takes the place of the single "#include <transmission_fragment>":
// there totalDiffuse holds the refracted, dispersed scene, totalSpecular = direct + indirect specular, and outgoingLight
// is summed on the next line.
// In scope: normal, nonPerturbedNormal, geometryViewDir, reflectedLight, vViewPosition, pow4, saturate, and luminance()
// (WebGLProgram's fragment prefix, the same weights the bloom high-pass uses).
const PRISM_GLSL = `
{
	float gpFr = 1.0 - saturate( abs( dot( normal, geometryViewDir ) ) );
	// bend per world unit (about 1/radius): 0 on flat faces, 2.2 on the 0.45 round-overs, 5-10 on the 0.1-0.2 slab
	// bevels, under 0.8 on the turned legs; faded where a bevel is narrower than about 2 px, so distant cuts do not shimmer
	vec3 gpDpx = dFdx( vViewPosition ), gpDpy = dFdy( vViewPosition );
	float gpCurv = max( length( dFdx( nonPerturbedNormal ) ) / max( length( gpDpx ), 1e-6 ),
	                    length( dFdy( nonPerturbedNormal ) ) / max( length( gpDpy ), 1e-6 ) );
	float gpPx = max( length( gpDpx ), length( gpDpy ) );
	float gpWide = smoothstep( 1.0, 3.0, 1.5708 / max( gpCurv * gpPx, 1e-6 ) );
	float gpCut = smoothstep( 1.0, 3.5, gpCurv ) * gpWide;
	float gpBevel = smoothstep( 3.5, 6.0, gpCurv ) * gpWide;
	// silhouette and cut lines: tighter and fainter when the studio draws the outline, pow 5.5 without an env map
	#ifdef USE_ENVMAP
		totalEmissiveRadiance += uEdge * ( 0.5 * pow( gpFr, 8.0 ) + ${f4(PRISM.cut)} * gpCut );
	#else
		totalEmissiveRadiance += uEdge * ( pow( gpFr, uEdgePow ) + ${f4(PRISM.cut)} * gpCut );
	#endif
	totalEmissiveRadiance += uStrike * max( pow( gpFr, uStrikePow ), 0.35 * gpBevel );
	// studio strips 1.8x and in colour along the cuts, 0.3x and neutral on the flat faces; a faint coating-like hue shift
	// at grazing only (RGB mean kept, luminance +-13 %)
	vec3 gpEnv = reflectedLight.indirectSpecular * ( ${f4(PRISM.flatEnv)} + ${f4(PRISM.cutEnv - PRISM.flatEnv)} * gpCut );
	gpEnv = mix( vec3( luminance( gpEnv ) ), gpEnv, gpCut );
	vec3 gpFilm = 1.0 + 0.22 * cos( 6.2831853 * ( 0.72 - 2.22 * gpFr + vec3( 0.0, 0.3333, 0.6667 ) ) );
	gpEnv *= mix( vec3( 1.0 ), gpFilm, pow4( gpFr ) );
	// soft knee against the headroom of this pixel: the reflection never pushes it past 0.86; a pixel already over that
	// keeps its own light and loses its reflection; over a dark interior this is the knee 0.55 easing to 0.80
	float gpRoom = clamp( 0.86 - luminance( totalDiffuse + reflectedLight.directSpecular + totalEmissiveRadiance ), 0.0, 0.80 );
	float gpK = 0.6875 * gpRoom;
	float gpL = luminance( gpEnv );
	float gpX = gpL - gpK;
	gpEnv *= gpX > 0.0 ? ( gpK + gpX / ( 1.0 + gpX / max( gpRoom - gpK, 1e-4 ) ) ) / max( gpL, 1e-4 ) : 1.0;
	totalSpecular = reflectedLight.directSpecular + gpEnv;
}`;

// "satin": sandblasted acrylic. Flat faces frost: their reflection is rough (0.42) and mirrors the host at 0.55 of the
// polished faces' strength, and the view through them is blurred (a sigma of 0.5 % of the frame's short side, the same at
// Studio and Cinema). The neutral milk veil is off (veil 0; the mechanism stays): round 1's 6 % greyed the 9:16 sky behind
// the far rim by about 12 sRGB levels over crystal and round 2's 1 % by 8-9 on the clear sky; with no veil and the
// frosted reflection at 0.55, round 3 measures +4.5 (sky between and right of the note bars, against crystal in the same
// frame). What a frosted face lets through is soft-kneed (max channel untouched to 0.15, easing to at most 0.25), so a
// hot plate end or a note bar cannot light a whole frosted panel, and at grazing a frosted face gains a faint neutral
// lift, 0.02 x (1 - |n.v|)^3, so it still reads over black. Bevels, lyre rods, braces and the prop stay polished
// (curvature from screen derivatives) and mirror the host at 1.4 (the frost against the sparkle is the look), and frosted
// faces turn glossy in REFLECTION only at grazing angles. The windows over the action (key slip, fallboard, desk rest,
// music desk: aPane 1) stay polished, so keys, hammers, dampers and strings stay sharp. They take no bevel boost (their
// bevels mirror at 0.55, so the key slip's line across the key fronts sits 30-40 sRGB levels over crystal; round 2
// +92) and a ceiling of their own, 0.15 on the base layer and on the clearcoat: at 0.35 the fallboard's long face
// mirrored the host as a cream slab at grazing in the lab close (5496 pixels over 150 sRGB levels in round 2, 2395 with
// the bevel fixes; 94 now, crystal 78). Only the music desk's top 0.6 units frost in, where the frosted far rim meets it
// in 16:9, so the window does not read as a hole; round 2 also frosted its sides, 1.45 units, which drew a frosted frame
// where the desk meets clear space, softened the lab close's dampers by 41 % and laid an 80 px band across the 9:16
// strings. The key blocks (aPane 2) and the cheeks (the rim in front of cheekZ: CHEEK) are polished too: frosted, the key
// blocks were dull grey slabs and the treble cheek blurred the plate's end into an amber smear (its detail -42 % against
// crystal; -9 % polished). Desaturating what the frost lets through, the other cure offered for the smear, turned the far
// rim at 9:16 into a grey panel over the purple sky. The legs read frosted top to toe (their lathe normals bend less than
// curv[0]). The blur is screen-space and has no depth, so a frosted face also softens opaque things just in front of it.
// Cost: about +0.1 ms at Cinema (5.43-5.66 vs 5.29-5.58 ms in round 1, not re-timed); one bicubic transmission sample as
// crystal, at a coarser mip; 4 derivatives and ~45 ALU; 3 cube lookups.
const SATIN = Object.freeze({
  rough: 0.42,         // reflection roughness of a fully frosted face, applied in the shader (m.roughness is never touched)
  polishRough: 0.05,   // polished bevels and windows (three floors roughness at 0.0525, then adds geometryRoughness)
  blur: 0.005,         // view-through blur sigma as a share of the frame's short side (Studio 5.4 px, Cinema 10.8 px)
  veil: 0,             // share of a frosted face's transmission given to the neutral diffuse film; 0 = none
  curv: [0.9, 2.0],    // curvature in 1/units: below 0.9 frosted, above 2.0 polished
  graze: [0.55, 0.9],  // 1 - |n.v|: where the REFLECTION turns glossy (the view through stays frosted)
  env: 0.9,            // envMapIntensity on the host's dark studio
  bevelEnv: 1.4,       // what the polished bevels and rods mirror instead (the shader scales them by bevelEnv / env)
  frostEnv: 0.55,      // what a frosted face's base layer mirrors, x env
  paneBevelEnv: 0.55,  // what the windows' polished bevels mirror (the key slip's line), base and clearcoat
  specCap: 0.5,        // per-layer ceiling on env specular, linear: base + 0.6 x clearcoat stays at or under ~0.8
  paneSpecCap: 0.15,   // the same ceiling on the windows' base layer
  paneCoatCap: 0.15,   // and on the windows' clearcoat
  knee: [0.15, 0.25],  // the light seen THROUGH a frosted face, max channel: untouched to [0], easing to at most [1]
  lift: 0.02,          // the neutral grazing lift on frosted faces, x (1 - |n.v|)^3
  feather: 0.6,        // units: the music desk's top frosts in over this much (its sides never do)
  cheekZ: -10,         // the rim is polished in front of this z (its front is -3.6): the cheeks flanking the keyboard
});
const SATIN_LOD = "float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );";  // r186 transmission_pars_fragment
const SATIN_TX = "material.transmission = transmission;";                                                 // r186 transmission_fragment
const SATIN_TX_END = "totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );";       // r186 transmission_fragment
const SATIN_DECL = "uniform vec2 uSatinRough;\nuniform vec4 uSatinShape;\nuniform float uSatinBlur, uSatinVeil, uSatinSpecCap;\n" +
  "uniform vec4 uSatinWin;\nvarying vec2 vSatinPos;\nfloat satinBlur = 0.0;\nfloat satinAARough = 0.0;\n";
// a bicubic tap of mip L spreads about 0.65 * 2^L px, so this lod gives sigma = satinBlur * the short side; never sharper
// than three's own anti-aliasing lod for a polished face
const SATIN_LOD_NEW = "float lod = max( log2( transmissionSamplerSize.x ) * applyIorToRoughness( satinAARough, ior ),\n" +
  "  log2( max( satinBlur * min( transmissionSamplerSize.x, transmissionSamplerSize.y ) * 1.54, 1.0 ) ) );";
// after the 0.0525 floor and geometryRoughness, before lights_fragment_begin reads material.roughness. uSatinWin is the
// music desk's own (half width, bottom, top, feather) in its local units, its bottom far below the desk so only the
// sides and top feather; w is 0 on the other two materials (no feather).
const SATIN_FROST = `
float satinCurv = max( length( dFdx( nonPerturbedNormal ) ) / max( length( dFdx( vViewPosition ) ), 1e-6 ),
  length( dFdy( nonPerturbedNormal ) ) / max( length( dFdy( vViewPosition ) ), 1e-6 ) );
float satinWin = 1.0;
if ( uSatinWin.w > 0.0 ) satinWin = smoothstep( 0.0, uSatinWin.w, min( uSatinWin.x - abs( vSatinPos.x ),
  min( vSatinPos.y - uSatinWin.y, uSatinWin.z - vSatinPos.y ) ) );
float satinBevel = smoothstep( uSatinShape.x, uSatinShape.y, satinCurv );
// the windows (1), key blocks (2) and the cheeks (CHEEK, -2, soft across the one ring where they meet the rim); the
// near-only legs (3) frost
float satinPolish = step( 0.5, vPane ) * step( vPane, 2.5 ) + smoothstep( -0.5, -1.5, vPane );
float satinFrost = ( 1.0 - satinPolish * satinWin ) * ( 1.0 - satinBevel );
float satinSheen = satinFrost * ( 1.0 - smoothstep( uSatinShape.z, uSatinShape.w,
  1.0 - abs( dot( nonPerturbedNormal, normalize( vViewPosition ) ) ) ) );
satinAARough = max( uSatinRough.x, 0.0525 ) + geometryRoughness;
material.roughness = min( max( mix( uSatinRough.x, uSatinRough.y, satinSheen ), 0.0525 ) + geometryRoughness, 1.0 );
#ifdef USE_CLEARCOAT
  material.clearcoat *= 1.0 - satinSheen;
#endif
satinBlur = satinFrost * uSatinBlur;
`;
// the polished bevels and rods mirror the host brighter; then env lines stay lines, never bloom sources at rest
// (clearcoatSpecularIndirect is a file-scope global in r186)
// The windows (glassWindow(), the desk's feathered top included) mirror at paneBevelEnv on their bevels instead of the
// bevelEnv boost, under ceilings of their own, base and clearcoat; a frosted face's base layer mirrors at frostEnv.
const SATIN_CAP = `
{
  float satinPane = glassWindow();
  float satinEnv = mix( 1.0, mix( ${f4(SATIN.bevelEnv / SATIN.env)}, ${f4(SATIN.paneBevelEnv / SATIN.env)}, satinPane ), satinBevel );
  float satinCap = mix( uSatinSpecCap, ${f4(SATIN.paneSpecCap)}, satinPane );
  float satinCoatCap = mix( uSatinSpecCap, ${f4(SATIN.paneCoatCap)}, satinPane );
  reflectedLight.indirectSpecular *= satinEnv * mix( 1.0, ${f4(SATIN.frostEnv)}, satinFrost );
  clearcoatSpecularIndirect *= satinEnv;
  reflectedLight.indirectSpecular *= min( 1.0, satinCap / max( max3( reflectedLight.indirectSpecular ), 1e-4 ) );
  clearcoatSpecularIndirect *= min( 1.0, satinCoatCap / max( max3( clearcoatSpecularIndirect ), 1e-4 ) );
}
`;
// the neutral veil: at frost 0 transmission stays 1, so mix(x, transmitted, 1) = transmitted and the windows are untouched
const SATIN_TX_NEW = "material.transmission = transmission * ( 1.0 - uSatinVeil * satinFrost );\n\ttotalDiffuse = vec3( luminance( totalDiffuse ) );";
// then the frosted light's knee (the same curve as studio's) and the grazing lift; n and v are the chunk's own
const SATIN_TX_END_NEW = SATIN_TX_END + `
	{
		float satinL = max3( totalDiffuse );
		const float SK0 = ${f4(SATIN.knee[0])}, SK1 = ${f4(SATIN.knee[1])};
		if ( satinL > SK0 ) totalDiffuse *= mix( 1.0, ( SK0 + ( SK1 - SK0 ) * ( 1.0 - exp( - ( satinL - SK0 ) / ( SK1 - SK0 ) ) ) ) / satinL, satinFrost );
		totalDiffuse += satinFrost * ${f4(SATIN.lift)} * pow( 1.0 - saturate( abs( dot( n, v ) ) ), 3.0 );
	}`;

// "smoked" (Smoked glass): grey-violet smoked acrylic that mirrors a studio of its own (smokeStudio, below; the host's
// strips sit where these faces never mirror them). A wall passes (0.52, 0.49, 0.60) head-on (luma 0.51) and 0.42 at
// grazing (the slab's true path t / cos theta_t, x1.35 at most, for the tint and the refraction offset alike); the
// panes over the action (key slip, fallboard, desk rest, music desk: aPane 1) take four times the attenuation distance,
// so the fallboard passes (0.76, 0.73, 0.83), luma 0.74, and the music desk, its real 10.4 mm pane, 0.77: a hammer flash
// behind the fallboard blooms from about velocity 65, behind the desk 63, behind a wall 78 (crystal 56).
// The pane factor departs from the round-1 synthesis, which asked for twice the distance; its bar is the action box at
// 9:16 within -15 % of crystal (mean sRGB levels; round 1's 0.43 panes: -35 %). Measured in one frame, twice still left
// -17 %, three times -14 %, four times -12 %. Round 2 shipped three times: -12.7 % in its frame, but -14.9 % in one of
// round 3's (the follow camera holds a different frame each render), a hair inside the bar, with the strip just behind
// the fallboard at -16.4 %; four times in that frame: -13.1 % and -14.8 %. Four times over four round-3 frames: action
// box -10.5 % to -14.8 % (-12 % to -23 % in linear light). The legs keep their 20 mm attenuation distance, (0.37, 0.35,
// 0.45): round 1's solid smoky columns.
// Reflections ride a soft ceiling (linear to the knee, easing to the ceiling per channel). Clearcoat stays 0.6, so the
// host lights' glints are crystal's. glint is the canvas alpha of the desk's glint band, now a crisp-topped band at
// 16-18 deg, on the desk's top edge rather than across the strings (sRGB: 0.25 is about 1/19 of its linear light at 1;
// 0 removes it).
// If the case reads purple, the neutral-cool fallback has the same luma: color 0xeeeef2, attenuationColor 0xbcbcc4,
// edgeColor 0xcfe0ff, and in smokeStudio a skylight of rgb(146,146,170) and a floor card of rgb(146,146,165).
// Cost: no pass; 3-6 cube fetches and ~30 ALU per glass fragment (5.8 vs 5.8 ms median at Cinema); once, a canvas paint,
// three transient PMREM programs and a bake (6 MB held).
const SMOKE = { color: 0xefebf6, attenuationColor: 0xbdbbc6, attenuationDistance: 20 / MM, legAttenuationDistance: 20 / MM,
  paneAttenuation: 4.0, deskThickness: 10.4 / MM, envMapIntensity: 2.0, legEnvMapIntensity: 2.2, edgeColor: 0xd8ccff,
  edgeGain: 0.07, knee: 0.30, ceiling: 0.65, glint: 0.25 };
const SMOKE_GLSL = `float smokePath( const in vec3 n, const in vec3 viewPos, const in float eta ) {
	float c = clamp( abs( dot( normalize( n ), normalize( viewPos ) ) ), 0.0, 1.0 );
	return inversesqrt( max( 1.0 - ( 1.0 - c * c ) / ( eta * eta ), 0.25 ) );
}
vec3 smokeCeil( const in vec3 x ) {
	vec3 over = max( x - ${f4(SMOKE.knee)}, 0.0 );
	return min( x, vec3( ${f4(SMOKE.knee)} ) ) + ${f4(SMOKE.ceiling - SMOKE.knee)} * ( 1.0 - exp( - over / ${f4(SMOKE.ceiling - SMOKE.knee)} ) );
}
`;
const SMOKE_TF_TO = "material.thickness = thickness * smokePath( normal, vViewPosition, material.ior );";
const SMOKE_ATT_TO = `material.attenuationDistance = attenuationDistance * mix( 1.0, ${f4(SMOKE.paneAttenuation)}, glassWindow() );`;
const SMOKE_CEIL = "\nreflectedLight.indirectSpecular = smokeCeil( reflectedLight.indirectSpecular );\nclearcoatSpecularIndirect = smokeCeil( clearcoatSpecularIndirect );";

// "lightguide" (Light guide): edge-lit acrylic, the way a lit acrylic sign glows at its polished edges.
// Where: the rounded bevels only. The shader measures how sharply the surface bends at each pixel (the shape operator's
// size, sqrt(k1^2 + k2^2), from screen derivatives of the normal and the position), so the bevels (radius 0.1-0.45 units,
// curvature 2.2-10 per unit) light, while flat faces (under 0.5) and the legs' shafts (about 0.6) stay clear; the mask
// (kLo/kHi 1.6/3.0) gives the 0.45 round-overs 39 % and the sharper slab bevels all of it. Rods (lyre posts, braces, the
// prop) are all bevel to that mask, so the leg material, which the prop joins in this look, keeps only a dim cool
// outline and takes no note light at all (partLegs). A bevel whose quarter round is wider on screen than LG.wide is a
// face at that range: it fades out, and so does its share of the silhouette line (round 1's lab close-up filled the
// cheek round-over with a pink and violet band, +58 % over crystal). The width is the pixels the normal takes to turn
// 90 deg (from its screen derivatives, so a bevel seen along its length is measured across it), as a share of the
// frame's short side, so Studio and Cinema match: 0.008-0.020 is 9-22 px at the lab close's 1080 and 17-43 px at
// Cinema's 2160. In the 9:16 follow view the bevels are about 1 % of the short side and keep about 93 % of it; the 6-14
// px gate the round-1 judges proposed would have darkened them at Cinema and not at Studio. The lab close's cheek box
// under the chord, linear against crystal: round 1 +122 %, round 2 +28 % (gate 0.015-0.035, host map 0.35), round 3
// +11 %; the same frame with the host map back at 0.35 gives +13 %, and with the line off +6 %.
// What: at rest a faint cool light, half as bright at the tail as at the keys, because the light comes in at the keyboard.
// A strike puts the note's colour into the edges at its key when the hammer reaches the string: a pool that fades where
// it landed, and two pulses that run left and right along the case, widening and fading. A sounding note keeps a low glow
// under its key on the strings' own envelope (bodyLvl), so it ends when the damper lands. The line is a 128-texel
// half-float texture across the case, rebuilt each frame from the strike events; it fades behind the keyboard and down
// the legs over LG.reach. The case-wide strike tint is off (strikeMul 0): the line carries the strikes, at their keys.
// Caps: each texel at luma 0.20 and 0.45 per channel, after the edge option. Thicker walls (20 mm) and legs (45 mm); the
// panes over the action keep crystal's 15 mm (at 20 mm the key slip lensed the brass caster's highlight into a warm hot
// spot right above it in the 9:16 view). The host studio at 0.25 under studio's knee, so the faces between the lines
// carry reflections (at round 2's 0.35 the host's warm strip lay on the 16:9 treble wall as a smudge, +11 sRGB levels
// over crystal, and brightened the 9:16 desk edge; round 3 +8), and a thinner clearcoat (0.3). The line depends on x
// only: a long edge running front to back shows a key's colour at every depth with that x, faded by reach (14, so the
// lid and tail edges stay cool).
// Cost: no pass; ~65 ALU per glass fragment (4 derivatives, one mat4), one fetch from the 128x1 line, the host map's
// cube lookups; 1 KB uploaded a frame while the line is lit; ~0.1 ms CPU worst case.
//   name          what it is                                                          value
//   rest          cool rest light on the bevels, x EDGE.color (luma 0.037)             0.05
//   restFar       the share of it the far edges keep                                   0.5
//   kLo/kHi       bevel mask: smoothstep on curvature per instrument unit              1.6 / 3.0 (radius 0.62 .. 0.33)
//   wide          the mask fades out as a quarter round grows from [0] to [1] of the    0.008 .. 0.020
//                 frame's short side (a close-up's round-over is a face, not an edge)
//   reach         units: the line light falls by e behind z = zFront / below the bed  14 (drop counts 0.6)
//   sil           share of the line light on the tightest silhouettes (pow 10)        0.35
//   speed         units/s each running pulse travels (an octave in 0.44 s)            16
//   sigma/spread  the pulse's width at the strike, and its widening per second        0.6 units, 1.5 units/s
//   tauRun/Pool   the running pulses' fade, the pool's fade                           0.6 s, 0.35 s
//   run/pool      each pulse's / the pool's peak at velocity 127, x note colour       0.20, 0.28 (x v^1.3)
//   sustain       the held glow under a sounding note, x bodyLvl x note colour        0.20
//   life/events   a strike is forgotten after life seconds; the event ring holds      3.0 s, 96
//   partCase/Legs (rest share, line share) per material                              [1, 1] / [0.35, 0]
const LG = Object.freeze({
  texels: 128, rest: 0.05, restFar: 0.5, kLo: 1.6, kHi: 3.0, wide: [0.008, 0.020], reach: 14, sil: 0.35, zFront: -6.3,
  speed: 16, sigma: 0.6, spread: 1.5, tauRun: 0.6, tauPool: 0.35, run: 0.20, pool: 0.28, sustain: 0.20, velExp: 1.3,
  life: 3.0, events: 96, maxLuma: 0.20, maxChannel: 0.45, partCase: [1, 1], partLegs: [0.35, 0],
});
const LIGHTGUIDE = { thickness: 20 / MM, paneThickness: GLASS.thickness, legThickness: 45 / MM, clearcoat: 0.3,
  envMapIntensity: 0.25 };
const LG_TX_THICKNESS = `material.thickness = thickness * mix( 1.0, ${f4(LIGHTGUIDE.paneThickness / LIGHTGUIDE.thickness)}, glassWindow() );`;
const LG_PARS = `uniform sampler2D uLgLine;
uniform mat4 uLgFrame;
uniform float uLgScale;
uniform vec3 uLgRest;
uniform vec4 uLgMask;
uniform vec4 uLgSpan;
uniform vec2 uLgPart;
`;
// uLgMask = (kLo, kHi, 1/reach, restFar), uLgSpan = (line x0, 1/line width, zFront, bed y), uLgFrame = world -> instrument.
// The first three lines are crystal's edge, unchanged. vWorldPosition exists whenever transmission is on (it always is here).
const LG_EDGE = `#include <emissivemap_fragment>
{ float fr = 1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0);
  float frS = pow(fr, uStrikePow);
  totalEmissiveRadiance += uEdge * pow(fr, uEdgePow) + uStrike * frS;
  vec3 lgNx = dFdx(normal), lgNy = dFdy(normal), lgPx = dFdx(vViewPosition), lgPy = dFdy(vViewPosition);
  vec3 lgC = cross(lgPx, lgPy);
  float lgT = dot(lgNx, lgNx) * dot(lgPy, lgPy) + dot(lgNy, lgNy) * dot(lgPx, lgPx) - 2.0 * dot(lgNx, lgNy) * dot(lgPx, lgPy);
  float lgK = sqrt(max(lgT, 0.0) / max(dot(lgC, lgC), 1e-24)) * uLgScale;
  float lgBevel = smoothstep(uLgMask.x, uLgMask.y, lgK);
  float lgNarrow = 1.0;
#ifdef USE_TRANSMISSION
  vec3 lgW = vWorldPosition;
  // the quarter round of this bevel on screen: the pixels its normal takes to turn 90 deg, then a share of the short side
  float lgArc = 1.5708 / max(sqrt(dot(lgNx, lgNx) + dot(lgNy, lgNy)), 1e-6);
  lgNarrow = 1.0 - smoothstep(${f4(LG.wide[0])}, ${f4(LG.wide[1])}, lgArc / min(transmissionSamplerSize.x, transmissionSamplerSize.y));
  lgBevel *= lgNarrow;
#else
  vec3 lgW = (vec4(-vViewPosition - viewMatrix[3].xyz, 0.0) * viewMatrix).xyz;
#endif
  vec3 lgP = (uLgFrame * vec4(lgW, 1.0)).xyz;
  float lgReach = exp(-(max(uLgSpan.z - lgP.z, 0.0) + 0.6 * max(uLgSpan.w - lgP.y, 0.0)) * uLgMask.z);
  vec3 lgLine = texture2D(uLgLine, vec2((lgP.x - uLgSpan.x) * uLgSpan.y, 0.5)).rgb * lgReach;
  totalEmissiveRadiance += lgBevel * (uLgRest * (uLgPart.x * mix(uLgMask.w, 1.0, lgReach)) + lgLine * uLgPart.y)
    + frS * ${LG.sil.toFixed(2)} * uLgPart.y * lgLine * lgNarrow; }`;

// Crystal's edge and strike, byte for byte as they have always been compiled ("glass-piano-crystal").
const EDGE_DECL = "uniform vec3 uEdge;\nuniform float uEdgePow;\nuniform vec3 uStrike;\nuniform float uStrikePow;\n";
const EDGE_GLSL = "#include <emissivemap_fragment>\n{ float fr = 1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0);\n  totalEmissiveRadiance += uEdge * pow(fr, uEdgePow) + uStrike * pow(fr, uStrikePow); }";
// A look whose anchor is gone from a future three still compiles: it warns and skips that part.
const hasAnchor = (src, at, look) => {
  if (src.includes(at)) return true;
  console.warn(`glass-piano: three's shader no longer has "${at}"; the ${look} glass skips that part`);
  return false;
};
// The panes over the action (key slip, fallboard, desk rest, music desk) are windows, flagged per vertex: aPane 1. The
// key blocks carry 2, a flag only satin reads (it polishes them, as it polishes the windows). The parts of the leg draw
// that never show their far faces carry 3 (NEAR_ONLY, below), and every other glass vertex 0. A part carries one flag
// throughout, so the varying never blends two flags, and glassWindow() is exactly 1 on the windows and 0 elsewhere (3
// included). Studio, satin, smoked, prism and the light guide read it; crystal and lens never do.
const paneVertex = (sh) => {
  sh.vertexShader = "attribute float aPane;\nvarying float vPane;\n" +
    sh.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\n\tvPane = aPane;");
};
const PANE_FRAG = "varying float vPane;\nfloat glassWindow() { return clamp( 1.0 - abs( vPane - 1.0 ), 0.0, 1.0 ); }\n";
// The foot, round 3. With every leg part DoubleSide (round 2), the left lyre post's far faces crossed the tail caster in
// the 9:16 view and lensed a second, smaller caster below it (the spot Daniel misread), a lit key hung under the key
// slip at the right post, and a gold sliver showed in the lab close; a same-frame render with the lyre's far faces back
// on puts all three back. Only the legs' far faces are wanted (the tail leg's show it standing on its caster through
// the key slip, the front legs' make them read as columns on their casters in the lab hero), so every other part of the
// leg draw (the lyre posts and braces, the pedal box, and the prop when the light guide hangs it on the leg glass)
// carries NEAR_ONLY and is drawn as if FrontSide. In three's transmission pass the leg
// glass is drawn BackSide (FLIP_SIDED; three also flips frontFace there, so gl_FrontFacing is true for every fragment
// and cannot tell the faces apart): those parts are dropped whole. In the main pass (DOUBLE_SIDED) their far faces are.
// The walls and the desk are FrontSide, compiled with neither define, so their programs carry no discard. One flag on
// one draw: no material, draw call or program is added, and crystal (FrontSide, never reading aPane) is untouched.
// Receipts, 2026-10-10, SwiftShader, each look against crystal in the same frame (9:16 Cinema boxes moved with the
// caster): where round 2's lyre post dropped part of the caster, +28.8 sRGB levels in studio, round 3 measures -2 to +2
// in every DoubleSide look over two frames; the right post's key tile, +26.6, now -4 to +4; the lab close's gold
// sliver, 1386 pixels more than 20 levels over crystal in studio, now 0.
const NEAR_ONLY = 3;
// Satin's polished cheeks (round 3): the rim's own vertices in front of SATIN.cheekZ carry CHEEK. It is negative, so
// across the one ring where the cheek meets the rest of the rim the varying runs -2..0 and never passes 1:
// glassWindow() stays 0 there, studio's near-only test stays false, and only satin reads it (it polishes the cheeks).
const CHEEK = -2;
// What a leg's far face refracts. three refracts every transmissive face as if it carried the whole path, and the far
// face is the leg's ONLY face in that pass: at studio's full 42 mm the sample landed about 20 px up the screen, on the
// key fronts above the caster, so the tail leg read as a tile of the lit key's colour that would change with every
// chord. Its
// thickness and attenuation distance are both scaled by LEG_FAR_PATH in that pass, so the Beer tint stays the leg's
// whole path and only the offset shrinks: the floor behind the leg shows through it, and the leg reads by its edges
// and what it mirrors. Main-pass faces are untouched (the define is FLIP_SIDED only).
const LEG_FAR_PATH = 0.25;
const LEG_FACES = `#include <clipping_planes_fragment>
#if defined( FLIP_SIDED )
	if ( vPane > 2.5 ) discard;
#elif defined( DOUBLE_SIDED )
	if ( vPane > 2.5 && ! gl_FrontFacing ) discard;
#endif`;
const TX_POS = "vec3 pos = vWorldPosition;";                                // r186 transmission_fragment
const TX_FAR = `#ifdef FLIP_SIDED
	material.thickness *= ${f4(LEG_FAR_PATH)};
	material.attenuationDistance *= ${f4(LEG_FAR_PATH)};
	#endif
	` + TX_POS;
// every look that draws the legs DoubleSide (legSide "double") calls this after declaring vPane
const nearOnly = (sh, look) => {
  if (hasAnchor(sh.fragmentShader, "#include <clipping_planes_fragment>", look))
    sh.fragmentShader = sh.fragmentShader.replace("#include <clipping_planes_fragment>", () => LEG_FACES);
};
// three's transmission chunk, inlined with some of its lines rewritten (satin, smoked, prism, the light guide); a line a
// future three no longer has is skipped with a warning, and the rest of the chunk is three's own
const TX_THICKNESS = "material.thickness = thickness;";                       // r186 transmission_fragment, once each
const TX_ATTENUATION = "material.attenuationDistance = attenuationDistance;";
const txChunk = (THREE, look, swaps) => {
  let c = THREE.ShaderChunk && THREE.ShaderChunk.transmission_fragment;
  if (!c || !hasAnchor(c, "#ifdef USE_TRANSMISSION", look)) return "#include <transmission_fragment>";
  for (const [from, to] of swaps) if (hasAnchor(c, from, look)) c = c.replace(from, () => to);
  return c;
};
// Each look's GLSL, applied in onBeforeCompile after every look's uniforms are installed. Replacements are functions,
// so no "$" in three's chunk text is ever read as a replacement pattern.
const LOOK_GLSL = {
  crystal(sh) {
    sh.fragmentShader = EDGE_DECL + sh.fragmentShader.replace("#include <emissivemap_fragment>", EDGE_GLSL);
  },
  // crystal, then the knee: "#include <aomap_fragment>" comes after lights_fragment_end, where indirectSpecular is final,
  // and before totalSpecular is summed, so it compresses only the mirrored environment
  studio(sh, THREE) {
    LOOK_GLSL.crystal(sh);
    if (hasAnchor(sh.fragmentShader, "#include <aomap_fragment>", "studio")) sh.fragmentShader = sh.fragmentShader.replace("#include <aomap_fragment>", () => STUDIO_KNEE);
    paneVertex(sh);   // only for the foot: studio reads aPane nowhere else
    sh.fragmentShader = PANE_FRAG + sh.fragmentShader.replace("#include <transmission_fragment>",
      () => txChunk(THREE, "studio", [[TX_POS, TX_FAR]]));
    nearOnly(sh, "studio");
  },
  // REPLACES crystal's edge injection (no emissivemap edge, so no double edge): the edge moves into the transmission chunk
  lens(sh, THREE) {
    const chunk = THREE.ShaderChunk && THREE.ShaderChunk.transmission_fragment;
    if (!chunk || !hasAnchor(chunk, LENS_ANCHOR, "lens") || !hasAnchor(sh.fragmentShader, "#include <transmission_fragment>", "lens")) {
      LOOK_GLSL.crystal(sh);
      return;
    }
    sh.fragmentShader = LENS_DECL + sh.fragmentShader.replace("#include <transmission_fragment>",
      () => chunk.replace(LENS_ANCHOR, () => LENS_GLSL + "\t" + LENS_ANCHOR));
  },
  // REPLACES crystal's edge injection: the edge, the cut lines and the tint are drawn after the transmission chunk, which
  // gives the panes their 15 mm
  prism(sh, THREE) {
    if (!hasAnchor(sh.fragmentShader, "#include <transmission_fragment>", "prism")) { LOOK_GLSL.crystal(sh); return; }
    paneVertex(sh);
    const tx = txChunk(THREE, "prism", [[TX_THICKNESS, PRISM_TX_THICKNESS], [TX_POS, TX_FAR]]);
    sh.fragmentShader = EDGE_DECL + PANE_FRAG + sh.fragmentShader.replace("#include <transmission_fragment>", () => tx + PRISM_GLSL);
    nearOnly(sh, "prism");
  },
  satin(sh, THREE) {
    LOOK_GLSL.crystal(sh);
    const C = THREE.ShaderChunk;
    const pars = hasAnchor(C.transmission_pars_fragment, SATIN_LOD, "satin") ? C.transmission_pars_fragment.replace(SATIN_LOD, () => SATIN_LOD_NEW)
      : C.transmission_pars_fragment;
    const tx = txChunk(THREE, "satin", [[SATIN_TX, SATIN_TX_NEW], [SATIN_TX_END, SATIN_TX_END_NEW], [TX_POS, TX_FAR]]);
    paneVertex(sh);
    sh.vertexShader = "varying vec2 vSatinPos;\n" +   // the music desk's own frame, for its feathered border
      sh.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\n\tvSatinPos = transformed.xy;");
    sh.fragmentShader = PANE_FRAG + SATIN_DECL + sh.fragmentShader
      .replace("#include <transmission_pars_fragment>", () => pars)
      .replace("#include <lights_physical_fragment>", () => "#include <lights_physical_fragment>\n" + SATIN_FROST)
      .replace("#include <lights_fragment_end>", () => "#include <lights_fragment_end>\n" + SATIN_CAP)
      .replace("#include <transmission_fragment>", () => tx);
    nearOnly(sh, "satin");
  },
  smoked(sh, THREE) {
    LOOK_GLSL.crystal(sh);
    paneVertex(sh);
    const tf = txChunk(THREE, "smoked", [[TX_THICKNESS, SMOKE_TF_TO], [TX_ATTENUATION, SMOKE_ATT_TO], [TX_POS, TX_FAR]]);
    sh.fragmentShader = PANE_FRAG + SMOKE_GLSL + sh.fragmentShader
      .replace("#include <lights_fragment_end>", () => "#include <lights_fragment_end>" + SMOKE_CEIL)   // the mirrored studio only
      .replace("#include <transmission_fragment>", () => tf);
    nearOnly(sh, "smoked");
  },
  // REPLACES crystal's edge injection with one that contains it (the first three lines of LG_EDGE); the panes take 15 mm
  // in the transmission chunk, and the host map's reflections take studio's knee
  lightguide(sh, THREE) {
    paneVertex(sh);
    let f = sh.fragmentShader.replace("#include <emissivemap_fragment>", () => LG_EDGE);
    if (hasAnchor(f, "#include <transmission_fragment>", "lightguide"))
      f = f.replace("#include <transmission_fragment>",
        () => txChunk(THREE, "lightguide", [[TX_THICKNESS, LG_TX_THICKNESS], [TX_POS, TX_FAR]]));
    if (hasAnchor(f, "#include <aomap_fragment>", "lightguide")) f = f.replace("#include <aomap_fragment>", () => STUDIO_KNEE);
    sh.fragmentShader = EDGE_DECL + LG_PARS + PANE_FRAG + f;
    nearOnly(sh, "lightguide");
  },
};

// The looks, in menu order (crystal first: the host shows choices[0] when nothing is saved; fast last). Every record
// sets every field a look may change; crystal is exactly makeGlass's constructor values. env: null (none), "host"
// (ctx.envMap, the page's dark studio) or the name of a map the instrument paints itself (GLASS_ENV_PAINTERS). The leg*
// and desk* fields are the legs' (legs, lyre, pedal box) and the music desk's own, null = the walls' value; legSide
// "double" draws the legs DoubleSide (the foot: see the rules above GLASS_LOOKS).
const CRYSTAL_LOOK = Object.freeze({
  name: "Crystal", shader: "crystal",
  transmission: 1, transparent: false, opacity: 1, depthWrite: true, color: GLASS.color, roughness: GLASS.roughness,
  ior: GLASS.ior, dispersion: 0, thickness: GLASS.thickness, legThickness: GLASS.legThickness, deskThickness: null,
  attenuationColor: GLASS.attenuationColor, attenuationDistance: GLASS.attenuationDistance, legAttenuationDistance: null,
  specularIntensity: 1, clearcoat: 0.6, clearcoatRoughness: 0.04, env: null, envMapIntensity: 1, legEnvMapIntensity: null,
  edgeColor: EDGE.color, edgeGain: EDGE.gain, strikeMul: 1, propOnLegs: false,
  legSide: "front", legRoughness: null, deskEnvMapIntensity: null,
});
const GLASS_LOOKS = Object.freeze({
  crystal: CRYSTAL_LOOK,
  studio: Object.freeze({ ...CRYSTAL_LOOK, name: "Studio crystal", shader: "studio", clearcoat: STUDIO.clearcoat,
    legThickness: STUDIO.legThickness, legRoughness: STUDIO.legRoughness, legAttenuationDistance: STUDIO.legAttenuationDistance,
    env: "studio", envMapIntensity: STUDIO.envMapIntensity, deskEnvMapIntensity: STUDIO.deskEnvMapIntensity,
    edgeGain: EDGE.gain * STUDIO.edgeMul, strikeMul: STUDIO.strikeMul, legSide: "double" }),
  lens: Object.freeze({ ...CRYSTAL_LOOK, name: "Lensing edges", shader: "lens", attenuationColor: LENS.attenuationColor,
    attenuationDistance: LENS.attenuationDistance, env: "host", envMapIntensity: LENS.envIntensity }),
  prism: Object.freeze({ ...CRYSTAL_LOOK, name: "Prism", shader: "prism", ior: PRISM.ior, dispersion: PRISM.dispersion,
    thickness: PRISM.thickness, legThickness: PRISM.legThickness, clearcoat: 0, env: "host", envMapIntensity: PRISM.envMapIntensity,
    legSide: "double" }),
  satin: Object.freeze({ ...CRYSTAL_LOOK, name: "Satin", shader: "satin", env: "host", envMapIntensity: SATIN.env,
    legSide: "double" }),
  smoked: Object.freeze({ ...CRYSTAL_LOOK, name: "Smoked glass", shader: "smoked", color: SMOKE.color,
    attenuationColor: SMOKE.attenuationColor, attenuationDistance: SMOKE.attenuationDistance,
    legAttenuationDistance: SMOKE.legAttenuationDistance, deskThickness: SMOKE.deskThickness, env: "smoke",
    envMapIntensity: SMOKE.envMapIntensity, legEnvMapIntensity: SMOKE.legEnvMapIntensity, edgeColor: SMOKE.edgeColor,
    edgeGain: SMOKE.edgeGain, legSide: "double" }),
  lightguide: Object.freeze({ ...CRYSTAL_LOOK, name: "Light guide", shader: "lightguide", thickness: LIGHTGUIDE.thickness,
    legThickness: LIGHTGUIDE.legThickness, clearcoat: LIGHTGUIDE.clearcoat, env: "host",
    envMapIntensity: LIGHTGUIDE.envMapIntensity, strikeMul: 0, propOnLegs: true, legSide: "double" }),
  fast: Object.freeze({ ...CRYSTAL_LOOK, name: "Fast (no refraction)", transmission: 0, transparent: true,
    opacity: GLASS.fastOpacity, depthWrite: false, color: GLASS.fastColor }),
});
const GLASS_TITLE = "How the acrylic case is drawn. Crystal: the original clear acrylic. Studio: lit like a product photo. " +
  "Lensing: the edges bend what is behind them. Prism: cut crystal with colour fringes. Satin: frosted faces, polished " +
  "edges. Smoked: tinted glass. Light guide: each note runs along the edges. Fast: no refraction pass.";
const STRING_W = 0.06;  // strings are thin crossed ribbons, not GL lines, so MSAA smooths them
const ETCH = { level: 0.15, flash: 0.9, tau: 0.5 };  // a low resting glow, so the etch never competes with the page's chord header
const CHECK = 0.42;   // share of the blow the hammer is held at while its key stays down

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const mix = (a, b, f) => a + (b - a) * f;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / tau);
// The damper's fade, x seconds after the sound ended: the body is already falling at TAU_DAMP, and this window closes
// that fall to exactly 0 at DAMP_FADE. A bare exponential has no end — at TAU_DAMP alone a loud release was still on
// screen a second later, i.e. the light outlived the sound. Smoothstep, so it lands with zero slope and never snaps.
const dampFade = (x) => { if (x >= DAMP_FADE) return 0; const u = x / DAMP_FADE; return 1 - u * u * (3 - 2 * u); };

// ---- the string ribbon shader (the same pair as concert-grand.js; kept per file, an instrument imports nothing) ----
// Vertex: the ribbon is widened perpendicular to the string AS DRAWN, in screen space, so a blur reads the same however
// the string is foreshortened. Half-width = the swing amplitude carried per note in uNote[i].w (world units, projected
// here), never under the string's own resting width. aParam = (u along the speaking length, side -1/+1, light dim, note).
// Fragment: the long-exposure density of a sine swing, 1/sqrt(1-(x/A)^2) — what the eye actually sees of a wing that beats
// faster than the frame rate — normalised and conserved, so a wider blur is fainter per pixel and never stacks to white.
const stringVert = (notes) => `
precision highp float;
uniform vec2 uRes;
uniform float uTime, uMinPx, uRestHalf, uWobble;
uniform vec4 uNote[${notes}];
attribute vec3 aBase;
attribute vec3 aDir;
attribute vec4 aParam;
attribute vec2 aVib;
varying vec3 vCol;
varying float vAcross;
varying float vCore;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec4 clip = projectionMatrix * mv;
  vec3 dv = mat3(modelViewMatrix) * aDir;                           // aDir is a unit vector in object space,
  float kScale = length(dv);                                        // so its length here is the host's scale on the instrument
  vec4 clipB = projectionMatrix * (mv + vec4(dv, 0.0));
  float w = max(clip.w, 1e-4);
  vec2 s0 = clip.xy / w * uRes * 0.5;
  vec2 s1 = clipB.xy / max(clipB.w, 1e-4) * uRes * 0.5;
  vec2 tang = s1 - s0;
  vec2 nrm = dot(tang, tang) > 1e-8 ? normalize(vec2(-tang.y, tang.x)) : vec2(1.0, 0.0);
  float pxPerUnit = projectionMatrix[1][1] * uRes.y * 0.5 / w;
  vec4 nd = uNote[int(aParam.w + 0.5)];
  float shape = sin(3.14159265 * aParam.x);
  float amp = nd.w * shape;
  float halfW = max(uRestHalf, amp * (0.80 + 0.20 * sin(uTime * aVib.y + aVib.x)));
  float wob = amp * uWobble * sin(uTime * aVib.y * 0.5 + aVib.x * 1.7);
  float restPx = max(uMinPx, uRestHalf * kScale * pxPerUnit);
  float halfPx = max(restPx, halfW * kScale * pxPerUnit);
  clip.xy += nrm * (aParam.y * halfPx + wob * kScale * pxPerUnit) / (uRes * 0.5) * w;
  gl_Position = clip;
  vCol = aBase + nd.rgb * aParam.z;
  vAcross = aParam.y;
  vCore = restPx / halfPx;
}`;
const STRING_FRAG = `
precision highp float;
uniform float uDensCap, uDensNorm, uConserve;
varying vec3 vCol;
varying float vAcross;
varying float vCore;
void main() {
  float d = min(abs(vAcross), 1.0);
  float dens = min(inversesqrt(max(1.0 - d * d, 1e-3)), uDensCap) * uDensNorm;
  float blur = dens * pow(vCore, uConserve) * smoothstep(1.0, 0.86, d);
  float solid = smoothstep(1.0, 0.72, d);                         // the string at rest: the thin ribbon it has always been
  float a = mix(solid, blur, smoothstep(0.0, 0.55, 1.0 - vCore));
  gl_FragColor = vec4(vCol, clamp(a, 0.0, 1.0));
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;
const isPortrait = (f) => !!f && (f.id === "9:16" || (f.h > 0 && f.h > f.w));
const norm2 = (x, z) => { const l = Math.hypot(x, z) || 1; return [x / l, z / l]; };

// ------------------------------------------------------------------ 2D helpers (x, z) --
function signedArea(poly) {
  let a = 0;
  for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length]; a += p[0] * q[1] - q[0] * p[1]; }
  return a / 2;
}
// Rings along a path in the XZ plane: position, tangent, outward normal n = (t.z, -t.x), miter k. Sharp corners (> 35
// degrees) get two rings, one per edge, so flat faces keep flat normals.
function pathRings(pts, closed) {
  const n = pts.length, out = [], cs = Math.cos(35 * DEG);
  for (let i = 0; i < n; i++) {
    const p = pts[i];
    const dIn = closed || i > 0 ? norm2(p[0] - pts[(i - 1 + n) % n][0], p[1] - pts[(i - 1 + n) % n][1]) : null;
    const dOut = closed || i < n - 1 ? norm2(pts[(i + 1) % n][0] - p[0], pts[(i + 1) % n][1] - p[1]) : null;
    const push = (d, k) => out.push({ x: p[0], z: p[1], tx: d[0], tz: d[1], nx: d[1], nz: -d[0], k });
    if (dIn && dOut) {
      const dot = dIn[0] * dOut[0] + dIn[1] * dOut[1];
      if (dot < cs) { push(dIn, 1); push(dOut, 1); } else {
        const a = norm2(dIn[0] + dOut[0], dIn[1] + dOut[1]);
        push(a, 1 / Math.max(0.4, a[0] * dIn[0] + a[1] * dIn[1]));
      }
    } else push(dIn || dOut, 1);
  }
  if (closed) out.push({ ...out[0] });
  return out;
}
function insetPoly(pts, d) {  // closed; positive d moves inward (against the outward normal)
  const n = pts.length;
  return pts.map((p, i) => {
    const a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n];
    const di = norm2(p[0] - a[0], p[1] - a[1]), dout = norm2(b[0] - p[0], b[1] - p[1]);
    const ni = [di[1], -di[0]], no = [dout[1], -dout[0]];
    const m = norm2(ni[0] + no[0], ni[1] + no[1]);
    const k = 1 / Math.max(0.3, m[0] * ni[0] + m[1] * ni[1]);
    return [p[0] - m[0] * d * k, p[1] - m[1] * d * k];
  });
}
function clipPolyZ(pts, zc) {  // closed polygon, keep z <= zc
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], q = pts[(i + 1) % pts.length], pin = p[1] <= zc, qin = q[1] <= zc;
    if (pin) out.push(p);
    if (pin !== qin) { const s = (zc - p[1]) / (q[1] - p[1]); out.push([p[0] + (q[0] - p[0]) * s, zc]); }
  }
  return out;
}
function clipLineZ(pts, zc) {  // open polyline, keep z <= zc
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], pin = p[1] <= zc;
    if (i > 0) {
      const q = pts[i - 1];
      if ((q[1] <= zc) !== pin) { const s = (zc - q[1]) / (p[1] - q[1]); out.push([q[0] + (p[0] - q[0]) * s, zc]); }
    }
    if (pin) out.push(p);
  }
  return out;
}
function resample(pts, maxLen, closed) {
  const out = [], n = pts.length;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const p = pts[i], q = pts[(i + 1) % n], steps = Math.max(1, Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / maxLen));
    for (let s = 0; s < steps; s++) out.push([p[0] + (q[0] - p[0]) * s / steps, p[1] + (q[1] - p[1]) * s / steps]);
  }
  if (!closed) out.push(pts[n - 1]);
  return out;
}
function inside(poly, x, z) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
  }
  return c;
}
// A rounded rectangle in the (u, v) profile plane, counter-clockwise.
function rrect(u0, u1, v0, v1, r, seg = 4) {
  r = Math.min(r, (u1 - u0) / 2 - 1e-4, (v1 - v0) / 2 - 1e-4);
  const out = [];
  const arc = (cu, cv, a0) => { for (let s = 0; s <= seg; s++) { const a = (a0 + 90 * s / seg) * DEG; out.push([cu + r * Math.cos(a), cv + r * Math.sin(a)]); } };
  if (r <= 1e-3) return [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
  arc(u1 - r, v0 + r, -90); arc(u1 - r, v1 - r, 0); arc(u0 + r, v1 - r, 90); arc(u0 + r, v0 + r, 180);
  return out;
}

// ------------------------------------------------------------------ geometry builders --
function makeBuilders(THREE) {
  // Sweep a closed (u, v) profile along XZ rings: u runs along the ring's outward normal, v is world y.
  function sweep(rings, poly, caps) {
    if (signedArea(poly) < 0) poly = poly.slice().reverse();
    const n = poly.length, cs = Math.cos(35 * DEG), prof = [];
    for (let i = 0; i < n; i++) {
      const p = poly[i], a = poly[(i - 1 + n) % n], b = poly[(i + 1) % n];
      const di = norm2(p[0] - a[0], p[1] - a[1]), dout = norm2(b[0] - p[0], b[1] - p[1]);
      const ni = [di[1], -di[0]], no = [dout[1], -dout[0]];
      if (di[0] * dout[0] + di[1] * dout[1] < cs) prof.push([p[0], p[1], ni[0], ni[1]], [p[0], p[1], no[0], no[1]]);
      else { const m = norm2(ni[0] + no[0], ni[1] + no[1]); prof.push([p[0], p[1], m[0], m[1]]); }
    }
    prof.push(prof[0].slice());
    const P = prof.length, R = rings.length, pos = [], nor = [], idx = [];
    for (const r of rings) for (const q of prof) {
      const u = q[0] * r.k;
      pos.push(r.x + r.nx * u, q[1], r.z + r.nz * u);
      nor.push(r.nx * q[2], q[3], r.nz * q[2]);
    }
    for (let i = 0; i < R - 1; i++) for (let j = 0; j < P - 1; j++) {
      const a = i * P + j, b = (i + 1) * P + j, c = a + 1, d = b + 1;
      idx.push(a, b, c, c, b, d);
    }
    const faceDot = (a, b, c) => {
      const ax = pos[a * 3], ay = pos[a * 3 + 1], az = pos[a * 3 + 2];
      const ux = pos[b * 3] - ax, uy = pos[b * 3 + 1] - ay, uz = pos[b * 3 + 2] - az;
      const vx = pos[c * 3] - ax, vy = pos[c * 3 + 1] - ay, vz = pos[c * 3 + 2] - az;
      const fx = uy * vz - uz * vy, fy = uz * vx - ux * vz, fz = ux * vy - uy * vx;
      return fx * (nor[a * 3] + nor[b * 3] + nor[c * 3]) + fy * (nor[a * 3 + 1] + nor[b * 3 + 1] + nor[c * 3 + 1]) + fz * (nor[a * 3 + 2] + nor[b * 3 + 2] + nor[c * 3 + 2]);
    };
    let score = 0;
    for (let k = 0; k < idx.length; k += 3) score += faceDot(idx[k], idx[k + 1], idx[k + 2]);
    if (score < 0) for (let k = 0; k < idx.length; k += 3) { const t = idx[k + 1]; idx[k + 1] = idx[k + 2]; idx[k + 2] = t; }
    if (caps) {
      const tris = THREE.ShapeUtils.triangulateShape(poly.map((p) => new THREE.Vector2(p[0], p[1])), []);
      for (const end of [0, 1]) {
        const r = end ? rings[R - 1] : rings[0], sg = end ? 1 : -1, base = pos.length / 3;
        for (const p of poly) { const u = p[0] * r.k; pos.push(r.x + r.nx * u, p[1], r.z + r.nz * u); nor.push(sg * r.tx, 0, sg * r.tz); }
        for (const t of tris) {
          const a = base + t[0], b = base + t[1], c = base + t[2];
          if (faceDot(a, b, c) >= 0) idx.push(a, b, c); else idx.push(a, c, b);
        }
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    return g;
  }
  const slabX = (x0, x1, zf, zb, y0, y1, r) => sweep(pathRings([[x0, 0], [x1, 0]], false), rrect(-zf, -zb, y0, y1, r), true);
  const slabZ = (zf, zb, xl, xr, y0, y1, r) => sweep(pathRings([[0, zf], [0, zb]], false), rrect(-xr, -xl, y0, y1, r), true);
  const bar = (x0, z0, x1, z1, hw, y0, y1, r) => sweep(pathRings([[x0, z0], [x1, z1]], false), rrect(-hw, hw, y0, y1, r), true);
  function capSlab(poly, y0, y1) {  // flat top and bottom caps of a closed XZ polygon (the lid's inner field)
    const tris = THREE.ShapeUtils.triangulateShape(poly.map((p) => new THREE.Vector2(p[0], -p[1])), []);
    const cw = signedArea(poly.map((p) => [p[0], -p[1]])) < 0;
    const pos = [], nor = [], idx = [];
    for (const [y, up] of [[y1, 1], [y0, -1]]) {
      const base = pos.length / 3;
      for (const p of poly) { pos.push(p[0], y, p[1]); nor.push(0, up, 0); }
      // triangulated in (x, -z): CCW there faces -y after mapping back, so flip for the top
      for (const t of tris) {
        const flip = (up > 0) !== cw;
        idx.push(base + t[0], base + (flip ? t[2] : t[1]), base + (flip ? t[1] : t[2]));
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    return g;
  }
  function merge(list) {
    const parts = list.map((g) => (g.index ? g.toNonIndexed() : g));
    let count = 0;
    for (const g of parts) count += g.attributes.position.count;
    const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), uv = new Float32Array(count * 2);
    let o = 0;
    for (const g of parts) {
      pos.set(g.attributes.position.array, o * 3);
      if (g.attributes.normal) nor.set(g.attributes.normal.array, o * 3);
      if (g.attributes.uv) uv.set(g.attributes.uv.array, o * 2);
      o += g.attributes.position.count;
    }
    for (const g of list) g.dispose();
    for (const g of parts) g.dispose();
    const out = new THREE.BufferGeometry();
    out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
    out.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    out.computeBoundingSphere();
    return out;
  }
  const at = (g, x, y, z, rx = 0, ry = 0, rz = 0) => {
    if (rx || ry || rz) g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rx, ry, rz)));
    g.translate(x, y, z);
    return g;
  };
  return { sweep, slabX, slabZ, bar, capSlab, merge, at };
}

// The case plan: spine straight on the left, rounded tail, a gently concave bentside, a short straight treble cheek.
// Returned as world (x, z) points from the front-left corner round to the front-right corner.
function caseOutline(THREE) {
  const W = G.halfW, f = -G.front;
  const p = new THREE.Path();
  p.moveTo(-W, f);
  p.lineTo(-W, 50);
  p.bezierCurveTo(-W, 72, -6, 82, -1, 74);
  p.bezierCurveTo(5, 64.4, 24, 27, W, 17);
  p.lineTo(W, f);
  const out = [];
  for (const v of p.getSpacedPoints(220)) {
    const q = [v.x, -v.y], last = out[out.length - 1];
    if (!last || Math.hypot(q[0] - last[0], q[1] - last[1]) > 1e-3) out.push(q);
  }
  return out;
}

function grainTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const g = c.getContext("2d");
  g.fillStyle = "#8d6c47";
  g.fillRect(0, 0, 512, 512);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 260; i++) {
    const x = rnd() * 512, w = 0.6 + rnd() * 2.6, light = rnd() < 0.5;
    g.fillStyle = light ? `rgba(236,205,160,${0.05 + rnd() * 0.12})` : `rgba(60,38,20,${0.05 + rnd() * 0.16})`;
    g.fillRect(x, 0, w, 512);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(1 / 26, 1 / 26);
  t.rotation = 0.55;
  return t;
}

// The two studios the glass paints for itself, 1024 x 512 equirects baked into a PMREM on the first frame their look
// draws. Three's equirectUv: u 0.25 = -z (the tail), 0.5 = +x, 0.75 = +z (the player and the page camera); rows are
// elevation. Each source is placed for what this case mirrors from the page's 22-degree follow camera and the lab views.
function canvasStudio(THREE, fill, paint) {
  const W = 1024, H = 512;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d");
  g.fillStyle = fill; g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = "lighter";
  const row = (e) => (0.5 - e / 180) * H, col = (u) => u * W;
  // a vertical gradient band, stops running top (e1) -> bottom (e0); blur in canvas px
  const band = (u0, u1, e0, e1, stops, blur) => {
    g.filter = `blur(${blur}px)`;
    const gr = g.createLinearGradient(0, row(e1), 0, row(e0));
    for (const [t, css] of stops) gr.addColorStop(t, css);
    g.fillStyle = gr; g.fillRect(col(u0), row(e1), col(u1) - col(u0), row(e0) - row(e1));
  };
  // a vertical strip with a horizontal falloff, clear at u0 and u1 and css at its centre, so a curved wall mirrors a
  // soft-edged softbox rather than a hard bar; blur in canvas px
  const column = (u0, u1, e0, e1, css, blur) => {
    g.filter = `blur(${blur}px)`;
    const gr = g.createLinearGradient(col(u0), 0, col(u1), 0);
    gr.addColorStop(0, "rgba(0,0,0,0)"); gr.addColorStop(0.5, css); gr.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = gr; g.fillRect(col(u0), row(e1), col(u1) - col(u0), row(e0) - row(e1));
  };
  paint(band, (css) => [[0, css], [1, css]], column);
  g.filter = "none"; g.globalCompositeOperation = "source-over";
  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
// studio: black so the stage stays dark. The desk mirrors +9..+15 deg toward the player, the key slip and the fallboard
// -18..-25, a vertical column -22..-30 all round, a rim top seen across the case +2..+7 behind. Round 2: the softbox
// peaks at rgb(110,110,114) (was 170) and ends at 17 deg (was 21), falling to a tenth by 11 deg, so the desk keeps a
// sheen along its top edge and none over the strings, and the raised lid's band is no longer the brightest thing in
// the lab hero; the tall strips behind are rgb(150,156,175) (was 236,240,255), 1.5x wider with a horizontal falloff and
// blurred 8 px (was 2), since the bass curve drew the u 0.155 strip as a hard bar like a rod; the side strips blur 6 px.
function acrylicStudio(THREE) {
  return canvasStudio(THREE, "#000", (band, flat, column) => {
    band(0, 1, 58, 90, flat("rgb(12,13,16)"), 16);                                                          // faint ceiling
    band(0.62, 0.88, 5, 17, [[0, "rgba(0,0,0,0)"], [0.12, "rgb(110,110,114)"], [0.35, "rgb(40,40,42)"],
      [0.7, "rgb(10,10,11)"], [1, "rgba(0,0,0,0)"]], 4);                                                   // softbox behind the camera: the desk's top edge
    band(0.64, 0.86, -28, -16, [[0, "rgba(0,0,0,0)"], [0.5, "rgb(60,60,66)"], [1, "rgba(0,0,0,0)"]], 6);   // low card in front: key slip, fallboard
    band(0.60, 0.90, 39, 45, flat("rgb(255,250,242)"), 3);                                                 // strip overhead in front: the up-front edges
    band(0.12, 0.38, 2, 7, flat(STUDIO_HORIZON), 2);                                                       // cool horizon strip behind: rim tops, lid edges
    for (const u of [0.161, 0.336]) column(u - 0.009, u + 0.009, -60, 40, "rgb(150,156,175)", 8);          // tall strips behind: legs, lyre, rim walls
    for (const u of [0.020, 0.455]) band(u, u + 0.012, -40, 30, flat("rgb(200,206,220)"), 6);              // tall strips at the sides
  });
}
// smoked: a dim violet room. The warm and cool strips sit at the host's own strip azimuths and skip +-14 deg, where the
// far tail wall drew a floating "pole"; they blur 6 px (round 1: 2). The desk glint is full from 16 to 18 deg with a
// crisp top and fades out by 15 deg, so it lands on the desk's top edge (round 1: a soft streak at 12-14.5 deg, across
// the strings and the chord etch in the 9:16 view).
function smokeStudio(THREE) {
  return canvasStudio(THREE, "rgb(5,4,9)", (band, flat) => {
    band(0.05, 0.45, 2, 30, [[0, "rgba(0,0,0,0)"], [0.6, "rgb(150,138,190)"], [1, "rgba(0,0,0,0)"]], 14);  // violet skylight: tops
    band(0.03, 0.47, -26, -6, [[0, "rgba(0,0,0,0)"], [0.5, "rgb(96,88,124)"], [1, "rgba(0,0,0,0)"]], 14);  // dim floor behind: edge-on walls
    band(0.0, 1.0, -4, 8, [[0, "rgba(0,0,0,0)"], [0.5, "rgb(54,50,72)"], [1, "rgba(0,0,0,0)"]], 14);       // nebula horizon: silhouettes
    band(0.58, 0.92, -34, -10, [[0, "rgba(0,0,0,0)"], [0.5, "rgb(150,140,175)"], [1, "rgba(0,0,0,0)"]], 14); // floor card: fronts
    const glint = `rgba(235,228,245,${SMOKE.glint})`;
    if (SMOKE.glint > 0) band(0.70, 0.80, 15, 18, [[0, glint], [0.667, glint], [1, "rgba(235,228,245,0)"]], 0);  // the desk glint (SMOKE.glint)
    band(0.60, 0.90, 40, 46, flat("rgb(220,220,235)"), 2);                                                  // overhead strip: top edges
    for (const [e0, e1] of [[-46, -14], [14, 48]]) {
      band(0.022, 0.040, e0, e1, flat("rgb(255,222,185)"), 6);                                               // warm, at the host's -x strip
      band(0.430, 0.448, e0, e1, flat("rgb(185,205,255)"), 6);                                               // cool, at the host's +x strip
    }
  });
}
const GLASS_ENV_PAINTERS = { studio: acrylicStudio, smoke: smokeStudio };

export default {
  id: "glass-piano",
  name: "Crystal Grand",
  keyStyle: KEY_STYLE,
  hints: HINTS,

  create(ctx) {
    const { THREE, scene } = ctx;
    const B = makeBuilders(THREE);
    const KEY = ctx.KEY || { first: 21, last: 108 };
    const first = KEY.first, N = KEY.last - KEY.first + 1;
    const keyX = ctx.keyX || ((m) => (m - 21 - 43.5) * 52 / 88);
    const span = ctx.span || {};
    const left = span.left ?? keyX(first) - 0.5, right = span.right ?? keyX(KEY.last) + 0.5;
    const options = { lid: "auto", glass: "crystal", desk: true, edge: 1, ...(ctx.options || {}) };
    let heroPose = false;  // the lab's hero view poses the lid on its long prop; the page takes it off so action and sky stay clear
    const fallbackColor = (m, vel, target) => target.setHSL(((m % 12) * 7 % 12) / 12, 0.9, 0.5);
    const noteColor = ctx.noteColor || fallbackColor;
    const floorY = ctx.floorY ?? G.floorY;

    const group = new THREE.Group();
    group.name = "instrument:glass-piano";
    group.position.x = (left + right) / 2;
    group.scale.setScalar((right - left) / 52);
    scene.add(group);
    const geos = [], mats = [], texs = [];
    const add = (mesh) => { group.add(mesh); return mesh; };

    // ---------------------------------------------------------------- materials --
    const edgeU = { value: new THREE.Color() }, edgePow = { value: EDGE.pow };   // applyEdge: the look's edge x the edge option
    const strikeU = { value: new THREE.Color(0, 0, 0) }, strikePow = { value: EDGE.strikePow };
    let edgeScale = 1, strikeMul = 1;
    // The look the glass is drawn in, and the shader its programs compile for. applyGlass sets both before needsUpdate;
    // the cache key and the hook read glassShader in the same getProgram call, so a program can never be filed under
    // another look's key.
    let glassLook = "crystal", glassShader = "crystal";
    // the light guide's line of light across the case (LG): rgb per texel, half float so the faint tail never bands
    const LINE_X0 = -G.halfW - 0.5, LINE_W = 2 * G.halfW + 1, LINE_DX = LINE_W / LG.texels;
    const lineData = new Uint16Array(LG.texels * 4);
    const lineTex = new THREE.DataTexture(lineData, LG.texels, 1, THREE.RGBAFormat, THREE.HalfFloatType);
    lineTex.magFilter = lineTex.minFilter = THREE.LinearFilter;   // the sampler interpolates between texels
    lineTex.needsUpdate = true;
    texs.push(lineTex);
    const lgRestBase = new THREE.Color(EDGE.color).multiplyScalar(LG.rest);
    const lgU = {
      uLgLine: { value: lineTex },
      uLgFrame: { value: new THREE.Matrix4() },
      uLgScale: { value: 1 },
      uLgRest: { value: lgRestBase.clone() },
      uLgMask: { value: new THREE.Vector4(LG.kLo, LG.kHi, 1 / LG.reach, LG.restFar) },
      uLgSpan: { value: new THREE.Vector4(LINE_X0, 1 / LINE_W, LG.zFront, G.bedBottom) },
    };
    const lensEdgeU = { value: new THREE.Color(1, 1, 1).multiplyScalar(LENS.edgeGain) };
    // EVERY look's uniforms, installed on every compile whatever the look (the rules above GLASS_LOOKS); crystal declares
    // only its four, and three uploads only what a program declares, so the rest cost crystal nothing
    const glassU = {
      uEdge: edgeU, uEdgePow: edgePow, uStrike: strikeU, uStrikePow: strikePow,
      uLensEdge: lensEdgeU, uLensAdd: { value: LENS.addMM / MM }, uLensPow: { value: LENS.pow }, uLensBlur: { value: LENS.blur },
      uLensPipe: { value: LENS.pipe },
      uSatinRough: { value: new THREE.Vector2(SATIN.polishRough, SATIN.rough) },
      uSatinShape: { value: new THREE.Vector4(SATIN.curv[0], SATIN.curv[1], SATIN.graze[0], SATIN.graze[1]) },
      uSatinBlur: { value: SATIN.blur }, uSatinVeil: { value: SATIN.veil }, uSatinSpecCap: { value: SATIN.specCap },
      ...lgU,
    };
    // each glass program's uniforms: the renderer puts its transmission render target's texture in them (see dispose)
    const glassUniforms = new Set();
    // one program per look, three materials: the case walls (rim, key blocks, keybed, key slip, belly, fallboard, desk rest,
    // lid, prop), the thicker legs/lyre/pedal box, and the music desk (its own only so smoked can give it its real 10.4 mm
    // pane; in every other look it equals the walls). part = the light guide's (rest share, line share) for this material.
    const makeGlass = (thickness, part, win = [0, 0, 0, 0]) => {
      const m = new THREE.MeshPhysicalMaterial({
        color: GLASS.color, roughness: GLASS.roughness, metalness: 0, transmission: 1, thickness, ior: GLASS.ior,
        attenuationColor: new THREE.Color(GLASS.attenuationColor), attenuationDistance: GLASS.attenuationDistance,
        specularIntensity: 1, clearcoat: 0.6, clearcoatRoughness: 0.04,
      });
      const own = {                                                                 // one program, a value per material
        uLgPart: { value: new THREE.Vector2(part[0], part[1]) },
        uSatinWin: { value: new THREE.Vector4(win[0], win[1], win[2], win[3]) },    // satin: the music desk's feathered border
      };
      m.onBeforeCompile = (sh) => {
        glassUniforms.add(sh.uniforms);
        Object.assign(sh.uniforms, glassU, own);
        LOOK_GLSL[glassShader](sh, THREE);
      };
      m.customProgramCacheKey = () => "glass-piano-" + glassShader;   // crystal and fast: "glass-piano-crystal", as always
      return m;
    };
    const glass = makeGlass(GLASS.thickness, LG.partCase), glassLeg = makeGlass(GLASS.legThickness, LG.partLegs);
    // the music desk's slab is x -15..15, y -0.2 (its lip) .. 9.5 in its own frame (deskGeo below); satin feathers its
    // top only, so its sides and bottom are given far outside the desk
    const glassDesk = makeGlass(GLASS.thickness, LG.partCase, [1000, -1000, 9.5, SATIN.feather]);
    const gold = new THREE.MeshPhysicalMaterial({ color: 0xc8a052, metalness: 0.55, roughness: 0.36, clearcoat: 0.5, clearcoatRoughness: 0.25 });
    const brass = new THREE.MeshPhysicalMaterial({ color: 0xd9b46c, metalness: 0.7, roughness: 0.28 });
    const grain = grainTexture(THREE);
    texs.push(grain);
    const spruce = new THREE.MeshPhysicalMaterial({ color: 0x957250, map: grain, roughness: 0.66 });
    const maple = new THREE.MeshPhysicalMaterial({ color: 0xc49a66, roughness: 0.55 });
    const dark = new THREE.MeshPhysicalMaterial({ color: 0x2b2019, roughness: 0.5, clearcoat: 0.4 });
    const steel = new THREE.MeshPhysicalMaterial({ color: 0xaeb4bd, metalness: 0.6, roughness: 0.3 });
    const felt = new THREE.MeshPhysicalMaterial({ color: 0xe6e0d2, roughness: 0.9, sheen: 0.8, sheenRoughness: 0.6, sheenColor: new THREE.Color(0xffffff) });
    felt.onBeforeCompile = (sh) => {
      sh.vertexShader = "attribute vec3 aGlow;\nattribute float aTip;\nvarying vec3 vGlow;\n" + sh.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvGlow = aGlow * aTip;");
      sh.fragmentShader = "varying vec3 vGlow;\n" + sh.fragmentShader.replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += vGlow;");
    };
    felt.customProgramCacheKey = () => "glass-piano-felt";
    // The strings must stay in the OPAQUE list: a transparent material drops out of three's transmission pass, and the
    // whole case is transmission 1 — the lit strings would vanish behind the desk and the rim. CustomBlending gives plain
    // "over" compositing without the transparent flag (three applies the blend either way), so a string at rest, alpha 1,
    // composites exactly as the opaque ribbon it replaces, and only a vibrating one goes translucent.
    const strU = {
      uRes: { value: new THREE.Vector2(1920, 1080) },
      uTime: { value: 0 },
      uNote: { value: new Float32Array(N * 4) },        // rgb = the note's light, w = its swing amplitude in units
      uMinPx: { value: STRING_MIN_PX }, uRestHalf: { value: STRING_W / 2 }, uWobble: { value: VIB_WOBBLE },
      uDensCap: { value: BLUR_DENS_CAP }, uDensNorm: { value: BLUR_DENS_NORM }, uConserve: { value: BLUR_CONSERVE },
    };
    const stringMat = new THREE.ShaderMaterial({
      uniforms: strU, vertexShader: stringVert(N), fragmentShader: STRING_FRAG,
      transparent: false, blending: THREE.CustomBlending, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      depthWrite: false, side: THREE.DoubleSide,
    });
    stringMat.customProgramCacheKey = () => "glass-piano-strings";
    mats.push(glass, glassLeg, glassDesk, gold, brass, spruce, maple, dark, steel, felt, stringMat);

    // Studio and smoked mirror a studio the instrument paints itself (GLASS_ENV_PAINTERS), baked into a PMREM on the first
    // frame the look draws. An instrument reaches the renderer only inside a draw, so a degenerate triangle drawn first in
    // the opaque list does it (the concert grand's frame hook), with a PMREMGenerator disposed at once (the renderer's own
    // would keep its 768x1024 half-float ping-pong target for the page's life). Three's transmission pass draws the opaque
    // list first, so the glass already has the map when it compiles that frame: one compile, never an env-less one. One
    // painted map is held at a time (6 MB, until dispose or another painted look); the hook is hidden, and draws nothing,
    // whenever no bake is pending, so crystal never sees it. A remount re-bakes (the generator's programs go with it).
    let privateEnv = null, bakeWant = null;   // { id, target } held; the painter id the next frame should bake
    const bakeGeo = new THREE.BufferGeometry();
    bakeGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(9), 3));
    geos.push(bakeGeo);
    const bakeHook = add(new THREE.Mesh(bakeGeo, dark));
    bakeHook.name = "glass studio-map hook";
    bakeHook.frustumCulled = false;
    bakeHook.renderOrder = -1e6;
    bakeHook.visible = false;
    bakeHook.onBeforeRender = (renderer) => {
      const id = bakeWant;
      bakeWant = null;
      bakeHook.visible = false;
      if (!id || (privateEnv && privateEnv.id === id)) return;
      const src = GLASS_ENV_PAINTERS[id](THREE), pmrem = new THREE.PMREMGenerator(renderer);
      const target = pmrem.fromEquirectangular(src);
      pmrem.dispose();
      src.dispose();
      if (privateEnv) privateEnv.target.dispose();
      privateEnv = { id, target };
      if (GLASS_LOOKS[glassLook].env === id) applyGlass(glassLook);   // hand it to the glass before the glass draws
    };

    // A look is applied whole: every field any look sets comes from its record, so nothing of the last look survives a
    // switch, and crystal and fast are their old values exactly. Setters that toggle a define (transmission, clearcoat,
    // dispersion) bump the material version only when they cross 0, and needsUpdate is set either way.
    function applyGlass(mode) {
      const id = Object.hasOwn(GLASS_LOOKS, mode) ? mode : "crystal";   // an unknown or stale saved value mounts crystal
      const L = GLASS_LOOKS[id];
      glassLook = id;
      glassShader = L.shader;
      strikeMul = L.strikeMul;
      let env = null, stale = null;
      if (L.env === "host") env = ctx.envMap || scene.environment || null;   // the host owns and disposes it
      else if (L.env) {
        if (privateEnv && privateEnv.id === L.env) env = privateEnv.target.texture;
        else {
          if (privateEnv) { stale = privateEnv.target; privateEnv = null; }   // freed below, once no glass holds it
          bakeWant = L.env;
          bakeHook.visible = true;
        }
      }
      if (!L.env || L.env === "host") { bakeWant = null; bakeHook.visible = false; }
      for (const m of [glass, glassLeg, glassDesk]) {
        const leg = m === glassLeg;
        m.transmission = L.transmission;
        m.transparent = L.transparent;               // false for every look but fast: the glass stays out of the transparent list
        m.opacity = L.opacity;
        m.depthWrite = L.depthWrite;
        m.color.set(L.color);
        m.roughness = leg && L.legRoughness != null ? L.legRoughness : L.roughness;
        m.ior = L.ior;
        m.dispersion = L.dispersion;
        m.thickness = leg ? L.legThickness : m === glassDesk && L.deskThickness != null ? L.deskThickness : L.thickness;
        m.attenuationColor.set(L.attenuationColor);
        m.attenuationDistance = leg && L.legAttenuationDistance != null ? L.legAttenuationDistance : L.attenuationDistance;
        m.specularIntensity = L.specularIntensity;
        m.clearcoat = L.clearcoat;
        m.clearcoatRoughness = L.clearcoatRoughness;
        m.envMap = env;
        m.envMapIntensity = leg && L.legEnvMapIntensity != null ? L.legEnvMapIntensity
          : m === glassDesk && L.deskEnvMapIntensity != null ? L.deskEnvMapIntensity : L.envMapIntensity;
        m.side = leg && L.legSide === "double" ? THREE.DoubleSide : THREE.FrontSide;   // the foot (see GLASS_LOOKS)
        m.needsUpdate = true;
      }
      if (stale) stale.dispose();
      prop.material = L.propOnLegs ? glassLeg : glass;   // the light guide: the prop is a rod, so it takes the legs' part
      if (id === "lightguide") lgFrame(); else clearLine();
      applyEdge();
    }
    function applyEdge() {
      edgeScale = Math.max(0, Math.min(2, Number(options.edge ?? 1) || 0));
      const L = GLASS_LOOKS[glassLook];
      edgeU.value.set(L.edgeColor).multiplyScalar(L.edgeGain).multiplyScalar(edgeScale);
      lensEdgeU.value.setScalar(LENS.edgeGain * edgeScale);
      lgU.uLgRest.value.copy(lgRestBase).multiplyScalar(edgeScale);
    }

    // ---------------------------------------------------------------- the plan --
    const outline = caseOutline(THREE);                 // U path, front-left round to front-right
    const innerRim = insetPoly(outline, G.rimTh);        // same indices
    const hitchPoly = insetPoly(outline, G.rimTh + 1.6);
    const strutPoly = insetPoly(outline, G.rimTh + 1.3);

    // ---------------------------------------------------------------- crystal body (one draw) --
    const W = G.halfW, bi = G.blockInner;
    // The panes over the action are windows, a per-vertex flag, aPane (paneVertex, above LOOK_GLSL): 1 on the key slip,
    // fallboard, desk rest and music desk, 2 on the key blocks (only satin reads 2: it polishes them), 0 on everything
    // else. Satin keeps the windows polished, smoked lets more light through them, prism and the light guide keep them
    // 15 mm. Every glass geometry carries it; no geometry, draw or crystal pixel changes for it.
    const pane = (g, flag = 1) => { g.userData.pane = flag; return g; };
    const setPane = (g, runs) => {                   // runs: [[vertex count, flag], ...] in merge order, or one flag (true = 1)
      const a = new Float32Array(g.attributes.position.count);
      if (Array.isArray(runs)) { let o = 0; for (const [n, f] of runs) { if (f) a.fill(f, o, o + n); o += n; } } else if (runs) a.fill(+runs);
      g.setAttribute("aPane", new THREE.BufferAttribute(a, 1));
    };
    const vertsOf = (g) => (g.index ? g.index.count : g.attributes.position.count);   // B.merge flattens to these
    const bodyParts = [
      B.sweep(pathRings(outline, false), rrect(-G.rimTh, 0, G.rimBottom, G.rimTop, 0.45), true),               // rim
      pane(B.slabZ(G.blockFront, G.front, -W, -bi, G.bedBottom, 1.45, 0.45), 2),                                // key blocks
      pane(B.slabZ(G.blockFront, G.front, bi, W, G.bedBottom, 1.45, 0.45), 2),
      B.slabX(-bi, bi, 3.2, G.front, G.bedBottom, G.bedTop, 0.1),                                               // keybed
      pane(B.slabX(-bi, bi, G.blockFront, 3.2, G.bedBottom, -0.28, 0.18)),                                      // key slip
      B.slabX(-W, W, G.front, G.gap0, G.rimBottom, G.bedBottom, 0.1),                                           // belly
      pane(B.slabX(-bi, bi, -3.72, -4.95, -0.55, 2.75, 0.35)),                                                  // fallboard
      pane(B.slabX(-15.5, 15.5, -5.0, -6.3, G.plateY1, 2.9, 0.2)),                                              // desk rest
    ];
    const bodyRuns = bodyParts.map((g) => [vertsOf(g), g.userData.pane || 0]);
    const leg = (x, z, top) => {
      const h = top - floorY - 0.9, pts = [[2.2, 0], [2.2, -0.5], [1.6, -1.2], [1.85, -4], [1.25, -h + 2.6], [1.55, -h + 0.5], [1.4, -h]];
      return B.at(new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), 28), x, top, z);
    };
    // legs, lyre and pedal box: one draw in the thicker-walled acrylic, so they read as crystal columns
    const legParts = [leg(-28.9, -0.4, G.bedBottom), leg(28.9, -0.4, G.bedBottom), leg(-8, -64, G.rimBottom)];
    const lyreTop = G.rimBottom, boxTop = floorY + 3.0;
    for (const x of [-2.9, 2.9]) legParts.push(B.at(new THREE.CylinderGeometry(0.42, 0.52, lyreTop - boxTop, 16), x, (lyreTop + boxTop) / 2, -5.8));
    legParts.push(B.slabX(-5.8, 5.8, -4.1, -7.6, floorY + 1.1, boxTop, 0.4));                                    // pedal box
    for (const x of [-4.2, 4.2]) {                                                                               // lyre braces
      const g = new THREE.CylinderGeometry(0.22, 0.22, 1, 10);
      const a = [x, boxTop, -7.2], b = [x * 0.6, lyreTop, -12.5];
      const len = Math.hypot(b[1] - a[1], b[2] - a[2]);
      g.scale(1, len, 1);
      g.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.atan2(b[2] - a[2], b[1] - a[1])));
      g.applyMatrix4(new THREE.Matrix4().makeRotationZ(-Math.atan2(b[0] - a[0], b[1] - a[1])));
      g.translate((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
      legParts.push(g);
    }
    // only the three legs (the first three parts) show their far faces in the DoubleSide looks (NEAR_ONLY, above
    // LOOK_GLSL); the lyre posts, braces and pedal box are near-only
    const legRuns = legParts.map((g, i) => [vertsOf(g), i < 3 ? 0 : NEAR_ONLY]);
    const bodyGeo = B.merge(bodyParts), legGeo = B.merge(legParts);
    setPane(bodyGeo, bodyRuns);
    { // satin's cheeks: the rim (the first body part) in front of SATIN.cheekZ (CHEEK, above LOOK_GLSL)
      const a = bodyGeo.attributes.aPane.array, p = bodyGeo.attributes.position;
      for (let i = 0; i < bodyRuns[0][0]; i++) if (p.getZ(i) > SATIN.cheekZ) a[i] = CHEEK;
    }
    setPane(legGeo, legRuns);
    const body = add(new THREE.Mesh(bodyGeo, glass));
    add(new THREE.Mesh(legGeo, glassLeg));
    geos.push(bodyGeo, legGeo);

    // music desk (glass) and its etched chord name
    const deskGroup = new THREE.Group();
    deskGroup.position.set(0, 2.9, -5.6);
    deskGroup.rotation.x = -14 * DEG;
    add(deskGroup);
    const deskGeo = B.merge([B.slabX(-15, 15, 0.22, -0.22, 0, 9.5, 0.12), B.slabX(-15, 15, 0.95, -0.22, -0.2, 0.45, 0.15)]);
    setPane(deskGeo, true);
    deskGroup.add(new THREE.Mesh(deskGeo, glassDesk));
    geos.push(deskGeo);
    const etchCanvas = document.createElement("canvas");
    etchCanvas.width = 1024;
    etchCanvas.height = 256;
    const etchTex = new THREE.CanvasTexture(etchCanvas);
    etchTex.colorSpace = THREE.SRGBColorSpace;
    texs.push(etchTex);
    const etchMat = new THREE.MeshBasicMaterial({ map: etchTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: 0x000000, toneMapped: true });
    mats.push(etchMat);
    const etchGeo = new THREE.PlaneGeometry(22, 5.5);
    geos.push(etchGeo);
    const etch = new THREE.Mesh(etchGeo, etchMat);
    etch.position.set(0, 5.4, 0.3);
    etch.renderOrder = 2;
    deskGroup.add(etch);

    // lid and prop (glass), hinged on the spine
    const lidPoly = resample(clipPolyZ(outline, G.lidFrontZ), 1.0, true).map((p) => [p[0] + W, p[1]]);
    const lidGeo = B.merge([
      B.sweep(pathRings(lidPoly, true), [[-0.7, 0], [-0.05, 0], [0.09, 0.06], [0.15, 0.2], [0.15, 0.35], [0.09, 0.49], [-0.05, 0.55], [-0.7, 0.55]], false),
      B.capSlab(insetPoly(lidPoly, 0.7), 0, G.lidTh),
    ]);
    geos.push(lidGeo);
    setPane(lidGeo, false);
    const lid = add(new THREE.Mesh(lidGeo, glass));
    lid.position.set(-W, G.rimTop, 0);
    const propGeo = new THREE.CylinderGeometry(0.3, 0.3, 1, 14);
    setPane(propGeo, NEAR_ONLY);   // near faces only when the light guide hangs it on the DoubleSide leg glass
    geos.push(propGeo);
    const prop = add(new THREE.Mesh(propGeo, glass));
    let propBase = [24, -36];
    { let best = Infinity;
      for (const p of insetPoly(outline, G.rimTh / 2)) if (p[0] > 0 && Math.abs(p[1] + 36) < best) { best = Math.abs(p[1] + 36); propBase = p; } }
    function applyLid(want) {
      // auto: lid off on the page (render 2026-09-15: even the short prop veiled the action in 9:16), long prop for the hero
      let mode = want === "auto" ? (heroPose ? "long" : "off") : want;
      if (portrait && mode === "long") mode = "short";  // judge 2026-09-15: a raised lid sat in the air the 9:16 note bars need
      const th = (LID_ANGLE[mode] ?? 10) * DEG;
      lid.visible = mode !== "off";
      lid.rotation.z = th;
      prop.visible = mode === "long" || mode === "short";
      const len = (propBase[0] + W) * Math.sin(th);
      prop.scale.set(1, Math.max(len, 0.01), 1);
      prop.rotation.z = th;
      prop.position.set(propBase[0] - Math.sin(th) * len / 2, G.rimTop + Math.cos(th) * len / 2, propBase[1]);
    }

    // ---------------------------------------------------------------- plate, soundboard, rails --
    const plateParts = [
      B.slabX(-30.3, 30.3, -5.0, G.gap0, G.plateY0, G.plateY1, 0.25),
      B.slabX(-30.4, 30.4, G.gap1, G.gap1 - 1.6, G.plateY0, G.plateY1, 0.25),
      B.sweep(pathRings(clipLineZ(innerRim, G.gap0), false), rrect(-2.6, 0, G.plateY0, G.plateY1, 0.2), true),
    ];
    for (const [x0, dx] of [[-11.3, 0.45], [6.5, 0.15], [19, 0]]) {
      const d = norm2(dx, -1);
      let L = 2;
      while (L < 90 && inside(strutPoly, x0 + d[0] * L, G.gap1 - 1.6 + d[1] * L)) L += 0.5;
      plateParts.push(B.bar(x0, G.gap1 - 1.2, x0 + d[0] * L, G.gap1 - 1.6 + d[1] * L, 0.6, G.plateY0, G.plateY1, 0.2));
    }
    const plateGeo = B.merge(plateParts);
    geos.push(plateGeo);
    add(new THREE.Mesh(plateGeo, gold));

    const boardPoly = clipPolyZ(innerRim, G.gap0);
    const boardShape = new THREE.Shape(boardPoly.map((p) => new THREE.Vector2(p[0], -p[1])));
    const boardGeo = new THREE.ShapeGeometry(boardShape, 1);
    boardGeo.rotateX(-Math.PI / 2);
    boardGeo.translate(0, G.boardY, 0);
    geos.push(boardGeo);
    add(new THREE.Mesh(boardGeo, spruce));

    // wood: hammer flange rail, rest rail, damper guide rail
    const hx0 = -26, pitch = 52 / N;
    const hammerX = (i) => hx0 + (i + 0.5) * pitch;
    const pivotZ = G.strikeZ + G.shank;
    const damperCount = Math.max(0, Math.min(N, 88 - first + 1));
    const woodGeo = B.merge([
      B.slabX(-26.6, 26.6, pivotZ + 0.5, pivotZ - 0.5, -1.6, -1.1, 0.12),
      B.slabX(-26.6, 26.6, -10.4, -11.2, -1.4, -1.08, 0.1),
      B.slabX(-26.4, hammerX(damperCount - 1) + 0.5, G.damperZ + 0.5, G.damperZ - 0.5, 0.35, 0.75, 0.1),
    ]);
    geos.push(woodGeo);
    add(new THREE.Mesh(woodGeo, dark));

    const brassParts = [];
    for (const x of [-26.9, -13.3, 13.3, 26.9]) brassParts.push(B.slabZ(-6.2, -8.8, x - 0.15, x + 0.15, G.bedBottom, -1.12, 0.05));
    for (const z of [-20, -42]) brassParts.push(B.slabZ(z + 1.2, z - 1.2, -W - 0.12, -W + 0.5, G.rimTop - 0.4, G.rimTop + 0.08, 0.08));
    const caster = (x, z) => B.at(new THREE.LatheGeometry([[0, 0], [1.2, 0], [1.5, 0.35], [1.45, 0.8], [1.1, 0.95], [0, 0.95]].map((p) => new THREE.Vector2(p[0], p[1])), 20), x, floorY, z);
    brassParts.push(caster(-28.9, -0.4), caster(28.9, -0.4), caster(-8, -64));
    const brassGeo = B.merge(brassParts);
    geos.push(brassGeo);
    add(new THREE.Mesh(brassGeo, brass));

    // ---------------------------------------------------------------- strings and pins --
    const strings = [];     // [key index, x front, y, z pin, x back, z back]
    const keyStr0 = new Uint16Array(N), keyStrN = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      const m = first + i, n = m <= 28 ? 1 : m <= 47 ? 2 : 3, bass = m < 48;
      const raw = 2.2 * Math.pow(1.94, (108 - m) / 12);
      let L = 62 * (1 - Math.exp(-raw / 62));
      const d = norm2(bass ? 0.45 : 0, -1), y = bass ? G.bassStrY : G.strY;
      keyStr0[i] = strings.length;
      keyStrN[i] = n;
      for (let s = 0; s < n; s++) {
        const xf = hammerX(i) + (n === 1 ? 0 : (s - (n - 1) / 2) * (n === 2 ? 0.16 : 0.14));
        let l = L;
        while (l > 1 && !inside(hitchPoly, xf + d[0] * l, G.agraffeZ + d[1] * l)) l -= 0.4;
        strings.push([i, xf, y, -5.7 - (strings.length % 3) * 1.1, xf + d[0] * l, G.agraffeZ + d[1] * l]);
      }
    }
    // A string is a screen-space ribbon: its width is set in the vertex shader, so it can widen into a vibration blur
    // without ever becoming a hairline that aliases. The speaking length is subdivided so sin(pi u) has somewhere to go;
    // the pin-to-agraffe stretch never moves and stays dimmed to 0.6 as it always was.
    const NS = strings.length;
    const SPEAK_SPANS = 8;
    const NODES = 2 + SPEAK_SPANS + 1;                 // pin, agraffe | agraffe ... hitch
    const SV = NODES * 2, TRIS = (1 + SPEAK_SPANS) * 2;
    const sPos = new Float32Array(NS * SV * 3), sBase = new Float32Array(NS * SV * 3), sDir = new Float32Array(NS * SV * 3);
    const sParam = new Float32Array(NS * SV * 4), sVib = new Float32Array(NS * SV * 2);
    const sIdx = new Uint16Array(NS * TRIS * 3);
    strings.forEach(([i, xf, y, zp, xb, zb], k) => {
      const m = first + i;
      const base = m < 41 ? [0.13, 0.065, 0.028] : [0.15, 0.155, 0.17];
      const nodes = [[xf, G.plateY1 + 0.55, zp, 0, 0.6], [xf, y, G.agraffeZ, 0, 0.6]];
      for (let q = 0; q <= SPEAK_SPANS; q++) {
        const f = q / SPEAK_SPANS;
        nodes.push([mix(xf, xb, f), y, mix(G.agraffeZ, zb, f), f, 1]);
      }
      const dir = (a, b) => { const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], l = Math.hypot(d[0], d[1], d[2]) || 1; return [d[0] / l, d[1] / l, d[2] / l]; };
      const d0 = dir(nodes[0], nodes[1]), d1 = dir(nodes[2], nodes[NODES - 1]);
      const l = k - keyStr0[i], n = keyStrN[i];                              // this string's place in its unison group
      const phase = (k * 2.39996323) % (2 * Math.PI);
      const om = 2 * Math.PI * overPitch(m, VIB_HZ_BASS, VIB_HZ_TREBLE) * (1 + VIB_DETUNE * (l - (n - 1) / 2));
      const v0 = k * SV;
      for (let q = 0; q < NODES; q++) {
        const nd = nodes[q], d = q < 2 ? d0 : d1;
        for (let side = 0; side < 2; side++) {
          const v = v0 + q * 2 + side, o3 = v * 3;
          sPos[o3] = nd[0]; sPos[o3 + 1] = nd[1]; sPos[o3 + 2] = nd[2];
          sBase[o3] = base[0] * nd[4]; sBase[o3 + 1] = base[1] * nd[4]; sBase[o3 + 2] = base[2] * nd[4];
          sDir[o3] = d[0]; sDir[o3 + 1] = d[1]; sDir[o3 + 2] = d[2];
          const o4 = v * 4;
          sParam[o4] = nd[3]; sParam[o4 + 1] = side ? 1 : -1; sParam[o4 + 2] = nd[4]; sParam[o4 + 3] = i;
          sVib[v * 2] = phase; sVib[v * 2 + 1] = om;
        }
      }
      let ti = k * TRIS * 3;
      const quad = (a) => { sIdx[ti++] = a; sIdx[ti++] = a + 2; sIdx[ti++] = a + 1; sIdx[ti++] = a + 1; sIdx[ti++] = a + 2; sIdx[ti++] = a + 3; };
      quad(v0);
      for (let q = 0; q < SPEAK_SPANS; q++) quad(v0 + (2 + q) * 2);
    });
    const stringGeo = new THREE.BufferGeometry();
    stringGeo.setAttribute("position", new THREE.BufferAttribute(sPos, 3));
    stringGeo.setAttribute("aBase", new THREE.BufferAttribute(sBase, 3));
    stringGeo.setAttribute("aDir", new THREE.BufferAttribute(sDir, 3));
    stringGeo.setAttribute("aParam", new THREE.BufferAttribute(sParam, 4));
    stringGeo.setAttribute("aVib", new THREE.BufferAttribute(sVib, 2));
    stringGeo.setIndex(new THREE.BufferAttribute(sIdx, 1));
    stringGeo.computeBoundingSphere();
    geos.push(stringGeo);
    const stringMesh = add(new THREE.Mesh(stringGeo, stringMat));
    stringMesh.renderOrder = 1;                        // after the plate and soundboard, so it blends over them
    stringMesh.frustumCulled = false;
    const strViewport = new THREE.Vector4();
    stringMesh.onBeforeRender = (renderer) => {        // the pass actually drawing: the transmission target is its own size
      renderer.getCurrentViewport(strViewport);
      strU.uRes.value.set(strViewport.z, strViewport.w);
    };

    const pinGeo = new THREE.CylinderGeometry(0.075, 0.075, 0.55, 6);
    pinGeo.translate(0, 0.275, 0);
    geos.push(pinGeo);
    const pins = add(new THREE.InstancedMesh(pinGeo, steel, NS));
    const m4 = new THREE.Matrix4();
    strings.forEach(([, xf, , zp], k) => pins.setMatrixAt(k, m4.makeTranslation(xf, G.plateY1, zp)));
    pins.frustumCulled = false;

    // ---------------------------------------------------------------- hammers --
    const shankGeo = B.merge([
      B.at(new THREE.CylinderGeometry(0.075, 0.075, G.shank + 0.3, 6), 0, 0, -(G.shank + 0.3) / 2 + 0.15, Math.PI / 2),
      new THREE.BoxGeometry(0.3, 0.42, 0.6).translate(0, -0.1, 0.05),
    ]);
    const headGeo = B.sweep(pathRings([[-0.22, 0], [0.22, 0]], false), [[-0.2, 0.05], [0.2, 0.05], [0.2, 0.38], [0.3, 0.5], [0.355, 0.68], [0.35, 0.86], [0.31, 1.02], [0.24, 1.16], [0.14, 1.26], [0, 1.3], [-0.14, 1.26], [-0.24, 1.16], [-0.31, 1.02], [-0.35, 0.86], [-0.355, 0.68], [-0.3, 0.5], [-0.2, 0.38]], true);
    headGeo.translate(0, 0.09, -G.shank);
    { const p = headGeo.attributes.position, tip = new Float32Array(p.count);
      for (let v = 0; v < p.count; v++) { const s = clamp01((p.getY(v) - 0.09 - 0.5) / 0.8); tip[v] = 0.15 + 0.85 * s * s * (3 - 2 * s); }
      headGeo.setAttribute("aTip", new THREE.BufferAttribute(tip, 1)); }
    const glowArr = new Float32Array(N * 3);
    const glowAttr = new THREE.InstancedBufferAttribute(glowArr, 3).setUsage(THREE.DynamicDrawUsage);
    headGeo.setAttribute("aGlow", glowAttr);
    geos.push(shankGeo, headGeo);
    const shanks = add(new THREE.InstancedMesh(shankGeo, maple, N));
    const heads = add(new THREE.InstancedMesh(headGeo, felt, N));
    shanks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    heads.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    shanks.frustumCulled = heads.frustumCulled = false;
    const aTop = new Float32Array(N);
    for (let i = 0; i < N; i++) aTop[i] = Math.asin(Math.min(0.9, ((first + i < 48 ? G.bassStrY : G.strY) - 0.03 - G.restTop) / G.shank));

    // ---------------------------------------------------------------- dampers and pedals --
    const damperGeo = B.merge([
      B.slabX(-0.21, 0.21, 0.55, -0.55, 0, 0.85, 0.08),
      new THREE.CylinderGeometry(0.035, 0.035, 4.2, 5).translate(0, -2.1, 0),
    ]);
    geos.push(damperGeo);
    const dampers = damperCount > 0 ? add(new THREE.InstancedMesh(damperGeo, dark, damperCount)) : null;
    if (dampers) { dampers.instanceMatrix.setUsage(THREE.DynamicDrawUsage); dampers.frustumCulled = false; }
    const pedalGeo = B.sweep(pathRings([[0, 0], [0, 3.3]], false), rrect(-0.36, 0.36, -0.14, 0.14, 0.1), true);
    geos.push(pedalGeo);
    const pedals = add(new THREE.InstancedMesh(pedalGeo, brass, 3));
    pedals.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    const pedalY = floorY + 2.0;

    // ---------------------------------------------------------------- reactive state --
    const strikeT = new Float64Array(N).fill(-1e9), strikeV = new Float32Array(N), strikeCol = new Float32Array(N * 3);
    const held = new Uint8Array(N), topHit = new Uint8Array(N), ang = new Float32Array(N), shownAng = new Float32Array(N).fill(NaN);
    const lift = new Float32Array(damperCount), shownLift = new Float32Array(damperCount).fill(NaN), strLevel = new Float32Array(N);
    // The light envelope (the tuning table at the top): body = floor + prompt + aftersound, plus the strike flash. It is
    // integrated, not recomputed from the strike clock, so a re-strike carries the level it finds, a sound's end fades
    // instead of snapping, and a pedal PRESS never resurrects a note the page has already ended.
    const bFloor = new Float32Array(N), bPrompt = new Float32Array(N), bAfter = new Float32Array(N);
    const bodyLvl = new Float32Array(N), flash = new Float32Array(N), vibGate = new Float32Array(N), shownAmp = new Float32Array(N);
    const dampT = new Float32Array(N);                               // seconds into the damper's fade, 0 while it sounds
    const alive = new Uint8Array(N), seenStrike = new Uint32Array(N);
    const lastNote = new Float64Array(N).fill(-Infinity);            // the strike ring's high-water mark per key
    const riseT = new Float64Array(N).fill(-1e9);                    // the hammer is still in flight until then
    const tauPrompt = new Float32Array(N), tauAfter = new Float32Array(N), ampMax = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      tauPrompt[i] = overPitch(first + i, TAU_PROMPT_BASS, TAU_PROMPT_TREBLE);
      tauAfter[i] = overPitch(first + i, TAU_AFTER_BASS, TAU_AFTER_TREBLE);
      ampMax[i] = overPitch(first + i, AMP_BASS, AMP_TREBLE);
    }
    let seeded = false;
    const tmp = new THREE.Color(), edgeAcc = new THREE.Color(0, 0, 0), chordCol = new THREE.Color(0.6, 0.7, 1);
    const chordAcc = new THREE.Color();
    let chordN = 0, frameT = 0, active = true, pedalAng = 0, shownPedal = NaN, etchName = null, etchLevel = 0, etchFlash = 0;
    let framing = ctx.framing || null;
    let portrait = isPortrait(framing);

    // ---- the light guide's line (LG): strike events, rebuilt into lineData each frame while that look is on ----
    const lgX = new Float32Array(LG.events), lgT = new Float64Array(LG.events), lgC = new Float32Array(LG.events * 3);
    let lgHead = 0, lgCount = 0, lineLit = false;
    const lgAcc = new Float32Array(LG.texels * 3);
    const lgKeyX = new Float32Array(N);              // each key's centre in the instrument's own x
    for (let i = 0; i < N; i++) lgKeyX[i] = (keyX(first + i) - group.position.x) / group.scale.x;
    function lgPush(i, v, t0) {                       // light enters when the hammer reaches the string
      const e = lgHead;
      lgHead = (lgHead + 1) % LG.events;
      lgCount = Math.min(lgCount + 1, LG.events);
      const a = Math.pow(v, LG.velExp);
      lgX[e] = lgKeyX[i];
      lgT[e] = t0 + (0.055 - 0.037 * v);
      lgC[e * 3] = strikeCol[i * 3] * a; lgC[e * 3 + 1] = strikeCol[i * 3 + 1] * a; lgC[e * 3 + 2] = strikeCol[i * 3 + 2] * a;
    }
    function lgSplat(x, sig, r, g, b) {               // a gaussian of peak (r, g, b) and width sig, at instrument x
      const c = (x - LINE_X0) / LINE_DX - 0.5, rad = 3 * sig / LINE_DX;
      const j0 = Math.max(0, Math.ceil(c - rad)), j1 = Math.min(LG.texels - 1, Math.floor(c + rad));
      if (j0 > j1) return;
      const k = -0.5 * (LINE_DX / sig) * (LINE_DX / sig);
      for (let j = j0; j <= j1; j++) {
        const w = Math.exp(k * (j - c) * (j - c)), o = j * 3;
        lgAcc[o] += r * w; lgAcc[o + 1] += g * w; lgAcc[o + 2] += b * w;
      }
    }
    function lgFrame() {                              // world -> the instrument's own frame, and its scale, for the shader
      group.updateWorldMatrix(true, false);
      lgU.uLgFrame.value.copy(group.matrixWorld).invert();
      lgU.uLgScale.value = group.matrixWorld.getMaxScaleOnAxis();
    }
    function clearLine() {
      lgCount = 0; lgHead = 0;
      if (!lineLit) return;
      lineData.fill(0); lineTex.needsUpdate = true; lineLit = false;
    }
    function updateLine(t) {
      lgAcc.fill(0);
      let any = false;
      for (let e = 0; e < lgCount; e++) {
        const a = t - lgT[e];
        if (a < 0 || a > LG.life) continue;
        any = true;
        const o = e * 3, x = lgX[e], r = lgC[o], g = lgC[o + 1], b = lgC[o + 2];
        const pool = LG.pool * Math.exp(-a / LG.tauPool);
        lgSplat(x, LG.sigma, r * pool, g * pool, b * pool);
        const sig = LG.sigma + LG.spread * a, run = LG.run * Math.exp(-a / LG.tauRun) * Math.sqrt(LG.sigma / sig), d = LG.speed * a;
        lgSplat(x - d, sig, r * run, g * run, b * run);
        lgSplat(x + d, sig, r * run, g * run, b * run);
      }
      for (let i = 0; i < N; i++) {
        if (!(bodyLvl[i] > 0)) continue;
        any = true;
        const s = LG.sustain * bodyLvl[i], o = i * 3;
        lgSplat(lgKeyX[i], LG.sigma, strikeCol[o] * s, strikeCol[o + 1] * s, strikeCol[o + 2] * s);
      }
      if (!any && !lineLit) return;
      const half = THREE.DataUtils.toHalfFloat;
      for (let j = 0; j < LG.texels; j++) {
        const o = j * 3;
        let r = lgAcc[o] * edgeScale, g = lgAcc[o + 1] * edgeScale, b = lgAcc[o + 2] * edgeScale;   // the edge option, then the caps
        const l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        if (l > LG.maxLuma) { const s = LG.maxLuma / l; r *= s; g *= s; b *= s; }
        const p = Math.max(r, g, b);
        if (p > LG.maxChannel) { const s = LG.maxChannel / p; r *= s; g *= s; b *= s; }
        lineData[j * 4] = half(r); lineData[j * 4 + 1] = half(g); lineData[j * 4 + 2] = half(b);
      }
      lineTex.needsUpdate = true;
      lineLit = any;
    }

    // age > 0 seeds a sound that was already ringing when the crystal was mounted, or a strike the ring reports late: the
    // envelope is analytic, so it can simply be advanced. A strike never dips the light to dark first — whatever is still
    // showing above the new peak is folded into the prompt term and decays from there.
    function strike(m, vel, t0, age = 0) {
      const i = m - first;
      if (i < 0 || i >= N) return;
      const v = clamp01(vel > 1 ? vel / 127 : vel);
      const lit = bodyLvl[i] > 0;                     // this string is still showing light from a sound that has not ended
      strikeT[i] = t0;
      strikeV[i] = v;
      topHit[i] = 0;
      // The hammer's flight, 18-33 ms: a DARK string waits for it. A lit one must not — re-arming the gate on a re-strike
      // blanked the note to full dark for the frames before the new flash, throwing away the level the carry just kept.
      // The hammer arm still flies either way: it is animated off strikeT/strikeV, not off this gate.
      riseT[i] = lit ? -1e9 : t0 + (0.055 - 0.037 * v);
      noteColor(m, vel > 1 ? vel : vel * 127, tmp);
      strikeCol[i * 3] = tmp.r; strikeCol[i * 3 + 1] = tmp.g; strikeCol[i * 3 + 2] = tmp.b;
      if (glassLook === "lightguide") lgPush(i, v, t0);
      const peak = Math.pow(v, PEAK_EXP), fl = peak * mix(FLOOR_LO, FLOOR_HI, v), above = peak - fl;
      const carry = Math.max(0, bodyLvl[i] - peak);
      bFloor[i] = fl;
      bPrompt[i] = (above * (1 - AFTER_SHARE) + carry) * Math.exp(-age / tauPrompt[i]);
      bAfter[i] = above * AFTER_SHARE * Math.exp(-age / tauAfter[i]);
      bodyLvl[i] = bFloor[i] + bPrompt[i] + bAfter[i];
      flash[i] = Math.max(flash[i], Math.pow(v, FLASH_EXP) * Math.exp(-age / TAU_FLASH));
      vibGate[i] = 1;
      dampT[i] = 0;                                   // a strike during the damper's fade reopens the window
      strLevel[i] = -1;                                 // the colour changed with the note: write it even at the same level
      const fade = age > 0 ? Math.exp(-age / EDGE.tau) : 1;
      edgeAcc.r += tmp.r * v * EDGE.strikeGain * fade; edgeAcc.g += tmp.g * v * EDGE.strikeGain * fade; edgeAcc.b += tmp.b * v * EDGE.strikeGain * fade;
    }
    function visitPressed(st, m) {                     // the etched chord name is what the FINGERS hold, as it always was
      const i = m - first;
      if (i < 0 || i >= N) return;
      noteColor(m, st.vel, tmp);
      chordAcc.r += tmp.r; chordAcc.g += tmp.g; chordAcc.b += tmp.b;
      chordN++;
    }
    // Daniel's lettering picks (Outfit, Raleway, Jost; OFL). The host's display face leads when it passes one. The etch
    // redraws when a web font finishes loading, so a first chord drawn in the fallback face gets replaced.
    const displayFace = ctx.fonts && ctx.fonts.display ? `${ctx.fonts.display}, ` : "";
    const NAME_FONT = `500 128px ${displayFace}Outfit, Jost, Raleway, "Segoe UI", sans-serif`;
    const NNS_FONT = '400 52px Raleway, Jost, Outfit, "Segoe UI", sans-serif';
    const fontSet = typeof document !== "undefined" && document.fonts ? document.fonts : null;
    let etchNns = "";
    const onFontsLoaded = () => { if (etchName) drawEtch(etchName, etchNns); };
    if (fontSet && fontSet.addEventListener) fontSet.addEventListener("loadingdone", onFontsLoaded);
    function drawEtch(name, nns) {
      etchNns = nns || "";
      const g = etchCanvas.getContext("2d");
      g.clearRect(0, 0, 1024, 256);
      if (!name) { etchTex.needsUpdate = true; return; }
      g.fillStyle = "#ffffff";
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.font = NAME_FONT;
      g.fillText(name, 512, nns ? 104 : 128, 1000);
      if (nns) {
        g.globalAlpha = 0.6;
        g.font = NNS_FONT;
        g.fillText(nns, 512, 208, 1000);
        g.globalAlpha = 1;
      }
      etchTex.needsUpdate = true;
    }

    function reset() {
      strikeT.fill(-1e9); riseT.fill(-1e9); held.fill(0); ang.fill(0); lift.fill(0); strLevel.fill(-1);
      bFloor.fill(0); bPrompt.fill(0); bAfter.fill(0); bodyLvl.fill(0); flash.fill(0); vibGate.fill(0); dampT.fill(0);
      alive.fill(0); shownAmp.fill(0); strU.uNote.value.fill(0);
      seeded = false;
      edgeAcc.setRGB(0, 0, 0); etchLevel = 0; etchFlash = 0; pedalAng = 0;
      clearLine();
      glowArr.fill(0); glowAttr.needsUpdate = true;
      strikeU.value.setRGB(0, 0, 0);
      etchMat.color.setRGB(0, 0, 0);
      pose(0);
    }

    function pose(dt) {
      let moved = false;
      for (let i = 0; i < N; i++) {
        if (shownAng[i] === ang[i]) continue;
        shownAng[i] = ang[i];
        m4.makeRotationX(ang[i]);
        m4.setPosition(hammerX(i), G.pivotY, pivotZ);
        shanks.setMatrixAt(i, m4);
        heads.setMatrixAt(i, m4);
        moved = true;
      }
      if (moved) { shanks.instanceMatrix.needsUpdate = true; heads.instanceMatrix.needsUpdate = true; }
      if (dampers) {
        let lifted = false;
        for (let i = 0; i < damperCount; i++) {
          if (shownLift[i] === lift[i]) continue;
          shownLift[i] = lift[i];
          m4.makeTranslation(hammerX(i), (first + i < 48 ? G.bassStrY : G.strY) + 0.03 + lift[i] * 0.5, G.damperZ);
          dampers.setMatrixAt(i, m4);
          lifted = true;
        }
        if (lifted) dampers.instanceMatrix.needsUpdate = true;
      }
      if (shownPedal !== pedalAng) {
        shownPedal = pedalAng;
        for (let k = 0; k < 3; k++) {
          m4.makeRotationX(k === 2 ? pedalAng : 0);
          m4.setPosition(-2.4 + 2.4 * k, pedalY, -4.1);
          pedals.setMatrixAt(k, m4);
        }
        pedals.instanceMatrix.needsUpdate = true;
      }
    }

    applyGlass(options.glass);
    applyEdge();
    applyLid(options.lid);
    deskGroup.visible = options.desk !== false;
    reset();

    return {
      group,
      keyStyle: KEY_STYLE,
      hints: HINTS,
      stage: { floorY },
      // The Studio menu (piano.js instrumentOptions / workbench.js): one select per entry, setOptions({ [key]: value }) on a
      // change, choices[0] shown when nothing is saved. The host refuses a change while REC runs, which covers the one-time
      // compile (and, for studio and smoked, the bake) on a look's first use.
      optionsSpec: [{ key: "glass", label: "Glass", title: GLASS_TITLE,
        choices: Object.entries(GLASS_LOOKS).map(([value, L]) => ({ value, name: L.name })) }],
      // lab cameras: a three-quarter from the front right (the open lid faces that way) and a close-up of the action
      views: {
        // fitted offline (judge 2026-09-15: the lid tip and tail were cropped): the case, the long-prop lid and the tail
        // sit inside +-0.9 NDC, centred; only the feet of the front legs leave the bottom edge
        hero: () => { heroPose = true; applyLid(options.lid); return { from: [106.4, 72.8, 78.7], target: [-7.3, 10.5, -23.4], fov: 30 }; },
        close: { from: [17, 12.5, -1.5], target: [-1.8, 1.2, -13], fov: 34 },
      },
      info: { hammers: N, strings: NS, dampers: damperCount, pins: NS, pedals: 3 },
      update(dt, t, state) {
        if (!active) return;
        dt = Math.min(Math.max(dt || 0, 0), 0.1);
        frameT = t;
        held.fill(0);
        alive.fill(0);
        chordAcc.setRGB(0, 0, 0);
        chordN = 0;
        if (state && state.pressed) state.pressed.forEach(visitPressed);
        const first0 = !seeded;
        seeded = true;
        // The sustain record (piano.js, the instrument-host header): an entry lives exactly while the page holds that
        // sound, finger or pedal. This is the whole of "the light lasts as long as the note does".
        const sounding = state && state.sounding;
        if (sounding) {
          for (const [m, e] of sounding) {
            const i = m - first;
            if (i < 0 || i >= N) continue;
            alive[i] = 1;
            held[i] = e.held ? 1 : 0;
            if (e.strike !== seenStrike[i]) {
              seenStrike[i] = e.strike;
              strike(m, e.vel, e.t0, first0 ? Math.max(0, t - e.t0) : 0);
              if (e.t0 > lastNote[i]) lastNote[i] = e.t0;     // the ring reports the same strike: do not count it twice
            }
          }
        } else if (state && state.pressed) {
          // A host with no sustain record (an older page, an embedder): fingers and the pedal, as this instrument read them before.
          state.pressed.forEach((st, m) => { const i = m - first; if (i >= 0 && i < N) { held[i] = 1; alive[i] = 1; } });
          const ped = !!(state && state.pedal);
          for (let i = 0; i < N; i++) if (!alive[i] && bodyLvl[i] > 0 && (ped ? i < damperCount : false)) alive[i] = 1;
        }
        // The strike ring: the only place a note struck and released inside one frame shows at all.
        const notes = state && state.notes;
        if (notes) {
          for (let k = 0; k < notes.length; k++) {
            const n = notes[k], i = n.midi - first;
            if (i < 0 || i >= N || !(n.t > lastNote[i]) || n.t > t + 0.05) continue;
            lastNote[i] = n.t;
            if (!first0) strike(n.midi, n.vel, n.t, Math.max(0, t - n.t));   // on the first frame the ring is history
          }
        }
        const pedal = !!(state && state.pedal);

        const eK = Math.exp(-dt / EDGE.tau);
        edgeAcc.r *= eK; edgeAcc.g *= eK; edgeAcc.b *= eK;
        const luma = 0.2126 * edgeAcc.r + 0.7152 * edgeAcc.g + 0.0722 * edgeAcc.b;
        if (luma > EDGE.maxLuma) { const s = EDGE.maxLuma / luma; edgeAcc.r *= s; edgeAcc.g *= s; edgeAcc.b *= s; }
        const peak = Math.max(edgeAcc.r, edgeAcc.g, edgeAcc.b);
        if (peak > EDGE.maxChannel) { const s = EDGE.maxChannel / peak; edgeAcc.r *= s; edgeAcc.g *= s; edgeAcc.b *= s; }
        // the look's share of the tint: studio 0.6 (no clearcoat dimming it), the light guide 0 (its line carries the
        // strikes, at their keys); crystal multiplies by exactly 1
        const sk = edgeScale * strikeMul;
        strikeU.value.setRGB(edgeAcc.r * sk, edgeAcc.g * sk, edgeAcc.b * sk);

        const kFlash = Math.exp(-dt / TAU_FLASH), kDamp = Math.exp(-dt / TAU_DAMP), kVibOff = Math.exp(-dt / TAU_VIB_OFF);
        const un = strU.uNote.value;
        let glowDirty = false;
        for (let i = 0; i < N; i++) {
          const age = t - strikeT[i], v = strikeV[i], rise = 0.055 - 0.037 * v;
          if (age >= 0 && age < rise) { const s = age / rise; ang[i] = aTop[i] * s * s; } else {
            let rem = dt;
            if (!topHit[i] && age >= rise && age < 2) { ang[i] = aTop[i]; topHit[i] = 1; rem = Math.min(dt, age - rise); }
            const goal = held[i] ? aTop[i] * CHECK : 0;
            ang[i] = Math.abs(ang[i] - goal) < 1e-4 ? goal : damp(ang[i], goal, held[i] ? 0.05 : 0.07, rem);
          }
          if (i < damperCount) {
            const goal = held[i] || pedal ? 1 : 0;
            lift[i] = Math.abs(lift[i] - goal) < 1e-3 ? goal : damp(lift[i], goal, goal ? 0.035 : 0.08, dt);
          }
          // the felt glow, still read straight off the strike clock (it is the crystal's bloom flash)
          const struck = age >= rise && age < 12;
          const g = struck ? GLOW.peak * v * v * Math.exp(-(age - rise) / GLOW.tau) + (held[i] ? GLOW.held * v : 0) : 0;
          const o = i * 3, gr = strikeCol[o] * g, gg = strikeCol[o + 1] * g, gb = strikeCol[o + 2] * g;
          if (glowArr[o] !== gr || glowArr[o + 1] !== gg || glowArr[o + 2] !== gb) { glowArr[o] = gr; glowArr[o + 1] = gg; glowArr[o + 2] = gb; glowDirty = true; }
          // the string light and its vibration blur, both alive exactly as long as the SOUND is
          flash[i] *= kFlash;
          if (flash[i] < 1e-4) flash[i] = 0;
          if (alive[i]) {                                 // sounding: the two-stage decay onto a velocity-scaled floor
            bPrompt[i] *= Math.exp(-dt / tauPrompt[i]);
            bAfter[i] *= Math.exp(-dt / tauAfter[i]);
            vibGate[i] = 1;
            if (dampT[i]) dampT[i] = 0;                   // it is sounding again: the damper's window reopens
          } else if (bodyLvl[i] > 0) {                    // the sound ended: the damper lands, a fade and not a snap
            dampT[i] += dt;
            bFloor[i] *= kDamp; bPrompt[i] *= kDamp; bAfter[i] *= kDamp;
            vibGate[i] *= kVibOff;                        // the string stops moving before its glow is gone
          }
          // the stored terms keep falling at TAU_DAMP; the window is applied on read, so it cannot compound frame to frame
          let b = bFloor[i] + bPrompt[i] + bAfter[i];
          if (dampT[i] > 0) b *= dampFade(dampT[i]);      // ... and it is over, all the way to rest, by DAMP_FADE
          if (b < 1.5e-3) { b = 0; bFloor[i] = 0; bPrompt[i] = 0; bAfter[i] = 0; vibGate[i] = 0; }
          bodyLvl[i] = b;
          const on = t >= riseT[i] ? 1 : 0;               // nothing lights while the hammer is still on its way
          let lvl = (b * STR_BODY_GAIN + flash[i] * STR_FLASH_GAIN) * on;
          if (lvl < 0.003) lvl = 0;
          const amp = b > 0 ? ampMax[i] * Math.pow(b, AMP_EXP) * vibGate[i] * on : 0;
          if (lvl !== strLevel[i] || amp !== shownAmp[i]) {
            strLevel[i] = lvl; shownAmp[i] = amp;
            const o4 = i * 4;
            un[o4] = strikeCol[o] * lvl; un[o4 + 1] = strikeCol[o + 1] * lvl; un[o4 + 2] = strikeCol[o + 2] * lvl;
            un[o4 + 3] = amp;
          }
        }
        if (glowDirty) glowAttr.needsUpdate = true;
        strU.uTime.value = t;
        pedalAng = Math.abs(pedalAng - (pedal ? -0.11 : 0)) < 1e-4 ? (pedal ? -0.11 : 0) : damp(pedalAng, pedal ? -0.11 : 0, 0.05, dt);
        pose(dt);

        // the light guide: the instrument's frame for the shader, then the line of light from the strikes and the sound
        if (glassLook === "lightguide") { lgFrame(); updateLine(t); }

        // the etched chord name
        if (deskGroup.visible) {
          const chord = state && state.chord, name = chord && chord.name ? chord.name : null;
          if (name !== etchName) {
            // no flare in portrait: there the etch sits behind the note bars and would echo the page's chord header
            if (name) { drawEtch(name, chord.nns || ""); etchFlash = portrait ? 0 : ETCH.flash; }
            etchName = name;
          }
          if (chordN > 0) chordCol.setRGB(chordAcc.r / chordN, chordAcc.g / chordN, chordAcc.b / chordN);
          etchFlash *= Math.exp(-dt / ETCH.tau);
          etchLevel = damp(etchLevel, name ? ETCH.level : 0, name ? 0.08 : 0.4, dt);
          const e = etchLevel + etchFlash * (name ? 1 : 0);
          etchMat.color.setRGB(chordCol.r * e, chordCol.g * e, chordCol.b * e);
          etch.visible = e > 0.002;
        }
      },
      resize(f) { framing = f || framing; portrait = isPortrait(framing); heroPose = false; applyLid(options.lid); },
      setActive(on) {
        active = !!on;
        group.visible = active;
        if (!active) reset();
      },
      setOptions(o) {
        Object.assign(options, o || {});
        applyGlass(options.glass);
        applyEdge();
        applyLid(options.lid);
        deskGroup.visible = options.desk !== false;
      },
      get framing() { return framing; },
      dispose() {
        scene.remove(group);
        if (fontSet && fontSet.removeEventListener) fontSet.removeEventListener("loadingdone", onFontsLoaded);
        for (const g of geos) g.dispose();
        for (const m of mats) m.dispose();
        for (const t of texs) t.dispose();
        shanks.dispose(); heads.dispose(); pins.dispose(); pedals.dispose();
        if (dampers) dampers.dispose();
        // the painted studio map (studio, smoked); the host's ctx.envMap is the host's to free
        if (privateEnv) { privateEnv.target.dispose(); privateEnv = null; }
        bakeWant = null;
        // The renderer draws what is behind transmissive glass into a render target it makes on first use and keeps for
        // the page's life (full size, 4x multisampled, mipmapped). It is freed with the glass; a later transmissive
        // material (spectacle's, or the glass again) gets a new one on its next frame.
        const targets = new Set();
        for (const u of glassUniforms) {
          const t = u.transmissionSamplerMap && u.transmissionSamplerMap.value;
          if (t && t.renderTarget && t.renderTarget.isRenderTarget) targets.add(t.renderTarget);
        }
        for (const rt of targets) rt.dispose();
        glassUniforms.clear();
      },
    };
  },
};
