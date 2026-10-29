// Stage stills (2026-10-29): candidate camera shots tried without editing the set. Daniel: "also can we add some more full
// set spectacle camera positions, i think a lot of ours are close and we dont have many good zoom out ones so i can
// appreciate the crazy ring effects and full set magic". The still-render lane (arsenal/lanes/stage_stills.mjs) renders
// shots at chosen bars on the GPU; this module is the page's side of it, kept apart from camera.js so the camera's own
// branches merge cleanly.
//
//   window.__extraShots = { ID: {kind, pos, look, ...} }   set before the page boots (the lane injects it): each shot is
//                                                            checked here, merged over the set's shots (an existing id is
//                                                            replaced, so a designer can retune one), and prepared by the
//                                                            Director with camera.js prepareShot like every other shot
//   ?shot=ID                                                 forces that shot by hand, as C does (played over its bars,
//                                                            looping); ?shot_u=0.5 holds it still at that point instead
import { prepareShot, shotPose } from "./camera.js";

export const SHOT_KINDS = Object.freeze(["static", "path", "orbit", "strand"]);
const ID_RE = /^[A-Za-z0-9_-]{1,48}$/;
const isVec = (v) => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite);
const isPath = (p) => Array.isArray(p) && p.length >= 2 && p.every(isVec);
// a shot's kind, as written or as its fields say (camera.js shotPose reads an orbit or a strand only by its kind)
export const kindOf = (def) => def.kind || (def.pos_path ? "path" : def.orbit ? "orbit" : def.strand ? "strand" : "static");

// What is wrong with one shot definition ([] when it can be dealt): the fields its kind needs, then prepareShot and the
// pose along it (u 0..1) must give finite numbers and a sane lens.
export function shotProblems(id, def) {
  const out = [];
  if (!ID_RE.test(String(id))) out.push(`${id}: a shot id is 1-48 letters, digits, _ or -`);
  if (!def || typeof def !== "object" || Array.isArray(def)) return [...out, `${id}: not an object`];
  const kind = kindOf(def);
  if (!SHOT_KINDS.includes(kind)) out.push(`${id}: kind ${def.kind} is not one of ${SHOT_KINDS.join(", ")}`);
  if (kind === "static" && !(isVec(def.pos) && isVec(def.look))) out.push(`${id}: a static shot needs pos and look ([x, y, z])`);
  if (kind === "path" && !(isPath(def.pos_path) && (isVec(def.look) || isPath(def.look_path)))) out.push(`${id}: a path shot needs pos_path (2+ points) and look or look_path`);
  if (kind === "orbit") {
    const o = def.orbit || {};
    if (!(isVec(o.centre) && [o.radius, o.height, o.from_deg, o.to_deg].every(Number.isFinite))) out.push(`${id}: an orbit needs orbit {centre, radius, height, from_deg, to_deg}`);
  }
  if (kind === "strand" && !(def.strand && Array.isArray(def.strand.s) && def.strand.s.length === 2 && def.strand.s.every(Number.isFinite))) out.push(`${id}: a strand shot needs strand.s [from, to]`);
  const h = def.hfov ?? 50;
  if (!((Number.isFinite(h) && h > 5 && h < 150) || (Array.isArray(h) && h.length === 2 && h.every((x) => Number.isFinite(x) && x > 5 && x < 150)))) out.push(`${id}: hfov is a number or [from, to] between 5 and 150 degrees`);
  if (def.bars !== undefined && !(Number.isFinite(def.bars) && def.bars > 0)) out.push(`${id}: bars is a positive number`);
  if (out.length) return out;
  try {
    const s = prepareShot({ id, ...def, kind });
    for (const u of [0, 0.25, 0.5, 0.75, 1]) {
      const p = shotPose(s, u, 0);
      if (![...p.pos, ...p.look, p.hfov, p.roll].every(Number.isFinite)) { out.push(`${id}: the pose at u ${u} is not finite`); break; }
      if (Math.hypot(p.look[0] - p.pos[0], p.look[1] - p.pos[1], p.look[2] - p.pos[2]) < 1e-3) { out.push(`${id}: at u ${u} the lens looks at itself (pos = look)`); break; }
    }
  } catch (e) { out.push(`${id}: ${e.message}`); }
  return out;
}

// The set's shots with the extra ones over them: {shots, added, replaced, problems}. A shot with problems is left out.
export function withExtraShots(shots, extra) {
  const res = { shots: { ...shots }, added: [], replaced: [], problems: [] };
  if (!extra || typeof extra !== "object") return res;
  for (const [id, def] of Object.entries(extra)) {
    if (id.startsWith("_")) continue;
    const p = shotProblems(id, def);
    if (p.length) { res.problems.push(...p); continue; }
    (shots[id] ? res.replaced : res.added).push(id);
    res.shots[id] = { ...def, kind: kindOf(def) };
  }
  return res;
}

// ?shot=ID (and ?shot_u=): the shot to force by hand, or null
export function askedShot(qs, shots) {
  const id = qs.get("shot");
  if (!id || !shots[id]) return null;
  const u = qs.get("shot_u");
  return u !== null && Number.isFinite(Number(u)) ? { id, u: Math.max(0, Math.min(1, Number(u))) } : { id, u: null };
}
