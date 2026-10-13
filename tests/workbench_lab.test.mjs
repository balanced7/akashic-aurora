// Node tests for the Shader Lab Workbench (arsenal/web/lib/workbench/*, mounted by arsenal/web/shaderlab/lab.js).
// Zero dependencies:  node tests/workbench_lab.test.mjs
//
// WHY THIS FILE EXISTS. The Workbench is the first home of the unified UI (build-spec-reconciled.md ruling 4), and the
// lab is the page Daniel opens in his own browser on a machine with an AMD display-driver crash history. Ruling 5 makes
// it safe by default: nothing renders live on page load, and running a shader on his GPU is an explicit click that
// names the subject's cost class first, starts at render scale 0.5 for C3 and C4 subjects, and stops on the house
// watchdog (consecutive slow frames while requestAnimationFrame is firing; hold the last frame). Those are promises a
// passing look cannot prove, so they are pinned here, with a fake document, a fake runtime and a hand-pumped
// animation clock (no jsdom, no browser, no WebGL).
//
// The other half: every panel is honest while the routes it reads do not exist yet (the Shelf slice adds them tonight):
// a panel says "not available yet" and names the route, never a blank.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { ROUTES, fetchJson, unavailable, studyBlocks } from "../arsenal/web/lib/workbench/common.js";
import { buildTree, filterTree, mountLibrary } from "../arsenal/web/lib/workbench/library.js";
import { licenceClass, normalizeShelf, shelfFromAtlas, sheetFrame, teachesFor, mountShelf } from "../arsenal/web/lib/workbench/shelf.js";
import * as stageMod from "../arsenal/web/lib/workbench/stage.js";
import {
  WATCHDOG, PREFLIGHT, costGate, costFloorFromShader, createWatchdog, preflightPlan, parseCard, bindParams, cardShader,
  mountStage,
} from "../arsenal/web/lib/workbench/stage.js";
// LADDER's step cap is new with the lab-safety fixes; read through the namespace so the pins can be seen failing on the
// stage that lacked it, instead of the whole file failing to load.
const LADDER = stageMod.LADDER || {};
// The one switch in front of the live path is off unless the page's address asks (?live=1) AND the browser holds the key.
// Tests that run the Stage hand it a page that has both; every other mount gets node's globals, which have neither.
const LIVE_KEY = (stageMod.LIVE_SWITCH && stageMod.LIVE_SWITCH.key) || "arsenal.shaderlab.live";
const LIVE_ON = { location: { search: "?live=1" }, localStorage: { getItem: (k) => (k === LIVE_KEY ? "on" : null) } };
// The pre-flight's frame sizes: the tiny pair, the second (or, for a heavy tiny frame, the smaller `mid` one), and the
// larger ones it draws while its readings leave the growth unproven. A fake cost tells them from live frames by these
// (no live size in these tests is one).
const PF_ALL = new Set([`${PREFLIGHT.w}x${PREFLIGHT.h}`, `${PREFLIGHT.w2}x${PREFLIGHT.h2}`,
  ...(PREFLIGHT.mid ? [`${PREFLIGHT.mid[0]}x${PREFLIGHT.mid[1]}`] : []),
  ...((PREFLIGHT.grow || []).map(([w, h]) => `${w}x${h}`))]);
const isPf = (w, h) => PF_ALL.has(`${w}x${h}`);
import { composedFacts, mountInspector, preflightText } from "../arsenal/web/lib/workbench/inspector.js";
import { mountStrip } from "../arsenal/web/lib/workbench/strip.js";
import { cardImages, closureCost, mediaFor, mountWorkbench } from "../arsenal/web/lib/workbench/workbench.js";
import * as paramsUi from "../arsenal/web/lib/params-ui.js";
import * as params from "../arsenal/web/lib/params.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);

const atlas = JSON.parse(readFileSync(here("../arsenal/shaders/atlas.json"), "utf8"));

// ------------------------------------------------------------------------------------------- the fake page --
// Just enough DOM for the components: they take the document as an argument and use createElement, appendChild,
// replaceChildren, attributes, properties and listeners only. Walking the tree replaces querySelector.
class FakeEl {
  constructor(doc, tag) {
    Object.assign(this, { ownerDocument: doc, tagName: tag.toUpperCase(), children: [], parentNode: null, attributes: {},
      dataset: {}, style: {}, className: "", textContent: "", hidden: false, disabled: false, value: "", title: "",
      type: "", src: "", alt: "", open: false, listeners: {} });
    if (tag === "canvas") {
      this.width = 300; this.height = 150; this.contexts = 0;
      this.getContext = () => { this.contexts++; doc.getContextCalls++; return null; };
      this.toDataURL = () => "data:image/png;base64,iVBORw0KGgo=";
    }
  }
  appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { for (const c of cs) this.appendChild(typeof c === "string" ? this.ownerDocument.createTextNode(c) : c); }
  removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  replaceChildren(...cs) { for (const c of this.children) c.parentNode = null; this.children = []; this.append(...cs); }
  get firstChild() { return this.children[0] || null; }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  removeEventListener(t, fn) { this.listeners[t] = (this.listeners[t] || []).filter((f) => f !== fn); }
  fire(type, props = {}) {
    const e = { type, target: this, currentTarget: this, detail: 1, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() {}, ...props };
    for (const fn of [...(this.listeners[type] || [])]) fn(e);
    return e;
  }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  getBoundingClientRect() { return { width: this.ownerDocument.boxW, height: this.ownerDocument.boxH, left: 0, top: 0 }; }
}
function fakeDocument() {
  const doc = { activeElement: null, getContextCalls: 0, canvases: 0, boxW: 640, boxH: 360, visibilityState: "visible" };
  doc.createElement = (t) => { if (t === "canvas") doc.canvases++; return new FakeEl(doc, t); };
  doc.createTextNode = (s) => Object.assign(new FakeEl(doc, "#text"), { textContent: String(s) });
  doc.body = new FakeEl(doc, "body");
  doc.activeElement = doc.body;
  return doc;
}
function* walk(el) { yield el; for (const c of el.children) yield* walk(c); }
const find = (root, pred) => { for (const el of walk(root)) if (pred(el)) return el; return null; };
const findAll = (root, pred) => [...walk(root)].filter(pred);
const hasClass = (el, c) => (" " + el.className + " ").includes(" " + c + " ");
const byClass = (root, c) => findAll(root, (el) => hasClass(el, c));
const textOf = (el) => [...walk(el)].map((e) => e.textContent || "").join(" ");
const tick = () => new Promise((r) => setTimeout(r, 0));
async function settle(n = 8) { for (let i = 0; i < n; i++) await tick(); }

// A fetch that answers from a table of url -> body (object = JSON, string = text) and 404s everything else.
function fakeFetch(table = {}) {
  const calls = [];
  const fn = async (url) => {
    const u = String(url);
    calls.push(u);
    if (!(u in table)) return { ok: false, status: 404, json: async () => ({ error: "not found" }), text: async () => "not found" };
    const body = table[u];
    return { ok: true, status: 200, json: async () => (typeof body === "string" ? JSON.parse(body) : body),
      text: async () => (typeof body === "string" ? body : JSON.stringify(body)) };
  };
  fn.calls = calls;
  return fn;
}

// A runtime with toy-runtime.js's surface (createToy -> gl, ready, compile, render, resize, reset, info, stats, destroy),
// counting what the stage asks of it. With a clock, a frame COSTS time: log.cost(w, h) milliseconds pass on the clock
// while render() runs (the way a GPU frame holds up the next animation frame), so the pre-flight and the watchdog can
// be driven by pixels the way a real shader drives them. gl.finish() is counted: the pre-flight times through it.
// A driver that compiles at its first draw is modelled by log.coldMs, spent on a toy's first render whatever it shades;
// a draw with the scissor test on and an empty rect shades nothing and costs no pixels (log.shaded counts the others).
// The frame counter is toy-runtime.js's: render() draws args.frame when given, else the counter, which then moves to
// that frame + 1, and reset() puts it back to 0; log.cost(w, h, iFrame) may depend on it. A resize to a new size queues
// log.reallocMs of GPU work (the buffers' reallocation), which gl.finish() waits out and which an unsynced render pays
// first. log.events records every finish and every render in order, with its toy, size, frame and cost. With
// log.asyncGpu a frame's cost is queued instead of spent (the GPU works behind the page), and with log.finishWaits ===
// false gl.finish() returns at once (as it did on SwiftShader through ANGLE, 2026-10-13): only gl.readPixels(), which
// cannot answer before the frame it reads is drawn, waits the queue out. log.cost gets the toy's number as a fourth
// argument (the first toy built is 1), and log.compileMs(toy) / log.compileFails(toy), when given, make a toy's compile
// hold the main thread that long / come back not drawable. log.overheadMs is what every draw pays whatever it shades
// (a submission and the read-back's round trip): a draw scissored to one pixel costs that much, and a frame that much
// more than its pixels' log.cost (its events and shadedLog carry the sum). log.onePixelMs(n, toy), when given and a
// number, is what the n-th draw scissored to one pixel costs instead (n counts from 0, the warm-up first): a hiccup in
// the timing (a GC pause, the scheduler) on the draw that reads what every frame pays.
function fakeRuntime(log = { created: 0, renders: 0, resizes: [], destroyed: 0, shaders: [] }, { clock = null } = {}) {
  Object.assign(log, { finishes: 0, resets: 0, sizes: [], cost: null, coldMs: 0, shaded: 0, reallocMs: 0, toys: 0,
    overheadMs: 0, events: [], shadedLog: [], ...log });
  return {
    log,
    module: {
      API: "arsenal.shaderlab-runtime/v1",
      createToy(canvas, shader, opts) {
        log.created++;
        log.shaders.push(shader);
        log.opts = opts;
        canvas.getContext("webgl2");
        const toy = ++log.toys;
        let scissor = false, rect = null, cold = true, frame = 0, queued = 0;
        const spend = (ms) => { if (clock && ms) clock.spend(ms); };
        const gl = {
          finish: () => { log.finishes++; log.events.push({ kind: "finish", toy }); if (log.finishWaits !== false) { spend(queued); queued = 0; } },
          readPixels: () => { log.readbacks = (log.readbacks || 0) + 1; spend(queued); queued = 0; },
          scissor: (x, y, w, h) => { rect = [w, h]; },
          enable: (cap) => { if (cap === 0x0C11) scissor = true; }, disable: (cap) => { if (cap === 0x0C11) scissor = false; } };
        return {
          gl, canvas, history: false, ready: Promise.resolve(), load: () => Promise.resolve(),
          compile: () => {
            if (typeof log.compileMs === "function") spend(log.compileMs(toy));
            if (typeof log.compileFails === "function" && log.compileFails(toy)) {
              return { ok: false, drawable: false, passes: [{ name: "Image", ok: false, firstError: "ERROR: 0:1: a knob value that does not compile" }], warnings: [] };
            }
            return { ok: true, drawable: true, passes: [{ name: "Image", ok: true }], warnings: [] };
          },
          render: (a = {}) => {
            log.renders++; log.lastTime = a && a.time;
            const f = Number.isFinite(a.frame) ? Math.floor(a.frame) : frame;
            frame = f + 1;
            // The compile at first draw; with log.coldNeedsPixels (SwiftShader) a draw clipped to nothing is skipped
            // before it, so the compile waits for the first draw that shades a pixel.
            const clippedAway = scissor && rect && rect[0] * rect[1] === 0;
            if (cold && !(log.coldNeedsPixels && clippedAway)) { if (clock && log.coldMs) clock.spend(log.coldMs); cold = false; }
            if (!log.asyncGpu) { spend(queued); queued = 0; }
            const w = canvas.width, h = canvas.height;
            const over = clock && Number(log.overheadMs) > 0 ? Number(log.overheadMs) : 0;
            if (scissor) {
              const n = log.onePixelDraws = (log.onePixelDraws || 0) + 1;
              const hit = clock && typeof log.onePixelMs === "function" ? log.onePixelMs(n - 1, toy) : null;
              const ms = Number.isFinite(hit) ? hit : over;
              log.events.push({ kind: "render", toy, w, h, iFrame: f, ms, scissor: true });
              if (log.asyncGpu) queued += ms; else spend(ms);
              return { frame: f, time: a && a.time };
            }
            log.shaded++; log.sizes.push([w, h]);
            const ms = over + (clock && typeof log.cost === "function" ? log.cost(w, h, f, toy) : 0);
            log.shadedLog.push({ toy, w, h, iFrame: f, ms });
            log.events.push({ kind: "render", toy, w, h, iFrame: f, ms, scissor: false });
            if (log.asyncGpu) queued += ms; else spend(ms);
            return { frame: f, time: a && a.time };
          },
          resize: (w, h) => {
            if (w !== canvas.width || h !== canvas.height) queued += log.reallocMs || 0;
            canvas.width = w; canvas.height = h; log.resizes.push([w, h]);
          },
          reset: () => { log.resets++; frame = 0; },
          info: () => ({ renderer: "Fake GPU renderer", caps: {} }),
          stats: () => ({ substituted: [], unsupported: [], bufferFormat: null }),
          destroy: () => { log.destroyed++; },
        };
      },
    },
  };
}

// A hand-pumped animation clock: raf queues, pump(dtMs) advances now and runs the queue once; spend(ms) moves the clock
// without running anything (time passing inside a frame, or while nothing is scheduled).
function fakeClock() {
  let now = 1000, q = [], id = 0;
  const clock = {
    rafCalls: 0,
    now: () => now,
    raf: (fn) => { clock.rafCalls++; q.push({ id: ++id, fn }); return id; },
    caf: (k) => { q = q.filter((e) => e.id !== k); },
    pending: () => q.length,
    spend(ms) { now += ms; },
    pump(dtMs = 16) { now += dtMs; const run = q; q = []; for (const e of run) e.fn(now); },
  };
  return clock;
}

// The page's global fetch, from a table keyed by path (modlib.loadLibrary fetches through it, with absolute URLs). A
// Uint8Array body answers arrayBuffer() with its bytes, as a real Response does, so a file that is not UTF-8 reaches
// the composer exactly as the CLI reads it.
function globalFetchFrom(table, calls = []) {
  return async (url) => {
    const path = new URL(String(url), "http://localhost/").pathname;
    calls.push(path);
    const body = table[path];
    if (body === undefined) return { ok: false, status: 404, json: async () => ({ error: "not found" }), text: async () => "not found" };
    if (body instanceof Uint8Array) {
      return { ok: true, status: 200, arrayBuffer: async () => body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength),
        text: async () => new TextDecoder().decode(body), json: async () => JSON.parse(new TextDecoder().decode(body)) };
    }
    return { ok: true, status: 200, json: async () => (typeof body === "string" ? JSON.parse(body) : body),
      text: async () => (typeof body === "string" ? body : JSON.stringify(body)) };
  };
}
async function withGlobalFetch(fetchFn, fn) {
  const saved = globalThis.fetch;
  globalThis.fetch = fetchFn;
  try { return await fn(); } finally { globalThis.fetch = saved; }
}

// =================================================================================== library: the tree --
{
  const tree = buildTree(atlas, new Map());
  eq("13 families, in atlas order", tree.families.map((f) => f.letter), atlas.families.map((f) => f.letter));
  const cats = tree.families.flatMap((f) => f.categories);
  eq("81 categories", cats.length, atlas.categories.length);
  const mods = cats.flatMap((c) => c.modules);
  const planned = new Set(atlas.parts.map((p) => p.module).filter(Boolean));
  eq("every module the atlas plans appears once", mods.map((m) => m.path).sort(), [...planned].sort());
  check("nothing built when the index is empty", mods.every((m) => m.status === "planned"));
  eq("totals count planned and built", [tree.totals.modules, tree.totals.built], [planned.size, 0]);
  eq("the 25 groups ride along", tree.groups.length, atlas.groups.length);

  // A module's cost is the heaviest of its parts and its priority the most urgent; its functions are the parts'.
  const safe = mods.find((m) => m.path === "core/safe.glsl");
  const safeParts = atlas.parts.filter((p) => p.module === "core/safe.glsl");
  eq("core/safe.glsl priority", safe.priority, safeParts.some((p) => p.status === "P0") ? "P0" : safe.priority);
  eq("core/safe.glsl functions", safe.functions, safeParts.flatMap((p) => p.functions));
  const march = mods.find((m) => m.path === "ray/march.glsl");
  check("ray/march.glsl is at least C2 (a march)", ["C2", "C3", "C4"].includes(march.cost), march.cost);

  // Built: a module the library index provides flips to built and carries its header; one the atlas does not plan is
  // listed honestly under its own heading, not dropped.
  const built = new Map([
    ["core/safe.glsl", { name: "core-safe", path: "core/safe.glsl", version: "1.0.0", kind: "helper",
      header: { name: "core-safe", kind: "helper", cat: "A1", version: "1.0.0", cost: { class: "C0" }, license: "Apache-2.0" } }],
    ["extra/odd.glsl", { name: "odd-one", path: "extra/odd.glsl", version: "0.1.0", kind: "helper",
      header: { name: "odd-one", kind: "helper", cat: "Z9", version: "0.1.0" } }],
  ]);
  const t2 = buildTree(atlas, built);
  const safe2 = t2.families.flatMap((f) => f.categories).flatMap((c) => c.modules).find((m) => m.path === "core/safe.glsl");
  eq("a built module is built, named by its header", [safe2.status, safe2.name, safe2.version], ["built", "core-safe", "1.0.0"]);
  eq("built totals", t2.totals.built, 2);
  check("a built module outside the atlas is listed under 'not in the atlas'",
    t2.unplaced.length === 1 && t2.unplaced[0].path === "extra/odd.glsl");
  const fA = t2.families.find((f) => f.letter === "A");
  eq("family counts built modules", fA.counts.built, 1);

  // Filtering keeps the path from family to module and drops empty branches.
  const f = filterTree(tree, "safeSqrt");
  eq("filter by a function name finds its module", f.families.flatMap((x) => x.categories).flatMap((c) => c.modules).map((m) => m.path), ["core/safe.glsl"]);
  eq("filter keeps one family", f.families.length, 1);
}

// ================================================================================ library: the mount --
{
  const doc = fakeDocument();
  const root = doc.createElement("section");
  const picked = [];
  const lib = mountLibrary(doc, root, { onSelect: (node) => picked.push(node), routes: ROUTES });
  // Before data: an honest loading state, never a blank.
  check("library shows something before data", textOf(root).trim().length > 0);
  lib.setUnavailable({ route: "/atlas.json", why: "HTTP 404" });
  check("library unavailable names the route", /not available yet/i.test(textOf(root)) && textOf(root).includes("/atlas.json"));

  const tree = buildTree(atlas, new Map());
  lib.setTree(tree);
  const families = byClass(root, "wb-family");
  eq("one family node per family", families.length, 13);
  const moduleRows = byClass(root, "wb-module");
  eq("one row per module", moduleRows.length, tree.totals.modules);
  const row = moduleRows.find((r) => r.dataset.path === "core/safe.glsl");
  check("a planned module row says planned", /planned/i.test(textOf(row)));
  check("a module row shows its cost class", /C0/.test(textOf(row)));
  row.fire("click");
  eq("clicking a module selects it", picked.map((n) => n.path), ["core/safe.glsl"]);
  check("the selected row is marked", hasClass(row, "is-selected"));
  // Groups are in the tree too.
  check("groups listed", byClass(root, "wb-group").length === atlas.groups.length);
  // reveal opens the family and category that hold a category id (a tag link from the Shelf lands here).
  lib.reveal("B3");
  const fam = byClass(root, "wb-family").find((n) => n.dataset.family === "B");
  const cat = byClass(root, "wb-category").find((n) => n.dataset.category === "B3");
  check("reveal opens the family and the category", fam.open === true && cat.open === true);
}

// ====================================================================================== shelf: the cards --
{
  eq("licence classes", ["MIT (explicit)", "CC0 (explicit)", "CC BY-NC-SA (default)", "CC-BY-NC-SA-3.0 (Shadertoy default)",
    "all rights reserved", "", null].map(licenceClass),
  ["permissive", "permissive", "restricted", "restricted", "restricted", "unknown", "unknown"]);

  // The shape arsenal/shaders/shelf.py writes (arsenal.shader-shelf/v1), trimmed to the fields the cards read.
  const shelfJson = {
    api: "arsenal.shader-shelf/v1",
    shaders: [
      { rank: 1, id: "ttScDc", title: "AURORA", short: "AURORA", author: "alro", url: "https://www.shadertoy.com/view/ttScDc",
        licence: { name: "MIT", meta: "MIT", explicit: true, line: "MIT License", corrected: false },
        study_only: false, study_only_reason: null,
        tags: ["raymarch.fixed_step", "noise.fbm"],
        categories: [{ id: "E3", name: "Marchers", family: "E", tags: ["raymarch.fixed_step"] },
          { id: "B3", name: "Fractal sums", family: "B", tags: ["noise.fbm"] }],
        groups: [{ name: "aurora", status: "P0", cost: "C2", line: "the aurora", study_only: false }],
        parts: [{ id: "G8.01", category: "G8", functions: ["auroraSheets"], module: "atmos/aurora.glsl", status: "P0", cost: "C2" }],
        study: { url: "/study/ttScDc.md", title: "Study: AURORA (ttScDc)", headings: ["3. How it works"], techniques: [], missing: false },
        renders: { status: "rendered", fps: 60,
          stills: [{ t: 1.0, url: "/renders/ttScDc/t1.00.png" }, { t: 4.0, url: "/renders/ttScDc/t4.00.png" }],
          filmstrip: { url: "/renders/ttScDc/filmstrip.png", frames: 8, to: 8.0, fps: 60 }, problems: [] },
        passes: ["image", "buffer"] },
      { rank: 2, id: "4s23zz", title: "Warping", author: "someone",
        licence: { name: "all-rights-reserved", meta: "CC-BY-NC-SA-3.0", corrected: true },
        study_only: true, study_only_reason: "its own header withholds permission",
        tags: ["noise.domain_warp"], categories: [{ id: "B4", name: "Domain warping", family: "B", tags: ["noise.domain_warp"] }],
        groups: [], parts: [], study: { url: "/study/4s23zz.md", missing: false },
        renders: { status: "withheld: study only (no images, whatever is on disk)", stills: [], filmstrip: null }, passes: ["image"] },
      { rank: 3, id: "7d2fDW", title: "Appolloian with a twist II", short: "Apollonian", author: "mrange",
        licence: { name: "CC0-1.0", explicit: true, corrected: false }, study_only: false, tags: [], categories: [],
        groups: [], parts: [], study: { missing: true }, renders: { status: "not rendered", stills: [], filmstrip: null },
        passes: ["image"] },
    ],
  };
  const norm = normalizeShelf(shelfJson, atlas, ROUTES);
  eq("three entries, in order", norm.entries.map((e) => e.id), ["ttScDc", "4s23zz", "7d2fDW"]);
  const aur = norm.entries[0];
  eq("tags keep the categories the Shelf placed them on", aur.tags.map((t) => [t.tag, t.categories]),
    [["raymarch.fixed_step", ["E3"]], ["noise.fbm", ["B3"]]]);
  eq("categories as ids", aur.categories, ["E3", "B3"]);
  eq("the licence object reads as its name", [aur.licence, aur.licenceClass], ["MIT", "permissive"]);
  const warp = norm.entries[1];
  check("a corrected licence says so", /all-rights-reserved/.test(warp.licence) && /corrected/.test(warp.licence) && warp.licenceClass === "restricted");
  eq("stills become the strip's frames", aur.images.frames.map((f) => [f.t, f.url]),
    [[1, "/renders/ttScDc/t1.00.png"], [4, "/renders/ttScDc/t4.00.png"]]);
  eq("the poster is the first still", aur.images.poster[0], "/renders/ttScDc/t1.00.png");
  const dark = normalizeShelf({ shaders: [{ id: "ltffzl", renders: { stills: [
    { t: 1, url: "/renders/ltffzl/t1.00.png", mean_luma: 1.2, flat: true },
    { t: 4, url: "/renders/ltffzl/t4.00.png", mean_luma: 38.5, flat: false }] } }] }, atlas, ROUTES).entries[0];
  eq("a black or flat still is not the poster when a brighter one exists", dark.images.poster[0], "/renders/ltffzl/t4.00.png");
  eq("the strip keeps the stills in time order", dark.images.frames.map((f) => f.t), [1, 4]);
  eq("the pass list is kept for the datasheet", aur.passTypes, ["image", "buffer"]);
  eq("the contact sheet url", aur.images.sheet, "/renders/ttScDc/filmstrip.png");
  eq("the flipbook plays the sheet's 8 frames", aur.images.flip && aur.images.flip.frames, 8);
  check("no frame-folder url (the server serves one level only)", ![...aur.images.poster, ...aur.images.frames.map((f) => f.url)].some((u) => /filmstrip\//.test(u)));
  eq("study only: no images at all", warp.images, { poster: [], frames: [], sheet: null, flip: null });
  check("an entry with no renders still gets poster candidates", norm.entries[2].images.poster.length > 0);
  eq("the study note url", aur.studyUrl, "/study/ttScDc.md");
  eq("buffers in the pass list make the cost C4 before any click", [aur.cost, norm.entries[2].cost], ["C4", null]);
  eq("the Shelf's own groups are what it teaches", aur.teaches.groups.map((g) => g.name), ["aurora"]);
  eq("and its parts' categories", aur.teaches.categories, ["G8"]);

  // Study only is the OR of every source: a stale `false` in the Shelf index never beats the atlas's `true` (the card
  // would offer "Put on stage" and Run would fetch the source), and a `true` anywhere wins.
  const stale = normalizeShelf({ shaders: [{ id: "4s23zz", title: "Warping", study_only: false }] }, atlas, ROUTES).entries[0];
  check("a stale study_only false in the index loses to the atlas's true", stale.studyOnly === true && stale.images.poster.length === 0);
  const camel = normalizeShelf({ shaders: [{ id: "4s23zz", studyOnly: false, study_only: false }] }, atlas, ROUTES).entries[0];
  check("so does a stale camel-case false", camel.studyOnly === true);
  const byIndex = normalizeShelf({ shaders: [{ id: "zzzzz2", study_only: true }] },
    { loved: [{ id: "zzzzz2", study_only: false }] }, ROUTES).entries[0];
  check("the index's true beats the atlas's false", byIndex.studyOnly === true);
  const byGroup = normalizeShelf({ shaders: [{ id: "zzzzz1", study_only: false }] },
    { loved: [{ id: "zzzzz1", study_only: false }], groups: [{ name: "g", study_only: ["zzzzz1"] }] }, ROUTES).entries[0];
  check("a group's study_only list is a source too", byGroup.studyOnly === true);
  check("the atlas fallback keeps it", shelfFromAtlas(atlas, ROUTES).entries.find((e) => e.id === "4s23zz").studyOnly === true);

  // Stand-in inputs: the Shelf index carries what each render substituted (a texture the corpus lacks, silent audio).
  const subbed = normalizeShelf({ shaders: [{ id: "ltffzl", title: "Heartfelt", renders: { status: "rendered",
    stills: [{ t: 1, url: "/renders/ltffzl/t1.00.png" }], warm_ms: 2.7,
    substituted: [{ src: "/media/a/abc123.png", kind: "texture", reason: "load failed: procedural stand-in", style: "noise" },
      { src: "/media/a/abc123.png", kind: "texture", reason: "load failed: procedural stand-in", style: "noise" },
      { src: "music", kind: "audio", reason: "no audio fed: silence" }] } }] }, atlas, ROUTES).entries[0];
  eq("stand-ins are read from the index, once each", subbed.standIns.map((s) => s.kind), ["texture", "audio"]);
  // shelf.py's own shape: one list per receipt ({stills, filmstrip}), the same stand-in usually in both.
  const tex = { src: "/media/a/cb49c0.png", kind: "texture", reason: "load failed: procedural stand-in", style: "noise" };
  const perReceipt = normalizeShelf({ shaders: [{ id: "lfscD7", renders: { status: "rendered",
    substituted: { stills: [tex], filmstrip: [tex, { src: "/media/a/x.mp3", kind: "audio", reason: "no audio fed: silence" }] } } }] },
  atlas, ROUTES).entries[0];
  eq("shelf.py's per-receipt lists are read and merged, once each", perReceipt.standIns.map((s) => [s.kind, s.src]),
    [["texture", "/media/a/cb49c0.png"], ["audio", "/media/a/x.mp3"]]);
  eq("an empty per-receipt block is no stand-ins", normalizeShelf({ shaders: [{ id: "ldSfWV",
    renders: { substituted: { stills: [], filmstrip: [] } } }] }, atlas, ROUTES).entries[0].standIns, []);
  eq("the SwiftShader warm ms rides along as a second cost signal", subbed.swiftshader, { warmMs: 2.7, size: null });
  eq("an entry with no stand-ins has none", [aur.standIns, aur.swiftshader], [[], null]);
  const withSize = normalizeShelf({ shaders: [{ id: "lfscD7", renders: { timings: { warm_ms: 125.8 }, request: { w: 480, h: 270 } } }] },
    atlas, ROUTES).entries[0];
  eq("the warm ms and its size from a receipt-shaped renders block", withSize.swiftshader, { warmMs: 125.8, size: [480, 270] });

  // The flipbook steps a window over the contact sheet render.py draws (4 columns, 6 px gaps, a 26 px header).
  const geo = sheetFrame(0, 8), geo5 = sheetFrame(5, 8);
  eq("sheet frame 0 sits under the header", [geo.x, geo.y, geo.w, geo.h], [6, 32, 1310, 404]);
  eq("sheet frame 5 is row 2, column 2", [geo5.x, geo5.y], [6 + 326, 32 + 186]);

  const teach = teachesFor(atlas, "ttScDc");
  const wantGroups = atlas.groups.filter((g) => (g.exemplars || []).includes("ttScDc")).map((g) => g.name);
  eq("what it teaches: the groups it exemplifies", teach.groups.map((g) => g.name), wantGroups);
  check("what it teaches: some parts", teach.parts.length > 0);

  const doc = fakeDocument();
  const root = doc.createElement("section");
  const opened = [], tagged = [];
  const fetch = fakeFetch({ "/study/ttScDc.md": "# Study: AURORA (ttScDc)\n\n- **Name:** AURORA\n\n## 3. How it works\n\nImagine a **glass tank**.\nIt glows.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n" });
  const timers = [];
  const shelf = mountShelf(doc, root, { routes: ROUTES, fetch, onStage: (e) => opened.push(e.id), onTag: (c) => tagged.push(c),
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length; }, clearTimeout: () => {} });
  shelf.setEntries(norm.entries);
  const cards = byClass(root, "wb-shelf-card");
  eq("one card per entry", cards.length, 3);
  const sprite = byClass(cards[0], "wb-sprite")[0];
  check("a card with a contact sheet has a flipbook, and loads nothing for it before a hover", sprite && !sprite.style.backgroundImage);
  const mediaEl = byClass(cards[0], "wb-shelf-media")[0];
  mediaEl.fire("pointerenter");
  check("hover plays the flipbook from the sheet", hasClass(sprite, "is-playing") && /filmstrip\.png/.test(sprite.style.backgroundImage)
    && sprite.style.backgroundPosition === "-12px -64px", sprite.style.backgroundPosition);
  timers.at(-1).fn();
  check("the next step moves one cell right", sprite.style.backgroundPosition === "-664px -64px", sprite.style.backgroundPosition);
  mediaEl.fire("pointerleave");
  check("leaving stops it", !hasClass(sprite, "is-playing"));
  const imgs = (card) => findAll(card, (el) => el.tagName === "IMG");
  check("a study-only card has no image", imgs(cards[1]).length === 0 && /study only/i.test(textOf(cards[1])));
  check("a card with renders shows one", imgs(cards[0]).length === 1);
  check("no image loads eagerly", imgs(cards[0]).every((i) => i.loading === "lazy"));
  const badge = byClass(cards[0], "wb-licence")[0];
  check("licence badge names the licence", badge && /MIT/.test(textOf(badge)) && hasClass(badge, "is-permissive"));
  const rootS = doc.createElement("section");
  mountShelf(doc, rootS, { routes: ROUTES, fetch }).setEntries([subbed, aur]);
  const standins = byClass(rootS, "wb-standin");
  eq("a stand-in badge on the card whose renders used stand-ins, and only there", standins.length, 1);
  check("the badge says stand-in inputs", standins[0] && /stand-in inputs/.test(textOf(standins[0])));
  check("its hover lists them", standins[0] && /texture/.test(standins[0].title) && /audio/.test(standins[0].title)
    && /silence/.test(standins[0].title) && standins[0].title.split("abc123").length === 2, standins[0] && standins[0].title);
  const many = normalizeShelf({ shaders: [{ id: "XtyXzW", title: "Glitch", tags: ["a.1", "a.2", "a.3", "a.4", "a.5", "a.6", "a.7", "a.8", "a.9"] }] }, atlas, ROUTES).entries;
  const root3 = doc.createElement("section");
  mountShelf(doc, root3, { routes: ROUTES, fetch }).setEntries(many);
  const more = byClass(root3, "wb-more")[0];
  eq("a card shows at most six tags, the rest folded into +N", [byClass(root3, "wb-tag").length, more ? textOf(more).trim() : null], [6, "+3"]);
  const studyAside = byClass(root, "wb-study")[0];
  check("the study column stays closed until a note is opened", studyAside.hidden === true);
  const tagBtn = byClass(cards[0], "wb-tag")[0];
  tagBtn.fire("click");
  eq("a tag links into the library tree, on the category the Shelf placed it", tagged, ["E3"]);
  byClass(cards[0], "wb-stage-btn")[0].fire("click");
  eq("put on stage", opened, ["ttScDc"]);

  // The study note: plain text paragraphs (never parsed as HTML).
  const blocks = studyBlocks("# Title\n\nA **bold** line\nwrapped.\n\n- one\n- two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n<script>x</script>\n");
  eq("study blocks", blocks.map((b) => b.kind), ["heading", "para", "list", "table", "para"]);
  eq("emphasis marks are dropped, lines joined", blocks[1].text, "A bold line wrapped.");
  eq("markup stays text", blocks[4].text, "<script>x</script>");
  byClass(cards[0], "wb-study-btn")[0].fire("click");
  await settle();
  const note = byClass(root, "wb-study")[0];
  check("the study panel shows the note's words", note && /glass tank/.test(textOf(note)) && !/\*\*/.test(textOf(note)));
  check("opening a note opens its column", note.hidden === false && hasClass(byClass(root, "wb-shelf-layout")[0], "has-study"));
  byClass(note, "wb-study-close")[0].fire("click");
  check("and Close puts the column away", note.hidden === true && !hasClass(byClass(root, "wb-shelf-layout")[0], "has-study"));
  check("the study note is never innerHTML", findAll(root, (el) => "innerHTML" in el).length === 0);

  // With no shelf index, the 42 loved shaders still show, from the atlas, under an honest banner.
  const fb = shelfFromAtlas(atlas, ROUTES);
  eq("fallback lists the 42 loved", fb.entries.length, 42);
  eq("fallback source", fb.source, "atlas");
  const root2 = doc.createElement("section");
  const shelf2 = mountShelf(doc, root2, { routes: ROUTES, fetch: fakeFetch() });
  shelf2.setEntries(fb.entries, { route: "/shelf/index.json", why: "HTTP 404" });
  check("fallback banner says not available yet", /not available yet/i.test(textOf(root2)) && textOf(root2).includes("/shelf/index.json"));
  eq("fallback cards", byClass(root2, "wb-shelf-card").length, 42);
}

// ============================================================================ stage: the cost-class gate --
{
  eq("C0..C2 run at full scale", ["C0", "C1", "C2"].map((c) => costGate(c).scale), [1, 1, 1]);
  eq("C3 and C4 start at half scale", ["C3", "C4"].map((c) => costGate(c).scale), [0.5, 0.5]);
  const unknown = costGate(null);
  check("an unknown cost is treated as heavy, and says so", unknown.scale === 0.5 && !unknown.known && /unknown/i.test(unknown.label));
  check("the label names the class", /C3/.test(costGate("C3").label) && /C1/.test(costGate("C1").label));
  eq("buffers make a shader stateful (C4)", costFloorFromShader({ renderpass: [{ type: "buffer" }, { type: "image" }] }), "C4");
  eq("a single image pass sets no floor", costFloorFromShader({ renderpass: [{ type: "image" }] }), null);

  // The watchdog: the avatar's count rule for light stutter, plus a TIME budget, because Windows resets the GPU when one
  // frame runs about 2 s, and 45 frames of 1 to 2 s each would be 45 to 90 s of exactly that.
  const w = createWatchdog();
  eq("watchdog: the avatar's count rule, a time budget and a one-frame limit",
    [WATCHDOG.slowMs, WATCHDOG.trip, WATCHDOG.budgetMs, WATCHDOG.gapMs], [55, 45, 2500, 500]);
  let t = 0, r = w.tick(t);
  for (let i = 0; i < WATCHDOG.trip - 1; i++) { t += 55.5; r = w.tick(t); }
  check("44 slow frames of 55.5 ms do not trip", !r.tripped && r.streak === WATCHDOG.trip - 1);
  t += 16; r = w.tick(t);
  check("an on-time frame resets the streak and its sum", r.streak === 0 && w.streakMs === 0 && !r.tripped);
  for (let i = 0; i < WATCHDOG.trip; i++) { t += 55.5; r = w.tick(t); }
  check("45 slow frames in a row trip on the count (2497 ms, under the budget)", r.tripped && w.tripped && w.reason === "count", w.reason);
  w.reset();
  check("reset clears the verdict, its reason and the sum", !w.tripped && w.reason === null && w.streakMs === 0);
  t = 0; w.tick(t);
  let heavyFrames = 6;
  while (heavyFrames--) { t += 400; r = w.tick(t); }
  check("six 400 ms frames (2400 ms) do not trip", !r.tripped && w.streakMs === 2400, String(w.streakMs));
  t += 400; r = w.tick(t);
  check("the seventh trips on the time budget (2800 ms), not after 45 frames", r.tripped && w.reason === "budget" && w.streakMs === 2800);
  w.reset(); w.tick(0); r = w.tick(500);
  check("one 500 ms frame alone does not trip", !r.tripped);
  w.reset(); w.tick(0); r = w.tick(600);
  check("one frame over 500 ms trips at once", r.tripped && w.reason === "gap" && w.worst === 600);
  w.reset(); w.tick(0); r = w.tick(1500);
  check("a 1.5 s frame, near the GPU reset, trips on its first gap", r.tripped && w.reason === "gap");
}

// ========================================================= stage: the pre-flight, before any full-size frame --
{
  eq("pre-flight constants: a 64 x 36 frame, refused over 200 ms, a 30 ms budget",
    [PREFLIGHT.w, PREFLIGHT.h, PREFLIGHT.refuseMs, PREFLIGHT.budgetMs], [64, 36, 200, 30]);
  const base = { tinyPx: 64 * 36, fullPx: 64 * 36 * 100 };   // the full frame has 100 times the pixels
  // The choice of scale, with a cost proven linear: a second reading at four times the pixels and four times the time,
  // read exactly (no timer uncertainty), so the prediction is the tiny time times the pixel ratio. (One reading alone
  // is taken at the heaviest growth: the third round's pins, below.)
  const lin = (tinyMs) => ({ tinyMs, secondMs: tinyMs * 4, secondPx: 64 * 36 * 4, resolutionMs: 0 });
  let p = preflightPlan({ ...base, ...lin(0.1), classScale: 1 });
  eq("light: full scale (10 ms predicted)", [p.ok, p.scale, p.predictedFullMs, p.predictedMs], [true, 1, 10, 10]);
  eq("never above the class default", preflightPlan({ ...base, ...lin(0.1), classScale: 0.5 }).scale, 0.5);
  p = preflightPlan({ ...base, ...lin(1), classScale: 1 });
  eq("100 ms predicted at full scale starts at half (25 ms)", [p.scale, p.predictedMs], [0.5, 25]);
  p = preflightPlan({ ...base, ...lin(4), classScale: 1 });
  eq("400 ms predicted starts at a quarter (25 ms)", [p.scale, p.predictedMs, p.overBudget], [0.25, 25, false]);
  eq("the prediction at every scale is kept for the receipt", p.perScale.map((x) => [x.scale, x.ms]),
    [[0.25, 25], [0.5, 100], [0.75, 225], [1, 400]]);
  p = preflightPlan({ ...base, ...lin(10), classScale: 0.5 });
  check("over the budget even at a quarter, under the one-frame limit: the smallest scale, marked over budget",
    p.ok && p.scale === 0.25 && p.overBudget && p.predictedMs === 62.5, JSON.stringify(p));
  p = preflightPlan({ ...base, ...lin(100), classScale: 0.5 });
  check("a first frame predicted past the watchdog's 500 ms limit even at a quarter is refused", !p.ok && /500 ms/.test(p.refused), p.refused);
  p = preflightPlan({ ...base, tinyMs: 250, classScale: 0.5 });
  check("a tiny frame alone over 200 ms is refused", !p.ok && /200 ms/.test(p.refused) && p.scale === null, p.refused);

  // On the stage, with frames that cost time in proportion to their pixels (4 ms at 64 x 36: 400 ms for the 640 x 360 box).
  const doc = fakeDocument();
  const root = doc.createElement("section");
  const clock = fakeClock();
  const rt = fakeRuntime(undefined, { clock });
  const receipts = [];
  const timers = [];
  const stage = mountStage(doc, root, {
    loadRuntime: async () => rt.module, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
    isHidden: () => false, onReceipt: (r) => receipts.push(r), env: LIVE_ON,
    setTimeout: (fn) => { timers.push(fn); return timers.length; }, clearTimeout: () => {},
  });
  const subject = (cost, extra = {}) => ({ kind: "shelf", id: "lfscD7", title: "Hex Glitch", cost, poster: [],
    swiftshader: { warmMs: 125.8, size: [480, 270] },
    load: async () => ({ shader: { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] } }),
    ...extra });
  const perPixel = (tinyMs) => (w, h) => w * h * (tinyMs / 2304);
  rt.log.cost = perPixel(4);
  stage.setSubject(subject("C2"));
  check("before the click, the cost line shows the SwiftShader warm ms as a second signal",
    /125\.8 ms/.test(textOf(root)) && /SwiftShader/.test(textOf(root)) && /480 × 270/.test(textOf(root)));
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("the pre-flight draws one 64 x 36 frame before any other", [rt.log.resizes[0], rt.log.sizes[0]], [[64, 36], [64, 36]]);
  check("timed through gl.finish", rt.log.finishes >= 1);
  eq("the toy is reset after the pre-flight, so the live run starts at frame 0", rt.log.resets, 1);
  eq("then it starts at the scale the prediction allows: a quarter, 160 x 90", rt.log.resizes.at(-1), [160, 90]);
  const pf = receipts.at(-1).preflight;
  // 4 and 16 ms, each read once (0.1 ms of timer each), less a per-frame cost measured at 0 ms (over 8 draws: 0.0125 ms
  // of timer), allow growth up to log(16.0875 / 3.8875) / log 4 = 1.025 (shown 1.03). The prediction is the per-frame
  // cost at its most (0.0125 ms) plus the 128 x 72 reading's work at its most: 16.1 ms (the reading at its most, less
  // the per-frame cost at its least, 0; the fourth round), grown to the full frame's 25 times the pixels at that, 435.6
  // ms; at a quarter, 25.4 ms (the frame: 25).
  check("the receipt holds the measured numbers", pf && pf.ms === 4 && pf.predictedFullMs === 435.6 && pf.scale === 0.25
    && pf.predictedMs === 25.4 && pf.size[0] === 64 && pf.fullSize[0] === 640 && pf.exponent === 1.03, JSON.stringify(pf));
  check("and the stage says them", /64 × 36/.test(textOf(root)) && /\b4 ms/.test(textOf(root)) && /128 × 72 one 16 ms/.test(textOf(root))
    && /435\.6 ms/.test(textOf(root)), textOf(byClass(root, "wb-cost-row")[0]));
  eq("the receipt keeps the SwiftShader signal", receipts.at(-1).swiftshader, { warmMs: 125.8, size: [480, 270] });
  clock.pump(16); clock.pump(16);
  check("it runs at the chosen scale", rt.log.sizes.at(-1)[0] === 160 && stage.state().running);

  // Knob rebuilds are pre-flighted too: a rebuilt program that fails it is never swapped in.
  stage.setSubject(subject("C2", { acceptsParams: true }));
  rt.log.cost = perPixel(0.01);
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  const destroyedBefore = rt.log.destroyed;
  rt.log.cost = () => 250;
  stage.setParams({ values: { gain: 9 }, descriptors: [] });
  await timers.at(-1)();
  await settle();
  eq("a rebuild that fails the pre-flight is freed; the running program stays", [rt.log.destroyed - destroyedBefore, stage.state().live], [1, true]);
  check("and the stage says why", /pre-flight/i.test(textOf(byClass(root, "wb-stage-status")[0])) && /250 ms/.test(textOf(root)));
  rt.log.cost = perPixel(0.5);   // 50 ms at 1 x: over Run's budget, under the one-frame limit
  stage.setParams({ values: { gain: 2 }, descriptors: [] });
  await timers.at(-1)();
  await settle();
  // 0.5 and 2 ms allow growth up to 1.09, which puts 0.75 x at 37 ms (its frames: 28.1) and 0.5 x at 15.3 ms.
  eq("a rebuild is held to Run's own 30 ms budget: 50 ms at 1 x is swapped in at 0.5 x (15.3 ms predicted), not 1 x", stage.state().scale, 0.5);
  rt.log.cost = perPixel(10);    // 1000 ms at 1 x
  stage.setParams({ values: { gain: 3 }, descriptors: [] });
  await timers.at(-1)();
  await settle();
  eq("a rebuild predicted past the limit at this scale is swapped in at a scale the pre-flight allows", stage.state().scale, 0.25);
  rt.log.cost = null;

  // A pump that keeps the longest gap it saw: no frame past the one-frame limit may ever be drawn.
  let worst = 0;
  const pumpN = (n) => { for (let left = n; left > 0; left -= 1) { const a = clock.now(); clock.pump(16); worst = Math.max(worst, clock.now() - a); } };

  // Over budget at every scale: the smallest, said plainly. Raising is a LADDER: only after frames have been measured
  // at the current scale, one step at a time, each predicted from the slowest recent frame, and never past the
  // ladder's step cap (150 ms, well below the 500 ms one-frame limit).
  stage.setSubject(subject("C3"));
  rt.log.cost = perPixel(10);
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("over budget everywhere: the smallest scale", rt.log.resizes.at(-1), [160, 90]);
  check("the stage says it is over the budget", /over the 30 ms budget/.test(textOf(root)), textOf(byClass(root, "wb-stage-status")[0]));
  const options = findAll(root, (el) => el.tagName === "OPTION");
  eq("before any frame is measured, no larger scale can be chosen", options.map((o) => o.disabled), [false, true, true, true]);
  stage.setScale(0.5);
  eq("a raise before frames are measured at this scale is refused", stage.state().scale, 0.25);
  check("and says to let it draw first", /let it draw/i.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  pumpN(8);   // 160 x 90 frames: 62.5 ms each, 78.5 ms apart
  // A 10 ms tiny frame could make a 640 ms 128 x 72 one at the cube, so its second reading is at 90 x 51 (19.9 ms; the
  // fourth round). 10 and 19.9 ms read once each allow growth up to 1.03 (shown): 78.5 ms grown to four times the
  // pixels at that is 327.3 ms.
  eq("the next step stays shut: 0.5 x would be about 327 ms by the frames drawn now, past the 150 ms step cap",
    options.map((o) => o.disabled), [false, true, true, true]);
  stage.setScale(1);
  eq("a raise past the step cap is refused", stage.state().scale, 0.25);
  check("and says by what: the slowest recent frame, grown to the step's pixels, against the cap",
    /0\.5 × would take about 327\.3 ms a frame by the frames drawn at 0\.25 × \(the slowest of the last \d+ took 78\.5 ms\), past the ladder's 150 ms step cap/
      .test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  rt.log.cost = null;

  // A climb: 0.5 ms at 64 x 36 is 12.5 ms a frame at 0.5 x.
  stage.setSubject(subject("C3"));
  rt.log.cost = perPixel(0.5);
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("a light C3 subject starts at its class's half scale", [stage.state().scale, stage.state().canvas], [0.5, [320, 180]]);
  pumpN(8);   // 320 x 180: 12.5 ms each, 28.5 ms apart
  eq("the next step opens (0.75: about 69 ms by the frames drawn now, at the growth its readings allow); past it stays shut",
    options.map((o) => o.disabled), [false, false, false, true]);
  const resetsBeforeStep = rt.log.resets;
  stage.setScale(1);
  eq("a raise to 1 x goes one step, to 0.75", [stage.state().scale, stage.state().canvas], [0.75, [480, 270]]);
  check("and says it is one step at a time", /one step at a time/i.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  eq("the step is a size change: the pre-flight ran again at the new size before its first frame", rt.log.resets, resetsBeforeStep + 1);
  pumpN(8);   // 480 x 270: 28.1 ms each, 44.1 ms apart
  stage.setScale(1);
  eq("then 1 x (about 82.6 ms by the frames drawn now)", stage.state().scale, 1);
  stage.setScale(0.25);
  eq("lowering is always allowed", stage.state().scale, 0.25);
  rt.log.cost = null;

  // The pre-flight's second, larger tiny frame (128 x 72) catches a cost that grows faster than the pixels: here the
  // square of them, 0.5 ms at 64 x 36 and about 5 s at the full 640 x 360, which one tiny frame would put at 50 ms. The
  // stage averages a reading under 1 ms over several draws, so the timer's 0.1 ms ticks are a fortieth of it here.
  // The exponent is the MOST growth the two readings allow: each is uncertain by the timer's resolution over the draws
  // averaged, so the larger at the top of its uncertainty over the smaller at the bottom of its, log((8 + 0.025) /
  // (0.5 - 0.025)) / log 4 = 2.039 here (shown 2.04), a little above the true 2 and never below it. The prediction grows
  // 8.025 ms at that: 5691.1 ms for the full frame (its true 5000), 19.9 ms at a quarter (its true 19.5).
  p = preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, secondMs: 8, secondPx: 9216, classScale: 1, resolutionMs: 0.025 });
  eq("two points: the most growth they allow and the prediction it makes", [p.exponent, p.predictedFullMs, p.scale, p.predictedMs], [2.04, 5691.1, 0.25, 19.9]);
  eq("one point alone shows no growth and is taken at the heaviest (0.6 ms, the reading at the top of its uncertainty, times the pixel ratio cubed); a flat second proves the spec's linear tiny-time-times-pixel-ratio",
    [preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, classScale: 1 }).predictedFullMs,
      preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, secondMs: 1, secondPx: 9216, classScale: 1 }).predictedFullMs], [600000, 50]);
  eq("the same two readings taken once each (0.1 ms ticks) allow up to 2.17, and that is what is used",
    [preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, secondMs: 8, secondPx: 9216, classScale: 1 }).exponent,
      preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, secondMs: 8, secondPx: 9216, classScale: 1 }).predictedFullMs > 5000], [2.17, true]);
  stage.setSubject(subject("C2"));
  rt.log.cost = (w, h) => 0.5 * ((w * h) / 2304) ** 2;
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  const pfq = receipts.at(-1).preflight;
  // 0.5 ms averaged over 4 draws (0.025 ms of timer) and 8 ms read once (0.1), less a per-frame cost measured at 0 ms
  // (0.0125 ms of timer): up to log(8.0875 / 0.4625) / log 4 = 2.064 (shown 2.07).
  check("on the stage: averaged readings, a second frame at 128 x 72, the most growth they allow (2.07), and a start at a quarter",
    pfq.second && pfq.second.size[0] === 128 && pfq.second.ms === 8 && pfq.reps > 1 && pfq.exponent === 2.07 && stage.state().scale === 0.25, JSON.stringify(pfq));
  pumpN(8);   // 160 x 90: 19.5 ms each, 35.5 ms apart
  stage.setScale(1);
  eq("its ladder stops at a quarter: the frames drawn now, grown at that exponent, put 0.5 x at 626.4 ms", stage.state().scale, 0.25);
  check("and says so", /0\.5 × would take about 626\.4 ms a frame/.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));

  // A cost that grows after the first frame (a shader whose buffers fill, as ldSfWV did on SwiftShader): the pre-flight
  // sees the cheap first frame; the ladder sees the frames drawn now.
  stage.setSubject(subject("C3"));
  rt.log.cost = perPixel(0.05);
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("a cheap first frame starts it at the class's half scale", stage.state().scale, 0.5);
  rt.log.cost = perPixel(10);   // 250 ms frames at 320 x 180 from now on
  pumpN(8);
  stage.setScale(0.75);
  eq("0.75 x is refused though the pre-flight said 2.9 ms: the frames drawn now predict about 633.5 ms", stage.state().scale, 0.5);
  check("and says from what", /frames drawn at 0\.5 ×/.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  check("no frame past the one-frame limit was drawn in all of this (a jump to 1 x would have been 5 s)", worst < WATCHDOG.gapMs, String(worst));
  rt.log.cost = null;

  // Refused: a tiny frame over 200 ms. (A refusal is remembered for its subject, so each refused one has its own id.)
  stage.setSubject(subject("C4", { id: "refus1" }));
  check("a new subject enables every scale again", findAll(root, (el) => el.tagName === "OPTION").every((o) => !o.disabled));
  rt.log.cost = () => 250;
  const renders0 = rt.log.renders, shaded0 = rt.log.shaded, destroyed0 = rt.log.destroyed;
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("refused: one frame shaded pixels, the tiny one (after one draw that shades none)",
    [rt.log.shaded - shaded0, rt.log.renders - renders0], [1, 2]);
  check("refused: the toy is freed and no canvas is on stage",
    rt.log.destroyed === destroyed0 + 1 && findAll(root, (el) => el.tagName === "CANVAS").length === 0);
  eq("refused: no animation frame is queued", clock.pending(), 0);
  const btnR = byClass(root, "wb-run")[0];
  check("refused: the button says so and cannot be pressed", btnR.disabled && /refused/i.test(textOf(btnR)), textOf(btnR));
  check("refused: the stage names the numbers", /250 ms/.test(textOf(root)) && /200 ms/.test(textOf(root)));
  check("refused: a receipt says what was measured", receipts.at(-1).preflight.refused && receipts.at(-1).preflight.ms === 250);
  await stage.run();
  eq("refused: run() does nothing more", rt.log.renders - renders0, 2);

  // A driver that compiles at the first draw: the compile lands on the one-pixel warm-up draw, not on the timed frame.
  stage.setSubject(subject("C2", { id: "cold01" }));
  rt.log.cost = perPixel(4);
  rt.log.coldMs = 300;
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  const pfc = receipts.at(-1).preflight;
  check("a 300 ms first-draw compile is not billed to the tiny frame: 4 ms timed, not refused",
    pfc && pfc.ms === 4 && pfc.compileMs === 300 && !pfc.refused && stage.state().running, JSON.stringify(pfc));
  rt.log.coldMs = 0;

  // Refused: predicted past the one-frame limit even at a quarter (100 ms at 64 x 36 is 625 ms at 160 x 90).
  stage.setSubject(subject("C4", { id: "refus2" }));
  rt.log.cost = perPixel(100);
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  check("a frame predicted past 500 ms even at a quarter is refused",
    byClass(root, "wb-run")[0].disabled && /500 ms/.test(textOf(root)) && findAll(root, (el) => el.tagName === "CANVAS").length === 0);
  rt.log.cost = null;
}

// =================================================================== stage: nothing renders live on load --
{
  const doc = fakeDocument();
  const root = doc.createElement("section");
  const clock = fakeClock();
  const rt = fakeRuntime(undefined, { clock });
  let loads = 0, hidden = false;
  const visListeners = [];
  const receipts = [];
  const stage = mountStage(doc, root, {
    loadRuntime: async () => { loads++; return rt.module; },
    raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
    isHidden: () => hidden, onVisibilityChange: (fn) => visListeners.push(fn),
    onReceipt: (r) => receipts.push(r), env: LIVE_ON,
  });
  check("an empty stage says what it is for", /nothing on stage|pick/i.test(textOf(root)));
  let subjectLoads = 0;
  const subject = (cost, id = "ttScDc") => ({
    kind: "shelf", id, title: "AURORA", byline: "alro", licence: "MIT (explicit)", cost,
    poster: ["/renders/ttScDc/t1.00.png"],
    load: async () => { subjectLoads++; return { shader: { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] }, receipt: { subject: "ttScDc" } }; },
  });
  stage.setSubject(subject("C3"));
  await settle();
  eq("on load: no runtime loaded, no subject fetched", [loads, subjectLoads], [0, 0]);
  eq("on load: no canvas, no WebGL context, no animation frame", [doc.canvases, doc.getContextCalls, clock.rafCalls], [0, 0, 0]);
  const btn = byClass(root, "wb-run")[0];
  check("the run button names the cost class before the click", btn && /C3/.test(textOf(btn)) && /GPU/i.test(textOf(btn)));
  check("the poster is a pre-rendered still", findAll(root, (el) => el.tagName === "IMG" && el.src === "/renders/ttScDc/t1.00.png").length === 1);

  btn.fire("click");
  await settle();
  eq("the click loads the runtime once and the subject once", [loads, subjectLoads, rt.log.created], [1, 1, 1]);
  eq("C3 starts at half scale: canvas is half the box", rt.log.resizes.at(-1), [320, 180]);
  check("a frame is requested only after the click", clock.rafCalls >= 1);
  clock.pump(16); clock.pump(16); clock.pump(16);
  check("frames render while running", rt.log.renders >= 3, String(rt.log.renders));
  check("the receipt names the renderer and the scale",
    receipts.length >= 1 && receipts.at(-1).renderer === "Fake GPU renderer" && receipts.at(-1).scale === 0.5);

  eq("the first frame is the pre-flight's, at 64 x 36", rt.log.sizes[0], [64, 36]);
  check("the receipt carries the pre-flight", receipts.at(-1).preflight && receipts.at(-1).preflight.scale === 0.5);

  // A hidden tab STOPS the stage: zero work, and coming back does not restart it (an explicit click does), with iTime
  // continuing where it stopped.
  const tBefore = rt.log.lastTime;
  hidden = true; visListeners.forEach((f) => f());
  const before = rt.log.renders;
  clock.pump(16); clock.pump(16);
  eq("hidden: no renders and no frames queued", [rt.log.renders - before, clock.pending()], [0, 0]);
  clock.spend(5000);
  hidden = false; visListeners.forEach((f) => f());
  clock.pump(16); clock.pump(16);
  eq("visible again: no auto-resume", [rt.log.renders - before, clock.pending()], [0, 0]);
  check("the stage says Run continues it", /press run/i.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  const again = byClass(root, "wb-run")[0];
  check("the button still names the cost class and the scale", /C3/.test(textOf(again)) && /half scale/.test(textOf(again)) && !again.disabled, textOf(again));
  again.fire("click");
  await settle();
  clock.pump(16);
  check("Run resumes it", rt.log.renders > before);
  check("iTime continues from where it stopped, not 5 s later", rt.log.lastTime - tBefore < 0.1, `${tBefore} -> ${rt.log.lastTime}`);

  // The watchdog trips on slow frames (here their time budget) and holds the last frame (no more renders, canvas kept).
  for (let i = 0; i < WATCHDOG.trip + 2; i++) clock.pump(90);
  const held = rt.log.renders;
  clock.pump(16); clock.pump(16);
  eq("tripped: rendering stopped", rt.log.renders, held);
  check("tripped: the canvas is kept (the last frame holds)", findAll(root, (el) => el.tagName === "CANVAS").length === 1);
  check("tripped: the stage says why", /slow frames/i.test(textOf(root)) && /2500 ms/.test(textOf(root)), textOf(byClass(root, "wb-stage-status")[0]));
  eq("tripped: the toy is not destroyed (destroying would blank the frame)", rt.log.destroyed, 0);
  // Every hold steps down: Run again measures first and continues below the frames that held (a quarter here).
  check("tripped: the button names the cost and the lower scale Run again will use", /C3/.test(textOf(again)) && /quarter scale/.test(textOf(again)), textOf(again));

  // One frame near the GPU reset limit trips at once: run again, and every live frame now takes 700 ms.
  rt.log.cost = (w, h) => (isPf(w, h) ? 0 : 700);
  again.fire("click");
  await settle();
  const r0 = rt.log.renders;
  for (let i = 0; i < 4; i++) clock.pump(16);
  check("a 700 ms frame trips at once: one frame drawn, not 45", rt.log.renders - r0 === 1, String(rt.log.renders - r0));
  check("and the stage says how long it took", /one frame took 716 ms/.test(textOf(root)), textOf(byClass(root, "wb-stage-status")[0]));
  rt.log.cost = null;

  // A light subject runs at full scale; changing subject frees the old toy first. (AURORA was refused just now, at the
  // smallest scale, and a refusal is remembered for its subject: these are other shaders.)
  stage.setSubject(subject("C1", "Ms2XWc"));
  eq("changing subject destroys the running toy", rt.log.destroyed, 1);
  check("and puts the still back, no canvas", findAll(root, (el) => el.tagName === "CANVAS").length === 0);
  const btn2 = byClass(root, "wb-run")[0];
  check("the new button names C1", /C1/.test(textOf(btn2)));
  btn2.fire("click");
  await settle();
  eq("C1 runs at full scale", rt.log.resizes.at(-1), [640, 360]);
  clock.pump(16); clock.pump(16);
  const tStop = rt.log.lastTime;
  stage.stop();
  const afterStop = rt.log.renders;
  clock.pump(16);
  eq("stop stops", rt.log.renders, afterStop);
  check("after Stop the button still names the cost and the scale", /C1/.test(textOf(btn2)) && /full scale/.test(textOf(btn2)), textOf(btn2));
  clock.spend(3000);
  btn2.fire("click");
  await settle();
  clock.pump(16);
  check("Stop and Run again keep iTime continuous", rt.log.renders > afterStop && rt.log.lastTime - tStop < 0.1, `${tStop} -> ${rt.log.lastTime}`);
  stage.stop();

  // An unknown cost runs at half scale, and buffers found at load raise a light declaration to C4.
  stage.setSubject({ ...subject(null, "unkn01"), load: async () => ({ shader: { renderpass: [{ type: "buffer" }, { type: "image" }] } }) });
  check("unknown cost is named on the button", /unknown/i.test(textOf(byClass(root, "wb-run")[0])));
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("unknown starts at half scale", rt.log.resizes.at(-1), [320, 180]);
  stage.setSubject({ ...subject("C1", "buff01"), load: async () => ({ shader: { renderpass: [{ type: "buffer" }, { type: "image" }] } }) });
  byClass(root, "wb-run")[0].fire("click");
  await settle();
  eq("buffers found at load raise C1 to C4: half scale", rt.log.resizes.at(-1), [320, 180]);
  check("and the stage says the class was raised", /Raised to C4 at load/.test(textOf(root)));
}

// =========================================== stage: GPU-safety pins from the lab-safety review (2026-10-13) --
// Each pin reproduces one defect the review found, with the real stage.js, a fake document and a fake runtime whose
// frames cost time by their pixels (and, where the defect needs it, by their frame number). Each was seen failing on
// the stage as reviewed, before the fix.
{
  const PF_SIZES = PF_ALL;   // the pre-flight's frames; no live size in these pins is one
  const isLive = (e) => e.kind === "render" && !e.scissor && !PF_SIZES.has(`${e.w}x${e.h}`);
  // The invariant: every live frame is drawn at the size the stage last admitted (a receipt names it, with what the
  // pre-flight predicted there), and costs no more than that prediction. A frame at a size nothing measured, or above
  // what was measured, is listed.
  function unadmitted(log) {
    let admit = null;
    const bad = [];
    for (const e of log.events) {
      if (e.kind === "admit") { admit = e; continue; }
      if (!isLive(e)) continue;
      const ok = admit && Array.isArray(admit.size) && e.w === admit.size[0] && e.h === admit.size[1]
        && Number.isFinite(admit.predictedMs) && e.ms <= admit.predictedMs + 0.05;
      if (!ok) bad.push(`${e.w}x${e.h} iFrame ${e.iFrame} took ${Math.round(e.ms * 10) / 10} ms; admitted: `
        + (admit ? `${JSON.stringify(admit.size)} at ${admit.predictedMs} ms` : "nothing"));
    }
    return bad;
  }
  function rig({ cost = null, box = [640, 360], dpr = 1, overheadMs = 0, onePixelMs = null } = {}) {
    const doc = fakeDocument();
    [doc.boxW, doc.boxH] = box;
    const root = doc.createElement("section");
    const clock = fakeClock();
    const rt = fakeRuntime(undefined, { clock });
    rt.log.cost = cost;
    rt.log.overheadMs = overheadMs;
    rt.log.onePixelMs = onePixelMs;
    const timers = [], sizeFns = [], receipts = [];
    const r = { doc, root, clock, rt, timers, receipts, dpr, away: null, worst: 0 };
    r.stage = mountStage(doc, root, {
      loadRuntime: async () => rt.module, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => r.dpr,
      isHidden: () => false, isAway: () => r.away, env: LIVE_ON,
      onReceipt: (x) => { receipts.push(x); rt.log.events.push({ kind: "admit", size: x.size, predictedMs: x.preflight ? x.preflight.predictedMs : null }); },
      onResize: (fn) => { sizeFns.push(fn); return () => {}; },
      setTimeout: (fn) => { timers.push(fn); return timers.length; }, clearTimeout: () => {},
    });
    r.resized = () => sizeFns.forEach((f) => f());
    r.pump = (n, dt = 16) => { for (let i = 0; i < n; i++) { const a = clock.now(); clock.pump(dt); r.worst = Math.max(r.worst, clock.now() - a); } };
    r.run = async () => { byClass(root, "wb-run")[0].fire("click"); await settle(); };
    r.status = () => textOf(byClass(root, "wb-stage-status")[0]);
    r.liveFrames = () => rt.log.events.filter(isLive);
    return r;
  }
  const subject = (cost, extra = {}) => ({ kind: "shelf", id: "pinPin", title: "Pin", cost, poster: [],
    load: async () => ({ shader: { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] } }),
    ...extra });
  const perPx = (tinyMs) => (w, h) => w * h * (tinyMs / 2304);

  // ---- 1 (HIGH): the size the pre-flight measured is locked; a box or pixel-ratio change measures again first ----
  // 0.1 ms at 64 x 36: in the 320 x 180 box a full frame is 2.5 ms, so it starts at 1 x. The window is then maximised onto
  // a display of twice the pixel ratio: a box 6 times larger each way, 3840 x 2160 device pixels at 1 x (360 ms a frame).
  {
    const r = rig({ cost: perPx(0.1), box: [320, 180] });
    r.stage.setSubject(subject("C2"));
    await r.run();
    eq("pin 1: it starts at 1 x in the small box", [r.stage.state().scale, r.stage.state().canvas], [1, [320, 180]]);
    r.pump(10);
    const resets = r.rt.log.resets, shadedBefore = r.rt.log.shadedLog.length;
    r.doc.boxW = 1920; r.doc.boxH = 1080; r.dpr = 2;
    r.resized();
    const next = r.rt.log.shadedLog.slice(shadedBefore);
    check("pin 1: a resize mid-run stops drawing and runs the pre-flight again at the new size before any frame",
      r.rt.log.resets === resets + 1 && next.length > 0 && next.every((e) => PF_SIZES.has(`${e.w}x${e.h}`))
      && JSON.stringify((r.stage.state().preflight || {}).fullSize) === "[3840,2160]",
    JSON.stringify({ resets: r.rt.log.resets - resets, next: next.map((e) => `${e.w}x${e.h}`), pf: r.stage.state().preflight }));
    eq("pin 1: it then draws at the scale the new measurement allows: 0.25 x, 960 x 540 (22.5 ms)",
      [r.stage.state().scale, r.stage.state().canvas], [0.25, [960, 540]]);
    r.stage.setScale(0.75);   // as reviewed, a scale change re-sized to 0.75 of the new box (2880 x 1620, 202 ms) unmeasured
    r.pump(10);
    eq("pin 1: no live frame at a size the stage did not measure, nor above what it predicted there", unadmitted(r.rt.log), []);
    check("pin 1: no frame near the one-frame limit", r.worst < WATCHDOG.gapMs, String(r.worst));
  }
  {
    // The same growth with no event at all (a browser that sends none): the loop checks the size before every frame.
    const r = rig({ cost: perPx(0.1), box: [320, 180] });
    r.stage.setSubject(subject("C2"));
    await r.run();
    r.pump(5);
    r.doc.boxW = 1920; r.doc.boxH = 1080; r.dpr = 2;
    r.pump(6);
    eq("pin 1: with no resize event, the next frame finds the change and measures again",
      [(r.stage.state().preflight || {}).fullSize, r.stage.state().canvas], [[3840, 2160], [960, 540]]);
    eq("pin 1: and every live frame was one it measured", unadmitted(r.rt.log), []);
  }
  {
    // Between runs: Stop, the box grows six times each way and the pixel ratio doubles, then Run again.
    const r = rig({ cost: perPx(0.1), box: [320, 180] });
    r.stage.setSubject(subject("C2"));
    await r.run();
    r.pump(5);
    r.stage.stop();
    r.doc.boxW = 1920; r.doc.boxH = 1080; r.dpr = 2;
    const shadedBefore = r.rt.log.shadedLog.length;
    await r.run();
    r.pump(5);
    const after = r.rt.log.shadedLog.slice(shadedBefore);
    check("pin 1: Run again at a new size measures before its first frame",
      after.length > 0 && PF_SIZES.has(`${after[0].w}x${after[0].h}`), JSON.stringify(after.slice(0, 3)));
    eq("pin 1: and draws at the measured scale, every frame within the 30 ms budget",
      [r.stage.state().scale, r.liveFrames().every((e) => e.ms <= PREFLIGHT.budgetMs)], [0.25, true]);
    eq("pin 1: no unmeasured frame between runs", unadmitted(r.rt.log), []);
    // ... and the box shrinks back while stopped: Run again keeps the scale it had (fewer pixels than measured).
    r.stage.stop();
    r.doc.boxW = 320; r.doc.boxH = 180; r.dpr = 1;
    await r.run();
    r.pump(3);
    eq("pin 1: a smaller box keeps the scale (fewer pixels than were measured), measured all the same",
      [r.stage.state().scale, r.stage.state().canvas, unadmitted(r.rt.log)], [0.25, [80, 45], []]);
  }
  {
    // The ladder predicts a step from the pixels it would really draw: the box grew 4 times each way since the frames
    // were measured, so 0.75 x is 36 times their pixels, not 2.25 times.
    const r = rig({ cost: perPx(1), box: [400, 225] });
    r.stage.setSubject(subject("C4"));
    await r.run();
    eq("pin 1: a C4 subject starts at half scale here", r.stage.state().canvas, [200, 113]);
    r.pump(8);
    r.doc.boxW = 1600; r.doc.boxH = 900;
    r.stage.setScale(0.75);
    eq("pin 1: a raise after the box grew is refused by the real pixel count", r.stage.state().scale, 0.5);
    check("pin 1: and says so", /0\.75 × would take about \d+(\.\d)? ms/.test(r.status()) && /step cap/.test(r.status()), r.status());
    r.pump(6);
    eq("pin 1: the next frame measures the grown box first; nothing unmeasured is drawn", unadmitted(r.rt.log), []);
    check("pin 1: no frame near the one-frame limit (as reviewed: a 352 ms frame)", r.worst < WATCHDOG.gapMs, String(r.worst));
  }

  // ---- 2 (HIGH): the pre-flight times frame 0, the frame the live run starts on ----
  {
    // Frame 0 does a hundred times the work of any other (a shader that fills its buffers on its first frame).
    const r = rig({ cost: (w, h, f) => perPx(0.2)(w, h) * (f === 0 ? 100 : 1) });
    r.stage.setSubject(subject("C4"));
    await r.run();
    const pf = r.stage.state().preflight || {};
    check("pin 2: a shaded 64 x 36 pre-flight frame was frame 0", r.rt.log.shadedLog.some((e) => e.w === 64 && e.iFrame === 0), JSON.stringify(r.rt.log.shadedLog.slice(0, 4)));
    check("pin 2: the tiny reading is the slower of frame 0 and a later frame (20 ms, not 0.2)", pf.ms >= 20, JSON.stringify(pf));
    r.pump(4);
    eq("pin 2: the first live frame (frame 0) costs no more than predicted", unadmitted(r.rt.log), []);
  }

  // ---- 3 (MEDIUM): Run again after a one-frame hold does not draw at the same scale ----
  {
    // Frames at 320 x 180 or more take 900 ms from the third on; smaller ones are cheap.
    let heavy = false;
    const r = rig({ cost: (w, h) => (heavy && w * h >= 320 * 180 ? 900 : perPx(0.5)(w, h)) });
    r.stage.setSubject(subject("C4"));
    await r.run();
    eq("pin 3: starts at half scale", r.stage.state().canvas, [320, 180]);
    r.pump(3);
    heavy = true;
    r.pump(3);
    check("pin 3: one 900 ms frame holds at once", r.stage.state().tripped && r.stage.state().trip.reason === "gap", JSON.stringify(r.stage.state().trip));
    check("pin 3: the button names the lower scale Run again will use", /quarter scale/.test(textOf(byClass(r.root, "wb-run")[0])), textOf(byClass(r.root, "wb-run")[0]));
    const n = r.liveFrames().length;
    await r.run();
    r.pump(4);
    const again = r.liveFrames().slice(n);
    check("pin 3: Run again drew one step lower, never again at the scale that held", again.length > 0 && again.every((e) => e.w === 160 && e.h === 90),
      JSON.stringify(again.map((e) => `${e.w}x${e.h}`)));
    // At the smallest scale a one-frame hold is the end: nothing more runs for this subject.
    heavy = false;
    const r2 = rig({ cost: (w, h) => (heavy ? 900 : perPx(10)(w, h)) });
    r2.stage.setSubject(subject("C4"));
    await r2.run();
    eq("pin 3: a heavy subject starts at the smallest scale", r2.stage.state().scale, 0.25);
    r2.pump(2);
    heavy = true;
    r2.pump(3);
    const m = r2.rt.log.shadedLog.length;
    await r2.run();
    r2.pump(4);
    check("pin 3: a one-frame hold at the smallest scale refuses Run again", r2.rt.log.shadedLog.length === m
      && byClass(r2.root, "wb-run")[0].disabled, `${r2.rt.log.shadedLog.length - m} frames; ${textOf(byClass(r2.root, "wb-run")[0])}`);
  }

  // ---- 4 (MEDIUM): the ladder sees a periodic spike, and a step is capped well below the one-frame limit ----
  {
    check("pin 4: the ladder's step cap is well below the one-frame limit", Number.isFinite(LADDER.stepCapMs)
      && LADDER.stepCapMs * 3 <= WATCHDOG.gapMs, JSON.stringify(LADDER));
    let k = 0;
    // 12.5 ms frames at 0.25 x, and every 15th live frame 25 times that (312 ms): under the one-frame limit, so the
    // watchdog lets it pass; a step to 0.5 x would make it 1250 ms.
    const r = rig({ cost: (w, h) => { const base = perPx(2)(w, h); if (isPf(w, h)) return base; k++; return k % 15 === 0 ? base * 25 : base; } });
    r.stage.setSubject(subject("C4"));
    await r.run();
    eq("pin 4: starts at a quarter", r.stage.state().scale, 0.25);
    r.pump(30, 4);
    check("pin 4: the spikes did not trip the watchdog", !r.stage.state().tripped);
    r.stage.setScale(0.5);
    eq("pin 4: a raise is predicted from the slowest recent frame, not the median: refused", r.stage.state().scale, 0.25);
    check("pin 4: and the stage names the slowest frame", /316(\.\d)? ms/.test(r.status()) || /slowest/.test(r.status()), r.status());
  }

  // ---- 5 (MEDIUM-LOW): a knob change never draws outside the watched loop, lands in order, and meets Run's budget ----
  {
    // Held: a knob change draws nothing (as reviewed: a full frame at the scale that had just held, unwatched).
    let heavy = false;
    const r = rig({ cost: (w, h) => (heavy && !isPf(w, h) ? 700 : perPx(0.5)(w, h)) });
    r.stage.setSubject(subject("C2", { acceptsParams: true }));
    await r.run();
    r.pump(3);
    heavy = true;
    r.pump(3);
    check("pin 5: held", r.stage.state().tripped);
    const n = r.liveFrames().length;
    r.stage.setParams({ values: { gain: 2 }, descriptors: [] });
    for (const fn of r.timers.splice(0)) await fn();
    await settle();
    eq("pin 5: a knob change while held draws no frame", r.liveFrames().length - n, 0);
    check("pin 5: and says it applies at Run again", /run again/i.test(r.status()), r.status());
    // ... nor while the Shelf is in front.
    heavy = false;
    await r.run();
    r.pump(3);
    r.away = "you switched to the Shelf";
    r.pump(1);
    const n2 = r.liveFrames().length, created = r.rt.log.created;
    r.stage.setParams({ values: { gain: 3 }, descriptors: [] });
    for (const fn of r.timers.splice(0)) await fn();
    await settle();
    eq("pin 5: a knob change while away draws no frame", r.liveFrames().length - n2, 0);
    r.away = null;
    await r.run();
    r.pump(2);
    check("pin 5: Run again rebuilds with the new knob values first, then draws",
      r.rt.log.created === created + 1 && r.stage.state().running && r.liveFrames().length > n2,
      `${r.rt.log.created - created} built, running ${r.stage.state().running}`);
  }
  {
    // Two rebuilds in flight: the older one finishing last is never swapped in over the newer.
    let releaseA;
    const gateA = new Promise((ok) => { releaseA = ok; });
    const r = rig({ cost: perPx(0.1) });
    const loads = [];
    r.stage.setSubject(subject("C2", { acceptsParams: true, load: async (p) => {
      const v = p && p.values ? p.values.v : "first";
      loads.push(v);
      if (v === "A") await gateA;
      return { shader: { renderpass: [{ type: "image", code: `void mainImage(out vec4 c, in vec2 p){c=vec4(1);} // ${v}` }] }, receipt: { knob: v } };
    } }));
    await r.run();
    r.pump(2);
    r.stage.setParams({ values: { v: "A" }, descriptors: [] });
    const fireA = r.timers.at(-1)();
    await settle();
    r.stage.setParams({ values: { v: "B" }, descriptors: [] });
    await r.timers.at(-1)();
    await settle();
    releaseA();
    await fireA;
    await settle();
    eq("pin 5: overlapping rebuilds land in order: the newest knob value is on stage", r.receipts.at(-1).knob, "B");
  }
  {
    // A rebuild is held to Run's budget (30 ms), not the one-frame limit; and the program on stage finishes its queued
    // work before the rebuilt one's tiny frames are timed (they share one GPU).
    const r = rig({ cost: perPx(0.1) });
    r.stage.setSubject(subject("C2", { acceptsParams: true }));
    await r.run();
    eq("pin 5: a cheap program runs at 1 x", r.stage.state().scale, 1);
    r.pump(3);
    r.rt.log.cost = perPx(0.5);    // the knob makes it 50 ms at 1 x: over Run's budget, under the one-frame limit
    const mark = r.rt.log.events.length, toyBefore = r.rt.log.toys;
    r.stage.setParams({ values: { gain: 2 }, descriptors: [] });
    await r.timers.at(-1)();
    await settle();
    // 0.5 and 2 ms allow growth up to 1.09: 0.75 x at 37 ms (its frames: 28.1), 0.5 x at 15.3 ms.
    eq("pin 5: the rebuilt program starts within Run's 30 ms budget: 0.5 x (15.3 ms predicted), not 1 x (50 ms)", r.stage.state().scale, 0.5);
    const ev = r.rt.log.events.slice(mark);
    const firstTimed = ev.findIndex((e) => e.kind === "render" && e.toy === toyBefore + 1 && !e.scissor);
    check("pin 5: the program on stage was drained (gl.finish) before the rebuilt one's first timed frame",
      firstTimed > 0 && ev.slice(0, firstTimed).some((e) => e.kind === "finish" && e.toy === toyBefore), JSON.stringify(ev.slice(0, firstTimed + 1)));
  }

  // ---- 7 (LOW): the second pre-flight frame is not billed the buffers' reallocation, and a noisy reading does not
  // cap the whole run ----
  {
    const r = rig({ cost: perPx(2) });
    r.rt.log.reallocMs = 6;   // resizing to 128 x 72 queues 6 ms of reallocation
    r.stage.setSubject(subject("C2"));
    await r.run();
    const pf = r.stage.state().preflight || {};
    // 2 and 8 ms read once each, less a per-frame cost measured at 0 ms (0.0125 ms of timer), allow up to
    // log(8.0875 / 1.8875) / log 4 = 1.0496; billed the 6 ms reallocation (14 ms) they would allow up to 1.45.
    check("pin 7: the 128 x 72 frame reads its own 8 ms (the queue drained first), so the growth reads linear within the timer's resolution (1.05 at most)",
      pf.second && pf.second.ms === 8 && pf.exponent <= 1.05, JSON.stringify(pf.second) + " exponent " + pf.exponent);
  }
  {
    // Single readings near the timer's resolution cannot prove their growth, so the most they allow is used (third
    // round): log(1.7 / 0.1) / log 4 = 2.04 (shown 2.05) for the reviewer's 0.2 and 1.6 ms read once, above the 1.5 they
    // show at face value and never below what they could be. What keeps such a reading from capping the whole run is
    // the ladder below: it steps from the frames drawn now, and every step measures again.
    eq("pin 7: single readings near the timer's resolution are taken at the most growth they allow: 2.05, not the face value 1.5",
      preflightPlan({ tinyMs: 0.2, tinyPx: 2304, fullPx: 1260 * 708, classScale: 0.5, secondMs: 1.6, secondPx: 9216 }).exponent, 2.05);
    // A first pre-flight inflated once (a 25 ms tiny frame, as a stall would make it) puts 0.5 x past the one-frame
    // limit (625 ms); the live frames are cheap. The ladder steps from the frames drawn now and measures again at the step.
    let once = true;
    const r = rig({ cost: (w, h) => { if (once && w === 64) { once = false; return 25; } return perPx(0.2)(w, h); } });
    r.stage.setSubject(subject("C3"));
    await r.run();
    eq("pin 7: the inflated reading starts it at a quarter", r.stage.state().scale, 0.25);
    r.pump(8);
    r.stage.setScale(0.5);
    eq("pin 7: a step is still reachable: one inflated reading does not cap the whole run", r.stage.state().scale, 0.5);
    r.pump(4);
    eq("pin 7: and what it drew there was measured", unadmitted(r.rt.log), []);
  }

  // ---- 8: the pre-flight's wait is one the GPU must honour (found on SwiftShader while checking these fixes) ----
  {
    // A GPU that works behind the page, and a gl.finish() that returns at once: 2 ms at 64 x 36 is 8 ms at 128 x 72.
    const r = rig({ cost: perPx(2) });
    r.rt.log.asyncGpu = true;
    r.rt.log.finishWaits = false;
    r.stage.setSubject(subject("C2"));
    await r.run();
    const pf = r.stage.state().preflight || {};
    check("pin 8: with a gl.finish() that does not wait, a one-pixel read-back makes the tiny frames read their real cost",
      pf.ms === 2 && pf.second && pf.second.ms === 8 && r.rt.log.readbacks > 0, JSON.stringify({ ms: pf.ms, second: pf.second, readbacks: r.rt.log.readbacks }));
    eq("pin 8: so the start is the one the real cost allows (0.25 x: 12.5 ms), not full scale (200 ms)", r.stage.state().scale, 0.25);
  }
  {
    // A driver that skips a draw clipped to nothing before compiling (SwiftShader): the warm-up must shade one pixel,
    // or the 300 ms compile lands on the timed frame 0.
    const r = rig({ cost: perPx(4) });
    r.rt.log.coldMs = 300;
    r.rt.log.coldNeedsPixels = true;
    r.stage.setSubject(subject("C2"));
    await r.run();
    const pf = r.stage.state().preflight || {};
    check("pin 8: the one-pixel warm-up takes the compile: frame 0 reads 4 ms, not 304", pf.ms === 4 && pf.compileMs === 300,
      JSON.stringify({ ms: pf.ms, frame0Ms: pf.frame0Ms, compileMs: pf.compileMs }));
  }

  // =================================== the lab re-review's new defects (2026-10-13, second round), one pin each --
  // A cost that is cheap for the pre-flight's tiny frames and for the first `after` live frames, then `slowMs` a frame.
  const stallAfter = (after, slowMs, tinyMs = 0.3) => {
    let n = 0;
    return (w, h) => { if (isPf(w, h)) return perPx(tinyMs)(w, h); n += 1; return n > after ? slowMs : 8; };
  };
  const pumpUntil = (r, done, max = 200) => { for (let i = 0; i < max && r.stage.state().running && !done(); i++) r.pump(1); };
  const lastLiveMs = (r) => { const l = r.liveFrames(); return l.length ? l.at(-1).ms : 0; };

  // ---- re-review 1 (MEDIUM): the frame in flight is judged when the loop stops for anything but a hold ----
  {
    // Stop pressed during each stall (live frames take 1500 ms from the 21st on), then Run again, five times.
    const r = rig({ cost: stallAfter(20, 1500) });
    r.stage.setSubject(subject("C2"));
    await r.run();
    let firstStop = null;
    for (let c = 0; c < 5 && !r.stage.state().refused; c++) {
      pumpUntil(r, () => lastLiveMs(r) >= 1500);
      r.stage.stop();
      if (!firstStop) firstStop = { halted: r.stage.state().halted, trip: r.stage.state().trip };
      await r.run();
      r.pump(1);
    }
    const slow = r.liveFrames().filter((e) => e.ms >= 1500).length;
    check("re-review 1: Stop during a 1500 ms frame judges it: a hold for one frame over the limit, not a plain stop",
      firstStop && firstStop.halted === "tripped" && firstStop.trip && firstStop.trip.reason === "gap" && firstStop.trip.gapMs >= 1500,
      JSON.stringify(firstStop));
    check("re-review 1: and every such frame steps it down until refused: at most 2 over five Stop / Run again cycles (as reviewed: 6, never held)",
      slow <= 2 && !!r.stage.state().refused, `${slow} frames of 1500 ms; refused ${r.stage.state().refused}`);
  }
  {
    // The Shelf tab during the stall.
    const r = rig({ cost: stallAfter(20, 1500) });
    r.stage.setSubject(subject("C2"));
    await r.run();
    pumpUntil(r, () => lastLiveMs(r) >= 1500);
    r.away = "you switched to the Shelf";
    r.stage.suspend("you switched to the Shelf");
    check("re-review 1: the Shelf tab during a 1500 ms frame judges it too: held, not merely away",
      r.stage.state().halted === "tripped" && (r.stage.state().trip || {}).reason === "gap", JSON.stringify({ halted: r.stage.state().halted, trip: r.stage.state().trip }));
  }
  {
    // A knob change right after the stall: the rebuild would have stopped the loop and reset the watchdog unjudged.
    const r = rig({ cost: stallAfter(20, 1500) });
    r.stage.setSubject(subject("C2", { acceptsParams: true }));
    await r.run();
    pumpUntil(r, () => lastLiveMs(r) >= 1500);
    r.stage.setParams({ values: { gain: 2 }, descriptors: [] });
    for (const fn of r.timers.splice(0)) await fn();
    await settle();
    check("re-review 1: a knob change right after a 1500 ms frame judges it: held, and the knob waits for Run again",
      r.stage.state().halted === "tripped" && r.stage.state().paramsPending === true, JSON.stringify({ halted: r.stage.state().halted, pending: r.stage.state().paramsPending, trip: r.stage.state().trip }));
  }
  {
    // The box nudged during the stall, found by the next frame (no event): the frame before is judged first.
    const r = rig({ cost: stallAfter(20, 1500) });
    r.stage.setSubject(subject("C2"));
    await r.run();
    pumpUntil(r, () => lastLiveMs(r) >= 1500);
    r.doc.boxW -= 2;
    r.pump(1);
    check("re-review 1: a size change found by the next frame judges the frame before it, then measures",
      r.stage.state().halted === "tripped" && (r.stage.state().trip || {}).reason === "gap", JSON.stringify({ halted: r.stage.state().halted, trip: r.stage.state().trip, measures: r.stage.state().measures }));
  }
  {
    // A window drag: a resize event before every frame (the HTML spec runs them before the frame's animation callbacks).
    const r = rig({ cost: stallAfter(5, 1200) });
    r.stage.setSubject(subject("C2"));
    await r.run();
    r.pump(4);
    for (let k = 0; k < 20 && r.stage.state().running; k++) { r.doc.boxW += (k % 2 ? -3 : 4); r.resized(); r.pump(1); }
    const slow = r.liveFrames().filter((e) => e.ms >= 1200).length;
    check("re-review 1: during a window drag every frame is still judged: the first 1200 ms frame holds (as reviewed: 21 drawn, none judged)",
      r.stage.state().halted === "tripped" && slow === 1, `${slow} frames of 1200 ms; trip ${JSON.stringify(r.stage.state().trip)}`);
  }

  // ---- re-review 2 (MEDIUM): readings near the timer's resolution keep the growth they prove, never reset to linear ----
  {
    const p = preflightPlan({ tinyMs: 0.1, tinyPx: 2304, fullPx: 230400, secondMs: 0.8, secondPx: 9216, classScale: 1,
      resolutionMs: 0.1 / 8, secondResolutionMs: 0.1 / 3 });
    // Up to log((0.8 + 0.1 / 3) / (0.1 - 0.1 / 8)) / log 4 = 1.626 (shown 1.63); at face value they show 1.5.
    check("re-review 2: 0.1 and 0.8 ms averaged over 8 and 3 draws are never reset to linear: the most growth they allow, 1.63",
      p.exponent === 1.63, String(p.exponent));
    for (const [label, tinyMs, e, box, dpr, reviewed] of [
      ["pixels^1.5 read at 0.1 ms", 0.1, 1.5, [640, 360], 1, "100 ms"],
      ["pixels^2 read at 0.1 ms", 0.1, 2, [640, 360], 1, "316 ms"],
      ["pixels^1.5 read at 0.12 ms on a 2x display", 0.12, 1.5, [630, 354], 2, "114 ms"]]) {
      const r = rig({ cost: (w, h) => tinyMs * ((w * h) / 2304) ** e, box, dpr });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const first = r.liveFrames()[0];
      const pf = r.stage.state().preflight || {};
      check(`re-review 2: ${label}: its first live frame stays within Run's 30 ms budget (as reviewed: ${reviewed})`,
        first && first.ms <= PREFLIGHT.budgetMs && pf.exponent > 1,
        JSON.stringify({ first, exponent: pf.exponent, predictedMs: pf.predictedMs, scale: pf.scale }));
    }
  }

  // ---- re-review 3 (LOW-MEDIUM): after a hold Run again always measures, and its step down is in pixels ----
  {
    // Held at 0.5 x (320 x 180, a 900 ms frame), then the window goes to a 2x display: 0.25 x there IS 320 x 180.
    const big = (w, h) => !isPf(w, h) && w * h > 30000;
    let n = 0;
    const r = rig({ cost: (w, h) => { if (!big(w, h)) return perPx(0.3)(w, h); n += 1; return n > 6 ? 900 : perPx(0.3)(w, h); } });
    r.stage.setSubject(subject("C4"));
    await r.run();
    r.pump(12);
    check("re-review 3: held at 0.5 x", r.stage.state().halted === "tripped" && (r.stage.state().trip || {}).scale === 0.5, JSON.stringify(r.stage.state().trip));
    r.dpr = 2;
    const before = r.liveFrames().length;
    await r.run();
    r.pump(3);
    const after = r.liveFrames().slice(before);
    check("re-review 3: on a 2x display nothing smaller than what held exists, so Run again draws nothing and refuses (as reviewed: 320 x 180 at 900 ms again)",
      after.length === 0 && !!r.stage.state().refused, `${after.map((e) => `${e.w}x${e.h} ${e.ms} ms`)}; refused ${r.stage.state().refused}`);
  }
  {
    // Held at 0.75 x (480 x 270), then the pixel ratio 1 to 1.5: 0.5 x there IS 480 x 270, so the step is to 0.25 x.
    // Frames of 480 x 270 or more take 900 ms from the 7th live frame on; smaller ones stay cheap. (0.35 and 1.4 ms, then
    // 5.6 ms at 256 x 144, allow growth up to 1.08, which puts 0.75 x at 21.9 ms: within the budget.)
    let n = 0;
    const r = rig({ cost: (w, h) => { if (isPf(w, h)) return perPx(0.35)(w, h); n += 1; return n > 6 && w * h >= 480 * 270 ? 900 : perPx(0.35)(w, h); } });
    r.stage.setSubject(subject("C2"));
    await r.run();
    check("re-review 3: a 35 ms program starts at 0.75 x", r.stage.state().scale === 0.75, String(r.stage.state().scale));
    r.pump(10);
    check("re-review 3: and is held there", r.stage.state().halted === "tripped" && (r.stage.state().trip || {}).scale === 0.75, JSON.stringify(r.stage.state().trip));
    const measures = r.stage.state().measures, before = r.liveFrames().length;
    r.dpr = 1.5;
    await r.run();
    r.pump(2);
    const s = r.stage.state(), after = r.liveFrames().slice(before);
    check("re-review 3: after the hold Run again measures, and draws only fewer pixels than the frames that held (0.25 x: 240 x 135)",
      s.measures === measures + 1 && after.length > 0 && after.every((e) => e.w * e.h < 480 * 270) && s.running,
      JSON.stringify({ measures: [measures, s.measures], canvas: s.canvas, scale: s.scale, after: after.map((e) => `${e.w}x${e.h} ${e.ms} ms`) }));
  }

  // ---- re-review 4 (LOW-MEDIUM): every hold steps down or refuses; a size change keeps its scale only under the cap ----
  {
    // A 1800 ms frame at 0.5 x; Run again draws at 0.25 x, where the frames take 450 ms: slow, under the one-frame limit.
    let n = 0;
    const r = rig({ cost: (w, h) => { if (isPf(w, h)) return perPx(0.3)(w, h); n += 1; return n > 10 ? w * h * (1800 / 57600) : perPx(0.3)(w, h); } });
    r.stage.setSubject(subject("C4"));
    await r.run();
    pumpUntil(r, () => false, 20);
    for (let c = 0; c < 2; c++) { await r.run(); pumpUntil(r, () => false, 20); }
    const heavy = r.liveFrames().filter((e) => e.ms > LADDER.stepCapMs).length;
    check("re-review 4: slow frames adding past the budget at the smallest scale end the run: refused, not 'Lower the scale' (as reviewed: 12 frames of 450 ms over two clicks, more on each)",
      !!r.stage.state().refused && heavy <= 7 && !/Lower the scale/.test(r.status()), `${heavy} frames over 150 ms; ${r.status()}`);
  }
  {
    // 39.5 ms frames at the smallest scale, 55.5 ms apart: 45 slow frames in a row, under the time budget.
    const r = rig({ cost: perPx(6.32) });
    r.stage.setSubject(subject("C4"));
    await r.run();
    r.pump(50);
    const s = r.stage.state();
    check("re-review 4: a count hold at the smallest scale refuses too: no impossible 'Lower the scale and run again'",
      (s.trip || {}).reason === "count" && !!s.refused && !/Lower the scale/.test(r.status()), JSON.stringify({ trip: s.trip, refused: s.refused, status: r.status() }));
  }
  {
    // Frames of 300 ms at 0.5 x, then the window shrinks a little: fewer pixels than were measured, but 300 ms is past
    // the ladder's step cap, so the size change starts over by Run's rule instead of keeping 0.5 x.
    let heavy = false;
    const r = rig({ cost: (w, h) => (heavy && !isPf(w, h) ? 300 : perPx(0.5)(w, h)) });
    r.stage.setSubject(subject("C4"));
    await r.run();
    r.pump(3);
    heavy = true;
    r.pump(3);
    r.doc.boxW = 630; r.doc.boxH = 354;
    r.resized();
    check("re-review 4: a size change keeps its scale only under the 150 ms step cap: 300 ms frames move it down (as reviewed: kept up to 500 ms)",
      r.stage.state().scale === 0.25, JSON.stringify({ scale: r.stage.state().scale, pf: (r.stage.state().preflight || {}).how }));
  }

  // ---- re-review 5 (LOW): a knob value that is refused or does not compile is no GPU gap for the program on stage ----
  {
    // The rebuilt program's tiny frames take 600 ms (the pre-flight refuses it); the program on stage draws 8 ms frames.
    const r = rig({ cost: (w, h, f, toy) => (isPf(w, h) ? (toy >= 2 ? 600 : perPx(0.3)(w, h)) : 8) });
    r.stage.setSubject(subject("C4", { acceptsParams: true }));
    await r.run();
    r.pump(10);
    r.stage.setParams({ values: { a: 1 }, descriptors: [] });
    for (const fn of r.timers.splice(0)) await fn();
    await settle();
    r.pump(2);
    check("re-review 5: a knob value the pre-flight refuses leaves the program on stage drawing, unheld (as reviewed: held for 'one frame took 624 ms')",
      r.stage.state().running && !r.stage.state().tripped, JSON.stringify({ trip: r.stage.state().trip, status: r.status() }));
    // A knob value that does not compile, after a 700 ms compile.
    r.rt.log.compileMs = (toy) => (toy >= 3 ? 700 : 0);
    r.rt.log.compileFails = (toy) => toy >= 3;
    r.stage.setParams({ values: { a: 2 }, descriptors: [] });
    for (const fn of r.timers.splice(0)) await fn();
    await settle();
    r.pump(2);
    check("re-review 5: nor does a knob value that does not compile after a 700 ms compile",
      r.stage.state().running && !r.stage.state().tripped && /did not compile/.test(r.status()),
      JSON.stringify({ trip: r.stage.state().trip, status: r.status() }));
  }

  // ---- re-review 6 (LOW): a refusal is remembered when the same subject is picked again ----
  {
    const r = rig({ cost: stallAfter(10, 900) });
    const s = subject("C4");
    r.stage.setSubject(s);
    await r.run();
    for (let i = 0; i < 5 && !r.stage.state().refused; i++) { pumpUntil(r, () => false, 20); if (!r.stage.state().refused) await r.run(); }
    check("re-review 6: refused at the smallest scale", !!r.stage.state().refused, JSON.stringify(r.stage.state().trip));
    const before = r.liveFrames().length;
    r.stage.setSubject(s);
    await r.run();
    r.pump(5);
    const btn = byClass(r.root, "wb-run")[0];
    check("re-review 6: picking the same subject again draws nothing, and the button says it was refused (as reviewed: another 900 ms frame)",
      r.liveFrames().length === before && btn.disabled && /refused/i.test(textOf(btn)), `${r.liveFrames().length - before} frames; ${textOf(btn)}`);
  }

  // ---- re-review 7 (LOW): one ladder step at a time even while stopped ----
  {
    const r = rig({ cost: perPx(0.35) });
    r.stage.setSubject(subject("C4"));
    await r.run();
    eq("re-review 7: starts at 0.5 x", r.stage.state().scale, 0.5);
    r.pump(10);
    r.stage.stop();
    r.stage.setScale(0.75);
    r.stage.setScale(1);
    await r.run();
    eq("re-review 7: two raises while stopped climb one step from the scale measured: 0.75 x (as reviewed: 0.5 x to 1 x in one Run again)",
      r.stage.state().scale, 0.75);
  }

  // ---- re-review 8 (LOW, wording): the receipt names the one-pixel warm-up, and a re-measure is not 'started at' ----
  {
    const line = preflightText({ size: [64, 36], ms: 0.5, fullSize: [640, 360], predictedFullMs: 50, scale: 0.75, predictedMs: 28.1,
      budgetMs: 30, compileMs: 17, timedWith: "gl.finish + readPixels", how: "kept", why: "the stage changed size" });
    check("re-review 8: the receipt says one-pixel draw, names the read-back wait, and says a re-measure kept its scale",
      /one-pixel draw/.test(line) && !/zero-pixel/.test(line) && /readPixels/.test(line) && !/started at/.test(line) && /measured again/i.test(line), line);
    const r = rig({ cost: perPx(0.1), box: [320, 180] });
    r.stage.setSubject(subject("C2"));
    await r.run();
    r.pump(3);
    r.doc.boxW = 300;
    r.resized();
    const pf = r.receipts.at(-1).preflight || {};
    check("re-review 8: a re-measure's receipt carries why it measured again and what it did", pf.why === "the stage changed size" && pf.how === "kept",
      JSON.stringify({ how: pf.how, why: pf.why }));
  }

  // ==================================== the lab re-review's new defects (2026-10-13, third round), one pin each --
  // ---- third round (MEDIUM): an exponent the readings cannot prove is taken as the heaviest growth they allow ----
  {
    // 0.005 and 0.08 ms, each averaged over 8 draws (0.0125 ms of timer each): within the timer's resolution of each
    // other, they allow anything from linear growth to pixels cubed.
    const p = preflightPlan({ tinyMs: 0.005, tinyPx: 2304, fullPx: 1260 * 708, classScale: 1, secondMs: 0.08, secondPx: 9216,
      resolutionMs: 0.1 / 8, secondResolutionMs: 0.1 / 8 });
    check("third round: readings within the timer's resolution prove no growth, so it is taken as the heaviest, 3 (as reviewed: linear)",
      p.exponent === 3, String(p.exponent));
    // One reading alone proves no growth either (the stage takes one when the tiny frame is too heavy for a second).
    const one = preflightPlan({ tinyMs: 40, tinyPx: 2304, fullPx: 230400, classScale: 0.5 });
    check("third round: one reading is taken at the heaviest growth too, so a 40 ms tiny frame is refused (before: started at 0.25 x, 250 ms predicted, linear)",
      one.exponent === 3 && !one.ok && /500 ms/.test(one.refused || ""), JSON.stringify({ exponent: one.exponent, ok: one.ok, refused: one.refused }));
    // Readings far above the resolution keep the growth they show: 0.5 and 8 ms, a cost that goes with the square.
    const sq = preflightPlan({ tinyMs: 0.5, tinyPx: 2304, fullPx: 230400, secondMs: 8, secondPx: 9216, classScale: 1, resolutionMs: 0.025 });
    check("third round: well-resolved readings are taken at the most they allow, a little above the true 2, never below",
      sq.exponent >= 2 && sq.exponent <= 2.05, String(sq.exponent));

    // The reviewer's cases on the stage: costs that go with a power of the pixels, read within the timer's resolution.
    for (const [label, tinyMs, e, box, dpr, reviewed] of [
      ["pixels^2 read at 0.01 ms", 0.01, 2, [640, 360], 1, "a 100 ms first frame"],
      ["pixels^2 read at 0.005 ms", 0.005, 2, [1260, 708], 1, "750 ms"],
      ["pixels^2 read at 0.005 ms, a 1600 x 900 box at a pixel ratio of 1.5", 0.005, 2, [1600, 900], 1.5, "9.9 s"],
      ["pixels^1.5 read at 0.01 ms in that box", 0.01, 1.5, [1600, 900], 1.5, "527 ms"]]) {
      const r = rig({ cost: (w, h) => tinyMs * ((w * h) / 2304) ** e, box, dpr });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const first = r.liveFrames()[0];
      const pf = r.stage.state().preflight || {};
      check(`third round: ${label}: the first live frame costs no more than predicted, and stays within the budget unless the stage said it would not (as reviewed: ${reviewed})`,
        !!first && unadmitted(r.rt.log).length === 0 && (first.ms <= PREFLIGHT.budgetMs || pf.overBudget) && first.ms < WATCHDOG.slowMs,
        JSON.stringify({ first, exponent: pf.exponent, predictedMs: pf.predictedMs, scale: pf.scale, overBudget: pf.overBudget, bad: unadmitted(r.rt.log).slice(0, 2) }));
    }

    // A grid like the reviewer's: four boxes, growth from pixels^1 to pixels^3, tiny readings from 0.001 to 0.3 ms.
    const bad = [];
    let cases = 0;
    for (const [box, dpr] of [[[320, 180], 1], [[640, 360], 1], [[1260, 708], 1], [[1600, 900], 1.5]]) {
      for (const e of [1, 1.5, 2, 2.5, 3]) {
        for (const tinyMs of [0.001, 0.003, 0.005, 0.01, 0.03, 0.1, 0.3]) {
          cases += 1;
          const r = rig({ cost: (w, h) => tinyMs * ((w * h) / 2304) ** e, box, dpr });
          r.stage.setSubject(subject("C2"));
          await r.run();
          r.pump(3);
          const pf = r.stage.state().preflight || {};
          const over = unadmitted(r.rt.log);
          const first = r.liveFrames()[0];
          if (over.length || (first && first.ms > PREFLIGHT.budgetMs && !pf.overBudget)) {
            bad.push(`${box.join("x")}@${dpr} pixels^${e} at ${tinyMs} ms: ${over[0] || `first frame ${Math.round(first.ms * 10) / 10} ms, not said over budget`}`);
          }
        }
      }
    }
    check(`third round: on a grid of ${cases} costs that go with a power of the pixels, no live frame costs more than the stage predicted for it`,
      bad.length === 0, `${bad.length} cases: ${bad.slice(0, 5).join("; ")}`);

    // The reviewer's other regime: a fixed cost every frame pays (the read-back's round trip, the submission) hides how
    // the pixels' own cost grows. A square-law cost of 0.03 ms at 64 x 36 behind 0.1 ms of it reads 0.13 and 0.58 ms:
    // the total looks linear, and a full 640 x 360 frame is 300 ms.
    {
      const r = rig({ cost: (w, h) => 0.03 * ((w * h) / 2304) ** 2, overheadMs: 0.1 });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const first = r.liveFrames()[0];
      const pf = r.stage.state().preflight || {};
      check("third round: a square-law cost behind a fixed per-frame cost starts where its first frame stays within the budget (as reviewed: could start near 675 ms; at 640 x 360, 300 ms)",
        !!first && unadmitted(r.rt.log).length === 0 && (first.ms <= PREFLIGHT.budgetMs || pf.overBudget) && first.ms < WATCHDOG.slowMs,
        JSON.stringify({ first, exponent: pf.exponent, overhead: pf.overhead, predictedMs: pf.predictedMs, scale: pf.scale, second: pf.second, more: pf.more }));
    }
    const badOver = [];
    let casesOver = 0;
    for (const [box, dpr] of [[[640, 360], 1], [[1600, 900], 1.5]]) {
      for (const overheadMs of [0.05, 0.2, 1]) {
        for (const e of [1, 2, 3]) {
          for (const tinyMs of [0.003, 0.03, 0.3]) {
            casesOver += 1;
            const r = rig({ cost: (w, h) => tinyMs * ((w * h) / 2304) ** e, box, dpr, overheadMs });
            r.stage.setSubject(subject("C2"));
            await r.run();
            r.pump(3);
            const pf = r.stage.state().preflight || {};
            const over = unadmitted(r.rt.log);
            const first = r.liveFrames()[0];
            if (over.length || (first && first.ms > PREFLIGHT.budgetMs && !pf.overBudget)) {
              badOver.push(`${box.join("x")}@${dpr} ${overheadMs} ms + pixels^${e} at ${tinyMs} ms: ${over[0] || `first frame ${Math.round(first.ms * 10) / 10} ms, not said over budget`}`);
            }
          }
        }
      }
    }
    check(`third round: on a grid of ${casesOver} costs that are a fixed per-frame cost plus a power of the pixels, no live frame costs more than predicted`,
      badOver.length === 0, `${badOver.length} cases: ${badOver.slice(0, 5).join("; ")}`);

    // The larger pre-flight frames: drawn while the readings leave the growth unproven, each only when even the heaviest
    // growth keeps it under the ladder's step cap; none when the first two readings prove it. Here 0.01 and 0.16 ms allow
    // linear to the cube; the 256 x 144 frame reads 2.56 ms, and a 512 x 288 one could take 169 ms at the cube, so it
    // is not drawn.
    const r = rig({ cost: (w, h) => 0.01 * ((w * h) / 2304) ** 2 });
    r.stage.setSubject(subject("C2"));
    await r.run();
    const pfm = r.stage.state().preflight || {};
    check("third round: readings within the timer's resolution draw a larger pre-flight frame (256 x 144) and stop where the next could pass the 150 ms step cap",
      Array.isArray(pfm.more) && pfm.more.length === 1 && JSON.stringify(pfm.more[0].size) === "[256,144]" && pfm.more.every((q) => q.ms <= LADDER.stepCapMs),
      JSON.stringify(pfm.more));
    const r2 = rig({ cost: perPx(2) });
    r2.stage.setSubject(subject("C2"));
    await r2.run();
    const pf2 = r2.stage.state().preflight || {};
    check("third round: readings that prove their growth (2 and 8 ms) draw no larger frame", Array.isArray(pf2.more) && pf2.more.length === 0, JSON.stringify(pf2.more));

    // A guard, not a pin (it passes before and after): a cheap linear cost is not left at a low scale by the heaviest
    // growth. Read at 0.01 ms, it is measured on larger frames until its growth is proven, and starts at full scale in a
    // 1920 x 1080 box.
    const r3 = rig({ cost: perPx(0.01), box: [1920, 1080] });
    r3.stage.setSubject(subject("C2"));
    await r3.run();
    eq("third round (guard): a linear cost read at 0.01 ms starts at full scale in a 1920 x 1080 box", r3.stage.state().scale, 1);
  }

  // ---- third round (LOW): a hold found while the subject changes sends no receipt, and its refusal stands ----
  {
    // 8 ms frames at a quarter, then 1500 ms from the 21st: another subject is picked while that frame is in flight.
    const r = rig({ cost: stallAfter(20, 1500, 2) });
    r.stage.setSubject(subject("C2", { id: "leave1", title: "Leaving" }));
    await r.run();
    eq("third round: it starts at a quarter", r.stage.state().scale, 0.25);
    pumpUntil(r, () => lastLiveMs(r) >= 1500);
    const n = r.receipts.length;
    r.stage.setSubject(subject("C2", { id: "next01", title: "Next" }));
    check("third round: the leaving subject's hold sends no receipt once another is picked (as reviewed: its held receipt reached the Inspector)",
      r.receipts.length === n, JSON.stringify(r.receipts.slice(n).map((x) => ({ subject: x.subject, held: !!x.held }))));
    check("third round: and leaves no amber outline on the next subject's still",
      !hasClass(byClass(r.root, "wb-stage-box")[0], "is-held"), byClass(r.root, "wb-stage-box")[0].className);
    r.stage.setSubject(subject("C2", { id: "leave1", title: "Leaving" }));
    const btn = byClass(r.root, "wb-run")[0];
    check("third round: the refusal that hold earned still stands for its subject", btn.disabled && /refused/i.test(textOf(btn)), textOf(btn));
  }

  // ---- third round (LOW, cosmetic): picking another subject takes a hold's outline off ----
  {
    const r = rig({ cost: stallAfter(5, 700, 0.3) });
    r.stage.setSubject(subject("C2", { id: "held01" }));
    await r.run();
    r.pump(10);
    const box = byClass(r.root, "wb-stage-box")[0];
    check("third round: a hold outlines the stage", r.stage.state().tripped && hasClass(box, "is-held"), `${r.stage.state().tripped} ${box.className}`);
    r.stage.setSubject(subject("C2", { id: "other1" }));
    check("third round: picking another subject takes the outline off (as reviewed: 'wb-stage-box is-held' on its still)",
      !hasClass(box, "is-held"), box.className);
  }

  // =================================== the lab re-review's new defects (2026-10-13, fourth round), one pin each --
  // The pre-flight's frames are the ones drawn before the first receipt (a refusal sends one too); the larger ones are
  // those above 128 x 72. pow(ms, e): a cost of `ms` at 64 x 36 that grows as the pixels to the power e.
  const preFrames = (r) => {
    const ev = r.rt.log.events;
    const k = ev.findIndex((e) => e.kind === "admit");
    return (k < 0 ? ev : ev.slice(0, k)).filter((e) => e.kind === "render" && !e.scissor);
  };
  const pow = (ms, e) => (w, h) => ms * ((w * h) / 2304) ** e;
  const r2ms = (x) => Math.round(x * 100) / 100;
  // What went wrong in one run: a larger pre-flight frame past the ladder's step cap, any pre-flight frame past the
  // one-frame limit, or a live frame above what the stage predicted for it.
  function overLimits(r) {
    const pre = preFrames(r);
    const out = [];
    const larger = pre.filter((e) => e.w * e.h > PREFLIGHT.w2 * PREFLIGHT.h2 && e.ms > LADDER.stepCapMs + 1e-9);
    if (larger.length) out.push(`a ${larger[0].w} x ${larger[0].h} pre-flight frame took ${r2ms(larger[0].ms)} ms (the step cap is ${LADDER.stepCapMs})`);
    const huge = pre.filter((e) => e.ms > WATCHDOG.gapMs);
    if (huge.length) out.push(`a ${huge[0].w} x ${huge[0].h} pre-flight frame took ${r2ms(huge[0].ms)} ms (the limit is ${WATCHDOG.gapMs})`);
    const bad = unadmitted(r.rt.log);
    if (bad.length) out.push(bad[0]);
    return out;
  }

  // ---- fourth round (MEDIUM): one hiccup on the timed one-pixel draw does not lift the guards ----
  {
    // The per-frame cost read as 10 ms (a GC pause) beside a 0.34 ms tiny frame and a 9.2 ms 128 x 72 one: what every
    // frame pays is part of every frame, so it is never more than the smallest of them, and a reading above that is a
    // hiccup. A cube-law cost: the truth at 0.25 x of a 1920 x 1080 box is about 25 s a frame.
    const truth = (p) => 0.2 + (9 / 64) * (p / 2304) ** 3;
    const p = preflightPlan({ tinyMs: 0.2 + 9 / 64, tinyPx: 2304, fullPx: 1920 * 1080, classScale: 1, resolutionMs: 0.1 / 6,
      secondMs: 9.2, secondPx: 9216, secondResolutionMs: 0.1, overheadMs: 10, overheadResolutionMs: 0.1 });
    const under = p.perScale.filter((q) => q.ms < truth(q.px) - 0.05);
    check("fourth round: a per-frame reading above the tiny frame is set aside, so no scale is predicted below its frame (as reviewed: 0.25 x started at about 129 ms for a 25 s frame)",
      under.length === 0 && !p.ok, JSON.stringify({ ok: p.ok, scale: p.scale, under: under.map((q) => [q.scale, q.ms, Math.round(truth(q.px))]) }));

    // The reviewer's cases on the stage (a 1920 x 1080 box, 0.2 ms per frame): one slow draw (n = 1, the first timed
    // one-pixel draw) while the per-frame cost is read.
    for (const [label, cost, spike, reviewed] of [
      ["cube, 9 ms of work at 128 x 72, a 10 ms hiccup", pow(9 / 64, 3), 10, "a 576 ms 256 x 144 frame"],
      ["cube, 2.5 ms of work at 128 x 72, a 1.5 ms hiccup", pow(2.5 / 64, 3), 1.5, "a 160 ms 256 x 144 frame"],
      ["square, 20 ms of work at 128 x 72, a 25 ms hiccup", pow(20 / 16, 2), 25, "a 320 ms 256 x 144 frame"],
      ["pixels^2.5, 1 ms of work at 128 x 72, a 25 ms hiccup", pow(1 / 4 ** 2.5, 2.5), 25, "started at 338 ms predicted, first live frame 742 ms"]]) {
      const r = rig({ cost: (w, h) => cost(w, h), box: [1920, 1080], overheadMs: 0.2, onePixelMs: (n) => (n === 1 ? spike : null) });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const why = overLimits(r);
      const pf = r.stage.state().preflight || {};
      check(`fourth round: ${label}: no pre-flight frame past its cap and no live frame above its prediction (as reviewed: ${reviewed})`,
        why.length === 0, `${why.join("; ")} | overhead ${JSON.stringify(pf.overhead)}`);
      check(`fourth round: ${label}: the per-frame cost is read twice and the smaller kept (0.2 ms, not the hiccup)`,
        !!pf.overhead && Math.abs(pf.overhead.ms - 0.2) < 0.005, JSON.stringify(pf.overhead));
    }

    // Both timed one-pixel draws slow: the smaller reading is still the hiccup, above the tiny frame, so it is set aside
    // and the work is taken whole.
    {
      const r = rig({ cost: pow(9 / 64, 3), box: [1920, 1080], overheadMs: 0.2, onePixelMs: (n) => (n >= 1 ? 10 : null) });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const why = overLimits(r);
      check("fourth round: every timed one-pixel draw slow (10 ms): the reading is set aside, and no pre-flight frame passes its cap (as reviewed: a 576 ms frame)",
        why.length === 0, why.join("; "));
    }

    // A grid like the reviewer's: two boxes, growth from the square to the cube, 1 to 30 ms of work at 128 x 72, and a
    // hiccup of 1.5, 10 or 40 ms on the first timed one-pixel draw, then on every one.
    const bad = [];
    let cases = 0;
    for (const [box, dpr] of [[[1920, 1080], 1], [[1366, 768], 1.25]]) {
      for (const e of [2, 2.5, 3]) {
        for (const at128 of [1, 2.5, 5, 9, 20, 30]) {
          for (const [spike, every] of [[1.5, false], [10, false], [40, false], [10, true]]) {
            cases += 1;
            const r = rig({ cost: pow(at128 / 4 ** e, e), box, dpr, overheadMs: 0.2,
              onePixelMs: (n) => ((every ? n >= 1 : n === 1) ? spike : null) });
            r.stage.setSubject(subject("C2"));
            await r.run();
            r.pump(3);
            const why = overLimits(r);
            if (why.length) bad.push(`${box.join("x")}@${dpr} pixels^${e} ${at128} ms at 128x72, ${every ? "every" : "one"} ${spike} ms hiccup: ${why[0]}`);
          }
        }
      }
    }
    check(`fourth round: on a grid of ${cases} hiccups on the timed one-pixel draw, no pre-flight frame passes its cap and no live frame its prediction (as reviewed: 64 of 216 past the cap, worst 1920 ms)`,
      bad.length === 0, `${bad.length} cases: ${bad.slice(0, 4).join("; ")}`);
  }

  // ---- fourth round (LOW): the work bound takes what every frame pays at its LEAST ----
  {
    // The reviewer's numbers: a cube-law cost of 0.1 ms at 64 x 36 behind a true 1 ms per frame, read as 1.1 ms (each
    // reading uncertain by 0.1 ms). True frames: 25.41 ms at 0.25 x and 1563.5 ms at 0.5 x of a 640 x 360 box.
    const p = preflightPlan({ tinyMs: 1.1, tinyPx: 2304, fullPx: 640 * 360, classScale: 1, secondMs: 7.4, secondPx: 9216,
      resolutionMs: 0.1, secondResolutionMs: 0.1, overheadMs: 1.1, overheadResolutionMs: 0.1 });
    const at = (s) => (p.perScale.find((q) => q.scale === s) || {}).ms;
    check("fourth round: within the readings' uncertainty no prediction is below the frame (as reviewed: 25.2 and 1539.3 ms for 25.41 and 1563.5)",
      at(0.25) >= 25.41 && at(0.5) >= 1563.5, JSON.stringify({ q: at(0.25), h: at(0.5) }));

    // The same on the stage's guard for the larger pre-flight frames: a true 1 ms per frame read as 1.1 ms, and a
    // cube-law cost whose 256 x 144 frame takes 153 ms. Taking 1.1 + 0.1 off the 128 x 72 reading predicted 146.8 ms.
    const r = rig({ cost: pow(2.375 / 64, 3), box: [1920, 1080], overheadMs: 1, onePixelMs: (n) => (n >= 1 ? 1.1 : null) });
    r.stage.setSubject(subject("C2"));
    await r.run();
    r.pump(3);
    const why = overLimits(r);
    check("fourth round: the guard on a larger pre-flight frame takes the per-frame cost at its least (as reviewed: a 153 ms 256 x 144 frame past the 150 ms cap)",
      why.length === 0, why.join("; "));
  }

  // ---- fourth round (LOW): the 128 x 72 pair is guarded to the cube, the growth the stage now assumes ----
  {
    for (const [tinyMs, reviewed] of [[20, "a 1280 ms 128 x 72 frame"], [7.9, "a 505.6 ms 128 x 72 frame"]]) {
      const r = rig({ cost: pow(tinyMs, 3), box: [1920, 1080] });
      r.stage.setSubject(subject("C2"));
      await r.run();
      r.pump(3);
      const why = overLimits(r);
      check(`fourth round: a cube-law tiny frame of ${tinyMs} ms draws no 128 x 72 frame past the one-frame limit (as reviewed: ${reviewed})`,
        why.length === 0, why.join("; "));
    }
    // When 128 x 72 could pass the limit at the cube, the second reading is at about twice the pixels (90 x 51, eight
    // times the time at the cube): a heavy tiny frame (10 ms; 1000 ms at 1 x) still gets one, and still starts at the
    // smallest scale, over the budget, instead of being refused on one reading taken at the cube.
    {
      const rh = rig({ cost: perPx(10) });
      rh.stage.setSubject(subject("C2"));
      await rh.run();
      const pfh = rh.stage.state().preflight || {};
      check("fourth round: a 10 ms tiny frame, too heavy for 128 x 72 at the cube, takes its second reading at 90 x 51 and starts at the smallest scale",
        !!pfh.second && JSON.stringify(pfh.second.size) === "[90,51]" && pfh.scale === 0.25 && pfh.overBudget === true && overLimits(rh).length === 0,
        JSON.stringify({ second: pfh.second, scale: pfh.scale, overBudget: pfh.overBudget, why: overLimits(rh) }));
    }
    // A guard, not a pin: SwiftShader's ldSfWV read its tiny frame at 4.1 to 5.2 ms; at 5.2 ms its 128 x 72 pair is still drawn.
    const r = rig({ cost: perPx(5.2), box: [1280, 720] });
    r.stage.setSubject(subject("C2"));
    await r.run();
    const pf = r.stage.state().preflight || {};
    check("fourth round (guard): a 5.2 ms tiny frame still draws its 128 x 72 pair", !!pf.second && pf.second.size[0] === 128, JSON.stringify(pf.second));
  }

  // ---- fourth round (NIT, decision): the larger pre-flight frames stay within the scale the class may start at ----
  {
    // A C4 subject in a 1920 x 1080 box starts at 0.5 x at most: 960 x 540, 518,400 pixels. A cheap linear cost read
    // under the timer's resolution leaves its growth unproven up to 512 x 288, and 1024 x 576 has more pixels than that.
    const r = rig({ cost: perPx(0.001), box: [1920, 1080] });
    r.stage.setSubject(subject("C4"));
    await r.run();
    const most = 960 * 540;
    const big = preFrames(r).filter((e) => e.w * e.h > most);
    const pf = r.stage.state().preflight || {};
    check("fourth round: a C4 subject's pre-flight draws nothing larger than its half-scale frame (as reviewed: 1024 x 576)",
      big.length === 0 && pf.scale === 0.5, JSON.stringify({ big: big.slice(0, 2).map((e) => [e.w, e.h]), scale: pf.scale }));
  }
}

// ============================================== stage: view only by default (one switch, off until set by hand) --
// Live runs are off until their safety review clears. The switch is on only when the page's address asks (?live=1) AND
// the browser holds the key; off, the Stage shows the SwiftShader still and filmstrip, has no Run button, and no code
// path loads the runtime, makes a canvas or asks for a WebGL context.
{
  const { liveSwitch, LIVE_SWITCH } = stageMod;
  check("view only: the stage exports its one switch", typeof liveSwitch === "function" && !!LIVE_SWITCH && typeof LIVE_SWITCH.key === "string");
  if (typeof liveSwitch === "function") {
    const store = (v) => ({ getItem: (k) => (k === LIVE_SWITCH.key ? v : null) });
    const on = (search, storage) => liveSwitch({ location: { search }, localStorage: storage }).on;
    eq("view only: off with nothing set, off with only ?live=1, off with only the key, on with both",
      [on("", store(null)), on("?live=1", store(null)), on("", store("on")), on("?live=1", store("on"))], [false, false, false, true]);
    eq("view only: any other value is off, a storage that throws (a private window) is off, and node's own globals are off",
      [on("?live=true", store("on")), on("?live=1", store("yes")),
        liveSwitch({ location: { search: "?live=1" }, get localStorage() { throw new Error("blocked"); } }).on, liveSwitch().on],
      [false, false, false, false]);
  }

  // The Stage with no switch given: the page's own location and storage decide, and node has neither.
  for (const [label, env] of [["no switch", undefined], ["?live=1 without the key", { location: { search: "?live=1" }, localStorage: { getItem: () => null } }]]) {
    const doc = fakeDocument();
    const root = doc.createElement("section");
    const clock = fakeClock();
    const rt = fakeRuntime(undefined, { clock });
    const timers = [], sizeFns = [], visFns = [];
    let loads = 0;
    const stage = mountStage(doc, root, {
      loadRuntime: async () => { loads++; return rt.module; }, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
      isHidden: () => false, onResize: (fn) => { sizeFns.push(fn); return () => {}; }, onVisibilityChange: (fn) => visFns.push(fn),
      setTimeout: (fn) => { timers.push(fn); return timers.length; }, clearTimeout: () => {}, ...(env ? { env } : {}),
    });
    check(`view only (${label}): the stage says so before anything is picked`, /Live runs are off until their safety review clears/.test(textOf(root)), textOf(root));
    stage.setSubject({ kind: "shelf", id: "ttScDc", title: "AURORA", cost: "C3", acceptsParams: true,
      poster: ["/renders/ttScDc/t1.00.png"], film: { sheet: "/renders/ttScDc/filmstrip.png", frames: 8, to: 8 },
      load: async () => ({ shader: { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] } }) });
    check(`view only (${label}): no Run button, no scale, no Stop and no Take on the page`,
      ["wb-run", "wb-scale", "wb-stop", "wb-take"].every((c) => byClass(root, c).length === 0), textOf(root));
    check(`view only (${label}): the honest line`, /Live runs are off until their safety review clears/.test(textOf(byClass(root, "wb-stage-status")[0] || root)),
      textOf(byClass(root, "wb-stage-status")[0] || root));
    check(`view only (${label}): the SwiftShader still is on stage`, findAll(root, (el) => el.tagName === "IMG" && el.src === "/renders/ttScDc/t1.00.png").length === 1);
    const play = byClass(root, "wb-film-play")[0];
    check(`view only (${label}): the Stage offers the filmstrip`, !!play && !play.hidden && /8 frames/.test(textOf(play)), play ? textOf(play) : "no button");
    if (play) {
      play.fire("click");
      const sprite = byClass(root, "wb-stage-film")[0];
      check(`view only (${label}): the filmstrip plays on the Stage, a window stepped across the contact sheet`,
        !!sprite && /filmstrip\.png/.test(sprite.style.backgroundImage || "") && hasClass(sprite, "is-playing") && /frame 1 of 8/.test(textOf(root)),
        sprite ? JSON.stringify(sprite.style) : "no sprite");
      for (const fn of timers.splice(0)) fn();
      check(`view only (${label}): and steps`, /frame 2 of 8/.test(textOf(root)), textOf(byClass(root, "wb-badge")[0] || root));
    }
    // Every way in to the live path, by the API and by events.
    await stage.run();
    stage.setScale(1);
    stage.setParams({ values: { gain: 2 }, descriptors: [] });
    for (const fn of timers.splice(0)) await fn();
    stage.take();
    stage.suspend("the Shelf");
    stage.raiseCost("C4", "a test");
    sizeFns.forEach((f) => f());
    visFns.forEach((f) => f());
    for (let i = 0; i < 4; i++) clock.pump(16);
    await settle();
    eq(`view only (${label}): no runtime loaded, no toy, no canvas, no WebGL context, no animation frame, whatever is called`,
      [loads, rt.log.created, doc.canvases, doc.getContextCalls, clock.rafCalls], [0, 0, 0, 0, 0]);
    eq(`view only (${label}): the stage reports itself off`, [stage.live, stage.state().live], [false, false]);
  }

  // The source: one place makes a canvas, one asks for a toy (its WebGL context), one loads the runtime, and each sits
  // behind the same check, so no code path reaches any of them while the switch is off.
  const src = readFileSync(here("../arsenal/web/lib/workbench/stage.js"), "utf8");
  const count = (re) => (src.match(re) || []).length;
  eq("view only: one canvas, one createToy, one runtime load in stage.js",
    [count(/h\(doc, 'canvas'/g), count(/\.createToy\(/g), count(/\bloadRuntime\(\)/g)], [1, 1, 1]);
  const body = (name) => { const i = src.indexOf(`async function ${name}(`); return i < 0 ? "" : src.slice(i, src.indexOf("\n  }\n", i)); };
  check("view only: the canvas and the toy are made in build(), which refuses first when the switch is off",
    /^async function build\([^)]*\) \{\s*mustBeLive\(/.test(body("build")) && body("build").includes("h(doc, 'canvas'") && body("build").includes(".createToy("),
    body("build").slice(0, 160));
  check("view only: the runtime is loaded in loadLive(), which refuses first too",
    /^async function loadLive\(\) \{\s*mustBeLive\(/.test(body("loadLive")) && body("loadLive").includes("loadRuntime()"), body("loadLive").slice(0, 160));

  // The whole Workbench as Daniel opens it: no switch set.
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const rt = fakeRuntime(undefined, { clock });
  const imports = [];
  const shelfJson = { shaders: [{ id: "ltffzl", title: "Heartfelt", renders: { status: "rendered",
    stills: [{ t: 1, url: "/renders/ltffzl/t1.00.png" }], filmstrip: { url: "/renders/ltffzl/filmstrip.png", frames: 8, to: 8 } } }] };
  const fetch = fakeFetch({ "/atlas.json": atlas, "/shelf/index.json": shelfJson,
    "/corpus/ltffzl/shader.json": { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] } });
  const wb = await mountWorkbench(doc, root, {
    fetch, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
    importModule: async (url) => { imports.push(url); if (/toy-runtime/.test(url)) return rt.module; throw new Error(`no module at ${url}`); },
    isHidden: () => false, onVisibilityChange: () => {},
  });
  await wb.ready;
  check("the lab as opened: the header says live runs are off", /Live runs are off until their safety review clears/.test(textOf(byClass(root, "wb-safety")[0] || root)),
    textOf(byClass(root, "wb-safety")[0] || root));
  byClass(byClass(root, "wb-shelf-card")[0], "wb-stage-btn")[0].fire("click");
  await settle();
  check("the lab as opened: a loved shader on stage has no Run button, and its filmstrip to play",
    byClass(root, "wb-run").length === 0 && byClass(root, "wb-film-play").length === 1, textOf(byClass(root, "wb-stage")[0]));
  await wb.stage.run();
  await settle();
  eq("the lab as opened: no runtime import, no canvas, no context, no animation frame",
    [imports.filter((u) => /toy-runtime/.test(u)).length, doc.canvases, doc.getContextCalls, clock.rafCalls], [0, 0, 0, 0]);
  check("the lab as opened: the Strip's takes say why there are none", /Live runs are off/.test(textOf(byClass(root, "wb-strip")[0])), textOf(byClass(root, "wb-strip")[0]));
  const emptyReceipt = textOf(byClass(root, "wb-insp-receipt")[0] || root);
  check("the lab as opened: the Inspector's empty receipt says live runs are off (third round; as reviewed: 'A live run writes here what ran...')",
    /Live runs are off until their safety review clears/.test(emptyReceipt) && !/^\s*Receipt\s+Nothing has run yet\. A live run writes here/.test(emptyReceipt), emptyReceipt);
}

// ============================================================================ stage: cards and params --
{
  const card = parseCard('//! {"card": "core-safe", "uses": ["core-safe"], "t": [0, 2],\n//!  "size": [320, 180], "note": "a curve"}\nvoid mainImage(out vec4 c, in vec2 p) { c = vec4(u_gain); }\n');
  eq("a card's header", [card.header.card, card.header.uses, card.header.t], ["core-safe", ["core-safe"], [0, 2]]);
  check("a card's body is the rest", card.body.startsWith("void mainImage") && !card.body.includes("//!"));
  let threw = false;
  try { parseCard("void mainImage(){}"); } catch { threw = true; }
  check("a card without a //! header is refused", threw);

  const desc = params.paramsFromModule({ name: "demo", params: [
    { name: "gain", label: "Gain", unit: "ratio", range: [0, 2], default: 1 },
    { name: "tint", label: "Tint", type: "colour", default: [1, 0.5, 0.25] },
    { name: "unused", label: "Unused", unit: "ratio", range: [0, 1], default: 0.5 }] }, null);
  const common = "// composed\nuniform float u_tint_never;\nuniform vec3 u_tint;\nvec3 demo(vec3 c) { return c * u_tint; }\n";
  const bound = bindParams(common, card.body, desc, { gain: 1.5, tint: [1, 0.5, 0.25], unused: 0.5 });
  check("a declared uniform becomes a constant", bound.common.includes("const vec3 u_tint = vec3(1.0, 0.5, 0.25);") && !/uniform vec3 u_tint;/.test(bound.common));
  check("a read but undeclared param is declared once", bound.common.includes("const float u_gain = 1.5;"));
  eq("bound and unread", [bound.bound.sort(), bound.unread], [["gain", "tint"], ["unused"]]);
  check("other uniforms are untouched", bound.common.includes("uniform float u_tint_never;"));
  // The card convention that works for the CLI render too: a knob declared as a const with its default; the Workbench
  // rewrites the value (the CLI renders the default, since it binds no uniforms).
  const constCard = bindParams("// lib\n", "const float u_gain = 1.0;\nconst vec3 u_tint = vec3(1.0);\nvoid mainImage(out vec4 color, in vec2 pixel) { color = vec4(u_tint * u_gain, 1.0); }\n",
    desc, { gain: 0.25, tint: [0.5, 0.5, 0.5], unused: 0.5 });
  check("a const knob gets the knob's value", constCard.body.includes("const float u_gain = 0.25;") && constCard.body.includes("const vec3 u_tint = vec3(0.5, 0.5, 0.5);"),
    constCard.body);
  check("and is not declared twice", (constCard.body + constCard.common).split("u_gain =").length === 2);
  eq("const knobs count as bound", constCard.bound.sort(), ["gain", "tint"]);
}

// ===================================================================== inspector: header, params, receipt --
// ---- fourth round (NIT): the pre-flight line says what every frame pays only when it is something, and never a
// reading the stage set aside as a hiccup ----
{
  const base = { size: [64, 36], ms: 2, fullSize: [640, 360], predictedFullMs: 237.4, scale: 0.25, predictedMs: 12.9, budgetMs: 30,
    timedWith: "gl.finish + readPixels", compileMs: 0, second: { size: [128, 72], ms: 8 }, exponent: 1.05,
    growth: { low: 1, high: 1.05, proven: true, readings: 2 } };
  const zero = preflightText({ ...base, overhead: { ms: 0.004, reps: 8 } });
  check("fourth round: a per-frame reading that rounds to 0 is not said (as reviewed: 'every frame pays 0 ms whatever its size')",
    !/every frame pays/.test(zero), zero);
  const some = preflightText({ ...base, overhead: { ms: 0.2, reps: 8 } });
  check("fourth round (guard): a per-frame reading of 0.2 ms is said", /every frame pays 0\.2 ms whatever its size/.test(some), some);
  const hiccup = preflightText({ ...base, overhead: { ms: 10, reps: 1, setAside: true } });
  check("fourth round: a per-frame reading set aside as a hiccup is said as such, not as what every frame pays",
    !/every frame pays/.test(hiccup) && /set aside/.test(hiccup) && /10 ms/.test(hiccup), hiccup);
}
{
  const facts = composedFacts("// arsenal.glsl-module/v1 compose: a, b\n// modules: a@1.0.0 b@0.2.0\n// sha256: abc123\n\nfloat a(){return 1.0;}\n");
  eq("composed facts", facts, { modules: ["a@1.0.0", "b@0.2.0"], sha: "abc123" });

  const doc = fakeDocument();
  const root = doc.createElement("section");
  const changes = [];
  const insp = mountInspector(doc, root, { paramsLib: { ...paramsUi, ...params }, onParams: (v) => changes.push(v) });
  check("inspector says what it shows before a pick", textOf(root).trim().length > 0);
  const recipe = { kind: "module", path: "groups/demo.glsl", name: "demo", status: "built", cost: "C2", priority: "P0",
    functions: ["demo"], parts: [], version: "0.1.0",
    header: { name: "demo", kind: "recipe", cat: "G8", version: "0.1.0", license: "Apache-2.0", credits: ["a public article"],
      cost: { class: "C2", loop: "layers <= 48" }, contract: "a promise", note: "a craft note",
      params: [{ name: "gain", label: "Gain", unit: "ratio", range: [0, 2], default: 1, group: "light" }] } };
  insp.showNode(recipe);
  check("header fields shown", /a promise/.test(textOf(root)) && /Apache-2.0/.test(textOf(root)) && /layers <= 48/.test(textOf(root)));
  const slider = find(root, (el) => el.tagName === "INPUT" && el.type === "range");
  check("a recipe's params become generated controls", !!slider);
  slider.value = "1.5"; slider.fire("input"); slider.fire("change");
  check("a knob change reaches the page", changes.length >= 1 && changes.at(-1).gain === 1.5, JSON.stringify(changes.at(-1)));
  const planned = { kind: "module", path: "core/safe.glsl", name: "core/safe.glsl", status: "planned", cost: "C0", priority: "P0",
    functions: ["safeSqrt"], parts: atlas.parts.filter((p) => p.module === "core/safe.glsl"), header: null };
  insp.showNode(planned);
  check("a planned module shows its parts' signatures", textOf(root).includes("float safeSqrt(float x)") && /planned/i.test(textOf(root)));
  insp.showReceipt({ subject: "card core-safe", renderer: "ANGLE (AMD Radeon)", scale: 0.5, size: [320, 180],
    modules: ["core-safe@1.0.0"], sha: "deadbeef", compile: { ok: true } });
  check("the receipt of what ran: modules@version and the composed sha",
    textOf(root).includes("core-safe@1.0.0") && textOf(root).includes("deadbeef") && /AMD Radeon/.test(textOf(root)));
  // The empty receipt says why nothing has run: with live runs off, that they are off (third round, NIT).
  const rootOff = doc.createElement("section");
  mountInspector(doc, rootOff, { live: false });
  check("view only: the Inspector's empty receipt says live runs are off (as reviewed: only 'A live run writes here what ran...')",
    /Live runs are off until their safety review clears/.test(textOf(byClass(rootOff, "wb-insp-receipt")[0])), textOf(rootOff));
  const rootOn = doc.createElement("section");
  mountInspector(doc, rootOn, { live: true });
  check("with them on, it says what a live run will write", /A live run writes here/.test(textOf(byClass(rootOn, "wb-insp-receipt")[0])), textOf(rootOn));

  // A loved shader's datasheet links its techniques and its groups back into the Library.
  const jumps = [];
  const root4 = doc.createElement("section");
  const insp4 = mountInspector(doc, root4, { onCategory: (c) => jumps.push(["cat", c]), onGroup: (g) => jumps.push(["group", g]) });
  const shelfEntry = normalizeShelf({ shaders: [{ id: "ttScDc", title: "AURORA", author: "alro", licence: { name: "MIT" },
    tags: ["noise.fbm"], categories: [{ id: "B3", tags: ["noise.fbm"] }], groups: [{ name: "aurora", line: "x" }],
    parts: [], passes: ["image", "buffer"] }] }, atlas, ROUTES).entries[0];
  insp4.showNode({ ...shelfEntry, kind: "shelf" });
  byClass(root4, "wb-tag")[0].fire("click");
  byClass(root4, "wb-teach")[0].fire("click");
  eq("datasheet links: technique to category, group to group", jumps, [["cat", "B3"], ["group", "aurora"]]);
  check("the passes are named", /image, buffer/.test(textOf(root4)));

  // Without params-ui the params are still listed, read-only, and the panel says why.
  const root2 = doc.createElement("section");
  const insp2 = mountInspector(doc, root2, { paramsLib: null, paramsWhy: "HTTP 404 on /webl/params-ui.js" });
  insp2.showNode(recipe);
  check("no params-ui: the params are listed and the reason given",
    /Gain/.test(textOf(root2)) && /params-ui/.test(textOf(root2)) && !find(root2, (el) => el.tagName === "INPUT"));
}

// ============================================================================== strip: renders and takes --
{
  const doc = fakeDocument();
  const root = doc.createElement("section");
  const strip = mountStrip(doc, root, {});
  check("an empty strip says so", textOf(root).trim().length > 0);
  strip.showRenders({ title: "AURORA", frames: [{ t: 0, url: "/renders/ttScDc/filmstrip/t0.00.png" }, { t: 1, url: "/renders/ttScDc/filmstrip/t1.00.png" }],
    sheet: "/renders/ttScDc/filmstrip.png", note: "SwiftShader, 320x180" });
  eq("frames as images", findAll(root, (el) => el.tagName === "IMG").map((i) => i.src).slice(0, 2),
    ["/renders/ttScDc/filmstrip/t0.00.png", "/renders/ttScDc/filmstrip/t1.00.png"]);
  check("each frame is labelled with its t", /t\s*=\s*0\.00/.test(textOf(root)) && /t\s*=\s*1\.00/.test(textOf(root)));
  strip.addTake({ url: "data:image/png;base64,AAAA", receipt: { subject: "AURORA", renderer: "ANGLE (AMD)", scale: 0.5, t: 3.2 } });
  check("a take carries its receipt", /AMD/.test(textOf(root)) && /0\.5/.test(textOf(root)));
}

// ================================================ the whole workbench with no routes yet: never a blank panel --
{
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const imports = [];
  const wb = await mountWorkbench(doc, root, {
    fetch: fakeFetch(), raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
    importModule: async (url) => { imports.push(url); throw new Error(`no module at ${url}`); },
    isHidden: () => false, onVisibilityChange: () => {},
  });
  await wb.ready;
  check("the header says Shader Lab", /Shader Lab/.test(textOf(root)));
  for (const panel of ["wb-library", "wb-stage", "wb-inspector", "wb-strip", "wb-shelf"]) {
    const el = byClass(root, panel)[0];
    check(`${panel} exists and is not blank`, el && textOf(el).trim().length > 0, panel);
  }
  check("the library says the atlas is not available yet", /not available yet/i.test(textOf(byClass(root, "wb-library")[0])));
  check("the shelf says its index is not available yet", /not available yet/i.test(textOf(byClass(root, "wb-shelf")[0])));
  check("no runtime import on load", !imports.some((u) => /toy-runtime/.test(u)));
  eq("no canvas, context or animation frame on load", [doc.canvases, doc.getContextCalls, clock.rafCalls], [0, 0, 0]);
}

// ======================================== the whole workbench with routes: tree, shelf and selection wire up --
{
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const modText = '//! {"name": "core-safe", "kind": "helper", "cat": "A1", "family": "A", "version": "1.0.0", "license": "Apache-2.0",\n//!  "cost": {"class": "C0"}, "contract": "never NaN"}\nfloat safeSqrt(float x) { return sqrt(max(x, 0.0)); }\n';
  // A module file that is not UTF-8 (byte 0xFF): the CLI quarantines it; text() would have hidden the bad byte.
  const notUtf8 = new Uint8Array([...new TextEncoder().encode('//! {"name": "odd-bytes", "kind": "helper", "cat": "A1", "version": "1.0.0"}\nfloat oddFn(float x) { return x; } // '), 0xff, 0x0a]);
  const table = {
    "/atlas.json": atlas,
    "/glsl/index.json": { api: "arsenal.glsl-module/v1", files: [{ path: "core/safe.glsl", sha256: "x" }, { path: "extra/odd.glsl", sha256: "y" }] },
    "/glsl/core/safe.glsl": modText,
    "/glsl/extra/odd.glsl": notUtf8,
    "/shelf/index.json": { shaders: [{ id: "ttScDc", title: "AURORA", author: "alro", licence: "MIT (explicit)", tags: ["noise.fbm"] }] },
  };
  const fetch = fakeFetch(table);
  const modlib = await import("../arsenal/web/glsl/modlib.js");
  const imports = [], loadCalls = [], globalCalls = [];
  // The composer's own loader, and nothing else: the private loader that read text() is gone.
  const modlibSeen = { ...modlib, loadLibrary: (url, o) => { loadCalls.push(url); return modlib.loadLibrary(url, o); },
    libraryFromSources: () => { throw new Error("the Workbench must load the library with modlib.loadLibrary"); } };
  const wb = await withGlobalFetch(globalFetchFrom(table, globalCalls), async () => {
    const w = await mountWorkbench(doc, root, {
      fetch, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
      importModule: async (url) => {
        imports.push(url);
        if (/modlib/.test(url)) return modlibSeen;
        if (/params-ui/.test(url)) return paramsUi;
        if (/params\.js/.test(url)) return params;
        throw new Error(`no module at ${url}`);
      },
      isHidden: () => false, onVisibilityChange: () => {},
    });
    await w.ready;
    return w;
  });
  eq("the library is loaded by modlib.loadLibrary from the index route", loadCalls, ["/glsl/index.json"]);
  check("its files are read through the composer's fetch (bytes)", globalCalls.includes("/glsl/core/safe.glsl"));
  const problems = wb.library.tree().problems;
  check("a file that is not UTF-8 is quarantined, as the CLI does", problems.some((p) => p.path === "extra/odd.glsl" && /not UTF-8/.test(p.problem)),
    JSON.stringify(problems));
  const lib = byClass(root, "wb-library")[0];
  const row = byClass(lib, "wb-module").find((r) => r.dataset.path === "core/safe.glsl");
  check("a module from the index shows as built", row && /built/i.test(textOf(row)) && /core-safe/.test(textOf(row)));
  row.fire("click");
  await settle();
  check("selecting it fills the inspector", /never NaN/.test(textOf(byClass(root, "wb-inspector")[0])));
  eq("the shelf has the index's entry", byClass(root, "wb-shelf-card").length, 1);
  byClass(root, "wb-tag")[0].fire("click");
  const want = atlas.tags.exact["noise.fbm"][0];
  const cat = byClass(lib, "wb-category").find((n) => n.dataset.category === want);
  check("a shelf tag reveals its category in the library", cat && cat.open === true);
  check("still no runtime import, no canvas", !imports.some((u) => /toy-runtime/.test(u)) && doc.canvases === 0);
}

// ======================================= a card's cost gate: the heaviest class across everything its uses pull in --
{
  const modlib = await import("../arsenal/web/glsl/modlib.js");
  const light = '//! {"name": "light-mod", "kind": "helper", "cat": "A1", "version": "1.0.0", "cost": {"class": "C0"}}\nfloat lightFn(float x) { return heavyFn(x) * 0.5; }\n';
  const heavy = '//! {"name": "heavy-mod", "kind": "helper", "cat": "A1", "version": "1.0.0", "cost": {"class": "C3"}}\nfloat heavyFn(float x) { return x; }\n';
  const bare = '//! {"name": "bare-mod", "kind": "helper", "cat": "A1", "version": "1.0.0"}\nfloat bareFn(float x) { return x; }\n';
  const mid = '//! {"name": "mid-mod", "kind": "helper", "cat": "A1", "version": "1.0.0", "cost": {"class": "C2"}}\nfloat midFn(float x) { return x; }\n';
  const lib = modlib.libraryFromSources([["a/light.glsl", light], ["a/heavy.glsl", heavy], ["a/bare.glsl", bare], ["a/mid.glsl", mid]], { strict: false });
  const c = closureCost(lib, ["light-mod"]);
  eq("a module's cost is the heaviest across what it pulls in", [c.cls, c.heaviest], ["C3", "heavy-mod"]);
  eq("an undeclared cost anywhere in the closure makes it unknown (run as C4)", closureCost(lib, ["light-mod", "bare-mod"]).cls, null);
  eq("no library: nothing known", closureCost(null, ["light-mod"]).cls, null);

  // In the Workbench: picking light-mod (declared C0) names C3 on the Run button before any click; its card, which also
  // uses mid-mod, cannot lower that.
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const table = {
    "/atlas.json": atlas,
    "/glsl/index.json": { files: [{ path: "a/light.glsl" }, { path: "a/heavy.glsl" }, { path: "a/mid.glsl" }] },
    "/glsl/a/light.glsl": light, "/glsl/a/heavy.glsl": heavy, "/glsl/a/mid.glsl": mid,
    "/glsl/cards/light-mod.card": '//! {"card": "light-mod", "uses": ["light-mod", "mid-mod"], "t": [0]}\nvoid mainImage(out vec4 color, in vec2 pixel) { color = vec4(lightFn(midFn(0.5))); }\n',
  };
  const rt = fakeRuntime(undefined, { clock });
  const receipts = [];
  const wb = await withGlobalFetch(globalFetchFrom(table), async () => {
    const w = await mountWorkbench(doc, root, {
      fetch: fakeFetch(table), raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
      importModule: async (url) => {
        if (/modlib/.test(url)) return modlib;
        if (/toy-runtime/.test(url)) return rt.module;
        throw new Error(`no module at ${url}`);
      },
      isHidden: () => false, onVisibilityChange: () => {}, env: LIVE_ON,
    });
    await w.ready;
    return w;
  });
  const row = byClass(root, "wb-module").find((r) => r.dataset.path === "a/light.glsl");
  row.fire("click");
  await settle();
  const runBtn = byClass(root, "wb-run")[0];
  check("the Run button names the heaviest class of the closure (C3), not the module's own (C0)", /C3/.test(textOf(runBtn)) && /half scale/.test(textOf(runBtn)), textOf(runBtn));
  check("and the cost line says which module made it so", /heavy-mod/.test(textOf(byClass(root, "wb-stage")[0])));
  check("with the switch on, the Inspector's empty receipt says a live run writes there, not that runs are off",
    /A live run writes here/.test(textOf(byClass(root, "wb-insp-receipt")[0])) && !/Live runs are off/.test(textOf(byClass(root, "wb-insp-receipt")[0])),
    textOf(byClass(root, "wb-insp-receipt")[0]));
  const origShow = wb.inspector.showReceipt;
  wb.inspector.showReceipt = (r) => { receipts.push(r); origShow(r); };
  await withGlobalFetch(globalFetchFrom(table), async () => { runBtn.fire("click"); await settle(); });
  eq("it starts at half scale", rt.log.resizes.at(-1), [320, 180]);
  eq("the stage reports C3", wb.stage.state().cost, "C3");

  // Leaving the Stage for the Shelf STOPS the loop; coming back does not restart it.
  check("running before the Shelf tab", wb.stage.state().running);
  clock.pump(16); clock.pump(16);
  const t0 = rt.log.lastTime;
  findAll(root, (el) => el.dataset && el.dataset.tab === "shelf")[0].fire("click");
  const n0 = rt.log.renders;
  clock.pump(16); clock.pump(16);
  eq("the Shelf tab stops the stage: no renders, nothing queued", [rt.log.renders - n0, clock.pending(), wb.stage.state().running], [0, 0, false]);
  clock.spend(4000);
  findAll(root, (el) => el.dataset && el.dataset.tab === "bench")[0].fire("click");
  clock.pump(16); clock.pump(16);
  eq("back on the Workbench: no auto-resume", [rt.log.renders - n0, wb.stage.state().running], [0, false]);
  check("the stage says why it stopped and that Run continues", /Shelf/.test(textOf(byClass(root, "wb-stage-status")[0]))
    && /press run/i.test(textOf(byClass(root, "wb-stage-status")[0])), textOf(byClass(root, "wb-stage-status")[0]));
  check("the button still names the cost and the scale", /C3/.test(textOf(runBtn)) && /half scale/.test(textOf(runBtn)) && !runBtn.disabled, textOf(runBtn));
  runBtn.fire("click");
  await settle();
  clock.pump(16);
  check("an explicit Run resumes it, iTime continuous", wb.stage.state().running && rt.log.lastTime - t0 < 0.1, `${t0} -> ${rt.log.lastTime}`);
}

// ====== third round (LOW): a module picked while a loved shader's frame stalls shows its own datasheet and no old receipt --
// The reviewer's probe: Heartfelt runs live at half scale, a frame stalls at 1500 ms, and a module is picked in the
// Library while it is in flight. The Stage judges that frame as the subject leaves; the Inspector must not then show
// Heartfelt's held receipt beside the module's datasheet.
{
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const rt = fakeRuntime(undefined, { clock });
  let live = 0;
  rt.log.cost = (w, h) => { if (isPf(w, h)) return w * h * (0.3 / 2304); live += 1; return live > 6 ? 1500 : 8; };
  const modText = '//! {"name": "core-safe", "kind": "helper", "cat": "A1", "family": "A", "version": "1.0.0", "license": "Apache-2.0",\n//!  "cost": {"class": "C0"}, "contract": "never NaN"}\nfloat safeSqrt(float x) { return sqrt(max(x, 0.0)); }\n';
  const table = {
    "/atlas.json": atlas,
    "/glsl/index.json": { api: "arsenal.glsl-module/v1", files: [{ path: "core/safe.glsl", sha256: "x" }] },
    "/glsl/core/safe.glsl": modText,
    "/shelf/index.json": { shaders: [{ id: "ltffzl", title: "Heartfelt", renders: { status: "rendered", stills: [{ t: 1, url: "/renders/ltffzl/t1.00.png" }] } }] },
    "/corpus/ltffzl/shader.json": { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] },
  };
  const modlib = await import("../arsenal/web/glsl/modlib.js");
  const wb = await withGlobalFetch(globalFetchFrom(table), async () => {
    const w = await mountWorkbench(doc, root, {
      fetch: fakeFetch(table), raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1, env: LIVE_ON,
      importModule: async (url) => {
        if (/modlib/.test(url)) return modlib;
        if (/toy-runtime/.test(url)) return rt.module;
        throw new Error(`no module at ${url}`);
      },
      isHidden: () => false, onVisibilityChange: () => {}, onResize: () => () => {},
    });
    await w.ready;
    return w;
  });
  byClass(byClass(root, "wb-shelf-card")[0], "wb-stage-btn")[0].fire("click");
  await settle();
  await withGlobalFetch(globalFetchFrom(table), async () => { byClass(root, "wb-run")[0].fire("click"); await settle(); });
  const insp = () => textOf(byClass(root, "wb-insp-receipt")[0]);
  check("third round (Workbench): Heartfelt runs live, its receipt in the Inspector",
    wb.stage.state().running && /Heartfelt/.test(insp()), JSON.stringify({ running: wb.stage.state().running, scale: wb.stage.state().scale, receipt: insp().slice(0, 120) }));
  for (let i = 0; i < 40 && wb.stage.state().running && !rt.log.shadedLog.some((e) => e.ms >= 1500); i++) clock.pump(16);
  check("third round (Workbench): a 1500 ms frame is in flight", wb.stage.state().running && rt.log.shadedLog.some((e) => e.ms >= 1500));
  const row = byClass(byClass(root, "wb-library")[0], "wb-module").find((x) => x.dataset.path === "core/safe.glsl");
  row.fire("click");
  await settle();
  check("third round (Workbench): the module is on stage, its datasheet in the Inspector",
    wb.stage.state().subject === "core-safe" && /never NaN/.test(textOf(byClass(root, "wb-inspector")[0])), String(wb.stage.state().subject));
  check("third round (Workbench): and no receipt of Heartfelt's beside it (as reviewed: 'Subject Heartfelt ... Scale 0.5 x')",
    !/Heartfelt/.test(insp()) && /Nothing has run/.test(insp()), insp().slice(0, 200));
}

// ================================== a Shelf subject: study-only refusal client-side, stand-ins, SwiftShader warm ms --
{
  const doc = fakeDocument();
  const root = doc.createElement("main");
  const clock = fakeClock();
  const rt = fakeRuntime(undefined, { clock });
  const shelfJson = { shaders: [
    { id: "4s23zz", title: "Warping", study_only: false },   // a stale false: the atlas says study only
    { id: "ltffzl", title: "Heartfelt", renders: { status: "rendered", stills: [{ t: 1, url: "/renders/ltffzl/t1.00.png" }],
      warm_ms: 2.7, substituted: [{ src: "/media/a/abc123.png", kind: "texture", reason: "load failed: procedural stand-in" }] } }] };
  const fetch = fakeFetch({ "/atlas.json": atlas, "/shelf/index.json": shelfJson,
    "/corpus/ltffzl/shader.json": { renderpass: [{ type: "image", code: "void mainImage(out vec4 c, in vec2 p){c=vec4(1);}" }] } });
  const wb = await mountWorkbench(doc, root, {
    fetch, raf: clock.raf, caf: clock.caf, now: clock.now, dpr: () => 1,
    importModule: async (url) => { if (/toy-runtime/.test(url)) return rt.module; throw new Error(`no module at ${url}`); },
    isHidden: () => false, onVisibilityChange: () => {},
  });
  await wb.ready;
  const cards = byClass(root, "wb-shelf-card");
  check("the stale-false study-only shader offers no Put on stage", byClass(cards[0], "wb-stage-btn").length === 0 && hasClass(cards[0], "is-study-only"));
  byClass(cards[1], "wb-stage-btn")[0].fire("click");
  await settle();
  const stageEl = byClass(root, "wb-stage")[0];
  check("the stage's still says it used stand-ins", /stand-in/.test(textOf(stageEl)), textOf(stageEl));
  check("the cost line carries the SwiftShader warm ms", /2\.7 ms/.test(textOf(stageEl)));
  check("the Strip's note names the stand-ins", /stand-in/.test(textOf(byClass(root, "wb-strip")[0])));
}

// ========================================= the card document is one the real runtime accepts (no WebGL needed) --
{
  const modlib = await import("../arsenal/web/glsl/modlib.js");
  const lib = modlib.libraryFromSources([["core/safe.glsl",
    '//! {"name": "core-safe", "kind": "helper", "cat": "A1", "version": "1.0.0"}\nfloat safeSqrt(float x) { return sqrt(max(x, 0.0)); }\n']], { strict: false });
  const composed = lib.compose(["core-safe"], "toy");
  const card = parseCard('//! {"card": "core-safe", "uses": ["core-safe"], "t": [0, 2]}\nvoid mainImage(out vec4 color, in vec2 pixel) { color = vec4(vec3(safeSqrt(pixel.x / iResolution.x)), 1.0); }\n');
  const doc = cardShader("core-safe", composed, card.body);
  const toy = await import("../arsenal/web/shaderlab/toy-runtime.js");
  let norm = null;
  try { norm = toy.normalizeShader(doc); } catch (e) { check("the runtime accepts a card document", false, e.message); }
  const order = toy.passOrder(norm ? norm.renderpass : []);
  eq("one drawn pass: Image", order.map((e) => e.key), ["image"]);
  const common = norm.renderpass.filter((p) => toy.passKey(p) === "common").map((p) => p.code).join("\n");
  const asm = toy.assembleSource(norm.renderpass.find((p) => toy.passKey(p) === "image"), common);
  check("the assembled source starts with the house template line", asm.source.startsWith("#version 300 es"));
  check("the composed library is the Common the Image pass sees", asm.source.includes("float safeSqrt(float x)") && asm.source.includes("// sha256: "));
  eq("the receipt facts come from the composed text", composedFacts(composed).modules, ["core-safe@1.0.0"]);

  eq("corpus media resolve to the lab server", [mediaFor(ROUTES, "/media/a/abc123.png"), mediaFor(ROUTES, "/presets/tex00.jpg"),
    mediaFor(ROUTES, "/media/a/../x.png")], ["/corpus/media/abc123.png", null, null]);
  eq("card stills follow the card's t list", cardImages(ROUTES, "core-safe", { t: [0, 2] }),
    ["/cards/core-safe/t0.00.png", "/cards/core-safe/t2.00.png"]);
  eq("a card with no t list pictures t = 0 (cards.py's default)", cardImages(ROUTES, "core-safe", {}), ["/cards/core-safe/t0.00.png"]);
}

// ============================================================================ the route contract itself --
{
  eq("route contract", [ROUTES.atlas, ROUTES.glslIndex, ROUTES.shelf, ROUTES.runtime, ROUTES.paramsUi, ROUTES.params,
    ROUTES.render("ab12CD", "t1.00.png"), ROUTES.study("ab12CD"), ROUTES.card("core-safe", "t0.00.png"),
    ROUTES.cardSource("core-safe"), ROUTES.corpusShader("ab12CD")],
  ["/atlas.json", "/glsl/index.json", "/shelf/index.json", "/lab/toy-runtime.js", "/webl/params-ui.js", "/webl/params.js",
    "/renders/ab12CD/t1.00.png", "/study/ab12CD.md", "/cards/core-safe/t0.00.png", "/glsl/cards/core-safe.card",
    "/corpus/ab12CD/shader.json"]);
  const r = await fetchJson(fakeFetch(), "/nowhere.json");
  check("a 404 is a reason, not a throw", r.ok === false && /404/.test(r.reason));
  const doc = fakeDocument();
  const u = unavailable(doc, { title: "Shelf", route: "/shelf/index.json", why: "HTTP 404", fills: "the Shelf slice" });
  check("the honest empty state", /not available yet/i.test(textOf(u)) && textOf(u).includes("/shelf/index.json"));
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
