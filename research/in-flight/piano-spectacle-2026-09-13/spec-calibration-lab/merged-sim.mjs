// Spec calibration: the theory-rarity lab's sessions re-run under the MERGED rules of spectacle-spec.md.
// Differences from design-theory-rarity-lab/sim.mjs (which is imported read-only for its Theory, scorer and voicings):
//   1. no velocity accent in fanciness (velocity sizes effects, never the tier)
//   2. novelty can lift an event at most ONE tier above its no-novelty tier
//   3. no Legendary banner in the first 45 s of the session
//   4. counts Common rail pulses with the home-chord suppression (Common and h < 0.75 -> no pulse)
// Run: node merged-sim.mjs  (Node 24)
import { Theory } from "../design-theory-rarity-lab/theory.mjs";
import { intrinsic, personal, tierOf, identities } from "../design-theory-rarity-lab/rarity.mjs";
import { V, GROUPS } from "../design-theory-rarity-lab/voicings.mjs";

let seed = 12345;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32; };
const pick = (xs) => xs[Math.floor(rnd() * xs.length)];
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const key = { tonic: 5, mode: "major", name: "F major", bias: -1 };

const STYLES = {
  daniel:   { loop: 0.58, everyday: 0.22, lush: 0.12, borrowed: 0.06, far: 0.02 },
  triads:   { triads: 1 },
  explorer: { loop: 0.25, everyday: 0.2, lush: 0.3, borrowed: 0.17, far: 0.08 },
};
function chooseChord(style, i) {
  let r = rnd();
  for (const [g, p] of Object.entries(STYLES[style])) {
    if ((r -= p) <= 0) {
      if (g === "loop") return GROUPS.loop[i % 4];
      if (g === "triads") return GROUPS.triads[i % 4];
      return pick(GROUPS[g]);
    }
  }
  return GROUPS.loop[i % 4];
}
function voice(notes) {
  const n = [...notes];
  if (rnd() < 0.3) n.push(n[n.length - 1] + 12);
  if (rnd() < 0.2 && n[0] - 12 >= 21) n.unshift(n[0] - 12);
  return n;
}

const RANKS = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"];
const COOL = { Rare: 12, Epic: 30, Legendary: 120 };
const LEGENDARY_WARMUP = 45;

function createGate() {
  const lastAt = { Rare: -1e9, Epic: -1e9, Legendary: -1e9, Mythic: -1e9 };
  let lastBanner = -1e9, mythicShown = false;
  const lastId = new Map(), idCount = new Map();
  const rarePlus = [];
  return {
    raise(t) {
      while (rarePlus.length && t - rarePlus[0] > 300) rarePlus.shift();
      const over = rarePlus.length - 15;
      return over > 0 ? Math.min(0.75, 0.25 * Math.ceil(over / 5)) : 0;
    },
    scored(rank, t) { if (rank >= 2) rarePlus.push(t); },
    tryBanner(tier, rank, id2, t) {
      if (rank < 2) return false;
      if (t - lastBanner < 6) return false;
      if (tier === "Legendary" && t < LEGENDARY_WARMUP) return false;
      if (tier === "Mythic") { if (mythicShown) return false; }
      else {
        const since = Math.max(...RANKS.slice(rank).filter((r) => r in lastAt).map((r) => lastAt[r]));
        if (t - since < COOL[tier]) return false;
      }
      if (t - (lastId.get(id2) ?? -1e9) < 90 || (idCount.get(id2) || 0) >= 3) return false;
      lastBanner = t; lastAt[tier] = t; if (tier === "Mythic") mythicShown = true;
      lastId.set(id2, t); idCount.set(id2, (idCount.get(id2) || 0) + 1);
      return true;
    },
  };
}

function scoreEvent(ctx, info, t) {
  const s = intrinsic({ info, key, keyConfidence: "sure" });  // no peakVel: rule 1
  if (!s.scorable) { ctx.scored.Common++; ctx.pulses++; return; }
  const { id1, id2 } = identities(info, s.nv);
  const h = ctx.history;
  const last = ctx.last2.get(id2);
  const f0 = s.core - 0.25;
  const wH = Math.min(1, 600 / Math.max(h.N, 1));
  const denom = ctx.Ns + wH * h.N;
  const bandShare = denom >= 20
    ? (ctx.cores.filter((x) => x >= f0).length + wH * h.cores.filter((x) => x >= f0).length) / denom : 0;
  const pers = personal({ Ns: ctx.Ns, ns1: ctx.s1.get(id1) || 0, ns2: ctx.s2.get(id2) || 0,
                          lastSeenAgo: last == null ? Infinity : ctx.Ns - last,
                          Nh: h.N, nh1: h.id1.get(id1) || 0, nh2: h.id2.get(id2) || 0, bandShare });
  const raise = ctx.gate.raise(t);
  const withN = tierOf(s.F, pers, raise);
  const without = tierOf(s.F, { ...pers, bonus: 0, lifetimeFirst: false }, raise);
  let rank = Math.min(withN.rank, without.rank + 1);  // rule 2
  // the one exception: "first time ever" may lift two tiers, only into Legendary or Mythic (as merged-examples.mjs)
  if (pers.novelty === "first time ever" && withN.rank >= 4 && withN.rank <= without.rank + 2) rank = withN.rank;
  if (rank < withN.rank) ctx.capped++;
  const tier = RANKS[rank];
  ctx.scored[tier]++;
  if (rank >= 1 || pers.h >= 0.75) ctx.pulses++;  // rule 4: a Common home chord gets no rail pulse
  ctx.gate.scored(rank, t);
  if (ctx.gate.tryBanner(tier, rank, id2, t)) {
    ctx.banners[tier]++;
    const why = [rank > without.rank ? pers.novelty : null, ...s.reasons].filter(Boolean).slice(0, 2).join(", ");
    ctx.log.push(`${t.toFixed(0).padStart(3)}s ${tier.toUpperCase()} · ${info.name} · ${s.nv ? s.nv.text : "-"}  (F ${s.F.toFixed(2)}, h ${pers.h.toFixed(2)}, phi ${withN.phi.toFixed(2)}; ${why})`);
  }
  ctx.s1.set(id1, (ctx.s1.get(id1) || 0) + 1);
  ctx.s2.set(id2, (ctx.s2.get(id2) || 0) + 1);
  ctx.last2.set(id2, ctx.Ns);
  ctx.cores.push(s.core);
  ctx.Ns++;
}
function newCtx(history) {
  return { history, gate: createGate(), Ns: 0, s1: new Map(), s2: new Map(), last2: new Map(), cores: [], pulses: 0, capped: 0,
           scored: Object.fromEntries(RANKS.map((r) => [r, 0])), banners: Object.fromEntries(RANKS.map((r) => [r, 0])), log: [] };
}
function runSession(style, history, { seconds = 600, meanGap = 2.0 } = {}) {
  const ctx = newCtx(history);
  let t = 0, i = 0;
  while (t < seconds) {
    t += meanGap * (0.6 + 0.8 * rnd());
    const label = chooseChord(style, i++);
    // velocity is drawn (and ignored) so the random sequence, and so the chords, match design-theory-rarity-lab/sim.mjs
    void Math.round(clamp(70 + 36 * (rnd() - 0.5) + (rnd() < 0.08 ? 35 : 0), 20, 127));
    scoreEvent(ctx, Theory.detect(voice(V[label]), key.bias), t);
  }
  ctx.seconds = seconds;
  return ctx;
}
function emptyHistory() { return { N: 0, id1: new Map(), id2: new Map(), cores: [] }; }
const copyH = (h) => ({ N: h.N, id1: new Map(h.id1), id2: new Map(h.id2), cores: [...h.cores] });
function absorb(h, ctx) {
  h.N += ctx.Ns;
  for (const [k, v] of ctx.s1) h.id1.set(k, (h.id1.get(k) || 0) + v);
  for (const [k, v] of ctx.s2) h.id2.set(k, (h.id2.get(k) || 0) + v);
  h.cores.push(...ctx.cores);
}
function report(title, ctx) {
  const n = Object.values(ctx.scored).reduce((a, b) => a + b, 0);
  const pct = (x) => ((100 * x) / n).toFixed(1) + "%";
  console.log(`\n## ${title}: ${n} scored events`);
  console.log("scored:  " + RANKS.map((r) => `${r} ${ctx.scored[r]} (${pct(ctx.scored[r])})`).join(" · "));
  console.log("banners: " + RANKS.slice(2).map((r) => `${r} ${ctx.banners[r]}`).join(" · "));
  console.log(`rail pulses per minute (home-chord suppression): ${(ctx.pulses / (ctx.seconds / 60)).toFixed(1)} of ${(n / (ctx.seconds / 60)).toFixed(1)} events/min · novelty cap applied ${ctx.capped}x`);
  for (const line of ctx.log) console.log("   " + line);
}

const h = emptyHistory();
const s1 = runSession("daniel", h); report("A'. Daniel style, first session, no history", s1); absorb(h, s1);
for (let k = 2; k <= 9; k++) absorb(h, runSession("daniel", copyH(h)));
console.log(`\n(history after 9 sessions: ${h.N} chords, ${h.id2.size} distinct chords-without-bass)`);
report("B'. Daniel style, 10th session", runSession("daniel", copyH(h)));
report("C'. Plain triad loop (F C Dm Bb), with that history", runSession("triads", copyH(h)));
report("D'. Explorer session, with that history", runSession("explorer", copyH(h)));
report("E'. Explorer session, no history", runSession("explorer", emptyHistory()));

const sweep = { Rare: [], Epic: [], Legendary: [], Mythic: [], pulsesPerMin: [] };
for (let sd = 1; sd <= 20; sd++) {
  seed = sd * 7919;
  const run = runSession("daniel", copyH(h));
  for (const r of ["Rare", "Epic", "Legendary", "Mythic"]) sweep[r].push(run.banners[r]);
  sweep.pulsesPerMin.push(+(run.pulses / 10).toFixed(1));
}
const stat = (xs) => `mean ${(xs.reduce((a, b) => a + b, 0) / xs.length).toFixed(1)} (min ${Math.min(...xs)}, max ${Math.max(...xs)})`;
console.log("\n## G'. 20 seeds, Daniel style 10th session, banners per 10 min (merged rules)");
for (const [k, xs] of Object.entries(sweep)) console.log(`  ${k}: ${stat(xs)}`);
