// arsenal/web/edit/inspector.js
// The Inspector: what the house knows about the selected clip's file (the probe sidecar: codec, size, frame rate,
// keyframe interval, recorded time, encoder, every audio track with its name, links to a practice session or a
// Riot match), plus the clip's own placement and which of its linked tracks are heard.

import * as T from "./timeline.js";

const LINK_NAMES = { practice_session: "Practice session", match_id: "Riot match", riot_match: "Riot match" };

export function createInspector(root, { onEntry }) {
  root.innerHTML = "";
  root.classList.add("ed-inspector");

  function row(dl, label, value, mono = true) {
    if (value === null || value === undefined || value === "") return;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    if (!mono) dd.classList.add("plain");
    if (value instanceof Node) dd.append(value); else dd.textContent = String(value);
    dl.append(dt, dd);
  }

  function fileFacts(dl, m) {
    const v = m.video || {};
    row(dl, "File", m.name, false);
    row(dl, "Duration", Number.isFinite(m.duration) ? T.formatTime(m.duration, 2) : null);
    row(dl, "Container", m.container);
    row(dl, "Video", v.codec ? `${v.codec}${v.w ? ` · ${v.w}x${v.h}` : ""}` : null);
    row(dl, "Frame rate", Number.isFinite(v.fps) ? `${+v.fps.toFixed(3)} fps${v.vfr ? " (variable)" : ""}` : null);
    row(dl, "Keyframes", Number.isFinite(v.keyint_s)
      ? `every ${v.keyint_s.toFixed(2)} s${Number.isFinite(v.keyframes_n) ? ` · ${v.keyframes_n} in all` : ""}` : null);
    row(dl, "B-frames", Number.isFinite(v.has_b_frames) ? (v.has_b_frames ? "yes (smart trim falls back to exact)" : "none") : null);
    const links = m.links || {};
    const rec = links.recorded && typeof links.recorded === "object" ? links.recorded : null;
    const when = m.recorded_at || (rec && rec.start);
    row(dl, "Recorded", when ? `${String(when).replace("T", " ")}${rec && rec.from ? ` · from ${rec.from}` : ""}` : null);
    row(dl, "Encoder", m.encoder, false);
    row(dl, "Kind", m.kind && m.kind !== "unknown" ? m.kind : null);
    row(dl, "Size", Number.isFinite(m.size) && m.size ? `${(m.size / 1048576).toFixed(1)} MB` : null);
    linkRows(dl, links);
    row(dl, "Path", m.path, true);
  }

  /** catalog.link's answer: practice sessions and Riot matches that overlap the recording in wall time. */
  function linkRows(dl, links) {
    const pct = (c) => (Number.isFinite(c) ? ` (${Math.round(c * 100)}%)` : "");
    const sessions = Array.isArray(links.practice_sessions) ? links.practice_sessions : null;
    const matches = Array.isArray(links.riot_matches) ? links.riot_matches : null;
    if (sessions) {
      row(dl, "Practice", sessions.length ? sessions.map((x) => `${x.session}${pct(x.confidence)}`
        + (Number.isFinite(x.events) ? ` · ${x.events} events` : "")).join("\n") : "none at that time");
    }
    if (matches) {
      row(dl, "Riot match", matches.length ? matches.map((x) => `${x.match_id} · ${String(x.relation || "").replace(/_/g, " ")}`
        + pct(x.confidence)).join("\n") : "none at that time");
    }
    for (const [k, val] of Object.entries(links)) {
      if (k === "practice_sessions" || k === "riot_matches" || k === "recorded") continue;
      if (val === null || val === undefined || val === "" || (Array.isArray(val) && !val.length)) continue;
      const text = typeof val === "object" ? (val.id || val.session || val.match_id || JSON.stringify(val)) : val;
      row(dl, LINK_NAMES[k] || k.replace(/_/g, " "), `${text}${typeof val === "object" ? pct(val.confidence) : ""}`);
    }
  }

  function tracks(m, clip, doc) {
    const ul = document.createElement("ul");
    ul.className = "ed-tracks";
    m.audio.forEach((a, n) => {
      const li = document.createElement("li");
      const what = [a.codec, Number.isFinite(a.channels) ? `${a.channels} ch` : null,
        Number.isFinite(a.sample_rate) && a.sample_rate ? `${a.sample_rate / 1000} kHz` : null].filter(Boolean).join(" ");
      const entry = clip ? clip.audio.find((x) => x.src_track === n) : null;
      if (entry) {
        const id = `ed-tr-${clip.id}-${n}`;
        const box = document.createElement("input");
        box.type = "checkbox";
        box.id = id;
        box.checked = !entry.mute;
        box.addEventListener("change", () => onEntry(clip.id, n, { mute: !box.checked }));
        const lab = document.createElement("label");
        lab.htmlFor = id;
        lab.textContent = `a:${n} ${a.label} → ${entry.lane}`;
        li.append(box, lab);
        if (!T.laneAudible(doc, entry.lane)) li.classList.add("dim");
      } else {
        li.textContent = `a:${n} ${a.label}`;
      }
      const meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = what;
      li.append(meta);
      ul.append(li);
    });
    if (!m.audio.length) {
      const li = document.createElement("li");
      li.textContent = "no audio tracks";
      ul.append(li);
    }
    return ul;
  }

  let shownKey = "";

  function show({ clip = null, media = null, doc = null, jobs = null, shots = "" } = {}) {
    // rebuild only when something shown changed, and give focus back to the checkbox that had it
    const lanes = doc ? doc.lanes.audio.map((l) => [l.id, l.mute, l.solo]) : null;
    const key = JSON.stringify([clip, media, jobs, lanes, shots]);
    if (key === shownKey) return;
    shownKey = key;
    const focused = root.contains(document.activeElement) ? document.activeElement.id : "";
    root.innerHTML = "";
    if (!media) {
      const p = document.createElement("p");
      p.className = "ed-muted";
      p.textContent = "Select a clip on the timeline or an item in the Media bin.";
      root.append(p);
      return;
    }
    const dl = document.createElement("dl");
    dl.className = "ed-props";
    if (clip) {
      row(dl, "Clip", `${T.formatTime(clip.src_in, 2)} – ${T.formatTime(clip.src_out, 2)} of the source`);
      row(dl, "On timeline", `at ${T.formatTime(clip.at, 2)} · ${T.formatTime(T.clipDuration(clip), 2)} long`);
    }
    fileFacts(dl, media);
    if (jobs) row(dl, "Analysis", Object.entries(jobs).map(([k, v]) => `${k}: ${v}`).join(" · "));
    if (shots) row(dl, "Scene cuts", shots);
    root.append(dl);
    const h = document.createElement("h3");
    h.className = "ed-sub";
    h.textContent = clip ? "Audio tracks (checked = heard in this clip)" : "Audio tracks";
    root.append(h, tracks(media, clip, doc));
    if (focused) { const el = document.getElementById(focused); if (el) el.focus(); }
  }

  show();
  return { show };
}
