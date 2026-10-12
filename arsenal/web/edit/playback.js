// arsenal/web/edit/playback.js
// Plays the timeline in the program monitor: picture from one muted <video> per source, sound from the demuxed
// per-track files routed through WebAudio, so every audio lane has its own gain and level meter.
//
// Why not the video's own audio: Chromium here has no HTMLMediaElement.audioTracks (measured, PRIMITIVES-SPEC P6), so
// a multi-track recording plays only its first track. The server demuxes each track to its own file
// (/api/edit/media/<mid>/audio/<n>) and the page mixes them.
//
// Graph per lane: <audio> (one per lane x source track, so a cut between sources never waits for a src swap)
//   -> MediaElementSource -> entry gain (the clip's own gain/mute) -> lane gain (lane gain, mute, solo)
//   -> AnalyserNode (the mixer's meter) -> destination.
// Source times are file times (seconds from the file's start, as edit.render cuts them); a <video> element counts on
// the container's own clock, so every read and seek of one goes through T.sourceTime / T.elementTime (1.4 s apart on
// an MPEG-TS remux, 0 on the OBS recordings).
// The video is the clock. Every animation frame each playing <audio> is compared with the video's source time and
// re-seeked when it drifts more than 40 ms; across a clip boundary the next source (pre-seeked a second ahead on a
// second <video> of the same file when the cut jumps inside it) takes over. A gap on V1 (the CLI can leave one) plays
// as black and silence on a wall clock, as edit.render renders it.
//
// Measured 2026-10-12, headless Chrome 154 on OBS recordings (HEVC 1080p60, Opus, 3 tracks) through arsenal serve:
// between resyncs every lane stayed within 17 ms of the picture; one resync per lane when a source starts, 0 dropped
// of 315 frames across a cut between two recordings.

import * as T from "./timeline.js";
import * as api from "./api.js";

export const RESYNC_S = 0.040;
const PREROLL_S = 1.0;
const PLAYERS_PER_SOURCE = 2; // A/B: a jump inside one file pre-seeks the idle twin

export function createPlayback({ monitor, getDoc, getMedia, onTime = () => {}, onState = () => {} }) {
  const players = new Map(); // mid -> [{el, mid}]
  const voices = new Map(); // lane|mid|track -> {el, node, gain, lane}
  const lanes = new Map(); // laneId -> {gain, analyser, buf}
  let ctx = null;
  let active = null; // {player, clipId}
  let prepared = null; // {player, clipId}
  let playing = false;
  let t = 0; // timeline seconds
  let raf = 0;
  let wallLast = 0; // the clock in a gap, where no video element keeps time
  const stats = { resyncs: 0, maxDriftMs: 0, boundaries: 0, lastDriftMs: {} };

  // ------------------------------------------------------------ elements --

  function player(mid, avoid) {
    let list = players.get(mid);
    if (!list) { list = []; players.set(mid, list); }
    let p = list.find((x) => x !== avoid);
    if (!p && list.length < PLAYERS_PER_SOURCE) {
      const el = document.createElement("video");
      el.className = "ed-video";
      el.muted = true;
      el.playsInline = true;
      el.preload = "auto";
      el.src = api.videoUrl(mid);
      el.setAttribute("aria-hidden", "true");
      monitor.appendChild(el);
      p = { el, mid };
      list.push(p);
    }
    return p || list[0];
  }

  function show(p) {
    for (const list of players.values()) {
      for (const x of list) x.el.classList.toggle("active", x === p);
    }
  }

  function ensureContext() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC({ latencyHint: "playback" });
    for (const v of voices.values()) attach(v);
    return ctx;
  }

  function laneNode(laneId) {
    let n = lanes.get(laneId);
    if (!n && ctx) {
      const gain = ctx.createGain();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0;
      gain.connect(analyser);
      analyser.connect(ctx.destination);
      n = { gain, analyser, buf: new Float32Array(analyser.fftSize) };
      lanes.set(laneId, n);
    }
    return n;
  }

  function attach(v) {
    if (!ctx || v.node) return;
    v.node = ctx.createMediaElementSource(v.el);
    v.gain = ctx.createGain();
    v.node.connect(v.gain);
    v.gain.connect(laneNode(v.lane).gain);
  }

  function voice(laneId, mid, track) {
    const key = `${laneId}|${mid}|${track}`;
    let v = voices.get(key);
    if (!v) {
      const el = new Audio();
      el.preload = "auto";
      el.src = api.audioUrl(mid, track);
      v = { key, el, node: null, gain: null, lane: laneId, failed: false };
      el.addEventListener("error", () => { v.failed = true; });
      voices.set(key, v);
      attach(v);
    }
    return v;
  }

  // -------------------------------------------------------------- clock ---

  function mediaOf(mid) {
    const e = getMedia(mid);
    return e ? e.media : null;
  }

  /** The source file time a player shows (its element counts on the container's clock). */
  function srcTime(p) {
    return T.sourceTime(mediaOf(p.mid), p.el.currentTime);
  }

  function seekSrc(p, srcT) {
    p.el.currentTime = T.elementTime(mediaOf(p.mid), srcT);
  }

  function hit(doc, at) {
    return T.clipAtTime(doc, Math.min(at, Math.max(0, T.totalDuration(doc) - 1e-6)));
  }

  /** Points the monitor and every lane at timeline time `at` (or at `forced`, a known hit); returns the hit or null. */
  function cue(at, { seekVideo = true, forced = null } = {}) {
    const doc = getDoc();
    const h = forced || hit(doc, at);
    if (!h) {
      show(null);
      active = null;
      for (const v of voices.values()) if (!v.el.paused) v.el.pause();
      return null;
    }
    let p = active && active.clipId === h.clip.id ? active.player : null;
    if (!p) {
      p = prepared && prepared.clipId === h.clip.id ? prepared.player : player(h.clip.media_id, active && active.player);
      prepared = null;
    }
    if (seekVideo && Math.abs(srcTime(p) - h.srcT) > 0.5 / T.docFps(doc)) seekSrc(p, h.srcT);
    active = { player: p, clipId: h.clip.id };
    show(p);
    return h;
  }

  function syncAudio(doc, h, srcT) {
    const want = new Set();
    for (const lane of doc.lanes.audio) {
      const n = laneNode(lane.id);
      if (n) n.gain.gain.value = T.laneAudible(doc, lane.id) ? T.dbToGain(lane.gain_db || 0) : 0;
      const entry = h ? h.clip.audio.find((a) => a.lane === lane.id) : null;
      if (!entry) continue;
      const m = getMedia(h.clip.media_id);
      if (!m || !m.demuxReady) continue;
      const v = voice(lane.id, h.clip.media_id, entry.src_track);
      want.add(v.key);
      if (v.gain) v.gain.gain.value = entry.mute ? 0 : T.dbToGain(entry.gain_db || 0);
      if (v.failed || v.el.readyState < 1) continue;
      const track = m.media && m.media.audio[entry.src_track];
      const fileT = Math.max(0, srcT - ((track && track.start_s) || 0)); // the demuxed file starts at start_s
      const drift = v.el.currentTime - fileT;
      if (playing) {
        if (v.el.paused) {
          v.el.currentTime = fileT;
          v.el.play().catch(() => {});
        } else if (Math.abs(drift) > RESYNC_S) {
          v.el.currentTime = fileT;
          stats.resyncs++;
        }
        const ms = Math.abs(drift) * 1000;
        stats.lastDriftMs[lane.id] = Math.round(ms * 10) / 10;
        if (!v.el.paused && ms < 1000) stats.maxDriftMs = Math.max(stats.maxDriftMs, ms);
      } else {
        if (!v.el.paused) v.el.pause();
        if (Math.abs(drift) > RESYNC_S) v.el.currentTime = fileT;
      }
    }
    for (const v of voices.values()) if (!want.has(v.key) && !v.el.paused) v.el.pause();
  }

  function prepareNext(doc, h) {
    const order = T.videoClips(doc);
    const next = order[h.index + 1];
    if (!next || (prepared && prepared.clipId === next.id)) return;
    const contiguous = next.media_id === h.clip.media_id && Math.abs(next.src_in - h.clip.src_out) < 1e-6;
    if (contiguous) return; // the playing element simply carries on
    const p = player(next.media_id, active.player);
    seekSrc(p, next.src_in);
    prepared = { player: p, clipId: next.id };
  }

  /** Leaves the picture black and the lanes silent from timeline time `at` (a gap on V1): the clock runs on its own. */
  function enterGap(doc, at) {
    if (active) active.player.el.pause();
    active = null;
    show(null);
    t = at;
    wallLast = performance.now();
    syncAudio(doc, null, 0);
  }

  function tick() {
    raf = 0;
    if (!playing) return;
    const doc = getDoc();
    const order = T.videoClips(doc);
    const now = performance.now();
    let idx = active ? order.findIndex((c) => c.id === active.clipId) : -1;
    if (idx < 0) { // in a gap, or the clip under the playhead was edited away while playing
      if (!active) { t += (now - wallLast) / 1000; wallLast = now; }
      const total = T.totalDuration(doc);
      if (t >= total) { t = total; pause(); onTime(t); return; }
      const h = cue(t);
      if (!h) { enterGap(doc, t); onTime(t); raf = requestAnimationFrame(tick); return; }
      active.player.el.play().catch(() => {});
      idx = h.index;
    }
    const c = order[idx];
    const el = active.player.el;
    const src = srcTime(active.player);
    t = c.at + (src - c.src_in);
    if (src >= c.src_out - 0.5 / T.docFps(doc) || el.ended) {
      const next = order[idx + 1];
      if (!next) {
        t = T.totalDuration(doc);
        pause();
        onTime(t);
        return;
      }
      stats.boundaries++;
      if (next.at > T.clipEnd(c) + 1e-4) { // a gap: black and silence until the next clip, as edit.render plays it
        enterGap(doc, T.clipEnd(c));
        onTime(t);
        raf = requestAnimationFrame(tick);
        return;
      }
      t = next.at;
      if (next.media_id === c.media_id && Math.abs(next.src_in - c.src_out) < 1e-6) {
        active = { player: active.player, clipId: next.id }; // contiguous: the same element carries on
      } else {
        const old = active.player;
        // the next clip by name, not by a time lookup: the boundary instant is where float noise lives
        cue(t, { forced: { clip: next, index: idx + 1, srcT: next.src_in } });
        if (active.player !== old) old.el.pause();
        active.player.el.play().catch(() => {});
      }
      syncAudio(doc, { clip: next, index: idx + 1 }, next.src_in);
    } else {
      if (c.src_out - src < PREROLL_S) prepareNext(doc, { clip: c, index: idx });
      syncAudio(doc, { clip: c, index: idx }, src);
    }
    onTime(t);
    raf = requestAnimationFrame(tick);
  }

  // ------------------------------------------------------------ control ---

  function play() {
    const doc = getDoc();
    const total = T.totalDuration(doc);
    if (!(total > 0)) return;
    if (t >= total - 1e-3) t = 0;
    const c = ensureContext();
    if (c && c.state === "suspended") c.resume().catch(() => {});
    const h = cue(t);
    playing = true;
    if (h) {
      active.player.el.play().catch(() => {});
      syncAudio(doc, h, h.srcT);
    } else {
      enterGap(doc, t);
    }
    onState(true);
    if (!raf) raf = requestAnimationFrame(tick);
  }

  function pause() {
    playing = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    for (const list of players.values()) for (const p of list) if (!p.el.paused) p.el.pause();
    for (const v of voices.values()) if (!v.el.paused) v.el.pause();
    onState(false);
  }

  function seek(at) {
    const doc = getDoc();
    t = Math.max(0, Math.min(at, T.totalDuration(doc)));
    const h = cue(t);
    if (playing && h) active.player.el.play().catch(() => {});
    if (playing && !h) enterGap(doc, t); // restarts the gap clock from here
    else syncAudio(doc, h, h ? h.srcT : 0);
    onTime(t);
  }

  /** The document changed (an edit, a gain): keep the playhead's timeline time, re-point picture and sound. */
  function refresh() {
    const doc = getDoc();
    if (t > T.totalDuration(doc)) t = T.totalDuration(doc);
    if (!playing) {
      seek(t);
      return;
    }
    const c = active && doc.clips.find((x) => x.id === active.clipId);
    const src = active ? srcTime(active.player) : NaN;
    if (c && c.media_id === active.player.mid && src >= c.src_in - 1e-3 && src < c.src_out) {
      // the edit left this clip playing where it is (a fader, a mute, a trim elsewhere): never seek the picture,
      // which would stall it; only the timeline time and the mix follow
      t = c.at + (src - c.src_in);
      syncAudio(doc, { clip: c }, src);
      return;
    }
    const h = cue(t, { seekVideo: true });
    if (!h) { enterGap(doc, t); return; }
    if (active.player.el.paused) active.player.el.play().catch(() => {});
    syncAudio(doc, h, h.srcT);
  }

  /**
   * Shows one source frame without moving the playhead (the trim gesture's edge); seek(time) puts the monitor back.
   * Ignored while playing.
   */
  function preview(mid, srcT) {
    if (playing || !Number.isFinite(srcT)) return;
    const own = active && active.player.mid === mid ? active.player : null;
    const p = own || player(mid, null);
    if (Math.abs(srcTime(p) - srcT) > 1e-3) seekSrc(p, srcT);
    show(p);
  }

  /** Peak level per lane in dBFS since the last call (the mixer's meters); -Infinity when silent or unknown. */
  function levels() {
    const out = {};
    for (const [id, n] of lanes) {
      n.analyser.getFloatTimeDomainData(n.buf);
      let peak = 0;
      for (let i = 0; i < n.buf.length; i++) { const a = Math.abs(n.buf[i]); if (a > peak) peak = a; }
      out[id] = peak > 1e-6 ? T.gainToDb(peak) : -Infinity; // below -120 dBFS is silence
    }
    return out;
  }

  /** Drops the elements of a media that left the document (keeps memory flat across long sessions). */
  function forget(keepMids) {
    for (const [mid, list] of players) {
      if (keepMids.has(mid)) continue;
      for (const p of list) { p.el.pause(); p.el.removeAttribute("src"); p.el.load(); p.el.remove(); }
      players.delete(mid);
    }
    for (const [key, v] of voices) {
      if (keepMids.has(key.split("|")[1])) continue;
      v.el.pause();
      v.el.removeAttribute("src");
      if (v.node) v.node.disconnect();
      voices.delete(key);
    }
    if (active && !keepMids.has(active.player.mid)) active = null;
    if (prepared && !keepMids.has(prepared.player.mid)) prepared = null;
  }

  return {
    play, pause, seek, refresh, levels, forget, preview,
    toggle: () => (playing ? pause() : play()),
    get playing() { return playing; },
    get time() { return t; },
    get audioRunning() { return !!ctx && ctx.state === "running"; },
    stats: () => ({ ...stats, voices: voices.size, players: [...players.values()].reduce((a, l) => a + l.length, 0) }),
  };
}
