// Shared headless-Chrome CDP helpers for the adaptive-resolution lab. Never opens a visible window.
import { spawn } from "node:child_process";
import { rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

export async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    try { const v = await fn(); if (v) return v; } catch { /* not yet */ }
    await delay(200);
  }
  throw new Error(`timed out waiting for ${what}`);
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 1;
    const pending = new Map();
    const listeners = [];
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      } else if (msg.method) listeners.forEach((l) => l(msg));
    };
    ws.onopen = () => resolve({
      send: (method, params = {}) => new Promise((res, rej) => { const i = id++; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); }),
      on: (fn) => listeners.push(fn),
      close: () => ws.close(),
    });
    ws.onerror = () => reject(new Error("websocket error"));
  });
}

// opts: { port, width, height, dpr }
export async function launch({ port, width = 1280, height = 900, dpr = null }) {
  const profile = join(tmpdir(), `piano-lab-res-${port}-${Date.now()}`);
  const args = [
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
    "--mute-audio", "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling", "--headless=new", `--window-size=${width},${height}`,
  ];
  if (dpr) args.push(`--force-device-scale-factor=${dpr}`);
  args.push("about:blank");
  const chrome = spawn(CHROME, args, { stdio: "ignore" });
  const getJSON = async (url) => (await fetch(url)).json();
  const version = await waitFor(() => getJSON(`http://127.0.0.1:${port}/json/version`), 20000, "Chrome");
  const browser = await connect(version.webSocketDebuggerUrl);
  const target = (await getJSON(`http://127.0.0.1:${port}/json/list`)).find((t) => t.type === "page");
  const page = await connect(target.webSocketDebuggerUrl);
  const errors = [];
  page.on((msg) => {
    if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
    if (msg.method === "Runtime.consoleAPICalled" && /error|warn/.test(msg.params.type)) {
      const text = msg.params.args.map((a) => a.value ?? a.description).join(" ");
      if (!/X4122|X4008/.test(text)) errors.push(text);
    }
  });
  await page.send("Runtime.enable");
  await page.send("Page.enable");
  const evaluate = async (expression) => {
    const r = await page.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };
  const close = async () => {
    try { await browser.send("Browser.close"); } catch { /* closed */ }
    await delay(800);
    try { chrome.kill(); } catch { /* gone */ }
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* busy */ }
  };
  return { page, evaluate, errors, close };
}
