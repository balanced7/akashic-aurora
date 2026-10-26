// Virtual Stage v0, lasers in 3D: arsenal/web/stage/lasers3d.js (pure ES module). Tests: tests/stage_lasers.test.mjs.
//
// The laser brain draws a PICTURE (Lasers v2's frame: centred units, frame height 1). A real projector draws the same
// picture as angles from its aperture. This adapter maps each picture segment from head h onto the projector that plays
// head h in the rig (the scene's lasers.projectors, in Lasers v2's head order: A1..A8, B1..B8, SL1, SL2, SR1, SR2, HERO)
// as a 3D ray:
//
//     d = normalize(r_h * dx + u_h * dy + f_h * k_h * |d2|)
//
// r, u, f are the projector's right, up and forward axes (forward = its aim, toward the audience by default), (dx, dy)
// the segment's picture direction, and k the REACH (depth ratio) of its role: Bank B 0.6 (a laser ceiling over the
// crowd), Bank A 0.9, towers 0.4, hero 1.0, times the look's own reach and the K7 knob. With k = 0 the front-of-house
// camera sees exactly the 2D picture; k > 0 throws the beams out over the crowd. A ray ends where it meets the room (the
// floor and the crowd's heads, the roof, the walls): a dot is drawn there.
//
// Power is physical (design 6.6, receipt L2): a projector's channel power (laser-10w: R 2 W, G 3 W, B 3 W) is shared
// among the beams it draws this frame in proportion to their intensities (gamma 1; a "show" gamma of 0.5 is Daniel's
// call), so the sum over its beams never exceeds what it has. One hot beam is blinding; a fan of 24 is a lace.
// Red is never emitted (the brain already refuses it; this checks again). Camera exclusion (L9, L14 as look rules): a
// beam whose axis passes within 2 degrees of the camera is attenuated to 10 %, and a beam passing closer than 4 m to the
// camera fades with its distance (a flythrough would otherwise wipe a blinding line across the whole frame).
//
// Output, 16 floats per 3D segment (the design's FrameState.lasers):
//   ox oy oz  ex ey ez  pr pg pb (watts)  width0 (m: the aperture at the origin)  divergence (rad, full angle)  kind  flags
//   head  dist0 (m: how far the origin is from the aperture, after clipping to the camera)  intensity
// flags: 1 = the ray ends on a surface (draw a dot), 2 = attenuated by the camera exclusion, 4 = clipped at the camera's
// near plane, 8 = faded for passing close to the camera.
//
// v1 (2026-10-25): projectors past the 21 Lasers v2 heads (the halo's twelve on ring 0) come in the brain's own head
// list (heads: LaserEngine.heads), and a head the brain gives an aim override (frame.aim[h * 4 .. + 3] = [x, y, z, k],
// k > 0) draws in that frame and depth ratio this frame: a laser riding a ring points where the ring holds it.

import { SEG, SEG_FLOATS, MAX_SEGMENTS, HEADS, isSaturatedRed } from "./lasers.js";

export const L3_FLOATS = 16;
export const L3 = Object.freeze({ OX: 0, OY: 1, OZ: 2, EX: 3, EY: 4, EZ: 5, PR: 6, PG: 7, PB: 8, W0: 9, DIV: 10, KIND: 11,
  FLAGS: 12, HEAD: 13, DIST0: 14, I: 15 });
const DEG = Math.PI / 180;

function norm(v) {
  const [x, y, z] = v;
  const inv = 1 / (Math.hypot(x, y, z) || 1);
  v[0] *= inv; v[1] *= inv; v[2] *= inv;
  return v;
}
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }

// The projector's frame from its aim: forward f = aim, right r = up x f (horizontal), up u = f x r.
export function projectorBasis(aim) {
  const f = norm(aim.slice());
  let r = cross([0, 1, 0], f);
  if (Math.hypot(r[0], r[1], r[2]) < 1e-6) r = [1, 0, 0];
  norm(r);
  // three.js frame: with f = +z (toward the audience), r = up x f = +x (house right). The FOH camera looks down -z, so
  // a picture's +x lands on the screen's right as the brain drew it.
  const u = norm(cross(f, r));
  return { r, u, f };
}

// The room's surfaces, as the axis-aligned box the hall fits in plus the crowd plane (heads at 1.9 m, over the floor in
// front of the stage) and the deck (2 m, upstage of the lip). Returns the distance along d to the first one, and which.
export function roomHit(o, d, venue) {
  const fx = venue.floor && venue.floor.x || [-38, 38], fz = venue.floor && venue.floor.z || [-24, 96];
  const roof = venue.roof_y ?? 38, crowdY = venue.crowd_y ?? 1.9, deckY = venue.deck_y ?? 2, deckZ = venue.deck_z ?? [-16, 0];
  let best = Infinity, what = "none";
  const plane = (axis, value, name, test) => {
    const dv = d[axis];
    if (Math.abs(dv) < 1e-9) return;
    const t = (value - o[axis]) / dv;
    if (t <= 1e-4 || t >= best) return;
    const p = [o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t];
    if (test && !test(p)) return;
    best = t; what = name;
  };
  plane(0, fx[0], "wall"); plane(0, fx[1], "wall");
  plane(2, fz[0], "wall"); plane(2, fz[1], "wall");
  plane(1, roof, "roof");
  plane(1, 0, "floor");
  plane(1, crowdY, "crowd", (p) => p[2] > 1 && o[1] > crowdY);
  plane(1, deckY, "deck", (p) => p[2] >= deckZ[0] && p[2] <= deckZ[1] && o[1] > deckY);
  return { t: best, what };
}

export class Lasers3D {
  constructor(projectors, venue = {}, { gamma = 1, exclusionDeg = 2, heads = HEADS } = {}) {
    if (projectors.length !== heads.length) throw new Error(`lasers3d: ${projectors.length} projectors for ${heads.length} heads`);
    projectors.forEach((p, i) => {
      if (p.name && p.name !== heads[i].name) throw new Error(`lasers3d: projector ${i} is ${p.name}, the brain's head ${i} is ${heads[i].name}`);
    });
    this.p = projectors.map((p) => ({ ...p, basis: projectorBasis(p.aim || [0, 0, 1]) }));
    this.venue = venue;
    this.gamma = gamma;
    this.exclusionCos = Math.cos(exclusionDeg * DEG);
    this.out = { seg: new Float32Array(MAX_SEGMENTS * L3_FLOATS), n: 0, power: new Float32Array(projectors.length * 3),
                 excluded: 0, dots: 0, clipped: 0 };
    this.share = new Float32Array(MAX_SEGMENTS);
  }
  // frame2d: the brain's frame() output. opts: reachScale (K7 and the look), master (F4, 0..1), camera {pos, fwd, near}
  map(frame2d, { reachScale = 1, master = 1, camera = null } = {}) {
    const o = this.out, s2 = frame2d.seg, n2 = frame2d.n;
    o.n = 0; o.excluded = 0; o.near = 0; o.dots = 0; o.clipped = 0; o.power.fill(0);
    // the intensity sum per projector, for the power share
    const sum = new Float64Array(this.p.length);
    for (let i = 0; i < n2; i++) {
      const b = i * SEG_FLOATS;
      sum[s2[b + SEG.HEAD]] += Math.pow(Math.max(0, s2[b + SEG.I]), this.gamma);
    }
    for (let i = 0; i < n2 && o.n < MAX_SEGMENTS; i++) {
      const b = i * SEG_FLOATS;
      const h = s2[b + SEG.HEAD], I = Math.max(0, s2[b + SEG.I]);
      if (I <= 0 || !(sum[h] > 0)) continue;
      const pr = this.p[h];
      const ao = frame2d.aim && frame2d.aim[h * 4 + 3] > 0 ? h * 4 : -1;
      const { r, u, f } = ao >= 0 ? projectorBasis([frame2d.aim[ao], frame2d.aim[ao + 1], frame2d.aim[ao + 2]]) : pr.basis;
      const dx = s2[b + SEG.X1] - s2[b + SEG.X0], dy = s2[b + SEG.Y1] - s2[b + SEG.Y0];
      const len2 = Math.hypot(dx, dy);
      if (len2 < 1e-9) continue;
      const k = ao >= 0 ? frame2d.aim[ao + 3] : (pr.reach ?? 0.6) * reachScale * (frame2d.reach ?? 1);
      const d = norm([r[0] * dx + u[0] * dy + f[0] * k * len2, r[1] * dx + u[1] * dy + f[1] * k * len2,
                      r[2] * dx + u[2] * dy + f[2] * k * len2]);
      const origin = pr.pos;
      const hit = roomHit(origin, d, this.venue);
      const tEnd = Number.isFinite(hit.t) ? hit.t : 200;
      // colour: never a saturated red
      let cr = s2[b + SEG.R], cg = s2[b + SEG.G], cb = s2[b + SEG.B];
      if (isSaturatedRed([cr, cg, cb])) { cr = 0.9; cg = 0.75; cb = 0.55; }
      const cmax = Math.max(cr, cg, cb, 1e-6);
      const share = Math.pow(I, this.gamma) / sum[h];
      const pw = pr.power_w;
      let PR = pw[0] * share * (cr / cmax) * master, PG = pw[1] * share * (cg / cmax) * master, PB = pw[2] * share * (cb / cmax) * master;
      let flags = Number.isFinite(hit.t) ? 1 : 0;
      // camera exclusion: the beam's axis within exclusionDeg of the direction to the camera
      let t0 = 0, t1 = tEnd;
      if (camera) {
        const toCam = [camera.pos[0] - origin[0], camera.pos[1] - origin[1], camera.pos[2] - origin[2]];
        const dc = Math.hypot(toCam[0], toCam[1], toCam[2]) || 1;
        const cosA = (toCam[0] * d[0] + toCam[1] * d[1] + toCam[2] * d[2]) / dc;
        if (cosA > this.exclusionCos && dc < tEnd) { PR *= 0.1; PG *= 0.1; PB *= 0.1; flags |= 2; o.excluded++; }
        // the closest approach of the beam to the camera (along the drawn part)
        const tc = Math.max(0, Math.min(tEnd, toCam[0] * d[0] + toCam[1] * d[1] + toCam[2] * d[2]));
        const near2 = Math.hypot(origin[0] + d[0] * tc - camera.pos[0], origin[1] + d[1] * tc - camera.pos[1], origin[2] + d[2] * tc - camera.pos[2]);
        if (near2 < 4) { const f = Math.max(0.05, (near2 - 1) / 3); const k = f < 0 ? 0.05 : f; PR *= k; PG *= k; PB *= k; flags |= 8; o.near++; }
        // clip to the camera's front (the renderer projects; a segment behind the camera would invert)
        const near = camera.near ?? 0.1, cf = camera.fwd;
        const s0 = (origin[0] - camera.pos[0]) * cf[0] + (origin[1] - camera.pos[1]) * cf[1] + (origin[2] - camera.pos[2]) * cf[2];
        const sd = d[0] * cf[0] + d[1] * cf[1] + d[2] * cf[2];
        // depth along the camera axis at distance t: s0 + sd t; keep where it is > near
        if (Math.abs(sd) < 1e-9) { if (s0 <= near) { o.clipped++; continue; } }
        else {
          const tn = (near - s0) / sd;
          if (sd > 0) t0 = Math.max(t0, tn); else t1 = Math.min(t1, tn);
        }
        if (t1 <= t0) { o.clipped++; continue; }
        if (t0 > 0) flags |= 4;
      }
      const w = o.n * L3_FLOATS, seg = o.seg;
      seg[w + L3.OX] = origin[0] + d[0] * t0; seg[w + L3.OY] = origin[1] + d[1] * t0; seg[w + L3.OZ] = origin[2] + d[2] * t0;
      seg[w + L3.EX] = origin[0] + d[0] * t1; seg[w + L3.EY] = origin[1] + d[1] * t1; seg[w + L3.EZ] = origin[2] + d[2] * t1;
      seg[w + L3.PR] = PR; seg[w + L3.PG] = PG; seg[w + L3.PB] = PB;
      seg[w + L3.W0] = (pr.aperture_mm ?? 3) / 1000; seg[w + L3.DIV] = (pr.divergence_mrad ?? 0.6) / 1000;
      seg[w + L3.KIND] = s2[b + SEG.KIND]; seg[w + L3.FLAGS] = t1 < tEnd ? flags & ~1 : flags; seg[w + L3.HEAD] = h;
      seg[w + L3.DIST0] = t0; seg[w + L3.I] = I;
      this.share[o.n] = share;
      o.power[h * 3] += PR; o.power[h * 3 + 1] += PG; o.power[h * 3 + 2] += PB;
      if (seg[w + L3.FLAGS] & 1) o.dots++;
      o.n++;
    }
    return o;
  }
}
