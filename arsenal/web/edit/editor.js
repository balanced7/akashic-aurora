// arsenal/web/edit/editor.js
// Edit mode of the First Light page: the program monitor on the stage, the timeline dock under it, and the Media,
// Inspector, Mixer and Export panels in the rack (EDITOR v0 CONTRACT). first-light.js owns the Perform | Edit switch;
// this module wakes on the first switch to Edit and does nothing (no fetch, no timers) before that, so Perform mode
// runs exactly as it did.
//
// One writer at a time: the page edits the project document only through timeline.js, keeps a local undo stack,
// and saves debounced (600 ms) with the revision it last saw. A 409 means the CLI, an agent or another tab wrote
// first: the page takes their copy, says "changed elsewhere - reloaded", and starts a fresh undo stack.
//
// window.arsenalEdit is a read-mostly handle for agents and smoke runs: the document, the timing stats, and the
// same commit path the gestures use.

import * as T from "./timeline.js";
import * as api from "./api.js";
import { createTimelineView } from "./timeline-view.js";
import { createPlayback } from "./playback.js";
import { createBin } from "./bin.js";
import { createInspector } from "./inspector.js";
import { createMixer } from "./mixer.js";
import { createExportPanel } from "./render.js";

const PROJECT_KEY = "arsenal.edit.project";
const SAVE_DEBOUNCE_MS = 600;
const SAVE_RETRY_MS = 3000;
const JOB_POLL_MS = 1000;

const SHORTCUTS = [
  ["Space", "Play / pause"],
  ["S", "Split the clip under the playhead"],
  ["Delete", "Delete the selected clip (the lane closes up)"],
  ["Ctrl+Z", "Undo"],
  ["Ctrl+Shift+Z / Ctrl+Y", "Redo"],
  ["[ and ]", "Trim the selected clip's in / out to the playhead"],
  ["← →", "One frame back / forward (Shift: one second)"],
  ["↑ ↓", "Select the previous / next clip"],
  ["Home / End", "Go to the start / end"],
  ["+ / − / \\", "Zoom in / out / fit"],
  ["Ctrl+wheel", "Zoom around the pointer"],
  ["Alt while trimming", "Trim without snapping"],
  ["Esc", "Cancel a drag, close this help, clear the selection"],
];

const state = {
  started: false,
  pid: null,
  hist: T.createHistory(T.emptyProject()),
  live: null, // a document heard while a mixer slider moves, before it becomes an undo step
  serverRev: 0,
  media: new Map(), // mid -> entry
  selected: null,
  inspectMid: null,
  projects: [],
  save: { timer: 0, inflight: false, dirty: false, status: "", error: null, saves: 0, conflicts: 0 },
};

const $ = (id) => document.getElementById(id);
const doc = () => state.live || state.hist.present;
const isEdit = () => document.documentElement.getAttribute("data-mode") === "edit";

let view, playback, bin, inspector, mixer, exporter;
let ui = {};

// ---------------------------------------------------------------- media --

function entryFor(mid) {
  let e = state.media.get(mid);
  if (!e) {
    e = { mid, media: null, raw: null, jobs: null, peaks: new Map(), shots: [], keyframes: [], peaksState: "waiting for peaks",
      shotsState: "", demuxReady: false, polling: false, missing: false, fetched: { peaks: false, shots: false, keyframes: false } };
    state.media.set(mid, e);
  }
  return e;
}

function setMedia(raw) {
  const m = T.normalizeMedia(raw);
  if (!m || !m.id) return null;
  const e = entryFor(m.id);
  e.raw = raw;
  e.media = m;
  return e;
}

const jobDone = (s) => s === "done";
const jobOver = (s) => s === "done" || (typeof s === "string" && s.startsWith("error"));

/** Follows a media's background jobs (demux, peaks, shots) and fetches each result once it is done. */
async function track(mid) {
  const e = entryFor(mid);
  if (e.polling) return;
  e.polling = true;
  try {
    if (!e.fetched.keyframes) {
      e.fetched.keyframes = true;
      api.keyframes(mid).then((r) => { e.keyframes = Array.isArray(r.keyframes) ? r.keyframes : []; view.invalidate(); })
        .catch(() => { e.keyframes = []; });
    }
    for (;;) {
      let r;
      try {
        r = await api.media(mid);
      } catch (err) {
        if (err.status === 404) { e.missing = true; e.peaksState = "media missing on the server"; view.invalidate(); return; }
        await sleep(JOB_POLL_MS * 3);
        continue;
      }
      if (r.media) setMedia(r.media);
      e.jobs = r.jobs || { demux: "done", peaks: "done", shots: "done" };
      const j = e.jobs;
      if (jobDone(j.demux) && !e.demuxReady) { e.demuxReady = true; playback.refresh(); }
      if (!jobDone(j.demux) && jobOver(j.demux)) e.peaksState = `demux ${j.demux}`;
      if (jobDone(j.peaks) && !e.fetched.peaks) { e.fetched.peaks = true; await loadPeaks(e); }
      else if (jobOver(j.peaks) && !jobDone(j.peaks)) e.peaksState = `peaks ${j.peaks}`;
      else if (!jobOver(j.peaks)) e.peaksState = `peaks ${j.peaks || "queued"}…`;
      if (jobDone(j.shots) && !e.fetched.shots) { e.fetched.shots = true; await loadShots(e); }
      else if (jobOver(j.shots) && !jobDone(j.shots)) e.shotsState = `shots ${j.shots}`;
      bin.render();
      refreshInspector();
      view.invalidate();
      if (jobOver(j.demux) && jobOver(j.peaks) && jobOver(j.shots)) return;
      await sleep(JOB_POLL_MS);
    }
  } finally {
    e.polling = false;
  }
}

async function loadPeaks(e) {
  const n = e.media ? e.media.audio.length : 0;
  for (let i = 0; i < n; i++) {
    try {
      const p = T.toPeaks(await api.peaks(e.mid, i));
      if (p) e.peaks.set(i, p);
    } catch (err) {
      e.peaksState = err.notBuilt ? err.message : `peaks unavailable: ${err.message}`;
    }
  }
}

async function loadShots(e) {
  try {
    const r = await api.shots(e.mid);
    e.shots = (Array.isArray(r.cuts) ? r.cuts : []).filter((c) => Number.isFinite(c.t));
    e.shotsState = `${e.shots.length} cut${e.shots.length === 1 ? "" : "s"}`;
  } catch (err) {
    e.shotsState = err.notBuilt ? err.message : `shots unavailable: ${err.message}`;
  }
}

function infoFor(mid) {
  return state.media.get(mid) || null;
}

function binEntries() {
  return [...state.media.values()].filter((e) => e.media).map((e) => ({ media: e.media, jobs: e.jobs }));
}

// --------------------------------------------------------------- import --

async function importFiles(files, index = null) {
  const added = [];
  for (const f of files) {
    bin.message(`importing ${f.name}…`);
    try {
      const r = await api.importDropped(f);
      const e = setMedia(r.media || r);
      if (!e) throw new Error("the server answered without a media record");
      added.push(e.mid);
      track(e.mid);
    } catch (err) {
      const hint = err.body && err.body.hint ? ` ${err.body.hint}` : "";
      const why = err.message.includes(f.name) ? err.message : `${f.name}: ${err.message}`;
      const text = `${why.replace(/\.$/, "")}.${hint}`;
      bin.message(text, "error");
      banner(text);
      continue;
    }
  }
  bin.render();
  if (added.length) {
    bin.message(`imported ${added.length} file${added.length === 1 ? "" : "s"}`, "ok", 2500);
    if (index !== null) insertMedia(added, index);
  }
  return added;
}

async function importPath(path) {
  bin.message(`importing ${path}…`);
  try {
    const r = await api.importPath(path);
    const e = setMedia(r.media || r);
    track(e.mid);
    bin.render();
    bin.message(`imported ${e.media.name}`, "ok", 2500);
    return true;
  } catch (err) {
    const hint = err.body && err.body.hint ? ` ${err.body.hint}` : "";
    bin.message(`${err.message}.${hint}`, "error");
    return false;
  }
}

function insertMedia(mids, index = Infinity) {
  let d = doc();
  let last = null;
  let i = index;
  for (const mid of mids) {
    const e = state.media.get(mid);
    if (!e || !e.media) continue;
    if (!(e.media.duration > 0)) { bin.message(`${e.media.name}: its duration is unknown, so it cannot go on the timeline`, "error"); continue; }
    const r = T.insertClip(d, e.media, i);
    d = r.doc;
    last = r.clip;
    if (Number.isFinite(i)) i += 1;
  }
  if (d !== doc()) {
    commit(d);
    if (last) select(last);
  }
}

// ----------------------------------------------------------------- edit --

let lastMerge = { key: "", at: 0 };

/**
 * Records an edit. merge names a run of small steps (a gain slider moved by keyboard, one step per key) that should
 * undo as one: the same key within a second replaces the present instead of stacking another step.
 */
function commit(next, merge = "") {
  if (!next || next === state.hist.present) return;
  state.live = null;
  const now = performance.now();
  const same = merge && merge === lastMerge.key && now - lastMerge.at < 1000 && T.canUndo(state.hist);
  state.hist = same ? T.replacePresent({ ...state.hist, future: [] }, next) : T.commit(state.hist, next);
  lastMerge = { key: merge, at: now };
  afterChange();
  scheduleSave();
}

function undo() {
  view.cancelGesture();
  if (!T.canUndo(state.hist)) return;
  state.hist = T.undo(state.hist);
  afterChange();
  scheduleSave();
}

function redo() {
  view.cancelGesture();
  if (!T.canRedo(state.hist)) return;
  state.hist = T.redo(state.hist);
  afterChange();
  scheduleSave();
}

function afterChange() {
  const d = doc();
  if (state.selected && !d.clips.some((c) => c.id === state.selected)) select(null);
  view.invalidate();
  mixer.render(d);
  playback.refresh();
  playback.forget(new Set(d.clips.map((c) => c.media_id)));
  refreshInspector();
  refreshToolbar();
}

function select(id) {
  state.selected = id;
  if (id) {
    const c = doc().clips.find((x) => x.id === id);
    if (c) state.inspectMid = c.media_id;
  }
  if (view.selected !== id) view.select(id);
  refreshInspector();
  refreshToolbar();
}

/** The frame grid ({fps, start_s}) of a media's video, else the doc's rate from 0. */
function gridOf(mid) {
  const e = mid ? infoFor(mid) : null;
  return T.frameGrid(e && e.media, e && e.keyframes, T.docFps(doc()));
}

/** The frame rate of the source under the playhead (a frame step moves by one of its frames), else the doc's. */
function fpsAt(t) {
  const h = T.clipAtTime(doc(), t);
  return gridOf(h ? h.clip.media_id : null).fps;
}

function split() {
  const h = T.clipAtTime(doc(), playback.time);
  const { fps, start_s } = gridOf(h ? h.clip.media_id : null);
  commit(T.splitClip(doc(), playback.time, { newId: T.newId(), fps, start_s }));
}

function deleteSelected() {
  if (!state.selected) return;
  commit(T.deleteClip(doc(), state.selected));
}

function trimToPlayhead(edge) {
  const d = doc();
  const c = d.clips.find((x) => x.id === state.selected);
  if (!c) return;
  const e = infoFor(c.media_id);
  const src = c.src_in + (playback.time - c.at);
  const { fps, start_s } = gridOf(c.media_id);
  commit(T.trimClip(d, c.id, edge, src, { mediaDuration: e && e.media ? e.media.duration : Infinity, fps, start_s }));
}

function selectStep(delta) {
  const order = T.videoClips(doc());
  if (!order.length) return;
  const i = order.findIndex((c) => c.id === state.selected);
  const next = order[Math.max(0, Math.min(order.length - 1, i < 0 ? 0 : i + delta))];
  select(next.id);
  view.focusClip(next.id);
}

// ----------------------------------------------------------------- save --

function scheduleSave(delay = SAVE_DEBOUNCE_MS) {
  if (!state.pid) return;
  state.save.dirty = true;
  setSaveStatus("unsaved");
  clearTimeout(state.save.timer);
  state.save.timer = setTimeout(flushSave, delay);
}

/**
 * PUTs the present at the revision the page last saw and says what happened: "clean" (nothing to save), "busy" (a
 * save is running and reschedules when it lands), "saved", "conflict" (409: the server's copy is now the page's),
 * "refused" (4xx: the document breaks a rule; waits for the next edit), "failed" (no answer; retried in 3 s) or
 * "switched" (another project opened meanwhile).
 */
async function flushSave({ closing = false } = {}) {
  clearTimeout(state.save.timer);
  if (!state.pid || !state.save.dirty) return "clean";
  if (state.save.inflight) return "busy";
  state.save.inflight = true;
  state.save.dirty = false;
  setSaveStatus("saving…");
  const pid = state.pid;
  const body = { ...state.hist.present, rev: state.serverRev };
  let outcome;
  try {
    const keepalive = closing && JSON.stringify(body).length < 60000;
    const r = await api.saveProject(pid, body, { keepalive });
    if (pid !== state.pid) return "switched";
    if (r.ok && r.project) {
      state.serverRev = r.project.rev;
      state.save.saves++;
      state.save.error = null;
      state.hist = T.replacePresent(state.hist, { ...state.hist.present, rev: r.project.rev, updated_at: r.project.updated_at });
      setSaveStatus(state.save.dirty ? "unsaved" : "saved");
      if (ui.banner && ui.bannerText.textContent.startsWith("not saved")) ui.banner.hidden = true; // the refusal is over
      outcome = "saved";
    } else if (r.project) {
      state.save.conflicts++;
      adopt(r.project);
      banner("changed elsewhere - reloaded");
      state.save.dirty = false;
      setSaveStatus("reloaded");
      outcome = "conflict";
    } else {
      throw new Error(r.error || "the server refused the save");
    }
  } catch (err) {
    state.save.dirty = true;
    state.save.error = err.message;
    if (err.status >= 400 && err.status < 500) {
      // a refusal (the document breaks a rule the server checks): retrying the same bytes cannot help, so say why
      // and wait; the next edit or an undo tries again
      state.save.refusals = (state.save.refusals || 0) + 1;
      setSaveStatus("not saved: refused");
      banner(`not saved: ${err.message}`, 0);
      return "refused";
    }
    clearTimeout(state.save.timer);
    state.save.timer = setTimeout(flushSave, SAVE_RETRY_MS); // the server did not answer: try the same save again
    setSaveStatus(`not saved (${err.message}); retrying`);
    return "failed";
  } finally {
    state.save.inflight = false;
  }
  if (state.save.dirty) scheduleSave();
  return outcome;
}

function setSaveStatus(text) {
  state.save.status = text;
  if (ui.saveStatus) ui.saveStatus.textContent = text;
}

/** Takes a document from the server as the new truth: a load, or the winner of a 409. */
function adopt(project) {
  // a trim or move in progress was aimed at the copy being replaced: drop it rather than replay it on theirs
  if (view) view.cancelGesture();
  const d = normalizeDoc(project);
  state.serverRev = d.rev;
  state.hist = T.createHistory(d);
  state.live = null;
  for (const mid of new Set(d.clips.map((c) => c.media_id))) {
    const e = entryFor(mid);
    if (!e.media && !e.polling) track(mid);
  }
  afterChange();
  if (ui.name && document.activeElement !== ui.name) ui.name.value = d.name;
  const known = state.projects.find((p) => p.id === d.id);
  if (known) known.name = d.name;
  if (ui.projects && state.pid) renderProjectSelect();
}

function normalizeDoc(p) {
  const d = { ...T.emptyProject(), ...p };
  d.settings = { ...T.emptyProject().settings, ...(p.settings || {}) };
  d.lanes = { video: (p.lanes && p.lanes.video) || [{ id: "V1" }], audio: (p.lanes && p.lanes.audio) || [] };
  d.clips = Array.isArray(p.clips) ? p.clips : [];
  d.markers = Array.isArray(p.markers) ? p.markers : [];
  return d;
}

// ------------------------------------------------------------- projects --

async function loadProjects() {
  try {
    const r = await api.listProjects();
    state.projects = Array.isArray(r.projects) ? r.projects : [];
  } catch (err) {
    state.projects = [];
    banner(`projects unavailable: ${err.message}`);
    return;
  }
  let pid = safeGet(PROJECT_KEY);
  if (!state.projects.some((p) => p.id === pid)) pid = state.projects[0] ? state.projects[0].id : null;
  if (!pid) {
    try {
      const r = await api.createProject("Untitled edit");
      state.projects = [r.project, ...state.projects];
      pid = r.project.id;
    } catch (err) {
      banner(`could not create a project: ${err.message}`);
      return;
    }
  }
  await openProject(pid);
}

async function openProject(pid) {
  if (state.pid && state.save.dirty) await flushSave();
  try {
    const r = await api.project(pid);
    state.pid = pid;
    safeSet(PROJECT_KEY, pid);
    adopt(r.project);
    playback.seek(0);
    view.fit();
    setSaveStatus("saved");
    renderProjectSelect();
  } catch (err) {
    banner(`could not open project ${pid}: ${err.message}`);
  }
}

async function newProject() {
  const n = state.projects.length + 1;
  try {
    const r = await api.createProject(`Untitled edit ${n}`);
    state.projects = [r.project, ...state.projects.filter((p) => p.id !== r.project.id)];
    await openProject(r.project.id);
    ui.name.focus();
    ui.name.select();
  } catch (err) {
    banner(`could not create a project: ${err.message}`);
  }
}

function renderProjectSelect() {
  const sel = ui.projects;
  sel.innerHTML = "";
  for (const p of state.projects) {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.id === state.pid ? doc().name : p.name;
    sel.append(o);
  }
  sel.value = state.pid || "";
}

// --------------------------------------------------------------- render --

function refreshInspector() {
  const d = doc();
  const clip = state.selected ? d.clips.find((c) => c.id === state.selected) : null;
  const mid = clip ? clip.media_id : state.inspectMid;
  const e = mid ? state.media.get(mid) : null;
  inspector.show({ clip, media: e ? e.media : null, doc: d, jobs: e ? e.jobs : null, shots: e ? e.shotsState : "" });
}

function refreshToolbar() {
  if (!ui.undo) return;
  const d = doc();
  ui.undo.disabled = !T.canUndo(state.hist);
  ui.redo.disabled = !T.canRedo(state.hist);
  ui.del.disabled = !state.selected;
  ui.split.disabled = !T.clipAtTime(d, playback.time);
  ui.play.disabled = !d.clips.length;
  ui.monitorEmpty.hidden = d.clips.length > 0;
}

function onTime(t) {
  const d = doc();
  ui.tc.textContent = `${T.formatTimecode(t, T.docFps(d))} / ${T.formatTimecode(T.totalDuration(d), T.docFps(d))}`;
  const h = T.clipAtTime(d, t);
  const e = h ? state.media.get(h.clip.media_id) : null;
  ui.monitorTc.textContent = h ? `${T.formatTimecode(t, T.docFps(d))}  ·  ${e && e.media ? e.media.name : ""} @ ${T.formatTime(h.srcT, 2)}` : "";
  if (playback.playing) view.follow(t); else view.placePlayhead();
  ui.split.disabled = !h;
}

function onPlayState(playing) {
  ui.play.textContent = playing ? "Pause" : "Play";
  ui.play.setAttribute("aria-pressed", String(playing));
  if (playing) meterLoop();
}

let meterRaf = 0;
let meterQuietSince = 0;
function meterLoop() {
  if (meterRaf) return;
  const step = () => {
    meterRaf = 0;
    mixer.meter(playback.levels());
    if (playback.playing) meterQuietSince = performance.now();
    if (playback.playing || performance.now() - meterQuietSince < 1500) meterRaf = requestAnimationFrame(step);
  };
  meterRaf = requestAnimationFrame(step);
}

let bannerTimer = 0;
function banner(text, ms = 6000) {
  if (!ui.banner) return;
  clearTimeout(bannerTimer);
  ui.bannerText.textContent = text;
  ui.banner.hidden = false;
  if (ms) bannerTimer = setTimeout(() => { ui.banner.hidden = true; }, ms);
}

// ------------------------------------------------------------- building --

function button(text, label, onClick, cls = "btn") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = cls;
  b.textContent = text;
  if (label) { b.setAttribute("aria-label", label); b.title = label; }
  b.addEventListener("click", onClick);
  return b;
}

function buildMonitor() {
  const mon = $("edit-monitor");
  mon.innerHTML = "";
  const empty = document.createElement("div");
  empty.className = "ed-monitor-empty";
  empty.innerHTML = "<p class=\"hint-title\">Edit mode</p><p class=\"hint-body\">Drop recordings here or on the Media bin. "
    + "Double-click a bin item to put it on the timeline.</p>";
  const tc = document.createElement("div");
  tc.className = "ed-monitor-tc";
  tc.setAttribute("aria-live", "off");
  const bn = document.createElement("div");
  bn.className = "ed-banner";
  bn.setAttribute("role", "status");
  bn.hidden = true;
  const bt = document.createElement("span");
  const close = button("×", "Dismiss", () => { bn.hidden = true; }, "ed-banner-close");
  bn.append(bt, close);
  mon.append(empty, tc, bn);
  ui.monitorEmpty = empty;
  ui.monitorTc = tc;
  ui.banner = bn;
  ui.bannerText = bt;
  return mon;
}

function buildToolbar(dock) {
  const bar = document.createElement("div");
  bar.className = "ed-toolbar";
  bar.setAttribute("role", "toolbar");
  bar.setAttribute("aria-label", "Timeline");

  const projects = document.createElement("select");
  projects.className = "ed-select ed-projects";
  projects.setAttribute("aria-label", "Project");
  projects.addEventListener("change", () => openProject(projects.value));
  const name = document.createElement("input");
  name.type = "text";
  name.className = "ed-name";
  name.setAttribute("aria-label", "Project name");
  name.addEventListener("change", () => { commit(T.rename(doc(), name.value)); renderProjectSelect(); });
  name.addEventListener("keydown", (e) => { if (e.key === "Enter") name.blur(); });
  const newBtn = button("New", "New project", newProject);

  const play = button("Play", "Play / pause (Space)", () => playback.toggle(), "btn btn-icon");
  play.setAttribute("aria-pressed", "false");
  const tc = document.createElement("output");
  tc.className = "ed-tc";
  tc.textContent = "0:00:00 / 0:00";

  const splitB = button("Split", "Split at the playhead (S)", split);
  const del = button("Delete", "Delete the selected clip (Del)", deleteSelected);
  const undoB = button("Undo", "Undo (Ctrl+Z)", undo);
  const redoB = button("Redo", "Redo (Ctrl+Shift+Z)", redo);
  const zout = button("−", "Zoom out (−)", () => view.zoom(1 / 1.5));
  const zfit = button("Fit", "Fit the timeline (\\)", () => view.fit());
  const zin = button("+", "Zoom in (+)", () => view.zoom(1.5));
  const help = button("?", "Keyboard shortcuts (?)", () => toggleHelp());
  help.setAttribute("aria-expanded", "false");
  help.setAttribute("aria-controls", "ed-help");
  const saveStatus = document.createElement("span");
  saveStatus.className = "ed-save";
  saveStatus.setAttribute("role", "status");

  const group = (...nodes) => { const g = document.createElement("div"); g.className = "ed-group"; g.append(...nodes); return g; };
  bar.append(group(projects, name, newBtn), group(play, tc), group(splitB, del, undoB, redoB),
    group(zout, zfit, zin), group(help, saveStatus));
  dock.append(bar);

  const pop = document.createElement("div");
  pop.className = "ed-help";
  pop.id = "ed-help";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "Keyboard shortcuts");
  pop.hidden = true;
  const title = document.createElement("h3");
  title.className = "ed-sub";
  title.textContent = "Keyboard shortcuts";
  const dl = document.createElement("dl");
  for (const [k, what] of SHORTCUTS) {
    const dt = document.createElement("dt");
    const kbd = document.createElement("kbd");
    kbd.textContent = k;
    dt.append(kbd);
    const dd = document.createElement("dd");
    dd.textContent = what;
    dl.append(dt, dd);
  }
  const closeHelp = button("Close", "Close the shortcuts", () => toggleHelp(false));
  pop.append(title, dl, closeHelp);
  dock.append(pop);

  Object.assign(ui, { projects, name, play, tc, split: splitB, del, undo: undoB, redo: redoB, help, helpPop: pop, saveStatus });
}

function toggleHelp(force) {
  const open = force === undefined ? ui.helpPop.hidden : force;
  ui.helpPop.hidden = !open;
  ui.help.setAttribute("aria-expanded", String(open));
  if (open) ui.helpPop.querySelector("button").focus(); else ui.help.focus();
}

// ------------------------------------------------------------- keyboard --

function typing(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

function onKey(e) {
  if (!state.started || !isEdit()) return;
  if (e.key === "Escape") {
    if (!ui.helpPop.hidden) { toggleHelp(false); e.preventDefault(); return; }
    view.cancelGesture();
    select(null);
    return;
  }
  const el = document.activeElement;
  if (typing(el)) return;
  const mod = e.ctrlKey || e.metaKey;
  const key = e.key;
  if (mod && (key === "z" || key === "Z")) { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
  if (mod && (key === "y" || key === "Y")) { e.preventDefault(); redo(); return; }
  if (mod || e.altKey) return;
  if (key === " " && el && el.tagName === "BUTTON") return; // the focused button's own Space
  const d = doc();
  switch (key) {
    case " ": e.preventDefault(); playback.toggle(); break;
    case "s": case "S": e.preventDefault(); split(); break;
    case "Delete": case "Backspace": e.preventDefault(); deleteSelected(); break;
    case "ArrowLeft": e.preventDefault(); playback.seek(Math.max(0, playback.time - (e.shiftKey ? 1 : 1 / fpsAt(playback.time)))); break;
    case "ArrowRight": e.preventDefault(); playback.seek(Math.min(T.totalDuration(d), playback.time + (e.shiftKey ? 1 : 1 / fpsAt(playback.time)))); break;
    case "ArrowUp": e.preventDefault(); selectStep(-1); break;
    case "ArrowDown": e.preventDefault(); selectStep(1); break;
    case "Home": e.preventDefault(); playback.seek(0); break;
    case "End": e.preventDefault(); playback.seek(T.totalDuration(d)); break;
    case "[": e.preventDefault(); trimToPlayhead("in"); break;
    case "]": e.preventDefault(); trimToPlayhead("out"); break;
    case "+": case "=": e.preventDefault(); view.zoom(1.5); break;
    case "-": case "_": e.preventDefault(); view.zoom(1 / 1.5); break;
    case "\\": e.preventDefault(); view.fit(); break;
    case "?": e.preventDefault(); toggleHelp(); break;
    default: return;
  }
}

// ----------------------------------------------------------------- start --

function start() {
  if (state.started) return;
  state.started = true;
  const dock = $("edit-dock");
  dock.innerHTML = "";
  const monitor = buildMonitor();
  buildToolbar(dock);
  const lanes = document.createElement("div");
  lanes.className = "ed-lanes";
  dock.append(lanes);

  playback = createPlayback({
    monitor, getDoc: doc, getMedia: (mid) => state.media.get(mid), onTime, onState: onPlayState,
  });
  view = createTimelineView(lanes, {
    getDoc: doc,
    getInfo: infoFor,
    getPlayhead: () => playback.time,
    onSeek: (t) => playback.seek(t),
    onCommit: (next) => commit(next),
    onSelect: (id) => { if (state.selected !== id) select(id); },
    onDropMedia: (mid, i) => insertMedia([mid], i),
    onDropFiles: (files, i) => importFiles(files, i),
    requestPlan: planCache,
    onPreview: previewFrame,
    onPreviewEnd: () => { clearTimeout(previewTimer); previewTimer = 0; playback.seek(playback.time); },
  });
  bin = createBin($("edit-bin"), {
    getEntries: binEntries,
    onImportFiles: (files) => importFiles(files),
    onImportPath: importPath,
    onAppend: (mid) => insertMedia([mid]),
    onInspect: (mid) => { state.inspectMid = mid; if (state.selected) select(null); else refreshInspector(); },
  });
  inspector = createInspector($("edit-inspector"), {
    onEntry: (clipId, n, patch) => commit(T.setClipAudio(doc(), clipId, n, patch)),
  });
  mixer = createMixer($("edit-mixer"), {
    onChange: (laneId, patch, final) => {
      if (final) commit(T.setLane(state.hist.present, laneId, patch), "gain_db" in patch ? `gain:${laneId}` : "");
      else { state.live = T.setLane(state.hist.present, laneId, patch); view.invalidate(); playback.refresh(); }
    },
  });
  exporter = createExportPanel($("edit-export"), {
    getProjectId: () => state.pid,
    beforeRender: saveNow,
  });

  // drops on the monitor import and append
  const stage = $("stage");
  stage.addEventListener("drop", (e) => {
    if (!isEdit()) return;
    const files = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
    if (files.length) importFiles(files, Infinity);
  });

  window.addEventListener("keydown", onKey);
  // Known gap: when a save is still in flight at close, edits made during its round trip are not sent. A keepalive
  // PUT would have to guess the revision that save gets, and a wrong guess overwrites another writer.
  window.addEventListener("pagehide", () => { if (state.save.dirty) flushSave({ closing: true }); });

  api.listMedia().then((r) => {
    for (const raw of Array.isArray(r.media) ? r.media : []) {
      const e = setMedia(raw);
      if (e) track(e.mid);
    }
    bin.render();
  }).catch((err) => bin.message(err.notBuilt ? err.message : `media list unavailable: ${err.message}`, "error"));
  exporter.load();
  mixer.render(doc());
  refreshToolbar();
  loadProjects();

  window.arsenalEdit = {
    get doc() { return doc(); },
    get pid() { return state.pid; },
    get selected() { return state.selected; },
    commit, undo, redo, split, select, seek: (t) => playback.seek(t),
    media: (mid) => state.media.get(mid),
    playback, view,
    stats: () => ({ view: view.stats(), playback: playback.stats(), save: { ...state.save, timer: undefined } }),
  };
}

// the trim gesture's monitor preview, at most one seek per 60 ms (a seek on HEVC costs a decode from a keyframe)
let previewTimer = 0;
let previewWant = null;
function previewFrame(mid, srcT) {
  previewWant = [mid, srcT];
  if (previewTimer) return;
  playback.preview(mid, srcT);
  const e = state.media.get(mid);
  ui.monitorTc.textContent = `trim  ·  ${e && e.media ? e.media.name : ""} @ ${T.formatTime(srcT, 2)}`;
  previewTimer = setTimeout(function again() {
    previewTimer = 0;
    if (previewWant && (previewWant[0] !== mid || previewWant[1] !== srcT)) previewFrame(previewWant[0], previewWant[1]);
  }, 60);
}

/**
 * Saves now and waits until the server holds what the page shows; returns that revision (the render reads the file
 * the server has). Throws instead when a save cannot land (refused, no answer, or another writer's copy came back),
 * so a render never runs on a revision the page no longer shows.
 */
async function saveNow(timeoutMs = 20000) {
  const until = performance.now() + timeoutMs;
  for (;;) {
    if (performance.now() > until) throw new Error("the save did not finish in time; try again");
    if (state.save.inflight) { await sleep(50); continue; }
    if (!state.save.dirty) return state.serverRev;
    const outcome = await flushSave();
    if (outcome === "refused") throw new Error(`the server refused the last save (${state.save.error}); undo or fix that edit first`);
    if (outcome === "failed") throw new Error(`the save did not reach the server (${state.save.error})`);
    if (outcome === "conflict") throw new Error("the project changed elsewhere and was reloaded; look it over, then render again");
  }
}

// cut.plan answers for trim hints: asked only once the pointer rests 150 ms on a position, remembered per position
const plans = new Map();
let planTimer = 0;
let planDrop = null;
function planCache(mid, start, end) {
  const key = `${mid}|${start.toFixed(3)}|${end.toFixed(3)}`;
  if (plans.has(key)) return Promise.resolve(plans.get(key));
  clearTimeout(planTimer);
  if (planDrop) planDrop(null);
  return new Promise((resolve) => {
    planDrop = resolve;
    planTimer = setTimeout(() => {
      planDrop = null;
      api.cutplan(mid, start, end).then((p) => {
        plans.set(key, p);
        if (plans.size > 300) plans.delete(plans.keys().next().value);
        resolve(p);
      }, () => resolve(null));
    }, 150);
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function safeGet(k) {
  try { return localStorage.getItem(k); } catch (_) { return null; }
}

function safeSet(k, v) {
  try { localStorage.setItem(k, v); } catch (_) { /* private mode: the project still opens, it is just not remembered */ }
}

window.addEventListener("arsenal:mode", (e) => {
  if (e.detail && e.detail.mode === "edit") {
    start();
    view.invalidate();
  } else if (state.started) {
    playback.pause();
    if (state.save.dirty) flushSave();
  }
});
if (isEdit()) start();
