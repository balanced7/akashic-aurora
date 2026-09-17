// Node tests for arsenal/web/piano/looks/store.js. Zero dependencies:  node tests/piano_looks_store.test.mjs
// A fake server keeps the same contract as GET/PUT /api/piano/looks (arsenal/pianolooks.py: rev, 409 with the current list)
// and can drop off the network, answer like a server from before the route, or let "another window" save first.
import { CACHE_KEY, LOOKS_URL, MAX_PRESETS, STARTER_PRESETS, applyOp, createLooksStore } from "../arsenal/web/piano/looks/store.js";
import { LOOK_IDS, validateValue } from "../arsenal/web/piano/looks/registry.js";

let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
const eq = (label, got, want) => check(label, JSON.stringify(got) === JSON.stringify(want),
  `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
const clone = (o) => JSON.parse(JSON.stringify(o));
const sorted = (o) => Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : 1)));
const sameSettings = (a, b) => JSON.stringify(sorted(a)) === JSON.stringify(sorted(b));
async function rejects(label, promise, code) {
  try { await promise; check(label, false, "resolved"); } catch (e) { check(label, e.code === code, `${e.code}: ${e.message}`); }
}

function fakeServer() {
  const srv = { rev: 0, presets: [], down: false, answer: null, calls: [], beforePut: [] };
  const reply = (status, obj) => ({ status, ok: status >= 200 && status < 300, json: async () => clone(obj) });
  srv.fetch = async (url, init) => {
    srv.calls.push(init.method);
    if (url !== LOOKS_URL) return reply(404, { error: "no route" });
    if (srv.down) throw new TypeError("Failed to fetch");
    if (srv.answer) return reply(srv.answer, { error: srv.answer === 400 ? "look 1 needs a name of 1-60 characters" : "no route" });
    if (init.method === "GET") return reply(200, { api: "arsenal.piano.looks/v1", rev: srv.rev, presets: srv.presets });
    if (init.method !== "PUT" || init.headers["Content-Type"] !== "application/json") return reply(415, { error: "json only" });
    const other = srv.beforePut.shift();
    if (other) other(srv);
    const body = JSON.parse(init.body);
    if (body.rev !== srv.rev) return reply(409, { error: "changed", rev: srv.rev, presets: srv.presets });
    srv.rev += 1;
    srv.presets = clone(body.presets);
    return reply(200, { api: "arsenal.piano.looks/v1", rev: srv.rev, presets: srv.presets });
  };
  return srv;
}
function fakeStorage(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), map: m };
}
let clock = 1893456000000, ids = 0;
const make = (srv, storage = fakeStorage(), extra = {}) =>
  createLooksStore({ fetch: srv.fetch, storage, now: () => ++clock, newId: () => `look-${++ids}`, ...extra });
const otherWindowAdds = (preset) => (srv) => { srv.rev += 1; srv.presets = [...srv.presets, clone(preset)]; };
const LOOK = { scheme: "synth-vandor", instrument: "page", enabled: false, framing: "9:16", colour: "velocity" };

// ------------------------------------------------------------- starters --
eq("four starter looks", STARTER_PRESETS.map((p) => p.name), ["Classic", "Film cue", "Straight Roll", "Moonlit lake"]);
check("starters are built in, with ids no saved look can take", STARTER_PRESETS.every((p) => p.builtIn === true && /^builtin:/.test(p.id)));
check("starters are frozen", STARTER_PRESETS.every((p) => Object.isFrozen(p) && Object.isFrozen(p.settings)));
for (const p of STARTER_PRESETS) {
  check(`${p.name}: every value is valid for the page`, Object.entries(p.settings).every(([id, v]) => LOOK_IDS.includes(id) && validateValue(id, v) === null),
    JSON.stringify(p.settings));
}
eq("Classic", STARTER_PRESETS[0].settings, { scheme: "classic", instrument: "page", enabled: false, colour: "pitch", framing: "9:16" });
eq("Film cue", STARTER_PRESETS[1].settings, { framing: "16:9", enabled: false, quality: "ultra", scheme: "synth-sol", instrument: "concert-grand", colour: "mono" });
eq("Straight Roll", STARTER_PRESETS[2].settings, { scheme: "synth-vandor", instrument: "page", enabled: false, framing: "9:16" });
eq("Moonlit lake", STARTER_PRESETS[3].settings, { enabled: true, theme: "moon", harmonyMode: "tonnetz", framing: "9:16" });

// ------------------------------------------------------------ round trip --
{
  const srv = fakeServer(), storage = fakeStorage();
  let changes = 0;
  const store = make(srv, storage, { onChange: () => { changes++; } });
  eq("before load: the starters", store.list().map((p) => p.name), STARTER_PRESETS.map((p) => p.name));
  await store.load();
  check("load reaches the server", store.status().loaded && !store.status().offline && store.status().rev === 0);
  const saved = await store.save("  Rain at night  ", { ...LOOK, key: "E minor", minor: "relative", theme: { bad: 1 } });
  eq("save trims the name and keeps only look settings", [saved.name, sorted(saved.settings)], ["Rain at night", sorted(LOOK)]);
  check("save stamps created and updated", saved.created > 0 && saved.updated === saved.created && saved.id === "look-1");
  eq("the server holds it at rev 1", [srv.rev, srv.presets.map((p) => p.name)], [1, ["Rain at night"]]);
  eq("the list shows starters then saved looks", store.list().map((p) => p.name), [...STARTER_PRESETS.map((p) => p.name), "Rain at night"]);
  const cache = JSON.parse(storage.getItem(CACHE_KEY));
  eq("the browser copy mirrors the server", [cache.rev, cache.presets.map((p) => p.id), cache.pending], [1, ["look-1"], []]);

  const renamed = await store.rename("look-1", "Rain, slow");
  check("rename", renamed.name === "Rain, slow" && srv.presets[0].name === "Rain, slow" && srv.rev === 2);
  const fav = await store.setFavourite("look-1", true);
  check("favourite", fav.favourite === true && srv.presets[0].favourite === true && srv.rev === 3);
  const over = await store.save("Rain, slow", { ...LOOK, colour: "mono" }, { id: "look-1" });
  check("save over a look keeps its id, favourite and created", over.id === "look-1" && over.favourite === true
    && over.created === saved.created && over.settings.colour === "mono" && srv.presets.length === 1);
  const dup = await store.duplicate("look-1");
  check("duplicate a saved look", dup.name === "Rain, slow copy" && dup.id !== "look-1" && !dup.favourite
    && sameSettings(dup.settings, over.settings));
  const fromStarter = await store.duplicate("builtin:film-cue", "My film cue");
  check("duplicate a starter look", fromStarter.name === "My film cue" && !fromStarter.builtIn
    && sameSettings(fromStarter.settings, STARTER_PRESETS[1].settings));
  check("delete", (await store.delete("look-1")) === true && !srv.presets.some((p) => p.id === "look-1"));
  eq("the server and the list agree", store.list().filter((p) => !p.builtIn).map((p) => p.name), srv.presets.map((p) => p.name));
  check("every change told the drawer", changes >= 7, String(changes));
  const listed = store.list();
  listed[listed.length - 1].name = "tampered";
  check("list() hands out copies", store.list().at(-1).name !== "tampered");
  check("remove is delete", store.remove === store.delete);
}

// ------------------------------------------------------- refusals, local --
{
  const srv = fakeServer();
  const store = make(srv);
  await store.load();
  srv.calls.length = 0;
  await rejects("a starter can't be renamed", store.rename("builtin:classic", "Mine"), "builtin");
  await rejects("a starter can't be deleted", store.delete("builtin:classic"), "builtin");
  await rejects("a starter can't be saved over", store.save("Classic", LOOK, { id: "builtin:classic" }), "builtin");
  await rejects("a starter can't be starred", store.setFavourite("builtin:moonlit-lake", true), "builtin");
  await rejects("an empty name", store.save("", LOOK), "name");
  await rejects("a blank name", store.save("   ", LOOK), "name");
  await rejects("a 61-character name", store.save("x".repeat(61), LOOK), "name");
  await rejects("a name with a line break", store.save("one\ntwo", LOOK), "name");
  await rejects("a look with nothing in it", store.save("Empty", { key: "E minor" }), "settings");
  await rejects("renaming a look that isn't there", store.rename("look-missing", "X"), "missing");
  eq("refusals never reach the server", srv.calls, []);
  const sixty = await store.save("x".repeat(60), LOOK);
  check("a 60-character name is fine", sixty.name.length === 60);
}

// -------------------------------------------------------------- 100 cap --
{
  const srv = fakeServer();
  srv.presets = Array.from({ length: MAX_PRESETS }, (_, i) => ({ id: `look-full-${i}`, name: `Look ${i}`, settings: { colour: "pitch" } }));
  srv.rev = 5;
  const store = make(srv);
  await store.load();
  srv.calls.length = 0;
  await rejects("the 101st look is refused", store.save("One more", LOOK), "full");
  await rejects("... and so is a duplicate", store.duplicate("builtin:classic"), "full");
  eq("... without asking the server", srv.calls, []);
}

// ------------------------------------------------------------ conflicts --
{
  const srv = fakeServer();
  const store = make(srv);
  await store.load();
  await store.save("Mine", LOOK);
  srv.calls.length = 0;
  srv.beforePut.push(otherWindowAdds({ id: "look-other", name: "Other window", settings: { colour: "mono" } }));
  const second = await store.save("Also mine", { ...LOOK, framing: "16:9" });
  eq("409: load the server's list, apply the change again, retry once", srv.calls, ["PUT", "GET", "PUT"]);
  eq("... and both windows' looks are kept", srv.presets.map((p) => p.name), ["Mine", "Other window", "Also mine"]);
  check("... the new look is returned", second.name === "Also mine" && store.status().rev === srv.rev);

  srv.beforePut.push((s) => { s.rev += 1; s.presets = s.presets.map((p) => (p.name === "Mine" ? { ...p, name: "Renamed elsewhere" } : p)); });
  await store.delete(store.list().find((p) => p.name === "Also mine").id);
  eq("merge by id: their rename and my delete both land", srv.presets.map((p) => p.name), ["Renamed elsewhere", "Other window"]);

  srv.beforePut.push((s) => { s.rev += 1; s.presets = s.presets.filter((p) => p.id !== "look-other"); });
  const gone = await store.rename("look-other", "Too late");
  check("merge by id: renaming a look another window deleted does nothing", gone === null && !srv.presets.some((p) => p.id === "look-other"));

  srv.calls.length = 0;
  srv.beforePut.push(otherWindowAdds({ id: "look-x1", name: "X1", settings: { nns: "off" } }),
    otherWindowAdds({ id: "look-x2", name: "X2", settings: { nns: "off" } }));
  await rejects("a second 409 in a row gives up", store.save("Unlucky", LOOK), "conflict");
  eq("... after exactly one retry", srv.calls, ["PUT", "GET", "PUT"]);
  check("... leaving nothing half-saved", !srv.presets.some((p) => p.name === "Unlucky") && store.status().pending === 0);
  await store.load();
  eq("... and the next load shows the server's list", store.list().filter((p) => !p.builtIn).map((p) => p.name), srv.presets.map((p) => p.name));
}

// ---------------------------------------------------------- unreachable --
{
  const srv = fakeServer(), storage = fakeStorage();
  const store = make(srv, storage);
  await store.load();
  await store.save("Before the outage", LOOK);
  srv.down = true;
  const offline = await store.save("During the outage", { ...LOOK, colour: "mono" });
  check("no server: the look is still saved, in this browser", offline && offline.name === "During the outage");
  eq("... marked offline with one pending change", [store.status().offline, store.status().pending], [true, 1]);
  await store.rename(offline.id, "During the outage, renamed");
  await store.delete(store.list().find((p) => p.name === "Before the outage").id);
  eq("... later changes queue behind it", store.status().pending, 3);
  eq("... and the drawer shows them", store.list().filter((p) => !p.builtIn).map((p) => p.name), ["During the outage, renamed"]);
  eq("the server still has the old list", srv.presets.map((p) => p.name), ["Before the outage"]);

  const reopened = make(srv, storage);
  eq("a reload while the server is away starts from the browser copy", reopened.list().filter((p) => !p.builtIn).map((p) => p.name),
    ["During the outage, renamed"]);
  await reopened.load();
  check("... and load() keeps it", reopened.status().offline && reopened.list().some((p) => p.name === "During the outage, renamed"));

  srv.down = false;
  srv.rev += 1;
  srv.presets = [...srv.presets, { id: "look-phone", name: "Saved elsewhere meanwhile", settings: { colour: "pitch" } }];
  await reopened.load();
  eq("back online: pending changes are replayed onto the server's newer list", srv.presets.map((p) => p.name),
    ["Saved elsewhere meanwhile", "During the outage, renamed"]);
  eq("... nothing pending, not offline", [reopened.status().pending, reopened.status().offline], [0, false]);
  eq("... the browser copy matches", JSON.parse(storage.getItem(CACHE_KEY)).presets.map((p) => p.name), srv.presets.map((p) => p.name));
}
for (const status of [404, 405, 501, 503, 403]) {
  const srv = fakeServer();
  srv.answer = status;
  const store = make(srv);
  await store.load();
  const saved = await store.save("Kept here", LOOK);
  check(`a server answering ${status} (no looks route here) keeps looks in the browser`, saved && store.status().offline && store.status().pending === 1);
}
{
  const srv = fakeServer();
  const store = make(srv);
  await store.load();
  srv.answer = 400;
  await rejects("a refusal from the server is reported", store.save("Refused", LOOK), "refused");
  check("... with the server's words", store.status().lastError.includes("name of 1-60"));
  check("... and not kept as pending", store.status().pending === 0 && !store.list().some((p) => p.name === "Refused"));
  const noFetch = createLooksStore({ fetch: null, storage: fakeStorage() });
  const kept = await noFetch.save("No fetch at all", LOOK);
  check("no fetch available: still kept in the browser", kept && noFetch.status().offline);
}
{
  const srv = fakeServer();
  const store = make(srv, fakeStorage({ [CACHE_KEY]: "{not json" }));
  eq("an unreadable browser copy is ignored", store.list().length, STARTER_PRESETS.length);
  const junk = make(srv, fakeStorage({ [CACHE_KEY]: JSON.stringify({ rev: 2, presets: [{ id: "bad id!", name: 5 }, { id: "look-ok", name: "OK", settings: {} }], pending: [{ kind: "explode" }] }) }));
  eq("malformed looks and changes in the copy are dropped", [junk.list().filter((p) => !p.builtIn).map((p) => p.id), junk.status().pending], [["look-ok"], 0]);
}

// ------------------------------------------------------- one at a time --
{
  const srv = fakeServer();
  const store = make(srv);
  await store.load();
  srv.calls.length = 0;
  const [a, b, c] = await Promise.all([store.save("One", LOOK), store.save("Two", LOOK), store.save("Three", LOOK)]);
  eq("three saves at once go one after another, with no self-conflict", srv.calls, ["PUT", "PUT", "PUT"]);
  eq("... all kept in order", srv.presets.map((p) => p.name), ["One", "Two", "Three"]);
  check("... each resolves to its own look", a.name === "One" && b.name === "Two" && c.name === "Three");
}

// --------------------------------------------------------------- applyOp --
{
  const list = [{ id: "a", name: "A", settings: {} }, { id: "b", name: "B", settings: {} }];
  eq("applyOp save replaces in place", applyOp(list, { kind: "save", preset: { id: "a", name: "A2", settings: {} } }).map((p) => p.name), ["A2", "B"]);
  eq("applyOp delete of a missing id is a no-op", applyOp(list, { kind: "delete", id: "z" }).length, 2);
  check("applyOp never changes its input", list[0].name === "A" && list.length === 2);
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
