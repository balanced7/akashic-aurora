// The shared GPU render lock (arsenal/GPU-LOCK.md): state/arsenal/gpu-render.lock, a directory, because mkdir either
// creates it or fails with EEXIST, atomically, for every process on this machine. The holder stamps owner.json inside it
// and a worker thread touches a heartbeat file every 15 s, so a waiter can tell a dead holder from a live one and reap
// the lock instead of retrying forever. On 2026-09-15 ab_shot.mjs died holding a bare lock, and every waiter spun for
// about 11 minutes until someone removed it by hand.
//
//   import { acquireGpuLock } from "./gpu_lock.mjs";
//   const gpu = await acquireGpuLock({ label: "lookdev burst" });  // waits out jam_timing / jam_verify runs, then the lock
//   try { /* headless Chrome work */ } finally { gpu.release(); }
//
//   node arsenal/lanes/gpu_lock.mjs status [--reap]                  who holds it and whether it is stale (reap it if so)
//   node arsenal/lanes/gpu_lock.mjs run [--label L] [--max-hold-min N] [--no-yield] -- <command> [args...]
//                                                                    one command under the lock (PowerShell or Python lanes)
import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmdirSync, rmSync, statSync, unlinkSync, utimesSync, writeFileSync } from "node:fs";
import { hostname } from "node:os";
import { basename, dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { isMainThread, parentPort, Worker, workerData } from "node:worker_threads";

const REPO = fileURLToPath(new URL("../..", import.meta.url));
export const LOCK_DIR = join(REPO, "state", "arsenal", "gpu-render.lock");
export const HEARTBEAT_EVERY_MS = 15_000;
export const HEARTBEAT_STALE_MS = 60_000;
export const HOLD_CAP_MS = 10 * 60_000;          // longer than the 3-minute burst rule
export const HOLD_CAP_CEILING_MS = 60 * 60_000;  // a holder may declare a longer cap (a 14-minute jam_timing run), never more
export const LEGACY_GRACE_MS = 5 * 60_000;       // a lock with no owner.json (an old-style mkdir) is reaped after this age
export const TOKEN_ENV = "ARSENAL_GPU_LOCK_TOKEN";  // children of a holder inherit the lock instead of waiting on it

const secs = (ms) => (ms >= 120_000 ? `${(ms / 60_000).toFixed(1)} min` : `${Math.round(ms / 1000)} s`);
const clampCap = (ms) => Math.min(HOLD_CAP_CEILING_MS, Math.max(60_000, Number(ms) || HOLD_CAP_MS));
const sleepSync = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

export function pidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === "EPERM"; }  // EPERM: it exists, we may not signal it
}

function readOwner(dir) {
  try { return JSON.parse(readFileSync(join(dir, "owner.json"), "utf8")); } catch { return null; }
}

// Windows refuses to unlink or rmdir for a moment while another handle is open (the heartbeat worker, a waiter reading)
function retrySync(fn) {
  for (let i = 0; ; i++) {
    try { return fn(); } catch (e) {
      if (e.code === "ENOENT") return undefined;
      if (i >= 25 || !["EPERM", "EBUSY", "EACCES", "ENOTEMPTY"].includes(e.code)) throw e;
      sleepSync(20);
    }
  }
}

export function describeOwner(owner) {
  if (!owner) return "no owner.json (an old-style lock)";
  return `pid ${owner.pid} on ${owner.hostname} (${owner.label}) since ${owner.acquiredAt}: ${String(owner.command).slice(0, 200)}`;
}

// What a waiter sees: { held: false } or { held, ino, owner, legacy, stale, reason, ages }. `ino` is the directory's NTFS
// file id; a reap acts only on the same directory it judged (a lock removed and taken again in between gets a new id).
export function inspectGpuLock(dir = LOCK_DIR, { now = Date.now(), alive = pidAlive, host = hostname() } = {}) {
  let st;
  try { st = statSync(dir, { bigint: true }); } catch (e) { if (e.code === "ENOENT") return { held: false }; throw e; }
  const ino = st.ino;
  const owner = readOwner(dir);
  if (!owner || !owner.token) {
    const dirAgeMs = now - Number(st.mtimeMs);
    const stale = dirAgeMs > LEGACY_GRACE_MS;
    return { held: true, ino, owner: null, legacy: true, dirAgeMs, stale,
             reason: stale ? `no owner.json and the directory is ${secs(dirAgeMs)} old (grace ${secs(LEGACY_GRACE_MS)})` : null };
  }
  const heldMs = now - (Number(owner.acquiredAtMs) || Number(st.mtimeMs));
  let heartbeatAgeMs;
  try { heartbeatAgeMs = now - statSync(join(dir, "heartbeat")).mtimeMs; } catch { heartbeatAgeMs = heldMs; }
  const capMs = clampCap(owner.maxHoldMs);
  let reason = null;
  // a pid means nothing on another host; there only the heartbeat and the cap can speak
  if (owner.hostname === host && !alive(owner.pid)) reason = `owner pid ${owner.pid} is not running`;
  else if (heartbeatAgeMs > HEARTBEAT_STALE_MS) reason = `heartbeat is ${secs(heartbeatAgeMs)} old (stale after ${secs(HEARTBEAT_STALE_MS)})`;
  else if (heldMs > capMs) reason = `held for ${secs(heldMs)}, past its ${secs(capMs)} cap`;
  return { held: true, ino, owner, legacy: false, heldMs, heartbeatAgeMs, capMs, stale: !!reason, reason };
}

// Remove a lock `verdict` judged stale. It judges again, moves the directory aside by rename (one reaper wins), checks it
// moved the directory it judged, then clears it and appends the reap to <dir>.reaps.jsonl. Returns the entry or null.
export function reapGpuLock(dir = LOCK_DIR, verdict, { log = console.log, ...judge } = {}) {
  if (!verdict || !verdict.stale) return null;
  const again = inspectGpuLock(dir, judge);
  if (!again.stale || again.ino !== verdict.ino || again.owner?.token !== verdict.owner?.token) return null;
  const tomb = `${dir}.reaped-${process.pid}-${Date.now()}`;
  try { renameSync(dir, tomb); } catch { return null; }  // gone, taken, or a handle still open: judge again next round
  let movedIno = null;
  // A concurrent reaper that opened the directory before our rename can still move it on from our name: it won, say nothing
  try { movedIno = statSync(tomb, { bigint: true }).ino; } catch { return null; }
  if (movedIno !== verdict.ino) {  // a fresh lock slipped in between the check and the rename: put it back
    try { renameSync(tomb, dir); log(`GPU lock: a reap raced a fresh lock and put it back`); } catch (e) {
      log(`GPU lock: a reap moved a fresh lock aside and could not put it back (${e.code}); its holder will see it lost: ${tomb}`);
    }
    return null;
  }
  try { rmSync(tomb, { recursive: true, force: true, maxRetries: 5, retryDelay: 50 }); } catch (e) { log(`GPU lock: could not clear ${tomb}: ${e.message}`); }
  const entry = {
    at: new Date().toISOString(), lock: dir, reason: verdict.reason, prior_owner: verdict.owner,
    ages_ms: { held: verdict.heldMs, heartbeat: verdict.heartbeatAgeMs, dir: verdict.dirAgeMs, cap: verdict.capMs },
    reaper: { pid: process.pid, hostname: hostname(), command: process.argv.join(" ") },
  };
  try { appendFileSync(`${dir}.reaps.jsonl`, JSON.stringify(entry) + "\n"); } catch (e) { log(`GPU lock: could not log the reap: ${e.message}`); }
  log(`GPU lock REAPED: ${verdict.reason}; prior owner ${describeOwner(verdict.owner)}`);
  return entry;
}

// One heartbeat: touch the file while owner.json carries `token`, else return why the lock is lost. A miss is read twice,
// 100 ms apart, so a reap that puts a fresh lock back, or a release moving someone else's lock aside, is not taken for a loss.
function beatOnce(dir, token) {
  for (let i = 0; ; i++) {
    const owner = readOwner(dir);
    if (owner && owner.token === token) break;
    if (i >= 1) return owner ? `owner.json now names pid ${owner.pid}` : "owner.json is gone";
    sleepSync(100);
  }
  try { const t = new Date(); utimesSync(join(dir, "heartbeat"), t, t); } catch { /* the next beat tries again */ }
  return null;
}

// The heartbeat runs this module again on a worker thread, so a holder whose main thread sits in a long synchronous step
// still beats. The worker gets no execArgv: a holder started as `node --input-type=module -e` must not pass that on.
if (!isMainThread && workerData && workerData.gpuLockHeartbeat) {
  const { dir, token, every } = workerData.gpuLockHeartbeat;
  const timer = setInterval(() => {
    const lost = beatOnce(dir, token);
    if (lost) { clearInterval(timer); parentPort.postMessage({ lost }); }
  }, every);
}

// Tombstones (<lock>.reaped-<pid>-<ms>, <lock>.released-<pid>-<ms>) left by a process killed while clearing one
function sweepTombs(dir) {
  try {
    for (const name of readdirSync(dirname(dir))) {
      const m = name.startsWith(`${basename(dir)}.`) && /\.(?:reaped|released)-\d+-(\d+)$/.exec(name);
      if (m && Date.now() - Number(m[1]) > 10 * 60_000) rmSync(join(dirname(dir), name), { recursive: true, force: true });
    }
  } catch { /* best effort */ }
}

// One attempt: null when the lock is held, else the handle { owner, inherited, lost, released, release() }.
export function tryAcquireGpuLock({ dir = LOCK_DIR, label = basename(process.argv[1] || "node"), maxHoldMs = HOLD_CAP_MS,
                                    heartbeatMs = HEARTBEAT_EVERY_MS, log = console.log, onLost = null, signals = true } = {}) {
  mkdirSync(dirname(dir), { recursive: true });
  // EPERM / EACCES / EBUSY: the name is still held by a directory Windows is deleting; it is free again in a moment
  try { mkdirSync(dir); } catch (e) { if (["EEXIST", "EPERM", "EACCES", "EBUSY"].includes(e.code)) return null; throw e; }
  const at = Date.now();
  const owner = {
    api: "arsenal.gpu-lock/v1", token: randomUUID(), pid: process.pid, ppid: process.ppid, hostname: hostname(), label,
    command: process.argv.join(" "), cwd: process.cwd(), acquiredAt: new Date(at).toISOString(), acquiredAtMs: at,
    maxHoldMs: clampCap(maxHoldMs), heartbeatMs,
  };
  let ino = null;
  try {  // heartbeat first, owner.json last and by rename, so a reader never sees a half-written owner
    ino = statSync(dir, { bigint: true }).ino;
    writeFileSync(join(dir, "heartbeat"), "");
    const tmp = join(dir, `owner.json.${process.pid}.tmp`);
    writeFileSync(tmp, JSON.stringify(owner, null, 1));
    renameSync(tmp, join(dir, "owner.json"));
  } catch (e) {
    try { if (ino !== null && statSync(dir, { bigint: true }).ino === ino) rmSync(dir, { recursive: true, force: true }); } catch { /* not ours, or gone */ }
    if (e.code === "ENOENT") return null;  // moved aside under us (a reap putting back what it raced): try again
    throw e;
  }
  sweepTombs(dir);
  const handle = { owner, inherited: false, lost: false, released: false, release: null };
  const lostBy = (why) => {
    if (handle.lost || handle.released) return;
    handle.lost = true;
    log(`GPU lock LOST: ${why}; another process reaped it, so this one no longer holds the GPU`);
    if (onLost) onLost(why);
  };
  let fallback = null;
  const worker = new Worker(new URL(import.meta.url), { execArgv: [], workerData: { gpuLockHeartbeat: { dir, token: owner.token, every: heartbeatMs } } });
  worker.on("message", (m) => { if (m.lost) lostBy(m.lost); });
  worker.on("error", (e) => {  // never leave a holder without a heartbeat: beat from the main thread instead
    if (handle.released || fallback) return;
    log(`GPU lock: the heartbeat thread failed (${e.message}); beating from the main thread`);
    fallback = setInterval(() => { const why = beatOnce(dir, owner.token); if (why) { clearInterval(fallback); lostBy(why); } }, heartbeatMs);
    fallback.unref();
  });
  worker.unref();  // after the listeners: a "message" listener added later refs the worker again and the holder never exits
  process.env[TOKEN_ENV] = owner.token;

  const handlers = {};
  const release = () => {
    if (handle.released) return;
    handle.released = true;
    worker.terminate().catch(() => {});
    if (fallback) clearInterval(fallback);
    process.removeListener("exit", release);
    for (const [sig, fn] of Object.entries(handlers)) process.removeListener(sig, fn);
    if (process.env[TOKEN_ENV] === owner.token) delete process.env[TOKEN_ENV];
    if (handle.lost) return;
    // Move the lock aside first, so it disappears in one step and no waiter sees it half removed; then check the moved
    // directory is ours (it is not if it was reaped and taken again) before removing owner.json and the directory.
    const tomb = `${dir}.released-${process.pid}-${Date.now()}`;
    try { retrySync(() => renameSync(dir, tomb)); } catch (e) {
      log(`GPU lock: release could not move the lock (${e.code}); a waiter reaps it once this process has exited`);
      return;
    }
    if (!existsSync(tomb)) return;  // already gone
    const moved = readOwner(tomb) || (sleepSync(50), readOwner(tomb));
    if (!moved || moved.token !== owner.token) {
      try { renameSync(tomb, dir); } catch (e) { log(`GPU lock: release moved another holder's lock aside and could not put it back (${e.code}): ${tomb}`); }
      return;
    }
    try {
      retrySync(() => unlinkSync(join(tomb, "owner.json")));
      retrySync(() => unlinkSync(join(tomb, "heartbeat")));
      retrySync(() => rmdirSync(tomb));
    } catch (e) { log(`GPU lock: released, but could not clear ${tomb} (${e.code}); the next holder sweeps it`); }
    log(`GPU lock released after ${secs(Date.now() - at)}`);
  };
  handle.release = release;
  process.on("exit", release);
  if (signals) {
    for (const [sig, code] of [["SIGINT", 130], ["SIGTERM", 143], ["SIGHUP", 129]]) {
      handlers[sig] = () => {
        const alone = process.listenerCount(sig) === 1;  // a handler of the script's own (even a once) exits its own way
        release();
        if (alone) process.exit(code);
      };
      process.prependListener(sig, handlers[sig]);  // first, so a script's process.once handler is still counted
    }
  }
  return handle;
}

// node.exe processes running jam_timing.mjs or jam_verify.mjs, other than this one (their receipts are load-sensitive).
// A gpu_lock.mjs wrapper around a jam lane is not one: two such wrappers would otherwise wait on each other forever.
export function foreignJamPids() {
  const r = spawnSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command",
    "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -match 'jam_timing\\.mjs|jam_verify\\.mjs' -and $_.CommandLine -notmatch 'gpu_lock\\.mjs' } | ForEach-Object { $_.ProcessId }"],
    { encoding: "utf8", windowsHide: true, timeout: 30_000 });
  return (r.stdout || "").split(/\r?\n/).map((s) => Number(s.trim())).filter((pid) => pid && pid !== process.pid);
}

// Wait for the lock and take it. Before each attempt it waits while a jam lane runs (yieldToJam; the jam lanes pass false),
// and it gives the lock straight back if a jam lane started while it was taking it. A stale lock is reaped and retried.
export async function acquireGpuLock({
  dir = LOCK_DIR, label = basename(process.argv[1] || "node"), yieldToJam = true, pollMs = 10_000, jamPollMs = 60_000,
  maxWaitMs = Infinity, maxHoldMs = HOLD_CAP_MS, heartbeatMs = HEARTBEAT_EVERY_MS, log = console.log, onLost = null,
  signals = true, jamPids = foreignJamPids,
} = {}) {
  const inheritedToken = process.env[TOKEN_ENV];
  if (inheritedToken) {
    let owner = readOwner(dir);
    if (owner && owner.token === inheritedToken && pidAlive(owner.pid)) {
      if (clampCap(maxHoldMs) > clampCap(owner.maxHoldMs)) {  // the run inside the wrapper needs longer than the wrapper asked
        const raised = { ...owner, maxHoldMs: clampCap(maxHoldMs) };
        try {
          const tmp = join(dir, `owner.json.${process.pid}.tmp`);
          writeFileSync(tmp, JSON.stringify(raised, null, 1));
          retrySync(() => renameSync(tmp, join(dir, "owner.json")));
          owner = raised;
        } catch (e) { log(`GPU lock: could not raise the inherited cap (${e.message})`); }
      }
      log(`GPU lock: inherited from pid ${owner.pid} (${owner.label}), cap ${secs(clampCap(owner.maxHoldMs))}`);
      return { owner, inherited: true, lost: false, released: false, release() {} };
    }
  }
  const t0 = Date.now();
  let told = null;
  const say = (key, text) => { if (told !== key) { told = key; log(text); } };
  for (;;) {
    if (Date.now() - t0 > maxWaitMs) {
      const v = inspectGpuLock(dir);
      throw new Error(`GPU lock: not taken after ${secs(maxWaitMs)}; ${v.held ? describeOwner(v.owner) : "free, but jam lanes kept running"}`);
    }
    if (yieldToJam) {
      const pids = jamPids();
      if (pids.length) { say(`jam ${pids}`, `GPU lock: jam_timing / jam_verify running (pids ${pids.join(", ")}); waiting ${secs(jamPollMs)} at a time`); await delay(jamPollMs); continue; }
    }
    const handle = tryAcquireGpuLock({ dir, label, maxHoldMs, heartbeatMs, log, onLost, signals });
    if (handle) {
      if (yieldToJam && jamPids().length) { handle.release(); say("jam-after", "GPU lock: a jam lane started while taking the lock; yielding to it"); continue; }
      log(`GPU lock taken (${label}, cap ${secs(handle.owner.maxHoldMs)})`);
      return handle;
    }
    const verdict = inspectGpuLock(dir);
    if (!verdict.held) {  // mkdir refused a free name (a directory Windows is still deleting): try again shortly
      say("unheld", "GPU lock: the lock directory could not be created though none is held; retrying");
      await delay(Math.min(pollMs, 250));
      continue;
    }
    if (verdict.stale && reapGpuLock(dir, verdict, { log })) continue;
    if (verdict.held) say(verdict.owner?.token || "legacy", `GPU lock held: ${describeOwner(verdict.owner)}; retrying every ${secs(pollMs)}`);
    await delay(pollMs * (0.8 + 0.4 * Math.random()));  // jitter, so two waiters do not step in lockstep
  }
}

// ------------------------------------------------------------------------------------------------------------ CLI
if (isMainThread && process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  const cut = argv.indexOf("--");
  const flags = cut < 0 ? argv : argv.slice(0, cut), command = cut < 0 ? [] : argv.slice(cut + 1);
  const flag = (name) => { const i = flags.indexOf(`--${name}`); return i < 0 ? null : flags[i + 1]; };
  const dir = flag("dir") || LOCK_DIR;
  if (flags[0] === "status") {
    const v = inspectGpuLock(dir);
    const out = v.held ? { lock: dir, ...v, ino: String(v.ino) } : { lock: dir, held: false };
    console.log(JSON.stringify(out, null, 1));
    if (flags.includes("--reap") && v.stale) process.exit(reapGpuLock(dir, v) ? 0 : 1);
  } else if (flags[0] === "run" && command.length) {
    const gpu = await acquireGpuLock({ dir, label: flag("label") || basename(command.slice(0, 2).join(" ")),
                                       maxHoldMs: flag("max-hold-min") ? Number(flag("max-hold-min")) * 60_000 : HOLD_CAP_MS,
                                       yieldToJam: !flags.includes("--no-yield") });
    const child = spawn(command[0], command.slice(1), { stdio: "inherit", windowsHide: true });
    const code = await new Promise((resolve) => { child.on("error", (e) => { console.error(e.message); resolve(127); }); child.on("close", (c) => resolve(c ?? 1)); });
    gpu.release();
    process.exit(code);
  } else {
    console.log("usage: node arsenal/lanes/gpu_lock.mjs status [--reap] [--dir D]\n" +
                "       node arsenal/lanes/gpu_lock.mjs run [--label L] [--max-hold-min N] [--no-yield] [--dir D] -- <command> [args...]");
    process.exit(2);
  }
}
