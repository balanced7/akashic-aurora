// arsenal/web/edit/bin.js
// The Media bin: every file imported into the editor, and a drop target. A browser drop hands the page only a name,
// a size and a modified time, never a path, so the server finds the real file under its library roots
// (POST /api/edit/import) and nothing is copied or uploaded. A pasted path imports the same way.

import * as T from "./timeline.js";

const MEDIA_MIME = "application/x-arsenal-media";
const JOB_KEYS = ["demux", "peaks", "shots"];

export function createBin(root, { getEntries, onImportFiles, onImportPath, onAppend, onInspect }) {
  root.innerHTML = "";
  root.classList.add("ed-bin");
  const list = document.createElement("ul");
  list.className = "ed-bin-list";
  list.setAttribute("aria-label", "Imported media");
  const empty = document.createElement("p");
  empty.className = "ed-bin-empty";
  empty.textContent = "Drop recordings here, on the monitor or on the timeline. They are found under the library "
    + "roots by name and size; nothing is copied.";
  const msg = document.createElement("p");
  msg.className = "ed-bin-msg";
  msg.setAttribute("role", "status");
  msg.hidden = true;
  const form = document.createElement("form");
  form.className = "ed-bin-path";
  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "or paste a file path";
  input.setAttribute("aria-label", "Import a file by its path");
  input.spellcheck = false;
  const go = document.createElement("button");
  go.type = "submit";
  go.className = "btn";
  go.textContent = "Import";
  form.append(input, go);
  root.append(list, empty, msg, form);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = input.value.trim().replace(/^"(.*)"$/, "$1");
    if (p) onImportPath(p).then((ok) => { if (ok) input.value = ""; });
  });

  root.addEventListener("dragover", (e) => {
    if (!Array.from(e.dataTransfer.types).includes("Files")) return;
    e.preventDefault();
    root.classList.add("ed-drop-active");
  });
  root.addEventListener("dragleave", (e) => {
    if (!root.contains(e.relatedTarget)) root.classList.remove("ed-drop-active");
  });
  root.addEventListener("drop", (e) => {
    e.preventDefault();
    root.classList.remove("ed-drop-active");
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) onImportFiles(files);
  });

  const items = new Map(); // mid -> {li, name, meta, jobs, add}

  /** One bin row per media, kept across renders so a double-click or keyboard focus survives a job update. */
  function item(m) {
    const li = document.createElement("li");
    li.className = "ed-bin-item";
    li.tabIndex = 0;
    li.draggable = true;
    li.dataset.mid = m.id;
    const name = document.createElement("div");
    name.className = "name";
    const meta = document.createElement("div");
    meta.className = "meta";
    const jobs = document.createElement("div");
    jobs.className = "ed-jobs";
    const dots = {};
    for (const k of JOB_KEYS) {
      const dot = document.createElement("span");
      dot.textContent = k;
      dots[k] = dot;
      jobs.append(dot);
    }
    const add = document.createElement("button");
    add.type = "button";
    add.className = "btn ed-mini";
    add.textContent = "+";
    add.addEventListener("click", (e) => { e.stopPropagation(); onAppend(m.id); });
    const body = document.createElement("div");
    body.className = "ed-bin-body";
    body.append(name, meta, jobs);
    li.append(body, add);
    li.addEventListener("dblclick", () => onAppend(m.id));
    li.addEventListener("click", () => onInspect(m.id));
    li.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target === li) { e.preventDefault(); onAppend(m.id); }
    });
    li.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData(MEDIA_MIME, m.id);
      e.dataTransfer.setData("text/plain", m.name);
      e.dataTransfer.effectAllowed = "copy";
    });
    return { li, name, meta, dots, add };
  }

  function update(row, entry) {
    const m = entry.media;
    row.li.title = m.path || m.name;
    row.name.textContent = m.name;
    const n = m.audio.length;
    const v = m.video;
    row.meta.textContent = [
      Number.isFinite(m.duration) ? T.formatTime(m.duration) : "?:??",
      v && v.w ? `${v.w}x${v.h}` : null,
      `${n} audio track${n === 1 ? "" : "s"}`,
      m.kind && m.kind !== "unknown" ? m.kind : null,
    ].filter(Boolean).join(" · ");
    for (const k of JOB_KEYS) {
      const s = (entry.jobs && entry.jobs[k]) || "queued";
      const state = s.startsWith("error") ? "error" : s;
      row.dots[k].className = `ed-job ed-job-${state}`;
      row.dots[k].title = `${k}: ${s}`;
    }
    row.add.setAttribute("aria-label", `Append ${m.name} to the timeline`);
  }

  function render() {
    const entries = getEntries();
    const seen = new Set();
    for (const e of entries) {
      let row = items.get(e.media.id);
      if (!row) { row = item(e.media); items.set(e.media.id, row); list.append(row.li); }
      update(row, e);
      seen.add(e.media.id);
    }
    for (const [mid, row] of items) {
      if (!seen.has(mid)) { row.li.remove(); items.delete(mid); }
    }
    empty.hidden = entries.length > 0;
  }

  let msgTimer = 0;
  function message(text, kind = "info", ms = 0) {
    clearTimeout(msgTimer);
    msg.hidden = !text;
    msg.textContent = text || "";
    msg.dataset.kind = kind;
    if (ms) msgTimer = setTimeout(() => { msg.hidden = true; }, ms);
  }

  return { render, message };
}
