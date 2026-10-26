// Virtual Stage v0, the shaders: arsenal/web/stage/shaders.js. GLSL ES 3.00 written fresh for this page (Apache-2.0,
// Akashic Aurora), composed at load time with the house library (arsenal/web/glsl: volume-phase for the scattering lobe,
// dither-masks for the static jitter, display-out for the finish, colour-transfer for the sRGB seam), so a change to a
// house module reaches the stage too (Daniel, 2026-10-13: "tweak one module and have everything update").
//
// The techniques, credited:
//   - wide beams: analytic ray-cone intersection, then the in-scatter integral of a point source in a participating
//     medium sampled EQUIANGULARLY about the lens (Kulla and Fajardo, "Importance Sampling Techniques for Path Tracing in
//     Participating Media", EGSR 2012; the closed form behind it: Sun, Ramamoorthi, Narasimhan and Nayar, "A Practical
//     Analytic Single Scattering Model for Real Time Rendering", SIGGRAPH 2005), so the 1/r^2 of the source cancels and
//     a beam seen down its axis is as clean as one seen side-on;
//   - thin beams and lasers: ribbons at least one pixel wide with their light scaled by coverage (Emil Persson,
//     "phone-wire anti-aliasing", 2012), radiance from the thin-beam law L = sigma Phi p(theta) / (a d sin(gamma) w);
//   - LED emitters: billboards no smaller than 1.5 px whose light is scaled by the area they really cover;
//   - bloom: the 13-tap downsample with a Karis average on the first level and a tent upsample (Jorge Jimenez, "Next
//     Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014);
//   - nothing temporal on beams or lasers (Lasers v2 rule 4): the jitter is spatial only, and the exposure is fixed per shot.
// Units: scene-linear light in nits (cd/m^2); the finish divides by the exposure reference before display-out.

export const MAX_SPOTS = 32;

// The shared medium: the CPU twin is atmos.js densityAt.
export const HAZE = `
uniform highp sampler3D uNoise;
uniform float uSigma0;
uniform float uNoiseAmp;
uniform vec3 uWind;
uniform vec4 uHazer[8];
uniform float uHazerSigma[8];
uniform float uG;
float hazeDensity(vec3 p) {
  float n1 = texture(uNoise, (p - uWind) * (1.0 / 26.0)).r;
  float n2 = texture(uNoise, (p - uWind * 1.7 + vec3(3.1, 7.7, 1.3)) * (1.0 / 9.0)).r;
  float n = (0.7 * n1 + 0.3 * n2) * 2.0 - 1.0;
  float sig = uSigma0 * max(0.0, 1.0 + 2.0 * uNoiseAmp * n);
  for (int h = 0; h < 8; h++) {
    vec3 off = p - uHazer[h].xyz;
    float rr = max(uHazer[h].w, 0.001);
    sig += uHazerSigma[h] * exp(-dot(off, off) / (rr * rr));
  }
  return min(sig, 0.26);
}
`;

const HEAD = `precision highp float;
precision highp int;
precision highp sampler2D;
precision highp sampler3D;
`;

// ------------------------------------------------------------------------------------------------- lit surfaces --
// The crowd near the lens (v1, the v0 judge's finding: a beat-swinging slab of crowd arm in front of TUNNEL_UP's lens
// made the final limiter act during the programmed demo). Fixed where it starts: a figure whose head is within
// uCullNear metres of the camera is not drawn (a camera crew stands in a gap), and within uFreezeFar the raised arms
// hold their mean pose instead of swinging with the beat, fading back to the full swing by 1.6 x that distance. Far
// figures are unchanged.
export const CROWD_CULL_NEAR_M = 4.0;
export const CROWD_FREEZE_M = 10.0;
export function litVertex({ instanced = false, crowd = false, nearCull = false } = {}) {
  const near = instanced && (crowd || nearCull);
  return `${HEAD}
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;
uniform mat4 modelMatrix;
in vec3 position;
in vec3 normal;
${instanced ? "in mat4 instanceMatrix;" : ""}
${crowd ? "in vec4 iCrowd;\nuniform float uBeatPhase;\nuniform float uEnergy;" : ""}
${near ? "uniform vec3 cameraPosition;\nuniform float uCullNear;\nuniform float uFreezeFar;" : ""}
out vec3 vWorld;
out vec3 vNormal;
void main() {
  vec3 p = position;
  ${near ? `
  vec3 headW = (modelMatrix * instanceMatrix * vec4(0.0, 1.6, 0.0, 1.0)).xyz;
  float dCam = distance(headW, cameraPosition);
  if (dCam < uCullNear) { vWorld = headW; vNormal = vec3(0.0, 1.0, 0.0); gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  float swing = smoothstep(uFreezeFar, uFreezeFar * 1.6, dCam);` : ""}
  ${crowd ? `
  // arms: vertices above the shoulder (y > 1.45 of a 1.75 m figure) of a raised-arm figure sway with the beat (near the
  // lens they hold the swing's mean pose: lift 0.75, no sideways sway)
  if (iCrowd.y > 0.5 && p.y > 1.42) {
    float lift = (p.y - 1.42) * (0.6 + 0.4 * uEnergy) * (0.75 + 0.25 * swing * sin(6.2831853 * (uBeatPhase + iCrowd.x)));
    p.y = 1.42 + lift * 1.15;
    p.x += (p.y - 1.42) * 0.25 * swing * sin(6.2831853 * (uBeatPhase * 0.5 + iCrowd.x));
  }` : ""}
  mat4 m = modelMatrix${instanced ? " * instanceMatrix" : ""};
  vec4 wp = m * vec4(p, 1.0);
  vWorld = wp.xyz;
  vNormal = normalize(mat3(m) * normal);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;
}

export function litFragment(prelude) {
  return `${HEAD}
${prelude}
uniform vec3 uAlbedo;
uniform vec3 uEmissive;
uniform vec3 uAmbient;
uniform int uNSpot;
uniform vec3 uSpotPos[${MAX_SPOTS}];
uniform vec3 uSpotDir[${MAX_SPOTS}];
uniform vec3 uSpotCol[${MAX_SPOTS}];
uniform vec3 uSpotShape[${MAX_SPOTS}];   // tan(beam half angle), lens radius, profile exponent
in vec3 vWorld;
in vec3 vNormal;
out vec4 fragColor;
void main() {
  vec3 n = normalize(vNormal);
  vec3 E = uAmbient;
  for (int i = 0; i < ${MAX_SPOTS}; i++) {
    if (i >= uNSpot) break;
    vec3 q = vWorld - uSpotPos[i];
    float r2 = max(dot(q, q), 0.04);
    float h = dot(q, uSpotDir[i]);
    if (h <= 0.0) continue;
    float rad = sqrt(max(r2 - h * h, 0.0));
    float prof = exp2(-pow(rad / (uSpotShape[i].y + h * uSpotShape[i].x), uSpotShape[i].z));
    vec3 l = -q * inversesqrt(r2);
    E += uSpotCol[i] * prof * max(dot(n, l), 0.0) / r2;
  }
  fragColor = vec4(min(uAlbedo / PI * E + uEmissive, vec3(3.0e4)), 1.0);
}`;
}

// ------------------------------------------------------------------------------------------------- cubes (lit LED) --
export const CUBE_VERTEX = `${HEAD}
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;
in vec3 position;
in vec3 normal;
in mat4 instanceMatrix;
in vec3 iEmit;
out vec3 vLocal;
out vec3 vNormalW;
out vec3 vWorld;
flat out vec3 fEmit;
void main() {
  vec4 wp = instanceMatrix * vec4(position, 1.0);
  vLocal = position;
  vWorld = wp.xyz;
  vNormalW = normalize(mat3(instanceMatrix) * normal);
  fEmit = iEmit;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;
export const CUBE_FRAGMENT = (prelude) => `${HEAD}
${prelude}
uniform vec3 cameraPosition;
in vec3 vLocal;
in vec3 vNormalW;
in vec3 vWorld;
flat in vec3 fEmit;
out vec4 fragColor;
void main() {
  // a translucent cube lit from inside: brightest where the view crosses the most of its volume (the centre of a face,
  // and the faces seen edge-on glow along their frame), with a faint frame of the aluminium edges
  vec3 a = abs(vLocal) / 0.55;
  float edge = max(max(min(a.x, a.y), min(a.y, a.z)), min(a.x, a.z));
  float frame = smoothstep(0.92, 0.985, edge);
  vec3 v = normalize(cameraPosition - vWorld);
  float facing = abs(dot(normalize(vNormalW), v));
  float glow = 0.55 + 0.45 * (1.0 - facing) + 0.35 * (1.0 - max(a.x, max(a.y, a.z)) * 0.7);
  fragColor = vec4(fEmit * glow * (1.0 - 0.85 * frame), 1.0);
}`;

// ------------------------------------------------------------------------------------------------- emitters --
export const EMIT_VERTEX = `${HEAD}
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;
uniform float uPixAngle;
uniform float uMinPx;
in vec3 position;
in vec3 iPos;
in vec3 iCol;
in float iSize;
out vec2 vUv;
flat out vec3 fCol;
void main() {
  vec4 vp = viewMatrix * vec4(iPos, 1.0);
  float depth = max(-vp.z, 0.05);
  float physPx = iSize / (depth * uPixAngle);
  float drawPx = max(physPx, uMinPx);
  float cov = physPx / drawPx;
  float rad = drawPx * depth * uPixAngle;
  vp.xy += position.xy * rad * 1.6;
  vUv = position.xy * 1.6;
  fCol = iCol * cov * cov;
  gl_Position = projectionMatrix * vp;
  if (vp.z > -0.1) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);   // behind the camera: off screen
}`;
export const EMIT_FRAGMENT = `${HEAD}
in vec2 vUv;
flat in vec3 fCol;
out vec4 fragColor;
void main() {
  float r2 = dot(vUv, vUv);
  if (r2 > 2.56) discard;
  // a Gaussian whose integral over the plane equals the disc of radius 1: the light of the cell, spread softly
  fragColor = vec4(min(fCol * 2.2 * exp(-2.2 * r2), vec3(3.0e4)), 1.0);
}`;

// ------------------------------------------------------------------------------------------------- lasers --
export const LASER_VERTEX = `${HEAD}
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;
uniform vec3 cameraPosition;
uniform vec2 uRes;
uniform float uPixAngle;
in vec3 position;          // x: along (0 or 1), y: side (-1 or 1)
in vec3 iA;
in vec3 iB;
in vec3 iPow;
in vec3 iMisc;             // width at the aperture (m), divergence (rad), distance of A from the aperture (m)
out float vAcross;
out float vWpx;
out vec3 vWorld;
flat out vec3 fPow;
flat out vec3 fDir;
void main() {
  vec3 P = mix(iA, iB, position.x);
  vec4 ca = projectionMatrix * viewMatrix * vec4(iA, 1.0);
  vec4 cb = projectionMatrix * viewMatrix * vec4(iB, 1.0);
  vec2 sa = ca.xy / ca.w * uRes * 0.5, sb = cb.xy / cb.w * uRes * 0.5;
  vec2 d2 = sb - sa;
  vec2 dir = length(d2) > 1e-4 ? normalize(d2) : vec2(1.0, 0.0);
  vec2 perp = vec2(-dir.y, dir.x);
  vec4 cp = position.x < 0.5 ? ca : cb;
  float along = iMisc.z + position.x * length(iB - iA);
  float dist = max(length(P - cameraPosition), 0.05);
  float wPx = (iMisc.x + iMisc.y * along) / (dist * uPixAngle);
  float drawn = max(wPx, 1.0) + 1.0;
  cp.xy += perp * position.y * (drawn * 0.5) * (2.0 / uRes) * cp.w;
  vAcross = position.y * drawn * 0.5;
  vWpx = wPx;
  vWorld = P;
  fPow = iPow;
  fDir = normalize(iB - iA);
  gl_Position = cp;
}`;
export const LASER_FRAGMENT = (prelude) => `${HEAD}
${prelude}
${HAZE}
uniform vec3 cameraPosition;
uniform float uPixAngle;
uniform float uSigmaAvg;
uniform vec3 uLumPerWatt;
in float vAcross;
in float vWpx;
in vec3 vWorld;
flat in vec3 fPow;
flat in vec3 fDir;
out vec4 fragColor;
void main() {
  vec3 rd = vWorld - cameraPosition;
  float d = max(length(rd), 0.05);
  rd /= d;
  float w = max(vWpx, 1.0);
  float prof = clamp(w * 0.5 + 0.5 - abs(vAcross), 0.0, 1.0);
  float sinG = max(length(cross(rd, fDir)), 0.03);
  float ph = phaseHG(dot(rd, -fDir), uG);
  float sigma = hazeDensity(vWorld);
  float T = exp(-uSigmaAvg * d);
  vec3 L = sigma * fPow * uLumPerWatt * ph * T / (uPixAngle * d * sinG * w);
  fragColor = vec4(min(L * prof, vec3(200.0)), 1.0);   // past ~60x white a laser line is white; the cap keeps its bloom honest
}`;

// ------------------------------------------------------------------------------------------------- wide beams --
export const BEAM_VERTEX = `${HEAD}
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;
in vec3 position;          // x = cos, y = sin, z = 0 at the lens, 1 at the far end
in vec3 iApex;
in vec3 iAxis;
in vec3 iShape;            // tan(beam half angle), tan(field half angle), lens radius
in vec2 iLenN;             // length (m), profile exponent
in vec3 iCol;              // linear colour x intensity (cd) x dimmer
out vec3 vWorld;
flat out vec3 fApex;
flat out vec3 fAxis;
flat out vec3 fShape;
flat out vec2 fLenN;
flat out vec3 fCol;
void main() {
  vec3 w = iAxis;
  // a perpendicular to the beam: world up crossed with the axis, written out, or world x crossed with it when the beam
  // itself is (nearly) vertical
  vec3 u = vec3(w.z, 0.0, -w.x);
  if (abs(w.y) >= 0.99) u = vec3(0.0, -w.z, w.y);
  u = normalize(u);
  vec3 v = cross(w, u);
  float s = position.z;
  float R = (iShape.z + s * iLenN.x * iShape.y * 1.35) * 1.1;
  vec3 p = iApex + w * (s * iLenN.x - (1.0 - s) * 0.05) + (u * position.x + v * position.y) * R;
  vWorld = p;
  fApex = iApex; fAxis = iAxis; fShape = iShape; fLenN = iLenN; fCol = iCol;
  gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
}`;
export const BEAM_FRAGMENT = (prelude, samples) => `${HEAD}
${prelude}
${HAZE}
uniform vec3 cameraPosition;
uniform sampler2D uDepth;
uniform vec2 uRes;
uniform float uNear;
uniform float uFar;
uniform vec3 uCamFwd;
uniform float uSigmaAvg;
in vec3 vWorld;
flat in vec3 fApex;
flat in vec3 fAxis;
flat in vec3 fShape;
flat in vec2 fLenN;
flat in vec3 fCol;
out vec4 fragColor;
float viewZ(float d) { return (uNear * uFar) / ((uFar - uNear) * d - uFar); }
bool insideCone(vec3 co, vec3 rd, float t, vec3 axis, float cos2) {
  vec3 p = co + rd * t;
  float h = dot(p, axis);
  return h > 0.0 && h * h >= cos2 * dot(p, p);
}
void main() {
  vec3 ro = cameraPosition;
  vec3 rd = normalize(vWorld - ro);
  float tBack = length(vWorld - ro);
  float dz = texture(uDepth, gl_FragCoord.xy / uRes).r;
  float tScene = dz >= 0.99999 ? 1e6 : -viewZ(dz) / max(1e-4, dot(rd, uCamFwd));
  float tMax = min(tBack, tScene);
  float tanF = fShape.y * 1.35;
  float hOff = fShape.z / tanF;
  vec3 A = fApex - fAxis * hOff;                 // the virtual apex of the cone through the lens
  float cos2 = 1.0 / (1.0 + tanF * tanF);
  vec3 co = ro - A;
  float dv = dot(rd, fAxis), cv = dot(co, fAxis);
  float qa = dv * dv - cos2, qb = 2.0 * (dv * cv - dot(rd, co) * cos2), qc = cv * cv - dot(co, co) * cos2;
  float tA = 0.0, tB = tMax;
  // the quadratic in its half-b form: roots (-hb -+ sqrt(hb^2 - qa qc)) / qa
  float hb = 0.5 * qb;
  float dq = hb * hb - qa * qc;
  if (dq < 0.0 || abs(qa) < 1e-9) {
    if (!insideCone(co, rd, 0.0, fAxis, cos2)) discard;
  } else {
    float rt = sqrt(dq);
    float t1 = (-hb - rt) / qa, t2 = (-hb + rt) / qa;
    if (t1 > t2) { float tt = t1; t1 = t2; t2 = tt; }
    if (insideCone(co, rd, 0.5 * (t1 + t2), fAxis, cos2)) { tA = max(tA, t1); tB = min(tB, t2); }
    else if (insideCone(co, rd, t2 + 1e-3 * (abs(t2) + 1.0), fAxis, cos2)) { tA = max(tA, t2); }
    else { tB = min(tB, t1); }
  }
  // the slab between the lens and the beam's end
  if (abs(dv) > 1e-6) {
    float ta = (hOff - cv) / dv, tb = (hOff + fLenN.x - cv) / dv;
    tA = max(tA, min(ta, tb)); tB = min(tB, max(ta, tb));
  } else if (cv < hOff || cv > hOff + fLenN.x) discard;
  if (tB <= tA) discard;
  // equiangular samples about the lens: t = delta + D tan(theta), theta even between the interval's ends
  vec3 L = fApex;
  float delta = dot(L - ro, rd);
  float D = max(length(L - ro - rd * delta), 1e-3);
  float thA = atan((tA - delta) / D), thB = atan((tB - delta) / D);
  float inscatter = 0.0;
  float jit = dthIgn(gl_FragCoord.xy);
  for (int k = 0; k < ${samples}; k++) {
    float th = mix(thA, thB, (float(k) + jit) / ${samples}.0);
    float t = delta + D * tan(th);
    vec3 p = ro + rd * t;
    vec3 q = p - fApex;
    float r2 = dot(q, q);
    float h = dot(q, fAxis);
    if (h <= 0.0) continue;
    float rad = sqrt(max(r2 - h * h, 0.0));
    float prof = exp2(-pow(rad / (fShape.z + h * fShape.x), fLenN.y));
    float ph = phaseHG(dot(rd, -q * inversesqrt(r2)), uG);
    float T = exp(-uSigmaAvg * (max(t, 0.0) + sqrt(r2)));
    inscatter += hazeDensity(p) * prof * ph * T;
  }
  // f / pdf: the source's 1 / r^2 cancels against the equiangular pdf, leaving (thB - thA) / D
  vec3 Lo = fCol * inscatter * (thB - thA) / (D * ${samples}.0);
  fragColor = vec4(min(Lo, vec3(3.0e4)), 1.0);
}`;

// ------------------------------------------------------------------------------------------------- full-screen --
export const FS_VERTEX = `${HEAD}
in vec3 position;
void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }`;

export const COMPOSITE_FRAGMENT = `${HEAD}
uniform sampler2D uScene;
uniform sampler2D uBeams;
uniform sampler2D uDepth;
uniform vec2 uRes;
uniform vec3 uVeil;
uniform float uSigma0;
uniform float uNear;
uniform float uFar;
uniform float uBeamsOn;
out vec4 fragColor;
float viewZ(float d) { return (uNear * uFar) / ((uFar - uNear) * d - uFar); }
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec3 c = texture(uScene, uv).rgb + uBeamsOn * texture(uBeams, uv).rgb;
  float dz = texture(uDepth, uv).r;
  float dist = dz >= 0.99999 ? 160.0 : -viewZ(dz);
  c += uVeil * (1.0 - exp(-uSigma0 * dist));
  // half-float targets overflow past 65504: an infinite or NaN pixel would smear through the bloom, so clamp here
  if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
  fragColor = vec4(clamp(c, vec3(0.0), vec3(6.0e4)), 1.0);
}`;

export const BLOOM_DOWN_FRAGMENT = `${HEAD}
uniform sampler2D uSrc;
uniform vec2 uTexel;
uniform vec2 uRes;
uniform int uKaris;
out vec4 fragColor;
// the first level reads the frame through a ceiling (uCeil, about 13 x white): a source far past white blooms like a
// bright one, not like a sun, so a fan of lasers glows instead of greying the whole frame
uniform float uCeil;
vec3 S(vec2 uv, vec2 o) { return min(texture(uSrc, uv + o * uTexel).rgb, vec3(uCeil)); }
float kw(vec3 c) { float luma = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b; return 1.0 / (luma + 1.0); }
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec3 a = S(uv, vec2(-2, 2)), b = S(uv, vec2(0, 2)), c = S(uv, vec2(2, 2));
  vec3 d = S(uv, vec2(-2, 0)), e = S(uv, vec2(0, 0)), f = S(uv, vec2(2, 0));
  vec3 g = S(uv, vec2(-2, -2)), h = S(uv, vec2(0, -2)), i = S(uv, vec2(2, -2));
  vec3 j = S(uv, vec2(-1, 1)), k = S(uv, vec2(1, 1)), l = S(uv, vec2(-1, -1)), m = S(uv, vec2(1, -1));
  vec3 o;
  if (uKaris == 1) {
    // the Karis average: each 2 x 2 group weighted by 1 / (1 + luma), so one hot pixel cannot become a flickering blob
    vec3 g0 = (j + k + l + m) * 0.25, g1 = (a + b + d + e) * 0.25, g2 = (b + c + e + f) * 0.25, g3 = (d + e + g + h) * 0.25, g4 = (e + f + h + i) * 0.25;
    float w0 = kw(g0) * 0.5, w1 = kw(g1) * 0.125, w2 = kw(g2) * 0.125, w3 = kw(g3) * 0.125, w4 = kw(g4) * 0.125;
    o = (g0 * w0 + g1 * w1 + g2 * w2 + g3 * w3 + g4 * w4) / (w0 + w1 + w2 + w3 + w4);
  } else {
    o = e * 0.125 + (a + c + g + i) * 0.03125 + (b + d + f + h) * 0.0625 + (j + k + l + m) * 0.125;
  }
  fragColor = vec4(o, 1.0);
}`;

export const BLOOM_UP_FRAGMENT = `${HEAD}
uniform sampler2D uSrc;
uniform vec2 uTexel;
uniform vec2 uRes;
uniform float uRadius;
out vec4 fragColor;
vec3 S(vec2 uv, vec2 o) { return texture(uSrc, uv + o * uTexel * uRadius).rgb; }
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec3 o = (S(uv, vec2(-1, 1)) + 2.0 * S(uv, vec2(0, 1)) + S(uv, vec2(1, 1))
          + 2.0 * S(uv, vec2(-1, 0)) + 4.0 * S(uv, vec2(0, 0)) + 2.0 * S(uv, vec2(1, 0))
          + S(uv, vec2(-1, -1)) + 2.0 * S(uv, vec2(0, -1)) + S(uv, vec2(1, -1))) / 16.0;
  fragColor = vec4(o, 1.0);
}`;

export const FINISH_FRAGMENT = (prelude) => `${HEAD}
${prelude}
uniform sampler2D uHdr;
uniform sampler2D uBloom;
uniform vec2 uRes;
uniform float uBloomMix;
uniform float uExposure;
uniform float uEv;
uniform int uCurve;
uniform float uSat;
uniform float uVig;
out vec4 fragColor;
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec3 c = texture(uHdr, uv).rgb;
  vec3 b = texture(uBloom, uv).rgb;
  vec3 lin = mix(c, b, uBloomMix) * uExposure;
  fragColor = vec4(displayOut(lin, gl_FragCoord.xy, uRes, uEv, uCurve, uSat, uVig, 0.0, 256.0), 1.0);
}`;

// the meter: per 4 x 4 block of the finished frame, the sums of relative luminance and of the WCAG red quantity, and
// the pixel count (exact box sums: the limiter's cells are means of every pixel)
export const METER1_FRAGMENT = (prelude) => `${HEAD}
${prelude}
uniform sampler2D uSrc;
uniform ivec2 uSrcSize;
out vec4 fragColor;
void main() {
  ivec2 base = ivec2(gl_FragCoord.xy) * 4;
  vec3 sums = vec3(0.0);
  for (int k = 0; k < 16; k++) {
    ivec2 p = base + ivec2(k % 4, k / 4);
    if (p.x >= uSrcSize.x || p.y >= uSrcSize.y) continue;
    vec3 e = texelFetch(uSrc, p, 0).rgb;
    vec3 l = srgbDecode(e);
    float s = e.r + e.g + e.b;
    float red = (s > 0.0 && e.r / s >= 0.8) ? max(0.0, (l.r - l.g - l.b) * 320.0) : 0.0;
    sums += vec3(dot(l, vec3(0.2126, 0.7152, 0.0722)), red, 1.0);
  }
  fragColor = vec4(sums, 1.0);
}`;
export const METER2_FRAGMENT = `${HEAD}
uniform sampler2D uSrc;
uniform ivec2 uSrcSize;
out vec4 fragColor;
void main() {
  ivec2 base = ivec2(gl_FragCoord.xy) * 4;
  vec3 sums = vec3(0.0);
  for (int k = 0; k < 16; k++) {
    ivec2 p = base + ivec2(k % 4, k / 4);
    if (p.x >= uSrcSize.x || p.y >= uSrcSize.y) continue;
    sums += texelFetch(uSrc, p, 0).rgb;
  }
  fragColor = vec4(sums, 1.0);
}`;

// the limiter's apply pass: identity copies the frame untouched; otherwise, in cell c (the meter's cells: 16-pixel blocks
// shared out four ways), x' = (1 - b_c) a_c x + b_c prev, per channel in linear light (prev: the last shown frame)
export const PRESENT_FRAGMENT = (prelude) => `${HEAD}
${prelude}
uniform sampler2D uSrc;
uniform sampler2D uPrev;
uniform float uA[16];
uniform float uB[16];
uniform ivec2 uM2;
uniform int uIdentity;
out vec4 fragColor;
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  vec4 e = texelFetch(uSrc, p, 0);
  if (uIdentity == 1) { fragColor = vec4(e.rgb, 1.0); return; }
  ivec2 bl = p / 16;
  int c = min(3, (bl.y * 4) / uM2.y) * 4 + min(3, (bl.x * 4) / uM2.x);
  vec3 l = uA[c] * srgbDecode(e.rgb);
  vec3 prev = srgbDecode(texelFetch(uPrev, p, 0).rgb);
  l = mix(l, prev, uB[c]);
  fragColor = vec4(srgbEncode(clamp(l, 0.0, 1.0)), 1.0);
}`;

// the profiler's fence: one pixel that depends on a pass's output
export const FENCE_FRAGMENT = `${HEAD}
uniform sampler2D uSrc;
out vec4 fragColor;
void main() { fragColor = vec4(clamp(texture(uSrc, vec2(0.5)).rgb, 0.0, 1.0), 1.0); }`;

export const COPY_FRAGMENT = `${HEAD}
uniform sampler2D uSrc;
out vec4 fragColor;
void main() { fragColor = vec4(texelFetch(uSrc, ivec2(gl_FragCoord.xy), 0).rgb, 1.0); }`;
