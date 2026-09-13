// Play Night receipt: sweep every preset in /play, first as a visualizer on a fake audio input, then
// over a library clip, in an isolated and muted Chrome driven over the DevTools protocol.
//
//   node arsenal/lanes/play_verify.mjs [--clip "<library file name>"] [--dwell 1500] [--out <dir>]
//
// Needs `py -m arsenal serve` on 127.0.0.1:8793, Chrome, Node 22+, and the page's test hook window.__play
// (presets, active, select, stats, errors, loadClip, setAudioSource). Writes play-<stamp>.json plus one
// screenshot per preset and mode under state/arsenal/receipts, and exits 1 if the verdict fails.
import { spawn } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { setTimeout as delay } from "node:timers/promises";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
const { values: opt } = parseArgs({
  options: {
    clip: { type: "string", default: "2026-09-06 10-32-02.mp4" },
    dwell: { type: "string", default: "1500" },
    out: { type: "string", default: join(REPO, "state", "arsenal", "receipts") },
    app: { type: "string", default: "http://127.0.0.1:8793" },
    chrome: { type: "string", default: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" },
    port: { type: "string", default: "9334" },
    // No window at all, so a run can't steal focus from whatever Daniel is doing (a full-screen game, say).
    headless: { type: "boolean", default: false },
  },
});
const dwellMs = Number(opt.dwell);
const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const shotDir = join(opt.out, `play-${stamp}`);
const jsonPath = join(opt.out, `play-${stamp}.json`);
const profile = join(tmpdir(), `arsenal-play-verify-${stamp}`);
mkdirSync(shotDir, { recursive: true });

const report = {
  api: "arsenal.receipt/v0", lane: "A", title: "Play Night preset sweep in Chrome",
  started_at: new Date().toISOString(), app: opt.app, clip: opt.clip, dwell_ms: dwellMs, headless: opt.headless,
  chrome: null, webgl: null, presets: [], sweeps: {}, clip_frames: null,
  console: [], exceptions: [], page_errors: [], media: {}, media_errors: [],
  not_measured: [
    "real audio devices: the visualizer sweep listens to Chrome's fake audio input",
    "MIDI: no controller is attached to the test browser",
    "how each preset looks to a person: the screenshots are for that",
  ],
};

const chrome = spawn(opt.chrome, [
  `--remote-debugging-port=${opt.port}`, `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--mute-audio",
  // A covered or background window throttles rAF and timers, which would make every fps and drop number meaningless.
  "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding", "--disable-background-timer-throttling",
  "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
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
      for (const prop of p.properties) report.media[prop.name] = prop.value;
    } else if (msg.method === "Media.playerErrorsRaised") {
      report.media_errors.push(...p.errors);
    }
  });
  for (const domain of ["Runtime", "Log", "Page", "Media"]) await page.send(`${domain}.enable`);

  // A page that never answers must become a named error, not a receipt that waits forever.
  const withTimeout = (promise, ms, what) => {
    let timer;
    return Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`no answer within ${ms} ms: ${what}`)), ms);
    })]).finally(() => clearTimeout(timer));
  };
  // userGesture lets the page resume its AudioContext as if the viewer had clicked.
  const evaluate = async (expression) => {
    const r = await withTimeout(
      page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }),
      45000, expression.replace(/\s+/g, " ").slice(0, 120));
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };

  await page.send("Page.navigate", { url: `${opt.app}/play` });
  await waitFor(() => evaluate(`!!(window.__play && document.readyState === "complete")`), 20000,
                "the Play page and its window.__play hook");
  await delay(2000);  // presets fetch and compile
  report.webgl = await evaluate(`(() => { for (const c of document.querySelectorAll("canvas")) {
      const g = c.getContext("webgl2"); if (!g) continue; const d = g.getExtension("WEBGL_debug_renderer_info");
      return { renderer: d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER) }; }
    return null; })()`);
  report.presets = await evaluate(`window.__play.presets()`);
  const playable = report.presets.filter((p) => !p.broken);
  console.log(`[presets] ${report.presets.length} listed, ${playable.length} playable`);

  const sweep = async (mode) => {
    const rows = [];
    for (const preset of playable) {
      const selected = await evaluate(`window.__play.select(${JSON.stringify(preset.id)})`);
      await delay(dwellMs);
      const active = await evaluate(`window.__play.active()`);
      const stats = await evaluate(`window.__play.stats()`);
      const shot = await withTimeout(page.send("Page.captureScreenshot", { format: "jpeg", quality: 70 }),
                                     30000, `screenshot ${mode}-${preset.id}`);
      const screenshot = join(shotDir, `${mode}-${preset.id}.jpg`);
      writeFileSync(screenshot, Buffer.from(shot.data, "base64"));
      rows.push({ id: preset.id, selected, active, stats, screenshot });
      console.log(`[${mode}] ${preset.id}: compiled=${active?.compiled} fps=${stats?.fps} level=${stats?.audio?.level}`);
    }
    return rows;
  };

  report.audio_source_visualizer = await evaluate(
    `Promise.resolve(window.__play.setAudioSource("input")).then(() => "input", (e) => "failed: " + e)`);
  await delay(1500);
  report.sweeps.visualizer = await sweep("visualizer");

  const clip = (await getJSON(`${opt.app}/api/library`)).clips.find((c) => c.name === opt.clip);
  if (!clip) throw new Error(`clip ${opt.clip} is not in the library`);
  await evaluate(`Promise.resolve(window.__play.loadClip(${JSON.stringify(clip.id)})).then(() => true)`);
  await waitFor(async () => {
    const s = await evaluate(`window.__play.stats()`);
    return s && s.hasVideo && s.total > 30;
  }, 20000, "clip playback");
  const before = await evaluate(`window.__play.stats()`);
  report.sweeps.clip = await sweep("clip");
  const after = await evaluate(`window.__play.stats()`);
  report.clip_frames = { dropped: after.dropped - before.dropped, total: after.total - before.total };
  report.page_errors = await evaluate(`window.__play.errors()`);
  await page.send("Page.navigate", { url: "about:blank" });  // pagehide closes the take
  await delay(1500);
} catch (err) {
  report.error = String((err && err.stack) || err);
  console.log("ERROR", report.error);
} finally {
  const compiledEverywhere = (rows) =>
    Array.isArray(rows) && rows.length > 0 && rows.every((r) => r.active?.compiled === true && r.active?.id === r.id);
  const maxLevel = Math.max(0, ...(report.sweeps.visualizer || []).map((r) => r.stats?.audio?.level || 0));
  const frames = report.clip_frames || { dropped: null, total: 0 };
  const checks = {
    presets_listed: report.presets.length > 0,
    every_playable_preset_compiled_as_visualizer: compiledEverywhere(report.sweeps.visualizer),
    every_playable_preset_compiled_over_the_clip: compiledEverywhere(report.sweeps.clip),
    input_audio_moves_the_meters: maxLevel > 0.05,
    hardware_video_decoder: report.media.kIsPlatformVideoDecoder === "true",
    dropped_frames_at_most_half_a_percent: frames.total > 0 && frames.dropped <= frames.total * 0.005,
    no_page_exceptions: report.exceptions.length === 0,
    no_media_errors: report.media_errors.length === 0,
    no_script_error: !report.error,
  };
  report.broken_presets = report.presets.filter((p) => p.broken).map((p) => ({ id: p.id, problem: p.problem }));
  report.verdict = { pass: Object.values(checks).every(Boolean), checks };
  report.finished_at = new Date().toISOString();
  writeFileSync(jsonPath, JSON.stringify(report, null, 2));
  try { await browser?.send("Browser.close"); } catch { /* already closed */ }
  await delay(1000);
  try { chrome.kill(); } catch { /* already gone */ }
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
  console.log("broken presets:", JSON.stringify(report.broken_presets));
  console.log("clip frames:", JSON.stringify(report.clip_frames), "| decoder:", report.media.kVideoDecoderName);
  console.log("verdict:", JSON.stringify(report.verdict));
  console.log("receipt:", jsonPath);
  for (const e of report.exceptions) console.log("EXC", e.description || e.text);
  process.exit(report.verdict.pass ? 0 : 1);
}
