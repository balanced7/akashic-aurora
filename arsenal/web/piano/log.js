// Practice log client: arsenal/web/piano/log.js (ES module). Contract: arsenal/PIANO-V2-SPEC.md sections 4 and 6.5.
//
//   const log = createPerformanceLog({ meta: { page: "piano" } });
//   log.noteOn(m, vel, t); log.noteOff(m, t); log.pedal(down, value, t); log.soundEnd(m, by, t); log.chord(info, t);
//   log.status();           // { state: "off"|"idle"|"live"|"buffering"|"uploading", session, sent, buffered, lastError }
//   log.setEnabled(false);  // stop recording; what is already buffered is kept, and still uploaded
//   log.timebase();         // { local, session, t0_perf_ms } of the session being recorded, or null
//
// t is page-clock seconds. A session starts lazily on the first note and ends after idleCloseMs without
// events, on setEnabled(false), on stop(), or on pagehide.
//
// The timebase (jam-spec 11.2, design-data 7.5). Every open, live, buffered or reopened, adds three fields to meta:
// page_id (the page that recorded the session: this log's pageId, which createPerformanceLog({ pageId }) sets
// so the jam transport's acks can share it; it must be unique per page load), t0_perf_ms (the page clock in ms at
// the session's t_ms 0) and opened_at_client (the browser's wall clock at t_ms 0). A session reopened after the
// server closed it keeps all three, because its t_ms still count from the same t0. timebase() hands the jam ack and
// template capture the same t0_perf_ms, the local id (the open's client_id, or its prefix after a reopen) and the
// server session (null until the open is answered).
//
// Nothing is sent per note. Every flushMs the queued events become one numbered batch in a local buffer
// (IndexedDB, or memory when IndexedDB is unavailable), and one uploader at a time (a Web Lock shared by
// every tab) sends the buffer in order: open, the batches, then close once the session has ended. When the
// server has no practice-log routes (a 404 "no route") or cannot be reached, the batches stay in the buffer
// and the uploader tries again, backing off to one try per uploadEveryMs, on this page or on the next one.
// Uploads cannot double up: open carries the local id as client_id and each batch carries its seq, and the
// server acknowledges a repeat without storing it twice. On pagehide the unsent tail and the session record
// also go to localStorage, which is synchronous, so a reload loses nothing IndexedDB had not committed.
// Nothing here ever throws into the caller.

const TAG = "[performance-log]";
const DB_NAME = "arsenal-performance-log";
const STASH_KEY = "arsenal-performance-log:stash";
const LOCK_NAME = "arsenal-performance-log:upload";
const KEEPALIVE_LIMIT = 60000;   // fetch keepalive and sendBeacon bodies share a 64 KB budget
const REQUEST_TIMEOUT_MS = 15000;
const RETRY_FIRST_MS = 2000;     // after a failed upload the next try waits this long, doubling up to uploadEveryMs
const LOCK_RETRY_MS = 1500;      // another tab holds the uploader: look again this soon
const LEASE_MS = 20000;          // a recording page refreshes its session's lease this often
const LEASE_STALE_MS = 180000;   // a session not refreshed for this long lost its page, so any page may upload it
const SOUND_END_BY = new Set(["release", "pedal", "repeat", "all-off"]);
const LETTERS = "CDEFGAB";
const PAGE_ID_RE = /^[A-Za-z0-9_.:-]{1,80}$/;  // as arsenal/jam/schemas.py PAGE_ID_RE
const WALL_SKEW_MAX_MS = 60000;  // a first note's t this far from performance.now() is not trusted for the wall clock

const clampInt = (x, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(x) || 0)));
const nowSec = () => performance.now() / 1000;
const bySeq = (a, b) => a.seq - b.seq;

function warn(...args) {
  try { console.warn(TAG, ...args); } catch { /* no console */ }
}

function randomHex(bytes) {
  const a = new Uint8Array(bytes);
  try { crypto.getRandomValues(a); } catch { for (let i = 0; i < bytes; i++) a[i] = Math.floor(Math.random() * 256); }
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
}

// Text for a note { name, octave }, a Theory spelling { letter: 0..6, acc }, a key { name }, or a string; else null.
function spellText(x) {
  if (typeof x === "string") return x;
  if (typeof x === "number" && Number.isFinite(x)) return String(+x.toFixed(3));
  if (x && typeof x === "object") {
    if (typeof x.name === "string") return x.name + (Number.isFinite(x.octave) ? x.octave : "");
    if (Number.isInteger(x.letter) && x.letter >= 0 && x.letter < 7) {
      const acc = clampInt(x.acc, -2, 2);
      return LETTERS[x.letter] + (acc > 0 ? "#".repeat(acc) : "b".repeat(-acc));
    }
  }
  return null;
}

async function post(url, body) {
  const text = JSON.stringify(body);
  const ctl = typeof AbortController === "function" ? new AbortController() : null;
  const timer = ctl ? setTimeout(() => ctl.abort(), REQUEST_TIMEOUT_MS) : 0;
  try {
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: text,
      keepalive: text.length < KEEPALIVE_LIMIT, signal: ctl ? ctl.signal : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch { /* not JSON */ }
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: String((err && err.message) || err) };
  } finally {
    clearTimeout(timer);
  }
}

const errorText = (r) => (r.data && typeof r.data.error === "string" ? r.data.error : "");
const describe = (r) => (r.status ? `${r.status} ${errorText(r)}`.trim() : `network error${r.error ? ": " + r.error : ""}`);
// The store answers "no session ..." or "not a session id ..." for a session it does not have; any other 404
// (Daniel's older server says "no route for ...") means the routes themselves are missing.
const sessionMissing = (r) => r.status === 404 && /^(no session|not a session id)/.test(errorText(r));
const transient = (r) => r.status === 0 || (r.status === 404 && !sessionMissing(r)) || r.status >= 500 ||
  r.status === 408 || r.status === 429;

function idbOpen() {
  return new Promise((resolve, reject) => {
    let req;
    try { req = indexedDB.open(DB_NAME, 1); } catch (err) { reject(err); return; }
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("sessions")) db.createObjectStore("sessions", { keyPath: "local" });
      if (!db.objectStoreNames.contains("batches")) db.createObjectStore("batches", { keyPath: ["local", "seq"] });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
    req.onblocked = () => reject(new Error("IndexedDB open blocked"));
  });
}

function idbReadAll(db) {
  return new Promise((resolve, reject) => {
    const out = { sessions: [], batches: [] };
    const tx = db.transaction(["sessions", "batches"], "readonly");
    tx.objectStore("sessions").getAll().onsuccess = (e) => { out.sessions = e.target.result || []; };
    tx.objectStore("batches").getAll().onsuccess = (e) => { out.batches = e.target.result || []; };
    tx.oncomplete = () => resolve(out);
    tx.onerror = tx.onabort = () => reject(tx.error || new Error("IndexedDB read aborted"));
  });
}

function readStash() {
  try {
    const value = JSON.parse(localStorage.getItem(STASH_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch { return []; }
}

function writeStash(entry) {
  try { localStorage.setItem(STASH_KEY, JSON.stringify([...readStash(), entry])); } catch { /* full or blocked: IndexedDB may still have it */ }
}

function removeStash(locals) {
  try {
    const left = readStash().filter((e) => !(e && e.rec && locals.has(e.rec.local)));
    if (left.length) localStorage.setItem(STASH_KEY, JSON.stringify(left));
    else localStorage.removeItem(STASH_KEY);
  } catch { /* blocked */ }
}

export function createPerformanceLog({
  endpoint = "/api/performance", flushMs = 1000, idleCloseMs = 300000, meta = {}, enabled = true,
  uploadEveryMs = 60000, maxBufferedEvents = 200000, maxBatch = 1000, storage = "indexeddb", pageId: pageIdOption = null,
} = {}) {
  const base = String(endpoint).replace(/\/+$/, "");
  let pageId = randomHex(6);
  if (pageIdOption != null) {
    if (typeof pageIdOption === "string" && PAGE_ID_RE.test(pageIdOption)) pageId = pageIdOption;
    else warn("pageId must be 1 to 80 letters, digits or _ . : -; using a random one");
  }
  let baseMeta = {};
  try { baseMeta = JSON.parse(JSON.stringify(meta || {})); } catch { warn("meta is not JSON; logging without it"); }
  let on = !!enabled;
  let stopped = false;

  // ---------------------------------------------------------------- the buffer --
  // Memory is the working copy; IndexedDB is the durable one, written behind it in order.
  // A record: { local, owner, lease_ms, created_ms, opened_at, t0_perf_ms, meta, next_seq, server_session, buffered,
  //             reopens, continued_from, lost, ended, events, sent }
  // opened_at and t0_perf_ms are the wall clock and the page clock at t_ms 0; records an older log.js stored have
  // no t0_perf_ms, and their opens go without it.
  const sessions = new Map();   // local id -> record
  const batches = new Map();    // local id -> [{ seq, events }], ascending seq
  let storedEvents = 0;         // events in batches: recorded, not yet accepted by the server
  let dbState = storage === "indexeddb" && typeof indexedDB !== "undefined" ? "opening" : "memory";
  const dbReady = dbState === "opening"
    ? idbOpen().then((db) => { dbState = "ready"; return db; },
      (err) => { dbState = "memory"; warn("IndexedDB is unavailable; buffering in memory only", err); return null; })
    : Promise.resolve(null);
  let writes = Promise.resolve();

  function persist(fn) {
    if (dbState === "memory" || dbState === "failed") return;
    writes = writes.then(() => dbReady).then((db) => db && dbState === "ready" && new Promise((resolve) => {
      const failed = (err) => {
        if (dbState !== "failed") warn("an IndexedDB write failed; buffering in memory only from here", err);
        dbState = "failed";
        resolve();
      };
      let tx;
      try {
        tx = db.transaction(["sessions", "batches"], "readwrite");
        fn(tx.objectStore("sessions"), tx.objectStore("batches"));
      } catch (err) { failed(err); return; }
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => failed(tx.error);
    }));
  }

  const saveSession = (rec) => persist((s) => { s.put(rec); });
  const listOf = (local) => { let list = batches.get(local); if (!list) batches.set(local, list = []); return list; };
  const storedOf = (rec) => (batches.get(rec.local) || []).reduce((n, b) => n + b.events.length, 0);
  const ordered = () => [...sessions.values()].sort((a, b) => a.created_ms - b.created_ms || (a.local < b.local ? -1 : 1));

  function addBatch(rec, events) {
    const batch = { seq: rec.next_seq++, events };
    listOf(rec.local).push(batch);
    storedEvents += events.length;
    rec.events += events.length;
    rec.lease_ms = Date.now();
    persist((s, b) => { b.put({ local: rec.local, seq: batch.seq, events }); s.put(rec); });
    return batch;
  }

  // Forget the batches the server already has (every seq up to uptoSeq).
  function removeBatches(rec, uptoSeq) {
    const list = batches.get(rec.local) || [];
    let n = 0;
    while (list.length && list[0].seq <= uptoSeq) n += list.shift().events.length;
    storedEvents -= n;
    if (n) persist((s, b) => { b.delete(IDBKeyRange.bound([rec.local, -Infinity], [rec.local, uptoSeq])); s.put(rec); });
    return n;
  }

  function forget(rec) {
    storedEvents -= storedOf(rec);
    sessions.delete(rec.local);
    batches.delete(rec.local);
    if (cur && cur.rec === rec) endRecording();
  }

  function dropSession(rec) {
    forget(rec);
    persist((s, b) => { s.delete(rec.local); b.delete(IDBKeyRange.bound([rec.local, -Infinity], [rec.local, Infinity])); });
    if (dbState !== "ready") removeStash(new Set([rec.local]));
  }

  function setForeign(rec, list) {
    storedEvents -= storedOf(rec);
    sessions.set(rec.local, rec);
    batches.set(rec.local, list);
    storedEvents += list.reduce((n, b) => n + b.events.length, 0);
  }

  // Other pages' sessions as IndexedDB has them: new ones, their new batches, and the ones they finished.
  async function refreshFromDb() {
    const db = await dbReady;
    if (!db || dbState !== "ready") return;
    await writes;
    let all;
    try { all = await idbReadAll(db); } catch (err) { warn("could not read the IndexedDB buffer", err); return; }
    const lists = new Map();
    for (const b of all.batches) {
      if (!lists.has(b.local)) lists.set(b.local, []);
      lists.get(b.local).push({ seq: b.seq, events: b.events });
    }
    const durable = new Set(all.sessions.map((r) => r.local));
    for (const rec of [...sessions.values()]) if (rec.owner !== pageId && !durable.has(rec.local)) forget(rec);
    for (const rec of all.sessions) {
      if (rec.owner === pageId) continue;  // this page's own sessions: memory is the truth
      setForeign(rec, (lists.get(rec.local) || []).sort(bySeq));
    }
  }

  // Sessions a page stashed on its way out: always ended. The IndexedDB copy wins where both exist.
  function importStash() {
    const entries = readStash();
    if (!entries.length) return;
    const locals = new Set();
    for (const entry of entries) {
      const rec = entry && entry.rec;
      if (!rec || typeof rec.local !== "string" || rec.owner === pageId) continue;
      locals.add(rec.local);
      const have = sessions.get(rec.local);
      const merged = { ...rec, ...(have || {}) };
      merged.ended = true;
      merged.next_seq = Math.max(Number(rec.next_seq) || 0, have ? have.next_seq : 0);
      merged.events = Math.max(Number(rec.events) || 0, have ? have.events : 0);
      const list = have ? [...(batches.get(rec.local) || [])] : [];
      const batch = entry.batch;
      const addIt = batch && Number.isInteger(batch.seq) && Array.isArray(batch.events) && !list.some((b) => b.seq === batch.seq);
      if (addIt) list.push({ seq: batch.seq, events: batch.events });
      setForeign(merged, list.sort(bySeq));
      persist((s, b) => { s.put(merged); if (addIt) b.put({ local: merged.local, seq: batch.seq, events: batch.events }); });
    }
    if (dbState === "ready") writes.then(() => { if (dbState === "ready") removeStash(locals); });
  }

  function enforceCap() {
    if (storedEvents <= maxBufferedEvents) return;
    const before = storedEvents;
    for (const rec of ordered()) {
      if (storedEvents <= maxBufferedEvents) break;
      if (!(cur && rec === cur.rec)) dropSession(rec);
    }
    const list = cur ? batches.get(cur.rec.local) || [] : [];
    while (storedEvents > maxBufferedEvents && list.length > 1) removeBatches(cur.rec, list[0].seq);
    const dropped = before - storedEvents;
    if (dropped) {
      counters.dropped += dropped;
      warn(`the buffer passed ${maxBufferedEvents} events, so the oldest ${dropped} were dropped`);
    }
  }

  // ------------------------------------------------------------------ recording --
  let cur = null;          // { rec, t0, queue, lastChord } while this page records a session
  let flushTimer = 0, idleTimer = 0, leaseTimer = 0;
  let lastPedal = null;    // remembered between sessions, so a session that starts under the pedal knows it
  let sent = 0;
  const counters = { recorded: 0, dropped: 0, opened: 0, closed: 0, beacons: 0 };
  const closedSessions = new Map();  // local id -> { session, summary }
  let lastSummary = null;

  const clock = (t) => (Number.isFinite(t) ? t : nowSec());
  const tms = (t) => Math.max(0, Math.round((t - cur.t0) * 1000));
  const recording = () => on && !stopped;

  function begin(t) {
    const now = Date.now();
    // t_ms 0 is the first event's t, which the caller may have stamped a moment before now: the page clock is kept to
    // the microsecond, and the wall clock is read at that same instant.
    const t0PerfMs = Math.round(t * 1e6) / 1e3;
    const skew = t0PerfMs - performance.now();
    const openedMs = Math.abs(skew) <= WALL_SKEW_MAX_MS ? Math.round(now + skew) : now;
    const rec = { local: `${now.toString(36)}-${randomHex(4)}`, owner: pageId, lease_ms: now, created_ms: now,
      opened_at: new Date(openedMs).toISOString(), t0_perf_ms: t0PerfMs, meta: baseMeta, next_seq: 0,
      server_session: null, buffered: offline, reopens: 0, continued_from: null, lost: 0, ended: false, events: 0, sent: 0 };
    sessions.set(rec.local, rec);
    batches.set(rec.local, []);
    saveSession(rec);
    cur = { rec, t0: t, queue: [], lastChord: "" };
    if (lastPedal && lastPedal.down) cur.queue.push({ t_ms: 0, kind: "pedal", down: true, value: lastPedal.value });
    clearInterval(leaseTimer);
    leaseTimer = setInterval(() => { if (cur) { cur.rec.lease_ms = Date.now(); saveSession(cur.rec); } }, LEASE_MS);
    pump();  // opens the server session now, so the state reads live within one request
  }

  function push(event) {
    cur.queue.push(event);
    counters.recorded++;
    if (!flushTimer) flushTimer = setTimeout(() => { flushTimer = 0; flushQueue(); }, flushMs);
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { idleTimer = 0; endSession(); }, idleCloseMs);
  }

  function flushQueue() {
    clearTimeout(flushTimer); flushTimer = 0;
    if (!cur || !cur.queue.length) return;
    const events = cur.queue.splice(0);
    for (let i = 0; i < events.length; i += maxBatch) addBatch(cur.rec, events.slice(i, i + maxBatch));
    enforceCap();
    pump();
  }

  function endRecording() {
    cur = null;
    clearTimeout(flushTimer); flushTimer = 0;
    clearTimeout(idleTimer); idleTimer = 0;
    clearInterval(leaseTimer); leaseTimer = 0;
  }

  // End the session being recorded: its tail becomes a batch, and the uploader closes it after the last batch.
  function endSession() {
    if (!cur) return null;
    flushQueue();
    if (!cur) return null;  // the cap dropped it
    const rec = cur.rec;
    endRecording();
    rec.ended = true;
    saveSession(rec);
    pump();
    return rec;
  }

  function onPageHide() {
    if (!cur) return;
    const rec = cur.rec;
    const events = cur.queue.splice(0);
    endRecording();
    const batch = events.length ? addBatch(rec, events) : null;
    rec.ended = true;
    saveSession(rec);
    writeStash({ rec, batch: batch && { seq: batch.seq, events: batch.events } });
    // When the upload has caught up, one beacon delivers the tail and the close now. If it never lands, the
    // stash still has both, and a resend of the same seq is acknowledged without being stored twice.
    const pending = (batches.get(rec.local) || []).length;
    if (!rec.server_session || offline || inFlight === rec.local || pending !== (batch ? 1 : 0)) return;
    const body = JSON.stringify(batch ? { events: batch.events, seq: batch.seq } : { events: [] });
    if (body.length >= KEEPALIVE_LIMIT) return;
    try {
      if (navigator.sendBeacon(`${base}/${rec.server_session}/close`, new Blob([body], { type: "application/json" }))) counters.beacons++;
    } catch { /* the stash has it */ }
  }

  // ------------------------------------------------------------------- uploader --
  let pumping = null, pumpAgain = false, inFlight = null;
  let needRefresh = true, stashPending = true;
  let offline = false, retryMs = 0, retryAt = 0, retryTimer = 0, lastError = null;

  function schedule(ms) {
    clearTimeout(retryTimer);
    retryTimer = setTimeout(() => { retryTimer = 0; pump(); }, ms);
  }

  async function withLock(fn) {
    const locks = typeof navigator !== "undefined" ? navigator.locks : null;
    if (!locks || typeof locks.request !== "function") { await fn(); return true; }
    return locks.request(LOCK_NAME, { ifAvailable: true }, async (lock) => {
      if (!lock) return false;
      await fn();
      return true;
    });
  }

  // One drain at a time per page; a call while one runs asks it to look again before it finishes.
  function pump() {
    if (pumping) { pumpAgain = true; return pumping; }
    if (Date.now() < retryAt) return Promise.resolve();
    pumping = (async () => {
      try {
        do {
          pumpAgain = false;
          if (!(await withLock(drain))) { schedule(LOCK_RETRY_MS); break; }
        } while (pumpAgain && Date.now() >= retryAt);
      } catch (err) {
        warn("the uploader failed", err);
      } finally {
        pumping = null;
      }
    })();
    return pumping;
  }

  async function drain() {
    if (needRefresh) { needRefresh = false; await refreshFromDb(); }
    if (stashPending) { stashPending = false; importStash(); }
    for (;;) {
      const job = nextJob();
      if (!job || !(await step(job))) return;
    }
  }

  function nextJob() {
    const now = Date.now();
    for (const rec of ordered()) {
      if (rec.owner !== pageId && !rec.ended) {
        if (now - (rec.lease_ms || 0) < LEASE_STALE_MS) continue;  // another page is still recording it
        rec.ended = true;  // its page is gone
        saveSession(rec);
      }
      const list = batches.get(rec.local) || [];
      if (!rec.server_session) {
        if (!list.length && rec.ended) { dropSession(rec); continue; }  // nothing of it is left to send
        return { rec, op: "open" };
      }
      if (list.length) return { rec, op: "events", batch: list[0] };
      if (rec.ended) return { rec, op: "close" };
    }
    return null;
  }

  // Resolves true to go on to the next job, false to stop and wait for the retry.
  async function step(job) {
    const { rec, op, batch } = job;
    let url, body;
    if (op === "open") {
      const m = { ...rec.meta };
      if (rec.buffered) m.buffered = true;
      if (rec.continued_from) m.continued_from = rec.continued_from;
      // The timebase, on every open (see the header): the recording page, not the one uploading.
      if (typeof rec.owner === "string") m.page_id = rec.owner;
      if (Number.isFinite(rec.t0_perf_ms)) m.t0_perf_ms = rec.t0_perf_ms;
      if (typeof rec.opened_at === "string") m.opened_at_client = rec.opened_at;
      url = `${base}/open`;
      body = { meta: m, client_id: rec.reopens ? `${rec.local}.${rec.reopens}` : rec.local };
    } else if (op === "events") {
      url = `${base}/${rec.server_session}/events`;
      body = { events: batch.events, seq: batch.seq };
    } else {
      url = `${base}/${rec.server_session}/close`;
      body = { events: [] };
    }
    inFlight = rec.local;
    const r = await post(url, body);
    inFlight = null;
    if (!sessions.has(rec.local)) return true;  // dropped while the request ran
    if (r.ok && (op !== "open" || (r.data && typeof r.data.session === "string"))) {
      offline = false; retryMs = 0; retryAt = 0; lastError = null;
      succeeded(job, r.data || {});
      return true;
    }
    if (r.ok || transient(r)) {
      if (op === "open") { rec.buffered = true; saveSession(rec); }
      retryMs = retryMs ? Math.min(uploadEveryMs, retryMs * 2) : Math.min(RETRY_FIRST_MS, uploadEveryMs);
      retryAt = Date.now() + retryMs;
      lastError = describe(r);
      if (!offline) warn(`the server is not taking the practice log (${lastError}); keeping events in this browser and retrying`);
      offline = true;
      schedule(retryMs);
      return false;
    }
    lastError = describe(r);
    if (r.status === 409) {
      closedOnServer(rec, Number.isInteger(r.data && r.data.last_seq) ? r.data.last_seq : -1);
    } else if (sessionMissing(r) && op !== "open") {
      if (++rec.lost > 3) {
        counters.dropped += storedOf(rec);
        warn(`the server keeps losing session ${rec.server_session}; dropping ${storedOf(rec)} buffered events`);
        dropSession(rec);
      } else {
        continueAsNew(rec);
      }
    } else if (op === "events") {
      counters.dropped += batch.events.length;
      warn(`the server refused a batch of ${batch.events.length} events`, lastError);
      removeBatches(rec, batch.seq);
    } else {
      counters.dropped += storedOf(rec);
      warn(`the server refused to ${op} a session; dropping ${storedOf(rec)} buffered events`, lastError);
      dropSession(rec);
    }
    return true;
  }

  function succeeded({ rec, op, batch }, data) {
    if (op === "open") {
      rec.server_session = data.session;
      if (data.resumed) {  // an open this browser sent before, whose answer it lost
        const last = Number.isInteger(data.last_seq) ? data.last_seq : -1;
        if (data.closed) { closedOnServer(rec, last); return; }
        removeBatches(rec, last);
      } else {
        counters.opened++;
      }
      saveSession(rec);
    } else if (op === "events") {
      const n = data.duplicate ? 0 : Number(data.accepted) || 0;
      sent += n;
      rec.sent += n;
      removeBatches(rec, batch.seq);
    } else {
      counters.closed++;
      lastSummary = { session: rec.server_session, summary: data.summary || null };
      closedSessions.set(rec.local, lastSummary);
      dropSession(rec);
    }
  }

  // The server session is closed: it holds every batch up to lastSeq. Anything later goes to a new session.
  function closedOnServer(rec, lastSeq) {
    removeBatches(rec, lastSeq);
    const left = (batches.get(rec.local) || []).length;
    if (!left && !(cur && cur.rec === rec)) { dropSession(rec); return; }
    continueAsNew(rec);
  }

  function continueAsNew(rec) {
    rec.continued_from = rec.server_session || rec.continued_from;
    rec.server_session = null;
    rec.reopens++;
    saveSession(rec);
  }

  function backlog() {
    const now = Date.now();
    for (const rec of sessions.values()) {
      if (cur && rec === cur.rec) {
        if ((batches.get(rec.local) || []).length > 2) return true;  // catching up on its own buffer
        continue;
      }
      if (rec.owner !== pageId && !rec.ended && now - (rec.lease_ms || 0) < LEASE_STALE_MS) continue;
      return true;
    }
    return false;
  }

  // -------------------------------------------------------------------- wiring --
  const tickTimer = setInterval(() => { needRefresh = true; pump(); }, uploadEveryMs);
  const onHidden = () => { if (document.visibilityState === "hidden") guard(flushQueue); };
  const onHide = () => guard(onPageHide);
  if (typeof window !== "undefined") {
    window.addEventListener("pagehide", onHide);
    document.addEventListener("visibilitychange", onHidden);
  }
  pump();  // upload whatever earlier pages left behind

  function guard(fn) {
    try { return fn(); } catch (err) { warn("internal error (ignored)", err); return undefined; }
  }

  return {
    noteOn(m, vel, t) {
      guard(() => {
        if (!recording()) return;
        const tt = clock(t);
        if (!cur) begin(tt);
        push({ t_ms: tms(tt), kind: "on", note: clampInt(m, 0, 127), vel: clampInt(vel, 1, 127) });
      });
    },
    noteOff(m, t) {
      guard(() => {
        if (!recording() || !cur) return;
        push({ t_ms: tms(clock(t)), kind: "off", note: clampInt(m, 0, 127) });
      });
    },
    pedal(down, value, t) {
      guard(() => {
        if (!recording()) return;
        lastPedal = { down: !!down, value: clampInt(value, 0, 127) };
        if (cur) push({ t_ms: tms(clock(t)), kind: "pedal", down: lastPedal.down, value: lastPedal.value });
      });
    },
    // by: "release" (finger up, no pedal), "pedal" (the lift ended it), "repeat" (re-struck), "all-off".
    soundEnd(m, by, t) {
      guard(() => {
        if (!recording() || !cur || !SOUND_END_BY.has(by)) return;
        push({ t_ms: tms(clock(t)), kind: "sound_end", note: clampInt(m, 0, 127), by });
      });
    },
    // info = { name, notes: [names or {name, octave}], key?, bass?, nns?, nns_key?, key_conf?, locked?, kind? } or null.
    // key and nns_key may be strings or {name}; bass a string or a Theory spelling; key_conf a string or number.
    // kind is Theory.detect's ("chord" | "interval" | "note" | "cluster"), sent as detect_kind so the analyzer
    // reads "E" (an octave) or "G5" (one note) the way the page did.
    // camelCase nnsKey and keyConf work too. Optional fields are sent only when the caller gives them.
    chord(info, t) {
      guard(() => {
        if (!recording() || !cur) return;
        let event = { kind: "chord", chord: null, notes: [], key: null };
        if (info) {
          event = { kind: "chord", chord: info.name == null ? null : String(info.name),
            notes: Array.isArray(info.notes) ? info.notes.map(spellText).filter((s) => typeof s === "string") : [],
            key: spellText(info.key) };
          const nnsKey = info.nns_key !== undefined ? info.nns_key : info.nnsKey;
          const keyConf = info.key_conf !== undefined ? info.key_conf : info.keyConf;
          if (info.bass !== undefined) event.bass = spellText(info.bass);
          if (info.nns !== undefined) event.nns = spellText(info.nns);
          if (nnsKey !== undefined) event.nns_key = spellText(nnsKey);
          if (keyConf !== undefined) event.key_conf = spellText(keyConf);
          if (info.locked !== undefined) event.locked = !!info.locked;
          const detectKind = info.detect_kind !== undefined ? info.detect_kind : info.kind;
          if (typeof detectKind === "string") event.detect_kind = detectKind;  // the event's own kind is "chord"
        }
        const signature = JSON.stringify(event);
        if (signature === cur.lastChord) return;  // the analyzer merges repeats anyway; don't send them
        cur.lastChord = signature;
        push({ t_ms: tms(clock(t)), ...event });
      });
    },
    // Move the queued events into the buffer and upload what can be uploaded. Resolves when that attempt ends.
    flush() {
      guard(flushQueue);
      return pump().then(() => undefined, () => undefined);
    },
    // End the session and stop recording. Resolves to { session, summary } once the server closed it, else null
    // (a buffered session stays in the browser and uploads from a later page).
    stop() {
      if (stopped) return Promise.resolve(null);
      const rec = guard(endSession);
      stopped = true;
      clearInterval(tickTimer);
      if (typeof window !== "undefined") {
        window.removeEventListener("pagehide", onHide);
        document.removeEventListener("visibilitychange", onHidden);
      }
      return pump().then(() => (rec && closedSessions.get(rec.local)) || null, () => null);
    },
    setEnabled(value) {
      guard(() => {
        value = !!value;
        if (value === on) return;
        on = value;
        if (!on) endSession();
      });
    },
    status() {
      let state = "idle";
      if (!on || stopped) state = "off";
      else if (offline && (cur || storedEvents > 0)) state = "buffering";
      else if (backlog()) state = "uploading";
      else if (cur) state = "live";
      return { state, session: (cur && cur.rec.server_session) || null, sent,
        buffered: storedEvents + (cur ? cur.queue.length : 0), lastError };
    },
    stats() {
      return { storage: dbState, page: pageId, enabled: on, stopped, offline, sent, stored: storedEvents,
        queued: cur ? cur.queue.length : 0, retryInMs: Math.max(0, retryAt - Date.now()), lastError, lastSummary,
        ...counters,
        sessions: ordered().map((r) => ({ local: r.local, server_session: r.server_session, mine: r.owner === pageId,
          ended: r.ended, events: r.events, sent: r.sent, batches: (batches.get(r.local) || []).length })) };
    },
    get session() { return (cur && cur.rec.server_session) || null; },
    // Read only. { local, session, t0_perf_ms } of the session being recorded, the values its open sends; session is
    // null until the server answers the open (a buffered session). null when no session is being recorded.
    timebase() {
      const tb = guard(() => (cur && Number.isFinite(cur.rec.t0_perf_ms)
        ? { local: cur.rec.local, session: cur.rec.server_session || null, t0_perf_ms: cur.rec.t0_perf_ms } : null));
      return tb || null;
    },
  };
}
