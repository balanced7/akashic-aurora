// v3 scorer: Legendary is the top of an arc (a run of block strikes, each louder than the last, ending loud),
// and Uncommon needs 2.5 points instead of 1.5 (v2 fired it on 22 of 39 chord changes).
import { readFileSync, writeFileSync } from "node:fs";
const FILE = "C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/fx_module.js";
let src = readFileSync(FILE, "utf8").replace(/\r\n/g, "\n");
const once = (from, to) => {
  const n = src.split(from).length - 1;
  if (n !== 1) throw new Error(`expected one match (${n}) for:\n${from}`);
  src = src.replace(from, to);
};
once(`let tier = score >= 8 ? 4 : score >= 6 ? 3 : score >= 4.5 ? 2 : score >= 1.5 ? 1 : 0;`,
     `let tier = score >= 8 ? 4 : score >= 6 ? 3 : score >= 4.5 ? 2 : score >= 2.5 ? 1 : 0;`);
once(`  const score = Object.values(parts).reduce((x, y) => x + y, 0);`,
     `  // v3: an arc. The third or later block strike in a run where each is louder than the last (by 4+, within 12 s),
  // ending at velocity 105+, is a climax, whatever its chord.
  if (strike.length >= 3) {
    const S = fxState.strikes || (fxState.strikes = []);
    if (!S.length || newest - S[S.length - 1].t > 0.2) S.push({ t: newest, vel });
    let run = 1;
    for (let i = S.length - 1; i > 0 && S[i].vel >= S[i - 1].vel + 4 && S[i].t - S[i - 1].t <= 12; i--) run++;
    if (run >= 3 && vel >= 105) parts.arc = 1.5;
  }
  const score = Object.values(parts).reduce((x, y) => x + y, 0);`);
writeFileSync(FILE, src);
console.log("v3 scorer applied");
