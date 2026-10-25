// Virtual Stage v0, the atmosphere: arsenal/web/stage/atmos.js (pure ES module). Tests: tests/stage_atmos.test.mjs.
//
// Haze is what makes a beam visible: light only reaches the eye from a beam if something in the air scatters it. Every
// volumetric pass in the renderer samples ONE medium, described here:
//
//   sigma(x, t) = sigma0 * H(t) * (1 + a * n(x - w t)) + sum over hazer plumes        (scattering coefficient, 1/m)
//
// H(t) is the haze master after the machines' lag: a hazer does not fill a hall instantly, the room's haze level moves
// toward the fader's target with a time constant of about 30 s (est.), so the Haze fader (F5) is a level that changes
// over minutes, never per beat. n is our own tileable noise, advected by a slow wind (0.1-0.5 m/s). Each hazer adds a
// soft plume around its nozzle while it runs. The albedo of haze is about 1, so extinction ~ scattering.
//
// Ranges (Koschmieder: visibility V = 3.912 / sigma): arena haze 0.003 to 0.02 1/m (about 1,300 m down to 200 m), a
// local fog burst up to 0.26 1/m (15 m). NEVER denser than that anywhere (the whiteout guard, receipt F1): clampSigma.
// Phase: Henyey-Greenstein, g = 0.75 for haze (F6: Colombi and Louedec 2013), g = 0.85 for fog and CO2.

export const ATMOS_API = "arsenal.stage-atmos/v1";
export const SIGMA_MIN = 0.003;
export const SIGMA_MAX = 0.02;
export const SIGMA_CAP = 0.26;
export const HAZE_G = 0.75;
export const FOG_G = 0.85;
export const MAX_HAZERS = 8;

export const visibility = (sigma) => 3.912 / sigma;
export const clampSigma = (s) => (s > SIGMA_CAP ? SIGMA_CAP : s < 0 ? 0 : s);

// Henyey-Greenstein (the same lobe as the house module volume/phase.glsl): mu = dot(viewDir, dirToLight).
export function phaseHG(mu, g) {
  const c = Math.max(-1, Math.min(1, mu)), gg = Math.max(-0.9999, Math.min(0.9999, g));
  const lean = 1 - gg * c, spread = lean * lean + gg * gg * (1 - c * c);
  return (1 - gg * gg) / (4 * Math.PI * spread * Math.sqrt(spread));
}

export class Atmosphere {
  constructor({ hazers = [], tau = 30, preHaze = 0.12, wind = [0.25, 0, -0.1], noiseAmp = 0.6 } = {}) {
    this.hazers = hazers.slice(0, MAX_HAZERS).map((h) => ({ ...h, output: h.out ?? 1 }));
    this.tau = tau;
    this.H = preHaze;            // the room's haze level 0..1 (pre-haze before doors: 10-15 %)
    this.target = preHaze;
    this.wind = wind.slice();
    this.offset = [0, 0, 0];     // the noise's advection, metres
    this.noiseAmp = noiseAmp;
    this.g = HAZE_G;
    this.uniform = { sigma0: 0, H: 0, noiseAmp, wind: this.offset, g: HAZE_G,
                     hazers: new Float32Array(MAX_HAZERS * 4), hazerSigma: new Float32Array(MAX_HAZERS), n: 0 };
  }
  setTarget(level) { this.target = Math.max(0, Math.min(1, level)); }
  // the room's base scattering coefficient at haze level H
  sigmaAt(H) { return clampSigma(SIGMA_MIN + (SIGMA_MAX - SIGMA_MIN) * H); }
  update(dt) {
    if (dt > 0) {
      const k = 1 - Math.exp(-dt / this.tau);
      this.H += (this.target - this.H) * k;
      for (let i = 0; i < 3; i++) this.offset[i] += this.wind[i] * dt;
    }
    const u = this.uniform;
    u.H = this.H;
    u.sigma0 = this.sigmaAt(this.H);
    u.n = this.hazers.length;
    for (let i = 0; i < MAX_HAZERS; i++) {
      const h = this.hazers[i];
      if (!h) { u.hazers.fill(0, i * 4, i * 4 + 4); u.hazerSigma[i] = 0; continue; }
      // the plume drifts downwind of the nozzle and spreads; its excess density follows the machine's output and the
      // room's level (a hazer at work while the room is still thin shows as a visible plume)
      u.hazers[i * 4] = h.pos[0] + this.wind[0] * 6; u.hazers[i * 4 + 1] = h.pos[1] + 1.5; u.hazers[i * 4 + 2] = h.pos[2] + this.wind[2] * 6;
      u.hazers[i * 4 + 3] = 7;
      u.hazerSigma[i] = clampSigma(0.012 * h.output * (0.4 + 0.6 * this.target));
    }
    return u;
  }
  // the density at a point, the CPU twin of the shader's hazeDensity (without the noise texture: n = 0), for receipts
  densityAt(p, noise = 0) {
    const u = this.uniform;
    let s = u.sigma0 * Math.max(0, 1 + u.noiseAmp * noise);
    for (let i = 0; i < u.n; i++) {
      const dx = p[0] - u.hazers[i * 4], dy = p[1] - u.hazers[i * 4 + 1], dz = p[2] - u.hazers[i * 4 + 2], r = u.hazers[i * 4 + 3];
      s += u.hazerSigma[i] * Math.exp(-(dx * dx + dy * dy + dz * dz) / (r * r));
    }
    return clampSigma(s);
  }
}

// Our own tileable value noise for the 3D texture (size^3, 8-bit): a lattice of hashed values, smoothly interpolated, two
// octaves; it wraps at the edges so the advected field never shows a seam.
export function hazeNoise3D(size = 32, seed = 2014) {
  const N = size;
  const lat = new Float32Array(N * N * N);
  let a = seed >>> 0;
  const r = () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  for (let i = 0; i < lat.length; i++) lat[i] = r();
  const L = (x, y, z) => lat[((z % N + N) % N) * N * N + ((y % N + N) % N) * N + ((x % N + N) % N)];
  const s = (t) => t * t * (3 - 2 * t);
  const sample = (x, y, z, period) => {
    // value noise with a lattice of `period` cells across the tile
    const f = period / N;
    const X = x * f, Y = y * f, Z = z * f;
    const xi = Math.floor(X), yi = Math.floor(Y), zi = Math.floor(Z);
    const fx = s(X - xi), fy = s(Y - yi), fz = s(Z - zi);
    const P = period, w = (v) => ((v % P) + P) % P;
    const c = (i, j, k) => L(w(xi + i) * (N / P) | 0, w(yi + j) * (N / P) | 0, w(zi + k) * (N / P) | 0);
    const lx = (j, k) => c(0, j, k) + (c(1, j, k) - c(0, j, k)) * fx;
    const ly = (k) => lx(0, k) + (lx(1, k) - lx(0, k)) * fy;
    return ly(0) + (ly(1) - ly(0)) * fz;
  };
  const out = new Uint8Array(N * N * N);
  let i = 0;
  for (let z = 0; z < N; z++) for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const v = 0.65 * sample(x, y, z, 4) + 0.35 * sample(x, y, z, 8);
    out[i++] = Math.max(0, Math.min(255, Math.round(v * 255)));
  }
  return out;
}
