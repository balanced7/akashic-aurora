"""present.three-js -- one HTML page: every slide is a textured plane in a three.js gallery.

Each slide's atoms are drawn to an offscreen canvas in logical units (background, headline,
body, quote, number, table rows, diagram boxes and connectors as rectangles and lines -- the
draw list comes from _paint.py) and become a CanvasTexture on a 16x9 plane. The planes stand
along a gentle arc in slide order, with a wider gap where a section starts; ArrowRight and
ArrowLeft fly the camera plane to plane (fade and magic dolly, push trucks); the note shows in
a caption bar under the view and the HUD names the slide. With autoplay (a render option, or
?autoplay=1 on the URL) the deck advances by each slide's duration_s.

three.js loads from exactly one external script, pinned: cdnjs r128 three.min.js (the UMD
build with the THREE global; HEAD 200 on 2026-09-28). `cdn_url(verify=True)` HEAD-checks it
with urllib and falls back to the jsdelivr npm build when cdnjs lacks the version. The page
works from file:// with no build step and stays under 200 KB. Never open it in the Claude
app's own browser pane (WebGL crashed the app on 2026-08-12); use Chrome.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional

from .. import scene as sc
from . import _core as C
from . import _paint
from ._core import esc

MODULE_ID = "present.three-js"
THREE_VERSION = "r128"
CDNJS = "https://cdnjs.cloudflare.com/ajax/libs/three.js/{v}/three.min.js"
JSDELIVR = "https://cdn.jsdelivr.net/npm/three@{v}/build/three.min.js"
DEFAULT_GAP = 480  # logical units between plane edges (a quarter of a slide)
SIZE_LIMIT = 200_000


def _npm_version(version: str) -> str:
    if version.startswith("r") and version[1:].isdigit():
        return f"0.{version[1:]}.0"
    return version


def _head_ok(url: str, timeout: float = 15) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "arsenal.present/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return False


def cdn_url(version: str = THREE_VERSION, verify: bool = False) -> str:
    """The one script the page loads. Unverified: the pinned cdnjs URL. Verified: HEAD cdnjs,
    else HEAD jsdelivr (the npm build of the same version), else refuse."""
    url = CDNJS.format(v=version)
    if not verify:
        return url
    if _head_ok(url):
        return url
    alt = JSDELIVR.format(v=_npm_version(version))
    if _head_ok(alt):
        return alt
    raise RuntimeError(f"three.js {version} answers neither at {url} nor at {alt}")


def deck_data(
    scene: dict, tk: dict | None = None, *, three: str, autoplay: bool = False, plane_gap: float = DEFAULT_GAP
) -> dict:
    tk = tk or C.tokens(scene)
    starts = C.section_starts(scene)
    slides = [_paint.paint_slide(scene, s, tk, section=starts.get(s["id"])) for s in C.ordered_slides(scene)]
    world_per_unit = 16 / sc.CANVAS["w"]
    return {
        "title": scene.get("title", ""),
        "three": three,
        "bg": tk["palette"]["dark"],
        "faces": tk["faces"],
        "autoplay": bool(autoplay),
        "gap": round(16 + plane_gap * world_per_unit, 3),
        "section_gap": round(plane_gap * world_per_unit, 3),
        "slides": slides,
    }


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
__FONTS__<style>
html, body { margin: 0; height: 100%; overflow: hidden; background: __BG__; color: #F6F7F5; font-family: __SANS__ }
#c { display: block; width: 100%; height: 100% }
#hud { position: fixed; left: 24px; top: 20px; font: 500 14px/1.4 __MONO__; letter-spacing: 1px; color: rgba(246,247,245,.85); text-transform: uppercase; pointer-events: none }
#hud b { font-weight: 500; color: #C8762E }
#caption { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); width: min(1100px, calc(100% - 48px)); max-height: 28vh; overflow: auto; padding: 16px 22px; border-radius: 12px; background: rgba(8,14,20,.78); border: 1px solid rgba(246,247,245,.12); font-size: 16px; line-height: 1.5; color: rgba(246,247,245,.92) }
#caption:empty { display: none }
#help { position: fixed; right: 24px; top: 20px; font: 400 13px/1.4 __MONO__; color: rgba(246,247,245,.55); pointer-events: none }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="hud"></div>
<div id="help">&larr; &rarr; slides &middot; click a plane &middot; home / end</div>
<div id="caption"></div>
<script src="__THREE__"></script>
<script>
var DECK = __DECK__;
(function () {
  var W = 1920, H = 1080, PW = 16, PH = 9;
  var canvas = document.getElementById('c'), hud = document.getElementById('hud'), cap = document.getElementById('caption');
  if (!window.THREE) {
    cap.textContent = 'three.js did not load from ' + DECK.three + ' (offline?). The deck is still in this file as DECK.slides.';
    return;
  }
  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(DECK.bg);
  var camera = new THREE.PerspectiveCamera(45, 1, 0.1, 5000);
  var N = DECK.slides.length, slots = [], arc = 0, i;
  for (i = 0; i < N; i++) { if (i > 0 && DECK.slides[i].section) arc += DECK.section_gap; slots.push(arc); arc += DECK.gap; }
  var R = Math.max(arc / 1.6, PW * 6);
  var geo = new THREE.PlaneGeometry(PW, PH), frameGeo = new THREE.PlaneGeometry(PW + 0.3, PH + 0.3);
  var frameMat = new THREE.MeshBasicMaterial({ color: 0x2c4356 });
  var planes = [], poses = [];
  for (i = 0; i < N; i++) {
    var a = slots[i] / R;
    var n = new THREE.Vector3(Math.sin(a), 0, -Math.cos(a));
    var pos = new THREE.Vector3(R * Math.sin(a), 0, R - R * Math.cos(a));
    var mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: new THREE.Color(DECK.slides[i].bg) }));
    mesh.position.copy(pos); mesh.rotation.y = Math.PI - a; mesh.userData.index = i;
    var border = new THREE.Mesh(frameGeo, frameMat);
    border.position.copy(pos).addScaledVector(n, -0.05); border.rotation.y = Math.PI - a;
    scene.add(border); scene.add(mesh); planes.push(mesh); poses.push({ pos: pos, n: n });
  }

  // ---- painting a slide into its texture
  function rr(ctx, x, y, w, h, r) {
    r = Math.min(r || 0, w / 2, h / 2);
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }
  function fontFor(o, mark) {
    var wt = mark === 'strong' ? Math.max(o.wt, 600) : o.wt;
    var face = mark === 'code' ? DECK.faces.mono : DECK.faces[o.f] || DECK.faces.sans;
    return (mark === 'em' ? 'italic ' : '') + wt + ' ' + o.z + 'px ' + face;
  }
  function colourFor(o, mark, s) { return mark === 'accent' ? s.ca : (mark === 'muted' ? s.cm : o.c); }
  function drawText(ctx, o, s) {
    var lh = o.z * o.lh, tokens = [];
    o.r.forEach(function (run) {
      String(run[0]).split('\\n').forEach(function (part, pi) {
        if (pi > 0) tokens.push({ br: true });
        part.split(/(\\s+)/).forEach(function (piece) { if (piece) tokens.push({ t: piece, m: run[1], sp: /^\\s+$/.test(piece) }); });
      });
    });
    if ('letterSpacing' in ctx) ctx.letterSpacing = (o.ls || 0) + 'px';
    // Whitespace is content: a code line's indentation is drawn (the first line, and every line
    // after a forced break, begins on purpose). A wrapped line never begins with a space, since
    // the wrap happens on the word and the space before it stayed on the line above -- so no
    // leading-space guard is needed (the one that was here dropped indentation, 2026-09-29).
    var lines = [[]], widths = [], width = 0;
    tokens.forEach(function (tk) {
      if (tk.br) { widths.push(width); lines.push([]); width = 0; return; }
      ctx.font = fontFor(o, tk.m);
      var w = ctx.measureText(tk.t).width;
      if (!tk.sp && width + w > o.w && lines[lines.length - 1].length) { widths.push(width); lines.push([]); width = 0; }
      tk.w = w; lines[lines.length - 1].push(tk); width += w;
    });
    widths.push(width);
    var y = o.y + (lh - o.z) / 2 + o.z * 0.8;
    lines.forEach(function (line, li) {
      var x = o.x;
      if (o.a === 'center') x = o.x + (o.w - widths[li]) / 2; else if (o.a === 'right') x = o.x + o.w - widths[li];
      line.forEach(function (tk) { ctx.font = fontFor(o, tk.m); ctx.fillStyle = colourFor(o, tk.m, s); ctx.fillText(tk.t, x, y); x += tk.w; });
      y += lh;
    });
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
  }
  function head(ctx, from, to, colour, sw) {
    var ang = Math.atan2(to[1] - from[1], to[0] - from[0]), L = Math.max(10, 4.5 * sw);
    ctx.fillStyle = colour; ctx.beginPath(); ctx.moveTo(to[0], to[1]);
    ctx.lineTo(to[0] - L * Math.cos(ang - 0.45), to[1] - L * Math.sin(ang - 0.45));
    ctx.lineTo(to[0] - L * Math.cos(ang + 0.45), to[1] - L * Math.sin(ang + 0.45)); ctx.closePath(); ctx.fill();
  }
  function drawLine(ctx, o) {
    var sw = o.sw || 2;
    ctx.strokeStyle = o.c; ctx.lineWidth = sw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.setLineDash(o.d ? [12, 10] : []);
    ctx.beginPath();
    o.p.forEach(function (pt, j) { if (j) ctx.lineTo(pt[0], pt[1]); else ctx.moveTo(pt[0], pt[1]); });
    ctx.stroke(); ctx.setLineDash([]);
    if (o.h === 'end' || o.h === 'both') head(ctx, o.p[o.p.length - 2], o.p[o.p.length - 1], o.c, sw);
    if (o.h === 'both') head(ctx, o.p[1], o.p[0], o.c, sw);
  }
  function paint(s) {
    var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d');
    ctx.fillStyle = s.bg; ctx.fillRect(0, 0, W, H);
    ctx.textBaseline = 'alphabetic';
    s.ops.forEach(function (o) {
      if (o.t === 'rect') {
        ctx.setLineDash(o.d ? [12, 10] : []); rr(ctx, o.x, o.y, o.w, o.h, o.r);
        if (o.f) { ctx.fillStyle = o.f; ctx.fill(); }
        if (o.s) { ctx.strokeStyle = o.s; ctx.lineWidth = o.sw || 1; ctx.stroke(); }
        ctx.setLineDash([]);
      } else if (o.t === 'line') drawLine(ctx, o);
      else if (o.t === 'text') drawText(ctx, o, s);
    });
    return cv;
  }
  var built = {};
  function ensure(i) {
    if (i < 0 || i >= N || built[i]) return;
    built[i] = true;
    var tex = new THREE.CanvasTexture(paint(DECK.slides[i]));
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    planes[i].material.map = tex; planes[i].material.color.set('#ffffff'); planes[i].material.needsUpdate = true;
  }

  // ---- the camera and its flights
  var current = 0, flight = null, timer = null;
  function dist() {
    var vh = 2 * Math.tan(camera.fov * Math.PI / 360);
    return Math.max(PH * 1.14 / vh, PW * 1.08 / (vh * camera.aspect));
  }
  function poseOf(i) { var p = poses[i]; return { pos: p.pos.clone().addScaledVector(p.n, dist()), target: p.pos.clone() }; }
  function place(i) { var q = poseOf(i); camera.position.copy(q.pos); camera.lookAt(q.target); }
  function show(i) {
    var s = DECK.slides[i];
    hud.innerHTML = '<b>' + (i + 1) + ' / ' + N + '</b> &middot; ' + esc(s.title) + (s.section ? ' &middot; ' + esc(s.section) : '');
    cap.textContent = s.note || '';
  }
  function esc(t) { return String(t).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }
  function go(i, instant) {
    i = Math.max(0, Math.min(N - 1, i));
    if (timer) { clearTimeout(timer); timer = null; }
    for (var k = i - 2; k <= i + 2; k++) ensure(k);
    var from = { pos: camera.position.clone(), target: poseOf(current).target }, to = poseOf(i);
    var tr = DECK.slides[i].transition;
    flight = instant ? null : { from: from, to: to, t0: performance.now(), dur: 650 + 90 * Math.min(6, Math.abs(i - current)),
      pull: tr === 'push' ? 0 : dist() * 0.35, n: poses[current].n.clone().add(poses[i].n).normalize() };
    current = i; show(i);
    if (instant) place(i);
    if (DECK.autoplay || /[?&]autoplay=1/.test(location.search)) timer = setTimeout(function () { go(current + 1); }, DECK.slides[i].duration_s * 1000);
  }
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
  function frame(now) {
    if (flight) {
      var t = Math.min(1, (now - flight.t0) / flight.dur), e = ease(t);
      var p = flight.from.pos.clone().lerp(flight.to.pos, e).addScaledVector(flight.n, flight.pull * Math.sin(Math.PI * e));
      camera.position.copy(p); camera.lookAt(flight.from.target.clone().lerp(flight.to.target, e));
      if (t >= 1) { flight = null; place(current); }
    }
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  function resize() {
    var w = window.innerWidth, h = window.innerHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    if (!flight) place(current);
  }
  window.addEventListener('resize', resize);
  window.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowRight' || ev.key === 'PageDown' || ev.key === ' ') { go(current + 1); ev.preventDefault(); }
    else if (ev.key === 'ArrowLeft' || ev.key === 'PageUp') { go(current - 1); ev.preventDefault(); }
    else if (ev.key === 'Home') go(0); else if (ev.key === 'End') go(N - 1);
  });
  var ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  canvas.addEventListener('click', function (ev) {
    mouse.x = (ev.clientX / window.innerWidth) * 2 - 1; mouse.y = -(ev.clientY / window.innerHeight) * 2 + 1;
    ray.setFromCamera(mouse, camera);
    var hit = ray.intersectObjects(planes)[0];
    if (hit) go(hit.object.userData.index);
  });
  function start() { resize(); go(0, true); requestAnimationFrame(frame); }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(start, start);
})();
</script>
</body>
</html>
"""


def page(
    scene: dict,
    tk: dict | None = None,
    *,
    three: str | None = None,
    autoplay: bool = False,
    plane_gap: float = DEFAULT_GAP,
) -> str:
    tk = tk or C.tokens(scene)
    data = deck_data(scene, tk, three=three or cdn_url(), autoplay=autoplay, plane_gap=plane_gap)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fonts = f'<link rel="stylesheet" href="{esc(tk["href"])}">\n' if tk.get("href") else ""
    return (
        PAGE.replace("__TITLE__", esc(scene.get("title", "")))
        .replace("__FONTS__", fonts)
        .replace("__BG__", tk["palette"]["dark"])
        .replace("__SANS__", tk["faces"]["sans"])
        .replace("__MONO__", tk["faces"]["mono"])
        .replace("__THREE__", esc(data["three"]))
        .replace("__DECK__", blob)
    )


def render(
    scene: dict,
    out_dir,
    verify_cdn: bool = False,
    autoplay: bool = False,
    plane_gap: float = DEFAULT_GAP,
    three_version: str = THREE_VERSION,
    **opts,
) -> list[Path]:
    """Write <out_dir>/index.html (one page, one external script, under 200 KB)."""
    three = cdn_url(three_version, verify=bool(verify_cdn))
    html = page(scene, three=three, autoplay=autoplay, plane_gap=float(plane_gap))
    size = len(html.encode("utf-8"))
    if size > SIZE_LIMIT:
        raise RuntimeError(f"the three.js page is {size} bytes; the ceiling is {SIZE_LIMIT} (split the deck)")
    return [C.write_bytes(Path(out_dir) / "index.html", html)]
