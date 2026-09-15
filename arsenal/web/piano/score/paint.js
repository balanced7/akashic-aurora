// The ribbon painter for what changes often or claims no rhythm: arsenal/web/piano/score/paint.js (Canvas2D; needs a 2D
// context only: no DOM, no clock). Slice LS5 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md
// (sections 2.1, 5.1, 7.3), amended by plan-amendments.md C6 (tape) and the LS3 header item (ls1-rulings.md "Readout
// after x0.5": the dimmed request with "hold", never a blank).
//
//   paintStaves(ctx, L, { width, clefs, fifths, fonts })    band-local: staff lines across the band, brace, clefs, signature
//   paintHeader(ctx, L, header, { fonts })                  page coordinates: "♩ ≈ 84 · loose · heard" and the meter
//   paintTape(ctx, L, columns, { dx, fonts, endX, ticks, freely })   heads by time, duration lines, 1 s ticks, "freely"
//   paintOpenBar(ctx, L, layout, { x, fonts })              heads at their slot inside fixed-width beats, beat ticks; no
//                                                           stems, beams or rests (the rhythm is not decided yet)
//   paintPedalLine(ctx, L, segments, { dx })                one bracket line along the band bottom, a notch per change
//
// Heads are vector ellipses (no font needed); accidentals use Bravura once fonts.smufl is true, else text glyphs.

import { stepY, ledgerSteps, keySigGlyphs } from "./layout.js";
import { SMUFL, ACC_GLYPH } from "./engrave.js";

export const PAINT_API = "arsenal.piano.score.paint/v0";
// The page's pinned Bravura (piano.js BRAVURA_URL, C9: no new host). tests/score_layout.test.mjs checks the two strings.
export const BRAVURA_URL = "https://cdn.jsdelivr.net/npm/@vexflow-fonts/bravura@1.0.2/bravura.woff2";

export const PAINT_COLORS = Object.freeze({ ink: "#ece6d6", faint: "rgba(236,230,214,0.28)", staff: "rgba(236,230,214,0.55)", tape: "#9fd3c7", open: "#ece6d6", pedal: "rgba(236,230,214,0.7)", bg: "#0d0f14" });
const TEXT_ACC = Object.freeze({ "-2": "\u{1D12B}", "-1": "♭", "0": "♮", "1": "♯", "2": "\u{1D12A}" });

export const SOURCE_WORD = Object.freeze({ jam: "jam", song: "song", taps: "tap", inferred: "heard", free: "—", none: "—", auto: "heard" });

function head(ctx, x, y, sp, filled) {
  ctx.beginPath();
  ctx.ellipse(x + 0.59 * sp, y, 0.6 * sp, 0.42 * sp, -0.35, 0, Math.PI * 2);
  if (filled) ctx.fill(); else { ctx.lineWidth = 0.16 * sp; ctx.stroke(); }
}
function accidental(ctx, acc, x, y, sp, fonts) {
  const k = String(Math.max(-2, Math.min(2, acc)));
  if (fonts && fonts.smufl) { ctx.font = `${4 * sp}px Bravura`; ctx.fillText(ACC_GLYPH[k], x, y); }
  else { ctx.font = `${2.2 * sp}px serif`; ctx.fillText(TEXT_ACC[k], x, y + 0.7 * sp); }
}

// --------------------------------------------------------------------------------------------- staves ---
export function paintStaves(ctx, L, { width = L.band.w, clefs = { 1: "treble", 2: "bass" }, fifths = 0, fonts = null, colors = PAINT_COLORS, clefColumn = true } = {}) {
  const sp = L.sp;
  ctx.save();
  ctx.strokeStyle = colors.staff; ctx.lineWidth = 0.1 * sp;
  ctx.beginPath();
  for (const staff of [1, 2]) for (let i = 0; i < 5; i++) { const y = L.staffTop[staff] + i * sp; ctx.moveTo(0, y); ctx.lineTo(width, y); }
  ctx.stroke();
  let colW = 0;
  if (clefColumn) {
    colW = (4.2 + Math.abs(fifths) * 1.0 + 0.8) * sp;
    ctx.fillStyle = colors.bg; ctx.globalAlpha = 0.92;
    ctx.fillRect(0, 0, colW, L.tileH - 2.2 * sp);
    ctx.globalAlpha = 1;
    ctx.beginPath();
    for (const staff of [1, 2]) for (let i = 0; i < 5; i++) { const y = L.staffTop[staff] + i * sp; ctx.moveTo(0, y); ctx.lineTo(colW, y); }
    ctx.stroke();
    ctx.fillStyle = colors.ink;
    ctx.fillRect(0, L.staffTop[1], 0.16 * sp, L.staffBottom[2] - L.staffTop[1]);
    if (fonts && fonts.smufl) {
      ctx.font = `${4 * sp}px Bravura`; ctx.textBaseline = "alphabetic";
      for (const staff of [1, 2]) {
        const cl = clefs[staff];
        ctx.fillText(cl === "treble" ? SMUFL.gClef : SMUFL.fClef, 0.7 * sp, stepY(L, staff, cl === "treble" ? -2 : 2));
        for (const k of keySigGlyphs(fifths, cl)) ctx.fillText(ACC_GLYPH[String(k.acc)], (3.9 + k.x) * sp, stepY(L, staff, k.step));
      }
    } else {
      ctx.font = `${1.4 * sp}px sans-serif`;
      for (const staff of [1, 2]) ctx.fillText(clefs[staff] === "treble" ? "G" : "F", 1.0 * sp, L.staffTop[staff] + 2.5 * sp);
      if (fifths) ctx.fillText((fifths > 0 ? "♯" : "♭") + Math.abs(fifths), 2.4 * sp, L.staffTop[1] + 1.4 * sp);
    }
  }
  ctx.restore();
  return { clefColumn: colW };
}

// --------------------------------------------------------------------------------------------- header ---
// header: index.js tick() header ({ bpm, dim, word, requested, source, meter, drawing, chip, suggestion }). A null bpm
// reads "…" (never a blank); a family press pending shows the requested tempo dimmed with "hold" (meter.js header model).
export function headerText(header) {
  const h = header || {};
  const bpm = h.bpm != null ? String(Math.round(h.bpm)) : "…";
  const word = h.word || "free";
  const src = SOURCE_WORD[h.source] ?? (h.source || "—");
  return { left: `♩ ≈ ${bpm} · ${word} · ${src}`, right: h.meter || "4/4", dim: !!h.dim || word === "hold", chip: h.chip ? (h.chip.kind === "triplets" ? "triplets?" : "straight?") : h.suggestion ? `${h.suggestion.meter || h.suggestion}?` : null };
}
export function paintHeader(ctx, L, header, { fonts = null, colors = PAINT_COLORS } = {}) {
  const sp = L.sp, t = headerText(header);
  ctx.save();
  ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
  ctx.fillStyle = colors.ink;
  ctx.globalAlpha = t.dim ? 0.45 : 1;
  ctx.font = `600 ${1.9 * sp}px "JetBrains Mono", ui-monospace, monospace`;
  const y = L.header.y + L.header.h * 0.75;
  ctx.fillText(t.left, L.header.x, y);
  ctx.globalAlpha = 1;
  ctx.textAlign = "right";
  ctx.fillText(t.right, L.band.x1, y);
  if (t.chip) { ctx.globalAlpha = 0.7; ctx.font = `${1.3 * sp}px "JetBrains Mono", ui-monospace, monospace`; ctx.fillText(t.chip, L.band.x1 - 5 * sp, y); }
  ctx.restore();
  return t;
}

// ---------------------------------------------------------------------------------------------- tape ---
// columns: [{ x, w, headX, heads: [{ staff, step, acc, dx, se (sound end ms or null), id }] }] in content x; dx: content
// x -> canvas x offset; endX(se) -> content x of a sound end (the warped time axis). ticks, freely: content xs.
export function paintTape(ctx, L, columns, { dx = 0, fonts = null, endX = null, ticks = [], freely = [], colors = PAINT_COLORS, alpha = 1 } = {}) {
  const sp = L.sp;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
  // ticks: faint marks under the lower staff
  ctx.strokeStyle = colors.faint; ctx.lineWidth = 0.1 * sp;
  ctx.beginPath();
  for (const x of ticks) { const X = x + dx; ctx.moveTo(X, L.staffBottom[2] + 1.2 * sp); ctx.lineTo(X, L.staffBottom[2] + 2.0 * sp); }
  ctx.stroke();
  // duration lines
  ctx.strokeStyle = colors.tape; ctx.lineWidth = 0.12 * sp; ctx.globalAlpha = alpha * 0.6;
  ctx.beginPath();
  if (endX) for (const col of columns) for (const h of col.heads) {
    const hx = col.headX + (h.dx || 0) + dx + 1.2 * sp, ex = endX(h) + dx, y = stepY(L, h.staff, h.step);
    if (ex > hx) { ctx.moveTo(hx, y); ctx.lineTo(ex, y); }
  }
  ctx.stroke();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = colors.tape; ctx.strokeStyle = colors.tape;
  ctx.lineWidth = 0.16 * sp;
  ctx.beginPath();
  for (const col of columns) for (const h of col.heads) for (const s of ledgerSteps(h.step)) {
    const y = stepY(L, h.staff, s), hx = col.headX + (h.dx || 0) + dx;
    ctx.moveTo(hx - 0.35 * sp, y); ctx.lineTo(hx + 1.53 * sp, y);
  }
  ctx.stroke();
  for (const col of columns) for (const h of col.heads) {
    const hx = col.headX + (h.dx || 0) + dx, y = stepY(L, h.staff, h.step);
    head(ctx, hx, y, sp, true);
    if (h.acc != null) accidental(ctx, h.acc, col.x + dx + 0.05 * sp, y, sp, fonts);
  }
  if (freely.length) {
    ctx.font = `italic ${1.3 * sp}px Georgia, serif`; ctx.fillStyle = colors.ink; ctx.globalAlpha = alpha * 0.8;
    for (const x of freely) ctx.fillText("freely", x + dx, L.staffTop[1] - 2.2 * sp);
  }
  ctx.restore();
  return columns.length;
}

// ------------------------------------------------------------------------------------------ open bar ---
// layout: layout.js layoutBar(model, L, { widen: false }); x: canvas x of the bar's left edge.
export function paintOpenBar(ctx, L, layout, { x = 0, fonts = null, colors = PAINT_COLORS, alpha = 1 } = {}) {
  const sp = L.sp;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
  ctx.strokeStyle = colors.faint; ctx.lineWidth = 0.12 * sp;
  ctx.beginPath();
  layout.beats.forEach((b, j) => {
    const X = x + b.x;
    if (j === 0) { ctx.moveTo(X, L.staffTop[1]); ctx.lineTo(X, L.staffBottom[2]); }
    else { ctx.moveTo(X, L.staffTop[1] - 1.2 * sp); ctx.lineTo(X, L.staffTop[1] - 0.4 * sp); ctx.moveTo(X, L.staffBottom[2] + 0.4 * sp); ctx.lineTo(X, L.staffBottom[2] + 1.2 * sp); }
  });
  ctx.stroke();
  ctx.strokeStyle = colors.open; ctx.fillStyle = colors.open; ctx.lineWidth = 0.16 * sp;
  ctx.beginPath();
  for (const h of layout.heads) for (const s of ledgerSteps(h.step)) { const y = stepY(L, h.staff, s); ctx.moveTo(x + h.x - 0.35 * sp, y); ctx.lineTo(x + h.x + 1.53 * sp, y); }
  ctx.stroke();
  for (const h of layout.heads) head(ctx, x + h.x, h.y, sp, h.kind === "black");
  for (const a of layout.accidentals) accidental(ctx, a.acc, x + a.x, a.y, sp, fonts);
  ctx.restore();
  return layout.heads.length;
}

// --------------------------------------------------------------------------------------------- pedal ---
// segments: [{ x0, x1, notches: [x], open }] in content x (the caller maps marks.js pedalMarks times to x).
export function paintPedalLine(ctx, L, segments, { dx = 0, colors = PAINT_COLORS } = {}) {
  const sp = L.sp, y = L.pedalY;
  ctx.save();
  ctx.strokeStyle = colors.pedal; ctx.lineWidth = 0.14 * sp;
  ctx.beginPath();
  for (const s of segments) {
    const a = s.x0 + dx, b = s.x1 + dx;
    ctx.moveTo(a, y - 0.9 * sp); ctx.lineTo(a, y);
    for (const n of s.notches) { const X = n + dx; ctx.lineTo(X - 0.45 * sp, y); ctx.lineTo(X, y - 0.9 * sp); ctx.lineTo(X + 0.45 * sp, y); }
    ctx.lineTo(b, y);
    if (!s.open) ctx.lineTo(b, y - 0.9 * sp);
  }
  ctx.stroke();
  ctx.restore();
  return segments.length;
}
