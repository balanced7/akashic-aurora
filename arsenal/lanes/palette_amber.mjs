// The amber receipt (node only: no browser, no GPU): what KICK COLOUR actually shows on the moving heads, per palette, by
// the method of research/in-flight/palettes-2026-10-28/inventory.md section 4 (measure_kick_colour.mjs) -- for each look,
// 12 colour-kick presses a bar apart, the deck dealing as it deals, held 2 beats at velocity 0.7, each kicked head's wheel
// slot read 1.5 beats in -- plus the same for the white kick (does any wheel move?).
//
//   node arsenal/lanes/palette_amber.mjs [--palettes a,b,...] [--looks intro,build,drop,break,groove] [--out file.json]
//
// Before the palettes (2026-10-28, the combined build's themes) the halo showed the wheel's warm white (slot 12, the CTO
// #ffd8a0) on 100 % of its colour-kicked head frames in Source Violet, Dreaming City and Genesis Indigo, the beams on 53-56 %.
import { readFileSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { fileURLToPath } from "node:url";
import { expandScene } from "../web/stage/rig.js";
import { Programmer } from "../web/stage/programmer.js";
import { BeatGrid } from "../web/stage/grid.js";
import { loadPalettes, stageTheme, planOf, lchOf, hueGap, CTO_SLOT } from "../web/palettes.js";

const { values: opt } = parseArgs({ options: { palettes: { type: "string", default: "" }, looks: { type: "string", default: "intro,build,drop,break,groove" },
                                               presses: { type: "string", default: "12" }, out: { type: "string", default: "" } } });
const WEB = fileURLToPath(new URL("../web/", import.meta.url));
const SCENE = JSON.parse(readFileSync(`${WEB}stage/sets/source-v1.json`, "utf8"));
const RIG = expandScene(SCENE);
const WHEEL = SCENE.types["beam-7r"].attrs.Color1.colours;
const NAME = ["white", "red", "orange", "yellow", "lime", "green", "cyan", "sky", "deep blue", "violet", "magenta", "pink", "warm white (CTO)", "deep violet"];
const LIB = loadPalettes(JSON.parse(readFileSync(`${WEB}palettes.json`, "utf8")), { wheel: WHEEL });
const IDS = opt.palettes ? opt.palettes.split(",").filter((x) => LIB.byId[x]) : LIB.ids;
const LOOKS = opt.looks.split(","), PRESSES = Number(opt.presses) || 12, FPS = 60;

function locked(bpm) { const g = new BeatGrid({ bpm, t0: 0 }); g.beat({ due_ms: 0, bpm, n: 0, conf: 1, bar: 1, ver: 0 }, 0); return g; }
function run(id, kind) {
  const pal = LIB.byId[id], plan = planOf(pal);
  const fam = [...pal.kick.ladder, ...pal.colours.filter((c) => ["base", "partner", "mid", "accent"].includes(c.role)).map((c) => c.hex)].map(lchOf);
  const byArea = {};
  let presses = 0, unlit = 0, wheelMoves = 0, headFrames = 0;
  for (const look of LOOKS) {
    const p = new Programmer(RIG, { theme: stageTheme(pal), seed: 7 });
    p.setLook(look, 0);
    const g = locked(150);
    let k = 0, pending = null;
    for (let t = 0; t < (4 + PRESSES * 4 + 4) * g.period; t += 1000 / FPS) {
      const pos = g.posAt(t);
      if (pos >= 4 + 4 * k && k < PRESSES && !pending) {
        const before = Array.from({ length: p.nH }, (_, i) => p.wheelSlotOf(i));
        const rec = p.pad(kind, 0.7, pos, { hold: true });
        presses++;
        if (!rec) unlit++;
        pending = rec ? { rec, at: pos, before } : null;
        k++;
      }
      p.tick(g, t, 1 / FPS);
      if (pending && pos >= pending.at + 1.5) {
        const { rec, before } = pending, a = (byArea[rec.card.name] = byArea[rec.card.name] || { presses: 0, frames: 0, slots: {}, cto: 0, palette: 0, moved: 0 });
        a.presses++;
        for (const i of rec.card.heads) {
          const s = p.wheelSlotOf(i);
          a.frames++; headFrames++;
          a.slots[NAME[s]] = (a.slots[NAME[s]] || 0) + 1;
          if (s === CTO_SLOT) a.cto++;
          if (s !== before[i]) { a.moved++; wheelMoves++; }
          if (s !== 0 && fam.some((f) => hueGap(f.h, lchOf(WHEEL[s]).h) <= 45)) a.palette++;
        }
        p.padRelease(kind, pos);
        pending = null;
      }
    }
  }
  let frames = 0, cto = 0, palette = 0;
  for (const a of Object.values(byArea)) { frames += a.frames; cto += a.cto; palette += a.palette; a.cto_share = a.frames ? +(a.cto / a.frames).toFixed(4) : null; a.palette_share = a.frames ? +(a.palette / a.frames).toFixed(4) : null; }
  return { id, kind, presses, unlit, head_frames: frames, cto_frames: cto, cto_share: frames ? +(cto / frames).toFixed(4) : 0,
           palette_share: frames ? +(palette / frames).toFixed(4) : 0, wheel_moves: wheelMoves, white_kicks_only: plan.whiteKicksOnly, warm: !!pal.warm_declared, areas: byArea };
}
const rows = [];
for (const id of IDS) {
  const c = run(id, "kick-colour"), w = run(id, "kick-white");
  rows.push({ id, colour: c, white: { presses: w.presses, unlit: w.unlit, head_frames: w.head_frames, wheel_moves: w.wheel_moves, cto_frames: w.cto_frames } });
  const area = (n) => (c.areas[n] ? `${n} ${(100 * c.areas[n].cto_share).toFixed(0)} % CTO / ${(100 * c.areas[n].palette_share).toFixed(0)} % palette (${c.areas[n].frames})` : `${n} -`);
  console.log(`${id.padEnd(17)} colour kick: head frames ${String(c.head_frames).padStart(5)}, warm white ${(100 * c.cto_share).toFixed(1)} %, palette colour ${(100 * c.palette_share).toFixed(1)} % | ${area("halo")} | ${area("beams")} | ${area("strand")} | white kick: ${w.head_frames} head frames, ${w.wheel_moves} wheels moved`);
}
const total = rows.reduce((s, r) => ({ f: s.f + r.colour.head_frames, c: s.c + r.colour.cto_frames, w: s.w + r.white.wheel_moves, u: s.u + r.colour.unlit + r.white.unlit }), { f: 0, c: 0, w: 0, u: 0 });
console.log(`ALL ${rows.length} palettes: colour-kick head frames ${total.f}, on the warm white ${total.c} (${(100 * total.c / Math.max(1, total.f)).toFixed(2)} %); white-kick wheel moves ${total.w}; unlit presses ${total.u}`);
if (opt.out) writeFileSync(opt.out, JSON.stringify({ method: "inventory.md section 4", looks: LOOKS, presses: PRESSES, rows, total }, null, 1));
