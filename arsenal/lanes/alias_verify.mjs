// arsenal/lanes/alias_verify.mjs -- RESOLUTION TRUTH and frame-time distribution for a page.
//
// WHY THIS EXISTS. "It must be performant AND render at perfect resolution with no aliasing" is two
// claims, and both were being argued by feel. There is a cheap hypothesis that has to be ruled out
// BEFORE any anti-aliasing technique can help: that one rendered pixel is one DEVICE pixel. If a
// canvas backing store is smaller than its CSS size times devicePixelRatio, the browser is
// upscaling the whole picture, and no amount of MSAA, SMAA or TAA buys that sharpness back -- the
// fix would be one line, not a rendering technique. So: measure resolution first, then frame time.
//
// WHAT IT REPORTS, per devicePixelRatio:
//   - every canvas: backing store, CSS size, DPR, and the FILL RATIO backing / (css * dpr).
//     1.0 means honest pixel-for-pixel rendering; below 1.0 means the page is drawing soft.
//   - the WebGL context: whether `antialias` was GRANTED (a request is not a grant), MAX_SAMPLES,
//     the unmasked renderer, and the drawing-buffer size the GPU actually got.
//   - a frame-time distribution at rest (p50/p95/p99 + dropped-frame count against the refresh).
//   - a PNG still, so the numbers and an eye can be pointed at the same frame.
//
// It runs HEADLESS by default: on this host a visible test browser steals focus from a full-screen
// game, and a measurement should never cost the operator his session.
//
// Run:
//   node arsenal/lanes/alias_verify.mjs
//   node arsenal/lanes/alias_verify.mjs --url http://127.0.0.1:8793/piano --dpr 1,1.5,2
//   node arsenal/lanes/alias_verify.mjs --window 2560x1440 --json

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock } from "./gpu_lock.mjs";

const REPO = join(import.meta.dirname, "..", "..");

const { values: opt } = parseArgs({
  options: {
    url: { type: "string", default: "http://127.0.0.1:8793/piano" },
    dpr: { type: "string", default: "1,1.5,2" },
    window: { type: "string", default: "1920x1080" },
    frames: { type: "string", default: "180" },
    out: { type: "string" },
    headless: { type: "boolean", default: true },
    json: { type: "boolean", default: false },
    "keep-profile": { type: "boolean", default: false },
  },
  allowPositionals: true,
});

const [winW, winH] = opt.window.split("x").map((n) => parseInt(n, 10));
const DPRS = opt.dpr.split(",").map((s) => parseFloat(s.trim())).filter((n) => n > 0);
const FRAMES = parseInt(opt.frames, 10);
const outDir = opt.out || join(REPO, "state", "arsenal", "receipts", "alias", `run-${stamp()}`);
mkdirSync(outDir, { recursive: true });

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

function chromePath() {
  const candidates = [
    process.env.CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    join(process.env.LOCALAPPDATA || "", "Google/Chrome/Application/chrome.exe"),
  ].filter(Boolean);
  for (const c of candidates) if (existsSync(c)) return c;
  throw new Error("chrome.exe not found -- set CHROME_PATH");
}

async function getJSON(url) {
  const res = await fetch(url);
  return res.json();
}

async function waitFor(fn, timeoutMs, what) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t0 > timeoutMs) throw new Error(`timed out waiting for ${what}`);
    await delay(150);
  }
}

// Minimal CDP client over Node's global WebSocket (the lane convention here).
function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    const pending = new Map();
    let id = 0;
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve: res, reject: rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(`${msg.error.message} (${msg.error.code})`));
        else res(msg.result);
      }
    };
    ws.onopen = () =>
      resolve({
        send(method, params = {}) {
          const myId = ++id;
          return new Promise((res, rej) => {
            pending.set(myId, { resolve: res, reject: rej });
            ws.send(JSON.stringify({ id: myId, method, params }));
          });
        },
        close: () => ws.close(),
      });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}

// One slice per evaluate: never return a big aggregate in a single round trip (a CDP timeout here
// would look like a page fault and send the next reader hunting the wrong thing).
const RESOLUTION_PROBE = `(() => {
  const out = [];
  const all = Array.from(document.querySelectorAll('canvas'));
  for (let i = 0; i < all.length; i++) {
    const cv = all[i];
    const rect = cv.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const want = Math.max(1, Math.round(rect.width * dpr)) * Math.max(1, Math.round(rect.height * dpr));
    const got = cv.width * cv.height;
    let gl = null, attrs = null, maxSamples = null, renderer = null, drawing = null;
    try {
      gl = cv.getContext('webgl2') || cv.getContext('webgl');
      if (gl) {
        attrs = gl.getContextAttributes();
        maxSamples = gl.getParameter(gl.MAX_SAMPLES);
        const dbg = gl.getExtension('WEBGL_debug_renderer_info');
        renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
        drawing = [gl.drawingBufferWidth, gl.drawingBufferHeight];
      }
    } catch (e) { /* a 2d canvas or a lost context: the geometry above still counts */ }
    out.push({
      index: i,
      id: cv.id || null,
      cls: cv.className || null,
      backing: [cv.width, cv.height],
      css: [Math.round(rect.width * 100) / 100, Math.round(rect.height * 100) / 100],
      dpr,
      wantPixels: want,
      gotPixels: got,
      fill: want > 0 ? Math.round((got / want) * 1000) / 1000 : null,
      antialias: attrs ? attrs.antialias : null,
      preserved: attrs ? attrs.preserveDrawingBuffer : null,
      alpha: attrs ? attrs.alpha : null,
      maxSamples: maxSamples === undefined ? null : maxSamples,
      drawingBuffer: drawing,
      renderer: renderer ? String(renderer).slice(0, 120) : null,
    });
  }
  return { dpr: window.devicePixelRatio || 1, inner: [window.innerWidth, window.innerHeight], canvases: out };
})()`;

// Frame pacing at rest: report the distribution, never a mean (a mean hides the stutter that a
// player actually feels, and the house rule is that a count never travels alone).
const FRAME_PROBE = (n) => `(async () => {
  const deltas = [];
  await new Promise((done) => {
    let last = performance.now();
    function tick(now) {
      deltas.push(now - last);
      last = now;
      if (deltas.length >= ${n}) done(); else requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
  return deltas;
})()`;

function quantile(sorted, q) {
  if (!sorted.length) return null;
  const i = Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))));
  return Math.round(sorted[i] * 100) / 100;
}

function frameStats(deltas) {
  const s = [...deltas].sort((a, b) => a - b);
  const p95 = quantile(s, 0.95);
  return {
    frames: deltas.length,
    p50: quantile(s, 0.5),
    p95,
    p99: quantile(s, 0.99),
    max: s.length ? Math.round(s[s.length - 1] * 100) / 100 : null,
    // A frame over 1.5x the p50 cadence is a visible hitch; we do not guess the refresh rate.
    over_1_5x_p50: deltas.filter((d) => d > 1.5 * (quantile(s, 0.5) || 16.7)).length,
  };
}

async function run() {
  const gpu = await acquireGpuLock({ label: "alias_verify" });
  const profile = join(tmpdir(), `alias-verify-${process.pid}`);
  let child, browser, page;
  try {
    const exe = chromePath();
    const args = [
      "--remote-debugging-port=0",
      `--user-data-dir=${profile}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--mute-audio",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--disable-background-timer-throttling",
      "--autoplay-policy=no-user-gesture-required",
      `--window-size=${winW},${winH}`,
      ...(opt.headless ? ["--headless=new"] : []),
      "about:blank",
    ];
    child = spawn(exe, args, { stdio: ["ignore", "pipe", "pipe"] });
    // Chrome writes its chosen debugging port to stderr when --remote-debugging-port=0. ONE listener
    // kept for the process's life: attaching inside the wait loop both warns and can miss the line.
    let devtoolsPort = null;
    child.stderr.on("data", (buf) => {
      const m = /DevTools listening on ws:\/\/127\.0\.0\.1:(\d+)\//.exec(String(buf));
      if (m) devtoolsPort = parseInt(m[1], 10);
    });
    const port = await waitFor(() => devtoolsPort, 15000, "chrome's debugging port");
    browser = await connect((await getJSON(`http://127.0.0.1:${port}/json/version`)).webSocketDebuggerUrl);
    const pageTarget = await waitFor(
      async () => (await getJSON(`http://127.0.0.1:${port}/json/list`)).find((t) => t.type === "page"),
      10000,
      "a page target",
    );
    page = await connect(pageTarget.webSocketDebuggerUrl);

    // Emulation has NO enable method (calling one is an "wasn't found" error, learned here).
    for (const domain of ["Page", "Runtime"]) await page.send(`${domain}.enable`);

    const rows = [];
    for (const dpr of DPRS) {
      await page.send("Emulation.setDeviceMetricsOverride", {
        width: winW, height: winH, deviceScaleFactor: dpr, mobile: false,
      });
      // A fresh navigation per DPR: the question is what the page does at LOAD time with this DPR,
      // which is where a fixed-internal-resolution renderer gives itself away.
      await page.send("Page.navigate", { url: opt.url });
      await delay(2500);
      const evalJSON = async (expression) => {
        const r = await page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
        if (r.exceptionDetails) throw new Error(r.exceptionDetails.text || "evaluate threw");
        return r.result.value;
      };
      const resolution = await evalJSON(RESOLUTION_PROBE);
      const deltas = await evalJSON(FRAME_PROBE(FRAMES));
      if (dpr === DPRS[0]) {
        const shot = await page.send("Page.captureScreenshot", { format: "png" });
        writeFileSync(join(outDir, `still-dpr${dpr}.png`), Buffer.from(shot.data, "base64"));
      }
      rows.push({ dpr, resolution, frame_stats: frameStats(deltas), frame_deltas: deltas.map((d) => Math.round(d * 100) / 100) });
    }

    await page.send("Page.navigate", { url: "about:blank" }).catch(() => {});
    const verdict = rows.map((r) => ({
      dpr: r.dpr,
      canvases: r.resolution.canvases.length,
      min_fill: r.resolution.canvases.length ? Math.min(...r.resolution.canvases.map((c) => (c.fill === null ? 1 : c.fill))) : null,
      antialias_granted: r.resolution.canvases.map((c) => c.antialias),
      p95_ms: r.frame_stats.p95,
    }));

    const report = {
      lane: "arsenal.alias_verify",
      url: opt.url,
      window: [winW, winH],
      headless: opt.headless,
      out_dir: outDir,
      rows,
      verdict,
      blind: [
        "this measures RESOLUTION TRUTH and FRAME PACING only -- it does not yet measure aliasing error itself",
        "headless rendering can differ from the visible window (compositor path, vsync); treat the numbers as a floor, and re-run with --no-headless on an idle machine before quoting them as the operator's experience",
        "devicePixelRatio is forced by the emulation override, so this says what the page DOES at each DPR, not what his display reports",
        "a page that has not been clicked may be paused by its own autoplay or idle logic; the still is the evidence for what was on screen",
      ],
    };
    console.log(JSON.stringify(report, opt.json ? null : 2));
    return report;
  } finally {
    try { await browser?.send("Browser.close"); } catch { /* already gone */ }
    try { page?.close(); } catch { /* already gone */ }
    if (child && !child.killed) child.kill();
    if (!opt["keep-profile"]) { try { rmSync(profile, { recursive: true, force: true }); } catch { /* best effort */ } }
    gpu.release();
  }
}

run().catch((e) => {
  console.error(`alias_verify failed: ${e.message}`);
  process.exitCode = 1;
});
