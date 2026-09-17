// Node tests for arsenal/lanes/gpu_lock.mjs, the shared GPU render lock with an owner stamp (arsenal/GPU-LOCK.md).
// Zero dependencies:  node tests/gpu_lock.test.mjs
// Every case runs on a throwaway lock directory under the system temp dir, never state/arsenal/gpu-render.lock, and stubs
// the jam-lane process scan, so it is safe to run while real render lanes hold the real lock. No Chrome, no GPU.
//   stamp      owner.json carries pid, command line, hostname, acquiredAt; the heartbeat moves; release removes it all
//   dead       a fake dead pid (fresh heartbeat, then also a stale one): reaped, and the reap log names the prior owner
//   stale      a live pid whose heartbeat stopped 2 minutes ago: reaped
//   cap        a live, beating owner past the 10-minute cap: reaped; the same age under a declared 30-minute cap: kept
//   live       a real holder in another process: not reaped, a waiter times out; hard-killed (the 2026-09-15 incident):
//              the waiter reaps it and takes the lock
//   legacy     a bare mkdir with no owner.json: kept at 0 s and at 4 minutes, reaped past the 5-minute grace
//   identity   a reap judged on one directory refuses a different directory at the same path
//   lost       a holder whose lock was reaped notices, and its release leaves the new owner's lock alone
//   exit       a holder that exits without calling release still removes the lock
//   signal     SIGINT with no other handler releases and exits 130; with the script's own process.once handler, releases and
//              lets that handler finish its cleanup
//   inherit    a child of the holder inherits the lock instead of waiting on its parent, and raises the cap if it needs longer
//   tombs      release leaves no tombstone behind; a tombstone older than 10 minutes is swept by the next holder
//   esm        a holder started as `node --input-type=module -e` keeps its heartbeat moving (the thread must not inherit that flag)
//   busy       a holder whose main thread is stuck in a synchronous step still beats (the heartbeat thread, not a timer)
//   jam        a waiter yields while a jam lane runs, and gives the lock back if one starts while it takes it
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, renameSync, rmSync, statSync, utimesSync, writeFileSync } from "node:fs";
import { hostname, tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import * as L from "../arsenal/lanes/gpu_lock.mjs";

const HELPER = new URL("../arsenal/lanes/gpu_lock.mjs", import.meta.url).href;
let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
async function rejects(promise) { try { await promise; return null; } catch (e) { return e; } }

const ROOT = mkdtempSync(join(tmpdir(), "gpu-lock-test-"));
let n = 0;
const lockPath = () => join(ROOT, `case-${++n}`, "gpu-render.lock");
const quiet = [];
const log = (m) => quiet.push(m);
const noJam = () => [];
const fast = { yieldToJam: false, pollMs: 100, heartbeatMs: 100, signals: false, log, jamPids: noJam };
const age = (p, ms) => { const t = new Date(Date.now() - ms); utimesSync(p, t, t); };
const reaps = (dir) => (existsSync(`${dir}.reaps.jsonl`) ? readFileSync(`${dir}.reaps.jsonl`, "utf8").trim().split("\n").map((l) => JSON.parse(l)) : []);

function fakeLock(dir, { pid, acquiredAgoMs = 1000, heartbeatAgoMs = 1000, maxHoldMs, token = "fake-" + Math.random() }) {
  mkdirSync(dir, { recursive: true });
  const at = Date.now() - acquiredAgoMs;
  writeFileSync(join(dir, "owner.json"), JSON.stringify({ api: "arsenal.gpu-lock/v1", token, pid, hostname: hostname(), label: "fake",
    command: "node fake_render.mjs", acquiredAt: new Date(at).toISOString(), acquiredAtMs: at, ...(maxHoldMs ? { maxHoldMs } : {}) }));
  writeFileSync(join(dir, "heartbeat"), "");
  age(join(dir, "heartbeat"), heartbeatAgoMs);
  return token;
}
function deadPid() {
  const r = spawnSync(process.execPath, ["-e", "console.log(process.pid)"], { encoding: "utf8" });
  return Number(r.stdout.trim());
}
function sleeper() { return spawn(process.execPath, ["-e", "setInterval(() => {}, 1000)"], { stdio: "ignore" }); }
const killHard = (pid) => spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" });

// a `node --input-type=module -e` process that takes the lock through the helper, prints a line, then does what `after` says
function holder(dir, after, { env = process.env, before = "", opts = "" } = {}) {
  const src = `import * as L from ${JSON.stringify(HELPER)};
    ${before}
    const h = await L.acquireGpuLock({ dir: ${JSON.stringify(dir)}, yieldToJam: false, heartbeatMs: 150, pollMs: 100, log: () => {}, ${opts} });
    console.log((h.inherited ? "INHERITED " : "HELD ") + h.owner.pid);
    ${after}`;
  const child = spawn(process.execPath, ["--input-type=module", "-e", src], { stdio: ["ignore", "pipe", "inherit"], env });
  let out = "";
  const line = new Promise((resolve) => { child.stdout.on("data", (d) => { out += d; if (out.includes("\n")) resolve(out.split("\n")[0].trim()); }); child.on("close", () => resolve(out.trim())); });
  const closed = new Promise((resolve) => child.on("close", (code) => resolve({ code, out })));
  return { child, line, closed };
}

const children = [];
try {
  // ------------------------------------------------------------------------------------------------------- stamp
  {
    const dir = lockPath();
    const h = await L.acquireGpuLock({ ...fast, dir, label: "stamp case" });
    const owner = JSON.parse(readFileSync(join(dir, "owner.json"), "utf8"));
    check("stamp: owner pid", owner.pid === process.pid, String(owner.pid));
    check("stamp: owner command line", /gpu_lock\.test\.mjs/.test(owner.command), owner.command);
    check("stamp: owner hostname", owner.hostname === hostname(), owner.hostname);
    check("stamp: owner acquiredAt", !Number.isNaN(Date.parse(owner.acquiredAt)) && Math.abs(Date.parse(owner.acquiredAt) - Date.now()) < 5000, owner.acquiredAt);
    check("stamp: default cap 10 minutes", owner.maxHoldMs === 10 * 60_000, String(owner.maxHoldMs));
    check("stamp: no temp file left", !existsSync(join(dir, `owner.json.${process.pid}.tmp`)));
    check("stamp: children inherit the token", process.env[L.TOKEN_ENV] === owner.token);
    age(join(dir, "heartbeat"), 30_000);
    await delay(450);
    const beat = Date.now() - statSync(join(dir, "heartbeat")).mtimeMs;
    check("stamp: the heartbeat thread refreshes the file", beat < 1000, `${beat} ms old`);
    const v = L.inspectGpuLock(dir);
    check("stamp: a live, beating holder is not stale", v.held && !v.stale && !v.legacy, JSON.stringify(v.reason));
    h.release();
    check("stamp: release removes the lock", !existsSync(dir));
    check("stamp: release clears the token", !process.env[L.TOKEN_ENV]);
    h.release();  // twice is harmless
  }

  // -------------------------------------------------------------------------------------------------------- dead
  for (const heartbeatAgoMs of [1000, 120_000]) {
    const dir = lockPath();
    const pid = deadPid();
    check(`dead: pid ${pid} is really gone`, !L.pidAlive(pid));
    fakeLock(dir, { pid, heartbeatAgoMs });
    const v = L.inspectGpuLock(dir);
    check(`dead (heartbeat ${heartbeatAgoMs} ms): judged stale on the pid`, v.stale && /not running/.test(v.reason), JSON.stringify(v.reason));
    const t0 = Date.now();
    const h = await L.acquireGpuLock({ ...fast, dir, maxWaitMs: 5000 });
    check(`dead (heartbeat ${heartbeatAgoMs} ms): a waiter takes it at once`, Date.now() - t0 < 2000, `${Date.now() - t0} ms`);
    const r = reaps(dir);
    check(`dead (heartbeat ${heartbeatAgoMs} ms): the reap is logged with the prior owner`, r.length === 1 && r[0].prior_owner.pid === pid && r[0].prior_owner.command === "node fake_render.mjs" && r[0].reaper.pid === process.pid, JSON.stringify(r));
    check(`dead (heartbeat ${heartbeatAgoMs} ms): the console says so`, quiet.some((m) => m.includes("REAPED") && m.includes(`pid ${pid}`)));
    check(`dead (heartbeat ${heartbeatAgoMs} ms): no tombstone left`, !readdirSync(dirname(dir)).some((f) => f.includes(".reaped-")));
    h.release();
  }

  // ------------------------------------------------------------------------------------------------------- stale
  {
    const live = sleeper(); children.push(live);
    await delay(200);
    const dir = lockPath();
    fakeLock(dir, { pid: live.pid, heartbeatAgoMs: 120_000 });
    const v = L.inspectGpuLock(dir);
    check("stale: a live pid with a 2-minute-old heartbeat is stale", L.pidAlive(live.pid) && v.stale && /heartbeat/.test(v.reason), JSON.stringify(v.reason));
    const fresh = lockPath();
    fakeLock(fresh, { pid: live.pid, heartbeatAgoMs: 45_000 });
    check("stale: a 45-second-old heartbeat is not", !L.inspectGpuLock(fresh).stale);
    const h = await L.acquireGpuLock({ ...fast, dir, maxWaitMs: 5000 });
    check("stale: reaped and taken", h.owner.pid === process.pid && reaps(dir).length === 1 && /heartbeat/.test(reaps(dir)[0].reason));
    h.release();

    // --------------------------------------------------------------------------------------------------------- cap
    const capped = lockPath();
    fakeLock(capped, { pid: live.pid, acquiredAgoMs: 11 * 60_000, heartbeatAgoMs: 2000 });
    const c = L.inspectGpuLock(capped);
    check("cap: a beating owner held 11 minutes is past the 10-minute cap", c.stale && /cap/.test(c.reason), JSON.stringify(c.reason));
    const declared = lockPath();
    fakeLock(declared, { pid: live.pid, acquiredAgoMs: 11 * 60_000, heartbeatAgoMs: 2000, maxHoldMs: 30 * 60_000 });
    check("cap: the same age under a declared 30-minute cap is kept", !L.inspectGpuLock(declared).stale);
    const huge = lockPath();
    fakeLock(huge, { pid: live.pid, acquiredAgoMs: 61 * 60_000, heartbeatAgoMs: 2000, maxHoldMs: 24 * 60 * 60_000 });
    check("cap: a declared cap is clamped to 60 minutes", L.inspectGpuLock(huge).stale);
    const h2 = await L.acquireGpuLock({ ...fast, dir: capped, maxWaitMs: 5000 });
    check("cap: reaped and taken", reaps(capped).length === 1);
    h2.release();
  }

  // -------------------------------------------------------------------------------------------------------- live
  {
    const dir = lockPath();
    const hold = holder(dir, "setInterval(() => {}, 1000);");
    children.push(hold.child);
    const line = await hold.line;
    check("live: the holder took the lock", /^HELD \d+$/.test(line), line);
    const holderPid = Number(line.split(" ")[1]);
    await delay(600);
    const v = L.inspectGpuLock(dir);
    check("live: not stale", v.held && !v.stale && v.owner.pid === holderPid && v.heartbeatAgeMs < 1000, JSON.stringify({ reason: v.reason, hb: v.heartbeatAgeMs }));
    age(join(dir, "heartbeat"), 30_000);  // --------------------------------------------------------------------------- esm
    await delay(700);
    const esmBeat = L.inspectGpuLock(dir).heartbeatAgeMs;
    check("esm: an --input-type=module holder's heartbeat keeps moving", esmBeat < 1000, `${esmBeat} ms old`);
    const err = await rejects(L.acquireGpuLock({ ...fast, dir, maxWaitMs: 1200 }));
    check("live: a waiter times out instead of reaping", err && /not taken/.test(err.message) && err.message.includes(`pid ${holderPid}`), String(err && err.message));
    check("live: the holder still owns it, nothing reaped", L.inspectGpuLock(dir).owner?.pid === holderPid && reaps(dir).length === 0);
    killHard(holderPid);  // no finally, no exit handler: what a tool timeout does
    const t0 = Date.now();
    const h = await L.acquireGpuLock({ ...fast, dir, maxWaitMs: 10_000 });
    const r = reaps(dir);
    check("live: after a hard kill a waiter reaps and takes it within seconds", h.owner.pid === process.pid && Date.now() - t0 < 5000, `${Date.now() - t0} ms`);
    check("live: the reap names the killed holder", r.length === 1 && r[0].prior_owner.pid === holderPid && /not running/.test(r[0].reason), JSON.stringify(r));
    h.release();
  }

  // ------------------------------------------------------------------------------------------------------ legacy
  {
    const dir = lockPath();
    mkdirSync(dir, { recursive: true });
    const v0 = L.inspectGpuLock(dir);
    check("legacy: a fresh bare lock is held, not stale", v0.held && v0.legacy && !v0.stale);
    age(dir, 4 * 60_000);
    check("legacy: at 4 minutes, not stale", !L.inspectGpuLock(dir).stale);
    const err = await rejects(L.acquireGpuLock({ ...fast, dir, maxWaitMs: 500 }));
    check("legacy: inside the grace a waiter waits", err && existsSync(dir) && reaps(dir).length === 0, String(err && err.message));
    age(dir, 6 * 60_000);
    const v = L.inspectGpuLock(dir);
    check("legacy: past 5 minutes, stale", v.stale && /no owner\.json/.test(v.reason), JSON.stringify(v.reason));
    const h = await L.acquireGpuLock({ ...fast, dir, maxWaitMs: 5000 });
    const r = reaps(dir);
    check("legacy: reaped, logged with no prior owner, taken", h.owner.pid === process.pid && r.length === 1 && r[0].prior_owner === null, JSON.stringify(r));
    h.release();
  }

  // ---------------------------------------------------------------------------------------------------- identity
  {
    const dir = lockPath();
    mkdirSync(dir, { recursive: true });
    age(dir, 6 * 60_000);
    const judged = L.inspectGpuLock(dir);
    rmSync(dir, { recursive: true });
    mkdirSync(dir);
    age(dir, 6 * 60_000);  // stale too, but a different directory than the one judged
    check("identity: a reap refuses a directory it did not judge", L.reapGpuLock(dir, judged, { log }) === null && existsSync(dir));
    check("identity: judged afresh, it reaps", L.reapGpuLock(dir, L.inspectGpuLock(dir), { log }) !== null && !existsSync(dir));
  }

  // -------------------------------------------------------------------------------------------------------- lost
  {
    const dir = lockPath();
    let lostWhy = null;
    const h = await L.acquireGpuLock({ ...fast, dir, onLost: (why) => { lostWhy = why; } });
    renameSync(dir, `${dir}.gone`);  // another process reaps it (say, past its cap) and takes it
    const theirs = fakeLock(dir, { pid: process.pid, heartbeatAgoMs: 0 });
    await delay(500);
    check("lost: the holder notices", h.lost && /pid/.test(String(lostWhy)), String(lostWhy));
    h.release();
    check("lost: its release leaves the new owner's lock alone", JSON.parse(readFileSync(join(dir, "owner.json"), "utf8")).token === theirs);
  }

  // -------------------------------------------------------------------------------------------------------- busy
  {
    const dir = lockPath();
    const hold = holder(dir, "await new Promise((r) => setTimeout(r, 300)); const t = Date.now(); while (Date.now() - t < 3000) {} process.exit(0);");
    children.push(hold.child);
    const line = await hold.line;
    check("busy: the holder took the lock", /^HELD/.test(line), line);
    await delay(500);  // inside the 3-second synchronous loop now
    age(join(dir, "heartbeat"), 30_000);
    await delay(900);
    const busyBeat = L.inspectGpuLock(dir).heartbeatAgeMs;
    check("busy: the heartbeat moves while the holder's main thread is blocked", busyBeat < 800, `${busyBeat} ms old`);
    await hold.closed;
  }

  // -------------------------------------------------------------------------------------------------------- exit
  {
    const dir = lockPath();
    const hold = holder(dir, "process.exit(0);");
    const line = await hold.line;
    await hold.closed;
    check("exit: the holder took the lock", /^HELD/.test(line), line);
    check("exit: exiting without release removes the lock", !existsSync(dir));
    const dir2 = lockPath();
    const drain = holder(dir2, "");  // no release, no process.exit: the event loop simply runs dry
    children.push(drain.child);
    const timer = setTimeout(() => killHard(drain.child.pid), 8000);
    const d = await drain.closed;
    clearTimeout(timer);
    check("exit: a holder whose event loop runs dry exits by itself and removes the lock", d.code === 0 && !existsSync(dir2), JSON.stringify(d));
  }

  // ------------------------------------------------------------------------------------------------------ signal
  {
    const dir = lockPath();
    const alone = holder(dir, "process.emit('SIGINT'); await new Promise((r) => setTimeout(r, 2000)); console.log('still running');");
    const a = await alone.closed;
    check("signal: SIGINT with no other handler releases and exits 130", a.code === 130 && !/still running/.test(a.out) && !existsSync(dir), JSON.stringify(a));
    const dir2 = lockPath();
    const own = holder(dir2, "process.emit('SIGINT');",
      { before: "process.once('SIGINT', async () => { console.log('cleanup start'); await new Promise((r) => setTimeout(r, 300)); console.log('cleanup done'); process.exit(3); });" });
    const b = await own.closed;
    check("signal: a script's process.once handler still finishes its cleanup", b.code === 3 && /cleanup done/.test(b.out) && !existsSync(dir2), JSON.stringify(b));
  }

  // ----------------------------------------------------------------------------------------------------- inherit
  {
    const dir = lockPath();
    const h = await L.acquireGpuLock({ ...fast, dir });
    const hold = holder(dir, "process.exit(0);", { env: { ...process.env }, opts: "maxHoldMs: 35 * 60_000" });
    const t0 = Date.now();
    const line = await hold.line;
    await hold.closed;
    check("inherit: a child of the holder inherits at once", line === `INHERITED ${process.pid}` && Date.now() - t0 < 5000, line);
    const after = L.inspectGpuLock(dir);
    check("inherit: the child's exit does not release the parent's lock", after.owner?.token === h.owner.token);
    check("inherit: a child that needs longer raises the cap", after.owner?.maxHoldMs === 35 * 60_000 && after.capMs === 35 * 60_000, String(after.owner?.maxHoldMs));
    h.release();
    check("inherit: the parent still releases it", !existsSync(dir));
  }

  // ------------------------------------------------------------------------------------------------------- tombs
  {
    const dir = lockPath();
    const oldTomb = `${dir}.reaped-4242-${Date.now() - 11 * 60_000}`, newTomb = `${dir}.released-4343-${Date.now() - 60_000}`;
    mkdirSync(oldTomb, { recursive: true });
    writeFileSync(join(oldTomb, "owner.json"), "{}");
    mkdirSync(newTomb, { recursive: true });
    const h = await L.acquireGpuLock({ ...fast, dir });
    check("tombs: a tombstone older than 10 minutes is swept by the next holder", !existsSync(oldTomb) && existsSync(newTomb));
    rmSync(newTomb, { recursive: true });
    h.release();
    check("tombs: release leaves no tombstone and no lock", !existsSync(dir) && !readdirSync(dirname(dir)).some((f) => /\.(released|reaped)-/.test(f)), readdirSync(dirname(dir)).join(","));
  }

  // --------------------------------------------------------------------------------------------------------- jam
  {
    const dir = lockPath();
    let calls = 0;
    const script = [[4242], [4242], []];
    const h = await L.acquireGpuLock({ ...fast, dir, yieldToJam: true, jamPollMs: 100, jamPids: () => script[Math.min(calls++, 2)] });
    check("jam: waits while a jam lane runs, then takes the lock", calls >= 4 && h.owner.pid === process.pid, `scan calls ${calls}`);
    h.release();
    let c2 = 0;
    const script2 = [[], [4343], [], []];
    const before = quiet.length;
    const h2 = await L.acquireGpuLock({ ...fast, dir, yieldToJam: true, jamPollMs: 100, jamPids: () => script2[Math.min(c2++, 3)] });
    check("jam: a jam lane that starts during the take gets the lock back first", quiet.slice(before).some((m) => /yielding/.test(m)) && c2 >= 4, `scan calls ${c2}`);
    h2.release();
    const h3 = await L.acquireGpuLock({ ...fast, dir, yieldToJam: false, jamPids: () => { throw new Error("scanned"); } });
    check("jam: the jam lanes themselves (yieldToJam false) never scan", h3.owner.pid === process.pid);
    h3.release();
  }
} catch (e) {
  check("the suite ran to the end", false, String(e && e.stack));
} finally {
  for (const c of children) if (c.exitCode === null) killHard(c.pid);
  await delay(300);
  try { rmSync(ROOT, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); } catch { /* temp */ }
}

console.log(`gpu_lock: ${pass} passed, ${fail} failed`);
if (fail && process.env.GPU_LOCK_TEST_VERBOSE) console.log(quiet.join("\n"));
process.exit(fail ? 1 : 0);
