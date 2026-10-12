// arsenal/web/edit/render.js
// The Export panel: pick a preset (GET /api/edit/presets), save, render the project (POST .../render -> a job),
// follow the job's progress, then show where the file landed and what the QC pass said. The server writes into a new
// folder (aurora-edits/<project>/ under its library root by default), never beside or over an original.
//
// The render reads the project file the server holds, so the panel renders only once the page's own copy has landed
// there (beforeRender resolves with that revision) and names the revision it rendered.

import * as api from "./api.js";

const POLL_MS = 500;
const PRESET_KEY = "arsenal.edit.preset";
// edit.render's own default: 4K60 on the AMF encoder, minutes rather than the x264 preset's hour
const DEFAULT_PRESET = "youtube_4k60_fast";

/**
 * The words and tone for a finished render's checks: "ok" only when audio.qc ran and found nothing and the output's
 * duration matched the timeline; "warn" when QC found problems, was skipped, failed to run or did not run, or the
 * duration is off. result is the render job's result ({path, duration_s, duration_expected_s, duration_ok, qc}).
 */
export function qcSummary(result) {
  const res = result || {};
  const qc = res.qc && typeof res.qc === "object" ? res.qc : null;
  const facts = [];
  const issues = [];
  if (qc && Number.isFinite(qc.I)) facts.push(`${qc.I.toFixed(1)} LUFS`);
  if (qc && Number.isFinite(qc.TP)) facts.push(`${qc.TP.toFixed(1)} dBTP`);
  const dur = qc && Number.isFinite(qc.duration_s) ? qc.duration_s : res.duration_s;
  if (Number.isFinite(dur)) facts.push(`${dur.toFixed(2)} s`);
  if (res.duration_ok === false) {
    const want = Number.isFinite(res.duration_expected_s) ? `${res.duration_expected_s.toFixed(2)} s` : "the timeline's length";
    issues.push(`duration ${Number.isFinite(res.duration_s) ? res.duration_s.toFixed(2) + " s" : "unknown"}, expected ${want}`);
  }
  let verdict;
  if (!qc) verdict = "QC not run";
  else if (qc.error) verdict = `QC failed to run: ${qc.error}`;
  else if (qc.skipped) verdict = `QC skipped: ${qc.skipped}`;
  else if (!Array.isArray(qc.problems)) verdict = "QC gave no verdict";
  else if (qc.problems.length || qc.ok === false) verdict = `QC: ${qc.problems.length ? qc.problems.join("; ") : "not ok"}`;
  else verdict = issues.length ? "QC passed the audio checks" : "QC clean";
  const clean = verdict === "QC clean";
  return { kind: clean ? "ok" : "warn", text: [...facts, ...issues, verdict].join(" · ") };
}

export function createExportPanel(root, { getProjectId, beforeRender }) {
  root.innerHTML = "";
  root.classList.add("ed-export");
  const row = document.createElement("div");
  row.className = "ed-export-row";
  const select = document.createElement("select");
  select.className = "ed-select";
  select.setAttribute("aria-label", "Export preset");
  const go = document.createElement("button");
  go.type = "button";
  go.className = "btn";
  go.textContent = "Render";
  row.append(select, go);
  const progress = document.createElement("progress");
  progress.className = "ed-progress";
  progress.max = 1;
  progress.value = 0;
  progress.hidden = true;
  progress.setAttribute("aria-label", "Render progress");
  const status = document.createElement("p");
  status.className = "ed-export-status";
  status.setAttribute("role", "status");
  root.append(row, progress, status);
  let busy = false;
  let loaded = false;

  function say(text, kind = "") {
    status.textContent = text;
    if (kind) status.dataset.kind = kind; else delete status.dataset.kind;
  }

  async function load() {
    if (loaded) return;
    try {
      const data = await api.presets();
      const list = Array.isArray(data.presets) ? data.presets : [];
      select.innerHTML = "";
      for (const p of list) {
        const o = document.createElement("option");
        o.value = p.id;
        o.textContent = p.label || p.id;
        if (p.why) o.title = p.why;
        select.append(o);
      }
      const ids = list.map((p) => p.id);
      const remembered = safeGet(PRESET_KEY);
      select.value = ids.includes(remembered) ? remembered : ids.includes(DEFAULT_PRESET) ? DEFAULT_PRESET : ids[0] || "";
      select.disabled = !list.length;
      go.disabled = !list.length;
      say(list.length ? "" : "no export presets");
      loaded = true;
    } catch (err) {
      select.disabled = true;
      go.disabled = true;
      say(err.notBuilt ? `export: ${err.message}` : `presets unavailable: ${err.message}`);
    }
  }

  async function run() {
    const pid = getProjectId();
    if (!pid || busy) return;
    busy = true;
    go.disabled = true;
    progress.hidden = false;
    progress.value = 0;
    say("saving, then rendering…");
    try {
      let rev;
      try {
        rev = await beforeRender();
      } catch (err) {
        progress.hidden = true;
        say(`not rendered: ${err.message}`, "error");
        return;
      }
      const r = await api.render(pid, select.value);
      const job = r.job || r;
      const jid = job.id || job.job_id;
      if (!jid) throw new Error("the server answered without a job id");
      const shown = Number.isFinite(job.rev) ? job.rev : rev;
      say(`rendering${revWords(shown)}…`);
      await follow(jid, shown);
    } catch (err) {
      say(`render failed: ${err.message}`, "error");
    } finally {
      busy = false;
      go.disabled = false;
    }
  }

  async function follow(jid, rev) {
    for (;;) {
      const j = await api.job(jid);
      const p = Number(j.progress);
      if (Number.isFinite(p)) progress.value = Math.max(0, Math.min(1, p));
      if (j.state === "done" || j.state === "error" || j.error) {
        if (j.state === "error" || j.error) throw new Error(j.error || "the render job failed");
        progress.value = 1;
        const res = j.result || {};
        const qc = qcSummary(res);
        say("", qc.kind);
        const path = document.createElement("code");
        path.textContent = res.path || "(no path reported)";
        status.append(`Rendered${revWords(rev)} to `, path, ` · ${qc.text}`);
        return;
      }
      say(`rendering${revWords(rev)}… ${Math.round(progress.value * 100)}%`);
      await new Promise((r) => setTimeout(r, POLL_MS));
    }
  }

  select.addEventListener("change", () => safeSet(PRESET_KEY, select.value));
  go.addEventListener("click", run);
  return { load, get busy() { return busy; } };
}

const revWords = (rev) => (Number.isFinite(rev) ? ` revision ${rev}` : "");

function safeGet(k) {
  try { return localStorage.getItem(k); } catch (_) { return null; }
}

function safeSet(k, v) {
  try { localStorage.setItem(k, v); } catch (_) { /* private mode: the choice is just not remembered */ }
}
