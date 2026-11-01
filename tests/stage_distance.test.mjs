// Virtual Stage: camera DISTANCE (arsenal/web/stage/distance.js). node --test tests/stage_distance.test.mjs
// Daniel, 2026-10-29: "can we think of a control scheme for camera distance so that i can trigger between closeup medium
// and far." Pure: the distance model (shot size on a log scale), the clamps (comfort, venue, structure, the 1.5 m rule),
// the handback, the beat landing, the clean cut, the fader's soft takeover, and the dolly that is never a zoom.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { STOPS, WIDTH, LN_RANGE, LOG_RATE_MAX, LOG_ACCEL_MAX, MIN_MOVE_BEATS, HANDBACK_BEATS, SUBJECT_MIN_M, widthOf, vOfWidth, stopOf,
         comfortSeconds, landingBeat, cutBeat, quintic, Channel, shotFrame, makeRoom, CameraDistance, KEY_STOPS }
  from "../arsenal/web/stage/distance.js";
import { prepareShot, shotPose, cameraModel, clearanceToStrand, clearanceToRings, CLEARANCE_M, DRONE, formationPoseSets }
  from "../arsenal/web/stage/camera.js";
import { expandScene, hallStructure } from "../arsenal/web/stage/rig.js";

const SCENE = JSON.parse(readFileSync(new URL("../arsenal/web/stage/sets/source-v1.json", import.meta.url), "utf8"));
const RIG = expandScene(SCENE);
const MODEL = cameraModel(RIG);
const HS = hallStructure(RIG.venue);
const ROOM = makeRoom(RIG.venue, [...HS.solid, ...HS.truss]);
const HOME = MODEL.z.map(() => ({ y: MODEL.homeY, roll: 0 }));
const SHOTS = Object.fromEntries(Object.entries(SCENE.cameras.shots).map(([id, d]) => [id, prepareShot({ id, ...d })]));
const close = (a, b, eps, msg = "") => assert.ok(Math.abs(a - b) <= eps, `${msg} ${a} != ${b} (eps ${eps})`);
const BPM = 150, SPB = 60 / BPM;
const newPose = () => ({ pos: [0, 0, 0], look: [0, 0, 0], hfov: 50, roll: 0, ev: 0 });
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const mk = () => new CameraDistance({ room: ROOM, z: MODEL.z, rings: MODEL.rings });

// one frame of a static shot through the layer at beat position pos (t = pos x SPB: a steady clock)
function frame(D, shot, pos, { u = 0.5, poses = HOME, cut = false } = {}) {
  const p = shotPose(shot, u, pos, newPose());
  const director = { pos: p.pos.slice(), look: p.look.slice(), hfov: p.hfov, roll: p.roll, ev: p.ev };
  const st = D.apply(p, shot, { t: pos * SPB, pos, poses, rings: null, cut });
  return { p, director, st };
}
const sizeK = (r) => dist(r.p.pos, r.p.look) / dist(r.director.pos, r.director.look);

test("shot size: CLOSE 14 m, MEDIUM the geometric middle (about 33.5 m), FAR 80 m across the frame at the subject", () => {
  close(widthOf(STOPS.close), WIDTH.close, 1e-12);
  close(widthOf(STOPS.far), WIDTH.far, 1e-9);
  close(widthOf(STOPS.medium), Math.sqrt(WIDTH.close * WIDTH.far), 1e-9);
  for (const v of [0, 0.1, 0.37, 0.5, 0.9, 1]) close(vOfWidth(widthOf(v)), v, 1e-12);
  assert.equal(stopOf(0.1), "close"); assert.equal(stopOf(0.5), "medium"); assert.equal(stopOf(0.95), "far");
  assert.deepEqual({ ...KEY_STOPS }, { KeyQ: "close", KeyW: "medium", KeyE: "far" });   // near-to-far, left to right
});

test("the beat landing: a press arrives ON the first beat line at least half a beat and the comfort time away", () => {
  const step = LN_RANGE / 2, full = LN_RANGE;
  // the comfort: a step about 0.36 s, the whole range about 0.73 s (peak rate LOG_RATE_MAX)
  close(comfortSeconds(step), 1.875 * step / LOG_RATE_MAX, 1e-12);
  assert.ok(comfortSeconds(step) < 0.4 && comfortSeconds(full) < 0.8);
  // 150 BPM: a step pressed on a beat lands on the next beat; pressed after mid-beat, the one after
  assert.equal(landingBeat(40.0, SPB, step), 41);
  assert.equal(landingBeat(40.2, SPB, step), 42);
  assert.equal(landingBeat(40.6, SPB, step), 42);
  // the whole range needs 1.8 beats at 150: never sooner
  assert.equal(landingBeat(40.0, SPB, full), 42);
  assert.equal(landingBeat(40.3, SPB, full), 43);
  // a tiny move still takes half a beat, landing on a line
  assert.equal(landingBeat(40.6, SPB, 0.01), 42);
  assert.equal(landingBeat(40.4, SPB, 0.01), 41);
  // every landing is a whole beat at least MIN_MOVE_BEATS and the comfort time after the press
  for (let pos = 0; pos < 8; pos += 0.07) for (const dl of [0, step, full]) for (const bpm of [90, 128, 150, 174]) {
    const spb = 60 / bpm, at = landingBeat(pos, spb, dl);
    assert.equal(at, Math.round(at));
    assert.ok(at - pos >= MIN_MOVE_BEATS - 1e-9 && (at - pos) * spb >= comfortSeconds(dl) - 1e-9);
    assert.ok(at - 1 - pos < Math.max(MIN_MOVE_BEATS, comfortSeconds(dl) / spb), "the FIRST such beat line");
  }
});

test("the clean cut: the next beat line, never within 2 beats of the director's last cut, and with the director's next cut when that is near", () => {
  assert.equal(cutBeat(40.3), 41);
  assert.equal(cutBeat(40.0), 41);
  assert.equal(cutBeat(40.3, 40), 42);                 // the director cut on 40: not before 42
  assert.equal(cutBeat(40.3, 36, 44), 41);             // the director's next cut is 3 beats after: two cuts, 3 beats apart
  assert.equal(cutBeat(42.5, 36, 44), 44);             // 43 would be 1 beat before the director's 44: one cut, on 44
  assert.equal(cutBeat(42.5, 36, 45), 43);             // 43 is exactly 2 beats before 45: allowed
});

test("the quintic: from rest it is the minimum-jerk move; retargeted mid-move it starts with the speed it had (no kink)", () => {
  const c = quintic(0, 0, 0, 1, 2);
  const at = (u) => c[0] + u * (c[1] + u * (c[2] + u * (c[3] + u * (c[4] + u * c[5]))));
  for (const u of [0, 0.3, 1, 1.4, 2]) close(at(u), 10 * (u / 2) ** 3 - 15 * (u / 2) ** 4 + 6 * (u / 2) ** 5, 1e-12);
  const ch = new Channel(0);
  ch.to(1, 0, 1);
  ch.tick(0.4, 0.4);
  const x = ch.x, v = ch.v;
  assert.ok(v > 0.5);
  ch.to(0.2, 0.4, 0.8);                                  // a second press bends the move
  ch.tick(0.4, 0);
  close(ch.x, x, 1e-12); close(ch.v, v, 1e-12);          // position and velocity continuous through the retarget
  ch.tick(1.2, 0.8);
  close(ch.x, 0.2, 1e-12); assert.equal(ch.v, 0);
});

test("auto is the director's pose exactly: the layer touches nothing until a stop is pressed", () => {
  const D = mk();
  for (const id of ["FOH_WIDE", "HALO_LOCK", "STRAND_FLYTHROUGH", "HELIX_CORKSCREW", "VERTIGO_TUNNEL"]) {
    for (const u of [0, 0.3, 0.97]) {
      const r = frame(D, SHOTS[id], 10, { u });
      assert.deepEqual(r.p.pos, r.director.pos, `${id} u=${u}`);
      assert.equal(r.st.k, 1);
    }
  }
  assert.equal(D.status().mode, "auto");
});

test("a dolly, never a zoom: the lens, the look point, the roll and the exposure are the shot's; only the distance along the same line changes", () => {
  for (const id of ["FOH_WIDE", "HALO_LOCK", "CRANE_RISE_REVEAL", "HEAD_ORBIT_SLOW", "WING_LAYERS", "CROWD_POV"]) {
    for (const stop of ["close", "far"]) {
      const D = mk();
      D.v.set(STOPS[stop]); D.w.set(1); D.mode = "manual";
      for (const u of [0.1, 0.5, 0.9]) {
        const r = frame(D, SHOTS[id], 10, { u });
        assert.deepEqual(r.p.look, r.director.look);
        assert.equal(r.p.hfov, r.director.hfov); assert.equal(r.p.roll, r.director.roll); assert.equal(r.p.ev, r.director.ev);
        const a = r.p.pos.map((x, i) => x - r.p.look[i]), b = r.director.pos.map((x, i) => x - r.director.look[i]);
        const la = Math.hypot(...a), lb = Math.hypot(...b);
        const cos = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (la * lb);
        assert.ok(cos > 1 - 1e-12, `${id} ${stop}: the camera stays on the shot's own line to the subject`);
      }
    }
  }
});

test("the size follows the stop: CLOSE frames 14 m at the subject (where nothing limits it), and a moving shot keeps its motion scaled by one factor", () => {
  const D = mk();
  D.v.set(STOPS.close); D.w.set(1); D.mode = "manual";
  const f = shotFrame(SHOTS.FOH_WIDE);
  const r = frame(D, SHOTS.FOH_WIDE, 10);
  const d = dist(r.p.pos, r.p.look);
  close(2 * d * Math.tan((r.p.hfov * Math.PI) / 360), WIDTH.close, 1e-6, "FOH_WIDE close: 14 m across at the look point");
  assert.equal(r.st.clamp, null);
  close(sizeK(r), WIDTH.close / f.wRef, 1e-9);
  // a crane: the same factor on every frame (it still rises; it is smaller in the frame by one ratio)
  const D2 = mk(); D2.v.set(STOPS.close); D2.w.set(1); D2.mode = "manual";
  const ks = [0.1, 0.3, 0.5, 0.7, 0.9].map((u) => sizeK(frame(D2, SHOTS.CRANE_RISE_REVEAL, 10, { u })));
  for (const k of ks) close(k, ks[0], 1e-9);
  const ys = [0.1, 0.9].map((u) => frame(D2, SHOTS.CRANE_RISE_REVEAL, 10, { u }).p.pos[1]);
  assert.ok(ys[1] > ys[0] + 1, "the crane still rises");
});

test("a press moves at once and lands on its beat; the same stop again hands back over two beats to the director's pose exactly", () => {
  const D = mk(), shot = SHOTS.HALO_LOCK, f = shotFrame(shot);
  const p0 = 40.1;
  frame(D, shot, p0 - 1 / 24);
  const res = D.press("close", { t: p0 * SPB, pos: p0, spb: SPB, shot });
  assert.equal(res.kind, "move");
  assert.equal(res.at, landingBeat(p0, SPB, Math.log(WIDTH.close / f.wRef)));
  const series = [];
  for (let pos = p0; pos <= res.at + 1; pos += 1 / 24) series.push({ pos, k: sizeK(frame(D, shot, pos)) });
  assert.ok(series[1].k < 1, "it starts moving on the next frame");
  for (let i = 1; i < series.length; i++) assert.ok(series[i].k <= series[i - 1].k + 1e-12, "monotonic, no overshoot");
  const landed = series.find((s) => s.pos >= res.at - 1e-9);
  const before = series.filter((s) => s.pos < res.at - 1 / 24 - 1e-9).at(-1);
  close(landed.k, WIDTH.close / f.wRef, 1e-9, "on the beat line it has arrived");
  assert.ok(before.k > landed.k + 1e-6, "and not a frame early");
  // the peak rate of size change keeps the comfort limit
  let peak = 0;
  for (let i = 1; i < series.length; i++) peak = Math.max(peak, Math.abs(Math.log(series[i].k / series[i - 1].k)) / (SPB / 24));
  assert.ok(peak <= LOG_RATE_MAX * 1.02, `peak ${peak.toFixed(2)} /s`);
  // Q again: back to the director, landing on a beat line at least two beats away
  const p1 = res.at + 1.3;
  const back = D.press("close", { t: p1 * SPB, pos: p1, spb: SPB, shot });
  assert.equal(back.kind, "handback");
  assert.ok(back.at - p1 >= HANDBACK_BEATS - 1e-9 && back.at === Math.round(back.at));
  assert.equal(D.status().mode, "auto");
  let prevK = sizeK(frame(D, shot, p1));
  for (let pos = p1 + 1 / 24; pos < back.at - 1e-9; pos += 1 / 24) { const k = sizeK(frame(D, shot, pos)); assert.ok(k >= prevK - 1e-12); prevK = k; }
  const end = frame(D, shot, back.at);
  assert.deepEqual(end.p.pos, end.director.pos, "the director's own pose, bit for bit");
});

test("Shift: a clean cut -- nothing moves before its beat, then the whole change on that frame", () => {
  const D = mk(), shot = SHOTS.FOH_WIDE, f = shotFrame(shot);
  const res = D.press("close", { t: 50.3 * SPB, pos: 50.3, spb: SPB, shot, cut: true, lastCutPos: 48, nextCutPos: 56 });
  assert.equal(res.kind, "cut"); assert.equal(res.at, 51);
  for (let pos = 50.3; pos < 51 - 1e-9; pos += 1 / 24) assert.equal(sizeK(frame(D, shot, pos)), 1);
  const r = frame(D, shot, 51);
  assert.equal(r.p.distCut, true);
  close(sizeK(r), WIDTH.close / f.wRef, 1e-9);
  assert.equal(D.cuts.length, 1);
  // and Shift on the active stop cuts back to auto on the beat
  const back = D.press("close", { t: 52.2 * SPB, pos: 52.2, spb: SPB, shot, cut: true, lastCutPos: 51, nextCutPos: 56 });
  assert.equal(back.kind, "cut"); assert.equal(back.at, 53);
  assert.ok(sizeK(frame(D, shot, 52.9)) < 1);
  assert.equal(sizeK(frame(D, shot, 53)), 1);
});

test("a second press mid-move bends the move: the size changes with no jolt, even where the venue's edge holds the first move", () => {
  const D = mk(), shot = SHOTS.HALO_LOCK;
  frame(D, shot, 20);
  const r1 = D.press("far", { t: 20 * SPB, pos: 20, spb: SPB, shot });
  assert.ok(r1.v < 1, "FAR is planned to the venue's edge (this shot would leave the hall), so the move lands there instead of meeting it");
  const lams = [];
  let pressed = false;
  for (let pos = 20; pos < 23.5; pos += 1 / 24) {
    if (!pressed && pos >= 20.75 - 1e-9) { D.press("close", { t: pos * SPB, pos, spb: SPB, shot }); pressed = true; }
    const r = frame(D, shot, pos);
    lams.push(Math.log(dist(r.p.pos, r.p.look)));
  }
  // the second difference of ln distance per frame (the size's acceleration): a kink would be a spike
  let worst = 0;
  for (let i = 2; i < lams.length; i++) worst = Math.max(worst, Math.abs(lams[i] - 2 * lams[i - 1] + lams[i - 2]));
  assert.ok(worst < 0.008, `worst second difference ${worst.toFixed(4)} (ln size per frame per frame)`);
});

test("the limits: the venue's edge, the 3 m subject floor, a dolly zoom keeps its own size, and never within 1.5 m of the strand or the rings", () => {
  // HALO_LOCK far would leave the hall at the back: held at the venue's edge
  const D = mk(); D.v.set(1); D.w.set(1); D.mode = "manual";
  const r = frame(D, SHOTS.HALO_LOCK, 10);
  assert.ok(ROOM.inside(r.p.pos) && r.st.clamp === "venue" && sizeK(r) > 1.2, JSON.stringify(r.st));
  // a dolly zoom is a lens move whose point is the subject's fixed size: untouched
  const D2 = mk(); D2.v.set(0); D2.w.set(1); D2.mode = "manual";
  const z = frame(D2, SHOTS.VERTIGO_TUNNEL, 10);
  assert.deepEqual(z.p.pos, z.director.pos); assert.equal(z.st.fixed, "dolly zoom");
  // a shot data may fix its size
  const fixedShot = prepareShot({ ...SHOTS.FOH_WIDE, id: "FIXED", distance: false });
  assert.equal(shotFrame(fixedShot).fixed, true);
  // the subject floor: a shot already near its subject never goes nearer than 3 m
  const near = prepareShot({ id: "NEAR", kind: "static", pos: [0, 6, 30], look: [0, 6, 26], hfov: 90 });
  const D3 = mk(); D3.v.set(0); D3.w.set(1); D3.mode = "manual";
  const n = frame(D3, near, 10);
  assert.ok(dist(n.p.pos, n.p.look) >= SUBJECT_MIN_M - 1e-9);
  // every shot of the set, every stop, along its move, against the strand at home and in the set's formations: 1.5 m
  const sets = [HOME, ...Object.values(RIG.formations).flatMap((fd) => formationPoseSets(fd, MODEL.z.length, 2) || [])].slice(0, 7);
  let worst = Infinity, where = "";
  for (const [id, shot] of Object.entries(SHOTS)) {
    if (shot.held) continue;
    for (const poses of sets) {
      // the director deals a shot only where it is clear: judge the layer only where the shot itself is
      for (const stop of ["close", "medium", "far"]) {
        const D4 = mk(); D4.v.set(STOPS[stop]); D4.w.set(1); D4.mode = "manual";
        for (const u of [0.05, 0.35, 0.65, 0.95]) {
          const own = shotPose(shot, u, 0, newPose());
          const ownClear = Math.min(clearanceToStrand(own.pos, poses, MODEL.z), clearanceToRings(own.pos, MODEL.rings));
          if (ownClear < CLEARANCE_M) continue;
          const r4 = frame(D4, shot, 0, { u, poses });
          const c = Math.min(clearanceToStrand(r4.p.pos, poses, MODEL.z), clearanceToRings(r4.p.pos, MODEL.rings));
          if (c < worst) { worst = c; where = `${id} ${stop} u=${u}`; }
        }
      }
    }
  }
  assert.ok(worst >= CLEARANCE_M - 1e-9, `closest ${worst.toFixed(3)} m at ${where}`);
});

test("comfort: a scaled move is never faster than the drone where the shot's own speed is known (a fast shot's FAR stays its own)", () => {
  for (const shot of Object.values(SHOTS)) {
    const f = shotFrame(shot);
    if (f.fixed || !(f.speed > 0)) continue;
    assert.ok(f.kMax >= 1);
    if (f.speed * f.kMax > DRONE.vmax + 1e-6) assert.equal(f.kMax, 1, `${shot.id}: its own speed ${f.speed.toFixed(1)} m/s`);
  }
  const fast = shotFrame(SHOTS.HEAD_ORBIT);
  assert.ok(fast.speed > DRONE.vmax && fast.kMax === 1);
});

test("the fader: soft takeover (nothing until it passes the live value), then it drives the distance smoothly; a key press lets go of it", () => {
  const D = mk(), shot = SHOTS.HALO_LOCK, f = shotFrame(shot);
  frame(D, shot, 30);
  // in auto the live value is the shot's own size; a fader far below does nothing
  const a = D.fader(0.05, { t: 30 * SPB, shot });
  assert.equal(a.caught, false);
  assert.equal(D.status().mode, "auto");
  close(a.live, f.vAuto, 1e-9);
  assert.equal(sizeK(frame(D, shot, 30.1)), 1);
  // moved up across the live value: caught, with no jump (the setting starts at the shot's own size)
  const b = D.fader(f.vAuto + 0.06, { t: 30.2 * SPB, shot });
  assert.equal(b.caught, true);
  const k0 = sizeK(frame(D, shot, 30.2));
  close(k0, 1, 0.05);                                    // the follower's first frame from rest: a start, not a jump
  // it follows the fader up (FAR is held at the venue's edge for this shot), smoothly
  let prev = k0;
  D.fader(0.95, { t: 30.2 * SPB, shot });
  for (let pos = 30.2 + 1 / 24; pos < 34; pos += 1 / 24) { const k = sizeK(frame(D, shot, pos)); assert.ok(k >= prev - 1e-9 && Math.log(k / prev) <= LOG_RATE_MAX * (SPB / 24) + 1e-6); prev = k; }
  assert.ok(prev > 1.2);
  assert.equal(D.status().source, "fader");
  // a key press takes over; the fader must pass the live value again
  D.press("close", { t: 34 * SPB, pos: 34, spb: SPB, shot });
  assert.equal(D.status().fader.caught, false);
  assert.equal(D.fader(0.9, { t: 34.1 * SPB, shot }).caught, false);
});

test("the HUD names the distance and whether it is manual or auto", () => {
  const D = mk(), shot = SHOTS.FOH_WIDE;
  frame(D, shot, 10);
  assert.match(D.hudText(shot), /^distance auto \(as shot: far\).*Q W E$/);
  D.press("close", { t: 10 * SPB, pos: 10, spb: SPB, shot });
  frame(D, shot, 10.1);
  assert.match(D.hudText(shot), /^distance CLOSE manual → beat \d+.*Q again = auto$/);
  for (let pos = 10.1; pos < 14; pos += 0.25) frame(D, shot, pos);
  assert.doesNotMatch(D.hudText(shot), /→/);
  D.auto({ t: 14 * SPB, pos: 14, spb: SPB, shot });
  assert.match(D.hudText(shot), /^distance auto \(handing back\)/);
  assert.equal(D.takeChange(), true); assert.equal(D.takeChange(), false);
});

// ------------------------------------------------------------------------------------- the review's findings (F1-F6) --
// a shot held at one stop through its whole move at 60 fps, the director's u on the pose (so the room is read ahead)
function hold(id, stop, poses = HOME, { fps = 60 } = {}) {
  const shot = SHOTS[id], D = mk(); D.v.set(STOPS[stop]); D.w.set(1); D.mode = "manual"; D.stop = stop; D.source = "key";
  const beats = (shot.bars ?? 4) * 4, N = Math.round(beats * SPB * fps), out = [];
  for (let i = 0; i <= N; i++) {
    const u = i / N, pos = 100 + u * beats, p = shotPose(shot, u, pos, newPose()); p.u = u;
    const own = Math.min(clearanceToStrand(p.pos, poses, MODEL.z), clearanceToRings(p.pos, MODEL.rings));
    const mount = p.pos.slice();
    const st = D.apply(p, shot, { t: pos * SPB, pos, poses, rings: null });
    out.push({ u, lam: st.lam, cut: !!p.distCut, own, mount, pos: p.pos.slice(), clamp: st.clamp,
               c: Math.min(clearanceToStrand(p.pos, poses, MODEL.z), clearanceToRings(p.pos, MODEL.rings)) });
  }
  return { D, out };
}

test("F1 the rigging grid: no stop lifts the lens into or over the grid's beams (a shot below it stays 1 m under them)", () => {
  const G = ROOM.grid;
  assert.ok(G.lo > 32 && G.hi < 34.5, JSON.stringify(G));
  let worst = -Infinity, where = "";
  for (const [id, shot] of Object.entries(SHOTS)) {
    if (shot.held || shotFrame(shot).fixed) continue;
    for (const stop of ["medium", "far"]) {
      for (const r of hold(id, stop, HOME, { fps: 20 }).out) {
        if (r.mount[1] > (G.lo + G.hi) / 2) continue;        // (no shot of the set stands above the grid)
        if (r.pos[1] > worst) { worst = r.pos[1]; where = `${id} ${stop} u=${r.u.toFixed(3)}`; }
        assert.ok(ROOM.inside(r.pos, r.mount), `${id} ${stop} u=${r.u.toFixed(3)}: ${r.pos.map((x) => x.toFixed(2))}`);
      }
    }
  }
  assert.ok(worst <= G.lo - 1 + 1e-9, `highest lens ${worst.toFixed(2)} m at ${where} (the grid's beams start at ${G.lo})`);
  // the review's black frames: TOPDOWN_DESCEND at FAR is held under the grid, and the HUD says so
  const { D, out } = hold("TOPDOWN_DESCEND", "far");
  const r = out[Math.round(0.2 * (out.length - 1))];
  assert.ok(r.pos[1] <= G.lo - 1 + 1e-9 && r.clamp === "grid", JSON.stringify({ y: r.pos[1], clamp: r.clamp }));
  assert.match(D.hudText(SHOTS.TOPDOWN_DESCEND), /held at the rigging grid/);
});

test("F2 held at a stop through every shot's whole move (60 fps): no jolt, no oscillation, the 1.5 m rule every frame, no forced cut", () => {
  const RATE = LOG_RATE_MAX / 60, ACC = LOG_ACCEL_MAX / 3600;
  let d1 = 0, d2 = 0, rev = 0, cuts = 0, clear = Infinity;
  const where = {};
  for (const [id, shot] of Object.entries(SHOTS)) {
    if (shot.held || shotFrame(shot).fixed) continue;
    for (const stop of ["close", "medium", "far"]) {
      const { out } = hold(id, stop);
      let a = null, b = null, last = 0, n = 0;
      for (const r of out) {
        if (r.own < CLEARANCE_M) { a = b = null; continue; }     // the director's own pose in the rig is his guard's business
        if (r.lam !== 0 && r.c < clear) { clear = r.c; where.clear = `${id} ${stop} u=${r.u.toFixed(3)}`; }
        assert.ok(ROOM.inside(r.pos, r.mount) || r.lam === 0, `${id} ${stop} u=${r.u.toFixed(3)} outside the room`);
        if (r.cut) { cuts++; a = b = null; continue; }
        if (a !== null) {
          const s1 = r.lam - a;
          if (Math.abs(s1) > d1) { d1 = Math.abs(s1); where.d1 = `${id} ${stop} u=${r.u.toFixed(3)}`; }
          if (Math.abs(s1) > 2e-3) { const sg = Math.sign(s1); if (last && sg !== last) n++; last = sg; }
          if (b !== null) { const s2 = Math.abs(r.lam - 2 * a + b); if (s2 > d2) { d2 = s2; where.d2 = `${id} ${stop} u=${r.u.toFixed(3)}`; } }
        }
        b = a; a = r.lam;
      }
      if (n > rev) { rev = n; where.rev = `${id} ${stop}`; }
    }
  }
  const msg = JSON.stringify({ d1, d2, rev, cuts, clear, where });
  assert.ok(d1 <= RATE * (1 + 1e-9), `the size never changes faster than e^4.5 a second: ${msg}`);
  assert.ok(d2 <= ACC * (1 + 1e-6), `nor accelerates faster than LOG_ACCEL_MAX: ${msg}`);
  assert.ok(rev <= 5, `no oscillation (direction reversals of more than 0.002 a frame): ${msg}`);
  assert.equal(cuts, 0, `the rig at home never forces a cut: ${msg}`);
  assert.ok(clear >= CLEARANCE_M, msg);
});

test("F2 the formations: the review's jitter shots ride smoothly; the rare forced cut is a cut, on a beat line when one comes first", () => {
  const RATE = LOG_RATE_MAX / 60, ACC = LOG_ACCEL_MAX / 3600;
  const sets = Object.fromEntries(Object.entries(RIG.formations).map(([k, fd]) => [k, (formationPoseSets(fd, MODEL.z.length, 1) || [])[0]]).filter(([, s]) => s));
  for (const [id, stop, key] of [["THREAD_THE_ZIPPER", "close", "high-wave"], ["TUBE_RIDE", "far", "high-wave"], ["TUBE_RIDE", "close", "home"],
                                 ["STRAND_FLYTHROUGH", "close", "home"], ["HEAD_ORBIT", "close", "home"], ["CRANE_RISE_REVEAL", "far", "home"],
                                 ["WING_LAYERS", "far", "home"], ["CRANE_RISE_REVEAL", "medium", "high-wave"], ["SPIRAL_ASCENT", "close", "high-wave"]]) {
    const poses = key === "home" ? HOME : sets[key];
    const { out } = hold(id, stop, poses);
    let a = null, b = null;
    for (const r of out) {
      if (r.own < CLEARANCE_M || r.cut) { a = b = null; continue; }
      assert.ok(r.lam === 0 || r.c >= CLEARANCE_M, `${id} ${stop} ${key} u=${r.u.toFixed(3)}: ${r.c.toFixed(2)} m`);
      if (a !== null) assert.ok(Math.abs(r.lam - a) <= RATE * (1 + 1e-9), `${id} ${stop} ${key} u=${r.u.toFixed(3)}: step ${(r.lam - a).toFixed(3)}`);
      if (b !== null) assert.ok(Math.abs(r.lam - 2 * a + b) <= ACC * (1 + 1e-6), `${id} ${stop} ${key} u=${r.u.toFixed(3)}: jolt`);
      b = a; a = r.lam;
    }
  }
  // CRANE_RISE_REVEAL in the high wave: its scaled rise meets a rung no move can clear -- one cut, on the beat line
  const { D } = hold("CRANE_RISE_REVEAL", "close", sets["high-wave"]);
  assert.ok(D.cuts.length <= 1 && D.cuts.every((c) => c.why === "rig, on the beat" && c.pos === Math.round(c.pos)), JSON.stringify(D.cuts));
});

test("F3 a press the room holds short of its stop: the HUD says what holds it, and the next shot gets the stop itself", () => {
  const D = mk(), halo = SHOTS.HALO_LOCK, foh = SHOTS.FOH_WIDE;
  frame(D, halo, 20);
  const r = D.press("far", { t: 20 * SPB, pos: 20, spb: SPB, shot: halo });
  assert.ok(r.v < 1, "planned to the venue's edge");
  for (let pos = 20; pos <= r.at + 0.5; pos += 1 / 24) frame(D, halo, pos);
  assert.equal(D.stop, "far");
  assert.match(D.hudText(halo), /^distance FAR manual · held at the venue's edge/);
  // the director cuts to FOH_WIDE: FAR there is the full 80 m
  const c = frame(D, foh, r.at + 1, { cut: true });
  const w = 2 * dist(c.p.pos, c.p.look) * Math.tan((c.p.hfov * Math.PI) / 360);
  close(w, WIDTH.far, 1e-6, "FOH_WIDE at FAR after the cut");
  assert.doesNotMatch(D.hudText(foh), /held/);
});

test("F4 the fader's soft takeover survives a key press: a brush of the fader after Q does not grab the camera", () => {
  const D = mk(), shot = SHOTS.FOH_WIDE;
  frame(D, shot, 10);
  D.fader(1.0, { t: 10 * SPB, shot });
  assert.equal(D.fader(0.6, { t: 10.1 * SPB, shot }).caught, true);        // caught from above
  for (let pos = 10.1; pos < 14; pos += 1 / 24) frame(D, shot, pos);
  D.press("close", { t: 14 * SPB, pos: 14, spb: SPB, shot });
  for (let pos = 14; pos < 18; pos += 1 / 24) frame(D, shot, pos);
  const k = D.last.k;
  const n = D.fader(0.61, { t: 18 * SPB, shot });
  assert.equal(n.caught, false, "0.60 -> 0.61 never passed the live value (0, CLOSE)");
  for (let pos = 18; pos < 20; pos += 1 / 24) frame(D, shot, pos);
  assert.equal(D.last.k, k); assert.equal(D.status().source, "key");
  // it catches when it really passes through the live value
  D.fader(0.01, { t: 20 * SPB, shot });
  assert.equal(D.fader(0.0, { t: 20.1 * SPB, shot }).caught, true);
});

test("F6 Shift during a move: the move eases to rest within a quarter second (no jolt), then nothing moves until the cut on its beat", () => {
  const D = mk(), shot = SHOTS.FOH_WIDE;
  frame(D, shot, 40);
  D.press("close", { t: 40 * SPB, pos: 40, spb: SPB, shot });
  let pos = 40;
  for (; pos < 40.1 - 1e-9; pos += 1 / 24) frame(D, shot, pos);
  const p0 = pos;
  const r = D.press("far", { t: pos * SPB, pos, spb: SPB, shot, cut: true, lastCutPos: 30, nextCutPos: 60 });
  assert.equal(r.kind, "cut"); assert.equal(r.at, 41);
  const ks = [];
  for (pos += 1 / 24; pos < r.at - 1e-9; pos += 1 / 24) ks.push({ pos, k: sizeK(frame(D, shot, pos)) });
  for (let i = 1; i < ks.length; i++) assert.ok(ks[i].k <= ks[i - 1].k + 1e-12, "it keeps going the way it was going, slowing");
  const after = ks.filter((x) => (x.pos - p0) * SPB > 0.25 + 1e-9);
  assert.ok(after.length >= 3 && after.every((x) => Math.abs(x.k - after[0].k) < 1e-12), "at rest after a quarter second");
  // an ease-out, not a stop: no step faster than the comfort, and the last steps before rest tiny
  const steps = ks.map((x, i) => (i ? Math.log(ks[i - 1].k / x.k) : 0)).slice(1);
  assert.ok(Math.max(...steps) <= LOG_RATE_MAX * (SPB / 24) + 1e-9);
  const lastMove = steps.findLastIndex((x) => x > 1e-12);
  assert.ok(lastMove >= 1 && steps[lastMove] < 0.25 * Math.max(...steps), JSON.stringify(steps.map((x) => +x.toFixed(4))));
  const c = frame(D, shot, r.at);
  assert.equal(c.p.distCut, true);
});
