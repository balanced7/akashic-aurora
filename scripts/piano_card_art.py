"""Card art for the piano Studio's instrument cards: a wireframe and a rendered preview of every instrument.

WHAT IT MAKES. For each id in arsenal/web/piano/instruments/catalog.js it writes two files to
arsenal/web/assets/instrument-art/:

  <id>.wire.webp      496x220 lossless WebP, white on alpha: a hidden-line technical drawing of the instrument's real 3D
                      model. The card paints it as a CSS mask over var(--card-accent), so every card tints itself.
  <id>.preview.webp   496x220 lossy WebP with alpha: the instrument as it actually renders (materials, light, the struck
                      chord), cut out of its stage. Meant to crossfade in on hover, focus and on the selected card.

496x220 is 2x the 248x110 art box of a card in the default 294 px inspector. Both kinds of one id are rendered through
ONE camera object (yaw / elevation / lens from CAMERAS below, then a crop fitted to the drawing), so the preview sits
exactly under its wireframe and the two can be layered.

HOW. Headless Brave on SwiftShader (one browser for the run, one page at a time), driven by Playwright:
  * every id but "page": the instruments lab, /web/piano-lab-instruments.html?id=<id>&view=hero&demo=0, posed by
    __lab.snapshot (D-flat 6/9 struck, pedal down, the frame taken 0.6 s later), so lids, hammers and lights are posed
    as they are when played;
  * "page" (the built-in keys, which have no module the lab can mount): RENDERED FROM /piano ITSELF, with the Page keys
    instrument (the default), the same chord sent through window.__piano.midiMessage and the page clock held. Only the
    page's own instrument is drawn: its 88 keys and the lacquer body (keybed, end cheeks, back rail, felt, rail light);
    the scheme's trails and everything else on that page are left out.
  The in-page script (CARD_JS below) reaches the module-local scene through a copy of the page module served by a
  Playwright route with ONE added line that exposes it (lab: __lab._rig; /piano: window.__pianoRig). Nothing in the
  repository is edited by a run.
  Wireframe: edges come from the live geometry -- creases (> 32 degrees between faces), silhouette edges (a face toward
  the camera meeting one facing away, so turned legs and rims trace), open boundaries -- per instance for
  InstancedMesh; every solid part is drawn depth-only and the edges are fat lines depth-tested against it, so hidden
  lines are removed. 3x supersampled, box-downsampled, plus a thin outer silhouette stroke and a faint body fill.
  The shader-driven light sculptures cannot be read from their geometry (their shapes live in vertex shaders), so they
  get a PROXY built from the module's own live attributes and uniforms: the Aurora Harp's 88 bands from aOffsetX /
  aHalfW / aLevel (soft ribbons, the struck ones bright, the emitter rail the lenses dive from), Abyssal's seven bells
  and 88 tentacles by replaying its bell and tentacle vertex maths on the CPU from uBellPos / uBellAnim / aAnchor /
  aTip, and the Orrery's visible motes as dots from its CPU-side particle buffer.
  Preview: the same camera on the page's own renderer and composer (its tone mapping and bloom), floor and fog off,
  rendered over black and over grey; the difference gives a true alpha matte, so glass, glow and bloom survive.

RUN (needs the piano server on http://127.0.0.1:8793 -- the page and the lab are served from there):
  py scripts/piano_card_art.py all                       every instrument, both kinds (about 2 to 4 minutes)
  py scripts/piano_card_art.py glass-piano               one id;  a comma list works too: aether,solstice
  py scripts/piano_card_art.py all --kinds wire          only the wireframes (or --kinds preview)
  py scripts/piano_card_art.py page --work DIR           also keep receipts in DIR: report.json, the lab's hero frame
                                                         per id (hero_<id>.jpg) and the raw renders
  options: --out DIR (default arsenal/web/assets/instrument-art)
Re-run an id whenever its module's look changes; output is deterministic for a given module and lab.
Every asset is checked to be under 40 KB and is written by Pillow with no EXIF/XMP chunks.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "arsenal" / "web" / "assets" / "instrument-art"
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BASE = "http://127.0.0.1:8793"
ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
OUT_W, OUT_H = 496, 220          # 2x the 248x110 art box
SS = 3                           # wireframe supersampling
PSS = 2                          # preview supersampling
GREY = 0.25                      # linear grey of the second matte pass (under the bloom threshold)
MAX_BYTES = 40 * 1024
CHORD = [49, 56, 65, 70, 75]     # the lab's D-flat 6/9 (piano-lab-instruments.js CHORDS), struck on /piano for "page"

ALL = ["page", "keylab88mk3", "concert-grand", "upright", "suitcase-ep", "vintage-synth", "glass-piano", "aether",
       "solstice", "nocturne", "light-kimi-aurora", "light-deepseek-orrery", "light-vandor-ornithopter",
       "light-vandor-abyssal"]

# ---------------------------------------------------------------------------------------------- the camera table --
# ONE table for both kinds. yaw: degrees round the instrument from the front (+ = from the treble/right side), elev:
# degrees above it, fov: lens. The crop is then fitted to the drawing: at most 88 % of the box wide, its lowest line on
# a shared baseline 7.3 % (8 CSS px) above the box bottom, so the list has one ground line.
CAMERAS = {
    "*":                        {"yaw": 66, "elev": 13, "fov": 20},     # the five grands share this exactly
    "page":                     {"yaw": 10, "elev": 34, "fov": 20},     # the player's side, nearly square on
    "keylab88mk3":              {"yaw": 34, "elev": 20, "fov": 20},
    "light-kimi-aurora":        {"yaw": -16, "elev": 8, "fov": 20},
    "light-deepseek-orrery":    {"yaw": -36, "elev": 16, "fov": 20},   # the bass side, as the lab hero
    "light-vandor-abyssal":     {"yaw": -26, "elev": 7, "fov": 20},
}

# Line weights in OUTPUT pixels (2.0 = one CSS pixel at 1x) and opacity, per role and edge class. The weight hierarchy
# (case outline heaviest, creases, keys, small parts and strings faint) is what makes the drawings read at 1x.
STYLES = {
    "*": {"w": 1.2, "a": 0.6},
    "body": {"contour": {"w": 2.1, "a": 1.0}, "crease": {"w": 1.45, "a": 0.82}, "boundary": {"w": 1.45, "a": 0.82}},
    "plate": {"contour": {"w": 1.6, "a": 0.95}, "crease": {"w": 1.3, "a": 0.9}, "boundary": {"w": 1.3, "a": 0.9}},
    "keys": {"contour": {"w": 1.15, "a": 0.62}, "crease": {"w": 1.0, "a": 0.5}, "boundary": {"w": 1.0, "a": 0.5}},
    "detail": {"*": {"w": 0.95, "a": 0.34}},
    "rail": {"*": {"w": 1.3, "a": 0.85}},
    "light": {"*": {"w": 1.0, "a": 0.55}, "strand": {"w": 0.9, "a": 0.4}, "lit": {"w": 1.7, "a": 1.0},
              "rail": {"w": 1.0, "a": 0.32}, "arm": {"w": 0.8, "a": 0.3}, "braid": {"w": 1.2, "a": 0.75}},
}

DEFAULT = {"after": 0.6, "vel": 110, "crease": 32, "marginX": 0.06, "marginTop": 0.05, "marginBottom": 0.073,
           "outline": 0.9, "fill": 0.07, "fitRoles": ["body", "plate", "keys", "detail", "light"], "exposure": 1.0}

PRESETS = {
    "page": {"source": "page", "fill": 0.05},
    "concert-grand": {"exposure": 1.45},
    # the crystal grand reads see-through: hidden lines show at 0.35 (case) and 0.22 (action, strings), and the gold
    # plate is its own, brighter role, so it is told from the concert grand by more than its colour
    "glass-piano": {"xray": {"body": 0.35, "plate": 0.6, "detail": 0.22}, "plate": True, "exposure": 1.4},
    "light-deepseek-orrery": {
        "additive": True, "lightInFit": True, "centerline": True, "litAttr": "aGlow", "fill": 0.05,
        # the unlit curtain dim and fading hard as it rises, the five struck strands bright, the motes as dots
        "fade": {"light": {"k": 10, "strand": 0.0, "lit": 0.45, "pow": 0.55}},
        "styles": {"rail": {"*": {"w": 1.0, "a": 0.0}}, "light": {"boundary": {"w": 1, "a": 0},
                                                                 "strand": {"w": 0.8, "a": 0.2},
                                                                 "lit": {"w": 2.3, "a": 1.0}}},
        "dots": {"min": 0.04, "px": [2.2, 3.8], "a": [0.22, 0.75]}},
    "light-kimi-aurora": {
        "proxy": "aurora", "lightProxy": True, "lightInFit": True, "fill": 0.05,
        # the emitter rail is the module's RAIL_Y (light-kimi-aurora.js), where the spectral hammers dive from
        # every band a soft ribbon as wide as the module makes it (broad in the bass, fine in the treble), widened so
        # it reads at card size; the unstruck ones a faint curtain, the struck ones bright with a hot core line
        "aurora": {"railY": 16.5, "ghostSoft": 0.14, "ghostWiden": 2.4, "ghostTop": 0.2, "ghostStrand": 0.0,
                   "litSoft": 0.8, "litWiden": 3.4, "litTop": 0.4},
        "styles": {"light": {"lit": {"w": 2.6, "a": 1.0}}},
        "fade": {"light": {"k": 10, "lit": 0.35, "strand": 0.1, "pow": 0.8}}},
    "light-vandor-abyssal": {
        "proxy": "abyssal", "lightProxy": True, "lightInFit": True, "fill": 0.05,
        "styles": {"body": {"contour": {"w": 1.9, "a": 0.95}, "crease": {"w": 1.0, "a": 0.45},
                            "boundary": {"w": 1.5, "a": 0.85}},
                   "light": {"strand": {"w": 0.75, "a": 0.26}, "lit": {"w": 1.9, "a": 1.0}, "arm": {"w": 0.85, "a": 0.32}}},
        "beads": {"px": [2.2, 4.6], "a": [0.35, 1.0]}},
}

# Things that are stage, not instrument, and would print a rectangle into the preview's matte (by object name).
PREVIEW_HIDE = {"light-vandor-abyssal": ["abyssal-water", "abyssal-bed"], "light-vandor-ornithopter": ["pool", "haze"]}


def params_for(iid: str) -> dict:
    p = dict(DEFAULT)
    p.update(CAMERAS["*"])
    p.update(CAMERAS.get(iid, {}))
    p.update(json.loads(json.dumps(PRESETS.get(iid, {}))))
    styles = json.loads(json.dumps(STYLES))
    for role, v in (p.pop("styles", None) or {}).items():
        styles.setdefault(role, {}).update(v)
    for role, xa in (p.pop("xray", None) or {}).items():   # a transparent instrument: hidden lines show, as through glass
        for st in styles.get(role, {}).values():
            st["xray"] = xa
            st["xw"] = min(st["w"], 1.1)
    p.update({"width": OUT_W, "height": OUT_H, "ss": SS, "pss": PSS, "grey": GREY, "styles": styles,
              "previewHide": PREVIEW_HIDE.get(iid, []), "source": p.get("source", "lab")})
    return p


# --------------------------------------------------------------------------------------------- the page script --
CARD_JS = r"""
async (P) => {
  const T0 = performance.now();
  const THREE = await import("three");
  const { LineSegments2 } = await import("three/addons/lines/LineSegments2.js");
  const { LineSegmentsGeometry } = await import("three/addons/lines/LineSegmentsGeometry.js");
  const { LineMaterial } = await import("three/addons/lines/LineMaterial.js");
  const deg = THREE.MathUtils.degToRad;
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const thumb = (src, w, h) => { const c = document.createElement("canvas"); c.width = w; c.height = h;
    c.getContext("2d").drawImage(src, 0, 0, w, h); return c.toDataURL("image/jpeg", 0.86); };

  // ------------------------------------------------------------------ the posed scene
  let scene, group = null, hero = null, allow = null, H;
  const sounding = new Set(P.sounding || []);
  if (P.source === "page") {
    H = window.__pianoRig;
    if (!H) return { error: "the /piano rig is missing (route patch not applied?)" };
    scene = H.scene;
    allow = new Map();   // the page's own instrument: its keys and lacquer body, nothing else on the page
    for (const k of H.keys.values()) k.pivot.traverse((o) => { if (o.isMesh && o.visible) allow.set(o, "keys"); });
    for (const o of H.pageBody) allow.set(o, o.material === H.lacquer ? "body" : "detail");
  } else {
    const L = window.__lab;
    if (!L || !L.ready) return { error: "lab not ready: " + (L && L.error) };
    H = L._rig;
    if (!H) return { error: "the lab rig is missing (route patch not applied?)" };
    await L.snapshot({ view: "hero", after: P.after, pedal: true, vel: P.vel });
    hero = thumb(document.getElementById("lab"), 480, 270);
    group = L.handle().group; scene = group.parent;
    for (const m of L.state.sounding.keys()) sounding.add(m);
    if (P.hideInstrument) group.visible = false;
  }
  scene.updateMatrixWorld(true);

  // ------------------------------------------------------------------ what to draw
  const inGroup = (o) => { for (let p = o; p; p = p.parent) if (p === group) return true; return false; };
  const items = [];   // { obj, occluder, role }
  const pointsObjs = [];
  let floorMesh = null;
  const skipped = [];
  scene.traverseVisible((o) => {
    if (o.isPoints) { if (group && inGroup(o)) pointsObjs.push(o); return; }
    if (!(o.isMesh || o.isLine)) return;
    const m = Array.isArray(o.material) ? o.material[0] : o.material;
    const g = o.geometry;
    if (!g || !g.attributes || !g.attributes.position) return;
    if (g.type === "PlaneGeometry" && g.parameters && g.parameters.width >= 500) { floorMesh = o; return; }   // the stage floor
    let role;
    if (allow) {
      role = allow.get(o);
      if (!role) return;
    } else {
      const host = !inGroup(o);
      if (m && (m.visible === false || (m.opacity !== undefined && m.opacity < 0.03))) { skipped.push("invisible " + g.type); return; }
      if (o.isMesh && g.attributes.position.count < 3) return;
      const additive = m && m.blending === THREE.AdditiveBlending;
      const light = additive || (m && m.depthWrite === false) || (m && m.transparent && !m.isMeshPhysicalMaterial);
      if (!host && light && P.lightProxy) { skipped.push("proxied " + (o.name || g.type)); return; }
      // additive single quads are glow cards (a floor pool, a halo), not structure
      if (additive && (P.additive === false || (!P.additive && g.attributes.position.count <= 4 && !o.isInstancedMesh))) {
        skipped.push("additive " + g.type + " " + g.attributes.position.count); return; }
      role = host ? "keys" : (o.isLine ? "rail" : (light ? "light" : "body"));
      if (!host && o.isInstancedMesh && o.count >= (P.detailInstances ?? 20) && role === "body") role = "detail";
      if (role === "light" && !additive) role = "detail";              // strings: shader ribbons that write no depth
      if (P.plate && !host && m && m.metalness >= 0.5 && m.color) {   // the crystal grand's gold plate
        const hsl = {}; m.color.getHSL(hsl);
        if (hsl.h > 0.07 && hsl.h < 0.17 && hsl.s > 0.3) role = "plate";
      }
    }
    items.push({ obj: o, occluder: !o.isLine && role !== "light" && !(m && m.depthWrite === false), role });
  });

  // ------------------------------------------------------------------ camera
  const box = new THREE.Box3();
  for (const it of items) if (it.role !== "light" || P.lightInFit) box.expandByObject(it.obj);
  const center = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
  const RW = P.width * P.ss, RH = P.height * P.ss;
  const camera = new THREE.PerspectiveCamera(P.fov, RW / RH, 0.1, 5000);
  {
    const yaw = deg(P.yaw), elev = deg(P.elev);
    const dist = size.length() / 2 / Math.sin(deg(camera.fov) / 2) * 1.1;
    camera.position.set(center.x + dist * Math.sin(yaw) * Math.cos(elev), center.y + dist * Math.sin(elev),
      center.z + dist * Math.cos(yaw) * Math.cos(elev));
    camera.lookAt(center);
  }
  camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
  const eye = camera.position.clone();

  // ------------------------------------------------------------------ edges
  const buckets = {};   // role -> class -> number[] (segment endpoints, world space)
  const floorY = floorMesh ? floorMesh.matrixWorld.elements[13] : null;
  const raw = (role, cls, ax, ay, az, bx, by, bz) => {
    const r = buckets[role] || (buckets[role] = {}); const a = r[cls] || (r[cls] = []); a.push(ax, ay, az, bx, by, bz);
  };
  const push = (role, cls, ax, ay, az, bx, by, bz) => {
    if (floorY !== null && (ay < floorY || by < floorY)) {   // clip at the stage floor
      if (ay < floorY && by < floorY) return;
      const t = (floorY - ay) / (by - ay);
      if (ay < floorY) { ax += (bx - ax) * t; az += (bz - az) * t; ay = floorY; } else { bx = ax + (bx - ax) * t; bz = az + (bz - az) * t; by = floorY; }
    }
    const fade = P.fade && P.fade[role];
    if (fade && fade[cls] !== undefined) {   // light that thins out as it rises: K pieces, each a fainter class "cls#k"
      const K = fade.k || 6;
      const up = by >= ay;
      for (let k = 0; k < K; k++) {
        const t0 = k / K, t1 = (k + 1) / K;
        const kk = up ? k : K - 1 - k;
        raw(role, cls + "#" + kk, ax + (bx - ax) * t0, ay + (by - ay) * t0, az + (bz - az) * t0, ax + (bx - ax) * t1, ay + (by - ay) * t1, az + (bz - az) * t1);
      }
      return;
    }
    raw(role, cls, ax, ay, az, bx, by, bz);
  };
  const pushV = (role, cls, a, b) => push(role, cls, a.x, a.y, a.z, b.x, b.y, b.z);
  const pushPolyline = (role, cls, pts) => { for (let i = 0; i + 1 < pts.length; i++) pushV(role, cls, pts[i], pts[i + 1]); };

  const adjCache = new Map();
  function adjacency(g) {
    if (adjCache.has(g.uuid)) return adjCache.get(g.uuid);
    const pos = g.attributes.position, idx = g.index, Q = 1e4;
    const map = new Map(), verts = [], remap = new Int32Array(pos.count);
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const k = Math.round(x * Q) + "," + Math.round(y * Q) + "," + Math.round(z * Q);
      let id = map.get(k);
      if (id === undefined) { id = verts.length / 3; verts.push(x, y, z); map.set(k, id); }
      remap[i] = id;
    }
    const n = idx ? idx.count : pos.count, tris = [];
    const start = g.drawRange ? g.drawRange.start : 0, end = Math.min(n, g.drawRange && isFinite(g.drawRange.count) ? start + g.drawRange.count : n);
    for (let t = start; t + 2 < end; t += 3) {
      const a = remap[idx ? idx.getX(t) : t], b = remap[idx ? idx.getX(t + 1) : t + 1], c = remap[idx ? idx.getX(t + 2) : t + 2];
      if (a === b || b === c || a === c) continue;
      tris.push(a, b, c);
    }
    const nv = verts.length / 3, edges = new Map(), E = [];
    for (let f = 0; f < tris.length / 3; f++) for (let k = 0; k < 3; k++) {
      const u = tris[f * 3 + k], v = tris[f * 3 + (k + 1) % 3], lo = Math.min(u, v), hi = Math.max(u, v), key = lo * nv + hi;
      const e = edges.get(key);
      if (e === undefined) { edges.set(key, E.length / 4); E.push(lo, hi, f, -1); }
      else if (E[e * 4 + 3] === -1) E[e * 4 + 3] = f;
      else E[e * 4 + 3] = -2;                                                        // non-manifold: always draw
    }
    const out = { verts: new Float32Array(verts), tris: new Int32Array(tris), E: new Int32Array(E) };
    adjCache.set(g.uuid, out);
    return out;
  }
  const thrCos = Math.cos(deg(P.crease));
  function emit(adj, M, role) {
    const v = adj.verts, nv = v.length / 3, e = M.elements, W = new Float32Array(v.length);
    for (let i = 0; i < nv; i++) {
      const x = v[i * 3], y = v[i * 3 + 1], z = v[i * 3 + 2];
      W[i * 3] = e[0] * x + e[4] * y + e[8] * z + e[12];
      W[i * 3 + 1] = e[1] * x + e[5] * y + e[9] * z + e[13];
      W[i * 3 + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
    }
    const tr = adj.tris, nt = tr.length / 3, N = new Float32Array(nt * 3), F = new Int8Array(nt);
    for (let t = 0; t < nt; t++) {
      const a = tr[t * 3] * 3, b = tr[t * 3 + 1] * 3, c = tr[t * 3 + 2] * 3;
      const ux = W[b] - W[a], uy = W[b + 1] - W[a + 1], uz = W[b + 2] - W[a + 2];
      const vx = W[c] - W[a], vy = W[c + 1] - W[a + 1], vz = W[c + 2] - W[a + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const len = Math.hypot(nx, ny, nz);
      if (len < 1e-12) { F[t] = 0; continue; }
      nx /= len; ny /= len; nz /= len;
      N[t * 3] = nx; N[t * 3 + 1] = ny; N[t * 3 + 2] = nz;
      const cx = (W[a] + W[b] + W[c]) / 3, cy = (W[a + 1] + W[b + 1] + W[c + 1]) / 3, cz = (W[a + 2] + W[b + 2] + W[c + 2]) / 3;
      F[t] = nx * (eye.x - cx) + ny * (eye.y - cy) + nz * (eye.z - cz) > 0 ? 1 : -1;
    }
    const E = adj.E;
    for (let k = 0; k < E.length; k += 4) {
      const a = E[k] * 3, b = E[k + 1] * 3, f0 = E[k + 2], f1 = E[k + 3];
      let cls = null;
      if (f1 === -1) cls = "boundary";
      else if (f1 === -2) cls = "crease";
      else if (F[f0] === 0 || F[f1] === 0) cls = null;
      else if (F[f0] !== F[f1]) cls = "contour";
      else if (N[f0 * 3] * N[f1 * 3] + N[f0 * 3 + 1] * N[f1 * 3 + 1] + N[f0 * 3 + 2] * N[f1 * 3 + 2] < thrCos) cls = "crease";
      if (cls) push(role, cls, W[a], W[a + 1], W[a + 2], W[b], W[b + 1], W[b + 2]);
    }
  }

  // ------------------------------------------------------------------ proxies for the shader-driven light sculptures
  const softs = [];   // { pos: number[], alpha: number[], index: number[] } world space, drawn as soft white fills
  const dots = [];    // [x, y, z, px, a]
  const proxyMeshes = [];
  const V = (x, y, z, M) => new THREE.Vector3(x, y, z).applyMatrix4(M);
  // a ribbon of light: centre column at alpha `core`, edges at 0, fading to `top` x core as it rises
  function softRibbon(M, x, w, y0, y1, z, core, top, rows = 10) {
    const pos = [], alpha = [], index = [];
    for (let r = 0; r <= rows; r++) {
      const t = r / rows, y = y0 + (y1 - y0) * t, a = core * (1 - (1 - top) * Math.pow(t, 0.8));
      for (const [dx, k] of [[-w / 2, 0], [0, 1], [w / 2, 0]]) { const p = V(x + dx, y, z, M); pos.push(p.x, p.y, p.z); alpha.push(a * k); }
      if (r < rows) { const b = r * 3; index.push(b, b + 1, b + 3, b + 1, b + 4, b + 3, b + 1, b + 2, b + 4, b + 2, b + 5, b + 4); }
    }
    softs.push({ pos, alpha, index });
  }
  let proxyInfo = null;
  if (P.proxy === "aurora") {
    let bands = null, braid = null;
    group.traverse((o) => {
      if (o.isInstancedMesh && o.geometry.attributes.aOffsetX) bands = o;
      if (o.isLine && o.visible && o.material && o.material.vertexColors) braid = o;
    });
    if (!bands) return { error: "aurora: band mesh not found" };
    const A = bands.geometry.attributes, M = bands.matrixWorld, cfg = P.aurora;
    if (!bands.geometry.boundingBox) bands.geometry.computeBoundingBox();
    const y0 = bands.geometry.boundingBox.min.y, y1 = bands.geometry.boundingBox.max.y;
    let xmin = Infinity, xmax = -Infinity, nlit = 0;
    for (let i = 0; i < bands.count; i++) {
      const x = A.aOffsetX.getX(i), w = A.aHalfW.getX(i), lvl = A.aLevel.getX(i) + A.aFlash.getX(i);
      xmin = Math.min(xmin, x); xmax = Math.max(xmax, x);
      if (lvl > 0.15) {
        nlit++;
        softRibbon(M, x, w * cfg.litWiden, y0, y1, 0, cfg.litSoft * clamp01(lvl), cfg.litTop);
        pushV("light", "lit", V(x, y0, 0, M), V(x, y1, 0, M));
      } else {
        if (cfg.ghostSoft > 0) softRibbon(M, x, w * cfg.ghostWiden, y0, y1, 0, cfg.ghostSoft, cfg.ghostTop);
        if (cfg.ghostStrand > 0) pushV("light", "strand", V(x, y0, 0, M), V(x, y1, 0, M));
      }
    }
    if (cfg.railY) pushV("light", "rail", V(xmin - 0.5, cfg.railY, 0, M), V(xmax + 0.5, cfg.railY, 0, M));
    if (braid) {
      const p = braid.geometry.attributes.position, pts = [];
      for (let i = 0; i < p.count; i++) pts.push(V(p.getX(i), p.getY(i), p.getZ(i), braid.matrixWorld));
      pushPolyline("light", "braid", pts);
    }
    proxyInfo = { bands: bands.count, lit: nlit, braid: !!braid };
  }
  if (P.proxy === "abyssal") {
    let tent = null, bellsM = null, beads = null;
    group.traverse((o) => {
      if (o.name === "abyssal-tentacles") tent = o; if (o.name === "abyssal-bells") bellsM = o; if (o.name === "abyssal-beads") beads = o; });
    if (!tent || !bellsM) return { error: "abyssal: tentacle or bell mesh not found" };
    const U = tent.material.uniforms, time = U.uTime.value, BP = U.uBellPos.value, BA = U.uBellAnim.value;
    const mPump = /contract = 1\.0 - \(([\d.]+) \* ba\.x/.exec(tent.material.vertexShader);
    const PUMP = mPump ? parseFloat(mPump[1]) : 0.14;
    const contractOf = (ba) => 1 - (PUMP * ba.x + ba.y) * 0.87 + 0.05 * ba.w;
    const bez = (a, b, c, d, t) => { const u = 1 - t; return a.clone().multiplyScalar(u * u * u).addScaledVector(b, 3 * u * u * t).addScaledVector(c, 3 * u * t * t).addScaledVector(d, t * t * t); };
    const TG = tent.geometry.attributes, Mt = tent.matrixWorld, S = 22;
    const nTent = TG.aInfo.count;
    let lit = 0, arms = 0;
    for (let j = 0; j < nTent; j++) {
      const kind = TG.aInfo.getZ(j), bi = Math.round(TG.aInfo.getY(j)), ph = TG.aInfo.getW(j);
      const bp = BP[bi], ba = BA[bi], c = contractOf(ba);
      const an = new THREE.Vector3(TG.aAnchor.getX(j), TG.aAnchor.getY(j), TG.aAnchor.getZ(j));
      const tp = new THREE.Vector3(TG.aTip.getX(j), TG.aTip.getY(j), TG.aTip.getZ(j));
      const p0 = new THREE.Vector3(bp.x + an.x * bp.w * c, bp.y + an.y * bp.w, bp.z + an.z * bp.w * c);
      let p1, p2, p3, cls;
      if (kind < 0.5) {            // a tentacle: bell rim to the bead behind its key
        const ni = Math.round(TG.aInfo.getX(j));
        p3 = tp; const L = p0.y - p3.y;
        p1 = p0.clone().add(new THREE.Vector3(an.x * bp.w * 0.22, -0.32 * L, an.z * bp.w * 0.3));
        p2 = p3.clone().add(new THREE.Vector3(0, 0.4 * L, -0.35));
        cls = sounding.has(21 + ni) ? "lit" : "strand";
        if (cls === "lit") lit++;
        const reg = TG.aShape.getW(j), sway = TG.aShape.getY(j), pts = [];
        for (let s = 0; s <= S; s++) {
          const t = s / S, q = bez(p0, p1, p2, p3, t), bow = 4 * t * (1 - t);
          q.x += sway * bow * Math.sin(time * (0.37 + 0.35 * reg) + t * 2.4 + ph);
          q.z += sway * bow * 0.7 * Math.sin(time * (0.29 + 0.3 * reg) + t * 2.0 + ph * 1.7);
          pts.push(q.applyMatrix4(Mt));
        }
        pushPolyline("light", cls, pts);
      } else if (kind < 1.5) {     // an oral arm, hanging inside its bell
        p3 = p0.clone().addScaledVector(tp, 1 + 0.1 * ba.x);
        p1 = p0.clone().add(new THREE.Vector3(tp.x * 0.1, tp.y * 0.35, tp.z * 0.1));
        p2 = p0.clone().add(new THREE.Vector3(tp.x * 0.8, tp.y * 0.7, tp.z * 0.8));
        const pts = [];
        for (let s = 0; s <= S; s++) pts.push(bez(p0, p1, p2, p3, s / S).applyMatrix4(Mt));
        pushPolyline("light", "arm", pts); arms++;
      }
    }
    // the bells: the module's revolved profile, put through its bell vertex maths, as solid (occluding) proxies
    const BG = bellsM.geometry, pos = BG.attributes.position, shape = BG.attributes.aBellShape;
    const sstep = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
    for (let b = 0; b < shape.count; b++) {
      const bp = BP[b], ba = BA[b], hf = shape.getX(b), flare = shape.getY(b);
      const arr = new Float32Array(pos.count * 3);
      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        const rho = Math.hypot(x, z), phi = Math.atan2(z, x);
        const squeeze = ba.x * PUMP + ba.y;
        let c = 1 - squeeze * (0.3 + 0.7 * rho * rho) + 0.055 * ba.w * rho;
        c *= (1 + flare * sstep(0.7, 1, rho)) * (1 + 0.2 * ba.z);
        const lapp = 0.028 * Math.sin(phi * 12 + b) * sstep(0.55, 1, rho) + 0.062 * Math.sin(phi * 3 + b * 1.7) * rho * rho;
        const swim = 0.011 * Math.sin(rho * 3 - time * 0.7 + b * 2.1);
        const py = y * hf * (1 + 0.13 * ba.x + 0.8 * ba.y + 0.1 * ba.z) + lapp + swim - 0.05 * ba.w * rho * rho;
        arr[i * 3] = bp.x + x * c * bp.w; arr[i * 3 + 1] = bp.y + py * bp.w; arr[i * 3 + 2] = bp.z + z * c * bp.w;
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
      g.setIndex(BG.index);
      const mesh = new THREE.Mesh(g);
      mesh.matrixAutoUpdate = false; mesh.matrixWorld.copy(bellsM.matrixWorld);
      items.push({ obj: mesh, occluder: true, role: "body" }); proxyMeshes.push(mesh);
    }
    if (beads && P.beads) {         // the photophore beads behind the keys
      const ti = beads.geometry.attributes.aTipInfo;
      for (let i = 0; i < ti.count; i++) {
        const on = sounding.has(21 + Math.round(ti.getW(i)));
        const q = V(ti.getX(i), ti.getY(i), ti.getZ(i), beads.matrixWorld);
        dots.push([q.x, q.y, q.z, on ? P.beads.px[1] : P.beads.px[0], on ? P.beads.a[1] : P.beads.a[0]]);
      }
    }
    proxyInfo = { tentacles: nTent, lit, arms, bells: shape.count, pump: PUMP };
  }
  if (P.dots) {                     // particles with CPU-side positions (the orrery's motes)
    for (const o of pointsObjs) {
      const g = o.geometry, pa = g.attributes.position, al = g.attributes.aAlpha, sz = g.attributes.aSize;
      if (!pa || !al) continue;
      for (let i = 0; i < pa.count; i++) {
        const a = al.getX(i);
        if (!(a > P.dots.min)) continue;
        const q = V(pa.getX(i), pa.getY(i), pa.getZ(i), o.matrixWorld), s = sz ? clamp01(sz.getX(i) / 2.4) : 0.5;
        dots.push([q.x, q.y, q.z, P.dots.px[0] + (P.dots.px[1] - P.dots.px[0]) * s, P.dots.a[0] + (P.dots.a[1] - P.dots.a[0]) * clamp01(a)]);
      }
    }
  }

  // ------------------------------------------------------------------ edges of every mesh
  const tmpM = new THREE.Matrix4(), tmpI = new THREE.Matrix4();
  let triTotal = 0;
  for (const it of items) {
    const o = it.obj;
    if (o.isLine) {
      const p = o.geometry.attributes.position, step = o.isLineSegments ? 2 : 1, va = new THREE.Vector3(), vb = new THREE.Vector3();
      for (let i = 0; i + 1 < p.count; i += step) {
        va.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld); vb.fromBufferAttribute(p, i + 1).applyMatrix4(o.matrixWorld);
        push(it.role, "line", va.x, va.y, va.z, vb.x, vb.y, vb.z);
      }
      continue;
    }
    if (o.isInstancedMesh && it.role === "light" && P.centerline) {
      // a band of light drawn as the strand it reads as: one line up its middle, lit when its note sounds
      if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
      const bb = o.geometry.boundingBox, c = bb.getCenter(new THREE.Vector3());
      const litA = P.litAttr && o.geometry.attributes[P.litAttr];
      const va = new THREE.Vector3(), vb = new THREE.Vector3();
      for (let i = 0; i < o.count; i++) {
        o.getMatrixAt(i, tmpI); tmpM.multiplyMatrices(o.matrixWorld, tmpI);
        va.set(c.x, bb.min.y, c.z).applyMatrix4(tmpM); vb.set(c.x, bb.max.y, c.z).applyMatrix4(tmpM);
        const on = litA && litA.getX(i) > (P.litMin ?? 0.2);
        push(it.role, on ? "lit" : "strand", va.x, va.y, va.z, vb.x, vb.y, vb.z);
      }
      continue;
    }
    const adj = adjacency(o.geometry);
    if (o.isInstancedMesh) {
      for (let i = 0; i < o.count; i++) {
        o.getMatrixAt(i, tmpI);
        if (Math.abs(tmpI.determinant()) < 1e-12) continue;                   // a hidden (zero-scaled) instance
        tmpM.multiplyMatrices(o.matrixWorld, tmpI);
        emit(adj, tmpM, it.role); triTotal += adj.tris.length / 3;
      }
    } else { emit(adj, o.matrixWorld, it.role); triTotal += adj.tris.length / 3; }
  }

  // ------------------------------------------------------------------ frame the drawing
  // Project every drawn endpoint; crop the camera (setViewOffset) so the drawing is at most (1 - 2 marginX) of the box
  // wide and (1 - marginTop - marginBottom) tall, centred across and standing on the baseline (marginBottom).
  const pr = new THREE.Vector3();
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, zmin = Infinity, zmax = -Infinity;
  const viewDir = new THREE.Vector3(); camera.getWorldDirection(viewDir);
  const fitPoint = (x, y, z) => {
    pr.set(x, y, z);
    const d = pr.clone().sub(eye).dot(viewDir); zmin = Math.min(zmin, d); zmax = Math.max(zmax, d);
    pr.project(camera);
    x0 = Math.min(x0, pr.x); x1 = Math.max(x1, pr.x); y0 = Math.min(y0, pr.y); y1 = Math.max(y1, pr.y);
  };
  for (const role in buckets) {
    if (!P.fitRoles.includes(role)) continue;
    if (role === "light" && !P.lightInFit) continue;
    for (const cls in buckets[role]) { const a = buckets[role][cls]; for (let i = 0; i < a.length; i += 3) fitPoint(a[i], a[i + 1], a[i + 2]); }
  }
  for (const d of dots) { const q = new THREE.Vector3(d[0], d[1], d[2]).sub(eye).dot(viewDir); zmin = Math.min(zmin, q); zmax = Math.max(zmax, q); }
  const mx = P.marginX, mt = P.marginTop, mb = P.marginBottom;
  const bw = (x1 - x0) / 2, bh = (y1 - y0) / 2;                  // the drawing's extent as a fraction of the frame
  const s = Math.max(bw / (1 - 2 * mx), bh / (1 - mt - mb));     // the crop window as a fraction of the frame
  const cropW = RW * s, cropH = RH * s;
  const cxp = ((x0 + x1) / 2 + 1) / 2 * RW, bottom = (1 - y0) / 2 * RH;
  camera.near = Math.max(0.05, zmin * 0.85); camera.far = zmax * 1.15 + 1;
  camera.setViewOffset(RW, RH, cxp - cropW / 2, bottom + mb * cropH - cropH, cropW, cropH);
  camera.updateProjectionMatrix();

  // ------------------------------------------------------------------ draw the wireframe
  const canvas = document.createElement("canvas");
  canvas.width = RW; canvas.height = RH;
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, preserveDrawingBuffer: true, premultipliedAlpha: false });
  renderer.setPixelRatio(1); renderer.setSize(RW, RH, false);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  const out = new THREE.Scene();
  const depthMat = new THREE.MeshBasicMaterial({ colorWrite: false, side: THREE.DoubleSide, polygonOffset: true,
    polygonOffsetFactor: P.offsetFactor ?? 1.5, polygonOffsetUnits: P.offsetUnits ?? 2 });
  let occluders = 0;
  for (const it of items) {
    if (!it.occluder) continue;
    const o = it.obj;
    let m;
    if (o.isInstancedMesh) {
      m = new THREE.InstancedMesh(o.geometry, depthMat, o.count);
      m.instanceMatrix.array.set(o.instanceMatrix.array.subarray(0, o.count * 16));
    } else m = new THREE.Mesh(o.geometry, depthMat);
    m.matrixAutoUpdate = false; m.matrix.copy(o.matrixWorld); m.matrixWorld.copy(o.matrixWorld);
    m.frustumCulled = false; m.renderOrder = -10;
    out.add(m); occluders++;
  }
  if (floorMesh) {   // nothing below the stage floor is seen in the real render
    const f = new THREE.Mesh(floorMesh.geometry, depthMat);
    f.matrixAutoUpdate = false; f.matrix.copy(floorMesh.matrixWorld); f.matrixWorld.copy(floorMesh.matrixWorld); f.renderOrder = -10;
    f.userData.floor = true;
    out.add(f);
  }
  const extras = [];
  for (const sf of softs) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(sf.pos), 3));
    g.setAttribute("aA", new THREE.BufferAttribute(new Float32Array(sf.alpha), 1));
    g.setIndex(sf.index);
    const mat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide,
      vertexShader: "attribute float aA; varying float vA; void main(){ vA=aA; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
      fragmentShader: "varying float vA; void main(){ gl_FragColor=vec4(1.0,1.0,1.0,vA); }" });
    const mesh = new THREE.Mesh(g, mat); mesh.frustumCulled = false; mesh.renderOrder = 50;
    out.add(mesh); extras.push(mesh);
  }
  if (dots.length) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(dots.flatMap((d) => [d[0], d[1], d[2]])), 3));
    g.setAttribute("aSize", new THREE.BufferAttribute(new Float32Array(dots.map((d) => d[3] * P.ss)), 1));
    g.setAttribute("aA", new THREE.BufferAttribute(new Float32Array(dots.map((d) => d[4])), 1));
    const mat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false,
      vertexShader: "attribute float aSize; attribute float aA; varying float vA; void main(){ vA=aA; gl_PointSize=aSize; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
      fragmentShader: "varying float vA; void main(){ vec2 q=gl_PointCoord*2.0-1.0; float d=dot(q,q); if(d>1.0) discard; gl_FragColor=vec4(1.0,1.0,1.0,vA*(1.0-smoothstep(0.35,1.0,d))); }" });
    const pts = new THREE.Points(g, mat); pts.frustumCulled = false; pts.renderOrder = 60;
    out.add(pts); extras.push(pts);
  }
  const styles = P.styles;
  const counts = {};
  let order = 0;
  for (const role in buckets) for (const cls in buckets[role]) {
    const [base, kk] = cls.split("#");
    let st = (styles[role] && (styles[role][base] || styles[role]["*"])) || styles["*"];
    if (kk !== undefined) {
      const f = P.fade[role], K = f.k || 6, lo = f[base] ?? 0.15;
      st = Object.assign({}, st, { a: st.a * (1 - (1 - lo) * Math.pow((+kk + 0.5) / K, f.pow ?? 1)) });
    }
    const a = buckets[role][cls];
    counts[role + "." + cls] = (counts[role + "." + cls] || 0) + a.length / 6;
    if (!st || st.a <= 0) continue;
    const geo = new LineSegmentsGeometry(); geo.setPositions(new Float32Array(a));
    const mat = new LineMaterial({ color: 0xffffff, linewidth: st.w * P.ss, transparent: true, opacity: st.a, depthTest: true,
      depthWrite: false, worldUnits: false });
    mat.resolution.set(RW, RH);
    const line = new LineSegments2(geo, mat); line.frustumCulled = false; line.renderOrder = order++;
    out.add(line);
    if (st.xray) {
      const mat2 = mat.clone(); mat2.opacity = st.xray * (kk !== undefined ? st.a : 1); mat2.depthFunc = THREE.GreaterDepth;
      mat2.linewidth = (st.xw ?? st.w) * P.ss; mat2.resolution.set(RW, RH);
      const ghost = new LineSegments2(geo, mat2); ghost.frustumCulled = false; ghost.renderOrder = 100 + order;
      out.add(ghost);
    }
  }
  renderer.render(out, camera);
  const png = canvas.toDataURL("image/png");
  // the footprint: every occluder (not the floor) drawn solid white, for the outer silhouette stroke and the body fill
  const solid = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
  const keepM = [];
  out.traverse((o) => { if (o.isLineSegments2 || o.isLine || extras.includes(o)) { o.visible = false; return; } if (o.isMesh) keepM.push(o); });
  for (const m of keepM) { if (m.userData.floor) m.visible = false; else m.material = solid; }
  renderer.clear(); renderer.render(out, camera);
  const footprint = canvas.toDataURL("image/png");
  renderer.dispose(); renderer.forceContextLoss();

  // ------------------------------------------------------------------ the rendered preview, through the SAME camera
  let previews = null;
  if (P.preview) {
    const hc = H.camera, hr = H.renderer, comp = H.composer;
    const PW = P.width * P.pss, PH = P.height * P.pss;
    const keep = { pos: hc.position.clone(), q: hc.quaternion.clone(), fov: hc.fov, aspect: hc.aspect, near: hc.near, far: hc.far,
      view: hc.view && hc.view.enabled ? { ...hc.view } : null, size: hr.getSize(new THREE.Vector2()), exp: hr.toneMappingExposure,
      bg: scene.background, fog: scene.fog };
    const hidden = [];
    const hide = (o) => { if (o.visible) { o.visible = false; hidden.push(o); } };
    if (floorMesh) hide(floorMesh);
    scene.traverse((o) => {
      if (P.previewHide.includes(o.name)) hide(o);
      if (allow && (o.isMesh || o.isPoints || o.isLine || o.isSprite) && !allow.has(o) && o !== floorMesh) hide(o);
    });
    hc.position.copy(camera.position); hc.quaternion.copy(camera.quaternion);
    hc.fov = camera.fov; hc.aspect = camera.aspect; hc.near = Math.max(0.05, zmin * 0.5); hc.far = zmax * 3 + 60;
    const v = camera.view;
    hc.setViewOffset(v.fullWidth, v.fullHeight, v.offsetX, v.offsetY, v.width, v.height);
    hc.updateProjectionMatrix(); hc.updateMatrixWorld(true);
    hr.setSize(PW, PH, false); comp.setSize(PW, PH);
    hr.toneMappingExposure = P.exposure;
    scene.fog = null;
    previews = [];
    for (const gv of [0, P.grey]) {
      scene.background = new THREE.Color().setRGB(gv, gv, gv, THREE.LinearSRGBColorSpace);
      comp.render();
      previews.push(hr.domElement.toDataURL("image/png"));
    }
    for (const o of hidden) o.visible = true;
    scene.background = keep.bg; scene.fog = keep.fog;
    hr.toneMappingExposure = keep.exp;
    hc.position.copy(keep.pos); hc.quaternion.copy(keep.q); hc.fov = keep.fov; hc.aspect = keep.aspect; hc.near = keep.near; hc.far = keep.far;
    if (keep.view) hc.setViewOffset(keep.view.fullWidth, keep.view.fullHeight, keep.view.offsetX, keep.view.offsetY, keep.view.width, keep.view.height);
    else hc.clearViewOffset();
    hc.updateProjectionMatrix();
    hr.setSize(keep.size.x, keep.size.y, false); comp.setSize(keep.size.x, keep.size.y);
  }
  for (const m of proxyMeshes) m.geometry.dispose();
  return { png, footprint, previews, hero, ms: Math.round(performance.now() - T0), counts, occluders, items: items.length,
    triTotal, dots: dots.length, softs: softs.length, proxy: proxyInfo, skipped: skipped.slice(0, 24), sounding: [...sounding],
    camera: { pos: eye.toArray().map((x) => +x.toFixed(3)), fov: camera.fov, yaw: P.yaw, elev: P.elev,
              crop: { x: +(camera.view.offsetX / RW).toFixed(4), y: +(camera.view.offsetY / RH).toFixed(4), s: +s.toFixed(4) } },
    box: { center: center.toArray().map((x) => +x.toFixed(2)), size: size.toArray().map((x) => +x.toFixed(2)) } };
}
"""

LAB_RIG = "lab._rig = { THREE, scene, camera, renderer, composer, bloom, floor, state };\n"
PAGE_RIG = ("\nwindow.__pianoRig = { THREE, scene, camera, renderer, composer, bloom, floor, keys, pageBody, lacquer, felt,"
            " railLine };\n")


def patched(url: str, anchor: str | None, inject: str) -> str:
    """The page module with one line added that exposes its module-local scene (served to the headless browser only)."""
    src = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
    if anchor is None:
        return src + inject
    if anchor not in src:
        raise SystemExit(f"{url} changed: anchor {anchor!r} not found -- update LAB_RIG/PAGE_RIG")
    return src.replace(anchor, inject + anchor, 1)


# ---------------------------------------------------------------------------------------------- image side --
def decode(data_url: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1])))


def wire_mask(r: dict, p: dict) -> Image.Image:
    """Lines (alpha) over a thin outer silhouette stroke and a faint body fill, both grown from the footprint, then
    box-downsampled from the supersampled render so every edge is anti-aliased by coverage. White RGB + alpha."""
    from scipy import ndimage
    lines = np.asarray(decode(r["png"]).convert("RGBA").getchannel("A"), dtype=np.float32) / 255
    foot = np.asarray(decode(r["footprint"]).convert("RGBA").getchannel("A"), dtype=np.float32) / 255 > 0.5
    a = lines
    rad = p["outline"] * p["ss"]
    if rad > 0 and foot.any():
        dist = ndimage.distance_transform_edt(~foot)
        ring = np.clip(rad + 0.5 - dist, 0, 1) * (dist > 0)
        a = 1 - (1 - a) * (1 - ring)
    if p["fill"] > 0:
        a = 1 - (1 - a) * (1 - foot * p["fill"])
    big = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))
    small = big.resize((OUT_W, OUT_H), Image.BOX).point(lambda v: round(255 * (v / 255) ** 0.85))
    # alpha is the only channel the card reads: quantised to 64 levels (invisible at one device pixel, half the bytes)
    small = small.point(lambda v: min(255, round(v / 4) * 4 + (3 if v > 250 else 0)))
    white = Image.new("L", small.size, 255)
    return Image.merge("RGBA", (white, white, white, small))


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def preview_image(shots: list[str], feather=0.025) -> Image.Image:
    """Premultiplied colour (the frame over black) and straight alpha (from the black/grey pair), downsampled
    premultiplied so no dark fringes appear, edges feathered a little; RGBA."""
    black, grey = (np.asarray(decode(s).convert("RGB"), dtype=np.float32) / 255 for s in shots)
    lb, lg = srgb_to_lin(black), srgb_to_lin(grey)
    bg = np.maximum(np.median(lg[:4, :4].reshape(-1, 3), axis=0), 1e-3)
    a = 1 - np.clip((lg - lb) / bg, 0, 1).mean(axis=2)          # coverage, in linear light
    a = np.clip(np.maximum(a, black.max(axis=2)), 0, 1)          # additive light (bloom, glow) kept as light
    small = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32)).resize((OUT_W, OUT_H), Image.BOX), dtype=np.float32)
    sa = np.clip(small(a), 0, 1)
    pm = np.minimum(np.stack([np.clip(small(black[..., c]), 0, 1) for c in range(3)], axis=2), sa[..., None])
    sm = lambda x: (lambda y: y * y * (3 - 2 * y))(np.clip(x, 0, 1))
    xs = (np.arange(OUT_W) + 0.5) / OUT_W; ys = (np.arange(OUT_H) + 0.5) / OUT_H
    mask = np.outer(sm(ys / feather) * sm((1 - ys) / feather), sm(xs / feather) * sm((1 - xs) / feather))
    sa, pm = sa * mask, pm * mask[..., None]
    sa[sa < 2 / 255] = 0
    col = np.where(sa[..., None] > 1e-4, pm / np.maximum(sa[..., None], 1e-4), 0)
    rgba = np.concatenate([np.clip(col, 0, 1), sa[..., None]], axis=2)
    return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8))


def save_wire(img: Image.Image, path: Path) -> int:
    img.save(path, "WEBP", lossless=True, quality=100, method=6)
    return path.stat().st_size


def save_preview(img: Image.Image, path: Path) -> int:
    for q, aq in ((74, 72), (66, 64), (56, 56), (46, 48)):   # step down until it fits the budget
        img.save(path, "WEBP", quality=q, alpha_quality=aq, method=6)
        if path.stat().st_size <= MAX_BYTES:
            break
    return path.stat().st_size


# ---------------------------------------------------------------------------------------------- driving pages --
def open_lab(ctx, iid: str, lab_js: str):
    ctx.route(re.compile(r".*/web/piano-lab-instruments\.js(\?.*)?$"),
              lambda route: route.fulfill(status=200, content_type="text/javascript", body=lab_js))
    page = ctx.new_page()
    page.goto(f"{BASE}/web/piano-lab-instruments.html?id={iid}&view=hero&demo=0", wait_until="load")
    page.wait_for_function("() => window.__lab && (window.__lab.ready || window.__lab.error)", timeout=180000)
    err = page.evaluate("() => window.__lab.error")
    if err:
        raise RuntimeError(f"{iid}: lab error: {err[:400]}")
    return page


def open_page_keys(ctx, piano_js: str):
    """/piano with the Page keys instrument, the chord struck with the pedal down and the page clock held."""
    ctx.route(re.compile(r".*/web/piano\.js(\?.*)?$"),
              lambda route: route.fulfill(status=200, content_type="text/javascript", body=piano_js))
    page = ctx.new_page()
    page.goto(f"{BASE}/piano", wait_until="load")
    page.wait_for_function("() => window.__piano && window.__piano.ready && window.__pianoRig", timeout=180000)
    # the page boots into its saved/default look (an instrument may still be loading when ready flips): let it land,
    # then put the built-in back -- that restores the lacquer body the instrument hid
    page.wait_for_function("() => { const l = window.__piano.looks(); return l.ready && !l.instrumentLoading; }",
                           timeout=180000)
    page.evaluate("""async () => { const P = window.__piano;
        P.setSmoothPreview(false);
        if ((P.looks().instrument || 'page') !== 'page') await P.selectInstrument('page', false); }""")
    page.wait_for_function("""() => { const l = window.__piano.looks();
        return l.instrument === 'page' && !l.instrumentLoading && window.__pianoRig.pageBody.every((o) => o.visible); }""",
                           timeout=120000)
    page.evaluate("""(chord) => { const P = window.__piano;
        P.jam.clock.hold();
        for (let i = 0; i < 2; i++) P.jam.clock.frame(0.1);
        P.midiMessage([0xB0, 64, 127]);
        chord.forEach((m, i) => P.midiMessage([0x90, m, 110 - i * 2]));
        for (let i = 0; i < 6; i++) P.jam.clock.frame(0.1);   // 0.6 s on, as the lab's snapshot (the page clamps dt at 0.1)
        P.setRenderPaused(true); }""", CHORD)
    hero = page.evaluate("() => window.__piano.snapshot()")
    sounding = page.evaluate("() => window.__piano.stats().sounding")
    return page, hero, sounding


def run(ids, kinds, out: Path, work: Path | None):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    if work:
        work.mkdir(parents=True, exist_ok=True)
    lab_js = patched(f"{BASE}/web/piano-lab-instruments.js", "Object.assign(lab, {", LAB_RIG)
    piano_js = patched(f"{BASE}/web/piano.js", None, PAGE_RIG) if "page" in ids else None
    report, problems = {}, []
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=BRAVE, headless=True, args=ARGS)
        try:
            for iid in ids:
                t0 = time.time()
                p = params_for(iid)
                p["preview"] = "preview" in kinds
                ctx = br.new_context(viewport={"width": 960, "height": 540}, device_scale_factor=1)
                errs: list[str] = []
                try:
                    if p["source"] == "page":
                        page, hero, sounding = open_page_keys(ctx, piano_js)
                        p["sounding"] = sounding
                    else:
                        page, hero = open_lab(ctx, iid, lab_js), None
                    page.on("pageerror", lambda e: errs.append(str(e)[:300]))
                    r = page.evaluate(CARD_JS, p)
                finally:
                    ctx.close()
                if r.get("error"):
                    problems.append(f"{iid}: {r['error']}")
                    print(iid, "ERROR", r["error"], flush=True)
                    continue
                rec = {k: r[k] for k in ("ms", "counts", "occluders", "items", "triTotal", "dots", "softs", "proxy",
                                         "skipped", "sounding", "camera", "box")}
                if "wire" in kinds:
                    rec["wire_bytes"] = save_wire(wire_mask(r, p), out / f"{iid}.wire.webp")
                if "preview" in kinds and r.get("previews"):
                    rec["preview_bytes"] = save_preview(preview_image(r["previews"]), out / f"{iid}.preview.webp")
                for k in ("wire_bytes", "preview_bytes"):
                    if rec.get(k, 0) > MAX_BYTES:
                        problems.append(f"{iid}: {k} {rec[k]} over {MAX_BYTES}")
                if work:
                    h = hero or r.get("hero")
                    if h:
                        decode(h).convert("RGB").save(work / f"hero_{iid}.jpg", quality=88)
                    decode(r["png"]).save(work / f"raw_{iid}.png")
                rec["page_errors"] = errs
                rec["seconds"] = round(time.time() - t0, 1)
                report[iid] = rec
                print(iid, json.dumps({k: rec.get(k) for k in ("seconds", "wire_bytes", "preview_bytes", "proxy", "dots")}),
                      flush=True)
        finally:
            br.close()
    if work:
        prev = {}
        rp = work / "report.json"
        if rp.exists():
            prev = json.loads(rp.read_text(encoding="utf-8"))
        prev.update(report)
        rp.write_text(json.dumps(prev, indent=1), encoding="utf-8")
    for line in problems:
        print("PROBLEM", line, flush=True)
    return report, problems


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", help="'all', one id, or a comma list (ids from arsenal/web/piano/instruments/catalog.js)")
    ap.add_argument("--kinds", default="wire,preview", help="wire, preview, or both (default)")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--work", default=None, help="a folder for receipts: report.json, hero frames, raw renders")
    o = ap.parse_args()
    ids = ALL if o.ids == "all" else [s for s in o.ids.split(",") if s]
    unknown = [i for i in ids if i not in ALL]
    if unknown:
        raise SystemExit(f"unknown id(s): {unknown}; known: {ALL}")
    kinds = {k for k in o.kinds.split(",") if k}
    _, problems = run(ids, kinds, Path(o.out), Path(o.work) if o.work else None)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
