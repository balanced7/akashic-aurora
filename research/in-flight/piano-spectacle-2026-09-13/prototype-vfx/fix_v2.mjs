// v2 fixes from the round-1 snapshots: soft protect mask, budgeted shimmer, a low aurora, a real fountain, scorer v2.
import { readFileSync, writeFileSync } from "node:fs";
const DIR = "C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/";
function edit(file, pairs) {
  let src = readFileSync(DIR + file, "utf8").replace(/\r\n/g, "\n");
  for (const [from, to] of pairs) {
    const n = src.split(from).length - 1;
    if (n !== 1) throw new Error(`${file}: expected one match (${n}) for:\n${from}`);
    src = src.replace(from, to);
  }
  writeFileSync(DIR + file, src);
  return src;
}

let mod = edit("fx_module.js", [
  [`  // effect light allowed here: 0 inside the chord name, 0.35 inside the staff, 1 elsewhere
  float fxProtect() {
    vec2 p = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
    return (1.0 - fxRect(p, uProtA, 0.035)) * (1.0 - 0.65 * fxRect(p, uProtB, 0.035));
  }`,
   `  // v2: a rectangle mask showed as a dark box. A super-ellipse with a wide feather has no edge or corner to see.
  float fxBlob(vec2 p, vec4 r, float feather) {
    vec2 c = 0.5 * (r.xy + r.zw);
    vec2 h = 0.5 * (r.zw - r.xy) + feather;
    vec2 q = abs(p - c) / h;
    float d = pow(pow(q.x, 4.0) + pow(q.y, 4.0), 0.25);
    return 1.0 - smoothstep(0.62, 1.0, d);
  }
  // effect light allowed here: about 0.12 at the heart of the chord name, 0.45 in the staff, 1 elsewhere
  float fxProtect() {
    vec2 p = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
    return (1.0 - 0.88 * fxBlob(p, uProtA, 0.09)) * (1.0 - 0.55 * fxBlob(p, uProtB, 0.06));
  }`],
  [`float hem = uBaseY + 1.0 + 2.4 * sin(`, `float hem = uBaseY + 2.0 + 2.4 * sin(`],
  [`    float curtain = smoothstep(-0.8, 0.6, h) * exp(-max(h, 0.0) / 10.0);`,
   `    float curtain = smoothstep(-0.8, 0.6, h) * exp(-max(h, 0.0) / 4.5);  // v2: a low horizon curtain, not a sky of blurred rays`],
  [`    vec3 col = mix(low, high, smoothstep(0.0, 14.0, h)) * curtain * rays * 0.34 + uGoldC * hemLine * 0.22;`,
   `    vec3 col = mix(low, high, smoothstep(0.0, 6.0, h)) * curtain * rays * 0.3 + uGoldC * hemLine * 0.24;`],
  [`const up = [0, 3.2, 6.0, 7.2, 8.5][tier]`, `const up = [0, 4.0, 9.0, 10.0, 11.0][tier]`],
  [`A.aSize.array[j] = 0.1 + Math.random() * 0.22;`, `A.aSize.array[j] = 0.14 + Math.random() * 0.26;`],
  [`    fxState.shimGain = tier >= 4 ? 1.3 : 1.0;`,
   `    // v2: the shimmer shares a budget: past 8 live columns under the chord it thins out instead of forming a bright bar
    let cols = 0;
    for (let j = 0; j < TRAIL_MAX; j++) {
      const A = trailAttr;
      if (A.aT0.array[j] < -1e5 || t - Math.min(t, A.aT2.array[j]) > LIGHT.endCut) continue;
      if (A.aX.array[j] >= x0 - 0.6 && A.aX.array[j] <= x1 + 0.6) cols++;
    }
    fxState.shimGain = (tier >= 4 ? 1.0 : 0.85) * Math.min(1, 8 / Math.max(cols, 1));`],
  [`banner: { t0: -1e6, hold: 1, tier: 0 }, shimGain: 0 };`,
   `banner: { t0: -1e6, hold: 1, tier: 0 }, shimGain: 0,
                  tokens: { 2: 3, 3: 1, 4: 0.75 } };  // v2: rarity tokens; no Legendary before ~45 s of play`],
  [`function fxUpdate(dt, t) {
  fxShared.uNow.value = t;`,
   `function fxUpdate(dt, t) {
  for (const k of [2, 3, 4]) fxState.tokens[k] = Math.min(FX_TOKENS[k].cap, fxState.tokens[k] + dt / FX_TOKENS[k].refill);
  fxShared.uNow.value = t;`],
]);
const a = mod.indexOf("// Fanciness score for a newly named chord");
const b = mod.indexOf("function fxUpdate(dt, t) {");
if (a < 0 || b < 0 || b < a) throw new Error("scorer block not found");
const SCORER = `// Fanciness score for a newly named chord (LAB v2; the design doc gives the production scorer).
//   harmony: finger-held notes plus pedal-held notes struck in the last 1.5 s (PIANO-V2-SPEC 6.1)
//   strike: notes whose onsets fall within 80 ms of the newest one
//   accent: the strike's velocity against the mean of the 20 s before it
const FX_TOKENS = { 2: { cap: 3, refill: 10 }, 3: { cap: 2, refill: 45 }, 4: { cap: 1, refill: 180 } };
const fxVelHist = [];
function fxNoteOn(vel, t) {
  fxVelHist.push([t, vel]);
  while (fxVelHist.length && t - fxVelHist[0][0] > 21) fxVelHist.shift();
}
function fxScore(info, t) {
  const parts = {};
  const entries = [...sounding.entries()];
  if (!info || !entries.length) return { score: 0, tier: 0, parts };
  const newest = Math.max(...entries.map(([, s]) => s.t0));
  const strike = entries.filter(([, s]) => newest - s.t0 < 0.08);
  const vel = strike.reduce((acc, [, s]) => acc + s.vel, 0) / strike.length;
  const before = fxVelHist.filter(([ht]) => ht < newest - 0.1 && newest - ht < 20);
  const mean = before.length >= 4 ? before.reduce((acc, [, v]) => acc + v, 0) / before.length : 80;
  const harmony = entries.filter(([, s]) => s.held || t - s.t0 < 1.5).map(([m]) => m);
  const h = harmony.length ? Theory.detect(harmony, keyGuess ? keyGuess.bias : 0) : null;
  if (h && h.kind === "chord") {
    const suf = h.suffix || "";
    parts.colour = /13|11/.test(suf) ? 3 : /9/.test(suf) ? 2.5 : /7|6/.test(suf) ? 1.5 : /sus|dim|aug/.test(suf) ? 1 : 0;
    if (h.bass) parts.slash = 0.5;
    const pcs = new Set(harmony.map((m) => Theory.mod(m, 12))).size;
    if (pcs > 4) parts.density = Math.min(1.5, 0.5 * (pcs - 4));
    if (keyGuess) {
      const scale = keyGuess.mode === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10, 11];
      if (harmony.some((m) => !scale.includes(Theory.mod(m - keyGuess.tonic, 12)))) parts.borrowed = 1.5;
    }
  }
  const sm = strike.map(([m]) => m);
  const span = Math.max(...sm) - Math.min(...sm);
  if (span >= 24) parts.span = span >= 36 ? 1.5 : 1;
  if (strike.length >= 4) parts.mass = strike.length >= 6 ? 1 : 0.5;
  const acc = vel - mean;
  if (acc >= 12) parts.accent = acc >= 22 ? 2 : 1;
  if (vel >= 112) parts.loud = 0.5;
  if (sustain && strike.length >= 3) parts.pedal = 0.5;
  const name = h ? h.name : info.name;
  const hist = (fxState.seen.get(name) || []).filter((x) => t - x < 60);
  if (!fxState.seen.has(name) && strike.length >= 3) parts.novelty = 0.5;
  if (hist.length >= 3) parts.fatigue = -1.5;
  fxState.seen.set(name, [...hist, t]);
  const score = Object.values(parts).reduce((x, y) => x + y, 0);
  let tier = score >= 8 ? 4 : score >= 6 ? 3 : score >= 4.5 ? 2 : score >= 1.5 ? 1 : 0;
  const want = tier;
  const gates = [];
  if (tier >= 4 && !(strike.length >= 5 && (parts.accent === 2 || vel >= 112))) { tier = 3; gates.push("legendary needs 5+ struck and a real accent"); }
  if (tier >= 3 && !(strike.length >= 4 && parts.accent)) { tier = 2; gates.push("epic needs 4+ struck and an accent"); }
  if (tier >= 2 && strike.length < 3) { tier = 1; gates.push("rare needs 3+ struck together"); }
  while (tier >= 2 && fxState.tokens[tier] < 1) { gates.push("no " + TIER_NAMES[tier] + " token"); tier--; }
  if (tier >= 2) fxState.tokens[tier] -= 1;
  return { score: +score.toFixed(2), want, tier, gates, parts, harmony: name, strike: strike.length, vel: Math.round(vel), mean: Math.round(mean) };
}
`;
mod = mod.slice(0, a) + SCORER + mod.slice(b);
writeFileSync(DIR + "fx_module.js", mod);

edit("patch_lab.mjs", [
  [`float lit = smoothstep(0.0, 0.04, energy) * (1.0 - smoothstep(1.4, 2.6, sAge)) * inX * uShimGain;`,
   `float lit = clamp(energy * 1.6, 0.0, 1.0) * (1.0 - smoothstep(1.4, 2.6, sAge)) * inX * uShimGain;`],
  [`shim += mix(mix(vColor, vec3(1.0), 0.3) * g, vec3(1.0, 0.62, 0.22) * g * 1.2 + fringe * g * 0.5, uShimGold);`,
   `shim += mix(mix(vColor, vec3(1.0), 0.15) * g, vec3(1.0, 0.62, 0.22) * g * 0.8 + fringe * g * 0.3, uShimGold);`],
  [`once(\`// ----------------------------------------------------------- notes engine --\`,`,
   `once(\`  stats.noteOns++;\`, \`  stats.noteOns++;
  fxNoteOn(vel, t);  // LAB spectacle: velocity history for the accent score\`);
once(\`// ----------------------------------------------------------- notes engine --\`,`],
]);

edit("vfx_check.mjs", [
  [`const OUT = join("E:\\\\AI-Setup\\\\state\\\\arsenal\\\\receipts\\\\piano-spectacle\\\\vfx", MODE);`,
   `const OUT = join("E:\\\\AI-Setup\\\\state\\\\arsenal\\\\receipts\\\\piano-spectacle\\\\vfx", process.argv[4] || MODE);`],
  [`JSON.stringify(e.why && { score: e.why.score, want: e.why.want, capped: e.why.capped, parts: e.why.parts, strike: e.why.strike, vel: e.why.vel })`,
   `JSON.stringify(e.why)`],
]);
console.log("v2 fixes applied");
