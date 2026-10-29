// The chord phrasing's replay: Daniel's recorded takes through the recogniser (arsenal/web/stage/grammar.js), offline.
//
//   node arsenal/lanes/grammar_replay.mjs <take.jsonl> [<take.jsonl> ...] [--out <file.json>]
//
// Daniel, 2026-10-29: "lets also land the chord phrasing." The takes (state/arsenal/performance/kick-session-*.jsonl in the
// main checkout) are PRIVATE and gitignored: this lane reads them and reports COUNTS and interval distributions only --
// never a key sequence, never a timestamp. Its output goes to the receipts folder (gitignored) or --out.
//
// What it does: every keyboard record ({src: "key", key, down, repeat, os_ms, pc}) of the number row and C enters the
// recogniser as the "key" source at its OS timestamp (os_ms), in recorded order; the utility keys (F, H, Shift, minus,
// MARK) never enter it, as on the page. B (ms per beat) is the engine's last beat's bpm when that beat is fresh (under two
// seconds old by the recorder's clock), else the recogniser's 400 ms. The recogniser's decisions are what the page would
// have decided; nothing here says whether Daniel MEANT a chord, a strum or a fade. Precision and recall need his
// annotations of the takes (the design's acceptance: per-class precision, recall and false takeovers per minute against
// labelled gestures), which do not exist yet -- so this lane measures neither.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { Grammar, windowsFor, positionOf } from "../web/stage/grammar.js";
import { Ensembles } from "../web/stage/ensemble.js";

const REPO = fileURLToPath(new URL("../..", import.meta.url)).replace(/[\\/]+$/, "");
const { values: opt, positionals } = parseArgs({ allowPositionals: true, options: { out: { type: "string", default: "" }, clock: { type: "string", default: "os" } } });
// --clock os: the key's OS timestamp (os_ms: the design's source timestamp, but Windows ticks it in ~15.6 ms steps);
// --clock pc: the recorder's performance counter at receipt (sub-millisecond, but it carries the delivery's jitter)
if (!["os", "pc"].includes(opt.clock)) { console.log("--clock os|pc"); process.exit(2); }
if (!positionals.length) { console.log("usage: node arsenal/lanes/grammar_replay.mjs <take.jsonl> [...] [--out file.json]"); process.exit(2); }

const q = (xs, p) => { if (!xs.length) return null; const s = xs.slice().sort((a, b) => a - b); return +s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 0.5))].toFixed(1); };
const dist = (xs) => ({ n: xs.length, p10: q(xs, 0.1), p50: q(xs, 0.5), p90: q(xs, 0.9), min: xs.length ? +Math.min(...xs).toFixed(1) : null, max: xs.length ? +Math.max(...xs).toFixed(1) : null });
const hist = (xs, edges) => { const h = new Array(edges.length + 1).fill(0); for (const x of xs) { let i = 0; while (i < edges.length && x > edges[i]) i++; h[i]++; } return h; };

function replay(file) {
  const lines = readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean);
  const recs = [];
  for (const l of lines) { try { recs.push(JSON.parse(l)); } catch { /* a torn last line */ } }
  let beat = null;                      // {bpm, pc}
  let nowPc = 0;
  // the ensembles as the page wires them: canFade reads the fade's target, every decision is planned (the BREATH path)
  const ens = new Ensembles();
  const g = new Grammar({ beatMs: () => (beat && nowPc - beat.pc < 2 && beat.bpm > 0 ? 60000 / beat.bpm : null), canFade: (dir) => ens.canFade(dir) });
  const all = [];
  const breathPath = [];                // [t, target] after every decision that moved it
  let noopTakeovers = 0;
  const lineageStart = new Map();       // lineage -> {t0, strum, W}: a new attack identity inside a strum's W is a split gesture
  let strumSplits = 0;
  const plan = (d, t) => {
    const before = ens.breath.target;
    ens.plan(d);
    if (d.type === "breath" && (d.phase === "start" || d.phase === "step") && ens.breath.target === before) noopTakeovers++;
    if (ens.breath.target !== before) breathPath.push([t, ens.breath.target]);
    if (d.type === "press" && !lineageStart.has(d.lineage)) {
      for (const L of lineageStart.values()) if (L.strum && d.t - L.t0 <= L.W) strumSplits++;
      lineageStart.set(d.lineage, { t0: d.t, strum: false, W: windowsFor(g.B()).W });
      if (lineageStart.size > 64) lineageStart.delete(lineageStart.keys().next().value);
    }
    if (d.type === "reclassify" && d.to === "strum" && lineageStart.has(d.lineage)) lineageStart.get(d.lineage).strum = true;
  };
  let fresh = 0, keys = 0, utility = 0, lastKeyT = null;
  const downGaps = [];                  // consecutive number-row/C downs, ms
  let firstT = null, lastT = null;
  for (const r of recs) {
    if (r.ev && r.ev.t === "beat" && Number.isFinite(r.ev.bpm)) { beat = { bpm: r.ev.bpm, pc: r.pc }; continue; }
    if (r.src !== "key" || typeof r.down !== "boolean") continue;
    const k = String(r.key);
    const control = /^[0-9]$/.test(k) ? k : k === "C" ? "C" : null;
    if (control === null) { utility++; continue; }
    nowPc = r.pc;
    const t = opt.clock === "pc" ? r.pc * 1000 : Number(r.os_ms);
    if (r.down && !r.repeat) {
      keys++;
      if (beat && nowPc - beat.pc < 2) fresh++;
      if (lastKeyT !== null) downGaps.push(t - lastKeyT);
      lastKeyT = t;
      if (firstT === null) firstT = t;
      lastT = t;
    }
    for (const d of g.settle(t)) { all.push(d); plan(d, t); }
    for (const d of g.input({ source: "key", control, down: r.down, t, velocity: 0.8 })) { all.push({ ...d, _t: t }); plan(d, t); }
  }
  for (const d of g.settle(Infinity)) { all.push(d); plan(d, lastT); }
  // BREATH over the take: the share of the playing time the fade's target sat below half, at black, and where it ended
  let below = 0, black = 0;
  if (firstT !== null && lastT > firstT) {
    let tgt = 1, at = firstT;
    for (const [t, v] of [...breathPath, [lastT, null]]) {
      const tt = Math.max(firstT, Math.min(lastT, t));
      if (tgt < 0.5) below += tt - at; if (tgt <= 1e-9) black += tt - at;
      at = tt; if (v !== null) tgt = v;
    }
  }
  const span = firstT !== null && lastT > firstT ? lastT - firstT : 0;
  // the gestures' own timing (no sequences: distributions only)
  const settles = all.filter((d) => d.type === "settle");
  const presses = all.filter((d) => d.type === "press");
  const byLineage = new Map();
  for (const p of presses) { if (!byLineage.has(p.lineage)) byLineage.set(p.lineage, []); byLineage.get(p.lineage).push(p.t); }
  // a strum's merged lineages: the root holds them all after the reclassify
  for (const rc of all.filter((d) => d.type === "reclassify" && d.absorbed && d.absorbed.length)) {
    const root = byLineage.get(rc.lineage) || [];
    for (const a of rc.absorbed) { root.push(...(byLineage.get(a) || [])); byLineage.delete(a); }
    root.sort((x, y) => x - y); byLineage.set(rc.lineage, root);
  }
  const chordSpread = [], chordSize = [], strumStep = [], strumLen = [], strumSpan = [];
  for (const s of settles) {
    const ts = byLineage.get(s.lineage) || [];
    if (s.kind === "chord" && !s.walk) { chordSize.push(s.controls.length); for (let i = 1; i < ts.length; i++) chordSpread.push(ts[i] - ts[0]); }
    if (s.kind === "strum") { strumLen.push(s.controls.length); strumSpan.push(ts[ts.length - 1] - ts[0]); for (let i = 1; i < ts.length; i++) strumStep.push(ts[i] - ts[i - 1]); }
  }
  const br = all.filter((d) => d.type === "breath");
  const fadeStepGap = [], fadeLen = [], fadeDir = { out: 0, in: 0 }, fadeSteps = [];
  let lastBreathT = null, cur = null;
  for (const d of br) {
    if (d.phase === "start") { cur = { steps: Math.round(Math.abs(d.delta) * 9), net: d.delta }; lastBreathT = d.t; if (d.delta < 0) fadeDir.out++; else fadeDir.in++; }
    else if (d.phase === "step" && cur) { cur.steps++; cur.net += d.delta; fadeStepGap.push(d.t - lastBreathT); lastBreathT = d.t; }
    else if (d.phase === "end" && cur) { fadeLen.push(cur.steps); fadeSteps.push(+(cur.net * 9).toFixed(0)); cur = null; }
  }
  const B0 = windowsFor(400);
  const c = g.counts;
  const minutes = firstT !== null && lastT > firstT ? (lastT - firstT) / 60000 : 0;
  return {
    take: basename(file), records: recs.length, minutes_of_playing: +minutes.toFixed(2),
    number_row_and_C_downs: keys, utility_keys_skipped: utility, with_a_fresh_clock: keys ? +(fresh / keys).toFixed(3) : null,
    recogniser: { singles: c.singles, chords: c.chords, strums: c.strums, walks: c.walks, fades: c.sweeps, fade_steps: c.breathSteps,
                  dispatched: c.dispatched, suppressed_by_fades: c.suppressed, auto_repeats_ignored: c.repeats,
                  fade_keys_that_moved_nothing: noopTakeovers, new_gestures_inside_a_strums_W: strumSplits },
    breath: { share_of_playing_below_half: span ? +(below / span).toFixed(3) : null, share_at_black: span ? +(black / span).toFixed(3) : null,
              final_target: +ens.breath.target.toFixed(3), punches: { attacks: ens.stats.attacks, joined: ens.stats.joined } },
    intervals_ms: {
      consecutive_downs: { ...dist(downGaps), bands_at_400ms: { edges: [90, B0.W, B0.slowMin, B0.slowMax, 450].map((x) => +x.toFixed(1)), counts: hist(downGaps, [90, B0.W, B0.slowMin, B0.slowMax, 450]) } },
      chord_member_after_first: dist(chordSpread), chord_size: dist(chordSize),
      strum_step: dist(strumStep), strum_keys: dist(strumLen), strum_span: dist(strumSpan),
      fade_step: dist(fadeStepGap), fade_steps_per_fade: dist(fadeLen), fade_net_positions: dist(fadeSteps), fades_by_direction: fadeDir,
    },
  };
}

const out = { api: "arsenal.receipt/v0", lane: "grammar_replay", at: new Date().toISOString(), clock: opt.clock,
              note: "counts and distributions only; precision and recall cannot be measured without Daniel's annotations of the takes", takes: positionals.map(replay) };
const file = opt.out || join(REPO, "state", "arsenal", "receipts", `grammar-replay-${opt.clock}-${out.at.slice(0, 19).replace(/[-:]/g, "").replace("T", "-")}.json`);
mkdirSync(dirname(file), { recursive: true });
writeFileSync(file, JSON.stringify(out, null, 2));
for (const t of out.takes) {
  const r = t.recogniser, iv = t.intervals_ms;
  console.log(`${t.take}: ${t.number_row_and_C_downs} downs (${t.minutes_of_playing} min, fresh clock ${t.with_a_fresh_clock}) -> singles ${r.singles}, chords ${r.chords}, strums ${r.strums}, walks ${r.walks}, fades ${r.fades} (${r.fade_steps} steps, ${r.suppressed_by_fades} keys owned by fades); auto-repeats ignored ${r.auto_repeats_ignored}`);
  console.log(`  breath: below half ${t.breath.share_of_playing_below_half}, at black ${t.breath.share_at_black}, ends at ${t.breath.final_target}; fade keys that moved nothing ${r.fade_keys_that_moved_nothing}; new gestures inside a strum's W ${r.new_gestures_inside_a_strums_W}`);
  console.log(`  consecutive downs ms p10/p50/p90 ${iv.consecutive_downs.p10}/${iv.consecutive_downs.p50}/${iv.consecutive_downs.p90}; chord spread p50 ${iv.chord_member_after_first.p50}; strum step p50 ${iv.strum_step.p50}; fade step p50 ${iv.fade_step.p50}`);
}
console.log(`receipt: ${file}`);
