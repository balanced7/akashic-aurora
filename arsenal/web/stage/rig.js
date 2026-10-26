// Virtual Stage v0, the rig model: arsenal/web/stage/rig.js (pure ES module: no DOM, no WebGL). Tests:
// tests/stage_rig.test.mjs.
//
// Daniel, 2026-10-24: "Also I want us to recreate that set or something similar with no fewer lasers and fog machines
// and lights. This will require research to find out how those things are wired and animated so we can build our own
// routines for this."
//
// A rig is data, not code. The scene file (format arsenal.arena/v1, the design of 2026-10-24, section 2.7) names fixture
// TYPES (GDTF-shaped: a geometry tree Body > Yoke (Pan) > Head (Tilt) > Beam or Pixel, attribute definitions with real
// travel times, a beam definition), OBJECTS (structures that never move and elements that hang from hoists, each with
// child fixtures, with `repeat` generators so twelve rungs are one entry), GROUPS (selectors over the expanded rig),
// focus points, effects, formations, looks, cameras and the show. expandScene() turns it into flat, typed, deterministic
// arrays: the same file always gives the same rig, in the same order.
//
// The frame (identical to the rig lane's rig-layout.json and three.js): the origin is on the floor at the centre of the
// stage lip; +x is house right (the audience's right when facing the stage), +y is up, +z runs out over the crowd.
// Metres, degrees, levels 0..1; time in beats.
//
// The MVR/GDTF bridge (DIN SPEC 15801 / 15800 are right-handed and Z-up, X left to right, Y into the screen, 1 unit =
// 1 mm): three = (x, z, -y) / 1000. The rotation part has determinant +1 (a proper rotation, no mirror), and MVR's +Y
// (upstage) becomes our -z. mvrToStage / stageToMvr are exact inverses.
//
// Nothing here is copied from a manufacturer's personality or from the GDTF/MVR spec text: the types are generic class
// personalities we write ourselves, and the travel times marked "est." are estimates until measured.
//
// v1 (2026-10-25, Daniel: "the three levels seems to be altitudes on the circular array where they group the lasers into
// thirds"): a polar repeat may name a RING PARAMETER for its count, start and step (each ring carries its own head count);
// a polar child's rot is added to the radial frame (rot [90, 0, 0] stands a head on the ring's face); every polar
// placement knows its CLOCK angle (0 at the top, clockwise as seen from front of house) and its LEVEL, the altitude third
// it belongs to by the ring-local angle (top |clock| < 60, middle 60..120, bottom beyond), so a tilt never moves a fixture
// between thirds. Groups take `where` ({tag, level, ring, side}) and `union` (earlier groups, same kind), and carry the
// order keys clock, level, level_mirror (top and bottom equal), column (1, 2, 3 outward by |x|) and depth (by z). Laser
// projectors may MOUNT on an element (a ring), and aimAt() turns a world point into pan and tilt (world-locked presets).

export const SCENE_FORMAT = "arsenal.arena/v1";

const DEG = Math.PI / 180;
const isNum = (x) => typeof x === "number" && Number.isFinite(x);
const isVec3 = (v) => Array.isArray(v) && v.length === 3 && v.every(isNum);

// ------------------------------------------------------------------------------------------------ the MVR bridge --
// The 3 x 3 rotation from MVR axes to ours (rows: our x, y, z in MVR components). Scale 1/1000 (mm -> m) is separate.
export const MVR_TO_STAGE = Object.freeze([[1, 0, 0], [0, 0, 1], [0, -1, 0]]);
export function det3(m) {
  return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
       + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
}
export function mvrToStage(p) { return [p[0] / 1000, p[2] / 1000, -p[1] / 1000]; }
export function stageToMvr(p) { return [p[0] * 1000, -p[2] * 1000, p[1] * 1000]; }

// --------------------------------------------------------------------------------------------- small vector maths --
// Rotation matrices are 3 x 3, row-major arrays of 9. Euler [rx, ry, rz] in degrees, applied X then Y then Z
// (R = Rz * Ry * Rx), the same convention as three.js's default 'XYZ' order.
export function eulerToMat3(rot, out = new Float64Array(9)) {
  const [rx, ry, rz] = rot ? rot.map((d) => d * DEG) : [0, 0, 0];
  const cx = Math.cos(rx), sx = Math.sin(rx), cy = Math.cos(ry), sy = Math.sin(ry), cz = Math.cos(rz), sz = Math.sin(rz);
  // Rz * Ry * Rx
  out[0] = cz * cy; out[1] = cz * sy * sx - sz * cx; out[2] = cz * sy * cx + sz * sx;
  out[3] = sz * cy; out[4] = sz * sy * sx + cz * cx; out[5] = sz * sy * cx - cz * sx;
  out[6] = -sy;     out[7] = cy * sx;                out[8] = cy * cx;
  return out;
}
export function mat3MulVec(m, v, out = [0, 0, 0]) {
  const x = v[0], y = v[1], z = v[2];
  out[0] = m[0] * x + m[1] * y + m[2] * z;
  out[1] = m[3] * x + m[4] * y + m[5] * z;
  out[2] = m[6] * x + m[7] * y + m[8] * z;
  return out;
}
export function mat3Mul(a, b, out = new Float64Array(9)) {
  const r = new Float64Array(9);
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) {
    r[i * 3 + j] = a[i * 3] * b[j] + a[i * 3 + 1] * b[3 + j] + a[i * 3 + 2] * b[6 + j];
  }
  out.set(r);
  return out;
}

// ------------------------------------------------------------------------------------------------- validation --
// Every problem the scene has, as plain sentences (an empty list is a valid scene). The page refuses to start on a bad
// scene and shows these; the node test feeds it broken scenes.
export function validateScene(scene) {
  const errors = [];
  const err = (m) => errors.push(m);
  if (!scene || typeof scene !== "object") return ["the scene is not an object"];
  if (scene.format !== SCENE_FORMAT) err(`format must be "${SCENE_FORMAT}" (got ${JSON.stringify(scene.format)})`);
  if (!scene.types || typeof scene.types !== "object") err("types: missing");
  if (!Array.isArray(scene.objects) || !scene.objects.length) err("objects: missing or empty");
  const types = scene.types || {};
  for (const [name, t] of Object.entries(types)) {
    if (!/^[a-z0-9][a-z0-9-]{0,31}$/.test(name)) err(`types.${name}: a type name is lower-case letters, digits and dashes`);
    if (!t || typeof t !== "object") { err(`types.${name}: not an object`); continue; }
    if (!["head", "pixel", "laser", "atmos", "axis", "sfx"].includes(t.class)) err(`types.${name}.class: one of head, pixel, laser, atmos, axis, sfx`);
    if (t.class === "pixel" && !(Number.isInteger(t.cells) && t.cells >= 1 && t.cells <= 4096)) err(`types.${name}.cells: an integer 1..4096`);
    for (const [a, def] of Object.entries(t.attrs || {})) {
      if ("min" in def && "max" in def && !(isNum(def.min) && isNum(def.max) && def.min < def.max)) err(`types.${name}.attrs.${a}: min < max`);
      if ("real_fade" in def && !(isNum(def.real_fade) && def.real_fade > 0)) err(`types.${name}.attrs.${a}.real_fade: a positive number of seconds`);
      if ("real_accel" in def && !(isNum(def.real_accel) && def.real_accel > 0)) err(`types.${name}.attrs.${a}.real_accel: a positive number of seconds`);
    }
  }
  const ids = new Set();
  for (const [i, o] of (scene.objects || []).entries()) {
    const where = `objects[${i}]${o && o.id ? ` (${o.id})` : ""}`;
    if (!o || typeof o !== "object") { err(`${where}: not an object`); continue; }
    if (!/^[a-z0-9][a-z0-9-]{0,31}$/.test(String(o.id))) err(`${where}.id: lower-case letters, digits and dashes`);
    if (ids.has(o.id)) err(`${where}.id: duplicate id`);
    ids.add(o.id);
    if (!["element", "structure"].includes(o.kind)) err(`${where}.kind: element or structure`);
    if (o.repeat) checkRepeat(o.repeat, where + ".repeat", err);
    if (!o.repeat && !isVec3(o.at)) err(`${where}.at: [x, y, z] for an object without repeat`);
    if (o.kind === "element") {
      if (!Array.isArray(o.dof) || !o.dof.length) err(`${where}.dof: the degrees of freedom, e.g. ["y", "roll"]`);
      for (const d of o.dof || []) if (!["y", "roll", "tilt"].includes(d)) err(`${where}.dof: unknown degree of freedom ${d}`);
      if (o.limits) for (const [d, lim] of Object.entries(o.limits)) {
        if (!(Array.isArray(lim) && lim.length === 2 && isNum(lim[0]) && isNum(lim[1]) && lim[0] < lim[1])) err(`${where}.limits.${d}: [lo, hi]`);
      }
    }
    for (const [j, c] of (o.children || []).entries()) {
      const cw = `${where}.children[${j}]`;
      if (!types[c.type]) err(`${cw}.type: unknown type ${JSON.stringify(c.type)}`);
      if (c.repeat) checkRepeat(c.repeat, cw + ".repeat", err);
      else if (c.ring) { if (!(typeof c.ring.radius === "string" || isNum(c.ring.radius))) err(`${cw}.ring.radius: a number or a ring parameter name`); }
      else if (!Array.isArray(c.at) || !c.at.length || !c.at.every(isVec3)) err(`${cw}.at: a list of [x, y, z]`);
      if (c.rot !== undefined && !isVec3(c.rot)) err(`${cw}.rot: [rx, ry, rz] degrees`);
    }
  }
  const seen = new Set();
  for (const [g, def] of Object.entries(scene.groups || {})) {
    if (!def || typeof def !== "object") { err(`groups.${g}: not an object`); continue; }
    if (def.union !== undefined) {
      if (!Array.isArray(def.union) || !def.union.length) err(`groups.${g}.union: a list of earlier group names`);
      else for (const u of def.union) if (!seen.has(u)) err(`groups.${g}.union: ${JSON.stringify(u)} is not a group defined above it`);
    } else if (typeof def.select !== "string" || !/^[a-z0-9.*-]+\/[a-z0-9-]+$/.test(def.select)) err(`groups.${g}.select: "<object>.*/<type>" or "<object>/<type>"`);
    if (def.where !== undefined) {
      if (!def.where || typeof def.where !== "object") err(`groups.${g}.where: an object`);
      else for (const k of Object.keys(def.where)) if (!["tag", "level", "ring", "side"].includes(k)) err(`groups.${g}.where.${k}: one of tag, level, ring, side`);
    }
    seen.add(g);
  }
  const l = scene.lasers;
  if (l) {
    if (!Array.isArray(l.projectors)) err("lasers.projectors: a list");
    else for (const [i, p] of l.projectors.entries()) {
      if (p.mount) {
        const m = p.mount;
        if (!(typeof m.object === "string" && Number.isInteger(m.index ?? 0) && isNum(m.angle_deg))) err(`lasers.projectors[${i}].mount: {object, index, angle_deg, radius}`);
        else if (!(scene.objects || []).some((o) => o && o.id === m.object)) err(`lasers.projectors[${i}].mount.object: unknown object ${JSON.stringify(m.object)}`);
      } else if (!isVec3(p.pos)) err(`lasers.projectors[${i}].pos: [x, y, z]`);
      if (!types[p.type]) err(`lasers.projectors[${i}].type: unknown type ${JSON.stringify(p.type)}`);
    }
  }
  return errors;
}

function checkRepeat(r, where, err) {
  const named = (v) => r.polar && typeof v === "string" && /^[a-z_][a-z0-9_]*$/.test(v);
  if (!(named(r.count) || (Number.isInteger(r.count) && r.count >= 1 && r.count <= 4096))) err(`${where}.count: an integer 1..4096 (or, on a polar repeat, a ring parameter name)`);
  for (const ax of ["x", "y", "z"]) {
    if (r[ax] !== undefined && !(r[ax] && isNum(r[ax].from) && isNum(r[ax].step))) err(`${where}.${ax}: {from, step}`);
  }
  if (r.values) for (const [k, v] of Object.entries(r.values)) {
    if (!Array.isArray(v) || v.length !== r.count) err(`${where}.values.${k}: one value per instance (${r.count})`);
  }
  if (r.polar && !((isNum(r.polar.step_deg) || named(r.polar.step_deg)) && (isNum(r.polar.radius) || typeof r.polar.radius === "string"))) err(`${where}.polar: {radius, step_deg}`);
  if (r.polar && r.polar.from_deg !== undefined && !(isNum(r.polar.from_deg) || named(r.polar.from_deg))) err(`${where}.polar.from_deg: degrees or a ring parameter name`);
}

// ------------------------------------------------------------------------------------------------- expansion --
// Type classes: head (a moving head: Pan, Tilt, a beam), pixel (a strip or block of LED cells), laser (a projector),
// atmos (hazer), axis (hoist / tilt), sfx (v1).
export const CELL_KIND = Object.freeze({ dot: 0, bar: 1, cube: 2, slat: 3, rim: 4, lens: 5 });

function repeatInstances(rep, base = [0, 0, 0]) {
  if (!rep) return [{ pos: base.slice(), params: {}, index: 0 }];
  const out = [];
  for (let i = 0; i < rep.count; i++) {
    const pos = base.slice();
    for (const [k, ax] of [[0, "x"], [1, "y"], [2, "z"]]) if (rep[ax]) pos[k] += rep[ax].from + rep[ax].step * i;
    const params = {};
    for (const [k, v] of Object.entries(rep.values || {})) params[k] = v[i];
    out.push({ pos, params, index: i });
  }
  return out;
}

// A number, or the instance's parameter of that name (a polar repeat's count, start or step can differ per ring).
function paramNum(params, v, what) {
  if (isNum(v)) return v;
  if (typeof v === "string" && isNum(params[v])) return params[v];
  throw new Error(`polar ${what}: no ring parameter ${JSON.stringify(v)}`);
}
// The clock angle of a polar angle a (radians, 0 = +x, counter-clockwise in the element's x-y plane): 0 at the top,
// clockwise as seen from front of house, in (-180, 180] degrees. The level: the altitude third by that ring-local angle.
export function clockOf(a) {
  let t = 90 - a / DEG;
  t = ((t + 180) % 360 + 360) % 360 - 180;
  return t <= -180 + 1e-9 ? 180 : t;
}
export const LEVEL_TOP_DEG = 60, LEVEL_MID_DEG = 120;
export function levelOf(clockDeg) {
  const t = Math.abs(clockDeg);
  return t < LEVEL_TOP_DEG ? 0 : t <= LEVEL_MID_DEG ? 1 : 2;
}

// A ring's named radii: outer = diameter / 2, inner = outer - depth (the annulus of slats).
function ringParam(params, name) {
  if (isNum(name)) return name;
  const outer = (params.diameter || 0) / 2;
  if (name === "outer") return outer;
  if (name === "inner") return outer - (params.depth || 0);
  if (name === "mid") return outer - (params.depth || 0) / 2;
  if (isNum(params[name])) return params[name];
  throw new Error(`unknown ring parameter ${name}`);
}

// Cells of one pixel fixture, in the fixture's own frame: along +x for strips, a grid for matrices, faces for a cube.
function fixtureCells(type, spanM = null) {
  const n = type.cells;
  const len = spanM !== null ? spanM : (type.length || 0);
  const cells = [];
  if (type.layout === "cube") {
    const h = (type.size || 1) / 2;
    const faces = [[h, 0, 0], [-h, 0, 0], [0, h, 0], [0, -h, 0], [0, 0, h], [0, 0, -h]];
    for (let i = 0; i < n; i++) cells.push(faces[i % 6]);
  } else if (type.layout === "radial") {
    for (let i = 0; i < n; i++) cells.push([0, len * (i + 0.5) / n, 0]);     // along local +y (outward on a ring)
  } else {
    for (let i = 0; i < n; i++) cells.push([n === 1 ? 0 : -len / 2 + len * (i + 0.5) / n, 0, 0]);
  }
  return cells;
}

// The whole rig, flat. Deterministic: objects in file order, instances in repeat order, children in file order.
export function expandScene(scene) {
  const errors = validateScene(scene);
  if (errors.length) throw new Error(`invalid scene: ${errors.join("; ")}`);
  const types = scene.types;
  const elements = [];      // movable or static frames: {key, id, index, kind, origin, home, limits, dof, pickups, params}
  const fixtures = [];      // {key, type, cls, element, local, rot, tags, head, cell0, ncell}
  const heads = [];         // fixture indices of moving heads
  const cellPos = [];       // local position in the ELEMENT frame (x, y, z), per cell
  const cellMeta = [];      // {fixture, element, kind, along, angle, size}
  for (const o of scene.objects) {
    const insts = o.repeat ? repeatInstances(o.repeat, isVec3(o.at) ? o.at : [0, 0, 0]) : [{ pos: o.at.slice(), params: {}, index: 0 }];
    for (const inst of insts) {
      const params = { ...(o.params || {}), ...inst.params };
      const eIdx = elements.length;
      const home = { ...(o.home || {}) };
      for (const d of ["y", "roll", "tilt"]) if (isNum(params[d])) home[d] = params[d];
      if (o.kind === "element" && home.y === undefined) home.y = inst.pos[1];
      elements.push({ key: `${o.id}.${inst.index}`, id: o.id, index: inst.index, kind: o.kind, origin: inst.pos,
                      home, limits: o.limits || {}, dof: o.dof || [], pickups: o.pickups || [], axisType: o.axis_type || null,
                      params, mesh: o.mesh || null, count: insts.length });
      const childCounts = {};
      for (const c of o.children || []) {
        const type = types[c.type];
        const placements = [];
        if (c.repeat && c.repeat.polar) {
          const r = ringParam(params, c.repeat.polar.radius);
          const count = paramNum(params, c.repeat.count, "count");
          const from = paramNum(params, c.repeat.polar.from_deg ?? 0, "from_deg");
          const step = paramNum(params, c.repeat.polar.step_deg, "step_deg");
          const r0 = c.rot || [0, 0, 0];
          for (let i = 0; i < count; i++) {
            const a = (from + step * i) * DEG;
            // radial: the fixture's local +y points outward; it sits in the element's x-y plane. A child rot is added to
            // the radial frame: [90, 0, 0] turns +y onto the ring's face normal (a head standing on the face).
            placements.push({ at: [r * Math.cos(a), r * Math.sin(a), 0], rot: [r0[0], r0[1], a / DEG - 90 + r0[2]], angle: a,
                              span: c.span ? ringParam(params, c.span) : null });
          }
        } else if (c.repeat) {
          for (const ri of repeatInstances(c.repeat, isVec3(c.at && c.at[0]) ? c.at[0] : [0, 0, 0])) {
            placements.push({ at: ri.pos, rot: c.rot || [0, 0, 0], angle: null, span: null });
          }
        } else if (c.ring) {
          placements.push({ at: [0, 0, 0], rot: [0, 0, 0], ring: ringParam(params, c.ring.radius), angle: null, span: null });
        } else {
          for (const at of c.at) placements.push({ at, rot: c.rot || [0, 0, 0], angle: null, span: null });
        }
        for (const pl of placements) {
          const k = childCounts[c.type] = (childCounts[c.type] || 0);
          childCounts[c.type]++;
          const fIdx = fixtures.length;
          const f = { key: `${o.id}.${inst.index}/${c.type}.${k}`, type: c.type, cls: type.class, element: eIdx,
                      local: pl.at.slice(), rot: pl.rot.slice(), tags: c.tags || [], head: -1, cell0: -1, ncell: 0,
                      angle: pl.angle, clock: pl.angle !== null ? clockOf(pl.angle) : null,
                      level: pl.angle !== null ? levelOf(clockOf(pl.angle)) : -1 };
          if (type.class === "head") { f.head = heads.length; heads.push(fIdx); }
          if (type.class === "pixel") {
            f.cell0 = cellPos.length;
            let local;
            if (pl.ring !== undefined) {
              // a ring outline: one cell per type.pitch metres round the circle, in the element's x-y plane
              const n = Math.max(8, Math.round((2 * Math.PI * pl.ring) / (type.pitch || 0.25)));
              local = [];
              for (let i = 0; i < n; i++) {
                const a = (2 * Math.PI * i) / n;
                local.push({ p: [pl.ring * Math.cos(a), pl.ring * Math.sin(a), 0], along: i / n, angle: a });
              }
            } else {
              const m = eulerToMat3(pl.rot);
              local = fixtureCells(type, pl.span).map((p, i, all) => {
                const q = mat3MulVec(m, p);
                return { p: [pl.at[0] + q[0], pl.at[1] + q[1], pl.at[2] + q[2]], along: all.length > 1 ? i / (all.length - 1) : 0,
                         angle: pl.angle !== null ? pl.angle : Math.atan2(pl.at[1] + q[1], pl.at[0] + q[0]) };
              });
            }
            for (const c2 of local) {
              cellPos.push(c2.p);
              cellMeta.push({ fixture: fIdx, element: eIdx, kind: CELL_KIND[type.cell_kind] ?? 0, along: c2.along,
                              angle: c2.angle, size: type.cell_size || 0.05 });
            }
            f.ncell = local.length;
          }
          fixtures.push(f);
        }
      }
    }
  }
  const nCell = cellPos.length;
  const cells = {
    n: nCell,
    pos: Float32Array.from(cellPos.flat()),
    fixture: Int32Array.from(cellMeta.map((c) => c.fixture)),
    element: Int32Array.from(cellMeta.map((c) => c.element)),
    kind: Uint8Array.from(cellMeta.map((c) => c.kind)),
    along: Float32Array.from(cellMeta.map((c) => c.along)),
    angle: Float32Array.from(cellMeta.map((c) => c.angle)),
    size: Float32Array.from(cellMeta.map((c) => c.size)),
  };
  const rig = {
    format: scene.format, name: scene.name, seed: scene.seed || 1, mode: (scene.show && scene.show.mode) || "real",
    venue: scene.venue || {}, types, elements, fixtures, heads, cells,
    projectors: expandProjectors(scene, elements),
    hazers: (scene.atmos && scene.atmos.hazers || []).map((h, i) => ({ id: h.id || `hazer.${i}`, type: h.type || "hazer", pos: h.pos.slice(),
                                                                       out: h.out ?? 1 })),
    focus: scene.focus || {}, effects: scene.effects || {}, formations: scene.formations || {}, looks: scene.looks || {},
    cameras: scene.cameras || {}, show: scene.show || {}, themes: scene.themes || {}, atmos: scene.atmos || {},
    groups: {},
  };
  for (const [name, def] of Object.entries(scene.groups || {})) rig.groups[name] = buildGroup(rig, name, def, rig.groups);
  rig.laserGroups = buildLaserGroups(rig.projectors, scene.laser_groups || {});
  rig.phrases = scene.phrases || {};
  rig.presets = scene.presets || {};
  rig.counts = countRig(rig);
  return rig;
}

// Laser groups: projectors by bank (A, B, S, H, R) and, for ring-mounted ones, by level; members ordered by x then
// height (a chase across a bank runs house left to house right). The member numbers are the projectors' indices, which
// are the laser brain's head indices.
export function buildLaserGroups(projectors, defs) {
  const out = {};
  for (const [name, def] of Object.entries(defs || {})) {
    const banks = def.banks || [];
    const levels = def.level === undefined ? null : [].concat(def.level);
    const heads = projectors.filter((p) => banks.includes(p.bank) && (!levels || levels.includes(p.level)))
      .sort((a, b) => (a.pos[0] - b.pos[0]) || (a.pos[1] - b.pos[1]) || (a.index - b.index)).map((p) => p.index);
    out[name] = { name, kind: "lasers", banks, level: levels, heads, n: heads.length };
  }
  return out;
}

// A projector at a fixed position, or MOUNTED on an element ({object, index, angle_deg, radius}: a point on a ring at
// that polar angle, at the element's home pose; the projector then carries the ring's clock angle and level too).
function expandProjectors(scene, elements = []) {
  const l = scene.lasers;
  if (!l || !Array.isArray(l.projectors)) return [];
  return l.projectors.map((p, i) => {
    let pos = isVec3(p.pos) ? p.pos.slice() : null, clock = null, level = -1, element = -1, radial = null, normal = null;
    if (p.mount) {
      const m = p.mount;
      element = elements.findIndex((e) => e.id === m.object && e.index === (m.index ?? 0));
      if (element < 0) throw new Error(`lasers.projectors[${i}].mount: no element ${m.object}.${m.index ?? 0}`);
      const el = elements[element];
      const r = ringParam(el.params, m.radius ?? "outer");
      const a = m.angle_deg * DEG;
      const em = elementMatrix(el);
      pos = transformPoint(em, [r * Math.cos(a), r * Math.sin(a), m.offset ?? 0]);
      clock = clockOf(a); level = levelOf(clock);
      // the mount's frame in world space: radially out in the ring's plane, and the ring's face normal
      radial = [em[0] * Math.cos(a) + em[1] * Math.sin(a), em[3] * Math.cos(a) + em[4] * Math.sin(a), em[6] * Math.cos(a) + em[7] * Math.sin(a)];
      normal = [em[2], em[5], em[8]];
    }
    return projectorOf(scene, l, p, i, pos, { clock, level, element, radial, normal });
  });
}
function projectorOf(scene, l, p, i, pos, extra) {
  return {
    index: i, name: p.name, bank: p.bank, role: p.role || p.bank, type: p.type, pos, ...extra,
    reach: isNum(p.reach) ? p.reach : (l.reach && l.reach[p.bank]) ?? 0.6,
    aim: isVec3(p.aim) ? p.aim.slice() : [0, 0, 1],
    power_w: (scene.types[p.type] && scene.types[p.type].power_w) || [2, 3, 3],
    divergence_mrad: (scene.types[p.type] && scene.types[p.type].divergence_mrad) || 0.6,
    aperture_mm: (scene.types[p.type] && scene.types[p.type].aperture_mm) || 3,
  };
}

// ---------------------------------------------------------------------------------------------- element frames --
// The home pose of an element: a 3 x 4 world matrix (rotation 3 x 3 row-major + translation) from its origin, its home
// height and its roll (about the strand axis, z) or tilt (about x).
export function elementMatrix(el, pose = null, out = new Float64Array(12)) {
  const y = pose && isNum(pose.y) ? pose.y : (isNum(el.home.y) ? el.home.y : el.origin[1]);
  const roll = pose && isNum(pose.roll) ? pose.roll : (el.home.roll || 0);
  const tilt = pose && isNum(pose.tilt) ? pose.tilt : (el.home.tilt || 0);
  // tilt leans the element back about x (a ring at tilt 0 faces the audience; at 90 it lies flat, face up)
  const m = eulerToMat3([-tilt, 0, roll]);
  out.set(m, 0);
  out[9] = el.origin[0]; out[10] = el.kind === "element" ? y : el.origin[1]; out[11] = el.origin[2];
  return out;
}
export function transformPoint(m12, p, out = [0, 0, 0]) {
  const x = p[0], y = p[1], z = p[2];
  out[0] = m12[0] * x + m12[1] * y + m12[2] * z + m12[9];
  out[1] = m12[3] * x + m12[4] * y + m12[5] * z + m12[10];
  out[2] = m12[6] * x + m12[7] * y + m12[8] * z + m12[11];
  return out;
}

// --------------------------------------------------------------------------------------------------- groups --
// A selector "rung.*/beam-7r" (every instance of object rung) or "truss-us/beam-7r" (the one instance). A group holds
// heads (moving heads), cells (pixels) or fixtures, plus the order keys a Spread can sort by, computed at the home pose:
// index, world x/y/z, helix (the strand parameter: element index, the two backbones as two wings), side (-1/+1 by local
// x), along (0..1 along a strip), angle (about a ring's centre), azimuth and radius (about the group's centre),
// element (the element's index within its object).
export function selectFixtures(rig, select) {
  const [objPart, typePart] = select.split("/");
  const all = objPart.endsWith(".*");
  const objId = all ? objPart.slice(0, -2) : objPart;
  const out = [];
  for (let i = 0; i < rig.fixtures.length; i++) {
    const f = rig.fixtures[i], el = rig.elements[f.element];
    if (el.id !== objId || f.type !== typePart) continue;
    if (!all && el.count > 1) continue;     // "rung/x" on a repeated object selects nothing: say rung.*
    out.push(i);
  }
  return out;
}

// A group's members as entries {fi, cell}: the selector's fixtures (every cell of a pixel fixture), filtered by `where`
// ({tag, level, ring, side}: a fixture tag, the altitude third, the element's index in its object, the side of x), or the
// union of earlier groups (one kind only).
function memberLevel(rig, f, cell) {
  if (cell >= 0) return rig.elements[f.element].id === "ring" || f.angle !== null ? levelOf(clockOf(rig.cells.angle[cell])) : -1;
  return f.level ?? -1;
}
function memberClock(rig, f, cell) {
  if (cell >= 0) return clockOf(rig.cells.angle[cell]);
  return f.clock ?? null;
}
function groupEntries(rig, def, groups) {
  if (def.union) {
    const out = [];
    for (const u of def.union) {
      const g = groups[u];
      if (!g) throw new Error(`group union: no group ${u}`);
      for (let m = 0; m < g.n; m++) out.push({ fi: g.memberFixture[m], cell: g.kind === "cells" ? g.members[m] : -1, kind: g.kind });
    }
    const kinds = new Set(out.map((e) => e.kind));
    if (kinds.size > 1) throw new Error(`group union mixes ${[...kinds].join(" and ")}`);
    return filterEntries(rig, out, def.where);
  }
  const fx = selectFixtures(rig, def.select);
  const type = fx.length ? rig.types[rig.fixtures[fx[0]].type] : null;
  const out = [];
  for (const fi of fx) {
    const f = rig.fixtures[fi];
    if (type && type.class === "pixel") for (let c = f.cell0; c < f.cell0 + f.ncell; c++) out.push({ fi, cell: c });
    else out.push({ fi, cell: -1 });
  }
  return filterEntries(rig, out, def.where);
}
function filterEntries(rig, entries, where) {
  if (!where) return entries;
  return entries.filter(({ fi, cell }) => {
    const f = rig.fixtures[fi], el = rig.elements[f.element];
    if (where.tag !== undefined && !(f.tags || []).includes(where.tag)) return false;
    if (where.ring !== undefined && (Array.isArray(where.ring) ? !where.ring.includes(el.index) : el.index !== where.ring)) return false;
    if (where.level !== undefined) {
      const lv = memberLevel(rig, f, cell);
      if (Array.isArray(where.level) ? !where.level.includes(lv) : lv !== where.level) return false;
    }
    if (where.side !== undefined) {
      const x = cell >= 0 ? transformPoint(elementMatrix(el), [rig.cells.pos[cell * 3], rig.cells.pos[cell * 3 + 1], rig.cells.pos[cell * 3 + 2]])[0]
                          : transformPoint(elementMatrix(el), f.local)[0];
      if (Math.sign(x) !== Math.sign(where.side)) return false;
    }
    return true;
  });
}
// Rank of each value among clusters of near-equal values (a gap over tol starts the next cluster): 0, 1, 2, ...
export function clusterRank(values, tol) {
  const idx = Array.from(values, (_, i) => i).sort((a, b) => values[a] - values[b]);
  const out = new Float64Array(values.length);
  let rank = 0;
  for (let k = 0; k < idx.length; k++) {
    if (k > 0 && values[idx[k]] - values[idx[k - 1]] > tol) rank++;
    out[idx[k]] = rank;
  }
  return out;
}
export const COLUMN_TOL_M = 2.0, DEPTH_TOL_M = 4.0;

export function buildGroup(rig, name, def, groups = rig.groups) {
  const entries = groupEntries(rig, def, groups || {});
  const f0 = entries.length ? rig.fixtures[entries[0].fi] : null;
  const type = f0 ? rig.types[f0.type] : null;
  const kind = !type ? "empty" : type.class === "head" ? "heads" : type.class === "pixel" ? "cells" : "fixtures";
  const members = [];
  const memberFixture = [];
  const world = [];
  const keys = { index: [], x: [], y: [], z: [], helix: [], side: [], along: [], angle: [], element: [], radius: [], azimuth: [],
                 clock: [], level: [], level_mirror: [], column: [], depth: [] };
  const mats = new Map();
  const matOf = (e) => { if (!mats.has(e)) mats.set(e, elementMatrix(rig.elements[e])); return mats.get(e); };
  for (const { fi, cell } of entries) {
    const f = rig.fixtures[fi];
    const el = rig.elements[f.element];
    memberFixture.push(fi);
    if (kind === "cells") {
      const c = cell;
      const lp = [rig.cells.pos[c * 3], rig.cells.pos[c * 3 + 1], rig.cells.pos[c * 3 + 2]];
      members.push(c);
      world.push(transformPoint(matOf(f.element), lp));
      keys.along.push(rig.cells.along[c]);
      keys.angle.push(rig.cells.angle[c]);
      keys.side.push(Math.sign(lp[0]) || 0);
      keys.element.push(el.index);
    } else {
      members.push(kind === "heads" ? f.head : fi);
      world.push(transformPoint(matOf(f.element), f.local));
      keys.along.push(0);
      keys.angle.push(f.angle ?? Math.atan2(f.local[1], f.local[0]));
      keys.side.push(Math.sign(f.local[0]) || 0);
      keys.element.push(el.index);
    }
    const clk = memberClock(rig, f, kind === "cells" ? cell : -1);
    const lv = memberLevel(rig, f, kind === "cells" ? cell : -1);
    keys.clock.push(clk === null ? 0 : ((clk % 360) + 360) % 360);
    keys.level.push(Math.max(0, lv));
    keys.level_mirror.push(lv === 1 ? 1 : 0);
  }
  const n = members.length;
  let cx = 0, cy = 0, cz = 0;
  for (const p of world) { cx += p[0]; cy += p[1]; cz += p[2]; }
  if (n) { cx /= n; cy /= n; cz /= n; }
  for (let i = 0; i < n; i++) {
    const p = world[i];
    keys.index.push(i); keys.x.push(p[0]); keys.y.push(p[1]); keys.z.push(p[2]);
    // the helix parameter: position along the strand (element index plus the position along the rung), the two sides as
    // two blocks (left side first), so a two-wing spread puts one backbone in each wing
    keys.helix.push((keys.side[i] > 0 ? 1000 : 0) + keys.element[i] + 0.5 * keys.along[i]);
    keys.radius.push(Math.hypot(p[0] - cx, p[1] - cy, p[2] - cz));
    keys.azimuth.push(Math.atan2(p[1] - cy, p[0] - cx));
  }
  // column: 1, 2, 3 outward from the centre by |x| (clusters 2 m apart); depth: by z (clusters 4 m apart), stage first
  keys.column = Array.from(clusterRank(keys.x.map((x) => Math.abs(x)), COLUMN_TOL_M));
  keys.depth = Array.from(clusterRank(keys.z, DEPTH_TOL_M));
  const frozen = {};
  for (const [k, v] of Object.entries(keys)) frozen[k] = Float64Array.from(v);
  const fxList = [...new Set(memberFixture)];
  return { name, select: def.select || null, union: def.union || null, where: def.where || null, kind, type: f0 ? f0.type : null,
           members: Int32Array.from(members), memberFixture: Int32Array.from(memberFixture), fixtures: Int32Array.from(fxList),
           keys: frozen, centre: [cx, cy, cz], n, world };
}

export function countRig(rig) {
  const byType = {};
  for (const f of rig.fixtures) byType[f.type] = (byType[f.type] || 0) + 1;
  const kinds = {};
  for (let i = 0; i < rig.cells.n; i++) kinds[rig.cells.kind[i]] = (kinds[rig.cells.kind[i]] || 0) + 1;
  const cellsOf = (k) => kinds[CELL_KIND[k]] || 0;
  const elementsOf = (id) => rig.elements.filter((e) => e.id === id).length;
  return {
    heads: rig.heads.length, fixtures: rig.fixtures.length, cells: rig.cells.n, by_type: byType,
    rungs: elementsOf("rung"), rings: elementsOf("ring"), cubes: byType["cube-6"] || 0,
    dot_cells: cellsOf("dot"), bar_cells: cellsOf("bar"), cube_cells: cellsOf("cube"), ring_cells: cellsOf("slat") + cellsOf("rim"),
    projectors: rig.projectors.length, hazers: rig.hazers.length,
    hoists: rig.elements.filter((e) => e.axisType === "hoist").reduce((s, e) => s + Math.max(1, e.pickups.length), 0),
  };
}

// The inverse of headPose (world-locked presets): the pan and tilt (degrees) that point a head's beam at a world point,
// from its tilt pivot. Of the two solutions for one direction ((pan, tilt) and (pan + 180, -tilt)) it takes the one whose
// pan is nearest panHint and inside the pan range; a direction beyond the tilt range is clamped to it.
export function aimAt(elemM12, fixture, target, { panHint = 0, panRange = 270, tiltRange = 135, headOffset = 0.32 } = {}) {
  const body = eulerToMat3(fixture.rot);
  const pivotE = mat3MulVec(body, [0, headOffset, 0]);
  const pivot = transformPoint(elemM12, [fixture.local[0] + pivotE[0], fixture.local[1] + pivotE[1], fixture.local[2] + pivotE[2]]);
  let dx = target[0] - pivot[0], dy = target[1] - pivot[1], dz = target[2] - pivot[2];
  const len = Math.hypot(dx, dy, dz) || 1;
  dx /= len; dy /= len; dz /= len;
  const m = elemM12;
  // world -> element (the rotation's transpose), element -> body (the body matrix's transpose)
  const e = [m[0] * dx + m[3] * dy + m[6] * dz, m[1] * dx + m[4] * dy + m[7] * dz, m[2] * dx + m[5] * dy + m[8] * dz];
  const b = [body[0] * e[0] + body[3] * e[1] + body[6] * e[2], body[1] * e[0] + body[4] * e[1] + body[7] * e[2],
             body[2] * e[0] + body[5] * e[1] + body[8] * e[2]];
  let tilt = Math.acos(Math.max(-1, Math.min(1, b[1]))) / DEG;
  let pan = Math.atan2(b[0], b[2]) / DEG;
  if (tilt < 1e-6) pan = panHint;                       // straight along the body axis: any pan works, keep the hint
  const cands = [];
  for (const [p0, t0] of [[pan, tilt], [pan + 180, -tilt]]) for (const k of [-360, 0, 360]) {
    const p = p0 + k;
    if (Math.abs(p) <= panRange + 1e-9) cands.push([p, t0]);
  }
  cands.sort((a, c) => Math.abs(a[0] - panHint) - Math.abs(c[0] - panHint));
  [pan, tilt] = cands[0] || [pan, tilt];
  const clamped = Math.abs(tilt) > tiltRange;
  if (clamped) tilt = Math.sign(tilt) * tiltRange;
  return { pan, tilt, clamped };
}

// The beam direction and the lens position of a moving head in world space, given its element's matrix and its pan and
// tilt (degrees). The geometry tree is Body > Yoke (Pan, about the body's +y) > Head (Tilt, about the yoke's +x) > Beam
// (the head's +y). An upright fixture at pan 0 / tilt 0 points straight up; one hung with rot [180, 0, 0] points down.
// headOffset is the tilt pivot above the base; lensOffset the lens beyond the pivot along the beam.
export function headPose(elemM12, fixture, pan, tilt, out, { headOffset = 0.32, lensOffset = 0.16 } = {}) {
  const body = eulerToMat3(fixture.rot);
  const pa = pan * DEG, ti = tilt * DEG;
  const cp = Math.cos(pa), sp = Math.sin(pa), ct = Math.cos(ti), st = Math.sin(ti);
  // Ry(pan) * Rx(tilt) * (0, 1, 0) = Ry(pan) * (0, ct, st) = (st*sp, ct, st*cp)
  const dirB = [st * sp, ct, st * cp];
  const lensB = [dirB[0] * lensOffset, headOffset + dirB[1] * lensOffset, dirB[2] * lensOffset];
  const dirE = mat3MulVec(body, dirB);
  const lensE = mat3MulVec(body, lensB);
  const local = [fixture.local[0] + lensE[0], fixture.local[1] + lensE[1], fixture.local[2] + lensE[2]];
  transformPoint(elemM12, local, out.lens);
  const m = elemM12;
  const dx = m[0] * dirE[0] + m[1] * dirE[1] + m[2] * dirE[2];
  const dy = m[3] * dirE[0] + m[4] * dirE[1] + m[5] * dirE[2];
  const dz = m[6] * dirE[0] + m[7] * dirE[1] + m[8] * dirE[2];
  const len = Math.hypot(dx, dy, dz) || 1;
  out.dir[0] = dx / len; out.dir[1] = dy / len; out.dir[2] = dz / len;
  return out;
}
