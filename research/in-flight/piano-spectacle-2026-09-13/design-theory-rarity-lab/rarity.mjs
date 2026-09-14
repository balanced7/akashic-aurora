// Rarity scale calibration model (design lab only; not wired into piano.js).
// Pure: takes a Theory.detect result + key context + performance context + personal counts.
import { Theory } from "./theory.mjs";
import { nashville } from "./nashville.mjs";

const mod = (a, n) => ((a % n) + n) % n;
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };

// C: chord colour by Theory.TEMPLATES suffix
export const COLOUR = {
  "5": 0, "": 0, m: 0,
  sus2: 0.75, sus4: 0.75,
  "6": 1.25, m6: 1.5, add9: 1.25, "m(add9)": 1.5, "7": 1.25, m7: 1.25, dim: 1.25,
  maj7: 2.0, aug: 2.0, m7b5: 2.25, dim7: 2.5, "7sus4": 1.75, add11: 1.75,
  "6/9": 2.25, "m6/9": 2.5,
  "9": 2.75, m9: 2.75, maj9: 3.0, "9sus4": 3.0, "m(maj7)": 3.25,
  "11": 3.25, m11: 3.25, "13": 3.5, m13: 3.5, maj13: 3.75,
  "maj7#11": 4.0, "7#11": 4.0, "7b5": 4.0, "7#5": 4.0, "maj7#5": 4.25,
  "7b9": 4.5, "7#9": 4.5,
};

const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const MINOR = [0, 2, 3, 5, 7, 8, 10, 11]; // natural minor + leading tone, as nashville FITS reads minor keys

function bassScore(info) {
  if (!info.bass) return { B: 0, why: null };
  const rootPc = Theory.pcOf(info.root), bassPc = Theory.pcOf(info.bass);
  const rel = mod(bassPc - rootPc, 12);
  const tone = Theory.TEMPLATES.filter((t) => t.suffix === info.suffix)
    .flatMap((t) => t.tones).find((x) => x[0] === rel);
  if (!tone) return { B: 1.75, why: "foreign bass" };
  const steps = tone[1];
  if (steps === 2) return { B: 0.75, why: "3rd in the bass" };
  if (steps === 4) return { B: 0.5, why: "5th in the bass" };
  if (steps === 6 || (steps === 5 && info.suffix === "dim7")) return { B: 1.25, why: "7th in the bass" };
  return { B: 1.5, why: "colour note in the bass" };
}

export function voicingScore(notes) {
  const span = notes[notes.length - 1].midi - notes[0].midi;
  const count = notes.length;
  let V = 0;
  if (span >= 24) V += 0.25;
  if (span >= 36) V += 0.25;
  if (count >= 6) V += 0.25;
  if (count >= 8) V += 0.25;
  if (notes.length >= 3 && notes[1].midi - notes[0].midi >= 7) V += 0.15;
  return { V: Math.min(V, 1.0), span, count };
}

function outsideTones(pcs, key) {
  const scale = (key.mode === "major" ? MAJOR : MINOR).map((s) => mod(key.tonic + s, 12));
  return pcs.filter((pc) => !scale.includes(pc)).length;
}

function keyScoreOne(info, pcs, key) {
  const out = outsideTones(pcs, key);
  const nv = nashville(info, key);
  const K = 0.75 * out + (nv && !nv.diatonic ? 0.75 : 0);
  return { K: Math.min(K, 3), out, nv };
}

// ev: { info, key, keyConfidence, candidateKey, peakVel, medianVel, pedalBlendShare, pedalPoint }
export function intrinsic(ev) {
  const { info } = ev;
  if (!info || info.kind !== "chord" || info.suffix === "5") return { F: 0, core: 0, parts: {}, reasons: [], scorable: false };
  const pcs = [...new Set(info.notes.map((n) => mod(n.midi, 12)))];
  const C = COLOUR[info.suffix] ?? 2.0;
  const { B, why: bassWhy } = bassScore(info);
  const { V } = voicingScore(info.notes);
  let K = 0, nv = null, out = 0;
  if (ev.key && ev.keyConfidence !== "unsure") {
    const a = keyScoreOne(info, pcs, ev.key);
    K = a.K; nv = a.nv; out = a.out;
    if (ev.candidateKey) { const b = keyScoreOne(info, pcs, ev.candidateKey); if (b.K < K) { K = b.K; out = b.out; } }
    if (ev.keyConfidence === "fair") K *= 0.6;
  }
  let P = 0;
  if (ev.peakVel != null && ev.medianVel != null && ev.peakVel - ev.medianVel >= 25) P += 0.3;
  if (ev.pedalPoint) P += 0.2;
  P = Math.min(P, 0.5);
  let F = C + B + V + K + P;
  const reasons = [];
  if (K >= 2.25) reasons.push("far outside the key");
  else if (K >= 1.5) reasons.push("outside the key");
  else if (K > 0) reasons.push("borrowed note");
  if (C >= 4.5) reasons.push("altered dominant");
  else if (C >= 4.0) reasons.push("sharp or flat colour");
  else if (C >= 2.75) reasons.push("rich extension");
  else if (C >= 2.0) reasons.push("seventh colour");
  if (bassWhy && B >= 1.25) reasons.push(bassWhy);
  if (V >= 0.75) reasons.push("wide voicing");
  if (P >= 0.3) reasons.push("accented");
  if (ev.pedalPoint) reasons.push("pedal point");
  let capped = null;
  if (ev.pedalBlendShare != null && ev.pedalBlendShare > 0.4) { F = Math.min(F, 2.0); capped = "pedal blend"; }
  if (info.cost != null && info.cost >= 4.2) { F = Math.min(F, 3.0); capped = capped || "uncertain reading"; }
  return { F, core: C + B + K, parts: { C, B, V, K, P }, reasons, capped, nv, scorable: true };
}

export const TIERS = [
  { name: "Common", phi: -Infinity, F: 0 },
  { name: "Uncommon", phi: 2.0, F: 0 },
  { name: "Rare", phi: 4.0, F: 2.0 },
  { name: "Epic", phi: 5.25, F: 3.0 },
  { name: "Legendary", phi: 6.75, F: 5.0, personal: true },   // also needs bonus >= 1.25, unless F >= 7
  { name: "Mythic", phi: 8.0, F: 5.5, lifetimeFirst: true },
];

// id1: the key-relative number with its bass ("4maj7/3"); id2: without the bass ("4maj7"). No key: the names.
export function identities(info, nv) {
  if (nv) return { id1: nv.text, id2: nv.text.split("/")[0] };
  return { id1: info.name, id2: info.name.split("/")[0] };
}

// c: { Ns, ns1, ns2, lastSeenAgo, Nh, nh1, nh2, bandShare }
//   Ns: committed chords so far this session; ns1/ns2: this identity's count this session
//   lastSeenAgo: committed chords since id2 was last seen this session (Infinity if not yet)
//   Nh, nh1, nh2: the same counts across every earlier logged session
//   bandShare: the share of his chords (tonight + history) whose core fanciness is at least this chord's, minus 0.25
export function personal(c) {
  const w = Math.min(1, 600 / Math.max(c.Nh, 1));
  const N = c.Ns + w * c.Nh;
  const blended = N >= 20 ? (0.7 * (c.ns1 + w * c.nh1) + 0.3 * (c.ns2 + w * c.nh2)) / N : 0;
  const tonight = c.Ns >= 20 ? (0.7 * c.ns1 + 0.3 * c.ns2) / c.Ns : 0;
  const share = Math.max(blended, tonight);
  const lifeShare = c.Nh > 0 ? c.nh2 / c.Nh : 0;
  const mature = c.Nh >= 2000;
  const firstSession = c.ns2 === 0;
  const oftenForYou = mature && lifeShare >= 0.01;
  let bonus = 0, novelty = null;
  if (mature && c.nh2 === 0 && firstSession) { bonus = 2.0; novelty = "first time ever"; }
  else if (mature && lifeShare < 1 / 500 && firstSession) { bonus = 1.25; novelty = "rare for you"; }
  else if (!mature && c.Ns >= 150 && firstSession) { bonus = 1.25; novelty = "first time tonight"; }
  else if (c.Ns >= 40 && firstSession && !oftenForYou) { bonus = 0.75; novelty = "first this session"; }
  else if (!firstSession && c.lastSeenAgo >= 150 && !oftenForYou) { bonus = 0.4; novelty = "back again"; }
  const famId = smooth(0.03, 0.12, share);
  const famBand = smooth(0.10, 0.30, c.bandShare || 0);
  const h = Math.max(0.5, 1 - 0.45 * famId - 0.25 * famBand);
  return { bonus, novelty, h, famId, famBand, share, lifeShare, mature, lifetimeFirst: novelty === "first time ever" };
}

export function tierOf(F, pers, raise = 0) {
  const phi = F * pers.h + pers.bonus;
  let tier = TIERS[0];
  for (const t of TIERS) {
    if (t.name === "Common") continue;
    const lift = t.phi >= 4.0 ? raise : 0;
    if (phi < t.phi + lift || F < t.F) continue;
    if (t.personal && !(pers.bonus >= 1.25 || F >= 7)) continue;
    if (t.lifetimeFirst && !pers.lifetimeFirst) continue;
    tier = t;
  }
  return { phi, tier: tier.name, rank: TIERS.indexOf(tier) };
}
