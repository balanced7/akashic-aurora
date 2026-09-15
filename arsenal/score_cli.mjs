// Live sheet music from practice logs: arsenal/score_cli.mjs (Node CLI, zero dependencies). Slice LS4 of
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 2.2, 4.2, 7.4, 8, 10.3), amended by
// plan-amendments.md (C3, C5, section 6 LS4) and ls1-rulings.md.
//
//   node arsenal/score_cli.mjs clean  <session|latest|S#> [--at 3:43 --seconds 30] [--meter 3/4] [--one 12.40] [--bpm 70]
//                                                       [--feel straight|triplet] [--taps taps.json] [--take name]
//   node arsenal/score_cli.mjs export <session|latest|S#> [same flags]
//   node arsenal/score_cli.mjs bench  [--min-ons 1] [--date 2026-09-15]
//
// Reads state/arsenal/performance/<session>/events.jsonl (read-only; S# is the session's place in name order, S1 first)
// and writes only under state/arsenal/score/:
//   clean   <session>/<take>/score.clean.json                      the clean copy (index.js clean(); pinnedClean with --bpm)
//   export  <session>/<take>/score.clean.json, score.json (the export view: export.js forced bars for tape), take.musicxml,
//           performance.mid, quantized.mid, export.json (options, stats, measure lengths, the events path for readers)
//   bench   every session with at least --min-ons note-ons: export <session>/full/ and the LR9 checks below; aggregates
//           only (S-numbers, counts, no ids, times or note content) to state/arsenal/score/ls4-bench-<date>.json.
// Flags: --at and --one take m:ss(.s) or seconds of session time; --seconds a length; --meter 4/4 | 3/4 | 6/8 | 12/8 | 2/4
// | free; --bpm pins a fixed tactus grid (rhythm "unverified", every measure forced and marked freely) with --one a
// downbeat; --taps a JSON file: an array of tap times in session ms, or { "taps_ms": [...] } or { "taps_s": [...] };
// --take names the output folder (default from the span and flags, e.g. full, at-223s-30s-3-4).
// Key: summary.json nashville.areas (the closed session's key areas), else the key the page's Nashville tracker logged on
// chord events. Spelling: the page's own spellForKey, built read-only from arsenal/web/piano.js the way
// tests/nashville_js.test.mjs builds it (plan-amendments.md section 0 rule 2; no speller copy in score code).
// Checks (verifyExport, used by bench and tests/score_export.test.mjs; tests/test_score_export.py reads the same files
// independently with the Python stdlib):
//   LR9a  take.musicxml well-formed; one measure per score measure; every voice stream (notes, rests, forwards with that
//         voice) sums to its measure length; tie starts and stops pair (same staff and pitch, the stop where the start
//         ends); the sounding notes after tie merge equal the performance notes (count and pitch multiset of the log's
//         note-ons in the span) and the score's own notes (tick, pitch, length); beam structure (ls1-rulings.md LS4: beam 1
//         runs begin..end over consecutive beamable notes of one voice, never across an unbeamed note, rest or forward);
//         every measure's length equals the time signature in force, and implicit="yes" appears only on the opening measure.
//   LR9b  performance.mid (SMF 0, PPQ 500, tempo 500,000): every logged on (with velocity), off and CC64 crossing at
//         t_ms - t0 ticks, 0 ms error; CC64 values in {0, 127}; the only extra events are the documented end offs.
//   LR9c  quantized.mid (SMF 1, 3 tracks, PPQ 480): note count equals the MusicXML sounding notes, and (tick, pitch) pairs
//         equal them at 20 ticks per score tick.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { clean } from "./web/piano/score/index.js";
import { pinnedClean, forceTape } from "./web/piano/score/export.js";
import { toMusicXML } from "./web/piano/score/musicxml.js";
import { performanceMid, quantizedMid, soundingNotes, tickToMs } from "./web/piano/score/midi.js";
import { parseKey, spellInKey } from "./web/piano/nashville.js";
import { keyContext, spellChord, spellNote } from "./web/piano/spell.js";
import { parseSuffix } from "./web/piano/chordread.js";

export const CLI_API = "arsenal.score.cli/v0";
export const MANIFEST_API = "arsenal.piano.score.export-manifest/v0";
const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO = path.resolve(HERE, "..");
export const PERF_ROOT = path.join(REPO, "state", "arsenal", "performance");
export const SCORE_ROOT = path.join(REPO, "state", "arsenal", "score");
const LOG_KINDS = new Set(["on", "off", "pedal", "sound_end"]);
const METER_LABELS = new Set(["4/4", "3/4", "2/4", "6/8", "12/8", "free"]);

// ------------------------------------------------------------------------------------------ arguments ---
export function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { out._.push(a); continue; }
    const k = a.slice(2), eq = k.indexOf("=");
    if (eq >= 0) out[k.slice(0, eq)] = k.slice(eq + 1);
    else if (i + 1 < argv.length && !argv[i + 1].startsWith("--")) out[k] = argv[++i];
    else out[k] = true;
  }
  return out;
}
// "3:43" -> 223000, "12.40" -> 12400 (seconds), "1:02.5" -> 62500
export function parseTime(s) {
  if (s == null) return null;
  const t = String(s).trim();
  const m = /^(\d+):(\d{1,2}(?:\.\d+)?)$/.exec(t);
  if (m) return Math.round((Number(m[1]) * 60 + Number(m[2])) * 1000);
  if (/^\d+(\.\d+)?$/.test(t)) return Math.round(Number(t) * 1000);
  throw new Error(`bad time "${s}": use m:ss or seconds`);
}
export function takeOptions(flags = {}) {
  const at = flags.at != null ? parseTime(flags.at) : null;
  const seconds = flags.seconds != null ? Number(flags.seconds) : null;
  if (seconds != null && !(seconds > 0)) throw new Error(`--seconds must be a positive number (got ${flags.seconds})`);
  const span = at != null || seconds != null ? { from_ms: at ?? 0, to_ms: seconds != null ? (at ?? 0) + seconds * 1000 : Infinity } : null;
  const meter = flags.meter || "4/4";
  if (!METER_LABELS.has(meter)) throw new Error(`--meter must be one of ${[...METER_LABELS].join(", ")}`);
  const feel = flags.feel || "straight";
  if (feel !== "straight" && feel !== "triplet") throw new Error("--feel must be straight or triplet");
  const one = flags.one != null ? parseTime(flags.one) : null;
  const bpm = flags.bpm != null ? Number(flags.bpm) : null;
  if (bpm != null && !(bpm >= 20 && bpm <= 300)) throw new Error("--bpm must be 20-300");
  let taps = [];
  if (flags.taps) {
    const j = JSON.parse(fs.readFileSync(path.resolve(String(flags.taps)), "utf8"));
    taps = Array.isArray(j) ? j : Array.isArray(j.taps_ms) ? j.taps_ms : Array.isArray(j.taps_s) ? j.taps_s.map((x) => x * 1000) : null;
    if (!taps || !taps.every(Number.isFinite)) throw new Error("--taps: a JSON array of ms, or { taps_ms } or { taps_s }");
  }
  return { span, meter, feel, one, bpm, taps, beats: null };
}
export function takeName(o, flags = {}) {
  if (flags.take != null) {
    const t = String(flags.take);
    if (!/^[A-Za-z0-9._-]{1,80}$/.test(t) || t.includes("..")) throw new Error("--take: 1-80 letters, digits, dot, underscore or dash, no ..");
    return t;
  }
  let n = o.span ? `at-${Math.round(o.span.from_ms / 1000)}s${Number.isFinite(o.span.to_ms) ? `-${Math.round((o.span.to_ms - o.span.from_ms) / 1000)}s` : ""}` : "full";
  if (o.meter !== "4/4") n += "-" + o.meter.replace("/", "-");
  if (o.feel !== "straight") n += "-" + o.feel;
  if (o.bpm) n += `-bpm${o.bpm}`;
  if (o.one != null) n += `-one${o.one}`;
  if (o.taps && o.taps.length) n += `-taps${o.taps.length}`;
  return n;
}

// ------------------------------------------------------------------------------------------- sessions ---
export function listSessions(root = PERF_ROOT) {
  if (!fs.existsSync(root)) return [];
  return fs.readdirSync(root).filter((d) => fs.existsSync(path.join(root, d, "events.jsonl"))).sort().map((id, i) => ({ name: "S" + (i + 1), id, dir: path.join(root, id) }));
}
export function resolveSession(ref, root = PERF_ROOT) {
  const all = listSessions(root);
  if (!all.length) throw new Error(`no sessions with events.jsonl under ${root}`);
  if (!ref || ref === "latest") return all[all.length - 1];
  const s = /^S(\d+)$/.exec(ref);
  if (s) { const hit = all[Number(s[1]) - 1]; if (!hit) throw new Error(`${ref}: there are ${all.length} sessions`); return hit; }
  const exact = all.find((x) => x.id === ref);
  if (exact) return exact;
  const pre = all.filter((x) => x.id.startsWith(ref));
  if (pre.length === 1) return pre[0];
  throw new Error(`session ${ref}: ${pre.length ? "ambiguous prefix" : "not found"}`);
}
export function loadEvents(dir) {
  const out = [];
  let bad = 0;
  for (const line of fs.readFileSync(path.join(dir, "events.jsonl"), "utf8").split("\n")) {
    if (!line.trim()) continue;
    try { out.push(JSON.parse(line)); } catch { bad++; }
  }
  out.badLines = bad;
  return out;
}
const keyObject = (name, tonic, mode) => { const k = typeof name === "string" ? parseKey(name) : null; return k && k.tonic === tonic && k.mode === mode ? k : { tonic, mode }; };
// Key areas: summary.json nashville.areas, else runs of the key the page's tracker logged on chord events.
export function keyAreasOf(dir, events) {
  const sp = path.join(dir, "summary.json");
  if (fs.existsSync(sp)) {
    try {
      const nv = JSON.parse(fs.readFileSync(sp, "utf8")).nashville;
      const areas = ((nv && nv.areas) || []).filter((a) => a.key && Number.isInteger(a.key.tonic));
      if (areas.length) return { source: "summary", areas: areas.map((a) => ({ start_ms: a.start_s * 1000, end_ms: a.end_s * 1000, key: keyObject(a.key.key, a.key.tonic, a.key.mode) })) };
    } catch { /* fall through to the logged tracker key */ }
  }
  const chords = events.filter((e) => e.kind === "chord" && typeof e.key === "string" && parseKey(e.key));
  if (!chords.length) return { source: null, areas: null };
  const areas = [];
  for (const e of chords) {
    const last = areas[areas.length - 1];
    if (last && last.name === e.key) continue;
    if (last) last.end_ms = e.t_ms;
    areas.push({ name: e.key, start_ms: areas.length ? e.t_ms : 0, end_ms: null, key: parseKey(e.key) });
  }
  areas[areas.length - 1].end_ms = Math.max(...events.map((e) => e.t_ms || 0));
  return { source: "chord-events", areas: areas.map(({ name, ...a }) => a) };
}
export function clipAreas(areas, span) {
  if (!areas || !span) return areas;
  const out = areas.filter((a) => a.end_ms > span.from_ms && a.start_ms < span.to_ms).map((a) => ({ ...a, start_ms: Math.max(a.start_ms, span.from_ms) }));
  return out.length ? out : null;
}

// The page's speller, read-only from piano.js (plan-amendments.md section 0 rule 2): its THEORY block and spellForKey, with
// the imports the page gives spellForKey (the one shared speller piano/spell.js, chordread.js parseSuffix), injected the
// way tests/nashville_js.test.mjs builds it. Returns null when piano.js no longer has those anchors.
export function pageSpeller({ minor = "tonic" } = {}) {
  const src = fs.readFileSync(path.join(REPO, "arsenal", "web", "piano.js"), "utf8");
  const ta = src.indexOf("// ===== THEORY BEGIN"), tb = src.indexOf("// ===== THEORY END");
  const sa = src.indexOf("function spellForKey(info, key) {"), sb = sa < 0 ? -1 : src.indexOf("\n}\n", sa);
  if (ta < 0 || tb < 0 || sa < 0 || sb < 0) return null;
  const Theory = new Function(src.slice(ta, tb) + "\nreturn Theory;")();
  const spellForKey = new Function("Theory", "spellInKey", "theoryUi", "keyContext", "spellChord", "spellNote", "parseSuffix", src.slice(sa, sb + 2) + "\nreturn spellForKey;")(
    Theory, spellInKey, { minor }, keyContext, spellChord, spellNote, parseSuffix);
  return (midis, key) => {
    const info = spellForKey(Theory.detect(midis, key ? key.bias || 0 : 0), key);
    return info && Array.isArray(info.notes) ? info.notes.map((n) => ({ midi: n.midi, letter: n.letter, acc: n.acc, name: n.name, octave: n.octave })) : null;
  };
}

// -------------------------------------------------------------------------------------------- build ---
// events: the whole log (other kinds are ignored); o: takeOptions (plus beats for a fixed grid); -> the clean copy, the
// export view, the three files and their stats
export function buildTake({ events, keyAreas = null, options: o, spell = null, title = null, params = {} }) {
  const log = events.filter((e) => LOG_KINDS.has(e.kind));
  const spanEvents = o.span ? log.filter((e) => e.t_ms >= o.span.from_ms && e.t_ms <= o.span.to_ms) : log;
  const opts = { span: o.span, meter: o.meter, feel: o.feel, one: o.one, taps: o.taps || [], beats: o.beats || null, bpm: o.bpm, spell, keyAreas: clipAreas(keyAreas, o.span), params };
  const t = performance.now();
  const base = o.bpm ? pinnedClean(log, opts) : clean(log, opts);
  const tClean = performance.now();
  const view = forceTape(base, spanEvents, opts);
  const tView = performance.now();
  const t0_ms = o.span ? o.span.from_ms : 0;
  const stats = { musicxml: {}, performance: {}, quantized: {} };
  const xml = toMusicXML(view, { title, stats: stats.musicxml });
  const perf = performanceMid(spanEvents, { t0_ms, stats: stats.performance });
  const quant = quantizedMid(view, { stats: stats.quantized });
  const ms = { clean: tClean - t, forced: tView - tClean, write: performance.now() - tView };
  return { base, view, xml, perf, quant, t0_ms, spanEvents, stats, ms, options: o };
}

function under(root, p) {
  const r = path.resolve(root) + path.sep, q = path.resolve(p);
  if (!(q + path.sep).startsWith(r)) throw new Error(`refusing to write outside ${root}: ${q}`);
  return q;
}
// dir must lie under state/arsenal/score. eventsRef: { base: "repo" | "dir", path } for readers of export.json.
export function writeTake(dir, b, { label = null, group = null, session = null, take = null, command = "export", eventsRef = null, keySource = null, writeJson = true } = {}) {
  const d = under(SCORE_ROOT, dir);
  fs.mkdirSync(d, { recursive: true });
  const put = (name, data) => { const p = under(SCORE_ROOT, path.join(d, name)); fs.writeFileSync(p, data); return p; };
  const files = {};
  if (writeJson) files.clean = put("score.clean.json", JSON.stringify(b.base));
  if (command === "export") {
    if (writeJson) files.score = put("score.json", JSON.stringify(b.view));
    files.musicxml = put("take.musicxml", b.xml);
    files.performance = put("performance.mid", Buffer.from(b.perf));
    files.quantized = put("quantized.mid", Buffer.from(b.quant));
    const o = b.options;
    const { measureTicks, ...xmlStats } = b.stats.musicxml;
    const manifest = {
      api: MANIFEST_API, label, group, session, take,
      options: { meter: o.meter, feel: o.feel, one_ms: o.one, bpm: o.bpm, taps: (o.taps || []).length, fixedBeats: !!o.beats, span: o.span ? { from_ms: o.span.from_ms, to_ms: Number.isFinite(o.span.to_ms) ? o.span.to_ms : null } : null },
      t0_ms: b.t0_ms, events: eventsRef, rhythm: b.view.rhythm, keySource, measureTicks,
      counts: { logOns: b.spanEvents.filter((e) => e.kind === "on").length, scoreSounding: soundingNotes(b.view).length, measures: b.view.measures.length },
      stats: { musicxml: xmlStats, performance: b.stats.performance, quantized: b.stats.quantized, forced: b.view.forced },
    };
    files.manifest = put("export.json", JSON.stringify(manifest, null, 1));
  }
  return files;
}

// ------------------------------------------------------------------------------------------- readers ---
export function readSmf(bytes) {
  const u = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let p = 0;
  const tag = () => String.fromCharCode(u[p], u[p + 1], u[p + 2], u[p + 3]);
  const r32 = () => { const v = ((u[p] << 24) | (u[p + 1] << 16) | (u[p + 2] << 8) | u[p + 3]) >>> 0; p += 4; return v; };
  const r16 = () => { const v = (u[p] << 8) | u[p + 1]; p += 2; return v; };
  const vlq = () => { let v = 0, b; do { b = u[p++]; v = (v << 7) | (b & 0x7f); } while (b & 0x80); return v; };
  if (tag() !== "MThd") throw new Error("not a MIDI file");
  p += 4;
  const hl = r32(), format = r16(), ntracks = r16(), ppq = r16();
  p = 8 + hl;
  const tracks = [];
  for (let t = 0; t < ntracks; t++) {
    if (tag() !== "MTrk") throw new Error(`track ${t}: no MTrk`);
    p += 4;
    const len = r32(), end = p + len, ev = [];
    let tick = 0, status = 0;
    while (p < end) {
      tick += vlq();
      let s = u[p];
      if (s & 0x80) p++; else s = status;
      if (s === 0xff) { const type = u[p++], l = vlq(); ev.push({ tick, meta: type, data: Array.from(u.slice(p, p + l)) }); p += l; if (type === 0x2f) break; continue; }
      if (s === 0xf0 || s === 0xf7) { const l = vlq(); p += l; continue; }
      status = s;
      const hi = s & 0xf0, a = u[p++], b2 = hi === 0xc0 || hi === 0xd0 ? null : u[p++];
      ev.push({ tick, status: hi, ch: s & 15, a, b: b2 });
    }
    p = end;
    tracks.push(ev);
  }
  return { format, ntracks, ppq, tracks };
}

const STEP_PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
export function readMusicXML(xml) {
  // beamBad (ls1-rulings.md LS4 beam writer): per measure and voice, beam 1 runs begin, continue..., end over consecutive
  // non-chord notes of that voice; a beam on a quarter or longer note, a continue or end with no open beam, a begin inside
  // one, an unbeamed note or rest or a <forward> of the voice inside an open beam, and a beam left open at the measure end
  // each count one. measures[i].implicit / .time (the time signature in force) feed the short-measure check in verifyExport.
  const out = { wellFormed: true, error: null, measures: [], sounding: [], tieUnmatchedStart: 0, tieUnmatchedStop: 0, negativeCursor: 0, divisions: null, beams: 0, beamBad: 0 };
  const BEAMABLE = new Set(["eighth", "16th", "32nd", "64th", "128th"]);
  let curTime = null;
  const fail = (e) => { if (out.wellFormed) { out.wellFormed = false; out.error = e; } };
  // well-formedness: one root, balanced tags, quoted attributes, escaped text
  const re = /<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<!DOCTYPE[^>]*>|<(\/?)([A-Za-z_][\w.:-]*)((?:\s+[A-Za-z_][\w.:-]*="[^"<]*")*)\s*(\/?)>/g;
  const stack = [];
  let last = 0, roots = 0, m;
  while ((m = re.exec(xml))) {
    const text = xml.slice(last, m.index);
    if (text.includes("<") || /&(?!(amp|lt|gt|quot|apos|#\d+);)/.test(text)) { fail(`bad text before offset ${m.index}`); break; }
    last = re.lastIndex;
    if (!m[2]) continue;
    if (m[1]) { if (stack.pop() !== m[2]) { fail(`mismatched </${m[2]}>`); break; } }
    else if (m[4]) { if (!stack.length) roots++; }
    else { if (!stack.length) roots++; stack.push(m[2]); }
  }
  if (out.wellFormed && (stack.length || roots !== 1 || xml.slice(last).includes("<"))) fail(`unbalanced (open ${stack.length}, roots ${roots})`);
  const dv = /<divisions>(\d+)<\/divisions>/.exec(xml);
  out.divisions = dv ? Number(dv[1]) : null;
  const open = new Map();
  let offset = 0;
  const measRe = /<measure\b([^>]*)>([\s\S]*?)<\/measure>/g;
  let mm;
  while ((mm = measRe.exec(xml))) {
    const body = mm[2], sums = new Map(), beamOpen = new Map();
    let cursor = 0, lastStart = 0, notes = 0;
    const tm = /<time><beats>(\d+)<\/beats><beat-type>(\d+)<\/beat-type><\/time>/.exec(body);
    if (tm) curTime = { beats: Number(tm[1]), beatType: Number(tm[2]) };
    const elRe = /<(note|backup|forward)>([\s\S]*?)<\/\1>/g;
    let el;
    while ((el = elRe.exec(body))) {
      const kind = el[1], b = el[2];
      const dur = Number((/<duration>(\d+)<\/duration>/.exec(b) || [0, 0])[1]);
      const voice = (/<voice>([^<]+)<\/voice>/.exec(b) || [0, null])[1];
      if (kind === "backup") { cursor -= dur; if (cursor < 0) out.negativeCursor++; continue; }
      if (kind === "forward") { if (voice != null) { sums.set(voice, (sums.get(voice) || 0) + dur); if (beamOpen.get(voice)) { out.beamBad++; beamOpen.set(voice, false); } } cursor += dur; continue; }
      notes++;
      const chord = /<chord\/>/.test(b);
      if (!chord) {
        const bm = (/<beam number="1">(\w+)<\/beam>/.exec(b) || [])[1], ty = (/<type>([^<]+)<\/type>/.exec(b) || [])[1], isOpen = !!beamOpen.get(voice);
        if (bm && !BEAMABLE.has(ty)) out.beamBad++;
        if (bm === "begin") { out.beams++; if (isOpen) out.beamBad++; beamOpen.set(voice, true); }
        else if (bm === "continue") { if (!isOpen) out.beamBad++; beamOpen.set(voice, true); }
        else if (bm === "end") { if (!isOpen) out.beamBad++; beamOpen.set(voice, false); }
        else if (isOpen) { out.beamBad++; beamOpen.set(voice, false); }
      }
      let start;
      if (chord) start = lastStart; else { start = cursor; lastStart = cursor; cursor += dur; sums.set(voice, (sums.get(voice) || 0) + dur); }
      if (/<rest\b/.test(b)) continue;
      const step = (/<step>([A-G])<\/step>/.exec(b) || [])[1], alter = Number((/<alter>(-?\d+)<\/alter>/.exec(b) || [0, 0])[1]), oct = Number((/<octave>(-?\d+)<\/octave>/.exec(b) || [0, 0])[1]);
      const midi = (oct + 1) * 12 + STEP_PC[step] + alter, staff = (/<staff>(\d+)<\/staff>/.exec(b) || [0, "1"])[1];
      const abs = offset + start, tieStart = /<tie type="start"\/>/.test(b), tieStop = /<tie type="stop"\/>/.test(b), k = staff + "|" + midi;
      if (tieStop) {
        const list = open.get(k) || [];
        const j = list.findIndex((ch) => ch.end === abs);
        if (j >= 0) { const ch = list[j]; ch.end = abs + dur; if (!tieStart) list.splice(j, 1); continue; }
        out.tieUnmatchedStop++;
      }
      const ch = { tick: abs, midi, staff: Number(staff), end: abs + dur };
      out.sounding.push(ch);
      if (tieStart) { if (!open.has(k)) open.set(k, []); open.get(k).push(ch); }
    }
    for (const open of beamOpen.values()) if (open) out.beamBad++;
    const len = Math.max(0, ...sums.values());
    out.measures.push({ attrs: mm[1], sums, length: len, notes, implicit: /implicit="yes"/.test(mm[1]), time: curTime });
    offset += len;
  }
  for (const l of open.values()) out.tieUnmatchedStart += l.length;
  return out;
}

const countBy = (arr, key) => { const m = new Map(); for (const x of arr) { const k = key(x); m.set(k, (m.get(k) || 0) + 1); } return m; };
const multisetDiff = (A, B) => { let d = 0; for (const k of new Set([...A.keys(), ...B.keys()])) d += Math.abs((A.get(k) || 0) - (B.get(k) || 0)); return d; };
const missingFrom = (need, have) => { let d = 0; for (const [k, n] of need) d += Math.max(0, n - (have.get(k) || 0)); return d; };
const med = (a) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); if (!s.length) return null; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const q95 = (a) => { const s = a.filter(Number.isFinite).sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(0.95 * s.length))] : null; };

// LR9a-c on a built take (buildTake output)
export function verifyExport(b) {
  const xr = readMusicXML(b.xml), MT = b.stats.musicxml.measureTicks;
  let voicesChecked = 0, voiceSumBad = 0;
  xr.measures.forEach((m, i) => { for (const s of m.sums.values()) { voicesChecked++; if (s !== MT[i]) voiceSumBad++; } });
  const logOns = b.spanEvents.filter((e) => e.kind === "on");
  const scoreSounding = soundingNotes(b.view);
  // timeBad (ls1-rulings.md LS4 short measures): a measure whose length differs from the time signature in force, unless it
  // is the opening measure marked implicit; implicitMid: implicit="yes" on any other measure
  let timeBad = 0, implicitMid = 0;
  xr.measures.forEach((m, i) => {
    if (m.implicit && i > 0) implicitMid++;
    const want = m.time && xr.divisions ? (m.time.beats * 4 * xr.divisions) / m.time.beatType : null;
    if (!(m.implicit && i === 0) && want !== MT[i]) timeBad++;
  });
  const lr9a = {
    wellFormed: xr.wellFormed, error: xr.error, divisions: xr.divisions, measures: xr.measures.length, measuresMatch: xr.measures.length === MT.length, voicesChecked, voiceSumBad, beams: xr.beams, beamBad: xr.beamBad, timeBad, implicitMid,
    tieUnmatchedStart: xr.tieUnmatchedStart, tieUnmatchedStop: xr.tieUnmatchedStop, negativeCursor: xr.negativeCursor, sounding: xr.sounding.length, logOns: logOns.length,
    pitchDiff: multisetDiff(countBy(xr.sounding, (x) => x.midi), countBy(logOns, (e) => e.note)),
    scoreDiff: multisetDiff(countBy(xr.sounding, (x) => `${x.tick}|${x.midi}|${x.end - x.tick}`), countBy(scoreSounding, (n) => `${n.tick}|${n.note}|${n.dur}`)),
  };
  lr9a.pass = lr9a.wellFormed && lr9a.divisions === 24 && lr9a.measuresMatch && lr9a.voiceSumBad === 0 && lr9a.tieUnmatchedStart === 0 && lr9a.tieUnmatchedStop === 0 && lr9a.negativeCursor === 0 && lr9a.sounding === lr9a.logOns && lr9a.pitchDiff === 0 && lr9a.scoreDiff === 0 && lr9a.beamBad === 0 && lr9a.timeBad === 0 && lr9a.implicitMid === 0;

  // LR9b
  const P = readSmf(b.perf), t0 = b.t0_ms;
  const tk = (t) => Math.round(t - t0);
  const logOnK = countBy(logOns, (e) => `${tk(e.t_ms)}|${e.note}|${Math.max(1, Math.min(127, Math.round(e.vel ?? 64)))}`);
  const logOffK = countBy(b.spanEvents.filter((e) => e.kind === "off"), (e) => `${tk(e.t_ms)}|${e.note}`);
  const cross = [];
  let down = false;
  for (const e of b.spanEvents.map((x, i) => ({ x, i })).filter((y) => y.x.kind === "pedal").sort((y, z) => y.x.t_ms - z.x.t_ms || y.i - z.i)) { if (!!e.x.down !== down) { down = !!e.x.down; cross.push(`${tk(e.x.t_ms)}|${down ? 127 : 0}`); } }
  const tr0 = P.tracks[0] || [];
  const midiOn = tr0.filter((e) => e.status === 0x90 && e.b > 0), midiOff = tr0.filter((e) => e.status === 0x80 || (e.status === 0x90 && e.b === 0)), midiCc = tr0.filter((e) => e.status === 0xb0 && e.a === 64);
  const tempo = tr0.find((e) => e.meta === 0x51);
  const offsHave = countBy(midiOff, (e) => `${e.tick}|${e.a}`);
  const lr9b = {
    format: P.format, ntracks: P.ntracks, ppq: P.ppq, tempoUs: tempo ? (tempo.data[0] << 16) | (tempo.data[1] << 8) | tempo.data[2] : null,
    logOns: logOns.length, midiOns: midiOn.length, onsDiff: multisetDiff(logOnK, countBy(midiOn, (e) => `${e.tick}|${e.a}|${e.b}`)),
    logOffs: [...logOffK.values()].reduce((s, n) => s + n, 0), midiOffs: midiOff.length, offsMissing: missingFrom(logOffK, offsHave), offsExtra: midiOff.length - ([...logOffK.values()].reduce((s, n) => s + n, 0) - missingFrom(logOffK, offsHave)),
    endOffs: b.stats.performance.endOffs, logCrossings: cross.length, midiCc64: midiCc.length, ccDiff: multisetDiff(countBy(cross, (x) => x), countBy(midiCc, (e) => `${e.tick}|${e.b}`)), ccBadValues: midiCc.filter((e) => e.b !== 0 && e.b !== 127).length,
    roundedTimes: b.stats.performance.rounded,
  };
  lr9b.pass = lr9b.format === 0 && lr9b.ntracks === 1 && lr9b.ppq === 500 && lr9b.tempoUs === 500000 && lr9b.onsDiff === 0 && lr9b.offsMissing === 0 && lr9b.offsExtra === lr9b.endOffs && lr9b.ccDiff === 0 && lr9b.ccBadValues === 0 && lr9b.roundedTimes === 0;

  // LR9c
  const Q = readSmf(b.quant);
  const qOn = [1, 2].flatMap((t) => (Q.tracks[t] || []).filter((e) => e.status === 0x90 && e.b > 0));
  const lr9c = {
    format: Q.format, ntracks: Q.ntracks, ppq: Q.ppq, notes: qOn.length, sounding: xr.sounding.length, tempos: (Q.tracks[0] || []).filter((e) => e.meta === 0x51).length,
    tickPitchDiff: multisetDiff(countBy(qOn, (e) => `${e.tick / 20}|${e.a}`), countBy(xr.sounding, (x) => `${x.tick}|${x.midi}`)),
  };
  lr9c.pass = lr9c.format === 1 && lr9c.ntracks === 3 && lr9c.ppq === 480 && lr9c.notes === lr9c.sounding && lr9c.tickPitchDiff === 0;

  // reported: quantized.mid playback against the performance inside each bar (tempo-map fidelity), ms
  const toMs = tickToMs(b.view), err = [];
  for (const n of b.view.notes) {
    const m = b.view.measures[n.bar];
    if (!m || !m.beats_ms || !m.beats_ms.length || !Number.isFinite(n.t_ms)) continue;
    err.push(Math.abs(toMs(m.startTick + n.pos) - toMs(m.startTick) - (n.t_ms - m.beats_ms[0])));
  }
  return { lr9a, lr9b, lr9c, playback: { notes: err.length, medianMs: med(err), p95Ms: q95(err) }, pass: lr9a.pass && lr9b.pass && lr9c.pass };
}

// -------------------------------------------------------------------------------------------- bench ---
// onBuilt(b, session): called with every built take (tests/score_export.test.mjs runs the construction audit there)
export function bench({ root = PERF_ROOT, minOns = 1, date = new Date().toISOString().slice(0, 10), write = true, log = console.log, onBuilt = null } = {}) {
  const spell = pageSpeller();
  const rows = [];
  const t = performance.now();
  for (const s of listSessions(root)) {
    const events = loadEvents(s.dir);
    const ons = events.filter((e) => e.kind === "on");
    if (ons.length < minOns) { rows.push({ name: s.name, skipped: true, ons: ons.length }); continue; }
    const ka = keyAreasOf(s.dir, events), o = takeOptions({});
    const b = buildTake({ events, keyAreas: ka.areas, options: o, spell, title: `Practice take ${s.name}` });
    const files = write ? writeTake(path.join(SCORE_ROOT, s.id, "full"), b, { label: s.name, group: "sessions", session: s.id, take: "full", eventsRef: { base: "repo", path: path.relative(REPO, path.join(s.dir, "events.jsonl")).split(path.sep).join("/") }, keySource: ka.source }) : {};
    const v = verifyExport(b);
    if (onBuilt) onBuilt(b, s);
    const X = b.stats.musicxml;
    rows.push({
      name: s.name, ons: ons.length, minutes: +((ons[ons.length - 1].t_ms - ons[0].t_ms) / 60000).toFixed(2), badLines: events.badLines, keySource: ka.source, rhythm: b.view.rhythm,
      measures: b.view.measures.length, cleanMeasures: b.base.measures.length, forced: b.view.forced,
      musicxml: { bytes: b.xml.length, pieces: X.pieces, chords: X.chords, rests: X.rests, extraLanes: X.extraLanes, chordSplits: X.chordSplits, overlapSplits: X.overlapSplits, forwards: X.forwards, emptyMeasures: X.emptyMeasures, tupletBeats: X.tupletBeats, bracketsSkipped: X.bracketsSkipped, tieStarts: X.tieStarts, crossVoiceTies: X.crossVoiceTies,
        pedal: X.pedal, pedalRepairs: X.pedalRepairs, pedalUnplaced: X.pedalUnplaced, unspelledNotes: X.unspelledNotes, untypedPieces: X.untypedPieces, metronomes: X.metronomes, rubato: X.rubato, freely: X.freely, keyChanges: X.keyChanges, clefChanges: X.clefChanges, octaveShifts: X.octaveShifts, dynamics: X.dynamics, pickups: X.pickups },
      performance: { ...b.stats.performance, t0_ms: undefined, bytes: b.perf.length }, quantized: { ...b.stats.quantized, bytes: b.quant.length },
      lr9a: v.lr9a, lr9b: v.lr9b, lr9c: v.lr9c, playback: v.playback, pass: v.pass, ms: { clean: Math.round(b.ms.clean), forced: Math.round(b.ms.forced), write: Math.round(b.ms.write) },
      wrote: Object.keys(files),
    });
    if (log) log(`${s.name}: ${ons.length} note-ons, ${b.view.measures.length} measures (${b.view.forced.measures} forced), LR9a ${v.lr9a.pass ? "pass" : "FAIL"}, LR9b ${v.lr9b.pass ? "pass" : "FAIL"}, LR9c ${v.lr9c.pass ? "pass" : "FAIL"}`);
  }
  const used = rows.filter((r) => !r.skipped);
  const sum = (f) => used.reduce((s, r) => s + f(r), 0);
  const summary = {
    date, slice: "LS4", api: CLI_API,
    config: "export full session: clean() meter 4/4, inferred beats, hands.js voices, marks.js defaults, key areas from summary.json (else logged tracker key), the page speller; export.js forced bars for tape; musicxml.js, midi.js",
    sessions: rows.length, used: used.length, skipped: rows.filter((r) => r.skipped).map((r) => r.name),
    totals: {
      ons: sum((r) => r.ons), measures: sum((r) => r.measures), forcedMeasures: sum((r) => r.forced.measures), forcedNotes: sum((r) => r.forced.notes), forcedRuns: sum((r) => r.forced.runs), tapeInsideMeasure: sum((r) => r.forced.tapeInsideMeasure), tapeLeft: sum((r) => r.forced.tapeLeft),
      extraLanes: sum((r) => r.musicxml.extraLanes), chordSplits: sum((r) => r.musicxml.chordSplits), overlapSplits: sum((r) => r.musicxml.overlapSplits), crossVoiceTies: sum((r) => r.musicxml.crossVoiceTies), pedalRepairs: sum((r) => r.musicxml.pedalRepairs), pedalUnplaced: sum((r) => r.musicxml.pedalUnplaced), unspelledNotes: sum((r) => r.musicxml.unspelledNotes), untypedPieces: sum((r) => r.musicxml.untypedPieces), bracketsSkipped: sum((r) => r.musicxml.bracketsSkipped),
      rubato: sum((r) => r.musicxml.rubato), metronomes: sum((r) => r.musicxml.metronomes), keyChanges: sum((r) => r.musicxml.keyChanges), endOffs: sum((r) => r.performance.endOffs), pedalNonCrossings: sum((r) => r.performance.pedalNonCrossings), velClamped: sum((r) => r.performance.velClamped),
    },
    LR9a: { pass: used.every((r) => r.lr9a.pass), failed: used.filter((r) => !r.lr9a.pass).map((r) => r.name), sounding: sum((r) => r.lr9a.sounding), logOns: sum((r) => r.lr9a.logOns), voicesChecked: sum((r) => r.lr9a.voicesChecked), voiceSumBad: sum((r) => r.lr9a.voiceSumBad), tieUnmatched: sum((r) => r.lr9a.tieUnmatchedStart + r.lr9a.tieUnmatchedStop) },
    LR9b: { pass: used.every((r) => r.lr9b.pass), failed: used.filter((r) => !r.lr9b.pass).map((r) => r.name), ons: sum((r) => r.lr9b.midiOns), offs: sum((r) => r.lr9b.midiOffs), cc64: sum((r) => r.lr9b.midiCc64), onsDiff: sum((r) => r.lr9b.onsDiff), offsMissing: sum((r) => r.lr9b.offsMissing), ccDiff: sum((r) => r.lr9b.ccDiff) },
    LR9c: { pass: used.every((r) => r.lr9c.pass), failed: used.filter((r) => !r.lr9c.pass).map((r) => r.name), notes: sum((r) => r.lr9c.notes), tickPitchDiff: sum((r) => r.lr9c.tickPitchDiff) },
    playback: { medianOfSessionMediansMs: med(used.map((r) => r.playback.medianMs)), worstP95Ms: Math.max(0, ...used.map((r) => r.playback.p95Ms ?? 0)) },
    rows, ms: Math.round(performance.now() - t),
  };
  if (write) { fs.mkdirSync(SCORE_ROOT, { recursive: true }); fs.writeFileSync(under(SCORE_ROOT, path.join(SCORE_ROOT, `ls4-bench-${date}.json`)), JSON.stringify(summary, null, 1)); }
  return summary;
}

// --------------------------------------------------------------------------------------------- main ---
const USAGE = `usage:
  node arsenal/score_cli.mjs clean  <session|latest|S#> [--at m:ss --seconds N] [--meter 4/4|3/4|2/4|6/8|12/8|free] [--one m:ss|s] [--bpm N] [--feel straight|triplet] [--taps file.json] [--take name]
  node arsenal/score_cli.mjs export <session|latest|S#> [same flags]
  node arsenal/score_cli.mjs bench  [--min-ons N] [--date YYYY-MM-DD]`;

export function main(argv) {
  const f = parseArgs(argv), [cmd, ref] = f._;
  if (!cmd || f.help || f.h) { console.log(USAGE); return 0; }
  if (cmd === "bench") {
    const r = bench({ minOns: f["min-ons"] != null ? Number(f["min-ons"]) : 1, date: typeof f.date === "string" ? f.date : undefined });
    console.log(JSON.stringify({ sessions: r.sessions, used: r.used, totals: r.totals, LR9a: r.LR9a, LR9b: r.LR9b, LR9c: r.LR9c, playback: r.playback, ms: r.ms }, null, 1));
    console.log(`bench written to ${path.relative(REPO, path.join(SCORE_ROOT, `ls4-bench-${r.date}.json`))}`);
    return r.LR9a.pass && r.LR9b.pass && r.LR9c.pass ? 0 : 1;
  }
  if (cmd !== "clean" && cmd !== "export") { console.error(USAGE); return 2; }
  const s = resolveSession(ref);
  const events = loadEvents(s.dir), o = takeOptions(f), take = takeName(o, f), ka = keyAreasOf(s.dir, events);
  const b = buildTake({ events, keyAreas: ka.areas, options: o, spell: pageSpeller(), title: `Practice take ${s.name}${take === "full" ? "" : " " + take}` });
  const dir = path.join(SCORE_ROOT, s.id, take);
  const files = writeTake(dir, b, { label: s.name, group: "cli", session: s.id, take, command: cmd, eventsRef: { base: "repo", path: path.relative(REPO, path.join(s.dir, "events.jsonl")).split(path.sep).join("/") }, keySource: ka.source });
  const X = b.stats.musicxml;
  console.log(`${s.name} (${s.id}) ${take}: ${b.spanEvents.filter((e) => e.kind === "on").length} note-ons, rhythm ${b.view.rhythm}, ${b.base.measures.length} clean measures, ${b.view.forced.measures} forced measures (${b.view.forced.notes} notes), key areas ${ka.source || "none"}`);
  if (cmd === "export") {
    const v = verifyExport(b);
    console.log(`  musicxml: ${X.measures} measures, ${X.pieces} note pieces, pedal start/change/stop ${X.pedal.start}/${X.pedal.change}/${X.pedal.stop}, metronome marks ${X.metronomes} (rubato ${X.rubato}), freely ${X.freely}`);
    console.log(`  LR9a ${v.lr9a.pass ? "pass" : "FAIL"} · LR9b ${v.lr9b.pass ? "pass" : "FAIL"} · LR9c ${v.lr9c.pass ? "pass" : "FAIL"}`);
  }
  for (const [k, p] of Object.entries(files)) console.log(`  ${k}: ${path.relative(REPO, p)}`);
  return 0;
}

const isMain = process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (isMain) {
  try { process.exitCode = main(process.argv.slice(2)); } catch (e) { console.error(`score_cli: ${e.message}`); process.exitCode = 2; }
}
