// Construction audit of a score (arsenal/web/piano/score/index.js score() or clean()), shared by
// tests/score_quantize.test.mjs and tests/score_settle.test.mjs so the fixture suites and the S1..Sn sessions check read
// the same five properties (counts only, no note content):
//   values     every note piece and rest is one written value, by an independent reading of the T4 spelling rules
//              (plan 6.5, transcription.md T4)
//   tiles      each note's pieces tile its written duration with ties
//   dangling   every bar-line tie leads into the next bar of the same segment, which holds the continuation (tieStop at 0)
//   twoBarLines  a note crosses at most one bar line (C7)
//   overlaps   a bar-line continuation never overlaps a later onset in its voice
import * as MX from "./metrics.mjs";

const TAB = new Map([[144, 1], [96, 0], [72, 1], [48, 0], [36, 1], [24, 0], [18, 1], [12, 0], [9, 1], [6, 0], [4.5, 1], [3, 0], [1.5, 0]]);

export const newAudit = () => ({ scores: 0, notes: 0, rests: 0, badNotes: 0, badRests: 0, tiles: 0, dangling: 0, multiBar: 0, overlap: 0, examples: [] });

export function auditScore(bad, sc, family) {
  bad.scores++;
  const BT = sc.meter.beatTicks, comp = sc.meter.compound, sum = new Map();
  const byIdx = new Map(sc.measures.map((m) => [m.index, m])), piecesOf = new Map();
  const ex = (x) => { if (bad.examples.length < 5) bad.examples.push([family, ...x]); };
  for (const m of sc.measures) {
    const four = m.barTicks === sc.meter.barTicks && m.barTicks === 4 * BT;
    for (const v of m.voices) {
      const pts = new Map(), add = (t) => { if (t >= m.barTicks) return; const k = Math.floor(t / BT); if (!pts.has(k)) pts.set(k, [0]); pts.get(k).push(t - k * BT); };
      v.notes.forEach((n) => { add(n.pos); add(n.pos + n.dur); });
      const tup = (k) => { const d = MX.normDiv(pts.get(k) || [0], BT); return comp ? (d === 2 || d === 4 ? 2 / 3 : null) : d === 3 || d === 6 || d === 12 ? 1.5 : null; };
      const judge = (p, dur, rest) => {
        const e = p + dur, k0 = Math.floor(p / BT), k1 = Math.ceil(e / BT) - 1, rel = p - k0 * BT, t = k0 === k1 ? tup(k0) : null;
        if (k1 > k0) for (let k = k0; k <= k1; k++) if (tup(k)) return "tuplet spill";
        const dots = TAB.get(t ? dur * t : dur);
        if (dots === undefined) return "no value";
        if (dots && (rest ? !(comp && !t && rel === 0 && dur % BT === 0) : rel % (comp ? (t ? 18 : 12) : t ? 8 : 12) !== 0 && !(t && !comp && rel % 12 === 0))) return "dotted off anchor";
        if (four && p < 2 * BT && e > 2 * BT && (rest || !(p === 0 || (p === BT && e <= 3 * BT)))) return "half bar";
        if (k1 > k0 && (rest ? !(comp ? rel === 0 && e % BT === 0 : four && dur === 2 * BT && (p === 0 || p === 2 * BT)) : comp ? !(rel === 0 && e % BT === 0) : !(rel === 0 || (rel % 12 === 0 && k1 === k0 + 1 && e % 12 === 0)))) return "beat line";
        return null;
      };
      for (const n of v.notes) {
        bad.notes++; sum.set(n.id, (sum.get(n.id) || 0) + n.dur);
        if (!piecesOf.has(n.id)) piecesOf.set(n.id, []);
        piecesOf.get(n.id).push({ bar: m.index, seg: m.seg, ...n });
        const why = judge(n.pos, n.dur, false); if (why || !n.type) { bad.badNotes++; ex(["note", m.index, n.pos, n.dur, why]); }
      }
      for (const r of v.rests) { bad.rests++; const why = judge(r.pos, r.dur, true); if (why || !r.type) { bad.badRests++; ex(["rest", m.index, r.pos, r.dur, why]); } }
      // a continuation's extent is every piece of its note in this bar (it may be spelled as several tied pieces), not only
      // the piece at position 0
      const conts = v.notes.filter((p) => p.tieStop && p.pos === 0);
      for (const c of conts) {
        const ext = Math.max(...v.notes.filter((q) => q.id === c.id).map((q) => q.pos + q.dur));
        if (v.notes.some((o) => !o.tieStop && o.pos < ext)) { bad.overlap++; ex(["overlap", m.index, c.id]); }
      }
    }
  }
  for (const nt of sc.notes) {
    if ((sum.get(nt.id) || 0) !== nt.dur) { bad.tiles++; ex(["untiled", nt.bar, nt.pos, nt.dur, sum.get(nt.id) || 0]); }
    if (new Set((piecesOf.get(nt.id) || []).map((p) => p.bar)).size > 2) { bad.multiBar++; ex(["two bar lines", nt.bar, nt.id]); }
  }
  for (const ps of piecesOf.values()) for (const p of ps) {
    if (!p.barTie) continue;
    const nb = byIdx.get(p.bar + 1);
    if (!(nb && nb.seg === p.seg && ps.some((q) => q.bar === p.bar + 1 && q.pos === 0 && q.tieStop))) { bad.dangling++; ex(["bar tie leads nowhere", p.bar, p.pos, p.dur, nb ? (nb.seg === p.seg ? "no continuation" : "next segment") : "no bar"]); }
  }
  return bad;
}

export const auditOk = (bad) => bad.badNotes === 0 && bad.badRests === 0 && bad.tiles === 0 && bad.dangling === 0 && bad.multiBar === 0 && bad.overlap === 0;
export const auditLine = (bad) => ({ scores: bad.scores, notePieces: bad.notes, rests: bad.rests, badNotes: bad.badNotes, badRests: bad.badRests, untiled: bad.tiles, danglingBarTies: bad.dangling, twoBarLines: bad.multiBar, overlaps: bad.overlap });
