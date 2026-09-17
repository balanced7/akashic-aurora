// Saved looks for the Studio drawer: the four starter looks built into the page, and Daniel's own looks kept by the
// server (GET/PUT /api/piano/looks, arsenal/pianolooks.py) with a copy in this browser (arsenal.piano.looks.cache).
//
// store = createLooksStore({ fetch, storage, url, now, newId, onChange })
//   load()                     -> the list; asks the server, or keeps the browser copy when the server can't be reached
//   list(), get(id), status()  -> starters first, then saved looks; { offline, pending, rev, loaded, lastError, count, max }
//   save(name, settings, { id, favourite })  -> the saved look (a new one, or the look with that id overwritten)
//   rename(id, name), duplicate(id, name?), setFavourite(id, on), delete(id)  (remove is the same as delete)
// Every change is sent as the whole list with the rev it was based on. When another window saved first (409), the store
// loads the server's list, applies the same changes to it by look id, and tries once more. When the server can't be
// reached (no answer, a refusal from another address, or a server from before this route), the change is kept in the
// browser copy as pending and sent with the next load() or change that gets through. Starter looks are read-only;
// duplicate one to make your own.
import { cleanLook } from "./registry.js";

export const LOOKS_URL = "/api/piano/looks";
export const LOOKS_API = "arsenal.piano.looks/v1";
export const CACHE_KEY = "arsenal.piano.looks.cache";
export const MAX_PRESETS = 100;
export const MAX_NAME = 60;
const MAX_STRING = 200;
const ID = /^[A-Za-z0-9_-]{1,64}$/;
const CONTROL = /[\x00-\x1f\x7f]/;
// Answers that mean "this server can't keep looks for this page": another address than this machine (403), a server from
// before this route (404, 405, 501), or a gateway's (502-504). A failed or timed-out connection counts the same.
const UNREACHABLE = new Set([403, 404, 405, 501, 502, 503, 504]);
const TIMEOUT_MS = 6000;

const deepFreeze = (o) => { for (const v of Object.values(o)) if (v && typeof v === "object") deepFreeze(v); return Object.freeze(o); };
const starter = (id, name, settings) => deepFreeze({ id: `builtin:${id}`, name, builtIn: true, settings });

// Built in, read-only. A starter holds only the settings it is about; everything else stays as it is.
export const STARTER_PRESETS = Object.freeze([
  starter("classic", "Classic", { scheme: "classic", instrument: "page", enabled: false, colour: "pitch", framing: "9:16" }),
  starter("film-cue", "Film cue", { framing: "16:9", enabled: false, quality: "ultra", scheme: "synth-sol",
    instrument: "concert-grand", colour: "mono" }),
  starter("straight-roll", "Straight Roll", { scheme: "synth-vandor", instrument: "page", enabled: false, framing: "9:16" }),
  starter("moonlit-lake", "Moonlit lake", { enabled: true, theme: "moon", harmonyMode: "tonnetz", framing: "9:16" }),
]);

export class LooksError extends Error {
  constructor(message, { status = 0, code = "error" } = {}) {
    super(message);
    this.name = "LooksError";
    this.status = status;
    this.code = code;  // unreachable | conflict | refused | full | name | settings | builtin | missing | id
  }
}

const copy = (p) => (p ? JSON.parse(JSON.stringify(p)) : null);
const fullError = () => new LooksError(`You can keep up to ${MAX_PRESETS} looks. Delete one to make room.`, { code: "full" });

function browserStorage() {
  try { return globalThis.localStorage || null; } catch { return null; }
}

// A trimmed name of 1-60 characters, or a LooksError saying what is wrong.
export function checkName(name) {
  const text = typeof name === "string" ? name.trim() : "";
  if (!text) throw new LooksError("Give the look a name.", { code: "name" });
  if (text.length > MAX_NAME) throw new LooksError(`Keep the name to ${MAX_NAME} characters or fewer.`, { code: "name" });
  if (CONTROL.test(text)) throw new LooksError("The name can't hold tabs or line breaks.", { code: "name" });
  return text;
}

function checkSettings(settings) {
  const clean = cleanLook(settings);
  for (const [key, value] of Object.entries(clean)) {
    if (typeof value === "string" && value.length > MAX_STRING) throw new LooksError(`${key} is too long to save.`, { code: "settings" });
  }
  if (!Object.keys(clean).length) throw new LooksError("There is nothing in this look to save.", { code: "settings" });
  return clean;
}

const wellFormed = (p) => !!p && typeof p === "object" && typeof p.id === "string" && ID.test(p.id)
  && typeof p.name === "string" && !!p.settings && typeof p.settings === "object" && !Array.isArray(p.settings);

// One change applied to a list of saved looks, by look id. The same change replays onto a fresher list after a 409:
// a rename or favourite of a look another window deleted does nothing, and a delete of a look already gone does nothing.
export function applyOp(presets, op) {
  const list = presets.map(copy);
  const id = op.kind === "save" ? op.preset.id : op.id;
  const at = list.findIndex((p) => p.id === id);
  if (op.kind === "save") { if (at >= 0) list[at] = copy(op.preset); else list.push(copy(op.preset)); }
  else if (op.kind === "rename" && at >= 0) Object.assign(list[at], { name: op.name, updated: op.at });
  else if (op.kind === "favourite" && at >= 0) Object.assign(list[at], { favourite: op.on, updated: op.at });
  else if (op.kind === "delete" && at >= 0) list.splice(at, 1);
  return list;
}

const validOp = (op) => !!op && ((op.kind === "save" && wellFormed(op.preset))
  || (["rename", "favourite", "delete"].includes(op.kind) && typeof op.id === "string"));

export function createLooksStore({ fetch: fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null,
  storage = browserStorage(), url = LOOKS_URL, now = () => Date.now(), newId = null, onChange = null } = {}) {
  // confirmed: the list and rev the server last answered; pending: changes it has not taken yet (made while unreachable).
  // What the drawer shows is pending replayed on confirmed.
  const state = { confirmed: { rev: 0, presets: [] }, pending: [], offline: false, loaded: false, lastError: null };
  let chain = Promise.resolve();
  const view = (ops = state.pending) => ops.reduce(applyOp, state.confirmed.presets);

  // ------------------------------------------------------------- the copy
  try {
    const doc = JSON.parse((storage && storage.getItem(CACHE_KEY)) || "null");
    if (doc && Number.isInteger(doc.rev) && doc.rev >= 0 && Array.isArray(doc.presets)) {
      state.confirmed = { rev: doc.rev, presets: doc.presets.filter(wellFormed).slice(0, MAX_PRESETS) };
      state.pending = Array.isArray(doc.pending) ? doc.pending.filter(validOp) : [];
    }
  } catch { /* an unreadable copy is ignored; the server's list replaces it */ }

  function changed() {
    try {
      if (storage) storage.setItem(CACHE_KEY, JSON.stringify({ api: LOOKS_API, rev: state.confirmed.rev,
        presets: state.confirmed.presets, pending: state.pending, savedAt: now() }));
    } catch { /* private mode or a full quota: the server still holds the looks */ }
    if (typeof onChange === "function") {
      try { onChange(api.list(), api.status()); } catch (e) { console.error("[looks] onChange failed:", e); }
    }
  }

  // ------------------------------------------------------------ the server
  async function request(method, body) {
    if (typeof fetchImpl !== "function") throw new LooksError("There is no looks server to reach.", { code: "unreachable" });
    const init = { method, cache: "no-store", headers: { Accept: "application/json" } };
    if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
    let timer = null;
    if (typeof AbortController === "function") {
      const ctl = new AbortController();
      init.signal = ctl.signal;
      timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    }
    let res, reply = null;
    try {
      res = await fetchImpl(url, init);
      try { reply = await res.json(); } catch { reply = null; }
    } catch {
      throw new LooksError("The looks server can't be reached.", { code: "unreachable" });
    } finally {
      if (timer) clearTimeout(timer);
    }
    if (res.status === 409) throw new LooksError("Another window saved looks at the same moment. Try again.", { status: 409, code: "conflict" });
    if (UNREACHABLE.has(res.status)) throw new LooksError("The looks server isn't available here.", { status: res.status, code: "unreachable" });
    if (!res.ok) {
      throw new LooksError(reply && typeof reply.error === "string" ? reply.error : `The looks server answered ${res.status}.`,
        { status: res.status, code: "refused" });
    }
    if (!reply || !Number.isInteger(reply.rev) || !Array.isArray(reply.presets)) {
      throw new LooksError("The looks server sent something that isn't a list of looks.", { status: res.status, code: "refused" });
    }
    return { rev: reply.rev, presets: reply.presets.filter(wellFormed) };
  }

  // Send ops replayed on the confirmed list. On a 409: load the server's list, replay the same ops by look id, try once more.
  async function sync(ops) {
    for (let attempt = 0; ; attempt++) {
      const next = view(ops);
      if (next.length > MAX_PRESETS) throw fullError();
      try {
        state.confirmed = await request("PUT", { rev: state.confirmed.rev, presets: next });
        return;
      } catch (e) {
        if (e.code !== "conflict" || attempt > 0) throw e;
        state.confirmed = await request("GET");
      }
    }
  }

  function serial(job) {
    const run = chain.then(job, job);
    chain = run.catch(() => {});
    return run;
  }

  // One change: sent with any pending ones; kept as pending when the server can't be reached; dropped when refused.
  function mutate(op, result) {
    return serial(async () => {
      const ops = [...state.pending, op];
      if (view(ops).length > MAX_PRESETS) throw fullError();
      try {
        await sync(ops);
        Object.assign(state, { pending: [], offline: false, loaded: true, lastError: null });
      } catch (e) {
        if (e.code !== "unreachable") { state.lastError = e.message; changed(); throw e; }
        Object.assign(state, { pending: ops, offline: true, lastError: null });
      }
      changed();
      return result();
    });
  }

  // ----------------------------------------------------------- public api
  const findSaved = (id) => view().find((p) => p.id === id) || null;
  const findAny = (id) => STARTER_PRESETS.find((p) => p.id === id) || findSaved(id);
  function ownLook(id) {
    if (STARTER_PRESETS.some((p) => p.id === id)) {
      throw new LooksError("Starter looks can't be changed. Duplicate it to make your own.", { code: "builtin" });
    }
    const p = findSaved(id);
    if (!p) throw new LooksError("That look isn't saved any more.", { code: "missing" });
    return p;
  }
  function makeId() {
    for (let i = 0; i < 20; i++) {
      const id = typeof newId === "function" ? newId()
        : `look-${Math.floor(now()).toString(36)}-${Math.random().toString(36).slice(2, 8).padEnd(6, "0")}`;
      if (ID.test(id) && !findAny(id)) return id;
    }
    throw new LooksError("Couldn't make a new look id.", { code: "id" });
  }
  const attempt = (build, run) => { try { return run(build()); } catch (e) { return Promise.reject(e); } };

  const api = {
    starters: STARTER_PRESETS,
    load: () => serial(async () => {
      try {
        state.confirmed = await request("GET");
        Object.assign(state, { loaded: true, offline: false, lastError: null });
        if (state.pending.length) {
          try {
            await sync(state.pending);
            state.pending = [];
          } catch (e) {
            if (e.code === "unreachable") state.offline = true;
            else if (e.code !== "conflict") {  // the server won't take them; keeping them would block every later save
              state.lastError = `Changes made while the server was away couldn't be saved: ${e.message}`;
              state.pending = [];
            }
          }
        }
      } catch (e) {
        state.offline = e.code === "unreachable";
        if (!state.offline) state.lastError = e.message;
      }
      changed();
      return api.list();
    }),
    list: () => [...STARTER_PRESETS, ...view()].map(copy),
    get: (id) => copy(findAny(id)),
    status: () => ({ offline: state.offline, pending: state.pending.length, rev: state.confirmed.rev, loaded: state.loaded,
      lastError: state.lastError, count: view().length, max: MAX_PRESETS }),
    save: (name, settings, { id = null, favourite } = {}) => attempt(() => {
      const text = checkName(name), clean = checkSettings(settings), at = now();
      const preset = id === null || id === undefined
        ? { id: makeId(), name: text, settings: clean, created: at, updated: at }
        : { ...copy(ownLook(id)), name: text, settings: clean, updated: at };
      if (typeof favourite === "boolean") preset.favourite = favourite;
      return preset;
    }, (preset) => mutate({ kind: "save", preset }, () => copy(findSaved(preset.id)))),
    rename: (id, name) => attempt(() => { ownLook(id); return checkName(name); },
      (text) => mutate({ kind: "rename", id, name: text, at: now() }, () => copy(findSaved(id)))),
    setFavourite: (id, on) => attempt(() => ownLook(id),
      () => mutate({ kind: "favourite", id, on: !!on, at: now() }, () => copy(findSaved(id)))),
    duplicate: (id, name) => attempt(() => {
      const from = findAny(id);
      if (!from) throw new LooksError("That look isn't saved any more.", { code: "missing" });
      const text = checkName(name === undefined ? `${from.name} copy`.slice(0, MAX_NAME) : name), at = now();
      return { id: makeId(), name: text, settings: checkSettings(from.settings), created: at, updated: at };
    }, (preset) => mutate({ kind: "save", preset }, () => copy(findSaved(preset.id)))),
    delete: (id) => attempt(() => ownLook(id), () => mutate({ kind: "delete", id }, () => true)),
  };
  api.remove = api.delete;
  return api;
}
