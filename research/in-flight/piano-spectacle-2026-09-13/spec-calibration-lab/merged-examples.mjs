// Spec calibration: the F major example table under the MERGED tier rule of spectacle-spec.md.
//   - fanciness F has no velocity term (the theory lab's examples already used a non-accent velocity, so F is unchanged)
//   - novelty may lift an event at most ONE tier above its no-novelty tier;
//     the one exception is "first time ever", which may lift two tiers, and only into Legendary or Mythic
// Reuses design-theory-rarity-lab (read-only): Theory, the scorer and the voicings. Run: node merged-examples.mjs
import { Theory } from "../design-theory-rarity-lab/theory.mjs";
import { intrinsic, personal, tierOf, TIERS } from "../design-theory-rarity-lab/rarity.mjs";
import { V } from "../design-theory-rarity-lab/voicings.mjs";

const key = { tonic: 5, mode: "major", name: "F major", bias: -1 };
const CTX = {
  start:      { Ns: 0,   ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 0,    nh1: 0,   nh2: 0,   bandShare: 0 },
  home:       { Ns: 150, ns1: 22, ns2: 24, lastSeenAgo: 3,        Nh: 5000, nh1: 750, nh2: 800, bandShare: 0.08 },
  occasional: { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 20,  nh2: 25,  bandShare: 0.08 },
  rareForYou: { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 4,   nh2: 5,   bandShare: 0.08 },
  firstEver:  { Ns: 100, ns1: 0,  ns2: 0,  lastSeenAgo: Infinity, Nh: 5000, nh1: 0,   nh2: 0,   bandShare: 0.08 },
};

export function mergedTier(F, pers, raise = 0) {
  const withN = tierOf(F, pers, raise);
  const base = tierOf(F, { ...pers, bonus: 0, novelty: null, lifetimeFirst: false }, raise);
  let rank = Math.min(withN.rank, base.rank + 1);
  if (pers.novelty === "first time ever" && withN.rank >= 4 && withN.rank <= base.rank + 2) rank = withN.rank;
  return { rank, tier: TIERS[rank].name, base: base.name ?? TIERS[base.rank].name, lifted: rank > base.rank, design: withN.tier };
}

const heads = ["voicing", "detect", "nashville", "F", ...Object.keys(CTX), "changed vs design table"];
console.log("| " + heads.join(" | ") + " |");
console.log("|" + heads.map(() => "---").join("|") + "|");
for (const [label, notes] of Object.entries(V)) {
  const info = Theory.detect(notes, key.bias);
  const s = intrinsic({ info, key, keyConfidence: "sure" });
  const cells = [], changed = [];
  for (const [name, c] of Object.entries(CTX)) {
    const m = mergedTier(s.F, personal(c));
    cells.push(m.tier);
    if (m.tier !== m.design) changed.push(`${name}: ${m.design} -> ${m.tier}`);
  }
  console.log("| " + [label, info.name, s.nv ? s.nv.text + (s.nv.diatonic ? "" : " (outside)") : "-", s.F.toFixed(2), ...cells, changed.join("; ") || ""].join(" | ") + " |");
}
