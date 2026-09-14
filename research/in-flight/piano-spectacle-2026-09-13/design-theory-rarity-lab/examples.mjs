import { Theory } from "./theory.mjs";
import { intrinsic, personal, tierOf } from "./rarity.mjs";
import { V } from "./voicings.mjs";

const key = { tonic: 5, mode: "major", name: "F major", bias: -1 };
const CTX = {
  // the first chords of a session, no log yet
  start:      { Ns: 0,   ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 0,    nh1: 0,   nh2: 0,   bandShare: 0 },
  // a home chord: 15% of everything he plays
  home:       { Ns: 150, ns1: 22, ns2: 24, lastSeenAgo: 3,        Nh: 5000, nh1: 750, nh2: 800, bandShare: 0.08 },
  // played before, 0.5% of his history, first time this session
  occasional: { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 20,  nh2: 25,  bandShare: 0.08 },
  // seen 5 times in 5000 (0.1%), first time this session
  rareForYou: { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 4,   nh2: 5,   bandShare: 0.08 },
  // never in 5000 logged chords
  firstEver:  { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 0,   nh2: 0,   bandShare: 0.08 },
};
const heads = ["voicing", "detect", "nashville", "cost", "C", "B", "V", "K", "F", ...Object.keys(CTX), "reasons"];
console.log(heads.join(" | "));
for (const [label, notes] of Object.entries(V)) {
  const info = Theory.detect(notes, key.bias);
  const s = intrinsic({ info, key, keyConfidence: "sure", peakVel: 80, medianVel: 78 });
  const p = s.parts;
  const tiers = Object.values(CTX).map((c) => tierOf(s.F, personal(c)).tier);
  console.log([label, info.name, s.nv ? s.nv.text + (s.nv.diatonic ? "" : " (outside)") : "-",
    (info.cost ?? 0).toFixed(1), p.C, p.B, p.V?.toFixed(2), p.K?.toFixed(2), s.F.toFixed(2), ...tiers,
    s.reasons.slice(0, 2).join(", ") + (s.capped ? ` [cap: ${s.capped}]` : "")].join(" | "));
}
