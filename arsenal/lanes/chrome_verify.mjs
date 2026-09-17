// Lane A receipt: First Light end to end in an isolated, muted Chrome, driven over the DevTools protocol.
// The Chrome gets a throwaway profile, so it never touches Daniel's own browser or its data.
//
//   node arsenal/lanes/chrome_verify.mjs [--clip "<library file name>"] [--out <dir>]
//
// Needs `py -m arsenal serve` on 127.0.0.1:8793, Chrome, and Node 22+ (global WebSocket and fetch).
// Writes first-light-chrome-<stamp>.json and .png to state/arsenal/receipts and exits 1 if the verdict fails.
// GPU lock (arsenal/GPU-LOCK.md): Chrome starts only under state/arsenal/gpu-render.lock, taken through gpu_lock.mjs after
// any jam_timing / jam_verify run ends; if the lock stays held past --gpu-wait-min (2) it prints ERROR and exits 1.
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";
import { acquireGpuLock } from "./gpu_lock.mjs";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const { values: opt } = parseArgs({
  options: {
    clip: { type: "string", default: "2026-09-06 10-32-02.mp4" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    app: { type: "string", default: "http://127.0.0.1:8793" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    "gpu-wait-min": { type: "string", default: "2" },  // then give up: `qm receipts` kills a run after 300 s
    port: { type: "string", default: "9333" },
    // No window at all, so a run can't steal focus from whatever Daniel is doing (a full-screen game, say).
    headless: { type: "boolean", default: false },
  },
});
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const profile = join(tmpdir(), `arsenal-chrome-verify-${stamp}`);
const jsonPath = join(opt.out, `first-light-chrome-${stamp}.json`);
const pngPath = join(opt.out, `first-light-chrome-${stamp}.png`);
mkdirSync(opt.out, { recursive: true });

const report = {
  api: "arsenal.receipt/v0", lane: "A", title: "First Light end to end in Chrome",
  started_at: new Date().toISOString(), clip: opt.clip, app: opt.app, headless: opt.headless,
  steps: [], samples: [], console: [], exceptions: [], media: {}, media_errors: [],
  not_measured: [
    "knob-to-screen latency p50/p95 (needs a person turning a knob)",
    "30-minute drift between media time and the analysis rows",
    "audio output (Chrome runs muted)",
  ],
};
const step = (name, data) => {
  report.steps.push({ name, at: new Date().toISOString(), ...data });
  console.log(`[${name}]`, JSON.stringify(data));
};

let gpu;
try {
  gpu = await acquireGpuLock({ label: "chrome_verify first-light", maxWaitMs: Number(opt["gpu-wait-min"]) * 60_000 });
} catch (err) {
  console.log("ERROR", err.message);
  process.exit(1);
}
report.gpu_lock = { acquired_at: gpu.owner.acquiredAt, inherited: gpu.inherited };

const chrome = spawn(opt.chrome, [
  `--remote-debugging-port=${opt.port}`, `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--mute-audio",
  // A covered or background window throttles rAF and timers, which would make every fps and drop number meaningless.
  "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding", "--disable-background-timer-throttling",
  "--autoplay-policy=no-user-gesture-required", "--window-size=1600,1000",
  ...(opt.headless ? ["--headless=new"] : []), "about:blank",
], { stdio: "ignore" });

async function getJSON(url) {
  const res = await fetch(url);
  return res.json();
}

async function waitFor(fn, timeoutMs, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      const value = await fn();
      if (value) return value;
    } catch { /* not ready yet */ }
    await delay(200);
  }
  throw new Error(`timed out waiting for ${what}`);
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(JSON.stringify(msg.error)));
        else res(msg.result);
      } else if (msg.method) {
        for (const listener of listeners) listener(msg);
      }
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => {
        const id = nextId++;
        pending.set(id, { res, rej });
        ws.send(JSON.stringify({ id, method, params }));
      }),
      on: (fn) => listeners.push(fn),
    });
    ws.onerror = () => reject(new Error(`websocket error on ${wsUrl}`));
  });
}

let browser;
try {
  const version = await waitFor(() => getJSON(`http://127.0.0.1:${opt.port}/json/version`), 20000, "Chrome DevTools");
  report.chrome = version.Browser;
  browser = await connect(version.webSocketDebuggerUrl);
  // grantPermissions rejects every permission it does not list, so both MIDI kinds go in one call.
  await browser.send("Browser.grantPermissions", { origin: opt.app, permissions: ["midi", "midiSysex"] });

  const target = (await getJSON(`http://127.0.0.1:${opt.port}/json/list`)).find((t) => t.type === "page");
  const page = await connect(target.webSocketDebuggerUrl);
  page.on((msg) => {
    const p = msg.params;
    if (msg.method === "Runtime.consoleAPICalled") {
      report.console.push({ type: p.type, text: p.args.map((a) => a.value ?? a.description ?? "").join(" ") });
    } else if (msg.method === "Runtime.exceptionThrown") {
      const d = p.exceptionDetails;
      report.exceptions.push({ text: d.text, description: d.exception?.description, line: d.lineNumber, url: d.url });
    } else if (msg.method === "Log.entryAdded") {
      if (p.entry.level === "error" || p.entry.level === "warning") {
        report.console.push({ type: `log-${p.entry.level}`, text: p.entry.text, url: p.entry.url });
      }
    } else if (msg.method === "Media.playerPropertiesChanged") {
      // The player's own account of its pipeline: kVideoDecoderName and kIsPlatformVideoDecoder are the evidence.
      for (const prop of p.properties) report.media[prop.name] = prop.value;
    } else if (msg.method === "Media.playerErrorsRaised") {
      report.media_errors.push(...p.errors);
    }
  });
  for (const domain of ["Runtime", "Log", "Page", "Media"]) await page.send(`${domain}.enable`);

  const evaluate = async (expression) => {
    const r = await page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const clickElement = async (elementExpr) => {
    const box = await evaluate(`(() => { const el = ${elementExpr}; if (!el) return null;
      el.scrollIntoView({ block: "center" }); const r = el.getBoundingClientRect();
      return { x: r.x + r.width / 2, y: r.y + r.height / 2, text: el.textContent.trim().slice(0, 80) }; })()`);
    if (box) {
      await page.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
      await page.send("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", clickCount: 1 });
      await page.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.x, y: box.y, button: "left", clickCount: 1 });
    }
    return box;
  };
  const hud = () => evaluate(`Object.fromEntries([...document.querySelectorAll('[id^="hud-"]')]
    .map((e) => [e.id, e.textContent.trim()]))`);
  const videoState = () => evaluate(`(() => { const v = document.getElementById("video");
    const q = v.getVideoPlaybackQuality ? v.getVideoPlaybackQuality() : null;
    return { t: v.currentTime, paused: v.paused, readyState: v.readyState, w: v.videoWidth, h: v.videoHeight,
             error: v.error && v.error.message, dropped: q && q.droppedVideoFrames, total: q && q.totalVideoFrames,
             bypass: !!document.querySelector(".gl-bypass") }; })()`);

  await page.send("Page.navigate", { url: `${opt.app}/first-light` });
  await waitFor(() => evaluate(`document.readyState === "complete" && document.querySelectorAll("#lib-list *").length > 0`),
                20000, "the page and its library");
  await delay(1000);
  report.webgl = await evaluate(`(() => { const g = document.getElementById("gl").getContext("webgl2"); if (!g) return null;
    const d = g.getExtension("WEBGL_debug_renderer_info");
    return { version: g.getParameter(g.VERSION), renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER) }; })()`);
  step("loaded", { webgl2: report.webgl, hud: await hud(),
                   shader_log: await evaluate(`document.getElementById("shader-log").textContent.trim().slice(0, 600)`) });

  const clicked = await clickElement(`(() => { const leaf = [...document.querySelectorAll("#lib-list *")]
    .find((e) => e.children.length === 0 && e.textContent.includes(${JSON.stringify(opt.clip)}));
    return leaf ? (leaf.closest("button, li, a, [role='button'], [data-id]") || leaf) : null; })()`);
  step("clip-clicked", { clicked });
  if (!clicked) throw new Error(`clip ${opt.clip} is not in #lib-list`);

  try {
    await waitFor(() => evaluate(`document.getElementById("video").readyState >= 2`), 20000, "video data");
  } catch (err) {
    // Say what the element was doing, so a timeout reads as a cause rather than a shrug.
    step("video-diagnostics", {
      video: await evaluate(`(() => { const v = document.getElementById("video");
        return { src: v.currentSrc, networkState: v.networkState, readyState: v.readyState,
                 error: v.error && v.error.message, paused: v.paused,
                 banner: (document.getElementById("banner-text") || {}).textContent || null }; })()`),
      hud: await hud(),
    });
    throw err;
  }
  if ((await videoState()).paused) step("play-clicked", { box: await clickElement(`document.getElementById("btn-play")`) });
  await waitFor(() => evaluate(`!document.getElementById("video").paused && document.getElementById("video").currentTime > 0.5`),
                15000, "playback");

  for (let i = 0; i < 6; i++) {
    await delay(1000);
    report.samples.push({ video: await videoState(), hud: await hud() });
  }
  step("playing", report.samples.at(-1));

  const shot = await page.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(pngPath, Buffer.from(shot.data, "base64"));
  report.screenshot = pngPath;

  // A seek bumps the epoch once; seeking near the end with loop on bumps it for the seek and again for the restart.
  await evaluate(`document.getElementById("video").currentTime = 3`);
  await delay(1500);
  step("seek", { epoch_after: (await hud())["hud-epoch"], video: await videoState() });
  await clickElement(`document.getElementById("btn-loop")`);
  await evaluate(`document.getElementById("video").currentTime = 14.6`);
  await delay(3000);
  step("loop", { loop: await evaluate(`document.getElementById("video").loop`),
                 epoch_after: (await hud())["hud-epoch"], video: await videoState() });

  await clickElement(`document.getElementById("btn-midi")`);
  await delay(1500);
  step("midi", { status: await evaluate(`document.getElementById("midi-status").textContent.trim()`) });
  step("plan", { head: await evaluate(`document.getElementById("plan-text").textContent.split("\\n")[0]`) });

  // Take the id from this page's own HUD: other clients may be opening takes at the same moment,
  // so "the newest take on the server" can belong to someone else.
  const takeId = /^\d{8}-\d{6}-[0-9a-f]{8}/.exec((await hud())["hud-take"] || "")?.[0];
  await page.send("Page.navigate", { url: "about:blank" });  // pagehide closes the take
  await delay(2500);
  if (takeId) {
    const take = await getJSON(`${opt.app}/api/take/${takeId}`);
    const kinds = {};
    let monotonic = true;
    let lastEpoch = 0;
    for (const e of take.events) {
      kinds[e.kind] = (kinds[e.kind] || 0) + 1;
      if (e.t.epoch < lastEpoch) monotonic = false;
      lastEpoch = Math.max(lastEpoch, e.t.epoch);
    }
    step("take-after-pagehide", { take_id: takeId, closed: take.take.closed, latest_epoch: take.take.latest_epoch,
                                  event_kinds: kinds, epochs_monotonic: monotonic, summary: take.take.summary });
  }
} catch (err) {
  step("error", { message: String((err && err.stack) || err) });
} finally {
  const seek = report.steps.find((s) => s.name === "seek");
  const loop = report.steps.find((s) => s.name === "loop");
  const take = report.steps.find((s) => s.name === "take-after-pagehide");
  const checks = {
    webgl2_on_the_gpu: !!report.webgl && !/swiftshader|software/i.test(report.webgl.renderer || ""),
    shader_compiled: /^compiled/.test(report.samples.at(-1)?.hud?.["hud-shader"] || ""),
    hardware_video_decoder: report.media.kIsPlatformVideoDecoder === "true",
    no_dropped_frames: loop?.video?.dropped === 0,
    epoch_bumps_on_seek_and_loop: seek?.epoch_after === "1" && loop?.epoch_after === "3",
    take_monotonic_and_closed: take?.closed === true && take?.epochs_monotonic === true,
    no_page_exceptions: report.exceptions.length === 0,
    no_media_errors: report.media_errors.length === 0,
    no_error_steps: !report.steps.some((s) => s.name === "error"),
  };
  report.verdict = { pass: Object.values(checks).every(Boolean), checks };
  report.finished_at = new Date().toISOString();
  writeFileSync(jsonPath, JSON.stringify(report, null, 2));
  try { await browser?.send("Browser.close"); } catch { /* already closed */ }
  await delay(1000);
  try { chrome.kill(); } catch { /* already gone */ }
  gpu.release();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
  console.log("decoder:", report.media.kVideoDecoderName, "| platform decoder:", report.media.kIsPlatformVideoDecoder);
  console.log("verdict:", JSON.stringify(report.verdict));
  console.log("receipt:", jsonPath);
  for (const e of report.exceptions) console.log("EXC", e.description || e.text);
  for (const c of report.console.filter((c) => /error|warn/.test(c.type))) console.log("CON", c.type, c.text, c.url || "");
  process.exit(report.verdict.pass ? 0 : 1);
}
