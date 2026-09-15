// The house engraver for settling and settled bars: arsenal/web/piano/score/engrave.js (Canvas2D; needs a 2D context
// only, no DOM, and reads no clock unless the caller injects one). Slice LS5 of
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (sections 5.1, 7.3), amended by
// plan-amendments.md section 0 rule 1 (VexFlow not approved in LS0-LS5: our own drawer behind an interface a VexFlow
// adapter can implement unchanged), C9 (the font gate) and C15 (beat widening, LR11g).
//
//   const E = createHouseEngraver({ now: () => performance.now() });   // now is optional: ms is null without it
//   E.ready({ smufl: true })                        // false until the SMuFL face (Bravura) is loaded
//   E.measureBar(model, { L })                      // pure: { minWidth, beatWidths }, constant glyph boxes in staff spaces
//   E.engraveBar(ctx, model, { L, ink: "full" | "light", x: 0 }) -> { width, boxes, ms, drawn, layout }
//
// model: layout.js modelBar(bar, ...). Coordinates: the tile's own (x from its left edge, y band-local). Staff lines are
// the band's (paint.js paintStaves): a tile draws the bar's content and its closing bar line on a clear background.
// What it draws (the plan's reduced set): heads (black, half, whole), accidentals, ledger lines, stems (up for an upper
// voice, down for a lower one; one voice on a staff by its mean position), one horizontal beam per beat group with
// secondary beams and stubs, flags on unbeamed pieces, SMuFL rests, augmentation dots, ties (a tie across the bar line is
// a half-tie at the tile edge), a tuplet numeral per bracketed beat, staccato dots, 8va / 8vb over a staff, a clef change
// and a key change (double bar, new signature) at the bar line. Dropped (plan 7.3): cross-staff beams and slurs.
// An ENGRAVER_API adapter for VexFlow (engrave_vexflow.js, after LQ1 and C9) implements ready, measureBar and engraveBar.

import { layoutBar, ledgerSteps, stepY, flagCount, keySigGlyphs, GLYPH } from "./layout.js";

export const ENGRAVER_API = "arsenal.piano.score.engrave/v0";

// SMuFL code points (Bravura). The clef, accidental and whole-note values equal piano.js SMUFL (tests/score_layout.test.mjs).
export const SMUFL = Object.freeze({
  gClef: "\uE050", fClef: "\uE062", brace: "\uE000",
  whole: "\uE0A2", half: "\uE0A3", black: "\uE0A4",
  flat: "\uE260", natural: "\uE261", sharp: "\uE262", dsharp: "\uE263", dflat: "\uE264",
  restWhole: "\uE4E3", restHalf: "\uE4E4", restQuarter: "\uE4E5", rest8th: "\uE4E6", rest16th: "\uE4E7", rest32nd: "\uE4E8", rest64th: "\uE4E9",
  flagUp: ["", "\uE240", "\uE242", "\uE244", "\uE246"], flagDown: ["", "\uE241", "\uE243", "\uE245", "\uE247"],
  dot: "\uE1E7", tuplet: (d) => String(d).split("").map((x) => String.fromCharCode(0xE880 + Number(x))).join(""),
  ottavaAlta: "\uE511", ottavaBassa: "\uE51C",
});
export const ACC_GLYPH = Object.freeze({ "-2": SMUFL.dflat, "-1": SMUFL.flat, "0": SMUFL.natural, "1": SMUFL.sharp, "2": SMUFL.dsharp });
export const REST_GLYPH = Object.freeze({ whole: SMUFL.restWhole, half: SMUFL.restHalf, quarter: SMUFL.restQuarter, eighth: SMUFL.rest8th, "16th": SMUFL.rest16th, "32nd": SMUFL.rest32nd, "64th": SMUFL.rest64th });

export const INK = Object.freeze({ full: 1, light: 0.45 });

export function createHouseEngraver(opts = {}) {
  const now = typeof opts.now === "function" ? opts.now : null;
  const color = opts.color || "#ece6d6";
  let fontsReady = false;

  function measureBar(model, geom) {
    const g = layoutBar(model, geom.L, { widen: geom.widen !== false });
    return { minWidth: g.width, beatWidths: g.beats.map((b) => b.w), widened: g.beats.map((b) => b.widened), layout: g };
  }

  function engraveBar(ctx, model, geom) {
    const t0 = now ? now() : null;
    const L = geom.L, sp = L.sp;
    const g = geom.layout || layoutBar(model, L, { widen: geom.widen !== false });
    if (!fontsReady) return { width: g.width, boxes: g.boxes, ms: now ? now() - t0 : null, drawn: false, layout: g };
    const ox = geom.x || 0;
    const font = `${4 * sp}px Bravura`;
    ctx.save();
    ctx.translate(ox, 0);
    ctx.globalAlpha = geom.ink === "light" ? INK.light : INK.full;
    ctx.fillStyle = color; ctx.strokeStyle = color;
    ctx.font = font; ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
    const yTop = L.staffTop[1], yBot = L.staffBottom[2];
    // lead-in: key change (double bar and the new signature), clef change
    let lx = 0.3 * sp;
    if (model.keyChange != null) {
      ctx.fillRect(0, yTop, 0.16 * sp, yBot - yTop);
      ctx.fillRect(0.45 * sp, yTop, 0.16 * sp, yBot - yTop);
      lx += 0.9 * sp;
    }
    if (model.clefChange) {
      const cl = model.clefs[2];
      const small = `${3 * sp}px Bravura`;
      ctx.font = small;
      ctx.fillText(cl === "treble" ? SMUFL.gClef : SMUFL.fClef, lx, stepY(L, 2, cl === "treble" ? -2 : 2));
      ctx.font = font;
      lx += 2.2 * sp;
    }
    if (model.keyChange != null) {
      for (const staff of [1, 2]) for (const k of keySigGlyphs(model.fifths, model.clefs[staff])) ctx.fillText(ACC_GLYPH[String(k.acc)], lx + k.x * sp, stepY(L, staff, k.step));
    }
    // ledger lines
    ctx.lineWidth = 0.16 * sp;
    ctx.beginPath();
    for (const h of g.heads) {
      const w = (GLYPH.head[h.kind] || GLYPH.head.black).w * sp;
      for (const s of ledgerSteps(h.step)) { const y = stepY(L, h.staff, s); ctx.moveTo(h.x - 0.35 * sp, y); ctx.lineTo(h.x + w + 0.35 * sp, y); }
    }
    ctx.stroke();
    // heads, accidentals, dots, rests
    for (const h of g.heads) ctx.fillText(SMUFL[h.kind], h.x, h.y);
    for (const a of g.accidentals) ctx.fillText(ACC_GLYPH[String(Math.max(-2, Math.min(2, a.acc)))], a.x, a.y);
    for (const d of g.dots) ctx.fillText(SMUFL.dot, d.x, d.y);
    for (const r of g.rests) ctx.fillText(REST_GLYPH[r.type] || SMUFL.restQuarter, r.x, r.y);
    // staccato
    for (const h of g.heads) if (h.staccato) { const y = h.y + (h.stemUp ? 1 : -1) * 1.0 * sp; ctx.beginPath(); ctx.arc(h.x + 0.59 * sp, y, 0.14 * sp, 0, Math.PI * 2); ctx.fill(); }
    // beams: stems of a beamed group end at one horizontal beam
    const stemKey = (s) => s.voice + ":" + s.pos;
    const beamOf = new Map();
    for (const bm of model.beams) {
      const ids = new Set(bm.ids);
      const group = g.stems.filter((s) => s.voice === bm.voice && Math.floor(s.pos / model.beatTicks) === bm.beat && s.ids.some((id) => ids.has(id))).sort((a, b) => a.pos - b.pos);
      if (group.length < 2) continue;
      const up = group[0].up;
      const y = up ? Math.min(...group.map((s) => s.yEnd)) : Math.max(...group.map((s) => s.yEnd));
      for (const s of group) beamOf.set(stemKey(s), { y, group, up });
    }
    ctx.lineWidth = 0.12 * sp;
    ctx.beginPath();
    for (const s of g.stems) {
      const bm = beamOf.get(stemKey(s));
      ctx.moveTo(s.x, s.yHead); ctx.lineTo(s.x, bm ? bm.y : s.yEnd);
    }
    ctx.stroke();
    const thick = 0.5 * sp, gap = 0.25 * sp;
    const drawn = new Set();
    for (const [, bm] of beamOf) {
      const key = bm.group.map(stemKey).join("|");
      if (drawn.has(key)) continue;
      drawn.add(key);
      const gr = bm.group, dir = bm.up ? 1 : -1;
      const y0 = bm.up ? bm.y : bm.y - thick;
      ctx.fillRect(gr[0].x, y0, gr[gr.length - 1].x - gr[0].x + 0.12 * sp, thick);
      const maxLevel = Math.max(...gr.map((s) => s.flags));
      for (let lev = 2; lev <= maxLevel; lev++) {
        const yl = y0 + dir * (lev - 1) * (thick + gap);
        for (let i = 0; i < gr.length; i++) {
          if (gr[i].flags < lev) continue;
          const next = gr[i + 1] && gr[i + 1].flags >= lev ? gr[i + 1] : null;
          const prev = gr[i - 1] && gr[i - 1].flags >= lev ? gr[i - 1] : null;
          if (next) ctx.fillRect(gr[i].x, yl, next.x - gr[i].x + 0.12 * sp, thick);
          else if (!prev) { const toward = i > 0 ? -1 : 1; ctx.fillRect(toward > 0 ? gr[i].x : gr[i].x - 1.0 * sp, yl, 1.0 * sp + 0.12 * sp, thick); }
        }
      }
    }
    // flags on unbeamed stems
    for (const s of g.stems) if (s.flags && !beamOf.has(stemKey(s))) ctx.fillText((s.up ? SMUFL.flagUp : SMUFL.flagDown)[Math.min(4, s.flags)], s.x - 0.06 * sp, s.yEnd);
    // ties: to the next piece of the same note in the bar, or a half-tie to the tile edge; a tie stop with no piece before
    // it in the bar is a half-tie from the left edge
    ctx.lineWidth = 0.14 * sp;
    const piecesOf = new Map();
    for (const h of g.heads) { const k = h.id + ":" + h.staff; if (!piecesOf.has(k)) piecesOf.set(k, []); piecesOf.get(k).push(h); }
    const arc = (xa, xb, y, down) => { const dy = (down ? 1 : -1) * 0.9 * sp; ctx.beginPath(); ctx.moveTo(xa, y + dy * 0.4); ctx.quadraticCurveTo((xa + xb) / 2, y + dy * 1.6, xb, y + dy * 0.4); ctx.stroke(); };
    for (const list of piecesOf.values()) {
      list.sort((a, b) => a.pos - b.pos);
      list.forEach((h, i) => {
        const down = h.stemUp;
        if (h.tieStart) { const nx = list[i + 1]; arc(h.x + 1.1 * sp, nx ? nx.x + 0.1 * sp : g.width, h.y, down); }
        if (h.tieStop && i === 0) arc(0, h.x + 0.1 * sp, h.y, down);
      });
    }
    // tuplet numerals over (or under) the beat's stems
    ctx.font = `${3 * sp}px Bravura`;
    for (const tp of model.tuplets) {
      const st = g.stems.filter((s) => s.voice === tp.voice && Math.floor(s.pos / model.beatTicks) === tp.beat);
      if (!st.length) continue;
      const up = st[0].up, xa = Math.min(...st.map((s) => s.x)), xb = Math.max(...st.map((s) => s.x));
      const y = up ? Math.min(...st.map((s) => s.yEnd)) - 0.8 * sp : Math.max(...st.map((s) => s.yEnd)) + 2.2 * sp;
      ctx.fillText(SMUFL.tuplet(tp.actual), (xa + xb) / 2 - 0.5 * sp, y);
    }
    ctx.font = font;
    // octave lines per bar
    ctx.lineWidth = 0.1 * sp;
    for (const staff of [1, 2]) {
      const o = model.octave[staff];
      if (!o) continue;
      const above = o === 8;
      const y = above ? L.staffTop[staff] - 3.2 * sp : L.staffBottom[staff] + 4.0 * sp;
      ctx.font = `${3 * sp}px Bravura`;
      ctx.fillText(above ? SMUFL.ottavaAlta : SMUFL.ottavaBassa, 0.4 * sp, y);
      ctx.font = font;
      ctx.setLineDash?.([0.6 * sp, 0.5 * sp]);
      ctx.beginPath(); ctx.moveTo(3.2 * sp, y - 0.6 * sp); ctx.lineTo(g.width - 0.4 * sp, y - 0.6 * sp); ctx.stroke();
      ctx.setLineDash?.([]);
    }
    // loose beats: a faint wave over the treble staff
    if (model.loose && model.loose.length) {
      ctx.globalAlpha *= 0.6;
      for (const b of model.loose) { const bb = g.beats[Math.floor(b)]; if (bb) { ctx.beginPath(); ctx.moveTo(bb.x + 0.3 * sp, L.staffTop[1] - 2 * sp); ctx.quadraticCurveTo(bb.x + bb.w / 2, L.staffTop[1] - 2.8 * sp, bb.x + bb.w - 0.3 * sp, L.staffTop[1] - 2 * sp); ctx.stroke(); } }
    }
    // the closing bar line
    ctx.globalAlpha = geom.ink === "light" ? INK.light : INK.full;
    ctx.fillRect(g.width - 0.16 * sp, yTop, 0.16 * sp, yBot - yTop);
    ctx.restore();
    return { width: g.width, boxes: g.boxes, ms: now ? now() - t0 : null, drawn: true, layout: g };
  }

  return {
    api: ENGRAVER_API, name: "house",
    ready(fonts) { fontsReady = !!(fonts && fonts.smufl); return fontsReady; },
    measureBar, engraveBar,
  };
}

export { flagCount };
